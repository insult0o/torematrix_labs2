"""
Advanced Batch Processing System for Merge/Split Operations.

Agent 4 - Integration & Advanced Features (Issue #237)
Provides high-performance batch processing with progress tracking,
parallel execution, error handling, and operation scheduling.
"""

from typing import Dict, List, Optional, Any, Callable, Union, Set, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import asyncio
import logging
import uuid
from datetime import datetime, timedelta
import time
from collections import deque
import json

from .....core.events import EventBus
from .....core.state import Store
from .....core.models import Element
from ..integration.component_integrator import MergeSplitIntegrator

logger = logging.getLogger(__name__)


class BatchStatus(Enum):
    """Status of batch operations."""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class OperationType(Enum):
    """Types of operations in batch."""
    MERGE = "merge"
    SPLIT = "split"
    VALIDATE = "validate"
    TRANSFORM = "transform"
    EXPORT = "export"
    CUSTOM = "custom"


@dataclass
class BatchOperation:
    """Individual operation within a batch."""
    operation_id: str
    operation_type: OperationType
    elements: List[str]  # Element IDs
    options: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1  # 1-10, higher is higher priority
    dependencies: List[str] = field(default_factory=list)  # Operation IDs this depends on
    timeout: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: BatchStatus = BatchStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class BatchProgress:
    """Progress information for batch operations."""
    batch_id: str
    total_operations: int
    completed_operations: int = 0
    failed_operations: int = 0
    skipped_operations: int = 0
    current_operation: Optional[str] = None
    estimated_remaining: Optional[float] = None
    start_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    
    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_operations == 0:
            return 100.0
        return (self.completed_operations / self.total_operations) * 100.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        processed = self.completed_operations + self.failed_operations
        if processed == 0:
            return 100.0
        return (self.completed_operations / processed) * 100.0


@dataclass
class BatchResult:
    """Result of a batch operation."""
    batch_id: str
    status: BatchStatus
    total_operations: int
    successful_operations: int
    failed_operations: int
    skipped_operations: int
    start_time: datetime
    end_time: Optional[datetime] = None
    execution_time: Optional[float] = None
    results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def success_rate(self) -> float:
        """Calculate overall success rate."""
        processed = self.successful_operations + self.failed_operations
        if processed == 0:
            return 100.0
        return (self.successful_operations / processed) * 100.0


@dataclass
class BatchConfiguration:
    """Configuration for batch processing."""
    max_concurrent_operations: int = 5
    operation_timeout: float = 300.0  # 5 minutes
    retry_delay: float = 1.0  # Initial retry delay
    retry_backoff_multiplier: float = 2.0
    max_retry_delay: float = 60.0
    enable_dependency_resolution: bool = True
    enable_parallel_execution: bool = True
    progress_update_interval: float = 1.0  # seconds
    enable_operation_caching: bool = False
    cache_duration: float = 3600.0  # 1 hour
    enable_performance_monitoring: bool = True
    log_level: str = "INFO"


