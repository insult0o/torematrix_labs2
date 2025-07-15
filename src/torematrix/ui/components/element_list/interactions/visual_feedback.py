"""
Visual Feedback System for Element Tree View

Provides animations, transitions, and visual effects for enhanced user experience.
"""

from typing import Dict, List, Optional, Any, Tuple
from PyQt6.QtCore import (QObject, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve, 
                         QParallelAnimationGroup, QSequentialAnimationGroup, QRect, QPoint)
from PyQt6.QtWidgets import QTreeView, QWidget, QGraphicsOpacityEffect
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QFontMetrics

from ..models.tree_node import TreeNode


class AnimationConfig:
    """Configuration for animations."""
    
    # Duration constants (ms)
    FAST = 150
    NORMAL = 250
    SLOW = 400
    
    # Easing curves
    EASE_IN_OUT = QEasingCurve.Type.InOutCubic
    EASE_OUT = QEasingCurve.Type.OutCubic
    EASE_IN = QEasingCurve.Type.InCubic
    BOUNCE = QEasingCurve.Type.OutBounce
    
    def __init__(self):
        self.enabled = True
        self.duration_multiplier = 1.0
        self.reduce_motion = False  # For accessibility
    
    def get_duration(self, base_duration: int) -> int:
        """Get adjusted duration based on config."""
        if not self.enabled or self.reduce_motion:
            return 0
        return int(base_duration * self.duration_multiplier)


class HighlightEffect:
    """Visual highlight effect for items."""
    
    def __init__(self, tree_view: QTreeView):
        self.tree_view = tree_view
        self.highlight_rect = QRect()
        self.highlight_color = QColor(255, 215, 0, 100)  # Gold with transparency
        self.border_color = QColor(255, 215, 0, 200)
        self.visible = False
        self.opacity = 0.0
        
        # Animation
        self.animation = QPropertyAnimation()
        self.animation.setTargetObject(self)
        self.animation.setPropertyName(b"opacity")
        self.animation.valueChanged.connect(self._update_view)
        self.animation.finished.connect(self._animation_finished)
    
    def show_highlight(self, rect: QRect, duration: int = 500) -> None:
        """Show highlight effect."""
        self.highlight_rect = rect
        self.visible = True
        
        # Animate opacity
        self.animation.stop()
        self.animation.setDuration(duration)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.start()
    
    def hide_highlight(self, duration: int = 300) -> None:
        """Hide highlight effect."""
        if not self.visible:
            return
        
        self.animation.stop()
        self.animation.setDuration(duration)
        self.animation.setStartValue(self.opacity)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.animation.start()
    
    def paint(self, painter: QPainter) -> None:
        """Paint the highlight effect."""
        if not self.visible or self.opacity <= 0:
            return
        
        painter.save()
        
        # Draw highlight
        color = QColor(self.highlight_color)
        color.setAlpha(int(self.highlight_color.alpha() * self.opacity))
        painter.fillRect(self.highlight_rect, color)
        
        # Draw border
        border_color = QColor(self.border_color)
        border_color.setAlpha(int(self.border_color.alpha() * self.opacity))
        painter.setPen(QPen(border_color, 2))
        painter.drawRect(self.highlight_rect)
        
        painter.restore()
    
    def _update_view(self) -> None:
        """Update view when animation changes."""
        self.tree_view.viewport().update(self.highlight_rect)
    
    def _animation_finished(self) -> None:
        """Handle animation completion."""
        if self.opacity <= 0:
            self.visible = False
    
    # Property for animation
    def get_opacity(self) -> float:
        return self.opacity
    
    def set_opacity(self, value: float) -> None:
        self.opacity = value
        self._update_view()
    
    opacity = property(get_opacity, set_opacity)


