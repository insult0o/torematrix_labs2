"""
Tests for Update Optimization System.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QWidget

from torematrix.ui.components.optimization import (
    MemoizationEntry,
    ComponentMemoizer,
    memoize_render,
    RenderOptimizer,
    UpdateBatcher,
    SmartUpdateDetector,
    get_render_optimizer,
    get_update_batcher,
    get_smart_detector,
    _deep_equal
)


class TestMemoizationEntry:
    """Test MemoizationEntry functionality."""
    
    def test_memoization_entry_creation(self):
        """Test creating memoization entries."""
        entry = MemoizationEntry(
            result="cached_result",
            timestamp=time.time(),
            dependencies={"dep1", "dep2"}
        )
        
        assert entry.result == "cached_result"
        assert entry.hit_count == 0
        assert "dep1" in entry.dependencies
        assert "dep2" in entry.dependencies
    
    def test_is_valid_no_max_age(self):
        """Test validity check without max age."""
        entry = MemoizationEntry(
            result="result",
            timestamp=time.time() - 1000  # Old timestamp
        )
        
        assert entry.is_valid()  # Should always be valid without max_age
    
    def test_is_valid_with_max_age(self):
        """Test validity check with max age."""
        current_time = time.time()
        
        # Recent entry
        recent_entry = MemoizationEntry(
            result="result",
            timestamp=current_time - 5
        )
        assert recent_entry.is_valid(max_age=10)  # Valid within 10 seconds
        
        # Old entry
        old_entry = MemoizationEntry(
            result="result",
            timestamp=current_time - 20
        )
        assert not old_entry.is_valid(max_age=10)  # Invalid after 10 seconds


class TestComponentMemoizer:
    """Test ComponentMemoizer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.memoizer = ComponentMemoizer(max_entries=10)
    
    def test_memoize_computation(self):
        """Test memoizing computation results."""
        compute_count = 0
        
        def compute():
            nonlocal compute_count
            compute_count += 1
            return f"result_{compute_count}"
        
        # First call - cache miss
        result1 = self.memoizer.memoize("key1", compute)
        assert result1 == "result_1"
        assert compute_count == 1
        assert self.memoizer._stats["misses"] == 1
        assert self.memoizer._stats["hits"] == 0
        
        # Second call - cache hit
        result2 = self.memoizer.memoize("key1", compute)
        assert result2 == "result_1"  # Same result
        assert compute_count == 1  # Not computed again
        assert self.memoizer._stats["hits"] == 1
    
    def test_memoize_with_dependencies(self):
        """Test memoization with dependencies."""
        result = self.memoizer.memoize(
            "key1",
            lambda: "result",
            dependencies={"state.value", "props.text"}
        )
        
        assert "key1" in self.memoizer._cache
        entry = self.memoizer._cache["key1"]
        assert "state.value" in entry.dependencies
        assert "props.text" in entry.dependencies
    
    def test_invalidate_specific_key(self):
        """Test invalidating specific cache key."""
        self.memoizer.memoize("key1", lambda: "result1")
        self.memoizer.memoize("key2", lambda: "result2")
        
        self.memoizer.invalidate("key1")
        
        assert "key1" not in self.memoizer._cache
        assert "key2" in self.memoizer._cache
    
    def test_invalidate_by_dependency(self):
        """Test invalidating by dependency."""
        self.memoizer.memoize("key1", lambda: "r1", dependencies={"dep1", "dep2"})
        self.memoizer.memoize("key2", lambda: "r2", dependencies={"dep2", "dep3"})
        self.memoizer.memoize("key3", lambda: "r3", dependencies={"dep3"})
        
        self.memoizer.invalidate(dependency="dep2")
        
        # key1 and key2 should be invalidated
        assert "key1" not in self.memoizer._cache
        assert "key2" not in self.memoizer._cache
        assert "key3" in self.memoizer._cache
    
    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        # Fill cache to max
        for i in range(10):
            self.memoizer.memoize(f"key{i}", lambda i=i: f"result{i}")
        
        assert len(self.memoizer._cache) == 10
        
        # Add one more - should evict oldest
        self.memoizer.memoize("key10", lambda: "result10")
        
        assert len(self.memoizer._cache) == 10
        assert "key0" not in self.memoizer._cache  # First one evicted
        assert "key10" in self.memoizer._cache
        assert self.memoizer._stats["evictions"] == 1
    
    def test_get_stats(self):
        """Test getting memoization statistics."""
        # Generate some activity
        self.memoizer.memoize("key1", lambda: "r1")
        self.memoizer.memoize("key1", lambda: "r1")  # Hit
        self.memoizer.memoize("key2", lambda: "r2")
        
        stats = self.memoizer.get_stats()
        
        assert stats["hits"] == 1
        assert stats["misses"] == 2
        assert stats["hit_rate"] == 1/3
        assert stats["cache_size"] == 2
        assert stats["max_entries"] == 10


