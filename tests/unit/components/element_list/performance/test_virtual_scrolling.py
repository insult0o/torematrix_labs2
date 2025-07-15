"""
Tests for Virtual Scrolling Engine

Comprehensive test suite for virtual scrolling performance optimization.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtCore import QRect, QModelIndex, QTimer
from PyQt6.QtWidgets import QTreeView, QApplication, QScrollBar
from PyQt6.QtGui import QPainter

from src.torematrix.ui.components.element_list.performance.virtual_scrolling import (
    VirtualScrollingEngine, ViewportManager, ItemRenderer,
    ScrollMetrics, RenderBatch, VirtualItemInfo
)


@pytest.fixture
def mock_tree_view():
    """Create mock tree view."""
    tree_view = Mock(spec=QTreeView)
    tree_view.model.return_value = Mock()
    tree_view.viewport.return_value = Mock()
    tree_view.verticalScrollBar.return_value = Mock(spec=QScrollBar)
    tree_view.horizontalScrollBar.return_value = Mock(spec=QScrollBar)
    tree_view.visualRect.return_value = QRect(0, 0, 200, 25)
    tree_view.sizeHint.return_value = Mock()
    tree_view.sizeHint.return_value.height.return_value = 25
    return tree_view


@pytest.fixture
def mock_model():
    """Create mock model with test data."""
    model = Mock()
    model.rowCount.return_value = 1000  # Large dataset
    model.index.side_effect = lambda row, col, parent=None: Mock(row=row, column=col)
    model.data.return_value = f"Item {model.index().row}"
    return model


class TestScrollMetrics:
    """Test scroll metrics tracking."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = ScrollMetrics()
        
        assert metrics.viewport_top == 0
        assert metrics.viewport_bottom == 0
        assert metrics.total_height == 0
        assert metrics.item_height == 25
        assert metrics.visible_count == 0
        assert metrics.buffer_size == 10
    
    def test_update_viewport(self):
        """Test viewport update."""
        metrics = ScrollMetrics()
        
        metrics.update_viewport(100, 500, 10000, 25)
        
        assert metrics.viewport_top == 100
        assert metrics.viewport_bottom == 500
        assert metrics.total_height == 10000
        assert metrics.item_height == 25
        assert metrics.visible_count == 16  # (500-100)/25 = 16
    
    def test_calculate_visible_range(self):
        """Test visible range calculation."""
        metrics = ScrollMetrics()
        metrics.update_viewport(100, 500, 10000, 25)
        
        start_index, end_index = metrics.calculate_visible_range()
        
        assert start_index == 4  # 100/25 = 4
        assert end_index == 20  # 500/25 = 20
    
    def test_calculate_render_range_with_buffer(self):
        """Test render range with buffer."""
        metrics = ScrollMetrics()
        metrics.update_viewport(250, 750, 10000, 25)  # Items 10-30 visible
        
        start_index, end_index = metrics.calculate_render_range()
        
        assert start_index == 0   # max(0, 10-10) = 0
        assert end_index == 40    # min(400, 30+10) = 40
        
        # Test with total items limit
        metrics.total_items = 35
        start_index, end_index = metrics.calculate_render_range()
        assert end_index == 35    # Limited by total items


class TestVirtualItemInfo:
    """Test virtual item information."""
    
    def test_item_info_creation(self):
        """Test creating virtual item info."""
        info = VirtualItemInfo(
            index=5,
            y_position=125,
            height=25,
            visible=True
        )
        
        assert info.index == 5
        assert info.y_position == 125
        assert info.height == 25
        assert info.visible is True
    
    def test_item_bounds(self):
        """Test item bounds calculation."""
        info = VirtualItemInfo(
            index=5,
            y_position=125,
            height=25,
            visible=True
        )
        
        bounds = info.get_bounds()
        assert bounds.top() == 125
        assert bounds.bottom() == 150
        assert bounds.height() == 25


