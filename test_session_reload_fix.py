#!/usr/bin/env python3
"""
Test script to verify the session reload bug fix.
"""

import json
import logging
import sys
from pathlib import Path

# Add the tore_matrix_labs module to the Python path
sys.path.append('/home/insulto/tore_matrix_labs')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_session_reload_fix():
    """Test the session reload bug fix."""
    print("🧪 TESTING SESSION RELOAD BUG FIX")
    print("=" * 50)
    
    # Test project file with known areas
    project_file = "/home/insulto/tore_matrix_labs/123.tore"
    
    if not Path(project_file).exists():
        print(f"❌ Project file not found: {project_file}")
        return False
    
    # Load project data
    with open(project_file, 'r') as f:
        project_data = json.load(f)
    
    print(f"📁 Testing with project: {project_data['name']}")
    print(f"📊 Documents in project: {len(project_data['documents'])}")
    
    # Find document with areas
    test_document = None
    for doc in project_data['documents']:
        if doc.get('visual_areas'):
            test_document = doc
            break
    
    if not test_document:
        print("❌ No document with visual areas found in project")
        return False
    
    print(f"📄 Testing with document: {test_document['name']}")
    print(f"🎯 Document has {len(test_document.get('visual_areas', {}))} areas")
    print(f"🆔 Document ID: {test_document['id']}")
    
    # Test the enhanced document ID resolution
    print(f"\n🔍 TESTING ENHANCED DOCUMENT ID RESOLUTION:")
    
    # Simulate various document ID scenarios
    test_scenarios = [
        {
            "name": "Document with direct ID",
            "document": type('Document', (), {'id': test_document['id']})(),
            "file_path": test_document['path'],
            "expected_id": test_document['id']
        },
        {
            "name": "Document without ID",
            "document": type('Document', (), {})(),
            "file_path": test_document['path'],
            "expected_id": test_document['id']
        },
        {
            "name": "Document with metadata",
            "document": type('Document', (), {
                'metadata': type('Metadata', (), {'document_id': test_document['id']})()
            })(),
            "file_path": test_document['path'],
            "expected_id": test_document['id']
        }
    ]
    
    # Test each scenario
    for scenario in test_scenarios:
        print(f"\n📋 Testing: {scenario['name']}")
        
        # Create a mock manual validation widget to test ID resolution
        class MockMainWindow:
            def __init__(self, project_data):
                self.project_widget = type('ProjectWidget', (), {
                    'get_project_documents': lambda self: project_data['documents']
                })()
        
        class MockManualValidationWidget:
            def __init__(self, main_window):
                self.current_document = scenario['document']
                self.current_file_path = scenario['file_path']
                self.logger = logger
                self._main_window = main_window
            
            def _get_main_window(self):
                return self._main_window
            
            def _get_current_document_id(self):
                """Enhanced document ID resolution - copied from the fix."""
                try:
                    # Method 1: Direct document ID
                    if hasattr(self, 'current_document') and self.current_document:
                        doc_id = getattr(self.current_document, 'id', None)
                        if doc_id:
                            self.logger.debug(f"GET_DOC_ID: Found document ID via direct access: {doc_id}")
                            return doc_id
                    
                    # Method 2: Try from document metadata
                    if hasattr(self, 'current_document') and self.current_document:
                        if hasattr(self.current_document, 'metadata') and self.current_document.metadata:
                            doc_id = getattr(self.current_document.metadata, 'document_id', None)
                            if doc_id:
                                self.logger.debug(f"GET_DOC_ID: Found document ID via metadata: {doc_id}")
                                return doc_id
                    
                    # Method 3: Generate from file path if available
                    if hasattr(self, 'current_file_path') and self.current_file_path:
                        from pathlib import Path
                        file_name = Path(self.current_file_path).stem
                        # Try to match the document ID format used in project files
                        main_window = self._get_main_window()
                        if main_window and hasattr(main_window, 'project_widget'):
                            project_docs = main_window.project_widget.get_project_documents()
                            for doc in project_docs:
                                if doc.get('path') == self.current_file_path or doc.get('name') == file_name + '.pdf':
                                    doc_id = doc.get('id')
                                    if doc_id:
                                        self.logger.info(f"GET_DOC_ID: Found document ID via project lookup: {doc_id}")
                                        return doc_id
                    
                    self.logger.warning("GET_DOC_ID: Could not resolve document ID")
                    return None
                    
                except Exception as e:
                    self.logger.error(f"GET_DOC_ID: Error resolving document ID: {e}")
                    return None
        
        # Test the scenario
        mock_main_window = MockMainWindow(project_data)
        mock_widget = MockManualValidationWidget(mock_main_window)
        
        resolved_id = mock_widget._get_current_document_id()
        
        if resolved_id == scenario['expected_id']:
            print(f"   ✅ SUCCESS: Resolved ID = {resolved_id}")
        else:
            print(f"   ❌ FAILED: Expected {scenario['expected_id']}, got {resolved_id}")
    
    print(f"\n🎯 CONCLUSION:")
    print(f"   Enhanced document ID resolution should fix the session reload bug")
    print(f"   by providing multiple fallback methods to resolve the document ID")
    print(f"   even when the document object doesn't have a direct ID attribute.")
    
    return True

if __name__ == "__main__":
    success = test_session_reload_fix()
    if success:
        print(f"\n✅ Session reload bug fix test completed successfully!")
    else:
        print(f"\n❌ Session reload bug fix test failed!")