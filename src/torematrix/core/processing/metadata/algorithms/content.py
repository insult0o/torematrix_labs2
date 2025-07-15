"""Content-based relationship algorithms for document elements.

This module provides algorithms for detecting relationships between elements
based on their text content, semantic similarity, and structural patterns.
"""

import logging
import re
from typing import List, Optional, Set, Dict, Any
from collections import Counter
import math

from ....models.element import Element as UnifiedElement
from ..models.relationship import Relationship, RelationshipType

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """Analyzer for content-based relationships between elements."""
    
    def __init__(self, config):
        """Initialize content analyzer.
        
        Args:
            config: Configuration object with content analysis settings
        """
        self.config = config
        self.similarity_threshold = getattr(config, 'content_similarity_threshold', 0.7)
        self.min_word_length = 3
        self.stop_words = self._get_stop_words()
        
    async def analyze_relationship(
        self, 
        element1: UnifiedElement, 
        element2: UnifiedElement
    ) -> List[Relationship]:
        """Analyze content-based relationship between two elements.
        
        Args:
            element1: First element
            element2: Second element
            
        Returns:
            List of detected content relationships
        """
        text1 = self._get_text_content(element1)
        text2 = self._get_text_content(element2)
        
        if not text1 or not text2:
            return []
        
        relationships = []
        
        # Check text similarity
        similarity_rel = self._analyze_text_similarity(element1, element2, text1, text2)
        if similarity_rel:
            relationships.append(similarity_rel)
        
        # Check cross-references
        cross_ref_rels = self._analyze_cross_references(element1, element2, text1, text2)
        relationships.extend(cross_ref_rels)
        
        # Check semantic grouping
        semantic_rel = self._analyze_semantic_grouping(element1, element2, text1, text2)
        if semantic_rel:
            relationships.append(semantic_rel)
        
        # Check caption relationships
        caption_rel = self._analyze_caption_relationship(element1, element2, text1, text2)
        if caption_rel:
            relationships.append(caption_rel)
        
        return relationships
    
    def _get_text_content(self, element: UnifiedElement) -> str:
        """Extract text content from element.
        
        Args:
            element: Element to extract text from
            
        Returns:
            Clean text content
        """
        text = element.text or ""
        
        # Add additional text from element properties if available
        if hasattr(element, 'title') and element.title:
            text = f"{element.title} {text}"
        
        if hasattr(element, 'alt_text') and element.alt_text:
            text = f"{text} {element.alt_text}"
        
        return text.strip()
    
    def _analyze_text_similarity(
        self,
        element1: UnifiedElement,
        element2: UnifiedElement,
        text1: str,
        text2: str
    ) -> Optional[Relationship]:
        """Analyze text similarity between elements.
        
        Args:
            element1: First element
            element2: Second element
            text1: Text content of first element
            text2: Text content of second element
            
        Returns:
            Similarity relationship if detected
        """
        # Calculate cosine similarity using word vectors
        similarity = self._calculate_cosine_similarity(text1, text2)
        
        if similarity >= self.similarity_threshold:
            return Relationship(
                source_id=element1.id,
                target_id=element2.id,
                relationship_type=RelationshipType.CONTENT_SIMILAR,
                confidence=similarity,
                metadata={
                    "similarity_score": similarity,
                    "analysis_method": "cosine_similarity",
                    "common_words": len(self._get_common_words(text1, text2))
                }
            )
        
        return None
    
    def _analyze_cross_references(
        self,
        element1: UnifiedElement,
        element2: UnifiedElement,
        text1: str,
        text2: str
    ) -> List[Relationship]:
        """Analyze cross-references between elements.
        
        Args:
            element1: First element
            element2: Second element
            text1: Text content of first element
            text2: Text content of second element
            
        Returns:
            List of cross-reference relationships
        """
        relationships = []
        
        # Look for references to figures, tables, sections, etc.
        ref_patterns = [
            r'\b(?:figure|fig\.?)\s*(\d+)',
            r'\b(?:table|tab\.?)\s*(\d+)',
            r'\b(?:section|sec\.?)\s*(\d+)',
            r'\b(?:equation|eq\.?)\s*(\d+)',
            r'\b(?:page|p\.?)\s*(\d+)'
        ]
        
        # Check if element1 references element2
        for pattern in ref_patterns:
            matches1 = re.finditer(pattern, text1, re.IGNORECASE)
            matches2 = re.finditer(pattern, text2, re.IGNORECASE)
            
            # If element1 contains references and element2 might be the target
            if list(matches1) and self._could_be_reference_target(element2, pattern):
                confidence = 0.8
                relationships.append(Relationship(
                    source_id=element1.id,
                    target_id=element2.id,
                    relationship_type=RelationshipType.CROSS_REFERENCE,
                    confidence=confidence,
                    metadata={
                        "reference_pattern": pattern,
                        "reference_text": [m.group() for m in re.finditer(pattern, text1, re.IGNORECASE)]
                    }
                ))
        
        return relationships
    
    def _analyze_semantic_grouping(
        self,
        element1: UnifiedElement,
        element2: UnifiedElement,
        text1: str,
        text2: str
    ) -> Optional[Relationship]:
        """Analyze semantic grouping between elements.
        
        Args:
            element1: First element
            element2: Second element
            text1: Text content of first element
            text2: Text content of second element
            
        Returns:
            Semantic grouping relationship if detected
        """
        # Check if elements belong to the same semantic group
        keywords1 = self._extract_keywords(text1)
        keywords2 = self._extract_keywords(text2)
        
        if not keywords1 or not keywords2:
            return None
        
        # Calculate keyword overlap
        common_keywords = keywords1.intersection(keywords2)
        total_keywords = keywords1.union(keywords2)
        
        if total_keywords:
            overlap_ratio = len(common_keywords) / len(total_keywords)
            
            if overlap_ratio >= 0.3:  # 30% keyword overlap
                confidence = min(0.9, overlap_ratio * 1.5)
                
                return Relationship(
                    source_id=element1.id,
                    target_id=element2.id,
                    relationship_type=RelationshipType.SEMANTIC_GROUP,
                    confidence=confidence,
                    metadata={
                        "keyword_overlap_ratio": overlap_ratio,
                        "common_keywords": list(common_keywords),
                        "total_unique_keywords": len(total_keywords)
                    }
                )
        
        return None
    
    def _analyze_caption_relationship(
        self,
        element1: UnifiedElement,
        element2: UnifiedElement,
        text1: str,
        text2: str
    ) -> Optional[Relationship]:
        """Analyze caption relationship between elements.
        
        Args:
            element1: First element
            element2: Second element
            text1: Text content of first element
            text2: Text content of second element
            
        Returns:
            Caption relationship if detected
        """
        # Check if one element is a caption for another
        caption_indicators = [
            r'\b(?:figure|fig\.?)\s*\d+',
            r'\b(?:table|tab\.?)\s*\d+',
            r'\b(?:image|img\.?)\s*\d+',
            r'\b(?:chart|graph)\s*\d+',
            r'\b(?:diagram|diag\.?)\s*\d+'
        ]
        
        # Check if element1 could be a caption for element2
        if self._could_be_caption(element1, text1, caption_indicators):
            if self._could_be_caption_target(element2):
                confidence = 0.85
                return Relationship(
                    source_id=element1.id,
                    target_id=element2.id,
                    relationship_type=RelationshipType.CAPTION_TARGET,
                    confidence=confidence,
                    metadata={
                        "caption_type": "figure_table",
                        "caption_text": text1[:100]  # First 100 chars
                    }
                )
        
        # Check if element2 could be a caption for element1
        if self._could_be_caption(element2, text2, caption_indicators):
            if self._could_be_caption_target(element1):
                confidence = 0.85
                return Relationship(
                    source_id=element2.id,
                    target_id=element1.id,
                    relationship_type=RelationshipType.CAPTION_TARGET,
                    confidence=confidence,
                    metadata={
                        "caption_type": "figure_table",
                        "caption_text": text2[:100]
                    }
                )
        
        return None
    
    def _calculate_cosine_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Cosine similarity score between 0 and 1
        """
        words1 = self._tokenize_text(text1)
        words2 = self._tokenize_text(text2)
        
        if not words1 or not words2:
            return 0.0
        
        # Create word frequency vectors
        all_words = set(words1 + words2)
        vector1 = [words1.count(word) for word in all_words]
        vector2 = [words2.count(word) for word in all_words]
        
        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(vector1, vector2))
        magnitude1 = math.sqrt(sum(a * a for a in vector1))
        magnitude2 = math.sqrt(sum(b * b for b in vector2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _tokenize_text(self, text: str) -> List[str]:
        """Tokenize text into words.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of cleaned words
        """
        # Convert to lowercase and extract words
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out stop words and short words
        filtered_words = [
            word for word in words 
            if len(word) >= self.min_word_length and word not in self.stop_words
        ]
        
        return filtered_words
    
    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract keywords from text.
        
        Args:
            text: Text to extract keywords from
            
        Returns:
            Set of keywords
        """
        words = self._tokenize_text(text)
        
        # Use word frequency to identify keywords
        word_freq = Counter(words)
        
        # Select words that appear more than once or are longer than average
        avg_length = sum(len(word) for word in words) / len(words) if words else 0
        
        keywords = set()
        for word, freq in word_freq.items():
            if freq > 1 or len(word) > avg_length:
                keywords.add(word)
        
        return keywords
    
    def _get_common_words(self, text1: str, text2: str) -> Set[str]:
        """Get common words between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Set of common words
        """
        words1 = set(self._tokenize_text(text1))
        words2 = set(self._tokenize_text(text2))
        
        return words1.intersection(words2)
    
    def _could_be_reference_target(self, element: UnifiedElement, pattern: str) -> bool:
        """Check if element could be a reference target.
        
        Args:
            element: Element to check
            pattern: Reference pattern
            
        Returns:
            True if element could be referenced
        """
        # Check element type
        if element.type in ['Figure', 'Image', 'Table', 'Formula']:
            return True
        
        # Check if element has title or caption that matches pattern
        if hasattr(element, 'title') and element.title:
            if re.search(pattern, element.title, re.IGNORECASE):
                return True
        
        return False
    
    def _could_be_caption(self, element: UnifiedElement, text: str, patterns: List[str]) -> bool:
        """Check if element could be a caption.
        
        Args:
            element: Element to check
            text: Element text
            patterns: Caption patterns to match
            
        Returns:
            True if element could be a caption
        """
        # Check if text matches caption patterns
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Check element type and length
        if element.type in ['Text', 'Title'] and len(text) < 500:  # Captions are usually short
            return True
        
        return False
    
    def _could_be_caption_target(self, element: UnifiedElement) -> bool:
        """Check if element could be a caption target.
        
        Args:
            element: Element to check
            
        Returns:
            True if element could have a caption
        """
        return element.type in ['Figure', 'Image', 'Table', 'Formula', 'Chart']
    
    def _get_stop_words(self) -> Set[str]:
        """Get common stop words.
        
        Returns:
            Set of stop words
        """
        return {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'this', 'these', 'they', 'their',
            'there', 'where', 'when', 'who', 'what', 'how', 'can', 'could',
            'should', 'would', 'may', 'might', 'must', 'shall', 'have', 'had',
            'do', 'does', 'did', 'been', 'being', 'am', 'were', 'but', 'or',
            'if', 'then', 'than', 'so', 'very', 'just', 'only', 'even', 'also',
            'more', 'most', 'much', 'many', 'some', 'any', 'all', 'each',
            'every', 'both', 'either', 'neither', 'one', 'two', 'first',
            'second', 'last', 'next', 'previous', 'other', 'another', 'same',
            'different', 'new', 'old', 'good', 'bad', 'big', 'small', 'long',
            'short', 'high', 'low', 'up', 'down', 'here', 'over', 'under',
            'above', 'below', 'between', 'through', 'during', 'before', 'after',
            'while', 'since', 'until', 'because', 'although', 'however',
            'therefore', 'thus', 'hence', 'moreover', 'furthermore', 'nevertheless'
        }