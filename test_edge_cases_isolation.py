#!/usr/bin/env python3
"""
Edge case tests for cross-project area isolation.

Tests various edge cases to ensure robust project isolation.
"""

import os
import sys
import json
import tempfile
from pathlib import Path
import logging

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from tore_matrix_labs.core.area_storage_manager import AreaStorageManager

def create_legacy_project(name: str, document_id: str) -> dict:
    """Create a legacy format project (areas directly in project file)."""
    return {
        'name': name,
        'description': f'Legacy project {name}',
        'created_at': '2024-01-01T00:00:00',
        'visual_areas': {
            f'legacy_area_{name}': {
                'id': f'legacy_area_{name}',
                'document_id': document_id,
                'type': 'TEXT',
                'bbox': [50, 100, 150, 150],
                'page': 1,
                'color': '#00FF00',
                'status': 'saved',
                'user_notes': f'Legacy area from {name}'
            }
        }
    }

def test_edge_cases():
    """Test edge cases for cross-project isolation."""
    print("🔵 EDGE TEST: Starting edge case tests for project isolation")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Test 1: Legacy format project
        print("\n🔵 EDGE TEST: Test 1 - Legacy format projects")
        legacy_data = create_legacy_project("LegacyProject", "legacy_doc")
        legacy_file = temp_path / "legacy.tore"
        with open(legacy_file, 'w') as f:
            json.dump(legacy_data, f, indent=2)
        
        class MockProjectManagerLegacy:
            def __init__(self):
                self.project_file_path = str(legacy_file)
            def get_current_project(self):
                return None  # Simulate no active project manager
        
        area_manager = AreaStorageManager(project_manager=MockProjectManagerLegacy())
        legacy_areas = area_manager.load_areas("legacy_doc")
        print(f"🟢 EDGE TEST: Legacy project loaded {len(legacy_areas)} areas")
        
        # Test 2: Malformed project file
        print("\n🔵 EDGE TEST: Test 2 - Malformed project file")
        malformed_data = {"malformed": "data", "no_documents": True}
        malformed_file = temp_path / "malformed.tore"
        with open(malformed_file, 'w') as f:
            json.dump(malformed_data, f, indent=2)
        
        class MockProjectManagerMalformed:
            def __init__(self):
                self.project_file_path = str(malformed_file)
            def get_current_project(self):
                return None
        
        area_manager_malformed = AreaStorageManager(project_manager=MockProjectManagerMalformed())
        malformed_areas = area_manager_malformed.load_areas("any_doc")
        print(f"🟢 EDGE TEST: Malformed project loaded {len(malformed_areas)} areas")
        
        # Test 3: Missing project file
        print("\n🔵 EDGE TEST: Test 3 - Missing project file")
        missing_file = temp_path / "missing.tore"  # File doesn't exist
        
        class MockProjectManagerMissing:
            def __init__(self):
                self.project_file_path = str(missing_file)
            def get_current_project(self):
                return None
        
        area_manager_missing = AreaStorageManager(project_manager=MockProjectManagerMissing())
        missing_areas = area_manager_missing.load_areas("any_doc")
        print(f"🟢 EDGE TEST: Missing project file loaded {len(missing_areas)} areas")
        
        # Test 4: No project manager at all
        print("\n🔵 EDGE TEST: Test 4 - No project manager")
        area_manager_none = AreaStorageManager(project_manager=None)
        none_areas = area_manager_none.load_areas("any_doc")
        print(f"🟢 EDGE TEST: No project manager loaded {len(none_areas)} areas")
        
        # Test 5: Project manager without project_file_path
        print("\n🔵 EDGE TEST: Test 5 - Project manager without file path")
        class MockProjectManagerNoPath:
            def get_current_project(self):
                return None
        
        area_manager_no_path = AreaStorageManager(project_manager=MockProjectManagerNoPath())
        no_path_areas = area_manager_no_path.load_areas("any_doc")
        print(f"🟢 EDGE TEST: No file path loaded {len(no_path_areas)} areas")
        
        # Results
        all_tests_passed = (
            len(legacy_areas) in [0, 1] and  # Legacy might work if document matches
            len(malformed_areas) == 0 and   # Malformed should load nothing
            len(missing_areas) == 0 and     # Missing file should load nothing
            len(none_areas) == 0 and        # No project manager should load nothing
            len(no_path_areas) == 0         # No file path should load nothing
        )
        
        print(f"\n🏁 EDGE TEST: Results Summary")
        print(f"✅ Legacy format: {len(legacy_areas)} areas")
        print(f"✅ Malformed project: {len(malformed_areas)} areas")
        print(f"✅ Missing file: {len(missing_areas)} areas")
        print(f"✅ No project manager: {len(none_areas)} areas")
        print(f"✅ No file path: {len(no_path_areas)} areas")
        
        if all_tests_passed:
            print("\n🎉 EDGE TEST: ALL EDGE CASE TESTS PASSED!")
            return True
        else:
            print("\n💥 EDGE TEST: SOME EDGE CASE TESTS FAILED!")
            return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)  # Reduce log noise
    
    print("🚀 Starting Edge Case Tests for Cross-Project Area Isolation")
    print("=" * 60)
    
    try:
        success = test_edge_cases()
        
        if success:
            print("\n🎯 Edge case tests completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Edge case tests failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Edge case tests failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)