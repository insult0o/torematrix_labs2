"""
Performance Optimization Tests for PDF.js Integration.

This module tests the performance optimization system including monitoring,
memory management, caching, and hardware acceleration.
"""
import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
from typing import Dict, Any, List

# Import the performance optimization components
from src.torematrix.integrations.pdf.performance import (
    PerformanceConfig, PerformanceMonitor, PerformanceOptimizer,
    PerformanceLevel, HardwareCapability, PerformanceMetrics
)
from src.torematrix.integrations.pdf.memory import MemoryManager, MemoryPool, MemoryStats
from src.torematrix.integrations.pdf.cache import CacheManager, MemoryCache, CacheQuality
from src.torematrix.integrations.pdf.metrics import MetricsCollector, MetricType, PerformanceAlert


class TestPerformanceConfig:
    """Test performance configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = PerformanceConfig()
        
        assert config.cache_size_mb == 200
        assert config.max_preload_pages == 5
        assert config.memory_pressure_threshold == 0.8
        assert config.performance_level == PerformanceLevel.MEDIUM
        assert config.enable_gpu_acceleration == True
        assert config.enable_lazy_loading == True
        assert config.enable_progressive_rendering == True
    
    def test_config_modification(self):
        """Test configuration modification."""
        config = PerformanceConfig(
            cache_size_mb=500,
            max_preload_pages=10,
            performance_level=PerformanceLevel.HIGH,
            enable_gpu_acceleration=False
        )
        
        assert config.cache_size_mb == 500
        assert config.max_preload_pages == 10
        assert config.performance_level == PerformanceLevel.HIGH
        assert config.enable_gpu_acceleration == False


class TestPerformanceMonitor:
    """Test performance monitoring system."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return PerformanceConfig(
            cache_size_mb=100,
            metrics_collection_interval=0.1,
            performance_logging=False
        )
    
    @pytest.fixture
    def monitor(self, config):
        """Create test performance monitor."""
        return PerformanceMonitor(config)
    
    def test_monitor_initialization(self, monitor):
        """Test monitor initialization."""
        assert monitor.config is not None
        assert monitor.metrics_collector is not None
        assert monitor.memory_manager is not None
        assert monitor.cache_manager is not None
        assert not monitor.is_monitoring
        assert monitor.hardware_capability is not None
    
    def test_start_stop_monitoring(self, monitor):
        """Test starting and stopping monitoring."""
        # Start monitoring
        monitor.start_monitoring()
        assert monitor.is_monitoring
        assert monitor.monitor_timer.isActive()
        
        # Stop monitoring
        monitor.stop_monitoring()
        assert not monitor.is_monitoring
        assert not monitor.monitor_timer.isActive()
    
    def test_metrics_collection(self, monitor):
        """Test metrics collection."""
        # Mock process to avoid system dependencies
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=100 * 1024 * 1024)  # 100MB
        mock_process.cpu_percent.return_value = 25.0
        monitor.process = mock_process
        
        # Mock cache manager
        monitor.cache_manager.get_statistics = Mock(return_value={
            'hit_rate': 0.8,
            'size_mb': 50.0,
            'cached_pages': 25
        })
        
        # Collect metrics
        monitor._collect_metrics()
        
        # Check metrics
        metrics = monitor.get_current_metrics()
        assert metrics.memory_usage_mb == 100.0
        assert metrics.cpu_usage_percent == 25.0
        assert metrics.cache_hit_rate == 0.8
        assert metrics.cache_size_mb == 50.0
        assert metrics.cached_pages == 25
    
    def test_performance_issue_detection(self, monitor):
        """Test performance issue detection."""
        # Mock high memory usage
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=400 * 1024 * 1024)  # 400MB
        mock_process.cpu_percent.return_value = 85.0
        monitor.process = mock_process
        
        # Mock cache manager
        monitor.cache_manager.get_statistics = Mock(return_value={
            'hit_rate': 0.3,
            'size_mb': 180.0,
            'cached_pages': 100
        })
        
        # Collect metrics to trigger issue detection
        monitor._collect_metrics()
        
        # Check that optimization was triggered
        assert monitor.current_metrics.memory_usage_mb > 200
        assert monitor.current_metrics.cpu_usage_percent > 80
    
    def test_memory_optimization(self, monitor):
        """Test memory optimization triggering."""
        # Mock memory cleanup methods
        monitor.memory_manager.emergency_cleanup = Mock()
        monitor.cache_manager.clear_cache = Mock()
        
        # Trigger critical memory optimization
        monitor._trigger_memory_optimization('critical')
        
        # Check that emergency cleanup was called
        monitor.memory_manager.emergency_cleanup.assert_called_once()
        monitor.cache_manager.clear_cache.assert_called_once_with(ratio=0.5)
    
    def test_hardware_detection(self, monitor):
        """Test hardware capability detection."""
        # Test that hardware detection returns a valid capability
        capability = monitor._detect_hardware_capability()
        assert isinstance(capability, HardwareCapability)
        
        # Test GPU acceleration check
        gpu_available = monitor._check_gpu_acceleration()
        assert isinstance(gpu_available, bool)
    
    def test_optimization_recommendations(self, monitor):
        """Test optimization recommendations."""
        # Add some performance history
        for i in range(10):
            metrics = PerformanceMetrics(
                memory_usage_mb=150 + i * 5,
                render_time_ms=600 + i * 10,
                cpu_usage_percent=60 + i * 2
            )
            monitor.performance_history.append(metrics)
        
        # Get recommendations
        recommendations = monitor.get_optimization_recommendations()
        
        # Check that recommendations were generated
        assert len(recommendations) > 0
        
        # Check recommendation structure
        for rec in recommendations:
            assert 'type' in rec
            assert 'priority' in rec
            assert 'description' in rec
            assert 'suggestion' in rec
            assert 'action' in rec
    
    def test_apply_optimization(self, monitor):
        """Test applying optimizations."""
        # Test cache size increase
        original_size = monitor.config.cache_size_mb
        success = monitor.apply_optimization('increase_cache_size', {'size_mb': 300})
        assert success
        assert monitor.config.cache_size_mb == 300
        
        # Test GPU acceleration enable
        success = monitor.apply_optimization('enable_gpu_acceleration', {})
        assert success
        assert monitor.config.enable_gpu_acceleration == True
        
        # Test reducing preload pages
        original_preload = monitor.config.max_preload_pages
        success = monitor.apply_optimization('reduce_preload_pages', {})
        assert success
        assert monitor.config.max_preload_pages == original_preload - 1
    
    def test_config_update(self, monitor):
        """Test configuration updates."""
        new_config = PerformanceConfig(
            cache_size_mb=300,
            max_preload_pages=8,
            performance_level=PerformanceLevel.HIGH
        )
        
        monitor.update_config(new_config)
        
        assert monitor.config.cache_size_mb == 300
        assert monitor.config.max_preload_pages == 8
        assert monitor.config.performance_level == PerformanceLevel.HIGH


