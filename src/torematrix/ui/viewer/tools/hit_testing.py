"""
Optimized hit testing for selection tools with spatial indexing.
Provides efficient element detection for large document sets.
"""

import time
import math
from typing import List, Optional, Set, Tuple, Dict, Any
from dataclasses import dataclass
from collections import defaultdict, deque

from PyQt6.QtCore import QObject, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPolygonF, QTransform

from ..coordinates import Point, Rectangle
from ..layers import LayerElement


@dataclass
class HitTestResult:
    """Result of a hit test operation."""
    element: LayerElement
    distance: float
    point: Point
    confidence: float = 1.0
    
    def __lt__(self, other):
        """Enable sorting by distance."""
        return self.distance < other.distance


class QuadTreeNode:
    """Spatial partitioning node for efficient hit testing."""
    
    def __init__(self, bounds: Rectangle, max_depth: int = 8, max_elements: int = 10):
        self.bounds = bounds
        self.max_depth = max_depth
        self.max_elements = max_elements
        self.depth = 0
        
        self.elements: List[LayerElement] = []
        self.children: List['QuadTreeNode'] = []
        self.is_leaf = True
    
    def insert(self, element: LayerElement) -> bool:
        """Insert element into quad tree."""
        if not self._contains_element(element):
            return False
        
        if self.is_leaf and len(self.elements) < self.max_elements:
            self.elements.append(element)
            return True
        
        if self.is_leaf and self.depth < self.max_depth:
            self._subdivide()
        
        if not self.is_leaf:
            for child in self.children:
                if child.insert(element):
                    return True
        
        # Fallback: add to current node
        self.elements.append(element)
        return True
    
    def query(self, bounds: Rectangle) -> List[LayerElement]:
        """Query elements within bounds."""
        results = []
        
        if not self.bounds.intersects(bounds):
            return results
        
        # Add elements from this node
        for element in self.elements:
            if self._element_intersects_bounds(element, bounds):
                results.append(element)
        
        # Query children
        if not self.is_leaf:
            for child in self.children:
                results.extend(child.query(bounds))
        
        return results
    
    def query_point(self, point: Point, tolerance: float = 1.0) -> List[LayerElement]:
        """Query elements at point with tolerance."""
        query_bounds = Rectangle(
            point.x - tolerance, point.y - tolerance,
            tolerance * 2, tolerance * 2
        )
        return self.query(query_bounds)
    
    def clear(self):
        """Clear all elements from tree."""
        self.elements.clear()
        self.children.clear()
        self.is_leaf = True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get tree statistics for optimization."""
        stats = {
            'total_elements': len(self.elements),
            'depth': self.depth,
            'is_leaf': self.is_leaf,
            'children_count': len(self.children)
        }
        
        if not self.is_leaf:
            child_stats = [child.get_statistics() for child in self.children]
            stats['children'] = child_stats
            stats['total_elements'] += sum(s['total_elements'] for s in child_stats)
        
        return stats
    
    def _subdivide(self):
        """Split node into four children."""
        if not self.is_leaf:
            return
        
        half_width = self.bounds.width / 2
        half_height = self.bounds.height / 2
        x, y = self.bounds.x, self.bounds.y
        
        # Create four children
        self.children = [
            QuadTreeNode(Rectangle(x, y, half_width, half_height), 
                        self.max_depth, self.max_elements),  # NW
            QuadTreeNode(Rectangle(x + half_width, y, half_width, half_height), 
                        self.max_depth, self.max_elements),  # NE
            QuadTreeNode(Rectangle(x, y + half_height, half_width, half_height), 
                        self.max_depth, self.max_elements),  # SW
            QuadTreeNode(Rectangle(x + half_width, y + half_height, half_width, half_height), 
                        self.max_depth, self.max_elements)   # SE
        ]
        
        # Set depth for children
        for child in self.children:
            child.depth = self.depth + 1
        
        # Redistribute elements
        elements_to_redistribute = self.elements[:]
        self.elements.clear()
        self.is_leaf = False
        
        for element in elements_to_redistribute:
            inserted = False
            for child in self.children:
                if child.insert(element):
                    inserted = True
                    break
            
            if not inserted:
                self.elements.append(element)  # Keep in parent if doesn't fit children
    
    def _contains_element(self, element: LayerElement) -> bool:
        """Check if element bounds intersect with node bounds."""
        if not hasattr(element, 'bounds') or not element.bounds:
            return False
        
        return self.bounds.intersects(element.bounds)
    
    def _element_intersects_bounds(self, element: LayerElement, bounds: Rectangle) -> bool:
        """Check if element intersects with query bounds."""
        if not hasattr(element, 'bounds') or not element.bounds:
            return False
        
        return element.bounds.intersects(bounds)


class SpatialIndex(QObject):
    """
    Spatial indexing system for optimized hit testing.
    Uses quad-tree for efficient spatial queries.
    """
    
    index_updated = pyqtSignal()
    performance_metrics = pyqtSignal(dict)
    
    def __init__(self, bounds: Rectangle = None, parent=None):
        super().__init__(parent)
        
        # Default bounds if not provided
        if bounds is None:
            bounds = Rectangle(0, 0, 10000, 10000)  # Large default area
        
        self.quad_tree = QuadTreeNode(bounds, max_depth=8, max_elements=10)
        self.element_cache: Dict[str, LayerElement] = {}
        self.dirty = False
        
        # Performance tracking
        self.query_times = deque(maxlen=100)
        self.rebuild_times = deque(maxlen=20)
        self.cache_hits = 0
        self.cache_misses = 0
    
    def add_element(self, element: LayerElement):
        """Add element to spatial index."""
        if not element or not hasattr(element, 'id'):
            return
        
        self.element_cache[element.id] = element
        self.quad_tree.insert(element)
        self.dirty = True
    
    def remove_element(self, element_id: str):
        """Remove element from spatial index."""
        if element_id in self.element_cache:
            del self.element_cache[element_id]
            self._rebuild_index()  # Full rebuild needed for removal
    
    def update_element(self, element: LayerElement):
        """Update element in spatial index."""
        if not element or not hasattr(element, 'id'):
            return
        
        # Remove old version and add new
        if element.id in self.element_cache:
            self.remove_element(element.id)
        
        self.add_element(element)
    
    def query_point(self, point: Point, tolerance: float = 5.0) -> List[LayerElement]:
        """Query elements at point with tolerance."""
        start_time = time.perf_counter()
        
        try:
            results = self.quad_tree.query_point(point, tolerance)
            
            # Filter by actual hit testing
            hit_results = []
            for element in results:
                if self._precise_hit_test(element, point, tolerance):
                    hit_results.append(element)
            
            return hit_results
        
        finally:
            # Record performance
            end_time = time.perf_counter()
            query_time = (end_time - start_time) * 1000
            self.query_times.append(query_time)
    
    def query_rectangle(self, bounds: Rectangle) -> List[LayerElement]:
        """Query elements within rectangular bounds."""
        start_time = time.perf_counter()
        
        try:
            return self.quad_tree.query(bounds)
        
        finally:
            # Record performance
            end_time = time.perf_counter()
            query_time = (end_time - start_time) * 1000
            self.query_times.append(query_time)
    
    def nearest_elements(self, point: Point, max_count: int = 5, 
                        max_distance: float = 100.0) -> List[HitTestResult]:
        """Find nearest elements to point."""
        # Query larger area around point
        search_bounds = Rectangle(
            point.x - max_distance, point.y - max_distance,
            max_distance * 2, max_distance * 2
        )
        
        candidates = self.query_rectangle(search_bounds)
        
        # Calculate distances and sort
        results = []
        for element in candidates:
            distance = self._calculate_distance(element, point)
            if distance <= max_distance:
                results.append(HitTestResult(
                    element=element,
                    distance=distance,
                    point=point,
                    confidence=1.0 - (distance / max_distance)
                ))
        
        results.sort()
        return results[:max_count]
    
    def clear(self):
        """Clear all elements from index."""
        self.quad_tree.clear()
        self.element_cache.clear()
        self.dirty = False
        self.index_updated.emit()
    
    def rebuild(self):
        """Force rebuild of spatial index."""
        self._rebuild_index()
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for optimization."""
        if not self.query_times:
            return {
                'avg_query_time': 0.0,
                'max_query_time': 0.0,
                'query_count': 0,
                'cache_hit_rate': 0.0,
                'element_count': len(self.element_cache)
            }
        
        avg_query = sum(self.query_times) / len(self.query_times)
        max_query = max(self.query_times)
        
        total_cache_ops = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_cache_ops * 100) if total_cache_ops > 0 else 0
        
        metrics = {
            'avg_query_time': avg_query,
            'max_query_time': max_query,
            'query_count': len(self.query_times),
            'cache_hit_rate': hit_rate,
            'element_count': len(self.element_cache),
            'tree_stats': self.quad_tree.get_statistics(),
            'meets_target': avg_query < 10.0  # 10ms target
        }
        
        self.performance_metrics.emit(metrics)
        return metrics
    
    def optimize(self):
        """Optimize spatial index performance."""
        if self.dirty or len(self.element_cache) > 1000:
            self._rebuild_index()
        
        # Emit current metrics
        self.get_performance_metrics()
    
    # Private methods
    
    def _rebuild_index(self):
        """Rebuild spatial index from scratch."""
        start_time = time.perf_counter()
        
        try:
            # Clear and rebuild
            elements = list(self.element_cache.values())
            self.quad_tree.clear()
            
            for element in elements:
                self.quad_tree.insert(element)
            
            self.dirty = False
            self.index_updated.emit()
        
        finally:
            # Record rebuild time
            end_time = time.perf_counter()
            rebuild_time = (end_time - start_time) * 1000
            self.rebuild_times.append(rebuild_time)
    
    def _precise_hit_test(self, element: LayerElement, point: Point, tolerance: float) -> bool:
        """Perform precise hit testing on element."""
        if not hasattr(element, 'bounds') or not element.bounds:
            return False
        
        # Check if point is within element bounds plus tolerance
        expanded_bounds = Rectangle(
            element.bounds.x - tolerance,
            element.bounds.y - tolerance,
            element.bounds.width + tolerance * 2,
            element.bounds.height + tolerance * 2
        )
        
        return expanded_bounds.contains_point(point)
    
    def _calculate_distance(self, element: LayerElement, point: Point) -> float:
        """Calculate distance from point to element."""
        if not hasattr(element, 'bounds') or not element.bounds:
            return float('inf')
        
        # Distance to center of element
        center_x = element.bounds.x + element.bounds.width / 2
        center_y = element.bounds.y + element.bounds.height / 2
        
        dx = point.x - center_x
        dy = point.y - center_y
        
        return math.sqrt(dx * dx + dy * dy)


