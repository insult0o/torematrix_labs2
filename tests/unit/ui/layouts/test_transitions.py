"""Tests for layout transitions system."""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QRect, QSize, QPoint
from PyQt6.QtWidgets import QWidget, QApplication

from src.torematrix.ui.layouts.transitions import (
    TransitionType, TransitionDirection, TransitionState, TransitionConfiguration,
    ComponentState, FadeTransition, SlideTransition, ScaleTransition,
    LayoutTransitionManager, LayoutTransition, AccessibleTransitionManager
)
from src.torematrix.core.events import EventBus
from src.torematrix.core.config import ConfigurationManager
from src.torematrix.core.state import Store


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
        assert config.stagger_delay_ms == 50
        assert config.use_pixmap_cache is True
        assert config.max_concurrent_animations == 10
        assert config.frame_rate_target == 60
    
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
    
    def test_component_state_creation(self):
        """Test creating component state."""
        widget = QWidget()
        widget.setObjectName("test_widget")
        widget.setGeometry(10, 20, 100, 200)
        
        state = ComponentState(
            widget_id="test_widget",
            geometry=QRect(10, 20, 100, 200),
            visibility=True,
            opacity=0.8,
            custom_properties={"test": "value"}
        )
        
        assert state.widget_id == "test_widget"
        assert state.geometry == QRect(10, 20, 100, 200)
        assert state.visibility is True
        assert state.opacity == 0.8
        assert state.custom_properties == {"test": "value"}
        assert state.timestamp is not None


class TestFadeTransition:
    """Test FadeTransition effect."""
    
    def test_fade_transition_creation(self):
        """Test creating fade transition."""
        transition = FadeTransition()
        
        assert transition.old_effect is None
        assert transition.new_effect is None
        assert transition.old_widget is None
        assert transition.new_widget is None
    
    def test_fade_transition_prepare(self):
        """Test preparing fade transition."""
        transition = FadeTransition()
        
        old_widget = QWidget()
        new_widget = QWidget()
        
        # Mock the graphics effects
        with patch('src.torematrix.ui.layouts.transitions.QGraphicsOpacityEffect') as mock_effect:
            mock_effect.return_value = Mock()
            
            transition.prepare(old_widget, new_widget)
            
            assert transition.old_widget == old_widget
            assert transition.new_widget == new_widget
            assert transition.old_effect is not None
            assert transition.new_effect is not None
    
    def test_fade_transition_cleanup(self):
        """Test cleaning up fade transition."""
        transition = FadeTransition()
        
        old_widget = QWidget()
        new_widget = QWidget()
        
        # Setup mock effects
        old_effect = Mock()
        new_effect = Mock()
        
        transition.old_widget = old_widget
        transition.new_widget = new_widget
        transition.old_effect = old_effect
        transition.new_effect = new_effect
        
        # Mock parent method
        old_effect.parent.return_value = old_widget
        new_effect.parent.return_value = new_widget
        
        transition.cleanup()
        
        assert transition.old_effect is None
        assert transition.new_effect is None
        assert transition.old_widget is None
        assert transition.new_widget is None


class TestSlideTransition:
    """Test SlideTransition effect."""
    
    def test_slide_transition_creation(self):
        """Test creating slide transition."""
        transition = SlideTransition()
        
        assert transition.old_widget is None
        assert transition.new_widget is None
        assert transition.container is None
        assert transition.original_geometry is None
    
    def test_slide_transition_prepare(self):
        """Test preparing slide transition."""
        transition = SlideTransition()
        
        # Create parent container
        container = QWidget()
        container.setGeometry(0, 0, 400, 300)
        
        # Create old and new widgets
        old_widget = QWidget(container)
        new_widget = QWidget(container)
        
        transition.prepare(old_widget, new_widget)
        
        assert transition.old_widget == old_widget
        assert transition.new_widget == new_widget
        assert transition.container == container
        assert transition.original_geometry == container.geometry()
    
    def test_slide_transition_cleanup(self):
        """Test cleaning up slide transition."""
        transition = SlideTransition()
        
        old_widget = QWidget()
        new_widget = QWidget()
        
        transition.old_widget = old_widget
        transition.new_widget = new_widget
        
        transition.cleanup()
        
        assert transition.old_widget is None
        assert transition.new_widget is None
        assert transition.container is None
        assert transition.original_geometry is None


