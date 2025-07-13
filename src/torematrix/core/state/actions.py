"""
Action system for state management.

This module provides type-safe action definitions, action creators,
and action validation for the state management system.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Type, TypeVar, Generic, Union
from datetime import datetime
import uuid


class ActionType(Enum):
    """Standard action types for the state management system."""
    
    # System actions
    INIT = "@@STATE/INIT"
    RESET = "@@STATE/RESET"
    HYDRATE = "@@STATE/HYDRATE"
    
    # Document actions
    SET_DOCUMENT = "DOCUMENT/SET"
    UPDATE_DOCUMENT = "DOCUMENT/UPDATE"
    CLOSE_DOCUMENT = "DOCUMENT/CLOSE"
    
    # Element actions
    ADD_ELEMENT = "ELEMENT/ADD"
    UPDATE_ELEMENT = "ELEMENT/UPDATE"
    DELETE_ELEMENT = "ELEMENT/DELETE"
    SELECT_ELEMENT = "ELEMENT/SELECT"
    
    # UI actions
    SET_PAGE = "UI/SET_PAGE"
    SET_ZOOM = "UI/SET_ZOOM"
    SET_VIEW_MODE = "UI/SET_VIEW_MODE"
    TOGGLE_SIDEBAR = "UI/TOGGLE_SIDEBAR"
    
    # Validation actions
    START_VALIDATION = "VALIDATION/START"
    UPDATE_VALIDATION = "VALIDATION/UPDATE"
    COMPLETE_VALIDATION = "VALIDATION/COMPLETE"
    
    # Async actions
    ASYNC_START = "ASYNC/START"
    ASYNC_SUCCESS = "ASYNC/SUCCESS"
    ASYNC_FAILURE = "ASYNC/FAILURE"


T = TypeVar('T')


@dataclass
class Action(Generic[T]):
    """
    Base action class with type safety.
    
    Attributes:
        type: The action type
        payload: The action payload (type-safe with generics)
        meta: Optional metadata
        error: Whether this is an error action
        timestamp: When the action was created
        id: Unique action identifier
    """
    type: Union[ActionType, str]
    payload: Optional[T] = None
    meta: Optional[Dict[str, Any]] = None
    error: bool = False
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def with_meta(self, **kwargs) -> 'Action[T]':
        """Add metadata to action."""
        self.meta = self.meta or {}
        self.meta.update(kwargs)
        return self
    
    def as_error(self, error_message: str = None) -> 'Action[T]':
        """Mark action as error."""
        self.error = True
        if error_message:
            self.with_meta(error_message=error_message)
        return self


# Action creator functions
def create_action(action_type: Union[ActionType, str], payload: Any = None) -> Action:
    """Create a generic action."""
    return Action(type=action_type, payload=payload)


def init_store() -> Action[None]:
    """Create store initialization action."""
    return Action(type=ActionType.INIT)


def reset_store() -> Action[None]:
    """Create store reset action."""
    return Action(type=ActionType.RESET)


def hydrate_store(state: Dict[str, Any]) -> Action[Dict[str, Any]]:
    """Create store hydration action."""
    return Action(type=ActionType.HYDRATE, payload=state)


# Document actions
@dataclass
class DocumentPayload:
    """Payload for document actions."""
    document_id: str
    document_path: Optional[str] = None
    document_data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


def set_document(document_id: str, document_path: str = None, 
                 document_data: Dict[str, Any] = None) -> Action[DocumentPayload]:
    """Create set document action."""
    return Action(
        type=ActionType.SET_DOCUMENT,
        payload=DocumentPayload(
            document_id=document_id,
            document_path=document_path,
            document_data=document_data
        )
    )


# Element actions
@dataclass
class ElementPayload:
    """Payload for element actions."""
    element_id: str
    element_type: Optional[str] = None
    element_data: Optional[Dict[str, Any]] = None
    page_number: Optional[int] = None


def add_element(element_id: str, element_type: str, 
                element_data: Dict[str, Any], page_number: int = None) -> Action[ElementPayload]:
    """Create add element action."""
    return Action(
        type=ActionType.ADD_ELEMENT,
        payload=ElementPayload(
            element_id=element_id,
            element_type=element_type,
            element_data=element_data,
            page_number=page_number
        )
    )


def update_element(element_id: str, element_data: Dict[str, Any]) -> Action[ElementPayload]:
    """Create update element action."""
    return Action(
        type=ActionType.UPDATE_ELEMENT,
        payload=ElementPayload(
            element_id=element_id,
            element_data=element_data
        )
    )


def delete_element(element_id: str) -> Action[ElementPayload]:
    """Create delete element action."""
    return Action(
        type=ActionType.DELETE_ELEMENT,
        payload=ElementPayload(element_id=element_id)
    )


# Async action creators
@dataclass
class AsyncPayload:
    """Payload for async actions."""
    request_id: str
    operation: str
    data: Optional[Any] = None
    error: Optional[Exception] = None


def async_start(request_id: str, operation: str, data: Any = None) -> Action[AsyncPayload]:
    """Create async start action."""
    return Action(
        type=ActionType.ASYNC_START,
        payload=AsyncPayload(
            request_id=request_id,
            operation=operation,
            data=data
        )
    )


def async_success(request_id: str, operation: str, data: Any) -> Action[AsyncPayload]:
    """Create async success action."""
    return Action(
        type=ActionType.ASYNC_SUCCESS,
        payload=AsyncPayload(
            request_id=request_id,
            operation=operation,
            data=data
        )
    )


def async_failure(request_id: str, operation: str, error: Exception) -> Action[AsyncPayload]:
    """Create async failure action."""
    return Action(
        type=ActionType.ASYNC_FAILURE,
        payload=AsyncPayload(
            request_id=request_id,
            operation=operation,
            error=error
        )
    ).as_error(str(error))


# Action validation
class ActionValidator:
    """Validates actions before processing."""
    
    @staticmethod
    def validate(action: Action) -> bool:
        """
        Validate an action.
        
        Args:
            action: Action to validate
            
        Returns:
            True if valid, raises ValueError if invalid
        """
        if not action.type:
            raise ValueError("Action must have a type")
        
        if action.timestamp <= 0:
            raise ValueError("Action must have valid timestamp")
        
        if not action.id:
            raise ValueError("Action must have an ID")
        
        return True
    
    @staticmethod
    def is_async_action(action: Action) -> bool:
        """Check if action is async-related."""
        return isinstance(action.type, ActionType) and action.type.value.startswith("ASYNC/")
    
    @staticmethod
    def is_system_action(action: Action) -> bool:
        """Check if action is system-related."""
        return isinstance(action.type, ActionType) and action.type.value.startswith("@@")