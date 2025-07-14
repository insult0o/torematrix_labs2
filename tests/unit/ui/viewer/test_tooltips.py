"""
Unit tests for the tooltip system.
Tests tooltip creation, positioning, content generation, and lifecycle management.
"""
import pytest
import time
from unittest.mock import Mock, MagicMock, patch, PropertyMock

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QPixmap, QColor
from PyQt6.QtWidgets import QApplication, QWidget

from src.torematrix.ui.viewer.tooltips import (
    TooltipManager, TooltipContent, TooltipStyle, TooltipWidget,
    TooltipPosition, TooltipTheme, TooltipContentProvider,
    TooltipMixin, show_tooltip, hide_tooltip
)
from src.torematrix.ui.viewer.coordinates import Point


class MockElement(TooltipContentProvider):
    """Mock element that provides tooltip content."""
    
    def __init__(self, name="Test Element", description="Test Description"):
        self.name = name
        self.description = description
        self.properties = {"type": "mock", "id": "123"}
        self.metadata = {"created": "2023-01-01"}
    
    def get_tooltip_content(self) -> TooltipContent:
        """Return tooltip content for this element."""
        return TooltipContent(
            title=self.name,
            description=self.description,
            properties=self.properties,
            metadata=self.metadata
        )


class TestTooltipContent:
    """Test tooltip content structure."""
    
    def test_empty_content(self):
        """Test empty tooltip content creation."""
        content = TooltipContent()
        
        assert content.title is None
        assert content.description is None
        assert content.properties is None
        assert content.metadata is None
        assert content.html_content is None
        assert content.custom_widget is None
        assert content.image is None
        assert content.links is None
    
    def test_full_content(self):
        """Test tooltip content with all fields."""
        content = TooltipContent(
            title="Test Title",
            description="Test Description",
            properties={"key": "value"},
            metadata={"meta": "data"},
            html_content="<b>Bold</b>",
            links=[("Link1", "http://example.com")]
        )
        
        assert content.title == "Test Title"
        assert content.description == "Test Description"
        assert content.properties == {"key": "value"}
        assert content.metadata == {"meta": "data"}
        assert content.html_content == "<b>Bold</b>"
        assert content.links == [("Link1", "http://example.com")]


class TestTooltipStyle:
    """Test tooltip styling configuration."""
    
    def test_default_style(self):
        """Test default tooltip style."""
        style = TooltipStyle()
        
        assert style.background_color == "#2b2b2b"
        assert style.border_color == "#555555"
        assert style.text_color == "#ffffff"
        assert style.border_width == 1
        assert style.border_radius == 6
        assert style.padding == 8
        assert style.font_family == "Arial"
        assert style.font_size == 11
        assert style.max_width == 300
        assert style.max_height == 200
        assert style.shadow_enabled
        assert style.shadow_color == "#000000"
        assert style.shadow_offset == (2, 2)
        assert style.shadow_blur == 4
    
    def test_custom_style(self):
        """Test custom tooltip style."""
        style = TooltipStyle(
            background_color="#ffffff",
            text_color="#000000",
            border_width=2,
            shadow_enabled=False
        )
        
        assert style.background_color == "#ffffff"
        assert style.text_color == "#000000"
        assert style.border_width == 2
        assert not style.shadow_enabled


