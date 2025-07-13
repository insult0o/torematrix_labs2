"""
Tests for Event Bus integration and state synchronization.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from src.torematrix.core.state.integration.event_bus import (
    EventBusIntegration,
    StateUpdateEvent,
    StateChangeEvent
)
from src.torematrix.core.state.integration.sync import (
    StateSyncManager,
    SyncMode,
    SyncRule,
    SyncEvent
)
from src.torematrix.core.state.integration.replay import (
    EventReplayManager,
    ReplayableEvent,
    ReplaySession
)


class TestEventBusIntegration:
    """Test Event Bus integration functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_event_bus = Mock()
        self.integration = EventBusIntegration(self.mock_event_bus)
        self.mock_store = Mock()
        self.mock_store.get_state.return_value = {'test': 'state'}
    
    def test_integration_creation(self):
        """Test Event Bus integration creation."""
        assert self.integration.event_bus == self.mock_event_bus
        assert self.integration._sync_enabled == True
        assert len(self.integration._action_handlers) == 0
    
    def test_middleware_creation(self):
        """Test middleware creation."""
        middleware = self.integration.create_middleware()
        assert callable(middleware)
        
        # Test middleware function
        middleware_func = middleware(self.mock_store)
        assert callable(middleware_func)
        
        # Test dispatch function
        dispatch_func = middleware_func(Mock(return_value='result'))
        assert callable(dispatch_func)
    
    def test_state_change_event_emission(self):
        """Test emission of state change events."""
        middleware = self.integration.create_middleware()
        middleware_func = middleware(self.mock_store)
        
        def mock_next_dispatch(action):
            # Simulate state change
            self.mock_store.get_state.return_value = {'updated': 'state'}
            return 'dispatched'
        
        dispatch_func = middleware_func(mock_next_dispatch)
        
        action = Mock()
        action.type = 'TEST_ACTION'
        
        result = dispatch_func(action)
        
        # Verify event was published
        assert self.mock_event_bus.publish.called
        published_event = self.mock_event_bus.publish.call_args[0][0]
        assert isinstance(published_event, StateChangeEvent)
        assert published_event.action == action
    
    def test_state_update_request_handling(self):
        """Test handling of state update requests."""
        # Create update event
        update_event = StateUpdateEvent(
            path="test.value",
            value="new_value"
        )
        
        # Mock store dispatch
        dispatched_actions = []
        def mock_dispatch(action):
            dispatched_actions.append(action)
            return action
        
        self.mock_store.dispatch = mock_dispatch
        
        # Handle update request
        self.integration._handle_state_update_request(self.mock_store, update_event)
        
        # Verify action was dispatched
        assert len(dispatched_actions) == 1
        assert dispatched_actions[0].type == "UPDATE_STATE"
        assert dispatched_actions[0].payload['path'] == "test.value"
        assert dispatched_actions[0].payload['value'] == "new_value"
    
    def test_action_handler_registration(self):
        """Test registration of action handlers."""
        def test_handler(event):
            return Mock(type='CUSTOM_ACTION')
        
        self.integration.register_action_handler('CUSTOM_EVENT', test_handler)
        
        assert 'CUSTOM_EVENT' in self.integration._action_handlers
        assert self.integration._action_handlers['CUSTOM_EVENT'] == test_handler
    
    def test_sync_enable_disable(self):
        """Test enabling and disabling sync."""
        assert self.integration._sync_enabled == True
        
        self.integration.disable_sync()
        assert self.integration._sync_enabled == False
        
        self.integration.enable_sync()
        assert self.integration._sync_enabled == True
    
    def test_sync_stats(self):
        """Test sync statistics."""
        stats = self.integration.get_sync_stats()
        
        assert 'events_sent' in stats
        assert 'events_received' in stats
        assert 'sync_errors' in stats
        assert 'last_sync' in stats


