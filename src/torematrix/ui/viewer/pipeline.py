"""
Rendering Pipeline Architecture for Document Viewer Overlay.
This module provides efficient rendering pipeline with dirty region tracking,
batch rendering optimization, and performance monitoring.
"""
from __future__ import annotations

import time
import weakref
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from queue import Queue, PriorityQueue
import threading
import logging

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread, QMutex, QMutexLocker
from PyQt6.QtWidgets import QWidget, QApplication

from .coordinates import Rectangle, Point
from .layers import OverlayLayer, LayerElement
from .renderer import RendererBackend, RenderStyle

logger = logging.getLogger(__name__)


class RenderPriority(Enum):
    """Priority levels for rendering operations."""
    CRITICAL = 0    # Immediate rendering required
    HIGH = 1        # User interaction elements
    NORMAL = 2      # Standard elements
    LOW = 3         # Background elements
    BACKGROUND = 4  # Deferred rendering


class RenderOperation(Enum):
    """Types of rendering operations."""
    FULL_RENDER = "full_render"
    PARTIAL_RENDER = "partial_render"
    LAYER_RENDER = "layer_render"
    ELEMENT_RENDER = "element_render"
    CLEAR_REGION = "clear_region"


@dataclass
class RenderRequest:
    """Individual rendering request."""
    operation: RenderOperation
    priority: RenderPriority
    timestamp: float
    dirty_region: Rectangle
    layer_name: Optional[str] = None
    element_id: Optional[str] = None
    callback: Optional[Callable] = None
    context: Optional[Dict[str, Any]] = None
    
    def __lt__(self, other: RenderRequest) -> bool:
        """Compare requests for priority queue."""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.timestamp < other.timestamp


@dataclass
class RenderBatch:
    """Batch of rendering requests that can be processed together."""
    requests: List[RenderRequest] = field(default_factory=list)
    combined_region: Optional[Rectangle] = None
    batch_priority: RenderPriority = RenderPriority.NORMAL
    creation_time: float = field(default_factory=time.time)
    
    def add_request(self, request: RenderRequest) -> None:
        """Add a request to the batch."""
        self.requests.append(request)
        
        # Update combined region
        if self.combined_region is None:
            self.combined_region = request.dirty_region
        else:
            self.combined_region = self.combined_region.union(request.dirty_region)
        
        # Update batch priority to highest priority request
        if request.priority.value < self.batch_priority.value:
            self.batch_priority = request.priority
    
    def can_merge(self, request: RenderRequest) -> bool:
        """Check if a request can be merged into this batch."""
        if not self.requests:
            return True
        
        # Check if regions overlap or are adjacent
        if self.combined_region and request.dirty_region.intersects(self.combined_region):
            return True
        
        # Check if same layer
        if self.requests[0].layer_name and request.layer_name:
            return self.requests[0].layer_name == request.layer_name
        
        return False


@dataclass
class RenderFrame:
    """Information about a rendered frame."""
    frame_number: int
    start_time: float
    end_time: float
    render_time: float
    primitive_count: int
    dirty_regions: List[Rectangle]
    layers_rendered: List[str]
    performance_metrics: Dict[str, Any]


