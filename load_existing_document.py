#!/usr/bin/env python3
"""
Script to manually load an existing processed document into the application.
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def load_existing_document():
    """Load the existing processed document and trigger the UI workflow."""
    
    try:
        from tore_matrix_labs.ui.main_window import MainWindow
        from tore_matrix_labs.config.settings import Settings
        from tore_matrix_labs.ui.qt_compat import QApplication
        
        print("Loading existing processed document...")
        
        # Check if output file exists
        output_file = Path("output/5555_complete.json")
        if not output_file.exists():
            print(f"❌ Output file not found: {output_file}")
            return
            
        print(f"✅ Found output file: {output_file}")
        
        # Start the application
        app = QApplication(sys.argv)
        settings = Settings()
        main_window = MainWindow(settings)
        
        # Manually trigger the document processed handler
        document_path = "/home/insulto/tore_matrix_labs/5555.pdf"
        print(f"📄 Manually triggering document loading: {document_path}")
        
        # Call the document processed handler directly
        main_window._on_document_processed(document_path)
        
        main_window.show()
        print("🚀 Application started with document loaded")
        print("   Check QA Validation tab for corrections")
        print("   Check Project Tree for document listing")
        print("   Click document in project tree to preview")
        
        sys.exit(app.exec_())
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    load_existing_document()