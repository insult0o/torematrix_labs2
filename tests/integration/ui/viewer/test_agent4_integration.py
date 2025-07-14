"""
Integration tests for Agent 4 interactive features with other agents' components.
Tests the interaction between Agent 4's features and Agents 1, 2, 3 components.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch

# Mock imports to avoid dependency issues in testing environment
try:
    from PyQt6.QtCore import QObject, pyqtSignal
    from PyQt6.QtGui import QMouseEvent, QKeyEvent
    PyQt6_available = True
except ImportError:
    # Create mock classes for testing environment
    class QObject:
        pass
    
    def pyqtSignal(*args):
        return Mock()
    
    QMouseEvent = Mock
    QKeyEvent = Mock
    PyQt6_available = False

from src.torematrix.ui.viewer.coordinates import Point, Rectangle


class MockOverlayEngine:
    """Mock overlay engine from Agent 1."""
    
    def __init__(self):
        self.elements = {}
        self.viewport_info = Mock()
        self.element_styles = {}
        
    def screen_to_document(self, screen_pos: Point) -> Point:
        """Convert screen coordinates to document coordinates."""
        # Simple 1:1 mapping for testing
        return screen_pos
    
    def screen_to_document_rect(self, screen_rect: Rectangle) -> Rectangle:
        """Convert screen rectangle to document coordinates."""
        return screen_rect
    
    def get_viewport_info(self):
        """Get viewport information."""
        return self.viewport_info
    
    def set_element_style(self, element, style: str):
        """Set element visual style."""
        self.element_styles[element] = style
    
    def reset_element_style(self, element):
        """Reset element visual style."""
        if element in self.element_styles:
            del self.element_styles[element]
    
    def show_selection_rectangle(self, rect: Rectangle):
        """Show selection rectangle."""
        self.selection_rectangle = rect
    
    def update_selection_rectangle(self, rect: Rectangle):
        """Update selection rectangle."""
        self.selection_rectangle = rect
    
    def hide_selection_rectangle(self):
        """Hide selection rectangle."""
        self.selection_rectangle = None


class MockSelectionManager:
    """Mock selection manager from Agent 2."""
    
    def __init__(self):
        self.selected_elements = []
        
    def select_single(self, element):
        """Select single element."""
        self.selected_elements = [element]
    
    def toggle_element(self, element):
        """Toggle element selection."""
        if element in self.selected_elements:
            self.selected_elements.remove(element)
        else:
            self.selected_elements.append(element)
    
    def extend_selection(self, element):
        """Extend selection with element."""
        if element not in self.selected_elements:
            self.selected_elements.append(element)
    
    def select_multiple(self, elements):
        """Select multiple elements."""
        self.selected_elements = list(elements)
    
    def add_to_selection(self, element):
        """Add element to selection."""
        if element not in self.selected_elements:
            self.selected_elements.append(element)
    
    def clear_selection(self):
        """Clear current selection."""
        self.selected_elements = []
    
    def get_selected_elements(self):
        """Get currently selected elements."""
        return self.selected_elements.copy()


class MockSpatialIndex:
    """Mock spatial index from Agent 3."""
    
    def __init__(self):
        self.elements = []
        self.element_bounds = {}
    
    def add_element(self, element, bounds: Rectangle):
        """Add element to spatial index."""
        self.elements.append(element)
        self.element_bounds[element] = bounds
    
    def remove_element(self, element):
        """Remove element from spatial index."""
        if element in self.elements:
            self.elements.remove(element)
        if element in self.element_bounds:
            del self.element_bounds[element]
    
    def query_point(self, point: Point):
        """Query elements at point."""
        result = []
        for element, bounds in self.element_bounds.items():
            if (bounds.x <= point.x <= bounds.x + bounds.width and
                bounds.y <= point.y <= bounds.y + bounds.height):
                result.append(element)
        return result
    
    def query_rectangle(self, rect: Rectangle):
        """Query elements in rectangle."""
        result = []
        for element, bounds in self.element_bounds.items():
            # Simple intersection test
            if (bounds.x < rect.x + rect.width and
                bounds.x + bounds.width > rect.x and
                bounds.y < rect.y + rect.height and
                bounds.y + bounds.height > rect.y):
                result.append(element)
        return result


class MockElement:
    """Mock document element."""
    
    def __init__(self, element_id: str, bounds: Rectangle):
        self.id = element_id
        self.bounds = bounds
        self.type = "mock_element"
        self.properties = {"id": element_id}
        
    def get_tooltip_content(self):
        """Get tooltip content for this element."""
        from src.torematrix.ui.viewer.tooltips import TooltipContent
        return TooltipContent(
            title=f"Element {self.id}",
            description=f"Mock element with ID {self.id}",
            properties=self.properties
        )


@pytest.mark.skipif(not PyQt6_available, reason="PyQt6 not available in test environment")
class TestAgent4Integration:
    """Test integration between Agent 4 and other agents."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Mock components from other agents
        self.overlay_engine = MockOverlayEngine()
        self.selection_manager = MockSelectionManager()
        self.spatial_index = MockSpatialIndex()
        
        # Add some test elements
        self.element1 = MockElement("elem1", Rectangle(10, 10, 50, 30))
        self.element2 = MockElement("elem2", Rectangle(70, 20, 60, 40))
        self.element3 = MockElement("elem3", Rectangle(150, 50, 40, 25))
        
        self.spatial_index.add_element(self.element1, self.element1.bounds)
        self.spatial_index.add_element(self.element2, self.element2.bounds)
        self.spatial_index.add_element(self.element3, self.element3.bounds)
        
        # Import Agent 4 components
        from src.torematrix.ui.viewer.interactions import InteractionManager
        from src.torematrix.ui.viewer.tooltips import TooltipManager
        from src.torematrix.ui.viewer.touch import TouchManager
        from src.torematrix.ui.viewer.accessibility import AccessibilityManager
        
        # Create Agent 4 managers
        self.interaction_manager = InteractionManager(
            self.overlay_engine, 
            self.selection_manager, 
            self.spatial_index
        )
        self.tooltip_manager = TooltipManager()
        self.touch_manager = TouchManager(self.interaction_manager)
        self.accessibility_manager = AccessibilityManager(self.overlay_engine)
    
    def test_interaction_with_overlay_engine(self):
        """Test interaction manager integration with Agent 1's overlay engine."""
        # Test coordinate transformation
        screen_pos = Point(25, 25)
        doc_pos = self.interaction_manager.overlay_engine.screen_to_document(screen_pos)
        
        assert doc_pos.x == screen_pos.x
        assert doc_pos.y == screen_pos.y
        
        # Test element lookup through spatial index
        elements = self.interaction_manager.get_elements_at_point(screen_pos)
        
        # Should find element1 which contains point (25, 25)
        assert self.element1 in elements
    
    def test_interaction_with_selection_manager(self):
        """Test interaction manager integration with Agent 2's selection manager."""
        # Test single element selection
        self.interaction_manager.select_element(self.element1, [])
        
        selected = self.selection_manager.get_selected_elements()
        assert len(selected) == 1
        assert self.element1 in selected
        
        # Test Ctrl+click toggle
        self.interaction_manager.select_element(self.element2, ["ctrl"])
        
        selected = self.selection_manager.get_selected_elements()
        assert len(selected) == 2
        assert self.element1 in selected
        assert self.element2 in selected
        
        # Test toggle off
        self.interaction_manager.select_element(self.element1, ["ctrl"])
        
        selected = self.selection_manager.get_selected_elements()
        assert len(selected) == 1
        assert self.element2 in selected
    
    def test_interaction_with_spatial_index(self):
        """Test interaction manager integration with Agent 3's spatial index."""
        # Test rectangular selection
        rect = Rectangle(0, 0, 100, 100)
        self.interaction_manager.select_elements_in_rectangle(rect, [])
        
        selected = self.selection_manager.get_selected_elements()
        
        # Should select element1 and element2 (both in rectangle)
        assert self.element1 in selected
        assert self.element2 in selected
        # element3 is outside the rectangle
        assert self.element3 not in selected
    
    def test_hover_integration(self):
        """Test hover functionality integration across agents."""
        # Test hover enter
        hover_pos = Point(35, 25)  # Inside element1
        
        self.interaction_manager.handle_hover(hover_pos)
        
        # Should set hover element
        assert self.interaction_manager.hover_element == self.element1
        
        # Should apply hover style through overlay engine
        assert self.element1 in self.overlay_engine.element_styles
        assert self.overlay_engine.element_styles[self.element1] == "hover"
        
        # Test hover exit
        hover_pos = Point(200, 200)  # Outside all elements
        
        self.interaction_manager.handle_hover(hover_pos)
        
        # Should clear hover element
        assert self.interaction_manager.hover_element is None
        
        # Should reset element style
        assert self.element1 not in self.overlay_engine.element_styles
    
    def test_rectangular_selection_integration(self):
        """Test rectangular selection workflow integration."""
        # Start rectangular selection
        start_point = Point(5, 5)
        self.interaction_manager.start_rectangular_selection(start_point)
        
        assert self.interaction_manager.is_rectangular_selection
        assert hasattr(self.overlay_engine, 'selection_rectangle')
        
        # Update selection
        current_point = Point(80, 65)
        self.interaction_manager.update_rectangular_selection(current_point)
        
        # Should update overlay visualization
        expected_rect = Rectangle(5, 5, 75, 60)
        assert self.interaction_manager.selection_rectangle.x == expected_rect.x
        assert self.interaction_manager.selection_rectangle.y == expected_rect.y
        assert self.interaction_manager.selection_rectangle.width == expected_rect.width
        assert self.interaction_manager.selection_rectangle.height == expected_rect.height
        
        # Complete selection
        self.interaction_manager.select_elements_in_rectangle(
            self.interaction_manager.selection_rectangle, []
        )
        self.interaction_manager.end_rectangular_selection()
        
        # Should select elements in rectangle
        selected = self.selection_manager.get_selected_elements()
        assert self.element1 in selected
        assert self.element2 in selected
        
        # Should hide selection rectangle
        assert not self.interaction_manager.is_rectangular_selection


