"""
Unit tests for performance monitoring and optimization.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, MagicMock, patch

from src.torematrix.core.state.performance.monitor import (
    PerformanceMonitor, PerformanceEntry, PerformanceStats, performance_monitor
)
from src.torematrix.core.state.performance.metrics import (
    MetricsCollector, StateMetrics, MetricType, MetricValue, metrics_collector
)
from src.torematrix.core.state.performance.optimization import (
    OptimizationEngine, OptimizationLevel, PerformanceThresholds,
    SelectorCacheOptimization, MemoryOptimization, OptimizationContext
)


class TestPerformanceMonitor:
    """Test PerformanceMonitor functionality."""
    
    def test_monitor_creation(self):
        """Test monitor creation."""
        monitor = PerformanceMonitor()
        assert monitor.max_entries == 10000
        assert monitor.enable_memory_tracking is True
        assert len(monitor._entries) == 0
        assert len(monitor._stats) == 0
    
    def test_measure_context_manager(self):
        """Test measure context manager."""
        monitor = PerformanceMonitor(enable_memory_tracking=False)
        
        with monitor.measure('test_operation') as measurement_id:
            time.sleep(0.001)  # 1ms delay
            assert isinstance(measurement_id, str)
            assert 'test_operation' in measurement_id
        
        # Check that measurement was recorded
        assert len(monitor._entries) == 1
        assert len(monitor._stats) == 1
        assert 'test_operation' in monitor._stats
        
        stats = monitor._stats['test_operation']
        assert stats.call_count == 1
        assert stats.avg_time > 0
    
    def test_track_selector_decorator(self):
        """Test track_selector decorator."""
        monitor = PerformanceMonitor(enable_memory_tracking=False)
        
        @monitor.track_selector('test_selector')
        def test_function(x):
            time.sleep(0.001)
            return x * 2
        
        result = test_function(21)
        assert result == 42
        
        stats = monitor.get_stats('selector_test_selector')
        assert stats['total_calls'] == 1
        assert stats['avg_execution_time_ms'] > 0
    
    @pytest.mark.asyncio
    async def test_track_async_selector_decorator(self):
        """Test track_async_selector decorator."""
        monitor = PerformanceMonitor(enable_memory_tracking=False)
        
        @monitor.track_async_selector('async_test_selector')
        async def async_test_function(x):
            await asyncio.sleep(0.001)
            return x * 3
        
        result = await async_test_function(14)
        assert result == 42
        
        stats = monitor.get_stats('async_selector_async_test_selector')
        assert stats['total_calls'] == 1
        assert stats['avg_execution_time_ms'] > 0
    
    def test_performance_alerts(self):
        """Test performance alert system."""
        monitor = PerformanceMonitor(enable_memory_tracking=False)
        
        alert_triggered = False
        alert_entry = None
        alert_threshold = None
        
        def alert_callback(entry, threshold):
            nonlocal alert_triggered, alert_entry, alert_threshold
            alert_triggered = True
            alert_entry = entry
            alert_threshold = threshold
        
        monitor.add_alert_callback(alert_callback)
        monitor.set_alert_threshold('slow_operation', 5.0)  # 5ms threshold
        
        with monitor.measure('slow_operation'):
            time.sleep(0.01)  # 10ms delay - should trigger alert
        
        assert alert_triggered
        assert alert_entry.name == 'slow_operation'
        assert alert_entry.duration > 0.005  # > 5ms
        assert alert_threshold == 0.005  # 5ms in seconds
    
    def test_get_performance_report(self):
        """Test performance report generation."""
        monitor = PerformanceMonitor(enable_memory_tracking=False)
        
        # Generate some measurements
        for i in range(5):
            with monitor.measure('test_op'):
                time.sleep(0.001)
        
        report = monitor.get_performance_report()
        
        assert 'summary' in report
        assert 'operations' in report
        assert 'alerts' in report
        
        assert report['summary']['total_operations'] == 1
        assert report['summary']['total_measurements'] == 5
        
        assert 'test_op' in report['operations']
        op_stats = report['operations']['test_op']
        assert op_stats['call_count'] == 5
        assert op_stats['avg_time_ms'] > 0
        assert op_stats['performance_grade'] in ['A+', 'A', 'B', 'C', 'D']
    
    @pytest.mark.asyncio
    async def test_real_time_monitoring(self):
        """Test real-time monitoring."""
        monitor = PerformanceMonitor(enable_memory_tracking=False)
        
        # Start monitoring
        await monitor.start_real_time_monitoring(interval=0.1)
        assert monitor._monitoring_active
        
        # Generate some measurements
        with monitor.measure('monitored_op'):
            time.sleep(0.001)
        
        # Wait for monitoring cycle
        await asyncio.sleep(0.15)
        
        # Stop monitoring
        await monitor.stop_real_time_monitoring()
        assert not monitor._monitoring_active
    
    def test_memory_tracking(self):
        """Test memory usage tracking."""
        monitor = PerformanceMonitor(enable_memory_tracking=True)
        
        with monitor.measure('memory_test'):
            # Allocate some memory
            large_list = [i for i in range(10000)]
            del large_list
        
        stats = monitor.get_stats('memory_test')
        # Memory tracking should work (though exact values depend on system)
        assert 'avg_memory_delta_kb' in stats
    
    def test_stats_aggregation(self):
        """Test statistics aggregation."""
        monitor = PerformanceMonitor(enable_memory_tracking=False)
        
        # Generate measurements with different durations
        for i in range(10):
            with monitor.measure('varying_op'):
                time.sleep(0.001 * (i + 1))  # Increasing delays
        
        stats = monitor._stats['varying_op']
        assert stats.call_count == 10
        assert stats.min_time > 0
        assert stats.max_time > stats.min_time
        assert stats.avg_time > 0
        assert stats.p95_time > 0
        assert stats.p99_time >= stats.p95_time


class TestMetricsCollector:
    """Test MetricsCollector functionality."""
    
    def test_collector_creation(self):
        """Test collector creation."""
        collector = MetricsCollector()
        assert collector.buffer_size == 10000
        assert collector.aggregation_interval == 1.0
        assert len(collector._metrics) == 0
    
    def test_record_counter(self):
        """Test counter metric recording."""
        collector = MetricsCollector()
        
        collector.record_counter('test_counter', 1)
        collector.record_counter('test_counter', 5)
        collector.record_counter('test_counter', 3)
        
        summary = collector.get_metric_summary('test_counter')
        assert summary['name'] == 'test_counter'
        assert summary['type'] == 'counter'
        assert summary['count'] == 3
        assert summary['total'] == 9
    
    def test_record_gauge(self):
        """Test gauge metric recording."""
        collector = MetricsCollector()
        
        collector.record_gauge('memory_usage', 100.5)
        collector.record_gauge('memory_usage', 105.2)
        collector.record_gauge('memory_usage', 98.7)
        
        summary = collector.get_metric_summary('memory_usage')
        assert summary['type'] == 'gauge'
        assert summary['count'] == 3
        assert summary['latest'] == 98.7
        assert summary['min'] == 98.7
        assert summary['max'] == 105.2
    
    def test_record_timer(self):
        """Test timer metric recording."""
        collector = MetricsCollector()
        
        collector.record_timer('operation_time', 15.5)
        collector.record_timer('operation_time', 12.3)
        collector.record_timer('operation_time', 18.7)
        
        summary = collector.get_metric_summary('operation_time')
        assert summary['type'] == 'timer'
        assert summary['count'] == 3
        assert summary['avg'] > 0
        assert summary['p95'] > 0
        assert summary['p99'] > 0
    
    def test_timer_context_manager(self):
        """Test timer context manager."""
        collector = MetricsCollector()
        
        with collector.timer('context_timer'):
            time.sleep(0.001)
        
        summary = collector.get_metric_summary('context_timer')
        assert summary['count'] == 1
        assert summary['avg'] > 0
    
    def test_increment_convenience_method(self):
        """Test increment convenience method."""
        collector = MetricsCollector()
        
        collector.increment('page_views')
        collector.increment('page_views', 5)
        
        summary = collector.get_metric_summary('page_views')
        assert summary['total'] == 6
    
    def test_set_gauge_convenience_method(self):
        """Test set_gauge convenience method."""
        collector = MetricsCollector()
        
        collector.set_gauge('cpu_usage', 45.6)
        collector.set_gauge('cpu_usage', 52.3)
        
        summary = collector.get_metric_summary('cpu_usage')
        assert summary['latest'] == 52.3
    
    def test_get_state_metrics(self):
        """Test state metrics aggregation."""
        collector = MetricsCollector()
        
        # Simulate various metrics
        collector.record_timer('selector_execution_time', 2.5)
        collector.record_counter('selector_cache_hits', 95)
        collector.record_counter('selector_cache_misses', 5)
        collector.record_timer('state_update_time', 8.2)
        collector.set_gauge('memory_usage', 256.7)
        collector.set_gauge('frame_rate', 58.3)
        
        state_metrics = collector.get_state_metrics()
        
        assert isinstance(state_metrics, StateMetrics)
        assert state_metrics.selector_avg_execution_time_ms == 2.5
        assert state_metrics.selector_cache_hits == 95
        assert state_metrics.selector_cache_misses == 5
        assert state_metrics.memory_usage_mb == 256.7
        assert state_metrics.frame_rate == 58.3
    
    def test_metric_callbacks(self):
        """Test metric callbacks."""
        collector = MetricsCollector()
        
        callback_triggered = False
        callback_name = None
        callback_value = None
        
        def test_callback(name, metric_value):
            nonlocal callback_triggered, callback_name, callback_value
            callback_triggered = True
            callback_name = name
            callback_value = metric_value
        
        collector.add_metric_callback('test_metric', test_callback)
        collector.record_gauge('test_metric', 42.0)
        
        assert callback_triggered
        assert callback_name == 'test_metric'
        assert callback_value.value == 42.0
    
    @pytest.mark.asyncio
    async def test_aggregation_loop(self):
        """Test background aggregation."""
        collector = MetricsCollector(aggregation_interval=0.1)
        
        await collector.start_aggregation()
        assert collector._running
        
        # Add some metrics
        collector.record_counter('test_counter', 1)
        
        # Wait for aggregation
        await asyncio.sleep(0.15)
        
        await collector.stop_aggregation()
        assert not collector._running
    
    def test_export_metrics_json(self):
        """Test JSON metrics export."""
        collector = MetricsCollector()
        
        collector.record_counter('requests', 100)
        collector.set_gauge('active_users', 42)
        
        exported = collector.export_metrics('json')
        
        assert 'metrics' in exported
        assert 'state_metrics' in exported
        assert 'timestamp' in exported
        assert 'requests' in exported['metrics']
        assert 'active_users' in exported['metrics']
    
    def test_export_metrics_prometheus(self):
        """Test Prometheus metrics export."""
        collector = MetricsCollector()
        
        collector.record_counter('http_requests', 150)
        collector.set_gauge('memory_bytes', 1024)
        
        exported = collector.export_metrics('prometheus')
        
        assert isinstance(exported, str)
        assert 'http_requests_total' in exported
        assert 'memory_bytes' in exported
        assert '150' in exported
        assert '1024' in exported


class TestOptimizationEngine:
    """Test OptimizationEngine functionality."""
    
    def test_engine_creation(self):
        """Test optimization engine creation."""
        engine = OptimizationEngine()
        assert engine.optimization_level == OptimizationLevel.BALANCED
        assert isinstance(engine.thresholds, PerformanceThresholds)
        assert len(engine._strategies) > 0
    
    @pytest.mark.asyncio
    async def test_analyze_performance(self):
        """Test performance analysis."""
        engine = OptimizationEngine()
        
        # Create metrics that should trigger issues
        metrics = {
            'selector': {
                'avg_execution_time_ms': 25.0,  # Above 10ms threshold
                'cache_hit_rate': 75.0  # Below 90% threshold
            },
            'memory': {
                'growth_rate_mb_per_min': 15.0  # Above 10MB/min threshold
            },
            'performance': {
                'frame_rate': 45.0,  # Below 60fps
                'render_time_ms': 20.0  # Above 16ms threshold
            }
        }
        
        analysis = await engine.analyze_performance(metrics)
        
        assert len(analysis['issues']) > 0
        assert len(analysis['critical_issues']) > 0
        assert analysis['optimization_score'] < 100
        
        # Check for specific issues
        issue_types = [issue['type'] for issue in analysis['issues']]
        assert 'selector_performance' in issue_types
        assert 'cache_efficiency' in issue_types
        assert 'frame_rate' in issue_types
        
        critical_types = [issue['type'] for issue in analysis['critical_issues']]
        assert 'memory_leak' in critical_types
    
    @pytest.mark.asyncio
    async def test_optimization_execution(self):
        """Test optimization execution."""
        engine = OptimizationEngine()
        
        # Create mock context
        mock_selector = Mock()
        mock_selector.name = 'test_selector'
        mock_selector.get_stats.return_value = {
            'cache_hit_rate': 75,
            'call_count': 200
        }
        mock_selector._max_cache_size = 100
        
        mock_subscription_manager = Mock()
        mock_subscription_manager.enable_batching = Mock()
        mock_subscription_manager.cleanup_dead_subscriptions = Mock(return_value=5)
        
        context = OptimizationContext(
            metrics={
                'selector': {'cache_hit_rate': 75, 'avg_execution_time_ms': 8},
                'subscriptions': {'avg_notification_time_ms': 8, 'active_count': 500}
            },
            selectors=[mock_selector],
            high_frequency_selectors=[mock_selector],
            subscription_manager=mock_subscription_manager,
            state_manager=Mock(),
            update_batcher=Mock(),
            element_renderer=Mock(),
            thresholds=engine.thresholds
        )
        
        result = await engine.optimize(context)
        
        assert result['total_optimizations'] > 0
        assert len(result['strategies_applied']) > 0
        
        # Check that optimizations were applied
        mock_subscription_manager.enable_batching.assert_called()
        mock_subscription_manager.cleanup_dead_subscriptions.assert_called()
    
    @pytest.mark.asyncio
    async def test_auto_optimization(self):
        """Test automatic optimization."""
        engine = OptimizationEngine()
        
        metrics_call_count = 0
        context_call_count = 0
        
        def metrics_provider():
            nonlocal metrics_call_count
            metrics_call_count += 1
            return {
                'selector': {'avg_execution_time_ms': 15},  # Trigger optimization
                'memory': {'growth_rate_mb_per_min': 5},
                'performance': {'frame_rate': 60}
            }
        
        def context_provider():
            nonlocal context_call_count
            context_call_count += 1
            return OptimizationContext(
                metrics={},
                selectors=[],
                high_frequency_selectors=[],
                subscription_manager=Mock(),
                state_manager=Mock(),
                update_batcher=Mock(),
                element_renderer=Mock(),
                thresholds=engine.thresholds
            )
        
        # Start auto-optimization with short interval
        await engine.start_auto_optimization(
            metrics_provider=metrics_provider,
            context_provider=context_provider,
            interval=0.1
        )
        
        assert engine._running
        
        # Wait for at least one optimization cycle
        await asyncio.sleep(0.15)
        
        await engine.stop_auto_optimization()
        assert not engine._running
        
        # Should have been called at least once
        assert metrics_call_count > 0
    
    def test_optimization_stats(self):
        """Test optimization statistics."""
        engine = OptimizationEngine()
        
        # Add some fake history
        engine._optimization_history.append({
            'total_optimizations': 5,
            'strategies_applied': [{'strategy': 'cache_optimization'}]
        })
        engine._optimization_history.append({
            'total_optimizations': 3,
            'strategies_applied': [{'strategy': 'memory_optimization'}]
        })
        
        stats = engine.get_optimization_stats()
        
        assert stats['total_optimizations'] == 8
        assert stats['optimization_runs'] == 2
        assert stats['avg_optimizations_per_run'] == 4.0
        assert 'cache_optimization' in stats['strategies_used']
        assert 'memory_optimization' in stats['strategies_used']


class TestOptimizationStrategies:
    """Test individual optimization strategies."""
    
    def test_selector_cache_optimization(self):
        """Test selector cache optimization strategy."""
        strategy = SelectorCacheOptimization()
        
        # Test can_optimize
        poor_metrics = {
            'selector': {'cache_hit_rate': 75, 'avg_execution_time_ms': 8}
        }
        assert strategy.can_optimize(poor_metrics)
        
        good_metrics = {
            'selector': {'cache_hit_rate': 95, 'avg_execution_time_ms': 2}
        }
        assert not strategy.can_optimize(good_metrics)
    
    @pytest.mark.asyncio
    async def test_memory_optimization(self):
        """Test memory optimization strategy."""
        strategy = MemoryOptimization()
        
        # Test can_optimize
        high_memory_metrics = {
            'memory': {'growth_rate_mb_per_min': 15, 'usage_mb': 1200}
        }
        assert strategy.can_optimize(high_memory_metrics)
        
        low_memory_metrics = {
            'memory': {'growth_rate_mb_per_min': 2, 'usage_mb': 100}
        }
        assert not strategy.can_optimize(low_memory_metrics)
        
        # Test optimization execution
        mock_selector = Mock()
        mock_selector.name = 'test_selector'
        mock_selector.get_stats = Mock(return_value={'cache_hit_rate': 40})
        mock_selector.invalidate = Mock()
        
        context = OptimizationContext(
            metrics=high_memory_metrics,
            selectors=[mock_selector],
            high_frequency_selectors=[],
            subscription_manager=Mock(),
            state_manager=Mock(),
            update_batcher=Mock(),
            element_renderer=Mock(),
            thresholds=PerformanceThresholds()
        )
        
        result = await strategy.optimize(context)
        
        assert result['strategy'] == 'memory_optimization'
        assert len(result['optimizations']) > 0
        mock_selector.invalidate.assert_called_once()


class TestBenchmarks:
    """Performance benchmarks for 10k+ elements."""
    
    def test_large_state_selector_performance(self):
        """Benchmark selector performance with 10k+ elements."""
        from src.torematrix.core.state.selectors.base import create_selector
        from src.torematrix.core.state.selectors.common import get_elements
        
        # Create large state with 10k elements
        large_elements = [
            {
                'id': i,
                'type': 'text' if i % 3 == 0 else 'image' if i % 3 == 1 else 'table',
                'visible': i % 4 != 0,
                'status': 'validated' if i % 5 == 0 else 'pending'
            }
            for i in range(10000)
        ]
        
        state = {'elements': large_elements}
        
        # Test various selectors
        def get_text_elements(elements):
            return [e for e in elements if e['type'] == 'text']
        
        def get_validated_elements(elements):
            return [e for e in elements if e['status'] == 'validated']
        
        text_selector = create_selector(get_elements, get_text_elements, name='get_text_elements')
        validated_selector = create_selector(get_elements, get_validated_elements, name='get_validated_elements')
        
        # Benchmark execution times
        start_time = time.perf_counter()
        text_result = text_selector(state)
        text_time = (time.perf_counter() - start_time) * 1000
        
        start_time = time.perf_counter()
        validated_result = validated_selector(state)
        validated_time = (time.perf_counter() - start_time) * 1000
        
        # Verify results
        assert len(text_result) > 0
        assert len(validated_result) > 0
        assert all(elem['type'] == 'text' for elem in text_result)
        assert all(elem['status'] == 'validated' for elem in validated_result)
        
        # Performance targets: <10ms for complex selectors with 10k elements
        assert text_time < 10.0, f"Text selector took {text_time:.2f}ms (target: <10ms)"
        assert validated_time < 10.0, f"Validated selector took {validated_time:.2f}ms (target: <10ms)"
        
        # Test cache performance
        start_time = time.perf_counter()
        text_result_cached = text_selector(state)
        cached_time = (time.perf_counter() - start_time) * 1000
        
        assert text_result_cached == text_result
        assert cached_time < 1.0, f"Cached selector took {cached_time:.2f}ms (target: <1ms)"
        
        # Verify cache hit rate
        stats = text_selector.get_stats()
        assert stats['cache_hit_rate'] >= 50  # At least 50% hit rate
    
    def test_subscription_performance_10k_elements(self):
        """Benchmark subscription performance with 10k updates."""
        from src.torematrix.core.state.subscription import SubscriptionManager, StateChange
        
        manager = SubscriptionManager(batch_notifications=True, batch_timeout_ms=1.0)
        
        callback_count = 0
        
        def test_callback(change):
            nonlocal callback_count
            callback_count += 1
        
        # Subscribe to pattern that matches many paths
        manager.subscribe_to_pattern('elements.*', test_callback)
        
        # Generate 10k state changes
        changes = [
            StateChange(
                path=f'elements.{i}',
                old_value={'status': 'pending'},
                new_value={'status': 'validated'}
            )
            for i in range(10000)
        ]
        
        # Benchmark notification time
        start_time = time.perf_counter()
        manager.notify_state_change(changes)
        notification_time = (time.perf_counter() - start_time) * 1000
        
        # Performance target: <50ms for 10k notifications
        assert notification_time < 50.0, f"Notifications took {notification_time:.2f}ms (target: <50ms)"
        
        # Wait for batch processing
        time.sleep(0.01)
        
        # Should have batched many notifications
        stats = manager.get_subscription_stats()
        assert stats['total_notifications'] > 0
    
    def test_metrics_collection_performance(self):
        """Benchmark metrics collection performance."""
        collector = MetricsCollector()
        
        # Benchmark 10k metric recordings
        start_time = time.perf_counter()
        
        for i in range(10000):
            collector.record_counter('requests', 1)
            collector.record_gauge('memory', 100 + i % 100)
            collector.record_timer('response_time', 10 + (i % 50))
        
        collection_time = (time.perf_counter() - start_time) * 1000
        
        # Performance target: <100ms for 30k recordings
        assert collection_time < 100.0, f"Metrics collection took {collection_time:.2f}ms (target: <100ms)"
        
        # Verify metrics were recorded
        assert collector.get_metric_summary('requests')['total'] == 10000
        assert collector.get_metric_summary('memory')['count'] == 10000
        assert collector.get_metric_summary('response_time')['count'] == 10000


if __name__ == '__main__':
    pytest.main([__file__])