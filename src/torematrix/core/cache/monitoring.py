"""Cache performance monitoring and metrics collection."""

import os
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from prometheus_client import Counter, Histogram, Gauge


class CacheMonitor:
    """Monitors cache performance and collects metrics."""
    
    def __init__(self, metrics_dir: Optional[Path] = None):
        """Initialize cache monitor.
        
        Args:
            metrics_dir: Directory to store metrics files
        """
        self.metrics_dir = metrics_dir or Path("/var/log/torematrix/cache")
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Prometheus metrics
        self.cache_hits = Counter(
            'cache_hits_total',
            'Total number of cache hits',
            ['cache_level']
        )
        
        self.cache_misses = Counter(
            'cache_misses_total',
            'Total number of cache misses',
            ['cache_level']
        )
        
        self.cache_size = Gauge(
            'cache_size_bytes',
            'Current cache size in bytes',
            ['cache_level']
        )
        
        self.cache_latency = Histogram(
            'cache_operation_duration_seconds',
            'Cache operation latency in seconds',
            ['cache_level', 'operation'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
        )
        
        self.cache_evictions = Counter(
            'cache_evictions_total',
            'Total number of cache evictions',
            ['cache_level']
        )
        
        self.cache_errors = Counter(
            'cache_errors_total',
            'Total number of cache errors',
            ['cache_level', 'error_type']
        )
    
    def record_hit(self, cache_level: str):
        """Record a cache hit.
        
        Args:
            cache_level: Cache level (memory, disk, redis, object)
        """
        self.cache_hits.labels(cache_level=cache_level).inc()
    
    def record_miss(self, cache_level: str):
        """Record a cache miss.
        
        Args:
            cache_level: Cache level (memory, disk, redis, object)
        """
        self.cache_misses.labels(cache_level=cache_level).inc()
    
    def record_size(self, cache_level: str, size_bytes: int):
        """Record current cache size.
        
        Args:
            cache_level: Cache level (memory, disk, redis, object)
            size_bytes: Current size in bytes
        """
        self.cache_size.labels(cache_level=cache_level).set(size_bytes)
    
    def record_latency(self, cache_level: str, operation: str, 
                      duration: float):
        """Record operation latency.
        
        Args:
            cache_level: Cache level (memory, disk, redis, object)
            operation: Operation type (get, set, delete)
            duration: Duration in seconds
        """
        self.cache_latency.labels(
            cache_level=cache_level,
            operation=operation
        ).observe(duration)
    
    def record_eviction(self, cache_level: str):
        """Record a cache eviction.
        
        Args:
            cache_level: Cache level (memory, disk, redis, object)
        """
        self.cache_evictions.labels(cache_level=cache_level).inc()
    
    def record_error(self, cache_level: str, error_type: str):
        """Record a cache error.
        
        Args:
            cache_level: Cache level (memory, disk, redis, object)
            error_type: Type of error
        """
        self.cache_errors.labels(
            cache_level=cache_level,
            error_type=error_type
        ).inc()
    
    def get_hit_rate(self, cache_level: str) -> float:
        """Get hit rate for cache level.
        
        Args:
            cache_level: Cache level (memory, disk, redis, object)
            
        Returns:
            Hit rate as float between 0 and 1
        """
        hits = self.cache_hits.labels(cache_level=cache_level)._value.get()
        misses = self.cache_misses.labels(cache_level=cache_level)._value.get()
        total = hits + misses
        return hits / total if total > 0 else 0
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all cache metrics.
        
        Returns:
            Dictionary with metrics summary
        """
        summary = {
            'hit_rates': {},
            'sizes': {},
            'latencies': {},
            'evictions': {},
            'errors': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # Hit rates
        for level in ['memory', 'disk', 'redis', 'object']:
            summary['hit_rates'][level] = self.get_hit_rate(level)
        
        # Sizes
        for level in ['memory', 'disk', 'redis', 'object']:
            summary['sizes'][level] = self.cache_size.labels(
                cache_level=level
            )._value.get()
        
        # Average latencies
        for level in ['memory', 'disk', 'redis', 'object']:
            level_latencies = {}
            for op in ['get', 'set', 'delete']:
                count = self.cache_latency.labels(
                    cache_level=level,
                    operation=op
                )._sum.get()
                total = self.cache_latency.labels(
                    cache_level=level,
                    operation=op
                )._count.get()
                avg = count / total if total > 0 else 0
                level_latencies[op] = avg
            summary['latencies'][level] = level_latencies
        
        # Evictions
        for level in ['memory', 'disk', 'redis', 'object']:
            summary['evictions'][level] = self.cache_evictions.labels(
                cache_level=level
            )._value.get()
        
        # Errors
        for level in ['memory', 'disk', 'redis', 'object']:
            level_errors = {}
            for error_type in ['connection', 'timeout', 'serialization']:
                count = self.cache_errors.labels(
                    cache_level=level,
                    error_type=error_type
                )._value.get()
                if count > 0:
                    level_errors[error_type] = count
            if level_errors:
                summary['errors'][level] = level_errors
        
        return summary
    
    def save_metrics(self, metrics_file: Optional[str] = None):
        """Save current metrics to file.
        
        Args:
            metrics_file: Optional filename, defaults to timestamp
        """
        if metrics_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            metrics_file = f"cache_metrics_{timestamp}.json"
        
        metrics_path = self.metrics_dir / metrics_file
        metrics = self.get_metrics_summary()
        
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
    
    def load_metrics(self, metrics_file: str) -> Dict[str, Any]:
        """Load metrics from file.
        
        Args:
            metrics_file: Metrics filename
            
        Returns:
            Metrics dictionary
        """
        metrics_path = self.metrics_dir / metrics_file
        
        with open(metrics_path) as f:
            return json.load(f)
    
    def cleanup_old_metrics(self, max_age_days: int = 30):
        """Clean up old metrics files.
        
        Args:
            max_age_days: Maximum age in days to keep
        """
        cutoff = datetime.now() - timedelta(days=max_age_days)
        
        for metrics_file in self.metrics_dir.glob("cache_metrics_*.json"):
            # Parse timestamp from filename
            try:
                timestamp = datetime.strptime(
                    metrics_file.stem[13:],  # Skip "cache_metrics_"
                    '%Y%m%d_%H%M%S'
                )
                if timestamp < cutoff:
                    metrics_file.unlink()
            except ValueError:
                continue  # Skip files with invalid timestamps