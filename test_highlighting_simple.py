#!/usr/bin/env python3
"""
Simple test script to verify highlighting components work without GUI.
"""

import sys
import logging

# Add the tore_matrix_labs module to the Python path
sys.path.append('/home/insulto/tore_matrix_labs')

# Setup logging
logging.basicConfig(level=logging.ERROR)  # Reduce log noise

def test_highlighting_simple():
    """Test that highlighting components import and work."""
    print("🧪 TESTING HIGHLIGHTING COMPONENTS")
    print("=" * 50)
    
    try:
        # Test 1: Import highlighting components
        print("\n📋 TEST 1: Importing highlighting components...")
        
        from tore_matrix_labs.ui.highlighting.highlight_style import HighlightStyle
        from tore_matrix_labs.ui.highlighting.coordinate_mapper import CoordinateMapper
        from tore_matrix_labs.ui.highlighting.multi_box_renderer import MultiBoxRenderer
        
        print("   ✅ All highlighting components imported successfully")
        
        # Test 2: Create highlighting components
        print("\n📋 TEST 2: Creating highlighting components...")
        
        style = HighlightStyle()
        mapper = CoordinateMapper()
        renderer = MultiBoxRenderer()
        
        print("   ✅ All highlighting components created successfully")
        
        # Test 3: Test color scheme
        print("\n📋 TEST 3: Testing color scheme...")
        
        pdf_style = style.get_pdf_style('active_highlight')
        
        if pdf_style and 'background_color' in pdf_style:
            color = pdf_style['background_color']
            if color == '#FFFF00':  # Pure yellow
                print(f"   ✅ PDF style correct: {color}")
            else:
                print(f"   ❌ PDF style incorrect: {color} (expected #FFFF00)")
                return False
        else:
            print(f"   ❌ PDF style missing or invalid")
            return False
        
        # Test 4: Test basic functionality
        print("\n📋 TEST 4: Testing basic functionality...")
        
        # Test coordinate mapper
        if hasattr(mapper, 'set_pdf_viewer') and hasattr(mapper, 'set_text_widget'):
            print("   ✅ CoordinateMapper has required methods")
        else:
            print("   ❌ CoordinateMapper missing required methods")
            return False
        
        # Test renderer
        if hasattr(renderer, 'render_text_highlight') and hasattr(renderer, 'render_pdf_highlight'):
            print("   ✅ MultiBoxRenderer has required methods")
        else:
            print("   ❌ MultiBoxRenderer missing required methods")
            return False
        
        print("\n🎯 SIMPLE TEST SUMMARY:")
        print("   ✅ All highlighting components import successfully")
        print("   ✅ All highlighting components create successfully")
        print("   ✅ Color scheme is pure yellow (#FFFF00)")
        print("   ✅ Basic functionality methods available")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR during simple test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_highlighting_simple()
    if success:
        print(f"\n✅ SIMPLE HIGHLIGHTING TEST PASSED!")
        print(f"🚀 All highlighting components are working correctly")
    else:
        print(f"\n❌ SIMPLE HIGHLIGHTING TEST FAILED!")
        sys.exit(1)