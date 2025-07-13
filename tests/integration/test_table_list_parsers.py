"""Integration tests for table and list parsers."""

import pytest
import asyncio
import json
from pathlib import Path

from src.torematrix.core.processing.parsers.table import TableParser
from src.torematrix.core.processing.parsers.list import ListParser
from src.torematrix.core.processing.parsers.types import ParserConfig


class MockElement:
    """Mock element for integration testing."""
    
    def __init__(self, text: str, element_type: str = "Table", element_id: str = "test-id"):
        self.text = text
        self.element_type = type('ElementType', (), {'value': element_type})()
        self.element_id = element_id
        self.metadata = {}


class TestTableListParsersIntegration:
    """Integration tests for table and list parsers."""
    
    @pytest.fixture
    def table_parser(self):
        """Create table parser instance."""
        config = ParserConfig()
        return TableParser(config)
    
    @pytest.fixture
    def list_parser(self):
        """Create list parser instance."""
        config = ParserConfig()
        return ListParser(config)
    
    @pytest.fixture
    def sample_tables(self):
        """Load sample table fixtures."""
        fixtures_path = Path(__file__).parent.parent / "fixtures" / "parsers" / "sample_tables.json"
        with open(fixtures_path) as f:
            return json.load(f)
    
    @pytest.fixture
    def sample_lists(self):
        """Load sample list fixtures."""
        fixtures_path = Path(__file__).parent.parent / "fixtures" / "parsers" / "sample_lists.json"
        with open(fixtures_path) as f:
            return json.load(f)
    
    @pytest.mark.asyncio
    async def test_table_parser_integration(self, table_parser, sample_tables):
        """Test table parser with all sample fixtures."""
        for table_name, table_data in sample_tables.items():
            element = MockElement(table_data["text"], "Table")
            
            # Test parsing
            result = await table_parser.parse(element)
            
            assert result.success, f"Failed to parse {table_name}: {result.validation_errors}"
            assert result.metadata.confidence > 0.5, f"Low confidence for {table_name}"
            
            # Validate dimensions if specified
            expected = table_data["expected"]
            if "rows" in expected:
                assert result.data["dimensions"]["rows"] == expected["rows"]
            if "columns" in expected:
                assert result.data["dimensions"]["columns"] == expected["columns"]
            
            # Validate headers if specified
            if "headers" in expected:
                assert len(result.data["headers"]) == len(expected["headers"])
                for expected_header in expected["headers"]:
                    assert expected_header in result.data["headers"]
    
    @pytest.mark.asyncio
    async def test_list_parser_integration(self, list_parser, sample_lists):
        """Test list parser with all sample fixtures."""
        for list_name, list_data in sample_lists.items():
            element = MockElement(list_data["text"], "List")
            
            # Test parsing
            result = await list_parser.parse(element)
            
            assert result.success, f"Failed to parse {list_name}: {result.validation_errors}"
            assert result.metadata.confidence > 0.5, f"Low confidence for {list_name}"
            
            # Validate structure if specified
            expected = list_data["expected"]
            stats = result.data["statistics"]
            
            if "total_items" in expected:
                assert stats["total_items"] == expected["total_items"]
            if "max_depth" in expected:
                assert stats["max_depth"] == expected["max_depth"]
            if "list_type" in expected:
                assert stats["list_type"] == expected["list_type"]
            if "has_mixed_content" in expected:
                assert stats["has_mixed_content"] == expected["has_mixed_content"]
    
    @pytest.mark.asyncio
    async def test_performance_requirements(self, table_parser, list_parser):
        """Test that parsers meet performance requirements."""
        import time
        
        # Test table parsing performance (<100ms)
        table_element = MockElement("""
Name | Age | City | Country
John | 25 | New York | USA
Jane | 30 | London | UK
Bob | 35 | Paris | France
""", "Table")
        
        start_time = time.time()
        table_result = await table_parser.parse(table_element)
        table_time = time.time() - start_time
        
        assert table_result.success
        assert table_time < 0.1, f"Table parsing took {table_time:.3f}s, should be <0.1s"
        
        # Test list parsing performance (<50ms)
        list_element = MockElement("""
1. First item
   a. Nested item
   b. Another nested
2. Second item
3. Third item
""", "List")
        
        start_time = time.time()
        list_result = await list_parser.parse(list_element)
        list_time = time.time() - start_time
        
        assert list_result.success
        assert list_time < 0.05, f"List parsing took {list_time:.3f}s, should be <0.05s"
    
    @pytest.mark.asyncio
    async def test_export_format_consistency(self, table_parser, list_parser):
        """Test that export formats are consistent and valid."""
        # Test table exports
        table_element = MockElement("Name | Age\nJohn | 25", "Table")
        table_result = await table_parser.parse(table_element)
        
        assert table_result.success
        assert "csv" in table_result.export_formats
        assert "json" in table_result.export_formats
        assert "html" in table_result.export_formats
        
        # Validate CSV format
        csv_content = table_result.export_formats["csv"]
        assert "Name,Age" in csv_content
        assert "John,25" in csv_content
        
        # Validate JSON format
        json_content = table_result.export_formats["json"]
        assert json_content["headers"] == [["Name", "Age"]]
        assert json_content["data"] == [["John", "25"]]
        
        # Test list exports
        list_element = MockElement("1. First\n2. Second", "List")
        list_result = await list_parser.parse(list_element)
        
        assert list_result.success
        assert "json" in list_result.export_formats
        assert "html" in list_result.export_formats
        assert "markdown" in list_result.export_formats
        
        # Validate Markdown format
        markdown_content = list_result.export_formats["markdown"]
        assert "1. First" in markdown_content
        assert "2. Second" in markdown_content
    
    def test_parser_capabilities_compatibility(self, table_parser, list_parser):
        """Test that parser capabilities are compatible with framework."""
        # Test table parser capabilities
        table_caps = table_parser.capabilities
        assert len(table_caps.supported_types) > 0
        assert table_caps.supports_async
        assert table_caps.supports_validation
        assert table_caps.supports_structured_output
        assert len(table_caps.supports_export_formats) >= 3
        
        # Test list parser capabilities
        list_caps = list_parser.capabilities
        assert len(list_caps.supported_types) > 0
        assert list_caps.supports_async
        assert list_caps.supports_validation
        assert list_caps.supports_structured_output
        assert len(list_caps.supports_export_formats) >= 3
    
    @pytest.mark.asyncio
    async def test_error_handling_robustness(self, table_parser, list_parser):
        """Test that parsers handle errors gracefully."""
        # Test empty elements
        empty_element = MockElement("")
        
        table_result = await table_parser.parse(empty_element)
        assert not table_result.success
        assert len(table_result.validation_errors) > 0
        
        list_result = await list_parser.parse(empty_element)
        assert not list_result.success
        assert len(list_result.validation_errors) > 0
        
        # Test malformed content
        malformed_table = MockElement("random text without structure")
        table_result = await table_parser.parse(malformed_table)
        # Should either fail gracefully or succeed with low confidence
        if table_result.success:
            assert table_result.metadata.confidence < 0.7
        else:
            assert len(table_result.validation_errors) > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_parsing(self, table_parser, list_parser):
        """Test that parsers can handle concurrent operations."""
        # Create multiple parsing tasks
        table_tasks = []
        list_tasks = []
        
        for i in range(5):
            table_element = MockElement(f"Col1 | Col2\nVal{i}1 | Val{i}2", "Table")
            table_tasks.append(table_parser.parse(table_element))
            
            list_element = MockElement(f"1. Item {i}1\n2. Item {i}2", "List")
            list_tasks.append(list_parser.parse(list_element))
        
        # Run concurrently
        table_results = await asyncio.gather(*table_tasks)
        list_results = await asyncio.gather(*list_tasks)
        
        # Verify all succeeded
        for result in table_results:
            assert result.success
        
        for result in list_results:
            assert result.success
    
    def test_memory_usage(self, table_parser, list_parser):
        """Test that parsers don't have excessive memory usage."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Create and parse many elements
        for i in range(100):
            element = MockElement(f"Col1 | Col2\nVal{i} | Val{i}", "Table")
            # Just test creation, not full parsing to keep test fast
            assert table_parser.can_parse(element)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Should not increase memory by more than 10MB
        assert memory_increase < 10 * 1024 * 1024, f"Memory increased by {memory_increase} bytes"