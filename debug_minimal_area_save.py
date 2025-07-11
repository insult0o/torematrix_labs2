#!/usr/bin/env python3
"""
Minimal test to create and save an area without GUI.

This will test the area creation and storage pipeline in isolation.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add the project path
sys.path.insert(0, str(Path(__file__).parent))

def test_minimal_area_save():
    """Test creating and saving an area with minimal setup."""
    print("🔍 MINIMAL AREA SAVE TEST")
    print("=" * 60)
    
    try:
        # Import required modules
        from tore_matrix_labs.core.area_storage_manager import AreaStorageManager
        from tore_matrix_labs.models.visual_area_models import VisualArea, AreaType
        from tore_matrix_labs.ui.components.project_manager_widget import ProjectManagerWidget
        
        print("✅ All modules imported successfully")
        
        # Create a mock project manager
        print("\n1️⃣ SETTING UP MOCK PROJECT MANAGER:")
        
        # Create minimal project data
        project_data = {
            "name": "Test Project",
            "created_at": datetime.now().isoformat(),
            "modified_at": datetime.now().isoformat(),
            "documents": [
                {
                    "id": "test_doc_123",
                    "name": "test.pdf",
                    "file_path": "/test/path.pdf",
                    "visual_areas": {}
                }
            ]
        }
        
        # Create a mock project manager class
        class MockProjectManager:
            def __init__(self):
                self.current_project = project_data
            
            def get_current_project(self):
                return self.current_project
            
            def save_current_project(self):
                print("🟢 MOCK: save_current_project() called")
                return True
        
        mock_pm = MockProjectManager()
        print("   ✅ Mock project manager created")
        print(f"   📊 Project has {len(project_data['documents'])} documents")
        
        # Create area storage manager
        print("\n2️⃣ CREATING AREA STORAGE MANAGER:")
        storage_manager = AreaStorageManager(mock_pm)
        print("   ✅ Area storage manager created")
        
        # Create a test area
        print("\n3️⃣ CREATING TEST AREA:")
        test_area = VisualArea(
            id="test_area_001",
            document_id="test_doc_123",  # Matches document in project
            area_type=AreaType.IMAGE,
            bbox=(10.0, 10.0, 100.0, 100.0),
            page=1
        )
        print(f"   ✅ Test area created: {test_area.id}")
        print(f"   📊 Area data: page={test_area.page}, bbox={test_area.bbox}")
        
        # Try to save the area
        print("\n4️⃣ ATTEMPTING TO SAVE AREA:")
        save_result = storage_manager.save_area("test_doc_123", test_area)
        print(f"   📊 Save result: {save_result}")
        
        if save_result:
            print("   ✅ Area saved successfully!")
            
            # Check if it was actually added to project data
            documents = mock_pm.get_current_project()["documents"]
            for doc in documents:
                if doc["id"] == "test_doc_123":
                    visual_areas = doc.get("visual_areas", {})
                    print(f"   📊 Document now has {len(visual_areas)} visual areas")
                    if test_area.id in visual_areas:
                        print(f"   ✅ Area {test_area.id} found in document data")
                        saved_area_data = visual_areas[test_area.id]
                        print(f"   📊 Saved area page: {saved_area_data.get('page')}")
                        print(f"   📊 Saved area bbox: {saved_area_data.get('bbox')}")
                    else:
                        print(f"   ❌ Area {test_area.id} NOT found in document data")
                    break
        else:
            print("   ❌ Area save failed!")
        
        # Test loading the area back
        print("\n5️⃣ TESTING AREA LOADING:")
        loaded_areas = storage_manager.load_areas("test_doc_123")
        print(f"   📊 Loaded {len(loaded_areas)} areas")
        
        if loaded_areas:
            for area_id, area in loaded_areas.items():
                print(f"   ✅ Loaded area: {area_id}, page={area.page}, bbox={area.bbox}")
        else:
            print("   ❌ No areas loaded")
        
        # Test page filtering
        print("\n6️⃣ TESTING PAGE FILTERING:")
        page_1_areas = storage_manager.get_areas_for_page("test_doc_123", 1)
        print(f"   📊 Found {len(page_1_areas)} areas on page 1")
        
        if page_1_areas:
            print("   ✅ Page filtering works correctly")
        else:
            print("   ❌ Page filtering failed or no areas on page 1")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n🎯 TEST CONCLUSIONS:")
    print("If this test passes, the area storage logic works correctly.")
    print("If this test fails, there's a fundamental issue with the storage system.")
    print("If this passes but the GUI doesn't work, the issue is in the GUI integration.")

if __name__ == "__main__":
    test_minimal_area_save()