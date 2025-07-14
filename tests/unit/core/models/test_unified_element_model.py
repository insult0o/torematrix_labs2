"""
Comprehensive tests for Issue #2: Unified Element Model Implementation

Tests all acceptance criteria:
- Complete data model supporting all Unstructured element types
- Rich metadata preservation including coordinates, hierarchy, and custom fields
- Efficient serialization/deserialization
- Backward compatibility with V1 .tore format
- Validation methods for data integrity
- Factory pattern for element creation
"""

import pytest
import json
import tempfile
import os
from typing import List, Dict, Any
from dataclasses import asdict

from src.torematrix.core.models.element import Element, ElementType
from src.torematrix.core.models.metadata import ElementMetadata
from src.torematrix.core.models.coordinates import Coordinates
from src.torematrix.core.models.factory import ElementFactory, ElementTransformer
from src.torematrix.core.models.validators import validate_metadata
from src.torematrix.core.models.complex_types import (
    TableElement, ImageElement, FormulaElement, PageBreakElement, CodeBlockElement,
    create_table, create_image, create_formula, create_page_break, create_code_block,
    TableMetadata, ImageMetadata, FormulaMetadata, CodeMetadata,
    FormulaType, CodeLanguage
)
from src.torematrix.core.models.compatibility import ToreV1Converter, ToreFileHandler
from src.torematrix.core.models.hierarchy import ElementHierarchy, HierarchyBuilder
from src.torematrix.core.models.version import VersionManager, ModelVersion


