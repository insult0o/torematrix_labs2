"""
Affine transformation system for coordinate mapping.

This module provides high-performance affine transformation matrices
for document viewer coordinate operations.
"""

from typing import Tuple, Optional, List
import numpy as np
from dataclasses import dataclass
import math

try:
    from PyQt6.QtGui import QTransform
    QT_AVAILABLE = True
except ImportError:
    QT_AVAILABLE = False

from ...utils.geometry import Point, Rect, Size


@dataclass
class TransformationMatrix:
    """Immutable 3x3 transformation matrix."""
    matrix: np.ndarray
    
    def __post_init__(self):
        """Validate matrix dimensions."""
        if not isinstance(self.matrix, np.ndarray):
            self.matrix = np.array(self.matrix)
        
        assert self.matrix.shape == (3, 3), f"Matrix must be 3x3, got {self.matrix.shape}"
        
        # Ensure matrix is float64 for precision
        self.matrix = self.matrix.astype(np.float64)
    
    @classmethod
    def identity(cls) -> 'TransformationMatrix':
        """Create identity transformation matrix."""
        return cls(np.eye(3, dtype=np.float64))
    
    @classmethod
    def translation(cls, dx: float, dy: float) -> 'TransformationMatrix':
        """Create translation transformation matrix."""
        matrix = np.eye(3, dtype=np.float64)
        matrix[0, 2] = dx
        matrix[1, 2] = dy
        return cls(matrix)
    
    @classmethod
    def scaling(cls, sx: float, sy: float) -> 'TransformationMatrix':
        """Create scaling transformation matrix."""
        matrix = np.eye(3, dtype=np.float64)
        matrix[0, 0] = sx
        matrix[1, 1] = sy
        return cls(matrix)
    
    @classmethod
    def rotation(cls, angle: float) -> 'TransformationMatrix':
        """Create rotation transformation matrix."""
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        matrix = np.array([
            [cos_a, -sin_a, 0.0],
            [sin_a,  cos_a, 0.0],
            [0.0,    0.0,   1.0]
        ], dtype=np.float64)
        
        return cls(matrix)
    
    @classmethod
    def shearing(cls, shx: float, shy: float) -> 'TransformationMatrix':
        """Create shearing transformation matrix."""
        matrix = np.array([
            [1.0, shx, 0.0],
            [shy, 1.0, 0.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)
        
        return cls(matrix)
    
    def apply(self, point: Tuple[float, float]) -> Tuple[float, float]:
        """Apply transformation to a point."""
        # Convert to homogeneous coordinates
        homogeneous = np.array([point[0], point[1], 1.0], dtype=np.float64)
        
        # Apply transformation
        result = self.matrix @ homogeneous
        
        # Convert back to 2D coordinates
        return (result[0], result[1])
    
    def apply_to_points(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Apply transformation to multiple points efficiently."""
        if not points:
            return []
        
        # Convert to homogeneous coordinates (Nx3 matrix)
        homogeneous = np.array([[p[0], p[1], 1.0] for p in points], dtype=np.float64)
        
        # Apply transformation (3x3 @ 3xN = 3xN)
        result = (self.matrix @ homogeneous.T).T
        
        # Convert back to 2D coordinates
        return [(result[i, 0], result[i, 1]) for i in range(len(points))]
    
    def compose(self, other: 'TransformationMatrix') -> 'TransformationMatrix':
        """Compose with another transformation (self * other)."""
        result_matrix = self.matrix @ other.matrix
        return TransformationMatrix(result_matrix)
    
    def inverse(self) -> 'TransformationMatrix':
        """Get inverse transformation."""
        try:
            inv_matrix = np.linalg.inv(self.matrix)
            return TransformationMatrix(inv_matrix)
        except np.linalg.LinAlgError:
            raise ValueError("Matrix is not invertible")
    
    def determinant(self) -> float:
        """Get transformation determinant."""
        return np.linalg.det(self.matrix)
    
    def is_invertible(self) -> bool:
        """Check if transformation is invertible."""
        return abs(self.determinant()) > 1e-10
    
    def is_identity(self, tolerance: float = 1e-10) -> bool:
        """Check if transformation is identity."""
        identity = np.eye(3, dtype=np.float64)
        return np.allclose(self.matrix, identity, atol=tolerance)
    
    def extract_translation(self) -> Tuple[float, float]:
        """Extract translation components."""
        return (self.matrix[0, 2], self.matrix[1, 2])
    
    def extract_scale(self) -> Tuple[float, float]:
        """Extract scale components."""
        sx = math.sqrt(self.matrix[0, 0]**2 + self.matrix[1, 0]**2)
        sy = math.sqrt(self.matrix[0, 1]**2 + self.matrix[1, 1]**2)
        return (sx, sy)
    
    def extract_rotation(self) -> float:
        """Extract rotation angle."""
        return math.atan2(self.matrix[1, 0], self.matrix[0, 0])
    
    def to_qtransform(self) -> 'QTransform':
        """Convert to Qt QTransform."""
        if not QT_AVAILABLE:
            raise ImportError("PyQt6 not available")
        
        # QTransform uses a different matrix layout
        return QTransform(
            self.matrix[0, 0], self.matrix[1, 0],  # m11, m12
            self.matrix[0, 1], self.matrix[1, 1],  # m21, m22
            self.matrix[0, 2], self.matrix[1, 2]   # dx, dy
        )
    
    def __eq__(self, other: 'TransformationMatrix') -> bool:
        """Check equality with another transformation matrix."""
        if not isinstance(other, TransformationMatrix):
            return False
        return np.allclose(self.matrix, other.matrix)
    
    def __str__(self) -> str:
        """String representation of the matrix."""
        return f"TransformationMatrix(\n{self.matrix}\n)"
    
    def __repr__(self) -> str:
        """Representation of the matrix."""
        return f"TransformationMatrix({self.matrix.tolist()})"


class AffineTransformation:
    """High-performance affine transformation with caching."""
    
    def __init__(self, matrix: Optional[TransformationMatrix] = None):
        """Initialize affine transformation."""
        self.matrix = matrix or TransformationMatrix.identity()
        self._cached_inverse: Optional[TransformationMatrix] = None
        self._cached_determinant: Optional[float] = None
        
    @classmethod
    def identity(cls) -> 'AffineTransformation':
        """Create identity transformation."""
        return cls(TransformationMatrix.identity())
    
    @classmethod
    def translation(cls, dx: float, dy: float) -> 'AffineTransformation':
        """Create translation transformation."""
        return cls(TransformationMatrix.translation(dx, dy))
    
    @classmethod
    def scaling(cls, sx: float, sy: float) -> 'AffineTransformation':
        """Create scaling transformation."""
        return cls(TransformationMatrix.scaling(sx, sy))
    
    @classmethod
    def uniform_scaling(cls, scale: float) -> 'AffineTransformation':
        """Create uniform scaling transformation."""
        return cls(TransformationMatrix.scaling(scale, scale))
    
    @classmethod
    def rotation(cls, angle: float) -> 'AffineTransformation':
        """Create rotation transformation."""
        return cls(TransformationMatrix.rotation(angle))
    
    @classmethod
    def rotation_degrees(cls, degrees: float) -> 'AffineTransformation':
        """Create rotation transformation from degrees."""
        return cls(TransformationMatrix.rotation(math.radians(degrees)))
    
    @classmethod
    def shearing(cls, shx: float, shy: float) -> 'AffineTransformation':
        """Create shearing transformation."""
        return cls(TransformationMatrix.shearing(shx, shy))
    
    @classmethod
    def from_points(cls, src_points: List[Point], dst_points: List[Point]) -> 'AffineTransformation':
        """Create transformation from corresponding points."""
        if len(src_points) != len(dst_points) or len(src_points) < 3:
            raise ValueError("Need at least 3 corresponding points")
        
        # Use least squares to find transformation
        # This is a simplified implementation - could be enhanced
        src_array = np.array([[p.x, p.y, 1.0] for p in src_points[:3]], dtype=np.float64)
        dst_array = np.array([[p.x, p.y, 1.0] for p in dst_points[:3]], dtype=np.float64)
        
        try:
            # Solve for transformation matrix
            transform = np.linalg.solve(src_array, dst_array)
            return cls(TransformationMatrix(transform.T))
        except np.linalg.LinAlgError:
            raise ValueError("Cannot determine transformation from given points")
    
    def transform_point(self, x: float, y: float) -> Tuple[float, float]:
        """Transform a single point."""
        return self.matrix.apply((x, y))
    
    def transform_point_obj(self, point: Point) -> Point:
        """Transform a Point object."""
        x, y = self.matrix.apply((point.x, point.y))
        return Point(x, y)
    
    def transform_rect(self, rect: Rect) -> Rect:
        """Transform a rectangle."""
        # Transform all four corners
        corners = [
            rect.top_left,
            rect.top_right,
            rect.bottom_left,
            rect.bottom_right
        ]
        
        transformed_corners = [self.transform_point_obj(corner) for corner in corners]
        
        # Find bounding box of transformed corners
        min_x = min(p.x for p in transformed_corners)
        max_x = max(p.x for p in transformed_corners)
        min_y = min(p.y for p in transformed_corners)
        max_y = max(p.y for p in transformed_corners)
        
        return Rect(min_x, min_y, max_x - min_x, max_y - min_y)
    
    def transform_points(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Transform multiple points efficiently."""
        return self.matrix.apply_to_points(points)
    
    def transform_point_objects(self, points: List[Point]) -> List[Point]:
        """Transform multiple Point objects efficiently."""
        tuples = [(p.x, p.y) for p in points]
        transformed = self.matrix.apply_to_points(tuples)
        return [Point(x, y) for x, y in transformed]
    
    def inverse(self) -> 'AffineTransformation':
        """Get cached inverse transformation."""
        if self._cached_inverse is None:
            self._cached_inverse = self.matrix.inverse()
        return AffineTransformation(self._cached_inverse)
    
    def compose(self, other: 'AffineTransformation') -> 'AffineTransformation':
        """Compose transformations (self * other)."""
        result_matrix = self.matrix.compose(other.matrix)
        return AffineTransformation(result_matrix)
    
    def prepend(self, other: 'AffineTransformation') -> 'AffineTransformation':
        """Prepend transformation (other * self)."""
        result_matrix = other.matrix.compose(self.matrix)
        return AffineTransformation(result_matrix)
    
    def determinant(self) -> float:
        """Get cached transformation determinant."""
        if self._cached_determinant is None:
            self._cached_determinant = self.matrix.determinant()
        return self._cached_determinant
    
    def is_invertible(self) -> bool:
        """Check if transformation is invertible."""
        return self.matrix.is_invertible()
    
    def is_identity(self, tolerance: float = 1e-10) -> bool:
        """Check if transformation is identity."""
        return self.matrix.is_identity(tolerance)
    
    def extract_translation(self) -> Point:
        """Extract translation as Point."""
        tx, ty = self.matrix.extract_translation()
        return Point(tx, ty)
    
    def extract_scale(self) -> Size:
        """Extract scale as Size."""
        sx, sy = self.matrix.extract_scale()
        return Size(sx, sy)
    
    def extract_rotation(self) -> float:
        """Extract rotation angle in radians."""
        return self.matrix.extract_rotation()
    
    def extract_rotation_degrees(self) -> float:
        """Extract rotation angle in degrees."""
        return math.degrees(self.extract_rotation())
    
    def to_qtransform(self) -> 'QTransform':
        """Convert to Qt QTransform."""
        return self.matrix.to_qtransform()
    
    def invalidate_cache(self):
        """Invalidate cached values."""
        self._cached_inverse = None
        self._cached_determinant = None
    
    def __eq__(self, other: 'AffineTransformation') -> bool:
        """Check equality with another transformation."""
        if not isinstance(other, AffineTransformation):
            return False
        return self.matrix == other.matrix
    
    def __str__(self) -> str:
        """String representation."""
        return f"AffineTransformation({self.matrix})"
    
    def __repr__(self) -> str:
        """Representation."""
        return f"AffineTransformation({self.matrix.matrix.tolist()})"


class TransformationBuilder:
    """Builder for composing complex transformations."""
    
    def __init__(self):
        """Initialize transformation builder."""
        self._transformation = AffineTransformation.identity()
    
    def translate(self, dx: float, dy: float) -> 'TransformationBuilder':
        """Add translation."""
        self._transformation = self._transformation.compose(
            AffineTransformation.translation(dx, dy)
        )
        return self
    
    def scale(self, sx: float, sy: float) -> 'TransformationBuilder':
        """Add scaling."""
        self._transformation = self._transformation.compose(
            AffineTransformation.scaling(sx, sy)
        )
        return self
    
    def uniform_scale(self, scale: float) -> 'TransformationBuilder':
        """Add uniform scaling."""
        self._transformation = self._transformation.compose(
            AffineTransformation.uniform_scaling(scale)
        )
        return self
    
    def rotate(self, angle: float) -> 'TransformationBuilder':
        """Add rotation."""
        self._transformation = self._transformation.compose(
            AffineTransformation.rotation(angle)
        )
        return self
    
    def rotate_degrees(self, degrees: float) -> 'TransformationBuilder':
        """Add rotation in degrees."""
        self._transformation = self._transformation.compose(
            AffineTransformation.rotation_degrees(degrees)
        )
        return self
    
    def shear(self, shx: float, shy: float) -> 'TransformationBuilder':
        """Add shearing."""
        self._transformation = self._transformation.compose(
            AffineTransformation.shearing(shx, shy)
        )
        return self
    
    def transform_around_point(self, point: Point, transform_func) -> 'TransformationBuilder':
        """Apply transformation around a specific point."""
        # Translate to origin
        self.translate(-point.x, -point.y)
        
        # Apply transformation
        transform_func(self)
        
        # Translate back
        self.translate(point.x, point.y)
        
        return self
    
    def scale_around_point(self, point: Point, sx: float, sy: float) -> 'TransformationBuilder':
        """Scale around a specific point."""
        return self.transform_around_point(
            point, 
            lambda builder: builder.scale(sx, sy)
        )
    
    def rotate_around_point(self, point: Point, angle: float) -> 'TransformationBuilder':
        """Rotate around a specific point."""
        return self.transform_around_point(
            point,
            lambda builder: builder.rotate(angle)
        )
    
    def build(self) -> AffineTransformation:
        """Build the final transformation."""
        return self._transformation
    
    def reset(self) -> 'TransformationBuilder':
        """Reset to identity transformation."""
        self._transformation = AffineTransformation.identity()
        return self