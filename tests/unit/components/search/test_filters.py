"""
Unit tests for advanced filter system components.
"""

import pytest
from unittest.mock import Mock

from src.torematrix.core.models.element import Element, ElementType
from src.torematrix.core.models.metadata import ElementMetadata
from src.torematrix.ui.components.search.filters import (
    FilterManager, FilterSet, FilterGroup, FilterCondition,
    FilterType, FilterOperator, FilterLogic, FilterValue
)


class TestFilterValue:
    """Test FilterValue functionality."""
    
    def test_filter_value_creation(self):
        """Test creating filter values."""
        # String value
        string_val = FilterValue("test", "string")
        assert string_val.value == "test"
        assert string_val.data_type == "string"
        
        # Number value
        number_val = FilterValue(42.5, "number")
        assert number_val.value == 42.5
        assert number_val.data_type == "number"
        
        # List value
        list_val = FilterValue([1, 2, 3], "list")
        assert list_val.value == [1, 2, 3]
        assert list_val.data_type == "list"
    
    def test_filter_value_serialization(self):
        """Test filter value serialization."""
        value = FilterValue("test", "string")
        data = value.to_dict()
        
        assert data == {"value": "test", "data_type": "string"}
        
        # Test deserialization
        restored = FilterValue.from_dict(data)
        assert restored.value == value.value
        assert restored.data_type == value.data_type


class TestFilterCondition:
    """Test FilterCondition functionality."""
    
    @pytest.fixture
    def sample_elements(self):
        """Create sample elements for testing."""
        metadata1 = ElementMetadata(
            confidence=0.95,
            page_number=1,
            languages=["en"],
            detection_method="ml"
        )
        
        metadata2 = ElementMetadata(
            confidence=0.75,
            page_number=2,
            languages=["en", "fr"],
            detection_method="rule"
        )
        
        elements = [
            Element(
                element_id="elem-1",
                element_type=ElementType.TITLE,
                text="Document Title",
                metadata=metadata1
            ),
            Element(
                element_id="elem-2",
                element_type=ElementType.NARRATIVE_TEXT,
                text="This is narrative text content",
                metadata=metadata2
            ),
            Element(
                element_id="elem-3",
                element_type=ElementType.TABLE,
                text="Table with data",
                metadata=metadata1
            )
        ]
        
        return elements
    
    def test_condition_creation(self):
        """Test creating filter conditions."""
        condition = FilterCondition(
            filter_type=FilterType.TEXT_CONTENT,
            operator=FilterOperator.CONTAINS,
            value=FilterValue("test", "string")
        )
        
        assert condition.filter_type == FilterType.TEXT_CONTENT
        assert condition.operator == FilterOperator.CONTAINS
        assert condition.value.value == "test"
        assert condition.enabled == True
    
    def test_text_matching(self, sample_elements):
        """Test text content matching."""
        # Contains operator
        condition = FilterCondition(
            filter_type=FilterType.TEXT_CONTENT,
            operator=FilterOperator.CONTAINS,
            value=FilterValue("narrative", "string")
        )
        
        assert not condition.matches(sample_elements[0])  # Title
        assert condition.matches(sample_elements[1])      # Contains "narrative"
        assert not condition.matches(sample_elements[2])  # Table
        
        # Starts with operator
        condition.operator = FilterOperator.STARTS_WITH
        condition.value = FilterValue("This", "string")
        
        assert not condition.matches(sample_elements[0])
        assert condition.matches(sample_elements[1])      # Starts with "This"
        assert not condition.matches(sample_elements[2])
    
    def test_type_matching(self, sample_elements):
        """Test element type matching."""
        condition = FilterCondition(
            filter_type=FilterType.ELEMENT_TYPE,
            operator=FilterOperator.EQUALS,
            value=FilterValue(ElementType.TITLE.value, "string")
        )
        
        assert condition.matches(sample_elements[0])      # Title
        assert not condition.matches(sample_elements[1])  # Narrative
        assert not condition.matches(sample_elements[2])  # Table
        
        # IN operator with multiple types
        condition.operator = FilterOperator.IN
        condition.value = FilterValue([ElementType.TITLE.value, ElementType.TABLE.value], "list")
        
        assert condition.matches(sample_elements[0])      # Title
        assert not condition.matches(sample_elements[1])  # Narrative
        assert condition.matches(sample_elements[2])      # Table
    
    def test_confidence_matching(self, sample_elements):
        """Test confidence-based matching."""
        condition = FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.GREATER_THAN,
            value=FilterValue(0.8, "number")
        )
        
        assert condition.matches(sample_elements[0])      # 0.95 > 0.8
        assert not condition.matches(sample_elements[1])  # 0.75 < 0.8
        assert condition.matches(sample_elements[2])      # 0.95 > 0.8
        
        # Between operator
        condition.operator = FilterOperator.BETWEEN
        condition.value = FilterValue([0.7, 0.9], "list")
        
        assert not condition.matches(sample_elements[0])  # 0.95 > 0.9
        assert condition.matches(sample_elements[1])      # 0.75 in range
        assert not condition.matches(sample_elements[2])  # 0.95 > 0.9
    
    def test_page_matching(self, sample_elements):
        """Test page number matching."""
        condition = FilterCondition(
            filter_type=FilterType.PAGE_NUMBER,
            operator=FilterOperator.EQUALS,
            value=FilterValue(1, "number")
        )
        
        assert condition.matches(sample_elements[0])      # Page 1
        assert not condition.matches(sample_elements[1])  # Page 2
        assert condition.matches(sample_elements[2])      # Page 1
    
    def test_detection_method_matching(self, sample_elements):
        """Test detection method matching."""
        condition = FilterCondition(
            filter_type=FilterType.DETECTION_METHOD,
            operator=FilterOperator.CONTAINS,
            value=FilterValue("ml", "string")
        )
        
        assert condition.matches(sample_elements[0])      # "ml"
        assert not condition.matches(sample_elements[1])  # "rule"
        assert condition.matches(sample_elements[2])      # "ml"
    
    def test_disabled_condition(self, sample_elements):
        """Test disabled conditions."""
        condition = FilterCondition(
            filter_type=FilterType.TEXT_CONTENT,
            operator=FilterOperator.CONTAINS,
            value=FilterValue("nonexistent", "string"),
            enabled=False
        )
        
        # Disabled conditions should always match
        assert condition.matches(sample_elements[0])
        assert condition.matches(sample_elements[1])
        assert condition.matches(sample_elements[2])
    
    def test_condition_serialization(self):
        """Test condition serialization."""
        condition = FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.GREATER_THAN,
            value=FilterValue(0.8, "number"),
            field_name="custom_field"
        )
        
        data = condition.to_dict()
        
        assert data["filter_type"] == FilterType.CONFIDENCE.value
        assert data["operator"] == FilterOperator.GREATER_THAN.value
        assert data["field_name"] == "custom_field"
        assert data["value"]["value"] == 0.8
        
        # Test deserialization
        restored = FilterCondition.from_dict(data)
        assert restored.filter_type == condition.filter_type
        assert restored.operator == condition.operator
        assert restored.field_name == condition.field_name
        assert restored.value.value == condition.value.value


