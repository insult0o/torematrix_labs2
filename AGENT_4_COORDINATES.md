# AGENT 4 COORDINATES - Multi-Page Integration & Production

## 🎯 Your Mission
You are **Agent 4** implementing the **Multi-Page Integration & Production** system for the Document Viewer Coordinate Mapping. You will create the final production-ready system with multi-page support, comprehensive testing, and complete integration.

## 📋 Your Assignment
**Sub-Issue #153**: [Coordinate Mapping Sub-Issue #18.4: Multi-Page Integration & Production](https://github.com/insult0o/torematrix_labs2/issues/153)

## 🚀 What You're Building
A production-ready coordinate mapping system with:
- Multi-page coordinate system management
- PDF.js integration for PDF document coordinates
- Comprehensive testing and debugging tools
- Production monitoring and performance profiling
- Complete documentation and deployment readiness

## 📁 Files to Create

### Primary Implementation Files
```
src/torematrix/ui/viewer/multipage.py
src/torematrix/ui/viewer/debug.py
src/torematrix/ui/viewer/integration.py
```

### Test Files
```
tests/integration/viewer/test_coordinate_mapping.py
tests/performance/viewer/test_coordinate_performance.py
```

### Documentation
```
docs/coordinate_mapping.md
```

## 🔧 Technical Implementation Details

