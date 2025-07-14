# AGENT 2 COORDINATES - Viewport & Screen Mapping

## 🎯 Your Mission
You are **Agent 2** implementing the **Viewport & Screen Mapping** system for the Document Viewer Coordinate Mapping. You will build viewer-to-screen coordinate conversion, DPI awareness, and viewport management.

## 📋 Your Assignment
**Sub-Issue #150**: [Coordinate Mapping Sub-Issue #18.2: Viewport & Screen Mapping](https://github.com/insult0o/torematrix_labs2/issues/150)

## 🚀 What You're Building
A comprehensive viewport and screen mapping system with:
- Viewer-to-screen coordinate conversion
- DPI awareness and high-DPI support
- Viewport clipping and bounds management
- Multi-monitor coordinate handling

## 📁 Files to Create

### Primary Implementation Files
```
src/torematrix/ui/viewer/viewport.py
src/torematrix/ui/viewer/screen.py
```

### Test Files
```
tests/unit/viewer/test_viewport.py
tests/unit/viewer/test_screen.py
```

## 🔧 Technical Implementation Details

### 1. Viewport Management (`src/torematrix/ui/viewer/viewport.py`)
```python
from typing import Tuple, Optional, List, Dict, Any
from dataclasses import dataclass
from PyQt6.QtCore import QRect, QRectF, QPointF, QSizeF, pyqtSignal, QObject
from PyQt6.QtGui import QTransform
from PyQt6.QtWidgets import QWidget

from .coordinates import CoordinateMapper, CoordinateSpace
from .transformations import AffineTransformation
from ..utils.geometry import Point, Rect, Size

@dataclass
class ViewportBounds:
    """Defines viewport boundaries and clipping."""
    visible_rect: Rect
    document_rect: Rect
    scale_factor: float
    rotation: float = 0.0

class ViewportManager(QObject):
    """Manages viewport transformations and bounds."""
    
    # Signals
    viewport_changed = pyqtSignal(ViewportBounds)
    bounds_changed = pyqtSignal(Rect)
    
    def __init__(self, widget: QWidget):
        super().__init__()
        self.widget = widget
        self._coordinate_mapper: Optional[CoordinateMapper] = None
        self._viewport_bounds: Optional[ViewportBounds] = None
        self._clipping_enabled = True
        self._bounds_cache: Dict[str, Rect] = {}
        
    def set_coordinate_mapper(self, mapper: CoordinateMapper):
        """Set the coordinate mapper instance."""
        self._coordinate_mapper = mapper
        
    def update_viewport(self, visible_rect: Rect, document_rect: Rect, scale: float):
        """Update viewport boundaries and emit signals."""
        # Update viewport bounds with validation
        
    def viewer_to_screen(self, point: Point) -> Point:
        """Convert viewer coordinates to screen coordinates."""
        if not self._coordinate_mapper:
            raise ValueError("Coordinate mapper not set")
            
        # Get widget position and apply transformations
        widget_pos = self.widget.mapToGlobal(point.to_qpoint())
        return Point(widget_pos.x(), widget_pos.y())
        
    def screen_to_viewer(self, point: Point) -> Point:
        """Convert screen coordinates to viewer coordinates."""
        if not self._coordinate_mapper:
            raise ValueError("Coordinate mapper not set")
            
        # Map from global to widget coordinates
        widget_pos = self.widget.mapFromGlobal(point.to_qpoint())
        return Point(widget_pos.x(), widget_pos.y())
        
    def clip_to_viewport(self, rect: Rect) -> Optional[Rect]:
        """Clip rectangle to viewport bounds."""
        if not self._viewport_bounds or not self._clipping_enabled:
            return rect
            
        # Implement viewport clipping algorithm
        return rect.intersection(self._viewport_bounds.visible_rect)
        
    def is_visible(self, point: Point) -> bool:
        """Check if point is visible in viewport."""
        if not self._viewport_bounds:
            return True
            
        return self._viewport_bounds.visible_rect.contains(point)
        
    def is_rect_visible(self, rect: Rect) -> bool:
        """Check if rectangle intersects with viewport."""
        if not self._viewport_bounds:
            return True
            
        return self._viewport_bounds.visible_rect.intersects(rect)
        
    def get_visible_bounds(self) -> Optional[Rect]:
        """Get current visible bounds."""
        return self._viewport_bounds.visible_rect if self._viewport_bounds else None
        
    def get_document_bounds(self) -> Optional[Rect]:
        """Get current document bounds."""
        return self._viewport_bounds.document_rect if self._viewport_bounds else None
        
    def invalidate_bounds_cache(self):
        """Invalidate cached bounds."""
        self._bounds_cache.clear()
        
    def batch_clip_rects(self, rects: List[Rect]) -> List[Optional[Rect]]:
        """Batch clip multiple rectangles."""
        if not self._viewport_bounds or not self._clipping_enabled:
            return rects
            
        return [self.clip_to_viewport(rect) for rect in rects]

class ViewportTransformation:
    """Handles viewport-specific transformations."""
    
    def __init__(self, viewport_manager: ViewportManager):
        self.viewport_manager = viewport_manager
        self._transformation_cache: Dict[str, AffineTransformation] = {}
        
    def get_viewer_to_screen_transform(self) -> AffineTransformation:
        """Get transformation from viewer to screen coordinates."""
        # Calculate transformation matrix considering:
        # - Widget position
        # - Viewport offset
        # - Scale factor
        
    def get_screen_to_viewer_transform(self) -> AffineTransformation:
        """Get transformation from screen to viewer coordinates."""
        # Return inverse of viewer-to-screen transformation
        
    def transform_viewport_rect(self, rect: Rect) -> Rect:
        """Transform rectangle through viewport."""
        # Apply viewport transformation to rectangle
        
    def clear_cache(self):
        """Clear transformation cache."""
        self._transformation_cache.clear()
```

