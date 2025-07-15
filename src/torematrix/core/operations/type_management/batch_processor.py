"""Batch Processing Engine

Chunked processing for large datasets with memory management and progress tracking.
Provides efficient parallel processing with resource optimization.
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed, Future
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from queue import Queue, Empty
from typing import Dict, List, Optional, Any, Callable, Union, Iterator, Tuple
import psutil
import gc

logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """Processing modes for batch operations"""
    SEQUENTIAL = "sequential"       # Process items one by one
    THREADED = "threaded"          # Use thread pool for I/O bound tasks
    MULTIPROCESS = "multiprocess"  # Use process pool for CPU bound tasks
    HYBRID = "hybrid"              # Combine threading and multiprocessing


class BatchStrategy(Enum):
    """Strategies for batch sizing"""
    FIXED = "fixed"               # Fixed batch size
    ADAPTIVE = "adaptive"         # Adapt based on system resources
    MEMORY_BASED = "memory_based" # Size based on memory usage
    TIME_BASED = "time_based"     # Size based on processing time


@dataclass
class BatchOptions:
    """Configuration options for batch processing"""
    batch_size: int = 1000
    max_workers: int = 4
    processing_mode: ProcessingMode = ProcessingMode.THREADED
    batch_strategy: BatchStrategy = BatchStrategy.ADAPTIVE
    memory_limit_mb: int = 1024
    timeout_seconds: Optional[int] = None
    retry_attempts: int = 3
    retry_delay: float = 1.0
    checkpoint_interval: int = 100
    enable_progress_callback: bool = True
    preserve_order: bool = False


@dataclass
class BatchStats:
    """Statistics for batch processing"""
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0
    successful_items: int = 0
    current_batch: int = 0
    total_batches: int = 0
    processing_rate: float = 0.0  # items per second
    estimated_time_remaining: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage"""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.processed_items == 0:
            return 0.0
        return (self.successful_items / self.processed_items) * 100.0


