"""
Multi-Element Selection Algorithms for Document Viewer Overlay.
This module provides advanced selection algorithms for complex multi-element
selection scenarios with geometric and semantic filtering capabilities.
"""
from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from .coordinates import Rectangle, Point
from .layers import LayerElement
from .selection import SelectionCriteria, SelectionAlgorithm


class SelectionStrategy(Enum):
    """Strategies for multi-element selection."""
    CONTAINS = "contains"           # Elements fully contained in selection
    INTERSECTS = "intersects"       # Elements intersecting with selection
    CENTER_POINT = "center_point"   # Elements whose center is in selection
    MAJORITY = "majority"           # Elements with majority area in selection


@dataclass
class SelectionPath:
    """Represents a selection path for lasso or polygon selection."""
    points: List[Point]
    closed: bool = False
    
    def get_bounds(self) -> Rectangle:
        """Get bounding rectangle of the path."""
        if not self.points:
            return Rectangle(0, 0, 0, 0)
        
        min_x = min(p.x for p in self.points)
        max_x = max(p.x for p in self.points)
        min_y = min(p.y for p in self.points)
        max_y = max(p.y for p in self.points)
        
        return Rectangle(min_x, min_y, max_x - min_x, max_y - min_y)


class GeometryUtils:
    """Utility functions for geometric calculations."""
    
    @staticmethod
    def point_in_polygon(point: Point, polygon: List[Point]) -> bool:
        """Check if a point is inside a polygon using ray casting algorithm."""
        x, y = point.x, point.y
        n = len(polygon)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i].x, polygon[i].y
            xj, yj = polygon[j].x, polygon[j].y
            
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        
        return inside
    
    @staticmethod
    def polygon_area(polygon: List[Point]) -> float:
        """Calculate area of a polygon using shoelace formula."""
        if len(polygon) < 3:
            return 0.0
        
        area = 0.0
        n = len(polygon)
        
        for i in range(n):
            j = (i + 1) % n
            area += polygon[i].x * polygon[j].y
            area -= polygon[j].x * polygon[i].y
        
        return abs(area) / 2.0
    
    @staticmethod
    def rectangle_polygon_intersection_area(rect: Rectangle, polygon: List[Point]) -> float:
        """Calculate intersection area between rectangle and polygon."""
        # Simplified implementation - returns approximate intersection
        # In a full implementation, you'd use a proper polygon clipping algorithm
        
        # Convert rectangle to polygon
        rect_polygon = [
            Point(rect.x, rect.y),
            Point(rect.x + rect.width, rect.y),
            Point(rect.x + rect.width, rect.y + rect.height),
            Point(rect.x, rect.y + rect.height)
        ]
        
        # Check if rectangle center is in polygon
        rect_center = Point(rect.x + rect.width/2, rect.y + rect.height/2)
        if GeometryUtils.point_in_polygon(rect_center, polygon):
            return rect.width * rect.height
        
        # Check if polygon center is in rectangle
        if polygon:
            poly_center_x = sum(p.x for p in polygon) / len(polygon)
            poly_center_y = sum(p.y for p in polygon) / len(polygon)
            poly_center = Point(poly_center_x, poly_center_y)
            
            if (rect.x <= poly_center.x <= rect.x + rect.width and
                rect.y <= poly_center.y <= rect.y + rect.height):
                return min(rect.width * rect.height, GeometryUtils.polygon_area(polygon))
        
        return 0.0
    
    @staticmethod
    def distance_point_to_line(point: Point, line_start: Point, line_end: Point) -> float:
        """Calculate distance from point to line segment."""
        # Vector from line_start to line_end
        line_vec = Point(line_end.x - line_start.x, line_end.y - line_start.y)
        
        # Vector from line_start to point
        point_vec = Point(point.x - line_start.x, point.y - line_start.y)
        
        # Calculate projection
        line_length_sq = line_vec.x * line_vec.x + line_vec.y * line_vec.y
        
        if line_length_sq == 0:
            # Line is a point
            return math.sqrt(point_vec.x * point_vec.x + point_vec.y * point_vec.y)
        
        t = max(0, min(1, (point_vec.x * line_vec.x + point_vec.y * line_vec.y) / line_length_sq))
        
        # Find closest point on line segment
        closest = Point(
            line_start.x + t * line_vec.x,
            line_start.y + t * line_vec.y
        )
        
        # Calculate distance
        dx = point.x - closest.x
        dy = point.y - closest.y
        return math.sqrt(dx * dx + dy * dy)


