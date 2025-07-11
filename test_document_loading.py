#!/usr/bin/env python3
"""
Test document loading specifically.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_document_creation():
    """Test document creation with file path."""
    print("🧪 Testing Document Creation")
    print("=" * 50)
    
    try:
        from tore_matrix_labs.models.document_models import Document, DocumentMetadata
        from datetime import datetime
        import uuid
        
        # Create a test file path
        test_file_path = "/test/path/to/document.pdf"
        
        # Create metadata like the main window does
        metadata = DocumentMetadata(
            file_name="document.pdf",
            file_path=test_file_path,
            file_size=1000,
            file_type=".pdf",
            creation_date=datetime.now(),
            modification_date=datetime.now(),
            page_count=5
        )
        
        print(f"✅ DocumentMetadata created with file_path: {metadata.file_path}")
        
        # Create document like the main window does
        document = Document(
            id=str(uuid.uuid4()),
            metadata=metadata,
            document_type="ICAO",
            processing_status="PENDING",
            processing_config=None,
            quality_level="GOOD",
            quality_score=0.0
        )
        
        print(f"✅ Document created with metadata.file_path: {document.metadata.file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    success = test_document_creation()
    if success:
        print("🎉 Document loading should work now!")
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)