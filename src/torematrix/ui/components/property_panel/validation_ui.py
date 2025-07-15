"""Validation UI Components

Visual feedback components for property validation including indicators,
tooltips, and error displays. Provides rich user feedback for validation
results with performance-optimized rendering.
"""

from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QScrollArea,
    QToolTip, QPushButton, QTextEdit, QDialog, QDialogButtonBox,
    QListWidget, QListWidgetItem, QSplitter, QGroupBox, QProgressBar
)
from PyQt6.QtCore import (
    Qt, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve,
    QRect, QSize, QPoint
)
from PyQt6.QtGui import (
    QPixmap, QPainter, QColor, QPen, QBrush, QFont, QIcon,
    QPalette, QLinearGradient, QRadialGradient
)

from .validators import ValidationResult, ValidationMessage, ValidationSeverity


class ValidationIcon(QWidget):
    """Animated validation status icon"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        
        # State
        self.severity = ValidationSeverity.INFO
        self.is_validating = False
        self.animation_angle = 0
        
        # Animation timer
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_animation)
        
        # Colors for different severities
        self.severity_colors = {
            ValidationSeverity.INFO: QColor(52, 152, 219),      # Blue
            ValidationSeverity.WARNING: QColor(241, 196, 15),   # Yellow
            ValidationSeverity.ERROR: QColor(231, 76, 60),      # Red
            ValidationSeverity.CRITICAL: QColor(192, 57, 43)    # Dark Red
        }
    
    def set_severity(self, severity: ValidationSeverity):
        """Set validation severity"""
        self.severity = severity
        self.update()
    
    def set_validating(self, validating: bool):
        """Set validating animation state"""
        self.is_validating = validating
        if validating:
            self.animation_timer.start(50)  # 20 FPS
        else:
            self.animation_timer.stop()
            self.animation_angle = 0
        self.update()
    
    def _update_animation(self):
        """Update animation frame"""
        self.animation_angle = (self.animation_angle + 15) % 360
        self.update()
    
    def paintEvent(self, event):
        """Paint the validation icon"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        center = rect.center()
        
        if self.is_validating:
            # Draw spinning animation
            painter.setPen(QPen(QColor(100, 100, 100), 2))
            painter.translate(center)
            painter.rotate(self.animation_angle)
            
            # Draw partial circle
            painter.drawArc(-6, -6, 12, 12, 0, 270 * 16)  # 270 degrees
        else:
            # Draw severity icon
            color = self.severity_colors.get(self.severity, QColor(100, 100, 100))
            
            if self.severity == ValidationSeverity.INFO:
                # Info icon (i)
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(color.darker(120), 1))
                painter.drawEllipse(center.x() - 6, center.y() - 6, 12, 12)
                
                painter.setPen(QPen(Qt.GlobalColor.white, 2))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "i")
            
            elif self.severity == ValidationSeverity.WARNING:
                # Warning icon (triangle with !)
                points = [
                    QPoint(center.x(), center.y() - 6),
                    QPoint(center.x() - 6, center.y() + 6),
                    QPoint(center.x() + 6, center.y() + 6)
                ]
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(color.darker(120), 1))
                painter.drawPolygon(points)
                
                painter.setPen(QPen(Qt.GlobalColor.white, 2))
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "!")
            
            elif self.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
                # Error icon (X)
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(color.darker(120), 1))
                painter.drawEllipse(center.x() - 6, center.y() - 6, 12, 12)
                
                painter.setPen(QPen(Qt.GlobalColor.white, 2))
                painter.drawLine(center.x() - 3, center.y() - 3, center.x() + 3, center.y() + 3)
                painter.drawLine(center.x() - 3, center.y() + 3, center.x() + 3, center.y() - 3)