class AdvancedRectangularSelector(SelectionAlgorithm):
    """Advanced rectangular selector with multiple strategies."""
    
    def __init__(self, strategy: SelectionStrategy = SelectionStrategy.INTERSECTS):
        self.strategy = strategy
    
    def select(self, elements: List[LayerElement], criteria: SelectionCriteria) -> List[str]:
        """Select elements using advanced rectangular selection."""
        if not criteria.bounds:
            return []
        
        selected = []
        selection_bounds = criteria.bounds
        
        for element in elements:
            if not element.is_visible():
                continue
            
            element_bounds = element.get_bounds()
            
            # Apply selection strategy
            if self._element_matches_strategy(element_bounds, selection_bounds):
                if self._passes_filters(element, criteria):
                    selected.append(element.get_id())
        
        return selected
    
    def _element_matches_strategy(self, element_bounds: Rectangle, selection_bounds: Rectangle) -> bool:
        """Check if element matches the selection strategy."""
        if self.strategy == SelectionStrategy.CONTAINS:
            # Element must be fully contained
            return (element_bounds.x >= selection_bounds.x and
                   element_bounds.y >= selection_bounds.y and
                   element_bounds.x + element_bounds.width <= selection_bounds.x + selection_bounds.width and
                   element_bounds.y + element_bounds.height <= selection_bounds.y + selection_bounds.height)
        
        elif self.strategy == SelectionStrategy.INTERSECTS:
            # Element must intersect with selection
            return selection_bounds.intersects(element_bounds)
        
        elif self.strategy == SelectionStrategy.CENTER_POINT:
            # Element center must be in selection
            center_x = element_bounds.x + element_bounds.width / 2
            center_y = element_bounds.y + element_bounds.height / 2
            return (selection_bounds.x <= center_x <= selection_bounds.x + selection_bounds.width and
                   selection_bounds.y <= center_y <= selection_bounds.y + selection_bounds.height)
        
        elif self.strategy == SelectionStrategy.MAJORITY:
            # Majority of element area must be in selection
            intersection = selection_bounds.intersection(element_bounds)
            if intersection.width <= 0 or intersection.height <= 0:
                return False
            
            intersection_area = intersection.width * intersection.height
            element_area = element_bounds.width * element_bounds.height
            
            return intersection_area > element_area * 0.5
        
        return False
    
    def _passes_filters(self, element: LayerElement, criteria: SelectionCriteria) -> bool:
        """Check if element passes additional filter criteria."""
        # Type filter
        if criteria.element_types:
            element_type = getattr(element, 'element_type', None)
            if element_type not in criteria.element_types:
                return False
        
        # Layer filter
        if criteria.layers:
            layer_name = getattr(element, 'layer_name', None)
            if layer_name not in criteria.layers:
                return False
        
        # Size filter
        if criteria.min_size or criteria.max_size:
            bounds = element.get_bounds()
            element_size = bounds.width * bounds.height
            
            if criteria.min_size and element_size < criteria.min_size:
                return False
            if criteria.max_size and element_size > criteria.max_size:
                return False
        
        return True


