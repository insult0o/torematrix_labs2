#!/usr/bin/env python3
"""
Add manual selections to the project file for testing.
"""

import json
import sys
from datetime import datetime

def add_manual_selections():
    """Add manual selections to test highlighting."""
    
    # Load the project file
    with open('/home/insulto/tore_matrix_labs/4.tore', 'r') as f:
        data = json.load(f)
    
    corrections = data['documents'][0]['processing_data']['corrections']
    
    # Add some manual selections for testing
    manual_selections = [
        {
            "id": "manual_image_1",
            "type": "manual_area",
            "description": "Manual image area selection",
            "confidence": 1.0,
            "reasoning": "User manually selected image area",
            "status": "approved",
            "location": {
                "page": 5,
                "bbox": [100, 200, 300, 400],  # Example bbox
                "text_position": []
            },
            "severity": "info",
            "manual_validation_status": "approved",
            "area_type": "image",
            "created_at": datetime.now().isoformat()
        },
        {
            "id": "manual_table_1", 
            "type": "manual_area",
            "description": "Manual table area selection",
            "confidence": 1.0,
            "reasoning": "User manually selected table area",
            "status": "approved",
            "location": {
                "page": 10,
                "bbox": [50, 150, 500, 350],  # Example bbox
                "text_position": []
            },
            "severity": "info",
            "manual_validation_status": "approved",
            "area_type": "table",
            "created_at": datetime.now().isoformat()
        },
        {
            "id": "manual_diagram_1",
            "type": "manual_area", 
            "description": "Manual diagram area selection",
            "confidence": 1.0,
            "reasoning": "User manually selected diagram area",
            "status": "approved",
            "location": {
                "page": 15,
                "bbox": [80, 100, 400, 300],  # Example bbox
                "text_position": []
            },
            "severity": "info",
            "manual_validation_status": "approved",
            "area_type": "diagram",
            "created_at": datetime.now().isoformat()
        }
    ]
    
    # Add manual selections to corrections
    corrections.extend(manual_selections)
    
    # Update corrections count
    data['documents'][0]['processing_data']['corrections_count'] = len(corrections)
    
    # Save back to file
    with open('/home/insulto/tore_matrix_labs/4.tore', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Added {len(manual_selections)} manual selections to project file")
    print(f"Total corrections now: {len(corrections)}")
    print("\nManual selections added:")
    for selection in manual_selections:
        print(f"  - {selection['area_type']} on page {selection['location']['page']}")

if __name__ == "__main__":
    add_manual_selections()