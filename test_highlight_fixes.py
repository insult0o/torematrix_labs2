#!/usr/bin/env python3
"""
Test the highlight fixes to see if they're working correctly.
"""

import sys
import os
import json
sys.path.insert(0, '/home/insulto/tore_matrix_labs')

from tore_matrix_labs.config.settings import Settings
from tore_matrix_labs.ui.components.page_validation_widget import PageValidationWidget
from pathlib import Path

def test_multiline_regions():
    """Test the multiline regions creation."""
    print("=== TESTING MULTILINE REGIONS CREATION ===")
    
    # Create a widget instance
    settings = Settings()
    widget = PageValidationWidget(settings)
    
    # Test different scenarios
    test_cases = [
        {
            'name': 'Small text (single line)',
            'bbox': [100, 100, 200, 115],  # Small height
            'description': 'Small text error',
            'expected_type': 'active_issue'
        },
        {
            'name': 'Multi-line text',
            'bbox': [100, 100, 200, 140],  # Height = 40, > 1.5 * 14 = 21
            'description': 'Multi-line text error',
            'expected_type': 'active_issue'
        },
        {
            'name': 'Image area',
            'bbox': [100, 100, 300, 200],  # Large area
            'description': 'Image area needs validation',
            'expected_type': 'manual_image'
        },
        {
            'name': 'Table area',
            'bbox': [100, 100, 400, 250],  # Large area
            'description': 'Table area needs validation',
            'expected_type': 'manual_table'
        },
        {
            'name': 'Diagram area',
            'bbox': [100, 100, 350, 300],  # Large area
            'description': 'Diagram area needs validation',
            'expected_type': 'manual_diagram'
        }
    ]
    
    for test_case in test_cases:
        print(f"\n--- Testing: {test_case['name']} ---")
        
        # Create a mock issue
        issue = {
            'type': 'ocr_correction',
            'description': test_case['description'],
            'location': {
                'bbox': test_case['bbox']
            }
        }
        
        # Get highlight type
        highlight_type = widget._get_highlight_type(issue)
        print(f"Highlight type: {highlight_type} (expected: {test_case['expected_type']})")
        
        # Test multiline regions creation
        enhanced_bbox = widget._create_multiline_regions(
            test_case['bbox'], 
            test_case['description'], 
            highlight_type
        )
        
        print(f"Original bbox: {test_case['bbox']}")
        print(f"Enhanced bbox: {enhanced_bbox}")
        
        # Check if it was enhanced
        if isinstance(enhanced_bbox, dict) and 'regions' in enhanced_bbox:
            print(f"✓ Enhanced with {len(enhanced_bbox['regions'])} regions")
            print(f"  Match type: {enhanced_bbox.get('match_type', 'unknown')}")
            
            if highlight_type in ['manual_image', 'manual_table', 'manual_diagram']:
                print(f"  Area type: {enhanced_bbox.get('area_type', 'unknown')}")
            elif 'lines' in enhanced_bbox:
                print(f"  Lines: {enhanced_bbox['lines']}")
        else:
            print("  No enhancement (using original bbox)")
        
        print("  " + "="*50)

def test_highlight_colors():
    """Test highlight color detection."""
    print("\n=== TESTING HIGHLIGHT COLOR DETECTION ===")
    
    # Create a widget instance
    settings = Settings()
    widget = PageValidationWidget(settings)
    
    test_descriptions = [
        ('Normal OCR error', 'active_issue'),
        ('Image area validation', 'manual_image'),
        ('Table structure validation', 'manual_table'), 
        ('Diagram content validation', 'manual_diagram'),
        ('Some random text', 'active_issue')
    ]
    
    for description, expected_type in test_descriptions:
        issue = {
            'type': 'ocr_correction',
            'description': description
        }
        
        highlight_type = widget._get_highlight_type(issue)
        print(f"Description: '{description}' -> Type: {highlight_type} (expected: {expected_type})")
        
        if highlight_type == expected_type:
            print("  ✓ Correct")
        else:
            print("  ✗ Incorrect")

def main():
    """Run all tests."""
    print("TESTING HIGHLIGHT FIXES")
    print("=" * 60)
    
    test_multiline_regions()
    test_highlight_colors()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("Tests completed. Check the output above for any issues.")
    print("\nExpected behavior:")
    print("1. ✓ Small text should use original bbox")
    print("2. ✓ Multi-line text should create multiple regions")
    print("3. ✓ Image/table/diagram areas should create enhanced regions with padding")
    print("4. ✓ Highlight types should be detected correctly from descriptions")

if __name__ == "__main__":
    main()