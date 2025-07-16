"""
Validation UI Components for Merge/Split Operations.

This module provides comprehensive validation warning displays and
accessibility features for the merge/split operation dialogs.
"""

from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
    QGroupBox, QPushButton, QListWidget, QListWidgetItem, QTextEdit,
    QProgressBar, QMessageBox, QToolTip
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap, QPainter


class ValidationWarningItem(QWidget):
    """Individual validation warning item with severity indication."""
    
    warning_dismissed = pyqtSignal(str)  # warning_id
    warning_details_requested = pyqtSignal(str)  # warning_id
    
    def __init__(self, warning_id: str, message: str, severity: str = "warning", parent=None):
        super().__init__(parent)
        self.warning_id = warning_id
        self.message = message
        self.severity = severity
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the warning item UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        
        # Severity icon
        icon_label = QLabel()
        icon_label.setFixedSize(20, 20)
        
        if self.severity == "error":
            icon_label.setText("❌")
            icon_label.setStyleSheet("color: #f44336; font-size: 14px;")
        elif self.severity == "warning":
            icon_label.setText("⚠️")
            icon_label.setStyleSheet("color: #ff9800; font-size: 14px;")
        elif self.severity == "info":
            icon_label.setText("ℹ️")
            icon_label.setStyleSheet("color: #2196f3; font-size: 14px;")
        else:
            icon_label.setText("•")
            icon_label.setStyleSheet("color: #666666; font-size: 14px;")
        
        layout.addWidget(icon_label)
        
        # Message
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("color: #333333; padding: 2px 8px;")
        layout.addWidget(message_label, 1)
        
        # Details button (if needed)
        if len(self.message) > 100:  # Show details for long messages
            details_button = QPushButton("Details")
            details_button.setMaximumWidth(60)
            details_button.clicked.connect(lambda: self.warning_details_requested.emit(self.warning_id))
            layout.addWidget(details_button)
        
        # Dismiss button
        dismiss_button = QPushButton("×")
        dismiss_button.setMaximumSize(20, 20)
        dismiss_button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
                color: #666666;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-radius: 10px;
            }
        """)
        dismiss_button.clicked.connect(lambda: self.warning_dismissed.emit(self.warning_id))
        layout.addWidget(dismiss_button)
        
        # Set background color based on severity
        if self.severity == "error":
            self.setStyleSheet("background-color: #ffebee; border-left: 4px solid #f44336; border-radius: 4px;")
        elif self.severity == "warning":
            self.setStyleSheet("background-color: #fff3e0; border-left: 4px solid #ff9800; border-radius: 4px;")
        elif self.severity == "info":
            self.setStyleSheet("background-color: #e3f2fd; border-left: 4px solid #2196f3; border-radius: 4px;")
        else:
            self.setStyleSheet("background-color: #f5f5f5; border-left: 4px solid #666666; border-radius: 4px;")


class AccessibilityHelper(QWidget):
    """Helper widget for accessibility features."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up accessibility helper UI."""
        layout = QVBoxLayout(self)
        
        # Accessibility info
        info_group = QGroupBox("Accessibility Features")
        info_layout = QVBoxLayout(info_group)
        
        # Keyboard shortcuts
        shortcuts_label = QLabel(
            "Keyboard Shortcuts:\n"
            "• Tab/Shift+Tab: Navigate between elements\n"
            "• Enter/Space: Activate buttons\n" 
            "• Ctrl+A: Select all elements\n"
            "• Escape: Cancel operation\n"
            "• F1: Show help"
        )
        shortcuts_label.setFont(QFont("Consolas", 9))
        shortcuts_label.setStyleSheet("color: #666666; padding: 8px; background-color: #f9f9f9; border-radius: 4px;")
        info_layout.addWidget(shortcuts_label)
        
        # Screen reader info
        screen_reader_label = QLabel(
            "This dialog supports screen readers with proper ARIA labels and role descriptions."
        )
        screen_reader_label.setWordWrap(True)
        screen_reader_label.setStyleSheet("color: #666666; font-style: italic; padding: 4px;")
        info_layout.addWidget(screen_reader_label)
        
        layout.addWidget(info_group)
    
    def announce_to_screen_reader(self, message: str):
        """Announce message to screen readers."""
        # This would integrate with platform-specific screen reader APIs
        # For now, we use QToolTip as a simple announcement mechanism
        QToolTip.showText(self.mapToGlobal(self.rect().center()), message, self, self.rect(), 2000)


