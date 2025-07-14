"""
Tests for Performance Monitoring System.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from torematrix.ui.components.monitoring import (
    RenderMetrics,
    ComponentMetrics,
    PerformanceSnapshot,
    PerformanceMonitor,
    PerformanceProfiler,
    get_performance_monitor,
    get_performance_profiler,
    track_performance,
    profile_operation
)


@pytest.fixture
def qapp():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestRenderMetrics:
    """Test RenderMetrics functionality."""
    
    def test_render_metrics_creation(self):
        """Test creating render metrics."""
        metrics = RenderMetrics(
            widget_id=123,
            widget_type="TestWidget",
            start_time=1.0,
            end_time=1.1,
            duration=0.1,
            patches_applied=5
        )
        
        assert metrics.widget_id == 123
        assert metrics.widget_type == "TestWidget"
        assert metrics.duration == 0.1
        assert metrics.duration_ms == 100.0
        assert metrics.patches_applied == 5


class TestComponentMetrics:
    """Test ComponentMetrics functionality."""
    
    def test_component_metrics_update(self):
        """Test updating component metrics."""
        comp_metrics = ComponentMetrics("TestWidget")
        
        # Add first render
        render1 = RenderMetrics(
            widget_id=1,
            widget_type="TestWidget",
            start_time=1.0,
            end_time=1.01,
            duration=0.01,
            memory_before=1000,
            memory_after=1100
        )
        
        comp_metrics.update(render1)
        
        assert comp_metrics.render_count == 1
        assert comp_metrics.total_time == 0.01
        assert comp_metrics.average_time == 0.01
        assert comp_metrics.min_time == 0.01
        assert comp_metrics.max_time == 0.01
        assert comp_metrics.memory_leaked == 100
        
        # Add second render
        render2 = RenderMetrics(
            widget_id=2,
            widget_type="TestWidget",
            start_time=2.0,
            end_time=2.02,
            duration=0.02,
            memory_before=1100,
            memory_after=1100
        )
        
        comp_metrics.update(render2)
        
        assert comp_metrics.render_count == 2
        assert comp_metrics.total_time == 0.03
        assert comp_metrics.average_time == 0.015
        assert comp_metrics.min_time == 0.01
        assert comp_metrics.max_time == 0.02
        assert comp_metrics.memory_leaked == 100  # No additional leak
    
    def test_error_counting(self):
        """Test error counting in metrics."""
        comp_metrics = ComponentMetrics("TestWidget")
        
        render_with_error = RenderMetrics(
            widget_id=1,
            widget_type="TestWidget",
            start_time=1.0,
            end_time=1.01,
            duration=0.01,
            error="Test error"
        )
        
        comp_metrics.update(render_with_error)
        
        assert comp_metrics.error_count == 1


class TestPerformanceSnapshot:
    """Test PerformanceSnapshot."""
    
    def test_snapshot_to_dict(self):
        """Test converting snapshot to dictionary."""
        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            fps=59.5,
            cpu_percent=45.2,
            memory_mb=256.7,
            active_components=10,
            render_queue_size=3,
            frame_drops=2,
            average_render_time=0.0156
        )
        
        data = snapshot.to_dict()
        
        assert data["fps"] == 59.5
        assert data["cpu_percent"] == 45.2
        assert data["memory_mb"] == 256.7
        assert data["average_render_time_ms"] == 15.6


class TestPerformanceMonitor:
    """Test PerformanceMonitor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.monitor = PerformanceMonitor()
        self.monitor._monitoring_timer.stop()  # Stop auto-updates
    
    def test_track_render_success(self):
        """Test tracking successful render."""
        widget = Mock()
        widget.__class__.__name__ = "TestWidget"
        
        with self.monitor.track_render(widget) as metrics:
            metrics.patches_applied = 3
            time.sleep(0.01)  # Simulate render time
        
        # Check metrics recorded
        assert len(self.monitor._render_metrics) == 1
        recorded = self.monitor._render_metrics[0]
        assert recorded.widget_type == "TestWidget"
        assert recorded.duration > 0
        assert recorded.patches_applied == 3
        assert recorded.error is None
    
    def test_track_render_error(self):
        """Test tracking render with error."""
        widget = Mock()
        widget.__class__.__name__ = "TestWidget"
        
        try:
            with self.monitor.track_render(widget) as metrics:
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Error should be recorded
        assert len(self.monitor._render_metrics) == 1
        recorded = self.monitor._render_metrics[0]
        assert recorded.error == "Test error"
    
    def test_frame_tracking(self):
        """Test frame time tracking."""
        # Simulate normal frame
        self.monitor.track_frame()
        time.sleep(0.016)  # 16ms
        self.monitor.track_frame()
        
        assert len(self.monitor._frame_times) == 1
        assert self.monitor._frame_drops == 0
        
        # Simulate dropped frame
        time.sleep(0.040)  # 40ms
        self.monitor.track_frame()
        
        assert self.monitor._frame_drops == 1
    
    def test_threshold_warnings(self):
        """Test performance threshold warnings."""
        widget = Mock()
        widget.__class__.__name__ = "SlowWidget"
        
        # Track warning signal
        warnings = []
        self.monitor.performance_warning.connect(warnings.append)
        
        # Track critical signal
        criticals = []
        self.monitor.performance_critical.connect(criticals.append)
        
        # Simulate slow render (20ms)
        with self.monitor.track_render(widget) as metrics:
            metrics.duration = 0.020
        
        self.monitor._record_metrics(metrics)
        
        # Should trigger warning
        assert len(warnings) == 1
        assert "SlowWidget" in warnings[0]
        assert "20.0ms" in warnings[0]
        
        # Simulate very slow render (40ms)
        metrics.duration = 0.040
        self.monitor._record_metrics(metrics)
        
        # Should trigger critical
        assert len(criticals) == 1
        assert "SlowWidget" in criticals[0]
        assert "40.0ms" in criticals[0]
    
    def test_component_report(self):
        """Test getting component performance report."""
        # Add some test data
        for i in range(5):
            widget = Mock()
            widget.__class__.__name__ = "Widget1"
            
            with self.monitor.track_render(widget) as metrics:
                metrics.duration = 0.01 + i * 0.002
                metrics.patches_applied = i
        
        report = self.monitor.get_component_report()
        
        assert "Widget1" in report
        widget1_stats = report["Widget1"]
        assert widget1_stats["render_count"] == 5
        assert widget1_stats["average_time_ms"] > 10
        assert widget1_stats["min_time_ms"] >= 10
        assert widget1_stats["max_time_ms"] >= widget1_stats["min_time_ms"]
    
    def test_performance_history(self):
        """Test getting performance history."""
        # Create some snapshots
        for i in range(3):
            snapshot = PerformanceSnapshot(
                timestamp=time.time() - (2 - i),
                fps=60 - i,
                cpu_percent=50 + i * 5,
                memory_mb=200 + i * 50,
                active_components=5 + i,
                render_queue_size=i,
                frame_drops=i,
                average_render_time=0.01 + i * 0.001
            )
            self.monitor._performance_snapshots.append(snapshot)
        
        # Get last 2 seconds
        history = self.monitor.get_performance_history(2)
        
        assert len(history) >= 2
        assert all("fps" in h for h in history)
        assert all("cpu_percent" in h for h in history)
    
    def test_bottleneck_detection(self):
        """Test finding performance bottlenecks."""
        # Create components with different performance
        components = [
            ("SlowWidget", 0.025),
            ("FastWidget", 0.005),
            ("MediumWidget", 0.015),
            ("VerySlowWidget", 0.035)
        ]
        
        for comp_type, duration in components:
            widget = Mock()
            widget.__class__.__name__ = comp_type
            
            with self.monitor.track_render(widget) as metrics:
                metrics.duration = duration
        
        bottlenecks = self.monitor.get_bottlenecks(top_n=3)
        
        assert len(bottlenecks) == 3
        assert bottlenecks[0][0] == "VerySlowWidget"
        assert bottlenecks[1][0] == "SlowWidget"
        assert bottlenecks[2][0] == "MediumWidget"
    
    def test_reset_metrics(self):
        """Test resetting all metrics."""
        # Add some data
        widget = Mock()
        widget.__class__.__name__ = "TestWidget"
        
        with self.monitor.track_render(widget):
            pass
        
        self.monitor.track_frame()
        
        # Reset
        self.monitor.reset_metrics()
        
        assert len(self.monitor._render_metrics) == 0
        assert len(self.monitor._component_metrics) == 0
        assert len(self.monitor._performance_snapshots) == 0
        assert len(self.monitor._frame_times) == 0
        assert self.monitor._frame_drops == 0
    
    def test_set_threshold(self):
        """Test setting custom thresholds."""
        self.monitor.set_threshold("render_time_ms", 10.0, 20.0)
        
        assert self.monitor.warning_thresholds["render_time_ms"] == 10.0
        assert self.monitor.critical_thresholds["render_time_ms"] == 20.0


