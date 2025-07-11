#!/usr/bin/env python3
"""
Check what's actually stored in the .tore file after creating areas.
"""

import json
import sys
from pathlib import Path

def check_tore_file(file_path):
    """Check the contents of a .tore file for visual areas."""
    try:
        print(f"🔍 CHECKING TORE FILE: {file_path}")
        print("=" * 60)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📊 PROJECT INFO:")
        print(f"   Name: {data.get('name', 'Unknown')}")
        print(f"   Created: {data.get('created_at', 'Unknown')}")
        print(f"   Modified: {data.get('modified_at', 'Unknown')}")
        print()
        
        documents = data.get('documents', [])
        print(f"📄 DOCUMENTS: {len(documents)} total")
        print()
        
        for i, doc in enumerate(documents):
            doc_id = doc.get('id', 'Unknown')
            doc_name = doc.get('name', 'Unknown')
            visual_areas = doc.get('visual_areas', {})
            
            print(f"   Document {i+1}:")
            print(f"      ID: {doc_id}")
            print(f"      Name: {doc_name}")
            print(f"      Visual Areas: {len(visual_areas)}")
            
            if visual_areas:
                print(f"      📍 AREAS FOUND:")
                for area_id, area_data in visual_areas.items():
                    page = area_data.get('page', 'Unknown')
                    bbox = area_data.get('bbox', 'Unknown')
                    area_type = area_data.get('type', 'Unknown')
                    print(f"         {area_id}: page={page}, type={area_type}, bbox={bbox}")
            else:
                print(f"      ❌ NO VISUAL AREAS FOUND")
            print()
        
        if not any(doc.get('visual_areas') for doc in documents):
            print("❌ NO AREAS FOUND IN ANY DOCUMENT")
            print("   This means areas are not being saved to the .tore file")
        else:
            print("✅ AREAS FOUND IN TORE FILE")
            print("   Areas are being saved properly")
        
    except FileNotFoundError:
        print(f"❌ FILE NOT FOUND: {file_path}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON DECODE ERROR: {e}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_tore_file.py <path_to_tore_file>")
        print("Example: python check_tore_file.py ./4.tore")
        sys.exit(1)
    
    file_path = sys.argv[1]
    check_tore_file(file_path)