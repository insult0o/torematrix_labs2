"""
Cleanup Strategies for Reactive Components.

This module provides comprehensive cleanup mechanisms for reactive components,
ensuring proper resource deallocation and preventing memory leaks.
"""

import weakref
import threading
import asyncio
from typing import Any, Callable, Dict, List, Optional, Protocol, Set, Union
from dataclasses import dataclass, field
from enum import Enum, auto
from contextlib import contextmanager, ExitStack
import logging
from functools import wraps
import traceback
import atexit

logger = logging.getLogger(__name__)


class CleanupPhase(Enum):
    """Cleanup phases for proper teardown order."""
    
    SUBSCRIPTIONS = auto()  # Clean up state subscriptions first
    EVENTS = auto()        # Then event listeners
    TIMERS = auto()        # Cancel timers and scheduled tasks
    ASYNC_TASKS = auto()   # Cancel async operations
    RESOURCES = auto()     # Release external resources
    MEMORY = auto()        # Final memory cleanup


@dataclass
class CleanupTask:
    """Represents a cleanup task to be executed."""
    
    phase: CleanupPhase
    callback: Callable[[], None]
    name: str
    priority: int = 0  # Higher priority runs first within phase
    error_handler: Optional[Callable[[Exception], None]] = None
    
    def __lt__(self, other):
        """Compare for sorting by phase and priority."""
        if self.phase.value != other.phase.value:
            return self.phase.value < other.phase.value
        return self.priority > other.priority


class CleanupProtocol(Protocol):
    """Protocol for objects that support cleanup."""
    
    def cleanup(self) -> None:
        """Perform cleanup operations."""
        ...


class CleanupRegistry:
    """Global registry for cleanup operations."""
    
    def __init__(self):
        """Initialize the registry."""
        self._tasks: Dict[int, List[CleanupTask]] = {}
        self._lock = threading.RLock()
        self._cleaned_up: Set[int] = set()
        self._exit_handlers_registered = False
        self._register_exit_handlers()
        
    def register(
        self,
        obj: Any,
        callback: Callable[[], None],
        phase: CleanupPhase,
        name: Optional[str] = None,
        priority: int = 0,
        error_handler: Optional[Callable[[Exception], None]] = None
    ) -> None:
        """
        Register a cleanup task for an object.
        
        Args:
            obj: Object to clean up
            callback: Cleanup callback function
            phase: Cleanup phase
            name: Optional task name for debugging
            priority: Priority within phase (higher runs first)
            error_handler: Optional error handler
        """
        with self._lock:
            obj_id = id(obj)
            
            if obj_id not in self._tasks:
                self._tasks[obj_id] = []
                
                # Create weak reference with cleanup
                def on_gc(ref):
                    self.cleanup_object(obj_id)
                
                weakref.ref(obj, on_gc)
            
            # Get callback name safely
            callback_name = getattr(callback, '__name__', 'callback')
            
            task = CleanupTask(
                phase=phase,
                callback=callback,
                name=name or f"{obj.__class__.__name__}.{callback_name}",
                priority=priority,
                error_handler=error_handler
            )
            
            self._tasks[obj_id].append(task)
    
    def cleanup_object(self, obj_or_id: Union[Any, int]) -> None:
        """Execute all cleanup tasks for an object."""
        with self._lock:
            if isinstance(obj_or_id, int):
                obj_id = obj_or_id
            else:
                obj_id = id(obj_or_id)
            
            # Check if already cleaned up
            if obj_id in self._cleaned_up:
                return
            
            self._cleaned_up.add(obj_id)
            
            # Get tasks
            tasks = self._tasks.pop(obj_id, [])
            if not tasks:
                return
            
            # Sort tasks by phase and priority
            tasks.sort()
        
        # Execute tasks outside lock
        for task in tasks:
            try:
                logger.debug(f"Executing cleanup: {task.name}")
                task.callback()
            except Exception as e:
                logger.error(f"Error in cleanup task {task.name}: {e}")
                logger.debug(traceback.format_exc())
                
                if task.error_handler:
                    try:
                        task.error_handler(e)
                    except Exception as handler_error:
                        logger.error(f"Error in error handler: {handler_error}")
    
    def cleanup_all(self) -> None:
        """Clean up all registered objects."""
        with self._lock:
            obj_ids = list(self._tasks.keys())
        
        for obj_id in obj_ids:
            self.cleanup_object(obj_id)
    
    def _register_exit_handlers(self) -> None:
        """Register exit handlers for final cleanup."""
        if not self._exit_handlers_registered:
            atexit.register(self.cleanup_all)
            self._exit_handlers_registered = True


# Global cleanup registry
_cleanup_registry = CleanupRegistry()


def get_cleanup_registry() -> CleanupRegistry:
    """Get the global cleanup registry."""
    return _cleanup_registry


