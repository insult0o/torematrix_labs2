"""
Selection geometry algorithms and utilities.

This module provides geometric calculations for selection tools including
point-in-polygon testing, intersection detection, and spatial analysis.
"""

import math
from typing import List, Set, Tuple, Optional, Union
from PyQt6.QtCore import QPoint, QRect, QRectF
from PyQt6.QtGui import QPolygon, QPolygonF

from ..coordinates import Point, Rectangle
from ..layers import LayerElement


class SelectionGeometry:
    """Geometric algorithms for selection operations."""
    
    # Tolerance for floating point comparisons
    EPSILON = 1e-9
    
    @staticmethod
    def point_in_polygon(point: QPoint, polygon: List[QPoint]) -> bool:
        """
        Test if a point is inside a polygon using ray casting algorithm.
        
        Args:
            point: Point to test
            polygon: List of polygon vertices
            
        Returns:
            True if point is inside polygon
        """
        if len(polygon) < 3:
            return False
        
        x, y = point.x(), point.y()
        n = len(polygon)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i].x(), polygon[i].y()
            xj, yj = polygon[j].x(), polygon[j].y()
            
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        
        return inside
    
    @staticmethod
    def point_in_polygon_f(point: QPoint, polygon: List[QPoint]) -> bool:
        """
        Enhanced point-in-polygon test with better floating point handling.
        
        Args:
            point: Point to test
            polygon: List of polygon vertices
            
        Returns:
            True if point is inside polygon
        """
        if len(polygon) < 3:
            return False
        
        x, y = float(point.x()), float(point.y())
        n = len(polygon)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi, yi = float(polygon[i].x()), float(polygon[i].y())
            xj, yj = float(polygon[j].x()), float(polygon[j].y())
            
            # Check if point is on edge
            if SelectionGeometry._point_on_line_segment(x, y, xi, yi, xj, yj):
                return True
            
            # Ray casting algorithm
            if ((yi > y) != (yj > y)):
                # Calculate intersection x-coordinate
                if abs(yj - yi) > SelectionGeometry.EPSILON:
                    x_intersect = (xj - xi) * (y - yi) / (yj - yi) + xi
                    if x < x_intersect:
                        inside = not inside
            j = i
        
        return inside
    
    @staticmethod
    def _point_on_line_segment(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> bool:
        """Check if point lies on line segment."""
        # Check if point is within bounding box of line segment
        if not (min(x1, x2) <= px <= max(x1, x2) and min(y1, y2) <= py <= max(y1, y2)):
            return False
        
        # Check if point is on the line
        if abs(x2 - x1) < SelectionGeometry.EPSILON:
            return abs(px - x1) < SelectionGeometry.EPSILON
        
        if abs(y2 - y1) < SelectionGeometry.EPSILON:
            return abs(py - y1) < SelectionGeometry.EPSILON
        
        # Calculate distance from point to line
        a = y2 - y1
        b = x1 - x2
        c = x2 * y1 - x1 * y2
        
        distance = abs(a * px + b * py + c) / math.sqrt(a * a + b * b)
        return distance < SelectionGeometry.EPSILON
    
    @staticmethod
    def rect_intersects_elements(rect: QRect, elements: List[LayerElement]) -> List[LayerElement]:
        """
        Find elements that intersect with rectangle.
        
        Args:
            rect: Selection rectangle
            elements: List of elements to test
            
        Returns:
            List of intersecting elements
        """
        intersecting = []
        
        for element in elements:
            if hasattr(element, 'get_bounds'):
                element_bounds = element.get_bounds()
                if element_bounds:
                    element_rect = QRect(
                        int(element_bounds.x),
                        int(element_bounds.y),
                        int(element_bounds.width),
                        int(element_bounds.height)
                    )
                    if rect.intersects(element_rect):
                        intersecting.append(element)
            elif hasattr(element, 'bounding_rect'):
                if rect.intersects(element.bounding_rect):
                    intersecting.append(element)
        
        return intersecting
    
    @staticmethod
    def polygon_intersects_elements(polygon: List[QPoint], elements: List[LayerElement]) -> List[LayerElement]:
        """
        Find elements that intersect with polygon.
        
        Args:
            polygon: Selection polygon
            elements: List of elements to test
            
        Returns:
            List of intersecting elements
        """
        intersecting = []
        
        for element in elements:
            if SelectionGeometry._element_intersects_polygon(element, polygon):
                intersecting.append(element)
        
        return intersecting
    
    @staticmethod
    def _element_intersects_polygon(element: LayerElement, polygon: List[QPoint]) -> bool:
        """Check if element intersects with polygon."""
        # Get element bounds
        if hasattr(element, 'get_bounds'):
            bounds = element.get_bounds()
            if not bounds:
                return False
            
            # Create element corners
            corners = [
                QPoint(int(bounds.x), int(bounds.y)),
                QPoint(int(bounds.x + bounds.width), int(bounds.y)),
                QPoint(int(bounds.x + bounds.width), int(bounds.y + bounds.height)),
                QPoint(int(bounds.x), int(bounds.y + bounds.height))
            ]
        elif hasattr(element, 'bounding_rect'):
            rect = element.bounding_rect
            corners = [
                QPoint(rect.left(), rect.top()),
                QPoint(rect.right(), rect.top()),
                QPoint(rect.right(), rect.bottom()),
                QPoint(rect.left(), rect.bottom())
            ]
        else:
            return False
        
        # Check if any corner is inside polygon
        for corner in corners:
            if SelectionGeometry.point_in_polygon_f(corner, polygon):
                return True
        
        # Check if any polygon vertex is inside element bounds
        if hasattr(element, 'get_bounds'):
            bounds = element.get_bounds()
            element_rect = QRect(
                int(bounds.x),
                int(bounds.y),
                int(bounds.width),
                int(bounds.height)
            )
        else:
            element_rect = element.bounding_rect
        
        for vertex in polygon:
            if element_rect.contains(vertex):
                return True
        
        # Check for edge intersections
        return SelectionGeometry._polygon_rect_intersection(polygon, element_rect)
    
    @staticmethod
    def _polygon_rect_intersection(polygon: List[QPoint], rect: QRect) -> bool:
        """Check if polygon edges intersect with rectangle edges."""
        # Rectangle edges
        rect_edges = [
            (QPoint(rect.left(), rect.top()), QPoint(rect.right(), rect.top())),
            (QPoint(rect.right(), rect.top()), QPoint(rect.right(), rect.bottom())),
            (QPoint(rect.right(), rect.bottom()), QPoint(rect.left(), rect.bottom())),
            (QPoint(rect.left(), rect.bottom()), QPoint(rect.left(), rect.top()))
        ]
        
        # Check each polygon edge against each rectangle edge
        n = len(polygon)
        for i in range(n):
            p1 = polygon[i]
            p2 = polygon[(i + 1) % n]
            
            for rect_edge in rect_edges:
                if SelectionGeometry._line_segments_intersect(p1, p2, rect_edge[0], rect_edge[1]):
                    return True
        
        return False
    
    @staticmethod
    def _line_segments_intersect(p1: QPoint, p2: QPoint, p3: QPoint, p4: QPoint) -> bool:
        """Check if two line segments intersect."""
        def ccw(A: QPoint, B: QPoint, C: QPoint) -> bool:
            return (C.y() - A.y()) * (B.x() - A.x()) > (B.y() - A.y()) * (C.x() - A.x())
        
        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)
    
    @staticmethod
    def calculate_polygon_bounds(polygon: List[QPoint]) -> QRect:
        """Calculate bounding rectangle of polygon."""
        if not polygon:
            return QRect()
        
        min_x = min(p.x() for p in polygon)
        max_x = max(p.x() for p in polygon)
        min_y = min(p.y() for p in polygon)
        max_y = max(p.y() for p in polygon)
        
        return QRect(min_x, min_y, max_x - min_x, max_y - min_y)
    
    @staticmethod
    def calculate_polygon_area(polygon: List[QPoint]) -> float:
        """Calculate area of polygon using shoelace formula."""
        if len(polygon) < 3:
            return 0.0
        
        area = 0.0
        n = len(polygon)
        
        for i in range(n):
            j = (i + 1) % n
            area += polygon[i].x() * polygon[j].y()
            area -= polygon[j].x() * polygon[i].y()
        
        return abs(area) / 2.0
    
    @staticmethod
    def calculate_polygon_centroid(polygon: List[QPoint]) -> QPoint:
        """Calculate centroid of polygon."""
        if not polygon:
            return QPoint()
        
        if len(polygon) == 1:
            return polygon[0]
        
        cx = sum(p.x() for p in polygon) / len(polygon)
        cy = sum(p.y() for p in polygon) / len(polygon)
        
        return QPoint(int(cx), int(cy))
    
    @staticmethod
    def simplify_polygon(polygon: List[QPoint], tolerance: float = 2.0) -> List[QPoint]:
        """
        Simplify polygon using Douglas-Peucker algorithm.
        
        Args:
            polygon: Input polygon
            tolerance: Simplification tolerance
            
        Returns:
            Simplified polygon
        """
        if len(polygon) <= 2:
            return polygon
        
        def perpendicular_distance(point: QPoint, line_start: QPoint, line_end: QPoint) -> float:
            """Calculate perpendicular distance from point to line."""
            if line_start == line_end:
                return math.sqrt((point.x() - line_start.x()) ** 2 + (point.y() - line_start.y()) ** 2)
            
            A = line_end.y() - line_start.y()
            B = line_start.x() - line_end.x()
            C = line_end.x() * line_start.y() - line_start.x() * line_end.y()
            
            return abs(A * point.x() + B * point.y() + C) / math.sqrt(A * A + B * B)
        
        def douglas_peucker(points: List[QPoint], epsilon: float) -> List[QPoint]:
            """Recursive Douglas-Peucker implementation."""
            if len(points) <= 2:
                return points
            
            # Find the point with maximum distance
            max_distance = 0.0
            index = 0
            
            for i in range(1, len(points) - 1):
                distance = perpendicular_distance(points[i], points[0], points[-1])
                if distance > max_distance:
                    max_distance = distance
                    index = i
            
            # If max distance is greater than epsilon, recursively simplify
            if max_distance > epsilon:
                # Recursive call on both parts
                left_part = douglas_peucker(points[:index + 1], epsilon)
                right_part = douglas_peucker(points[index:], epsilon)
                
                # Combine results (remove duplicate point at index)
                return left_part[:-1] + right_part
            else:
                # All points between first and last can be removed
                return [points[0], points[-1]]
        
        return douglas_peucker(polygon, tolerance)
    
    @staticmethod
    def expand_rectangle(rect: QRect, pixels: int) -> QRect:
        """Expand rectangle by specified number of pixels."""
        return QRect(
            rect.x() - pixels,
            rect.y() - pixels,
            rect.width() + 2 * pixels,
            rect.height() + 2 * pixels
        )
    
    @staticmethod
    def contract_rectangle(rect: QRect, pixels: int) -> QRect:
        """Contract rectangle by specified number of pixels."""
        new_width = max(0, rect.width() - 2 * pixels)
        new_height = max(0, rect.height() - 2 * pixels)
        
        return QRect(
            rect.x() + pixels,
            rect.y() + pixels,
            new_width,
            new_height
        )
    
    @staticmethod
    def calculate_distance(p1: QPoint, p2: QPoint) -> float:
        """Calculate Euclidean distance between two points."""
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        return math.sqrt(dx * dx + dy * dy)
    
    @staticmethod
    def calculate_manhattan_distance(p1: QPoint, p2: QPoint) -> int:
        """Calculate Manhattan distance between two points."""
        return abs(p2.x() - p1.x()) + abs(p2.y() - p1.y())
    
    @staticmethod
    def point_to_line_distance(point: QPoint, line_start: QPoint, line_end: QPoint) -> float:
        """Calculate minimum distance from point to line segment."""
        if line_start == line_end:
            return SelectionGeometry.calculate_distance(point, line_start)
        
        # Vector from line_start to line_end
        line_vec_x = line_end.x() - line_start.x()
        line_vec_y = line_end.y() - line_start.y()
        
        # Vector from line_start to point
        point_vec_x = point.x() - line_start.x()
        point_vec_y = point.y() - line_start.y()
        
        # Project point onto line
        line_len_sq = line_vec_x * line_vec_x + line_vec_y * line_vec_y
        if line_len_sq == 0:
            return SelectionGeometry.calculate_distance(point, line_start)
        
        t = max(0, min(1, (point_vec_x * line_vec_x + point_vec_y * line_vec_y) / line_len_sq))
        
        # Find closest point on line segment
        closest_x = line_start.x() + t * line_vec_x
        closest_y = line_start.y() + t * line_vec_y
        
        # Calculate distance to closest point
        dx = point.x() - closest_x
        dy = point.y() - closest_y
        return math.sqrt(dx * dx + dy * dy)