### 2. Screen Coordinate System (`src/torematrix/ui/viewer/screen.py`)
```python
from typing import Tuple, Optional, List, Dict
from dataclasses import dataclass
from PyQt6.QtCore import QRect, QPoint, QSize
from PyQt6.QtGui import QScreen, QGuiApplication
from PyQt6.QtWidgets import QWidget, QApplication

from ..utils.geometry import Point, Rect, Size

@dataclass
class ScreenInfo:
    """Screen information with DPI and geometry."""
    screen_id: str
    geometry: Rect
    dpi_x: float
    dpi_y: float
    scale_factor: float
    name: str

class ScreenCoordinateSystem:
    """Manages screen coordinate system and DPI awareness."""
    
    def __init__(self, widget: QWidget):
        self.widget = widget
        self._screen_info: Optional[ScreenInfo] = None
        self._dpi_scale_factor = 1.0
        self._screen_cache: Dict[str, ScreenInfo] = {}
        
    def update_screen_info(self):
        """Update screen information for current widget."""
        if not self.widget:
            return
            
        screen = self.widget.screen()
        if not screen:
            return
            
        geometry = screen.geometry()
        self._screen_info = ScreenInfo(
            screen_id=screen.name(),
            geometry=Rect(geometry.x(), geometry.y(), geometry.width(), geometry.height()),
            dpi_x=screen.logicalDotsPerInchX(),
            dpi_y=screen.logicalDotsPerInchY(),
            scale_factor=screen.devicePixelRatio(),
            name=screen.name()
        )
        
        self._dpi_scale_factor = screen.devicePixelRatio()
        
    def get_screen_info(self) -> Optional[ScreenInfo]:
        """Get current screen information."""
        if not self._screen_info:
            self.update_screen_info()
        return self._screen_info
        
    def apply_dpi_scaling(self, point: Point) -> Point:
        """Apply DPI scaling to point."""
        return Point(
            point.x * self._dpi_scale_factor,
            point.y * self._dpi_scale_factor
        )
        
    def remove_dpi_scaling(self, point: Point) -> Point:
        """Remove DPI scaling from point."""
        return Point(
            point.x / self._dpi_scale_factor,
            point.y / self._dpi_scale_factor
        )
        
    def get_screen_bounds(self) -> Optional[Rect]:
        """Get screen bounds."""
        if not self._screen_info:
            return None
        return self._screen_info.geometry
        
    def point_to_screen_space(self, point: Point) -> Point:
        """Convert point to screen space coordinates."""
        if not self.widget:
            return point
            
        # Map widget coordinates to global screen coordinates
        global_pos = self.widget.mapToGlobal(QPoint(int(point.x), int(point.y)))
        return Point(global_pos.x(), global_pos.y())
        
    def point_from_screen_space(self, point: Point) -> Point:
        """Convert point from screen space coordinates."""
        if not self.widget:
            return point
            
        # Map global screen coordinates to widget coordinates
        widget_pos = self.widget.mapFromGlobal(QPoint(int(point.x), int(point.y)))
        return Point(widget_pos.x(), widget_pos.y())
        
    def get_all_screens(self) -> List[ScreenInfo]:
        """Get information for all available screens."""
        screens = []
        for screen in QGuiApplication.screens():
            geometry = screen.geometry()
            screen_info = ScreenInfo(
                screen_id=screen.name(),
                geometry=Rect(geometry.x(), geometry.y(), geometry.width(), geometry.height()),
                dpi_x=screen.logicalDotsPerInchX(),
                dpi_y=screen.logicalDotsPerInchY(),
                scale_factor=screen.devicePixelRatio(),
                name=screen.name()
            )
            screens.append(screen_info)
        return screens
        
    def find_screen_for_point(self, point: Point) -> Optional[ScreenInfo]:
        """Find which screen contains the given point."""
        for screen_info in self.get_all_screens():
            if screen_info.geometry.contains(point):
                return screen_info
        return None
        
    def is_high_dpi(self) -> bool:
        """Check if current screen is high DPI."""
        return self._dpi_scale_factor > 1.0

class MultiMonitorCoordinateSystem:
    """Handles coordinate mapping across multiple monitors."""
    
    def __init__(self):
        self._primary_screen: Optional[ScreenInfo] = None
        self._screen_mapping: Dict[str, ScreenInfo] = {}
        
    def update_screen_mapping(self):
        """Update mapping of all available screens."""
        self._screen_mapping.clear()
        
        for screen in QGuiApplication.screens():
            geometry = screen.geometry()
            screen_info = ScreenInfo(
                screen_id=screen.name(),
                geometry=Rect(geometry.x(), geometry.y(), geometry.width(), geometry.height()),
                dpi_x=screen.logicalDotsPerInchX(),
                dpi_y=screen.logicalDotsPerInchY(),
                scale_factor=screen.devicePixelRatio(),
                name=screen.name()
            )
            self._screen_mapping[screen.name()] = screen_info
            
            # Set primary screen
            if screen == QGuiApplication.primaryScreen():
                self._primary_screen = screen_info
                
    def get_primary_screen(self) -> Optional[ScreenInfo]:
        """Get primary screen information."""
        if not self._primary_screen:
            self.update_screen_mapping()
        return self._primary_screen
        
    def convert_between_screens(self, point: Point, from_screen: str, to_screen: str) -> Point:
        """Convert point coordinates between different screens."""
        if from_screen == to_screen:
            return point
            
        from_info = self._screen_mapping.get(from_screen)
        to_info = self._screen_mapping.get(to_screen)
        
        if not from_info or not to_info:
            return point
            
        # Convert to global coordinates
        global_x = point.x + from_info.geometry.x
        global_y = point.y + from_info.geometry.y
        
        # Convert to target screen coordinates
        target_x = global_x - to_info.geometry.x
        target_y = global_y - to_info.geometry.y
        
        # Apply DPI scaling differences
        scale_ratio = to_info.scale_factor / from_info.scale_factor
        
        return Point(target_x * scale_ratio, target_y * scale_ratio)
        
    def get_screen_for_widget(self, widget: QWidget) -> Optional[ScreenInfo]:
        """Get screen information for a widget."""
        if not widget:
            return None
            
        screen = widget.screen()
        if not screen:
            return None
            
        return self._screen_mapping.get(screen.name())
```

