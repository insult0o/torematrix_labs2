"""Tests for resource monitoring and management."""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from torematrix.processing.workers.resources import (
    ResourceMonitor, ResourceSnapshot
)
from torematrix.processing.workers.config import ResourceLimits, ResourceType


class TestResourceSnapshot:
    """Test ResourceSnapshot dataclass."""
    
    def test_create_snapshot(self):
        """Test creating a resource snapshot."""
        timestamp = datetime.utcnow()
        snapshot = ResourceSnapshot(
            timestamp=timestamp,
            cpu_percent=45.5,
            memory_percent=60.2,
            memory_mb=1024.0,
            disk_io_read_mb=10.5,
            disk_io_write_mb=5.2,
            network_io_sent_mb=2.1,
            network_io_recv_mb=8.7,
            active_tasks=5,
            queued_tasks=10
        )
        
        assert snapshot.timestamp == timestamp
        assert snapshot.cpu_percent == 45.5
        assert snapshot.memory_percent == 60.2
        assert snapshot.memory_mb == 1024.0
        assert snapshot.disk_io_read_mb == 10.5
        assert snapshot.disk_io_write_mb == 5.2
        assert snapshot.network_io_sent_mb == 2.1
        assert snapshot.network_io_recv_mb == 8.7
        assert snapshot.active_tasks == 5
        assert snapshot.queued_tasks == 10


