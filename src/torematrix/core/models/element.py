"""
Base Element model for unified document processing.

This module provides the core Element dataclass that serves as the foundation
for all document elements in the TORE Matrix Labs V3 system.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, TYPE_CHECKING
from enum import Enum
import json
import uuid

if TYPE_CHECKING:
    from .metadata import ElementMetadata


class ElementType(Enum):
    """All supported element types from unstructured library"""
    TITLE = "Title"
    NARRATIVE_TEXT = "NarrativeText"
    LIST_ITEM = "ListItem"
    HEADER = "Header"
    FOOTER = "Footer"
    TEXT = "Text"
    TABLE = "Table"
    TABLE_ROW = "TableRow"
    TABLE_CELL = "TableCell"
    IMAGE = "Image"
    FIGURE = "Figure"
    FIGURE_CAPTION = "FigureCaption"
    FORMULA = "Formula"
    ADDRESS = "Address"
    EMAIL_ADDRESS = "EmailAddress"
    PAGE_BREAK = "PageBreak"
    PAGE_NUMBER = "PageNumber"
    UNCATEGORIZED_TEXT = "UncategorizedText"
    CODE_BLOCK = "CodeBlock"
    LIST = "List"
    COMPOSITE_ELEMENT = "CompositeElement"
    TABLE_OF_CONTENTS = "TableOfContents"


@dataclass(frozen=True)
class Element:
    """
    Base immutable element class for all document elements.
    
    This class provides the foundation for representing document elements
    with full support for serialization, comparison, and hierarchy.
    """
    element_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    element_type: ElementType = ElementType.NARRATIVE_TEXT
    text: str = ""
    metadata: Optional['ElementMetadata'] = None
    parent_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate element after initialization."""
        if not isinstance(self.element_type, ElementType):
            raise ValueError(f"element_type must be ElementType, got {type(self.element_type)}")
    
    def __hash__(self) -> int:
        """
        Generate hash for element deduplication.
        
        Hash is based on element_id, type, and text content.
        """
        return hash((self.element_id, self.element_type.value, self.text))
    
    def __eq__(self, other: Any) -> bool:
        """
        Compare elements for equality.
        
        Elements are equal if they have the same ID, type, and text.
        """
        if not isinstance(other, Element):
            return False
        return (
            self.element_id == other.element_id
            and self.element_type == other.element_type
            and self.text == other.text
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize element to dictionary.
        
        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        data = {
            "element_id": self.element_id,
            "element_type": self.element_type.value,
            "text": self.text,
            "parent_id": self.parent_id,
        }
        
        if self.metadata:
            data["metadata"] = self.metadata.to_dict()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Element':
        """
        Deserialize element from dictionary.
        
        Args:
            data: Dictionary containing element data
            
        Returns:
            Element instance reconstructed from data
        """
        # Import from local module
        from .metadata import ElementMetadata
        
        # Handle metadata if present
        metadata = None
        if "metadata" in data and data["metadata"]:
            metadata = ElementMetadata.from_dict(data["metadata"])
        
        return cls(
            element_id=data.get("element_id", str(uuid.uuid4())),
            element_type=ElementType(data["element_type"]),
            text=data.get("text", ""),
            metadata=metadata,
            parent_id=data.get("parent_id"),
        )
    
    def to_json(self) -> str:
        """
        Serialize element to JSON string.
        
        Returns:
            JSON string representation
        """
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Element':
        """
        Deserialize element from JSON string.
        
        Args:
            json_str: JSON string containing element data
            
        Returns:
            Element instance
        """
        return cls.from_dict(json.loads(json_str))
    
    def copy_with(self, **kwargs) -> 'Element':
        """
        Create a new element with modified attributes.
        
        Since elements are immutable, this creates a new instance
        with the specified changes.
        
        Args:
            **kwargs: Attributes to override
            
        Returns:
            New Element instance with modifications
        """
        current_data = self.to_dict()
        current_data.update(kwargs)
        return self.from_dict(current_data)