class AdvancedPolygonSelector(SelectionAlgorithm):
    """Advanced polygon selector with geometric precision."""
    
    def __init__(self, strategy: SelectionStrategy = SelectionStrategy.INTERSECTS):
        self.strategy = strategy
        self.selection_path: Optional[SelectionPath] = None
    
    def set_selection_path(self, path: SelectionPath) -> None:
        """Set the selection path."""
        self.selection_path = path
    
    def select(self, elements: List[LayerElement], criteria: SelectionCriteria) -> List[str]:
        """Select elements using polygon selection."""
        if not self.selection_path or not self.selection_path.points:
            return []
        
        selected = []
        polygon_points = self.selection_path.points
        
        for element in elements:
            if not element.is_visible():
                continue
            
            element_bounds = element.get_bounds()
            
            # Apply selection strategy
            if self._element_matches_polygon_strategy(element_bounds, polygon_points):
                if self._passes_filters(element, criteria):
                    selected.append(element.get_id())
        
        return selected
    
    def _element_matches_polygon_strategy(self, element_bounds: Rectangle, polygon: List[Point]) -> bool:
        """Check if element matches polygon selection strategy."""
        if self.strategy == SelectionStrategy.CENTER_POINT:
            # Element center must be in polygon
            center = Point(
                element_bounds.x + element_bounds.width / 2,
                element_bounds.y + element_bounds.height / 2
            )
            return GeometryUtils.point_in_polygon(center, polygon)
        
        elif self.strategy == SelectionStrategy.CONTAINS:
            # All element corners must be in polygon
            corners = [
                Point(element_bounds.x, element_bounds.y),
                Point(element_bounds.x + element_bounds.width, element_bounds.y),
                Point(element_bounds.x + element_bounds.width, element_bounds.y + element_bounds.height),
                Point(element_bounds.x, element_bounds.y + element_bounds.height)
            ]
            
            return all(GeometryUtils.point_in_polygon(corner, polygon) for corner in corners)
        
        elif self.strategy == SelectionStrategy.INTERSECTS:
            # Element must intersect with polygon
            # Check if any corner is in polygon or polygon intersects element
            corners = [
                Point(element_bounds.x, element_bounds.y),
                Point(element_bounds.x + element_bounds.width, element_bounds.y),
                Point(element_bounds.x + element_bounds.width, element_bounds.y + element_bounds.height),
                Point(element_bounds.x, element_bounds.y + element_bounds.height)
            ]
            
            # Check if any corner is in polygon
            if any(GeometryUtils.point_in_polygon(corner, polygon) for corner in corners):
                return True
            
            # Check if any polygon point is in element
            for point in polygon:
                if (element_bounds.x <= point.x <= element_bounds.x + element_bounds.width and
                    element_bounds.y <= point.y <= element_bounds.y + element_bounds.height):
                    return True
            
            return False
        
        elif self.strategy == SelectionStrategy.MAJORITY:
            # Majority of element area must be in polygon
            intersection_area = GeometryUtils.rectangle_polygon_intersection_area(element_bounds, polygon)
            element_area = element_bounds.width * element_bounds.height
            
            return intersection_area > element_area * 0.5
        
        return False
    
    def _passes_filters(self, element: LayerElement, criteria: SelectionCriteria) -> bool:
        """Check if element passes additional filter criteria."""
        # Same as rectangular selector
        return True


class LassoSelector(SelectionAlgorithm):
    """Lasso (freehand) selector with smoothing and optimization."""
    
    def __init__(self, tolerance: float = 5.0):
        self.tolerance = tolerance  # Pixel tolerance for path smoothing
        self.selection_path: Optional[SelectionPath] = None
    
    def set_selection_path(self, path: SelectionPath) -> None:
        """Set the lasso selection path."""
        # Smooth the path to reduce noise
        smoothed_points = self._smooth_path(path.points)
        self.selection_path = SelectionPath(smoothed_points, closed=True)
    
    def select(self, elements: List[LayerElement], criteria: SelectionCriteria) -> List[str]:
        """Select elements using lasso selection."""
        if not self.selection_path:
            return []
        
        # Use polygon selector with the lasso path
        polygon_selector = AdvancedPolygonSelector(SelectionStrategy.INTERSECTS)
        polygon_selector.set_selection_path(self.selection_path)
        
        return polygon_selector.select(elements, criteria)
    
    def _smooth_path(self, points: List[Point]) -> List[Point]:
        """Smooth the lasso path using Douglas-Peucker algorithm."""
        if len(points) <= 2:
            return points
        
        return self._douglas_peucker(points, self.tolerance)
    
    def _douglas_peucker(self, points: List[Point], tolerance: float) -> List[Point]:
        """Douglas-Peucker line simplification algorithm."""
        if len(points) <= 2:
            return points
        
        # Find the point with maximum distance from line
        max_distance = 0
        max_index = 0
        
        for i in range(1, len(points) - 1):
            distance = GeometryUtils.distance_point_to_line(points[i], points[0], points[-1])
            if distance > max_distance:
                max_distance = distance
                max_index = i
        
        # If max distance is greater than tolerance, recursively simplify
        if max_distance > tolerance:
            # Recursive call
            left_points = self._douglas_peucker(points[:max_index + 1], tolerance)
            right_points = self._douglas_peucker(points[max_index:], tolerance)
            
            # Combine results
            return left_points[:-1] + right_points
        else:
            # Return endpoints only
            return [points[0], points[-1]]


