"""
Table Element Types for Document Parsing

This module defines table-related element types including tables,
rows, cells, and their associated structures.
"""

import json
from typing import Dict, List, Optional, Any, Tuple, Union

from .base_element import ParsedElement, ElementType, BoundingBox, ElementMetadata


class TableCell:
    """Represents a single cell in a table"""
    
    def __init__(
        self,
        content: str,
        row_index: int,
        col_index: int,
        row_span: int = 1,
        col_span: int = 1,
        is_header: bool = False,
        alignment: str = "left",
        bbox: Optional[BoundingBox] = None
    ):
        """Initialize table cell"""
        self.content = content
        self.row_index = row_index
        self.col_index = col_index
        self.row_span = row_span
        self.col_span = col_span
        self.is_header = is_header
        self.alignment = alignment
        self.bbox = bbox
    
    def get_text(self) -> str:
        """Get cell text content"""
        return str(self.content)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'content': self.content,
            'row_index': self.row_index,
            'col_index': self.col_index,
            'row_span': self.row_span,
            'col_span': self.col_span,
            'is_header': self.is_header,
            'alignment': self.alignment,
            'bbox': self.bbox.to_dict() if self.bbox else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TableCell':
        """Create from dictionary"""
        bbox = None
        if data.get('bbox'):
            bbox = BoundingBox(**data['bbox'])
        
        return cls(
            content=data['content'],
            row_index=data['row_index'],
            col_index=data['col_index'],
            row_span=data.get('row_span', 1),
            col_span=data.get('col_span', 1),
            is_header=data.get('is_header', False),
            alignment=data.get('alignment', 'left'),
            bbox=bbox
        )


class TableRow:
    """Represents a row in a table"""
    
    def __init__(self, cells: List[TableCell], row_index: int):
        """Initialize table row"""
        self.cells = cells
        self.row_index = row_index
    
    def get_cell(self, col_index: int) -> Optional[TableCell]:
        """Get cell at column index"""
        for cell in self.cells:
            if cell.col_index == col_index:
                return cell
        return None
    
    def get_text(self) -> str:
        """Get row text as tab-separated values"""
        return '\t'.join(cell.get_text() for cell in self.cells)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'row_index': self.row_index,
            'cells': [cell.to_dict() for cell in self.cells]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TableRow':
        """Create from dictionary"""
        cells = [TableCell.from_dict(cell_data) for cell_data in data['cells']]
        return cls(cells=cells, row_index=data['row_index'])


