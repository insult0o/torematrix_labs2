"""
Animation System for Document Viewer Overlay.
This module provides smooth animations and transitions for overlay elements
including selection states, hover effects, and viewport changes.
"""
from __future__ import annotations

import math
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Callable, Tuple, Union

from PyQt6.QtCore import (QObject, QTimer, QPropertyAnimation, QEasingCurve, 
                         QSequentialAnimationGroup, QParallelAnimationGroup,
                         QVariantAnimation, pyqtSignal, QAbstractAnimation)
from PyQt6.QtGui import QColor, QTransform
from PyQt6.QtWidgets import QWidget, QGraphicsOpacityEffect

from .coordinates import Point, Rectangle


class AnimationType(Enum):
    """Types of animations."""
    FADE = "fade"                   # Opacity transitions
    SCALE = "scale"                 # Size scaling
    TRANSLATE = "translate"         # Position movement
    ROTATE = "rotate"              # Rotation
    COLOR = "color"                # Color transitions
    MORPH = "morph"                # Shape morphing
    ELASTIC = "elastic"            # Elastic/spring effects
    BOUNCE = "bounce"              # Bounce effects
    SELECTION = "selection"        # Selection state changes
    HOVER = "hover"                # Hover state changes


class EasingType(Enum):
    """Easing function types."""
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    EASE_IN_BACK = "ease_in_back"
    EASE_OUT_BACK = "ease_out_back"
    EASE_IN_OUT_BACK = "ease_in_out_back"
    EASE_IN_ELASTIC = "ease_in_elastic"
    EASE_OUT_ELASTIC = "ease_out_elastic"
    EASE_IN_OUT_ELASTIC = "ease_in_out_elastic"
    EASE_IN_BOUNCE = "ease_in_bounce"
    EASE_OUT_BOUNCE = "ease_out_bounce"
    EASE_IN_OUT_BOUNCE = "ease_in_out_bounce"


@dataclass
class AnimationConfig:
    """Configuration for animations."""
    duration: int = 300  # milliseconds
    easing: EasingType = EasingType.EASE_OUT
    delay: int = 0  # milliseconds
    loop_count: int = 1  # -1 for infinite
    auto_reverse: bool = False
    performance_mode: bool = False  # Reduced quality for performance


@dataclass
class AnimationKeyframe:
    """Keyframe for complex animations."""
    time: float  # 0.0 to 1.0
    value: Any
    easing: Optional[EasingType] = None


class AnimationTarget(Protocol):
    """Protocol for objects that can be animated."""
    
    def set_animation_property(self, property_name: str, value: Any) -> None:
        """Set an animated property value."""
        ...
    
    def get_animation_property(self, property_name: str) -> Any:
        """Get current property value."""
        ...


class CustomEasingCurve:
    """Custom easing curve implementations."""
    
    @staticmethod
    def ease_in_back(t: float, overshoot: float = 1.70158) -> float:
        """Ease in back with overshoot."""
        return t * t * ((overshoot + 1) * t - overshoot)
    
    @staticmethod
    def ease_out_back(t: float, overshoot: float = 1.70158) -> float:
        """Ease out back with overshoot."""
        t -= 1
        return t * t * ((overshoot + 1) * t + overshoot) + 1
    
    @staticmethod
    def ease_in_out_back(t: float, overshoot: float = 1.70158) -> float:
        """Ease in-out back with overshoot."""
        overshoot *= 1.525
        t *= 2
        if t < 1:
            return 0.5 * (t * t * ((overshoot + 1) * t - overshoot))
        t -= 2
        return 0.5 * (t * t * ((overshoot + 1) * t + overshoot) + 2)
    
    @staticmethod
    def ease_out_elastic(t: float, amplitude: float = 1.0, period: float = 0.3) -> float:
        """Ease out elastic with amplitude and period."""
        if t == 0 or t == 1:
            return t
        
        s = period / 4 if amplitude < 1 else period / (2 * math.pi) * math.asin(1 / amplitude)
        return amplitude * (2 ** (-10 * t)) * math.sin((t - s) * (2 * math.pi) / period) + 1
    
    @staticmethod
    def ease_out_bounce(t: float) -> float:
        """Ease out bounce."""
        if t < 1 / 2.75:
            return 7.5625 * t * t
        elif t < 2 / 2.75:
            t -= 1.5 / 2.75
            return 7.5625 * t * t + 0.75
        elif t < 2.5 / 2.75:
            t -= 2.25 / 2.75
            return 7.5625 * t * t + 0.9375
        else:
            t -= 2.625 / 2.75
            return 7.5625 * t * t + 0.984375