class TestFilterGroup:
    """Test FilterGroup functionality."""
    
    @pytest.fixture
    def sample_elements(self):
        """Create sample elements for testing."""
        metadata1 = ElementMetadata(confidence=0.95, page_number=1)
        metadata2 = ElementMetadata(confidence=0.75, page_number=2)
        
        elements = [
            Element(
                element_id="elem-1",
                element_type=ElementType.TITLE,
                text="Document Title",
                metadata=metadata1
            ),
            Element(
                element_id="elem-2", 
                element_type=ElementType.NARRATIVE_TEXT,
                text="This is narrative text",
                metadata=metadata2
            )
        ]
        
        return elements
    
    def test_group_creation(self):
        """Test creating filter groups."""
        group = FilterGroup(logic=FilterLogic.AND)
        
        assert group.logic == FilterLogic.AND
        assert group.enabled == True
        assert len(group.conditions) == 0
    
    def test_and_logic(self, sample_elements):
        """Test AND logic in groups."""
        group = FilterGroup(logic=FilterLogic.AND)
        
        # Add conditions: confidence > 0.8 AND type = TITLE
        group.add_condition(FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.GREATER_THAN,
            value=FilterValue(0.8, "number")
        ))
        
        group.add_condition(FilterCondition(
            filter_type=FilterType.ELEMENT_TYPE,
            operator=FilterOperator.EQUALS,
            value=FilterValue(ElementType.TITLE.value, "string")
        ))
        
        # First element: high confidence AND title -> matches
        assert group.matches(sample_elements[0])
        
        # Second element: low confidence, not title -> doesn't match
        assert not group.matches(sample_elements[1])
    
    def test_or_logic(self, sample_elements):
        """Test OR logic in groups."""
        group = FilterGroup(logic=FilterLogic.OR)
        
        # Add conditions: confidence > 0.9 OR type = NARRATIVE_TEXT
        group.add_condition(FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.GREATER_THAN,
            value=FilterValue(0.9, "number")
        ))
        
        group.add_condition(FilterCondition(
            filter_type=FilterType.ELEMENT_TYPE,
            operator=FilterOperator.EQUALS,
            value=FilterValue(ElementType.NARRATIVE_TEXT.value, "string")
        ))
        
        # First element: high confidence -> matches
        assert group.matches(sample_elements[0])
        
        # Second element: narrative text -> matches
        assert group.matches(sample_elements[1])
    
    def test_not_logic(self, sample_elements):
        """Test NOT logic in groups."""
        group = FilterGroup(logic=FilterLogic.NOT)
        
        # Add condition: NOT (type = TABLE)
        group.add_condition(FilterCondition(
            filter_type=FilterType.ELEMENT_TYPE,
            operator=FilterOperator.EQUALS,
            value=FilterValue(ElementType.TABLE.value, "string")
        ))
        
        # Both elements are not tables -> should match
        assert group.matches(sample_elements[0])
        assert group.matches(sample_elements[1])
    
    def test_group_serialization(self):
        """Test group serialization."""
        group = FilterGroup(logic=FilterLogic.AND)
        group.add_condition(FilterCondition(
            filter_type=FilterType.TEXT_CONTENT,
            operator=FilterOperator.CONTAINS,
            value=FilterValue("test", "string")
        ))
        
        data = group.to_dict()
        
        assert data["logic"] == FilterLogic.AND.value
        assert len(data["conditions"]) == 1
        
        # Test deserialization
        restored = FilterGroup.from_dict(data)
        assert restored.logic == group.logic
        assert len(restored.conditions) == 1
        assert restored.conditions[0].filter_type == FilterType.TEXT_CONTENT


