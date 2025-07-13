"""
Unit tests for reducers.

Tests cover:
- State updates
- Immutability verification
- Unknown action handling
- Reducer composition
"""

import pytest
from copy import deepcopy

from torematrix.core.state.reducers import (
    combine_reducers, create_root_reducer,
    document_reducer, elements_reducer, ui_reducer, async_reducer,
    update_nested
)
from torematrix.core.state.actions import (
    Action, ActionType,
    set_document, add_element, update_element, delete_element,
    async_start, async_success, async_failure,
    create_action
)


class TestDocumentReducer:
    """Test document reducer functionality."""
    
    def test_initial_state(self):
        """Test document reducer returns initial state."""
        state = document_reducer(None, Action(type='UNKNOWN'))
        
        assert state == {
            'current_id': None,
            'document_path': None,
            'document_data': None,
            'is_modified': False,
            'metadata': {}
        }
    
    def test_set_document(self):
        """Test setting a document."""
        initial_state = document_reducer(None, Action(type='INIT'))
        action = set_document('doc123', '/path/to/doc.pdf', {'pages': 10})
        action.payload.metadata = {'author': 'Test'}
        
        new_state = document_reducer(initial_state, action)
        
        assert new_state['current_id'] == 'doc123'
        assert new_state['document_path'] == '/path/to/doc.pdf'
        assert new_state['document_data'] == {'pages': 10}
        assert new_state['is_modified'] is False
        assert new_state['metadata'] == {'author': 'Test'}
        
        # Check immutability
        assert new_state is not initial_state
    
    def test_update_document(self):
        """Test updating document data."""
        # Set initial document
        state = document_reducer(None, set_document('doc123', '/path/doc.pdf', {'pages': 10}))
        
        # Update document
        update_action = Action(
            type=ActionType.UPDATE_DOCUMENT,
            payload=type('obj', (object,), {
                'document_id': 'doc123',
                'document_data': {'title': 'Updated Title'}
            })()
        )
        
        new_state = document_reducer(state, update_action)
        
        assert new_state['document_data'] == {'pages': 10, 'title': 'Updated Title'}
        assert new_state['is_modified'] is True
        
        # Update different document ID should not change state
        update_action2 = Action(
            type=ActionType.UPDATE_DOCUMENT,
            payload=type('obj', (object,), {
                'document_id': 'different_id',
                'document_data': {'title': 'Should not update'}
            })()
        )
        
        unchanged_state = document_reducer(new_state, update_action2)
        assert unchanged_state == new_state
    
    def test_close_document(self):
        """Test closing document."""
        # Set document first
        state = document_reducer(None, set_document('doc123', '/path/doc.pdf'))
        
        # Close document
        close_action = Action(type=ActionType.CLOSE_DOCUMENT)
        new_state = document_reducer(state, close_action)
        
        assert new_state == {
            'current_id': None,
            'document_path': None,
            'document_data': None,
            'is_modified': False,
            'metadata': {}
        }
    
    def test_unknown_action(self):
        """Test unknown actions don't change state."""
        state = document_reducer(None, set_document('doc123'))
        unknown_action = Action(type='UNKNOWN_ACTION')
        
        new_state = document_reducer(state, unknown_action)
        assert new_state == state  # Same reference, no change


