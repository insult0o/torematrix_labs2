"""
Selection Algorithms for Overlay Integration.
This module provides concrete implementations of selection algorithms that work
with the overlay system for different selection modes and strategies.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

from .coordinates import Rectangle, Point
from .layers import LayerElement
from .multi_select import SelectionStrategy, SelectionAlgorithm
from .overlay_integration import OverlayElementAdapter


@dataclass
class SelectionContext:
    """Context information for selection algorithms."""
    coordinate_transform: Optional[Any] = None
    viewport_bounds: Optional[Rectangle] = None
    zoom_level: float = 1.0
    selection_tolerance: float = 5.0  # pixels
    performance_mode: bool = False


class OverlaySelectionAlgorithm(SelectionAlgorithm):
    """Base class for overlay-aware selection algorithms."""
    
    def __init__(self, overlay_integration):
        self.overlay_integration = overlay_integration
        self.context = SelectionContext()
    
    def set_context(self, context: SelectionContext) -> None:
        """Set selection context."""
        self.context = context
    
    def get_available_elements(self) -> List[OverlayElementAdapter]:
        """Get all available elements from overlay."""
        return list(self.overlay_integration.element_cache.values())
    
    def transform_to_document_space(self, point: Point) -> Point:
        """Transform point to document space."""
        return self.overlay_integration.transform_point_to_document(point)
    
    def transform_to_screen_space(self, point: Point) -> Point:
        """Transform point to screen space."""
        return self.overlay_integration.transform_point_to_screen(point)


class RectangularSelector(OverlaySelectionAlgorithm):
    """Rectangular selection algorithm with overlay integration."""
    
    def __init__(self, overlay_integration, strategy: SelectionStrategy = SelectionStrategy.CONTAINS):
        super().__init__(overlay_integration)
        self.strategy = strategy
    
    def select(self, selection_bounds: Rectangle, elements: Optional[List[OverlayElementAdapter]] = None) -> List[OverlayElementAdapter]:
        """Select elements within rectangular bounds."""
        if elements is None:
            elements = self.get_available_elements()
        
        # Transform selection bounds to document space
        doc_bounds = self._transform_bounds_to_document(selection_bounds)
        
        selected = []
        
        for element in elements:
            if not element.is_visible():
                continue
            
            element_bounds = element.get_bounds()
            
            # Apply selection strategy
            if self._element_matches_strategy(element_bounds, doc_bounds):
                selected.append(element)
        
        return selected
    
    def _transform_bounds_to_document(self, screen_bounds: Rectangle) -> Rectangle:
        """Transform screen bounds to document coordinates."""
        if self.context.coordinate_transform:
            # Transform corners
            top_left = self.transform_to_document_space(
                Point(screen_bounds.x, screen_bounds.y)
            )
            bottom_right = self.transform_to_document_space(
                Point(screen_bounds.x + screen_bounds.width, screen_bounds.y + screen_bounds.height)
            )
            
            return Rectangle(
                top_left.x,
                top_left.y,
                bottom_right.x - top_left.x,
                bottom_right.y - top_left.y
            )
        
        return screen_bounds
    
    def _element_matches_strategy(self, element_bounds: Rectangle, selection_bounds: Rectangle) -> bool:
        """Check if element matches selection strategy."""
        if self.strategy == SelectionStrategy.CONTAINS:
            # Element must be completely contained within selection
            return (element_bounds.x >= selection_bounds.x and
                    element_bounds.y >= selection_bounds.y and
                    element_bounds.x + element_bounds.width <= selection_bounds.x + selection_bounds.width and
                    element_bounds.y + element_bounds.height <= selection_bounds.y + selection_bounds.height)
        
        elif self.strategy == SelectionStrategy.INTERSECTS:
            # Element must intersect with selection
            return selection_bounds.intersects(element_bounds)
        
        elif self.strategy == SelectionStrategy.CENTER_POINT:
            # Element center must be within selection
            center_x = element_bounds.x + element_bounds.width / 2
            center_y = element_bounds.y + element_bounds.height / 2
            return (center_x >= selection_bounds.x and
                    center_x <= selection_bounds.x + selection_bounds.width and
                    center_y >= selection_bounds.y and
                    center_y <= selection_bounds.y + selection_bounds.height)
        
        elif self.strategy == SelectionStrategy.MAJORITY:
            # Majority of element must be within selection
            intersection = selection_bounds.intersection(element_bounds)
            if intersection:
                element_area = element_bounds.width * element_bounds.height
                intersection_area = intersection.width * intersection.height
                return intersection_area > element_area * 0.5
            return False
        
        return False


class PolygonSelector(OverlaySelectionAlgorithm):
    """Polygon selection algorithm with overlay integration."""
    
    def __init__(self, overlay_integration, strategy: SelectionStrategy = SelectionStrategy.INTERSECTS):
        super().__init__(overlay_integration)
        self.strategy = strategy
    
    def select(self, polygon_points: List[Point], elements: Optional[List[OverlayElementAdapter]] = None) -> List[OverlayElementAdapter]:
        """Select elements within polygon bounds."""
        if elements is None:
            elements = self.get_available_elements()
        
        if len(polygon_points) < 3:
            return []
        
        # Transform polygon points to document space
        doc_points = [self.transform_to_document_space(point) for point in polygon_points]
        
        selected = []
        
        for element in elements:
            if not element.is_visible():
                continue
            
            element_bounds = element.get_bounds()
            
            # Apply selection strategy
            if self._element_matches_polygon_strategy(element_bounds, doc_points):
                selected.append(element)
        
        return selected
    
    def _element_matches_polygon_strategy(self, element_bounds: Rectangle, polygon_points: List[Point]) -> bool:
        """Check if element matches polygon selection strategy."""
        if self.strategy == SelectionStrategy.CONTAINS:
            # All corners of element must be within polygon
            corners = [
                Point(element_bounds.x, element_bounds.y),
                Point(element_bounds.x + element_bounds.width, element_bounds.y),
                Point(element_bounds.x + element_bounds.width, element_bounds.y + element_bounds.height),
                Point(element_bounds.x, element_bounds.y + element_bounds.height)
            ]
            return all(self._point_in_polygon(corner, polygon_points) for corner in corners)
        
        elif self.strategy == SelectionStrategy.INTERSECTS:
            # Element must intersect with polygon
            return self._rectangle_intersects_polygon(element_bounds, polygon_points)
        
        elif self.strategy == SelectionStrategy.CENTER_POINT:
            # Element center must be within polygon
            center = Point(
                element_bounds.x + element_bounds.width / 2,
                element_bounds.y + element_bounds.height / 2
            )
            return self._point_in_polygon(center, polygon_points)
        
        elif self.strategy == SelectionStrategy.MAJORITY:
            # Majority of element must be within polygon
            return self._majority_in_polygon(element_bounds, polygon_points)
        
        return False
    
    def _point_in_polygon(self, point: Point, polygon_points: List[Point]) -> bool:
        """Check if point is inside polygon using ray casting algorithm."""
        x, y = point.x, point.y
        n = len(polygon_points)
        inside = False
        
        p1x, p1y = polygon_points[0].x, polygon_points[0].y
        for i in range(1, n + 1):
            p2x, p2y = polygon_points[i % n].x, polygon_points[i % n].y
            
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            
            p1x, p1y = p2x, p2y
        
        return inside
    
    def _rectangle_intersects_polygon(self, rect: Rectangle, polygon_points: List[Point]) -> bool:
        """Check if rectangle intersects with polygon."""
        # Check if any polygon point is inside rectangle
        for point in polygon_points:
            if rect.contains(point):
                return True
        
        # Check if any rectangle corner is inside polygon
        corners = [
            Point(rect.x, rect.y),
            Point(rect.x + rect.width, rect.y),
            Point(rect.x + rect.width, rect.y + rect.height),
            Point(rect.x, rect.y + rect.height)
        ]
        
        for corner in corners:
            if self._point_in_polygon(corner, polygon_points):
                return True
        
        # Check if any polygon edge intersects rectangle edges
        rect_edges = [
            (corners[0], corners[1]),  # Top
            (corners[1], corners[2]),  # Right
            (corners[2], corners[3]),  # Bottom
            (corners[3], corners[0])   # Left
        ]
        
        for i in range(len(polygon_points)):
            poly_edge = (polygon_points[i], polygon_points[(i + 1) % len(polygon_points)])
            for rect_edge in rect_edges:
                if self._lines_intersect(poly_edge[0], poly_edge[1], rect_edge[0], rect_edge[1]):
                    return True
        
        return False
    
    def _lines_intersect(self, p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
        """Check if two line segments intersect."""
        def ccw(A, B, C):
            return (C.y - A.y) * (B.x - A.x) > (B.y - A.y) * (C.x - A.x)
        
        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)
    
    def _majority_in_polygon(self, rect: Rectangle, polygon_points: List[Point]) -> bool:
        """Check if majority of rectangle is within polygon."""
        # Sample points within rectangle
        sample_points = []
        samples_per_side = 5
        
        for i in range(samples_per_side):
            for j in range(samples_per_side):
                x = rect.x + (rect.width * i / (samples_per_side - 1))
                y = rect.y + (rect.height * j / (samples_per_side - 1))
                sample_points.append(Point(x, y))
        
        # Count how many sample points are inside polygon
        inside_count = sum(1 for point in sample_points if self._point_in_polygon(point, polygon_points))
        
        return inside_count > len(sample_points) * 0.5


class LassoSelector(OverlaySelectionAlgorithm):
    """Lasso (freehand) selection algorithm with overlay integration."""
    
    def __init__(self, overlay_integration, strategy: SelectionStrategy = SelectionStrategy.INTERSECTS):
        super().__init__(overlay_integration)
        self.strategy = strategy
        self.smoothing_enabled = True
        self.smoothing_tolerance = 3.0  # pixels
    
    def select(self, lasso_points: List[Point], elements: Optional[List[OverlayElementAdapter]] = None) -> List[OverlayElementAdapter]:
        """Select elements within lasso bounds."""
        if elements is None:
            elements = self.get_available_elements()
        
        if len(lasso_points) < 3:
            return []
        
        # Smooth lasso path if enabled
        if self.smoothing_enabled:
            lasso_points = self._smooth_lasso_path(lasso_points)
        
        # Transform lasso points to document space
        doc_points = [self.transform_to_document_space(point) for point in lasso_points]
        
        # Close the lasso path
        if doc_points[0] != doc_points[-1]:
            doc_points.append(doc_points[0])
        
        selected = []
        
        for element in elements:
            if not element.is_visible():
                continue
            
            element_bounds = element.get_bounds()
            
            # Apply selection strategy (reuse polygon logic)
            if self._element_matches_lasso_strategy(element_bounds, doc_points):
                selected.append(element)
        
        return selected
    
    def _smooth_lasso_path(self, points: List[Point]) -> List[Point]:
        """Smooth lasso path using Douglas-Peucker algorithm."""
        if len(points) < 3:
            return points
        
        return self._douglas_peucker_simplify(points, self.smoothing_tolerance)
    
    def _douglas_peucker_simplify(self, points: List[Point], tolerance: float) -> List[Point]:
        """Simplify path using Douglas-Peucker algorithm."""
        if len(points) < 3:
            return points
        
        # Find the point with maximum distance from line between first and last points
        max_distance = 0
        max_index = 0
        
        for i in range(1, len(points) - 1):
            distance = self._point_line_distance(points[i], points[0], points[-1])
            if distance > max_distance:
                max_distance = distance
                max_index = i
        
        # If max distance is greater than tolerance, recursively simplify
        if max_distance > tolerance:
            # Recursively simplify both parts
            left_part = self._douglas_peucker_simplify(points[:max_index + 1], tolerance)
            right_part = self._douglas_peucker_simplify(points[max_index:], tolerance)
            
            # Combine results (remove duplicate point at junction)
            return left_part[:-1] + right_part
        else:
            # If max distance is within tolerance, return line between first and last points
            return [points[0], points[-1]]
    
    def _point_line_distance(self, point: Point, line_start: Point, line_end: Point) -> float:
        """Calculate perpendicular distance from point to line."""
        # Vector from line_start to line_end
        line_vec = Point(line_end.x - line_start.x, line_end.y - line_start.y)
        
        # Vector from line_start to point
        point_vec = Point(point.x - line_start.x, point.y - line_start.y)
        
        # Calculate line length squared
        line_length_sq = line_vec.x * line_vec.x + line_vec.y * line_vec.y
        
        if line_length_sq == 0:
            # Line is actually a point
            return math.sqrt(point_vec.x * point_vec.x + point_vec.y * point_vec.y)
        
        # Calculate projection of point onto line
        projection = (point_vec.x * line_vec.x + point_vec.y * line_vec.y) / line_length_sq
        
        # Clamp projection to line segment
        projection = max(0, min(1, projection))
        
        # Calculate closest point on line
        closest_x = line_start.x + projection * line_vec.x
        closest_y = line_start.y + projection * line_vec.y
        
        # Calculate distance
        dx = point.x - closest_x
        dy = point.y - closest_y
        
        return math.sqrt(dx * dx + dy * dy)
    
    def _element_matches_lasso_strategy(self, element_bounds: Rectangle, lasso_points: List[Point]) -> bool:
        """Check if element matches lasso selection strategy."""
        # Reuse polygon selection logic
        polygon_selector = PolygonSelector(self.overlay_integration, self.strategy)
        return polygon_selector._element_matches_polygon_strategy(element_bounds, lasso_points)


class LayerSelector(OverlaySelectionAlgorithm):
    """Layer-based selection algorithm with overlay integration."""
    
    def __init__(self, overlay_integration):
        super().__init__(overlay_integration)
    
    def select(self, layer_names: List[str], elements: Optional[List[OverlayElementAdapter]] = None) -> List[OverlayElementAdapter]:
        """Select all elements in specified layers."""
        if elements is None:
            elements = self.get_available_elements()
        
        selected = []
        
        for element in elements:
            if not element.is_visible():
                continue
            
            if element.layer_name in layer_names:
                selected.append(element)
        
        return selected
    
    def select_by_layer_pattern(self, layer_pattern: str, elements: Optional[List[OverlayElementAdapter]] = None) -> List[OverlayElementAdapter]:
        """Select elements in layers matching a pattern."""
        if elements is None:
            elements = self.get_available_elements()
        
        import re
        pattern = re.compile(layer_pattern)
        
        selected = []
        
        for element in elements:
            if not element.is_visible():
                continue
            
            if pattern.match(element.layer_name):
                selected.append(element)
        
        return selected


class TypeSelector(OverlaySelectionAlgorithm):
    """Type-based selection algorithm with overlay integration."""
    
    def __init__(self, overlay_integration):
        super().__init__(overlay_integration)
    
    def select(self, element_types: List[str], elements: Optional[List[OverlayElementAdapter]] = None) -> List[OverlayElementAdapter]:
        """Select all elements of specified types."""
        if elements is None:
            elements = self.get_available_elements()
        
        selected = []
        
        for element in elements:
            if not element.is_visible():
                continue
            
            if element.element_type in element_types:
                selected.append(element)
        
        return selected
    
    def select_by_property(self, property_name: str, property_value: Any, elements: Optional[List[OverlayElementAdapter]] = None) -> List[OverlayElementAdapter]:
        """Select elements with specific property values."""
        if elements is None:
            elements = self.get_available_elements()
        
        selected = []
        
        for element in elements:
            if not element.is_visible():
                continue
            
            if property_name in element.properties:
                if element.properties[property_name] == property_value:
                    selected.append(element)
        
        return selected


class HybridSelector(OverlaySelectionAlgorithm):
    """Hybrid selection algorithm combining multiple strategies."""
    
    def __init__(self, overlay_integration):
        super().__init__(overlay_integration)
        self.selectors = {
            'rectangular': RectangularSelector(overlay_integration),
            'polygon': PolygonSelector(overlay_integration),
            'lasso': LassoSelector(overlay_integration),
            'layer': LayerSelector(overlay_integration),
            'type': TypeSelector(overlay_integration)
        }
    
    def select_hybrid(self, selection_criteria: Dict[str, Any], elements: Optional[List[OverlayElementAdapter]] = None) -> List[OverlayElementAdapter]:
        """Select elements using multiple criteria."""
        if elements is None:
            elements = self.get_available_elements()
        
        selected = set(elements)  # Start with all elements
        
        # Apply each criterion
        for criterion_type, criterion_value in selection_criteria.items():
            if criterion_type == 'bounds' and isinstance(criterion_value, Rectangle):
                selector = self.selectors['rectangular']
                criterion_results = selector.select(criterion_value, list(selected))
                selected &= set(criterion_results)
            
            elif criterion_type == 'polygon' and isinstance(criterion_value, list):
                selector = self.selectors['polygon']
                criterion_results = selector.select(criterion_value, list(selected))
                selected &= set(criterion_results)
            
            elif criterion_type == 'layers' and isinstance(criterion_value, list):
                selector = self.selectors['layer']
                criterion_results = selector.select(criterion_value, list(selected))
                selected &= set(criterion_results)
            
            elif criterion_type == 'types' and isinstance(criterion_value, list):
                selector = self.selectors['type']
                criterion_results = selector.select(criterion_value, list(selected))
                selected &= set(criterion_results)
            
            elif criterion_type == 'property' and isinstance(criterion_value, dict):
                selector = self.selectors['type']
                property_name = criterion_value.get('name')
                property_value = criterion_value.get('value')
                if property_name and property_value is not None:
                    criterion_results = selector.select_by_property(property_name, property_value, list(selected))
                    selected &= set(criterion_results)
        
        return list(selected)
    
    def select_union(self, selection_criteria: List[Dict[str, Any]], elements: Optional[List[OverlayElementAdapter]] = None) -> List[OverlayElementAdapter]:
        """Select elements that match any of the criteria (union)."""
        if elements is None:
            elements = self.get_available_elements()
        
        selected = set()
        
        for criterion in selection_criteria:
            criterion_results = self.select_hybrid(criterion, elements)
            selected |= set(criterion_results)
        
        return list(selected)