class TestFilterSet:
    """Test FilterSet functionality."""
    
    @pytest.fixture
    def sample_elements(self):
        """Create sample elements for testing."""
        metadata1 = ElementMetadata(confidence=0.95, page_number=1)
        metadata2 = ElementMetadata(confidence=0.75, page_number=2)
        metadata3 = ElementMetadata(confidence=0.85, page_number=1)
        
        elements = [
            Element(
                element_id="elem-1",
                element_type=ElementType.TITLE,
                text="Document Title",
                metadata=metadata1
            ),
            Element(
                element_id="elem-2",
                element_type=ElementType.NARRATIVE_TEXT,
                text="This is narrative text",
                metadata=metadata2
            ),
            Element(
                element_id="elem-3",
                element_type=ElementType.TABLE,
                text="Table data",
                metadata=metadata3
            )
        ]
        
        return elements
    
    def test_filter_set_creation(self):
        """Test creating filter sets."""
        filter_set = FilterSet(
            name="Test Filter",
            description="Test description",
            combination_logic=FilterLogic.AND
        )
        
        assert filter_set.name == "Test Filter"
        assert filter_set.description == "Test description"
        assert filter_set.combination_logic == FilterLogic.AND
        assert len(filter_set.groups) == 0
    
    def test_complex_filter_set(self, sample_elements):
        """Test complex filter set with multiple groups."""
        filter_set = FilterSet(
            name="Complex Filter",
            combination_logic=FilterLogic.OR
        )
        
        # Group 1: High confidence elements
        group1 = FilterGroup()
        group1.add_condition(FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.GREATER_THAN,
            value=FilterValue(0.9, "number")
        ))
        filter_set.add_group(group1)
        
        # Group 2: Elements from page 1
        group2 = FilterGroup()
        group2.add_condition(FilterCondition(
            filter_type=FilterType.PAGE_NUMBER,
            operator=FilterOperator.EQUALS,
            value=FilterValue(1, "number")
        ))
        filter_set.add_group(group2)
        
        # Test matching (OR logic between groups)
        assert filter_set.matches(sample_elements[0])  # High confidence AND page 1
        assert not filter_set.matches(sample_elements[1])  # Low confidence AND page 2
        assert filter_set.matches(sample_elements[2])  # Medium confidence BUT page 1
    
    def test_filter_set_serialization(self):
        """Test filter set serialization."""
        filter_set = FilterSet(
            name="Test Filter",
            description="Test description",
            tags=["test", "filter"]
        )
        
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.TEXT_CONTENT,
            operator=FilterOperator.CONTAINS,
            value=FilterValue("test", "string")
        ))
        filter_set.add_group(group)
        
        data = filter_set.to_dict()
        
        assert data["name"] == "Test Filter"
        assert data["description"] == "Test description"
        assert data["tags"] == ["test", "filter"]
        assert len(data["groups"]) == 1
        
        # Test deserialization
        restored = FilterSet.from_dict(data)
        assert restored.name == filter_set.name
        assert restored.description == filter_set.description
        assert restored.tags == filter_set.tags
        assert len(restored.groups) == 1