class HitTestOptimizer(QObject):
    """
    Advanced hit testing optimization system.
    Provides caching, prediction, and adaptive algorithms.
    """
    
    optimization_applied = pyqtSignal(str, dict)  # optimization_type, details
    
    def __init__(self, spatial_index: SpatialIndex, parent=None):
        super().__init__(parent)
        
        self.spatial_index = spatial_index
        
        # Caching system
        self.hit_cache: Dict[str, List[HitTestResult]] = {}
        self.cache_max_size = 1000
        self.cache_ttl = 5000  # 5 seconds
        
        # Prediction system
        self.recent_queries = deque(maxlen=50)
        self.hot_regions: Dict[str, int] = defaultdict(int)
        
        # Adaptive thresholds
        self.tolerance_history = deque(maxlen=100)
        self.optimal_tolerance = 5.0
    
    def optimized_hit_test(self, point: Point, tolerance: float = None) -> List[HitTestResult]:
        """Perform optimized hit test with caching and prediction."""
        if tolerance is None:
            tolerance = self.optimal_tolerance
        
        # Check cache first
        cache_key = f"{point.x}_{point.y}_{tolerance}"
        if cache_key in self.hit_cache:
            self.spatial_index.cache_hits += 1
            return self.hit_cache[cache_key]
        
        self.spatial_index.cache_misses += 1
        
        # Perform hit test
        elements = self.spatial_index.query_point(point, tolerance)
        
        # Convert to hit test results
        results = []
        for element in elements:
            distance = self.spatial_index._calculate_distance(element, point)
            results.append(HitTestResult(
                element=element,
                distance=distance,
                point=point,
                confidence=1.0 - (distance / tolerance) if tolerance > 0 else 1.0
            ))
        
        results.sort()
        
        # Cache result
        self._cache_result(cache_key, results)
        
        # Update statistics
        self._update_statistics(point, tolerance, len(results))
        
        return results
    
    def predict_next_queries(self, current_point: Point) -> List[Point]:
        """Predict likely next query points based on patterns."""
        if len(self.recent_queries) < 3:
            return []
        
        # Simple prediction based on movement pattern
        recent_points = list(self.recent_queries)[-3:]
        
        # Calculate movement vector
        dx = recent_points[-1].x - recent_points[-2].x
        dy = recent_points[-1].y - recent_points[-2].y
        
        # Predict next points along trajectory
        predictions = []
        for i in range(1, 4):  # Predict next 3 points
            predicted_point = Point(
                current_point.x + dx * i,
                current_point.y + dy * i
            )
            predictions.append(predicted_point)
        
        return predictions
    
    def preload_region(self, center: Point, radius: float):
        """Preload hit testing data for a region."""
        bounds = Rectangle(
            center.x - radius, center.y - radius,
            radius * 2, radius * 2
        )
        
        # Query and cache the region
        elements = self.spatial_index.query_rectangle(bounds)
        
        # Pre-cache common query points in the region
        step = max(1, radius / 10)
        for x in range(int(center.x - radius), int(center.x + radius), int(step)):
            for y in range(int(center.y - radius), int(center.y + radius), int(step)):
                point = Point(x, y)
                self.optimized_hit_test(point, self.optimal_tolerance)
        
        self.optimization_applied.emit("preload_region", {
            'center': (center.x, center.y),
            'radius': radius,
            'elements_loaded': len(elements)
        })
    
    def adapt_tolerance(self, success_rate: float):
        """Adapt hit testing tolerance based on success rate."""
        if success_rate < 0.3:  # Too restrictive
            self.optimal_tolerance *= 1.1
        elif success_rate > 0.8:  # Too permissive
            self.optimal_tolerance *= 0.95
        
        # Keep within reasonable bounds
        self.optimal_tolerance = max(1.0, min(20.0, self.optimal_tolerance))
        
        self.optimization_applied.emit("tolerance_adaptation", {
            'new_tolerance': self.optimal_tolerance,
            'success_rate': success_rate
        })
    
    def clear_cache(self):
        """Clear hit test cache."""
        self.hit_cache.clear()
        self.optimization_applied.emit("cache_cleared", {
            'cache_size_before': len(self.hit_cache)
        })
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_ops = self.spatial_index.cache_hits + self.spatial_index.cache_misses
        hit_rate = (self.spatial_index.cache_hits / total_ops * 100) if total_ops > 0 else 0
        
        return {
            'cache_size': len(self.hit_cache),
            'hit_rate': hit_rate,
            'total_operations': total_ops,
            'optimal_tolerance': self.optimal_tolerance
        }
    
    # Private methods
    
    def _cache_result(self, cache_key: str, results: List[HitTestResult]):
        """Cache hit test result with TTL."""
        if len(self.hit_cache) >= self.cache_max_size:
            # Remove oldest entries
            keys_to_remove = list(self.hit_cache.keys())[:10]
            for key in keys_to_remove:
                del self.hit_cache[key]
        
        self.hit_cache[cache_key] = results
    
    def _update_statistics(self, point: Point, tolerance: float, result_count: int):
        """Update hit testing statistics."""
        self.recent_queries.append(point)
        self.tolerance_history.append(tolerance)
        
        # Update hot regions
        region_key = f"{int(point.x // 100)}_{int(point.y // 100)}"
        self.hot_regions[region_key] += 1