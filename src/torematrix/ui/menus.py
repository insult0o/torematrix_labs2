"""Menu construction and organization for ToreMatrix V3."""

from typing import Dict, List, Optional, Union, Tuple
from dataclasses import dataclass

from PyQt6.QtWidgets import QMenuBar, QMenu, QToolBar
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QAction

from ..core.events import EventBus
from ..core.config import ConfigManager
from ..core.state import StateManager
from .base import BaseUIComponent
from .actions import ActionManager, ActionCategory


@dataclass
class MenuDefinition:
    """Definition for menu structure."""
    name: str
    title: str
    actions: List[Union[str, None]]  # None represents separator
    submenu_definitions: Optional[Dict[str, 'MenuDefinition']] = None


class MenuBuilder(BaseUIComponent):
    """Dynamic menu construction with proper organization."""
    
    # Signals
    menu_created = pyqtSignal(str, QMenu)
    menu_updated = pyqtSignal(str, QMenu)
    
    def __init__(
        self,
        action_manager: ActionManager,
        event_bus: EventBus,
        config_manager: Optional[ConfigManager] = None,
        state_manager: Optional[StateManager] = None,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        self._action_manager = action_manager
        self._menus: Dict[str, QMenu] = {}
        self._menu_definitions: Dict[str, MenuDefinition] = {}
        
        # Setup standard menu definitions
        self._setup_standard_menus()
    
    def _setup_component(self) -> None:
        """Setup the menu builder system."""
        pass
    
    def _setup_standard_menus(self) -> None:
        """Define standard application menus."""
        # File menu
        file_menu = MenuDefinition(
            name="file",
            title="&File",
            actions=[
                "file_new",
                "file_open",
                None,  # Separator
                "file_save",
                "file_save_as",
                None,
                "file_export",
                None,
                "file_recent",
                None,
                "file_exit"
            ]
        )
        
        # Edit menu
        edit_menu = MenuDefinition(
            name="edit",
            title="&Edit", 
            actions=[
                "edit_undo",
                "edit_redo",
                None,
                "edit_cut",
                "edit_copy",
                "edit_paste",
                None,
                "edit_select_all",
                None,
                "edit_preferences"
            ]
        )
        
        # View menu
        view_menu = MenuDefinition(
            name="view",
            title="&View",
            actions=[
                "view_zoom_in",
                "view_zoom_out",
                "view_zoom_reset",
                None,
                "view_fullscreen",
                "view_toggle_sidebar"
            ]
        )
        
        # Tools menu
        tools_menu = MenuDefinition(
            name="tools",
            title="&Tools",
            actions=[
                "tools_process_document",
                "tools_validate_project",
                "tools_export_data"
            ]
        )
        
        # Help menu
        help_menu = MenuDefinition(
            name="help",
            title="&Help",
            actions=[
                "help_documentation",
                "help_keyboard_shortcuts",
                None,
                "help_about"
            ]
        )
        
        # Store definitions
        self._menu_definitions.update({
            "file": file_menu,
            "edit": edit_menu,
            "view": view_menu,
            "tools": tools_menu,
            "help": help_menu
        })
    
    def build_menubar(self, menubar: QMenuBar) -> None:
        """Build complete menubar with all standard menus."""
        # Clear existing menus
        menubar.clear()
        self._menus.clear()
        
        # Create all standard actions first
        self._action_manager.create_all_standard_actions()
        
        # Build menus in order
        menu_order = ["file", "edit", "view", "tools", "help"]
        
        for menu_name in menu_order:
            if menu_name in self._menu_definitions:
                menu = self.build_menu(menu_name, menubar)
                if menu:
                    menubar.addMenu(menu)
    
    def build_menu(self, menu_name: str, parent: Optional[Union[QMenuBar, QMenu]] = None) -> Optional[QMenu]:
        """Build a specific menu."""
        if menu_name not in self._menu_definitions:
            return None
        
        definition = self._menu_definitions[menu_name]
        
        # Create menu
        if parent:
            menu = parent.addMenu(definition.title)
        else:
            menu = QMenu(definition.title)
        
        # Populate menu with actions
        self._populate_menu(menu, definition)
        
        # Store menu
        self._menus[menu_name] = menu
        
        # Emit signal
        self.menu_created.emit(menu_name, menu)
        
        return menu
    
    def _populate_menu(self, menu: QMenu, definition: MenuDefinition) -> None:
        """Populate menu with actions from definition."""
        for action_item in definition.actions:
            if action_item is None:
                # Add separator
                menu.addSeparator()
            elif isinstance(action_item, str):
                # Add action
                action = self._action_manager.get_action(action_item)
                if action:
                    menu.addAction(action)
                else:
                    # Create placeholder for missing action
                    placeholder = menu.addAction(f"[Missing: {action_item}]")
                    placeholder.setEnabled(False)
        
        # Add submenus if defined
        if definition.submenu_definitions:
            if definition.actions:  # Add separator before submenus if actions exist
                menu.addSeparator()
            
            for submenu_name, submenu_def in definition.submenu_definitions.items():
                submenu = self.build_menu(submenu_name, menu)
                if submenu:
                    self._menus[submenu_name] = submenu
    
    def add_menu_action(self, menu_name: str, action_name: str, position: Optional[int] = None) -> bool:
        """Add action to existing menu."""
        if menu_name not in self._menus:
            return False
        
        action = self._action_manager.get_action(action_name)
        if not action:
            return False
        
        menu = self._menus[menu_name]
        
        if position is None:
            menu.addAction(action)
        else:
            actions = menu.actions()
            if 0 <= position <= len(actions):
                if position == len(actions):
                    menu.addAction(action)
                else:
                    menu.insertAction(actions[position], action)
            else:
                return False
        
        # Update definition
        if menu_name in self._menu_definitions:
            definition = self._menu_definitions[menu_name]
            if position is None:
                definition.actions.append(action_name)
            else:
                definition.actions.insert(position, action_name)
        
        self.menu_updated.emit(menu_name, menu)
        return True
    
    def remove_menu_action(self, menu_name: str, action_name: str) -> bool:
        """Remove action from menu."""
        if menu_name not in self._menus:
            return False
        
        action = self._action_manager.get_action(action_name)
        if not action:
            return False
        
        menu = self._menus[menu_name]
        menu.removeAction(action)
        
        # Update definition
        if menu_name in self._menu_definitions:
            definition = self._menu_definitions[menu_name]
            if action_name in definition.actions:
                definition.actions.remove(action_name)
        
        self.menu_updated.emit(menu_name, menu)
        return True
    
    def add_menu_separator(self, menu_name: str, position: Optional[int] = None) -> bool:
        """Add separator to menu."""
        if menu_name not in self._menus:
            return False
        
        menu = self._menus[menu_name]
        
        if position is None:
            menu.addSeparator()
        else:
            actions = menu.actions()
            if 0 <= position <= len(actions):
                if position == len(actions):
                    menu.addSeparator()
                else:
                    menu.insertSeparator(actions[position])
            else:
                return False
        
        # Update definition
        if menu_name in self._menu_definitions:
            definition = self._menu_definitions[menu_name]
            if position is None:
                definition.actions.append(None)
            else:
                definition.actions.insert(position, None)
        
        self.menu_updated.emit(menu_name, menu)
        return True
    
    def create_custom_menu(
        self,
        menu_name: str,
        title: str,
        actions: List[Union[str, None]],
        parent: Optional[Union[QMenuBar, QMenu]] = None
    ) -> Optional[QMenu]:
        """Create a custom menu."""
        if menu_name in self._menus:
            return self._menus[menu_name]
        
        # Create definition
        definition = MenuDefinition(
            name=menu_name,
            title=title,
            actions=actions.copy()
        )
        
        self._menu_definitions[menu_name] = definition
        
        # Build menu
        return self.build_menu(menu_name, parent)
    
    def create_context_menu(self, actions: List[str]) -> QMenu:
        """Create a context menu with specified actions."""
        menu = QMenu()
        
        for action_name in actions:
            if action_name is None:
                menu.addSeparator()
            else:
                action = self._action_manager.get_action(action_name)
                if action:
                    menu.addAction(action)
        
        return menu
    
    def get_menu(self, menu_name: str) -> Optional[QMenu]:
        """Get menu by name."""
        return self._menus.get(menu_name)
    
    def get_all_menus(self) -> Dict[str, QMenu]:
        """Get all created menus."""
        return self._menus.copy()
    
    def update_menu_visibility(self, menu_name: str, visible: bool) -> None:
        """Update menu visibility."""
        if menu_name in self._menus:
            menu = self._menus[menu_name]
            menu.setVisible(visible)
    
    def enable_menu(self, menu_name: str, enabled: bool) -> None:
        """Enable or disable menu."""
        if menu_name in self._menus:
            menu = self._menus[menu_name]
            menu.setEnabled(enabled)
    
    def rebuild_menu(self, menu_name: str) -> bool:
        """Rebuild a menu from its definition."""
        if menu_name not in self._menu_definitions:
            return False
        
        if menu_name in self._menus:
            # Get parent and remove old menu
            menu = self._menus[menu_name]
            parent = menu.parent()
            
            # Clear and rebuild
            menu.clear()
            definition = self._menu_definitions[menu_name]
            self._populate_menu(menu, definition)
            
            self.menu_updated.emit(menu_name, menu)
            return True
        
        return False
    
    def get_menu_definition(self, menu_name: str) -> Optional[MenuDefinition]:
        """Get menu definition."""
        return self._menu_definitions.get(menu_name)
    
    def set_menu_definition(self, menu_name: str, definition: MenuDefinition) -> None:
        """Set menu definition."""
        self._menu_definitions[menu_name] = definition
        
        # Rebuild if menu exists
        if menu_name in self._menus:
            self.rebuild_menu(menu_name)