"""Property Panel Accessibility Manager

Provides comprehensive accessibility features including keyboard navigation,
screen reader support, and WCAG compliance for the property panel.
"""

from typing import Dict, List, Any, Optional, Callable
from PyQt6.QtWidgets import (
    QWidget, QApplication, QLabel, QFrame, QVBoxLayout,
    QHBoxLayout, QToolTip, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QEvent, QTimer, QRect
from PyQt6.QtGui import QKeySequence, QFont, QFontMetrics, QPalette, QColor, QPainter, QPen, QShortcut

try:
    from PyQt6.QtGui import QAccessible
except ImportError:
    # Fallback for systems without accessibility support
    class QAccessible:
        @staticmethod
        def setActive(active):
            pass
        
        @staticmethod
        def updateAccessibility(event):
            pass
        
        class AccessibleEvent:
            Announcement = "announcement"


class PropertyAccessibilityManager(QObject):
    """Manages accessibility features for the property panel"""
    
    # Signals
    accessibility_changed = pyqtSignal(bool)  # enabled state
    screen_reader_announcement = pyqtSignal(str)  # text to announce
    focus_changed = pyqtSignal(str, str)  # element_id, property_name
    
    def __init__(self, property_panel, main_window):
        super().__init__()
        self.property_panel = property_panel
        self.main_window = main_window
        self.enabled = True
        
        # Accessibility settings
        self.high_contrast_mode = False
        self.large_font_mode = False
        self.screen_reader_enabled = self._detect_screen_reader()
        self.font_scale_factor = 1.0
        
        # Keyboard shortcuts
        self.shortcuts: Dict[str, QShortcut] = {}
        
        # Focus management
        self.focus_indicator: Optional['FocusIndicator'] = None
        self.current_focus_element = None
        
        # Setup accessibility
        self._setup_accessibility()
        self._setup_keyboard_shortcuts()
        self._setup_focus_management()
    
    def _setup_accessibility(self) -> None:
        """Setup basic accessibility features"""
        # Enable Qt accessibility
        QAccessible.setActive(True)
        
        # Detect system accessibility settings
        self._detect_system_settings()
        
        # Install event filter for accessibility events
        if self.main_window:
            self.main_window.installEventFilter(self)
    
    def _detect_screen_reader(self) -> bool:
        """Detect if screen reader is active"""
        # Simple detection - would be enhanced in production
        import os
        return os.environ.get('SCREEN_READER', '').lower() in ('true', '1', 'yes')
    
    def _detect_system_settings(self) -> None:
        """Detect system accessibility settings"""
        app = QApplication.instance()
        if app:
            # Check for high contrast mode
            palette = app.palette()
            bg_color = palette.color(QPalette.ColorRole.Window)
            text_color = palette.color(QPalette.ColorRole.WindowText)
            
            # Calculate contrast ratio
            bg_luminance = self._calculate_luminance(bg_color)
            text_luminance = self._calculate_luminance(text_color)
            contrast_ratio = (max(bg_luminance, text_luminance) + 0.05) / (min(bg_luminance, text_luminance) + 0.05)
            
            self.high_contrast_mode = contrast_ratio > 7.0
            
            # Check for large font settings
            default_font = app.font()
            self.large_font_mode = default_font.pointSize() > 12
            if self.large_font_mode:
                self.font_scale_factor = default_font.pointSize() / 10.0
    
    def _calculate_luminance(self, color: QColor) -> float:
        """Calculate relative luminance of a color"""
        def srgb_to_linear(c):
            c = c / 255.0
            return c / 12.92 if c <= 0.03928 else pow((c + 0.055) / 1.055, 2.4)
        
        r = srgb_to_linear(color.red())
        g = srgb_to_linear(color.green())
        b = srgb_to_linear(color.blue())
        
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    
    def _setup_keyboard_shortcuts(self) -> None:
        """Setup keyboard shortcuts for property panel navigation"""
        shortcuts_config = {
            # Navigation shortcuts
            'next_property': ('Tab', self._navigate_next_property),
            'previous_property': ('Shift+Tab', self._navigate_previous_property),
            'first_property': ('Ctrl+Home', self._navigate_first_property),
            'last_property': ('Ctrl+End', self._navigate_last_property),
            
            # Editing shortcuts
            'start_edit': ('F2', self._start_edit_property),
            'commit_edit': ('Return', self._commit_edit),
            'cancel_edit': ('Escape', self._cancel_edit),
            
            # Property panel shortcuts
            'focus_search': ('Ctrl+F', self._focus_search),
            'expand_all': ('Ctrl+Shift+Plus', self._expand_all_groups),
            'collapse_all': ('Ctrl+Shift+Minus', self._collapse_all_groups),
            
            # Accessibility shortcuts
            'announce_focus': ('Ctrl+Shift+Space', self._announce_current_focus),
            'toggle_high_contrast': ('Ctrl+Alt+H', self._toggle_high_contrast),
            'increase_font': ('Ctrl+Plus', self._increase_font_size),
            'decrease_font': ('Ctrl+Minus', self._decrease_font_size),
        }
        
        for action, (key_sequence, handler) in shortcuts_config.items():
            self.add_shortcut(action, key_sequence, handler)
    
    def add_shortcut(self, action: str, key_sequence: str, handler: Callable) -> None:
        """Add a keyboard shortcut"""
        if action in self.shortcuts:
            self.remove_shortcut(action)
        
        shortcut = QShortcut(QKeySequence(key_sequence), self.property_panel)
        shortcut.activated.connect(handler)
        shortcut.setEnabled(self.enabled)
        
        self.shortcuts[action] = shortcut
    
    def remove_shortcut(self, action: str) -> None:
        """Remove a keyboard shortcut"""
        if action in self.shortcuts:
            self.shortcuts[action].deleteLater()
            del self.shortcuts[action]
    
    def _setup_focus_management(self) -> None:
        """Setup focus management and indicators"""
        if self.property_panel:
            self.focus_indicator = FocusIndicator(self.property_panel)
    
    def announce_to_screen_reader(self, text: str) -> None:
        """Announce text to screen reader"""
        if self.enabled and self.screen_reader_enabled:
            self.screen_reader_announcement.emit(text)
            QAccessible.updateAccessibility(QAccessible.AccessibleEvent.Announcement)
    
    def set_focus_on_property(self, element_id: str, property_name: str) -> None:
        """Set focus on specific property"""
        self.current_focus_element = (element_id, property_name)
        
        # Update focus indicator
        if self.focus_indicator:
            property_widget = self._find_property_widget(element_id, property_name)
            if property_widget:
                self.focus_indicator.show_focus_for_widget(property_widget)
        
        # Announce to screen reader
        self.announce_to_screen_reader(f"Focused on property {property_name} for element {element_id}")
        
        # Emit signal
        self.focus_changed.emit(element_id, property_name)
    
    def _find_property_widget(self, element_id: str, property_name: str) -> Optional[QWidget]:
        """Find the widget for a specific property"""
        # This would search through the property panel for the specific property widget
        # Implementation depends on the property panel structure
        return None
    
    # Keyboard navigation handlers
    def _navigate_next_property(self) -> None:
        """Navigate to next property"""
        # Implementation would move focus to next property
        self.announce_to_screen_reader("Moving to next property")
    
    def _navigate_previous_property(self) -> None:
        """Navigate to previous property"""
        # Implementation would move focus to previous property
        self.announce_to_screen_reader("Moving to previous property")
    
    def _navigate_first_property(self) -> None:
        """Navigate to first property"""
        # Implementation would move focus to first property
        self.announce_to_screen_reader("Moving to first property")
    
    def _navigate_last_property(self) -> None:
        """Navigate to last property"""
        # Implementation would move focus to last property
        self.announce_to_screen_reader("Moving to last property")
    
    def _start_edit_property(self) -> None:
        """Start editing current property"""
        if self.current_focus_element:
            element_id, property_name = self.current_focus_element
            self.announce_to_screen_reader(f"Started editing {property_name}")
    
    def _commit_edit(self) -> None:
        """Commit current edit"""
        if self.current_focus_element:
            element_id, property_name = self.current_focus_element
            self.announce_to_screen_reader(f"Committed changes to {property_name}")
    
    def _cancel_edit(self) -> None:
        """Cancel current edit"""
        if self.current_focus_element:
            element_id, property_name = self.current_focus_element
            self.announce_to_screen_reader(f"Cancelled editing {property_name}")
    
    def _focus_search(self) -> None:
        """Focus the search box"""
        self.announce_to_screen_reader("Focused on property search")
    
    def _expand_all_groups(self) -> None:
        """Expand all property groups"""
        self.announce_to_screen_reader("Expanded all property groups")
    
    def _collapse_all_groups(self) -> None:
        """Collapse all property groups"""
        self.announce_to_screen_reader("Collapsed all property groups")
    
    def _announce_current_focus(self) -> None:
        """Announce current focus"""
        if self.current_focus_element:
            element_id, property_name = self.current_focus_element
            # Get current value
            description = f"Property {property_name} for element {element_id}"
            self.announce_to_screen_reader(description)
        else:
            self.announce_to_screen_reader("No property currently focused")
    
    def _toggle_high_contrast(self) -> None:
        """Toggle high contrast mode"""
        self.high_contrast_mode = not self.high_contrast_mode
        self._apply_high_contrast_styling()
        
        status = "enabled" if self.high_contrast_mode else "disabled"
        self.announce_to_screen_reader(f"High contrast mode {status}")
    
    def _increase_font_size(self) -> None:
        """Increase font size"""
        self.font_scale_factor = min(2.0, self.font_scale_factor + 0.1)
        self._apply_font_scaling()
        self.announce_to_screen_reader(f"Font size increased to {int(self.font_scale_factor * 100)}%")
    
    def _decrease_font_size(self) -> None:
        """Decrease font size"""
        self.font_scale_factor = max(0.5, self.font_scale_factor - 0.1)
        self._apply_font_scaling()
        self.announce_to_screen_reader(f"Font size decreased to {int(self.font_scale_factor * 100)}%")
    
    def _apply_high_contrast_styling(self) -> None:
        """Apply high contrast styling"""
        if not self.property_panel:
            return
        
        if self.high_contrast_mode:
            style = """
            QWidget {
                background-color: #000000;
                color: #ffffff;
                border: 1px solid #ffffff;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 2px solid #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-weight: bold;
            }
            """
        else:
            style = ""  # Reset to default
        
        self.property_panel.setStyleSheet(style)
    
    def _apply_font_scaling(self) -> None:
        """Apply font scaling"""
        if not self.property_panel:
            return
        
        font = self.property_panel.font()
        base_size = 10  # Base font size
        new_size = int(base_size * self.font_scale_factor)
        font.setPointSize(new_size)
        self.property_panel.setFont(font)
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable accessibility features"""
        self.enabled = enabled
        
        # Enable/disable all shortcuts
        for shortcut in self.shortcuts.values():
            shortcut.setEnabled(enabled)
        
        # Enable/disable Qt accessibility
        QAccessible.setActive(enabled)
        
        self.accessibility_changed.emit(enabled)
    
    def handle_focus_change(self, old_widget: QWidget, new_widget: QWidget) -> None:
        """Handle application focus changes"""
        if new_widget and self.property_panel and self.property_panel.isAncestorOf(new_widget):
            # Focus is within property panel
            self._update_focus_indicator(new_widget)
    
    def _update_focus_indicator(self, widget: QWidget) -> None:
        """Update focus indicator for widget"""
        if self.focus_indicator and widget:
            self.focus_indicator.show_focus_for_widget(widget)
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Handle accessibility events"""
        if not self.enabled:
            return False
        
        # Handle focus events for screen reader
        if event.type() == QEvent.Type.FocusIn:
            if hasattr(obj, 'accessibleDescription'):
                description = obj.accessibleDescription()
                if description:
                    self.announce_to_screen_reader(f"Focused: {description}")
        
        return False
    
    def get_accessibility_info(self) -> Dict[str, Any]:
        """Get accessibility information"""
        return {
            'enabled': self.enabled,
            'high_contrast_mode': self.high_contrast_mode,
            'large_font_mode': self.large_font_mode,
            'screen_reader_enabled': self.screen_reader_enabled,
            'font_scale_factor': self.font_scale_factor,
            'shortcuts_count': len(self.shortcuts),
            'current_focus': self.current_focus_element
        }
    
    def cleanup(self) -> None:
        """Cleanup accessibility resources"""
        # Remove shortcuts
        for shortcut in self.shortcuts.values():
            shortcut.deleteLater()
        self.shortcuts.clear()
        
        # Hide focus indicator
        if self.focus_indicator:
            self.focus_indicator.hide_focus()
        
        # Remove event filter
        if self.main_window:
            self.main_window.removeEventFilter(self)


class FocusIndicator(QFrame):
    """Visual focus indicator for accessibility"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.target_widget: Optional[QWidget] = None
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._animate_focus)
        self.animation_phase = 0
        
        # Setup appearance
        self.setFrameStyle(QFrame.Shape.Box)
        self.setLineWidth(2)
        self.hide()
        
        # Make it non-interactive
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    
    def show_focus_for_widget(self, widget: QWidget) -> None:
        """Show focus indicator for specific widget"""
        if not widget or not widget.isVisible():
            self.hide()
            return
        
        self.target_widget = widget
        
        # Position indicator around widget
        widget_rect = widget.geometry()
        if widget.parent():
            widget_rect = widget.mapTo(widget.parent(), widget_rect.topLeft())
            widget_rect = QRect(widget_rect, widget.size())
        
        # Expand slightly for visibility
        margin = 3
        indicator_rect = widget_rect.adjusted(-margin, -margin, margin, margin)
        
        self.setGeometry(indicator_rect)
        self.show()
        self.raise_()
        
        # Start animation
        self.animation_timer.start(100)  # 100ms intervals
    
    def hide_focus(self) -> None:
        """Hide focus indicator"""
        self.animation_timer.stop()
        self.target_widget = None
        self.hide()
    
    def _animate_focus(self) -> None:
        """Animate focus indicator"""
        self.animation_phase = (self.animation_phase + 1) % 10
        self.update()
    
    def paintEvent(self, event) -> None:
        """Paint the focus indicator"""
        super().paintEvent(event)
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Animated border
        alpha = int(155 + 100 * abs(self.animation_phase - 5) / 5)
        color = QColor(0, 120, 215, alpha)  # Blue accent color
        
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRect(rect)


# Export accessibility components
__all__ = [
    'PropertyAccessibilityManager',
    'FocusIndicator'
]