#!/usr/bin/env python3
"""
Trace immediate area storage to see exactly where the flow breaks.

Areas should be stored immediately when created and updated when resized.
"""

import sys
import logging
import os
from pathlib import Path

# Add the project path
sys.path.insert(0, str(Path(__file__).parent))

# Set up aggressive logging to catch everything
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/immediate_storage_trace.log')
    ]
)

def trace_immediate_storage():
    """Trace the immediate storage flow step by step."""
    try:
        print("🔍 TRACING IMMEDIATE AREA STORAGE FLOW")
        print("=" * 60)
        
        # Set bypass for automated testing
        os.environ['TORE_BYPASS_DIALOG'] = 'true'
        
        # Enable ALL logging
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        print("📋 IMMEDIATE STORAGE EXPECTATIONS:")
        print()
        print("AREA CREATION:")
        print("1. Drag → Release → Dialog/Bypass")
        print("2. _handle_area_selection() called")
        print("3. _create_visual_area() called")
        print("4. area.to_dict() creates data")
        print("5. area_storage_manager.save_area() called")
        print("6. Area added to persistent_areas dict")
        print("7. Project auto-saved IMMEDIATELY")
        print("8. Area visible on screen")
        print()
        
        print("AREA RESIZE:")
        print("1. Drag corner → _handle_resize() called")
        print("2. area.update_bbox() updates coordinates")
        print("3. Mouse release → _complete_resize() called")
        print("4. area_storage_manager.update_area() called")
        print("5. Same area ID re-saved with new bbox")
        print("6. Project auto-saved IMMEDIATELY")
        print("7. New size visible on screen")
        print()
        
        print("🔍 CRITICAL CHECKPOINTS TO WATCH:")
        print("✅ Area created: 'SUCCESS: Created area X of type Y'")
        print("✅ Added to memory: 'Area added to persistent areas. Total: N'")
        print("✅ Saved to storage: 'SAVE: ✅ Successfully saved area X'")
        print("✅ Project saved: '🟢 SAVE PROJECT: Returning True'")
        print("✅ Resize saved: 'RESIZE_COMPLETE: ✅ Successfully updated area X'")
        print()
        
        print("❌ FAILURE INDICATORS:")
        print("❌ 'No area storage manager available'")
        print("❌ 'SAVE: ❌ Document X not found in project'")
        print("❌ 'SAVE: ❌ Project save failed'")
        print("❌ 'RESIZE_COMPLETE: ❌ Failed to update area'")
        print()
        
        print("🎯 TEST ACTIONS:")
        print("1. Create area → Check ALL checkpoints pass")
        print("2. Resize area → Check resize checkpoints pass")
        print("3. Change page → Check area disappears")
        print("4. Return to page → Check area reappears")
        print()
        
        print("📁 Full trace: /tmp/immediate_storage_trace.log")
        print("🚀 Starting application with FULL logging...")
        print("=" * 60)
        
        from tore_matrix_labs import main
        main()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    trace_immediate_storage()