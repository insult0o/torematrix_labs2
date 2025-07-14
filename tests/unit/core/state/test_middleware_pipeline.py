"""
Tests for middleware pipeline functionality.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from src.torematrix.core.state.middleware.pipeline import (
    MiddlewarePipeline, 
    logging_middleware, 
    timing_middleware
)
from src.torematrix.core.state.middleware.async_middleware import AsyncMiddleware
from src.torematrix.core.state.middleware.error_handler import (
    ErrorHandlerMiddleware,
    retry_recovery_strategy,
    fallback_recovery_strategy
)
from src.torematrix.core.state.middleware.validator import (
    ValidatorMiddleware,
    ValidationRule,
    TypeValidator,
    RequiredFieldValidator
)


class TestMiddlewarePipeline:
    """Test the middleware pipeline implementation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.pipeline = MiddlewarePipeline()
        self.mock_store = Mock()
        self.mock_store.get_state.return_value = {'test': 'state'}
        self.mock_store._dispatch = Mock(return_value='dispatched')
    
    def test_pipeline_creation(self):
        """Test middleware pipeline creation."""
        assert len(self.pipeline) == 0
        assert not self.pipeline
        
        # Add middleware
        self.pipeline.use(logging_middleware)
        assert len(self.pipeline) == 1
        assert bool(self.pipeline)
    
    def test_middleware_composition(self):
        """Test middleware composition."""
        # Create test middleware
        def test_middleware1(store):
            def middleware(next_dispatch):
                def dispatch(action):
                    action.middleware1 = True
                    return next_dispatch(action)
                return dispatch
            return middleware
        
        def test_middleware2(store):
            def middleware(next_dispatch):
                def dispatch(action):
                    action.middleware2 = True
                    return next_dispatch(action)
                return dispatch
            return middleware
        
        # Add middleware
        self.pipeline.use(test_middleware1).use(test_middleware2)
        
        # Compose pipeline
        composed = self.pipeline.compose()
        dispatch_func = composed(self.mock_store)
        
        # Test dispatch
        action = Mock()
        action.type = 'TEST_ACTION'
        result = dispatch_func(action)
        
        assert hasattr(action, 'middleware1')
        assert hasattr(action, 'middleware2')
        assert result == 'dispatched'
    
    def test_middleware_order(self):
        """Test middleware execution order."""
        order = []
        
        def middleware1(store):
            def middleware(next_dispatch):
                def dispatch(action):
                    order.append('middleware1_start')
                    result = next_dispatch(action)
                    order.append('middleware1_end')
                    return result
                return dispatch
            return middleware
        
        def middleware2(store):
            def middleware(next_dispatch):
                def dispatch(action):
                    order.append('middleware2_start')
                    result = next_dispatch(action)
                    order.append('middleware2_end')
                    return result
                return dispatch
            return middleware
        
        # Add middleware in order
        self.pipeline.use(middleware1).use(middleware2)
        
        # Execute
        composed = self.pipeline.compose()
        dispatch_func = composed(self.mock_store)
        
        action = Mock()
        action.type = 'TEST_ACTION'
        dispatch_func(action)
        
        # Check order (middleware executes in order, but completion is reverse)
        expected_order = [
            'middleware1_start',
            'middleware2_start',
            'middleware2_end',
            'middleware1_end'
        ]
        assert order == expected_order
    
    def test_middleware_error_handling(self):
        """Test middleware error handling."""
        def error_middleware(store):
            def middleware(next_dispatch):
                def dispatch(action):
                    if action.type == 'ERROR_ACTION':
                        raise ValueError("Test error")
                    return next_dispatch(action)
                return dispatch
            return middleware
        
        self.pipeline.use(error_middleware)
        composed = self.pipeline.compose()
        dispatch_func = composed(self.mock_store)
        
        # Normal action should work
        normal_action = Mock()
        normal_action.type = 'NORMAL_ACTION'
        result = dispatch_func(normal_action)
        assert result == 'dispatched'
        
        # Error action should raise
        error_action = Mock()
        error_action.type = 'ERROR_ACTION'
        with pytest.raises(ValueError, match="Test error"):
            dispatch_func(error_action)
    
    def test_middleware_metrics(self):
        """Test middleware metrics collection."""
        # Add some middleware
        self.pipeline.use(logging_middleware).use(timing_middleware)
        
        composed = self.pipeline.compose()
        dispatch_func = composed(self.mock_store)
        
        # Execute some actions
        for i in range(5):
            action = Mock()
            action.type = f'ACTION_{i}'
            dispatch_func(action)
        
        metrics = self.pipeline.get_metrics()
        assert metrics['total_actions'] == 5
        assert metrics['middleware_time'] > 0
        assert metrics['avg_time_per_action'] > 0
        assert metrics['errors'] == 0
    
    def test_pipeline_clear(self):
        """Test pipeline clearing."""
        self.pipeline.use(logging_middleware).use(timing_middleware)
        assert len(self.pipeline) == 2
        
        self.pipeline.clear()
        assert len(self.pipeline) == 0
        assert not self.pipeline


