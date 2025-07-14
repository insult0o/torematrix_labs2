# AGENT 1 COORDINATES - Core Transformation Engine

## 🎯 Your Mission
You are **Agent 1** implementing the **Core Transformation Engine** for the Document Viewer Coordinate Mapping system. You will build the mathematical foundation and core APIs for all coordinate transformations.

## 📋 Your Assignment
**Sub-Issue #149**: [Coordinate Mapping Sub-Issue #18.1: Core Transformation Engine](https://github.com/insult0o/torematrix_labs2/issues/149)

## 🚀 What You're Building
A high-performance coordinate transformation engine with:
- Affine transformation matrices
- Document-to-viewer coordinate conversion
- Coordinate validation and caching
- Mathematical utilities for geometric operations

## 📁 Files to Create

### Primary Implementation Files
```
src/torematrix/ui/viewer/coordinates.py
src/torematrix/ui/viewer/transformations.py
src/torematrix/utils/geometry.py
```

### Test Files
```
tests/unit/viewer/test_coordinates.py
tests/unit/viewer/test_transformations.py
tests/unit/utils/test_geometry.py
```

## 🔧 Technical Implementation Details

### 1. Core Coordinate Mapper (`src/torematrix/ui/viewer/coordinates.py`)
```python
from typing import Tuple, Optional, List, Union, Dict, Any
from dataclasses import dataclass
import numpy as np
from PyQt6.QtCore import QPointF, QRectF, QSizeF
from PyQt6.QtGui import QTransform

from .transformations import AffineTransformation, TransformationMatrix
from ..utils.geometry import Point, Rect, Size

@dataclass
class CoordinateSpace:
    """Defines a coordinate space with origin and scale."""
    origin: Point
    scale: float
    rotation: float = 0.0
    name: str = "default"

class CoordinateMapper:
    """Core coordinate mapping engine with caching and validation."""
    
    def __init__(self, document_space: CoordinateSpace, viewer_space: CoordinateSpace):
        self.document_space = document_space
        self.viewer_space = viewer_space
        self._transformation_cache: Dict[str, AffineTransformation] = {}
        self._validation_enabled = True
        
    def document_to_viewer(self, point: Union[Point, Tuple[float, float]]) -> Point:
        """Transform document coordinates to viewer coordinates."""
        # Implementation with caching and validation
        
    def viewer_to_document(self, point: Union[Point, Tuple[float, float]]) -> Point:
        """Transform viewer coordinates to document coordinates."""
        # Implementation with caching and validation
        
    def batch_transform(self, points: List[Point], source: str, target: str) -> List[Point]:
        """Batch transform multiple points efficiently."""
        # Optimized batch processing
        
    def validate_coordinate(self, point: Point, space: str) -> bool:
        """Validate coordinate within space bounds."""
        # Coordinate validation logic
        
    def clear_cache(self):
        """Clear transformation cache."""
        self._transformation_cache.clear()
        
    def get_transformation(self, source: str, target: str) -> AffineTransformation:
        """Get cached or create new transformation."""
        # Transformation caching and retrieval
```

### 2. Affine Transformations (`src/torematrix/ui/viewer/transformations.py`)
```python
from typing import Tuple, Optional, List
import numpy as np
from PyQt6.QtGui import QTransform
from dataclasses import dataclass

@dataclass
class TransformationMatrix:
    """Immutable 3x3 transformation matrix."""
    matrix: np.ndarray
    
    def __post_init__(self):
        assert self.matrix.shape == (3, 3), "Matrix must be 3x3"
        
    def apply(self, point: Tuple[float, float]) -> Tuple[float, float]:
        """Apply transformation to a point."""
        
    def compose(self, other: 'TransformationMatrix') -> 'TransformationMatrix':
        """Compose with another transformation."""
        
    def inverse(self) -> 'TransformationMatrix':
        """Get inverse transformation."""
        
    def to_qtransform(self) -> QTransform:
        """Convert to Qt QTransform."""

class AffineTransformation:
    """High-performance affine transformation with caching."""
    
    def __init__(self, matrix: Optional[TransformationMatrix] = None):
        self.matrix = matrix or TransformationMatrix.identity()
        self._cached_inverse: Optional[TransformationMatrix] = None
        
    @classmethod
    def identity(cls) -> 'AffineTransformation':
        """Create identity transformation."""
        
    @classmethod
    def translation(cls, dx: float, dy: float) -> 'AffineTransformation':
        """Create translation transformation."""
        
    @classmethod
    def scaling(cls, sx: float, sy: float) -> 'AffineTransformation':
        """Create scaling transformation."""
        
    @classmethod
    def rotation(cls, angle: float) -> 'AffineTransformation':
        """Create rotation transformation."""
        
    def transform_point(self, x: float, y: float) -> Tuple[float, float]:
        """Transform a single point."""
        
    def transform_rect(self, rect: Rect) -> Rect:
        """Transform a rectangle."""
        
    def transform_points(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Transform multiple points efficiently."""
        
    def inverse(self) -> 'AffineTransformation':
        """Get cached inverse transformation."""
        
    def compose(self, other: 'AffineTransformation') -> 'AffineTransformation':
        """Compose transformations."""
```

