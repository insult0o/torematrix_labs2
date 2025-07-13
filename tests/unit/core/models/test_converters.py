"""
Tests for format conversion utilities.
"""

import pytest
import json
import xml.etree.ElementTree as ET
from io import StringIO

from src.torematrix.core.models.converters import (
    JSONConverter, XMLConverter, CSVConverter, 
    PlainTextConverter, UniversalConverter
)
from src.torematrix.core.models.factory import ElementFactory
from src.torematrix.core.models.element import ElementType


class TestJSONConverter:
    """Test JSON conversion functionality"""
    
    def create_test_elements(self):
        """Create test elements for conversion tests"""
        return [
            ElementFactory.create_element(
                element_type=ElementType.TITLE,
                text="Test Title",
                metadata={'confidence': 0.9, 'page_number': 1}
            ),
            ElementFactory.create_element(
                element_type=ElementType.NARRATIVE_TEXT,
                text="Test paragraph text.",
                metadata={'confidence': 0.85, 'page_number': 1}
            )
        ]
    
    def test_elements_to_json_basic(self):
        """Test basic JSON conversion"""
        elements = self.create_test_elements()
        
        json_str = JSONConverter.elements_to_json(elements)
        
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert len(data) == 2
        assert data[0]['element_type'] == 'Title'
        assert data[0]['text'] == 'Test Title'
        assert data[1]['element_type'] == 'NarrativeText'
    
    def test_elements_to_json_compact(self):
        """Test compact JSON conversion"""
        elements = self.create_test_elements()
        
        json_str = JSONConverter.elements_to_json(elements, indent=None)
        
        assert '\n' not in json_str  # Compact format
        data = json.loads(json_str)
        assert len(data) == 2
    
    def test_elements_to_json_no_metadata(self):
        """Test JSON conversion without metadata"""
        elements = self.create_test_elements()
        
        json_str = JSONConverter.elements_to_json(elements, include_metadata=False)
        
        data = json.loads(json_str)
        assert 'metadata' not in data[0]
        assert 'element_type' in data[0]
        assert 'text' in data[0]
    
    def test_elements_from_json_string(self):
        """Test creating elements from JSON string"""
        elements = self.create_test_elements()
        json_str = JSONConverter.elements_to_json(elements)
        
        restored_elements = JSONConverter.elements_from_json(json_str)
        
        assert len(restored_elements) == 2
        assert restored_elements[0].element_type == ElementType.TITLE
        assert restored_elements[0].text == "Test Title"
        assert restored_elements[1].element_type == ElementType.NARRATIVE_TEXT
    
    def test_elements_from_json_dict(self):
        """Test creating elements from parsed JSON dict"""
        elements = self.create_test_elements()
        json_str = JSONConverter.elements_to_json(elements)
        data = json.loads(json_str)
        
        restored_elements = JSONConverter.elements_from_json(data)
        
        assert len(restored_elements) == 2
        assert restored_elements[0].element_type == ElementType.TITLE
    
    def test_elements_from_json_invalid_json(self):
        """Test error handling for invalid JSON"""
        with pytest.raises(ValueError, match="Invalid JSON"):
            JSONConverter.elements_from_json("invalid json {")
    
    def test_elements_from_json_invalid_format(self):
        """Test error handling for non-list JSON"""
        with pytest.raises(ValueError, match="JSON must contain a list"):
            JSONConverter.elements_from_json('{"not": "a list"}')
    
    def test_element_to_dict_basic(self):
        """Test single element to dict conversion"""
        element = ElementFactory.create_element(
            element_type=ElementType.HEADER,
            text="Test Header"
        )
        
        result = JSONConverter.element_to_dict(element)
        
        assert result['element_type'] == 'Header'
        assert result['text'] == 'Test Header'
        assert 'metadata' in result
    
    def test_element_to_dict_no_metadata(self):
        """Test single element to dict without metadata"""
        element = ElementFactory.create_element(
            element_type=ElementType.HEADER,
            text="Test Header"
        )
        
        result = JSONConverter.element_to_dict(element, include_metadata=False)
        
        assert 'metadata' not in result
        assert result['element_type'] == 'Header'


