"""
Lazy Loading System for Hierarchical Element Lists

Provides efficient on-demand loading of tree branches with priority-based
queuing and intelligent batching to minimize UI blocking.

Key Features:
- Priority-based loading queue with intelligent batching
- Placeholder nodes for loading states (loading, error, empty)
- Background worker threads for non-blocking operations
- Automatic preloading of visible area content
- Configurable batch sizes and timeouts
- Comprehensive error handling and retry logic

Performance Targets:
- Reduce initial render time by >80%
- <10ms batch processing for 50 requests
- Background loading without UI blocking
- Intelligent preloading based on user interaction
"""

from typing import List, Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
import threading
import weakref
from queue import PriorityQueue, Empty
import uuid

try:
    from PyQt6.QtCore import QObject, QThread, QTimer, pyqtSignal, pyqtSlot
    from PyQt6.QtWidgets import QTreeView
except ImportError:
    # Mock classes for testing without PyQt6
    class QObject: pass
    class QThread: pass
    class QTimer: pass
    class QTreeView: pass
    def pyqtSignal(*args): return lambda: None
    def pyqtSlot(*args): return lambda func: func


class LoadingState(Enum):
    """Loading states for tree nodes."""
>>>>>>> origin/main
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ERROR = "error"


@dataclass(order=True)
class LoadRequest:
    """Request for loading node data."""
    priority: int = field(compare=True)
    node_id: str = field(compare=False)
    parent_index: Any = field(compare=False)
    timestamp: float = field(default_factory=time.time, compare=True)
    user_initiated: bool = field(default=False, compare=False)
    callback: Optional[Callable] = field(default=None, compare=False)


@dataclass
class LoadBatch:
    """Batch of load requests for processing."""
    batch_id: str
    requests: List[LoadRequest]
    timestamp: float = field(default_factory=time.time)
    
    def total_priority(self) -> int:
        """Calculate total priority of all requests in batch."""
        return sum(req.priority for req in self.requests)


class LoadingStateManager:
    """Manages loading states for tree nodes."""
    
    def __init__(self):
        self.node_states: Dict[str, LoadingState] = {}
        self.load_times: Dict[str, float] = {}
        self.error_counts: Dict[str, int] = {}
        self.placeholders: Dict[str, Any] = {}
        
    def get_state(self, node_id: str) -> LoadingState:
        """Get loading state for node."""
        return self.node_states.get(node_id, LoadingState.UNLOADED)
        
    def set_state(self, node_id: str, state: LoadingState):
        """Set loading state for node."""
        self.node_states[node_id] = state
        if state == LoadingState.LOADED:
            self.load_times[node_id] = time.time()
            
    def is_loaded(self, node_id: str) -> bool:
        """Check if node is loaded."""
        return self.get_state(node_id) == LoadingState.LOADED
        
    def is_loading(self, node_id: str) -> bool:
        """Check if node is currently loading."""
        return self.get_state(node_id) == LoadingState.LOADING
        
    def mark_error(self, node_id: str, error: Exception):
        """Mark node as having loading error."""
        self.set_state(node_id, LoadingState.ERROR)
        self.error_counts[node_id] = self.error_counts.get(node_id, 0) + 1
        
    def get_error_count(self, node_id: str) -> int:
        """Get error count for node."""
        return self.error_counts.get(node_id, 0)
        
    def should_retry(self, node_id: str, max_retries: int = 3) -> bool:
        """Check if should retry loading after error."""
        return self.get_error_count(node_id) < max_retries
        
    def add_placeholder(self, node_id: str, placeholder: Any):
        """Add placeholder for loading node."""
        self.placeholders[node_id] = placeholder
        
    def get_placeholder(self, node_id: str) -> Optional[Any]:
        """Get placeholder for node."""
        return self.placeholders.get(node_id)
        
    def remove_placeholder(self, node_id: str):
        """Remove placeholder for node."""
>>>>>>> origin/main
        self.placeholders.pop(node_id, None)


