"""
Text Merging Algorithms

Provides intelligent text concatenation algorithms for merge operations.
"""

import re
from typing import List, Optional
from enum import Enum
import logging

from torematrix.core.models.element import Element

logger = logging.getLogger(__name__)


class MergeStrategy(Enum):
    """Text merge strategies."""
    SIMPLE = "simple"
    SMART = "smart"
    PARAGRAPH = "paragraph"


class TextMerger:
    """Handles text merging operations with various strategies."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".TextMerger")
    
    def merge_texts(self, elements: List[Element], strategy: MergeStrategy = MergeStrategy.SMART) -> str:
        """Merge text content from multiple elements."""
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
        # No separator needed if previous text ends with whitespace
        if prev_text.endswith((" ", "\t", "\n")):
            return ""
        
        # No separator needed if next text starts with punctuation
        if next_text.startswith((".", "!", "?", ",", ":", ";")):
            return ""
        
        # Use line break if previous text ends with sentence-ending punctuation
        if prev_text.endswith((".", "!", "?")):
            if next_text and next_text[0].isupper():
                return "\n"
        
        # Default to space
        return " "
    
    def split_text(self, text: str, split_points: List[int]) -> List[str]:
        """Split text at specified positions."""
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