"""
Comprehensive test suite for geometric utilities.
Tests all classes and methods in src.torematrix.utils.geometry.
"""

import pytest
import math
from unittest.mock import Mock, patch

from src.torematrix.utils.geometry import Point, Rect, Size, GeometryUtils


class TestPoint:
    """Test Point class functionality."""
    
    def test_point_creation(self):
        """Test point creation with various inputs."""
        p1 = Point(10.0, 20.0)
        assert p1.x == 10.0
        assert p1.y == 20.0
        
        p2 = Point(0, 0)
        assert p2.x == 0.0
        assert p2.y == 0.0
        
        p3 = Point(-5.5, 3.14)
        assert p3.x == -5.5
        assert p3.y == 3.14
    
    def test_point_distance(self):
        """Test distance calculation between points."""
        p1 = Point(0.0, 0.0)
        p2 = Point(3.0, 4.0)
        
        distance = p1.distance_to(p2)
        assert distance == 5.0
        
        # Distance is symmetric
        assert p2.distance_to(p1) == distance
        
        # Distance to self is zero
        assert p1.distance_to(p1) == 0.0
    
    def test_point_midpoint(self):
        """Test midpoint calculation."""
        p1 = Point(0.0, 0.0)
        p2 = Point(10.0, 20.0)
        
        midpoint = p1.midpoint(p2)
        assert midpoint.x == 5.0
        assert midpoint.y == 10.0
    
    def test_point_rotation(self):
        """Test point rotation."""
        p = Point(1.0, 0.0)
        
        # Rotate 90 degrees around origin
        rotated = p.rotate(math.pi / 2)
        assert abs(rotated.x) < 1e-10
        assert abs(rotated.y - 1.0) < 1e-10
        
        # Rotate around center
        center = Point(5.0, 5.0)
        rotated_center = p.rotate(math.pi / 2, center)
        assert abs(rotated_center.x - 5.0) < 1e-10
        assert abs(rotated_center.y - 1.0) < 1e-10
    
    def test_point_scale(self):
        """Test point scaling."""
        p = Point(10.0, 20.0)
        
        # Scale from origin
        scaled = p.scale(2.0)
        assert scaled.x == 20.0
        assert scaled.y == 40.0
        
        # Scale with different factors
        scaled_xy = p.scale_xy(2.0, 3.0)
        assert scaled_xy.x == 20.0
        assert scaled_xy.y == 60.0
        
        # Scale around center
        center = Point(5.0, 5.0)
        scaled_center = p.scale(2.0, center)
        assert scaled_center.x == 15.0  # 5 + (10-5)*2
        assert scaled_center.y == 35.0  # 5 + (20-5)*2
    
    def test_point_translate(self):
        """Test point translation."""
        p = Point(10.0, 20.0)
        
        translated = p.translate(5.0, 10.0)
        assert translated.x == 15.0
        assert translated.y == 30.0
    
    def test_point_normalize(self):
        """Test point normalization."""
        p = Point(3.0, 4.0)
        normalized = p.normalize()
        
        # Length should be 1.0
        assert abs(normalized.magnitude() - 1.0) < 1e-10
        
        # Direction should be preserved
        assert abs(normalized.x - 0.6) < 1e-10
        assert abs(normalized.y - 0.8) < 1e-10
    
    def test_point_magnitude(self):
        """Test point magnitude calculation."""
        p = Point(3.0, 4.0)
        assert p.magnitude() == 5.0
        
        p_zero = Point(0.0, 0.0)
        assert p_zero.magnitude() == 0.0
    
    def test_point_dot_product(self):
        """Test point dot product."""
        p1 = Point(1.0, 2.0)
        p2 = Point(3.0, 4.0)
        
        dot = p1.dot(p2)
        assert dot == 11.0  # 1*3 + 2*4
        
        # Perpendicular points
        p3 = Point(1.0, 0.0)
        p4 = Point(0.0, 1.0)
        assert p3.dot(p4) == 0.0
    
    def test_point_cross_product(self):
        """Test point cross product (2D)."""
        p1 = Point(1.0, 0.0)
        p2 = Point(0.0, 1.0)
        
        cross = p1.cross(p2)
        assert cross == 1.0
        
        # Parallel points
        p3 = Point(2.0, 0.0)
        assert p1.cross(p3) == 0.0
    
    def test_point_angle(self):
        """Test angle calculation between points."""
        p1 = Point(1.0, 0.0)
        p2 = Point(0.0, 1.0)
        
        angle = p1.angle_to(p2)
        assert abs(angle - math.pi/2) < 1e-10
        
        # Same direction
        p3 = Point(2.0, 0.0)
        assert abs(p1.angle_to(p3)) < 1e-10
    
    def test_point_lerp(self):
        """Test linear interpolation."""
        p1 = Point(0.0, 0.0)
        p2 = Point(10.0, 20.0)
        
        # Middle point
        mid = p1.lerp(p2, 0.5)
        assert mid.x == 5.0
        assert mid.y == 10.0
        
        # Start point
        start = p1.lerp(p2, 0.0)
        assert start.x == 0.0
        assert start.y == 0.0
        
        # End point
        end = p1.lerp(p2, 1.0)
        assert end.x == 10.0
        assert end.y == 20.0
    
    def test_point_to_tuple(self):
        """Test point to tuple conversion."""
        p = Point(10.5, 20.7)
        t = p.to_tuple()
        
        assert t == (10.5, 20.7)
        assert isinstance(t, tuple)
    
    def test_point_from_tuple(self):
        """Test point creation from tuple."""
        t = (15.0, 25.0)
        p = Point.from_tuple(t)
        
        assert p.x == 15.0
        assert p.y == 25.0
    
    def test_point_string_representation(self):
        """Test string representation of point."""
        p = Point(10.0, 20.0)
        
        str_repr = str(p)
        assert "Point" in str_repr
        assert "10.0" in str_repr
        assert "20.0" in str_repr