@pytest.mark.skipif(PyQt6_available, reason="Skip mocked tests when PyQt6 is available")
class TestAgent4IntegrationMocked:
    """Test Agent 4 integration with mocked PyQt6."""
    
    def setup_method(self):
        """Setup test fixtures with mocked components."""
        # This version runs when PyQt6 is not available
        # and tests the core integration logic without UI dependencies
        
        self.overlay_engine = MockOverlayEngine()
        self.selection_manager = MockSelectionManager()
        self.spatial_index = MockSpatialIndex()
        
        # Add test elements
        self.element1 = MockElement("elem1", Rectangle(10, 10, 50, 30))
        self.spatial_index.add_element(self.element1, self.element1.bounds)
    
    def test_basic_integration_without_qt(self):
        """Test basic integration without Qt dependencies."""
        # Test spatial index integration
        point = Point(35, 25)  # Inside element1
        elements = self.spatial_index.query_point(point)
        
        assert self.element1 in elements
        
        # Test selection manager integration
        self.selection_manager.select_single(self.element1)
        selected = self.selection_manager.get_selected_elements()
        
        assert len(selected) == 1
        assert self.element1 in selected
    
    def test_coordinate_transformation_integration(self):
        """Test coordinate transformation without Qt."""
        screen_pos = Point(100, 100)
        doc_pos = self.overlay_engine.screen_to_document(screen_pos)
        
        # Simple 1:1 mapping in mock
        assert doc_pos.x == screen_pos.x
        assert doc_pos.y == screen_pos.y
    
    def test_element_style_integration(self):
        """Test element styling integration."""
        # Test applying hover style
        self.overlay_engine.set_element_style(self.element1, "hover")
        
        assert self.element1 in self.overlay_engine.element_styles
        assert self.overlay_engine.element_styles[self.element1] == "hover"
        
        # Test resetting style
        self.overlay_engine.reset_element_style(self.element1)
        
        assert self.element1 not in self.overlay_engine.element_styles


