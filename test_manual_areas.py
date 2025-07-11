#!/usr/bin/env python3
"""
Test if manual areas are being detected properly.
"""

import sys
import os
import json
sys.path.insert(0, '/home/insulto/tore_matrix_labs')

def test_manual_area_detection():
    """Test manual area detection."""
    print("=== TESTING MANUAL AREA DETECTION ===")
    
    # Load project data
    with open('/home/insulto/tore_matrix_labs/4.tore', 'r') as f:
        data = json.load(f)
    
    corrections = data['documents'][0]['processing_data']['corrections']
    print(f"Total corrections: {len(corrections)}")
    
    # Find manual areas
    manual_areas = []
    for i, correction in enumerate(corrections):
        if correction.get('type') == 'manual_area':
            manual_areas.append((i, correction))
    
    print(f"Found {len(manual_areas)} manual areas")
    
    # Test highlight type detection for manual areas
    def get_highlight_type(issue):
        issue_type = issue.get('type', 'ocr_correction')
        description = issue.get('description', '').lower()
        manual_validation_status = issue.get('manual_validation_status', 'not_validated')
        
        # Check if it's a manually created area
        is_manual_area = (issue_type == 'manual_area' or 
                         'manual' in description or 
                         issue.get('area_type') in ['image', 'table', 'diagram'])
        
        # Auto-detected areas have specific patterns
        is_auto_detected = ('has only' in description and 'rows' in description) or \
                          ('empty cells' in description and 'threshold' in description)
        
        # If it's a manual area, treat as approved
        if is_manual_area and not is_auto_detected:
            manual_validation_status = 'approved'
        
        # Only highlight areas that have been manually validated or are manually created
        if manual_validation_status == 'approved':
            # Check area_type field first, then fall back to description
            area_type = issue.get('area_type', '')
            if area_type == 'image' or 'image' in description:
                return 'manual_image'
            elif area_type == 'table' or 'table' in description:
                return 'manual_table'
            elif area_type == 'diagram' or 'diagram' in description:
                return 'manual_diagram'
        
        if issue_type == 'ocr_correction':
            return 'active_issue'
        else:
            return 'issue'
    
    # Test each manual area
    for i, (idx, correction) in enumerate(manual_areas):
        print(f"\nManual area {i+1} (index {idx}):")
        print(f"  Type: {correction.get('type', '')}")
        print(f"  Description: {correction.get('description', '')}")
        print(f"  Area type: {correction.get('area_type', '')}")
        print(f"  Page: {correction.get('location', {}).get('page', '')}")
        print(f"  Bbox: {correction.get('location', {}).get('bbox', [])}")
        print(f"  Manual validation status: {correction.get('manual_validation_status', 'not_set')}")
        
        highlight_type = get_highlight_type(correction)
        print(f"  Highlight type: {highlight_type}")
        
        if highlight_type in ['manual_image', 'manual_table', 'manual_diagram']:
            print(f"  ✓ Should show {highlight_type.replace('manual_', '')} highlighting")
        else:
            print(f"  ✗ Will not show proper highlighting")

if __name__ == "__main__":
    test_manual_area_detection()