"""
Unit tests for selector system.
"""

import pytest
import time
from unittest.mock import Mock, MagicMock

from src.torematrix.core.state.selectors.base import (
    Selector, ParametricSelector, SelectorKey, create_selector, create_parametric_selector
)
from src.torematrix.core.state.selectors.factory import SelectorFactory
from src.torematrix.core.state.selectors.common import (
    get_elements, get_visible_elements, get_elements_by_type
)


class TestSelectorKey:
    """Test SelectorKey functionality."""
    
    def test_create_selector_key(self):
        """Test selector key creation."""
        state = {'elements': [1, 2, 3], 'document': {'title': 'test'}}
        args = ('test', 123)
        
        key = SelectorKey.create(state, args)
        
        assert isinstance(key.state_hash, int)
        assert isinstance(key.args_hash, int)
        assert key.state_hash != 0
        assert key.args_hash != 0
    
    def test_selector_key_equality(self):
        """Test selector key equality."""
        state = {'elements': [1, 2, 3]}
        args = ('test',)
        
        key1 = SelectorKey.create(state, args)
        key2 = SelectorKey.create(state, args)
        
        assert key1 == key2
    
    def test_selector_key_inequality(self):
        """Test selector key inequality with different state."""
        state1 = {'elements': [1, 2, 3]}
        state2 = {'elements': [4, 5, 6]}
        args = ('test',)
        
        key1 = SelectorKey.create(state1, args)
        key2 = SelectorKey.create(state2, args)
        
        assert key1 != key2


class TestSelector:
    """Test basic Selector functionality."""
    
    def test_selector_creation(self):
        """Test basic selector creation."""
        def test_fn(state):
            return state.get('test', 'default')
        
        selector = Selector(test_fn, name='test_selector')
        
        assert selector.name == 'test_selector'
        assert selector.selector_fn == test_fn
        assert selector.dependencies == []
        assert selector._total_calls == 0
    
    def test_selector_execution(self):
        """Test selector execution."""
        def get_value(state):
            return state.get('value', 0)
        
        selector = Selector(get_value)
        state = {'value': 42}
        
        result = selector(state)
        
        assert result == 42
        assert selector._total_calls == 1
        assert selector._cache_hits == 0
        assert selector._cache_misses == 1
    
    def test_selector_memoization(self):
        """Test selector memoization."""
        call_count = 0
        
        def expensive_computation(state):
            nonlocal call_count
            call_count += 1
            return state.get('value', 0) * 2
        
        selector = Selector(expensive_computation)
        state = {'value': 21}
        
        # First call
        result1 = selector(state)
        assert result1 == 42
        assert call_count == 1
        assert selector._cache_misses == 1
        
        # Second call with same state - should use cache
        result2 = selector(state)
        assert result2 == 42
        assert call_count == 1  # Function not called again
        assert selector._cache_hits == 1
    
    def test_selector_cache_invalidation(self):
        """Test selector cache invalidation."""
        def get_value(state):
            return state.get('value', 0)
        
        selector = Selector(get_value)
        state1 = {'value': 42}
        state2 = {'value': 84}
        
        # First call
        result1 = selector(state1)
        assert result1 == 42
        
        # Second call with different state
        result2 = selector(state2)
        assert result2 == 84
        
        # Cache should have 2 entries
        assert len(selector._cache) == 2
        
        # Invalidate cache
        selector.invalidate()
        assert len(selector._cache) == 0
    
    def test_selector_with_dependencies(self):
        """Test selector with dependencies."""
        get_base = lambda state: state.get('base', [])
        
        def filter_positive(base_result):
            return [x for x in base_result if x > 0]
        
        selector = create_selector(get_base, filter_positive)
        state = {'base': [-2, -1, 0, 1, 2, 3]}
        
        result = selector(state)
        assert result == [1, 2, 3]
    
    def test_selector_performance_tracking(self):
        """Test selector performance tracking."""
        def slow_function(state):
            time.sleep(0.001)  # 1ms delay
            return state.get('value', 0)
        
        selector = Selector(slow_function)
        state = {'value': 42}
        
        selector(state)
        
        stats = selector.get_stats()
        assert stats['total_calls'] == 1
        assert stats['avg_execution_time_ms'] > 0
        assert stats['cache_hit_rate'] == 0  # First call is always miss
    
    def test_selector_cache_size_limit(self):
        """Test selector cache size limiting."""
        def get_value(state):
            return state.get('value', 0)
        
        selector = Selector(get_value)
        selector._max_cache_size = 5  # Small cache for testing
        
        # Fill cache beyond limit
        for i in range(10):
            state = {'value': i}
            selector(state)
        
        # Cache should be limited
        assert len(selector._cache) <= selector._max_cache_size


