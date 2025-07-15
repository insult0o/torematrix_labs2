"""Parallel Processing Optimization

Advanced parallel processing for search and filter operations using
multiprocessing, threading, and async patterns for maximum performance
on multi-core systems.
"""

import asyncio
import threading
import multiprocessing as mp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, Union, Tuple, Iterator
from enum import Enum
import time
import logging
import queue
import pickle
from functools import partial

from torematrix.core.models.element import Element
from torematrix.ui.components.search.filters import FilterSet, FilterManager
from torematrix.ui.components.search.performance import get_performance_monitor, time_operation


logger = logging.getLogger(__name__)


class ProcessingMode(Enum):
    """Processing execution modes"""
    SEQUENTIAL = "sequential"
    THREADED = "threaded"
    MULTIPROCESS = "multiprocess"
    ASYNC = "async"
    HYBRID = "hybrid"


@dataclass
class ProcessingConfig:
    """Configuration for parallel processing"""
    mode: ProcessingMode = ProcessingMode.THREADED
    max_workers: int = 4
    chunk_size: int = 1000
    memory_limit_mb: int = 200
    timeout_seconds: float = 30.0
    enable_progress: bool = True
    enable_metrics: bool = True


@dataclass
class ProcessingResult:
    """Result from parallel processing operation"""
    results: Any
    execution_time: float
    worker_count: int
    chunks_processed: int
    success: bool = True
    error_message: Optional[str] = None
    memory_peak_mb: float = 0.0


def serialize_filter_set(filter_set: FilterSet) -> Dict[str, Any]:
    """Serialize FilterSet for multiprocessing"""
    return {
        'filter_set_id': filter_set.filter_set_id,
        'name': filter_set.name,
        'description': filter_set.description,
        'groups': [
            {
                'group_id': group.group_id,
                'logic': group.logic.value,
                'enabled': group.enabled,
                'conditions': [
                    {
                        'filter_id': cond.filter_id,
                        'filter_type': cond.filter_type.value,
                        'field_name': cond.field_name,
                        'operator': cond.operator.value,
                        'value': {
                            'value': cond.value.value,
                            'data_type': cond.value.data_type
                        },
                        'enabled': cond.enabled
                    }
                    for cond in group.conditions
                ]
            }
            for group in filter_set.groups
        ],
        'combination_logic': filter_set.combination_logic.value,
        'created_date': filter_set.created_date,
        'modified_date': filter_set.modified_date,
        'is_preset': filter_set.is_preset,
        'tags': list(filter_set.tags)
    }


def deserialize_filter_set(data: Dict[str, Any]) -> FilterSet:
    """Deserialize FilterSet from multiprocessing"""
    from torematrix.ui.components.search.filters import (
        FilterSet, FilterGroup, FilterCondition, FilterValue,
        FilterType, FilterOperator, FilterLogic
    )
    
    # Create filter set
    filter_set = FilterSet(
        filter_set_id=data['filter_set_id'],
        name=data['name'],
        description=data['description'],
        combination_logic=FilterLogic(data['combination_logic']),
        created_date=data['created_date'],
        modified_date=data['modified_date'],
        is_preset=data['is_preset'],
        tags=set(data['tags'])
    )
    
    # Add groups
    for group_data in data['groups']:
        group = FilterGroup(
            group_id=group_data['group_id'],
            logic=FilterLogic(group_data['logic']),
            enabled=group_data['enabled']
        )
        
        # Add conditions
        for cond_data in group_data['conditions']:
            condition = FilterCondition(
                filter_id=cond_data['filter_id'],
                filter_type=FilterType(cond_data['filter_type']),
                field_name=cond_data['field_name'],
                operator=FilterOperator(cond_data['operator']),
                value=FilterValue(
                    cond_data['value']['value'],
                    cond_data['value']['data_type']
                ),
                enabled=cond_data['enabled']
            )
            group.add_condition(condition)
        
        filter_set.add_group(group)
    
    return filter_set


def apply_filter_parallel_worker(args: Tuple[List[Element], Dict[str, Any]]) -> List[Element]:
    """Worker function for parallel filter application"""
    elements, filter_data = args
    
    try:
        # Deserialize filter set
        filter_set = deserialize_filter_set(filter_data)
        
        # Create temporary filter manager
        from torematrix.ui.components.search.filters import FilterManager
        filter_manager = FilterManager()
        
        # Apply filter
        return filter_manager.filter_elements(elements, filter_set)
        
    except Exception as e:
        logger.error(f"Parallel filter worker failed: {e}")
        return []


