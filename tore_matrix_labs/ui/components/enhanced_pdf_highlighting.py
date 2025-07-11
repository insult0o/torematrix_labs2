#!/usr/bin/env python3
"""
Enhanced PDF highlighting system with proper multi-line text selection support.
"""

import logging
import fitz  # PyMuPDF
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from ..qt_compat import QPixmap, QPainter, QPen, QBrush, QColor


@dataclass
class HighlightRectangle:
    """Represents a single highlight rectangle."""
    x: float
    y: float
    width: float
    height: float
    line_number: int = 0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'line_number': self.line_number
        }


@dataclass
class MultiLineHighlight:
    """Represents a multi-line highlight with multiple rectangles."""
    rectangles: List[HighlightRectangle]
    original_bbox: List[float]
    text_content: str = ""
    color: Tuple[int, int, int, int] = (255, 255, 0, 180)  # Default yellow
    border_color: Tuple[int, int, int, int] = (255, 0, 0, 255)  # Default red
    border_width: int = 2
    
    def add_rectangle(self, rect: HighlightRectangle):
        """Add a rectangle to the highlight."""
        self.rectangles.append(rect)
    
    def get_total_area(self) -> float:
        """Calculate total highlighted area."""
        return sum(rect.width * rect.height for rect in self.rectangles)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'rectangles': [rect.to_dict() for rect in self.rectangles],
            'original_bbox': self.original_bbox,
            'text_content': self.text_content,
            'total_rectangles': len(self.rectangles)
        }