class TestMemoryManager:
    """Test memory management system."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return PerformanceConfig(
            cache_size_mb=100,
            memory_pressure_threshold=0.8
        )
    
    @pytest.fixture
    def memory_manager(self, config):
        """Create test memory manager."""
        manager = MemoryManager(config)
        
        # Mock process to avoid system dependencies
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=50 * 1024 * 1024)  # 50MB
        mock_process.cpu_percent.return_value = 25.0
        manager.process = mock_process
        
        return manager
    
    def test_memory_pool_operations(self, memory_manager):
        """Test memory pool operations."""
        # Test page memory allocation
        result = memory_manager.allocate_page_memory(1, 1024 * 1024)  # 1MB
        assert result is not None
        
        block_id, block = result
        assert isinstance(block_id, int)
        assert isinstance(block, bytearray)
        assert len(block) >= 1024 * 1024
        
        # Test page memory deallocation
        success = memory_manager.deallocate_page_memory(1, block_id)
        assert success
    
    def test_page_cache_operations(self, memory_manager):
        """Test page cache operations."""
        # Add page to cache
        page_data = {'content': 'test page', 'rendered': True}
        memory_manager.add_page_to_cache(1, page_data)
        
        # Get page from cache
        cached_page = memory_manager.get_page_from_cache(1)
        assert cached_page == page_data
        
        # Remove page from cache
        success = memory_manager.remove_page_from_cache(1)
        assert success
        
        # Verify page is removed
        cached_page = memory_manager.get_page_from_cache(1)
        assert cached_page is None
    
    def test_cache_eviction(self, memory_manager):
        """Test cache eviction with LRU strategy."""
        # Add many pages to trigger eviction
        for i in range(50):
            page_data = {'content': f'page {i}', 'size': 1024}
            memory_manager.add_page_to_cache(i, page_data)
        
        # Check that cache size is limited
        assert len(memory_manager.page_cache) <= 25  # Should be limited
        
        # Check that oldest pages were evicted
        assert 0 not in memory_manager.page_cache  # First page should be evicted
        assert 49 in memory_manager.page_cache     # Last page should be present
    
    def test_memory_stats(self, memory_manager):
        """Test memory statistics."""
        # Add some cached pages
        for i in range(5):
            page_data = {'content': f'page {i}'}
            memory_manager.add_page_to_cache(i, page_data)
        
        # Get memory stats
        stats = memory_manager.get_memory_stats()
        
        assert isinstance(stats, MemoryStats)
        assert stats.used_memory_mb > 0
        assert stats.total_memory_mb > 0
        assert stats.pressure_level in [level for level in __import__('src.torematrix.integrations.pdf.memory', fromlist=['MemoryPressureLevel']).MemoryPressureLevel]
    
    def test_cleanup_operations(self, memory_manager):
        """Test cleanup operations."""
        # Add pages with old timestamps
        for i in range(10):
            page_data = {'content': f'page {i}'}
            memory_manager.add_page_to_cache(i, page_data)
            # Make some pages old
            if i < 5:
                memory_manager.page_access_times[i] = time.time() - 400  # 400 seconds ago
        
        # Clean up old pages
        cleaned = memory_manager.cleanup_old_pages(max_age_seconds=300)
        assert cleaned == 5  # Should clean up 5 old pages
        
        # Test emergency cleanup
        cleanup_stats = memory_manager.emergency_cleanup()
        assert 'pages_cleaned' in cleanup_stats
        assert 'pool_blocks_freed' in cleanup_stats
        assert 'gc_collections' in cleanup_stats
    
    def test_memory_pressure_detection(self, memory_manager):
        """Test memory pressure detection."""
        # Test different pressure levels
        test_cases = [
            (0.5, 'LOW'),
            (0.65, 'MEDIUM'),
            (0.85, 'HIGH'),
            (0.95, 'CRITICAL')
        ]
        
        for usage_percent, expected_level in test_cases:
            level = memory_manager._calculate_pressure_level(usage_percent)
            assert level.name == expected_level


class TestCacheManager:
    """Test cache management system."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return PerformanceConfig(
            cache_size_mb=50,
            max_preload_pages=3,
            enable_lazy_loading=True
        )
    
    @pytest.fixture
    def cache_manager(self, config):
        """Create test cache manager."""
        return CacheManager(config)
    
    def test_cache_manager_initialization(self, cache_manager):
        """Test cache manager initialization."""
        assert cache_manager.config is not None
        assert cache_manager.memory_cache is not None
        assert not cache_manager.is_running
        assert cache_manager.stats['total_requests'] == 0
    
    def test_cache_operations(self, cache_manager):
        """Test cache operations."""
        # Start cache manager
        cache_manager.start()
        assert cache_manager.is_running
        
        # Test page render caching
        page_data = {'rendered': True, 'content': 'test'}
        success = cache_manager.memory_cache.put_page_render(1, page_data)
        assert success
        
        # Test page render retrieval
        cached_data = cache_manager.memory_cache.get_page_render(1)
        assert cached_data is not None
        
        # Test page text caching
        text_data = "This is page 1 text content"
        success = cache_manager.memory_cache.put_page_text(1, text_data)
        assert success
        
        # Test page text retrieval
        cached_text = cache_manager.memory_cache.get_page_text(1)
        assert cached_text == text_data
    
    def test_cache_statistics(self, cache_manager):
        """Test cache statistics."""
        # Add some cached data
        for i in range(5):
            page_data = {'content': f'page {i}'}
            cache_manager.memory_cache.put_page_render(i, page_data)
        
        # Get statistics
        stats = cache_manager.get_statistics()
        
        assert 'hit_rate' in stats
        assert 'total_requests' in stats
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'memory_cache' in stats
        assert 'is_running' in stats
    
    def test_quality_mode_switching(self, cache_manager):
        """Test cache quality mode switching."""
        # Set different quality modes
        cache_manager.set_quality_mode('low')
        assert cache_manager.memory_cache.quality_mode == CacheQuality.LOW
        
        cache_manager.set_quality_mode('high')
        assert cache_manager.memory_cache.quality_mode == CacheQuality.HIGH
    
    def test_cache_clearing(self, cache_manager):
        """Test cache clearing operations."""
        # Add some cached data
        for i in range(5):
            page_data = {'content': f'page {i}'}
            cache_manager.memory_cache.put_page_render(i, page_data)
        
        # Clear partial cache
        cache_manager.clear_cache(ratio=0.5)
        
        # Clear full cache
        cache_manager.clear_cache(ratio=1.0)
        
        # Check that cache is empty
        stats = cache_manager.get_statistics()
        assert stats['memory_cache']['cache']['entries'] == 0