class TestRect:
    """Test Rect class functionality."""
    
    def test_rect_creation(self):
        """Test rectangle creation."""
        r = Rect(10.0, 20.0, 30.0, 40.0)
        assert r.x == 10.0
        assert r.y == 20.0
        assert r.width == 30.0
        assert r.height == 40.0
    
    def test_rect_properties(self):
        """Test rectangle computed properties."""
        r = Rect(10.0, 20.0, 30.0, 40.0)
        
        assert r.left == 10.0
        assert r.right == 40.0
        assert r.top == 20.0
        assert r.bottom == 60.0
        
        center = r.center
        assert center.x == 25.0
        assert center.y == 40.0
        
        # Test corner points
        assert r.top_left.x == 10.0
        assert r.top_left.y == 20.0
        
        assert r.top_right.x == 40.0
        assert r.top_right.y == 20.0
        
        assert r.bottom_left.x == 10.0
        assert r.bottom_left.y == 60.0
        
        assert r.bottom_right.x == 40.0
        assert r.bottom_right.y == 60.0
    
    def test_rect_area(self):
        """Test rectangle area calculation."""
        r = Rect(0.0, 0.0, 10.0, 20.0)
        assert r.area() == 200.0
        
        r_zero = Rect(0.0, 0.0, 0.0, 0.0)
        assert r_zero.area() == 0.0
    
    def test_rect_perimeter(self):
        """Test rectangle perimeter calculation."""
        r = Rect(0.0, 0.0, 10.0, 20.0)
        assert r.perimeter() == 60.0
    
    def test_rect_contains_point(self):
        """Test point containment in rectangle."""
        r = Rect(10.0, 20.0, 30.0, 40.0)
        
        # Inside
        assert r.contains_point(Point(25.0, 40.0))
        assert r.contains_point(Point(10.0, 20.0))  # Edge case
        
        # Outside
        assert not r.contains_point(Point(5.0, 15.0))
        assert not r.contains_point(Point(45.0, 25.0))
    
    def test_rect_contains_rect(self):
        """Test rectangle containment."""
        r1 = Rect(0.0, 0.0, 20.0, 20.0)
        r2 = Rect(5.0, 5.0, 10.0, 10.0)
        r3 = Rect(15.0, 15.0, 10.0, 10.0)
        
        assert r1.contains_rect(r2)
        assert not r1.contains_rect(r3)
    
    def test_rect_intersects(self):
        """Test rectangle intersection."""
        r1 = Rect(0.0, 0.0, 10.0, 10.0)
        r2 = Rect(5.0, 5.0, 10.0, 10.0)
        r3 = Rect(20.0, 20.0, 5.0, 5.0)
        
        assert r1.intersects(r2)
        assert r2.intersects(r1)
        assert not r1.intersects(r3)
    
    def test_rect_intersection(self):
        """Test rectangle intersection calculation."""
        r1 = Rect(0.0, 0.0, 10.0, 10.0)
        r2 = Rect(5.0, 5.0, 10.0, 10.0)
        
        intersection = r1.intersection(r2)
        assert intersection.x == 5.0
        assert intersection.y == 5.0
        assert intersection.width == 5.0
        assert intersection.height == 5.0
        
        # No intersection
        r3 = Rect(20.0, 20.0, 5.0, 5.0)
        no_intersection = r1.intersection(r3)
        assert no_intersection.width == 0.0
        assert no_intersection.height == 0.0
    
    def test_rect_union(self):
        """Test rectangle union calculation."""
        r1 = Rect(0.0, 0.0, 10.0, 10.0)
        r2 = Rect(5.0, 5.0, 10.0, 10.0)
        
        union = r1.union(r2)
        assert union.x == 0.0
        assert union.y == 0.0
        assert union.width == 15.0
        assert union.height == 15.0
    
    def test_rect_expand(self):
        """Test rectangle expansion."""
        r = Rect(10.0, 20.0, 30.0, 40.0)
        expanded = r.expand(5.0)
        
        assert expanded.x == 5.0
        assert expanded.y == 15.0
        assert expanded.width == 40.0
        assert expanded.height == 50.0
    
    def test_rect_scale(self):
        """Test rectangle scaling."""
        r = Rect(10.0, 20.0, 30.0, 40.0)
        scaled = r.scale(2.0)
        
        assert scaled.x == 20.0
        assert scaled.y == 40.0
        assert scaled.width == 60.0
        assert scaled.height == 80.0
    
    def test_rect_translate(self):
        """Test rectangle translation."""
        r = Rect(10.0, 20.0, 30.0, 40.0)
        translated = r.translate(5.0, 10.0)
        
        assert translated.x == 15.0
        assert translated.y == 30.0
        assert translated.width == 30.0
        assert translated.height == 40.0
    
    def test_rect_is_empty(self):
        """Test empty rectangle detection."""
        r1 = Rect(0.0, 0.0, 0.0, 0.0)
        assert r1.is_empty()
        
        r2 = Rect(0.0, 0.0, 10.0, 0.0)
        assert r2.is_empty()
        
        r3 = Rect(0.0, 0.0, 10.0, 10.0)
        assert not r3.is_empty()
    
    def test_rect_from_points(self):
        """Test rectangle creation from points."""
        points = [Point(0.0, 0.0), Point(10.0, 5.0), Point(-5.0, 15.0)]
        r = Rect.from_points(points)
        
        assert r.x == -5.0
        assert r.y == 0.0
        assert r.width == 15.0
        assert r.height == 15.0
    
    def test_rect_from_center_size(self):
        """Test rectangle creation from center and size."""
        center = Point(10.0, 20.0)
        size = Size(30.0, 40.0)
        r = Rect.from_center_size(center, size)
        
        assert r.x == -5.0  # 10 - 30/2
        assert r.y == 0.0   # 20 - 40/2
        assert r.width == 30.0
        assert r.height == 40.0