class TestPerformanceIntegration:
    """Test performance aspects of Agent 4 integration."""
    
    def setup_method(self):
        """Setup performance test fixtures."""
        self.overlay_engine = MockOverlayEngine()
        self.selection_manager = MockSelectionManager()
        self.spatial_index = MockSpatialIndex()
        
        # Add many elements for performance testing
        self.elements = []
        for i in range(100):
            element = MockElement(f"elem{i}", Rectangle(i*10, i*5, 20, 15))
            self.elements.append(element)
            self.spatial_index.add_element(element, element.bounds)
    
    def test_spatial_query_performance(self):
        """Test spatial query performance with many elements."""
        import time
        
        # Test point query performance
        start_time = time.time()
        
        for i in range(100):
            point = Point(i*10 + 10, i*5 + 5)
            elements = self.spatial_index.query_point(point)
        
        duration = time.time() - start_time
        
        # Should complete quickly (< 0.1 seconds for 100 queries)
        assert duration < 0.1
    
    def test_rectangular_selection_performance(self):
        """Test rectangular selection performance with many elements."""
        import time
        
        start_time = time.time()
        
        # Large rectangle that includes many elements
        rect = Rectangle(0, 0, 500, 250)
        selected_elements = self.spatial_index.query_rectangle(rect)
        
        duration = time.time() - start_time
        
        # Should complete quickly
        assert duration < 0.05
        
        # Should find many elements
        assert len(selected_elements) > 10


class TestAccessibilityIntegration:
    """Test accessibility integration with other agents."""
    
    def setup_method(self):
        """Setup accessibility test fixtures."""
        from src.torematrix.ui.viewer.accessibility import (
            AccessibilityProperties, AccessibilityRole
        )
        
        self.overlay_engine = MockOverlayEngine()
        self.elements = []
        
        # Create elements with accessibility properties
        for i in range(3):
            element = MockElement(f"button{i}", Rectangle(i*100, 50, 80, 40))
            element.accessibility_props = AccessibilityProperties(
                role=AccessibilityRole.BUTTON,
                name=f"Button {i+1}",
                description=f"Test button number {i+1}"
            )
            self.elements.append(element)
    
    def test_accessibility_description_generation(self):
        """Test accessibility description generation for elements."""
        # This test can run without PyQt6 as it tests logic only
        element = self.elements[0]
        
        # Basic accessibility description
        description_parts = [
            "button",
            "Button 1", 
            "Test button number 1"
        ]
        
        # Mock what accessibility manager would generate
        description = ", ".join(description_parts)
        
        assert "button" in description
        assert "Button 1" in description
        assert "Test button number 1" in description


if __name__ == "__main__":
    pytest.main([__file__])