class TestAsyncMiddleware:
    """Test async middleware functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_store = Mock()
        self.mock_store.get_state.return_value = {'test': 'state'}
    
    @pytest.mark.asyncio
    async def test_async_middleware_creation(self):
        """Test async middleware creation."""
        async def async_handler(store, action, next_dispatch):
            await asyncio.sleep(0.001)
            return next_dispatch(action)
        
        middleware = AsyncMiddleware(async_handler)
        assert middleware.async_handler == async_handler
    
    @pytest.mark.asyncio
    async def test_async_middleware_execution(self):
        """Test async middleware execution."""
        executed = []
        
        async def async_handler(store, action, next_dispatch):
            executed.append('async_start')
            await asyncio.sleep(0.001)
            result = next_dispatch(action)
            executed.append('async_end')
            return result
        
        middleware = AsyncMiddleware(async_handler)
        middleware_func = middleware(self.mock_store)
        
        def mock_next_dispatch(action):
            executed.append('dispatch')
            return 'result'
        
        dispatch_func = middleware_func(mock_next_dispatch)
        
        action = Mock()
        action.type = 'ASYNC_ACTION'
        action.id = 'test_id'
        
        result = await dispatch_func(action)
        
        assert executed == ['async_start', 'dispatch', 'async_end']
        assert result == 'result'
    
    @pytest.mark.asyncio
    async def test_async_middleware_error_handling(self):
        """Test async middleware error handling."""
        async def failing_handler(store, action, next_dispatch):
            await asyncio.sleep(0.001)
            raise ValueError("Async error")
        
        middleware = AsyncMiddleware(failing_handler)
        middleware_func = middleware(self.mock_store)
        dispatch_func = middleware_func(Mock(return_value='result'))
        
        action = Mock()
        action.type = 'FAILING_ACTION'
        action.id = 'test_id'
        
        with pytest.raises(ValueError, match="Async error"):
            await dispatch_func(action)


class TestErrorHandlerMiddleware:
    """Test error handler middleware."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.error_handler = ErrorHandlerMiddleware()
        self.mock_store = Mock()
        self.mock_store.get_state.return_value = {'test': 'state'}
    
    def test_error_detection_and_logging(self):
        """Test error detection and logging."""
        middleware_func = self.error_handler(self.mock_store)
        
        def failing_dispatch(action):
            raise ValueError("Test error")
        
        dispatch_func = middleware_func(failing_dispatch)
        
        action = Mock()
        action.type = 'FAILING_ACTION'
        
        with pytest.raises(ValueError):
            dispatch_func(action)
        
        metrics = self.error_handler.get_error_metrics()
        assert metrics['total_errors'] == 1
        assert 'ValueError' in metrics['error_counts']
        assert 'FAILING_ACTION' in metrics['error_counts']
    
    def test_recovery_strategy(self):
        """Test error recovery strategies."""
        # Add retry recovery strategy
        retry_strategy = retry_recovery_strategy(max_retries=2)
        self.error_handler.add_recovery_strategy('ValueError', retry_strategy)
        
        middleware_func = self.error_handler(self.mock_store)
        
        call_count = 0
        
        def sometimes_failing_dispatch(action):
            nonlocal call_count
            call_count += 1
            if call_count < 3:  # Fail first 2 times
                raise ValueError("Temporary error")
            return "success"
        
        dispatch_func = middleware_func(sometimes_failing_dispatch)
        
        action = Mock()
        action.type = 'RETRY_ACTION'
        
        # Mock store dispatch for retries
        self.mock_store.dispatch = Mock(side_effect=lambda a: sometimes_failing_dispatch(a))
        
        result = dispatch_func(action)
        assert result == "success"
        assert call_count == 3  # Original + 2 retries
    
    def test_fallback_recovery(self):
        """Test fallback recovery strategy."""
        fallback_strategy = fallback_recovery_strategy("fallback_value")
        self.error_handler.add_recovery_strategy('ValueError', fallback_strategy)
        
        middleware_func = self.error_handler(self.mock_store)
        
        def failing_dispatch(action):
            raise ValueError("Always fails")
        
        dispatch_func = middleware_func(failing_dispatch)
        
        action = Mock()
        action.type = 'FALLBACK_ACTION'
        
        result = dispatch_func(action)
        assert result == "fallback_value"
        
        metrics = self.error_handler.get_error_metrics()
        assert metrics['recovered_errors'] == 1
        assert metrics['recovery_rate'] == 1.0


