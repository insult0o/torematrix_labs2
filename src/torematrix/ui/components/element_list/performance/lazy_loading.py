"""
Lazy Loading System for Element Tree View

Provides on-demand loading of tree branches to improve performance with large datasets.
"""

from typing import Dict, List, Optional, Set, Callable, Any, Tuple
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QModelIndex, QThread, pyqtSlot
from PyQt6.QtWidgets import QTreeView
import weakref
import time
from collections import deque
from dataclasses import dataclass, field

from ..models.tree_node import TreeNode


@dataclass
class LoadRequest:
    """Represents a lazy loading request."""
    node_id: str
    parent_index: QModelIndex
    priority: int = 0
    timestamp: float = field(default_factory=time.time)
    callback: Optional[Callable] = None
    user_initiated: bool = False
    
    def __lt__(self, other):
        """Sort by priority (higher first), then timestamp."""
        if self.priority != other.priority:
            return self.priority > other.priority
        return self.timestamp < other.timestamp


@dataclass
class LoadBatch:
    """Batch of loading requests to process together."""
    requests: List[LoadRequest]
    batch_id: str
    created_at: float = field(default_factory=time.time)
    
    def total_priority(self) -> int:
        """Calculate total batch priority."""
        return sum(req.priority for req in self.requests)


class LoadingState:
    """Tracks loading state for tree nodes."""
    
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"
    
    def __init__(self):
        self.node_states: Dict[str, str] = {}
        self.load_times: Dict[str, float] = {}
        self.error_counts: Dict[str, int] = {}
        self.placeholders: Dict[str, TreeNode] = {}
    
    def get_state(self, node_id: str) -> str:
        """Get loading state for node."""
        return self.node_states.get(node_id, self.UNLOADED)
    
    def set_state(self, node_id: str, state: str) -> None:
        """Set loading state for node."""
        self.node_states[node_id] = state
        if state == self.LOADED:
            self.load_times[node_id] = time.time()
    
    def is_loaded(self, node_id: str) -> bool:
        """Check if node is loaded."""
        return self.get_state(node_id) == self.LOADED
    
    def is_loading(self, node_id: str) -> bool:
        """Check if node is currently loading."""
        return self.get_state(node_id) == self.LOADING
    
    def mark_error(self, node_id: str, error: Exception) -> None:
        """Mark node as having loading error."""
        self.set_state(node_id, self.ERROR)
        self.error_counts[node_id] = self.error_counts.get(node_id, 0) + 1
    
    def get_error_count(self, node_id: str) -> int:
        """Get error count for node."""
        return self.error_counts.get(node_id, 0)
    
    def should_retry(self, node_id: str, max_retries: int = 3) -> bool:
        """Check if should retry loading after error."""
        return self.get_error_count(node_id) < max_retries
    
    def add_placeholder(self, node_id: str, placeholder: TreeNode) -> None:
        """Add placeholder node."""
        self.placeholders[node_id] = placeholder
    
    def get_placeholder(self, node_id: str) -> Optional[TreeNode]:
        """Get placeholder node."""
        return self.placeholders.get(node_id)
    
    def remove_placeholder(self, node_id: str) -> None:
        """Remove placeholder node."""
        self.placeholders.pop(node_id, None)


