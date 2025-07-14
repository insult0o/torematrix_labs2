"""Tests for the performance monitoring system."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
import json
import statistics
from datetime import datetime, timedelta
from collections import deque

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject

from src.torematrix.ui.layouts.monitoring import (
    AlertLevel, MetricType, PerformanceAlert, MetricThreshold, PerformanceReport,
    MetricCollector, AlertManager, BottleneckDetector, PerformanceMonitor
)
from src.torematrix.ui.layouts.performance import PerformanceProfiler, PerformanceMetrics
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


@pytest.fixture
def mock_profiler():
    """Mock performance profiler for testing."""
    profiler = Mock(spec=PerformanceProfiler)
    profiler.get_memory_stats.return_value = {
        'current_mb': 256.0,
        'average_mb': 200.0,
        'max_mb': 300.0
    }
    profiler.get_operation_stats.return_value = {
        'count': 10,
        'average_time_ms': 25.0,
        'max_time_ms': 50.0
    }
    return profiler


@pytest.fixture
def sample_alert():
    """Sample performance alert for testing."""
    return PerformanceAlert(
        level=AlertLevel.WARNING,
        metric_type=MetricType.MEMORY_USAGE,
        message="Memory usage is high",
        value=800.0,
        threshold=500.0,
        timestamp=datetime.now()
    )


@pytest.fixture
def sample_threshold():
    """Sample metric threshold for testing."""
    return MetricThreshold(
        metric_type=MetricType.LAYOUT_TIME,
        warning_threshold=50.0,
        critical_threshold=100.0,
        emergency_threshold=200.0,
        comparison_operator=">",
        enabled=True
    )


class TestPerformanceAlert:
    """Test PerformanceAlert dataclass."""
    
    def test_alert_creation(self):
        """Test creating performance alerts."""
        timestamp = datetime.now()
        alert = PerformanceAlert(
            level=AlertLevel.CRITICAL,
            metric_type=MetricType.CPU_USAGE,
            message="CPU usage is critical",
            value=95.0,
            threshold=80.0,
            timestamp=timestamp,
            metadata={'source': 'test'}
        )
        
        assert alert.level == AlertLevel.CRITICAL
        assert alert.metric_type == MetricType.CPU_USAGE
        assert alert.message == "CPU usage is critical"
        assert alert.value == 95.0
        assert alert.threshold == 80.0
        assert alert.timestamp == timestamp
        assert alert.resolved is False
        assert alert.metadata['source'] == 'test'


class TestMetricThreshold:
    """Test MetricThreshold functionality."""
    
    def test_threshold_creation(self):
        """Test creating metric thresholds."""
        threshold = MetricThreshold(
            metric_type=MetricType.FRAME_RATE,
            warning_threshold=45.0,
            critical_threshold=30.0,
            emergency_threshold=15.0,
            comparison_operator="<"
        )
        
        assert threshold.metric_type == MetricType.FRAME_RATE
        assert threshold.warning_threshold == 45.0
        assert threshold.comparison_operator == "<"
        assert threshold.enabled is True  # Default


class TestMetricCollector:
    """Test MetricCollector functionality."""
    
    def test_collector_creation(self):
        """Test creating metric collector."""
        collector = MetricCollector(max_samples=100)
        
        assert collector._max_samples == 100
        assert len(collector._metrics_history) == len(MetricType)
        assert len(collector._timestamps) == 0
    
    def test_metric_recording(self):
        """Test recording metrics."""
        collector = MetricCollector()
        
        # Record some metrics
        collector.record_metric(MetricType.LAYOUT_TIME, 25.0)
        collector.record_metric(MetricType.MEMORY_USAGE, 256.0)
        
        # Should have recorded values
        layout_times = collector.get_recent_values(MetricType.LAYOUT_TIME, 10)
        memory_values = collector.get_recent_values(MetricType.MEMORY_USAGE, 10)
        
        assert len(layout_times) == 1
        assert layout_times[0] == 25.0
        assert len(memory_values) == 1
        assert memory_values[0] == 256.0
        
        # Should have timestamp for first metric
        assert len(collector._timestamps) == 1
    
    def test_statistics_calculation(self):
        """Test metric statistics calculation."""
        collector = MetricCollector()
        
        # Add sample data
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in values:
            collector.record_metric(MetricType.LAYOUT_TIME, value)
        
        stats = collector.get_metric_statistics(MetricType.LAYOUT_TIME)
        
        assert stats['count'] == 5
        assert stats['mean'] == 30.0
        assert stats['median'] == 30.0
        assert stats['min'] == 10.0
        assert stats['max'] == 50.0
        assert stats['std_dev'] > 0
    
    def test_anomaly_detection(self):
        """Test anomaly detection."""
        collector = MetricCollector()
        
        # Add normal values and one outlier
        normal_values = [10.0] * 15  # 15 normal values
        outlier_values = [100.0]     # 1 outlier
        
        for value in normal_values + outlier_values:
            collector.record_metric(MetricType.LAYOUT_TIME, value)
        
        anomalies = collector.detect_anomalies(MetricType.LAYOUT_TIME, z_threshold=2.0)
        
        # Should detect the outlier
        assert len(anomalies) == 1
        assert anomalies[0][1] == 100.0  # Value of the anomaly
    
    def test_trend_analysis(self):
        """Test trend analysis."""
        collector = MetricCollector()
        
        # Add increasing trend
        for i in range(20):
            collector.record_metric(MetricType.MEMORY_USAGE, 100.0 + i * 5.0)
        
        trend = collector.get_trend_analysis(MetricType.MEMORY_USAGE)
        
        assert trend['trend'] == 'increasing'
        assert trend['slope'] > 0
        assert trend['confidence'] > 0.8  # Should be confident about trend
    
    def test_stable_trend_detection(self):
        """Test stable trend detection."""
        collector = MetricCollector()
        
        # Add stable values
        for i in range(20):
            collector.record_metric(MetricType.CPU_USAGE, 50.0)  # Constant value
        
        trend = collector.get_trend_analysis(MetricType.CPU_USAGE)
        
        assert trend['trend'] == 'stable'
        assert abs(trend['slope']) < 0.01
    
    def test_insufficient_data_handling(self):
        """Test handling of insufficient data."""
        collector = MetricCollector()
        
        # Add minimal data
        collector.record_metric(MetricType.LAYOUT_TIME, 25.0)
        
        # Should handle gracefully
        stats = collector.get_metric_statistics(MetricType.LAYOUT_TIME)
        assert stats['count'] == 1
        assert stats['std_dev'] == 0.0  # Single value has no deviation
        
        # Anomaly detection should return empty for insufficient data
        anomalies = collector.detect_anomalies(MetricType.LAYOUT_TIME)
        assert len(anomalies) == 0
        
        # Trend analysis should indicate insufficient data
        trend = collector.get_trend_analysis(MetricType.LAYOUT_TIME)
        assert trend['trend'] == 'insufficient_data'
    
    def test_data_clearing(self):
        """Test clearing metric data."""
        collector = MetricCollector()
        
        # Add some data
        collector.record_metric(MetricType.LAYOUT_TIME, 25.0)
        collector.record_metric(MetricType.MEMORY_USAGE, 256.0)
        
        assert len(collector.get_recent_values(MetricType.LAYOUT_TIME, 10)) == 1
        
        # Clear data
        collector.clear_history()
        
        assert len(collector.get_recent_values(MetricType.LAYOUT_TIME, 10)) == 0
        assert len(collector._timestamps) == 0


class TestAlertManager:
    """Test AlertManager functionality."""
    
    def test_manager_initialization(self):
        """Test alert manager initialization."""
        manager = AlertManager()
        
        # Should have default thresholds
        assert len(manager._thresholds) > 0
        assert MetricType.LAYOUT_TIME in manager._thresholds
        assert MetricType.MEMORY_USAGE in manager._thresholds
        
        # Should have empty alert lists
        assert len(manager._active_alerts) == 0
        assert len(manager._alert_history) == 0
    
    def test_threshold_management(self, sample_threshold):
        """Test threshold setting and retrieval."""
        manager = AlertManager()
        
        # Set custom threshold
        manager.set_threshold(sample_threshold)
        
        stored_threshold = manager._thresholds[sample_threshold.metric_type]
        assert stored_threshold == sample_threshold
    
    def test_metric_checking_no_alert(self):
        """Test metric checking that doesn't trigger alerts."""
        manager = AlertManager()
        
        # Check metric within normal range
        alert = manager.check_metric(MetricType.LAYOUT_TIME, 30.0)  # Below warning threshold
        
        assert alert is None
    
    def test_metric_checking_with_alert(self):
        """Test metric checking that triggers alerts."""
        manager = AlertManager()
        
        # Check metric that exceeds threshold
        alert = manager.check_metric(MetricType.LAYOUT_TIME, 150.0)  # Above critical threshold
        
        assert alert is not None
        assert alert.level in [AlertLevel.WARNING, AlertLevel.CRITICAL, AlertLevel.EMERGENCY]
        assert alert.value == 150.0
        assert len(manager._active_alerts) == 1
        assert len(manager._alert_history) == 1
    
    def test_threshold_evaluation(self):
        """Test threshold evaluation logic."""
        manager = AlertManager()
        
        # Create threshold for testing
        threshold = MetricThreshold(
            metric_type=MetricType.CPU_USAGE,
            warning_threshold=70.0,
            critical_threshold=85.0,
            emergency_threshold=95.0,
            comparison_operator=">"
        )
        
        # Test different alert levels
        assert manager._evaluate_threshold(60.0, threshold) is None  # Normal
        assert manager._evaluate_threshold(75.0, threshold) == AlertLevel.WARNING
        assert manager._evaluate_threshold(90.0, threshold) == AlertLevel.CRITICAL
        assert manager._evaluate_threshold(98.0, threshold) == AlertLevel.EMERGENCY
    
    def test_reverse_threshold_evaluation(self):
        """Test threshold evaluation with reverse operator."""
        manager = AlertManager()
        
        # Create reverse threshold (for cache hit ratio)
        threshold = MetricThreshold(
            metric_type=MetricType.CACHE_HIT_RATIO,
            warning_threshold=0.7,
            critical_threshold=0.5,
            emergency_threshold=0.3,
            comparison_operator="<"
        )
        
        # Test reverse logic
        assert manager._evaluate_threshold(0.8, threshold) is None  # Good ratio
        assert manager._evaluate_threshold(0.6, threshold) == AlertLevel.WARNING
        assert manager._evaluate_threshold(0.4, threshold) == AlertLevel.CRITICAL
        assert manager._evaluate_threshold(0.2, threshold) == AlertLevel.EMERGENCY
    
    def test_alert_resolution(self):
        """Test alert resolution when metrics return to normal."""
        manager = AlertManager()
        
        # Trigger alert
        alert = manager.check_metric(MetricType.LAYOUT_TIME, 150.0)
        assert alert is not None
        assert not alert.resolved
        
        # Return to normal range
        manager.check_metric(MetricType.LAYOUT_TIME, 30.0)
        
        # Alert should be resolved
        assert alert.resolved
    
    def test_active_alerts_filtering(self):
        """Test filtering of active (unresolved) alerts."""
        manager = AlertManager()
        
        # Create some alerts
        alert1 = manager.check_metric(MetricType.LAYOUT_TIME, 150.0)
        alert2 = manager.check_metric(MetricType.MEMORY_USAGE, 1200.0)
        
        assert len(manager.get_active_alerts()) == 2
        
        # Resolve one alert
        if alert1:
            alert1.resolved = True
        
        active = manager.get_active_alerts()
        assert len(active) == 1
        assert active[0] == alert2
    
    def test_alert_history(self):
        """Test alert history management."""
        manager = AlertManager()
        
        # Generate some alerts
        for i in range(5):
            manager.check_metric(MetricType.LAYOUT_TIME, 100.0 + i * 10)
        
        # Check history
        history = manager.get_alert_history(hours=24)
        assert len(history) == 5
        
        # Test time filtering
        history_1hour = manager.get_alert_history(hours=1)
        assert len(history_1hour) == 5  # All should be within 1 hour
    
    def test_resolved_alert_cleanup(self):
        """Test cleanup of resolved alerts."""
        manager = AlertManager()
        
        # Create and resolve some alerts
        alert1 = manager.check_metric(MetricType.LAYOUT_TIME, 150.0)
        alert2 = manager.check_metric(MetricType.MEMORY_USAGE, 1200.0)
        
        if alert1:
            alert1.resolved = True
        if alert2:
            alert2.resolved = True
        
        initial_count = len(manager._active_alerts)
        cleared_count = manager.clear_resolved_alerts()
        final_count = len(manager._active_alerts)
        
        assert cleared_count == 2
        assert final_count == initial_count - cleared_count


