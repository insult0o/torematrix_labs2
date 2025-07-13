"""
Tests for V1 .tore format backward compatibility

This test suite specifically validates Issue #2 AC4:
"Backward compatibility with V1 .tore format"
"""

import pytest
import json
import tempfile
import os
from typing import Dict, Any

from src.torematrix.core.models.element import Element, ElementType
from src.torematrix.core.models.metadata import ElementMetadata
from src.torematrix.core.models.complex_types import (
    TableElement, ImageElement, FormulaElement, CodeBlockElement
)
from src.torematrix.core.models.compatibility import ToreV1Converter, ToreFileHandler


class TestV1CompatibilityComprehensive:
    """Comprehensive tests for V1 .tore format compatibility"""
    
    def test_v1_basic_elements_conversion(self):
        """Test conversion of basic V1 elements"""
        v1_data = {
            "version": "1.0",
            "created_at": "2024-01-15T10:30:00Z",
            "elements": [
                {
                    "id": "title-001",
                    "type": "title",
                    "text": "Document Title",
                    "confidence": 0.95,
                    "page_number": 1
                },
                {
                    "id": "text-001",
                    "type": "narrative_text",
                    "text": "This is the main content.",
                    "confidence": 0.92,
                    "page_number": 1,
                    "parent_id": "title-001"
                },
                {
                    "id": "header-001",
                    "type": "header",
                    "text": "Section Header",
                    "confidence": 0.88,
                    "page_number": 2
                },
                {
                    "id": "footer-001",
                    "type": "footer",
                    "text": "Page Footer",
                    "confidence": 0.85,
                    "page_number": 2
                },
                {
                    "id": "list-001",
                    "type": "list_item",
                    "text": "• First item",
                    "confidence": 0.90,
                    "page_number": 2
                }
            ]
        }
        
        # Convert from V1
        elements = ToreV1Converter.from_v1_format(v1_data)
        
        assert len(elements) == 5
        
        # Verify title
        title = elements[0]
        assert title.element_type == ElementType.TITLE
        assert title.text == "Document Title"
        assert title.metadata.confidence == 0.95
        assert title.metadata.page_number == 1
        assert title.metadata.detection_method == "v1_migration"
        
        # Verify narrative text with parent
        text = elements[1]
        assert text.element_type == ElementType.NARRATIVE_TEXT
        assert text.text == "This is the main content."
        assert text.parent_id == "title-001"
        assert text.metadata.confidence == 0.92
        
        # Verify other types
        header = elements[2]
        assert header.element_type == ElementType.HEADER
        assert header.text == "Section Header"
        
        footer = elements[3]
        assert footer.element_type == ElementType.FOOTER
        assert footer.text == "Page Footer"
        
        list_item = elements[4]
        assert list_item.element_type == ElementType.LIST_ITEM
        assert list_item.text == "• First item"
    
    def test_v1_coordinates_conversion(self):
        """Test V1 coordinates (bbox) conversion"""
        v1_data = {
            "version": "1.0",
            "elements": [
                {
                    "id": "coord-test",
                    "type": "title",
                    "text": "Title with coordinates",
                    "bbox": {
                        "layout_bbox": [10, 20, 200, 50],
                        "text_bbox": [12, 22, 198, 48],
                        "points": [[10, 20], [200, 50]],
                        "system": "pixel"
                    },
                    "confidence": 0.95
                }
            ]
        }
        
        elements = ToreV1Converter.from_v1_format(v1_data)
        element = elements[0]
        
        assert element.metadata.coordinates is not None
        assert element.metadata.coordinates.layout_bbox == (10, 20, 200, 50)
        assert element.metadata.coordinates.text_bbox == (12, 22, 198, 48)
        assert element.metadata.coordinates.points == [(10, 20), (200, 50)]
        assert element.metadata.coordinates.system == "pixel"
    
    def test_v1_table_conversion(self):
        """Test V1 table element conversion"""
        v1_data = {
            "version": "1.0",
            "elements": [
                {
                    "id": "table-001",
                    "type": "table",
                    "text": "Financial Summary Table",
                    "cells": [
                        ["Quarter", "Revenue", "Profit"],
                        ["Q1 2024", "$100M", "$15M"],
                        ["Q2 2024", "$120M", "$18M"],
                        ["Q3 2024", "$110M", "$16M"]
                    ],
                    "headers": ["Quarter", "Revenue", "Profit"],
                    "table_type": "financial",
                    "confidence": 0.88,
                    "page_number": 3
                }
            ]
        }
        
        elements = ToreV1Converter.from_v1_format(v1_data)
        table = elements[0]
        
        assert isinstance(table, TableElement)
        assert table.element_type == ElementType.TABLE
        assert table.text == "Financial Summary Table"
        assert table.cells == [
            ["Quarter", "Revenue", "Profit"],
            ["Q1 2024", "$100M", "$15M"],
            ["Q2 2024", "$120M", "$18M"],
            ["Q3 2024", "$110M", "$16M"]
        ]
        assert table.headers == ["Quarter", "Revenue", "Profit"]
        assert table.table_metadata.table_type == "financial"
        assert table.table_metadata.num_rows == 4
        assert table.table_metadata.num_cols == 3
        assert table.table_metadata.has_header == True
    
    def test_v1_image_conversion(self):
        """Test V1 image element conversion"""
        v1_data = {
            "version": "1.0",
            "elements": [
                {
                    "id": "image-001",
                    "type": "image",
                    "text": "Chart showing quarterly performance",
                    "alt_text": "Quarterly performance chart",
                    "caption": "Figure 1: Q1-Q3 2024 Performance",
                    "width": 800,
                    "height": 600,
                    "format": "PNG",
                    "dpi": 300,
                    "image_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ",
                    "image_url": "https://example.com/chart.png",
                    "confidence": 0.85,
                    "page_number": 4
                }
            ]
        }
        
        elements = ToreV1Converter.from_v1_format(v1_data)
        image = elements[0]
        
        assert isinstance(image, ImageElement)
        assert image.element_type == ElementType.IMAGE
        assert image.text == "Chart showing quarterly performance"
        assert image.alt_text == "Quarterly performance chart"
        assert image.caption == "Figure 1: Q1-Q3 2024 Performance"
        assert image.image_data == "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
        assert image.image_url == "https://example.com/chart.png"
        assert image.image_metadata.width == 800
        assert image.image_metadata.height == 600
        assert image.image_metadata.format == "PNG"
        assert image.image_metadata.dpi == 300
    
    def test_v1_formula_conversion(self):
        """Test V1 formula element conversion"""
        v1_data = {
            "version": "1.0",
            "elements": [
                {
                    "id": "formula-001",
                    "type": "formula",
                    "text": "E = mc²",
                    "latex": "E = mc^2",
                    "mathml": "<math><mrow><mi>E</mi><mo>=</mo><mi>m</mi><msup><mi>c</mi><mn>2</mn></msup></mrow></math>",
                    "formula_type": "equation",
                    "confidence": 0.92,
                    "page_number": 5
                }
            ]
        }
        
        elements = ToreV1Converter.from_v1_format(v1_data)
        formula = elements[0]
        
        assert isinstance(formula, FormulaElement)
        assert formula.element_type == ElementType.FORMULA
        assert formula.text == "E = mc²"
        assert formula.latex == "E = mc^2"
        assert formula.mathml == "<math><mrow><mi>E</mi><mo>=</mo><mi>m</mi><msup><mi>c</mi><mn>2</mn></msup></mrow></math>"
        assert formula.formula_metadata.formula_type.value == "equation"
    
    def test_v1_code_block_conversion(self):
        """Test V1 code block element conversion"""
        v1_data = {
            "version": "1.0",
            "elements": [
                {
                    "id": "code-001",
                    "type": "code_block",
                    "text": "def hello_world():\n    print('Hello, World!')",
                    "language": "python",
                    "confidence": 0.90,
                    "page_number": 6
                }
            ]
        }
        
        elements = ToreV1Converter.from_v1_format(v1_data)
        code = elements[0]
        
        assert isinstance(code, CodeBlockElement)
        assert code.element_type == ElementType.CODE_BLOCK
        assert code.text == "def hello_world():\n    print('Hello, World!')"
        assert code.code_metadata.language.value == "python"
        assert code.code_metadata.line_count == 2
    
    def test_v1_custom_fields_preservation(self):
        """Test that V1-specific fields are preserved in custom_fields"""
        v1_data = {
            "version": "1.0",
            "elements": [
                {
                    "id": "custom-001",
                    "type": "title",
                    "text": "Title with custom fields",
                    "confidence": 0.95,
                    "source_document": "original.pdf",
                    "extraction_tool": "pdf_parser_v1",
                    "processing_timestamp": "2024-01-15T10:30:00Z",
                    "custom_score": 0.88,
                    "flags": ["important", "verified"]
                }
            ]
        }
        
        elements = ToreV1Converter.from_v1_format(v1_data)
        element = elements[0]
        
        # Check that custom fields are preserved with v1_ prefix
        custom_fields = element.metadata.custom_fields
        assert custom_fields["v1_source_document"] == "original.pdf"
        assert custom_fields["v1_extraction_tool"] == "pdf_parser_v1"
        assert custom_fields["v1_processing_timestamp"] == "2024-01-15T10:30:00Z"
        assert custom_fields["v1_custom_score"] == 0.88
        assert custom_fields["v1_flags"] == ["important", "verified"]
    
    def test_v3_to_v1_conversion_roundtrip(self):
        """Test V3 to V1 conversion (round-trip)"""
        # Create V3 elements
        from src.torematrix.core.models.factory import ElementFactory
        from src.torematrix.core.models.complex_types import create_table, create_image
        
        elements = [
            ElementFactory.create_element(
                ElementType.TITLE,
                "V3 Title",
                metadata={
                    "confidence": 0.95,
                    "page_number": 1,
                    "custom_fields": {"source": "v3_test"}
                }
            ),
            create_table(
                cells=[["Name", "Value"], ["Test", "123"]],
                headers=["Name", "Value"]
            ),
            create_image(
                alt_text="Test image",
                image_data="base64data"
            )
        ]
        
        # Convert to V1
        v1_data = ToreV1Converter.to_v1_format(elements)
        
        # Verify V1 structure
        assert v1_data["version"] == "1.0"
        assert "migrated_from" in v1_data
        assert v1_data["migrated_from"] == "v3"
        assert len(v1_data["elements"]) == 3
        
        # Check title conversion
        v1_title = v1_data["elements"][0]
        assert v1_title["type"] == "title"
        assert v1_title["text"] == "V3 Title"
        assert v1_title["confidence"] == 0.95
        assert v1_title["page_number"] == 1
        
        # Check table conversion
        v1_table = v1_data["elements"][1]
        assert v1_table["type"] == "table"
        assert v1_table["cells"] == [["Name", "Value"], ["Test", "123"]]
        assert v1_table["headers"] == ["Name", "Value"]
        
        # Check image conversion
        v1_image = v1_data["elements"][2]
        assert v1_image["type"] == "image"
        assert v1_image["alt_text"] == "Test image"
        assert v1_image["image_data"] == "base64data"
        
        # Test round-trip: V3 -> V1 -> V3
        converted_back = ToreV1Converter.from_v1_format(v1_data)
        assert len(converted_back) == 3
        assert converted_back[0].element_type == ElementType.TITLE
        assert converted_back[0].text == "V3 Title"
    
    def test_v1_file_operations(self):
        """Test .tore file operations with V1 format"""
        from src.torematrix.core.models.factory import ElementFactory
        
        # Create test elements
        elements = [
            ElementFactory.create_element(
                ElementType.TITLE,
                "File Test Document",
                metadata={"confidence": 0.95, "page_number": 1}
            ),
            ElementFactory.create_element(
                ElementType.NARRATIVE_TEXT,
                "This is test content for file operations.",
                metadata={"confidence": 0.90, "page_number": 1}
            )
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test saving as V1 format
            v1_file_path = os.path.join(temp_dir, "test_v1.tore")
            ToreFileHandler.save_tore_file(elements, v1_file_path, format_version="v1")
            
            # Verify file exists and is valid JSON
            assert os.path.exists(v1_file_path)
            
            with open(v1_file_path, 'r') as f:
                v1_content = json.load(f)
            
            assert v1_content["version"] == "1.0"
            assert len(v1_content["elements"]) == 2
            
            # Test loading V1 file
            loaded_elements = ToreFileHandler.load_tore_file(v1_file_path)
            
            assert len(loaded_elements) == 2
            assert loaded_elements[0].element_type == ElementType.TITLE
            assert loaded_elements[0].text == "File Test Document"
            assert loaded_elements[1].element_type == ElementType.NARRATIVE_TEXT
            assert loaded_elements[1].text == "This is test content for file operations."
            
            # Test V3 format for comparison
            v3_file_path = os.path.join(temp_dir, "test_v3.tore")
            ToreFileHandler.save_tore_file(elements, v3_file_path, format_version="v3")
            
            loaded_v3_elements = ToreFileHandler.load_tore_file(v3_file_path)
            
            # Both should load the same data
            assert len(loaded_v3_elements) == len(loaded_elements)
            assert loaded_v3_elements[0].text == loaded_elements[0].text
    
    def test_v1_format_detection(self):
        """Test automatic V1 format detection"""
        # Create V1 format data
        v1_content = {
            "version": "1.0",
            "elements": [
                {"id": "test", "type": "title", "text": "Auto-detected V1"}
            ]
        }
        
        # Create V3 format data
        from src.torematrix.core.models.factory import ElementFactory
        v3_element = ElementFactory.create_element(ElementType.TITLE, "V3 Title")
        v3_content = {
            "version": "3.0",
            "format": "unified_element_model",
            "elements": [v3_element.to_dict()]
        }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save both formats
            v1_path = os.path.join(temp_dir, "v1_format.tore")
            v3_path = os.path.join(temp_dir, "v3_format.tore")
            
            with open(v1_path, 'w') as f:
                json.dump(v1_content, f)
            
            with open(v3_path, 'w') as f:
                json.dump(v3_content, f)
            
            # Test automatic detection
            v1_loaded = ToreFileHandler.load_tore_file(v1_path)
            v3_loaded = ToreFileHandler.load_tore_file(v3_path)
            
            # Both should load successfully
            assert len(v1_loaded) == 1
            assert len(v3_loaded) == 1
            
            # Both should have the same element type
            assert v1_loaded[0].element_type == ElementType.TITLE
            assert v3_loaded[0].element_type == ElementType.TITLE
    
    def test_v1_error_handling(self):
        """Test error handling for invalid V1 data"""
        # Test invalid V1 structure
        invalid_v1_cases = [
            {},  # Empty data
            {"version": "1.0"},  # Missing elements
            {"elements": []},  # Missing version
            {"version": "2.0", "elements": []},  # Wrong version
            {
                "version": "1.0",
                "elements": [
                    {"type": "title", "text": "Missing ID"}  # Missing required ID
                ]
            },
            {
                "version": "1.0", 
                "elements": [
                    {"id": "test", "text": "Missing type"}  # Missing required type
                ]
            }
        ]
        
        for i, invalid_data in enumerate(invalid_v1_cases):
            with pytest.raises(ValueError, match="Failed to convert V1 format"):
                ToreV1Converter.from_v1_format(invalid_data)
    
    def test_v1_element_type_mapping(self):
        """Test comprehensive element type mapping between V1 and V3"""
        # Test all supported V1 element types
        v1_types = [
            "title", "narrative_text", "list_item", "header", "footer",
            "text", "table", "table_row", "table_cell", "image", "figure",
            "figure_caption", "formula", "address", "email_address",
            "page_break", "page_number", "uncategorized_text", "code_block",
            "list", "composite_element", "table_of_contents"
        ]
        
        v1_data = {
            "version": "1.0",
            "elements": [
                {"id": f"elem-{i}", "type": v1_type, "text": f"Test {v1_type}"}
                for i, v1_type in enumerate(v1_types)
            ]
        }
        
        elements = ToreV1Converter.from_v1_format(v1_data)
        
        # Verify all types are converted
        assert len(elements) == len(v1_types)
        
        # Check specific mappings
        type_mapping = ToreV1Converter.V1_TYPE_MAPPING
        for i, v1_type in enumerate(v1_types):
            expected_v3_type = type_mapping.get(v1_type, ElementType.NARRATIVE_TEXT)
            assert elements[i].element_type == expected_v3_type, f"Type {v1_type} mapped incorrectly"
    
    def test_v1_large_document_compatibility(self):
        """Test V1 compatibility with large documents"""
        # Create a large V1 document
        large_v1_data = {
            "version": "1.0",
            "created_at": "2024-01-15T10:30:00Z",
            "elements": []
        }
        
        # Add 1000 elements of various types
        element_types = ["title", "narrative_text", "list_item", "table", "image"]
        for i in range(1000):
            element_type = element_types[i % len(element_types)]
            element = {
                "id": f"elem-{i:04d}",
                "type": element_type,
                "text": f"Element {i} content",
                "confidence": 0.9 + (i % 10) * 0.01,
                "page_number": (i // 50) + 1
            }
            
            # Add type-specific fields
            if element_type == "table":
                element["cells"] = [["Header"], [f"Row {i}"]]
                element["headers"] = ["Header"]
            elif element_type == "image":
                element["alt_text"] = f"Image {i} description"
                element["width"] = 400 + (i % 100)
                element["height"] = 300 + (i % 50)
            
            large_v1_data["elements"].append(element)
        
        # Test conversion
        import time
        start_time = time.time()
        
        converted_elements = ToreV1Converter.from_v1_format(large_v1_data)
        
        conversion_time = time.time() - start_time
        
        # Verify results
        assert len(converted_elements) == 1000
        assert conversion_time < 10.0, f"Conversion took {conversion_time}s, should be < 10s"
        
        # Verify data integrity for sample elements
        for i in [0, 100, 500, 999]:
            element = converted_elements[i]
            assert element.text == f"Element {i} content"
            assert abs(element.metadata.confidence - (0.9 + (i % 10) * 0.01)) < 0.001
            assert element.metadata.page_number == (i // 50) + 1
        
        print(f"✅ Large document conversion: 1000 elements in {conversion_time:.3f}s")


def test_v1_compatibility_acceptance_criteria():
    """
    Final test that validates AC4: Backward compatibility with V1 .tore format
    """
    print("\n🧪 Testing V1 .tore format backward compatibility...")
    
    # Sample V1 document with all major features
    comprehensive_v1_data = {
        "version": "1.0",
        "created_at": "2024-01-15T10:30:00Z",
        "metadata": {
            "source": "comprehensive_test.pdf",
            "total_pages": 5
        },
        "elements": [
            # Basic text elements
            {
                "id": "title-001",
                "type": "title",
                "text": "Comprehensive Test Document",
                "confidence": 0.98,
                "page_number": 1,
                "bbox": {
                    "layout_bbox": [50, 50, 500, 100],
                    "system": "pixel"
                }
            },
            # Complex table
            {
                "id": "table-001",
                "type": "table",
                "text": "Performance Data",
                "cells": [
                    ["Metric", "Q1", "Q2", "Q3"],
                    ["Revenue", "$1M", "$1.2M", "$1.1M"],
                    ["Profit", "$200K", "$250K", "$220K"]
                ],
                "headers": ["Metric", "Q1", "Q2", "Q3"],
                "confidence": 0.92,
                "page_number": 2
            },
            # Image with metadata
            {
                "id": "image-001",
                "type": "image",
                "text": "Performance Chart",
                "alt_text": "Chart showing quarterly performance",
                "width": 600,
                "height": 400,
                "image_data": "base64imagedata",
                "confidence": 0.88,
                "page_number": 3
            },
            # Formula
            {
                "id": "formula-001",
                "type": "formula",
                "text": "Einstein's equation",
                "latex": "E = mc^2",
                "formula_type": "equation",
                "confidence": 0.95,
                "page_number": 4
            }
        ]
    }
    
    # Test conversion
    converted_elements = ToreV1Converter.from_v1_format(comprehensive_v1_data)
    
    # Verify conversion success
    assert len(converted_elements) == 4
    print(f"✅ Converted {len(converted_elements)} elements from V1 format")
    
    # Verify element types and data integrity
    title = converted_elements[0]
    assert title.element_type == ElementType.TITLE
    assert title.text == "Comprehensive Test Document"
    assert title.metadata.confidence == 0.98
    assert title.metadata.coordinates.layout_bbox == (50, 50, 500, 100)
    
    table = converted_elements[1]
    assert isinstance(table, TableElement)
    assert table.cells[1][1] == "$1M"  # Check data preservation
    
    image = converted_elements[2]
    assert isinstance(image, ImageElement)
    assert image.image_metadata.width == 600
    
    formula = converted_elements[3]
    assert isinstance(formula, FormulaElement)
    assert formula.latex == "E = mc^2"
    
    # Test round-trip conversion
    v1_converted_back = ToreV1Converter.to_v1_format(converted_elements)
    round_trip_elements = ToreV1Converter.from_v1_format(v1_converted_back)
    
    assert len(round_trip_elements) == len(converted_elements)
    print("✅ Round-trip conversion successful")
    
    # Test file operations
    with tempfile.TemporaryDirectory() as temp_dir:
        v1_file = os.path.join(temp_dir, "v1_test.tore")
        
        # Save in V1 format
        ToreFileHandler.save_tore_file(converted_elements, v1_file, format_version="v1")
        
        # Load from V1 format
        loaded_elements = ToreFileHandler.load_tore_file(v1_file)
        
        assert len(loaded_elements) == 4
        assert loaded_elements[0].text == "Comprehensive Test Document"
        print("✅ File operations successful")
    
    print("🎉 AC4: V1 .tore format backward compatibility VERIFIED!")
    return True