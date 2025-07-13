"""
Unit tests for the base Element class.

Tests cover initialization, serialization, comparison, and immutability.
"""

import pytest
import json
import uuid
from typing import Dict, Any

from torematrix.core.models import Element, ElementType, ElementMetadata, Coordinates


class TestElement:
    """Test suite for the base Element class."""
    
    def test_element_creation_with_defaults(self):
        """Test creating an element with default values."""
        element = Element()
        
        assert element.element_id is not None
        assert len(element.element_id) == 36  # UUID format
        assert element.element_type == ElementType.NARRATIVE_TEXT
        assert element.text == ""
        assert element.metadata is None
        assert element.parent_id is None
    
    def test_element_creation_with_values(self):
        """Test creating an element with specific values."""
        metadata = ElementMetadata()
        element = Element(
            element_id="test-123",
            element_type=ElementType.TITLE,
            text="Test Title",
            metadata=metadata,
            parent_id="parent-456"
        )
        
        assert element.element_id == "test-123"
        assert element.element_type == ElementType.TITLE
        assert element.text == "Test Title"
        assert element.metadata == metadata
        assert element.parent_id == "parent-456"
    
    def test_element_immutability(self):
        """Test that elements are immutable."""
        element = Element(text="Original")
        
        with pytest.raises(AttributeError):
            element.text = "Modified"
        
        with pytest.raises(AttributeError):
            element.element_type = ElementType.HEADER
    
    def test_element_validation(self):
        """Test element validation in __post_init__."""
        with pytest.raises(ValueError, match="element_type must be ElementType"):
            Element(element_type="NotAnEnum")
    
    def test_element_hash(self):
        """Test element hashing for use in sets and dicts."""
        element1 = Element(
            element_id="test-123",
            element_type=ElementType.TITLE,
            text="Test"
        )
        element2 = Element(
            element_id="test-123",
            element_type=ElementType.TITLE,
            text="Test"
        )
        element3 = Element(
            element_id="test-456",
            element_type=ElementType.TITLE,
            text="Test"
        )
        
        # Same content should have same hash
        assert hash(element1) == hash(element2)
        # Different ID should have different hash
        assert hash(element1) != hash(element3)
        
        # Should work in sets
        element_set = {element1, element2, element3}
        assert len(element_set) == 2  # element1 and element2 are considered same
    
    def test_element_equality(self):
        """Test element equality comparison."""
        element1 = Element(
            element_id="test-123",
            element_type=ElementType.TITLE,
            text="Test"
        )
        element2 = Element(
            element_id="test-123",
            element_type=ElementType.TITLE,
            text="Test"
        )
        element3 = Element(
            element_id="test-123",
            element_type=ElementType.TITLE,
            text="Different"
        )
        
        assert element1 == element2
        assert element1 != element3
        assert element1 != "not an element"
        assert element1 != None
    
    def test_to_dict_basic(self):
        """Test serialization to dictionary."""
        element = Element(
            element_id="test-123",
            element_type=ElementType.HEADER,
            text="Test Header",
            parent_id="parent-456"
        )
        
        data = element.to_dict()
        
        assert data["element_id"] == "test-123"
        assert data["element_type"] == "Header"
        assert data["text"] == "Test Header"
        assert data["parent_id"] == "parent-456"
        assert "metadata" not in data  # None metadata shouldn't be included
    
    def test_to_dict_with_metadata(self):
        """Test serialization with metadata."""
        coordinates = Coordinates(
            layout_bbox=(10, 20, 100, 50),
            system="pixel"
        )
        metadata = ElementMetadata(
            coordinates=coordinates,
            confidence=0.95,
            page_number=1
        )
        element = Element(
            element_type=ElementType.TITLE,
            text="Test",
            metadata=metadata
        )
        
        data = element.to_dict()
        
        assert "metadata" in data
        assert data["metadata"]["confidence"] == 0.95
        assert data["metadata"]["page_number"] == 1
    
    def test_from_dict_basic(self):
        """Test deserialization from dictionary."""
        data = {
            "element_id": "test-123",
            "element_type": "Title",
            "text": "Test Title",
            "parent_id": "parent-456"
        }
        
        element = Element.from_dict(data)
        
        assert element.element_id == "test-123"
        assert element.element_type == ElementType.TITLE
        assert element.text == "Test Title"
        assert element.parent_id == "parent-456"
        assert element.metadata is None
    
    def test_from_dict_with_metadata(self):
        """Test deserialization with metadata."""
        data = {
            "element_id": "test-123",
            "element_type": "Title",
            "text": "Test",
            "metadata": {
                "confidence": 0.95,
                "page_number": 1,
                "coordinates": {
                    "layout_bbox": [10, 20, 100, 50],
                    "system": "pixel"
                }
            }
        }
        
        element = Element.from_dict(data)
        
        assert element.metadata is not None
        assert element.metadata.confidence == 0.95
        assert element.metadata.page_number == 1
        assert element.metadata.coordinates is not None
    
    def test_from_dict_generates_id(self):
        """Test that from_dict generates ID if missing."""
        data = {
            "element_type": "Title",
            "text": "Test"
        }
        
        element = Element.from_dict(data)
        
        assert element.element_id is not None
        assert len(element.element_id) == 36  # UUID format
    
    def test_to_json(self):
        """Test JSON serialization."""
        element = Element(
            element_id="test-123",
            element_type=ElementType.TITLE,
            text="Test Title"
        )
        
        json_str = element.to_json()
        data = json.loads(json_str)
        
        assert data["element_id"] == "test-123"
        assert data["element_type"] == "Title"
        assert data["text"] == "Test Title"
    
    def test_from_json(self):
        """Test JSON deserialization."""
        json_str = """{
            "element_id": "test-123",
            "element_type": "Title",
            "text": "Test Title",
            "parent_id": null
        }"""
        
        element = Element.from_json(json_str)
        
        assert element.element_id == "test-123"
        assert element.element_type == ElementType.TITLE
        assert element.text == "Test Title"
    
    def test_round_trip_serialization(self):
        """Test that serialization round-trip preserves data."""
        original = Element(
            element_type=ElementType.FOOTER,
            text="Page 1",
            parent_id="doc-123"
        )
        
        # Dictionary round-trip
        dict_data = original.to_dict()
        from_dict = Element.from_dict(dict_data)
        assert from_dict.element_type == original.element_type
        assert from_dict.text == original.text
        assert from_dict.parent_id == original.parent_id
        
        # JSON round-trip
        json_data = original.to_json()
        from_json = Element.from_json(json_data)
        assert from_json.element_type == original.element_type
        assert from_json.text == original.text
        assert from_json.parent_id == original.parent_id
    
    def test_copy_with(self):
        """Test creating modified copies of immutable elements."""
        original = Element(
            element_id="test-123",
            element_type=ElementType.TITLE,
            text="Original Title",
            parent_id="parent-456"
        )
        
        # Copy with new text
        modified = original.copy_with(text="Modified Title")
        assert modified.text == "Modified Title"
        assert modified.element_id == original.element_id
        assert modified.element_type == original.element_type
        assert modified.parent_id == original.parent_id
        
        # Copy with new type
        modified2 = original.copy_with(
            element_type="Header",
            text="Now a header"
        )
        assert modified2.element_type == ElementType.HEADER
        assert modified2.text == "Now a header"
        
        # Original should be unchanged
        assert original.text == "Original Title"
        assert original.element_type == ElementType.TITLE
    
    def test_all_element_types(self):
        """Test that all ElementType values work correctly."""
        for element_type in ElementType:
            element = Element(
                element_type=element_type,
                text=f"Test {element_type.value}"
            )
            
            assert element.element_type == element_type
            
            # Test serialization
            data = element.to_dict()
            assert data["element_type"] == element_type.value
            
            # Test deserialization
            restored = Element.from_dict(data)
            assert restored.element_type == element_type