"""
Reducer implementation for state management.

This module provides pure reducer functions that handle state updates
in an immutable manner, following the Redux pattern.
"""

from typing import Dict, Any, Callable, TypeVar
from copy import deepcopy

from .actions import Action, ActionType
from .types import State, StateSlice, ReducerType


def combine_reducers(reducers: Dict[str, ReducerType]) -> ReducerType:
    """
    Combine multiple reducers into a single root reducer.
    
    Args:
        reducers: Dictionary mapping state keys to reducer functions
        
    Returns:
        A root reducer function
    """
    def root_reducer(state: State, action: Action) -> State:
        has_changed = False
        next_state = {}
        
        for key, reducer in reducers.items():
            previous_state_for_key = state.get(key, None)
            next_state_for_key = reducer(previous_state_for_key, action)
            
            next_state[key] = next_state_for_key
            has_changed = has_changed or (next_state_for_key != previous_state_for_key)
        
        # Always return next_state to ensure all reducers are initialized
        return next_state
    
    return root_reducer


# Document reducer
def document_reducer(state: StateSlice = None, action: Action = None) -> StateSlice:
    """
    Handle document-related state changes.
    
    State shape:
    {
        'current_id': str,
        'document_path': str,
        'document_data': dict,
        'is_modified': bool,
        'metadata': dict
    }
    """
    if state is None:
        state = {
            'current_id': None,
            'document_path': None,
            'document_data': None,
            'is_modified': False,
            'metadata': {}
        }
    
    if action is None:
        return state
    
    if action.type == ActionType.SET_DOCUMENT:
        payload = action.payload
        return {
            **state,
            'current_id': payload.document_id,
            'document_path': payload.document_path,
            'document_data': payload.document_data,
            'is_modified': False,
            'metadata': payload.metadata or {}
        }
    
    elif action.type == ActionType.UPDATE_DOCUMENT:
        if state['current_id'] == action.payload.document_id:
            return {
                **state,
                'document_data': {**state['document_data'], **action.payload.document_data},
                'is_modified': True
            }
    
    elif action.type == ActionType.CLOSE_DOCUMENT:
        return {
            'current_id': None,
            'document_path': None,
            'document_data': None,
            'is_modified': False,
            'metadata': {}
        }
    
    return state


# Elements reducer
def elements_reducer(state: StateSlice = None, action: Action = None) -> StateSlice:
    """
    Handle element-related state changes.
    
    State shape:
    {
        'byId': {element_id: element_data},
        'allIds': [element_id],
        'selectedIds': [element_id]
    }
    """
    if state is None:
        state = {
            'byId': {},
            'allIds': [],
            'selectedIds': []
        }
    
    if action is None:
        return state
    
    if action.type == ActionType.ADD_ELEMENT:
        payload = action.payload
        element_id = payload.element_id
        
        # Don't add if already exists
        if element_id in state['byId']:
            return state
        
        return {
            'byId': {
                **state['byId'],
                element_id: {
                    'id': element_id,
                    'type': payload.element_type,
                    'page_number': payload.page_number,
                    **payload.element_data
                }
            },
            'allIds': state['allIds'] + [element_id],
            'selectedIds': state['selectedIds']
        }
    
    elif action.type == ActionType.UPDATE_ELEMENT:
        payload = action.payload
        element_id = payload.element_id
        
        if element_id not in state['byId']:
            return state
        
        return {
            **state,
            'byId': {
                **state['byId'],
                element_id: {
                    **state['byId'][element_id],
                    **payload.element_data
                }
            }
        }
    
    elif action.type == ActionType.DELETE_ELEMENT:
        element_id = action.payload.element_id
        
        if element_id not in state['byId']:
            return state
        
        # Create new byId without the element
        new_by_id = {k: v for k, v in state['byId'].items() if k != element_id}
        
        return {
            'byId': new_by_id,
            'allIds': [id for id in state['allIds'] if id != element_id],
            'selectedIds': [id for id in state['selectedIds'] if id != element_id]
        }
    
    elif action.type == ActionType.SELECT_ELEMENT:
        element_id = action.payload.element_id
        
        if element_id not in state['byId']:
            return state
        
        return {
            **state,
            'selectedIds': [element_id]
        }
    
    return state


# UI reducer
def ui_reducer(state: StateSlice = None, action: Action = None) -> StateSlice:
    """
    Handle UI-related state changes.
    
    State shape:
    {
        'current_page': int,
        'zoom_level': float,
        'view_mode': str,
        'sidebar_visible': bool
    }
    """
    if state is None:
        state = {
            'current_page': 1,
            'zoom_level': 1.0,
            'view_mode': 'single',
            'sidebar_visible': True
        }
    
    if action is None:
        return state
    
    if action.type == ActionType.SET_PAGE:
        return {
            **state,
            'current_page': action.payload
        }
    
    elif action.type == ActionType.SET_ZOOM:
        return {
            **state,
            'zoom_level': max(0.1, min(5.0, action.payload))  # Clamp between 0.1 and 5.0
        }
    
    elif action.type == ActionType.SET_VIEW_MODE:
        if action.payload in ['single', 'continuous', 'two-page']:
            return {
                **state,
                'view_mode': action.payload
            }
    
    elif action.type == ActionType.TOGGLE_SIDEBAR:
        return {
            **state,
            'sidebar_visible': not state['sidebar_visible']
        }
    
    return state


# Async reducer for handling async operations
def async_reducer(state: StateSlice = None, action: Action = None) -> StateSlice:
    """
    Handle async operation state.
    
    State shape:
    {
        'pending': {request_id: {operation, started_at}},
        'errors': {request_id: {operation, error, timestamp}}
    }
    """
    if state is None:
        state = {
            'pending': {},
            'errors': {}
        }
    
    if action is None:
        return state
    
    if action.type == ActionType.ASYNC_START:
        payload = action.payload
        return {
            **state,
            'pending': {
                **state['pending'],
                payload.request_id: {
                    'operation': payload.operation,
                    'started_at': action.timestamp,
                    'data': payload.data
                }
            }
        }
    
    elif action.type == ActionType.ASYNC_SUCCESS:
        payload = action.payload
        # Remove from pending
        new_pending = {k: v for k, v in state['pending'].items() if k != payload.request_id}
        return {
            **state,
            'pending': new_pending
        }
    
    elif action.type == ActionType.ASYNC_FAILURE:
        payload = action.payload
        # Remove from pending and add to errors
        new_pending = {k: v for k, v in state['pending'].items() if k != payload.request_id}
        return {
            'pending': new_pending,
            'errors': {
                **state['errors'],
                payload.request_id: {
                    'operation': payload.operation,
                    'error': str(payload.error),
                    'timestamp': action.timestamp
                }
            }
        }
    
    return state


# Create root reducer
def create_root_reducer() -> ReducerType:
    """Create the root reducer for the application."""
    return combine_reducers({
        'document': document_reducer,
        'elements': elements_reducer,
        'ui': ui_reducer,
        'async': async_reducer
    })


# Utility function for immutable updates
def update_nested(obj: Dict[str, Any], path: str, value: Any) -> Dict[str, Any]:
    """
    Update a nested value in an object immutably.
    
    Args:
        obj: Object to update
        path: Dot-separated path to the value
        value: New value
        
    Returns:
        New object with updated value
    """
    keys = path.split('.')
    result = deepcopy(obj)
    
    current = result
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value
    return result