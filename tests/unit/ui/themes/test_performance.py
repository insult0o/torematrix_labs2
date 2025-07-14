"""Tests for theme performance optimization system."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from src.torematrix.ui.themes.performance import (
    PerformanceProfiler, MemoryProfiler, PerformanceOptimizer,
    ThemePerformanceManager, PerformanceMetric, PerformanceSnapshot,
    PerformanceTarget, OptimizationSuggestion
)


class TestPerformanceProfiler:
    """Test PerformanceProfiler class."""
    
    @pytest.fixture
    def profiler(self):
        """Create performance profiler instance."""
        return PerformanceProfiler(max_snapshots=100)
    
    def test_profiler_initialization(self, profiler):
        """Test profiler initialization."""
        assert profiler.max_snapshots == 100
        assert len(profiler.snapshots) == 0
        assert len(profiler.active_sessions) == 0
        assert len(profiler.targets) > 0
        
        # Check default targets exist
        assert PerformanceMetric.THEME_LOAD_TIME in profiler.targets
        assert PerformanceMetric.STYLESHEET_GENERATION_TIME in profiler.targets
    
    def test_session_management(self, profiler):
        """Test performance session start/end."""
        session_id = "test_session"
        theme_name = "test_theme"
        
        # Start session
        profiler.start_session(session_id)
        assert session_id in profiler.active_sessions
        
        # End session
        time.sleep(0.01)  # Small delay
        duration = profiler.end_session(
            session_id, 
            theme_name, 
            PerformanceMetric.THEME_LOAD_TIME
        )
        
        assert duration > 0
        assert session_id not in profiler.active_sessions
        assert len(profiler.snapshots) == 1
        
        snapshot = profiler.snapshots[0]
        assert snapshot.theme_name == theme_name
        assert snapshot.metric_type == PerformanceMetric.THEME_LOAD_TIME
        assert snapshot.value == duration
    
    def test_direct_metric_recording(self, profiler):
        """Test recording metrics directly."""
        profiler.record_metric(
            "test_theme",
            PerformanceMetric.MEMORY_USAGE,
            25.5
        )
        
        assert len(profiler.snapshots) == 1
        snapshot = profiler.snapshots[0]
        assert snapshot.value == 25.5
        assert snapshot.metric_type == PerformanceMetric.MEMORY_USAGE
    
    def test_performance_targets_checking(self, profiler):
        """Test performance target checking."""
        # Record metric that exceeds warning threshold
        with patch('logging.Logger.warning') as mock_warning:
            profiler.record_metric(
                "slow_theme",
                PerformanceMetric.THEME_LOAD_TIME,
                150.0  # Exceeds 100ms warning threshold
            )
            mock_warning.assert_called()
    
    def test_statistics_calculation(self, profiler):
        """Test performance statistics calculation."""
        # Record several metrics
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in values:
            profiler.record_metric(
                "test_theme",
                PerformanceMetric.THEME_LOAD_TIME,
                value
            )
        
        stats = profiler.get_statistics(PerformanceMetric.THEME_LOAD_TIME)
        
        assert stats['count'] == 5
        assert stats['min'] == 10.0
        assert stats['max'] == 50.0
        assert stats['avg'] == 30.0
        assert stats['median'] == 30.0
    
    def test_statistics_filtering(self, profiler):
        """Test statistics with filtering."""
        # Record metrics for different themes
        profiler.record_metric("theme1", PerformanceMetric.THEME_LOAD_TIME, 10.0)
        profiler.record_metric("theme2", PerformanceMetric.THEME_LOAD_TIME, 20.0)
        profiler.record_metric("theme1", PerformanceMetric.STYLESHEET_GENERATION_TIME, 30.0)
        
        # Filter by theme
        stats = profiler.get_statistics(
            PerformanceMetric.THEME_LOAD_TIME,
            theme_name="theme1"
        )
        assert stats['count'] == 1
        assert stats['avg'] == 10.0
        
        # Filter by metric type
        stats = profiler.get_statistics(PerformanceMetric.THEME_LOAD_TIME)
        assert stats['count'] == 2
    
    def test_recent_snapshots(self, profiler):
        """Test getting recent snapshots."""
        # Record multiple metrics
        for i in range(15):
            profiler.record_metric("theme", PerformanceMetric.THEME_LOAD_TIME, i)
        
        recent = profiler.get_recent_snapshots(5)
        assert len(recent) == 5
        
        # Should be most recent
        assert recent[-1].value == 14.0


class TestMemoryProfiler:
    """Test MemoryProfiler class."""
    
    @pytest.fixture
    def memory_profiler(self):
        """Create memory profiler instance."""
        return MemoryProfiler()
    
    @patch('psutil.Process')
    def test_memory_measurement(self, mock_process, memory_profiler):
        """Test memory usage measurement."""
        # Mock process memory info
        mock_memory_info = Mock()
        mock_memory_info.rss = 1024 * 1024 * 50  # 50MB
        mock_process.return_value.memory_info.return_value = mock_memory_info
        
        memory_usage = memory_profiler._get_memory_usage()
        assert memory_usage == 50.0  # 50MB
    
    @patch('psutil.Process')
    def test_theme_memory_tracking(self, mock_process, memory_profiler):
        """Test theme-specific memory tracking."""
        # Mock increasing memory usage
        mock_memory_info_start = Mock()
        mock_memory_info_start.rss = 1024 * 1024 * 50  # 50MB
        
        mock_memory_info_end = Mock()
        mock_memory_info_end.rss = 1024 * 1024 * 55   # 55MB
        
        mock_process.return_value.memory_info.side_effect = [
            mock_memory_info_start,
            mock_memory_info_end
        ]
        
        # Start measurement
        memory_profiler.start_measurement("test_theme")
        
        # End measurement
        usage = memory_profiler.end_measurement("test_theme")
        
        assert usage == 5.0  # 5MB increase
        assert memory_profiler.get_theme_memory_usage("test_theme") == 5.0
    
    def test_total_memory_calculation(self, memory_profiler):
        """Test total theme memory calculation."""
        # Manually set theme memory usage
        memory_profiler.theme_memory_usage = {
            "theme1": 10.0,
            "theme2": 15.0,
            "theme3_start": 5.0  # Should be ignored
        }
        
        total = memory_profiler.get_total_theme_memory()
        assert total == 25.0  # 10 + 15


class TestPerformanceOptimizer:
    """Test PerformanceOptimizer class."""
    
    @pytest.fixture
    def optimizer(self):
        """Create performance optimizer instance."""
        profiler = PerformanceProfiler()
        memory_profiler = MemoryProfiler()
        return PerformanceOptimizer(profiler, memory_profiler)
    
    def test_performance_analysis(self, optimizer):
        """Test performance analysis and suggestions."""
        # Add some performance data that should trigger suggestions
        optimizer.profiler.record_metric(
            "slow_theme",
            PerformanceMetric.STYLESHEET_GENERATION_TIME,
            250.0  # Slow generation
        )
        
        optimizer.memory_profiler.theme_memory_usage = {
            "memory_hog": 60.0  # High memory usage
        }
        
        suggestions = optimizer.analyze_performance()
        
        assert len(suggestions) > 0
        
        # Should have stylesheet generation suggestion
        generation_suggestions = [
            s for s in suggestions 
            if s.category == "Stylesheet Generation"
        ]
        assert len(generation_suggestions) > 0
        
        # Should have memory suggestion
        memory_suggestions = [
            s for s in suggestions 
            if s.category == "Memory Usage"
        ]
        assert len(memory_suggestions) > 0
    
    def test_performance_report_generation(self, optimizer):
        """Test performance report generation."""
        # Add some test data
        optimizer.profiler.record_metric(
            "test_theme",
            PerformanceMetric.THEME_LOAD_TIME,
            45.0
        )
        
        report = optimizer.get_performance_report()
        
        assert 'timestamp' in report
        assert 'summary' in report
        assert 'metrics' in report
        assert 'suggestions' in report
        assert 'targets' in report
        
        # Should have metrics data
        assert len(report['metrics']) > 0
    
    @patch('pathlib.Path.open')
    def test_report_export(self, mock_open, optimizer):
        """Test exporting performance report."""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        from pathlib import Path
        output_path = Path("/tmp/report.json")
        
        optimizer.export_report(output_path)
        
        mock_open.assert_called_once()
        mock_file.write.assert_called()


class TestThemePerformanceManager:
    """Test ThemePerformanceManager class."""
    
    @pytest.fixture
    def performance_manager(self):
        """Create performance manager instance."""
        return ThemePerformanceManager()
    
    def test_manager_initialization(self, performance_manager):
        """Test manager initialization."""
        assert performance_manager.profiler is not None
        assert performance_manager.memory_profiler is not None
        assert performance_manager.optimizer is not None
        assert performance_manager.monitoring_enabled is True
    
    def test_monitoring_control(self, performance_manager):
        """Test starting and stopping monitoring."""
        assert not performance_manager.monitor_timer.isActive()
        
        performance_manager.start_monitoring()
        assert performance_manager.monitor_timer.isActive()
        assert performance_manager.monitoring_enabled is True
        
        performance_manager.stop_monitoring()
        assert not performance_manager.monitor_timer.isActive()
        assert performance_manager.monitoring_enabled is False
    
    def test_operation_measurement_context(self, performance_manager):
        """Test operation measurement context manager."""
        with performance_manager.measure_operation(
            "test_op", 
            "test_theme", 
            PerformanceMetric.THEME_LOAD_TIME
        ):
            time.sleep(0.01)  # Simulate work
        
        # Should have recorded the metric
        stats = performance_manager.profiler.get_statistics(
            PerformanceMetric.THEME_LOAD_TIME
        )
        assert stats['count'] == 1
        assert stats['avg'] > 0
    
    def test_memory_measurement_context(self, performance_manager):
        """Test memory measurement context manager."""
        with patch.object(performance_manager.memory_profiler, 'start_measurement') as mock_start, \
             patch.object(performance_manager.memory_profiler, 'end_measurement', return_value=5.0) as mock_end:
            
            with performance_manager.measure_operation(
                "memory_op",
                "test_theme",
                PerformanceMetric.MEMORY_USAGE
            ):
                pass
            
            mock_start.assert_called_once_with("test_theme")
            mock_end.assert_called_once_with("test_theme")
    
    def test_performance_summary(self, performance_manager):
        """Test getting performance summary."""
        summary = performance_manager.get_performance_summary()
        
        assert 'current_memory_mb' in summary
        assert 'total_theme_memory_mb' in summary
        assert 'recent_operations' in summary
        assert 'monitoring_active' in summary
        assert 'suggestions_count' in summary
        
        assert isinstance(summary['current_memory_mb'], (int, float))
        assert isinstance(summary['monitoring_active'], bool)
    
    def test_data_clearing(self, performance_manager):
        """Test clearing performance data."""
        # Add some test data
        performance_manager.profiler.record_metric(
            "test_theme",
            PerformanceMetric.THEME_LOAD_TIME,
            50.0
        )
        
        performance_manager.memory_profiler.theme_memory_usage["test"] = 10.0
        
        # Clear data
        performance_manager.clear_performance_data()
        
        # Should be empty
        assert len(performance_manager.profiler.snapshots) == 0
        assert len(performance_manager.memory_profiler.theme_memory_usage) == 0


class TestPerformanceDataStructures:
    """Test performance-related data structures."""
    
    def test_performance_snapshot(self):
        """Test PerformanceSnapshot data structure."""
        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            theme_name="test_theme",
            metric_type=PerformanceMetric.THEME_LOAD_TIME,
            value=50.0
        )
        
        assert not snapshot.is_expired()  # No expiry set
        
        # Test with expiry
        snapshot.expiry_time = time.time() - 10  # Expired 10 seconds ago
        assert snapshot.is_expired()
        
        # Test touch method
        old_access_time = snapshot.last_accessed
        old_access_count = snapshot.access_count
        
        time.sleep(0.001)
        snapshot.touch()
        
        assert snapshot.last_accessed > old_access_time
        assert snapshot.access_count == old_access_count + 1
    
    def test_performance_target(self):
        """Test PerformanceTarget data structure."""
        target = PerformanceTarget(
            metric=PerformanceMetric.THEME_LOAD_TIME,
            target_value=50.0,
            warning_threshold=100.0,
            critical_threshold=200.0,
            unit="ms"
        )
        
        assert target.metric == PerformanceMetric.THEME_LOAD_TIME
        assert target.target_value == 50.0
        assert target.unit == "ms"
    
    def test_optimization_suggestion(self):
        """Test OptimizationSuggestion data structure."""
        suggestion = OptimizationSuggestion(
            category="Performance",
            priority="high",
            description="Slow operation detected",
            potential_improvement="50% faster",
            implementation_complexity="medium",
            code_example="# Example code"
        )
        
        assert suggestion.category == "Performance"
        assert suggestion.priority == "high"
        assert suggestion.code_example == "# Example code"


@pytest.mark.integration
class TestPerformanceSystemIntegration:
    """Integration tests for the performance system."""
    
    def test_complete_performance_workflow(self):
        """Test complete performance monitoring workflow."""
        manager = ThemePerformanceManager()
        
        # Start monitoring
        manager.start_monitoring()
        
        # Simulate theme operations
        theme_name = "integration_test_theme"
        
        # Measure stylesheet generation
        with manager.measure_operation(
            "stylesheet_gen",
            theme_name,
            PerformanceMetric.STYLESHEET_GENERATION_TIME
        ):
            time.sleep(0.02)  # Simulate 20ms generation
        
        # Measure theme switching
        with manager.measure_operation(
            "theme_switch",
            theme_name,
            PerformanceMetric.THEME_SWITCH_TIME
        ):
            time.sleep(0.05)  # Simulate 50ms switch
        
        # Get performance summary
        summary = manager.get_performance_summary()
        assert summary['recent_operations'] >= 2
        
        # Get detailed statistics
        gen_stats = manager.profiler.get_statistics(
            PerformanceMetric.STYLESHEET_GENERATION_TIME
        )
        assert gen_stats['count'] == 1
        assert gen_stats['avg'] >= 20.0  # Should be around 20ms
        
        switch_stats = manager.profiler.get_statistics(
            PerformanceMetric.THEME_SWITCH_TIME
        )
        assert switch_stats['count'] == 1
        assert switch_stats['avg'] >= 50.0  # Should be around 50ms
        
        # Analyze performance
        suggestions = manager.optimizer.analyze_performance(theme_name)
        # Should not have critical suggestions for good performance
        critical_suggestions = [s for s in suggestions if s.priority == "critical"]
        assert len(critical_suggestions) == 0
        
        # Stop monitoring
        manager.stop_monitoring()
        assert not manager.monitoring_enabled