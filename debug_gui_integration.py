#!/usr/bin/env python3
"""
Debug the GUI integration issues for area persistence.

Since the storage logic works, the issue must be in GUI integration.
"""

import sys
from pathlib import Path

# Add the project path
sys.path.insert(0, str(Path(__file__).parent))

def debug_gui_integration():
    """Debug GUI integration issues by examining the connection points."""
    print("🔍 DEBUGGING GUI INTEGRATION ISSUES")
    print("=" * 60)
    
    print("✅ CONFIRMED: Storage logic works correctly (from minimal test)")
    print("❌ ISSUE: Areas not saving in actual GUI")
    print("🎯 FOCUS: GUI integration problems")
    
    print("\n📋 GUI INTEGRATION CHECKPOINTS:")
    
    # 1. Check main window initialization order
    main_window_file = Path("tore_matrix_labs/ui/main_window.py")
    if main_window_file.exists():
        with open(main_window_file, 'r') as f:
            content = f.read()
        
        print("\n1️⃣ MAIN WINDOW INITIALIZATION ORDER:")
        
        # Find the order of widget creation
        lines = content.split('\n')
        initialization_order = []
        
        for i, line in enumerate(lines):
            if 'self.pdf_viewer = PDFViewer(' in line:
                initialization_order.append(f"Line {i+1}: PDF viewer created")
            elif 'self.project_widget = ProjectManagerWidget(' in line:
                initialization_order.append(f"Line {i+1}: Project widget created")
            elif 'self.area_storage_manager = AreaStorageManager(' in line:
                initialization_order.append(f"Line {i+1}: Area storage manager created")
            elif 'set_area_storage_manager(' in line:
                initialization_order.append(f"Line {i+1}: Storage manager connected to PDF viewer")
        
        for order in initialization_order:
            print(f"   📊 {order}")
        
        # Check if PDF viewer is created before area storage manager
        pdf_viewer_line = next((i for i, order in enumerate(initialization_order) if 'PDF viewer created' in order), -1)
        storage_manager_line = next((i for i, order in enumerate(initialization_order) if 'Area storage manager created' in order), -1)
        connection_line = next((i for i, order in enumerate(initialization_order) if 'Storage manager connected' in order), -1)
        
        if pdf_viewer_line < storage_manager_line < connection_line:
            print("   ✅ Initialization order is correct")
        else:
            print("   ❌ Initialization order might be wrong")
    
    # 2. Check PDF viewer page_label setup
    pdf_viewer_file = Path("tore_matrix_labs/ui/components/pdf_viewer.py")
    if pdf_viewer_file.exists():
        with open(pdf_viewer_file, 'r') as f:
            content = f.read()
        
        print("\n2️⃣ PDF VIEWER PAGE LABEL SETUP:")
        
        if 'from .enhanced_drag_select import EnhancedDragSelectLabel' in content:
            print("   ✅ EnhancedDragSelectLabel is imported")
        else:
            print("   ❌ EnhancedDragSelectLabel not imported")
        
        if 'self.page_label = EnhancedDragSelectLabel(' in content:
            print("   ✅ page_label is EnhancedDragSelectLabel")
        else:
            print("   ❌ page_label is not EnhancedDragSelectLabel")
    
    # 3. Check document activation flow
    print("\n3️⃣ DOCUMENT ACTIVATION FLOW:")
    
    # Check if document activation sets current_document_id
    if 'current_document_id' in content:
        print("   ✅ PDF viewer handles current_document_id")
    else:
        print("   ❌ PDF viewer doesn't handle current_document_id")
    
    print("\n4️⃣ POTENTIAL GUI INTEGRATION ISSUES:")
    
    issues = [
        "Area storage manager is None when area is created",
        "Document ID not set when area is created", 
        "Project not loaded when area is created",
        "Page change signal not properly connected",
        "Enhanced drag select not receiving storage manager",
        "Dialog bypass not working correctly",
        "Area creation happening before storage manager setup"
    ]
    
    for i, issue in enumerate(issues, 1):
        print(f"   {i}. {issue}")
    
    print("\n🔧 DEBUGGING STRATEGY:")
    print("Since storage logic works, add debug prints to these GUI events:")
    print("1. Area creation in _handle_area_selection()")
    print("2. Storage manager connection in main window")
    print("3. Document activation in PDF viewer")
    print("4. Page change events")
    print("5. Storage manager availability checks")
    
    print("\n🎯 MOST LIKELY ISSUES:")
    print("1. self.area_storage_manager is None during area creation")
    print("2. Document ID mismatch between PDF viewer and project")
    print("3. Project not loaded/current when saving areas")
    print("4. Area creation bypassing save logic entirely")
    
    print("\n📋 IMMEDIATE ACTIONS:")
    print("1. Add 'AREA_CREATE: Storage manager available: True/False' debug")
    print("2. Add 'AREA_CREATE: Document ID matches project: True/False' debug")
    print("3. Add 'AREA_CREATE: Current project exists: True/False' debug")
    print("4. Run GUI with debug logging to see which checkpoint fails")

if __name__ == "__main__":
    debug_gui_integration()