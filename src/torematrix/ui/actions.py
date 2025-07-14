"""Action management system for ToreMatrix V3."""

from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, QSettings, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QKeySequence, QIcon

from ..core.events import EventBus
from ..core.config import ConfigManager
from ..core.state import StateManager
from .base import BaseUIComponent


class ActionCategory(Enum):
    """Categories for organizing actions."""
    FILE = "file"
    EDIT = "edit"
    VIEW = "view"
    TOOLS = "tools"
    HELP = "help"
    CUSTOM = "custom"


@dataclass
class ActionDefinition:
    """Definition for creating an action."""
    name: str
    text: str
    tooltip: str = ""
    shortcut: str = ""
    icon: str = ""
    category: ActionCategory = ActionCategory.CUSTOM
    checkable: bool = False
    enabled: bool = True
    separator_after: bool = False
    handler: Optional[Callable] = None


class ActionManager(BaseUIComponent):
    """Centralized action management with shortcuts and persistence."""
    
    # Signals
    action_triggered = pyqtSignal(str, object)  # action_name, action
    shortcut_conflict = pyqtSignal(str, str)    # shortcut, conflicting_actions
    
    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigManager,
        state_manager: StateManager,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        # Action storage
        self._actions: Dict[str, QAction] = {}
        self._action_groups: Dict[str, QActionGroup] = {}
        self._action_definitions: Dict[str, ActionDefinition] = {}
        
        # Shortcut management
        self._shortcuts: Dict[str, str] = {}  # shortcut -> action_name
        self._shortcut_conflicts: Set[str] = set()
        
        # Settings for persistence
        self._settings = QSettings("ToreMatrix", "ToreMatrixV3")
        
        # Standard actions
        self._setup_standard_actions()
    
    def _setup_component(self) -> None:
        """Setup the action management system."""
        self._load_action_states()
        self._restore_shortcut_customizations()
    
    def _setup_standard_actions(self) -> None:
        """Define standard application actions."""
        standard_actions = [
            # File actions
            ActionDefinition("file_new", "&New", "Create new project", "Ctrl+N", "new", ActionCategory.FILE),
            ActionDefinition("file_open", "&Open...", "Open existing project", "Ctrl+O", "open", ActionCategory.FILE),
            ActionDefinition("file_save", "&Save", "Save current project", "Ctrl+S", "save", ActionCategory.FILE),
            ActionDefinition("file_save_as", "Save &As...", "Save project with new name", "Ctrl+Shift+S", "save-as", ActionCategory.FILE),
            ActionDefinition("file_export", "&Export...", "Export project data", "Ctrl+E", "export", ActionCategory.FILE),
            ActionDefinition("file_recent", "&Recent Projects", "Open recent project", "", "recent", ActionCategory.FILE),
            ActionDefinition("file_exit", "E&xit", "Exit application", "Alt+F4", "exit", ActionCategory.FILE),
            
            # Edit actions
            ActionDefinition("edit_undo", "&Undo", "Undo last action", "Ctrl+Z", "undo", ActionCategory.EDIT),
            ActionDefinition("edit_redo", "&Redo", "Redo last undone action", "Ctrl+Y", "redo", ActionCategory.EDIT),
            ActionDefinition("edit_cut", "Cu&t", "Cut selection", "Ctrl+X", "cut", ActionCategory.EDIT),
            ActionDefinition("edit_copy", "&Copy", "Copy selection", "Ctrl+C", "copy", ActionCategory.EDIT),
            ActionDefinition("edit_paste", "&Paste", "Paste from clipboard", "Ctrl+V", "paste", ActionCategory.EDIT),
            ActionDefinition("edit_select_all", "Select &All", "Select all items", "Ctrl+A", "select-all", ActionCategory.EDIT),
            ActionDefinition("edit_preferences", "&Preferences...", "Open preferences", "Ctrl+,", "preferences", ActionCategory.EDIT),
            
            # View actions
            ActionDefinition("view_zoom_in", "Zoom &In", "Increase zoom level", "Ctrl++", "zoom-in", ActionCategory.VIEW),
            ActionDefinition("view_zoom_out", "Zoom &Out", "Decrease zoom level", "Ctrl+-", "zoom-out", ActionCategory.VIEW),
            ActionDefinition("view_zoom_reset", "&Reset Zoom", "Reset zoom to 100%", "Ctrl+0", "zoom-reset", ActionCategory.VIEW),
            ActionDefinition("view_fullscreen", "&Full Screen", "Toggle full screen mode", "F11", "fullscreen", ActionCategory.VIEW, checkable=True),
            ActionDefinition("view_toggle_sidebar", "Toggle &Sidebar", "Show/hide sidebar", "Ctrl+B", "sidebar", ActionCategory.VIEW, checkable=True),
            
            # Tools actions
            ActionDefinition("tools_process_document", "&Process Document", "Process selected document", "F5", "process", ActionCategory.TOOLS),
            ActionDefinition("tools_validate_project", "&Validate Project", "Validate current project", "F6", "validate", ActionCategory.TOOLS),
            ActionDefinition("tools_export_data", "&Export Data", "Export processed data", "F7", "export-data", ActionCategory.TOOLS),
            
            # Help actions
            ActionDefinition("help_documentation", "&Documentation", "Open documentation", "F1", "help", ActionCategory.HELP),
            ActionDefinition("help_keyboard_shortcuts", "&Keyboard Shortcuts", "Show keyboard shortcuts", "Ctrl+?", "shortcuts", ActionCategory.HELP),
            ActionDefinition("help_about", "&About", "About this application", "", "about", ActionCategory.HELP),
        ]
        
        for action_def in standard_actions:
            self._action_definitions[action_def.name] = action_def
    
    def create_action(
        self,
        name: str,
        text: str,
        shortcut: str = "",
        tooltip: str = "",
        icon: str = "",
        category: ActionCategory = ActionCategory.CUSTOM,
        checkable: bool = False,
        enabled: bool = True,
        handler: Optional[Callable] = None
    ) -> QAction:
        """Create and register a new action."""
        if name in self._actions:
            return self._actions[name]
        
        # Create action definition
        action_def = ActionDefinition(
            name=name,
            text=text,
            tooltip=tooltip or text,
            shortcut=shortcut,
            icon=icon,
            category=category,
            checkable=checkable,
            enabled=enabled,
            handler=handler
        )
        
        return self._create_action_from_definition(action_def)
    
    def _create_action_from_definition(self, action_def: ActionDefinition) -> QAction:
        """Create QAction from ActionDefinition."""
        action = QAction(action_def.text, self)
        action.setToolTip(action_def.tooltip)
        action.setCheckable(action_def.checkable)
        action.setEnabled(action_def.enabled)
        
        # Set shortcut if provided
        if action_def.shortcut:
            self._set_action_shortcut(action, action_def.name, action_def.shortcut)
        
        # Set icon if provided
        if action_def.icon:
            icon = self._load_action_icon(action_def.icon)
            if icon:
                action.setIcon(icon)
        
        # Connect handler
        if action_def.handler:
            action.triggered.connect(action_def.handler)
        else:
            action.triggered.connect(lambda: self._handle_action_triggered(action_def.name, action))
        
        # Store action and definition
        self._actions[action_def.name] = action
        self._action_definitions[action_def.name] = action_def
        
        return action
    
    def _set_action_shortcut(self, action: QAction, action_name: str, shortcut: str) -> bool:
        """Set shortcut for action with conflict detection."""
        # Check for conflicts
        if shortcut in self._shortcuts:
            existing_action = self._shortcuts[shortcut]
            if existing_action != action_name:
                self._shortcut_conflicts.add(shortcut)
                self.shortcut_conflict.emit(shortcut, f"{existing_action}, {action_name}")
                return False
        
        # Set the shortcut
        key_sequence = QKeySequence(shortcut)
        if not key_sequence.isEmpty():
            action.setShortcut(key_sequence)
            self._shortcuts[shortcut] = action_name
            return True
        
        return False
    
    def _load_action_icon(self, icon_name: str) -> Optional[QIcon]:
        """Load icon for action."""
        # This will be enhanced by ResourceManager later
        icon_path = f":/icons/toolbar/{icon_name}.svg"
        icon = QIcon(icon_path)
        if not icon.isNull():
            return icon
        
        # Fallback to standard icons
        if hasattr(QApplication.style(), f"SP_{icon_name.upper()}"):
            standard_icon = getattr(QApplication.style(), f"SP_{icon_name.upper()}")
            return QApplication.style().standardIcon(standard_icon)
        
        return None
    
    def _handle_action_triggered(self, action_name: str, action: QAction) -> None:
        """Handle action triggered event."""
        self.action_triggered.emit(action_name, action)
        self.publish_event("action.triggered", {
            "action_name": action_name,
            "checked": action.isChecked() if action.isCheckable() else None
        })
    
    def get_action(self, name: str) -> Optional[QAction]:
        """Get action by name."""
        return self._actions.get(name)
    
    def get_actions_by_category(self, category: ActionCategory) -> List[QAction]:
        """Get all actions in a category."""
        actions = []
        for name, definition in self._action_definitions.items():
            if definition.category == category and name in self._actions:
                actions.append(self._actions[name])
        return actions
    
    def create_action_group(self, group_name: str, action_names: List[str], exclusive: bool = True) -> QActionGroup:
        """Create an action group."""
        if group_name in self._action_groups:
            return self._action_groups[group_name]
        
        group = QActionGroup(self)
        group.setExclusive(exclusive)
        
        for action_name in action_names:
            if action_name in self._actions:
                group.addAction(self._actions[action_name])
        
        self._action_groups[group_name] = group
        return group
    
    def set_action_enabled(self, action_name: str, enabled: bool) -> None:
        """Enable or disable an action."""
        if action_name in self._actions:
            self._actions[action_name].setEnabled(enabled)
    
    def set_action_checked(self, action_name: str, checked: bool) -> None:
        """Set checked state of a checkable action."""
        if action_name in self._actions:
            action = self._actions[action_name]
            if action.isCheckable():
                action.setChecked(checked)
    
    def customize_shortcut(self, action_name: str, new_shortcut: str) -> bool:
        """Customize keyboard shortcut for an action."""
        if action_name not in self._actions:
            return False
        
        action = self._actions[action_name]
        old_shortcut = action.shortcut().toString()
        
        # Remove old shortcut mapping
        if old_shortcut in self._shortcuts:
            del self._shortcuts[old_shortcut]
        
        # Set new shortcut
        if self._set_action_shortcut(action, action_name, new_shortcut):
            self._save_shortcut_customization(action_name, new_shortcut)
            return True
        
        # Restore old shortcut if new one failed
        if old_shortcut:
            self._set_action_shortcut(action, action_name, old_shortcut)
        
        return False
    
    def get_shortcut_conflicts(self) -> Set[str]:
        """Get list of conflicting shortcuts."""
        return self._shortcut_conflicts.copy()
    
    def resolve_shortcut_conflict(self, shortcut: str, preferred_action: str) -> None:
        """Resolve shortcut conflict by assigning to preferred action."""
        if shortcut not in self._shortcut_conflicts:
            return
        
        # Clear shortcut from all actions that have it
        for action in self._actions.values():
            if action.shortcut().toString() == shortcut:
                action.setShortcut(QKeySequence())
        
        # Assign to preferred action
        if preferred_action in self._actions:
            self._set_action_shortcut(self._actions[preferred_action], preferred_action, shortcut)
        
        self._shortcut_conflicts.discard(shortcut)
    
    def create_all_standard_actions(self) -> Dict[str, QAction]:
        """Create all standard actions."""
        actions = {}
        for name, definition in self._action_definitions.items():
            action = self._create_action_from_definition(definition)
            actions[name] = action
        return actions
    
    def _save_action_states(self) -> None:
        """Save action states to settings."""
        self._settings.beginGroup("actions")
        
        for name, action in self._actions.items():
            self._settings.beginGroup(name)
            self._settings.setValue("enabled", action.isEnabled())
            if action.isCheckable():
                self._settings.setValue("checked", action.isChecked())
            self._settings.endGroup()
        
        self._settings.endGroup()
    
    def _load_action_states(self) -> None:
        """Load action states from settings."""
        self._settings.beginGroup("actions")
        
        for name in self._settings.childGroups():
            if name in self._actions:
                self._settings.beginGroup(name)
                action = self._actions[name]
                
                enabled = self._settings.value("enabled", True, bool)
                action.setEnabled(enabled)
                
                if action.isCheckable():
                    checked = self._settings.value("checked", False, bool)
                    action.setChecked(checked)
                
                self._settings.endGroup()
        
        self._settings.endGroup()
    
    def _save_shortcut_customization(self, action_name: str, shortcut: str) -> None:
        """Save customized shortcut."""
        self._settings.beginGroup("shortcuts")
        self._settings.setValue(action_name, shortcut)
        self._settings.endGroup()
    
    def _restore_shortcut_customizations(self) -> None:
        """Restore customized shortcuts."""
        self._settings.beginGroup("shortcuts")
        
        for action_name in self._settings.childKeys():
            if action_name in self._actions:
                shortcut = self._settings.value(action_name, "", str)
                if shortcut:
                    self.customize_shortcut(action_name, shortcut)
        
        self._settings.endGroup()
    
    def save_states(self) -> None:
        """Save all action states and customizations."""
        self._save_action_states()
    
    def get_all_actions(self) -> Dict[str, QAction]:
        """Get all registered actions."""
        return self._actions.copy()
    
    def get_action_definition(self, action_name: str) -> Optional[ActionDefinition]:
        """Get action definition by name."""
        return self._action_definitions.get(action_name)