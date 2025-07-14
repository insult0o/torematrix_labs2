"""
Integration tests for the unified element model.

Tests the complete element model including all types, factory integration,
hierarchy management, V1 compatibility, and version tracking.
"""

import pytest
import json
import tempfile
import os
from typing import List

from src.torematrix.core.models.element import Element, ElementType
from src.torematrix.core.models.metadata import ElementMetadata
from src.torematrix.core.models.factory import ElementFactory, ElementTransformer
from src.torematrix.core.models.complex_types import (
    TableElement, ImageElement, FormulaElement, PageBreakElement, CodeBlockElement,
    FormulaType, CodeLanguage, create_table, create_image, create_formula,
    create_page_break, create_code_block
)
from src.torematrix.core.models.hierarchy import (
    ElementHierarchy, HierarchyOperations, HierarchyBuilder
)
from src.torematrix.core.models.compatibility import (
    ToreV1Converter, ToreFileHandler
)
from src.torematrix.core.models.version import (
    VersionManager, MigrationEngine, VersionedElementCollection,
    ModelVersion, VersionInfo
)


class TestUnifiedElementModel:
    """Test the complete unified element model"""
    
    def test_all_element_types_creation(self):
        """Test creating all supported element types"""
        # Basic types via factory
        title = ElementFactory.create_element(ElementType.TITLE, "Main Title")
        narrative = ElementFactory.create_element(ElementType.NARRATIVE_TEXT, "Some text")
        list_item = ElementFactory.create_element(ElementType.LIST_ITEM, "List item")
        
        # Complex types
        table = create_table(cells=[["A", "B"], ["C", "D"]])
        image = create_image(alt_text="Test image")
        formula = create_formula(latex="x^2 + y^2 = z^2")
        page_break = create_page_break()
        code_block = create_code_block(code="print('hello')", language=CodeLanguage.PYTHON)
        
        elements = [title, narrative, list_item, table, image, formula, page_break, code_block]
        
        # Verify all elements are valid
        for element in elements:
            assert isinstance(element, Element)
            assert element.element_id
            assert element.element_type in ElementType
            assert hasattr(element, 'text')
        
        # Verify type diversity
        types = {elem.element_type for elem in elements}
        assert len(types) == len(elements)  # All different types
    
    def test_element_factory_integration(self):
        """Test element factory with all types"""
        # Test batch creation
        elements_data = [
            {"element_type": ElementType.TITLE, "text": "Title 1"},
            {"element_type": ElementType.NARRATIVE_TEXT, "text": "Text 1"},
            {"element_type": ElementType.TABLE, "text": "Table 1"},
        ]
        
        elements = ElementFactory.create_batch(elements_data)
        assert len(elements) == 3
        assert elements[0].element_type == ElementType.TITLE
        assert elements[1].element_type == ElementType.NARRATIVE_TEXT
        assert elements[2].element_type == ElementType.TABLE
    
    def test_element_transformation(self):
        """Test element transformation operations"""
        # Create elements
        title = ElementFactory.create_element(ElementType.TITLE, "Original Title")
        text1 = ElementFactory.create_element(ElementType.NARRATIVE_TEXT, "First sentence.")
        text2 = ElementFactory.create_element(ElementType.NARRATIVE_TEXT, "Second sentence.")
        
        # Test type change
        new_header = ElementTransformer.change_type(title, ElementType.HEADER)
        assert new_header.element_type == ElementType.HEADER
        assert new_header.text == title.text
        assert new_header.element_id != title.element_id  # New ID generated
        
        # Test merge
        merged = ElementTransformer.merge_text([text1, text2], separator=" ")
        assert merged.text == "First sentence. Second sentence."
        assert merged.element_type == ElementType.NARRATIVE_TEXT
        
        # Test split
        long_text = ElementFactory.create_element(
            ElementType.NARRATIVE_TEXT, 
            "First sentence. Second sentence! Third question?"
        )
        split_elements = ElementTransformer.split_by_sentences(long_text)
        assert len(split_elements) == 3
        assert all(elem.parent_id == long_text.element_id for elem in split_elements)