class TestFilterManager:
    """Test FilterManager functionality."""
    
    @pytest.fixture
    def filter_manager(self):
        """Create filter manager for testing."""
        return FilterManager()
    
    @pytest.fixture
    def sample_elements(self):
        """Create sample elements for testing."""
        metadata1 = ElementMetadata(confidence=0.95, page_number=1)
        metadata2 = ElementMetadata(confidence=0.75, page_number=2)
        
        elements = [
            Element(
                element_id="elem-1",
                element_type=ElementType.TITLE,
                text="Document Title",
                metadata=metadata1
            ),
            Element(
                element_id="elem-2",
                element_type=ElementType.NARRATIVE_TEXT,
                text="This is narrative text",
                metadata=metadata2
            )
        ]
        
        return elements
    
    def test_filter_manager_creation(self, filter_manager):
        """Test filter manager creation."""
        assert len(filter_manager.filter_sets) == 0
        assert len(filter_manager.presets) > 0  # Should have default presets
        assert filter_manager.active_filter_set is None
    
    def test_create_filter_set(self, filter_manager):
        """Test creating filter sets."""
        filter_set = filter_manager.create_filter_set("Test Filter", "Test description")
        
        assert filter_set.name == "Test Filter"
        assert filter_set.description == "Test description"
        assert filter_set.filter_set_id in filter_manager.filter_sets
    
    def test_filter_elements(self, filter_manager, sample_elements):
        """Test filtering elements."""
        # Create a filter set
        filter_set = filter_manager.create_filter_set("High Confidence", "High confidence elements")
        
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.GREATER_THAN,
            value=FilterValue(0.8, "number")
        ))
        filter_set.add_group(group)
        
        # Filter elements
        filtered = filter_manager.filter_elements(sample_elements, filter_set)
        
        # Should only return high confidence element
        assert len(filtered) == 1
        assert filtered[0].element_id == "elem-1"
    
    def test_active_filter_set(self, filter_manager, sample_elements):
        """Test active filter set functionality."""
        # Create and set active filter
        filter_set = filter_manager.create_filter_set("Active Filter")
        filter_manager.set_active_filter_set(filter_set)
        
        assert filter_manager.get_active_filter_set() == filter_set
        
        # Test filtering with active set
        filtered = filter_manager.filter_elements(sample_elements)
        assert len(filtered) == 2  # Empty filter should return all
    
    def test_search_filter_sets(self, filter_manager):
        """Test searching filter sets."""
        # Create test filter sets
        filter_manager.create_filter_set("Quality Filter", "High quality elements")
        filter_manager.create_filter_set("Page Filter", "First page elements")
        filter_manager.create_filter_set("Text Search", "Text content search")
        
        # Search by name
        results = filter_manager.search_filter_sets("quality")
        assert len(results) == 1
        assert results[0].name == "Quality Filter"
        
        # Search by description
        results = filter_manager.search_filter_sets("first page")
        assert len(results) == 1
        assert results[0].name == "Page Filter"
    
    def test_duplicate_filter_set(self, filter_manager):
        """Test duplicating filter sets."""
        # Create original filter set
        original = filter_manager.create_filter_set("Original Filter", "Original description")
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.TEXT_CONTENT,
            operator=FilterOperator.CONTAINS,
            value=FilterValue("test", "string")
        ))
        original.add_group(group)
        
        # Duplicate it
        duplicate = filter_manager.duplicate_filter_set(original.filter_set_id, "Duplicate Filter")
        
        assert duplicate is not None
        assert duplicate.name == "Duplicate Filter"
        assert duplicate.filter_set_id != original.filter_set_id
        assert len(duplicate.groups) == 1
        assert duplicate.groups[0].conditions[0].value.value == "test"
    
    def test_export_import_filter_set(self, filter_manager):
        """Test exporting and importing filter sets."""
        # Create filter set
        filter_set = filter_manager.create_filter_set("Export Test", "Export description")
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.GREATER_THAN,
            value=FilterValue(0.8, "number")
        ))
        filter_set.add_group(group)
        
        # Export
        json_data = filter_manager.export_filter_set(filter_set.filter_set_id)
        assert json_data is not None
        
        # Import
        imported = filter_manager.import_filter_set(json_data)
        assert imported is not None
        assert imported.name == "Export Test"
        assert imported.description == "Export description"
        assert len(imported.groups) == 1
    
    def test_get_statistics(self, filter_manager):
        """Test getting filter statistics."""
        # Create some filter sets
        filter_manager.create_filter_set("Filter 1")
        filter_manager.create_filter_set("Filter 2")
        
        stats = filter_manager.get_statistics()
        
        assert stats["total_filter_sets"] == 2
        assert stats["total_presets"] > 0
        assert stats["active_filter"] is None
    
    def test_default_presets(self, filter_manager):
        """Test that default presets are created."""
        presets = filter_manager.presets
        
        # Should have default presets
        assert len(presets) > 0
        
        # Check for specific presets
        preset_names = [preset.name for preset in presets.values()]
        assert "High Confidence Elements" in preset_names
        assert "Title Elements Only" in preset_names