class TestResourceMonitor:
    """Test ResourceMonitor class."""
    
    @pytest.fixture
    def resource_limits(self):
        """Create test resource limits."""
        return ResourceLimits(
            max_cpu_percent=80.0,
            warning_cpu_percent=70.0,
            max_memory_percent=75.0,
            warning_memory_percent=65.0,
            max_disk_io_mbps=100.0,
            warning_disk_io_mbps=80.0
        )
    
    @pytest.fixture
    def monitor(self, resource_limits):
        """Create test resource monitor."""
        return ResourceMonitor(resource_limits, check_interval=0.1)
    
    def test_initialization(self, monitor, resource_limits):
        """Test resource monitor initialization."""
        assert monitor.limits == resource_limits
        assert monitor.check_interval == 0.1
        assert monitor.current_usage == {}
        assert monitor.history == []
        assert monitor.allocated_resources == {}
        assert not monitor._monitoring
        assert monitor.max_history_size == 300
    
    @pytest.mark.asyncio
    async def test_start_stop(self, monitor):
        """Test starting and stopping the monitor."""
        assert not monitor._monitoring
        
        # Start monitoring
        await monitor.start()
        assert monitor._monitoring
        assert monitor._monitor_task is not None
        
        # Give it a moment to start
        await asyncio.sleep(0.05)
        
        # Stop monitoring
        await monitor.stop()
        assert not monitor._monitoring
        assert monitor._monitor_task.done()
    
    @pytest.mark.asyncio
    async def test_double_start(self, monitor):
        """Test that starting an already running monitor is safe."""
        await monitor.start()
        
        # Starting again should not raise an error
        await monitor.start()
        assert monitor._monitoring
        
        await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_check_availability_success(self, monitor):
        """Test resource availability check when resources are available."""
        # Set current usage to be within limits
        monitor.current_usage = {
            ResourceType.CPU: 30.0,
            ResourceType.MEMORY: 40.0
        }
        
        required = {
            ResourceType.CPU: 20.0,
            ResourceType.MEMORY: 15.0
        }
        
        available, reason = await monitor.check_availability(required)
        assert available is True
        assert reason is None
    
    @pytest.mark.asyncio
    async def test_check_availability_failure(self, monitor):
        """Test resource availability check when resources are insufficient."""
        # Set current usage to be high
        monitor.current_usage = {
            ResourceType.CPU: 70.0,
            ResourceType.MEMORY: 60.0
        }
        
        required = {
            ResourceType.CPU: 20.0,  # Would exceed 80% limit
            ResourceType.MEMORY: 10.0
        }
        
        available, reason = await monitor.check_availability(required)
        assert available is False
        assert reason is not None
        assert "CPU" in reason
        assert "90.0 > 80.0" in reason
    
    @pytest.mark.asyncio
    async def test_allocate_release_resources(self, monitor):
        """Test resource allocation and release."""
        task_id = "test-task-123"
        resources = {
            ResourceType.CPU: 10.0,
            ResourceType.MEMORY: 20.0
        }
        
        # Allocate resources
        success = await monitor.allocate(task_id, resources)
        assert success is True
        assert task_id in monitor.allocated_resources
        assert monitor.allocated_resources[task_id] == resources
        
        # Release resources
        await monitor.release(task_id)
        assert task_id not in monitor.allocated_resources
    
    @pytest.mark.asyncio
    async def test_allocate_insufficient_resources(self, monitor):
        """Test allocation failure when resources are insufficient."""
        # Set high current usage
        monitor.current_usage = {
            ResourceType.CPU: 75.0,
            ResourceType.MEMORY: 70.0
        }
        
        task_id = "test-task-456"
        resources = {
            ResourceType.CPU: 10.0,  # Would exceed limit
            ResourceType.MEMORY: 5.0
        }
        
        success = await monitor.allocate(task_id, resources)
        assert success is False
        assert task_id not in monitor.allocated_resources
    
    @pytest.mark.asyncio
    async def test_allocate_with_existing_allocations(self, monitor):
        """Test allocation considering existing allocations."""
        # Allocate some resources first
        task1_id = "task-1"
        task1_resources = {ResourceType.CPU: 30.0, ResourceType.MEMORY: 25.0}
        await monitor.allocate(task1_id, task1_resources)
        
        # Set current usage
        monitor.current_usage = {ResourceType.CPU: 20.0, ResourceType.MEMORY: 15.0}
        
        # Try to allocate more resources
        task2_id = "task-2"
        task2_resources = {ResourceType.CPU: 25.0, ResourceType.MEMORY: 20.0}  # Total would be 75% CPU, 60% memory
        
        success = await monitor.allocate(task2_id, task2_resources)
        assert success is True  # Should fit within limits
        
        # Try to allocate resources that would exceed limits
        task3_id = "task-3"
        task3_resources = {ResourceType.CPU: 30.0}  # Total would be 105% CPU
        
        success = await monitor.allocate(task3_id, task3_resources)
        assert success is False  # Should fail
    
    def test_get_current_usage(self, monitor):
        """Test getting current resource usage."""
        monitor.current_usage = {
            ResourceType.CPU: 45.0,
            ResourceType.MEMORY: 60.0
        }
        
        usage = monitor.get_current_usage()
        assert usage == monitor.current_usage
        assert usage is not monitor.current_usage  # Should be a copy
    
    def test_get_allocated_resources(self, monitor):
        """Test getting allocated resources."""
        monitor.allocated_resources = {
            "task-1": {ResourceType.CPU: 10.0},
            "task-2": {ResourceType.MEMORY: 20.0}
        }
        
        allocated = monitor.get_allocated_resources()
        assert allocated == monitor.allocated_resources
        assert allocated is not monitor.allocated_resources  # Should be a copy
    
    def test_get_resource_history(self, monitor):
        """Test getting resource history."""
        now = datetime.utcnow()
        
        # Add some history
        for i in range(10):
            snapshot = ResourceSnapshot(
                timestamp=now - timedelta(minutes=i),
                cpu_percent=float(i * 10),
                memory_percent=float(i * 5),
                memory_mb=1024.0,
                disk_io_read_mb=0.0,
                disk_io_write_mb=0.0,
                network_io_sent_mb=0.0,
                network_io_recv_mb=0.0,
                active_tasks=i,
                queued_tasks=0
            )
            monitor.history.append(snapshot)
        
        # Get history for last 5 minutes
        history = monitor.get_resource_history(minutes=5)
        assert len(history) == 6  # Including current minute
        
        # Check that all returned snapshots are within the time window
        cutoff = now - timedelta(minutes=5)
        for snapshot in history:
            assert snapshot.timestamp >= cutoff
    
    @patch('torematrix.processing.workers.resources.psutil.Process')
    @patch('torematrix.processing.workers.resources.psutil.net_io_counters')
    @pytest.mark.asyncio
    async def test_collect_snapshot(self, mock_net_io, mock_process_class, monitor):
        """Test collecting resource usage snapshot."""
        # Mock process
        mock_process = MagicMock()
        mock_process.cpu_percent.return_value = 45.5
        mock_process.memory_info.return_value = MagicMock(rss=1024 * 1024 * 512)  # 512 MB
        mock_process.memory_percent.return_value = 60.2
        mock_process.io_counters.return_value = MagicMock(
            read_bytes=1024 * 1024 * 100,  # 100 MB
            write_bytes=1024 * 1024 * 50   # 50 MB
        )
        monitor._process = mock_process
        
        # Mock network I/O
        mock_net_io.return_value = MagicMock(
            bytes_sent=1024 * 1024 * 10,   # 10 MB
            bytes_recv=1024 * 1024 * 25    # 25 MB
        )
        
        # Collect snapshot
        snapshot = await monitor._collect_snapshot()
        
        assert isinstance(snapshot, ResourceSnapshot)
        assert snapshot.cpu_percent == 45.5
        assert snapshot.memory_percent == 60.2
        assert snapshot.memory_mb == 512.0
        assert snapshot.active_tasks == 0  # No allocated resources
        assert snapshot.queued_tasks == 0
    
    @pytest.mark.asyncio
    async def test_monitor_loop_integration(self, monitor):
        """Test the monitoring loop with mocked data."""
        with patch.object(monitor, '_collect_snapshot') as mock_collect:
            # Mock snapshot data
            mock_snapshot = ResourceSnapshot(
                timestamp=datetime.utcnow(),
                cpu_percent=50.0,
                memory_percent=60.0,
                memory_mb=1024.0,
                disk_io_read_mb=5.0,
                disk_io_write_mb=3.0,
                network_io_sent_mb=1.0,
                network_io_recv_mb=2.0,
                active_tasks=3,
                queued_tasks=5
            )
            mock_collect.return_value = mock_snapshot
            
            # Start monitoring
            await monitor.start()
            
            # Let it run for a bit
            await asyncio.sleep(0.25)
            
            # Stop monitoring
            await monitor.stop()
            
            # Check that data was collected
            assert len(monitor.history) > 0
            assert ResourceType.CPU in monitor.current_usage
            assert ResourceType.MEMORY in monitor.current_usage
            assert monitor.current_usage[ResourceType.CPU] == 50.0
            assert monitor.current_usage[ResourceType.MEMORY] == 60.0
    
    @pytest.mark.asyncio
    async def test_check_resource_warnings(self, monitor):
        """Test resource warning detection."""
        # Create a snapshot that exceeds warning thresholds
        snapshot = ResourceSnapshot(
            timestamp=datetime.utcnow(),
            cpu_percent=75.0,  # Above warning threshold of 70%
            memory_percent=70.0,  # Above warning threshold of 65%
            memory_mb=1024.0,
            disk_io_read_mb=50.0,
            disk_io_write_mb=40.0,  # Total 90 MB/s, above warning of 80
            network_io_sent_mb=0.0,
            network_io_recv_mb=0.0,
            active_tasks=5,
            queued_tasks=10
        )
        
        with patch('torematrix.processing.workers.resources.logger') as mock_logger:
            await monitor._check_resource_warnings(snapshot)
            
            # Should have logged warnings for CPU, memory, and disk I/O
            warning_calls = [call for call in mock_logger.warning.call_args_list]
            assert len(warning_calls) >= 2  # At least CPU and memory warnings
    
    def test_string_representation(self, monitor):
        """Test string representation of resource monitor."""
        monitor.current_usage = {
            ResourceType.CPU: 45.5,
            ResourceType.MEMORY: 60.2
        }
        monitor.allocated_resources = {"task-1": {}, "task-2": {}}
        
        str_repr = str(monitor)
        assert "ResourceMonitor" in str_repr
        assert "cpu=45.5%" in str_repr
        assert "memory=60.2%" in str_repr
        assert "active_tasks=2" in str_repr


@pytest.mark.asyncio
class TestResourceMonitorIntegration:
    """Integration tests for resource monitor."""
    
    async def test_full_lifecycle(self):
        """Test complete resource monitor lifecycle."""
        limits = ResourceLimits(
            max_cpu_percent=80.0,
            max_memory_percent=75.0
        )
        monitor = ResourceMonitor(limits, check_interval=0.05)
        
        try:
            # Start monitoring
            await monitor.start()
            assert monitor._monitoring
            
            # Allocate some resources
            task1_resources = {ResourceType.CPU: 20.0, ResourceType.MEMORY: 30.0}
            success = await monitor.allocate("task-1", task1_resources)
            assert success
            
            # Let monitoring run for a bit
            await asyncio.sleep(0.1)
            
            # Check that history is being collected
            assert len(monitor.history) > 0
            
            # Release resources
            await monitor.release("task-1")
            assert "task-1" not in monitor.allocated_resources
            
        finally:
            # Always stop monitoring
            await monitor.stop()
            assert not monitor._monitoring