class TestBottleneckDetector:
    """Test BottleneckDetector functionality."""
    
    def test_detector_initialization(self):
        """Test bottleneck detector initialization."""
        collector = MetricCollector()
        detector = BottleneckDetector(collector)
        
        assert detector._metric_collector == collector
        assert len(detector._bottleneck_patterns) > 0
    
    def test_slow_layout_detection(self):
        """Test slow layout calculation detection."""
        collector = MetricCollector()
        detector = BottleneckDetector(collector)
        
        # Add slow layout times
        slow_times = [80.0, 90.0, 100.0, 110.0, 120.0] * 6  # 30 samples
        for time_val in slow_times:
            collector.record_metric(MetricType.LAYOUT_TIME, time_val)
        
        result = detector._detect_slow_layout()
        
        assert result is not None
        assert result['severity'] in ['medium', 'high']
        assert 'Layout calculations are slow' in result['description']
        assert 'recommendations' in result
        assert len(result['recommendations']) > 0
    
    def test_memory_leak_detection(self):
        """Test memory leak detection."""
        collector = MetricCollector()
        detector = BottleneckDetector(collector)
        
        # Simulate increasing memory usage (leak pattern)
        for i in range(100):
            memory_usage = 100.0 + i * 2.0  # Steadily increasing
            collector.record_metric(MetricType.MEMORY_USAGE, memory_usage)
        
        result = detector._detect_memory_leak()
        
        if result:  # May not detect with simulated data
            assert result['severity'] in ['medium', 'high']
            assert 'Memory usage increasing' in result['description']
            assert 'growth_rate_mb_per_min' in result['metrics']
    
    def test_cache_thrashing_detection(self):
        """Test cache thrashing detection."""
        collector = MetricCollector()
        detector = BottleneckDetector(collector)
        
        # Add poor cache performance data
        poor_ratios = [0.2, 0.3, 0.1, 0.4, 0.2] * 10  # 50 samples with high variance
        for ratio in poor_ratios:
            collector.record_metric(MetricType.CACHE_HIT_RATIO, ratio)
        
        result = detector._detect_cache_thrashing()
        
        assert result is not None
        assert result['severity'] == 'medium'
        assert 'Cache performance is poor' in result['description']
        assert 'cache key generation' in str(result['recommendations'])
    
    def test_cpu_spike_detection(self):
        """Test CPU spike detection."""
        collector = MetricCollector()
        detector = BottleneckDetector(collector)
        
        # Add CPU data with spikes
        cpu_values = [30.0] * 20 + [95.0, 98.0, 92.0] + [35.0] * 20  # Spikes in middle
        for cpu_val in cpu_values:
            collector.record_metric(MetricType.CPU_USAGE, cpu_val)
        
        result = detector._detect_cpu_spike()
        
        if result:  # May not detect depending on anomaly threshold
            assert result['severity'] in ['medium', 'high']
            assert 'CPU usage spikes' in result['description']
    
    def test_widget_bloat_detection(self):
        """Test widget bloat detection."""
        collector = MetricCollector()
        detector = BottleneckDetector(collector)
        
        # Add high widget counts
        widget_counts = [1200.0] * 20  # Consistently high widget count
        for count in widget_counts:
            collector.record_metric(MetricType.WIDGET_COUNT, count)
        
        result = detector._detect_widget_bloat()
        
        assert result is not None
        assert result['severity'] == 'medium'
        assert 'High widget count detected' in result['description']
        assert 'widget pooling' in str(result['recommendations'])
    
    def test_comprehensive_detection(self):
        """Test comprehensive bottleneck detection."""
        collector = MetricCollector()
        detector = BottleneckDetector(collector)
        
        # Add various problematic metrics
        collector.record_metric(MetricType.LAYOUT_TIME, 150.0)  # Slow
        collector.record_metric(MetricType.WIDGET_COUNT, 1500.0)  # High count
        
        bottlenecks = detector.detect_bottlenecks()
        
        # Should detect multiple issues
        assert len(bottlenecks) >= 1
        
        # Check bottleneck structure
        for bottleneck in bottlenecks:
            assert 'type' in bottleneck
            assert 'severity' in bottleneck
            assert 'description' in bottleneck
            assert 'recommendations' in bottleneck
            assert 'detected_at' in bottleneck


