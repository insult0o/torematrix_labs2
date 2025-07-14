"""Hierarchical list parser with nested structure detection."""

import re
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from .base import BaseParser, ParserResult, ParserMetadata
from ...models.element import Element as UnifiedElement
from .types import ElementType, ParserConfig, ParserCapabilities, ProcessingHints, ParserPriority
from .structural.list_detector import ListDetector, ListItem, ListStructure, ListType
from .exceptions import StructureExtractionError, ValidationError


class ListParser(BaseParser):
    """Hierarchical list parser with nested structure detection up to 5 levels."""
    
    def __init__(self, config: Optional[ParserConfig] = None):
        super().__init__(config)
        self.max_depth = config.parser_specific.get('list_max_depth', 5) if config else 5
        self.min_confidence = config.parser_specific.get('list_min_confidence', 0.8) if config else 0.8
        self.min_items = config.parser_specific.get('list_min_items', 2) if config else 2
        
        # Initialize detector
        detector_config = {
            'max_depth': self.max_depth,
            'min_items': self.min_items
        }
        self.detector = ListDetector(detector_config)
        
        self.logger = logging.getLogger(f"torematrix.parsers.{self.name.lower()}")
    
    @property
    def capabilities(self) -> ParserCapabilities:
        """Return parser capabilities."""
        return ParserCapabilities(
            supported_types=[ElementType.LIST, ElementType.LIST_ITEM],
            max_element_size=1024 * 1024 * 5,  # 5MB
            supports_batch=True,
            supports_async=True,
            confidence_range=(0.0, 1.0),
            supports_validation=True,
            supports_metadata_extraction=True,
            supports_structured_output=True,
            supports_export_formats=["json", "html", "markdown", "text"]
        )
    
    def can_parse(self, element: UnifiedElement) -> bool:
        """Check if element is a list."""
        if not element:
            return False
        
        # Check element type
        if hasattr(element, 'element_type'):
            return element.element_type.value in [ElementType.LIST.value, ElementType.LIST_ITEM.value]
        elif hasattr(element, 'type'):
            return element.type in [ElementType.LIST.value, ElementType.LIST_ITEM.value]
        elif hasattr(element, 'category'):
            return element.category == "list"
        
        # Check for list indicators in content
        return self._has_list_indicators(element)
    
    def _has_list_indicators(self, element: UnifiedElement) -> bool:
        """Check if element has list-like indicators."""
        if not hasattr(element, 'text') or not element.text:
            return False
        
        text = element.text.strip()
        if not text:
            return False
        
        lines = text.split('\n')
        if len(lines) < self.min_items:
            return False
        
        # Look for list patterns
        list_patterns = [
            r'^\s*\d+[\.\)]\s+',       # 1. item
            r'^\s*[a-zA-Z][\.\)]\s+',  # a. item
            r'^\s*[•·▪▫◦‣⁃]\s+',       # • item
            r'^\s*[-*+]\s+',           # - item
            r'^\s*.+:\s+',             # term: definition
        ]
        
        matching_lines = 0
        for line in lines:
            if any(re.match(pattern, line) for pattern in list_patterns):
                matching_lines += 1
        
        # If at least 60% of lines match list patterns
        return matching_lines / len(lines) >= 0.6
    
    async def parse(self, element: UnifiedElement, hints: Optional[ProcessingHints] = None) -> ParserResult:
        """Parse list with hierarchy preservation."""
        try:
            self.logger.debug(f"Starting list parsing for element {getattr(element, 'element_id', 'unknown')}")
            
            # Extract list items
            raw_items = self._extract_list_items(element)
            if not raw_items:
                return self._create_failure_result("No list items found in element")
            
            # Detect hierarchy and structure
            structure = await self.detector.detect_hierarchy(raw_items)
            if not structure:
                return self._create_failure_result("Failed to detect list structure")
            
            # Validate depth limits
            if structure.max_depth > self.max_depth:
                structure = self._truncate_depth(structure)
            
            # Build nested structure
            nested_items = self.detector.build_nested_structure(structure.items)
            
            # Validate structure
            validation_errors = self.validate_structure(structure)
            confidence = self._calculate_list_confidence(structure, validation_errors)
            
            # Create export formats
            export_formats = self._export_formats(structure)
            
            return ParserResult(
                success=True,
                data={
                    "structure": structure,
                    "items": self._flatten_items(structure.items),
                    "hierarchy": self._export_hierarchy(nested_items),
                    "statistics": {
                        "total_items": structure.total_items,
                        "max_depth": structure.max_depth,
                        "list_type": structure.list_type.value,
                        "has_mixed_content": structure.has_mixed_content
                    },
                    "nested_structure": nested_items
                },
                metadata=ParserMetadata(
                    confidence=confidence,
                    parser_name=self.name,
                    parser_version=self.version,
                    warnings=validation_errors if confidence > self.min_confidence else [],
                    element_metadata={
                        "list_complexity": self._calculate_complexity(structure),
                        "content_density": self._calculate_content_density(structure),
                        "structure_quality": self._assess_structure_quality(structure)
                    }
                ),
                validation_errors=validation_errors if confidence <= self.min_confidence else [],
                structured_data=self._create_structured_data(structure),
                export_formats=export_formats
            )
            
        except Exception as e:
            self.logger.error(f"List parsing failed: {str(e)}")
            return self._create_failure_result(f"List parsing failed: {str(e)}")
    
    def validate(self, result: ParserResult) -> List[str]:
        """Validate list parsing result."""
        errors = []
        
        if not result.success:
            return ["List parsing failed"]
        
        structure = result.data.get("structure")
        if not structure:
            errors.append("No list structure found")
            return errors
        
        # Validate depth
        if structure.max_depth > self.max_depth:
            errors.append(f"List depth {structure.max_depth} exceeds maximum {self.max_depth}")
        
        # Validate item count
        if structure.total_items == 0:
            errors.append("List has no items")
        elif structure.total_items < self.min_items:
            errors.append(f"List has {structure.total_items} items, minimum required is {self.min_items}")
        
        # Validate structure quality
        structure_quality = result.metadata.element_metadata.get("structure_quality", 0)
        if structure_quality < 0.5:
            errors.append("List structure quality below acceptable threshold")
        
        return errors
    
    def validate_structure(self, structure: ListStructure) -> List[str]:
        """Validate list structure integrity."""
        return self.detector.validate_hierarchy(structure)
    
    def _extract_list_items(self, element: UnifiedElement) -> List[str]:
        """Extract list items from element."""
        if not hasattr(element, 'text') or not element.text:
            return []
        
        text = element.text.strip()
        if not text:
            return []
        
        # Split into lines and filter out empty ones
        lines = [line.rstrip() for line in text.split('\n')]
        non_empty_lines = [line for line in lines if line.strip()]
        
        return non_empty_lines
    
    def _truncate_depth(self, structure: ListStructure) -> ListStructure:
        """Truncate list depth to maximum allowed."""
        if structure.max_depth <= self.max_depth:
            return structure
        
        # Filter items to maximum depth
        truncated_items = [item for item in structure.items if item.level < self.max_depth]
        
        # Update structure
        new_max_depth = max(item.level for item in truncated_items) if truncated_items else 0
        
        return ListStructure(
            items=truncated_items,
            list_type=structure.list_type,
            max_depth=new_max_depth,
            total_items=len(truncated_items),
            has_mixed_content=structure.has_mixed_content
        )
    
    def _calculate_list_confidence(self, structure: ListStructure, validation_errors: List[str]) -> float:
        """Calculate confidence score for list parsing."""
        base_confidence = 0.85
        
        # Reduce confidence for validation errors
        error_penalty = len(validation_errors) * 0.1
        base_confidence -= error_penalty
        
        # Adjust based on structure quality
        if structure.total_items >= self.min_items:
            base_confidence += 0.05
        
        # Bonus for consistent structure
        if not structure.has_mixed_content:
            base_confidence += 0.05
        
        # Penalty for excessive depth
        if structure.max_depth > 3:
            base_confidence -= 0.05
        
        return max(0.0, min(1.0, base_confidence))
    
    def _calculate_complexity(self, structure: ListStructure) -> str:
        """Calculate list complexity level."""
        if structure.max_depth >= 4:
            return "high"
        elif structure.max_depth >= 2 or structure.total_items > 20:
            return "medium"
        else:
            return "low"
    
    def _calculate_content_density(self, structure: ListStructure) -> float:
        """Calculate content density (average content length per item)."""
        if not structure.items:
            return 0.0
        
        total_content_length = sum(len(item.content) for item in structure.items)
        return total_content_length / len(structure.items)
    
    def _assess_structure_quality(self, structure: ListStructure) -> float:
        """Assess overall structure quality (0-1)."""
        if not structure.items:
            return 0.0
        
        quality_factors = []
        
        # Consistency factor
        if not structure.has_mixed_content:
            quality_factors.append(0.9)
        else:
            quality_factors.append(0.6)
        
        # Depth appropriateness
        if structure.max_depth <= 3:
            quality_factors.append(0.9)
        elif structure.max_depth <= 5:
            quality_factors.append(0.7)
        else:
            quality_factors.append(0.4)
        
        # Content completeness
        empty_items = sum(1 for item in structure.items if not item.content.strip())
        completeness = 1.0 - (empty_items / len(structure.items))
        quality_factors.append(completeness)
        
        return sum(quality_factors) / len(quality_factors)
    
    def _flatten_items(self, items: List[ListItem]) -> List[Dict[str, Any]]:
        """Flatten list items to dictionary format."""
        return [
            {
                "content": item.content,
                "level": item.level,
                "type": item.item_type,
                "number": item.number,
                "metadata": item.metadata
            }
            for item in items
        ]
    
    def _export_hierarchy(self, nested_items: List[ListItem]) -> Dict[str, Any]:
        """Export hierarchical structure."""
        return {
            "type": "nested_list",
            "items": self._items_to_dict(nested_items)
        }
    
    def _items_to_dict(self, items: List[ListItem]) -> List[Dict[str, Any]]:
        """Convert ListItem objects to dictionary format."""
        result = []
        for item in items:
            item_dict = {
                "content": item.content,
                "level": item.level,
                "type": item.item_type,
                "number": item.number,
                "metadata": item.metadata
            }
            
            if item.children:
                item_dict["children"] = self._items_to_dict(item.children)
            
            result.append(item_dict)
        
        return result
    
    def _create_structured_data(self, structure: ListStructure) -> Dict[str, Any]:
        """Create structured data representation."""
        return {
            "list_type": structure.list_type.value,
            "max_depth": structure.max_depth,
            "total_items": structure.total_items,
            "items": [
                {
                    "content": item.content,
                    "level": item.level,
                    "type": item.item_type,
                    "number": item.number
                }
                for item in structure.items
            ]
        }
    
    def _export_formats(self, structure: ListStructure) -> Dict[str, Any]:
        """Export list in multiple formats."""
        formats = {}
        
        try:
            formats["json"] = self._to_json(structure)
        except Exception as e:
            self.logger.warning(f"JSON export failed: {e}")
        
        try:
            formats["html"] = self._to_html(structure)
        except Exception as e:
            self.logger.warning(f"HTML export failed: {e}")
        
        try:
            formats["markdown"] = self._to_markdown(structure)
        except Exception as e:
            self.logger.warning(f"Markdown export failed: {e}")
        
        try:
            formats["text"] = self._to_text(structure)
        except Exception as e:
            self.logger.warning(f"Text export failed: {e}")
        
        return formats
    
    def _to_json(self, structure: ListStructure) -> Dict[str, Any]:
        """Convert list to JSON format."""
        return {
            "list_type": structure.list_type.value,
            "max_depth": structure.max_depth,
            "total_items": structure.total_items,
            "has_mixed_content": structure.has_mixed_content,
            "items": [
                {
                    "content": item.content,
                    "level": item.level,
                    "type": item.item_type,
                    "number": item.number,
                    "metadata": item.metadata
                }
                for item in structure.items
            ]
        }
    
    def _to_html(self, structure: ListStructure) -> str:
        """Convert list to HTML format."""
        if not structure.items:
            return ""
        
        # Group items by level for nested HTML generation
        html_parts = []
        current_lists = {}  # level -> list_type
        
        html_parts.append("<div class='parsed-list'>")
        
        for item in structure.items:
            level = item.level
            
            # Close deeper lists
            levels_to_close = [l for l in current_lists.keys() if l > level]
            for close_level in sorted(levels_to_close, reverse=True):
                list_type = current_lists[close_level]
                tag = "ol" if list_type == "ordered" else "ul"
                html_parts.append("  " * close_level + f"</{tag}>")
                del current_lists[close_level]
            
            # Open new list if needed
            if level not in current_lists:
                list_type = "ordered" if item.item_type == "ordered" else "unordered"
                current_lists[level] = list_type
                tag = "ol" if list_type == "ordered" else "ul"
                html_parts.append("  " * level + f"<{tag}>")
            
            # Add list item
            indent = "  " * (level + 1)
            html_parts.append(f"{indent}<li>{item.content}</li>")
        
        # Close remaining lists
        for close_level in sorted(current_lists.keys(), reverse=True):
            list_type = current_lists[close_level]
            tag = "ol" if list_type == "ordered" else "ul"
            html_parts.append("  " * close_level + f"</{tag}>")
        
        html_parts.append("</div>")
        return "\n".join(html_parts)
    
    def _to_markdown(self, structure: ListStructure) -> str:
        """Convert list to Markdown format."""
        if not structure.items:
            return ""
        
        lines = []
        
        for item in structure.items:
            indent = "  " * item.level
            
            if item.item_type == "ordered":
                marker = f"{item.number}." if item.number else "1."
            else:
                marker = "-"
            
            lines.append(f"{indent}{marker} {item.content}")
        
        return "\n".join(lines)
    
    def _to_text(self, structure: ListStructure) -> str:
        """Convert list to plain text format."""
        if not structure.items:
            return ""
        
        lines = []
        
        for item in structure.items:
            indent = "  " * item.level
            lines.append(f"{indent}{item.content}")
        
        return "\n".join(lines)