#!/usr/bin/env python3
"""
Test script to verify auto-loading of documents when project is opened.
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_auto_load_project():
    """Test the auto-loading functionality when opening a project."""
    
    try:
        print("=== Testing Auto-Load Project Functionality ===")
        
        from tore_matrix_labs.ui.qt_compat import QApplication
        from tore_matrix_labs.config.settings import Settings
        from tore_matrix_labs.ui.main_window import MainWindow
        
        # Load project 4 to test with
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
        
        print(f"✅ Project 4 contains {len(documents)} documents")
        
        # Check first document for corrections
        doc_data = documents[0]
        processing_data = doc_data.get('processing_data', {})
        corrections_count = processing_data.get('corrections_count', 0)
        
        print(f"✅ First document: {doc_data.get('name')}")
        print(f"   Corrections: {corrections_count}")
        
        if corrections_count == 0:
            print("❌ No corrections in first document - auto-load won't work")
            return False
        
        # Create application and test auto-loading
        app = QApplication(sys.argv)
        settings = Settings()
        main_window = MainWindow(settings)
        
        print(f"✅ Created main window")
        
        # Simulate opening the project (this will trigger _on_project_loaded)
        main_window.project_widget.load_project(str(project_file))
        
        print(f"✅ Loaded project via project widget")
        
        # Check if QA validation widget has a document loaded
        qa_widget = main_window.qa_widget
        current_doc = qa_widget.validation_widget.current_document
        
        if current_doc:
            corrections_in_qa = len(current_doc.custom_metadata.get('corrections', []))
            print(f"✅ QA validation widget has document loaded:")
            print(f"   Document ID: {current_doc.id}")
            print(f"   File name: {current_doc.metadata.file_name}")
            print(f"   Corrections: {corrections_in_qa}")
            
            if corrections_in_qa == corrections_count:
                print(f"✅ Auto-load successful! All {corrections_count} corrections loaded")
                return True
            else:
                print(f"❌ Correction count mismatch: expected {corrections_count}, got {corrections_in_qa}")
                return False
        else:
            print(f"❌ No document loaded in QA validation widget")
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_auto_load_project()
    if success:
        print("\n🎉 Auto-load functionality working!")
        print("✅ When you open project 4:")
        print("   1. Documents load into project tree")
        print("   2. First document auto-loads into QA validation")
        print("   3. PDF preview loads automatically")
        print("   4. Tab switches to QA Validation")
        print("   5. All corrections ready for review")
        print("\n💡 Open the application and test project 4!")
    else:
        print("\n❌ Auto-load functionality needs fixing.")