#!/usr/bin/env python3
"""
Test script to simulate opening project 4 and loading corrections.
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_project_4_simulation():
    """Simulate the complete project 4 workflow."""
    
    try:
        print("=== Simulating Project 4 Workflow ===")
        
        from tore_matrix_labs.ui.qt_compat import QApplication
        from tore_matrix_labs.config.settings import Settings
        from tore_matrix_labs.ui.components.validation_widget import ValidationWidget
        from tore_matrix_labs.models.document_models import Document, DocumentMetadata, ProcessingConfiguration
        from tore_matrix_labs.config.constants import DocumentType, ProcessingStatus, QualityLevel
        from datetime import datetime
        
        # Step 1: Load project 4 data
        project_file = Path("4.tore")
        if not project_file.exists():
            print(f"❌ Project file not found: {project_file}")
            return False
            
        with open(project_file, 'r') as f:
            project_data = json.load(f)
        
        documents = project_data.get('documents', [])
        if not documents:
            print("❌ No documents in project")
            return False
        
        doc_data = documents[0]
        processing_data = doc_data.get('processing_data', {})
        corrections = processing_data.get('corrections', [])
        
        print(f"✅ Step 1: Loaded project with {len(corrections)} corrections")
        
        # Step 2: Simulate document selection (as would happen in _load_document_corrections_from_project_data)
        metadata = DocumentMetadata(
            file_name=doc_data.get('name', 'Unknown'),
            file_path=doc_data.get('path', ''),
            file_size=processing_data.get('file_size', 0),
            file_type='pdf',
            creation_date=datetime.now(),
            modification_date=datetime.now(),
            page_count=processing_data.get('page_count', 0)
        )
        
        processing_config = ProcessingConfiguration()
        
        quality_level_str = processing_data.get('quality_level', 'good')
        try:
            quality_level = QualityLevel(quality_level_str.upper())
        except (ValueError, AttributeError):
            quality_level = QualityLevel.GOOD
        
        document = Document(
            id=doc_data.get('id', 'project_doc'),
            metadata=metadata,
            document_type=DocumentType.ICAO,
            processing_status=ProcessingStatus.EXTRACTED,
            processing_config=processing_config,
            quality_level=quality_level,
            quality_score=processing_data.get('quality_score', 0.5),
            custom_metadata={'corrections': corrections}
        )
        
        print(f"✅ Step 2: Recreated document object")
        print(f"   File: {document.metadata.file_name}")
        print(f"   Corrections: {len(document.custom_metadata.get('corrections', []))}")
        
        # Step 3: Test loading into validation widget
        app = QApplication(sys.argv)
        settings = Settings()
        
        validation_widget = ValidationWidget(settings)
        validation_widget.load_document(document)
        
        print(f"✅ Step 3: Loaded document into validation widget")
        
        # Step 4: Test corrections display
        corrections_count = len(validation_widget.current_document.custom_metadata.get('corrections', []))
        print(f"✅ Step 4: Validation widget has {corrections_count} corrections")
        
        # Step 5: Test display corrections method
        validation_widget._display_corrections()
        
        # Count displayed widgets
        widget_count = 0
        for i in range(validation_widget.corrections_layout.count()):
            item = validation_widget.corrections_layout.itemAt(i)
            if item and item.widget():
                widget_count += 1
        
        print(f"✅ Step 5: Displayed {widget_count} correction widgets")
        
        # Verify complete workflow
        if widget_count == len(corrections) and widget_count > 0:
            print(f"\n🎉 Project 4 simulation successful!")
            print(f"   Project loaded: ✅")
            print(f"   Document reconstructed: ✅") 
            print(f"   Corrections loaded: ✅ ({len(corrections)})")
            print(f"   Corrections displayed: ✅ ({widget_count})")
            return True
        else:
            print(f"\n❌ Workflow incomplete")
            print(f"   Expected: {len(corrections)} corrections")
            print(f"   Displayed: {widget_count} widgets")
            return False
        
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_project_4_simulation()
    if success:
        print("\n✅ Project 4 should work correctly now!")
        print("   Open the application and load project 4")
        print("   Click on the document in the project tree")
        print("   Switch to QA Validation tab")
        print("   You should see all 184 corrections ready for review")
    else:
        print("\n❌ Issues still need to be resolved.")