class TestScaleTransition:
    """Test ScaleTransition effect."""
    
    def test_scale_transition_creation(self):
        """Test creating scale transition."""
        transition = ScaleTransition()
        
        assert transition.old_widget is None
        assert transition.new_widget is None
        assert transition.old_effect is None
        assert transition.new_effect is None
    
    def test_scale_transition_prepare(self):
        """Test preparing scale transition."""
        transition = ScaleTransition()
        
        old_widget = QWidget()
        new_widget = QWidget()
        
        with patch('src.torematrix.ui.layouts.transitions.QGraphicsOpacityEffect') as mock_effect:
            mock_effect.return_value = Mock()
            
            transition.prepare(old_widget, new_widget)
            
            assert transition.old_widget == old_widget
            assert transition.new_widget == new_widget
            assert transition.old_effect is not None
            assert transition.new_effect is not None
    
    def test_scale_transition_cleanup(self):
        """Test cleaning up scale transition."""
        transition = ScaleTransition()
        
        old_widget = QWidget()
        new_widget = QWidget()
        
        # Setup mock effects
        old_effect = Mock()
        new_effect = Mock()
        
        transition.old_widget = old_widget
        transition.new_widget = new_widget
        transition.old_effect = old_effect
        transition.new_effect = new_effect
        
        transition.cleanup()
        
        assert transition.old_effect is None
        assert transition.new_effect is None
        assert transition.old_widget is None
        assert transition.new_widget is None