class RenderScheduler:
    """Scheduler for rendering operations with priority and batching."""
    
    def __init__(self, max_batch_size: int = 10, batch_timeout_ms: int = 16):
        self.max_batch_size = max_batch_size
        self.batch_timeout_ms = batch_timeout_ms
        
        # Request queues
        self.pending_requests: PriorityQueue[RenderRequest] = PriorityQueue()
        self.current_batches: List[RenderBatch] = []
        
        # Threading
        self.scheduler_thread: Optional[QThread] = None
        self.running = False
        self.mutex = QMutex()
        
        # Batch timer
        self.batch_timer = QTimer()
        self.batch_timer.setSingleShot(True)
        self.batch_timer.timeout.connect(self._flush_batches)
    
    def start(self) -> None:
        """Start the scheduler."""
        with QMutexLocker(self.mutex):
            if not self.running:
                self.running = True
                self._start_batch_timer()
    
    def stop(self) -> None:
        """Stop the scheduler."""
        with QMutexLocker(self.mutex):
            self.running = False
            self.batch_timer.stop()
    
    def schedule_request(self, request: RenderRequest) -> None:
        """Schedule a rendering request."""
        with QMutexLocker(self.mutex):
            if not self.running:
                return
            
            # Try to add to existing batch
            merged = False
            for batch in self.current_batches:
                if batch.can_merge(request):
                    batch.add_request(request)
                    merged = True
                    break
            
            # Create new batch if not merged
            if not merged:
                new_batch = RenderBatch()
                new_batch.add_request(request)
                self.current_batches.append(new_batch)
            
            # Check if we should flush batches
            if (len(self.current_batches) >= self.max_batch_size or
                request.priority == RenderPriority.CRITICAL):
                self._flush_batches()
    
    def get_next_batch(self) -> Optional[RenderBatch]:
        """Get the next batch for rendering."""
        with QMutexLocker(self.mutex):
            if self.current_batches:
                # Sort by priority and return highest priority batch
                self.current_batches.sort(key=lambda b: b.batch_priority.value)
                return self.current_batches.pop(0)
        return None
    
    def _start_batch_timer(self) -> None:
        """Start the batch timer."""
        if self.running:
            self.batch_timer.start(self.batch_timeout_ms)
    
    def _flush_batches(self) -> None:
        """Flush current batches to the render queue."""
        with QMutexLocker(self.mutex):
            if self.current_batches:
                # Sort batches by priority
                self.current_batches.sort(key=lambda b: b.batch_priority.value)
                
                # Add to pending queue
                for batch in self.current_batches:
                    for request in batch.requests:
                        self.pending_requests.put(request)
                
                self.current_batches.clear()
        
        # Restart timer
        self._start_batch_timer()


class DirtyRegionTracker:
    """Tracks dirty regions that need re-rendering."""
    
    def __init__(self, viewport_bounds: Rectangle):
        self.viewport_bounds = viewport_bounds
        self.dirty_regions: List[Rectangle] = []
        self.full_redraw_needed = False
        self.mutex = QMutex()
    
    def mark_dirty(self, region: Rectangle) -> None:
        """Mark a region as dirty."""
        with QMutexLocker(self.mutex):
            if self.full_redraw_needed:
                return
            
            # Check if region is within viewport
            if not self.viewport_bounds.intersects(region):
                return
            
            # Clip region to viewport
            clipped_region = self.viewport_bounds.intersection(region)
            
            # Try to merge with existing dirty regions
            merged = False
            for i, existing_region in enumerate(self.dirty_regions):
                if existing_region.intersects(clipped_region):
                    # Merge regions
                    self.dirty_regions[i] = existing_region.union(clipped_region)
                    merged = True
                    break
            
            if not merged:
                self.dirty_regions.append(clipped_region)
            
            # Check if we should do full redraw
            total_dirty_area = sum(r.width * r.height for r in self.dirty_regions)
            viewport_area = self.viewport_bounds.width * self.viewport_bounds.height
            
            if total_dirty_area > viewport_area * 0.75:  # 75% threshold
                self.mark_full_redraw()
    
    def mark_full_redraw(self) -> None:
        """Mark for full redraw."""
        with QMutexLocker(self.mutex):
            self.full_redraw_needed = True
            self.dirty_regions.clear()
    
    def get_dirty_regions(self) -> List[Rectangle]:
        """Get current dirty regions."""
        with QMutexLocker(self.mutex):
            if self.full_redraw_needed:
                return [self.viewport_bounds]
            return self.dirty_regions.copy()
    
    def clear_dirty_regions(self) -> None:
        """Clear all dirty regions."""
        with QMutexLocker(self.mutex):
            self.dirty_regions.clear()
            self.full_redraw_needed = False
    
    def update_viewport(self, new_bounds: Rectangle) -> None:
        """Update viewport bounds."""
        with QMutexLocker(self.mutex):
            self.viewport_bounds = new_bounds
            self.mark_full_redraw()  # Force full redraw on viewport change


