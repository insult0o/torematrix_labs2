#!/usr/bin/env python3
"""
Remove test manual areas from project file.
"""

import json

def remove_manual_areas():
    """Remove manual areas from project file."""
    
    with open('/home/insulto/tore_matrix_labs/4.tore', 'r') as f:
        data = json.load(f)
        
    corrections = data['documents'][0]['processing_data']['corrections']
    print(f'Before: {len(corrections)} corrections')

    # Remove manual areas
    corrections = [c for c in corrections if c.get('type') != 'manual_area']
    print(f'After removal: {len(corrections)} corrections')

    data['documents'][0]['processing_data']['corrections'] = corrections
    data['documents'][0]['processing_data']['corrections_count'] = len(corrections)

    with open('/home/insulto/tore_matrix_labs/4.tore', 'w') as f:
        json.dump(data, f, indent=2)
        
    print('Manual areas removed')

if __name__ == "__main__":
    remove_manual_areas()