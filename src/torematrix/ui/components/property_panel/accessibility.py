"""Accessibility features and keyboard shortcuts for property panel"""

from typing import Dict, List, Any, Optional, Callable
from PyQt6.QtWidgets import (
    QWidget, QApplication, QLabel, QFrame, QVBoxLayout,
    QHBoxLayout, QToolTip, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QEvent, QTimer, QRect
from PyQt6.QtGui import (
    QKeySequence, QAction, QFont, QFontMetrics, QPalette, QColor,
    QAccessible, QPainter, QPen, QShortcut
)
from PyQt6.QtAccessibility import QAccessibleInterface

from .models import PropertyMetadata
from .events import PropertyNotificationCenter


class AccessibilityManager(QObject):
    """Manages accessibility features for the property panel"""
    
    # Signals
    accessibility_changed = pyqtSignal(bool)  # enabled state
    screen_reader_announcement = pyqtSignal(str)  # text to announce
    focus_changed = pyqtSignal(str, str)  # element_id, property_name
    
    def __init__(self, notification_center: PropertyNotificationCenter):
        super().__init__()
        self.notification_center = notification_center
        self.enabled = True
        self.high_contrast_mode = False
        self.large_font_mode = False
        self.screen_reader_enabled = False
        
        # Accessibility settings
        self.font_scale_factor = 1.0
        self.contrast_ratio = 1.0
        self.animation_enabled = True
        self.tooltip_delay = 500
        
        # Detect system accessibility settings
        self._detect_system_settings()
        
        # Setup accessibility features
        self._setup_accessibility()
    
    def _detect_system_settings(self) -> None:
        """Detect system accessibility settings"""
        app = QApplication.instance()
        if app:
            # Check for high contrast mode
            palette = app.palette()
            bg_color = palette.color(QPalette.ColorRole.Window)
            text_color = palette.color(QPalette.ColorRole.WindowText)
            
            # Simple contrast detection
            bg_luminance = self._calculate_luminance(bg_color)
            text_luminance = self._calculate_luminance(text_color)
            contrast_ratio = (max(bg_luminance, text_luminance) + 0.05) / (min(bg_luminance, text_luminance) + 0.05)
            
            self.high_contrast_mode = contrast_ratio > 7.0
            self.contrast_ratio = contrast_ratio
            
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
    
    def _setup_accessibility(self) -> None:
        """Setup accessibility features"""
        # Enable accessibility by default
        QAccessible.setActive(True)
        
        # Register for accessibility events
        app = QApplication.instance()
        if app:
            app.installEventFilter(self)
    
    def enable_accessibility(self, enabled: bool) -> None:
        """Enable or disable accessibility features"""
        self.enabled = enabled
        QAccessible.setActive(enabled)
        self.accessibility_changed.emit(enabled)
    
    def set_high_contrast_mode(self, enabled: bool) -> None:
        """Enable or disable high contrast mode"""
        self.high_contrast_mode = enabled
        # Apply high contrast styling to property panel
        self._apply_high_contrast_styling()
    
    def set_large_font_mode(self, enabled: bool, scale_factor: float = 1.5) -> None:
        """Enable or disable large font mode"""
        self.large_font_mode = enabled
        self.font_scale_factor = scale_factor if enabled else 1.0
        self._apply_font_scaling()
    
    def announce_to_screen_reader(self, text: str) -> None:
        """Announce text to screen reader"""
        if self.enabled and self.screen_reader_enabled:
            self.screen_reader_announcement.emit(text)
            # Use QAccessible to announce
            QAccessible.updateAccessibility(QAccessible.AccessibleEvent.Announcement)
    
    def set_focus_description(self, widget: QWidget, description: str) -> None:
        """Set accessibility description for focused widget"""
        if self.enabled:
            widget.setAccessibleDescription(description)
    
    def _apply_high_contrast_styling(self) -> None:
        """Apply high contrast styling"""
        if not self.high_contrast_mode:
            return
        
        # This would apply high contrast styles to property panel components
        # Implementation would depend on specific styling system
        pass
    
    def _apply_font_scaling(self) -> None:
        """Apply font scaling"""
        if not self.large_font_mode:
            return
        
        app = QApplication.instance()
        if app:
            font = app.font()
            font.setPointSizeF(font.pointSizeF() * self.font_scale_factor)
            app.setFont(font)
    
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


class KeyboardShortcutManager(QObject):
    """Manages keyboard shortcuts for property panel navigation and editing"""
    
    # Signals
    shortcut_activated = pyqtSignal(str, str)  # action, context
    navigation_requested = pyqtSignal(str)  # direction: up, down, left, right
    editing_requested = pyqtSignal(str)  # action: start, commit, cancel
    
    def __init__(self, parent_widget: QWidget):
        super().__init__(parent_widget)
        self.parent_widget = parent_widget
        self.shortcuts: Dict[str, QShortcut] = {}
        self.enabled = True
        
        # Setup default shortcuts
        self._setup_default_shortcuts()
    
    def _setup_default_shortcuts(self) -> None:
        """Setup default keyboard shortcuts"""
        shortcuts_config = {
            # Navigation shortcuts
            'next_property': ('Tab', self._next_property),
            'previous_property': ('Shift+Tab', self._previous_property),
            'first_property': ('Ctrl+Home', self._first_property),
            'last_property': ('Ctrl+End', self._last_property),
            
            # Editing shortcuts
            'start_edit': ('F2', self._start_edit),
            'commit_edit': ('Return', self._commit_edit),
            'cancel_edit': ('Escape', self._cancel_edit),
            'delete_value': ('Delete', self._delete_value),
            
            # Property panel shortcuts
            'toggle_panel': ('F4', self._toggle_panel),
            'focus_search': ('Ctrl+F', self._focus_search),
            'expand_all': ('Ctrl+Shift+Plus', self._expand_all),
            'collapse_all': ('Ctrl+Shift+Minus', self._collapse_all),
            
            # Selection shortcuts
            'select_all': ('Ctrl+A', self._select_all),
            'copy_value': ('Ctrl+C', self._copy_value),
            'paste_value': ('Ctrl+V', self._paste_value),
            'cut_value': ('Ctrl+X', self._cut_value),
            
            # Batch editing shortcuts
            'batch_edit': ('Ctrl+B', self._batch_edit),
            'apply_batch': ('Ctrl+Shift+Return', self._apply_batch),
            
            # Help and accessibility
            'show_help': ('F1', self._show_help),
            'announce_focus': ('Ctrl+Shift+Space', self._announce_focus),
        }
        
        for action, (key_sequence, handler) in shortcuts_config.items():
            self.add_shortcut(action, key_sequence, handler)
    
    def add_shortcut(self, action: str, key_sequence: str, handler: Callable) -> None:
        """Add a keyboard shortcut"""
        if action in self.shortcuts:
            self.remove_shortcut(action)
        
        shortcut = QShortcut(QKeySequence(key_sequence), self.parent_widget)
        shortcut.activated.connect(lambda: self._handle_shortcut(action, handler))
        shortcut.setEnabled(self.enabled)
        
        self.shortcuts[action] = shortcut
    
    def remove_shortcut(self, action: str) -> None:
        """Remove a keyboard shortcut"""
        if action in self.shortcuts:
            self.shortcuts[action].deleteLater()
            del self.shortcuts[action]
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable all shortcuts"""
        self.enabled = enabled
        for shortcut in self.shortcuts.values():
            shortcut.setEnabled(enabled)
    
    def get_shortcut_help(self) -> Dict[str, str]:
        """Get help text for all shortcuts"""
        help_text = {
            'next_property': 'Move to next property',
            'previous_property': 'Move to previous property',
            'first_property': 'Move to first property',
            'last_property': 'Move to last property',
            'start_edit': 'Start editing selected property',
            'commit_edit': 'Commit current edit',
            'cancel_edit': 'Cancel current edit',
            'delete_value': 'Delete property value',
            'toggle_panel': 'Show/hide property panel',
            'focus_search': 'Focus property search box',
            'expand_all': 'Expand all property groups',
            'collapse_all': 'Collapse all property groups',
            'select_all': 'Select all properties',
            'copy_value': 'Copy property value',
            'paste_value': 'Paste property value',
            'cut_value': 'Cut property value',
            'batch_edit': 'Start batch editing mode',
            'apply_batch': 'Apply batch changes',
            'show_help': 'Show keyboard shortcuts help',
            'announce_focus': 'Announce focused element to screen reader',
        }
        
        result = {}
        for action, shortcut in self.shortcuts.items():
            key_sequence = shortcut.key().toString()
            description = help_text.get(action, action.replace('_', ' ').title())
            result[key_sequence] = description
        
        return result
    
    def _handle_shortcut(self, action: str, handler: Callable) -> None:
        """Handle shortcut activation"""
        if self.enabled:
            try:
                handler()
                self.shortcut_activated.emit(action, 'property_panel')
            except Exception as e:
                print(f"Error handling shortcut {action}: {e}")
    
    # Shortcut handlers
    def _next_property(self) -> None:
        self.navigation_requested.emit('next')
    
    def _previous_property(self) -> None:
        self.navigation_requested.emit('previous')
    
    def _first_property(self) -> None:
        self.navigation_requested.emit('first')
    
    def _last_property(self) -> None:
        self.navigation_requested.emit('last')
    
    def _start_edit(self) -> None:
        self.editing_requested.emit('start')
    
    def _commit_edit(self) -> None:
        self.editing_requested.emit('commit')
    
    def _cancel_edit(self) -> None:
        self.editing_requested.emit('cancel')
    
    def _delete_value(self) -> None:
        self.editing_requested.emit('delete')
    
    def _toggle_panel(self) -> None:
        self.shortcut_activated.emit('toggle_panel', 'main')
    
    def _focus_search(self) -> None:
        self.shortcut_activated.emit('focus_search', 'search')
    
    def _expand_all(self) -> None:
        self.shortcut_activated.emit('expand_all', 'navigation')
    
    def _collapse_all(self) -> None:
        self.shortcut_activated.emit('collapse_all', 'navigation')
    
    def _select_all(self) -> None:
        self.shortcut_activated.emit('select_all', 'selection')
    
    def _copy_value(self) -> None:
        self.shortcut_activated.emit('copy_value', 'clipboard')
    
    def _paste_value(self) -> None:
        self.shortcut_activated.emit('paste_value', 'clipboard')
    
    def _cut_value(self) -> None:
        self.shortcut_activated.emit('cut_value', 'clipboard')
    
    def _batch_edit(self) -> None:
        self.shortcut_activated.emit('batch_edit', 'editing')
    
    def _apply_batch(self) -> None:
        self.shortcut_activated.emit('apply_batch', 'editing')
    
    def _show_help(self) -> None:
        self.shortcut_activated.emit('show_help', 'help')
    
    def _announce_focus(self) -> None:
        self.shortcut_activated.emit('announce_focus', 'accessibility')


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
        color = QColor(0, 120, 215, alpha)  # Windows accent color
        
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.drawRect(rect)


class ScreenReaderSupport(QObject):
    """Enhanced screen reader support for property panel"""
    
    def __init__(self, accessibility_manager: AccessibilityManager):
        super().__init__()
        self.accessibility_manager = accessibility_manager
        self.current_context: Dict[str, Any] = {}
        self.announcement_queue: List[str] = []
        self.announcement_timer = QTimer()
        self.announcement_timer.timeout.connect(self._process_announcement_queue)
        
    def announce_property_change(self, element_id: str, property_name: str, 
                                old_value: Any, new_value: Any) -> None:
        """Announce property value change to screen reader"""
        message = f"Property {property_name} changed from {old_value} to {new_value}"
        self._queue_announcement(message)
    
    def announce_selection_change(self, element_ids: List[str], 
                                property_names: List[str]) -> None:
        """Announce selection change"""
        if len(element_ids) == 1:
            message = f"Selected element with {len(property_names)} properties"
        else:
            message = f"Selected {len(element_ids)} elements with {len(property_names)} common properties"
        
        self._queue_announcement(message)
    
    def announce_navigation(self, direction: str, current_property: str) -> None:
        """Announce navigation action"""
        message = f"Moved {direction} to property {current_property}"
        self._queue_announcement(message)
    
    def announce_editing_state(self, state: str, property_name: str) -> None:
        """Announce editing state change"""
        state_messages = {
            'start': f"Started editing {property_name}",
            'commit': f"Committed changes to {property_name}",
            'cancel': f"Cancelled editing {property_name}"
        }
        
        message = state_messages.get(state, f"Editing state {state} for {property_name}")
        self._queue_announcement(message)
    
    def announce_batch_operation(self, operation_type: str, count: int) -> None:
        """Announce batch operation"""
        message = f"Batch {operation_type} operation on {count} elements"
        self._queue_announcement(message)
    
    def set_context(self, context: Dict[str, Any]) -> None:
        """Set current context for screen reader"""
        self.current_context = context
    
    def get_context_description(self) -> str:
        """Get description of current context"""
        if not self.current_context:
            return "Property panel"
        
        element_count = self.current_context.get('element_count', 0)
        property_count = self.current_context.get('property_count', 0)
        current_property = self.current_context.get('current_property', '')
        
        description = f"Property panel with {element_count} elements, {property_count} properties"
        if current_property:
            description += f", focused on {current_property}"
        
        return description
    
    def _queue_announcement(self, message: str) -> None:
        """Queue announcement for screen reader"""
        self.announcement_queue.append(message)
        
        # Start processing if not already running
        if not self.announcement_timer.isActive():
            self.announcement_timer.start(500)  # 500ms delay between announcements
    
    def _process_announcement_queue(self) -> None:
        """Process queued announcements"""
        if self.announcement_queue:
            message = self.announcement_queue.pop(0)
            self.accessibility_manager.announce_to_screen_reader(message)
        
        # Continue processing if more announcements
        if not self.announcement_queue:
            self.announcement_timer.stop()


class AccessiblePropertyWidget(QWidget):
    """Base widget with enhanced accessibility features"""
    
    def __init__(self, property_metadata: PropertyMetadata, parent=None):
        super().__init__(parent)
        self.property_metadata = property_metadata
        self.accessibility_manager: Optional[AccessibilityManager] = None
        self.focus_indicator: Optional[FocusIndicator] = None
        
        # Setup accessibility attributes
        self._setup_accessibility_attributes()
    
    def _setup_accessibility_attributes(self) -> None:
        """Setup accessibility attributes"""
        # Set accessible name and description
        self.setAccessibleName(self.property_metadata.display_name)
        self.setAccessibleDescription(self.property_metadata.description)
        
        # Set role
        self.setProperty('accessibleRole', 'property_editor')
        
        # Enable focus
        self.setFocusPolicy(Qt.FocusPolicy.TabFocus)
    
    def set_accessibility_manager(self, manager: AccessibilityManager) -> None:
        """Set accessibility manager"""
        self.accessibility_manager = manager
    
    def focusInEvent(self, event) -> None:
        """Handle focus in event"""
        super().focusInEvent(event)
        
        if self.accessibility_manager:
            # Show focus indicator
            if not self.focus_indicator:
                self.focus_indicator = FocusIndicator(self.parent())
            
            self.focus_indicator.show_focus_for_widget(self)
            
            # Announce focus
            description = self.get_detailed_description()
            self.accessibility_manager.announce_to_screen_reader(description)
    
    def focusOutEvent(self, event) -> None:
        """Handle focus out event"""
        super().focusOutEvent(event)
        
        if self.focus_indicator:
            self.focus_indicator.hide_focus()
    
    def get_detailed_description(self) -> str:
        """Get detailed accessibility description"""
        description = f"Property {self.property_metadata.display_name}"
        
        if self.property_metadata.description:
            description += f", {self.property_metadata.description}"
        
        # Add value information
        if hasattr(self, 'get_value'):
            try:
                value = self.get_value()
                description += f", current value: {value}"
            except:
                pass
        
        return description


# Export accessibility components
__all__ = [
    'AccessibilityManager',
    'KeyboardShortcutManager',
    'FocusIndicator',
    'ScreenReaderSupport',
    'AccessiblePropertyWidget'
]
