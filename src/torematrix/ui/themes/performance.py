"""Performance optimization utilities for the theme system.

This module provides advanced performance monitoring, optimization tools,
and caching strategies for efficient theme operations.
"""

import logging
import time
import threading
import psutil
from typing import Dict, List, Optional, Any, Callable, NamedTuple
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict, deque
from enum import Enum
import json

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .base import Theme
from .exceptions import ThemeError

logger = logging.getLogger(__name__)


class PerformanceMetric(Enum):
    """Performance metrics tracked by the system."""
    THEME_LOAD_TIME = "theme_load_time"
    STYLESHEET_GENERATION_TIME = "stylesheet_generation_time"
    THEME_SWITCH_TIME = "theme_switch_time"
    MEMORY_USAGE = "memory_usage"
    CACHE_HIT_RATIO = "cache_hit_ratio"
    CSS_COMPILATION_TIME = "css_compilation_time"
    HOT_RELOAD_TIME = "hot_reload_time"


@dataclass
class PerformanceSnapshot:
    """Snapshot of performance metrics at a point in time."""
    timestamp: float
    theme_name: str
    metric_type: PerformanceMetric
    value: float
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceTarget:
    """Performance target definition."""
    metric: PerformanceMetric
    target_value: float
    warning_threshold: float
    critical_threshold: float
    unit: str = "ms"


@dataclass
class OptimizationSuggestion:
    """Performance optimization suggestion."""
    category: str
    priority: str  # "low", "medium", "high", "critical"
    description: str
    potential_improvement: str
    implementation_complexity: str  # "easy", "medium", "hard"
    code_example: Optional[str] = None


