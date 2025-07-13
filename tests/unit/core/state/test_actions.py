"""
Unit tests for the action system.

Tests cover:
- Action creation
- Action validation
- Type safety
- Action creators
- Async actions
"""

import pytest
from datetime import datetime
import time

from torematrix.core.state.actions import (
    Action, ActionType, ActionValidator,
    create_action, init_store, reset_store, hydrate_store,
    set_document, add_element, update_element, delete_element,
    async_start, async_success, async_failure,
    DocumentPayload, ElementPayload, AsyncPayload
)


class TestActionTypes:
    """Test action type definitions."""
    
    def test_action_type_enum(self):
        """Test ActionType enum values."""
        # System actions
        assert ActionType.INIT.value == "@@STATE/INIT"
        assert ActionType.RESET.value == "@@STATE/RESET"
        assert ActionType.HYDRATE.value == "@@STATE/HYDRATE"
        
        # Document actions
        assert ActionType.SET_DOCUMENT.value == "DOCUMENT/SET"
        assert ActionType.UPDATE_DOCUMENT.value == "DOCUMENT/UPDATE"
        
        # Element actions
        assert ActionType.ADD_ELEMENT.value == "ELEMENT/ADD"
        assert ActionType.UPDATE_ELEMENT.value == "ELEMENT/UPDATE"
        assert ActionType.DELETE_ELEMENT.value == "ELEMENT/DELETE"
        
        # Async actions
        assert ActionType.ASYNC_START.value == "ASYNC/START"
        assert ActionType.ASYNC_SUCCESS.value == "ASYNC/SUCCESS"
        assert ActionType.ASYNC_FAILURE.value == "ASYNC/FAILURE"


class TestActionCreation:
    """Test action creation and structure."""
    
    def test_basic_action_creation(self):
        """Test creating a basic action."""
        action = Action(type=ActionType.INIT)
        
        assert action.type == ActionType.INIT
        assert action.payload is None
        assert action.meta is None
        assert action.error is False
        assert isinstance(action.timestamp, float)
        assert action.timestamp > 0
        assert isinstance(action.id, str)
        assert len(action.id) > 0
    
    def test_action_with_payload(self):
        """Test creating action with payload."""
        payload = {'key': 'value'}
        action = Action(type=ActionType.SET_DOCUMENT, payload=payload)
        
        assert action.payload == payload
        assert action.type == ActionType.SET_DOCUMENT
    
    def test_action_with_meta(self):
        """Test adding metadata to action."""
        action = Action(type=ActionType.INIT)
        action.with_meta(user='test', source='unit-test')
        
        assert action.meta == {'user': 'test', 'source': 'unit-test'}
        
        # Test chaining
        action.with_meta(additional='data')
        assert action.meta == {
            'user': 'test',
            'source': 'unit-test',
            'additional': 'data'
        }
    
    def test_action_as_error(self):
        """Test marking action as error."""
        action = Action(type=ActionType.ASYNC_FAILURE)
        action.as_error('Something went wrong')
        
        assert action.error is True
        assert action.meta['error_message'] == 'Something went wrong'
    
    def test_action_generic_typing(self):
        """Test action with generic typing."""
        # Action with string payload
        action1 = Action[str](type='TEST', payload='string payload')
        assert action1.payload == 'string payload'
        
        # Action with dict payload
        action2 = Action[dict](type='TEST', payload={'key': 'value'})
        assert action2.payload == {'key': 'value'}


class TestActionCreators:
    """Test action creator functions."""
    
    def test_create_action(self):
        """Test generic action creator."""
        action = create_action(ActionType.RESET, {'data': 'test'})
        
        assert action.type == ActionType.RESET
        assert action.payload == {'data': 'test'}
    
    def test_init_store_action(self):
        """Test init store action creator."""
        action = init_store()
        
        assert action.type == ActionType.INIT
        assert action.payload is None
    
    def test_reset_store_action(self):
        """Test reset store action creator."""
        action = reset_store()
        
        assert action.type == ActionType.RESET
        assert action.payload is None
    
    def test_hydrate_store_action(self):
        """Test hydrate store action creator."""
        state = {'document': {'id': 'doc1'}, 'ui': {'page': 1}}
        action = hydrate_store(state)
        
        assert action.type == ActionType.HYDRATE
        assert action.payload == state
    
    def test_document_actions(self):
        """Test document action creators."""
        # Set document
        action = set_document('doc123', '/path/to/doc.pdf', {'title': 'Test'})
        
        assert action.type == ActionType.SET_DOCUMENT
        assert isinstance(action.payload, DocumentPayload)
        assert action.payload.document_id == 'doc123'
        assert action.payload.document_path == '/path/to/doc.pdf'
        assert action.payload.document_data == {'title': 'Test'}
    
    def test_element_actions(self):
        """Test element action creators."""
        # Add element
        add_action = add_element('elem1', 'text', {'content': 'Hello'}, 1)
        
        assert add_action.type == ActionType.ADD_ELEMENT
        assert isinstance(add_action.payload, ElementPayload)
        assert add_action.payload.element_id == 'elem1'
        assert add_action.payload.element_type == 'text'
        assert add_action.payload.element_data == {'content': 'Hello'}
        assert add_action.payload.page_number == 1
        
        # Update element
        update_action = update_element('elem1', {'content': 'Updated'})
        
        assert update_action.type == ActionType.UPDATE_ELEMENT
        assert update_action.payload.element_id == 'elem1'
        assert update_action.payload.element_data == {'content': 'Updated'}
        
        # Delete element
        delete_action = delete_element('elem1')
        
        assert delete_action.type == ActionType.DELETE_ELEMENT
        assert delete_action.payload.element_id == 'elem1'
    
    def test_async_actions(self):
        """Test async action creators."""
        # Async start
        start_action = async_start('req123', 'loadDocument', {'id': 'doc1'})
        
        assert start_action.type == ActionType.ASYNC_START
        assert isinstance(start_action.payload, AsyncPayload)
        assert start_action.payload.request_id == 'req123'
        assert start_action.payload.operation == 'loadDocument'
        assert start_action.payload.data == {'id': 'doc1'}
        
        # Async success
        success_action = async_success('req123', 'loadDocument', {'document': 'data'})
        
        assert success_action.type == ActionType.ASYNC_SUCCESS
        assert success_action.payload.request_id == 'req123'
        assert success_action.payload.data == {'document': 'data'}
        
        # Async failure
        error = Exception('Network error')
        failure_action = async_failure('req123', 'loadDocument', error)
        
        assert failure_action.type == ActionType.ASYNC_FAILURE
        assert failure_action.payload.error == error
        assert failure_action.error is True
        assert failure_action.meta['error_message'] == 'Network error'


