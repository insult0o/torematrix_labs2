"""
Element factory for creating unified elements from unstructured elements.

This module provides the main factory class for converting unstructured.io
elements to our unified element model with comprehensive type support.
"""

from typing import Any, Dict, List, Optional
import logging

from torematrix.core.models.element import Element, ElementType
from .base import ElementMapper, MapperRegistry

logger = logging.getLogger(__name__)


class ElementFactory:
    """Factory for creating unified elements from unstructured elements."""
    
    def __init__(self):
        self._registry = MapperRegistry()
        self._logger = logging.getLogger(__name__)
        self._setup_mappers()
    
    def _setup_mappers(self):
        """Register all element mappers."""
        # Register basic mappers for all major element types
        self._registry.register(TitleMapper())
        self._registry.register(NarrativeTextMapper())
        self._registry.register(TextMapper())
        self._registry.register(TableMapper())
        self._registry.register(ListItemMapper())
        self._registry.register(ImageMapper())
        self._registry.register(HeaderMapper())
        self._registry.register(FooterMapper())
        
        self._logger.info(f"Registered {self._registry.get_mapper_count()} element mappers")
    
    def create_element(self, unstructured_element: Any) -> Optional[Element]:
        """Create unified element from unstructured element."""
        try:
            mapped_element = self._registry.map_element(unstructured_element)
            return mapped_element
        except Exception as e:
            self._logger.error(f"Failed to create element: {e}")
            return None
    
    def create_elements(self, unstructured_elements: List[Any]) -> List[Element]:
        """Create multiple elements with relationship tracking."""
        elements = []
        
        for uns_elem in unstructured_elements:
            element = self.create_element(uns_elem)
            if element:
                elements.append(element)
        
        self._logger.info(f"Created {len(elements)}/{len(unstructured_elements)} elements")
        return elements
    
    def get_supported_types(self) -> List[str]:
        """Get list of all supported element types."""
        return [t.__name__ for t in self._registry.get_supported_types()]


# Basic mapper implementations
class TitleMapper(ElementMapper):
    """Maps Title elements to unified model."""
    
    def can_map(self, element: Any) -> bool:
        return type(element).__name__ == 'Title'
    
    def map(self, element: Any) -> Element:
        return Element(
            element_type=ElementType.TITLE,
            text=getattr(element, 'text', '')
        )
    
    def extract_metadata(self, element: Any) -> Dict[str, Any]:
        return {'is_title': True}


class NarrativeTextMapper(ElementMapper):
    """Maps NarrativeText elements."""
    
    def can_map(self, element: Any) -> bool:
        return type(element).__name__ == 'NarrativeText'
    
    def map(self, element: Any) -> Element:
        return Element(
            element_type=ElementType.NARRATIVE_TEXT,
            text=getattr(element, 'text', '')
        )
    
    def extract_metadata(self, element: Any) -> Dict[str, Any]:
        return {'is_narrative': True}


class TextMapper(ElementMapper):
    """Maps generic Text elements."""
    
    def can_map(self, element: Any) -> bool:
        return type(element).__name__ == 'Text'
    
    def map(self, element: Any) -> Element:
        return Element(
            element_type=ElementType.TEXT,
            text=getattr(element, 'text', '')
        )
    
    def extract_metadata(self, element: Any) -> Dict[str, Any]:
        return {}


class TableMapper(ElementMapper):
    """Maps Table elements."""
    
    def can_map(self, element: Any) -> bool:
        return type(element).__name__ == 'Table'
    
    def map(self, element: Any) -> Element:
        return Element(
            element_type=ElementType.TABLE,
            text=getattr(element, 'text', '')
        )
    
    def extract_metadata(self, element: Any) -> Dict[str, Any]:
        return {'is_table': True}


class ListItemMapper(ElementMapper):
    """Maps ListItem elements."""
    
    def can_map(self, element: Any) -> bool:
        return type(element).__name__ == 'ListItem'
    
    def map(self, element: Any) -> Element:
        return Element(
            element_type=ElementType.LIST_ITEM,
            text=getattr(element, 'text', '')
        )
    
    def extract_metadata(self, element: Any) -> Dict[str, Any]:
        return {'is_list_item': True}


class ImageMapper(ElementMapper):
    """Maps Image elements."""
    
    def can_map(self, element: Any) -> bool:
        return type(element).__name__ == 'Image'
    
    def map(self, element: Any) -> Element:
        return Element(
            element_type=ElementType.IMAGE,
            text=getattr(element, 'text', '')
        )
    
    def extract_metadata(self, element: Any) -> Dict[str, Any]:
        return {'is_image': True}


class HeaderMapper(ElementMapper):
    """Maps Header elements."""
    
    def can_map(self, element: Any) -> bool:
        return type(element).__name__ == 'Header'
    
    def map(self, element: Any) -> Element:
        return Element(
            element_type=ElementType.HEADER,
            text=getattr(element, 'text', '')
        )
    
    def extract_metadata(self, element: Any) -> Dict[str, Any]:
        return {'is_header': True}


class FooterMapper(ElementMapper):
    """Maps Footer elements."""
    
    def can_map(self, element: Any) -> bool:
        return type(element).__name__ == 'Footer'
    
    def map(self, element: Any) -> Element:
        return Element(
            element_type=ElementType.FOOTER,
            text=getattr(element, 'text', '')
        )
    
    def extract_metadata(self, element: Any) -> Dict[str, Any]:
        return {'is_footer': True}