### 1. Multi-Page Coordinate System (`src/torematrix/ui/viewer/multipage.py`)
```python
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal
import math

from .coordinates import CoordinateMapper, CoordinateSpace
from .transformations import AffineTransformation
from .viewport import ViewportManager
from .zoom import ZoomManager
from .pan import PanManager
from .rotation import RotationManager
from ..utils.geometry import Point, Rect, Size

@dataclass
class PageInfo:
    """Information about a document page."""
    page_number: int
    size: Size
    offset: Point
    coordinate_space: CoordinateSpace
    pdf_page_ref: Optional[Any] = None  # PDF.js page reference

@dataclass
class MultiPageState:
    """State of multi-page coordinate system."""
    pages: List[PageInfo]
    current_page: int
    page_spacing: float
    layout_mode: str  # 'single', 'continuous', 'spread'
    total_size: Size

class MultiPageCoordinateSystem(QObject):
    """Manages coordinates across multiple document pages."""
    
    # Signals
    page_changed = pyqtSignal(int)  # page_number
    layout_changed = pyqtSignal(str)  # layout_mode
    coordinates_updated = pyqtSignal()
    
    def __init__(self, viewport_manager: ViewportManager):
        super().__init__()
        self.viewport_manager = viewport_manager
        self._state = MultiPageState([], 0, 20.0, 'single', Size(0, 0))
        self._coordinate_mappers: Dict[int, CoordinateMapper] = {}
        self._page_transformations: Dict[int, AffineTransformation] = {}
        
    def add_page(self, page_info: PageInfo):
        """Add a page to the coordinate system."""
        self._state.pages.append(page_info)
        
        # Create coordinate mapper for this page
        document_space = page_info.coordinate_space
        viewer_space = self._create_viewer_space_for_page(page_info)
        
        mapper = CoordinateMapper(document_space, viewer_space)
        self._coordinate_mappers[page_info.page_number] = mapper
        
        # Update layout
        self._update_layout()
        
    def remove_page(self, page_number: int) -> bool:
        """Remove a page from the coordinate system."""
        page_index = self._find_page_index(page_number)
        if page_index is None:
            return False
            
        # Remove page and mapper
        self._state.pages.pop(page_index)
        self._coordinate_mappers.pop(page_number, None)
        self._page_transformations.pop(page_number, None)
        
        # Update layout
        self._update_layout()
        return True
        
    def get_page_count(self) -> int:
        """Get total number of pages."""
        return len(self._state.pages)
        
    def set_current_page(self, page_number: int) -> bool:
        """Set current active page."""
        if not self._is_valid_page(page_number):
            return False
            
        self._state.current_page = page_number
        self.page_changed.emit(page_number)
        return True
        
    def get_current_page(self) -> int:
        """Get current active page."""
        return self._state.current_page
        
    def set_layout_mode(self, mode: str):
        """Set page layout mode."""
        if mode not in ['single', 'continuous', 'spread']:
            raise ValueError(f"Invalid layout mode: {mode}")
            
        self._state.layout_mode = mode
        self._update_layout()
        self.layout_changed.emit(mode)
        
    def get_layout_mode(self) -> str:
        """Get current layout mode."""
        return self._state.layout_mode
        
    def document_to_viewer(self, point: Point, page_number: int) -> Optional[Point]:
        """Convert document coordinates to viewer coordinates for specific page."""
        mapper = self._coordinate_mappers.get(page_number)
        if not mapper:
            return None
            
        # Convert to page coordinates
        page_point = mapper.document_to_viewer(point)
        
        # Apply page transformation
        page_transform = self._get_page_transformation(page_number)
        if page_transform:
            transformed = page_transform.transform_point(page_point.x, page_point.y)
            return Point(transformed[0], transformed[1])
            
        return page_point
        
    def viewer_to_document(self, point: Point, page_number: int) -> Optional[Point]:
        """Convert viewer coordinates to document coordinates for specific page."""
        mapper = self._coordinate_mappers.get(page_number)
        if not mapper:
            return None
            
        # Remove page transformation
        page_transform = self._get_page_transformation(page_number)
        if page_transform:
            inverse_transform = page_transform.inverse()
            untransformed = inverse_transform.transform_point(point.x, point.y)
            point = Point(untransformed[0], untransformed[1])
            
        # Convert to document coordinates
        return mapper.viewer_to_document(point)
        
    def find_page_at_point(self, point: Point) -> Optional[int]:
        """Find which page contains the given viewer point."""
        for page_info in self._state.pages:
            page_bounds = self._get_page_bounds(page_info.page_number)
            if page_bounds and page_bounds.contains(point):
                return page_info.page_number
        return None
        
    def get_page_bounds(self, page_number: int) -> Optional[Rect]:
        """Get page bounds in viewer coordinates."""
        return self._get_page_bounds(page_number)
        
    def get_visible_pages(self) -> List[int]:
        """Get list of currently visible pages."""
        viewport_bounds = self.viewport_manager.get_visible_bounds()
        if not viewport_bounds:
            return []
            
        visible_pages = []
        for page_info in self._state.pages:
            page_bounds = self._get_page_bounds(page_info.page_number)
            if page_bounds and page_bounds.intersects(viewport_bounds):
                visible_pages.append(page_info.page_number)
                
        return visible_pages
        
    def scroll_to_page(self, page_number: int, position: str = 'top') -> bool:
        """Scroll to show specific page."""
        if not self._is_valid_page(page_number):
            return False
            
        page_bounds = self._get_page_bounds(page_number)
        if not page_bounds:
            return False
            
        # Calculate scroll position
        if position == 'top':
            scroll_point = Point(page_bounds.x, page_bounds.y)
        elif position == 'center':
            scroll_point = page_bounds.center
        elif position == 'bottom':
            scroll_point = Point(page_bounds.x, page_bounds.y + page_bounds.height)
        else:
            return False
            
        # Scroll viewport to show page
        # This would integrate with pan manager
        return True
        
    def get_total_document_size(self) -> Size:
        """Get total document size across all pages."""
        return self._state.total_size
        
    def batch_transform_points(self, points: List[Tuple[Point, int]]) -> List[Optional[Point]]:
        """Batch transform multiple points with their page numbers."""
        results = []
        for point, page_number in points:
            result = self.document_to_viewer(point, page_number)
            results.append(result)
        return results
        
    def update_page_transformations(self):
        """Update all page transformations based on current state."""
        for page_info in self._state.pages:
            self._update_page_transformation(page_info.page_number)
            
    def _create_viewer_space_for_page(self, page_info: PageInfo) -> CoordinateSpace:
        """Create viewer coordinate space for a page."""
        return CoordinateSpace(
            origin=Point(0, 0),
            scale=1.0,
            name=f"viewer_page_{page_info.page_number}"
        )
        
    def _update_layout(self):
        """Update page layout based on current mode."""
        if not self._state.pages:
            self._state.total_size = Size(0, 0)
            return
            
        if self._state.layout_mode == 'single':
            self._layout_single_page()
        elif self._state.layout_mode == 'continuous':
            self._layout_continuous()
        elif self._state.layout_mode == 'spread':
            self._layout_spread()
            
        self.coordinates_updated.emit()
        
    def _layout_single_page(self):
        """Layout pages in single page mode."""
        # In single page mode, only current page is positioned
        current_page_info = self._get_page_info(self._state.current_page)
        if current_page_info:
            current_page_info.offset = Point(0, 0)
            self._state.total_size = current_page_info.size
            
    def _layout_continuous(self):
        """Layout pages in continuous mode."""
        y_offset = 0.0
        max_width = 0.0
        
        for page_info in self._state.pages:
            page_info.offset = Point(0, y_offset)
            y_offset += page_info.size.height + self._state.page_spacing
            max_width = max(max_width, page_info.size.width)
            
        self._state.total_size = Size(max_width, y_offset - self._state.page_spacing)
        
    def _layout_spread(self):
        """Layout pages in spread mode (two pages side by side)."""
        y_offset = 0.0
        max_width = 0.0
        
        for i in range(0, len(self._state.pages), 2):
            left_page = self._state.pages[i]
            right_page = self._state.pages[i + 1] if i + 1 < len(self._state.pages) else None
            
            # Position left page
            left_page.offset = Point(0, y_offset)
            
            # Position right page
            if right_page:
                right_page.offset = Point(left_page.size.width + self._state.page_spacing, y_offset)
                spread_width = left_page.size.width + self._state.page_spacing + right_page.size.width
                spread_height = max(left_page.size.height, right_page.size.height)
            else:
                spread_width = left_page.size.width
                spread_height = left_page.size.height
                
            max_width = max(max_width, spread_width)
            y_offset += spread_height + self._state.page_spacing
            
        self._state.total_size = Size(max_width, y_offset - self._state.page_spacing)
        
    def _get_page_transformation(self, page_number: int) -> Optional[AffineTransformation]:
        """Get transformation for specific page."""
        page_info = self._get_page_info(page_number)
        if not page_info:
            return None
            
        # Create transformation based on page offset
        return AffineTransformation.translation(page_info.offset.x, page_info.offset.y)
        
    def _update_page_transformation(self, page_number: int):
        """Update transformation for specific page."""
        transformation = self._get_page_transformation(page_number)
        if transformation:
            self._page_transformations[page_number] = transformation
            
    def _get_page_bounds(self, page_number: int) -> Optional[Rect]:
        """Get page bounds in viewer coordinates."""
        page_info = self._get_page_info(page_number)
        if not page_info:
            return None
            
        return Rect(
            page_info.offset.x,
            page_info.offset.y,
            page_info.size.width,
            page_info.size.height
        )
        
    def _get_page_info(self, page_number: int) -> Optional[PageInfo]:
        """Get page information by number."""
        for page_info in self._state.pages:
            if page_info.page_number == page_number:
                return page_info
        return None
        
    def _find_page_index(self, page_number: int) -> Optional[int]:
        """Find page index by number."""
        for i, page_info in enumerate(self._state.pages):
            if page_info.page_number == page_number:
                return i
        return None
        
    def _is_valid_page(self, page_number: int) -> bool:
        """Check if page number is valid."""
        return any(page.page_number == page_number for page in self._state.pages)
```

