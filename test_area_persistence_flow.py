#!/usr/bin/env python3
"""
Test script to trace the complete area persistence flow.

This will help identify exactly where the area loading is failing.
"""

import sys
import logging
import os
from pathlib import Path

# Add the project path
sys.path.insert(0, str(Path(__file__).parent))

# Set up comprehensive logging
log_file = '/tmp/area_persistence_flow.log'
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file)
    ]
)

def test_area_persistence():
    """Test the complete area persistence flow with detailed tracing."""
    try:
        print("🔍 TESTING AREA PERSISTENCE FLOW")
        print("=" * 70)
        
        # Set bypass for automated testing
        os.environ['TORE_BYPASS_DIALOG'] = 'true'
        
        # Configure comprehensive logging
        loggers = [
            'tore_matrix_labs.ui.components.enhanced_drag_select',
            'tore_matrix_labs.core.area_storage_manager',
            'tore_matrix_labs.ui.components.project_manager_widget',
            'tore_matrix_labs.ui.components.pdf_viewer',
            'tore_matrix_labs.ui.main_window'
        ]
        
        for logger_name in loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.DEBUG)
        
        print(f"📝 Enhanced logging enabled for all components")
        print(f"📁 Log file: {log_file}")
        print()
        
        print("🎯 TEST PROCEDURE:")
        print("1. Load project with document (e.g., 4.tore)")
        print("2. Click document to activate it")
        print("3. Go to Manual Validation tab")
        print("4. Create area by dragging on PDF")
        print("5. Watch logs for SAVE sequence")
        print("6. Change to different page")
        print("7. Watch logs for PAGE CHANGE sequence")
        print("8. Return to original page")
        print("9. Watch logs for LOAD AREAS sequence")
        print()
        
        print("🔍 CRITICAL LOG PATTERNS TO WATCH:")
        print()
        print("AREA CREATION:")
        print("  ✅ 'SUCCESS: Created area X of type Y at Z'")
        print("  ✅ 'SAVE: ✅ Successfully saved area X for document Y'")
        print()
        print("PAGE CHANGE AWAY:")
        print("  ✅ 'PAGE CHANGE: Cleared N areas from previous page'")
        print()
        print("PAGE RETURN:")
        print("  ✅ 'LOAD AREAS: Document 'X' has N total areas'")
        print("  ✅ 'GET_PAGE: Found N areas for page Y'")
        print("  ✅ 'LOAD AREAS: Successfully loaded N areas for page Y'")
        print()
        
        print("❌ FAILURE INDICATORS:")
        print("  ❌ 'SAVE: ❌ Project save failed'")
        print("  ❌ 'LOAD: No visual_areas data found'")
        print("  ❌ 'GET_PAGE: Found 0 areas for page Y' (when should be > 0)")
        print("  ❌ 'LOAD: ❌ Document 'X' not found'")
        print()
        
        print("🚀 Starting application with enhanced debugging...")
        print("=" * 70)
        
        # Start main application
        from tore_matrix_labs import main
        main()
        
    except KeyboardInterrupt:
        print("\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"\n📋 Full debug log saved to: {log_file}")

if __name__ == "__main__":
    test_area_persistence()