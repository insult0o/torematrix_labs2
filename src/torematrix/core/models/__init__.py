"""
Core models for TORE Matrix Labs V3.

This module provides the unified element model for document processing.
"""

from .element import Element, ElementType
from .base_types import (
    TitleElement,
    NarrativeTextElement,
    ListItemElement,
    HeaderElement,
    FooterElement,
    create_title,
    create_narrative_text,
    create_list_item,
    create_header,
    create_footer,
)
# TODO: Replace with actual implementations from Agent 2
try:
    from .metadata import ElementMetadata
    from .coordinates import Coordinates
except ImportError:
    # Use stubs until Agent 2 implements these
    from .metadata_stub import ElementMetadata, Coordinates

__all__ = [
    # Core classes
    "Element",
    "ElementType",
    "ElementMetadata",
    "Coordinates",
    # Base element types
    "TitleElement",
    "NarrativeTextElement",
    "ListItemElement",
    "HeaderElement",
    "FooterElement",
    # Factory functions
    "create_title",
    "create_narrative_text",
    "create_list_item",
    "create_header",
    "create_footer",
]