### 2. Debug Visualization (`src/torematrix/ui/viewer/debug.py`)
```python
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PyQt6.QtWidgets import QWidget

from .coordinates import CoordinateMapper
from .multipage import MultiPageCoordinateSystem
from ..utils.geometry import Point, Rect

@dataclass
class DebugInfo:
    """Debug information for coordinate mapping."""
    coordinate_points: List[Tuple[Point, str]]  # (point, label)
    transformation_matrices: Dict[str, str]  # transformation_name -> matrix_string
    performance_metrics: Dict[str, float]
    page_boundaries: List[Rect]
    coordinate_spaces: List[str]

class CoordinateDebugger(QObject):
    """Debug visualization for coordinate mapping system."""
    
    # Signals
    debug_info_updated = pyqtSignal(DebugInfo)
    
    def __init__(self, multipage_system: MultiPageCoordinateSystem):
        super().__init__()
        self.multipage_system = multipage_system
        self._debug_enabled = False
        self._debug_info = DebugInfo([], {}, {}, [], [])
        
    def enable_debug(self, enabled: bool):
        """Enable or disable debug visualization."""
        self._debug_enabled = enabled
        if enabled:
            self._update_debug_info()
            
    def is_debug_enabled(self) -> bool:
        """Check if debug is enabled."""
        return self._debug_enabled
        
    def add_debug_point(self, point: Point, label: str):
        """Add a debug point to visualize."""
        if self._debug_enabled:
            self._debug_info.coordinate_points.append((point, label))
            self._update_debug_info()
            
    def clear_debug_points(self):
        """Clear all debug points."""
        self._debug_info.coordinate_points.clear()
        self._update_debug_info()
        
    def draw_debug_overlay(self, painter: QPainter, widget: QWidget):
        """Draw debug overlay on widget."""
        if not self._debug_enabled:
            return
            
        # Set up painter
        painter.save()
        
        # Draw coordinate grid
        self._draw_coordinate_grid(painter, widget)
        
        # Draw page boundaries
        self._draw_page_boundaries(painter)
        
        # Draw debug points
        self._draw_debug_points(painter)
        
        # Draw transformation info
        self._draw_transformation_info(painter, widget)
        
        # Draw performance metrics
        self._draw_performance_metrics(painter, widget)
        
        painter.restore()
        
    def get_debug_info(self) -> DebugInfo:
        """Get current debug information."""
        return self._debug_info
        
    def log_coordinate_transformation(self, from_point: Point, to_point: Point, 
                                    transformation_name: str):
        """Log a coordinate transformation for debugging."""
        if self._debug_enabled:
            print(f"Transform {transformation_name}: {from_point} -> {to_point}")
            
    def validate_coordinate_accuracy(self, expected: Point, actual: Point, 
                                   tolerance: float = 0.01) -> bool:
        """Validate coordinate transformation accuracy."""
        distance = expected.distance_to(actual)
        is_accurate = distance <= tolerance
        
        if not is_accurate and self._debug_enabled:
            print(f"Coordinate accuracy warning: expected {expected}, got {actual}, "
                  f"distance {distance}, tolerance {tolerance}")
                  
        return is_accurate
        
    def _update_debug_info(self):
        """Update debug information."""
        if not self._debug_enabled:
            return
            
        # Update page boundaries
        self._debug_info.page_boundaries.clear()
        for page_num in range(self.multipage_system.get_page_count()):
            bounds = self.multipage_system.get_page_bounds(page_num)
            if bounds:
                self._debug_info.page_boundaries.append(bounds)
                
        # Update coordinate spaces
        self._debug_info.coordinate_spaces = [
            f"Page {i}" for i in range(self.multipage_system.get_page_count())
        ]
        
        self.debug_info_updated.emit(self._debug_info)
        
    def _draw_coordinate_grid(self, painter: QPainter, widget: QWidget):
        """Draw coordinate grid."""
        grid_color = QColor(100, 100, 100, 100)
        grid_pen = QPen(grid_color, 1)
        painter.setPen(grid_pen)
        
        # Draw grid lines every 50 pixels
        grid_spacing = 50
        
        for x in range(0, widget.width(), grid_spacing):
            painter.drawLine(x, 0, x, widget.height())
            
        for y in range(0, widget.height(), grid_spacing):
            painter.drawLine(0, y, widget.width(), y)
            
    def _draw_page_boundaries(self, painter: QPainter):
        """Draw page boundaries."""
        boundary_color = QColor(255, 0, 0, 150)
        boundary_pen = QPen(boundary_color, 2)
        painter.setPen(boundary_pen)
        
        for rect in self._debug_info.page_boundaries:
            painter.drawRect(int(rect.x), int(rect.y), 
                           int(rect.width), int(rect.height))
            
    def _draw_debug_points(self, painter: QPainter):
        """Draw debug points."""
        point_color = QColor(0, 255, 0, 200)
        point_brush = QBrush(point_color)
        painter.setBrush(point_brush)
        
        text_color = QColor(0, 0, 0, 255)
        text_pen = QPen(text_color)
        painter.setPen(text_pen)
        
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        for point, label in self._debug_info.coordinate_points:
            # Draw point
            painter.drawEllipse(int(point.x - 3), int(point.y - 3), 6, 6)
            
            # Draw label
            painter.drawText(int(point.x + 5), int(point.y - 5), label)
            
    def _draw_transformation_info(self, painter: QPainter, widget: QWidget):
        """Draw transformation information."""
        if not self._debug_info.transformation_matrices:
            return
            
        text_color = QColor(0, 0, 0, 200)
        text_pen = QPen(text_color)
        painter.setPen(text_pen)
        
        font = QFont("Courier", 8)
        painter.setFont(font)
        
        y_offset = 20
        for name, matrix_str in self._debug_info.transformation_matrices.items():
            painter.drawText(10, y_offset, f"{name}: {matrix_str}")
            y_offset += 15
            
    def _draw_performance_metrics(self, painter: QPainter, widget: QWidget):
        """Draw performance metrics."""
        if not self._debug_info.performance_metrics:
            return
            
        text_color = QColor(0, 0, 255, 200)
        text_pen = QPen(text_color)
        painter.setPen(text_pen)
        
        font = QFont("Arial", 8)
        painter.setFont(font)
        
        y_offset = widget.height() - 80
        for metric, value in self._debug_info.performance_metrics.items():
            painter.drawText(10, y_offset, f"{metric}: {value:.2f}")
            y_offset += 15

class CoordinateValidator:
    """Validates coordinate transformations for correctness."""
    
    def __init__(self, multipage_system: MultiPageCoordinateSystem):
        self.multipage_system = multipage_system
        self._validation_enabled = True
        self._validation_tolerance = 0.01
        
    def enable_validation(self, enabled: bool):
        """Enable or disable coordinate validation."""
        self._validation_enabled = enabled
        
    def set_tolerance(self, tolerance: float):
        """Set validation tolerance."""
        self._validation_tolerance = tolerance
        
    def validate_round_trip(self, point: Point, page_number: int) -> bool:
        """Validate round-trip coordinate transformation."""
        if not self._validation_enabled:
            return True
            
        # Document -> Viewer -> Document
        viewer_point = self.multipage_system.document_to_viewer(point, page_number)
        if not viewer_point:
            return False
            
        back_to_document = self.multipage_system.viewer_to_document(viewer_point, page_number)
        if not back_to_document:
            return False
            
        # Check if we got back to the original point
        distance = point.distance_to(back_to_document)
        return distance <= self._validation_tolerance
        
    def validate_coordinate_consistency(self) -> Dict[str, bool]:
        """Validate coordinate system consistency."""
        results = {}
        
        # Test points for validation
        test_points = [
            Point(0, 0), Point(100, 100), Point(500, 300),
            Point(-50, 200), Point(1000, 1000)
        ]
        
        for page_num in range(self.multipage_system.get_page_count()):
            for i, point in enumerate(test_points):
                test_name = f"page_{page_num}_point_{i}"
                results[test_name] = self.validate_round_trip(point, page_num)
                
        return results
        
    def run_validation_suite(self) -> Dict[str, Any]:
        """Run complete validation suite."""
        return {
            'round_trip_tests': self.validate_coordinate_consistency(),
            'tolerance': self._validation_tolerance,
            'enabled': self._validation_enabled
        }
```

