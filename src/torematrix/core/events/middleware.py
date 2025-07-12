import logging
from typing import Any, Callable, Dict, List, Optional
from .event_types import Event

logger = logging.getLogger(__name__)

class BaseMiddleware:
    async def __call__(self, event: Event) -> Optional[Event]:
        try:
            return await self.process(event)
        except Exception as e:
            logger.error(f"Middleware error in {self.__class__.__name__}: {e}")
            return None

    async def process(self, event: Event) -> Optional[Event]:
        raise NotImplementedError

class ValidationMiddleware(BaseMiddleware):
    async def process(self, event: Event) -> Optional[Event]:
        if not event.event_type:
            logger.error("Event type is required")
            return None
        if not isinstance(event.payload, dict):
            logger.error("Event payload must be a dictionary")
            return None
        return event

class LoggingMiddleware(BaseMiddleware):
    def __init__(self, log_level: int = logging.INFO):
        self.log_level = log_level

    async def process(self, event: Event) -> Event:
        logger.log(self.log_level, f"Processing event: {event.event_type}")
        return event

class MetricsMiddleware(BaseMiddleware):
    def __init__(self):
        self.event_counts: Dict[str, int] = {}
        self.error_counts: Dict[str, int] = {}

    async def process(self, event: Event) -> Event:
        self.event_counts[event.event_type] = self.event_counts.get(event.event_type, 0) + 1
        if event.event_type.endswith(".error.occurred"):
            error_type = event.payload.get("error_type", "unknown")
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        return event

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "event_counts": self.event_counts.copy(),
            "error_counts": self.error_counts.copy(),
            "total_events": sum(self.event_counts.values()),
            "total_errors": sum(self.error_counts.values())
        }

class FilterMiddleware(BaseMiddleware):
    def __init__(self, event_types: Optional[List[str]] = None):
        self.event_types = set(event_types) if event_types else None

    async def process(self, event: Event) -> Optional[Event]:
        if self.event_types is None or event.event_type in self.event_types:
            return event
        return None