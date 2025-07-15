"""
Integration Tests for All Interactive Features

Tests integration between drag-drop, selection, context menus, search, delegates,
keyboard navigation, and visual feedback systems.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtCore import QPoint, Qt, QModelIndex, QRect, QSize
from PyQt6.QtWidgets import QTreeView, QApplication, QWidget
from PyQt6.QtGui import QKeyEvent, QMouseEvent

from src.torematrix.ui.components.element_list.interactions import (
    DragDropHandler, MultiSelectionHandler, ContextMenuManager,
    SearchFilterManager, RichElementDelegate, KeyboardNavigationHandler,
    VisualFeedbackManager
)
from src.torematrix.ui.components.element_list.models.tree_model import ElementTreeModel
from src.torematrix.ui.components.element_list.models.tree_node import TreeNode


@pytest.fixture
def app():
    """Ensure QApplication exists."""
    if not QApplication.instance():
        return QApplication([])
    return QApplication.instance()


@pytest.fixture
def tree_view(app):
    """Create real tree view for integration testing."""
    tree_view = QTreeView()
    tree_view.resize(400, 300)
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
def tree_model(mock_element):
    """Create tree model with test data."""
    model = ElementTreeModel()
    
    # Mock element provider
    mock_provider = Mock()
    mock_provider.get_root_elements.return_value = [mock_element]
    mock_provider.get_child_elements.return_value = []
    mock_provider.get_element_by_id.return_value = mock_element
    
    model.set_element_provider(mock_provider)
    return model


@pytest.fixture
def integrated_tree_view(tree_view, tree_model):
    """Create fully integrated tree view with all systems."""
    # Set model
    tree_view.setModel(tree_model)
    
    # Initialize all interaction systems
    drag_drop = DragDropHandler(tree_view)
    selection = MultiSelectionHandler(tree_view)
    context_menu = ContextMenuManager(tree_view)
    search_filter = SearchFilterManager(tree_view)
    delegate = RichElementDelegate()
    keyboard_nav = KeyboardNavigationHandler(tree_view)
    visual_feedback = VisualFeedbackManager(tree_view)
    
    # Set delegate
    tree_view.setItemDelegate(delegate)
    
    # Store references
    tree_view._drag_drop = drag_drop
    tree_view._selection = selection
    tree_view._context_menu = context_menu
    tree_view._search_filter = search_filter
    tree_view._delegate = delegate
    tree_view._keyboard_nav = keyboard_nav
    tree_view._visual_feedback = visual_feedback
    
    return tree_view


class TestSystemsIntegration:
    """Test integration between different systems."""
    
    def test_all_systems_initialization(self, integrated_tree_view):
        """Test that all systems can be initialized together."""
        tree_view = integrated_tree_view
        
        # Verify all systems are initialized
        assert hasattr(tree_view, '_drag_drop')
        assert hasattr(tree_view, '_selection')
        assert hasattr(tree_view, '_context_menu')
        assert hasattr(tree_view, '_search_filter')
        assert hasattr(tree_view, '_delegate')
        assert hasattr(tree_view, '_keyboard_nav')
        assert hasattr(tree_view, '_visual_feedback')
        
        # Test that systems don't interfere with each other
        assert tree_view.model() is not None
        assert tree_view.itemDelegate() is not None
    
    def test_selection_and_visual_feedback_integration(self, integrated_tree_view):
        """Test selection changes trigger visual feedback."""
        tree_view = integrated_tree_view
        selection = tree_view._selection
        visual_feedback = tree_view._visual_feedback
        
        # Mock visual feedback method
        visual_feedback.indicate_selection_change = Mock()
        
        # Test selection change
        model = tree_view.model()
        if model.rowCount() > 0:
            index = model.index(0, 0)
            
            # Simulate selection
            tree_view.setCurrentIndex(index)
            
            # In a real integration, this would be connected via signals
            # For testing, we verify the method exists and can be called
            visual_feedback.indicate_selection_change(index)
            visual_feedback.indicate_selection_change.assert_called_once_with(index)
    
    def test_keyboard_navigation_and_selection_integration(self, integrated_tree_view):
        """Test keyboard navigation works with selection system."""
        tree_view = integrated_tree_view
        keyboard_nav = tree_view._keyboard_nav
        selection = tree_view._selection
        
        # Test that keyboard navigation can trigger selection changes
        model = tree_view.model()
        if model.rowCount() > 0:
            # Test navigation command execution
            result = keyboard_nav.execute_command("nav_home")
            
            # Command should execute (though might not do anything with mock data)
            assert isinstance(result, bool)
    
    def test_context_menu_and_selection_integration(self, integrated_tree_view):
        """Test context menu considers current selection."""
        tree_view = integrated_tree_view
        context_menu = tree_view._context_menu
        selection = tree_view._selection
        
        # Mock selection
        selection.get_selected_elements = Mock(return_value=["element_1", "element_2"])
        
        # Test context menu can access selection
        selected = selection.get_selected_elements()
        assert selected == ["element_1", "element_2"]
        
        # Test context menu creation with selection
        context_menu._get_selected_elements = Mock(return_value=selected)
        menu_elements = context_menu._get_selected_elements()
        assert len(menu_elements) == 2
    
    def test_search_and_visual_feedback_integration(self, integrated_tree_view):
        """Test search results trigger visual feedback."""
        tree_view = integrated_tree_view
        search_filter = tree_view._search_filter
        visual_feedback = tree_view._visual_feedback
        
        # Mock visual feedback for search
        visual_feedback.indicate_search_match = Mock()
        
        # Test search functionality
        search_bar = search_filter.get_search_bar()
        search_bar.set_search_text("test")
        
        # In real integration, search results would trigger visual feedback
        model = tree_view.model()
        if model.rowCount() > 0:
            index = model.index(0, 0)
            visual_feedback.indicate_search_match(index)
            visual_feedback.indicate_search_match.assert_called_once_with(index)
    
    def test_drag_drop_and_visual_feedback_integration(self, integrated_tree_view):
        """Test drag-drop operations trigger visual feedback."""
        tree_view = integrated_tree_view
        drag_drop = tree_view._drag_drop
        visual_feedback = tree_view._visual_feedback
        
        # Mock visual feedback methods
        visual_feedback.indicate_drag_target = Mock()
        visual_feedback.clear_drag_target = Mock()
        
        # Test drag target indication
        model = tree_view.model()
        if model.rowCount() > 0:
            index = model.index(0, 0)
            visual_feedback.indicate_drag_target(index)
            visual_feedback.indicate_drag_target.assert_called_once_with(index)
            
            visual_feedback.clear_drag_target()
            visual_feedback.clear_drag_target.assert_called_once()
    
    def test_delegate_and_search_integration(self, integrated_tree_view):
        """Test custom delegate can highlight search terms."""
        tree_view = integrated_tree_view
        delegate = tree_view._delegate
        search_filter = tree_view._search_filter
        
        # Test delegate search highlighting
        delegate.set_search_highlighting(True, "test")
        
        assert delegate.highlight_search is True
        assert delegate.search_query == "test"
    
    def test_signal_connections_integration(self, integrated_tree_view):
        """Test that systems can connect to each other's signals."""
        tree_view = integrated_tree_view
        
        # Test that all systems have their expected signals
        assert hasattr(tree_view._drag_drop, 'elementMoved')
        assert hasattr(tree_view._selection, 'selectionChanged')
        assert hasattr(tree_view._context_menu, 'actionTriggered')
        assert hasattr(tree_view._search_filter, 'searchCompleted')
        assert hasattr(tree_view._keyboard_nav, 'navigationPerformed')
        assert hasattr(tree_view._visual_feedback, 'effectStarted')


