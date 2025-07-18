"""
Core Overlay Rendering Engine for Document Viewer.
This module provides the main overlay system that handles transparent overlay rendering
with support for multiple backends (SVG/Canvas) and coordinate transformations.
"""
from __future__ import annotations

import time
import weakref
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple, Union
from dataclasses import dataclass, field

import numpy as np
from PyQt6.QtCore import QObject, QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush
from PyQt6.QtWidgets import QWidget

from .coordinates import CoordinateTransform, Rectangle, Point
from .layers import LayerManager, OverlayLayer
from .renderer import RendererBackend, CanvasRenderer, SVGRenderer
from .pipeline import RenderPipeline, RenderOperation, RenderPriority


class RenderBackend(Enum):
    """Supported rendering backends."""
    CANVAS = "canvas"
    SVG = "svg"


class OverlaySignals(QObject):
    """Signals for overlay events."""
    render_started = pyqtSignal()
    render_completed = pyqtSignal(float)  # render_time_ms
    viewport_changed = pyqtSignal(object)  # viewport_bounds
    layer_added = pyqtSignal(str)  # layer_name
    layer_removed = pyqtSignal(str)  # layer_name
    backend_changed = pyqtSignal(str)  # backend_name


@dataclass
class ViewportInfo:
    """Information about the current viewport."""
    bounds: Rectangle
    zoom_level: float
    center: Point
    rotation: float = 0.0
    last_updated: float = field(default_factory=time.time)


@dataclass
class RenderContext:
    """Context information for rendering operations."""
    viewport: ViewportInfo
    coordinate_transform: CoordinateTransform
    dirty_regions: List[Rectangle]
    performance_metrics: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


class OverlayElement(Protocol):
    """Protocol for elements that can be rendered in the overlay."""
    
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
        """Get the z-index for layering."""
        ...


