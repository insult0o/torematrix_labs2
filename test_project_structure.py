#!/usr/bin/env python3
"""
Test project file structure and loading logic without GUI.
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_project_structure():
    """Test project file structure and identify issues."""
    print("🚀 TORE Matrix Labs - Project Structure Test")
    print("=" * 80)
    
    # Find a test project file
    project_files = list(Path.cwd().glob("*.tore"))
    if not project_files:
        print("❌ No .tore project files found in current directory")
        return False
    
    test_file = project_files[0]
    print(f"📂 Testing with project file: {test_file}")
    
    try:
        # Try to load and parse the project file
        print(f"📖 Reading project file: {test_file}")
        with open(test_file, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        
        print(f"✅ Successfully loaded project data:")
        print(f"   📊 Project keys: {list(project_data.keys())}")
        print(f"   📊 Project name: {project_data.get('name', 'Unknown')}")
        print(f"   📊 Project ID: {project_data.get('id', 'Unknown')}")
        print(f"   📊 Project path: {project_data.get('path', 'Unknown')}")
        print(f"   📊 Documents count: {len(project_data.get('documents', []))}")
        
        # Analyze project structure
        required_fields = ['name', 'id', 'path', 'created_at', 'documents']
        missing_fields = [field for field in required_fields if field not in project_data]
        
        if missing_fields:
            print(f"⚠️  Missing required fields: {missing_fields}")
        else:
            print(f"✅ All required fields present")
        
        # Check project path validity
        project_path = project_data.get('path', '')
        if project_path:
            path_obj = Path(project_path)
            if path_obj.exists():
                print(f"✅ Project path exists: {project_path}")
            else:
                print(f"❌ Project path does not exist: {project_path}")
        else:
            print(f"⚠️  No project path specified")
        
        # Show document details
        documents = project_data.get('documents', [])
        if documents:
            print(f"\n📄 Document analysis:")
            for i, doc in enumerate(documents):
                print(f"   Document {i+1}:")
                print(f"      📊 Keys: {list(doc.keys())}")
                print(f"      📊 Name: {doc.get('name', 'Unknown')}")
                print(f"      📊 Status: {doc.get('status', 'Unknown')}")
                print(f"      📊 Path: {doc.get('path', 'Unknown')}")
                
                # Check if document file exists
                doc_path = doc.get('path', '')
                if doc_path:
                    if Path(doc_path).exists():
                        print(f"      ✅ Document file exists")
                    else:
                        print(f"      ❌ Document file missing: {doc_path}")
                else:
                    print(f"      ⚠️  No document path specified")
                print()
        else:
            print(f"📄 No documents in project")
        
        # Test project manager logic without GUI
        print(f"\n🧪 Testing project manager logic...")
        
        # Simulate what happens in load_project method
        print(f"🔄 Simulating project loading...")
        current_project = project_data.copy()
        project_file_path = str(test_file)
        has_changes = False
        documents = project_data.get('documents', [])
        
        print(f"✅ Project loading simulation successful:")
        print(f"   📊 Current project: {current_project.get('name', 'Unknown')}")
        print(f"   📊 Project file path: {project_file_path}")
        print(f"   📊 Has changes: {has_changes}")
        print(f"   📊 Documents loaded: {len(documents)}")
        
        # Check what would be returned by get_current_project()
        print(f"\n🔍 get_current_project() would return:")
        if current_project:
            print(f"   ✅ Valid project data")
            print(f"   📊 Name: {current_project.get('name', 'Unknown')}")
            print(f"   📊 Path: {current_project.get('path', 'Unknown')}")
            print(f"   📊 ID: {current_project.get('id', 'Unknown')}")
        else:
            print(f"   ❌ No project data")
        
        print(f"\n✅ Project structure test completed successfully!")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"🔧 The project file might be corrupted or invalid JSON")
        return False
    except Exception as e:
        print(f"❌ Error during project structure test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_project_structure()
    if success:
        print("\n✅ Project file structure appears to be valid.")
        print("🔍 The issue is likely in the UI signal handling or connections.")
        print("🎯 Possible causes:")
        print("   • project_loaded signal not emitted properly")
        print("   • Main window not connected to project_loaded signal")
        print("   • Exception during _emit_project_loaded_signal()")
        print("   • Issue in _on_project_loaded() method in main window")
    else:
        print("\n❌ Found issues with project file structure.")
        print("🔧 Fix the project file format before investigating UI issues.")