class TestElementHierarchy:
    """Test element hierarchy management"""
    
    def test_hierarchy_creation_and_navigation(self):
        """Test creating and navigating element hierarchies"""
        # Create elements with hierarchy
        doc = ElementFactory.create_element(ElementType.NARRATIVE_TEXT, "Document")
        chapter1 = ElementFactory.create_element(
            ElementType.TITLE, "Chapter 1", parent_id=doc.element_id
        )
        section1 = ElementFactory.create_element(
            ElementType.HEADER, "Section 1.1", parent_id=chapter1.element_id
        )
        paragraph1 = ElementFactory.create_element(
            ElementType.NARRATIVE_TEXT, "Paragraph text", parent_id=section1.element_id
        )
        
        # Create hierarchy
        elements = [doc, chapter1, section1, paragraph1]
        hierarchy = ElementHierarchy(elements)
        
        # Test navigation
        assert hierarchy.get_parent(chapter1.element_id) == doc
        assert hierarchy.get_parent(section1.element_id) == chapter1
        assert hierarchy.get_parent(paragraph1.element_id) == section1
        
        children = hierarchy.get_children(doc.element_id)
        assert len(children) == 1
        assert children[0] == chapter1
        
        descendants = hierarchy.get_descendants(doc.element_id)
        assert len(descendants) == 3
        assert chapter1 in descendants
        assert section1 in descendants
        assert paragraph1 in descendants
        
        # Test depth
        assert hierarchy.get_depth(doc.element_id) == 0
        assert hierarchy.get_depth(chapter1.element_id) == 1
        assert hierarchy.get_depth(section1.element_id) == 2
        assert hierarchy.get_depth(paragraph1.element_id) == 3
    
    def test_hierarchy_operations(self):
        """Test hierarchy utility operations"""
        # Create mixed hierarchy
        elements = []
        
        # Root elements
        doc1 = ElementFactory.create_element(ElementType.TITLE, "Document 1")
        doc2 = ElementFactory.create_element(ElementType.TITLE, "Document 2")
        elements.extend([doc1, doc2])
        
        # Children
        for i, parent in enumerate([doc1, doc2]):
            for j in range(2):
                child = ElementFactory.create_element(
                    ElementType.NARRATIVE_TEXT, 
                    f"Text {i+1}.{j+1}",
                    parent_id=parent.element_id
                )
                elements.append(child)
        
        hierarchy = ElementHierarchy(elements)
        
        # Test flattening
        flattened = HierarchyOperations.flatten_hierarchy(hierarchy)
        assert len(flattened) == 6  # 2 docs + 4 text elements
        
        # Test grouping by type
        groups = HierarchyOperations.group_by_type(hierarchy)
        assert len(groups[ElementType.TITLE]) == 2
        assert len(groups[ElementType.NARRATIVE_TEXT]) == 4
        
        # Test grouping by depth
        depth_groups = HierarchyOperations.group_by_depth(hierarchy)
        assert len(depth_groups[0]) == 2  # Root elements
        assert len(depth_groups[1]) == 4  # Child elements
    
    def test_hierarchy_builder(self):
        """Test hierarchy builder pattern"""
        builder = HierarchyBuilder()
        
        # Build hierarchy using builder
        root = ElementFactory.create_element(ElementType.TITLE, "Root")
        child1 = ElementFactory.create_element(ElementType.NARRATIVE_TEXT, "Child 1")
        child2 = ElementFactory.create_element(ElementType.NARRATIVE_TEXT, "Child 2")
        
        hierarchy = (builder
                    .add_element(root)
                    .add_child(root, child1)
                    .add_child(root, child2)
                    .build())
        
        # Verify structure
        children = hierarchy.get_children(root.element_id)
        assert len(children) == 2
        assert child1.element_id in [c.element_id for c in children]
        assert child2.element_id in [c.element_id for c in children]


