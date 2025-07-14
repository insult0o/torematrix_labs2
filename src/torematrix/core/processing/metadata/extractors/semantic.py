"""Semantic role classification for document elements.

This module provides ML-based and rule-based semantic role classification
to identify the functional role of elements within documents.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import asyncio

from ....models.element import UnifiedElement

logger = logging.getLogger(__name__)


class SemanticRole(str, Enum):
    """Semantic roles for document elements."""
    TITLE = "title"
    HEADING = "heading"
    SUBHEADING = "subheading"
    BODY_TEXT = "body_text"
    PARAGRAPH = "paragraph"
    CAPTION = "caption"
    FOOTER = "footer"
    HEADER = "header"
    SIDEBAR = "sidebar"
    METADATA = "metadata"
    AUTHOR = "author"
    DATE = "date"
    PAGE_NUMBER = "page_number"
    TABLE_HEADER = "table_header"
    TABLE_CELL = "table_cell"
    LIST_ITEM = "list_item"
    BULLET_POINT = "bullet_point"
    QUOTE = "quote"
    FOOTNOTE = "footnote"
    REFERENCE = "reference"
    ABSTRACT = "abstract"
    CONCLUSION = "conclusion"
    INTRODUCTION = "introduction"
    FIGURE_CAPTION = "figure_caption"
    TABLE_CAPTION = "table_caption"
    FORMULA = "formula"
    CODE = "code"
    NAVIGATION = "navigation"
    WATERMARK = "watermark"
    BACKGROUND = "background"


@dataclass
class SemanticConfig:
    """Configuration for semantic role classification."""
    enable_ml_classification: bool = True
    enable_rule_based_classification: bool = True
    confidence_threshold: float = 0.6
    max_title_length: int = 200
    max_caption_length: int = 500
    min_paragraph_length: int = 50


@dataclass
class ClassificationResult:
    """Result of semantic classification."""
    role: SemanticRole
    confidence: float
    method: str  # "ml", "rules", "combined"
    metadata: Dict[str, Any]


class RuleBasedClassifier:
    """Rule-based semantic role classifier."""
    
    def __init__(self, config: SemanticConfig):
        """Initialize rule-based classifier.
        
        Args:
            config: Configuration for classification
        """
        self.config = config
        self._init_patterns()
    
    def _init_patterns(self):
        """Initialize classification patterns."""
        self.title_patterns = [
            r'^[A-Z][A-Z\s]{10,}$',  # ALL CAPS
            r'^\d+\.\s*[A-Z]',  # "1. Title"
            r'^Chapter\s+\d+',  # "Chapter 1"
            r'^Section\s+\d+',  # "Section 1"
        ]
        
        self.heading_patterns = [
            r'^\d+\.\d+',  # "1.1 Heading"
            r'^\d+\.\d+\.\d+',  # "1.1.1 Subheading"
            r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$',  # Title Case
        ]
        
        self.caption_patterns = [
            r'^(?:Figure|Fig\.?)\s*\d+',
            r'^(?:Table|Tab\.?)\s*\d+',
            r'^(?:Image|Img\.?)\s*\d+',
            r'^(?:Chart|Graph)\s*\d+',
        ]
        
        self.metadata_patterns = [
            r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$',  # Date
            r'^\d{4}-\d{2}-\d{2}$',  # ISO date
            r'^(?:Page|P\.?)\s*\d+',  # Page number
            r'^©\s*\d{4}',  # Copyright
            r'^(?:Author|By):\s*',  # Author
        ]
        
        self.footer_patterns = [
            r'^\d+$',  # Page number only
            r'^©',  # Copyright
            r'confidential',
            r'proprietary',
            r'all rights reserved',
        ]
        
        self.header_patterns = [
            r'^(?:Chapter|Section)\s+\d+',
            r'^\d+\s+(?:Chapter|Section)',
        ]
    
    def classify(
        self, 
        element: UnifiedElement,
        context: Dict[str, Any]
    ) -> Optional[ClassificationResult]:
        """Classify element using rules.
        
        Args:
            element: Element to classify
            context: Document context
            
        Returns:
            Classification result or None
        """
        text = element.text or ""
        text_lower = text.lower()
        
        # Check for title
        title_result = self._check_title(element, text, context)
        if title_result:
            return title_result
        
        # Check for headings
        heading_result = self._check_heading(element, text, context)
        if heading_result:
            return heading_result
        
        # Check for captions
        caption_result = self._check_caption(element, text, context)
        if caption_result:
            return caption_result
        
        # Check for metadata
        metadata_result = self._check_metadata(element, text, context)
        if metadata_result:
            return metadata_result
        
        # Check for footer/header
        footer_result = self._check_footer_header(element, text, context)
        if footer_result:
            return footer_result
        
        # Check for list items
        list_result = self._check_list_item(element, text, context)
        if list_result:
            return list_result
        
        # Check for table elements
        table_result = self._check_table_element(element, text, context)
        if table_result:
            return table_result
        
        # Default classification based on element type and length
        return self._default_classification(element, text, context)
    
    def _check_title(
        self, 
        element: UnifiedElement, 
        text: str, 
        context: Dict[str, Any]
    ) -> Optional[ClassificationResult]:
        """Check if element is a title."""
        if len(text) > self.config.max_title_length:
            return None
        
        # Check element type
        if element.type in ['Title', 'Header']:
            return ClassificationResult(
                role=SemanticRole.TITLE,
                confidence=0.9,
                method="rules",
                metadata={"reason": "element_type"}
            )
        
        # Check patterns
        for pattern in self.title_patterns:
            if re.match(pattern, text):
                return ClassificationResult(
                    role=SemanticRole.TITLE,
                    confidence=0.8,
                    method="rules",
                    metadata={"reason": "pattern_match", "pattern": pattern}
                )
        
        # Check position (first significant text element)
        if (context.get("is_first_text", False) and 
            len(text) < 100 and 
            text.isupper()):
            return ClassificationResult(
                role=SemanticRole.TITLE,
                confidence=0.7,
                method="rules",
                metadata={"reason": "position_and_format"}
            )
        
        return None
    
    def _check_heading(
        self, 
        element: UnifiedElement, 
        text: str, 
        context: Dict[str, Any]
    ) -> Optional[ClassificationResult]:
        """Check if element is a heading."""
        # Check patterns
        for pattern in self.heading_patterns:
            if re.match(pattern, text):
                # Determine heading level based on pattern
                if re.match(r'^\d+\.\d+\.\d+', text):
                    role = SemanticRole.SUBHEADING
                else:
                    role = SemanticRole.HEADING
                
                return ClassificationResult(
                    role=role,
                    confidence=0.85,
                    method="rules",
                    metadata={"reason": "pattern_match", "pattern": pattern}
                )
        
        # Check font size/styling if available
        if self._has_heading_styling(element, context):
            return ClassificationResult(
                role=SemanticRole.HEADING,
                confidence=0.7,
                method="rules",
                metadata={"reason": "styling"}
            )
        
        return None
    
    def _check_caption(
        self, 
        element: UnifiedElement, 
        text: str, 
        context: Dict[str, Any]
    ) -> Optional[ClassificationResult]:
        """Check if element is a caption."""
        if len(text) > self.config.max_caption_length:
            return None
        
        # Check patterns
        for pattern in self.caption_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                # Determine caption type
                if re.match(r'^(?:Figure|Fig\.?)', text, re.IGNORECASE):
                    role = SemanticRole.FIGURE_CAPTION
                elif re.match(r'^(?:Table|Tab\.?)', text, re.IGNORECASE):
                    role = SemanticRole.TABLE_CAPTION
                else:
                    role = SemanticRole.CAPTION
                
                return ClassificationResult(
                    role=role,
                    confidence=0.9,
                    method="rules",
                    metadata={"reason": "pattern_match", "pattern": pattern}
                )
        
        # Check proximity to figures/tables
        if self._is_near_figure_table(element, context):
            return ClassificationResult(
                role=SemanticRole.CAPTION,
                confidence=0.6,
                method="rules",
                metadata={"reason": "proximity"}
            )
        
        return None
    
    def _check_metadata(
        self, 
        element: UnifiedElement, 
        text: str, 
        context: Dict[str, Any]
    ) -> Optional[ClassificationResult]:
        """Check if element is metadata."""
        # Check patterns
        for pattern in self.metadata_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                # Determine specific metadata type
                if re.match(r'^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$', text):
                    role = SemanticRole.DATE
                elif re.match(r'^(?:Page|P\.?)\s*\d+', text, re.IGNORECASE):
                    role = SemanticRole.PAGE_NUMBER
                elif re.match(r'^(?:Author|By):', text, re.IGNORECASE):
                    role = SemanticRole.AUTHOR
                else:
                    role = SemanticRole.METADATA
                
                return ClassificationResult(
                    role=role,
                    confidence=0.85,
                    method="rules",
                    metadata={"reason": "pattern_match", "pattern": pattern}
                )
        
        return None
    
    def _check_footer_header(
        self, 
        element: UnifiedElement, 
        text: str, 
        context: Dict[str, Any]
    ) -> Optional[ClassificationResult]:
        """Check if element is footer or header."""
        text_lower = text.lower()
        
        # Check footer patterns
        for pattern in self.footer_patterns:
            if re.search(pattern, text_lower):
                return ClassificationResult(
                    role=SemanticRole.FOOTER,
                    confidence=0.8,
                    method="rules",
                    metadata={"reason": "pattern_match", "pattern": pattern}
                )
        
        # Check header patterns
        for pattern in self.header_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return ClassificationResult(
                    role=SemanticRole.HEADER,
                    confidence=0.8,
                    method="rules",
                    metadata={"reason": "pattern_match", "pattern": pattern}
                )
        
        # Check position on page
        if context.get("position") == "top" and len(text) < 100:
            return ClassificationResult(
                role=SemanticRole.HEADER,
                confidence=0.6,
                method="rules",
                metadata={"reason": "top_position"}
            )
        
        if context.get("position") == "bottom" and len(text) < 100:
            return ClassificationResult(
                role=SemanticRole.FOOTER,
                confidence=0.6,
                method="rules",
                metadata={"reason": "bottom_position"}
            )
        
        return None
    
    def _check_list_item(
        self, 
        element: UnifiedElement, 
        text: str, 
        context: Dict[str, Any]
    ) -> Optional[ClassificationResult]:
        """Check if element is a list item."""
        if element.type in ['ListItem', 'List']:
            return ClassificationResult(
                role=SemanticRole.LIST_ITEM,
                confidence=0.9,
                method="rules",
                metadata={"reason": "element_type"}
            )
        
        # Check for bullet patterns
        bullet_patterns = [
            r'^\s*[•·▪▫◦‣⁃]\s+',  # Unicode bullets
            r'^\s*[-*+]\s+',  # ASCII bullets
            r'^\s*\d+\.\s+',  # Numbered list
            r'^\s*[a-z]\.\s+',  # Lettered list
            r'^\s*\([a-z]\)\s+',  # Parenthesized list
        ]
        
        for pattern in bullet_patterns:
            if re.match(pattern, text):
                return ClassificationResult(
                    role=SemanticRole.LIST_ITEM,
                    confidence=0.8,
                    method="rules",
                    metadata={"reason": "bullet_pattern", "pattern": pattern}
                )
        
        return None
    
    def _check_table_element(
        self, 
        element: UnifiedElement, 
        text: str, 
        context: Dict[str, Any]
    ) -> Optional[ClassificationResult]:
        """Check if element is part of a table."""
        if element.type in ['Table', 'TableHeader', 'TableCell']:
            if element.type == 'TableHeader':
                role = SemanticRole.TABLE_HEADER
            else:
                role = SemanticRole.TABLE_CELL
            
            return ClassificationResult(
                role=role,
                confidence=0.9,
                method="rules",
                metadata={"reason": "element_type"}
            )
        
        # Check if element is within a table structure
        if context.get("in_table", False):
            return ClassificationResult(
                role=SemanticRole.TABLE_CELL,
                confidence=0.7,
                method="rules",
                metadata={"reason": "table_context"}
            )
        
        return None
    
    def _default_classification(
        self, 
        element: UnifiedElement, 
        text: str, 
        context: Dict[str, Any]
    ) -> ClassificationResult:
        """Provide default classification based on element characteristics."""
        # Check text length for paragraph vs other classifications
        if len(text) >= self.config.min_paragraph_length:
            if element.type in ['Text', 'Paragraph']:
                return ClassificationResult(
                    role=SemanticRole.PARAGRAPH,
                    confidence=0.7,
                    method="rules",
                    metadata={"reason": "length_and_type"}
                )
            else:
                return ClassificationResult(
                    role=SemanticRole.BODY_TEXT,
                    confidence=0.6,
                    method="rules",
                    metadata={"reason": "text_length"}
                )
        
        # Short text elements
        if len(text) < 50:
            return ClassificationResult(
                role=SemanticRole.METADATA,
                confidence=0.4,
                method="rules",
                metadata={"reason": "short_text"}
            )
        
        # Medium length text
        return ClassificationResult(
            role=SemanticRole.BODY_TEXT,
            confidence=0.5,
            method="rules",
            metadata={"reason": "default"}
        )
    
    def _has_heading_styling(self, element: UnifiedElement, context: Dict[str, Any]) -> bool:
        """Check if element has heading-like styling."""
        # This would check font size, weight, etc. if available in metadata
        # For now, return False as we don't have styling information
        return False
    
    def _is_near_figure_table(self, element: UnifiedElement, context: Dict[str, Any]) -> bool:
        """Check if element is near a figure or table."""
        # This would check spatial proximity to figure/table elements
        # For now, return False as we don't have spatial context
        return False


class MLSemanticClassifier:
    """ML-based semantic role classifier (placeholder for future implementation)."""
    
    def __init__(self, config: SemanticConfig):
        """Initialize ML classifier.
        
        Args:
            config: Configuration for classification
        """
        self.config = config
        self.model = None  # Placeholder for ML model
        self.is_loaded = False
    
    async def classify(
        self, 
        element: UnifiedElement,
        context: Dict[str, Any]
    ) -> Optional[ClassificationResult]:
        """Classify element using ML model.
        
        Args:
            element: Element to classify
            context: Document context
            
        Returns:
            Classification result or None
        """
        if not self.config.enable_ml_classification or not self.is_loaded:
            return None
        
        # Placeholder for ML classification
        # In a real implementation, this would:
        # 1. Extract features from element (text, position, styling, etc.)
        # 2. Run through trained model
        # 3. Return classification with confidence
        
        return None
    
    def load_model(self, model_path: str):
        """Load ML model from path.
        
        Args:
            model_path: Path to model file
        """
        # Placeholder for model loading
        pass


class SemanticRoleExtractor:
    """Main semantic role extractor combining ML and rule-based approaches."""
    
    def __init__(self, config: SemanticConfig):
        """Initialize semantic role extractor.
        
        Args:
            config: Configuration for extraction
        """
        self.config = config
        self.rule_classifier = RuleBasedClassifier(config)
        self.ml_classifier = MLSemanticClassifier(config)
        
    async def extract_semantic_roles(
        self, 
        elements: List[UnifiedElement],
        context: Dict[str, Any]
    ) -> Dict[str, SemanticRole]:
        """Extract semantic roles for all elements.
        
        Args:
            elements: List of elements to classify
            context: Document context
            
        Returns:
            Dictionary mapping element IDs to semantic roles
        """
        logger.debug(f"Extracting semantic roles for {len(elements)} elements")
        
        roles = {}
        
        # Add positional context
        enhanced_context = self._enhance_context(elements, context)
        
        # Classify each element
        for i, element in enumerate(elements):
            element_context = {
                **enhanced_context,
                "element_index": i,
                "is_first_text": i == 0 and element.text,
                "is_last_text": i == len(elements) - 1 and element.text,
            }
            
            # Try ML classification first
            ml_result = None
            if self.config.enable_ml_classification:
                ml_result = await self.ml_classifier.classify(element, element_context)
            
            # Try rule-based classification
            rule_result = None
            if self.config.enable_rule_based_classification:
                rule_result = self.rule_classifier.classify(element, element_context)
            
            # Combine results
            final_result = self._combine_results(ml_result, rule_result)
            
            if final_result and final_result.confidence >= self.config.confidence_threshold:
                roles[element.id] = final_result.role
                logger.debug(f"Classified {element.id} as {final_result.role} (confidence: {final_result.confidence:.2f})")
            else:
                # Default to body text if no confident classification
                roles[element.id] = SemanticRole.BODY_TEXT
                logger.debug(f"Default classification for {element.id}: {SemanticRole.BODY_TEXT}")
        
        logger.debug(f"Classified {len(roles)} elements")
        return roles
    
    def _enhance_context(
        self, 
        elements: List[UnifiedElement], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance context with document structure information.
        
        Args:
            elements: All elements in document
            context: Base context
            
        Returns:
            Enhanced context dictionary
        """
        enhanced = context.copy()
        
        # Add element type statistics
        type_counts = {}
        for element in elements:
            type_counts[element.type] = type_counts.get(element.type, 0) + 1
        
        enhanced["element_type_counts"] = type_counts
        enhanced["total_elements"] = len(elements)
        
        # Identify table and figure elements
        table_elements = [e.id for e in elements if e.type in ['Table', 'TableHeader', 'TableCell']]
        figure_elements = [e.id for e in elements if e.type in ['Figure', 'Image']]
        
        enhanced["table_elements"] = table_elements
        enhanced["figure_elements"] = figure_elements
        
        return enhanced
    
    def _combine_results(
        self, 
        ml_result: Optional[ClassificationResult],
        rule_result: Optional[ClassificationResult]
    ) -> Optional[ClassificationResult]:
        """Combine ML and rule-based classification results.
        
        Args:
            ml_result: ML classification result
            rule_result: Rule-based classification result
            
        Returns:
            Combined classification result
        """
        # If only one result available, use it
        if ml_result and not rule_result:
            return ml_result
        elif rule_result and not ml_result:
            return rule_result
        elif not ml_result and not rule_result:
            return None
        
        # Both results available - combine them
        if ml_result.role == rule_result.role:
            # Agreement - boost confidence
            combined_confidence = min(0.95, (ml_result.confidence + rule_result.confidence) / 2 + 0.1)
            return ClassificationResult(
                role=ml_result.role,
                confidence=combined_confidence,
                method="combined",
                metadata={
                    "ml_confidence": ml_result.confidence,
                    "rule_confidence": rule_result.confidence,
                    "agreement": True
                }
            )
        else:
            # Disagreement - use higher confidence result
            if ml_result.confidence > rule_result.confidence:
                return ClassificationResult(
                    role=ml_result.role,
                    confidence=ml_result.confidence * 0.9,  # Slight penalty for disagreement
                    method="ml_priority",
                    metadata={
                        "ml_role": ml_result.role,
                        "rule_role": rule_result.role,
                        "ml_confidence": ml_result.confidence,
                        "rule_confidence": rule_result.confidence,
                        "agreement": False
                    }
                )
            else:
                return ClassificationResult(
                    role=rule_result.role,
                    confidence=rule_result.confidence * 0.9,
                    method="rule_priority",
                    metadata={
                        "ml_role": ml_result.role,
                        "rule_role": rule_result.role,
                        "ml_confidence": ml_result.confidence,
                        "rule_confidence": rule_result.confidence,
                        "agreement": False
                    }
                )