### 3. System Integration (`src/torematrix/ui/viewer/integration.py`)
```python
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal
import time

from .coordinates import CoordinateMapper
from .multipage import MultiPageCoordinateSystem
from .viewport import ViewportManager
from .zoom import ZoomManager
from .pan import PanManager
from .rotation import RotationManager
from .debug import CoordinateDebugger, CoordinateValidator
from ..utils.geometry import Point, Rect

@dataclass
class IntegrationState:
    """State of the integrated coordinate system."""
    initialized: bool = False
    pdf_integration_active: bool = False
    debug_enabled: bool = False
    performance_monitoring: bool = False

class CoordinateSystemIntegrator(QObject):
    """Integrates all coordinate system components."""
    
    # Signals
    system_initialized = pyqtSignal()
    integration_error = pyqtSignal(str)
    performance_update = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self._state = IntegrationState()
        
        # Core components
        self._viewport_manager: Optional[ViewportManager] = None
        self._multipage_system: Optional[MultiPageCoordinateSystem] = None
        self._zoom_manager: Optional[ZoomManager] = None
        self._pan_manager: Optional[PanManager] = None
        self._rotation_manager: Optional[RotationManager] = None
        
        # Debug and monitoring
        self._debugger: Optional[CoordinateDebugger] = None
        self._validator: Optional[CoordinateValidator] = None
        
        # Performance monitoring
        self._performance_metrics: Dict[str, float] = {}
        self._performance_history: List[Dict[str, float]] = []
        
    def initialize(self, widget) -> bool:
        """Initialize the integrated coordinate system."""
        try:
            # Initialize core components
            self._viewport_manager = ViewportManager(widget)
            self._multipage_system = MultiPageCoordinateSystem(self._viewport_manager)
            
            # Initialize transformation managers
            base_mapper = CoordinateMapper(
                document_space=None,  # Will be set per page
                viewer_space=None     # Will be set per page
            )
            
            self._zoom_manager = ZoomManager(base_mapper)
            self._pan_manager = PanManager(base_mapper)
            self._rotation_manager = RotationManager(base_mapper)
            
            # Initialize debug tools
            self._debugger = CoordinateDebugger(self._multipage_system)
            self._validator = CoordinateValidator(self._multipage_system)
            
            # Connect signals
            self._connect_signals()
            
            self._state.initialized = True
            self.system_initialized.emit()
            return True
            
        except Exception as e:
            self.integration_error.emit(f"Failed to initialize coordinate system: {str(e)}")
            return False
            
    def is_initialized(self) -> bool:
        """Check if system is initialized."""
        return self._state.initialized
        
    def get_viewport_manager(self) -> Optional[ViewportManager]:
        """Get viewport manager."""
        return self._viewport_manager
        
    def get_multipage_system(self) -> Optional[MultiPageCoordinateSystem]:
        """Get multi-page coordinate system."""
        return self._multipage_system
        
    def get_zoom_manager(self) -> Optional[ZoomManager]:
        """Get zoom manager."""
        return self._zoom_manager
        
    def get_pan_manager(self) -> Optional[PanManager]:
        """Get pan manager."""
        return self._pan_manager
        
    def get_rotation_manager(self) -> Optional[RotationManager]:
        """Get rotation manager."""
        return self._rotation_manager
        
    def get_debugger(self) -> Optional[CoordinateDebugger]:
        """Get coordinate debugger."""
        return self._debugger
        
    def get_validator(self) -> Optional[CoordinateValidator]:
        """Get coordinate validator."""
        return self._validator
        
    def enable_pdf_integration(self, pdf_document) -> bool:
        """Enable PDF.js integration."""
        if not self._state.initialized:
            return False
            
        try:
            # Extract page information from PDF
            for page_num in range(pdf_document.numPages):
                page = pdf_document.getPage(page_num)
                page_info = self._create_page_info_from_pdf(page, page_num)
                
                if self._multipage_system:
                    self._multipage_system.add_page(page_info)
                    
            self._state.pdf_integration_active = True
            return True
            
        except Exception as e:
            self.integration_error.emit(f"Failed to enable PDF integration: {str(e)}")
            return False
            
    def enable_debug_mode(self, enabled: bool):
        """Enable or disable debug mode."""
        self._state.debug_enabled = enabled
        if self._debugger:
            self._debugger.enable_debug(enabled)
            
    def enable_performance_monitoring(self, enabled: bool):
        """Enable or disable performance monitoring."""
        self._state.performance_monitoring = enabled
        if enabled:
            self._start_performance_monitoring()
        else:
            self._stop_performance_monitoring()
            
    def get_performance_metrics(self) -> Dict[str, float]:
        """Get current performance metrics."""
        return self._performance_metrics.copy()
        
    def run_validation_suite(self) -> Dict[str, Any]:
        """Run complete validation suite."""
        if not self._validator:
            return {'error': 'Validator not initialized'}
            
        return self._validator.run_validation_suite()
        
    def transform_point(self, point: Point, from_space: str, to_space: str, 
                       page_number: int = 0) -> Optional[Point]:
        """Transform point between coordinate spaces."""
        if not self._state.initialized or not self._multipage_system:
            return None
            
        if from_space == 'document' and to_space == 'viewer':
            return self._multipage_system.document_to_viewer(point, page_number)
        elif from_space == 'viewer' and to_space == 'document':
            return self._multipage_system.viewer_to_document(point, page_number)
        elif from_space == 'viewer' and to_space == 'screen':
            if self._viewport_manager:
                return self._viewport_manager.viewer_to_screen(point)
        elif from_space == 'screen' and to_space == 'viewer':
            if self._viewport_manager:
                return self._viewport_manager.screen_to_viewer(point)
                
        return None
        
    def batch_transform_points(self, points: List[Tuple[Point, str, str, int]]) -> List[Optional[Point]]:
        """Batch transform multiple points."""
        results = []
        for point, from_space, to_space, page_number in points:
            result = self.transform_point(point, from_space, to_space, page_number)
            results.append(result)
        return results
        
    def _connect_signals(self):
        """Connect component signals."""
        if self._multipage_system:
            self._multipage_system.coordinates_updated.connect(self._on_coordinates_updated)
            
        if self._zoom_manager:
            self._zoom_manager.zoom_changed.connect(self._on_zoom_changed)
            
        if self._pan_manager:
            self._pan_manager.pan_changed.connect(self._on_pan_changed)
            
        if self._rotation_manager:
            self._rotation_manager.rotation_changed.connect(self._on_rotation_changed)
            
    def _on_coordinates_updated(self):
        """Handle coordinate system updates."""
        if self._state.performance_monitoring:
            self._update_performance_metrics()
            
    def _on_zoom_changed(self, zoom_level: float):
        """Handle zoom changes."""
        if self._state.performance_monitoring:
            self._performance_metrics['zoom_level'] = zoom_level
            
    def _on_pan_changed(self, offset: Point):
        """Handle pan changes."""
        if self._state.performance_monitoring:
            self._performance_metrics['pan_offset_x'] = offset.x
            self._performance_metrics['pan_offset_y'] = offset.y
            
    def _on_rotation_changed(self, angle: float):
        """Handle rotation changes."""
        if self._state.performance_monitoring:
            self._performance_metrics['rotation_angle'] = angle
            
    def _create_page_info_from_pdf(self, pdf_page, page_number: int):
        """Create page info from PDF page."""
        from .multipage import PageInfo
        from .coordinates import CoordinateSpace
        from ..utils.geometry import Size
        
        # Get page dimensions from PDF
        page_rect = pdf_page.getDisplayBox('/MediaBox')
        page_size = Size(page_rect[2] - page_rect[0], page_rect[3] - page_rect[1])
        
        # Create coordinate space for PDF page
        coordinate_space = CoordinateSpace(
            origin=Point(page_rect[0], page_rect[1]),
            scale=1.0,
            name=f"pdf_page_{page_number}"
        )
        
        return PageInfo(
            page_number=page_number,
            size=page_size,
            offset=Point(0, 0),
            coordinate_space=coordinate_space,
            pdf_page_ref=pdf_page
        )
        
    def _start_performance_monitoring(self):
        """Start performance monitoring."""
        # Implementation for performance monitoring
        pass
        
    def _stop_performance_monitoring(self):
        """Stop performance monitoring."""
        # Implementation to stop monitoring
        pass
        
    def _update_performance_metrics(self):
        """Update performance metrics."""
        current_time = time.time()
        
        # Collect metrics from all components
        if self._zoom_manager:
            zoom_metrics = self._zoom_manager.get_performance_metrics()
            self._performance_metrics.update(zoom_metrics)
            
        # Add timestamp
        self._performance_metrics['timestamp'] = current_time
        
        # Keep performance history
        self._performance_history.append(self._performance_metrics.copy())
        
        # Limit history size
        if len(self._performance_history) > 1000:
            self._performance_history.pop(0)
            
        # Emit performance update
        self.performance_update.emit(self._performance_metrics)
```

