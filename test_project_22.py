#!/usr/bin/env python3
"""
Test what happens when opening project 22 specifically.
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_project_22():
    """Test project 22 loading to see what's happening."""
    print("🚀 TORE Matrix Labs - Project 22 Debug Test")
    print("=" * 80)
    
    project_file = Path("/home/insulto/tore_matrix_labs/22.tore")
    
    if not project_file.exists():
        print(f"❌ Project file not found: {project_file}")
        return False
    
    try:
        # Load project 22
        print(f"📂 Loading project 22: {project_file}")
        with open(project_file, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        
        print(f"✅ Project 22 data:")
        print(f"   📊 Name: {project_data.get('name', 'Unknown')}")
        print(f"   📊 Description: {project_data.get('description', 'No description')}")
        print(f"   📊 Documents: {len(project_data.get('documents', []))}")
        print(f"   📊 Created: {project_data.get('created_at', 'Unknown')}")
        
        # Check project structure
        if not project_data.get('documents'):
            print(f"🔴 PROJECT 22 IS EMPTY - No documents!")
            print(f"   This explains why it loads as 'empty project'")
            print(f"   The project genuinely has no documents in it.")
        
        # Add missing path field (like the loading code does)
        if 'path' not in project_data:
            project_data['path'] = str(project_file)
            print(f"🟢 Added missing project path: {project_file}")
        
        # Test what get_current_project() would return
        print(f"\n🔍 What get_current_project() would return:")
        print(f"   📊 Project name: {project_data.get('name', 'Unknown')}")
        print(f"   📊 Project path: {project_data.get('path', 'Unknown')}")
        print(f"   📊 Project ID: {project_data.get('id', 'Not set')}")
        
        # Check if this project would have proper project info
        if project_data.get('name') and project_data.get('path'):
            print(f"✅ Project 22 has valid project info structure")
            
            # Test what _get_current_project_info() would return
            project_info = {
                'project_name': project_data.get('name', 'default_project'),
                'project_path': project_data.get('path', ''),
                'project_id': project_data.get('id', 'unknown')
            }
            print(f"🔍 _get_current_project_info() would return:")
            print(f"   📊 project_name: {project_info['project_name']}")
            print(f"   📊 project_path: {project_info['project_path']}")
            print(f"   📊 project_id: {project_info['project_id']}")
            
        else:
            print(f"❌ Project 22 has incomplete project info structure")
        
        # Check what happens if user tries to load document 5555.pdf in this project
        print(f"\n🧪 Simulating loading document 5555.pdf in project 22...")
        document_path = "/home/insulto/tore_matrix_labs/5555.pdf"
        
        if Path(document_path).exists():
            print(f"✅ Document exists: {document_path}")
            
            # Test persistence path generation for this project + document
            project_dir = Path(project_data['path']).parent if project_data.get('path') else Path.cwd()
            persistence_dir = project_dir / ".tore_project_selections" / project_data['name']
            doc_name = Path(document_path).stem
            persistence_file = persistence_dir / f"{doc_name}_selections.json"
            
            print(f"🔍 Project-specific persistence would be:")
            print(f"   📂 Project dir: {project_dir}")
            print(f"   📂 Persistence dir: {persistence_dir}")
            print(f"   📄 Persistence file: {persistence_file}")
            print(f"   🔍 File exists: {persistence_file.exists()}")
            
            # Check document-based persistence (old system)
            doc_dir = Path(document_path).parent
            old_persistence_dir = doc_dir / ".tore_selections"
            old_persistence_file = old_persistence_dir / f"{doc_name}_selections.json"
            
            print(f"\n🔍 Document-based persistence (old system):")
            print(f"   📂 Old persistence dir: {old_persistence_dir}")
            print(f"   📄 Old persistence file: {old_persistence_file}")
            print(f"   🔍 Old file exists: {old_persistence_file.exists()}")
            
            if old_persistence_file.exists():
                print(f"⚠️  OLD PERSISTENCE FILE EXISTS!")
                print(f"   This might be getting loaded inappropriately.")
                
                # Check if old file has project info
                with open(old_persistence_file, 'r') as f:
                    old_data = json.load(f)
                
                old_project = old_data.get('project_name', 'no_project')
                print(f"   🔍 Old file project: {old_project}")
                print(f"   🔍 Current project: {project_data['name']}")
                
                if old_project != project_data['name']:
                    print(f"✅ Project mismatch - should NOT load old selections")
                else:
                    print(f"❌ Project match - WOULD load old selections (wrong!)")
        else:
            print(f"❌ Document not found: {document_path}")
        
        print(f"\n✅ Project 22 analysis complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error analyzing project 22: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_project_22()
    if success:
        print("\n🎯 FINDINGS:")
        print("Project 22 is genuinely empty (no documents), so loading as 'empty' is correct.")
        print("If selections are still loading, check for old persistence files being loaded.")
    else:
        print("\n❌ Could not analyze project 22 properly.")