class TestValidatorMiddleware:
    """Test validator middleware."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ValidatorMiddleware()
        self.mock_store = Mock()
        self.mock_store.get_state.return_value = {'valid': 'state'}
    
    def test_action_validation(self):
        """Test action validation."""
        # Add validation rule
        type_rule = ValidationRule(
            name="type_check",
            validator=TypeValidator(object),
            required=True,
            error_message="Action must be an object"
        )
        
        self.validator.add_action_validator('TEST_ACTION', type_rule)
        
        middleware_func = self.validator(self.mock_store)
        
        def mock_dispatch(action):
            return "dispatched"
        
        dispatch_func = middleware_func(mock_dispatch)
        
        # Valid action
        valid_action = Mock()
        valid_action.type = 'TEST_ACTION'
        result = dispatch_func(valid_action)
        assert result == "dispatched"
        
        # Invalid action (None)
        with pytest.raises(Exception):  # ValidationError or similar
            dispatch_func(None)
    
    def test_required_field_validation(self):
        """Test required field validation."""
        required_field_rule = ValidationRule(
            name="payload_required",
            validator=RequiredFieldValidator('payload'),
            required=True,
            error_message="Action must have payload"
        )
        
        self.validator.add_action_validator('PAYLOAD_ACTION', required_field_rule)
        
        middleware_func = self.validator(self.mock_store)
        dispatch_func = middleware_func(Mock(return_value="dispatched"))
        
        # Action with payload
        action_with_payload = Mock()
        action_with_payload.type = 'PAYLOAD_ACTION'
        action_with_payload.payload = {'data': 'test'}
        
        result = dispatch_func(action_with_payload)
        assert result == "dispatched"
        
        # Action without payload
        action_without_payload = Mock()
        action_without_payload.type = 'PAYLOAD_ACTION'
        del action_without_payload.payload
        
        from src.torematrix.core.state.middleware.validator import ValidationError
        with pytest.raises(ValidationError):
            dispatch_func(action_without_payload)
    
    def test_validation_stats(self):
        """Test validation statistics."""
        middleware_func = self.validator(self.mock_store)
        dispatch_func = middleware_func(Mock(return_value="dispatched"))
        
        # Execute valid actions
        for i in range(3):
            action = Mock()
            action.type = f'ACTION_{i}'
            dispatch_func(action)
        
        stats = self.validator.get_validation_stats()
        assert stats['total_validations'] == 3
        assert stats['failed_validations'] == 0
        assert stats['success_rate'] == 1.0


@pytest.fixture
def integration_pipeline():
    """Create an integrated pipeline with all middleware types."""
    pipeline = MiddlewarePipeline()
    
    # Add logging middleware
    pipeline.use(logging_middleware)
    
    # Add error handling
    error_handler = ErrorHandlerMiddleware()
    pipeline.use(error_handler)
    
    # Add validation
    validator = ValidatorMiddleware()
    pipeline.use(validator)
    
    # Add timing
    pipeline.use(timing_middleware)
    
    return pipeline


class TestIntegratedPipeline:
    """Test integrated middleware pipeline."""
    
    def test_full_pipeline_integration(self, integration_pipeline):
        """Test full pipeline with all middleware."""
        mock_store = Mock()
        mock_store.get_state.return_value = {'integrated': 'state'}
        mock_store._dispatch = Mock(return_value='final_result')
        
        composed = integration_pipeline.compose()
        dispatch_func = composed(mock_store)
        
        action = Mock()
        action.type = 'INTEGRATED_ACTION'
        action.payload = {'test': 'data'}
        
        result = dispatch_func(action)
        assert result == 'final_result'
        
        # Check metrics
        metrics = integration_pipeline.get_metrics()
        assert metrics['total_actions'] == 1
        assert metrics['errors'] == 0
    
    def test_pipeline_performance(self, integration_pipeline):
        """Test pipeline performance with multiple actions."""
        mock_store = Mock()
        mock_store.get_state.return_value = {'performance': 'test'}
        mock_store._dispatch = Mock(return_value='result')
        
        composed = integration_pipeline.compose()
        dispatch_func = composed(mock_store)
        
        # Execute many actions
        start_time = time.time()
        for i in range(100):
            action = Mock()
            action.type = f'PERF_ACTION_{i}'
            dispatch_func(action)
        
        duration = time.time() - start_time
        
        metrics = integration_pipeline.get_metrics()
        assert metrics['total_actions'] == 100
        assert metrics['avg_time_per_action'] < 0.01  # Should be fast
        assert duration < 1.0  # Should complete quickly


if __name__ == '__main__':
    pytest.main([__file__])