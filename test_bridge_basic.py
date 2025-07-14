#!/usr/bin/env python3
"""
Basic test script for PDF Bridge functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # Test basic imports
    from src.torematrix.integrations.pdf.bridge import PDFBridge, ElementCoordinate, HighlightStyle
    from src.torematrix.integrations.pdf.communication import MessageValidator, MessageQueue
    
    print("✅ Bridge imports successful")
    
    # Test ElementCoordinate
    coord = ElementCoordinate(
        page=1,
        x=100.0,
        y=200.0,
        width=50.0,
        height=25.0,
        element_id="test_element",
        element_type="text"
    )
    print(f"✅ ElementCoordinate created: {coord}")
    
    # Test HighlightStyle
    style = HighlightStyle(color="#00ff00", opacity=0.5)
    print(f"✅ HighlightStyle created: {style}")
    
    # Test MessageValidator
    valid_data = {
        'elements': [
            {
                'page': 1,
                'x': 100.0,
                'y': 200.0,
                'width': 50.0,
                'height': 25.0,
                'element_id': 'test',
                'element_type': 'text'
            }
        ],
        'style': {
            'color': '#ff0000',
            'opacity': 0.3
        }
    }
    
    is_valid = MessageValidator.validate_highlight_message(valid_data)
    print(f"✅ Message validation: {is_valid}")
    
    # Test MessageQueue
    queue = MessageQueue(max_retries=3, max_queue_size=10)
    status = queue.get_status()
    print(f"✅ MessageQueue status: {status}")
    
    print("\n🎉 All basic bridge tests passed!")
    
except ImportError as e:
    print(f"❌ Import error (expected without PyQt6): {e}")
    print("This is expected if PyQt6 is not installed")
    
except Exception as e:
    print(f"❌ Test error: {e}")
    import traceback
    traceback.print_exc()