"""
Validation UI Components for Agent 2 - Issue #235.

This module provides UI components for displaying validation warnings
and status with categorized warning system and accessibility support.
"""

from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGroupBox, QProgressBar, QListWidget,
    QListWidgetItem, QTextEdit, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon


class ValidationWarningItem(QWidget):
    """Widget for displaying a single validation warning."""
    
    warning_dismissed = pyqtSignal(str)  # warning_id
    
    def __init__(self, warning_id: str, message: str, severity: str = "warning", parent=None):
        super().__init__(parent)
        self.warning_id = warning_id
        self.message = message
        self.severity = severity
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the warning item UI."""
        layout = QHBoxLayout(self)
        
        # Severity indicator
        severity_colors = {
            "error": "#ff4444",
            "warning": "#ffaa00", 
            "info": "#4488ff"
        }
        
        severity_label = QLabel("●")
        severity_label.setStyleSheet(f"color: {severity_colors.get(self.severity, '#666')}; font-size: 16px;")
        severity_label.setFixedWidth(20)
        layout.addWidget(severity_label)
        
        # Message
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        layout.addWidget(message_label)
        
        # Dismiss button
        dismiss_button = QPushButton("×")
        dismiss_button.setFixedSize(20, 20)
        dismiss_button.setStyleSheet("""
            QPushButton {
                border: none;
                background: #ddd;
                border-radius: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #bbb;
            }
        """)
        dismiss_button.clicked.connect(lambda: self.warning_dismissed.emit(self.warning_id))
        layout.addWidget(dismiss_button)
        
        # Style the widget based on severity
        if self.severity == "error":
            self.setStyleSheet("background-color: #ffeeee; border-left: 3px solid #ff4444; padding: 5px;")
        elif self.severity == "warning":
            self.setStyleSheet("background-color: #fffaee; border-left: 3px solid #ffaa00; padding: 5px;")
        else:  # info
            self.setStyleSheet("background-color: #eeeeff; border-left: 3px solid #4488ff; padding: 5px;")


class AccessibilityHelper(QWidget):
    """Helper widget for accessibility features."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup accessibility helper UI."""
        layout = QVBoxLayout(self)
        
        # Screen reader support
        self.screen_reader_label = QLabel()
        self.screen_reader_label.setAccessibleName("Validation Status")
        layout.addWidget(self.screen_reader_label)
        
        # Keyboard navigation hints
        self.keyboard_hints = QLabel("Press Tab to navigate, Enter to dismiss warnings")
        self.keyboard_hints.setStyleSheet("color: #666; font-size: 10px; font-style: italic;")
        layout.addWidget(self.keyboard_hints)
        
    def update_screen_reader_text(self, text: str):
        """Update text for screen readers."""
        self.screen_reader_label.setText(text)
        self.screen_reader_label.setAccessibleDescription(text)


class ProgressIndicator(QWidget):
    """Progress indicator for validation operations."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup progress indicator UI."""
        layout = QVBoxLayout(self)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Validating...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
    def set_status(self, status: str):
        """Set the current status text."""
        self.status_label.setText(status)
        
    def set_progress(self, value: int, maximum: int = 100):
        """Set determinate progress."""
        self.progress_bar.setRange(0, maximum)
        self.progress_bar.setValue(value)
        
    def set_indeterminate(self):
        """Set indeterminate progress."""
        self.progress_bar.setRange(0, 0)


