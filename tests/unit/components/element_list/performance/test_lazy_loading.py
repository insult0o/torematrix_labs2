"""
Tests for Lazy Loading System

Comprehensive test suite for lazy loading performance optimization.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import time
from PyQt6.QtCore import QModelIndex, QTimer
from PyQt6.QtWidgets import QTreeView, QApplication

from src.torematrix.ui.components.element_list.performance.lazy_loading import (
    LazyLoadingManager, LoadingState, LoadingQueue, LoadRequest,
    PlaceholderNode, LoadWorker, LoadBatch
)
from src.torematrix.ui.components.element_list.models.tree_node import TreeNode


@pytest.fixture
def mock_tree_view():
    """Create mock tree view."""
    tree_view = Mock(spec=QTreeView)
    tree_view.model.return_value = Mock()
    tree_view.expanded = Mock()
    tree_view.collapsed = Mock()
    tree_view.viewport.return_value = Mock()
    return tree_view


@pytest.fixture
def mock_element():
    """Create mock element."""
    element = Mock()
    element.id = "test_element_1"
    element.type = "text"
    element.text = "Test content"
    element.confidence = 0.95
    return element


@pytest.fixture
def sample_tree_node(mock_element):
    """Create sample tree node."""
    return TreeNode(mock_element)


class TestLoadRequest:
    """Test load request functionality."""
    
    def test_request_creation(self):
        """Test creating load request."""
        index = Mock()
        request = LoadRequest(
            node_id="test_node_1",
            parent_index=index,
            priority=5,
            user_initiated=True
        )
        
        assert request.node_id == "test_node_1"
        assert request.parent_index == index
        assert request.priority == 5
        assert request.user_initiated is True
        assert request.callback is None
    
    def test_request_sorting(self):
        """Test request priority sorting."""
        request1 = LoadRequest("node1", Mock(), priority=1)
        request2 = LoadRequest("node2", Mock(), priority=5)
        request3 = LoadRequest("node3", Mock(), priority=3)
        
        # Sort by priority (higher first)
        requests = [request1, request2, request3]
        requests.sort()
        
        assert requests[0].priority == 5
        assert requests[1].priority == 3
        assert requests[2].priority == 1
    
    def test_request_timestamp_sorting(self):
        """Test sorting by timestamp when priority is same."""
        import time
        
        request1 = LoadRequest("node1", Mock(), priority=5)
        time.sleep(0.001)
        request2 = LoadRequest("node2", Mock(), priority=5)
        
        # Earlier timestamp should come first
        assert request1 < request2


class TestLoadBatch:
    """Test load batch functionality."""
    
    def test_batch_creation(self):
        """Test creating load batch."""
        requests = [
            LoadRequest("node1", Mock(), priority=5),
            LoadRequest("node2", Mock(), priority=3),
            LoadRequest("node3", Mock(), priority=1)
        ]
        
        batch = LoadBatch(requests=requests, batch_id="batch_1")
        
        assert batch.batch_id == "batch_1"
        assert len(batch.requests) == 3
        assert batch.total_priority() == 9


class TestLoadingState:
    """Test loading state tracking."""
    
    def test_state_initialization(self):
        """Test loading state initialization."""
        state = LoadingState()
        
        assert state.get_state("any_node") == LoadingState.UNLOADED
        assert not state.is_loaded("any_node")
        assert not state.is_loading("any_node")
    
    def test_state_transitions(self):
        """Test state transitions."""
        state = LoadingState()
        node_id = "test_node"
        
        # Unloaded -> Loading
        state.set_state(node_id, LoadingState.LOADING)
        assert state.is_loading(node_id)
        assert not state.is_loaded(node_id)
        
        # Loading -> Loaded
        state.set_state(node_id, LoadingState.LOADED)
        assert state.is_loaded(node_id)
        assert not state.is_loading(node_id)
    
    def test_error_handling(self):
        """Test error state handling."""
        state = LoadingState()
        node_id = "test_node"
        
        error = Exception("Test error")
        state.mark_error(node_id, error)
        
        assert state.get_state(node_id) == LoadingState.ERROR
        assert state.get_error_count(node_id) == 1
        assert state.should_retry(node_id, max_retries=3)
        
        # Multiple errors
        state.mark_error(node_id, error)
        state.mark_error(node_id, error)
        state.mark_error(node_id, error)
        
        assert state.get_error_count(node_id) == 4
        assert not state.should_retry(node_id, max_retries=3)
    
    def test_placeholder_management(self):
        """Test placeholder node management."""
        state = LoadingState()
        node_id = "test_node"
        placeholder = Mock()
        
        state.add_placeholder(node_id, placeholder)
        assert state.get_placeholder(node_id) == placeholder
        
        state.remove_placeholder(node_id)
        assert state.get_placeholder(node_id) is None


class TestLoadingQueue:
    """Test loading queue functionality."""
    
    def test_queue_initialization(self):
        """Test queue initialization."""
        queue = LoadingQueue(max_size=100)
        
        assert queue.max_size == 100
        assert queue.size() == 0
        assert not queue.is_pending("any_node")
    
    def test_add_request(self):
        """Test adding requests to queue."""
        queue = LoadingQueue(max_size=10)
        
        request = LoadRequest("node1", Mock(), priority=5)
        result = queue.add_request(request)
        
        assert result is True
        assert queue.size() == 1
        assert queue.is_pending("node1")
    
    def test_priority_replacement(self):
        """Test replacing lower priority requests."""
        queue = LoadingQueue(max_size=10)
        
        # Add low priority request
        low_priority = LoadRequest("node1", Mock(), priority=1)
        queue.add_request(low_priority)
        
        # Add high priority request for same node
        high_priority = LoadRequest("node1", Mock(), priority=5)
        result = queue.add_request(high_priority)
        
        assert result is True
        assert queue.size() == 1
        
        # Should have high priority request
        next_request = queue.get_next_request()
        assert next_request.priority == 5
    
    def test_no_downgrade(self):
        """Test that higher priority requests are not replaced by lower."""
        queue = LoadingQueue(max_size=10)
        
        # Add high priority request
        high_priority = LoadRequest("node1", Mock(), priority=5)
        queue.add_request(high_priority)
        
        # Try to add low priority request for same node
        low_priority = LoadRequest("node1", Mock(), priority=1)
        result = queue.add_request(low_priority)
        
        assert result is False  # Should not replace
        assert queue.size() == 1
    
    def test_queue_size_limit(self):
        """Test queue size limit enforcement."""
        queue = LoadingQueue(max_size=3)
        
        # Fill queue to capacity
        for i in range(3):
            request = LoadRequest(f"node{i}", Mock(), priority=i)
            queue.add_request(request)
        
        assert queue.size() == 3
        
        # Add one more (should evict lowest priority)
        high_priority = LoadRequest("node_high", Mock(), priority=10)
        result = queue.add_request(high_priority)
        
        assert result is True
        assert queue.size() == 3  # Still at max size
        
        # Lowest priority should be evicted
        assert not queue.is_pending("node0")
    
    def test_get_batch(self):
        """Test getting batch of requests."""
        queue = LoadingQueue(max_size=10)
        
        # Add multiple requests
        for i in range(5):
            request = LoadRequest(f"node{i}", Mock(), priority=i)
            queue.add_request(request)
        
        # Get batch of 3
        batch = queue.get_batch(max_size=3)
        
        assert len(batch) == 3
        assert queue.size() == 2  # Remaining requests
        
        # Should be in priority order (highest first)
        priorities = [req.priority for req in batch]
        assert priorities == sorted(priorities, reverse=True)
    
    def test_remove_request(self):
        """Test removing specific request."""
        queue = LoadingQueue(max_size=10)
        
        request = LoadRequest("node1", Mock(), priority=5)
        queue.add_request(request)
        
        assert queue.is_pending("node1")
        
        result = queue.remove_request("node1")
        
        assert result is True
        assert not queue.is_pending("node1")
        assert queue.size() == 0
    
    def test_clear_queue(self):
        """Test clearing entire queue."""
        queue = LoadingQueue(max_size=10)
        
        # Add multiple requests
        for i in range(5):
            request = LoadRequest(f"node{i}", Mock(), priority=i)
            queue.add_request(request)
        
        queue.clear()
        
        assert queue.size() == 0
        for i in range(5):
            assert not queue.is_pending(f"node{i}")


class TestPlaceholderNode:
    """Test placeholder node creation."""
    
    def test_create_loading_placeholder(self, sample_tree_node):
        """Test creating loading placeholder."""
        placeholder = PlaceholderNode.create_loading_placeholder(sample_tree_node, estimated_count=5)
        
        assert placeholder.element is not None
        assert placeholder.element.type == "loading"
        assert "Loading 5 items" in placeholder.element.text
        assert placeholder.element.metadata.get("is_placeholder") is True
        assert placeholder.element.metadata.get("loading") is True
    
    def test_create_error_placeholder(self, sample_tree_node):
        """Test creating error placeholder."""
        error = Exception("Network error")
        placeholder = PlaceholderNode.create_error_placeholder(sample_tree_node, error)
        
        assert placeholder.element is not None
        assert placeholder.element.type == "error"
        assert "Error loading: Network error" in placeholder.element.text
        assert placeholder.element.metadata.get("is_placeholder") is True
        assert placeholder.element.metadata.get("error") is True
    
    def test_create_empty_placeholder(self, sample_tree_node):
        """Test creating empty placeholder."""
        placeholder = PlaceholderNode.create_empty_placeholder(sample_tree_node)
        
        assert placeholder.element is not None
        assert placeholder.element.type == "empty"
        assert "No items to display" in placeholder.element.text
        assert placeholder.element.metadata.get("is_placeholder") is True
        assert placeholder.element.metadata.get("empty") is True


class TestLoadWorker:
    """Test load worker functionality."""
    
    def setup_method(self):
        """Setup test method."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
    
    def test_worker_initialization(self):
        """Test worker initialization."""
        worker = LoadWorker()
        
        assert worker.data_provider is None
        assert worker.current_batch is None
        assert not worker.should_stop
    
    def test_set_data_provider(self):
        """Test setting data provider."""
        worker = LoadWorker()
        
        def test_provider(node_id):
            return f"data_for_{node_id}"
        
        worker.set_data_provider(test_provider)
        assert worker.data_provider == test_provider
    
    @patch('src.torematrix.ui.components.element_list.performance.lazy_loading.LoadWorker.start')
    def test_load_batch(self, mock_start):
        """Test loading batch."""
        worker = LoadWorker()
        
        requests = [LoadRequest("node1", Mock(), priority=5)]
        batch = LoadBatch(requests=requests, batch_id="batch_1")
        
        worker.load_batch(batch)
        
        assert worker.current_batch == batch
        mock_start.assert_called_once()
    
    def test_stop_loading(self):
        """Test stopping loading operation."""
        worker = LoadWorker()
        
        worker.stop_loading()
        
        assert worker.should_stop is True