### 3. Geometric Utilities (`src/torematrix/utils/geometry.py`)
```python
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
        
    def midpoint(self, other: 'Point') -> 'Point':
        """Calculate midpoint with another point."""
        
    def rotate(self, angle: float, center: Optional['Point'] = None) -> 'Point':
        """Rotate point around center."""
        
    def scale(self, factor: float, center: Optional['Point'] = None) -> 'Point':
        """Scale point from center."""
        
    def to_tuple(self) -> Tuple[float, float]:
        """Convert to tuple."""
        return (self.x, self.y)

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
        
    @property
    def top_left(self) -> Point:
        """Get top-left corner."""
        
    @property
    def bottom_right(self) -> Point:
        """Get bottom-right corner."""
        
    def contains(self, point: Point) -> bool:
        """Check if point is inside rectangle."""
        
    def intersects(self, other: 'Rect') -> bool:
        """Check if rectangles intersect."""
        
    def intersection(self, other: 'Rect') -> Optional['Rect']:
        """Get intersection rectangle."""
        
    def transform(self, transformation) -> 'Rect':
        """Apply transformation to rectangle."""

@dataclass
class Size:
    """2D size with utility methods."""
    width: float
    height: float
    
    def scale(self, factor: float) -> 'Size':
        """Scale size by factor."""
        
    def aspect_ratio(self) -> float:
        """Calculate aspect ratio."""

class GeometryUtils:
    """Utility functions for geometric operations."""
    
    @staticmethod
    def angle_between_points(p1: Point, p2: Point) -> float:
        """Calculate angle between two points."""
        
    @staticmethod
    def point_in_polygon(point: Point, polygon: List[Point]) -> bool:
        """Check if point is inside polygon."""
        
    @staticmethod
    def line_intersection(p1: Point, p2: Point, p3: Point, p4: Point) -> Optional[Point]:
        """Find intersection of two lines."""
        
    @staticmethod
    def normalize_angle(angle: float) -> float:
        """Normalize angle to [-π, π]."""
        
    @staticmethod
    def clamp(value: float, min_val: float, max_val: float) -> float:
        """Clamp value between min and max."""
```

## 🧪 Testing Requirements

### 1. Coordinate Transformation Tests (`tests/unit/viewer/test_coordinates.py`)
```python
import pytest
from src.torematrix.ui.viewer.coordinates import CoordinateMapper, CoordinateSpace
from src.torematrix.utils.geometry import Point, Rect

class TestCoordinateMapper:
    def test_document_to_viewer_conversion(self):
        """Test basic document to viewer coordinate conversion."""
        
    def test_viewer_to_document_conversion(self):
        """Test basic viewer to document coordinate conversion."""
        
    def test_batch_transformation(self):
        """Test batch point transformation performance."""
        
    def test_coordinate_validation(self):
        """Test coordinate validation within bounds."""
        
    def test_transformation_caching(self):
        """Test transformation caching efficiency."""
        
    def test_coordinate_accuracy(self):
        """Test sub-pixel coordinate accuracy."""
        
    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
```

### 2. Transformation Matrix Tests (`tests/unit/viewer/test_transformations.py`)
```python
import pytest
import numpy as np
from src.torematrix.ui.viewer.transformations import AffineTransformation, TransformationMatrix

class TestAffineTransformation:
    def test_identity_transformation(self):
        """Test identity transformation."""
        
    def test_translation_transformation(self):
        """Test translation transformation."""
        
    def test_scaling_transformation(self):
        """Test scaling transformation."""
        
    def test_rotation_transformation(self):
        """Test rotation transformation."""
        
    def test_transformation_composition(self):
        """Test transformation composition."""
        
    def test_inverse_transformation(self):
        """Test inverse transformation accuracy."""
        
    def test_batch_point_transformation(self):
        """Test batch point transformation performance."""
```