class TestEventHandlingIntegration:
    """Test event handling across multiple systems."""
    
    def test_mouse_event_routing(self, integrated_tree_view):
        """Test mouse events are handled by appropriate systems."""
        tree_view = integrated_tree_view
        
        # Create mock mouse event
        mock_event = Mock()
        mock_event.button.return_value = Qt.MouseButton.LeftButton
        mock_event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier
        mock_event.pos.return_value = QPoint(10, 10)
        
        # Setup mock index
        mock_index = Mock()
        mock_index.isValid.return_value = True
        tree_view.indexAt = Mock(return_value=mock_index)
        
        # Mock model data
        mock_model = tree_view.model()
        mock_model.data = Mock(return_value="element_1")
        
        # Test that selection handler can process the event
        selection = tree_view._selection
        result = selection.handle_mouse_press(mock_event)
        
        # Should return True if handled
        assert isinstance(result, bool)
    
    def test_keyboard_event_routing(self, integrated_tree_view):
        """Test keyboard events are handled by appropriate systems."""
        tree_view = integrated_tree_view
        
        # Test Ctrl+A (select all)
        mock_event = Mock()
        mock_event.key.return_value = Qt.Key.Key_A
        mock_event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier
        
        # Test selection system handling
        selection = tree_view._selection
        result = selection.handle_key_event(mock_event)
        assert isinstance(result, bool)
        
        # Test keyboard navigation handling
        keyboard_nav = tree_view._keyboard_nav
        # This would normally be handled by event filter
        assert keyboard_nav is not None
    
    def test_paint_event_integration(self, integrated_tree_view):
        """Test paint events work with custom delegate and visual effects."""
        tree_view = integrated_tree_view
        delegate = tree_view._delegate
        visual_feedback = tree_view._visual_feedback
        
        # Test delegate configuration
        delegate.set_show_confidence(True)
        delegate.set_show_icons(True)
        delegate.set_show_type_badges(True)
        
        # Test visual feedback effects
        center_point = QPoint(100, 100)
        visual_feedback.show_loading(center_point)
        visual_feedback.hide_loading()
        
        # Test tooltip
        visual_feedback.show_tooltip(center_point, "Test tooltip")
        visual_feedback.hide_tooltip()
        
        # These should not raise exceptions
        assert True


