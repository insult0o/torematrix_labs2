#!/usr/bin/env python3
"""
Debug script for area loading issues.

This will help identify why areas aren't reappearing when returning to pages.
"""

import sys
import logging
import os
from pathlib import Path

# Add the project path
sys.path.insert(0, str(Path(__file__).parent))

# Set up comprehensive debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/area_loading_debug.log')
    ]
)

def debug_area_loading():
    """Debug the area loading mechanism comprehensively."""
    try:
        print("🔍 DEBUGGING AREA LOADING ISSUE")
        print("=" * 60)
        
        # Set environment variable to bypass dialog for testing
        os.environ['TORE_BYPASS_DIALOG'] = 'true'
        
        print("Environment: TORE_BYPASS_DIALOG = true (for testing)")
        print("Debug log: /tmp/area_loading_debug.log")
        print()
        
        # Enable detailed logging for our components
        logger_names = [
            'tore_matrix_labs.ui.components.enhanced_drag_select',
            'tore_matrix_labs.core.area_storage_manager',
            'tore_matrix_labs.ui.components.project_manager_widget',
            'tore_matrix_labs.ui.components.pdf_viewer'
        ]
        
        for name in logger_names:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
        
        print("📋 DEBUG CHECKLIST:")
        print("1. Create an area on a page")
        print("2. Watch logs for 'SAVE: Saved area X for document Y'")
        print("3. Change to different page")
        print("4. Watch logs for 'PAGE CHANGE: Cleared X areas from previous page'")
        print("5. Return to original page")
        print("6. Watch logs for 'LOAD AREAS: Successfully loaded X areas for page Y'")
        print()
        print("🔍 EXPECTED LOG PATTERNS:")
        print("SAVE: area_X saved → PROJECT: auto-save successful")
        print("PAGE CHANGE: clearing areas → LOAD AREAS: requesting areas")
        print("LOAD AREAS: get_areas_for_page called → areas loaded")
        print()
        print("❌ FAILURE POINTS TO WATCH:")
        print("- Areas saved but project not auto-saved")
        print("- get_areas_for_page returns empty dict")
        print("- load_areas finds document but no visual_areas")
        print("- Page number mismatch (1-based vs 0-based)")
        print()
        
        # Start the application with enhanced logging
        from tore_matrix_labs import main
        main()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_area_loading()