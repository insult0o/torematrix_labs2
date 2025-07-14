"""
Lifecycle management for ReactiveWidget components.

This module provides lifecycle management utilities including mount/unmount hooks,
update cycles, render optimization, and cleanup mechanisms.
"""

from __future__ import annotations

import asyncio
import logging
import time
import weakref
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    TYPE_CHECKING,
)

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

if TYPE_CHECKING:
    from torematrix.ui.components.reactive import ReactiveWidget

logger = logging.getLogger(__name__)


class LifecyclePhase(Enum):
    """Component lifecycle phases."""
    
    UNMOUNTED = auto()
    MOUNTING = auto()
    MOUNTED = auto()
    UPDATING = auto()
    UNMOUNTING = auto()
    ERROR = auto()


@dataclass
class LifecycleEvent:
    """Represents a lifecycle event."""
    
    phase: LifecyclePhase
    component_id: str
    component_type: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RenderMetrics:
    """Metrics for component rendering."""
    
    render_count: int = 0
    total_render_time: float = 0.0
    last_render_time: float = 0.0
    average_render_time: float = 0.0
    slowest_render_time: float = 0.0
    fastest_render_time: float = float("inf")


class LifecycleManager(QObject):
    """
    Manages component lifecycle for ReactiveWidget instances.
    
    Features:
    - Lifecycle phase tracking
    - Mount/unmount orchestration
    - Update cycle management
    - Performance monitoring
    - Memory leak prevention
    - Error boundary support
    """
    
    # Signals
    lifecycle_event = pyqtSignal(LifecycleEvent)
    error_occurred = pyqtSignal(str, Exception)  # component_id, error
    
    def __init__(self):
        """Initialize lifecycle manager."""
        super().__init__()
        
        # Component tracking
        self._components: Dict[str, weakref.ref[ReactiveWidget]] = {}
        self._component_phases: Dict[str, LifecyclePhase] = {}
        self._component_metrics: Dict[str, RenderMetrics] = {}
        
        # Update management
        self._update_queue: Set[str] = set()
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._process_update_queue)
        self._update_timer.setSingleShot(True)
        self._update_batch_size = 10
        self._update_delay_ms = 16  # ~60fps
        
        # Lifecycle hooks
        self._global_hooks: Dict[LifecyclePhase, List[Callable]] = {
            phase: [] for phase in LifecyclePhase
        }
        
        # Error handling
        self._error_handlers: List[Callable[[str, Exception], None]] = []
        
        # Performance monitoring
        self._performance_enabled = True
        self._slow_render_threshold_ms = 50.0
    
    def register_component(self, component: ReactiveWidget) -> None:
        """
        Register a component with the lifecycle manager.
        
        Args:
            component: Component to register
        """
        component_id = component.component_id
        self._components[component_id] = weakref.ref(component)
        self._component_phases[component_id] = LifecyclePhase.UNMOUNTED
        self._component_metrics[component_id] = RenderMetrics()
        
        logger.debug(f"Registered component {component_id} ({component.__class__.__name__})")
    
    def unregister_component(self, component_id: str) -> None:
        """
        Unregister a component from the lifecycle manager.
        
        Args:
            component_id: ID of component to unregister
        """
        self._components.pop(component_id, None)
        self._component_phases.pop(component_id, None)
        self._component_metrics.pop(component_id, None)
        self._update_queue.discard(component_id)
        
        logger.debug(f"Unregistered component {component_id}")
    
    def mount_component(self, component: ReactiveWidget) -> None:
        """
        Mount a component and its children.
        
        Args:
            component: Component to mount
        """
        component_id = component.component_id
        
        if component_id not in self._components:
            self.register_component(component)
        
        current_phase = self._component_phases.get(component_id, LifecyclePhase.UNMOUNTED)
        
        if current_phase != LifecyclePhase.UNMOUNTED:
            logger.warning(f"Component {component_id} already mounted or mounting")
            return
        
        try:
            # Update phase
            self._set_phase(component_id, LifecyclePhase.MOUNTING)
            
            # Pre-mount hooks
            self._call_global_hooks(LifecyclePhase.MOUNTING, component)
            
            # Mount component
            with self._performance_monitor(component_id, "mount"):
                component.mount()
            
            # Update phase
            self._set_phase(component_id, LifecyclePhase.MOUNTED)
            
            # Post-mount hooks
            self._call_global_hooks(LifecyclePhase.MOUNTED, component)
            
            logger.info(f"Mounted component {component_id}")
            
        except Exception as e:
            self._handle_error(component_id, e, LifecyclePhase.MOUNTING)
            raise
    
    def unmount_component(self, component: ReactiveWidget) -> None:
        """
        Unmount a component and its children.
        
        Args:
            component: Component to unmount
        """
        component_id = component.component_id
        current_phase = self._component_phases.get(component_id, LifecyclePhase.UNMOUNTED)
        
        if current_phase == LifecyclePhase.UNMOUNTED:
            logger.warning(f"Component {component_id} already unmounted")
            return
        
        try:
            # Update phase
            self._set_phase(component_id, LifecyclePhase.UNMOUNTING)
            
            # Pre-unmount hooks
            self._call_global_hooks(LifecyclePhase.UNMOUNTING, component)
            
            # Unmount component
            with self._performance_monitor(component_id, "unmount"):
                component.unmount()
            
            # Update phase
            self._set_phase(component_id, LifecyclePhase.UNMOUNTED)
            
            # Cleanup
            self.unregister_component(component_id)
            
            logger.info(f"Unmounted component {component_id}")
            
        except Exception as e:
            self._handle_error(component_id, e, LifecyclePhase.UNMOUNTING)
            raise
    
    def schedule_update(self, component_id: str) -> None:
        """
        Schedule a component update.
        
        Args:
            component_id: ID of component to update
        """
        if component_id not in self._components:
            logger.warning(f"Unknown component {component_id}")
            return
        
        current_phase = self._component_phases.get(component_id)
        
        if current_phase != LifecyclePhase.MOUNTED:
            logger.debug(f"Skipping update for component {component_id} in phase {current_phase}")
            return
        
        # Add to update queue
        self._update_queue.add(component_id)
        
        # Start update timer if not running
        if not self._update_timer.isActive():
            self._update_timer.start(self._update_delay_ms)
    
    def force_update(self, component_id: str) -> None:
        """
        Force immediate update of a component.
        
        Args:
            component_id: ID of component to update
        """
        component_ref = self._components.get(component_id)
        if not component_ref:
            return
        
        component = component_ref()
        if not component:
            self.unregister_component(component_id)
            return
        
        self._update_component(component)
    
    def add_global_hook(
        self,
        phase: LifecyclePhase,
        hook: Callable[[ReactiveWidget], None]
    ) -> None:
        """
        Add a global lifecycle hook.
        
        Args:
            phase: Lifecycle phase to hook into
            hook: Hook function to call
        """
        self._global_hooks[phase].append(hook)
    
    def remove_global_hook(
        self,
        phase: LifecyclePhase,
        hook: Callable[[ReactiveWidget], None]
    ) -> None:
        """
        Remove a global lifecycle hook.
        
        Args:
            phase: Lifecycle phase
            hook: Hook function to remove
        """
        if hook in self._global_hooks[phase]:
            self._global_hooks[phase].remove(hook)
    
    def add_error_handler(
        self,
        handler: Callable[[str, Exception], None]
    ) -> None:
        """
        Add an error handler.
        
        Args:
            handler: Error handler function
        """
        self._error_handlers.append(handler)
    
    def get_component_phase(self, component_id: str) -> Optional[LifecyclePhase]:
        """
        Get current lifecycle phase of a component.
        
        Args:
            component_id: Component ID
            
        Returns:
            Current lifecycle phase or None
        """
        return self._component_phases.get(component_id)
    
    def get_component_metrics(self, component_id: str) -> Optional[RenderMetrics]:
        """
        Get render metrics for a component.
        
        Args:
            component_id: Component ID
            
        Returns:
            Render metrics or None
        """
        return self._component_metrics.get(component_id)
    
    def get_all_metrics(self) -> Dict[str, RenderMetrics]:
        """Get metrics for all components."""
        return self._component_metrics.copy()
    
    def enable_performance_monitoring(self, enabled: bool = True) -> None:
        """Enable or disable performance monitoring."""
        self._performance_enabled = enabled
    
    def set_slow_render_threshold(self, threshold_ms: float) -> None:
        """Set threshold for slow render warnings."""
        self._slow_render_threshold_ms = threshold_ms
    
    # Private methods
    
    def _set_phase(self, component_id: str, phase: LifecyclePhase) -> None:
        """Set component lifecycle phase."""
        self._component_phases[component_id] = phase
        
        # Get component info
        component_ref = self._components.get(component_id)
        component_type = "Unknown"
        
        if component_ref:
            component = component_ref()
            if component:
                component_type = component.__class__.__name__
        
        # Emit event
        event = LifecycleEvent(
            phase=phase,
            component_id=component_id,
            component_type=component_type
        )
        self.lifecycle_event.emit(event)
    
    def _process_update_queue(self) -> None:
        """Process queued component updates."""
        if not self._update_queue:
            return
        
        # Process batch of updates
        batch = list(self._update_queue)[:self._update_batch_size]
        self._update_queue -= set(batch)
        
        for component_id in batch:
            component_ref = self._components.get(component_id)
            if not component_ref:
                continue
            
            component = component_ref()
            if not component:
                self.unregister_component(component_id)
                continue
            
            self._update_component(component)
        
        # Continue processing if more updates queued
        if self._update_queue:
            self._update_timer.start(self._update_delay_ms)
    
    def _update_component(self, component: ReactiveWidget) -> None:
        """Update a single component."""
        component_id = component.component_id
        
        try:
            # Update phase
            self._set_phase(component_id, LifecyclePhase.UPDATING)
            
            # Perform update with monitoring
            with self._performance_monitor(component_id, "update"):
                component.force_update()
            
            # Restore phase
            self._set_phase(component_id, LifecyclePhase.MOUNTED)
            
        except Exception as e:
            self._handle_error(component_id, e, LifecyclePhase.UPDATING)
    
    def _call_global_hooks(
        self,
        phase: LifecyclePhase,
        component: ReactiveWidget
    ) -> None:
        """Call global lifecycle hooks."""
        for hook in self._global_hooks[phase]:
            try:
                hook(component)
            except Exception as e:
                logger.error(f"Error in global hook for {phase}: {e}")
    
    def _handle_error(
        self,
        component_id: str,
        error: Exception,
        phase: LifecyclePhase
    ) -> None:
        """Handle component error."""
        # Update phase
        self._set_phase(component_id, LifecyclePhase.ERROR)
        
        # Log error
        logger.error(f"Component {component_id} error in {phase}: {error}", exc_info=True)
        
        # Emit signal
        self.error_occurred.emit(component_id, error)
        
        # Call handlers
        for handler in self._error_handlers:
            try:
                handler(component_id, error)
            except Exception as e:
                logger.error(f"Error in error handler: {e}")
    
    @contextmanager
    def _performance_monitor(self, component_id: str, operation: str):
        """Monitor performance of an operation."""
        if not self._performance_enabled:
            yield
            return
        
        start_time = time.time()
        
        try:
            yield
        finally:
            end_time = time.time()
            elapsed_ms = (end_time - start_time) * 1000
            
            # Update metrics if render operation
            if operation == "update":
                metrics = self._component_metrics.get(component_id)
                if metrics:
                    metrics.render_count += 1
                    metrics.last_render_time = elapsed_ms
                    metrics.total_render_time += elapsed_ms
                    metrics.average_render_time = (
                        metrics.total_render_time / metrics.render_count
                    )
                    metrics.slowest_render_time = max(
                        metrics.slowest_render_time,
                        elapsed_ms
                    )
                    metrics.fastest_render_time = min(
                        metrics.fastest_render_time,
                        elapsed_ms
                    )
            
            # Warn if slow
            if elapsed_ms > self._slow_render_threshold_ms:
                logger.warning(
                    f"Slow {operation} for component {component_id}: "
                    f"{elapsed_ms:.2f}ms"
                )


