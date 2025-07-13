"""Comprehensive tests for TableParser functionality."""

import pytest
import asyncio
from unittest.mock import Mock, patch

from src.torematrix.core.processing.parsers.table import TableParser, TableCell, TableStructure
from src.torematrix.core.processing.parsers.types import ParserConfig, ElementType, ProcessingHints
from src.torematrix.core.processing.parsers.base import ParserResult


class MockElement:
    """Mock element for testing."""
    
    def __init__(self, text: str, element_type: str = "Table", element_id: str = "test-id"):
        self.text = text
        self.element_type = Mock()
        self.element_type.value = element_type
        self.element_id = element_id
        self.metadata = {}


class TestTableParser:
    """Test suite for TableParser."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        config = ParserConfig()
        return TableParser(config)
    
    @pytest.fixture
    def simple_table_element(self):
        """Create simple table element."""
        table_text = """Name | Age | City
John | 25 | New York
Jane | 30 | London"""
        return MockElement(table_text)
    
    @pytest.fixture
    def csv_table_element(self):
        """Create CSV-style table element."""
        table_text = """Product,Price,Stock
Laptop,999.99,15
Mouse,29.99,50
Keyboard,79.99,25"""
        return MockElement(table_text)
    
    @pytest.fixture
    def complex_table_element(self):
        """Create complex table with mixed data types."""
        table_text = """ID | Product Name | Price | Available | Launch Date
