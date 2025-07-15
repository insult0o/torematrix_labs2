"""Bulk Operations Framework

High-performance batch processing for search and filter operations.
Enables efficient processing of large datasets with parallel execution,
memory optimization, and progress tracking.
"""

import asyncio
import time
import threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Union, Iterator, Tuple, Set
from enum import Enum
import logging
from contextlib import contextmanager

from torematrix.core.models.element import Element
from torematrix.ui.components.search.filters import FilterSet, FilterManager
from torematrix.ui.components.search.cache import get_cache_manager


logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of bulk operations"""
    SEARCH = "search"
    FILTER = "filter"
    INDEX = "index"
    TRANSFORM = "transform"
    VALIDATE = "validate"


class OperationStatus(Enum):
    """Operation execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OperationProgress:
    """Progress tracking for bulk operations"""
    total_items: int = 0
    processed_items: int = 0
    failed_items: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: OperationStatus = OperationStatus.PENDING
    current_phase: str = ""
    error_messages: List[str] = field(default_factory=list)
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage"""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100
    
    @property
    def duration_seconds(self) -> float:
        """Calculate operation duration"""
        end = self.end_time or time.time()
        return end - self.start_time
    
    @property
    def items_per_second(self) -> float:
        """Calculate processing rate"""
        duration = self.duration_seconds
        if duration == 0:
            return 0.0
        return self.processed_items / duration
    
    @property
    def estimated_time_remaining(self) -> float:
        """Estimate remaining time in seconds"""
        if self.processed_items == 0:
            return 0.0
        
        rate = self.items_per_second
        if rate == 0:
            return 0.0
        
        remaining_items = self.total_items - self.processed_items
        return remaining_items / rate


@dataclass
class BulkOperationConfig:
    """Configuration for bulk operations"""
    batch_size: int = 1000
    max_workers: int = 4
    use_processes: bool = False  # Use ProcessPoolExecutor instead of ThreadPoolExecutor
    enable_caching: bool = True
    cache_ttl_seconds: float = 300
    memory_limit_mb: int = 500
    progress_callback: Optional[Callable[[OperationProgress], None]] = None
    error_callback: Optional[Callable[[Exception, Any], None]] = None


class BulkOperationExecutor:
    """High-performance bulk operation executor"""
    
    def __init__(self, config: Optional[BulkOperationConfig] = None):
        """Initialize executor
        
        Args:
            config: Operation configuration
        """
        self.config = config or BulkOperationConfig()
        self.cache_manager = get_cache_manager()
        self._active_operations: Dict[str, OperationProgress] = {}
        self._operation_lock = threading.Lock()
        
        logger.info(f"BulkOperationExecutor initialized: batch_size={self.config.batch_size}, "
                   f"workers={self.config.max_workers}, processes={self.config.use_processes}")
    
    def execute_bulk_search(self,
                          queries: List[str],
                          search_function: Callable[[str], List[Element]],
                          operation_id: Optional[str] = None) -> Dict[str, List[Element]]:
        """Execute bulk search operations
        
        Args:
            queries: List of search queries
            search_function: Function to execute single search
            operation_id: Optional operation ID for tracking
            
        Returns:
            Dictionary mapping queries to results
        """
        operation_id = operation_id or f"bulk_search_{int(time.time())}"
        
        # Initialize progress tracking
        progress = OperationProgress(
            total_items=len(queries),
            status=OperationStatus.RUNNING,
            current_phase="Searching"
        )
        self._register_operation(operation_id, progress)
        
        try:
            # Process in batches
            results = {}
            batch_size = self.config.batch_size
            
            for i in range(0, len(queries), batch_size):
                batch = queries[i:i + batch_size]
                batch_results = self._execute_search_batch(batch, search_function)
                results.update(batch_results)
                
                # Update progress
                progress.processed_items = min(i + batch_size, len(queries))
                self._notify_progress(progress)
            
            # Mark as completed
            progress.status = OperationStatus.COMPLETED
            progress.end_time = time.time()
            self._notify_progress(progress)
            
            logger.info(f"Bulk search completed: {len(queries)} queries in "
                       f"{progress.duration_seconds:.2f}s")
            
            return results
            
        except Exception as e:
            progress.status = OperationStatus.FAILED
            progress.error_messages.append(str(e))
            progress.end_time = time.time()
            self._notify_progress(progress)
            self._notify_error(e, queries)
            raise
        
        finally:
            self._unregister_operation(operation_id)
    
    def execute_bulk_filter(self,
                          elements: List[Element],
                          filter_sets: List[FilterSet],
                          filter_manager: FilterManager,
                          operation_id: Optional[str] = None) -> Dict[str, List[Element]]:
        """Execute bulk filter operations
        
        Args:
            elements: Elements to filter
            filter_sets: Filter sets to apply
            filter_manager: Filter manager instance
            operation_id: Optional operation ID for tracking
            
        Returns:
            Dictionary mapping filter set IDs to filtered results
        """
        operation_id = operation_id or f"bulk_filter_{int(time.time())}"
        
        # Initialize progress tracking
        progress = OperationProgress(
            total_items=len(filter_sets),
            status=OperationStatus.RUNNING,
            current_phase="Filtering"
        )
        self._register_operation(operation_id, progress)
        
        try:
            results = {}
            
            # Check cache first
            if self.config.enable_caching:
                cached_results, remaining_filters = self._check_filter_cache(
                    elements, filter_sets
                )
                results.update(cached_results)
                filter_sets = remaining_filters
                progress.processed_items = len(cached_results)
                self._notify_progress(progress)
            
            if filter_sets:
                # Process remaining filters in parallel
                batch_results = self._execute_filter_parallel(
                    elements, filter_sets, filter_manager, progress
                )
                results.update(batch_results)
                
                # Cache new results
                if self.config.enable_caching:
                    self._cache_filter_results(batch_results, elements)
            
            # Mark as completed
            progress.status = OperationStatus.COMPLETED
            progress.end_time = time.time()
            self._notify_progress(progress)
            
            logger.info(f"Bulk filter completed: {len(filter_sets)} filters on "
                       f"{len(elements)} elements in {progress.duration_seconds:.2f}s")
            
            return results
            
        except Exception as e:
            progress.status = OperationStatus.FAILED
            progress.error_messages.append(str(e))
            progress.end_time = time.time()
            self._notify_progress(progress)
            self._notify_error(e, filter_sets)
            raise
        
        finally:
            self._unregister_operation(operation_id)
    
    def execute_bulk_operation(self,
                             items: List[Any],
                             operation_function: Callable[[Any], Any],
                             operation_type: OperationType,
                             operation_id: Optional[str] = None) -> List[Any]:
        """Execute generic bulk operation
        
        Args:
            items: Items to process
            operation_function: Function to apply to each item
            operation_type: Type of operation
            operation_id: Optional operation ID for tracking
            
        Returns:
            List of operation results
        """
        operation_id = operation_id or f"bulk_{operation_type.value}_{int(time.time())}"
        
        # Initialize progress tracking
        progress = OperationProgress(
            total_items=len(items),
            status=OperationStatus.RUNNING,
            current_phase=f"Processing {operation_type.value}"
        )
        self._register_operation(operation_id, progress)
        
        try:
            results = []
            batch_size = self.config.batch_size
            
            # Process in parallel batches
            executor_class = ProcessPoolExecutor if self.config.use_processes else ThreadPoolExecutor
            
            with executor_class(max_workers=self.config.max_workers) as executor:
                # Submit batches
                futures = []
                for i in range(0, len(items), batch_size):
                    batch = items[i:i + batch_size]
                    future = executor.submit(self._process_batch, batch, operation_function)
                    futures.append(future)
                
                # Collect results
                for future in as_completed(futures):
                    try:
                        batch_results = future.result()
                        results.extend(batch_results)
                        
                        # Update progress
                        progress.processed_items = len(results)
                        self._notify_progress(progress)
                        
                    except Exception as e:
                        progress.failed_items += batch_size
                        progress.error_messages.append(str(e))
                        logger.warning(f"Batch processing failed: {e}")
            
            # Mark as completed
            progress.status = OperationStatus.COMPLETED
            progress.end_time = time.time()
            self._notify_progress(progress)
            
            logger.info(f"Bulk {operation_type.value} completed: {len(items)} items in "
                       f"{progress.duration_seconds:.2f}s")
            
            return results
            
        except Exception as e:
            progress.status = OperationStatus.FAILED
            progress.error_messages.append(str(e))
            progress.end_time = time.time()
            self._notify_progress(progress)
            self._notify_error(e, items)
            raise
        
        finally:
            self._unregister_operation(operation_id)
    
    def stream_bulk_operation(self,
                            items: List[Any],
                            operation_function: Callable[[Any], Any],
                            operation_type: OperationType,
                            operation_id: Optional[str] = None) -> Iterator[Any]:
        """Stream bulk operation results as they become available
        
        Args:
            items: Items to process
            operation_function: Function to apply to each item
            operation_type: Type of operation
            operation_id: Optional operation ID for tracking
            
        Yields:
            Operation results as they complete
        """
        operation_id = operation_id or f"stream_{operation_type.value}_{int(time.time())}"
        
        # Initialize progress tracking
        progress = OperationProgress(
            total_items=len(items),
            status=OperationStatus.RUNNING,
            current_phase=f"Streaming {operation_type.value}"
        )
        self._register_operation(operation_id, progress)
        
        try:
            batch_size = self.config.batch_size
            executor_class = ProcessPoolExecutor if self.config.use_processes else ThreadPoolExecutor
            
            with executor_class(max_workers=self.config.max_workers) as executor:
                # Submit all batches
                future_to_batch = {}
                for i in range(0, len(items), batch_size):
                    batch = items[i:i + batch_size]
                    future = executor.submit(self._process_batch, batch, operation_function)
                    future_to_batch[future] = i
                
                # Yield results as they complete
                for future in as_completed(future_to_batch):
                    try:
                        batch_results = future.result()
                        for result in batch_results:
                            yield result
                        
                        # Update progress
                        progress.processed_items += len(batch_results)
                        self._notify_progress(progress)
                        
                    except Exception as e:
                        batch_index = future_to_batch[future]
                        progress.failed_items += min(batch_size, len(items) - batch_index)
                        progress.error_messages.append(str(e))
                        logger.warning(f"Batch {batch_index} failed: {e}")
            
            # Mark as completed
            progress.status = OperationStatus.COMPLETED
            progress.end_time = time.time()
            self._notify_progress(progress)
            
        except Exception as e:
            progress.status = OperationStatus.FAILED
            progress.error_messages.append(str(e))
            progress.end_time = time.time()
            self._notify_progress(progress)
            self._notify_error(e, items)
            raise
        
        finally:
            self._unregister_operation(operation_id)
    
    def get_operation_progress(self, operation_id: str) -> Optional[OperationProgress]:
        """Get progress for specific operation
        
        Args:
            operation_id: Operation ID
            
        Returns:
            Progress information or None if not found
        """
        with self._operation_lock:
            return self._active_operations.get(operation_id)
    
    def cancel_operation(self, operation_id: str) -> bool:
        """Cancel active operation
        
        Args:
            operation_id: Operation ID to cancel
            
        Returns:
            True if operation was cancelled
        """
        with self._operation_lock:
            if operation_id in self._active_operations:
                progress = self._active_operations[operation_id]
                progress.status = OperationStatus.CANCELLED
                progress.end_time = time.time()
                self._notify_progress(progress)
                return True
            return False
    
    def get_active_operations(self) -> Dict[str, OperationProgress]:
        """Get all active operations"""
        with self._operation_lock:
            return self._active_operations.copy()
    
    def _execute_search_batch(self,
                            queries: List[str],
                            search_function: Callable[[str], List[Element]]) -> Dict[str, List[Element]]:
        """Execute search batch"""
        results = {}
        
        for query in queries:
            try:
                # Check cache first
                if self.config.enable_caching:
                    cache_key = self.cache_manager.search_results.create_key("search", query)
                    cached_result = self.cache_manager.search_results.get(cache_key)
                    if cached_result is not None:
                        results[query] = cached_result
                        continue
                
                # Execute search
                search_results = search_function(query)
                results[query] = search_results
                
                # Cache result
                if self.config.enable_caching:
                    cache_key = self.cache_manager.search_results.create_key("search", query)
                    tags = {f"query:{query}"}
                    self.cache_manager.search_results.put(
                        cache_key, search_results,
                        ttl_seconds=self.config.cache_ttl_seconds,
                        tags=tags
                    )
                
            except Exception as e:
                logger.warning(f"Search failed for query '{query}': {e}")
                results[query] = []
        
        return results
    
    def _execute_filter_parallel(self,
                                elements: List[Element],
                                filter_sets: List[FilterSet],
                                filter_manager: FilterManager,
                                progress: OperationProgress) -> Dict[str, List[Element]]:
        """Execute filters in parallel"""
        results = {}
        executor_class = ProcessPoolExecutor if self.config.use_processes else ThreadPoolExecutor
        
        with executor_class(max_workers=self.config.max_workers) as executor:
            # Submit filter tasks
            future_to_filter = {}
            for filter_set in filter_sets:
                future = executor.submit(
                    self._apply_single_filter,
                    elements, filter_set, filter_manager
                )
                future_to_filter[future] = filter_set
            
            # Collect results
            for future in as_completed(future_to_filter):
                filter_set = future_to_filter[future]
                try:
                    filtered_elements = future.result()
                    results[filter_set.filter_set_id] = filtered_elements
                    
                    # Update progress
                    progress.processed_items += 1
                    self._notify_progress(progress)
                    
                except Exception as e:
                    logger.warning(f"Filter failed for {filter_set.filter_set_id}: {e}")
                    results[filter_set.filter_set_id] = []
                    progress.failed_items += 1
        
        return results
    
    def _apply_single_filter(self,
                           elements: List[Element],
                           filter_set: FilterSet,
                           filter_manager: FilterManager) -> List[Element]:
        """Apply single filter to elements"""
        return filter_manager.filter_elements(elements, filter_set)
    
    def _check_filter_cache(self,
                          elements: List[Element],
                          filter_sets: List[FilterSet]) -> Tuple[Dict[str, List[Element]], List[FilterSet]]:
        """Check cache for filter results"""
        if not self.config.enable_caching:
            return {}, filter_sets
        
        cached_results = {}
        remaining_filters = []
        
        # Create element signature for cache key
        element_signature = self._create_element_signature(elements)
        
        for filter_set in filter_sets:
            cache_key = self.cache_manager.filter_results.create_key(
                "filter", element_signature, filter_set.filter_set_id
            )
            
            cached_result = self.cache_manager.filter_results.get(cache_key)
            if cached_result is not None:
                cached_results[filter_set.filter_set_id] = cached_result
            else:
                remaining_filters.append(filter_set)
        
        return cached_results, remaining_filters
    
    def _cache_filter_results(self,
                            results: Dict[str, List[Element]],
                            original_elements: List[Element]) -> None:
        """Cache filter results"""
        if not self.config.enable_caching:
            return
        
        element_signature = self._create_element_signature(original_elements)
        
        for filter_set_id, filtered_elements in results.items():
            cache_key = self.cache_manager.filter_results.create_key(
                "filter", element_signature, filter_set_id
            )
            
            tags = {f"filter:{filter_set_id}", "elements"}
            self.cache_manager.filter_results.put(
                cache_key, filtered_elements,
                ttl_seconds=self.config.cache_ttl_seconds,
                tags=tags
            )
    
    def _create_element_signature(self, elements: List[Element]) -> str:
        """Create signature for element list"""
        # Use hash of element IDs and modification times
        signature_data = []
        for element in elements[:100]:  # Limit to first 100 for performance
            signature_data.append(element.element_id)
        
        signature_str = "|".join(signature_data)
        return str(hash(signature_str))
    
    def _process_batch(self, batch: List[Any], operation_function: Callable[[Any], Any]) -> List[Any]:
        """Process a batch of items"""
        results = []
        for item in batch:
            try:
                result = operation_function(item)
                results.append(result)
            except Exception as e:
                logger.warning(f"Item processing failed: {e}")
                results.append(None)  # Or handle differently based on requirements
        return results
    
    def _register_operation(self, operation_id: str, progress: OperationProgress) -> None:
        """Register active operation"""
        with self._operation_lock:
            self._active_operations[operation_id] = progress
    
    def _unregister_operation(self, operation_id: str) -> None:
        """Unregister completed operation"""
        with self._operation_lock:
            self._active_operations.pop(operation_id, None)
    
    def _notify_progress(self, progress: OperationProgress) -> None:
        """Notify progress callback"""
        if self.config.progress_callback:
            try:
                self.config.progress_callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
    
    def _notify_error(self, error: Exception, context: Any) -> None:
        """Notify error callback"""
        if self.config.error_callback:
            try:
                self.config.error_callback(error, context)
            except Exception as e:
                logger.warning(f"Error callback error: {e}")


# Global bulk operation executor
_bulk_executor: Optional[BulkOperationExecutor] = None


def get_bulk_executor() -> BulkOperationExecutor:
    """Get global bulk operation executor"""
    global _bulk_executor
    if _bulk_executor is None:
        _bulk_executor = BulkOperationExecutor()
    return _bulk_executor


@contextmanager
def bulk_operation_context(config: Optional[BulkOperationConfig] = None):
    """Context manager for bulk operations with custom configuration"""
    old_executor = _bulk_executor
    global _bulk_executor
    
    try:
        _bulk_executor = BulkOperationExecutor(config)
        yield _bulk_executor
    finally:
        _bulk_executor = old_executor