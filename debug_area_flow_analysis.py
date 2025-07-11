#!/usr/bin/env python3
"""
Analyze the area persistence flow without running the GUI.

This will examine the code structure and data flow to identify issues.
"""

import sys
import json
from pathlib import Path

# Add the project path
sys.path.insert(0, str(Path(__file__).parent))

def analyze_area_flow():
    """Analyze the area persistence flow by examining code structure."""
    print("🔍 ANALYZING AREA PERSISTENCE FLOW")
    print("=" * 60)
    
    try:
        # Import without GUI
        from tore_matrix_labs.core.area_storage_manager import AreaStorageManager
        from tore_matrix_labs.models.visual_area_models import VisualArea, AreaType
        print("✅ Core modules imported successfully")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return
    
    print("\n📋 FLOW ANALYSIS:")
    
    # 1. Check AreaStorageManager methods
    print("\n1️⃣ AREA STORAGE MANAGER METHODS:")
    storage_methods = [method for method in dir(AreaStorageManager) if not method.startswith('_')]
    for method in storage_methods:
        print(f"   ✅ {method}")
    
    # 2. Check VisualArea structure
    print("\n2️⃣ VISUAL AREA MODEL:")
    try:
        # Create a test area
        test_area = VisualArea(
            id="test_area",
            document_id="test_doc",
            area_type=AreaType.IMAGE,
            bbox=(10, 10, 100, 100),
            page=1
        )
        area_dict = test_area.to_dict()
        print("   ✅ VisualArea creation works")
        print(f"   📊 Area dict keys: {list(area_dict.keys())}")
    except Exception as e:
        print(f"   ❌ VisualArea creation failed: {e}")
    
    # 3. Analyze project structure 
    print("\n3️⃣ PROJECT FILE ANALYSIS:")
    project_files = list(Path(".").glob("*.tore"))
    if project_files:
        for project_file in project_files[:3]:  # Check first 3 files
            print(f"\n   📁 Analyzing: {project_file}")
            try:
                with open(project_file, 'r') as f:
                    data = json.load(f)
                
                documents = data.get('documents', [])
                print(f"      📄 Documents: {len(documents)}")
                
                for i, doc in enumerate(documents):
                    doc_id = doc.get('id', 'No ID')
                    visual_areas = doc.get('visual_areas', {})
                    print(f"         Doc {i+1}: ID={doc_id}, Areas={len(visual_areas)}")
                    
                    if visual_areas:
                        for area_id in list(visual_areas.keys())[:2]:  # Show first 2 areas
                            area = visual_areas[area_id]
                            print(f"            Area: {area_id}, page={area.get('page')}, type={area.get('type')}")
                
            except Exception as e:
                print(f"      ❌ Error reading {project_file}: {e}")
    else:
        print("   📁 No .tore files found in current directory")
    
    # 4. Check for common issues in the code
    print("\n4️⃣ CODE STRUCTURE ANALYSIS:")
    
    # Check enhanced_drag_select.py for potential issues
    drag_select_file = Path("tore_matrix_labs/ui/components/enhanced_drag_select.py")
    if drag_select_file.exists():
        with open(drag_select_file, 'r') as f:
            content = f.read()
        
        issues = []
        
        # Check for area storage manager setup
        if 'self.area_storage_manager = None' in content:
            issues.append("Area storage manager initialized as None")
        
        # Check for save_area calls
        save_calls = content.count('save_area(')
        if save_calls > 0:
            print(f"   ✅ Found {save_calls} save_area() calls")
        else:
            issues.append("No save_area() calls found")
        
        # Check for load_persistent_areas calls
        load_calls = content.count('load_persistent_areas(')
        if load_calls > 0:
            print(f"   ✅ Found {load_calls} load_persistent_areas() calls")
        else:
            issues.append("No load_persistent_areas() calls found")
        
        if issues:
            print("   ❌ Potential issues found:")
            for issue in issues:
                print(f"      • {issue}")
        else:
            print("   ✅ No obvious code structure issues found")
    
    # 5. Check area_storage_manager.py
    storage_file = Path("tore_matrix_labs/core/area_storage_manager.py")
    if storage_file.exists():
        with open(storage_file, 'r') as f:
            content = f.read()
        
        print("\n   📊 Storage Manager Analysis:")
        
        # Check save_area method
        if 'def save_area(' in content:
            print("      ✅ save_area method exists")
        else:
            print("      ❌ save_area method missing")
        
        # Check for project manager usage
        if 'self.project_manager' in content:
            print("      ✅ Uses project_manager")
        else:
            print("      ❌ No project_manager usage")
        
        # Check for auto-save calls
        if 'save_current_project()' in content:
            print("      ✅ Calls save_current_project()")
        else:
            print("      ❌ No save_current_project() calls")
    
    print("\n🎯 LIKELY ISSUES TO INVESTIGATE:")
    print("1. Area storage manager not properly connected to enhanced_drag_select")
    print("2. Document ID mismatch between PDF viewer and project documents")
    print("3. save_current_project() not being called or failing")
    print("4. load_persistent_areas() not being called on page changes")
    print("5. Project data structure issues")
    
    print("\n📁 For more detailed analysis, check these files manually:")
    print("   • enhanced_drag_select.py: Area creation and loading logic")
    print("   • area_storage_manager.py: Storage and retrieval logic")
    print("   • project_manager_widget.py: Project save/load logic")
    print("   • main_window.py: Component connection logic")

if __name__ == "__main__":
    analyze_area_flow()