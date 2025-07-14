"""Tests for layout animations system."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QSize, QPoint, QRect, QTimer
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QColor

from src.torematrix.ui.layouts.animations import (
    AnimationType, AnimationTiming, AnimationState, AnimationConfiguration,
    AnimationKeyframe, AnimationMetrics, CustomEasing, BaseAnimation,
    PropertyAnimation, KeyframeAnimation, StaggeredAnimation, AnimationManager
)
from src.torematrix.core.events import EventBus
from src.torematrix.core.config import ConfigurationManager
from src.torematrix.core.state import Store


class TestAnimationConfiguration:
    """Test AnimationConfiguration class."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = AnimationConfiguration()
        
        assert config.duration_ms == 300
        assert config.timing == AnimationTiming.EASE_OUT
        assert config.delay_ms == 0
        assert config.loop_count == 1
        assert config.auto_reverse is False
        assert config.target_fps == 60
        assert config.use_hardware_acceleration is True
        assert config.optimize_for_battery is False
        assert config.respect_reduced_motion is True
        assert config.provide_alternatives is True
    
    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = AnimationConfiguration(
            duration_ms=500,
            timing=AnimationTiming.BOUNCE,
            delay_ms=100,
            loop_count=3,
            auto_reverse=True,
            target_fps=30
        )
        
        assert config.duration_ms == 500
        assert config.timing == AnimationTiming.BOUNCE
        assert config.delay_ms == 100
        assert config.loop_count == 3
        assert config.auto_reverse is True
        assert config.target_fps == 30


class TestAnimationKeyframe:
    """Test AnimationKeyframe class."""
    
    def test_keyframe_creation(self):
        """Test creating animation keyframe."""
        keyframe = AnimationKeyframe(
            time_percent=0.5,
            value=100,
            easing=AnimationTiming.EASE_IN
        )
        
        assert keyframe.time_percent == 0.5
        assert keyframe.value == 100
        assert keyframe.easing == AnimationTiming.EASE_IN
    
    def test_keyframe_without_easing(self):
        """Test creating keyframe without easing."""
        keyframe = AnimationKeyframe(time_percent=0.3, value="test")
        
        assert keyframe.time_percent == 0.3
        assert keyframe.value == "test"
        assert keyframe.easing is None


class TestAnimationMetrics:
    """Test AnimationMetrics class."""
    
    def test_metrics_creation(self):
        """Test creating animation metrics."""
        metrics = AnimationMetrics(
            animation_id="test_anim",
            start_time=time.time(),
            target_duration_ms=300.0,
            frame_count=18,
            average_fps=60.0
        )
        
        assert metrics.animation_id == "test_anim"
        assert metrics.start_time > 0
        assert metrics.target_duration_ms == 300.0
        assert metrics.frame_count == 18
        assert metrics.average_fps == 60.0
        assert metrics.end_time is None
        assert metrics.actual_duration_ms == 0.0
        assert metrics.dropped_frames == 0
        assert metrics.cpu_usage_percent == 0.0
        assert metrics.memory_usage_mb == 0.0


