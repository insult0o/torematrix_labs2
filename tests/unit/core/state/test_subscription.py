"""
Unit tests for subscription management system.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, MagicMock

from src.torematrix.core.state.subscription import (
    SubscriptionManager, StateChange, Subscription, SubscriptionType
)


class TestStateChange:
    """Test StateChange functionality."""
    
    def test_state_change_creation(self):
        """Test state change creation."""
        change = StateChange(
            path='document.title',
            old_value='Old Title',
            new_value='New Title'
        )
        
        assert change.path == 'document.title'
        assert change.old_value == 'Old Title'
        assert change.new_value == 'New Title'
        assert change.change_type == 'update'
        assert isinstance(change.timestamp, float)
    
    def test_has_actual_change(self):
        """Test actual change detection."""
        # Real change
        change1 = StateChange('path', 'old', 'new')
        assert change1.has_actual_change
        
        # No change
        change2 = StateChange('path', 'same', 'same')
        assert not change2.has_actual_change


class TestSubscription:
    """Test Subscription functionality."""
    
    def test_subscription_creation(self):
        """Test subscription creation."""
        callback = Mock()
        
        subscription = Subscription(
            id='test_sub',
            subscription_type=SubscriptionType.PATH,
            path='test.path',
            callback=callback
        )
        
        assert subscription.id == 'test_sub'
        assert subscription.subscription_type == SubscriptionType.PATH
        assert subscription.path == 'test.path'
        assert subscription.callback == callback
        assert subscription.is_active
        assert subscription.notification_count == 0
    
    def test_path_subscription_should_notify(self):
        """Test path subscription notification logic."""
        callback = Mock()
        subscription = Subscription(
            id='test',
            subscription_type=SubscriptionType.PATH,
            path='document.title',
            callback=callback
        )
        
        # Matching path
        change1 = StateChange('document.title', 'old', 'new')
        assert subscription.should_notify(change1)
        
        # Non-matching path
        change2 = StateChange('document.author', 'old', 'new')
        assert not subscription.should_notify(change2)
    
    def test_pattern_subscription_should_notify(self):
        """Test pattern subscription notification logic."""
        callback = Mock()
        subscription = Subscription(
            id='test',
            subscription_type=SubscriptionType.PATTERN,
            path='elements.*.status',
            callback=callback
        )
        
        # Matching patterns
        change1 = StateChange('elements.1.status', 'old', 'new')
        assert subscription.should_notify(change1)
        
        change2 = StateChange('elements.999.status', 'old', 'new')
        assert subscription.should_notify(change2)
        
        # Non-matching pattern
        change3 = StateChange('elements.1.type', 'old', 'new')
        assert not subscription.should_notify(change3)
    
    def test_deep_subscription_should_notify(self):
        """Test deep subscription notification logic."""
        callback = Mock()
        subscription = Subscription(
            id='test',
            subscription_type=SubscriptionType.DEEP,
            path='document',
            callback=callback
        )
        
        # Exact path
        change1 = StateChange('document', 'old', 'new')
        assert subscription.should_notify(change1)
        
        # Child paths
        change2 = StateChange('document.title', 'old', 'new')
        assert subscription.should_notify(change2)
        
        change3 = StateChange('document.metadata.author', 'old', 'new')
        assert subscription.should_notify(change3)
        
        # Non-matching path
        change4 = StateChange('elements', 'old', 'new')
        assert not subscription.should_notify(change4)
    
    def test_change_subscription_should_notify(self):
        """Test change subscription notification logic."""
        callback = Mock()
        subscription = Subscription(
            id='test',
            subscription_type=SubscriptionType.CHANGE,
            path='*',
            callback=callback
        )
        
        # Should notify for any change
        change1 = StateChange('any.path', 'old', 'new')
        assert subscription.should_notify(change1)
        
        change2 = StateChange('different.path', 'old', 'new')
        assert subscription.should_notify(change2)


class TestSubscriptionManager:
    """Test SubscriptionManager functionality."""
    
    def test_manager_creation(self):
        """Test manager creation."""
        manager = SubscriptionManager()
        
        assert manager.batch_notifications is True
        assert manager.batch_timeout_ms == 5.0
        assert len(manager._subscriptions) == 0
    
    def test_subscribe_to_path(self):
        """Test path subscription."""
        manager = SubscriptionManager()
        callback = Mock()
        
        sub_id = manager.subscribe_to_path('document.title', callback)
        
        assert isinstance(sub_id, str)
        assert len(manager._subscriptions) == 1
        assert sub_id in manager._subscriptions
        
        subscription = manager._subscriptions[sub_id]
        assert subscription.subscription_type == SubscriptionType.PATH
        assert subscription.path == 'document.title'
        assert subscription.callback == callback
    
    def test_subscribe_to_pattern(self):
        """Test pattern subscription."""
        manager = SubscriptionManager()
        callback = Mock()
        
        sub_id = manager.subscribe_to_pattern('elements.*.status', callback)
        
        subscription = manager._subscriptions[sub_id]
        assert subscription.subscription_type == SubscriptionType.PATTERN
        assert subscription.path == 'elements.*.status'
    
    def test_subscribe_to_deep_path(self):
        """Test deep path subscription."""
        manager = SubscriptionManager()
        callback = Mock()
        
        sub_id = manager.subscribe_to_deep_path('document', callback)
        
        subscription = manager._subscriptions[sub_id]
        assert subscription.subscription_type == SubscriptionType.DEEP
        assert subscription.path == 'document'
    
    def test_subscribe_to_selector(self):
        """Test selector subscription."""
        manager = SubscriptionManager()
        callback = Mock()
        selector = Mock()
        selector.name = 'test_selector'
        
        sub_id = manager.subscribe_to_selector(selector, callback)
        
        subscription = manager._subscriptions[sub_id]
        assert subscription.subscription_type == SubscriptionType.SELECTOR
        assert subscription.selector == selector
        assert selector in manager._subscriptions_by_selector
    
    def test_subscribe_to_any_change(self):
        """Test global change subscription."""
        manager = SubscriptionManager()
        callback = Mock()
        
        sub_id = manager.subscribe_to_any_change(callback)
        
        subscription = manager._subscriptions[sub_id]
        assert subscription.subscription_type == SubscriptionType.CHANGE
        assert subscription.path == '*'
    
    def test_unsubscribe(self):
        """Test unsubscribing."""
        manager = SubscriptionManager()
        callback = Mock()
        
        sub_id = manager.subscribe_to_path('test.path', callback)
        assert len(manager._subscriptions) == 1
        
        success = manager.unsubscribe(sub_id)
        assert success
        assert len(manager._subscriptions) == 0
        
        # Unsubscribing non-existent subscription
        success = manager.unsubscribe('non_existent')
        assert not success
    
    def test_notify_path_subscription(self):
        """Test notifying path subscriptions."""
        manager = SubscriptionManager(batch_notifications=False)
        callback = Mock()
        
        manager.subscribe_to_path('document.title', callback)
        
        # Matching change
        change = StateChange('document.title', 'old', 'new')
        manager.notify_state_change(change)
        
        callback.assert_called_once_with(change)
        
        # Non-matching change
        callback.reset_mock()
        change2 = StateChange('document.author', 'old', 'new')
        manager.notify_state_change(change2)
        
        callback.assert_not_called()
    
    def test_notify_pattern_subscription(self):
        """Test notifying pattern subscriptions."""
        manager = SubscriptionManager(batch_notifications=False)
        callback = Mock()
        
        manager.subscribe_to_pattern('elements.*.status', callback)
        
        # Matching changes
        change1 = StateChange('elements.1.status', 'pending', 'validated')
        change2 = StateChange('elements.999.status', 'pending', 'validated')
        
        manager.notify_state_change([change1, change2])
        
        assert callback.call_count == 2
        callback.assert_any_call(change1)
        callback.assert_any_call(change2)
        
        # Non-matching change
        callback.reset_mock()
        change3 = StateChange('elements.1.type', 'text', 'image')
        manager.notify_state_change(change3)
        
        callback.assert_not_called()
    
    def test_notify_deep_subscription(self):
        """Test notifying deep subscriptions."""
        manager = SubscriptionManager(batch_notifications=False)
        callback = Mock()
        
        manager.subscribe_to_deep_path('document', callback)
        
        # Should notify for document and all children
        changes = [
            StateChange('document', {}, {'title': 'test'}),
            StateChange('document.title', 'old', 'new'),
            StateChange('document.metadata.author', 'old', 'new'),
        ]
        
        for change in changes:
            manager.notify_state_change(change)
        
        assert callback.call_count == 3
    
    def test_notify_change_subscription(self):
        """Test notifying global change subscriptions."""
        manager = SubscriptionManager(batch_notifications=False)
        callback = Mock()
        
        manager.subscribe_to_any_change(callback)
        
        # Should notify for any change
        changes = [
            StateChange('document.title', 'old', 'new'),
            StateChange('elements.1.status', 'pending', 'validated'),
            StateChange('ui.current_page', 0, 1),
        ]
        
        for change in changes:
            manager.notify_state_change(change)
        
        assert callback.call_count == 3
    
    def test_notify_selector_change(self):
        """Test notifying selector changes."""
        manager = SubscriptionManager()
        callback = Mock()
        selector = Mock()
        
        manager.subscribe_to_selector(selector, callback)
        
        old_value = ['old', 'data']
        new_value = ['new', 'data']
        
        manager.notify_selector_change(selector, old_value, new_value)
        
        callback.assert_called_once_with(old_value, new_value)
    
    @pytest.mark.asyncio
    async def test_batch_notifications(self):
        """Test batch notification system."""
        manager = SubscriptionManager(batch_notifications=True, batch_timeout_ms=10)
        callback = Mock()
        
        manager.subscribe_to_path('test.path', callback)
        
        # Send multiple changes quickly
        changes = [
            StateChange('test.path', f'old{i}', f'new{i}')
            for i in range(5)
        ]
        
        for change in changes:
            manager.notify_state_change(change)
        
        # Should not be called immediately due to batching
        callback.assert_not_called()
        
        # Wait for batch timeout
        await asyncio.sleep(0.02)
        await manager.flush_batch()
        
        # Should be called once with the latest change
        assert callback.call_count == 1
    
    @pytest.mark.asyncio
    async def test_flush_batch(self):
        """Test manual batch flushing."""
        manager = SubscriptionManager(batch_notifications=True, batch_timeout_ms=1000)
        callback = Mock()
        
        manager.subscribe_to_path('test.path', callback)
        
        change = StateChange('test.path', 'old', 'new')
        manager.notify_state_change(change)
        
        # Should not be called yet
        callback.assert_not_called()
        
        # Manually flush
        await manager.flush_batch()
        
        # Should be called now
        callback.assert_called_once_with(change)
    
    def test_cleanup_dead_subscriptions(self):
        """Test cleanup of dead subscriptions."""
        manager = SubscriptionManager()
        
        # Create some subscriptions
        callback1 = Mock()
        callback2 = Mock()
        
        sub_id1 = manager.subscribe_to_path('path1', callback1)
        sub_id2 = manager.subscribe_to_path('path2', callback2)
        
        assert len(manager._subscriptions) == 2
        
        # Mark one as inactive
        manager._subscriptions[sub_id1].is_active = False
        
        # Cleanup
        cleaned = manager.cleanup_dead_subscriptions()
        
        assert cleaned == 1
        assert len(manager._subscriptions) == 1
        assert sub_id1 not in manager._subscriptions
        assert sub_id2 in manager._subscriptions
    
    def test_subscription_stats(self):
        """Test subscription statistics."""
        manager = SubscriptionManager()
        
        # Create various subscriptions
        callback = Mock()
        manager.subscribe_to_path('path1', callback)
        manager.subscribe_to_pattern('pattern.*', callback)
        manager.subscribe_to_deep_path('deep', callback)
        manager.subscribe_to_any_change(callback)
        
        stats = manager.get_subscription_stats()
        
        assert stats['total_subscriptions'] == 4
        assert stats['active_subscriptions'] == 4
        assert stats['inactive_subscriptions'] == 0
        assert stats['subscriptions_by_type']['path'] == 2  # path and deep
        assert stats['subscriptions_by_type']['pattern'] == 1
        assert stats['subscriptions_by_type']['change'] == 1
    
    def test_get_subscription_details(self):
        """Test getting subscription details."""
        manager = SubscriptionManager()
        callback = Mock()
        
        sub_id = manager.subscribe_to_path('test.path', callback, {'option': 'value'})
        
        details = manager.get_subscription_details(sub_id)
        
        assert details is not None
        assert details['id'] == sub_id
        assert details['type'] == 'path'
        assert details['path'] == 'test.path'
        assert details['is_active'] is True
        assert details['options'] == {'option': 'value'}
        assert details['notification_count'] == 0
        
        # Non-existent subscription
        details = manager.get_subscription_details('non_existent')
        assert details is None
    
    def test_enable_disable_batching(self):
        """Test enabling/disabling batching."""
        manager = SubscriptionManager(batch_notifications=False)
        
        assert not manager.batch_notifications
        
        manager.enable_batching(True)
        assert manager.batch_notifications
        
        manager.enable_batching(False)
        assert not manager.batch_notifications
    
    def test_set_batch_timeout(self):
        """Test setting batch timeout."""
        manager = SubscriptionManager()
        
        original_timeout = manager.batch_timeout_ms
        new_timeout = 50.0
        
        manager.set_batch_timeout(new_timeout)
        assert manager.batch_timeout_ms == new_timeout
        assert manager.batch_timeout_ms != original_timeout
    
    def test_clear_all_subscriptions(self):
        """Test clearing all subscriptions."""
        manager = SubscriptionManager()
        callback = Mock()
        
        # Create several subscriptions
        manager.subscribe_to_path('path1', callback)
        manager.subscribe_to_pattern('pattern.*', callback)
        manager.subscribe_to_deep_path('deep', callback)
        
        assert len(manager._subscriptions) == 3
        
        manager.clear_all_subscriptions()
        
        assert len(manager._subscriptions) == 0
        assert len(manager._subscriptions_by_path) == 0
        assert len(manager._subscriptions_by_pattern) == 0
    
    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test manager shutdown."""
        manager = SubscriptionManager(batch_notifications=True)
        callback = Mock()
        
        manager.subscribe_to_path('test.path', callback)
        
        # Add pending notification
        change = StateChange('test.path', 'old', 'new')
        manager.notify_state_change(change)
        
        # Shutdown should flush pending notifications
        await manager.shutdown()
        
        # Should be empty after shutdown
        assert len(manager._subscriptions) == 0
        assert len(manager._pending_notifications) == 0
    
    def test_no_actual_change_ignored(self):
        """Test that changes without actual value differences are ignored."""
        manager = SubscriptionManager(batch_notifications=False)
        callback = Mock()
        
        manager.subscribe_to_path('test.path', callback)
        
        # Change with same old and new value
        no_change = StateChange('test.path', 'same', 'same')
        manager.notify_state_change(no_change)
        
        # Should not notify
        callback.assert_not_called()
        
        # Actual change
        real_change = StateChange('test.path', 'old', 'new')
        manager.notify_state_change(real_change)
        
        # Should notify
        callback.assert_called_once_with(real_change)
    
    def test_subscription_notification_tracking(self):
        """Test tracking of subscription notifications."""
        manager = SubscriptionManager(batch_notifications=False)
        callback = Mock()
        
        sub_id = manager.subscribe_to_path('test.path', callback)
        subscription = manager._subscriptions[sub_id]
        
        # Initial state
        assert subscription.notification_count == 0
        assert subscription.last_notified == 0.0
        
        # Send notification
        change = StateChange('test.path', 'old', 'new')
        manager.notify_state_change(change)
        
        # Should be updated
        assert subscription.notification_count == 1
        assert subscription.last_notified > 0.0
    
    def test_multiple_subscription_types_same_path(self):
        """Test multiple subscription types for the same path."""
        manager = SubscriptionManager(batch_notifications=False)
        
        path_callback = Mock()
        deep_callback = Mock()
        change_callback = Mock()
        
        # Subscribe with different types to overlapping paths
        manager.subscribe_to_path('document.title', path_callback)
        manager.subscribe_to_deep_path('document', deep_callback)
        manager.subscribe_to_any_change(change_callback)
        
        # Send change
        change = StateChange('document.title', 'old', 'new')
        manager.notify_state_change(change)
        
        # All should be notified
        path_callback.assert_called_once_with(change)
        deep_callback.assert_called_once_with(change)
        change_callback.assert_called_once_with(change)
    
    def test_subscription_error_handling(self):
        """Test handling of subscription callback errors."""
        manager = SubscriptionManager(batch_notifications=False)
        
        # Callback that raises exception
        def error_callback(change):
            raise Exception("Callback error")
        
        # Normal callback
        normal_callback = Mock()
        
        manager.subscribe_to_path('test.path', error_callback)
        manager.subscribe_to_path('test.path', normal_callback)
        
        change = StateChange('test.path', 'old', 'new')
        
        # Should not raise exception, but continue with other callbacks
        manager.notify_state_change(change)
        
        # Normal callback should still be called
        normal_callback.assert_called_once_with(change)


if __name__ == '__main__':
    pytest.main([__file__])