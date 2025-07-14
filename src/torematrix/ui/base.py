"""Base UI components and patterns for ToreMatrix V3."""

from typing import Optional, Any, Dict, TYPE_CHECKING
from abc import ABC, abstractmethod

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:
    from ..core.events import EventBus
    from ..core.config import ConfigManager
    from ..core.state import StateManager


class UIError(Exception):
    """Base exception for UI-related errors."""
    pass


class BaseUIComponent(QObject):
    """Base class for all UI components with common patterns."""
    
    # Common signals
    component_ready = pyqtSignal()
    component_error = pyqtSignal(str)
    
    def __init__(
        self,
        event_bus: 'EventBus',
        config_manager: Optional['ConfigManager'] = None,
        state_manager: Optional['StateManager'] = None,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        
        # Core dependencies
        self._event_bus = event_bus
        self._config_manager = config_manager
        self._state_manager = state_manager
        
        # Component state
        self._initialized = False
        self._component_id = self.__class__.__name__
    
    @property
    def component_id(self) -> str:
        """Get the component identifier."""
        return self._component_id
    
    @property
    def is_initialized(self) -> bool:
        """Check if component is initialized."""
        return self._initialized
    
    def initialize(self) -> None:
        """Initialize the component."""
        if self._initialized:
            return
        
        try:
            self._setup_component()
            self._connect_events()
            self._initialized = True
            self.component_ready.emit()
        except Exception as e:
            error_msg = f"Failed to initialize {self._component_id}: {str(e)}"
            self.component_error.emit(error_msg)
            raise UIError(error_msg) from e
    
    @abstractmethod
    def _setup_component(self) -> None:
        """Setup the component-specific functionality."""
        pass
    
    def _connect_events(self) -> None:
        """Connect to event bus signals. Override in subclasses."""
        pass
    
    def publish_event(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Publish an event to the event bus."""
        event_data = data or {}
        event_data["source"] = self._component_id
        self._event_bus.publish(event_type, event_data)
    
    def subscribe_to_event(self, event_type: str, handler) -> None:
        """Subscribe to an event type."""
        self._event_bus.subscribe(event_type, handler)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        if self._config_manager:
            return self._config_manager.get(key, default)
        return default
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """Get a state value."""
        if self._state_manager:
            return self._state_manager.get_state(key, default)
        return default
    
    def set_state(self, key: str, value: Any) -> None:
        """Set a state value."""
        if self._state_manager:
            self._state_manager.set_state(key, value)


class BaseUIWidget(QWidget, BaseUIComponent):
    """Base class for UI widgets combining QWidget and BaseUIComponent."""
    
    def __init__(
        self,
        event_bus: 'EventBus',
        config_manager: Optional['ConfigManager'] = None,
        state_manager: Optional['StateManager'] = None,
        parent: Optional[QWidget] = None
    ):
        QWidget.__init__(self, parent)
        BaseUIComponent.__init__(self, event_bus, config_manager, state_manager, parent)
    
    def show_error(self, message: str) -> None:
        """Show an error message to the user."""
        self.publish_event("ui.error", {"message": message})
    
    def show_info(self, message: str) -> None:
        """Show an information message to the user."""
        self.publish_event("ui.info", {"message": message})
    
    def show_warning(self, message: str) -> None:
        """Show a warning message to the user."""
        self.publish_event("ui.warning", {"message": message})