class TestCustomEasing:
    """Test CustomEasing class."""
    
    def test_elastic_ease_out(self):
        """Test elastic ease out function."""
        # Test boundary values
        assert CustomEasing.elastic_ease_out(0.0) == 0.0
        assert CustomEasing.elastic_ease_out(1.0) == 1.0
        
        # Test middle value
        result = CustomEasing.elastic_ease_out(0.5)
        assert isinstance(result, float)
        assert result > 0.0
    
    def test_bounce_ease_out(self):
        """Test bounce ease out function."""
        # Test boundary values
        assert CustomEasing.bounce_ease_out(0.0) == 0.0
        
        # Test different segments
        result1 = CustomEasing.bounce_ease_out(0.2)
        result2 = CustomEasing.bounce_ease_out(0.6)
        result3 = CustomEasing.bounce_ease_out(0.8)
        result4 = CustomEasing.bounce_ease_out(0.95)
        
        assert all(isinstance(r, float) for r in [result1, result2, result3, result4])
        assert all(r >= 0.0 for r in [result1, result2, result3, result4])
    
    def test_back_ease_out(self):
        """Test back ease out function."""
        # Test with default overshoot
        result = CustomEasing.back_ease_out(0.5)
        assert isinstance(result, float)
        
        # Test with custom overshoot
        result_custom = CustomEasing.back_ease_out(0.5, overshoot=2.0)
        assert isinstance(result_custom, float)
        assert result_custom != result
    
    def test_spring_ease_out(self):
        """Test spring ease out function."""
        # Test with default parameters
        result = CustomEasing.spring_ease_out(0.5)
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0
        
        # Test with custom parameters
        result_custom = CustomEasing.spring_ease_out(0.5, tension=400, friction=20)
        assert isinstance(result_custom, float)
        assert 0.0 <= result_custom <= 1.0


class TestBaseAnimation:
    """Test BaseAnimation class."""
    
    class TestAnimation(BaseAnimation):
        """Test implementation of BaseAnimation."""
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.animation_steps = []
            self.prepared = False
            self.cleaned_up = False
        
        def _apply_animation_step(self, progress: float):
            self.animation_steps.append(progress)
        
        def _prepare_animation(self) -> bool:
            self.prepared = True
            return True
        
        def _cleanup_animation(self):
            self.cleaned_up = True
    
    @pytest.fixture
    def animation_config(self):
        """Create animation configuration."""
        return AnimationConfiguration(duration_ms=100, target_fps=10)
    
    @pytest.fixture
    def test_animation(self, animation_config):
        """Create test animation."""
        return self.TestAnimation("test_anim", animation_config)
    
    def test_animation_initialization(self, test_animation):
        """Test animation initialization."""
        assert test_animation.animation_id == "test_anim"
        assert test_animation.config.duration_ms == 100
        assert test_animation._state == AnimationState.IDLE
        assert test_animation._start_time is None
        assert test_animation._pause_time is None
        assert test_animation._accumulated_time == 0.0
        assert test_animation.animation_steps == []
        assert test_animation.prepared is False
        assert test_animation.cleaned_up is False
    
    def test_animation_start_success(self, test_animation):
        """Test successful animation start."""
        result = test_animation.start()
        
        assert result is True
        assert test_animation.prepared is True
        assert test_animation._state == AnimationState.PREPARING
    
    def test_animation_start_failure(self, test_animation):
        """Test failed animation start."""
        # Make preparation fail
        test_animation._prepare_animation = Mock(return_value=False)
        
        result = test_animation.start()
        
        assert result is False
        assert test_animation._state == AnimationState.FAILED
    
    def test_animation_start_already_running(self, test_animation):
        """Test starting animation that's already running."""
        test_animation._state = AnimationState.RUNNING
        
        result = test_animation.start()
        
        assert result is False
    
    def test_animation_pause_resume(self, test_animation):
        """Test pausing and resuming animation."""
        # Start animation
        test_animation.start()
        test_animation._start_animation()
        
        # Pause
        test_animation.pause()
        assert test_animation._state == AnimationState.PAUSED
        assert test_animation._pause_time is not None
        
        # Resume
        test_animation.resume()
        assert test_animation._state == AnimationState.RUNNING
        assert test_animation._pause_time is None
    
    def test_animation_stop(self, test_animation):
        """Test stopping animation."""
        # Start animation
        test_animation.start()
        test_animation._start_animation()
        
        # Stop
        test_animation.stop()
        assert test_animation._state == AnimationState.INTERRUPTED
        assert test_animation.cleaned_up is True
    
    def test_apply_easing_linear(self, test_animation):
        """Test linear easing."""
        test_animation.config.timing = AnimationTiming.LINEAR
        
        result = test_animation._apply_easing(0.5)
        assert result == 0.5
    
    def test_apply_easing_ease_in(self, test_animation):
        """Test ease in easing."""
        test_animation.config.timing = AnimationTiming.EASE_IN
        
        result = test_animation._apply_easing(0.5)
        assert result == 0.25  # 0.5^2
    
    def test_apply_easing_ease_out(self, test_animation):
        """Test ease out easing."""
        test_animation.config.timing = AnimationTiming.EASE_OUT
        
        result = test_animation._apply_easing(0.5)
        assert result == 0.75  # 1 - (1-0.5)^2
    
    def test_apply_easing_ease_in_out(self, test_animation):
        """Test ease in out easing."""
        test_animation.config.timing = AnimationTiming.EASE_IN_OUT
        
        result1 = test_animation._apply_easing(0.25)
        result2 = test_animation._apply_easing(0.75)
        
        assert result1 == 0.125  # 2 * 0.25^2
        assert result2 == 0.875  # 1 - 2 * (1-0.75)^2
    
    def test_apply_easing_custom(self, test_animation):
        """Test custom easing functions."""
        test_animation.config.timing = AnimationTiming.ELASTIC
        result = test_animation._apply_easing(0.5)
        assert isinstance(result, float)
        
        test_animation.config.timing = AnimationTiming.BOUNCE
        result = test_animation._apply_easing(0.5)
        assert isinstance(result, float)
        
        test_animation.config.timing = AnimationTiming.BACK
        result = test_animation._apply_easing(0.5)
        assert isinstance(result, float)
    
    def test_get_metrics(self, test_animation):
        """Test getting animation metrics."""
        metrics = test_animation.get_metrics()
        
        assert isinstance(metrics, AnimationMetrics)
        assert metrics.animation_id == "test_anim"
        assert metrics.target_duration_ms == 100.0
    
    def test_get_state(self, test_animation):
        """Test getting animation state."""
        assert test_animation.get_state() == AnimationState.IDLE
        
        test_animation._state = AnimationState.RUNNING
        assert test_animation.get_state() == AnimationState.RUNNING


