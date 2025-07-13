"""Handle merged cells and spans in table structures."""

import logging
from typing import Dict, Any, List, Optional, Tuple
from .table_analyzer import TableStructure, TableCell


class CellMerger:
    """Handler for cell merging and span processing."""
    
    def __init__(self):
        self.logger = logging.getLogger("torematrix.parsers.cell_merger")
    
    def process_spans(self, structure: TableStructure) -> TableStructure:
        """Process cell spans and merging in table structure."""
        try:
            # For now, we'll implement basic span detection
            # In a real implementation, this would analyze the table for merged cells
            
            # Detect potential spans by looking for empty cells following content
            self._detect_column_spans(structure)
            self._detect_row_spans(structure)
            
            return structure
            
        except Exception as e:
            self.logger.error(f"Cell span processing failed: {e}")
            return structure
    
    def _detect_column_spans(self, structure: TableStructure) -> None:
        """Detect horizontal spans (colspan)."""
        # Look for patterns where cells are empty following non-empty cells
        for row_cells in structure.rows:
            for i, cell in enumerate(row_cells):
                if cell.content.strip() and i + 1 < len(row_cells):
                    # Check if next cells are empty
                    span_length = 1
                    for j in range(i + 1, len(row_cells)):
                        if not row_cells[j].content.strip():
                            span_length += 1
                        else:
                            break
                    
                    if span_length > 1:
                        cell.col_span = span_length
                        # Mark spanned cells
                        for k in range(i + 1, i + span_length):
                            if k < len(row_cells):
                                row_cells[k].content = ""  # Clear spanned cells
    
    def _detect_row_spans(self, structure: TableStructure) -> None:
        """Detect vertical spans (rowspan)."""
        if len(structure.rows) < 2:
            return
        
        # Check each column for potential row spans
        max_cols = max(len(row) for row in structure.rows) if structure.rows else 0
        
        for col_idx in range(max_cols):
            for row_idx in range(len(structure.rows)):
                if col_idx >= len(structure.rows[row_idx]):
                    continue
                
                cell = structure.rows[row_idx][col_idx]
                if cell.content.strip():
                    # Check if subsequent rows have empty cells in this column
                    span_length = 1
                    for next_row_idx in range(row_idx + 1, len(structure.rows)):
                        if (col_idx < len(structure.rows[next_row_idx]) and 
                            not structure.rows[next_row_idx][col_idx].content.strip()):
                            span_length += 1
                        else:
                            break
                    
                    if span_length > 1:
                        cell.row_span = span_length
                        # Mark spanned cells
                        for k in range(row_idx + 1, row_idx + span_length):
                            if (k < len(structure.rows) and 
                                col_idx < len(structure.rows[k])):
                                structure.rows[k][col_idx].content = ""