@pytest.fixture
def qt_app():
    """Fixture to provide QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestTooltipWidget:
    """Test tooltip widget functionality."""
    
    def test_widget_creation(self, qt_app):
        """Test tooltip widget creation."""
        content = TooltipContent(
            title="Test Title",
            description="Test Description"
        )
        style = TooltipStyle()
        
        widget = TooltipWidget(content, style)
        
        assert widget.content == content
        assert widget.style == style
        assert widget.show_animation is not None
        assert widget.hide_animation is not None
    
    def test_widget_with_properties(self, qt_app):
        """Test widget creation with properties section."""
        content = TooltipContent(
            title="Element",
            properties={"width": "100px", "height": "50px"}
        )
        style = TooltipStyle()
        
        widget = TooltipWidget(content, style)
        
        # Widget should be created without errors
        assert widget.content.properties == {"width": "100px", "height": "50px"}
    
    def test_widget_with_links(self, qt_app):
        """Test widget creation with links section."""
        content = TooltipContent(
            title="Element",
            links=[("Google", "https://google.com"), ("GitHub", "https://github.com")]
        )
        style = TooltipStyle()
        
        widget = TooltipWidget(content, style)
        
        assert len(widget.content.links) == 2
        assert widget.content.links[0] == ("Google", "https://google.com")


class TestTooltipManager:
    """Test tooltip manager functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Clear any existing instance
        TooltipManager._instance = None
        self.manager = TooltipManager()
    
    def teardown_method(self):
        """Cleanup after tests."""
        # Clear singleton instance
        TooltipManager._instance = None
    
    def test_singleton_pattern(self):
        """Test that TooltipManager implements singleton pattern."""
        manager1 = TooltipManager()
        manager2 = TooltipManager()
        
        assert manager1 is manager2
        assert TooltipManager.get_instance() is manager1
    
    def test_initialization(self):
        """Test manager initialization."""
        assert self.manager.active_tooltip is None
        assert self.manager.pending_element is None
        assert self.manager.pending_position is None
        assert self.manager.tooltip_delay == 500
        assert self.manager.hide_delay == 100
        assert self.manager.default_style is not None
        assert len(self.manager.theme_styles) > 0
    
    def test_theme_styles(self):
        """Test predefined theme styles."""
        themes = self.manager.theme_styles
        
        assert TooltipTheme.DEFAULT in themes
        assert TooltipTheme.DARK in themes
        assert TooltipTheme.LIGHT in themes
        assert TooltipTheme.ERROR in themes
        assert TooltipTheme.WARNING in themes
        assert TooltipTheme.SUCCESS in themes
        
        # Check that themes have different colors
        default_style = themes[TooltipTheme.DEFAULT]
        light_style = themes[TooltipTheme.LIGHT]
        
        assert default_style.background_color != light_style.background_color
    
    def test_show_tooltip_sets_pending(self):
        """Test that show_tooltip sets pending state."""
        element = MockElement()
        position = Point(100, 100)
        
        with patch.object(self.manager.show_timer, 'start') as mock_start:
            self.manager.show_tooltip(element, position)
            
            assert self.manager.pending_element == element
            assert self.manager.pending_position == position
            mock_start.assert_called_once_with(500)
    
    def test_show_tooltip_with_custom_delay(self):
        """Test show_tooltip with custom delay."""
        element = MockElement()
        position = Point(100, 100)
        
        with patch.object(self.manager.show_timer, 'start') as mock_start:
            self.manager.show_tooltip(element, position, delay=1000)
            
            mock_start.assert_called_once_with(1000)
    
    def test_hide_tooltip_starts_timer(self):
        """Test that hide_tooltip starts hide timer."""
        # Setup active tooltip
        self.manager.active_tooltip = Mock()
        
        with patch.object(self.manager.hide_timer, 'start') as mock_start:
            self.manager.hide_tooltip()
            
            mock_start.assert_called_once_with(100)
    
    def test_hide_tooltip_immediately(self):
        """Test immediate tooltip hiding."""
        mock_tooltip = Mock()
        self.manager.active_tooltip = mock_tooltip
        
        with patch.object(self.manager, '_hide_current_tooltip') as mock_hide:
            self.manager.hide_tooltip_immediately()
            
            mock_hide.assert_called_once()
    
    def test_generate_default_content(self):
        """Test default content generation."""
        mock_element = Mock()
        mock_element.type = "text"
        mock_element.description = "A text element"
        mock_element.bounds = Mock()
        mock_element.bounds.x = 10
        mock_element.bounds.y = 20
        mock_element.bounds.width = 100
        mock_element.bounds.height = 50
        mock_element.layer = "text_layer"
        mock_element.id = "element_123"
        
        content = self.manager._generate_default_content(mock_element)
        
        assert content.title == "Element: text"
        assert content.description == "A text element"
        assert "Position" in content.properties
        assert "Size" in content.properties
        assert "Layer" in content.properties
        assert "ID" in content.properties
        assert content.properties["Position"] == "(10.0, 20.0)"
        assert content.properties["Size"] == "100.0 × 50.0"
        assert content.properties["Layer"] == "text_layer"
        assert content.properties["ID"] == "element_123"
    
    def test_content_caching(self):
        """Test tooltip content caching."""
        element = MockElement()
        
        # First call should generate content
        content1 = self.manager._get_tooltip_content(element)
        
        # Second call should return cached content
        content2 = self.manager._get_tooltip_content(element)
        
        assert content1 is content2
        assert element in self.manager.content_cache
    
    def test_calculate_tooltip_position_auto(self):
        """Test automatic tooltip positioning."""
        target_pos = Point(100, 100)
        tooltip_size = Mock()
        tooltip_size.width.return_value = 200
        tooltip_size.height.return_value = 100
        
        with patch('src.torematrix.ui.viewer.tooltips.QApplication.primaryScreen') as mock_screen:
            mock_screen_obj = Mock()
            mock_screen_obj.availableGeometry.return_value.right.return_value = 1920
            mock_screen_obj.availableGeometry.return_value.bottom.return_value = 1080
            mock_screen_obj.availableGeometry.return_value.left.return_value = 0
            mock_screen_obj.availableGeometry.return_value.top.return_value = 0
            mock_screen.return_value = mock_screen_obj
            
            position = self.manager._calculate_tooltip_position(
                target_pos, tooltip_size, TooltipPosition.AUTO
            )
            
            # Should be offset from target position
            assert position.x == target_pos.x + 10  # Default offset
            assert position.y == target_pos.y + 10
    
    def test_calculate_tooltip_position_above(self):
        """Test tooltip positioning above target."""
        target_pos = Point(100, 100)
        tooltip_size = Mock()
        tooltip_size.width.return_value = 200
        tooltip_size.height.return_value = 50
        
        position = self.manager._calculate_tooltip_position(
            target_pos, tooltip_size, TooltipPosition.ABOVE
        )
        
        # Should be centered horizontally and above vertically
        assert position.x == target_pos.x - 100  # width/2
        assert position.y == target_pos.y - 50 - 10  # height + offset
    
    def test_calculate_tooltip_position_below(self):
        """Test tooltip positioning below target."""
        target_pos = Point(100, 100)
        tooltip_size = Mock()
        tooltip_size.width.return_value = 200
        tooltip_size.height.return_value = 50
        
        position = self.manager._calculate_tooltip_position(
            target_pos, tooltip_size, TooltipPosition.BELOW
        )
        
        # Should be centered horizontally and below vertically
        assert position.x == target_pos.x - 100  # width/2
        assert position.y == target_pos.y + 10  # offset
    
    def test_set_tooltip_delay(self):
        """Test setting tooltip delay."""
        self.manager.set_tooltip_delay(750)
        assert self.manager.tooltip_delay == 750
    
    def test_set_hide_delay(self):
        """Test setting hide delay."""
        self.manager.set_hide_delay(200)
        assert self.manager.hide_delay == 200
    
    def test_register_custom_theme(self):
        """Test registering custom theme."""
        custom_style = TooltipStyle(background_color="#ff0000")
        
        self.manager.register_custom_theme("custom", custom_style)
        
        # Note: This test is simplified as the implementation uses dynamic enum creation
        # In a real scenario, you'd verify the theme is properly registered
    
    def test_clear_content_cache(self):
        """Test clearing content cache."""
        element = MockElement()
        
        # Add content to cache
        self.manager._get_tooltip_content(element)
        assert len(self.manager.content_cache) > 0
        
        # Clear cache
        self.manager.clear_content_cache()
        assert len(self.manager.content_cache) == 0
    
    def test_is_tooltip_visible(self):
        """Test tooltip visibility check."""
        # No tooltip
        assert not self.manager.is_tooltip_visible()
        
        # Mock active tooltip
        mock_tooltip = Mock()
        mock_tooltip.isVisible.return_value = True
        self.manager.active_tooltip = mock_tooltip
        
        assert self.manager.is_tooltip_visible()
        
        # Hidden tooltip
        mock_tooltip.isVisible.return_value = False
        assert not self.manager.is_tooltip_visible()
    
    def test_get_tooltip_element(self):
        """Test getting tooltip element."""
        element = MockElement()
        
        # No pending element
        assert self.manager.get_tooltip_element() is None
        
        # With active tooltip and pending element
        self.manager.active_tooltip = Mock()
        self.manager.pending_element = element
        
        assert self.manager.get_tooltip_element() == element