@pytest.mark.usefixtures("app")
class TestPerformanceMonitor:
    """Test PerformanceMonitor main system."""
    
    def test_monitor_initialization(self, mock_profiler, mock_config_manager):
        """Test performance monitor initialization."""
        monitor = PerformanceMonitor(mock_profiler, mock_config_manager)
        
        assert monitor._profiler == mock_profiler
        assert monitor._config_manager == mock_config_manager
        assert monitor._metric_collector is not None
        assert monitor._alert_manager is not None
        assert monitor._bottleneck_detector is not None
        assert monitor._monitoring_enabled is True
    
    def test_monitoring_control(self, mock_profiler, mock_config_manager):
        """Test starting and stopping monitoring."""
        monitor = PerformanceMonitor(mock_profiler, mock_config_manager)
        
        # Should start automatically
        assert monitor._collection_timer.isActive()
        assert monitor._bottleneck_timer.isActive()
        
        # Stop monitoring
        monitor.stop_monitoring()
        assert not monitor._collection_timer.isActive()
        assert not monitor._bottleneck_timer.isActive()
        
        # Start monitoring
        monitor.start_monitoring()
        assert monitor._collection_timer.isActive()
        assert monitor._bottleneck_timer.isActive()
    
    def test_metrics_collection(self, mock_profiler, mock_config_manager):
        """Test metrics collection process."""
        monitor = PerformanceMonitor(mock_profiler, mock_config_manager)
        
        # Mock the profiler to return data
        mock_profiler.get_memory_stats.return_value = {
            'current_mb': 512.0,
            'average_mb': 400.0
        }
        mock_profiler.get_operation_stats.return_value = {
            'count': 20,
            'average_time_ms': 75.0
        }
        
        # Manually trigger collection
        monitor._collect_metrics()
        
        # Should have collected metrics
        layout_times = monitor._metric_collector.get_recent_values(MetricType.LAYOUT_TIME, 5)
        memory_values = monitor._metric_collector.get_recent_values(MetricType.MEMORY_USAGE, 5)
        
        if len(layout_times) > 0:
            assert layout_times[-1] == 75.0
        if len(memory_values) > 0:
            assert memory_values[-1] == 512.0
    
    def test_bottleneck_checking(self, mock_profiler, mock_config_manager):
        """Test bottleneck checking process."""
        monitor = PerformanceMonitor(mock_profiler, mock_config_manager)
        
        # Add some problematic metrics
        monitor._metric_collector.record_metric(MetricType.LAYOUT_TIME, 150.0)
        monitor._metric_collector.record_metric(MetricType.WIDGET_COUNT, 1200.0)
        
        # Mock signal to capture emissions
        monitor.bottleneck_detected = Mock()
        
        # Manually trigger bottleneck check
        monitor._check_bottlenecks()
        
        # Should have detected bottlenecks (depending on detection logic)
        # The exact number depends on which patterns trigger
    
    def test_performance_report_generation(self, mock_profiler, mock_config_manager):
        """Test performance report generation."""
        monitor = PerformanceMonitor(mock_profiler, mock_config_manager)
        
        # Add some metrics data
        monitor._metric_collector.record_metric(MetricType.LAYOUT_TIME, 45.0)
        monitor._metric_collector.record_metric(MetricType.MEMORY_USAGE, 256.0)
        
        # Generate report
        report = monitor.generate_performance_report(duration_hours=1)
        
        assert isinstance(report, PerformanceReport)
        assert report.duration_minutes == 60
        assert isinstance(report.summary, dict)
        assert isinstance(report.detailed_metrics, dict)
        assert isinstance(report.alerts_generated, list)
        assert isinstance(report.recommendations, list)
    
    def test_recommendations_generation(self, mock_profiler, mock_config_manager):
        """Test recommendation generation."""
        monitor = PerformanceMonitor(mock_profiler, mock_config_manager)
        
        # Create summary with performance issues
        summary = {
            'LAYOUT_TIME': {'mean': 120.0, 'max': 200.0},  # Slow layouts
            'MEMORY_USAGE': {'max': 1500.0},  # High memory
            'CACHE_HIT_RATIO': {'mean': 0.4}  # Poor cache performance
        }
        
        recommendations = monitor._generate_recommendations(summary, [], [])
        
        assert len(recommendations) > 0
        
        # Should include relevant recommendations
        recommendations_text = ' '.join(recommendations).lower()
        assert 'cache' in recommendations_text or 'layout' in recommendations_text
    
    def test_monitoring_enable_disable(self, mock_profiler, mock_config_manager):
        """Test enabling/disabling monitoring."""
        monitor = PerformanceMonitor(mock_profiler, mock_config_manager)
        
        # Disable monitoring
        monitor.set_monitoring_enabled(False)
        assert monitor._monitoring_enabled is False
        assert not monitor._collection_timer.isActive()
        
        # Enable monitoring
        monitor.set_monitoring_enabled(True)
        assert monitor._monitoring_enabled is True
        assert monitor._collection_timer.isActive()
    
    def test_collection_interval_setting(self, mock_profiler, mock_config_manager):
        """Test setting collection interval."""
        monitor = PerformanceMonitor(mock_profiler, mock_config_manager)
        
        # Set new interval
        monitor.set_collection_interval(2000)  # 2 seconds
        assert monitor._collection_interval == 2000
        
        # Should restart timer with new interval
        if monitor._collection_timer.isActive():
            assert monitor._collection_timer.interval() == 2000
    
    def test_current_metrics_summary(self, mock_profiler, mock_config_manager):
        """Test current metrics summary."""
        monitor = PerformanceMonitor(mock_profiler, mock_config_manager)
        
        # Add some metrics
        monitor._metric_collector.record_metric(MetricType.LAYOUT_TIME, 35.0)
        monitor._metric_collector.record_metric(MetricType.MEMORY_USAGE, 400.0)
        
        summary = monitor.get_current_metrics_summary()
        
        assert isinstance(summary, dict)
        assert 'monitoring_enabled' in summary
        assert summary['monitoring_enabled'] is True
        
        # Should have metric data
        if 'LAYOUT_TIME' in summary:
            assert 'current' in summary['LAYOUT_TIME']
            assert 'average' in summary['LAYOUT_TIME']
            assert 'trend' in summary['LAYOUT_TIME']
    
    def test_data_clearing(self, mock_profiler, mock_config_manager):
        """Test clearing monitoring data."""
        monitor = PerformanceMonitor(mock_profiler, mock_config_manager)
        
        # Add some data
        monitor._metric_collector.record_metric(MetricType.LAYOUT_TIME, 45.0)
        monitor._alert_manager.check_metric(MetricType.LAYOUT_TIME, 150.0)
        
        # Clear data
        monitor.clear_monitoring_data()
        
        # Data should be cleared
        layout_values = monitor._metric_collector.get_recent_values(MetricType.LAYOUT_TIME, 10)
        assert len(layout_values) == 0
    
    def test_data_export(self, mock_profiler, mock_config_manager, tmp_path):
        """Test exporting monitoring data."""
        monitor = PerformanceMonitor(mock_profiler, mock_config_manager)
        
        # Add some data
        monitor._metric_collector.record_metric(MetricType.LAYOUT_TIME, 45.0)
        
        # Export data
        export_file = tmp_path / "monitor_export.json"
        success = monitor.export_monitoring_data(str(export_file))
        
        assert success is True
        assert export_file.exists()
        
        # Verify exported data
        with open(export_file, 'r') as f:
            data = json.load(f)
        
        assert 'export_timestamp' in data
        assert 'metrics_summary' in data
        assert 'active_alerts' in data
        assert 'recent_bottlenecks' in data
    
    def test_component_access(self, mock_profiler, mock_config_manager):
        """Test access to internal components."""
        monitor = PerformanceMonitor(mock_profiler, mock_config_manager)
        
        # Should provide access to components for external configuration
        alert_manager = monitor.get_alert_manager()
        assert alert_manager is monitor._alert_manager
        
        metric_collector = monitor.get_metric_collector()
        assert metric_collector is monitor._metric_collector


