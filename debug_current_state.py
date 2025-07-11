#!/usr/bin/env python3
"""
Debug the current state of the text highlighting and area detection.
"""

import sys
import os
sys.path.insert(0, '/home/insulto/tore_matrix_labs')

from tore_matrix_labs.ui.qt_compat import *
from tore_matrix_labs.config.settings import Settings
import json

# Fix imports
from PyQt5.QtGui import QTextCursor, QTextCharFormat

def test_text_highlighting():
    """Test text highlighting with a simple QTextEdit."""
    print("=== TESTING TEXT HIGHLIGHTING ===")
    
    app = QApplication(sys.argv)
    
    # Create a simple text edit
    text_edit = QTextEdit()
    text_edit.setPlainText("This is a test text with multiple lines.\nSecond line here.\nThird line here.")
    text_edit.show()
    
    # Test highlighting
    cursor = text_edit.textCursor()
    cursor.setPosition(10)
    cursor.setPosition(25, QTextCursor.KeepAnchor)
    
    # Create highlight format
    highlight_format = QTextCharFormat()
    highlight_format.setBackground(QColor("#ffeb3b"))  # Yellow
    highlight_format.setForeground(QColor("#d32f2f"))  # Red
    
    cursor.setCharFormat(highlight_format)
    text_edit.setTextCursor(cursor)
    
    print("Text highlighting test window opened")
    print("Check if text is readable and highlighting works")
    
    # Don't run the app, just test the setup
    text_edit.close()
    app.quit()
    
    return True

def test_area_detection():
    """Test area detection in corrections."""
    print("\n=== TESTING AREA DETECTION ===")
    
    try:
        with open('/home/insulto/tore_matrix_labs/4.tore', 'r') as f:
            data = json.load(f)
        
        corrections = data['documents'][0]['processing_data']['corrections']
        print(f"Total corrections: {len(corrections)}")
        
        # Test highlight type detection
        areas_found = []
        for correction in corrections:
            description = correction.get('description', '').lower()
            
            highlight_type = None
            if 'image' in description:
                highlight_type = 'manual_image'
            elif 'table' in description:
                highlight_type = 'manual_table'
            elif 'diagram' in description:
                highlight_type = 'manual_diagram'
            elif correction.get('type') == 'ocr_correction':
                highlight_type = 'active_issue'
            else:
                highlight_type = 'issue'
            
            if highlight_type in ['manual_image', 'manual_table', 'manual_diagram']:
                areas_found.append({
                    'id': correction.get('id'),
                    'type': highlight_type,
                    'description': correction.get('description'),
                    'page': correction.get('location', {}).get('page'),
                    'bbox': correction.get('location', {}).get('bbox', [])
                })
        
        print(f"Found {len(areas_found)} areas that should be highlighted:")
        for area in areas_found:
            print(f"  - Page {area['page']}: {area['type']} - {area['description']}")
            print(f"    Bbox: {area['bbox']}")
        
        return len(areas_found) > 0
        
    except Exception as e:
        print(f"Error testing area detection: {e}")
        return False

if __name__ == "__main__":
    # Test text highlighting
    text_ok = test_text_highlighting()
    
    # Test area detection
    areas_ok = test_area_detection()
    
    print(f"\n=== RESULTS ===")
    print(f"Text highlighting setup: {'✓' if text_ok else '✗'}")
    print(f"Area detection: {'✓' if areas_ok else '✗'}")
    
    if not areas_ok:
        print("\nNo areas found - this explains why outlines don't appear!")
    
    print("\nTo fix the issues:")
    print("1. Text readability: Check QTextEdit stylesheet and default colors")
    print("2. Multi-line highlighting: Standard Qt should handle this automatically")
    print("3. Area outlines: Need actual area data in corrections")