class TestMemoizeRenderDecorator:
    """Test memoize_render decorator."""
    
    def test_memoize_render_decorator(self):
        """Test memoizing render functions."""
        render_count = 0
        
        class TestWidget:
            @memoize_render(max_age=10)
            def render(self, text):
                nonlocal render_count
                render_count += 1
                return f"Rendered: {text}"
        
        widget = TestWidget()
        
        # First render
        result1 = widget.render("Hello")
        assert result1 == "Rendered: Hello"
        assert render_count == 1
        
        # Same args - should use cache
        result2 = widget.render("Hello")
        assert result2 == "Rendered: Hello"
        assert render_count == 1  # Not incremented
        
        # Different args - new computation
        result3 = widget.render("World")
        assert result3 == "Rendered: World"
        assert render_count == 2
    
    def test_memoize_with_dependencies(self):
        """Test memoize decorator with dependencies."""
        class TestWidget:
            @memoize_render(dependencies=["state.value"])
            def render(self):
                return "Rendered"
        
        widget = TestWidget()
        result = widget.render()
        
        # Check that memoizer is attached
        assert hasattr(widget.render, "memoizer")
        assert isinstance(widget.render.memoizer, ComponentMemoizer)


class TestRenderOptimizer:
    """Test RenderOptimizer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.optimizer = RenderOptimizer()
    
    def test_should_component_update_first_render(self):
        """Test should update check for first render."""
        widget = Mock(spec=QWidget)
        widget.__class__.__name__ = "TestWidget"
        
        should_update = self.optimizer.should_component_update(
            widget,
            {"text": "Hello"},
            {"value": 42}
        )
        
        assert should_update  # First render always updates
        assert widget in self.optimizer._prop_checksums
    
    def test_should_component_update_no_changes(self):
        """Test should update with no changes."""
        widget = Mock(spec=QWidget)
        widget.__class__.__name__ = "TestWidget"
        
        props = {"text": "Hello"}
        state = {"value": 42}
        
        # First render
        self.optimizer.should_component_update(widget, props, state)
        
        # Same props/state
        should_update = self.optimizer.should_component_update(widget, props, state)
        
        assert not should_update  # No changes, no update
        assert self.optimizer._skip_counts["TestWidget"] == 1
    
    def test_should_component_update_prop_change(self):
        """Test should update with prop change."""
        widget = Mock(spec=QWidget)
        
        # First render
        self.optimizer.should_component_update(
            widget,
            {"text": "Hello"},
            {"value": 42}
        )
        
        # Changed prop
        should_update = self.optimizer.should_component_update(
            widget,
            {"text": "World"},  # Changed
            {"value": 42}
        )
        
        assert should_update
    
    def test_should_component_update_state_change(self):
        """Test should update with state change."""
        widget = Mock(spec=QWidget)
        
        # First render
        self.optimizer.should_component_update(
            widget,
            {"text": "Hello"},
            {"value": 42}
        )
        
        # Changed state
        should_update = self.optimizer.should_component_update(
            widget,
            {"text": "Hello"},
            {"value": 100}  # Changed
        )
        
        assert should_update
    
    def test_optimization_stats(self):
        """Test getting optimization statistics."""
        widget1 = Mock(spec=QWidget)
        widget1.__class__.__name__ = "Widget1"
        widget2 = Mock(spec=QWidget)
        widget2.__class__.__name__ = "Widget2"
        
        # Generate some skips
        props = {"a": 1}
        state = {"b": 2}
        
        for widget in [widget1, widget2]:
            self.optimizer.should_component_update(widget, props, state)
            self.optimizer.should_component_update(widget, props, state)  # Skip
            self.optimizer.should_component_update(widget, props, state)  # Skip
        
        stats = self.optimizer.get_optimization_stats()
        
        assert stats["total_skips"] == 4
        assert stats["skips_by_component"]["Widget1"] == 2
        assert stats["skips_by_component"]["Widget2"] == 2
        assert stats["cached_widgets"] == 2


class TestUpdateBatcher:
    """Test UpdateBatcher."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.batcher = UpdateBatcher()
    
    def test_batch_update(self):
        """Test batching updates."""
        widget = Mock(spec=QWidget)
        
        updates = [
            ("prop1", "value1"),
            ("prop2", "value2"),
            ("prop3", "value3")
        ]
        
        self.batcher.batch_update(widget, updates)
        
        widget_id = id(widget)
        assert widget_id in self.batcher._pending_updates
        assert len(self.batcher._pending_updates[widget_id]) == 3
    
    def test_batch_update_with_callback(self):
        """Test batching with callback."""
        widget = Mock(spec=QWidget)
        callback = Mock()
        
        self.batcher.batch_update(widget, [("prop", "value")], callback)
        
        widget_id = id(widget)
        assert widget_id in self.batcher._update_callbacks
        assert self.batcher._update_callbacks[widget_id] == callback
    
    def test_flush_specific_widget(self):
        """Test flushing updates for specific widget."""
        widget1 = Mock(spec=QWidget)
        widget2 = Mock(spec=QWidget)
        callback1 = Mock()
        callback2 = Mock()
        
        self.batcher.batch_update(widget1, [("p1", "v1")], callback1)
        self.batcher.batch_update(widget2, [("p2", "v2")], callback2)
        
        # Flush only widget1
        flushed = self.batcher.flush_updates(widget1)
        
        assert id(widget1) in flushed
        assert id(widget2) not in flushed
        callback1.assert_called_once()
        callback2.assert_not_called()
        
        # widget2 still pending
        assert self.batcher.has_pending_updates(widget2)
    
    def test_flush_all(self):
        """Test flushing all updates."""
        widgets = [Mock(spec=QWidget) for _ in range(3)]
        callbacks = [Mock() for _ in range(3)]
        
        for widget, callback in zip(widgets, callbacks):
            self.batcher.batch_update(widget, [("p", "v")], callback)
        
        flushed = self.batcher.flush_updates()
        
        assert len(flushed) == 3
        for callback in callbacks:
            callback.assert_called_once()
        
        assert not self.batcher.has_pending_updates()


