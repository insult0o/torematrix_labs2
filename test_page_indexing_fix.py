#!/usr/bin/env python3
"""
Test script to verify the page indexing fix and identify remaining issues.
"""

import sys
import logging
import os
from pathlib import Path

# Add the project path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/page_indexing_fix_test.log')
    ]
)

def test_page_indexing_fix():
    """Test the page indexing fix and remaining area issues."""
    try:
        print("🔧 TESTING PAGE INDEXING FIX")
        print("=" * 60)
        
        # Set bypass for automated testing
        os.environ['TORE_BYPASS_DIALOG'] = 'true'
        
        # Enable comprehensive logging
        loggers = [
            'tore_matrix_labs.ui.components.enhanced_drag_select',
            'tore_matrix_labs.core.area_storage_manager',
            'tore_matrix_labs.ui.components.manual_validation_widget',
            'tore_matrix_labs.ui.components.pdf_viewer'
        ]
        
        for name in loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
        
        print("🎯 TEST PLAN:")
        print("1. Create area on first page of document")
        print("2. Verify preview shows correct page (should be first page now)")
        print("3. Change to different page")
        print("4. Return to first page - areas should reappear")
        print("5. Click area in selection list - should highlight properly")
        print()
        
        print("✅ EXPECTED FIXES:")
        print("📍 Preview shows correct page (not +1 page)")
        print("📍 'Preview bbox: X, page: 1 (1-based) → 0 (0-based for PyMuPDF)'")
        print()
        
        print("❌ REMAINING ISSUES TO IDENTIFY:")
        print("📍 Areas not reappearing when returning to page")
        print("📍 Area selection from list not highlighting")
        print()
        
        print("🔍 LOG PATTERNS TO WATCH:")
        print("✅ Fixed: Correct PyMuPDF page access")
        print("❌ Issue: 'LOAD AREAS: Found 0 areas for page X' when should be > 0")
        print("❌ Issue: Area list selection not triggering highlight")
        print()
        
        print("🚀 Starting application with comprehensive debugging...")
        print("=" * 60)
        
        from tore_matrix_labs import main
        main()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_page_indexing_fix()