"""
Element Factory for creating and converting document elements.
Supports creation of all element types with validation and batch operations.
"""

from typing import Any, Dict, List, Optional, Union
import uuid
from dataclasses import asdict

from .element import Element, ElementType
from .metadata import ElementMetadata
from .coordinates import Coordinates
from .validators import validate_metadata


class ElementFactory:
    """Factory for creating document elements with validation"""
    
    @staticmethod
    def create_element(
        element_type: Union[ElementType, str],
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        element_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        **kwargs
    ) -> Element:
        """
        Create element with validation
        
        Args:
            element_type: Type of element to create
            text: Element text content
            metadata: Optional metadata dictionary
            element_id: Optional custom element ID
            parent_id: Optional parent element ID
            **kwargs: Additional metadata fields
            
        Returns:
            Validated Element instance
            
        Raises:
            ValueError: If element type is invalid or metadata validation fails
        """
        # Convert string to ElementType if needed
        if isinstance(element_type, str):
            try:
                element_type = ElementType(element_type)
            except ValueError:
                raise ValueError(f"Invalid element type: {element_type}")
        
        # Generate ID if not provided
        if not element_id:
            element_id = str(uuid.uuid4())
        
        # Build metadata
        metadata_dict = metadata or {}
        metadata_dict.update(kwargs)
        
        # Create ElementMetadata instance
        coordinates = None
        if 'coordinates' in metadata_dict:
            coord_data = metadata_dict['coordinates']
            if coord_data:
                coordinates = Coordinates(
                    layout_bbox=coord_data.get('layout_bbox'),
                    text_bbox=coord_data.get('text_bbox'),
                    points=coord_data.get('points'),
                    system=coord_data.get('system', 'pixel')
                )
        
        element_metadata = ElementMetadata(
            coordinates=coordinates,
            confidence=metadata_dict.get('confidence', 1.0),
            detection_method=metadata_dict.get('detection_method', 'factory'),
            page_number=metadata_dict.get('page_number'),
            languages=metadata_dict.get('languages', []),
            custom_fields=metadata_dict.get('custom_fields', {})
        )
        
        # Create appropriate element type based on element_type
        if element_type == ElementType.TABLE:
            from .complex_types import TableElement, TableMetadata
            cells = kwargs.get('cells', [])
            headers = kwargs.get('headers')
            table_metadata = TableMetadata(
                num_rows=len(cells),
                num_cols=max(len(row) for row in cells) if cells else 0,
                has_header=headers is not None
            )
            return TableElement(
                element_id=element_id,
                element_type=element_type,
                text=text,
                metadata=element_metadata,
                parent_id=parent_id,
                cells=cells,
                headers=headers,
                table_metadata=table_metadata
            )
        elif element_type == ElementType.IMAGE:
            from .complex_types import ImageElement, ImageMetadata
            return ImageElement(
                element_id=element_id,
                element_type=element_type,
                text=text,
                metadata=element_metadata,
                parent_id=parent_id,
                image_data=kwargs.get('image_data'),
                image_url=kwargs.get('image_url'),
                alt_text=kwargs.get('alt_text', text),
                caption=kwargs.get('caption'),
                image_metadata=ImageMetadata(
                    width=kwargs.get('width'),
                    height=kwargs.get('height'),
                    format=kwargs.get('format')
                )
            )
        elif element_type == ElementType.FORMULA:
            from .complex_types import FormulaElement, FormulaMetadata, FormulaType
            formula_type = kwargs.get('formula_type', FormulaType.INLINE)
            return FormulaElement(
                element_id=element_id,
                element_type=element_type,
                text=text,
                metadata=element_metadata,
                parent_id=parent_id,
                latex=kwargs.get('latex', text),
                mathml=kwargs.get('mathml'),
                formula_metadata=FormulaMetadata(formula_type=formula_type)
            )
        elif element_type == ElementType.CODE_BLOCK:
            from .complex_types import CodeBlockElement, CodeMetadata, CodeLanguage
            language = kwargs.get('language', CodeLanguage.UNKNOWN)
            return CodeBlockElement(
                element_id=element_id,
                element_type=element_type,
                text=text,
                metadata=element_metadata,
                parent_id=parent_id,
                code_metadata=CodeMetadata(
                    language=language,
                    line_count=len(text.split('\n')) if text else 0
                )
            )
        elif element_type == ElementType.PAGE_BREAK:
            from .complex_types import PageBreakElement
            return PageBreakElement(
                element_id=element_id,
                element_type=element_type,
                text=text or "[Page Break]",
                metadata=element_metadata,
                parent_id=parent_id
            )
        else:
            # Default to basic Element for simple types
            return Element(
                element_id=element_id,
                element_type=element_type,
                text=text,
                metadata=element_metadata,
                parent_id=parent_id
            )
    
    @staticmethod
    def from_unstructured(unstructured_element: Any) -> Element:
        """
        Convert from Unstructured library format
        
        Args:
            unstructured_element: Element from unstructured library
            
        Returns:
            Element instance
            
        Raises:
            ValueError: If conversion fails
        """
        try:
            # Extract basic properties
            element_type_str = unstructured_element.category
            text = str(unstructured_element.text or "")
            
            # Extract metadata
            metadata = {}
            
            # Coordinates from unstructured
            if hasattr(unstructured_element, 'metadata') and unstructured_element.metadata:
                uns_metadata = unstructured_element.metadata
                
                # Convert coordinates
                coordinates_data = {}
                if hasattr(uns_metadata, 'coordinates'):
                    coords = uns_metadata.coordinates
                    if coords:
                        if hasattr(coords, 'layout_bbox'):
                            coordinates_data['layout_bbox'] = coords.layout_bbox
                        if hasattr(coords, 'text_bbox'):
                            coordinates_data['text_bbox'] = coords.text_bbox
                        if hasattr(coords, 'points'):
                            coordinates_data['points'] = coords.points
                        if hasattr(coords, 'system'):
                            coordinates_data['system'] = coords.system
                
                if coordinates_data:
                    metadata['coordinates'] = coordinates_data
                
                # Other metadata fields
                if hasattr(uns_metadata, 'confidence'):
                    metadata['confidence'] = uns_metadata.confidence
                if hasattr(uns_metadata, 'detection_class_prob'):
                    metadata['confidence'] = max(uns_metadata.detection_class_prob.values())
                if hasattr(uns_metadata, 'page_number'):
                    metadata['page_number'] = uns_metadata.page_number
                if hasattr(uns_metadata, 'languages'):
                    metadata['languages'] = uns_metadata.languages
                
                metadata['detection_method'] = 'unstructured'
            
            # Generate element ID
            element_id = str(uuid.uuid4())
            
            return ElementFactory.create_element(
                element_type=element_type_str,
                text=text,
                metadata=metadata,
                element_id=element_id
            )
            
        except Exception as e:
            raise ValueError(f"Failed to convert unstructured element: {e}")
    
    @staticmethod
    def create_batch(
        elements_data: List[Dict[str, Any]]
    ) -> List[Element]:
        """
        Batch creation with optimization
        
        Args:
            elements_data: List of element data dictionaries
            
        Returns:
            List of created elements
            
        Raises:
            ValueError: If any element creation fails
        """
        elements = []
        
        for i, data in enumerate(elements_data):
            try:
                element = ElementFactory.create_element(**data)
                elements.append(element)
            except Exception as e:
                raise ValueError(f"Failed to create element at index {i}: {e}")
        
        return elements
    
    @staticmethod
    def create_from_text(
        text: str,
        element_type: Union[ElementType, str] = ElementType.NARRATIVE_TEXT,
        page_number: Optional[int] = None,
        **kwargs
    ) -> Element:
        """
        Quick element creation from text with minimal metadata
        
        Args:
            text: Element text content
            element_type: Type of element (default: NARRATIVE_TEXT)
            page_number: Optional page number
            **kwargs: Additional metadata
            
        Returns:
            Element instance
        """
        metadata = {}
        if page_number is not None:
            metadata['page_number'] = page_number
        metadata.update(kwargs)
        
        return ElementFactory.create_element(
            element_type=element_type,
            text=text,
            metadata=metadata if metadata else None
        )
    
    @staticmethod
    def clone_element(
        element: Element,
        **overrides
    ) -> Element:
        """
        Clone an element with optional property overrides
        
        Args:
            element: Source element to clone
            **overrides: Properties to override in the clone
            
        Returns:
            New element instance with specified changes
        """
        # Generate new ID unless explicitly overridden
        if 'element_id' not in overrides:
            overrides['element_id'] = str(uuid.uuid4())
        
        return element.copy_with(**overrides)


