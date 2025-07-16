#!/usr/bin/env python3
"""
Test script for Agent 1 validation implementation.

This script tests the core validation framework components:
- DrawingStateManager
- ValidationAreaSelector
- Selection shapes and tools
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from PyQt6.QtWidgets import QApplication, QWidget
    from PyQt6.QtCore import QPointF
    from PyQt6.QtGui import QPixmap
    
    from torematrix.ui.tools.validation import (
        DrawingStateManager,
        DrawingMode,
        DrawingState,
        ValidationAreaSelector,
        AreaSelectionMode,
        RectangleShape,
        RectangleSelectionTool
    )
    from torematrix.utils.geometry import Rect as Rectangle
    from torematrix.core.models import ElementType
    
    def test_drawing_state_manager():
        """Test the DrawingStateManager functionality."""
        print("Testing DrawingStateManager...")
        
        manager = DrawingStateManager()
        
        # Test initial state
        assert manager.mode == DrawingMode.DISABLED
        assert manager.state == DrawingState.IDLE
        assert manager.current_session is None
        assert manager.current_area is None
        
        # Test activate draw mode
        result = manager.activate_draw_mode(batch_mode=False)
        assert result is True
        assert manager.mode == DrawingMode.SELECTION
        assert manager.state == DrawingState.IDLE
        assert manager.current_session is not None
        
        # Test start area selection
        result = manager.start_area_selection()
        assert result is True
        assert manager.state == DrawingState.SELECTING_AREA
        
        # Test complete area selection
        rectangle = Rectangle(x=10, y=20, width=100, height=80)
        result = manager.complete_area_selection(rectangle)
        assert result is True
        assert manager.state == DrawingState.AREA_SELECTED
        assert manager.current_area is not None
        
        # Test set element type
        result = manager.set_element_type(ElementType.TEXT)
        assert result is True
        assert manager.current_area.element_type == ElementType.TEXT
        
        # Test deactivate draw mode
        result = manager.deactivate_draw_mode()
        assert result is True
        assert manager.mode == DrawingMode.DISABLED
        
        print("✓ DrawingStateManager tests passed")
    
    def test_validation_area_selector():
        """Test the ValidationAreaSelector functionality."""
        print("Testing ValidationAreaSelector...")
        
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        widget = QWidget()
        selector = ValidationAreaSelector(widget)
        
        # Test initial state
        assert selector.mode == AreaSelectionMode.CREATE_NEW
        assert selector.is_selecting is False
        assert len(selector.selections) == 0
        
        # Test tool selection
        selector.set_tool('rectangle')
        assert selector.active_tool_name == 'rectangle'
        assert isinstance(selector.current_tool, RectangleSelectionTool)
        
        # Test selection process
        start_point = QPointF(10, 20)
        end_point = QPointF(110, 100)
        
        selector.start_selection(start_point)
        assert selector.is_selecting is True
        
        selector.update_selection(end_point)
        assert selector.current_shape is not None
        
        selector.complete_selection()
        assert selector.is_selecting is False
        assert len(selector.selections) == 1
        
        print("✓ ValidationAreaSelector tests passed")
    
    def test_rectangle_shape():
        """Test the RectangleShape functionality."""
        print("Testing RectangleShape...")
        
        shape = RectangleShape()
        shape.set_from_points(QPointF(10, 20), QPointF(110, 100))
        
        # Test bounding rect
        rect = shape.get_bounding_rect()
        assert rect.width() == 100
        assert rect.height() == 80
        
        # Test contains
        assert shape.contains(QPointF(50, 50)) is True
        assert shape.contains(QPointF(200, 200)) is False
        
        # Test handles
        handles = shape.get_handles()
        assert len(handles) == 8  # 4 corners + 4 edge midpoints
        
        print("✓ RectangleShape tests passed")
    
    def run_all_tests():
        """Run all Agent 1 validation tests."""
        print("🧪 Starting Agent 1 Validation Tests...")
        print("=" * 50)
        
        try:
            test_drawing_state_manager()
            test_validation_area_selector()
            test_rectangle_shape()
            
            print("=" * 50)
            print("🎉 All Agent 1 tests passed successfully!")
            print("✅ Core validation framework is working correctly")
            return True
            
        except Exception as e:
            print("=" * 50)
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    if __name__ == "__main__":
        success = run_all_tests()
        sys.exit(0 if success else 1)

except ImportError as e:
    print(f"❌ Import failed: {e}")
    print("Please ensure all dependencies are installed and paths are correct")
    sys.exit(1)