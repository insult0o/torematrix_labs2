"""
Metadata Merge Algorithms

Implementation of metadata conflict resolution and merging strategies.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

from torematrix.core.models.element import Element
from torematrix.core.models.metadata import ElementMetadata

logger = logging.getLogger(__name__)


class ConflictResolution(Enum):
    """Strategies for resolving metadata conflicts."""
    KEEP_FIRST = "keep_first"
    KEEP_LAST = "keep_last"
    MERGE_VALUES = "merge_values"
    CUSTOM_CHOICE = "custom_choice"


@dataclass
class MetadataConflict:
    """Represents a metadata conflict between elements."""
    key: str
    values: List[Any]
    elements: List[Element]
    severity: str = "medium"  # low, medium, high
    
    @property
    def conflicting_values(self) -> List[Any]:
        """Get unique conflicting values."""
        return list(set(self.values))


class MetadataMergeEngine:
    """Engine for merging metadata with conflict resolution."""
    
    def detect_conflicts(self, elements: List[Element]) -> List[MetadataConflict]:
        """
        Detect metadata conflicts between elements.
        
        Args:
            elements: List of elements to check for conflicts
            
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        if len(elements) < 2:
            return conflicts
        
        # Collect all metadata keys
        all_keys = set()
        for element in elements:
            if element.metadata and element.metadata.custom_fields:
                all_keys.update(element.metadata.custom_fields.keys())
        
        # Check each key for conflicts
        for key in all_keys:
            values = []
            conflicting_elements = []
            
            for element in elements:
                if (element.metadata and 
                    element.metadata.custom_fields and 
                    key in element.metadata.custom_fields):
                    values.append(element.metadata.custom_fields[key])
                    conflicting_elements.append(element)
                else:
                    values.append(None)
                    conflicting_elements.append(element)
            
            # Check if there are actual conflicts
            unique_values = set(v for v in values if v is not None)
            if len(unique_values) > 1:
                # Determine severity
                severity = self._determine_conflict_severity(key, unique_values)
                
                conflict = MetadataConflict(
                    key=key,
                    values=values,
                    elements=conflicting_elements,
                    severity=severity
                )
                conflicts.append(conflict)
        
        return conflicts
    
    def _determine_conflict_severity(self, key: str, values: set) -> str:
        """Determine the severity of a metadata conflict."""
        # High severity for important keys
        important_keys = ["type", "category", "priority", "status"]
        if key.lower() in important_keys:
            return "high"
        
        # Medium severity for most conflicts
        return "medium"
    
    def resolve_conflict(self, conflict: MetadataConflict, 
                        resolution: ConflictResolution, 
                        custom_value: Any = None) -> Any:
        """
        Resolve a metadata conflict using specified strategy.
        
        Args:
            conflict: The conflict to resolve
            resolution: Resolution strategy to use
            custom_value: Custom value for CUSTOM_CHOICE strategy
            
        Returns:
            Resolved value
        """
        if resolution == ConflictResolution.KEEP_FIRST:
            # Return first non-None value
            for value in conflict.values:
                if value is not None:
                    return value
            return None
        
        elif resolution == ConflictResolution.KEEP_LAST:
            # Return last non-None value
            for value in reversed(conflict.values):
                if value is not None:
                    return value
            return None
        
        elif resolution == ConflictResolution.MERGE_VALUES:
            # Merge values (implementation depends on value type)
            non_none_values = [v for v in conflict.values if v is not None]
            if not non_none_values:
                return None
            
            # For strings, join with delimiter
            if all(isinstance(v, str) for v in non_none_values):
                return " | ".join(non_none_values)
            
            # For lists, concatenate
            if all(isinstance(v, list) for v in non_none_values):
                result = []
                for v in non_none_values:
                    result.extend(v)
                return result
            
            # For other types, return as list
            return non_none_values
        
        elif resolution == ConflictResolution.CUSTOM_CHOICE:
            return custom_value
        
        else:
            # Default to keep first
            return self.resolve_conflict(conflict, ConflictResolution.KEEP_FIRST)
    
    def merge_metadata(self, elements: List[Element], 
                      strategies: Dict[str, ConflictResolution] = None) -> ElementMetadata:
        """
        Merge metadata from multiple elements.
        
        Args:
            elements: Elements to merge metadata from
            strategies: Conflict resolution strategies per field
            
        Returns:
            Merged metadata
        """
        if not elements:
            return ElementMetadata()
        
        if len(elements) == 1:
            return elements[0].metadata or ElementMetadata()
        
        # Detect conflicts
        conflicts = self.detect_conflicts(elements)
        
        # Resolve conflicts
        merged_custom_fields = {}
        for conflict in conflicts:
            strategy = strategies.get(conflict.key, ConflictResolution.KEEP_FIRST) if strategies else ConflictResolution.KEEP_FIRST
            resolved_value = self.resolve_conflict(conflict, strategy)
            if resolved_value is not None:
                merged_custom_fields[conflict.key] = resolved_value
        
        # Add non-conflicting fields
        all_keys = set()
        for element in elements:
            if element.metadata and element.metadata.custom_fields:
                all_keys.update(element.metadata.custom_fields.keys())
        
        conflict_keys = {c.key for c in conflicts}
        non_conflict_keys = all_keys - conflict_keys
        
        for key in non_conflict_keys:
            for element in elements:
                if (element.metadata and 
                    element.metadata.custom_fields and 
                    key in element.metadata.custom_fields):
                    merged_custom_fields[key] = element.metadata.custom_fields[key]
                    break
        
        # Merge other metadata fields
        # Use first element's metadata as base
        base_metadata = elements[0].metadata or ElementMetadata()
        
        # Merge coordinates (use first element's coordinates)
        merged_coordinates = base_metadata.coordinates
        
        # Merge other fields (use highest confidence, etc.)
        merged_confidence = max(
            (elem.metadata.confidence for elem in elements if elem.metadata),
            default=1.0
        )
        
        # Merge page numbers (use first non-None)
        merged_page_number = None
        for element in elements:
            if element.metadata and element.metadata.page_number:
                merged_page_number = element.metadata.page_number
                break
        
        # Merge languages (combine unique languages)
        merged_languages = []
        for element in elements:
            if element.metadata and element.metadata.languages:
                for lang in element.metadata.languages:
                    if lang not in merged_languages:
                        merged_languages.append(lang)
        
        return ElementMetadata(
            coordinates=merged_coordinates,
            confidence=merged_confidence,
            detection_method="merged",
            page_number=merged_page_number,
            languages=merged_languages,
            custom_fields=merged_custom_fields
        )