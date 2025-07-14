"""
Coordinate Transformation System for Document Viewer Overlay.
This module provides accurate coordinate transformation between document space
and screen space, handling zoom, pan, and rotation transformations.
"""
from __future__ import annotations

import math
from typing import Tuple, Union
from dataclasses import dataclass

import numpy as np


@dataclass
class Point:
    """2D point representation."""
    x: float
    y: float
    
    def __add__(self, other: Union[Point, Tuple[float, float]]) -> Point:
        if isinstance(other, Point):
            return Point(self.x + other.x, self.y + other.y)
        return Point(self.x + other[0], self.y + other[1])
    
    def __sub__(self, other: Union[Point, Tuple[float, float]]) -> Point:
        if isinstance(other, Point):
            return Point(self.x - other.x, self.y - other.y)
        return Point(self.x - other[0], self.y - other[1])
    
    def __mul__(self, scalar: float) -> Point:
        return Point(self.x * scalar, self.y * scalar)
    
    def __truediv__(self, scalar: float) -> Point:
        return Point(self.x / scalar, self.y / scalar)
    
    def distance_to(self, other: Point) -> float:
        """Calculate distance to another point."""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
    
    def to_numpy(self) -> np.ndarray:
        """Convert to numpy array."""
        return np.array([self.x, self.y])
    
    @classmethod
    def from_numpy(cls, array: np.ndarray) -> Point:
        """Create point from numpy array."""
        return cls(array[0], array[1])


@dataclass
class Rectangle:
    """Rectangle representation."""
    x: float
    y: float
    width: float
    height: float
    
    @property
    def left(self) -> float:
        return self.x
    
    @property
    def right(self) -> float:
        return self.x + self.width
    
    @property
    def top(self) -> float:
        return self.y
    
    @property
    def bottom(self) -> float:
        return self.y + self.height
    
    @property
    def center(self) -> Point:
        return Point(self.x + self.width / 2, self.y + self.height / 2)
    
    @property
    def top_left(self) -> Point:
        return Point(self.x, self.y)
    
    @property
    def top_right(self) -> Point:
        return Point(self.x + self.width, self.y)
    
    @property
    def bottom_left(self) -> Point:
        return Point(self.x, self.y + self.height)
    
    @property
    def bottom_right(self) -> Point:
        return Point(self.x + self.width, self.y + self.height)
    
    def contains(self, point: Point) -> bool:
        """Check if rectangle contains a point."""
        return (self.x <= point.x <= self.x + self.width and
                self.y <= point.y <= self.y + self.height)
    
    def intersects(self, other: Rectangle) -> bool:
        """Check if this rectangle intersects with another."""
        return not (self.right < other.left or
                   self.left > other.right or
                   self.bottom < other.top or
                   self.top > other.bottom)
    
    def intersection(self, other: Rectangle) -> Rectangle:
        """Get intersection rectangle with another rectangle."""
        left = max(self.left, other.left)
        right = min(self.right, other.right)
        top = max(self.top, other.top)
        bottom = min(self.bottom, other.bottom)
        
        if left < right and top < bottom:
            return Rectangle(left, top, right - left, bottom - top)
        return Rectangle(0, 0, 0, 0)  # No intersection
    
    def union(self, other: Rectangle) -> Rectangle:
        """Get union rectangle with another rectangle."""
        left = min(self.left, other.left)
        right = max(self.right, other.right)
        top = min(self.top, other.top)
        bottom = max(self.bottom, other.bottom)
        
        return Rectangle(left, top, right - left, bottom - top)
    
    def expand(self, amount: float) -> Rectangle:
        """Expand rectangle by given amount."""
        return Rectangle(
            self.x - amount,
            self.y - amount,
            self.width + 2 * amount,
            self.height + 2 * amount
        )
    
    def scale(self, factor: float) -> Rectangle:
        """Scale rectangle by given factor."""
        return Rectangle(
            self.x * factor,
            self.y * factor,
            self.width * factor,
            self.height * factor
        )


