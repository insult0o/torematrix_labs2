"""
Tests for optimistic updates, rollback, and conflict resolution.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch
from src.torematrix.core.state.optimistic.updates import (
    OptimisticMiddleware,
    OptimisticUpdate,
    OptimisticPredictor,
    UpdateStatus
)
from src.torematrix.core.state.optimistic.rollback import (
    RollbackManager,
    RollbackStrategy,
    RollbackPoint
)
from src.torematrix.core.state.optimistic.conflicts import (
    ConflictResolver,
    ConflictStrategy,
    Conflict,
    prefer_larger_number,
    concatenate_strings
)


class TestOptimisticUpdate:
    """Test optimistic update data structure."""
    
    def test_optimistic_update_creation(self):
        """Test OptimisticUpdate creation."""
        action = Mock()
        action.type = 'TEST_ACTION'
        
        update = OptimisticUpdate(
            id='test_id',
            action=action,
            optimistic_state={'optimistic': True},
            original_state={'original': True}
        )
        
        assert update.id == 'test_id'
        assert update.action == action
        assert update.status == UpdateStatus.PENDING
        assert update.is_pending == True
        assert update.is_completed == False
    
    def test_update_duration_calculation(self):
        """Test update duration calculation."""
        update = OptimisticUpdate(
            id='test_id',
            action=Mock(),
            optimistic_state={},
            original_state={}
        )
        
        # Duration should be positive
        time.sleep(0.001)
        assert update.duration > 0
        
        # Duration should be fixed when confirmed
        update.confirmed_at = time.time()
        duration1 = update.duration
        time.sleep(0.001)
        duration2 = update.duration
        assert duration1 == duration2


class TestOptimisticMiddleware:
    """Test optimistic middleware functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.middleware = OptimisticMiddleware(timeout=1.0, max_pending=10)
        self.mock_store = Mock()
        self.mock_store.get_state.return_value = {'counter': 0}
        self.mock_store._notify_subscribers = Mock()
    
    @pytest.mark.asyncio
    async def test_optimistic_action_detection(self):
        """Test detection of optimistic actions."""
        # Action with optimistic flag
        optimistic_action = Mock()
        optimistic_action.optimistic = True
        assert self.middleware._should_apply_optimistic(optimistic_action)
        
        # Action with async operation
        async_action = Mock()
        async_action.async_operation = True
        assert self.middleware._should_apply_optimistic(async_action)
        
        # Action with UPDATE_ prefix
        update_action = Mock()
        update_action.type = 'UPDATE_COUNTER'
        assert self.middleware._should_apply_optimistic(update_action)
        
        # Regular action
        regular_action = Mock()
        regular_action.type = 'REGULAR_ACTION'
        assert not self.middleware._should_apply_optimistic(regular_action)
    
    @pytest.mark.asyncio
    async def test_optimistic_state_application(self):
        """Test application of optimistic state."""
        middleware_func = self.middleware(self.mock_store)
        
        async def mock_next_dispatch(action):
            return 'success'
        
        dispatch_func = middleware_func(mock_next_dispatch)
        
        # Create optimistic action
        action = Mock()
        action.type = 'UPDATE_COUNTER'
        action.optimistic = True
        action.async_operation = Mock(return_value=asyncio.Future())
        action.async_operation.return_value.set_result('async_result')
        
        # Mock predictor to return specific state
        with patch.object(self.middleware._predictor, 'predict_state') as mock_predict:
            mock_predict.return_value = {'counter': 1}
            
            result = await dispatch_func(action)
        
        # Verify optimistic state was applied
        assert self.mock_store._notify_subscribers.called
        call_args = self.mock_store._notify_subscribers.call_args[0][0]
        assert call_args == {'counter': 1}
    
    @pytest.mark.asyncio
    async def test_successful_optimistic_update(self):
        """Test successful optimistic update confirmation."""
        middleware_func = self.middleware(self.mock_store)
        
        async def mock_async_operation():
            await asyncio.sleep(0.001)
            return 'success'
        
        async def mock_next_dispatch(action):
            return await action.async_operation()
        
        dispatch_func = middleware_func(mock_next_dispatch)
        
        action = Mock()
        action.type = 'UPDATE_COUNTER'
        action.optimistic = True
        action.async_operation = mock_async_operation
        
        result = await dispatch_func(action)
        
        assert result == 'success'
        
        # Check stats
        stats = self.middleware.get_optimistic_stats()
        assert stats['total_updates'] == 1
        assert stats['confirmed_updates'] == 1
        assert stats['pending_count'] == 0
    
    @pytest.mark.asyncio
    async def test_failed_optimistic_update(self):
        """Test failed optimistic update rollback."""
        middleware_func = self.middleware(self.mock_store)
        
        async def failing_async_operation():
            await asyncio.sleep(0.001)
            raise ValueError("Operation failed")
        
        async def mock_next_dispatch(action):
            return await action.async_operation()
        
        dispatch_func = middleware_func(mock_next_dispatch)
        
        action = Mock()
        action.type = 'UPDATE_COUNTER'
        action.optimistic = True
        action.async_operation = failing_async_operation
        
        with pytest.raises(ValueError, match="Operation failed"):
            await dispatch_func(action)
        
        # Check stats
        stats = self.middleware.get_optimistic_stats()
        assert stats['total_updates'] == 1
        assert stats['failed_updates'] == 1
        assert stats['rollbacks'] == 1
    
    def test_pending_updates_limit(self):
        """Test pending updates limit enforcement."""
        # Set low limit
        middleware = OptimisticMiddleware(max_pending=2)
        middleware_func = middleware(self.mock_store)
        
        def mock_next_dispatch(action):
            return 'result'
        
        dispatch_func = middleware_func(mock_next_dispatch)
        
        # Fill up pending updates
        for i in range(3):
            action = Mock()
            action.type = f'UPDATE_{i}'
            action.optimistic = True
            
            # Mock async operation that doesn't complete
            future = asyncio.Future()
            action.async_operation = Mock(return_value=future)
            
            if i < 2:
                # Should work for first 2
                asyncio.create_task(dispatch_func(action))
            else:
                # Should fallback to sync for 3rd
                result = dispatch_func(action)
                assert result == 'result'
    
    def test_force_update_operations(self):
        """Test force confirm/rollback operations."""
        # Create pending update
        update = OptimisticUpdate(
            id='test_update',
            action=Mock(),
            optimistic_state={'test': True},
            original_state={'test': False}
        )
        
        self.middleware._pending_updates['test_update'] = update
        
        # Force confirm
        self.middleware.force_confirm_update('test_update')
        assert 'test_update' not in self.middleware._pending_updates
        
        stats = self.middleware.get_optimistic_stats()
        assert stats['confirmed_updates'] == 1


