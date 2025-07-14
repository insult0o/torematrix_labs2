"""
Performance monitoring and optimization for zoom/pan controls.
Provides real-time performance tracking, analysis, and optimization suggestions.
"""

from typing import Dict, List, Optional, Tuple, Any, Callable
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
import time
import psutil
import threading
from collections import deque, defaultdict
from dataclasses import dataclass, field
from enum import Enum
import statistics
import gc
import sys


class PerformanceLevel(Enum):
    """Performance quality levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    CRITICAL = "critical"


@dataclass
class PerformanceMetrics:
    """Performance measurement data."""
    operation_type: str
    execution_time: float  # milliseconds
    memory_usage: float   # megabytes
    cpu_usage: float     # percentage
    timestamp: float = field(default_factory=time.time)
    frame_rate: Optional[float] = None
    
    def meets_target(self, target_time: float = 16.0) -> bool:
        """Check if execution time meets target (default 60fps)."""
        return self.execution_time <= target_time


class PerformanceMonitor(QObject):
    """
    Real-time performance monitoring system for zoom/pan controls.
    Tracks execution times, memory usage, and frame rates.
    """
    
    # Performance signals
    performance_data_updated = pyqtSignal(dict)  # latest_metrics
    performance_warning = pyqtSignal(str, dict)  # warning_type, details
    optimization_suggestion = pyqtSignal(str, dict)  # suggestion_type, details
    frame_rate_changed = pyqtSignal(float)  # current_fps
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Monitoring configuration
        self.monitoring_enabled = True
        self.detailed_monitoring = False  # Enables more expensive monitoring
        self.sample_rate = 60  # Hz - how often to collect samples
        self.history_size = 1000  # Number of samples to keep
        
        # Performance targets
        self.targets = {
            'zoom_operation': 16.0,      # 60fps
            'pan_operation': 8.0,        # 120fps for smooth panning
            'animation_frame': 16.0,     # 60fps
            'ui_update': 32.0,           # 30fps minimum
            'gesture_recognition': 10.0,  # 100fps for responsiveness
            'memory_limit': 100.0,       # 100MB
            'cpu_limit': 80.0            # 80% CPU
        }
        
        # Data storage
        self.metrics_history = deque(maxlen=self.history_size)
        self.operation_timings = defaultdict(lambda: deque(maxlen=100))
        self.frame_times = deque(maxlen=120)  # 2 seconds at 60fps
        
        # System monitoring
        self.system_metrics = {}
        self.last_frame_time = time.time()
        self.frame_count = 0
        
        # Monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._collect_system_metrics)
        self.monitor_timer.setInterval(1000 // self.sample_rate)  # Based on sample rate
        
        # Garbage collection monitoring
        self.gc_stats = {'collections': 0, 'time': 0.0}
        
        # Thread safety
        self._metrics_lock = threading.RLock()
        
        # Start monitoring
        if self.monitoring_enabled:
            self.start_monitoring()
    
    def start_monitoring(self):
        """Start performance monitoring."""
        self.monitoring_enabled = True
        self.monitor_timer.start()
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring_enabled = False
        self.monitor_timer.stop()
    
    def record_operation(self, operation_type: str, execution_time: float, 
                        additional_data: Dict[str, Any] = None):
        """
        Record performance data for an operation.
        
        Args:
            operation_type: Type of operation performed
            execution_time: Time taken in milliseconds
            additional_data: Additional performance data
        """
        if not self.monitoring_enabled:
            return
        
        try:
            with self._metrics_lock:
                # Get system metrics if detailed monitoring enabled
                memory_usage = 0.0
                cpu_usage = 0.0
                
                if self.detailed_monitoring:
                    process = psutil.Process()
                    memory_usage = process.memory_info().rss / 1024 / 1024  # MB
                    cpu_usage = process.cpu_percent()
                
                # Create metrics entry
                metrics = PerformanceMetrics(
                    operation_type=operation_type,
                    execution_time=execution_time,
                    memory_usage=memory_usage,
                    cpu_usage=cpu_usage
                )
                
                # Add additional data
                if additional_data:
                    for key, value in additional_data.items():
                        setattr(metrics, key, value)
                
                # Store metrics
                self.metrics_history.append(metrics)
                self.operation_timings[operation_type].append(execution_time)
                
                # Check for performance issues
                self._check_performance_warnings(metrics)
                
                # Emit update
                self.performance_data_updated.emit(self._get_current_summary())
                
        except Exception as e:
            # Avoid recursion - don't record performance issues in performance monitoring
            pass
    
    def record_frame_time(self, frame_time: float):
        """Record frame rendering time for FPS calculation."""
        if not self.monitoring_enabled:
            return
        
        with self._metrics_lock:
            self.frame_times.append(frame_time)
            self.frame_count += 1
            
            # Calculate current FPS
            if len(self.frame_times) > 10:  # Need enough samples
                avg_frame_time = statistics.mean(list(self.frame_times)[-60:])  # Last second
                current_fps = 1000.0 / avg_frame_time if avg_frame_time > 0 else 0
                self.frame_rate_changed.emit(current_fps)
    
    def get_operation_statistics(self, operation_type: str) -> Dict[str, float]:
        """Get statistical analysis for specific operation type."""
        if operation_type not in self.operation_timings:
            return {}
        
        timings = list(self.operation_timings[operation_type])
        if not timings:
            return {}
        
        return {
            'count': len(timings),
            'mean': statistics.mean(timings),
            'median': statistics.median(timings),
            'std_dev': statistics.stdev(timings) if len(timings) > 1 else 0,
            'min': min(timings),
            'max': max(timings),
            'p95': self._percentile(timings, 95),
            'p99': self._percentile(timings, 99),
            'target': self.targets.get(operation_type, 16.0),
            'meets_target': statistics.mean(timings) <= self.targets.get(operation_type, 16.0)
        }
    
    def get_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        report = {
            'summary': self._get_current_summary(),
            'operations': {},
            'system': self.system_metrics.copy(),
            'frame_rate': self._calculate_frame_rate(),
            'memory': self._get_memory_analysis(),
            'recommendations': self._generate_recommendations()
        }
        
        # Add per-operation statistics
        for operation_type in self.operation_timings.keys():
            report['operations'][operation_type] = self.get_operation_statistics(operation_type)
        
        return report
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Get current real-time performance metrics."""
        with self._metrics_lock:
            if not self.metrics_history:
                return {}
            
            recent_metrics = list(self.metrics_history)[-10:]  # Last 10 operations
            
            return {
                'current_fps': self._calculate_frame_rate(),
                'avg_execution_time': statistics.mean([m.execution_time for m in recent_metrics]),
                'memory_usage': recent_metrics[-1].memory_usage if self.detailed_monitoring else 0,
                'cpu_usage': recent_metrics[-1].cpu_usage if self.detailed_monitoring else 0,
                'operation_count': len(self.metrics_history),
                'performance_level': self._assess_performance_level()
            }
    
    def optimize_performance(self, target_level: PerformanceLevel = PerformanceLevel.HIGH):
        """Apply performance optimizations based on current metrics."""
        current_level = self._assess_performance_level()
        
        if current_level == target_level:
            return  # Already at target level
        
        optimizations = []
        
        # Check frame rate
        current_fps = self._calculate_frame_rate()
        if current_fps < 30:
            optimizations.append(('reduce_quality', {'reason': 'low_fps', 'current_fps': current_fps}))
        
        # Check memory usage
        if self.detailed_monitoring and self._get_memory_usage() > self.targets['memory_limit']:
            optimizations.append(('reduce_memory', {'reason': 'high_memory'}))
            self._force_garbage_collection()
        
        # Check operation timings
        for op_type, timings in self.operation_timings.items():
            if timings and statistics.mean(list(timings)[-10:]) > self.targets.get(op_type, 16.0):
                optimizations.append(('optimize_operation', {
                    'operation': op_type,
                    'current_time': statistics.mean(list(timings)[-10:]),
                    'target': self.targets.get(op_type, 16.0)
                }))
        
        # Apply optimizations
        for optimization_type, details in optimizations:
            self.optimization_suggestion.emit(optimization_type, details)
    
    def set_performance_targets(self, targets: Dict[str, float]):
        """Update performance targets."""
        self.targets.update(targets)
    
    def enable_detailed_monitoring(self, enabled: bool = True):
        """Enable/disable detailed system monitoring (CPU, memory)."""
        self.detailed_monitoring = enabled
    
    def clear_metrics_history(self):
        """Clear all collected metrics."""
        with self._metrics_lock:
            self.metrics_history.clear()
            self.operation_timings.clear()
            self.frame_times.clear()
            self.frame_count = 0
    
    def export_metrics(self) -> List[Dict[str, Any]]:
        """Export metrics data for analysis."""
        with self._metrics_lock:
            return [
                {
                    'operation_type': m.operation_type,
                    'execution_time': m.execution_time,
                    'memory_usage': m.memory_usage,
                    'cpu_usage': m.cpu_usage,
                    'timestamp': m.timestamp,
                    'frame_rate': m.frame_rate
                }
                for m in self.metrics_history
            ]
    
    # Private methods
    
    def _collect_system_metrics(self):
        """Collect system-wide performance metrics."""
        if not self.detailed_monitoring:
            return
        
        try:
            process = psutil.Process()
            
            self.system_metrics.update({
                'memory_percent': process.memory_percent(),
                'cpu_percent': process.cpu_percent(),
                'num_threads': process.num_threads(),
                'open_files': len(process.open_files()),
                'timestamp': time.time()
            })
            
            # System-wide metrics
            self.system_metrics.update({
                'system_memory_percent': psutil.virtual_memory().percent,
                'system_cpu_percent': psutil.cpu_percent(),
                'available_memory': psutil.virtual_memory().available / 1024 / 1024  # MB
            })
            
        except Exception:
            # Graceful fallback if system monitoring fails
            pass
    
    def _check_performance_warnings(self, metrics: PerformanceMetrics):
        """Check metrics for performance warnings."""
        target = self.targets.get(metrics.operation_type, 16.0)
        
        if metrics.execution_time > target * 2:  # Significantly over target
            self.performance_warning.emit('slow_operation', {
                'operation': metrics.operation_type,
                'time': metrics.execution_time,
                'target': target,
                'severity': 'high' if metrics.execution_time > target * 3 else 'medium'
            })
        
        if self.detailed_monitoring:
            if metrics.memory_usage > self.targets['memory_limit']:
                self.performance_warning.emit('high_memory', {
                    'memory_usage': metrics.memory_usage,
                    'limit': self.targets['memory_limit']
                })
            
            if metrics.cpu_usage > self.targets['cpu_limit']:
                self.performance_warning.emit('high_cpu', {
                    'cpu_usage': metrics.cpu_usage,
                    'limit': self.targets['cpu_limit']
                })
    
    def _get_current_summary(self) -> Dict[str, Any]:
        """Get summary of current performance state."""
        if not self.metrics_history:
            return {'status': 'no_data'}
        
        recent_metrics = list(self.metrics_history)[-10:]
        
        return {
            'avg_execution_time': statistics.mean([m.execution_time for m in recent_metrics]),
            'operation_count': len(self.metrics_history),
            'current_fps': self._calculate_frame_rate(),
            'performance_level': self._assess_performance_level().value,
            'warnings_count': self._count_recent_warnings(),
            'timestamp': time.time()
        }
    
    def _calculate_frame_rate(self) -> float:
        """Calculate current frame rate."""
        if len(self.frame_times) < 10:
            return 0.0
        
        recent_frames = list(self.frame_times)[-60:]  # Last second
        if not recent_frames:
            return 0.0
        
        avg_frame_time = statistics.mean(recent_frames)
        return 1000.0 / avg_frame_time if avg_frame_time > 0 else 0.0
    
    def _assess_performance_level(self) -> PerformanceLevel:
        """Assess current performance level."""
        if not self.metrics_history:
            return PerformanceLevel.HIGH
        
        recent_metrics = list(self.metrics_history)[-20:]
        avg_time = statistics.mean([m.execution_time for m in recent_metrics])
        fps = self._calculate_frame_rate()
        
        if avg_time <= 8.0 and fps >= 60:
            return PerformanceLevel.HIGH
        elif avg_time <= 16.0 and fps >= 30:
            return PerformanceLevel.MEDIUM
        elif avg_time <= 32.0 and fps >= 15:
            return PerformanceLevel.LOW
        else:
            return PerformanceLevel.CRITICAL
    
    def _get_memory_analysis(self) -> Dict[str, Any]:
        """Analyze memory usage patterns."""
        if not self.detailed_monitoring or not self.metrics_history:
            return {}
        
        memory_values = [m.memory_usage for m in self.metrics_history if m.memory_usage > 0]
        if not memory_values:
            return {}
        
        return {
            'current': memory_values[-1] if memory_values else 0,
            'average': statistics.mean(memory_values),
            'peak': max(memory_values),
            'trend': self._calculate_trend(memory_values[-10:]) if len(memory_values) >= 10 else 'stable'
        }
    
    def _generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate performance optimization recommendations."""
        recommendations = []
        
        current_fps = self._calculate_frame_rate()
        performance_level = self._assess_performance_level()
        
        if current_fps < 30:
            recommendations.append({
                'type': 'reduce_animation_quality',
                'priority': 'high',
                'description': 'Consider reducing animation quality to improve frame rate',
                'current_fps': current_fps
            })
        
        if performance_level == PerformanceLevel.CRITICAL:
            recommendations.append({
                'type': 'enable_performance_mode',
                'priority': 'critical',
                'description': 'Enable performance mode to reduce resource usage'
            })
        
        # Check for slow operations
        for op_type, timings in self.operation_timings.items():
            if timings:
                avg_time = statistics.mean(list(timings)[-10:])
                target = self.targets.get(op_type, 16.0)
                
                if avg_time > target * 1.5:
                    recommendations.append({
                        'type': 'optimize_operation',
                        'priority': 'medium',
                        'description': f'Optimize {op_type} operations',
                        'operation': op_type,
                        'current_time': avg_time,
                        'target': target
                    })
        
        return recommendations
    
    def _count_recent_warnings(self) -> int:
        """Count warnings in recent metrics."""
        # This would track warnings emitted in the last period
        # Implementation depends on warning tracking mechanism
        return 0
    
    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction for values."""
        if len(values) < 3:
            return 'stable'
        
        # Simple linear trend calculation
        x = list(range(len(values)))
        correlation = statistics.correlation(x, values) if len(values) > 1 else 0
        
        if correlation > 0.3:
            return 'increasing'
        elif correlation < -0.3:
            return 'decreasing'
        else:
            return 'stable'
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage."""
        if not self.detailed_monitoring:
            return 0.0
        
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # MB
        except Exception:
            return 0.0
    
    def _force_garbage_collection(self):
        """Force garbage collection to free memory."""
        gc_start = time.time()
        collected = gc.collect()
        gc_time = (time.time() - gc_start) * 1000
        
        self.gc_stats['collections'] += 1
        self.gc_stats['time'] += gc_time
        
        if collected > 0:
            self.optimization_suggestion.emit('garbage_collection', {
                'objects_collected': collected,
                'time_ms': gc_time
            })
    
    @staticmethod
    def _percentile(data: List[float], percentile: float) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0.0
        
        sorted_data = sorted(data)
        index = (percentile / 100.0) * (len(sorted_data) - 1)
        
        if index.is_integer():
            return sorted_data[int(index)]
        else:
            lower = sorted_data[int(index)]
            upper = sorted_data[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))


class PerformanceProfiler(QObject):
    """
    Advanced performance profiler for zoom/pan operations.
    Provides detailed analysis and bottleneck identification.
    """
    
    profiling_complete = pyqtSignal(dict)  # profile_results
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.profiling_active = False
        self.profile_data = {}
        self.start_time = 0.0
    
    def start_profiling(self, operation_name: str):
        """Start profiling an operation."""
        self.operation_name = operation_name
        self.start_time = time.perf_counter()
        self.profiling_active = True
        self.profile_data = {
            'operation': operation_name,
            'start_time': self.start_time,
            'checkpoints': []
        }
    
    def checkpoint(self, name: str):
        """Add profiling checkpoint."""
        if not self.profiling_active:
            return
        
        current_time = time.perf_counter()
        elapsed = (current_time - self.start_time) * 1000
        
        self.profile_data['checkpoints'].append({
            'name': name,
            'elapsed_time': elapsed,
            'timestamp': current_time
        })
    
    def end_profiling(self) -> Dict[str, Any]:
        """End profiling and return results."""
        if not self.profiling_active:
            return {}
        
        end_time = time.perf_counter()
        total_time = (end_time - self.start_time) * 1000
        
        self.profile_data.update({
            'total_time': total_time,
            'end_time': end_time
        })
        
        self.profiling_active = False
        
        # Analyze bottlenecks
        analysis = self._analyze_profile()
        self.profile_data['analysis'] = analysis
        
        self.profiling_complete.emit(self.profile_data.copy())
        return self.profile_data
    
    def _analyze_profile(self) -> Dict[str, Any]:
        """Analyze profile data for bottlenecks."""
        if not self.profile_data.get('checkpoints'):
            return {}
        
        checkpoints = self.profile_data['checkpoints']
        total_time = self.profile_data['total_time']
        
        # Calculate time between checkpoints
        checkpoint_times = []
        for i in range(len(checkpoints)):
            if i == 0:
                time_taken = checkpoints[i]['elapsed_time']
            else:
                time_taken = checkpoints[i]['elapsed_time'] - checkpoints[i-1]['elapsed_time']
            
            checkpoint_times.append({
                'name': checkpoints[i]['name'],
                'time': time_taken,
                'percentage': (time_taken / total_time) * 100
            })
        
        # Identify bottlenecks (operations taking >20% of total time)
        bottlenecks = [cp for cp in checkpoint_times if cp['percentage'] > 20]
        
        return {
            'checkpoint_times': checkpoint_times,
            'bottlenecks': bottlenecks,
            'total_checkpoints': len(checkpoints),
            'bottleneck_count': len(bottlenecks)
        }