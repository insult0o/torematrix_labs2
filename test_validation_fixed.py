#!/usr/bin/env python3
"""
Test validation tools after fixes.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_validation_tools():
    """Test core validation tools functionality."""
    print("Testing validation tools after fixes...")
    
    try:
        # Test imports
        from torematrix.ui.tools.validation.drawing_state import DrawingStateManager, DrawingMode
        from torematrix.ui.tools.validation.area_select import ValidationAreaSelector, AreaSelectionMode
        from torematrix.ui.tools.validation.shapes import RectangleShape, RectangleSelectionTool
        from PyQt6.QtCore import QPointF
        
        print("✓ All imports successful")
        
        # Test basic functionality
        # Test shapes
        rect = RectangleShape(QPointF(10, 10), QPointF(100, 100))
        bounds = rect.get_bounding_rect()
        print(f"✓ RectangleShape working: bounds={bounds.width()}x{bounds.height()}")
        
        # Test selection tool
        tool = RectangleSelectionTool()
        print(f"✓ RectangleSelectionTool created: active={tool.is_active}")
        
        # Test area selector (without Qt application)
        selector = ValidationAreaSelector()
        print(f"✓ ValidationAreaSelector created: mode={selector.mode}")
        
        print("\n🎉 All validation tools tests PASSED!")
        return True
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_validation_tools()
    sys.exit(0 if success else 1)