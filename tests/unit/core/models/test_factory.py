"""
Tests for ElementFactory and related factory functionality.
"""

import pytest
import uuid
from unittest.mock import Mock, patch

from src.torematrix.core.models.factory import ElementFactory, ElementTransformer
from src.torematrix.core.models.element import Element, ElementType
from src.torematrix.core.models.metadata import ElementMetadata
from src.torematrix.core.models.coordinates import Coordinates


class TestElementFactory:
    """Test ElementFactory functionality"""
    
    def test_create_element_basic(self):
        """Test basic element creation"""
        element = ElementFactory.create_element(
            element_type=ElementType.TITLE,
            text="Test Title"
        )
        
        assert element.element_type == ElementType.TITLE
        assert element.text == "Test Title"
        assert element.element_id is not None
        assert element.parent_id is None
        assert element.metadata.detection_method == "factory"
    
    def test_create_element_with_string_type(self):
        """Test element creation with string element type"""
        element = ElementFactory.create_element(
            element_type="Title",
            text="Test Title"
        )
        
        assert element.element_type == ElementType.TITLE
        assert element.text == "Test Title"
    
    def test_create_element_with_invalid_type(self):
        """Test element creation with invalid type raises error"""
        with pytest.raises(ValueError, match="Invalid element type"):
            ElementFactory.create_element(
                element_type="InvalidType",
                text="Test"
            )
    
    def test_create_element_with_metadata(self):
        """Test element creation with metadata"""
        metadata = {
            'confidence': 0.95,
            'page_number': 1,
            'languages': ['en'],
            'custom_fields': {'test': 'value'}
        }
        
        element = ElementFactory.create_element(
            element_type=ElementType.NARRATIVE_TEXT,
            text="Test text",
            metadata=metadata
        )
        
        assert element.metadata.confidence == 0.95
        assert element.metadata.page_number == 1
        assert element.metadata.languages == ['en']
        assert element.metadata.custom_fields['test'] == 'value'
    
    def test_create_element_with_coordinates(self):
        """Test element creation with coordinates"""
        metadata = {
            'coordinates': {
                'layout_bbox': [10.0, 20.0, 100.0, 200.0],
                'text_bbox': [15.0, 25.0, 95.0, 195.0],
                'system': 'pixel'
            }
        }
        
        element = ElementFactory.create_element(
            element_type=ElementType.TEXT,
            text="Test text",
            metadata=metadata
        )
        
        assert element.metadata.coordinates is not None
        assert element.metadata.coordinates.layout_bbox == [10.0, 20.0, 100.0, 200.0]
        assert element.metadata.coordinates.text_bbox == [15.0, 25.0, 95.0, 195.0]
        assert element.metadata.coordinates.system == 'pixel'
    
    def test_create_element_with_custom_id(self):
        """Test element creation with custom ID"""
        custom_id = "custom-element-id"
        
        element = ElementFactory.create_element(
            element_type=ElementType.HEADER,
            text="Test header",
            element_id=custom_id
        )
        
        assert element.element_id == custom_id
    
    def test_create_element_with_parent(self):
        """Test element creation with parent ID"""
        parent_id = "parent-element-id"
        
        element = ElementFactory.create_element(
            element_type=ElementType.LIST_ITEM,
            text="Test item",
            parent_id=parent_id
        )
        
        assert element.parent_id == parent_id
    
    def test_create_element_with_kwargs(self):
        """Test element creation with kwargs metadata"""
        element = ElementFactory.create_element(
            element_type=ElementType.FOOTER,
            text="Test footer",
            confidence=0.8,
            page_number=5,
            custom_field="value"
        )
        
        assert element.metadata.confidence == 0.8
        assert element.metadata.page_number == 5
    
    def test_from_unstructured_basic(self):
        """Test conversion from unstructured element"""
        # Mock unstructured element
        mock_unstructured = Mock()
        mock_unstructured.category = "Title"
        mock_unstructured.text = "Test Title"
        mock_unstructured.metadata = None
        
        element = ElementFactory.from_unstructured(mock_unstructured)
        
        assert element.element_type == ElementType.TITLE
        assert element.text == "Test Title"
        assert element.metadata.detection_method == "unstructured"
    
    def test_from_unstructured_with_metadata(self):
        """Test conversion from unstructured element with metadata"""
        # Mock unstructured element with metadata
        mock_metadata = Mock()
        mock_metadata.confidence = 0.9
        mock_metadata.page_number = 2
        mock_metadata.languages = ['en', 'es']
        
        mock_coordinates = Mock()
        mock_coordinates.layout_bbox = [10, 20, 100, 200]
        mock_coordinates.text_bbox = [15, 25, 95, 195]
        mock_coordinates.system = "pixel"
        mock_metadata.coordinates = mock_coordinates
        
        mock_unstructured = Mock()
        mock_unstructured.category = "NarrativeText"
        mock_unstructured.text = "Test text"
        mock_unstructured.metadata = mock_metadata
        
        element = ElementFactory.from_unstructured(mock_unstructured)
        
        assert element.element_type == ElementType.NARRATIVE_TEXT
        assert element.text == "Test text"
        assert element.metadata.confidence == 0.9
        assert element.metadata.page_number == 2
        assert element.metadata.languages == ['en', 'es']
        assert element.metadata.coordinates.layout_bbox == [10, 20, 100, 200]
    
    def test_from_unstructured_with_detection_class_prob(self):
        """Test conversion using detection_class_prob for confidence"""
        mock_metadata = Mock()
        mock_metadata.detection_class_prob = {'Title': 0.95, 'Header': 0.05}
        
        mock_unstructured = Mock()
        mock_unstructured.category = "Title"
        mock_unstructured.text = "Test Title"
        mock_unstructured.metadata = mock_metadata
        
        element = ElementFactory.from_unstructured(mock_unstructured)
        
        assert element.metadata.confidence == 0.95
    
    def test_from_unstructured_invalid_fails(self):
        """Test that invalid unstructured element raises error"""
        mock_unstructured = Mock()
        mock_unstructured.category = "InvalidCategory"
        mock_unstructured.text = "Test"
        mock_unstructured.metadata = None
        
        with pytest.raises(ValueError, match="Failed to convert unstructured element"):
            ElementFactory.from_unstructured(mock_unstructured)
    
    def test_create_batch_success(self):
        """Test successful batch element creation"""
        elements_data = [
            {
                'element_type': ElementType.TITLE,
                'text': 'Title 1'
            },
            {
                'element_type': 'NarrativeText',
                'text': 'Text 1',
                'metadata': {'confidence': 0.9}
            },
            {
                'element_type': ElementType.FOOTER,
                'text': 'Footer 1'
            }
        ]
        
        elements = ElementFactory.create_batch(elements_data)
        
        assert len(elements) == 3
        assert elements[0].element_type == ElementType.TITLE
        assert elements[1].element_type == ElementType.NARRATIVE_TEXT
        assert elements[1].metadata.confidence == 0.9
        assert elements[2].element_type == ElementType.FOOTER
    
    def test_create_batch_with_failure(self):
        """Test batch creation with one failure"""
        elements_data = [
            {
                'element_type': ElementType.TITLE,
                'text': 'Title 1'
            },
            {
                'element_type': 'InvalidType',  # This will fail
                'text': 'Text 1'
            }
        ]
        
        with pytest.raises(ValueError, match="Failed to create element at index 1"):
            ElementFactory.create_batch(elements_data)
    
    def test_create_from_text_basic(self):
        """Test quick element creation from text"""
        element = ElementFactory.create_from_text("Test text")
        
        assert element.element_type == ElementType.NARRATIVE_TEXT
        assert element.text == "Test text"
        assert element.metadata.page_number is None
    
    def test_create_from_text_with_options(self):
        """Test text element creation with options"""
        element = ElementFactory.create_from_text(
            text="Test header",
            element_type=ElementType.HEADER,
            page_number=3,
            confidence=0.85
        )
        
        assert element.element_type == ElementType.HEADER
        assert element.text == "Test header"
        assert element.metadata.page_number == 3
        assert element.metadata.confidence == 0.85
    
    def test_clone_element_basic(self):
        """Test basic element cloning"""
        original = ElementFactory.create_element(
            element_type=ElementType.TITLE,
            text="Original title",
            metadata={'confidence': 0.9}
        )
        
        clone = ElementFactory.clone_element(original)
        
        assert clone.element_type == original.element_type
        assert clone.text == original.text
        assert clone.metadata.confidence == original.metadata.confidence
        assert clone.element_id != original.element_id  # Should have new ID
    
    def test_clone_element_with_overrides(self):
        """Test element cloning with overrides"""
        original = ElementFactory.create_element(
            element_type=ElementType.TITLE,
            text="Original title",
            metadata={'confidence': 0.9}
        )
        
        clone = ElementFactory.clone_element(
            original,
            text="New title",
            metadata={'confidence': 0.95}
        )
        
        assert clone.text == "New title"
        assert clone.metadata.confidence == 0.95
        assert clone.element_type == original.element_type
        assert clone.element_id != original.element_id


