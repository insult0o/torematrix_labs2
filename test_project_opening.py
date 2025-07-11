#!/usr/bin/env python3
"""
Test project opening functionality to diagnose the issue.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_project_opening():
    """Test opening an existing project file to see what happens."""
    print("🚀 TORE Matrix Labs - Project Opening Test")
    print("=" * 80)
    
    # Find a test project file
    project_files = list(Path.cwd().glob("*.tore"))
    if not project_files:
        print("❌ No .tore project files found in current directory")
        return False
    
    test_file = project_files[0]
    print(f"📂 Testing with project file: {test_file}")
    
    try:
        import json
        
        # Try to load and parse the project file
        print(f"📖 Reading project file: {test_file}")
        with open(test_file, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        
        print(f"✅ Successfully loaded project data:")
        print(f"   📊 Project name: {project_data.get('name', 'Unknown')}")
        print(f"   📊 Description: {project_data.get('description', 'No description')[:100]}...")
        print(f"   📊 Documents: {len(project_data.get('documents', []))}")
        print(f"   📊 Created: {project_data.get('created_at', 'Unknown')}")
        print(f"   📊 Modified: {project_data.get('modified_at', 'Unknown')}")
        
        # Show document details
        documents = project_data.get('documents', [])
        if documents:
            print(f"\n📄 Document details:")
            for i, doc in enumerate(documents[:3]):  # Show first 3
                print(f"   {i+1}. {doc.get('name', 'Unknown')} ({doc.get('status', 'Unknown')})")
                if 'path' in doc:
                    doc_path = Path(doc['path'])
                    if doc_path.exists():
                        print(f"      ✅ File exists: {doc['path']}")
                    else:
                        print(f"      ❌ File missing: {doc['path']}")
        
        print(f"\n🧪 Now testing actual project loading through the UI...")
        
        # Test the project manager loading
        from tore_matrix_labs.config.settings import Settings
        from tore_matrix_labs.ui.components.project_manager_widget import ProjectManagerWidget
        from tore_matrix_labs.ui.qt_compat import QApplication
        
        # Create Qt application if needed
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        
        # Create and test project widget
        settings = Settings()
        project_widget = ProjectManagerWidget(settings)
        
        print(f"🔄 Loading project through ProjectManagerWidget...")
        project_widget.load_project(str(test_file))
        
        # Check if project was loaded
        current_project = project_widget.get_current_project()
        if current_project:
            print(f"✅ Project successfully loaded in widget:")
            print(f"   📊 Name: {current_project.get('name', 'Unknown')}")
            print(f"   📊 Documents: {len(current_project.get('documents', []))}")
        else:
            print(f"❌ Project loading failed in widget")
            return False
        
        print(f"\n✅ Project opening test completed successfully!")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error during project opening test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_project_opening()
    if success:
        print("\n✅ Project opening functionality appears to work correctly.")
        print("🔍 The issue might be in the UI integration or signal handling.")
        print("🎯 Check the main window's project loading signals and connections.")
    else:
        print("\n❌ Found issues with project opening functionality.")
        print("🔧 Fix the project loading logic before investigating further.")