class RenderPipeline(QObject):
    """Main rendering pipeline that orchestrates all rendering operations."""
    
    # Signals
    frame_rendered = pyqtSignal(object)  # RenderFrame
    pipeline_error = pyqtSignal(str)     # error_message
    performance_update = pyqtSignal(dict)  # performance_metrics
    
    def __init__(self, renderer: RendererBackend, viewport_bounds: Rectangle):
        super().__init__()
        
        self.renderer = renderer
        self.viewport_bounds = viewport_bounds
        
        # Pipeline components
        self.scheduler = RenderScheduler()
        self.dirty_tracker = DirtyRegionTracker(viewport_bounds)
        
        # Rendering state
        self.current_frame = 0
        self.is_rendering = False
        self.render_thread: Optional[QThread] = None
        
        # Performance monitoring
        self.performance_metrics = {
            'frames_rendered': 0,
            'average_frame_time': 0.0,
            'average_fps': 0.0,
            'total_render_time': 0.0,
            'peak_memory_usage': 0,
            'render_queue_size': 0
        }
        
        # Frame history
        self.frame_history: List[RenderFrame] = []
        self.max_frame_history = 100
        
        # Render timer
        self.render_timer = QTimer()
        self.render_timer.setSingleShot(True)
        self.render_timer.timeout.connect(self._execute_render_cycle)
        
        # Layer cache
        self.layer_cache: Dict[str, Any] = {}
        
        logger.debug("RenderPipeline initialized")
    
    def start(self) -> None:
        """Start the rendering pipeline."""
        self.scheduler.start()
        self.render_timer.start(16)  # ~60fps
        logger.info("Rendering pipeline started")
    
    def stop(self) -> None:
        """Stop the rendering pipeline."""
        self.scheduler.stop()
        self.render_timer.stop()
        logger.info("Rendering pipeline stopped")
    
    def schedule_render(self, operation: RenderOperation, region: Rectangle, 
                       priority: RenderPriority = RenderPriority.NORMAL,
                       layer_name: Optional[str] = None, callback: Optional[Callable] = None) -> None:
        """Schedule a rendering operation."""
        request = RenderRequest(
            operation=operation,
            priority=priority,
            timestamp=time.time(),
            dirty_region=region,
            layer_name=layer_name,
            callback=callback
        )
        
        self.scheduler.schedule_request(request)
        self.dirty_tracker.mark_dirty(region)
    
    def schedule_full_render(self, priority: RenderPriority = RenderPriority.NORMAL) -> None:
        """Schedule a full screen render."""
        self.schedule_render(
            RenderOperation.FULL_RENDER,
            self.viewport_bounds,
            priority
        )
    
    def schedule_layer_render(self, layer_name: str, region: Rectangle,
                             priority: RenderPriority = RenderPriority.NORMAL) -> None:
        """Schedule rendering of a specific layer."""
        self.schedule_render(
            RenderOperation.LAYER_RENDER,
            region,
            priority,
            layer_name
        )
    
    def invalidate_region(self, region: Rectangle) -> None:
        """Invalidate a region for re-rendering."""
        self.dirty_tracker.mark_dirty(region)
        
        # Schedule a render if not already scheduled
        if not self.render_timer.isActive():
            self.render_timer.start(16)
    
    def update_viewport(self, new_bounds: Rectangle) -> None:
        """Update viewport bounds."""
        self.viewport_bounds = new_bounds
        self.dirty_tracker.update_viewport(new_bounds)
        self.schedule_full_render(RenderPriority.HIGH)
    
    def _execute_render_cycle(self) -> None:
        """Execute a single render cycle."""
        if self.is_rendering:
            # Reschedule if already rendering
            self.render_timer.start(16)
            return
        
        try:
            self.is_rendering = True
            frame_start = time.time()
            
            # Get dirty regions
            dirty_regions = self.dirty_tracker.get_dirty_regions()
            
            if not dirty_regions:
                # No dirty regions, skip rendering
                self.is_rendering = False
                self.render_timer.start(16)
                return
            
            # Create render frame
            frame = RenderFrame(
                frame_number=self.current_frame,
                start_time=frame_start,
                end_time=0.0,
                render_time=0.0,
                primitive_count=0,
                dirty_regions=dirty_regions,
                layers_rendered=[],
                performance_metrics={}
            )
            
            # Begin rendering
            self.renderer.begin_render(self._create_render_context())
            
            # Process render requests
            primitive_count = 0
            layers_rendered = set()
            
            while True:
                batch = self.scheduler.get_next_batch()
                if not batch:
                    break
                
                # Process batch
                for request in batch.requests:
                    result = self._process_render_request(request)
                    if result:
                        primitive_count += result.get('primitive_count', 0)
                        if request.layer_name:
                            layers_rendered.add(request.layer_name)
                    
                    # Execute callback if provided
                    if request.callback:
                        request.callback(result)
            
            # End rendering
            self.renderer.end_render()
            
            # Clear dirty regions
            self.dirty_tracker.clear_dirty_regions()
            
            # Complete frame
            frame.end_time = time.time()
            frame.render_time = frame.end_time - frame.start_time
            frame.primitive_count = primitive_count
            frame.layers_rendered = list(layers_rendered)
            frame.performance_metrics = self.renderer.get_performance_metrics()
            
            # Update performance metrics
            self._update_performance_metrics(frame)
            
            # Add to frame history
            self.frame_history.append(frame)
            if len(self.frame_history) > self.max_frame_history:
                self.frame_history.pop(0)
            
            # Emit signals
            self.frame_rendered.emit(frame)
            self.performance_update.emit(self.performance_metrics)
            
            self.current_frame += 1
            
        except Exception as e:
            error_msg = f"Render cycle error: {e}"
            logger.error(error_msg)
            self.pipeline_error.emit(error_msg)
        
        finally:
            self.is_rendering = False
            
            # Schedule next render cycle
            self.render_timer.start(16)
    
    def _process_render_request(self, request: RenderRequest) -> Optional[Dict[str, Any]]:
        """Process a single render request."""
        try:
            if request.operation == RenderOperation.FULL_RENDER:
                return self._execute_full_render(request)
            elif request.operation == RenderOperation.LAYER_RENDER:
                return self._execute_layer_render(request)
            elif request.operation == RenderOperation.ELEMENT_RENDER:
                return self._execute_element_render(request)
            elif request.operation == RenderOperation.CLEAR_REGION:
                return self._execute_clear_region(request)
            else:
                return self._execute_partial_render(request)
        
        except Exception as e:
            logger.error(f"Error processing render request: {e}")
            return None
    
    def _execute_full_render(self, request: RenderRequest) -> Dict[str, Any]:
        """Execute a full render operation."""
        primitive_count = 0
        
        # Clear the region first
        self.renderer.clear_region(request.dirty_region)
        
        # Render all layers in the region
        # This would integrate with the layer manager
        # For now, return basic metrics
        
        return {
            'primitive_count': primitive_count,
            'render_time': 0.0,
            'success': True
        }
    
    def _execute_layer_render(self, request: RenderRequest) -> Dict[str, Any]:
        """Execute a layer render operation."""
        if not request.layer_name:
            return {'success': False, 'error': 'No layer name provided'}
        
        # Render specific layer
        # This would integrate with the layer manager
        
        return {
            'primitive_count': 0,
            'render_time': 0.0,
            'success': True,
            'layer_name': request.layer_name
        }
    
    def _execute_element_render(self, request: RenderRequest) -> Dict[str, Any]:
        """Execute an element render operation."""
        if not request.element_id:
            return {'success': False, 'error': 'No element ID provided'}
        
        # Render specific element
        # This would integrate with the element system
        
        return {
            'primitive_count': 1,
            'render_time': 0.0,
            'success': True,
            'element_id': request.element_id
        }
    
    def _execute_partial_render(self, request: RenderRequest) -> Dict[str, Any]:
        """Execute a partial render operation."""
        # Render only the dirty region
        primitive_count = 0
        
        # Clear the region first
        self.renderer.clear_region(request.dirty_region)
        
        # Render elements that intersect with the region
        # This would integrate with spatial indexing
        
        return {
            'primitive_count': primitive_count,
            'render_time': 0.0,
            'success': True
        }
    
    def _execute_clear_region(self, request: RenderRequest) -> Dict[str, Any]:
        """Execute a clear region operation."""
        self.renderer.clear_region(request.dirty_region)
        
        return {
            'primitive_count': 0,
            'render_time': 0.0,
            'success': True
        }
    
    def _create_render_context(self) -> Dict[str, Any]:
        """Create rendering context."""
        return {
            'viewport_bounds': self.viewport_bounds,
            'frame_number': self.current_frame,
            'timestamp': time.time(),
            'performance_metrics': self.performance_metrics
        }
    
    def _update_performance_metrics(self, frame: RenderFrame) -> None:
        """Update performance metrics with frame data."""
        self.performance_metrics['frames_rendered'] += 1
        self.performance_metrics['total_render_time'] += frame.render_time
        
        # Calculate averages
        frame_count = self.performance_metrics['frames_rendered']
        self.performance_metrics['average_frame_time'] = (
            self.performance_metrics['total_render_time'] / frame_count
        )
        
        if frame.render_time > 0:
            fps = 1.0 / frame.render_time
            if self.performance_metrics['average_fps'] == 0:
                self.performance_metrics['average_fps'] = fps
            else:
                # Exponential moving average
                alpha = 0.1
                self.performance_metrics['average_fps'] = (
                    alpha * fps + (1 - alpha) * self.performance_metrics['average_fps']
                )
        
        # Update queue size
        self.performance_metrics['render_queue_size'] = self.scheduler.pending_requests.qsize()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.performance_metrics.copy()
    
    def get_frame_history(self) -> List[RenderFrame]:
        """Get frame history."""
        return self.frame_history.copy()
    
    def cleanup(self) -> None:
        """Clean up pipeline resources."""
        self.stop()
        self.renderer.cleanup()
        self.layer_cache.clear()
        self.frame_history.clear()
        
        logger.debug("RenderPipeline cleaned up")


