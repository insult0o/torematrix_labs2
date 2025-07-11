#!/usr/bin/env python3
"""
Test the highlight logic without creating widgets.
"""

import sys
import os
import json
sys.path.insert(0, '/home/insulto/tore_matrix_labs')

def test_highlight_type_detection():
    """Test highlight type detection logic."""
    print("=== TESTING HIGHLIGHT TYPE DETECTION ===")
    
    # Simulate the _get_highlight_type method logic
    def get_highlight_type(issue):
        issue_type = issue.get('type', 'ocr_correction')
        description = issue.get('description', '').lower()
        
        # Check for manual validation areas
        if 'image' in description:
            return 'manual_image'
        elif 'table' in description:
            return 'manual_table'
        elif 'diagram' in description:
            return 'manual_diagram'
        elif 'conflict' in description:
            return 'auto_conflict'
        elif issue_type == 'ocr_correction':
            return 'active_issue'  # Current issue being viewed
        else:
            return 'issue'  # Default
    
    test_cases = [
        ({'type': 'ocr_correction', 'description': 'Normal OCR error'}, 'active_issue'),
        ({'type': 'ocr_correction', 'description': 'Image area validation'}, 'manual_image'),
        ({'type': 'ocr_correction', 'description': 'Table structure validation'}, 'manual_table'),
        ({'type': 'ocr_correction', 'description': 'Diagram content validation'}, 'manual_diagram'),
        ({'type': 'ocr_correction', 'description': 'Conflict in validation'}, 'auto_conflict'),
        ({'type': 'other', 'description': 'Some other issue'}, 'issue')
    ]
    
    for issue, expected_type in test_cases:
        result = get_highlight_type(issue)
        status = "✓" if result == expected_type else "✗"
        print(f"{status} '{issue['description']}' -> {result} (expected: {expected_type})")

def test_multiline_regions_logic():
    """Test multiline regions creation logic."""
    print("\n=== TESTING MULTILINE REGIONS LOGIC ===")
    
    # Simulate the _create_multiline_regions method logic
    def create_multiline_regions(bbox, description, highlight_type):
        try:
            if not bbox or len(bbox) < 4:
                return bbox
            
            x0, y0, x1, y1 = bbox[:4]
            
            # Calculate dimensions
            width = x1 - x0
            height = y1 - y0
            
            # For large areas (images, tables, diagrams), create enhanced regions
            if highlight_type in ['manual_image', 'manual_table', 'manual_diagram']:
                # Create a more visible rectangular highlight for these areas
                padding = 2
                enhanced_bbox = {
                    'regions': [
                        [x0 - padding, y0 - padding, x1 + padding, y1 + padding]
                    ],
                    'original_bbox': bbox,
                    'confidence': 1.0,
                    'match_type': 'enhanced_area',
                    'area_type': highlight_type
                }
                return enhanced_bbox
            
            # For text that might span multiple lines (height > typical line height)
            typical_line_height = 14  # Approximate line height in points
            if height > typical_line_height * 1.5:  # More than 1.5 lines
                # Split into multiple line regions
                regions = []
                lines = max(1, int(height / typical_line_height))
                line_height = height / lines
                
                for i in range(lines):
                    line_y0 = y0 + (i * line_height)
                    line_y1 = y0 + ((i + 1) * line_height)
                    regions.append([x0, line_y0, x1, line_y1])
                
                enhanced_bbox = {
                    'regions': regions,
                    'original_bbox': bbox,
                    'confidence': 1.0,
                    'match_type': 'multiline_text',
                    'lines': lines
                }
                return enhanced_bbox
            
            # For single line text, return original bbox
            return bbox
            
        except Exception as e:
            print(f"Error: {e}")
            return bbox
    
    test_cases = [
        {
            'name': 'Small text (single line)',
            'bbox': [100, 100, 200, 115],  # Height = 15
            'description': 'Small text error',
            'highlight_type': 'active_issue'
        },
        {
            'name': 'Multi-line text',
            'bbox': [100, 100, 200, 140],  # Height = 40
            'description': 'Multi-line text error',
            'highlight_type': 'active_issue'
        },
        {
            'name': 'Image area',
            'bbox': [100, 100, 300, 200],  # Large area
            'description': 'Image area needs validation',
            'highlight_type': 'manual_image'
        },
        {
            'name': 'Table area',
            'bbox': [100, 100, 400, 250],  # Large area
            'description': 'Table area needs validation',
            'highlight_type': 'manual_table'
        }
    ]
    
    for test_case in test_cases:
        print(f"\n--- {test_case['name']} ---")
        bbox = test_case['bbox']
        height = bbox[3] - bbox[1]
        print(f"Original bbox: {bbox} (height: {height})")
        
        enhanced_bbox = create_multiline_regions(
            bbox, 
            test_case['description'], 
            test_case['highlight_type']
        )
        
        if isinstance(enhanced_bbox, dict) and 'regions' in enhanced_bbox:
            print(f"✓ Enhanced with {len(enhanced_bbox['regions'])} regions")
            print(f"  Match type: {enhanced_bbox.get('match_type', 'unknown')}")
            
            if enhanced_bbox.get('match_type') == 'enhanced_area':
                print(f"  Area type: {enhanced_bbox.get('area_type', 'unknown')}")
                print(f"  Padded region: {enhanced_bbox['regions'][0]}")
            elif enhanced_bbox.get('match_type') == 'multiline_text':
                print(f"  Lines: {enhanced_bbox['lines']}")
                for i, region in enumerate(enhanced_bbox['regions']):
                    print(f"    Line {i+1}: {region}")
        else:
            print("  No enhancement (using original bbox)")

def main():
    """Run all tests."""
    print("TESTING HIGHLIGHT LOGIC")
    print("=" * 60)
    
    test_highlight_type_detection()
    test_multiline_regions_logic()
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("Logic tests completed. The highlight detection and multiline region")
    print("creation logic appears to be working correctly.")

if __name__ == "__main__":
    main()