"""
Reactive UI Components for TORE Matrix Labs V3.

This package provides reactive UI components with automatic state subscription,
efficient re-rendering, and comprehensive lifecycle management.

Key Features:
- ReactiveWidget base class for all reactive components
- Automatic state subscription and synchronization
- Property binding decorators for declarative syntax
- Lifecycle management with mount/unmount/update hooks
- Performance optimization with batched updates
- Memory-safe cleanup mechanisms
- Component composition patterns

Example Usage:
    from torematrix.ui.components import ReactiveWidget, bind_state, computed

    class DocumentTitle(ReactiveWidget):
        @bind_state("document.title", bidirectional=True)
        def title(self) -> str:
            pass
        
        @computed("document.metadata.author", "document.metadata.date")
        def subtitle(self, author: str, date: str) -> str:
            return f"By {author} - {date}"
"""

from torematrix.ui.components.decorators import (
    bind_state,
    computed,
    debounce,
    lifecycle,
    memoize,
    reactive_property,
    throttle,
    watch,
)
from torematrix.ui.components.lifecycle import (
    LifecycleManager,
    LifecycleMixin,
    LifecyclePhase,
    RenderMetrics,
    get_lifecycle_manager,
    with_lifecycle,
)
from torematrix.ui.components.reactive import (
    ReactiveMetaclass,
    ReactiveProperty,
    ReactiveWidget,
    StateBinding,
)

__all__ = [
    # Core classes
    "ReactiveWidget",
    "ReactiveMetaclass",
    "ReactiveProperty",
    "StateBinding",
    # Decorators
    "reactive_property",
    "bind_state",
    "computed",
    "watch",
    "lifecycle",
    "throttle",
    "debounce",
    "memoize",
    # Lifecycle management
    "LifecycleManager",
    "LifecycleMixin",
    "LifecyclePhase",
    "RenderMetrics",
    "get_lifecycle_manager",
    "with_lifecycle",
]

# Package metadata
__version__ = "1.0.0"
__author__ = "TORE Matrix Labs"
__license__ = "MIT"