class ProgressIndicator(QWidget):
    """Progress indicator for long-running operations."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._timer = QTimer()
        self._timer.timeout.connect(self.update_progress)
    
    def setup_ui(self):
        """Set up progress indicator UI."""
        layout = QVBoxLayout(self)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #666666; font-size: 10px;")
        layout.addWidget(self.status_label)
    
    def start_progress(self, message: str = "Processing..."):
        """Start progress indication."""
        self.status_label.setText(message)
        self.progress_bar.setValue(0)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self._timer.start(100)
    
    def set_progress(self, value: int, message: str = ""):
        """Set specific progress value."""
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(value)
        if message:
            self.status_label.setText(message)
    
    def complete_progress(self, message: str = "Completed"):
        """Complete progress indication."""
        self._timer.stop()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.status_label.setText(message)
        
        # Auto-hide after delay
        QTimer.singleShot(2000, self.hide_progress)
    
    def hide_progress(self):
        """Hide progress indicator."""
        self.progress_bar.setValue(0)
        self.status_label.setText("Ready")
    
    def update_progress(self):
        """Update indeterminate progress (animated)."""
        # This creates a simple animation effect
        current = self.progress_bar.value()
        if self.progress_bar.maximum() == 0:  # Indeterminate mode
            # The Qt progress bar handles indeterminate animation automatically
            pass


class ValidationWarnings(QWidget):
    """
    Comprehensive validation warnings widget for merge/split operations.
    
    Provides categorized warning display with severity levels, dismissal
    capabilities, and accessibility features.
    """
    
    warnings_cleared = pyqtSignal()
    warning_dismissed = pyqtSignal(str)  # warning_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._warnings: Dict[str, Dict[str, Any]] = {}
        self._dismissed_warnings: set = set()
    
    def setup_ui(self):
        """Set up the main warnings UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel("Validation Status")
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        self.status_label = QLabel("✅ All checks passed")
        self.status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        header_layout.addWidget(self.status_label)
        
        layout.addLayout(header_layout)
        
        # Warnings container
        self.warnings_scroll = QScrollArea()
        self.warnings_scroll.setWidgetResizable(True)
        self.warnings_scroll.setMaximumHeight(200)
        self.warnings_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.warnings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarNever)
        
        self.warnings_container = QWidget()
        self.warnings_layout = QVBoxLayout(self.warnings_container)
        self.warnings_layout.addStretch()  # Add stretch at the end
        
        self.warnings_scroll.setWidget(self.warnings_container)
        layout.addWidget(self.warnings_scroll)
        
        # Initially hidden
        self.warnings_scroll.setVisible(False)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.clear_all_button = QPushButton("Clear All Warnings")
        self.clear_all_button.clicked.connect(self.clear_all_warnings)
        self.clear_all_button.setVisible(False)
        
        self.show_details_button = QPushButton("Show Details")
        self.show_details_button.clicked.connect(self.show_warnings_details)
        self.show_details_button.setVisible(False)
        
        button_layout.addStretch()
        button_layout.addWidget(self.clear_all_button)
        button_layout.addWidget(self.show_details_button)
        
        layout.addLayout(button_layout)
        
        # Progress indicator
        self.progress_indicator = ProgressIndicator()
        self.progress_indicator.setVisible(False)
        layout.addWidget(self.progress_indicator)
        
        # Accessibility helper
        self.accessibility_helper = AccessibilityHelper()
        self.accessibility_helper.setVisible(False)
        layout.addWidget(self.accessibility_helper)
    
    def set_warnings(self, warnings: List[str], severity: str = "warning"):
        """Set validation warnings to display."""
        # Clear existing warnings
        self.clear_warnings_display()
        
        # Add new warnings
        for i, warning in enumerate(warnings):
            warning_id = f"{severity}_{i}"
            self._warnings[warning_id] = {
                "message": warning,
                "severity": severity,
                "timestamp": QTimer().singleShot(0, lambda: None)  # Current time placeholder
            }
        
        self.update_warnings_display()
    
    def add_warning(self, message: str, severity: str = "warning", warning_id: Optional[str] = None):
        """Add a single warning."""
        if warning_id is None:
            warning_id = f"{severity}_{len(self._warnings)}"
        
        self._warnings[warning_id] = {
            "message": message,
            "severity": severity,
            "timestamp": QTimer().singleShot(0, lambda: None)  # Current time placeholder
        }
        
        self.update_warnings_display()
    
    def remove_warning(self, warning_id: str):
        """Remove a specific warning."""
        if warning_id in self._warnings:
            del self._warnings[warning_id]
            self._dismissed_warnings.add(warning_id)
            self.update_warnings_display()
            self.warning_dismissed.emit(warning_id)
    
    def clear_all_warnings(self):
        """Clear all warnings."""
        self._warnings.clear()
        self._dismissed_warnings.clear()
        self.update_warnings_display()
        self.warnings_cleared.emit()
    
    def clear_warnings_display(self):
        """Clear the warnings display widgets."""
        for i in reversed(range(self.warnings_layout.count() - 1)):  # -1 to keep stretch
            child = self.warnings_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
    
    def update_warnings_display(self):
        """Update the warnings display."""
        # Clear existing display
        self.clear_warnings_display()
        
        # Count warnings by severity
        error_count = sum(1 for w in self._warnings.values() if w["severity"] == "error")
        warning_count = sum(1 for w in self._warnings.values() if w["severity"] == "warning")
        info_count = sum(1 for w in self._warnings.values() if w["severity"] == "info")
        
        total_warnings = len(self._warnings)
        
        # Update header
        if total_warnings == 0:
            self.status_label.setText("✅ All checks passed")
            self.status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
            self.warnings_scroll.setVisible(False)
            self.clear_all_button.setVisible(False)
            self.show_details_button.setVisible(False)
        else:
            if error_count > 0:
                self.status_label.setText(f"❌ {error_count} error{'s' if error_count != 1 else ''}")
                self.status_label.setStyleSheet("color: #f44336; font-weight: bold;")
            elif warning_count > 0:
                self.status_label.setText(f"⚠️ {warning_count} warning{'s' if warning_count != 1 else ''}")
                self.status_label.setStyleSheet("color: #ff9800; font-weight: bold;")
            else:
                self.status_label.setText(f"ℹ️ {info_count} info")
                self.status_label.setStyleSheet("color: #2196f3; font-weight: bold;")
            
            self.warnings_scroll.setVisible(True)
            self.clear_all_button.setVisible(True)
            self.show_details_button.setVisible(total_warnings > 3)
        
        # Add warning items
        for warning_id, warning_data in self._warnings.items():
            if warning_id not in self._dismissed_warnings:
                warning_item = ValidationWarningItem(
                    warning_id,
                    warning_data["message"],
                    warning_data["severity"]
                )
                warning_item.warning_dismissed.connect(self.remove_warning)
                warning_item.warning_details_requested.connect(self.show_warning_details)
                
                self.warnings_layout.insertWidget(self.warnings_layout.count() - 1, warning_item)
        
        # Announce to accessibility
        if hasattr(self, 'accessibility_helper') and total_warnings > 0:
            if error_count > 0:
                message = f"Validation found {error_count} errors that must be resolved."
            elif warning_count > 0:
                message = f"Validation found {warning_count} warnings to review."
            else:
                message = f"Validation completed with {info_count} informational messages."
            
            self.accessibility_helper.announce_to_screen_reader(message)
    
    def show_warning_details(self, warning_id: str):
        """Show detailed information for a warning."""
        if warning_id in self._warnings:
            warning_data = self._warnings[warning_id]
            
            details_dialog = QMessageBox(self)
            details_dialog.setWindowTitle("Warning Details")
            details_dialog.setText(f"Severity: {warning_data['severity'].title()}")
            details_dialog.setDetailedText(warning_data["message"])
            details_dialog.setIcon(QMessageBox.Icon.Warning)
            details_dialog.exec()
    
    def show_warnings_details(self):
        """Show details for all warnings."""
        if not self._warnings:
            return
        
        details_text = []
        for warning_id, warning_data in self._warnings.items():
            details_text.append(
                f"{warning_data['severity'].upper()}: {warning_data['message']}"
            )
        
        details_dialog = QMessageBox(self)
        details_dialog.setWindowTitle("All Validation Results")
        details_dialog.setText(f"Found {len(self._warnings)} validation issues:")
        details_dialog.setDetailedText("\n\n".join(details_text))
        details_dialog.setIcon(QMessageBox.Icon.Information)
        details_dialog.exec()
    
    def start_validation(self, message: str = "Validating..."):
        """Start validation progress indication."""
        self.progress_indicator.setVisible(True)
        self.progress_indicator.start_progress(message)
    
    def complete_validation(self, message: str = "Validation completed"):
        """Complete validation and show results."""
        self.progress_indicator.complete_progress(message)
        QTimer.singleShot(2000, lambda: self.progress_indicator.setVisible(False))
    
    def show_accessibility_help(self):
        """Show accessibility help."""
        self.accessibility_helper.setVisible(not self.accessibility_helper.isVisible())
    
    def get_warning_count(self) -> Dict[str, int]:
        """Get count of warnings by severity."""
        counts = {"error": 0, "warning": 0, "info": 0, "total": 0}
        
        for warning_data in self._warnings.values():
            severity = warning_data["severity"]
            if severity in counts:
                counts[severity] += 1
            counts["total"] += 1
        
        return counts
    
    def has_errors(self) -> bool:
        """Check if there are any error-level warnings."""
        return any(w["severity"] == "error" for w in self._warnings.values())
    
    def has_warnings(self) -> bool:
        """Check if there are any warning-level issues."""
        return any(w["severity"] == "warning" for w in self._warnings.values())
    
    def get_all_warnings(self) -> List[Dict[str, Any]]:
        """Get all current warnings."""
        return [
            {"id": warning_id, **warning_data}
            for warning_id, warning_data in self._warnings.items()
            if warning_id not in self._dismissed_warnings
        ]