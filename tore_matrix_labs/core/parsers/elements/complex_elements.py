"""
Complex Element Types for Document Parsing

This module defines complex element types including diagrams,
formulas, code blocks, and other specialized content.
"""

import re
from typing import Dict, List, Optional, Any, Tuple

from .base_element import ParsedElement, ElementType, BoundingBox, ElementMetadata
from .image_elements import ImageElement


class DiagramElement(ParsedElement):
    """Diagram element with structured data and optional image"""
    
    def __init__(
        self,
        diagram_type: str,
        data: Dict[str, Any],
        image: Optional[ImageElement] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        bbox: Optional[BoundingBox] = None,
        metadata: Optional[ElementMetadata] = None,
        parent_id: Optional[str] = None,
        children_ids: Optional[List[str]] = None
    ):
        """
        Initialize diagram element
        
        Args:
            diagram_type: Type of diagram (flowchart, uml, etc.)
            data: Structured diagram data
            image: Optional rendered image of diagram
            title: Diagram title
            description: Diagram description
            bbox: Bounding box location
            metadata: Element metadata
            parent_id: Parent element ID
            children_ids: Child element IDs
        """
        content = {
            'type': diagram_type,
            'data': data,
            'image': image,
            'title': title,
            'description': description
        }
        
        super().__init__(ElementType.DIAGRAM, content, bbox, metadata, parent_id, children_ids)
        
        # Add diagram type to metadata
        self.metadata.add_attribute('diagram_type', diagram_type)
        
        # Add image as child if present
        if image:
            self.add_child(image.id)
    
    def get_text(self) -> str:
        """Get text representation"""
        parts = []
        
        if self.content['title']:
            parts.append(f"Diagram: {self.content['title']}")
        else:
            parts.append(f"{self.content['type'].title()} Diagram")
        
        if self.content['description']:
            parts.append(self.content['description'])
        
        # Add textual representation of data if possible
        if self.content['type'] == 'flowchart' and 'nodes' in self.content['data']:
            nodes = self.content['data']['nodes']
            parts.append(f"Contains {len(nodes)} nodes")
        
        return '\n'.join(parts)
    
    def get_diagram_type(self) -> str:
        """Get diagram type"""
        return self.content['type']
    
    def get_data(self) -> Dict[str, Any]:
        """Get structured diagram data"""
        return self.content['data']
    
    def get_image(self) -> Optional[ImageElement]:
        """Get rendered image if available"""
        return self.content['image']
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            'id': self.id,
            'element_type': self.element_type.value,
            'diagram_type': self.content['type'],
            'data': self.content['data'],
            'title': self.content['title'],
            'description': self.content['description'],
            'bbox': self.bbox.to_dict() if self.bbox else None,
            'metadata': self.metadata.to_dict(),
            'parent_id': self.parent_id,
            'children_ids': self.children_ids
        }
        
        if self.content['image']:
            data['image'] = self.content['image'].to_dict()
        
        return data
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate diagram element"""
        if not self.content['type']:
            return False, "Diagram must have a type"
        
        if not self.content['data']:
            return False, "Diagram must have data"
        
        # Validate known diagram types
        known_types = ['flowchart', 'uml', 'sequence', 'gantt', 'mindmap', 'network']
        if self.content['type'] not in known_types:
            return True, f"Unknown diagram type: {self.content['type']}"
        
        # Validate image if present
        if self.content['image']:
            is_valid, error = self.content['image'].validate()
            if not is_valid:
                return False, f"Invalid diagram image: {error}"
        
        return True, None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DiagramElement':
        """Create from dictionary"""
        image = None
        if data.get('image'):
            image = ImageElement.from_dict(data['image'])
        
        bbox = None
        if data.get('bbox'):
            bbox = BoundingBox(**data['bbox'])
        
        metadata = ElementMetadata()
        if data.get('metadata'):
            metadata = ElementMetadata(**data['metadata'])
        
        return cls(
            diagram_type=data['diagram_type'],
            data=data['data'],
            image=image,
            title=data.get('title'),
            description=data.get('description'),
            bbox=bbox,
            metadata=metadata,
            parent_id=data.get('parent_id'),
            children_ids=data.get('children_ids', [])
        )


class FormulaElement(ParsedElement):
    """Mathematical formula or equation element"""
    
    def __init__(
        self,
        formula: str,
        format: str = "latex",
        rendered_text: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
        bbox: Optional[BoundingBox] = None,
        metadata: Optional[ElementMetadata] = None,
        parent_id: Optional[str] = None,
        children_ids: Optional[List[str]] = None
    ):
        """
        Initialize formula element
        
        Args:
            formula: Formula string in specified format
            format: Formula format (latex, mathml, asciimath)
            rendered_text: Plain text rendering of formula
            variables: Dictionary of variable definitions
            bbox: Bounding box location
            metadata: Element metadata
            parent_id: Parent element ID
            children_ids: Child element IDs
        """
        content = {
            'formula': formula,
            'format': format,
            'rendered_text': rendered_text,
            'variables': variables or {}
        }
        
        super().__init__(ElementType.FORMULA, content, bbox, metadata, parent_id, children_ids)
        
        # Add format to metadata
        self.metadata.add_attribute('format', format)
    
    def get_text(self) -> str:
        """Get text representation"""
        if self.content['rendered_text']:
            return self.content['rendered_text']
        
        # For LaTeX, try to extract a simple representation
        if self.content['format'] == 'latex':
            # Remove common LaTeX commands
            text = self.content['formula']
            text = re.sub(r'\\[a-zA-Z]+\{([^}]+)\}', r'\1', text)
            text = re.sub(r'\\[a-zA-Z]+', '', text)
            text = re.sub(r'[{}]', '', text)
            text = re.sub(r'\^', '^', text)
            text = re.sub(r'_', '_', text)
            return text.strip()
        
        return self.content['formula']
    
    def get_formula(self) -> str:
        """Get formula string"""
        return self.content['formula']
    
    def get_format(self) -> str:
        """Get formula format"""
        return self.content['format']
    
    def get_variables(self) -> Dict[str, str]:
        """Get variable definitions"""
        return self.content['variables']
    
    def add_variable(self, name: str, description: str) -> None:
        """Add variable definition"""
        self.content['variables'][name] = description
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'type': self.element_type.value,
            'formula': self.content['formula'],
            'format': self.content['format'],
            'rendered_text': self.content['rendered_text'],
            'variables': self.content['variables'],
            'bbox': self.bbox.to_dict() if self.bbox else None,
            'metadata': self.metadata.to_dict(),
            'parent_id': self.parent_id,
            'children_ids': self.children_ids
        }
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate formula element"""
        if not self.content['formula']:
            return False, "Formula cannot be empty"
        
        valid_formats = ['latex', 'mathml', 'asciimath', 'plain']
        if self.content['format'] not in valid_formats:
            return False, f"Invalid formula format: {self.content['format']}"
        
        # Basic LaTeX validation
        if self.content['format'] == 'latex':
            # Check for balanced braces
            open_braces = self.content['formula'].count('{')
            close_braces = self.content['formula'].count('}')
            if open_braces != close_braces:
                return False, "Unbalanced braces in LaTeX formula"
        
        return True, None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FormulaElement':
        """Create from dictionary"""
        bbox = None
        if data.get('bbox'):
            bbox = BoundingBox(**data['bbox'])
        
        metadata = ElementMetadata()
        if data.get('metadata'):
            metadata = ElementMetadata(**data['metadata'])
        
        return cls(
            formula=data['formula'],
            format=data.get('format', 'latex'),
            rendered_text=data.get('rendered_text'),
            variables=data.get('variables'),
            bbox=bbox,
            metadata=metadata,
            parent_id=data.get('parent_id'),
            children_ids=data.get('children_ids', [])
        )


