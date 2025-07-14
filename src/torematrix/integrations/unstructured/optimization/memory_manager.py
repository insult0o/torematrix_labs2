"""
Memory management for document processing operations.
"""

import gc
import time
import threading
from enum import Enum
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass


class MemoryPriority(Enum):
    """Priority levels for memory allocation."""
    LOW = "low"
    NORMAL = "normal" 
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MemoryStats:
    """Memory usage statistics."""
    total_system_mb: float
    available_mb: float
    process_mb: float
    pressure_level: float  # 0.0 to 1.0
    last_updated: float


class MemoryManager:
    """Memory management with monitoring and limits."""
    
    def __init__(self, 
                 limit_mb: int = 2048,
                 warning_threshold: float = 0.8,
                 pressure_threshold: float = 0.9):
        self.limit_mb = limit_mb
        self.warning_threshold = warning_threshold
        self.pressure_threshold = pressure_threshold
        
        self._lock = threading.RLock()
        self._callbacks: Dict[str, Callable] = {}
        self._last_stats = MemoryStats(0, 0, 0, 0, 0)
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        
        # Start monitoring
        self.start_monitoring()
    
    def start_monitoring(self) -> None:
        """Start memory monitoring thread."""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="MemoryMonitor"
        )
        self._monitor_thread.start()
    
    def stop_monitoring(self) -> None:
        """Stop memory monitoring."""
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._monitoring:
            try:
                self._update_stats()
                self._check_thresholds()
                time.sleep(1.0)  # Check every second
            except Exception:
                pass  # Continue monitoring even if updates fail
    
    def _update_stats(self) -> None:
        """Update memory statistics."""
        try:
            import psutil
            
            # System memory
            system_memory = psutil.virtual_memory()
            total_mb = system_memory.total / (1024 * 1024)
            available_mb = system_memory.available / (1024 * 1024)
            
            # Process memory
            process = psutil.Process()
            process_mb = process.memory_info().rss / (1024 * 1024)
            
            # Calculate pressure level
            pressure = 1.0 - (available_mb / total_mb)
            pressure = max(0.0, min(1.0, pressure))
            
            with self._lock:
                self._last_stats = MemoryStats(
                    total_system_mb=total_mb,
                    available_mb=available_mb,
                    process_mb=process_mb,
                    pressure_level=pressure,
                    last_updated=time.time()
                )
        
        except ImportError:
            # Fallback without psutil
            with self._lock:
                self._last_stats = MemoryStats(
                    total_system_mb=8192.0,  # Assume 8GB
                    available_mb=4096.0,     # Assume 4GB available
                    process_mb=512.0,        # Assume 512MB process
                    pressure_level=0.5,      # Moderate pressure
                    last_updated=time.time()
                )
    
    def _check_thresholds(self) -> None:
        """Check memory thresholds and trigger callbacks."""
        stats = self.get_memory_stats()
        
        # Check process memory limit
        if stats.process_mb > self.limit_mb:
            self._trigger_callback("limit_exceeded", stats)
        
        # Check warning threshold
        elif stats.pressure_level > self.warning_threshold:
            self._trigger_callback("warning", stats)
        
        # Check pressure threshold
        elif stats.pressure_level > self.pressure_threshold:
            self._trigger_callback("pressure", stats)
    
    def _trigger_callback(self, event_type: str, stats: MemoryStats) -> None:
        """Trigger registered callbacks for memory events."""
        callback = self._callbacks.get(event_type)
        if callback:
            try:
                callback(stats)
            except Exception:
                pass  # Don't let callback errors stop monitoring
    
    def register_callback(self, event_type: str, callback: Callable[[MemoryStats], None]) -> None:
        """Register callback for memory events."""
        with self._lock:
            self._callbacks[event_type] = callback
    
    def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        with self._lock:
            return self._last_stats
    
    def check_can_allocate(self, estimated_mb: float, priority: MemoryPriority = MemoryPriority.NORMAL) -> bool:
        """Check if we can safely allocate the requested memory."""
        stats = self.get_memory_stats()
        
        # Check against our process limit
        projected_usage = stats.process_mb + estimated_mb
        if projected_usage > self.limit_mb:
            return priority == MemoryPriority.CRITICAL
        
        # Check system pressure
        if stats.pressure_level > self.pressure_threshold:
            return priority in [MemoryPriority.HIGH, MemoryPriority.CRITICAL]
        
        if stats.pressure_level > self.warning_threshold:
            return priority != MemoryPriority.LOW
        
        return True
    
    def suggest_memory_cleanup(self) -> Dict[str, Any]:
        """Suggest memory cleanup actions."""
        stats = self.get_memory_stats()
        suggestions = []
        
        if stats.pressure_level > self.pressure_threshold:
            suggestions.extend([
                "Force garbage collection",
                "Clear document caches",
                "Reduce concurrent operations",
                "Switch to low-memory processing mode"
            ])
        elif stats.pressure_level > self.warning_threshold:
            suggestions.extend([
                "Run garbage collection",
                "Clear old cache entries"
            ])
        
        return {
            "memory_stats": stats,
            "suggestions": suggestions,
            "severity": "critical" if stats.pressure_level > self.pressure_threshold else
                       "warning" if stats.pressure_level > self.warning_threshold else "normal"
        }
    
    def force_cleanup(self) -> Dict[str, Any]:
        """Force memory cleanup operations."""
        initial_stats = self.get_memory_stats()
        
        # Force garbage collection
        gc.collect()
        
        # Additional cleanup can be added here
        # - Clear caches
        # - Release temporary resources
        
        # Wait a moment for cleanup to take effect
        time.sleep(0.1)
        
        final_stats = self.get_memory_stats()
        
        return {
            "initial_memory_mb": initial_stats.process_mb,
            "final_memory_mb": final_stats.process_mb,
            "freed_mb": initial_stats.process_mb - final_stats.process_mb,
            "gc_collections": sum(gc.get_stats())
        }
    
    def shutdown(self) -> None:
        """Shutdown memory manager."""
        self.stop_monitoring()
        with self._lock:
            self._callbacks.clear()