"""Theme Customizer Dialog for creating and editing themes.

Provides a comprehensive interface for users to create custom themes,
modify existing themes, and preview changes in real-time.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QScrollArea, QWidget, QGroupBox, QComboBox, QLineEdit, QCheckBox,
    QFrame, QSplitter, QTextEdit, QTabWidget, QListWidget, QListWidgetItem,
    QSizePolicy, QApplication, QMessageBox, QSlider, QSpinBox, QColorDialog,
    QFontComboBox, QDoubleSpinBox, QProgressBar, QStackedWidget, QTreeWidget,
    QTreeWidgetItem, QToolButton, QMenu, QAction, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QThread, pyqtSlot, QPropertyAnimation
from PyQt6.QtGui import (
    QPixmap, QPainter, QFont, QIcon, QColor, QPalette, QBrush, QPen,
    QLinearGradient, QGradient, QFontMetrics
)

from ..themes.base import Theme, ThemeMetadata, ColorPalette, Typography
from ..themes.customization import (
    ThemeBuilder, ThemeCustomizer, ThemeExporter, CustomThemeConfig,
    ThemeTemplate, ThemeExportSettings, ExportFormat, ColorSchemePreset,
    BUILTIN_COLOR_SCHEMES
)
from ..themes.validation import ThemeValidator, ValidationLevel, ValidationResult
from ..themes.types import ThemeType, AccessibilityLevel
from ..themes.accessibility import AccessibilityManager
from .base import BaseDialog
from .theme_selector_dialog import ThemePreviewWidget

logger = logging.getLogger(__name__)


class ColorPickerWidget(QWidget):
    """Custom color picker widget with hex input and preview."""
    
    color_changed = pyqtSignal(str)  # hex color
    
    def __init__(self, initial_color: str = "#FFFFFF", parent=None):
        super().__init__(parent)
        self.current_color = QColor(initial_color)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the color picker UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Color preview button
        self.color_button = QPushButton()
        self.color_button.setFixedSize(40, 30)
        self.color_button.clicked.connect(self._show_color_dialog)
        layout.addWidget(self.color_button)
        
        # Hex input
        self.hex_input = QLineEdit()
        self.hex_input.setPlaceholderText("#FFFFFF")
        self.hex_input.setMaxLength(7)
        self.hex_input.textChanged.connect(self._on_hex_changed)
        layout.addWidget(self.hex_input)
        
        self.update_display()
    
    def update_display(self):
        """Update the color preview and hex input."""
        # Update button background
        self.color_button.setStyleSheet(
            f"QPushButton {{ background-color: {self.current_color.name()}; "
            f"border: 1px solid #ccc; }}"
        )
        
        # Update hex input
        self.hex_input.blockSignals(True)
        self.hex_input.setText(self.current_color.name())
        self.hex_input.blockSignals(False)
    
    def _show_color_dialog(self):
        """Show color selection dialog."""
        color = QColorDialog.getColor(self.current_color, self, "Select Color")
        if color.isValid():
            self.set_color(color.name())
    
    def _on_hex_changed(self, text: str):
        """Handle hex input changes."""
        if text.startswith('#') and len(text) == 7:
            try:
                color = QColor(text)
                if color.isValid():
                    self.current_color = color
                    self.update_display()
                    self.color_changed.emit(text)
            except Exception:
                pass
    
    def set_color(self, hex_color: str):
        """Set the current color."""
        color = QColor(hex_color)
        if color.isValid():
            self.current_color = color
            self.update_display()
            self.color_changed.emit(hex_color)
    
    def get_color(self) -> str:
        """Get the current color as hex string."""
        return self.current_color.name()


class TypographyWidget(QWidget):
    """Widget for editing typography settings."""
    
    typography_changed = pyqtSignal(str, dict)  # name, definition
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the typography UI."""
        layout = QGridLayout(self)
        
        # Font family
        layout.addWidget(QLabel("Font Family:"), 0, 0)
        self.font_combo = QFontComboBox()
        self.font_combo.currentFontChanged.connect(self._on_font_changed)
        layout.addWidget(self.font_combo, 0, 1)
        
        # Font size
        layout.addWidget(QLabel("Size:"), 1, 0)
        self.size_spinbox = QSpinBox()
        self.size_spinbox.setRange(8, 72)
        self.size_spinbox.setValue(12)
        self.size_spinbox.valueChanged.connect(self._on_font_changed)
        layout.addWidget(self.size_spinbox, 1, 1)
        
        # Font weight
        layout.addWidget(QLabel("Weight:"), 2, 0)
        self.weight_combo = QComboBox()
        self.weight_combo.addItems([
            "100 - Thin", "200 - Extra Light", "300 - Light", 
            "400 - Normal", "500 - Medium", "600 - Semi Bold",
            "700 - Bold", "800 - Extra Bold", "900 - Black"
        ])
        self.weight_combo.setCurrentText("400 - Normal")
        self.weight_combo.currentTextChanged.connect(self._on_font_changed)
        layout.addWidget(self.weight_combo, 2, 1)
        
        # Line height
        layout.addWidget(QLabel("Line Height:"), 3, 0)
        self.line_height_spinbox = QDoubleSpinBox()
        self.line_height_spinbox.setRange(0.8, 3.0)
        self.line_height_spinbox.setSingleStep(0.1)
        self.line_height_spinbox.setValue(1.4)
        self.line_height_spinbox.valueChanged.connect(self._on_font_changed)
        layout.addWidget(self.line_height_spinbox, 3, 1)
        
        # Preview
        self.preview_label = QLabel("The quick brown fox jumps over the lazy dog")
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("border: 1px solid #ccc; padding: 10px;")
        layout.addWidget(self.preview_label, 4, 0, 1, 2)
        
        self._update_preview()
    
    def _on_font_changed(self):
        """Handle font changes."""
        self._update_preview()
        
        definition = self.get_typography_definition()
        self.typography_changed.emit("preview", definition)
    
    def _update_preview(self):
        """Update the font preview."""
        font = QFont()
        font.setFamily(self.font_combo.currentFont().family())
        font.setPointSize(self.size_spinbox.value())
        
        # Extract weight from combo text
        weight_text = self.weight_combo.currentText()
        weight = int(weight_text.split(" - ")[0])
        font.setWeight(QFont.Weight(weight))
        
        self.preview_label.setFont(font)
        
        # Apply line height via stylesheet
        line_height = self.line_height_spinbox.value()
        self.preview_label.setStyleSheet(
            f"border: 1px solid #ccc; padding: 10px; line-height: {line_height};"
        )
    
    def get_typography_definition(self) -> dict:
        """Get the current typography definition."""
        weight_text = self.weight_combo.currentText()
        weight = int(weight_text.split(" - ")[0])
        
        return {
            'font_family': self.font_combo.currentFont().family(),
            'font_size': self.size_spinbox.value(),
            'font_weight': weight,
            'line_height': self.line_height_spinbox.value()
        }
    
    def set_typography_definition(self, definition: dict):
        """Set the typography definition."""
        if 'font_family' in definition:
            font = QFont(definition['font_family'])
            self.font_combo.setCurrentFont(font)
        
        if 'font_size' in definition:
            self.size_spinbox.setValue(definition['font_size'])
        
        if 'font_weight' in definition:
            weight = definition['font_weight']
            for i in range(self.weight_combo.count()):
                text = self.weight_combo.itemText(i)
                if text.startswith(str(weight)):
                    self.weight_combo.setCurrentIndex(i)
                    break
        
        if 'line_height' in definition:
            self.line_height_spinbox.setValue(definition['line_height'])
        
        self._update_preview()


