"""Base layout classes and interfaces for ToreMatrix Layout Management System.

This module provides the foundational classes and interfaces that all layout
managers and templates inherit from, ensuring consistent behavior and type safety.
"""

from typing import Dict, List, Optional, Any, Union, Protocol, runtime_checkable
from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
import logging
from uuid import uuid4

from PyQt6.QtWidgets import QWidget, QSplitter, QTabWidget, QLayout, QLayoutItem
from PyQt6.QtCore import QObject, QSize, QRect, pyqtSignal, QMargins
from PyQt6.QtGui import QResizeEvent

logger = logging.getLogger(__name__)


class LayoutType(Enum):
    """Available layout types."""
    DOCUMENT = "document"
    SPLIT_HORIZONTAL = "split_horizontal" 
    SPLIT_VERTICAL = "split_vertical"
    TABBED = "tabbed"
    MULTI_PANEL = "multi_panel"
    CUSTOM = "custom"


class LayoutState(Enum):
    """Layout state indicators."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    TRANSITIONING = "transitioning"
    ERROR = "error"


@dataclass
class LayoutGeometry:
    """Layout geometry information."""
    x: int = 0
    y: int = 0
    width: int = 800
    height: int = 600
    margins: QMargins = field(default_factory=lambda: QMargins(0, 0, 0, 0))
    
    def to_rect(self) -> QRect:
        """Convert to QRect."""
        return QRect(self.x, self.y, self.width, self.height)
    
    def to_size(self) -> QSize:
        """Convert to QSize."""
        return QSize(self.width, self.height)


@dataclass
class LayoutItem:
    """Represents an item within a layout."""
    id: str
    widget: QWidget
    name: str
    layout_type: LayoutType
    geometry: LayoutGeometry
    visible: bool = True
    stretch_factor: int = 1
    minimum_size: Optional[QSize] = None
    maximum_size: Optional[QSize] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Post-initialization setup."""
        if not self.id:
            self.id = str(uuid4())


@dataclass
class LayoutConfiguration:
    """Complete layout configuration."""
    id: str
    name: str
    layout_type: LayoutType
    geometry: LayoutGeometry
    items: List[LayoutItem] = field(default_factory=list)
    splitter_states: Dict[str, bytes] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0"
    
    def __post_init__(self):
        """Post-initialization setup."""
        if not self.id:
            self.id = str(uuid4())


@runtime_checkable
class LayoutProvider(Protocol):
    """Protocol for layout providers."""
    
    def get_supported_layouts(self) -> List[LayoutType]:
        """Get list of supported layout types."""
        ...
    
    def create_layout(self, layout_type: LayoutType, config: LayoutConfiguration) -> QWidget:
        """Create a layout of the specified type."""
        ...
    
    def validate_configuration(self, config: LayoutConfiguration) -> bool:
        """Validate a layout configuration."""
        ...