class TableElement(ParsedElement):
    """Table element containing rows and cells"""
    
    def __init__(
        self,
        rows: List[TableRow],
        bbox: Optional[BoundingBox] = None,
        metadata: Optional[ElementMetadata] = None,
        parent_id: Optional[str] = None,
        children_ids: Optional[List[str]] = None,
        caption: Optional[str] = None
    ):
        """Initialize table element"""
        super().__init__(ElementType.TABLE, rows, bbox, metadata, parent_id, children_ids)
        self.caption = caption
        self._column_count = self._calculate_column_count()
        self._row_count = len(rows)
        
        if caption:
            self.metadata.add_attribute('caption', caption)
        self.metadata.add_attribute('dimensions', {
            'rows': self._row_count,
            'columns': self._column_count
        })
    
    def _calculate_column_count(self) -> int:
        """Calculate maximum column count across all rows"""
        if not self.content:
            return 0
        
        max_col = 0
        for row in self.content:
            for cell in row.cells:
                max_col = max(max_col, cell.col_index + cell.col_span)
        return max_col
    
    def get_text(self) -> str:
        """Get text representation of table"""
        lines = []
        
        if self.caption:
            lines.append(f"Table: {self.caption}")
            lines.append("")
        
        for row in self.content:
            lines.append(row.get_text())
        
        return '\n'.join(lines)
    
    def get_row(self, row_index: int) -> Optional[TableRow]:
        """Get row at index"""
        for row in self.content:
            if row.row_index == row_index:
                return row
        return None
    
    def get_cell(self, row_index: int, col_index: int) -> Optional[TableCell]:
        """Get cell at row and column index"""
        row = self.get_row(row_index)
        if row:
            return row.get_cell(col_index)
        return None
    
    def get_headers(self) -> List[TableCell]:
        """Get all header cells"""
        headers = []
        for row in self.content:
            for cell in row.cells:
                if cell.is_header:
                    headers.append(cell)
        return headers
    
    def to_html(self) -> str:
        """Convert table to HTML representation"""
        html_parts = ['<table>']
        
        if self.caption:
            html_parts.append(f'<caption>{self.caption}</caption>')
        
        # Check if first row contains headers
        has_header = any(cell.is_header for cell in self.content[0].cells) if self.content else False
        
        if has_header and self.content:
            html_parts.append('<thead>')
            html_parts.append('<tr>')
            for cell in self.content[0].cells:
                tag = 'th' if cell.is_header else 'td'
                span_attrs = []
                if cell.row_span > 1:
                    span_attrs.append(f'rowspan="{cell.row_span}"')
                if cell.col_span > 1:
                    span_attrs.append(f'colspan="{cell.col_span}"')
                span_str = ' ' + ' '.join(span_attrs) if span_attrs else ''
                html_parts.append(f'<{tag}{span_str}>{cell.content}</{tag}>')
            html_parts.append('</tr>')
            html_parts.append('</thead>')
            
            # Body starts from second row
            body_rows = self.content[1:]
        else:
            body_rows = self.content
        
        if body_rows:
            html_parts.append('<tbody>')
            for row in body_rows:
                html_parts.append('<tr>')
                for cell in row.cells:
                    tag = 'th' if cell.is_header else 'td'
                    span_attrs = []
                    if cell.row_span > 1:
                        span_attrs.append(f'rowspan="{cell.row_span}"')
                    if cell.col_span > 1:
                        span_attrs.append(f'colspan="{cell.col_span}"')
                    span_str = ' ' + ' '.join(span_attrs) if span_attrs else ''
                    html_parts.append(f'<{tag}{span_str}>{cell.content}</{tag}>')
                html_parts.append('</tr>')
            html_parts.append('</tbody>')
        
        html_parts.append('</table>')
        
        return '\n'.join(html_parts)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'type': self.element_type.value,
            'rows': [row.to_dict() for row in self.content],
            'caption': self.caption,
            'dimensions': {
                'rows': self._row_count,
                'columns': self._column_count
            },
            'bbox': self.bbox.to_dict() if self.bbox else None,
            'metadata': self.metadata.to_dict(),
            'parent_id': self.parent_id,
            'children_ids': self.children_ids
        }
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate table element"""
        if not self.content:
            return False, "Table has no rows"
        
        if not isinstance(self.content, list):
            return False, f"Content must be list of rows, got {type(self.content)}"
        
        # Validate each row
        for i, row in enumerate(self.content):
            if not isinstance(row, TableRow):
                return False, f"Row {i} is not a TableRow instance"
            
            if row.row_index != i:
                return False, f"Row {i} has incorrect index: {row.row_index}"
        
        # Check for consistent column structure
        col_counts = set()
        for row in self.content:
            col_count = max(cell.col_index + cell.col_span for cell in row.cells) if row.cells else 0
            col_counts.add(col_count)
        
        if len(col_counts) > 1:
            # Allow some variation for tables with merged cells
            min_cols = min(col_counts)
            max_cols = max(col_counts)
            if max_cols - min_cols > 2:
                return True, "Table has inconsistent column structure (warning)"
        
        return True, None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TableElement':
        """Create from dictionary"""
        rows = [TableRow.from_dict(row_data) for row_data in data['rows']]
        
        bbox = None
        if data.get('bbox'):
            bbox = BoundingBox(**data['bbox'])
        
        metadata = ElementMetadata()
        if data.get('metadata'):
            metadata = ElementMetadata(**data['metadata'])
        
        return cls(
            rows=rows,
            bbox=bbox,
            metadata=metadata,
            parent_id=data.get('parent_id'),
            children_ids=data.get('children_ids', []),
            caption=data.get('caption')
        )