## 🧪 Testing Requirements

### 1. Viewport Tests (`tests/unit/viewer/test_viewport.py`)
```python
import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QRect

from src.torematrix.ui.viewer.viewport import ViewportManager, ViewportBounds
from src.torematrix.utils.geometry import Point, Rect

class TestViewportManager:
    def test_viewport_bounds_update(self):
        """Test viewport bounds updating."""
        
    def test_viewer_to_screen_conversion(self):
        """Test viewer to screen coordinate conversion."""
        
    def test_screen_to_viewer_conversion(self):
        """Test screen to viewer coordinate conversion."""
        
    def test_viewport_clipping(self):
        """Test viewport clipping functionality."""
        
    def test_visibility_checks(self):
        """Test point and rectangle visibility checks."""
        
    def test_batch_clipping(self):
        """Test batch rectangle clipping."""
        
    def test_bounds_caching(self):
        """Test bounds caching mechanism."""
```

### 2. Screen Coordinate Tests (`tests/unit/viewer/test_screen.py`)
```python
import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtGui import QScreen

from src.torematrix.ui.viewer.screen import ScreenCoordinateSystem, MultiMonitorCoordinateSystem
from src.torematrix.utils.geometry import Point, Rect

class TestScreenCoordinateSystem:
    def test_dpi_scaling(self):
        """Test DPI scaling application and removal."""
        
    def test_screen_info_update(self):
        """Test screen information updating."""
        
    def test_screen_space_conversion(self):
        """Test screen space coordinate conversion."""
        
    def test_multi_monitor_support(self):
        """Test multi-monitor coordinate handling."""
        
    def test_high_dpi_detection(self):
        """Test high DPI screen detection."""
        
    def test_screen_bounds_calculation(self):
        """Test screen bounds calculation."""
```

