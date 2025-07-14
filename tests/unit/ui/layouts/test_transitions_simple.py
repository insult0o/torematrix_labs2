"""Simple tests for layout transitions system."""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtCore import QRect, QSize, QPoint
from PyQt6.QtWidgets import QWidget, QApplication

from src.torematrix.ui.layouts.transitions import (
    TransitionType, TransitionDirection, TransitionState, TransitionConfiguration,
    ComponentState, TransitionMetrics, LayoutTransitionManager
)
from src.torematrix.core.events import EventBus
from src.torematrix.core.config import ConfigurationManager
from src.torematrix.core.state import Store


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestTransitionConfiguration:
    """Test TransitionConfiguration class."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = TransitionConfiguration()
        
        assert config.transition_type == TransitionType.FADE
        assert config.duration_ms == 300
        assert config.preserve_state is True
        assert config.enable_accessibility is True
        assert config.stagger_components is False
    
    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = TransitionConfiguration(
            transition_type=TransitionType.SLIDE,
            duration_ms=500,
            direction=TransitionDirection.LEFT,
            preserve_state=False,
            enable_accessibility=False
        )
        
        assert config.transition_type == TransitionType.SLIDE
        assert config.duration_ms == 500
        assert config.direction == TransitionDirection.LEFT
        assert config.preserve_state is False
        assert config.enable_accessibility is False


class TestComponentState:
    """Test ComponentState class."""
    
    def test_component_state_creation(self, qapp):
        """Test creating component state."""
        state = ComponentState(
            widget_id="test_widget",
            geometry=QRect(10, 20, 100, 200),
            visibility=True,
            opacity=0.8
        )
        
        assert state.widget_id == "test_widget"
        assert state.geometry == QRect(10, 20, 100, 200)
        assert state.visibility is True
        assert state.opacity == 0.8


class TestTransitionMetrics:
    """Test TransitionMetrics class."""
    
    def test_metrics_creation(self):
        """Test creating transition metrics."""
        from datetime import datetime
        
        start_time = datetime.now()
        metrics = TransitionMetrics(
            start_time=start_time,
            target_duration_ms=300.0
        )
        
        assert metrics.start_time == start_time
        assert metrics.target_duration_ms == 300.0
        assert metrics.end_time is None
        assert metrics.actual_duration_ms == 0.0


class TestLayoutTransitionManager:
    """Test LayoutTransitionManager class."""
    
    @pytest.fixture
    def event_bus(self):
        return Mock(spec=EventBus)
    
    @pytest.fixture
    def config_manager(self):
        mock_config = Mock(spec=ConfigurationManager)
        mock_config.get.return_value = True
        return mock_config
    
    @pytest.fixture
    def state_manager(self):
        return Mock(spec=Store)
    
    @pytest.fixture
    def transition_manager(self, event_bus, config_manager, state_manager):
        with patch.object(LayoutTransitionManager, 'get_config', return_value=True):
            return LayoutTransitionManager(event_bus, config_manager, state_manager)
    
    def test_initialization(self, transition_manager):
        """Test transition manager initialization."""
        assert transition_manager is not None
        assert transition_manager._current_state == TransitionState.IDLE
        assert transition_manager._default_config is not None
        assert transition_manager._accessibility_enabled is True
    
    def test_default_configuration(self, transition_manager):
        """Test default configuration management."""
        config = TransitionConfiguration(
            transition_type=TransitionType.SLIDE,
            duration_ms=500
        )
        
        transition_manager.set_default_configuration(config)
        
        retrieved_config = transition_manager.get_default_configuration()
        assert retrieved_config.transition_type == TransitionType.SLIDE
        assert retrieved_config.duration_ms == 500
    
    def test_current_state(self, transition_manager):
        """Test current state management."""
        assert transition_manager.get_current_state() == TransitionState.IDLE
        
        # Can't directly set state, but can check it returns properly
        assert isinstance(transition_manager.get_current_state(), TransitionState)


def test_transition_types():
    """Test transition type enumeration."""
    assert TransitionType.FADE is not None
    assert TransitionType.SLIDE is not None
    assert TransitionType.SCALE is not None
    assert TransitionType.FLIP is not None
    assert TransitionType.MORPH is not None
    assert TransitionType.INSTANT is not None


def test_transition_directions():
    """Test transition direction enumeration."""
    assert TransitionDirection.LEFT is not None
    assert TransitionDirection.RIGHT is not None
    assert TransitionDirection.UP is not None
    assert TransitionDirection.DOWN is not None
    assert TransitionDirection.IN is not None
    assert TransitionDirection.OUT is not None


def test_transition_states():
    """Test transition state enumeration."""
    assert TransitionState.IDLE is not None
    assert TransitionState.PREPARING is not None
    assert TransitionState.ANIMATING is not None
    assert TransitionState.COMPLETING is not None
    assert TransitionState.INTERRUPTED is not None
    assert TransitionState.FAILED is not None