class TestXMLConverter:
    """Test XML conversion functionality"""
    
    def create_test_elements(self):
        """Create test elements for XML tests"""
        return [
            ElementFactory.create_element(
                element_type=ElementType.TITLE,
                text="Test Title",
                metadata={'confidence': 0.9, 'page_number': 1}
            ),
            ElementFactory.create_element(
                element_type=ElementType.TEXT,
                text="Test text content.",
                parent_id="parent-123"
            )
        ]
    
    def test_elements_to_xml_basic(self):
        """Test basic XML conversion"""
        elements = self.create_test_elements()
        
        xml_str = XMLConverter.elements_to_xml(elements)
        
        root = ET.fromstring(xml_str)
        assert root.tag == "document"
        
        element_nodes = root.findall("element")
        assert len(element_nodes) == 2
        
        assert element_nodes[0].get("type") == "Title"
        assert element_nodes[1].get("parent_id") == "parent-123"
    
    def test_elements_to_xml_custom_root(self):
        """Test XML conversion with custom root name"""
        elements = self.create_test_elements()
        
        xml_str = XMLConverter.elements_to_xml(elements, root_name="mydoc")
        
        root = ET.fromstring(xml_str)
        assert root.tag == "mydoc"
    
    def test_elements_to_xml_no_metadata(self):
        """Test XML conversion without metadata"""
        elements = self.create_test_elements()
        
        xml_str = XMLConverter.elements_to_xml(elements, include_metadata=False)
        
        root = ET.fromstring(xml_str)
        element_nodes = root.findall("element")
        
        # Should not have metadata nodes
        for elem_node in element_nodes:
            assert elem_node.find("metadata") is None
    
    def test_elements_from_xml_basic(self):
        """Test creating elements from XML"""
        elements = self.create_test_elements()
        xml_str = XMLConverter.elements_to_xml(elements)
        
        restored_elements = XMLConverter.elements_from_xml(xml_str)
        
        assert len(restored_elements) == 2
        assert restored_elements[0].element_type == ElementType.TITLE
        assert restored_elements[0].text == "Test Title"
        assert restored_elements[1].parent_id == "parent-123"
    
    def test_elements_from_xml_invalid(self):
        """Test error handling for invalid XML"""
        with pytest.raises(ValueError, match="Invalid XML"):
            XMLConverter.elements_from_xml("<invalid xml")
    
    def test_xml_with_coordinates(self):
        """Test XML conversion with coordinate metadata"""
        element = ElementFactory.create_element(
            element_type=ElementType.IMAGE,
            text="Image description",
            metadata={
                'coordinates': {
                    'layout_bbox': [10.0, 20.0, 100.0, 200.0],
                    'system': 'pixel'
                }
            }
        )
        
        xml_str = XMLConverter.elements_to_xml([element])
        restored_elements = XMLConverter.elements_from_xml(xml_str)
        
        assert len(restored_elements) == 1
        restored = restored_elements[0]
        assert restored.metadata.coordinates is not None
        assert restored.metadata.coordinates.layout_bbox == [10.0, 20.0, 100.0, 200.0]
        assert restored.metadata.coordinates.system == 'pixel'