class OverlayEngine:
    """
    Core overlay rendering engine that manages transparent overlays over documents.
    
    This engine provides:
    - Multi-backend rendering (Canvas/SVG)
    - Coordinate transformation between document and screen space
    - Layer management with z-order control
    - Viewport management and efficient updates
    - Performance monitoring and optimization
    """
    
    def __init__(self, parent_widget: QWidget, backend: RenderBackend = RenderBackend.CANVAS):
        self.parent_widget = parent_widget
        self.signals = OverlaySignals()
        
        # Core components
        self.layer_manager = LayerManager()
        self.coordinate_transform: Optional[CoordinateTransform] = None
        self.renderer_backend: Optional[RendererBackend] = None
        
        # Viewport management
        self.viewport_info: Optional[ViewportInfo] = None
        self.dirty_regions: List[Rectangle] = []
        
        # Performance monitoring
        self.performance_metrics = {
            'render_times': [],
            'frame_count': 0,
            'last_fps': 0.0,
            'memory_usage': 0
        }
        
        # Rendering state
        self.is_rendering = False
        self.render_scheduled = False
        self.render_timer = QTimer()
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self._execute_render)
        
        # Pipeline integration
        self.render_pipeline: Optional[RenderPipeline] = None
        self.use_pipeline = False
        
        # Initialize backend
        self.set_backend(backend)
        
        # Setup default viewport
        self._initialize_viewport()
    
    def set_backend(self, backend: RenderBackend) -> None:
        """Set the rendering backend."""
        if backend == RenderBackend.CANVAS:
            self.renderer_backend = CanvasRenderer(self.parent_widget)
        elif backend == RenderBackend.SVG:
            self.renderer_backend = SVGRenderer(self.parent_widget)
        else:
            raise ValueError(f"Unsupported backend: {backend}")
        
        self.current_backend = backend
        self.signals.backend_changed.emit(backend.value)
    
    def get_backend(self) -> RenderBackend:
        """Get the current rendering backend."""
        return self.current_backend
    
    def set_document_bounds(self, bounds: Rectangle) -> None:
        """Set the document bounds for coordinate transformation."""
        if self.viewport_info:
            self.coordinate_transform = CoordinateTransform(
                document_bounds=bounds,
                viewport_bounds=self.viewport_info.bounds,
                zoom_level=self.viewport_info.zoom_level
            )
            self.schedule_render()
    
    def set_viewport(self, bounds: Rectangle, zoom_level: float = 1.0, center: Optional[Point] = None) -> None:
        """Set the viewport bounds and zoom level."""
        if center is None:
            center = Point(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2)
        
        self.viewport_info = ViewportInfo(
            bounds=bounds,
            zoom_level=zoom_level,
            center=center
        )
        
        # Update coordinate transform if document bounds are available
        if self.coordinate_transform:
            self.coordinate_transform.update_viewport(bounds, zoom_level)
        
        self.signals.viewport_changed.emit(self.viewport_info)
        self.schedule_render()
    
    def get_viewport(self) -> Optional[ViewportInfo]:
        """Get the current viewport information."""
        return self.viewport_info
    
    def create_layer(self, name: str, z_index: int = 0) -> OverlayLayer:
        """Create a new overlay layer."""
        layer = self.layer_manager.create_layer(name, z_index)
        self.signals.layer_added.emit(name)
        return layer
    
    def remove_layer(self, name: str) -> bool:
        """Remove an overlay layer."""
        removed = self.layer_manager.remove_layer(name)
        if removed:
            self.signals.layer_removed.emit(name)
            self.schedule_render()
        return removed
    
    def get_layer(self, name: str) -> Optional[OverlayLayer]:
        """Get an overlay layer by name."""
        return self.layer_manager.get_layer(name)
    
    def get_all_layers(self) -> List[OverlayLayer]:
        """Get all overlay layers."""
        return self.layer_manager.get_all_layers()
    
    def add_element(self, layer_name: str, element: OverlayElement) -> bool:
        """Add an element to a layer."""
        layer = self.layer_manager.get_layer(layer_name)
        if layer:
            layer.add_element(element)
            self._mark_dirty(element.get_bounds())
            return True
        return False
    
    def remove_element(self, layer_name: str, element: OverlayElement) -> bool:
        """Remove an element from a layer."""
        layer = self.layer_manager.get_layer(layer_name)
        if layer:
            removed = layer.remove_element(element)
            if removed:
                self._mark_dirty(element.get_bounds())
            return removed
        return False
    
    def clear_layer(self, layer_name: str) -> bool:
        """Clear all elements from a layer."""
        layer = self.layer_manager.get_layer(layer_name)
        if layer:
            layer.clear()
            self.schedule_render()
            return True
        return False
    
    def schedule_render(self) -> None:
        """Schedule a render operation."""
        if not self.render_scheduled:
            self.render_scheduled = True
            self.render_timer.start(16)  # ~60fps
    
    def render_now(self) -> None:
        """Render immediately without scheduling."""
        if not self.is_rendering:
            self._execute_render()
    
    def _execute_render(self) -> None:
        """Execute the rendering operation."""
        if self.is_rendering:
            return
        
        self.is_rendering = True
        self.render_scheduled = False
        
        start_time = time.time()
        
        try:
            self.signals.render_started.emit()
            
            # Create render context
            context = RenderContext(
                viewport=self.viewport_info,
                coordinate_transform=self.coordinate_transform,
                dirty_regions=self.dirty_regions.copy(),
                performance_metrics=self.performance_metrics
            )
            
            # Render all layers
            if self.renderer_backend and self.viewport_info:
                self.renderer_backend.begin_render(context)
                
                # Render layers in z-order
                for layer in self.layer_manager.get_layers_by_z_order():
                    if layer.is_visible():
                        self._render_layer(layer, context)
                
                self.renderer_backend.end_render()
            
            # Clear dirty regions
            self.dirty_regions.clear()
            
            # Update performance metrics
            render_time = (time.time() - start_time) * 1000  # Convert to ms
            self._update_performance_metrics(render_time)
            
            self.signals.render_completed.emit(render_time)
            
        except Exception as e:
            print(f"Render error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_rendering = False
    
    def _render_layer(self, layer: OverlayLayer, context: RenderContext) -> None:
        """Render a single layer."""
        if not layer.is_visible():
            return
        
        # Get elements in layer
        elements = layer.get_elements()
        
        # Render each element
        for element in elements:
            if element.is_visible():
                self._render_element(element, context)
    
    def _render_element(self, element: OverlayElement, context: RenderContext) -> None:
        """Render a single element."""
        # Transform element bounds to screen coordinates
        if context.coordinate_transform:
            screen_bounds = context.coordinate_transform.transform_bounds(element.get_bounds())
        else:
            screen_bounds = element.get_bounds()
        
        # Check if element is in viewport
        if not self._is_in_viewport(screen_bounds, context.viewport):
            return
        
        # Render element using backend
        style = element.get_style()
        self.renderer_backend.render_element(element, screen_bounds, style, context)
    
    def _is_in_viewport(self, bounds: Rectangle, viewport: ViewportInfo) -> bool:
        """Check if bounds intersect with viewport."""
        if not viewport:
            return True
        
        return (bounds.x < viewport.bounds.x + viewport.bounds.width and
                bounds.x + bounds.width > viewport.bounds.x and
                bounds.y < viewport.bounds.y + viewport.bounds.height and
                bounds.y + bounds.height > viewport.bounds.y)
    
    def _mark_dirty(self, bounds: Rectangle) -> None:
        """Mark a region as dirty for re-rendering."""
        self.dirty_regions.append(bounds)
        self.schedule_render()
    
    def _update_performance_metrics(self, render_time: float) -> None:
        """Update performance metrics."""
        self.performance_metrics['render_times'].append(render_time)
        self.performance_metrics['frame_count'] += 1
        
        # Keep only last 60 frame times for FPS calculation
        if len(self.performance_metrics['render_times']) > 60:
            self.performance_metrics['render_times'].pop(0)
        
        # Calculate FPS
        if len(self.performance_metrics['render_times']) >= 2:
            avg_render_time = sum(self.performance_metrics['render_times']) / len(self.performance_metrics['render_times'])
            self.performance_metrics['last_fps'] = 1000.0 / avg_render_time if avg_render_time > 0 else 0
            
        # Update pipeline performance if enabled
        if self.render_pipeline:
            pipeline_metrics = self.render_pipeline.get_performance_metrics()
            self.performance_metrics['pipeline_fps'] = pipeline_metrics.get('average_fps', 0)
            self.performance_metrics['pipeline_frame_time'] = pipeline_metrics.get('average_frame_time', 0)
            self.performance_metrics['pipeline_queue_size'] = pipeline_metrics.get('render_queue_size', 0)
        
        # Trigger performance hooks
        self._trigger_performance_hooks('render_complete', {
            'render_time': render_time,
            'frame_count': self.performance_metrics['frame_count'],
            'fps': self.performance_metrics['last_fps']
        })
    
    def add_performance_hook(self, hook_name: str, callback: callable) -> None:
        """Add a performance monitoring hook."""
        if 'performance_hooks' not in self.performance_metrics:
            self.performance_metrics['performance_hooks'] = {}
        self.performance_metrics['performance_hooks'][hook_name] = callback
    
    def remove_performance_hook(self, hook_name: str) -> None:
        """Remove a performance monitoring hook."""
        if 'performance_hooks' in self.performance_metrics:
            self.performance_metrics['performance_hooks'].pop(hook_name, None)
    
    def _trigger_performance_hooks(self, event_type: str, data: Dict[str, Any]) -> None:
        """Trigger performance hooks with event data."""
        if 'performance_hooks' in self.performance_metrics:
            for hook_name, callback in self.performance_metrics['performance_hooks'].items():
                try:
                    callback(event_type, data)
                except Exception as e:
                    print(f"Performance hook '{hook_name}' failed: {e}")
    
    def _initialize_viewport(self) -> None:
        """Initialize default viewport."""
        if self.parent_widget:
            widget_rect = self.parent_widget.rect()
            bounds = Rectangle(
                x=widget_rect.x(),
                y=widget_rect.y(),
                width=widget_rect.width(),
                height=widget_rect.height()
            )
            self.set_viewport(bounds, zoom_level=1.0)
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.performance_metrics.copy()
    
    def document_to_screen(self, point: Point) -> Point:
        """Transform document coordinates to screen coordinates."""
        if self.coordinate_transform:
            return self.coordinate_transform.document_to_screen(point)
        return point
    
    def screen_to_document(self, point: Point) -> Point:
        """Transform screen coordinates to document coordinates."""
        if self.coordinate_transform:
            return self.coordinate_transform.screen_to_document(point)
        return point
    
    def get_visible_elements(self) -> List[OverlayElement]:
        """Get all visible elements in the current viewport."""
        visible_elements = []
        
        if not self.viewport_info:
            return visible_elements
        
        for layer in self.layer_manager.get_all_layers():
            if layer.is_visible():
                for element in layer.get_elements():
                    if element.is_visible():
                        element_bounds = element.get_bounds()
                        if self.coordinate_transform:
                            screen_bounds = self.coordinate_transform.transform_bounds(element_bounds)
                        else:
                            screen_bounds = element_bounds
                        
                        if self._is_in_viewport(screen_bounds, self.viewport_info):
                            visible_elements.append(element)
        
        return visible_elements
    
    def hit_test(self, point: Point) -> List[OverlayElement]:
        """Find elements at the given point."""
        hit_elements = []
        
        # Convert screen point to document coordinates
        doc_point = self.screen_to_document(point)
        
        # Check all layers in reverse z-order (top to bottom)
        for layer in reversed(self.layer_manager.get_layers_by_z_order()):
            if layer.is_visible():
                for element in layer.get_elements():
                    if element.is_visible():
                        bounds = element.get_bounds()
                        if (doc_point.x >= bounds.x and doc_point.x <= bounds.x + bounds.width and
                            doc_point.y >= bounds.y and doc_point.y <= bounds.y + bounds.height):
                            hit_elements.append(element)
        
        return hit_elements
    
    def render_layer_to_buffer(self, layer_name: str, buffer_size: Optional[Tuple[int, int]] = None) -> Optional[bytes]:
        """Render a specific layer to a buffer for caching or export."""
        layer = self.layer_manager.get_layer(layer_name)
        if not layer or not layer.is_visible():
            return None
        
        # Create temporary renderer for buffer rendering
        if buffer_size:
            # Create a temporary widget for rendering
            temp_widget = QWidget()
            temp_widget.resize(buffer_size[0], buffer_size[1])
            temp_renderer = CanvasRenderer(temp_widget)
        else:
            temp_renderer = self.renderer_backend
        
        if not temp_renderer:
            return None
        
        # Create context for buffer rendering
        viewport_bounds = Rectangle(0, 0, buffer_size[0] if buffer_size else 800, buffer_size[1] if buffer_size else 600)
        context = RenderContext(
            viewport=ViewportInfo(
                bounds=viewport_bounds,
                zoom_level=1.0,
                center=Point(viewport_bounds.width/2, viewport_bounds.height/2)
            ),
            coordinate_transform=self.coordinate_transform,
            dirty_regions=[],
            performance_metrics={}
        )
        
        try:
            temp_renderer.begin_render(context)
            self._render_layer(layer, context)
            temp_renderer.end_render()
            
            # Extract buffer data (implementation depends on renderer type)
            return None  # Would return actual buffer data
        except Exception as e:
            print(f"Layer buffer rendering error: {e}")
            return None
        finally:
            if buffer_size and temp_renderer != self.renderer_backend:
                temp_renderer.cleanup()
    
    def invalidate_layer(self, layer_name: str) -> None:
        """Invalidate a specific layer for re-rendering."""
        layer = self.layer_manager.get_layer(layer_name)
        if layer:
            layer_bounds = layer.get_bounds()
            if layer_bounds:
                self._mark_dirty(layer_bounds)
    
    def invalidate_element(self, element: OverlayElement) -> None:
        """Invalidate a specific element for re-rendering."""
        element_bounds = element.get_bounds()
        if element_bounds:
            self._mark_dirty(element_bounds)
    
    def enable_pipeline(self, enable: bool = True) -> None:
        """Enable or disable pipeline rendering."""
        if enable and not self.render_pipeline:
            if self.viewport_info:
                self.render_pipeline = RenderPipeline(self.renderer_backend, self.viewport_info.bounds)
                self.render_pipeline.start()
                self.use_pipeline = True
        elif not enable and self.render_pipeline:
            self.render_pipeline.stop()
            self.render_pipeline = None
            self.use_pipeline = False
    
    def schedule_pipeline_render(self, layer_name: Optional[str] = None, 
                                priority: RenderPriority = RenderPriority.NORMAL) -> None:
        """Schedule a render operation through the pipeline."""
        if not self.render_pipeline or not self.viewport_info:
            return
        
        if layer_name:
            layer = self.layer_manager.get_layer(layer_name)
            if layer:
                layer_bounds = layer.get_bounds()
                if layer_bounds:
                    self.render_pipeline.schedule_layer_render(layer_name, layer_bounds, priority)
        else:
            self.render_pipeline.schedule_full_render(priority)
    
    def get_pipeline_performance(self) -> Dict[str, Any]:
        """Get pipeline performance metrics."""
        if self.render_pipeline:
            return self.render_pipeline.get_performance_metrics()
        return {}
    
    def get_render_statistics(self) -> Dict[str, Any]:
        """Get detailed rendering statistics."""
        stats = {
            'total_layers': len(self.layer_manager.get_all_layers()),
            'visible_layers': len([l for l in self.layer_manager.get_all_layers() if l.is_visible()]),
            'total_elements': sum(len(l.get_elements()) for l in self.layer_manager.get_all_layers()),
            'visible_elements': len(self.get_visible_elements()),
            'current_backend': self.current_backend.value,
            'dirty_regions': len(self.dirty_regions),
            'performance_metrics': self.performance_metrics.copy(),
            'use_pipeline': self.use_pipeline
        }
        
        # Add pipeline statistics
        if self.render_pipeline:
            stats['pipeline_metrics'] = self.render_pipeline.get_performance_metrics()
            stats['pipeline_frame_history'] = len(self.render_pipeline.get_frame_history())
        
        # Add layer-specific statistics
        layer_stats = {}
        for layer in self.layer_manager.get_all_layers():
            layer_stats[layer.name] = {
                'visible': layer.is_visible(),
                'element_count': len(layer.get_elements()),
                'bounds': layer.get_bounds(),
                'z_index': layer.get_z_index()
            }
        stats['layer_details'] = layer_stats
        
        return stats
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self.render_timer:
            self.render_timer.stop()
        
        if self.render_pipeline:
            self.render_pipeline.cleanup()
            self.render_pipeline = None
        
        if self.renderer_backend:
            self.renderer_backend.cleanup()
            self.renderer_backend = None
        
        self.layer_manager.cleanup()
        self.dirty_regions.clear()
        self.performance_metrics.clear()
        self.coordinate_transform = None
        self.viewport_info = None
        self.use_pipeline = False


class OverlayManager:
    """
    High-level manager for overlay operations.
    
    This class provides a simplified interface for common overlay operations
    and manages multiple overlay engines if needed.
    """
    
    def __init__(self):
        self.engines: Dict[str, OverlayEngine] = {}
        self.active_engine: Optional[str] = None
    
    def create_engine(self, name: str, parent_widget: QWidget, backend: RenderBackend = RenderBackend.CANVAS) -> OverlayEngine:
        """Create a new overlay engine."""
        engine = OverlayEngine(parent_widget, backend)
        self.engines[name] = engine
        
        if not self.active_engine:
            self.active_engine = name
        
        return engine
    
    def get_engine(self, name: str) -> Optional[OverlayEngine]:
        """Get an overlay engine by name."""
        return self.engines.get(name)
    
    def set_active_engine(self, name: str) -> bool:
        """Set the active overlay engine."""
        if name in self.engines:
            self.active_engine = name
            return True
        return False
    
    def get_active_engine(self) -> Optional[OverlayEngine]:
        """Get the active overlay engine."""
        if self.active_engine:
            return self.engines.get(self.active_engine)
        return None
    
    def remove_engine(self, name: str) -> bool:
        """Remove an overlay engine."""
        if name in self.engines:
            engine = self.engines[name]
            engine.cleanup()
            del self.engines[name]
            
            if self.active_engine == name:
                self.active_engine = next(iter(self.engines.keys())) if self.engines else None
            
            return True
        return False
    
    def cleanup(self) -> None:
        """Clean up all engines."""
        for engine in self.engines.values():
            engine.cleanup()
        self.engines.clear()
        self.active_engine = None