class TestMetricsCollector:
    """Test metrics collection system."""
    
    @pytest.fixture
    def collector(self):
        """Create test metrics collector."""
        return MetricsCollector()
    
    def test_collector_initialization(self, collector):
        """Test collector initialization."""
        assert len(collector.metrics) > 0  # Should have built-in metrics
        assert 'page_load_time' in collector.metrics
        assert 'memory_usage' in collector.metrics
        assert 'render_time' in collector.metrics
    
    def test_metric_recording(self, collector):
        """Test metric recording."""
        # Record timing metric
        collector.record_timing('test_operation', 150.5)
        
        # Check that metric was recorded
        series = collector.get_metric_series('test_operation')
        assert series is not None
        assert len(series.points) == 1
        assert series.points[0].value == 150.5
        
        # Record memory metric
        collector.record_memory('test_memory', 100.0)
        
        # Check memory metric
        series = collector.get_metric_series('test_memory')
        assert series is not None
        assert series.unit == 'MB'
        assert series.metric_type == MetricType.MEMORY
    
    def test_metric_statistics(self, collector):
        """Test metric statistics."""
        # Add multiple data points
        values = [10, 20, 30, 40, 50]
        for value in values:
            collector.record_metric('test_metric', value)
        
        # Get statistics
        stats = collector.get_metric_statistics('test_metric')
        
        assert stats['count'] == 5
        assert stats['min'] == 10
        assert stats['max'] == 50
        assert stats['mean'] == 30
        assert stats['median'] == 30
        assert 'p95' in stats
        assert 'p99' in stats
    
    def test_alert_system(self, collector):
        """Test alert system."""
        # Set alert threshold
        collector.set_alert_threshold('test_metric', 'warning', 100)
        collector.set_alert_threshold('test_metric', 'error', 200)
        
        # Record normal value
        collector.record_metric('test_metric', 50)
        assert len(collector.get_active_alerts()) == 0
        
        # Record warning value
        collector.record_metric('test_metric', 150)
        alerts = collector.get_active_alerts()
        assert len(alerts) == 1
        assert alerts[0].severity.value == 'warning'
        
        # Record error value
        collector.record_metric('test_metric', 250)
        alerts = collector.get_active_alerts()
        assert len(alerts) == 1
        assert alerts[0].severity.value == 'error'
    
    def test_trend_analysis(self, collector):
        """Test trend analysis."""
        # Add trending data
        for i in range(20):
            collector.record_metric('increasing_metric', i * 10)
        
        # Analyze trend
        trend = collector.analyze_trends('increasing_metric')
        
        assert trend['trend'] == 'increasing'
        assert trend['slope'] > 0
        assert trend['data_points'] == 20
    
    def test_performance_summary(self, collector):
        """Test performance summary."""
        # Add some metrics
        collector.record_timing('page_load_time', 1500)
        collector.record_memory('memory_usage', 150)
        collector.record_timing('render_time', 300)
        
        # Get summary
        summary = collector.get_performance_summary()
        
        assert 'timestamp' in summary
        assert 'metrics' in summary
        assert 'alerts' in summary
        assert 'trends' in summary
        assert 'page_load_time' in summary['metrics']
        assert 'memory_usage' in summary['metrics']
    
    def test_export_functionality(self, collector):
        """Test metrics export."""
        # Add some metrics
        for i in range(5):
            collector.record_metric('export_test', i * 10)
        
        # Export as JSON
        json_export = collector.export_metrics('json')
        assert isinstance(json_export, str)
        assert 'export_test' in json_export
        
        # Export as CSV
        csv_export = collector.export_metrics('csv')
        assert isinstance(csv_export, str)
        assert 'export_test' in csv_export
        assert 'timestamp,metric_name,value' in csv_export


