"""
Text Element Types for Document Parsing

This module defines text-based element types including paragraphs,
headings, lists, and other textual content.
"""

import re
from typing import Dict, List, Optional, Any, Tuple

from .base_element import ParsedElement, ElementType, BoundingBox, ElementMetadata


class TextElement(ParsedElement):
    """Base class for text-based elements"""
    
    def __init__(
        self,
        content: str,
        element_type: ElementType = ElementType.TEXT,
        bbox: Optional[BoundingBox] = None,
        metadata: Optional[ElementMetadata] = None,
        parent_id: Optional[str] = None,
        children_ids: Optional[List[str]] = None
    ):
        """Initialize text element"""
        super().__init__(element_type, content, bbox, metadata, parent_id, children_ids)
        self._normalized_text = None
    
    def get_text(self) -> str:
        """Get text content"""
        return str(self.content)
    
    def get_normalized_text(self) -> str:
        """Get normalized text (cached)"""
        if self._normalized_text is None:
            self._normalized_text = self._normalize_text(self.get_text())
        return self._normalized_text
    
    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize text by removing extra whitespace"""
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'type': self.element_type.value,
            'content': self.content,
            'bbox': self.bbox.to_dict() if self.bbox else None,
            'metadata': self.metadata.to_dict(),
            'parent_id': self.parent_id,
            'children_ids': self.children_ids
        }
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate text element"""
        if not self.content:
            return False, "Text content is empty"
        
        if not isinstance(self.content, str):
            return False, f"Content must be string, got {type(self.content)}"
        
        # Check for suspicious content
        if len(self.content) > 100000:
            return False, "Text content exceeds maximum length"
        
        return True, None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextElement':
        """Create from dictionary"""
        bbox = None
        if data.get('bbox'):
            bbox = BoundingBox(**data['bbox'])
        
        metadata = ElementMetadata()
        if data.get('metadata'):
            metadata = ElementMetadata(**data['metadata'])
        
        return cls(
            content=data['content'],
            element_type=ElementType(data['type']),
            bbox=bbox,
            metadata=metadata,
            parent_id=data.get('parent_id'),
            children_ids=data.get('children_ids', [])
        )


class HeadingElement(TextElement):
    """Heading element with level information"""
    
    def __init__(
        self,
        content: str,
        level: int = 1,
        bbox: Optional[BoundingBox] = None,
        metadata: Optional[ElementMetadata] = None,
        parent_id: Optional[str] = None,
        children_ids: Optional[List[str]] = None
    ):
        """Initialize heading element"""
        super().__init__(content, ElementType.HEADING, bbox, metadata, parent_id, children_ids)
        self.level = max(1, min(6, level))  # Clamp to H1-H6
        self.metadata.add_attribute('level', self.level)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = super().to_dict()
        data['level'] = self.level
        return data
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate heading element"""
        is_valid, error = super().validate()
        if not is_valid:
            return is_valid, error
        
        if self.level < 1 or self.level > 6:
            return False, f"Invalid heading level: {self.level}"
        
        return True, None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HeadingElement':
        """Create from dictionary"""
        bbox = None
        if data.get('bbox'):
            bbox = BoundingBox(**data['bbox'])
        
        metadata = ElementMetadata()
        if data.get('metadata'):
            metadata = ElementMetadata(**data['metadata'])
        
        return cls(
            content=data['content'],
            level=data.get('level', 1),
            bbox=bbox,
            metadata=metadata,
            parent_id=data.get('parent_id'),
            children_ids=data.get('children_ids', [])
        )


class ParagraphElement(TextElement):
    """Paragraph element"""
    
    def __init__(
        self,
        content: str,
        bbox: Optional[BoundingBox] = None,
        metadata: Optional[ElementMetadata] = None,
        parent_id: Optional[str] = None,
        children_ids: Optional[List[str]] = None
    ):
        """Initialize paragraph element"""
        super().__init__(content, ElementType.PARAGRAPH, bbox, metadata, parent_id, children_ids)
    
    def get_sentences(self) -> List[str]:
        """Split paragraph into sentences"""
        # Simple sentence splitting (can be improved with NLP)
        sentences = re.split(r'[.!?]+', self.get_text())
        return [s.strip() for s in sentences if s.strip()]
    
    def get_word_count(self) -> int:
        """Get word count"""
        return len(self.get_text().split())


class ListElement(ParsedElement):
    """List element containing list items"""
    
    def __init__(
        self,
        items: List[str],
        ordered: bool = False,
        bbox: Optional[BoundingBox] = None,
        metadata: Optional[ElementMetadata] = None,
        parent_id: Optional[str] = None,
        children_ids: Optional[List[str]] = None
    ):
        """Initialize list element"""
        super().__init__(ElementType.LIST, items, bbox, metadata, parent_id, children_ids)
        self.ordered = ordered
        self.metadata.add_attribute('ordered', ordered)
    
    def get_text(self) -> str:
        """Get text representation of list"""
        if self.ordered:
            return '\n'.join(f"{i+1}. {item}" for i, item in enumerate(self.content))
        else:
            return '\n'.join(f"• {item}" for item in self.content)
    
    def get_items(self) -> List[str]:
        """Get list items"""
        return self.content
    
    def add_item(self, item: str) -> None:
        """Add item to list"""
        self.content.append(item)
    
    def remove_item(self, index: int) -> None:
        """Remove item from list"""
        if 0 <= index < len(self.content):
            self.content.pop(index)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'type': self.element_type.value,
            'items': self.content,
            'ordered': self.ordered,
            'bbox': self.bbox.to_dict() if self.bbox else None,
            'metadata': self.metadata.to_dict(),
            'parent_id': self.parent_id,
            'children_ids': self.children_ids
        }
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate list element"""
        if not self.content:
            return False, "List has no items"
        
        if not isinstance(self.content, list):
            return False, f"Content must be list, got {type(self.content)}"
        
        for item in self.content:
            if not isinstance(item, str):
                return False, f"List item must be string, got {type(item)}"
        
        return True, None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ListElement':
        """Create from dictionary"""
        bbox = None
        if data.get('bbox'):
            bbox = BoundingBox(**data['bbox'])
        
        metadata = ElementMetadata()
        if data.get('metadata'):
            metadata = ElementMetadata(**data['metadata'])
        
        return cls(
            items=data['items'],
            ordered=data.get('ordered', False),
            bbox=bbox,
            metadata=metadata,
            parent_id=data.get('parent_id'),
            children_ids=data.get('children_ids', [])
        )