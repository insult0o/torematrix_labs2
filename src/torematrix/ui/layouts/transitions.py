"""Layout Transition System for TORE Matrix Labs V3.

This module provides smooth layout transitions with animation support, state preservation,
and accessibility considerations for the layout management system.
"""

from typing import Dict, List, Optional, Any, Callable, Union, Protocol
from enum import Enum, auto
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
import asyncio
from datetime import datetime, timedelta

from PyQt6.QtWidgets import (
    QWidget, QGraphicsOpacityEffect, QGraphicsEffect, QLayout,
    QApplication, QMainWindow
)
from PyQt6.QtCore import (
    QObject, QTimer, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QSequentialAnimationGroup, pyqtSignal, QRect, QSize, QPoint
)
from PyQt6.QtGui import QPixmap, QPainter

from ...core.events import EventBus
from ...core.config import ConfigurationManager
from ...core.state import Store
from ..base import BaseUIComponent
from .base import LayoutConfiguration, LayoutState, LayoutType, LayoutGeometry

logger = logging.getLogger(__name__)


class TransitionType(Enum):
    """Available transition animation types."""
    SLIDE = auto()      # Sliding motion between layouts
    FADE = auto()       # Cross-fade between layouts  
    SCALE = auto()      # Scaling transition effect
    FLIP = auto()       # 3D flip transition
    MORPH = auto()      # Morphing component transitions
    INSTANT = auto()    # No animation for accessibility


class TransitionDirection(Enum):
    """Direction for directional transitions."""
    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()
    IN = auto()
    OUT = auto()


class TransitionState(Enum):
    """Current state of a transition."""
    IDLE = auto()
    PREPARING = auto()
    ANIMATING = auto()
    COMPLETING = auto()
    INTERRUPTED = auto()
    FAILED = auto()


@dataclass
class TransitionConfiguration:
    """Configuration for layout transitions."""
    transition_type: TransitionType = TransitionType.FADE
    duration_ms: int = 300
    easing_curve: QEasingCurve.Type = QEasingCurve.Type.OutCubic
    direction: Optional[TransitionDirection] = None
    preserve_state: bool = True
    enable_accessibility: bool = True
    stagger_components: bool = False
    stagger_delay_ms: int = 50
    
    # Performance settings
    use_pixmap_cache: bool = True
    max_concurrent_animations: int = 10
    frame_rate_target: int = 60


@dataclass
class ComponentState:
    """Preserved component state during transitions."""
    widget_id: str
    geometry: QRect
    visibility: bool
    opacity: float = 1.0
    scroll_position: Optional[QPoint] = None
    selection_state: Optional[Dict[str, Any]] = None
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class TransitionMetrics:
    """Performance metrics for transitions."""
    start_time: datetime
    end_time: Optional[datetime] = None
    actual_duration_ms: float = 0.0
    target_duration_ms: float = 300.0
    frame_drops: int = 0
    average_fps: float = 0.0
    memory_peak_mb: float = 0.0
    cpu_usage_percent: float = 0.0


