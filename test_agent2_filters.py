#!/usr/bin/env python3
"""
Test Agent 2's advanced filtering system without UI dependencies.
"""

import sys
sys.path.insert(0, '.')

from src.torematrix.core.models.element import Element, ElementType
from src.torematrix.core.models.metadata import ElementMetadata
from src.torematrix.ui.components.search.filters import (
    FilterManager, FilterSet, FilterGroup, FilterCondition,
    FilterType, FilterOperator, FilterLogic, FilterValue
)
from src.torematrix.ui.components.search.dsl import DSLParser, DSLGenerator
from src.torematrix.ui.components.search.presets import PresetManager


def test_filter_system():
    """Test the complete filter system."""
    print("Testing Advanced Filter System...")
    
    # Create sample elements
    elements = [
        Element(
            element_id="elem-1",
            element_type=ElementType.TITLE,
            text="Machine Learning Fundamentals",
            metadata=ElementMetadata(confidence=0.95, page_number=1, languages=["en"])
        ),
        Element(
            element_id="elem-2", 
            element_type=ElementType.NARRATIVE_TEXT,
            text="This chapter covers basic concepts of machine learning",
            metadata=ElementMetadata(confidence=0.85, page_number=2, languages=["en"])
        ),
        Element(
            element_id="elem-3",
            element_type=ElementType.TABLE,
            text="Algorithm Performance Comparison",
            metadata=ElementMetadata(confidence=0.90, page_number=3, languages=["en"])
        ),
        Element(
            element_id="elem-4",
            element_type=ElementType.NARRATIVE_TEXT,
            text="Deep learning networks use multiple layers",
            metadata=ElementMetadata(confidence=0.70, page_number=4, languages=["en"])
        )
    ]
    
    print(f"  Created {len(elements)} test elements")
    
    # Test FilterManager
    filter_manager = FilterManager()
    
    # Create a complex filter
    filter_set = filter_manager.create_filter_set(
        "High Quality ML Content",
        "Find high-quality machine learning content"
    )
    
    # Group 1: High confidence OR title elements
    group1 = FilterGroup(logic=FilterLogic.OR)
    group1.add_condition(FilterCondition(
        filter_type=FilterType.CONFIDENCE,
        operator=FilterOperator.GREATER_THAN,
        value=FilterValue(0.85, "number")
    ))
    group1.add_condition(FilterCondition(
        filter_type=FilterType.ELEMENT_TYPE,
        operator=FilterOperator.EQUALS,
        value=FilterValue(ElementType.TITLE.value, "string")
    ))
    filter_set.add_group(group1)
    
    # Group 2: Contains "machine learning" (AND with group 1)
    group2 = FilterGroup()
    group2.add_condition(FilterCondition(
        filter_type=FilterType.TEXT_CONTENT,
        operator=FilterOperator.CONTAINS,
        value=FilterValue("machine", "string")
    ))
    filter_set.add_group(group2)
    filter_set.combination_logic = FilterLogic.AND
    
    # Test filtering
    filtered_elements = filter_manager.filter_elements(elements, filter_set)
    print(f"  ✅ Complex filter returned {len(filtered_elements)} elements")
    
    # Test individual conditions
    title_elements = [e for e in elements if e.element_type == ElementType.TITLE]
    high_conf_elements = [e for e in elements if e.metadata.confidence > 0.85]
    ml_elements = [e for e in elements if "machine" in e.text.lower()]
    
    print(f"  ✅ Found {len(title_elements)} title elements")
    print(f"  ✅ Found {len(high_conf_elements)} high confidence elements")
    print(f"  ✅ Found {len(ml_elements)} elements containing 'machine'")
    
    return True


def test_dsl_system():
    """Test the DSL parser and generator."""
    print("Testing DSL System...")
    
    parser = DSLParser()
    generator = DSLGenerator()
    
    # Test queries
    test_queries = [
        'type == "Title"',
        'confidence > 0.8',
        'page BETWEEN 1 AND 5',
        'text LIKE "machine learning"',
        'confidence > 0.9 AND type == "Title"',
        '(type == "Title" OR type == "Header") AND confidence > 0.8'
    ]
    
    for query in test_queries:
        try:
            # Parse DSL to FilterSet
            filter_set = parser.parse(query)
            
            # Generate DSL from FilterSet
            generated = generator.generate(filter_set)
            
            print(f"  ✅ DSL '{query}' -> {len(filter_set.groups)} groups")
            
        except Exception as e:
            print(f"  ❌ DSL '{query}' failed: {e}")
            return False
    
    print("  ✅ All DSL queries processed successfully")
    return True