class TestElementTransformer:
    """Test ElementTransformer functionality"""
    
    def test_change_type(self):
        """Test changing element type"""
        element = ElementFactory.create_element(
            element_type=ElementType.TEXT,
            text="Test text"
        )
        
        transformed = ElementTransformer.change_type(element, ElementType.NARRATIVE_TEXT)
        
        assert transformed.element_type == ElementType.NARRATIVE_TEXT
        assert transformed.text == element.text
        assert transformed.element_id != element.element_id
    
    def test_change_type_with_string(self):
        """Test changing element type with string"""
        element = ElementFactory.create_element(
            element_type=ElementType.TEXT,
            text="Test text"
        )
        
        transformed = ElementTransformer.change_type(element, "Title")
        
        assert transformed.text == element.text
    
    def test_merge_text_basic(self):
        """Test merging multiple elements"""
        elements = [
            ElementFactory.create_element(ElementType.TEXT, "First"),
            ElementFactory.create_element(ElementType.TEXT, "Second"),
            ElementFactory.create_element(ElementType.TEXT, "Third")
        ]
        
        merged = ElementTransformer.merge_text(elements)
        
        assert merged.text == "First Second Third"
        assert merged.element_type == ElementType.NARRATIVE_TEXT
        assert merged.metadata.detection_method == "merged"
        assert 'merged_from' in merged.metadata.custom_fields
        assert len(merged.metadata.custom_fields['merged_from']) == 3
    
    def test_merge_text_with_custom_separator(self):
        """Test merging with custom separator"""
        elements = [
            ElementFactory.create_element(ElementType.TEXT, "First"),
            ElementFactory.create_element(ElementType.TEXT, "Second")
        ]
        
        merged = ElementTransformer.merge_text(elements, separator=" | ")
        
        assert merged.text == "First | Second"
    
    def test_merge_text_with_custom_type(self):
        """Test merging with custom result type"""
        elements = [
            ElementFactory.create_element(ElementType.TEXT, "First"),
            ElementFactory.create_element(ElementType.TEXT, "Second")
        ]
        
        merged = ElementTransformer.merge_text(elements, new_type=ElementType.TITLE)
        
        assert merged.element_type == ElementType.TITLE
    
    def test_merge_text_empty_list_fails(self):
        """Test that merging empty list raises error"""
        with pytest.raises(ValueError, match="Cannot merge empty list"):
            ElementTransformer.merge_text([])
    
    def test_split_by_sentences_basic(self):
        """Test splitting element by sentences"""
        element = ElementFactory.create_element(
            ElementType.NARRATIVE_TEXT,
            "First sentence. Second sentence! Third sentence?"
        )
        
        split_elements = ElementTransformer.split_by_sentences(element)
        
        assert len(split_elements) == 3
        assert split_elements[0].text == "First sentence."
        assert split_elements[1].text == "Second sentence!"
        assert split_elements[2].text == "Third sentence?"
        
        for i, elem in enumerate(split_elements):
            assert elem.metadata.detection_method == "split"
            assert elem.metadata.custom_fields['split_from'] == element.element_id
            assert elem.metadata.custom_fields['sentence_index'] == i
            assert elem.parent_id == element.element_id
    
    def test_split_by_sentences_no_split(self):
        """Test splitting element with no sentence endings"""
        element = ElementFactory.create_element(
            ElementType.NARRATIVE_TEXT,
            "Single sentence without ending"
        )
        
        split_elements = ElementTransformer.split_by_sentences(element)
        
        assert len(split_elements) == 1
        assert split_elements[0] == element
    
    def test_split_by_sentences_empty_text(self):
        """Test splitting element with empty text"""
        element = ElementFactory.create_element(
            ElementType.NARRATIVE_TEXT,
            ""
        )
        
        split_elements = ElementTransformer.split_by_sentences(element)
        
        assert len(split_elements) == 1
        assert split_elements[0] == element
    
    def test_split_by_sentences_custom_endings(self):
        """Test splitting with custom sentence endings"""
        element = ElementFactory.create_element(
            ElementType.NARRATIVE_TEXT,
            "First part; second part; third part"
        )
        
        split_elements = ElementTransformer.split_by_sentences(
            element,
            sentence_endings=[';']
        )
        
        assert len(split_elements) == 3
        assert split_elements[0].text == "First part;"
        assert split_elements[1].text == "second part;"
        assert split_elements[2].text == "third part"


if __name__ == "__main__":
    pytest.main([__file__])