class PulseEffect:
    """Pulsing animation effect."""
    
    def __init__(self, tree_view: QTreeView):
        self.tree_view = tree_view
        self.target_rect = QRect()
        self.base_color = QColor(0, 120, 215, 80)
        self.pulse_scale = 1.0
        self.visible = False
        
        # Animation group
        self.animation_group = QSequentialAnimationGroup()
        
        # Scale up animation
        self.scale_up = QPropertyAnimation()
        self.scale_up.setTargetObject(self)
        self.scale_up.setPropertyName(b"pulse_scale")
        self.scale_up.setDuration(600)
        self.scale_up.setStartValue(1.0)
        self.scale_up.setEndValue(1.2)
        self.scale_up.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        # Scale down animation
        self.scale_down = QPropertyAnimation()
        self.scale_down.setTargetObject(self)
        self.scale_down.setPropertyName(b"pulse_scale")
        self.scale_down.setDuration(600)
        self.scale_down.setStartValue(1.2)
        self.scale_down.setEndValue(1.0)
        self.scale_down.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        # Setup animation group
        self.animation_group.addAnimation(self.scale_up)
        self.animation_group.addAnimation(self.scale_down)
        self.animation_group.setLoopCount(-1)  # Infinite loop
        
        # Connect signals
        self.scale_up.valueChanged.connect(self._update_view)
        self.scale_down.valueChanged.connect(self._update_view)
    
    def start_pulse(self, rect: QRect, color: Optional[QColor] = None) -> None:
        """Start pulsing effect."""
        self.target_rect = rect
        if color:
            self.base_color = color
        self.visible = True
        self.animation_group.start()
    
    def stop_pulse(self) -> None:
        """Stop pulsing effect."""
        self.animation_group.stop()
        self.visible = False
        self.pulse_scale = 1.0
        self._update_view()
    
    def paint(self, painter: QPainter) -> None:
        """Paint the pulse effect."""
        if not self.visible:
            return
        
        painter.save()
        
        # Calculate scaled rect
        center = self.target_rect.center()
        scaled_width = int(self.target_rect.width() * self.pulse_scale)
        scaled_height = int(self.target_rect.height() * self.pulse_scale)
        scaled_rect = QRect(
            center.x() - scaled_width // 2,
            center.y() - scaled_height // 2,
            scaled_width,
            scaled_height
        )
        
        # Draw pulse
        painter.fillRect(scaled_rect, self.base_color)
        
        painter.restore()
    
    def _update_view(self) -> None:
        """Update view when animation changes."""
        # Update larger area to account for scaling
        update_rect = self.target_rect.adjusted(-20, -20, 20, 20)
        self.tree_view.viewport().update(update_rect)
    
    # Property for animation
    def get_pulse_scale(self) -> float:
        return self.pulse_scale
    
    def set_pulse_scale(self, value: float) -> None:
        self.pulse_scale = value
    
    pulse_scale = property(get_pulse_scale, set_pulse_scale)


class FlashEffect:
    """Quick flash animation for notifications."""
    
    def __init__(self, tree_view: QTreeView):
        self.tree_view = tree_view
        self.flash_rect = QRect()
        self.flash_color = QColor(255, 255, 255, 200)
        self.visible = False
        self.flash_opacity = 0.0
        
        # Animation
        self.animation = QSequentialAnimationGroup()
        
        # Flash on
        self.flash_on = QPropertyAnimation()
        self.flash_on.setTargetObject(self)
        self.flash_on.setPropertyName(b"flash_opacity")
        self.flash_on.setDuration(100)
        self.flash_on.setStartValue(0.0)
        self.flash_on.setEndValue(1.0)
        self.flash_on.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Flash off
        self.flash_off = QPropertyAnimation()
        self.flash_off.setTargetObject(self)
        self.flash_off.setPropertyName(b"flash_opacity")
        self.flash_off.setDuration(200)
        self.flash_off.setStartValue(1.0)
        self.flash_off.setEndValue(0.0)
        self.flash_off.setEasingCurve(QEasingCurve.Type.InCubic)
        
        # Setup group
        self.animation.addAnimation(self.flash_on)
        self.animation.addAnimation(self.flash_off)
        self.animation.finished.connect(self._flash_finished)
        
        # Connect updates
        self.flash_on.valueChanged.connect(self._update_view)
        self.flash_off.valueChanged.connect(self._update_view)
    
    def flash(self, rect: QRect, color: Optional[QColor] = None) -> None:
        """Trigger flash effect."""
        self.flash_rect = rect
        if color:
            self.flash_color = color
        self.visible = True
        self.animation.start()
    
    def paint(self, painter: QPainter) -> None:
        """Paint the flash effect."""
        if not self.visible or self.flash_opacity <= 0:
            return
        
        painter.save()
        
        # Draw flash
        color = QColor(self.flash_color)
        color.setAlpha(int(self.flash_color.alpha() * self.flash_opacity))
        painter.fillRect(self.flash_rect, color)
        
        painter.restore()
    
    def _update_view(self) -> None:
        """Update view when animation changes."""
        self.tree_view.viewport().update(self.flash_rect)
    
    def _flash_finished(self) -> None:
        """Handle flash completion."""
        self.visible = False
    
    # Property for animation
    def get_flash_opacity(self) -> float:
        return self.flash_opacity
    
    def set_flash_opacity(self, value: float) -> None:
        self.flash_opacity = value
    
    flash_opacity = property(get_flash_opacity, set_flash_opacity)


