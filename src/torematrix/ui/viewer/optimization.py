"""
Performance Optimization Utilities for Agent 3.
This module provides various optimization strategies and utilities
for improving rendering and interaction performance.
"""
from __future__ import annotations

import gc
import time
import threading
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
from datetime import datetime

from .coordinates import Rectangle, Point
# Forward reference to avoid circular imports


class OptimizationMode(Enum):
    """Performance optimization modes."""
    QUALITY = "quality"           # Prioritize visual quality
    PERFORMANCE = "performance"   # Prioritize performance
    BALANCED = "balanced"         # Balance quality and performance
    ADAPTIVE = "adaptive"         # Adapt based on system performance


@dataclass
class PerformanceTarget:
    """Performance targets for optimization."""
    target_fps: float = 60.0
    max_frame_time_ms: float = 16.67  # 1000ms / 60fps
    max_memory_mb: float = 100.0
    max_elements_per_frame: int = 1000


@dataclass
class OptimizationStats:
    """Statistics for performance optimization."""
    total_frames: int = 0
    dropped_frames: int = 0
    average_frame_time: float = 0.0
    peak_frame_time: float = 0.0
    memory_usage_mb: float = 0.0
    optimization_savings_ms: float = 0.0
    
    @property
    def frame_drop_rate(self) -> float:
        """Calculate frame drop rate."""
        if self.total_frames == 0:
            return 0.0
        return self.dropped_frames / self.total_frames
    
    @property
    def effective_fps(self) -> float:
        """Calculate effective FPS."""
        if self.average_frame_time == 0:
            return 0.0
        return 1000.0 / self.average_frame_time


class LevelOfDetail:
    """Level of Detail (LOD) management for elements."""
    
    def __init__(self):
        self.lod_thresholds = {
            0: 2.0,   # Full detail at zoom >= 2.0
            1: 1.0,   # High detail at zoom >= 1.0
            2: 0.5,   # Medium detail at zoom >= 0.5
            3: 0.25,  # Low detail at zoom >= 0.25
            4: 0.0    # Minimal detail below 0.25
        }
    
    def get_lod_level(self, zoom_level: float) -> int:
        """Get appropriate LOD level for zoom."""
        for lod_level in sorted(self.lod_thresholds.keys()):
            if zoom_level >= self.lod_thresholds[lod_level]:
                return lod_level
        return max(self.lod_thresholds.keys())
    
    def should_render_at_lod(self, element: Any, 
                           lod_level: int, zoom_level: float) -> bool:
        """Determine if element should be rendered at LOD level."""
        # Element size in screen pixels
        screen_size = min(element.bounds.width, element.bounds.height) * zoom_level
        
        # LOD-based filtering
        if lod_level >= 4:  # Minimal detail
            return screen_size >= 10 and element.get_z_index() > 50
        elif lod_level >= 3:  # Low detail
            return screen_size >= 5 and element.get_z_index() > 20
        elif lod_level >= 2:  # Medium detail
            return screen_size >= 2
        else:  # High or full detail
            return screen_size >= 1


class PerformanceOptimizer:
    """Main performance optimization system."""
    
    def __init__(self, targets: Optional[PerformanceTarget] = None):
        self.targets = targets or PerformanceTarget()
        self.mode = OptimizationMode.BALANCED
        self.lod_manager = LevelOfDetail()
        self.stats = OptimizationStats()
        self.auto_adjust_enabled = True
        self.last_gc_time = time.time()
        self.gc_interval = 30.0  # Force GC every 30 seconds
        self.lock = threading.Lock()
    
    def optimize_frame(self, elements: List[Any], 
                      zoom_level: float, viewport: Rectangle) -> Dict[str, Any]:
        """Perform frame-level optimizations."""
        frame_start = time.time()
        frame_number = self.stats.total_frames
        
        optimizations_applied = []
        
        with self.lock:
            # LOD optimization
            lod_level = self.lod_manager.get_lod_level(zoom_level)
            optimized_elements = []
            
            for element in elements:
                if self.lod_manager.should_render_at_lod(element, lod_level, zoom_level):
                    optimized_elements.append(element)
                else:
                    optimizations_applied.append('lod_culling')
            
            # Memory optimization
            if time.time() - self.last_gc_time > self.gc_interval:
                gc.collect()
                self.last_gc_time = time.time()
                optimizations_applied.append('garbage_collection')
            
            # Update statistics
            frame_time = (time.time() - frame_start) * 1000
            self._update_frame_statistics(frame_number, frame_time, len(optimized_elements))
        
        return {
            'optimized_elements': optimized_elements,
            'original_count': len(elements),
            'optimized_count': len(optimized_elements),
            'lod_level': lod_level,
            'frame_time_ms': frame_time,
            'optimizations_applied': optimizations_applied
        }
    
    def _update_frame_statistics(self, frame_number: int, frame_time: float, element_count: int) -> None:
        """Update frame statistics."""
        self.stats.total_frames += 1
        
        # Update average frame time (exponential moving average)
        alpha = 0.1
        if self.stats.average_frame_time == 0:
            self.stats.average_frame_time = frame_time
        else:
            self.stats.average_frame_time = (1 - alpha) * self.stats.average_frame_time + alpha * frame_time
        
        # Update peak frame time
        self.stats.peak_frame_time = max(self.stats.peak_frame_time, frame_time)
        
        # Check for dropped frames
        if frame_time > self.targets.max_frame_time_ms:
            self.stats.dropped_frames += 1
    
    def get_comprehensive_statistics(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        with self.lock:
            return {
                'optimization_mode': self.mode.value,
                'performance_targets': {
                    'target_fps': self.targets.target_fps,
                    'max_frame_time_ms': self.targets.max_frame_time_ms,
                    'max_memory_mb': self.targets.max_memory_mb
                },
                'frame_statistics': {
                    'total_frames': self.stats.total_frames,
                    'dropped_frames': self.stats.dropped_frames,
                    'frame_drop_rate': self.stats.frame_drop_rate,
                    'average_frame_time': self.stats.average_frame_time,
                    'effective_fps': self.stats.effective_fps,
                    'peak_frame_time': self.stats.peak_frame_time
                },
                'auto_adjust_enabled': self.auto_adjust_enabled,
                'last_gc_time': self.last_gc_time
            }