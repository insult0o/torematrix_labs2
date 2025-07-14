"""
Overlay Integration for Agent 2 Selection System.
This module provides seamless integration between the selection system and Agent 1's overlay engine,
handling element discovery, coordinate transformation, and visual feedback.
"""
from __future__ import annotations

import asyncio
import weakref
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QColor

from .coordinates import Rectangle, Point, CoordinateTransform
from .layers import LayerElement, OverlayLayer
from .selection import SelectionManager, SelectionState, SelectionMode, SelectionStrategy
from .multi_select import SelectionAlgorithm, SelectionCriteria
from .integration_api import OverlayIntegrationAPI


class IntegrationMode(Enum):
    """Integration modes for overlay interaction."""
    PASSIVE = "passive"      # Read-only integration
    ACTIVE = "active"        # Full bidirectional integration
    SELECTIVE = "selective"  # Selective element integration
    CACHED = "cached"        # Cached element access


@dataclass
class OverlayElementAdapter:
    """Adapter for overlay elements to work with selection system."""
    element_id: str
    layer_name: str
    element_type: str
    bounds: Rectangle
    properties: Dict[str, Any]
    overlay_element: Any  # Reference to actual overlay element
    last_updated: datetime = field(default_factory=datetime.now)
    
    def get_bounds(self) -> Rectangle:
        """Get element bounds."""
        return self.bounds
    
    def get_style(self) -> Dict[str, Any]:
        """Get element style."""
        return self.properties.get('style', {})
    
    def is_visible(self) -> bool:
        """Check if element is visible."""
        return self.properties.get('visible', True)
    
    def get_z_index(self) -> int:
        """Get element z-index."""
        return self.properties.get('z_index', 0)
    
    def render(self, renderer, context) -> None:
        """Render the element."""
        if self.overlay_element and hasattr(self.overlay_element, 'render'):
            self.overlay_element.render(renderer, context)


@dataclass
class SelectionVisualFeedback:
    """Visual feedback configuration for selections."""
    selection_color: QColor = field(default_factory=lambda: QColor(0, 120, 215, 100))
    hover_color: QColor = field(default_factory=lambda: QColor(0, 120, 215, 50))
    stroke_width: float = 2.0
    stroke_color: QColor = field(default_factory=lambda: QColor(0, 120, 215, 255))
    animation_duration: int = 200  # milliseconds
    show_bounds: bool = True
    show_handles: bool = True
    handle_size: float = 8.0


class OverlayIntegrationSignals(QObject):
    """Signals for overlay integration events."""
    elements_discovered = pyqtSignal(int)  # count
    selection_rendered = pyqtSignal(str)  # selection_id
    coordinate_transform_updated = pyqtSignal(object)  # CoordinateTransform
    layer_sync_completed = pyqtSignal(str)  # layer_name
    integration_error = pyqtSignal(str, str)  # operation, error
    visual_feedback_updated = pyqtSignal(object)  # feedback config