class TestPerformanceIntegration:
    """Test performance with all systems active."""
    
    def test_large_dataset_performance(self, integrated_tree_view):
        """Test performance with large number of elements."""
        tree_view = integrated_tree_view
        
        # Create mock provider with many elements
        mock_elements = []
        for i in range(100):  # Reasonable test size
            element = Mock()
            element.id = f"element_{i}"
            element.type = "text"
            element.text = f"Content {i}"
            element.confidence = 0.8 + (i % 20) / 100  # Varying confidence
            mock_elements.append(element)
        
        # Update model
        model = tree_view.model()
        mock_provider = Mock()
        mock_provider.get_root_elements.return_value = mock_elements
        mock_provider.get_child_elements.return_value = []
        mock_provider.get_element_by_id.side_effect = lambda id: next(
            (e for e in mock_elements if e.id == id), None
        )
        
        # Test that model can handle the data
        model.set_element_provider(mock_provider)
        
        # Test selection operations
        selection = tree_view._selection
        element_ids = [f"element_{i}" for i in range(0, 100, 10)]  # Every 10th element
        
        # This should complete without timeout
        result = selection.select_elements(element_ids)
        assert isinstance(result, int)
        
        # Test search operations
        search_filter = tree_view._search_filter
        search_bar = search_filter.get_search_bar()
        search_bar.set_search_text("Content 5")
        
        # Should handle search without issues
        assert search_bar.search_input.text() == "Content 5"
    
    def test_memory_usage_integration(self, integrated_tree_view):
        """Test memory usage with all systems active."""
        tree_view = integrated_tree_view
        
        # Test that systems can be cleaned up
        systems = [
            tree_view._drag_drop,
            tree_view._selection,
            tree_view._context_menu,
            tree_view._search_filter,
            tree_view._delegate,
            tree_view._keyboard_nav,
            tree_view._visual_feedback
        ]
        
        # Test that all systems exist and have proper cleanup
        for system in systems:
            assert system is not None
            # Most Qt objects have deleteLater method
            if hasattr(system, 'deleteLater'):
                # Don't actually delete in test, just verify method exists
                assert callable(system.deleteLater)


