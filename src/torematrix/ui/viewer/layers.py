"""
Layer Management System for Document Viewer Overlay.
This module provides layer management with z-order control, visibility management,
and efficient layer rendering for the overlay system.
"""
from __future__ import annotations

import weakref
from typing import Any, Dict, List, Optional, Protocol, Set
from dataclasses import dataclass, field
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal

from .coordinates import Rectangle, Point


class LayerType(Enum):
    """Types of overlay layers."""
    SELECTION = "selection"
    HIGHLIGHT = "highlight"
    ANNOTATION = "annotation"
    DECORATION = "decoration"
    INTERACTION = "interaction"
    CUSTOM = "custom"


@dataclass
class LayerStyle:
    """Style configuration for a layer."""
    opacity: float = 1.0
    blend_mode: str = "normal"
    visible: bool = True
    z_index: int = 0
    clip_to_bounds: bool = True
    enable_hit_testing: bool = True


class LayerElement(Protocol):
    """Protocol for elements that can be added to layers."""
    
    def get_bounds(self) -> Rectangle:
        """Get the bounding rectangle of the element."""
        ...
    
    def get_style(self) -> Dict[str, Any]:
        """Get the style properties of the element."""
        ...
    
    def is_visible(self) -> bool:
        """Check if the element is visible."""
        ...
    
    def get_z_index(self) -> int:
        """Get the z-index for element layering within the layer."""
        ...
    
    def render(self, renderer, context) -> None:
        """Render the element using the given renderer."""
        ...


class LayerSignals(QObject):
    """Signals for layer events."""
    visibility_changed = pyqtSignal(bool)
    z_index_changed = pyqtSignal(int)
    element_added = pyqtSignal(object)
    element_removed = pyqtSignal(object)
    layer_cleared = pyqtSignal()
    style_changed = pyqtSignal(object)  # LayerStyle


