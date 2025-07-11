#!/usr/bin/env python3
"""
Test script to verify corrections display in QA validation widget.
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_corrections_display():
    """Test the corrections display functionality."""
    
    try:
        from tore_matrix_labs.ui.qt_compat import QApplication
        from tore_matrix_labs.config.settings import Settings
        from tore_matrix_labs.ui.components.validation_widget import ValidationWidget
        from tore_matrix_labs.models.document_models import Document, DocumentMetadata, ProcessingConfiguration
        from tore_matrix_labs.config.constants import DocumentType, ProcessingStatus, QualityLevel
        from datetime import datetime
        
        print("=== Testing Corrections Display ===")
        
        # Load the actual output file to get corrections
        output_file = Path("output/5555_complete.json")
        if not output_file.exists():
            print(f"❌ Output file not found: {output_file}")
            return False
            
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        qa = data.get('quality_assessment', {})
        issues = qa.get('issues', [])
        
        print(f"✅ Found {len(issues)} quality issues")
        
        # Convert issues to corrections format
        corrections = []
        for idx, issue in enumerate(issues):
            correction = {
                'id': f'correction_{idx}',
                'type': issue.get('type', 'ocr_error'),
                'description': issue.get('description', ''),
                'suggested_fix': issue.get('suggested_fix', ''),
                'confidence': issue.get('confidence', 0.5),
                'location': issue.get('location', {}),
                'severity': issue.get('severity', 'medium')
            }
            corrections.append(correction)
        
        # Create document with corrections
        metadata = DocumentMetadata(
            file_name="5555.pdf",
            file_path="/home/insulto/tore_matrix_labs/5555.pdf",
            file_size=5337922,
            file_type='pdf',
            creation_date=datetime.now(),
            modification_date=datetime.now(),
            page_count=55
        )
        
        processing_config = ProcessingConfiguration()
        
        document = Document(
            id="test_doc",
            metadata=metadata,
            document_type=DocumentType.ICAO,
            processing_status=ProcessingStatus.EXTRACTED,
            processing_config=processing_config,
            quality_level=QualityLevel.GOOD,
            quality_score=0.5,
            custom_metadata={'corrections': corrections}
        )
        
        print(f"✅ Created document with {len(corrections)} corrections")
        
        # Test the validation widget
        app = QApplication(sys.argv)
        settings = Settings()
        
        validation_widget = ValidationWidget(settings)
        validation_widget.load_document(document)
        
        print(f"✅ Loaded document into validation widget")
        print(f"   Current document: {validation_widget.current_document.metadata.file_name}")
        print(f"   Corrections count: {len(validation_widget.current_document.custom_metadata.get('corrections', []))}")
        
        # Test the _display_corrections method
        validation_widget._display_corrections()
        
        # Count widgets in the layout
        corrections_count = 0
        for i in range(validation_widget.corrections_layout.count()):
            item = validation_widget.corrections_layout.itemAt(i)
            if item and item.widget():
                corrections_count += 1
        
        print(f"✅ Displayed corrections in UI")
        print(f"   Widget count: {corrections_count}")
        print(f"   Expected: {len(corrections)}")
        
        success = corrections_count > 0
        print(f"\n{'✅ SUCCESS' if success else '❌ FAILURE'}: Corrections display test")
        
        return success
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_corrections_display()
    if success:
        print("\n🎉 Corrections display is working properly!")
    else:
        print("\n❌ Corrections display needs fixing.")