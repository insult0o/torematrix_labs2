"""
Core element type implementations.

This module provides factory functions for creating base element types
including Title, NarrativeText, ListItem, Header, and Footer.

Since Element is immutable and we want proper ID generation, we use
factory functions instead of subclasses.
"""

from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .element import Element
    from .metadata import ElementMetadata


def _create_element(
    element_type,
    text: str,
    metadata: Optional['ElementMetadata'] = None,
    parent_id: Optional[str] = None,
    element_id: Optional[str] = None,
) -> 'Element':
    """
    Internal helper to create elements without passing None for element_id.
    
    This ensures the default_factory generates IDs when element_id is not provided.
    """
    from .element import Element
    
    elem_kwargs = {
        'element_type': element_type,
        'text': text,
        'metadata': metadata,
        'parent_id': parent_id,
    }
    if element_id is not None:
        elem_kwargs['element_id'] = element_id
        
    return Element(**elem_kwargs)


def create_title(
    text: str,
    metadata: Optional['ElementMetadata'] = None,
    parent_id: Optional[str] = None,
    element_id: Optional[str] = None,
    **kwargs
) -> 'Element':
    """
    Create a Title element.
    
    Args:
        text: The title text content
        metadata: Optional metadata for the element
        parent_id: Optional ID of parent element
        element_id: Optional explicit element ID
        **kwargs: Additional arguments
        
    Returns:
        Element configured as a Title
    """
    from .element import ElementType
    return _create_element(
        element_type=ElementType.TITLE,
        text=text,
        metadata=metadata,
        parent_id=parent_id,
        element_id=element_id
    )


def create_narrative_text(
    text: str,
    metadata: Optional['ElementMetadata'] = None,
    parent_id: Optional[str] = None,
    element_id: Optional[str] = None,
    **kwargs
) -> 'Element':
    """
    Create a NarrativeText element.
    
    Args:
        text: The narrative text content
        metadata: Optional metadata for the element
        parent_id: Optional ID of parent element
        element_id: Optional explicit element ID
        **kwargs: Additional arguments
        
    Returns:
        Element configured as NarrativeText
    """
    from .element import ElementType
    return _create_element(
        element_type=ElementType.NARRATIVE_TEXT,
        text=text,
        metadata=metadata,
        parent_id=parent_id,
        element_id=element_id
    )


def create_list_item(
    text: str,
    parent_id: Optional[str] = None,
    metadata: Optional['ElementMetadata'] = None,
    element_id: Optional[str] = None,
    **kwargs
) -> 'Element':
    """
    Create a ListItem element.
    
    Args:
        text: The list item text content
        parent_id: Optional ID of parent element (usually a List)
        metadata: Optional metadata for the element
        element_id: Optional explicit element ID
        **kwargs: Additional arguments
        
    Returns:
        Element configured as ListItem
    """
    from .element import ElementType
    return _create_element(
        element_type=ElementType.LIST_ITEM,
        text=text,
        metadata=metadata,
        parent_id=parent_id,
        element_id=element_id
    )


def create_header(
    text: str,
    metadata: Optional['ElementMetadata'] = None,
    parent_id: Optional[str] = None,
    element_id: Optional[str] = None,
    **kwargs
) -> 'Element':
    """
    Create a Header element.
    
    Args:
        text: The header text content
        metadata: Optional metadata for the element
        parent_id: Optional ID of parent element
        element_id: Optional explicit element ID
        **kwargs: Additional arguments
        
    Returns:
        Element configured as Header
    """
    from .element import ElementType
    return _create_element(
        element_type=ElementType.HEADER,
        text=text,
        metadata=metadata,
        parent_id=parent_id,
        element_id=element_id
    )


def create_footer(
    text: str,
    metadata: Optional['ElementMetadata'] = None,
    parent_id: Optional[str] = None,
    element_id: Optional[str] = None,
    **kwargs
) -> 'Element':
    """
    Create a Footer element.
    
    Args:
        text: The footer text content
        metadata: Optional metadata for the element
        parent_id: Optional ID of parent element
        element_id: Optional explicit element ID
        **kwargs: Additional arguments
        
    Returns:
        Element configured as Footer
    """
    from .element import ElementType
    return _create_element(
        element_type=ElementType.FOOTER,
        text=text,
        metadata=metadata,
        parent_id=parent_id,
        element_id=element_id
    )


# Convenience classes that act like the old subclasses
class TitleElement:
    """Factory for Title elements."""
    def __new__(cls, text: str, **kwargs):
        return create_title(text=text, **kwargs)


class NarrativeTextElement:
    """Factory for NarrativeText elements."""
    def __new__(cls, text: str, **kwargs):
        return create_narrative_text(text=text, **kwargs)


class ListItemElement:
    """Factory for ListItem elements."""
    def __new__(cls, text: str, **kwargs):
        return create_list_item(text=text, **kwargs)


class HeaderElement:
    """Factory for Header elements."""
    def __new__(cls, text: str, **kwargs):
        return create_header(text=text, **kwargs)


class FooterElement:
    """Factory for Footer elements."""
    def __new__(cls, text: str, **kwargs):
        return create_footer(text=text, **kwargs)