## 🧪 Testing Requirements

### 1. Integration Tests (`tests/integration/viewer/test_coordinate_mapping.py`)
```python
import pytest
from PyQt6.QtWidgets import QApplication, QWidget
from unittest.mock import Mock, patch

from src.torematrix.ui.viewer.integration import CoordinateSystemIntegrator
from src.torematrix.ui.viewer.multipage import MultiPageCoordinateSystem, PageInfo
from src.torematrix.utils.geometry import Point, Rect, Size

class TestCoordinateMapping:
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app
        
    @pytest.fixture
    def widget(self, app):
        """Create test widget."""
        return QWidget()
        
    @pytest.fixture
    def integrator(self, widget):
        """Create coordinate system integrator."""
        integrator = CoordinateSystemIntegrator()
        integrator.initialize(widget)
        return integrator
        
    def test_system_initialization(self, integrator):
        """Test coordinate system initialization."""
        assert integrator.is_initialized()
        assert integrator.get_viewport_manager() is not None
        assert integrator.get_multipage_system() is not None
        
    def test_multi_page_coordinate_mapping(self, integrator):
        """Test multi-page coordinate transformations."""
        multipage = integrator.get_multipage_system()
        
        # Add test pages
        page1 = PageInfo(
            page_number=1,
            size=Size(600, 800),
            offset=Point(0, 0),
            coordinate_space=Mock()
        )
        page2 = PageInfo(
            page_number=2,
            size=Size(600, 800),
            offset=Point(0, 820),
            coordinate_space=Mock()
        )
        
        multipage.add_page(page1)
        multipage.add_page(page2)
        
        # Test coordinate transformations
        test_point = Point(100, 100)
        viewer_point = multipage.document_to_viewer(test_point, 1)
        
        assert viewer_point is not None
        
    def test_pdf_integration(self, integrator):
        """Test PDF.js integration."""
        # Mock PDF document
        pdf_doc = Mock()
        pdf_doc.numPages = 2
        
        # Mock PDF pages
        page1 = Mock()
        page1.getDisplayBox.return_value = [0, 0, 600, 800]
        page2 = Mock()
        page2.getDisplayBox.return_value = [0, 0, 600, 800]
        
        pdf_doc.getPage.side_effect = [page1, page2]
        
        # Test PDF integration
        success = integrator.enable_pdf_integration(pdf_doc)
        assert success
        
    def test_coordinate_validation(self, integrator):
        """Test coordinate validation."""
        validator = integrator.get_validator()
        assert validator is not None
        
        # Run validation suite
        results = integrator.run_validation_suite()
        assert 'round_trip_tests' in results
        
    def test_performance_monitoring(self, integrator):
        """Test performance monitoring."""
        integrator.enable_performance_monitoring(True)
        
        # Simulate coordinate transformations
        test_point = Point(100, 100)
        integrator.transform_point(test_point, 'document', 'viewer', 1)
        
        metrics = integrator.get_performance_metrics()
        assert 'timestamp' in metrics
        
    def test_debug_mode(self, integrator):
        """Test debug mode functionality."""
        integrator.enable_debug_mode(True)
        
        debugger = integrator.get_debugger()
        assert debugger is not None
        assert debugger.is_debug_enabled()
```