class TestElementsReducer:
    """Test elements reducer functionality."""
    
    def test_initial_state(self):
        """Test elements reducer initial state."""
        state = elements_reducer(None, Action(type='UNKNOWN'))
        
        assert state == {
            'byId': {},
            'allIds': [],
            'selectedIds': []
        }
    
    def test_add_element(self):
        """Test adding an element."""
        initial_state = elements_reducer(None, Action(type='INIT'))
        action = add_element('elem1', 'text', {'content': 'Hello'}, page_number=1)
        
        new_state = elements_reducer(initial_state, action)
        
        assert 'elem1' in new_state['byId']
        assert new_state['byId']['elem1'] == {
            'id': 'elem1',
            'type': 'text',
            'page_number': 1,
            'content': 'Hello'
        }
        assert 'elem1' in new_state['allIds']
        assert len(new_state['allIds']) == 1
    
    def test_add_duplicate_element(self):
        """Test adding duplicate element doesn't change state."""
        state = elements_reducer(None, add_element('elem1', 'text', {'content': 'Hello'}))
        duplicate_action = add_element('elem1', 'text', {'content': 'Different'})
        
        new_state = elements_reducer(state, duplicate_action)
        
        # Should not add duplicate
        assert new_state == state
        assert new_state['byId']['elem1']['content'] == 'Hello'  # Original content
    
    def test_update_element(self):
        """Test updating an element."""
        # Add element first
        state = elements_reducer(None, add_element('elem1', 'text', {'content': 'Hello'}))
        
        # Update element
        update_action = update_element('elem1', {'content': 'Updated', 'style': 'bold'})
        new_state = elements_reducer(state, update_action)
        
        assert new_state['byId']['elem1']['content'] == 'Updated'
        assert new_state['byId']['elem1']['style'] == 'bold'
        assert new_state['byId']['elem1']['type'] == 'text'  # Unchanged
    
    def test_update_nonexistent_element(self):
        """Test updating non-existent element doesn't change state."""
        state = elements_reducer(None, Action(type='INIT'))
        update_action = update_element('nonexistent', {'content': 'Test'})
        
        new_state = elements_reducer(state, update_action)
        assert new_state == state
    
    def test_delete_element(self):
        """Test deleting an element."""
        # Add two elements
        state = elements_reducer(None, add_element('elem1', 'text', {}))
        state = elements_reducer(state, add_element('elem2', 'text', {}))
        
        # Select elem1
        state['selectedIds'] = ['elem1']
        
        # Delete elem1
        delete_action = delete_element('elem1')
        new_state = elements_reducer(state, delete_action)
        
        assert 'elem1' not in new_state['byId']
        assert 'elem1' not in new_state['allIds']
        assert 'elem1' not in new_state['selectedIds']
        assert 'elem2' in new_state['byId']
        assert len(new_state['allIds']) == 1
    
    def test_select_element(self):
        """Test selecting an element."""
        # Add elements
        state = elements_reducer(None, add_element('elem1', 'text', {}))
        state = elements_reducer(state, add_element('elem2', 'text', {}))
        
        # Select elem2
        select_action = Action(
            type=ActionType.SELECT_ELEMENT,
            payload=type('obj', (object,), {'element_id': 'elem2'})()
        )
        
        new_state = elements_reducer(state, select_action)
        assert new_state['selectedIds'] == ['elem2']


class TestUIReducer:
    """Test UI reducer functionality."""
    
    def test_initial_state(self):
        """Test UI reducer initial state."""
        state = ui_reducer(None, Action(type='UNKNOWN'))
        
        assert state == {
            'current_page': 1,
            'zoom_level': 1.0,
            'view_mode': 'single',
            'sidebar_visible': True
        }
    
    def test_set_page(self):
        """Test setting current page."""
        state = ui_reducer(None, Action(type='INIT'))
        action = Action(type=ActionType.SET_PAGE, payload=5)
        
        new_state = ui_reducer(state, action)
        assert new_state['current_page'] == 5
    
    def test_set_zoom(self):
        """Test setting zoom level."""
        state = ui_reducer(None, Action(type='INIT'))
        
        # Normal zoom
        action = Action(type=ActionType.SET_ZOOM, payload=2.0)
        new_state = ui_reducer(state, action)
        assert new_state['zoom_level'] == 2.0
        
        # Test clamping - too low
        action_low = Action(type=ActionType.SET_ZOOM, payload=0.05)
        new_state = ui_reducer(state, action_low)
        assert new_state['zoom_level'] == 0.1
        
        # Test clamping - too high
        action_high = Action(type=ActionType.SET_ZOOM, payload=10.0)
        new_state = ui_reducer(state, action_high)
        assert new_state['zoom_level'] == 5.0
    
    def test_set_view_mode(self):
        """Test setting view mode."""
        state = ui_reducer(None, Action(type='INIT'))
        
        # Valid view mode
        action = Action(type=ActionType.SET_VIEW_MODE, payload='continuous')
        new_state = ui_reducer(state, action)
        assert new_state['view_mode'] == 'continuous'
        
        # Invalid view mode
        action_invalid = Action(type=ActionType.SET_VIEW_MODE, payload='invalid')
        unchanged_state = ui_reducer(new_state, action_invalid)
        assert unchanged_state == new_state
    
    def test_toggle_sidebar(self):
        """Test toggling sidebar visibility."""
        state = ui_reducer(None, Action(type='INIT'))
        assert state['sidebar_visible'] is True
        
        # Toggle off
        action = Action(type=ActionType.TOGGLE_SIDEBAR)
        new_state = ui_reducer(state, action)
        assert new_state['sidebar_visible'] is False
        
        # Toggle back on
        new_state2 = ui_reducer(new_state, action)
        assert new_state2['sidebar_visible'] is True


