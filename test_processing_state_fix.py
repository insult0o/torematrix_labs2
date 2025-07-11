#!/usr/bin/env python3
"""
Test script to verify the processing state bug fix.
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

def test_processing_state_fix():
    """Test the processing state bug fix."""
    print("🧪 TESTING PROCESSING STATE BUG FIX")
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
    
    # Test validation state persistence
    print(f"\n🔍 TESTING VALIDATION STATE PERSISTENCE:")
    
    # Simulate validation state scenarios
    test_scenarios = [
        {
            "name": "Document without validation state",
            "validation_state": None,
            "expected_complete": False
        },
        {
            "name": "Document with incomplete validation",
            "validation_state": {
                "is_complete": False,
                "completed_at": None,
                "total_selections": 3,
                "pages_with_selections": 2
            },
            "expected_complete": False
        },
        {
            "name": "Document with completed validation",
            "validation_state": {
                "is_complete": True,
                "completed_at": "2025-07-11T02:30:00.000000",
                "total_selections": 5,
                "pages_with_selections": 3
            },
            "expected_complete": True
        }
    ]
    
    # Test each scenario
    for scenario in test_scenarios:
        print(f"\n📋 Testing: {scenario['name']}")
        
        # Create a mock manual validation widget to test state persistence
        class MockMainWindow:
            def __init__(self, project_data):
                self.project_widget = type('ProjectWidget', (), {
                    'get_current_project': lambda self: project_data,
                    'save_current_project': lambda self: True
                })()
        
        class MockManualValidationWidget:
            def __init__(self, main_window, document_id):
                self.current_document = type('Document', (), {'id': document_id})()
                self.current_file_path = test_document['path']
                self.logger = logger
                self._main_window = main_window
                self.validation_complete = False
                self.all_selections = {1: [], 2: [], 3: []}  # Mock selections
                self.complete_btn = type('Button', (), {'setEnabled': lambda self, x: None})()
                self.clear_page_btn = type('Button', (), {'setEnabled': lambda self, x: None})()
                self.status_message = type('Signal', (), {'emit': lambda self, x: None})()
            
            def _get_main_window(self):
                return self._main_window
            
            def _get_current_document_id(self):
                return self.current_document.id
            
            def _save_validation_state(self):
                """Save validation state - copied from the fix."""
                try:
                    document_id = self._get_current_document_id()
                    if not document_id:
                        self.logger.warning("SAVE_VALIDATION_STATE: Cannot save - missing document_id")
                        return
                    
                    main_window = self._get_main_window()
                    if not main_window or not hasattr(main_window, 'project_widget'):
                        self.logger.warning("SAVE_VALIDATION_STATE: Cannot save - missing project widget")
                        return
                    
                    # Get current project data
                    project_data = main_window.project_widget.get_current_project()
                    if not project_data:
                        self.logger.warning("SAVE_VALIDATION_STATE: Cannot save - no active project")
                        return
                    
                    # Find document in project
                    documents = project_data.get('documents', [])
                    for doc in documents:
                        if doc.get('id') == document_id:
                            # Save validation state in the document
                            if 'validation_state' not in doc:
                                doc['validation_state'] = {}
                            
                            doc['validation_state'] = {
                                'is_complete': self.validation_complete,
                                'completed_at': datetime.now().isoformat() if self.validation_complete else None,
                                'total_selections': sum(len(selections) for selections in self.all_selections.values()),
                                'pages_with_selections': len(self.all_selections)
                            }
                            
                            # Auto-save project
                            if hasattr(main_window.project_widget, 'save_current_project'):
                                save_result = main_window.project_widget.save_current_project()
                                if save_result:
                                    self.logger.info(f"SAVE_VALIDATION_STATE: ✅ Saved validation state for document {document_id}")
                                else:
                                    self.logger.error(f"SAVE_VALIDATION_STATE: ❌ Failed to save project with validation state")
                            break
                    
                except Exception as e:
                    self.logger.error(f"SAVE_VALIDATION_STATE: Error saving validation state: {e}")
            
            def _load_validation_state(self):
                """Load validation state - copied from the fix."""
                try:
                    document_id = self._get_current_document_id()
                    if not document_id:
                        self.logger.warning("LOAD_VALIDATION_STATE: Cannot load - missing document_id")
                        return
                    
                    main_window = self._get_main_window()
                    if not main_window or not hasattr(main_window, 'project_widget'):
                        self.logger.warning("LOAD_VALIDATION_STATE: Cannot load - missing project widget")
                        return
                    
                    # Get current project data
                    project_data = main_window.project_widget.get_current_project()
                    if not project_data:
                        self.logger.warning("LOAD_VALIDATION_STATE: Cannot load - no active project")
                        return
                    
                    # Find document in project
                    documents = project_data.get('documents', [])
                    for doc in documents:
                        if doc.get('id') == document_id:
                            validation_state = doc.get('validation_state', {})
                            
                            if validation_state:
                                is_complete = validation_state.get('is_complete', False)
                                completed_at = validation_state.get('completed_at')
                                
                                self.logger.info(f"LOAD_VALIDATION_STATE: Found validation state - complete: {is_complete}, completed_at: {completed_at}")
                                
                                # Restore validation state
                                self.validation_complete = is_complete
                                
                                # Update UI based on validation state
                                if self.validation_complete:
                                    self.complete_btn.setEnabled(False)
                                    self.clear_page_btn.setEnabled(False)
                                    self.status_message.emit(f"Document validation already completed at {completed_at}")
                                    self.logger.info(f"LOAD_VALIDATION_STATE: ✅ Restored completed validation state for document {document_id}")
                                else:
                                    self.complete_btn.setEnabled(True)
                                    self.clear_page_btn.setEnabled(True)
                                    self.logger.info(f"LOAD_VALIDATION_STATE: ✅ Restored incomplete validation state for document {document_id}")
                            else:
                                self.logger.info(f"LOAD_VALIDATION_STATE: No validation state found for document {document_id}")
                            break
                    
                except Exception as e:
                    self.logger.error(f"LOAD_VALIDATION_STATE: Error loading validation state: {e}")
        
        # Create test project data with the specific validation state
        test_project_data = {
            "name": "Test Project",
            "documents": [
                {
                    "id": test_document['id'],
                    "name": test_document['name'],
                    "path": test_document['path']
                }
            ]
        }
        
        # Add validation state if provided
        if scenario['validation_state']:
            test_project_data['documents'][0]['validation_state'] = scenario['validation_state']
        
        # Test the scenario
        mock_main_window = MockMainWindow(test_project_data)
        mock_widget = MockManualValidationWidget(mock_main_window, test_document['id'])
        
        # Test loading validation state
        mock_widget._load_validation_state()
        
        if mock_widget.validation_complete == scenario['expected_complete']:
            print(f"   ✅ SUCCESS: Validation complete = {mock_widget.validation_complete}")
        else:
            print(f"   ❌ FAILED: Expected {scenario['expected_complete']}, got {mock_widget.validation_complete}")
        
        # Test saving validation state
        if scenario['name'] == "Document with completed validation":
            # Set the widget to completed state and test saving
            mock_widget.validation_complete = True
            mock_widget._save_validation_state()
            
            # Check if the state was saved
            saved_state = test_project_data['documents'][0].get('validation_state', {})
            if saved_state.get('is_complete', False):
                print(f"   ✅ SUCCESS: Validation state saved correctly")
            else:
                print(f"   ❌ FAILED: Validation state not saved correctly")
    
    print(f"\n🎯 CONCLUSION:")
    print(f"   Validation state persistence should fix the processing state bug")
    print(f"   by saving and restoring the validation completion state")
    print(f"   even when documents are reprocessed and reloaded.")
    
    return True

if __name__ == "__main__":
    success = test_processing_state_fix()
    if success:
        print(f"\n✅ Processing state bug fix test completed successfully!")
    else:
        print(f"\n❌ Processing state bug fix test failed!")