class LoadingQueue:
    """Priority queue for loading requests."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.requests: deque = deque()
        self.pending_by_id: Dict[str, LoadRequest] = {}
        self.batch_requests: Dict[str, List[LoadRequest]] = {}
    
    def add_request(self, request: LoadRequest) -> bool:
        """Add loading request to queue."""
        # Replace existing request if higher priority
        existing = self.pending_by_id.get(request.node_id)
        if existing:
            if request.priority <= existing.priority:
                return False  # Don't add lower priority request
            self.remove_request(request.node_id)
        
        # Check queue size
        if len(self.requests) >= self.max_size:
            # Remove lowest priority request
            self._remove_lowest_priority()
        
        # Insert request in priority order
        self._insert_sorted(request)
        self.pending_by_id[request.node_id] = request
        return True
    
    def remove_request(self, node_id: str) -> bool:
        """Remove request from queue."""
        request = self.pending_by_id.pop(node_id, None)
        if request:
            try:
                self.requests.remove(request)
                return True
            except ValueError:
                pass
        return False
    
    def get_next_request(self) -> Optional[LoadRequest]:
        """Get next request to process."""
        if self.requests:
            request = self.requests.popleft()
            self.pending_by_id.pop(request.node_id, None)
            return request
        return None
    
    def get_batch(self, max_size: int = 10, max_wait_time: float = 0.1) -> List[LoadRequest]:
        """Get batch of requests to process together."""
        batch = []
        start_time = time.time()
        
        while len(batch) < max_size and self.requests:
            if time.time() - start_time > max_wait_time and batch:
                break
                
            request = self.get_next_request()
            if request:
                batch.append(request)
        
        return batch
    
    def _insert_sorted(self, request: LoadRequest) -> None:
        """Insert request in priority order."""
        # Simple insertion for small queues, can optimize later
        inserted = False
        for i, existing in enumerate(self.requests):
            if request < existing:
                self.requests.insert(i, request)
                inserted = True
                break
        
        if not inserted:
            self.requests.append(request)
    
    def _remove_lowest_priority(self) -> None:
        """Remove lowest priority request."""
        if self.requests:
            # Remove from end (lowest priority)
            removed = self.requests.pop()
            self.pending_by_id.pop(removed.node_id, None)
    
    def clear(self) -> None:
        """Clear all requests."""
        self.requests.clear()
        self.pending_by_id.clear()
    
    def size(self) -> int:
        """Get queue size."""
        return len(self.requests)
    
    def is_pending(self, node_id: str) -> bool:
        """Check if node has pending request."""
        return node_id in self.pending_by_id


class PlaceholderNode:
    """Creates placeholder nodes for lazy loading."""
    
    @staticmethod
    def create_loading_placeholder(parent: TreeNode, estimated_count: int = 1) -> TreeNode:
        """Create loading placeholder node."""
        from ....core.interfaces import ElementProtocol
        
        class LoadingElement(ElementProtocol):
            def __init__(self):
                self.id = f"loading_{id(self)}"
                self.type = "loading"
                self.text = f"Loading {estimated_count} items..."
                self.bbox = None
                self.confidence = 1.0
                self.metadata = {"is_placeholder": True, "loading": True}
        
        placeholder_element = LoadingElement()
        placeholder = TreeNode(placeholder_element, parent)
        return placeholder
    
    @staticmethod
    def create_error_placeholder(parent: TreeNode, error: Exception) -> TreeNode:
        """Create error placeholder node."""
        from ....core.interfaces import ElementProtocol
        
        class ErrorElement(ElementProtocol):
            def __init__(self, error_msg: str):
                self.id = f"error_{id(self)}"
                self.type = "error"
                self.text = f"Error loading: {error_msg}"
                self.bbox = None
                self.confidence = 0.0
                self.metadata = {"is_placeholder": True, "error": True}
        
        error_element = ErrorElement(str(error))
        placeholder = TreeNode(error_element, parent)
        return placeholder
    
    @staticmethod
    def create_empty_placeholder(parent: TreeNode) -> TreeNode:
        """Create empty state placeholder."""
        from ....core.interfaces import ElementProtocol
        
        class EmptyElement(ElementProtocol):
            def __init__(self):
                self.id = f"empty_{id(self)}"
                self.type = "empty"
                self.text = "No items to display"
                self.bbox = None
                self.confidence = 1.0
                self.metadata = {"is_placeholder": True, "empty": True}
        
        empty_element = EmptyElement()
        placeholder = TreeNode(empty_element, parent)
        return placeholder


class LoadWorker(QThread):
    """Background worker for lazy loading operations."""
    
    # Signals
    batchCompleted = pyqtSignal(str, list)  # batch_id, loaded_nodes
    requestCompleted = pyqtSignal(str, object, object)  # node_id, loaded_data, error
    progressUpdated = pyqtSignal(str, int, int)  # batch_id, completed, total
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_provider = None
        self.current_batch: Optional[LoadBatch] = None
        self.should_stop = False
    
    def set_data_provider(self, provider: Callable[[str], Any]) -> None:
        """Set data provider function."""
        self.data_provider = provider
    
    def load_batch(self, batch: LoadBatch) -> None:
        """Load a batch of requests."""
        self.current_batch = batch
        self.start()
    
    def run(self) -> None:
        """Run loading process."""
        if not self.current_batch or not self.data_provider:
            return
        
        batch = self.current_batch
        loaded_nodes = []
        completed = 0
        total = len(batch.requests)
        
        try:
            for request in batch.requests:
                if self.should_stop:
                    break
                
                try:
                    # Load data for node
                    loaded_data = self.data_provider(request.node_id)
                    loaded_nodes.append((request.node_id, loaded_data))
                    self.requestCompleted.emit(request.node_id, loaded_data, None)
                    
                except Exception as e:
                    self.requestCompleted.emit(request.node_id, None, e)
                
                completed += 1
                self.progressUpdated.emit(batch.batch_id, completed, total)
            
            self.batchCompleted.emit(batch.batch_id, loaded_nodes)
            
        except Exception as e:
            # Emit error for all remaining requests
            for i in range(completed, total):
                request = batch.requests[i]
                self.requestCompleted.emit(request.node_id, None, e)
        
        finally:
            self.current_batch = None
    
    def stop_loading(self) -> None:
        """Stop current loading operation."""
        self.should_stop = True
        self.wait(1000)  # Wait up to 1 second


class LazyLoadingManager(QObject):
    """Manages lazy loading for tree view."""
    
    # Signals
    nodeLoaded = pyqtSignal(str, object)  # node_id, loaded_data
    nodeLoadFailed = pyqtSignal(str, object)  # node_id, error
    loadingStarted = pyqtSignal(str)  # node_id
    loadingCompleted = pyqtSignal(str, bool)  # node_id, success
    batchLoadingStarted = pyqtSignal(str, int)  # batch_id, count
    batchLoadingCompleted = pyqtSignal(str, int, int)  # batch_id, success_count, total_count
    
    def __init__(self, tree_view: QTreeView, parent=None):
        super().__init__(parent)
        self.tree_view = weakref.ref(tree_view)
        self.loading_state = LoadingState()
        self.loading_queue = LoadingQueue()
        self.data_provider: Optional[Callable[[str], Any]] = None
        
        # Configuration
        self.max_concurrent_loads = 3
        self.batch_size = 10
        self.batch_timeout = 100  # ms
        self.auto_load_on_expand = True
        self.preload_visible_threshold = 5  # Load items within 5 rows of visible area
        
        # Workers
        self.workers: List[LoadWorker] = []
        self.active_batches: Dict[str, LoadBatch] = {}
        
        # Timers
        self.batch_timer = QTimer()
        self.batch_timer.timeout.connect(self._process_batch)
        self.batch_timer.setSingleShot(True)
        
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self._cleanup_old_data)
        self.cleanup_timer.start(30000)  # Cleanup every 30 seconds
        
        # Performance tracking
        self.load_statistics = {
            'total_requests': 0,
            'successful_loads': 0,
            'failed_loads': 0,
            'average_load_time': 0.0,
            'cache_hits': 0
        }
        
        # Connect tree view signals
        tree_view_obj = self.tree_view()
        if tree_view_obj:
            tree_view_obj.expanded.connect(self._on_node_expanded)
            tree_view_obj.collapsed.connect(self._on_node_collapsed)
    
    def set_data_provider(self, provider: Callable[[str], Any]) -> None:
        """Set data provider function."""
        self.data_provider = provider
        for worker in self.workers:
            worker.set_data_provider(provider)
    
    def request_load(self, node_id: str, parent_index: QModelIndex, 
                    priority: int = 0, user_initiated: bool = False,
                    callback: Optional[Callable] = None) -> bool:
        """Request lazy loading of a node."""
        # Check if already loaded or loading
        if self.loading_state.is_loaded(node_id):
            if callback:
                callback(node_id, True)
            return True
        
        if self.loading_state.is_loading(node_id):
            return False  # Already loading
        
        # Create load request
        request = LoadRequest(
            node_id=node_id,
            parent_index=parent_index,
            priority=priority,
            user_initiated=user_initiated,
            callback=callback
        )
        
        # Add to queue
        if self.loading_queue.add_request(request):
            self.load_statistics['total_requests'] += 1
            
            # Start batch timer if not running
            if not self.batch_timer.isActive():
                self.batch_timer.start(self.batch_timeout)
            
            return True
        
        return False
    
    def load_children_lazily(self, parent_node: TreeNode, parent_index: QModelIndex,
                           priority: int = 0) -> bool:
        """Request lazy loading of node's children."""
        if not parent_node.element:
            return False
        
        node_id = parent_node.element.id
        
        # Add loading placeholder if not present
        if parent_node.child_count() == 0 and not self.loading_state.is_loaded(node_id):
            placeholder = PlaceholderNode.create_loading_placeholder(parent_node)
            parent_node.add_child(placeholder)
            self.loading_state.add_placeholder(node_id, placeholder)
        
        return self.request_load(node_id, parent_index, priority, user_initiated=True)
    
    def preload_visible_area(self) -> None:
        """Preload nodes in visible area and nearby."""
        tree_view = self.tree_view()
        if not tree_view:
            return
        
        # Get visible indices
        viewport = tree_view.viewport()
        visible_rect = viewport.rect()
        
        # Find visible and nearby indices
        model = tree_view.model()
        if not model:
            return
        
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            if not index.isValid():
                continue
            
            rect = tree_view.visualRect(index)
            if rect.intersects(visible_rect) or self._is_near_visible(rect, visible_rect):
                self._preload_index(index)
    
    def _preload_index(self, index: QModelIndex) -> None:
        """Preload data for index if needed."""
        tree_view = self.tree_view()
        model = tree_view.model() if tree_view else None
        
        if not model:
            return
        
        # Get node ID from model
        node_id = model.data(index, Qt.ItemDataRole.UserRole)
        if node_id and not self.loading_state.is_loaded(node_id):
            self.request_load(node_id, index, priority=1)  # Lower priority for preload
    
    def _is_near_visible(self, rect, visible_rect) -> bool:
        """Check if rect is near visible area."""
        threshold = self.preload_visible_threshold * 25  # Assuming ~25px per row
        
        return (rect.bottom() >= visible_rect.top() - threshold and
                rect.top() <= visible_rect.bottom() + threshold)
    
    @pyqtSlot()
    def _process_batch(self) -> None:
        """Process batch of loading requests."""
        if self.loading_queue.size() == 0:
            return
        
        # Get batch of requests
        batch_requests = self.loading_queue.get_batch(self.batch_size)
        if not batch_requests:
            return
        
        # Create batch
        batch_id = f"batch_{int(time.time() * 1000)}_{id(self)}"
        batch = LoadBatch(requests=batch_requests, batch_id=batch_id)
        
        # Find available worker or create new one
        worker = self._get_available_worker()
        if worker:
            self.active_batches[batch_id] = batch
            self.batchLoadingStarted.emit(batch_id, len(batch_requests))
            
            # Mark nodes as loading
            for request in batch_requests:
                self.loading_state.set_state(request.node_id, LoadingState.LOADING)
                self.loadingStarted.emit(request.node_id)
            
            # Start loading
            worker.load_batch(batch)
        
        # Schedule next batch if more requests pending
        if self.loading_queue.size() > 0:
            self.batch_timer.start(self.batch_timeout)
    
    def _get_available_worker(self) -> Optional[LoadWorker]:
        """Get available worker or create new one."""
        # Find idle worker
        for worker in self.workers:
            if not worker.isRunning():
                return worker
        
        # Create new worker if under limit
        if len(self.workers) < self.max_concurrent_loads:
            worker = LoadWorker()
            worker.set_data_provider(self.data_provider)
            worker.requestCompleted.connect(self._on_request_completed)
            worker.batchCompleted.connect(self._on_batch_completed)
            worker.progressUpdated.connect(self._on_progress_updated)
            self.workers.append(worker)
            return worker
        
        return None
    
    @pyqtSlot(str, object, object)
    def _on_request_completed(self, node_id: str, loaded_data: Any, error: Exception) -> None:
        """Handle completed load request."""
        if error:
            self.loading_state.mark_error(node_id, error)
            self.nodeLoadFailed.emit(node_id, error)
            self.loadingCompleted.emit(node_id, False)
            self.load_statistics['failed_loads'] += 1
            
            # Replace loading placeholder with error placeholder
            placeholder = self.loading_state.get_placeholder(node_id)
            if placeholder and placeholder.parent():
                parent = placeholder.parent()
                parent.remove_child(placeholder)
                error_placeholder = PlaceholderNode.create_error_placeholder(parent, error)
                parent.add_child(error_placeholder)
        else:
            self.loading_state.set_state(node_id, LoadingState.LOADED)
            self.nodeLoaded.emit(node_id, loaded_data)
            self.loadingCompleted.emit(node_id, True)
            self.load_statistics['successful_loads'] += 1
            
            # Remove loading placeholder
            placeholder = self.loading_state.get_placeholder(node_id)
            if placeholder and placeholder.parent():
                placeholder.parent().remove_child(placeholder)
            self.loading_state.remove_placeholder(node_id)
    
    @pyqtSlot(str, list)
    def _on_batch_completed(self, batch_id: str, loaded_nodes: List[Tuple[str, Any]]) -> None:
        """Handle completed batch."""
        batch = self.active_batches.pop(batch_id, None)
        if batch:
            success_count = len(loaded_nodes)
            total_count = len(batch.requests)
            self.batchLoadingCompleted.emit(batch_id, success_count, total_count)
    
    @pyqtSlot(str, int, int)
    def _on_progress_updated(self, batch_id: str, completed: int, total: int) -> None:
        """Handle batch progress update."""
        # Can emit progress signals if needed
        pass
    
    @pyqtSlot(QModelIndex)
    def _on_node_expanded(self, index: QModelIndex) -> None:
        """Handle node expansion."""
        if not self.auto_load_on_expand:
            return
        
        tree_view = self.tree_view()
        model = tree_view.model() if tree_view else None
        
        if not model:
            return
        
        # Get node from index
        node_id = model.data(index, Qt.ItemDataRole.UserRole)
        if node_id:
            self.request_load(node_id, index, priority=5, user_initiated=True)  # High priority for user expansion
    
    @pyqtSlot(QModelIndex)
    def _on_node_collapsed(self, index: QModelIndex) -> None:
        """Handle node collapse."""
        # Can implement cleanup logic here if needed
        pass
    
    @pyqtSlot()
    def _cleanup_old_data(self) -> None:
        """Clean up old loaded data and placeholders."""
        current_time = time.time()
        cleanup_threshold = 300  # 5 minutes
        
        # Clean up old load times
        to_remove = []
        for node_id, load_time in self.loading_state.load_times.items():
            if current_time - load_time > cleanup_threshold:
                to_remove.append(node_id)
        
        for node_id in to_remove:
            self.loading_state.load_times.pop(node_id, None)
            # Could also unload data here if memory is a concern
    
    def cancel_loading(self, node_id: str) -> bool:
        """Cancel loading request for node."""
        return self.loading_queue.remove_request(node_id)
    
    def cancel_all_loading(self) -> None:
        """Cancel all pending loading requests."""
        self.loading_queue.clear()
        
        # Stop all workers
        for worker in self.workers:
            worker.stop_loading()
    
    def is_loaded(self, node_id: str) -> bool:
        """Check if node is loaded."""
        return self.loading_state.is_loaded(node_id)
    
    def is_loading(self, node_id: str) -> bool:
        """Check if node is currently loading."""
        return self.loading_state.is_loading(node_id)
    
    def get_loading_statistics(self) -> Dict[str, Any]:
        """Get loading performance statistics."""
        return self.load_statistics.copy()
    
    def configure_lazy_loading(self, **kwargs) -> None:
        """Configure lazy loading parameters."""
        if 'max_concurrent_loads' in kwargs:
            self.max_concurrent_loads = kwargs['max_concurrent_loads']
        if 'batch_size' in kwargs:
            self.batch_size = kwargs['batch_size']
        if 'batch_timeout' in kwargs:
            self.batch_timeout = kwargs['batch_timeout']
        if 'auto_load_on_expand' in kwargs:
            self.auto_load_on_expand = kwargs['auto_load_on_expand']
        if 'preload_visible_threshold' in kwargs:
            self.preload_visible_threshold = kwargs['preload_visible_threshold']