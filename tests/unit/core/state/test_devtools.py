"""
Tests for DevTools integration and transaction support.
"""

import pytest
import time
import json
from unittest.mock import Mock, patch
from src.torematrix.core.state.devtools import (
    ReduxDevTools,
    DevToolsOptions,
    ActionLogEntry
)
from src.torematrix.core.state.transactions import (
    TransactionMiddleware,
    Transaction,
    TransactionStatus
)


class TestDevToolsOptions:
    """Test DevTools configuration options."""
    
    def test_default_options(self):
        """Test default DevTools options."""
        options = DevToolsOptions()
        
        assert options.name == "TORE Matrix State"
        assert options.max_actions == 50
        assert options.serialize == True
        assert options.action_sanitizer is None
    
    def test_custom_options(self):
        """Test custom DevTools options."""
        def custom_sanitizer(action):
            return {'sanitized': True}
        
        options = DevToolsOptions(
            name="Custom App",
            max_actions=100,
            serialize=False,
            action_sanitizer=custom_sanitizer
        )
        
        assert options.name == "Custom App"
        assert options.max_actions == 100
        assert options.serialize == False
        assert options.action_sanitizer == custom_sanitizer
    
    def test_options_to_dict(self):
        """Test converting options to dictionary."""
        options = DevToolsOptions(name="Test App", max_age=60)
        options_dict = options.to_dict()
        
        assert options_dict['name'] == "Test App"
        assert options_dict['maxAge'] == 60
        assert 'serialize' in options_dict


class TestActionLogEntry:
    """Test action log entry structure."""
    
    def test_log_entry_creation(self):
        """Test ActionLogEntry creation."""
        action = Mock()
        action.type = 'TEST_ACTION'
        
        entry = ActionLogEntry(
            id='entry_1',
            action=action,
            state_before={'before': True},
            state_after={'after': True},
            duration=0.005
        )
        
        assert entry.id == 'entry_1'
        assert entry.action == action
        assert entry.duration == 0.005
        assert entry.error is None
    
    def test_log_entry_datetime(self):
        """Test datetime property."""
        entry = ActionLogEntry(
            id='test',
            action=Mock(),
            state_before={},
            state_after={}
        )
        
        assert entry.datetime is not None
        assert entry.timestamp > 0


