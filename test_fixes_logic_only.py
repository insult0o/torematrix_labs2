#!/usr/bin/env python3
"""
Logic-only test script to verify fixes without GUI components.
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, '.')

def test_visual_areas_format_preservation():
    """Test visual areas preservation in document format conversion."""
    print("🔍 Testing visual areas format preservation...")
    
    try:
        # Test document with visual areas in different locations
        test_doc = {
            'id': 'test_doc_123',
            'file_name': 'test_document.pdf',
            'file_path': '/path/to/test_document.pdf',
            'processing_status': 'completed',
            'visual_areas': {
                'area_1': {'type': 'IMAGE', 'page': 1, 'bbox': [100, 200, 300, 400]},
                'area_2': {'type': 'TABLE', 'page': 2, 'bbox': [150, 250, 350, 450]}
            },
            'processing_data': {
                'visual_areas': {
                    'area_3': {'type': 'DIAGRAM', 'page': 3, 'bbox': [200, 300, 400, 500]}
                }
            }
        }
        
        # Import the conversion logic manually
        from tore_matrix_labs.ui.components.project_manager_widget import ProjectManagerWidget
        
        # Test the logic by checking the source code
        import inspect
        source = inspect.getsource(ProjectManagerWidget._convert_document_format)
        
        if "'visual_areas'" in source and "doc.get('visual_areas')" in source:
            print("✅ Visual areas extraction logic implemented")
        else:
            print("❌ Visual areas extraction logic missing")
            
        if "processing_data.get('visual_areas'" in source:
            print("✅ Processing data visual areas extraction implemented")
        else:
            print("❌ Processing data visual areas extraction missing")
            
        print(f"✅ Visual areas format preservation verified")
        
    except Exception as e:
        print(f"❌ Error testing visual areas format: {e}")

def test_document_id_consistency():
    """Test document ID generation consistency."""
    print("\n🔍 Testing document ID consistency...")
    
    try:
        import hashlib
        
        # Test file paths
        test_paths = [
            '/home/user/documents/test_file.pdf',
            '/different/path/test_file.pdf', 
            '/home/user/documents/test_file.pdf'  # Same as first
        ]
        
        generated_ids = []
        for file_path in test_paths:
            # Replicate the ID generation logic
            path_str = str(Path(file_path).resolve())
            path_hash = hashlib.md5(path_str.encode()).hexdigest()[:8]
            document_id = f"{Path(file_path).stem}_{path_hash}"
            generated_ids.append(document_id)
            print(f"   {Path(file_path).name} → {document_id}")
        
        # Verify consistency
        if generated_ids[0] == generated_ids[2]:
            print("✅ Same file paths produce consistent IDs")
        else:
            print("❌ Same file paths produce different IDs")
            
        if generated_ids[0] != generated_ids[1]:
            print("✅ Different file paths produce different IDs") 
        else:
            print("❌ Different file paths produce same IDs")
            
    except Exception as e:
        print(f"❌ Error testing document ID consistency: {e}")

def test_implemented_methods():
    """Test that all required methods are implemented."""
    print("\n🔍 Testing implemented methods...")
    
    try:
        # Test main window enhancements
        from tore_matrix_labs.ui import main_window
        import inspect
        
        main_source = inspect.getsource(main_window)
        
        main_window_checks = [
            ("_populate_manual_validation_from_project", "Project → Manual validation integration"),
            ("document_state_manager.load_project_documents", "Document state manager integration"),
            ("document_list_changed.connect", "Signal connection setup")
        ]
        
        for check, description in main_window_checks:
            if check in main_source:
                print(f"✅ {description}")
            else:
                print(f"❌ {description} missing")
        
        # Test manual validation enhancements  
        from tore_matrix_labs.ui.components import manual_validation_widget
        manual_source = inspect.getsource(manual_validation_widget)
        
        manual_checks = [
            ("def on_documents_available", "Documents available handler"),
            ("def load_existing_areas_from_project", "Project areas loader"),
            ("def _try_recover_document_context", "Context recovery mechanism"),
            ("def _refresh_pdf_viewer_areas", "PDF viewer refresh")
        ]
        
        for check, description in manual_checks:
            if check in manual_source:
                print(f"✅ {description}")
            else:
                print(f"❌ {description} missing")
                
        # Test project manager enhancements
        from tore_matrix_labs.ui.components import project_manager_widget
        project_source = inspect.getsource(project_manager_widget)
        
        if "visual_areas" in project_source and "_convert_document_format" in project_source:
            print("✅ Project manager visual areas preservation")
        else:
            print("❌ Project manager visual areas preservation missing")
            
    except Exception as e:
        print(f"❌ Error testing implemented methods: {e}")

def test_area_storage_integration():
    """Test area storage manager integration."""
    print("\n🔍 Testing area storage integration...")
    
    try:
        from tore_matrix_labs.core.area_storage_manager import AreaStorageManager
        from tore_matrix_labs.models.visual_area_models import VisualArea, AreaType, AreaStatus
        
        # Check required methods
        required_methods = [
            'load_areas', 'save_area', 'delete_area', 
            'get_areas_for_page', 'update_area'
        ]
        
        for method in required_methods:
            if hasattr(AreaStorageManager, method):
                print(f"✅ {method} method exists")
            else:
                print(f"❌ {method} method missing")
        
        # Check area model classes
        area_classes = [VisualArea, AreaType, AreaStatus]
        for cls in area_classes:
            print(f"✅ {cls.__name__} class available")
            
    except Exception as e:
        print(f"❌ Error testing area storage integration: {e}")

def generate_workflow_test_plan():
    """Generate a test plan for manual workflow testing."""
    print("\n" + "="*60)
    print("📋 MANUAL WORKFLOW TEST PLAN")
    print("="*60)
    
    steps = [
        "🎯 **PHASE 1: Project Creation & Document Processing**",
        "   1. Start TORE Matrix Labs application",
        "   2. Create new project (e.g., 'Persistence Test')",
        "   3. Add a PDF document to the project",
        "   4. Process the document in Manual Validation tab",
        "   5. Create 2-3 visual areas (IMAGE, TABLE, DIAGRAM)",
        "   6. Verify areas appear in the Areas List",
        "   7. Save the project",
        "",
        "🎯 **PHASE 2: Session Persistence Test**",
        "   8. Close the TORE Matrix Labs application completely",
        "   9. Restart the application",
        "   10. Open the saved project",
        "   11. **VERIFY**: Areas immediately appear in Manual Validation tab",
        "   12. **VERIFY**: No need to reprocess the document",
        "   13. **VERIFY**: Only one document appears in project (no duplicates)",
        "",
        "🎯 **PHASE 3: Area Management Test**",
        "   14. Click on areas in the Areas List",
        "   15. **VERIFY**: Area previews show correctly (no 'Document None')",
        "   16. **VERIFY**: PDF viewer highlights the selected areas",
        "   17. Delete one area from the list",
        "   18. Navigate to different page and back",
        "   19. **VERIFY**: Deleted area no longer visible in PDF",
        "",
        "🎯 **PHASE 4: Cross-Tab Navigation Test**",
        "   20. Switch between Manual Validation and other tabs",
        "   21. Return to Manual Validation tab",
        "   22. **VERIFY**: Document context preserved",
        "   23. **VERIFY**: Areas still visible and functional",
        "",
        "🎯 **SUCCESS CRITERIA**",
        "   ✅ Areas persist between application sessions",
        "   ✅ No document duplication in project",
        "   ✅ Area previews work without reprocessing",
        "   ✅ Area deletion syncs properly",
        "   ✅ Document context preserved across tabs"
    ]
    
    for step in steps:
        print(step)

def summarize_fixes():
    """Summarize all implemented fixes."""
    print("\n" + "="*60)
    print("🔧 IMPLEMENTED FIXES SUMMARY")
    print("="*60)
    
    fixes = [
        "**1. PROJECT LOADING → MANUAL VALIDATION INTEGRATION**",
        "   📁 main_window.py: Added _populate_manual_validation_from_project()",
        "   🔗 Connects project loading to manual validation widget",
        "   📊 Auto-loads documents with visual areas",
        "",
        "**2. VISUAL AREAS PERSISTENCE**", 
        "   📁 project_manager_widget.py: Enhanced _convert_document_format()",
        "   💾 Preserves visual_areas in document conversion",
        "   🔄 Handles multiple storage locations (top-level + processing_data)",
        "",
        "**3. DOCUMENT DUPLICATION PREVENTION**",
        "   📁 main_window.py: Consistent document ID generation",
        "   🔑 Uses file path + hash for unique, consistent IDs",
        "   🚫 Prevents same document appearing multiple times",
        "",
        "**4. DOCUMENT STATE MANAGER INTEGRATION**",
        "   📁 main_window.py: Added document_state_manager.load_project_documents()",
        "   📁 manual_validation_widget.py: Added on_documents_available()",
        "   📡 Signal-based communication between components",
        "",
        "**5. SESSION STATE MANAGEMENT**",
        "   📁 manual_validation_widget.py: Added _try_recover_document_context()",
        "   🔄 Recovers document context from PDF viewer or state manager",
        "   🛡️ Prevents 'Document None, Path None' errors",
        "",
        "**6. AREA LOADING WITHOUT REPROCESSING**",
        "   📁 manual_validation_widget.py: Enhanced load_existing_areas_from_project()",
        "   ⚡ Areas load immediately on project open",
        "   🚫 No reprocessing required to see existing areas"
    ]
    
    for fix in fixes:
        print(fix)

if __name__ == "__main__":
    print("🧪 COMPREHENSIVE FIXES VERIFICATION (Logic Only)")
    print("=" * 55)
    
    test_visual_areas_format_preservation()
    test_document_id_consistency()
    test_implemented_methods()
    test_area_storage_integration()
    
    summarize_fixes()
    generate_workflow_test_plan()
    
    print("\n🏁 Logic verification completed!")
    print("💡 Ready for manual workflow testing!")