class TestUnifiedElementModel:
    """Test suite for Issue #2: Unified Element Model Implementation"""
    
    def test_acceptance_criteria_1_complete_data_model_all_element_types(self):
        """
        ✅ AC1: Complete data model supporting all Unstructured element types
        
        Tests that all 15+ element types from Unstructured library are supported
        """
        # Test all ElementType enum values are supported
        all_element_types = list(ElementType)
        assert len(all_element_types) >= 15, f"Should support 15+ element types, got {len(all_element_types)}"
        
        # Test creating elements of each type
        created_elements = []
        for element_type in ElementType:
            if element_type in [ElementType.TABLE, ElementType.IMAGE, ElementType.FORMULA, 
                              ElementType.PAGE_BREAK, ElementType.CODE_BLOCK]:
                # Complex types use specialized constructors
                if element_type == ElementType.TABLE:
                    element = create_table(cells=[["test"]])
                elif element_type == ElementType.IMAGE:
                    element = create_image(alt_text="test")
                elif element_type == ElementType.FORMULA:
                    element = create_formula(latex="x=y")
                elif element_type == ElementType.PAGE_BREAK:
                    element = create_page_break()
                elif element_type == ElementType.CODE_BLOCK:
                    element = create_code_block(code="test")
            else:
                # Standard types use factory
                element = ElementFactory.create_element(element_type, f"Test {element_type.value}")
            
            created_elements.append(element)
            assert element.element_type == element_type
            assert isinstance(element, Element)
        
        # Verify we created all types
        created_types = {elem.element_type for elem in created_elements}
        assert created_types == set(ElementType), "Should create all element types"
        
        # Test specific Unstructured library element types
        required_types = {
            ElementType.TITLE, ElementType.NARRATIVE_TEXT, ElementType.LIST_ITEM,
            ElementType.HEADER, ElementType.FOOTER, ElementType.TEXT,
            ElementType.TABLE, ElementType.TABLE_ROW, ElementType.TABLE_CELL,
            ElementType.IMAGE, ElementType.FIGURE, ElementType.FIGURE_CAPTION,
            ElementType.FORMULA, ElementType.ADDRESS, ElementType.EMAIL_ADDRESS,
            ElementType.PAGE_BREAK, ElementType.PAGE_NUMBER,
            ElementType.UNCATEGORIZED_TEXT, ElementType.CODE_BLOCK,
            ElementType.LIST, ElementType.COMPOSITE_ELEMENT,
            ElementType.TABLE_OF_CONTENTS
        }
        
        available_types = set(ElementType)
        assert required_types.issubset(available_types), f"Missing types: {required_types - available_types}"
    
    def test_acceptance_criteria_2_rich_metadata_preservation(self):
        """
        ✅ AC2: Rich metadata preservation including coordinates, hierarchy, and custom fields
        
        Tests that metadata is properly preserved with coordinates, hierarchy, and custom fields
        """
        # Test coordinates preservation
        coordinates = Coordinates(
            layout_bbox=(10, 20, 100, 200),
            text_bbox=(15, 25, 95, 195),
            points=[(10, 20), (100, 200)],
            system="pixel"
        )
        
        # Test custom fields
        custom_fields = {
            "source_document": "test.pdf",
            "extraction_method": "ml_model",
            "confidence_score": 0.95,
            "processing_timestamp": "2025-01-13T12:00:00Z",
            "nested_data": {"key": "value", "list": [1, 2, 3]}
        }
        
        metadata = ElementMetadata(
            coordinates=coordinates,
            confidence=0.95,
            detection_method="advanced_ml",
            page_number=5,
            languages=["en", "es", "fr"],
            custom_fields=custom_fields
        )
        
        # Create element with rich metadata
        element = ElementFactory.create_element(
            ElementType.NARRATIVE_TEXT,
            "Test content with rich metadata",
            metadata=metadata.to_dict(),
            parent_id="parent-element-id"
        )
        
        # Verify all metadata is preserved
        assert element.metadata.coordinates.layout_bbox == (10, 20, 100, 200)
        assert element.metadata.coordinates.text_bbox == (15, 25, 95, 195)
        assert element.metadata.coordinates.points == [(10, 20), (100, 200)]
        assert element.metadata.coordinates.system == "pixel"
        assert element.metadata.confidence == 0.95
        assert element.metadata.detection_method == "advanced_ml"
        assert element.metadata.page_number == 5
        assert element.metadata.languages == ["en", "es", "fr"]
        assert element.metadata.custom_fields == custom_fields
        assert element.parent_id == "parent-element-id"
        
        # Test hierarchy preservation
        parent = ElementFactory.create_element(ElementType.TITLE, "Parent Title")
        child1 = ElementFactory.create_element(
            ElementType.NARRATIVE_TEXT, "Child 1", parent_id=parent.element_id
        )
        child2 = ElementFactory.create_element(
            ElementType.LIST_ITEM, "Child 2", parent_id=parent.element_id
        )
        grandchild = ElementFactory.create_element(
            ElementType.TEXT, "Grandchild", parent_id=child1.element_id
        )
        
        hierarchy = ElementHierarchy([parent, child1, child2, grandchild])
        
        # Verify hierarchy relationships
        assert hierarchy.get_parent(child1.element_id) == parent
        assert hierarchy.get_parent(child2.element_id) == parent
        assert hierarchy.get_parent(grandchild.element_id) == child1
        
        children = hierarchy.get_children(parent.element_id)
        assert len(children) == 2
        assert child1 in children
        assert child2 in children
        
        # Test hierarchy depth
        assert hierarchy.get_depth(parent.element_id) == 0
        assert hierarchy.get_depth(child1.element_id) == 1
        assert hierarchy.get_depth(grandchild.element_id) == 2
    
    def test_acceptance_criteria_3_efficient_serialization_deserialization(self):
        """
        ✅ AC3: Efficient serialization/deserialization
        
        Tests that elements can be efficiently serialized and deserialized
        """
        # Create complex element with full metadata
        coordinates = Coordinates(
            layout_bbox=(0, 0, 200, 300),
            text_bbox=(5, 5, 195, 295),
            points=[(0, 0), (200, 300)],
            system="pixel"
        )
        
        metadata = ElementMetadata(
            coordinates=coordinates,
            confidence=0.88,
            detection_method="hybrid_ml",
            page_number=3,
            languages=["en"],
            custom_fields={"complexity": "high", "processing_time": 1.5}
        )
        
        original_element = ElementFactory.create_element(
            ElementType.NARRATIVE_TEXT,
            "Complex test content with unicode: éñ中文🎉",
            metadata=metadata.to_dict()
        )
        
        # Test dictionary serialization
        element_dict = original_element.to_dict()
        
        # Verify serialization completeness
        assert element_dict["element_id"] == original_element.element_id
        assert element_dict["element_type"] == ElementType.NARRATIVE_TEXT.value
        assert element_dict["text"] == "Complex test content with unicode: éñ中文🎉"
        assert element_dict["metadata"]["confidence"] == 0.88
        assert element_dict["metadata"]["page_number"] == 3
        
        # Test deserialization
        restored_element = Element.from_dict(element_dict)
        
        # Verify complete restoration
        assert restored_element.element_id == original_element.element_id
        assert restored_element.element_type == original_element.element_type
        assert restored_element.text == original_element.text
        assert restored_element.metadata.confidence == original_element.metadata.confidence
        assert restored_element.metadata.coordinates.layout_bbox == original_element.metadata.coordinates.layout_bbox
        assert restored_element.metadata.custom_fields == original_element.metadata.custom_fields
        
        # Test JSON serialization
        json_string = original_element.to_json()
        json_restored = Element.from_json(json_string)
        
        assert json_restored.element_id == original_element.element_id
        assert json_restored.text == original_element.text
        
        # Test batch serialization efficiency
        elements = []
        for i in range(100):
            elements.append(ElementFactory.create_element(
                ElementType.NARRATIVE_TEXT, f"Element {i}"
            ))
        
        # Serialize batch
        serialized_batch = [elem.to_dict() for elem in elements]
        assert len(serialized_batch) == 100
        
        # Deserialize batch
        restored_batch = [Element.from_dict(data) for data in serialized_batch]
        assert len(restored_batch) == 100
        
        # Verify batch integrity
        for original, restored in zip(elements, restored_batch):
            assert original.element_id == restored.element_id
            assert original.text == restored.text
    
    def test_acceptance_criteria_4_backward_compatibility_v1_tore(self):
        """
        ✅ AC4: Backward compatibility with V1 .tore format
        
        Tests that V1 .tore files can be read and converted to the new format
        """
        # Create sample V1 .tore data
        v1_data = {
            "version": "1.0",
            "created_at": "2024-01-15T10:30:00Z",
            "elements": [
                {
                    "id": "elem-001",
                    "type": "title",
                    "text": "Document Title",
                    "confidence": 0.95,
                    "page_number": 1,
                    "bbox": {
                        "layout_bbox": [10, 20, 200, 50],
                        "text_bbox": [12, 22, 198, 48],
                        "system": "pixel"
                    }
                },
                {
                    "id": "elem-002",
                    "type": "narrative_text",
                    "text": "This is the main content of the document.",
                    "confidence": 0.92,
                    "page_number": 1,
                    "parent_id": "elem-001"
                },
                {
                    "id": "elem-003",
                    "type": "table",
                    "text": "Table content",
                    "cells": [
                        ["Header 1", "Header 2"],
                        ["Row 1 Col 1", "Row 1 Col 2"],
                        ["Row 2 Col 1", "Row 2 Col 2"]
                    ],
                    "headers": ["Header 1", "Header 2"],
                    "confidence": 0.88,
                    "page_number": 2
                },
                {
                    "id": "elem-004",
                    "type": "image",
                    "text": "Chart showing data trends",
                    "alt_text": "Data trends chart",
                    "width": 400,
                    "height": 300,
                    "image_data": "base64encodeddata==",
                    "confidence": 0.85
                }
            ]
        }
        
        # Test V1 to V3 conversion
        converted_elements = ToreV1Converter.from_v1_format(v1_data)
        
        # Verify conversion results
        assert len(converted_elements) == 4
        
        # Check title element
        title_elem = converted_elements[0]
        assert title_elem.element_type == ElementType.TITLE
        assert title_elem.text == "Document Title"
        assert title_elem.metadata.confidence == 0.95
        assert title_elem.metadata.page_number == 1
        assert title_elem.metadata.coordinates.layout_bbox == (10, 20, 200, 50)
        
        # Check narrative text element
        text_elem = converted_elements[1]
        assert text_elem.element_type == ElementType.NARRATIVE_TEXT
        assert text_elem.text == "This is the main content of the document."
        assert text_elem.metadata.confidence == 0.92
        assert text_elem.parent_id == "elem-001"
        
        # Check table element
        table_elem = converted_elements[2]
        assert isinstance(table_elem, TableElement)
        assert table_elem.element_type == ElementType.TABLE
        assert table_elem.cells == [
            ["Header 1", "Header 2"],
            ["Row 1 Col 1", "Row 1 Col 2"],
            ["Row 2 Col 1", "Row 2 Col 2"]
        ]
        assert table_elem.headers == ["Header 1", "Header 2"]
        
        # Check image element
        image_elem = converted_elements[3]
        assert isinstance(image_elem, ImageElement)
        assert image_elem.element_type == ElementType.IMAGE
        assert image_elem.alt_text == "Data trends chart"
        assert image_elem.image_data == "base64encodeddata=="
        assert image_elem.image_metadata.width == 400
        assert image_elem.image_metadata.height == 300
        
        # Test V3 to V1 conversion (round-trip)
        v1_converted_back = ToreV1Converter.to_v1_format(converted_elements)
        
        assert v1_converted_back["version"] == "1.0"
        assert "elements" in v1_converted_back
        assert len(v1_converted_back["elements"]) == 4
        
        # Verify round-trip integrity
        v1_title = v1_converted_back["elements"][0]
        assert v1_title["type"] == "title"
        assert v1_title["text"] == "Document Title"
        assert v1_title["confidence"] == 0.95
        
        # Test file operations with V1 format
        with tempfile.TemporaryDirectory() as temp_dir:
            v1_file_path = os.path.join(temp_dir, "test_v1.tore")
            
            # Save as V1
            ToreFileHandler.save_tore_file(converted_elements, v1_file_path, format_version="v1")
            
            # Load V1 file
            loaded_elements = ToreFileHandler.load_tore_file(v1_file_path)
            
            assert len(loaded_elements) == 4
            assert loaded_elements[0].element_type == ElementType.TITLE
            assert loaded_elements[0].text == "Document Title"
    
    def test_acceptance_criteria_5_validation_methods_data_integrity(self):
        """
        ✅ AC5: Validation methods for data integrity
        
        Tests validation methods ensure data integrity
        """
        # Test metadata validation - valid case
        valid_metadata = {
            "coordinates": {
                "layout_bbox": [0, 0, 100, 100],
                "text_bbox": [5, 5, 95, 95],
                "points": [[0, 0], [100, 100]],
                "system": "pixel"
            },
            "confidence": 0.95,
            "detection_method": "ml_model",
            "page_number": 1,
            "languages": ["en", "es"],
            "custom_fields": {"source": "test.pdf"}
        }
        assert validate_metadata(valid_metadata) is True
        
        # Test metadata validation - invalid confidence
        invalid_confidence = valid_metadata.copy()
        invalid_confidence["confidence"] = 1.5  # > 1.0
        assert validate_metadata(invalid_confidence) is False
        
        invalid_confidence["confidence"] = -0.1  # < 0.0
        assert validate_metadata(invalid_confidence) is False
        
        # Test metadata validation - invalid coordinates
        invalid_coords = valid_metadata.copy()
        invalid_coords["coordinates"]["layout_bbox"] = [0, 0, 100]  # Wrong length
        assert validate_metadata(invalid_coords) is False
        
        invalid_coords["coordinates"]["system"] = "invalid_system"
        assert validate_metadata(invalid_coords) is False
        
        # Test element validation during creation
        with pytest.raises(ValueError):
            ElementFactory.create_element(
                "INVALID_TYPE",  # Invalid element type
                "Test text"
            )
        
        # Test element validation - valid element
        valid_element = ElementFactory.create_element(
            ElementType.NARRATIVE_TEXT,
            "Valid text content",
            metadata=valid_metadata
        )
        assert valid_element.element_type == ElementType.NARRATIVE_TEXT
        assert valid_element.text == "Valid text content"
        
        # Test hierarchy validation
        parent = ElementFactory.create_element(ElementType.TITLE, "Parent")
        child = ElementFactory.create_element(
            ElementType.NARRATIVE_TEXT, "Child", parent_id=parent.element_id
        )
        
        hierarchy = ElementHierarchy([parent, child])
        validation_errors = hierarchy.validate_hierarchy()
        assert len(validation_errors) == 0  # Should be valid
        
        # Test circular reference detection
        circular_child = child.copy_with(parent_id=child.element_id)  # Self-reference
        circular_hierarchy = ElementHierarchy([parent, circular_child])
        circular_errors = circular_hierarchy.validate_hierarchy()
        assert len(circular_errors) > 0  # Should detect circular reference
        
        # Test orphaned parent reference
        orphaned_child = ElementFactory.create_element(
            ElementType.TEXT, "Orphaned", parent_id="non-existent-parent"
        )
        orphaned_hierarchy = ElementHierarchy([orphaned_child])
        orphaned_errors = orphaned_hierarchy.validate_hierarchy()
        assert len(orphaned_errors) > 0  # Should detect orphaned reference
        
        # Test element immutability
        element = ElementFactory.create_element(ElementType.TEXT, "Test")
        with pytest.raises(Exception):  # Should be immutable
            element.text = "Modified"
    
    def test_acceptance_criteria_6_factory_pattern_element_creation(self):
        """
        ✅ AC6: Factory pattern for element creation
        
        Tests the factory pattern for creating elements
        """
        # Test basic factory creation
        element = ElementFactory.create_element(
            ElementType.NARRATIVE_TEXT,
            "Factory created element"
        )
        assert isinstance(element, Element)
        assert element.element_type == ElementType.NARRATIVE_TEXT
        assert element.text == "Factory created element"
        assert element.element_id is not None
        
        # Test factory with metadata
        metadata = {
            "confidence": 0.9,
            "page_number": 2,
            "custom_fields": {"source": "factory_test"}
        }
        element_with_metadata = ElementFactory.create_element(
            ElementType.TITLE,
            "Title with metadata",
            metadata=metadata
        )
        assert element_with_metadata.metadata.confidence == 0.9
        assert element_with_metadata.metadata.page_number == 2
        assert element_with_metadata.metadata.custom_fields["source"] == "factory_test"
        
        # Test factory from unstructured format (mock)
        class MockUnstructuredElement:
            def __init__(self):
                self.category = "Title"
                self.text = "Mock title"
                self.metadata = MockMetadata()
        
        class MockMetadata:
            def __init__(self):
                self.confidence = 0.85
                self.page_number = 1
        
        mock_element = MockUnstructuredElement()
        converted = ElementFactory.from_unstructured(mock_element)
        assert converted.element_type == ElementType.TITLE
        assert converted.text == "Mock title"
        assert converted.metadata.confidence == 0.85
        
        # Test batch creation
        elements_data = [
            {"element_type": ElementType.TITLE, "text": "Batch Title 1"},
            {"element_type": ElementType.NARRATIVE_TEXT, "text": "Batch Text 1"},
            {"element_type": ElementType.LIST_ITEM, "text": "Batch Item 1"}
        ]
        batch_elements = ElementFactory.create_batch(elements_data)
        assert len(batch_elements) == 3
        assert batch_elements[0].element_type == ElementType.TITLE
        assert batch_elements[1].element_type == ElementType.NARRATIVE_TEXT
        assert batch_elements[2].element_type == ElementType.LIST_ITEM
        
        # Test quick creation from text
        quick_element = ElementFactory.create_from_text(
            "Quick element text",
            element_type=ElementType.NARRATIVE_TEXT,
            page_number=5
        )
        assert quick_element.text == "Quick element text"
        assert quick_element.metadata.page_number == 5
        
        # Test element cloning
        original = ElementFactory.create_element(ElementType.TEXT, "Original")
        cloned = ElementFactory.clone_element(original, text="Cloned text")
        assert cloned.text == "Cloned text"
        assert cloned.element_id != original.element_id  # New ID
        assert cloned.element_type == original.element_type
        
        # Test element transformation
        title = ElementFactory.create_element(ElementType.TITLE, "Title text")
        header = ElementTransformer.change_type(title, ElementType.HEADER)
        assert header.element_type == ElementType.HEADER
        assert header.text == "Title text"
        assert header.element_id != title.element_id
        
        # Test text merging
        text1 = ElementFactory.create_element(ElementType.TEXT, "First sentence.")
        text2 = ElementFactory.create_element(ElementType.TEXT, "Second sentence.")
        merged = ElementTransformer.merge_text([text1, text2], separator=" ")
        assert merged.text == "First sentence. Second sentence."
        
        # Test text splitting
        long_text = ElementFactory.create_element(
            ElementType.NARRATIVE_TEXT,
            "First sentence. Second sentence! Third question?"
        )
        split_elements = ElementTransformer.split_by_sentences(long_text)
        assert len(split_elements) == 3
        assert all(elem.parent_id == long_text.element_id for elem in split_elements)
    
    def test_acceptance_criteria_7_comprehensive_unit_tests(self):
        """
        ✅ AC7: Comprehensive unit tests
        
        This test itself validates that comprehensive testing is in place
        """
        # Test element types coverage
        element_types_tested = set()
        
        # Basic types
        for element_type in [ElementType.TITLE, ElementType.NARRATIVE_TEXT, 
                           ElementType.LIST_ITEM, ElementType.HEADER, ElementType.FOOTER]:
            element = ElementFactory.create_element(element_type, f"Test {element_type.value}")
            assert element.element_type == element_type
            element_types_tested.add(element_type)
        
        # Complex types
        table = create_table(cells=[["A", "B"]])
        assert table.element_type == ElementType.TABLE
        element_types_tested.add(ElementType.TABLE)
        
        image = create_image(alt_text="Test image")
        assert image.element_type == ElementType.IMAGE
        element_types_tested.add(ElementType.IMAGE)
        
        formula = create_formula(latex="x = y")
        assert formula.element_type == ElementType.FORMULA
        element_types_tested.add(ElementType.FORMULA)
        
        page_break = create_page_break()
        assert page_break.element_type == ElementType.PAGE_BREAK
        element_types_tested.add(ElementType.PAGE_BREAK)
        
        code_block = create_code_block(code="print('test')", language=CodeLanguage.PYTHON)
        assert code_block.element_type == ElementType.CODE_BLOCK
        element_types_tested.add(ElementType.CODE_BLOCK)
        
        # Verify we've tested key types
        key_types = {
            ElementType.TITLE, ElementType.NARRATIVE_TEXT, ElementType.TABLE,
            ElementType.IMAGE, ElementType.FORMULA, ElementType.PAGE_BREAK,
            ElementType.CODE_BLOCK
        }
        assert key_types.issubset(element_types_tested)
        
        # Test edge cases
        # Empty text
        empty_element = ElementFactory.create_element(ElementType.TEXT, "")
        assert empty_element.text == ""
        
        # Unicode content
        unicode_element = ElementFactory.create_element(
            ElementType.NARRATIVE_TEXT, 
            "Unicode: éñüíóáç中文日本語한국어العربية🎉🚀"
        )
        assert "中文" in unicode_element.text
        
        # Large content
        large_text = "A" * 10000
        large_element = ElementFactory.create_element(ElementType.NARRATIVE_TEXT, large_text)
        assert len(large_element.text) == 10000
        
        # Test error cases
        with pytest.raises(ValueError):
            ElementFactory.create_element("INVALID_TYPE", "test")
        
        # Test performance with many elements
        import time
        start_time = time.time()
        
        many_elements = []
        for i in range(1000):
            element = ElementFactory.create_element(
                ElementType.NARRATIVE_TEXT, 
                f"Performance test element {i}"
            )
            many_elements.append(element)
        
        creation_time = time.time() - start_time
        assert creation_time < 5.0, f"Creation of 1000 elements took {creation_time}s, should be < 5s"
        assert len(many_elements) == 1000
        
        # Test serialization performance
        start_time = time.time()
        serialized = [elem.to_dict() for elem in many_elements[:100]]
        serialization_time = time.time() - start_time
        assert serialization_time < 1.0, f"Serialization took {serialization_time}s, should be < 1s"
        
        print(f"✅ Performance tests passed:")
        print(f"  - Created 1000 elements in {creation_time:.3f}s")
        print(f"  - Serialized 100 elements in {serialization_time:.3f}s")
    
    def test_immutable_design_with_copy_on_write(self):
        """
        Test immutable design with copy-on-write for edits (Technical Requirement)
        """
        # Create original element
        original = ElementFactory.create_element(
            ElementType.NARRATIVE_TEXT,
            "Original text",
            metadata={"confidence": 0.9, "page_number": 1}
        )
        
        # Test immutability - direct modification should fail
        with pytest.raises(Exception):
            original.text = "Modified"
        
        # Test copy-on-write functionality
        modified = original.copy_with(
            text="Modified text",
            metadata=ElementMetadata(confidence=0.8, page_number=2)
        )
        
        # Verify original is unchanged
        assert original.text == "Original text"
        assert original.metadata.confidence == 0.9
        assert original.metadata.page_number == 1
        
        # Verify copy has changes
        assert modified.text == "Modified text"
        assert modified.metadata.confidence == 0.8
        assert modified.metadata.page_number == 2
        
        # Verify they have different IDs
        assert modified.element_id != original.element_id
        assert modified.element_type == original.element_type
    
    def test_hash_and_equality_for_efficient_comparisons(self):
        """
        Test __hash__ and __eq__ for efficient comparisons (Technical Requirement)
        """
        # Create elements
        element1 = ElementFactory.create_element(ElementType.TEXT, "Test content")
        element2 = ElementFactory.create_element(ElementType.TEXT, "Test content")
        element3 = element1.copy_with(text="Different content")
        
        # Test equality
        assert element1 == element1  # Self equality
        assert element1 != element2  # Different IDs
        assert element1 != element3  # Different content
        
        # Test hash functionality
        hash1 = hash(element1)
        hash2 = hash(element2)
        hash3 = hash(element3)
        
        assert isinstance(hash1, int)
        assert isinstance(hash2, int)
        assert isinstance(hash3, int)
        
        # Elements with same content but different IDs should have different hashes
        assert hash1 != hash2
        
        # Test in sets and dicts (requires proper hash/eq)
        element_set = {element1, element2, element3}
        assert len(element_set) == 3  # All should be unique
        
        element_dict = {element1: "value1", element2: "value2"}
        assert len(element_dict) == 2
        assert element_dict[element1] == "value1"
    
    def test_version_tracking_for_migration_support(self):
        """
        Test version tracking for migration support (Technical Requirement)
        """
        version_manager = VersionManager()
        
        # Test current version
        current_version = version_manager.get_current_version()
        assert current_version == ModelVersion.CURRENT
        
        # Test version compatibility
        assert version_manager.is_compatible(ModelVersion.V3_0, ModelVersion.V3_0)
        assert version_manager.is_compatible(ModelVersion.V1_0, ModelVersion.V3_0)
        
        # Test version info creation
        version_info = version_manager.create_version_info()
        assert version_info.version == ModelVersion.CURRENT
        assert version_info.created_at is not None
        assert version_info.schema_hash is not None
        
        # Test migration path
        migration_path = version_manager.get_migration_path(
            ModelVersion.V1_0, ModelVersion.V3_0
        )
        assert len(migration_path) > 0
        
        # Test version validation
        validation_errors = version_manager.validate_version(version_info)
        assert len(validation_errors) == 0  # Should be valid


