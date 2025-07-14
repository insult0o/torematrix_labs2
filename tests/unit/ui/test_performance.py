"""Tests for performance optimization system."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
import time
from pathlib import Path
import tempfile

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtGui import QIcon

from torematrix.ui.performance import (
    PerformanceOptimizer, PerformanceLevel, PerformanceMetrics,
    OptimizationResult, IconCache, StylesheetCache, PerformanceMonitor
)
from torematrix.core.events import EventBus
from torematrix.core.config import ConfigManager
from torematrix.core.state import StateManager


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for PerformanceOptimizer."""
    event_bus = Mock(spec=EventBus)
    config_manager = Mock(spec=ConfigManager)
    state_manager = Mock(spec=StateManager)
    
    return event_bus, config_manager, state_manager


@pytest.fixture
def performance_optimizer(app, mock_dependencies):
    """Create PerformanceOptimizer instance for testing."""
    event_bus, config_manager, state_manager = mock_dependencies
    
    with patch('torematrix.ui.performance.QSettings'):
        optimizer = PerformanceOptimizer(event_bus, config_manager, state_manager)
    
    return optimizer


class TestPerformanceMetrics:
    """Test PerformanceMetrics data class."""
    
    def test_metrics_creation(self):
        """Test creating PerformanceMetrics instance."""
        metrics = PerformanceMetrics(
            widget_creation_time=50.0,
            stylesheet_load_time=25.0,
            layout_time=10.0,
            paint_time=5.0,
            memory_usage_mb=128.5,
            widget_count=100,
            icon_cache_size=50,
            stylesheet_cache_size=10
        )
        
        assert metrics.widget_creation_time == 50.0
        assert metrics.memory_usage_mb == 128.5
        assert metrics.widget_count == 100


class TestOptimizationResult:
    """Test OptimizationResult data class."""
    
    def test_result_creation(self):
        """Test creating OptimizationResult instance."""
        result = OptimizationResult(
            success=True,
            time_saved_ms=100.0,
            memory_saved_mb=25.0,
            description="Test optimization",
            recommendations=["Use lazy loading", "Cache icons"]
        )
        
        assert result.success is True
        assert result.time_saved_ms == 100.0
        assert len(result.recommendations) == 2


class TestIconCache:
    """Test IconCache functionality."""
    
    def test_initialization(self):
        """Test IconCache initialization."""
        cache = IconCache(max_size=500)
        
        assert cache._max_size == 500
        assert cache._cache_hits == 0
        assert cache._cache_misses == 0
        assert len(cache._cache) == 0
    
    def test_icon_caching(self):
        """Test icon caching and retrieval."""
        cache = IconCache()
        
        # Mock successful icon loading
        with patch.object(cache, '_load_icon') as mock_load:
            mock_icon = Mock()
            mock_icon.isNull.return_value = False
            mock_load.return_value = mock_icon
            
            # First request (cache miss)
            icon1 = cache.get_icon("test_icon.svg")
            assert icon1 == mock_icon
            assert cache._cache_misses == 1
            assert cache._cache_hits == 0
            
            # Second request (cache hit)
            icon2 = cache.get_icon("test_icon.svg")
            assert icon2 == mock_icon
            assert cache._cache_hits == 1
            assert cache._cache_misses == 1
    
    def test_icon_loading_failure(self):
        """Test handling of icon loading failures."""
        cache = IconCache()
        
        # Mock failed icon loading
        with patch.object(cache, '_load_icon', return_value=None):
            icon = cache.get_icon("nonexistent.svg")
            assert icon is None
            assert cache._cache_misses == 1
    
    def test_cache_eviction(self):
        """Test LRU cache eviction."""
        cache = IconCache(max_size=2)
        
        with patch.object(cache, '_load_icon') as mock_load:
            mock_icon = Mock()
            mock_icon.isNull.return_value = False
            mock_load.return_value = mock_icon
            
            # Fill cache to capacity
            cache.get_icon("icon1.svg")
            cache.get_icon("icon2.svg")
            assert len(cache._cache) == 2
            
            # Add third icon (should evict oldest)
            cache.get_icon("icon3.svg")
            assert len(cache._cache) == 2
            assert "icon1.svg" not in cache._cache  # Should be evicted
    
    def test_cache_statistics(self):
        """Test cache statistics."""
        cache = IconCache()
        
        with patch.object(cache, '_load_icon') as mock_load:
            mock_icon = Mock()
            mock_icon.isNull.return_value = False
            mock_load.return_value = mock_icon
            
            # Generate some cache activity
            cache.get_icon("icon1.svg")  # Miss
            cache.get_icon("icon1.svg")  # Hit
            cache.get_icon("icon2.svg")  # Miss
            
            stats = cache.get_stats()
            assert stats["size"] == 2
            assert stats["hits"] == 1
            assert stats["misses"] == 2
            assert stats["hit_rate"] == 33.333333333333336  # 1/3 * 100
    
    def test_cache_clearing(self):
        """Test cache clearing."""
        cache = IconCache()
        
        with patch.object(cache, '_load_icon') as mock_load:
            mock_icon = Mock()
            mock_icon.isNull.return_value = False
            mock_load.return_value = mock_icon
            
            cache.get_icon("icon1.svg")
            assert len(cache._cache) > 0
            
            cache.clear()
            assert len(cache._cache) == 0
            assert cache._cache_hits == 0
            assert cache._cache_misses == 0