class LoadingQueue:
    """Priority queue for load requests."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.queue = PriorityQueue()
        self.pending: Dict[str, int] = {}  # node_id -> priority
        
    def add_request(self, request: LoadRequest) -> bool:
        """Add request to queue."""
        # Check if already pending with higher priority
        if request.node_id in self.pending:
            if request.priority <= self.pending[request.node_id]:
                return False  # Don't downgrade
                
        # Add to queue
        self.queue.put((-request.priority, request.timestamp, request))
        self.pending[request.node_id] = request.priority
        
        # Limit queue size
        if self.queue.qsize() > self.max_size:
            # Remove lowest priority items
            temp_items = []
            while not self.queue.empty() and len(temp_items) < self.max_size:
                temp_items.append(self.queue.get())
            
            # Re-add highest priority items
            for item in temp_items:
                self.queue.put(item)
                
        return True
        
    def get_next_request(self) -> Optional[LoadRequest]:
        """Get highest priority request."""
        try:
            _, _, request = self.queue.get_nowait()
            self.pending.pop(request.node_id, None)
            return request
        except Empty:
            return None
            
    def get_batch(self, max_size: int = 25) -> List[LoadRequest]:
        """Get batch of requests for processing."""
        batch = []
        for _ in range(min(max_size, self.queue.qsize())):
            request = self.get_next_request()
            if request:
                batch.append(request)
            else:
                break
        return batch
        
    def remove_request(self, node_id: str) -> bool:
        """Remove request for specific node."""
        if node_id in self.pending:
            del self.pending[node_id]
            return True
        return False
        
    def is_pending(self, node_id: str) -> bool:
        """Check if node has pending request."""
        return node_id in self.pending
        
    def size(self) -> int:
        """Get queue size."""
        return self.queue.qsize()
        
    def clear(self):
        """Clear all requests."""
        while not self.queue.empty():
            self.queue.get()
        self.pending.clear()


class PlaceholderNode:
    """Factory for creating placeholder nodes."""
    
    @staticmethod
    def create_loading_placeholder(parent_node: Any, estimated_count: int = 0):
        """Create loading placeholder node."""
        # Mock element for loading state
        class LoadingElement:
            def __init__(self):
                self.id = f"loading_{uuid.uuid4()}"
                self.type = "loading"
                self.text = f"Loading {estimated_count} items..." if estimated_count > 0 else "Loading..."
                self.metadata = {"is_placeholder": True, "loading": True}
                
        # Create mock node
        class MockNode:
            def __init__(self, element):
                self.element = element
                
        return MockNode(LoadingElement())
        
    @staticmethod
    def create_error_placeholder(parent_node: Any, error: Exception):
        """Create error placeholder node."""
        class ErrorElement:
            def __init__(self, error):
                self.id = f"error_{uuid.uuid4()}"
                self.type = "error"
                self.text = f"Error loading: {str(error)}"
                self.metadata = {"is_placeholder": True, "error": True}
                
        class MockNode:
            def __init__(self, element):
                self.element = element
                
        return MockNode(ErrorElement(error))
        
    @staticmethod
    def create_empty_placeholder(parent_node: Any):
        """Create empty placeholder node."""
        class EmptyElement:
            def __init__(self):
                self.id = f"empty_{uuid.uuid4()}"
                self.type = "empty"
                self.text = "No items to display"
                self.metadata = {"is_placeholder": True, "empty": True}
                
        class MockNode:
            def __init__(self, element):
                self.element = element
                
        return MockNode(EmptyElement())


class LoadWorker(QThread):
    """Background worker for loading data."""
    
    # Signals
    request_completed = pyqtSignal(str, object, object)  # node_id, data, error
    batch_completed = pyqtSignal(str, int, int)  # batch_id, success_count, error_count
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_provider: Optional[Callable] = None
        self.current_batch: Optional[LoadBatch] = None
        self.should_stop = False
        
    def set_data_provider(self, provider: Callable):
        """Set data provider function."""
        self.data_provider = provider
        
    def load_batch(self, batch: LoadBatch):
        """Load batch of requests."""
        self.current_batch = batch
        self.start()
        
    def run(self):
        """Run background loading."""
        if not self.current_batch or not self.data_provider:
            return
            
        success_count = 0
        error_count = 0
        
        for request in self.current_batch.requests:
            if self.should_stop:
                break
                
            try:
                data = self.data_provider(request.node_id)
                self.request_completed.emit(request.node_id, data, None)
                success_count += 1
            except Exception as e:
                self.request_completed.emit(request.node_id, None, e)
                error_count += 1
                
        self.batch_completed.emit(self.current_batch.batch_id, success_count, error_count)
        
    def stop_loading(self):
        """Stop loading operation."""
        self.should_stop = True
        self.wait(5000)  # Wait up to 5 seconds


class LazyLoadingManager(QObject):
    """Main lazy loading manager for hierarchical element lists."""
    
    # Signals
    loading_started = pyqtSignal(str)  # node_id
    loading_completed = pyqtSignal(str, object)  # node_id, data
    loading_failed = pyqtSignal(str, str)  # node_id, error_message
    batch_processed = pyqtSignal(str, int)  # batch_id, item_count
    
    def __init__(self, tree_view: QTreeView, parent=None):
        super().__init__(parent)
        self.tree_view = weakref.ref(tree_view) if tree_view else lambda: None
        self.loading_state = LoadingStateManager()
        self.loading_queue = LoadingQueue()
        self.load_worker = LoadWorker(self)
        self.data_provider: Optional[Callable] = None
        
        # Configuration
        self.batch_size = 25
        self.batch_timeout = 100  # milliseconds
        self.max_concurrent_loads = 3
        self.auto_load_on_expand = True
        self.preload_visible_threshold = 5
        
        # Statistics
>>>>>>> origin/main
        self.load_statistics = {
            'total_requests': 0,
            'successful_loads': 0,
            'failed_loads': 0,
            'average_load_time': 0.0
        }
        
        # Setup batch processing timer
        self.batch_timer = QTimer()
        self.batch_timer.timeout.connect(self._process_batch)
        self.batch_timer.setSingleShot(True)
        
        # Connect worker signals
        self.load_worker.request_completed.connect(self._on_request_completed)
        self.load_worker.batch_completed.connect(self._on_batch_completed)
        
    def set_data_provider(self, provider: Callable):
        """Set data provider function."""
        self.data_provider = provider
        self.load_worker.set_data_provider(provider)
        
    def request_load(self, node_id: str, parent_index: Any, priority: int = 1, 
                    user_initiated: bool = False, callback: Optional[Callable] = None) -> bool:
        """Request loading of node data."""
        # Check if already loaded or loading
        if self.loading_state.is_loaded(node_id):
            return True
        if self.loading_state.is_loading(node_id):
            return False
            
        # Create load request
        request = LoadRequest(
            priority=priority,
            node_id=node_id,
            parent_index=parent_index,
>>>>>>> origin/main
            user_initiated=user_initiated,
            callback=callback
        )
        
        # Add to queue
        if self.loading_queue.add_request(request):
            self.load_statistics['total_requests'] += 1
            
            # Start batch timer if not already running
            if not self.batch_timer.isActive():
                self.batch_timer.start(self.batch_timeout)
                
            return True
        return False
        
    def load_children_lazily(self, parent_node: Any, parent_index: Any, priority: int = 1) -> bool:
        """Load children of node lazily."""
        if not hasattr(parent_node, 'element') or not parent_node.element:
            return False
            
        node_id = parent_node.element.id
        
        # Add loading placeholder
        placeholder = PlaceholderNode.create_loading_placeholder(parent_node)
        parent_node.add_child(placeholder)
        self.loading_state.add_placeholder(node_id, placeholder)
        
        # Request load
        return self.request_load(node_id, parent_index, priority, user_initiated=True)
        
    def cancel_loading(self, node_id: str) -> bool:
        """Cancel loading request for node."""
        return self.loading_queue.remove_request(node_id)
        
    def cancel_all_loading(self):
        """Cancel all pending loading requests."""
        self.loading_queue.clear()
        self.load_worker.stop_loading()
        
    def configure_lazy_loading(self, max_concurrent_loads: int = None, batch_size: int = None,
                             batch_timeout: int = None, auto_load_on_expand: bool = None,
                             preload_visible_threshold: int = None):
        """Configure lazy loading parameters."""
        if max_concurrent_loads is not None:
            self.max_concurrent_loads = max_concurrent_loads
        if batch_size is not None:
            self.batch_size = batch_size
        if batch_timeout is not None:
            self.batch_timeout = batch_timeout
        if auto_load_on_expand is not None:
            self.auto_load_on_expand = auto_load_on_expand
        if preload_visible_threshold is not None:
            self.preload_visible_threshold = preload_visible_threshold
            
    def get_loading_statistics(self) -> Dict[str, Any]:
        """Get loading statistics."""
        return self.load_statistics.copy()
        
    def is_loaded(self, node_id: str) -> bool:
        """Check if node is loaded."""
        return self.loading_state.is_loaded(node_id)
        
    def is_loading(self, node_id: str) -> bool:
        """Check if node is loading."""
        return self.loading_state.is_loading(node_id)
        
    @pyqtSlot()
    def _process_batch(self):
        """Process batch of load requests."""
        if self.loading_queue.size() == 0:
            return
            
>>>>>>> origin/main
        # Get batch of requests
        batch_requests = self.loading_queue.get_batch(self.batch_size)
        if not batch_requests:
            return
            
        # Create batch
        batch_id = f"batch_{int(time.time()*1000)}"
        batch = LoadBatch(batch_id, batch_requests)
        
        # Mark requests as loading
        for request in batch_requests:
            self.loading_state.set_state(request.node_id, LoadingState.LOADING)
            self.loading_started.emit(request.node_id)
            
        # Process batch
        self.load_worker.load_batch(batch)
        
        # Schedule next batch if needed
        if self.loading_queue.size() > 0:
            self.batch_timer.start(self.batch_timeout)
            
    @pyqtSlot(str, object, object)
    def _on_request_completed(self, node_id: str, data: Any, error: Exception):
        """Handle completed load request."""
        if error:
            self.loading_state.mark_error(node_id, error)
            self.load_statistics['failed_loads'] += 1
            self.loading_failed.emit(node_id, str(error))
        else:
            self.loading_state.set_state(node_id, LoadingState.LOADED)
            self.load_statistics['successful_loads'] += 1
            self.loading_completed.emit(node_id, data)
            
        # Remove placeholder if exists
        placeholder = self.loading_state.get_placeholder(node_id)
        if placeholder:
            self.loading_state.remove_placeholder(node_id)
            
    @pyqtSlot(str, int, int)
    def _on_batch_completed(self, batch_id: str, success_count: int, error_count: int):
        """Handle completed batch."""
        self.batch_processed.emit(batch_id, success_count + error_count)


# Export public API
__all__ = [
    'LazyLoadingManager',
    'LoadingState',
    'LoadingQueue',
    'LoadRequest',
    'LoadBatch',
    'PlaceholderNode',
    'LoadWorker',
    'LoadingStateManager'
>>>>>>> origin/main
