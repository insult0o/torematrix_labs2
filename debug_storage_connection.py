#!/usr/bin/env python3
"""
Debug the area storage manager connection without GUI.

This will check if the storage manager is properly connected to the cutting tool.
"""

import sys
from pathlib import Path

# Add the project path
sys.path.insert(0, str(Path(__file__).parent))

def debug_storage_connection():
    """Debug the storage manager connection by examining code logic."""
    print("🔍 DEBUGGING STORAGE MANAGER CONNECTION")
    print("=" * 60)
    
    # Check the main window setup
    main_window_file = Path("tore_matrix_labs/ui/main_window.py")
    if main_window_file.exists():
        with open(main_window_file, 'r') as f:
            content = f.read()
        
        print("1️⃣ MAIN WINDOW SETUP ANALYSIS:")
        
        # Check area storage manager initialization
        if 'self.area_storage_manager = AreaStorageManager(' in content:
            print("   ✅ Area storage manager is initialized")
        else:
            print("   ❌ Area storage manager not initialized")
        
        # Check connection to PDF viewer
        if 'set_area_storage_manager(self.area_storage_manager)' in content:
            print("   ✅ Storage manager connected to PDF viewer")
        else:
            print("   ❌ Storage manager not connected to PDF viewer")
        
        # Check page change signal connection
        if 'page_changed.connect' in content and 'on_page_changed' in content:
            print("   ✅ Page change signal connected")
        else:
            print("   ❌ Page change signal not connected")
    
    # Check enhanced drag select setup
    drag_select_file = Path("tore_matrix_labs/ui/components/enhanced_drag_select.py")
    if drag_select_file.exists():
        with open(drag_select_file, 'r') as f:
            content = f.read()
        
        print("\n2️⃣ ENHANCED DRAG SELECT ANALYSIS:")
        
        # Check if set_area_storage_manager method exists
        if 'def set_area_storage_manager(' in content:
            print("   ✅ set_area_storage_manager method exists")
        else:
            print("   ❌ set_area_storage_manager method missing")
        
        # Check if area_storage_manager is used in save operations
        if 'self.area_storage_manager.save_area(' in content:
            print("   ✅ Storage manager used for saving areas")
        else:
            print("   ❌ Storage manager not used for saving areas")
        
        # Check if area_storage_manager is used in load operations
        if 'self.area_storage_manager.get_areas_for_page(' in content:
            print("   ✅ Storage manager used for loading areas")
        else:
            print("   ❌ Storage manager not used for loading areas")
        
        # Check for None checks
        if 'if not self.area_storage_manager:' in content:
            print("   ✅ None checks for storage manager exist")
        else:
            print("   ⚠️  No None checks for storage manager")
    
    # Check area storage manager implementation
    storage_file = Path("tore_matrix_labs/core/area_storage_manager.py")
    if storage_file.exists():
        with open(storage_file, 'r') as f:
            content = f.read()
        
        print("\n3️⃣ AREA STORAGE MANAGER ANALYSIS:")
        
        # Check save_area method implementation
        if 'def save_area(' in content and 'project_manager' in content:
            print("   ✅ save_area method uses project_manager")
        else:
            print("   ❌ save_area method implementation issue")
        
        # Check if it finds documents properly
        if 'documents = project_data.get("documents", [])' in content:
            print("   ✅ Searches for documents in project data")
        else:
            print("   ❌ Does not search for documents properly")
        
        # Check if it saves visual_areas
        if 'visual_areas' in content and 'doc["visual_areas"]' in content:
            print("   ✅ Handles visual_areas in document data")
        else:
            print("   ❌ Does not handle visual_areas properly")
    
    print("\n4️⃣ POTENTIAL CONNECTION ISSUES:")
    
    # Look for common connection problems
    issues = []
    
    # Check if PDF viewer has page_label
    pdf_viewer_file = Path("tore_matrix_labs/ui/components/pdf_viewer.py")
    if pdf_viewer_file.exists():
        with open(pdf_viewer_file, 'r') as f:
            content = f.read()
        
        if 'self.page_label = ' in content:
            print("   ✅ PDF viewer has page_label")
        else:
            issues.append("PDF viewer missing page_label")
        
        if 'EnhancedDragSelectLabel' in content:
            print("   ✅ PDF viewer uses EnhancedDragSelectLabel")
        else:
            issues.append("PDF viewer not using EnhancedDragSelectLabel")
    
    if issues:
        print("\n   ❌ CONNECTION ISSUES FOUND:")
        for issue in issues:
            print(f"      • {issue}")
    else:
        print("   ✅ No obvious connection issues found")
    
    print("\n🎯 MOST LIKELY ISSUE:")
    print("Based on the .tore file analysis showing 0 areas,")
    print("the issue is likely one of these:")
    print("1. Area storage manager is None when save_area() is called")
    print("2. Document ID mismatch prevents finding the document to save to")
    print("3. save_area() fails silently without proper error handling")
    print("4. Project manager has no current project when saving")
    print("5. Area creation bypasses the save process entirely")
    
    print("\n📋 NEXT STEPS:")
    print("1. Add debug prints to _handle_area_selection() to trace execution")
    print("2. Add debug prints to save_area() to see if it's being called")
    print("3. Check if self.area_storage_manager is None during area creation")
    print("4. Verify document ID matches between PDF viewer and project")

if __name__ == "__main__":
    debug_storage_connection()