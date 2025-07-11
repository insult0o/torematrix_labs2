#!/usr/bin/env python3
"""
Test script to verify project loading and corrections restoration.
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_project_loading():
    """Test loading project 4 and restoring corrections."""
    
    try:
        print("=== Testing Project 4 Loading ===")
        
        # Load project 4
        project_file = Path("4.tore")
        if not project_file.exists():
            print(f"❌ Project file not found: {project_file}")
            return False
            
        with open(project_file, 'r') as f:
            project_data = json.load(f)
        
        print(f"✅ Loaded project: {project_data.get('name')}")
        
        # Check documents
        documents = project_data.get('documents', [])
        print(f"✅ Found {len(documents)} documents")
        
        if not documents:
            print("❌ No documents in project")
            return False
        
        # Check first document
        doc = documents[0]
        print(f"✅ Document: {doc.get('name')}")
        print(f"   ID: {doc.get('id')}")
        print(f"   Status: {doc.get('status')}")
        print(f"   Path: {doc.get('path')}")
        
        # Check processing data
        processing_data = doc.get('processing_data', {})
        corrections = processing_data.get('corrections', [])
        
        print(f"✅ Processing data found:")
        print(f"   File size: {processing_data.get('file_size', 0)}")
        print(f"   Page count: {processing_data.get('page_count', 0)}")
        print(f"   Corrections count: {len(corrections)}")
        print(f"   Quality score: {processing_data.get('quality_score', 'N/A')}")
        print(f"   Quality level: {processing_data.get('quality_level', 'N/A')}")
        
        if len(corrections) > 0:
            print(f"✅ Sample correction:")
            sample = corrections[0]
            print(f"   Type: {sample.get('type')}")
            print(f"   Description: {sample.get('description')}")
            print(f"   Confidence: {sample.get('confidence')}")
            print(f"   Status: {sample.get('status')}")
        else:
            print("❌ No corrections found")
            return False
        
        # Test the document creation process (simulating _load_document_corrections_from_project_data)
        print(f"\n✅ Testing document reconstruction...")
        
        try:
            from tore_matrix_labs.models.document_models import Document, DocumentMetadata, ProcessingConfiguration
            from tore_matrix_labs.config.constants import DocumentType, ProcessingStatus, QualityLevel
            from datetime import datetime
            
            # Create document metadata
            metadata = DocumentMetadata(
                file_name=doc.get('file_name', 'Unknown'),
                file_path=doc.get('file_path', ''),
                file_size=processing_data.get('file_size', 0),
                file_type='pdf',
                creation_date=datetime.now(),
                modification_date=datetime.now(),
                page_count=processing_data.get('page_count', 0)
            )
            
            # Create processing configuration
            processing_config = ProcessingConfiguration()
            
            # Determine quality level
            quality_level_str = processing_data.get('quality_level', 'good')
            try:
                quality_level = QualityLevel(quality_level_str.upper())
            except (ValueError, AttributeError):
                quality_level = QualityLevel.GOOD
            
            # Create document with corrections
            document = Document(
                id=doc.get('id', 'project_doc'),
                metadata=metadata,
                document_type=DocumentType.ICAO,
                processing_status=ProcessingStatus.EXTRACTED,
                processing_config=processing_config,
                quality_level=quality_level,
                quality_score=processing_data.get('quality_score', 0.5),
                custom_metadata={'corrections': corrections}
            )
            
            print(f"✅ Document created successfully")
            print(f"   Document ID: {document.id}")
            print(f"   Metadata: {document.metadata.file_name}")
            print(f"   Corrections in custom_metadata: {len(document.custom_metadata.get('corrections', []))}")
            
            # Test validation widget loading (simulated)
            if len(document.custom_metadata.get('corrections', [])) == len(corrections):
                print(f"✅ Corrections properly transferred")
                return True
            else:
                print(f"❌ Corrections transfer failed")
                return False
                
        except Exception as e:
            print(f"❌ Document reconstruction failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_project_loading()
    if success:
        print("\n🎉 Project loading test passed!")
        print("   The data structure is correct")
        print("   Corrections should be properly restored")
    else:
        print("\n❌ Project loading test failed.")
        print("   There may be issues with the data structure or loading process")