class CodeElement(ParsedElement):
    """Code block or snippet element"""
    
    def __init__(
        self,
        code: str,
        language: Optional[str] = None,
        filename: Optional[str] = None,
        line_numbers: bool = False,
        highlighted: bool = False,
        bbox: Optional[BoundingBox] = None,
        metadata: Optional[ElementMetadata] = None,
        parent_id: Optional[str] = None,
        children_ids: Optional[List[str]] = None
    ):
        """
        Initialize code element
        
        Args:
            code: Code content
            language: Programming language
            filename: Source filename if applicable
            line_numbers: Whether to show line numbers
            highlighted: Whether syntax highlighting is applied
            bbox: Bounding box location
            metadata: Element metadata
            parent_id: Parent element ID
            children_ids: Child element IDs
        """
        content = {
            'code': code,
            'language': language,
            'filename': filename,
            'line_numbers': line_numbers,
            'highlighted': highlighted
        }
        
        super().__init__(ElementType.CODE, content, bbox, metadata, parent_id, children_ids)
        
        # Add language to metadata
        if language:
            self.metadata.add_attribute('language', language)
            self.metadata.language = language
    
    def get_text(self) -> str:
        """Get code text"""
        return self.content['code']
    
    def get_language(self) -> Optional[str]:
        """Get programming language"""
        return self.content['language']
    
    def get_line_count(self) -> int:
        """Get number of lines"""
        return len(self.content['code'].splitlines())
    
    def get_lines(self) -> List[str]:
        """Get code lines"""
        return self.content['code'].splitlines()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'type': self.element_type.value,
            'code': self.content['code'],
            'language': self.content['language'],
            'filename': self.content['filename'],
            'line_numbers': self.content['line_numbers'],
            'highlighted': self.content['highlighted'],
            'bbox': self.bbox.to_dict() if self.bbox else None,
            'metadata': self.metadata.to_dict(),
            'parent_id': self.parent_id,
            'children_ids': self.children_ids
        }
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate code element"""
        if not self.content['code']:
            return False, "Code content cannot be empty"
        
        # Check for reasonable code size
        if len(self.content['code']) > 100000:
            return True, "Very large code block"
        
        # Validate language if specified
        if self.content['language']:
            # List of common programming languages
            common_languages = [
                'python', 'javascript', 'java', 'c', 'cpp', 'csharp', 'go',
                'rust', 'ruby', 'php', 'swift', 'kotlin', 'typescript',
                'html', 'css', 'sql', 'bash', 'shell', 'yaml', 'json', 'xml'
            ]
            
            lang_lower = self.content['language'].lower()
            if lang_lower not in common_languages:
                return True, f"Uncommon language: {self.content['language']}"
        
        return True, None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeElement':
        """Create from dictionary"""
        bbox = None
        if data.get('bbox'):
            bbox = BoundingBox(**data['bbox'])
        
        metadata = ElementMetadata()
        if data.get('metadata'):
            metadata = ElementMetadata(**data['metadata'])
        
        return cls(
            code=data['code'],
            language=data.get('language'),
            filename=data.get('filename'),
            line_numbers=data.get('line_numbers', False),
            highlighted=data.get('highlighted', False),
            bbox=bbox,
            metadata=metadata,
            parent_id=data.get('parent_id'),
            children_ids=data.get('children_ids', [])
        )