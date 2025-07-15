"""
Keyboard Shortcuts System for Document Viewer Controls

Provides comprehensive keyboard shortcuts for zoom, pan, and navigation
operations with customizable key bindings and accessibility support.
"""

from typing import Dict, List, Optional, Callable, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal, Qt, QEvent
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import QWidget, QApplication


class ActionType(Enum):
    """Types of keyboard actions"""
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    ZOOM_FIT_WIDTH = "zoom_fit_width"
    ZOOM_FIT_HEIGHT = "zoom_fit_height"
    ZOOM_FIT_PAGE = "zoom_fit_page"
    ZOOM_ACTUAL_SIZE = "zoom_actual_size"
    ZOOM_SELECTION = "zoom_selection"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    PAN_UP = "pan_up"
    PAN_DOWN = "pan_down"
    PAN_PAGE_UP = "pan_page_up"
    PAN_PAGE_DOWN = "pan_page_down"
    PAN_HOME = "pan_home"
    PAN_END = "pan_end"
    RESET_VIEW = "reset_view"
    TOGGLE_FULLSCREEN = "toggle_fullscreen"


@dataclass
class KeyboardAction:
    """Keyboard action configuration"""
    action_type: ActionType
    key_sequence: str
    description: str
    enabled: bool = True
    context: str = "viewer"
    modifiers_required: bool = False
    repeat_delay: int = 100  # ms
    
    def __post_init__(self):
        self.qt_sequence = QKeySequence(self.key_sequence)