class PerformanceProfiler:
    """Advanced performance profiler for theme operations."""
    
    def __init__(self, max_snapshots: int = 1000):
        """Initialize performance profiler.
        
        Args:
            max_snapshots: Maximum number of snapshots to retain
        """
        self.max_snapshots = max_snapshots
        self.snapshots: deque = deque(maxlen=max_snapshots)
        self.active_sessions: Dict[str, float] = {}
        self.lock = threading.Lock()
        
        # Performance targets
        self.targets = {
            PerformanceMetric.THEME_LOAD_TIME: PerformanceTarget(
                metric=PerformanceMetric.THEME_LOAD_TIME,
                target_value=50.0,    # 50ms
                warning_threshold=100.0,  # 100ms
                critical_threshold=200.0,  # 200ms
                unit="ms"
            ),
            PerformanceMetric.STYLESHEET_GENERATION_TIME: PerformanceTarget(
                metric=PerformanceMetric.STYLESHEET_GENERATION_TIME,
                target_value=100.0,   # 100ms
                warning_threshold=200.0,  # 200ms
                critical_threshold=500.0,  # 500ms
                unit="ms"
            ),
            PerformanceMetric.THEME_SWITCH_TIME: PerformanceTarget(
                metric=PerformanceMetric.THEME_SWITCH_TIME,
                target_value=200.0,   # 200ms
                warning_threshold=500.0,  # 500ms
                critical_threshold=1000.0,  # 1s
                unit="ms"
            ),
            PerformanceMetric.MEMORY_USAGE: PerformanceTarget(
                metric=PerformanceMetric.MEMORY_USAGE,
                target_value=5.0,     # 5MB per theme
                warning_threshold=10.0,   # 10MB
                critical_threshold=20.0,  # 20MB
                unit="MB"
            ),
            PerformanceMetric.CACHE_HIT_RATIO: PerformanceTarget(
                metric=PerformanceMetric.CACHE_HIT_RATIO,
                target_value=0.85,    # 85%
                warning_threshold=0.70,   # 70%
                critical_threshold=0.50,  # 50%
                unit="%"
            ),
        }
    
    def start_session(self, session_id: str) -> None:
        """Start a performance measurement session.
        
        Args:
            session_id: Unique identifier for the session
        """
        with self.lock:
            self.active_sessions[session_id] = time.time()
    
    def end_session(
        self, 
        session_id: str, 
        theme_name: str, 
        metric_type: PerformanceMetric,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> float:
        """End a performance measurement session and record the result.
        
        Args:
            session_id: Session identifier
            theme_name: Name of theme being measured
            metric_type: Type of metric being measured
            additional_data: Additional data to store with the snapshot
            
        Returns:
            Duration of the session in milliseconds
        """
        with self.lock:
            if session_id not in self.active_sessions:
                logger.warning(f"Session '{session_id}' not found")
                return 0.0
            
            start_time = self.active_sessions.pop(session_id)
            duration = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Create snapshot
            snapshot = PerformanceSnapshot(
                timestamp=time.time(),
                theme_name=theme_name,
                metric_type=metric_type,
                value=duration,
                additional_data=additional_data or {}
            )
            
            self.snapshots.append(snapshot)
            
            # Check against targets
            self._check_performance_target(snapshot)
            
            return duration
    
    def record_metric(
        self, 
        theme_name: str, 
        metric_type: PerformanceMetric, 
        value: float,
        additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a performance metric directly.
        
        Args:
            theme_name: Name of theme
            metric_type: Type of metric
            value: Metric value
            additional_data: Additional data to store
        """
        snapshot = PerformanceSnapshot(
            timestamp=time.time(),
            theme_name=theme_name,
            metric_type=metric_type,
            value=value,
            additional_data=additional_data or {}
        )
        
        with self.lock:
            self.snapshots.append(snapshot)
        
        self._check_performance_target(snapshot)
    
    def _check_performance_target(self, snapshot: PerformanceSnapshot) -> None:
        """Check snapshot against performance targets."""
        target = self.targets.get(snapshot.metric_type)
        if not target:
            return
        
        if snapshot.value > target.critical_threshold:
            logger.error(f"CRITICAL: {snapshot.metric_type.value} for '{snapshot.theme_name}' "
                        f"({snapshot.value:.1f}{target.unit}) exceeds critical threshold "
                        f"({target.critical_threshold}{target.unit})")
        elif snapshot.value > target.warning_threshold:
            logger.warning(f"WARNING: {snapshot.metric_type.value} for '{snapshot.theme_name}' "
                          f"({snapshot.value:.1f}{target.unit}) exceeds warning threshold "
                          f"({target.warning_threshold}{target.unit})")
        elif snapshot.value > target.target_value:
            logger.info(f"INFO: {snapshot.metric_type.value} for '{snapshot.theme_name}' "
                       f"({snapshot.value:.1f}{target.unit}) exceeds target "
                       f"({target.target_value}{target.unit})")
    
    def get_statistics(
        self, 
        metric_type: Optional[PerformanceMetric] = None,
        theme_name: Optional[str] = None,
        time_window: Optional[float] = None
    ) -> Dict[str, Any]:
        """Get performance statistics.
        
        Args:
            metric_type: Filter by metric type
            theme_name: Filter by theme name
            time_window: Time window in seconds (None for all time)
            
        Returns:
            Performance statistics
        """
        with self.lock:
            # Filter snapshots
            filtered_snapshots = list(self.snapshots)
            
            if time_window:
                cutoff_time = time.time() - time_window
                filtered_snapshots = [s for s in filtered_snapshots if s.timestamp >= cutoff_time]
            
            if metric_type:
                filtered_snapshots = [s for s in filtered_snapshots if s.metric_type == metric_type]
            
            if theme_name:
                filtered_snapshots = [s for s in filtered_snapshots if s.theme_name == theme_name]
            
            if not filtered_snapshots:
                return {}
            
            # Calculate statistics
            values = [s.value for s in filtered_snapshots]
            
            return {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'median': sorted(values)[len(values) // 2],
                'total_time_span': max(s.timestamp for s in filtered_snapshots) - 
                                  min(s.timestamp for s in filtered_snapshots) if len(filtered_snapshots) > 1 else 0,
                'themes_measured': len(set(s.theme_name for s in filtered_snapshots)),
            }
    
    def get_recent_snapshots(self, count: int = 10) -> List[PerformanceSnapshot]:
        """Get most recent performance snapshots.
        
        Args:
            count: Number of snapshots to retrieve
            
        Returns:
            List of recent snapshots
        """
        with self.lock:
            return list(self.snapshots)[-count:]
    
    def clear_snapshots(self) -> None:
        """Clear all performance snapshots."""
        with self.lock:
            self.snapshots.clear()
            self.active_sessions.clear()


class MemoryProfiler:
    """Memory usage profiler for theme operations."""
    
    def __init__(self):
        """Initialize memory profiler."""
        self.baseline_memory = self._get_memory_usage()
        self.theme_memory_usage: Dict[str, float] = {}
        
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except Exception:
            return 0.0
    
    def start_measurement(self, theme_name: str) -> None:
        """Start memory measurement for theme.
        
        Args:
            theme_name: Name of theme
        """
        current_memory = self._get_memory_usage()
        self.theme_memory_usage[f"{theme_name}_start"] = current_memory
    
    def end_measurement(self, theme_name: str) -> float:
        """End memory measurement and calculate usage.
        
        Args:
            theme_name: Name of theme
            
        Returns:
            Memory usage in MB
        """
        current_memory = self._get_memory_usage()
        start_key = f"{theme_name}_start"
        
        if start_key in self.theme_memory_usage:
            start_memory = self.theme_memory_usage.pop(start_key)
            usage = current_memory - start_memory
            self.theme_memory_usage[theme_name] = usage
            return usage
        
        return 0.0
    
    def get_theme_memory_usage(self, theme_name: str) -> float:
        """Get memory usage for specific theme.
        
        Args:
            theme_name: Name of theme
            
        Returns:
            Memory usage in MB
        """
        return self.theme_memory_usage.get(theme_name, 0.0)
    
    def get_total_theme_memory(self) -> float:
        """Get total memory usage by all themes.
        
        Returns:
            Total memory usage in MB
        """
        return sum(usage for theme, usage in self.theme_memory_usage.items() 
                  if not theme.endswith('_start'))


class PerformanceOptimizer:
    """Performance optimization analyzer and advisor."""
    
    def __init__(self, profiler: PerformanceProfiler, memory_profiler: MemoryProfiler):
        """Initialize performance optimizer.
        
        Args:
            profiler: Performance profiler instance
            memory_profiler: Memory profiler instance
        """
        self.profiler = profiler
        self.memory_profiler = memory_profiler
    
    def analyze_performance(self, theme_name: Optional[str] = None) -> List[OptimizationSuggestion]:
        """Analyze performance and generate optimization suggestions.
        
        Args:
            theme_name: Specific theme to analyze (None for all)
            
        Returns:
            List of optimization suggestions
        """
        suggestions = []
        
        # Analyze stylesheet generation times
        generation_stats = self.profiler.get_statistics(
            PerformanceMetric.STYLESHEET_GENERATION_TIME, 
            theme_name
        )
        
        if generation_stats and generation_stats['avg'] > 100:  # 100ms threshold
            suggestions.append(OptimizationSuggestion(
                category="Stylesheet Generation",
                priority="high" if generation_stats['avg'] > 200 else "medium",
                description=f"Stylesheet generation averaging {generation_stats['avg']:.1f}ms",
                potential_improvement="50-70% faster generation with caching",
                implementation_complexity="medium",
                code_example="""
# Enable aggressive caching
cache = ThemeCache(max_size=100, enable_compression=True)
generator = StyleSheetGenerator(cache=cache)
"""
            ))
        
        # Analyze memory usage
        total_memory = self.memory_profiler.get_total_theme_memory()
        if total_memory > 50:  # 50MB threshold
            suggestions.append(OptimizationSuggestion(
                category="Memory Usage",
                priority="high" if total_memory > 100 else "medium",
                description=f"High memory usage: {total_memory:.1f}MB total",
                potential_improvement="30-50% memory reduction with optimizations",
                implementation_complexity="medium",
                code_example="""
# Enable memory optimization
optimizer = MemoryOptimizer()
optimizer.enable_stylesheet_compression()
optimizer.enable_lazy_loading()
optimizer.set_cache_limit(themes=20)
"""
            ))
        
        # Analyze cache hit ratio
        cache_stats = self.profiler.get_statistics(PerformanceMetric.CACHE_HIT_RATIO)
        if cache_stats and cache_stats['avg'] < 0.8:  # 80% threshold
            suggestions.append(OptimizationSuggestion(
                category="Caching",
                priority="medium",
                description=f"Low cache hit ratio: {cache_stats['avg']:.1%}",
                potential_improvement="2-3x faster theme operations",
                implementation_complexity="easy",
                code_example="""
# Increase cache size and enable preloading
cache.set_max_size(200)
cache.enable_preloading(most_used_themes)
"""
            ))
        
        # Analyze theme switching times
        switch_stats = self.profiler.get_statistics(
            PerformanceMetric.THEME_SWITCH_TIME, 
            theme_name
        )
        
        if switch_stats and switch_stats['avg'] > 500:  # 500ms threshold
            suggestions.append(OptimizationSuggestion(
                category="Theme Switching",
                priority="high",
                description=f"Slow theme switching: {switch_stats['avg']:.1f}ms average",
                potential_improvement="60-80% faster switching with precompilation",
                implementation_complexity="hard",
                code_example="""
# Enable theme precompilation
precompiler = ThemePrecompiler()
precompiler.precompile_all_themes()
precompiler.enable_background_compilation()
"""
            ))
        
        return suggestions
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report.
        
        Returns:
            Performance report dictionary
        """
        report = {
            'timestamp': time.time(),
            'summary': {},
            'metrics': {},
            'suggestions': self.analyze_performance(),
            'targets': {}
        }
        
        # Overall summary
        all_snapshots = self.profiler.get_recent_snapshots(1000)
        report['summary'] = {
            'total_measurements': len(all_snapshots),
            'themes_measured': len(set(s.theme_name for s in all_snapshots)),
            'time_span_hours': (max(s.timestamp for s in all_snapshots) - 
                               min(s.timestamp for s in all_snapshots)) / 3600 if all_snapshots else 0,
            'total_memory_mb': self.memory_profiler.get_total_theme_memory(),
        }
        
        # Per-metric statistics
        for metric in PerformanceMetric:
            stats = self.profiler.get_statistics(metric)
            if stats:
                report['metrics'][metric.value] = stats
        
        # Target compliance
        for metric, target in self.profiler.targets.items():
            stats = self.profiler.get_statistics(metric)
            if stats:
                report['targets'][metric.value] = {
                    'target': target.target_value,
                    'current_avg': stats['avg'],
                    'compliance': stats['avg'] <= target.target_value,
                    'warning_exceeded': stats['avg'] > target.warning_threshold,
                    'critical_exceeded': stats['avg'] > target.critical_threshold,
                }
        
        return report
    
    def export_report(self, file_path: Path) -> None:
        """Export performance report to file.
        
        Args:
            file_path: Path to save report
        """
        report = self.get_performance_report()
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)
            
            logger.info(f"Performance report exported to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to export performance report: {e}")


class ThemePerformanceManager(QObject):
    """High-level theme performance management coordinator."""
    
    # Signals for performance events
    performance_warning = pyqtSignal(str, str)  # metric_name, message
    performance_critical = pyqtSignal(str, str)  # metric_name, message
    optimization_available = pyqtSignal(list)   # suggestions
    
    def __init__(self, parent: Optional[QObject] = None):
        """Initialize theme performance manager.
        
        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self.profiler = PerformanceProfiler()
        self.memory_profiler = MemoryProfiler()
        self.optimizer = PerformanceOptimizer(self.profiler, self.memory_profiler)
        
        # Performance monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._periodic_check)
        self.monitor_timer.setInterval(30000)  # 30 seconds
        
        # Enable monitoring by default
        self.monitoring_enabled = True
        
        logger.info("ThemePerformanceManager initialized")
    
    def start_monitoring(self) -> None:
        """Start automatic performance monitoring."""
        if not self.monitor_timer.isActive():
            self.monitor_timer.start()
            self.monitoring_enabled = True
            logger.info("Performance monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop automatic performance monitoring."""
        if self.monitor_timer.isActive():
            self.monitor_timer.stop()
            self.monitoring_enabled = False
            logger.info("Performance monitoring stopped")
    
    def _periodic_check(self) -> None:
        """Periodic performance check."""
        if not self.monitoring_enabled:
            return
        
        try:
            # Generate optimization suggestions
            suggestions = self.optimizer.analyze_performance()
            
            # Filter critical and high priority suggestions
            critical_suggestions = [s for s in suggestions if s.priority == "critical"]
            high_priority_suggestions = [s for s in suggestions if s.priority == "high"]
            
            # Emit signals for critical issues
            if critical_suggestions:
                for suggestion in critical_suggestions:
                    self.performance_critical.emit(suggestion.category, suggestion.description)
            
            # Emit signals for warnings
            if high_priority_suggestions:
                for suggestion in high_priority_suggestions:
                    self.performance_warning.emit(suggestion.category, suggestion.description)
            
            # Emit optimization suggestions
            if suggestions:
                self.optimization_available.emit(suggestions)
        
        except Exception as e:
            logger.error(f"Performance monitoring check failed: {e}")
    
    def measure_operation(self, operation_name: str, theme_name: str, metric_type: PerformanceMetric):
        """Context manager for measuring theme operations.
        
        Usage:
            with manager.measure_operation("stylesheet_gen", "dark", PerformanceMetric.STYLESHEET_GENERATION_TIME):
                # Theme operation code here
                pass
        """
        class OperationMeasurement:
            def __init__(self, performance_manager, op_name, th_name, met_type):
                self.manager = performance_manager
                self.operation_name = op_name
                self.theme_name = th_name
                self.metric_type = met_type
            
            def __enter__(self):
                self.manager.profiler.start_session(self.operation_name)
                if self.metric_type == PerformanceMetric.MEMORY_USAGE:
                    self.manager.memory_profiler.start_measurement(self.theme_name)
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                if self.metric_type == PerformanceMetric.MEMORY_USAGE:
                    memory_usage = self.manager.memory_profiler.end_measurement(self.theme_name)
                    self.manager.profiler.record_metric(
                        self.theme_name, 
                        self.metric_type, 
                        memory_usage
                    )
                else:
                    self.manager.profiler.end_session(
                        self.operation_name,
                        self.theme_name,
                        self.metric_type
                    )
        
        return OperationMeasurement(self, operation_name, theme_name, metric_type)
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for UI display.
        
        Returns:
            Performance summary suitable for UI
        """
        return {
            'current_memory_mb': self.memory_profiler._get_memory_usage(),
            'total_theme_memory_mb': self.memory_profiler.get_total_theme_memory(),
            'recent_operations': len(self.profiler.get_recent_snapshots(100)),
            'monitoring_active': self.monitoring_enabled,
            'suggestions_count': len(self.optimizer.analyze_performance()),
        }
    
    def clear_performance_data(self) -> None:
        """Clear all performance data."""
        self.profiler.clear_snapshots()
        self.memory_profiler.theme_memory_usage.clear()
        logger.info("Performance data cleared")