1 | Gaming Laptop | $1299.99 | Yes | 2023-01-15
2 | Wireless Mouse | $49.99 | No | 2022-11-20
3 | Mechanical Keyboard | $129.99 | Yes | 2023-03-10"""
        return MockElement(table_text)
    
    def test_parser_capabilities(self, parser):
        """Test parser capabilities."""
        caps = parser.capabilities
        assert ElementType.TABLE in caps.supported_types
        assert caps.supports_async
        assert caps.supports_validation
        assert "csv" in caps.supports_export_formats
        assert "json" in caps.supports_export_formats
        assert "html" in caps.supports_export_formats
    
    def test_can_parse_table_element(self, parser, simple_table_element):
        """Test parser can identify table elements."""
        assert parser.can_parse(simple_table_element)
    
    def test_can_parse_non_table_element(self, parser):
        """Test parser rejects non-table elements."""
        text_element = MockElement("Just some regular text without table structure", "Text")
        assert not parser.can_parse(text_element)
    
    def test_table_indicators_detection(self, parser):
        """Test detection of table-like patterns."""
        # Pipe-separated
        pipe_element = MockElement("col1 | col2 | col3\nval1 | val2 | val3")
        assert parser._has_table_indicators(pipe_element)
        
        # Tab-separated
        tab_element = MockElement("col1\tcol2\tcol3\nval1\tval2\tval3")
        assert parser._has_table_indicators(tab_element)
        
        # CSV-like
        csv_element = MockElement("col1,col2,col3\nval1,val2,val3")
        assert parser._has_table_indicators(csv_element)
        
        # Regular text
        text_element = MockElement("This is just regular text")
        assert not parser._has_table_indicators(text_element)
    
    @pytest.mark.asyncio
    async def test_parse_simple_table(self, parser, simple_table_element):
        """Test parsing simple pipe-separated table."""
        result = await parser.parse(simple_table_element)
        
        assert result.success
        assert result.metadata.confidence > 0.5
        
        data = result.data
        assert data["has_headers"]
        assert data["dimensions"]["rows"] == 2  # Data rows (excluding header)
        assert data["dimensions"]["columns"] == 3
        assert len(data["headers"]) == 3
        assert "Name" in data["headers"]
        assert "Age" in data["headers"]
        assert "City" in data["headers"]
    
    @pytest.mark.asyncio
    async def test_parse_csv_table(self, parser, csv_table_element):
        """Test parsing CSV-style table."""
        result = await parser.parse(csv_table_element)
        
        assert result.success
        assert result.metadata.confidence > 0.5
        
        data = result.data
        assert data["dimensions"]["rows"] == 3
        assert data["dimensions"]["columns"] == 3
        assert "Product" in data["headers"]
        assert "Price" in data["headers"]
        assert "Stock" in data["headers"]
    
    @pytest.mark.asyncio
    async def test_parse_complex_table_with_types(self, parser, complex_table_element):
        """Test parsing complex table with data type detection."""
        result = await parser.parse(complex_table_element)
        
        assert result.success
        assert result.metadata.confidence > 0.6
        
        data = result.data
        column_types = data["column_types"]
        
        # Should detect different data types
        assert len(column_types) == 5
        # ID column should be detected as number
        # Price should be detected as number (currency)
        # Available should be detected as boolean-like
        # Date should be detected appropriately
    
    @pytest.mark.asyncio
    async def test_parse_empty_element(self, parser):
        """Test parsing empty element."""
        empty_element = MockElement("")
        result = await parser.parse(empty_element)
        
        assert not result.success
        assert "No table data found" in result.validation_errors[0]
    
    @pytest.mark.asyncio
    async def test_parse_malformed_table(self, parser):
        """Test parsing malformed table data."""
        malformed_element = MockElement("col1 | col2\nval1\nval2 | val3 | val4")
        result = await parser.parse(malformed_element)
        
        # Should still succeed but with lower confidence or warnings
        if result.success:
            assert result.metadata.confidence < 0.8
        else:
            assert len(result.validation_errors) > 0
    
    def test_validation_with_valid_result(self, parser):
        """Test validation with valid parsing result."""
        # Create mock valid result
        structure = TableStructure(
            headers=[[TableCell("Name"), TableCell("Age")]],
            rows=[[TableCell("John"), TableCell("25")]],
            metadata={},
            column_types=["text", "number"],
            has_headers=True
        )
        
        result = ParserResult(
            success=True,
            data={
                "structure": structure,
                "dimensions": {"rows": 1, "columns": 2}
            },
            metadata=Mock(),
            validation_errors=[]
        )
        result.metadata.element_metadata = {"data_quality": 0.9}
        
        errors = parser.validate(result)
        assert len(errors) == 0
    
    def test_validation_with_invalid_result(self, parser):
        """Test validation with invalid parsing result."""
        result = ParserResult(
            success=False,
            data={},
            metadata=Mock(),
            validation_errors=["Parse failed"]
        )
        
        errors = parser.validate(result)
        assert len(errors) > 0
        assert "Table parsing failed" in errors
    
    def test_validation_with_dimension_errors(self, parser):
        """Test validation with dimension errors."""
        result = ParserResult(
            success=True,
            data={
                "structure": Mock(),
                "dimensions": {"rows": 0, "columns": 0}
            },
            metadata=Mock(),
            validation_errors=[]
        )
        result.metadata.element_metadata = {"data_quality": 0.9}
        
        errors = parser.validate(result)
        assert len(errors) >= 2  # No rows and no columns
        assert any("no data rows" in error for error in errors)
        assert any("no columns" in error for error in errors)
    
    def test_cell_creation_validation(self):
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
    
    def test_export_formats(self, parser):
        """Test export format generation."""
        structure = TableStructure(
            headers=[[TableCell("Name"), TableCell("Age")]],
            rows=[[TableCell("John"), TableCell("25")]],
            metadata={},
            column_types=["text", "number"],
            has_headers=True
        )
        
        formats = parser._export_formats(structure)
        
        assert "csv" in formats
        assert "json" in formats
        assert "html" in formats
        
        # Test CSV format
        csv_content = formats["csv"]
        assert "Name,Age" in csv_content
        assert "John,25" in csv_content
        
        # Test JSON format
        json_content = formats["json"]
        assert json_content["headers"] == [["Name", "Age"]]
        assert json_content["data"] == [["John", "25"]]
        
        # Test HTML format
        html_content = formats["html"]
        assert "<table>" in html_content
        assert "<th>Name</th>" in html_content
        assert "<td>John</td>" in html_content
    
    @pytest.mark.asyncio
    async def test_performance_simple_table(self, parser, simple_table_element):
        """Test parsing performance for simple table."""
        import time
        
        start_time = time.time()
        result = await parser.parse(simple_table_element)
        end_time = time.time()
        
        assert result.success
        # Should parse simple table in under 100ms
        assert (end_time - start_time) < 0.1
    
    def test_consistent_separator_detection(self, parser):
        """Test consistent separator detection algorithm."""
        # Highly consistent pipe separation
        lines = ["col1 | col2 | col3", "val1 | val2 | val3", "val4 | val5 | val6"]
        assert parser._has_consistent_separators(lines, r'\|')
        
        # Inconsistent separation
        lines = ["col1 | col2", "val1 | val2 | val3", "val4"]
        assert not parser._has_consistent_separators(lines, r'\|')
        
        # Empty lines
        assert not parser._has_consistent_separators([], r'\|')
    
    def test_table_confidence_calculation(self, parser):
        """Test table confidence score calculation."""
        # High quality structure
        good_structure = TableStructure(
            headers=[[TableCell("Name"), TableCell("Age")]],
            rows=[
                [TableCell("John"), TableCell("25")],
                [TableCell("Jane"), TableCell("30")]
            ],
            metadata={},
            column_types=["text", "number"],
            has_headers=True
        )
        
        confidence = parser._calculate_table_confidence(good_structure, [])
        assert confidence > 0.8
        
        # Lower quality with validation errors
        confidence_with_errors = parser._calculate_table_confidence(good_structure, ["Error 1", "Error 2"])
        assert confidence_with_errors < confidence
    
    def test_table_classification(self, parser):
        """Test table type classification."""
        # Simple table
        simple_structure = TableStructure(
            headers=[],
            rows=[[TableCell("A"), TableCell("B")]],
            metadata={},
            column_types=[]
        )
        assert parser._classify_table_type(simple_structure) == "simple"
        
        # Complex table
        complex_rows = []
        for i in range(25):
            row = [TableCell(f"val{i}_{j}") for j in range(12)]
            complex_rows.append(row)
        
        complex_structure = TableStructure(
            headers=[],
            rows=complex_rows,
            metadata={},
            column_types=[]
        )
        assert parser._classify_table_type(complex_structure) == "complex"
    
    @pytest.mark.parametrize("table_text,expected_success", [
        ("Name|Age\nJohn|25", True),  # Simple pipe
        ("Name\tAge\nJohn\t25", True),  # Tab separated
        ("Name,Age\nJohn,25", True),  # CSV
        ("Just text", False),  # No table pattern
        ("", False),  # Empty
    ])
    @pytest.mark.asyncio
    async def test_parse_various_formats(self, parser, table_text, expected_success):
        """Test parsing various table formats."""
        element = MockElement(table_text)
        result = await parser.parse(element)
        assert result.success == expected_success
    
    def test_data_quality_assessment(self, parser):
        """Test data quality assessment."""
        # High quality (no empty cells)
        high_quality = TableStructure(
            headers=[],
            rows=[
                [TableCell("John"), TableCell("25")],
                [TableCell("Jane"), TableCell("30")]
            ],
            metadata={},
            column_types=[]
        )
        quality = parser._assess_data_quality(high_quality)
        assert quality == 1.0
        
        # Lower quality (some empty cells)
        low_quality = TableStructure(
            headers=[],
            rows=[
                [TableCell("John"), TableCell("")],
                [TableCell(""), TableCell("30")]
            ],
            metadata={},
            column_types=[]
        )
        quality = parser._assess_data_quality(low_quality)
        assert quality == 0.5