class KeyboardShortcutManager(QObject):
    """Manages keyboard shortcuts for document viewer"""
    
    # Action signals
    zoom_in_requested = pyqtSignal()
    zoom_out_requested = pyqtSignal()
    zoom_fit_width_requested = pyqtSignal()
    zoom_fit_height_requested = pyqtSignal()
    zoom_fit_page_requested = pyqtSignal()
    zoom_actual_size_requested = pyqtSignal()
    zoom_selection_requested = pyqtSignal()
    
    pan_left_requested = pyqtSignal()
    pan_right_requested = pyqtSignal()
    pan_up_requested = pyqtSignal()
    pan_down_requested = pyqtSignal()
    pan_page_up_requested = pyqtSignal()
    pan_page_down_requested = pyqtSignal()
    pan_home_requested = pyqtSignal()
    pan_end_requested = pyqtSignal()
    
    reset_view_requested = pyqtSignal()
    toggle_fullscreen_requested = pyqtSignal()
    
    # Configuration signals
    shortcut_changed = pyqtSignal(ActionType, str)  # action_type, new_key_sequence
    
    def __init__(self, parent_widget: QWidget, parent=None):
        super().__init__(parent)
        
        self._parent_widget = parent_widget
        self._actions: Dict[ActionType, KeyboardAction] = {}
        self._shortcuts: Dict[ActionType, QShortcut] = {}
        self._signal_map: Dict[ActionType, pyqtSignal] = {}
        
        # Pan settings
        self._pan_step = 50  # pixels
        self._pan_page_factor = 0.8  # 80% of viewport
        
        self._setup_default_actions()
        self._setup_signal_mapping()
        self._create_shortcuts()
    
    def _setup_default_actions(self) -> None:
        """Setup default keyboard actions"""
        default_actions = [
            # Zoom actions
            KeyboardAction(
                ActionType.ZOOM_IN,
                "Ctrl++",
                "Zoom In",
                description="Increase zoom level"
            ),
            KeyboardAction(
                ActionType.ZOOM_OUT,
                "Ctrl+-",
                "Zoom Out", 
                description="Decrease zoom level"
            ),
            KeyboardAction(
                ActionType.ZOOM_FIT_WIDTH,
                "Ctrl+1",
                "Fit to Width",
                description="Fit document width to viewport"
            ),
            KeyboardAction(
                ActionType.ZOOM_FIT_HEIGHT,
                "Ctrl+2",
                "Fit to Height",
                description="Fit document height to viewport"
            ),
            KeyboardAction(
                ActionType.ZOOM_FIT_PAGE,
                "Ctrl+0",
                "Fit to Page",
                description="Fit entire page to viewport"
            ),
            KeyboardAction(
                ActionType.ZOOM_ACTUAL_SIZE,
                "Ctrl+Alt+0",
                "Actual Size",
                description="Display at 100% actual size"
            ),
            KeyboardAction(
                ActionType.ZOOM_SELECTION,
                "Ctrl+Shift+0",
                "Zoom to Selection",
                description="Zoom to fit selected area"
            ),
            
            # Pan actions
            KeyboardAction(
                ActionType.PAN_LEFT,
                "Left",
                "Pan Left",
                description="Pan view to the left"
            ),
            KeyboardAction(
                ActionType.PAN_RIGHT,
                "Right",
                "Pan Right",
                description="Pan view to the right"
            ),
            KeyboardAction(
                ActionType.PAN_UP,
                "Up",
                "Pan Up",
                description="Pan view upward"
            ),
            KeyboardAction(
                ActionType.PAN_DOWN,
                "Down",
                "Pan Down",
                description="Pan view downward"
            ),
            KeyboardAction(
                ActionType.PAN_PAGE_UP,
                "Page Up",
                "Pan Page Up",
                description="Pan up by page"
            ),
            KeyboardAction(
                ActionType.PAN_PAGE_DOWN,
                "Page Down",
                "Pan Page Down", 
                description="Pan down by page"
            ),
            KeyboardAction(
                ActionType.PAN_HOME,
                "Home",
                "Pan to Start",
                description="Pan to beginning of document"
            ),
            KeyboardAction(
                ActionType.PAN_END,
                "End",
                "Pan to End",
                description="Pan to end of document"
            ),
            
            # View actions
            KeyboardAction(
                ActionType.RESET_VIEW,
                "Ctrl+R",
                "Reset View",
                description="Reset zoom and pan to defaults"
            ),
            KeyboardAction(
                ActionType.TOGGLE_FULLSCREEN,
                "F11",
                "Toggle Fullscreen",
                description="Toggle fullscreen view"
            )
        ]
        
        for action in default_actions:
            self._actions[action.action_type] = action
    
    def _setup_signal_mapping(self) -> None:
        """Setup mapping between actions and signals"""
        self._signal_map = {
            ActionType.ZOOM_IN: self.zoom_in_requested,
            ActionType.ZOOM_OUT: self.zoom_out_requested,
            ActionType.ZOOM_FIT_WIDTH: self.zoom_fit_width_requested,
            ActionType.ZOOM_FIT_HEIGHT: self.zoom_fit_height_requested,
            ActionType.ZOOM_FIT_PAGE: self.zoom_fit_page_requested,
            ActionType.ZOOM_ACTUAL_SIZE: self.zoom_actual_size_requested,
            ActionType.ZOOM_SELECTION: self.zoom_selection_requested,
            ActionType.PAN_LEFT: self.pan_left_requested,
            ActionType.PAN_RIGHT: self.pan_right_requested,
            ActionType.PAN_UP: self.pan_up_requested,
            ActionType.PAN_DOWN: self.pan_down_requested,
            ActionType.PAN_PAGE_UP: self.pan_page_up_requested,
            ActionType.PAN_PAGE_DOWN: self.pan_page_down_requested,
            ActionType.PAN_HOME: self.pan_home_requested,
            ActionType.PAN_END: self.pan_end_requested,
            ActionType.RESET_VIEW: self.reset_view_requested,
            ActionType.TOGGLE_FULLSCREEN: self.toggle_fullscreen_requested
        }
    
    def _create_shortcuts(self) -> None:
        """Create QShortcut objects for all actions"""
        for action_type, action in self._actions.items():
            if action.enabled and action.qt_sequence:
                shortcut = QShortcut(action.qt_sequence, self._parent_widget)
                shortcut.activated.connect(
                    lambda at=action_type: self._handle_shortcut_activated(at)
                )
                self._shortcuts[action_type] = shortcut
    
    def _handle_shortcut_activated(self, action_type: ActionType) -> None:
        """Handle shortcut activation"""
        action = self._actions.get(action_type)
        if not action or not action.enabled:
            return
        
        # Emit appropriate signal
        signal = self._signal_map.get(action_type)
        if signal:
            signal.emit()
    
    def set_action_enabled(self, action_type: ActionType, enabled: bool) -> None:
        """Enable or disable a keyboard action"""
        action = self._actions.get(action_type)
        if action:
            action.enabled = enabled
            
            # Update shortcut
            if action_type in self._shortcuts:
                self._shortcuts[action_type].setEnabled(enabled)
    
    def change_key_sequence(self, action_type: ActionType, key_sequence: str) -> bool:
        """Change the key sequence for an action"""
        action = self._actions.get(action_type)
        if not action:
            return False
        
        try:
            # Validate key sequence
            qt_sequence = QKeySequence(key_sequence)
            if qt_sequence.isEmpty():
                return False
            
            # Update action
            action.key_sequence = key_sequence
            action.qt_sequence = qt_sequence
            
            # Recreate shortcut
            if action_type in self._shortcuts:
                self._shortcuts[action_type].deleteLater()
                del self._shortcuts[action_type]
            
            if action.enabled:
                shortcut = QShortcut(qt_sequence, self._parent_widget)
                shortcut.activated.connect(
                    lambda at=action_type: self._handle_shortcut_activated(at)
                )
                self._shortcuts[action_type] = shortcut
            
            self.shortcut_changed.emit(action_type, key_sequence)
            return True
        
        except Exception:
            return False
    
    def get_action(self, action_type: ActionType) -> Optional[KeyboardAction]:
        """Get keyboard action by type"""
        return self._actions.get(action_type)
    
    def get_all_actions(self) -> List[KeyboardAction]:
        """Get all keyboard actions"""
        return list(self._actions.values())
    
    def get_actions_by_context(self, context: str) -> List[KeyboardAction]:
        """Get actions for specific context"""
        return [action for action in self._actions.values() if action.context == context]
    
    def set_pan_step(self, step: int) -> None:
        """Set pan step size in pixels"""
        self._pan_step = max(1, step)
    
    def get_pan_step(self) -> int:
        """Get current pan step size"""
        return self._pan_step
    
    def set_pan_page_factor(self, factor: float) -> None:
        """Set pan page factor (0.0 to 1.0)"""
        self._pan_page_factor = max(0.1, min(1.0, factor))
    
    def get_pan_page_factor(self) -> float:
        """Get current pan page factor"""
        return self._pan_page_factor
    
    def get_conflicting_shortcuts(self) -> List[Tuple[ActionType, ActionType]]:
        """Get list of conflicting keyboard shortcuts"""
        conflicts = []
        actions_list = list(self._actions.items())
        
        for i, (type1, action1) in enumerate(actions_list):
            for type2, action2 in actions_list[i+1:]:
                if (action1.enabled and action2.enabled and
                    action1.key_sequence == action2.key_sequence):
                    conflicts.append((type1, type2))
        
        return conflicts
    
    def export_shortcuts(self) -> Dict[str, str]:
        """Export shortcuts configuration"""
        return {
            action_type.value: action.key_sequence
            for action_type, action in self._actions.items()
        }
    
    def import_shortcuts(self, shortcuts: Dict[str, str]) -> bool:
        """Import shortcuts configuration"""
        try:
            for action_name, key_sequence in shortcuts.items():
                try:
                    action_type = ActionType(action_name)
                    self.change_key_sequence(action_type, key_sequence)
                except ValueError:
                    continue  # Skip unknown actions
            return True
        except Exception:
            return False


