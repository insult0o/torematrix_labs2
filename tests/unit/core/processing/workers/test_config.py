"""Tests for worker configuration models."""

import pytest
from pydantic import ValidationError

from torematrix.processing.workers.config import (
    WorkerConfig, ResourceLimits, ResourceType
)


class TestWorkerConfig:
    """Test WorkerConfig model."""
    
    def test_default_values(self):
        """Test default configuration values."""
        config = WorkerConfig()
        
        assert config.async_workers == 4
        assert config.thread_workers == 2
        assert config.process_workers == 0
        assert config.max_queue_size == 1000
        assert config.priority_queue_size == 100
        assert config.default_timeout == 300.0
        assert config.worker_heartbeat_interval == 10.0
        assert config.max_concurrent_tasks == 50
        assert config.task_memory_limit_mb == 1024
    
    def test_custom_values(self):
        """Test configuration with custom values."""
        config = WorkerConfig(
            async_workers=8,
            thread_workers=4,
            process_workers=2,
            max_queue_size=2000,
            default_timeout=600.0
        )
        
        assert config.async_workers == 8
        assert config.thread_workers == 4
        assert config.process_workers == 2
        assert config.max_queue_size == 2000
        assert config.default_timeout == 600.0
    
    def test_validation_errors(self):
        """Test validation errors for invalid values."""
        # Async workers must be >= 1
        with pytest.raises(ValidationError):
            WorkerConfig(async_workers=0)
        
        # Thread workers can be 0 but not negative
        with pytest.raises(ValidationError):
            WorkerConfig(thread_workers=-1)
        
        # Queue size must be >= 10
        with pytest.raises(ValidationError):
            WorkerConfig(max_queue_size=5)
        
        # Timeout must be > 0
        with pytest.raises(ValidationError):
            WorkerConfig(default_timeout=0)
        
        # Memory limit must be >= 64
        with pytest.raises(ValidationError):
            WorkerConfig(task_memory_limit_mb=32)
    
    def test_serialization(self):
        """Test configuration serialization."""
        config = WorkerConfig(async_workers=6, thread_workers=3)
        
        # Test dict conversion
        config_dict = config.dict()
        assert isinstance(config_dict, dict)
        assert config_dict["async_workers"] == 6
        assert config_dict["thread_workers"] == 3
        
        # Test JSON serialization
        config_json = config.json()
        assert isinstance(config_json, str)
        assert "async_workers" in config_json


class TestResourceLimits:
    """Test ResourceLimits model."""
    
    def test_default_values(self):
        """Test default resource limit values."""
        limits = ResourceLimits()
        
        assert limits.max_cpu_percent == 80.0
        assert limits.warning_cpu_percent == 70.0
        assert limits.max_memory_percent == 75.0
        assert limits.warning_memory_percent == 65.0
        assert limits.max_disk_io_mbps is None
        assert limits.warning_disk_io_mbps is None
        assert limits.max_network_io_mbps is None
        assert limits.max_gpu_percent is None
        assert limits.max_gpu_memory_mb is None
    
    def test_custom_values(self):
        """Test resource limits with custom values."""
        limits = ResourceLimits(
            max_cpu_percent=90.0,
            warning_cpu_percent=80.0,
            max_memory_percent=85.0,
            max_disk_io_mbps=100.0,
            max_gpu_percent=95.0,
            max_gpu_memory_mb=8192
        )
        
        assert limits.max_cpu_percent == 90.0
        assert limits.warning_cpu_percent == 80.0
        assert limits.max_memory_percent == 85.0
        assert limits.max_disk_io_mbps == 100.0
        assert limits.max_gpu_percent == 95.0
        assert limits.max_gpu_memory_mb == 8192
    
    def test_validation_errors(self):
        """Test validation errors for invalid limits."""
        # CPU percent must be 10-100
        with pytest.raises(ValidationError):
            ResourceLimits(max_cpu_percent=5.0)
        
        with pytest.raises(ValidationError):
            ResourceLimits(max_cpu_percent=105.0)
        
        # Memory percent must be 10-100
        with pytest.raises(ValidationError):
            ResourceLimits(max_memory_percent=5.0)
        
        # Disk I/O must be >= 1.0 if specified
        with pytest.raises(ValidationError):
            ResourceLimits(max_disk_io_mbps=0.5)
        
        # GPU memory must be >= 100 if specified
        with pytest.raises(ValidationError):
            ResourceLimits(max_gpu_memory_mb=50)
    
    def test_get_limit(self):
        """Test get_limit method for different resource types."""
        limits = ResourceLimits(
            max_cpu_percent=80.0,
            max_memory_percent=75.0,
            max_disk_io_mbps=100.0,
            max_gpu_percent=90.0
        )
        
        assert limits.get_limit(ResourceType.CPU) == 80.0
        assert limits.get_limit(ResourceType.MEMORY) == 75.0
        assert limits.get_limit(ResourceType.DISK_IO) == 100.0
        assert limits.get_limit(ResourceType.GPU) == 90.0
        assert limits.get_limit(ResourceType.NETWORK_IO) == float('inf')  # Not set
    
    def test_get_warning_threshold(self):
        """Test get_warning_threshold method."""
        limits = ResourceLimits(
            warning_cpu_percent=70.0,
            warning_memory_percent=65.0,
            warning_disk_io_mbps=80.0
        )
        
        assert limits.get_warning_threshold(ResourceType.CPU) == 70.0
        assert limits.get_warning_threshold(ResourceType.MEMORY) == 65.0
        assert limits.get_warning_threshold(ResourceType.DISK_IO) == 80.0
        
        # For GPU (no warning threshold set), should default to 80% of limit
        limits_with_gpu = ResourceLimits(max_gpu_percent=90.0)
        assert limits_with_gpu.get_warning_threshold(ResourceType.GPU) == 72.0  # 80% of 90