class TestSize:
    """Test Size class functionality."""
    
    def test_size_creation(self):
        """Test size creation."""
        s = Size(100.0, 200.0)
        assert s.width == 100.0
        assert s.height == 200.0
    
    def test_size_area(self):
        """Test size area calculation."""
        s = Size(10.0, 20.0)
        assert s.area() == 200.0
        
        s_zero = Size(0.0, 0.0)
        assert s_zero.area() == 0.0
    
    def test_size_aspect_ratio(self):
        """Test aspect ratio calculation."""
        s = Size(16.0, 9.0)
        assert abs(s.aspect_ratio() - 16.0/9.0) < 1e-10
        
        s_square = Size(10.0, 10.0)
        assert s_square.aspect_ratio() == 1.0
    
    def test_size_scale(self):
        """Test size scaling."""
        s = Size(10.0, 20.0)
        scaled = s.scale(2.0)
        
        assert scaled.width == 20.0
        assert scaled.height == 40.0
        
        # Scale by different factors
        scaled_xy = s.scale_xy(2.0, 3.0)
        assert scaled_xy.width == 20.0
        assert scaled_xy.height == 60.0
    
    def test_size_fits_in(self):
        """Test size fitting calculations."""
        s1 = Size(10.0, 20.0)
        s2 = Size(30.0, 40.0)
        
        assert s1.fits_in(s2)
        assert not s2.fits_in(s1)
    
    def test_size_fit_within(self):
        """Test size fitting with scaling."""
        s1 = Size(100.0, 200.0)
        s2 = Size(50.0, 100.0)
        
        scaled = s1.fit_within(s2)
        assert scaled.width <= s2.width
        assert scaled.height <= s2.height
    
    def test_size_is_empty(self):
        """Test empty size detection."""
        s1 = Size(0.0, 0.0)
        assert s1.is_empty()
        
        s2 = Size(10.0, 0.0)
        assert s2.is_empty()
        
        s3 = Size(10.0, 10.0)
        assert not s3.is_empty()