class LoadingIndicator:
    """Loading spinner animation."""
    
    def __init__(self, tree_view: QTreeView):
        self.tree_view = tree_view
        self.center_point = QPoint()
        self.radius = 20
        self.rotation = 0.0
        self.visible = False
        
        # Animation
        self.animation = QPropertyAnimation()
        self.animation.setTargetObject(self)
        self.animation.setPropertyName(b"rotation")
        self.animation.setDuration(1000)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(360.0)
        self.animation.setLoopCount(-1)
        self.animation.setEasingCurve(QEasingCurve.Type.Linear)
        self.animation.valueChanged.connect(self._update_view)
    
    def show_loading(self, center: QPoint) -> None:
        """Show loading indicator."""
        self.center_point = center
        self.visible = True
        self.animation.start()
    
    def hide_loading(self) -> None:
        """Hide loading indicator."""
        self.animation.stop()
        self.visible = False
        self._update_view()
    
    def paint(self, painter: QPainter) -> None:
        """Paint the loading indicator."""
        if not self.visible:
            return
        
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw spinning dots
        num_dots = 8
        dot_radius = 3
        
        for i in range(num_dots):
            angle = (self.rotation + i * 45) * 3.14159 / 180
            
            # Calculate dot position
            x = self.center_point.x() + self.radius * float(self.cos(angle))
            y = self.center_point.y() + self.radius * float(self.sin(angle))
            
            # Fade dots based on position
            alpha = int(255 * (i + 1) / num_dots)
            color = QColor(100, 100, 100, alpha)
            
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color))
            painter.drawEllipse(int(x - dot_radius), int(y - dot_radius), 
                              dot_radius * 2, dot_radius * 2)
        
        painter.restore()
    
    @staticmethod
    def cos(angle_degrees: float) -> float:
        """Cosine function for degrees."""
        import math
        return math.cos(math.radians(angle_degrees))
    
    @staticmethod
    def sin(angle_degrees: float) -> float:
        """Sine function for degrees."""
        import math
        return math.sin(math.radians(angle_degrees))
    
    def _update_view(self) -> None:
        """Update view when animation changes."""
        update_rect = QRect(
            self.center_point.x() - self.radius - 10,
            self.center_point.y() - self.radius - 10,
            (self.radius + 10) * 2,
            (self.radius + 10) * 2
        )
        self.tree_view.viewport().update(update_rect)
    
    # Property for animation
    def get_rotation(self) -> float:
        return self.rotation
    
    def set_rotation(self, value: float) -> None:
        self.rotation = value % 360.0
    
    rotation = property(get_rotation, set_rotation)


