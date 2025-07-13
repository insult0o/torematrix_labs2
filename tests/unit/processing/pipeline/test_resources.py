"""
Unit tests for resource monitoring.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import psutil

from torematrix.processing.pipeline.resources import (
    ResourceMonitor,
    ResourceUsage
)
from torematrix.processing.pipeline.config import ResourceRequirements


class TestResourceUsage:
    """Test cases for ResourceUsage dataclass."""
    
    def test_resource_usage_creation(self):
        """Test creating resource usage snapshot."""
        usage = ResourceUsage(
            timestamp=datetime.utcnow(),
            cpu_percent=45.5,
            memory_mb=2048,
            memory_percent=50.0,
            gpu_memory_mb=1024,
            gpu_percent=25.0
        )
        
        assert usage.cpu_percent == 45.5
        assert usage.memory_mb == 2048
        assert usage.gpu_memory_mb == 1024
    
    def test_resource_usage_without_gpu(self):
        """Test resource usage without GPU data."""
        usage = ResourceUsage(
            timestamp=datetime.utcnow(),
            cpu_percent=30.0,
            memory_mb=1024,
            memory_percent=25.0
        )
        
        assert usage.gpu_memory_mb is None
        assert usage.gpu_percent is None


class TestResourceMonitor:
    """Test cases for ResourceMonitor."""
    
    @pytest.fixture
    def monitor(self):
        """Create resource monitor instance."""
        return ResourceMonitor(
            max_cpu_percent=80.0,
            max_memory_percent=75.0,
            update_interval=0.1,  # Fast updates for testing
            history_size=10
        )
    
    @pytest.mark.asyncio
    async def test_monitor_lifecycle(self, monitor):
        """Test starting and stopping monitor."""
        assert not monitor._running
        
        await monitor.start()
        assert monitor._running
        assert monitor._monitor_task is not None
        
        await monitor.stop()
        assert not monitor._running
    
    @pytest.mark.asyncio
    async def test_resource_collection(self, monitor):
        """Test resource usage collection."""
        # Mock psutil functions
        with patch('psutil.cpu_percent', return_value=50.0):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value = Mock(
                    used=2147483648,  # 2GB
                    percent=50.0,
                    available=2147483648,
                    total=4294967296  # 4GB
                )
                
                await monitor.start()
                await asyncio.sleep(0.3)  # Let it collect a few samples
                
                assert monitor.current_usage is not None
                assert monitor.current_usage.cpu_percent == 50.0
                assert monitor.current_usage.memory_mb == 2048
                assert monitor.current_usage.memory_percent == 50.0
                assert len(monitor.history) > 0
                
                await monitor.stop()
    
    @pytest.mark.asyncio
    async def test_check_availability_no_data(self, monitor):
        """Test resource availability check with no data."""
        requirements = ResourceRequirements(cpu_cores=2.0, memory_mb=1024)
        
        # Should return True when no data available
        available = await monitor.check_availability(requirements)
        assert available is True
    
    @pytest.mark.asyncio
    async def test_check_availability_sufficient(self, monitor):
        """Test resource availability with sufficient resources."""
        # Set current usage
        monitor.current_usage = ResourceUsage(
            timestamp=datetime.utcnow(),
            cpu_percent=30.0,
            memory_mb=1024,
            memory_percent=25.0
        )
        
        with patch('psutil.cpu_count', return_value=8):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value = Mock(
                    available=3221225472,  # 3GB available
                    total=4294967296  # 4GB total
                )
                
                requirements = ResourceRequirements(cpu_cores=2.0, memory_mb=1024)
                available = await monitor.check_availability(requirements)
                assert available is True
    
    @pytest.mark.asyncio
    async def test_check_availability_insufficient_cpu(self, monitor):
        """Test resource availability with insufficient CPU."""
        # Set high CPU usage
        monitor.current_usage = ResourceUsage(
            timestamp=datetime.utcnow(),
            cpu_percent=75.0,
            memory_mb=1024,
            memory_percent=25.0
        )
        
        with patch('psutil.cpu_count', return_value=4):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value = Mock(
                    available=3221225472,  # 3GB available
                    total=4294967296  # 4GB total
                )
                
                # Requesting 2 cores = 50% of 4 cores, but only 25% available
                requirements = ResourceRequirements(cpu_cores=2.0, memory_mb=512)
                available = await monitor.check_availability(requirements)
                assert available is False
    
    @pytest.mark.asyncio
    async def test_check_availability_insufficient_memory(self, monitor):
        """Test resource availability with insufficient memory."""
        monitor.current_usage = ResourceUsage(
            timestamp=datetime.utcnow(),
            cpu_percent=30.0,
            memory_mb=3072,
            memory_percent=75.0
        )
        
        with patch('psutil.cpu_count', return_value=8):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value = Mock(
                    available=536870912,  # 512MB available
                    total=4294967296  # 4GB total
                )
                
                requirements = ResourceRequirements(cpu_cores=1.0, memory_mb=1024)
                available = await monitor.check_availability(requirements)
                assert available is False
    
    @pytest.mark.asyncio
    async def test_check_availability_would_exceed_limits(self, monitor):
        """Test resource availability considering limits."""
        monitor.current_usage = ResourceUsage(
            timestamp=datetime.utcnow(),
            cpu_percent=70.0,  # Already at 70%
            memory_mb=2048,
            memory_percent=50.0
        )
        
        with patch('psutil.cpu_count', return_value=8):
            with patch('psutil.virtual_memory') as mock_memory:
                mock_memory.return_value = Mock(
                    available=2147483648,  # 2GB available
                    total=4294967296  # 4GB total
                )
                
                # This would push CPU to 82.5% (over 80% limit)
                requirements = ResourceRequirements(cpu_cores=1.0, memory_mb=512)
                available = await monitor.check_availability(requirements)
                assert available is False
    
    @pytest.mark.asyncio
    async def test_allocate_release(self, monitor):
        """Test resource allocation and release."""
        requirements = ResourceRequirements(cpu_cores=2.0, memory_mb=1024)
        
        await monitor.allocate("stage1", requirements)
        assert "stage1" in monitor.allocated_resources
        assert monitor.allocated_resources["stage1"] == requirements
        
        await monitor.release("stage1")
        assert "stage1" not in monitor.allocated_resources
    
    def test_get_allocated_totals(self, monitor):
        """Test getting total allocated resources."""
        monitor.allocated_resources = {
            "stage1": ResourceRequirements(cpu_cores=2.0, memory_mb=1024),
            "stage2": ResourceRequirements(cpu_cores=1.5, memory_mb=512),
            "stage3": ResourceRequirements(cpu_cores=0.5, memory_mb=256, gpu_required=True, gpu_memory_mb=1024)
        }
        
        totals = monitor.get_allocated_totals()
        
        assert totals.cpu_cores == 4.0
        assert totals.memory_mb == 1792
        assert totals.gpu_required is True
        assert totals.gpu_memory_mb == 1024
    
    def test_get_usage_history(self, monitor):
        """Test getting usage history."""
        now = datetime.utcnow()
        
        # Add usage data
        for i in range(10):
            usage = ResourceUsage(
                timestamp=now - timedelta(minutes=9-i),
                cpu_percent=30.0 + i,
                memory_mb=1024 + i*100,
                memory_percent=25.0 + i*2
            )
            monitor.history.append(usage)
        
        # Get last 5 minutes
        recent = monitor.get_usage_history(minutes=5)
        
        assert len(recent) <= 5
        assert all(u.timestamp > now - timedelta(minutes=5) for u in recent)
    
    def test_get_average_usage(self, monitor):
        """Test calculating average usage."""
        now = datetime.utcnow()
        
        # Add usage data
        for i in range(5):
            usage = ResourceUsage(
                timestamp=now - timedelta(minutes=4-i),
                cpu_percent=40.0 + i*2,  # 40, 42, 44, 46, 48
                memory_mb=1000 + i*100,  # 1000, 1100, 1200, 1300, 1400
                memory_percent=25.0 + i  # 25, 26, 27, 28, 29
            )
            monitor.history.append(usage)
        
        avg = monitor.get_average_usage(minutes=5)
        
        assert avg is not None
        assert avg.cpu_percent == 44.0  # Average of 40-48
        assert avg.memory_mb == 1200  # Average of 1000-1400
        assert avg.memory_percent == 27.0  # Average of 25-29
    
    def test_get_average_usage_with_gpu(self, monitor):
        """Test average usage calculation with GPU data."""
        now = datetime.utcnow()
        
        # Add mixed usage data (some with GPU, some without)
        for i in range(4):
            usage = ResourceUsage(
                timestamp=now - timedelta(minutes=3-i),
                cpu_percent=50.0,
                memory_mb=2048,
                memory_percent=50.0,
                gpu_memory_mb=512 if i % 2 == 0 else None,
                gpu_percent=25.0 if i % 2 == 0 else None
            )
            monitor.history.append(usage)
        
        avg = monitor.get_average_usage(minutes=5)
        
        assert avg is not None
        assert avg.gpu_memory_mb == 512  # Average of available GPU data
        assert avg.gpu_percent == 25.0
    
    def test_get_current_usage(self, monitor):
        """Test getting current usage as dictionary."""
        monitor.current_usage = ResourceUsage(
            timestamp=datetime.utcnow(),
            cpu_percent=45.5,
            memory_mb=2048,
            memory_percent=50.0,
            gpu_memory_mb=1024,
            gpu_percent=30.0
        )
        
        usage_dict = monitor.get_current_usage()
        
        assert usage_dict["cpu"] == 45.5
        assert usage_dict["memory"] == 50.0
        assert usage_dict["memory_mb"] == 2048
        assert usage_dict["gpu"] == 30.0
        assert usage_dict["gpu_memory_mb"] == 1024
    
    def test_get_current_usage_no_data(self, monitor):
        """Test getting current usage with no data."""
        usage_dict = monitor.get_current_usage()
        assert usage_dict == {}
    
    def test_get_stats(self, monitor):
        """Test getting monitor statistics."""
        monitor.current_usage = ResourceUsage(
            timestamp=datetime.utcnow(),
            cpu_percent=50.0,
            memory_mb=2048,
            memory_percent=50.0
        )
        
        monitor.allocated_resources = {
            "stage1": ResourceRequirements(cpu_cores=2.0, memory_mb=1024),
            "stage2": ResourceRequirements(cpu_cores=1.0, memory_mb=512)
        }
        
        for i in range(5):
            monitor.history.append(monitor.current_usage)
        
        stats = monitor.get_stats()
        
        assert stats["current_usage"]["cpu"] == 50.0
        assert stats["allocated_stages"] == 2
        assert stats["allocated_resources"]["cpu_cores"] == 3.0
        assert stats["allocated_resources"]["memory_mb"] == 1536
        assert stats["limits"]["max_cpu_percent"] == 80.0
        assert stats["limits"]["max_memory_percent"] == 75.0
        assert stats["history_size"] == 5
    
    @pytest.mark.asyncio
    async def test_high_resource_warning(self, monitor, caplog):
        """Test warning logs for high resource usage."""
        # Set high usage
        monitor.current_usage = ResourceUsage(
            timestamp=datetime.utcnow(),
            cpu_percent=85.0,  # Over 80% limit
            memory_mb=3277,  # ~80% of 4GB
            memory_percent=80.0  # Over 75% limit
        )
        
        # Mock the collection to return high usage
        async def mock_collect():
            return monitor.current_usage
        
        monitor._collect_usage = mock_collect
        
        await monitor.start()
        await asyncio.sleep(0.2)  # Let it run one cycle
        await monitor.stop()
        
        # Check for warning logs
        assert any("High CPU usage" in record.message for record in caplog.records)
        assert any("High memory usage" in record.message for record in caplog.records)