class TestGeometryUtils:
    """Test GeometryUtils class functionality."""
    
    def test_geometry_utils_point_distance(self):
        """Test point distance calculation."""
        p1 = Point(0.0, 0.0)
        p2 = Point(3.0, 4.0)
        
        distance = GeometryUtils.point_distance(p1, p2)
        assert distance == 5.0
    
    def test_geometry_utils_point_in_rect(self):
        """Test point in rectangle check."""
        point = Point(5.0, 10.0)
        rect = Rect(0.0, 0.0, 10.0, 20.0)
        
        assert GeometryUtils.point_in_rect(point, rect)
        
        point_outside = Point(15.0, 10.0)
        assert not GeometryUtils.point_in_rect(point_outside, rect)
    
    def test_geometry_utils_rect_intersection(self):
        """Test rectangle intersection calculation."""
        r1 = Rect(0.0, 0.0, 10.0, 10.0)
        r2 = Rect(5.0, 5.0, 10.0, 10.0)
        
        intersection = GeometryUtils.rect_intersection(r1, r2)
        assert intersection.x == 5.0
        assert intersection.y == 5.0
        assert intersection.width == 5.0
        assert intersection.height == 5.0
    
    def test_geometry_utils_rect_union(self):
        """Test rectangle union calculation."""
        r1 = Rect(0.0, 0.0, 10.0, 10.0)
        r2 = Rect(5.0, 5.0, 10.0, 10.0)
        
        union = GeometryUtils.rect_union(r1, r2)
        assert union.x == 0.0
        assert union.y == 0.0
        assert union.width == 15.0
        assert union.height == 15.0
    
    def test_geometry_utils_line_intersection(self):
        """Test line intersection calculation."""
        # Two perpendicular lines intersecting at (5, 5)
        line1_start = Point(0.0, 5.0)
        line1_end = Point(10.0, 5.0)
        line2_start = Point(5.0, 0.0)
        line2_end = Point(5.0, 10.0)
        
        intersection = GeometryUtils.line_intersection(
            line1_start, line1_end, line2_start, line2_end
        )
        
        assert intersection is not None
        assert abs(intersection.x - 5.0) < 1e-10
        assert abs(intersection.y - 5.0) < 1e-10
    
    def test_geometry_utils_polygon_area(self):
        """Test polygon area calculation."""
        # Simple square
        points = [Point(0.0, 0.0), Point(10.0, 0.0), Point(10.0, 10.0), Point(0.0, 10.0)]
        area = GeometryUtils.polygon_area(points)
        assert abs(area - 100.0) < 1e-10
        
        # Triangle
        triangle = [Point(0.0, 0.0), Point(10.0, 0.0), Point(5.0, 10.0)]
        area = GeometryUtils.polygon_area(triangle)
        assert abs(area - 50.0) < 1e-10
    
    def test_geometry_utils_closest_point_on_line(self):
        """Test closest point on line calculation."""
        line_start = Point(0.0, 0.0)
        line_end = Point(10.0, 0.0)
        point = Point(5.0, 5.0)
        
        closest = GeometryUtils.closest_point_on_line(point, line_start, line_end)
        assert abs(closest.x - 5.0) < 1e-10
        assert abs(closest.y - 0.0) < 1e-10
    
    def test_geometry_utils_angle_between_vectors(self):
        """Test angle between vectors calculation."""
        v1 = Point(1.0, 0.0)
        v2 = Point(0.0, 1.0)
        
        angle = GeometryUtils.angle_between_vectors(v1, v2)
        assert abs(angle - math.pi/2) < 1e-10
    
    def test_geometry_utils_rotate_point(self):
        """Test point rotation."""
        point = Point(1.0, 0.0)
        rotated = GeometryUtils.rotate_point(point, math.pi/2)
        
        assert abs(rotated.x) < 1e-10
        assert abs(rotated.y - 1.0) < 1e-10
    
    def test_geometry_utils_lerp(self):
        """Test linear interpolation."""
        result = GeometryUtils.lerp(0.0, 10.0, 0.5)
        assert result == 5.0
        
        result = GeometryUtils.lerp(0.0, 10.0, 0.0)
        assert result == 0.0
        
        result = GeometryUtils.lerp(0.0, 10.0, 1.0)
        assert result == 10.0
    
    def test_geometry_utils_clamp(self):
        """Test value clamping."""
        assert GeometryUtils.clamp(5.0, 0.0, 10.0) == 5.0
        assert GeometryUtils.clamp(-5.0, 0.0, 10.0) == 0.0
        assert GeometryUtils.clamp(15.0, 0.0, 10.0) == 10.0


