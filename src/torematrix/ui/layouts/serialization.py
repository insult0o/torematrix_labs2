"""Layout serialization system for ToreMatrix V3.

Provides JSON-based layout serialization and deserialization with type safety,
version compatibility, and error handling.
"""

from typing import Dict, List, Optional, Any, Union, Type, TypeVar
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import logging
from enum import Enum

from PyQt6.QtWidgets import (
    QWidget, QSplitter, QTabWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout, QLayout
)
from PyQt6.QtCore import QSize, QRect, QPoint
from PyQt6.QtGui import QScreen

from ..base import BaseUIComponent
from ...core.events import EventBus
from ...core.config import ConfigurationManager  
from ...core.state import Store

logger = logging.getLogger(__name__)

T = TypeVar('T')


class LayoutType(Enum):
    """Supported layout types for serialization."""
    SPLITTER = "splitter"
    TAB_WIDGET = "tab_widget"
    STACKED_WIDGET = "stacked_widget"
    VBOX_LAYOUT = "vbox_layout"
    HBOX_LAYOUT = "hbox_layout"
    GRID_LAYOUT = "grid_layout"
    WIDGET = "widget"
    CUSTOM = "custom"


class SerializationError(Exception):
    """Raised when layout serialization fails."""
    pass


class DeserializationError(Exception):
    """Raised when layout deserialization fails."""
    pass


@dataclass
class DisplayGeometry:
    """Display geometry information."""
    x: int
    y: int
    width: int
    height: int
    dpi: float
    name: str = ""
    primary: bool = False


@dataclass
class LayoutMetadata:
    """Layout metadata information."""
    name: str
    version: str = "1.0.0"
    created: datetime = None
    modified: datetime = None
    author: str = ""
    description: str = ""
    tags: List[str] = None
    
    def __post_init__(self):
        if self.created is None:
            self.created = datetime.now(timezone.utc)
        if self.modified is None:
            self.modified = self.created
        if self.tags is None:
            self.tags = []


@dataclass
class ComponentState:
    """Serializable component state."""
    visible: bool = True
    enabled: bool = True
    geometry: Optional[Dict[str, int]] = None
    size_policy: Optional[Dict[str, Any]] = None
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = {}


@dataclass
class LayoutNode:
    """Represents a node in the layout tree."""
    type: LayoutType
    component_id: str
    state: ComponentState
    children: List['LayoutNode'] = None
    properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.properties is None:
            self.properties = {}


@dataclass
class SerializedLayout:
    """Complete serialized layout structure."""
    metadata: LayoutMetadata
    displays: List[DisplayGeometry]
    layout: LayoutNode
    global_properties: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.global_properties is None:
            self.global_properties = {}