class TestPropertyAnimation:
    """Test PropertyAnimation class."""
    
    @pytest.fixture
    def widget(self):
        """Create test widget."""
        widget = QWidget()
        widget.resize(100, 100)
        return widget
    
    @pytest.fixture
    def animation_config(self):
        """Create animation configuration."""
        return AnimationConfiguration(duration_ms=100)
    
    @pytest.fixture
    def property_animation(self, widget, animation_config):
        """Create property animation."""
        return PropertyAnimation(
            animation_id="prop_anim",
            widget=widget,
            property_name="size",
            start_value=QSize(100, 100),
            end_value=QSize(200, 200),
            config=animation_config
        )
    
    def test_property_animation_initialization(self, property_animation, widget):
        """Test property animation initialization."""
        assert property_animation.animation_id == "prop_anim"
        assert property_animation.widget_ref() == widget
        assert property_animation.property_name == "size"
        assert property_animation.start_value == QSize(100, 100)
        assert property_animation.end_value == QSize(200, 200)
    
    def test_property_animation_prepare(self, property_animation):
        """Test preparing property animation."""
        # Mock the property setter
        property_animation._property_setter = Mock()
        
        result = property_animation._prepare_animation()
        
        assert result is True
        property_animation._property_setter.assert_called_once_with(QSize(100, 100))
    
    def test_property_animation_prepare_failure(self, property_animation):
        """Test preparing property animation failure."""
        # Mock the property setter to raise exception
        property_animation._property_setter = Mock(side_effect=Exception("Test error"))
        
        result = property_animation._prepare_animation()
        
        assert result is False
    
    def test_property_animation_apply_step_numeric(self):
        """Test applying animation step with numeric values."""
        widget = QWidget()
        config = AnimationConfiguration()
        
        animation = PropertyAnimation(
            animation_id="test",
            widget=widget,
            property_name="x",
            start_value=0,
            end_value=100,
            config=config
        )
        
        # Mock the property setter
        animation._property_setter = Mock()
        
        # Test at 50% progress
        animation._apply_animation_step(0.5)
        
        # Should call setter with interpolated value
        animation._property_setter.assert_called_once_with(50)
    
    def test_property_animation_apply_step_qsize(self):
        """Test applying animation step with QSize values."""
        widget = QWidget()
        config = AnimationConfiguration()
        
        animation = PropertyAnimation(
            animation_id="test",
            widget=widget,
            property_name="size",
            start_value=QSize(100, 100),
            end_value=QSize(200, 300),
            config=config
        )
        
        # Mock the property setter
        animation._property_setter = Mock()
        
        # Test at 50% progress
        animation._apply_animation_step(0.5)
        
        # Should call setter with interpolated QSize
        expected_size = QSize(150, 200)
        animation._property_setter.assert_called_once_with(expected_size)
    
    def test_property_animation_apply_step_qpoint(self):
        """Test applying animation step with QPoint values."""
        widget = QWidget()
        config = AnimationConfiguration()
        
        animation = PropertyAnimation(
            animation_id="test",
            widget=widget,
            property_name="pos",
            start_value=QPoint(0, 0),
            end_value=QPoint(100, 200),
            config=config
        )
        
        # Mock the property setter
        animation._property_setter = Mock()
        
        # Test at 25% progress
        animation._apply_animation_step(0.25)
        
        # Should call setter with interpolated QPoint
        expected_point = QPoint(25, 50)
        animation._property_setter.assert_called_once_with(expected_point)
    
    def test_property_animation_apply_step_qcolor(self):
        """Test applying animation step with QColor values."""
        widget = QWidget()
        config = AnimationConfiguration()
        
        animation = PropertyAnimation(
            animation_id="test",
            widget=widget,
            property_name="color",
            start_value=QColor(0, 0, 0, 255),
            end_value=QColor(255, 255, 255, 255),
            config=config
        )
        
        # Mock the property setter
        animation._property_setter = Mock()
        
        # Test at 50% progress
        animation._apply_animation_step(0.5)
        
        # Should call setter with interpolated QColor
        expected_color = QColor(127, 127, 127, 255)
        animation._property_setter.assert_called_once_with(expected_color)
    
    def test_property_animation_apply_step_non_interpolable(self):
        """Test applying animation step with non-interpolable values."""
        widget = QWidget()
        config = AnimationConfiguration()
        
        animation = PropertyAnimation(
            animation_id="test",
            widget=widget,
            property_name="text",
            start_value="start",
            end_value="end",
            config=config
        )
        
        # Mock the property setter
        animation._property_setter = Mock()
        
        # Test at 25% progress (should use start value)
        animation._apply_animation_step(0.25)
        animation._property_setter.assert_called_once_with("start")
        
        # Reset mock
        animation._property_setter.reset_mock()
        
        # Test at 75% progress (should use end value)
        animation._apply_animation_step(0.75)
        animation._property_setter.assert_called_once_with("end")
    
    def test_property_animation_cleanup(self, property_animation):
        """Test cleaning up property animation."""
        # Mock the property setter
        property_animation._property_setter = Mock()
        
        property_animation._cleanup_animation()
        
        # Should set final value
        property_animation._property_setter.assert_called_once_with(QSize(200, 200))