class ValidationWidget(QWidget):
    """Widget for displaying theme validation results."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the validation UI."""
        layout = QVBoxLayout(self)
        
        # Validation status
        self.status_label = QLabel("Theme validation status will appear here")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Progress bar for validation score
        score_layout = QHBoxLayout()
        score_layout.addWidget(QLabel("Validation Score:"))
        self.score_progress = QProgressBar()
        self.score_progress.setRange(0, 100)
        score_layout.addWidget(self.score_progress)
        self.score_label = QLabel("0%")
        score_layout.addWidget(self.score_label)
        layout.addLayout(score_layout)
        
        # Issues list
        issues_group = QGroupBox("Validation Issues")
        issues_layout = QVBoxLayout(issues_group)
        
        self.issues_list = QListWidget()
        self.issues_list.setMaximumHeight(150)
        issues_layout.addWidget(self.issues_list)
        
        layout.addWidget(issues_group)
        
        # Auto-fix button
        self.auto_fix_btn = QPushButton("Auto-Fix Issues")
        self.auto_fix_btn.setEnabled(False)
        layout.addWidget(self.auto_fix_btn)
    
    def update_validation_result(self, result: ValidationResult):
        """Update display with validation result."""
        # Update status
        if result.is_valid:
            self.status_label.setText("✅ Theme validation passed")
            self.status_label.setStyleSheet("color: green;")
        else:
            self.status_label.setText(f"❌ Theme validation failed ({result.error_count} errors)")
            self.status_label.setStyleSheet("color: red;")
        
        # Update score
        score = int(result.score)
        self.score_progress.setValue(score)
        self.score_label.setText(f"{score}%")
        
        # Update issues list
        self.issues_list.clear()
        for issue in result.issues:
            item_text = f"{issue.severity.upper()}: {issue.message}"
            if hasattr(issue, 'location') and issue.location:
                item_text += f" (at {issue.location})"
            
            item = QListWidgetItem(item_text)
            
            # Color-code by severity
            if issue.severity == "error":
                item.setForeground(QColor("red"))
            elif issue.severity == "warning":
                item.setForeground(QColor("orange"))
            else:
                item.setForeground(QColor("blue"))
            
            self.issues_list.addItem(item)
        
        # Enable auto-fix if there are fixable issues
        self.auto_fix_btn.setEnabled(result.error_count > 0)


