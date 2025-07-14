"""
Middleware pipeline implementation for composable action processing.
"""

from typing import List, Callable, Any, Protocol, Dict
import asyncio
from functools import reduce
import logging
import time

logger = logging.getLogger(__name__)


class Middleware(Protocol):
    """Protocol for middleware functions."""
    
    def __call__(self, store: 'Store') -> Callable[[Callable], Callable]:
        """
        Middleware signature: store -> next -> action -> result
        """
        ...


class MiddlewarePipeline:
    """
    Composable middleware pipeline for processing actions.
    
    Middleware are applied in the order they are added, with each
    middleware wrapping the next one in the chain.
    """
    
    def __init__(self):
        self._middleware: List[Middleware] = []
        self._metrics = {
            'total_actions': 0,
            'middleware_time': 0,
            'errors': 0,
        }
    
    def use(self, middleware: Middleware) -> 'MiddlewarePipeline':
        """
        Add middleware to the pipeline.
        
        Args:
            middleware: Middleware function following the protocol
            
        Returns:
            Self for chaining
        """
        self._middleware.append(middleware)
        logger.debug(f"Added middleware: {middleware.__class__.__name__}")
        return self
    
    def compose(self) -> Callable:
        """
        Compose all middleware into a single dispatch function.
        
        Returns:
            Composed dispatch function
        """
        def composed(store):
            # Build middleware chain from right to left
            chain = []
            for middleware in reversed(self._middleware):
                try:
                    chain.append(middleware(store))
                except Exception as e:
                    logger.error(f"Error initializing middleware {middleware}: {e}")
                    self._metrics['errors'] += 1
                    continue
            
            def dispatch(action):
                start_time = time.time()
                self._metrics['total_actions'] += 1
                
                try:
                    # Apply middleware chain
                    enhanced_dispatch = reduce(
                        lambda next_func, middleware: middleware(next_func),
                        chain,
                        store._dispatch
                    )
                    
                    result = enhanced_dispatch(action)
                    
                    # Track timing
                    duration = time.time() - start_time
                    self._metrics['middleware_time'] += duration
                    
                    logger.debug(f"Action {action.type} processed in {duration:.3f}s")
                    return result
                    
                except Exception as e:
                    self._metrics['errors'] += 1
                    logger.error(f"Middleware error processing {action.type}: {e}")
                    raise
            
            return dispatch
        return composed
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get middleware performance metrics."""
        return {
            **self._metrics,
            'avg_time_per_action': (
                self._metrics['middleware_time'] / self._metrics['total_actions']
                if self._metrics['total_actions'] > 0 else 0
            )
        }
    
    def clear(self) -> None:
        """Clear all middleware from the pipeline."""
        self._middleware.clear()
        logger.debug("Middleware pipeline cleared")
    
    def __len__(self) -> int:
        """Return number of middleware in pipeline."""
        return len(self._middleware)
    
    def __bool__(self) -> bool:
        """Return True if pipeline has middleware."""
        return bool(self._middleware)


def logging_middleware(store):
    """Basic logging middleware for debugging."""
    def middleware(next_dispatch):
        def dispatch(action):
            logger.info(f"Dispatching action: {action.type}")
            logger.debug(f"Action payload: {getattr(action, 'payload', None)}")
            
            result = next_dispatch(action)
            
            logger.debug(f"Action {action.type} completed")
            return result
        return dispatch
    return middleware


def timing_middleware(store):
    """Middleware for measuring action processing time."""
    def middleware(next_dispatch):
        def dispatch(action):
            start_time = time.time()
            
            result = next_dispatch(action)
            
            duration = time.time() - start_time
            logger.info(f"Action {action.type} took {duration:.3f}s")
            
            return result
        return dispatch
    return middleware