class ProgressIndicator:
    """Progress bar animation for operations."""
    
    def __init__(self, tree_view: QTreeView):
        self.tree_view = tree_view
        self.progress_rect = QRect()
        self.progress = 0.0
        self.visible = False
        self.background_color = QColor(230, 230, 230)
        self.progress_color = QColor(0, 120, 215)
        self.text = ""
        
        # Animation for smooth progress updates
        self.animation = QPropertyAnimation()
        self.animation.setTargetObject(self)
        self.animation.setPropertyName(b"progress")
        self.animation.valueChanged.connect(self._update_view)
    
    def show_progress(self, rect: QRect, text: str = "") -> None:
        """Show progress indicator."""
        self.progress_rect = rect
        self.text = text
        self.visible = True
        self.progress = 0.0
        self._update_view()
    
    def update_progress(self, value: float, animated: bool = True) -> None:
        """Update progress value."""
        if not self.visible:
            return
        
        value = max(0.0, min(1.0, value))
        
        if animated:
            self.animation.stop()
            self.animation.setDuration(200)
            self.animation.setStartValue(self.progress)
            self.animation.setEndValue(value)
            self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.animation.start()
        else:
            self.progress = value
            self._update_view()
    
    def hide_progress(self) -> None:
        """Hide progress indicator."""
        self.animation.stop()
        self.visible = False
        self._update_view()
    
    def paint(self, painter: QPainter) -> None:
        """Paint the progress indicator."""
        if not self.visible:
            return
        
        painter.save()
        
        # Draw background
        painter.fillRect(self.progress_rect, self.background_color)
        
        # Draw progress
        progress_width = int(self.progress_rect.width() * self.progress)
        progress_fill_rect = QRect(
            self.progress_rect.left(),
            self.progress_rect.top(),
            progress_width,
            self.progress_rect.height()
        )
        painter.fillRect(progress_fill_rect, self.progress_color)
        
        # Draw border
        painter.setPen(QPen(QColor(180, 180, 180), 1))
        painter.drawRect(self.progress_rect)
        
        # Draw text
        if self.text:
            painter.setPen(QPen(QColor(50, 50, 50)))
            font = painter.font()
            font.setPointSize(8)
            painter.setFont(font)
            painter.drawText(self.progress_rect, Qt.AlignmentFlag.AlignCenter, self.text)
        
        painter.restore()
    
    def _update_view(self) -> None:
        """Update view when progress changes."""
        self.tree_view.viewport().update(self.progress_rect)
    
    # Property for animation
    def get_progress(self) -> float:
        return self.progress
    
    def set_progress(self, value: float) -> None:
        self.progress = max(0.0, min(1.0, value))
    
    progress = property(get_progress, set_progress)