class CoordinateTransform:
    """
    Coordinate transformation system for document viewer overlay.
    
    Handles transformations between document coordinate space and screen coordinate space,
    including zoom, pan, and rotation transformations with high accuracy.
    """
    
    def __init__(self, document_bounds: Rectangle, viewport_bounds: Rectangle, zoom_level: float = 1.0):
        self.document_bounds = document_bounds
        self.viewport_bounds = viewport_bounds
        self.zoom_level = zoom_level
        self.rotation_angle = 0.0  # Radians
        self.pan_offset = Point(0, 0)
        
        # Calculate transformation matrices
        self._update_transform_matrices()
    
    def _update_transform_matrices(self) -> None:
        """Update the transformation matrices."""
        # Translation to center document in viewport
        doc_center = self.document_bounds.center
        viewport_center = self.viewport_bounds.center
        
        # Create transformation matrix (document to screen)
        # Order: translate to origin, scale, rotate, translate to viewport center
        self.doc_to_screen_matrix = np.eye(3)
        
        # 1. Translate document center to origin
        translate_to_origin = np.array([
            [1, 0, -doc_center.x],
            [0, 1, -doc_center.y],
            [0, 0, 1]
        ])
        
        # 2. Scale (zoom)
        scale_matrix = np.array([
            [self.zoom_level, 0, 0],
            [0, self.zoom_level, 0],
            [0, 0, 1]
        ])
        
        # 3. Rotate
        cos_angle = math.cos(self.rotation_angle)
        sin_angle = math.sin(self.rotation_angle)
        rotation_matrix = np.array([
            [cos_angle, -sin_angle, 0],
            [sin_angle, cos_angle, 0],
            [0, 0, 1]
        ])
        
        # 4. Translate to viewport center with pan offset
        translate_to_viewport = np.array([
            [1, 0, viewport_center.x + self.pan_offset.x],
            [0, 1, viewport_center.y + self.pan_offset.y],
            [0, 0, 1]
        ])
        
        # Combine transformations
        self.doc_to_screen_matrix = (translate_to_viewport @ 
                                   rotation_matrix @ 
                                   scale_matrix @ 
                                   translate_to_origin)
        
        # Create inverse transformation matrix (screen to document)
        self.screen_to_doc_matrix = np.linalg.inv(self.doc_to_screen_matrix)
    
    def update_viewport(self, viewport_bounds: Rectangle, zoom_level: float) -> None:
        """Update viewport bounds and zoom level."""
        self.viewport_bounds = viewport_bounds
        self.zoom_level = zoom_level
        self._update_transform_matrices()
    
    def update_document_bounds(self, document_bounds: Rectangle) -> None:
        """Update document bounds."""
        self.document_bounds = document_bounds
        self._update_transform_matrices()
    
    def set_zoom_level(self, zoom_level: float) -> None:
        """Set zoom level."""
        self.zoom_level = max(0.01, zoom_level)  # Prevent division by zero
        self._update_transform_matrices()
    
    def set_rotation(self, angle_radians: float) -> None:
        """Set rotation angle in radians."""
        self.rotation_angle = angle_radians
        self._update_transform_matrices()
    
    def set_pan_offset(self, offset: Point) -> None:
        """Set pan offset."""
        self.pan_offset = offset
        self._update_transform_matrices()
    
    def document_to_screen(self, point: Point) -> Point:
        """Transform document coordinates to screen coordinates."""
        # Convert point to homogeneous coordinates
        doc_point = np.array([point.x, point.y, 1])
        
        # Apply transformation
        screen_point = self.doc_to_screen_matrix @ doc_point
        
        return Point(screen_point[0], screen_point[1])
    
    def screen_to_document(self, point: Point) -> Point:
        """Transform screen coordinates to document coordinates."""
        # Convert point to homogeneous coordinates
        screen_point = np.array([point.x, point.y, 1])
        
        # Apply inverse transformation
        doc_point = self.screen_to_doc_matrix @ screen_point
        
        return Point(doc_point[0], doc_point[1])
    
    def transform_bounds(self, bounds: Rectangle) -> Rectangle:
        """Transform document bounds to screen bounds."""
        # Transform all four corners
        corners = [
            self.document_to_screen(bounds.top_left),
            self.document_to_screen(bounds.top_right),
            self.document_to_screen(bounds.bottom_left),
            self.document_to_screen(bounds.bottom_right)
        ]
        
        # Find bounding box of transformed corners
        min_x = min(corner.x for corner in corners)
        max_x = max(corner.x for corner in corners)
        min_y = min(corner.y for corner in corners)
        max_y = max(corner.y for corner in corners)
        
        return Rectangle(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def inverse_transform_bounds(self, bounds: Rectangle) -> Rectangle:
        """Transform screen bounds to document bounds."""
        # Transform all four corners
        corners = [
            self.screen_to_document(bounds.top_left),
            self.screen_to_document(bounds.top_right),
            self.screen_to_document(bounds.bottom_left),
            self.screen_to_document(bounds.bottom_right)
        ]
        
        # Find bounding box of transformed corners
        min_x = min(corner.x for corner in corners)
        max_x = max(corner.x for corner in corners)
        min_y = min(corner.y for corner in corners)
        max_y = max(corner.y for corner in corners)
        
        return Rectangle(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def get_visible_document_bounds(self) -> Rectangle:
        """Get the document bounds that are visible in the current viewport."""
        return self.inverse_transform_bounds(self.viewport_bounds)
    
    def get_scale_factor(self) -> float:
        """Get the current scale factor."""
        return self.zoom_level
    
    def get_rotation_angle(self) -> float:
        """Get the current rotation angle in radians."""
        return self.rotation_angle
    
    def get_pan_offset(self) -> Point:
        """Get the current pan offset."""
        return self.pan_offset
    
    def is_point_in_viewport(self, doc_point: Point) -> bool:
        """Check if a document point is visible in the viewport."""
        screen_point = self.document_to_screen(doc_point)
        return self.viewport_bounds.contains(screen_point)
    
    def is_bounds_in_viewport(self, doc_bounds: Rectangle) -> bool:
        """Check if document bounds intersect with the viewport."""
        screen_bounds = self.transform_bounds(doc_bounds)
        return self.viewport_bounds.intersects(screen_bounds)
    
    def get_pixel_size_in_document(self) -> float:
        """Get the size of one pixel in document coordinates."""
        return 1.0 / self.zoom_level
    
    def snap_to_pixel(self, point: Point) -> Point:
        """Snap a screen point to pixel boundaries."""
        return Point(round(point.x), round(point.y))
    
    def validate_transformation(self) -> bool:
        """Validate that transformation matrices are valid."""
        try:
            # Check if matrices are valid
            if np.any(np.isnan(self.doc_to_screen_matrix)) or np.any(np.isinf(self.doc_to_screen_matrix)):
                return False
            
            if np.any(np.isnan(self.screen_to_doc_matrix)) or np.any(np.isinf(self.screen_to_doc_matrix)):
                return False
            
            # Check if inverse transformation is consistent
            test_point = Point(100, 100)
            transformed = self.document_to_screen(test_point)
            inverse_transformed = self.screen_to_document(transformed)
            
            # Allow small floating point errors
            tolerance = 1e-10
            return (abs(test_point.x - inverse_transformed.x) < tolerance and
                   abs(test_point.y - inverse_transformed.y) < tolerance)
        
        except Exception:
            return False


class CoordinateValidator:
    """Utility class for validating coordinate transformations."""
    
    @staticmethod
    def validate_point(point: Point) -> bool:
        """Validate that a point has valid coordinates."""
        return (not math.isnan(point.x) and not math.isnan(point.y) and
                not math.isinf(point.x) and not math.isinf(point.y))
    
    @staticmethod
    def validate_rectangle(rect: Rectangle) -> bool:
        """Validate that a rectangle has valid dimensions."""
        return (not math.isnan(rect.x) and not math.isnan(rect.y) and
                not math.isnan(rect.width) and not math.isnan(rect.height) and
                not math.isinf(rect.x) and not math.isinf(rect.y) and
                not math.isinf(rect.width) and not math.isinf(rect.height) and
                rect.width >= 0 and rect.height >= 0)
    
    @staticmethod
    def validate_zoom_level(zoom_level: float) -> bool:
        """Validate that zoom level is valid."""
        return (not math.isnan(zoom_level) and not math.isinf(zoom_level) and
                zoom_level > 0)
    
    @staticmethod
    def clamp_to_bounds(point: Point, bounds: Rectangle) -> Point:
        """Clamp a point to within given bounds."""
        return Point(
            max(bounds.left, min(bounds.right, point.x)),
            max(bounds.top, min(bounds.bottom, point.y))
        )


class CoordinateConverter:
    """Utility class for coordinate conversions."""
    
    @staticmethod
    def qt_point_to_point(qt_point) -> Point:
        """Convert Qt QPoint/QPointF to Point."""
        return Point(qt_point.x(), qt_point.y())
    
    @staticmethod
    def point_to_qt_point(point: Point):
        """Convert Point to Qt QPointF."""
        from PyQt6.QtCore import QPointF
        return QPointF(point.x, point.y)
    
    @staticmethod
    def qt_rect_to_rectangle(qt_rect) -> Rectangle:
        """Convert Qt QRect/QRectF to Rectangle."""
        return Rectangle(qt_rect.x(), qt_rect.y(), qt_rect.width(), qt_rect.height())
    
    @staticmethod
    def rectangle_to_qt_rect(rect: Rectangle):
        """Convert Rectangle to Qt QRectF."""
        from PyQt6.QtCore import QRectF
        return QRectF(rect.x, rect.y, rect.width, rect.height)
    
    @staticmethod
    def degrees_to_radians(degrees: float) -> float:
        """Convert degrees to radians."""
        return degrees * math.pi / 180.0
    
    @staticmethod
    def radians_to_degrees(radians: float) -> float:
        """Convert radians to degrees."""
        return radians * 180.0 / math.pi