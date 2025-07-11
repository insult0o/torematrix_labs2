#!/usr/bin/env python3
"""
Coordinate Mapper for TORE Matrix Labs Highlighting System
Handles precise coordinate conversion between text positions and PDF coordinates.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
import fitz  # PyMuPDF
from collections import defaultdict


class CoordinateMapper:
    """Handles precise coordinate conversion between text positions and PDF coordinates."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Components
        self.pdf_viewer = None
        self.text_widget = None
        self.pdf_document = None
        
        # Coordinate mapping cache
        self.character_maps: Dict[int, Dict[int, Dict[str, Any]]] = {}  # page -> char_index -> coords
        self.word_boundaries: Dict[int, List[Tuple[int, int]]] = {}  # page -> [(start, end), ...]
        self.line_boundaries: Dict[int, List[Tuple[int, int]]] = {}  # page -> [(start, end), ...]
        self.page_text_offsets: Dict[int, int] = {}  # page -> global_text_offset
        
        # Configuration
        self.fallback_enabled = True
        self.cache_enabled = True
        self.debug_mode = False
        
        self.logger.info("Coordinate mapper initialized")
    
    def set_pdf_viewer(self, pdf_viewer):
        """Set the PDF viewer for coordinate mapping."""
        self.pdf_viewer = pdf_viewer
        
        # Extract PDF document if available - check both document and current_document
        if hasattr(pdf_viewer, 'current_document') and pdf_viewer.current_document:
            self.pdf_document = pdf_viewer.current_document
            self._build_coordinate_maps()
            self.logger.info("COORDINATE_MAPPER: PDF document found and coordinate maps built")
        elif hasattr(pdf_viewer, 'document') and pdf_viewer.document:
            self.pdf_document = pdf_viewer.document
            self._build_coordinate_maps()
            self.logger.info("COORDINATE_MAPPER: PDF document found and coordinate maps built")
        else:
            self.logger.warning("COORDINATE_MAPPER: No PDF document available yet")
        
        self.logger.info("COORDINATE_MAPPER: PDF viewer set")
    
    def set_text_widget(self, text_widget):
        """Set the text widget for coordinate mapping."""
        self.text_widget = text_widget
        self.logger.info("COORDINATE_MAPPER: Text widget set")
    
    def _build_coordinate_maps(self):
        """Build coordinate mapping for all pages."""
        try:
            if not self.pdf_document:
                self.logger.warning("COORDINATE_MAPPER: No PDF document available")
                return
            
            self.logger.info(f"COORDINATE_MAPPER: Building coordinate maps for {len(self.pdf_document)} pages")
            
            global_text_offset = 0
            
            for page_num in range(len(self.pdf_document)):
                page = self.pdf_document.load_page(page_num)
                
                # Build character map for this page
                char_map = self._build_character_map(page, global_text_offset)
                self.character_maps[page_num + 1] = char_map
                
                # Build word boundaries
                word_boundaries = self._build_word_boundaries(page, global_text_offset)
                self.word_boundaries[page_num + 1] = word_boundaries
                
                # Build line boundaries
                line_boundaries = self._build_line_boundaries(page, global_text_offset)
                self.line_boundaries[page_num + 1] = line_boundaries
                
                # Store page text offset
                self.page_text_offsets[page_num + 1] = global_text_offset
                
                # Update global offset
                page_text = page.get_text()
                global_text_offset += len(page_text)
                
                self.logger.debug(f"COORDINATE_MAPPER: Built maps for page {page_num + 1}, chars: {len(char_map)}")
            
            self.logger.info("COORDINATE_MAPPER: Coordinate maps built successfully")
            
        except Exception as e:
            self.logger.error(f"COORDINATE_MAPPER: Error building coordinate maps: {e}")
    
    def _build_character_map(self, page: fitz.Page, global_offset: int) -> Dict[int, Dict[str, Any]]:
        """Build precise character-to-coordinate mapping for a page."""
        try:
            char_map = {}
            
            # Get text with detailed positioning
            text_dict = page.get_text("dict")
            char_index = global_offset
            
            for block in text_dict.get("blocks", []):
                if "lines" not in block:
                    continue
                
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"]
                        bbox = span["bbox"]
                        font_size = span["size"]
                        
                        if not text:
                            continue
                        
                        # Calculate character positions within span
                        span_width = bbox[2] - bbox[0]
                        span_height = bbox[3] - bbox[1]
                        
                        for i, char in enumerate(text):
                            # Calculate character position
                            char_progress = i / len(text) if len(text) > 1 else 0
                            char_x = bbox[0] + char_progress * span_width
                            char_width = span_width / len(text)
                            
                            char_map[char_index] = {
                                'x': char_x,
                                'y': bbox[1],
                                'width': char_width,
                                'height': span_height,
                                'char': char,
                                'font_size': font_size,
                                'bbox': [char_x, bbox[1], char_x + char_width, bbox[3]],
                                'page': page.number + 1,
                                'span_bbox': bbox,
                                'block_bbox': block.get("bbox", bbox)
                            }
                            char_index += 1
            
            return char_map
            
        except Exception as e:
            self.logger.error(f"COORDINATE_MAPPER: Error building character map: {e}")
            return {}
    
    def _build_word_boundaries(self, page: fitz.Page, global_offset: int) -> List[Tuple[int, int]]:
        """Build word boundary information for a page."""
        try:
            word_boundaries = []
            
            # Get words with positions
            words = page.get_text("words")
            char_index = global_offset
            
            for word_info in words:
                word_text = word_info[4]  # word text
                word_start = char_index
                word_end = char_index + len(word_text)
                
                word_boundaries.append((word_start, word_end))
                char_index = word_end + 1  # Account for space
            
            return word_boundaries
            
        except Exception as e:
            self.logger.error(f"COORDINATE_MAPPER: Error building word boundaries: {e}")
            return []
    
    def _build_line_boundaries(self, page: fitz.Page, global_offset: int) -> List[Tuple[int, int]]:
        """Build line boundary information for a page."""
        try:
            line_boundaries = []
            
            # Get text with line information
            text_dict = page.get_text("dict")
            char_index = global_offset
            
            for block in text_dict.get("blocks", []):
                if "lines" not in block:
                    continue
                
                for line in block["lines"]:
                    line_start = char_index
                    
                    # Count characters in this line
                    line_length = 0
                    for span in line["spans"]:
                        line_length += len(span["text"])
                    
                    line_end = char_index + line_length
                    line_boundaries.append((line_start, line_end))
                    
                    char_index = line_end + 1  # Account for line break
            
            return line_boundaries
            
        except Exception as e:
            self.logger.error(f"COORDINATE_MAPPER: Error building line boundaries: {e}")
            return []
    
    def map_text_to_pdf(self, text_start: int, text_end: int, page: int) -> List[Dict[str, Any]]:
        """Convert text selection to PDF coordinates with multi-box support."""
        try:
            if page not in self.character_maps:
                self.logger.warning(f"COORDINATE_MAPPER: No character map for page {page}")
                return []
            
            char_map = self.character_maps[page]
            
            # Find characters in the range
            range_chars = []
            for char_pos in range(text_start, text_end):
                if char_pos in char_map:
                    range_chars.append(char_map[char_pos])
            
            if not range_chars:
                self.logger.warning(f"COORDINATE_MAPPER: No characters found for range {text_start}-{text_end}")
                return []
            
            # Group characters by lines for multi-box rendering
            line_groups = self._group_characters_by_line(range_chars)
            
            # Create boxes for each line
            boxes = []
            for line_chars in line_groups:
                if not line_chars:
                    continue
                
                # Calculate bounding box for this line
                min_x = min(char['x'] for char in line_chars)
                max_x = max(char['x'] + char['width'] for char in line_chars)
                min_y = min(char['y'] for char in line_chars)
                max_y = max(char['y'] + char['height'] for char in line_chars)
                
                box = {
                    'x': min_x,
                    'y': min_y,
                    'width': max_x - min_x,
                    'height': max_y - min_y,
                    'bbox': [min_x, min_y, max_x, max_y],
                    'page': page,
                    'char_count': len(line_chars),
                    'line_chars': line_chars
                }
                boxes.append(box)
            
            self.logger.debug(f"COORDINATE_MAPPER: Mapped text range {text_start}-{text_end} to {len(boxes)} boxes")
            return boxes
            
        except Exception as e:
            self.logger.error(f"COORDINATE_MAPPER: Error mapping text to PDF: {e}")
            return []
    
    def _group_characters_by_line(self, chars: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group characters by line for multi-box rendering."""
        try:
            if not chars:
                return []
            
            # Group by Y coordinate (line)
            line_groups = defaultdict(list)
            
            for char in chars:
                # Round Y coordinate to group characters on same line
                line_y = round(char['y'])
                line_groups[line_y].append(char)
            
            # Sort groups by Y coordinate (top to bottom)
            sorted_groups = []
            for y in sorted(line_groups.keys()):
                # Sort characters within line by X coordinate (left to right)
                line_chars = sorted(line_groups[y], key=lambda c: c['x'])
                sorted_groups.append(line_chars)
            
            return sorted_groups
            
        except Exception as e:
            self.logger.error(f"COORDINATE_MAPPER: Error grouping characters by line: {e}")
            return []
    
    def map_pdf_to_text(self, pdf_coords: Dict[str, Any], page: int) -> Optional[int]:
        """Convert PDF coordinates to text position."""
        try:
            if page not in self.character_maps:
                self.logger.warning(f"COORDINATE_MAPPER: No character map for page {page}")
                return None
            
            char_map = self.character_maps[page]
            
            # Find the closest character to the PDF coordinates
            pdf_x = pdf_coords.get('x', 0)
            pdf_y = pdf_coords.get('y', 0)
            
            closest_char = None
            closest_distance = float('inf')
            
            for char_pos, char_info in char_map.items():
                # Calculate distance from PDF coordinate to character center
                char_center_x = char_info['x'] + char_info['width'] / 2
                char_center_y = char_info['y'] + char_info['height'] / 2
                
                distance = ((pdf_x - char_center_x) ** 2 + (pdf_y - char_center_y) ** 2) ** 0.5
                
                if distance < closest_distance:
                    closest_distance = distance
                    closest_char = char_pos
            
            if closest_char is not None:
                self.logger.debug(f"COORDINATE_MAPPER: Mapped PDF coords ({pdf_x}, {pdf_y}) to text position {closest_char}")
            
            return closest_char
            
        except Exception as e:
            self.logger.error(f"COORDINATE_MAPPER: Error mapping PDF to text: {e}")
            return None
    
    def get_character_info(self, text_position: int) -> Optional[Dict[str, Any]]:
        """Get character information for a text position."""
        try:
            # Find which page contains this character
            for page, char_map in self.character_maps.items():
                if text_position in char_map:
                    return char_map[text_position]
            
            return None
            
        except Exception as e:
            self.logger.error(f"COORDINATE_MAPPER: Error getting character info: {e}")
            return None
    
    def get_word_boundaries(self, page: int) -> List[Tuple[int, int]]:
        """Get word boundaries for a page."""
        return self.word_boundaries.get(page, [])
    
    def get_line_boundaries(self, page: int) -> List[Tuple[int, int]]:
        """Get line boundaries for a page."""
        return self.line_boundaries.get(page, [])
    
    def clear_cache(self):
        """Clear coordinate mapping cache."""
        self.character_maps.clear()
        self.word_boundaries.clear()
        self.line_boundaries.clear()
        self.page_text_offsets.clear()
    
    def update_document(self, pdf_document=None):
        """Update PDF document and rebuild coordinate maps."""
        try:
            if pdf_document:
                self.pdf_document = pdf_document
            elif self.pdf_viewer and hasattr(self.pdf_viewer, 'current_document') and self.pdf_viewer.current_document:
                self.pdf_document = self.pdf_viewer.current_document
            elif self.pdf_viewer and hasattr(self.pdf_viewer, 'document') and self.pdf_viewer.document:
                self.pdf_document = self.pdf_viewer.document
            
            if self.pdf_document:
                self.clear_cache()
                self._build_coordinate_maps()
                self.logger.info("COORDINATE_MAPPER: Document updated and coordinate maps rebuilt")
                return True
            else:
                self.logger.warning("COORDINATE_MAPPER: No PDF document available for update")
                return False
                
        except Exception as e:
            self.logger.error(f"COORDINATE_MAPPER: Error updating document: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get coordinate mapper statistics."""
        total_chars = sum(len(char_map) for char_map in self.character_maps.values())
        total_words = sum(len(word_bounds) for word_bounds in self.word_boundaries.values())
        total_lines = sum(len(line_bounds) for line_bounds in self.line_boundaries.values())
        
        return {
            'pages_mapped': len(self.character_maps),
            'total_characters': total_chars,
            'total_words': total_words,
            'total_lines': total_lines,
            'cache_enabled': self.cache_enabled,
            'fallback_enabled': self.fallback_enabled,
            'debug_mode': self.debug_mode
        }