class TestLazyLoadingManager:
    """Test main lazy loading manager."""
    
    def setup_method(self):
        """Setup test method."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
    
    def test_manager_initialization(self, mock_tree_view):
        """Test manager initialization."""
        manager = LazyLoadingManager(mock_tree_view)
        
        assert manager.tree_view() == mock_tree_view
        assert isinstance(manager.loading_state, LoadingState)
        assert isinstance(manager.loading_queue, LoadingQueue)
        assert manager.auto_load_on_expand is True
    
    def test_set_data_provider(self, mock_tree_view):
        """Test setting data provider."""
        manager = LazyLoadingManager(mock_tree_view)
        
        def test_provider(node_id):
            return f"data_for_{node_id}"
        
        manager.set_data_provider(test_provider)
        assert manager.data_provider == test_provider
    
    def test_request_load_new_node(self, mock_tree_view):
        """Test requesting load for new node."""
        manager = LazyLoadingManager(mock_tree_view)
        
        index = Mock()
        result = manager.request_load("node1", index, priority=5, user_initiated=True)
        
        assert result is True
        assert manager.loading_queue.is_pending("node1")
    
    def test_request_load_already_loaded(self, mock_tree_view):
        """Test requesting load for already loaded node."""
        manager = LazyLoadingManager(mock_tree_view)
        
        # Mark as loaded
        manager.loading_state.set_state("node1", LoadingState.LOADED)
        
        index = Mock()
        result = manager.request_load("node1", index, priority=5)
        
        assert result is True  # Returns True but doesn't queue
        assert not manager.loading_queue.is_pending("node1")
    
    def test_request_load_already_loading(self, mock_tree_view):
        """Test requesting load for node that's already loading."""
        manager = LazyLoadingManager(mock_tree_view)
        
        # Mark as loading
        manager.loading_state.set_state("node1", LoadingState.LOADING)
        
        index = Mock()
        result = manager.request_load("node1", index, priority=5)
        
        assert result is False  # Already loading
    
    def test_load_children_lazily(self, mock_tree_view, sample_tree_node):
        """Test lazy loading of children."""
        manager = LazyLoadingManager(mock_tree_view)
        
        index = Mock()
        result = manager.load_children_lazily(sample_tree_node, index, priority=3)
        
        assert result is True
        
        # Should have added placeholder
        assert sample_tree_node.child_count() == 1
        placeholder_child = sample_tree_node.get_child(0)
        assert placeholder_child.element.metadata.get("is_placeholder") is True
    
    def test_cancel_loading(self, mock_tree_view):
        """Test canceling loading request."""
        manager = LazyLoadingManager(mock_tree_view)
        
        # Add request
        index = Mock()
        manager.request_load("node1", index, priority=5)
        
        assert manager.loading_queue.is_pending("node1")
        
        # Cancel request
        result = manager.cancel_loading("node1")
        
        assert result is True
        assert not manager.loading_queue.is_pending("node1")
    
    def test_cancel_all_loading(self, mock_tree_view):
        """Test canceling all loading requests."""
        manager = LazyLoadingManager(mock_tree_view)
        
        # Add multiple requests
        index = Mock()
        for i in range(3):
            manager.request_load(f"node{i}", index, priority=i)
        
        assert manager.loading_queue.size() == 3
        
        # Cancel all
        manager.cancel_all_loading()
        
        assert manager.loading_queue.size() == 0
    
    def test_configuration(self, mock_tree_view):
        """Test configuration settings."""
        manager = LazyLoadingManager(mock_tree_view)
        
        # Test configuration
        manager.configure_lazy_loading(
            max_concurrent_loads=5,
            batch_size=20,
            batch_timeout=200,
            auto_load_on_expand=False,
            preload_visible_threshold=10
        )
        
        assert manager.max_concurrent_loads == 5
        assert manager.batch_size == 20
        assert manager.batch_timeout == 200
        assert manager.auto_load_on_expand is False
        assert manager.preload_visible_threshold == 10
    
    def test_get_statistics(self, mock_tree_view):
        """Test getting loading statistics."""
        manager = LazyLoadingManager(mock_tree_view)
        
        # Simulate some activity
        manager.load_statistics['total_requests'] = 10
        manager.load_statistics['successful_loads'] = 8
        manager.load_statistics['failed_loads'] = 2
        
        stats = manager.get_loading_statistics()
        
        assert stats['total_requests'] == 10
        assert stats['successful_loads'] == 8
        assert stats['failed_loads'] == 2
    
    def test_is_loaded_and_loading_states(self, mock_tree_view):
        """Test checking loading states."""
        manager = LazyLoadingManager(mock_tree_view)
        
        # Initially unloaded
        assert not manager.is_loaded("node1")
        assert not manager.is_loading("node1")
        
        # Set loading
        manager.loading_state.set_state("node1", LoadingState.LOADING)
        assert not manager.is_loaded("node1")
        assert manager.is_loading("node1")
        
        # Set loaded
        manager.loading_state.set_state("node1", LoadingState.LOADED)
        assert manager.is_loaded("node1")
        assert not manager.is_loading("node1")


