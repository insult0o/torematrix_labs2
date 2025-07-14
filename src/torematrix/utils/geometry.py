"""
Geometric utilities for coordinate transformations.

This module provides fundamental geometric data structures and utilities
for 2D coordinate operations in the document viewer.
"""

from typing import Tuple, Optional, List, Union
from dataclasses import dataclass
import math


@dataclass
class Point:
    """2D point with utility methods."""
    x: float
    y: float
    
    def distance_to(self, other: 'Point') -> float:
        """Calculate distance to another point."""
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)
    
    def midpoint(self, other: 'Point') -> 'Point':
        """Calculate midpoint with another point."""
        return Point(
            (self.x + other.x) / 2.0,
            (self.y + other.y) / 2.0
        )
    
    def rotate(self, angle: float, center: Optional['Point'] = None) -> 'Point':
        """Rotate point around center."""
        if center is None:
            center = Point(0, 0)
        
        # Translate to origin
        x = self.x - center.x
        y = self.y - center.y
        
        # Rotate
        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)
        
        rotated_x = x * cos_angle - y * sin_angle
        rotated_y = x * sin_angle + y * cos_angle
        
        # Translate back
        return Point(
            rotated_x + center.x,
            rotated_y + center.y
        )
    
    def scale(self, factor: float, center: Optional['Point'] = None) -> 'Point':
        """Scale point from center."""
        if center is None:
            center = Point(0, 0)
        
        # Translate to origin
        x = self.x - center.x
        y = self.y - center.y
        
        # Scale
        scaled_x = x * factor
        scaled_y = y * factor
        
        # Translate back
        return Point(
            scaled_x + center.x,
            scaled_y + center.y
        )
    
    def to_tuple(self) -> Tuple[float, float]:
        """Convert to tuple."""
        return (self.x, self.y)
    
    def __add__(self, other: 'Point') -> 'Point':
        """Add two points."""
        return Point(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: 'Point') -> 'Point':
        """Subtract two points."""
        return Point(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float) -> 'Point':
        """Multiply point by scalar."""
        return Point(self.x * scalar, self.y * scalar)
    
    def __truediv__(self, scalar: float) -> 'Point':
        """Divide point by scalar."""
        return Point(self.x / scalar, self.y / scalar)
    
    def __abs__(self) -> float:
        """Get magnitude (distance from origin)."""
        return math.sqrt(self.x * self.x + self.y * self.y)
    
    def normalized(self) -> 'Point':
        """Get normalized point (unit vector)."""
        magnitude = abs(self)
        if magnitude == 0:
            return Point(0, 0)
        return self / magnitude


@dataclass
class Rect:
    """2D rectangle with utility methods."""
    x: float
    y: float
    width: float
    height: float
    
    @property
    def center(self) -> Point:
        """Get rectangle center."""
        return Point(
            self.x + self.width / 2.0,
            self.y + self.height / 2.0
        )
    
    @property
    def top_left(self) -> Point:
        """Get top-left corner."""
        return Point(self.x, self.y)
    
    @property
    def top_right(self) -> Point:
        """Get top-right corner."""
        return Point(self.x + self.width, self.y)
    
    @property
    def bottom_left(self) -> Point:
        """Get bottom-left corner."""
        return Point(self.x, self.y + self.height)
    
    @property
    def bottom_right(self) -> Point:
        """Get bottom-right corner."""
        return Point(self.x + self.width, self.y + self.height)
    
    @property
    def area(self) -> float:
        """Get rectangle area."""
        return self.width * self.height
    
    @property
    def perimeter(self) -> float:
        """Get rectangle perimeter."""
        return 2 * (self.width + self.height)
    
    def contains(self, point: Point) -> bool:
        """Check if point is inside rectangle."""
        return (self.x <= point.x <= self.x + self.width and
                self.y <= point.y <= self.y + self.height)
    
    def intersects(self, other: 'Rect') -> bool:
        """Check if rectangles intersect."""
        return not (self.x + self.width < other.x or
                   other.x + other.width < self.x or
                   self.y + self.height < other.y or
                   other.y + other.height < self.y)
    
    def intersection(self, other: 'Rect') -> Optional['Rect']:
        """Get intersection rectangle."""
        if not self.intersects(other):
            return None
        
        left = max(self.x, other.x)
        top = max(self.y, other.y)
        right = min(self.x + self.width, other.x + other.width)
        bottom = min(self.y + self.height, other.y + other.height)
        
        return Rect(left, top, right - left, bottom - top)
    
    def union(self, other: 'Rect') -> 'Rect':
        """Get union rectangle."""
        left = min(self.x, other.x)
        top = min(self.y, other.y)
        right = max(self.x + self.width, other.x + other.width)
        bottom = max(self.y + self.height, other.y + other.height)
        
        return Rect(left, top, right - left, bottom - top)
    
    def expanded(self, margin: float) -> 'Rect':
        """Get expanded rectangle with margin."""
        return Rect(
            self.x - margin,
            self.y - margin,
            self.width + 2 * margin,
            self.height + 2 * margin
        )
    
    def scaled(self, factor: float, center: Optional[Point] = None) -> 'Rect':
        """Get scaled rectangle."""
        if center is None:
            center = self.center
        
        new_width = self.width * factor
        new_height = self.height * factor
        
        return Rect(
            center.x - new_width / 2.0,
            center.y - new_height / 2.0,
            new_width,
            new_height
        )
    
    def translated(self, offset: Point) -> 'Rect':
        """Get translated rectangle."""
        return Rect(
            self.x + offset.x,
            self.y + offset.y,
            self.width,
            self.height
        )


