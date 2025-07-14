"""Animation Framework for TORE Matrix Labs V3 Layout System.

This module provides a comprehensive animation system for layout components with
performance optimization, accessibility support, and advanced easing functions.
"""

from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from enum import Enum, auto
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
import math
import time
import weakref
from collections import deque

from PyQt6.QtWidgets import QWidget, QGraphicsEffect, QGraphicsOpacityEffect
from PyQt6.QtCore import (
    QObject, QTimer, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QSequentialAnimationGroup, QAbstractAnimation, pyqtSignal, QRect, QSize, QPoint,
    QVariantAnimation, QPropertyAnimation
)
from PyQt6.QtGui import QColor, QPainter, QPixmap

from ...core.events import EventBus
from ...core.config import ConfigurationManager
from ...core.state import Store
from ..base import BaseUIComponent

logger = logging.getLogger(__name__)


class AnimationType(Enum):
    """Types of animations available."""
    PROPERTY = auto()       # Property-based animation (opacity, size, position)
    MORPHING = auto()       # Smooth morphing between states
    STAGGER = auto()        # Staggered animation of multiple components
    PHYSICS = auto()        # Physics-based animation (spring, bounce)
    PATH = auto()           # Path-based movement animation
    PARTICLE = auto()       # Particle effect animation


class AnimationTiming(Enum):
    """Animation timing functions."""
    LINEAR = auto()
    EASE_IN = auto()
    EASE_OUT = auto() 
    EASE_IN_OUT = auto()
    ELASTIC = auto()
    BOUNCE = auto()
    BACK = auto()
    CUSTOM = auto()


class AnimationState(Enum):
    """Current state of an animation."""
    IDLE = auto()
    PREPARING = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    INTERRUPTED = auto()
    FAILED = auto()


@dataclass
class AnimationConfiguration:
    """Configuration for animations."""
    duration_ms: int = 300
    timing: AnimationTiming = AnimationTiming.EASE_OUT
    delay_ms: int = 0
    loop_count: int = 1
    auto_reverse: bool = False
    
    # Performance settings
    target_fps: int = 60
    use_hardware_acceleration: bool = True
    optimize_for_battery: bool = False
    
    # Accessibility
    respect_reduced_motion: bool = True
    provide_alternatives: bool = True


@dataclass
class AnimationKeyframe:
    """A keyframe in an animation sequence."""
    time_percent: float  # 0.0 to 1.0
    value: Any
    easing: Optional[AnimationTiming] = None


@dataclass 
class AnimationMetrics:
    """Performance metrics for animations."""
    animation_id: str
    start_time: float
    end_time: Optional[float] = None
    target_duration_ms: float = 0.0
    actual_duration_ms: float = 0.0
    frame_count: int = 0
    dropped_frames: int = 0
    average_fps: float = 0.0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0


class CustomEasing:
    """Custom easing function implementations."""
    
    @staticmethod
    def elastic_ease_out(progress: float, amplitude: float = 1.0, period: float = 0.3) -> float:
        """Elastic ease out with customizable amplitude and period."""
        if progress == 0.0 or progress == 1.0:
            return progress
        
        return (amplitude * (2 ** (-10 * progress)) * 
                math.sin((progress - period / 4) * (2 * math.pi) / period) + 1)
    
    @staticmethod
    def bounce_ease_out(progress: float) -> float:
        """Bounce ease out function."""
        if progress < 1 / 2.75:
            return 7.5625 * progress * progress
        elif progress < 2 / 2.75:
            progress -= 1.5 / 2.75
            return 7.5625 * progress * progress + 0.75
        elif progress < 2.5 / 2.75:
            progress -= 2.25 / 2.75
            return 7.5625 * progress * progress + 0.9375
        else:
            progress -= 2.625 / 2.75
            return 7.5625 * progress * progress + 0.984375
    
    @staticmethod
    def back_ease_out(progress: float, overshoot: float = 1.70158) -> float:
        """Back ease out with customizable overshoot."""
        progress -= 1
        return progress * progress * ((overshoot + 1) * progress + overshoot) + 1
    
    @staticmethod
    def spring_ease_out(progress: float, tension: float = 300, friction: float = 10) -> float:
        """Spring-based easing function."""
        # Simplified spring physics
        w = math.sqrt(tension)
        c = 2 * math.sqrt(tension * friction)
        
        if c < 2:  # Under-damped
            wd = w * math.sqrt(1 - (c / 2) ** 2)
            A = 1
            B = (c / 2) / wd
            return 1 - (A * math.cos(wd * progress) + B * math.sin(wd * progress)) * math.exp(-c / 2 * progress)
        else:  # Over-damped or critically damped
            r = -c / 2
            return 1 - (1 + r * progress) * math.exp(r * progress)