class TestLayoutTransitionManager:
    """Test LayoutTransitionManager class."""
    
    @pytest.fixture
    def event_bus(self):
        """Create event bus mock."""
        return Mock(spec=EventBus)
    
    @pytest.fixture
    def config_manager(self):
        """Create config manager mock."""
        manager = Mock(spec=ConfigurationManager)
        manager.get_config.return_value = {}
        return manager
    
    @pytest.fixture
    def state_manager(self):
        """Create state manager mock."""
        return Mock(spec=Store)
    
    @pytest.fixture
    def transition_manager(self, event_bus, config_manager, state_manager):
        """Create transition manager instance."""
        return LayoutTransitionManager(event_bus, config_manager, state_manager)
    
    def test_transition_manager_initialization(self, transition_manager):
        """Test transition manager initialization."""
        assert transition_manager._current_state == TransitionState.IDLE
        assert transition_manager._active_animation is None
        assert len(transition_manager._transition_effects) == 3
        assert TransitionType.FADE in transition_manager._transition_effects
        assert TransitionType.SLIDE in transition_manager._transition_effects
        assert TransitionType.SCALE in transition_manager._transition_effects
    
    def test_transition_manager_setup(self, transition_manager):
        """Test transition manager setup."""
        transition_manager._setup_component()
        
        # Check that event subscriptions were made
        transition_manager.event_bus.subscribe.assert_called()
        
        # Check that accessibility was setup
        assert transition_manager._accessibility_enabled is not None
    
    @pytest.mark.asyncio
    async def test_instant_transition(self, transition_manager):
        """Test instant transition without animation."""
        from_widget = QWidget()
        to_widget = QWidget()
        
        from_widget.show()
        to_widget.hide()
        
        result = await transition_manager._instant_transition(
            from_widget, to_widget, "from_layout", "to_layout",
            Mock()
        )
        
        assert result is True
        assert not from_widget.isVisible()
        assert to_widget.isVisible()
        assert transition_manager._current_state == TransitionState.IDLE
    
    @pytest.mark.asyncio
    async def test_preserve_component_states(self, transition_manager):
        """Test preserving component states."""
        widget = QWidget()
        child1 = QWidget(widget)
        child2 = QWidget(widget)
        
        child1.setObjectName("child1")
        child2.setObjectName("child2")
        
        child1.setGeometry(10, 10, 100, 100)
        child2.setGeometry(20, 20, 200, 200)
        
        await transition_manager._preserve_component_states(widget, "test_layout")
        
        assert "test_layout" in transition_manager._preserved_states
        states = transition_manager._preserved_states["test_layout"]
        assert len(states) >= 2  # At least the two children
    
    def test_find_stateful_widgets(self, transition_manager):
        """Test finding stateful widgets."""
        widget = QWidget()
        
        # Create different types of widgets
        from PyQt6.QtWidgets import QScrollArea, QTextEdit, QLineEdit
        
        scroll_area = QScrollArea(widget)
        text_edit = QTextEdit(widget)
        line_edit = QLineEdit(widget)
        regular_widget = QWidget(widget)
        
        stateful_widgets = transition_manager._find_stateful_widgets(widget)
        
        # Should find the stateful widgets
        assert scroll_area in stateful_widgets
        assert text_edit in stateful_widgets
        assert line_edit in stateful_widgets
        # Regular widget should not be in the list (unless it has preserve_state method)
    
    def test_restore_component_states(self, transition_manager):
        """Test restoring component states."""
        widget = QWidget()
        child = QWidget(widget)
        child.setObjectName("test_child")
        
        # Create a state to restore
        state = ComponentState(
            widget_id="test_child",
            geometry=QRect(50, 50, 150, 150),
            visibility=True
        )
        transition_manager._preserved_states["test_layout"] = [state]
        
        # Restore states
        result = transition_manager.restore_component_states(widget, "test_layout")
        
        assert result is True
        assert child.geometry() == QRect(50, 50, 150, 150)
    
    def test_interrupt_transition(self, transition_manager):
        """Test interrupting a transition."""
        # Set up a transition in progress
        transition_manager._current_state = TransitionState.ANIMATING
        mock_animation = Mock()
        transition_manager._active_animation = mock_animation
        
        result = transition_manager.interrupt_transition()
        
        assert result is True
        assert transition_manager._current_state == TransitionState.INTERRUPTED
        mock_animation.stop.assert_called_once()
        assert transition_manager._active_animation is None
    
    def test_clear_preserved_states(self, transition_manager):
        """Test clearing preserved states."""
        # Add some states
        transition_manager._preserved_states["layout1"] = [Mock()]
        transition_manager._preserved_states["layout2"] = [Mock()]
        
        # Clear specific layout
        transition_manager.clear_preserved_states("layout1")
        assert "layout1" not in transition_manager._preserved_states
        assert "layout2" in transition_manager._preserved_states
        
        # Clear all
        transition_manager.clear_preserved_states()
        assert len(transition_manager._preserved_states) == 0
    
    def test_set_default_configuration(self, transition_manager):
        """Test setting default configuration."""
        config = TransitionConfiguration(
            transition_type=TransitionType.SLIDE,
            duration_ms=500
        )
        
        transition_manager.set_default_configuration(config)
        
        assert transition_manager._default_config == config
    
    def test_get_current_state(self, transition_manager):
        """Test getting current state."""
        assert transition_manager.get_current_state() == TransitionState.IDLE
        
        transition_manager._current_state = TransitionState.ANIMATING
        assert transition_manager.get_current_state() == TransitionState.ANIMATING
    
    def test_get_transition_metrics(self, transition_manager):
        """Test getting transition metrics."""
        # Add some mock metrics
        mock_metrics = Mock()
        transition_manager._transition_metrics = [mock_metrics]
        
        metrics = transition_manager.get_transition_metrics()
        
        assert metrics == [mock_metrics]
        assert metrics is not transition_manager._transition_metrics  # Should be a copy


