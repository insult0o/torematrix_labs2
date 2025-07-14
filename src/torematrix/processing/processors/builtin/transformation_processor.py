"""Document transformation processor implementation.

This module provides a base processor for applying various transformations
to document content, including text normalization, formatting, and structure
modifications.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import re
import logging

from ..base import (
    BaseProcessor,
    ProcessorMetadata,
    ProcessorContext,
    ProcessorResult,
    ProcessorCapability,
    StageStatus,
    ProcessorPriority
)

logger = logging.getLogger(__name__)


class TransformationProcessor(BaseProcessor):
    """Base processor for content transformation."""
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="transformation_processor",
            version="1.0.0",
            description="Transform document content",
            author="ToreMatrix",
            capabilities=[ProcessorCapability.TRANSFORMATION],
            supported_formats=["*"],
            is_cpu_intensive=True,
            timeout_seconds=300,
            priority=ProcessorPriority.NORMAL
        )
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """Transform document content."""
        start_time = datetime.utcnow()
        result = ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.COMPLETED,
            start_time=start_time,
            end_time=start_time
        )
        
        try:
            # Get content from previous processor
            if "unstructured_processor" not in context.previous_results:
                raise ValueError("No content to transform - unstructured_processor required")
            
            unstructured_result = context.previous_results["unstructured_processor"]
            extracted_data = unstructured_result.get("extracted_data", {})
            elements = extracted_data.get("elements", [])
            
            if not elements:
                raise ValueError("No elements to transform")
            
            # Apply transformations based on config
            transformations = self.config.get("transformations", [])
            transformed_elements = await self._apply_transformations(elements, transformations)
            
            # Calculate transformation statistics
            stats = self._calculate_transformation_stats(elements, transformed_elements)
            
            result.extracted_data = {
                "elements": transformed_elements,
                "original_element_count": len(elements),
                "transformed_element_count": len(transformed_elements),
                "transformation_stats": stats
            }
            
            result.metadata = {
                "transformations_applied": len(transformations),
                "elements_modified": stats["elements_modified"],
                "text_length_change": stats["text_length_change"],
                "transformation_success_rate": stats["success_rate"]
            }
            
            # Update metrics
            self.increment_metric("documents_transformed")
            self.update_metric("average_transformations_per_doc", len(transformations))
            
        except Exception as e:
            logger.error(f"Transformation failed: {e}")
            result.errors.append(str(e))
            result.status = StageStatus.FAILED
            self.increment_metric("transformation_failures")
        
        result.end_time = datetime.utcnow()
        return result
    
    async def _apply_transformations(
        self, 
        elements: List[Dict[str, Any]], 
        transformations: List[str]
    ) -> List[Dict[str, Any]]:
        """Apply specified transformations to elements."""
        transformed_elements = [elem.copy() for elem in elements]
        
        for transformation in transformations:
            logger.debug(f"Applying transformation: {transformation}")
            
            if transformation == "normalize_whitespace":
                transformed_elements = self._normalize_whitespace(transformed_elements)
            elif transformation == "remove_empty_elements":
                transformed_elements = self._remove_empty_elements(transformed_elements)
            elif transformation == "lowercase_text":
                transformed_elements = self._lowercase_text(transformed_elements)
            elif transformation == "remove_special_chars":
                transformed_elements = self._remove_special_chars(transformed_elements)
            elif transformation == "merge_similar_elements":
                transformed_elements = self._merge_similar_elements(transformed_elements)
            elif transformation == "extract_numbers":
                transformed_elements = self._extract_numbers(transformed_elements)
            elif transformation == "standardize_headers":
                transformed_elements = self._standardize_headers(transformed_elements)
            elif transformation.startswith("custom:"):
                # Allow custom transformations via config
                custom_func_name = transformation[7:]  # Remove 'custom:' prefix
                if hasattr(self, f"_transform_{custom_func_name}"):
                    custom_func = getattr(self, f"_transform_{custom_func_name}")
                    transformed_elements = custom_func(transformed_elements)
                else:
                    logger.warning(f"Unknown custom transformation: {custom_func_name}")
            else:
                logger.warning(f"Unknown transformation: {transformation}")
        
        return transformed_elements
    
    def _normalize_whitespace(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize whitespace in text elements."""
        for elem in elements:
            if "text" in elem and elem["text"]:
                # Replace multiple whitespace with single space
                elem["text"] = re.sub(r'\s+', ' ', elem["text"].strip())
        return elements
    
    def _remove_empty_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove elements with no meaningful content."""
        return [
            elem for elem in elements 
            if elem.get("text", "").strip() or 
               elem.get("type") in ["Table", "Image", "Figure"]
        ]
    
    def _lowercase_text(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert text to lowercase."""
        for elem in elements:
            if "text" in elem and elem["text"]:
                elem["text"] = elem["text"].lower()
        return elements
    
    def _remove_special_chars(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove special characters from text."""
        for elem in elements:
            if "text" in elem and elem["text"]:
                # Keep alphanumeric, whitespace, and basic punctuation
                elem["text"] = re.sub(r'[^\w\s.,!?;:()\-]', '', elem["text"])
        return elements
    
    def _merge_similar_elements(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge consecutive elements of the same type."""
        if not elements:
            return elements
        
        merged = [elements[0].copy()]
        
        for elem in elements[1:]:
            last_elem = merged[-1]
            
            # Merge if same type and both have text
            if (elem.get("type") == last_elem.get("type") and 
                elem.get("text") and last_elem.get("text") and
                elem.get("type") in ["NarrativeText", "ListItem"]):
                
                # Merge text with appropriate separator
                separator = " " if elem.get("type") == "NarrativeText" else "\n"
                last_elem["text"] += separator + elem["text"]
            else:
                merged.append(elem.copy())
        
        return merged
    
    def _extract_numbers(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract and annotate numbers in text."""
        number_pattern = re.compile(r'\b\d+(?:\.\d+)?\b')
        
        for elem in elements:
            if "text" in elem and elem["text"]:
                numbers = number_pattern.findall(elem["text"])
                if numbers:
                    if "metadata" not in elem:
                        elem["metadata"] = {}
                    elem["metadata"]["extracted_numbers"] = numbers
        
        return elements
    
    def _standardize_headers(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Standardize header elements."""
        for elem in elements:
            if elem.get("type") in ["Title", "Header"]:
                if "text" in elem and elem["text"]:
                    # Remove extra whitespace and standardize case
                    text = elem["text"].strip()
                    # Capitalize first letter of each word for headers
                    elem["text"] = text.title()
                    
                    # Add header level if not present
                    if "metadata" not in elem:
                        elem["metadata"] = {}
                    if "header_level" not in elem["metadata"]:
                        # Try to infer header level from text characteristics
                        if len(text) < 20 and text.isupper():
                            elem["metadata"]["header_level"] = 1
                        elif len(text) < 50:
                            elem["metadata"]["header_level"] = 2
                        else:
                            elem["metadata"]["header_level"] = 3
        
        return elements
    
    def _calculate_transformation_stats(
        self, 
        original: List[Dict[str, Any]], 
        transformed: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate statistics about the transformation."""
        original_text_length = sum(
            len(elem.get("text", "")) for elem in original
        )
        
        transformed_text_length = sum(
            len(elem.get("text", "")) for elem in transformed
        )
        
        # Count modified elements by comparing text content
        elements_modified = 0
        for i, (orig, trans) in enumerate(zip(original, transformed)):
            if orig.get("text") != trans.get("text"):
                elements_modified += 1
        
        # Add any new elements
        if len(transformed) != len(original):
            elements_modified += abs(len(transformed) - len(original))
        
        return {
            "original_text_length": original_text_length,
            "transformed_text_length": transformed_text_length,
            "text_length_change": transformed_text_length - original_text_length,
            "elements_modified": elements_modified,
            "success_rate": 1.0 if not self._metrics.get("transformation_failures", 0) else 0.9,
            "element_count_change": len(transformed) - len(original)
        }