class KeyboardEventFilter(QObject):
    """Event filter for advanced keyboard handling"""
    
    def __init__(self, shortcut_manager: KeyboardShortcutManager, parent=None):
        super().__init__(parent)
        self._shortcut_manager = shortcut_manager
        self._key_repeat_enabled = True
        self._repeat_actions = {
            ActionType.PAN_LEFT, ActionType.PAN_RIGHT,
            ActionType.PAN_UP, ActionType.PAN_DOWN,
            ActionType.ZOOM_IN, ActionType.ZOOM_OUT
        }
    
    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Filter keyboard events"""
        if event.type() == QEvent.Type.KeyPress:
            return self._handle_key_press(event)
        elif event.type() == QEvent.Type.KeyRelease:
            return self._handle_key_release(event)
        
        return False
    
    def _handle_key_press(self, event) -> bool:
        """Handle key press events"""
        # Check for modifier combinations that might not be in shortcuts
        modifiers = event.modifiers()
        key = event.key()
        
        # Handle special key combinations
        if self._handle_special_combinations(key, modifiers):
            return True
        
        # Let normal shortcut processing continue
        return False
    
    def _handle_key_release(self, event) -> bool:
        """Handle key release events"""
        # Could be used for key repeat handling
        return False
    
    def _handle_special_combinations(self, key: int, modifiers: Qt.KeyboardModifier) -> bool:
        """Handle special key combinations"""
        # Ctrl + Mouse wheel equivalent (Ctrl + Plus/Minus with numeric keypad)
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_Plus or key == Qt.Key.Key_Equal:
                self._shortcut_manager.zoom_in_requested.emit()
                return True
            elif key == Qt.Key.Key_Minus:
                self._shortcut_manager.zoom_out_requested.emit()
                return True
        
        # Shift + Arrow keys for fine panning
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            fine_step = self._shortcut_manager.get_pan_step() // 4
            
            if key == Qt.Key.Key_Left:
                # Emit with fine step - would need custom signal
                return True
            elif key == Qt.Key.Key_Right:
                # Emit with fine step - would need custom signal
                return True
            elif key == Qt.Key.Key_Up:
                # Emit with fine step - would need custom signal
                return True
            elif key == Qt.Key.Key_Down:
                # Emit with fine step - would need custom signal
                return True
        
        return False
    
    def set_key_repeat_enabled(self, enabled: bool) -> None:
        """Enable or disable key repeat for supported actions"""
        self._key_repeat_enabled = enabled


class AccessibilityKeyboardHandler(QObject):
    """Accessibility-focused keyboard handler"""
    
    def __init__(self, shortcut_manager: KeyboardShortcutManager, parent=None):
        super().__init__(parent)
        self._shortcut_manager = shortcut_manager
        self._high_contrast_mode = False
        self._screen_reader_mode = False
        
        # Connect to system accessibility changes
        self._setup_accessibility_monitoring()
    
    def _setup_accessibility_monitoring(self) -> None:
        """Setup monitoring for system accessibility changes"""
        # Monitor system accessibility settings
        # This would integrate with system accessibility APIs
        pass
    
    def set_high_contrast_mode(self, enabled: bool) -> None:
        """Enable high contrast mode adjustments"""
        self._high_contrast_mode = enabled
        if enabled:
            self._apply_high_contrast_shortcuts()
    
    def set_screen_reader_mode(self, enabled: bool) -> None:
        """Enable screen reader mode adjustments"""
        self._screen_reader_mode = enabled
        if enabled:
            self._apply_screen_reader_shortcuts()
    
    def _apply_high_contrast_shortcuts(self) -> None:
        """Apply keyboard shortcuts optimized for high contrast mode"""
        # Could modify shortcuts for better accessibility
        pass
    
    def _apply_screen_reader_shortcuts(self) -> None:
        """Apply keyboard shortcuts optimized for screen readers"""
        # Could add additional shortcuts for screen reader navigation
        pass
    
    def get_accessibility_help_text(self) -> str:
        """Get accessibility help text for keyboard shortcuts"""
        help_lines = [
            "Document Viewer Keyboard Shortcuts:",
            "",
            "Zoom Controls:",
            "  Ctrl + Plus: Zoom In",
            "  Ctrl + Minus: Zoom Out", 
            "  Ctrl + 0: Fit to Page",
            "  Ctrl + 1: Fit to Width",
            "  Ctrl + 2: Fit to Height",
            "  Ctrl + Alt + 0: Actual Size",
            "",
            "Navigation Controls:",
            "  Arrow Keys: Pan in direction",
            "  Page Up/Down: Pan by page",
            "  Home: Go to start",
            "  End: Go to end",
            "",
            "View Controls:",
            "  Ctrl + R: Reset view",
            "  F11: Toggle fullscreen"
        ]
        
        return "\n".join(help_lines)


class KeyboardShortcutWidget(QWidget):
    """Widget for displaying and configuring keyboard shortcuts"""
    
    def __init__(self, shortcut_manager: KeyboardShortcutManager, parent=None):
        super().__init__(parent)
        self._shortcut_manager = shortcut_manager
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup keyboard shortcut configuration UI"""
        # This would create a UI for viewing and configuring shortcuts
        # Including tables, key sequence editors, conflict detection, etc.
        pass
    
    def refresh_display(self) -> None:
        """Refresh the shortcut display"""
        pass
    
    def validate_shortcuts(self) -> List[str]:
        """Validate current shortcuts and return any issues"""
        issues = []
        
        # Check for conflicts
        conflicts = self._shortcut_manager.get_conflicting_shortcuts()
        for action1, action2 in conflicts:
            issues.append(f"Conflict between {action1.value} and {action2.value}")
        
        return issues