class OverlaySelectionIntegration:
    """
    Integration layer between Agent 2 selection system and Agent 1 overlay engine.
    
    This class provides:
    - Element discovery and caching from overlay layers
    - Coordinate transformation between document and screen space
    - Visual feedback rendering for selections
    - Synchronization between selection and overlay states
    """
    
    def __init__(
        self,
        selection_manager: SelectionManager,
        overlay_api: OverlayIntegrationAPI,
        integration_mode: IntegrationMode = IntegrationMode.ACTIVE
    ):
        self.selection_manager = selection_manager
        self.overlay_api = overlay_api
        self.integration_mode = integration_mode
        self.signals = OverlayIntegrationSignals()
        
        # Element management
        self.element_cache: Dict[str, OverlayElementAdapter] = {}
        self.layer_elements: Dict[str, Set[str]] = {}  # layer_name -> element_ids
        self.element_lookup: Dict[str, str] = {}  # element_id -> layer_name
        
        # Visual feedback
        self.visual_feedback = SelectionVisualFeedback()
        self.selection_layer: Optional[OverlayLayer] = None
        self.feedback_elements: Dict[str, Any] = {}
        
        # Coordinate transformation
        self.coordinate_transform: Optional[CoordinateTransform] = None
        
        # Synchronization
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self._sync_with_overlay)
        self.sync_interval = 100  # milliseconds
        
        # Threading
        self.sync_lock = threading.RLock()
        self.discovery_active = False
        
        # Setup integration
        self._setup_integration()
    
    def _setup_integration(self) -> None:
        """Setup the integration with overlay system."""
        try:
            # Create selection visualization layer
            self.selection_layer = self.overlay_api.create_integration_layer(
                "agent2_selection", 
                z_index=1000  # High z-index for selection feedback
            )
            
            # Setup coordinate transformation
            self.coordinate_transform = self.overlay_api.get_coordinate_transform()
            if self.coordinate_transform:
                self.signals.coordinate_transform_updated.emit(self.coordinate_transform)
            
            # Connect to selection manager events
            self.selection_manager.selection_changed.connect(self._on_selection_changed)
            self.selection_manager.mode_changed.connect(self._on_mode_changed)
            
            # Start synchronization if in active mode
            if self.integration_mode == IntegrationMode.ACTIVE:
                self.sync_timer.start(self.sync_interval)
            
            # Perform initial element discovery
            self._discover_overlay_elements()
            
        except Exception as e:
            self.signals.integration_error.emit("setup", str(e))
    
    def _discover_overlay_elements(self) -> None:
        """Discover all available elements from overlay layers."""
        if self.discovery_active:
            return
        
        self.discovery_active = True
        
        try:
            with self.sync_lock:
                # Get current viewport for element discovery
                viewport = self.overlay_api.get_current_viewport()
                if not viewport:
                    return
                
                # Discover elements in viewport
                elements = self.overlay_api.get_elements_in_viewport(viewport)
                
                # Clear old cache
                self.element_cache.clear()
                self.layer_elements.clear()
                self.element_lookup.clear()
                
                # Process discovered elements
                for element in elements:
                    self._process_discovered_element(element)
                
                self.signals.elements_discovered.emit(len(self.element_cache))
                
        except Exception as e:
            self.signals.integration_error.emit("discover_elements", str(e))
        finally:
            self.discovery_active = False
    
    def _process_discovered_element(self, element: Any) -> None:
        """Process a discovered overlay element."""
        try:
            # Extract element information
            element_id = str(id(element))
            layer_name = getattr(element, 'layer_name', 'default')
            element_type = getattr(element, 'element_type', 'unknown')
            bounds = element.get_bounds()
            
            # Create adapter
            adapter = OverlayElementAdapter(
                element_id=element_id,
                layer_name=layer_name,
                element_type=element_type,
                bounds=bounds,
                properties=element.get_style() if hasattr(element, 'get_style') else {},
                overlay_element=element
            )
            
            # Store in cache
            self.element_cache[element_id] = adapter
            
            # Update layer tracking
            if layer_name not in self.layer_elements:
                self.layer_elements[layer_name] = set()
            self.layer_elements[layer_name].add(element_id)
            
            # Update lookup
            self.element_lookup[element_id] = layer_name
            
        except Exception as e:
            self.signals.integration_error.emit("process_element", str(e))
    
    def _sync_with_overlay(self) -> None:
        """Synchronize with overlay system."""
        try:
            # Update coordinate transformation
            current_transform = self.overlay_api.get_coordinate_transform()
            if current_transform != self.coordinate_transform:
                self.coordinate_transform = current_transform
                self.signals.coordinate_transform_updated.emit(current_transform)
            
            # Update element cache if needed
            if self.integration_mode == IntegrationMode.ACTIVE:
                self._update_element_cache()
            
            # Update visual feedback
            self._update_selection_visualization()
            
        except Exception as e:
            self.signals.integration_error.emit("sync", str(e))
    
    def _update_element_cache(self) -> None:
        """Update element cache with current overlay state."""
        try:
            # Get current viewport
            viewport = self.overlay_api.get_current_viewport()
            if not viewport:
                return
            
            # Get current elements in viewport
            current_elements = self.overlay_api.get_elements_in_viewport(viewport)
            current_ids = {str(id(elem)) for elem in current_elements}
            
            # Remove stale elements
            stale_ids = set(self.element_cache.keys()) - current_ids
            for stale_id in stale_ids:
                self._remove_cached_element(stale_id)
            
            # Add new elements
            for element in current_elements:
                element_id = str(id(element))
                if element_id not in self.element_cache:
                    self._process_discovered_element(element)
                else:
                    # Update existing element
                    self._update_cached_element(element_id, element)
                    
        except Exception as e:
            self.signals.integration_error.emit("update_cache", str(e))
    
    def _remove_cached_element(self, element_id: str) -> None:
        """Remove an element from cache."""
        if element_id in self.element_cache:
            adapter = self.element_cache[element_id]
            layer_name = adapter.layer_name
            
            # Remove from cache
            del self.element_cache[element_id]
            
            # Update layer tracking
            if layer_name in self.layer_elements:
                self.layer_elements[layer_name].discard(element_id)
                if not self.layer_elements[layer_name]:
                    del self.layer_elements[layer_name]
            
            # Update lookup
            self.element_lookup.pop(element_id, None)
    
    def _update_cached_element(self, element_id: str, element: Any) -> None:
        """Update a cached element with new data."""
        if element_id in self.element_cache:
            adapter = self.element_cache[element_id]
            adapter.bounds = element.get_bounds()
            adapter.properties = element.get_style() if hasattr(element, 'get_style') else {}
            adapter.overlay_element = element
            adapter.last_updated = datetime.now()
    
    def _on_selection_changed(self, selection_state: SelectionState) -> None:
        """Handle selection changes."""
        try:
            # Update visual feedback
            self._update_selection_visualization()
            
            # Notify overlay system of selection change
            if self.integration_mode == IntegrationMode.ACTIVE:
                self._notify_overlay_selection_change(selection_state)
                
        except Exception as e:
            self.signals.integration_error.emit("selection_changed", str(e))
    
    def _on_mode_changed(self, mode: SelectionMode) -> None:
        """Handle selection mode changes."""
        try:
            # Update visual feedback style based on mode
            self._update_feedback_for_mode(mode)
            
        except Exception as e:
            self.signals.integration_error.emit("mode_changed", str(e))
    
    def _update_selection_visualization(self) -> None:
        """Update visual feedback for current selection."""
        try:
            if not self.selection_layer:
                return
            
            # Clear existing feedback
            self.selection_layer.clear()
            self.feedback_elements.clear()
            
            # Get current selection
            current_state = self.selection_manager.get_current_state()
            if not current_state.selected_elements:
                return
            
            # Create visual feedback for each selected element
            for element in current_state.selected_elements:
                self._create_selection_feedback(element)
            
            # Invalidate layer for re-rendering
            self.overlay_api.invalidate_agent_layer("agent2_selection")
            
            # Emit signal
            selection_id = getattr(current_state, 'selection_id', 'current')
            self.signals.selection_rendered.emit(selection_id)
            
        except Exception as e:
            self.signals.integration_error.emit("update_visualization", str(e))
    
    def _create_selection_feedback(self, element: Any) -> None:
        """Create visual feedback for a selected element."""
        try:
            # Get element bounds
            bounds = element.get_bounds()
            
            # Transform to screen coordinates if needed
            if self.coordinate_transform:
                screen_bounds = self.coordinate_transform.transform_bounds(bounds)
            else:
                screen_bounds = bounds
            
            # Create selection rectangle
            selection_rect = self._create_selection_rectangle(screen_bounds)
            
            # Add to selection layer
            self.selection_layer.add_element(selection_rect)
            
            # Store reference
            element_id = str(id(element))
            self.feedback_elements[element_id] = selection_rect
            
            # Add selection handles if enabled
            if self.visual_feedback.show_handles:
                handles = self._create_selection_handles(screen_bounds)
                for handle in handles:
                    self.selection_layer.add_element(handle)
                    
        except Exception as e:
            self.signals.integration_error.emit("create_feedback", str(e))
    
    def _create_selection_rectangle(self, bounds: Rectangle) -> Any:
        """Create a selection rectangle element."""
        # This would create an actual overlay element
        # For now, return a placeholder
        return SelectionRectangleElement(bounds, self.visual_feedback)
    
    def _create_selection_handles(self, bounds: Rectangle) -> List[Any]:
        """Create selection handles for a rectangle."""
        handles = []
        handle_size = self.visual_feedback.handle_size
        
        # Corner handles
        positions = [
            Point(bounds.x, bounds.y),  # Top-left
            Point(bounds.x + bounds.width, bounds.y),  # Top-right
            Point(bounds.x + bounds.width, bounds.y + bounds.height),  # Bottom-right
            Point(bounds.x, bounds.y + bounds.height),  # Bottom-left
        ]
        
        # Edge handles
        edge_positions = [
            Point(bounds.x + bounds.width/2, bounds.y),  # Top
            Point(bounds.x + bounds.width, bounds.y + bounds.height/2),  # Right
            Point(bounds.x + bounds.width/2, bounds.y + bounds.height),  # Bottom
            Point(bounds.x, bounds.y + bounds.height/2),  # Left
        ]
        
        all_positions = positions + edge_positions
        
        for pos in all_positions:
            handle = SelectionHandleElement(
                Rectangle(
                    pos.x - handle_size/2,
                    pos.y - handle_size/2,
                    handle_size,
                    handle_size
                ),
                self.visual_feedback
            )
            handles.append(handle)
        
        return handles
    
    def _update_feedback_for_mode(self, mode: SelectionMode) -> None:
        """Update visual feedback based on selection mode."""
        try:
            # Adjust feedback style based on mode
            if mode == SelectionMode.SINGLE:
                self.visual_feedback.selection_color = QColor(0, 120, 215, 100)
                self.visual_feedback.show_handles = True
            elif mode == SelectionMode.MULTI:
                self.visual_feedback.selection_color = QColor(0, 150, 100, 80)
                self.visual_feedback.show_handles = False
            elif mode == SelectionMode.RECTANGULAR:
                self.visual_feedback.selection_color = QColor(200, 100, 0, 60)
                self.visual_feedback.show_handles = True
            elif mode == SelectionMode.POLYGON:
                self.visual_feedback.selection_color = QColor(150, 0, 150, 60)
                self.visual_feedback.show_handles = False
            elif mode == SelectionMode.LASSO:
                self.visual_feedback.selection_color = QColor(0, 200, 200, 60)
                self.visual_feedback.show_handles = False
            
            # Update existing feedback
            self._update_selection_visualization()
            
            # Emit signal
            self.signals.visual_feedback_updated.emit(self.visual_feedback)
            
        except Exception as e:
            self.signals.integration_error.emit("update_feedback_mode", str(e))
    
    def _notify_overlay_selection_change(self, selection_state: SelectionState) -> None:
        """Notify overlay system of selection changes."""
        try:
            # Convert selection to overlay format
            selected_elements = list(selection_state.selected_elements)
            
            # Use overlay API to notify of selection
            if hasattr(self.overlay_api, 'notify_selection_change'):
                self.overlay_api.notify_selection_change(selected_elements)
                
        except Exception as e:
            self.signals.integration_error.emit("notify_overlay", str(e))
    
    # Public API methods
    
    def get_selectable_elements(self, region: Rectangle) -> List[OverlayElementAdapter]:
        """Get selectable elements in a region."""
        with self.sync_lock:
            selectable = []
            
            # Transform region to document coordinates if needed
            if self.coordinate_transform:
                doc_region = self.coordinate_transform.screen_to_document_bounds(region)
            else:
                doc_region = region
            
            # Find intersecting elements
            for adapter in self.element_cache.values():
                if adapter.bounds.intersects(doc_region):
                    selectable.append(adapter)
            
            return selectable
    
    def get_element_by_id(self, element_id: str) -> Optional[OverlayElementAdapter]:
        """Get element by ID."""
        with self.sync_lock:
            return self.element_cache.get(element_id)
    
    def get_elements_by_layer(self, layer_name: str) -> List[OverlayElementAdapter]:
        """Get all elements in a layer."""
        with self.sync_lock:
            if layer_name not in self.layer_elements:
                return []
            
            return [
                self.element_cache[element_id]
                for element_id in self.layer_elements[layer_name]
                if element_id in self.element_cache
            ]
    
    def get_elements_by_type(self, element_type: str) -> List[OverlayElementAdapter]:
        """Get all elements of a specific type."""
        with self.sync_lock:
            return [
                adapter for adapter in self.element_cache.values()
                if adapter.element_type == element_type
            ]
    
    def refresh_element_cache(self) -> None:
        """Manually refresh element cache."""
        self._discover_overlay_elements()
    
    def set_visual_feedback(self, feedback: SelectionVisualFeedback) -> None:
        """Set visual feedback configuration."""
        self.visual_feedback = feedback
        self._update_selection_visualization()
        self.signals.visual_feedback_updated.emit(feedback)
    
    def get_visual_feedback(self) -> SelectionVisualFeedback:
        """Get current visual feedback configuration."""
        return self.visual_feedback
    
    def set_integration_mode(self, mode: IntegrationMode) -> None:
        """Set integration mode."""
        self.integration_mode = mode
        
        if mode == IntegrationMode.ACTIVE:
            if not self.sync_timer.isActive():
                self.sync_timer.start(self.sync_interval)
        else:
            if self.sync_timer.isActive():
                self.sync_timer.stop()
    
    def get_integration_mode(self) -> IntegrationMode:
        """Get current integration mode."""
        return self.integration_mode
    
    def get_coordinate_transform(self) -> Optional[CoordinateTransform]:
        """Get current coordinate transformation."""
        return self.coordinate_transform
    
    def transform_point_to_document(self, screen_point: Point) -> Point:
        """Transform screen point to document coordinates."""
        if self.coordinate_transform:
            return self.coordinate_transform.screen_to_document(screen_point)
        return screen_point
    
    def transform_point_to_screen(self, doc_point: Point) -> Point:
        """Transform document point to screen coordinates."""
        if self.coordinate_transform:
            return self.coordinate_transform.document_to_screen(doc_point)
        return doc_point
    
    def get_integration_statistics(self) -> Dict[str, Any]:
        """Get integration statistics."""
        with self.sync_lock:
            return {
                'integration_mode': self.integration_mode.value,
                'cached_elements': len(self.element_cache),
                'layers_tracked': len(self.layer_elements),
                'sync_active': self.sync_timer.isActive(),
                'sync_interval': self.sync_interval,
                'discovery_active': self.discovery_active,
                'selection_layer_active': self.selection_layer is not None,
                'feedback_elements': len(self.feedback_elements)
            }
    
    def cleanup(self) -> None:
        """Clean up integration resources."""
        # Stop synchronization
        if self.sync_timer.isActive():
            self.sync_timer.stop()
        
        # Clear selection layer
        if self.selection_layer:
            self.selection_layer.clear()
            self.overlay_api.cleanup_agent_resources("agent2_selection")
        
        # Clear caches
        with self.sync_lock:
            self.element_cache.clear()
            self.layer_elements.clear()
            self.element_lookup.clear()
            self.feedback_elements.clear()
        
        # Reset state
        self.coordinate_transform = None
        self.selection_layer = None
        self.discovery_active = False