### 2. Performance Tests (`tests/performance/viewer/test_coordinate_performance.py`)
```python
import pytest
import time
from typing import List
from unittest.mock import Mock

from src.torematrix.ui.viewer.integration import CoordinateSystemIntegrator
from src.torematrix.utils.geometry import Point

class TestCoordinatePerformance:
    @pytest.fixture
    def integrator(self):
        """Create integrator for performance testing."""
        integrator = CoordinateSystemIntegrator()
        widget = Mock()
        integrator.initialize(widget)
        return integrator
        
    def test_single_point_transformation_performance(self, integrator):
        """Test single point transformation performance."""
        test_point = Point(100, 100)
        
        # Warm up
        for _ in range(100):
            integrator.transform_point(test_point, 'document', 'viewer', 1)
            
        # Measure performance
        start_time = time.time()
        for _ in range(1000):
            integrator.transform_point(test_point, 'document', 'viewer', 1)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 1000
        assert avg_time < 0.001  # Less than 1ms per transformation
        
    def test_batch_transformation_performance(self, integrator):
        """Test batch transformation performance."""
        # Create test points
        test_points = []
        for i in range(10000):
            test_points.append((Point(i, i), 'document', 'viewer', 1))
            
        # Measure batch performance
        start_time = time.time()
        results = integrator.batch_transform_points(test_points)
        end_time = time.time()
        
        total_time = end_time - start_time
        assert total_time < 0.1  # Less than 100ms for 10k points
        assert len(results) == 10000
        
    def test_multi_page_performance(self, integrator):
        """Test multi-page coordinate performance."""
        multipage = integrator.get_multipage_system()
        
        # Add multiple pages
        for i in range(100):
            page = Mock()
            page.page_number = i
            page.size = Mock()
            page.offset = Point(0, i * 820)
            page.coordinate_space = Mock()
            multipage.add_page(page)
            
        # Test performance across pages
        start_time = time.time()
        for page_num in range(100):
            test_point = Point(100, 100)
            multipage.document_to_viewer(test_point, page_num)
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 100
        assert avg_time < 0.002  # Less than 2ms per page
        
    def test_memory_usage(self, integrator):
        """Test memory usage of coordinate system."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform many transformations
        for i in range(10000):
            test_point = Point(i, i)
            integrator.transform_point(test_point, 'document', 'viewer', 1)
            
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Should not increase memory by more than 50MB
        assert memory_increase < 50 * 1024 * 1024
```