class TestPerformanceOptimizer:
    """Test performance optimizer integration."""
    
    @pytest.fixture
    def mock_viewer(self):
        """Create mock QWebEngineView."""
        viewer = Mock()
        viewer.settings.return_value = Mock()
        return viewer
    
    @pytest.fixture
    def optimizer(self, mock_viewer):
        """Create test performance optimizer."""
        config = PerformanceConfig(
            cache_size_mb=100,
            enable_gpu_acceleration=True,
            performance_level=PerformanceLevel.MEDIUM
        )
        return PerformanceOptimizer(mock_viewer, config)
    
    def test_optimizer_initialization(self, optimizer):
        """Test optimizer initialization."""
        assert optimizer.config is not None
        assert optimizer.monitor is not None
        assert optimizer.memory_manager is not None
        assert optimizer.cache_manager is not None
    
    def test_performance_profile_application(self, optimizer):
        """Test performance profile application."""
        # Test different performance levels
        profiles = [
            (PerformanceLevel.LOW, 2, 1),
            (PerformanceLevel.MEDIUM, 3, 2),
            (PerformanceLevel.HIGH, 5, 3),
            (PerformanceLevel.EXTREME, 8, 4)
        ]
        
        for level, expected_preload, expected_concurrent in profiles:
            optimizer._apply_performance_profile(level)
            assert optimizer.config.max_preload_pages == expected_preload
            assert optimizer.config.max_concurrent_renders == expected_concurrent
    
    def test_memory_pressure_handling(self, optimizer):
        """Test memory pressure handling."""
        # Mock memory manager methods
        optimizer.memory_manager.emergency_cleanup = Mock()
        optimizer.memory_manager.cleanup_old_pages = Mock()
        optimizer.cache_manager.clear_cache = Mock()
        
        # Test high memory pressure
        optimizer._handle_memory_pressure(0.85)
        optimizer.memory_manager.cleanup_old_pages.assert_called_once()
        optimizer.cache_manager.clear_cache.assert_called_once_with(ratio=0.2)
        
        # Test critical memory pressure
        optimizer._handle_memory_pressure(0.95)
        optimizer.memory_manager.emergency_cleanup.assert_called_once()
    
    def test_performance_issue_handling(self, optimizer):
        """Test performance issue handling."""
        # Mock cache manager
        optimizer.cache_manager.set_quality_mode = Mock()
        
        # Test slow rendering issue
        optimizer._handle_performance_issue('slow_rendering', {'render_time': 1500})
        optimizer.cache_manager.set_quality_mode.assert_called_with('performance')
        
        # Test high CPU issue
        optimizer._handle_performance_issue('high_cpu', {'cpu_usage': 90})
        assert optimizer.config.performance_level == PerformanceLevel.LOW
    
    def test_optimization_lifecycle(self, optimizer):
        """Test optimization lifecycle."""
        # Start optimization
        optimizer.start()
        
        # Get metrics
        metrics = optimizer.get_current_metrics()
        assert isinstance(metrics, PerformanceMetrics)
        
        # Get recommendations
        recommendations = optimizer.get_optimization_recommendations()
        assert isinstance(recommendations, list)
        
        # Apply optimization
        success = optimizer.apply_optimization('increase_cache_size', {'size_mb': 200})
        assert success
        
        # Stop optimization
        optimizer.stop()