class PropertyAnimation(QVariantAnimation):
    """Custom property animation with extended easing support."""
    
    def __init__(self, target: AnimationTarget, property_name: str):
        super().__init__()
        self.target = target
        self.property_name = property_name
        self.custom_easing: Optional[Callable[[float], float]] = None
        
    def set_custom_easing(self, easing_func: Callable[[float], float]) -> None:
        """Set custom easing function."""
        self.custom_easing = easing_func
    
    def updateCurrentValue(self, value) -> None:
        """Update the target property with current value."""
        if self.target:
            self.target.set_animation_property(self.property_name, value)
    
    def interpolated(self, from_value, to_value, progress: float):
        """Custom interpolation with easing support."""
        if self.custom_easing:
            progress = self.custom_easing(progress)
        
        # Handle different value types
        if isinstance(from_value, (int, float)):
            return from_value + (to_value - from_value) * progress
        elif isinstance(from_value, Point):
            return Point(
                from_value.x + (to_value.x - from_value.x) * progress,
                from_value.y + (to_value.y - from_value.y) * progress
            )
        elif isinstance(from_value, QColor):
            return QColor(
                int(from_value.red() + (to_value.red() - from_value.red()) * progress),
                int(from_value.green() + (to_value.green() - from_value.green()) * progress),
                int(from_value.blue() + (to_value.blue() - from_value.blue()) * progress),
                int(from_value.alpha() + (to_value.alpha() - from_value.alpha()) * progress)
            )
        else:
            # Default interpolation
            return super().interpolated(from_value, to_value, progress)


class AnimationGroup(QObject):
    """Group of related animations."""
    
    def __init__(self, name: str = "", parallel: bool = True):
        super().__init__()
        self.name = name
        self.animations: List[PropertyAnimation] = []
        
        if parallel:
            self.group = QParallelAnimationGroup()
        else:
            self.group = QSequentialAnimationGroup()
        
        # Signals
        self.group.finished.connect(self._on_finished)
        self.group.stateChanged.connect(self._on_state_changed)
    
    def add_animation(self, animation: PropertyAnimation) -> None:
        """Add animation to the group."""
        self.animations.append(animation)
        self.group.addAnimation(animation)
    
    def start(self) -> None:
        """Start the animation group."""
        self.group.start()
    
    def stop(self) -> None:
        """Stop the animation group."""
        self.group.stop()
    
    def pause(self) -> None:
        """Pause the animation group."""
        self.group.pause()
    
    def resume(self) -> None:
        """Resume the animation group."""
        self.group.resume()
    
    def _on_finished(self) -> None:
        """Handle animation group finished."""
        pass
    
    def _on_state_changed(self, new_state, old_state) -> None:
        """Handle animation state change."""
        pass


class AnimationSignals(QObject):
    """Signals for animation events."""
    animation_started = pyqtSignal(str)  # animation_id
    animation_finished = pyqtSignal(str)  # animation_id
    animation_group_started = pyqtSignal(str)  # group_name
    animation_group_finished = pyqtSignal(str)  # group_name
    performance_warning = pyqtSignal(str)  # warning_message


