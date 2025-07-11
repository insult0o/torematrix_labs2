#!/usr/bin/env python3
"""
Test GUI components integration without full GUI display.

This will simulate the component setup to identify integration issues.
"""

import sys
import os
from pathlib import Path

# Add the project path
sys.path.insert(0, str(Path(__file__).parent))

def test_gui_components():
    """Test GUI component integration without display."""
    print("🔍 TESTING GUI COMPONENTS INTEGRATION")
    print("=" * 60)
    
    try:
        # Set bypass for testing
        os.environ['TORE_BYPASS_DIALOG'] = 'true'
        
        # Import components
        from tore_matrix_labs.core.area_storage_manager import AreaStorageManager
        from tore_matrix_labs.models.visual_area_models import VisualArea, AreaType
        
        print("✅ Core components imported")
        
        # Test 1: Create mock project manager like the real one
        print("\n1️⃣ TESTING PROJECT MANAGER INTEGRATION:")
        
        # Create minimal project data like real project files
        project_data = {
            "name": "Test Project",
            "documents": [
                {
                    "id": "doc_20250708_040740_5555",  # Same ID as in 4.tore
                    "name": "5555.pdf",
                    "file_path": "/path/to/5555.pdf",
                    "visual_areas": {}
                }
            ]
        }
        
        class MockProjectManager:
            def __init__(self):
                self.current_project = project_data
                self.documents = project_data["documents"]
            
            def get_current_project(self):
                return self.current_project
            
            def save_current_project(self):
                print("🟢 MOCK: save_current_project() called")
                return True
        
        mock_pm = MockProjectManager()
        print(f"   ✅ Mock project manager created with {len(project_data['documents'])} documents")
        
        # Test 2: Create area storage manager
        print("\n2️⃣ TESTING AREA STORAGE MANAGER:")
        storage_manager = AreaStorageManager(mock_pm)
        print("   ✅ Area storage manager created")
        
        # Test 3: Simulate enhanced drag select setup
        print("\n3️⃣ SIMULATING ENHANCED DRAG SELECT SETUP:")
        
        class MockEnhancedDragSelect:
            def __init__(self):
                self.area_storage_manager = None
                self.pdf_viewer = MockPDFViewer()
                self.persistent_areas = {}
                self.active_area_id = None
            
            def set_area_storage_manager(self, storage_manager):
                self.area_storage_manager = storage_manager
                print("   ✅ Area storage manager connected to drag select")
            
            def simulate_area_creation(self):
                """Simulate the area creation process."""
                print("\n   🎯 SIMULATING AREA CREATION PROCESS:")
                
                # Get document info like real GUI
                document_id = getattr(self.pdf_viewer, 'current_document_id', None)
                print(f"      Document ID from PDF viewer: '{document_id}'")
                
                # Run the same checkpoints as real code
                storage_available = self.area_storage_manager is not None
                print(f"      CHECKPOINT 1: Storage manager available: {storage_available}")
                
                project_manager_available = False
                if self.area_storage_manager and hasattr(self.area_storage_manager, 'project_manager'):
                    project_manager_available = self.area_storage_manager.project_manager is not None
                print(f"      CHECKPOINT 2: Project manager available: {project_manager_available}")
                
                current_project_exists = False
                current_project = None
                if project_manager_available:
                    pm = self.area_storage_manager.project_manager
                    if hasattr(pm, 'get_current_project'):
                        current_project = pm.get_current_project()
                        current_project_exists = current_project is not None
                print(f"      CHECKPOINT 3: Current project exists: {current_project_exists}")
                
                document_id_matches = False
                if current_project_exists and document_id:
                    documents = current_project.get('documents', [])
                    doc_ids = [doc.get('id') for doc in documents]
                    document_id_matches = document_id in doc_ids
                    print(f"      CHECKPOINT 4: Document ID '{document_id}' matches project: {document_id_matches}")
                    print(f"      Project document IDs: {doc_ids}")
                
                ready_to_save = storage_available and project_manager_available and current_project_exists and document_id_matches
                print(f"      🎯 OVERALL READINESS: Ready to save areas: {ready_to_save}")
                
                if ready_to_save:
                    # Try to save area
                    test_area = VisualArea(
                        id="test_area_gui",
                        document_id=document_id,
                        area_type=AreaType.IMAGE,
                        bbox=(10, 10, 100, 100),
                        page=1
                    )
                    
                    save_result = self.area_storage_manager.save_area(document_id, test_area)
                    print(f"      SAVE RESULT: {save_result}")
                    
                    if save_result:
                        print("      ✅ Area saved successfully!")
                        self.persistent_areas[test_area.id] = test_area
                    else:
                        print("      ❌ Area save failed!")
                else:
                    print("      ❌ Not ready to save - missing requirements")
                    if not storage_available:
                        print("         - No area storage manager")
                    if not project_manager_available:
                        print("         - No project manager")
                    if not current_project_exists:
                        print("         - No current project")
                    if not document_id_matches:
                        print("         - Document ID mismatch")
                
                return ready_to_save
        
        class MockPDFViewer:
            def __init__(self):
                self.current_document_id = "doc_20250708_040740_5555"  # Same as in project
                self.current_page = 0
        
        # Test the full integration
        drag_select = MockEnhancedDragSelect()
        drag_select.set_area_storage_manager(storage_manager)
        
        # Test area creation
        success = drag_select.simulate_area_creation()
        
        print(f"\n🎯 INTEGRATION TEST RESULT: {'SUCCESS' if success else 'FAILED'}")
        
        # Test 4: Check what happens with different document ID
        print("\n4️⃣ TESTING DOCUMENT ID MISMATCH:")
        drag_select.pdf_viewer.current_document_id = "wrong_document_id"
        success_wrong_id = drag_select.simulate_area_creation()
        print(f"   🎯 MISMATCH TEST RESULT: {'SUCCESS' if success_wrong_id else 'FAILED (expected)'}")
        
        # Test 5: Check what happens with no project
        print("\n5️⃣ TESTING NO PROJECT:")
        mock_pm.current_project = None
        success_no_project = drag_select.simulate_area_creation()
        print(f"   🎯 NO PROJECT TEST RESULT: {'SUCCESS' if success_no_project else 'FAILED (expected)'}")
        
        print("\n📋 CONCLUSIONS:")
        if success:
            print("✅ GUI integration should work when properly set up")
            print("🎯 Issue likely: Document not activated or project not loaded")
        else:
            print("❌ GUI integration has fundamental issues")
            print("🎯 Need to identify which checkpoint fails in real GUI")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_gui_components()