class TestPerformanceProfiler:
    """Test PerformanceProfiler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.profiler = PerformanceProfiler()
    
    def test_profile_operation(self):
        """Test profiling operations."""
        # Profile some operations
        with self.profiler.profile("operation1"):
            time.sleep(0.01)
        
        with self.profiler.profile("operation1"):
            time.sleep(0.02)
        
        with self.profiler.profile("operation2"):
            time.sleep(0.005)
        
        report = self.profiler.get_profile_report()
        
        assert "operation1" in report
        assert "operation2" in report
        
        op1_stats = report["operation1"]
        assert op1_stats["call_count"] == 2
        assert op1_stats["total_time"] > 0.03
        assert op1_stats["average_time"] > 0.015
        assert op1_stats["min_time"] < op1_stats["max_time"]
        
        op2_stats = report["operation2"]
        assert op2_stats["call_count"] == 1
        assert op2_stats["total_time"] > 0.005
    
    def test_reset_profiler(self):
        """Test resetting profiler data."""
        with self.profiler.profile("test"):
            pass
        
        self.profiler.reset()
        
        report = self.profiler.get_profile_report()
        assert len(report) == 0


class TestGlobalInstances:
    """Test global instance functions."""
    
    def test_get_performance_monitor(self):
        """Test getting global monitor."""
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()
        
        assert monitor1 is monitor2
        assert isinstance(monitor1, PerformanceMonitor)
    
    def test_get_performance_profiler(self):
        """Test getting global profiler."""
        profiler1 = get_performance_profiler()
        profiler2 = get_performance_profiler()
        
        assert profiler1 is profiler2
        assert isinstance(profiler1, PerformanceProfiler)
    
    def test_track_performance_context(self):
        """Test track_performance context manager."""
        widget = Mock()
        widget.__class__.__name__ = "TestWidget"
        
        with track_performance(widget) as metrics:
            metrics.patches_applied = 5
        
        # Should be tracked in global monitor
        monitor = get_performance_monitor()
        assert len(monitor._render_metrics) > 0
    
    def test_profile_operation_context(self):
        """Test profile_operation context manager."""
        with profile_operation("test_op"):
            time.sleep(0.001)
        
        # Should be profiled in global profiler
        profiler = get_performance_profiler()
        report = profiler.get_profile_report()
        assert "test_op" in report