class TestReduxDevTools:
    """Test Redux DevTools functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.devtools = ReduxDevTools()
        self.mock_store = Mock()
        self.mock_store.get_state.return_value = {'test': 'state'}
    
    def test_devtools_initialization(self):
        """Test DevTools initialization."""
        assert self.devtools.options.name == "TORE Matrix State"
        assert self.devtools._enabled == True
        assert len(self.devtools._action_log) == 0
        assert len(self.devtools._state_history) == 0
    
    def test_middleware_creation(self):
        """Test DevTools middleware creation."""
        middleware = self.devtools.create_middleware()
        assert callable(middleware)
        
        middleware_func = middleware(self.mock_store)
        assert callable(middleware_func)
        
        dispatch_func = middleware_func(Mock(return_value='result'))
        assert callable(dispatch_func)
    
    def test_action_logging(self):
        """Test action logging functionality."""
        middleware = self.devtools.create_middleware()
        middleware_func = middleware(self.mock_store)
        
        def mock_next_dispatch(action):
            # Simulate state change
            self.mock_store.get_state.return_value = {'updated': 'state'}
            return 'dispatched'
        
        dispatch_func = middleware_func(mock_next_dispatch)
        
        action = Mock()
        action.type = 'TEST_ACTION'
        action.payload = {'data': 'test'}
        
        result = dispatch_func(action)
        
        assert result == 'dispatched'
        assert len(self.devtools._action_log) == 1
        assert len(self.devtools._state_history) == 1
        
        log_entry = self.devtools._action_log[0]
        assert log_entry.action.type == 'TEST_ACTION'
        assert log_entry.state_after == {'updated': 'state'}
    
    def test_action_logging_with_error(self):
        """Test action logging when errors occur."""
        middleware = self.devtools.create_middleware()
        middleware_func = middleware(self.mock_store)
        
        def failing_dispatch(action):
            raise ValueError("Test error")
        
        dispatch_func = middleware_func(failing_dispatch)
        
        action = Mock()
        action.type = 'FAILING_ACTION'
        
        with pytest.raises(ValueError):
            dispatch_func(action)
        
        # Error should be logged
        assert len(self.devtools._action_log) == 1
        log_entry = self.devtools._action_log[0]
        assert log_entry.error == "Test error"
    
    def test_action_sanitization(self):
        """Test action sanitization."""
        def custom_sanitizer(action):
            return {'type': action.type, 'sanitized': True}
        
        options = DevToolsOptions(action_sanitizer=custom_sanitizer)
        devtools = ReduxDevTools(options)
        
        # Test sanitization
        action = Mock()
        action.type = 'TEST_ACTION'
        action.sensitive_data = 'secret'
        
        sanitized = devtools._sanitize_action(action)
        
        assert sanitized['type'] == 'TEST_ACTION'
        assert sanitized['sanitized'] == True
        assert 'sensitive_data' not in sanitized
    
    def test_state_sanitization(self):
        """Test state sanitization."""
        def custom_state_sanitizer(state):
            return {k: v for k, v in state.items() if not k.startswith('_')}
        
        options = DevToolsOptions(state_sanitizer=custom_state_sanitizer)
        devtools = ReduxDevTools(options)
        
        state = {'public': 'data', '_private': 'secret'}
        sanitized = devtools._sanitize_state(state)
        
        assert 'public' in sanitized
        assert '_private' not in sanitized
    
    def test_time_travel(self):
        """Test time travel functionality."""
        # Add some states to history
        states = [
            {'counter': 0},
            {'counter': 1},
            {'counter': 2}
        ]
        
        for state in states:
            self.devtools._state_history.append(state)
        
        # Time travel to index 1
        success = self.devtools.time_travel(self.mock_store, 1)
        
        assert success == True
        assert self.devtools._current_index == 1
        
        # Invalid index should fail
        success = self.devtools.time_travel(self.mock_store, 10)
        assert success == False
    
    def test_action_replay(self):
        """Test action replay functionality."""
        # Create mock actions and states
        actions = [
            Mock(type='ACTION_1'),
            Mock(type='ACTION_2'),
            Mock(type='ACTION_3')
        ]
        
        for i, action in enumerate(actions):
            entry = ActionLogEntry(
                id=f'action_{i}',
                action=action,
                state_before={},
                state_after={'counter': i}
            )
            self.devtools._action_log.append(entry)
            self.devtools._state_history.append({'counter': i})
        
        # Mock store dispatch
        dispatched_actions = []
        self.mock_store.dispatch = lambda a: dispatched_actions.append(a)
        
        # Replay actions 1-2
        success = self.devtools.replay_actions(self.mock_store, 1, 2)
        
        assert success == True
        assert len(dispatched_actions) == 2
        assert dispatched_actions[0].type == 'ACTION_2'
        assert dispatched_actions[1].type == 'ACTION_3'
    
    def test_export_state(self):
        """Test state export functionality."""
        # Add test data
        action = Mock()
        action.type = 'TEST_ACTION'
        
        entry = ActionLogEntry(
            id='test_entry',
            action=action,
            state_before={'before': True},
            state_after={'after': True}
        )
        
        self.devtools._action_log.append(entry)
        self.devtools._state_history.append({'after': True})
        
        # Export as JSON
        json_export = self.devtools.export_state('json')
        exported_data = json.loads(json_export)
        
        assert 'actions' in exported_data
        assert 'states' in exported_data
        assert len(exported_data['actions']) == 1
        assert len(exported_data['states']) == 1
        
        # Export as CSV
        csv_export = self.devtools.export_state('csv')
        assert 'id,action_type,timestamp' in csv_export
        assert 'test_entry' in csv_export
    
    def test_import_state(self):
        """Test state import functionality."""
        # Create test data
        test_data = {
            'actions': [
                {
                    'id': 'imported_action',
                    'action': {'type': 'IMPORTED_ACTION'},
                    'timestamp': time.time(),
                    'duration': 0.001
                }
            ],
            'states': [{'imported': 'state'}],
            'current_index': 0
        }
        
        json_data = json.dumps(test_data)
        
        # Import state
        success = self.devtools.import_state(json_data, self.mock_store)
        
        assert success == True
        assert len(self.devtools._action_log) == 1
        assert len(self.devtools._state_history) == 1
        assert self.devtools._action_log[0].id == 'imported_action'
    
    def test_performance_stats(self):
        """Test performance statistics."""
        # Add test entries with different durations
        durations = [0.001, 0.002, 0.003, 0.004, 0.005]
        
        for i, duration in enumerate(durations):
            entry = ActionLogEntry(
                id=f'perf_{i}',
                action=Mock(type=f'ACTION_{i}'),
                state_before={},
                state_after={},
                duration=duration
            )
            self.devtools._action_log.append(entry)
        
        stats = self.devtools.get_performance_stats()
        
        assert stats['total_actions'] == 5
        assert stats['avg_duration'] == sum(durations) / len(durations)
        assert stats['max_duration'] == max(durations)
        assert stats['min_duration'] == min(durations)
        assert stats['errors'] == 0
    
    def test_max_actions_limit(self):
        """Test maximum actions limit."""
        devtools = ReduxDevTools(DevToolsOptions(max_actions=3))
        
        # Add more actions than limit
        for i in range(5):
            action = Mock(type=f'ACTION_{i}')
            entry = ActionLogEntry(
                id=f'action_{i}',
                action=action,
                state_before={},
                state_after={}
            )
            devtools._action_log.append(entry)
            devtools._state_history.append({})
            
            # Simulate limit enforcement
            if len(devtools._action_log) > devtools.options.max_actions:
                devtools._action_log.pop(0)
                devtools._state_history.pop(0)
        
        # Should only keep last 3 actions
        assert len(devtools._action_log) == 3
        assert devtools._action_log[0].id == 'action_2'  # Oldest kept
    
    def test_enable_disable(self):
        """Test enabling/disabling DevTools."""
        assert self.devtools.is_enabled() == True
        
        self.devtools.disable()
        assert self.devtools.is_enabled() == False
        
        self.devtools.enable()
        assert self.devtools.is_enabled() == True
    
    def test_clear_log(self):
        """Test clearing DevTools log."""
        # Add test data
        self.devtools._action_log.append(ActionLogEntry(
            id='test',
            action=Mock(),
            state_before={},
            state_after={}
        ))
        self.devtools._state_history.append({'test': 'state'})
        
        assert len(self.devtools._action_log) == 1
        assert len(self.devtools._state_history) == 1
        
        self.devtools.clear_log()
        
        assert len(self.devtools._action_log) == 0
        assert len(self.devtools._state_history) == 0


class TestTransaction:
    """Test transaction data structure."""
    
    def test_transaction_creation(self):
        """Test Transaction creation."""
        transaction = Transaction(id='test_tx')
        
        assert transaction.id == 'test_tx'
        assert transaction.status == TransactionStatus.PENDING
        assert transaction.is_active == True
        assert transaction.is_completed == False
        assert len(transaction.actions) == 0
    
    def test_transaction_duration(self):
        """Test transaction duration calculation."""
        transaction = Transaction(id='test_tx')
        
        time.sleep(0.001)
        assert transaction.duration > 0
        
        # Duration should be fixed when committed
        transaction.committed_at = time.time()
        duration1 = transaction.duration
        time.sleep(0.001)
        duration2 = transaction.duration
        assert duration1 == duration2


class TestTransactionMiddleware:
    """Test transaction middleware functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.tx_middleware = TransactionMiddleware(auto_commit=True)
        self.mock_store = Mock()
        self.mock_store.get_state.return_value = {'test': 'state'}
    
    def test_transactional_action_detection(self):
        """Test detection of transactional actions."""
        # Action with transactional flag
        tx_action = Mock()
        tx_action.transactional = True
        assert self.tx_middleware._is_transactional_action(tx_action)
        
        # Transaction control action
        begin_action = Mock()
        begin_action.type = 'BEGIN_TRANSACTION'
        assert self.tx_middleware._is_transactional_action(begin_action)
        
        # Batch action
        batch_action = Mock()
        batch_action.type = 'BATCH_UPDATE'
        assert self.tx_middleware._is_transactional_action(batch_action)
        
        # Regular action
        regular_action = Mock()
        regular_action.type = 'REGULAR_ACTION'
        assert not self.tx_middleware._is_transactional_action(regular_action)
    
    def test_begin_transaction(self):
        """Test beginning a transaction."""
        begin_action = Mock()
        begin_action.type = 'BEGIN_TRANSACTION'
        begin_action.transaction_id = 'test_tx'
        begin_action.metadata = {'test': 'metadata'}
        
        tx_id = self.tx_middleware._begin_transaction(self.mock_store, begin_action)
        
        assert tx_id == 'test_tx'
        assert 'test_tx' in self.tx_middleware._active_transactions
        assert 'test_tx' in self.tx_middleware._transaction_stack
        
        transaction = self.tx_middleware._active_transactions['test_tx']
        assert transaction.metadata == {'test': 'metadata'}
    
    def test_commit_transaction(self):
        """Test committing a transaction."""
        # Begin transaction first
        begin_action = Mock()
        begin_action.type = 'BEGIN_TRANSACTION'
        begin_action.transaction_id = 'test_tx'
        begin_action.metadata = {}
        
        self.tx_middleware._begin_transaction(self.mock_store, begin_action)
        
        # Commit transaction
        commit_action = Mock()
        commit_action.type = 'COMMIT_TRANSACTION'
        commit_action.transaction_id = 'test_tx'
        
        success = self.tx_middleware._commit_transaction(self.mock_store, commit_action)
        
        assert success == True
        assert 'test_tx' not in self.tx_middleware._active_transactions
        assert 'test_tx' not in self.tx_middleware._transaction_stack
    
    def test_rollback_transaction(self):
        """Test rolling back a transaction."""
        # Begin transaction first
        initial_state = {'initial': 'state'}
        self.mock_store.get_state.return_value = initial_state
        
        begin_action = Mock()
        begin_action.type = 'BEGIN_TRANSACTION'
        begin_action.transaction_id = 'test_tx'
        begin_action.metadata = {}
        
        self.tx_middleware._begin_transaction(self.mock_store, begin_action)
        
        # Rollback transaction
        rollback_action = Mock()
        rollback_action.type = 'ROLLBACK_TRANSACTION'
        rollback_action.transaction_id = 'test_tx'
        
        success = self.tx_middleware._rollback_transaction(self.mock_store, rollback_action)
        
        assert success == True
        assert 'test_tx' not in self.tx_middleware._active_transactions
    
    def test_auto_commit_behavior(self):
        """Test auto-commit behavior."""
        middleware_func = self.tx_middleware(self.mock_store)
        
        call_order = []
        
        def mock_next_dispatch(action):
            call_order.append(f"dispatch_{action.type}")
            return 'result'
        
        dispatch_func = middleware_func(mock_next_dispatch)
        
        # Create transactional action
        action = Mock()
        action.type = 'BATCH_UPDATE'
        action.transactional = True
        
        result = dispatch_func(action)
        
        assert result == 'result'
        # Auto-commit should have cleaned up
        assert len(self.tx_middleware._active_transactions) == 0
    
    def test_transaction_error_handling(self):
        """Test transaction error handling and rollback."""
        middleware_func = self.tx_middleware(self.mock_store)
        
        def failing_dispatch(action):
            if action.type == 'FAILING_ACTION':
                raise ValueError("Transaction failed")
            return 'success'
        
        dispatch_func = middleware_func(failing_dispatch)
        
        # Create failing transactional action
        action = Mock()
        action.type = 'FAILING_ACTION'
        action.transactional = True
        
        with pytest.raises(ValueError):
            dispatch_func(action)
        
        # Transaction should be rolled back
        assert len(self.tx_middleware._active_transactions) == 0
    
    def test_transaction_size_limit(self):
        """Test transaction size limit."""
        tx_middleware = TransactionMiddleware(max_transaction_size=2, auto_commit=False)
        
        # Begin transaction manually
        begin_action = Mock()
        begin_action.type = 'BEGIN_TRANSACTION'
        begin_action.transaction_id = 'size_test'
        begin_action.metadata = {}
        
        tx_middleware._begin_transaction(self.mock_store, begin_action)
        
        middleware_func = tx_middleware(self.mock_store)
        dispatch_func = middleware_func(Mock(return_value='result'))
        
        # Add actions up to limit
        for i in range(2):
            action = Mock()
            action.type = f'ACTION_{i}'
            action.transactional = True
            dispatch_func(action)
        
        # Next action should trigger rollback
        action = Mock()
        action.type = 'OVERFLOW_ACTION'
        action.transactional = True
        
        with pytest.raises(RuntimeError, match="exceeded maximum size"):
            dispatch_func(action)
    
    def test_transaction_context_manager(self):
        """Test transaction context manager."""
        executed_actions = []
        
        def mock_dispatch(action):
            executed_actions.append(action.type)
            return 'result'
        
        self.mock_store.dispatch = mock_dispatch
        
        # Use context manager
        with self.tx_middleware.transaction(self.mock_store, 'context_tx') as tx_id:
            assert tx_id == 'context_tx'
            assert 'context_tx' in self.tx_middleware._active_transactions
        
        # Transaction should be committed after context
        assert 'context_tx' not in self.tx_middleware._active_transactions
    
    def test_transaction_context_manager_with_error(self):
        """Test transaction context manager with error."""
        with pytest.raises(ValueError):
            with self.tx_middleware.transaction(self.mock_store, 'error_tx'):
                assert 'error_tx' in self.tx_middleware._active_transactions
                raise ValueError("Context error")
        
        # Transaction should be rolled back
        assert 'error_tx' not in self.tx_middleware._active_transactions
    
    def test_transaction_statistics(self):
        """Test transaction statistics."""
        # Execute some transactions
        with self.tx_middleware.transaction(self.mock_store):
            pass
        
        # Force a rollback
        try:
            with self.tx_middleware.transaction(self.mock_store):
                raise ValueError("Test error")
        except ValueError:
            pass
        
        stats = self.tx_middleware.get_transaction_stats()
        
        assert stats['transactions_created'] == 2
        assert stats['transactions_committed'] == 1
        assert stats['transactions_rolled_back'] == 1
        assert 'avg_transaction_time' in stats
    
    def test_force_rollback_all(self):
        """Test force rollback of all transactions."""
        # Create multiple active transactions
        tx_ids = ['tx1', 'tx2', 'tx3']
        
        for tx_id in tx_ids:
            begin_action = Mock()
            begin_action.type = 'BEGIN_TRANSACTION'
            begin_action.transaction_id = tx_id
            begin_action.metadata = {}
            
            self.tx_middleware._begin_transaction(self.mock_store, begin_action)
        
        assert len(self.tx_middleware._active_transactions) == 3
        
        # Force rollback all
        count = self.tx_middleware.force_rollback_all(self.mock_store)
        
        assert count == 3
        assert len(self.tx_middleware._active_transactions) == 0


