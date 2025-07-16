"""
Validation UI Components.

This module provides UI components for displaying validation warnings,
accessibility features, and progress indicators.
"""

from typing import List, Dict, Any, Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QProgressBar, QToolButton, QSpacerItem,
    QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon, QPixmap, QPainter


class ValidationWarningItem(QWidget):
    """Individual validation warning item widget."""
    
    warning_dismissed = pyqtSignal(str)  # warning_id
    
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
        icon_label.setFixedSize(16, 16)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Set icon based on severity
        icon_color = self._get_severity_color()
        icon_pixmap = self._create_severity_icon(icon_color)
        icon_label.setPixmap(icon_pixmap)
        
        layout.addWidget(icon_label)
        
        # Message text
        message_label = QLabel(self.message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet(f"color: {icon_color}; font-weight: bold;")
        layout.addWidget(message_label, 1)
        
        # Dismiss button
        dismiss_button = QToolButton()
        dismiss_button.setText("×")
        dismiss_button.setFixedSize(20, 20)
        dismiss_button.setStyleSheet("""
            QToolButton {
                background: transparent;
                border: none;
                font-size: 16px;
                font-weight: bold;
                color: #666666;
            }
            QToolButton:hover {
                background: rgba(0,0,0,0.1);
                border-radius: 10px;
            }
        """)
        dismiss_button.clicked.connect(lambda: self.warning_dismissed.emit(self.warning_id))
        layout.addWidget(dismiss_button)
        
        # Set background color based on severity
        self.setStyleSheet(f"""
            ValidationWarningItem {{
                background-color: {self._get_background_color()};
                border: 1px solid {icon_color};
                border-radius: 4px;
                margin: 2px;
            }}
        """)
    
    def _get_severity_color(self) -> str:
        """Get color based on severity level."""
        colors = {
            "error": "#f44336",
            "warning": "#ff9800", 
            "info": "#2196f3",
            "success": "#4caf50"
        }
        return colors.get(self.severity, "#ff9800")
    
    def _get_background_color(self) -> str:
        """Get background color based on severity."""
        backgrounds = {
            "error": "#ffebee",
            "warning": "#fff8e1",
            "info": "#e3f2fd", 
            "success": "#e8f5e8"
        }
        return backgrounds.get(self.severity, "#fff8e1")
    
    def _create_severity_icon(self, color: str) -> QPixmap:
        """Create severity icon pixmap."""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(color))
        painter.setBrush(QColor(color))
        
        if self.severity == "error":
            # X mark
            painter.drawLine(4, 4, 12, 12)
            painter.drawLine(4, 12, 12, 4)
        elif self.severity == "warning":
            # Triangle with !
            painter.drawPolygon([
                (8, 2), (14, 14), (2, 14)
            ])
            painter.setPen(QColor("white"))
            painter.drawLine(8, 5, 8, 10)
            painter.drawEllipse(7, 11, 2, 2)
        elif self.severity == "info":
            # Circle with i
            painter.drawEllipse(2, 2, 12, 12)
            painter.setPen(QColor("white"))
            painter.drawEllipse(7, 5, 2, 2)
            painter.drawLine(8, 8, 8, 12)
        elif self.severity == "success":
            # Check mark
            painter.drawLine(4, 8, 7, 11)
            painter.drawLine(7, 11, 12, 5)
        
        painter.end()
        return pixmap


class AccessibilityHelper:
    """Helper class for accessibility features."""
    
    @staticmethod
    def set_accessible_name(widget: QWidget, name: str):
        """Set accessible name for screen readers."""
        widget.setAccessibleName(name)
    
    @staticmethod
    def set_accessible_description(widget: QWidget, description: str):
        """Set accessible description for screen readers."""
        widget.setAccessibleDescription(description)
    
    @staticmethod
    def set_focus_policy(widget: QWidget, policy: Qt.FocusPolicy = Qt.FocusPolicy.TabFocus):
        """Set focus policy for keyboard navigation."""
        widget.setFocusPolicy(policy)
    
    @staticmethod
    def ensure_minimum_size(widget: QWidget, min_width: int = 44, min_height: int = 44):
        """Ensure minimum touch target size."""
        widget.setMinimumSize(min_width, min_height)
    
    @staticmethod
    def set_high_contrast_stylesheet(widget: QWidget):
        """Apply high contrast stylesheet for accessibility."""
        widget.setStyleSheet("""
            QWidget {
                background-color: white;
                color: black;
                border: 2px solid black;
            }
            QWidget:focus {
                outline: 3px solid #005fcc;
                outline-offset: 2px;
            }
        """)