### 3. Geometry Tests (`tests/unit/utils/test_geometry.py`)
```python
import pytest
from src.torematrix.utils.geometry import Point, Rect, Size, GeometryUtils

class TestGeometryUtils:
    def test_point_operations(self):
        """Test point distance, midpoint, rotation."""
        
    def test_rectangle_operations(self):
        """Test rectangle intersection, contains, transform."""
        
    def test_geometric_calculations(self):
        """Test angle calculations, line intersections."""
        
    def test_coordinate_precision(self):
        """Test sub-pixel precision in calculations."""
```

## 🎯 Success Criteria

### Core Functionality
- [ ] CoordinateMapper class with document-to-viewer conversion
- [ ] AffineTransformation with matrix operations
- [ ] Geometric utilities with Point, Rect, Size classes
- [ ] Coordinate validation and bounds checking
- [ ] Transformation caching for performance
- [ ] Sub-pixel accuracy in all transformations

### Performance Requirements
- [ ] Batch transformation of 10,000+ points in <100ms
- [ ] Coordinate conversion accuracy to 0.01 pixel
- [ ] Transformation caching reduces computation by 80%
- [ ] Memory usage <10MB for typical document

### Testing Requirements
- [ ] >95% code coverage across all files
- [ ] Performance benchmarks for key operations
- [ ] Accuracy tests with known coordinate values
- [ ] Edge case handling for invalid inputs

## 🔗 Integration Points

### For Agent 2 (Viewport & Screen Mapping)
- Export `CoordinateMapper` class
- Provide `CoordinateSpace` definitions
- Supply transformation validation utilities

### For Agent 3 (Zoom, Pan & Rotation)
- Export `AffineTransformation` class
- Provide transformation composition methods
- Supply performance monitoring hooks

### For Agent 4 (Multi-Page Integration)
- Export complete coordinate mapping API
- Provide debugging and validation tools
- Supply geometric utility functions

## 📊 Performance Targets
- Document-to-viewer conversion: <1ms for single point
- Batch transformation: <100ms for 10,000 points
- Coordinate validation: <0.1ms per point
- Memory usage: <10MB for coordinate cache

## 🛠️ Development Workflow

### Phase 1: Core Implementation (Days 1-2)
1. Create coordinate system abstractions
2. Implement affine transformation engine
3. Add geometric utilities
4. Create basic coordinate mapper
5. Add coordinate validation
6. Implement transformation caching

### Phase 2: Testing & Optimization (Days 1-2)
1. Write comprehensive unit tests
2. Add performance benchmarks
3. Optimize transformation algorithms
4. Add debug visualization helpers
5. Complete API documentation

## 🚀 Getting Started

1. **Create your feature branch**: `git checkout -b feature/coordinates-core-agent1-issue149`
2. **Verify branch**: `git branch --show-current`
3. **Start with coordinate mapper**: Implement the core CoordinateMapper class
4. **Add transformations**: Create the AffineTransformation system
5. **Build utilities**: Add geometric utility functions
6. **Write tests**: Create comprehensive test suite
7. **Optimize**: Add caching and performance optimization

## 📝 Implementation Notes

### Key Architecture Decisions
- Use numpy for matrix operations (performance)
- Implement immutable transformation matrices
- Cache transformations for repeated operations
- Support both PyQt6 and raw coordinate types
- Maintain sub-pixel accuracy throughout

### Performance Considerations
- Pre-compute transformation matrices
- Use vectorized operations for batch processing
- Implement lazy evaluation for expensive operations
- Cache frequently used transformations
- Monitor memory usage for large documents

### Integration Requirements
- Thread-safe coordinate operations
- Consistent API across all coordinate spaces
- Proper error handling and validation
- Debug visualization support
- Performance monitoring hooks

## 🎯 Communication Protocol

- **Daily Progress**: Comment on Issue #149 with progress updates
- **Blockers**: Tag @insult0o for immediate assistance
- **Integration**: Coordinate with other agents via main issue #18
- **Testing**: Report test coverage and performance metrics

## 📚 Reference Materials

- [Qt Coordinate System Documentation](https://doc.qt.io/qt-6/coordsys.html)
- [NumPy Array Operations](https://numpy.org/doc/stable/reference/routines.array-manipulation.html)
- [Affine Transformation Mathematics](https://en.wikipedia.org/wiki/Affine_transformation)
- [Computer Graphics Coordinate Systems](https://www.scratchapixel.com/lessons/mathematics-physics-for-computer-graphics/geometry/coordinate-systems)

**Good luck, Agent 1! You're building the foundation that enables all coordinate mapping in the document viewer. Focus on accuracy, performance, and clean APIs that other agents can easily integrate with.**