"""
Tests for Render Batching System.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import QTimer

from torematrix.ui.components.render_batching import (
    RenderPriority,
    RenderTask,
    BatchStatistics,
    RenderScheduler,
    RenderBatcher,
    get_render_batcher,
    schedule_render,
    batch_render
)
from torematrix.ui.components.diffing import DiffPatch, DiffOperation


@pytest.fixture
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestRenderTask:
    """Test RenderTask functionality."""
    
    def test_render_task_creation(self):
        """Test creating render tasks."""
        widget = Mock(spec=QWidget)
        patches = [Mock(spec=DiffPatch)]
        
        task = RenderTask(
            widget=Mock(return_value=widget),
            patches=patches,
            priority=RenderPriority.HIGH
        )
        
        assert task.get_widget() == widget
        assert task.patches == patches
        assert task.priority == RenderPriority.HIGH
        assert task.timestamp > 0
    
    def test_render_task_comparison(self):
        """Test render task priority comparison."""
        widget = Mock(spec=QWidget)
        
        high_task = RenderTask(
            widget=Mock(return_value=widget),
            patches=[],
            priority=RenderPriority.HIGH
        )
        
        low_task = RenderTask(
            widget=Mock(return_value=widget),
            patches=[],
            priority=RenderPriority.LOW
        )
        
        # High priority should come first
        assert high_task < low_task
    
    def test_dead_widget_reference(self):
        """Test handling dead widget references."""
        task = RenderTask(
            widget=Mock(return_value=None),  # Dead reference
            patches=[]
        )
        
        assert task.get_widget() is None


class TestRenderScheduler:
    """Test RenderScheduler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scheduler = RenderScheduler(target_fps=60)
        self.scheduler._render_timer.stop()  # Stop auto-processing
    
    def test_schedule_render(self):
        """Test scheduling render tasks."""
        widget = Mock(spec=QWidget)
        patches = [Mock(spec=DiffPatch)]
        
        self.scheduler.schedule_render(widget, patches)
        
        assert id(widget) in self.scheduler._tasks
        assert len(self.scheduler._task_queue) == 1
    
    def test_merge_patches(self):
        """Test merging patches for same widget."""
        widget = Mock(spec=QWidget)
        patch1 = Mock(spec=DiffPatch)
        patch2 = Mock(spec=DiffPatch)
        
        self.scheduler.schedule_render(widget, [patch1])
        self.scheduler.schedule_render(widget, [patch2])
        
        # Should have merged into single task
        assert len(self.scheduler._tasks) == 1
        task = self.scheduler._tasks[id(widget)]
        assert len(task.patches) == 2
        assert patch1 in task.patches
        assert patch2 in task.patches
    
    def test_priority_upgrade(self):
        """Test priority upgrade when scheduling."""
        widget = Mock(spec=QWidget)
        
        self.scheduler.schedule_render(widget, [], RenderPriority.LOW)
        self.scheduler.schedule_render(widget, [], RenderPriority.HIGH)
        
        task = self.scheduler._tasks[id(widget)]
        assert task.priority == RenderPriority.HIGH
    
    def test_batch_processing(self):
        """Test batch processing of tasks."""
        # Create multiple tasks
        widgets = [Mock(spec=QWidget) for _ in range(5)]
        
        for i, widget in enumerate(widgets):
            priority = RenderPriority.HIGH if i == 0 else RenderPriority.NORMAL
            patch = Mock(spec=DiffPatch)
            patch.apply = Mock()
            
            self.scheduler.schedule_render(widget, [patch], priority)
        
        # Process batch
        self.scheduler._process_batch()
        
        # All patches should be applied
        for task in self.scheduler._task_queue:
            for patch in task.patches:
                patch.apply.assert_called_once()
    
    def test_frame_drop_detection(self):
        """Test frame drop detection."""
        self.scheduler._last_frame_time = time.time() - 0.1  # 100ms ago
        
        # Track frame drops
        frame_dropped = False
        self.scheduler.frame_dropped.connect(lambda: setattr(locals(), 'frame_dropped', True))
        
        self.scheduler._process_batch()
        
        assert self.scheduler._statistics.frame_drops == 1
    
    def test_statistics_update(self):
        """Test statistics tracking."""
        widget = Mock(spec=QWidget)
        patch = Mock(spec=DiffPatch)
        patch.apply = Mock()
        
        self.scheduler.schedule_render(widget, [patch])
        self.scheduler._process_batch()
        
        stats = self.scheduler.get_statistics()
        
        assert stats.total_batches == 1
        assert stats.total_renders == 1
        assert stats.patches_applied == 1
        assert stats.average_batch_size == 1.0
    
    def test_target_fps_change(self):
        """Test changing target FPS."""
        self.scheduler.set_target_fps(30)
        
        assert self.scheduler.target_fps == 30
        assert self.scheduler.frame_time == 1000 / 30
    
    def test_pause_resume(self):
        """Test pause and resume functionality."""
        self.scheduler.pause()
        assert not self.scheduler._render_timer.isActive()
        
        self.scheduler.resume()
        assert self.scheduler._render_timer.isActive()
    
    def test_flush(self):
        """Test flushing all pending renders."""
        widgets = [Mock(spec=QWidget) for _ in range(3)]
        
        for widget in widgets:
            patch = Mock(spec=DiffPatch)
            patch.apply = Mock()
            self.scheduler.schedule_render(widget, [patch])
        
        self.scheduler.flush()
        
        # All tasks should be processed
        assert len(self.scheduler._tasks) == 0
        assert len(self.scheduler._task_queue) == 0


