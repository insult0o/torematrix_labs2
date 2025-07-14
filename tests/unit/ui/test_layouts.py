"""Tests for responsive layout system."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import QSize, QRect
from PyQt6.QtGui import QResizeEvent

from torematrix.ui.layouts import (
    ResponsiveLayout, ResponsiveWidget, ScreenSize, 
    ResponsiveRule, Breakpoint
)
from torematrix.core.events import EventBus
from torematrix.core.config import ConfigManager
from torematrix.core.state import StateManager


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_dependencies():
    """Create mock dependencies for ResponsiveLayout."""
    event_bus = Mock(spec=EventBus)
    config_manager = Mock(spec=ConfigManager)
    state_manager = Mock(spec=StateManager)
    
    return event_bus, config_manager, state_manager


@pytest.fixture
def container_widget(app):
    """Create container widget for testing."""
    container = QWidget()
    container.resize(1000, 600)
    return container


@pytest.fixture
def responsive_layout(app, mock_dependencies, container_widget):
    """Create ResponsiveLayout instance for testing."""
    event_bus, config_manager, state_manager = mock_dependencies
    
    layout = ResponsiveLayout(
        container_widget, event_bus, config_manager, state_manager
    )
    
    return layout


class TestBreakpoint:
    """Test Breakpoint data class."""
    
    def test_breakpoint_creation(self):
        """Test creating Breakpoint instance."""
        breakpoint = Breakpoint("md", 768, 991)
        
        assert breakpoint.name == "md"
        assert breakpoint.min_width == 768
        assert breakpoint.max_width == 991
        
        # Test without max_width
        breakpoint_open = Breakpoint("xl", 1200)
        assert breakpoint_open.max_width is None


class TestResponsiveRule:
    """Test ResponsiveRule data class."""
    
    def test_responsive_rule_creation(self):
        """Test creating ResponsiveRule instance."""
        rule = ResponsiveRule(
            screen_sizes=[ScreenSize.MEDIUM, ScreenSize.LARGE],
            visible=True,
            minimum_size=QSize(200, 100)
        )
        
        assert ScreenSize.MEDIUM in rule.screen_sizes
        assert ScreenSize.LARGE in rule.screen_sizes
        assert rule.visible is True
        assert rule.minimum_size == QSize(200, 100)


class TestResponsiveWidget:
    """Test ResponsiveWidget functionality."""
    
    def test_initialization(self, app):
        """Test ResponsiveWidget initialization."""
        widget = ResponsiveWidget()
        
        assert widget._current_screen_size == ScreenSize.MEDIUM
        assert len(widget._breakpoints) == 6  # All ScreenSize values
        assert ScreenSize.EXTRA_SMALL in widget._breakpoints
    
    def test_default_breakpoints(self, app):
        """Test default breakpoint configuration."""
        widget = ResponsiveWidget()
        breakpoints = widget._breakpoints
        
        assert breakpoints[ScreenSize.EXTRA_SMALL].min_width == 0
        assert breakpoints[ScreenSize.SMALL].min_width == 576
        assert breakpoints[ScreenSize.MEDIUM].min_width == 768
        assert breakpoints[ScreenSize.LARGE].min_width == 992
        assert breakpoints[ScreenSize.EXTRA_LARGE].min_width == 1200
        assert breakpoints[ScreenSize.EXTRA_EXTRA_LARGE].min_width == 1400
    
    def test_screen_size_determination(self, app):
        """Test screen size determination from width."""
        widget = ResponsiveWidget()
        
        assert widget._determine_screen_size(500) == ScreenSize.EXTRA_SMALL
        assert widget._determine_screen_size(600) == ScreenSize.SMALL
        assert widget._determine_screen_size(800) == ScreenSize.MEDIUM
        assert widget._determine_screen_size(1000) == ScreenSize.LARGE
        assert widget._determine_screen_size(1300) == ScreenSize.EXTRA_LARGE
        assert widget._determine_screen_size(1500) == ScreenSize.EXTRA_EXTRA_LARGE
    
    def test_responsive_rule_addition(self, app):
        """Test adding responsive rules."""
        widget = ResponsiveWidget()
        
        rule = ResponsiveRule(
            screen_sizes=[ScreenSize.SMALL],
            visible=False,
            minimum_size=QSize(100, 50)
        )
        
        widget.add_responsive_rule(ScreenSize.SMALL, rule)
        assert ScreenSize.SMALL in widget._responsive_rules
        assert widget._responsive_rules[ScreenSize.SMALL] == rule
    
    def test_resize_event_handling(self, app):
        """Test resize event handling."""
        widget = ResponsiveWidget()
        widget.resize(1000, 600)
        
        # Mock the responsive rule application
        with patch.object(widget, '_apply_responsive_rule') as mock_apply:
            # Simulate resize event
            resize_event = QResizeEvent(QSize(500, 400), QSize(1000, 600))
            widget.resizeEvent(resize_event)
            
            # Should trigger rule application for new screen size
            mock_apply.assert_called_with(ScreenSize.EXTRA_SMALL)
    
    def test_responsive_rule_application(self, app):
        """Test responsive rule application."""
        widget = ResponsiveWidget()
        
        # Create rule that hides widget on small screens
        rule = ResponsiveRule(
            screen_sizes=[ScreenSize.SMALL],
            visible=False,
            minimum_size=QSize(100, 50)
        )
        
        widget.add_responsive_rule(ScreenSize.SMALL, rule)
        widget._apply_responsive_rule(ScreenSize.SMALL)
        
        assert widget.isVisible() is False
        assert widget.minimumSize() == QSize(100, 50)


class TestResponsiveLayout:
    """Test ResponsiveLayout functionality."""
    
    def test_initialization(self, responsive_layout):
        """Test ResponsiveLayout initialization."""
        assert responsive_layout._container is not None
        assert responsive_layout._current_screen_size == ScreenSize.MEDIUM
        assert responsive_layout._adaptation_enabled is True
        assert responsive_layout._adaptation_delay == 100
    
    def test_screen_size_determination(self, responsive_layout):
        """Test screen size determination."""
        assert responsive_layout._determine_screen_size(500) == ScreenSize.EXTRA_SMALL
        assert responsive_layout._determine_screen_size(800) == ScreenSize.MEDIUM
        assert responsive_layout._determine_screen_size(1200) == ScreenSize.EXTRA_LARGE
    
    def test_custom_breakpoints(self, responsive_layout):
        """Test setting custom breakpoints."""
        custom_breakpoints = {
            ScreenSize.SMALL: Breakpoint("sm", 400, 699),
            ScreenSize.MEDIUM: Breakpoint("md", 700, 999),
            ScreenSize.LARGE: Breakpoint("lg", 1000, None)
        }
        
        responsive_layout.set_breakpoints(custom_breakpoints)
        assert responsive_layout._custom_breakpoints == custom_breakpoints
    
    def test_responsive_widget_addition(self, responsive_layout, app):
        """Test adding responsive widgets."""
        widget = QWidget()
        rules = {
            ScreenSize.SMALL: ResponsiveRule(
                screen_sizes=[ScreenSize.SMALL],
                visible=False
            ),
            ScreenSize.LARGE: ResponsiveRule(
                screen_sizes=[ScreenSize.LARGE],
                visible=True,
                minimum_size=QSize(200, 100)
            )
        }
        
        responsive_widget = responsive_layout.add_responsive_widget(widget, rules)
        
        assert isinstance(responsive_widget, ResponsiveWidget)
        assert responsive_widget in responsive_layout._responsive_widgets
        assert len(responsive_widget._responsive_rules) == 2
    
    def test_responsive_widget_removal(self, responsive_layout, app):
        """Test removing responsive widgets."""
        widget = QWidget()
        rules = {ScreenSize.MEDIUM: ResponsiveRule([ScreenSize.MEDIUM])}
        
        responsive_widget = responsive_layout.add_responsive_widget(widget, rules)
        assert responsive_widget in responsive_layout._responsive_widgets
        
        responsive_layout.remove_responsive_widget(responsive_widget)
        assert responsive_widget not in responsive_layout._responsive_widgets
    
    def test_layout_update(self, responsive_layout):
        """Test layout update for specific size."""
        with patch.object(responsive_layout, '_update_layout_for_width') as mock_update:
            responsive_layout.update_layout(QSize(800, 600))
            mock_update.assert_called_once_with(800)
    
    def test_adaptation_enabling(self, responsive_layout):
        """Test enabling/disabling adaptation."""
        assert responsive_layout.is_adaptation_enabled() is True
        
        responsive_layout.enable_adaptation(False)
        assert responsive_layout.is_adaptation_enabled() is False
        
        responsive_layout.enable_adaptation(True)
        assert responsive_layout.is_adaptation_enabled() is True
    
    def test_adaptation_delay(self, responsive_layout):
        """Test setting adaptation delay."""
        responsive_layout.set_adaptation_delay(200)
        assert responsive_layout._adaptation_delay == 200
        
        # Test minimum value
        responsive_layout.set_adaptation_delay(-100)
        assert responsive_layout._adaptation_delay == 0
    
    def test_mobile_optimization(self, responsive_layout):
        """Test mobile-specific optimizations."""
        with patch.object(responsive_layout, '_find_widgets_of_type') as mock_find:
            mock_splitter = Mock()
            mock_splitter.orientation.return_value = 1  # Horizontal
            mock_find.return_value = [mock_splitter]
            
            responsive_layout._optimize_for_mobile()
            
            # Should convert horizontal splitters to vertical
            mock_splitter.setOrientation.assert_called_with(2)  # Vertical
    
    def test_desktop_optimization(self, responsive_layout):
        """Test desktop-specific optimizations."""
        with patch.object(responsive_layout, '_find_widgets_of_type') as mock_find:
            mock_splitter = Mock()
            mock_splitter._original_orientation = 1  # Original horizontal
            mock_find.return_value = [mock_splitter]
            
            responsive_layout._optimize_for_desktop()
            
            # Should restore original orientation
            mock_splitter.setOrientation.assert_called_with(1)
    
    def test_touch_target_adjustment(self, responsive_layout):
        """Test touch target size adjustment."""
        with patch.object(responsive_layout, '_find_widgets_of_type') as mock_find:
            mock_button = Mock()
            mock_button.sizeHint.return_value = QSize(30, 20)  # Small button
            mock_find.return_value = [mock_button]
            
            responsive_layout._adjust_touch_targets()
            
            # Should increase size to minimum touch target (44px)
            mock_button.setMinimumSize.assert_called_with(QSize(44, 44))
    
    def test_widget_type_finding(self, responsive_layout, app):
        """Test finding widgets of specific type."""
        # Add some widgets to container
        widget1 = QWidget()
        widget2 = QWidget()
        layout = QVBoxLayout(responsive_layout._container)
        layout.addWidget(widget1)
        layout.addWidget(widget2)
        
        widgets = responsive_layout._find_widgets_of_type(QWidget)
        assert len(widgets) >= 2  # At least the two we added
    
    def test_responsive_splitter_creation(self, responsive_layout):
        """Test creating responsive splitters."""
        splitter = responsive_layout.create_responsive_splitter(
            orientation=1,  # Horizontal
            mobile_orientation=2  # Vertical for mobile
        )
        
        assert splitter.orientation() == 1
        assert hasattr(splitter, '_original_orientation')
        assert splitter._original_orientation == 1
        assert hasattr(splitter, '_mobile_orientation')
        assert splitter._mobile_orientation == 2
    
    def test_responsive_scroll_area_creation(self, responsive_layout):
        """Test creating responsive scroll areas."""
        scroll_area = responsive_layout.create_responsive_scroll_area()
        
        assert scroll_area.widgetResizable() is True
        assert scroll_area.horizontalScrollBarPolicy() == 1  # As needed
        assert scroll_area.verticalScrollBarPolicy() == 1    # As needed
    
    def test_signal_emissions(self, responsive_layout):
        """Test signal emissions."""
        signal_spy = Mock()
        responsive_layout.layout_changed.connect(signal_spy)
        
        # Trigger layout change
        responsive_layout._update_layout_for_width(500)  # Small screen
        
        signal_spy.assert_called_once_with(ScreenSize.EXTRA_SMALL)
    
    def test_event_publishing(self, responsive_layout):
        """Test event publishing through event bus."""
        # Trigger layout change
        responsive_layout._update_layout_for_width(1200)  # Extra large screen
        
        # Verify event was published
        responsive_layout._event_bus.publish.assert_called_with(
            "layout.size_changed",
            {
                "screen_size": ScreenSize.EXTRA_LARGE.value,
                "width": 1200
            }
        )
    
    def test_container_resize_handling(self, responsive_layout, app):
        """Test container resize event handling."""
        # Mock the adaptation timer
        with patch.object(responsive_layout._adaptation_timer, 'start') as mock_start:
            # Simulate resize event
            resize_event = QResizeEvent(QSize(800, 600), QSize(1000, 600))
            responsive_layout._handle_container_resize(resize_event)
            
            # Should start adaptation timer
            mock_start.assert_called_once_with(responsive_layout._adaptation_delay)
    
    def test_layout_adaptation_performance(self, responsive_layout):
        """Test layout adaptation with timer."""
        with patch.object(responsive_layout, '_update_layout_for_width') as mock_update:
            # Perform layout adaptation
            responsive_layout._perform_layout_adaptation()
            
            # Should update layout for container width
            mock_update.assert_called_once_with(responsive_layout._container.width())
    
    def test_responsive_widgets_management(self, responsive_layout, app):
        """Test responsive widgets management."""
        widget1 = QWidget()
        widget2 = QWidget()
        
        rules = {ScreenSize.MEDIUM: ResponsiveRule([ScreenSize.MEDIUM])}
        
        # Add widgets
        resp_widget1 = responsive_layout.add_responsive_widget(widget1, rules)
        resp_widget2 = responsive_layout.add_responsive_widget(widget2, rules)
        
        # Get all responsive widgets
        widgets = responsive_layout.get_responsive_widgets()
        assert resp_widget1 in widgets
        assert resp_widget2 in widgets
        assert len(widgets) == 2
        
        # Clear all widgets
        responsive_layout.clear_responsive_widgets()
        widgets = responsive_layout.get_responsive_widgets()
        assert len(widgets) == 0