class TransitionEffect(ABC):
    """Abstract base class for transition effects."""
    
    @abstractmethod
    def prepare(self, old_layout: QWidget, new_layout: QWidget) -> None:
        """Prepare widgets for transition."""
        pass
    
    @abstractmethod
    def create_animation(self, config: TransitionConfiguration) -> QPropertyAnimation:
        """Create the animation for this effect."""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up after transition."""
        pass


class FadeTransition(TransitionEffect):
    """Cross-fade transition between layouts."""
    
    def __init__(self):
        self.old_effect: Optional[QGraphicsOpacityEffect] = None
        self.new_effect: Optional[QGraphicsOpacityEffect] = None
        self.old_widget: Optional[QWidget] = None
        self.new_widget: Optional[QWidget] = None
    
    def prepare(self, old_layout: QWidget, new_layout: QWidget) -> None:
        """Prepare widgets for fade transition."""
        self.old_widget = old_layout
        self.new_widget = new_layout
        
        # Create opacity effects
        self.old_effect = QGraphicsOpacityEffect()
        self.new_effect = QGraphicsOpacityEffect()
        
        # Set initial states
        self.old_effect.setOpacity(1.0)
        self.new_effect.setOpacity(0.0)
        
        # Apply effects
        old_layout.setGraphicsEffect(self.old_effect)
        new_layout.setGraphicsEffect(self.new_effect)
        
        # Show new widget
        new_layout.show()
    
    def create_animation(self, config: TransitionConfiguration) -> QParallelAnimationGroup:
        """Create fade animation group."""
        animation_group = QParallelAnimationGroup()
        
        # Fade out old widget
        if self.old_effect:
            fade_out = QPropertyAnimation(self.old_effect, b"opacity")
            fade_out.setStartValue(1.0)
            fade_out.setEndValue(0.0)
            fade_out.setDuration(config.duration_ms)
            fade_out.setEasingCurve(config.easing_curve)
            animation_group.addAnimation(fade_out)
        
        # Fade in new widget
        if self.new_effect:
            fade_in = QPropertyAnimation(self.new_effect, b"opacity")
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setDuration(config.duration_ms)
            fade_in.setEasingCurve(config.easing_curve)
            animation_group.addAnimation(fade_in)
        
        return animation_group
    
    def cleanup(self) -> None:
        """Clean up fade transition effects."""
        if self.old_widget and self.old_effect:
            self.old_widget.setGraphicsEffect(None)
            self.old_widget.hide()
        
        if self.new_widget and self.new_effect:
            self.new_widget.setGraphicsEffect(None)
        
        self.old_effect = None
        self.new_effect = None
        self.old_widget = None
        self.new_widget = None


class SlideTransition(TransitionEffect):
    """Sliding transition between layouts."""
    
    def __init__(self):
        self.old_widget: Optional[QWidget] = None
        self.new_widget: Optional[QWidget] = None
        self.container: Optional[QWidget] = None
        self.original_geometry: Optional[QRect] = None
    
    def prepare(self, old_layout: QWidget, new_layout: QWidget) -> None:
        """Prepare widgets for slide transition."""
        self.old_widget = old_layout
        self.new_widget = new_layout
        self.container = old_layout.parent()
        
        if self.container:
            self.original_geometry = self.container.geometry()
    
    def create_animation(self, config: TransitionConfiguration) -> QParallelAnimationGroup:
        """Create slide animation group."""
        animation_group = QParallelAnimationGroup()
        
        if not self.container or not self.original_geometry:
            return animation_group
        
        # Determine slide direction
        direction = config.direction or TransitionDirection.LEFT
        width = self.original_geometry.width()
        height = self.original_geometry.height()
        
        # Calculate start and end positions
        if direction == TransitionDirection.LEFT:
            old_end = QRect(-width, 0, width, height)
            new_start = QRect(width, 0, width, height)
        elif direction == TransitionDirection.RIGHT:
            old_end = QRect(width, 0, width, height)
            new_start = QRect(-width, 0, width, height)
        elif direction == TransitionDirection.UP:
            old_end = QRect(0, -height, width, height)
            new_start = QRect(0, height, width, height)
        else:  # DOWN
            old_end = QRect(0, height, width, height)
            new_start = QRect(0, -height, width, height)
        
        new_end = QRect(0, 0, width, height)
        
        # Position new widget
        if self.new_widget:
            self.new_widget.setGeometry(new_start)
            self.new_widget.show()
        
        # Animate old widget out
        if self.old_widget:
            old_animation = QPropertyAnimation(self.old_widget, b"geometry")
            old_animation.setStartValue(self.original_geometry)
            old_animation.setEndValue(old_end)
            old_animation.setDuration(config.duration_ms)
            old_animation.setEasingCurve(config.easing_curve)
            animation_group.addAnimation(old_animation)
        
        # Animate new widget in
        if self.new_widget:
            new_animation = QPropertyAnimation(self.new_widget, b"geometry")
            new_animation.setStartValue(new_start)
            new_animation.setEndValue(new_end)
            new_animation.setDuration(config.duration_ms)
            new_animation.setEasingCurve(config.easing_curve)
            animation_group.addAnimation(new_animation)
        
        return animation_group
    
    def cleanup(self) -> None:
        """Clean up slide transition."""
        if self.old_widget:
            self.old_widget.hide()
        
        self.old_widget = None
        self.new_widget = None
        self.container = None
        self.original_geometry = None


class ScaleTransition(TransitionEffect):
    """Scaling transition effect."""
    
    def __init__(self):
        self.old_widget: Optional[QWidget] = None
        self.new_widget: Optional[QWidget] = None
        self.old_effect: Optional[QGraphicsOpacityEffect] = None
        self.new_effect: Optional[QGraphicsOpacityEffect] = None
    
    def prepare(self, old_layout: QWidget, new_layout: QWidget) -> None:
        """Prepare widgets for scale transition."""
        self.old_widget = old_layout
        self.new_widget = new_layout
        
        # Create effects for opacity changes
        self.old_effect = QGraphicsOpacityEffect()
        self.new_effect = QGraphicsOpacityEffect()
        
        self.old_effect.setOpacity(1.0)
        self.new_effect.setOpacity(0.0)
        
        old_layout.setGraphicsEffect(self.old_effect)
        new_layout.setGraphicsEffect(self.new_effect)
        
        # Start new widget scaled down
        new_layout.setFixedSize(1, 1)
        new_layout.show()
    
    def create_animation(self, config: TransitionConfiguration) -> QSequentialAnimationGroup:
        """Create scale animation sequence."""
        animation_group = QSequentialAnimationGroup()
        
        # Phase 1: Scale down old widget while fading out
        phase1 = QParallelAnimationGroup()
        
        if self.old_widget and self.old_effect:
            # Scale animation (simulate by changing size)
            current_size = self.old_widget.size()
            scale_animation = QPropertyAnimation(self.old_widget, b"size")
            scale_animation.setStartValue(current_size)
            scale_animation.setEndValue(QSize(1, 1))
            scale_animation.setDuration(config.duration_ms // 2)
            scale_animation.setEasingCurve(QEasingCurve.Type.InCubic)
            phase1.addAnimation(scale_animation)
            
            # Fade out
            fade_out = QPropertyAnimation(self.old_effect, b"opacity")
            fade_out.setStartValue(1.0)
            fade_out.setEndValue(0.0)
            fade_out.setDuration(config.duration_ms // 2)
            fade_out.setEasingCurve(QEasingCurve.Type.InCubic)
            phase1.addAnimation(fade_out)
        
        animation_group.addAnimation(phase1)
        
        # Phase 2: Scale up new widget while fading in
        phase2 = QParallelAnimationGroup()
        
        if self.new_widget and self.new_effect:
            # Get target size
            target_size = self.old_widget.size() if self.old_widget else QSize(800, 600)
            
            # Scale animation
            scale_animation = QPropertyAnimation(self.new_widget, b"size")
            scale_animation.setStartValue(QSize(1, 1))
            scale_animation.setEndValue(target_size)
            scale_animation.setDuration(config.duration_ms // 2)
            scale_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            phase2.addAnimation(scale_animation)
            
            # Fade in
            fade_in = QPropertyAnimation(self.new_effect, b"opacity")
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setDuration(config.duration_ms // 2)
            fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
            phase2.addAnimation(fade_in)
        
        animation_group.addAnimation(phase2)
        
        return animation_group
    
    def cleanup(self) -> None:
        """Clean up scale transition."""
        if self.old_widget:
            self.old_widget.setGraphicsEffect(None)
            self.old_widget.hide()
        
        if self.new_widget:
            self.new_widget.setGraphicsEffect(None)
        
        self.old_effect = None
        self.new_effect = None
        self.old_widget = None
        self.new_widget = None


class LayoutTransitionManager(BaseUIComponent):
    """Manages smooth transitions between layouts with animation support."""
    
    # Signals
    transition_started = pyqtSignal(str, str)  # from_layout_id, to_layout_id
    transition_progress = pyqtSignal(float)    # progress (0.0 to 1.0)
    transition_completed = pyqtSignal(str, str, float)  # from_id, to_id, duration_ms
    transition_failed = pyqtSignal(str, str, str)  # from_id, to_id, error_message
    state_preserved = pyqtSignal(str, int)     # layout_id, component_count
    
    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigurationManager,
        state_manager: Store,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        # Core properties
        self._current_state = TransitionState.IDLE
        self._active_animation: Optional[QPropertyAnimation] = None
        self._transition_effects: Dict[TransitionType, TransitionEffect] = {}
        self._preserved_states: Dict[str, List[ComponentState]] = {}
        
        # Configuration
        self._default_config = TransitionConfiguration()
        self._accessibility_enabled = True
        self._performance_monitoring = True
        
        # Metrics
        self._transition_metrics: List[TransitionMetrics] = []
        self._max_metrics_history = 100
        
        # Setup
        self._initialize_effects()
        self._setup_accessibility()
        
        logger.debug("LayoutTransitionManager initialized")
    
    def _setup_component(self) -> None:
        """Setup the transition manager."""
        # Subscribe to layout events
        self.subscribe_to_event("layout.before_switch", self._handle_before_switch)
        self.subscribe_to_event("layout.switch_request", self._handle_switch_request)
        self.subscribe_to_event("accessibility.reduce_motion", self._handle_reduce_motion)
        
        logger.info("Layout transition manager setup complete")
    
    def _initialize_effects(self) -> None:
        """Initialize available transition effects."""
        self._transition_effects = {
            TransitionType.FADE: FadeTransition(),
            TransitionType.SLIDE: SlideTransition(),
            TransitionType.SCALE: ScaleTransition(),
        }
    
    def _setup_accessibility(self) -> None:
        """Setup accessibility considerations."""
        # Check system preferences for reduced motion
        app = QApplication.instance()
        if app:
            # This would ideally check system accessibility settings
            # For now, we'll use a configuration-based approach
            self._accessibility_enabled = self.get_config(
                "accessibility.enable_transitions", True
            )
            
            reduce_motion = self.get_config(
                "accessibility.reduce_motion", False
            )
            
            if reduce_motion:
                self._default_config.transition_type = TransitionType.INSTANT
                self._default_config.duration_ms = 0
    
    async def transition_layout(
        self,
        from_widget: QWidget,
        to_widget: QWidget,
        from_layout_id: str,
        to_layout_id: str,
        config: Optional[TransitionConfiguration] = None
    ) -> bool:
        """Perform animated transition between layouts.
        
        Args:
            from_widget: Current layout widget
            to_widget: Target layout widget
            from_layout_id: ID of current layout
            to_layout_id: ID of target layout
            config: Transition configuration (uses default if None)
            
        Returns:
            True if transition completed successfully
        """
        if self._current_state != TransitionState.IDLE:
            logger.warning(f"Transition already in progress: {self._current_state}")
            return False
        
        try:
            self._current_state = TransitionState.PREPARING
            config = config or self._default_config
            
            # Start metrics collection
            metrics = TransitionMetrics(
                start_time=datetime.now(),
                target_duration_ms=config.duration_ms
            )
            
            # Emit start signal
            self.transition_started.emit(from_layout_id, to_layout_id)
            
            # Preserve component states
            if config.preserve_state:
                await self._preserve_component_states(from_widget, from_layout_id)
            
            # Handle accessibility
            if not self._accessibility_enabled or config.transition_type == TransitionType.INSTANT:
                return await self._instant_transition(
                    from_widget, to_widget, from_layout_id, to_layout_id, metrics
                )
            
            # Perform animated transition
            return await self._animated_transition(
                from_widget, to_widget, from_layout_id, to_layout_id, config, metrics
            )
            
        except Exception as e:
            error_msg = f"Transition failed: {e}"
            logger.error(error_msg)
            self.transition_failed.emit(from_layout_id, to_layout_id, error_msg)
            self._current_state = TransitionState.FAILED
            return False
    
    async def _instant_transition(
        self,
        from_widget: QWidget,
        to_widget: QWidget,
        from_layout_id: str,
        to_layout_id: str,
        metrics: TransitionMetrics
    ) -> bool:
        """Perform instant transition without animation."""
        self._current_state = TransitionState.COMPLETING
        
        # Hide old, show new
        from_widget.hide()
        to_widget.show()
        
        # Complete metrics
        metrics.end_time = datetime.now()
        metrics.actual_duration_ms = 0.0
        self._transition_metrics.append(metrics)
        
        # Emit completion
        self.transition_completed.emit(from_layout_id, to_layout_id, 0.0)
        self._current_state = TransitionState.IDLE
        
        logger.debug(f"Instant transition completed: {from_layout_id} -> {to_layout_id}")
        return True
    
    async def _animated_transition(
        self,
        from_widget: QWidget,
        to_widget: QWidget,
        from_layout_id: str,
        to_layout_id: str,
        config: TransitionConfiguration,
        metrics: TransitionMetrics
    ) -> bool:
        """Perform animated transition."""
        self._current_state = TransitionState.ANIMATING
        
        # Get transition effect
        effect = self._transition_effects.get(config.transition_type)
        if not effect:
            logger.warning(f"Unknown transition type: {config.transition_type}")
            return await self._instant_transition(
                from_widget, to_widget, from_layout_id, to_layout_id, metrics
            )
        
        try:
            # Prepare transition
            effect.prepare(from_widget, to_widget)
            
            # Create animation
            animation = effect.create_animation(config)
            if not animation:
                return await self._instant_transition(
                    from_widget, to_widget, from_layout_id, to_layout_id, metrics
                )
            
            # Setup animation completion
            animation_completed = False
            
            def on_animation_finished():
                nonlocal animation_completed
                animation_completed = True
            
            animation.finished.connect(on_animation_finished)
            
            # Track progress
            def on_animation_progress():
                if animation.state() == animation.State.Running:
                    progress = animation.currentTime() / animation.totalDuration()
                    self.transition_progress.emit(progress)
            
            # Setup progress tracking
            progress_timer = QTimer()
            progress_timer.timeout.connect(on_animation_progress)
            progress_timer.start(16)  # ~60fps
            
            # Start animation
            animation.start()
            
            # Wait for completion (with timeout)
            timeout_ms = config.duration_ms + 1000  # Add 1 second buffer
            elapsed = 0
            while not animation_completed and elapsed < timeout_ms:
                await asyncio.sleep(0.016)  # ~60fps
                elapsed += 16
                QApplication.processEvents()
            
            progress_timer.stop()
            
            # Complete transition
            self._current_state = TransitionState.COMPLETING
            effect.cleanup()
            
            # Finalize metrics
            metrics.end_time = datetime.now()
            duration = metrics.end_time - metrics.start_time
            metrics.actual_duration_ms = duration.total_seconds() * 1000
            self._transition_metrics.append(metrics)
            
            # Trim metrics history
            if len(self._transition_metrics) > self._max_metrics_history:
                self._transition_metrics = self._transition_metrics[-self._max_metrics_history:]
            
            # Emit completion
            self.transition_completed.emit(from_layout_id, to_layout_id, metrics.actual_duration_ms)
            self._current_state = TransitionState.IDLE
            
            logger.info(f"Animated transition completed: {from_layout_id} -> {to_layout_id} "
                       f"({metrics.actual_duration_ms:.1f}ms)")
            return True
            
        except Exception as e:
            effect.cleanup()
            self._current_state = TransitionState.FAILED
            raise e
    
    async def _preserve_component_states(self, widget: QWidget, layout_id: str) -> None:
        """Preserve state of components in the current layout."""
        states = []
        
        # Find all widgets with state to preserve
        widgets_to_preserve = self._find_stateful_widgets(widget)
        
        for widget_item in widgets_to_preserve:
            state = ComponentState(
                widget_id=widget_item.objectName() or f"widget_{id(widget_item)}",
                geometry=widget_item.geometry(),
                visibility=widget_item.isVisible(),
                opacity=1.0,  # Could extract from graphics effect if present
            )
            
            # Try to preserve scroll position
            if hasattr(widget_item, 'verticalScrollBar') and hasattr(widget_item, 'horizontalScrollBar'):
                state.scroll_position = QPoint(
                    widget_item.horizontalScrollBar().value(),
                    widget_item.verticalScrollBar().value()
                )
            
            # Add widget-specific state preservation
            if hasattr(widget_item, 'preserve_state'):
                state.custom_properties = widget_item.preserve_state()
            
            states.append(state)
        
        self._preserved_states[layout_id] = states
        self.state_preserved.emit(layout_id, len(states))
        
        logger.debug(f"Preserved state for {len(states)} components in layout {layout_id}")
    
    def _find_stateful_widgets(self, root_widget: QWidget) -> List[QWidget]:
        """Find widgets that should have their state preserved."""
        stateful_widgets = []
        
        # Add the root widget if it has state
        if self._widget_has_state(root_widget):
            stateful_widgets.append(root_widget)
        
        # Recursively find child widgets with state
        for child in root_widget.findChildren(QWidget):
            if self._widget_has_state(child):
                stateful_widgets.append(child)
        
        return stateful_widgets
    
    def _widget_has_state(self, widget: QWidget) -> bool:
        """Check if a widget has state worth preserving."""
        # Check for common stateful widget types
        from PyQt6.QtWidgets import (
            QScrollArea, QTextEdit, QPlainTextEdit, QLineEdit,
            QSpinBox, QDoubleSpinBox, QSlider, QTabWidget
        )
        
        stateful_types = (
            QScrollArea, QTextEdit, QPlainTextEdit, QLineEdit,
            QSpinBox, QDoubleSpinBox, QSlider, QTabWidget
        )
        
        return (isinstance(widget, stateful_types) or 
                hasattr(widget, 'preserve_state'))
    
    def restore_component_states(self, widget: QWidget, layout_id: str) -> bool:
        """Restore preserved component states to a layout.
        
        Args:
            widget: Root widget of the layout
            layout_id: ID of the layout to restore
            
        Returns:
            True if states were restored successfully
        """
        if layout_id not in self._preserved_states:
            logger.debug(f"No preserved states found for layout {layout_id}")
            return False
        
        states = self._preserved_states[layout_id]
        restored_count = 0
        
        for state in states:
            # Find the widget by ID
            target_widget = self._find_widget_by_id(widget, state.widget_id)
            if not target_widget:
                continue
            
            try:
                # Restore geometry
                target_widget.setGeometry(state.geometry)
                target_widget.setVisible(state.visibility)
                
                # Restore scroll position
                if state.scroll_position and hasattr(target_widget, 'verticalScrollBar'):
                    target_widget.horizontalScrollBar().setValue(state.scroll_position.x())
                    target_widget.verticalScrollBar().setValue(state.scroll_position.y())
                
                # Restore custom properties
                if state.custom_properties and hasattr(target_widget, 'restore_state'):
                    target_widget.restore_state(state.custom_properties)
                
                restored_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to restore state for widget {state.widget_id}: {e}")
        
        logger.info(f"Restored state for {restored_count}/{len(states)} components in layout {layout_id}")
        return restored_count > 0
    
    def _find_widget_by_id(self, root_widget: QWidget, widget_id: str) -> Optional[QWidget]:
        """Find a widget by its preserved ID."""
        # Check root widget
        if root_widget.objectName() == widget_id or f"widget_{id(root_widget)}" == widget_id:
            return root_widget
        
        # Search children
        for child in root_widget.findChildren(QWidget):
            if child.objectName() == widget_id or f"widget_{id(child)}" == widget_id:
                return child
        
        return None
    
    def interrupt_transition(self) -> bool:
        """Interrupt the current transition.
        
        Returns:
            True if a transition was interrupted
        """
        if self._current_state in (TransitionState.ANIMATING, TransitionState.PREPARING):
            self._current_state = TransitionState.INTERRUPTED
            
            if self._active_animation:
                self._active_animation.stop()
                self._active_animation = None
            
            logger.info("Layout transition interrupted")
            return True
        
        return False
    
    def get_transition_metrics(self) -> List[TransitionMetrics]:
        """Get performance metrics for recent transitions."""
        return self._transition_metrics.copy()
    
    def clear_preserved_states(self, layout_id: Optional[str] = None) -> None:
        """Clear preserved states for a layout or all layouts.
        
        Args:
            layout_id: Specific layout ID to clear, or None for all
        """
        if layout_id:
            self._preserved_states.pop(layout_id, None)
            logger.debug(f"Cleared preserved states for layout {layout_id}")
        else:
            self._preserved_states.clear()
            logger.debug("Cleared all preserved states")
    
    def set_default_configuration(self, config: TransitionConfiguration) -> None:
        """Set the default transition configuration."""
        self._default_config = config
        logger.debug(f"Updated default transition configuration: {config.transition_type.name}")
    
    def get_default_configuration(self) -> TransitionConfiguration:
        """Get the default transition configuration."""
        return self._default_config
    
    def get_current_state(self) -> TransitionState:
        """Get the current transition state."""
        return self._current_state
    
    # Event handlers
    def _handle_before_switch(self, event_data: Dict[str, Any]) -> None:
        """Handle before layout switch event."""
        from_layout_id = event_data.get("from_layout_id")
        if from_layout_id and self._current_state == TransitionState.IDLE:
            # Prepare for transition
            logger.debug(f"Preparing for layout switch from {from_layout_id}")
    
    def _handle_switch_request(self, event_data: Dict[str, Any]) -> None:
        """Handle layout switch request event."""
        # This would be implemented to coordinate with LayoutManager
        pass
    
    def _handle_reduce_motion(self, event_data: Dict[str, Any]) -> None:
        """Handle accessibility reduce motion setting change."""
        reduce_motion = event_data.get("enabled", False)
        if reduce_motion:
            self._default_config.transition_type = TransitionType.INSTANT
            self._default_config.duration_ms = 0
            logger.info("Reduced motion enabled - disabling transitions")
        else:
            self._default_config.transition_type = TransitionType.FADE
            self._default_config.duration_ms = 300
            logger.info("Reduced motion disabled - enabling transitions")