class TestStateSyncManager:
    """Test state synchronization manager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.sync_manager = StateSyncManager(SyncMode.MANUAL)
        
        # Create mock stores
        self.store1 = Mock()
        self.store1.get_state.return_value = {'store1': 'data', 'shared': 'value1'}
        self.store1.dispatch = Mock()
        
        self.store2 = Mock()
        self.store2.get_state.return_value = {'store2': 'data', 'shared': 'value2'}
        self.store2.dispatch = Mock()
    
    def test_store_registration(self):
        """Test store registration."""
        self.sync_manager.register_store('store1', self.store1)
        self.sync_manager.register_store('store2', self.store2)
        
        assert 'store1' in self.sync_manager.stores
        assert 'store2' in self.sync_manager.stores
    
    def test_sync_rule_addition(self):
        """Test adding sync rules."""
        rule = SyncRule(path='shared', direction='bidirectional')
        self.sync_manager.add_sync_rule('store1', rule)
        
        assert 'store1' in self.sync_manager.sync_rules
        assert len(self.sync_manager.sync_rules['store1']) == 1
        assert self.sync_manager.sync_rules['store1'][0] == rule
    
    def test_manual_sync(self):
        """Test manual synchronization."""
        # Register stores
        self.sync_manager.register_store('store1', self.store1)
        self.sync_manager.register_store('store2', self.store2)
        
        # Add sync rule
        rule = SyncRule(path='shared', direction='outbound')
        self.sync_manager.add_sync_rule('store1', rule)
        
        # Perform sync
        self.sync_manager.sync_stores('store1', ['store2'])
        
        # Verify store2 was updated
        assert self.store2.dispatch.called
    
    def test_conflict_resolution(self):
        """Test conflict resolution."""
        def conflict_resolver(source_value, target_value, **kwargs):
            return f"resolved:{source_value}:{target_value}"
        
        self.sync_manager.set_conflict_resolver(conflict_resolver)
        
        # Register stores with conflicting values
        self.sync_manager.register_store('store1', self.store1)
        self.sync_manager.register_store('store2', self.store2)
        
        # Add sync rule
        rule = SyncRule(path='shared', direction='bidirectional')
        self.sync_manager.add_sync_rule('store1', rule)
        
        # Sync should resolve conflict
        self.sync_manager.sync_stores('store1', ['store2'])
        
        # Verify resolution was called
        assert self.store2.dispatch.called
    
    def test_sync_statistics(self):
        """Test sync statistics."""
        stats = self.sync_manager.get_sync_stats()
        
        assert 'total_syncs' in stats
        assert 'successful_syncs' in stats
        assert 'failed_syncs' in stats
        assert 'conflicts_resolved' in stats
    
    def test_sync_history(self):
        """Test sync history tracking."""
        # Register stores
        self.sync_manager.register_store('store1', self.store1)
        self.sync_manager.register_store('store2', self.store2)
        
        # Perform sync
        self.sync_manager.sync_stores('store1', ['store2'])
        
        # Check history
        history = self.sync_manager.get_sync_history()
        assert len(history) > 0
        assert isinstance(history[0], SyncEvent)


class TestEventReplayManager:
    """Test event replay manager."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.replay_manager = EventReplayManager(max_events=100)
        self.mock_store = Mock()
        self.mock_store.get_state.return_value = {'initial': 'state'}
        self.mock_store.dispatch = Mock()
    
    def test_event_capture(self):
        """Test event capture."""
        self.replay_manager.capture_event(
            event_id='event1',
            event_type='ACTION_DISPATCHED',
            data={'action': 'test_action'},
            source='store1'
        )
        
        assert len(self.replay_manager.events) == 1
        event = self.replay_manager.events[0]
        assert event.event_id == 'event1'
        assert event.event_type == 'ACTION_DISPATCHED'
        assert event.data == {'action': 'test_action'}
        assert event.source == 'store1'
    
    def test_replay_session_creation(self):
        """Test replay session creation."""
        session = self.replay_manager.create_replay_session(
            session_id='session1',
            event_types=['ACTION_DISPATCHED'],
            event_sources=['store1']
        )
        
        assert session.session_id == 'session1'
        assert session.event_types == ['ACTION_DISPATCHED']
        assert session.event_sources == ['store1']
        assert 'session1' in self.replay_manager.sessions
    
    def test_event_filtering(self):
        """Test event filtering for replay sessions."""
        # Capture multiple events
        events_data = [
            ('event1', 'TYPE_A', {'data': 1}, 'source1'),
            ('event2', 'TYPE_B', {'data': 2}, 'source2'),
            ('event3', 'TYPE_A', {'data': 3}, 'source1'),
            ('event4', 'TYPE_C', {'data': 4}, 'source3'),
        ]
        
        for event_id, event_type, data, source in events_data:
            self.replay_manager.capture_event(event_id, event_type, data, source)
        
        # Create filtered session
        session = self.replay_manager.create_replay_session(
            session_id='filtered',
            event_types=['TYPE_A'],
            event_sources=['source1']
        )
        
        # Get filtered events
        filtered_events = self.replay_manager.get_events_for_session('filtered')
        
        assert len(filtered_events) == 2  # Only TYPE_A from source1
        assert all(e.event_type == 'TYPE_A' for e in filtered_events)
        assert all(e.source == 'source1' for e in filtered_events)
    
    def test_replay_to_store(self):
        """Test replaying events to a store."""
        # Capture events
        self.replay_manager.capture_event('event1', 'ACTION', {'type': 'ADD_ITEM'})
        self.replay_manager.capture_event('event2', 'ACTION', {'type': 'UPDATE_ITEM'})
        
        # Create session
        session = self.replay_manager.create_replay_session('replay_test')
        
        # Define action converter
        def action_converter(event):
            class Action:
                def __init__(self, data):
                    self.type = data['type']
                    self.payload = data
            return Action(event.data)
        
        # Replay to store
        stats = self.replay_manager.replay_to_store('replay_test', self.mock_store, action_converter)
        
        assert stats['total_events'] == 2
        assert stats['successful_replays'] == 2
        assert stats['failed_replays'] == 0
        assert self.mock_store.dispatch.call_count == 2
    
    def test_state_reconstruction(self):
        """Test state reconstruction from events."""
        # Capture state change events
        self.replay_manager.capture_event('event1', 'STATE_CHANGE', {
            'path': 'counter',
            'value': 1
        })
        self.replay_manager.capture_event('event2', 'STATE_CHANGE', {
            'path': 'counter', 
            'value': 2
        })
        
        # Create session
        session = self.replay_manager.create_replay_session('reconstruct')
        
        # Define state reducer
        def state_reducer(state, event):
            new_state = dict(state)
            if event.event_type == 'STATE_CHANGE':
                path = event.data['path']
                value = event.data['value']
                new_state[path] = value
            return new_state
        
        # Reconstruct state
        initial_state = {'counter': 0}
        final_state = self.replay_manager.reconstruct_state(
            'reconstruct', 
            initial_state, 
            state_reducer
        )
        
        assert final_state['counter'] == 2
    
    def test_event_analysis(self):
        """Test event pattern analysis."""
        # Capture various events
        event_data = [
            ('e1', 'TYPE_A', {}, 'source1'),
            ('e2', 'TYPE_A', {}, 'source1'),
            ('e3', 'TYPE_B', {}, 'source2'),
            ('e4', 'TYPE_A', {}, 'source1'),
        ]
        
        for event_id, event_type, data, source in event_data:
            self.replay_manager.capture_event(event_id, event_type, data, source)
        
        analysis = self.replay_manager.analyze_event_patterns()
        
        assert analysis['total_events'] == 4
        assert analysis['event_types']['TYPE_A'] == 3
        assert analysis['event_types']['TYPE_B'] == 1
        assert analysis['event_sources']['source1'] == 3
        assert analysis['event_sources']['source2'] == 1
    
    def test_event_export(self):
        """Test event export."""
        # Capture events
        self.replay_manager.capture_event('event1', 'TEST', {'data': 'test1'})
        self.replay_manager.capture_event('event2', 'TEST', {'data': 'test2'})
        
        # Export as JSON
        json_export = self.replay_manager.export_events(format='json')
        assert 'event1' in json_export
        assert 'event2' in json_export
        
        # Export as CSV
        csv_export = self.replay_manager.export_events(format='csv')
        assert 'event_id' in csv_export
        assert 'event1' in csv_export
        assert 'event2' in csv_export
    
    def test_max_events_limit(self):
        """Test maximum events limit."""
        replay_manager = EventReplayManager(max_events=3)
        
        # Capture more events than limit
        for i in range(5):
            replay_manager.capture_event(f'event{i}', 'TEST', {'data': i})
        
        # Should only keep last 3 events
        assert len(replay_manager.events) == 3
        assert replay_manager.events[0].event_id == 'event2'  # Oldest kept
        assert replay_manager.events[-1].event_id == 'event4'  # Newest


