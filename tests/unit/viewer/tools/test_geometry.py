"""
Tests for selection geometry algorithms and utilities.
"""

import pytest
import math
from PyQt6.QtCore import QPoint, QRect
from PyQt6.QtGui import QPolygon

from src.torematrix.ui.viewer.tools.geometry import SelectionGeometry, HitTesting


class MockLayerElement:
    """Mock layer element for testing."""
    
    def __init__(self, x, y, width, height, element_id="test"):
        from src.torematrix.ui.viewer.coordinates import Rectangle
        self._bounds = Rectangle(x, y, width, height)
        self._id = element_id
    
    def get_bounds(self):
        return self._bounds
    
    def get_id(self):
        return self._id


class TestSelectionGeometry:
    """Test SelectionGeometry class."""
    
    def test_point_in_polygon_simple(self):
        """Test point in polygon for simple cases."""
        # Square polygon
        polygon = [
            QPoint(0, 0),
            QPoint(10, 0),
            QPoint(10, 10),
            QPoint(0, 10)
        ]
        
        # Point inside
        assert SelectionGeometry.point_in_polygon(QPoint(5, 5), polygon) == True
        
        # Point outside
        assert SelectionGeometry.point_in_polygon(QPoint(15, 15), polygon) == False
        
        # Point on edge (may vary by implementation)
        edge_point = QPoint(5, 0)
        result = SelectionGeometry.point_in_polygon(edge_point, polygon)
        assert isinstance(result, bool)  # Should return a boolean
    
    def test_point_in_polygon_triangle(self):
        """Test point in polygon for triangle."""
        triangle = [
            QPoint(0, 0),
            QPoint(10, 0),
            QPoint(5, 10)
        ]
        
        # Point inside triangle
        assert SelectionGeometry.point_in_polygon(QPoint(5, 3), triangle) == True
        
        # Point outside triangle
        assert SelectionGeometry.point_in_polygon(QPoint(1, 8), triangle) == False
        assert SelectionGeometry.point_in_polygon(QPoint(9, 8), triangle) == False
    
    def test_point_in_polygon_degenerate(self):
        """Test point in polygon for degenerate cases."""
        # Empty polygon
        assert SelectionGeometry.point_in_polygon(QPoint(0, 0), []) == False
        
        # Single point
        assert SelectionGeometry.point_in_polygon(QPoint(0, 0), [QPoint(5, 5)]) == False
        
        # Two points (line)
        line = [QPoint(0, 0), QPoint(10, 0)]
        assert SelectionGeometry.point_in_polygon(QPoint(5, 0), line) == False
    
    def test_point_in_polygon_f_enhanced(self):
        """Test enhanced point in polygon with floating point handling."""
        polygon = [
            QPoint(0, 0),
            QPoint(10, 0),
            QPoint(10, 10),
            QPoint(0, 10)
        ]
        
        # Test same points as basic version
        assert SelectionGeometry.point_in_polygon_f(QPoint(5, 5), polygon) == True
        assert SelectionGeometry.point_in_polygon_f(QPoint(15, 15), polygon) == False
        
        # Test edge detection (should return True for points on edges)
        assert SelectionGeometry.point_in_polygon_f(QPoint(5, 0), polygon) == True
        assert SelectionGeometry.point_in_polygon_f(QPoint(10, 5), polygon) == True
    
    def test_rect_intersects_elements(self):
        """Test rectangle intersection with elements."""
        elements = [
            MockLayerElement(0, 0, 10, 10),    # Overlaps
            MockLayerElement(5, 5, 10, 10),    # Overlaps
            MockLayerElement(20, 20, 10, 10),  # No overlap
            MockLayerElement(-5, -5, 8, 8),    # Partial overlap
        ]
        
        test_rect = QRect(0, 0, 12, 12)
        intersecting = SelectionGeometry.rect_intersects_elements(test_rect, elements)
        
        # Should find first 3 elements (those that intersect)
        assert len(intersecting) == 3
        
        # Check specific elements
        ids = [elem.get_id() for elem in intersecting]
        assert "test" in ids  # All elements have same ID in this test
    
    def test_polygon_intersects_elements(self):
        """Test polygon intersection with elements."""
        elements = [
            MockLayerElement(0, 0, 10, 10),    # Should intersect
            MockLayerElement(20, 20, 10, 10),  # Should not intersect
            MockLayerElement(5, 5, 5, 5),      # Should intersect (inside)
        ]
        
        # L-shaped polygon
        polygon = [
            QPoint(0, 0),
            QPoint(15, 0),
            QPoint(15, 8),
            QPoint(8, 8),
            QPoint(8, 15),
            QPoint(0, 15)
        ]
        
        intersecting = SelectionGeometry.polygon_intersects_elements(polygon, elements)
        
        # Should find first and third elements
        assert len(intersecting) == 2
    
    def test_calculate_polygon_bounds(self):
        """Test polygon bounds calculation."""
        polygon = [
            QPoint(2, 3),
            QPoint(10, 1),
            QPoint(8, 12),
            QPoint(0, 8)
        ]
        
        bounds = SelectionGeometry.calculate_polygon_bounds(polygon)
        
        assert bounds.x() == 0
        assert bounds.y() == 1
        assert bounds.width() == 10
        assert bounds.height() == 11
    
    def test_calculate_polygon_bounds_empty(self):
        """Test polygon bounds for empty polygon."""
        bounds = SelectionGeometry.calculate_polygon_bounds([])
        assert bounds.isEmpty()
    
    def test_calculate_polygon_area(self):
        """Test polygon area calculation."""
        # Square with area 100
        square = [
            QPoint(0, 0),
            QPoint(10, 0),
            QPoint(10, 10),
            QPoint(0, 10)
        ]
        
        area = SelectionGeometry.calculate_polygon_area(square)
        assert area == 100.0
        
        # Triangle with area 25
        triangle = [
            QPoint(0, 0),
            QPoint(10, 0),
            QPoint(5, 10)
        ]
        
        area = SelectionGeometry.calculate_polygon_area(triangle)
        assert area == 50.0  # Base 10, height 10, area = 0.5 * 10 * 10 = 50
    
    def test_calculate_polygon_area_degenerate(self):
        """Test polygon area for degenerate cases."""
        # Empty polygon
        assert SelectionGeometry.calculate_polygon_area([]) == 0.0
        
        # Single point
        assert SelectionGeometry.calculate_polygon_area([QPoint(5, 5)]) == 0.0
        
        # Two points
        assert SelectionGeometry.calculate_polygon_area([QPoint(0, 0), QPoint(5, 5)]) == 0.0
    
    def test_calculate_polygon_centroid(self):
        """Test polygon centroid calculation."""
        # Square
        square = [
            QPoint(0, 0),
            QPoint(10, 0),
            QPoint(10, 10),
            QPoint(0, 10)
        ]
        
        centroid = SelectionGeometry.calculate_polygon_centroid(square)
        assert centroid.x() == 5
        assert centroid.y() == 5
        
        # Single point
        single_point = [QPoint(7, 13)]
        centroid = SelectionGeometry.calculate_polygon_centroid(single_point)
        assert centroid.x() == 7
        assert centroid.y() == 13
    
    def test_calculate_polygon_centroid_empty(self):
        """Test centroid for empty polygon."""
        centroid = SelectionGeometry.calculate_polygon_centroid([])
        assert centroid.x() == 0
        assert centroid.y() == 0
    
    def test_simplify_polygon(self):
        """Test polygon simplification."""
        # Create polygon with redundant points
        complex_polygon = [
            QPoint(0, 0),
            QPoint(1, 0),  # Redundant - on same line
            QPoint(2, 0),  # Redundant - on same line
            QPoint(10, 0),
            QPoint(10, 10),
            QPoint(0, 10)
        ]
        
        simplified = SelectionGeometry.simplify_polygon(complex_polygon, tolerance=1.0)
        
        # Should remove some redundant points
        assert len(simplified) <= len(complex_polygon)
        assert len(simplified) >= 3  # Should maintain basic shape
    
    def test_simplify_polygon_degenerate(self):
        """Test polygon simplification for degenerate cases."""
        # Empty polygon
        assert SelectionGeometry.simplify_polygon([]) == []
        
        # Single point
        single = [QPoint(5, 5)]
        assert SelectionGeometry.simplify_polygon(single) == single
        
        # Two points
        line = [QPoint(0, 0), QPoint(10, 10)]
        assert SelectionGeometry.simplify_polygon(line) == line
    
    def test_expand_rectangle(self):
        """Test rectangle expansion."""
        rect = QRect(10, 10, 20, 20)
        expanded = SelectionGeometry.expand_rectangle(rect, 5)
        
        assert expanded.x() == 5
        assert expanded.y() == 5
        assert expanded.width() == 30
        assert expanded.height() == 30
    
    def test_contract_rectangle(self):
        """Test rectangle contraction."""
        rect = QRect(10, 10, 20, 20)
        contracted = SelectionGeometry.contract_rectangle(rect, 3)
        
        assert contracted.x() == 13
        assert contracted.y() == 13
        assert contracted.width() == 14
        assert contracted.height() == 14
    
    def test_contract_rectangle_excessive(self):
        """Test rectangle contraction with excessive amount."""
        rect = QRect(10, 10, 20, 20)
        contracted = SelectionGeometry.contract_rectangle(rect, 15)  # More than half
        
        # Should not go negative
        assert contracted.width() >= 0
        assert contracted.height() >= 0
    
    def test_calculate_distance(self):
        """Test distance calculation."""
        p1 = QPoint(0, 0)
        p2 = QPoint(3, 4)
        
        distance = SelectionGeometry.calculate_distance(p1, p2)
        assert distance == 5.0  # 3-4-5 triangle
        
        # Same point
        distance = SelectionGeometry.calculate_distance(p1, p1)
        assert distance == 0.0
    
    def test_calculate_manhattan_distance(self):
        """Test Manhattan distance calculation."""
        p1 = QPoint(0, 0)
        p2 = QPoint(3, 4)
        
        distance = SelectionGeometry.calculate_manhattan_distance(p1, p2)
        assert distance == 7  # |3-0| + |4-0| = 7
        
        # Same point
        distance = SelectionGeometry.calculate_manhattan_distance(p1, p1)
        assert distance == 0
    
    def test_point_to_line_distance(self):
        """Test point to line distance calculation."""
        # Point to horizontal line
        point = QPoint(5, 10)
        line_start = QPoint(0, 5)
        line_end = QPoint(10, 5)
        
        distance = SelectionGeometry.point_to_line_distance(point, line_start, line_end)
        assert distance == 5.0  # Perpendicular distance
        
        # Point on line
        point_on_line = QPoint(5, 5)
        distance = SelectionGeometry.point_to_line_distance(point_on_line, line_start, line_end)
        assert abs(distance) < 0.001  # Should be very close to 0
    
    def test_point_to_line_distance_degenerate(self):
        """Test point to line distance for degenerate line."""
        point = QPoint(5, 5)
        line_point = QPoint(10, 10)
        
        # Line with same start and end point
        distance = SelectionGeometry.point_to_line_distance(point, line_point, line_point)
        expected = SelectionGeometry.calculate_distance(point, line_point)
        assert distance == expected


