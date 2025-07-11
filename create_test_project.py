#!/usr/bin/env python3
"""
Create a test project with the processed document to verify the workflow.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def create_test_project():
    """Create a test project with the processed document."""
    print("=== Creating Test Project ===")
    
    # Load the processed document data
    output_file = Path("output/5555_complete.json")
    if not output_file.exists():
        print(f"❌ Output file not found: {output_file}")
        return
        
    with open(output_file, 'r') as f:
        processing_data = json.load(f)
    
    doc_info = processing_data.get('document_info', {})
    quality_assessment = processing_data.get('quality_assessment', {})
    issues = quality_assessment.get('issues', [])
    
    print(f"✅ Loaded processed document: {doc_info.get('file_name')}")
    print(f"   Document ID: {doc_info.get('id')}")
    print(f"   Quality issues: {len(issues)}")
    
    # Create a test project with the document
    project_data = {
        "name": "Test Project with Document",
        "description": "Test project containing processed document with corrections",
        "created_at": datetime.now().isoformat(),
        "modified_at": datetime.now().isoformat(),
        "version": "1.0.0",
        "documents": [
            {
                "id": doc_info.get('id', 'unknown'),
                "path": "/home/insulto/tore_matrix_labs/5555.pdf",
                "name": doc_info.get('file_name', '5555.pdf'),
                "added_at": datetime.now().isoformat(),
                "status": "processed",
                "processing_data": {
                    "file_size": doc_info.get('file_size', 0),
                    "page_count": processing_data.get('processing_summary', {}).get('content_metrics', {}).get('page_count', 0),
                    "corrections_count": len(issues),
                    "quality_score": quality_assessment.get('overall_score', 0.0),
                    "quality_level": quality_assessment.get('quality_level', 'unknown')
                }
            }
        ]
    }
    
    # Save the test project
    project_file = Path("test_project.tore")
    with open(project_file, 'w') as f:
        json.dump(project_data, f, indent=2)
    
    print(f"✅ Created test project: {project_file}")
    print(f"   Project contains 1 document with {len(issues)} corrections")
    print(f"   Document path: /home/insulto/tore_matrix_labs/5555.pdf")
    print(f"\n🎯 To test:")
    print(f"   1. Start the application")
    print(f"   2. Open project: {project_file}")
    print(f"   3. Should see document in project tree")
    print(f"   4. Click document → should preview in PDF viewer")
    print(f"   5. Go to QA Validation → should see corrections")

if __name__ == "__main__":
    create_test_project()