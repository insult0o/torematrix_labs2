"""
Performance Profiling System for Agent 3.
This module provides comprehensive performance monitoring and profiling
for the document viewer overlay system.
"""
from __future__ import annotations

import time
import threading
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
from datetime import datetime
from contextlib import contextmanager


class ProfilingLevel(Enum):
    """Profiling detail levels."""
    DISABLED = "disabled"
    BASIC = "basic"           # Basic timing and counters
    DETAILED = "detailed"     # Detailed function-level profiling


@dataclass
class ProfilingConfiguration:
    """Configuration for performance profiling."""
    level: ProfilingLevel = ProfilingLevel.BASIC
    sample_rate: float = 1.0  # Fraction of operations to profile (0.0-1.0)
    max_history_size: int = 1000
    enable_memory_tracking: bool = True
    output_threshold_ms: float = 1.0  # Only log operations slower than this


@dataclass
class PerformanceMetric:
    """A performance metric with statistics."""
    name: str
    total_value: float = 0.0
    count: int = 0
    min_value: float = float('inf')
    max_value: float = 0.0
    recent_values: deque = field(default_factory=lambda: deque(maxlen=100))
    last_updated: datetime = field(default_factory=datetime.now)
    
    @property
    def average_value(self) -> float:
        """Calculate average value."""
        return self.total_value / self.count if self.count > 0 else 0.0
    
    def add_value(self, value: float) -> None:
        """Add a new value to the metric."""
        self.total_value += value
        self.count += 1
        self.min_value = min(self.min_value, value)
        self.max_value = max(self.max_value, value)
        self.recent_values.append(value)
        self.last_updated = datetime.now()


class PerformanceProfiler:
    """Main performance profiling system."""
    
    def __init__(self, config: Optional[ProfilingConfiguration] = None):
        self.config = config or ProfilingConfiguration()
        self.metrics: Dict[str, PerformanceMetric] = {}
        self.active_operations: Dict[str, float] = {}  # operation_id -> start_time
        self.profiling_overhead_ms = 0.0
        self.profiling_call_count = 0
        self.lock = threading.RLock()
    
    @contextmanager
    def profile_operation(self, operation_name: str, custom_data: Optional[Dict[str, Any]] = None):
        """Context manager for profiling operations."""
        if self.config.level == ProfilingLevel.DISABLED:
            yield
            return
        
        operation_id = f"{operation_name}_{threading.get_ident()}_{time.time()}"
        
        # Start profiling
        start_time = time.time()
        profiling_start = time.time()
        
        try:
            with self.lock:
                self.active_operations[operation_id] = start_time
            
            yield
            
        finally:
            # End profiling
            end_time = time.time()
            profiling_end = time.time()
            
            # Track profiling overhead
            overhead = (profiling_end - profiling_start - (end_time - start_time)) * 1000
            self.profiling_overhead_ms += overhead
            self.profiling_call_count += 1
            
            duration_ms = (end_time - start_time) * 1000
            
            # Only record if above threshold
            if duration_ms >= self.config.output_threshold_ms:
                self._record_timing_metric(operation_name, duration_ms)
            
            with self.lock:
                self.active_operations.pop(operation_id, None)
    
    def record_metric(self, name: str, value: float) -> None:
        """Record a custom metric value."""
        with self.lock:
            if name not in self.metrics:
                self.metrics[name] = PerformanceMetric(name)
            
            self.metrics[name].add_value(value)
    
    def _record_timing_metric(self, operation_name: str, duration_ms: float) -> None:
        """Record a timing metric."""
        with self.lock:
            timing_metric_name = f"{operation_name}_timing"
            if timing_metric_name not in self.metrics:
                self.metrics[timing_metric_name] = PerformanceMetric(timing_metric_name)
            self.metrics[timing_metric_name].add_value(duration_ms)
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all metrics with their statistics."""
        with self.lock:
            return {
                name: {
                    'name': metric.name,
                    'count': metric.count,
                    'total': metric.total_value,
                    'average': metric.average_value,
                    'min': metric.min_value if metric.min_value != float('inf') else 0.0,
                    'max': metric.max_value,
                    'last_updated': metric.last_updated.isoformat()
                }
                for name, metric in self.metrics.items()
            }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        return {
            'configuration': {
                'level': self.config.level.value,
                'sample_rate': self.config.sample_rate,
                'max_history_size': self.config.max_history_size,
                'memory_tracking_enabled': self.config.enable_memory_tracking
            },
            'metrics': self.get_all_metrics(),
            'profiling_overhead': {
                'total_overhead_ms': self.profiling_overhead_ms,
                'call_count': self.profiling_call_count,
                'average_overhead_per_call_ms': (
                    self.profiling_overhead_ms / self.profiling_call_count 
                    if self.profiling_call_count > 0 else 0.0
                )
            },
            'active_operations': len(self.active_operations),
            'report_generated': datetime.now().isoformat()
        }


# Convenience functions for global profiler instance
_global_profiler: Optional[PerformanceProfiler] = None


def get_global_profiler() -> PerformanceProfiler:
    """Get or create global profiler instance."""
    global _global_profiler
    if _global_profiler is None:
        _global_profiler = PerformanceProfiler()
    return _global_profiler


def profile_operation(operation_name: str, custom_data: Optional[Dict[str, Any]] = None):
    """Context manager using global profiler."""
    return get_global_profiler().profile_operation(operation_name, custom_data)