class TestAsyncReducer:
    """Test async reducer functionality."""
    
    def test_initial_state(self):
        """Test async reducer initial state."""
        state = async_reducer(None, Action(type='UNKNOWN'))
        
        assert state == {
            'pending': {},
            'errors': {}
        }
    
    def test_async_start(self):
        """Test starting async operation."""
        state = async_reducer(None, Action(type='INIT'))
        action = async_start('req123', 'loadDocument', {'id': 'doc1'})
        
        new_state = async_reducer(state, action)
        
        assert 'req123' in new_state['pending']
        assert new_state['pending']['req123']['operation'] == 'loadDocument'
        assert new_state['pending']['req123']['data'] == {'id': 'doc1'}
        assert 'started_at' in new_state['pending']['req123']
    
    def test_async_success(self):
        """Test async operation success."""
        # Start operation
        state = async_reducer(None, async_start('req123', 'loadDocument'))
        
        # Complete successfully
        action = async_success('req123', 'loadDocument', {'result': 'success'})
        new_state = async_reducer(state, action)
        
        # Should be removed from pending
        assert 'req123' not in new_state['pending']
        assert len(new_state['errors']) == 0
    
    def test_async_failure(self):
        """Test async operation failure."""
        # Start operation
        state = async_reducer(None, async_start('req123', 'loadDocument'))
        
        # Fail
        error = Exception('Network error')
        action = async_failure('req123', 'loadDocument', error)
        new_state = async_reducer(state, action)
        
        # Should be removed from pending and added to errors
        assert 'req123' not in new_state['pending']
        assert 'req123' in new_state['errors']
        assert new_state['errors']['req123']['error'] == 'Network error'
        assert new_state['errors']['req123']['operation'] == 'loadDocument'


class TestCombineReducers:
    """Test reducer composition."""
    
    def test_combine_reducers(self):
        """Test combining multiple reducers."""
        # Create simple reducers
        def counter_reducer(state=0, action):
            if action.type == 'INCREMENT':
                return state + 1
            return state
        
        def toggle_reducer(state=False, action):
            if action.type == 'TOGGLE':
                return not state
            return state
        
        # Combine them
        root_reducer = combine_reducers({
            'counter': counter_reducer,
            'toggle': toggle_reducer
        })
        
        # Test initial state
        state = root_reducer({}, Action(type='INIT'))
        assert state == {'counter': 0, 'toggle': False}
        
        # Test increment
        state = root_reducer(state, Action(type='INCREMENT'))
        assert state == {'counter': 1, 'toggle': False}
        
        # Test toggle
        state = root_reducer(state, Action(type='TOGGLE'))
        assert state == {'counter': 1, 'toggle': True}
    
    def test_combine_reducers_immutability(self):
        """Test combined reducers maintain immutability."""
        def changing_reducer(state={'value': 1}, action):
            if action.type == 'CHANGE':
                return {'value': state['value'] + 1}
            return state
        
        root_reducer = combine_reducers({'data': changing_reducer})
        
        state1 = root_reducer({}, Action(type='INIT'))
        state2 = root_reducer(state1, Action(type='CHANGE'))
        
        # States should be different objects
        assert state1 is not state2
        assert state1['data'] is not state2['data']
        assert state1['data']['value'] == 1
        assert state2['data']['value'] == 2
    
    def test_root_reducer(self):
        """Test the actual root reducer."""
        reducer = create_root_reducer()
        
        # Initial state
        state = reducer({}, Action(type='INIT'))
        
        # Should have all slices
        assert 'document' in state
        assert 'elements' in state
        assert 'ui' in state
        assert 'async' in state
        
        # Test a real action
        state = reducer(state, set_document('doc123'))
        assert state['document']['current_id'] == 'doc123'


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_update_nested(self):
        """Test nested update utility."""
        obj = {
            'level1': {
                'level2': {
                    'value': 'original'
                }
            }
        }
        
        # Update nested value
        new_obj = update_nested(obj, 'level1.level2.value', 'updated')
        
        assert new_obj['level1']['level2']['value'] == 'updated'
        assert obj['level1']['level2']['value'] == 'original'  # Original unchanged
        
        # Test creating new paths
        new_obj2 = update_nested(obj, 'level1.new.path', 'created')
        assert new_obj2['level1']['new']['path'] == 'created'