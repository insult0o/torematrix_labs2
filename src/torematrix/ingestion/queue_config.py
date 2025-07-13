"""
Queue configuration for document processing pipeline.

This module provides configuration classes for Redis/RQ queue management,
including retry policies and performance optimization settings.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import timedelta
import random


class QueueConfig(BaseModel):
    """Configuration for document processing queues."""
    
    # Redis connection
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_max_connections: int = Field(default=50)
    redis_socket_timeout: int = Field(default=30)
    redis_connection_pool_size: int = Field(default=20)
    
    # Queue settings
    default_queue_name: str = Field(default="document_processing")
    priority_queue_name: str = Field(default="document_processing_priority")
    failed_queue_name: str = Field(default="document_processing_failed")
    
    # Job settings
    job_timeout: int = Field(default=3600)  # 1 hour
    result_ttl: int = Field(default=86400)  # 24 hours
    failure_ttl: int = Field(default=604800)  # 7 days
    
    # Retry settings
    max_retries: int = Field(default=3)
    retry_delays: List[int] = Field(default=[60, 300, 900])  # 1min, 5min, 15min
    
    # Batch processing
    batch_size: int = Field(default=10)
    batch_timeout: int = Field(default=300)  # 5 minutes
    max_concurrent_batches: int = Field(default=5)
    
    # Worker settings
    worker_poll_interval: float = Field(default=1.0)
    worker_max_jobs: Optional[int] = Field(default=None)
    worker_ttl: int = Field(default=420)  # 7 minutes
    
    # Performance settings
    enable_job_compression: bool = Field(default=True)
    compression_level: int = Field(default=6)
    enable_job_deduplication: bool = Field(default=True)
    deduplication_window: int = Field(default=300)  # 5 minutes
    
    # Monitoring
    enable_metrics: bool = Field(default=True)
    metrics_update_interval: int = Field(default=30)  # seconds
    max_failed_jobs_to_keep: int = Field(default=1000)
    
    class Config:
        """Pydantic configuration."""
        env_prefix = "TOREMATRIX_QUEUE_"
        schema_extra = {
            "example": {
                "redis_url": "redis://localhost:6379/0",
                "batch_size": 10,
                "max_retries": 3,
                "job_timeout": 3600,
                "enable_metrics": True
            }
        }


class RetryPolicy(BaseModel):
    """Retry policy for failed jobs with configurable backoff strategies."""
    
    max_attempts: int = Field(default=3, ge=1, le=10)
    backoff_type: str = Field(default="exponential", regex="^(linear|exponential|fixed)$")
    initial_delay: int = Field(default=60, ge=1)  # seconds
    max_delay: int = Field(default=3600, ge=60)  # 1 hour max
    jitter: bool = Field(default=True)
    jitter_max_percent: float = Field(default=0.5, ge=0.0, le=1.0)
    
    def get_delay(self, attempt: int) -> int:
        """
        Calculate delay for retry attempt.
        
        Args:
            attempt: The attempt number (1-based)
            
        Returns:
            Delay in seconds for this attempt
        """
        if attempt <= 0:
            return self.initial_delay
            
        if self.backoff_type == "fixed":
            delay = self.initial_delay
        elif self.backoff_type == "linear":
            delay = self.initial_delay * attempt
        else:  # exponential
            delay = self.initial_delay * (2 ** (attempt - 1))
        
        # Apply maximum delay limit
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_amount = delay * self.jitter_max_percent
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay = max(1, int(delay + jitter))
        
        return delay
    
    def should_retry(self, attempt: int, error_type: Optional[str] = None) -> bool:
        """
        Determine if a job should be retried.
        
        Args:
            attempt: Current attempt number (1-based)
            error_type: Optional error type for selective retry logic
            
        Returns:
            True if the job should be retried
        """
        if attempt >= self.max_attempts:
            return False
            
        # Don't retry certain types of errors
        if error_type in ["validation_error", "format_not_supported", "permission_denied"]:
            return False
            
        return True
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "max_attempts": 3,
                "backoff_type": "exponential",
                "initial_delay": 60,
                "max_delay": 3600,
                "jitter": True
            }
        }


class WorkerConfig(BaseModel):
    """Configuration for queue workers."""
    
    name: str = Field(..., description="Worker name/identifier")
    queues: List[str] = Field(default_factory=list, description="Queue names to process")
    connection_class: str = Field(default="redis.Redis", description="Redis connection class")
    max_jobs: Optional[int] = Field(default=None, description="Maximum jobs per worker")
    default_result_ttl: int = Field(default=86400, description="Default result TTL in seconds")
    
    # Worker behavior
    poll_interval: float = Field(default=1.0, description="Queue polling interval in seconds")
    fork_job_execution: bool = Field(default=True, description="Fork processes for job execution")
    disable_default_exception_handler: bool = Field(default=False)
    
    # Resource limits
    memory_limit_mb: Optional[int] = Field(default=None, description="Memory limit in MB")
    cpu_limit_percent: Optional[float] = Field(default=None, description="CPU usage limit as percentage")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "name": "document-processor-1",
                "queues": ["document_processing", "document_processing_priority"],
                "max_jobs": 10,
                "poll_interval": 1.0
            }
        }


class QueueHealthConfig(BaseModel):
    """Configuration for queue health monitoring."""
    
    # Health check thresholds
    max_queue_size: int = Field(default=1000, description="Maximum queue size before alerting")
    max_failed_job_rate: float = Field(default=0.1, description="Maximum failed job rate (0.0-1.0)")
    max_avg_processing_time: int = Field(default=300, description="Maximum average processing time in seconds")
    
    # Worker health
    min_active_workers: int = Field(default=1, description="Minimum number of active workers")
    worker_timeout: int = Field(default=300, description="Worker timeout in seconds")
    
    # Redis health
    max_redis_latency_ms: float = Field(default=100.0, description="Maximum Redis latency in milliseconds")
    redis_memory_warning_threshold: float = Field(default=0.8, description="Redis memory usage warning threshold")
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "max_queue_size": 1000,
                "max_failed_job_rate": 0.1,
                "min_active_workers": 2,
                "max_redis_latency_ms": 100.0
            }
        }


class PriorityConfig(BaseModel):
    """Configuration for job priority handling."""
    
    enable_priority_processing: bool = Field(default=True)
    priority_queue_weight: int = Field(default=3, description="Weight for priority queue processing")
    default_queue_weight: int = Field(default=1, description="Weight for default queue processing")
    
    # Priority assignment rules
    large_file_threshold_mb: int = Field(default=100, description="Files larger than this get lower priority")
    rush_job_keywords: List[str] = Field(
        default_factory=lambda: ["urgent", "asap", "priority"],
        description="Keywords that trigger high priority"
    )
    
    class Config:
        """Pydantic configuration."""
        schema_extra = {
            "example": {
                "enable_priority_processing": True,
                "priority_queue_weight": 3,
                "large_file_threshold_mb": 100,
                "rush_job_keywords": ["urgent", "asap"]
            }
        }