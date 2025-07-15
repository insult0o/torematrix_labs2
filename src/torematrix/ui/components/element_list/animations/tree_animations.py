"""
Tree Animations for Hierarchical Element List

Provides smooth animations for tree operations including expand/collapse,
selection feedback, and visual transitions.
"""

import logging
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, QPropertyAnimation, QEasingCurve, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class TreeAnimationManager(QObject):
    """
    Animation manager for tree operations
    
    Provides smooth animations for expand/collapse operations,
    selection feedback, and other visual transitions.
    """
    
    # Signals
    animation_started = pyqtSignal(str, str)  # element_id, animation_type
    animation_finished = pyqtSignal(str, str)  # element_id, animation_type
    
    def __init__(self, element_list_widget: QWidget, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        self.element_list = element_list_widget
        self.enable_animations = True
        self.animation_duration = 250  # ms
        
        # Active animations
        self._active_animations: Dict[str, QPropertyAnimation] = {}
        
        logger.info("TreeAnimationManager initialized")
    
    def animate_expand(self, element_id: str, widget: QWidget) -> None:
        """Animate element expansion"""
        if not self.enable_animations:
            return
        
        animation = QPropertyAnimation(widget, b"maximumHeight")
        animation.setDuration(self.animation_duration)
        animation.setStartValue(0)
        animation.setEndValue(widget.sizeHint().height())
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        animation.finished.connect(lambda: self._on_animation_finished(element_id, "expand"))
        
        self._active_animations[f"{element_id}_expand"] = animation
        animation.start()
        
        self.animation_started.emit(element_id, "expand")
    
    def animate_collapse(self, element_id: str, widget: QWidget) -> None:
        """Animate element collapse"""
        if not self.enable_animations:
            return
        
        animation = QPropertyAnimation(widget, b"maximumHeight")
        animation.setDuration(self.animation_duration)
        animation.setStartValue(widget.height())
        animation.setEndValue(0)
        animation.setEasingCurve(QEasingCurve.Type.InCubic)
        
        animation.finished.connect(lambda: self._on_animation_finished(element_id, "collapse"))
        
        self._active_animations[f"{element_id}_collapse"] = animation
        animation.start()
        
        self.animation_started.emit(element_id, "collapse")
    
    def _on_animation_finished(self, element_id: str, animation_type: str):
        """Handle animation completion"""
        animation_key = f"{element_id}_{animation_type}"
        if animation_key in self._active_animations:
            del self._active_animations[animation_key]
        
        self.animation_finished.emit(element_id, animation_type)