class TestResourceType:
    """Test ResourceType enum."""
    
    def test_resource_types(self):
        """Test all resource type values."""
        assert ResourceType.CPU == "cpu"
        assert ResourceType.MEMORY == "memory"
        assert ResourceType.DISK_IO == "disk_io"
        assert ResourceType.NETWORK_IO == "network_io"
        assert ResourceType.GPU == "gpu"
    
    def test_enum_iteration(self):
        """Test iterating over resource types."""
        types = list(ResourceType)
        assert len(types) == 5
        assert ResourceType.CPU in types
        assert ResourceType.MEMORY in types
        assert ResourceType.DISK_IO in types
        assert ResourceType.NETWORK_IO in types
        assert ResourceType.GPU in types


class TestConfigIntegration:
    """Test integration between configuration models."""
    
    def test_worker_config_with_resource_limits(self):
        """Test using worker config with resource limits."""
        worker_config = WorkerConfig(
            async_workers=6,
            max_concurrent_tasks=100
        )
        
        resource_limits = ResourceLimits(
            max_cpu_percent=85.0,
            max_memory_percent=80.0
        )
        
        # Both should be valid and work together
        assert worker_config.async_workers == 6
        assert resource_limits.max_cpu_percent == 85.0
        
        # Resource limits should provide appropriate thresholds
        cpu_limit = resource_limits.get_limit(ResourceType.CPU)
        cpu_warning = resource_limits.get_warning_threshold(ResourceType.CPU)
        
        assert cpu_limit > cpu_warning
        assert cpu_warning > 0
    
    def test_realistic_production_config(self):
        """Test a realistic production configuration."""
        worker_config = WorkerConfig(
            async_workers=8,
            thread_workers=4,
            process_workers=2,
            max_queue_size=5000,
            priority_queue_size=500,
            default_timeout=900.0,  # 15 minutes
            max_concurrent_tasks=200,
            task_memory_limit_mb=2048
        )
        
        resource_limits = ResourceLimits(
            max_cpu_percent=85.0,
            warning_cpu_percent=75.0,
            max_memory_percent=80.0,
            warning_memory_percent=70.0,
            max_disk_io_mbps=500.0,
            warning_disk_io_mbps=400.0
        )
        
        # Validate the configuration makes sense
        assert worker_config.async_workers > 0
        assert worker_config.max_queue_size > worker_config.priority_queue_size
        assert worker_config.default_timeout > 0
        assert resource_limits.max_cpu_percent > resource_limits.warning_cpu_percent
        assert resource_limits.max_memory_percent > resource_limits.warning_memory_percent