class ValidationWarnings(QWidget):
    """Main validation warnings widget with categorized warning system."""
    
    warning_dismissed = pyqtSignal(str)  # warning_id
    all_warnings_cleared = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._warnings = {}  # warning_id -> warning_data
        self._dismissed_warnings = set()
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the validation warnings UI."""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("Validation Status")
        self.title_label.setFont(QFont("", 12, QFont.Weight.Bold))
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Filter controls
        self.severity_filter = QComboBox()
        self.severity_filter.addItems(["All", "Errors", "Warnings", "Info"])
        self.severity_filter.currentTextChanged.connect(self.filter_warnings)
        header_layout.addWidget(self.severity_filter)
        
        # Clear all button
        self.clear_all_button = QPushButton("Clear All")
        self.clear_all_button.clicked.connect(self.clear_all_warnings)
        self.clear_all_button.setVisible(False)
        header_layout.addWidget(self.clear_all_button)
        
        layout.addLayout(header_layout)
        
        # Status label
        self.status_label = QLabel("All checks passed")
        self.status_label.setStyleSheet("color: #008800; font-weight: bold; padding: 10px;")
        layout.addWidget(self.status_label)
        
        # Warnings scroll area
        self.warnings_scroll = QScrollArea()
        self.warnings_scroll.setWidgetResizable(True)
        self.warnings_scroll.setVisible(False)
        
        self.warnings_widget = QWidget()
        self.warnings_layout = QVBoxLayout(self.warnings_widget)
        self.warnings_scroll.setWidget(self.warnings_widget)
        
        layout.addWidget(self.warnings_scroll)
        
        # Progress indicator
        self.progress_indicator = ProgressIndicator()
        self.progress_indicator.setVisible(False)
        layout.addWidget(self.progress_indicator)
        
        # Accessibility helper
        self.accessibility_helper = AccessibilityHelper()
        layout.addWidget(self.accessibility_helper)
        
        # Summary stats
        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        layout.addWidget(self.summary_label)
        
        layout.addStretch()
        
    def set_warnings(self, warnings: List[str], severity: str = "warning"):
        """Set warnings from a list of strings."""
        self.clear_all_warnings()
        
        for i, warning_text in enumerate(warnings):
            warning_id = f"warning_{i}"
            self.add_warning(warning_text, severity, warning_id)
            
    def add_warning(self, message: str, severity: str = "warning", warning_id: Optional[str] = None):
        """Add a single warning."""
        if warning_id is None:
            warning_id = f"warning_{len(self._warnings)}"
            
        if warning_id in self._dismissed_warnings:
            return  # Don't re-add dismissed warnings
            
        warning_data = {
            "message": message,
            "severity": severity,
            "id": warning_id
        }
        
        self._warnings[warning_id] = warning_data
        
        # Create warning widget
        warning_widget = ValidationWarningItem(warning_id, message, severity)
        warning_widget.warning_dismissed.connect(self.remove_warning)
        
        # Add to layout
        self.warnings_layout.addWidget(warning_widget)
        
        # Update UI
        self.update_display()
        
    def remove_warning(self, warning_id: str):
        """Remove a warning."""
        if warning_id in self._warnings:
            # Find and remove the widget
            for i in range(self.warnings_layout.count()):
                widget = self.warnings_layout.itemAt(i).widget()
                if isinstance(widget, ValidationWarningItem) and widget.warning_id == warning_id:
                    widget.setParent(None)
                    break
                    
            # Remove from data
            del self._warnings[warning_id]
            self._dismissed_warnings.add(warning_id)
            
            # Update display
            self.update_display()
            
            # Emit signal
            self.warning_dismissed.emit(warning_id)
            
    def clear_all_warnings(self):
        """Clear all warnings."""
        # Remove all widgets
        for i in reversed(range(self.warnings_layout.count())):
            widget = self.warnings_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                
        # Clear data
        self._warnings.clear()
        self._dismissed_warnings.clear()
        
        # Update display
        self.update_display()
        
        # Emit signal
        self.all_warnings_cleared.emit()
        
    def filter_warnings(self, filter_text: str):
        """Filter warnings by severity."""
        for i in range(self.warnings_layout.count()):
            widget = self.warnings_layout.itemAt(i).widget()
            if isinstance(widget, ValidationWarningItem):
                if filter_text == "All":
                    widget.setVisible(True)
                elif filter_text == "Errors" and widget.severity != "error":
                    widget.setVisible(False)
                elif filter_text == "Warnings" and widget.severity != "warning":
                    widget.setVisible(False)
                elif filter_text == "Info" and widget.severity != "info":
                    widget.setVisible(False)
                else:
                    widget.setVisible(True)
                    
    def update_display(self):
        """Update the display based on current warnings."""
        warning_count = len(self._warnings)
        
        if warning_count == 0:
            # No warnings
            self.status_label.setText("All checks passed")
            self.status_label.setStyleSheet("color: #008800; font-weight: bold; padding: 10px;")
            self.warnings_scroll.setVisible(False)
            self.clear_all_button.setVisible(False)
            self.accessibility_helper.update_screen_reader_text("All validation checks passed")
            self.summary_label.setText("")
            
        else:
            # Has warnings
            error_count = sum(1 for w in self._warnings.values() if w["severity"] == "error")
            warning_count_only = sum(1 for w in self._warnings.values() if w["severity"] == "warning")
            info_count = sum(1 for w in self._warnings.values() if w["severity"] == "info")
            
            if error_count > 0:
                self.status_label.setText(f"{error_count} error{'s' if error_count != 1 else ''} found")
                self.status_label.setStyleSheet("color: #cc0000; font-weight: bold; padding: 10px;")
            elif warning_count_only > 0:
                self.status_label.setText(f"{warning_count_only} warning{'s' if warning_count_only != 1 else ''} found")
                self.status_label.setStyleSheet("color: #cc6600; font-weight: bold; padding: 10px;")
            else:
                self.status_label.setText(f"{info_count} info message{'s' if info_count != 1 else ''}")
                self.status_label.setStyleSheet("color: #0066cc; font-weight: bold; padding: 10px;")
                
            self.warnings_scroll.setVisible(True)
            self.clear_all_button.setVisible(True)
            
            # Update accessibility
            severity_text = "errors" if error_count > 0 else "warnings" if warning_count_only > 0 else "info messages"
            self.accessibility_helper.update_screen_reader_text(f"{warning_count} {severity_text} found")
            
            # Update summary
            summary_parts = []
            if error_count > 0:
                summary_parts.append(f"{error_count} error{'s' if error_count != 1 else ''}")
            if warning_count_only > 0:
                summary_parts.append(f"{warning_count_only} warning{'s' if warning_count_only != 1 else ''}")
            if info_count > 0:
                summary_parts.append(f"{info_count} info")
                
            self.summary_label.setText(" | ".join(summary_parts))
            
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
        """Check if there are any errors."""
        return any(w["severity"] == "error" for w in self._warnings.values())
        
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return any(w["severity"] == "warning" for w in self._warnings.values())
        
    def start_validation(self, message: str = "Validating..."):
        """Start validation progress indicator."""
        self.progress_indicator.setVisible(True)
        self.progress_indicator.set_status(message)
        self.progress_indicator.set_indeterminate()
        
    def update_validation_progress(self, value: int, maximum: int = 100, message: str = ""):
        """Update validation progress."""
        if self.progress_indicator.isVisible():
            self.progress_indicator.set_progress(value, maximum)
            if message:
                self.progress_indicator.set_status(message)
                
    def complete_validation(self, message: str = "Validation complete"):
        """Complete validation and hide progress."""
        if self.progress_indicator.isVisible():
            self.progress_indicator.set_status(message)
            
            # Hide progress after a short delay
            QTimer.singleShot(1000, lambda: self.progress_indicator.setVisible(False))
            
    def get_all_warnings(self) -> Dict[str, Dict[str, Any]]:
        """Get all current warnings."""
        return self._warnings.copy()