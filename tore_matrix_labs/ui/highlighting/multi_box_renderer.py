#!/usr/bin/env python3
"""
Multi-Box Renderer for TORE Matrix Labs Highlighting System
Renders complex highlighting using multiple boxes for line wraps and formatting.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QTextCharFormat, QTextCursor, QPainter, QPen, QBrush
from PyQt5.QtWidgets import QTextEdit

from .highlight_style import HighlightStyle


class MultiBoxRenderer:
    """Renders complex highlighting using multiple boxes for line wraps and formatting."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.highlight_style = HighlightStyle()
        self.render_enabled = True
        self.debug_mode = False
        
        # State tracking
        self.active_text_highlights: Dict[str, List[Tuple[int, int]]] = {}  # widget_id -> [(start, end), ...]
        self.active_pdf_highlights: Dict[str, List[Dict[str, Any]]] = {}  # page -> [box_info, ...]
        
        self.logger.info("Multi-box renderer initialized")
    
    def set_style(self, highlight_style: HighlightStyle):
        """Set the highlighting style."""
        self.highlight_style = highlight_style
        self.logger.info("MULTI_BOX_RENDERER: Style updated")
    
    def render_text_highlight(self, text_widget: QTextEdit, text_start: int, text_end: int, 
                            highlight_type: str = 'active_highlight') -> bool:
        """Render highlighting in text widget with multi-box support."""
        try:
            if not self.render_enabled:
                return False
            
            # Get highlighting format
            highlight_format = self.highlight_style.get_text_format(highlight_type)
            
            # Get text cursor
            cursor = text_widget.textCursor()
            
            # Save current cursor position
            original_position = cursor.position()
            
            # Apply highlighting
            cursor.setPosition(text_start)
            cursor.setPosition(text_end, QTextCursor.KeepAnchor)
            cursor.mergeCharFormat(highlight_format)
            
            # Restore cursor position
            cursor.setPosition(original_position)
            text_widget.setTextCursor(cursor)
            
            # Track this highlight
            widget_id = id(text_widget)
            if widget_id not in self.active_text_highlights:
                self.active_text_highlights[widget_id] = []
            self.active_text_highlights[widget_id].append((text_start, text_end))
            
            self.logger.debug(f"MULTI_BOX_RENDERER: Applied text highlight {text_start}-{text_end} with type {highlight_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"MULTI_BOX_RENDERER: Error rendering text highlight: {e}")
            return False
    
    def render_pdf_highlight(self, pdf_viewer, boxes: List[Dict[str, Any]], 
                           page: int, highlight_type: str = 'active_highlight') -> bool:
        """Render highlighting in PDF viewer with multiple boxes."""
        try:
            if not self.render_enabled or not boxes:
                return False
            
            # Get highlighting style
            style = self.highlight_style.get_pdf_style(highlight_type)
            
            # Check if PDF viewer supports custom highlighting
            if hasattr(pdf_viewer, 'add_highlight_boxes'):
                # Use PDF viewer's native highlighting
                return pdf_viewer.add_highlight_boxes(boxes, page, style)
            
            elif hasattr(pdf_viewer, 'page_label'):
                # Use page label for highlighting
                return self._render_pdf_highlight_on_page_label(
                    pdf_viewer.page_label, boxes, page, style
                )
            
            else:
                # Fallback to basic highlighting
                return self._render_pdf_highlight_fallback(
                    pdf_viewer, boxes, page, style
                )
            
        except Exception as e:
            self.logger.error(f"MULTI_BOX_RENDERER: Error rendering PDF highlight: {e}")
            return False
    
    def _render_pdf_highlight_on_page_label(self, page_label, boxes: List[Dict[str, Any]], 
                                          page: int, style: Dict[str, Any]) -> bool:
        """Render highlighting on PDF page label."""
        try:
            if not hasattr(page_label, 'add_highlight_boxes'):
                return False
            
            # Convert boxes to page label format
            highlight_boxes = []
            for box in boxes:
                highlight_box = {
                    'x': box['x'],
                    'y': box['y'],
                    'width': box['width'],
                    'height': box['height'],
                    'color': style['background_color'],
                    'opacity': style['opacity'],
                    'border_color': style.get('border_color'),
                    'border_width': style.get('border_width', 0)
                }
                highlight_boxes.append(highlight_box)
            
            # Add highlights to page label
            page_label.add_highlight_boxes(highlight_boxes, page)
            
            # Track this highlight
            if page not in self.active_pdf_highlights:
                self.active_pdf_highlights[page] = []
            self.active_pdf_highlights[page].extend(highlight_boxes)
            
            self.logger.debug(f"MULTI_BOX_RENDERER: Applied PDF highlight with {len(boxes)} boxes on page {page}")
            return True
            
        except Exception as e:
            self.logger.error(f"MULTI_BOX_RENDERER: Error rendering on page label: {e}")
            return False
    
    def _render_pdf_highlight_fallback(self, pdf_viewer, boxes: List[Dict[str, Any]], 
                                     page: int, style: Dict[str, Any]) -> bool:
        """Fallback PDF highlighting method."""
        try:
            # Store highlight information for manual rendering
            if page not in self.active_pdf_highlights:
                self.active_pdf_highlights[page] = []
            
            for box in boxes:
                highlight_info = {
                    'x': box['x'],
                    'y': box['y'],
                    'width': box['width'],
                    'height': box['height'],
                    'style': style,
                    'type': 'fallback'
                }
                self.active_pdf_highlights[page].append(highlight_info)
            
            # Trigger PDF viewer update if possible
            if hasattr(pdf_viewer, 'update'):
                pdf_viewer.update()
            
            self.logger.debug(f"MULTI_BOX_RENDERER: Stored fallback highlight with {len(boxes)} boxes on page {page}")
            return True
            
        except Exception as e:
            self.logger.error(f"MULTI_BOX_RENDERER: Error in fallback rendering: {e}")
            return False
    
    def remove_text_highlight(self, text_widget: QTextEdit, text_start: int, text_end: int) -> bool:
        """Remove highlighting from text widget."""
        try:
            # Get default format
            default_format = QTextCharFormat()
            
            # Get text cursor
            cursor = text_widget.textCursor()
            
            # Save current cursor position
            original_position = cursor.position()
            
            # Remove highlighting
            cursor.setPosition(text_start)
            cursor.setPosition(text_end, QTextCursor.KeepAnchor)
            cursor.setCharFormat(default_format)
            
            # Restore cursor position
            cursor.setPosition(original_position)
            text_widget.setTextCursor(cursor)
            
            # Remove from tracking
            widget_id = id(text_widget)
            if widget_id in self.active_text_highlights:
                highlights = self.active_text_highlights[widget_id]
                self.active_text_highlights[widget_id] = [
                    (s, e) for s, e in highlights if not (s == text_start and e == text_end)
                ]
            
            self.logger.debug(f"MULTI_BOX_RENDERER: Removed text highlight {text_start}-{text_end}")
            return True
            
        except Exception as e:
            self.logger.error(f"MULTI_BOX_RENDERER: Error removing text highlight: {e}")
            return False
    
    def remove_pdf_highlight(self, pdf_viewer, boxes: List[Dict[str, Any]], page: int) -> bool:
        """Remove highlighting from PDF viewer."""
        try:
            if hasattr(pdf_viewer, 'remove_highlight_boxes'):
                # Use PDF viewer's native method
                return pdf_viewer.remove_highlight_boxes(boxes, page)
            
            elif hasattr(pdf_viewer, 'page_label') and hasattr(pdf_viewer.page_label, 'remove_highlight_boxes'):
                # Use page label method
                return pdf_viewer.page_label.remove_highlight_boxes(boxes, page)
            
            else:
                # Remove from tracking
                if page in self.active_pdf_highlights:
                    # Remove matching boxes
                    remaining_highlights = []
                    for existing_box in self.active_pdf_highlights[page]:
                        should_remove = False
                        for remove_box in boxes:
                            if (abs(existing_box['x'] - remove_box['x']) < 1 and
                                abs(existing_box['y'] - remove_box['y']) < 1 and
                                abs(existing_box['width'] - remove_box['width']) < 1 and
                                abs(existing_box['height'] - remove_box['height']) < 1):
                                should_remove = True
                                break
                        
                        if not should_remove:
                            remaining_highlights.append(existing_box)
                    
                    self.active_pdf_highlights[page] = remaining_highlights
                
                # Trigger PDF viewer update if possible
                if hasattr(pdf_viewer, 'update'):
                    pdf_viewer.update()
            
            self.logger.debug(f"MULTI_BOX_RENDERER: Removed PDF highlight with {len(boxes)} boxes on page {page}")
            return True
            
        except Exception as e:
            self.logger.error(f"MULTI_BOX_RENDERER: Error removing PDF highlight: {e}")
            return False
    
    def clear_text_highlights(self, text_widget: QTextEdit) -> bool:
        """Clear all text highlights from a text widget."""
        try:
            # Get all text and reset formatting
            cursor = text_widget.textCursor()
            cursor.select(QTextCursor.Document)
            cursor.setCharFormat(QTextCharFormat())
            
            # Clear tracking
            widget_id = id(text_widget)
            if widget_id in self.active_text_highlights:
                del self.active_text_highlights[widget_id]
            
            self.logger.debug("MULTI_BOX_RENDERER: Cleared all text highlights")
            return True
            
        except Exception as e:
            self.logger.error(f"MULTI_BOX_RENDERER: Error clearing text highlights: {e}")
            return False
    
    def clear_pdf_highlights(self, pdf_viewer) -> bool:
        """Clear all PDF highlights from a PDF viewer."""
        try:
            if hasattr(pdf_viewer, 'clear_all_highlights'):
                # Use PDF viewer's native method
                return pdf_viewer.clear_all_highlights()
            
            elif hasattr(pdf_viewer, 'page_label') and hasattr(pdf_viewer.page_label, 'clear_all_highlights'):
                # Use page label method
                return pdf_viewer.page_label.clear_all_highlights()
            
            else:
                # Clear tracking
                self.active_pdf_highlights.clear()
                
                # Trigger PDF viewer update if possible
                if hasattr(pdf_viewer, 'update'):
                    pdf_viewer.update()
            
            self.logger.debug("MULTI_BOX_RENDERER: Cleared all PDF highlights")
            return True
            
        except Exception as e:
            self.logger.error(f"MULTI_BOX_RENDERER: Error clearing PDF highlights: {e}")
            return False
    
    def show_cursor_location(self, pdf_viewer, pdf_coords: Dict[str, Any], page: int) -> bool:
        """Show cursor location in PDF viewer."""
        try:
            if hasattr(pdf_viewer, 'show_cursor_location'):
                return pdf_viewer.show_cursor_location(pdf_coords, page)
            
            elif hasattr(pdf_viewer, 'page_label') and hasattr(pdf_viewer.page_label, 'show_cursor_location'):
                return pdf_viewer.page_label.show_cursor_location(pdf_coords, page)
            
            else:
                # Fallback - create a small highlight at cursor position
                cursor_box = {
                    'x': pdf_coords['x'],
                    'y': pdf_coords['y'],
                    'width': 2,
                    'height': pdf_coords.get('height', 12),
                    'color': self.highlight_style.get_cursor_color(),
                    'opacity': 0.8,
                    'type': 'cursor'
                }
                
                return self._render_pdf_highlight_fallback(pdf_viewer, [cursor_box], page, {
                    'background_color': self.highlight_style.get_cursor_color(),
                    'opacity': 0.8
                })
            
        except Exception as e:
            self.logger.error(f"MULTI_BOX_RENDERER: Error showing cursor location: {e}")
            return False
    
    def render_multiline_selection(self, text_widget: QTextEdit, pdf_viewer, 
                                 text_start: int, text_end: int, page: int,
                                 coordinate_mapper) -> bool:
        """Render a multiline selection with synchronized highlighting."""
        try:
            # Render in text widget
            text_success = self.render_text_highlight(text_widget, text_start, text_end, 'active_highlight')
            
            # Get PDF coordinates
            pdf_boxes = coordinate_mapper.map_text_to_pdf(text_start, text_end, page)
            
            # Render in PDF viewer
            pdf_success = False
            if pdf_boxes:
                pdf_success = self.render_pdf_highlight(pdf_viewer, pdf_boxes, page, 'active_highlight')
            
            success = text_success and pdf_success
            self.logger.debug(f"MULTI_BOX_RENDERER: Multiline selection rendered - text: {text_success}, pdf: {pdf_success}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"MULTI_BOX_RENDERER: Error rendering multiline selection: {e}")
            return False
    
    def enable_rendering(self):
        """Enable rendering functionality."""
        self.render_enabled = True
        self.logger.info("MULTI_BOX_RENDERER: Rendering enabled")
    
    def disable_rendering(self):
        """Disable rendering functionality."""
        self.render_enabled = False
        self.logger.info("MULTI_BOX_RENDERER: Rendering disabled")
    
    def get_active_highlights(self) -> Dict[str, Any]:
        """Get information about active highlights."""
        return {
            'text_highlights': len(self.active_text_highlights),
            'pdf_highlights': {page: len(highlights) for page, highlights in self.active_pdf_highlights.items()},
            'total_pdf_highlights': sum(len(highlights) for highlights in self.active_pdf_highlights.values())
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get multi-box renderer statistics."""
        return {
            'render_enabled': self.render_enabled,
            'debug_mode': self.debug_mode,
            'active_text_widgets': len(self.active_text_highlights),
            'active_pdf_pages': len(self.active_pdf_highlights),
            'total_text_highlights': sum(len(highlights) for highlights in self.active_text_highlights.values()),
            'total_pdf_highlights': sum(len(highlights) for highlights in self.active_pdf_highlights.values())
        }
    
    def apply_highlights_to_pixmap(self, pixmap, highlights: Dict[str, Any], zoom_factor: float):
        """Apply highlights to a pixmap using pure yellow color scheme."""
        try:
            if not highlights:
                return pixmap
            
            # Create a painter to draw on the pixmap
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Set up pure yellow highlighting (no red outlines)
            brush = QBrush(QColor(255, 255, 0, 100))  # Pure yellow with transparency
            painter.setBrush(brush)
            painter.setPen(Qt.NoPen)  # No outline
            
            # Draw highlights
            for highlight_id, highlight_info in highlights.items():
                try:
                    pdf_boxes = highlight_info.get('pdf_boxes', [])
                    
                    for box in pdf_boxes:
                        if isinstance(box, (list, tuple)) and len(box) >= 4:
                            x0, y0, x1, y1 = box[:4]
                            
                            # Scale coordinates by zoom factor
                            x0 *= zoom_factor
                            y0 *= zoom_factor
                            x1 *= zoom_factor
                            y1 *= zoom_factor
                            
                            # Calculate rectangle dimensions
                            width = abs(x1 - x0)
                            height = abs(y1 - y0)
                            
                            # Draw the highlight rectangle
                            if width > 2 and height > 2:
                                painter.drawRect(int(x0), int(y0), int(width), int(height))
                                
                except Exception as e:
                    self.logger.warning(f"Error drawing highlight {highlight_id}: {e}")
                    continue
            
            painter.end()
            
            self.logger.debug(f"MULTI_BOX_RENDERER: Applied {len(highlights)} highlights to pixmap")
            return pixmap
            
        except Exception as e:
            self.logger.error(f"MULTI_BOX_RENDERER: Error applying highlights to pixmap: {e}")
            if 'painter' in locals():
                painter.end()
            return pixmap