"""Toolbar management system for ToreMatrix V3."""

from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtWidgets import QToolBar, QWidget, QMainWindow
from PyQt6.QtCore import Qt, QObject, QSettings, pyqtSignal
from PyQt6.QtGui import QAction

from ..core.events import EventBus
from ..core.config import ConfigManager
from ..core.state import StateManager
from .base import BaseUIComponent
from .actions import ActionManager
from .resources import ResourceManager, IconSize


class ToolbarArea(Enum):
    """Toolbar placement areas."""
    TOP = Qt.ToolBarArea.TopToolBarArea
    BOTTOM = Qt.ToolBarArea.BottomToolBarArea
    LEFT = Qt.ToolBarArea.LeftToolBarArea
    RIGHT = Qt.ToolBarArea.RightToolBarArea


@dataclass
class ToolbarDefinition:
    """Definition for toolbar structure."""
    name: str
    title: str
    actions: List[Union[str, None]]  # None represents separator
    area: ToolbarArea = ToolbarArea.TOP
    movable: bool = True
    floatable: bool = False
    visible: bool = True
    icon_size: IconSize = IconSize.TOOLBAR


class ToolbarManager(BaseUIComponent):
    """Configurable toolbar system with persistence."""
    
    # Signals
    toolbar_created = pyqtSignal(str, QToolBar)
    toolbar_updated = pyqtSignal(str, QToolBar)
    toolbar_visibility_changed = pyqtSignal(str, bool)
    
    def __init__(
        self,
        main_window: QMainWindow,
        action_manager: ActionManager,
        resource_manager: Optional[ResourceManager],
        event_bus: EventBus,
        config_manager: Optional[ConfigManager] = None,
        state_manager: Optional[StateManager] = None,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        self._main_window = main_window
        self._action_manager = action_manager
        self._resource_manager = resource_manager
        
        # Toolbar storage
        self._toolbars: Dict[str, QToolBar] = {}
        self._toolbar_definitions: Dict[str, ToolbarDefinition] = {}
        
        # Settings for persistence
        self._settings = QSettings("ToreMatrix", "ToreMatrixV3")
        
        # Setup standard toolbars
        self._setup_standard_toolbars()
    
    def _setup_component(self) -> None:
        """Setup the toolbar management system."""
        self._restore_toolbar_states()
    
    def _setup_standard_toolbars(self) -> None:
        """Define standard application toolbars."""
        # Main toolbar
        main_toolbar = ToolbarDefinition(
            name="main",
            title="Main Toolbar",
            actions=[
                "file_new",
                "file_open",
                "file_save",
                None,  # Separator
                "edit_undo",
                "edit_redo",
                None,
                "edit_cut",
                "edit_copy",
                "edit_paste",
                None,
                "view_zoom_in",
                "view_zoom_out",
                "view_zoom_reset"
            ],
            area=ToolbarArea.TOP,
            movable=True,
            floatable=False
        )
        
        # Tools toolbar
        tools_toolbar = ToolbarDefinition(
            name="tools",
            title="Tools",
            actions=[
                "tools_process_document",
                "tools_validate_project",
                "tools_export_data"
            ],
            area=ToolbarArea.TOP,
            movable=True,
            floatable=False
        )
        
        # View toolbar
        view_toolbar = ToolbarDefinition(
            name="view",
            title="View",
            actions=[
                "view_fullscreen",
                "view_toggle_sidebar"
            ],
            area=ToolbarArea.RIGHT,
            movable=True,
            floatable=False,
            visible=False  # Hidden by default
        )
        
        # Store definitions
        self._toolbar_definitions.update({
            "main": main_toolbar,
            "tools": tools_toolbar,
            "view": view_toolbar
        })
    
    def create_toolbar(
        self,
        name: str,
        title: str,
        actions: List[Union[str, None]],
        area: ToolbarArea = ToolbarArea.TOP,
        movable: bool = True,
        floatable: bool = False,
        visible: bool = True,
        icon_size: IconSize = IconSize.TOOLBAR
    ) -> QToolBar:
        """Create and register a new toolbar."""
        if name in self._toolbars:
            return self._toolbars[name]
        
        # Create toolbar definition
        definition = ToolbarDefinition(
            name=name,
            title=title,
            actions=actions.copy(),
            area=area,
            movable=movable,
            floatable=floatable,
            visible=visible,
            icon_size=icon_size
        )
        
        return self._create_toolbar_from_definition(definition)
    
    def _create_toolbar_from_definition(self, definition: ToolbarDefinition) -> QToolBar:
        """Create QToolBar from ToolbarDefinition."""
        # Create toolbar
        toolbar = QToolBar(definition.title, self._main_window)
        toolbar.setObjectName(f"{definition.name}ToolBar")
        
        # Configure toolbar properties
        toolbar.setMovable(definition.movable)
        toolbar.setFloatable(definition.floatable)
        toolbar.setVisible(definition.visible)
        
        # Set icon size
        icon_size = definition.icon_size.value
        toolbar.setIconSize(Qt.QSize(icon_size[0], icon_size[1]))
        
        # Populate with actions
        self._populate_toolbar(toolbar, definition)
        
        # Add to main window
        self._main_window.addToolBar(definition.area.value, toolbar)
        
        # Store toolbar and definition
        self._toolbars[definition.name] = toolbar
        self._toolbar_definitions[definition.name] = definition
        
        # Connect signals
        toolbar.visibilityChanged.connect(
            lambda visible: self.toolbar_visibility_changed.emit(definition.name, visible)
        )
        
        # Emit signal
        self.toolbar_created.emit(definition.name, toolbar)
        
        return toolbar
    
    def _populate_toolbar(self, toolbar: QToolBar, definition: ToolbarDefinition) -> None:
        """Populate toolbar with actions from definition."""
        for action_item in definition.actions:
            if action_item is None:
                # Add separator
                toolbar.addSeparator()
            elif isinstance(action_item, str):
                # Add action
                action = self._action_manager.get_action(action_item)
                if action:
                    # Update icon if resource manager available
                    if self._resource_manager and not action.icon().isNull():
                        icon = self._resource_manager.get_icon(
                            action_item, 
                            definition.icon_size, 
                            theme_aware=True
                        )
                        if not icon.isNull():
                            action.setIcon(icon)
                    
                    toolbar.addAction(action)
                else:
                    # Create placeholder for missing action
                    placeholder = toolbar.addAction(f"[Missing: {action_item}]")
                    placeholder.setEnabled(False)
    
    def get_toolbar(self, name: str) -> Optional[QToolBar]:
        """Get toolbar by name."""
        return self._toolbars.get(name)
    
    def get_all_toolbars(self) -> Dict[str, QToolBar]:
        """Get all created toolbars."""
        return self._toolbars.copy()
    
    def create_all_standard_toolbars(self) -> Dict[str, QToolBar]:
        """Create all standard toolbars."""
        toolbars = {}
        for name, definition in self._toolbar_definitions.items():
            toolbar = self._create_toolbar_from_definition(definition)
            toolbars[name] = toolbar
        return toolbars
    
    def add_toolbar_action(self, toolbar_name: str, action_name: str, position: Optional[int] = None) -> bool:
        """Add action to existing toolbar."""
        if toolbar_name not in self._toolbars:
            return False
        
        action = self._action_manager.get_action(action_name)
        if not action:
            return False
        
        toolbar = self._toolbars[toolbar_name]
        
        if position is None:
            toolbar.addAction(action)
        else:
            actions = toolbar.actions()
            if 0 <= position <= len(actions):
                if position == len(actions):
                    toolbar.addAction(action)
                else:
                    toolbar.insertAction(actions[position], action)
            else:
                return False
        
        # Update definition
        if toolbar_name in self._toolbar_definitions:
            definition = self._toolbar_definitions[toolbar_name]
            if position is None:
                definition.actions.append(action_name)
            else:
                definition.actions.insert(position, action_name)
        
        self.toolbar_updated.emit(toolbar_name, toolbar)
        return True
    
    def remove_toolbar_action(self, toolbar_name: str, action_name: str) -> bool:
        """Remove action from toolbar."""
        if toolbar_name not in self._toolbars:
            return False
        
        action = self._action_manager.get_action(action_name)
        if not action:
            return False
        
        toolbar = self._toolbars[toolbar_name]
        toolbar.removeAction(action)
        
        # Update definition
        if toolbar_name in self._toolbar_definitions:
            definition = self._toolbar_definitions[toolbar_name]
            if action_name in definition.actions:
                definition.actions.remove(action_name)
        
        self.toolbar_updated.emit(toolbar_name, toolbar)
        return True
    
    def add_toolbar_separator(self, toolbar_name: str, position: Optional[int] = None) -> bool:
        """Add separator to toolbar."""
        if toolbar_name not in self._toolbars:
            return False
        
        toolbar = self._toolbars[toolbar_name]
        
        if position is None:
            toolbar.addSeparator()
        else:
            actions = toolbar.actions()
            if 0 <= position <= len(actions):
                if position == len(actions):
                    toolbar.addSeparator()
                else:
                    toolbar.insertSeparator(actions[position])
            else:
                return False
        
        # Update definition
        if toolbar_name in self._toolbar_definitions:
            definition = self._toolbar_definitions[toolbar_name]
            if position is None:
                definition.actions.append(None)
            else:
                definition.actions.insert(position, None)
        
        self.toolbar_updated.emit(toolbar_name, toolbar)
        return True
    
    def set_toolbar_visible(self, toolbar_name: str, visible: bool) -> bool:
        """Set toolbar visibility."""
        if toolbar_name not in self._toolbars:
            return False
        
        toolbar = self._toolbars[toolbar_name]
        toolbar.setVisible(visible)
        
        # Update definition
        if toolbar_name in self._toolbar_definitions:
            self._toolbar_definitions[toolbar_name].visible = visible
        
        return True
    
    def toggle_toolbar_visibility(self, toolbar_name: str) -> bool:
        """Toggle toolbar visibility."""
        if toolbar_name not in self._toolbars:
            return False
        
        toolbar = self._toolbars[toolbar_name]
        new_visibility = not toolbar.isVisible()
        return self.set_toolbar_visible(toolbar_name, new_visibility)
    
    def set_toolbar_icon_size(self, toolbar_name: str, icon_size: IconSize) -> bool:
        """Set toolbar icon size."""
        if toolbar_name not in self._toolbars:
            return False
        
        toolbar = self._toolbars[toolbar_name]
        size = icon_size.value
        toolbar.setIconSize(Qt.QSize(size[0], size[1]))
        
        # Update definition
        if toolbar_name in self._toolbar_definitions:
            self._toolbar_definitions[toolbar_name].icon_size = icon_size
        
        # Update action icons if resource manager available
        if self._resource_manager:
            self._update_toolbar_icons(toolbar_name, icon_size)
        
        self.toolbar_updated.emit(toolbar_name, toolbar)
        return True
    
    def _update_toolbar_icons(self, toolbar_name: str, icon_size: IconSize) -> None:
        """Update all icons in toolbar with new size."""
        if toolbar_name not in self._toolbars:
            return
        
        toolbar = self._toolbars[toolbar_name]
        definition = self._toolbar_definitions[toolbar_name]
        
        for action in toolbar.actions():
            if not action.isSeparator():
                # Find action name from definition
                action_name = None
                for def_action in definition.actions:
                    if def_action and self._action_manager.get_action(def_action) == action:
                        action_name = def_action
                        break
                
                if action_name:
                    icon = self._resource_manager.get_icon(action_name, icon_size, theme_aware=True)
                    if not icon.isNull():
                        action.setIcon(icon)
    
    def move_toolbar(self, toolbar_name: str, area: ToolbarArea) -> bool:
        """Move toolbar to different area."""
        if toolbar_name not in self._toolbars:
            return False
        
        toolbar = self._toolbars[toolbar_name]
        self._main_window.addToolBar(area.value, toolbar)
        
        # Update definition
        if toolbar_name in self._toolbar_definitions:
            self._toolbar_definitions[toolbar_name].area = area
        
        return True
    
    def customize_toolbar(self, toolbar_name: str, actions: List[Union[str, None]]) -> bool:
        """Customize toolbar with new action list."""
        if toolbar_name not in self._toolbars:
            return False
        
        toolbar = self._toolbars[toolbar_name]
        definition = self._toolbar_definitions[toolbar_name]
        
        # Clear current actions
        toolbar.clear()
        
        # Update definition
        definition.actions = actions.copy()
        
        # Repopulate
        self._populate_toolbar(toolbar, definition)
        
        self.toolbar_updated.emit(toolbar_name, toolbar)
        return True
    
    def reset_toolbar_to_default(self, toolbar_name: str) -> bool:
        """Reset toolbar to default configuration."""
        # This would need to store original definitions
        # For now, just rebuild from current definition
        return self.rebuild_toolbar(toolbar_name)
    
    def rebuild_toolbar(self, toolbar_name: str) -> bool:
        """Rebuild toolbar from its definition."""
        if toolbar_name not in self._toolbar_definitions:
            return False
        
        if toolbar_name in self._toolbars:
            toolbar = self._toolbars[toolbar_name]
            definition = self._toolbar_definitions[toolbar_name]
            
            # Clear and rebuild
            toolbar.clear()
            self._populate_toolbar(toolbar, definition)
            
            self.toolbar_updated.emit(toolbar_name, toolbar)
            return True
        
        return False
    
    def _save_toolbar_states(self) -> None:
        """Save toolbar states to settings."""
        self._settings.beginGroup("toolbars")
        
        for name, toolbar in self._toolbars.items():
            self._settings.beginGroup(name)
            self._settings.setValue("visible", toolbar.isVisible())
            self._settings.setValue("geometry", toolbar.saveGeometry())
            self._settings.setValue("area", int(self._main_window.toolBarArea(toolbar)))
            self._settings.endGroup()
        
        self._settings.endGroup()
    
    def _restore_toolbar_states(self) -> None:
        """Restore toolbar states from settings."""
        self._settings.beginGroup("toolbars")
        
        for name in self._settings.childGroups():
            if name in self._toolbars:
                self._settings.beginGroup(name)
                toolbar = self._toolbars[name]
                
                # Restore visibility
                visible = self._settings.value("visible", True, bool)
                toolbar.setVisible(visible)
                
                # Restore geometry
                geometry = self._settings.value("geometry")
                if geometry:
                    toolbar.restoreGeometry(geometry)
                
                # Restore area
                area_int = self._settings.value("area", int(ToolbarArea.TOP.value), int)
                area = Qt.ToolBarArea(area_int)
                self._main_window.addToolBar(area, toolbar)
                
                self._settings.endGroup()
        
        self._settings.endGroup()
    
    def save_states(self) -> None:
        """Save all toolbar states."""
        self._save_toolbar_states()
    
    def get_toolbar_definition(self, toolbar_name: str) -> Optional[ToolbarDefinition]:
        """Get toolbar definition."""
        return self._toolbar_definitions.get(toolbar_name)
    
    def get_visible_toolbars(self) -> List[str]:
        """Get list of visible toolbar names."""
        visible = []
        for name, toolbar in self._toolbars.items():
            if toolbar.isVisible():
                visible.append(name)
        return visible
    
    def get_toolbar_actions(self, toolbar_name: str) -> List[str]:
        """Get list of action names in toolbar."""
        if toolbar_name not in self._toolbar_definitions:
            return []
        
        return [action for action in self._toolbar_definitions[toolbar_name].actions if action is not None]