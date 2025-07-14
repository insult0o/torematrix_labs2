"""Resilience and error handling for processors.

This module provides circuit breaker, retry logic, and fault tolerance
features to make processors more resilient to failures.
"""

import asyncio
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import logging

from .base import (
    BaseProcessor,
    ProcessorContext,
    ProcessorResult,
    ProcessorException,
    ProcessorTimeoutError,
    StageStatus,
    ProcessorMetadata
)

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """
    Circuit breaker for processor fault tolerance.
    
    Prevents cascading failures by temporarily disabling
    failing processors.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_requests: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_count = 0
        
        self._state_change_callbacks: List[Callable] = []
    
    def call_succeeded(self):
        """Record successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.half_open_count += 1
            if self.half_open_count >= self.half_open_requests:
                self._transition_to(CircuitState.CLOSED)
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def call_failed(self):
        """Record failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                self._transition_to(CircuitState.OPEN)
        elif self.state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.OPEN)
    
    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == CircuitState.CLOSED:
            return True
        elif self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._transition_to(CircuitState.HALF_OPEN)
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset."""
        return (
            self.last_failure_time and
            datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
        )
    
    def _transition_to(self, new_state: CircuitState):
        """Transition to new state."""
        if new_state != self.state:
            old_state = self.state
            self.state = new_state
            
            if new_state == CircuitState.CLOSED:
                self.failure_count = 0
            elif new_state == CircuitState.HALF_OPEN:
                self.half_open_count = 0
            
            logger.info(f"Circuit breaker: {old_state.value} -> {new_state.value}")
            
            # Notify callbacks
            for callback in self._state_change_callbacks:
                callback(old_state, new_state)
    
    def add_state_change_callback(self, callback: Callable):
        """Add callback for state changes."""
        self._state_change_callbacks.append(callback)
    
    def get_state_info(self) -> Dict[str, Any]:
        """Get circuit breaker state information."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None
        }


class ResilientProcessor(BaseProcessor):
    """
    Wrapper that adds resilience features to any processor.
    
    Features:
    - Circuit breaker
    - Retry logic
    - Timeout enforcement
    - Fallback handling
    """
    
    def __init__(
        self,
        processor: BaseProcessor,
        circuit_breaker: Optional[CircuitBreaker] = None,
        retry_count: int = 3,
        retry_delay: float = 1.0,
        timeout: Optional[float] = None,
        fallback_processor: Optional[BaseProcessor] = None
    ):
        super().__init__(processor.config)
        self.processor = processor
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.timeout = timeout or processor.get_metadata().timeout_seconds
        self.fallback_processor = fallback_processor
        
        # Metrics
        self._retry_metrics = deque(maxlen=100)
        self._timeout_metrics = deque(maxlen=100)
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        # This would be dynamically generated from wrapped processor
        raise NotImplementedError("Use wrapped processor metadata")
    
    def get_metadata(self) -> ProcessorMetadata:
        """Get metadata from wrapped processor."""
        return self.processor.get_metadata()
    
    async def initialize(self) -> None:
        """Initialize wrapped processor."""
        await self.processor.initialize()
        if self.fallback_processor:
            await self.fallback_processor.initialize()
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """Process with resilience features."""
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker OPEN for {self.processor.get_metadata().name}")
            
            # Use fallback if available
            if self.fallback_processor:
                return await self.fallback_processor.process(context)
            
            # Return failure
            return ProcessorResult(
                processor_name=self.processor.get_metadata().name,
                status=StageStatus.FAILED,
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                errors=["Circuit breaker is OPEN"]
            )
        
        # Try processing with retries
        last_error = None
        for attempt in range(self.retry_count):
            try:
                # Process with timeout
                result = await asyncio.wait_for(
                    self.processor.process(context),
                    timeout=self.timeout
                )
                
                # Success
                self.circuit_breaker.call_succeeded()
                return result
                
            except asyncio.TimeoutError:
                last_error = ProcessorTimeoutError(
                    f"Processor timed out after {self.timeout}s"
                )
                self._timeout_metrics.append(datetime.utcnow())
                logger.warning(f"Timeout on attempt {attempt + 1}")
                
            except Exception as e:
                last_error = e
                logger.warning(f"Error on attempt {attempt + 1}: {e}")
            
            # Wait before retry (except last attempt)
            if attempt < self.retry_count - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))
                self._retry_metrics.append(datetime.utcnow())
        
        # All retries failed
        self.circuit_breaker.call_failed()
        
        # Try fallback
        if self.fallback_processor:
            logger.info("Using fallback processor")
            try:
                return await self.fallback_processor.process(context)
            except Exception as e:
                logger.error(f"Fallback also failed: {e}")
        
        # Return failure
        return ProcessorResult(
            processor_name=self.processor.get_metadata().name,
            status=StageStatus.FAILED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            errors=[str(last_error)] if last_error else ["Processing failed"]
        )
    
    async def cleanup(self) -> None:
        """Cleanup wrapped processors."""
        await self.processor.cleanup()
        if self.fallback_processor:
            await self.fallback_processor.cleanup()
    
    def get_resilience_metrics(self) -> Dict[str, Any]:
        """Get resilience-related metrics."""
        now = datetime.utcnow()
        
        # Calculate retry rate (last minute)
        recent_retries = [
            t for t in self._retry_metrics
            if now - t < timedelta(minutes=1)
        ]
        
        # Calculate timeout rate (last minute)
        recent_timeouts = [
            t for t in self._timeout_metrics
            if now - t < timedelta(minutes=1)
        ]
        
        return {
            "circuit_breaker": self.circuit_breaker.get_state_info(),
            "retry_rate_per_minute": len(recent_retries),
            "timeout_rate_per_minute": len(recent_timeouts),
            "total_retries": len(self._retry_metrics),
            "total_timeouts": len(self._timeout_metrics)
        }


class ProcessorChain:
    """
    Chain multiple processors with fallback support.
    
    Tries processors in order until one succeeds.
    """
    
    def __init__(self, processors: List[BaseProcessor]):
        if not processors:
            raise ValueError("At least one processor required")
        
        self.processors = processors
    
    async def initialize(self):
        """Initialize all processors in chain."""
        for processor in self.processors:
            await processor.initialize()
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        """Process using chain of processors."""
        errors = []
        
        for i, processor in enumerate(self.processors):
            try:
                logger.info(f"Trying processor {i + 1}/{len(self.processors)}: {processor.get_metadata().name}")
                result = await processor.process(context)
                
                if result.status == StageStatus.COMPLETED:
                    return result
                
                errors.extend(result.errors)
                
            except Exception as e:
                errors.append(f"{processor.get_metadata().name}: {str(e)}")
                logger.error(f"Processor {processor.get_metadata().name} failed: {e}")
        
        # All processors failed
        return ProcessorResult(
            processor_name="processor_chain",
            status=StageStatus.FAILED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            errors=errors
        )
    
    async def cleanup(self):
        """Cleanup all processors."""
        for processor in self.processors:
            await processor.cleanup()
    
    def get_metadata(self) -> ProcessorMetadata:
        """Get metadata for the chain (uses first processor as primary)."""
        primary = self.processors[0].get_metadata()
        return ProcessorMetadata(
            name=f"chain_{primary.name}",
            version=primary.version,
            description=f"Chain with {len(self.processors)} processors",
            author=primary.author,
            capabilities=primary.capabilities,
            supported_formats=primary.supported_formats
        )