"""Comprehensive tests for ListParser functionality."""

import pytest
import asyncio
from unittest.mock import Mock

from src.torematrix.core.processing.parsers.list import ListParser
from src.torematrix.core.processing.parsers.structural.list_detector import ListItem, ListStructure, ListType
from src.torematrix.core.processing.parsers.types import ParserConfig, ElementType, ProcessingHints
from src.torematrix.core.processing.parsers.base import ParserResult


class MockElement:
    """Mock element for testing."""
    
    def __init__(self, text: str, element_type: str = "List", element_id: str = "test-id"):
        self.text = text
        self.element_type = Mock()
        self.element_type.value = element_type
        self.element_id = element_id
        self.metadata = {}


class TestListParser:
    """Test suite for ListParser."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        config = ParserConfig()
        return ListParser(config)
    
    @pytest.fixture
    def simple_ordered_list(self):
        """Create simple ordered list element."""
        list_text = """1. First item
2. Second item
3. Third item"""
        return MockElement(list_text)
    
    @pytest.fixture
    def simple_unordered_list(self):
        """Create simple unordered list element."""
        list_text = """• First item
• Second item
• Third item"""
        return MockElement(list_text)
    
    @pytest.fixture
    def nested_list(self):
        """Create nested list element."""
        list_text = """1. First level item
   a. Second level item
   b. Another second level
      i. Third level item
2. Another first level
   a. More second level"""
        return MockElement(list_text)
    
    @pytest.fixture
    def complex_mixed_list(self):
        """Create complex mixed list element."""
        list_text = """1. Ordered item
• Unordered item
  - Nested unordered
    • Deep nested
2. Back to ordered
   a. Mixed nested ordered"""
        return MockElement(list_text)
    
    @pytest.fixture
    def definition_list(self):
        """Create definition list element."""
        list_text = """Term 1: Definition of first term