class TestParametricSelector:
    """Test ParametricSelector functionality."""
    
    def test_parametric_selector_creation(self):
        """Test parametric selector creation."""
        def filter_fn(items, min_value):
            return [x for x in items if x >= min_value]
        
        selector = ParametricSelector(filter_fn)
        
        assert isinstance(selector, Selector)
        assert isinstance(selector, ParametricSelector)
    
    def test_parametric_selector_execution(self):
        """Test parametric selector execution with parameters."""
        def filter_fn(items, min_value=0):
            return [x for x in items if x >= min_value]
        
        get_items = lambda state: state.get('items', [])
        selector = create_parametric_selector(get_items, output_fn=filter_fn)
        
        state = {'items': [-2, -1, 0, 1, 2, 3]}
        
        # Test with different parameters
        result1 = selector(state, min_value=0)
        assert result1 == [0, 1, 2, 3]
        
        result2 = selector(state, min_value=2)
        assert result2 == [2, 3]
    
    def test_parametric_selector_memoization(self):
        """Test parametric selector memoization with parameters."""
        call_count = 0
        
        def expensive_filter(items, threshold):
            nonlocal call_count
            call_count += 1
            return [x for x in items if x > threshold]
        
        get_items = lambda state: state.get('items', [])
        selector = create_parametric_selector(get_items, output_fn=expensive_filter)
        
        state = {'items': [1, 2, 3, 4, 5]}
        
        # First call with threshold=2
        result1 = selector(state, threshold=2)
        assert result1 == [3, 4, 5]
        assert call_count == 1
        
        # Second call with same parameters - should use cache
        result2 = selector(state, threshold=2)
        assert result2 == [3, 4, 5]
        assert call_count == 1  # No additional call
        
        # Third call with different threshold
        result3 = selector(state, threshold=3)
        assert result3 == [4, 5]
        assert call_count == 2  # New call for different parameters


class TestSelectorFactory:
    """Test SelectorFactory functionality."""
    
    def test_factory_creation(self):
        """Test factory creation."""
        factory = SelectorFactory()
        assert isinstance(factory, SelectorFactory)
        assert len(factory._created_selectors) == 0
    
    def test_create_path_selector(self):
        """Test path selector creation."""
        factory = SelectorFactory()
        
        selector = factory.create_path_selector('document.title', 'untitled')
        state = {
            'document': {'title': 'Test Document'},
            'other': 'data'
        }
        
        result = selector(state)
        assert result == 'Test Document'
        
        # Test with missing path
        empty_state = {}
        result = selector(empty_state)
        assert result == 'untitled'
    
    def test_create_filter_selector(self):
        """Test filter selector creation."""
        factory = SelectorFactory()
        
        get_numbers = lambda state: state.get('numbers', [])
        is_even = lambda x: x % 2 == 0
        
        selector = factory.create_filter_selector(get_numbers, is_even)
        state = {'numbers': [1, 2, 3, 4, 5, 6]}
        
        result = selector(state)
        assert result == [2, 4, 6]
    
    def test_create_map_selector(self):
        """Test map selector creation."""
        factory = SelectorFactory()
        
        get_numbers = lambda state: state.get('numbers', [])
        double = lambda x: x * 2
        
        selector = factory.create_map_selector(get_numbers, double)
        state = {'numbers': [1, 2, 3]}
        
        result = selector(state)
        assert result == [2, 4, 6]
    
    def test_create_aggregation_selector(self):
        """Test aggregation selector creation."""
        factory = SelectorFactory()
        
        get_numbers = lambda state: state.get('numbers', [])
        sum_fn = lambda items: sum(items)
        
        selector = factory.create_aggregation_selector(get_numbers, sum_fn)
        state = {'numbers': [1, 2, 3, 4, 5]}
        
        result = selector(state)
        assert result == 15
    
    def test_create_parametric_filter_selector(self):
        """Test parametric filter selector creation."""
        factory = SelectorFactory()
        
        get_items = lambda state: state.get('items', [])
        selector = factory.create_parametric_filter_selector(get_items)
        
        state = {
            'items': [
                {'type': 'text', 'value': 'hello'},
                {'type': 'number', 'value': 42},
                {'type': 'text', 'value': 'world'}
            ]
        }
        
        result = selector(state, type='text')
        assert len(result) == 2
        assert all(item['type'] == 'text' for item in result)
    
    def test_create_sorted_selector(self):
        """Test sorted selector creation."""
        factory = SelectorFactory()
        
        get_items = lambda state: state.get('items', [])
        selector = factory.create_sorted_selector(get_items, 'value', reverse=True)
        
        state = {
            'items': [
                {'value': 1},
                {'value': 3},
                {'value': 2}
            ]
        }
        
        result = selector(state)
        assert [item['value'] for item in result] == [3, 2, 1]
    
    def test_factory_selector_caching(self):
        """Test that factory caches selectors by name."""
        factory = SelectorFactory()
        
        selector1 = factory.create_path_selector('test.path', name='test_selector')
        selector2 = factory.create_path_selector('test.path', name='test_selector')
        
        # Should return the same instance
        assert selector1 is selector2
        assert len(factory._created_selectors) == 1


