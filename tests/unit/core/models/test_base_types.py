"""
Unit tests for base element type implementations.

Tests cover TitleElement, NarrativeTextElement, ListItemElement,
HeaderElement, and FooterElement classes.
"""

import pytest
from typing import Optional

from torematrix.core.models import (
    Element,
    ElementType,
    ElementMetadata,
    Coordinates,
    TitleElement,
    NarrativeTextElement,
    ListItemElement,
    HeaderElement,
    FooterElement,
    create_title,
    create_narrative_text,
    create_list_item,
    create_header,
    create_footer,
)


class TestTitleElement:
    """Test suite for TitleElement."""
    
    def test_title_creation(self):
        """Test creating a title element."""
        title = TitleElement(text="Chapter 1: Introduction")
        
        assert title.element_type == ElementType.TITLE
        assert title.text == "Chapter 1: Introduction"
        assert title.element_id is not None
        assert title.metadata is None
        assert title.parent_id is None
    
    def test_title_with_metadata(self):
        """Test title with metadata."""
        metadata = ElementMetadata(
            confidence=0.98,
            page_number=1
        )
        title = TitleElement(
            text="Main Title",
            metadata=metadata,
            element_id="title-123"
        )
        
        assert title.metadata == metadata
        assert title.element_id == "title-123"
    
    def test_title_inheritance(self):
        """Test that TitleElement creates an Element."""
        title = TitleElement(text="Test")
        assert isinstance(title, Element)
        # TitleElement is a factory, not a class inheritance
    
    def test_title_immutability(self):
        """Test that title elements are immutable."""
        title = TitleElement(text="Original")
        
        with pytest.raises(AttributeError):
            title.text = "Modified"
    
    def test_create_title_factory(self):
        """Test the create_title factory function."""
        title = create_title("Factory Title")
        
        assert isinstance(title, Element)
        assert title.text == "Factory Title"
        assert title.element_type == ElementType.TITLE


class TestNarrativeTextElement:
    """Test suite for NarrativeTextElement."""
    
    def test_narrative_creation(self):
        """Test creating a narrative text element."""
        narrative = NarrativeTextElement(
            text="This is a paragraph of narrative text."
        )
        
        assert narrative.element_type == ElementType.NARRATIVE_TEXT
        assert narrative.text == "This is a paragraph of narrative text."
    
    def test_narrative_with_parent(self):
        """Test narrative text with parent ID."""
        narrative = NarrativeTextElement(
            text="Child paragraph",
            parent_id="section-123"
        )
        
        assert narrative.parent_id == "section-123"
    
    def test_narrative_serialization(self):
        """Test narrative text serialization."""
        narrative = NarrativeTextElement(
            text="Test paragraph",
            element_id="para-123"
        )
        
        data = narrative.to_dict()
        assert data["element_type"] == "NarrativeText"
        assert data["text"] == "Test paragraph"
        assert data["element_id"] == "para-123"
        
        # Round-trip
        restored = Element.from_dict(data)
        assert restored.element_type == ElementType.NARRATIVE_TEXT
        assert restored.text == narrative.text
    
    def test_create_narrative_factory(self):
        """Test the create_narrative_text factory function."""
        narrative = create_narrative_text(
            "Factory narrative",
            parent_id="doc-123"
        )
        
        assert isinstance(narrative, Element)
        assert narrative.text == "Factory narrative"
        assert narrative.parent_id == "doc-123"


class TestListItemElement:
    """Test suite for ListItemElement."""
    
    def test_list_item_creation(self):
        """Test creating a list item element."""
        item = ListItemElement(
            text="First item in the list",
            parent_id="list-123"
        )
        
        assert item.element_type == ElementType.LIST_ITEM
        assert item.text == "First item in the list"
        assert item.parent_id == "list-123"
    
    def test_list_item_hierarchy(self):
        """Test list items in a hierarchy."""
        parent_list_id = "list-main"
        
        item1 = ListItemElement(
            text="Item 1",
            parent_id=parent_list_id
        )
        item2 = ListItemElement(
            text="Item 2",
            parent_id=parent_list_id
        )
        
        assert item1.parent_id == parent_list_id
        assert item2.parent_id == parent_list_id
        assert item1.element_id != item2.element_id
    
    def test_create_list_item_factory(self):
        """Test the create_list_item factory function."""
        item = create_list_item(
            "• Bullet point",
            parent_id="list-456"
        )
        
        assert isinstance(item, Element)
        assert item.text == "• Bullet point"
        assert item.parent_id == "list-456"


