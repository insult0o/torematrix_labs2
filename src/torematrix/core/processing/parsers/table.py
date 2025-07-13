"""Table structure parser with data type inference."""

import re
import json
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass

from torematrix_parser.src.torematrix.core.models.element import Element as UnifiedElement
from .base import BaseParser, ParserResult, ParserMetadata
from .types import ElementType, ParserCapabilities, ProcessingHints
from .exceptions import StructureExtractionError


@dataclass
class TableCell:
    """Represents a table cell."""
    content: str
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    data_type: str = "text"
    confidence: float = 1.0


@dataclass
class TableStructure:
    """Represents table structure."""
    rows: int
    cols: int
    cells: List[TableCell]
    headers: List[str]
    column_types: List[str]
    has_header: bool = False
    has_footer: bool = False
    merged_cells: List[Tuple[int, int, int, int]] = None  # (row1, col1, row2, col2)


class TableParser(BaseParser):
    """Parser for table elements with structure preservation."""
    
    @property
    def capabilities(self) -> ParserCapabilities:
        return ParserCapabilities(
            supported_types=[ElementType.TABLE],
            supports_batch=True,
            supports_async=True,
            supports_validation=True,
            supports_metadata_extraction=True,
            supports_structured_output=True,
            supports_export_formats=["csv", "json", "html", "xlsx", "markdown"]
        )
    
    def can_parse(self, element: UnifiedElement) -> bool:
        """Check if element is a table."""
        return (
            hasattr(element, 'type') and element.type == "Table" or
            hasattr(element, 'category') and element.category == "table" or
            self._has_table_indicators(element)
        )
    
    async def parse(self, element: UnifiedElement, hints: Optional[ProcessingHints] = None) -> ParserResult:
        """Parse table with structure preservation."""
        try:
            # Extract table structure
            structure = await self._extract_table_structure(element)
            
            # Infer data types for columns
            await self._infer_column_types(structure)
            
            # Detect headers and footers
            self._detect_headers_footers(structure)
            
            # Calculate confidence
            confidence = self._calculate_table_confidence(structure, element)
            
            # Generate export formats
            export_formats = self._generate_export_formats(structure)
            
            return ParserResult(
                success=True,
                data={
                    "structure": structure,
                    "rows": structure.rows,
                    "columns": structure.cols,
                    "headers": structure.headers,
                    "column_types": structure.column_types,
                    "cells": [self._cell_to_dict(cell) for cell in structure.cells],
                    "has_merged_cells": bool(structure.merged_cells),
                    "table_data": self._structure_to_data(structure)
                },
                metadata=ParserMetadata(
                    confidence=confidence,
                    element_metadata={
                        "cell_count": len(structure.cells),
                        "data_density": self._calculate_data_density(structure),
                        "structure_complexity": self._calculate_complexity(structure)
                    }
                ),
                extracted_content=self._structure_to_text(structure),
                structured_data=self._structure_to_data(structure),
                export_formats=export_formats
            )
            
        except Exception as e:
            return self._create_failure_result(
                f"Table parsing failed: {str(e)}",
                validation_errors=[f"Structure extraction error: {str(e)}"]
            )
    
    def validate(self, result: ParserResult) -> List[str]:
        """Validate table parsing result."""
        errors = []
        
        if not result.success:
            return ["Table parsing failed"]
        
        structure = result.data.get("structure")
        if not structure:
            errors.append("No table structure extracted")
            return errors
        
        # Validate basic structure
        if structure.rows <= 0 or structure.cols <= 0:
            errors.append("Invalid table dimensions")
        
        # Validate cell consistency
        expected_cells = structure.rows * structure.cols
        if len(structure.cells) != expected_cells:
            errors.append(f"Cell count mismatch: expected {expected_cells}, got {len(structure.cells)}")
        
        # Validate column types
        if len(structure.column_types) != structure.cols:
            errors.append("Column type count doesn't match column count")
        
        return errors
    
    async def _extract_table_structure(self, element: UnifiedElement) -> TableStructure:
        """Extract table structure from element."""
        if hasattr(element, 'metadata') and element.metadata:
            # Use structured metadata if available
            return await self._extract_from_metadata(element.metadata)
        else:
            # Parse from text content
            return await self._extract_from_text(element.text)
    
    async def _extract_from_metadata(self, metadata: Dict[str, Any]) -> TableStructure:
        """Extract table structure from element metadata."""
        if 'table_data' in metadata:
            table_data = metadata['table_data']
            return self._parse_table_data(table_data)
        
        if 'text_as_html' in metadata:
            return await self._parse_html_table(metadata['text_as_html'])
        
        raise StructureExtractionError("table", "No usable table metadata found")
    
    async def _extract_from_text(self, text: str) -> TableStructure:
        """Extract table structure from plain text."""
        # Try different table text patterns
        patterns = [
            self._parse_pipe_separated,
            self._parse_tab_separated,
            self._parse_comma_separated,
            self._parse_aligned_columns
        ]
        
        for pattern_parser in patterns:
            try:
                structure = await pattern_parser(text)
                if structure and structure.rows > 0 and structure.cols > 0:
                    return structure
            except Exception:
                continue
        
        raise StructureExtractionError("table", "Could not extract table structure from text")
    
    async def _parse_pipe_separated(self, text: str) -> TableStructure:
        """Parse pipe-separated table format."""
        lines = text.strip().split('\n')
        if not lines:
            raise StructureExtractionError("table", "Empty text")
        
        # Filter out separator lines (lines with only |, -, +, space)
        data_lines = [line for line in lines if not re.match(r'^[\|\-\+\s]*$', line.strip())]
        
        if not data_lines:
            raise StructureExtractionError("table", "No data lines found")
        
        rows = len(data_lines)
        cells = []
        
        # Parse each line
        for row_idx, line in enumerate(data_lines):
            # Split by pipe and clean
            row_cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            
            for col_idx, content in enumerate(row_cells):
                cells.append(TableCell(
                    content=content,
                    row=row_idx,
                    col=col_idx
                ))
        
        # Determine column count from maximum columns in any row
        cols = max(cell.col for cell in cells) + 1 if cells else 0
        
        return TableStructure(
            rows=rows,
            cols=cols,
            cells=cells,
            headers=[],
            column_types=[]
        )
    
    async def _parse_tab_separated(self, text: str) -> TableStructure:
        """Parse tab-separated table format."""
        lines = text.strip().split('\n')
        if not lines:
            raise StructureExtractionError("table", "Empty text")
        
        rows = len(lines)
        cells = []
        
        for row_idx, line in enumerate(lines):
            row_cells = line.split('\t')
            for col_idx, content in enumerate(row_cells):
                cells.append(TableCell(
                    content=content.strip(),
                    row=row_idx,
                    col=col_idx
                ))
        
        cols = max(cell.col for cell in cells) + 1 if cells else 0
        
        return TableStructure(
            rows=rows,
            cols=cols,
            cells=cells,
            headers=[],
            column_types=[]
        )
    
    async def _parse_comma_separated(self, text: str) -> TableStructure:
        """Parse comma-separated table format."""
        import csv
        from io import StringIO
        
        try:
            reader = csv.reader(StringIO(text))
            rows_data = list(reader)
            
            if not rows_data:
                raise StructureExtractionError("table", "No rows found")
            
            rows = len(rows_data)
            cols = max(len(row) for row in rows_data) if rows_data else 0
            cells = []
            
            for row_idx, row in enumerate(rows_data):
                for col_idx, content in enumerate(row):
                    cells.append(TableCell(
                        content=content.strip(),
                        row=row_idx,
                        col=col_idx
                    ))
            
            return TableStructure(
                rows=rows,
                cols=cols,
                cells=cells,
                headers=[],
                column_types=[]
            )
            
        except Exception as e:
            raise StructureExtractionError("table", f"CSV parsing failed: {e}")
    
    async def _parse_aligned_columns(self, text: str) -> TableStructure:
        """Parse aligned column table format."""
        lines = text.strip().split('\n')
        if not lines:
            raise StructureExtractionError("table", "Empty text")
        
        # Analyze column positions based on whitespace
        column_positions = self._detect_column_positions(lines)
        
        if len(column_positions) < 2:
            raise StructureExtractionError("table", "Could not detect columns")
        
        rows = len(lines)
        cols = len(column_positions) - 1
        cells = []
        
        for row_idx, line in enumerate(lines):
            for col_idx in range(cols):
                start_pos = column_positions[col_idx]
                end_pos = column_positions[col_idx + 1]
                content = line[start_pos:end_pos].strip()
                
                cells.append(TableCell(
                    content=content,
                    row=row_idx,
                    col=col_idx
                ))
        
        return TableStructure(
            rows=rows,
            cols=cols,
            cells=cells,
            headers=[],
            column_types=[]
        )
    
    def _detect_column_positions(self, lines: List[str]) -> List[int]:
        """Detect column positions in aligned text."""
        if not lines:
            return [0]
        
        # Find positions where all lines have whitespace
        max_length = max(len(line) for line in lines)
        column_breaks = []
        
        for pos in range(max_length):
            is_break = True
            for line in lines:
                if pos < len(line) and not line[pos].isspace():
                    is_break = False
                    break
            if is_break:
                column_breaks.append(pos)
        
        # Convert breaks to column start positions
        positions = [0]
        in_break = False
        
        for pos in range(max_length):
            if pos in column_breaks:
                if not in_break:
                    in_break = True
            else:
                if in_break:
                    positions.append(pos)
                    in_break = False
        
        positions.append(max_length)
        return positions
    
    async def _infer_column_types(self, structure: TableStructure) -> None:
        """Infer data types for table columns."""
        structure.column_types = []
        
        for col in range(structure.cols):
            column_cells = [cell for cell in structure.cells if cell.col == col]
            column_type = self._infer_column_type(column_cells)
            structure.column_types.append(column_type)
    
    def _infer_column_type(self, cells: List[TableCell]) -> str:
        """Infer data type for a column."""
        if not cells:
            return "text"
        
        # Count type matches
        type_counts = {
            "integer": 0,
            "float": 0,
            "date": 0,
            "boolean": 0,
            "currency": 0,
            "percentage": 0,
            "text": 0
        }
        
        for cell in cells:
            content = cell.content.strip()
            if not content:
                continue
            
            # Check each type
            if self._is_integer(content):
                type_counts["integer"] += 1
            elif self._is_float(content):
                type_counts["float"] += 1
            elif self._is_date(content):
                type_counts["date"] += 1
            elif self._is_boolean(content):
                type_counts["boolean"] += 1
            elif self._is_currency(content):
                type_counts["currency"] += 1
            elif self._is_percentage(content):
                type_counts["percentage"] += 1
            else:
                type_counts["text"] += 1
        
        # Return most common type (excluding text)
        non_text_types = {k: v for k, v in type_counts.items() if k != "text" and v > 0}
        if non_text_types:
            return max(non_text_types, key=non_text_types.get)
        return "text"
    
    def _is_integer(self, value: str) -> bool:
        """Check if value is an integer."""
        try:
            int(value.replace(',', ''))
            return True
        except ValueError:
            return False
    
    def _is_float(self, value: str) -> bool:
        """Check if value is a float."""
        try:
            float(value.replace(',', ''))
            return '.' in value
        except ValueError:
            return False
    
    def _is_date(self, value: str) -> bool:
        """Check if value is a date."""
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2}-\d{1,2}-\d{4}',
            r'\d{4}-\d{1,2}-\d{1,2}',
            r'\w+ \d{1,2}, \d{4}'
        ]
        return any(re.match(pattern, value) for pattern in date_patterns)
    
    def _is_boolean(self, value: str) -> bool:
        """Check if value is a boolean."""
        return value.lower() in ['true', 'false', 'yes', 'no', '1', '0', 'y', 'n']
    
    def _is_currency(self, value: str) -> bool:
        """Check if value is currency."""
        return bool(re.match(r'[\$€£¥][\d,]+\.?\d*', value))
    
    def _is_percentage(self, value: str) -> bool:
        """Check if value is percentage."""
        return value.endswith('%') and self._is_float(value[:-1])
    
    def _detect_headers_footers(self, structure: TableStructure) -> None:
        """Detect header and footer rows."""
        if structure.rows < 2:
            return
        
        # Check if first row looks like headers
        first_row_cells = [cell for cell in structure.cells if cell.row == 0]
        if self._is_header_row(first_row_cells):
            structure.has_header = True
            structure.headers = [cell.content for cell in sorted(first_row_cells, key=lambda c: c.col)]
        
        # Check if last row looks like footer (totals, summaries)
        last_row_cells = [cell for cell in structure.cells if cell.row == structure.rows - 1]
        if self._is_footer_row(last_row_cells):
            structure.has_footer = True
    
    def _is_header_row(self, cells: List[TableCell]) -> bool:
        """Check if row looks like a header."""
        if not cells:
            return False
        
        # Headers typically have:
        # - No numbers (or fewer numbers)
        # - Different formatting (all caps, etc.)
        # - Descriptive text
        numeric_count = sum(1 for cell in cells if self._is_numeric(cell.content))
        total_cells = len(cells)
        
        return numeric_count / total_cells < 0.3  # Less than 30% numeric
    
    def _is_footer_row(self, cells: List[TableCell]) -> bool:
        """Check if row looks like a footer."""
        if not cells:
            return False
        
        # Footers often contain totals, summaries
        footer_indicators = ['total', 'sum', 'average', 'mean', 'summary', 'subtotal']
        
        for cell in cells:
            if any(indicator in cell.content.lower() for indicator in footer_indicators):
                return True
        
        return False
    
    def _is_numeric(self, value: str) -> bool:
        """Check if value is numeric."""
        return self._is_integer(value) or self._is_float(value)
    
    def _has_table_indicators(self, element: UnifiedElement) -> bool:
        """Check if element has table-like indicators."""
        if not hasattr(element, 'text') or not element.text:
            return False
        
        text = element.text
        
        # Look for table patterns
        table_patterns = [
            r'\|.*\|',  # Pipe-separated
            r'\t.*\t',  # Tab-separated
            r'^\s*\w+\s+\w+\s+\w+',  # Multiple columns
        ]
        
        return any(re.search(pattern, text, re.MULTILINE) for pattern in table_patterns)
    
    def _calculate_table_confidence(self, structure: TableStructure, element: UnifiedElement) -> float:
        """Calculate confidence in table parsing."""
        confidence_factors = []
        
        # Structure quality (40%)
        if structure.rows > 1 and structure.cols > 1:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.3)
        
        # Data type consistency (30%)
        type_consistency = self._calculate_type_consistency(structure)
        confidence_factors.append(type_consistency)
        
        # Content quality (30%)
        content_quality = self._calculate_content_quality(structure)
        confidence_factors.append(content_quality)
        
        return sum(confidence_factors) / len(confidence_factors)
    
    def _calculate_type_consistency(self, structure: TableStructure) -> float:
        """Calculate type consistency across columns."""
        if not structure.column_types:
            return 0.5
        
        consistent_columns = sum(1 for col_type in structure.column_types if col_type != "text")
        return consistent_columns / len(structure.column_types)
    
    def _calculate_content_quality(self, structure: TableStructure) -> float:
        """Calculate content quality score."""
        if not structure.cells:
            return 0.0
        
        non_empty_cells = sum(1 for cell in structure.cells if cell.content.strip())
        return non_empty_cells / len(structure.cells)
    
    def _calculate_data_density(self, structure: TableStructure) -> float:
        """Calculate data density (non-empty cells ratio)."""
        if not structure.cells:
            return 0.0
        
        non_empty_cells = sum(1 for cell in structure.cells if cell.content.strip())
        return non_empty_cells / len(structure.cells)
    
    def _calculate_complexity(self, structure: TableStructure) -> str:
        """Calculate table complexity level."""
        total_cells = structure.rows * structure.cols
        
        if total_cells > 100:
            return "high"
        elif total_cells > 20:
            return "medium"
        else:
            return "low"
    
    def _cell_to_dict(self, cell: TableCell) -> Dict[str, Any]:
        """Convert cell to dictionary."""
        return {
            "content": cell.content,
            "row": cell.row,
            "col": cell.col,
            "rowspan": cell.rowspan,
            "colspan": cell.colspan,
            "data_type": cell.data_type,
            "confidence": cell.confidence
        }
    
    def _structure_to_data(self, structure: TableStructure) -> List[List[str]]:
        """Convert structure to 2D array."""
        data = [['' for _ in range(structure.cols)] for _ in range(structure.rows)]
        
        for cell in structure.cells:
            if cell.row < structure.rows and cell.col < structure.cols:
                data[cell.row][cell.col] = cell.content
        
        return data
    
    def _structure_to_text(self, structure: TableStructure) -> str:
        """Convert structure to formatted text."""
        data = self._structure_to_data(structure)
        return '\n'.join('\t'.join(row) for row in data)
    
    def _generate_export_formats(self, structure: TableStructure) -> Dict[str, Any]:
        """Generate various export formats."""
        data = self._structure_to_data(structure)
        
        return {
            "csv": self._to_csv(data),
            "json": self._to_json(structure),
            "html": self._to_html(structure),
            "markdown": self._to_markdown(data)
        }
    
    def _to_csv(self, data: List[List[str]]) -> str:
        """Convert to CSV format."""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        for row in data:
            writer.writerow(row)
        return output.getvalue()
    
    def _to_json(self, structure: TableStructure) -> str:
        """Convert to JSON format."""
        data = {
            "headers": structure.headers,
            "rows": structure.rows,
            "columns": structure.cols,
            "column_types": structure.column_types,
            "data": self._structure_to_data(structure)
        }
        return json.dumps(data, indent=2)
    
    def _to_html(self, structure: TableStructure) -> str:
        """Convert to HTML table format."""
        data = self._structure_to_data(structure)
        
        html = ["<table>"]
        
        if structure.has_header and structure.headers:
            html.append("  <thead>")
            html.append("    <tr>")
            for header in structure.headers:
                html.append(f"      <th>{header}</th>")
            html.append("    </tr>")
            html.append("  </thead>")
        
        html.append("  <tbody>")
        start_row = 1 if structure.has_header else 0
        for row in data[start_row:]:
            html.append("    <tr>")
            for cell in row:
                html.append(f"      <td>{cell}</td>")
            html.append("    </tr>")
        html.append("  </tbody>")
        html.append("</table>")
        
        return '\n'.join(html)
    
    def _to_markdown(self, data: List[List[str]]) -> str:
        """Convert to Markdown table format."""
        if not data:
            return ""
        
        lines = []
        
        # Headers
        if data:
            headers = data[0]
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            
            # Data rows
            for row in data[1:]:
                lines.append("| " + " | ".join(row) + " |")
        
        return '\n'.join(lines)
    
    def _parse_table_data(self, table_data: Any) -> TableStructure:
        """Parse table data from various formats."""
        if isinstance(table_data, list):
            return self._parse_list_table(table_data)
        elif isinstance(table_data, dict):
            return self._parse_dict_table(table_data)
        else:
            raise StructureExtractionError("table", f"Unsupported table data format: {type(table_data)}")
    
    def _parse_list_table(self, table_data: List[List[str]]) -> TableStructure:
        """Parse table from list of lists."""
        if not table_data:
            raise StructureExtractionError("table", "Empty table data")
        
        rows = len(table_data)
        cols = max(len(row) for row in table_data) if table_data else 0
        cells = []
        
        for row_idx, row in enumerate(table_data):
            for col_idx, content in enumerate(row):
                cells.append(TableCell(
                    content=str(content),
                    row=row_idx,
                    col=col_idx
                ))
        
        return TableStructure(
            rows=rows,
            cols=cols,
            cells=cells,
            headers=[],
            column_types=[]
        )
    
    def _parse_dict_table(self, table_data: Dict[str, Any]) -> TableStructure:
        """Parse table from dictionary format."""
        if 'data' in table_data and isinstance(table_data['data'], list):
            return self._parse_list_table(table_data['data'])
        else:
            raise StructureExtractionError("table", "Invalid dictionary table format")
    
    async def _parse_html_table(self, html: str) -> TableStructure:
        """Parse HTML table structure."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            table = soup.find('table')
            
            if not table:
                raise StructureExtractionError("table", "No table element found in HTML")
            
            rows = []
            for tr in table.find_all('tr'):
                row = []
                for cell in tr.find_all(['td', 'th']):
                    row.append(cell.get_text(strip=True))
                rows.append(row)
            
            return self._parse_list_table(rows)
            
        except ImportError:
            raise StructureExtractionError("table", "BeautifulSoup not available for HTML parsing")
        except Exception as e:
            raise StructureExtractionError("table", f"HTML parsing failed: {e}")