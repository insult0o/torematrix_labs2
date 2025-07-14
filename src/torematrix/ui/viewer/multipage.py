"""
Multi-page coordinate system management.

This module provides comprehensive coordinate mapping for multi-page documents
with support for different layout modes and PDF.js integration.
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import math

try:
    from PyQt6.QtCore import QObject, pyqtSignal
    PyQt6_available = True
except ImportError:
    class QObject:
        pass
    def pyqtSignal(*args):
        return None
    PyQt6_available = False

from .coordinates import CoordinateMapper, CoordinateSpace
from .transformations import AffineTransformation
from .viewport import ViewportManager


@dataclass
class PageInfo:
    """Information about a document page."""
    page_number: int
    size: 'Size'
    offset: 'Point'
    coordinate_space: CoordinateSpace
    pdf_page_ref: Optional[Any] = None  # PDF.js page reference


@dataclass
class MultiPageState:
    """State of multi-page coordinate system."""
    pages: List[PageInfo]
    current_page: int
    page_spacing: float
    layout_mode: str  # 'single', 'continuous', 'spread'
    total_size: 'Size'


class MultiPageCoordinateSystem(QObject):
    """Manages coordinates across multiple document pages."""
    
    # Signals
    page_changed = pyqtSignal(int) if PyQt6_available else None
    layout_changed = pyqtSignal(str) if PyQt6_available else None
    coordinates_updated = pyqtSignal() if PyQt6_available else None
    
    def __init__(self, viewport_manager: ViewportManager):
        if PyQt6_available:
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
        if self.page_changed and PyQt6_available:
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
        if self.layout_changed and PyQt6_available:
            self.layout_changed.emit(mode)
        
    def get_layout_mode(self) -> str:
        """Get current layout mode."""
        return self._state.layout_mode
        
    def document_to_viewer(self, point: 'Point', page_number: int) -> Optional['Point']:
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
        
    def viewer_to_document(self, point: 'Point', page_number: int) -> Optional['Point']:
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
        
    def find_page_at_point(self, point: 'Point') -> Optional[int]:
        """Find which page contains the given viewer point."""
        for page_info in self._state.pages:
            page_bounds = self._get_page_bounds(page_info.page_number)
            if page_bounds and page_bounds.contains(point):
                return page_info.page_number
        return None
        
    def get_page_bounds(self, page_number: int) -> Optional['Rect']:
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
        
    def get_total_document_size(self) -> 'Size':
        """Get total document size across all pages."""
        return self._state.total_size
        
    def batch_transform_points(self, points: List[Tuple['Point', int]]) -> List[Optional['Point']]:
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
            
        if self.coordinates_updated and PyQt6_available:
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
            
    def _get_page_bounds(self, page_number: int) -> Optional['Rect']:
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


# Import geometry classes to support type hints
try:
    from ..utils.geometry import Point, Rect, Size
except ImportError:
    # Fallback classes for testing environment
    @dataclass
    class Point:
        x: float
        y: float
        
        def distance_to(self, other: 'Point') -> float:
            return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    @dataclass 
    class Rect:
        x: float
        y: float
        width: float
        height: float
        
        @property
        def center(self) -> Point:
            return Point(self.x + self.width / 2, self.y + self.height / 2)
        
        def contains(self, point: Point) -> bool:
            return (self.x <= point.x <= self.x + self.width and
                    self.y <= point.y <= self.y + self.height)
        
        def intersects(self, other: 'Rect') -> bool:
            return not (self.x + self.width < other.x or
                       other.x + other.width < self.x or
                       self.y + self.height < other.y or
                       other.y + other.height < self.y)
    
    @dataclass
    class Size:
        width: float
        height: float