class TestAccessibleTransitionManager:
    """Test AccessibleTransitionManager class."""
    
    @pytest.fixture
    def accessible_manager(self):
        """Create accessible transition manager."""
        event_bus = Mock(spec=EventBus)
        config_manager = Mock(spec=ConfigurationManager)
        state_manager = Mock(spec=Store)
        
        config_manager.get_config.return_value = {}
        
        return AccessibleTransitionManager(event_bus, config_manager, state_manager)
    
    def test_accessible_manager_initialization(self, accessible_manager):
        """Test accessible manager initialization."""
        assert accessible_manager.announce_transitions is True
        assert accessible_manager.focus_management is True
    
    @pytest.mark.asyncio
    async def test_accessible_transition_with_announcements(self, accessible_manager):
        """Test transition with accessibility announcements."""
        from_widget = QWidget()
        to_widget = QWidget()
        
        from_widget.show()
        to_widget.hide()
        
        # Mock the announcement and focus management methods
        accessible_manager._announce_transition_start = Mock()
        accessible_manager._manage_focus_during_transition = Mock()
        
        # Mock the parent transition method
        with patch.object(LayoutTransitionManager, 'transition_layout') as mock_transition:
            mock_transition.return_value = "test_transition_id"
            
            result = await accessible_manager.transition_layout(
                from_widget, to_widget, "from_layout", "to_layout"
            )
            
            # Should announce transition
            accessible_manager._announce_transition_start.assert_called_once()
            
            # Should manage focus
            accessible_manager._manage_focus_during_transition.assert_called_once()
            
            # Should call parent method
            mock_transition.assert_called_once()


class TestLayoutTransition:
    """Test LayoutTransition class."""
    
    @pytest.fixture
    def transition_manager(self):
        """Create mock transition manager."""
        manager = Mock()
        manager.get_transition_effect.return_value = Mock()
        return manager
    
    @pytest.fixture
    def layout_transition(self, transition_manager):
        """Create layout transition instance."""
        config = TransitionConfiguration()
        
        return LayoutTransition(
            transition_id="test_transition",
            from_layout=Mock(),
            to_layout=Mock(),
            config=config,
            manager=transition_manager
        )
    
    def test_layout_transition_initialization(self, layout_transition):
        """Test layout transition initialization."""
        assert layout_transition.transition_id == "test_transition"
        assert layout_transition.state == TransitionState.IDLE
        assert layout_transition.progress == 0.0
        assert layout_transition.start_time == 0
        assert layout_transition.from_state == {}
        assert layout_transition.to_state == {}
    
    @pytest.mark.asyncio
    async def test_layout_transition_start(self, layout_transition):
        """Test starting layout transition."""
        # Mock the effect
        mock_effect = Mock()
        mock_effect.prepare = Mock()
        layout_transition.effect = mock_effect
        
        # Mock prepare states
        layout_transition._prepare_states = Mock()
        
        await layout_transition.start()
        
        assert layout_transition.state == TransitionState.ANIMATING
        assert layout_transition.start_time > 0
        mock_effect.prepare.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_layout_transition_cancel(self, layout_transition):
        """Test canceling layout transition."""
        # Set up transition as running
        layout_transition.state = TransitionState.ANIMATING
        layout_transition.animation_timer = Mock()
        
        await layout_transition.cancel()
        
        assert layout_transition.state == TransitionState.CANCELLED
        layout_transition.animation_timer.stop.assert_called_once()
    
    def test_apply_easing(self, layout_transition):
        """Test applying easing curve."""
        # Test linear easing (default should be linear for this test)
        progress = 0.5
        eased_progress = layout_transition._apply_easing(progress)
        
        # Should return the same value for linear easing
        assert eased_progress == progress
    
    def test_complete_transition(self, layout_transition):
        """Test completing transition."""
        # Set up animation timer
        layout_transition.animation_timer = Mock()
        layout_transition.effect = Mock()
        
        # Set up manager in active transitions
        layout_transition.manager.active_transitions = {
            layout_transition.transition_id: layout_transition
        }
        layout_transition.manager.transition_completed = Mock()
        
        layout_transition._complete_transition()
        
        assert layout_transition.state == TransitionState.IDLE
        layout_transition.animation_timer.stop.assert_called_once()
        layout_transition.manager.transition_completed.emit.assert_called_once()


def test_transition_types():
    """Test transition type enumeration."""
    assert TransitionType.SLIDE is not None
    assert TransitionType.FADE is not None
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