class TestKeyframeAnimation:
    """Test KeyframeAnimation class."""
    
    @pytest.fixture
    def widget(self):
        """Create test widget."""
        return QWidget()
    
    @pytest.fixture
    def keyframes(self):
        """Create test keyframes."""
        return [
            AnimationKeyframe(0.0, 0, AnimationTiming.LINEAR),
            AnimationKeyframe(0.5, 50, AnimationTiming.EASE_IN),
            AnimationKeyframe(1.0, 100, AnimationTiming.EASE_OUT),
        ]
    
    @pytest.fixture
    def keyframe_animation(self, widget, keyframes):
        """Create keyframe animation."""
        config = AnimationConfiguration()
        return KeyframeAnimation(
            animation_id="keyframe_anim",
            widget=widget,
            property_name="x",
            keyframes=keyframes,
            config=config
        )
    
    def test_keyframe_animation_initialization(self, keyframe_animation, widget, keyframes):
        """Test keyframe animation initialization."""
        assert keyframe_animation.animation_id == "keyframe_anim"
        assert keyframe_animation.widget_ref() == widget
        assert keyframe_animation.property_name == "x"
        assert len(keyframe_animation.keyframes) == 3
        # Should be sorted by time
        assert keyframe_animation.keyframes[0].time_percent == 0.0
        assert keyframe_animation.keyframes[1].time_percent == 0.5
        assert keyframe_animation.keyframes[2].time_percent == 1.0
    
    def test_keyframe_animation_prepare(self, keyframe_animation):
        """Test preparing keyframe animation."""
        # Mock the property setter
        keyframe_animation._property_setter = Mock()
        
        result = keyframe_animation._prepare_animation()
        
        assert result is True
    
    def test_keyframe_animation_prepare_failure(self, keyframe_animation):
        """Test preparing keyframe animation failure."""
        # Remove widget reference
        keyframe_animation.widget_ref = Mock(return_value=None)
        
        result = keyframe_animation._prepare_animation()
        
        assert result is False
    
    def test_keyframe_animation_apply_step_between_keyframes(self, keyframe_animation):
        """Test applying animation step between keyframes."""
        # Mock the property setter
        keyframe_animation._property_setter = Mock()
        
        # Test at 25% progress (between first and second keyframe)
        keyframe_animation._apply_animation_step(0.25)
        
        # Should interpolate between 0 and 50
        keyframe_animation._property_setter.assert_called_once_with(25)
    
    def test_keyframe_animation_apply_step_at_keyframe(self, keyframe_animation):
        """Test applying animation step at exact keyframe."""
        # Mock the property setter
        keyframe_animation._property_setter = Mock()
        
        # Test at 50% progress (exact keyframe)
        keyframe_animation._apply_animation_step(0.5)
        
        # Should use keyframe value
        keyframe_animation._property_setter.assert_called_once_with(50)
    
    def test_keyframe_animation_apply_step_beyond_last_keyframe(self, keyframe_animation):
        """Test applying animation step beyond last keyframe."""
        # Mock the property setter
        keyframe_animation._property_setter = Mock()
        
        # Test at 100% progress (at last keyframe)
        keyframe_animation._apply_animation_step(1.0)
        
        # Should use last keyframe value
        keyframe_animation._property_setter.assert_called_once_with(100)
    
    def test_keyframe_animation_cleanup(self, keyframe_animation):
        """Test cleaning up keyframe animation."""
        # Mock the property setter
        keyframe_animation._property_setter = Mock()
        
        keyframe_animation._cleanup_animation()
        
        # Should set final keyframe value
        keyframe_animation._property_setter.assert_called_once_with(100)