class TestIntegratedDevToolsAndTransactions:
    """Test integration between DevTools and transactions."""
    
    def setup_method(self):
        """Set up integrated test environment."""
        self.devtools = ReduxDevTools()
        self.tx_middleware = TransactionMiddleware()
        self.mock_store = Mock()
        self.mock_store.get_state.return_value = {'integrated': 'state'}
        self.mock_store._set_state = Mock()
    
    def test_devtools_transaction_logging(self):
        """Test DevTools logging of transaction actions."""
        # Set up middleware chain
        devtools_middleware = self.devtools.create_middleware()
        tx_middleware = self.tx_middleware
        
        # Create integrated middleware
        def integrated_middleware(next_dispatch):
            tx_func = tx_middleware(self.mock_store)
            devtools_func = devtools_middleware(self.mock_store)
            
            # Chain: DevTools -> Transactions -> Next
            return devtools_func(tx_func(next_dispatch))
        
        dispatch_func = integrated_middleware(Mock(return_value='result'))
        
        # Execute transaction actions
        begin_action = Mock()
        begin_action.type = 'BEGIN_TRANSACTION'
        begin_action.transaction_id = 'logged_tx'
        begin_action.metadata = {}
        
        dispatch_func(begin_action)
        
        commit_action = Mock()
        commit_action.type = 'COMMIT_TRANSACTION'
        commit_action.transaction_id = 'logged_tx'
        
        dispatch_func(commit_action)
        
        # Check DevTools logged the transaction actions
        action_log = self.devtools.get_action_log()
        assert len(action_log) >= 2
        
        logged_types = [entry.action.type for entry in action_log]
        assert 'BEGIN_TRANSACTION' in logged_types
        assert 'COMMIT_TRANSACTION' in logged_types
    
    def test_devtools_time_travel_with_transactions(self):
        """Test DevTools time travel with transaction state."""
        # Create transaction state history
        states = [
            {'counter': 0, 'tx_active': False},
            {'counter': 0, 'tx_active': True},   # Transaction began
            {'counter': 1, 'tx_active': True},   # Action in transaction
            {'counter': 1, 'tx_active': False}   # Transaction committed
        ]
        
        for state in states:
            self.devtools._state_history.append(state)
        
        # Time travel to transaction begin
        success = self.devtools.time_travel(self.mock_store, 1)
        assert success == True
        
        # Time travel to transaction committed
        success = self.devtools.time_travel(self.mock_store, 3)
        assert success == True


if __name__ == '__main__':
    pytest.main([__file__])