class ThemeCustomizerDialog(BaseDialog):
    """Dialog for customizing and creating themes."""
    
    theme_created = pyqtSignal(object)  # New theme
    theme_updated = pyqtSignal(object)  # Updated theme
    
    def __init__(self, 
                 base_theme: Optional[Theme] = None,
                 theme_config: Optional[CustomThemeConfig] = None,
                 parent=None):
        """Initialize theme customizer dialog.
        
        Args:
            base_theme: Base theme to customize (None for new theme)
            theme_config: Custom theme configuration
            parent: Parent widget
        """
        self.base_theme = base_theme
        self.theme_config = theme_config or self._create_default_config()
        self.theme_builder: Optional[ThemeBuilder] = None
        self.theme_customizer: Optional[ThemeCustomizer] = None
        self.current_theme: Optional[Theme] = None
        
        super().__init__(parent)
        
        self.setWindowTitle("Theme Customizer" if base_theme else "Create New Theme")
        self.setModal(True)
        self.resize(1200, 800)
        
        self.initialize_customization()
    
    def _create_default_config(self) -> CustomThemeConfig:
        """Create default theme configuration."""
        return CustomThemeConfig(
            name="New Custom Theme",
            description="A custom theme created with the theme customizer",
            author="User",
            category=ThemeType.LIGHT,
            base_template=ThemeTemplate.LIGHT_MODERN,
            accessibility_target=AccessibilityLevel.AA
        )
    
    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QHBoxLayout(self)
        
        # Left panel - controls
        left_panel = self.create_controls_panel()
        layout.addWidget(left_panel)
        
        # Right panel - preview
        right_panel = self.create_preview_panel()
        layout.addWidget(right_panel)
        
        # Set splitter sizes
        layout.setStretch(0, 1)  # Controls panel
        layout.setStretch(1, 1)  # Preview panel
    
    def create_controls_panel(self) -> QWidget:
        """Create the controls panel."""
        panel = QWidget()
        panel.setMaximumWidth(500)
        layout = QVBoxLayout(panel)
        
        # Theme configuration
        config_group = QGroupBox("Theme Configuration")
        config_layout = QGridLayout(config_group)
        
        # Name
        config_layout.addWidget(QLabel("Name:"), 0, 0)
        self.name_input = QLineEdit(self.theme_config.name)
        self.name_input.textChanged.connect(self._on_config_changed)
        config_layout.addWidget(self.name_input, 0, 1)
        
        # Description
        config_layout.addWidget(QLabel("Description:"), 1, 0)
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(60)
        self.description_input.setPlainText(self.theme_config.description or "")
        self.description_input.textChanged.connect(self._on_config_changed)
        config_layout.addWidget(self.description_input, 1, 1)
        
        # Author
        config_layout.addWidget(QLabel("Author:"), 2, 0)
        self.author_input = QLineEdit(self.theme_config.author or "")
        self.author_input.textChanged.connect(self._on_config_changed)
        config_layout.addWidget(self.author_input, 2, 1)
        
        # Category
        config_layout.addWidget(QLabel("Category:"), 3, 0)
        self.category_combo = QComboBox()
        for theme_type in ThemeType:
            self.category_combo.addItem(theme_type.value.title(), theme_type)
        
        # Set current category
        for i in range(self.category_combo.count()):
            if self.category_combo.itemData(i) == self.theme_config.category:
                self.category_combo.setCurrentIndex(i)
                break
        
        self.category_combo.currentIndexChanged.connect(self._on_config_changed)
        config_layout.addWidget(self.category_combo, 3, 1)
        
        layout.addWidget(config_group)
        
        # Customization tabs
        self.tabs = QTabWidget()
        
        # Colors tab
        self.colors_widget = self.create_colors_tab()
        self.tabs.addTab(self.colors_widget, "Colors")
        
        # Typography tab
        self.typography_widget = self.create_typography_tab()
        self.tabs.addTab(self.typography_widget, "Typography")
        
        # Color schemes tab
        self.schemes_widget = self.create_schemes_tab()
        self.tabs.addTab(self.schemes_widget, "Color Schemes")
        
        # Validation tab
        self.validation_widget = ValidationWidget()
        self.validation_widget.auto_fix_btn.clicked.connect(self._on_auto_fix)
        self.tabs.addTab(self.validation_widget, "Validation")
        
        layout.addWidget(self.tabs)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self._on_reset)
        button_layout.addWidget(self.reset_btn)
        
        self.validate_btn = QPushButton("Validate")
        self.validate_btn.clicked.connect(self._on_validate)
        button_layout.addWidget(self.validate_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save Theme")
        self.save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        
        return panel
    
    def create_colors_tab(self) -> QWidget:
        """Create the colors customization tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Color list with editors
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        self.colors_layout = QVBoxLayout(scroll_widget)
        
        # Common colors
        common_colors = [
            ("Primary", "primary"),
            ("Secondary", "secondary"), 
            ("Accent", "accent"),
            ("Background", "background"),
            ("Surface", "surface"),
            ("Text Primary", "text_primary"),
            ("Text Secondary", "text_secondary"),
            ("Border", "border"),
            ("Success", "success"),
            ("Warning", "warning"),
            ("Error", "error"),
            ("Info", "info")
        ]
        
        self.color_pickers: Dict[str, ColorPickerWidget] = {}
        
        for display_name, color_key in common_colors:
            color_group = QGroupBox(display_name)
            color_layout = QHBoxLayout(color_group)
            
            picker = ColorPickerWidget()
            picker.color_changed.connect(
                lambda color, key=color_key: self._on_color_changed(key, color)
            )
            self.color_pickers[color_key] = picker
            color_layout.addWidget(picker)
            
            self.colors_layout.addWidget(color_group)
        
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        return widget
    
    def create_typography_tab(self) -> QWidget:
        """Create the typography customization tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Typography presets
        presets_group = QGroupBox("Typography Elements")
        presets_layout = QVBoxLayout(presets_group)
        
        # Typography elements
        typography_elements = [
            ("Default Text", "default"),
            ("Headings", "heading"),
            ("Captions", "caption"),
            ("Code", "code")
        ]
        
        self.typography_widgets: Dict[str, TypographyWidget] = {}
        
        for display_name, typo_key in typography_elements:
            element_group = QGroupBox(display_name)
            element_layout = QVBoxLayout(element_group)
            
            typo_widget = TypographyWidget()
            typo_widget.typography_changed.connect(
                lambda name, definition, key=typo_key: self._on_typography_changed(key, definition)
            )
            self.typography_widgets[typo_key] = typo_widget
            element_layout.addWidget(typo_widget)
            
            presets_layout.addWidget(element_group)
        
        scroll_area = QScrollArea()
        scroll_area.setWidget(presets_group)
        layout.addWidget(scroll_area)
        
        return widget
    
    def create_schemes_tab(self) -> QWidget:
        """Create the color schemes tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Built-in color schemes
        schemes_group = QGroupBox("Built-in Color Schemes")
        schemes_layout = QVBoxLayout(schemes_group)
        
        schemes_list = QListWidget()
        schemes_list.setMaximumHeight(200)
        
        for scheme in BUILTIN_COLOR_SCHEMES:
            item = QListWidgetItem(f"{scheme.name} - {scheme.description}")
            item.setData(Qt.ItemDataRole.UserRole, scheme)
            schemes_list.addItem(item)
        
        schemes_list.itemDoubleClicked.connect(self._on_scheme_selected)
        schemes_layout.addWidget(schemes_list)
        
        apply_scheme_btn = QPushButton("Apply Selected Scheme")
        apply_scheme_btn.clicked.connect(
            lambda: self._on_scheme_selected(schemes_list.currentItem())
        )
        schemes_layout.addWidget(apply_scheme_btn)
        
        layout.addWidget(schemes_group)
        
        # Accessibility optimization
        accessibility_group = QGroupBox("Accessibility Optimization")
        accessibility_layout = QVBoxLayout(accessibility_group)
        
        auto_optimize_btn = QPushButton("Auto-Optimize for Accessibility")
        auto_optimize_btn.clicked.connect(self._on_auto_optimize)
        accessibility_layout.addWidget(auto_optimize_btn)
        
        generate_variants_btn = QPushButton("Generate Color Variants")
        generate_variants_btn.clicked.connect(self._on_generate_variants)
        accessibility_layout.addWidget(generate_variants_btn)
        
        layout.addWidget(accessibility_group)
        
        layout.addStretch()
        
        return widget
    
    def create_preview_panel(self) -> QWidget:
        """Create the preview panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Preview header
        header = QLabel("Live Preview")
        header.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Preview widget
        self.preview_widget = ThemePreviewWidget()
        layout.addWidget(self.preview_widget)
        
        return panel
    
    def initialize_customization(self):
        """Initialize the theme customization."""
        try:
            # Create theme builder
            self.theme_builder = ThemeBuilder(self.theme_config)
            
            # Create theme customizer
            self.theme_customizer = ThemeCustomizer()
            self.theme_customizer.start_customization(self.theme_config)
            
            # Load initial theme data
            self._load_theme_data()
            
            # Update preview
            self._update_preview()
            
        except Exception as e:
            logger.error(f"Failed to initialize customization: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to initialize theme customization: {str(e)}"
            )
    
    def _load_theme_data(self):
        """Load theme data into UI controls."""
        if not self.theme_builder:
            return
        
        theme_data = self.theme_builder.get_theme_data()
        
        # Load colors
        colors = theme_data.get('colors', {})
        for color_key, picker in self.color_pickers.items():
            if color_key in colors:
                color_value = colors[color_key]
                if isinstance(color_value, dict):
                    color_value = color_value.get('value', '#FFFFFF')
                picker.set_color(color_value)
        
        # Load typography
        typography = theme_data.get('typography', {})
        for typo_key, widget in self.typography_widgets.items():
            if typo_key in typography:
                widget.set_typography_definition(typography[typo_key])
    
    def _on_config_changed(self):
        """Handle configuration changes."""
        if not self.theme_builder:
            return
        
        # Update configuration
        self.theme_config.name = self.name_input.text()
        self.theme_config.description = self.description_input.toPlainText()
        self.theme_config.author = self.author_input.text()
        self.theme_config.category = self.category_combo.currentData()
        
        # Update theme builder with new config
        self.theme_builder = ThemeBuilder(self.theme_config)
        self._load_theme_data()
        self._update_preview()
    
    def _on_color_changed(self, color_key: str, color_value: str):
        """Handle color changes."""
        if self.theme_builder:
            self.theme_builder.set_color(color_key, color_value)
            self._update_preview()
    
    def _on_typography_changed(self, typo_key: str, definition: dict):
        """Handle typography changes."""
        if self.theme_builder:
            self.theme_builder.set_typography(
                typo_key,
                definition['font_family'],
                definition['font_size'],
                definition['font_weight'],
                definition['line_height']
            )
            self._update_preview()
    
    def _on_scheme_selected(self, item: QListWidgetItem):
        """Handle color scheme selection."""
        if not item or not self.theme_builder:
            return
        
        scheme = item.data(Qt.ItemDataRole.UserRole)
        if scheme:
            self.theme_builder.apply_color_scheme_preset(scheme)
            self._load_theme_data()
            self._update_preview()
    
    def _on_auto_optimize(self):
        """Handle auto-optimization for accessibility."""
        if self.theme_builder:
            self.theme_builder.optimize_for_accessibility()
            self._load_theme_data()
            self._update_preview()
    
    def _on_generate_variants(self):
        """Handle color variant generation."""
        if self.theme_builder:
            self.theme_builder.auto_generate_variants()
            self._load_theme_data()
            self._update_preview()
    
    def _on_validate(self):
        """Handle theme validation."""
        if not self.theme_builder:
            return
        
        try:
            issues = self.theme_builder.validate_theme()
            
            # Create validation result
            from ..themes.validation import ValidationResult
            result = ValidationResult(
                is_valid=len(issues) == 0,
                issues=issues,
                error_count=len([i for i in issues if getattr(i, 'severity', 'error') == 'error']),
                warning_count=len([i for i in issues if getattr(i, 'severity', 'warning') == 'warning']),
                score=max(0, 100 - len(issues) * 10)  # Simple scoring
            )
            
            self.validation_widget.update_validation_result(result)
            
            # Switch to validation tab
            self.tabs.setCurrentWidget(self.validation_widget)
            
        except Exception as e:
            logger.error(f"Theme validation failed: {e}")
            QMessageBox.warning(
                self,
                "Validation Error",
                f"Theme validation failed: {str(e)}"
            )
    
    def _on_auto_fix(self):
        """Handle auto-fix of validation issues."""
        if self.theme_builder:
            # Perform auto-fixes
            self.theme_builder.optimize_for_accessibility()
            self._load_theme_data()
            self._update_preview()
            
            # Re-validate
            self._on_validate()
    
    def _on_reset(self):
        """Handle reset to original theme."""
        reply = QMessageBox.question(
            self,
            "Reset Theme",
            "Are you sure you want to reset all changes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.initialize_customization()
    
    def _on_save(self):
        """Handle saving the customized theme."""
        if not self.theme_builder:
            return
        
        try:
            # Validate theme before saving
            issues = self.theme_builder.validate_theme()
            if issues:
                reply = QMessageBox.question(
                    self,
                    "Validation Issues",
                    f"Theme has {len(issues)} validation issues. Save anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply != QMessageBox.StandardButton.Yes:
                    return
            
            # Build final theme
            theme = self.theme_builder.build_theme()
            
            if theme:
                if self.base_theme:
                    self.theme_updated.emit(theme)
                else:
                    self.theme_created.emit(theme)
                
                self.accept()
            else:
                QMessageBox.warning(
                    self,
                    "Save Error",
                    "Failed to build theme. Please check validation issues."
                )
                
        except Exception as e:
            logger.error(f"Failed to save theme: {e}")
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save theme: {str(e)}"
            )
    
    def _update_preview(self):
        """Update the live preview."""
        if self.theme_builder:
            try:
                theme = self.theme_builder.build_theme()
                self.preview_widget.set_theme(theme)
                self.current_theme = theme
            except Exception as e:
                logger.warning(f"Failed to update preview: {e}")


# Convenience function for showing theme customizer
def show_theme_customizer(base_theme: Optional[Theme] = None,
                         theme_config: Optional[CustomThemeConfig] = None,
                         parent=None) -> Optional[Theme]:
    """Show theme customizer dialog and return created/modified theme.
    
    Args:
        base_theme: Base theme to customize
        theme_config: Custom theme configuration
        parent: Parent widget
        
    Returns:
        Created or modified theme, or None if cancelled
    """
    dialog = ThemeCustomizerDialog(base_theme, theme_config, parent)
    
    result_theme = None
    
    def on_theme_created(theme):
        nonlocal result_theme
        result_theme = theme
    
    def on_theme_updated(theme):
        nonlocal result_theme
        result_theme = theme
    
    dialog.theme_created.connect(on_theme_created)
    dialog.theme_updated.connect(on_theme_updated)
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return result_theme
    
    return None