class TestIntegratedStateSystems:
    """Test integration between all state management systems."""
    
    def setup_method(self):
        """Set up integrated test environment."""
        # Event Bus
        self.mock_event_bus = Mock()
        
        # Event Bus Integration
        self.event_integration = EventBusIntegration(self.mock_event_bus)
        
        # Sync Manager
        self.sync_manager = StateSyncManager(SyncMode.AUTOMATIC)
        
        # Replay Manager
        self.replay_manager = EventReplayManager()
        
        # Mock stores
        self.store1 = Mock()
        self.store1.get_state.return_value = {'store1_data': 'value1'}
        self.store1.dispatch = Mock()
        
        self.store2 = Mock()
        self.store2.get_state.return_value = {'store2_data': 'value2'}
        self.store2.dispatch = Mock()
    
    def test_event_bus_sync_integration(self):
        """Test integration between Event Bus and sync manager."""
        # Register stores with sync manager
        self.sync_manager.register_store('store1', self.store1)
        self.sync_manager.register_store('store2', self.store2)
        
        # Set up Event Bus integration
        middleware = self.event_integration.create_middleware()
        middleware_func = middleware(self.store1)
        dispatch_func = middleware_func(Mock(return_value='result'))
        
        # Dispatch action
        action = Mock()
        action.type = 'SYNC_ACTION'
        dispatch_func(action)
        
        # Verify event was published
        assert self.mock_event_bus.publish.called
    
    def test_replay_sync_integration(self):
        """Test integration between replay manager and sync."""
        # Capture sync events
        self.replay_manager.capture_event(
            'sync1',
            'SYNC_PERFORMED',
            {
                'source_store': 'store1',
                'target_store': 'store2',
                'synced_data': {'key': 'value'}
            }
        )
        
        # Create replay session
        session = self.replay_manager.create_replay_session(
            'sync_replay',
            event_types=['SYNC_PERFORMED']
        )
        
        filtered_events = self.replay_manager.get_events_for_session('sync_replay')
        assert len(filtered_events) == 1
        assert filtered_events[0].event_type == 'SYNC_PERFORMED'
    
    def test_full_system_integration(self):
        """Test full integration of all systems."""
        # Set up complete integration
        
        # 1. Register stores with sync
        self.sync_manager.register_store('store1', self.store1)
        self.sync_manager.register_store('store2', self.store2)
        
        # 2. Set up Event Bus integration
        self.event_integration.sync_with_event_bus(self.store1)
        
        # 3. Enable event capture
        self.replay_manager.enable_capture()
        
        # 4. Perform operations
        action = Mock()
        action.type = 'INTEGRATED_ACTION'
        
        # Simulate action dispatch with all systems
        middleware = self.event_integration.create_middleware()
        middleware_func = middleware(self.store1)
        
        def integrated_dispatch(action):
            # Capture event
            self.replay_manager.capture_event(
                f'action_{action.type}',
                'ACTION_DISPATCHED',
                {'action_type': action.type}
            )
            
            # Trigger sync
            self.sync_manager.sync_stores('store1', ['store2'])
            
            return 'integrated_result'
        
        dispatch_func = middleware_func(integrated_dispatch)
        result = dispatch_func(action)
        
        # Verify integration
        assert result == 'integrated_result'
        assert len(self.replay_manager.events) == 1
        assert self.store2.dispatch.called
        assert self.mock_event_bus.publish.called


if __name__ == '__main__':
    pytest.main([__file__])