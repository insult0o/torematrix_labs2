#!/usr/bin/env python3
"""
Advanced Highlighting Engine for TORE Matrix Labs
Provides precise, multi-box text highlighting with perfect synchronization.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import uuid

from .coordinate_mapper import CoordinateMapper
from .multi_box_renderer import MultiBoxRenderer
from .position_tracker import PositionTracker
from .highlight_style import HighlightStyle
from .test_harness import HighlightingTestHarness


class HighlightingEngine:
    """Central coordinator for all highlighting operations."""
    
    def __init__(self, pdf_viewer=None, text_widget=None):
        self.pdf_viewer = pdf_viewer
        self.text_widget = text_widget
        self.logger = logging.getLogger(__name__)
        
        # Core components
        self.coordinate_mapper = CoordinateMapper()
        self.multi_box_renderer = MultiBoxRenderer()
        self.position_tracker = PositionTracker()
        self.highlight_style = HighlightStyle()
        self.test_harness = HighlightingTestHarness()
        
        # State management
        self.active_highlights: Dict[str, Dict[str, Any]] = {}
        self.current_page = 1
        self.is_enabled = True
        
        # Initialize components
        self._initialize_components()
        
        self.logger.info("Highlighting engine initialized")
    
    def _initialize_components(self):
        """Initialize all highlighting components."""
        try:
            # Configure coordinate mapper
            if self.pdf_viewer:
                self.coordinate_mapper.set_pdf_viewer(self.pdf_viewer)
            
            if self.text_widget:
                self.coordinate_mapper.set_text_widget(self.text_widget)
            
            # Configure multi-box renderer
            self.multi_box_renderer.set_style(self.highlight_style)
            
            # Configure position tracker
            self.position_tracker.set_engine(self)
            
            # Set up event connections
            self._setup_event_connections()
            
        except Exception as e:
            self.logger.error(f"HIGHLIGHTING_ENGINE: Error initializing components: {e}")
    
    def _setup_event_connections(self):
        """Set up event connections between components."""
        try:
            # Connect position tracker events
            if self.text_widget:
                # Connect cursor position changes
                if hasattr(self.text_widget, 'cursorPositionChanged'):
                    self.text_widget.cursorPositionChanged.connect(
                        self.position_tracker.on_cursor_position_changed
                    )
                
                # Connect selection changes
                if hasattr(self.text_widget, 'selectionChanged'):
                    self.text_widget.selectionChanged.connect(
                        self.position_tracker.on_selection_changed
                    )
            
            self.logger.info("HIGHLIGHTING_ENGINE: Event connections established")
            
        except Exception as e:
            self.logger.error(f"HIGHLIGHTING_ENGINE: Error setting up event connections: {e}")
    
    def set_pdf_viewer(self, pdf_viewer):
        """Set the PDF viewer for highlighting."""
        self.pdf_viewer = pdf_viewer
        self.coordinate_mapper.set_pdf_viewer(pdf_viewer)
        self.logger.info("HIGHLIGHTING_ENGINE: PDF viewer set")
    
    def set_text_widget(self, text_widget):
        """Set the text widget for highlighting."""
        self.text_widget = text_widget
        self.coordinate_mapper.set_text_widget(text_widget)
        self._setup_event_connections()
        self.logger.info("HIGHLIGHTING_ENGINE: Text widget set")
    
    def update_text_content(self, page: int = None):
        """Update coordinate mapping when text content changes."""
        try:
            if not self.coordinate_mapper:
                self.logger.warning("HIGHLIGHTING_ENGINE: No coordinate mapper available")
                return
            
            # Use current page if not specified
            if page is None:
                page = self.current_page
            
            self.logger.info(f"HIGHLIGHTING_ENGINE: Updating coordinate mapping for page {page}")
            
            # Rebuild coordinate maps for the new text content
            self.coordinate_mapper.rebuild_maps()
            
            # Clear any existing highlights that might be invalid
            page_highlights = [hid for hid, hinfo in self.active_highlights.items() 
                             if hinfo['page'] == page and hinfo.get('type') == 'active_highlight']
            
            for highlight_id in page_highlights:
                self.clear_highlight(highlight_id)
            
            self.logger.info(f"HIGHLIGHTING_ENGINE: Text content updated for page {page}, cleared {len(page_highlights)} text highlights")
            
        except Exception as e:
            self.logger.error(f"HIGHLIGHTING_ENGINE: Error updating text content: {e}")
    
    def highlight_text_range(self, text_start: int, text_end: int, 
                           highlight_type: str = 'active_highlight',
                           page: int = None) -> str:
        """Highlight a range of text with multi-box rendering."""
        try:
            if not self.is_enabled:
                return None
            
            # Generate unique highlight ID
            highlight_id = f"highlight_{uuid.uuid4().hex[:8]}"
            
            # Use current page if not specified
            if page is None:
                page = self.current_page
            
            self.logger.info(f"HIGHLIGHTING_ENGINE: Creating highlight {highlight_id} for text range {text_start}-{text_end} on page {page}")
            
            # Get coordinate mapping for the text range
            pdf_boxes = self.coordinate_mapper.map_text_to_pdf(text_start, text_end, page)
            
            if not pdf_boxes:
                self.logger.warning(f"HIGHLIGHTING_ENGINE: No PDF coordinates found for text range {text_start}-{text_end}")
                return None
            
            # Create highlight info
            highlight_info = {
                'id': highlight_id,
                'text_start': text_start,
                'text_end': text_end,
                'page': page,
                'type': highlight_type,
                'pdf_boxes': pdf_boxes,
                'created_at': datetime.now().isoformat(),
                'active': True
            }
            
            # Store highlight
            self.active_highlights[highlight_id] = highlight_info
            
            # Render in text widget
            if self.text_widget:
                self.multi_box_renderer.render_text_highlight(
                    self.text_widget, text_start, text_end, highlight_type
                )
            
            # Render in PDF viewer
            if self.pdf_viewer:
                self.multi_box_renderer.render_pdf_highlight(
                    self.pdf_viewer, pdf_boxes, page, highlight_type
                )
            
            # Track position
            self.position_tracker.track_highlight(highlight_id, highlight_info)
            
            self.logger.info(f"HIGHLIGHTING_ENGINE: Successfully created highlight {highlight_id}")
            return highlight_id
            
        except Exception as e:
            self.logger.error(f"HIGHLIGHTING_ENGINE: Error creating highlight: {e}")
            return None
    
    def remove_highlight(self, highlight_id: str) -> bool:
        """Remove a specific highlight."""
        try:
            if highlight_id not in self.active_highlights:
                self.logger.warning(f"HIGHLIGHTING_ENGINE: Highlight {highlight_id} not found")
                return False
            
            highlight_info = self.active_highlights[highlight_id]
            
            # Remove from text widget
            if self.text_widget:
                self.multi_box_renderer.remove_text_highlight(
                    self.text_widget, highlight_info['text_start'], highlight_info['text_end']
                )
            
            # Remove from PDF viewer
            if self.pdf_viewer:
                self.multi_box_renderer.remove_pdf_highlight(
                    self.pdf_viewer, highlight_info['pdf_boxes'], highlight_info['page']
                )
            
            # Remove from tracking
            self.position_tracker.untrack_highlight(highlight_id)
            
            # Remove from active highlights
            del self.active_highlights[highlight_id]
            
            self.logger.info(f"HIGHLIGHTING_ENGINE: Removed highlight {highlight_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"HIGHLIGHTING_ENGINE: Error removing highlight: {e}")
            return False
    
    def clear_all_highlights(self) -> bool:
        """Clear all active highlights."""
        try:
            highlight_ids = list(self.active_highlights.keys())
            
            for highlight_id in highlight_ids:
                self.remove_highlight(highlight_id)
            
            self.logger.info(f"HIGHLIGHTING_ENGINE: Cleared {len(highlight_ids)} highlights")
            return True
            
        except Exception as e:
            self.logger.error(f"HIGHLIGHTING_ENGINE: Error clearing highlights: {e}")
            return False
    
    def update_page(self, page: int):
        """Update current page and refresh highlights."""
        try:
            self.current_page = page
            
            # Clear existing highlights
            if self.text_widget:
                self.multi_box_renderer.clear_text_highlights(self.text_widget)
            
            if self.pdf_viewer:
                self.multi_box_renderer.clear_pdf_highlights(self.pdf_viewer)
            
            # Re-render highlights for current page
            page_highlights = {
                hid: hinfo for hid, hinfo in self.active_highlights.items() 
                if hinfo['page'] == page
            }
            
            for highlight_id, highlight_info in page_highlights.items():
                # Re-render in text widget
                if self.text_widget:
                    self.multi_box_renderer.render_text_highlight(
                        self.text_widget, 
                        highlight_info['text_start'], 
                        highlight_info['text_end'], 
                        highlight_info['type']
                    )
                
                # Re-render in PDF viewer
                if self.pdf_viewer:
                    self.multi_box_renderer.render_pdf_highlight(
                        self.pdf_viewer, 
                        highlight_info['pdf_boxes'], 
                        page, 
                        highlight_info['type']
                    )
            
            self.logger.info(f"HIGHLIGHTING_ENGINE: Updated to page {page}, refreshed {len(page_highlights)} highlights")
            
        except Exception as e:
            self.logger.error(f"HIGHLIGHTING_ENGINE: Error updating page: {e}")
    
    def sync_cursor_position(self, text_position: int):
        """Synchronize cursor position between text and PDF."""
        try:
            if not self.is_enabled:
                return
            
            # Get PDF coordinates for text position
            pdf_coords = self.coordinate_mapper.map_text_to_pdf(
                text_position, text_position + 1, self.current_page
            )
            
            if pdf_coords and self.pdf_viewer:
                # Show cursor location in PDF
                self.multi_box_renderer.show_cursor_location(
                    self.pdf_viewer, pdf_coords[0], self.current_page
                )
            
            # Update position tracker
            self.position_tracker.track_cursor_position(text_position)
            
        except Exception as e:
            self.logger.error(f"HIGHLIGHTING_ENGINE: Error syncing cursor position: {e}")
    
    def get_highlight_info(self, highlight_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific highlight."""
        return self.active_highlights.get(highlight_id)
    
    def get_active_highlights(self) -> Dict[str, Dict[str, Any]]:
        """Get all active highlights."""
        return self.active_highlights.copy()
    
    def enable_highlighting(self):
        """Enable highlighting functionality."""
        self.is_enabled = True
        self.logger.info("HIGHLIGHTING_ENGINE: Highlighting enabled")
    
    def disable_highlighting(self):
        """Disable highlighting functionality."""
        self.is_enabled = False
        self.logger.info("HIGHLIGHTING_ENGINE: Highlighting disabled")
    
    def run_accuracy_tests(self) -> Dict[str, Any]:
        """Run accuracy tests on the highlighting system."""
        try:
            return self.test_harness.run_accuracy_tests(self)
        except Exception as e:
            self.logger.error(f"HIGHLIGHTING_ENGINE: Error running accuracy tests: {e}")
            return {'status': 'error', 'message': str(e)}
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get highlighting engine statistics."""
        return {
            'active_highlights': len(self.active_highlights),
            'current_page': self.current_page,
            'is_enabled': self.is_enabled,
            'has_pdf_viewer': self.pdf_viewer is not None,
            'has_text_widget': self.text_widget is not None,
            'coordinate_mapper_stats': self.coordinate_mapper.get_statistics(),
            'position_tracker_stats': self.position_tracker.get_statistics()
        }
    
    def has_highlights(self) -> bool:
        """Check if there are any active highlights."""
        return len(self.active_highlights) > 0
    
    def clear_highlights(self):
        """Clear all highlights (alias for clear_all_highlights)."""
        self.clear_all_highlights()
    
    def highlight_area(self, page_number: int, bbox, search_text: str = None, highlight_type: str = "issue"):
        """Highlight a specific area on a page."""
        try:
            if not self.is_enabled:
                return
            
            # Generate unique highlight ID
            highlight_id = f"area_{uuid.uuid4().hex[:8]}"
            
            self.logger.info(f"HIGHLIGHTING_ENGINE: Creating area highlight {highlight_id} for page {page_number}")
            
            # Convert bbox to proper format
            if isinstance(bbox, dict) and 'regions' in bbox:
                # Enhanced coordinate data with multi-line support
                pdf_boxes = bbox['regions']
            elif isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                # Simple bbox format
                pdf_boxes = [bbox]
            else:
                self.logger.warning(f"Invalid bbox format: {bbox}")
                return
            
            # Create highlight info
            highlight_info = {
                'id': highlight_id,
                'page': page_number,
                'type': highlight_type,
                'bbox': bbox,
                'search_text': search_text,
                'pdf_boxes': pdf_boxes,
                'created_at': datetime.now().isoformat(),
                'active': True
            }
            
            # Store highlight
            self.active_highlights[highlight_id] = highlight_info
            
            # Render in PDF viewer
            if self.pdf_viewer:
                self.multi_box_renderer.render_pdf_highlight(
                    self.pdf_viewer, pdf_boxes, page_number, highlight_type
                )
            
            self.logger.info(f"HIGHLIGHTING_ENGINE: Successfully created area highlight {highlight_id}")
            return highlight_id
            
        except Exception as e:
            self.logger.error(f"HIGHLIGHTING_ENGINE: Error creating area highlight: {e}")
            return None
    
    def update_current_page(self, page_number: int):
        """Update the current page number for proper highlight filtering."""
        self.current_page = page_number
        self.logger.debug(f"HIGHLIGHTING_ENGINE: Current page updated to {page_number}")
    
    def apply_highlights_to_pixmap(self, pixmap, zoom_factor: float):
        """Apply highlights to a pixmap."""
        try:
            if not self.has_highlights():
                return pixmap
            
            # Get PDF viewer's current page if available
            if self.pdf_viewer and hasattr(self.pdf_viewer, 'current_page'):
                pdf_current_page = self.pdf_viewer.current_page + 1  # Convert to 1-based
                self.current_page = pdf_current_page
            
            # Get current page highlights
            page_highlights = {
                hid: hinfo for hid, hinfo in self.active_highlights.items()
                if hinfo['page'] == self.current_page
            }
            
            if not page_highlights:
                self.logger.debug(f"HIGHLIGHTING_ENGINE: No highlights for page {self.current_page}")
                return pixmap
            
            self.logger.info(f"HIGHLIGHTING_ENGINE: Applying {len(page_highlights)} highlights to page {self.current_page}")
            
            # Use multi-box renderer to apply highlights
            return self.multi_box_renderer.apply_highlights_to_pixmap(
                pixmap, page_highlights, zoom_factor
            )
            
        except Exception as e:
            self.logger.error(f"HIGHLIGHTING_ENGINE: Error applying highlights to pixmap: {e}")
            import traceback
            self.logger.error(f"HIGHLIGHTING_ENGINE: Traceback: {traceback.format_exc()}")
            return pixmap