class CleanupManager:
    """Manages cleanup operations for a component."""
    
    def __init__(self, component: Any):
        """Initialize cleanup manager for a component."""
        self.component = component
        self.component_id = id(component)
        self.registry = get_cleanup_registry()
        self._cleanup_stack = ExitStack()
        self._async_tasks: Set[asyncio.Task] = set()
        self._timers: List[threading.Timer] = []
        self._resources: List[Any] = []
        self._is_cleaned_up = False
        self._lock = threading.Lock()
        
    def register_cleanup(
        self,
        callback: Callable[[], None],
        phase: CleanupPhase = CleanupPhase.RESOURCES,
        name: Optional[str] = None,
        priority: int = 0
    ) -> None:
        """Register a cleanup callback."""
        self.registry.register(
            obj=self.component,
            callback=callback,
            phase=phase,
            name=name,
            priority=priority
        )
    
    def add_subscription_cleanup(self, cleanup_func: Callable[[], None]) -> None:
        """Add cleanup for state subscriptions."""
        self.register_cleanup(
            cleanup_func,
            CleanupPhase.SUBSCRIPTIONS,
            "subscription_cleanup",
            priority=100
        )
    
    def add_event_cleanup(self, cleanup_func: Callable[[], None]) -> None:
        """Add cleanup for event listeners."""
        self.register_cleanup(
            cleanup_func,
            CleanupPhase.EVENTS,
            "event_cleanup",
            priority=90
        )
    
    def add_timer(self, timer: threading.Timer) -> threading.Timer:
        """Add a timer that will be cancelled on cleanup."""
        with self._lock:
            self._timers.append(timer)
        return timer
    
    def add_async_task(self, task: asyncio.Task) -> asyncio.Task:
        """Add an async task that will be cancelled on cleanup."""
        with self._lock:
            self._async_tasks.add(task)
            task.add_done_callback(self._async_tasks.discard)
        return task
    
    def add_resource(self, resource: Any) -> Any:
        """Add a resource to be cleaned up."""
        with self._lock:
            self._resources.append(resource)
        return resource
    
    def add_context_manager(self, cm: Any) -> Any:
        """Add a context manager to the cleanup stack."""
        return self._cleanup_stack.enter_context(cm)
    
    def cleanup(self) -> None:
        """Perform all cleanup operations."""
        with self._lock:
            if self._is_cleaned_up:
                return
            self._is_cleaned_up = True
        
        # Cancel timers
        for timer in self._timers:
            timer.cancel()
        self._timers.clear()
        
        # Cancel async tasks
        for task in self._async_tasks:
            if not task.done():
                task.cancel()
        self._async_tasks.clear()
        
        # Clean up resources
        for resource in self._resources:
            if hasattr(resource, 'close'):
                try:
                    resource.close()
                except Exception as e:
                    logger.error(f"Error closing resource: {e}")
            elif hasattr(resource, 'cleanup'):
                try:
                    resource.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up resource: {e}")
        self._resources.clear()
        
        # Close context managers
        self._cleanup_stack.close()
        
        # Execute registered cleanup tasks
        self.registry.cleanup_object(self.component)
    
    def __enter__(self):
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and perform cleanup."""
        self.cleanup()
        return False


def with_cleanup(func: Callable) -> Callable:
    """
    Decorator that ensures cleanup on function exit.
    
    The decorated function should accept a CleanupManager as first argument after self.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract self if this is a method
        if args and hasattr(args[0], '__class__'):
            component = args[0]
            remaining_args = args[1:]
        else:
            component = None
            remaining_args = args
        
        with CleanupManager(component or func) as cleanup:
            # Insert cleanup manager as first argument after self
            if component:
                return func(component, cleanup, *remaining_args, **kwargs)
            else:
                return func(cleanup, *remaining_args, **kwargs)
    
    return wrapper


class CleanupMixin:
    """Mixin to add automatic cleanup capabilities to components."""
    
    def __init__(self, *args, **kwargs):
        """Initialize cleanup support."""
        super().__init__(*args, **kwargs)
        self._cleanup_manager = CleanupManager(self)
        self._cleanup_registered = False
        
    @property
    def cleanup_manager(self) -> CleanupManager:
        """Get the cleanup manager for this component."""
        return self._cleanup_manager
    
    def register_cleanup(
        self,
        callback: Callable[[], None],
        phase: CleanupPhase = CleanupPhase.RESOURCES,
        name: Optional[str] = None,
        priority: int = 0
    ) -> None:
        """Register a cleanup callback."""
        self._cleanup_manager.register_cleanup(callback, phase, name, priority)
    
    def cleanup(self) -> None:
        """Perform cleanup operations."""
        self._cleanup_manager.cleanup()
    
    def __del__(self):
        """Ensure cleanup on garbage collection."""
        try:
            self.cleanup()
        except Exception as e:
            logger.error(f"Error during __del__ cleanup: {e}")


class ResourceGuard:
    """
    Context manager that ensures resource cleanup even on errors.
    
    Example:
        with ResourceGuard() as guard:
            file = guard.add(open('file.txt'))
            connection = guard.add(create_connection())
            # Resources automatically cleaned up on exit
    """
    
    def __init__(self):
        """Initialize resource guard."""
        self._resources: List[Tuple[Any, Callable]] = []
        self._lock = threading.Lock()
        
    def add(self, resource: Any, cleanup: Optional[Callable] = None) -> Any:
        """
        Add a resource to guard.
        
        Args:
            resource: Resource to guard
            cleanup: Optional cleanup function (defaults to close())
            
        Returns:
            The resource for chaining
        """
        with self._lock:
            if cleanup is None:
                if hasattr(resource, 'close'):
                    cleanup = resource.close
                elif hasattr(resource, 'cleanup'):
                    cleanup = resource.cleanup
                else:
                    cleanup = lambda: None
            
            self._resources.append((resource, cleanup))
            return resource
    
    def cleanup(self) -> None:
        """Clean up all guarded resources."""
        with self._lock:
            resources = self._resources.copy()
            self._resources.clear()
        
        # Clean up in reverse order
        for resource, cleanup in reversed(resources):
            try:
                cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up resource {resource}: {e}")
    
    def __enter__(self):
        """Enter context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and clean up."""
        self.cleanup()
        return False


@contextmanager
def cleanup_on_error(cleanup_func: Callable[[], None]):
    """
    Context manager that runs cleanup only on error.
    
    Example:
        with cleanup_on_error(lambda: print("Cleaning up")):
            risky_operation()
    """
    try:
        yield
    except Exception:
        try:
            cleanup_func()
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}")
        raise