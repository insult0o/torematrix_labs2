"""Unit tests for processor resilience features."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from typing import Dict, Any

from torematrix.processing.processors.base import (
    BaseProcessor,
    ProcessorMetadata,
    ProcessorContext,
    ProcessorResult,
    StageStatus,
    ProcessorTimeoutError
)
from torematrix.processing.processors.resilience import (
    CircuitBreaker,
    CircuitState,
    ResilientProcessor,
    ProcessorChain
)


class TestProcessor(BaseProcessor):
    """Test processor for resilience tests."""
    
    def __init__(self, config: Dict[str, Any] = None, should_fail: bool = False):
        super().__init__(config)
        self.should_fail = should_fail
        self.call_count = 0
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="test_processor",
            version="1.0.0",
            description="Test processor",
            timeout_seconds=5
        )
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        self.call_count += 1
        
        if self.should_fail:
            raise Exception(f"Test failure #{self.call_count}")
        
        return ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            extracted_data={"call_count": self.call_count}
        )


class SlowProcessor(BaseProcessor):
    """Processor that takes time to complete."""
    
    def __init__(self, delay: float = 1.0):
        super().__init__()
        self.delay = delay
    
    @classmethod
    def get_metadata(cls) -> ProcessorMetadata:
        return ProcessorMetadata(
            name="slow_processor",
            version="1.0.0",
            description="Slow test processor",
            timeout_seconds=2
        )
    
    async def process(self, context: ProcessorContext) -> ProcessorResult:
        await asyncio.sleep(self.delay)
        return ProcessorResult(
            processor_name=self.get_metadata().name,
            status=StageStatus.COMPLETED,
            start_time=datetime.utcnow(),
            end_time=datetime.utcnow(),
            extracted_data={"delayed": True}
        )


@pytest.fixture
def test_context():
    """Create test processing context."""
    return ProcessorContext(
        document_id="doc123",
        file_path="/tmp/test.txt",
        mime_type="text/plain"
    )


class TestCircuitBreaker:
    """Test cases for CircuitBreaker."""
    
    def test_initial_state(self):
        """Test initial circuit breaker state."""
        cb = CircuitBreaker(failure_threshold=3)
        
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute()
        assert cb.failure_count == 0
    
    def test_call_succeeded_closed_state(self):
        """Test successful call in closed state."""
        cb = CircuitBreaker(failure_threshold=3)
        
        # Record some failures first
        cb.call_failed()
        cb.call_failed()
        assert cb.failure_count == 2
        
        # Success should reset failure count
        cb.call_succeeded()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED
    
    def test_circuit_opens_on_threshold(self):
        """Test circuit opens when failure threshold is reached."""
        cb = CircuitBreaker(failure_threshold=3)
        
        # Record failures up to threshold
        cb.call_failed()
        cb.call_failed()
        assert cb.state == CircuitState.CLOSED
        
        cb.call_failed()  # Third failure
        assert cb.state == CircuitState.OPEN
        assert not cb.can_execute()
    
    def test_half_open_after_timeout(self):
        """Test circuit goes to half-open after timeout."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        
        # Open the circuit
        cb.call_failed()
        assert cb.state == CircuitState.OPEN
        
        # Should immediately allow execution (timeout = 0)
        assert cb.can_execute()
        assert cb.state == CircuitState.HALF_OPEN
    
    def test_half_open_to_closed_on_success(self):
        """Test transition from half-open to closed on success."""
        cb = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=0,
            half_open_requests=2
        )
        
        # Open circuit
        cb.call_failed()
        assert cb.state == CircuitState.OPEN
        
        # Go to half-open
        cb.can_execute()
        assert cb.state == CircuitState.HALF_OPEN
        
        # Successful calls should eventually close circuit
        cb.call_succeeded()
        assert cb.state == CircuitState.HALF_OPEN
        
        cb.call_succeeded()  # Second success
        assert cb.state == CircuitState.CLOSED
    
    def test_half_open_to_open_on_failure(self):
        """Test transition from half-open to open on failure."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0)
        
        # Open circuit
        cb.call_failed()
        assert cb.state == CircuitState.OPEN
        
        # Go to half-open
        cb.can_execute()
        assert cb.state == CircuitState.HALF_OPEN
        
        # Failure should reopen circuit
        cb.call_failed()
        assert cb.state == CircuitState.OPEN
    
    def test_state_change_callbacks(self):
        """Test state change callbacks."""
        cb = CircuitBreaker(failure_threshold=1)
        
        callback_calls = []
        def callback(old_state, new_state):
            callback_calls.append((old_state, new_state))
        
        cb.add_state_change_callback(callback)
        
        # Trigger state change
        cb.call_failed()
        
        assert len(callback_calls) == 1
        assert callback_calls[0] == (CircuitState.CLOSED, CircuitState.OPEN)
    
    def test_get_state_info(self):
        """Test getting state information."""
        cb = CircuitBreaker(failure_threshold=2)
        
        info = cb.get_state_info()
        assert info["state"] == "closed"
        assert info["failure_count"] == 0
        assert info["last_failure"] is None
        
        # Add failure
        cb.call_failed()
        info = cb.get_state_info()
        assert info["failure_count"] == 1
        assert info["last_failure"] is not None


class TestResilientProcessor:
    """Test cases for ResilientProcessor."""
    
    @pytest.mark.asyncio
    async def test_successful_processing(self, test_context):
        """Test successful processing through resilient wrapper."""
        base_processor = TestProcessor()
        resilient = ResilientProcessor(base_processor)
        
        await resilient.initialize()
        result = await resilient.process(test_context)
        
        assert result.status == StageStatus.COMPLETED
        assert result.extracted_data["call_count"] == 1
        assert base_processor.call_count == 1
        assert resilient.circuit_breaker.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self, test_context):
        """Test retry logic on processor failure."""
        base_processor = TestProcessor(should_fail=True)
        resilient = ResilientProcessor(
            base_processor,
            retry_count=3,
            retry_delay=0.01  # Short delay for testing
        )
        
        await resilient.initialize()
        result = await resilient.process(test_context)
        
        assert result.status == StageStatus.FAILED
        assert base_processor.call_count == 3  # Should retry 3 times
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_retry_with_eventual_success(self, test_context):
        """Test retry logic with eventual success."""
        # Create processor that fails twice then succeeds
        call_count = 0
        
        class FlakyProcessor(BaseProcessor):
            @classmethod
            def get_metadata(cls) -> ProcessorMetadata:
                return ProcessorMetadata(name="flaky", version="1.0.0", description="Flaky")
            
            async def process(self, context: ProcessorContext) -> ProcessorResult:
                nonlocal call_count
                call_count += 1
                
                if call_count <= 2:
                    raise Exception(f"Failure #{call_count}")
                
                return ProcessorResult(
                    processor_name="flaky",
                    status=StageStatus.COMPLETED,
                    start_time=datetime.utcnow(),
                    end_time=datetime.utcnow(),
                    extracted_data={"success_on_attempt": call_count}
                )
        
        base_processor = FlakyProcessor()
        resilient = ResilientProcessor(
            base_processor,
            retry_count=3,
            retry_delay=0.01
        )
        
        await resilient.initialize()
        result = await resilient.process(test_context)
        
        assert result.status == StageStatus.COMPLETED
        assert call_count == 3  # Failed twice, succeeded on third attempt
        assert result.extracted_data["success_on_attempt"] == 3
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, test_context):
        """Test timeout handling."""
        slow_processor = SlowProcessor(delay=3.0)  # 3 second delay
        resilient = ResilientProcessor(
            slow_processor,
            timeout=0.1,  # 100ms timeout
            retry_count=1
        )
        
        await resilient.initialize()
        result = await resilient.process(test_context)
        
        assert result.status == StageStatus.FAILED
        assert any("timed out" in error for error in result.errors)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, test_context):
        """Test circuit breaker integration."""
        base_processor = TestProcessor(should_fail=True)
        cb = CircuitBreaker(failure_threshold=2)
        resilient = ResilientProcessor(
            base_processor,
            circuit_breaker=cb,
            retry_count=1
        )
        
        await resilient.initialize()
        
        # First failure
        result1 = await resilient.process(test_context)
        assert result1.status == StageStatus.FAILED
        assert cb.state == CircuitState.CLOSED
        
        # Second failure should open circuit
        result2 = await resilient.process(test_context)
        assert result2.status == StageStatus.FAILED
        assert cb.state == CircuitState.OPEN
        
        # Third attempt should be blocked by circuit
        result3 = await resilient.process(test_context)
        assert result3.status == StageStatus.FAILED
        assert "Circuit breaker is OPEN" in result3.errors
    
    @pytest.mark.asyncio
    async def test_fallback_processor(self, test_context):
        """Test fallback processor when primary fails."""
        primary = TestProcessor(should_fail=True)
        fallback = TestProcessor(should_fail=False)
        
        resilient = ResilientProcessor(
            primary,
            fallback_processor=fallback,
            retry_count=1
        )
        
        await resilient.initialize()
        result = await resilient.process(test_context)
        
        assert result.status == StageStatus.COMPLETED
        assert result.processor_name == "test_processor"  # Fallback succeeded
        assert fallback.call_count == 1
    
    @pytest.mark.asyncio
    async def test_fallback_when_circuit_open(self, test_context):
        """Test fallback processor when circuit is open."""
        primary = TestProcessor(should_fail=True)
        fallback = TestProcessor(should_fail=False)
        cb = CircuitBreaker(failure_threshold=1)
        
        resilient = ResilientProcessor(
            primary,
            circuit_breaker=cb,
            fallback_processor=fallback,
            retry_count=1
        )
        
        await resilient.initialize()
        
        # Open circuit
        result1 = await resilient.process(test_context)
        assert cb.state == CircuitState.OPEN
        
        # Next call should use fallback immediately
        result2 = await resilient.process(test_context)
        assert result2.status == StageStatus.COMPLETED
        assert fallback.call_count == 2  # Once for retry, once for circuit open
    
    @pytest.mark.asyncio
    async def test_cleanup(self, test_context):
        """Test cleanup of wrapped processors."""
        primary = Mock(spec=BaseProcessor)
        primary.get_metadata.return_value = ProcessorMetadata(
            name="mock", version="1.0.0", description="Mock"
        )
        primary.initialize = AsyncMock()
        primary.cleanup = AsyncMock()
        
        fallback = Mock(spec=BaseProcessor)
        fallback.initialize = AsyncMock()
        fallback.cleanup = AsyncMock()
        
        resilient = ResilientProcessor(primary, fallback_processor=fallback)
        
        await resilient.initialize()
        await resilient.cleanup()
        
        primary.cleanup.assert_called_once()
        fallback.cleanup.assert_called_once()
    
    def test_resilience_metrics(self):
        """Test resilience metrics collection."""
        base_processor = TestProcessor()
        resilient = ResilientProcessor(base_processor)
        
        # Add some metrics data
        resilient._retry_metrics.extend([datetime.utcnow()] * 5)
        resilient._timeout_metrics.extend([datetime.utcnow()] * 2)
        
        metrics = resilient.get_resilience_metrics()
        
        assert "circuit_breaker" in metrics
        assert "retry_rate_per_minute" in metrics
        assert "timeout_rate_per_minute" in metrics
        assert "total_retries" in metrics
        assert "total_timeouts" in metrics
        assert metrics["total_retries"] == 5
        assert metrics["total_timeouts"] == 2


class TestProcessorChain:
    """Test cases for ProcessorChain."""
    
    @pytest.mark.asyncio
    async def test_chain_initialization(self):
        """Test chain initialization."""
        proc1 = TestProcessor()
        proc2 = TestProcessor()
        
        chain = ProcessorChain([proc1, proc2])
        await chain.initialize()
        
        assert proc1._initialized
        assert proc2._initialized
    
    @pytest.mark.asyncio
    async def test_chain_success_first_processor(self, test_context):
        """Test chain succeeds with first processor."""
        proc1 = TestProcessor(should_fail=False)
        proc2 = TestProcessor(should_fail=False)
        
        chain = ProcessorChain([proc1, proc2])
        await chain.initialize()
        
        result = await chain.process(test_context)
        
        assert result.status == StageStatus.COMPLETED
        assert proc1.call_count == 1
        assert proc2.call_count == 0  # Should not be called
    
    @pytest.mark.asyncio
    async def test_chain_fallback_to_second(self, test_context):
        """Test chain falls back to second processor."""
        proc1 = TestProcessor(should_fail=True)
        proc2 = TestProcessor(should_fail=False)
        
        chain = ProcessorChain([proc1, proc2])
        await chain.initialize()
        
        result = await chain.process(test_context)
        
        assert result.status == StageStatus.COMPLETED
        assert proc1.call_count == 1
        assert proc2.call_count == 1
    
    @pytest.mark.asyncio
    async def test_chain_all_fail(self, test_context):
        """Test chain when all processors fail."""
        proc1 = TestProcessor(should_fail=True)
        proc2 = TestProcessor(should_fail=True)
        
        chain = ProcessorChain([proc1, proc2])
        await chain.initialize()
        
        result = await chain.process(test_context)
        
        assert result.status == StageStatus.FAILED
        assert proc1.call_count == 1
        assert proc2.call_count == 1
        assert len(result.errors) == 2  # Errors from both processors
    
    @pytest.mark.asyncio
    async def test_chain_cleanup(self):
        """Test chain cleanup."""
        proc1 = Mock(spec=BaseProcessor)
        proc1.initialize = AsyncMock()
        proc1.cleanup = AsyncMock()
        
        proc2 = Mock(spec=BaseProcessor)
        proc2.initialize = AsyncMock()
        proc2.cleanup = AsyncMock()
        
        chain = ProcessorChain([proc1, proc2])
        await chain.initialize()
        await chain.cleanup()
        
        proc1.cleanup.assert_called_once()
        proc2.cleanup.assert_called_once()
    
    def test_chain_empty_processors(self):
        """Test chain with empty processor list."""
        with pytest.raises(ValueError, match="At least one processor required"):
            ProcessorChain([])
    
    def test_chain_metadata(self):
        """Test chain metadata."""
        proc1 = TestProcessor()
        proc2 = TestProcessor()
        
        chain = ProcessorChain([proc1, proc2])
        metadata = chain.get_metadata()
        
        assert metadata.name == "chain_test_processor"
        assert "Chain with 2 processors" in metadata.description