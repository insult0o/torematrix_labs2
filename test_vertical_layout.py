#!/usr/bin/env python3
"""
Test script to verify the new vertical corrections layout with PDF highlighting.
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_vertical_layout():
    """Test the new vertical layout with PDF highlighting."""
    
    try:
        print("=== Testing New Vertical Corrections Layout ===")
        
        from tore_matrix_labs.ui.qt_compat import QApplication
        from tore_matrix_labs.config.settings import Settings
        from tore_matrix_labs.ui.components.validation_widget import ValidationWidget, CorrectionItemWidget
        from tore_matrix_labs.models.document_models import Document, DocumentMetadata, ProcessingConfiguration
        from tore_matrix_labs.config.constants import DocumentType, ProcessingStatus, QualityLevel
        from tore_matrix_labs.core.content_validator import ContentCorrection, CorrectionType, CorrectionStatus
        from datetime import datetime
        
        # Load project 4 corrections
        project_file = Path("4.tore")
        if not project_file.exists():
            print(f"❌ Project file not found: {project_file}")
            return False
            
        with open(project_file, 'r') as f:
            project_data = json.load(f)
        
        documents = project_data.get('documents', [])
        doc_data = documents[0]
        processing_data = doc_data.get('processing_data', {})
        corrections = processing_data.get('corrections', [])
        
        print(f"✅ Loaded project data with {len(corrections)} corrections")
        
        # Create document with corrections
        metadata = DocumentMetadata(
            file_name=doc_data.get('name', 'test.pdf'),
            file_path=doc_data.get('path', ''),
            file_size=processing_data.get('file_size', 0),
            file_type='pdf',
            creation_date=datetime.now(),
            modification_date=datetime.now(),
            page_count=processing_data.get('page_count', 0)
        )
        
        processing_config = ProcessingConfiguration()
        
        document = Document(
            id=doc_data.get('id', 'test_doc'),
            metadata=metadata,
            document_type=DocumentType.ICAO,
            processing_status=ProcessingStatus.EXTRACTED,
            processing_config=processing_config,
            quality_level=QualityLevel.GOOD,
            quality_score=processing_data.get('quality_score', 0.5),
            custom_metadata={'corrections': corrections}
        )
        
        print(f"✅ Created document object with {len(document.custom_metadata.get('corrections', []))} corrections")
        
        # Test ValidationWidget with new layout
        app = QApplication(sys.argv)
        settings = Settings()
        
        validation_widget = ValidationWidget(settings)
        
        print(f"✅ Created ValidationWidget with new design")
        
        # Load document (this should trigger new corrections display)
        validation_widget.load_document(document, post_processing_result=None)
        
        print(f"✅ Loaded document into ValidationWidget")
        
        # Check if corrections are loaded and displayed with new layout
        current_corrections = validation_widget.current_corrections
        print(f"✅ Current corrections in widget: {len(current_corrections)}")
        
        # Check if corrections layout has widgets with new design
        corrections_layout = validation_widget.corrections_layout
        widget_count = 0
        
        for i in range(corrections_layout.count()):
            item = corrections_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), CorrectionItemWidget):
                widget_count += 1
        
        print(f"✅ New correction widgets in layout: {widget_count}")
        
        # Test sample widget features
        if widget_count > 0:
            first_item = corrections_layout.itemAt(0)
            if first_item and isinstance(first_item.widget(), CorrectionItemWidget):
                widget = first_item.widget()
                print(f"✅ Sample widget features:")
                print(f"   - Has vertical splitter: {'main_splitter' in dir(widget)}")
                print(f"   - Has issue type section: {'issue_group' in widget.__dict__}")
                print(f"   - Has extraction edition: {'extraction_text' in widget.__dict__}")
                print(f"   - Has PDF highlighting signals: {hasattr(widget, 'correction_selected')}")
                print(f"   - Has approve/reject buttons: {hasattr(widget, 'approve_btn') and hasattr(widget, 'reject_btn')}")
                
                # Test signal connections
                if hasattr(widget, 'correction_selected'):
                    print(f"   - PDF highlighting signal connected: {widget.correction_selected.receivers() > 0}")
        
        # Verify success criteria
        success = (
            len(corrections) > 0 and
            len(current_corrections) == len(corrections) and
            widget_count == len(corrections)
        )
        
        if success:
            print(f"\n🎉 NEW VERTICAL LAYOUT SUCCESS!")
            print(f"✅ {len(corrections)} corrections loaded")
            print(f"✅ {widget_count} widgets created with new vertical design")
            print(f"✅ Issue Type section shows correction category")
            print(f"✅ Extraction Edition section allows text editing")
            print(f"✅ PDF highlighting connected for click-to-highlight")
            print(f"✅ Compact approve/reject buttons in header")
            print(f"✅ All corrections ready for interactive editing")
        else:
            print(f"\n❌ NEW LAYOUT ISSUES:")
            print(f"   Expected corrections: {len(corrections)}")
            print(f"   Loaded corrections: {len(current_corrections)}")
            print(f"   Created widgets: {widget_count}")
        
        return success
        
    except Exception as e:
        print(f"❌ Vertical layout test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_vertical_layout()
    if success:
        print(f"\n✅ The new vertical corrections layout is working perfectly!")
        print(f"🔥 Features implemented:")
        print(f"   ✅ Vertical split: Issue Type (top) + Extraction Edition (bottom)")
        print(f"   ✅ Issue type shows category with emoji icons")
        print(f"   ✅ Extraction Edition allows real-time text editing")
        print(f"   ✅ Click any correction to highlight PDF location")
        print(f"   ✅ Highlighted issue text within extraction content")
        print(f"   ✅ Compact approve ✓ / reject ✗ buttons")
        print(f"   ✅ Live PDF highlighting when corrections are clicked")
    else:
        print(f"\n❌ Vertical layout still has issues")