class TestStaggeredAnimation:
    """Test StaggeredAnimation class."""
    
    @pytest.fixture
    def child_animations(self):
        """Create child animations."""
        animations = []
        for i in range(3):
            animation = Mock(spec=BaseAnimation)
            animation.animation_id = f"child_{i}"
            animation._prepare_animation.return_value = True
            animations.append(animation)
        return animations
    
    @pytest.fixture
    def staggered_animation(self, child_animations):
        """Create staggered animation."""
        config = AnimationConfiguration(duration_ms=300)
        return StaggeredAnimation(
            animation_id="staggered_anim",
            animations=child_animations,
            stagger_delay_ms=100,
            config=config
        )
    
    def test_staggered_animation_initialization(self, staggered_animation, child_animations):
        """Test staggered animation initialization."""
        assert staggered_animation.animation_id == "staggered_anim"
        assert len(staggered_animation.animations) == 3
        assert staggered_animation.stagger_delay_ms == 100
        assert len(staggered_animation._started_animations) == 3
        assert all(not started for started in staggered_animation._started_animations)
    
    def test_staggered_animation_prepare(self, staggered_animation):
        """Test preparing staggered animation."""
        result = staggered_animation._prepare_animation()
        
        assert result is True
        # Should call prepare on all child animations
        for animation in staggered_animation.animations:
            animation._prepare_animation.assert_called_once()
    
    def test_staggered_animation_prepare_failure(self, staggered_animation):
        """Test preparing staggered animation failure."""
        # Make one child animation fail
        staggered_animation.animations[1]._prepare_animation.return_value = False
        
        result = staggered_animation._prepare_animation()
        
        assert result is False
    
    def test_staggered_animation_apply_step_start_first(self, staggered_animation):
        """Test applying animation step to start first animation."""
        # Test at 50ms elapsed (should start first animation)
        staggered_animation._apply_animation_step(50 / 300)  # 50ms out of 300ms total
        
        # Should start first animation
        staggered_animation.animations[0].start.assert_called_once()
        assert staggered_animation._started_animations[0] is True
        
        # Others should not be started
        staggered_animation.animations[1].start.assert_not_called()
        staggered_animation.animations[2].start.assert_not_called()
    
    def test_staggered_animation_apply_step_start_multiple(self, staggered_animation):
        """Test applying animation step to start multiple animations."""
        # Test at 250ms elapsed (should start first three animations)
        staggered_animation._apply_animation_step(250 / 300)  # 250ms out of 300ms total
        
        # Should start first three animations
        staggered_animation.animations[0].start.assert_called_once()
        staggered_animation.animations[1].start.assert_called_once()
        staggered_animation.animations[2].start.assert_called_once()
        
        assert all(staggered_animation._started_animations)
    
    def test_staggered_animation_cleanup(self, staggered_animation):
        """Test cleaning up staggered animation."""
        # Mark some animations as not started
        staggered_animation._started_animations[1] = False
        staggered_animation._started_animations[2] = False
        
        staggered_animation._cleanup_animation()
        
        # Should start all animations during cleanup
        staggered_animation.animations[1].start.assert_called_once()
        staggered_animation.animations[2].start.assert_called_once()


