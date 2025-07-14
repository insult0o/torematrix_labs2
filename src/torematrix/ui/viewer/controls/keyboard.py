"""
Keyboard navigation support for document viewer.
Provides arrow key panning, zoom shortcuts, and custom key bindings.
"""

from typing import Dict, Callable, Optional, Set
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QKeyEvent, QKeySequence
from PyQt6.QtWidgets import QWidget


class KeyboardNavigator(QObject):
    """
    Keyboard navigation support for document viewer.
    Provides arrow key panning, zoom shortcuts, and custom key bindings.
    """
    
    # Navigation signals
    pan_requested = pyqtSignal(str, float)  # direction, distance
    zoom_requested = pyqtSignal(str)  # action: 'in', 'out', 'fit', 'reset'
    navigation_requested = pyqtSignal(str)  # action: 'home', 'end', 'page_up', 'page_down'
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Key configuration
        self.pan_step_size = 50  # pixels per arrow key press
        self.fast_pan_multiplier = 3  # with Shift modifier
        self.page_scroll_multiplier = 5  # for Page Up/Down
        
        # Key repeat handling
        self.repeat_delay = 500  # ms before key repeat starts
        self.repeat_interval = 50  # ms between key repeats
        self.pressed_keys: Set[int] = set()
        
        # Repeat timer
        self.repeat_timer = QTimer()
        self.repeat_timer.timeout.connect(self._handle_key_repeat)
        
        # Default key bindings
        self.key_bindings = self._create_default_bindings()
        
        # Modifier-specific bindings
        self.modifier_bindings = self._create_modifier_bindings()
        
        # Custom bindings
        self.custom_bindings: Dict[int, Callable] = {}
    
    def _create_default_bindings(self) -> Dict[int, Callable]:
        """Create default key bindings."""
        return {
            # Pan controls
            Qt.Key.Key_Up: lambda: self.pan_requested.emit('up', self.pan_step_size),
            Qt.Key.Key_Down: lambda: self.pan_requested.emit('down', self.pan_step_size),
            Qt.Key.Key_Left: lambda: self.pan_requested.emit('left', self.pan_step_size),
            Qt.Key.Key_Right: lambda: self.pan_requested.emit('right', self.pan_step_size),
            
            # Zoom controls
            Qt.Key.Key_Plus: lambda: self.zoom_requested.emit('in'),
            Qt.Key.Key_Equal: lambda: self.zoom_requested.emit('in'),  # For US keyboards
            Qt.Key.Key_Minus: lambda: self.zoom_requested.emit('out'),
            Qt.Key.Key_0: lambda: self.zoom_requested.emit('reset'),
            
            # Navigation
            Qt.Key.Key_Home: lambda: self.navigation_requested.emit('home'),
            Qt.Key.Key_End: lambda: self.navigation_requested.emit('end'),
            Qt.Key.Key_PageUp: lambda: self.navigation_requested.emit('page_up'),
            Qt.Key.Key_PageDown: lambda: self.navigation_requested.emit('page_down'),
            
            # Fit controls
            Qt.Key.Key_F: lambda: self.zoom_requested.emit('fit'),
        }
    
    def _create_modifier_bindings(self) -> Dict[tuple, Callable]:
        """Create modifier-specific key bindings."""
        return {
            # Ctrl + zoom
            (Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_Plus): 
                lambda: self.zoom_requested.emit('in'),
            (Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_Equal):
                lambda: self.zoom_requested.emit('in'),
            (Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_Minus): 
                lambda: self.zoom_requested.emit('out'),
            (Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_0): 
                lambda: self.zoom_requested.emit('reset'),
            
            # Shift + fast pan
            (Qt.KeyboardModifier.ShiftModifier, Qt.Key.Key_Up):
                lambda: self.pan_requested.emit('up', self.pan_step_size * self.fast_pan_multiplier),
            (Qt.KeyboardModifier.ShiftModifier, Qt.Key.Key_Down):
                lambda: self.pan_requested.emit('down', self.pan_step_size * self.fast_pan_multiplier),
            (Qt.KeyboardModifier.ShiftModifier, Qt.Key.Key_Left):
                lambda: self.pan_requested.emit('left', self.pan_step_size * self.fast_pan_multiplier),
            (Qt.KeyboardModifier.ShiftModifier, Qt.Key.Key_Right):
                lambda: self.pan_requested.emit('right', self.pan_step_size * self.fast_pan_multiplier),
            
            # Ctrl + navigation
            (Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_Home):
                lambda: self.navigation_requested.emit('document_start'),
            (Qt.KeyboardModifier.ControlModifier, Qt.Key.Key_End):
                lambda: self.navigation_requested.emit('document_end'),
            
            # Alt + special functions
            (Qt.KeyboardModifier.AltModifier, Qt.Key.Key_F):
                lambda: self.zoom_requested.emit('fit_width'),
        }
    
    def handle_key_press(self, event: QKeyEvent) -> bool:
        """
        Handle keyboard key press events.
        
        Args:
            event: Qt key event
            
        Returns:
            bool: True if key was handled
        """
        key = event.key()
        modifiers = event.modifiers()
        
        # Clean modifiers (remove lock keys)
        clean_modifiers = modifiers & ~(Qt.KeyboardModifier.CapsLockModifier | 
                                       Qt.KeyboardModifier.NumLockModifier |
                                       Qt.KeyboardModifier.ScrollLockModifier)
        
        # Check modifier-specific bindings first
        modifier_key = (clean_modifiers, key)
        if modifier_key in self.modifier_bindings:
            self.modifier_bindings[modifier_key]()
            self._start_key_repeat(key, modifier_key)
            return True
        
        # Check custom bindings
        if key in self.custom_bindings:
            self.custom_bindings[key]()
            return True
        
        # Check standard key bindings (only if no modifiers)
        if clean_modifiers == Qt.KeyboardModifier.NoModifier:
            if key in self.key_bindings:
                self.key_bindings[key]()
                self._start_key_repeat(key)
                return True
        
        return False
    
    def handle_key_release(self, event: QKeyEvent) -> bool:
        """
        Handle keyboard key release events.
        
        Args:
            event: Qt key event
            
        Returns:
            bool: True if key was handled
        """
        key = event.key()
        
        # Remove from pressed keys and stop repeat if needed
        if key in self.pressed_keys:
            self.pressed_keys.remove(key)
            
            if not self.pressed_keys:
                self.repeat_timer.stop()
            
            return True
        
        return False
    
    def _start_key_repeat(self, key: int, modifier_key: Optional[tuple] = None):
        """Start key repeat for navigation keys."""
        # Only enable repeat for navigation keys
        navigation_keys = {
            Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right,
            Qt.Key.Key_PageUp, Qt.Key.Key_PageDown
        }
        
        if key in navigation_keys:
            self.pressed_keys.add(key)
            self.repeat_timer.start(self.repeat_delay)
            
            # Store the action for repeat
            if modifier_key:
                self._current_repeat_action = lambda: self.modifier_bindings[modifier_key]()
            else:
                self._current_repeat_action = lambda: self.key_bindings[key]()
    
    def _handle_key_repeat(self):
        """Handle repeated key press for smooth navigation."""
        if not self.pressed_keys or not hasattr(self, '_current_repeat_action'):
            self.repeat_timer.stop()
            return
        
        # Execute the stored action
        try:
            self._current_repeat_action()
        except (KeyError, AttributeError):
            # Action no longer valid, stop repeat
            self.repeat_timer.stop()
            return
        
        # Set faster repeat interval
        self.repeat_timer.start(self.repeat_interval)
    
    def add_key_binding(self, key: int, action: Callable, 
                       modifiers: Optional[Qt.KeyboardModifier] = None):
        """
        Add custom key binding.
        
        Args:
            key: Key code
            action: Action to execute
            modifiers: Optional modifier keys
        """
        if modifiers:
            self.modifier_bindings[(modifiers, key)] = action
        else:
            self.custom_bindings[key] = action
    
    def remove_key_binding(self, key: int, 
                          modifiers: Optional[Qt.KeyboardModifier] = None):
        """
        Remove key binding.
        
        Args:
            key: Key code
            modifiers: Optional modifier keys
        """
        if modifiers:
            modifier_key = (modifiers, key)
            if modifier_key in self.modifier_bindings:
                del self.modifier_bindings[modifier_key]
        else:
            if key in self.custom_bindings:
                del self.custom_bindings[key]
            elif key in self.key_bindings:
                del self.key_bindings[key]
    
    def set_pan_step_size(self, step_size: int):
        """Set the step size for arrow key panning."""
        if step_size > 0:
            self.pan_step_size = step_size
            # Update the bindings with new step size
            self.key_bindings.update(self._create_default_bindings())
    
    def set_fast_pan_multiplier(self, multiplier: float):
        """Set the multiplier for fast panning with Shift."""
        if multiplier > 1.0:
            self.fast_pan_multiplier = multiplier
            # Update modifier bindings
            self.modifier_bindings.update(self._create_modifier_bindings())
    
    def set_repeat_timing(self, delay: int, interval: int):
        """
        Set key repeat timing.
        
        Args:
            delay: Initial delay before repeat starts (ms)
            interval: Interval between repeats (ms)
        """
        if delay > 0:
            self.repeat_delay = delay
        if interval > 0:
            self.repeat_interval = interval
    
    def enable_key_repeat(self, enabled: bool = True):
        """Enable or disable key repeat functionality."""
        if not enabled:
            self.repeat_timer.stop()
            self.pressed_keys.clear()
    
    def get_key_bindings_info(self) -> Dict[str, List[str]]:
        """Get information about current key bindings."""
        info = {
            'navigation': [
                'Arrow Keys - Pan view',
                'Shift + Arrow Keys - Fast pan',
                'Page Up/Down - Page navigation',
                'Home/End - Go to start/end',
                'Ctrl+Home/End - Document start/end'
            ],
            'zoom': [
                '+/= - Zoom in',
                '- - Zoom out', 
                '0 - Reset zoom (100%)',
                'Ctrl + zoom keys - Alternative zoom',
                'F - Fit to view',
                'Alt+F - Fit width'
            ],
            'custom': [
                f"Key {key}: Custom action" 
                for key in self.custom_bindings.keys()
            ]
        }
        return info
    
    def reset_to_defaults(self):
        """Reset all key bindings to defaults."""
        self.key_bindings = self._create_default_bindings()
        self.modifier_bindings = self._create_modifier_bindings()
        self.custom_bindings.clear()
        self.pressed_keys.clear()
        self.repeat_timer.stop()
    
    def export_bindings(self) -> Dict:
        """Export current key bindings for saving."""
        return {
            'pan_step_size': self.pan_step_size,
            'fast_pan_multiplier': self.fast_pan_multiplier,
            'repeat_delay': self.repeat_delay,
            'repeat_interval': self.repeat_interval,
            # Note: Actions are not serializable, so we just export the keys
            'custom_keys': list(self.custom_bindings.keys())
        }
    
    def import_bindings(self, bindings: Dict):
        """Import key binding configuration."""
        if 'pan_step_size' in bindings:
            self.set_pan_step_size(bindings['pan_step_size'])
        
        if 'fast_pan_multiplier' in bindings:
            self.set_fast_pan_multiplier(bindings['fast_pan_multiplier'])
        
        if 'repeat_delay' in bindings and 'repeat_interval' in bindings:
            self.set_repeat_timing(bindings['repeat_delay'], bindings['repeat_interval'])