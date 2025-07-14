"""Theme Accessibility Dialog for configuring accessibility features.
Provides a comprehensive interface for users to configure accessibility
settings, test theme compliance, and adjust accessibility features.
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QTabWidget,
    QLabel, QPushButton, QCheckBox, QSlider, QComboBox, QSpinBox,
    QGroupBox, QScrollArea, QTextEdit, QProgressBar, QFrame,
    QButtonGroup, QRadioButton, QWidget, QSplitter, QTreeWidget,
    QTreeWidgetItem, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFileDialog, QColorDialog, QApplication
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QObject, QSize
from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap, QPainter, QIcon

from ..themes.accessibility import (
    AccessibilityManager, AccessibilitySettings, AccessibilityLevel,
    HighContrastLevel, ColorBlindnessSimulator, AccessibilityThemeValidator,
    AccessibilityReport, HighContrastGenerator
)
from ..themes.base import Theme
from ..themes.colors import ColorBlindnessType
from ..themes.engine import ThemeEngine
from ..themes.types import ThemeMetadata

logger = logging.getLogger(__name__)


class AccessibilityTestWorker(QObject):
    """Worker thread for running accessibility tests."""
    
    testCompleted = pyqtSignal(object)  # AccessibilityReport
    testProgress = pyqtSignal(str, int)  # message, percentage
    testError = pyqtSignal(str)
    
    def __init__(self, theme: Theme, target_level: AccessibilityLevel):
        super().__init__()
        self.theme = theme
        self.target_level = target_level
        self.validator = AccessibilityThemeValidator()
    
    def run_test(self):
        """Run comprehensive accessibility test."""
        try:
            self.testProgress.emit("Starting accessibility validation...", 0)
            
            # Run comprehensive validation
            self.testProgress.emit("Validating color contrasts...", 25)
            report = self.validator.validate_theme_accessibility(self.theme, self.target_level)
            
            self.testProgress.emit("Checking color blindness compatibility...", 50)
            # Additional detailed tests would go here
            
            self.testProgress.emit("Generating recommendations...", 75)
            # Additional recommendation generation
            
            self.testProgress.emit("Accessibility test complete!", 100)
            self.testCompleted.emit(report)
            
        except Exception as e:
            logger.error(f"Accessibility test failed: {e}")
            self.testError.emit(str(e))


class ColorBlindnessPreviewWidget(QWidget):
    """Widget for previewing colors under different color blindness conditions."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.original_color = "#007bff"
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the color blindness preview interface."""
        layout = QVBoxLayout(self)
        
        # Original color
        original_frame = QFrame()
        original_frame.setFrameStyle(QFrame.Shape.Box)
        original_frame.setFixedHeight(40)
        original_frame.setStyleSheet(f"background-color: {self.original_color}; border: 1px solid #ccc;")
        
        original_label = QLabel("Original Color")
        original_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Color blindness simulations
        simulations = [
            (ColorBlindnessType.PROTANOPIA, "Protanopia (Red-blind)"),
            (ColorBlindnessType.DEUTERANOPIA, "Deuteranopia (Green-blind)"),
            (ColorBlindnessType.TRITANOPIA, "Tritanopia (Blue-blind)"),
            (ColorBlindnessType.PROTANOMALY, "Protanomaly (Red-weak)"),
            (ColorBlindnessType.DEUTERANOMALY, "Deuteranomaly (Green-weak)"),
            (ColorBlindnessType.TRITANOMALY, "Tritanomaly (Blue-weak)"),
            (ColorBlindnessType.ACHROMATOPSIA, "Achromatopsia (No color)"),
            (ColorBlindnessType.ACHROMATOMALY, "Achromatomaly (Weak color)"),
        ]
        
        self.simulation_frames = {}
        
        layout.addWidget(QLabel("Original:"))
        layout.addWidget(original_frame)
        layout.addWidget(original_label)
        
        layout.addWidget(QLabel("\nColor Blindness Simulations:"))
        
        for blindness_type, description in simulations:
            sim_color = ColorBlindnessSimulator.simulate_color_blindness(
                self.original_color, blindness_type
            )
            
            frame = QFrame()
            frame.setFrameStyle(QFrame.Shape.Box)
            frame.setFixedHeight(30)
            frame.setStyleSheet(f"background-color: {sim_color}; border: 1px solid #ccc;")
            
            label = QLabel(description)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            self.simulation_frames[blindness_type] = frame
            layout.addWidget(frame)
            layout.addWidget(label)
    
    def update_color(self, color: str):
        """Update the color being previewed."""
        self.original_color = color
        
        # Update original color frame
        original_frame = self.findChild(QFrame)
        if original_frame:
            original_frame.setStyleSheet(f"background-color: {color}; border: 1px solid #ccc;")
        
        # Update simulation frames
        for blindness_type, frame in self.simulation_frames.items():
            sim_color = ColorBlindnessSimulator.simulate_color_blindness(color, blindness_type)
            frame.setStyleSheet(f"background-color: {sim_color}; border: 1px solid #ccc;")


class AccessibilityDialog(QDialog):
    """Main accessibility configuration dialog."""
    
    settingsChanged = pyqtSignal(object)  # AccessibilitySettings
    themeTestRequested = pyqtSignal(object, object)  # Theme, AccessibilityLevel
    
    def __init__(self, theme_engine: ThemeEngine, parent=None):
        super().__init__(parent)
        self.theme_engine = theme_engine
        self.accessibility_manager = AccessibilityManager(theme_engine)
        self.current_theme = theme_engine.get_current_theme()
        self.current_settings = self.accessibility_manager.get_accessibility_settings()
        self.test_worker = None
        self.test_thread = None
        
        self.setWindowTitle("Accessibility Settings")
        self.setMinimumSize(800, 600)
        self.setup_ui()
        self.load_current_settings()
        
        # Connect signals
        self.accessibility_manager.settingsChanged.connect(self.on_settings_changed)
        self.accessibility_manager.highContrastToggled.connect(self.on_high_contrast_toggled)
        self.accessibility_manager.colorBlindnessFilterChanged.connect(self.on_color_blindness_filter_changed)
    
    def setup_ui(self):
        """Setup the main dialog interface."""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create tabs
        self.create_general_tab()
        self.create_contrast_tab()
        self.create_color_blindness_tab()
        self.create_testing_tab()
        self.create_advanced_tab()
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.apply_button = QPushButton("Apply")
        self.apply_button.clicked.connect(self.apply_settings)
        
        self.reset_button = QPushButton("Reset")
        self.reset_button.clicked.connect(self.reset_settings)
        
        self.test_button = QPushButton("Run Accessibility Test")
        self.test_button.clicked.connect(self.run_accessibility_test)
        
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        
        button_layout.addWidget(self.apply_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.test_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        layout.addLayout(button_layout)
    
    def create_general_tab(self):
        """Create general accessibility settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Font size adjustments
        font_group = QGroupBox("Font Size Adjustments")
        font_layout = QVBoxLayout(font_group)
        
        self.increased_font_sizes = QCheckBox("Increase font sizes")
        self.increased_font_sizes.setToolTip("Increase font sizes for better readability")
        font_layout.addWidget(self.increased_font_sizes)
        
        # Font size slider
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("Font scale:"))
        
        self.font_scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.font_scale_slider.setRange(100, 200)
        self.font_scale_slider.setValue(100)
        self.font_scale_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.font_scale_slider.setTickInterval(25)
        
        self.font_scale_label = QLabel("100%")
        self.font_scale_slider.valueChanged.connect(
            lambda v: self.font_scale_label.setText(f"{v}%")
        )
        
        font_size_layout.addWidget(self.font_scale_slider)
        font_size_layout.addWidget(self.font_scale_label)
        font_layout.addLayout(font_size_layout)
        
        layout.addWidget(font_group)
        
        # Navigation enhancements
        nav_group = QGroupBox("Navigation Enhancements")
        nav_layout = QVBoxLayout(nav_group)
        
        self.enhanced_focus = QCheckBox("Enhanced focus indicators")
        self.enhanced_focus.setToolTip("Make keyboard focus more visible")
        nav_layout.addWidget(self.enhanced_focus)
        
        self.keyboard_nav_enhanced = QCheckBox("Enhanced keyboard navigation")
        self.keyboard_nav_enhanced.setToolTip("Improve keyboard navigation throughout the application")
        nav_layout.addWidget(self.keyboard_nav_enhanced)
        
        layout.addWidget(nav_group)
        
        # Motion and effects
        motion_group = QGroupBox("Motion and Effects")
        motion_layout = QVBoxLayout(motion_group)
        
        self.reduced_motion = QCheckBox("Reduce motion and animations")
        self.reduced_motion.setToolTip("Reduce or disable animations for users sensitive to motion")
        motion_layout.addWidget(self.reduced_motion)
        
        self.reduced_transparency = QCheckBox("Reduce transparency effects")
        self.reduced_transparency.setToolTip("Reduce transparency effects for better visibility")
        motion_layout.addWidget(self.reduced_transparency)
        
        layout.addWidget(motion_group)
        
        # Cursor enhancements
        cursor_group = QGroupBox("Cursor Enhancements")
        cursor_layout = QVBoxLayout(cursor_group)
        
        self.high_contrast_cursor = QCheckBox("High contrast cursor")
        self.high_contrast_cursor.setToolTip("Use high contrast cursor for better visibility")
        cursor_layout.addWidget(self.high_contrast_cursor)
        
        layout.addWidget(cursor_group)
        
        layout.addStretch()
        self.tab_widget.addTab(widget, "General")
    
    def create_contrast_tab(self):
        """Create high contrast settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # High contrast mode
        contrast_group = QGroupBox("High Contrast Mode")
        contrast_layout = QVBoxLayout(contrast_group)
        
        self.high_contrast_enabled = QCheckBox("Enable high contrast mode")
        self.high_contrast_enabled.setToolTip("Enable high contrast theme for better visibility")
        contrast_layout.addWidget(self.high_contrast_enabled)
        
        # Contrast level selection
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("Contrast level:"))
        
        self.contrast_level_combo = QComboBox()
        self.contrast_level_combo.addItem("Standard (WCAG AA - 4.5:1)", HighContrastLevel.STANDARD)
        self.contrast_level_combo.addItem("Enhanced (WCAG AAA - 7:1)", HighContrastLevel.ENHANCED)
        self.contrast_level_combo.addItem("Maximum (Pure B&W - 21:1)", HighContrastLevel.MAXIMUM)
        
        level_layout.addWidget(self.contrast_level_combo)
        level_layout.addStretch()
        contrast_layout.addLayout(level_layout)
        
        # High contrast preview
        preview_group = QGroupBox("High Contrast Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.contrast_preview = QLabel("Preview area")
        self.contrast_preview.setMinimumHeight(100)
        self.contrast_preview.setStyleSheet("border: 1px solid #ccc; padding: 10px;")
        self.contrast_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        preview_layout.addWidget(self.contrast_preview)
        
        # Preview buttons
        preview_button_layout = QHBoxLayout()
        
        self.preview_button = QPushButton("Preview High Contrast")
        self.preview_button.clicked.connect(self.preview_high_contrast)
        
        self.generate_button = QPushButton("Generate High Contrast Theme")
        self.generate_button.clicked.connect(self.generate_high_contrast_theme)
        
        preview_button_layout.addWidget(self.preview_button)
        preview_button_layout.addWidget(self.generate_button)
        preview_layout.addLayout(preview_button_layout)
        
        contrast_layout.addWidget(preview_group)
        layout.addWidget(contrast_group)
        
        layout.addStretch()
        self.tab_widget.addTab(widget, "High Contrast")
    
    def create_color_blindness_tab(self):
        """Create color blindness settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Color blindness filter
        filter_group = QGroupBox("Color Blindness Filter")
        filter_layout = QVBoxLayout(filter_group)
        
        filter_layout.addWidget(QLabel("Select color blindness simulation:"))
        
        self.color_blindness_combo = QComboBox()
        self.color_blindness_combo.addItem("None (Normal vision)", None)
        self.color_blindness_combo.addItem("Protanopia (Red-blind)", ColorBlindnessType.PROTANOPIA)
        self.color_blindness_combo.addItem("Deuteranopia (Green-blind)", ColorBlindnessType.DEUTERANOPIA)
        self.color_blindness_combo.addItem("Tritanopia (Blue-blind)", ColorBlindnessType.TRITANOPIA)
        self.color_blindness_combo.addItem("Protanomaly (Red-weak)", ColorBlindnessType.PROTANOMALY)
        self.color_blindness_combo.addItem("Deuteranomaly (Green-weak)", ColorBlindnessType.DEUTERANOMALY)
        self.color_blindness_combo.addItem("Tritanomaly (Blue-weak)", ColorBlindnessType.TRITANOMALY)
        self.color_blindness_combo.addItem("Achromatopsia (No color)", ColorBlindnessType.ACHROMATOPSIA)
        self.color_blindness_combo.addItem("Achromatomaly (Weak color)", ColorBlindnessType.ACHROMATOMALY)
        
        filter_layout.addWidget(self.color_blindness_combo)
        
        # Color blindness preview
        preview_group = QGroupBox("Color Blindness Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        # Color picker for testing
        color_picker_layout = QHBoxLayout()
        color_picker_layout.addWidget(QLabel("Test color:"))
        
        self.color_picker_button = QPushButton()
        self.color_picker_button.setFixedSize(50, 30)
        self.color_picker_button.setStyleSheet("background-color: #007bff; border: 1px solid #ccc;")
        self.color_picker_button.clicked.connect(self.pick_color)
        
        color_picker_layout.addWidget(self.color_picker_button)
        color_picker_layout.addStretch()
        preview_layout.addLayout(color_picker_layout)
        
        # Color blindness preview widget
        scroll_area = QScrollArea()
        self.color_blindness_preview = ColorBlindnessPreviewWidget()
        scroll_area.setWidget(self.color_blindness_preview)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(300)
        
        preview_layout.addWidget(scroll_area)
        filter_layout.addWidget(preview_group)
        
        layout.addWidget(filter_group)
        layout.addStretch()
        self.tab_widget.addTab(widget, "Color Blindness")
    
    def create_testing_tab(self):
        """Create accessibility testing tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Test configuration
        config_group = QGroupBox("Test Configuration")
        config_layout = QVBoxLayout(config_group)
        
        target_level_layout = QHBoxLayout()
        target_level_layout.addWidget(QLabel("Target compliance level:"))
        
        self.target_level_combo = QComboBox()
        self.target_level_combo.addItem("WCAG A", AccessibilityLevel.A)
        self.target_level_combo.addItem("WCAG AA", AccessibilityLevel.AA)
        self.target_level_combo.addItem("WCAG AAA", AccessibilityLevel.AAA)
        self.target_level_combo.setCurrentText("WCAG AA")
        
        target_level_layout.addWidget(self.target_level_combo)
        target_level_layout.addStretch()
        config_layout.addLayout(target_level_layout)
        
        # Test progress
        self.test_progress = QProgressBar()
        self.test_progress.setVisible(False)
        config_layout.addWidget(self.test_progress)
        
        layout.addWidget(config_group)
        
        # Test results
        results_group = QGroupBox("Test Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(200)
        results_layout.addWidget(self.results_text)
        
        layout.addWidget(results_group)
        
        # Recommendations
        recommendations_group = QGroupBox("Recommendations")
        recommendations_layout = QVBoxLayout(recommendations_group)
        
        self.recommendations_text = QTextEdit()
        self.recommendations_text.setReadOnly(True)
        self.recommendations_text.setMaximumHeight(150)
        recommendations_layout.addWidget(self.recommendations_text)
        
        layout.addWidget(recommendations_group)
        
        layout.addStretch()
        self.tab_widget.addTab(widget, "Testing")
    
    def create_advanced_tab(self):
        """Create advanced accessibility settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Custom settings
        custom_group = QGroupBox("Custom Accessibility Settings")
        custom_layout = QVBoxLayout(custom_group)
        
        # Custom contrast ratios
        contrast_layout = QHBoxLayout()
        contrast_layout.addWidget(QLabel("Custom contrast ratio:"))
        
        self.custom_contrast_spin = QSpinBox()
        self.custom_contrast_spin.setRange(1, 21)
        self.custom_contrast_spin.setValue(4)
        self.custom_contrast_spin.setSuffix(":1")
        
        contrast_layout.addWidget(self.custom_contrast_spin)
        contrast_layout.addStretch()
        custom_layout.addLayout(contrast_layout)
        
        # Import/Export settings
        import_export_layout = QHBoxLayout()
        
        self.import_button = QPushButton("Import Settings")
        self.import_button.clicked.connect(self.import_settings)
        
        self.export_button = QPushButton("Export Settings")
        self.export_button.clicked.connect(self.export_settings)
        
        import_export_layout.addWidget(self.import_button)
        import_export_layout.addWidget(self.export_button)
        import_export_layout.addStretch()
        custom_layout.addLayout(import_export_layout)
        
        layout.addWidget(custom_group)
        
        # Reset options
        reset_group = QGroupBox("Reset Options")
        reset_layout = QVBoxLayout(reset_group)
        
        self.reset_all_button = QPushButton("Reset All Accessibility Settings")
        self.reset_all_button.clicked.connect(self.reset_all_settings)
        
        self.reset_theme_button = QPushButton("Reset Theme to Default")
        self.reset_theme_button.clicked.connect(self.reset_theme)
        
        reset_layout.addWidget(self.reset_all_button)
        reset_layout.addWidget(self.reset_theme_button)
        
        layout.addWidget(reset_group)
        
        layout.addStretch()
        self.tab_widget.addTab(widget, "Advanced")
    
    def load_current_settings(self):
        """Load current accessibility settings into the UI."""
        settings = self.current_settings
        
        # General tab
        self.increased_font_sizes.setChecked(settings.increased_font_sizes)
        self.enhanced_focus.setChecked(settings.enhanced_focus_indicators)
        self.keyboard_nav_enhanced.setChecked(settings.keyboard_navigation_enhanced)
        self.reduced_motion.setChecked(settings.reduced_motion)
        self.reduced_transparency.setChecked(settings.reduced_transparency)
        self.high_contrast_cursor.setChecked(settings.high_contrast_cursor)
        
        # High contrast tab
        self.high_contrast_enabled.setChecked(settings.high_contrast_enabled)
        
        # Find and set contrast level
        for i in range(self.contrast_level_combo.count()):
            if self.contrast_level_combo.itemData(i) == settings.high_contrast_level:
                self.contrast_level_combo.setCurrentIndex(i)
                break
        
        # Color blindness tab
        for i in range(self.color_blindness_combo.count()):
            if self.color_blindness_combo.itemData(i) == settings.color_blindness_filter:
                self.color_blindness_combo.setCurrentIndex(i)
                break
    
    def get_current_settings(self) -> AccessibilitySettings:
        """Get current settings from UI."""
        return AccessibilitySettings(
            high_contrast_enabled=self.high_contrast_enabled.isChecked(),
            high_contrast_level=self.contrast_level_combo.currentData(),
            color_blindness_filter=self.color_blindness_combo.currentData(),
            increased_font_sizes=self.increased_font_sizes.isChecked(),
            enhanced_focus_indicators=self.enhanced_focus.isChecked(),
            reduced_motion=self.reduced_motion.isChecked(),
            reduced_transparency=self.reduced_transparency.isChecked(),
            high_contrast_cursor=self.high_contrast_cursor.isChecked(),
            keyboard_navigation_enhanced=self.keyboard_nav_enhanced.isChecked()
        )
    
    def apply_settings(self):
        """Apply current settings."""
        try:
            settings = self.get_current_settings()
            self.accessibility_manager.update_settings(settings)
            self.current_settings = settings
            self.settingsChanged.emit(settings)
            
            QMessageBox.information(self, "Settings Applied", 
                                  "Accessibility settings have been applied successfully.")
        except Exception as e:
            logger.error(f"Failed to apply accessibility settings: {e}")
            QMessageBox.critical(self, "Error", f"Failed to apply settings: {e}")
    
    def reset_settings(self):
        """Reset settings to defaults."""
        self.current_settings = AccessibilitySettings()
        self.load_current_settings()
    
    def reset_all_settings(self):
        """Reset all accessibility settings to defaults."""
        reply = QMessageBox.question(self, "Reset All Settings",
                                   "Are you sure you want to reset all accessibility settings to defaults?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.reset_settings()
            self.apply_settings()
    
    def reset_theme(self):
        """Reset theme to default."""
        reply = QMessageBox.question(self, "Reset Theme",
                                   "Are you sure you want to reset the theme to default?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # Reset to default theme
            default_theme = self.theme_engine.get_default_theme()
            if default_theme:
                self.theme_engine.apply_theme(default_theme)
    
    def preview_high_contrast(self):
        """Preview high contrast mode."""
        if not self.current_theme:
            return
        
        try:
            level = self.contrast_level_combo.currentData()
            hc_theme = HighContrastGenerator.generate_high_contrast_theme(self.current_theme, level)
            
            # Update preview
            palette = hc_theme.get_color_palette()
            bg_color = palette.get_color_value('background', '#ffffff')
            text_color = palette.get_color_value('text_primary', '#000000')
            
            self.contrast_preview.setStyleSheet(
                f"background-color: {bg_color}; color: {text_color}; "
                f"border: 1px solid {text_color}; padding: 10px;"
            )
            self.contrast_preview.setText(f"High Contrast Preview\n{level.value.upper()}")
            
        except Exception as e:
            logger.error(f"Failed to preview high contrast: {e}")
            QMessageBox.warning(self, "Preview Error", f"Failed to generate preview: {e}")
    
    def generate_high_contrast_theme(self):
        """Generate and apply high contrast theme."""
        if not self.current_theme:
            return
        
        try:
            level = self.contrast_level_combo.currentData()
            hc_theme = HighContrastGenerator.generate_high_contrast_theme(self.current_theme, level)
            
            # Apply the high contrast theme
            self.theme_engine.apply_theme(hc_theme)
            
            QMessageBox.information(self, "High Contrast Theme Generated",
                                  f"High contrast theme ({level.value}) has been generated and applied.")
            
        except Exception as e:
            logger.error(f"Failed to generate high contrast theme: {e}")
            QMessageBox.critical(self, "Error", f"Failed to generate high contrast theme: {e}")
    
    def pick_color(self):
        """Pick a color for testing."""
        color = QColorDialog.getColor(QColor("#007bff"), self)
        if color.isValid():
            hex_color = color.name()
            self.color_picker_button.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #ccc;")
            self.color_blindness_preview.update_color(hex_color)
    
    def run_accessibility_test(self):
        """Run comprehensive accessibility test."""
        if not self.current_theme:
            QMessageBox.warning(self, "No Theme", "No theme is currently loaded.")
            return
        
        try:
            # Disable test button during test
            self.test_button.setEnabled(False)
            self.test_progress.setVisible(True)
            self.test_progress.setValue(0)
            
            # Get target level
            target_level = self.target_level_combo.currentData()
            
            # Create and setup worker
            self.test_worker = AccessibilityTestWorker(self.current_theme, target_level)
            self.test_thread = QThread()
            self.test_worker.moveToThread(self.test_thread)
            
            # Connect signals
            self.test_worker.testCompleted.connect(self.on_test_completed)
            self.test_worker.testProgress.connect(self.on_test_progress)
            self.test_worker.testError.connect(self.on_test_error)
            self.test_thread.started.connect(self.test_worker.run_test)
            
            # Start test
            self.test_thread.start()
            
        except Exception as e:
            logger.error(f"Failed to start accessibility test: {e}")
            QMessageBox.critical(self, "Test Error", f"Failed to start test: {e}")
            self.test_button.setEnabled(True)
            self.test_progress.setVisible(False)
    
    def on_test_completed(self, report: AccessibilityReport):
        """Handle test completion."""
        self.test_button.setEnabled(True)
        self.test_progress.setVisible(False)
        
        # Display results
        results_text = f"Theme: {report.theme_name}\n"
        results_text += f"Overall Compliance: {report.overall_compliance.value.upper()}\n"
        results_text += f"Color Blind Friendly: {'Yes' if report.color_blind_friendly else 'No'}\n"
        results_text += f"High Contrast Available: {'Yes' if report.high_contrast_available else 'No'}\n\n"
        
        if report.issues:
            results_text += "Issues:\n"
            for issue in report.issues:
                results_text += f"• {issue}\n"
        
        if report.warnings:
            results_text += "\nWarnings:\n"
            for warning in report.warnings:
                results_text += f"• {warning}\n"
        
        self.results_text.setText(results_text)
        
        # Display recommendations
        recommendations_text = "\n".join(f"• {rec}" for rec in report.recommendations)
        self.recommendations_text.setText(recommendations_text)
        
        # Cleanup
        self.test_thread.quit()
        self.test_thread.wait()
        self.test_worker = None
        self.test_thread = None
    
    def on_test_progress(self, message: str, percentage: int):
        """Handle test progress updates."""
        self.test_progress.setValue(percentage)
        # Could also update a status label with the message
    
    def on_test_error(self, error_message: str):
        """Handle test errors."""
        self.test_button.setEnabled(True)
        self.test_progress.setVisible(False)
        
        QMessageBox.critical(self, "Test Error", f"Accessibility test failed: {error_message}")
        
        # Cleanup
        if self.test_thread:
            self.test_thread.quit()
            self.test_thread.wait()
            self.test_worker = None
            self.test_thread = None
    
    def import_settings(self):
        """Import accessibility settings from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import Accessibility Settings", "", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                # Create settings from data
                settings = AccessibilitySettings(**data)
                self.current_settings = settings
                self.load_current_settings()
                
                QMessageBox.information(self, "Import Successful",
                                      "Accessibility settings have been imported successfully.")
                
            except Exception as e:
                logger.error(f"Failed to import settings: {e}")
                QMessageBox.critical(self, "Import Error", f"Failed to import settings: {e}")
    
    def export_settings(self):
        """Export accessibility settings to file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Accessibility Settings", "accessibility_settings.json", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                settings = self.get_current_settings()
                data = {
                    'high_contrast_enabled': settings.high_contrast_enabled,
                    'high_contrast_level': settings.high_contrast_level.value,
                    'color_blindness_filter': settings.color_blindness_filter.value if settings.color_blindness_filter else None,
                    'increased_font_sizes': settings.increased_font_sizes,
                    'enhanced_focus_indicators': settings.enhanced_focus_indicators,
                    'reduced_motion': settings.reduced_motion,
                    'reduced_transparency': settings.reduced_transparency,
                    'high_contrast_cursor': settings.high_contrast_cursor,
                    'keyboard_navigation_enhanced': settings.keyboard_navigation_enhanced
                }
                
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2)
                
                QMessageBox.information(self, "Export Successful",
                                      "Accessibility settings have been exported successfully.")
                
            except Exception as e:
                logger.error(f"Failed to export settings: {e}")
                QMessageBox.critical(self, "Export Error", f"Failed to export settings: {e}")
    
    def on_settings_changed(self, settings: AccessibilitySettings):
        """Handle settings changes from accessibility manager."""
        self.current_settings = settings
        self.load_current_settings()
    
    def on_high_contrast_toggled(self, enabled: bool):
        """Handle high contrast mode toggle."""
        self.high_contrast_enabled.setChecked(enabled)
    
    def on_color_blindness_filter_changed(self, filter_type):
        """Handle color blindness filter changes."""
        for i in range(self.color_blindness_combo.count()):
            if self.color_blindness_combo.itemData(i) == filter_type:
                self.color_blindness_combo.setCurrentIndex(i)
                break
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        # Cleanup test thread if running
        if self.test_thread and self.test_thread.isRunning():
            self.test_thread.quit()
            self.test_thread.wait()
        
        super().closeEvent(event)