"""Caption and metadata extraction for images."""

import re
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class CaptionData:
    """Extracted caption information."""
    caption: Optional[str] = None
    alt_text: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    figure_number: Optional[str] = None
    source: Optional[str] = None
    confidence: float = 0.0
    extraction_method: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)


class CaptionExtractor:
    """Extract captions and descriptive text from image elements."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("torematrix.parsers.caption_extractor")
        
        # Caption detection patterns
        self.caption_patterns = [
            # Figure captions
            r'(?i)fig(?:ure)?\s*(\d+[a-z]?)[:.\s]\s*(.+)',
            r'(?i)figure\s+(\d+[a-z]?)[:.\s]\s*(.+)',
            
            # Image captions
            r'(?i)image\s*(\d+[a-z]?)[:.\s]\s*(.+)',
            r'(?i)img\s*(\d+[a-z]?)[:.\s]\s*(.+)',
            
            # Chart/Graph captions
            r'(?i)chart\s*(\d+[a-z]?)[:.\s]\s*(.+)',
            r'(?i)graph\s*(\d+[a-z]?)[:.\s]\s*(.+)',
            
            # Table captions (for table images)
            r'(?i)table\s*(\d+[a-z]?)[:.\s]\s*(.+)',
            
            # Generic numbered captions
            r'(\d+)[:.\s]\s*(.+)',
            
            # Source indicators
            r'(?i)source[:.\s]\s*(.+)',
            r'(?i)credit[:.\s]\s*(.+)',
        ]
        
        # Alt text patterns (for web content)
        self.alt_text_patterns = [
            r'alt\s*=\s*["\']([^"\']+)["\']',
            r'alt-text[:.\s]\s*(.+)',
            r'alternative\s+text[:.\s]\s*(.+)',
        ]
        
        # Title patterns
        self.title_patterns = [
            r'title\s*=\s*["\']([^"\']+)["\']',
            r'title[:.\s]\s*(.+)',
        ]

    def extract(self, element: Any) -> CaptionData:
        """Extract caption information from element.
        
        Args:
            element: UnifiedElement or similar object with text/metadata
            
        Returns:
            CaptionData with extracted information
        """
        caption_data = CaptionData()
        
        try:
            # Extract from element metadata if available
            if hasattr(element, 'metadata') and element.metadata:
                self._extract_from_metadata(element.metadata, caption_data)
            
            # Extract from element text if available
            if hasattr(element, 'text') and element.text:
                self._extract_from_text(element.text, caption_data)
            
            # Extract from surrounding context if available
            if hasattr(element, 'context') and element.context:
                self._extract_from_context(element.context, caption_data)
            
            # Calculate overall confidence
            caption_data.confidence = self._calculate_confidence(caption_data)
            
            # Determine extraction method
            caption_data.extraction_method = self._determine_extraction_method(caption_data)
            
        except Exception as e:
            self.logger.error(f"Caption extraction failed: {e}")
            caption_data.confidence = 0.0
            caption_data.extraction_method = "error"
        
        return caption_data

    def _extract_from_metadata(self, metadata: Dict[str, Any], caption_data: CaptionData) -> None:
        """Extract caption information from element metadata."""
        # Direct metadata fields
        direct_fields = {
            'caption': 'caption',
            'alt_text': 'alt_text',
            'alt': 'alt_text',
            'title': 'title',
            'description': 'description',
            'figure_number': 'figure_number',
            'source': 'source'
        }
        
        for metadata_key, caption_field in direct_fields.items():
            if metadata_key in metadata and metadata[metadata_key]:
                value = str(metadata[metadata_key]).strip()
                if value:
                    setattr(caption_data, caption_field, value)
        
        # Store original metadata
        caption_data.metadata.update(metadata)

    def _extract_from_text(self, text: str, caption_data: CaptionData) -> None:
        """Extract caption information from element text."""
        if not text:
            return
        
        text = text.strip()
        
        # Try caption patterns
        for pattern in self.caption_patterns:
            match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
            if match:
                if len(match.groups()) == 2:
                    # Pattern with number and caption
                    number, caption_text = match.groups()
                    if not caption_data.figure_number:
                        caption_data.figure_number = number.strip()
                    if not caption_data.caption:
                        caption_data.caption = caption_text.strip()
                elif len(match.groups()) == 1:
                    # Pattern with just caption or source
                    caption_text = match.groups()[0]
                    if 'source' in pattern.lower() or 'credit' in pattern.lower():
                        if not caption_data.source:
                            caption_data.source = caption_text.strip()
                    else:
                        if not caption_data.caption:
                            caption_data.caption = caption_text.strip()
                break
        
        # Try alt text patterns
        if not caption_data.alt_text:
            for pattern in self.alt_text_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    caption_data.alt_text = match.group(1).strip()
                    break
        
        # Try title patterns
        if not caption_data.title:
            for pattern in self.title_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    caption_data.title = match.group(1).strip()
                    break
        
        # If no specific patterns matched, use heuristics
        if not any([caption_data.caption, caption_data.alt_text, caption_data.title]):
            caption_candidate = self._extract_caption_heuristic(text)
            if caption_candidate:
                caption_data.caption = caption_candidate

    def _extract_from_context(self, context: Any, caption_data: CaptionData) -> None:
        """Extract caption information from surrounding context."""
        # This would extract from surrounding elements, previous/next text, etc.
        # Implementation depends on the context structure
        if hasattr(context, 'preceding_text'):
            self._analyze_preceding_text(context.preceding_text, caption_data)
        
        if hasattr(context, 'following_text'):
            self._analyze_following_text(context.following_text, caption_data)

    def _extract_caption_heuristic(self, text: str) -> Optional[str]:
        """Extract caption using heuristic methods."""
        # Clean the text
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Skip very short text
        if len(text) < 10:
            return None
        
        # Skip text that looks like metadata
        metadata_patterns = [
            r'^\d+\s*[x×]\s*\d+$',  # Just dimensions
            r'^[a-zA-Z]+\.(jpg|png|gif|svg)$',  # Just filename
            r'^\d+\s*(kb|mb|bytes?)$',  # Just file size
        ]
        
        for pattern in metadata_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return None
        
        # Look for descriptive sentences
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and len(sentence) < 200:
                # Check if it's descriptive (contains verbs, adjectives, etc.)
                if self._is_descriptive_text(sentence):
                    return sentence
        
        # If no good sentence found, return the first reasonable chunk
        if len(text) > 20 and len(text) < 300:
            return text[:200] + ('...' if len(text) > 200 else '')
        
        return None

    def _is_descriptive_text(self, text: str) -> bool:
        """Check if text is descriptive rather than just keywords."""
        # Look for common descriptive words
        descriptive_indicators = [
            r'\b(shows?|displays?|illustrates?|depicts?|represents?)\b',
            r'\b(contains?|includes?|features?|presents?)\b',
            r'\b(this|that|the|a|an)\s+\w+',
            r'\b(is|are|was|were|has|have|will|would|can|could)\b'
        ]
        
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in descriptive_indicators)

    def _analyze_preceding_text(self, preceding_text: str, caption_data: CaptionData) -> None:
        """Analyze text that comes before the image for caption information."""
        if not preceding_text:
            return
        
        # Look for figure references that might be captions
        lines = preceding_text.split('\n')[-3:]  # Last few lines
        
        for line in reversed(lines):
            line = line.strip()
            if line and len(line) > 10:
                # Check if it looks like a caption
                if any(re.search(pattern, line) for pattern in self.caption_patterns):
                    if not caption_data.caption:
                        caption_data.caption = line
                    break

    def _analyze_following_text(self, following_text: str, caption_data: CaptionData) -> None:
        """Analyze text that comes after the image for caption information."""
        if not following_text:
            return
        
        # Look for captions that come after the image
        lines = following_text.split('\n')[:3]  # First few lines
        
        for line in lines:
            line = line.strip()
            if line and len(line) > 10:
                # Check if it looks like a caption
                if any(re.search(pattern, line) for pattern in self.caption_patterns):
                    if not caption_data.caption:
                        caption_data.caption = line
                    break

    def _calculate_confidence(self, caption_data: CaptionData) -> float:
        """Calculate confidence in extracted caption data."""
        confidence = 0.0
        
        # Base confidence for having any information
        if any([caption_data.caption, caption_data.alt_text, caption_data.title]):
            confidence += 0.3
        
        # Boost for having multiple fields
        field_count = sum(1 for field in [
            caption_data.caption, caption_data.alt_text, caption_data.title,
            caption_data.description, caption_data.source
        ] if field)
        
        confidence += field_count * 0.15
        
        # Boost for having figure number (indicates structured content)
        if caption_data.figure_number:
            confidence += 0.2
        
        # Boost for having source information
        if caption_data.source:
            confidence += 0.15
        
        # Quality assessment of caption text
        if caption_data.caption:
            caption_quality = self._assess_caption_quality(caption_data.caption)
            confidence += caption_quality * 0.3
        
        return min(1.0, confidence)

    def _assess_caption_quality(self, caption: str) -> float:
        """Assess the quality of a caption."""
        if not caption:
            return 0.0
        
        quality = 0.0
        
        # Length assessment
        length = len(caption)
        if 20 <= length <= 200:
            quality += 0.4
        elif 10 <= length < 20 or 200 < length <= 300:
            quality += 0.2
        
        # Descriptiveness assessment
        if self._is_descriptive_text(caption):
            quality += 0.3
        
        # Completeness (ends with punctuation)
        if re.search(r'[.!?]$', caption.strip()):
            quality += 0.2
        
        # Contains specific information
        specific_indicators = [
            r'\b\d+%\b',  # Percentages
            r'\b\d{4}\b',  # Years
            r'\b(shows?|displays?|illustrates?)\b',  # Action words
        ]
        
        if any(re.search(pattern, caption, re.IGNORECASE) for pattern in specific_indicators):
            quality += 0.1
        
        return min(1.0, quality)

    def _determine_extraction_method(self, caption_data: CaptionData) -> str:
        """Determine the primary method used for extraction."""
        methods = []
        
        if caption_data.metadata:
            methods.append("metadata")
        
        if caption_data.caption and any(re.search(pattern, caption_data.caption) 
                                       for pattern in self.caption_patterns):
            methods.append("pattern_matching")
        
        if caption_data.alt_text:
            methods.append("alt_text")
        
        if not methods:
            methods.append("heuristic")
        
        return "+".join(methods)

    def extract_bulk(self, elements: List[Any]) -> List[CaptionData]:
        """Extract captions from multiple elements.
        
        Args:
            elements: List of elements to process
            
        Returns:
            List of CaptionData objects
        """
        results = []
        
        for element in elements:
            try:
                caption_data = self.extract(element)
                results.append(caption_data)
            except Exception as e:
                self.logger.error(f"Failed to extract caption from element: {e}")
                results.append(CaptionData(confidence=0.0, extraction_method="error"))
        
        return results

    def get_extraction_statistics(self, results: List[CaptionData]) -> Dict[str, Any]:
        """Get statistics about caption extraction results.
        
        Args:
            results: List of CaptionData objects
            
        Returns:
            Dictionary with extraction statistics
        """
        if not results:
            return {}
        
        total_elements = len(results)
        successful_extractions = sum(1 for r in results if r.confidence > 0.5)
        
        confidence_scores = [r.confidence for r in results]
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        
        methods_used = {}
        for result in results:
            method = result.extraction_method
            methods_used[method] = methods_used.get(method, 0) + 1
        
        field_coverage = {
            'caption': sum(1 for r in results if r.caption),
            'alt_text': sum(1 for r in results if r.alt_text),
            'title': sum(1 for r in results if r.title),
            'description': sum(1 for r in results if r.description),
            'figure_number': sum(1 for r in results if r.figure_number),
            'source': sum(1 for r in results if r.source)
        }
        
        return {
            'total_elements': total_elements,
            'successful_extractions': successful_extractions,
            'success_rate': successful_extractions / total_elements,
            'average_confidence': avg_confidence,
            'methods_used': methods_used,
            'field_coverage': field_coverage,
            'coverage_rates': {
                field: count / total_elements 
                for field, count in field_coverage.items()
            }
        }