## 🎯 Success Criteria

### Core Functionality
- [ ] ViewportManager with viewer-to-screen conversion
- [ ] ScreenCoordinateSystem with DPI awareness
- [ ] Viewport clipping and bounds management
- [ ] Multi-monitor coordinate support
- [ ] High-DPI screen handling

### Performance Requirements
- [ ] Viewport clipping of 1000+ rectangles in <50ms
- [ ] Screen coordinate conversion accuracy to 1 pixel
- [ ] DPI scaling maintains sub-pixel accuracy
- [ ] Multi-monitor conversion in <1ms

### Integration Requirements
- [ ] Seamless integration with Agent 1's coordinate mapper
- [ ] Qt widget system compatibility
- [ ] Thread-safe screen information updates
- [ ] Signal-based viewport change notifications

## 🔗 Integration Points

### From Agent 1 (Core Transformation Engine)
- Use `CoordinateMapper` for base transformations
- Utilize `AffineTransformation` for viewport transforms
- Apply `Point` and `Rect` geometric utilities

### For Agent 3 (Zoom, Pan & Rotation)
- Provide viewport bounds for optimization
- Supply screen coordinate conversion
- Export DPI-aware transformation methods

### For Agent 4 (Multi-Page Integration)
- Export complete viewport management API
- Provide multi-monitor coordinate system
- Supply screen information utilities

## 📊 Performance Targets
- Viewer-to-screen conversion: <0.5ms per point
- Viewport clipping: <50ms for 1000 rectangles
- Screen info update: <10ms for screen changes
- Multi-monitor conversion: <1ms per point

## 🛠️ Development Workflow

### Phase 1: Core Viewport (Days 3-4)
1. Implement ViewportManager class
2. Add viewer-to-screen coordinate conversion
3. Create viewport clipping algorithms
4. Add bounds management and caching

### Phase 2: Screen Integration (Days 3-4)
1. Implement ScreenCoordinateSystem
2. Add DPI awareness and scaling
3. Create multi-monitor support
4. Add comprehensive testing

## 🚀 Getting Started

1. **Create your feature branch**: `git checkout -b feature/coordinates-viewport-agent2-issue150`
2. **Verify branch**: `git branch --show-current`
3. **Start with viewport manager**: Build the core viewport system
4. **Add screen coordinates**: Implement DPI-aware screen mapping
5. **Create multi-monitor support**: Add multi-screen coordination
6. **Write comprehensive tests**: Test all coordinate conversions
7. **Optimize performance**: Ensure fast viewport operations

## 📝 Implementation Notes

### Key Architecture Decisions
- Qt widget integration for screen mapping
- Signal-based viewport change notifications
- Cached screen information for performance
- DPI-aware coordinate transformations
- Multi-monitor coordinate system support

### Dependencies on Agent 1
- `CoordinateMapper` for base coordinate transformations
- `AffineTransformation` for viewport transforms
- `Point`, `Rect` utilities for geometric operations
- Coordinate validation and caching framework

## 🎯 Communication Protocol

- **Daily Progress**: Comment on Issue #150 with progress updates
- **Agent 1 Integration**: Coordinate via main issue #18
- **Blockers**: Tag @insult0o for immediate assistance
- **Testing**: Report viewport and screen coordinate accuracy

## 📚 Reference Materials

- [Qt Screen API Documentation](https://doc.qt.io/qt-6/qscreen.html)
- [High DPI Support in Qt](https://doc.qt.io/qt-6/highdpi.html)
- [Multi-Monitor Coordinate Systems](https://docs.microsoft.com/en-us/windows/win32/gdi/multiple-display-monitors)
- [Viewport Clipping Algorithms](https://en.wikipedia.org/wiki/Sutherland%E2%80%93Hodgman_algorithm)

**Good luck, Agent 2! You're building the bridge between the core coordinate system and the real screen, enabling precise viewport management and multi-monitor support.**