# Global lifecycle manager instance
_lifecycle_manager: Optional[LifecycleManager] = None


def get_lifecycle_manager() -> LifecycleManager:
    """Get or create the global lifecycle manager."""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = LifecycleManager()
    return _lifecycle_manager


def with_lifecycle(
    component_class: type[ReactiveWidget]
) -> type[ReactiveWidget]:
    """
    Class decorator to automatically register component with lifecycle manager.
    
    Args:
        component_class: Component class to decorate
        
    Returns:
        Decorated component class
    """
    original_init = component_class.__init__
    
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        get_lifecycle_manager().register_component(self)
    
    component_class.__init__ = new_init
    return component_class


class LifecycleMixin:
    """
    Mixin to add lifecycle management to any widget.
    
    This can be used with non-ReactiveWidget classes to add
    lifecycle tracking capabilities.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize lifecycle mixin."""
        super().__init__(*args, **kwargs)
        
        # Generate component ID if not present
        if not hasattr(self, "_component_id"):
            from uuid import uuid4
            self._component_id = str(uuid4())
        
        # Register with lifecycle manager
        get_lifecycle_manager().register_component(self)
    
    @property
    def component_id(self) -> str:
        """Get component ID."""
        return self._component_id
    
    def mount(self) -> None:
        """Mount component."""
        get_lifecycle_manager().mount_component(self)
    
    def unmount(self) -> None:
        """Unmount component."""
        get_lifecycle_manager().unmount_component(self)
    
    def schedule_update(self) -> None:
        """Schedule component update."""
        get_lifecycle_manager().schedule_update(self.component_id)
    
    def force_update(self) -> None:
        """Force immediate update."""
        get_lifecycle_manager().force_update(self.component_id)