class TestLazyLoadingIntegration:
    """Integration tests for lazy loading system."""
    
    def setup_method(self):
        """Setup test method."""
        if not QApplication.instance():
            self.app = QApplication([])
        else:
            self.app = QApplication.instance()
    
    def test_complete_loading_workflow(self, mock_tree_view):
        """Test complete loading workflow."""
        manager = LazyLoadingManager(mock_tree_view)
        
        # Setup data provider
        def mock_data_provider(node_id):
            return {"id": node_id, "children": [f"{node_id}_child_{i}" for i in range(3)]}
        
        manager.set_data_provider(mock_data_provider)
        
        # Request load
        index = Mock()
        result = manager.request_load("root", index, priority=5, user_initiated=True)
        
        assert result is True
        assert manager.loading_queue.is_pending("root")
        
        # Simulate batch processing (normally done by timer)
        manager._process_batch()
        
        # Check that request was processed
        assert not manager.loading_queue.is_pending("root")
    
    def test_error_handling_workflow(self, mock_tree_view):
        """Test error handling in loading workflow."""
        manager = LazyLoadingManager(mock_tree_view)
        
        # Setup data provider that throws error
        def failing_data_provider(node_id):
            raise Exception("Network error")
        
        manager.set_data_provider(failing_data_provider)
        
        # Request load
        index = Mock()
        manager.request_load("failing_node", index, priority=5)
        
        # Simulate processing and error
        manager._on_request_completed("failing_node", None, Exception("Network error"))
        
        # Should be in error state
        assert manager.loading_state.get_state("failing_node") == LoadingState.ERROR
        assert manager.loading_state.get_error_count("failing_node") == 1
    
    def test_large_queue_performance(self, mock_tree_view):
        """Test performance with large number of requests."""
        manager = LazyLoadingManager(mock_tree_view)
        
        # Add many requests
        index = Mock()
        for i in range(1000):
            manager.request_load(f"node_{i}", index, priority=i % 10)
        
        # Should handle efficiently
        assert manager.loading_queue.size() <= manager.loading_queue.max_size
        
        # Get batch should be fast
        import time
        start_time = time.time()
        batch = manager.loading_queue.get_batch(max_size=50)
        end_time = time.time()
        
        assert (end_time - start_time) < 0.1  # Should be very fast
        assert len(batch) <= 50


class TestLazyLoadingEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_loading_with_no_data_provider(self, mock_tree_view):
        """Test loading without data provider."""
        manager = LazyLoadingManager(mock_tree_view)
        
        # No data provider set
        index = Mock()
        result = manager.request_load("node1", index, priority=5)
        
        # Should still queue the request
        assert result is True
        assert manager.loading_queue.is_pending("node1")
    
    def test_loading_with_invalid_node(self, mock_tree_view):
        """Test loading with invalid node data."""
        manager = LazyLoadingManager(mock_tree_view)
        
        # Try to load children of node without element
        node_without_element = TreeNode(None)
        index = Mock()
        
        result = manager.load_children_lazily(node_without_element, index)
        
        assert result is False  # Should fail gracefully
    
    def test_placeholder_cleanup_on_error(self, mock_tree_view, sample_tree_node):
        """Test placeholder cleanup when loading fails."""
        manager = LazyLoadingManager(mock_tree_view)
        
        # Setup node with loading placeholder
        node_id = sample_tree_node.element.id
        placeholder = PlaceholderNode.create_loading_placeholder(sample_tree_node)
        sample_tree_node.add_child(placeholder)
        manager.loading_state.add_placeholder(node_id, placeholder)
        
        # Simulate loading error
        error = Exception("Load failed")
        manager._on_request_completed(node_id, None, error)
        
        # Should replace loading placeholder with error placeholder
        assert sample_tree_node.child_count() == 1
        error_child = sample_tree_node.get_child(0)
        assert error_child.element.type == "error"


if __name__ == "__main__":
    pytest.main([__file__])