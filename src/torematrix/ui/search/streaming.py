"""Memory-Efficient Result Streaming

High-performance result streaming system that handles massive datasets
without loading everything into memory. Provides real-time result delivery
with backpressure handling and adaptive buffering.
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, List, Optional, Any, Callable, Union, Set
from enum import Enum
from abc import ABC, abstractmethod

from torematrix.core.models.element import Element

logger = logging.getLogger(__name__)


class StreamState(Enum):
    """Stream processing states"""
    IDLE = "idle"
    STREAMING = "streaming"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BackpressureStrategy(Enum):
    """Backpressure handling strategies"""
    DROP_OLDEST = "drop_oldest"
    DROP_NEWEST = "drop_newest"
    PAUSE_PRODUCER = "pause_producer"
    BLOCK = "block"


@dataclass
class StreamMetrics:
    """Metrics for stream processing"""
    stream_id: str
    start_time: float
    items_produced: int = 0
    items_consumed: int = 0
    bytes_streamed: int = 0
    buffer_size: int = 0
    max_buffer_size: int = 0
    backpressure_events: int = 0
    processing_time: float = 0.0
    current_rate: float = 0.0  # items per second
    avg_rate: float = 0.0
    
    @property
    def elapsed_time(self) -> float:
        return time.time() - self.start_time
    
    @property
    def buffer_utilization(self) -> float:
        if self.max_buffer_size == 0:
            return 0.0
        return (self.buffer_size / self.max_buffer_size) * 100.0


@dataclass
class StreamChunk:
    """A chunk of streamed data"""
    chunk_id: str
    sequence_number: int
    data: List[Element]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    size_bytes: int = 0
    
    def __post_init__(self):
        if self.size_bytes == 0:
            # Estimate size based on data
            self.size_bytes = len(str(self.data))


class ResultStreamer(ABC):
    """Abstract interface for result streaming"""
    
    @abstractmethod
    async def stream_results(self, query_params: Dict[str, Any]) -> AsyncIterator[StreamChunk]:
        """Stream results for given query"""
        pass
    
    @abstractmethod
    async def get_total_count(self, query_params: Dict[str, Any]) -> int:
        """Get total number of results for query"""
        pass


class MemoryEfficientResultStreamer:
    """Memory-efficient result streamer with adaptive buffering"""
    
    def __init__(self,
                 result_provider: ResultStreamer,
                 max_buffer_size: int = 100,
                 chunk_size: int = 50,
                 backpressure_strategy: BackpressureStrategy = BackpressureStrategy.PAUSE_PRODUCER):
        """
        Initialize result streamer
        
        Args:
            result_provider: Provider for streaming results
            max_buffer_size: Maximum number of chunks to buffer
            chunk_size: Number of items per chunk
            backpressure_strategy: How to handle backpressure
        """
        self.result_provider = result_provider
        self.max_buffer_size = max_buffer_size
        self.chunk_size = chunk_size
        self.backpressure_strategy = backpressure_strategy
        
        # State
        self._active_streams: Dict[str, Dict[str, Any]] = {}
        self._stream_tasks: Dict[str, asyncio.Task] = {}
        self._buffer_queues: Dict[str, asyncio.Queue] = {}
        self._metrics: Dict[str, StreamMetrics] = {}
        
        # Configuration
        self.enable_adaptive_buffering = True
        self.min_buffer_size = 10
        self.buffer_growth_factor = 1.5
        self.target_latency_ms = 100
        self.memory_limit_mb = 100
        
        # Rate limiting
        self.max_streams = 10
        self.rate_limit_per_second = 1000
        
        logger.info(f"MemoryEfficientResultStreamer initialized: chunk_size={chunk_size}")
    
    async def start_stream(self,
                          stream_id: str,
                          query_params: Dict[str, Any],
                          consumer_callback: Optional[Callable[[StreamChunk], None]] = None) -> str:
        """
        Start streaming results
        
        Args:
            stream_id: Unique stream identifier
            query_params: Query parameters for result provider
            consumer_callback: Optional callback for each chunk
            
        Returns:
            Stream ID for tracking
        """
        if stream_id in self._active_streams:
            raise ValueError(f"Stream {stream_id} already active")
        
        if len(self._active_streams) >= self.max_streams:
            raise RuntimeError(f"Maximum number of streams ({self.max_streams}) reached")
        
        # Initialize stream state
        buffer_queue = asyncio.Queue(maxsize=self.max_buffer_size)
        
        self._active_streams[stream_id] = {
            'query_params': query_params,
            'consumer_callback': consumer_callback,
            'state': StreamState.STREAMING,
            'buffer_queue': buffer_queue,
            'producer_paused': False
        }
        
        self._buffer_queues[stream_id] = buffer_queue
        
        # Initialize metrics
        self._metrics[stream_id] = StreamMetrics(
            stream_id=stream_id,
            start_time=time.time(),
            max_buffer_size=self.max_buffer_size
        )
        
        # Start producer task
        producer_task = asyncio.create_task(
            self._producer_loop(stream_id, query_params)
        )
        self._stream_tasks[stream_id] = producer_task
        
        logger.info(f"Started stream {stream_id}")
        return stream_id
    
    async def stop_stream(self, stream_id: str) -> bool:
        """
        Stop streaming for given stream ID
        
        Args:
            stream_id: Stream to stop
            
        Returns:
            True if stream was stopped successfully
        """
        if stream_id not in self._active_streams:
            return False
        
        # Update state
        self._active_streams[stream_id]['state'] = StreamState.CANCELLED
        
        # Cancel producer task
        if stream_id in self._stream_tasks:
            self._stream_tasks[stream_id].cancel()
            try:
                await self._stream_tasks[stream_id]
            except asyncio.CancelledError:
                pass
            del self._stream_tasks[stream_id]
        
        # Cleanup
        await self._cleanup_stream(stream_id)
        
        logger.info(f"Stopped stream {stream_id}")
        return True
    
    async def get_next_chunk(self, stream_id: str, timeout: float = 1.0) -> Optional[StreamChunk]:
        """
        Get next chunk from stream
        
        Args:
            stream_id: Stream to read from
            timeout: Timeout in seconds
            
        Returns:
            Next chunk or None if timeout/end of stream
        """
        if stream_id not in self._active_streams:
            return None
        
        buffer_queue = self._buffer_queues[stream_id]
        metrics = self._metrics[stream_id]
        
        try:
            chunk = await asyncio.wait_for(buffer_queue.get(), timeout=timeout)
            
            # Update metrics
            metrics.items_consumed += len(chunk.data) if chunk.data else 0
            metrics.buffer_size = buffer_queue.qsize()
            
            # Handle consumer callback
            callback = self._active_streams[stream_id].get('consumer_callback')
            if callback:
                try:
                    callback(chunk)
                except Exception as e:
                    logger.error(f"Error in consumer callback: {e}")
            
            # Check if producer was paused due to backpressure
            if (self._active_streams[stream_id]['producer_paused'] and 
                buffer_queue.qsize() < self.max_buffer_size * 0.5):
                self._active_streams[stream_id]['producer_paused'] = False
                logger.debug(f"Resumed producer for stream {stream_id}")
            
            return chunk
            
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Error getting chunk from stream {stream_id}: {e}")
            return None
    
    async def pause_stream(self, stream_id: str) -> bool:
        """Pause streaming"""
        if stream_id in self._active_streams:
            self._active_streams[stream_id]['state'] = StreamState.PAUSED
            return True
        return False
    
    async def resume_stream(self, stream_id: str) -> bool:
        """Resume streaming"""
        if stream_id in self._active_streams:
            self._active_streams[stream_id]['state'] = StreamState.STREAMING
            return True
        return False
    
    def get_stream_metrics(self, stream_id: str) -> Optional[StreamMetrics]:
        """Get metrics for specific stream"""
        return self._metrics.get(stream_id)
    
    def get_all_stream_metrics(self) -> Dict[str, StreamMetrics]:
        """Get metrics for all active streams"""
        return self._metrics.copy()
    
    def get_active_streams(self) -> List[str]:
        """Get list of active stream IDs"""
        return list(self._active_streams.keys())
    
    async def _producer_loop(self, stream_id: str, query_params: Dict[str, Any]) -> None:
        """Producer loop for streaming results"""
        try:
            stream_info = self._active_streams[stream_id]
            buffer_queue = self._buffer_queues[stream_id]
            metrics = self._metrics[stream_id]
            
            chunk_sequence = 0
            rate_limiter = AsyncRateLimiter(self.rate_limit_per_second)
            
            async for chunk in self.result_provider.stream_results(query_params):
                # Check if stream was cancelled or paused
                if stream_info['state'] == StreamState.CANCELLED:
                    break
                
                while stream_info['state'] == StreamState.PAUSED:
                    await asyncio.sleep(0.1)
                    if stream_info['state'] == StreamState.CANCELLED:
                        return
                
                # Rate limiting
                await rate_limiter.acquire()
                
                # Create stream chunk
                stream_chunk = StreamChunk(
                    chunk_id=f"{stream_id}_chunk_{chunk_sequence}",
                    sequence_number=chunk_sequence,
                    data=chunk.data if hasattr(chunk, 'data') else chunk,
                    metadata=chunk.metadata if hasattr(chunk, 'metadata') else {}
                )
                
                # Handle backpressure
                await self._handle_backpressure(stream_id, stream_chunk, buffer_queue)
                
                # Update metrics
                metrics.items_produced += len(stream_chunk.data)
                metrics.bytes_streamed += stream_chunk.size_bytes
                metrics.buffer_size = buffer_queue.qsize()
                self._update_rate_metrics(metrics)
                
                chunk_sequence += 1
                
                # Adaptive buffering
                if self.enable_adaptive_buffering:
                    await self._adjust_buffer_size(stream_id, metrics)
            
            # Mark stream as completed
            stream_info['state'] = StreamState.COMPLETED
            logger.debug(f"Producer completed for stream {stream_id}")
            
        except asyncio.CancelledError:
            logger.debug(f"Producer cancelled for stream {stream_id}")
        except Exception as e:
            logger.error(f"Producer error for stream {stream_id}: {e}")
            self._active_streams[stream_id]['state'] = StreamState.FAILED
    
    async def _handle_backpressure(self, stream_id: str, chunk: StreamChunk, buffer_queue: asyncio.Queue) -> None:
        """Handle backpressure when buffer is full"""
        stream_info = self._active_streams[stream_id]
        metrics = self._metrics[stream_id]
        
        if buffer_queue.full():
            metrics.backpressure_events += 1
            
            if self.backpressure_strategy == BackpressureStrategy.DROP_OLDEST:
                # Remove oldest item and add new one
                try:
                    buffer_queue.get_nowait()
                    await buffer_queue.put(chunk)
                except:
                    pass
            
            elif self.backpressure_strategy == BackpressureStrategy.DROP_NEWEST:
                # Drop the new chunk
                logger.debug(f"Dropping chunk due to backpressure: {chunk.chunk_id}")
                return
            
            elif self.backpressure_strategy == BackpressureStrategy.PAUSE_PRODUCER:
                # Pause producer until buffer has space
                stream_info['producer_paused'] = True
                logger.debug(f"Producer paused due to backpressure: {stream_id}")
                
                while buffer_queue.full() and stream_info['state'] == StreamState.STREAMING:
                    await asyncio.sleep(0.01)
                
                stream_info['producer_paused'] = False
                await buffer_queue.put(chunk)
            
            elif self.backpressure_strategy == BackpressureStrategy.BLOCK:
                # Block until space is available
                await buffer_queue.put(chunk)
        else:
            # Normal case - buffer has space
            await buffer_queue.put(chunk)
    
    async def _adjust_buffer_size(self, stream_id: str, metrics: StreamMetrics) -> None:
        """Dynamically adjust buffer size based on performance"""
        current_latency = time.time() - metrics.start_time
        target_latency = self.target_latency_ms / 1000.0
        
        # If we're falling behind target latency, try to increase buffer
        if (current_latency > target_latency and 
            metrics.buffer_utilization > 80 and
            self.max_buffer_size < 1000):
            
            new_size = min(1000, int(self.max_buffer_size * self.buffer_growth_factor))
            
            # Create new larger queue
            old_queue = self._buffer_queues[stream_id]
            new_queue = asyncio.Queue(maxsize=new_size)
            
            # Transfer existing items
            while not old_queue.empty():
                try:
                    item = old_queue.get_nowait()
                    await new_queue.put(item)
                except:
                    break
            
            self._buffer_queues[stream_id] = new_queue
            self._active_streams[stream_id]['buffer_queue'] = new_queue
            self.max_buffer_size = new_size
            metrics.max_buffer_size = new_size
            
            logger.debug(f"Increased buffer size to {new_size} for stream {stream_id}")
    
    def _update_rate_metrics(self, metrics: StreamMetrics) -> None:
        """Update rate calculation metrics"""
        elapsed = metrics.elapsed_time
        if elapsed > 0:
            metrics.avg_rate = metrics.items_produced / elapsed
            
            # Calculate current rate over last 10 seconds
            current_window = min(10.0, elapsed)
            if current_window > 0:
                recent_items = metrics.items_produced  # Simplified - could track recent window
                metrics.current_rate = recent_items / current_window
    
    async def _cleanup_stream(self, stream_id: str) -> None:
        """Clean up stream resources"""
        try:
            # Clear buffer queue
            if stream_id in self._buffer_queues:
                queue = self._buffer_queues[stream_id]
                while not queue.empty():
                    try:
                        queue.get_nowait()
                    except:
                        break
                del self._buffer_queues[stream_id]
            
            # Remove from active streams
            if stream_id in self._active_streams:
                del self._active_streams[stream_id]
            
            # Keep metrics for historical purposes
            # Don't delete self._metrics[stream_id]
            
        except Exception as e:
            logger.error(f"Error cleaning up stream {stream_id}: {e}")


class AsyncRateLimiter:
    """Simple async rate limiter"""
    
    def __init__(self, rate_per_second: float):
        self.rate_per_second = rate_per_second
        self.last_call = 0.0
        self.min_interval = 1.0 / rate_per_second if rate_per_second > 0 else 0
    
    async def acquire(self) -> None:
        """Acquire rate limit token"""
        if self.min_interval <= 0:
            return
        
        current_time = time.time()
        elapsed = current_time - self.last_call
        
        if elapsed < self.min_interval:
            await asyncio.sleep(self.min_interval - elapsed)
        
        self.last_call = time.time()


class ElementResultStreamer(ResultStreamer):
    """Implementation of ResultStreamer for Element data"""
    
    def __init__(self, element_provider: Callable[[Dict[str, Any]], AsyncIterator[List[Element]]]):
        self.element_provider = element_provider
    
    async def stream_results(self, query_params: Dict[str, Any]) -> AsyncIterator[StreamChunk]:
        """Stream element results"""
        chunk_id = 0
        async for element_batch in self.element_provider(query_params):
            yield StreamChunk(
                chunk_id=f"element_chunk_{chunk_id}",
                sequence_number=chunk_id,
                data=element_batch,
                metadata={'source': 'element_provider'}
            )
            chunk_id += 1
    
    async def get_total_count(self, query_params: Dict[str, Any]) -> int:
        """Get total count of elements for query"""
        # This would need to be implemented based on the actual data source
        return -1  # Unknown count


# Factory functions
def create_memory_efficient_streamer(
    result_provider: ResultStreamer,
    max_buffer_size: int = 100,
    chunk_size: int = 50,
    backpressure_strategy: BackpressureStrategy = BackpressureStrategy.PAUSE_PRODUCER
) -> MemoryEfficientResultStreamer:
    """Create memory-efficient result streamer with configuration"""
    return MemoryEfficientResultStreamer(
        result_provider=result_provider,
        max_buffer_size=max_buffer_size,
        chunk_size=chunk_size,
        backpressure_strategy=backpressure_strategy
    )


def create_element_streamer(
    element_provider: Callable[[Dict[str, Any]], AsyncIterator[List[Element]]]
) -> ElementResultStreamer:
    """Create element result streamer"""
    return ElementResultStreamer(element_provider)


# Utility functions
async def stream_to_list(streamer: MemoryEfficientResultStreamer, stream_id: str, 
                        max_items: int = 1000) -> List[Element]:
    """Convert stream to list (for testing/debugging)"""
    results = []
    items_collected = 0
    
    while items_collected < max_items:
        chunk = await streamer.get_next_chunk(stream_id, timeout=0.1)
        if chunk is None:
            break
        
        if chunk.data:
            results.extend(chunk.data)
            items_collected += len(chunk.data)
    
    return results[:max_items]


def calculate_stream_efficiency(metrics: StreamMetrics) -> Dict[str, float]:
    """Calculate stream efficiency metrics"""
    efficiency_metrics = {}
    
    if metrics.elapsed_time > 0:
        efficiency_metrics['throughput'] = metrics.items_produced / metrics.elapsed_time
        efficiency_metrics['consumption_rate'] = metrics.items_consumed / metrics.elapsed_time
    
    if metrics.items_produced > 0:
        efficiency_metrics['consumption_ratio'] = metrics.items_consumed / metrics.items_produced
    
    efficiency_metrics['buffer_efficiency'] = 100 - metrics.buffer_utilization
    efficiency_metrics['backpressure_ratio'] = metrics.backpressure_events / max(1, metrics.items_produced)
    
    return efficiency_metrics