class BaseAnimation(QObject):
    """Base class for all animations."""
    
    # Signals
    started = pyqtSignal()
    finished = pyqtSignal()
    progress_changed = pyqtSignal(float)  # 0.0 to 1.0
    frame_rendered = pyqtSignal(int)  # frame number
    
    def __init__(
        self,
        animation_id: str,
        config: AnimationConfiguration,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        
        self.animation_id = animation_id
        self.config = config
        self._state = AnimationState.IDLE
        self._start_time: Optional[float] = None
        self._pause_time: Optional[float] = None
        self._accumulated_time: float = 0.0
        
        # Animation control
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_animation)
        
        # Performance metrics
        self._metrics = AnimationMetrics(
            animation_id=animation_id,
            start_time=0.0,
            target_duration_ms=config.duration_ms
        )
        self._frame_times: deque = deque(maxlen=60)  # Last 60 frame times
        
        # Calculate timer interval for target FPS
        self._timer_interval = max(1, 1000 // config.target_fps)
    
    @abstractmethod
    def _apply_animation_step(self, progress: float) -> None:
        """Apply animation at given progress (0.0 to 1.0)."""
        pass
    
    @abstractmethod
    def _prepare_animation(self) -> bool:
        """Prepare animation. Return True if ready to start."""
        pass
    
    @abstractmethod
    def _cleanup_animation(self) -> None:
        """Clean up after animation completion."""
        pass
    
    def start(self) -> bool:
        """Start the animation."""
        if self._state != AnimationState.IDLE:
            logger.warning(f"Animation {self.animation_id} already running")
            return False
        
        if not self._prepare_animation():
            logger.error(f"Failed to prepare animation {self.animation_id}")
            self._state = AnimationState.FAILED
            return False
        
        self._state = AnimationState.PREPARING
        
        # Apply delay
        if self.config.delay_ms > 0:
            QTimer.singleShot(self.config.delay_ms, self._start_animation)
        else:
            self._start_animation()
        
        return True
    
    def _start_animation(self) -> None:
        """Internal animation start."""
        self._state = AnimationState.RUNNING
        self._start_time = time.time()
        self._metrics.start_time = self._start_time
        self._accumulated_time = 0.0
        
        self._timer.start(self._timer_interval)
        self.started.emit()
        
        logger.debug(f"Animation {self.animation_id} started")
    
    def pause(self) -> None:
        """Pause the animation."""
        if self._state == AnimationState.RUNNING:
            self._state = AnimationState.PAUSED
            self._pause_time = time.time()
            self._timer.stop()
    
    def resume(self) -> None:
        """Resume the animation."""
        if self._state == AnimationState.PAUSED and self._pause_time:
            pause_duration = time.time() - self._pause_time
            self._start_time += pause_duration  # Adjust start time
            self._pause_time = None
            self._state = AnimationState.RUNNING
            self._timer.start(self._timer_interval)
    
    def stop(self) -> None:
        """Stop the animation."""
        if self._state in (AnimationState.RUNNING, AnimationState.PAUSED):
            self._state = AnimationState.INTERRUPTED
            self._timer.stop()
            self._finish_animation()
    
    def _update_animation(self) -> None:
        """Update animation frame."""
        if self._state != AnimationState.RUNNING or not self._start_time:
            return
        
        current_time = time.time()
        elapsed_ms = (current_time - self._start_time) * 1000
        
        # Calculate progress
        progress = min(1.0, elapsed_ms / self.config.duration_ms)
        
        # Apply easing
        eased_progress = self._apply_easing(progress)
        
        # Update metrics
        self._update_metrics(current_time)
        
        # Apply animation step
        try:
            self._apply_animation_step(eased_progress)
            self.progress_changed.emit(progress)
            self.frame_rendered.emit(self._metrics.frame_count)
            
        except Exception as e:
            logger.error(f"Animation {self.animation_id} failed: {e}")
            self._state = AnimationState.FAILED
            self._timer.stop()
            return
        
        # Check if animation is complete
        if progress >= 1.0:
            self._state = AnimationState.COMPLETED
            self._timer.stop()
            self._finish_animation()
    
    def _apply_easing(self, progress: float) -> float:
        """Apply easing function to progress."""
        timing = self.config.timing
        
        if timing == AnimationTiming.LINEAR:
            return progress
        elif timing == AnimationTiming.EASE_IN:
            return progress * progress
        elif timing == AnimationTiming.EASE_OUT:
            return 1 - (1 - progress) ** 2
        elif timing == AnimationTiming.EASE_IN_OUT:
            if progress < 0.5:
                return 2 * progress * progress
            else:
                return 1 - 2 * (1 - progress) ** 2
        elif timing == AnimationTiming.ELASTIC:
            return CustomEasing.elastic_ease_out(progress)
        elif timing == AnimationTiming.BOUNCE:
            return CustomEasing.bounce_ease_out(progress)
        elif timing == AnimationTiming.BACK:
            return CustomEasing.back_ease_out(progress)
        else:
            return progress
    
    def _update_metrics(self, current_time: float) -> None:
        """Update performance metrics."""
        self._metrics.frame_count += 1
        self._frame_times.append(current_time)
        
        # Calculate FPS
        if len(self._frame_times) > 1:
            time_diff = self._frame_times[-1] - self._frame_times[0]
            self._metrics.average_fps = (len(self._frame_times) - 1) / time_diff
        
        # Detect dropped frames
        if len(self._frame_times) >= 2:
            frame_time = self._frame_times[-1] - self._frame_times[-2]
            expected_frame_time = 1.0 / self.config.target_fps
            if frame_time > expected_frame_time * 1.5:  # 50% tolerance
                self._metrics.dropped_frames += 1
    
    def _finish_animation(self) -> None:
        """Finish animation and cleanup."""
        if self._start_time:
            self._metrics.end_time = time.time()
            self._metrics.actual_duration_ms = (self._metrics.end_time - self._start_time) * 1000
        
        self._cleanup_animation()
        self.finished.emit()
        
        logger.debug(f"Animation {self.animation_id} finished "
                    f"({self._metrics.actual_duration_ms:.1f}ms, "
                    f"{self._metrics.average_fps:.1f}fps)")
    
    def get_metrics(self) -> AnimationMetrics:
        """Get animation performance metrics."""
        return self._metrics
    
    def get_state(self) -> AnimationState:
        """Get current animation state."""
        return self._state


class PropertyAnimation(BaseAnimation):
    """Animation for widget properties."""
    
    def __init__(
        self,
        animation_id: str,
        widget: QWidget,
        property_name: str,
        start_value: Any,
        end_value: Any,
        config: AnimationConfiguration,
        parent: Optional[QObject] = None
    ):
        super().__init__(animation_id, config, parent)
        
        self.widget_ref = weakref.ref(widget)
        self.property_name = property_name
        self.start_value = start_value
        self.end_value = end_value
        
        # Property setter
        self._property_setter = getattr(widget, f"set{property_name.capitalize()}", None)
        if not self._property_setter:
            # Try alternative setter names
            alt_names = [f"set_{property_name}", f"set{property_name}"]
            for alt_name in alt_names:
                if hasattr(widget, alt_name):
                    self._property_setter = getattr(widget, alt_name)
                    break
    
    def _prepare_animation(self) -> bool:
        """Prepare property animation."""
        widget = self.widget_ref()
        if not widget or not self._property_setter:
            return False
        
        # Validate property values
        try:
            self._property_setter(self.start_value)
            return True
        except Exception as e:
            logger.error(f"Failed to set property {self.property_name}: {e}")
            return False
    
    def _apply_animation_step(self, progress: float) -> None:
        """Apply property animation step."""
        widget = self.widget_ref()
        if not widget or not self._property_setter:
            return
        
        # Interpolate value
        if isinstance(self.start_value, (int, float)) and isinstance(self.end_value, (int, float)):
            current_value = self.start_value + (self.end_value - self.start_value) * progress
        elif isinstance(self.start_value, QSize) and isinstance(self.end_value, QSize):
            w = int(self.start_value.width() + (self.end_value.width() - self.start_value.width()) * progress)
            h = int(self.start_value.height() + (self.end_value.height() - self.start_value.height()) * progress)
            current_value = QSize(w, h)
        elif isinstance(self.start_value, QPoint) and isinstance(self.end_value, QPoint):
            x = int(self.start_value.x() + (self.end_value.x() - self.start_value.x()) * progress)
            y = int(self.start_value.y() + (self.end_value.y() - self.start_value.y()) * progress)
            current_value = QPoint(x, y)
        elif isinstance(self.start_value, QColor) and isinstance(self.end_value, QColor):
            r = int(self.start_value.red() + (self.end_value.red() - self.start_value.red()) * progress)
            g = int(self.start_value.green() + (self.end_value.green() - self.start_value.green()) * progress)
            b = int(self.start_value.blue() + (self.end_value.blue() - self.start_value.blue()) * progress)
            a = int(self.start_value.alpha() + (self.end_value.alpha() - self.start_value.alpha()) * progress)
            current_value = QColor(r, g, b, a)
        else:
            # For non-interpolable values, switch at 50%
            current_value = self.end_value if progress >= 0.5 else self.start_value
        
        self._property_setter(current_value)
    
    def _cleanup_animation(self) -> None:
        """Clean up property animation."""
        # Ensure final value is set
        widget = self.widget_ref()
        if widget and self._property_setter:
            self._property_setter(self.end_value)


class KeyframeAnimation(BaseAnimation):
    """Animation using keyframes."""
    
    def __init__(
        self,
        animation_id: str,
        widget: QWidget,
        property_name: str,
        keyframes: List[AnimationKeyframe],
        config: AnimationConfiguration,
        parent: Optional[QObject] = None
    ):
        super().__init__(animation_id, config, parent)
        
        self.widget_ref = weakref.ref(widget)
        self.property_name = property_name
        self.keyframes = sorted(keyframes, key=lambda k: k.time_percent)
        
        # Property setter
        self._property_setter = getattr(widget, f"set{property_name.capitalize()}", None)
    
    def _prepare_animation(self) -> bool:
        """Prepare keyframe animation."""
        widget = self.widget_ref()
        return widget is not None and self._property_setter is not None and len(self.keyframes) >= 2
    
    def _apply_animation_step(self, progress: float) -> None:
        """Apply keyframe animation step."""
        widget = self.widget_ref()
        if not widget or not self._property_setter:
            return
        
        # Find surrounding keyframes
        current_keyframe = None
        next_keyframe = None
        
        for i, keyframe in enumerate(self.keyframes):
            if keyframe.time_percent <= progress:
                current_keyframe = keyframe
                if i + 1 < len(self.keyframes):
                    next_keyframe = self.keyframes[i + 1]
            else:
                break
        
        if not current_keyframe:
            current_keyframe = self.keyframes[0]
        
        if not next_keyframe:
            # Use last keyframe value
            self._property_setter(current_keyframe.value)
            return
        
        # Interpolate between keyframes
        keyframe_progress = ((progress - current_keyframe.time_percent) / 
                           (next_keyframe.time_percent - current_keyframe.time_percent))
        
        # Apply keyframe-specific easing
        if next_keyframe.easing:
            # Temporarily change config timing for this segment
            original_timing = self.config.timing
            self.config.timing = next_keyframe.easing
            keyframe_progress = self._apply_easing(keyframe_progress)
            self.config.timing = original_timing
        
        # Interpolate value (simplified - could be extended for different types)
        if isinstance(current_keyframe.value, (int, float)) and isinstance(next_keyframe.value, (int, float)):
            current_value = (current_keyframe.value + 
                           (next_keyframe.value - current_keyframe.value) * keyframe_progress)
        else:
            current_value = next_keyframe.value if keyframe_progress >= 0.5 else current_keyframe.value
        
        self._property_setter(current_value)
    
    def _cleanup_animation(self) -> None:
        """Clean up keyframe animation."""
        # Set final keyframe value
        widget = self.widget_ref()
        if widget and self._property_setter and self.keyframes:
            self._property_setter(self.keyframes[-1].value)


class StaggeredAnimation(BaseAnimation):
    """Animation that staggers multiple sub-animations."""
    
    def __init__(
        self,
        animation_id: str,
        animations: List[BaseAnimation],
        stagger_delay_ms: int,
        config: AnimationConfiguration,
        parent: Optional[QObject] = None
    ):
        super().__init__(animation_id, config, parent)
        
        self.animations = animations
        self.stagger_delay_ms = stagger_delay_ms
        self._started_animations: List[bool] = [False] * len(animations)
    
    def _prepare_animation(self) -> bool:
        """Prepare staggered animation."""
        return all(anim._prepare_animation() for anim in self.animations)
    
    def _apply_animation_step(self, progress: float) -> None:
        """Apply staggered animation step."""
        elapsed_ms = progress * self.config.duration_ms
        
        for i, animation in enumerate(self.animations):
            start_time_ms = i * self.stagger_delay_ms
            
            if elapsed_ms >= start_time_ms and not self._started_animations[i]:
                animation.start()
                self._started_animations[i] = True
    
    def _cleanup_animation(self) -> None:
        """Clean up staggered animation."""
        # Ensure all animations are started
        for i, animation in enumerate(self.animations):
            if not self._started_animations[i]:
                animation.start()


class AnimationManager(BaseUIComponent):
    """Manages and orchestrates animations in the layout system."""
    
    # Signals
    animation_started = pyqtSignal(str)  # animation_id
    animation_completed = pyqtSignal(str, float)  # animation_id, duration_ms
    animation_failed = pyqtSignal(str, str)  # animation_id, error_message
    performance_warning = pyqtSignal(str, float)  # metric_name, value
    
    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigurationManager,
        state_manager: Store,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        # Animation tracking
        self._active_animations: Dict[str, BaseAnimation] = {}
        self._completed_animations: List[AnimationMetrics] = []
        self._max_history = 100
        
        # Configuration
        self._default_config = AnimationConfiguration()
        self._max_concurrent_animations = 10
        self._performance_monitoring = True
        
        # Performance monitoring
        self._performance_timer = QTimer(self)
        self._performance_timer.timeout.connect(self._monitor_performance)
        self._performance_timer.start(1000)  # Monitor every second
        
        logger.debug("AnimationManager initialized")
    
    def _setup_component(self) -> None:
        """Setup animation manager."""
        # Subscribe to events
        self.subscribe_to_event("accessibility.reduce_motion", self._handle_reduce_motion)
        self.subscribe_to_event("system.performance_mode", self._handle_performance_mode)
        
        # Load configuration
        self._load_configuration()
        
        logger.info("Animation manager setup complete")
    
    def _load_configuration(self) -> None:
        """Load animation configuration from settings."""
        # Animation preferences
        self._default_config.duration_ms = self.get_config("animations.default_duration", 300)
        self._default_config.target_fps = self.get_config("animations.target_fps", 60)
        self._default_config.respect_reduced_motion = self.get_config(
            "accessibility.respect_reduced_motion", True
        )
        
        # Performance settings
        self._max_concurrent_animations = self.get_config("animations.max_concurrent", 10)
        battery_mode = self.get_config("system.battery_optimization", False)
        if battery_mode:
            self._default_config.target_fps = 30
            self._default_config.optimize_for_battery = True
    
    def create_property_animation(
        self,
        animation_id: str,
        widget: QWidget,
        property_name: str,
        start_value: Any,
        end_value: Any,
        config: Optional[AnimationConfiguration] = None
    ) -> PropertyAnimation:
        """Create a property animation.
        
        Args:
            animation_id: Unique identifier for the animation
            widget: Target widget
            property_name: Name of property to animate
            start_value: Starting value
            end_value: Ending value
            config: Animation configuration (uses default if None)
            
        Returns:
            PropertyAnimation instance
        """
        config = config or self._default_config
        
        animation = PropertyAnimation(
            animation_id=animation_id,
            widget=widget,
            property_name=property_name,
            start_value=start_value,
            end_value=end_value,
            config=config,
            parent=self
        )
        
        # Connect signals
        animation.started.connect(lambda: self._on_animation_started(animation))
        animation.finished.connect(lambda: self._on_animation_finished(animation))
        
        return animation
    
    def create_keyframe_animation(
        self,
        animation_id: str,
        widget: QWidget,
        property_name: str,
        keyframes: List[AnimationKeyframe],
        config: Optional[AnimationConfiguration] = None
    ) -> KeyframeAnimation:
        """Create a keyframe animation.
        
        Args:
            animation_id: Unique identifier for the animation
            widget: Target widget
            property_name: Name of property to animate
            keyframes: List of keyframes
            config: Animation configuration (uses default if None)
            
        Returns:
            KeyframeAnimation instance
        """
        config = config or self._default_config
        
        animation = KeyframeAnimation(
            animation_id=animation_id,
            widget=widget,
            property_name=property_name,
            keyframes=keyframes,
            config=config,
            parent=self
        )
        
        # Connect signals
        animation.started.connect(lambda: self._on_animation_started(animation))
        animation.finished.connect(lambda: self._on_animation_finished(animation))
        
        return animation
    
    def create_staggered_animation(
        self,
        animation_id: str,
        animations: List[BaseAnimation],
        stagger_delay_ms: int,
        config: Optional[AnimationConfiguration] = None
    ) -> StaggeredAnimation:
        """Create a staggered animation.
        
        Args:
            animation_id: Unique identifier for the animation
            animations: List of animations to stagger
            stagger_delay_ms: Delay between each animation start
            config: Animation configuration (uses default if None)
            
        Returns:
            StaggeredAnimation instance
        """
        config = config or self._default_config
        
        animation = StaggeredAnimation(
            animation_id=animation_id,
            animations=animations,
            stagger_delay_ms=stagger_delay_ms,
            config=config,
            parent=self
        )
        
        # Connect signals
        animation.started.connect(lambda: self._on_animation_started(animation))
        animation.finished.connect(lambda: self._on_animation_finished(animation))
        
        return animation
    
    def start_animation(self, animation: BaseAnimation) -> bool:
        """Start an animation.
        
        Args:
            animation: Animation to start
            
        Returns:
            True if animation was started successfully
        """
        # Check concurrent animation limit
        if len(self._active_animations) >= self._max_concurrent_animations:
            logger.warning(f"Max concurrent animations reached ({self._max_concurrent_animations})")
            return False
        
        # Check if animation ID is already in use
        if animation.animation_id in self._active_animations:
            logger.warning(f"Animation {animation.animation_id} is already running")
            return False
        
        # Start animation
        if animation.start():
            self._active_animations[animation.animation_id] = animation
            return True
        
        return False
    
    def stop_animation(self, animation_id: str) -> bool:
        """Stop a running animation.
        
        Args:
            animation_id: ID of animation to stop
            
        Returns:
            True if animation was stopped
        """
        if animation_id in self._active_animations:
            animation = self._active_animations[animation_id]
            animation.stop()
            return True
        
        return False
    
    def pause_animation(self, animation_id: str) -> bool:
        """Pause a running animation.
        
        Args:
            animation_id: ID of animation to pause
            
        Returns:
            True if animation was paused
        """
        if animation_id in self._active_animations:
            animation = self._active_animations[animation_id]
            animation.pause()
            return True
        
        return False
    
    def resume_animation(self, animation_id: str) -> bool:
        """Resume a paused animation.
        
        Args:
            animation_id: ID of animation to resume
            
        Returns:
            True if animation was resumed
        """
        if animation_id in self._active_animations:
            animation = self._active_animations[animation_id]
            animation.resume()
            return True
        
        return False
    
    def stop_all_animations(self) -> int:
        """Stop all running animations.
        
        Returns:
            Number of animations that were stopped
        """
        stopped_count = 0
        for animation in list(self._active_animations.values()):
            animation.stop()
            stopped_count += 1
        
        return stopped_count
    
    def get_active_animations(self) -> List[str]:
        """Get list of active animation IDs."""
        return list(self._active_animations.keys())
    
    def get_animation_metrics(self) -> List[AnimationMetrics]:
        """Get performance metrics for recent animations."""
        return self._completed_animations.copy()
    
    def clear_animation_history(self) -> None:
        """Clear animation metrics history."""
        self._completed_animations.clear()
    
    def set_default_configuration(self, config: AnimationConfiguration) -> None:
        """Set default animation configuration."""
        self._default_config = config
        logger.debug("Updated default animation configuration")
    
    def _on_animation_started(self, animation: BaseAnimation) -> None:
        """Handle animation start."""
        self.animation_started.emit(animation.animation_id)
        logger.debug(f"Animation started: {animation.animation_id}")
    
    def _on_animation_finished(self, animation: BaseAnimation) -> None:
        """Handle animation completion."""
        animation_id = animation.animation_id
        
        # Remove from active animations
        self._active_animations.pop(animation_id, None)
        
        # Store metrics
        metrics = animation.get_metrics()
        self._completed_animations.append(metrics)
        
        # Trim history
        if len(self._completed_animations) > self._max_history:
            self._completed_animations = self._completed_animations[-self._max_history:]
        
        # Emit completion signal
        self.animation_completed.emit(animation_id, metrics.actual_duration_ms)
        
        logger.debug(f"Animation completed: {animation_id} "
                    f"({metrics.actual_duration_ms:.1f}ms, {metrics.average_fps:.1f}fps)")
    
    def _monitor_performance(self) -> None:
        """Monitor animation performance."""
        if not self._performance_monitoring or not self._active_animations:
            return
        
        # Calculate average FPS across all active animations
        total_fps = 0.0
        active_count = 0
        total_dropped_frames = 0
        
        for animation in self._active_animations.values():
            metrics = animation.get_metrics()
            if metrics.average_fps > 0:
                total_fps += metrics.average_fps
                active_count += 1
                total_dropped_frames += metrics.dropped_frames
        
        if active_count > 0:
            average_fps = total_fps / active_count
            
            # Check for performance issues
            if average_fps < self._default_config.target_fps * 0.8:  # 80% of target
                self.performance_warning.emit("low_fps", average_fps)
                logger.warning(f"Low animation FPS detected: {average_fps:.1f}")
            
            if total_dropped_frames > 5:  # Arbitrary threshold
                self.performance_warning.emit("dropped_frames", total_dropped_frames)
                logger.warning(f"Dropped frames detected: {total_dropped_frames}")
    
    # Event handlers
    def _handle_reduce_motion(self, event_data: Dict[str, Any]) -> None:
        """Handle reduced motion accessibility setting."""
        reduce_motion = event_data.get("enabled", False)
        
        if reduce_motion:
            # Disable animations or use instant transitions
            self._default_config.duration_ms = 0
            self._default_config.timing = AnimationTiming.LINEAR
            
            # Stop all current animations
            self.stop_all_animations()
            
            logger.info("Reduced motion enabled - disabling animations")
        else:
            # Re-enable animations
            self._default_config.duration_ms = 300
            self._default_config.timing = AnimationTiming.EASE_OUT
            
            logger.info("Reduced motion disabled - enabling animations")
    
    def _handle_performance_mode(self, event_data: Dict[str, Any]) -> None:
        """Handle system performance mode changes."""
        performance_mode = event_data.get("mode", "normal")
        
        if performance_mode == "battery":
            # Optimize for battery life
            self._default_config.target_fps = 30
            self._default_config.optimize_for_battery = True
            self._max_concurrent_animations = 5
            
            logger.info("Battery mode enabled - reducing animation performance")
        
        elif performance_mode == "performance":
            # Optimize for performance
            self._default_config.target_fps = 60
            self._default_config.optimize_for_battery = False
            self._max_concurrent_animations = 15
            
            logger.info("Performance mode enabled - increasing animation quality")
        
        else:  # normal
            # Default settings
            self._default_config.target_fps = 60
            self._default_config.optimize_for_battery = False
            self._max_concurrent_animations = 10
            
            logger.info("Normal mode enabled - using default animation settings")