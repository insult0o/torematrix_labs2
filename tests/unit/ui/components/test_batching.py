"""
Tests for State Change Batching System.
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from collections import deque

from tore_matrix_labs.ui.components.batching import (
    UpdatePriority,
    StateChange,
    BatchedUpdate,
    BatchingStrategy,
    TimeBatchingStrategy,
    AdaptiveBatchingStrategy,
    BatchProcessor,
    DebouncedUpdater,
    get_batch_processor,
    batch_state_change
)


class TestUpdatePriority:
    """Test the UpdatePriority enum."""
    
    def test_priority_order(self):
        """Test that priorities have correct order."""
        priorities = list(UpdatePriority)
        
        # Verify all priorities exist
        assert UpdatePriority.IMMEDIATE in priorities
        assert UpdatePriority.HIGH in priorities
        assert UpdatePriority.NORMAL in priorities
        assert UpdatePriority.LOW in priorities
        assert UpdatePriority.IDLE in priorities
        
        # Verify value ordering (lower value = higher priority)
        assert UpdatePriority.IMMEDIATE.value < UpdatePriority.HIGH.value
        assert UpdatePriority.HIGH.value < UpdatePriority.NORMAL.value
        assert UpdatePriority.NORMAL.value < UpdatePriority.LOW.value
        assert UpdatePriority.LOW.value < UpdatePriority.IDLE.value


class TestStateChange:
    """Test the StateChange dataclass."""
    
    def test_state_change_creation(self):
        """Test creating a state change."""
        change = StateChange(
            store_id='test_store',
            key='user.name',
            value='John',
            timestamp=time.time(),
            priority=UpdatePriority.NORMAL
        )
        
        assert change.store_id == 'test_store'
        assert change.key == 'user.name'
        assert change.value == 'John'
        assert change.priority == UpdatePriority.NORMAL
    
    def test_state_change_hash(self):
        """Test state change hashing for deduplication."""
        change1 = StateChange(
            store_id='store1',
            key='key1',
            value='value1',
            timestamp=1.0
        )
        
        change2 = StateChange(
            store_id='store1',
            key='key1',
            value='value2',
            timestamp=2.0
        )
        
        # Same store and key should have same hash
        assert hash(change1) == hash(change2)
        
        # Different store or key should have different hash
        change3 = StateChange(
            store_id='store2',
            key='key1',
            value='value1',
            timestamp=1.0
        )
        
        assert hash(change1) != hash(change3)


class TestBatchedUpdate:
    """Test the BatchedUpdate dataclass."""
    
    def test_batched_update_creation(self):
        """Test creating a batched update."""
        changes = [
            StateChange('store1', 'key1', 'value1', 1.0),
            StateChange('store1', 'key2', 'value2', 2.0)
        ]
        callback = Mock()
        
        batch = BatchedUpdate(
            changes=changes,
            callback=callback,
            timestamp=1.0,
            priority=UpdatePriority.NORMAL
        )
        
        assert len(batch.changes) == 2
        assert batch.callback == callback
        assert batch.timestamp == 1.0
        assert batch.priority == UpdatePriority.NORMAL
    
    def test_merge_with(self):
        """Test merging batched updates."""
        # First batch
        changes1 = [
            StateChange('store1', 'key1', 'value1', 1.0),
            StateChange('store1', 'key2', 'value2', 1.0)
        ]
        batch1 = BatchedUpdate(
            changes=changes1,
            callback=Mock(),
            timestamp=1.0,
            priority=UpdatePriority.NORMAL
        )
        
        # Second batch with overlapping keys
        changes2 = [
            StateChange('store1', 'key1', 'value1_new', 2.0),  # Updated
            StateChange('store1', 'key3', 'value3', 2.0)      # New
        ]
        batch2 = BatchedUpdate(
            changes=changes2,
            callback=Mock(),
            timestamp=2.0,
            priority=UpdatePriority.HIGH
        )
        
        # Merge
        merged = batch1.merge_with(batch2)
        
        # Should have 3 unique keys
        assert len(merged.changes) == 3
        
        # Should keep latest values
        key1_change = next(c for c in merged.changes if c.key == 'key1')
        assert key1_change.value == 'value1_new'
        assert key1_change.timestamp == 2.0
        
        # Should use earliest timestamp and highest priority
        assert merged.timestamp == 1.0
        assert merged.priority == UpdatePriority.HIGH


class TestTimeBatchingStrategy:
    """Test the TimeBatchingStrategy class."""
    
    def test_default_delays(self):
        """Test default delay values."""
        strategy = TimeBatchingStrategy()
        
        assert strategy.get_delay(UpdatePriority.IMMEDIATE) == 0.0
        assert strategy.get_delay(UpdatePriority.HIGH) == 0.016
        assert strategy.get_delay(UpdatePriority.NORMAL) == 0.050
        assert strategy.get_delay(UpdatePriority.LOW) == 0.100
        assert strategy.get_delay(UpdatePriority.IDLE) == 0.500
    
    def test_custom_delays(self):
        """Test custom delay values."""
        strategy = TimeBatchingStrategy(
            high_delay=0.01,
            normal_delay=0.02,
            low_delay=0.05
        )
        
        assert strategy.get_delay(UpdatePriority.HIGH) == 0.01
        assert strategy.get_delay(UpdatePriority.NORMAL) == 0.02
        assert strategy.get_delay(UpdatePriority.LOW) == 0.05
    
    def test_should_flush_immediate(self):
        """Test that immediate priority always flushes."""
        strategy = TimeBatchingStrategy()
        
        batch = BatchedUpdate(
            changes=[],
            callback=Mock(),
            timestamp=time.time(),
            priority=UpdatePriority.IMMEDIATE
        )
        
        assert strategy.should_flush(batch, time.time()) is True
    
    def test_should_flush_time_based(self):
        """Test time-based flushing."""
        strategy = TimeBatchingStrategy(normal_delay=0.05)
        
        current_time = time.time()
        batch = BatchedUpdate(
            changes=[],
            callback=Mock(),
            timestamp=current_time - 0.03,  # 30ms ago
            priority=UpdatePriority.NORMAL
        )
        
        # Should not flush yet
        assert strategy.should_flush(batch, current_time) is False
        
        # Should flush after delay
        assert strategy.should_flush(batch, current_time + 0.03) is True
    
    def test_should_flush_size_based(self):
        """Test size-based flushing."""
        strategy = TimeBatchingStrategy(max_batch_size=3)
        
        # Create batch with many changes
        changes = [
            StateChange(f'store', f'key{i}', f'value{i}', time.time())
            for i in range(5)
        ]
        
        batch = BatchedUpdate(
            changes=changes,
            callback=Mock(),
            timestamp=time.time(),
            priority=UpdatePriority.NORMAL
        )
        
        # Should flush due to size
        assert strategy.should_flush(batch, time.time()) is True


class TestAdaptiveBatchingStrategy:
    """Test the AdaptiveBatchingStrategy class."""
    
    def test_adaptive_initialization(self):
        """Test initializing adaptive strategy."""
        base_strategy = TimeBatchingStrategy()
        adaptive = AdaptiveBatchingStrategy(base_strategy)
        
        assert adaptive.base_strategy is base_strategy
        assert adaptive.load_factor == 1.0
        assert isinstance(adaptive.recent_flush_times, deque)
    
    def test_adaptive_delay_adjustment(self):
        """Test that delays are adjusted by load factor."""
        base_strategy = TimeBatchingStrategy(normal_delay=0.05)
        adaptive = AdaptiveBatchingStrategy(base_strategy)
        
        # Set load factor
        adaptive.load_factor = 2.0
        
        # Delay should be multiplied by load factor
        assert adaptive.get_delay(UpdatePriority.NORMAL) == 0.1
    
    def test_record_flush(self):
        """Test recording flush events."""
        adaptive = AdaptiveBatchingStrategy(TimeBatchingStrategy())
        
        # Record some flushes
        for i in range(5):
            adaptive.record_flush(i * 0.01)
        
        assert len(adaptive.recent_flush_times) == 5
    
    def test_load_factor_adjustment(self):
        """Test load factor adjustment based on activity."""
        adaptive = AdaptiveBatchingStrategy(TimeBatchingStrategy())
        
        # Simulate high frequency flushes
        current_time = time.time()
        for i in range(10):
            adaptive.record_flush(current_time + i * 0.005)  # 5ms apart
        
        adaptive._update_load_factor()
        
        # Load factor should increase for high frequency
        assert adaptive.load_factor > 1.0
        
        # Simulate low frequency flushes
        adaptive.recent_flush_times.clear()
        for i in range(10):
            adaptive.record_flush(current_time + i * 0.2)  # 200ms apart
        
        adaptive._update_load_factor()
        
        # Load factor should decrease for low frequency
        assert adaptive.load_factor < 1.0


class TestBatchProcessor:
    """Test the BatchProcessor class."""
    
    def test_processor_initialization(self):
        """Test initializing batch processor."""
        processor = BatchProcessor(worker_thread=False)
        
        assert isinstance(processor.strategy, TimeBatchingStrategy)
        assert not processor._running
        assert len(processor.batches) == 0
    
    def test_start_stop(self):
        """Test starting and stopping processor."""
        processor = BatchProcessor(worker_thread=False)
        
        processor.start()
        assert processor._running is True
        assert processor._worker_thread is not None
        
        processor.stop()
        assert processor._running is False
    
    def test_add_change_immediate(self):
        """Test adding immediate priority change."""
        processor = BatchProcessor(worker_thread=False)
        callback = Mock()
        
        processor.add_change(
            store_id='store1',
            key='key1',
            value='value1',
            priority=UpdatePriority.IMMEDIATE,
            callback=callback
        )
        
        # Immediate changes should be processed immediately
        callback.assert_called_once()
        changes = callback.call_args[0][0]
        assert len(changes) == 1
        assert changes[0].key == 'key1'
    
    def test_add_change_batched(self):
        """Test adding batched changes."""
        processor = BatchProcessor(worker_thread=False)
        callback = Mock()
        
        # Add multiple changes
        for i in range(3):
            processor.add_change(
                store_id='store1',
                key=f'key{i}',
                value=f'value{i}',
                priority=UpdatePriority.NORMAL,
                callback=callback
            )
        
        # Should not be called immediately
        callback.assert_not_called()
        
        # Should have one batch
        assert len(processor.batches) == 1
        
        # Force flush
        processor.flush(force=True)
        
        # Callback should be called with all changes
        callback.assert_called_once()
        changes = callback.call_args[0][0]
        assert len(changes) == 3
    
    def test_change_merging(self):
        """Test that changes to same key are merged."""
        processor = BatchProcessor(worker_thread=False)
        callback = Mock()
        
        # Add multiple changes to same key
        processor.add_change('store1', 'key1', 'value1', callback=callback)
        processor.add_change('store1', 'key1', 'value2', callback=callback)
        processor.add_change('store1', 'key1', 'value3', callback=callback)
        
        # Force flush
        processor.flush(force=True)
        
        # Should only have latest value
        callback.assert_called_once()
        changes = callback.call_args[0][0]
        assert len(changes) == 1
        assert changes[0].value == 'value3'
    
    def test_batch_context(self):
        """Test batch context manager."""
        processor = BatchProcessor(worker_thread=True)
        callback = Mock()
        
        with processor.batch_context():
            # Add changes
            for i in range(5):
                processor.add_change(
                    store_id='store1',
                    key=f'key{i}',
                    value=f'value{i}',
                    callback=callback
                )
            
            # Should not be processed yet
            callback.assert_not_called()
        
        # Should be flushed on exit
        callback.assert_called_once()
        changes = callback.call_args[0][0]
        assert len(changes) == 5
        
        processor.stop()
    
    def test_flush_with_strategy(self):
        """Test that flush respects strategy."""
        strategy = TimeBatchingStrategy(normal_delay=0.1)
        processor = BatchProcessor(strategy=strategy, worker_thread=False)
        callback = Mock()
        
        # Add change
        processor.add_change(
            store_id='store1',
            key='key1',
            value='value1',
            priority=UpdatePriority.NORMAL,
            callback=callback
        )
        
        # Flush without force - should not flush yet
        processor.flush(force=False)
        callback.assert_not_called()
        
        # Wait for delay and flush
        time.sleep(0.15)
        processor.flush(force=False)
        callback.assert_called_once()


class TestDebouncedUpdater:
    """Test the DebouncedUpdater class."""
    
    def test_debounced_update(self):
        """Test basic debouncing."""
        callback = Mock()
        updater = DebouncedUpdater(callback, delay=0.05)
        
        # Multiple rapid updates
        updater.update('value1')
        updater.update('value2')
        updater.update('value3')
        
        # Should not be called immediately
        callback.assert_not_called()
        
        # Wait for debounce delay
        time.sleep(0.1)
        
        # Should be called with last value
        callback.assert_called_once_with('value3')
    
    def test_max_wait(self):
        """Test max wait time."""
        callback = Mock()
        updater = DebouncedUpdater(callback, delay=0.1, max_wait=0.15)
        
        # Keep updating
        start_time = time.time()
        while time.time() - start_time < 0.2:
            updater.update(f'value_{time.time()}')
            time.sleep(0.05)
        
        # Should have been called due to max_wait
        assert callback.call_count >= 1
    
    def test_cancel(self):
        """Test cancelling pending updates."""
        callback = Mock()
        updater = DebouncedUpdater(callback, delay=0.05)
        
        updater.update('value1')
        updater.cancel()
        
        # Wait longer than delay
        time.sleep(0.1)
        
        # Should not be called
        callback.assert_not_called()
    
    def test_error_handling(self):
        """Test that errors in callback are handled."""
        def failing_callback(value):
            raise RuntimeError("Callback error")
        
        updater = DebouncedUpdater(failing_callback, delay=0.05)
        
        # Should not raise
        updater.update('value1')
        time.sleep(0.1)


class TestGlobalFunctions:
    """Test global functions."""
    
    def test_get_batch_processor(self):
        """Test getting global batch processor."""
        processor1 = get_batch_processor()
        processor2 = get_batch_processor()
        
        assert processor1 is processor2
        assert isinstance(processor1, BatchProcessor)
        
        # Clean up
        processor1.stop()
    
    def test_batch_state_change(self):
        """Test global batch_state_change function."""
        # Mock the global processor
        mock_processor = Mock()
        
        with patch('tore_matrix_labs.ui.components.batching.get_batch_processor',
                   return_value=mock_processor):
            
            batch_state_change(
                store_id='store1',
                key='key1',
                value='value1',
                priority=UpdatePriority.HIGH
            )
            
            mock_processor.add_change.assert_called_once_with(
                store_id='store1',
                key='key1',
                value='value1',
                priority=UpdatePriority.HIGH,
                callback=None
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])