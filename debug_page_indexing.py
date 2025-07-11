#!/usr/bin/env python3
"""
Debug script to trace page indexing issues in the cutting tool.

This will help identify the off-by-one error between page creation and loading.
"""

import sys
import logging
import os
from pathlib import Path

# Add the project path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging focused on page indexing
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/page_indexing_debug.log')
    ]
)

def debug_page_indexing():
    """Debug page indexing issues with detailed tracing."""
    try:
        print("🔍 DEBUGGING PAGE INDEXING ISSUE")
        print("=" * 60)
        
        # Set bypass for automated testing
        os.environ['TORE_BYPASS_DIALOG'] = 'true'
        
        # Enable logging for page-related components
        loggers = [
            'tore_matrix_labs.ui.components.enhanced_drag_select',
            'tore_matrix_labs.core.area_storage_manager',
            'tore_matrix_labs.ui.components.pdf_viewer'
        ]
        
        for name in loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
        
        print("📋 PAGE INDEXING TEST PROCEDURE:")
        print("1. Load document and go to FIRST page (page 1)")
        print("2. Create area on first page")
        print("3. Watch logs for AREA_CREATE page numbers")
        print("4. Go to second page")
        print("5. Return to first page")
        print("6. Watch logs for PAGE CHANGE and LOAD AREAS page numbers")
        print()
        
        print("🎯 KEY LOG PATTERNS TO WATCH:")
        print()
        print("AREA CREATION ON FIRST PAGE:")
        print("  📍 'AREA_CREATE: Page (0-based): 0'")
        print("  📍 'AREA_CREATE: Page (1-based): 1'")
        print("  📍 'SAVE: Added area X to document (page 1, bbox Y)'")
        print()
        
        print("PAGE NAVIGATION:")
        print("  📍 'PAGE CHANGE: Page changed to 1' (when returning to first page)")
        print("  📍 'PAGE CHANGE: PDF viewer current_page (0-based): 0'")
        print("  📍 'PAGE CHANGE: Page signal received (1-based): 1'")
        print()
        
        print("AREA LOADING:")
        print("  📍 'GET_PAGE: Filtering areas for document X, page 1'")
        print("  📍 'GET_PAGE: Area Y is on page 1 (looking for page 1)'")
        print("  📍 'GET_PAGE: ✅ Area Y matches page 1'")
        print()
        
        print("❌ BUG INDICATORS:")
        print("  ❌ Area saved with page N but loaded looking for page M")
        print("  ❌ 'GET_PAGE: Area Y is on page 2 (looking for page 1)' <- Wrong!")
        print("  ❌ 'GET_PAGE: Found 0 areas for page 1' when should be > 0")
        print()
        
        print("🚀 Starting application with page indexing debug...")
        print("=" * 60)
        
        from tore_matrix_labs import main
        main()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_page_indexing()