class TestActionValidation:
    """Test action validation."""
    
    def test_valid_action(self):
        """Test validating a valid action."""
        action = create_action(ActionType.INIT)
        assert ActionValidator.validate(action) is True
    
    def test_invalid_action_no_type(self):
        """Test action without type."""
        action = Action(type=None)
        
        with pytest.raises(ValueError, match="Action must have a type"):
            ActionValidator.validate(action)
    
    def test_invalid_action_bad_timestamp(self):
        """Test action with invalid timestamp."""
        action = create_action(ActionType.INIT)
        action.timestamp = -1
        
        with pytest.raises(ValueError, match="valid timestamp"):
            ActionValidator.validate(action)
    
    def test_invalid_action_no_id(self):
        """Test action without ID."""
        action = create_action(ActionType.INIT)
        action.id = ""
        
        with pytest.raises(ValueError, match="Action must have an ID"):
            ActionValidator.validate(action)
    
    def test_is_async_action(self):
        """Test checking if action is async."""
        async_action = async_start('req1', 'test')
        normal_action = set_document('doc1')
        
        assert ActionValidator.is_async_action(async_action) is True
        assert ActionValidator.is_async_action(normal_action) is False
    
    def test_is_system_action(self):
        """Test checking if action is system action."""
        system_action = init_store()
        normal_action = set_document('doc1')
        
        assert ActionValidator.is_system_action(system_action) is True
        assert ActionValidator.is_system_action(normal_action) is False


class TestActionPayloads:
    """Test action payload dataclasses."""
    
    def test_document_payload(self):
        """Test DocumentPayload structure."""
        payload = DocumentPayload(
            document_id='doc123',
            document_path='/path/to/doc.pdf',
            document_data={'pages': 10},
            metadata={'author': 'Test'}
        )
        
        assert payload.document_id == 'doc123'
        assert payload.document_path == '/path/to/doc.pdf'
        assert payload.document_data == {'pages': 10}
        assert payload.metadata == {'author': 'Test'}
    
    def test_element_payload(self):
        """Test ElementPayload structure."""
        payload = ElementPayload(
            element_id='elem123',
            element_type='text',
            element_data={'content': 'Hello'},
            page_number=5
        )
        
        assert payload.element_id == 'elem123'
        assert payload.element_type == 'text'
        assert payload.element_data == {'content': 'Hello'}
        assert payload.page_number == 5
    
    def test_async_payload(self):
        """Test AsyncPayload structure."""
        error = Exception('Test error')
        payload = AsyncPayload(
            request_id='req123',
            operation='testOp',
            data={'result': 'success'},
            error=error
        )
        
        assert payload.request_id == 'req123'
        assert payload.operation == 'testOp'
        assert payload.data == {'result': 'success'}
        assert payload.error == error


class TestActionTimestamps:
    """Test action timestamp handling."""
    
    def test_action_timestamp_auto_generated(self):
        """Test timestamp is automatically generated."""
        before = time.time()
        action = create_action(ActionType.INIT)
        after = time.time()
        
        assert before <= action.timestamp <= after
    
    def test_action_timestamp_format(self):
        """Test timestamp is proper format."""
        action = create_action(ActionType.INIT)
        
        # Should be able to convert to datetime
        dt = datetime.fromtimestamp(action.timestamp)
        assert isinstance(dt, datetime)
    
    def test_multiple_actions_have_different_ids(self):
        """Test each action has unique ID."""
        actions = [create_action(ActionType.INIT) for _ in range(100)]
        ids = [action.id for action in actions]
        
        # All IDs should be unique
        assert len(set(ids)) == len(ids)