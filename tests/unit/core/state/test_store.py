"""
Unit tests for the Store class.

Tests cover:
- State initialization
- Action dispatching
- Subscription mechanism
- Thread safety
- State immutability
"""

import pytest
import threading
import time
from unittest.mock import Mock, patch

from torematrix.core.state import (
    Store, StoreConfig, State,
    Action, ActionType, create_action, init_store,
    set_document, add_element, update_element,
    create_root_reducer
)
from torematrix.core.state.middleware import LoggingMiddleware


class TestStore:
    """Test cases for Store class."""
    
    def test_store_initialization(self):
        """Test store initializes with correct state."""
        initial_state = {
            'document': {'current_id': None},
            'elements': {'byId': {}, 'allIds': []},
            'ui': {'current_page': 1}
        }
        
        config = StoreConfig(
            initial_state=initial_state,
            reducer=create_root_reducer()
        )
        
        store = Store(config)
        state = store.get_state()
        
        # Check initial state structure
        assert 'document' in state
        assert 'elements' in state
        assert 'ui' in state
        assert 'async' in state  # Added by root reducer
        
        # Verify initialization action was dispatched
        history = store.get_action_history()
        assert len(history) == 1
        assert history[0].type == ActionType.INIT
    
    def test_dispatch_action(self):
        """Test action dispatching updates state."""
        store = Store(StoreConfig(
            initial_state={},
            reducer=create_root_reducer()
        ))
        
        # Dispatch document action
        action = set_document('doc123', '/path/to/doc.pdf')
        result = store.dispatch(action)
        
        # Check action was processed
        assert result == action
        
        # Check state was updated
        state = store.get_state()
        assert state['document']['current_id'] == 'doc123'
        assert state['document']['document_path'] == '/path/to/doc.pdf'
    
    def test_subscribe_unsubscribe(self):
        """Test subscription mechanism."""
        store = Store(StoreConfig(
            initial_state={},
            reducer=create_root_reducer()
        ))
        
        # Track calls
        subscriber1_calls = []
        subscriber2_calls = []
        
        def subscriber1(state):
            subscriber1_calls.append(state)
        
        def subscriber2(state):
            subscriber2_calls.append(state)
        
        # Subscribe
        unsubscribe1 = store.subscribe(subscriber1)
        unsubscribe2 = store.subscribe(subscriber2)
        
        # Dispatch action
        store.dispatch(set_document('doc123'))
        
        # Both subscribers should be called
        assert len(subscriber1_calls) == 1
        assert len(subscriber2_calls) == 1
        
        # Unsubscribe first
        unsubscribe1()
        
        # Dispatch another action
        store.dispatch(update_element('elem1', {'text': 'updated'}))
        
        # Only subscriber2 should be called
        assert len(subscriber1_calls) == 1  # No new calls
        assert len(subscriber2_calls) == 2
        
        # Unsubscribe second
        unsubscribe2()
        
        # No subscribers should be called
        store.dispatch(create_action(ActionType.RESET))
        assert len(subscriber1_calls) == 1
        assert len(subscriber2_calls) == 2
    
    def test_state_immutability(self):
        """Test that state updates are immutable."""
        initial_state = {
            'document': {'current_id': None},
            'elements': {'byId': {}, 'allIds': []}
        }
        
        store = Store(StoreConfig(
            initial_state=initial_state,
            reducer=create_root_reducer()
        ))
        
        # Get initial state
        state1 = store.get_state()
        
        # Dispatch action
        store.dispatch(set_document('doc123'))
        
        # Get new state
        state2 = store.get_state()
        
        # States should be different objects
        assert state1 is not state2
        assert state1['document'] is not state2['document']
        
        # Original state should be unchanged
        assert initial_state['document']['current_id'] is None
        assert state1['document']['current_id'] is None
        assert state2['document']['current_id'] == 'doc123'
    
    def test_thread_safety(self):
        """Test thread-safe operations."""
        store = Store(StoreConfig(
            initial_state={},
            reducer=create_root_reducer()
        ))
        
        results = []
        errors = []
        
        def dispatch_actions():
            try:
                for i in range(100):
                    store.dispatch(add_element(
                        f'elem{i}',
                        'text',
                        {'content': f'Element {i}'}
                    ))
            except Exception as e:
                errors.append(e)
        
        def subscribe_and_read():
            try:
                states = []
                
                def subscriber(state):
                    states.append(len(state['elements']['allIds']))
                
                unsubscribe = store.subscribe(subscriber)
                time.sleep(0.1)  # Let some actions process
                unsubscribe()
                
                results.append(states)
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        
        # Dispatch threads
        for _ in range(3):
            t = threading.Thread(target=dispatch_actions)
            threads.append(t)
            t.start()
        
        # Subscribe threads
        for _ in range(2):
            t = threading.Thread(target=subscribe_and_read)
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join()
        
        # Check no errors occurred
        assert len(errors) == 0
        
        # Check final state has all elements
        state = store.get_state()
        assert len(state['elements']['allIds']) == 300  # 3 threads × 100 elements
    
    def test_middleware_integration(self):
        """Test middleware is properly integrated."""
        # Create mock middleware
        mock_middleware = Mock()
        mock_middleware.return_value = lambda next_dispatch: lambda action: next_dispatch(action)
        
        # Create store with middleware
        store = Store(StoreConfig(
            initial_state={},
            reducer=create_root_reducer(),
            middleware=[mock_middleware]
        ))
        
        # Middleware should be called during initialization
        mock_middleware.assert_called_once()
        
        # Dispatch action
        store.dispatch(set_document('doc123'))
        
        # Check action was processed
        state = store.get_state()
        assert state['document']['current_id'] == 'doc123'
    
    def test_logging_middleware(self):
        """Test logging middleware works correctly."""
        with patch('torematrix.core.state.middleware.logging.logger') as mock_logger:
            # Create store with logging middleware
            store = Store(StoreConfig(
                initial_state={},
                reducer=create_root_reducer(),
                middleware=[LoggingMiddleware()]
            ))
            
            # Dispatch action
            action = set_document('doc123')
            store.dispatch(action)
            
            # Check logging calls
            assert mock_logger.log.called
            # Should log dispatch and completion
            assert mock_logger.log.call_count >= 2
    
    def test_get_state_returns_copy(self):
        """Test get_state returns a deep copy."""
        store = Store(StoreConfig(
            initial_state={},
            reducer=create_root_reducer()
        ))
        
        # Add element
        store.dispatch(add_element('elem1', 'text', {'content': 'test'}))
        
        # Get state
        state1 = store.get_state()
        state2 = store.get_state()
        
        # Should be different objects
        assert state1 is not state2
        assert state1['elements'] is not state2['elements']
        assert state1['elements']['byId'] is not state2['elements']['byId']
        
        # Modifying returned state shouldn't affect store
        state1['elements']['byId']['elem1']['content'] = 'modified'
        
        state3 = store.get_state()
        assert state3['elements']['byId']['elem1']['content'] == 'test'
    
    def test_action_validation(self):
        """Test action validation."""
        store = Store(StoreConfig(
            initial_state={},
            reducer=create_root_reducer()
        ))
        
        # Invalid action - no type
        with pytest.raises(ValueError, match="Action must have a type"):
            store.dispatch(Action(type=None))
        
        # Invalid action - bad timestamp
        action = create_action(ActionType.RESET)
        action.timestamp = -1
        with pytest.raises(ValueError, match="valid timestamp"):
            store.dispatch(action)
    
    def test_replace_reducer(self):
        """Test replacing the reducer."""
        store = Store(StoreConfig(
            initial_state={},
            reducer=create_root_reducer()
        ))
        
        # Custom reducer that always returns fixed state
        def custom_reducer(state, action):
            return {'custom': True}
        
        # Replace reducer
        store.replace_reducer(custom_reducer)
        
        # Dispatch action
        store.dispatch(create_action('TEST'))
        
        # State should be from custom reducer
        state = store.get_state()
        assert state == {'custom': True}
    
    def test_select_method(self):
        """Test select method for extracting data."""
        store = Store(StoreConfig(
            initial_state={},
            reducer=create_root_reducer()
        ))
        
        # Add some elements
        store.dispatch(add_element('elem1', 'text', {'content': 'test1'}))
        store.dispatch(add_element('elem2', 'text', {'content': 'test2'}))
        
        # Define selector
        def get_element_count(state):
            return len(state['elements']['allIds'])
        
        # Use select
        count = store.select(get_element_count)
        assert count == 2
    
    def test_action_history(self):
        """Test action history tracking."""
        store = Store(StoreConfig(
            initial_state={},
            reducer=create_root_reducer()
        ))
        
        # Dispatch several actions
        actions = [
            set_document('doc1'),
            add_element('elem1', 'text', {}),
            update_element('elem1', {'content': 'updated'})
        ]
        
        for action in actions:
            store.dispatch(action)
        
        # Get history
        history = store.get_action_history()
        
        # Should have init action + 3 dispatched
        assert len(history) == 4
        assert history[0].type == ActionType.INIT
        assert history[1] == actions[0]
        assert history[2] == actions[1]
        assert history[3] == actions[2]
        
        # Clear history
        store.clear_action_history()
        assert len(store.get_action_history()) == 0
    
    def test_prevent_dispatch_while_dispatching(self):
        """Test preventing recursive dispatch."""
        store = Store(StoreConfig(
            initial_state={},
            reducer=create_root_reducer()
        ))
        
        # Create middleware that tries to dispatch
        def recursive_middleware(store):
            def middleware(next_dispatch):
                def dispatch(action):
                    if action.type != ActionType.INIT:
                        # Try to dispatch another action
                        store.dispatch(create_action('RECURSIVE'))
                    return next_dispatch(action)
                return dispatch
            return middleware
        
        # Add middleware after store creation
        with pytest.raises(RuntimeError, match="Cannot add middleware after dispatching"):
            store.add_middleware(recursive_middleware)
    
    def test_event_bus_integration(self):
        """Test Event Bus integration if configured."""
        mock_event_bus = Mock()
        
        store = Store(StoreConfig(
            initial_state={},
            reducer=create_root_reducer(),
            event_bus=mock_event_bus
        ))
        
        # Dispatch action that changes state
        store.dispatch(set_document('doc123'))
        
        # Event bus should be notified
        mock_event_bus.publish.assert_called()
        
        # Check event details
        call_args = mock_event_bus.publish.call_args[0][0]
        assert call_args.event_type == "STATE_CHANGED"
        assert 'old_state' in call_args.payload
        assert 'new_state' in call_args.payload
        assert 'action' in call_args.payload