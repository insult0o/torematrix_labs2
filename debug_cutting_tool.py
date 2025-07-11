#!/usr/bin/env python3
"""
Debug script for the cutting tool issue.

This will help identify why areas disappear after creation.
"""

import sys
import logging
from pathlib import Path

# Add the project path
sys.path.insert(0, str(Path(__file__).parent))

# Set up debug logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('/tmp/cutting_tool_debug.log')
    ]
)

def test_dialog_only():
    """Test just the dialog to see if it works."""
    try:
        from PyQt5.QtWidgets import QApplication
        from tore_matrix_labs.ui.dialogs.area_type_dialog import AreaTypeDialog
        from tore_matrix_labs.models.visual_area_models import AreaType
        
        app = QApplication(sys.argv)
        
        print("Testing AreaTypeDialog...")
        dialog = AreaTypeDialog()
        
        # Show dialog and wait for result
        result = dialog.exec_()
        selected_type = dialog.get_selected_type()
        
        print(f"Dialog result: {result}")
        print(f"Selected type: {selected_type}")
        
        if result == dialog.Accepted and selected_type:
            print(f"SUCCESS: Selected {selected_type.value}")
        else:
            print("FAILED: Dialog canceled or no selection")
            
    except Exception as e:
        print(f"Error testing dialog: {e}")
        import traceback
        traceback.print_exc()

def run_with_debug():
    """Run the full application with debug logging enabled."""
    try:
        # Enable debug logging for our components
        logger_names = [
            'tore_matrix_labs.ui.components.enhanced_drag_select',
            'tore_matrix_labs.core.area_storage_manager',
            'tore_matrix_labs.ui.dialogs.area_type_dialog'
        ]
        
        for name in logger_names:
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
        
        print("🔍 Debug mode enabled")
        print("Log file: /tmp/cutting_tool_debug.log")
        print("Watch the console and log file for detailed debug info...")
        print()
        
        from tore_matrix_labs import main
        main()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--dialog-test":
        test_dialog_only()
    else:
        run_with_debug()