class EnhancedPDFHighlighter:
    """Enhanced PDF highlighter with multi-line text selection support."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.line_height_threshold = 5  # Minimum line height difference to consider separate lines
        self.line_spacing_threshold = 10  # Maximum vertical gap between lines to group them
    
    def create_multiline_highlight(self, document: fitz.Document, page_num: int, 
                                 bbox: List[float], search_text: str = "") -> MultiLineHighlight:
        """
        Create a multi-line highlight by analyzing the text structure within the bbox.
        
        Args:
            document: PyMuPDF document
            page_num: Page number (0-based)
            bbox: Bounding box [x0, y0, x1, y1]
            search_text: Text to search for (optional)
            
        Returns:
            MultiLineHighlight object with proper rectangles
        """
        self.logger.info(f"Creating multi-line highlight for bbox {bbox} on page {page_num}")
        
        highlight = MultiLineHighlight(rectangles=[], original_bbox=bbox, text_content=search_text)
        
        try:
            page = document[page_num]
            
            if search_text:
                # Method 1: Search for specific text and get its precise rectangles
                rectangles = self._get_text_rectangles_by_search(page, search_text, bbox)
            else:
                # Method 2: Analyze text within bbox area and create line-by-line rectangles
                rectangles = self._get_text_rectangles_by_area(page, bbox)
            
            # Convert to HighlightRectangle objects
            for i, rect_data in enumerate(rectangles):
                rect = HighlightRectangle(
                    x=rect_data['x'],
                    y=rect_data['y'],
                    width=rect_data['width'],
                    height=rect_data['height'],
                    line_number=rect_data.get('line_number', i)
                )
                highlight.add_rectangle(rect)
            
            if not highlight.rectangles:
                # Fallback: Create single rectangle from original bbox
                self.logger.warning("No text rectangles found, using fallback single rectangle")
                rect = HighlightRectangle(
                    x=bbox[0],
                    y=bbox[1],
                    width=bbox[2] - bbox[0],
                    height=bbox[3] - bbox[1],
                    line_number=0
                )
                highlight.add_rectangle(rect)
            
            self.logger.info(f"Created multi-line highlight with {len(highlight.rectangles)} rectangles")
            return highlight
            
        except Exception as e:
            self.logger.error(f"Error creating multi-line highlight: {e}")
            # Return fallback single rectangle
            rect = HighlightRectangle(
                x=bbox[0],
                y=bbox[1], 
                width=bbox[2] - bbox[0],
                height=bbox[3] - bbox[1],
                line_number=0
            )
            highlight.add_rectangle(rect)
            return highlight
    
    def _get_text_rectangles_by_search(self, page: fitz.Page, search_text: str, 
                                     bbox: List[float]) -> List[Dict[str, Any]]:
        """Get precise rectangles by searching for specific text."""
        rectangles = []
        
        # Search for text instances
        text_instances = page.search_for(search_text)
        
        if not text_instances:
            # Try case-insensitive search
            text_instances = page.search_for(search_text, flags=fitz.TEXT_DEHYPHENATE)
        
        for instance in text_instances:
            # Check if this instance overlaps with our target bbox
            if self._rectangles_overlap(instance, bbox):
                # Get the actual text rectangles for this instance
                instance_rects = self._break_rectangle_into_lines(page, instance)
                rectangles.extend(instance_rects)
        
        return rectangles
    
    def _get_text_rectangles_by_area(self, page: fitz.Page, bbox: List[float]) -> List[Dict[str, Any]]:
        """Get rectangles by analyzing text structure within the bbox area."""
        rectangles = []
        
        # Get text with character-level details
        text_dict = page.get_text("dict")
        
        for block in text_dict["blocks"]:
            if "lines" not in block:
                continue
                
            for line in block["lines"]:
                line_bbox = line["bbox"]
                
                # Check if this line intersects with our target bbox
                if self._rectangles_overlap(line_bbox, bbox):
                    # Create rectangle for the intersection
                    intersection = self._get_intersection(line_bbox, bbox)
                    
                    if intersection and intersection[2] > intersection[0] and intersection[3] > intersection[1]:
                        rect_data = {
                            'x': intersection[0],
                            'y': intersection[1],
                            'width': intersection[2] - intersection[0],
                            'height': intersection[3] - intersection[1],
                            'line_number': len(rectangles)
                        }
                        rectangles.append(rect_data)
        
        # If no text found, create line-by-line rectangles based on estimated line height
        if not rectangles:
            rectangles = self._create_estimated_line_rectangles(bbox)
        
        return rectangles
    
    def _break_rectangle_into_lines(self, page: fitz.Page, rect: fitz.Rect) -> List[Dict[str, Any]]:
        """Break a rectangle into separate line rectangles based on text structure."""
        rectangles = []
        
        # Get text blocks within this rectangle
        text_dict = page.get_text("dict", clip=rect)
        
        for block in text_dict["blocks"]:
            if "lines" not in block:
                continue
                
            for line_num, line in enumerate(block["lines"]):
                line_bbox = line["bbox"]
                
                # Create rectangle for this line
                rect_data = {
                    'x': line_bbox[0],
                    'y': line_bbox[1],
                    'width': line_bbox[2] - line_bbox[0],
                    'height': line_bbox[3] - line_bbox[1],
                    'line_number': line_num
                }
                rectangles.append(rect_data)
        
        return rectangles
    
    def _create_estimated_line_rectangles(self, bbox: List[float]) -> List[Dict[str, Any]]:
        """Create estimated line rectangles when text analysis fails."""
        rectangles = []
        
        x0, y0, x1, y1 = bbox
        total_height = y1 - y0
        width = x1 - x0
        
        # Force minimum line height for visibility
        min_line_height = 12  # Minimum readable text size
        
        # Calculate number of lines based on height
        num_lines = max(1, int(total_height / min_line_height))
        actual_line_height = total_height / num_lines
        
        # Create rectangles for each estimated line
        for line_number in range(num_lines):
            current_y = y0 + (line_number * actual_line_height)
            
            rect_data = {
                'x': x0,
                'y': current_y,
                'width': width,
                'height': actual_line_height,
                'line_number': line_number
            }
            rectangles.append(rect_data)
        
        self.logger.info(f"Created {len(rectangles)} estimated line rectangles for bbox {bbox}")
        return rectangles
    
    def _rectangles_overlap(self, rect1: Any, rect2: Any) -> bool:
        """Check if two rectangles overlap."""
        # Convert to consistent format
        if hasattr(rect1, 'x0'):  # fitz.Rect
            r1 = [rect1.x0, rect1.y0, rect1.x1, rect1.y1]
        else:
            r1 = list(rect1)
            
        if hasattr(rect2, 'x0'):  # fitz.Rect
            r2 = [rect2.x0, rect2.y0, rect2.x1, rect2.y1]
        else:
            r2 = list(rect2)
        
        # Check overlap
        return not (r1[2] < r2[0] or r1[0] > r2[2] or r1[3] < r2[1] or r1[1] > r2[3])
    
    def _get_intersection(self, rect1: Any, rect2: Any) -> Optional[List[float]]:
        """Get intersection of two rectangles."""
        # Convert to consistent format
        if hasattr(rect1, 'x0'):  # fitz.Rect
            r1 = [rect1.x0, rect1.y0, rect1.x1, rect1.y1]
        else:
            r1 = list(rect1)
            
        if hasattr(rect2, 'x0'):  # fitz.Rect
            r2 = [rect2.x0, rect2.y0, rect2.x1, rect2.y1]
        else:
            r2 = list(rect2)
        
        # Calculate intersection
        x0 = max(r1[0], r2[0])
        y0 = max(r1[1], r2[1])
        x1 = min(r1[2], r2[2])
        y1 = min(r1[3], r2[3])
        
        if x1 > x0 and y1 > y0:
            return [x0, y0, x1, y1]
        return None
    
    def draw_multiline_highlight(self, qpixmap: QPixmap, highlight: MultiLineHighlight, 
                               zoom_factor: float) -> QPixmap:
        """Draw multi-line highlight on QPixmap with type-specific colors."""
        try:
            painter = QPainter(qpixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Set up highlighting style using colors from highlight object
            border_color = QColor(*highlight.border_color)
            fill_color = QColor(*highlight.color)
            pen = QPen(border_color, highlight.border_width)
            brush = QBrush(fill_color)
            
            painter.setPen(pen)
            painter.setBrush(brush)
            
            # Draw each rectangle
            for i, rect in enumerate(highlight.rectangles):
                # Scale coordinates by zoom factor
                scaled_x = rect.x * zoom_factor
                scaled_y = rect.y * zoom_factor
                scaled_width = rect.width * zoom_factor
                scaled_height = rect.height * zoom_factor
                
                # Ensure minimum size for visibility
                min_size = 2
                if scaled_width < min_size:
                    scaled_width = min_size
                if scaled_height < min_size:
                    scaled_height = min_size
                
                # Draw rectangle
                painter.drawRect(int(scaled_x), int(scaled_y), 
                               int(scaled_width), int(scaled_height))
                
                self.logger.debug(f"Drew rectangle {i}: ({scaled_x:.1f}, {scaled_y:.1f}) "
                                f"size ({scaled_width:.1f}, {scaled_height:.1f}) "
                                f"color {highlight.color}")
            
            # Draw additional outline for better visibility (optional)
            if highlight.border_width > 1:
                outline_pen = QPen(QColor(0, 0, 0, 100), 1)
                painter.setPen(outline_pen)
                painter.setBrush(QBrush())  # No fill
                
                for rect in highlight.rectangles:
                    scaled_x = rect.x * zoom_factor
                    scaled_y = rect.y * zoom_factor
                    scaled_width = rect.width * zoom_factor
                    scaled_height = rect.height * zoom_factor
                    
                    painter.drawRect(int(scaled_x - 1), int(scaled_y - 1), 
                                   int(scaled_width + 2), int(scaled_height + 2))
            
            painter.end()
            
            self.logger.info(f"Successfully drew multi-line highlight with {len(highlight.rectangles)} rectangles "
                           f"using colors: fill={highlight.color}, border={highlight.border_color}")
            return qpixmap
            
        except Exception as e:
            self.logger.error(f"Error drawing multi-line highlight: {e}")
            if 'painter' in locals():
                painter.end()
            return qpixmap


class HighlightCache:
    """Cache for storing computed highlights to improve performance."""
    
    def __init__(self, max_size: int = 100):
        self.cache: Dict[str, MultiLineHighlight] = {}
        self.max_size = max_size
        self.access_order: List[str] = []
    
    def get_cache_key(self, page_num: int, bbox: List[float], search_text: str) -> str:
        """Generate cache key for highlight."""
        return f"p{page_num}_b{bbox[0]:.1f},{bbox[1]:.1f},{bbox[2]:.1f},{bbox[3]:.1f}_t{hash(search_text)}"
    
    def get(self, page_num: int, bbox: List[float], search_text: str) -> Optional[MultiLineHighlight]:
        """Get cached highlight."""
        key = self.get_cache_key(page_num, bbox, search_text)
        
        if key in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        
        return None
    
    def put(self, page_num: int, bbox: List[float], search_text: str, highlight: MultiLineHighlight):
        """Store highlight in cache."""
        key = self.get_cache_key(page_num, bbox, search_text)
        
        # Remove oldest if cache is full
        if len(self.cache) >= self.max_size and key not in self.cache:
            oldest_key = self.access_order.pop(0)
            del self.cache[oldest_key]
        
        # Add/update cache
        if key in self.cache:
            self.access_order.remove(key)
        
        self.cache[key] = highlight
        self.access_order.append(key)
    
    def clear(self):
        """Clear cache."""
        self.cache.clear()
        self.access_order.clear()


# Global highlighter instance
_highlighter = EnhancedPDFHighlighter()
_highlight_cache = HighlightCache()


def create_multiline_highlight(document: fitz.Document, page_num: int, 
                             bbox: List[float], search_text: str = "",
                             color: Tuple[int, int, int, int] = (255, 255, 0, 180),
                             border_color: Tuple[int, int, int, int] = (255, 0, 0, 255),
                             border_width: int = 2) -> MultiLineHighlight:
    """Create a multi-line highlight (convenience function)."""
    # Check cache first (cache key includes colors)
    cache_key = f"{page_num}_{bbox}_{search_text}_{color}_{border_color}_{border_width}"
    cached = _highlight_cache.get(page_num, bbox, cache_key)
    if cached:
        return cached
    
    # Create new highlight
    highlight = _highlighter.create_multiline_highlight(document, page_num, bbox, search_text)
    
    # Apply color scheme
    if hasattr(highlight, 'color'):
        highlight.color = color
    if hasattr(highlight, 'border_color'):
        highlight.border_color = border_color
    if hasattr(highlight, 'border_width'):
        highlight.border_width = border_width
    
    # Cache result
    _highlight_cache.put(page_num, bbox, cache_key, highlight)
    
    return highlight


def draw_multiline_highlight(qpixmap: QPixmap, highlight: MultiLineHighlight, zoom_factor: float) -> QPixmap:
    """Draw multi-line highlight on QPixmap (convenience function)."""
    return _highlighter.draw_multiline_highlight(qpixmap, highlight, zoom_factor)