class TestV1Compatibility:
    """Test V1 .tore format compatibility"""
    
    def test_v1_to_v3_conversion(self):
        """Test converting V1 format to V3"""
        # Sample V1 data
        v1_data = {
            "version": "1.0",
            "elements": [
                {
                    "id": "elem1",
                    "type": "title",
                    "text": "Sample Title",
                    "confidence": 0.95,
                    "page_number": 1
                },
                {
                    "id": "elem2", 
                    "type": "table",
                    "text": "Table data",
                    "cells": [["A", "B"], ["C", "D"]],
                    "headers": ["Col1", "Col2"],
                    "confidence": 0.88
                },
                {
                    "id": "elem3",
                    "type": "image",
                    "text": "Image description",
                    "alt_text": "Sample image",
                    "width": 800,
                    "height": 600
                }
            ]
        }
        
        # Convert to V3
        elements = ToreV1Converter.from_v1_format(v1_data)
        
        assert len(elements) == 3
        
        # Check title element
        title_elem = elements[0]
        assert title_elem.element_type == ElementType.TITLE
        assert title_elem.text == "Sample Title"
        assert title_elem.metadata.confidence == 0.95
        assert title_elem.metadata.page_number == 1
        
        # Check table element
        table_elem = elements[1]
        assert isinstance(table_elem, TableElement)
        assert table_elem.cells == [["A", "B"], ["C", "D"]]
        assert table_elem.headers == ["Col1", "Col2"]
        
        # Check image element
        image_elem = elements[2]
        assert isinstance(image_elem, ImageElement)
        assert image_elem.alt_text == "Sample image"
        assert image_elem.image_metadata.width == 800
    
    def test_v3_to_v1_conversion(self):
        """Test converting V3 format to V1"""
        # Create V3 elements
        elements = [
            ElementFactory.create_element(
                ElementType.TITLE, "Test Title",
                metadata={"confidence": 0.9, "page_number": 1}
            ),
            create_table(
                cells=[["Name", "Age"], ["Alice", "30"]],
                headers=["Name", "Age"]
            ),
            create_image(alt_text="Test image", image_data="base64data")
        ]
        
        # Convert to V1
        v1_data = ToreV1Converter.to_v1_format(elements)
        
        assert "version" in v1_data
        assert "elements" in v1_data
        assert len(v1_data["elements"]) == 3
        
        # Check structure
        v1_elements = v1_data["elements"]
        
        # Title
        assert v1_elements[0]["type"] == "title"
        assert v1_elements[0]["text"] == "Test Title"
        assert v1_elements[0]["confidence"] == 0.9
        
        # Table
        assert v1_elements[1]["type"] == "table"
        assert v1_elements[1]["cells"] == [["Name", "Age"], ["Alice", "30"]]
        assert v1_elements[1]["headers"] == ["Name", "Age"]
        
        # Image
        assert v1_elements[2]["type"] == "image"
        assert v1_elements[2]["alt_text"] == "Test image"
        assert v1_elements[2]["image_data"] == "base64data"
    
    def test_tore_file_handling(self):
        """Test .tore file loading and saving"""
        # Create test elements
        elements = [
            ElementFactory.create_element(ElementType.TITLE, "Test Document"),
            create_table(cells=[["A", "B"]], headers=["Col1", "Col2"]),
            create_formula(latex="E = mc^2")
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test V3 format save/load
            v3_path = os.path.join(temp_dir, "test_v3.tore")
            ToreFileHandler.save_tore_file(elements, v3_path, format_version="v3")
            
            loaded_elements = ToreFileHandler.load_tore_file(v3_path)
            assert len(loaded_elements) == 3
            assert loaded_elements[0].element_type == ElementType.TITLE
            
            # Test V1 format save/load
            v1_path = os.path.join(temp_dir, "test_v1.tore")
            ToreFileHandler.save_tore_file(elements, v1_path, format_version="v1")
            
            loaded_v1_elements = ToreFileHandler.load_tore_file(v1_path)
            assert len(loaded_v1_elements) == 3


class TestVersionTracking:
    """Test version tracking and migration"""
    
    def test_version_manager(self):
        """Test version management functionality"""
        version_manager = VersionManager()
        
        # Test current version
        current = version_manager.get_current_version()
        assert current == ModelVersion.CURRENT
        
        # Test compatibility
        assert version_manager.is_compatible(ModelVersion.V3_0, ModelVersion.V3_0)
        assert version_manager.is_compatible(ModelVersion.V1_0, ModelVersion.V3_0)
        
        # Test version info creation
        version_info = version_manager.create_version_info()
        assert version_info.version == ModelVersion.CURRENT
        assert version_info.schema_hash is not None
    
    def test_migration_engine(self):
        """Test migration engine functionality"""
        version_manager = VersionManager()
        migration_engine = MigrationEngine(version_manager)
        
        # Test V1 to V3 migration
        v1_data = {
            "version": "1.0",
            "elements": [
                {"id": "test1", "type": "title", "text": "Test Title"}
            ]
        }
        
        migrated_data, version_info = migration_engine.migrate_data(
            v1_data, ModelVersion.V1_0, ModelVersion.V3_0
        )
        
        assert version_info.version == ModelVersion.V3_0
        assert "elements" in migrated_data
        assert migrated_data["elements"][0]["element_type"] == "Title"
    
    def test_versioned_element_collection(self):
        """Test versioned element collections"""
        elements = [
            ElementFactory.create_element(ElementType.TITLE, "Test"),
            create_table(cells=[["A"]])
        ]
        
        # Create versioned collection
        collection = VersionedElementCollection(elements)
        assert collection.version_info.version == ModelVersion.CURRENT
        
        # Test serialization
        data = collection.to_dict()
        assert "version_info" in data
        assert "elements" in data
        
        # Test deserialization
        restored_collection = VersionedElementCollection.from_dict(data)
        assert len(restored_collection.elements) == 2
        assert restored_collection.version_info.version == ModelVersion.CURRENT
        
        # Test validation
        errors = collection.validate()
        assert len(errors) == 0  # Should be valid


class TestCompleteIntegration:
    """Test complete system integration"""
    
    def test_full_workflow(self):
        """Test complete workflow with all components"""
        # 1. Create diverse elements
        elements = [
            # Basic elements
            ElementFactory.create_element(ElementType.TITLE, "Document Title"),
            ElementFactory.create_element(
                ElementType.NARRATIVE_TEXT, 
                "This is a sample document with various element types."
            ),
            
            # Complex elements
            create_table(
                cells=[
                    ["Feature", "Status", "Priority"],
                    ["Tables", "Complete", "High"],
                    ["Images", "Complete", "High"],
                    ["Formulas", "Complete", "Medium"]
                ],
                headers=["Feature", "Status", "Priority"]
            ),
            create_image(
                alt_text="Architecture diagram",
                caption="System architecture overview"
            ),
            create_formula(
                latex=r"\sum_{i=1}^{n} x_i = X",
                formula_type=FormulaType.DISPLAY
            ),
            create_code_block(
                code="def process_elements(elements):\n    return [elem.to_dict() for elem in elements]",
                language=CodeLanguage.PYTHON
            ),
            create_page_break()
        ]
        
        # 2. Build hierarchy
        builder = HierarchyBuilder()
        root = elements[0]  # Title as root
        
        hierarchy = builder.add_element(root)
        for elem in elements[1:]:
            hierarchy = hierarchy.add_child(root, elem)
        hierarchy = hierarchy.build()
        
        # 3. Validate hierarchy
        errors = hierarchy.validate_hierarchy()
        assert len(errors) == 0
        
        # 4. Test serialization/deserialization
        all_elements = list(hierarchy.elements.values())
        for element in all_elements:
            data = element.to_dict()
            
            # Verify serialization contains required fields
            assert "element_id" in data
            assert "element_type" in data
            assert "text" in data
            
            # Test deserialization based on type
            if element.element_type == ElementType.TABLE:
                restored = TableElement.from_dict(data)
            elif element.element_type == ElementType.IMAGE:
                restored = ImageElement.from_dict(data)
            elif element.element_type == ElementType.FORMULA:
                restored = FormulaElement.from_dict(data)
            elif element.element_type == ElementType.CODE_BLOCK:
                restored = CodeBlockElement.from_dict(data)
            elif element.element_type == ElementType.PAGE_BREAK:
                restored = PageBreakElement.from_dict(data)
            else:
                restored = Element.from_dict(data)
            
            assert restored.element_id == element.element_id
            assert restored.element_type == element.element_type
        
        # 5. Test file operations
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save as V3 format
            file_path = os.path.join(temp_dir, "complete_test.tore")
            ToreFileHandler.save_tore_file(all_elements, file_path, format_version="v3")
            
            # Load and verify
            loaded_elements = ToreFileHandler.load_tore_file(file_path)
            assert len(loaded_elements) == len(all_elements)
            
            # Test V1 compatibility
            v1_path = os.path.join(temp_dir, "v1_compat.tore")
            ToreFileHandler.save_tore_file(all_elements, v1_path, format_version="v1")
            
            v1_loaded = ToreFileHandler.load_tore_file(v1_path)
            assert len(v1_loaded) == len(all_elements)
        
        # 6. Test version tracking
        versioned_collection = VersionedElementCollection(all_elements)
        validation_errors = versioned_collection.validate()
        assert len(validation_errors) == 0
    
    def test_performance_with_large_dataset(self):
        """Test performance with larger element sets"""
        # Create 1000 mixed elements
        elements = []
        
        for i in range(200):
            # Mix of different element types
            elements.extend([
                ElementFactory.create_element(ElementType.TITLE, f"Title {i}"),
                ElementFactory.create_element(ElementType.NARRATIVE_TEXT, f"Text content {i}"),
                create_table(cells=[[f"Cell {i}", f"Value {i}"]]),
                create_image(alt_text=f"Image {i}"),
                create_formula(latex=f"x_{i} = {i}")
            ])
        
        # Test hierarchy creation
        hierarchy = ElementHierarchy(elements)
        assert len(hierarchy.elements) == 1000
        
        # Test operations
        root_elements = hierarchy.get_root_elements()
        assert len(root_elements) == 1000  # All are roots
        
        # Test serialization
        first_100 = elements[:100]
        serialized_data = [elem.to_dict() for elem in first_100]
        assert len(serialized_data) == 100
        
        # Test batch factory operations
        batch_data = [
            {"element_type": ElementType.NARRATIVE_TEXT, "text": f"Batch element {i}"}
            for i in range(100)
        ]
        batch_elements = ElementFactory.create_batch(batch_data)
        assert len(batch_elements) == 100