class PipelineManager:
    """High-level manager for render pipelines."""
    
    def __init__(self):
        self.pipelines: Dict[str, RenderPipeline] = {}
        self.active_pipeline: Optional[str] = None
    
    def create_pipeline(self, name: str, renderer: RendererBackend, 
                       viewport_bounds: Rectangle) -> RenderPipeline:
        """Create a new render pipeline."""
        pipeline = RenderPipeline(renderer, viewport_bounds)
        self.pipelines[name] = pipeline
        
        if not self.active_pipeline:
            self.active_pipeline = name
        
        return pipeline
    
    def get_pipeline(self, name: str) -> Optional[RenderPipeline]:
        """Get a render pipeline by name."""
        return self.pipelines.get(name)
    
    def set_active_pipeline(self, name: str) -> bool:
        """Set the active render pipeline."""
        if name in self.pipelines:
            self.active_pipeline = name
            return True
        return False
    
    def get_active_pipeline(self) -> Optional[RenderPipeline]:
        """Get the active render pipeline."""
        if self.active_pipeline:
            return self.pipelines.get(self.active_pipeline)
        return None
    
    def remove_pipeline(self, name: str) -> bool:
        """Remove a render pipeline."""
        if name in self.pipelines:
            pipeline = self.pipelines[name]
            pipeline.cleanup()
            del self.pipelines[name]
            
            if self.active_pipeline == name:
                self.active_pipeline = next(iter(self.pipelines.keys())) if self.pipelines else None
            
            return True
        return False
    
    def cleanup(self) -> None:
        """Clean up all pipelines."""
        for pipeline in self.pipelines.values():
            pipeline.cleanup()
        self.pipelines.clear()
        self.active_pipeline = None