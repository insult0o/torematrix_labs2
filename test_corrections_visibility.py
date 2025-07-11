#!/usr/bin/env python3
"""
Test script to specifically verify corrections are visible in the UI.
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_corrections_visibility():
    """Test that corrections are actually visible and interactive in the UI."""
    
    try:
        print("=== Testing Corrections Visibility ===")
        
        from tore_matrix_labs.ui.qt_compat import QApplication
        from tore_matrix_labs.config.settings import Settings
        from tore_matrix_labs.ui.components.validation_widget import ValidationWidget
        from tore_matrix_labs.models.document_models import Document, DocumentMetadata, ProcessingConfiguration
        from tore_matrix_labs.config.constants import DocumentType, ProcessingStatus, QualityLevel
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
        
        # Create document with corrections (simulating auto-load process)
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
        
        # Test ValidationWidget directly
        app = QApplication(sys.argv)
        settings = Settings()
        
        validation_widget = ValidationWidget(settings)
        
        print(f"✅ Created ValidationWidget")
        
        # Load document (this should trigger corrections display)
        validation_widget.load_document(document, post_processing_result=None)
        
        print(f"✅ Loaded document into ValidationWidget")
        
        # Check if corrections are loaded in memory
        current_corrections = validation_widget.current_corrections
        print(f"✅ Current corrections in widget: {len(current_corrections)}")
        
        # Check if corrections layout has widgets
        corrections_layout = validation_widget.corrections_layout
        widget_count = 0
        
        for i in range(corrections_layout.count()):
            item = corrections_layout.itemAt(i)
            if item and item.widget():
                widget_count += 1
        
        print(f"✅ Correction widgets in layout: {widget_count}")
        
        # Verify widget visibility
        visible_widgets = 0
        for i in range(corrections_layout.count()):
            item = corrections_layout.itemAt(i)
            if item and item.widget() and item.widget().isVisible():
                visible_widgets += 1
        
        print(f"✅ Visible correction widgets: {visible_widgets}")
        
        # Test sample widget content
        if widget_count > 0:
            first_item = corrections_layout.itemAt(0)
            if first_item and first_item.widget():
                widget = first_item.widget()
                print(f"✅ Sample widget type: {type(widget).__name__}")
                
                # Check if it's a CorrectionItemWidget with content
                if hasattr(widget, 'correction'):
                    correction = widget.correction
                    print(f"✅ Sample correction:")
                    print(f"   Type: {correction.correction_type}")
                    print(f"   Original: {correction.original_content[:50]}...")
                    print(f"   Suggested: {correction.suggested_content[:50]}...")
                    print(f"   Confidence: {correction.confidence:.1%}")
        
        # Verify success criteria
        success = (
            len(corrections) > 0 and
            len(current_corrections) == len(corrections) and
            widget_count == len(corrections) and
            visible_widgets == len(corrections)
        )
        
        if success:
            print(f"\n🎉 CORRECTIONS VISIBILITY SUCCESS!")
            print(f"✅ {len(corrections)} corrections loaded")
            print(f"✅ {widget_count} widgets created")
            print(f"✅ {visible_widgets} widgets visible")
            print(f"✅ All corrections ready for interaction")
        else:
            print(f"\n❌ CORRECTIONS VISIBILITY ISSUES:")
            print(f"   Expected corrections: {len(corrections)}")
            print(f"   Loaded corrections: {len(current_corrections)}")
            print(f"   Created widgets: {widget_count}")
            print(f"   Visible widgets: {visible_widgets}")
        
        return success
        
    except Exception as e:
        print(f"❌ Visibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_corrections_visibility()
    if success:
        print(f"\n✅ The corrections display is working correctly!")
        print(f"   Open the application and you should see all corrections")
    else:
        print(f"\n❌ Corrections display still has issues")