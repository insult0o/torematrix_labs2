"""Unit tests for processor monitoring."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any

from torematrix.processing.processors.base import (
    BaseProcessor,
    ProcessorMetadata,
    ProcessorContext,
    ProcessorResult,
    StageStatus
)
from torematrix.processing.processors.registry import ProcessorRegistry
from torematrix.processing.processors.monitoring import (
    ProcessorMetrics,
    ProcessorMonitor,
    ProcessorProfiler,
    monitor_processor
)


class TestProcessor(BaseProcessor):
    """Test processor for monitoring tests."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.process_count = 0
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="test_processor",
            version="1.0.0",
            description="Test processor"
        )
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        self.process_count += 1
        return ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            extracted_data={"count": self.process_count}
        )


@pytest.fixture
def registry():
    """Create processor registry."""
    return ProcessorRegistry()


@pytest.fixture
def test_context():
    """Create test context."""
    return ProcessorContext(
        document_id="doc123",
        file_path="/tmp/test.txt",
        mime_type="text/plain"
    )


class TestProcessorMetrics:
    """Test cases for ProcessorMetrics."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = ProcessorMetrics(name="test")
        
        assert metrics.name == "test"
        assert metrics.total_processed == 0
        assert metrics.total_failed == 0
        assert metrics.total_duration == 0.0
        assert len(metrics.recent_durations) == 0
        assert len(metrics.recent_failures) == 0
    
    def test_record_success(self):
        """Test recording successful processing."""
        metrics = ProcessorMetrics(name="test")
        
        metrics.record_success(1.5)
        metrics.record_success(2.0)
        
        assert metrics.total_processed == 2
        assert metrics.total_duration == 3.5
        assert len(metrics.recent_durations) == 2
        assert metrics.average_duration == 1.75
        assert metrics.recent_average_duration == 1.75
    
    def test_record_failure(self):
        """Test recording failed processing."""
        metrics = ProcessorMetrics(name="test")
        
        metrics.record_failure()
        metrics.record_failure()
        
        assert metrics.total_failed == 2
        assert len(metrics.recent_failures) == 2
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        metrics = ProcessorMetrics(name="test")
        
        # No processing yet
        assert metrics.success_rate == 0.0
        
        # Some successes and failures
        metrics.record_success(1.0)
        metrics.record_success(1.0)
        metrics.record_failure()
        
        assert metrics.success_rate == 2.0 / 3.0  # 2 successes out of 3 total
    
    def test_failure_rate_calculation(self):
        """Test failure rate calculation."""
        metrics = ProcessorMetrics(name="test")
        
        # No failures
        assert metrics.get_failure_rate(5) == 0.0
        
        # Add recent failures
        metrics.record_failure()
        metrics.record_failure()
        
        rate = metrics.get_failure_rate(5)
        assert rate == 2.0 / 5.0  # 2 failures in 5 minutes
    
    def test_recent_durations_sliding_window(self):
        """Test recent durations sliding window behavior."""
        metrics = ProcessorMetrics(name="test")
        
        # Add more than 100 durations (the maxlen)
        for i in range(150):
            metrics.record_success(float(i))
        
        # Should only keep the last 100
        assert len(metrics.recent_durations) == 100
        assert list(metrics.recent_durations) == list(range(50, 150))


class TestProcessorMonitor:
    """Test cases for ProcessorMonitor."""
    
    @pytest.fixture
    async def monitor(self, registry):
        """Create processor monitor."""
        return ProcessorMonitor(registry)
    
    @pytest.mark.asyncio
    async def test_monitor_start_stop(self, monitor):
        """Test monitor start and stop."""
        assert not monitor._running
        assert monitor._monitoring_task is None
        
        await monitor.start()
        
        assert monitor._running
        assert monitor._monitoring_task is not None
        
        await monitor.stop()
        
        assert not monitor._running
    
    def test_processor_loaded_hook(self, monitor):
        """Test processor loaded hook."""
        assert len(monitor.metrics) == 0
        
        monitor._on_processor_loaded("test_processor", TestProcessor)
        
        assert "test_processor" in monitor.metrics
        assert monitor.metrics["test_processor"].name == "test_processor"
    
    def test_record_processing_success(self, monitor):
        """Test recording successful processing."""
        monitor.record_processing("test_processor", True, 1.5, 512.0, 25.0)
        
        metrics = monitor.metrics["test_processor"]
        assert metrics.total_processed == 1
        assert metrics.total_failed == 0
        assert metrics.total_duration == 1.5
        assert metrics.peak_memory_mb == 512.0
        assert metrics.peak_cpu_percent == 25.0
    
    def test_record_processing_failure(self, monitor):
        """Test recording failed processing."""
        monitor.record_processing("test_processor", False, 0.5)
        
        metrics = monitor.metrics["test_processor"]
        assert metrics.total_processed == 0
        assert metrics.total_failed == 1
        assert len(metrics.recent_failures) == 1
    
    def test_update_peak_resources(self, monitor):
        """Test updating peak resource usage."""
        # Record initial values
        monitor.record_processing("test_processor", True, 1.0, 100.0, 20.0)
        
        # Record higher values
        monitor.record_processing("test_processor", True, 1.0, 200.0, 30.0)
        
        # Record lower values (should not update peaks)
        monitor.record_processing("test_processor", True, 1.0, 50.0, 10.0)
        
        metrics = monitor.metrics["test_processor"]
        assert metrics.peak_memory_mb == 200.0
        assert metrics.peak_cpu_percent == 30.0
    
    @pytest.mark.asyncio
    async def test_alert_handlers(self, monitor):
        """Test alert handlers."""
        alert_calls = []
        
        async def alert_handler(alert):
            alert_calls.append(alert)
        
        monitor.add_alert_handler(alert_handler)
        
        # Trigger alert by exceeding threshold
        alert = {
            "type": "test_alert",
            "processor": "test_processor",
            "value": 100,
            "threshold": 50
        }
        
        await monitor._trigger_alert(alert)
        
        assert len(alert_calls) == 1
        assert alert_calls[0] == alert
    
    def test_set_alert_threshold(self, monitor):
        """Test setting alert thresholds."""
        monitor.set_alert_threshold("failure_rate", 0.2)
        monitor.set_alert_threshold("custom_metric", 100.0)
        
        assert monitor._alert_thresholds["failure_rate"] == 0.2
        assert monitor._alert_thresholds["custom_metric"] == 100.0
    
    def test_get_processor_metrics(self, monitor):
        """Test getting specific processor metrics."""
        monitor.record_processing("test_processor", True, 1.0)
        
        metrics = monitor.get_processor_metrics("test_processor")
        assert metrics is not None
        assert metrics.name == "test_processor"
        
        # Non-existent processor
        metrics = monitor.get_processor_metrics("nonexistent")
        assert metrics is None
    
    def test_get_all_metrics(self, monitor):
        """Test getting all processor metrics."""
        monitor.record_processing("proc1", True, 1.0)
        monitor.record_processing("proc2", False, 0.5)
        
        all_metrics = monitor.get_all_metrics()
        
        assert len(all_metrics) == 2
        assert "proc1" in all_metrics
        assert "proc2" in all_metrics
    
    def test_get_summary(self, monitor):
        """Test getting summary statistics."""
        monitor.record_processing("proc1", True, 1.0)
        monitor.record_processing("proc1", True, 2.0)
        monitor.record_processing("proc2", False, 0.5)
        
        summary = monitor.get_summary()
        
        assert summary["processor_count"] == 2
        assert summary["total_processed"] == 2
        assert summary["total_failed"] == 1
        assert summary["overall_success_rate"] == 2.0 / 3.0
        assert "processors" in summary
        assert "proc1" in summary["processors"]
        assert "proc2" in summary["processors"]
    
    def test_get_health_status(self, monitor):
        """Test getting health status."""
        # Healthy processor
        for _ in range(10):
            monitor.record_processing("healthy_proc", True, 1.0)
        
        # Unhealthy processor (low success rate)
        for _ in range(10):
            monitor.record_processing("unhealthy_proc", False, 1.0)
        
        # Slow processor
        for _ in range(5):
            monitor.record_processing("slow_proc", True, 35.0)  # > 30 seconds
        
        health = monitor.get_health_status()
        
        assert health["healthy"] is False  # Due to unhealthy processor
        assert health["processor_count"] == 3
        assert len(health["unhealthy_processors"]) == 1
        assert health["unhealthy_processors"][0]["name"] == "unhealthy_proc"
        assert len(health["warnings"]) == 1
        assert health["warnings"][0]["name"] == "slow_proc"


class TestProcessorProfiler:
    """Test cases for ProcessorProfiler."""
    
    @pytest.fixture
    def profiler(self):
        """Create processor profiler."""
        return ProcessorProfiler()
    
    @pytest.mark.asyncio
    async def test_profiling_lifecycle(self, profiler, test_context):
        """Test complete profiling lifecycle."""
        processor_name = "test_processor"
        
        # Start profiling
        profile_id = await profiler.start_profiling(processor_name, test_context)
        assert profile_id is not None
        assert profile_id in profiler._active_profiles
        
        # Simulate processing result
        result = ProcessorResult(
            processor_name=processor_name,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            extracted_data={"test": "data"}
        )
        
        # End profiling
        await profiler.end_profiling(profile_id, result, memory_usage=256.0, cpu_usage=15.0)
        
        # Check profile was recorded
        assert profile_id not in profiler._active_profiles
        assert processor_name in profiler._profiles
        assert len(profiler._profiles[processor_name]) == 1
        
        profile_data = profiler._profiles[processor_name][0]
        assert profile_data["profile_id"] == profile_id
        assert profile_data["status"] == StageStatus.COMPLETED
        assert profile_data["memory_mb"] == 256.0
        assert profile_data["cpu_percent"] == 15.0
    
    @pytest.mark.asyncio
    async def test_end_profiling_invalid_id(self, profiler):
        """Test ending profiling with invalid ID."""
        result = ProcessorResult(
            processor_name="test",
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow()
        )
        
        # Should not raise exception
        await profiler.end_profiling("invalid_id", result)
    
    def test_get_performance_insights_no_data(self, profiler):
        """Test getting insights with no profiling data."""
        insights = profiler.get_performance_insights("nonexistent")
        
        assert "message" in insights
        assert "No profiling data available" in insights["message"]
    
    @pytest.mark.asyncio
    async def test_get_performance_insights_with_data(self, profiler, test_context):
        """Test getting performance insights with data."""
        processor_name = "test_processor"
        
        # Create multiple profiles
        for i in range(5):
            profile_id = await profiler.start_profiling(processor_name, test_context)
            
            result = ProcessorResult(
                processor_name=processor_name,
                status=StageStatus.COMPLETED if i < 4 else StageStatus.FAILED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow()
            )
            
            await profiler.end_profiling(
                profile_id, 
                result, 
                memory_usage=100.0 + i * 10,
                cpu_usage=10.0 + i * 5
            )
        
        insights = profiler.get_performance_insights(processor_name)
        
        assert insights["total_executions"] == 5
        assert "average_duration" in insights
        assert "min_duration" in insights
        assert "max_duration" in insights
        assert "average_memory_mb" in insights
        assert insights["success_rate"] == 0.8  # 4 out of 5 succeeded
        assert "recent_trends" in insights
    
    def test_profile_history_limit(self, profiler):
        """Test profile history is limited to 100 entries."""
        processor_name = "test_processor"
        
        # Add more than 100 profiles
        for i in range(150):
            profile_data = {
                "profile_id": f"profile_{i}",
                "start_time": datetime.utcnow(),
                "end_time": datetime.utcnow(),
                "duration": 1.0,
                "status": StageStatus.COMPLETED,
                "errors": [],
                "memory_mb": None,
                "cpu_percent": None,
                "result_size": 100
            }
            profiler._profiles[processor_name].append(profile_data)
        
        # Should only keep the last 100
        assert len(profiler._profiles[processor_name]) == 100
        # Should be the most recent ones
        assert profiler._profiles[processor_name][0]["profile_id"] == "profile_50"
        assert profiler._profiles[processor_name][-1]["profile_id"] == "profile_149"


class TestMonitorDecorator:
    """Test cases for monitor_processor decorator."""
    
    @pytest.mark.asyncio
    async def test_monitor_decorator(self, test_context):
        """Test monitor_processor decorator."""
        registry = ProcessorRegistry()
        monitor = ProcessorMonitor(registry)
        
        @monitor_processor(monitor)
        class MonitoredProcessor(BaseProcessor):
            @classmethod
            def get_metadata(cls) -> ProcessorMetadata:
                return ProcessorMetadata(
                    name="monitored_processor",
                    version="1.0.0",
                    description="Monitored processor"
                )
            
            async def process(self, context: ProcessorContext) -> ProcessorResult:
                return ProcessorResult(
                    processor_name=self.get_metadata().name,
                    status=StageStatus.COMPLETED,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    extracted_data={"monitored": True}
                )
        
        processor = MonitoredProcessor()
        await processor.initialize()
        
        # Process should be monitored
        result = await processor.process(test_context)
        
        assert result.status == StageStatus.COMPLETED
        
        # Check that metrics were recorded
        metrics = monitor.get_processor_metrics("monitored_processor")
        assert metrics is not None
        assert metrics.total_processed == 1
        assert metrics.total_failed == 0
    
    @pytest.mark.asyncio
    async def test_monitor_decorator_with_failure(self, test_context):
        """Test monitor_processor decorator with processor failure."""
        registry = ProcessorRegistry()
        monitor = ProcessorMonitor(registry)
        
        @monitor_processor(monitor)
        class FailingProcessor(BaseProcessor):
            @classmethod
            def get_metadata(cls) -> ProcessorMetadata:
                return ProcessorMetadata(
                    name="failing_processor",
                    version="1.0.0",
                    description="Failing processor"
                )
            
            async def process(self, context: ProcessorContext) -> ProcessorResult:
                raise Exception("Test failure")
        
        processor = FailingProcessor()
        await processor.initialize()
        
        # Process should fail but still be monitored
        with pytest.raises(Exception, match="Test failure"):
            await processor.process(test_context)
        
        # Check that failure was recorded
        metrics = monitor.get_processor_metrics("failing_processor")
        assert metrics is not None
        assert metrics.total_processed == 0
        assert metrics.total_failed == 1