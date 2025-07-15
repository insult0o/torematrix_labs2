"""Accessibility features and keyboard navigation support for inline editors"""

from typing import Dict, Any, List, Optional, Callable
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QShortcut, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import (
    QKeySequence, QAccessible, QAccessibleEvent, QFont, QPalette, 
    QAccessibleInterface, QAction
)
import platform
import sys


class AccessibilityFeatures:
    """Enumeration of accessibility features"""
    
    SCREEN_READER = "screen_reader"
    HIGH_CONTRAST = "high_contrast"
    LARGE_FONT = "large_font"
    KEYBOARD_NAVIGATION = "keyboard_navigation"
    VOICE_COMMANDS = "voice_commands"
    MAGNIFICATION = "magnification"
    REDUCED_MOTION = "reduced_motion"


class AccessibilitySettings:
    """Container for accessibility settings and preferences"""
    
    def __init__(self):
        # Detection results
        self.screen_reader_enabled = self._detect_screen_reader()
        self.high_contrast_enabled = self._detect_high_contrast()
        self.large_font_enabled = self._detect_large_font()
        self.reduced_motion_enabled = self._detect_reduced_motion()
        
        # Manual overrides
        self.keyboard_navigation_enabled = True
        self.voice_commands_enabled = False
        self.magnification_enabled = False
        self.custom_shortcuts_enabled = True
        
        # Visual settings
        self.contrast_ratio = 4.5  # WCAG AA standard
        self.font_scale_factor = 1.0
        self.focus_indicator_width = 2
        self.animation_duration_ms = 200
        
        # Audio settings
        self.audio_feedback_enabled = False
        self.audio_volume = 0.5
        
        # Timing settings
        self.keyboard_repeat_delay = 500
        self.double_click_time = 500
        self.focus_timeout = 5000
    
    def _detect_screen_reader(self) -> bool:
        """Detect if screen reader is active"""
        try:
            # Check Qt accessibility
            if hasattr(QAccessible, 'isActive'):
                if QAccessible.isActive():
                    return True
            
            # Platform-specific detection
            if platform.system() == "Windows":
                try:
                    import winreg
                    # Check for NVDA, JAWS, etc.
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                       r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\AccessibilityTemp")
                    return True
                except (ImportError, OSError):
                    pass
            
            elif platform.system() == "Darwin":  # macOS
                try:
                    import subprocess
                    result = subprocess.run(['defaults', 'read', 'com.apple.universalaccess', 'voiceOverOnOffKey'],
                                          capture_output=True, text=True)
                    return result.returncode == 0
                except Exception:
                    pass
            
            elif platform.system() == "Linux":
                try:
                    import subprocess
                    # Check for Orca screen reader
                    result = subprocess.run(['pgrep', 'orca'], capture_output=True)
                    return result.returncode == 0
                except Exception:
                    pass
            
            return False
        except Exception:
            return False
    
    def _detect_high_contrast(self) -> bool:
        """Detect if high contrast mode is enabled"""
        try:
            app = QApplication.instance()
            if app:
                palette = app.palette()
                # Simple contrast detection based on color values
                bg = palette.color(QPalette.ColorRole.Window)
                fg = palette.color(QPalette.ColorRole.WindowText)
                
                # Calculate luminance contrast
                bg_lum = self._calculate_luminance(bg.red(), bg.green(), bg.blue())
                fg_lum = self._calculate_luminance(fg.red(), fg.green(), fg.blue())
                
                contrast_ratio = (max(bg_lum, fg_lum) + 0.05) / (min(bg_lum, fg_lum) + 0.05)
                return contrast_ratio > 7.0  # WCAG AAA standard
            
            return False
        except Exception:
            return False
    
    def _calculate_luminance(self, r: int, g: int, b: int) -> float:
        """Calculate relative luminance of a color"""
        def linearize(c):
            c = c / 255.0
            return c / 12.92 if c <= 0.03928 else pow((c + 0.055) / 1.055, 2.4)
        
        return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)
    
    def _detect_large_font(self) -> bool:
        """Detect if large font/scaling is enabled"""
        try:
            app = QApplication.instance()
            if app:
                font = app.font()
                default_size = 9  # Typical default
                return font.pointSize() > default_size * 1.2
            return False
        except Exception:
            return False
    
    def _detect_reduced_motion(self) -> bool:
        """Detect if reduced motion is preferred"""
        try:
            # This would check system settings for reduced motion preference
            # Implementation varies by platform
            return False
        except Exception:
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary"""
        return {
            'screen_reader_enabled': self.screen_reader_enabled,
            'high_contrast_enabled': self.high_contrast_enabled,
            'large_font_enabled': self.large_font_enabled,
            'reduced_motion_enabled': self.reduced_motion_enabled,
            'keyboard_navigation_enabled': self.keyboard_navigation_enabled,
            'voice_commands_enabled': self.voice_commands_enabled,
            'magnification_enabled': self.magnification_enabled,
            'custom_shortcuts_enabled': self.custom_shortcuts_enabled,
            'contrast_ratio': self.contrast_ratio,
            'font_scale_factor': self.font_scale_factor,
            'focus_indicator_width': self.focus_indicator_width,
            'animation_duration_ms': self.animation_duration_ms,
            'audio_feedback_enabled': self.audio_feedback_enabled,
            'audio_volume': self.audio_volume,
            'keyboard_repeat_delay': self.keyboard_repeat_delay,
            'double_click_time': self.double_click_time,
            'focus_timeout': self.focus_timeout
        }


class AccessibilityManager(QObject):
    """Main accessibility manager for inline editors
    
    Features:
    - Automatic accessibility detection
    - Screen reader compatibility
    - Keyboard navigation enhancement
    - High contrast mode support
    - ARIA label management
    - Focus management
    - Audio feedback
    """
    
    # Signals
    accessibility_changed = pyqtSignal(str, bool)  # feature, enabled
    focus_changed = pyqtSignal(QWidget)  # widget
    screen_reader_announcement = pyqtSignal(str)  # message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.settings = AccessibilitySettings()
        self.managed_widgets: Dict[QWidget, Dict[str, Any]] = {}
        self.shortcuts: Dict[str, QShortcut] = {}
        self.focus_history: List[QWidget] = []
        self.current_focus: Optional[QWidget] = None
        
        # Focus management timer
        self.focus_timer = QTimer()
        self.focus_timer.setSingleShot(True)
        self.focus_timer.timeout.connect(self._on_focus_timeout)
        
        # Setup global shortcuts
        self._setup_global_shortcuts()
        
        # Connect to Qt accessibility system
        if hasattr(QAccessible, 'updateAccessibility'):
            self._accessibility_active = True
        else:
            self._accessibility_active = False
    
    def setup_accessibility(self, widget: QWidget, config: Optional[Dict[str, Any]] = None):
        """Setup accessibility features for a widget
        
        Args:
            widget: Widget to make accessible
            config: Configuration options
        """
        if not isinstance(widget, QWidget):
            return
        
        config = config or {}
        
        # Store widget configuration
        self.managed_widgets[widget] = {
            'config': config,
            'original_style': widget.styleSheet(),
            'shortcuts': [],
            'aria_properties': {}
        }
        
        # Set accessible properties
        self._setup_accessible_properties(widget, config)
        
        # Setup keyboard navigation
        if self.settings.keyboard_navigation_enabled:
            self._setup_keyboard_navigation(widget, config)
        
        # Apply visual accessibility
        if self.settings.high_contrast_enabled:
            self._apply_high_contrast(widget)
        
        if self.settings.large_font_enabled:
            self._apply_large_font(widget)
        
        # Setup screen reader support
        if self.settings.screen_reader_enabled:
            self._setup_screen_reader_support(widget, config)
        
        # Setup focus management
        self._setup_focus_management(widget)
        
        # Connect widget events
        widget.installEventFilter(self)
    
    def _setup_accessible_properties(self, widget: QWidget, config: Dict[str, Any]):
        """Setup accessible properties for widget"""
        # Set accessible name
        accessible_name = config.get('accessible_name', widget.objectName() or 'Editor')
        widget.setAccessibleName(accessible_name)
        
        # Set accessible description
        description = config.get('accessible_description', 
                               'Inline text editor for document elements. Use Tab to navigate, F2 to edit, Escape to cancel.')
        widget.setAccessibleDescription(description)
        
        # Set ARIA role equivalent
        role = config.get('role', 'textbox')
        self.managed_widgets[widget]['aria_properties']['role'] = role
        
        # Set other ARIA properties
        aria_props = config.get('aria_properties', {})
        self.managed_widgets[widget]['aria_properties'].update(aria_props)
    
    def _setup_keyboard_navigation(self, widget: QWidget, config: Dict[str, Any]):
        """Setup keyboard navigation for widget"""
        # Ensure widget can receive focus
        widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Setup custom shortcuts
        shortcuts = config.get('shortcuts', {})
        
        # Default accessibility shortcuts
        default_shortcuts = {
            'Alt+H': lambda: self.announce_help(widget),
            'Alt+D': lambda: self.announce_description(widget),
            'Alt+S': lambda: self.announce_state(widget),
            'F1': lambda: self.show_help(widget)
        }
        
        # Combine shortcuts
        all_shortcuts = {**default_shortcuts, **shortcuts}
        
        # Create QShortcut objects
        widget_shortcuts = []
        for key_sequence, callback in all_shortcuts.items():
            shortcut = QShortcut(QKeySequence(key_sequence), widget)
            shortcut.activated.connect(callback)
            widget_shortcuts.append(shortcut)
        
        self.managed_widgets[widget]['shortcuts'] = widget_shortcuts
    
    def _apply_high_contrast(self, widget: QWidget):
        """Apply high contrast styling to widget"""
        high_contrast_style = f"""
        QWidget {{
            background-color: black;
            color: white;
            border: {self.settings.focus_indicator_width}px solid white;
            font-weight: bold;
        }}
        QWidget:focus {{
            border: {self.settings.focus_indicator_width + 1}px solid yellow;
            background-color: #000080;
        }}
        QWidget:hover {{
            background-color: #333333;
        }}
        QWidget:disabled {{
            background-color: #404040;
            color: #808080;
        }}
        """
        
        # Merge with existing styles
        existing_style = widget.styleSheet()
        widget.setStyleSheet(existing_style + high_contrast_style)
    
    def _apply_large_font(self, widget: QWidget):
        """Apply large font scaling to widget"""
        font = widget.font()
        current_size = font.pointSize()
        
        if current_size > 0:
            new_size = int(current_size * self.settings.font_scale_factor)
            font.setPointSize(max(new_size, 12))  # Minimum 12pt
        else:
            font.setPointSize(14)  # Default large size
        
        font.setBold(True)  # Bold for better readability
        widget.setFont(font)
    
    def _setup_screen_reader_support(self, widget: QWidget, config: Dict[str, Any]):
        """Setup screen reader specific features"""
        # Connect to widget signals for announcements
        if hasattr(widget, 'textChanged'):
            widget.textChanged.connect(
                lambda: self._announce_delayed("Text changed", 500)
            )
        
        if hasattr(widget, 'editing_started'):
            widget.editing_started.connect(
                lambda: self.announce("Editing started")
            )
        
        if hasattr(widget, 'editing_finished'):
            widget.editing_finished.connect(
                lambda success: self.announce(
                    "Editing completed" if success else "Editing cancelled"
                )
            )
        
        if hasattr(widget, 'validation_failed'):
            widget.validation_failed.connect(
                lambda msg: self.announce(f"Validation error: {msg}")
            )
    
    def _setup_focus_management(self, widget: QWidget):
        """Setup focus management for widget"""
        # Enhanced focus handling will be done via event filter
        pass
    
    def _setup_global_shortcuts(self):
        """Setup global accessibility shortcuts"""
        if not self.settings.custom_shortcuts_enabled:
            return
        
        # Global shortcuts (these work across the application)
        global_shortcuts = {
            'Ctrl+Alt+A': self.toggle_accessibility_mode,
            'Ctrl+Alt+C': self.toggle_high_contrast,
            'Ctrl+Alt+F': self.cycle_focus,
            'Ctrl+Alt+H': self.announce_current_focus,
            'Ctrl+Alt+R': self.refresh_accessibility
        }
        
        for key_sequence, callback in global_shortcuts.items():
            shortcut = QShortcut(QKeySequence(key_sequence), None)  # Global
            shortcut.activated.connect(callback)
            self.shortcuts[key_sequence] = shortcut
    
    def eventFilter(self, obj: QObject, event) -> bool:
        """Handle events for accessibility features"""
        if not isinstance(obj, QWidget) or obj not in self.managed_widgets:
            return False
        
        event_type = event.type()
        
        # Focus events
        if event_type == event.Type.FocusIn:
            self._on_focus_in(obj)
        elif event_type == event.Type.FocusOut:
            self._on_focus_out(obj)
        
        # Mouse events for screen reader users
        elif event_type == event.Type.Enter:
            if self.settings.screen_reader_enabled:
                self.announce_widget_info(obj)
        
        # Key events for enhanced navigation
        elif event_type == event.Type.KeyPress:
            return self._handle_accessibility_key_press(obj, event)
        
        return False
    
    def _on_focus_in(self, widget: QWidget):
        """Handle widget receiving focus"""
        self.current_focus = widget
        self.focus_history.append(widget)
        
        # Limit focus history
        if len(self.focus_history) > 10:
            self.focus_history.pop(0)
        
        # Announce focus change to screen readers
        if self.settings.screen_reader_enabled:
            self.announce_widget_info(widget)
        
        # Start focus timeout
        if self.settings.focus_timeout > 0:
            self.focus_timer.start(self.settings.focus_timeout)
        
        self.focus_changed.emit(widget)
    
    def _on_focus_out(self, widget: QWidget):
        """Handle widget losing focus"""
        if self.current_focus == widget:
            self.current_focus = None
        
        # Stop focus timeout
        self.focus_timer.stop()
    
    def _on_focus_timeout(self):
        """Handle focus timeout"""
        if self.current_focus and self.settings.screen_reader_enabled:
            self.announce("Focus timeout - press Tab to continue navigation")
    
    def _handle_accessibility_key_press(self, widget: QWidget, event) -> bool:
        """Handle accessibility-specific key presses"""
        key = event.key()
        modifiers = event.modifiers()
        
        # Enhanced Tab navigation
        if key == Qt.Key.Key_Tab:
            if modifiers & Qt.KeyboardModifier.ShiftModifier:
                self._navigate_previous(widget)
            else:
                self._navigate_next(widget)
            return True
        
        # Home/End for quick navigation
        elif key == Qt.Key.Key_Home and modifiers & Qt.KeyboardModifier.ControlModifier:
            self._navigate_to_first()
            return True
        elif key == Qt.Key.Key_End and modifiers & Qt.KeyboardModifier.ControlModifier:
            self._navigate_to_last()
            return True
        
        return False
    
    def _navigate_next(self, current_widget: QWidget):
        """Navigate to next accessible widget"""
        # Find next widget in tab order
        next_widget = current_widget.nextInFocusChain()
        if next_widget and next_widget != current_widget:
            next_widget.setFocus()
    
    def _navigate_previous(self, current_widget: QWidget):
        """Navigate to previous accessible widget"""
        # Find previous widget in tab order
        prev_widget = current_widget.previousInFocusChain()
        if prev_widget and prev_widget != current_widget:
            prev_widget.setFocus()
    
    def _navigate_to_first(self):
        """Navigate to first accessible widget"""
        if self.managed_widgets:
            first_widget = next(iter(self.managed_widgets.keys()))
            first_widget.setFocus()
    
    def _navigate_to_last(self):
        """Navigate to last accessible widget"""
        if self.managed_widgets:
            last_widget = list(self.managed_widgets.keys())[-1]
            last_widget.setFocus()
    
    # Public API methods
    
    def announce(self, message: str, priority: str = 'polite'):
        """Announce message to screen readers
        
        Args:
            message: Message to announce
            priority: Announcement priority ('polite' or 'assertive')
        """
        if not self.settings.screen_reader_enabled:
            return
        
        try:
            if self._accessibility_active:
                # Use Qt accessibility system
                event_type = QAccessible.Event.Alert
                event = QAccessibleEvent(event_type, 0)
                event.setText(message)
                QAccessible.updateAccessibility(event)
            
            self.screen_reader_announcement.emit(message)
            
        except Exception:
            # Fallback - just emit signal
            self.screen_reader_announcement.emit(message)
    
    def _announce_delayed(self, message: str, delay_ms: int):
        """Announce message after delay"""
        QTimer.singleShot(delay_ms, lambda: self.announce(message))
    
    def announce_widget_info(self, widget: QWidget):
        """Announce information about a widget"""
        if not self.settings.screen_reader_enabled:
            return
        
        name = widget.accessibleName() or widget.objectName() or "Widget"
        description = widget.accessibleDescription() or ""
        
        # Get widget state
        state_info = []
        if hasattr(widget, 'is_editing') and widget.is_editing():
            state_info.append("editing")
        if not widget.isEnabled():
            state_info.append("disabled")
        if widget.isReadOnly() if hasattr(widget, 'isReadOnly') else False:
            state_info.append("read only")
        
        # Build announcement
        announcement_parts = [name]
        if description:
            announcement_parts.append(description)
        if state_info:
            announcement_parts.append(", ".join(state_info))
        
        self.announce(". ".join(announcement_parts))
    
    def announce_help(self, widget: QWidget):
        """Announce help for widget"""
        help_text = self._get_widget_help(widget)
        self.announce(f"Help: {help_text}")
    
    def announce_description(self, widget: QWidget):
        """Announce description for widget"""
        description = widget.accessibleDescription()
        if description:
            self.announce(f"Description: {description}")
        else:
            self.announce("No description available")
    
    def announce_state(self, widget: QWidget):
        """Announce current state of widget"""
        state_parts = []
        
        if hasattr(widget, 'is_editing'):
            state_parts.append("editing" if widget.is_editing() else "not editing")
        
        if hasattr(widget, 'is_dirty'):
            state_parts.append("modified" if widget.is_dirty() else "unmodified")
        
        if not widget.isEnabled():
            state_parts.append("disabled")
        
        if hasattr(widget, 'isReadOnly') and widget.isReadOnly():
            state_parts.append("read only")
        
        state_text = ", ".join(state_parts) if state_parts else "normal"
        self.announce(f"State: {state_text}")
    
    def show_help(self, widget: QWidget):
        """Show help dialog for widget"""
        # This would show a help dialog
        # For now, just announce help
        self.announce_help(widget)
    
    def _get_widget_help(self, widget: QWidget) -> str:
        """Get help text for widget"""
        if widget in self.managed_widgets:
            config = self.managed_widgets[widget]['config']
            return config.get('help_text', 'Use Tab to navigate, F2 to edit, Escape to cancel')
        return 'No help available'
    
    # Global accessibility methods
    
    def toggle_accessibility_mode(self):
        """Toggle enhanced accessibility mode"""
        # This would toggle various accessibility features
        self.announce("Accessibility mode toggled")
    
    def toggle_high_contrast(self):
        """Toggle high contrast mode"""
        self.settings.high_contrast_enabled = not self.settings.high_contrast_enabled
        
        # Apply to all managed widgets
        for widget in self.managed_widgets:
            if self.settings.high_contrast_enabled:
                self._apply_high_contrast(widget)
            else:
                # Restore original style
                original_style = self.managed_widgets[widget]['original_style']
                widget.setStyleSheet(original_style)
        
        status = "enabled" if self.settings.high_contrast_enabled else "disabled"
        self.announce(f"High contrast mode {status}")
        self.accessibility_changed.emit(AccessibilityFeatures.HIGH_CONTRAST, 
                                      self.settings.high_contrast_enabled)
    
    def cycle_focus(self):
        """Cycle through focus history"""
        if len(self.focus_history) > 1:
            # Get previous widget in history
            current_index = -1
            if self.current_focus in self.focus_history:
                current_index = self.focus_history.index(self.current_focus)
            
            next_index = (current_index + 1) % len(self.focus_history)
            next_widget = self.focus_history[next_index]
            
            if next_widget and next_widget.isVisible() and next_widget.isEnabled():
                next_widget.setFocus()
                self.announce(f"Focus cycled to {next_widget.accessibleName()}")
    
    def announce_current_focus(self):
        """Announce information about currently focused widget"""
        if self.current_focus:
            self.announce_widget_info(self.current_focus)
        else:
            self.announce("No widget has focus")
    
    def refresh_accessibility(self):
        """Refresh accessibility settings and apply changes"""
        # Re-detect system settings
        old_settings = self.settings.to_dict()
        self.settings = AccessibilitySettings()
        new_settings = self.settings.to_dict()
        
        # Apply changes to all managed widgets
        for widget in self.managed_widgets:
            config = self.managed_widgets[widget]['config']
            self.setup_accessibility(widget, config)
        
        # Announce changes
        changes = []
        for key, new_value in new_settings.items():
            if old_settings.get(key) != new_value and key.endswith('_enabled'):
                feature_name = key.replace('_enabled', '').replace('_', ' ')
                status = "enabled" if new_value else "disabled"
                changes.append(f"{feature_name} {status}")
        
        if changes:
            self.announce(f"Accessibility updated: {', '.join(changes)}")
        else:
            self.announce("Accessibility settings refreshed")
    
    # Widget management
    
    def remove_widget(self, widget: QWidget):
        """Remove widget from accessibility management"""
        if widget in self.managed_widgets:
            # Cleanup shortcuts
            shortcuts = self.managed_widgets[widget]['shortcuts']
            for shortcut in shortcuts:
                shortcut.deleteLater()
            
            # Remove event filter
            widget.removeEventFilter(self)
            
            # Remove from managed widgets
            del self.managed_widgets[widget]
            
            # Remove from focus history
            while widget in self.focus_history:
                self.focus_history.remove(widget)
    
    def get_accessibility_info(self, widget: QWidget) -> Dict[str, Any]:
        """Get accessibility information for widget"""
        if widget not in self.managed_widgets:
            return {}
        
        return {
            'accessible_name': widget.accessibleName(),
            'accessible_description': widget.accessibleDescription(),
            'is_enabled': widget.isEnabled(),
            'has_focus': widget.hasFocus(),
            'config': self.managed_widgets[widget]['config'],
            'aria_properties': self.managed_widgets[widget]['aria_properties']
        }
    
    def get_accessibility_summary(self) -> Dict[str, Any]:
        """Get summary of accessibility status"""
        return {
            'settings': self.settings.to_dict(),
            'managed_widgets_count': len(self.managed_widgets),
            'current_focus': self.current_focus.accessibleName() if self.current_focus else None,
            'focus_history_length': len(self.focus_history),
            'shortcuts_count': len(self.shortcuts)
        }


class AccessibleInlineEditor:
    """Mixin for accessibility features in inline editors
    
    This mixin can be added to any editor class to provide
    comprehensive accessibility support.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.accessibility_manager = AccessibilityManager()
        self._setup_accessibility()
    
    def _setup_accessibility(self):
        """Setup accessibility features for this editor"""
        config = {
            'accessible_name': 'Inline Text Editor',
            'accessible_description': (
                'Editable text area for document elements. '
                'Double-click or press F2 to edit. '
                'Press Escape to cancel or Ctrl+Enter to save.'
            ),
            'role': 'textbox',
            'aria_properties': {
                'aria-multiline': 'true',
                'aria-required': 'false',
                'aria-label': 'Document element editor'
            },
            'help_text': (
                'Navigation: Tab/Shift+Tab to move between elements. '
                'Editing: F2 to start, Escape to cancel, Ctrl+Enter to save. '
                'Help: Alt+H for this message, Alt+D for description, Alt+S for state.'
            ),
            'shortcuts': {
                'Ctrl+A': self._select_all_accessible,
                'Ctrl+Z': self._undo_accessible,
                'Ctrl+Y': self._redo_accessible
            }
        }
        
        self.accessibility_manager.setup_accessibility(self, config)
        
        # Connect to editor signals for announcements
        self._connect_accessibility_signals()
    
    def _connect_accessibility_signals(self):
        """Connect editor signals to accessibility announcements"""
        # Connect editor-specific signals if they exist
        if hasattr(self, 'editing_started'):
            self.editing_started.connect(
                lambda: self.accessibility_manager.announce("Editing mode activated. Type to edit, press Escape to cancel.")
            )
        
        if hasattr(self, 'editing_finished'):
            self.editing_finished.connect(
                lambda success: self.accessibility_manager.announce(
                    "Changes saved." if success else "Editing cancelled."
                )
            )
        
        if hasattr(self, 'content_changed'):
            # Debounced content change announcements
            self._content_change_timer = QTimer()
            self._content_change_timer.setSingleShot(True)
            self._content_change_timer.timeout.connect(
                lambda: self.accessibility_manager.announce("Content changed", 'polite')
            )
            self.content_changed.connect(
                lambda: self._content_change_timer.start(1000)  # 1 second delay
            )
        
        if hasattr(self, 'validation_failed'):
            self.validation_failed.connect(
                lambda msg: self.accessibility_manager.announce(f"Error: {msg}", 'assertive')
            )
    
    def _select_all_accessible(self):
        """Accessible select all with announcement"""
        if hasattr(self, 'select_all'):
            self.select_all()
            self.accessibility_manager.announce("All text selected")
    
    def _undo_accessible(self):
        """Accessible undo with announcement"""
        if hasattr(self, 'undo'):
            if self.undo():
                self.accessibility_manager.announce("Undo performed")
            else:
                self.accessibility_manager.announce("Nothing to undo")
    
    def _redo_accessible(self):
        """Accessible redo with announcement"""
        if hasattr(self, 'redo'):
            if self.redo():
                self.accessibility_manager.announce("Redo performed")
            else:
                self.accessibility_manager.announce("Nothing to redo")
    
    def announce_status(self, message: str):
        """Announce status message to screen readers"""
        self.accessibility_manager.announce(message)
    
    def get_accessibility_manager(self) -> AccessibilityManager:
        """Get the accessibility manager instance"""
        return self.accessibility_manager