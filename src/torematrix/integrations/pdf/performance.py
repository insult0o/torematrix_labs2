"""
PDF.js Performance Optimization System.

This module provides comprehensive performance monitoring, optimization,
and configuration for PDF.js integration with focus on large document handling.
"""
from __future__ import annotations

import gc
import os
import time
import threading
import psutil
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Tuple
from enum import Enum
from collections import deque

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, QThread
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView

from .cache import MemoryCache, CacheManager
from .memory import MemoryManager, MemoryPool
from .metrics import MetricsCollector, PerformanceMetrics


class PerformanceLevel(Enum):
    """Performance optimization levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class HardwareCapability(Enum):
    """Hardware acceleration capabilities."""
    SOFTWARE_ONLY = "software"
    BASIC_GPU = "basic_gpu"
    ADVANCED_GPU = "advanced_gpu"


@dataclass
class PerformanceConfig:
    """Performance configuration settings."""
    # Memory Management
    cache_size_mb: int = 200
    max_preload_pages: int = 5
    memory_pressure_threshold: float = 0.8
    gc_threshold_mb: int = 100
    
    # Performance Levels
    performance_level: PerformanceLevel = PerformanceLevel.MEDIUM
    enable_gpu_acceleration: bool = True
    enable_lazy_loading: bool = True
    enable_progressive_rendering: bool = True
    
    # Hardware Settings
    hardware_capability: HardwareCapability = HardwareCapability.BASIC_GPU
    enable_webgl: bool = True
    enable_hardware_canvas: bool = True
    
    # Monitoring
    enable_performance_monitoring: bool = True
    metrics_collection_interval: float = 1.0
    performance_logging: bool = True
    
    # Optimization Thresholds
    large_pdf_threshold_mb: int = 50
    page_render_timeout_ms: int = 5000
    max_concurrent_renders: int = 3
    
    # Cache Configuration
    enable_page_cache: bool = True
    enable_image_cache: bool = True
    cache_compression: bool = True
    cache_persistence: bool = False


@dataclass
class PerformanceMetrics:
    """Real-time performance metrics."""
    # Memory Metrics
    memory_usage_mb: float = 0.0
    peak_memory_mb: float = 0.0
    cache_hit_rate: float = 0.0
    cache_size_mb: float = 0.0
    
    # Performance Metrics
    page_load_time_ms: float = 0.0
    render_time_ms: float = 0.0
    navigation_time_ms: float = 0.0
    
    # Hardware Metrics
    gpu_acceleration_active: bool = False
    gpu_memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    # Document Metrics
    document_size_mb: float = 0.0
    total_pages: int = 0
    loaded_pages: int = 0
    cached_pages: int = 0
    
    # Timing Metrics
    timestamp: float = field(default_factory=time.time)
    collection_time_ms: float = 0.0


class PerformanceMonitor(QObject):
    """
    Real-time performance monitoring and optimization system.
    
    Monitors PDF.js performance, manages memory usage, and provides
    real-time feedback for optimization decisions.
    """
    
    # Signals
    metrics_updated = pyqtSignal(PerformanceMetrics)
    memory_pressure_warning = pyqtSignal(float)  # usage_percent
    performance_issue_detected = pyqtSignal(str, dict)  # issue_type, details
    optimization_applied = pyqtSignal(str, dict)  # optimization_type, details
    
    def __init__(self, config: PerformanceConfig):
        super().__init__()
        self.config = config
        self.metrics_collector = MetricsCollector()
        self.memory_manager = MemoryManager(config)
        self.cache_manager = CacheManager(config)
        
        # Performance state
        self.current_metrics = PerformanceMetrics()
        self.performance_history: deque = deque(maxlen=1000)
        self.is_monitoring = False
        self.optimization_callbacks: List[Callable] = []
        
        # Hardware detection
        self.hardware_capability = self._detect_hardware_capability()
        self.gpu_acceleration_available = self._check_gpu_acceleration()
        
        # Monitoring timer
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._collect_metrics)
        
        # Process monitoring
        self.process = psutil.Process()
        self.performance_thread: Optional[QThread] = None
        
        # Performance thresholds
        self.thresholds = {
            'memory_warning': 0.75,
            'memory_critical': 0.90,
            'render_time_warning': 1000,  # ms
            'load_time_warning': 5000,    # ms
            'cpu_usage_warning': 80       # percent
        }
    
    def start_monitoring(self) -> None:
        """Start performance monitoring."""
        if not self.is_monitoring:
            self.is_monitoring = True
            interval_ms = int(self.config.metrics_collection_interval * 1000)
            self.monitor_timer.start(interval_ms)
            
            # Start memory manager
            self.memory_manager.start()
            
            # Start cache manager
            self.cache_manager.start()
            
            if self.config.performance_logging:
                print(f"Performance monitoring started (interval: {interval_ms}ms)")
    
    def stop_monitoring(self) -> None:
        """Stop performance monitoring."""
        if self.is_monitoring:
            self.is_monitoring = False
            self.monitor_timer.stop()
            
            # Stop managers
            self.memory_manager.stop()
            self.cache_manager.stop()
            
            if self.config.performance_logging:
                print("Performance monitoring stopped")
    
    def _collect_metrics(self) -> None:
        """Collect current performance metrics."""
        start_time = time.time()
        
        try:
            # Memory metrics
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)
            
            # Cache metrics
            cache_stats = self.cache_manager.get_statistics()
            
            # Hardware metrics
            gpu_active = self.gpu_acceleration_available and self.config.enable_gpu_acceleration
            cpu_percent = self.process.cpu_percent()
            
            # Create metrics object
            metrics = PerformanceMetrics(
                memory_usage_mb=memory_mb,
                peak_memory_mb=max(self.current_metrics.peak_memory_mb, memory_mb),
                cache_hit_rate=cache_stats.get('hit_rate', 0.0),
                cache_size_mb=cache_stats.get('size_mb', 0.0),
                gpu_acceleration_active=gpu_active,
                cpu_usage_percent=cpu_percent,
                cached_pages=cache_stats.get('cached_pages', 0),
                collection_time_ms=(time.time() - start_time) * 1000
            )
            
            # Update current metrics
            self.current_metrics = metrics
            self.performance_history.append(metrics)
            
            # Check for performance issues
            self._check_performance_issues(metrics)
            
            # Emit metrics update
            self.metrics_updated.emit(metrics)
            
        except Exception as e:
            if self.config.performance_logging:
                print(f"Metrics collection error: {e}")
    
    def _check_performance_issues(self, metrics: PerformanceMetrics) -> None:
        """Check for performance issues and trigger optimizations."""
        # Memory pressure check
        memory_usage_percent = metrics.memory_usage_mb / (self.config.cache_size_mb * 1.5)
        
        if memory_usage_percent > self.thresholds['memory_critical']:
            self.memory_pressure_warning.emit(memory_usage_percent)
            self._trigger_memory_optimization('critical')
        elif memory_usage_percent > self.thresholds['memory_warning']:
            self.memory_pressure_warning.emit(memory_usage_percent)
            self._trigger_memory_optimization('warning')
        
        # Render time check
        if metrics.render_time_ms > self.thresholds['render_time_warning']:
            self.performance_issue_detected.emit('slow_rendering', {
                'render_time': metrics.render_time_ms,
                'threshold': self.thresholds['render_time_warning']
            })
            self._trigger_render_optimization()
        
        # CPU usage check
        if metrics.cpu_usage_percent > self.thresholds['cpu_usage_warning']:
            self.performance_issue_detected.emit('high_cpu', {
                'cpu_usage': metrics.cpu_usage_percent,
                'threshold': self.thresholds['cpu_usage_warning']
            })
            self._trigger_cpu_optimization()
    
    def _trigger_memory_optimization(self, level: str) -> None:
        """Trigger memory optimization based on pressure level."""
        if level == 'critical':
            # Aggressive memory cleanup
            self.memory_manager.emergency_cleanup()
            self.cache_manager.clear_cache(ratio=0.5)
            gc.collect()
        elif level == 'warning':
            # Moderate memory cleanup
            self.memory_manager.cleanup_old_pages()
            self.cache_manager.clear_cache(ratio=0.2)
        
        self.optimization_applied.emit('memory_optimization', {'level': level})
    
    def _trigger_render_optimization(self) -> None:
        """Trigger rendering optimization."""
        # Reduce render quality temporarily
        self.cache_manager.set_quality_mode('performance')
        
        # Limit concurrent renders
        if self.config.max_concurrent_renders > 1:
            self.config.max_concurrent_renders = 1
        
        self.optimization_applied.emit('render_optimization', {
            'quality_mode': 'performance',
            'max_concurrent': 1
        })
    
    def _trigger_cpu_optimization(self) -> None:
        """Trigger CPU optimization."""
        # Increase render intervals
        self.config.performance_level = PerformanceLevel.LOW
        
        # Reduce preload pages
        self.config.max_preload_pages = max(1, self.config.max_preload_pages - 1)
        
        self.optimization_applied.emit('cpu_optimization', {
            'performance_level': 'low',
            'preload_pages': self.config.max_preload_pages
        })
    
    def _detect_hardware_capability(self) -> HardwareCapability:
        """Detect hardware acceleration capabilities."""
        try:
            # Check for GPU availability
            import GPUtil
            gpus = GPUtil.getGPUs()
            
            if gpus:
                # Check GPU memory and capabilities
                gpu = gpus[0]
                if gpu.memoryTotal > 2048:  # >2GB VRAM
                    return HardwareCapability.ADVANCED_GPU
                else:
                    return HardwareCapability.BASIC_GPU
            else:
                return HardwareCapability.SOFTWARE_ONLY
                
        except ImportError:
            # GPUtil not available, fall back to basic detection
            return HardwareCapability.BASIC_GPU
    
    def _check_gpu_acceleration(self) -> bool:
        """Check if GPU acceleration is available."""
        try:
            # Check Qt WebEngine GPU support
            return True  # Assume available for now
        except Exception:
            return False
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        return self.current_metrics
    
    def get_performance_history(self) -> List[PerformanceMetrics]:
        """Get performance history."""
        return list(self.performance_history)
    
    def get_hardware_info(self) -> Dict[str, Any]:
        """Get hardware information."""
        return {
            'capability': self.hardware_capability.value,
            'gpu_acceleration_available': self.gpu_acceleration_available,
            'gpu_enabled': self.config.enable_gpu_acceleration,
            'webgl_enabled': self.config.enable_webgl,
            'hardware_canvas_enabled': self.config.enable_hardware_canvas
        }
    
    def add_optimization_callback(self, callback: Callable) -> None:
        """Add optimization callback."""
        self.optimization_callbacks.append(callback)
    
    def remove_optimization_callback(self, callback: Callable) -> None:
        """Remove optimization callback."""
        if callback in self.optimization_callbacks:
            self.optimization_callbacks.remove(callback)
    
    def update_config(self, config: PerformanceConfig) -> None:
        """Update performance configuration."""
        self.config = config
        self.memory_manager.update_config(config)
        self.cache_manager.update_config(config)
        
        # Update monitoring interval
        if self.is_monitoring:
            interval_ms = int(config.metrics_collection_interval * 1000)
            self.monitor_timer.setInterval(interval_ms)
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get performance optimization recommendations."""
        recommendations = []
        
        if not self.performance_history:
            return recommendations
        
        # Analyze recent performance
        recent_metrics = list(self.performance_history)[-10:]  # Last 10 samples
        
        # Memory recommendations
        avg_memory = sum(m.memory_usage_mb for m in recent_metrics) / len(recent_metrics)
        if avg_memory > self.config.cache_size_mb * 0.8:
            recommendations.append({
                'type': 'memory',
                'priority': 'high',
                'description': 'High memory usage detected',
                'suggestion': 'Consider increasing cache size or reducing preload pages',
                'action': 'increase_cache_size'
            })
        
        # Performance recommendations
        avg_render_time = sum(m.render_time_ms for m in recent_metrics if m.render_time_ms > 0) / len(recent_metrics)
        if avg_render_time > 500:  # 500ms threshold
            recommendations.append({
                'type': 'performance',
                'priority': 'medium',
                'description': 'Slow rendering detected',
                'suggestion': 'Enable hardware acceleration or reduce quality',
                'action': 'enable_gpu_acceleration'
            })
        
        # Hardware recommendations
        if not self.gpu_acceleration_available and self.hardware_capability != HardwareCapability.SOFTWARE_ONLY:
            recommendations.append({
                'type': 'hardware',
                'priority': 'low',
                'description': 'GPU acceleration not enabled',
                'suggestion': 'Enable GPU acceleration for better performance',
                'action': 'enable_gpu'
            })
        
        return recommendations
    
    def apply_optimization(self, optimization_type: str, parameters: Dict[str, Any]) -> bool:
        """Apply performance optimization."""
        try:
            if optimization_type == 'increase_cache_size':
                new_size = parameters.get('size_mb', self.config.cache_size_mb * 1.5)
                self.config.cache_size_mb = int(new_size)
                self.cache_manager.update_config(self.config)
                return True
            
            elif optimization_type == 'enable_gpu_acceleration':
                self.config.enable_gpu_acceleration = True
                self.config.enable_webgl = True
                self.config.enable_hardware_canvas = True
                return True
            
            elif optimization_type == 'reduce_preload_pages':
                self.config.max_preload_pages = max(1, self.config.max_preload_pages - 1)
                return True
            
            elif optimization_type == 'performance_mode':
                level = parameters.get('level', 'medium')
                self.config.performance_level = PerformanceLevel(level)
                return True
            
            return False
            
        except Exception as e:
            if self.config.performance_logging:
                print(f"Optimization application error: {e}")
            return False
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_monitoring()
        self.memory_manager.cleanup()
        self.cache_manager.cleanup()


