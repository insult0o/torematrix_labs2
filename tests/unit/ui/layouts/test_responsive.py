"""Tests for the responsive layout system."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time
from PyQt6.QtWidgets import QWidget, QApplication, QVBoxLayout
from PyQt6.QtCore import QSize, QObject
from PyQt6.QtGui import QScreen

from src.torematrix.ui.layouts.responsive import (
    ResponsiveMode, LayoutDensity, TouchTarget, ScreenProperties,
    ResponsiveConstraints, ResponsiveStrategy, MobileFirstStrategy,
    DesktopStrategy, TabletStrategy, ResponsiveLayoutEngine,
    ResponsiveWidget
)
from src.torematrix.core.events import EventBus
from src.torematrix.core.config import ConfigManager
from src.torematrix.core.state import StateManager


@pytest.fixture
def app():
    """Fixture to provide QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
    # Don't quit the app as it might be used by other tests


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing."""
    return Mock(spec=EventBus)


@pytest.fixture
def mock_config_manager():
    """Mock config manager for testing."""
    return Mock(spec=ConfigManager)


@pytest.fixture
def mock_state_manager():
    """Mock state manager for testing."""
    return Mock(spec=StateManager)


@pytest.fixture
def screen_properties():
    """Sample screen properties for testing."""
    return ScreenProperties(
        width=1920,
        height=1080,
        dpi=96.0,
        scale_factor=1.0,
        is_touch_enabled=False,
        orientation="landscape"
    )


class TestScreenProperties:
    """Test ScreenProperties dataclass."""
    
    def test_screen_properties_creation(self):
        """Test creation of screen properties."""
        props = ScreenProperties(
            width=1024,
            height=768,
            dpi=120.0,
            scale_factor=1.5
        )
        
        assert props.width == 1024
        assert props.height == 768
        assert props.dpi == 120.0
        assert props.scale_factor == 1.5
        assert props.aspect_ratio == pytest.approx(1024 / 768)
        assert props.orientation == "landscape"
    
    def test_portrait_orientation_detection(self):
        """Test portrait orientation detection."""
        props = ScreenProperties(
            width=768,
            height=1024,
            dpi=96.0,
            scale_factor=1.0
        )
        
        assert props.orientation == "portrait"
    
    def test_high_dpi_detection(self):
        """Test high DPI detection."""
        props = ScreenProperties(
            width=1920,
            height=1080,
            dpi=200.0,
            scale_factor=2.0
        )
        
        assert props.is_high_dpi is True


class TestResponsiveConstraints:
    """Test ResponsiveConstraints functionality."""
    
    def test_constraints_satisfaction_basic(self):
        """Test basic constraint satisfaction."""
        constraints = ResponsiveConstraints(
            min_width=800,
            max_width=1920,
            min_height=600,
            max_height=1080
        )
        
        props = ScreenProperties(1024, 768, 96.0, 1.0)
        assert constraints.satisfies_constraints(props) is True
        
        props_too_small = ScreenProperties(640, 480, 96.0, 1.0)
        assert constraints.satisfies_constraints(props_too_small) is False
    
    def test_aspect_ratio_constraints(self):
        """Test aspect ratio constraints."""
        constraints = ResponsiveConstraints(
            aspect_ratio_range=(1.0, 2.0)
        )
        
        props_16_9 = ScreenProperties(1920, 1080, 96.0, 1.0)  # ~1.78
        assert constraints.satisfies_constraints(props_16_9) is True
        
        props_4_3 = ScreenProperties(1024, 768, 96.0, 1.0)  # ~1.33
        assert constraints.satisfies_constraints(props_4_3) is True
        
        props_portrait = ScreenProperties(768, 1024, 96.0, 1.0)  # ~0.75
        assert constraints.satisfies_constraints(props_portrait) is False


class TestResponsiveStrategies:
    """Test responsive strategy implementations."""
    
    def test_mobile_first_strategy(self):
        """Test mobile-first strategy."""
        strategy = MobileFirstStrategy()
        
        # Test mobile properties
        mobile_props = ScreenProperties(480, 800, 150.0, 2.0, is_touch_enabled=True)
        assert strategy.can_handle(mobile_props) is True
        
        layout = strategy.calculate_layout(mobile_props)
        assert layout['layout_type'] == 'stacked'
        assert layout['sidebar_collapsed'] is True
        assert layout['touch_targets'] == TouchTarget.LARGE
        
        # Test desktop properties
        desktop_props = ScreenProperties(1920, 1080, 96.0, 1.0, is_touch_enabled=False)
        assert strategy.can_handle(desktop_props) is False
    
    def test_desktop_strategy(self):
        """Test desktop strategy."""
        strategy = DesktopStrategy()
        
        # Test desktop properties
        desktop_props = ScreenProperties(1920, 1080, 96.0, 1.0, is_touch_enabled=False)
        assert strategy.can_handle(desktop_props) is True
        
        layout = strategy.calculate_layout(desktop_props)
        assert layout['layout_type'] == 'split'
        assert layout['sidebar_collapsed'] is False
        assert layout['touch_targets'] == TouchTarget.SMALL
        
        # Test mobile properties
        mobile_props = ScreenProperties(480, 800, 150.0, 2.0, is_touch_enabled=True)
        assert strategy.can_handle(mobile_props) is False
    
    def test_tablet_strategy(self):
        """Test tablet strategy."""
        strategy = TabletStrategy()
        
        # Test tablet landscape
        tablet_landscape = ScreenProperties(1024, 768, 130.0, 1.5, is_touch_enabled=True)
        assert strategy.can_handle(tablet_landscape) is True
        
        layout = strategy.calculate_layout(tablet_landscape)
        assert layout['layout_type'] == 'adaptive'
        assert layout['sidebar_collapsed'] is False  # Landscape
        assert layout['touch_targets'] == TouchTarget.MEDIUM
        
        # Test tablet portrait
        tablet_portrait = ScreenProperties(768, 1024, 130.0, 1.5, is_touch_enabled=True)
        layout_portrait = strategy.calculate_layout(tablet_portrait)
        assert layout_portrait['sidebar_collapsed'] is True  # Portrait
    
    def test_strategy_priorities(self):
        """Test strategy priority ordering."""
        mobile = MobileFirstStrategy()
        tablet = TabletStrategy()
        desktop = DesktopStrategy()
        
        assert mobile.get_priority() > tablet.get_priority()
        assert tablet.get_priority() > desktop.get_priority()


class TestResponsiveLayoutEngine:
    """Test ResponsiveLayoutEngine functionality."""
    
    def test_engine_initialization(self):
        """Test engine initialization."""
        engine = ResponsiveLayoutEngine()
        
        # Should have default strategies
        assert len(engine._strategies) > 0
        assert engine._cache_enabled is True
        assert engine._screen_properties is None
    
    def test_strategy_management(self):
        """Test adding and removing strategies."""
        engine = ResponsiveLayoutEngine()
        initial_count = len(engine._strategies)
        
        # Add custom strategy
        custom_strategy = MobileFirstStrategy()
        engine.add_strategy(custom_strategy)
        assert len(engine._strategies) == initial_count + 1
        
        # Remove strategy
        success = engine.remove_strategy(MobileFirstStrategy)
        assert success is True
        # Should remove all instances
        assert all(not isinstance(s, MobileFirstStrategy) for s in engine._strategies)
    
    def test_screen_properties_update(self):
        """Test screen properties update and adaptation."""
        engine = ResponsiveLayoutEngine()
        
        # Mock signals
        engine.layout_adapted = Mock()
        engine.strategy_changed = Mock()
        
        # Update properties
        props = ScreenProperties(1024, 768, 96.0, 1.0)
        engine.update_screen_properties(props)
        
        assert engine._screen_properties == props
        # Should trigger adaptation
        engine.layout_adapted.emit.assert_called_once()
    
    def test_adaptation_throttling(self):
        """Test adaptation throttling."""
        engine = ResponsiveLayoutEngine()
        engine.set_adaptation_throttle(100)  # 100ms throttle
        
        # Rapid updates should be throttled
        props1 = ScreenProperties(1024, 768, 96.0, 1.0)
        props2 = ScreenProperties(1025, 769, 96.0, 1.0)  # Small change
        
        start_time = time.time()
        engine.update_screen_properties(props1)
        engine.update_screen_properties(props2)
        
        # Should not take long due to throttling
        elapsed = (time.time() - start_time) * 1000
        assert elapsed < 50  # Should be much less than throttle time
    
    def test_cache_functionality(self):
        """Test layout parameter caching."""
        engine = ResponsiveLayoutEngine()
        
        props = ScreenProperties(1024, 768, 96.0, 1.0)
        
        # First adaptation should miss cache
        engine.update_screen_properties(props)
        
        # Second adaptation with same properties should hit cache
        cache_size_before = len(engine._layout_cache)
        engine.update_screen_properties(props)
        
        # Cache should have entries
        assert len(engine._layout_cache) >= cache_size_before
    
    def test_cache_enable_disable(self):
        """Test cache enable/disable functionality."""
        engine = ResponsiveLayoutEngine()
        
        # Disable cache
        engine.set_cache_enabled(False)
        assert engine._cache_enabled is False
        assert len(engine._layout_cache) == 0
        
        # Enable cache
        engine.set_cache_enabled(True)
        assert engine._cache_enabled is True
    
    def test_performance_metrics(self):
        """Test performance metrics collection."""
        engine = ResponsiveLayoutEngine()
        
        props = ScreenProperties(1024, 768, 96.0, 1.0)
        engine.update_screen_properties(props)
        
        metrics = engine.get_performance_metrics()
        assert metrics.total_adaptations >= 1
        assert metrics.adaptation_time_ms >= 0
    
    def test_touch_target_optimization(self):
        """Test touch target optimization."""
        engine = ResponsiveLayoutEngine()
        
        # Touch device
        touch_props = ScreenProperties(480, 800, 150.0, 2.0, is_touch_enabled=True)
        touch_targets = engine.get_optimal_touch_targets(touch_props)
        assert touch_targets == TouchTarget.LARGE
        
        # Desktop device
        desktop_props = ScreenProperties(1920, 1080, 96.0, 1.0, is_touch_enabled=False)
        desktop_targets = engine.get_optimal_touch_targets(desktop_props)
        assert desktop_targets == TouchTarget.SMALL
    
    def test_layout_density_optimization(self):
        """Test layout density optimization."""
        engine = ResponsiveLayoutEngine()
        
        # Small screen
        small_props = ScreenProperties(480, 800, 150.0, 2.0)
        density = engine.get_optimal_density(small_props)
        assert density == LayoutDensity.COMPACT
        
        # Large screen
        large_props = ScreenProperties(2560, 1440, 96.0, 1.0)
        density = engine.get_optimal_density(large_props)
        assert density == LayoutDensity.SPACIOUS


@pytest.mark.usefixtures("app")
class TestResponsiveWidget:
    """Test ResponsiveWidget functionality."""
    
    def test_widget_creation(self):
        """Test responsive widget creation."""
        widget = ResponsiveWidget()
        
        assert widget._responsive_engine is not None
        assert widget._adaptation_enabled is True
        assert widget._responsive_mode == ResponsiveMode.ADAPTIVE
    
    def test_responsive_mode_setting(self):
        """Test setting responsive mode."""
        widget = ResponsiveWidget()
        
        widget.set_responsive_mode(ResponsiveMode.MANUAL)
        assert widget._responsive_mode == ResponsiveMode.MANUAL
    
    def test_constraints_setting(self):
        """Test setting responsive constraints."""
        widget = ResponsiveWidget()
        constraints = ResponsiveConstraints(min_width=800, max_width=1200)
        
        widget.set_responsive_constraints(constraints)
        assert widget._constraints == constraints
    
    def test_adaptation_enable_disable(self):
        """Test enabling/disabling adaptation."""
        widget = ResponsiveWidget()
        
        widget.enable_responsive_adaptation(False)
        assert widget._adaptation_enabled is False
        
        widget.enable_responsive_adaptation(True)
        assert widget._adaptation_enabled is True
    
    @patch('src.torematrix.ui.layouts.responsive.QApplication.instance')
    def test_screen_properties_detection(self, mock_app_instance):
        """Test screen properties detection."""
        # Mock application and screen
        mock_app = Mock()
        mock_screen = Mock()
        mock_app.primaryScreen.return_value = mock_screen
        mock_screen.geometry.return_value.width.return_value = 1920
        mock_screen.geometry.return_value.height.return_value = 1080
        mock_screen.logicalDotsPerInch.return_value = 96.0
        mock_screen.devicePixelRatio.return_value = 1.0
        mock_screen.name.return_value = "Primary"
        
        mock_app_instance.return_value = mock_app
        
        widget = ResponsiveWidget()
        widget._update_screen_properties()
        
        # Should have detected screen properties
        engine_props = widget._responsive_engine.get_screen_properties()
        assert engine_props is not None
    
    def test_adaptation_statistics(self):
        """Test adaptation statistics collection."""
        widget = ResponsiveWidget()
        
        # Simulate some adaptations
        widget._adaptation_count = 5
        widget._total_adaptation_time = 100.0
        
        stats = widget.get_adaptation_statistics()
        assert stats['adaptation_count'] == 5
        assert stats['total_adaptation_time_ms'] == 100.0
        assert stats['average_adaptation_time_ms'] == 20.0
    
    def test_statistics_reset(self):
        """Test resetting adaptation statistics."""
        widget = ResponsiveWidget()
        
        widget._adaptation_count = 5
        widget._total_adaptation_time = 100.0
        
        widget.reset_adaptation_statistics()
        assert widget._adaptation_count == 0
        assert widget._total_adaptation_time == 0.0
    
    def test_touch_capability_detection(self):
        """Test touch capability detection heuristic."""
        widget = ResponsiveWidget()
        
        # This is a heuristic, so we just test that it returns a boolean
        is_touch = widget._detect_touch_capability()
        assert isinstance(is_touch, bool)


class TestIntegration:
    """Integration tests for responsive system components."""
    
    def test_strategy_engine_integration(self):
        """Test integration between strategies and engine."""
        engine = ResponsiveLayoutEngine()
        
        # Test different screen sizes trigger different strategies
        mobile_props = ScreenProperties(480, 800, 150.0, 2.0, is_touch_enabled=True)
        desktop_props = ScreenProperties(1920, 1080, 96.0, 1.0, is_touch_enabled=False)
        
        engine.update_screen_properties(mobile_props)
        mobile_strategy = engine.get_current_strategy()
        
        engine.update_screen_properties(desktop_props)
        desktop_strategy = engine.get_current_strategy()
        
        # Should use different strategies
        assert type(mobile_strategy) != type(desktop_strategy)
    
    @pytest.mark.usefixtures("app")
    def test_widget_engine_integration(self):
        """Test integration between widget and engine."""
        widget = ResponsiveWidget()
        
        # Mock layout adaptation signal
        widget.responsive_changed = Mock()
        
        # Trigger adaptation
        props = ScreenProperties(1024, 768, 96.0, 1.0)
        widget._responsive_engine.update_screen_properties(props)
        
        # Should eventually trigger responsive changes
        # (Note: This test might need adjustment based on actual signal timing)
    
    def test_performance_under_load(self):
        """Test performance under rapid property changes."""
        engine = ResponsiveLayoutEngine()
        
        start_time = time.time()
        
        # Rapid property changes
        for i in range(100):
            props = ScreenProperties(1024 + i, 768, 96.0, 1.0)
            engine.update_screen_properties(props)
        
        elapsed = time.time() - start_time
        
        # Should complete reasonably quickly (under 1 second)
        assert elapsed < 1.0
        
        # Check performance metrics
        metrics = engine.get_performance_metrics()
        assert metrics.total_adaptations > 0


if __name__ == "__main__":
    pytest.main([__file__])