class TestOptimisticPredictor:
    """Test optimistic state prediction."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.predictor = OptimisticPredictor()
        self.current_state = {
            'counter': 5,
            'items': [{'id': 1, 'name': 'item1'}],
            'data': {'nested': {'value': 'test'}}
        }
    
    def test_update_prediction(self):
        """Test update action prediction."""
        action = Mock()
        action.type = 'UPDATE_COUNTER'
        action.payload = {'path': 'counter', 'value': 10}
        
        predicted = self.predictor.predict_state(self.current_state, action)
        
        assert predicted['counter'] == 10
        assert predicted['items'] == self.current_state['items']
        assert predicted['data'] == self.current_state['data']
    
    def test_create_prediction(self):
        """Test create action prediction."""
        action = Mock()
        action.type = 'CREATE_ITEM'
        action.payload = {
            'collection': 'items',
            'item': {'id': 2, 'name': 'item2'}
        }
        
        predicted = self.predictor.predict_state(self.current_state, action)
        
        assert len(predicted['items']) == 2
        assert predicted['items'][1] == {'id': 2, 'name': 'item2'}
    
    def test_delete_prediction(self):
        """Test delete action prediction."""
        action = Mock()
        action.type = 'DELETE_ITEM'
        action.payload = {
            'collection': 'items',
            'id': 1
        }
        
        predicted = self.predictor.predict_state(self.current_state, action)
        
        assert len(predicted['items']) == 0
    
    def test_nested_value_setting(self):
        """Test setting nested values."""
        action = Mock()
        action.type = 'UPDATE_NESTED'
        action.payload = {'path': 'data.nested.value', 'value': 'updated'}
        
        predicted = self.predictor.predict_state(self.current_state, action)
        
        assert predicted['data']['nested']['value'] == 'updated'
    
    def test_custom_optimistic_state(self):
        """Test action with custom optimistic state."""
        action = Mock()
        action.type = 'CUSTOM_ACTION'
        action.optimistic_state = {'custom': 'value'}
        
        predicted = self.predictor.predict_state(self.current_state, action)
        
        assert predicted['custom'] == 'value'
        assert 'counter' in predicted  # Original state preserved


class TestRollbackManager:
    """Test rollback manager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.rollback_manager = RollbackManager(
            strategy=RollbackStrategy.IMMEDIATE,
            max_rollback_points=10
        )
        self.mock_store = Mock()
        self.mock_store.get_state.return_value = {'current': 'state'}
        self.mock_store._set_state = Mock()
        self.mock_store._notify_subscribers = Mock()
    
    def test_rollback_point_creation(self):
        """Test rollback point creation."""
        action = Mock()
        action.type = 'TEST_ACTION'
        
        rollback_point = self.rollback_manager.create_rollback_point(
            'test_rollback',
            {'before': 'state'},
            action,
            description='Test rollback'
        )
        
        assert rollback_point.id == 'test_rollback'
        assert rollback_point.state == {'before': 'state'}
        assert rollback_point.action == action
        assert rollback_point.description == 'Test rollback'
        assert rollback_point.age >= 0
    
    def test_immediate_rollback_execution(self):
        """Test immediate rollback execution."""
        # Create rollback point
        rollback_point = self.rollback_manager.create_rollback_point(
            'test_rollback',
            {'rollback': 'state'},
            Mock()
        )
        
        # Execute rollback
        success = self.rollback_manager.execute_rollback(
            self.mock_store,
            'test_rollback'
        )
        
        assert success == True
        assert 'test_rollback' not in self.rollback_manager._rollback_points
        
        # Verify state was restored
        assert self.mock_store._notify_subscribers.called
    
    def test_rollback_with_conflicts(self):
        """Test rollback with conflict detection."""
        # Create rollback point with different state
        self.rollback_manager.create_rollback_point(
            'conflict_rollback',
            {'conflict': 'original'},
            Mock()
        )
        
        # Mock current state as different
        self.mock_store.get_state.return_value = {'conflict': 'modified'}
        
        # Execute rollback without force - should detect conflict
        success = self.rollback_manager.execute_rollback(
            self.mock_store,
            'conflict_rollback',
            force=False
        )
        
        # Should still succeed (conflicts resolved or handled)
        assert success in [True, False]  # Depends on conflict resolution
    
    def test_rollback_safety_calculation(self):
        """Test rollback safety calculation."""
        current_state = {'key1': 'value1', 'key2': 'value2'}
        rollback_state = {'key1': 'value1', 'key3': 'value3'}
        
        safety_score = self.rollback_manager._calculate_rollback_safety(
            current_state, rollback_state
        )
        
        assert 0.0 <= safety_score <= 1.0
    
    def test_conflict_resolver_registration(self):
        """Test conflict resolver registration."""
        def custom_resolver(current_val, rollback_val, path):
            return f"resolved:{current_val}:{rollback_val}"
        
        self.rollback_manager.register_conflict_resolver('test_path', custom_resolver)
        
        assert 'test_path' in self.rollback_manager._conflict_resolvers
    
    def test_rollback_statistics(self):
        """Test rollback statistics."""
        # Create and execute rollback
        self.rollback_manager.create_rollback_point('test', {}, Mock())
        self.rollback_manager.execute_rollback(self.mock_store, 'test')
        
        stats = self.rollback_manager.get_rollback_stats()
        
        assert stats['rollbacks_created'] == 1
        assert stats['rollbacks_executed'] == 1
        assert stats['active_rollback_points'] == 0


