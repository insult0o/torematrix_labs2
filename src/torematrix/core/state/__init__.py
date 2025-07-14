"""
State management system for TORE Matrix Labs V3.

This package provides a Redux-like state management system with:
- Centralized state store
- Type-safe actions
- Pure reducer functions
- Middleware support
- Thread-safe operations
"""

from .store import Store
from .types import StoreConfig, State, StateChange
from .actions import (
    Action, ActionType, ActionValidator,
    create_action, init_store, reset_store, hydrate_store,
    set_document, add_element, update_element, delete_element,
    async_start, async_success, async_failure
)
from .reducers import (
    create_root_reducer, combine_reducers,
    document_reducer, elements_reducer, ui_reducer, async_reducer
)
from .middleware.logging import LoggingMiddleware
from .middleware.base import Middleware, compose_middleware

__all__ = [
    # Store
    'Store',
    'StoreConfig',
    'State',
    'StateChange',
    
    # Actions
    'Action',
    'ActionType',
    'ActionValidator',
    'create_action',
    'init_store',
    'reset_store',
    'hydrate_store',
    'set_document',
    'add_element',
    'update_element',
    'delete_element',
    'async_start',
    'async_success',
    'async_failure',
    
    # Reducers
    'create_root_reducer',
    'combine_reducers',
    'document_reducer',
    'elements_reducer',
    'ui_reducer',
    'async_reducer',
    
    # Middleware
    'Middleware',
    'compose_middleware',
    'LoggingMiddleware',
]