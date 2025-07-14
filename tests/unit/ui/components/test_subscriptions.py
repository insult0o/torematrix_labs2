"""
Tests for State Subscription Manager.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from tore_matrix_labs.ui.components.subscriptions import (
    Subscription,
    SubscriptionManager,
    get_subscription_manager,
    bind_state,
    connect_state,
    StateSubscriptionMixin
)


class TestSubscription:
    """Test the Subscription dataclass."""
    
    def test_subscription_creation(self):
        """Test creating a subscription."""
        component = Mock()
        selector = lambda state: state.get('value')
        callback = Mock()
        
        sub = Subscription(
            component_ref=weakref.ref(component),
            selector=selector,
            callback=callback,
            store_id='test_store',
            property_name='test_prop'
        )
        
        assert sub.store_id == 'test_store'
        assert sub.property_name == 'test_prop'
        assert sub.active is True
        assert sub.last_value is None
    
    def test_subscription_hash_and_equality(self):
        """Test subscription hashing and equality."""
        component = Mock()
        selector = lambda state: state.get('value')
        
        sub1 = Subscription(
            component_ref=weakref.ref(component),
            selector=selector,
            callback=Mock(),
            store_id='store1'
        )
        
        sub2 = Subscription(
            component_ref=weakref.ref(component),
            selector=selector,
            callback=Mock(),
            store_id='store1'
        )
        
        # Same component, selector, and store should be equal
        assert sub1 == sub2
        assert hash(sub1) == hash(sub2)


class TestSubscriptionManager:
    """Test the SubscriptionManager class."""
    
    def test_register_store(self):
        """Test registering a state store."""
        manager = SubscriptionManager()
        store = {'state': 'initial'}
        
        manager.register_store('test_store', store)
        
        assert 'test_store' in manager._stores
        assert manager._stores['test_store'] == store
    
    def test_subscribe_with_callback(self):
        """Test subscribing with a custom callback."""
        manager = SubscriptionManager()
        component = Mock()
        callback = Mock()
        selector = lambda state: state.get('value')
        
        # Register store
        store = {'value': 42}
        manager.register_store('test_store', store)
        
        # Subscribe
        sub = manager.subscribe(
            component=component,
            store_id='test_store',
            selector=selector,
            callback=callback
        )
        
        # Verify subscription created
        assert sub is not None
        assert sub.store_id == 'test_store'
        assert sub.callback == callback
        
        # Verify initial callback called
        callback.assert_called_once_with(42)
    
    def test_subscribe_with_property_binding(self):
        """Test subscribing with property binding."""
        manager = SubscriptionManager()
        component = Mock()
        selector = lambda state: state.get('value')
        
        # Register store
        store = {'value': 'initial'}
        manager.register_store('test_store', store)
        
        # Subscribe with property binding
        sub = manager.subscribe(
            component=component,
            store_id='test_store',
            selector=selector,
            property_name='test_prop'
        )
        
        # Verify property was set
        assert hasattr(component, 'test_prop')
        assert component.test_prop == 'initial'
    
    def test_notify_change(self):
        """Test notifying subscribers of changes."""
        manager = SubscriptionManager()
        component = Mock()
        callback = Mock()
        selector = lambda state: state.get('value')
        
        # Subscribe
        manager.register_store('test_store', {})
        sub = manager.subscribe(
            component=component,
            store_id='test_store',
            selector=selector,
            callback=callback
        )
        
        # Reset mock to ignore initial call
        callback.reset_mock()
        
        # Notify change
        new_state = {'value': 'changed'}
        manager.notify_change('test_store', new_state)
        
        # Verify callback called with new value
        callback.assert_called_once_with('changed')
    
    def test_notify_change_only_on_value_change(self):
        """Test that notifications only happen when value changes."""
        manager = SubscriptionManager()
        component = Mock()
        callback = Mock()
        selector = lambda state: state.get('value')
        
        # Subscribe
        manager.register_store('test_store', {'value': 'initial'})
        sub = manager.subscribe(
            component=component,
            store_id='test_store',
            selector=selector,
            callback=callback
        )
        
        callback.reset_mock()
        
        # Notify with same value
        manager.notify_change('test_store', {'value': 'initial'})
        callback.assert_not_called()
        
        # Notify with different value
        manager.notify_change('test_store', {'value': 'changed'})
        callback.assert_called_once_with('changed')
    
    def test_unsubscribe(self):
        """Test unsubscribing."""
        manager = SubscriptionManager()
        component = Mock()
        callback = Mock()
        
        # Subscribe
        manager.register_store('test_store', {})
        sub = manager.subscribe(
            component=component,
            store_id='test_store',
            selector=lambda s: s.get('value'),
            callback=callback
        )
        
        # Unsubscribe
        manager.unsubscribe(sub)
        
        # Verify subscription inactive
        assert not sub.active
        assert sub not in manager._subscriptions['test_store']
    
    def test_unsubscribe_component(self):
        """Test unsubscribing all subscriptions for a component."""
        manager = SubscriptionManager()
        component = Mock()
        
        # Create multiple subscriptions
        manager.register_store('store1', {})
        manager.register_store('store2', {})
        
        sub1 = manager.subscribe(
            component=component,
            store_id='store1',
            selector=lambda s: s,
            callback=Mock()
        )
        
        sub2 = manager.subscribe(
            component=component,
            store_id='store2',
            selector=lambda s: s,
            callback=Mock()
        )
        
        # Unsubscribe component
        manager.unsubscribe_component(component)
        
        # Verify all subscriptions removed
        assert id(component) not in manager._component_subscriptions
        assert sub1 not in manager._subscriptions['store1']
        assert sub2 not in manager._subscriptions['store2']
    
    def test_weak_reference_cleanup(self):
        """Test that subscriptions are cleaned up when component is garbage collected."""
        manager = SubscriptionManager()
        callback = Mock()
        
        # Create component in scope
        def create_subscription():
            component = Mock()
            manager.register_store('test_store', {})
            sub = manager.subscribe(
                component=component,
                store_id='test_store',
                selector=lambda s: s,
                callback=callback
            )
            return id(component)
        
        component_id = create_subscription()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Verify subscription cleaned up
        assert component_id not in manager._component_subscriptions
    
    def test_suspend_notifications(self):
        """Test suspending notifications."""
        manager = SubscriptionManager()
        component = Mock()
        callback = Mock()
        
        # Subscribe
        manager.register_store('test_store', {})
        manager.subscribe(
            component=component,
            store_id='test_store',
            selector=lambda s: s.get('value'),
            callback=callback
        )
        
        callback.reset_mock()
        
        # Suspend notifications
        with manager.suspend_notifications():
            manager.notify_change('test_store', {'value': 'changed'})
            callback.assert_not_called()
        
        # Notifications should work again
        manager.notify_change('test_store', {'value': 'changed2'})
        callback.assert_called_once_with('changed2')
    
    def test_thread_safety(self):
        """Test thread safety of subscription manager."""
        manager = SubscriptionManager()
        manager.register_store('test_store', {})
        
        components = []
        subscriptions = []
        errors = []
        
        def worker(worker_id):
            try:
                # Create component and subscribe
                component = Mock()
                components.append(component)
                
                sub = manager.subscribe(
                    component=component,
                    store_id='test_store',
                    selector=lambda s: s.get(f'value_{worker_id}'),
                    callback=Mock()
                )
                subscriptions.append(sub)
                
                # Notify changes
                for i in range(10):
                    manager.notify_change('test_store', {f'value_{worker_id}': i})
                
                # Unsubscribe
                manager.unsubscribe(sub)
                
            except Exception as e:
                errors.append(e)
        
        # Run multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        for t in threads:
            t.join()
        
        # Verify no errors
        assert len(errors) == 0


class TestBindStateDecorator:
    """Test the bind_state decorator."""
    
    def test_bind_state_with_string_selector(self):
        """Test bind_state with string selector."""
        @bind_state('test_store', 'user.name', 'username')
        def get_username(self):
            pass
        
        # Verify binding info stored
        assert hasattr(get_username, '_state_binding')
        binding = get_username._state_binding
        assert binding['store_id'] == 'test_store'
        assert binding['property_name'] == 'username'
        
        # Test selector
        state = {'user': {'name': 'John'}}
        assert binding['selector'](state) == 'John'
    
    def test_bind_state_with_function_selector(self):
        """Test bind_state with function selector."""
        def custom_selector(state):
            return state.get('users', [])
        
        @bind_state('test_store', custom_selector)
        def get_users(self):
            pass
        
        binding = get_users._state_binding
        assert binding['selector'] == custom_selector
        assert binding['property_name'] == 'get_users'  # Uses function name


class TestConnectStateDecorator:
    """Test the connect_state class decorator."""
    
    def test_connect_state_decorator(self):
        """Test that connect_state sets up subscriptions."""
        manager = get_subscription_manager()
        manager.register_store('test_store', {'value': 42})
        
        @connect_state
        class TestComponent:
            def __init__(self):
                self.value = None
            
            @bind_state('test_store', 'value', 'value')
            def get_value(self):
                pass
        
        # Create component
        component = TestComponent()
        
        # Verify subscription created and value set
        assert component.value == 42
        
        # Verify component has subscriptions
        subs = manager.get_subscriptions_for_component(component)
        assert len(subs) == 1
    
    def test_connect_state_cleanup(self):
        """Test that connect_state adds cleanup."""
        @connect_state
        class TestComponent:
            pass
        
        # Verify __del__ method added
        assert hasattr(TestComponent, '__del__')


class TestStateSubscriptionMixin:
    """Test the StateSubscriptionMixin class."""
    
    def test_subscribe_to_state_with_string_selector(self):
        """Test subscribing with string selector."""
        manager = get_subscription_manager()
        manager.register_store('test_store', {'user': {'name': 'Alice'}})
        
        class TestComponent(StateSubscriptionMixin):
            def __init__(self):
                self.username = None
        
        component = TestComponent()
        
        # Subscribe using string selector
        sub = component.subscribe_to_state(
            'test_store',
            'user.name',
            property_name='username'
        )
        
        # Verify property set
        assert component.username == 'Alice'
    
    def test_subscribe_to_state_with_callback(self):
        """Test subscribing with callback."""
        manager = get_subscription_manager()
        manager.register_store('test_store', {'count': 0})
        
        class TestComponent(StateSubscriptionMixin):
            def __init__(self):
                self.update_count = 0
            
            def on_count_change(self, value):
                self.update_count += 1
        
        component = TestComponent()
        callback = Mock()
        
        # Subscribe with callback
        sub = component.subscribe_to_state(
            'test_store',
            lambda s: s.get('count'),
            callback=callback
        )
        
        # Notify change
        manager.notify_change('test_store', {'count': 1})
        
        # Verify callback called
        callback.assert_called_with(1)
    
    def test_unsubscribe_all(self):
        """Test unsubscribing all subscriptions."""
        manager = get_subscription_manager()
        manager.register_store('store1', {})
        manager.register_store('store2', {})
        
        class TestComponent(StateSubscriptionMixin):
            pass
        
        component = TestComponent()
        
        # Create multiple subscriptions
        sub1 = component.subscribe_to_state('store1', lambda s: s)
        sub2 = component.subscribe_to_state('store2', lambda s: s)
        
        # Unsubscribe all
        component.unsubscribe_all()
        
        # Verify all subscriptions removed
        assert len(component.get_subscriptions()) == 0
    
    def test_get_subscriptions(self):
        """Test getting all subscriptions."""
        manager = get_subscription_manager()
        manager.register_store('test_store', {})
        
        class TestComponent(StateSubscriptionMixin):
            pass
        
        component = TestComponent()
        
        # Create subscriptions
        sub1 = component.subscribe_to_state('test_store', lambda s: s.get('a'))
        sub2 = component.subscribe_to_state('test_store', lambda s: s.get('b'))
        
        # Get subscriptions
        subs = component.get_subscriptions()
        
        assert len(subs) == 2
        assert sub1 in subs
        assert sub2 in subs


# Import weakref at module level
import weakref


if __name__ == '__main__':
    pytest.main([__file__, '-v'])