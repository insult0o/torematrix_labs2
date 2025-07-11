#!/usr/bin/env python3
"""
Test to reproduce the page number issue with debug output.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_page_number_issue():
    """Test to reproduce the page number issue."""
    print("🔍 TESTING PAGE NUMBER ISSUE")
    print("=" * 50)
    
    try:
        from tore_matrix_labs.config.settings import Settings
        from tore_matrix_labs.models.document_models import Document, DocumentMetadata
        
        # Create a mock document
        file_path = "/home/insulto/tore_matrix_labs/5555.pdf"
        if not Path(file_path).exists():
            print(f"❌ Test file not found: {file_path}")
            return
        
        # Create document metadata
        from datetime import datetime
        metadata = DocumentMetadata(
            file_path=file_path,
            file_name="5555.pdf",
            file_size=1024,
            file_type="application/pdf",
            page_count=55,
            creation_date=datetime.now(),
            modification_date=datetime.now()
        )
        
        # Create document
        from tore_matrix_labs.models.document_models import ProcessingConfiguration
        from tore_matrix_labs.config.constants import DocumentType, ProcessingStatus, QualityLevel
        
        processing_config = ProcessingConfiguration()
        
        document = Document(
            id="test-doc-1",
            metadata=metadata,
            document_type=DocumentType.REGULATORY,
            processing_status=ProcessingStatus.APPROVED,
            processing_config=processing_config,
            quality_level=QualityLevel.EXCELLENT,
            quality_score=0.95,
            custom_metadata={}
        )
        
        # Mock corrections with page 1
        mock_corrections = [
            {
                'id': 'text_issue_1',
                'type': 'ocr_correction',
                'description': 'OCR may have misread "procedural" as "proccdural" - please verify spelling',
                'original_text': 'proccdural guidance',
                'suggested_fix': 'procedural guidance',
                'confidence': 0.8,
                'reasoning': 'Text processing found potential OCR spelling errors in non-excluded areas',
                'status': 'suggested',
                'location': {
                    'page': 1,  # This should be correct
                    'paragraph': 1,
                    'bbox': [100, 200, 400, 220],
                    'text_position': {'start': 0, 'end': 17}
                },
                'severity': 'medium'
            }
        ]
        
        document.custom_metadata['corrections'] = mock_corrections
        
        print(f"📄 Created document with {len(mock_corrections)} corrections")
        print(f"   Correction page: {mock_corrections[0]['location']['page']}")
        
        # Test page validation widget loading
        from tore_matrix_labs.ui.components.page_validation_widget import PageValidationWidget
        settings = Settings()
        
        # Create widget (this will fail due to Qt, but we can test the logic)
        try:
            widget = PageValidationWidget(settings)
            print("✅ PageValidationWidget created successfully")
            
            # Test document loading
            widget.load_document_for_validation(document)
            print("✅ Document loaded successfully")
            
            # Check the page number state
            print(f"   Current page: {widget.current_page}")
            print(f"   Total pages: {widget.total_pages}")
            print(f"   Corrections by page: {list(widget.corrections_by_page.keys())}")
            
            # Check if current page is correct
            if widget.current_page == 1:
                print("✅ Current page is correct (1)")
            else:
                print(f"❌ Current page is wrong: {widget.current_page}")
                
        except Exception as e:
            print(f"❌ Qt widget creation failed (expected): {e}")
            
            # Still test the logic parts
            from tore_matrix_labs.ui.components.page_validation_widget import PageValidationWidget
            
            # Create a mock widget state
            current_page = 1
            corrections_by_page = {}
            
            # Process corrections like the widget does
            for correction in mock_corrections:
                page = correction.get('location', {}).get('page', 1)
                if page not in corrections_by_page:
                    corrections_by_page[page] = []
                corrections_by_page[page].append(correction)
            
            print(f"   Corrections by page: {list(corrections_by_page.keys())}")
            
            if corrections_by_page:
                first_page = min(corrections_by_page.keys())
                current_page = first_page
                print(f"   First page with corrections: {first_page}")
                print(f"   Current page set to: {current_page}")
                
                # This should be 1, not 0
                if current_page == 1:
                    print("✅ Page number logic is correct")
                else:
                    print(f"❌ Page number logic is wrong: {current_page}")
            
        print("\n🔍 TESTING ENHANCED EXTRACTION")
        print("=" * 50)
        
        # Test enhanced extraction directly
        from tore_matrix_labs.core.enhanced_pdf_extractor import EnhancedPDFExtractor
        
        extractor = EnhancedPDFExtractor(settings)
        elements, full_text, page_texts = extractor.extract_with_perfect_correlation(file_path)
        
        print(f"✅ Enhanced extraction successful")
        print(f"   Elements: {len(elements)}")
        print(f"   Full text length: {len(full_text)}")
        print(f"   Page texts keys: {list(page_texts.keys())}")
        
        # Test accessing page 1
        if 1 in page_texts:
            print("✅ Page 1 found in extraction")
            print(f"   Page 1 text length: {len(page_texts[1])}")
        else:
            print("❌ Page 1 NOT found in extraction")
            
        # Test accessing page 0 (should fail)
        if 0 in page_texts:
            print("❌ Page 0 found in extraction (this is wrong)")
        else:
            print("✅ Page 0 NOT found in extraction (this is correct)")
            
        print("\n🔍 CONCLUSION")
        print("=" * 50)
        
        # The issue is likely that somewhere, page 1 gets converted to page 0
        # Let's check the debug output to see where this happens
        print("The page numbering issue might be in the coordinate correspondence system")
        print("or when the page number gets passed between components.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_page_number_issue()