class TestCommonSelectors:
    """Test common selector implementations."""
    
    def test_get_elements(self):
        """Test get_elements selector."""
        state = {'elements': [1, 2, 3], 'other': 'data'}
        result = get_elements(state)
        assert result == [1, 2, 3]
        
        # Test with empty state
        empty_state = {}
        result = get_elements(empty_state)
        assert result == []
    
    def test_get_visible_elements(self):
        """Test get_visible_elements selector."""
        state = {
            'elements': [
                {'id': 1, 'visible': True},
                {'id': 2, 'visible': False},
                {'id': 3},  # Missing visible property
                {'id': 4, 'visible': True}
            ]
        }
        
        result = get_visible_elements(state)
        
        # Should include elements with visible=True and missing visible property
        visible_ids = [elem['id'] for elem in result]
        assert visible_ids == [1, 3, 4]
    
    def test_get_elements_by_type(self):
        """Test parametric get_elements_by_type selector."""
        state = {
            'elements': [
                {'id': 1, 'type': 'text'},
                {'id': 2, 'type': 'image'},
                {'id': 3, 'type': 'text'},
                {'id': 4, 'type': 'table'}
            ]
        }
        
        result = get_elements_by_type(state, 'text')
        
        text_ids = [elem['id'] for elem in result]
        assert text_ids == [1, 3]


class TestSelectorPerformance:
    """Test selector performance characteristics."""
    
    def test_selector_performance_with_large_state(self):
        """Test selector performance with large state."""
        # Create large state
        large_elements = [{'id': i, 'value': i} for i in range(10000)]
        state = {'elements': large_elements}
        
        def get_high_value_elements(elements):
            return [elem for elem in elements if elem['value'] > 5000]
        
        selector = create_selector(get_elements, get_high_value_elements)
        
        # Time the execution
        start_time = time.perf_counter()
        result = selector(state)
        execution_time = (time.perf_counter() - start_time) * 1000
        
        # Verify result
        assert len(result) == 4999  # Elements with value 5001-9999
        
        # Check performance
        stats = selector.get_stats()
        assert stats['avg_execution_time_ms'] > 0
        assert execution_time < 100  # Should complete within 100ms
    
    def test_selector_cache_performance(self):
        """Test selector cache performance."""
        call_count = 0
        
        def expensive_computation(state):
            nonlocal call_count
            call_count += 1
            # Simulate expensive computation
            return sum(state.get('numbers', []))
        
        selector = Selector(expensive_computation)
        state = {'numbers': list(range(1000))}
        
        # First call
        result1 = selector(state)
        assert call_count == 1
        
        # Multiple subsequent calls should use cache
        for _ in range(100):
            result = selector(state)
            assert result == result1
        
        assert call_count == 1  # Function called only once
        
        stats = selector.get_stats()
        assert stats['cache_hit_rate'] > 99  # Should be >99%
    
    def test_selector_memory_efficiency(self):
        """Test selector memory efficiency."""
        import gc
        import sys
        
        def create_selector_with_large_result(multiplier):
            def large_computation(state):
                return [i * multiplier for i in range(1000)]
            return Selector(large_computation)
        
        # Create many selectors
        selectors = []
        for i in range(100):
            selector = create_selector_with_large_result(i)
            state = {'value': i}
            selector(state)  # Execute to populate cache
            selectors.append(selector)
        
        # Force garbage collection
        initial_objects = len(gc.get_objects())
        
        # Clear references
        selectors.clear()
        gc.collect()
        
        final_objects = len(gc.get_objects())
        
        # Memory should be properly cleaned up
        assert final_objects <= initial_objects + 100  # Allow some variance


if __name__ == '__main__':
    pytest.main([__file__])