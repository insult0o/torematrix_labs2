#!/usr/bin/env python3
"""
Enhanced coordinate correspondence system for fixing multi-line highlighting issues.
Provides accurate coordinate mapping between text elements and PDF locations.
"""

import logging
from typing import List, Tuple, Optional, Dict, Any
import fitz  # PyMuPDF
from dataclasses import dataclass


@dataclass
class TextBlock:
    """Represents a block of text with precise coordinates."""
    text: str
    bbox: List[float]  # [x0, y0, x1, y1]
    page: int
    line_bboxes: List[List[float]]  # Individual line bounding boxes
    char_positions: List[Tuple[int, List[float]]]  # Character index to bbox mapping


@dataclass 
class HighlightRegion:
    """Represents a region to highlight with multi-line support."""
    page: int
    text: str
    regions: List[List[float]]  # Multiple bounding boxes for multi-line text
    confidence: float
    match_type: str  # 'exact', 'fuzzy', 'partial'


class CoordinateCorrespondenceEngine:
    """Engine for accurate coordinate correspondence between text and PDF."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._text_cache = {}  # Cache extracted text for performance
        
    def find_text_coordinates(self, pdf_path: str, page_number: int, 
                            search_text: str, fallback_bbox: Optional[List[float]] = None) -> HighlightRegion:
        """
        Find accurate coordinates for text with multi-line support.
        
        Args:
            pdf_path: Path to PDF document
            page_number: Page number (0-indexed)
            search_text: Text to find and highlight
            fallback_bbox: Fallback bounding box if text search fails
            
        Returns:
            HighlightRegion with accurate coordinates
        """
        try:
            with fitz.open(pdf_path) as doc:
                self.logger.info(f"Document has {len(doc)} pages, requested page {page_number} (0-indexed)")
                
                if page_number >= len(doc):
                    self.logger.error(f"Page {page_number} does not exist in document (document has {len(doc)} pages)")
                    return self._create_fallback_region(page_number, search_text, fallback_bbox)
                
                if page_number < 0:
                    self.logger.error(f"Invalid negative page number: {page_number}")
                    return self._create_fallback_region(page_number, search_text, fallback_bbox)
                
                page = doc[page_number]
                
                # Try multiple search strategies
                strategies = [
                    self._exact_text_search,
                    self._fuzzy_text_search,
                    self._word_by_word_search,
                    self._character_level_search
                ]
                
                for strategy in strategies:
                    result = strategy(page, search_text, page_number)
                    if result and result.regions:
                        self.logger.info(f"Found text using {strategy.__name__}: {result.match_type}")
                        return result
                
                # If all strategies fail, use fallback
                self.logger.warning(f"Could not find text '{search_text[:50]}...' on page {page_number}")
                return self._create_fallback_region(page_number, search_text, fallback_bbox)
                
        except Exception as e:
            self.logger.error(f"Error finding text coordinates: {e}")
            return self._create_fallback_region(page_number, search_text, fallback_bbox)
    
    def _exact_text_search(self, page: fitz.Page, search_text: str, page_number: int) -> Optional[HighlightRegion]:
        """Search for exact text match."""
        try:
            # Clean search text
            cleaned_text = self._clean_search_text(search_text)
            
            # Search for exact matches
            text_instances = page.search_for(cleaned_text)
            
            if text_instances:
                regions = [list(rect) for rect in text_instances]
                return HighlightRegion(
                    page=page_number,
                    text=search_text,
                    regions=regions,
                    confidence=1.0,
                    match_type='exact'
                )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Exact search failed: {e}")
            return None
    
    def _fuzzy_text_search(self, page: fitz.Page, search_text: str, page_number: int) -> Optional[HighlightRegion]:
        """Search with OCR-error tolerant fuzzy matching."""
        try:
            # Get all text from page with coordinates
            text_dict = page.get_text("dict")
            
            # Clean search text
            cleaned_search = self._clean_search_text(search_text)
            search_words = cleaned_search.split()
            
            if not search_words:
                return None
            
            # Find fuzzy matches
            matches = []
            
            for block in text_dict.get("blocks", []):
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    line_text = ""
                    line_bbox = line.get("bbox", [0, 0, 0, 0])
                    
                    # Collect text from line
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                    
                    # Check for fuzzy match
                    if self._fuzzy_match(cleaned_search, line_text.strip()):
                        matches.append(line_bbox)
            
            if matches:
                return HighlightRegion(
                    page=page_number,
                    text=search_text,
                    regions=matches,
                    confidence=0.8,
                    match_type='fuzzy'
                )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Fuzzy search failed: {e}")
            return None
    
    def _word_by_word_search(self, page: fitz.Page, search_text: str, page_number: int) -> Optional[HighlightRegion]:
        """Search word by word and combine regions."""
        try:
            words = search_text.split()
            if len(words) < 2:
                return None  # Single words handled by exact search
            
            regions = []
            found_words = 0
            
            for word in words:
                cleaned_word = self._clean_search_text(word)
                if len(cleaned_word) < 2:  # Skip very short words
                    continue
                    
                word_instances = page.search_for(cleaned_word)
                if word_instances:
                    regions.extend([list(rect) for rect in word_instances])
                    found_words += 1
            
            # Require at least half the words to be found
            if found_words >= len(words) // 2 and regions:
                # Merge nearby regions for multi-line text
                merged_regions = self._merge_nearby_regions(regions)
                
                return HighlightRegion(
                    page=page_number,
                    text=search_text,
                    regions=merged_regions,
                    confidence=found_words / len(words),
                    match_type='word_by_word'
                )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Word-by-word search failed: {e}")
            return None
    
    def _character_level_search(self, page: fitz.Page, search_text: str, page_number: int) -> Optional[HighlightRegion]:
        """Character-level search for difficult cases."""
        try:
            # Get text with detailed coordinates
            text_dict = page.get_text("dict")
            
            # Build character-level map
            char_map = []
            full_text = ""
            
            for block in text_dict.get("blocks", []):
                if "lines" not in block:
                    continue
                    
                for line in block["lines"]:
                    for span in line.get("spans", []):
                        span_text = span.get("text", "")
                        span_bbox = span.get("bbox", [0, 0, 0, 0])
                        
                        # Estimate character positions within span
                        chars_in_span = len(span_text)
                        if chars_in_span > 0:
                            char_width = (span_bbox[2] - span_bbox[0]) / chars_in_span
                            
                            for i, char in enumerate(span_text):
                                char_x = span_bbox[0] + (i * char_width)
                                char_bbox = [
                                    char_x,
                                    span_bbox[1],
                                    char_x + char_width,
                                    span_bbox[3]
                                ]
                                char_map.append((char, char_bbox))
                                full_text += char
            
            # Search for text in character map
            cleaned_search = self._clean_search_text(search_text)
            start_index = full_text.lower().find(cleaned_search.lower())
            
            if start_index >= 0 and start_index < len(char_map):
                end_index = min(start_index + len(cleaned_search), len(char_map))
                
                # Collect bounding boxes for matched characters
                char_regions = []
                for i in range(start_index, end_index):
                    if i < len(char_map):
                        char_regions.append(char_map[i][1])
                
                if char_regions:
                    # Merge character regions into line regions
                    line_regions = self._merge_character_regions_to_lines(char_regions)
                    
                    return HighlightRegion(
                        page=page_number,
                        text=search_text,
                        regions=line_regions,
                        confidence=0.6,
                        match_type='character_level'
                    )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Character-level search failed: {e}")
            return None
    
    def _clean_search_text(self, text: str) -> str:
        """Clean text for better matching."""
        # Remove extra whitespace
        cleaned = ' '.join(text.split())
        
        # Handle common OCR errors
        replacements = {
            'ﬁ': 'fi', 'ﬂ': 'fl', '–': '-', '—': '-',
            ''': "'", ''': "'", '"': '"', '"': '"'
        }
        
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        
        return cleaned
    
    def _fuzzy_match(self, search_text: str, line_text: str, threshold: float = 0.7) -> bool:
        """Check if line_text fuzzy matches search_text."""
        # Simple similarity check
        search_words = set(search_text.lower().split())
        line_words = set(line_text.lower().split())
        
        if not search_words:
            return False
        
        # Calculate word overlap
        overlap = len(search_words.intersection(line_words))
        similarity = overlap / len(search_words)
        
        return similarity >= threshold
    
    def _merge_nearby_regions(self, regions: List[List[float]], 
                            max_distance: float = 50.0) -> List[List[float]]:
        """Merge regions that are close to each other (for multi-line text)."""
        if not regions:
            return []
        
        # Sort regions by position (top-to-bottom, left-to-right)
        sorted_regions = sorted(regions, key=lambda r: (r[1], r[0]))
        
        merged = []
        current_group = [sorted_regions[0]]
        
        for region in sorted_regions[1:]:
            # Check if this region is close to the current group
            last_region = current_group[-1]
            
            vertical_distance = abs(region[1] - last_region[3])  # Distance between bottom of last and top of current
            horizontal_overlap = max(0, min(region[2], last_region[2]) - max(region[0], last_region[0]))
            
            if vertical_distance <= max_distance or horizontal_overlap > 0:
                current_group.append(region)
            else:
                # Start new group
                if current_group:
                    merged.append(self._combine_regions(current_group))
                current_group = [region]
        
        # Add final group
        if current_group:
            merged.append(self._combine_regions(current_group))
        
        return merged
    
    def _combine_regions(self, regions: List[List[float]]) -> List[float]:
        """Combine multiple regions into one bounding box."""
        if not regions:
            return [0, 0, 0, 0]
        
        min_x = min(r[0] for r in regions)
        min_y = min(r[1] for r in regions)
        max_x = max(r[2] for r in regions)
        max_y = max(r[3] for r in regions)
        
        return [min_x, min_y, max_x, max_y]
    
    def _merge_character_regions_to_lines(self, char_regions: List[List[float]]) -> List[List[float]]:
        """Merge character-level regions into line-level regions."""
        if not char_regions:
            return []
        
        # Group characters by line (similar Y coordinates)
        line_groups = []
        current_line = [char_regions[0]]
        
        for char_region in char_regions[1:]:
            # Check if this character is on the same line
            last_char = current_line[-1]
            vertical_distance = abs(char_region[1] - last_char[1])
            
            if vertical_distance <= 5:  # Same line threshold
                current_line.append(char_region)
            else:
                # New line
                line_groups.append(current_line)
                current_line = [char_region]
        
        # Add final line
        if current_line:
            line_groups.append(current_line)
        
        # Combine each line group into a single region
        line_regions = []
        for line_group in line_groups:
            line_region = self._combine_regions(line_group)
            line_regions.append(line_region)
        
        return line_regions
    
    def _create_fallback_region(self, page_number: int, search_text: str, 
                              fallback_bbox: Optional[List[float]]) -> HighlightRegion:
        """Create a fallback highlight region when text search fails."""
        if fallback_bbox and len(fallback_bbox) == 4:
            regions = [fallback_bbox]
            confidence = 0.3
        else:
            # Create a small region at top-left of page as last resort
            regions = [[50, 50, 200, 80]]
            confidence = 0.1
        
        return HighlightRegion(
            page=page_number,
            text=search_text,
            regions=regions,
            confidence=confidence,
            match_type='fallback'
        )
    
    def validate_coordinates(self, pdf_path: str, page_number: int, 
                           regions: List[List[float]]) -> bool:
        """Validate that coordinate regions are within page bounds."""
        try:
            with fitz.open(pdf_path) as doc:
                if page_number >= len(doc):
                    return False
                
                page = doc[page_number]
                page_rect = page.rect
                
                for region in regions:
                    if len(region) != 4:
                        return False
                    
                    x0, y0, x1, y1 = region
                    
                    # Check if region is within page bounds
                    if (x0 < 0 or y0 < 0 or 
                        x1 > page_rect.width or y1 > page_rect.height or
                        x0 >= x1 or y0 >= y1):
                        return False
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error validating coordinates: {e}")
            return False


# Global instance for reuse
coordinate_engine = CoordinateCorrespondenceEngine()