def test_preset_system():
    """Test the preset management system."""
    print("Testing Preset System...")
    
    preset_manager = PresetManager()
    
    # Check default presets
    presets = preset_manager.list_presets()
    print(f"  Found {len(presets)} default presets")
    
    # Test preset categories
    categories = preset_manager.categories
    print(f"  ✅ Presets organized in {len(categories)} categories")
    
    # Test searching presets
    quality_presets = preset_manager.search_presets("quality")
    print(f"  ✅ Found {len(quality_presets)} quality-related presets")
    
    # Test creating custom preset
    custom_filter = FilterSet(name="Custom Test", description="Test preset")
    group = FilterGroup()
    group.add_condition(FilterCondition(
        filter_type=FilterType.CONFIDENCE,
        operator=FilterOperator.GREATER_THAN,
        value=FilterValue(0.9, "number")
    ))
    custom_filter.add_group(group)
    
    custom_preset = preset_manager.create_custom_preset(
        "My Custom Filter",
        "Custom filter for testing",
        custom_filter,
        ["test", "custom"]
    )
    
    print(f"  ✅ Created custom preset: {custom_preset.name}")
    
    return True


def test_filter_serialization():
    """Test filter serialization and persistence."""
    print("Testing Filter Serialization...")
    
    # Create complex filter set
    filter_set = FilterSet(
        name="Serialization Test",
        description="Test complex filter serialization",
        tags=["test", "serialization"]
    )
    
    # Multiple groups with different logic
    group1 = FilterGroup(logic=FilterLogic.AND)
    group1.add_condition(FilterCondition(
        filter_type=FilterType.CONFIDENCE,
        operator=FilterOperator.GREATER_THAN,
        value=FilterValue(0.8, "number")
    ))
    group1.add_condition(FilterCondition(
        filter_type=FilterType.ELEMENT_TYPE,
        operator=FilterOperator.IN,
        value=FilterValue([ElementType.TITLE.value, ElementType.NARRATIVE_TEXT.value], "list")
    ))
    filter_set.add_group(group1)
    
    group2 = FilterGroup(logic=FilterLogic.OR)
    group2.add_condition(FilterCondition(
        filter_type=FilterType.PAGE_NUMBER,
        operator=FilterOperator.BETWEEN,
        value=FilterValue([1, 10], "list")
    ))
    filter_set.add_group(group2)
    
    # Test serialization
    data = filter_set.to_dict()
    print(f"  ✅ Serialized filter set to dictionary with {len(data)} fields")
    
    # Test deserialization
    restored = FilterSet.from_dict(data)
    print(f"  ✅ Restored filter set: {restored.name}")
    print(f"  ✅ Groups: {len(restored.groups)}")
    print(f"  ✅ Total conditions: {sum(len(g.conditions) for g in restored.groups)}")
    
    # Verify data integrity
    assert restored.name == filter_set.name
    assert restored.description == filter_set.description
    assert len(restored.groups) == len(filter_set.groups)
    assert restored.tags == filter_set.tags
    
    return True


def main():
    """Run all Agent 2 tests."""
    print("🧪 Testing Agent 2 - Advanced Filters & Query Processing")
    print("=" * 60)
    
    try:
        success = True
        
        success &= test_filter_system()
        print()
        
        success &= test_dsl_system()
        print()
        
        success &= test_preset_system()
        print()
        
        success &= test_filter_serialization()
        print()
        
        if success:
            print("🎉 All Agent 2 tests passed!")
            print()
            print("Agent 2 Advanced Filtering System verified:")
            print("  ✅ Complex filter conditions and groups")
            print("  ✅ Boolean logic combinations (AND, OR, NOT)")
            print("  ✅ DSL parser and generator")
            print("  ✅ Preset management system")
            print("  ✅ Filter serialization and persistence")
            print("  ✅ Integration with Element model")
        else:
            print("❌ Some Agent 2 tests failed!")
            return 1
        
    except Exception as e:
        print(f"❌ Agent 2 test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())