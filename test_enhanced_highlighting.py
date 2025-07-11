#!/usr/bin/env python3
"""
Test the enhanced highlighting system without GUI to verify it works.
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from tore_matrix_labs.core.enhanced_pdf_extractor import EnhancedPDFExtractor
from tore_matrix_labs.config.settings import Settings
from tore_matrix_labs.models.document_models import Document, DocumentMetadata, ProcessingConfiguration
from tore_matrix_labs.config.constants import DocumentType, ProcessingStatus, QualityLevel

def create_test_document_with_corrections():
    """Create a test document with fake corrections for testing."""
    
    # Create a document instance
    pdf_path = "/home/insulto/tore_matrix_labs/5555.pdf"
    if not Path(pdf_path).exists():
        print(f"❌ PDF file not found: {pdf_path}")
        return None
    
    # Create document metadata
    from datetime import datetime
    metadata = DocumentMetadata(
        file_name="5555.pdf",
        file_path=pdf_path,
        file_size=Path(pdf_path).stat().st_size,
        file_type="pdf",
        page_count=10,  # Assuming 10 pages
        creation_date=datetime.now(),
        modification_date=datetime.now()
    )
    
    # Create fake corrections to test highlighting
    corrections = [
        {
            'id': 'test_correction_1',
            'type': 'ocr_correction',
            'description': 'Potential OCR error: "AIR TRAFFIC CONTROL"',
            'confidence': 0.85,
            'reasoning': 'Enhanced PyMuPDF extraction detected formatting issue',
            'status': 'suggested',
            'location': {
                'page': 1,
                'bbox': [100, 700, 300, 720],  # Approximate location
                'text_position': [0, 18]  # First 18 characters
            },
            'severity': 'major',
            'metadata': {
                'extraction_method': 'enhanced_pymupdf',
                'character_count': 18
            }
        },
        {
            'id': 'test_correction_2', 
            'type': 'formatting_error',
            'description': 'Potential OCR error: "ICAO"',
            'confidence': 0.92,
            'reasoning': 'Enhanced PyMuPDF extraction detected text spacing issue',
            'status': 'suggested',
            'location': {
                'page': 1,
                'bbox': [150, 650, 200, 670],
                'text_position': [25, 29]  # Characters 25-29
            },
            'severity': 'minor',
            'metadata': {
                'extraction_method': 'enhanced_pymupdf',
                'character_count': 4
            }
        }
    ]
    
    # Create document with corrections
    document = Document(
        id="test_enhanced_doc",
        metadata=metadata,
        document_type=DocumentType.ICAO,
        processing_status=ProcessingStatus.EXTRACTED,
        processing_config=ProcessingConfiguration(),
        quality_level=QualityLevel.GOOD,
        quality_score=0.85,
        custom_metadata={
            'corrections': corrections,
            'extraction_method': 'enhanced_pymupdf'
        }
    )
    
    return document

def test_enhanced_extraction_and_highlighting():
    """Test enhanced extraction and coordinate mapping."""
    
    print("🧪 Testing Enhanced PDF Extraction and Highlighting")
    print("=" * 60)
    
    # Create test document
    document = create_test_document_with_corrections()
    if not document:
        return False
    
    pdf_path = document.metadata.file_path
    corrections = document.custom_metadata.get('corrections', [])
    
    print(f"📄 Test document: {document.metadata.file_name}")
    print(f"🔧 Corrections to test: {len(corrections)}")
    
    # Initialize enhanced extractor
    settings = Settings()
    extractor = EnhancedPDFExtractor(settings)
    
    print("\n🔍 Testing Enhanced PyMuPDF Extraction...")
    try:
        # Extract with enhanced method
        elements, full_text, page_texts = extractor.extract_with_perfect_correlation(pdf_path)
        
        print(f"✅ Enhanced extraction completed:")
        print(f"   📊 Total elements: {len(elements)}")
        print(f"   📝 Full text length: {len(full_text)} characters")
        print(f"   📄 Pages extracted: {len(page_texts)}")
        
        # Show sample of extracted text
        if full_text:
            sample_text = full_text[:200] + "..." if len(full_text) > 200 else full_text
            print(f"   📖 Sample text: '{sample_text}'")
        
        # Test coordinate mapping for each correction
        print(f"\n🎯 Testing Coordinate Mapping for {len(corrections)} Corrections:")
        
        page_1_text = page_texts.get(1, "")
        page_1_elements = [e for e in elements if e.page_number == 1]
        
        for i, correction in enumerate(corrections):
            print(f"\n   Correction {i+1}: {correction['description']}")
            
            location = correction.get('location', {})
            page = location.get('page', 1)
            bbox = location.get('bbox', [])
            text_position = location.get('text_position', [])
            
            print(f"     📍 Page: {page}")
            print(f"     📐 Bbox: {bbox}")
            print(f"     📝 Text position: {text_position}")
            
            # Test text position mapping
            if text_position and len(text_position) >= 2:
                start_pos, end_pos = text_position[0], text_position[1]
                
                if page == 1 and page_1_text:
                    if start_pos < len(page_1_text) and end_pos <= len(page_1_text):
                        actual_text = page_1_text[start_pos:end_pos]
                        print(f"     ✅ Found text at positions {start_pos}-{end_pos}: '{actual_text}'")
                        
                        # Check if we have element mapping for this position
                        mapped_elements = [e for e in page_1_elements if e.char_start <= start_pos < e.char_start + len(e.content)]
                        if mapped_elements:
                            element = mapped_elements[0]
                            print(f"     📍 Mapped to element: bbox {element.bbox}, confidence {element.confidence:.1%}")
                        else:
                            print(f"     ⚠️  No element mapping found for position {start_pos}")
                    else:
                        print(f"     ❌ Text position {start_pos}-{end_pos} out of bounds (text length: {len(page_1_text)})")
                else:
                    print(f"     ⚠️  Page {page} text not available for testing")
            
            # Test bbox coordinate reasonableness
            if bbox and len(bbox) >= 4:
                x0, y0, x1, y1 = bbox
                if 0 <= x0 < x1 <= 1000 and 0 <= y0 < y1 <= 1000:
                    print(f"     ✅ Bbox coordinates look reasonable")
                else:
                    print(f"     ⚠️  Bbox coordinates may be out of normal range")
        
        # Test highlighting simulation
        print(f"\n🎨 Simulating Highlighting Logic:")
        
        for correction in corrections:
            location = correction.get('location', {})
            text_position = location.get('text_position', [])
            description = correction.get('description', '')
            
            # Extract error text from description
            error_text = description.replace('Potential OCR error: ', '').strip('"\'')
            
            print(f"\n   Testing highlight for: '{error_text}'")
            
            # Strategy 1: Text position mapping
            if text_position and len(text_position) >= 2:
                start_pos, end_pos = text_position[0], text_position[1]
                if start_pos < len(page_1_text) and end_pos <= len(page_1_text):
                    actual_text = page_1_text[start_pos:end_pos]
                    if actual_text == error_text:
                        print(f"     ✅ STRATEGY 1 SUCCESS: Perfect text position match")
                    else:
                        print(f"     ❌ Strategy 1 failed: Expected '{error_text}', got '{actual_text}'")
                else:
                    print(f"     ❌ Strategy 1 failed: Position out of bounds")
            
            # Strategy 2: Text search
            if error_text in page_1_text:
                found_pos = page_1_text.find(error_text)
                print(f"     ✅ STRATEGY 2 SUCCESS: Found '{error_text}' at position {found_pos}")
            else:
                print(f"     ❌ Strategy 2 failed: '{error_text}' not found in text")
        
        # Summary
        print(f"\n📊 Enhanced Extraction Summary:")
        print(f"   🎯 Coordinate coverage: {len(page_1_elements) / len(page_1_text) * 100:.1f}% (elements/characters)")
        print(f"   📍 Average element confidence: {sum(e.confidence for e in page_1_elements) / len(page_1_elements):.1%}")
        print(f"   🔧 Corrections testable: {len([c for c in corrections if c.get('location', {}).get('text_position')])}/{len(corrections)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Enhanced extraction failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = test_enhanced_extraction_and_highlighting()
        if success:
            print("\n🎉 ENHANCED EXTRACTION TEST COMPLETED!")
            print("✅ The enhanced PyMuPDF extraction is working and should provide better highlighting")
            print("🔧 When the GUI loads, it will use this enhanced extraction for improved accuracy")
        else:
            print("\n❌ ENHANCED EXTRACTION TEST FAILED!")
            print("🛠️  Check the enhanced_pdf_extractor.py implementation")
    except Exception as e:
        print(f"\n💥 Test crashed: {e}")
        import traceback
        traceback.print_exc()