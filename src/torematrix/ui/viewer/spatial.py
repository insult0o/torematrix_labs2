"""
Spatial Indexing System for Agent 3 Performance Optimization.
This module provides quadtree spatial indexing for efficient element lookup
and management in the document viewer overlay system.
"""
from __future__ import annotations

import math
import threading
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from datetime import datetime

from .coordinates import Rectangle, Point
from .overlay_integration import OverlayElementAdapter


@dataclass
class SpatialBounds:
    """Spatial bounds for spatial indexing."""
    x: float
    y: float
    width: float
    height: float
    
    def intersects(self, other: 'SpatialBounds') -> bool:
        """Check if this bounds intersects with another."""
        return not (self.x + self.width < other.x or
                   other.x + other.width < self.x or
                   self.y + self.height < other.y or
                   other.y + other.height < self.y)
    
    def contains(self, point: Point) -> bool:
        """Check if bounds contains a point."""
        return (self.x <= point.x <= self.x + self.width and
                self.y <= point.y <= self.y + self.height)
    
    def contains_bounds(self, other: 'SpatialBounds') -> bool:
        """Check if this bounds completely contains another."""
        return (self.x <= other.x and
                self.y <= other.y and
                self.x + self.width >= other.x + other.width and
                self.y + self.height >= other.y + other.height)
    
    def area(self) -> float:
        """Calculate area of bounds."""
        return self.width * self.height
    
    def center(self) -> Point:
        """Get center point of bounds."""
        return Point(self.x + self.width / 2, self.y + self.height / 2)
    
    def expand(self, margin: float) -> 'SpatialBounds':
        """Expand bounds by margin."""
        return SpatialBounds(
            self.x - margin,
            self.y - margin,
            self.width + 2 * margin,
            self.height + 2 * margin
        )
    
    def to_rectangle(self) -> Rectangle:
        """Convert to Rectangle."""
        return Rectangle(self.x, self.y, self.width, self.height)
    
    @classmethod
    def from_rectangle(cls, rect: Rectangle) -> 'SpatialBounds':
        """Create from Rectangle."""
        return cls(rect.x, rect.y, rect.width, rect.height)


@dataclass
class SpatialElement:
    """Wrapper for elements in spatial index."""
    element_id: str
    bounds: SpatialBounds
    element: OverlayElementAdapter
    last_updated: datetime = field(default_factory=datetime.now)
    z_index: int = 0
    layer_name: str = ""
    
    def get_center(self) -> Point:
        """Get element center point."""
        return self.bounds.center()
    
    def get_area(self) -> float:
        """Get element area."""
        return self.bounds.area()
    
    def intersects(self, bounds: SpatialBounds) -> bool:
        """Check if element intersects with bounds."""
        return self.bounds.intersects(bounds)


class SpatialIndex(ABC):
    """Abstract base class for spatial indexing structures."""
    
    @abstractmethod
    def insert(self, element: SpatialElement) -> bool:
        """Insert element into spatial index."""
        pass
    
    @abstractmethod
    def remove(self, element_id: str) -> bool:
        """Remove element from spatial index."""
        pass
    
    @abstractmethod
    def query(self, bounds: SpatialBounds) -> List[SpatialElement]:
        """Query elements within bounds."""
        pass
    
    @abstractmethod
    def query_point(self, point: Point) -> List[SpatialElement]:
        """Query elements at a point."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all elements from index."""
        pass
    
    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """Get spatial index statistics."""
        pass