class TooltipAnimation:
    """Animated tooltip display."""
    
    def __init__(self, tree_view: QTreeView):
        self.tree_view = tree_view
        self.tooltip_rect = QRect()
        self.tooltip_text = ""
        self.visible = False
        self.opacity = 0.0
        self.background_color = QColor(255, 255, 220)
        self.border_color = QColor(120, 120, 120)
        self.text_color = QColor(50, 50, 50)
        
        # Animation
        self.fade_animation = QPropertyAnimation()
        self.fade_animation.setTargetObject(self)
        self.fade_animation.setPropertyName(b"opacity")
        self.fade_animation.valueChanged.connect(self._update_view)
        self.fade_animation.finished.connect(self._animation_finished)
        
        # Hide timer
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.hide_tooltip)
    
    def show_tooltip(self, point: QPoint, text: str, duration: int = 3000) -> None:
        """Show animated tooltip."""
        if not text:
            return
        
        self.tooltip_text = text
        
        # Calculate tooltip rect
        font = QFont()
        metrics = QFontMetrics(font)
        text_rect = metrics.boundingRect(text)
        
        padding = 8
        self.tooltip_rect = QRect(
            point.x(),
            point.y() - text_rect.height() - padding * 2 - 5,
            text_rect.width() + padding * 2,
            text_rect.height() + padding * 2
        )
        
        # Ensure tooltip stays within view
        view_rect = self.tree_view.viewport().rect()
        if self.tooltip_rect.right() > view_rect.right():
            self.tooltip_rect.moveRight(view_rect.right() - 5)
        if self.tooltip_rect.left() < view_rect.left():
            self.tooltip_rect.moveLeft(view_rect.left() + 5)
        if self.tooltip_rect.top() < view_rect.top():
            self.tooltip_rect.moveTop(point.y() + 5)
        
        self.visible = True
        
        # Animate in
        self.fade_animation.stop()
        self.fade_animation.setDuration(200)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.start()
        
        # Set hide timer
        if duration > 0:
            self.hide_timer.start(duration)
    
    def hide_tooltip(self) -> None:
        """Hide tooltip with animation."""
        if not self.visible:
            return
        
        self.hide_timer.stop()
        
        self.fade_animation.stop()
        self.fade_animation.setDuration(150)
        self.fade_animation.setStartValue(self.opacity)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_animation.start()
    
    def paint(self, painter: QPainter) -> None:
        """Paint the tooltip."""
        if not self.visible or self.opacity <= 0:
            return
        
        painter.save()
        
        # Set opacity
        painter.setOpacity(self.opacity)
        
        # Draw background
        bg_color = QColor(self.background_color)
        painter.fillRect(self.tooltip_rect, bg_color)
        
        # Draw border
        painter.setPen(QPen(self.border_color, 1))
        painter.drawRect(self.tooltip_rect)
        
        # Draw text
        painter.setPen(QPen(self.text_color))
        painter.drawText(self.tooltip_rect, Qt.AlignmentFlag.AlignCenter, self.tooltip_text)
        
        painter.restore()
    
    def _update_view(self) -> None:
        """Update view when animation changes."""
        self.tree_view.viewport().update(self.tooltip_rect)
    
    def _animation_finished(self) -> None:
        """Handle animation completion."""
        if self.opacity <= 0:
            self.visible = False
    
    # Property for animation
    def get_opacity(self) -> float:
        return self.opacity
    
    def set_opacity(self, value: float) -> None:
        self.opacity = value
    
    opacity = property(get_opacity, set_opacity)


