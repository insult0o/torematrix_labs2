#!/usr/bin/env python3
"""
Focused debug script to trace the complete area loading pipeline.

This will trace every step from area creation → storage → retrieval → display.
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
        logging.FileHandler('/tmp/area_loading_pipeline.log')
    ]
)

def debug_area_loading_pipeline():
    """Debug the complete area loading pipeline step by step."""
    try:
        print("🔍 DEBUGGING AREA LOADING PIPELINE")
        print("=" * 60)
        
        # Set bypass for automated testing
        os.environ['TORE_BYPASS_DIALOG'] = 'true'
        
        # Enable detailed logging for critical components
        critical_loggers = [
            'tore_matrix_labs.ui.components.enhanced_drag_select',
            'tore_matrix_labs.core.area_storage_manager'
        ]
        
        for name in critical_loggers:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
        
        print("🎯 AREA LOADING PIPELINE TEST:")
        print()
        print("STEP 1: CREATE AREA")
        print("   - Create area on page 1")
        print("   - Watch: 'AREA_CREATE: Area will be stored with page=1'")
        print("   - Watch: 'SAVE: ✅ Successfully saved area X for document Y'")
        print()
        
        print("STEP 2: VERIFY STORAGE")
        print("   - Area should be in project data")
        print("   - Watch: 'SAVE: Added area X to document (page 1, bbox Y)'")
        print("   - Watch: 'SAVE: Project auto-save result: True'")
        print()
        
        print("STEP 3: PAGE CHANGE AWAY")
        print("   - Go to page 2")
        print("   - Watch: 'PAGE CHANGE: Cleared N areas from previous page'")
        print()
        
        print("STEP 4: RETURN TO PAGE 1")
        print("   - Go back to page 1")
        print("   - Watch complete loading sequence:")
        print("     📍 'PAGE CHANGE: Loading areas for document X, page 1'")
        print("     📍 'LOAD AREAS: Document X has N total areas'")
        print("     📍 'GET_PAGE: Found N areas for page 1'")
        print("     📍 'LOAD AREAS: Successfully loaded N areas for page 1'")
        print("     📍 'PAINT: Drawing N persistent areas'")
        print()
        
        print("🔍 CRITICAL FAILURE POINTS TO IDENTIFY:")
        print("❌ SAVE FAILURE: 'SAVE: ❌ Project save failed'")
        print("❌ LOAD FAILURE: 'LOAD: No visual_areas data found'")
        print("❌ FILTER FAILURE: 'GET_PAGE: Found 0 areas for page 1' (when should be > 0)")
        print("❌ DISPLAY FAILURE: 'PAINT: No persistent areas to draw'")
        print()
        
        print("🔧 DEBUG COMMANDS:")
        print("1. Create area → Check console for SAVE sequence")
        print("2. Change page → Check console for PAGE CHANGE sequence")  
        print("3. Return to page → Check console for LOAD sequence")
        print("4. If areas don't appear → Check which step failed")
        print()
        
        print("📁 Full debug log: /tmp/area_loading_pipeline.log")
        print("🚀 Starting application...")
        print("=" * 60)
        
        from tore_matrix_labs import main
        main()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_area_loading_pipeline()