class SmartSelector:
    """Smart selector that combines multiple selection algorithms."""
    
    def __init__(self):
        self.selectors = {
            'rectangular': AdvancedRectangularSelector(),
            'polygon': AdvancedPolygonSelector(),
            'lasso': LassoSelector()
        }
    
    def select_with_context(self, elements: List[LayerElement], selection_context: Dict[str, Any]) -> List[str]:
        """Select elements using context-aware algorithm selection."""
        selection_type = selection_context.get('type', 'rectangular')
        criteria = selection_context.get('criteria', SelectionCriteria())
        
        if selection_type == 'rectangular':
            bounds = selection_context.get('bounds')
            if bounds:
                criteria.bounds = bounds
                return self.selectors['rectangular'].select(elements, criteria)
        
        elif selection_type == 'polygon':
            polygon_points = selection_context.get('polygon_points')
            if polygon_points:
                path = SelectionPath(polygon_points, closed=True)
                selector = self.selectors['polygon']
                selector.set_selection_path(path)
                return selector.select(elements, criteria)
        
        elif selection_type == 'lasso':
            lasso_points = selection_context.get('lasso_points')
            if lasso_points:
                path = SelectionPath(lasso_points, closed=True)
                selector = self.selectors['lasso']
                selector.set_selection_path(path)
                return selector.select(elements, criteria)
        
        return []
    
    def get_selection_preview(self, elements: List[LayerElement], partial_context: Dict[str, Any]) -> List[str]:
        """Get preview of selection while user is still selecting."""
        # This could be used for real-time selection feedback
        return self.select_with_context(elements, partial_context)


class SelectionOptimizer:
    """Optimizer for selection performance with large datasets."""
    
    def __init__(self):
        self.element_cache = {}
        self.spatial_cache = {}
    
    def optimize_selection(self, elements: List[LayerElement], bounds: Rectangle) -> List[LayerElement]:
        """Optimize element list for selection within bounds."""
        # Pre-filter elements that are clearly outside bounds
        optimized_elements = []
        
        for element in elements:
            if not element.is_visible():
                continue
            
            element_bounds = element.get_bounds()
            
            # Quick bounds check
            if bounds.intersects(element_bounds):
                optimized_elements.append(element)
        
        return optimized_elements
    
    def cache_element_bounds(self, element: LayerElement) -> Rectangle:
        """Cache element bounds for performance."""
        element_id = element.get_id()
        
        if element_id in self.element_cache:
            return self.element_cache[element_id]
        
        bounds = element.get_bounds()
        self.element_cache[element_id] = bounds
        return bounds
    
    def clear_cache(self) -> None:
        """Clear optimization caches."""
        self.element_cache.clear()
        self.spatial_cache.clear()


# Export the main classes
__all__ = [
    'SelectionStrategy',
    'SelectionPath',
    'GeometryUtils',
    'AdvancedRectangularSelector',
    'AdvancedPolygonSelector',
    'LassoSelector',
    'SmartSelector',
    'SelectionOptimizer'
]