class TestRenderBatch:
    """Test render batch management."""
    
    def test_batch_creation(self):
        """Test creating render batch."""
        items = [
            VirtualItemInfo(0, 0, 25, True),
            VirtualItemInfo(1, 25, 25, True),
            VirtualItemInfo(2, 50, 25, True)
        ]
        
        batch = RenderBatch("test_batch", items, 0, 75)
        
        assert batch.batch_id == "test_batch"
        assert len(batch.items) == 3
        assert batch.start_y == 0
        assert batch.end_y == 75
    
    def test_batch_bounds(self):
        """Test batch bounds."""
        items = [
            VirtualItemInfo(0, 0, 25, True),
            VirtualItemInfo(1, 25, 25, True),
            VirtualItemInfo(2, 50, 25, True)
        ]
        
        batch = RenderBatch("test_batch", items, 0, 75)
        bounds = batch.get_bounds()
        
        assert bounds.top() == 0
        assert bounds.bottom() == 75
        assert bounds.height() == 75
    
    def test_batch_visible_items(self):
        """Test getting visible items from batch."""
        items = [
            VirtualItemInfo(0, 0, 25, True),
            VirtualItemInfo(1, 25, 25, False),
            VirtualItemInfo(2, 50, 25, True)
        ]
        
        batch = RenderBatch("test_batch", items, 0, 75)
        visible_items = batch.get_visible_items()
        
        assert len(visible_items) == 2
        assert visible_items[0].index == 0
        assert visible_items[1].index == 2


class TestViewportManager:
    """Test viewport management."""
    
    def setup_method(self):
        """Setup test method."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
    
    def test_manager_initialization(self, mock_tree_view):
        """Test viewport manager initialization."""
        manager = ViewportManager(mock_tree_view)
        
        assert manager.tree_view == mock_tree_view
        assert isinstance(manager.metrics, ScrollMetrics)
        assert manager.last_scroll_position == 0
    
    def test_update_viewport(self, mock_tree_view):
        """Test viewport update."""
        manager = ViewportManager(mock_tree_view)
        
        # Setup viewport rect
        viewport_rect = QRect(0, 100, 400, 300)
        mock_tree_view.viewport.return_value.rect.return_value = viewport_rect
        
        # Setup scrollbar
        scrollbar = mock_tree_view.verticalScrollBar.return_value
        scrollbar.value.return_value = 100
        
        manager.update_viewport()
        
        assert manager.metrics.viewport_top == 100
        assert manager.metrics.viewport_bottom == 400  # 100 + 300
    
    def test_scroll_position_change(self, mock_tree_view):
        """Test scroll position change detection."""
        manager = ViewportManager(mock_tree_view)
        
        # Initial position
        manager.last_scroll_position = 0
        
        # Setup new position
        scrollbar = mock_tree_view.verticalScrollBar.return_value
        scrollbar.value.return_value = 100
        
        viewport_rect = QRect(0, 0, 400, 300)
        mock_tree_view.viewport.return_value.rect.return_value = viewport_rect
        
        changed = manager.has_scroll_position_changed()
        
        assert changed is True
        assert manager.last_scroll_position == 100
    
    def test_estimate_item_height(self, mock_tree_view, mock_model):
        """Test item height estimation."""
        manager = ViewportManager(mock_tree_view)
        mock_tree_view.model.return_value = mock_model
        
        # Setup sample indices
        sample_indices = [Mock(), Mock(), Mock()]
        sample_heights = [25, 30, 25]
        
        mock_tree_view.visualRect.side_effect = lambda idx: QRect(0, 0, 200, sample_heights.pop(0))
        
        estimated_height = manager.estimate_item_height(sample_indices)
        
        # Should be average: (25 + 30 + 25) / 3 ≈ 26.67
        assert 26 <= estimated_height <= 27


class TestItemRenderer:
    """Test item rendering optimization."""
    
    def setup_method(self):
        """Setup test method."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
    
    def test_renderer_initialization(self, mock_tree_view):
        """Test item renderer initialization."""
        renderer = ItemRenderer(mock_tree_view)
        
        assert renderer.tree_view == mock_tree_view
        assert renderer.render_cache == {}
        assert renderer.cache_enabled is True
    
    def test_render_cache_key(self, mock_tree_view):
        """Test render cache key generation."""
        renderer = ItemRenderer(mock_tree_view)
        
        item_info = VirtualItemInfo(5, 125, 25, True)
        cache_key = renderer._get_cache_key(item_info, "test_data")
        
        assert "index_5" in cache_key
        assert "height_25" in cache_key
    
    def test_cache_operations(self, mock_tree_view):
        """Test cache put and get operations."""
        renderer = ItemRenderer(mock_tree_view)
        
        # Test cache put
        test_data = {"rendered": "content"}
        renderer._cache_put("test_key", test_data, 100)
        
        assert "test_key" in renderer.render_cache
        
        # Test cache get
        cached_data = renderer._cache_get("test_key")
        assert cached_data == test_data
        
        # Test cache miss
        assert renderer._cache_get("nonexistent") is None
    
    def test_cache_cleanup(self, mock_tree_view):
        """Test cache cleanup by size."""
        renderer = ItemRenderer(mock_tree_view)
        renderer.max_cache_size = 200  # Small cache for testing
        
        # Fill cache beyond limit
        for i in range(5):
            renderer._cache_put(f"key_{i}", f"data_{i}", 100)
        
        # Should have cleaned up to stay under limit
        assert len(renderer.render_cache) <= 2  # 200/100 = 2 max entries
    
    def test_cache_cleanup_by_age(self, mock_tree_view):
        """Test cache cleanup by age."""
        renderer = ItemRenderer(mock_tree_view)
        renderer.cache_max_age = 0.001  # Very short age for testing
        
        # Add entry
        renderer._cache_put("old_key", "old_data", 100)
        
        # Wait and add new entry to trigger cleanup
        import time
        time.sleep(0.002)
        
        renderer._cache_put("new_key", "new_data", 100)
        renderer._cleanup_cache()
        
        # Old entry should be removed
        assert "old_key" not in renderer.render_cache
        assert "new_key" in renderer.render_cache