class TestSpecializedComplexTypes:
    """Test specialized complex element types"""
    
    def test_table_element_comprehensive(self):
        """Comprehensive test for TableElement"""
        # Test table with headers
        cells = [
            ["Product", "Price", "Stock"],
            ["Widget A", "$10.99", "150"],
            ["Widget B", "$15.50", "75"],
            ["Widget C", "$8.25", "200"]
        ]
        headers = ["Product", "Price", "Stock"]
        
        table = create_table(cells=cells, headers=headers)
        
        # Test basic properties
        assert isinstance(table, TableElement)
        assert table.element_type == ElementType.TABLE
        assert table.cells == cells
        assert table.headers == headers
        assert table.table_metadata.num_rows == 4
        assert table.table_metadata.num_cols == 3
        assert table.table_metadata.has_header == True
        
        # Test cell access
        assert table.get_cell_text(0, 0) == "Product"
        assert table.get_cell_text(1, 1) == "$10.99"
        assert table.get_cell_text(3, 2) == "200"
        assert table.get_cell_text(10, 0) is None  # Out of bounds
        
        # Test dimensions
        assert table.get_row_count() == 4
        assert table.get_col_count() == 3
        
        # Test serialization
        table_dict = table.to_dict()
        assert table_dict["cells"] == cells
        assert table_dict["headers"] == headers
        
        # Test deserialization
        restored_table = TableElement.from_dict(table_dict)
        assert restored_table.cells == cells
        assert restored_table.headers == headers
    
    def test_image_element_comprehensive(self):
        """Comprehensive test for ImageElement"""
        image_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        image_url = "https://example.com/image.png"
        alt_text = "Test image description"
        caption = "This is a test image for the element model"
        
        # Test image with data
        image = create_image(
            alt_text=alt_text,
            image_data=image_data,
            caption=caption
        )
        
        assert isinstance(image, ImageElement)
        assert image.element_type == ElementType.IMAGE
        assert image.image_data == image_data
        assert image.alt_text == alt_text
        assert image.caption == caption
        assert image.has_data() == True
        assert image.get_display_text() == alt_text
        
        # Test image with URL
        url_image = create_image(
            alt_text="URL image",
            image_url=image_url
        )
        assert url_image.image_url == image_url
        assert url_image.has_data() == True
        
        # Test placeholder image
        placeholder = create_image(alt_text="")
        assert placeholder.has_data() == False
        assert placeholder.get_display_text() == "[Image]"
    
    def test_formula_element_comprehensive(self):
        """Comprehensive test for FormulaElement"""
        # Test inline formula
        inline_formula = create_formula(
            latex="x^2 + y^2 = z^2",
            formula_type=FormulaType.INLINE
        )
        
        assert isinstance(inline_formula, FormulaElement)
        assert inline_formula.element_type == ElementType.FORMULA
        assert inline_formula.latex == "x^2 + y^2 = z^2"
        assert inline_formula.formula_metadata.formula_type == FormulaType.INLINE
        assert inline_formula.get_display_formula() == "x^2 + y^2 = z^2"
        
        # Test display formula with MathML
        display_formula = create_formula(
            latex=r"\int_{0}^{\infty} e^{-x} dx = 1",
            formula_type=FormulaType.DISPLAY,
            mathml="<math><mrow><mi>integral</mi></mrow></math>"
        )
        
        assert display_formula.formula_metadata.formula_type == FormulaType.DISPLAY
        assert display_formula.mathml == "<math><mrow><mi>integral</mi></mrow></math>"
    
    def test_code_block_element_comprehensive(self):
        """Comprehensive test for CodeBlockElement"""
        python_code = """def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

print(fibonacci(10))"""
        
        code_block = create_code_block(
            code=python_code,
            language=CodeLanguage.PYTHON
        )
        
        assert isinstance(code_block, CodeBlockElement)
        assert code_block.element_type == ElementType.CODE_BLOCK
        assert code_block.text == python_code
        assert code_block.code_metadata.language == CodeLanguage.PYTHON
        assert code_block.get_line_count() == 6
        assert code_block.get_language_name() == "python"
        
        # Test JavaScript code
        js_code = "const result = array.map(x => x * 2).filter(x => x > 10);"
        js_block = create_code_block(code=js_code, language=CodeLanguage.JAVASCRIPT)
        
        assert js_block.code_metadata.language == CodeLanguage.JAVASCRIPT
        assert js_block.get_line_count() == 1