@dataclass
class Size:
    """2D size with utility methods."""
    width: float
    height: float
    
    def scale(self, factor: float) -> 'Size':
        """Scale size by factor."""
        return Size(self.width * factor, self.height * factor)
    
    def scale_to_fit(self, container: 'Size') -> 'Size':
        """Scale size to fit within container while maintaining aspect ratio."""
        scale_x = container.width / self.width
        scale_y = container.height / self.height
        scale = min(scale_x, scale_y)
        
        return Size(self.width * scale, self.height * scale)
    
    def scale_to_fill(self, container: 'Size') -> 'Size':
        """Scale size to fill container while maintaining aspect ratio."""
        scale_x = container.width / self.width
        scale_y = container.height / self.height
        scale = max(scale_x, scale_y)
        
        return Size(self.width * scale, self.height * scale)
    
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio."""
        return self.width / self.height if self.height != 0 else 0
    
    def is_empty(self) -> bool:
        """Check if size is empty."""
        return self.width <= 0 or self.height <= 0
    
    def is_valid(self) -> bool:
        """Check if size is valid."""
        return self.width > 0 and self.height > 0
    
    def __add__(self, other: 'Size') -> 'Size':
        """Add two sizes."""
        return Size(self.width + other.width, self.height + other.height)
    
    def __sub__(self, other: 'Size') -> 'Size':
        """Subtract two sizes."""
        return Size(self.width - other.width, self.height - other.height)
    
    def __mul__(self, scalar: float) -> 'Size':
        """Multiply size by scalar."""
        return Size(self.width * scalar, self.height * scalar)
    
    def __truediv__(self, scalar: float) -> 'Size':
        """Divide size by scalar."""
        return Size(self.width / scalar, self.height / scalar)


class GeometryUtils:
    """Utility functions for geometric operations."""
    
    @staticmethod
    def angle_between_points(p1: Point, p2: Point) -> float:
        """Calculate angle between two points."""
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        return math.atan2(dy, dx)
    
    @staticmethod
    def point_in_polygon(point: Point, polygon: List[Point]) -> bool:
        """Check if point is inside polygon using ray casting."""
        if len(polygon) < 3:
            return False
        
        x, y = point.x, point.y
        n = len(polygon)
        inside = False
        
        p1x, p1y = polygon[0].x, polygon[0].y
        for i in range(1, n + 1):
            p2x, p2y = polygon[i % n].x, polygon[i % n].y
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y
        
        return inside
    
    @staticmethod
    def line_intersection(p1: Point, p2: Point, p3: Point, p4: Point) -> Optional[Point]:
        """Find intersection of two lines."""
        x1, y1 = p1.x, p1.y
        x2, y2 = p2.x, p2.y
        x3, y3 = p3.x, p3.y
        x4, y4 = p4.x, p4.y
        
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-10:
            return None  # Lines are parallel
        
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        
        return Point(
            x1 + t * (x2 - x1),
            y1 + t * (y2 - y1)
        )
    
    @staticmethod
    def distance_point_to_line(point: Point, line_start: Point, line_end: Point) -> float:
        """Calculate distance from point to line segment."""
        # Vector from line_start to line_end
        line_vec = line_end - line_start
        
        # Vector from line_start to point
        point_vec = point - line_start
        
        # Project point onto line
        line_len_sq = line_vec.x * line_vec.x + line_vec.y * line_vec.y
        if line_len_sq == 0:
            return point.distance_to(line_start)
        
        t = max(0, min(1, (point_vec.x * line_vec.x + point_vec.y * line_vec.y) / line_len_sq))
        
        # Find closest point on line
        closest = line_start + line_vec * t
        
        return point.distance_to(closest)
    
    @staticmethod
    def normalize_angle(angle: float) -> float:
        """Normalize angle to [-π, π]."""
        while angle > math.pi:
            angle -= 2 * math.pi
        while angle < -math.pi:
            angle += 2 * math.pi
        return angle
    
    @staticmethod
    def angle_difference(angle1: float, angle2: float) -> float:
        """Calculate the smallest difference between two angles."""
        diff = angle2 - angle1
        return GeometryUtils.normalize_angle(diff)
    
    @staticmethod
    def clamp(value: float, min_val: float, max_val: float) -> float:
        """Clamp value between min and max."""
        return max(min_val, min(max_val, value))
    
    @staticmethod
    def lerp(start: float, end: float, t: float) -> float:
        """Linear interpolation between start and end."""
        return start + t * (end - start)
    
    @staticmethod
    def point_lerp(start: Point, end: Point, t: float) -> Point:
        """Linear interpolation between two points."""
        return Point(
            GeometryUtils.lerp(start.x, end.x, t),
            GeometryUtils.lerp(start.y, end.y, t)
        )
    
    @staticmethod
    def rect_lerp(start: Rect, end: Rect, t: float) -> Rect:
        """Linear interpolation between two rectangles."""
        return Rect(
            GeometryUtils.lerp(start.x, end.x, t),
            GeometryUtils.lerp(start.y, end.y, t),
            GeometryUtils.lerp(start.width, end.width, t),
            GeometryUtils.lerp(start.height, end.height, t)
        )
    
    @staticmethod
    def is_point_near_line(point: Point, line_start: Point, line_end: Point, tolerance: float = 1.0) -> bool:
        """Check if point is near a line within tolerance."""
        return GeometryUtils.distance_point_to_line(point, line_start, line_end) <= tolerance
    
    @staticmethod
    def bounding_box(points: List[Point]) -> Optional[Rect]:
        """Calculate bounding box for a list of points."""
        if not points:
            return None
        
        min_x = min(p.x for p in points)
        max_x = max(p.x for p in points)
        min_y = min(p.y for p in points)
        max_y = max(p.y for p in points)
        
        return Rect(min_x, min_y, max_x - min_x, max_y - min_y)