Term 2: Definition of second term
Long Term: A much longer definition that spans and explains the concept"""
        return MockElement(list_text)
    
    def test_parser_capabilities(self, parser):
        """Test parser capabilities."""
        caps = parser.capabilities
        assert ElementType.LIST in caps.supported_types
        assert ElementType.LIST_ITEM in caps.supported_types
        assert caps.supports_async
        assert caps.supports_validation
        assert "json" in caps.supports_export_formats
        assert "html" in caps.supports_export_formats
        assert "markdown" in caps.supports_export_formats
    
    def test_can_parse_list_element(self, parser, simple_ordered_list):
        """Test parser can identify list elements."""
        assert parser.can_parse(simple_ordered_list)
    
    def test_can_parse_various_list_types(self, parser, simple_unordered_list, definition_list):
        """Test parser can identify various list types."""
        assert parser.can_parse(simple_unordered_list)
        assert parser.can_parse(definition_list)
    
    def test_can_parse_non_list_element(self, parser):
        """Test parser rejects non-list elements."""
        text_element = MockElement("Just some regular text without list structure", "Text")
        assert not parser.can_parse(text_element)
    
    def test_list_indicators_detection(self, parser):
        """Test detection of list-like patterns."""
        # Numbered list
        numbered = MockElement("1. Item one\n2. Item two\n3. Item three")
        assert parser._has_list_indicators(numbered)
        
        # Bullet list
        bullet = MockElement("• Item one\n• Item two\n• Item three")
        assert parser._has_list_indicators(bullet)
        
        # Dash list
        dash = MockElement("- Item one\n- Item two\n- Item three")
        assert parser._has_list_indicators(dash)
        
        # Definition list
        definition = MockElement("Term: Definition\nOther: Another definition")
        assert parser._has_list_indicators(definition)
        
        # Regular text
        text = MockElement("This is just regular text")
        assert not parser._has_list_indicators(text)
    
    @pytest.mark.asyncio
    async def test_parse_simple_ordered_list(self, parser, simple_ordered_list):
        """Test parsing simple ordered list."""
        result = await parser.parse(simple_ordered_list)
        
        assert result.success
        assert result.metadata.confidence > 0.7
        
        data = result.data
        stats = data["statistics"]
        assert stats["total_items"] == 3
        assert stats["max_depth"] == 0  # All items at level 0
        assert stats["list_type"] == "ordered"
        assert not stats["has_mixed_content"]
    
    @pytest.mark.asyncio
    async def test_parse_simple_unordered_list(self, parser, simple_unordered_list):
        """Test parsing simple unordered list."""
        result = await parser.parse(simple_unordered_list)
        
        assert result.success
        assert result.metadata.confidence > 0.7
        
        data = result.data
        stats = data["statistics"]
        assert stats["total_items"] == 3
        assert stats["list_type"] == "unordered"
    
    @pytest.mark.asyncio
    async def test_parse_nested_list(self, parser, nested_list):
        """Test parsing nested list with hierarchy."""
        result = await parser.parse(nested_list)
        
        assert result.success
        assert result.metadata.confidence > 0.6
        
        data = result.data
        stats = data["statistics"]
        assert stats["max_depth"] >= 2  # Should detect multiple levels
        assert stats["total_items"] >= 5
        
        # Check hierarchy structure
        hierarchy = data["hierarchy"]
        assert hierarchy["type"] == "nested_list"
        assert len(hierarchy["items"]) > 0
    
    @pytest.mark.asyncio
    async def test_parse_complex_mixed_list(self, parser, complex_mixed_list):
        """Test parsing complex mixed list."""
        result = await parser.parse(complex_mixed_list)
        
        assert result.success
        
        data = result.data
        stats = data["statistics"]
        assert stats["has_mixed_content"]  # Should detect mixed content
        assert stats["list_type"] == "mixed"
    
    @pytest.mark.asyncio
    async def test_parse_definition_list(self, parser, definition_list):
        """Test parsing definition list."""
        result = await parser.parse(definition_list)
        
        assert result.success
        
        data = result.data
        stats = data["statistics"]
        assert stats["list_type"] in ["definition", "mixed"]  # Could be detected as either
    
    @pytest.mark.asyncio
    async def test_parse_deep_nested_list(self, parser):
        """Test parsing very deep nested list."""
        # Create 6-level deep list (exceeds default max of 5)
        deep_text = """1. Level 1
  a. Level 2
    i. Level 3
      - Level 4
        • Level 5
          * Level 6"""
        
        deep_element = MockElement(deep_text)
        result = await parser.parse(deep_element)
        
        # Should truncate to max depth
        assert result.success
        data = result.data
        assert data["statistics"]["max_depth"] <= 5
    
    @pytest.mark.asyncio
    async def test_parse_empty_element(self, parser):
        """Test parsing empty element."""
        empty_element = MockElement("")
        result = await parser.parse(empty_element)
        
        assert not result.success
        assert "No list items found" in result.validation_errors[0]
    
    @pytest.mark.asyncio
    async def test_parse_insufficient_items(self, parser):
        """Test parsing element with too few items."""
        single_item = MockElement("1. Only one item")
        result = await parser.parse(single_item)
        
        # Should fail or have low confidence due to min_items requirement
        if not result.success:
            assert len(result.validation_errors) > 0
        else:
            assert result.metadata.confidence < 0.7
    
    def test_validation_with_valid_result(self, parser):
        """Test validation with valid parsing result."""
        structure = ListStructure(
            items=[
                ListItem("Item 1", 0, "ordered", "1"),
                ListItem("Item 2", 0, "ordered", "2")
            ],
            list_type=ListType.ORDERED,
            max_depth=0,
            total_items=2
        )
        
        result = ParserResult(
            success=True,
            data={
                "structure": structure,
                "statistics": {
                    "total_items": 2,
                    "max_depth": 0
                }
            },
            metadata=Mock(),
            validation_errors=[]
        )
        result.metadata.element_metadata = {"structure_quality": 0.9}
        
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
        assert "List parsing failed" in errors
    
    def test_validation_with_depth_errors(self, parser):
        """Test validation with excessive depth."""
        structure = ListStructure(
            items=[],
            list_type=ListType.ORDERED,
            max_depth=10,  # Exceeds max_depth of 5
            total_items=0
        )
        
        result = ParserResult(
            success=True,
            data={
                "structure": structure,
                "statistics": {"max_depth": 10, "total_items": 0}
            },
            metadata=Mock(),
            validation_errors=[]
        )
        result.metadata.element_metadata = {"structure_quality": 0.9}
        
        errors = parser.validate(result)
        assert len(errors) >= 2  # Depth error + no items
        assert any("depth" in error for error in errors)
        assert any("no items" in error for error in errors)
    
    def test_list_item_creation(self):
        """Test ListItem creation and validation."""
        item = ListItem(
            content="Test content",
            level=1,
            item_type="ordered",
            number="1",
            metadata={"test": "value"}
        )
        
        assert item.content == "Test content"
        assert item.level == 1
        assert item.item_type == "ordered"
        assert item.number == "1"
        assert item.metadata["test"] == "value"
        assert len(item.children) == 0
    
    def test_list_structure_creation(self):
        """Test ListStructure creation."""
        items = [
            ListItem("Item 1", 0, "ordered", "1"),
            ListItem("Item 2", 0, "ordered", "2")
        ]
        
        structure = ListStructure(
            items=items,
            list_type=ListType.ORDERED,
            max_depth=0,
            total_items=2,
            has_mixed_content=False
        )
        
        assert len(structure.items) == 2
        assert structure.list_type == ListType.ORDERED
        assert structure.max_depth == 0
        assert structure.total_items == 2
        assert not structure.has_mixed_content
    
    def test_export_formats(self, parser):
        """Test export format generation."""
        structure = ListStructure(
            items=[
                ListItem("First item", 0, "ordered", "1"),
                ListItem("Second item", 0, "ordered", "2")
            ],
            list_type=ListType.ORDERED,
            max_depth=0,
            total_items=2
        )
        
        formats = parser._export_formats(structure)
        
        assert "json" in formats
        assert "html" in formats
        assert "markdown" in formats
        assert "text" in formats
        
        # Test JSON format
        json_content = formats["json"]
        assert json_content["list_type"] == "ordered"
        assert json_content["total_items"] == 2
        assert len(json_content["items"]) == 2
        
        # Test HTML format
        html_content = formats["html"]
        assert "<ol>" in html_content or "<ul>" in html_content
        assert "<li>First item</li>" in html_content
        
        # Test Markdown format
        markdown_content = formats["markdown"]
        assert "1. First item" in markdown_content
        assert "2. Second item" in markdown_content
    
    @pytest.mark.asyncio
    async def test_performance_simple_list(self, parser, simple_ordered_list):
        """Test parsing performance for simple list."""
        import time
        
        start_time = time.time()
        result = await parser.parse(simple_ordered_list)
        end_time = time.time()
        
        assert result.success
        # Should parse simple list in under 50ms
        assert (end_time - start_time) < 0.05
    
    def test_flatten_items(self, parser):
        """Test flattening of list items to dictionary format."""
        items = [
            ListItem("Item 1", 0, "ordered", "1", metadata={"test": "value"}),
            ListItem("Item 2", 1, "ordered", "a")
        ]
        
        flattened = parser._flatten_items(items)
        
        assert len(flattened) == 2
        assert flattened[0]["content"] == "Item 1"
        assert flattened[0]["level"] == 0
        assert flattened[0]["type"] == "ordered"
        assert flattened[0]["number"] == "1"
        assert flattened[0]["metadata"]["test"] == "value"
        
        assert flattened[1]["level"] == 1
        assert flattened[1]["number"] == "a"
    
    def test_hierarchy_export(self, parser):
        """Test hierarchical structure export."""
        parent = ListItem("Parent", 0, "ordered", "1")
        child = ListItem("Child", 1, "ordered", "a")
        parent.children = [child]
        
        hierarchy = parser._export_hierarchy([parent])
        
        assert hierarchy["type"] == "nested_list"
        assert len(hierarchy["items"]) == 1
        
        parent_dict = hierarchy["items"][0]
        assert parent_dict["content"] == "Parent"
        assert "children" in parent_dict
        assert len(parent_dict["children"]) == 1
        assert parent_dict["children"][0]["content"] == "Child"
    
    @pytest.mark.parametrize("list_text,expected_success,expected_type", [
        ("1. Item\n2. Item", True, "ordered"),  # Ordered
        ("• Item\n• Item", True, "unordered"),  # Unordered
        ("- Item\n- Item", True, "unordered"),  # Dash
        ("Term: Def\nOther: Def", True, "definition"),  # Definition
        ("Just text", False, None),  # No list pattern
        ("", False, None),  # Empty
    ])
    @pytest.mark.asyncio
    async def test_parse_various_list_formats(self, parser, list_text, expected_success, expected_type):
        """Test parsing various list formats."""
        element = MockElement(list_text)
        result = await parser.parse(element)
        
        assert result.success == expected_success
        if expected_success and expected_type:
            assert result.data["statistics"]["list_type"] == expected_type
    
    def test_complexity_calculation(self, parser):
        """Test list complexity calculation."""
        # Simple list
        simple_structure = ListStructure(
            items=[ListItem("Item", 0, "ordered", "1")],
            list_type=ListType.ORDERED,
            max_depth=0,
            total_items=1
        )
        assert parser._calculate_complexity(simple_structure) == "low"
        
        # Complex list (deep nesting)
        complex_structure = ListStructure(
            items=[],
            list_type=ListType.MIXED,
            max_depth=4,
            total_items=25
        )
        assert parser._calculate_complexity(complex_structure) == "high"
    
    def test_content_density_calculation(self, parser):
        """Test content density calculation."""
        structure = ListStructure(
            items=[
                ListItem("Short", 0, "ordered", "1"),
                ListItem("Much longer content here", 0, "ordered", "2")
            ],
            list_type=ListType.ORDERED,
            max_depth=0,
            total_items=2
        )
        
        density = parser._calculate_content_density(structure)
        expected_avg = (len("Short") + len("Much longer content here")) / 2
        assert density == expected_avg
    
    def test_structure_quality_assessment(self, parser):
        """Test structure quality assessment."""
        # High quality structure
        high_quality = ListStructure(
            items=[
                ListItem("Good content", 0, "ordered", "1"),
                ListItem("More content", 1, "ordered", "a")
            ],
            list_type=ListType.ORDERED,
            max_depth=1,
            total_items=2,
            has_mixed_content=False
        )
        
        quality = parser._assess_structure_quality(high_quality)
        assert quality > 0.8
        
        # Lower quality structure (mixed, deep, empty content)
        low_quality = ListStructure(
            items=[
                ListItem("", 0, "ordered", "1"),  # Empty content
                ListItem("Content", 5, "unordered", None)  # Very deep, mixed type
            ],
            list_type=ListType.MIXED,
            max_depth=5,
            total_items=2,
            has_mixed_content=True
        )
        
        quality = parser._assess_structure_quality(low_quality)
        assert quality < 0.6