class TestHeaderElement:
    """Test suite for HeaderElement."""
    
    def test_header_creation(self):
        """Test creating a header element."""
        header = HeaderElement(
            text="Document Title - Page Header"
        )
        
        assert header.element_type == ElementType.HEADER
        assert header.text == "Document Title - Page Header"
    
    def test_header_with_coordinates(self):
        """Test header with coordinate metadata."""
        coordinates = Coordinates(
            layout_bbox=(0, 0, 612, 50),
            system="point"
        )
        metadata = ElementMetadata(
            coordinates=coordinates,
            page_number=1
        )
        
        header = HeaderElement(
            text="Page Header",
            metadata=metadata
        )
        
        assert header.metadata.coordinates.layout_bbox == (0, 0, 612, 50)
        assert header.metadata.coordinates.system == "point"
    
    def test_header_json_serialization(self):
        """Test header JSON serialization."""
        header = HeaderElement(
            text="JSON Header",
            element_id="header-789"
        )
        
        json_str = header.to_json()
        restored = Element.from_json(json_str)
        
        assert restored.element_type == ElementType.HEADER
        assert restored.text == "JSON Header"
        assert restored.element_id == "header-789"
    
    def test_create_header_factory(self):
        """Test the create_header factory function."""
        header = create_header("Factory Header")
        
        assert isinstance(header, Element)
        assert header.element_type == ElementType.HEADER


class TestFooterElement:
    """Test suite for FooterElement."""
    
    def test_footer_creation(self):
        """Test creating a footer element."""
        footer = FooterElement(
            text="Page 1 of 10"
        )
        
        assert footer.element_type == ElementType.FOOTER
        assert footer.text == "Page 1 of 10"
    
    def test_footer_with_metadata(self):
        """Test footer with full metadata."""
        metadata = ElementMetadata(
            confidence=0.99,
            detection_method="pattern_match",
            page_number=1,
            languages=["en"]
        )
        
        footer = FooterElement(
            text="© 2024 Company Name",
            metadata=metadata,
            element_id="footer-123"
        )
        
        assert footer.metadata.confidence == 0.99
        assert footer.metadata.detection_method == "pattern_match"
        assert footer.metadata.languages == ["en"]
    
    def test_footer_equality(self):
        """Test footer element equality."""
        footer1 = FooterElement(
            text="Page 1",
            element_id="footer-same"
        )
        footer2 = FooterElement(
            text="Page 1",
            element_id="footer-same"
        )
        footer3 = FooterElement(
            text="Page 2",
            element_id="footer-same"
        )
        
        assert footer1 == footer2
        assert footer1 != footer3  # Different text
    
    def test_create_footer_factory(self):
        """Test the create_footer factory function."""
        footer = create_footer(
            "Copyright 2024",
            element_id="footer-456"
        )
        
        assert isinstance(footer, Element)
        assert footer.text == "Copyright 2024"
        assert footer.element_id == "footer-456"


class TestBaseTypesIntegration:
    """Integration tests for all base types."""
    
    def test_all_types_serialization(self):
        """Test that all base types can be serialized and restored."""
        elements = [
            TitleElement(text="Title Test"),
            NarrativeTextElement(text="Narrative Test"),
            ListItemElement(text="List Test"),
            HeaderElement(text="Header Test"),
            FooterElement(text="Footer Test"),
        ]
        
        for original in elements:
            # Dictionary serialization
            data = original.to_dict()
            restored = Element.from_dict(data)
            
            assert restored.element_type == original.element_type
            assert restored.text == original.text
            assert type(restored) == Element  # Not the specific subclass
            
            # JSON serialization
            json_str = original.to_json()
            restored_json = Element.from_json(json_str)
            
            assert restored_json.element_type == original.element_type
            assert restored_json.text == original.text
    
    def test_document_hierarchy(self):
        """Test creating a document hierarchy with base types."""
        # Create a simple document structure
        doc_title = TitleElement(
            text="Document Title",
            element_id="title-main"
        )
        
        header = HeaderElement(
            text="Chapter 1",
            element_id="header-ch1"
        )
        
        para1 = NarrativeTextElement(
            text="First paragraph of content.",
            parent_id="section-1"
        )
        
        para2 = NarrativeTextElement(
            text="Second paragraph of content.",
            parent_id="section-1"
        )
        
        list_item1 = ListItemElement(
            text="First list item",
            parent_id="list-1"
        )
        
        list_item2 = ListItemElement(
            text="Second list item",
            parent_id="list-1"
        )
        
        footer = FooterElement(
            text="Page 1",
            element_id="footer-p1"
        )
        
        # Verify structure
        elements = [
            doc_title, header, para1, para2,
            list_item1, list_item2, footer
        ]
        
        # All should be Element instances
        assert all(isinstance(e, Element) for e in elements)
        
        # Check parent relationships
        assert para1.parent_id == para2.parent_id == "section-1"
        assert list_item1.parent_id == list_item2.parent_id == "list-1"
        
        # Each should have unique IDs
        ids = [e.element_id for e in elements]
        assert len(ids) == len(set(ids))  # All unique
    
    def test_factory_functions_with_metadata(self):
        """Test all factory functions with metadata."""
        metadata = ElementMetadata(
            confidence=0.95,
            page_number=1
        )
        
        elements = [
            create_title("Title", metadata=metadata),
            create_narrative_text("Text", metadata=metadata),
            create_list_item("Item", metadata=metadata),
            create_header("Header", metadata=metadata),
            create_footer("Footer", metadata=metadata),
        ]
        
        for element in elements:
            assert element.metadata == metadata
            assert element.metadata.confidence == 0.95
            assert element.metadata.page_number == 1