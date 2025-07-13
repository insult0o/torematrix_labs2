#!/usr/bin/env python3
"""
Simple test to verify parser framework is working
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from tore_matrix_labs.core.parsers import (
    ParserConfiguration,
    ParsingStrategy,
    DocumentParserFactory
)
from tore_matrix_labs.core.parsers.elements import (
    TextElement,
    HeadingElement,
    TableElement,
    TableCell,
    TableRow,
    BoundingBox,
    ElementMetadata
)

def test_basic_elements():
    """Test basic element creation"""
    print("Testing basic element creation...")
    
    # Test text element
    text_elem = TextElement("This is a test text element")
    print(f"✓ Created TextElement: {text_elem.get_text()}")
    
    # Test heading element
    heading = HeadingElement("Test Heading", level=2)
    print(f"✓ Created HeadingElement (H{heading.level}): {heading.get_text()}")
    
    # Test table element
    cells = [
        TableCell("Name", 0, 0, is_header=True),
        TableCell("Value", 0, 1, is_header=True)
    ]
    header_row = TableRow(cells, 0)
    
    cells2 = [
        TableCell("Test", 1, 0),
        TableCell("123", 1, 1)
    ]
    data_row = TableRow(cells2, 1)
    
    table = TableElement([header_row, data_row], caption="Test Table")
    print(f"✓ Created TableElement with {table._row_count} rows, {table._column_count} columns")
    print(f"  Table HTML preview: {table.to_html()[:100]}...")

def test_element_serialization():
    """Test element serialization"""
    print("\nTesting element serialization...")
    
    # Create element with metadata
    bbox = BoundingBox(x0=10, y0=20, x1=110, y1=40, page=1)
    metadata = ElementMetadata(confidence=0.95, language="en")
    
    elem = TextElement(
        content="Serialization test",
        bbox=bbox,
        metadata=metadata
    )
    
    # Serialize
    data = elem.to_dict()
    print(f"✓ Serialized element to dict with {len(data)} keys")
    
    # Deserialize
    elem2 = TextElement.from_dict(data)
    print(f"✓ Deserialized element: {elem2.get_text()}")
    print(f"  Confidence: {elem2.metadata.confidence}")
    print(f"  BBox: page={elem2.bbox.page}, area={elem2.bbox.area}")

def test_parser_configuration():
    """Test parser configuration"""
    print("\nTesting parser configuration...")
    
    config = ParserConfiguration(
        strategy=ParsingStrategy.PYMUPDF,
        enable_ocr=True,
        extract_tables=True,
        quality_threshold=0.9
    )
    
    print(f"✓ Created configuration:")
    print(f"  Strategy: {config.strategy.value}")
    print(f"  OCR Enabled: {config.enable_ocr}")
    print(f"  Quality Threshold: {config.quality_threshold}")
    
    # Test merge
    config2 = ParserConfiguration(quality_threshold=0.95)
    merged = config.merge(config2)
    print(f"✓ Merged configuration quality threshold: {merged.quality_threshold}")

def test_parser_factory():
    """Test parser factory"""
    print("\nTesting parser factory...")
    
    # Check supported extensions
    extensions = DocumentParserFactory.get_supported_extensions()
    print(f"✓ Supported extensions: {', '.join(extensions[:5])}...")
    
    # Check strategies for PDF
    pdf_strategies = DocumentParserFactory.get_strategies_for_extension('.pdf')
    print(f"✓ PDF strategies: {[s.value for s in pdf_strategies]}")
    
    # Check if extension is supported
    is_supported = DocumentParserFactory.is_extension_supported('.pdf')
    print(f"✓ PDF support check: {is_supported}")

def main():
    """Run all tests"""
    print("=== TORE Matrix Labs Parser Framework Test ===\n")
    
    try:
        test_basic_elements()
        test_element_serialization()
        test_parser_configuration()
        test_parser_factory()
        
        print("\n✅ All tests passed successfully!")
        print("\nThe parser framework is ready for use.")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())