class QuadTreeNode:
    """Node in a quadtree spatial index."""
    
    def __init__(self, bounds: SpatialBounds, max_objects: int = 10, max_levels: int = 5, level: int = 0):
        self.bounds = bounds
        self.max_objects = max_objects
        self.max_levels = max_levels
        self.level = level
        self.objects: List[SpatialElement] = []
        self.nodes: List[Optional[QuadTreeNode]] = [None, None, None, None]
        
        # Statistics
        self.query_count = 0
        self.insert_count = 0
        self.last_accessed = datetime.now()
    
    def clear(self) -> None:
        """Clear all objects and child nodes."""
        self.objects.clear()
        for i in range(4):
            if self.nodes[i] is not None:
                self.nodes[i].clear()
                self.nodes[i] = None
    
    def is_leaf(self) -> bool:
        """Check if this is a leaf node."""
        return all(node is None for node in self.nodes)
    
    def _get_index(self, element_bounds: SpatialBounds) -> int:
        """Determine which quadrant the element belongs to."""
        mid_x = self.bounds.x + self.bounds.width / 2
        mid_y = self.bounds.y + self.bounds.height / 2
        
        # Check if element can fit completely in a quadrant
        top_quadrant = element_bounds.y + element_bounds.height < mid_y
        bottom_quadrant = element_bounds.y >= mid_y
        left_quadrant = element_bounds.x + element_bounds.width < mid_x
        right_quadrant = element_bounds.x >= mid_x
        
        if top_quadrant:
            if right_quadrant:
                return 0  # Top-right
            elif left_quadrant:
                return 1  # Top-left
        elif bottom_quadrant:
            if left_quadrant:
                return 2  # Bottom-left
            elif right_quadrant:
                return 3  # Bottom-right
        
        return -1  # Element doesn't fit completely in any quadrant
    
    def _split(self) -> None:
        """Split the node into four quadrants."""
        sub_width = self.bounds.width / 2
        sub_height = self.bounds.height / 2
        x = self.bounds.x
        y = self.bounds.y
        
        # Create child nodes for each quadrant
        self.nodes[0] = QuadTreeNode(  # Top-right
            SpatialBounds(x + sub_width, y, sub_width, sub_height),
            self.max_objects, self.max_levels, self.level + 1
        )
        self.nodes[1] = QuadTreeNode(  # Top-left
            SpatialBounds(x, y, sub_width, sub_height),
            self.max_objects, self.max_levels, self.level + 1
        )
        self.nodes[2] = QuadTreeNode(  # Bottom-left
            SpatialBounds(x, y + sub_height, sub_width, sub_height),
            self.max_objects, self.max_levels, self.level + 1
        )
        self.nodes[3] = QuadTreeNode(  # Bottom-right
            SpatialBounds(x + sub_width, y + sub_height, sub_width, sub_height),
            self.max_objects, self.max_levels, self.level + 1
        )
    
    def insert(self, element: SpatialElement) -> bool:
        """Insert element into this node."""
        self.insert_count += 1
        self.last_accessed = datetime.now()
        
        # If we have child nodes, try to insert into appropriate child
        if not self.is_leaf():
            index = self._get_index(element.bounds)
            if index != -1:
                return self.nodes[index].insert(element)
        
        # Add to this node
        self.objects.append(element)
        
        # Check if we need to split
        if len(self.objects) > self.max_objects and self.level < self.max_levels:
            if self.is_leaf():
                self._split()
            
            # Try to redistribute objects to child nodes
            objects_to_keep = []
            for obj in self.objects:
                index = self._get_index(obj.bounds)
                if index != -1:
                    self.nodes[index].insert(obj)
                else:
                    objects_to_keep.append(obj)
            
            self.objects = objects_to_keep
        
        return True
    
    def remove(self, element_id: str) -> bool:
        """Remove element from this node."""
        self.last_accessed = datetime.now()
        
        # Remove from this node's objects
        initial_count = len(self.objects)
        self.objects = [obj for obj in self.objects if obj.element_id != element_id]
        removed = len(self.objects) < initial_count
        
        # Remove from child nodes
        if not self.is_leaf():
            for node in self.nodes:
                if node is not None and node.remove(element_id):
                    removed = True
        
        return removed
    
    def query(self, bounds: SpatialBounds) -> List[SpatialElement]:
        """Query elements within bounds."""
        self.query_count += 1
        self.last_accessed = datetime.now()
        
        results = []
        
        # Check objects in this node
        for obj in self.objects:
            if obj.intersects(bounds):
                results.append(obj)
        
        # Check child nodes that intersect with query bounds
        if not self.is_leaf():
            for node in self.nodes:
                if node is not None and node.bounds.intersects(bounds):
                    results.extend(node.query(bounds))
        
        return results
    
    def query_point(self, point: Point) -> List[SpatialElement]:
        """Query elements at a specific point."""
        self.query_count += 1
        self.last_accessed = datetime.now()
        
        results = []
        
        # Check objects in this node
        for obj in self.objects:
            if obj.bounds.contains(point):
                results.append(obj)
        
        # Check child nodes that contain the point
        if not self.is_leaf():
            for node in self.nodes:
                if node is not None and node.bounds.contains(point):
                    results.extend(node.query_point(point))
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics for this node and all children."""
        stats = {
            'level': self.level,
            'object_count': len(self.objects),
            'is_leaf': self.is_leaf(),
            'query_count': self.query_count,
            'insert_count': self.insert_count,
            'last_accessed': self.last_accessed,
            'bounds': {
                'x': self.bounds.x,
                'y': self.bounds.y,
                'width': self.bounds.width,
                'height': self.bounds.height
            }
        }
        
        if not self.is_leaf():
            stats['children'] = []
            for i, node in enumerate(self.nodes):
                if node is not None:
                    child_stats = node.get_statistics()
                    child_stats['quadrant'] = i
                    stats['children'].append(child_stats)
        
        return stats


class QuadTreeSpatialIndex(SpatialIndex):
    """Quadtree implementation of spatial indexing."""
    
    def __init__(self, bounds: SpatialBounds, max_objects: int = 10, max_levels: int = 5):
        self.bounds = bounds
        self.max_objects = max_objects
        self.max_levels = max_levels
        self.root = QuadTreeNode(bounds, max_objects, max_levels, 0)
        self.element_lookup: Dict[str, SpatialElement] = {}
        
        # Thread safety
        self.lock = threading.RLock()
        
        # Performance tracking
        self.total_queries = 0
        self.total_inserts = 0
        self.total_removes = 0
        self.average_query_time = 0.0
        self.created_time = datetime.now()
    
    def insert(self, element: SpatialElement) -> bool:
        """Insert element into spatial index."""
        with self.lock:
            try:
                start_time = datetime.now()
                
                # Remove existing element if it exists
                if element.element_id in self.element_lookup:
                    self.remove(element.element_id)
                
                # Insert new element
                success = self.root.insert(element)
                
                if success:
                    self.element_lookup[element.element_id] = element
                    self.total_inserts += 1
                
                # Update performance metrics
                elapsed = (datetime.now() - start_time).total_seconds() * 1000
                self._update_performance_metrics('insert', elapsed)
                
                return success
                
            except Exception:
                return False
    
    def remove(self, element_id: str) -> bool:
        """Remove element from spatial index."""
        with self.lock:
            try:
                start_time = datetime.now()
                
                if element_id not in self.element_lookup:
                    return False
                
                success = self.root.remove(element_id)
                
                if success:
                    del self.element_lookup[element_id]
                    self.total_removes += 1
                
                # Update performance metrics
                elapsed = (datetime.now() - start_time).total_seconds() * 1000
                self._update_performance_metrics('remove', elapsed)
                
                return success
                
            except Exception:
                return False
    
    def query(self, bounds: SpatialBounds) -> List[SpatialElement]:
        """Query elements within bounds."""
        with self.lock:
            try:
                start_time = datetime.now()
                
                results = self.root.query(bounds)
                self.total_queries += 1
                
                # Update performance metrics
                elapsed = (datetime.now() - start_time).total_seconds() * 1000
                self._update_performance_metrics('query', elapsed)
                
                return results
                
            except Exception:
                return []
    
    def query_point(self, point: Point) -> List[SpatialElement]:
        """Query elements at a point."""
        with self.lock:
            try:
                start_time = datetime.now()
                
                results = self.root.query_point(point)
                self.total_queries += 1
                
                # Update performance metrics
                elapsed = (datetime.now() - start_time).total_seconds() * 1000
                self._update_performance_metrics('query_point', elapsed)
                
                return results
                
            except Exception:
                return []
    
    def query_nearest(self, point: Point, max_distance: float = float('inf'), max_results: int = 10) -> List[Tuple[SpatialElement, float]]:
        """Query nearest elements to a point."""
        with self.lock:
            try:
                start_time = datetime.now()
                
                # Get all elements within expanded bounds
                search_bounds = SpatialBounds(
                    point.x - max_distance,
                    point.y - max_distance,
                    2 * max_distance,
                    2 * max_distance
                )
                
                candidates = self.query(search_bounds)
                
                # Calculate distances and sort
                distances = []
                for element in candidates:
                    center = element.get_center()
                    distance = math.sqrt((center.x - point.x) ** 2 + (center.y - point.y) ** 2)
                    
                    if distance <= max_distance:
                        distances.append((element, distance))
                
                # Sort by distance and limit results
                distances.sort(key=lambda x: x[1])
                results = distances[:max_results]
                
                # Update performance metrics
                elapsed = (datetime.now() - start_time).total_seconds() * 1000
                self._update_performance_metrics('query_nearest', elapsed)
                
                return results
                
            except Exception:
                return []
    
    def clear(self) -> None:
        """Clear all elements from index."""
        with self.lock:
            self.root.clear()
            self.element_lookup.clear()
            
            # Reset statistics
            self.total_queries = 0
            self.total_inserts = 0
            self.total_removes = 0
            self.average_query_time = 0.0
    
    def rebuild(self, new_bounds: Optional[SpatialBounds] = None) -> None:
        """Rebuild the spatial index with optional new bounds."""
        with self.lock:
            # Store current elements
            elements = list(self.element_lookup.values())
            
            # Update bounds if provided
            if new_bounds:
                self.bounds = new_bounds
            
            # Clear and rebuild
            self.clear()
            self.root = QuadTreeNode(self.bounds, self.max_objects, self.max_levels, 0)
            
            # Re-insert all elements
            for element in elements:
                self.insert(element)
    
    def get_element(self, element_id: str) -> Optional[SpatialElement]:
        """Get element by ID."""
        with self.lock:
            return self.element_lookup.get(element_id)
    
    def get_all_elements(self) -> List[SpatialElement]:
        """Get all elements in the index."""
        with self.lock:
            return list(self.element_lookup.values())
    
    def get_element_count(self) -> int:
        """Get total number of elements."""
        with self.lock:
            return len(self.element_lookup)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive spatial index statistics."""
        with self.lock:
            root_stats = self.root.get_statistics()
            
            return {
                'index_type': 'QuadTree',
                'total_elements': len(self.element_lookup),
                'total_queries': self.total_queries,
                'total_inserts': self.total_inserts,
                'total_removes': self.total_removes,
                'average_query_time_ms': self.average_query_time,
                'max_objects_per_node': self.max_objects,
                'max_levels': self.max_levels,
                'created_time': self.created_time,
                'bounds': {
                    'x': self.bounds.x,
                    'y': self.bounds.y,
                    'width': self.bounds.width,
                    'height': self.bounds.height
                },
                'tree_structure': root_stats
            }
    
    def _update_performance_metrics(self, operation: str, elapsed_ms: float) -> None:
        """Update performance metrics."""
        # Update average query time (simple moving average)
        if operation in ['query', 'query_point', 'query_nearest']:
            if self.total_queries == 1:
                self.average_query_time = elapsed_ms
            else:
                alpha = 0.1  # Smoothing factor
                self.average_query_time = (1 - alpha) * self.average_query_time + alpha * elapsed_ms


