"""
Text Merging Algorithms

Implementation of various text merging strategies for document elements.
"""

from enum import Enum
from typing import List, Optional
import re


class MergeStrategy(Enum):
    """Strategies for merging text content."""
    SMART = "smart"
    SIMPLE = "simple"
    PARAGRAPH = "paragraph"


class TextMerger:
    """Text merging algorithms for combining element text content."""
    
    @staticmethod
    def merge_text(texts: List[str], strategy: MergeStrategy = MergeStrategy.SMART) -> str:
        """
        Merge text content using specified strategy.
        
        Args:
            texts: List of text strings to merge
            strategy: Merge strategy to use
            
        Returns:
            Merged text content
        """
        if not texts:
            return ""
        
        # Filter out empty/None texts
        valid_texts = [text for text in texts if text and text.strip()]
        
        if not valid_texts:
            return ""
        
        if len(valid_texts) == 1:
            return valid_texts[0]
        
        if strategy == MergeStrategy.SMART:
            return TextMerger._smart_merge(valid_texts)
        elif strategy == MergeStrategy.SIMPLE:
            return TextMerger._simple_merge(valid_texts)
        elif strategy == MergeStrategy.PARAGRAPH:
            return TextMerger._paragraph_merge(valid_texts)
        else:
            return TextMerger._smart_merge(valid_texts)
    
    @staticmethod
    def _smart_merge(texts: List[str]) -> str:
        """Smart merge that handles punctuation and spacing intelligently."""
        if not texts:
            return ""
        
        result = texts[0]
        
        for i in range(1, len(texts)):
            current_text = texts[i]
            
            # Check if result ends with punctuation
            result_ends_with_punct = result.strip() and result.strip()[-1] in '.!?'
            
            # Check if current text starts with punctuation
            current_starts_with_punct = current_text.strip() and current_text.strip()[0] in '.!?,'
            
            # Determine separator
            if result_ends_with_punct or current_starts_with_punct:
                separator = " "
            else:
                separator = " "
            
            # Merge with appropriate separator
            result = result.rstrip() + separator + current_text.lstrip()
        
        return result
    
    @staticmethod
    def _simple_merge(texts: List[str]) -> str:
        """Simple merge with space separation."""
        return " ".join(text.strip() for text in texts if text.strip())
    
    @staticmethod
    def _paragraph_merge(texts: List[str]) -> str:
        """Paragraph merge with line breaks."""
        return "\n".join(text.strip() for text in texts if text.strip())