class TestVirtualScrollingEngine:
    """Test main virtual scrolling engine."""
    
    def setup_method(self):
        """Setup test method."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
    
    def test_engine_initialization(self, mock_tree_view):
        """Test engine initialization."""
        engine = VirtualScrollingEngine(mock_tree_view)
        
        assert engine.tree_view == mock_tree_view
        assert isinstance(engine.viewport_manager, ViewportManager)
        assert isinstance(engine.item_renderer, ItemRenderer)
        assert engine.enabled is True
    
    def test_calculate_visible_range(self, mock_tree_view, mock_model):
        """Test visible range calculation."""
        engine = VirtualScrollingEngine(mock_tree_view)
        mock_tree_view.model.return_value = mock_model
        
        # Setup viewport
        viewport_rect = QRect(0, 100, 400, 300)
        mock_tree_view.viewport.return_value.rect.return_value = viewport_rect
        
        scrollbar = mock_tree_view.verticalScrollBar.return_value
        scrollbar.value.return_value = 100
        
        visible_range = engine.calculate_visible_range(mock_model)
        
        assert len(visible_range) > 0
        # Should include items in viewport plus buffer
    
    def test_create_render_batch(self, mock_tree_view, mock_model):
        """Test render batch creation."""
        engine = VirtualScrollingEngine(mock_tree_view)
        mock_tree_view.model.return_value = mock_model
        
        # Create sample visible items
        visible_items = [
            VirtualItemInfo(0, 0, 25, True),
            VirtualItemInfo(1, 25, 25, True),
            VirtualItemInfo(2, 50, 25, True)
        ]
        
        batch = engine._create_render_batch(visible_items)
        
        assert isinstance(batch, RenderBatch)
        assert len(batch.items) == 3
        assert batch.start_y == 0
        assert batch.end_y == 75
    
    def test_enable_disable_virtual_scrolling(self, mock_tree_view):
        """Test enabling/disabling virtual scrolling."""
        engine = VirtualScrollingEngine(mock_tree_view)
        
        # Test disable
        engine.set_enabled(False)
        assert engine.enabled is False
        
        # Test enable
        engine.set_enabled(True)
        assert engine.enabled is True
    
    def test_performance_monitoring(self, mock_tree_view):
        """Test performance monitoring."""
        engine = VirtualScrollingEngine(mock_tree_view)
        
        # Get initial stats
        stats = engine.get_performance_stats()
        
        assert 'render_time_ms' in stats
        assert 'cache_hit_rate' in stats
        assert 'visible_items' in stats
        assert stats['enabled'] is True
    
    def test_large_dataset_handling(self, mock_tree_view):
        """Test handling of large datasets."""
        # Create model with large dataset
        large_model = Mock()
        large_model.rowCount.return_value = 100000  # 100K items
        large_model.index.side_effect = lambda row, col, parent=None: Mock(row=row, column=col)
        
        mock_tree_view.model.return_value = large_model
        
        engine = VirtualScrollingEngine(mock_tree_view)
        
        # Setup viewport for middle of dataset
        viewport_rect = QRect(0, 0, 400, 300)
        mock_tree_view.viewport.return_value.rect.return_value = viewport_rect
        
        scrollbar = mock_tree_view.verticalScrollBar.return_value
        scrollbar.value.return_value = 50000 * 25  # Middle of dataset
        
        visible_range = engine.calculate_visible_range(large_model)
        
        # Should only render visible items plus buffer, not entire dataset
        assert len(visible_range) < 100
        assert len(visible_range) > 10  # But enough for smooth scrolling


class TestVirtualScrollingIntegration:
    """Integration tests for virtual scrolling system."""
    
    def setup_method(self):
        """Setup test method."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
    
    def test_scroll_performance_with_large_dataset(self, mock_tree_view):
        """Test scroll performance with large dataset."""
        # Setup large dataset
        large_model = Mock()
        large_model.rowCount.return_value = 50000
        large_model.index.side_effect = lambda row, col, parent=None: Mock(row=row, column=col)
        mock_tree_view.model.return_value = large_model
        
        engine = VirtualScrollingEngine(mock_tree_view)
        
        # Simulate scrolling
        scroll_positions = [0, 1000, 5000, 10000, 25000, 49000]
        render_times = []
        
        for position in scroll_positions:
            scrollbar = mock_tree_view.verticalScrollBar.return_value
            scrollbar.value.return_value = position
            
            viewport_rect = QRect(0, 0, 400, 300)
            mock_tree_view.viewport.return_value.rect.return_value = viewport_rect
            
            import time
            start_time = time.time()
            
            visible_range = engine.calculate_visible_range(large_model)
            
            end_time = time.time()
            render_times.append((end_time - start_time) * 1000)  # Convert to ms
        
        # All render times should be fast (< 10ms)
        for render_time in render_times:
            assert render_time < 10.0
    
    def test_memory_usage_with_virtual_scrolling(self, mock_tree_view):
        """Test memory usage remains bounded with virtual scrolling."""
        engine = VirtualScrollingEngine(mock_tree_view)
        
        # Enable caching
        engine.item_renderer.cache_enabled = True
        engine.item_renderer.max_cache_size = 1000  # Small cache
        
        # Simulate rendering many items
        for i in range(1000):
            item_info = VirtualItemInfo(i, i * 25, 25, True)
            cache_key = engine.item_renderer._get_cache_key(item_info, f"data_{i}")
            engine.item_renderer._cache_put(cache_key, f"rendered_{i}", 50)
        
        # Cache should be limited in size
        cache_size = len(engine.item_renderer.render_cache)
        total_cache_bytes = sum(entry['size'] for entry in engine.item_renderer.render_cache.values())
        
        assert cache_size <= 20  # Should have evicted old entries
        assert total_cache_bytes <= 1000  # Should respect size limit


class TestVirtualScrollingEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_model(self, mock_tree_view):
        """Test handling of empty model."""
        empty_model = Mock()
        empty_model.rowCount.return_value = 0
        mock_tree_view.model.return_value = empty_model
        
        engine = VirtualScrollingEngine(mock_tree_view)
        
        visible_range = engine.calculate_visible_range(empty_model)
        
        assert len(visible_range) == 0
    
    def test_invalid_model(self, mock_tree_view):
        """Test handling of invalid model."""
        mock_tree_view.model.return_value = None
        
        engine = VirtualScrollingEngine(mock_tree_view)
        
        visible_range = engine.calculate_visible_range(None)
        
        assert len(visible_range) == 0
    
    def test_zero_height_items(self, mock_tree_view, mock_model):
        """Test handling of zero-height items."""
        mock_tree_view.model.return_value = mock_model
        mock_tree_view.visualRect.return_value = QRect(0, 0, 200, 0)  # Zero height
        
        engine = VirtualScrollingEngine(mock_tree_view)
        
        # Should handle gracefully and use default height
        engine.viewport_manager.update_viewport()
        
        assert engine.viewport_manager.metrics.item_height > 0
    
    def test_extremely_large_dataset(self, mock_tree_view):
        """Test handling of extremely large dataset."""
        huge_model = Mock()
        huge_model.rowCount.return_value = 10000000  # 10 million items
        mock_tree_view.model.return_value = huge_model
        
        engine = VirtualScrollingEngine(mock_tree_view)
        
        # Should still work efficiently
        visible_range = engine.calculate_visible_range(huge_model)
        
        # Should only render small subset
        assert len(visible_range) < 1000


if __name__ == "__main__":
    pytest.main([__file__])