class AnimationManager(QObject):
    """
    Main animation manager for the overlay system.
    Handles animation creation, scheduling, and performance optimization.
    """
    
    def __init__(self):
        super().__init__()
        
        # Animation registry
        self.active_animations: Dict[str, PropertyAnimation] = {}
        self.animation_groups: Dict[str, AnimationGroup] = {}
        
        # Configuration
        self.global_config = AnimationConfig()
        self.performance_mode = False
        self.animations_enabled = True
        
        # Performance tracking
        self.animation_metrics: Dict[str, List[float]] = {}
        self.max_concurrent_animations = 20
        
        # Predefined animation configs
        self.animation_presets: Dict[str, AnimationConfig] = {
            "fast": AnimationConfig(duration=150, easing=EasingType.EASE_OUT),
            "normal": AnimationConfig(duration=300, easing=EasingType.EASE_OUT),
            "slow": AnimationConfig(duration=500, easing=EasingType.EASE_IN_OUT),
            "bounce": AnimationConfig(duration=600, easing=EasingType.EASE_OUT_BOUNCE),
            "elastic": AnimationConfig(duration=800, easing=EasingType.EASE_OUT_ELASTIC),
            "selection": AnimationConfig(duration=200, easing=EasingType.EASE_OUT),
            "hover": AnimationConfig(duration=150, easing=EasingType.EASE_OUT),
        }
        
        # Signals
        self.signals = AnimationSignals()
        
        # Performance timer
        self.performance_timer = QTimer()
        self.performance_timer.setInterval(1000)  # Check every second
        self.performance_timer.timeout.connect(self._check_performance)
        self.performance_timer.start()
    
    def animate_property(self, target: AnimationTarget, property_name: str,
                        from_value: Any, to_value: Any,
                        config: Optional[AnimationConfig] = None,
                        animation_id: Optional[str] = None) -> str:
        """Animate a property from one value to another."""
        if not self.animations_enabled:
            # Set final value immediately if animations disabled
            target.set_animation_property(property_name, to_value)
            return ""
        
        # Generate animation ID
        if not animation_id:
            animation_id = f"{id(target)}_{property_name}_{time.time()}"
        
        # Use provided config or default
        if not config:
            config = self.global_config
        
        # Check performance limits
        if len(self.active_animations) >= self.max_concurrent_animations:
            self.signals.performance_warning.emit(
                f"Maximum concurrent animations ({self.max_concurrent_animations}) reached"
            )
            if self.performance_mode:
                # Skip animation in performance mode
                target.set_animation_property(property_name, to_value)
                return ""
        
        # Stop existing animation for the same property
        existing_key = f"{id(target)}_{property_name}"
        for key in list(self.active_animations.keys()):
            if key.startswith(existing_key):
                self.stop_animation(key)
        
        # Create animation
        animation = PropertyAnimation(target, property_name)
        animation.setStartValue(from_value)
        animation.setEndValue(to_value)
        animation.setDuration(config.duration)
        
        # Set easing curve
        self._set_easing_curve(animation, config.easing)
        
        # Connect signals
        animation.finished.connect(lambda: self._on_animation_finished(animation_id))
        animation.stateChanged.connect(
            lambda new_state, old_state: self._on_animation_state_changed(
                animation_id, new_state, old_state
            )
        )
        
        # Add delay if specified
        if config.delay > 0:
            QTimer.singleShot(config.delay, animation.start)
        else:
            animation.start()
        
        # Track animation
        self.active_animations[animation_id] = animation
        self.signals.animation_started.emit(animation_id)
        
        return animation_id
    
    def animate_selection(self, target: AnimationTarget, selected: bool) -> str:
        """Animate element selection state."""
        config = self.animation_presets["selection"]
        
        if selected:
            # Animate to selected state
            return self.animate_property(
                target, "selection_opacity", 0.7, 1.0, config,
                f"selection_{id(target)}"
            )
        else:
            # Animate to unselected state
            return self.animate_property(
                target, "selection_opacity", 1.0, 0.7, config,
                f"selection_{id(target)}"
            )
    
    def animate_hover(self, target: AnimationTarget, hover: bool) -> str:
        """Animate element hover state."""
        config = self.animation_presets["hover"]
        
        if hover:
            # Animate to hover state
            return self.animate_property(
                target, "hover_brightness", 1.0, 1.2, config,
                f"hover_{id(target)}"
            )
        else:
            # Animate to normal state
            return self.animate_property(
                target, "hover_brightness", 1.2, 1.0, config,
                f"hover_{id(target)}"
            )
    
    def animate_fade_in(self, target: AnimationTarget, 
                       config: Optional[AnimationConfig] = None) -> str:
        """Animate element fade in."""
        if not config:
            config = self.animation_presets["normal"]
        
        return self.animate_property(
            target, "opacity", 0.0, 1.0, config,
            f"fade_in_{id(target)}"
        )
    
    def animate_fade_out(self, target: AnimationTarget,
                        config: Optional[AnimationConfig] = None) -> str:
        """Animate element fade out."""
        if not config:
            config = self.animation_presets["normal"]
        
        return self.animate_property(
            target, "opacity", 1.0, 0.0, config,
            f"fade_out_{id(target)}"
        )
    
    def animate_scale(self, target: AnimationTarget, from_scale: float, to_scale: float,
                     config: Optional[AnimationConfig] = None) -> str:
        """Animate element scaling."""
        if not config:
            config = self.animation_presets["normal"]
        
        return self.animate_property(
            target, "scale", from_scale, to_scale, config,
            f"scale_{id(target)}"
        )
    
    def animate_translate(self, target: AnimationTarget, from_pos: Point, to_pos: Point,
                         config: Optional[AnimationConfig] = None) -> str:
        """Animate element translation."""
        if not config:
            config = self.animation_presets["normal"]
        
        return self.animate_property(
            target, "position", from_pos, to_pos, config,
            f"translate_{id(target)}"
        )
    
    def animate_color(self, target: AnimationTarget, from_color: QColor, to_color: QColor,
                     config: Optional[AnimationConfig] = None) -> str:
        """Animate color transition."""
        if not config:
            config = self.animation_presets["normal"]
        
        return self.animate_property(
            target, "color", from_color, to_color, config,
            f"color_{id(target)}"
        )
    
    def create_animation_sequence(self, name: str) -> AnimationGroup:
        """Create a sequential animation group."""
        group = AnimationGroup(name, parallel=False)
        self.animation_groups[name] = group
        
        group.group.finished.connect(
            lambda: self.signals.animation_group_finished.emit(name)
        )
        
        return group
    
    def create_animation_parallel(self, name: str) -> AnimationGroup:
        """Create a parallel animation group."""
        group = AnimationGroup(name, parallel=True)
        self.animation_groups[name] = group
        
        group.group.finished.connect(
            lambda: self.signals.animation_group_finished.emit(name)
        )
        
        return group
    
    def stop_animation(self, animation_id: str) -> bool:
        """Stop a specific animation."""
        if animation_id in self.active_animations:
            animation = self.active_animations[animation_id]
            animation.stop()
            del self.active_animations[animation_id]
            return True
        return False
    
    def stop_all_animations(self) -> None:
        """Stop all active animations."""
        for animation_id in list(self.active_animations.keys()):
            self.stop_animation(animation_id)
    
    def pause_animation(self, animation_id: str) -> bool:
        """Pause a specific animation."""
        if animation_id in self.active_animations:
            animation = self.active_animations[animation_id]
            animation.pause()
            return True
        return False
    
    def resume_animation(self, animation_id: str) -> bool:
        """Resume a paused animation."""
        if animation_id in self.active_animations:
            animation = self.active_animations[animation_id]
            animation.resume()
            return True
        return False
    
    def set_performance_mode(self, enabled: bool) -> None:
        """Enable or disable performance mode."""
        self.performance_mode = enabled
        
        if enabled:
            # Reduce animation quality and duration
            for preset in self.animation_presets.values():
                preset.duration = int(preset.duration * 0.5)
                preset.performance_mode = True
        else:
            # Restore normal animation quality
            self._restore_animation_presets()
    
    def set_animations_enabled(self, enabled: bool) -> None:
        """Enable or disable all animations."""
        self.animations_enabled = enabled
        
        if not enabled:
            self.stop_all_animations()
    
    def _set_easing_curve(self, animation: PropertyAnimation, easing: EasingType) -> None:
        """Set easing curve for animation."""
        if easing == EasingType.LINEAR:
            animation.setEasingCurve(QEasingCurve.Type.Linear)
        elif easing == EasingType.EASE_IN:
            animation.setEasingCurve(QEasingCurve.Type.InCubic)
        elif easing == EasingType.EASE_OUT:
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        elif easing == EasingType.EASE_IN_OUT:
            animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        elif easing == EasingType.EASE_IN_BACK:
            animation.set_custom_easing(CustomEasingCurve.ease_in_back)
        elif easing == EasingType.EASE_OUT_BACK:
            animation.set_custom_easing(CustomEasingCurve.ease_out_back)
        elif easing == EasingType.EASE_IN_OUT_BACK:
            animation.set_custom_easing(CustomEasingCurve.ease_in_out_back)
        elif easing == EasingType.EASE_OUT_ELASTIC:
            animation.set_custom_easing(CustomEasingCurve.ease_out_elastic)
        elif easing == EasingType.EASE_OUT_BOUNCE:
            animation.set_custom_easing(CustomEasingCurve.ease_out_bounce)
        else:
            # Default to ease out
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def _on_animation_finished(self, animation_id: str) -> None:
        """Handle animation finished."""
        if animation_id in self.active_animations:
            del self.active_animations[animation_id]
        
        self.signals.animation_finished.emit(animation_id)
    
    def _on_animation_state_changed(self, animation_id: str, new_state, old_state) -> None:
        """Handle animation state change."""
        # Track performance metrics
        if new_state == QAbstractAnimation.State.Running:
            self._start_performance_tracking(animation_id)
        elif new_state == QAbstractAnimation.State.Stopped:
            self._end_performance_tracking(animation_id)
    
    def _start_performance_tracking(self, animation_id: str) -> None:
        """Start performance tracking for animation."""
        if animation_id not in self.animation_metrics:
            self.animation_metrics[animation_id] = []
        
        # Record start time
        start_time = time.time()
        self.animation_metrics[animation_id].append(start_time)
    
    def _end_performance_tracking(self, animation_id: str) -> None:
        """End performance tracking for animation."""
        if animation_id in self.animation_metrics:
            metrics = self.animation_metrics[animation_id]
            if metrics:
                # Calculate duration
                start_time = metrics[-1]
                duration = time.time() - start_time
                
                # Store duration instead of start time
                metrics[-1] = duration
    
    def _check_performance(self) -> None:
        """Check animation performance and adjust if needed."""
        active_count = len(self.active_animations)
        
        if active_count > self.max_concurrent_animations * 0.8:
            self.signals.performance_warning.emit(
                f"High animation load: {active_count} active animations"
            )
            
            if not self.performance_mode:
                # Auto-enable performance mode
                self.set_performance_mode(True)
    
    def _restore_animation_presets(self) -> None:
        """Restore original animation preset values."""
        self.animation_presets = {
            "fast": AnimationConfig(duration=150, easing=EasingType.EASE_OUT),
            "normal": AnimationConfig(duration=300, easing=EasingType.EASE_OUT),
            "slow": AnimationConfig(duration=500, easing=EasingType.EASE_IN_OUT),
            "bounce": AnimationConfig(duration=600, easing=EasingType.EASE_OUT_BOUNCE),
            "elastic": AnimationConfig(duration=800, easing=EasingType.EASE_OUT_ELASTIC),
            "selection": AnimationConfig(duration=200, easing=EasingType.EASE_OUT),
            "hover": AnimationConfig(duration=150, easing=EasingType.EASE_OUT),
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get animation performance metrics."""
        total_animations = len(self.animation_metrics)
        active_animations = len(self.active_animations)
        
        # Calculate average duration
        all_durations = []
        for metrics in self.animation_metrics.values():
            all_durations.extend([m for m in metrics if isinstance(m, float)])
        
        avg_duration = sum(all_durations) / len(all_durations) if all_durations else 0
        
        return {
            "total_animations": total_animations,
            "active_animations": active_animations,
            "average_duration": avg_duration,
            "performance_mode": self.performance_mode,
            "animations_enabled": self.animations_enabled,
            "max_concurrent": self.max_concurrent_animations
        }
    
    def register_animation_preset(self, name: str, config: AnimationConfig) -> None:
        """Register a custom animation preset."""
        self.animation_presets[name] = config
    
    def get_animation_preset(self, name: str) -> Optional[AnimationConfig]:
        """Get an animation preset by name."""
        return self.animation_presets.get(name)


# Utility functions for animations
def animate_element_selection(element: AnimationTarget, selected: bool, 
                            manager: Optional[AnimationManager] = None) -> str:
    """Utility function to animate element selection."""
    if not manager:
        manager = AnimationManager()
    
    return manager.animate_selection(element, selected)


def animate_element_hover(element: AnimationTarget, hover: bool,
                         manager: Optional[AnimationManager] = None) -> str:
    """Utility function to animate element hover."""
    if not manager:
        manager = AnimationManager()
    
    return manager.animate_hover(element, hover)


class AnimationMixin:
    """Mixin to add animation support to any object."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.animation_manager: Optional[AnimationManager] = None
        self.animated_properties: Dict[str, Any] = {}
    
    def set_animation_manager(self, manager: AnimationManager) -> None:
        """Set the animation manager."""
        self.animation_manager = manager
    
    def set_animation_property(self, property_name: str, value: Any) -> None:
        """Set an animated property value."""
        self.animated_properties[property_name] = value
        
        # Apply the property change (override in subclasses)
        self._apply_animation_property(property_name, value)
    
    def get_animation_property(self, property_name: str) -> Any:
        """Get current animated property value."""
        return self.animated_properties.get(property_name)
    
    def _apply_animation_property(self, property_name: str, value: Any) -> None:
        """Apply animated property change (override in subclasses)."""
        pass
    
    def animate_to(self, property_name: str, target_value: Any,
                   config: Optional[AnimationConfig] = None) -> str:
        """Animate this object's property to a target value."""
        if not self.animation_manager:
            self.set_animation_property(property_name, target_value)
            return ""
        
        current_value = self.get_animation_property(property_name)
        return self.animation_manager.animate_property(
            self, property_name, current_value, target_value, config
        )