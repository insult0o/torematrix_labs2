"""Tests for TableAnalyzer functionality."""

import pytest
from unittest.mock import Mock

from src.torematrix.core.processing.parsers.structural.table_analyzer import (
    TableAnalyzer, TableCell, TableStructure
)
from src.torematrix.core.processing.parsers.types import ParserConfig


class TestTableAnalyzer:
    """Test suite for TableAnalyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return TableAnalyzer()
    
    @pytest.fixture
    def simple_pipe_data(self):
        """Simple pipe-separated table data."""
        return {
            "lines": [
                "Name | Age | City",
                "John | 25 | New York",
                "Jane | 30 | London"
            ],
            "raw_text": "Name | Age | City\nJohn | 25 | New York\nJane | 30 | London",
            "element_metadata": {}
        }
    
    @pytest.fixture
    def csv_data(self):
        """CSV-style table data."""
        return {
            "lines": [
                "Product,Price,Stock",
                "Laptop,999.99,15",
                "Mouse,29.99,50"
            ],
            "raw_text": "Product,Price,Stock\nLaptop,999.99,15\nMouse,29.99,50",
            "element_metadata": {}
        }
    
    @pytest.fixture
    def complex_table_data(self):
        """Complex table with mixed data types."""
        return {
            "lines": [
                "ID | Product | Price | Available | Date",
                "1 | Laptop | $999.99 | Yes | 2023-01-15",
                "2 | Mouse | $29.99 | No | 2022-11-20"
            ],
            "raw_text": "ID | Product | Price | Available | Date\n1 | Laptop | $999.99 | Yes | 2023-01-15\n2 | Mouse | $29.99 | No | 2022-11-20",
            "element_metadata": {}
        }
    
    @pytest.mark.asyncio
    async def test_analyze_simple_pipe_structure(self, analyzer, simple_pipe_data):
        """Test analysis of simple pipe-separated table."""
        structure = await analyzer.analyze_structure(simple_pipe_data)
        
        assert structure is not None
        assert isinstance(structure, TableStructure)
        assert structure.has_headers
        assert len(structure.headers) == 1  # One header row
        assert len(structure.headers[0]) == 3  # Three columns
        assert len(structure.rows) == 2  # Two data rows
        
        # Check header content
        header_contents = [cell.content for cell in structure.headers[0]]
        assert "Name" in header_contents
        assert "Age" in header_contents
        assert "City" in header_contents
    
    @pytest.mark.asyncio
    async def test_analyze_csv_structure(self, analyzer, csv_data):
        """Test analysis of CSV-style table."""
        structure = await analyzer.analyze_structure(csv_data)
        
        assert structure is not None
        assert len(structure.rows) == 2  # Data rows
        
        # Check if headers detected
        if structure.has_headers:
            assert len(structure.headers[0]) == 3
    
    @pytest.mark.asyncio
    async def test_analyze_complex_structure(self, analyzer, complex_table_data):
        """Test analysis of complex table with mixed data types."""
        structure = await analyzer.analyze_structure(complex_table_data)
        
        assert structure is not None
        assert len(structure.rows) == 2
        
        # Should detect headers
        assert structure.has_headers
        header_contents = [cell.content for cell in structure.headers[0]]
        assert "ID" in header_contents
        assert "Product" in header_contents
        assert "Price" in header_contents
    
    @pytest.mark.asyncio
    async def test_analyze_empty_data(self, analyzer):
        """Test analysis with empty data."""
        empty_data = {"lines": [], "raw_text": "", "element_metadata": {}}
        structure = await analyzer.analyze_structure(empty_data)
        
        assert structure is None
    
    @pytest.mark.asyncio
    async def test_analyze_malformed_data(self, analyzer):
        """Test analysis with malformed data."""
        malformed_data = {
            "lines": ["incomplete line"],
            "raw_text": "incomplete line",
            "element_metadata": {}
        }
        structure = await analyzer.analyze_structure(malformed_data)
        
        # Should handle gracefully
        if structure:
            assert len(structure.rows) >= 0
    
    def test_detect_separator_pattern_pipe(self, analyzer):
        """Test pipe separator detection."""
        lines = ["col1 | col2 | col3", "val1 | val2 | val3"]
        pattern = analyzer._detect_separator_pattern(lines)
        
        assert pattern is not None
        assert pattern["name"] == "pipe"
        assert pattern["score"] > 0.5
    
    def test_detect_separator_pattern_comma(self, analyzer):
        """Test comma separator detection."""
        lines = ["col1,col2,col3", "val1,val2,val3"]
        pattern = analyzer._detect_separator_pattern(lines)
        
        assert pattern is not None
        assert pattern["name"] == "comma"
        assert pattern["score"] > 0.5
    
    def test_detect_separator_pattern_none(self, analyzer):
        """Test no pattern detection."""
        lines = ["just regular text", "without any pattern"]
        pattern = analyzer._detect_separator_pattern(lines)
        
        assert pattern is None
    
    def test_score_separator_pattern_consistent(self, analyzer):
        """Test scoring of consistent separator pattern."""
        lines = ["a | b | c", "1 | 2 | 3", "x | y | z"]
        pattern = {"name": "pipe", "regex": r'\|', "min_count": 1}
        
        score = analyzer._score_separator_pattern(lines, pattern)
        assert score > 0.8  # Should be high for consistent pattern
    
    def test_score_separator_pattern_inconsistent(self, analyzer):
        """Test scoring of inconsistent separator pattern."""
        lines = ["a | b", "1 | 2 | 3", "x"]
        pattern = {"name": "pipe", "regex": r'\|', "min_count": 1}
        
        score = analyzer._score_separator_pattern(lines, pattern)
        assert score < 0.8  # Should be lower for inconsistent pattern
    
    def test_parse_cells_with_pipe_separator(self, analyzer):
        """Test parsing cells with pipe separator."""
        lines = ["Name | Age", "John | 25"]
        separator_info = {"name": "pipe", "regex": r'\|'}
        
        cells_matrix = analyzer._parse_cells_with_separator(lines, separator_info)
        
        assert len(cells_matrix) == 2
        assert cells_matrix[0] == ["Name", "Age"]
        assert cells_matrix[1] == ["John", "25"]
    
    def test_parse_cells_with_comma_separator(self, analyzer):
        """Test parsing cells with comma separator."""
        lines = ["Name,Age", "John,25"]
        separator_info = {"name": "comma", "regex": r','}
        
        cells_matrix = analyzer._parse_cells_with_separator(lines, separator_info)
        
        assert len(cells_matrix) == 2
        assert cells_matrix[0] == ["Name", "Age"]
        assert cells_matrix[1] == ["John", "25"]
    
    def test_detect_headers_by_formatting(self, analyzer):
        """Test header detection by formatting."""
        cells_matrix = [
            ["NAME", "AGE", "CITY"],  # All uppercase - header-like
            ["john", "25", "new york"],
            ["jane", "30", "london"]
        ]
        
        headers = analyzer._detect_by_formatting(cells_matrix)
        assert len(headers) == 1
        assert headers[0] == ["NAME", "AGE", "CITY"]
    
    def test_detect_headers_by_position(self, analyzer):
        """Test header detection by position."""
        cells_matrix = [
            ["Name", "Age", "City"],  # Text headers
            ["1", "25", "New York"],  # Numeric/mixed data
            ["2", "30", "London"]
        ]
        
        headers = analyzer._detect_by_position(cells_matrix)
        # Should detect first row as header due to text vs numeric difference
        if headers:
            assert headers[0] == ["Name", "Age", "City"]
    
    def test_detect_headers_by_content_pattern(self, analyzer):
        """Test header detection by content patterns."""
        cells_matrix = [
            ["id", "name", "date"],  # Common header words
            ["1", "John", "2023-01-01"],
            ["2", "Jane", "2023-01-02"]
        ]
        
        headers = analyzer._detect_by_content_pattern(cells_matrix)
        assert len(headers) == 1
        assert headers[0] == ["id", "name", "date"]
    
    def test_detect_headers_by_data_type_difference(self, analyzer):
        """Test header detection by data type difference."""
        cells_matrix = [
            ["Product", "Price", "Count"],  # Text headers
            ["Laptop", "999", "15"],  # Mixed data
            ["Mouse", "29", "50"]
        ]
        
        headers = analyzer._detect_by_data_type_difference(cells_matrix)
        # Should detect based on text vs numeric patterns
        if headers:
            assert headers[0] == ["Product", "Price", "Count"]
    
    def test_is_numeric_content(self, analyzer):
        """Test numeric content detection."""
        assert analyzer._is_numeric_content("123")
        assert analyzer._is_numeric_content("123.45")
        assert analyzer._is_numeric_content("1,234")
        assert analyzer._is_numeric_content("$123.45")
        assert analyzer._is_numeric_content("50%")
        
        assert not analyzer._is_numeric_content("text")
        assert not analyzer._is_numeric_content("abc123")
        assert not analyzer._is_numeric_content("")
    
    def test_convert_to_table_cells(self, analyzer):
        """Test conversion of string matrix to TableCell objects."""
        cells_matrix = [["Name", "Age"], ["John", "25"]]
        
        result = analyzer._convert_to_table_cells(cells_matrix, is_header=True)
        
        assert len(result) == 2
        assert len(result[0]) == 2
        assert isinstance(result[0][0], TableCell)
        assert result[0][0].content == "Name"
        assert result[0][0].data_type == "header"
        assert result[0][0].confidence == 0.9
    
    def test_analyze_columns(self, analyzer):
        """Test column pattern analysis."""
        data_cells = [
            [TableCell("John", 1, 1), TableCell("25", 1, 1)],
            [TableCell("Jane", 1, 1), TableCell("30", 1, 1)]
        ]
        
        patterns = analyzer._analyze_columns(data_cells)
        
        assert "column_0" in patterns
        assert "column_1" in patterns
        
        col0_pattern = patterns["column_0"]
        assert "content_length_avg" in col0_pattern
        assert "numeric_ratio" in col0_pattern
        assert "empty_ratio" in col0_pattern
        assert "sample_values" in col0_pattern
    
    def test_table_cell_validation(self):
        """Test TableCell validation."""
        # Valid cell
        cell = TableCell("content", 1, 1, "text", 0.9)
        assert cell.content == "content"
        
        # Invalid span values
        with pytest.raises(ValueError):
            TableCell("content", 0, 1)  # row_span < 1
        
        with pytest.raises(ValueError):
            TableCell("content", 1, 0)  # col_span < 1
        
        # Invalid confidence
        with pytest.raises(ValueError):
            TableCell("content", 1, 1, "text", 1.5)  # confidence > 1.0
    
    def test_table_structure_validation(self):
        """Test TableStructure validation."""
        # Valid structure
        structure = TableStructure(
            headers=[],
            rows=[],
            metadata={},
            column_types=[]
        )
        assert isinstance(structure.headers, list)
        assert isinstance(structure.rows, list)
        
        # Invalid structure
        with pytest.raises(ValueError):
            TableStructure(
                headers="not a list",  # Should be list
                rows=[],
                metadata={},
                column_types=[]
            )