class ValidationIndicatorWidget(QWidget):
    """Comprehensive validation indicator with tooltip and click details"""
    
    clicked = pyqtSignal()
    details_requested = pyqtSignal(ValidationResult)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self.validation_result: Optional[ValidationResult] = None
        self.show_summary = True
        self.auto_hide_when_valid = True
        
        # UI setup
        self.setup_ui()
        self.setup_animations()
        
        # Initially hidden
        self.setVisible(False)
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        
        # Validation icon
        self.icon = ValidationIcon()
        layout.addWidget(self.icon)
        
        # Summary label
        self.summary_label = QLabel()
        self.summary_label.setFont(QFont("", 8))
        layout.addWidget(self.summary_label)
        
        layout.addStretch()
        
        # Details button (small)
        self.details_btn = QPushButton("⋯")
        self.details_btn.setFixedSize(16, 16)
        self.details_btn.setToolTip("Show validation details")
        self.details_btn.clicked.connect(self._show_details)
        layout.addWidget(self.details_btn)
        
        # Styling
        self.setStyleSheet("""
            ValidationIndicatorWidget {
                background: rgba(240, 240, 240, 200);
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            ValidationIndicatorWidget[severity="error"] {
                background: rgba(231, 76, 60, 30);
                border-color: rgba(231, 76, 60, 100);
            }
            ValidationIndicatorWidget[severity="warning"] {
                background: rgba(241, 196, 15, 30);
                border-color: rgba(241, 196, 15, 100);
            }
            ValidationIndicatorWidget[severity="info"] {
                background: rgba(52, 152, 219, 30);
                border-color: rgba(52, 152, 219, 100);
            }
            QPushButton {
                border: none;
                background: transparent;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(0, 0, 0, 20);
                border-radius: 2px;
            }
        """)
    
    def setup_animations(self):
        """Setup show/hide animations"""
        self.show_animation = QPropertyAnimation(self, b"maximumHeight")
        self.show_animation.setDuration(200)
        self.show_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.hide_animation = QPropertyAnimation(self, b"maximumHeight")
        self.hide_animation.setDuration(200)
        self.hide_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.hide_animation.finished.connect(lambda: self.setVisible(False))
    
    def set_validation_result(self, result: ValidationResult):
        """Set validation result and update display"""
        self.validation_result = result
        self._update_display()
    
    def set_validating(self, validating: bool):
        """Set validating state"""
        self.icon.set_validating(validating)
        
        if validating:
            self.summary_label.setText("Validating...")
            self.details_btn.setVisible(False)
            self._show_animated()
        else:
            self.details_btn.setVisible(True)
    
    def _update_display(self):
        """Update visual display based on validation result"""
        if not self.validation_result:
            self._hide_animated()
            return
        
        result = self.validation_result
        
        # Determine severity
        if result.get_error_count() > 0:
            severity = ValidationSeverity.ERROR
        elif result.get_warning_count() > 0:
            severity = ValidationSeverity.WARNING
        else:
            severity = ValidationSeverity.INFO
        
        # Update icon
        self.icon.set_severity(severity)
        self.icon.set_validating(False)
        
        # Update summary
        if self.show_summary:
            self.summary_label.setText(result.get_summary())
        else:
            self.summary_label.setText("")
        
        # Update styling
        self.setProperty("severity", severity.value)
        self.style().unpolish(self)
        self.style().polish(self)
        
        # Update tooltip
        self._update_tooltip()
        
        # Show/hide widget
        if result.is_valid and self.auto_hide_when_valid and result.get_warning_count() == 0:
            self._hide_animated()
        else:
            self._show_animated()
    
    def _update_tooltip(self):
        """Update tooltip with validation details"""
        if not self.validation_result:
            self.setToolTip("")
            return
        
        result = self.validation_result
        tooltip_parts = []
        
        # Add errors
        errors = [m for m in result.messages 
                 if m.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]]
        if errors:
            tooltip_parts.append("<b>Errors:</b>")
            for error in errors[:3]:  # Show max 3
                tooltip_parts.append(f"• {error.message}")
            if len(errors) > 3:
                tooltip_parts.append(f"• ... and {len(errors) - 3} more")
        
        # Add warnings
        warnings = [m for m in result.messages if m.severity == ValidationSeverity.WARNING]
        if warnings:
            if tooltip_parts:
                tooltip_parts.append("")
            tooltip_parts.append("<b>Warnings:</b>")
            for warning in warnings[:3]:  # Show max 3
                tooltip_parts.append(f"• {warning.message}")
            if len(warnings) > 3:
                tooltip_parts.append(f"• ... and {len(warnings) - 3} more")
        
        # Add performance info
        if result.performance_ms is not None:
            if tooltip_parts:
                tooltip_parts.append("")
            tooltip_parts.append(f"<i>Validation time: {result.performance_ms:.1f}ms</i>")
        
        self.setToolTip("<br>".join(tooltip_parts))
    
    def _show_animated(self):
        """Show widget with animation"""
        if self.isVisible():
            return
        
        self.setVisible(True)
        self.setMaximumHeight(0)
        
        target_height = self.sizeHint().height()
        self.show_animation.setStartValue(0)
        self.show_animation.setEndValue(target_height)
        self.show_animation.start()
    
    def _hide_animated(self):
        """Hide widget with animation"""
        if not self.isVisible():
            return
        
        current_height = self.height()
        self.hide_animation.setStartValue(current_height)
        self.hide_animation.setEndValue(0)
        self.hide_animation.start()
    
    def _show_details(self):
        """Show detailed validation results"""
        if self.validation_result:
            self.details_requested.emit(self.validation_result)
    
    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class ValidationDetailsDialog(QDialog):
    """Dialog showing detailed validation results"""
    
    def __init__(self, validation_result: ValidationResult, parent=None):
        super().__init__(parent)
        self.validation_result = validation_result
        
        self.setWindowTitle("Validation Details")
        self.setMinimumSize(500, 400)
        self.setup_ui()
        self.populate_data()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        # Summary
        summary_group = QGroupBox("Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        self.summary_label = QLabel()
        self.summary_label.setFont(QFont("", 10, QFont.Weight.Bold))
        summary_layout.addWidget(self.summary_label)
        
        # Performance info
        self.performance_label = QLabel()
        self.performance_label.setFont(QFont("", 8))
        self.performance_label.setStyleSheet("color: #666;")
        summary_layout.addWidget(self.performance_label)
        
        layout.addWidget(summary_group)
        
        # Details splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Messages list
        messages_group = QGroupBox("Messages")
        messages_layout = QVBoxLayout(messages_group)
        
        self.messages_list = QListWidget()
        messages_layout.addWidget(self.messages_list)
        
        splitter.addWidget(messages_group)
        
        # Message details
        details_group = QGroupBox("Message Details")
        details_layout = QVBoxLayout(details_group)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        details_layout.addWidget(self.details_text)
        
        splitter.addWidget(details_group)
        splitter.setSizes([300, 200])
        
        layout.addWidget(splitter)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Connections
        self.messages_list.itemSelectionChanged.connect(self._on_message_selected)
    
    def populate_data(self):
        """Populate dialog with validation data"""
        result = self.validation_result
        
        # Summary
        self.summary_label.setText(result.get_summary())
        
        # Performance
        if result.performance_ms is not None:
            self.performance_label.setText(
                f"Validation completed in {result.performance_ms:.1f}ms"
            )
        else:
            self.performance_label.setText("")
        
        # Messages
        self.messages_list.clear()
        for i, message in enumerate(result.messages):
            item = QListWidgetItem()
            
            # Set text
            text = message.message
            if message.field:
                text = f"[{message.field}] {text}"
            item.setText(text)
            
            # Set icon and color based on severity
            if message.severity == ValidationSeverity.ERROR:
                item.setForeground(QColor(231, 76, 60))
                icon_text = "❌"
            elif message.severity == ValidationSeverity.CRITICAL:
                item.setForeground(QColor(192, 57, 43))
                icon_text = "🚫"
            elif message.severity == ValidationSeverity.WARNING:
                item.setForeground(QColor(241, 196, 15))
                icon_text = "⚠️"
            else:
                item.setForeground(QColor(52, 152, 219))
                icon_text = "ℹ️"
            
            item.setText(f"{icon_text} {text}")
            item.setData(Qt.ItemDataRole.UserRole, message)
            
            self.messages_list.addItem(item)
        
        # Select first item if any
        if self.messages_list.count() > 0:
            self.messages_list.setCurrentRow(0)
    
    def _on_message_selected(self):
        """Handle message selection"""
        current_item = self.messages_list.currentItem()
        if not current_item:
            self.details_text.clear()
            return
        
        message = current_item.data(Qt.ItemDataRole.UserRole)
        if not message:
            return
        
        # Build details text
        details_parts = []
        details_parts.append(f"<b>Message:</b> {message.message}")
        details_parts.append(f"<b>Severity:</b> {message.severity.value.title()}")
        
        if message.field:
            details_parts.append(f"<b>Field:</b> {message.field}")
        
        if message.code:
            details_parts.append(f"<b>Code:</b> {message.code}")
        
        if message.suggestion:
            details_parts.append(f"<b>Suggestion:</b> {message.suggestion}")
        
        if message.details:
            details_parts.append("<b>Additional Details:</b>")
            for key, value in message.details.items():
                details_parts.append(f"• <b>{key}:</b> {value}")
        
        self.details_text.setHtml("<br>".join(details_parts))


class ValidationSummaryWidget(QWidget):
    """Summary widget showing overall validation status"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State
        self.field_results: Dict[str, ValidationResult] = {}
        
        # UI setup
        self.setup_ui()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        
        # Overall status icon
        self.status_icon = ValidationIcon()
        layout.addWidget(self.status_icon)
        
        # Status text
        self.status_label = QLabel("No validation results")
        self.status_label.setFont(QFont("", 9))
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Progress bar for validation
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(100)
        self.progress_bar.setMaximumHeight(8)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Statistics
        self.stats_label = QLabel()
        self.stats_label.setFont(QFont("", 8))
        self.stats_label.setStyleSheet("color: #666;")
        layout.addWidget(self.stats_label)
    
    def set_field_result(self, field_name: str, result: ValidationResult):
        """Set validation result for a field"""
        self.field_results[field_name] = result
        self._update_summary()
    
    def remove_field_result(self, field_name: str):
        """Remove validation result for a field"""
        if field_name in self.field_results:
            del self.field_results[field_name]
            self._update_summary()
    
    def clear_results(self):
        """Clear all validation results"""
        self.field_results.clear()
        self._update_summary()
    
    def set_validating(self, field_name: str, validating: bool):
        """Set validation state for a field"""
        if validating:
            self.status_icon.set_validating(True)
            self.status_label.setText(f"Validating {field_name}...")
            self.progress_bar.setVisible(True)
        else:
            self.status_icon.set_validating(False)
            self.progress_bar.setVisible(False)
            self._update_summary()
    
    def _update_summary(self):
        """Update summary display"""
        if not self.field_results:
            self.status_label.setText("No validation results")
            self.stats_label.setText("")
            self.status_icon.set_severity(ValidationSeverity.INFO)
            return
        
        # Calculate overall statistics
        total_errors = 0
        total_warnings = 0
        total_fields = len(self.field_results)
        valid_fields = 0
        
        for result in self.field_results.values():
            total_errors += result.get_error_count()
            total_warnings += result.get_warning_count()
            if result.is_valid:
                valid_fields += 1
        
        # Determine overall status
        if total_errors > 0:
            overall_severity = ValidationSeverity.ERROR
            status_text = f"{total_errors} errors"
            if total_warnings > 0:
                status_text += f", {total_warnings} warnings"
        elif total_warnings > 0:
            overall_severity = ValidationSeverity.WARNING
            status_text = f"{total_warnings} warnings"
        else:
            overall_severity = ValidationSeverity.INFO
            status_text = "All valid"
        
        # Update display
        self.status_icon.set_severity(overall_severity)
        self.status_label.setText(status_text)
        
        # Update statistics
        stats_text = f"{valid_fields}/{total_fields} fields valid"
        self.stats_label.setText(stats_text)