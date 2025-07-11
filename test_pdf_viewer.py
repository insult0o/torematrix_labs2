#!/usr/bin/env python3
"""
Test script to verify PDF viewer functionality.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from tore_matrix_labs.ui.components.pdf_viewer import PDFViewer
    from tore_matrix_labs.ui.qt_compat import QApplication, QMainWindow
    
    class TestWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("PDF Viewer Test")
            self.setGeometry(100, 100, 800, 600)
            
            # Create PDF viewer
            self.pdf_viewer = PDFViewer()
            self.setCentralWidget(self.pdf_viewer)
            
            # Load test PDF
            pdf_path = "/home/insulto/tore_matrix_labs/5555.pdf"
            if Path(pdf_path).exists():
                print(f"Loading PDF: {pdf_path}")
                self.pdf_viewer.load_document(pdf_path)
            else:
                print(f"PDF not found: {pdf_path}")
    
    def main():
        app = QApplication(sys.argv)
        window = TestWindow()
        window.show()
        
        print("PDF viewer test started. Close window to exit.")
        sys.exit(app.exec_())
    
    if __name__ == "__main__":
        main()

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()