class BaseLayout(QObject):
    """Base class for all layout implementations."""
    
    # Signals
    layout_changed = pyqtSignal(LayoutConfiguration)
    item_added = pyqtSignal(LayoutItem)
    item_removed = pyqtSignal(str)  # item_id
    geometry_changed = pyqtSignal(LayoutGeometry)
    state_changed = pyqtSignal(LayoutState)
    error_occurred = pyqtSignal(str)  # error_message
    
    def __init__(self, config: LayoutConfiguration, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._config = config
        self._state = LayoutState.INACTIVE
        self._items: Dict[str, LayoutItem] = {}
        self._container: Optional[QWidget] = None
        self._validated = False
        
        # Add items from config
        for item in config.items:
            self._items[item.id] = item
    
    @property
    def config(self) -> LayoutConfiguration:
        """Get layout configuration."""
        return self._config
    
    @property
    def state(self) -> LayoutState:
        """Get current layout state."""
        return self._state
    
    @property
    def container(self) -> Optional[QWidget]:
        """Get layout container widget."""
        return self._container
    
    @property
    def items(self) -> Dict[str, LayoutItem]:
        """Get all layout items."""
        return self._items.copy()
    
    def set_state(self, state: LayoutState) -> None:
        """Set layout state."""
        if state != self._state:
            old_state = self._state
            self._state = state
            self.state_changed.emit(state)
            logger.debug(f"Layout {self._config.id} state changed: {old_state} -> {state}")
    
    @abstractmethod
    def create_container(self) -> QWidget:
        """Create the main container widget for this layout."""
        pass
    
    @abstractmethod
    def apply_layout(self) -> bool:
        """Apply the layout configuration to the container."""
        pass
    
    @abstractmethod
    def add_item(self, item: LayoutItem) -> bool:
        """Add an item to the layout."""
        pass
    
    @abstractmethod
    def remove_item(self, item_id: str) -> bool:
        """Remove an item from the layout."""
        pass
    
    @abstractmethod
    def update_item(self, item_id: str, item: LayoutItem) -> bool:
        """Update an existing layout item."""
        pass
    
    def validate(self) -> bool:
        """Validate the layout configuration."""
        try:
            # Basic validation
            if not self._config.name:
                raise ValueError("Layout name cannot be empty")
            
            if not self._config.layout_type:
                raise ValueError("Layout type must be specified")
            
            # Validate items
            for item in self._config.items:
                if not item.widget:
                    raise ValueError(f"Layout item {item.id} has no widget")
                
                if not item.name:
                    raise ValueError(f"Layout item {item.id} has no name")
            
            # Check for duplicate item IDs
            item_ids = [item.id for item in self._config.items]
            if len(item_ids) != len(set(item_ids)):
                raise ValueError("Duplicate item IDs found in layout")
            
            self._validated = True
            return True
            
        except Exception as e:
            error_msg = f"Layout validation failed: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self._validated = False
            return False
    
    def is_validated(self) -> bool:
        """Check if layout has been validated."""
        return self._validated
    
    def activate(self) -> bool:
        """Activate the layout."""
        if not self.validate():
            return False
        
        try:
            self.set_state(LayoutState.TRANSITIONING)
            
            # Create container if not exists
            if not self._container:
                self._container = self.create_container()
            
            # Apply layout
            if not self.apply_layout():
                self.set_state(LayoutState.ERROR)
                return False
            
            self.set_state(LayoutState.ACTIVE)
            logger.info(f"Layout {self._config.id} activated successfully")
            return True
            
        except Exception as e:
            error_msg = f"Failed to activate layout {self._config.id}: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.set_state(LayoutState.ERROR)
            return False
    
    def deactivate(self) -> bool:
        """Deactivate the layout."""
        try:
            self.set_state(LayoutState.TRANSITIONING)
            
            # Clean up container
            if self._container:
                self._container.setParent(None)
                self._container = None
            
            self.set_state(LayoutState.INACTIVE)
            logger.info(f"Layout {self._config.id} deactivated successfully")
            return True
            
        except Exception as e:
            error_msg = f"Failed to deactivate layout {self._config.id}: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            self.set_state(LayoutState.ERROR)
            return False
    
    def get_item(self, item_id: str) -> Optional[LayoutItem]:
        """Get layout item by ID."""
        return self._items.get(item_id)
    
    def get_items_by_type(self, layout_type: LayoutType) -> List[LayoutItem]:
        """Get all items of a specific layout type."""
        return [item for item in self._items.values() if item.layout_type == layout_type]
    
    def update_geometry(self, geometry: LayoutGeometry) -> None:
        """Update layout geometry."""
        self._config.geometry = geometry
        
        if self._container:
            rect = geometry.to_rect()
            self._container.setGeometry(rect)
        
        self.geometry_changed.emit(geometry)
    
    def save_state(self) -> Dict[str, Any]:
        """Save current layout state."""
        state = {
            "config": {
                "id": self._config.id,
                "name": self._config.name,
                "layout_type": self._config.layout_type.value,
                "geometry": {
                    "x": self._config.geometry.x,
                    "y": self._config.geometry.y,
                    "width": self._config.geometry.width,
                    "height": self._config.geometry.height,
                    "margins": [
                        self._config.geometry.margins.left(),
                        self._config.geometry.margins.top(),
                        self._config.geometry.margins.right(),
                        self._config.geometry.margins.bottom()
                    ]
                },
                "properties": self._config.properties,
                "version": self._config.version
            },
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "layout_type": item.layout_type.value,
                    "visible": item.visible,
                    "stretch_factor": item.stretch_factor,
                    "geometry": {
                        "x": item.geometry.x,
                        "y": item.geometry.y,
                        "width": item.geometry.width,
                        "height": item.geometry.height
                    },
                    "properties": item.properties
                }
                for item in self._items.values()
            ],
            "splitter_states": self._config.splitter_states,
            "state": self._state.value
        }
        
        return state
    
    def restore_state(self, state: Dict[str, Any]) -> bool:
        """Restore layout from saved state."""
        try:
            # Restore configuration
            config_data = state["config"]
            self._config.id = config_data["id"]
            self._config.name = config_data["name"]
            self._config.layout_type = LayoutType(config_data["layout_type"])
            self._config.properties = config_data.get("properties", {})
            self._config.version = config_data.get("version", "1.0")
            
            # Restore geometry
            geo_data = config_data["geometry"]
            margins_data = geo_data.get("margins", [0, 0, 0, 0])
            self._config.geometry = LayoutGeometry(
                x=geo_data["x"],
                y=geo_data["y"],
                width=geo_data["width"],
                height=geo_data["height"],
                margins=QMargins(*margins_data)
            )
            
            # Restore splitter states
            self._config.splitter_states = state.get("splitter_states", {})
            
            # Note: Items restoration handled by derived classes since widgets can't be serialized
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to restore layout state: {e}"
            logger.error(error_msg)
            self.error_occurred.emit(error_msg)
            return False


class LayoutItemRegistry:
    """Registry for layout items and widgets."""
    
    def __init__(self):
        self._widgets: Dict[str, QWidget] = {}
        self._items: Dict[str, LayoutItem] = {}
    
    def register_widget(self, widget_id: str, widget: QWidget) -> None:
        """Register a widget."""
        self._widgets[widget_id] = widget
    
    def unregister_widget(self, widget_id: str) -> None:
        """Unregister a widget."""
        self._widgets.pop(widget_id, None)
    
    def get_widget(self, widget_id: str) -> Optional[QWidget]:
        """Get a registered widget."""
        return self._widgets.get(widget_id)
    
    def register_item(self, item: LayoutItem) -> None:
        """Register a layout item."""
        self._items[item.id] = item
        if item.widget:
            self.register_widget(item.id, item.widget)
    
    def unregister_item(self, item_id: str) -> None:
        """Unregister a layout item."""
        self._items.pop(item_id, None)
        self.unregister_widget(item_id)
    
    def get_item(self, item_id: str) -> Optional[LayoutItem]:
        """Get a registered layout item."""
        return self._items.get(item_id)
    
    def get_all_items(self) -> List[LayoutItem]:
        """Get all registered layout items."""
        return list(self._items.values())
    
    def clear(self) -> None:
        """Clear all registrations."""
        self._widgets.clear()
        self._items.clear()