@dataclass
class BatchResult:
    """Result of batch processing operation"""
    operation_id: str
    total_items: int
    successful_results: List[Any]
    failed_results: List[Tuple[Any, Exception]]
    skipped_items: List[Any]
    stats: BatchStats
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    @property
    def duration_seconds(self) -> float:
        """Calculate processing duration"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def is_successful(self) -> bool:
        """Check if processing was successful"""
        return self.stats.failed_items == 0


class BatchProcessor:
    """Chunked processing engine for large datasets
    
    Provides efficient processing with:
    - Adaptive batch sizing based on system resources
    - Multiple processing modes (threaded, multiprocess, hybrid)
    - Memory management and resource monitoring
    - Progress tracking and checkpointing
    - Error handling and retry mechanisms
    - Performance optimization
    """
    
    def __init__(self, 
                 batch_size: int = 1000,
                 max_workers: int = 4,
                 memory_limit_mb: int = 1024):
        """Initialize batch processor
        
        Args:
            batch_size: Default batch size
            max_workers: Maximum number of worker threads/processes
            memory_limit_mb: Memory limit in megabytes
        """
        self.default_batch_size = batch_size
        self.max_workers = max_workers
        self.memory_limit_mb = memory_limit_mb
        
        self._active_operations: Dict[str, BatchResult] = {}
        self._operation_lock = threading.RLock()
        self._system_monitor = SystemResourceMonitor()
        
        logger.info(f"BatchProcessor initialized: batch_size={batch_size}, "
                   f"max_workers={max_workers}, memory_limit={memory_limit_mb}MB")
    
    def process_in_batches(self, 
                          items: List[Any], 
                          operation: Callable,
                          options: Optional[BatchOptions] = None,
                          progress_callback: Optional[Callable] = None) -> BatchResult:
        """Process items in batches with the specified operation
        
        Args:
            items: List of items to process
            operation: Function to apply to each item
            options: Batch processing options
            progress_callback: Optional progress callback function
            
        Returns:
            BatchResult with processing results and statistics
            
        Raises:
            ValueError: If items list is empty or operation is invalid
            RuntimeError: If processing fails
        """
        if not items:
            raise ValueError("Items list cannot be empty")
        
        if not callable(operation):
            raise ValueError("Operation must be a callable function")
        
        options = options or BatchOptions()
        operation_id = f"batch_{int(time.time())}_{id(items)}"
        
        logger.info(f"Starting batch processing {operation_id}: {len(items)} items")
        
        # Initialize result
        result = BatchResult(
            operation_id=operation_id,
            total_items=len(items),
            successful_results=[],
            failed_results=[],
            skipped_items=[],
            stats=BatchStats(total_items=len(items))
        )
        
        with self._operation_lock:
            self._active_operations[operation_id] = result
        
        try:
            # Optimize batch configuration
            optimized_options = self._optimize_batch_configuration(items, options)
            
            # Create batches
            batches = self._create_batches(items, optimized_options)
            result.stats.total_batches = len(batches)
            
            logger.debug(f"Created {len(batches)} batches with optimized configuration")
            
            # Process batches based on mode
            if optimized_options.processing_mode == ProcessingMode.SEQUENTIAL:
                self._process_sequential(batches, operation, optimized_options, result, progress_callback)
            elif optimized_options.processing_mode == ProcessingMode.THREADED:
                self._process_threaded(batches, operation, optimized_options, result, progress_callback)
            elif optimized_options.processing_mode == ProcessingMode.MULTIPROCESS:
                self._process_multiprocess(batches, operation, optimized_options, result, progress_callback)
            elif optimized_options.processing_mode == ProcessingMode.HYBRID:
                self._process_hybrid(batches, operation, optimized_options, result, progress_callback)
            
            # Finalize results
            result.stats.successful_items = len(result.successful_results)
            result.stats.failed_items = len(result.failed_results)
            result.stats.skipped_items = len(result.skipped_items)
            result.stats.processed_items = (result.stats.successful_items + 
                                          result.stats.failed_items + 
                                          result.stats.skipped_items)
            
        except Exception as e:
            logger.error(f"Batch processing {operation_id} failed: {e}")
            raise RuntimeError(f"Batch processing failed: {e}")
        
        finally:
            result.end_time = datetime.now()
            with self._operation_lock:
                self._active_operations.pop(operation_id, None)
        
        logger.info(f"Batch processing {operation_id} completed: "
                   f"{result.stats.successful_items}/{result.total_items} successful")
        return result
    
    def estimate_processing_time(self, 
                               item_count: int, 
                               operation_type: str = "default") -> float:
        """Estimate processing time for given number of items
        
        Args:
            item_count: Number of items to process
            operation_type: Type of operation for estimation
            
        Returns:
            Estimated processing time in seconds
        """
        # Base processing rates (items per second) for different operation types
        base_rates = {
            "default": 1000,
            "type_conversion": 500,
            "validation": 2000,
            "data_transformation": 200,
            "file_processing": 50
        }
        
        rate = base_rates.get(operation_type, base_rates["default"])
        
        # Adjust for system resources
        cpu_count = psutil.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        # Simple heuristic adjustment
        resource_multiplier = min(cpu_count / 4, memory_gb / 8, 2.0)
        adjusted_rate = rate * resource_multiplier
        
        estimated_time = item_count / adjusted_rate
        return max(estimated_time, 0.1)  # Minimum 0.1 seconds
    
    def optimize_batch_size(self, 
                          item_count: int, 
                          memory_limit_mb: int,
                          item_size_estimate: int = 1024) -> int:
        """Optimize batch size based on system resources
        
        Args:
            item_count: Total number of items
            memory_limit_mb: Memory limit in megabytes
            item_size_estimate: Estimated size per item in bytes
            
        Returns:
            Optimized batch size
        """
        # Available memory
        available_memory = psutil.virtual_memory().available
        memory_limit_bytes = memory_limit_mb * 1024 * 1024
        usable_memory = min(available_memory * 0.8, memory_limit_bytes)  # Use 80% of available
        
        # Calculate batch size based on memory
        memory_based_size = int(usable_memory / item_size_estimate)
        
        # Consider CPU cores for parallel processing
        cpu_based_size = psutil.cpu_count() * 100  # 100 items per core as baseline
        
        # Combine factors
        optimal_size = min(memory_based_size, cpu_based_size * 2)
        
        # Apply reasonable bounds
        min_batch_size = 10
        max_batch_size = 10000
        
        optimal_size = max(min_batch_size, min(optimal_size, max_batch_size))
        
        logger.debug(f"Optimized batch size: {optimal_size} (memory: {memory_based_size}, "
                    f"cpu: {cpu_based_size}, available_mem: {available_memory/1024/1024:.1f}MB)")
        
        return optimal_size
    
    def get_active_operations(self) -> List[str]:
        """Get list of currently active operation IDs"""
        with self._operation_lock:
            return list(self._active_operations.keys())
    
    def get_operation_status(self, operation_id: str) -> Optional[BatchResult]:
        """Get status of a batch operation"""
        with self._operation_lock:
            return self._active_operations.get(operation_id)
    
    def _optimize_batch_configuration(self, items: List[Any], options: BatchOptions) -> BatchOptions:
        """Optimize batch configuration based on system resources and data"""
        optimized = BatchOptions(
            batch_size=options.batch_size,
            max_workers=options.max_workers,
            processing_mode=options.processing_mode,
            batch_strategy=options.batch_strategy,
            memory_limit_mb=options.memory_limit_mb,
            timeout_seconds=options.timeout_seconds,
            retry_attempts=options.retry_attempts,
            retry_delay=options.retry_delay,
            checkpoint_interval=options.checkpoint_interval,
            enable_progress_callback=options.enable_progress_callback,
            preserve_order=options.preserve_order
        )
        
        # Optimize batch size if using adaptive strategy
        if options.batch_strategy == BatchStrategy.ADAPTIVE:
            optimized.batch_size = self.optimize_batch_size(
                len(items), 
                options.memory_limit_mb
            )
        
        # Optimize worker count based on system resources
        cpu_count = psutil.cpu_count()
        if options.processing_mode == ProcessingMode.THREADED:
            optimized.max_workers = min(options.max_workers, cpu_count * 2)
        elif options.processing_mode == ProcessingMode.MULTIPROCESS:
            optimized.max_workers = min(options.max_workers, cpu_count)
        
        return optimized
    
    def _create_batches(self, items: List[Any], options: BatchOptions) -> List[List[Any]]:
        """Create batches from items list"""
        batches = []
        batch_size = options.batch_size
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batches.append(batch)
        
        return batches
    
    def _process_sequential(self, 
                          batches: List[List[Any]], 
                          operation: Callable,
                          options: BatchOptions,
                          result: BatchResult,
                          progress_callback: Optional[Callable]) -> None:
        """Process batches sequentially"""
        logger.debug("Processing batches sequentially")
        
        for batch_idx, batch in enumerate(batches):
            self._process_single_batch(batch, operation, batch_idx, options, result)
            
            if progress_callback and options.enable_progress_callback:
                progress = (batch_idx + 1) / len(batches)
                progress_callback(progress, f"Processed batch {batch_idx + 1}/{len(batches)}")
            
            # Update statistics
            self._update_batch_stats(result.stats, batch_idx, len(batches))
    
    def _process_threaded(self, 
                        batches: List[List[Any]], 
                        operation: Callable,
                        options: BatchOptions,
                        result: BatchResult,
                        progress_callback: Optional[Callable]) -> None:
        """Process batches using thread pool"""
        logger.debug(f"Processing batches with {options.max_workers} threads")
        
        with ThreadPoolExecutor(max_workers=options.max_workers) as executor:
            # Submit all batches
            future_to_batch = {
                executor.submit(self._process_single_batch, batch, operation, idx, options, result): idx
                for idx, batch in enumerate(batches)
            }
            
            # Process completed batches
            completed_batches = 0
            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                
                try:
                    future.result()  # This will raise exception if batch failed
                    completed_batches += 1
                    
                    if progress_callback and options.enable_progress_callback:
                        progress = completed_batches / len(batches)
                        progress_callback(progress, f"Completed batch {completed_batches}/{len(batches)}")
                    
                except Exception as e:
                    logger.error(f"Batch {batch_idx} failed: {e}")
                    # Error handling is done in _process_single_batch
                
                # Update statistics
                self._update_batch_stats(result.stats, completed_batches - 1, len(batches))
    
    def _process_multiprocess(self, 
                            batches: List[List[Any]], 
                            operation: Callable,
                            options: BatchOptions,
                            result: BatchResult,
                            progress_callback: Optional[Callable]) -> None:
        """Process batches using process pool"""
        logger.debug(f"Processing batches with {options.max_workers} processes")
        
        # Note: Multiprocessing requires special handling for sharing results
        # This is a simplified implementation
        
        with ProcessPoolExecutor(max_workers=options.max_workers) as executor:
            # Submit all batches
            futures = []
            for idx, batch in enumerate(batches):
                future = executor.submit(self._process_batch_for_multiprocess, batch, operation)
                futures.append((future, idx))
            
            # Process completed batches
            completed_batches = 0
            for future, batch_idx in futures:
                try:
                    batch_results = future.result()
                    self._merge_batch_results(batch_results, result)
                    completed_batches += 1
                    
                    if progress_callback and options.enable_progress_callback:
                        progress = completed_batches / len(batches)
                        progress_callback(progress, f"Completed batch {completed_batches}/{len(batches)}")
                    
                except Exception as e:
                    logger.error(f"Batch {batch_idx} failed: {e}")
                
                # Update statistics
                self._update_batch_stats(result.stats, completed_batches - 1, len(batches))
    
    def _process_hybrid(self, 
                       batches: List[List[Any]], 
                       operation: Callable,
                       options: BatchOptions,
                       result: BatchResult,
                       progress_callback: Optional[Callable]) -> None:
        """Process batches using hybrid approach (threads + processes)"""
        logger.debug("Processing batches with hybrid approach")
        
        # For hybrid mode, use threads for I/O bound operations
        # and processes for CPU bound operations (simplified implementation)
        self._process_threaded(batches, operation, options, result, progress_callback)
    
    def _process_single_batch(self, 
                            batch: List[Any], 
                            operation: Callable,
                            batch_idx: int,
                            options: BatchOptions,
                            result: BatchResult) -> None:
        """Process a single batch of items"""
        start_time = time.time()
        
        for item in batch:
            try:
                # Apply operation with retry logic
                item_result = self._execute_with_retry(operation, item, options)
                result.successful_results.append(item_result)
                
            except Exception as e:
                logger.warning(f"Item processing failed in batch {batch_idx}: {e}")
                result.failed_results.append((item, e))
        
        # Update processing rate
        batch_time = time.time() - start_time
        if batch_time > 0:
            rate = len(batch) / batch_time
            result.stats.processing_rate = rate
        
        # Checkpoint if needed
        if options.checkpoint_interval > 0 and batch_idx % options.checkpoint_interval == 0:
            self._create_checkpoint(result, batch_idx)
        
        # Memory management
        if batch_idx % 10 == 0:  # Every 10 batches
            self._manage_memory(result.stats)
    
    def _process_batch_for_multiprocess(self, 
                                       batch: List[Any], 
                                       operation: Callable) -> Dict[str, Any]:
        """Process batch for multiprocessing (returns serializable results)"""
        successful = []
        failed = []
        
        for item in batch:
            try:
                item_result = operation(item)
                successful.append(item_result)
            except Exception as e:
                failed.append((item, str(e)))  # Convert exception to string for serialization
        
        return {
            'successful': successful,
            'failed': failed
        }
    
    def _merge_batch_results(self, batch_results: Dict[str, Any], result: BatchResult) -> None:
        """Merge batch results from multiprocessing"""
        result.successful_results.extend(batch_results['successful'])
        
        for item, error_msg in batch_results['failed']:
            result.failed_results.append((item, RuntimeError(error_msg)))
    
    def _execute_with_retry(self, 
                          operation: Callable, 
                          item: Any, 
                          options: BatchOptions) -> Any:
        """Execute operation with retry logic"""
        last_exception = None
        
        for attempt in range(options.retry_attempts):
            try:
                return operation(item)
            except Exception as e:
                last_exception = e
                if attempt < options.retry_attempts - 1:
                    time.sleep(options.retry_delay * (2 ** attempt))  # Exponential backoff
                    logger.debug(f"Retrying operation (attempt {attempt + 2}/{options.retry_attempts})")
        
        raise last_exception
    
    def _update_batch_stats(self, stats: BatchStats, current_batch: int, total_batches: int) -> None:
        """Update batch processing statistics"""
        stats.current_batch = current_batch + 1
        stats.total_batches = total_batches
        
        # Update system resource usage
        memory_info = psutil.virtual_memory()
        stats.memory_usage_mb = (memory_info.total - memory_info.available) / (1024 * 1024)
        stats.cpu_usage_percent = psutil.cpu_percent(interval=None)
        
        # Estimate time remaining
        if stats.processing_rate > 0:
            remaining_items = stats.total_items - stats.processed_items
            stats.estimated_time_remaining = remaining_items / stats.processing_rate
    
    def _create_checkpoint(self, result: BatchResult, batch_idx: int) -> None:
        """Create processing checkpoint"""
        checkpoint = {
            'batch_idx': batch_idx,
            'timestamp': datetime.now().isoformat(),
            'processed_items': result.stats.processed_items,
            'successful_items': len(result.successful_results),
            'failed_items': len(result.failed_results)
        }
        result.checkpoints.append(checkpoint)
        logger.debug(f"Created checkpoint at batch {batch_idx}")
    
    def _manage_memory(self, stats: BatchStats) -> None:
        """Manage memory usage during processing"""
        memory_info = psutil.virtual_memory()
        memory_usage_mb = (memory_info.total - memory_info.available) / (1024 * 1024)
        
        if memory_usage_mb > self.memory_limit_mb:
            logger.warning(f"Memory usage ({memory_usage_mb:.1f}MB) exceeds limit ({self.memory_limit_mb}MB)")
            
            # Force garbage collection
            gc.collect()
            
            # Update stats
            stats.memory_usage_mb = memory_usage_mb


class SystemResourceMonitor:
    """Monitor system resources during processing"""
    
    def __init__(self):
        self.start_time = time.time()
        self.initial_memory = psutil.virtual_memory().used
    
    def get_resource_usage(self) -> Dict[str, float]:
        """Get current resource usage"""
        memory_info = psutil.virtual_memory()
        
        return {
            'cpu_percent': psutil.cpu_percent(interval=None),
            'memory_percent': memory_info.percent,
            'memory_used_mb': memory_info.used / (1024 * 1024),
            'memory_available_mb': memory_info.available / (1024 * 1024),
            'uptime_seconds': time.time() - self.start_time
        }