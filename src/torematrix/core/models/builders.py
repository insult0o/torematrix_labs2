"""
Builder patterns for complex element construction.
Provides fluent interfaces for creating elements with complex structures.
"""

from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, field

from .element import Element, ElementType
from .factory import ElementFactory
from .metadata import ElementMetadata
from .coordinates import Coordinates


@dataclass
class TableCell:
    """Represents a table cell with content and properties"""
    content: str
    col_span: int = 1
    row_span: int = 1
    is_header: bool = False
    metadata: Optional[Dict[str, Any]] = None


@dataclass 
class TableRow:
    """Represents a table row with cells"""
    cells: List[TableCell] = field(default_factory=list)
    is_header: bool = False
    metadata: Optional[Dict[str, Any]] = None


class ElementBuilder:
    """Base builder for creating elements with fluent interface"""
    
    def __init__(self, element_type: Union[ElementType, str]):
        self.element_type = element_type
        self.text = ""
        self.metadata: Dict[str, Any] = {}
        self.element_id: Optional[str] = None
        self.parent_id: Optional[str] = None
    
    def with_text(self, text: str) -> 'ElementBuilder':
        """Set element text"""
        self.text = text
        return self
    
    def with_id(self, element_id: str) -> 'ElementBuilder':
        """Set element ID"""
        self.element_id = element_id
        return self
    
    def with_parent(self, parent_id: str) -> 'ElementBuilder':
        """Set parent element ID"""
        self.parent_id = parent_id
        return self
    
    def with_coordinates(
        self,
        layout_bbox: Optional[Tuple[float, float, float, float]] = None,
        text_bbox: Optional[Tuple[float, float, float, float]] = None,
        points: Optional[List[Tuple[float, float]]] = None,
        system: str = "pixel"
    ) -> 'ElementBuilder':
        """Set coordinate information"""
        coords = {
            'layout_bbox': layout_bbox,
            'text_bbox': text_bbox,
            'points': points,
            'system': system
        }
        # Remove None values
        coords = {k: v for k, v in coords.items() if v is not None}
        
        if coords:
            self.metadata['coordinates'] = coords
        return self
    
    def with_confidence(self, confidence: float) -> 'ElementBuilder':
        """Set detection confidence"""
        self.metadata['confidence'] = confidence
        return self
    
    def with_page(self, page_number: int) -> 'ElementBuilder':
        """Set page number"""
        self.metadata['page_number'] = page_number
        return self
    
    def with_languages(self, languages: List[str]) -> 'ElementBuilder':
        """Set detected languages"""
        self.metadata['languages'] = languages
        return self
    
    def with_custom_field(self, key: str, value: Any) -> 'ElementBuilder':
        """Add custom metadata field"""
        if 'custom_fields' not in self.metadata:
            self.metadata['custom_fields'] = {}
        self.metadata['custom_fields'][key] = value
        return self
    
    def with_detection_method(self, method: str) -> 'ElementBuilder':
        """Set detection method"""
        self.metadata['detection_method'] = method
        return self
    
    def build(self) -> Element:
        """Build the element"""
        return ElementFactory.create_element(
            element_type=self.element_type,
            text=self.text,
            metadata=self.metadata,
            element_id=self.element_id,
            parent_id=self.parent_id
        )


