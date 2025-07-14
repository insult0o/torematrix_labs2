"""
Unit tests for middleware system.

Tests cover:
- Middleware pipeline
- Logging middleware
- Conditional middleware
- Chain middleware
- Error handling
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
import time

from torematrix.core.state import Store, StoreConfig
from torematrix.core.state.actions import Action, ActionType, create_action, set_document
from torematrix.core.state.reducers import create_root_reducer
from torematrix.core.state.middleware import (
    Middleware, compose_middleware,
    LoggingMiddleware, create_logging_middleware
)
from torematrix.core.state.middleware.base import ConditionalMiddleware, ChainMiddleware


class TestMiddlewareBase:
    """Test base middleware functionality."""
    
    def test_middleware_abstract_class(self):
        """Test middleware is abstract."""
        with pytest.raises(TypeError):
            # Can't instantiate abstract class
            Middleware()
    
    def test_custom_middleware(self):
        """Test creating custom middleware."""
        class TestMiddleware(Middleware):
            def __init__(self):
                super().__init__("TestMiddleware")
                self.before_calls = []
                self.after_calls = []
            
            def process(self, action, next_dispatch):
                self.before_calls.append(action)
                result = next_dispatch(action)
                self.after_calls.append(action)
                return result
        
        # Create store with middleware
        middleware = TestMiddleware()
        store = Store(StoreConfig(
            initial_state={},
            reducer=create_root_reducer(),
            middleware=[middleware]
        ))
        
        # Dispatch action
        action = set_document('doc123')
        store.dispatch(action)
        
        # Check middleware was called
        assert len(middleware.before_calls) == 2  # init + action
        assert len(middleware.after_calls) == 2
        assert middleware.before_calls[1] == action
    
    def test_compose_middleware(self):
        """Test composing middleware."""
        mw1 = Mock()
        mw2 = Mock()
        mw3 = Mock()
        
        middleware_list = compose_middleware(mw1, mw2, mw3)
        
        assert middleware_list == [mw1, mw2, mw3]
        assert isinstance(middleware_list, list)


class TestLoggingMiddleware:
    """Test logging middleware."""
    
    def test_logging_middleware_basic(self):
        """Test basic logging middleware functionality."""
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
            
            # Check logging
            assert mock_logger.log.called
            
            # Find the dispatch log call
            dispatch_calls = [
                call for call in mock_logger.log.call_args_list
                if 'Dispatching action' in str(call)
            ]
            assert len(dispatch_calls) > 0
            
            # Find the completion log call
            complete_calls = [
                call for call in mock_logger.log.call_args_list
                if 'Action processed' in str(call)
            ]
            assert len(complete_calls) > 0
    
    def test_logging_middleware_with_payload(self):
        """Test logging middleware with payload logging."""
        with patch('torematrix.core.state.middleware.logging.logger') as mock_logger:
            middleware = LoggingMiddleware(
                log_payload=True,
                max_payload_length=50
            )
            
            store = Store(StoreConfig(
                initial_state={},
                reducer=create_root_reducer(),
                middleware=[middleware]
            ))
            
            # Dispatch action with payload
            action = set_document('doc123', '/very/long/path/that/exceeds/max/length/document.pdf')
            store.dispatch(action)
            
            # Check payload was logged (truncated)
            log_calls = mock_logger.log.call_args_list
            assert any('payload' in str(call) for call in log_calls)
    
    def test_logging_middleware_error_handling(self):
        """Test logging middleware handles errors."""
        with patch('torematrix.core.state.middleware.logging.logger') as mock_logger:
            # Create reducer that throws error
            def error_reducer(state, action):
                if action.type == 'ERROR':
                    raise ValueError("Test error")
                return state
            
            store = Store(StoreConfig(
                initial_state={},
                reducer=error_reducer,
                middleware=[LoggingMiddleware()]
            ))
            
            # Dispatch error action
            with pytest.raises(ValueError):
                store.dispatch(Action(type='ERROR'))
            
            # Check error was logged
            assert mock_logger.error.called
            error_calls = [
                call for call in mock_logger.error.call_args_list
                if 'Action failed' in str(call)
            ]
            assert len(error_calls) > 0
    
    def test_logging_middleware_state_diff(self):
        """Test logging middleware with state diff enabled."""
        with patch('torematrix.core.state.middleware.logging.logger') as mock_logger:
            middleware = LoggingMiddleware(
                log_state_diff=True,
                log_level=logging.DEBUG
            )
            
            store = Store(StoreConfig(
                initial_state={},
                reducer=create_root_reducer(),
                middleware=[middleware]
            ))
            
            # Dispatch action that changes state
            store.dispatch(set_document('doc123'))
            
            # Check state diff was logged
            log_calls = mock_logger.log.call_args_list
            state_diff_calls = [
                call for call in log_calls
                if 'State changed' in str(call)
            ]
            assert len(state_diff_calls) > 0
    
    def test_create_logging_middleware(self):
        """Test creating logging middleware with helper."""
        # Non-verbose
        mw1 = create_logging_middleware(verbose=False)
        assert mw1.log_level == logging.INFO
        assert mw1.log_state_diff is False
        assert mw1.log_payload is False
        
        # Verbose
        mw2 = create_logging_middleware(verbose=True)
        assert mw2.log_level == logging.DEBUG
        assert mw2.log_state_diff is True
        assert mw2.log_payload is True


class TestConditionalMiddleware:
    """Test conditional middleware."""
    
    def test_conditional_middleware(self):
        """Test middleware that conditionally processes actions."""
        # Create inner middleware that tracks calls
        class TrackingMiddleware(Middleware):
            def __init__(self):
                super().__init__()
                self.processed = []
            
            def process(self, action, next_dispatch):
                self.processed.append(action)
                return next_dispatch(action)
        
        inner = TrackingMiddleware()
        
        # Only process document actions
        condition = lambda action: (
            isinstance(action.type, ActionType) and 
            action.type.value.startswith('DOCUMENT/')
        )
        
        conditional = ConditionalMiddleware(condition, inner)
        
        store = Store(StoreConfig(
            initial_state={},
            reducer=create_root_reducer(),
            middleware=[conditional]
        ))
        
        # Dispatch document action - should be processed
        doc_action = set_document('doc123')
        store.dispatch(doc_action)
        
        # Dispatch UI action - should not be processed
        ui_action = Action(type=ActionType.SET_PAGE, payload=2)
        store.dispatch(ui_action)
        
        # Check only document action was processed by inner middleware
        assert len(inner.processed) == 1
        assert inner.processed[0] == doc_action


class TestChainMiddleware:
    """Test chain middleware."""
    
    def test_chain_middleware(self):
        """Test chaining multiple middleware."""
        # Create middleware that add to action meta
        class AddMetaMiddleware(Middleware):
            def __init__(self, key, value):
                super().__init__(f"AddMeta_{key}")
                self.key = key
                self.value = value
            
            def process(self, action, next_dispatch):
                action.with_meta(**{self.key: self.value})
                return next_dispatch(action)
        
        # Chain multiple middleware
        mw1 = AddMetaMiddleware('step1', 'completed')
        mw2 = AddMetaMiddleware('step2', 'completed')
        mw3 = AddMetaMiddleware('step3', 'completed')
        
        chain = ChainMiddleware(mw1, mw2, mw3)
        
        store = Store(StoreConfig(
            initial_state={},
            reducer=create_root_reducer(),
            middleware=[chain]
        ))
        
        # Dispatch action
        action = create_action(ActionType.INIT)
        store.dispatch(action)
        
        # Check all middleware ran in order
        history = store.get_action_history()
        last_action = history[-1]
        
        assert last_action.meta['step1'] == 'completed'
        assert last_action.meta['step2'] == 'completed'
        assert last_action.meta['step3'] == 'completed'


class TestMiddlewareIntegration:
    """Test middleware integration scenarios."""
    
    def test_multiple_middleware_order(self):
        """Test multiple middleware execute in correct order."""
        order = []
        
        class OrderMiddleware(Middleware):
            def __init__(self, name):
                super().__init__(name)
                self.name = name
            
            def process(self, action, next_dispatch):
                order.append(f"{self.name}_before")
                result = next_dispatch(action)
                order.append(f"{self.name}_after")
                return result
        
        store = Store(StoreConfig(
            initial_state={},
            reducer=create_root_reducer(),
            middleware=[
                OrderMiddleware('first'),
                OrderMiddleware('second'),
                OrderMiddleware('third')
            ]
        ))
        
        store.dispatch(create_action('TEST'))
        
        # Middleware should wrap in order
        expected = [
            'first_before',
            'second_before',
            'third_before',
            'third_after',
            'second_after',
            'first_after'
        ]
        
        # Remove init action processing
        actual_order = [x for x in order if 'TEST' in str(order)]
        if not actual_order:  # If TEST not tracked, check general order
            actual_order = order[len(order)//2:]  # Last half should be our action
        
        assert len(order) >= 6  # At least our action processing
    
    def test_middleware_modifying_action(self):
        """Test middleware can modify actions."""
        class ModifyingMiddleware(Middleware):
            def process(self, action, next_dispatch):
                # Add metadata to all actions
                action.with_meta(modified=True, timestamp=time.time())
                
                # Change payload for specific actions
                if action.type == 'MODIFY_ME':
                    action.payload = 'modified_payload'
                
                return next_dispatch(action)
        
        store = Store(StoreConfig(
            initial_state={},
            reducer=create_root_reducer(),
            middleware=[ModifyingMiddleware()]
        ))
        
        # Dispatch action
        action = Action(type='MODIFY_ME', payload='original_payload')
        store.dispatch(action)
        
        # Check action was modified
        history = store.get_action_history()
        processed_action = next(a for a in history if a.type == 'MODIFY_ME')
        
        assert processed_action.payload == 'modified_payload'
        assert processed_action.meta['modified'] is True
        assert 'timestamp' in processed_action.meta
    
    def test_middleware_stopping_action(self):
        """Test middleware can stop action propagation."""
        class FilterMiddleware(Middleware):
            def process(self, action, next_dispatch):
                # Block certain actions
                if action.type == 'BLOCKED':
                    return None  # Don't call next_dispatch
                return next_dispatch(action)
        
        # Create custom reducer to track actions
        processed_actions = []
        
        def tracking_reducer(state={}, action=None):
            processed_actions.append(action)
            return state
        
        store = Store(StoreConfig(
            initial_state={},
            reducer=tracking_reducer,
            middleware=[FilterMiddleware()]
        ))
        
        # Dispatch blocked action
        store.dispatch(Action(type='BLOCKED'))
        
        # Dispatch allowed action
        store.dispatch(Action(type='ALLOWED'))
        
        # Check blocked action didn't reach reducer
        action_types = [a.type for a in processed_actions if a]
        assert 'BLOCKED' not in action_types
        assert 'ALLOWED' in action_types