class TestStylesheetCache:
    """Test StylesheetCache functionality."""
    
    def test_initialization(self):
        """Test StylesheetCache initialization."""
        cache = StylesheetCache()
        
        assert len(cache._cache) == 0
        assert len(cache._optimized_cache) == 0
        assert len(cache._load_times) == 0
    
    def test_stylesheet_caching(self):
        """Test stylesheet caching and retrieval."""
        cache = StylesheetCache()
        
        # Create temporary stylesheet file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.qss', delete=False) as f:
            f.write("QWidget { background: red; }")
            stylesheet_path = f.name
        
        try:
            # First request (load from file)
            stylesheet1 = cache.get_stylesheet(stylesheet_path)
            assert "QWidget { background: red; }" in stylesheet1
            
            # Second request (from cache)
            stylesheet2 = cache.get_stylesheet(stylesheet_path)
            assert stylesheet1 == stylesheet2
            
        finally:
            Path(stylesheet_path).unlink()
    
    def test_stylesheet_optimization(self):
        """Test stylesheet optimization."""
        cache = StylesheetCache()
        
        unoptimized = """
        /* This is a comment */
        QWidget {
            margin: 0px 0px 0px 0px;
            padding: 0px 0px 0px 0px;
            border: 0px;
        }
        // Another comment
        """
        
        optimized = cache._optimize_stylesheet(unoptimized)
        
        # Should remove comments and optimize properties
        assert "/* This is a comment */" not in optimized
        assert "// Another comment" not in optimized
        assert "margin: 0" in optimized
        assert "padding: 0" in optimized
        assert "border: none" in optimized
    
    def test_cache_statistics(self):
        """Test cache statistics."""
        cache = StylesheetCache()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.qss', delete=False) as f:
            f.write("QWidget { color: blue; }")
            stylesheet_path = f.name
        
        try:
            cache.get_stylesheet(stylesheet_path)
            stats = cache.get_stats()
            
            assert stats["size"] == 1
            assert stats["total_stylesheets"] == 1
            assert "average_load_time" in stats
            
        finally:
            Path(stylesheet_path).unlink()


class TestPerformanceMonitor:
    """Test PerformanceMonitor functionality."""
    
    @patch('torematrix.ui.performance.psutil')
    def test_metrics_collection(self, mock_psutil):
        """Test performance metrics collection."""
        # Mock psutil
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 134217728  # 128 MB in bytes
        mock_process.memory_info.return_value = mock_memory_info
        mock_psutil.Process.return_value = mock_process
        
        monitor = PerformanceMonitor()
        monitor._collect_metrics()
        
        assert monitor._metrics.memory_usage_mb == 128.0
    
    def test_monitoring_lifecycle(self):
        """Test performance monitoring start/stop."""
        monitor = PerformanceMonitor()
        
        # Test starting monitoring
        with patch.object(monitor, 'start') as mock_start:
            monitor.start_monitoring(update_interval=1.0)
            assert monitor._update_interval == 1.0
            assert monitor._running is True
            mock_start.assert_called_once()
        
        # Test stopping monitoring
        with patch.object(monitor, 'quit') as mock_quit:
            with patch.object(monitor, 'wait') as mock_wait:
                monitor.stop_monitoring()
                assert monitor._running is False
                mock_quit.assert_called_once()
                mock_wait.assert_called_once()


