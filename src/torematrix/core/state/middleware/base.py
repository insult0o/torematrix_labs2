"""
Base middleware classes and utilities.

This module provides the base classes and utilities for creating
middleware for the state management system.
"""

from typing import Callable, List, Any
from abc import ABC, abstractmethod
import logging

from ..types import Middleware as MiddlewareBase
from ..actions import Action

logger = logging.getLogger(__name__)


class Middleware(MiddlewareBase):
    """
    Base middleware class.
    
    Middleware allows you to intercept actions before they reach the reducer,
    enabling logging, async operations, validation, and more.
    """
    
    def __init__(self, name: str = None):
        """
        Initialize middleware.
        
        Args:
            name: Optional name for debugging
        """
        self.name = name or self.__class__.__name__
    
    @abstractmethod
    def process(self, action: Action, next_dispatch: Callable) -> Any:
        """
        Process an action.
        
        Args:
            action: The action being dispatched
            next_dispatch: Function to call to continue the chain
            
        Returns:
            Result of the dispatch
        """
        pass
    
    def __call__(self, store: 'Store') -> Callable[[Callable], Callable]:
        """
        Apply middleware to store.
        
        Args:
            store: The store instance
            
        Returns:
            Middleware function
        """
        def middleware(next_dispatch: Callable) -> Callable:
            def dispatch(action: Action) -> Any:
                return self.process(action, next_dispatch)
            return dispatch
        return middleware


def compose_middleware(*middleware: Middleware) -> List[Middleware]:
    """
    Compose multiple middleware into a list.
    
    Args:
        *middleware: Middleware instances
        
    Returns:
        List of middleware
    """
    return list(middleware)


class ConditionalMiddleware(Middleware):
    """Middleware that conditionally processes actions."""
    
    def __init__(self, condition: Callable[[Action], bool], 
                 middleware: Middleware, name: str = None):
        """
        Initialize conditional middleware.
        
        Args:
            condition: Function to determine if middleware should process action
            middleware: Middleware to apply if condition is true
            name: Optional name for debugging
        """
        super().__init__(name)
        self.condition = condition
        self.middleware = middleware
    
    def process(self, action: Action, next_dispatch: Callable) -> Any:
        """Process action if condition is met."""
        if self.condition(action):
            return self.middleware.process(action, next_dispatch)
        return next_dispatch(action)


class ChainMiddleware(Middleware):
    """Middleware that chains multiple middleware together."""
    
    def __init__(self, *middleware: Middleware, name: str = None):
        """
        Initialize chain middleware.
        
        Args:
            *middleware: Middleware to chain
            name: Optional name for debugging
        """
        super().__init__(name)
        self.middleware_list = list(middleware)
    
    def process(self, action: Action, next_dispatch: Callable) -> Any:
        """Process action through all middleware in chain."""
        # Build the chain in reverse order
        chain = next_dispatch
        for mw in reversed(self.middleware_list):
            # Create closure to capture current chain
            def make_next(current_chain, current_mw):
                return lambda act: current_mw.process(act, current_chain)
            chain = make_next(chain, mw)
        
        return chain(action)