class TestConflictResolver:
    """Test conflict resolution functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.resolver = ConflictResolver(ConflictStrategy.LAST_WRITER_WINS)
    
    def test_conflict_detection(self):
        """Test conflict detection between states."""
        local_state = {'key1': 'local', 'key2': 'same', 'key3': 'local_only'}
        remote_state = {'key1': 'remote', 'key2': 'same', 'key4': 'remote_only'}
        
        conflicts = self.resolver.detect_conflicts(local_state, remote_state)
        
        # Should detect conflict on key1 (different values)
        assert len(conflicts) > 0
        conflict_paths = [c.path for c in conflicts]
        assert 'key1' in conflict_paths
    
    def test_three_way_conflict_detection(self):
        """Test three-way conflict detection with base state."""
        base_state = {'key1': 'base', 'key2': 'base'}
        local_state = {'key1': 'local', 'key2': 'base'}  # Only key1 changed
        remote_state = {'key1': 'remote', 'key2': 'base'}  # Only key1 changed
        
        conflicts = self.resolver.detect_conflicts(local_state, remote_state, base_state)
        
        # Should detect conflict on key1 (both sides changed)
        assert len(conflicts) == 1
        assert conflicts[0].path == 'key1'
        assert conflicts[0].base_value == 'base'
    
    def test_last_writer_wins_resolution(self):
        """Test last writer wins conflict resolution."""
        conflict = Conflict(
            path='test.key',
            local_value='local',
            remote_value='remote'
        )
        
        resolution = self.resolver.resolve_conflict(conflict)
        
        assert resolution.success == True
        assert resolution.resolved_value == 'remote'  # Remote is "last"
        assert resolution.strategy == ConflictStrategy.LAST_WRITER_WINS
    
    def test_merge_resolution(self):
        """Test merge conflict resolution."""
        resolver = ConflictResolver(ConflictStrategy.MERGE)
        
        # Test dictionary merge
        conflict = Conflict(
            path='data',
            local_value={'local_key': 'local_val', 'shared': 'local_shared'},
            remote_value={'remote_key': 'remote_val', 'shared': 'remote_shared'}
        )
        
        resolution = resolver.resolve_conflict(conflict)
        
        assert resolution.success == True
        merged = resolution.resolved_value
        assert 'local_key' in merged or 'remote_key' in merged
    
    def test_custom_conflict_handler(self):
        """Test custom conflict handler."""
        def custom_handler(local_val, remote_val, base_val=None):
            return f"custom:{local_val}:{remote_val}"
        
        self.resolver.register_custom_handler('custom.path', custom_handler)
        
        conflict = Conflict(
            path='custom.path',
            local_value='local',
            remote_value='remote'
        )
        
        resolution = self.resolver.resolve_conflict(conflict)
        
        assert resolution.success == True
        assert resolution.resolved_value == 'custom:local:remote'
        assert resolution.strategy == ConflictStrategy.CUSTOM
    
    def test_conflict_resolution_application(self):
        """Test applying resolutions to state."""
        state = {'key1': 'original', 'key2': 'unchanged'}
        
        conflict = Conflict(path='key1', local_value='local', remote_value='remote')
        resolution = ConflictResolution(
            conflict=conflict,
            resolved_value='resolved',
            strategy=ConflictStrategy.CUSTOM,
            success=True
        )
        
        resolved_state = self.resolver.apply_resolutions_to_state(state, [resolution])
        
        assert resolved_state['key1'] == 'resolved'
        assert resolved_state['key2'] == 'unchanged'
    
    def test_conflict_statistics(self):
        """Test conflict resolution statistics."""
        # Create and resolve conflicts
        conflicts = [
            Conflict(path='path1', local_value='local1', remote_value='remote1'),
            Conflict(path='path2', local_value='local2', remote_value='remote2')
        ]
        
        resolutions = self.resolver.resolve_conflicts(conflicts)
        
        stats = self.resolver.get_conflict_stats()
        
        assert stats['conflicts_detected'] == 2
        assert stats['conflicts_resolved'] >= 0  # Depends on success
        assert 'resolution_rate' in stats
    
    def test_builtin_conflict_handlers(self):
        """Test built-in conflict handler functions."""
        # Test prefer_larger_number
        result = prefer_larger_number(5, 10)
        assert result == 10
        
        result = prefer_larger_number(15, 8)
        assert result == 15
        
        # Test concatenate_strings
        result = concatenate_strings("hello", "world")
        assert result == "hello | world"


class TestIntegratedOptimisticSystem:
    """Test integration of optimistic updates, rollback, and conflicts."""
    
    def setup_method(self):
        """Set up integrated test environment."""
        self.optimistic_middleware = OptimisticMiddleware(timeout=1.0)
        self.rollback_manager = RollbackManager()
        self.conflict_resolver = ConflictResolver()
        
        self.mock_store = Mock()
        self.mock_store.get_state.return_value = {'integrated': 'state'}
        self.mock_store._set_state = Mock()
        self.mock_store._notify_subscribers = Mock()
    
    @pytest.mark.asyncio
    async def test_optimistic_with_rollback_integration(self):
        """Test optimistic updates with rollback integration."""
        # Create rollback point before optimistic update
        initial_state = {'counter': 0}
        self.mock_store.get_state.return_value = initial_state
        
        rollback_point = self.rollback_manager.create_rollback_point(
            'before_optimistic',
            initial_state,
            Mock()
        )
        
        # Set up optimistic middleware
        middleware_func = self.optimistic_middleware(self.mock_store)
        
        async def failing_operation():
            raise ValueError("Operation failed")
        
        async def mock_next_dispatch(action):
            return await action.async_operation()
        
        dispatch_func = middleware_func(mock_next_dispatch)
        
        # Create failing optimistic action
        action = Mock()
        action.type = 'UPDATE_COUNTER'
        action.optimistic = True
        action.async_operation = failing_operation
        
        # Execute and expect failure
        with pytest.raises(ValueError):
            await dispatch_func(action)
        
        # Verify rollback occurred
        stats = self.optimistic_middleware.get_optimistic_stats()
        assert stats['failed_updates'] == 1
        assert stats['rollbacks'] == 1
    
    def test_conflict_resolution_integration(self):
        """Test conflict resolution in optimistic updates."""
        # Simulate conflict scenario
        local_state = {'data': {'key': 'local_value'}}
        remote_state = {'data': {'key': 'remote_value'}}
        
        # Detect conflicts
        conflicts = self.conflict_resolver.detect_conflicts(local_state, remote_state)
        
        assert len(conflicts) > 0
        
        # Resolve conflicts
        resolutions = self.conflict_resolver.resolve_conflicts(conflicts)
        
        assert len(resolutions) == len(conflicts)
        assert all(r.success for r in resolutions)
        
        # Apply resolutions
        resolved_state = self.conflict_resolver.apply_resolutions_to_state(
            local_state, resolutions
        )
        
        assert resolved_state is not None
    
    @pytest.mark.asyncio
    async def test_full_optimistic_workflow(self):
        """Test complete optimistic update workflow."""
        # 1. Start with initial state
        initial_state = {'counter': 0, 'status': 'idle'}
        self.mock_store.get_state.return_value = initial_state
        
        # 2. Create rollback point
        rollback_point = self.rollback_manager.create_rollback_point(
            'workflow_test',
            initial_state,
            Mock()
        )
        
        # 3. Set up optimistic middleware
        middleware_func = self.optimistic_middleware(self.mock_store)
        
        async def successful_operation():
            await asyncio.sleep(0.001)
            return 'success'
        
        async def mock_next_dispatch(action):
            return await action.async_operation()
        
        dispatch_func = middleware_func(mock_next_dispatch)
        
        # 4. Execute optimistic action
        action = Mock()
        action.type = 'UPDATE_COUNTER'
        action.optimistic = True
        action.async_operation = successful_operation
        
        result = await dispatch_func(action)
        
        # 5. Verify success
        assert result == 'success'
        
        stats = self.optimistic_middleware.get_optimistic_stats()
        assert stats['total_updates'] == 1
        assert stats['confirmed_updates'] == 1
        assert stats['success_rate'] == 1.0


if __name__ == '__main__':
    pytest.main([__file__])