class OverlayLayer:
    """
    Individual overlay layer that can contain multiple elements.
    
    Layers provide organization and z-order control for overlay elements.
    Each layer can have its own style, visibility, and rendering properties.
    """
    
    def __init__(self, name: str, layer_type: LayerType = LayerType.CUSTOM, z_index: int = 0):
        self.name = name
        self.layer_type = layer_type
        self.style = LayerStyle(z_index=z_index)
        self.signals = LayerSignals()
        
        # Element storage
        self.elements: List[LayerElement] = []
        self.element_index: Dict[int, LayerElement] = {}  # For fast lookup
        
        # Spatial optimization
        self.bounds_cache: Optional[Rectangle] = None
        self.bounds_dirty = True
        
        # Metadata
        self.metadata: Dict[str, Any] = {}
        self.creation_time = 0
        self.last_modified = 0
    
    def add_element(self, element: LayerElement) -> None:
        """Add an element to the layer."""
        if element not in self.elements:
            self.elements.append(element)
            self.element_index[id(element)] = element
            self._mark_bounds_dirty()
            self.signals.element_added.emit(element)
    
    def remove_element(self, element: LayerElement) -> bool:
        """Remove an element from the layer."""
        if element in self.elements:
            self.elements.remove(element)
            del self.element_index[id(element)]
            self._mark_bounds_dirty()
            self.signals.element_removed.emit(element)
            return True
        return False
    
    def clear(self) -> None:
        """Clear all elements from the layer."""
        self.elements.clear()
        self.element_index.clear()
        self._mark_bounds_dirty()
        self.signals.layer_cleared.emit()
    
    def get_elements(self) -> List[LayerElement]:
        """Get all elements in the layer."""
        return self.elements.copy()
    
    def get_element_count(self) -> int:
        """Get the number of elements in the layer."""
        return len(self.elements)
    
    def get_visible_elements(self) -> List[LayerElement]:
        """Get all visible elements in the layer."""
        return [element for element in self.elements if element.is_visible()]
    
    def get_elements_in_bounds(self, bounds: Rectangle) -> List[LayerElement]:
        """Get elements that intersect with the given bounds."""
        intersecting_elements = []
        
        for element in self.elements:
            if element.is_visible():
                element_bounds = element.get_bounds()
                if bounds.intersects(element_bounds):
                    intersecting_elements.append(element)
        
        return intersecting_elements
    
    def get_elements_at_point(self, point: Point) -> List[LayerElement]:
        """Get elements that contain the given point."""
        hit_elements = []
        
        for element in self.elements:
            if element.is_visible():
                element_bounds = element.get_bounds()
                if element_bounds.contains(point):
                    hit_elements.append(element)
        
        return hit_elements
    
    def set_visible(self, visible: bool) -> None:
        """Set layer visibility."""
        if self.style.visible != visible:
            self.style.visible = visible
            self.signals.visibility_changed.emit(visible)
    
    def is_visible(self) -> bool:
        """Check if layer is visible."""
        return self.style.visible
    
    def set_z_index(self, z_index: int) -> None:
        """Set layer z-index."""
        if self.style.z_index != z_index:
            self.style.z_index = z_index
            self.signals.z_index_changed.emit(z_index)
    
    def get_z_index(self) -> int:
        """Get layer z-index."""
        return self.style.z_index
    
    def set_opacity(self, opacity: float) -> None:
        """Set layer opacity."""
        self.style.opacity = max(0.0, min(1.0, opacity))
        self.signals.style_changed.emit(self.style)
    
    def get_opacity(self) -> float:
        """Get layer opacity."""
        return self.style.opacity
    
    def set_blend_mode(self, blend_mode: str) -> None:
        """Set layer blend mode."""
        self.style.blend_mode = blend_mode
        self.signals.style_changed.emit(self.style)
    
    def get_blend_mode(self) -> str:
        """Get layer blend mode."""
        return self.style.blend_mode
    
    def get_style(self) -> LayerStyle:
        """Get layer style."""
        return self.style
    
    def set_style(self, style: LayerStyle) -> None:
        """Set layer style."""
        self.style = style
        self.signals.style_changed.emit(self.style)
    
    def get_bounds(self) -> Rectangle:
        """Get the bounding rectangle of all elements in the layer."""
        if self.bounds_dirty or self.bounds_cache is None:
            self._update_bounds_cache()
        return self.bounds_cache
    
    def _update_bounds_cache(self) -> None:
        """Update the cached bounds of the layer."""
        if not self.elements:
            self.bounds_cache = Rectangle(0, 0, 0, 0)
            return
        
        # Calculate union of all element bounds
        first_element = self.elements[0]
        bounds = first_element.get_bounds()
        
        for element in self.elements[1:]:
            element_bounds = element.get_bounds()
            bounds = bounds.union(element_bounds)
        
        self.bounds_cache = bounds
        self.bounds_dirty = False
    
    def _mark_bounds_dirty(self) -> None:
        """Mark bounds cache as dirty."""
        self.bounds_dirty = True
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self.metadata.get(key, default)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata value."""
        self.metadata[key] = value
    
    def render(self, renderer, context) -> None:
        """Render the layer using the given renderer."""
        if not self.is_visible():
            return
        
        # Sort elements by z-index
        sorted_elements = sorted(self.elements, key=lambda e: e.get_z_index())
        
        # Render each element
        for element in sorted_elements:
            if element.is_visible():
                element.render(renderer, context)


class LayerManager:
    """
    Manager for overlay layers with z-order control and efficient rendering.
    
    The LayerManager handles multiple layers, maintains z-order,
    and provides efficient access to layers and their elements.
    """
    
    def __init__(self):
        self.layers: Dict[str, OverlayLayer] = {}
        self.layer_order: List[str] = []
        self.layer_types: Dict[LayerType, List[str]] = {
            layer_type: [] for layer_type in LayerType
        }
        
        # Performance optimization
        self.visible_layers_cache: Optional[List[OverlayLayer]] = None
        self.cache_dirty = True
    
    def create_layer(self, name: str, layer_type: LayerType = LayerType.CUSTOM, z_index: int = 0) -> OverlayLayer:
        """Create a new overlay layer."""
        if name in self.layers:
            raise ValueError(f"Layer '{name}' already exists")
        
        layer = OverlayLayer(name, layer_type, z_index)
        self.layers[name] = layer
        self.layer_types[layer_type].append(name)
        
        # Insert in correct z-order position
        self._insert_layer_in_order(name, z_index)
        
        # Connect to layer signals
        layer.signals.visibility_changed.connect(self._on_layer_visibility_changed)
        layer.signals.z_index_changed.connect(lambda z: self._on_layer_z_index_changed(name, z))
        
        self._mark_cache_dirty()
        return layer
    
    def remove_layer(self, name: str) -> bool:
        """Remove a layer."""
        if name not in self.layers:
            return False
        
        layer = self.layers[name]
        
        # Remove from storage
        del self.layers[name]
        self.layer_order.remove(name)
        self.layer_types[layer.layer_type].remove(name)
        
        self._mark_cache_dirty()
        return True
    
    def get_layer(self, name: str) -> Optional[OverlayLayer]:
        """Get a layer by name."""
        return self.layers.get(name)
    
    def get_layers_by_type(self, layer_type: LayerType) -> List[OverlayLayer]:
        """Get all layers of a specific type."""
        layer_names = self.layer_types[layer_type]
        return [self.layers[name] for name in layer_names if name in self.layers]
    
    def get_all_layers(self) -> List[OverlayLayer]:
        """Get all layers."""
        return list(self.layers.values())
    
    def get_visible_layers(self) -> List[OverlayLayer]:
        """Get all visible layers."""
        if self.cache_dirty or self.visible_layers_cache is None:
            self._update_visible_layers_cache()
        return self.visible_layers_cache
    
    def get_layers_by_z_order(self) -> List[OverlayLayer]:
        """Get all layers sorted by z-order."""
        return [self.layers[name] for name in self.layer_order if name in self.layers]
    
    def get_layer_names(self) -> List[str]:
        """Get all layer names."""
        return list(self.layers.keys())
    
    def get_layer_count(self) -> int:
        """Get the number of layers."""
        return len(self.layers)
    
    def set_layer_z_index(self, name: str, z_index: int) -> bool:
        """Set the z-index of a layer."""
        if name not in self.layers:
            return False
        
        layer = self.layers[name]
        old_z_index = layer.get_z_index()
        
        if old_z_index != z_index:
            layer.set_z_index(z_index)
            self._reorder_layer(name, z_index)
            self._mark_cache_dirty()
        
        return True
    
    def move_layer_up(self, name: str) -> bool:
        """Move a layer up in the z-order."""
        if name not in self.layers:
            return False
        
        current_index = self.layer_order.index(name)
        if current_index < len(self.layer_order) - 1:
            # Swap with next layer
            self.layer_order[current_index], self.layer_order[current_index + 1] = \
                self.layer_order[current_index + 1], self.layer_order[current_index]
            
            # Update z-indices
            self._update_z_indices_from_order()
            self._mark_cache_dirty()
            return True
        
        return False
    
    def move_layer_down(self, name: str) -> bool:
        """Move a layer down in the z-order."""
        if name not in self.layers:
            return False
        
        current_index = self.layer_order.index(name)
        if current_index > 0:
            # Swap with previous layer
            self.layer_order[current_index], self.layer_order[current_index - 1] = \
                self.layer_order[current_index - 1], self.layer_order[current_index]
            
            # Update z-indices
            self._update_z_indices_from_order()
            self._mark_cache_dirty()
            return True
        
        return False
    
    def move_layer_to_top(self, name: str) -> bool:
        """Move a layer to the top of the z-order."""
        if name not in self.layers:
            return False
        
        self.layer_order.remove(name)
        self.layer_order.append(name)
        
        # Update z-indices
        self._update_z_indices_from_order()
        self._mark_cache_dirty()
        return True
    
    def move_layer_to_bottom(self, name: str) -> bool:
        """Move a layer to the bottom of the z-order."""
        if name not in self.layers:
            return False
        
        self.layer_order.remove(name)
        self.layer_order.insert(0, name)
        
        # Update z-indices
        self._update_z_indices_from_order()
        self._mark_cache_dirty()
        return True
    
    def get_elements_at_point(self, point: Point) -> List[LayerElement]:
        """Get all elements at a given point from all layers."""
        hit_elements = []
        
        # Check layers in reverse z-order (top to bottom)
        for layer in reversed(self.get_visible_layers()):
            layer_elements = layer.get_elements_at_point(point)
            hit_elements.extend(layer_elements)
        
        return hit_elements
    
    def get_elements_in_bounds(self, bounds: Rectangle) -> List[LayerElement]:
        """Get all elements that intersect with the given bounds."""
        intersecting_elements = []
        
        for layer in self.get_visible_layers():
            layer_elements = layer.get_elements_in_bounds(bounds)
            intersecting_elements.extend(layer_elements)
        
        return intersecting_elements
    
    def get_top_element_at_point(self, point: Point) -> Optional[LayerElement]:
        """Get the top-most element at a given point."""
        # Check layers in reverse z-order (top to bottom)
        for layer in reversed(self.get_visible_layers()):
            elements = layer.get_elements_at_point(point)
            if elements:
                # Return the element with highest z-index in this layer
                return max(elements, key=lambda e: e.get_z_index())
        
        return None
    
    def clear_all_layers(self) -> None:
        """Clear all elements from all layers."""
        for layer in self.layers.values():
            layer.clear()
        self._mark_cache_dirty()
    
    def _insert_layer_in_order(self, name: str, z_index: int) -> None:
        """Insert a layer in the correct z-order position."""
        # Find the correct position to insert
        insert_pos = 0
        for i, layer_name in enumerate(self.layer_order):
            if self.layers[layer_name].get_z_index() <= z_index:
                insert_pos = i + 1
            else:
                break
        
        self.layer_order.insert(insert_pos, name)
    
    def _reorder_layer(self, name: str, new_z_index: int) -> None:
        """Reorder a layer based on new z-index."""
        # Remove from current position
        self.layer_order.remove(name)
        
        # Insert in new position
        self._insert_layer_in_order(name, new_z_index)
    
    def _update_z_indices_from_order(self) -> None:
        """Update z-indices based on current layer order."""
        for i, layer_name in enumerate(self.layer_order):
            self.layers[layer_name].set_z_index(i)
    
    def _on_layer_visibility_changed(self, visible: bool) -> None:
        """Handle layer visibility change."""
        self._mark_cache_dirty()
    
    def _on_layer_z_index_changed(self, layer_name: str, z_index: int) -> None:
        """Handle layer z-index change."""
        self._reorder_layer(layer_name, z_index)
        self._mark_cache_dirty()
    
    def _update_visible_layers_cache(self) -> None:
        """Update the visible layers cache."""
        self.visible_layers_cache = [
            layer for layer in self.get_layers_by_z_order() if layer.is_visible()
        ]
        self.cache_dirty = False
    
    def _mark_cache_dirty(self) -> None:
        """Mark caches as dirty."""
        self.cache_dirty = True
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.layers.clear()
        self.layer_order.clear()
        for layer_list in self.layer_types.values():
            layer_list.clear()
        self.visible_layers_cache = None


class LayerFactory:
    """Factory for creating common types of layers."""
    
    @staticmethod
    def create_selection_layer(name: str = "selection") -> OverlayLayer:
        """Create a selection layer."""
        layer = OverlayLayer(name, LayerType.SELECTION, z_index=100)
        layer.set_opacity(0.7)
        layer.set_blend_mode("multiply")
        return layer
    
    @staticmethod
    def create_highlight_layer(name: str = "highlight") -> OverlayLayer:
        """Create a highlight layer."""
        layer = OverlayLayer(name, LayerType.HIGHLIGHT, z_index=50)
        layer.set_opacity(0.5)
        layer.set_blend_mode("overlay")
        return layer
    
    @staticmethod
    def create_annotation_layer(name: str = "annotation") -> OverlayLayer:
        """Create an annotation layer."""
        layer = OverlayLayer(name, LayerType.ANNOTATION, z_index=200)
        layer.set_opacity(1.0)
        layer.set_blend_mode("normal")
        return layer
    
    @staticmethod
    def create_decoration_layer(name: str = "decoration") -> OverlayLayer:
        """Create a decoration layer."""
        layer = OverlayLayer(name, LayerType.DECORATION, z_index=10)
        layer.set_opacity(0.8)
        layer.set_blend_mode("normal")
        return layer