class PerformanceOptimizer:
    """
    High-level performance optimization orchestrator.
    
    Coordinates all performance optimization systems and provides
    a unified interface for PDF.js performance management.
    """
    
    def __init__(self, viewer: QWebEngineView, config: Optional[PerformanceConfig] = None):
        self.viewer = viewer
        self.config = config or PerformanceConfig()
        
        # Initialize components
        self.monitor = PerformanceMonitor(self.config)
        self.memory_manager = MemoryManager(self.config)
        self.cache_manager = CacheManager(self.config)
        
        # Connect signals
        self.monitor.memory_pressure_warning.connect(self._handle_memory_pressure)
        self.monitor.performance_issue_detected.connect(self._handle_performance_issue)
        
        # Apply initial configuration
        self._apply_initial_configuration()
    
    def _apply_initial_configuration(self) -> None:
        """Apply initial performance configuration to the viewer."""
        # Configure WebEngine settings
        settings = self.viewer.settings()
        
        # Hardware acceleration
        if self.config.enable_gpu_acceleration:
            settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, self.config.enable_webgl)
        
        # Performance settings
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        
        # Apply performance profile
        self._apply_performance_profile(self.config.performance_level)
    
    def _apply_performance_profile(self, level: PerformanceLevel) -> None:
        """Apply performance profile settings."""
        if level == PerformanceLevel.LOW:
            self.config.max_preload_pages = 2
            self.config.max_concurrent_renders = 1
        elif level == PerformanceLevel.MEDIUM:
            self.config.max_preload_pages = 3
            self.config.max_concurrent_renders = 2
        elif level == PerformanceLevel.HIGH:
            self.config.max_preload_pages = 5
            self.config.max_concurrent_renders = 3
        elif level == PerformanceLevel.EXTREME:
            self.config.max_preload_pages = 8
            self.config.max_concurrent_renders = 4
    
    def _handle_memory_pressure(self, usage_percent: float) -> None:
        """Handle memory pressure warnings."""
        if usage_percent > 0.9:
            # Emergency cleanup
            self.memory_manager.emergency_cleanup()
            self.cache_manager.clear_cache(ratio=0.5)
        elif usage_percent > 0.75:
            # Moderate cleanup
            self.memory_manager.cleanup_old_pages()
            self.cache_manager.clear_cache(ratio=0.2)
    
    def _handle_performance_issue(self, issue_type: str, details: Dict[str, Any]) -> None:
        """Handle performance issues."""
        if issue_type == 'slow_rendering':
            # Reduce quality temporarily
            self.cache_manager.set_quality_mode('performance')
        elif issue_type == 'high_cpu':
            # Reduce performance level
            self._apply_performance_profile(PerformanceLevel.LOW)
    
    def start(self) -> None:
        """Start performance optimization."""
        self.monitor.start_monitoring()
        self.memory_manager.start()
        self.cache_manager.start()
    
    def stop(self) -> None:
        """Stop performance optimization."""
        self.monitor.stop_monitoring()
        self.memory_manager.stop()
        self.cache_manager.stop()
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        return self.monitor.get_current_metrics()
    
    def get_optimization_recommendations(self) -> List[Dict[str, Any]]:
        """Get performance optimization recommendations."""
        return self.monitor.get_optimization_recommendations()
    
    def apply_optimization(self, optimization_type: str, parameters: Dict[str, Any]) -> bool:
        """Apply performance optimization."""
        return self.monitor.apply_optimization(optimization_type, parameters)
    
    def update_config(self, config: PerformanceConfig) -> None:
        """Update performance configuration."""
        self.config = config
        self.monitor.update_config(config)
        self.memory_manager.update_config(config)
        self.cache_manager.update_config(config)
        self._apply_initial_configuration()
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.monitor.cleanup()
        self.memory_manager.cleanup()
        self.cache_manager.cleanup()