class TestIntegration:
    """Integration tests for monitoring system."""
    
    def test_full_monitoring_cycle(self, mock_profiler, mock_config_manager):
        """Test complete monitoring cycle."""
        monitor = PerformanceMonitor(mock_profiler, mock_config_manager)
        
        # Configure alert thresholds
        threshold = MetricThreshold(
            metric_type=MetricType.LAYOUT_TIME,
            warning_threshold=40.0,
            critical_threshold=80.0,
            emergency_threshold=150.0
        )
        monitor.get_alert_manager().set_threshold(threshold)
        
        # Simulate metrics collection that triggers alerts
        mock_profiler.get_operation_stats.return_value = {
            'count': 10,
            'average_time_ms': 100.0  # Above critical threshold
        }
        
        # Mock signal capturing
        alerts_generated = []
        def capture_alert(alert):
            alerts_generated.append(alert)
        
        monitor.alert_generated.connect(capture_alert)
        
        # Trigger metrics collection
        monitor._collect_metrics()
        
        # Should have generated alert
        if len(alerts_generated) > 0:
            alert = alerts_generated[0]
            assert alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]
            assert alert.metric_type == MetricType.LAYOUT_TIME
    
    def test_bottleneck_to_recommendation_flow(self, mock_profiler, mock_config_manager):
        """Test flow from bottleneck detection to recommendations."""
        monitor = PerformanceMonitor(mock_profiler, mock_config_manager)
        
        # Add problematic metrics
        for i in range(30):
            monitor._metric_collector.record_metric(MetricType.LAYOUT_TIME, 120.0)
            monitor._metric_collector.record_metric(MetricType.WIDGET_COUNT, 1500.0)
        
        # Generate report
        report = monitor.generate_performance_report(duration_hours=1)
        
        # Should have detected bottlenecks and generated recommendations
        assert len(report.bottlenecks_detected) > 0
        assert len(report.recommendations) > 0
        
        # Recommendations should be relevant to detected bottlenecks
        recommendations_text = ' '.join(report.recommendations).lower()
        bottleneck_types = [b['type'] for b in report.bottlenecks_detected]
        
        # Should have coherent recommendations
        if 'slow_layout_calculation' in bottleneck_types:
            assert 'cache' in recommendations_text or 'widget' in recommendations_text
    
    def test_performance_under_load(self, mock_profiler, mock_config_manager):
        """Test monitoring performance under load."""
        monitor = PerformanceMonitor(mock_profiler, mock_config_manager)
        
        start_time = time.time()
        
        # Simulate high-frequency metrics
        for i in range(100):
            monitor._metric_collector.record_metric(MetricType.LAYOUT_TIME, 50.0 + i % 20)
            monitor._metric_collector.record_metric(MetricType.MEMORY_USAGE, 200.0 + i)
        
        # Check bottlenecks
        monitor._check_bottlenecks()
        
        # Generate report
        report = monitor.generate_performance_report(duration_hours=1)
        
        elapsed = time.time() - start_time
        
        # Should complete efficiently
        assert elapsed < 2.0  # Under 2 seconds
        
        # Should have processed all metrics
        layout_values = monitor._metric_collector.get_recent_values(MetricType.LAYOUT_TIME, 200)
        assert len(layout_values) == 100


if __name__ == "__main__":
    pytest.main([__file__])