class TestCSVConverter:
    """Test CSV conversion functionality"""
    
    def create_test_elements(self):
        """Create test elements for CSV tests"""
        return [
            ElementFactory.create_element(
                element_type=ElementType.TITLE,
                text="Test Title",
                metadata={'confidence': 0.9, 'page_number': 1}
            ),
            ElementFactory.create_element(
                element_type=ElementType.TEXT,
                text="Test text",
                parent_id="parent-123"
            )
        ]
    
    def test_elements_to_csv_basic(self):
        """Test basic CSV conversion"""
        elements = self.create_test_elements()
        
        csv_str = CSVConverter.elements_to_csv(elements)
        
        lines = csv_str.strip().split('\n')
        assert len(lines) == 3  # Header + 2 data rows
        assert 'element_id,element_type,text,parent_id' in lines[0]
        assert 'Title' in lines[1]
        assert 'Text' in lines[2]
    
    def test_elements_to_csv_with_metadata(self):
        """Test CSV conversion with metadata columns"""
        elements = self.create_test_elements()
        
        csv_str = CSVConverter.elements_to_csv(elements, include_metadata=True)
        
        lines = csv_str.strip().split('\n')
        header = lines[0]
        assert 'confidence' in header
        assert 'page_number' in header
        assert 'detection_method' in header
    
    def test_elements_to_csv_custom_delimiter(self):
        """Test CSV conversion with custom delimiter"""
        elements = self.create_test_elements()
        
        csv_str = CSVConverter.elements_to_csv(elements, delimiter=';')
        
        lines = csv_str.strip().split('\n')
        assert ';' in lines[0]
        assert ';' in lines[1]
    
    def test_elements_from_csv_basic(self):
        """Test creating elements from CSV"""
        elements = self.create_test_elements()
        csv_str = CSVConverter.elements_to_csv(elements)
        
        restored_elements = CSVConverter.elements_from_csv(csv_str)
        
        assert len(restored_elements) == 2
        assert restored_elements[0].element_type == ElementType.TITLE
        assert restored_elements[0].text == "Test Title"
    
    def test_elements_from_csv_with_metadata(self):
        """Test creating elements from CSV with metadata"""
        elements = self.create_test_elements()
        csv_str = CSVConverter.elements_to_csv(elements, include_metadata=True)
        
        restored_elements = CSVConverter.elements_from_csv(csv_str, has_metadata=True)
        
        assert len(restored_elements) == 2
        assert restored_elements[0].metadata.confidence == 0.9
        assert restored_elements[0].metadata.page_number == 1
    
    def test_elements_from_csv_invalid(self):
        """Test error handling for invalid CSV"""
        with pytest.raises(ValueError, match="Failed to parse CSV"):
            CSVConverter.elements_from_csv("invalid,csv\ndata")


class TestPlainTextConverter:
    """Test plain text conversion functionality"""
    
    def test_elements_to_text_basic(self):
        """Test basic text conversion"""
        elements = [
            ElementFactory.create_element(ElementType.TITLE, "Title"),
            ElementFactory.create_element(ElementType.TEXT, "Content")
        ]
        
        text = PlainTextConverter.elements_to_text(elements)
        
        assert text == "Title\n\nContent"
    
    def test_elements_to_text_with_types(self):
        """Test text conversion including element types"""
        elements = [
            ElementFactory.create_element(ElementType.TITLE, "Title"),
            ElementFactory.create_element(ElementType.TEXT, "Content")
        ]
        
        text = PlainTextConverter.elements_to_text(elements, include_types=True)
        
        assert "[Title] Title" in text
        assert "[Text] Content" in text
    
    def test_elements_to_text_custom_separator(self):
        """Test text conversion with custom separator"""
        elements = [
            ElementFactory.create_element(ElementType.TEXT, "First"),
            ElementFactory.create_element(ElementType.TEXT, "Second")
        ]
        
        text = PlainTextConverter.elements_to_text(elements, separator=" | ")
        
        assert text == "First | Second"
    
    def test_text_to_elements_basic(self):
        """Test creating elements from plain text"""
        text = "First paragraph.\n\nSecond paragraph."
        
        elements = PlainTextConverter.text_to_elements(text)
        
        assert len(elements) == 2
        assert elements[0].text == "First paragraph."
        assert elements[1].text == "Second paragraph."
        assert all(elem.element_type == ElementType.NARRATIVE_TEXT for elem in elements)
    
    def test_text_to_elements_custom_type(self):
        """Test creating elements with custom type"""
        text = "Header text"
        
        elements = PlainTextConverter.text_to_elements(
            text, 
            element_type=ElementType.HEADER
        )
        
        assert len(elements) == 1
        assert elements[0].element_type == ElementType.HEADER
    
    def test_text_to_elements_custom_splitter(self):
        """Test creating elements with custom splitter"""
        text = "First;Second;Third"
        
        elements = PlainTextConverter.text_to_elements(text, split_by=";")
        
        assert len(elements) == 3
        assert elements[0].text == "First"
        assert elements[1].text == "Second"
        assert elements[2].text == "Third"
    
    def test_text_to_elements_empty(self):
        """Test handling empty text"""
        elements = PlainTextConverter.text_to_elements("")
        
        assert len(elements) == 0