## 🎯 Success Criteria

### Core Functionality
- [ ] Multi-page coordinate system implemented
- [ ] PDF.js integration working
- [ ] Debug visualization system operational
- [ ] Coordinate validation system functional
- [ ] Performance monitoring active
- [ ] Complete system integration

### Performance Requirements
- [ ] Multi-page transformations in <2ms
- [ ] PDF coordinate extraction in <100ms
- [ ] Debug overlay rendering in <16ms (60fps)
- [ ] Memory usage <200MB for 100-page document
- [ ] Validation suite runs in <1 second

### Production Readiness
- [ ] Comprehensive error handling
- [ ] Performance monitoring and alerting
- [ ] Complete API documentation
- [ ] Production deployment scripts
- [ ] Debugging and troubleshooting tools

## 🔗 Integration Points

### From All Previous Agents
- Agent 1: Core transformation engine and coordinate mapping
- Agent 2: Viewport management and screen coordinate conversion
- Agent 3: High-performance zoom, pan, and rotation optimization
- PDF.js Integration (#16): PDF document coordinate extraction
- Element Overlay System (#17): Coordinate-based element positioning

### For Production Deployment
- Complete coordinate mapping API
- Debug and monitoring tools
- Performance optimization framework
- Multi-page document support
- PDF.js integration bridge

## 📊 Performance Targets
- Multi-page coordinate mapping: <2ms per transformation
- PDF page coordinate extraction: <100ms per page
- Debug visualization: <16ms for 60fps rendering
- Validation suite: <1 second for complete run
- Memory usage: <200MB for 100-page document

## 🛠️ Development Workflow

### Phase 1: Multi-Page System (Days 5-6)
1. Implement multi-page coordinate system
2. Add PDF.js integration
3. Create page layout management
4. Add coordinate transformation APIs

### Phase 2: Integration & Production (Days 5-6)
1. Create debug visualization system
2. Add comprehensive validation
3. Implement performance monitoring
4. Complete system integration and testing

## 🚀 Getting Started

1. **Create your feature branch**: `git checkout -b feature/coordinates-integration-agent4-issue153`
2. **Verify branch**: `git branch --show-current`
3. **Start with multi-page system**: Build comprehensive page management
4. **Add PDF.js integration**: Connect with PDF document coordinates
5. **Create debug tools**: Build visualization and validation systems
6. **Complete integration**: Ensure all components work together
7. **Test thoroughly**: Run all integration and performance tests
8. **Document everything**: Complete API documentation

## 📝 Implementation Notes

### Key Architecture Decisions
- Multi-page coordinate system with layout management
- PDF.js integration for PDF document coordinates
- Debug visualization with real-time performance monitoring
- Comprehensive validation system for coordinate accuracy
- Production-ready error handling and monitoring

### Dependencies on Previous Agents
- Agent 1: Core coordinate transformation engine
- Agent 2: Viewport management and screen mapping
- Agent 3: High-performance optimization and caching
- PDF.js Integration: Document coordinate extraction
- Element Overlay System: Coordinate-based positioning

### Production Considerations
- Comprehensive error handling and recovery
- Performance monitoring and alerting
- Memory management for large documents
- Thread safety for concurrent operations
- API documentation and usage examples

## 🎯 Communication Protocol

- **Daily Progress**: Comment on Issue #153 with integration milestones
- **System Integration**: Report on component integration status
- **Performance**: Document performance benchmarks and optimization
- **Production**: Report on deployment readiness and monitoring
- **Blockers**: Tag @insult0o for immediate assistance

## 📚 Reference Materials

- [PDF.js API Documentation](https://mozilla.github.io/pdf.js/api/)
- [Qt Graphics System](https://doc.qt.io/qt-6/graphicsview.html)
- [Multi-Page Document Layout](https://developer.mozilla.org/en-US/docs/Web/API/Document_Object_Model)
- [Performance Monitoring Best Practices](https://docs.python.org/3/library/profile.html)
- [Debug Visualization Techniques](https://matplotlib.org/stable/tutorials/colors/colors.html)

**Good luck, Agent 4! You're completing the coordinate mapping system by bringing everything together into a production-ready, multi-page document viewer with comprehensive debugging and monitoring capabilities.**