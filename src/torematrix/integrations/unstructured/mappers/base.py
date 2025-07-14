"""
Base mapper interface and registry for unstructured element mapping.

This module provides the foundation for mapping unstructured.io elements
to the unified TORE Matrix Labs element model.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Generic, TypeVar
import logging

# Type variables for generic mapping
T = TypeVar('T')  # Target element type  
U = TypeVar('U')  # Source unstructured element type

logger = logging.getLogger(__name__)


class ElementMapper(ABC, Generic[U, T]):
    """
    Abstract base class for element mappers.
    
    Maps from Unstructured elements to our unified element model.
    Each mapper handles a specific element type with specialized logic.
    """
    
    @abstractmethod
    def can_map(self, element: Any) -> bool:
        """Check if this mapper can handle the given element."""
        pass
    
    @abstractmethod
    def map(self, element: U) -> T:
        """Map unstructured element to our unified model."""
        pass
    
    @abstractmethod
    def extract_metadata(self, element: U) -> Dict[str, Any]:
        """Extract metadata from unstructured element."""
        pass
    
    def validate(self, element: T) -> List[str]:
        """Validate mapped element for completeness."""
        return []


class MapperRegistry:
    """Registry for managing element mappers."""
    
    def __init__(self):
        self._mappers: List[ElementMapper] = []
        self._type_map: Dict[type, ElementMapper] = {}
        self._logger = logging.getLogger(__name__)
    
    def register(self, mapper: ElementMapper, element_type: Optional[type] = None):
        """Register a mapper with optional type association."""
        if mapper not in self._mappers:
            self._mappers.append(mapper)
        
        if element_type:
            self._type_map[element_type] = mapper
    
    def get_mapper(self, element: Any) -> Optional[ElementMapper]:
        """Get appropriate mapper for element."""
        # Try type-based lookup first
        mapper = self._type_map.get(type(element))
        if mapper and mapper.can_map(element):
            return mapper
        
        # Fall back to checking all mappers
        for mapper in self._mappers:
            if mapper.can_map(element):
                return mapper
        
        return None
    
    def map_element(self, element: Any) -> Optional[Any]:
        """Map an element using appropriate mapper."""
        mapper = self.get_mapper(element)
        if mapper:
            try:
                return mapper.map(element)
            except Exception as e:
                self._logger.error(f"Mapping failed: {e}")
        return None
    
    def get_mapper_count(self) -> int:
        """Get total number of registered mappers."""
        return len(self._mappers)
    
    def get_supported_types(self) -> List[type]:
        """Get list of all supported element types."""
        return list(self._type_map.keys())