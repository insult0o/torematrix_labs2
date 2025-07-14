"""Tests for the performance optimization system."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
import threading
from PyQt6.QtWidgets import QWidget, QApplication, QPushButton
from PyQt6.QtCore import QSize, QRect, QObject, QTimer
from PyQt6.QtGui import QPixmap

from src.torematrix.ui.layouts.performance import (
    PerformanceLevel, OptimizationType, PerformanceMetrics, PerformanceProfiler,
    performance_timer, LayoutCache, WidgetPool, LazyLoader, MemoryOptimizer,
    RenderOptimizer, PerformanceOptimizer
)
from src.torematrix.core.config import ConfigurationManager


@pytest.fixture
def app():
    """Fixture to provide QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_config_manager():
    """Mock config manager for testing."""
    return Mock(spec=ConfigManager)


class TestPerformanceMetrics:
    """Test PerformanceMetrics dataclass."""
    
    def test_metrics_creation(self):
        """Test creating performance metrics."""
        metrics = PerformanceMetrics(
            layout_calculation_time_ms=50.0,
            memory_usage_mb=256.0,
            cpu_usage_percent=45.0,
            total_layouts_calculated=100,
            cache_hits=80,
            cache_misses=20
        )
        
        assert metrics.layout_calculation_time_ms == 50.0
        assert metrics.memory_usage_mb == 256.0
        assert metrics.total_layouts_calculated == 100
        assert metrics.cache_hit_ratio == 0.8
        assert metrics.widgets_per_second > 0
    
    def test_derived_calculations(self):
        """Test derived metric calculations."""
        metrics = PerformanceMetrics(
            layout_calculation_time_ms=100.0,
            widgets_created=50,
            cache_hits=30,
            cache_misses=10
        )
        
        # Test cache hit ratio
        assert metrics.cache_hit_ratio == 0.75
        
        # Test widgets per second
        expected_wps = 50 / (100.0 / 1000)  # 50 widgets / 0.1 seconds
        assert metrics.widgets_per_second == expected_wps


class TestPerformanceProfiler:
    """Test PerformanceProfiler functionality."""
    
    def test_profiler_creation(self):
        """Test creating performance profiler."""
        profiler = PerformanceProfiler(max_samples=100)
        
        assert profiler._max_samples == 100
        assert len(profiler._timing_data) == 0
        assert len(profiler._active_timers) == 0
    
    def test_timing_operations(self):
        """Test timing operations."""
        profiler = PerformanceProfiler()
        
        # Start timing
        profiler.start_timing("test_operation")
        assert "test_operation" in profiler._active_timers
        
        # Simulate some work
        time.sleep(0.01)  # 10ms
        
        # End timing
        duration = profiler.end_timing("test_operation")
        
        assert duration > 0
        assert duration >= 10  # Should be at least 10ms
        assert "test_operation" not in profiler._active_timers
        assert len(profiler._timing_data["test_operation"]) == 1
    
    def test_multiple_operations(self):
        """Test timing multiple operations."""
        profiler = PerformanceProfiler()
        
        # Time multiple operations
        for i in range(5):
            profiler.start_timing("batch_operation")
            time.sleep(0.001)  # 1ms
            profiler.end_timing("batch_operation")
        
        stats = profiler.get_operation_stats("batch_operation")
        
        assert stats['count'] == 5
        assert stats['average_time_ms'] > 0
        assert stats['min_time_ms'] > 0
        assert stats['max_time_ms'] >= stats['min_time_ms']
    
    @patch('src.torematrix.ui.layouts.performance.psutil.Process')
    def test_memory_recording(self, mock_process_class):
        """Test memory usage recording."""
        # Mock process memory info
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 1024 * 1024 * 100  # 100MB in bytes
        mock_process.memory_info.return_value = mock_memory_info
        mock_process_class.return_value = mock_process
        
        profiler = PerformanceProfiler()
        memory_mb = profiler.record_memory_usage()
        
        assert memory_mb == 100.0
        assert len(profiler._memory_samples) == 1
    
    def test_statistics_calculation(self):
        """Test operation statistics calculation."""
        profiler = PerformanceProfiler()
        
        # Add sample timing data
        operation = "test_stats"
        sample_times = [10.0, 20.0, 30.0, 40.0, 50.0]
        
        for time_val in sample_times:
            profiler._timing_data[operation].append(time_val)
        
        stats = profiler.get_operation_stats(operation)
        
        assert stats['count'] == 5
        assert stats['total_time_ms'] == 150.0
        assert stats['average_time_ms'] == 30.0
        assert stats['min_time_ms'] == 10.0
        assert stats['max_time_ms'] == 50.0
        assert stats['median_time_ms'] == 30.0
    
    def test_data_clearing(self):
        """Test clearing profiler data."""
        profiler = PerformanceProfiler()
        
        # Add some data
        profiler.start_timing("test")
        profiler.end_timing("test")
        profiler.record_memory_usage()
        
        assert len(profiler._timing_data["test"]) > 0
        
        # Clear data
        profiler.clear_data()
        
        assert len(profiler._timing_data) == 0
        assert len(profiler._memory_samples) == 0
        assert len(profiler._active_timers) == 0