class ElementTransformer:
    """Utilities for transforming and converting elements"""
    
    @staticmethod
    def change_type(
        element: Element,
        new_type: Union[ElementType, str]
    ) -> Element:
        """
        Change element type while preserving other properties
        
        Args:
            element: Source element
            new_type: New element type
            
        Returns:
            Element with new type
        """
        return ElementFactory.clone_element(
            element,
            element_type=new_type.value if isinstance(new_type, ElementType) else new_type
        )
    
    @staticmethod
    def merge_text(
        elements: List[Element],
        separator: str = " ",
        new_type: Union[ElementType, str] = ElementType.NARRATIVE_TEXT
    ) -> Element:
        """
        Merge multiple elements into a single element
        
        Args:
            elements: Elements to merge
            separator: Text separator
            new_type: Type for merged element
            
        Returns:
            Merged element
        """
        if not elements:
            raise ValueError("Cannot merge empty list of elements")
        
        # Merge text
        merged_text = separator.join(elem.text for elem in elements)
        
        # Use metadata from first element as base
        base_metadata = elements[0].metadata.to_dict() if elements[0].metadata else {}
        
        # Update detection method
        base_metadata['detection_method'] = 'merged'
        base_metadata['custom_fields'] = base_metadata.get('custom_fields', {})
        base_metadata['custom_fields']['merged_from'] = [elem.element_id for elem in elements]
        
        return ElementFactory.create_element(
            element_type=new_type,
            text=merged_text,
            metadata=base_metadata
        )
    
    @staticmethod
    def split_by_sentences(
        element: Element,
        sentence_endings: List[str] = ['.', '!', '?']
    ) -> List[Element]:
        """
        Split element into multiple elements by sentences
        
        Args:
            element: Element to split
            sentence_endings: Characters that end sentences
            
        Returns:
            List of split elements
        """
        text = element.text.strip()
        if not text:
            return [element]
        
        # Simple sentence splitting
        sentences = []
        current = ""
        
        for char in text:
            current += char
            if char in sentence_endings and current.strip():
                sentences.append(current.strip())
                current = ""
        
        if current.strip():
            sentences.append(current.strip())
        
        if len(sentences) <= 1:
            return [element]
        
        # Create new elements for each sentence
        result = []
        base_metadata = element.metadata.to_dict() if element.metadata else {}
        base_metadata['detection_method'] = 'split'
        base_metadata['custom_fields'] = base_metadata.get('custom_fields', {})
        base_metadata['custom_fields']['split_from'] = element.element_id
        
        for i, sentence in enumerate(sentences):
            metadata = base_metadata.copy()
            metadata['custom_fields'] = metadata['custom_fields'].copy()
            metadata['custom_fields']['sentence_index'] = i
            
            new_element = ElementFactory.create_element(
                element_type=element.element_type,
                text=sentence,
                metadata=metadata,
                parent_id=element.element_id
            )
            result.append(new_element)
        
        return result