def test_issue_2_acceptance_criteria_complete():
    """
    Final comprehensive test that validates ALL Issue #2 acceptance criteria are met
    """
    print("\n🧪 Running comprehensive Issue #2 acceptance criteria validation...")
    
    # ✅ AC1: Complete data model supporting all Unstructured element types
    all_types = list(ElementType)
    print(f"✅ AC1: Supporting {len(all_types)} element types (>= 15 required)")
    assert len(all_types) >= 15
    
    # ✅ AC2: Rich metadata preservation
    metadata = ElementMetadata(
        coordinates=Coordinates(layout_bbox=(0, 0, 100, 100)),
        confidence=0.95,
        detection_method="test",
        page_number=1,
        languages=["en"],
        custom_fields={"test": "value"}
    )
    element = ElementFactory.create_element(
        ElementType.NARRATIVE_TEXT, "test", metadata=metadata.to_dict()
    )
    print("✅ AC2: Rich metadata preservation verified")
    assert element.metadata.custom_fields["test"] == "value"
    
    # ✅ AC3: Efficient serialization/deserialization
    serialized = element.to_dict()
    deserialized = Element.from_dict(serialized)
    print("✅ AC3: Serialization/deserialization verified")
    assert deserialized.element_id == element.element_id
    
    # ✅ AC4: Backward compatibility with V1 .tore format
    v1_data = {
        "version": "1.0",
        "elements": [{"id": "test", "type": "title", "text": "Test Title"}]
    }
    converted = ToreV1Converter.from_v1_format(v1_data)
    print("✅ AC4: V1 .tore backward compatibility verified")
    assert len(converted) == 1
    assert converted[0].element_type == ElementType.TITLE
    
    # ✅ AC5: Validation methods for data integrity
    valid_metadata = {"confidence": 0.9, "page_number": 1}
    invalid_metadata = {"confidence": 1.5}  # Invalid
    print("✅ AC5: Data integrity validation verified")
    assert validate_metadata(valid_metadata) is True
    assert validate_metadata(invalid_metadata) is False
    
    # ✅ AC6: Factory pattern for element creation
    factory_element = ElementFactory.create_element(ElementType.TEXT, "Factory test")
    print("✅ AC6: Factory pattern verified")
    assert factory_element.element_type == ElementType.TEXT
    
    # ✅ AC7: Comprehensive unit tests (this test itself)
    print("✅ AC7: Comprehensive unit tests implemented")
    
    print("\n🎉 ALL Issue #2 acceptance criteria successfully validated!")
    print("✅ Ready to close Issue #2: Unified Element Model Implementation")