class TestPerformanceTimer:
    """Test performance_timer decorator."""
    
    def test_timer_decorator(self):
        """Test the performance timer decorator."""
        profiler = PerformanceProfiler()
        
        class TestClass:
            def __init__(self):
                self._profiler = profiler
            
            @performance_timer("decorated_method")
            def timed_method(self):
                time.sleep(0.01)  # 10ms
                return "result"
        
        test_obj = TestClass()
        result = test_obj.timed_method()
        
        assert result == "result"
        
        # Should have recorded timing
        stats = profiler.get_operation_stats("decorated_method")
        assert stats['count'] == 1
        assert stats['average_time_ms'] > 0
    
    def test_timer_without_profiler(self):
        """Test timer decorator when no profiler is available."""
        class TestClass:
            @performance_timer("no_profiler_method")
            def method_without_profiler(self):
                return "success"
        
        test_obj = TestClass()
        result = test_obj.method_without_profiler()
        
        # Should still work without profiler
        assert result == "success"


class TestLayoutCache:
    """Test LayoutCache functionality."""
    
    def test_cache_creation(self):
        """Test creating layout cache."""
        cache = LayoutCache(max_size=10, ttl_seconds=60.0)
        
        assert cache._max_size == 10
        assert cache._ttl_seconds == 60.0
        assert len(cache._cache) == 0
    
    def test_cache_operations(self):
        """Test basic cache operations."""
        cache = LayoutCache(max_size=5, ttl_seconds=3600.0)
        
        # Put value
        cache.put("key1", "value1")
        assert len(cache._cache) == 1
        
        # Get value
        result = cache.get("key1")
        assert result == "value1"
        
        # Get non-existent value
        result = cache.get("nonexistent")
        assert result is None
    
    def test_cache_eviction(self):
        """Test cache size-based eviction."""
        cache = LayoutCache(max_size=3)
        
        # Fill cache beyond capacity
        for i in range(5):
            cache.put(f"key{i}", f"value{i}")
        
        # Should not exceed max size
        assert len(cache._cache) <= 3
        
        # Older entries should be evicted
        assert cache.get("key0") is None
        assert cache.get("key4") == "value4"  # Most recent should be there
    
    def test_cache_ttl(self):
        """Test cache TTL expiration."""
        cache = LayoutCache(ttl_seconds=0.1)  # 100ms TTL
        
        cache.put("temp_key", "temp_value")
        
        # Should be available immediately
        assert cache.get("temp_key") == "temp_value"
        
        # Wait for expiration
        time.sleep(0.15)
        
        # Should be expired
        assert cache.get("temp_key") is None
    
    def test_cache_invalidation(self):
        """Test cache invalidation."""
        cache = LayoutCache()
        
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        
        # Invalidate specific key
        success = cache.invalidate("key1")
        assert success is True
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        
        # Try to invalidate non-existent key
        success = cache.invalidate("nonexistent")
        assert success is False
    
    def test_cache_statistics(self):
        """Test cache statistics."""
        cache = LayoutCache(max_size=5)
        
        # Generate some hits and misses
        cache.put("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss
        
        stats = cache.get_stats()
        
        assert stats['size'] == 1
        assert stats['max_size'] == 5
        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['hit_ratio'] == 2/3


@pytest.mark.usefixtures("app")
class TestWidgetPool:
    """Test WidgetPool functionality."""
    
    def test_pool_creation(self):
        """Test creating widget pool."""
        def widget_factory():
            return QWidget()
        
        pool = WidgetPool(widget_factory, max_size=10)
        
        assert pool._max_size == 10
        assert len(pool._available_widgets) == 0
        assert len(pool._in_use_widgets) == 0
    
    def test_widget_acquisition(self):
        """Test acquiring widgets from pool."""
        def widget_factory():
            widget = QWidget()
            widget.setObjectName("pooled_widget")
            return widget
        
        pool = WidgetPool(widget_factory)
        
        # First acquisition should create new widget
        widget1 = pool.acquire_widget()
        assert widget1 is not None
        assert widget1.objectName() == "pooled_widget"
        assert len(pool._in_use_widgets) == 1
        
        # Release widget
        pool.release_widget(widget1)
        assert len(pool._available_widgets) == 1
        assert len(pool._in_use_widgets) == 0
        
        # Second acquisition should reuse widget
        widget2 = pool.acquire_widget()
        assert widget2 == widget1  # Same widget instance
    
    def test_pool_size_limit(self):
        """Test pool size limitations."""
        def widget_factory():
            return QWidget()
        
        pool = WidgetPool(widget_factory, max_size=2)
        
        # Create and release widgets beyond pool size
        widgets = []
        for i in range(5):
            widget = pool.acquire_widget()
            widgets.append(widget)
        
        # Release all widgets
        for widget in widgets:
            pool.release_widget(widget)
        
        # Pool should not exceed max size
        assert len(pool._available_widgets) <= 2
    
    def test_widget_reset(self):
        """Test widget state reset."""
        def widget_factory():
            return QPushButton("Test Button")
        
        pool = WidgetPool(widget_factory)
        
        # Acquire and modify widget
        button = pool.acquire_widget()
        button.setEnabled(False)
        button.setVisible(False)
        button.setStyleSheet("background-color: red;")
        
        # Release and reacquire
        pool.release_widget(button)
        reacquired_button = pool.acquire_widget()
        
        # Should be reset to default state
        assert reacquired_button.isEnabled() is True
        assert reacquired_button.isVisible() is True
        assert reacquired_button.styleSheet() == ""
    
    def test_pool_statistics(self):
        """Test pool statistics."""
        def widget_factory():
            return QWidget()
        
        pool = WidgetPool(widget_factory)
        
        # Create some activity
        widgets = []
        for i in range(3):
            widget = pool.acquire_widget()
            widgets.append(widget)
        
        # Release some widgets
        for widget in widgets[:2]:
            pool.release_widget(widget)
        
        stats = pool.get_stats()
        
        assert stats['available'] == 2
        assert stats['in_use'] == 1
        assert stats['created'] == 3
        assert stats['reused'] >= 0
    
    def test_pool_cleanup(self):
        """Test pool cleanup."""
        def widget_factory():
            return QWidget()
        
        pool = WidgetPool(widget_factory)
        
        # Add widgets to pool
        for i in range(3):
            widget = pool.acquire_widget()
            pool.release_widget(widget)
        
        assert len(pool._available_widgets) == 3
        
        # Clear pool
        pool.clear_pool()
        
        assert len(pool._available_widgets) == 0


@pytest.mark.usefixtures("app")
class TestLazyLoader:
    """Test LazyLoader functionality."""
    
    def test_loader_creation(self):
        """Test creating lazy loader."""
        loader = LazyLoader(viewport_margin=50)
        
        assert loader._viewport_margin == 50
        assert len(loader._lazy_widgets) == 0
        assert len(loader._loaded_widgets) == 0
    
    def test_widget_registration(self):
        """Test widget registration for lazy loading."""
        loader = LazyLoader()
        widget = QWidget()
        
        load_called = False
        def mock_loader():
            nonlocal load_called
            load_called = True
        
        # Register widget
        loader.register_lazy_widget(widget, mock_loader)
        
        assert widget in loader._lazy_widgets
        assert not load_called
        
        # Unregister widget
        loader.unregister_lazy_widget(widget)
        
        assert widget not in loader._lazy_widgets
        assert widget not in loader._loaded_widgets
    
    def test_viewport_based_loading(self):
        """Test viewport-based widget loading."""
        loader = LazyLoader(viewport_margin=10)
        
        # Create widget in viewport
        widget = QWidget()
        widget.setGeometry(50, 50, 100, 100)
        
        load_called = False
        def mock_loader():
            nonlocal load_called
            load_called = True
        
        loader.register_lazy_widget(widget, mock_loader)
        
        # Check loading with viewport that includes widget
        viewport = QRect(0, 0, 200, 200)
        loaded_widgets = loader.check_and_load_widgets(viewport)
        
        assert len(loaded_widgets) == 1
        assert loaded_widgets[0] == widget
        assert load_called is True
        assert widget in loader._loaded_widgets
    
    def test_distant_widget_unloading(self):
        """Test unloading of distant widgets."""
        loader = LazyLoader(viewport_margin=10)
        
        # Create widget far from viewport
        widget = QWidget()
        widget.setGeometry(1000, 1000, 100, 100)
        
        # Mark as loaded
        loader._loaded_widgets.add(widget)
        
        # Check unloading with small viewport
        viewport = QRect(0, 0, 100, 100)
        unloaded_widgets = loader.unload_distant_widgets(viewport)
        
        assert len(unloaded_widgets) == 1
        assert unloaded_widgets[0] == widget
        assert widget not in loader._loaded_widgets
    
    def test_distance_calculation(self):
        """Test distance calculation between rectangles."""
        loader = LazyLoader()
        
        # Overlapping rectangles
        rect1 = QRect(0, 0, 100, 100)
        rect2 = QRect(50, 50, 100, 100)
        distance = loader._calculate_distance_to_rect(rect1, rect2)
        assert distance == 0.0  # Overlapping
        
        # Non-overlapping rectangles
        rect3 = QRect(200, 200, 100, 100)
        distance = loader._calculate_distance_to_rect(rect1, rect3)
        assert distance > 0
    
    def test_loader_statistics(self):
        """Test lazy loader statistics."""
        loader = LazyLoader()
        
        # Register some widgets
        for i in range(5):
            widget = QWidget()
            loader.register_lazy_widget(widget, lambda: None)
        
        # Mark some as loaded
        widgets = list(loader._lazy_widgets.keys())
        for widget in widgets[:3]:
            loader._loaded_widgets.add(widget)
        
        stats = loader.get_stats()
        
        assert stats['registered'] == 5
        assert stats['loaded'] == 3
        assert stats['pending'] == 2


@pytest.mark.usefixtures("app")
class TestMemoryOptimizer:
    """Test MemoryOptimizer functionality."""
    
    def test_optimizer_creation(self):
        """Test creating memory optimizer."""
        optimizer = MemoryOptimizer()
        
        assert len(optimizer._weak_references) == 0
        assert optimizer._cleanup_timer is not None
    
    def test_reference_registration(self):
        """Test registering objects for cleanup."""
        optimizer = MemoryOptimizer()
        
        # Create test object
        test_obj = QWidget()
        
        # Register for cleanup
        optimizer.register_for_cleanup(test_obj)
        
        assert len(optimizer._weak_references) == 1
        
        # Delete object
        del test_obj
        
        # Cleanup should eventually remove dead reference
        optimizer._cleanup_references()
        assert len(optimizer._weak_references) == 0
    
    @patch('src.torematrix.ui.layouts.performance.gc.collect')
    @patch('src.torematrix.ui.layouts.performance.gc.get_objects')
    def test_garbage_collection(self, mock_get_objects, mock_collect):
        """Test forced garbage collection."""
        optimizer = MemoryOptimizer()
        
        # Mock gc functions
        mock_get_objects.side_effect = [
            list(range(1000)),  # Before
            list(range(900))    # After
        ]
        mock_collect.return_value = 50
        
        with patch.object(optimizer, '_get_memory_usage', side_effect=[100.0, 95.0]):
            stats = optimizer.force_garbage_collection()
        
        assert stats['objects_before'] == 1000
        assert stats['objects_after'] == 900
        assert stats['objects_collected'] == 100
        assert stats['memory_before_mb'] == 100.0
        assert stats['memory_after_mb'] == 95.0
        assert stats['memory_freed_mb'] == 5.0
        assert stats['gc_collected'] == 50
    
    def test_widget_memory_optimization(self):
        """Test widget-specific memory optimization."""
        optimizer = MemoryOptimizer()
        
        widget = QWidget()
        widget.setToolTip("Test tooltip")
        widget.setWhatsThis("Test whatsthis")
        widget.setStyleSheet("color: red;")
        
        # Optimize widget memory
        optimizer.optimize_widget_memory(widget)
        
        # Properties should be cleared
        assert widget.toolTip() == ""
        assert widget.whatsThis() == ""
        assert widget.styleSheet() == ""


@pytest.mark.usefixtures("app")
class TestRenderOptimizer:
    """Test RenderOptimizer functionality."""
    
    def test_optimizer_creation(self):
        """Test creating render optimizer."""
        optimizer = RenderOptimizer()
        
        assert len(optimizer._render_cache) == 0
        assert optimizer._max_cache_size == 50
    
    def test_render_caching(self):
        """Test render caching functionality."""
        optimizer = RenderOptimizer()
        
        widget = QWidget()
        widget.resize(100, 50)
        
        # Cache widget render
        pixmap = optimizer.cache_widget_render(widget, "test_widget")
        
        assert isinstance(pixmap, QPixmap)
        assert len(optimizer._render_cache) == 1
        
        # Get cached render
        cached_pixmap = optimizer.get_cached_render("test_widget")
        assert cached_pixmap == pixmap
    
    def test_cache_invalidation(self):
        """Test render cache invalidation."""
        optimizer = RenderOptimizer()
        
        widget = QWidget()
        widget.resize(100, 50)
        
        # Cache render
        optimizer.cache_widget_render(widget, "test_widget")
        assert len(optimizer._render_cache) == 1
        
        # Invalidate specific cache
        optimizer.invalidate_render_cache("test_widget")
        assert len(optimizer._render_cache) == 0
        
        # Cache again and invalidate all
        optimizer.cache_widget_render(widget, "test_widget")
        optimizer.invalidate_render_cache()
        assert len(optimizer._render_cache) == 0


class TestPerformanceOptimizer:
    """Test PerformanceOptimizer main coordinator."""
    
    def test_optimizer_initialization(self, mock_config_manager):
        """Test optimizer initialization."""
        optimizer = PerformanceOptimizer(
            mock_config_manager,
            PerformanceLevel.STANDARD
        )
        
        assert optimizer._performance_level == PerformanceLevel.STANDARD
        assert optimizer._profiler is not None
        assert optimizer._layout_cache is not None
        assert len(optimizer._optimizations_enabled) > 0
    
    def test_optimization_levels(self, mock_config_manager):
        """Test different optimization levels."""
        # Minimal level
        minimal_optimizer = PerformanceOptimizer(
            mock_config_manager,
            PerformanceLevel.MINIMAL
        )
        minimal_opts = minimal_optimizer._optimizations_enabled
        
        # Aggressive level
        aggressive_optimizer = PerformanceOptimizer(
            mock_config_manager,
            PerformanceLevel.AGGRESSIVE
        )
        aggressive_opts = aggressive_optimizer._optimizations_enabled
        
        # Aggressive should have more optimizations
        assert len(aggressive_opts) > len(minimal_opts)
        assert OptimizationType.LAYOUT_CACHING in minimal_opts
        assert OptimizationType.LAZY_LOADING in aggressive_opts
    
    def test_layout_calculation_optimization(self, mock_config_manager):
        """Test layout calculation optimization."""
        optimizer = PerformanceOptimizer(
            mock_config_manager,
            PerformanceLevel.STANDARD
        )
        
        # Mock calculation function
        call_count = 0
        def mock_calculation(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return f"result_{call_count}"
        
        # First call should execute function
        result1 = optimizer.optimize_layout_calculation(
            mock_calculation, "arg1", kwarg1="value1"
        )
        assert result1 == "result_1"
        assert call_count == 1
        
        # Second call with same parameters should use cache
        result2 = optimizer.optimize_layout_calculation(
            mock_calculation, "arg1", kwarg1="value1"
        )
        
        if OptimizationType.LAYOUT_CACHING in optimizer._optimizations_enabled:
            assert result2 == "result_1"  # Cached result
            assert call_count == 1  # Function not called again
    
    def test_widget_pool_creation(self, mock_config_manager):
        """Test widget pool creation."""
        optimizer = PerformanceOptimizer(
            mock_config_manager,
            PerformanceLevel.STANDARD
        )
        
        def widget_factory():
            return QWidget()
        
        pool = optimizer.create_widget_pool("test_pool", widget_factory)
        
        assert pool is not None
        if OptimizationType.WIDGET_POOLING in optimizer._optimizations_enabled:
            assert "test_pool" in optimizer._widget_pools
    
    def test_memory_optimization(self, mock_config_manager):
        """Test memory optimization."""
        optimizer = PerformanceOptimizer(
            mock_config_manager,
            PerformanceLevel.STANDARD
        )
        
        # Mock high memory usage
        with patch.object(optimizer._profiler, 'record_memory_usage', return_value=600.0):
            stats = optimizer.optimize_memory_usage()
        
        # Should perform optimization if memory management is enabled
        if OptimizationType.MEMORY_MANAGEMENT in optimizer._optimizations_enabled:
            assert isinstance(stats, dict)
    
    def test_performance_level_change(self, mock_config_manager):
        """Test changing performance level."""
        optimizer = PerformanceOptimizer(
            mock_config_manager,
            PerformanceLevel.MINIMAL
        )
        
        initial_opts = len(optimizer._optimizations_enabled)
        
        # Change to aggressive level
        optimizer.set_performance_level(PerformanceLevel.AGGRESSIVE)
        
        assert optimizer._performance_level == PerformanceLevel.AGGRESSIVE
        assert len(optimizer._optimizations_enabled) > initial_opts
    
    def test_optimization_enable_disable(self, mock_config_manager):
        """Test enabling/disabling specific optimizations."""
        optimizer = PerformanceOptimizer(
            mock_config_manager,
            PerformanceLevel.MINIMAL
        )
        
        # Enable specific optimization
        optimizer.enable_optimization(OptimizationType.LAZY_LOADING)
        assert OptimizationType.LAZY_LOADING in optimizer._optimizations_enabled
        
        # Disable optimization
        optimizer.disable_optimization(OptimizationType.LAZY_LOADING)
        assert OptimizationType.LAZY_LOADING not in optimizer._optimizations_enabled
    
    def test_comprehensive_statistics(self, mock_config_manager):
        """Test comprehensive statistics collection."""
        optimizer = PerformanceOptimizer(
            mock_config_manager,
            PerformanceLevel.STANDARD
        )
        
        # Generate some activity
        optimizer.optimize_layout_calculation(lambda: "test", "arg1")
        
        stats = optimizer.get_comprehensive_stats()
        
        assert 'metrics' in stats
        assert 'profiler' in stats
        assert 'cache' in stats
        assert 'optimizations_enabled' in stats
        assert 'performance_level' in stats
        
        assert stats['performance_level'] == PerformanceLevel.STANDARD.name
    
    def test_cache_clearing(self, mock_config_manager):
        """Test clearing all caches."""
        optimizer = PerformanceOptimizer(
            mock_config_manager,
            PerformanceLevel.STANDARD
        )
        
        # Add some data to caches
        optimizer._layout_cache.put("test_key", "test_value")
        
        # Clear all caches
        optimizer.clear_all_caches()
        
        # Caches should be empty
        cache_stats = optimizer._layout_cache.get_stats()
        assert cache_stats['size'] == 0


class TestIntegration:
    """Integration tests for performance system."""
    
    def test_thread_safety(self):
        """Test thread safety of performance components."""
        profiler = PerformanceProfiler()
        cache = LayoutCache()
        
        def worker(thread_id):
            for i in range(10):
                # Test profiler thread safety
                profiler.start_timing(f"thread_{thread_id}_op_{i}")
                time.sleep(0.001)
                profiler.end_timing(f"thread_{thread_id}_op_{i}")
                
                # Test cache thread safety
                cache.put(f"thread_{thread_id}_key_{i}", f"value_{i}")
                cache.get(f"thread_{thread_id}_key_{i}")
        
        # Run multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have data from all threads
        assert len(profiler._timing_data) > 0
        assert cache.get_stats()['size'] > 0
    
    def test_performance_under_load(self, mock_config_manager):
        """Test performance under high load."""
        optimizer = PerformanceOptimizer(
            mock_config_manager,
            PerformanceLevel.AGGRESSIVE
        )
        
        start_time = time.time()
        
        # Perform many optimizations
        for i in range(100):
            def dummy_calc():
                return f"result_{i}"
            
            optimizer.optimize_layout_calculation(dummy_calc)
        
        elapsed = time.time() - start_time
        
        # Should complete efficiently
        assert elapsed < 1.0  # Under 1 second for 100 operations


if __name__ == "__main__":
    pytest.main([__file__])