class TestAnimationManager:
    """Test AnimationManager class."""
    
    @pytest.fixture
    def event_bus(self):
        """Create event bus mock."""
        return Mock(spec=EventBus)
    
    @pytest.fixture
    def config_manager(self):
        """Create config manager mock."""
        manager = Mock(spec=ConfigurationManager)
        manager.get_config.return_value = None
        return manager
    
    @pytest.fixture
    def state_manager(self):
        """Create state manager mock."""
        return Mock(spec=Store)
    
    @pytest.fixture
    def animation_manager(self, event_bus, config_manager, state_manager):
        """Create animation manager."""
        return AnimationManager(event_bus, config_manager, state_manager)
    
    def test_animation_manager_initialization(self, animation_manager):
        """Test animation manager initialization."""
        assert len(animation_manager._active_animations) == 0
        assert len(animation_manager._completed_animations) == 0
        assert animation_manager._max_history == 100
        assert animation_manager._max_concurrent_animations == 10
        assert animation_manager._performance_monitoring is True
    
    def test_animation_manager_setup(self, animation_manager):
        """Test animation manager setup."""
        animation_manager._setup_component()
        
        # Should subscribe to events
        animation_manager.event_bus.subscribe.assert_called()
        
        # Should load configuration
        animation_manager.config_manager.get_config.assert_called()
    
    def test_create_property_animation(self, animation_manager):
        """Test creating property animation."""
        widget = QWidget()
        
        animation = animation_manager.create_property_animation(
            animation_id="test_anim",
            widget=widget,
            property_name="size",
            start_value=QSize(100, 100),
            end_value=QSize(200, 200)
        )
        
        assert isinstance(animation, PropertyAnimation)
        assert animation.animation_id == "test_anim"
        assert animation.widget_ref() == widget
        assert animation.property_name == "size"
        assert animation.start_value == QSize(100, 100)
        assert animation.end_value == QSize(200, 200)
    
    def test_create_keyframe_animation(self, animation_manager):
        """Test creating keyframe animation."""
        widget = QWidget()
        keyframes = [
            AnimationKeyframe(0.0, 0),
            AnimationKeyframe(1.0, 100),
        ]
        
        animation = animation_manager.create_keyframe_animation(
            animation_id="keyframe_anim",
            widget=widget,
            property_name="x",
            keyframes=keyframes
        )
        
        assert isinstance(animation, KeyframeAnimation)
        assert animation.animation_id == "keyframe_anim"
        assert animation.widget_ref() == widget
        assert animation.property_name == "x"
        assert len(animation.keyframes) == 2
    
    def test_create_staggered_animation(self, animation_manager):
        """Test creating staggered animation."""
        child_animations = [Mock(spec=BaseAnimation) for _ in range(3)]
        
        animation = animation_manager.create_staggered_animation(
            animation_id="staggered_anim",
            animations=child_animations,
            stagger_delay_ms=100
        )
        
        assert isinstance(animation, StaggeredAnimation)
        assert animation.animation_id == "staggered_anim"
        assert len(animation.animations) == 3
        assert animation.stagger_delay_ms == 100
    
    def test_start_animation_success(self, animation_manager):
        """Test starting animation successfully."""
        # Create mock animation
        animation = Mock(spec=BaseAnimation)
        animation.animation_id = "test_anim"
        animation.start.return_value = True
        
        result = animation_manager.start_animation(animation)
        
        assert result is True
        assert "test_anim" in animation_manager._active_animations
        animation.start.assert_called_once()
    
    def test_start_animation_failure(self, animation_manager):
        """Test starting animation failure."""
        # Create mock animation that fails to start
        animation = Mock(spec=BaseAnimation)
        animation.animation_id = "test_anim"
        animation.start.return_value = False
        
        result = animation_manager.start_animation(animation)
        
        assert result is False
        assert "test_anim" not in animation_manager._active_animations
    
    def test_start_animation_concurrent_limit(self, animation_manager):
        """Test starting animation with concurrent limit."""
        # Fill up active animations
        for i in range(animation_manager._max_concurrent_animations):
            animation_manager._active_animations[f"anim_{i}"] = Mock()
        
        # Try to start another animation
        animation = Mock(spec=BaseAnimation)
        animation.animation_id = "test_anim"
        
        result = animation_manager.start_animation(animation)
        
        assert result is False
        assert "test_anim" not in animation_manager._active_animations
        animation.start.assert_not_called()
    
    def test_start_animation_duplicate_id(self, animation_manager):
        """Test starting animation with duplicate ID."""
        # Add existing animation
        animation_manager._active_animations["test_anim"] = Mock()
        
        # Try to start animation with same ID
        animation = Mock(spec=BaseAnimation)
        animation.animation_id = "test_anim"
        
        result = animation_manager.start_animation(animation)
        
        assert result is False
        animation.start.assert_not_called()
    
    def test_stop_animation(self, animation_manager):
        """Test stopping animation."""
        # Add active animation
        animation = Mock(spec=BaseAnimation)
        animation_manager._active_animations["test_anim"] = animation
        
        result = animation_manager.stop_animation("test_anim")
        
        assert result is True
        animation.stop.assert_called_once()
    
    def test_stop_animation_not_found(self, animation_manager):
        """Test stopping animation that doesn't exist."""
        result = animation_manager.stop_animation("nonexistent_anim")
        
        assert result is False
    
    def test_pause_animation(self, animation_manager):
        """Test pausing animation."""
        # Add active animation
        animation = Mock(spec=BaseAnimation)
        animation_manager._active_animations["test_anim"] = animation
        
        result = animation_manager.pause_animation("test_anim")
        
        assert result is True
        animation.pause.assert_called_once()
    
    def test_resume_animation(self, animation_manager):
        """Test resuming animation."""
        # Add active animation
        animation = Mock(spec=BaseAnimation)
        animation_manager._active_animations["test_anim"] = animation
        
        result = animation_manager.resume_animation("test_anim")
        
        assert result is True
        animation.resume.assert_called_once()
    
    def test_stop_all_animations(self, animation_manager):
        """Test stopping all animations."""
        # Add multiple active animations
        animations = [Mock(spec=BaseAnimation) for _ in range(3)]
        for i, animation in enumerate(animations):
            animation_manager._active_animations[f"anim_{i}"] = animation
        
        result = animation_manager.stop_all_animations()
        
        assert result == 3
        for animation in animations:
            animation.stop.assert_called_once()
    
    def test_get_active_animations(self, animation_manager):
        """Test getting active animation IDs."""
        # Add some active animations
        animation_manager._active_animations["anim1"] = Mock()
        animation_manager._active_animations["anim2"] = Mock()
        
        active_ids = animation_manager.get_active_animations()
        
        assert set(active_ids) == {"anim1", "anim2"}
    
    def test_get_animation_metrics(self, animation_manager):
        """Test getting animation metrics."""
        # Add some completed animations
        metrics = [Mock(spec=AnimationMetrics) for _ in range(3)]
        animation_manager._completed_animations = metrics
        
        result = animation_manager.get_animation_metrics()
        
        assert result == metrics
        assert result is not animation_manager._completed_animations  # Should be a copy
    
    def test_clear_animation_history(self, animation_manager):
        """Test clearing animation history."""
        # Add some completed animations
        animation_manager._completed_animations = [Mock() for _ in range(3)]
        
        animation_manager.clear_animation_history()
        
        assert len(animation_manager._completed_animations) == 0
    
    def test_set_default_configuration(self, animation_manager):
        """Test setting default configuration."""
        config = AnimationConfiguration(duration_ms=500)
        
        animation_manager.set_default_configuration(config)
        
        assert animation_manager._default_config == config
    
    def test_on_animation_finished(self, animation_manager):
        """Test handling animation completion."""
        # Create mock animation
        animation = Mock(spec=BaseAnimation)
        animation.animation_id = "test_anim"
        animation.get_metrics.return_value = Mock(spec=AnimationMetrics)
        
        # Add to active animations
        animation_manager._active_animations["test_anim"] = animation
        
        # Call completion handler
        animation_manager._on_animation_finished(animation)
        
        # Should remove from active animations
        assert "test_anim" not in animation_manager._active_animations
        
        # Should add to completed animations
        assert len(animation_manager._completed_animations) == 1
        
        # Should emit completion signal
        animation_manager.animation_completed.emit.assert_called_once()


def test_animation_types():
    """Test animation type enumeration."""
    assert AnimationType.PROPERTY is not None
    assert AnimationType.MORPHING is not None
    assert AnimationType.STAGGER is not None
    assert AnimationType.PHYSICS is not None
    assert AnimationType.PATH is not None
    assert AnimationType.PARTICLE is not None


def test_animation_timing():
    """Test animation timing enumeration."""
    assert AnimationTiming.LINEAR is not None
    assert AnimationTiming.EASE_IN is not None
    assert AnimationTiming.EASE_OUT is not None
    assert AnimationTiming.EASE_IN_OUT is not None
    assert AnimationTiming.ELASTIC is not None
    assert AnimationTiming.BOUNCE is not None
    assert AnimationTiming.BACK is not None
    assert AnimationTiming.CUSTOM is not None


def test_animation_states():
    """Test animation state enumeration."""
    assert AnimationState.IDLE is not None
    assert AnimationState.PREPARING is not None
    assert AnimationState.RUNNING is not None
    assert AnimationState.PAUSED is not None
    assert AnimationState.COMPLETED is not None
    assert AnimationState.INTERRUPTED is not None
    assert AnimationState.FAILED is not None