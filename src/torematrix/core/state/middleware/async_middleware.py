"""
Async middleware support for handling asynchronous operations.
"""

import asyncio
from typing import Callable, Any, Awaitable
import logging

logger = logging.getLogger(__name__)


class AsyncMiddleware:
    """
    Support for asynchronous middleware in the pipeline.
    
    Wraps async handlers to work with the synchronous middleware interface.
    """
    
    def __init__(self, async_handler: Callable):
        """
        Initialize async middleware.
        
        Args:
            async_handler: Async function with signature (store, action, next_dispatch) -> result
        """
        self.async_handler = async_handler
        self._pending_actions = {}
    
    def __call__(self, store):
        """Create middleware function."""
        def middleware(next_dispatch):
            def dispatch(action):
                # Check if we're already in an async context
                try:
                    loop = asyncio.get_running_loop()
                    # We're in an async context, schedule the coroutine
                    task = loop.create_task(self._async_dispatch(store, action, next_dispatch))
                    self._pending_actions[action.id] = task
                    return task
                except RuntimeError:
                    # No running loop, use asyncio.run
                    return asyncio.run(self._async_dispatch(store, action, next_dispatch))
            
            return dispatch
        return middleware
    
    async def _async_dispatch(self, store, action, next_dispatch):
        """Internal async dispatch handler."""
        try:
            logger.debug(f"Processing async action: {action.type}")
            
            # Call the async handler
            result = await self.async_handler(store, action, next_dispatch)
            
            # Clean up tracking
            if hasattr(action, 'id') and action.id in self._pending_actions:
                del self._pending_actions[action.id]
            
            logger.debug(f"Async action {action.type} completed")
            return result
            
        except Exception as e:
            logger.error(f"Async middleware error for {action.type}: {e}")
            # Clean up on error
            if hasattr(action, 'id') and action.id in self._pending_actions:
                del self._pending_actions[action.id]
            raise
    
    def get_pending_actions(self):
        """Get currently pending async actions."""
        return list(self._pending_actions.keys())
    
    async def wait_for_completion(self):
        """Wait for all pending actions to complete."""
        if self._pending_actions:
            await asyncio.gather(*self._pending_actions.values(), return_exceptions=True)


def async_logging_middleware(store, action, next_dispatch):
    """Example async middleware for logging with async operations."""
    async def handler():
        logger.info(f"Async processing: {action.type}")
        
        # Simulate async operation
        await asyncio.sleep(0.001)
        
        # Continue with next middleware
        result = next_dispatch(action) 
        
        logger.info(f"Async completed: {action.type}")
        return result
    
    return handler()


def async_validation_middleware(store, action, next_dispatch):
    """Example async middleware for validation."""
    async def handler():
        # Simulate async validation (e.g., API call)
        await asyncio.sleep(0.001)
        
        # Validate action
        if not hasattr(action, 'type'):
            raise ValueError("Action must have a type")
        
        # Continue processing
        return next_dispatch(action)
    
    return handler()