class OperationBatch:
    """Container for batch operations with dependency management."""
    
    def __init__(self, batch_id: str, name: str = ""):
        self.batch_id = batch_id
        self.name = name or f"Batch-{batch_id[:8]}"
        self.operations: Dict[str, BatchOperation] = {}
        self.operation_order: List[str] = []
        self.status = BatchStatus.PENDING
        self.created_at = datetime.now()
        self.metadata: Dict[str, Any] = {}
    
    def add_operation(self, operation: BatchOperation) -> None:
        """Add operation to batch."""
        self.operations[operation.operation_id] = operation
        self._update_operation_order()
    
    def remove_operation(self, operation_id: str) -> bool:
        """Remove operation from batch."""
        if operation_id in self.operations:
            del self.operations[operation_id]
            self._update_operation_order()
            return True
        return False
    
    def get_operation(self, operation_id: str) -> Optional[BatchOperation]:
        """Get operation by ID."""
        return self.operations.get(operation_id)
    
    def get_ready_operations(self) -> List[BatchOperation]:
        """Get operations that are ready to execute (dependencies satisfied)."""
        ready_ops = []
        
        for op_id in self.operation_order:
            operation = self.operations[op_id]
            
            if operation.status != BatchStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            dependencies_satisfied = True
            for dep_id in operation.dependencies:
                dep_op = self.operations.get(dep_id)
                if not dep_op or dep_op.status != BatchStatus.COMPLETED:
                    dependencies_satisfied = False
                    break
            
            if dependencies_satisfied:
                ready_ops.append(operation)
        
        # Sort by priority (higher priority first)
        ready_ops.sort(key=lambda op: op.priority, reverse=True)
        return ready_ops
    
    def _update_operation_order(self) -> None:
        """Update operation execution order based on dependencies."""
        # Topological sort based on dependencies
        visited = set()
        temp_mark = set()
        self.operation_order = []
        
        def visit(op_id: str):
            if op_id in temp_mark:
                logger.warning(f"Circular dependency detected in batch {self.batch_id}")
                return
            if op_id in visited:
                return
            
            temp_mark.add(op_id)
            operation = self.operations.get(op_id)
            if operation:
                for dep_id in operation.dependencies:
                    if dep_id in self.operations:
                        visit(dep_id)
            temp_mark.remove(op_id)
            visited.add(op_id)
            self.operation_order.append(op_id)
        
        for op_id in self.operations:
            if op_id not in visited:
                visit(op_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get batch statistics."""
        stats = {
            'total_operations': len(self.operations),
            'pending': 0,
            'running': 0,
            'completed': 0,
            'failed': 0,
            'cancelled': 0
        }
        
        for operation in self.operations.values():
            if operation.status == BatchStatus.PENDING:
                stats['pending'] += 1
            elif operation.status == BatchStatus.RUNNING:
                stats['running'] += 1
            elif operation.status == BatchStatus.COMPLETED:
                stats['completed'] += 1
            elif operation.status == BatchStatus.FAILED:
                stats['failed'] += 1
            elif operation.status == BatchStatus.CANCELLED:
                stats['cancelled'] += 1
        
        return stats


class BatchProcessor:
    """High-performance batch processor for merge/split operations."""
    
    def __init__(
        self, 
        integrator: MergeSplitIntegrator,
        event_bus: EventBus,
        store: Store,
        config: Optional[BatchConfiguration] = None
    ):
        self.integrator = integrator
        self.event_bus = event_bus
        self.store = store
        self.config = config or BatchConfiguration()
        
        # Batch management
        self._batches: Dict[str, OperationBatch] = {}
        self._batch_progress: Dict[str, BatchProgress] = {}
        self._batch_results: Dict[str, BatchResult] = {}
        
        # Execution management
        self._running_batches: Set[str] = set()
        self._active_operations: Dict[str, asyncio.Task] = {}
        self._operation_semaphore = asyncio.Semaphore(config.max_concurrent_operations)
        
        # Performance tracking
        self._operation_times: deque = deque(maxlen=1000)
        self._last_progress_update = time.time()
        
        # Shutdown management
        self._shutdown_event = asyncio.Event()
        self._monitor_task: Optional[asyncio.Task] = None
    
    async def initialize(self) -> None:
        """Initialize the batch processor."""
        # Start progress monitoring task
        self._monitor_task = asyncio.create_task(self._progress_monitor())
        
        # Subscribe to events
        await self.event_bus.subscribe('batch_operation_completed', self._handle_operation_completed)
        await self.event_bus.subscribe('batch_operation_failed', self._handle_operation_failed)
        
        logger.info("BatchProcessor initialized")
    
    def create_batch(self, name: str = "") -> str:
        """Create a new batch and return its ID."""
        batch_id = str(uuid.uuid4())
        batch = OperationBatch(batch_id, name)
        self._batches[batch_id] = batch
        
        logger.info(f"Created batch: {batch_id} ({name})")
        return batch_id
    
    def add_merge_operation(
        self, 
        batch_id: str, 
        elements: List[str], 
        options: Dict[str, Any] = None,
        priority: int = 1,
        dependencies: List[str] = None
    ) -> str:
        """Add a merge operation to a batch."""
        operation_id = str(uuid.uuid4())
        operation = BatchOperation(
            operation_id=operation_id,
            operation_type=OperationType.MERGE,
            elements=elements,
            options=options or {},
            priority=priority,
            dependencies=dependencies or []
        )
        
        batch = self._batches.get(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
        
        batch.add_operation(operation)
        logger.debug(f"Added merge operation {operation_id} to batch {batch_id}")
        return operation_id
    
    def add_split_operation(
        self, 
        batch_id: str, 
        element: str, 
        split_points: List[int],
        options: Dict[str, Any] = None,
        priority: int = 1,
        dependencies: List[str] = None
    ) -> str:
        """Add a split operation to a batch."""
        operation_id = str(uuid.uuid4())
        operation = BatchOperation(
            operation_id=operation_id,
            operation_type=OperationType.SPLIT,
            elements=[element],
            options={**(options or {}), 'split_points': split_points},
            priority=priority,
            dependencies=dependencies or []
        )
        
        batch = self._batches.get(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
        
        batch.add_operation(operation)
        logger.debug(f"Added split operation {operation_id} to batch {batch_id}")
        return operation_id
    
    async def execute_batch(self, batch_id: str) -> BatchResult:
        """Execute a batch of operations."""
        batch = self._batches.get(batch_id)
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")
        
        if batch_id in self._running_batches:
            raise ValueError(f"Batch {batch_id} is already running")
        
        logger.info(f"Starting execution of batch {batch_id} with {len(batch.operations)} operations")
        
        # Initialize batch tracking
        self._running_batches.add(batch_id)
        batch.status = BatchStatus.RUNNING
        
        progress = BatchProgress(
            batch_id=batch_id,
            total_operations=len(batch.operations)
        )
        self._batch_progress[batch_id] = progress
        
        result = BatchResult(
            batch_id=batch_id,
            status=BatchStatus.RUNNING,
            total_operations=len(batch.operations),
            successful_operations=0,
            failed_operations=0,
            skipped_operations=0,
            start_time=datetime.now()
        )
        
        try:
            # Execute operations
            if self.config.enable_parallel_execution:
                await self._execute_batch_parallel(batch, progress, result)
            else:
                await self._execute_batch_sequential(batch, progress, result)
            
            # Update final status
            result.end_time = datetime.now()
            result.execution_time = (result.end_time - result.start_time).total_seconds()
            
            if result.failed_operations == 0:
                result.status = BatchStatus.COMPLETED
                batch.status = BatchStatus.COMPLETED
            elif result.successful_operations > 0:
                result.status = BatchStatus.PARTIAL
                batch.status = BatchStatus.PARTIAL
            else:
                result.status = BatchStatus.FAILED
                batch.status = BatchStatus.FAILED
            
            logger.info(f"Batch {batch_id} completed: {result.successful_operations}/{result.total_operations} successful")
            
        except Exception as e:
            result.status = BatchStatus.FAILED
            batch.status = BatchStatus.FAILED
            result.errors.append(f"Batch execution failed: {e}")
            logger.error(f"Batch {batch_id} execution failed: {e}")
            
        finally:
            # Cleanup
            self._running_batches.discard(batch_id)
            self._batch_results[batch_id] = result
            
            # Emit completion event
            await self.event_bus.emit('batch_completed', {
                'batch_id': batch_id,
                'result': result.__dict__
            })
        
        return result
    
    async def _execute_batch_parallel(
        self, 
        batch: OperationBatch, 
        progress: BatchProgress, 
        result: BatchResult
    ) -> None:
        """Execute batch operations in parallel with dependency management."""
        remaining_operations = set(batch.operations.keys())
        
        while remaining_operations and not self._shutdown_event.is_set():
            # Get operations ready to execute
            ready_operations = [
                op for op in batch.get_ready_operations()
                if op.operation_id in remaining_operations
            ]
            
            if not ready_operations:
                # No ready operations - check if we're deadlocked
                running_count = len([op for op in batch.operations.values() 
                                   if op.status == BatchStatus.RUNNING])
                if running_count == 0:
                    # Deadlock or all remaining operations have failed dependencies
                    for op_id in remaining_operations:
                        operation = batch.operations[op_id]
                        operation.status = BatchStatus.FAILED
                        operation.error = "Dependency deadlock or failed dependencies"
                        result.failed_operations += 1
                        result.errors.append(f"Operation {op_id} failed due to dependency issues")
                    break
                
                # Wait for running operations to complete
                await asyncio.sleep(0.1)
                continue
            
            # Start ready operations (up to concurrency limit)
            tasks = []
            for operation in ready_operations[:self.config.max_concurrent_operations]:
                if operation.operation_id in self._active_operations:
                    continue
                
                task = asyncio.create_task(self._execute_operation(operation, batch, progress, result))
                self._active_operations[operation.operation_id] = task
                tasks.append(task)
                
                operation.status = BatchStatus.RUNNING
                operation.started_at = datetime.now()
                progress.current_operation = operation.operation_id
            
            # Wait for at least one operation to complete
            if tasks:
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                
                for task in done:
                    operation_id = None
                    for op_id, op_task in self._active_operations.items():
                        if op_task == task:
                            operation_id = op_id
                            break
                    
                    if operation_id:
                        del self._active_operations[operation_id]
                        remaining_operations.discard(operation_id)
    
    async def _execute_batch_sequential(
        self, 
        batch: OperationBatch, 
        progress: BatchProgress, 
        result: BatchResult
    ) -> None:
        """Execute batch operations sequentially in dependency order."""
        for operation_id in batch.operation_order:
            if self._shutdown_event.is_set():
                break
            
            operation = batch.operations[operation_id]
            
            # Check dependencies
            dependencies_satisfied = True
            for dep_id in operation.dependencies:
                dep_op = batch.operations.get(dep_id)
                if not dep_op or dep_op.status != BatchStatus.COMPLETED:
                    dependencies_satisfied = False
                    break
            
            if not dependencies_satisfied:
                operation.status = BatchStatus.FAILED
                operation.error = "Dependency not satisfied"
                result.failed_operations += 1
                result.errors.append(f"Operation {operation_id} failed due to unsatisfied dependencies")
                continue
            
            # Execute operation
            operation.status = BatchStatus.RUNNING
            operation.started_at = datetime.now()
            progress.current_operation = operation_id
            
            await self._execute_operation(operation, batch, progress, result)
    
    async def _execute_operation(
        self, 
        operation: BatchOperation, 
        batch: OperationBatch, 
        progress: BatchProgress, 
        result: BatchResult
    ) -> None:
        """Execute a single operation."""
        start_time = time.time()
        
        try:
            async with self._operation_semaphore:
                # Get elements from store
                state = self.store.get_state()
                document_elements = state.get('document', {}).get('elements', {})
                elements = [document_elements.get(elem_id) for elem_id in operation.elements]
                elements = [elem for elem in elements if elem is not None]
                
                if not elements:
                    raise ValueError(f"No valid elements found for operation {operation.operation_id}")
                
                # Execute based on operation type
                if operation.operation_type == OperationType.MERGE:
                    operation_result = await self.integrator.coordinator.coordinate_merge_operation(
                        elements, operation.options, operation.operation_id
                    )
                elif operation.operation_type == OperationType.SPLIT:
                    if len(elements) != 1:
                        raise ValueError("Split operation requires exactly one element")
                    
                    split_points = operation.options.get('split_points', [])
                    operation_result = await self.integrator.coordinator.coordinate_split_operation(
                        elements[0], split_points, operation.options, operation.operation_id
                    )
                else:
                    raise ValueError(f"Unsupported operation type: {operation.operation_type}")
                
                # Handle result
                if operation_result.get('success', False):
                    operation.status = BatchStatus.COMPLETED
                    operation.result = operation_result
                    result.successful_operations += 1
                    result.results.append(operation_result)
                else:
                    operation.status = BatchStatus.FAILED
                    operation.error = operation_result.get('error', 'Unknown error')
                    result.failed_operations += 1
                    result.errors.append(f"Operation {operation.operation_id}: {operation.error}")
                
        except Exception as e:
            operation.status = BatchStatus.FAILED
            operation.error = str(e)
            result.failed_operations += 1
            result.errors.append(f"Operation {operation.operation_id}: {str(e)}")
            
            logger.error(f"Operation {operation.operation_id} failed: {e}")
        
        finally:
            operation.completed_at = datetime.now()
            execution_time = time.time() - start_time
            self._operation_times.append(execution_time)
            
            # Update progress
            if operation.status == BatchStatus.COMPLETED:
                progress.completed_operations += 1
            elif operation.status == BatchStatus.FAILED:
                progress.failed_operations += 1
            
            progress.last_update = datetime.now()
            
            # Estimate remaining time
            if self._operation_times:
                avg_time = sum(self._operation_times) / len(self._operation_times)
                remaining_ops = progress.total_operations - progress.completed_operations - progress.failed_operations
                progress.estimated_remaining = avg_time * remaining_ops
    
    async def _progress_monitor(self) -> None:
        """Monitor and emit progress updates."""
        while not self._shutdown_event.is_set():
            try:
                current_time = time.time()
                
                if current_time - self._last_progress_update >= self.config.progress_update_interval:
                    for batch_id, progress in self._batch_progress.items():
                        if batch_id in self._running_batches:
                            await self.event_bus.emit('batch_progress', {
                                'batch_id': batch_id,
                                'progress': progress.__dict__
                            })
                    
                    self._last_progress_update = current_time
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Progress monitor error: {e}")
                await asyncio.sleep(1.0)
    
    async def _handle_operation_completed(self, event_data: Dict[str, Any]) -> None:
        """Handle operation completion events."""
        operation_id = event_data.get('operation_id')
        if operation_id:
            logger.debug(f"Operation completed: {operation_id}")
    
    async def _handle_operation_failed(self, event_data: Dict[str, Any]) -> None:
        """Handle operation failure events."""
        operation_id = event_data.get('operation_id')
        error = event_data.get('error')
        if operation_id:
            logger.debug(f"Operation failed: {operation_id} - {error}")
    
    def get_batch_progress(self, batch_id: str) -> Optional[BatchProgress]:
        """Get progress for a specific batch."""
        return self._batch_progress.get(batch_id)
    
    def get_batch_result(self, batch_id: str) -> Optional[BatchResult]:
        """Get result for a specific batch."""
        return self._batch_results.get(batch_id)
    
    def get_batch_statistics(self) -> Dict[str, Any]:
        """Get overall batch processing statistics."""
        total_batches = len(self._batches)
        running_batches = len(self._running_batches)
        completed_batches = len(self._batch_results)
        
        total_operations = sum(len(batch.operations) for batch in self._batches.values())
        
        avg_operation_time = 0.0
        if self._operation_times:
            avg_operation_time = sum(self._operation_times) / len(self._operation_times)
        
        return {
            'total_batches': total_batches,
            'running_batches': running_batches,
            'completed_batches': completed_batches,
            'total_operations': total_operations,
            'average_operation_time': avg_operation_time,
            'active_operations': len(self._active_operations),
            'max_concurrent_operations': self.config.max_concurrent_operations
        }
    
    async def cancel_batch(self, batch_id: str) -> bool:
        """Cancel a running batch."""
        if batch_id not in self._running_batches:
            return False
        
        batch = self._batches.get(batch_id)
        if batch:
            batch.status = BatchStatus.CANCELLED
            
            # Cancel running operations
            operations_to_cancel = [
                task for op_id, task in self._active_operations.items()
                if op_id in batch.operations
            ]
            
            for task in operations_to_cancel:
                task.cancel()
            
            self._running_batches.discard(batch_id)
            
            logger.info(f"Cancelled batch {batch_id}")
            return True
        
        return False
    
    async def shutdown(self) -> None:
        """Shutdown the batch processor."""
        logger.info("Shutting down BatchProcessor...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel all running operations
        for task in self._active_operations.values():
            task.cancel()
        
        # Wait for operations to complete
        if self._active_operations:
            await asyncio.gather(*self._active_operations.values(), return_exceptions=True)
        
        # Stop monitor task
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("BatchProcessor shutdown completed")


# Convenience factory function
async def create_batch_processor(
    integrator: MergeSplitIntegrator,
    event_bus: EventBus,
    store: Store,
    config: Optional[BatchConfiguration] = None
) -> BatchProcessor:
    """Create and initialize a batch processor."""
    processor = BatchProcessor(integrator, event_bus, store, config)
    await processor.initialize()
    return processor