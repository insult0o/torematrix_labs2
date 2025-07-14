"""Core Layout Manager for ToreMatrix Layout Management System.

This module provides the central LayoutManager class that coordinates all layout
operations, manages layout templates, and handles layout switching and state management.
"""

from typing import Dict, List, Optional, Any, Callable, Union, Set
import logging
from uuid import uuid4
from contextlib import contextmanager

from PyQt6.QtWidgets import QWidget, QMainWindow, QSplitter, QStackedWidget
from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QSize
from PyQt6.QtGui import QResizeEvent

from ...core.events import EventBus
from ...core.config import ConfigurationManager
from ...core.state import Store
from ..base import BaseUIComponent
from .base import (
    BaseLayout, LayoutConfiguration, LayoutItem, LayoutType, LayoutState,
    LayoutGeometry, LayoutProvider, LayoutItemRegistry
)

logger = logging.getLogger(__name__)


class LayoutTransitionError(Exception):
    """Raised when layout transition fails."""
    pass


class LayoutValidationError(Exception):
    """Raised when layout validation fails."""
    pass


class LayoutManager(BaseUIComponent):
    """Central layout management system for ToreMatrix V3.
    
    The LayoutManager coordinates all layout operations including:
    - Layout template management and instantiation
    - Layout switching with smooth transitions
    - Layout state persistence and restoration
    - Layout validation and error handling
    - Component registration and tracking
    """
    
    # Signals
    layout_activated = pyqtSignal(LayoutConfiguration)
    layout_deactivated = pyqtSignal(str)  # layout_id
    layout_switched = pyqtSignal(str, str)  # from_id, to_id
    layout_error = pyqtSignal(str, str)  # layout_id, error_message
    template_registered = pyqtSignal(LayoutType, str)  # layout_type, template_name
    component_registered = pyqtSignal(str, QWidget)  # component_id, widget
    
    def __init__(
        self,
        main_window: QMainWindow,
        event_bus: EventBus,
        config_manager: ConfigurationManager,
        state_manager: Store,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        self._main_window = main_window
        self._current_layout: Optional[BaseLayout] = None
        self._layouts: Dict[str, BaseLayout] = {}
        self._templates: Dict[LayoutType, Callable[..., BaseLayout]] = {}
        self._providers: List[LayoutProvider] = []
        self._registry = LayoutItemRegistry()
        
        # Layout switching
        self._transition_duration = 300  # milliseconds
        self._transition_timer: Optional[QTimer] = None
        self._pending_layout: Optional[str] = None
        self._switching_enabled = True
        
        # Layout stack for managing containers
        self._layout_stack: Optional[QStackedWidget] = None
        
        # Component tracking
        self._registered_components: Dict[str, QWidget] = {}
        self._component_layouts: Dict[str, str] = {}  # component_id -> layout_id
        
        # State management
        self._auto_save_enabled = True
        self._auto_save_interval = 30000  # 30 seconds
        self._auto_save_timer: Optional[QTimer] = None
        
        # Layout history for undo/redo
        self._layout_history: List[str] = []
        self._history_index = -1
        self._max_history = 50
    
    def _setup_component(self) -> None:
        """Setup the layout manager."""
        self._setup_layout_stack()
        self._setup_auto_save()
        self._setup_transition_timer()
        self._load_saved_layouts()
        
        # Register for events
        self.subscribe_to_event("layout.request_switch", self._handle_layout_switch_request)
        self.subscribe_to_event("layout.request_save", self._handle_layout_save_request)
        self.subscribe_to_event("window.resize", self._handle_window_resize)
        
        logger.info("Layout Manager initialized successfully")
    
    def _setup_layout_stack(self) -> None:
        """Setup the layout stack widget."""
        self._layout_stack = QStackedWidget(self._main_window)
        self._main_window.setCentralWidget(self._layout_stack)
    
    def _setup_auto_save(self) -> None:
        """Setup automatic layout state saving."""
        if self._auto_save_enabled:
            self._auto_save_timer = QTimer(self)
            self._auto_save_timer.timeout.connect(self._auto_save_current_layout)
            self._auto_save_timer.start(self._auto_save_interval)
    
    def _setup_transition_timer(self) -> None:
        """Setup timer for layout transitions."""
        self._transition_timer = QTimer(self)
        self._transition_timer.setSingleShot(True)
        self._transition_timer.timeout.connect(self._complete_layout_transition)
    
    def _load_saved_layouts(self) -> None:
        """Load saved layouts from configuration."""
        try:
            saved_layouts = self.get_config("layouts.saved", {})
            for layout_id, layout_data in saved_layouts.items():
                # Note: Actual restoration would need widget recreation
                # This is a placeholder for the restoration logic
                logger.debug(f"Found saved layout: {layout_id}")
                
        except Exception as e:
            logger.warning(f"Failed to load saved layouts: {e}")
    
    def register_template(
        self,
        layout_type: LayoutType,
        template_factory: Callable[..., BaseLayout],
        template_name: Optional[str] = None
    ) -> None:
        """Register a layout template factory."""
        self._templates[layout_type] = template_factory
        
        name = template_name or layout_type.value
        self.template_registered.emit(layout_type, name)
        
        logger.info(f"Registered layout template: {layout_type.value}")
    
    def register_provider(self, provider: LayoutProvider) -> None:
        """Register a layout provider."""
        self._providers.append(provider)
        
        supported_layouts = provider.get_supported_layouts()
        logger.info(f"Registered layout provider supporting: {[lt.value for lt in supported_layouts]}")
    
    def register_component(
        self,
        component_id: str,
        widget: QWidget,
        layout_types: Optional[List[LayoutType]] = None
    ) -> None:
        """Register a UI component for layout management."""
        self._registered_components[component_id] = widget
        self._registry.register_widget(component_id, widget)
        
        self.component_registered.emit(component_id, widget)
        
        logger.debug(f"Registered component: {component_id}")
    
    def unregister_component(self, component_id: str) -> None:
        """Unregister a UI component."""
        if component_id in self._registered_components:
            del self._registered_components[component_id]
            self._registry.unregister_widget(component_id)
            
            # Remove from layout if assigned
            if component_id in self._component_layouts:
                layout_id = self._component_layouts[component_id]
                if layout_id in self._layouts:
                    layout = self._layouts[layout_id]
                    layout.remove_item(component_id)
                del self._component_layouts[component_id]
            
            logger.debug(f"Unregistered component: {component_id}")
    
    def create_layout(
        self,
        layout_type: LayoutType,
        name: str,
        geometry: Optional[LayoutGeometry] = None,
        **kwargs
    ) -> str:
        """Create a new layout instance."""
        try:
            # Generate unique ID
            layout_id = kwargs.get('layout_id', str(uuid4()))
            
            # Create default geometry if none provided
            if not geometry:
                size = self._main_window.size()
                geometry = LayoutGeometry(
                    width=size.width(),
                    height=size.height()
                )
            
            # Create configuration
            config = LayoutConfiguration(
                id=layout_id,
                name=name,
                layout_type=layout_type,
                geometry=geometry,
                properties=kwargs.get('properties', {})
            )
            
            # Create layout instance
            layout = self._create_layout_instance(config)
            
            # Store layout
            self._layouts[layout_id] = layout
            
            # Connect signals
            self._connect_layout_signals(layout)
            
            logger.info(f"Created layout: {name} ({layout_type.value})")
            return layout_id
            
        except Exception as e:
            error_msg = f"Failed to create layout {name}: {e}"
            logger.error(error_msg)
            raise LayoutValidationError(error_msg)
    
    def _create_layout_instance(self, config: LayoutConfiguration) -> BaseLayout:
        """Create layout instance from configuration."""
        layout_type = config.layout_type
        
        # Try registered templates first
        if layout_type in self._templates:
            factory = self._templates[layout_type]
            return factory(config)
        
        # Try providers
        for provider in self._providers:
            if layout_type in provider.get_supported_layouts():
                if provider.validate_configuration(config):
                    container = provider.create_layout(layout_type, config)
                    # For now, just use the container directly
                    # In a full implementation, we'd create a wrapper
                    logger.warning(f"Provider-based layouts not fully implemented yet for {layout_type}")
        
        raise ValueError(f"No template or provider found for layout type: {layout_type}")
    
    def _connect_layout_signals(self, layout: BaseLayout) -> None:
        """Connect layout signals to manager handlers."""
        layout.state_changed.connect(self._handle_layout_state_change)
        layout.error_occurred.connect(self._handle_layout_error)
        layout.item_added.connect(self._handle_layout_item_added)
        layout.item_removed.connect(self._handle_layout_item_removed)
    
    def activate_layout(self, layout_id: str) -> bool:
        """Activate a specific layout."""
        if layout_id not in self._layouts:
            logger.error(f"Layout {layout_id} not found")
            return False
        
        try:
            layout = self._layouts[layout_id]
            
            # Deactivate current layout if exists
            if self._current_layout and self._current_layout != layout:
                self.deactivate_current_layout()
            
            # Activate new layout
            if layout.activate():
                self._current_layout = layout
                
                # Add to layout stack
                if layout.container and self._layout_stack:
                    if self._layout_stack.indexOf(layout.container) == -1:
                        self._layout_stack.addWidget(layout.container)
                    self._layout_stack.setCurrentWidget(layout.container)
                
                # Update history
                self._add_to_history(layout_id)
                
                # Emit signal
                self.layout_activated.emit(layout.config)
                
                # Publish event
                self.publish_event("layout.activated", {
                    "layout_id": layout_id,
                    "layout_type": layout.config.layout_type.value,
                    "layout_name": layout.config.name
                })
                
                logger.info(f"Activated layout: {layout.config.name}")
                return True
            else:
                logger.error(f"Failed to activate layout: {layout_id}")
                return False
                
        except Exception as e:
            error_msg = f"Error activating layout {layout_id}: {e}"
            logger.error(error_msg)
            self.layout_error.emit(layout_id, error_msg)
            return False
    
    def deactivate_current_layout(self) -> bool:
        """Deactivate the currently active layout."""
        if not self._current_layout:
            return True
        
        try:
            layout_id = self._current_layout.config.id
            
            # Save current state before deactivating
            self._save_layout_state(self._current_layout)
            
            # Deactivate layout
            if self._current_layout.deactivate():
                # Remove from layout stack
                if self._current_layout.container and self._layout_stack:
                    self._layout_stack.removeWidget(self._current_layout.container)
                
                # Emit signal
                self.layout_deactivated.emit(layout_id)
                
                # Publish event
                self.publish_event("layout.deactivated", {
                    "layout_id": layout_id
                })
                
                self._current_layout = None
                logger.info(f"Deactivated layout: {layout_id}")
                return True
            else:
                logger.error(f"Failed to deactivate layout: {layout_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deactivating current layout: {e}")
            return False
    
    def switch_layout(self, target_layout_id: str, transition: bool = True) -> bool:
        """Switch to a different layout with optional transition."""
        if not self._switching_enabled:
            logger.warning("Layout switching is currently disabled")
            return False
        
        if target_layout_id not in self._layouts:
            logger.error(f"Target layout {target_layout_id} not found")
            return False
        
        try:
            current_id = self._current_layout.config.id if self._current_layout else None
            
            if transition and self._transition_duration > 0:
                # Start transition
                self._pending_layout = target_layout_id
                self._transition_timer.start(self._transition_duration)
                logger.debug(f"Starting layout transition: {current_id} -> {target_layout_id}")
            else:
                # Immediate switch
                self._perform_layout_switch(target_layout_id)
            
            # Emit signal
            self.layout_switched.emit(current_id or "", target_layout_id)
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to switch layout: {e}"
            logger.error(error_msg)
            self.layout_error.emit(target_layout_id, error_msg)
            return False
    
    def _perform_layout_switch(self, target_layout_id: str) -> None:
        """Perform the actual layout switch."""
        # Deactivate current layout
        if self._current_layout:
            self.deactivate_current_layout()
        
        # Activate target layout
        self.activate_layout(target_layout_id)
    
    def _complete_layout_transition(self) -> None:
        """Complete a layout transition."""
        if self._pending_layout:
            self._perform_layout_switch(self._pending_layout)
            self._pending_layout = None
    
    def get_current_layout(self) -> Optional[BaseLayout]:
        """Get the currently active layout."""
        return self._current_layout
    
    def get_layout(self, layout_id: str) -> Optional[BaseLayout]:
        """Get a specific layout by ID."""
        return self._layouts.get(layout_id)
    
    def get_layouts(self) -> Dict[str, BaseLayout]:
        """Get all managed layouts."""
        return self._layouts.copy()
    
    def get_layout_types(self) -> List[LayoutType]:
        """Get all available layout types."""
        types = set(self._templates.keys())
        
        for provider in self._providers:
            types.update(provider.get_supported_layouts())
        
        return list(types)
    
    def add_component_to_layout(
        self,
        layout_id: str,
        component_id: str,
        **kwargs
    ) -> bool:
        """Add a registered component to a specific layout."""
        if layout_id not in self._layouts:
            logger.error(f"Layout {layout_id} not found")
            return False
        
        if component_id not in self._registered_components:
            logger.error(f"Component {component_id} not registered")
            return False
        
        try:
            layout = self._layouts[layout_id]
            widget = self._registered_components[component_id]
            
            # Create layout item
            item = LayoutItem(
                id=component_id,
                widget=widget,
                name=kwargs.get('name', component_id),
                layout_type=layout.config.layout_type,
                geometry=kwargs.get('geometry', LayoutGeometry()),
                visible=kwargs.get('visible', True),
                stretch_factor=kwargs.get('stretch_factor', 1),
                properties=kwargs.get('properties', {})
            )
            
            # Add to layout
            if layout.add_item(item):
                self._component_layouts[component_id] = layout_id
                self._registry.register_item(item)
                
                logger.debug(f"Added component {component_id} to layout {layout_id}")
                return True
            else:
                logger.error(f"Failed to add component {component_id} to layout {layout_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error adding component to layout: {e}")
            return False
    
    def remove_component_from_layout(self, layout_id: str, component_id: str) -> bool:
        """Remove a component from a specific layout."""
        if layout_id not in self._layouts:
            logger.error(f"Layout {layout_id} not found")
            return False
        
        try:
            layout = self._layouts[layout_id]
            
            if layout.remove_item(component_id):
                self._component_layouts.pop(component_id, None)
                self._registry.unregister_item(component_id)
                
                logger.debug(f"Removed component {component_id} from layout {layout_id}")
                return True
            else:
                logger.error(f"Failed to remove component {component_id} from layout {layout_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing component from layout: {e}")
            return False
    
    def delete_layout(self, layout_id: str) -> bool:
        """Delete a layout."""
        if layout_id not in self._layouts:
            logger.warning(f"Layout {layout_id} not found for deletion")
            return True
        
        try:
            layout = self._layouts[layout_id]
            
            # Deactivate if current
            if self._current_layout == layout:
                self.deactivate_current_layout()
            
            # Remove from stack
            if layout.container and self._layout_stack:
                self._layout_stack.removeWidget(layout.container)
            
            # Clean up components
            components_to_remove = [
                comp_id for comp_id, comp_layout_id in self._component_layouts.items()
                if comp_layout_id == layout_id
            ]
            
            for comp_id in components_to_remove:
                del self._component_layouts[comp_id]
                self._registry.unregister_item(comp_id)
            
            # Delete layout
            del self._layouts[layout_id]
            
            # Remove from history
            self._layout_history = [lid for lid in self._layout_history if lid != layout_id]
            if self._history_index >= len(self._layout_history):
                self._history_index = len(self._layout_history) - 1
            
            logger.info(f"Deleted layout: {layout_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting layout {layout_id}: {e}")
            return False
    
    def _add_to_history(self, layout_id: str) -> None:
        """Add layout to history."""
        # Remove if already exists
        if layout_id in self._layout_history:
            self._layout_history.remove(layout_id)
        
        # Add to end
        self._layout_history.append(layout_id)
        
        # Trim history if too long
        if len(self._layout_history) > self._max_history:
            self._layout_history.pop(0)
        
        self._history_index = len(self._layout_history) - 1
    
    def go_back(self) -> bool:
        """Go back in layout history."""
        if self._history_index > 0:
            self._history_index -= 1
            layout_id = self._layout_history[self._history_index]
            return self.switch_layout(layout_id, transition=False)
        return False
    
    def go_forward(self) -> bool:
        """Go forward in layout history."""
        if self._history_index < len(self._layout_history) - 1:
            self._history_index += 1
            layout_id = self._layout_history[self._history_index]
            return self.switch_layout(layout_id, transition=False)
        return False
    
    def _save_layout_state(self, layout: BaseLayout) -> None:
        """Save layout state to configuration."""
        try:
            state = layout.save_state()
            self.set_config(f"layouts.saved.{layout.config.id}", state)
            
        except Exception as e:
            logger.warning(f"Failed to save layout state: {e}")
    
    def _auto_save_current_layout(self) -> None:
        """Auto-save current layout state."""
        if self._current_layout:
            self._save_layout_state(self._current_layout)
    
    def set_switching_enabled(self, enabled: bool) -> None:
        """Enable or disable layout switching."""
        self._switching_enabled = enabled
    
    def is_switching_enabled(self) -> bool:
        """Check if layout switching is enabled."""
        return self._switching_enabled
    
    def set_transition_duration(self, duration_ms: int) -> None:
        """Set layout transition duration."""
        self._transition_duration = max(0, duration_ms)
    
    def get_transition_duration(self) -> int:
        """Get layout transition duration."""
        return self._transition_duration
    
    @contextmanager
    def switching_disabled(self):
        """Context manager to temporarily disable layout switching."""
        was_enabled = self._switching_enabled
        self._switching_enabled = False
        try:
            yield
        finally:
            self._switching_enabled = was_enabled
    
    # Event handlers
    def _handle_layout_state_change(self, state: LayoutState) -> None:
        """Handle layout state change."""
        sender = self.sender()
        if isinstance(sender, BaseLayout):
            layout_id = sender.config.id
            
            self.publish_event("layout.state_changed", {
                "layout_id": layout_id,
                "state": state.value
            })
    
    def _handle_layout_error(self, error_message: str) -> None:
        """Handle layout error."""
        sender = self.sender()
        if isinstance(sender, BaseLayout):
            layout_id = sender.config.id
            self.layout_error.emit(layout_id, error_message)
    
    def _handle_layout_item_added(self, item: LayoutItem) -> None:
        """Handle layout item added."""
        self._registry.register_item(item)
    
    def _handle_layout_item_removed(self, item_id: str) -> None:
        """Handle layout item removed."""
        self._registry.unregister_item(item_id)
    
    def _handle_layout_switch_request(self, event_data: Dict[str, Any]) -> None:
        """Handle layout switch request from events."""
        layout_id = event_data.get("layout_id")
        if layout_id:
            self.switch_layout(layout_id)
    
    def _handle_layout_save_request(self, event_data: Dict[str, Any]) -> None:
        """Handle layout save request from events."""
        layout_id = event_data.get("layout_id")
        if layout_id and layout_id in self._layouts:
            self._save_layout_state(self._layouts[layout_id])
    
    def _handle_window_resize(self, event_data: Dict[str, Any]) -> None:
        """Handle window resize event."""
        if self._current_layout:
            size = event_data.get("size", {})
            if size:
                geometry = LayoutGeometry(
                    width=size.get("width", 800),
                    height=size.get("height", 600)
                )
                self._current_layout.update_geometry(geometry)