def search_parallel_worker(args: Tuple[List[Element], str, Dict[str, Any]]) -> List[Element]:
    """Worker function for parallel search"""
    elements, query, search_config = args
    
    try:
        # Simple text search implementation for parallel processing
        results = []
        query_lower = query.lower()
        
        for element in elements:
            if (query_lower in element.text.lower() or
                query_lower in element.element_type.value.lower()):
                results.append(element)
        
        return results
        
    except Exception as e:
        logger.error(f"Parallel search worker failed: {e}")
        return []


class ParallelFilterProcessor:
    """High-performance parallel filter processor"""
    
    def __init__(self, config: Optional[ProcessingConfig] = None):
        """Initialize processor
        
        Args:
            config: Processing configuration
        """
        self.config = config or ProcessingConfig()
        self.performance_monitor = get_performance_monitor()
        
        # Determine optimal worker count
        self.optimal_workers = min(
            self.config.max_workers,
            mp.cpu_count(),
            4  # Reasonable upper limit
        )
        
        logger.info(f"ParallelFilterProcessor initialized: mode={self.config.mode.value}, "
                   f"workers={self.optimal_workers}")
    
    def filter_elements_parallel(self,
                                elements: List[Element],
                                filter_sets: List[FilterSet],
                                filter_manager: FilterManager) -> Dict[str, List[Element]]:
        """Apply multiple filters to elements in parallel
        
        Args:
            elements: Elements to filter
            filter_sets: Filter sets to apply
            filter_manager: Filter manager instance
            
        Returns:
            Dictionary mapping filter set IDs to results
        """
        operation_name = "parallel_filter"
        
        with time_operation(operation_name, {'mode': self.config.mode.value}):
            if self.config.mode == ProcessingMode.SEQUENTIAL:
                return self._filter_sequential(elements, filter_sets, filter_manager)
            elif self.config.mode == ProcessingMode.THREADED:
                return self._filter_threaded(elements, filter_sets, filter_manager)
            elif self.config.mode == ProcessingMode.MULTIPROCESS:
                return self._filter_multiprocess(elements, filter_sets)
            elif self.config.mode == ProcessingMode.ASYNC:
                return asyncio.run(self._filter_async(elements, filter_sets, filter_manager))
            elif self.config.mode == ProcessingMode.HYBRID:
                return self._filter_hybrid(elements, filter_sets, filter_manager)
            else:
                raise ValueError(f"Unsupported processing mode: {self.config.mode}")
    
    def search_elements_parallel(self,
                                elements: List[Element],
                                queries: List[str]) -> Dict[str, List[Element]]:
        """Search elements with multiple queries in parallel
        
        Args:
            elements: Elements to search
            queries: Search queries
            
        Returns:
            Dictionary mapping queries to results
        """
        operation_name = "parallel_search"
        
        with time_operation(operation_name, {'mode': self.config.mode.value}):
            if self.config.mode == ProcessingMode.MULTIPROCESS:
                return self._search_multiprocess(elements, queries)
            else:
                return self._search_threaded(elements, queries)
    
    def process_elements_chunked(self,
                                elements: List[Element],
                                processor_func: Callable[[List[Element]], Any],
                                combine_func: Callable[[List[Any]], Any]) -> Any:
        """Process elements in chunks with parallel execution
        
        Args:
            elements: Elements to process
            processor_func: Function to process each chunk
            combine_func: Function to combine chunk results
            
        Returns:
            Combined processing result
        """
        operation_name = "chunked_processing"
        
        with time_operation(operation_name):
            # Split into chunks
            chunks = self._create_chunks(elements, self.config.chunk_size)
            
            if self.config.mode == ProcessingMode.MULTIPROCESS:
                results = self._process_chunks_multiprocess(chunks, processor_func)
            else:
                results = self._process_chunks_threaded(chunks, processor_func)
            
            # Combine results
            return combine_func(results)
    
    def _filter_sequential(self,
                          elements: List[Element],
                          filter_sets: List[FilterSet],
                          filter_manager: FilterManager) -> Dict[str, List[Element]]:
        """Apply filters sequentially"""
        results = {}
        
        for filter_set in filter_sets:
            filtered = filter_manager.filter_elements(elements, filter_set)
            results[filter_set.filter_set_id] = filtered
        
        return results
    
    def _filter_threaded(self,
                        elements: List[Element],
                        filter_sets: List[FilterSet],
                        filter_manager: FilterManager) -> Dict[str, List[Element]]:
        """Apply filters using threads"""
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.optimal_workers) as executor:
            # Submit filter tasks
            future_to_filter = {}
            for filter_set in filter_sets:
                future = executor.submit(
                    filter_manager.filter_elements,
                    elements,
                    filter_set
                )
                future_to_filter[future] = filter_set
            
            # Collect results
            for future in as_completed(future_to_filter):
                filter_set = future_to_filter[future]
                try:
                    filtered_elements = future.result(timeout=self.config.timeout_seconds)
                    results[filter_set.filter_set_id] = filtered_elements
                except Exception as e:
                    logger.warning(f"Threaded filter failed for {filter_set.filter_set_id}: {e}")
                    results[filter_set.filter_set_id] = []
        
        return results
    
    def _filter_multiprocess(self,
                           elements: List[Element],
                           filter_sets: List[FilterSet]) -> Dict[str, List[Element]]:
        """Apply filters using multiprocessing"""
        results = {}
        
        # Prepare arguments for workers
        worker_args = []
        for filter_set in filter_sets:
            filter_data = serialize_filter_set(filter_set)
            worker_args.append((elements, filter_data))
        
        with ProcessPoolExecutor(max_workers=self.optimal_workers) as executor:
            # Submit filter tasks
            future_to_filter = {}
            for i, args in enumerate(worker_args):
                future = executor.submit(apply_filter_parallel_worker, args)
                future_to_filter[future] = filter_sets[i]
            
            # Collect results
            for future in as_completed(future_to_filter):
                filter_set = future_to_filter[future]
                try:
                    filtered_elements = future.result(timeout=self.config.timeout_seconds)
                    results[filter_set.filter_set_id] = filtered_elements
                except Exception as e:
                    logger.warning(f"Multiprocess filter failed for {filter_set.filter_set_id}: {e}")
                    results[filter_set.filter_set_id] = []
        
        return results
    
    async def _filter_async(self,
                          elements: List[Element],
                          filter_sets: List[FilterSet],
                          filter_manager: FilterManager) -> Dict[str, List[Element]]:
        """Apply filters using async/await"""
        results = {}
        
        async def apply_filter_async(filter_set: FilterSet) -> Tuple[str, List[Element]]:
            # Run filter in thread pool
            loop = asyncio.get_event_loop()
            filtered = await loop.run_in_executor(
                None,
                filter_manager.filter_elements,
                elements,
                filter_set
            )
            return filter_set.filter_set_id, filtered
        
        # Execute all filters concurrently
        tasks = [apply_filter_async(fs) for fs in filter_sets]
        
        try:
            completed_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in completed_results:
                if isinstance(result, Exception):
                    logger.warning(f"Async filter failed: {result}")
                    continue
                
                filter_id, filtered_elements = result
                results[filter_id] = filtered_elements
        
        except Exception as e:
            logger.error(f"Async filter execution failed: {e}")
        
        return results
    
    def _filter_hybrid(self,
                      elements: List[Element],
                      filter_sets: List[FilterSet],
                      filter_manager: FilterManager) -> Dict[str, List[Element]]:
        """Apply filters using hybrid approach"""
        # Use threading for I/O bound operations, multiprocessing for CPU bound
        if len(elements) > 10000:  # Large dataset - use multiprocessing
            return self._filter_multiprocess(elements, filter_sets)
        else:  # Smaller dataset - use threading
            return self._filter_threaded(elements, filter_sets, filter_manager)
    
    def _search_threaded(self,
                        elements: List[Element],
                        queries: List[str]) -> Dict[str, List[Element]]:
        """Search using threads"""
        results = {}
        
        def search_single_query(query: str) -> Tuple[str, List[Element]]:
            matches = []
            query_lower = query.lower()
            
            for element in elements:
                if (query_lower in element.text.lower() or
                    query_lower in element.element_type.value.lower()):
                    matches.append(element)
            
            return query, matches
        
        with ThreadPoolExecutor(max_workers=self.optimal_workers) as executor:
            futures = [executor.submit(search_single_query, query) for query in queries]
            
            for future in as_completed(futures):
                try:
                    query, matches = future.result(timeout=self.config.timeout_seconds)
                    results[query] = matches
                except Exception as e:
                    logger.warning(f"Threaded search failed: {e}")
        
        return results
    
    def _search_multiprocess(self,
                           elements: List[Element],
                           queries: List[str]) -> Dict[str, List[Element]]:
        """Search using multiprocessing"""
        results = {}
        
        # Prepare worker arguments
        worker_args = [(elements, query, {}) for query in queries]
        
        with ProcessPoolExecutor(max_workers=self.optimal_workers) as executor:
            future_to_query = {}
            for i, args in enumerate(worker_args):
                future = executor.submit(search_parallel_worker, args)
                future_to_query[future] = queries[i]
            
            for future in as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    matches = future.result(timeout=self.config.timeout_seconds)
                    results[query] = matches
                except Exception as e:
                    logger.warning(f"Multiprocess search failed for '{query}': {e}")
                    results[query] = []
        
        return results
    
    def _process_chunks_threaded(self,
                               chunks: List[List[Element]],
                               processor_func: Callable[[List[Element]], Any]) -> List[Any]:
        """Process chunks using threads"""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.optimal_workers) as executor:
            futures = [executor.submit(processor_func, chunk) for chunk in chunks]
            
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=self.config.timeout_seconds)
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Chunk processing failed: {e}")
                    results.append(None)
        
        return [r for r in results if r is not None]
    
    def _process_chunks_multiprocess(self,
                                   chunks: List[List[Element]],
                                   processor_func: Callable[[List[Element]], Any]) -> List[Any]:
        """Process chunks using multiprocessing"""
        results = []
        
        with ProcessPoolExecutor(max_workers=self.optimal_workers) as executor:
            futures = [executor.submit(processor_func, chunk) for chunk in chunks]
            
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=self.config.timeout_seconds)
                    results.append(result)
                except Exception as e:
                    logger.warning(f"Multiprocess chunk processing failed: {e}")
                    results.append(None)
        
        return [r for r in results if r is not None]
    
    def _create_chunks(self, elements: List[Element], chunk_size: int) -> List[List[Element]]:
        """Split elements into chunks"""
        chunks = []
        for i in range(0, len(elements), chunk_size):
            chunk = elements[i:i + chunk_size]
            chunks.append(chunk)
        return chunks