class TestGeometryIntegration:
    """Test integration between geometry classes."""
    
    def test_complex_geometry_operations(self):
        """Test complex operations involving multiple geometry classes."""
        # Create a set of points
        points = [Point(0.0, 0.0), Point(10.0, 0.0), Point(10.0, 10.0), Point(0.0, 10.0)]
        
        # Create rectangle from points
        rect = Rect.from_points(points)
        
        # Test that all points are contained or on boundary
        for point in points:
            assert rect.contains_point(point)
        
        # Test center calculation
        center = rect.center
        assert center.x == 5.0
        assert center.y == 5.0
        
        # Test distance from center to corner
        corner = rect.top_right
        distance = center.distance_to(corner)
        assert abs(distance - math.sqrt(50)) < 1e-10
    
    def test_performance_critical_operations(self):
        """Test performance-critical operations."""
        # Create many points
        points = [Point(i * 0.1, i * 0.1) for i in range(1000)]
        
        # Test rectangle creation (should be fast)
        rect = Rect.from_points(points)
        
        # Test that it's correct
        assert rect.x == 0.0
        assert rect.y == 0.0
        assert rect.width == 99.9
        assert rect.height == 99.9
    
    def test_numerical_precision(self):
        """Test numerical precision in calculations."""
        # Test with very small numbers
        p1 = Point(1e-10, 1e-10)
        p2 = Point(2e-10, 2e-10)
        
        distance = p1.distance_to(p2)
        assert distance > 0.0
        
        # Test with very large numbers
        p3 = Point(1e10, 1e10)
        p4 = Point(2e10, 2e10)
        
        distance_large = p3.distance_to(p4)
        assert distance_large > 0.0
    
    def test_coordinate_transformation_compatibility(self):
        """Test compatibility with coordinate transformation system."""
        # Test that geometry classes work well with transformation matrices
        rect = Rect(0.0, 0.0, 100.0, 100.0)
        
        # Test center point
        center = rect.center
        assert center.x == 50.0
        assert center.y == 50.0
        
        # Test that rectangle methods work correctly
        assert rect.area() == 10000.0
        assert rect.perimeter() == 400.0
        
        # Test point containment
        assert rect.contains_point(center)
        assert not rect.contains_point(Point(150.0, 150.0))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])