# Helper classes for visual feedback elements

class SelectionRectangleElement:
    """Selection rectangle visual element."""
    
    def __init__(self, bounds: Rectangle, feedback: SelectionVisualFeedback):
        self.bounds = bounds
        self.feedback = feedback
    
    def get_bounds(self) -> Rectangle:
        return self.bounds
    
    def get_style(self) -> Dict[str, Any]:
        return {
            'fill_color': self.feedback.selection_color,
            'stroke_color': self.feedback.stroke_color,
            'stroke_width': self.feedback.stroke_width,
            'opacity': self.feedback.selection_color.alpha() / 255.0
        }
    
    def is_visible(self) -> bool:
        return True
    
    def get_z_index(self) -> int:
        return 1000
    
    def render(self, renderer, context) -> None:
        if renderer and hasattr(renderer, 'render_rectangle'):
            from .renderer import RenderStyle
            style = RenderStyle(
                fill_color=self.feedback.selection_color,
                stroke_color=self.feedback.stroke_color,
                stroke_width=self.feedback.stroke_width
            )
            renderer.render_rectangle(self.bounds, style)


class SelectionHandleElement:
    """Selection handle visual element."""
    
    def __init__(self, bounds: Rectangle, feedback: SelectionVisualFeedback):
        self.bounds = bounds
        self.feedback = feedback
    
    def get_bounds(self) -> Rectangle:
        return self.bounds
    
    def get_style(self) -> Dict[str, Any]:
        return {
            'fill_color': self.feedback.stroke_color,
            'stroke_color': self.feedback.stroke_color,
            'stroke_width': 1.0
        }
    
    def is_visible(self) -> bool:
        return True
    
    def get_z_index(self) -> int:
        return 1001
    
    def render(self, renderer, context) -> None:
        if renderer and hasattr(renderer, 'render_rectangle'):
            from .renderer import RenderStyle
            style = RenderStyle(
                fill_color=self.feedback.stroke_color,
                stroke_color=self.feedback.stroke_color,
                stroke_width=1.0
            )
            renderer.render_rectangle(self.bounds, style)