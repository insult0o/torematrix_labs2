"""
Viewport Culling System for Agent 3 Performance Optimization.
This module provides efficient viewport culling to render only visible elements
and improve performance for large document sets.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta

from .coordinates import Rectangle, Point
from .spatial import SpatialIndexManager, SpatialElement
from .overlay_integration import OverlayElementAdapter


class CullingStrategy(Enum):
    """Culling strategy options."""
    BASIC = "basic"           # Simple viewport intersection
    HIERARCHICAL = "hierarchical"  # Hierarchical culling with LOD
    FRUSTUM = "frustum"       # Frustum culling for 3D-like behavior
    OCCLUSION = "occlusion"   # Occlusion culling (advanced)


@dataclass
class ViewportBounds:
    """Viewport bounds with additional culling information."""
    bounds: Rectangle
    zoom_level: float = 1.0
    rotation: float = 0.0  # Future support for rotation
    margin: float = 0.0    # Extra margin for preloading
    
    def expanded_bounds(self) -> Rectangle:
        """Get bounds expanded by margin."""
        margin = self.margin
        return Rectangle(
            self.bounds.x - margin,
            self.bounds.y - margin,
            self.bounds.width + 2 * margin,
            self.bounds.height + 2 * margin
        )
    
    def get_lod_level(self) -> int:
        """Get level-of-detail based on zoom."""
        if self.zoom_level >= 2.0:
            return 0  # Highest detail
        elif self.zoom_level >= 1.0:
            return 1  # Medium detail
        elif self.zoom_level >= 0.5:
            return 2  # Low detail
        else:
            return 3  # Lowest detail


@dataclass
class CullingResult:
    """Result of viewport culling operation."""
    visible_elements: List[OverlayElementAdapter]
    culled_count: int
    total_elements: int
    culling_time_ms: float
    lod_level: int
    cache_hit: bool = False
    
    @property
    def cull_ratio(self) -> float:
        """Calculate culling efficiency ratio."""
        if self.total_elements == 0:
            return 0.0
        return self.culled_count / self.total_elements
    
    @property
    def visible_ratio(self) -> float:
        """Calculate visible element ratio."""
        if self.total_elements == 0:
            return 0.0
        return len(self.visible_elements) / self.total_elements


@dataclass
class ElementCullInfo:
    """Culling information for an element."""
    element_id: str
    bounds: Rectangle
    min_size_threshold: float = 1.0  # Minimum size in pixels to render
    max_distance: float = float('inf')  # Maximum distance from viewport center
    importance: float = 1.0  # Element importance (0-1)
    last_visible: Optional[datetime] = None
    visibility_count: int = 0
    
    def should_cull(self, viewport: ViewportBounds, distance_from_center: float) -> bool:
        """Determine if element should be culled."""
        # Size-based culling
        element_size = min(self.bounds.width, self.bounds.height) * viewport.zoom_level
        if element_size < self.min_size_threshold:
            return True
        
        # Distance-based culling
        if distance_from_center > self.max_distance:
            return True
        
        # Importance-based culling at low zoom levels
        if viewport.zoom_level < 0.5 and self.importance < 0.3:
            return True
        
        return False


class ViewportCullingCache:
    """Cache for viewport culling results."""
    
    def __init__(self, max_entries: int = 100, ttl_seconds: float = 1.0):
        self.cache: Dict[str, Tuple[CullingResult, datetime]] = {}
        self.max_entries = max_entries
        self.ttl = timedelta(seconds=ttl_seconds)
        self.lock = threading.RLock()
        
        # Statistics
        self.hits = 0
        self.misses = 0
        self.evictions = 0
    
    def _generate_key(self, viewport: ViewportBounds, strategy: CullingStrategy) -> str:
        """Generate cache key for viewport and strategy."""
        bounds = viewport.bounds
        return f"{strategy.value}_{bounds.x:.1f}_{bounds.y:.1f}_{bounds.width:.1f}_{bounds.height:.1f}_{viewport.zoom_level:.2f}"
    
    def get(self, viewport: ViewportBounds, strategy: CullingStrategy) -> Optional[CullingResult]:
        """Get cached culling result."""
        with self.lock:
            key = self._generate_key(viewport, strategy)
            
            if key in self.cache:
                result, timestamp = self.cache[key]
                
                # Check if cache entry is still valid
                if datetime.now() - timestamp <= self.ttl:
                    self.hits += 1
                    result.cache_hit = True
                    return result
                else:
                    # Remove expired entry
                    del self.cache[key]
            
            self.misses += 1
            return None
    
    def put(self, viewport: ViewportBounds, strategy: CullingStrategy, result: CullingResult) -> None:
        """Cache culling result."""
        with self.lock:
            key = self._generate_key(viewport, strategy)
            
            # Evict old entries if cache is full
            if len(self.cache) >= self.max_entries:
                self._evict_oldest()
            
            self.cache[key] = (result, datetime.now())
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self.lock:
            self.cache.clear()
            self.hits = 0
            self.misses = 0
            self.evictions = 0
    
    def _evict_oldest(self) -> None:
        """Evict oldest cache entry."""
        if not self.cache:
            return
        
        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
        del self.cache[oldest_key]
        self.evictions += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total_requests = self.hits + self.misses
            hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
            
            return {
                'entries': len(self.cache),
                'max_entries': self.max_entries,
                'hits': self.hits,
                'misses': self.misses,
                'evictions': self.evictions,
                'hit_rate': hit_rate,
                'ttl_seconds': self.ttl.total_seconds()
            }


class ViewportCuller:
    """Main viewport culling system."""
    
    def __init__(self, spatial_index: SpatialIndexManager, strategy: CullingStrategy = CullingStrategy.HIERARCHICAL):
        self.spatial_index = spatial_index
        self.strategy = strategy
        self.cache = ViewportCullingCache()
        
        # Element culling information
        self.element_cull_info: Dict[str, ElementCullInfo] = {}
        
        # Performance tracking
        self.total_culls = 0
        self.total_culling_time = 0.0
        self.average_culling_time = 0.0
        
        # Configuration
        self.enable_caching = True
        self.enable_lod = True
        self.preload_margin = 100.0  # pixels
        self.min_element_size_pixels = 2.0
        
        # Thread safety
        self.lock = threading.RLock()
    
    def cull_elements(self, viewport: ViewportBounds) -> CullingResult:
        """Perform viewport culling on elements."""
        with self.lock:
            start_time = time.time()
            
            # Check cache first
            if self.enable_caching:
                cached_result = self.cache.get(viewport, self.strategy)
                if cached_result is not None:
                    return cached_result
            
            # Perform culling based on strategy
            if self.strategy == CullingStrategy.BASIC:
                result = self._basic_culling(viewport)
            elif self.strategy == CullingStrategy.HIERARCHICAL:
                result = self._hierarchical_culling(viewport)
            elif self.strategy == CullingStrategy.FRUSTUM:
                result = self._frustum_culling(viewport)
            elif self.strategy == CullingStrategy.OCCLUSION:
                result = self._occlusion_culling(viewport)
            else:
                result = self._basic_culling(viewport)
            
            # Update performance metrics
            culling_time = (time.time() - start_time) * 1000
            result.culling_time_ms = culling_time
            self._update_performance_metrics(culling_time)
            
            # Cache result
            if self.enable_caching:
                self.cache.put(viewport, self.strategy, result)
            
            return result
    
    def _basic_culling(self, viewport: ViewportBounds) -> CullingResult:
        """Basic viewport culling using simple intersection."""
        # Expand viewport bounds for preloading
        expanded_bounds = viewport.expanded_bounds()
        
        # Query spatial index
        all_elements = self.spatial_index.query_region(expanded_bounds)
        visible_elements = []
        
        viewport_center = Point(
            viewport.bounds.x + viewport.bounds.width / 2,
            viewport.bounds.y + viewport.bounds.height / 2
        )
        
        for element in all_elements:
            # Basic visibility check
            if viewport.bounds.intersects(element.bounds):
                # Size-based culling
                if self._should_render_element(element, viewport, viewport_center):
                    visible_elements.append(element)
                    self._update_element_visibility(element.element_id)
        
        return CullingResult(
            visible_elements=visible_elements,
            culled_count=len(all_elements) - len(visible_elements),
            total_elements=len(all_elements),
            culling_time_ms=0.0,  # Will be set by caller
            lod_level=viewport.get_lod_level()
        )
    
    def _hierarchical_culling(self, viewport: ViewportBounds) -> CullingResult:
        """Hierarchical culling with level-of-detail support."""
        lod_level = viewport.get_lod_level()
        
        # Adjust culling parameters based on LOD
        if lod_level == 0:  # Highest detail
            margin_multiplier = 1.5
            size_threshold = self.min_element_size_pixels
        elif lod_level == 1:  # Medium detail
            margin_multiplier = 1.2
            size_threshold = self.min_element_size_pixels * 1.5
        elif lod_level == 2:  # Low detail
            margin_multiplier = 1.0
            size_threshold = self.min_element_size_pixels * 2.0
        else:  # Lowest detail
            margin_multiplier = 0.8
            size_threshold = self.min_element_size_pixels * 3.0
        
        # Expand viewport with LOD-adjusted margin
        viewport.margin = self.preload_margin * margin_multiplier
        expanded_bounds = viewport.expanded_bounds()
        
        # Query spatial index
        all_elements = self.spatial_index.query_region(expanded_bounds)
        visible_elements = []
        
        viewport_center = Point(
            viewport.bounds.x + viewport.bounds.width / 2,
            viewport.bounds.y + viewport.bounds.height / 2
        )
        
        for element in all_elements:
            # Check if element should be visible at this LOD level
            if self._should_render_at_lod(element, viewport, viewport_center, lod_level, size_threshold):
                visible_elements.append(element)
                self._update_element_visibility(element.element_id)
        
        return CullingResult(
            visible_elements=visible_elements,
            culled_count=len(all_elements) - len(visible_elements),
            total_elements=len(all_elements),
            culling_time_ms=0.0,
            lod_level=lod_level
        )
    
    def _frustum_culling(self, viewport: ViewportBounds) -> CullingResult:
        """Frustum culling for 3D-like behavior."""
        # For 2D, this is similar to hierarchical but with distance-based importance
        lod_level = viewport.get_lod_level()
        
        # Calculate frustum parameters
        viewport_center = Point(
            viewport.bounds.x + viewport.bounds.width / 2,
            viewport.bounds.y + viewport.bounds.height / 2
        )
        
        max_distance = max(viewport.bounds.width, viewport.bounds.height) * 0.7
        
        # Expand viewport for frustum
        viewport.margin = self.preload_margin
        expanded_bounds = viewport.expanded_bounds()
        
        # Query spatial index
        all_elements = self.spatial_index.query_region(expanded_bounds)
        visible_elements = []
        
        for element in all_elements:
            # Calculate distance from viewport center
            element_center = Point(
                element.bounds.x + element.bounds.width / 2,
                element.bounds.y + element.bounds.height / 2
            )
            
            distance = ((element_center.x - viewport_center.x) ** 2 + 
                       (element_center.y - viewport_center.y) ** 2) ** 0.5
            
            # Distance-based culling
            if distance <= max_distance:
                if self._should_render_element(element, viewport, viewport_center):
                    visible_elements.append(element)
                    self._update_element_visibility(element.element_id)
        
        return CullingResult(
            visible_elements=visible_elements,
            culled_count=len(all_elements) - len(visible_elements),
            total_elements=len(all_elements),
            culling_time_ms=0.0,
            lod_level=lod_level
        )
    
    def _occlusion_culling(self, viewport: ViewportBounds) -> CullingResult:
        """Advanced occlusion culling (simplified for 2D)."""
        # Start with hierarchical culling
        result = self._hierarchical_culling(viewport)
        
        # Sort by z-index (front to back)
        result.visible_elements.sort(key=lambda e: e.get_z_index(), reverse=True)
        
        # Simple occlusion test - remove elements completely behind others
        final_elements = []
        for element in result.visible_elements:
            # Check if element is occluded by any element already in final list
            is_occluded = False
            for front_element in final_elements:
                if (front_element.get_z_index() > element.get_z_index() and
                    front_element.bounds.contains_bounds(element.bounds)):
                    is_occluded = True
                    break
            
            if not is_occluded:
                final_elements.append(element)
        
        # Update result
        result.visible_elements = final_elements
        result.culled_count = result.total_elements - len(final_elements)
        
        return result
    
    def _should_render_element(self, element: OverlayElementAdapter, viewport: ViewportBounds, viewport_center: Point) -> bool:
        """Determine if element should be rendered."""
        # Get or create cull info
        cull_info = self._get_element_cull_info(element)
        
        # Calculate distance from viewport center
        element_center = Point(
            element.bounds.x + element.bounds.width / 2,
            element.bounds.y + element.bounds.height / 2
        )
        
        distance = ((element_center.x - viewport_center.x) ** 2 + 
                   (element_center.y - viewport_center.y) ** 2) ** 0.5
        
        # Use cull info to determine visibility
        return not cull_info.should_cull(viewport, distance)
    
    def _should_render_at_lod(self, element: OverlayElementAdapter, viewport: ViewportBounds, 
                             viewport_center: Point, lod_level: int, size_threshold: float) -> bool:
        """Determine if element should be rendered at specific LOD level."""
        # Basic visibility check
        if not viewport.bounds.intersects(element.bounds):
            return False
        
        # Size-based culling with LOD threshold
        element_size = min(element.bounds.width, element.bounds.height) * viewport.zoom_level
        if element_size < size_threshold:
            return False
        
        # LOD-specific filtering
        if lod_level >= 2:  # Low detail levels
            # Only render important elements
            cull_info = self._get_element_cull_info(element)
            if cull_info.importance < 0.5:
                return False
        
        if lod_level >= 3:  # Lowest detail
            # Only render very important elements
            cull_info = self._get_element_cull_info(element)
            if cull_info.importance < 0.8:
                return False
        
        return self._should_render_element(element, viewport, viewport_center)
    
    def _get_element_cull_info(self, element: OverlayElementAdapter) -> ElementCullInfo:
        """Get or create culling info for element."""
        if element.element_id not in self.element_cull_info:
            # Calculate importance based on element properties
            importance = self._calculate_element_importance(element)
            
            self.element_cull_info[element.element_id] = ElementCullInfo(
                element_id=element.element_id,
                bounds=element.bounds,
                min_size_threshold=self.min_element_size_pixels,
                importance=importance
            )
        
        return self.element_cull_info[element.element_id]
    
    def _calculate_element_importance(self, element: OverlayElementAdapter) -> float:
        """Calculate element importance for culling decisions."""
        importance = 0.5  # Base importance
        
        # Size-based importance
        area = element.bounds.width * element.bounds.height
        if area > 10000:  # Large elements are more important
            importance += 0.2
        elif area < 100:  # Small elements are less important
            importance -= 0.2
        
        # Z-index based importance
        z_index = element.get_z_index()
        if z_index > 100:  # High z-index elements are more important
            importance += 0.2
        
        # Layer-based importance (could be configured)
        if element.layer_name in ['annotations', 'text', 'important']:
            importance += 0.3
        
        # Type-based importance
        if element.element_type in ['text', 'title', 'heading']:
            importance += 0.2
        
        return max(0.0, min(1.0, importance))  # Clamp to [0, 1]
    
    def _update_element_visibility(self, element_id: str) -> None:
        """Update element visibility tracking."""
        if element_id in self.element_cull_info:
            cull_info = self.element_cull_info[element_id]
            cull_info.last_visible = datetime.now()
            cull_info.visibility_count += 1
    
    def _update_performance_metrics(self, culling_time_ms: float) -> None:
        """Update performance tracking metrics."""
        self.total_culls += 1
        self.total_culling_time += culling_time_ms
        
        # Update running average
        self.average_culling_time = self.total_culling_time / self.total_culls
    
    def set_strategy(self, strategy: CullingStrategy) -> None:
        """Set culling strategy."""
        if strategy != self.strategy:
            self.strategy = strategy
            self.cache.clear()  # Clear cache when strategy changes
    
    def set_configuration(self, **kwargs) -> None:
        """Set culling configuration parameters."""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Clear cache if configuration changes
        self.cache.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive culling statistics."""
        cache_stats = self.cache.get_statistics()
        
        return {
            'strategy': self.strategy.value,
            'total_culls': self.total_culls,
            'average_culling_time_ms': self.average_culling_time,
            'total_culling_time_ms': self.total_culling_time,
            'element_cull_info_count': len(self.element_cull_info),
            'cache_enabled': self.enable_caching,
            'lod_enabled': self.enable_lod,
            'preload_margin': self.preload_margin,
            'min_element_size_pixels': self.min_element_size_pixels,
            'cache_statistics': cache_stats
        }
    
    def clear_cache(self) -> None:
        """Clear culling cache."""
        self.cache.clear()
    
    def cleanup(self) -> None:
        """Clean up culling resources."""
        self.cache.clear()
        self.element_cull_info.clear()
        
        # Reset statistics
        self.total_culls = 0
        self.total_culling_time = 0.0
        self.average_culling_time = 0.0