class TestPerformanceOptimizer:
    """Test PerformanceOptimizer functionality."""
    
    def test_initialization(self, performance_optimizer):
        """Test PerformanceOptimizer initialization."""
        assert performance_optimizer._performance_level == PerformanceLevel.BALANCED
        assert isinstance(performance_optimizer._icon_cache, IconCache)
        assert isinstance(performance_optimizer._stylesheet_cache, StylesheetCache)
        assert isinstance(performance_optimizer._monitor, PerformanceMonitor)
    
    def test_performance_level_setting(self, performance_optimizer):
        """Test setting performance levels."""
        # Test minimal performance
        performance_optimizer.set_performance_level(PerformanceLevel.MINIMAL)
        assert performance_optimizer._performance_level == PerformanceLevel.MINIMAL
        assert performance_optimizer._icon_cache._max_size == 100
        
        # Test maximum performance
        performance_optimizer.set_performance_level(PerformanceLevel.MAXIMUM)
        assert performance_optimizer._performance_level == PerformanceLevel.MAXIMUM
        assert performance_optimizer._icon_cache._max_size == 1000
    
    def test_widget_creation_profiling(self, performance_optimizer):
        """Test widget creation profiling."""
        @performance_optimizer.profile_widget_creation(QWidget)
        def create_widget():
            return QWidget()
        
        # Create widget and check profiling
        widget = create_widget()
        assert isinstance(widget, QWidget)
        assert "QWidget" in performance_optimizer._profiling_data
        assert len(performance_optimizer._profiling_data["QWidget"]) == 1
    
    def test_stylesheet_optimization(self, performance_optimizer):
        """Test stylesheet loading optimization."""
        # Create temporary stylesheet
        with tempfile.NamedTemporaryFile(mode='w', suffix='.qss', delete=False) as f:
            f.write("QWidget { background: green; }")
            stylesheet_path = f.name
        
        try:
            optimized = performance_optimizer.optimize_stylesheet_loading(stylesheet_path)
            assert "QWidget { background: green; }" in optimized
            
        finally:
            Path(stylesheet_path).unlink()
    
    def test_icon_caching(self, performance_optimizer):
        """Test icon render caching."""
        with patch.object(performance_optimizer._icon_cache, 'get_icon') as mock_get:
            mock_icon = Mock()
            mock_get.return_value = mock_icon
            
            cached_icons = performance_optimizer.cache_icon_renders("test_icon", [16, 24, 32])
            
            assert len(cached_icons) == 3
            assert 16 in cached_icons
            assert 24 in cached_icons
            assert 32 in cached_icons
    
    def test_lazy_loading(self, performance_optimizer):
        """Test lazy component loading."""
        # Register component
        def create_component():
            return QWidget()
        
        performance_optimizer.lazy_load_component("test_component", create_component)
        assert "test_component" in performance_optimizer._lazy_components
        
        # Load component
        component = performance_optimizer.load_component("test_component")
        assert isinstance(component, QWidget)
        assert "test_component" in performance_optimizer._loaded_components
        
        # Try to load already loaded component
        component2 = performance_optimizer.load_component("test_component")
        assert component2 is None  # Already loaded
    
    @patch('torematrix.ui.performance.psutil')
    def test_memory_monitoring(self, mock_psutil, performance_optimizer):
        """Test memory usage monitoring."""
        # Mock psutil
        mock_process = Mock()
        mock_memory_info = Mock()
        mock_memory_info.rss = 268435456  # 256 MB
        mock_memory_info.vms = 536870912  # 512 MB
        mock_process.memory_info.return_value = mock_memory_info
        mock_process.memory_percent.return_value = 15.5
        mock_psutil.Process.return_value = mock_process
        
        usage = performance_optimizer.monitor_memory_usage()
        
        assert usage["rss_mb"] == 256.0
        assert usage["vms_mb"] == 512.0
        assert usage["percent"] == 15.5
    
    def test_memory_cleanup(self, performance_optimizer):
        """Test memory cleanup operations."""
        with patch('gc.collect', return_value=10) as mock_gc:
            with patch.object(performance_optimizer, '_cleanup_caches') as mock_cleanup:
                performance_optimizer._perform_memory_cleanup()
                
                mock_gc.assert_called_once()
                mock_cleanup.assert_called_once()
    
    def test_cache_cleanup(self, performance_optimizer):
        """Test cache cleanup when full."""
        # Mock icon cache to appear full
        performance_optimizer._icon_cache._cache = {"icon{}".format(i): Mock() for i in range(500)}
        performance_optimizer._icon_cache._max_size = 500
        
        with patch.object(performance_optimizer._icon_cache, '_evict_oldest') as mock_evict:
            performance_optimizer._cleanup_caches()
            # Should evict half the cache (250 items)
            assert mock_evict.call_count == 250
    
    def test_performance_benchmarking(self, performance_optimizer):
        """Test operation benchmarking."""
        def test_operation():
            time.sleep(0.01)  # 10ms operation
        
        execution_time = performance_optimizer.benchmark_operation("test_op", test_operation)
        
        assert execution_time >= 10  # At least 10ms
        assert "test_op" in performance_optimizer._profiling_data
        assert len(performance_optimizer._profiling_data["test_op"]) == 1
    
    def test_ui_performance_optimization(self, performance_optimizer, app):
        """Test comprehensive UI performance optimization."""
        with patch('gc.collect', return_value=5):
            with patch.object(performance_optimizer, 'monitor_memory_usage') as mock_monitor:
                mock_monitor.side_effect = [{"rss_mb": 150.0}, {"rss_mb": 140.0}]
                
                result = performance_optimizer.optimize_ui_performance()
                
                assert isinstance(result, OptimizationResult)
                assert result.success is True
                assert result.memory_saved_mb == 10.0
                assert len(result.recommendations) > 0
    
    def test_performance_recommendations(self, performance_optimizer):
        """Test performance improvement recommendations."""
        # Set up conditions for recommendations
        performance_optimizer._profiling_data["SlowWidget"] = [150.0, 200.0]  # Slow widget creation
        
        with patch.object(performance_optimizer, 'monitor_memory_usage') as mock_monitor:
            mock_monitor.return_value = {"rss_mb": 300.0}  # High memory usage
            
            with patch.object(performance_optimizer._icon_cache, 'get_stats') as mock_stats:
                mock_stats.return_value = {"hit_rate": 60}  # Low hit rate
                
                recommendations = performance_optimizer._get_performance_recommendations()
                
                assert len(recommendations) > 0
                # Should recommend memory reduction
                assert any("memory" in rec.lower() for rec in recommendations)
                # Should recommend icon cache improvement
                assert any("icon cache" in rec.lower() for rec in recommendations)
                # Should mention slow widget
                assert any("SlowWidget" in rec for rec in recommendations)
    
    def test_cache_statistics(self, performance_optimizer):
        """Test getting cache statistics."""
        stats = performance_optimizer.get_cache_statistics()
        
        assert "icon_cache" in stats
        assert "stylesheet_cache" in stats
        assert "lazy_components" in stats
        
        assert "size" in stats["icon_cache"]
        assert "registered" in stats["lazy_components"]
        assert "loaded" in stats["lazy_components"]
    
    def test_event_handling(self, performance_optimizer):
        """Test event handling for widget creation and theme changes."""
        # Test widget created event
        performance_optimizer._handle_widget_created({
            "widget_type": "TestWidget",
            "creation_time": 75.0
        })
        
        assert "TestWidget" in performance_optimizer._profiling_data
        assert performance_optimizer._profiling_data["TestWidget"][0] == 75.0
        
        # Test theme changed event
        performance_optimizer._handle_theme_changed({"theme": "dark"})
        # Should clear caches (tested by checking if clear methods were called)
    
    def test_cleanup(self, performance_optimizer):
        """Test performance optimizer cleanup."""
        with patch.object(performance_optimizer._monitor, 'isRunning', return_value=True):
            with patch.object(performance_optimizer._monitor, 'stop_monitoring') as mock_stop:
                with patch.object(performance_optimizer._memory_cleanup_timer, 'stop') as mock_timer_stop:
                    performance_optimizer.cleanup()
                    
                    mock_stop.assert_called_once()
                    mock_timer_stop.assert_called_once()
    
    def test_performance_warning_signals(self, performance_optimizer):
        """Test performance warning signal emissions."""
        signal_spy = Mock()
        performance_optimizer.performance_warning.connect(signal_spy)
        
        # Create slow widget to trigger warning
        @performance_optimizer.profile_widget_creation(QWidget)
        def slow_create_widget():
            time.sleep(0.11)  # 110ms > 100ms threshold
            return QWidget()
        
        slow_create_widget()
        
        signal_spy.assert_called()
        args = signal_spy.call_args[0]
        assert args[0] == "slow_widget_creation"
        assert args[1] > 100  # Time should be > 100ms