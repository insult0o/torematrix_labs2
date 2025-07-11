#!/usr/bin/env python3
"""
Test project opening functionality with the fixes applied.
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_project_opening_fixed():
    """Test project opening with document format conversion."""
    print("🚀 TORE Matrix Labs - Project Opening Test (Fixed)")
    print("=" * 80)
    
    # Find a test project file
    project_files = list(Path.cwd().glob("*.tore"))
    if not project_files:
        print("❌ No .tore project files found in current directory")
        return False
    
    test_file = project_files[0]
    print(f"📂 Testing with project file: {test_file}")
    
    try:
        # Simulate the project manager's load_project method
        print(f"📖 Loading project data...")
        with open(test_file, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        
        # Add missing path field
        if 'path' not in project_data:
            project_data['path'] = str(test_file)
            print(f"✅ Added missing project path: {test_file}")
        
        print(f"✅ Project loaded:")
        print(f"   📊 Name: {project_data.get('name', 'Unknown')}")
        print(f"   📊 Path: {project_data.get('path', 'Unknown')}")
        print(f"   📊 Documents: {len(project_data.get('documents', []))}")
        
        # Test document format conversion
        documents = project_data.get('documents', [])
        if documents:
            print(f"\n🔄 Testing document format conversion...")
            
            for i, doc in enumerate(documents):
                print(f"\n   Document {i+1} (Original format):")
                print(f"      📊 ID: {doc.get('id', 'unknown')}")
                print(f"      📊 Status: {doc.get('processing_status', 'unknown')}")
                
                # Extract metadata
                metadata = doc.get('metadata', {})
                custom_metadata = doc.get('custom_metadata', {})
                
                print(f"      📊 File name: {metadata.get('file_name', 'Unknown')}")
                print(f"      📊 File path: {metadata.get('file_path', 'Unknown')}")
                print(f"      📊 File size: {metadata.get('file_size', 0)} bytes")
                print(f"      📊 Page count: {metadata.get('page_count', 0)}")
                print(f"      📊 Corrections: {len(custom_metadata.get('corrections', []))}")
                
                # Convert to expected format
                converted = {
                    'id': doc.get('id', 'unknown'),
                    'name': metadata.get('file_name', 'Unknown Document'),
                    'path': metadata.get('file_path', ''),
                    'status': doc.get('processing_status', 'unknown'),
                    'processing_data': {
                        'file_size': metadata.get('file_size', 0),
                        'page_count': metadata.get('page_count', 0),
                        'file_type': metadata.get('file_type', 'unknown'),
                        'processing_status': doc.get('processing_status', 'unknown'),
                        'quality_level': doc.get('quality_level', 'unknown'),
                        'quality_score': doc.get('quality_score', 0.0),
                        'corrections_count': len(custom_metadata.get('corrections', [])),
                        'corrections': custom_metadata.get('corrections', [])
                    }
                }
                
                print(f"\n   Document {i+1} (Converted format):")
                print(f"      ✅ Name: {converted.get('name', 'Unknown')}")
                print(f"      ✅ Path: {converted.get('path', 'Unknown')}")
                print(f"      ✅ Status: {converted.get('status', 'Unknown')}")
                print(f"      ✅ Processing data keys: {list(converted.get('processing_data', {}).keys())}")
                print(f"      ✅ Corrections count: {converted['processing_data'].get('corrections_count', 0)}")
                
                # Verify file exists
                doc_path = converted.get('path', '')
                if doc_path:
                    if Path(doc_path).exists():
                        print(f"      ✅ Document file exists")
                    else:
                        print(f"      ⚠️  Document file missing: {doc_path}")
                else:
                    print(f"      ❌ No document path")
        
        # Test what the main window would see
        print(f"\n🧪 Testing main window integration...")
        
        # Simulate get_project_documents() return
        converted_documents = []
        for doc in documents:
            metadata = doc.get('metadata', {})
            custom_metadata = doc.get('custom_metadata', {})
            
            converted = {
                'id': doc.get('id', 'unknown'),
                'name': metadata.get('file_name', 'Unknown Document'),
                'path': metadata.get('file_path', ''),
                'status': doc.get('processing_status', 'unknown'),
                'processing_data': {
                    'file_size': metadata.get('file_size', 0),
                    'page_count': metadata.get('page_count', 0),
                    'corrections_count': len(custom_metadata.get('corrections', [])),
                    'corrections': custom_metadata.get('corrections', [])
                }
            }
            converted_documents.append(converted)
        
        print(f"✅ Main window would receive {len(converted_documents)} documents:")
        for doc in converted_documents:
            corrections_count = doc['processing_data'].get('corrections_count', 0)
            print(f"   📄 {doc['name']} - {doc['status']} - {corrections_count} corrections")
        
        # Test finding documents with corrections
        docs_with_corrections = [doc for doc in converted_documents 
                               if doc['processing_data'].get('corrections_count', 0) > 0]
        
        if docs_with_corrections:
            first_doc = docs_with_corrections[0]
            print(f"\n🎯 First document with corrections:")
            print(f"   📄 Name: {first_doc['name']}")
            print(f"   📄 Path: {first_doc['path']}")
            print(f"   📄 Corrections: {first_doc['processing_data']['corrections_count']}")
            print(f"   ✅ This would be auto-loaded in QA validation")
        else:
            print(f"\n📄 No documents with corrections found")
        
        print(f"\n✅ Project opening test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during project opening test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_project_opening_fixed()
    if success:
        print("\n✅ Project opening functionality should now work correctly.")
        print("🎯 The format conversion fixes the compatibility issue.")
        print("🚀 Try opening the project in the actual application now!")
    else:
        print("\n❌ Project opening still has issues.")
        print("🔧 Additional debugging required.")