class HitTesting:
    """Optimized hit testing for selection operations."""
    
    @staticmethod
    def test_point_hit(point: QPoint, elements: List[LayerElement], tolerance: int = 3) -> List[LayerElement]:
        """
        Test which elements are hit by a point with tolerance.
        
        Args:
            point: Test point
            elements: Elements to test
            tolerance: Hit tolerance in pixels
            
        Returns:
            List of hit elements
        """
        hit_elements = []
        test_rect = QRect(
            point.x() - tolerance,
            point.y() - tolerance,
            2 * tolerance,
            2 * tolerance
        )
        
        for element in elements:
            if hasattr(element, 'get_bounds'):
                bounds = element.get_bounds()
                if bounds:
                    element_rect = QRect(
                        int(bounds.x),
                        int(bounds.y),
                        int(bounds.width),
                        int(bounds.height)
                    )
                    if test_rect.intersects(element_rect):
                        hit_elements.append(element)
            elif hasattr(element, 'bounding_rect'):
                if test_rect.intersects(element.bounding_rect):
                    hit_elements.append(element)
        
        return hit_elements
    
    @staticmethod
    def test_rect_hit(rect: QRect, elements: List[LayerElement], mode: str = 'intersect') -> List[LayerElement]:
        """
        Test which elements are hit by a rectangle.
        
        Args:
            rect: Test rectangle
            elements: Elements to test
            mode: 'intersect' or 'contain'
            
        Returns:
            List of hit elements
        """
        hit_elements = []
        
        for element in elements:
            if hasattr(element, 'get_bounds'):
                bounds = element.get_bounds()
                if bounds:
                    element_rect = QRect(
                        int(bounds.x),
                        int(bounds.y),
                        int(bounds.width),
                        int(bounds.height)
                    )
                    
                    if mode == 'contain':
                        if rect.contains(element_rect):
                            hit_elements.append(element)
                    else:  # intersect
                        if rect.intersects(element_rect):
                            hit_elements.append(element)
            elif hasattr(element, 'bounding_rect'):
                if mode == 'contain':
                    if rect.contains(element.bounding_rect):
                        hit_elements.append(element)
                else:  # intersect
                    if rect.intersects(element.bounding_rect):
                        hit_elements.append(element)
        
        return hit_elements
    
    @staticmethod
    def test_polygon_hit(polygon: List[QPoint], elements: List[LayerElement], mode: str = 'intersect') -> List[LayerElement]:
        """
        Test which elements are hit by a polygon.
        
        Args:
            polygon: Test polygon
            elements: Elements to test
            mode: 'intersect' or 'contain'
            
        Returns:
            List of hit elements
        """
        if mode == 'contain':
            return HitTesting._test_polygon_contain(polygon, elements)
        else:
            return SelectionGeometry.polygon_intersects_elements(polygon, elements)
    
    @staticmethod
    def _test_polygon_contain(polygon: List[QPoint], elements: List[LayerElement]) -> List[LayerElement]:
        """Test which elements are completely contained within polygon."""
        contained_elements = []
        
        for element in elements:
            if hasattr(element, 'get_bounds'):
                bounds = element.get_bounds()
                if bounds:
                    corners = [
                        QPoint(int(bounds.x), int(bounds.y)),
                        QPoint(int(bounds.x + bounds.width), int(bounds.y)),
                        QPoint(int(bounds.x + bounds.width), int(bounds.y + bounds.height)),
                        QPoint(int(bounds.x), int(bounds.y + bounds.height))
                    ]
                else:
                    continue
            elif hasattr(element, 'bounding_rect'):
                rect = element.bounding_rect
                corners = [
                    QPoint(rect.left(), rect.top()),
                    QPoint(rect.right(), rect.top()),
                    QPoint(rect.right(), rect.bottom()),
                    QPoint(rect.left(), rect.bottom())
                ]
            else:
                continue
            
            # Check if all corners are inside polygon
            all_inside = True
            for corner in corners:
                if not SelectionGeometry.point_in_polygon_f(corner, polygon):
                    all_inside = False
                    break
            
            if all_inside:
                contained_elements.append(element)
        
        return contained_elements