class ParallelExecutionManager:
    """Manager for parallel execution strategies"""
    
    def __init__(self):
        """Initialize execution manager"""
        self.processors = {
            ProcessingMode.SEQUENTIAL: ParallelFilterProcessor(ProcessingConfig(ProcessingMode.SEQUENTIAL)),
            ProcessingMode.THREADED: ParallelFilterProcessor(ProcessingConfig(ProcessingMode.THREADED)),
            ProcessingMode.MULTIPROCESS: ParallelFilterProcessor(ProcessingConfig(ProcessingMode.MULTIPROCESS)),
            ProcessingMode.ASYNC: ParallelFilterProcessor(ProcessingConfig(ProcessingMode.ASYNC)),
            ProcessingMode.HYBRID: ParallelFilterProcessor(ProcessingConfig(ProcessingMode.HYBRID))
        }
    
    def get_optimal_processor(self,
                            element_count: int,
                            operation_complexity: str = "medium") -> ParallelFilterProcessor:
        """Get optimal processor for given workload
        
        Args:
            element_count: Number of elements to process
            operation_complexity: Complexity level (low, medium, high)
            
        Returns:
            Optimal processor for the workload
        """
        # Decision logic based on workload characteristics
        if element_count < 100:
            return self.processors[ProcessingMode.SEQUENTIAL]
        elif element_count < 1000:
            return self.processors[ProcessingMode.THREADED]
        elif operation_complexity == "high":
            return self.processors[ProcessingMode.MULTIPROCESS]
        else:
            return self.processors[ProcessingMode.HYBRID]
    
    def benchmark_processors(self,
                           elements: List[Element],
                           filter_sets: List[FilterSet],
                           filter_manager: FilterManager) -> Dict[str, float]:
        """Benchmark different processors
        
        Args:
            elements: Test elements
            filter_sets: Test filter sets
            filter_manager: Filter manager
            
        Returns:
            Dictionary of execution times by processor mode
        """
        results = {}
        
        for mode, processor in self.processors.items():
            try:
                start_time = time.time()
                processor.filter_elements_parallel(elements, filter_sets, filter_manager)
                execution_time = time.time() - start_time
                results[mode.value] = execution_time
                
                logger.info(f"Benchmark {mode.value}: {execution_time:.3f}s")
                
            except Exception as e:
                logger.warning(f"Benchmark failed for {mode.value}: {e}")
                results[mode.value] = float('inf')
        
        return results


# Global parallel execution manager
_execution_manager: Optional[ParallelExecutionManager] = None


def get_execution_manager() -> ParallelExecutionManager:
    """Get global parallel execution manager"""
    global _execution_manager
    if _execution_manager is None:
        _execution_manager = ParallelExecutionManager()
    return _execution_manager


def create_optimal_processor(element_count: int, 
                           operation_complexity: str = "medium") -> ParallelFilterProcessor:
    """Create optimal processor for workload"""
    return get_execution_manager().get_optimal_processor(element_count, operation_complexity)