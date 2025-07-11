#!/usr/bin/env python3
"""
Test the QA validation workflow to reproduce the error.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_qa_workflow():
    """Test the QA validation workflow."""
    print("🔍 TESTING QA VALIDATION WORKFLOW")
    print("=" * 60)
    
    try:
        from tore_matrix_labs.config.settings import Settings
        from tore_matrix_labs.models.document_models import Document, DocumentMetadata, ProcessingConfiguration
        from tore_matrix_labs.config.constants import DocumentType, ProcessingStatus, QualityLevel
        from datetime import datetime
        
        # Create test document
        file_path = "/home/insulto/tore_matrix_labs/5555.pdf"
        if not Path(file_path).exists():
            print(f"❌ Test file not found: {file_path}")
            return
        
        # Create document metadata
        metadata = DocumentMetadata(
            file_path=file_path,
            file_name="5555.pdf",
            file_size=1024,
            file_type="application/pdf",
            page_count=55,
            creation_date=datetime.now(),
            modification_date=datetime.now()
        )
        
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
        
        # Add mock corrections
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
                    'page': 1,
                    'paragraph': 1,
                    'bbox': [100, 200, 400, 220],
                    'text_position': {'start': 0, 'end': 17}
                },
                'severity': 'medium'
            }
        ]
        
        document.custom_metadata['corrections'] = mock_corrections
        
        print(f"📄 Created document with {len(mock_corrections)} corrections")
        
        # Test page validation widget loading (this is what happens in the main window)
        print("\n🔍 Testing PageValidationWidget.load_document_for_validation")
        
        settings = Settings()
        
        # Mock the page validation widget without Qt
        class MockPageValidationWidget:
            def __init__(self, settings):
                self.settings = settings
                self.current_document = None
                self.post_processing_result = None
                self._current_page = 1
                self.total_pages = 0
                self.current_page_issues = []
                self.current_issue_index = 0
                self.corrections_by_page = {}
                
                # Mock extractors
                from tore_matrix_labs.core.enhanced_pdf_extractor import EnhancedPDFExtractor
                self.enhanced_extractor = EnhancedPDFExtractor(settings)
                
                # Mock extraction strategy
                self.use_unstructured = False
                self.use_ocr = False
                self.use_enhanced = True
                
                # Mock UI elements
                self.extracted_text = MockTextEdit()
                self.log_messages = []
                
            @property
            def current_page(self):
                return self._current_page
            
            @current_page.setter
            def current_page(self, value):
                if value <= 0:
                    print(f"WARNING: Attempted to set current_page to {value}, correcting to 1")
                    self._current_page = 1
                else:
                    self._current_page = value
                print(f"Current page set to: {self._current_page}")
                
            def log_message_emit(self, message):
                self.log_messages.append(message)
                print(f"LOG: {message}")
                
            def load_document_for_validation(self, document, post_processing_result=None):
                print(f"Loading document for validation: {document.metadata.file_name}")
                
                self.current_document = document
                self.post_processing_result = post_processing_result
                
                # Extract corrections from document
                corrections = document.custom_metadata.get('corrections', [])
                
                # Group corrections by page 
                self.corrections_by_page = {}
                for correction in corrections:
                    page = correction.get('location', {}).get('page', 1)
                    print(f"Processing correction with page: {page}")
                    if page not in self.corrections_by_page:
                        self.corrections_by_page[page] = []
                    self.corrections_by_page[page].append(correction)
                
                print(f"Corrections by page: {list(self.corrections_by_page.keys())}")
                
                # Set total pages
                self.total_pages = document.metadata.page_count or 55
                
                # Load first page with corrections
                if self.corrections_by_page:
                    first_page = min(self.corrections_by_page.keys())
                    print(f"Setting current_page to first_page: {first_page}")
                    self.current_page = first_page
                    self.current_page_issues = self.corrections_by_page[first_page]
                    self.current_issue_index = 0
                    
                    # This is where the error might occur
                    print(f"Calling _load_page_text with page: {self.current_page}")
                    try:
                        self._load_page_text(self.current_page)
                        print("✅ _load_page_text completed successfully")
                    except Exception as e:
                        print(f"❌ _load_page_text failed: {e}")
                        raise e
                        
            def _load_page_text(self, page_number):
                print(f"_load_page_text called with page_number={page_number}")
                
                try:
                    if not self.current_document or not self.current_document.metadata.file_path:
                        self.extracted_text.setPlainText("No document loaded.")
                        return
                    
                    # Ensure page_number is valid
                    if page_number <= 0:
                        print(f"CRITICAL: Invalid page number {page_number}!")
                        page_number = 1
                        self.current_page = 1
                    
                    file_path = self.current_document.metadata.file_path
                    print(f"Loading page {page_number} from {file_path}")
                    
                    # Call enhanced extraction
                    self._load_page_text_with_enhanced_extraction(page_number, file_path)
                    
                except Exception as e:
                    error_msg = f"Failed to load page {page_number} text: {str(e)}"
                    print(f"ERROR: {error_msg}")
                    self.extracted_text.setPlainText(error_msg)
                    raise e
                    
            def _load_page_text_with_enhanced_extraction(self, page_number, file_path):
                print(f"_load_page_text_with_enhanced_extraction called with page_number={page_number}")
                
                try:
                    # Run enhanced extraction
                    elements, full_text, page_texts = self.enhanced_extractor.extract_with_perfect_correlation(file_path)
                    
                    print(f"Enhanced extraction returned: {len(elements)} elements, {len(full_text)} chars total, {len(page_texts)} pages")
                    print(f"Available pages in page_texts: {list(page_texts.keys())[:5]}...")
                    
                    # Check if page exists
                    if page_number in page_texts:
                        page_text = page_texts[page_number]
                        print(f"Found page {page_number} text: {len(page_text)} characters")
                        self.extracted_text.setPlainText(page_text)
                        return page_text
                    else:
                        error_msg = f"Page {page_number} not found in enhanced extraction."
                        print(f"ERROR: {error_msg}")
                        self.extracted_text.setPlainText(error_msg)
                        return None
                        
                except Exception as e:
                    error_msg = f"Enhanced extraction failed: {str(e)}"
                    print(f"ERROR: {error_msg}")
                    self.extracted_text.setPlainText(f"Failed to extract text from page {page_number}: {str(e)}")
                    raise e
        
        class MockTextEdit:
            def __init__(self):
                self.text = ""
                
            def setPlainText(self, text):
                self.text = text
                print(f"TEXT SET: {text[:100]}..." if len(text) > 100 else f"TEXT SET: {text}")
                
            def toPlainText(self):
                return self.text
        
        # Test the workflow
        widget = MockPageValidationWidget(settings)
        
        print("\n🔍 Loading document into widget...")
        widget.load_document_for_validation(document)
        
        print(f"\n✅ Workflow completed successfully!")
        print(f"Final current_page: {widget.current_page}")
        print(f"Final text length: {len(widget.extracted_text.text)}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_qa_workflow()