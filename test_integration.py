#!/usr/bin/env python3
"""
Test script to verify application integration.
"""

import sys
import json
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_document_processing():
    """Test the document processing and data flow."""
    print("=== Testing Document Processing Integration ===")
    
    # Check if processed document exists
    output_file = Path("output/5555_complete.json")
    if output_file.exists():
        print(f"✅ Found processed document: {output_file}")
        
        # Load and analyze the data
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        print(f"✅ Document ID: {data.get('document_info', {}).get('id')}")
        print(f"✅ File name: {data.get('document_info', {}).get('file_name')}")
        print(f"✅ Processing status: {data.get('document_info', {}).get('processing_status')}")
        
        # Check for quality assessment
        qa = data.get('quality_assessment', {})
        if qa:
            issues = qa.get('issues', [])
            print(f"✅ Quality issues found: {len(issues)}")
            if issues:
                print(f"   First issue: {issues[0].get('description', 'No description')}")
        else:
            print("❌ No quality assessment found")
            
    else:
        print(f"❌ No processed document found at: {output_file}")

def test_project_file():
    """Test project file structure."""
    print("\n=== Testing Project File ===")
    
    project_file = Path("1.tore")
    if project_file.exists():
        print(f"✅ Found project file: {project_file}")
        
        with open(project_file, 'r') as f:
            project_data = json.load(f)
        
        print(f"✅ Project name: {project_data.get('name')}")
        print(f"✅ Documents in project: {len(project_data.get('documents', []))}")
        
        for doc in project_data.get('documents', []):
            print(f"   - {doc.get('name', 'Unknown')} ({doc.get('status', 'unknown')})")
    else:
        print(f"❌ No project file found")

def test_pdf_file():
    """Test PDF file accessibility."""
    print("\n=== Testing PDF File ===")
    
    pdf_file = Path("5555.pdf")
    if pdf_file.exists():
        print(f"✅ Found PDF file: {pdf_file}")
        print(f"✅ File size: {pdf_file.stat().st_size / (1024*1024):.1f} MB")
        
        # Test if we can import and use PyMuPDF
        try:
            import fitz
            doc = fitz.open(str(pdf_file))
            print(f"✅ PyMuPDF can open file: {len(doc)} pages")
            doc.close()
        except Exception as e:
            print(f"❌ PyMuPDF error: {e}")
    else:
        print(f"❌ PDF file not found")

if __name__ == "__main__":
    test_document_processing()
    test_project_file()
    test_pdf_file()
    print("\n=== Integration Test Complete ===")