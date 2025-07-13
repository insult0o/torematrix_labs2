"""
Base Element Classes for Document Parsing

This module defines the base classes for all parsed elements
in the TORE Matrix Labs document processing framework.
"""

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple


class ElementType(Enum):
    """Types of elements that can be parsed from documents"""
    TEXT = "text"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    TABLE_CELL = "table_cell"
    IMAGE = "image"
    FIGURE = "figure"
    DIAGRAM = "diagram"
    FORMULA = "formula"
    CODE = "code"
    FOOTNOTE = "footnote"
    HEADER = "header"
    FOOTER = "footer"
    PAGE_NUMBER = "page_number"
    CAPTION = "caption"
    UNKNOWN = "unknown"


@dataclass
class BoundingBox:
    """Bounding box for element location in document"""
    x0: float
    y0: float
    x1: float
    y1: float
    page: int
    
    @property
    def width(self) -> float:
        """Get width of bounding box"""
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        """Get height of bounding box"""
        return self.y1 - self.y0
    
    @property
    def area(self) -> float:
        """Get area of bounding box"""
        return self.width * self.height
    
    def contains(self, x: float, y: float) -> bool:
        """Check if point is within bounding box"""
        return self.x0 <= x <= self.x1 and self.y0 <= y <= self.y1
    
    def intersects(self, other: 'BoundingBox') -> bool:
        """Check if this box intersects with another"""
        if self.page != other.page:
            return False
        return not (self.x1 < other.x0 or self.x0 > other.x1 or 
                   self.y1 < other.y0 or self.y0 > other.y1)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary"""
        return {
            'x0': self.x0,
            'y0': self.y0,
            'x1': self.x1,
            'y1': self.y1,
            'page': self.page
        }


@dataclass
class ElementMetadata:
    """Metadata associated with parsed elements"""
    confidence: float = 1.0
    source_parser: Optional[str] = None
    extraction_method: Optional[str] = None
    language: Optional[str] = None
    encoding: Optional[str] = None
    style: Dict[str, Any] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)
    validation_status: Optional[str] = None
    validation_notes: List[str] = field(default_factory=list)
    
    def add_style(self, key: str, value: Any) -> None:
        """Add style information"""
        self.style[key] = value
    
    def add_attribute(self, key: str, value: Any) -> None:
        """Add custom attribute"""
        self.attributes[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'confidence': self.confidence,
            'source_parser': self.source_parser,
            'extraction_method': self.extraction_method,
            'language': self.language,
            'encoding': self.encoding,
            'style': self.style,
            'attributes': self.attributes,
            'validation_status': self.validation_status,
            'validation_notes': self.validation_notes
        }


class ParsedElement(ABC):
    """Abstract base class for all parsed elements"""
    
    def __init__(
        self,
        element_type: ElementType,
        content: Any,
        bbox: Optional[BoundingBox] = None,
        metadata: Optional[ElementMetadata] = None,
        parent_id: Optional[str] = None,
        children_ids: Optional[List[str]] = None
    ):
        """
        Initialize parsed element
        
        Args:
            element_type: Type of the element
            content: Element content
            bbox: Bounding box location
            metadata: Element metadata
            parent_id: ID of parent element
            children_ids: IDs of child elements
        """
        self.element_type = element_type
        self.content = content
        self.bbox = bbox
        self.metadata = metadata or ElementMetadata()
        self.parent_id = parent_id
        self.children_ids = children_ids or []
        self._id = self._generate_id()
        self._cached_text = None
    
    def _generate_id(self) -> str:
        """Generate unique ID for element"""
        content_str = str(self.content)[:100]
        type_str = self.element_type.value
        bbox_str = str(self.bbox.to_dict()) if self.bbox else ""
        
        hash_input = f"{type_str}:{content_str}:{bbox_str}:{datetime.now().isoformat()}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    @property
    def id(self) -> str:
        """Get element ID"""
        return self._id
    
    @abstractmethod
    def get_text(self) -> str:
        """Get text representation of element"""
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert element to dictionary for serialization"""
        pass
    
    @abstractmethod
    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate element content and structure
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
    
    def get_confidence(self) -> float:
        """Get confidence score for element"""
        return self.metadata.confidence
    
    def set_confidence(self, confidence: float) -> None:
        """Set confidence score"""
        self.metadata.confidence = max(0.0, min(1.0, confidence))
    
    def add_child(self, child_id: str) -> None:
        """Add child element ID"""
        if child_id not in self.children_ids:
            self.children_ids.append(child_id)
    
    def remove_child(self, child_id: str) -> None:
        """Remove child element ID"""
        if child_id in self.children_ids:
            self.children_ids.remove(child_id)
    
    def has_children(self) -> bool:
        """Check if element has children"""
        return len(self.children_ids) > 0
    
    def get_size(self) -> int:
        """Get size of element content in bytes"""
        return len(self.get_text().encode('utf-8'))
    
    def to_json(self) -> str:
        """Convert element to JSON string"""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParsedElement':
        """Create element from dictionary"""
        pass
    
    def __repr__(self) -> str:
        """String representation"""
        return f"{self.__class__.__name__}(type={self.element_type.value}, id={self.id[:8]}...)"