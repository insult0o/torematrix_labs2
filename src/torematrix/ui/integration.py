"""Integration module for Agent 2 UI Framework components."""

import logging
from typing import Optional, Dict, Any

from PyQt6.QtWidgets import QMainWindow
from PyQt6.QtCore import QObject, QSettings, pyqtSignal

from ..core.events import EventBus
from ..core.config import ConfigManager
from ..core.state import StateManager
from .base import BaseUIComponent
from .main_window import MainWindow
from .actions import ActionManager
from .menus import MenuBuilder
from .resources import ResourceManager
from .toolbars import ToolbarManager
from .shortcuts import ShortcutManager

logger = logging.getLogger(__name__)


class UIFrameworkIntegrator(BaseUIComponent):
    """Central coordinator for all Agent 2 UI components."""
    
    # Signals
    framework_initialized = pyqtSignal()
    framework_error = pyqtSignal(str)
    
    def __init__(
        self,
        main_window: MainWindow,
        event_bus: EventBus,
        config_manager: ConfigManager,
        state_manager: StateManager,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        # Core window
        self._main_window = main_window
        
        # Component managers
        self._action_manager: Optional[ActionManager] = None
        self._menu_builder: Optional[MenuBuilder] = None
        self._resource_manager: Optional[ResourceManager] = None
        self._toolbar_manager: Optional[ToolbarManager] = None
        self._shortcut_manager: Optional[ShortcutManager] = None
        
        # Settings for persistence
        self._settings = QSettings("ToreMatrix", "ToreMatrixV3")
        
        # Initialization state
        self._components_initialized = False
    
    def _setup_component(self) -> None:
        """Setup the UI framework integration."""
        try:
            self._initialize_components()
            self._wire_components()
            self._setup_ui_framework()
            self._components_initialized = True
            self.framework_initialized.emit()
            logger.info("UI Framework integration completed successfully")
        except Exception as e:
            error_msg = f"Failed to initialize UI framework: {str(e)}"
            logger.error(error_msg)
            self.framework_error.emit(error_msg)
            raise
    
    def _initialize_components(self) -> None:
        """Initialize all UI framework components."""
        # Resource Manager (needed first for icons)
        self._resource_manager = ResourceManager(
            event_bus=self._event_bus,
            config_manager=self._config_manager,
            state_manager=self._state_manager,
            parent=self
        )
        self._resource_manager.initialize()
        
        # Action Manager
        self._action_manager = ActionManager(
            event_bus=self._event_bus,
            config_manager=self._config_manager,
            state_manager=self._state_manager,
            parent=self
        )
        self._action_manager.initialize()
        
        # Menu Builder
        self._menu_builder = MenuBuilder(
            action_manager=self._action_manager,
            event_bus=self._event_bus,
            config_manager=self._config_manager,
            state_manager=self._state_manager,
            parent=self
        )
        self._menu_builder.initialize()
        
        # Toolbar Manager
        self._toolbar_manager = ToolbarManager(
            main_window=self._main_window,
            action_manager=self._action_manager,
            resource_manager=self._resource_manager,
            event_bus=self._event_bus,
            config_manager=self._config_manager,
            state_manager=self._state_manager,
            parent=self
        )
        self._toolbar_manager.initialize()
        
        # Shortcut Manager
        self._shortcut_manager = ShortcutManager(
            main_window=self._main_window,
            action_manager=self._action_manager,
            event_bus=self._event_bus,
            config_manager=self._config_manager,
            state_manager=self._state_manager,
            parent=self
        )
        self._shortcut_manager.initialize()
    
    def _wire_components(self) -> None:
        """Wire components together for proper integration."""
        # Connect action manager signals
        if self._action_manager:
            self._action_manager.action_triggered.connect(self._handle_action_triggered)
            self._action_manager.shortcut_conflict.connect(self._handle_shortcut_conflict)
        
        # Connect resource manager signals
        if self._resource_manager:
            self._resource_manager.theme_changed.connect(self._handle_theme_changed)
        
        # Connect shortcut manager signals
        if self._shortcut_manager:
            self._shortcut_manager.shortcut_activated.connect(self._handle_shortcut_activated)
            self._shortcut_manager.shortcut_conflict.connect(self._handle_shortcut_conflict)
        
        # Connect menu builder signals
        if self._menu_builder:
            self._menu_builder.menu_created.connect(self._handle_menu_created)
        
        # Connect toolbar manager signals
        if self._toolbar_manager:
            self._toolbar_manager.toolbar_created.connect(self._handle_toolbar_created)
    
    def _setup_ui_framework(self) -> None:
        """Setup the complete UI framework."""
        # Build menubar
        menubar = self._main_window.get_menubar_container()
        self._menu_builder.build_menubar(menubar)
        
        # Create all standard toolbars
        self._toolbar_manager.create_all_standard_toolbars()
        
        # Create all shortcuts
        self._shortcut_manager.create_all_shortcuts()
        
        # Load saved states
        self._load_framework_state()
    
    def _handle_action_triggered(self, action_name: str, action) -> None:
        """Handle action triggered events."""
        logger.debug(f"Action triggered: {action_name}")
        self.publish_event("ui.action.triggered", {
            "action_name": action_name,
            "checked": action.isChecked() if action.isCheckable() else None
        })
    
    def _handle_shortcut_conflict(self, sequence: str, conflicting_items) -> None:
        """Handle shortcut conflicts."""
        logger.warning(f"Shortcut conflict detected: {sequence} -> {conflicting_items}")
        self.publish_event("ui.shortcut.conflict", {
            "sequence": sequence,
            "conflicts": conflicting_items
        })
    
    def _handle_shortcut_activated(self, shortcut_name: str) -> None:
        """Handle shortcut activation."""
        logger.debug(f"Shortcut activated: {shortcut_name}")
        self.publish_event("ui.shortcut.activated", {"shortcut_name": shortcut_name})
    
    def _handle_theme_changed(self, theme_name: str) -> None:
        """Handle theme changes."""
        logger.info(f"Theme changed to: {theme_name}")
        self.publish_event("ui.theme.changed", {"theme": theme_name})
        
        # Update all UI components for new theme
        self._update_components_for_theme()
    
    def _handle_menu_created(self, menu_name: str, menu) -> None:
        """Handle menu creation."""
        logger.debug(f"Menu created: {menu_name}")
    
    def _handle_toolbar_created(self, toolbar_name: str, toolbar) -> None:
        """Handle toolbar creation."""
        logger.debug(f"Toolbar created: {toolbar_name}")
    
    def _update_components_for_theme(self) -> None:
        """Update all components when theme changes."""
        # Rebuild toolbars to update icons
        if self._toolbar_manager:
            for toolbar_name in self._toolbar_manager.get_all_toolbars().keys():
                self._toolbar_manager.rebuild_toolbar(toolbar_name)
        
        # Update menu icons (if needed)
        if self._menu_builder:
            for menu_name in self._menu_builder.get_all_menus().keys():
                self._menu_builder.rebuild_menu(menu_name)
    
    def _save_framework_state(self) -> None:
        """Save the state of all framework components."""
        if not self._components_initialized:
            return
        
        try:
            # Save action states
            if self._action_manager:
                self._action_manager.save_states()
            
            # Save toolbar states
            if self._toolbar_manager:
                self._toolbar_manager.save_states()
            
            # Resource manager saves its own theme state
            
            # Shortcut customizations are auto-saved
            
            logger.debug("Framework state saved")
        except Exception as e:
            logger.error(f"Failed to save framework state: {e}")
    
    def _load_framework_state(self) -> None:
        """Load the state of all framework components."""
        try:
            # Component states are loaded during their initialization
            # This method can be used for additional state restoration
            pass
        except Exception as e:
            logger.error(f"Failed to load framework state: {e}")
    
    # Public API for other agents
    def get_action_manager(self) -> ActionManager:
        """Get the action manager for Agent 3 and 4."""
        return self._action_manager
    
    def get_menu_builder(self) -> MenuBuilder:
        """Get the menu builder for Agent 3 and 4."""
        return self._menu_builder
    
    def get_resource_manager(self) -> ResourceManager:
        """Get the resource manager for Agent 3 and 4."""
        return self._resource_manager
    
    def get_toolbar_manager(self) -> ToolbarManager:
        """Get the toolbar manager for Agent 3 and 4."""
        return self._toolbar_manager
    
    def get_shortcut_manager(self) -> ShortcutManager:
        """Get the shortcut manager for Agent 3 and 4."""
        return self._shortcut_manager
    
    def set_theme(self, theme_name: str) -> bool:
        """Set application theme."""
        if self._resource_manager:
            self._resource_manager.set_theme(theme_name)
            return True
        return False
    
    def get_current_theme(self) -> str:
        """Get current theme name."""
        if self._resource_manager:
            return self._resource_manager.get_current_theme()
        return "light"
    
    def save_all_states(self) -> None:
        """Save all component states."""
        self._save_framework_state()
    
    def get_framework_status(self) -> Dict[str, Any]:
        """Get status of all framework components."""
        return {
            "initialized": self._components_initialized,
            "action_manager": self._action_manager is not None and self._action_manager.is_initialized,
            "menu_builder": self._menu_builder is not None and self._menu_builder.is_initialized,
            "resource_manager": self._resource_manager is not None and self._resource_manager.is_initialized,
            "toolbar_manager": self._toolbar_manager is not None and self._toolbar_manager.is_initialized,
            "shortcut_manager": self._shortcut_manager is not None and self._shortcut_manager.is_initialized,
            "theme": self.get_current_theme(),
            "action_count": len(self._action_manager.get_all_actions()) if self._action_manager else 0,
            "menu_count": len(self._menu_builder.get_all_menus()) if self._menu_builder else 0,
            "toolbar_count": len(self._toolbar_manager.get_all_toolbars()) if self._toolbar_manager else 0,
            "shortcut_count": len(self._shortcut_manager.get_all_shortcuts()) if self._shortcut_manager else 0
        }


def create_ui_framework(
    main_window: MainWindow,
    event_bus: EventBus,
    config_manager: ConfigManager,
    state_manager: StateManager
) -> UIFrameworkIntegrator:
    """Create and initialize the complete UI framework."""
    integrator = UIFrameworkIntegrator(
        main_window=main_window,
        event_bus=event_bus,
        config_manager=config_manager,
        state_manager=state_manager
    )
    
    integrator.initialize()
    return integrator