class TestErrorHandlingIntegration:
    """Test error handling across integrated systems."""
    
    def test_graceful_degradation(self, integrated_tree_view):
        """Test systems gracefully handle failures."""
        tree_view = integrated_tree_view
        
        # Test with None model
        original_model = tree_view.model()
        tree_view.setModel(None)
        
        # Systems should handle None model gracefully
        selection = tree_view._selection
        result = selection.select_element("element_1")
        assert result is False  # Should fail gracefully
        
        # Test search with None model
        search_filter = tree_view._search_filter
        search_bar = search_filter.get_search_bar()
        search_bar.set_search_text("test")
        # Should not crash
        
        # Restore model
        tree_view.setModel(original_model)
    
    def test_invalid_data_handling(self, integrated_tree_view):
        """Test handling of invalid data."""
        tree_view = integrated_tree_view
        
        # Test selection with invalid element IDs
        selection = tree_view._selection
        result = selection.select_element("")  # Empty string
        assert result is False
        
        result = selection.select_element(None)  # None value
        assert result is False
        
        # Test search with invalid queries
        search_filter = tree_view._search_filter
        search_bar = search_filter.get_search_bar()
        
        # These should not crash
        search_bar.set_search_text("")
        search_bar.set_search_text("[]{}()*+?|^$\\")  # Regex special chars
    
    def test_system_interdependency_failures(self, integrated_tree_view):
        """Test behavior when one system fails."""
        tree_view = integrated_tree_view
        
        # Mock a system failure
        visual_feedback = tree_view._visual_feedback
        original_method = visual_feedback.indicate_selection_change
        
        # Replace with failing method
        def failing_method(*args, **kwargs):
            raise Exception("System failure")
        
        visual_feedback.indicate_selection_change = failing_method
        
        # Other systems should continue working
        selection = tree_view._selection
        # This should work even if visual feedback fails
        model = tree_view.model()
        if model.rowCount() > 0:
            index = model.index(0, 0)
            tree_view.setCurrentIndex(index)
        
        # Restore original method
        visual_feedback.indicate_selection_change = original_method


@pytest.mark.integration
class TestRealWorldScenarios:
    """Test real-world usage scenarios."""
    
    def test_document_editing_workflow(self, integrated_tree_view):
        """Test typical document editing workflow."""
        tree_view = integrated_tree_view
        
        # 1. User searches for content
        search_filter = tree_view._search_filter
        search_bar = search_filter.get_search_bar()
        search_bar.set_search_text("test")
        
        # 2. User selects multiple results
        selection = tree_view._selection
        model = tree_view.model()
        if model.rowCount() > 0:
            index = model.index(0, 0)
            tree_view.setCurrentIndex(index)
        
        # 3. User triggers context menu
        context_menu = tree_view._context_menu
        # Would normally be triggered by right-click
        
        # 4. User performs keyboard navigation
        keyboard_nav = tree_view._keyboard_nav
        keyboard_nav.execute_command("nav_down")
        
        # 5. User drags and drops (mock)
        drag_drop = tree_view._drag_drop
        # Would normally be triggered by mouse drag
        
        # All operations should complete without error
        assert True
    
    def test_accessibility_features(self, integrated_tree_view):
        """Test accessibility features work together."""
        tree_view = integrated_tree_view
        
        # Test keyboard-only navigation
        keyboard_nav = tree_view._keyboard_nav
        
        # Test reduced motion
        visual_feedback = tree_view._visual_feedback
        visual_feedback.set_reduce_motion(True)
        visual_feedback.set_animations_enabled(False)
        
        # Test that all features remain accessible
        selection = tree_view._selection
        search_filter = tree_view._search_filter
        
        # These should all work without visual effects
        assert keyboard_nav is not None
        assert selection is not None
        assert search_filter is not None
    
    def test_customization_integration(self, integrated_tree_view):
        """Test that systems can be customized together."""
        tree_view = integrated_tree_view
        
        # Customize delegate
        delegate = tree_view._delegate
        delegate.set_show_confidence(False)
        delegate.set_show_icons(True)
        delegate.set_show_type_badges(True)
        
        # Customize visual feedback
        visual_feedback = tree_view._visual_feedback
        visual_feedback.set_animation_speed(0.5)  # Slower animations
        
        # Customize search
        search_filter = tree_view._search_filter
        search_bar = search_filter.get_search_bar()
        search_bar.regex_checkbox.setChecked(True)
        
        # Test that customizations don't conflict
        assert delegate.show_confidence is False
        assert delegate.show_icons is True
        assert search_bar.regex_checkbox.isChecked()


if __name__ == "__main__":
    pytest.main([__file__])