class ProgressIndicator(QWidget):
    """Animated progress indicator widget."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self._animation_timer = QTimer()
        self._animation_timer.timeout.connect(self._update_animation)
    
    def setup_ui(self):
        """Set up the progress indicator UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(0)  # Indeterminate progress
        self.progress_bar.setFixedHeight(4)
        layout.addWidget(self.progress_bar)
        
        # Hide by default
        self.setVisible(False)
    
    def start_progress(self, message: str = "Processing..."):
        """Start the progress indicator."""
        self.setVisible(True)
        self.progress_bar.setVisible(True)
        self._animation_timer.start(50)  # Update every 50ms
        
        # Set accessible name
        AccessibilityHelper.set_accessible_name(self, f"Progress: {message}")
    
    def stop_progress(self):
        """Stop the progress indicator."""
        self._animation_timer.stop()
        self.setVisible(False)
    
    def _update_animation(self):
        """Update progress animation."""
        # The QProgressBar handles the animation automatically when min=max=0
        pass


class ValidationWarnings(QWidget):
    """
    Main validation warnings widget.
    
    Displays validation warnings, errors, and informational messages
    with proper accessibility support and user interaction.
    """
    
    warnings_changed = pyqtSignal(int)  # warning_count
    all_warnings_dismissed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._warnings: Dict[str, Dict[str, Any]] = {}
        self._dismissed_warnings: set = set()
        self._warning_counter = 0
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the main warnings widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header with status
        header_layout = QHBoxLayout()
        
        self.status_label = QLabel("All checks passed")
        self.status_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        self.status_label.setStyleSheet("color: #4caf50;")
        header_layout.addWidget(self.status_label)
        
        header_layout.addStretch()
        
        # Dismiss all button
        self.dismiss_all_button = QPushButton("Dismiss All")
        self.dismiss_all_button.setVisible(False)
        self.dismiss_all_button.clicked.connect(self.clear_all_warnings)
        header_layout.addWidget(self.dismiss_all_button)
        
        layout.addLayout(header_layout)
        
        # Progress indicator
        self.progress_indicator = ProgressIndicator()
        layout.addWidget(self.progress_indicator)
        
        # Warnings scroll area
        self.warnings_scroll = QScrollArea()
        self.warnings_scroll.setWidgetResizable(True)
        self.warnings_scroll.setMaximumHeight(200)
        self.warnings_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.warnings_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarNever)
        self.warnings_scroll.setVisible(False)
        
        self.warnings_widget = QWidget()
        self.warnings_layout = QVBoxLayout(self.warnings_widget)
        self.warnings_layout.setContentsMargins(0, 0, 0, 0)
        self.warnings_scroll.setWidget(self.warnings_widget)
        
        layout.addWidget(self.warnings_scroll)
        
        # Set accessibility properties
        AccessibilityHelper.set_accessible_name(self, "Validation warnings")
        AccessibilityHelper.set_accessible_description(
            self, "Displays validation warnings and errors for the current operation"
        )
    
    def set_warnings(self, warnings: List[str], severity: str = "warning"):
        """Set multiple warnings at once."""
        self.clear_all_warnings()
        
        for warning in warnings:
            self.add_warning(warning, severity)
    
    def add_warning(self, message: str, severity: str = "warning", warning_id: Optional[str] = None):
        """Add a single warning."""
        if warning_id is None:
            warning_id = f"warning_{self._warning_counter}"
            self._warning_counter += 1
        
        if warning_id in self._dismissed_warnings:
            return  # Already dismissed
        
        # Store warning data
        self._warnings[warning_id] = {
            "message": message,
            "severity": severity,
            "timestamp": QTimer().remainingTime()
        }
        
        # Create warning widget
        warning_widget = ValidationWarningItem(warning_id, message, severity)
        warning_widget.warning_dismissed.connect(self.remove_warning)
        
        # Add to layout
        self.warnings_layout.addWidget(warning_widget)
        
        # Update display
        self._update_warnings_display()
    
    def remove_warning(self, warning_id: str):
        """Remove a specific warning."""
        if warning_id in self._warnings:
            del self._warnings[warning_id]
            self._dismissed_warnings.add(warning_id)
        
        # Remove widget from layout
        for i in range(self.warnings_layout.count()):
            item = self.warnings_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if isinstance(widget, ValidationWarningItem) and widget.warning_id == warning_id:
                    widget.setParent(None)
                    break
        
        self._update_warnings_display()
    
    def clear_all_warnings(self):
        """Clear all warnings."""
        self._warnings.clear()
        self._dismissed_warnings.clear()
        
        # Remove all warning widgets
        for i in reversed(range(self.warnings_layout.count())):
            item = self.warnings_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
        
        self._update_warnings_display()
        self.all_warnings_dismissed.emit()
    
    def start_validation(self, message: str = "Validating..."):
        """Start validation progress indicator."""
        self.progress_indicator.start_progress(message)
    
    def complete_validation(self, message: str = "Validation complete"):
        """Complete validation and hide progress."""
        self.progress_indicator.stop_progress()
        
        # Show temporary completion message
        if not self._warnings:
            self.status_label.setText(message)
            QTimer.singleShot(2000, lambda: self.status_label.setText("All checks passed"))
    
    def get_warning_count(self) -> Dict[str, int]:
        """Get count of warnings by severity."""
        counts = {"error": 0, "warning": 0, "info": 0, "success": 0, "total": 0}
        
        for warning_data in self._warnings.values():
            severity = warning_data.get("severity", "warning")
            if severity in counts:
                counts[severity] += 1
            counts["total"] += 1
        
        return counts
    
    def has_errors(self) -> bool:
        """Check if there are any error-level warnings."""
        return any(
            warning_data.get("severity") == "error" 
            for warning_data in self._warnings.values()
        )
    
    def has_warnings(self) -> bool:
        """Check if there are any warning-level warnings."""
        return any(
            warning_data.get("severity") == "warning"
            for warning_data in self._warnings.values()
        )
    
    def _update_warnings_display(self):
        """Update the warnings display based on current warnings."""
        warning_count = len(self._warnings)
        
        if warning_count == 0:
            # No warnings
            self.status_label.setText("All checks passed")
            self.status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
            self.warnings_scroll.setVisible(False)
            self.dismiss_all_button.setVisible(False)
        else:
            # Has warnings
            counts = self.get_warning_count()
            
            # Determine overall status
            if counts["error"] > 0:
                status_color = "#f44336"
                status_text = f"{counts['error']} error{'s' if counts['error'] != 1 else ''}"
                if counts["warning"] > 0:
                    status_text += f", {counts['warning']} warning{'s' if counts['warning'] != 1 else ''}"
            elif counts["warning"] > 0:
                status_color = "#ff9800"
                status_text = f"{counts['warning']} warning{'s' if counts['warning'] != 1 else ''}"
            else:
                status_color = "#2196f3"
                status_text = f"{warning_count} message{'s' if warning_count != 1 else ''}"
            
            self.status_label.setText(status_text)
            self.status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
            self.warnings_scroll.setVisible(True)
            self.dismiss_all_button.setVisible(True)
        
        # Emit signal
        self.warnings_changed.emit(warning_count)
        
        # Update accessibility
        AccessibilityHelper.set_accessible_description(
            self, f"Displaying {warning_count} validation warnings"
        )