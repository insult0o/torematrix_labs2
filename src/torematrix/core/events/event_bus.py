import asyncio
import logging
import time
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .event_types import Event, EventPriority
from .monitoring import PerformanceMonitor

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        self._handlers: Dict[str, Set[Callable]] = defaultdict(set)
        self._middlewares: List[Callable] = []
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._process_task: Optional[asyncio.Task] = None
        self._monitor = PerformanceMonitor()
        self._monitor_task: Optional[asyncio.Task] = None
    
    def subscribe(self, event_type: str, handler: Callable) -> None:
        self._handlers[event_type].add(handler)
        
    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        if event_type in self._handlers:
            self._handlers[event_type].discard(handler)
            if not self._handlers[event_type]:
                del self._handlers[event_type]
    
    def add_middleware(self, middleware: Callable) -> None:
        self._middlewares.append(middleware)
    
    async def publish(self, event: Event) -> None:
        start_time = time.time()
        success = True
        original_event = event  # Keep original event for metrics
        
        try:
            for middleware in self._middlewares:
                try:
                    event = await middleware(event)
                    if event is None:
                        logger.debug("Event dropped by middleware")
                        return
                except Exception as e:
                    logger.error(f"Middleware error: {e}")
                    success = False
                    return
            
            await self._event_queue.put(event)
            
        except Exception as e:
            logger.error(f"Error publishing event: {e}")
            success = False
            raise
        
        finally:
            processing_time = time.time() - start_time
            # Use original event for metrics even if middleware drops it
            self._monitor.record_event_processing(original_event, processing_time, success)
    
    async def start(self) -> None:
        if self._running:
            return
        
        self._running = True
        self._process_task = asyncio.create_task(self._process_events())
        self._monitor_task = asyncio.create_task(
            self._monitor.start_snapshot_collection(self._event_queue)
        )
    
    async def stop(self) -> None:
        if not self._running:
            return
        
        self._running = False
        await self._event_queue.put(None)  # Sentinel value
        if self._process_task:
            await self._process_task
            self._process_task = None
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
    
    def get_metrics(self) -> Dict[str, Any]:
        return {
            "events": self._monitor.get_event_metrics(),
            "handlers": self._monitor.get_handler_metrics(),
            "total": self._monitor.get_total_metrics(),
            "queue_size": self._event_queue.qsize()
        }
    
    async def _process_events(self) -> None:
        while self._running:
            event = await self._event_queue.get()
            if event is None:  # Sentinel value
                break
                
            if event.event_type not in self._handlers:
                logger.warning(f"No handlers for event type: {event.event_type}")
                continue
                
            await self._process_handlers(event)
            self._event_queue.task_done()
    
    async def _process_handlers(self, event: Event) -> None:
        for handler in self._handlers[event.event_type]:
            handler_name = getattr(handler, "__name__", str(handler))
            start_time = time.time()
            success = True
            
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Handler error: {e}")
                success = False
            finally:
                execution_time = time.time() - start_time
                self._monitor.record_handler_execution(
                    handler_name,
                    execution_time,
                    success
                )