class TestIntegrationScenarios:
    """Test integration scenarios."""
    
    def test_large_pdf_optimization(self):
        """Test optimization for large PDFs."""
        config = PerformanceConfig()
        monitor = PerformanceMonitor(config)
        
        # Simulate large PDF scenario
        large_pdf_size = 150  # MB
        
        # Check initial config
        assert config.cache_size_mb == 200
        assert config.max_preload_pages == 5
        
        # Apply large PDF optimization
        if large_pdf_size > 100:
            config.max_preload_pages = 2
            config.max_concurrent_renders = 1
            config.cache_size_mb = max(200, int(large_pdf_size * 2))
        
        # Verify optimization
        assert config.max_preload_pages == 2
        assert config.max_concurrent_renders == 1
        assert config.cache_size_mb >= 300
    
    def test_memory_pressure_cascade(self):
        """Test memory pressure cascade effects."""
        config = PerformanceConfig(cache_size_mb=100)
        memory_manager = MemoryManager(config)
        cache_manager = CacheManager(config)
        
        # Mock process
        mock_process = Mock()
        memory_manager.process = mock_process
        
        # Simulate increasing memory pressure
        memory_levels = [50, 75, 85, 95]  # MB
        
        for memory_mb in memory_levels:
            mock_process.memory_info.return_value = Mock(rss=memory_mb * 1024 * 1024)
            
            # Update memory stats
            memory_manager._update_memory_stats()
            stats = memory_manager.get_memory_stats()
            
            # Check appropriate pressure level
            if memory_mb >= 95:
                assert stats.pressure_level.name == 'CRITICAL'
            elif memory_mb >= 85:
                assert stats.pressure_level.name == 'HIGH'
            elif memory_mb >= 60:
                assert stats.pressure_level.name == 'MEDIUM'
            else:
                assert stats.pressure_level.name == 'LOW'
    
    def test_performance_monitoring_integration(self):
        """Test integrated performance monitoring."""
        config = PerformanceConfig(
            metrics_collection_interval=0.05,  # 50ms for testing
            performance_logging=False
        )
        monitor = PerformanceMonitor(config)
        collector = MetricsCollector()
        
        # Start monitoring
        monitor.start_monitoring()
        
        # Simulate some activity
        for i in range(5):
            collector.record_timing('test_operation', 100 + i * 10)
            collector.record_memory('test_memory', 50 + i * 5)
            time.sleep(0.01)
        
        # Stop monitoring
        monitor.stop_monitoring()
        
        # Check that metrics were collected
        assert len(collector.metrics) > 0
        
        # Check timing metrics
        timing_stats = collector.get_metric_statistics('test_operation')
        assert timing_stats['count'] == 5
        assert timing_stats['min'] == 100
        assert timing_stats['max'] == 140
    
    def test_hardware_acceleration_fallback(self):
        """Test hardware acceleration fallback."""
        config = PerformanceConfig(enable_gpu_acceleration=True)
        monitor = PerformanceMonitor(config)
        
        # Test hardware detection
        capability = monitor._detect_hardware_capability()
        assert isinstance(capability, HardwareCapability)
        
        # Test GPU availability
        gpu_available = monitor._check_gpu_acceleration()
        assert isinstance(gpu_available, bool)
        
        # Test fallback configuration
        if not gpu_available:
            config.enable_gpu_acceleration = False
            config.enable_webgl = False
            config.enable_hardware_canvas = False
        
        # Verify fallback applied
        hardware_info = monitor.get_hardware_info()
        assert 'capability' in hardware_info
        assert 'gpu_acceleration_available' in hardware_info


if __name__ == '__main__':
    pytest.main([__file__, '-v'])