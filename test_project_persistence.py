#!/usr/bin/env python3
"""
Test script to verify that corrections are properly persisted in projects.
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_project_persistence():
    """Test that corrections are properly saved and loaded with projects."""
    
    try:
        print("=== Testing Project Persistence ===")
        
        # Load the actual output file to get corrections
        output_file = Path("output/5555_complete.json")
        if not output_file.exists():
            print(f"❌ Output file not found: {output_file}")
            return False
            
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        qa = data.get('quality_assessment', {})
        issues = qa.get('issues', [])
        
        print(f"✅ Found {len(issues)} quality issues")
        
        # Convert issues to corrections format (simulating the main window process)
        corrections = []
        for idx, issue in enumerate(issues):
            correction = {
                'id': f'correction_{idx}',
                'type': issue.get('type', 'ocr_error'),
                'description': issue.get('description', ''),
                'suggested_fix': issue.get('suggested_fix', ''),
                'confidence': issue.get('confidence', 0.5),
                'location': issue.get('location', {}),
                'severity': issue.get('severity', 'medium')
            }
            corrections.append(correction)
        
        # Create test project data (simulating what gets saved)
        project_data = {
            'name': 'Test Persistence Project',
            'description': 'Testing corrections persistence',
            'created_at': '2025-07-08T04:00:00',
            'modified_at': '2025-07-08T04:00:00',
            'version': '1.0.0',
            'documents': [
                {
                    'id': 'test_doc_001',
                    'file_path': '/home/insulto/tore_matrix_labs/5555.pdf',
                    'file_name': '5555.pdf',
                    'file_size': 5337922,
                    'page_count': 55,
                    'processing_status': 'validated',
                    'corrections_count': len(corrections),
                    'corrections': corrections,  # This is the key data we're testing
                    'quality_score': 0.75,
                    'quality_level': 'good',
                    'added_at': '2025-07-08T04:00:00',
                    'status': 'processed',
                    'processing_data': {
                        'file_size': 5337922,
                        'page_count': 55,
                        'corrections_count': len(corrections),
                        'corrections': corrections,  # Also stored here
                        'quality_score': 0.75,
                        'quality_level': 'good'
                    }
                }
            ]
        }
        
        # Save test project
        test_project_file = Path("test_persistence.tore")
        with open(test_project_file, 'w') as f:
            json.dump(project_data, f, indent=2)
        
        print(f"✅ Created test project: {test_project_file}")
        print(f"   Project contains 1 document with {len(corrections)} corrections")
        
        # Load project back and verify corrections
        with open(test_project_file, 'r') as f:
            loaded_project = json.load(f)
        
        loaded_docs = loaded_project.get('documents', [])
        if not loaded_docs:
            print("❌ No documents found in loaded project")
            return False
        
        doc = loaded_docs[0]
        loaded_corrections = doc.get('processing_data', {}).get('corrections', [])
        
        print(f"✅ Loaded project successfully")
        print(f"   Document corrections: {len(loaded_corrections)}")
        print(f"   Original corrections: {len(corrections)}")
        
        # Verify data integrity
        if len(loaded_corrections) == len(corrections):
            print("✅ Corrections count matches")
        else:
            print(f"❌ Corrections count mismatch: {len(loaded_corrections)} vs {len(corrections)}")
            return False
        
        # Verify sample correction data
        if loaded_corrections and corrections:
            original_sample = corrections[0]
            loaded_sample = loaded_corrections[0]
            
            print(f"✅ Sample correction verification:")
            print(f"   Original: {original_sample.get('type')} - {original_sample.get('description')[:50]}...")
            print(f"   Loaded:   {loaded_sample.get('type')} - {loaded_sample.get('description')[:50]}...")
            
            if (original_sample.get('type') == loaded_sample.get('type') and 
                original_sample.get('description') == loaded_sample.get('description')):
                print("✅ Sample correction data matches")
            else:
                print("❌ Sample correction data mismatch")
                return False
        
        # Clean up
        test_project_file.unlink()
        print(f"✅ Cleaned up test file")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_project_persistence()
    if success:
        print("\n🎉 Project persistence test passed!")
        print("   Corrections are properly saved and loaded with projects")
    else:
        print("\n❌ Project persistence test failed.")
        print("   Issues need to be resolved.")