class SpatialIndexManager:
    """Manager for spatial indexing operations."""
    
    def __init__(self, initial_bounds: SpatialBounds, max_objects: int = 10, max_levels: int = 5):
        self.spatial_index = QuadTreeSpatialIndex(initial_bounds, max_objects, max_levels)
        self.auto_rebuild_threshold = 1000  # Rebuild after this many operations
        self.operation_count = 0
        
        # Performance monitoring
        self.performance_history: List[Dict[str, Any]] = []
        self.max_history_size = 100
        
        # Element tracking
        self.element_layers: Dict[str, Set[str]] = {}  # layer_name -> element_ids
        self.element_types: Dict[str, Set[str]] = {}   # element_type -> element_ids
    
    def add_element(self, element: OverlayElementAdapter) -> bool:
        """Add element to spatial index."""
        try:
            # Convert to spatial element
            spatial_bounds = SpatialBounds.from_rectangle(element.bounds)
            spatial_element = SpatialElement(
                element_id=element.element_id,
                bounds=spatial_bounds,
                element=element,
                z_index=element.get_z_index(),
                layer_name=element.layer_name
            )
            
            # Insert into spatial index
            success = self.spatial_index.insert(spatial_element)
            
            if success:
                # Update tracking
                if element.layer_name not in self.element_layers:
                    self.element_layers[element.layer_name] = set()
                self.element_layers[element.layer_name].add(element.element_id)
                
                if element.element_type not in self.element_types:
                    self.element_types[element.element_type] = set()
                self.element_types[element.element_type].add(element.element_id)
                
                self._check_auto_rebuild()
            
            return success
            
        except Exception:
            return False
    
    def remove_element(self, element_id: str) -> bool:
        """Remove element from spatial index."""
        try:
            # Get element for cleanup
            spatial_element = self.spatial_index.get_element(element_id)
            
            success = self.spatial_index.remove(element_id)
            
            if success and spatial_element:
                # Update tracking
                layer_name = spatial_element.layer_name
                if layer_name in self.element_layers:
                    self.element_layers[layer_name].discard(element_id)
                    if not self.element_layers[layer_name]:
                        del self.element_layers[layer_name]
                
                element_type = spatial_element.element.element_type
                if element_type in self.element_types:
                    self.element_types[element_type].discard(element_id)
                    if not self.element_types[element_type]:
                        del self.element_types[element_type]
                
                self._check_auto_rebuild()
            
            return success
            
        except Exception:
            return False
    
    def query_region(self, bounds: Rectangle) -> List[OverlayElementAdapter]:
        """Query elements in a region."""
        try:
            spatial_bounds = SpatialBounds.from_rectangle(bounds)
            spatial_elements = self.spatial_index.query(spatial_bounds)
            return [elem.element for elem in spatial_elements]
        except Exception:
            return []
    
    def query_point(self, point: Point) -> List[OverlayElementAdapter]:
        """Query elements at a point."""
        try:
            spatial_elements = self.spatial_index.query_point(point)
            return [elem.element for elem in spatial_elements]
        except Exception:
            return []
    
    def query_nearest(self, point: Point, max_distance: float = 50.0, max_results: int = 10) -> List[Tuple[OverlayElementAdapter, float]]:
        """Query nearest elements to a point."""
        try:
            spatial_results = self.spatial_index.query_nearest(point, max_distance, max_results)
            return [(elem.element, distance) for elem, distance in spatial_results]
        except Exception:
            return []
    
    def query_by_layer(self, layer_name: str) -> List[OverlayElementAdapter]:
        """Query all elements in a layer."""
        try:
            if layer_name not in self.element_layers:
                return []
            
            elements = []
            for element_id in self.element_layers[layer_name]:
                spatial_element = self.spatial_index.get_element(element_id)
                if spatial_element:
                    elements.append(spatial_element.element)
            
            return elements
        except Exception:
            return []
    
    def query_by_type(self, element_type: str) -> List[OverlayElementAdapter]:
        """Query all elements of a type."""
        try:
            if element_type not in self.element_types:
                return []
            
            elements = []
            for element_id in self.element_types[element_type]:
                spatial_element = self.spatial_index.get_element(element_id)
                if spatial_element:
                    elements.append(spatial_element.element)
            
            return elements
        except Exception:
            return []
    
    def update_bounds(self, new_bounds: Rectangle) -> None:
        """Update spatial index bounds."""
        spatial_bounds = SpatialBounds.from_rectangle(new_bounds)
        self.spatial_index.rebuild(spatial_bounds)
        self.operation_count = 0  # Reset counter after rebuild
    
    def get_performance_statistics(self) -> Dict[str, Any]:
        """Get performance statistics."""
        stats = self.spatial_index.get_statistics()
        stats.update({
            'operation_count': self.operation_count,
            'auto_rebuild_threshold': self.auto_rebuild_threshold,
            'layer_count': len(self.element_layers),
            'type_count': len(self.element_types),
            'performance_history_size': len(self.performance_history)
        })
        return stats
    
    def _check_auto_rebuild(self) -> None:
        """Check if auto-rebuild is needed."""
        self.operation_count += 1
        
        if self.operation_count >= self.auto_rebuild_threshold:
            # Record performance before rebuild
            stats = self.spatial_index.get_statistics()
            self.performance_history.append({
                'timestamp': datetime.now(),
                'operation_count': self.operation_count,
                'element_count': stats['total_elements'],
                'average_query_time': stats['average_query_time_ms']
            })
            
            # Limit history size
            if len(self.performance_history) > self.max_history_size:
                self.performance_history = self.performance_history[-self.max_history_size:]
            
            # Rebuild with current bounds
            self.spatial_index.rebuild()
            self.operation_count = 0