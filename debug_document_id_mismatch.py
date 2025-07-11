#!/usr/bin/env python3
"""
Debug document ID mismatch issues in area storage.

This will identify if areas aren't being saved because the document ID
from the PDF viewer doesn't match the document ID in the project.
"""

import sys
import logging
import os
from pathlib import Path

# Add the project path
sys.path.insert(0, str(Path(__file__).parent))

# Set up focused logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/document_id_debug.log')
    ]
)

def debug_document_id_mismatch():
    """Debug document ID consistency issues."""
    try:
        print("🔍 DEBUGGING DOCUMENT ID MISMATCH")
        print("=" * 60)
        
        # Set bypass for automated testing
        os.environ['TORE_BYPASS_DIALOG'] = 'true'
        
        # Enable targeted logging
        loggers = [
            'tore_matrix_labs.ui.components.enhanced_drag_select',
            'tore_matrix_labs.core.area_storage_manager'
        ]
        
        for name in loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
        
        print("🎯 DOCUMENT ID MISMATCH INVESTIGATION:")
        print()
        print("POTENTIAL ISSUE:")
        print("❌ PDF viewer document ID ≠ Project document ID")
        print("❌ Area storage can't find document to save to")
        print("❌ Areas created but never persisted")
        print()
        
        print("🔍 KEY LOGS TO WATCH:")
        print()
        print("AREA CREATION:")
        print("📍 'AREA_CREATE: Document ID: X'")
        print("📍 'AREA_CREATE: Project has N documents with IDs: [Y, Z]'")
        print("📍 'AREA_CREATE: ✅ Document ID X found in project' (GOOD)")
        print("📍 'AREA_CREATE: ❌ Document ID X NOT found in project!' (BAD)")
        print()
        
        print("AREA STORAGE:")
        print("📍 'SAVE: Attempting to save area X for document Y'")
        print("📍 'SAVE: Checking document Z against Y'")
        print("📍 'SAVE: Found target document Y' (GOOD)")
        print("📍 'SAVE: ❌ Document Y not found in project documents' (BAD)")
        print()
        
        print("🔧 DIAGNOSIS:")
        print("If you see:")
        print("✅ Document ID found in project → Document ID matching works")
        print("❌ Document ID NOT found → Document ID mismatch issue")
        print("❌ Document not found in storage → Storage lookup issue")
        print()
        
        print("📋 TEST PROCEDURE:")
        print("1. Load project with document")
        print("2. Click document to activate it")
        print("3. Create area → Watch document ID logs")
        print("4. Check if area is saved or rejected")
        print()
        
        print("📁 Full debug: /tmp/document_id_debug.log")
        print("🚀 Starting application with document ID debugging...")
        print("=" * 60)
        
        from tore_matrix_labs import main
        main()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_document_id_mismatch()