class VisualFeedbackManager(QObject):
    """Manages all visual feedback effects for the tree view."""
    
    # Signals
    effectStarted = pyqtSignal(str)  # effect_name
    effectFinished = pyqtSignal(str)  # effect_name
    
    def __init__(self, tree_view: QTreeView, parent=None):
        super().__init__(parent)
        self.tree_view = tree_view
        self.config = AnimationConfig()
        
        # Effects
        self.highlight = HighlightEffect(tree_view)
        self.pulse = PulseEffect(tree_view)
        self.flash = FlashEffect(tree_view)
        self.loading = LoadingIndicator(tree_view)
        self.progress = ProgressIndicator(tree_view)
        self.tooltip = TooltipAnimation(tree_view)
        
        # Install paint event handler
        self.tree_view.viewport().installEventFilter(self)
    
    def eventFilter(self, obj, event) -> bool:
        """Filter paint events to draw effects."""
        if obj == self.tree_view.viewport() and event.type() == event.Type.Paint:
            # Let Qt handle the normal painting first
            result = super().eventFilter(obj, event)
            
            # Then draw our effects on top
            painter = QPainter(self.tree_view.viewport())
            self._paint_all_effects(painter)
            painter.end()
            
            return result
        
        return super().eventFilter(obj, event)
    
    def _paint_all_effects(self, painter: QPainter) -> None:
        """Paint all active effects."""
        # Paint in layered order
        self.highlight.paint(painter)
        self.pulse.paint(painter)
        self.flash.paint(painter)
        self.progress.paint(painter)
        self.loading.paint(painter)
        self.tooltip.paint(painter)  # Tooltip on top
    
    # Effect control methods
    
    def show_item_highlight(self, index, duration: int = 500) -> None:
        """Highlight an item."""
        rect = self.tree_view.visualRect(index)
        if not rect.isEmpty():
            duration = self.config.get_duration(duration)
            self.highlight.show_highlight(rect, duration)
            self.effectStarted.emit("highlight")
    
    def show_item_pulse(self, index, color: Optional[QColor] = None) -> None:
        """Start pulsing an item."""
        rect = self.tree_view.visualRect(index)
        if not rect.isEmpty():
            self.pulse.start_pulse(rect, color)
            self.effectStarted.emit("pulse")
    
    def stop_item_pulse(self) -> None:
        """Stop pulsing effect."""
        self.pulse.stop_pulse()
        self.effectFinished.emit("pulse")
    
    def flash_item(self, index, color: Optional[QColor] = None) -> None:
        """Flash an item."""
        rect = self.tree_view.visualRect(index)
        if not rect.isEmpty():
            self.flash.flash(rect, color)
            self.effectStarted.emit("flash")
    
    def show_loading(self, center: Optional[QPoint] = None) -> None:
        """Show loading indicator."""
        if center is None:
            center = self.tree_view.viewport().rect().center()
        self.loading.show_loading(center)
        self.effectStarted.emit("loading")
    
    def hide_loading(self) -> None:
        """Hide loading indicator."""
        self.loading.hide_loading()
        self.effectFinished.emit("loading")
    
    def show_progress(self, rect: QRect, text: str = "") -> None:
        """Show progress indicator."""
        self.progress.show_progress(rect, text)
        self.effectStarted.emit("progress")
    
    def update_progress(self, value: float, animated: bool = True) -> None:
        """Update progress value."""
        self.progress.update_progress(value, animated)
    
    def hide_progress(self) -> None:
        """Hide progress indicator."""
        self.progress.hide_progress()
        self.effectFinished.emit("progress")
    
    def show_tooltip(self, point: QPoint, text: str, duration: int = 3000) -> None:
        """Show animated tooltip."""
        self.tooltip.show_tooltip(point, text, duration)
        self.effectStarted.emit("tooltip")
    
    def hide_tooltip(self) -> None:
        """Hide tooltip."""
        self.tooltip.hide_tooltip()
        self.effectFinished.emit("tooltip")
    
    # Convenience methods for common scenarios
    
    def indicate_selection_change(self, index) -> None:
        """Visual feedback for selection change."""
        self.flash_item(index, QColor(0, 120, 215, 100))
    
    def indicate_item_added(self, index) -> None:
        """Visual feedback for item addition."""
        self.flash_item(index, QColor(50, 150, 50, 100))
    
    def indicate_item_removed(self, rect: QRect) -> None:
        """Visual feedback for item removal."""
        self.flash.flash(rect, QColor(200, 50, 50, 100))
    
    def indicate_item_modified(self, index) -> None:
        """Visual feedback for item modification."""
        self.flash_item(index, QColor(255, 165, 0, 100))
    
    def indicate_search_match(self, index) -> None:
        """Visual feedback for search match."""
        self.show_item_highlight(index, 1000)
    
    def indicate_drag_target(self, index) -> None:
        """Visual feedback for drag target."""
        self.show_item_pulse(index, QColor(0, 120, 215, 80))
    
    def clear_drag_target(self) -> None:
        """Clear drag target indication."""
        self.stop_item_pulse()
    
    def indicate_error(self, index) -> None:
        """Visual feedback for error."""
        self.show_item_pulse(index, QColor(200, 50, 50, 100))
    
    def indicate_success(self, index) -> None:
        """Visual feedback for success."""
        self.flash_item(index, QColor(50, 150, 50, 120))
    
    # Configuration
    
    def set_animations_enabled(self, enabled: bool) -> None:
        """Enable/disable animations."""
        self.config.enabled = enabled
    
    def set_animation_speed(self, multiplier: float) -> None:
        """Set animation speed multiplier."""
        self.config.duration_multiplier = multiplier
    
    def set_reduce_motion(self, reduce: bool) -> None:
        """Enable reduced motion for accessibility."""
        self.config.reduce_motion = reduce
    
    def get_config(self) -> AnimationConfig:
        """Get animation configuration."""
        return self.config