class TestHitTesting:
    """Test HitTesting class."""
    
    def test_test_point_hit(self):
        """Test point hit testing."""
        elements = [
            MockLayerElement(0, 0, 10, 10),
            MockLayerElement(20, 20, 10, 10),
            MockLayerElement(5, 5, 10, 10),  # Overlaps with first
        ]
        
        # Point that hits first and third elements
        hit_elements = HitTesting.test_point_hit(QPoint(7, 7), elements, tolerance=2)
        
        assert len(hit_elements) == 2  # First and third elements
        
        # Point that hits no elements
        hit_elements = HitTesting.test_point_hit(QPoint(100, 100), elements, tolerance=2)
        assert len(hit_elements) == 0
    
    def test_test_point_hit_tolerance(self):
        """Test point hit testing with different tolerances."""
        elements = [MockLayerElement(10, 10, 10, 10)]
        
        # Point just outside element
        test_point = QPoint(21, 15)
        
        # Small tolerance - should miss
        hit_elements = HitTesting.test_point_hit(test_point, elements, tolerance=1)
        assert len(hit_elements) == 0
        
        # Large tolerance - should hit
        hit_elements = HitTesting.test_point_hit(test_point, elements, tolerance=5)
        assert len(hit_elements) == 1
    
    def test_test_rect_hit_intersect(self):
        """Test rectangle hit testing with intersect mode."""
        elements = [
            MockLayerElement(0, 0, 10, 10),    # Partially intersects
            MockLayerElement(5, 5, 5, 5),      # Completely inside
            MockLayerElement(20, 20, 10, 10),  # No intersection
            MockLayerElement(-5, -5, 8, 8),    # Partially intersects
        ]
        
        test_rect = QRect(0, 0, 12, 12)
        hit_elements = HitTesting.test_rect_hit(test_rect, elements, mode='intersect')
        
        # Should hit first 3 elements
        assert len(hit_elements) == 3
    
    def test_test_rect_hit_contain(self):
        """Test rectangle hit testing with contain mode."""
        elements = [
            MockLayerElement(1, 1, 8, 8),      # Completely inside
            MockLayerElement(5, 5, 10, 10),    # Partially outside
            MockLayerElement(20, 20, 10, 10),  # Completely outside
        ]
        
        test_rect = QRect(0, 0, 10, 10)
        hit_elements = HitTesting.test_rect_hit(test_rect, elements, mode='contain')
        
        # Should only hit first element (completely contained)
        assert len(hit_elements) == 1
    
    def test_test_polygon_hit_intersect(self):
        """Test polygon hit testing with intersect mode."""
        elements = [
            MockLayerElement(0, 0, 5, 5),      # Should intersect
            MockLayerElement(10, 10, 5, 5),    # Should intersect
            MockLayerElement(20, 20, 5, 5),    # Should not intersect
        ]
        
        # Triangle polygon
        polygon = [
            QPoint(0, 0),
            QPoint(15, 0),
            QPoint(7, 15)
        ]
        
        hit_elements = HitTesting.test_polygon_hit(polygon, elements, mode='intersect')
        
        # Should hit first two elements
        assert len(hit_elements) == 2
    
    def test_test_polygon_hit_contain(self):
        """Test polygon hit testing with contain mode."""
        elements = [
            MockLayerElement(2, 2, 3, 3),      # Completely inside
            MockLayerElement(0, 0, 10, 10),    # Partially outside
            MockLayerElement(20, 20, 5, 5),    # Completely outside
        ]
        
        # Square polygon
        polygon = [
            QPoint(0, 0),
            QPoint(10, 0),
            QPoint(10, 10),
            QPoint(0, 10)
        ]
        
        hit_elements = HitTesting.test_polygon_hit(polygon, elements, mode='contain')
        
        # Should only hit first element (completely contained)
        assert len(hit_elements) == 1


if __name__ == "__main__":
    pytest.main([__file__])