class TableBuilder:
    """Builder for complex table elements with rows and cells"""
    
    def __init__(self):
        self.rows: List[TableRow] = []
        self.headers: List[str] = []
        self.metadata: Dict[str, Any] = {}
        self.element_id: Optional[str] = None
        self.parent_id: Optional[str] = None
        self.caption: Optional[str] = None
    
    def with_id(self, element_id: str) -> 'TableBuilder':
        """Set table element ID"""
        self.element_id = element_id
        return self
    
    def with_parent(self, parent_id: str) -> 'TableBuilder':
        """Set parent element ID"""
        self.parent_id = parent_id
        return self
    
    def with_caption(self, caption: str) -> 'TableBuilder':
        """Set table caption"""
        self.caption = caption
        return self
    
    def with_coordinates(
        self,
        layout_bbox: Optional[Tuple[float, float, float, float]] = None,
        text_bbox: Optional[Tuple[float, float, float, float]] = None,
        system: str = "pixel"
    ) -> 'TableBuilder':
        """Set coordinate information"""
        coords = {
            'layout_bbox': layout_bbox,
            'text_bbox': text_bbox,
            'system': system
        }
        # Remove None values
        coords = {k: v for k, v in coords.items() if v is not None}
        
        if coords:
            self.metadata['coordinates'] = coords
        return self
    
    def with_page(self, page_number: int) -> 'TableBuilder':
        """Set page number"""
        self.metadata['page_number'] = page_number
        return self
    
    def add_header_row(self, headers: List[str]) -> 'TableBuilder':
        """Add header row to table"""
        self.headers = headers
        header_cells = [TableCell(content=header, is_header=True) for header in headers]
        header_row = TableRow(cells=header_cells, is_header=True)
        self.rows.append(header_row)
        return self
    
    def add_row(self, cells: List[Union[str, TableCell]]) -> 'TableBuilder':
        """Add data row to table"""
        table_cells = []
        for cell in cells:
            if isinstance(cell, str):
                table_cells.append(TableCell(content=cell))
            else:
                table_cells.append(cell)
        
        row = TableRow(cells=table_cells)
        self.rows.append(row)
        return self
    
    def add_cell(self, content: str, col_span: int = 1, row_span: int = 1, is_header: bool = False) -> TableCell:
        """Create a table cell for use in add_row"""
        return TableCell(
            content=content,
            col_span=col_span,
            row_span=row_span,
            is_header=is_header
        )
    
    def with_custom_field(self, key: str, value: Any) -> 'TableBuilder':
        """Add custom metadata field"""
        if 'custom_fields' not in self.metadata:
            self.metadata['custom_fields'] = {}
        self.metadata['custom_fields'][key] = value
        return self
    
    def build(self) -> Element:
        """Build the table element"""
        # Generate table text representation
        table_text = self._generate_table_text()
        
        # Add table-specific metadata
        table_metadata = self.metadata.copy()
        table_metadata['custom_fields'] = table_metadata.get('custom_fields', {})
        table_metadata['custom_fields']['table_structure'] = {
            'rows': len(self.rows),
            'columns': len(self.headers) if self.headers else (len(self.rows[0].cells) if self.rows else 0),
            'has_headers': bool(self.headers),
            'caption': self.caption
        }
        
        # Store detailed table data
        table_metadata['custom_fields']['table_data'] = self._serialize_table_data()
        
        return ElementFactory.create_element(
            element_type=ElementType.TABLE,
            text=table_text,
            metadata=table_metadata,
            element_id=self.element_id,
            parent_id=self.parent_id
        )
    
    def _generate_table_text(self) -> str:
        """Generate text representation of the table"""
        if not self.rows:
            return ""
        
        lines = []
        
        # Add caption if present
        if self.caption:
            lines.append(f"Table: {self.caption}")
            lines.append("")
        
        # Process each row
        for row in self.rows:
            row_text = " | ".join(cell.content for cell in row.cells)
            lines.append(row_text)
            
            # Add separator after header row
            if row.is_header and len(self.rows) > 1:
                separator = " | ".join("---" for _ in row.cells)
                lines.append(separator)
        
        return "\n".join(lines)
    
    def _serialize_table_data(self) -> Dict[str, Any]:
        """Serialize detailed table structure"""
        return {
            'caption': self.caption,
            'headers': self.headers,
            'rows': [
                {
                    'is_header': row.is_header,
                    'cells': [
                        {
                            'content': cell.content,
                            'col_span': cell.col_span,
                            'row_span': cell.row_span,
                            'is_header': cell.is_header,
                            'metadata': cell.metadata
                        }
                        for cell in row.cells
                    ],
                    'metadata': row.metadata
                }
                for row in self.rows
            ]
        }


