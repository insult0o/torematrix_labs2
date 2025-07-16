"""
Text Merging Algorithms

Provides intelligent text concatenation algorithms for merge operations.
"""

import re
from typing import List, Optional
Provides intelligent text concatenation and splitting algorithms for merge/split operations.
"""

import re
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum
import logging

from torematrix.core.models.element import Element

logger = logging.getLogger(__name__)


class MergeStrategy(Enum):
    """Text merge strategies."""
    SIMPLE = "simple"
    SMART = "smart"
    PARAGRAPH = "paragraph"
    SIMPLE = "simple"              # Just concatenate with spaces
    SMART = "smart"                # Intelligent spacing based on content
    PARAGRAPH = "paragraph"        # Merge as paragraphs with line breaks
    PRESERVE_FORMATTING = "preserve"  # Preserve original formatting


class TextMerger:
    """Handles text merging operations with various strategies."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".TextMerger")
    
    def merge_texts(self, elements: List[Element], strategy: MergeStrategy = MergeStrategy.SMART) -> str:
        """Merge text content from multiple elements."""
        
        # Patterns for smart merging
        self.sentence_end_pattern = re.compile(r'[.!?]\s*$')
        self.word_end_pattern = re.compile(r'\w\s*$')
        self.punctuation_start_pattern = re.compile(r'^\s*[.!?,:;]')
        self.number_pattern = re.compile(r'^\s*\d+\.?\s*')
        self.bullet_pattern = re.compile(r'^\s*[•\-\*]\s*')
        
    def merge_texts(self, elements: List[Element], strategy: MergeStrategy = MergeStrategy.SMART) -> str:
        """
        Merge text content from multiple elements.
        
        Args:
            elements: List of elements to merge
            strategy: Merge strategy to use
            
        Returns:
            str: Merged text content
        """
        if not elements:
            return ""
        
        texts = [elem.text for elem in elements if elem.text]
        if not texts:
            return ""
        
        if strategy == MergeStrategy.SIMPLE:
            return self._merge_simple(texts)
        elif strategy == MergeStrategy.SMART:
            return self._merge_smart(texts)
        elif strategy == MergeStrategy.PARAGRAPH:
            return self._merge_paragraph(texts)
        elif strategy == MergeStrategy.PRESERVE_FORMATTING:
            return self._merge_preserve_formatting(texts)
        else:
            return self._merge_simple(texts)
    
    def _merge_simple(self, texts: List[str]) -> str:
        """Simple merge with space separation."""
        return " ".join(text.strip() for text in texts if text.strip())
    
    def _merge_smart(self, texts: List[str]) -> str:
        """Smart merge with intelligent spacing."""
        if not texts:
            return ""
        
        result = texts[0].strip()
        
        for i in range(1, len(texts)):
            current_text = texts[i].strip()
            if not current_text:
                continue
            
            # Determine appropriate separator
            separator = self._determine_separator(result, current_text)
            result += separator + current_text
        
        return result
    
    def _merge_paragraph(self, texts: List[str]) -> str:
        """Merge as paragraphs with line breaks."""
        paragraphs = []
        for text in texts:
            stripped = text.strip()
            if stripped:
                paragraphs.append(stripped)
        
        return "\n\n".join(paragraphs)
    
    def _determine_separator(self, prev_text: str, next_text: str) -> str:
        """Determine appropriate separator between two text segments."""
    def _merge_preserve_formatting(self, texts: List[str]) -> str:
        """Preserve original formatting and spacing."""
        return "".join(texts)
    
    def _determine_separator(self, prev_text: str, next_text: str) -> str:
        """
        Determine appropriate separator between two text segments.
        
        Args:
            prev_text: Previous text segment
            next_text: Next text segment
            
        Returns:
            str: Appropriate separator
        """
        # No separator needed if previous text ends with whitespace
        if prev_text.endswith((" ", "\t", "\n")):
            return ""
        
        # No separator needed if next text starts with punctuation
        if next_text.startswith((".", "!", "?", ",", ":", ";")):
            return ""
        
        # Use line break if previous text ends with sentence-ending punctuation
        if prev_text.endswith((".", "!", "?")):
        if self.punctuation_start_pattern.match(next_text):
            return ""
        
        # Use line break for list items or numbered items
        if (self.bullet_pattern.match(next_text) or 
            self.number_pattern.match(next_text)):
            return "\n"
        
        # Use line break if previous text ends with sentence-ending punctuation
        if self.sentence_end_pattern.search(prev_text):
            # Check if next text starts with capital letter (new sentence)
            if next_text and next_text[0].isupper():
                return "\n"
        
        # Default to space
        return " "
    
    def split_text(self, text: str, split_points: List[int]) -> List[str]:
        """Split text at specified positions."""
        """
        Split text at specified positions.
        
        Args:
            text: Text to split
            split_points: List of split positions
            
        Returns:
            List[str]: Split text segments
        """
        if not text or not split_points:
            return [text] if text else []
        
        # Sort split points and ensure they're valid
        valid_points = [point for point in sorted(split_points) 
                       if 0 <= point <= len(text)]
        
        if not valid_points:
            return [text]
        
        # Split the text
        segments = []
        start = 0
        
        for point in valid_points:
            if point > start:
                segments.append(text[start:point])
                start = point
        
        # Add remaining text
        if start < len(text):
            segments.append(text[start:])
        
        return [seg for seg in segments if seg]  # Remove empty segments
        return [seg for seg in segments if seg]  # Remove empty segments
    
    def find_optimal_split_points(self, text: str, target_segments: int) -> List[int]:
        """
        Find optimal split points for dividing text into segments.
        
        Args:
            text: Text to split
            target_segments: Desired number of segments
            
        Returns:
            List[int]: Optimal split points
        """
        if not text or target_segments <= 1:
            return []
        
        # Find potential split points (sentence boundaries, paragraph breaks, etc.)
        potential_points = self._find_potential_split_points(text)
        
        if not potential_points:
            # Fall back to character-based splitting
            segment_length = len(text) // target_segments
            return [i * segment_length for i in range(1, target_segments)]
        
        # Select optimal points based on target segments
        return self._select_optimal_points(potential_points, target_segments, len(text))
    
    def _find_potential_split_points(self, text: str) -> List[int]:
        """Find potential split points in text."""
        points = []
        
        # Sentence boundaries
        for match in re.finditer(r'[.!?]\s+[A-Z]', text):
            points.append(match.start() + 1)
        
        # Paragraph breaks
        for match in re.finditer(r'\n\s*\n', text):
            points.append(match.end())
        
        # List item boundaries
        for match in re.finditer(r'\n\s*[•\-\*\d+\.]', text):
            points.append(match.start() + 1)
        
        # Remove duplicates and sort
        return sorted(list(set(points)))
    
    def _select_optimal_points(self, potential_points: List[int], 
                              target_segments: int, text_length: int) -> List[int]:
        """Select optimal split points from potential points."""
        if len(potential_points) < target_segments - 1:
            return potential_points
        
        # Calculate ideal segment length
        ideal_segment_length = text_length / target_segments
        
        # Select points closest to ideal positions
        selected_points = []
        for i in range(1, target_segments):
            ideal_position = i * ideal_segment_length
            closest_point = min(potential_points, 
                               key=lambda p: abs(p - ideal_position))
            selected_points.append(closest_point)
            potential_points.remove(closest_point)
        
        return sorted(selected_points)
    
    def estimate_merge_quality(self, elements: List[Element]) -> float:
        """
        Estimate the quality of a potential merge operation.
        
        Args:
            elements: Elements to merge
            
        Returns:
            float: Quality score (0.0 to 1.0)
        """
        if not elements or len(elements) < 2:
            return 0.0
        
        quality_score = 0.0
        total_checks = 0
        
        texts = [elem.text for elem in elements if elem.text]
        if not texts:
            return 0.0
        
        # Check text coherence
        coherence_score = self._calculate_text_coherence(texts)
        quality_score += coherence_score
        total_checks += 1
        
        # Check element type consistency
        element_types = [elem.element_type for elem in elements]
        if len(set(element_types)) == 1:
            quality_score += 1.0
        else:
            quality_score += 0.5
        total_checks += 1
        
        # Check spatial proximity (if coordinates available)
        spatial_score = self._calculate_spatial_coherence(elements)
        if spatial_score >= 0:
            quality_score += spatial_score
            total_checks += 1
        
        return quality_score / total_checks if total_checks > 0 else 0.0
    
    def _calculate_text_coherence(self, texts: List[str]) -> float:
        """Calculate text coherence score."""
        if len(texts) < 2:
            return 1.0
        
        coherence_score = 0.0
        comparisons = 0
        
        for i in range(len(texts) - 1):
            current = texts[i].strip()
            next_text = texts[i + 1].strip()
            
            if not current or not next_text:
                continue
            
            # Check if texts flow naturally
            if self._texts_flow_naturally(current, next_text):
                coherence_score += 1.0
            else:
                coherence_score += 0.5
            
            comparisons += 1
        
        return coherence_score / comparisons if comparisons > 0 else 1.0
    
    def _texts_flow_naturally(self, text1: str, text2: str) -> bool:
        """Check if two texts flow naturally together."""
        # Text flows naturally if:
        # 1. First text doesn't end with sentence-ending punctuation, or
        # 2. Second text doesn't start with capital letter, or
        # 3. Texts are part of a list or numbered sequence
        
        ends_with_sentence = self.sentence_end_pattern.search(text1)
        starts_with_capital = text2 and text2[0].isupper()
        
        if not ends_with_sentence:
            return True
        
        if not starts_with_capital:
            return True
        
        # Check for list or numbered sequence
        if (self.bullet_pattern.match(text1) or self.number_pattern.match(text1) or
            self.bullet_pattern.match(text2) or self.number_pattern.match(text2)):
            return True
        
        return False
    
    def _calculate_spatial_coherence(self, elements: List[Element]) -> float:
        """Calculate spatial coherence score."""
        elements_with_coords = [
            elem for elem in elements
            if elem.metadata and elem.metadata.coordinates and elem.metadata.coordinates.layout_bbox
        ]
        
        if len(elements_with_coords) < 2:
            return -1.0  # No spatial information available
        
        # Calculate average distance between elements
        from torematrix.core.processing.metadata.algorithms.spatial import BoundingBox
        
        bboxes = []
        for elem in elements_with_coords:
            bbox_coords = elem.metadata.coordinates.layout_bbox
            bbox = BoundingBox(
                left=bbox_coords[0],
                top=bbox_coords[1],
                right=bbox_coords[2],
                bottom=bbox_coords[3]
            )
            bboxes.append(bbox)
        
        total_distance = 0.0
        pairs = 0
        
        for i in range(len(bboxes)):
            for j in range(i + 1, len(bboxes)):
                distance = bboxes[i].distance_to(bboxes[j])
                total_distance += distance
                pairs += 1
        
        if pairs == 0:
            return 1.0
        
        average_distance = total_distance / pairs
        
        # Convert distance to quality score (closer = better)
        # Normalize based on typical document dimensions
        max_reasonable_distance = 100.0  # pixels
        quality = max(0.0, 1.0 - (average_distance / max_reasonable_distance))
        
        return quality