class TestSmartUpdateDetector:
    """Test SmartUpdateDetector."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.detector = SmartUpdateDetector()
    
    def test_has_changed_first_time(self):
        """Test change detection for first time values."""
        widget = Mock(spec=QWidget)
        
        changed = self.detector.has_changed(widget, "prop1", "value1")
        
        assert changed  # First time is always changed
        assert widget in self.detector._previous_values
    
    def test_has_changed_same_value(self):
        """Test no change for same value."""
        widget = Mock(spec=QWidget)
        
        self.detector.has_changed(widget, "prop1", "value1")
        changed = self.detector.has_changed(widget, "prop1", "value1")
        
        assert not changed
    
    def test_has_changed_different_value(self):
        """Test change detection for different value."""
        widget = Mock(spec=QWidget)
        
        self.detector.has_changed(widget, "prop1", "value1")
        changed = self.detector.has_changed(widget, "prop1", "value2")
        
        assert changed
    
    def test_track_values(self):
        """Test tracking multiple values."""
        widget = Mock(spec=QWidget)
        
        # First set of values
        values1 = {"prop1": "v1", "prop2": "v2", "prop3": "v3"}
        changed1 = self.detector.track_values(widget, values1)
        
        assert len(changed1) == 3  # All new
        
        # Second set with some changes
        values2 = {"prop1": "v1", "prop2": "v2_new", "prop3": "v3"}
        changed2 = self.detector.track_values(widget, values2)
        
        assert len(changed2) == 1
        assert "prop2" in changed2


class TestDeepEqual:
    """Test deep equality function."""
    
    def test_deep_equal_primitives(self):
        """Test deep equal for primitives."""
        assert _deep_equal(1, 1)
        assert _deep_equal("hello", "hello")
        assert not _deep_equal(1, 2)
        assert not _deep_equal(1, "1")
    
    def test_deep_equal_lists(self):
        """Test deep equal for lists."""
        assert _deep_equal([1, 2, 3], [1, 2, 3])
        assert not _deep_equal([1, 2, 3], [1, 2])
        assert not _deep_equal([1, 2, 3], [1, 3, 2])
    
    def test_deep_equal_dicts(self):
        """Test deep equal for dictionaries."""
        assert _deep_equal({"a": 1, "b": 2}, {"b": 2, "a": 1})
        assert not _deep_equal({"a": 1}, {"a": 2})
        assert not _deep_equal({"a": 1}, {"b": 1})
    
    def test_deep_equal_nested(self):
        """Test deep equal for nested structures."""
        struct1 = {"list": [1, 2, {"nested": True}]}
        struct2 = {"list": [1, 2, {"nested": True}]}
        struct3 = {"list": [1, 2, {"nested": False}]}
        
        assert _deep_equal(struct1, struct2)
        assert not _deep_equal(struct1, struct3)


class TestGlobalInstances:
    """Test global instance functions."""
    
    def test_get_render_optimizer(self):
        """Test getting global render optimizer."""
        opt1 = get_render_optimizer()
        opt2 = get_render_optimizer()
        
        assert opt1 is opt2
        assert isinstance(opt1, RenderOptimizer)
    
    def test_get_update_batcher(self):
        """Test getting global update batcher."""
        batcher1 = get_update_batcher()
        batcher2 = get_update_batcher()
        
        assert batcher1 is batcher2
        assert isinstance(batcher1, UpdateBatcher)
    
    def test_get_smart_detector(self):
        """Test getting global smart detector."""
        detector1 = get_smart_detector()
        detector2 = get_smart_detector()
        
        assert detector1 is detector2
        assert isinstance(detector1, SmartUpdateDetector)