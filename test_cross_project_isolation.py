#!/usr/bin/env python3
"""
Test script for cross-project area isolation fix.

This test verifies that areas from one project don't leak into another project,
ensuring complete project isolation for visual areas.
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
from tore_matrix_labs.models.visual_area_models import VisualArea, AreaType, AreaStatus
from tore_matrix_labs.ui.components.project_manager_widget import ProjectManagerWidget

def setup_logging():
    """Setup logging for testing."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def create_test_project(name: str, document_id: str, areas_count: int = 2) -> dict:
    """Create a test project with visual areas."""
    project_data = {
        'name': name,
        'description': f'Test project {name}',
        'created_at': '2024-01-01T00:00:00',
        'modified_at': '2024-01-01T00:00:00',
        'version': '1.0.0',
        'documents': [{
            'id': document_id,
            'name': f'{document_id}.pdf',
            'path': f'/test/path/{document_id}.pdf',
            'status': 'processed',
            'visual_areas': {}
        }]
    }
    
    # Add visual areas to the document
    for i in range(areas_count):
        area_id = f"area_{name}_{i}"
        area_data = {
            'id': area_id,
            'document_id': document_id,
            'type': 'TEXT',
            'bbox': [100 + i*50, 200 + i*30, 200 + i*50, 250 + i*30],
            'page': 1,
            'color': '#FF4444',
            'status': 'saved',
            'created_at': '2024-01-01T00:00:00',
            'modified_at': '2024-01-01T00:00:00',
            'user_notes': f'Test area {i} from project {name}',
            'border_width': 2,
            'fill_opacity': 0.3,
            'border_glow': True,
            'widget_rect': None
        }
        project_data['documents'][0]['visual_areas'][area_id] = area_data
    
    return project_data

def test_cross_project_isolation():
    """Test that areas from different projects don't leak into each other."""
    print("🔵 ISOLATION TEST: Starting cross-project area isolation test")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create Project A with areas
        project_a_data = create_test_project("ProjectA", "doc_a", 3)
        project_a_file = temp_path / "project_a.tore"
        with open(project_a_file, 'w') as f:
            json.dump(project_a_data, f, indent=2)
        print(f"🟢 ISOLATION TEST: Created Project A at {project_a_file}")
        print(f"   - Document: doc_a")
        print(f"   - Areas: {len(project_a_data['documents'][0]['visual_areas'])}")
        
        # Create Project B with areas
        project_b_data = create_test_project("ProjectB", "doc_b", 2)
        project_b_file = temp_path / "project_b.tore"
        with open(project_b_file, 'w') as f:
            json.dump(project_b_data, f, indent=2)
        print(f"🟢 ISOLATION TEST: Created Project B at {project_b_file}")
        print(f"   - Document: doc_b")
        print(f"   - Areas: {len(project_b_data['documents'][0]['visual_areas'])}")
        
        # Test 1: Load areas from Project A
        print("\n🔵 ISOLATION TEST: Test 1 - Loading areas from Project A")
        
        # Create mock project manager for Project A
        class MockProjectManagerA:
            def __init__(self):
                self.project_file_path = str(project_a_file)
                self.current_project_data = project_a_data
            
            def get_current_project(self):
                return self.current_project_data
        
        area_manager_a = AreaStorageManager(project_manager=MockProjectManagerA())
        areas_a = area_manager_a.load_areas("doc_a")
        
        print(f"🟢 ISOLATION TEST: Project A loaded {len(areas_a)} areas for doc_a")
        for area_id, area in areas_a.items():
            print(f"   - {area_id}: {area.user_notes}")
        
        # Test 2: Load areas from Project B
        print("\n🔵 ISOLATION TEST: Test 2 - Loading areas from Project B")
        
        # Create mock project manager for Project B
        class MockProjectManagerB:
            def __init__(self):
                self.project_file_path = str(project_b_file)
                self.current_project_data = project_b_data
            
            def get_current_project(self):
                return self.current_project_data
        
        area_manager_b = AreaStorageManager(project_manager=MockProjectManagerB())
        areas_b = area_manager_b.load_areas("doc_b")
        
        print(f"🟢 ISOLATION TEST: Project B loaded {len(areas_b)} areas for doc_b")
        for area_id, area in areas_b.items():
            print(f"   - {area_id}: {area.user_notes}")
        
        # Test 3: Cross-contamination check
        print("\n🔵 ISOLATION TEST: Test 3 - Cross-contamination check")
        
        # Try to load Project A's document from Project B's context
        areas_cross = area_manager_b.load_areas("doc_a")
        print(f"🟢 ISOLATION TEST: Project B trying to load doc_a: {len(areas_cross)} areas")
        
        if len(areas_cross) == 0:
            print("✅ ISOLATION TEST: Cross-contamination prevented - Project B cannot see Project A's areas")
        else:
            print("❌ ISOLATION TEST: Cross-contamination detected - Project B can see Project A's areas")
            for area_id, area in areas_cross.items():
                print(f"   - LEAKED: {area_id}: {area.user_notes}")
        
        # Test 4: Direct file loading isolation
        print("\n🔵 ISOLATION TEST: Test 4 - Direct file loading isolation")
        
        # Test when no project manager is available (fallback to direct loading)
        area_manager_no_pm = AreaStorageManager(project_manager=None)
        
        # Should not find any areas since no current project file is set
        areas_no_pm = area_manager_no_pm.load_areas("doc_a")
        print(f"🟢 ISOLATION TEST: No project manager - loaded {len(areas_no_pm)} areas")
        
        if len(areas_no_pm) == 0:
            print("✅ ISOLATION TEST: Direct loading isolation working - no project file = no areas")
        else:
            print("❌ ISOLATION TEST: Direct loading isolation failed - areas loaded without project context")
        
        # Results summary
        print("\n🏁 ISOLATION TEST: Test Results Summary")
        print(f"✅ Project A areas: {len(areas_a)}")
        print(f"✅ Project B areas: {len(areas_b)}")
        print(f"✅ Cross-contamination prevention: {'PASS' if len(areas_cross) == 0 else 'FAIL'}")
        print(f"✅ Direct loading isolation: {'PASS' if len(areas_no_pm) == 0 else 'FAIL'}")
        
        # Overall result
        all_tests_passed = (
            len(areas_a) == 3 and  # Project A should have 3 areas
            len(areas_b) == 2 and  # Project B should have 2 areas
            len(areas_cross) == 0 and  # No cross-contamination
            len(areas_no_pm) == 0  # No direct loading without project
        )
        
        if all_tests_passed:
            print("\n🎉 ISOLATION TEST: ALL TESTS PASSED - Cross-project isolation is working correctly!")
            return True
        else:
            print("\n💥 ISOLATION TEST: TESTS FAILED - Cross-project isolation needs fixes")
            return False

if __name__ == "__main__":
    setup_logging()
    
    print("🚀 Starting TORE Matrix Labs Cross-Project Area Isolation Test")
    print("=" * 60)
    
    try:
        success = test_cross_project_isolation()
        
        if success:
            print("\n🎯 Test completed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Test failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)