"""
Integration API for Agent 1 Overlay System.
This module provides the integration interface for other agents to interact with the overlay system.
"""
from typing import Any, Dict, List, Optional, Tuple, Union, Protocol
from dataclasses import dataclass
from enum import Enum
import time

from .overlay import OverlayEngine, OverlayManager, RenderBackend
from .coordinates import Rectangle, Point, CoordinateTransform
from .layers import OverlayLayer, LayerElement
from .renderer import RendererBackend, RenderStyle
from .pipeline import RenderPipeline, RenderPriority, RenderOperation


class OverlayIntegrationAPI:
    """
    High-level integration API for other agents to interact with the overlay system.
    
    This API provides a simplified interface for:
    - Agent 2: Element selection and state management
    - Agent 3: Spatial indexing and performance optimization
    - Agent 4: Interactive features and touch support
    """
    
    def __init__(self, engine: OverlayEngine):
        self.engine = engine
        self.callbacks = {}
        self.agent_contexts = {}
    
    # === Agent 2 Integration: Element Selection & State Management ===
    
    def register_selection_callback(self, callback: callable) -> None:
        """Register callback for element selection events."""
        self.callbacks['selection'] = callback
    
    def get_selectable_elements(self, region: Rectangle) -> List[LayerElement]:
        """Get all selectable elements in a region."""
        elements = []
        for layer in self.engine.layer_manager.get_all_layers():
            if layer.is_visible():
                for element in layer.get_elements():
                    if element.is_visible() and element.get_bounds().intersects(region):
                        elements.append(element)
        return elements
    
    def multi_select_elements(self, regions: List[Rectangle]) -> List[LayerElement]:
        """Select multiple elements across multiple regions."""
        selected_elements = []
        for region in regions:
            selected_elements.extend(self.get_selectable_elements(region))
        return list(set(selected_elements))  # Remove duplicates
    
    def save_selection_state(self, selection_id: str, elements: List[LayerElement]) -> None:
        """Save selection state for persistence."""
        if 'selection_states' not in self.agent_contexts:
            self.agent_contexts['selection_states'] = {}
        
        self.agent_contexts['selection_states'][selection_id] = {
            'elements': elements,
            'timestamp': time.time(),
            'bounds': [element.get_bounds() for element in elements]
        }
    
    def restore_selection_state(self, selection_id: str) -> Optional[List[LayerElement]]:
        """Restore selection state."""
        if 'selection_states' not in self.agent_contexts:
            return None
        
        state = self.agent_contexts['selection_states'].get(selection_id)
        return state['elements'] if state else None
    
    # === Agent 3 Integration: Spatial Indexing & Performance ===
    
    def register_spatial_index(self, index_callback: callable) -> None:
        """Register spatial indexing callback for performance optimization."""
        self.callbacks['spatial_index'] = index_callback
    
    def get_elements_in_viewport(self, viewport: Rectangle) -> List[LayerElement]:
        """Get all elements visible in the current viewport."""
        return self.engine.get_visible_elements()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        return self.engine.get_render_statistics()
    
    def enable_performance_optimization(self, enable: bool = True) -> None:
        """Enable performance optimization through pipeline."""
        self.engine.enable_pipeline(enable)
    
    def schedule_optimized_render(self, priority: RenderPriority = RenderPriority.NORMAL) -> None:
        """Schedule an optimized render operation."""
        if self.engine.use_pipeline:
            self.engine.schedule_pipeline_render(priority=priority)
        else:
            self.engine.schedule_render()
    
    def add_performance_monitor(self, monitor_name: str, callback: callable) -> None:
        """Add a performance monitoring callback."""
        self.engine.add_performance_hook(monitor_name, callback)
    
    # === Agent 4 Integration: Interactive Features & Touch Support ===
    
    def register_interaction_handler(self, interaction_type: str, handler: callable) -> None:
        """Register interaction handler for touch/mouse events."""
        if 'interaction_handlers' not in self.callbacks:
            self.callbacks['interaction_handlers'] = {}
        self.callbacks['interaction_handlers'][interaction_type] = handler
    
    def handle_touch_event(self, touch_point: Point, touch_type: str) -> List[LayerElement]:
        """Handle touch events and return affected elements."""
        hit_elements = self.engine.hit_test(touch_point)
        
        # Notify interaction handlers
        if 'interaction_handlers' in self.callbacks:
            handler = self.callbacks['interaction_handlers'].get(touch_type)
            if handler:
                handler(touch_point, hit_elements)
        
        return hit_elements
    
    def enable_accessibility_mode(self, enable: bool = True) -> None:
        """Enable accessibility features."""
        if 'accessibility_mode' not in self.agent_contexts:
            self.agent_contexts['accessibility_mode'] = {}
        
        self.agent_contexts['accessibility_mode']['enabled'] = enable
        
        # Adjust rendering for accessibility
        if enable:
            # Increase contrast, larger hit areas, etc.
            self.engine.performance_metrics['accessibility_mode'] = True
    
    def get_element_accessibility_info(self, element: LayerElement) -> Dict[str, Any]:
        """Get accessibility information for an element."""
        return {
            'bounds': element.get_bounds(),
            'type': getattr(element, 'element_type', 'unknown'),
            'description': getattr(element, 'description', ''),
            'interactive': getattr(element, 'interactive', False),
            'screen_reader_text': getattr(element, 'screen_reader_text', '')
        }
    
    # === Common Integration Methods ===
    
    def create_integration_layer(self, agent_id: str, z_index: int = 0) -> OverlayLayer:
        """Create a layer for agent-specific elements."""
        layer_name = f"agent_{agent_id}_layer"
        return self.engine.create_layer(layer_name, z_index)
    
    def add_element_to_agent_layer(self, agent_id: str, element: LayerElement) -> bool:
        """Add an element to an agent's layer."""
        layer_name = f"agent_{agent_id}_layer"
        return self.engine.add_element(layer_name, element)
    
    def invalidate_agent_layer(self, agent_id: str) -> None:
        """Invalidate an agent's layer for re-rendering."""
        layer_name = f"agent_{agent_id}_layer"
        self.engine.invalidate_layer(layer_name)
    
    def get_coordinate_transform(self) -> Optional[CoordinateTransform]:
        """Get the current coordinate transformation."""
        return self.engine.coordinate_transform
    
    def document_to_screen(self, point: Point) -> Point:
        """Transform document coordinates to screen coordinates."""
        return self.engine.document_to_screen(point)
    
    def screen_to_document(self, point: Point) -> Point:
        """Transform screen coordinates to document coordinates."""
        return self.engine.screen_to_document(point)
    
    def get_current_viewport(self) -> Optional[Rectangle]:
        """Get the current viewport bounds."""
        if self.engine.viewport_info:
            return self.engine.viewport_info.bounds
        return None
    
    def cleanup_agent_resources(self, agent_id: str) -> None:
        """Clean up resources for a specific agent."""
        layer_name = f"agent_{agent_id}_layer"
        self.engine.remove_layer(layer_name)
        
        # Remove agent-specific callbacks
        agent_callbacks = [key for key in self.callbacks.keys() if agent_id in key]
        for callback_key in agent_callbacks:
            self.callbacks.pop(callback_key, None)
        
        # Remove agent context
        self.agent_contexts.pop(agent_id, None)


class IntegrationAPIFactory:
    """Factory for creating integration APIs."""
    
    @staticmethod
    def create_api(overlay_engine: OverlayEngine) -> OverlayIntegrationAPI:
        """Create an integration API for the given overlay engine."""
        return OverlayIntegrationAPI(overlay_engine)
    
    @staticmethod
    def create_api_for_manager(overlay_manager: OverlayManager) -> Optional[OverlayIntegrationAPI]:
        """Create an integration API for the active engine in the manager."""
        active_engine = overlay_manager.get_active_engine()
        if active_engine:
            return OverlayIntegrationAPI(active_engine)
        return None


# Export key integration classes for other agents
__all__ = [
    'OverlayIntegrationAPI',
    'IntegrationAPIFactory',
    'OverlayEngine',
    'OverlayManager',
    'RenderBackend',
    'Rectangle',
    'Point',
    'CoordinateTransform',
    'RenderPriority',
    'RenderOperation'
]