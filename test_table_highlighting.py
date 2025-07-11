#!/usr/bin/env python3
"""
Test if table highlighting is working correctly.
"""

import sys
import os
import json
sys.path.insert(0, '/home/insulto/tore_matrix_labs')

def test_table_corrections():
    """Test table correction detection."""
    print("=== TESTING TABLE CORRECTIONS ===")
    
    # Load project data
    with open('/home/insulto/tore_matrix_labs/4.tore', 'r') as f:
        data = json.load(f)
    
    corrections = data['documents'][0]['processing_data']['corrections']
    
    # Find table corrections
    table_corrections = []
    for i, correction in enumerate(corrections):
        desc = correction.get('description', '').lower()
        if 'table' in desc:
            table_corrections.append((i, correction))
    
    print(f"Found {len(table_corrections)} table corrections")
    
    # Test the first table correction
    if table_corrections:
        idx, correction = table_corrections[0]
        print(f"\nFirst table correction (index {idx}):")
        print(f"  Description: {correction.get('description', '')}")
        print(f"  Type: {correction.get('type', '')}")
        print(f"  Page: {correction.get('location', {}).get('page', '')}")
        print(f"  Bbox: {correction.get('location', {}).get('bbox', [])}")
        print(f"  Manual validation status: {correction.get('manual_validation_status', 'not_validated')}")
        
        # Test highlight type detection
        def get_highlight_type(issue):
            issue_type = issue.get('type', 'ocr_correction')
            description = issue.get('description', '').lower()
            manual_validation_status = issue.get('manual_validation_status', 'not_validated')
            
            if manual_validation_status == 'approved':
                if 'table' in description:
                    return 'manual_table'
            
            if manual_validation_status == 'not_validated':
                if 'table' in description and ('rows' in description or 'empty cells' in description):
                    return 'auto_detected_table'
            
            if issue_type == 'ocr_correction':
                return 'active_issue'
            else:
                return 'issue'
        
        highlight_type = get_highlight_type(correction)
        print(f"  Highlight type: {highlight_type}")
        
        # Test multiline regions creation
        def create_multiline_regions(bbox, description, highlight_type):
            if not bbox or len(bbox) < 4:
                return bbox
            
            x0, y0, x1, y1 = bbox[:4]
            
            if highlight_type in ['auto_detected_table', 'auto_detected_image', 'auto_detected_diagram']:
                enhanced_bbox = {
                    'regions': [
                        [x0, y0, x1, y1]
                    ],
                    'original_bbox': bbox,
                    'confidence': 1.0,
                    'match_type': 'auto_detected_area',
                    'area_type': highlight_type
                }
                return enhanced_bbox
            
            return bbox
        
        bbox = correction.get('location', {}).get('bbox', [])
        enhanced_bbox = create_multiline_regions(bbox, correction.get('description', ''), highlight_type)
        
        print(f"  Enhanced bbox: {enhanced_bbox}")
        
        # Calculate bbox dimensions
        if isinstance(bbox, list) and len(bbox) >= 4:
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            print(f"  Bbox dimensions: {width:.1f} x {height:.1f}")

def main():
    test_table_corrections()

if __name__ == "__main__":
    main()