"""Advanced table structure analysis algorithms."""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from ..types import ParserConfig


@dataclass
class TableCell:
    """Represents a single table cell with structure information."""
    content: str
    row_span: int = 1
    col_span: int = 1
    data_type: str = "text"
    confidence: float = 1.0
    
    def __post_init__(self):
        """Validate cell after initialization."""
        if self.row_span < 1 or self.col_span < 1:
            raise ValueError("Span values must be >= 1")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")


@dataclass 
class TableStructure:
    """Complete table structure with headers and data."""
    headers: List[List[TableCell]]
    rows: List[List[TableCell]]
    metadata: Dict[str, Any]
    column_types: List[str]
    has_headers: bool = True
    
    def __post_init__(self):
        """Validate structure after initialization."""
        if not isinstance(self.headers, list):
            raise ValueError("Headers must be a list")
        if not isinstance(self.rows, list):
            raise ValueError("Rows must be a list")


class TableAnalyzer:
    """Advanced table structure analysis with header detection."""
    
    def __init__(self, config: Optional[ParserConfig] = None):
        self.config = config or ParserConfig()
        self.logger = logging.getLogger(f"torematrix.parsers.table_analyzer")
        
        # Analysis thresholds
        self.header_confidence_threshold = 0.7
        self.structure_confidence_threshold = 0.6
        
    async def analyze_structure(self, raw_data: Dict[str, Any]) -> Optional[TableStructure]:
        """Analyze table structure with header detection."""
        try:
            if not raw_data or 'lines' not in raw_data:
                return None
            
            lines = raw_data['lines']
            if len(lines) < 1:
                return None
            
            # Detect separator pattern and parse cells
            separator_info = self._detect_separator_pattern(lines)
            if not separator_info:
                return None
            
            cells_matrix = self._parse_cells_with_separator(lines, separator_info)
            if not cells_matrix:
                return None
            
            # Detect headers using multiple strategies
            headers = self._detect_headers(cells_matrix)
            
            # Extract data rows (excluding headers)
            data_rows = cells_matrix[len(headers):] if headers else cells_matrix
            
            # Convert to TableCell objects
            header_cells = self._convert_to_table_cells(headers, is_header=True)
            data_cells = self._convert_to_table_cells(data_rows, is_header=False, offset=len(headers))
            
            # Analyze column patterns
            column_patterns = self._analyze_columns(data_cells)
            
            return TableStructure(
                headers=header_cells,
                rows=data_cells,
                metadata={
                    "patterns": column_patterns,
                    "separator_info": separator_info,
                    "analysis_method": "pattern_detection"
                },
                column_types=[],  # Will be filled by DataTyper
                has_headers=len(header_cells) > 0
            )
            
        except Exception as e:
            self.logger.error(f"Table structure analysis failed: {e}")
            return None
    
    def _detect_separator_pattern(self, lines: List[str]) -> Optional[Dict[str, Any]]:
        """Detect the most consistent separator pattern in lines."""
        if not lines:
            return None
        
        # Try different separator patterns
        patterns = [
            {"name": "pipe", "regex": r'\|', "min_count": 1},
            {"name": "tab", "regex": r'\t', "min_count": 1},
            {"name": "multi_space", "regex": r'\s{2,}', "min_count": 1},
            {"name": "comma", "regex": r',(?=\S)', "min_count": 1},
        ]
        
        best_pattern = None
        best_score = 0
        
        for pattern in patterns:
            score = self._score_separator_pattern(lines, pattern)
            if score > best_score and score > 0.5:  # Minimum threshold
                best_score = score
                best_pattern = pattern
        
        if best_pattern:
            best_pattern['score'] = best_score
            return best_pattern
        
        return None
    
    def _score_separator_pattern(self, lines: List[str], pattern: Dict[str, Any]) -> float:
        """Score how well a separator pattern matches the lines."""
        if not lines:
            return 0.0
        
        regex = pattern['regex']
        min_count = pattern['min_count']
        
        # Count separators in each line
        separator_counts = []
        for line in lines[:10]:  # Check first 10 lines
            matches = re.findall(regex, line)
            separator_counts.append(len(matches))
        
        # Filter out lines with too few separators
        valid_counts = [count for count in separator_counts if count >= min_count]
        
        if len(valid_counts) < 2:
            return 0.0
        
        # Calculate consistency score
        if len(set(valid_counts)) == 1:
            # Perfect consistency
            consistency = 1.0
        else:
            # Check variance
            mean_count = sum(valid_counts) / len(valid_counts)
            variance = sum((x - mean_count) ** 2 for x in valid_counts) / len(valid_counts)
            consistency = max(0.0, 1.0 - (variance / max(mean_count, 1)))
        
        # Coverage score (how many lines have the pattern)
        coverage = len(valid_counts) / len(separator_counts)
        
        return (consistency * 0.7) + (coverage * 0.3)
    
    def _parse_cells_with_separator(self, lines: List[str], separator_info: Dict[str, Any]) -> List[List[str]]:
        """Parse lines into cell matrix using detected separator."""
        if not lines or not separator_info:
            return []
        
        regex = separator_info['regex']
        cells_matrix = []
        
        for line in lines:
            if separator_info['name'] == 'pipe':
                # Special handling for pipe-separated (remove leading/trailing pipes)
                cells = [cell.strip() for cell in line.split('|')]
                # Remove empty cells at start/end
                while cells and not cells[0]:
                    cells.pop(0)
                while cells and not cells[-1]:
                    cells.pop()
            elif separator_info['name'] == 'tab':
                cells = [cell.strip() for cell in line.split('\t')]
            elif separator_info['name'] == 'comma':
                import csv
                import io
                reader = csv.reader(io.StringIO(line))
                cells = next(reader, [])
            else:  # multi_space
                cells = [cell.strip() for cell in re.split(regex, line) if cell.strip()]
            
            if cells:  # Only add non-empty rows
                cells_matrix.append(cells)
        
        return cells_matrix
    
    def _detect_headers(self, cells_matrix: List[List[str]]) -> List[List[str]]:
        """Multi-strategy header detection."""
        if not cells_matrix:
            return []
        
        strategies = [
            self._detect_by_formatting,
            self._detect_by_position,
            self._detect_by_content_pattern,
            self._detect_by_data_type_difference
        ]
        
        for strategy in strategies:
            headers = strategy(cells_matrix)
            if headers:
                return headers
        
        return []
    
    def _detect_by_formatting(self, cells_matrix: List[List[str]]) -> List[List[str]]:
        """Detect headers by text formatting patterns."""
        if not cells_matrix:
            return []
        
        first_row = cells_matrix[0]
        
        # Check if first row has header-like formatting
        header_indicators = 0
        total_cells = len(first_row)
        
        for cell in first_row:
            cell_content = cell.strip()
            if not cell_content:
                continue
            
            # Header indicators
            if cell_content.isupper():  # All uppercase
                header_indicators += 1
            elif cell_content.istitle():  # Title case
                header_indicators += 1
            elif not any(char.isdigit() for char in cell_content):  # No numbers
                header_indicators += 0.5
        
        # If enough indicators, consider it a header
        if header_indicators / max(total_cells, 1) > 0.5:
            return [first_row]
        
        return []
    
    def _detect_by_position(self, cells_matrix: List[List[str]]) -> List[List[str]]:
        """Detect headers by position (first row if different from others)."""
        if len(cells_matrix) < 2:
            return []
        
        first_row = cells_matrix[0]
        
        # Check if first row is significantly different from data rows
        data_rows = cells_matrix[1:3]  # Check next 2 rows
        
        # Compare numeric content
        first_row_numeric = sum(1 for cell in first_row if self._is_numeric_content(cell))
        data_numeric_avg = 0
        
        for row in data_rows:
            data_numeric_avg += sum(1 for cell in row if self._is_numeric_content(cell))
        
        if data_rows:
            data_numeric_avg /= len(data_rows)
        
        # If first row has significantly fewer numbers, it's likely a header
        if first_row_numeric < data_numeric_avg * 0.5:
            return [first_row]
        
        return []
    
    def _detect_by_content_pattern(self, cells_matrix: List[List[str]]) -> List[List[str]]:
        """Detect headers by content patterns."""
        if not cells_matrix:
            return []
        
        first_row = cells_matrix[0]
        
        # Common header patterns
        header_words = [
            'name', 'id', 'date', 'time', 'value', 'amount', 'total', 'count',
            'type', 'status', 'category', 'description', 'title', 'code'
        ]
        
        header_matches = 0
        for cell in first_row:
            cell_lower = cell.lower().strip()
            if any(word in cell_lower for word in header_words):
                header_matches += 1
        
        # If multiple cells match header patterns
        if header_matches >= 2 or (len(first_row) <= 3 and header_matches >= 1):
            return [first_row]
        
        return []
    
    def _detect_by_data_type_difference(self, cells_matrix: List[List[str]]) -> List[List[str]]:
        """Detect headers by data type difference from body."""
        if len(cells_matrix) < 3:
            return []
        
        first_row = cells_matrix[0]
        data_rows = cells_matrix[1:]
        
        # Analyze data type patterns in columns
        for col_idx in range(len(first_row)):
            first_cell = first_row[col_idx] if col_idx < len(first_row) else ""
            
            # Get data cells for this column
            data_cells = []
            for row in data_rows:
                if col_idx < len(row):
                    data_cells.append(row[col_idx])
            
            # If first cell is text and data cells are mostly numeric
            if not self._is_numeric_content(first_cell) and data_cells:
                numeric_count = sum(1 for cell in data_cells if self._is_numeric_content(cell))
                if numeric_count / len(data_cells) > 0.6:  # 60% of data is numeric
                    return [first_row]
        
        return []
    
    def _is_numeric_content(self, content: str) -> bool:
        """Check if content is numeric."""
        content = content.strip()
        if not content:
            return False
        
        # Remove common formatting
        clean_content = content.replace(',', '').replace('$', '').replace('%', '')
        
        try:
            float(clean_content)
            return True
        except ValueError:
            return False
    
    def _convert_to_table_cells(self, cells_matrix: List[List[str]], 
                               is_header: bool = False, offset: int = 0) -> List[List[TableCell]]:
        """Convert string matrix to TableCell objects."""
        result = []
        
        for row_idx, row in enumerate(cells_matrix):
            cell_row = []
            for col_idx, content in enumerate(row):
                cell = TableCell(
                    content=content.strip(),
                    row_span=1,
                    col_span=1,
                    data_type="header" if is_header else "text",
                    confidence=0.9 if is_header else 0.8
                )
                cell_row.append(cell)
            result.append(cell_row)
        
        return result
    
    def _analyze_columns(self, data_cells: List[List[TableCell]]) -> Dict[str, Any]:
        """Analyze column patterns in the data."""
        if not data_cells:
            return {}
        
        # Determine column count
        max_cols = max(len(row) for row in data_cells) if data_cells else 0
        
        column_patterns = {}
        
        for col_idx in range(max_cols):
            # Get all cells in this column
            column_cells = []
            for row in data_cells:
                if col_idx < len(row):
                    column_cells.append(row[col_idx].content)
            
            # Analyze this column
            column_patterns[f"column_{col_idx}"] = {
                "content_length_avg": sum(len(cell) for cell in column_cells) / max(len(column_cells), 1),
                "numeric_ratio": sum(1 for cell in column_cells if self._is_numeric_content(cell)) / max(len(column_cells), 1),
                "empty_ratio": sum(1 for cell in column_cells if not cell.strip()) / max(len(column_cells), 1),
                "sample_values": column_cells[:3]  # First 3 values as samples
            }
        
        return column_patterns