class LayoutSerializer:
    """Serializes Qt layout structures to JSON format."""
    
    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        config_manager: Optional[ConfigurationManager] = None,
        state_manager: Optional[Store] = None
    ):
        self._event_bus = event_bus
        self._config_manager = config_manager
        self._state_manager = state_manager
        self._component_registry: Dict[QWidget, str] = {}
        self._serialization_handlers: Dict[Type, callable] = {}
        
        self._setup_default_handlers()
        
    def _setup_default_handlers(self) -> None:
        """Setup default serialization handlers for Qt widgets."""
        self._serialization_handlers.update({
            QSplitter: self._serialize_splitter,
            QTabWidget: self._serialize_tab_widget,
            QStackedWidget: self._serialize_stacked_widget,
            QVBoxLayout: self._serialize_vbox_layout,
            QHBoxLayout: self._serialize_hbox_layout,
            QGridLayout: self._serialize_grid_layout,
            QWidget: self._serialize_widget,
        })
    
    def register_component(self, widget: QWidget, component_id: str) -> None:
        """Register a component with a unique identifier."""
        self._component_registry[widget] = component_id
        logger.debug(f"Registered component {component_id} for widget {type(widget).__name__}")
    
    def register_serialization_handler(
        self,
        widget_type: Type,
        handler: callable
    ) -> None:
        """Register custom serialization handler for widget type."""
        self._serialization_handlers[widget_type] = handler
        logger.debug(f"Registered serialization handler for {widget_type.__name__}")
    
    def serialize_layout(
        self,
        root_widget: QWidget,
        metadata: LayoutMetadata,
        displays: Optional[List[QScreen]] = None
    ) -> SerializedLayout:
        """Serialize a complete layout to structured format."""
        try:
            # Serialize display information
            display_geometries = self._serialize_displays(displays or [])
            
            # Serialize layout tree
            layout_tree = self._serialize_widget_tree(root_widget)
            
            # Create serialized layout
            serialized = SerializedLayout(
                metadata=metadata,
                displays=display_geometries,
                layout=layout_tree,
                global_properties=self._get_global_properties(root_widget)
            )
            
            # Publish event
            if self._event_bus:
                self._event_bus.publish("layout.serialized", {
                    "layout_name": metadata.name,
                    "node_count": self._count_nodes(layout_tree)
                })
            
            logger.info(f"Successfully serialized layout '{metadata.name}'")
            return serialized
            
        except Exception as e:
            logger.error(f"Failed to serialize layout: {e}")
            raise SerializationError(f"Layout serialization failed: {e}") from e
    
    def serialize_to_json(
        self,
        root_widget: QWidget,
        metadata: LayoutMetadata,
        displays: Optional[List[QScreen]] = None,
        indent: int = 2
    ) -> str:
        """Serialize layout directly to JSON string."""
        serialized = self.serialize_layout(root_widget, metadata, displays)
        return self._to_json(serialized, indent)
    
    def _serialize_displays(self, displays: List[QScreen]) -> List[DisplayGeometry]:
        """Serialize display information."""
        geometries = []
        
        for i, screen in enumerate(displays):
            if screen:
                rect = screen.geometry()
                geometries.append(DisplayGeometry(
                    x=rect.x(),
                    y=rect.y(),
                    width=rect.width(),
                    height=rect.height(),
                    dpi=screen.logicalDotsPerInch(),
                    name=screen.name() or f"Display_{i}",
                    primary=(i == 0)  # Assume first is primary
                ))
        
        return geometries
    
    def _serialize_widget_tree(self, widget: QWidget) -> LayoutNode:
        """Recursively serialize widget tree."""
        # Get component ID
        component_id = self._component_registry.get(widget, self._generate_component_id(widget))
        
        # Determine widget type
        layout_type = self._determine_layout_type(widget)
        
        # Serialize component state
        state = self._serialize_component_state(widget)
        
        # Get type-specific properties
        properties = self._get_widget_properties(widget)
        
        # Create layout node
        node = LayoutNode(
            type=layout_type,
            component_id=component_id,
            state=state,
            properties=properties
        )
        
        # Serialize children
        node.children = self._serialize_children(widget)
        
        return node
    
    def _determine_layout_type(self, widget: QWidget) -> LayoutType:
        """Determine the layout type for a widget."""
        widget_type = type(widget)
        
        if widget_type == QSplitter:
            return LayoutType.SPLITTER
        elif widget_type == QTabWidget:
            return LayoutType.TAB_WIDGET
        elif widget_type == QStackedWidget:
            return LayoutType.STACKED_WIDGET
        elif isinstance(widget, QWidget) and widget.layout():
            layout = widget.layout()
            layout_type = type(layout)
            
            if layout_type == QVBoxLayout:
                return LayoutType.VBOX_LAYOUT
            elif layout_type == QHBoxLayout:
                return LayoutType.HBOX_LAYOUT
            elif layout_type == QGridLayout:
                return LayoutType.GRID_LAYOUT
        
        return LayoutType.WIDGET
    
    def _serialize_component_state(self, widget: QWidget) -> ComponentState:
        """Serialize component state."""
        geometry = None
        if widget.geometry().isValid():
            rect = widget.geometry()
            geometry = {
                "x": rect.x(),
                "y": rect.y(),
                "width": rect.width(),
                "height": rect.height()
            }
        
        size_policy = None
        if widget.sizePolicy():
            policy = widget.sizePolicy()
            size_policy = {
                "horizontal": policy.horizontalPolicy(),
                "vertical": policy.verticalPolicy(),
                "horizontal_stretch": policy.horizontalStretch(),
                "vertical_stretch": policy.verticalStretch()
            }
        
        return ComponentState(
            visible=widget.isVisible(),
            enabled=widget.isEnabled(),
            geometry=geometry,
            size_policy=size_policy,
            properties=self._get_component_properties(widget)
        )
    
    def _get_widget_properties(self, widget: QWidget) -> Dict[str, Any]:
        """Get widget-specific properties."""
        handler = self._serialization_handlers.get(type(widget))
        if handler:
            try:
                return handler(widget)
            except Exception as e:
                logger.warning(f"Failed to serialize properties for {type(widget).__name__}: {e}")
                return {}
        
        return {}
    
    def _serialize_children(self, widget: QWidget) -> List[LayoutNode]:
        """Serialize child widgets."""
        children = []
        
        # Handle different container types
        if isinstance(widget, QSplitter):
            for i in range(widget.count()):
                child = widget.widget(i)
                if child:
                    children.append(self._serialize_widget_tree(child))
                    
        elif isinstance(widget, QTabWidget):
            for i in range(widget.count()):
                child = widget.widget(i)
                if child:
                    child_node = self._serialize_widget_tree(child)
                    # Add tab-specific properties
                    child_node.properties.update({
                        "tab_text": widget.tabText(i),
                        "tab_tooltip": widget.tabToolTip(i),
                        "tab_index": i
                    })
                    children.append(child_node)
                    
        elif isinstance(widget, QStackedWidget):
            for i in range(widget.count()):
                child = widget.widget(i)
                if child:
                    child_node = self._serialize_widget_tree(child)
                    child_node.properties["stack_index"] = i
                    children.append(child_node)
                    
        elif widget.layout():
            layout = widget.layout()
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget():
                    child = item.widget()
                    child_node = self._serialize_widget_tree(child)
                    
                    # Add layout-specific properties
                    if isinstance(layout, QGridLayout):
                        row, col, row_span, col_span = layout.getItemPosition(i)
                        child_node.properties.update({
                            "grid_row": row,
                            "grid_column": col,
                            "grid_row_span": row_span,
                            "grid_column_span": col_span
                        })
                    
                    children.append(child_node)
        
        return children
    
    def _serialize_splitter(self, splitter: QSplitter) -> Dict[str, Any]:
        """Serialize QSplitter properties."""
        sizes = splitter.sizes()
        return {
            "orientation": splitter.orientation(),
            "sizes": sizes,
            "handle_width": splitter.handleWidth(),
            "children_collapsible": splitter.childrenCollapsible(),
            "opaqueResize": splitter.opaqueResize()
        }
    
    def _serialize_tab_widget(self, tab_widget: QTabWidget) -> Dict[str, Any]:
        """Serialize QTabWidget properties."""
        return {
            "current_index": tab_widget.currentIndex(),
            "tab_position": tab_widget.tabPosition(),
            "tab_shape": tab_widget.tabShape(),
            "tabs_closable": tab_widget.tabsClosable(),
            "tabs_movable": tab_widget.tabsMovable(),
            "document_mode": tab_widget.documentMode()
        }
    
    def _serialize_stacked_widget(self, stacked: QStackedWidget) -> Dict[str, Any]:
        """Serialize QStackedWidget properties."""
        return {
            "current_index": stacked.currentIndex()
        }
    
    def _serialize_vbox_layout(self, layout: QVBoxLayout) -> Dict[str, Any]:
        """Serialize QVBoxLayout properties."""
        margins = layout.contentsMargins()
        return {
            "spacing": layout.spacing(),
            "margins": {
                "left": margins.left(),
                "top": margins.top(),
                "right": margins.right(),
                "bottom": margins.bottom()
            }
        }
    
    def _serialize_hbox_layout(self, layout: QHBoxLayout) -> Dict[str, Any]:
        """Serialize QHBoxLayout properties."""
        margins = layout.contentsMargins()
        return {
            "spacing": layout.spacing(),
            "margins": {
                "left": margins.left(),
                "top": margins.top(),
                "right": margins.right(),
                "bottom": margins.bottom()
            }
        }
    
    def _serialize_grid_layout(self, layout: QGridLayout) -> Dict[str, Any]:
        """Serialize QGridLayout properties."""
        margins = layout.contentsMargins()
        return {
            "horizontal_spacing": layout.horizontalSpacing(),
            "vertical_spacing": layout.verticalSpacing(),
            "margins": {
                "left": margins.left(),
                "top": margins.top(),
                "right": margins.right(),
                "bottom": margins.bottom()
            },
            "row_count": layout.rowCount(),
            "column_count": layout.columnCount()
        }
    
    def _serialize_widget(self, widget: QWidget) -> Dict[str, Any]:
        """Serialize generic QWidget properties."""
        return {
            "object_name": widget.objectName(),
            "style_sheet": widget.styleSheet(),
            "window_title": widget.windowTitle() if hasattr(widget, 'windowTitle') else "",
            "tooltip": widget.toolTip(),
            "status_tip": widget.statusTip(),
            "what_this": widget.whatsThis()
        }
    
    def _get_component_properties(self, widget: QWidget) -> Dict[str, Any]:
        """Get component-specific properties."""
        properties = {}
        
        # Add common properties that might be useful
        if hasattr(widget, 'text') and callable(widget.text):
            try:
                properties["text"] = widget.text()
            except Exception:
                pass
                
        if hasattr(widget, 'value') and callable(widget.value):
            try:
                properties["value"] = widget.value()
            except Exception:
                pass
        
        return properties
    
    def _get_global_properties(self, root_widget: QWidget) -> Dict[str, Any]:
        """Get global layout properties."""
        return {
            "root_widget_type": type(root_widget).__name__,
            "serialization_timestamp": datetime.now(timezone.utc).isoformat(),
            "qt_version": f"{QWidget.staticMetaObject.className()}",
        }
    
    def _generate_component_id(self, widget: QWidget) -> str:
        """Generate unique component ID for unregistered widgets."""
        widget_type = type(widget).__name__
        widget_id = id(widget)
        object_name = widget.objectName() or "unnamed"
        return f"{widget_type}_{object_name}_{widget_id}"
    
    def _count_nodes(self, node: LayoutNode) -> int:
        """Count total nodes in layout tree."""
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count
    
    def _to_json(self, serialized: SerializedLayout, indent: int = 2) -> str:
        """Convert serialized layout to JSON string."""
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        # Convert to dict
        data = asdict(serialized)
        
        # Convert enums to strings
        def convert_enums(obj):
            if isinstance(obj, dict):
                return {k: convert_enums(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_enums(item) for item in obj]
            elif isinstance(obj, Enum):
                return obj.value
            return obj
        
        data = convert_enums(data)
        
        return json.dumps(data, indent=indent, default=serialize_datetime, ensure_ascii=False)


class LayoutDeserializer:
    """Deserializes JSON layout structures back to Qt widgets."""
    
    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        config_manager: Optional[ConfigurationManager] = None,
        state_manager: Optional[Store] = None
    ):
        self._event_bus = event_bus
        self._config_manager = config_manager
        self._state_manager = state_manager
        self._component_factory: Dict[str, callable] = {}
        self._deserialization_handlers: Dict[LayoutType, callable] = {}
        
        self._setup_default_handlers()
    
    def _setup_default_handlers(self) -> None:
        """Setup default deserialization handlers."""
        self._deserialization_handlers.update({
            LayoutType.SPLITTER: self._deserialize_splitter,
            LayoutType.TAB_WIDGET: self._deserialize_tab_widget,
            LayoutType.STACKED_WIDGET: self._deserialize_stacked_widget,
            LayoutType.VBOX_LAYOUT: self._deserialize_vbox_layout,
            LayoutType.HBOX_LAYOUT: self._deserialize_hbox_layout,
            LayoutType.GRID_LAYOUT: self._deserialize_grid_layout,
            LayoutType.WIDGET: self._deserialize_widget,
        })
    
    def register_component_factory(self, component_id: str, factory: callable) -> None:
        """Register factory function for component creation."""
        self._component_factory[component_id] = factory
        logger.debug(f"Registered component factory for {component_id}")
    
    def register_deserialization_handler(
        self,
        layout_type: LayoutType,
        handler: callable
    ) -> None:
        """Register custom deserialization handler."""
        self._deserialization_handlers[layout_type] = handler
        logger.debug(f"Registered deserialization handler for {layout_type}")
    
    def deserialize_layout(self, serialized: SerializedLayout) -> QWidget:
        """Deserialize layout structure back to Qt widgets."""
        try:
            # Validate version compatibility
            self._validate_version(serialized.metadata.version)
            
            # Deserialize root widget
            root_widget = self._deserialize_node(serialized.layout)
            
            # Apply global properties
            self._apply_global_properties(root_widget, serialized.global_properties)
            
            # Publish event
            if self._event_bus:
                self._event_bus.publish("layout.deserialized", {
                    "layout_name": serialized.metadata.name,
                    "version": serialized.metadata.version
                })
            
            logger.info(f"Successfully deserialized layout '{serialized.metadata.name}'")
            return root_widget
            
        except Exception as e:
            logger.error(f"Failed to deserialize layout: {e}")
            raise DeserializationError(f"Layout deserialization failed: {e}") from e
    
    def deserialize_from_json(self, json_str: str) -> QWidget:
        """Deserialize layout from JSON string."""
        try:
            data = json.loads(json_str)
            
            # Convert to SerializedLayout
            serialized = self._from_dict(data)
            
            return self.deserialize_layout(serialized)
            
        except json.JSONDecodeError as e:
            raise DeserializationError(f"Invalid JSON format: {e}") from e
    
    def _validate_version(self, version: str) -> None:
        """Validate layout version compatibility."""
        # For now, accept all versions - migration system will handle upgrades
        logger.debug(f"Validating layout version: {version}")
    
    def _deserialize_node(self, node: LayoutNode) -> QWidget:
        """Deserialize a layout node to a Qt widget."""
        # Get deserialization handler
        handler = self._deserialization_handlers.get(node.type)
        if not handler:
            raise DeserializationError(f"No handler for layout type: {node.type}")
        
        # Create widget using handler
        widget = handler(node)
        
        # Apply component state
        self._apply_component_state(widget, node.state)
        
        # Deserialize children
        children = [self._deserialize_node(child) for child in node.children]
        
        # Add children to widget
        self._add_children_to_widget(widget, children, node)
        
        return widget
    
    def _deserialize_splitter(self, node: LayoutNode) -> QSplitter:
        """Deserialize QSplitter."""
        splitter = QSplitter()
        
        # Apply properties
        props = node.properties
        if "orientation" in props:
            splitter.setOrientation(props["orientation"])
        if "handle_width" in props:
            splitter.setHandleWidth(props["handle_width"])
        if "children_collapsible" in props:
            splitter.setChildrenCollapsible(props["children_collapsible"])
        if "opaqueResize" in props:
            splitter.setOpaqueResize(props["opaqueResize"])
        
        return splitter
    
    def _deserialize_tab_widget(self, node: LayoutNode) -> QTabWidget:
        """Deserialize QTabWidget."""
        tab_widget = QTabWidget()
        
        # Apply properties
        props = node.properties
        if "tab_position" in props:
            tab_widget.setTabPosition(props["tab_position"])
        if "tab_shape" in props:
            tab_widget.setTabShape(props["tab_shape"])
        if "tabs_closable" in props:
            tab_widget.setTabsClosable(props["tabs_closable"])
        if "tabs_movable" in props:
            tab_widget.setTabsMovable(props["tabs_movable"])
        if "document_mode" in props:
            tab_widget.setDocumentMode(props["document_mode"])
        
        return tab_widget
    
    def _deserialize_stacked_widget(self, node: LayoutNode) -> QStackedWidget:
        """Deserialize QStackedWidget."""
        return QStackedWidget()
    
    def _deserialize_vbox_layout(self, node: LayoutNode) -> QWidget:
        """Deserialize QVBoxLayout container."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Apply layout properties
        props = node.properties
        if "spacing" in props:
            layout.setSpacing(props["spacing"])
        if "margins" in props:
            margins = props["margins"]
            layout.setContentsMargins(
                margins.get("left", 0),
                margins.get("top", 0),
                margins.get("right", 0),
                margins.get("bottom", 0)
            )
        
        return widget
    
    def _deserialize_hbox_layout(self, node: LayoutNode) -> QWidget:
        """Deserialize QHBoxLayout container."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        # Apply layout properties
        props = node.properties
        if "spacing" in props:
            layout.setSpacing(props["spacing"])
        if "margins" in props:
            margins = props["margins"]
            layout.setContentsMargins(
                margins.get("left", 0),
                margins.get("top", 0),
                margins.get("right", 0),
                margins.get("bottom", 0)
            )
        
        return widget
    
    def _deserialize_grid_layout(self, node: LayoutNode) -> QWidget:
        """Deserialize QGridLayout container."""
        widget = QWidget()
        layout = QGridLayout(widget)
        
        # Apply layout properties
        props = node.properties
        if "horizontal_spacing" in props:
            layout.setHorizontalSpacing(props["horizontal_spacing"])
        if "vertical_spacing" in props:
            layout.setVerticalSpacing(props["vertical_spacing"])
        if "margins" in props:
            margins = props["margins"]
            layout.setContentsMargins(
                margins.get("left", 0),
                margins.get("top", 0),
                margins.get("right", 0),
                margins.get("bottom", 0)
            )
        
        return widget
    
    def _deserialize_widget(self, node: LayoutNode) -> QWidget:
        """Deserialize generic QWidget."""
        # Try to create using registered factory
        if node.component_id in self._component_factory:
            factory = self._component_factory[node.component_id]
            widget = factory()
        else:
            widget = QWidget()
        
        # Apply widget properties
        props = node.properties
        if "object_name" in props:
            widget.setObjectName(props["object_name"])
        if "style_sheet" in props:
            widget.setStyleSheet(props["style_sheet"])
        if "tooltip" in props:
            widget.setToolTip(props["tooltip"])
        if "status_tip" in props:
            widget.setStatusTip(props["status_tip"])
        if "what_this" in props:
            widget.setWhatsThis(props["what_this"])
        
        return widget
    
    def _apply_component_state(self, widget: QWidget, state: ComponentState) -> None:
        """Apply component state to widget."""
        widget.setVisible(state.visible)
        widget.setEnabled(state.enabled)
        
        # Apply geometry if available
        if state.geometry:
            geom = state.geometry
            widget.setGeometry(geom["x"], geom["y"], geom["width"], geom["height"])
        
        # Apply size policy if available
        if state.size_policy:
            policy = widget.sizePolicy()
            sp = state.size_policy
            
            if "horizontal" in sp:
                policy.setHorizontalPolicy(sp["horizontal"])
            if "vertical" in sp:
                policy.setVerticalPolicy(sp["vertical"])
            if "horizontal_stretch" in sp:
                policy.setHorizontalStretch(sp["horizontal_stretch"])
            if "vertical_stretch" in sp:
                policy.setVerticalStretch(sp["vertical_stretch"])
            
            widget.setSizePolicy(policy)
        
        # Apply component properties
        self._apply_component_properties(widget, state.properties)
    
    def _apply_component_properties(self, widget: QWidget, properties: Dict[str, Any]) -> None:
        """Apply component-specific properties."""
        for key, value in properties.items():
            if hasattr(widget, f'set{key.title()}') and callable(getattr(widget, f'set{key.title()}')):
                try:
                    setter = getattr(widget, f'set{key.title()}')
                    setter(value)
                except Exception as e:
                    logger.warning(f"Failed to set property {key} on {type(widget).__name__}: {e}")
    
    def _add_children_to_widget(
        self,
        parent: QWidget,
        children: List[QWidget],
        node: LayoutNode
    ) -> None:
        """Add child widgets to parent widget."""
        if isinstance(parent, QSplitter):
            for child in children:
                parent.addWidget(child)
            
            # Restore splitter sizes
            if "sizes" in node.properties:
                parent.setSizes(node.properties["sizes"])
                
        elif isinstance(parent, QTabWidget):
            for i, child in enumerate(children):
                child_node = node.children[i] if i < len(node.children) else None
                tab_text = ""
                tab_tooltip = ""
                
                if child_node and child_node.properties:
                    tab_text = child_node.properties.get("tab_text", f"Tab {i+1}")
                    tab_tooltip = child_node.properties.get("tab_tooltip", "")
                
                parent.addTab(child, tab_text)
                if tab_tooltip:
                    parent.setTabToolTip(i, tab_tooltip)
            
            # Restore current tab
            if "current_index" in node.properties:
                parent.setCurrentIndex(node.properties["current_index"])
                
        elif isinstance(parent, QStackedWidget):
            for child in children:
                parent.addWidget(child)
            
            # Restore current widget
            if "current_index" in node.properties:
                parent.setCurrentIndex(node.properties["current_index"])
                
        elif parent.layout():
            layout = parent.layout()
            
            if isinstance(layout, QGridLayout):
                for i, child in enumerate(children):
                    child_node = node.children[i] if i < len(node.children) else None
                    
                    if child_node and child_node.properties:
                        row = child_node.properties.get("grid_row", 0)
                        col = child_node.properties.get("grid_column", 0)
                        row_span = child_node.properties.get("grid_row_span", 1)
                        col_span = child_node.properties.get("grid_column_span", 1)
                        
                        layout.addWidget(child, row, col, row_span, col_span)
                    else:
                        layout.addWidget(child)
            else:
                for child in children:
                    layout.addWidget(child)
    
    def _apply_global_properties(self, widget: QWidget, properties: Dict[str, Any]) -> None:
        """Apply global layout properties."""
        # Apply any global properties that make sense
        logger.debug(f"Applied global properties to layout: {list(properties.keys())}")
    
    def _from_dict(self, data: Dict[str, Any]) -> SerializedLayout:
        """Convert dictionary to SerializedLayout."""
        # Convert datetime strings back to datetime objects
        def parse_datetime(date_str: str) -> datetime:
            try:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except Exception:
                return datetime.now(timezone.utc)
        
        # Parse metadata
        metadata_dict = data["metadata"]
        metadata = LayoutMetadata(
            name=metadata_dict["name"],
            version=metadata_dict.get("version", "1.0.0"),
            created=parse_datetime(metadata_dict.get("created", "")),
            modified=parse_datetime(metadata_dict.get("modified", "")),
            author=metadata_dict.get("author", ""),
            description=metadata_dict.get("description", ""),
            tags=metadata_dict.get("tags", [])
        )
        
        # Parse displays
        displays = [
            DisplayGeometry(**display_dict)
            for display_dict in data.get("displays", [])
        ]
        
        # Parse layout tree
        layout = self._parse_layout_node(data["layout"])
        
        return SerializedLayout(
            metadata=metadata,
            displays=displays,
            layout=layout,
            global_properties=data.get("global_properties", {})
        )
    
    def _parse_layout_node(self, node_dict: Dict[str, Any]) -> LayoutNode:
        """Parse layout node from dictionary."""
        # Parse component state
        state_dict = node_dict.get("state", {})
        state = ComponentState(
            visible=state_dict.get("visible", True),
            enabled=state_dict.get("enabled", True),
            geometry=state_dict.get("geometry"),
            size_policy=state_dict.get("size_policy"),
            properties=state_dict.get("properties", {})
        )
        
        # Parse children recursively
        children = [
            self._parse_layout_node(child_dict)
            for child_dict in node_dict.get("children", [])
        ]
        
        return LayoutNode(
            type=LayoutType(node_dict["type"]),
            component_id=node_dict["component_id"],
            state=state,
            children=children,
            properties=node_dict.get("properties", {})
        )