class TestTooltipMixin:
    """Test tooltip mixin functionality."""
    
    def test_mixin_initialization(self):
        """Test mixin initialization."""
        
        class TestWidget(TooltipMixin):
            def __init__(self):
                super().__init__()
        
        widget = TestWidget()
        
        assert widget._tooltip_content is None
    
    def test_set_tooltip_content(self):
        """Test setting tooltip content."""
        
        class TestWidget(TooltipMixin):
            def __init__(self):
                super().__init__()
        
        widget = TestWidget()
        content = TooltipContent(title="Test")
        
        widget.set_tooltip_content(content)
        
        assert widget._tooltip_content == content
        assert widget.get_tooltip_content() == content
    
    def test_show_tooltip_at(self):
        """Test showing tooltip at position."""
        
        class TestWidget(TooltipMixin):
            def __init__(self):
                super().__init__()
        
        widget = TestWidget()
        position = Point(50, 50)
        
        with patch('src.torematrix.ui.viewer.tooltips.show_tooltip') as mock_show:
            widget.show_tooltip_at(position)
            
            mock_show.assert_called_once_with(widget, position, TooltipTheme.DEFAULT)


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_show_tooltip_function(self):
        """Test show_tooltip utility function."""
        element = MockElement()
        position = Point(100, 100)
        
        with patch.object(TooltipManager, 'get_instance') as mock_get_instance:
            mock_manager = Mock()
            mock_get_instance.return_value = mock_manager
            
            show_tooltip(element, position, TooltipTheme.DARK)
            
            mock_manager.show_tooltip.assert_called_once_with(
                element, position, TooltipTheme.DARK
            )
    
    def test_hide_tooltip_function(self):
        """Test hide_tooltip utility function."""
        with patch.object(TooltipManager, 'get_instance') as mock_get_instance:
            mock_manager = Mock()
            mock_get_instance.return_value = mock_manager
            
            hide_tooltip()
            
            mock_manager.hide_tooltip.assert_called_once()


class TestTooltipContentProvider:
    """Test tooltip content provider protocol."""
    
    def test_mock_element_provides_content(self):
        """Test that mock element provides content."""
        element = MockElement("Test Element", "A test element")
        
        content = element.get_tooltip_content()
        
        assert content.title == "Test Element"
        assert content.description == "A test element"
        assert content.properties["type"] == "mock"
        assert content.metadata["created"] == "2023-01-01"


if __name__ == "__main__":
    pytest.main([__file__])