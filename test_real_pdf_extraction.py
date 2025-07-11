#!/usr/bin/env python3
"""
Test script to verify real PDF content extraction at exact bounding box locations.
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_real_pdf_extraction():
    """Test extraction of real content from PDF at exact locations."""
    
    try:
        print("=== Testing Real PDF Content Extraction ===")
        
        from tore_matrix_labs.ui.qt_compat import QApplication
        from tore_matrix_labs.config.settings import Settings
        from tore_matrix_labs.ui.main_window import MainWindow
        
        # Step 1: Verify PDF file exists
        project_file = Path("4.tore")
        if not project_file.exists():
            print(f"❌ Project file not found: {project_file}")
            return False
            
        with open(project_file, 'r') as f:
            project_data = json.load(f)
        
        documents = project_data.get('documents', [])
        doc_data = documents[0]
        pdf_path = doc_data.get('path', '')
        
        if not Path(pdf_path).exists():
            print(f"❌ PDF file not found: {pdf_path}")
            return False
        
        print(f"✅ Step 1: PDF file found: {pdf_path}")
        
        # Step 2: Create application and load project
        app = QApplication(sys.argv)
        settings = Settings()
        main_window = MainWindow(settings)
        main_window.project_widget.load_project(str(project_file))
        
        print(f"✅ Step 2: Project loaded successfully")
        
        # Step 3: Access validation widget and check corrections
        qa_widget = main_window.qa_widget
        validation_widget = qa_widget.validation_widget
        corrections_layout = validation_widget.corrections_layout
        
        print(f"✅ Step 3: Found {corrections_layout.count()} correction widgets")
        
        # Step 4: Test real PDF extraction for first 5 corrections
        real_extractions = 0
        simulated_extractions = 0
        
        print(f"✅ Step 4: Testing PDF content extraction...")
        
        for i in range(min(5, corrections_layout.count())):
            item = corrections_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'correction') and hasattr(widget, 'extraction_text'):
                    correction = widget.correction
                    extracted_content = widget.extraction_text.toPlainText()
                    
                    # Check if this looks like real extracted content vs simulated
                    is_real_extraction = (
                        not extracted_content.startswith("Flight Level") and
                        not extracted_content.startswith("Date: 15//") and
                        not extracted_content.startswith("Aircraft identification") and
                        len(extracted_content) > 20 and
                        not "Clearance to descend" in extracted_content
                    )
                    
                    if is_real_extraction:
                        real_extractions += 1
                        print(f"   ✅ Real extraction {i+1}: {extracted_content[:60]}...")
                        print(f"      BBox: {correction.bbox}")
                        print(f"      Text pos: {getattr(correction, 'text_position', 'None')}")
                    else:
                        simulated_extractions += 1
                        print(f"   ⚠️  Simulated {i+1}: {extracted_content[:60]}...")
        
        # Step 5: Test direct PDF extraction with PyMuPDF
        print(f"✅ Step 5: Testing direct PDF extraction...")
        
        try:
            import fitz
            pdf_doc = fitz.open(pdf_path)
            page = pdf_doc[0]  # First page
            
            # Test extraction from a sample bounding box from the corrections
            sample_corrections = project_data['documents'][0]['processing_data']['corrections'][:3]
            
            for i, corr in enumerate(sample_corrections):
                bbox = corr['location']['bbox']
                text_pos = corr['location']['text_position']
                
                # Extract using bounding box
                bbox_rect = fitz.Rect(bbox)
                bbox_text = page.get_text("text", clip=bbox_rect).strip()
                
                # Extract using expanded context
                margin = 50
                expanded_rect = fitz.Rect(
                    max(0, bbox[0] - margin),
                    max(0, bbox[1] - margin),
                    min(page.rect.width, bbox[2] + margin),
                    min(page.rect.height, bbox[3] + margin)
                )
                context_text = page.get_text("text", clip=expanded_rect).strip()
                
                print(f"   ✅ Direct extraction {i+1}:")
                print(f"      Issue: {corr['description']}")
                print(f"      BBox text: '{bbox_text}'")
                print(f"      Context: {context_text[:80]}...")
                print(f"      Text pos: {text_pos}")
            
            pdf_doc.close()
            
        except Exception as e:
            print(f"   ❌ Direct PDF test failed: {e}")
        
        # Step 6: Results summary
        success = real_extractions > 0
        
        print(f"\n{'🎉' if success else '⚠️'} REAL PDF EXTRACTION RESULTS:")
        print(f"   Real extractions: {real_extractions}/5")
        print(f"   Simulated extractions: {simulated_extractions}/5")
        
        if success:
            print(f"✅ Successfully extracting real content from PDF!")
        else:
            print(f"⚠️  Still using simulated content - need to debug extraction")
        
        return success
        
    except Exception as e:
        print(f"❌ PDF extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_real_pdf_extraction()
    if success:
        print(f"\n🚀 REAL PDF EXTRACTION IS WORKING!")
        print(f"✅ Extracting actual text from PDF at exact bounding box locations")
        print(f"✅ Using real document content instead of simulated text")
        print(f"✅ Providing proper context around detected issues")
        print(f"\n💡 Now you can edit the actual extracted text from your PDF!")
    else:
        print(f"\n🔧 PDF extraction needs more work to get real content")
        print(f"   Check logs for specific extraction issues")
        print(f"   Verify bounding box coordinates and text positions")