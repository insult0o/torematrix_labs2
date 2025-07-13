"""
Image Element Types for Document Parsing

This module defines image-related element types including images,
figures, and their associated metadata.
"""

import base64
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union

from .base_element import ParsedElement, ElementType, BoundingBox, ElementMetadata


class ImageElement(ParsedElement):
    """Image element with binary data or reference"""
    
    def __init__(
        self,
        image_data: Optional[bytes] = None,
        image_path: Optional[str] = None,
        format: Optional[str] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        alt_text: Optional[str] = None,
        bbox: Optional[BoundingBox] = None,
        metadata: Optional[ElementMetadata] = None,
        parent_id: Optional[str] = None,
        children_ids: Optional[List[str]] = None
    ):
        """
        Initialize image element
        
        Args:
            image_data: Binary image data
            image_path: Path to image file
            format: Image format (png, jpg, etc.)
            width: Image width in pixels
            height: Image height in pixels
            alt_text: Alternative text description
            bbox: Bounding box location
            metadata: Element metadata
            parent_id: Parent element ID
            children_ids: Child element IDs
        """
        # Store either data or path, not both
        content = {
            'data': image_data,
            'path': image_path,
            'format': format,
            'width': width,
            'height': height,
            'alt_text': alt_text
        }
        
        super().__init__(ElementType.IMAGE, content, bbox, metadata, parent_id, children_ids)
        
        # Calculate checksum if we have data
        if image_data:
            self._checksum = hashlib.md5(image_data).hexdigest()
        else:
            self._checksum = None
        
        # Add image properties to metadata
        if format:
            self.metadata.add_attribute('format', format)
        if width and height:
            self.metadata.add_attribute('dimensions', {'width': width, 'height': height})
    
    def get_text(self) -> str:
        """Get text representation (alt text or description)"""
        return self.content.get('alt_text', f"Image ({self.content.get('format', 'unknown')} format)")
    
    def get_image_data(self) -> Optional[bytes]:
        """Get image binary data"""
        if self.content.get('data'):
            return self.content['data']
        
        # Try to load from path if available
        if self.content.get('path'):
            path = Path(self.content['path'])
            if path.exists():
                try:
                    with open(path, 'rb') as f:
                        return f.read()
                except Exception:
                    pass
        
        return None
    
    def get_base64(self) -> Optional[str]:
        """Get base64 encoded image data"""
        data = self.get_image_data()
        if data:
            return base64.b64encode(data).decode('utf-8')
        return None
    
    def get_data_uri(self) -> Optional[str]:
        """Get data URI for embedding in HTML"""
        base64_data = self.get_base64()
        if base64_data and self.content.get('format'):
            mime_type = f"image/{self.content['format'].lower()}"
            return f"data:{mime_type};base64,{base64_data}"
        return None
    
    def get_dimensions(self) -> Tuple[Optional[int], Optional[int]]:
        """Get image dimensions (width, height)"""
        return self.content.get('width'), self.content.get('height')
    
    def set_alt_text(self, alt_text: str) -> None:
        """Set alternative text"""
        self.content['alt_text'] = alt_text
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'type': self.element_type.value,
            'format': self.content.get('format'),
            'width': self.content.get('width'),
            'height': self.content.get('height'),
            'alt_text': self.content.get('alt_text'),
            'bbox': self.bbox.to_dict() if self.bbox else None,
            'metadata': self.metadata.to_dict(),
            'parent_id': self.parent_id,
            'children_ids': self.children_ids
        }
        
        # Include either data or path
        if self.content.get('data'):
            data['data_base64'] = self.get_base64()
            data['checksum'] = self._checksum
        elif self.content.get('path'):
            data['path'] = self.content['path']
        
        return data
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate image element"""
        # Must have either data or path
        if not self.content.get('data') and not self.content.get('path'):
            return False, "Image must have either data or path"
        
        # Validate format if specified
        if self.content.get('format'):
            valid_formats = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'svg', 'webp']
            if self.content['format'].lower() not in valid_formats:
                return True, f"Unusual image format: {self.content['format']}"
        
        # Validate dimensions if specified
        if self.content.get('width') or self.content.get('height'):
            width = self.content.get('width', 0)
            height = self.content.get('height', 0)
            if width <= 0 or height <= 0:
                return False, f"Invalid dimensions: {width}x{height}"
            if width > 10000 or height > 10000:
                return True, f"Very large image dimensions: {width}x{height}"
        
        return True, None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImageElement':
        """Create from dictionary"""
        # Decode base64 data if present
        image_data = None
        if data.get('data_base64'):
            image_data = base64.b64decode(data['data_base64'])
        
        bbox = None
        if data.get('bbox'):
            bbox = BoundingBox(**data['bbox'])
        
        metadata = ElementMetadata()
        if data.get('metadata'):
            metadata = ElementMetadata(**data['metadata'])
        
        return cls(
            image_data=image_data,
            image_path=data.get('path'),
            format=data.get('format'),
            width=data.get('width'),
            height=data.get('height'),
            alt_text=data.get('alt_text'),
            bbox=bbox,
            metadata=metadata,
            parent_id=data.get('parent_id'),
            children_ids=data.get('children_ids', [])
        )


class FigureElement(ParsedElement):
    """Figure element containing image with caption"""
    
    def __init__(
        self,
        image_element: ImageElement,
        caption: Optional[str] = None,
        figure_number: Optional[str] = None,
        bbox: Optional[BoundingBox] = None,
        metadata: Optional[ElementMetadata] = None,
        parent_id: Optional[str] = None,
        children_ids: Optional[List[str]] = None
    ):
        """
        Initialize figure element
        
        Args:
            image_element: The image element
            caption: Figure caption text
            figure_number: Figure number (e.g., "Figure 1.2")
            bbox: Bounding box location
            metadata: Element metadata
            parent_id: Parent element ID
            children_ids: Child element IDs
        """
        content = {
            'image': image_element,
            'caption': caption,
            'figure_number': figure_number
        }
        
        super().__init__(ElementType.FIGURE, content, bbox, metadata, parent_id, children_ids)
        
        # Add image as child
        self.add_child(image_element.id)
        
        # Add figure properties to metadata
        if figure_number:
            self.metadata.add_attribute('figure_number', figure_number)
    
    def get_text(self) -> str:
        """Get text representation"""
        parts = []
        
        if self.content['figure_number']:
            parts.append(self.content['figure_number'])
        
        if self.content['caption']:
            parts.append(self.content['caption'])
        
        if not parts:
            parts.append(self.content['image'].get_text())
        
        return ': '.join(parts)
    
    def get_image(self) -> ImageElement:
        """Get the image element"""
        return self.content['image']
    
    def get_caption(self) -> Optional[str]:
        """Get figure caption"""
        return self.content['caption']
    
    def set_caption(self, caption: str) -> None:
        """Set figure caption"""
        self.content['caption'] = caption
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'type': self.element_type.value,
            'image': self.content['image'].to_dict(),
            'caption': self.content['caption'],
            'figure_number': self.content['figure_number'],
            'bbox': self.bbox.to_dict() if self.bbox else None,
            'metadata': self.metadata.to_dict(),
            'parent_id': self.parent_id,
            'children_ids': self.children_ids
        }
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate figure element"""
        if not self.content.get('image'):
            return False, "Figure must have an image"
        
        if not isinstance(self.content['image'], ImageElement):
            return False, "Figure image must be ImageElement instance"
        
        # Validate the image
        is_valid, error = self.content['image'].validate()
        if not is_valid:
            return False, f"Invalid image: {error}"
        
        return True, None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FigureElement':
        """Create from dictionary"""
        # Create image element
        image_element = ImageElement.from_dict(data['image'])
        
        bbox = None
        if data.get('bbox'):
            bbox = BoundingBox(**data['bbox'])
        
        metadata = ElementMetadata()
        if data.get('metadata'):
            metadata = ElementMetadata(**data['metadata'])
        
        return cls(
            image_element=image_element,
            caption=data.get('caption'),
            figure_number=data.get('figure_number'),
            bbox=bbox,
            metadata=metadata,
            parent_id=data.get('parent_id'),
            children_ids=data.get('children_ids', [])
        )