class TestRenderBatcher:
    """Test RenderBatcher."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.batcher = RenderBatcher()
        self.batcher._scheduler._render_timer.stop()  # Stop auto-processing
    
    def test_request_render(self):
        """Test requesting widget render."""
        widget = Mock(spec=QWidget)
        widget.isEnabled.return_value = True
        widget.isVisible.return_value = True
        widget.geometry.return_value = Mock()
        
        # First render should proceed
        self.batcher.request_render(widget)
        
        # Check that state was captured
        assert widget in self.batcher._widget_states
    
    def test_should_render_memoization(self):
        """Test render memoization."""
        widget = Mock(spec=QWidget)
        widget.isEnabled.return_value = True
        widget.isVisible.return_value = True
        widget.geometry.return_value = Mock()
        
        state = {"enabled": True, "visible": True}
        
        # First check - not memoized
        should_render1 = self.batcher._should_render(widget, state)
        
        # Second check - memoized
        should_render2 = self.batcher._should_render(widget, state)
        
        # Should have memoization entry
        assert len(self.batcher._memoization_cache) > 0
    
    def test_batch_update(self):
        """Test batch updating multiple widgets."""
        widgets = [Mock(spec=QWidget) for _ in range(3)]
        
        for widget in widgets:
            widget.isEnabled.return_value = True
            widget.isVisible.return_value = True
            widget.geometry.return_value = Mock()
        
        self.batcher.batch_update(widgets, RenderPriority.HIGH)
        
        # All widgets should be scheduled
        for widget in widgets:
            assert widget in self.batcher._widget_states
    
    def test_capture_widget_state(self):
        """Test capturing widget state."""
        widget = Mock(spec=QWidget)
        widget.isEnabled.return_value = True
        widget.isVisible.return_value = False
        widget.geometry.return_value = Mock()
        widget.text.return_value = "Test"
        widget.value.return_value = 42
        
        state = self.batcher._capture_widget_state(widget)
        
        assert state["enabled"] is True
        assert state["visible"] is False
        assert state["text"] == "Test"
        assert state["value"] == 42
    
    def test_invalidate_memoization(self):
        """Test invalidating memoization cache."""
        widget = Mock(spec=QWidget)
        
        # Add some cache entries
        self.batcher._memoization_cache[(id(widget), "hash1")] = True
        self.batcher._memoization_cache[(id(widget), "hash2")] = False
        self.batcher._memoization_cache[(999, "hash3")] = True
        
        # Invalidate specific widget
        self.batcher.invalidate_memoization(widget)
        
        assert (id(widget), "hash1") not in self.batcher._memoization_cache
        assert (id(widget), "hash2") not in self.batcher._memoization_cache
        assert (999, "hash3") in self.batcher._memoization_cache
        
        # Invalidate all
        self.batcher.invalidate_memoization()
        assert len(self.batcher._memoization_cache) == 0
    
    def test_get_statistics(self):
        """Test getting comprehensive statistics."""
        stats = self.batcher.get_statistics()
        
        assert "scheduler" in stats
        assert "memoization" in stats
        assert "total_batches" in stats["scheduler"]
        assert "cache_size" in stats["memoization"]


class TestGlobalFunctions:
    """Test global functions."""
    
    def test_get_render_batcher(self):
        """Test getting global render batcher."""
        batcher1 = get_render_batcher()
        batcher2 = get_render_batcher()
        
        assert batcher1 is batcher2
        assert isinstance(batcher1, RenderBatcher)
    
    def test_schedule_render(self):
        """Test global schedule_render function."""
        widget = Mock(spec=QWidget)
        widget.isEnabled.return_value = True
        widget.isVisible.return_value = True
        widget.geometry.return_value = Mock()
        
        schedule_render(widget, RenderPriority.HIGH)
        
        # Should be scheduled in global batcher
        batcher = get_render_batcher()
        assert widget in batcher._widget_states
    
    def test_batch_render(self):
        """Test global batch_render function."""
        widgets = [Mock(spec=QWidget) for _ in range(2)]
        
        for widget in widgets:
            widget.isEnabled.return_value = True
            widget.isVisible.return_value = True
            widget.geometry.return_value = Mock()
        
        batch_render(widgets, RenderPriority.NORMAL)
        
        # All should be scheduled
        batcher = get_render_batcher()
        for widget in widgets:
            assert widget in batcher._widget_states