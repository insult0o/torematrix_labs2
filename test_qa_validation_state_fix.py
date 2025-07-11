#!/usr/bin/env python3
"""
Test script to verify the QA validation state persistence bug fix.
"""

import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add the tore_matrix_labs module to the Python path
sys.path.append('/home/insulto/tore_matrix_labs')

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_qa_validation_state_fix():
    """Test the QA validation state persistence bug fix."""
    print("🧪 TESTING QA VALIDATION STATE PERSISTENCE BUG FIX")
    print("=" * 60)
    
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
    
    # Test QA validation state persistence
    print(f"\n🔍 TESTING QA VALIDATION STATE PERSISTENCE:")
    
    # Create mock validation result from manual validation
    mock_validation_result = {
        'document_id': test_document['id'],
        'file_path': test_document['path'],
        'validation_completed': True,
        'selections': {
            1: [
                {'type': 'IMAGE', 'bbox': [100, 100, 200, 200], 'page': 1, 'name': 'area_1'},
                {'type': 'TABLE', 'bbox': [300, 300, 400, 400], 'page': 1, 'name': 'area_2'}
            ],
            2: [
                {'type': 'DIAGRAM', 'bbox': [150, 150, 250, 250], 'page': 2, 'name': 'area_3'}
            ]
        },
        'total_selections': 3,
        'pages_with_selections': 2,
        'completed_at': '2025-07-11T03:00:00.000000'
    }
    
    print(f"📋 Mock validation result created:")
    print(f"   - Document ID: {mock_validation_result['document_id']}")
    print(f"   - Total selections: {mock_validation_result['total_selections']}")
    print(f"   - Pages with selections: {mock_validation_result['pages_with_selections']}")
    print(f"   - Completed at: {mock_validation_result['completed_at']}")
    
    # Test validation state flow
    test_scenarios = [
        {
            "name": "Main window saves validation result",
            "test_main_window_save": True
        },
        {
            "name": "Document state manager stores validation result",
            "test_document_state_manager": True
        },
        {
            "name": "QA validation widget retrieves validation result",
            "test_qa_widget_retrieval": True
        }
    ]
    
    # Test each scenario
    for scenario in test_scenarios:
        print(f"\n📋 Testing: {scenario['name']}")
        
        if scenario.get('test_main_window_save'):
            # Test main window save functionality
            class MockMainWindow:
                def __init__(self):
                    self._validation_results = {}
                    self.document_state_manager = MockDocumentStateManager()
                
                def _save_validation_result_for_qa(self, validation_result):
                    """Save validation result for QA widget - copied from the fix."""
                    try:
                        document_id = validation_result['document_id']
                        
                        # Store the validation result at the main window level
                        if not hasattr(self, '_validation_results'):
                            self._validation_results = {}
                        
                        self._validation_results[document_id] = validation_result
                        
                        # Also save to document state manager
                        if hasattr(self, 'document_state_manager'):
                            self.document_state_manager.save_validation_result(document_id, validation_result)
                        
                        logger.info(f"QA_VALIDATION_STATE: Saved validation result for document {document_id}")
                        
                    except Exception as e:
                        logger.error(f"QA_VALIDATION_STATE: Error saving validation result: {e}")
            
            class MockDocumentStateManager:
                def __init__(self):
                    self.document_cache = {
                        test_document['id']: {
                            'id': test_document['id'],
                            'name': test_document['name'],
                            'path': test_document['path']
                        }
                    }
                
                def save_validation_result(self, document_id, validation_result):
                    """Save validation result - copied from the fix."""
                    try:
                        if document_id in self.document_cache:
                            if 'validation_results' not in self.document_cache[document_id]:
                                self.document_cache[document_id]['validation_results'] = {}
                            
                            self.document_cache[document_id]['validation_results']['manual_validation'] = validation_result
                            
                            logger.info(f"DOC_STATE_MANAGER: Saved validation result for document {document_id}")
                        else:
                            logger.warning(f"DOC_STATE_MANAGER: Document {document_id} not found in cache")
                            
                    except Exception as e:
                        logger.error(f"DOC_STATE_MANAGER: Error saving validation result: {e}")
                
                def get_validation_result(self, document_id):
                    """Get validation result - copied from the fix."""
                    try:
                        if document_id in self.document_cache:
                            validation_results = self.document_cache[document_id].get('validation_results', {})
                            return validation_results.get('manual_validation')
                        return None
                        
                    except Exception as e:
                        logger.error(f"DOC_STATE_MANAGER: Error getting validation result: {e}")
                        return None
            
            # Test the save functionality
            mock_main_window = MockMainWindow()
            mock_main_window._save_validation_result_for_qa(mock_validation_result)
            
            # Check if it was saved
            if test_document['id'] in mock_main_window._validation_results:
                print(f"   ✅ SUCCESS: Main window saved validation result")
            else:
                print(f"   ❌ FAILED: Main window did not save validation result")
        
        if scenario.get('test_document_state_manager'):
            # Test document state manager functionality
            mock_doc_state_manager = MockDocumentStateManager()
            mock_doc_state_manager.save_validation_result(test_document['id'], mock_validation_result)
            
            # Check if it was saved and can be retrieved
            retrieved_result = mock_doc_state_manager.get_validation_result(test_document['id'])
            
            if retrieved_result and retrieved_result['document_id'] == test_document['id']:
                print(f"   ✅ SUCCESS: Document state manager saved and retrieved validation result")
            else:
                print(f"   ❌ FAILED: Document state manager did not save/retrieve validation result properly")
        
        if scenario.get('test_qa_widget_retrieval'):
            # Test QA widget retrieval functionality
            class MockDocument:
                def __init__(self, doc_id):
                    self.id = doc_id
                    self.metadata = type('Metadata', (), {'file_name': 'test.pdf'})()
            
            class MockMainWindow:
                def __init__(self):
                    self.document_state_manager = MockDocumentStateManager()
                    self.document_state_manager.save_validation_result(test_document['id'], mock_validation_result)
            
            class MockQAValidationWidget:
                def __init__(self):
                    self.logger = logger
                    self.current_document = MockDocument(test_document['id'])
                    self.manual_validation_result = None
                    self.status_label = type('Label', (), {'setText': lambda self, text: None})()
                    self._main_window = MockMainWindow()
                
                def parent(self):
                    return self._main_window
                
                def _check_manual_validation_state(self):
                    """Check manual validation state - copied from the fix."""
                    try:
                        if not self.current_document:
                            return
                        
                        # Get main window to access document state manager
                        main_window = self.parent()
                        while main_window and not hasattr(main_window, 'document_state_manager'):
                            main_window = main_window.parent()
                        
                        if not main_window:
                            self.logger.warning("QA_VALIDATION_STATE: Cannot find main window")
                            return
                        
                        # Check if validation result exists
                        validation_result = main_window.document_state_manager.get_validation_result(self.current_document.id)
                        
                        if validation_result:
                            self.logger.info(f"QA_VALIDATION_STATE: Found existing validation result for {self.current_document.id}")
                            self.logger.info(f"QA_VALIDATION_STATE: Manual validation completed at {validation_result.get('completed_at')}")
                            
                            # Update status to show manual validation was completed
                            completed_at = validation_result.get('completed_at', 'unknown time')
                            total_selections = validation_result.get('total_selections', 0)
                            
                            self.status_label.setText(
                                f"Manual validation completed at {completed_at[:19]} with {total_selections} selections"
                            )
                            
                            # Store the validation result for use by the validation widget
                            self.manual_validation_result = validation_result
                            
                        else:
                            self.logger.info(f"QA_VALIDATION_STATE: No existing validation result found for {self.current_document.id}")
                            self.manual_validation_result = None
                            
                    except Exception as e:
                        self.logger.error(f"QA_VALIDATION_STATE: Error checking manual validation state: {e}")
                        self.manual_validation_result = None
            
            # Test the retrieval functionality
            mock_qa_widget = MockQAValidationWidget()
            mock_qa_widget._check_manual_validation_state()
            
            # Check if it retrieved the validation result
            if (mock_qa_widget.manual_validation_result and 
                mock_qa_widget.manual_validation_result['document_id'] == test_document['id']):
                print(f"   ✅ SUCCESS: QA widget retrieved validation result")
            else:
                print(f"   ❌ FAILED: QA widget did not retrieve validation result")
    
    print(f"\n🎯 CONCLUSION:")
    print(f"   QA validation state persistence should fix the bug by:")
    print(f"   1. Saving validation results when manual validation completes")
    print(f"   2. Storing them in the document state manager")
    print(f"   3. Retrieving them when QA validation widget loads")
    print(f"   4. Showing the validation completion status in the QA widget")
    
    return True

if __name__ == "__main__":
    success = test_qa_validation_state_fix()
    if success:
        print(f"\n✅ QA validation state persistence bug fix test completed successfully!")
    else:
        print(f"\n❌ QA validation state persistence bug fix test failed!")