class TestUniversalConverter:
    """Test universal format converter"""
    
    def create_test_elements(self):
        """Create test elements"""
        return [
            ElementFactory.create_element(
                element_type=ElementType.TITLE,
                text="Test Title"
            )
        ]
    
    def test_auto_convert_json_hint(self):
        """Test auto-conversion with JSON hint"""
        elements = self.create_test_elements()
        json_str = JSONConverter.elements_to_json(elements)
        
        restored = UniversalConverter.auto_convert_from_string(
            json_str, 
            format_hint='json'
        )
        
        assert len(restored) == 1
        assert restored[0].element_type == ElementType.TITLE
    
    def test_auto_convert_xml_hint(self):
        """Test auto-conversion with XML hint"""
        elements = self.create_test_elements()
        xml_str = XMLConverter.elements_to_xml(elements)
        
        restored = UniversalConverter.auto_convert_from_string(
            xml_str,
            format_hint='xml'
        )
        
        assert len(restored) == 1
        assert restored[0].element_type == ElementType.TITLE
    
    def test_auto_convert_csv_hint(self):
        """Test auto-conversion with CSV hint"""
        elements = self.create_test_elements()
        csv_str = CSVConverter.elements_to_csv(elements)
        
        restored = UniversalConverter.auto_convert_from_string(
            csv_str,
            format_hint='csv'
        )
        
        assert len(restored) == 1
        assert restored[0].element_type == ElementType.TITLE
    
    def test_auto_convert_text_hint(self):
        """Test auto-conversion with text hint"""
        text = "Test paragraph text."
        
        restored = UniversalConverter.auto_convert_from_string(
            text,
            format_hint='txt'
        )
        
        assert len(restored) == 1
        assert restored[0].text == "Test paragraph text."
    
    def test_auto_detect_json(self):
        """Test auto-detection of JSON format"""
        elements = self.create_test_elements()
        json_str = JSONConverter.elements_to_json(elements)
        
        restored = UniversalConverter.auto_convert_from_string(json_str)
        
        assert len(restored) == 1
        assert restored[0].element_type == ElementType.TITLE
    
    def test_auto_detect_xml(self):
        """Test auto-detection of XML format"""
        elements = self.create_test_elements()
        xml_str = XMLConverter.elements_to_xml(elements)
        
        restored = UniversalConverter.auto_convert_from_string(xml_str)
        
        assert len(restored) == 1
        assert restored[0].element_type == ElementType.TITLE
    
    def test_auto_detect_csv(self):
        """Test auto-detection of CSV format"""
        elements = self.create_test_elements()
        csv_str = CSVConverter.elements_to_csv(elements)
        
        restored = UniversalConverter.auto_convert_from_string(csv_str)
        
        assert len(restored) == 1
        assert restored[0].element_type == ElementType.TITLE
    
    def test_auto_detect_fallback_to_text(self):
        """Test fallback to plain text when format cannot be detected"""
        text = "Just some plain text content."
        
        restored = UniversalConverter.auto_convert_from_string(text)
        
        assert len(restored) == 1
        assert restored[0].text == "Just some plain text content."
        assert restored[0].element_type == ElementType.NARRATIVE_TEXT
    
    def test_convert_elements_to_format_json(self):
        """Test converting elements to specific format - JSON"""
        elements = self.create_test_elements()
        
        result = UniversalConverter.convert_elements_to_format(
            elements, 
            'json'
        )
        
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]['element_type'] == 'Title'
    
    def test_convert_elements_to_format_xml(self):
        """Test converting elements to specific format - XML"""
        elements = self.create_test_elements()
        
        result = UniversalConverter.convert_elements_to_format(
            elements,
            'xml'
        )
        
        root = ET.fromstring(result)
        assert root.tag == 'document'
        assert len(root.findall('element')) == 1
    
    def test_convert_elements_to_format_csv(self):
        """Test converting elements to specific format - CSV"""
        elements = self.create_test_elements()
        
        result = UniversalConverter.convert_elements_to_format(
            elements,
            'csv'
        )
        
        lines = result.strip().split('\n')
        assert len(lines) == 2  # Header + 1 data row
        assert 'Title' in lines[1]
    
    def test_convert_elements_to_format_txt(self):
        """Test converting elements to specific format - Text"""
        elements = self.create_test_elements()
        
        result = UniversalConverter.convert_elements_to_format(
            elements,
            'txt'
        )
        
        assert result.strip() == "Test Title"
    
    def test_convert_elements_unsupported_format(self):
        """Test error handling for unsupported format"""
        elements = self.create_test_elements()
        
        with pytest.raises(ValueError, match="Unsupported format"):
            UniversalConverter.convert_elements_to_format(
                elements,
                'unsupported'
            )


if __name__ == "__main__":
    pytest.main([__file__])