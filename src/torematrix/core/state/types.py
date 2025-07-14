"""
Type definitions for the state management system.

This module provides core types used throughout the state management system,
ensuring type safety and consistency across all components.
"""

from typing import TypeVar, Dict, Any, Callable, Optional, List, Union
from dataclasses import dataclass
from abc import ABC, abstractmethod

# Type variables
StateType = TypeVar('StateType', bound=Dict[str, Any])
ActionType = TypeVar('ActionType')
ReducerType = Callable[[StateType, ActionType], StateType]
MiddlewareType = Callable[['Store'], Callable[[Callable], Callable]]
SubscriberType = Callable[[StateType], None]
UnsubscribeType = Callable[[], None]

# State types
State = Dict[str, Any]
StateSlice = Dict[str, Any]


@dataclass
class StoreConfig:
    """Configuration for Store initialization."""
    initial_state: State
    reducer: ReducerType
    middleware: Optional[List[MiddlewareType]] = None
    event_bus: Optional[Any] = None  # Avoid circular import
    enable_devtools: bool = False
    enable_time_travel: bool = False


class Middleware(ABC):
    """Base class for middleware implementations."""
    
    @abstractmethod
    def __call__(self, store: 'Store') -> Callable[[Callable], Callable]:
        """
        Apply middleware to the store.
        
        Args:
            store: The store instance
            
        Returns:
            A function that takes the next dispatch function and returns
            a new dispatch function.
        """
        pass


class Reducer(ABC):
    """Base class for reducer implementations."""
    
    @abstractmethod
    def __call__(self, state: StateType, action: ActionType) -> StateType:
        """
        Process an action and return new state.
        
        Args:
            state: Current state
            action: Action to process
            
        Returns:
            New state (must be immutable update)
        """
        pass


@dataclass
class StateChange:
    """Represents a state change event."""
    old_state: State
    new_state: State
    action: Any
    timestamp: float
    
    @property
    def has_changed(self) -> bool:
        """Check if state actually changed."""
        return self.old_state != self.new_state