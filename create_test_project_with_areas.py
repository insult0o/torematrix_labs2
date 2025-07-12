#!/usr/bin/env python3
"""
Create a test project file with visual areas to test area restoration.
"""

import json
import sys
from pathlib import Path

def create_test_project():
    """Create a test project with visual areas."""
    
    project_data = {
        "project_id": "test_area_persistence",
        "project_name": "Test Area Persistence",
        "version": "1.0",
        "created_at": "2025-07-12T10:00:00",
        "documents": [
            {
                "id": "test_doc_with_areas",
                "name": "test_document.pdf",
                "path": "/home/insulto/tore_matrix_labs/5555.pdf",  # Use existing PDF
                "visual_areas": {
                    "area_001": {
                        "id": "area_001",
                        "page": 1,
                        "bbox": [100, 100, 300, 200],
                        "area_type": "IMAGE",
                        "text": "Test area 1",
                        "status": "approved",
                        "processing_options": {
                            "high_quality": True,
                            "preserve_aspect_ratio": True
                        }
                    },
                    "area_002": {
                        "id": "area_002", 
                        "page": 1,
                        "bbox": [400, 150, 600, 250],
                        "area_type": "TABLE",
                        "text": "Test area 2", 
                        "status": "pending",
                        "processing_options": {
                            "extract_borders": True,
                            "preserve_formatting": True
                        }
                    },
                    "area_003": {
                        "id": "area_003",
                        "page": 2, 
                        "bbox": [50, 50, 250, 150],
                        "area_type": "DIAGRAM",
                        "text": "Test area 3",
                        "status": "approved",
                        "processing_options": {
                            "vectorize": True,
                            "preserve_colors": True
                        }
                    }
                },
                "processing_data": {
                    "status": "completed",
                    "page_count": 6,
                    "visual_areas": {
                        "area_processing_001": {
                            "id": "area_processing_001",
                            "page": 2,
                            "bbox": [300, 300, 500, 400],
                            "area_type": "IMAGE",
                            "text": "Processing area 1",
                            "status": "pending"
                        }
                    }
                }
            }
        ]
    }
    
    # Save to test project file
    test_project_path = "/home/insulto/tore_matrix_labs/test_area_project.tore"
    
    with open(test_project_path, 'w', encoding='utf-8') as f:
        json.dump(project_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Created test project with areas: {test_project_path}")
    print(f"📊 Project contains 1 document with 4 total areas:")
    print(f"   - 3 direct visual areas (area_001, area_002, area_003)")
    print(f"   - 1 processing area (area_processing_001)")
    
    return test_project_path

if __name__ == "__main__":
    create_test_project()