class ListBuilder:
    """Builder for creating list structures"""
    
    def __init__(self, is_ordered: bool = False):
        self.items: List[str] = []
        self.is_ordered = is_ordered
        self.metadata: Dict[str, Any] = {}
        self.element_id: Optional[str] = None
        self.parent_id: Optional[str] = None
        self.nesting_level: int = 0
    
    def with_id(self, element_id: str) -> 'ListBuilder':
        """Set list element ID"""
        self.element_id = element_id
        return self
    
    def with_parent(self, parent_id: str) -> 'ListBuilder':
        """Set parent element ID"""
        self.parent_id = parent_id
        return self
    
    def with_nesting_level(self, level: int) -> 'ListBuilder':
        """Set list nesting level"""
        self.nesting_level = level
        return self
    
    def add_item(self, text: str) -> 'ListBuilder':
        """Add item to the list"""
        self.items.append(text)
        return self
    
    def add_items(self, items: List[str]) -> 'ListBuilder':
        """Add multiple items to the list"""
        self.items.extend(items)
        return self
    
    def with_page(self, page_number: int) -> 'ListBuilder':
        """Set page number"""
        self.metadata['page_number'] = page_number
        return self
    
    def with_custom_field(self, key: str, value: Any) -> 'ListBuilder':
        """Add custom metadata field"""
        if 'custom_fields' not in self.metadata:
            self.metadata['custom_fields'] = {}
        self.metadata['custom_fields'][key] = value
        return self
    
    def build(self) -> List[Element]:
        """Build list item elements"""
        if not self.items:
            return []
        
        elements = []
        list_metadata = self.metadata.copy()
        list_metadata['custom_fields'] = list_metadata.get('custom_fields', {})
        list_metadata['custom_fields']['list_type'] = 'ordered' if self.is_ordered else 'unordered'
        list_metadata['custom_fields']['nesting_level'] = self.nesting_level
        
        for i, item_text in enumerate(self.items):
            item_metadata = list_metadata.copy()
            item_metadata['custom_fields']['list_index'] = i
            
            # Format text based on list type
            if self.is_ordered:
                formatted_text = f"{i + 1}. {item_text}"
            else:
                formatted_text = f"• {item_text}"
            
            element = ElementFactory.create_element(
                element_type=ElementType.LIST_ITEM,
                text=formatted_text,
                metadata=item_metadata,
                parent_id=self.parent_id
            )
            elements.append(element)
        
        return elements


class DocumentBuilder:
    """Builder for creating structured documents with multiple elements"""
    
    def __init__(self):
        self.elements: List[Element] = []
        self.title: Optional[str] = None
        self.metadata: Dict[str, Any] = {}
    
    def with_title(self, title: str) -> 'DocumentBuilder':
        """Set document title"""
        self.title = title
        return self
    
    def add_element(self, element: Element) -> 'DocumentBuilder':
        """Add an element to the document"""
        self.elements.append(element)
        return self
    
    def add_elements(self, elements: List[Element]) -> 'DocumentBuilder':
        """Add multiple elements to the document"""
        self.elements.extend(elements)
        return self
    
    def add_text(self, text: str, element_type: ElementType = ElementType.NARRATIVE_TEXT) -> 'DocumentBuilder':
        """Add text as an element"""
        element = ElementFactory.create_from_text(text, element_type)
        self.elements.append(element)
        return self
    
    def add_header(self, text: str, level: int = 1) -> 'DocumentBuilder':
        """Add header element"""
        element = ElementBuilder(ElementType.HEADER)\
            .with_text(text)\
            .with_custom_field('header_level', level)\
            .build()
        self.elements.append(element)
        return self
    
    def add_list(self, items: List[str], ordered: bool = False) -> 'DocumentBuilder':
        """Add list elements"""
        list_elements = ListBuilder(ordered)\
            .add_items(items)\
            .build()
        self.elements.extend(list_elements)
        return self
    
    def add_table(self, table_builder: TableBuilder) -> 'DocumentBuilder':
        """Add table element"""
        table_element = table_builder.build()
        self.elements.append(table_element)
        return self
    
    def with_custom_field(self, key: str, value: Any) -> 'DocumentBuilder':
        """Add custom metadata field"""
        if 'custom_fields' not in self.metadata:
            self.metadata['custom_fields'] = {}
        self.metadata['custom_fields'][key] = value
        return self
    
    def build(self) -> List[Element]:
        """Build the complete document structure"""
        result = []
        
        # Add title if specified
        if self.title:
            title_element = ElementBuilder(ElementType.TITLE)\
                .with_text(self.title)\
                .with_custom_field('document_title', True)\
                .build()
            result.append(title_element)
        
        # Add all elements
        result.extend(self.elements)
        
        # Add document metadata to all elements
        if self.metadata:
            for element in result:
                # Clone element with additional metadata
                element_metadata = element.metadata.custom_fields.copy()
                element_metadata.update(self.metadata.get('custom_fields', {}))
                
                updated_element = ElementFactory.clone_element(
                    element,
                    metadata={'custom_fields': element_metadata}
                )
                # Replace in result
                idx = result.index(element)
                result[idx] = updated_element
        
        return result