"""Responsive layout system for ToreMatrix V3.

This module provides adaptive layout management with breakpoints,
responsive behavior, and dynamic sizing for modern UI experiences.
"""

from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from enum import Enum
from dataclasses import dataclass
import logging

from PyQt6.QtWidgets import (
    QWidget, QLayout, QLayoutItem, QSizePolicy, QApplication,
    QVBoxLayout, QHBoxLayout, QGridLayout, QSplitter, QScrollArea
)
from PyQt6.QtCore import QObject, QSize, QRect, QTimer, pyqtSignal, QMargins
from PyQt6.QtGui import QResizeEvent

from ..core.events import EventBus
from ..core.config import ConfigManager
from ..core.state import StateManager
from .base import BaseUIComponent

logger = logging.getLogger(__name__)


class ScreenSize(Enum):
    """Screen size categories for responsive design."""
    EXTRA_SMALL = "xs"  # < 576px
    SMALL = "sm"        # >= 576px
    MEDIUM = "md"       # >= 768px
    LARGE = "lg"        # >= 992px
    EXTRA_LARGE = "xl"  # >= 1200px
    EXTRA_EXTRA_LARGE = "xxl"  # >= 1400px


@dataclass
class Breakpoint:
    """Responsive breakpoint definition."""
    name: str
    min_width: int
    max_width: Optional[int] = None


@dataclass
class ResponsiveRule:
    """Rule for responsive behavior."""
    screen_sizes: List[ScreenSize]
    visible: bool = True
    size_policy: Optional[QSizePolicy] = None
    minimum_size: Optional[QSize] = None
    maximum_size: Optional[QSize] = None
    stretch: Optional[int] = None
    margin: Optional[QMargins] = None
    custom_handler: Optional[Callable[['ResponsiveWidget', ScreenSize], None]] = None


class ResponsiveWidget(QWidget):
    """Widget with responsive behavior."""
    
    size_changed = pyqtSignal(ScreenSize)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._responsive_rules: Dict[ScreenSize, ResponsiveRule] = {}
        self._current_screen_size: ScreenSize = ScreenSize.MEDIUM
        self._breakpoints = self._get_default_breakpoints()
        
    def _get_default_breakpoints(self) -> Dict[ScreenSize, Breakpoint]:
        """Get default responsive breakpoints."""
        return {
            ScreenSize.EXTRA_SMALL: Breakpoint("xs", 0, 575),
            ScreenSize.SMALL: Breakpoint("sm", 576, 767),
            ScreenSize.MEDIUM: Breakpoint("md", 768, 991),
            ScreenSize.LARGE: Breakpoint("lg", 992, 1199),
            ScreenSize.EXTRA_LARGE: Breakpoint("xl", 1200, 1399),
            ScreenSize.EXTRA_EXTRA_LARGE: Breakpoint("xxl", 1400, None)
        }
    
    def add_responsive_rule(self, screen_size: ScreenSize, rule: ResponsiveRule) -> None:
        """Add responsive rule for a screen size."""
        self._responsive_rules[screen_size] = rule
    
    def set_responsive_rules(self, rules: Dict[ScreenSize, ResponsiveRule]) -> None:
        """Set multiple responsive rules at once."""
        self._responsive_rules = rules.copy()
    
    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handle resize event and apply responsive rules."""
        super().resizeEvent(event)
        self._update_responsive_behavior(event.size().width())
    
    def _update_responsive_behavior(self, width: int) -> None:
        """Update widget behavior based on width."""
        new_screen_size = self._determine_screen_size(width)
        
        if new_screen_size != self._current_screen_size:
            self._current_screen_size = new_screen_size
            self._apply_responsive_rule(new_screen_size)
            self.size_changed.emit(new_screen_size)
    
    def _determine_screen_size(self, width: int) -> ScreenSize:
        """Determine screen size category from width."""
        for screen_size, breakpoint in self._breakpoints.items():
            if width >= breakpoint.min_width:
                if breakpoint.max_width is None or width <= breakpoint.max_width:
                    return screen_size
        
        return ScreenSize.EXTRA_SMALL
    
    def _apply_responsive_rule(self, screen_size: ScreenSize) -> None:
        """Apply responsive rule for current screen size."""
        if screen_size not in self._responsive_rules:
            return
        
        rule = self._responsive_rules[screen_size]
        
        # Apply visibility
        self.setVisible(rule.visible)
        
        # Apply size policy
        if rule.size_policy:
            self.setSizePolicy(rule.size_policy)
        
        # Apply size constraints
        if rule.minimum_size:
            self.setMinimumSize(rule.minimum_size)
        
        if rule.maximum_size:
            self.setMaximumSize(rule.maximum_size)
        
        # Apply margins (if parent layout supports it)
        if rule.margin and self.parent():
            layout = self.parent().layout()
            if layout:
                layout.setContentsMargins(rule.margin)
        
        # Apply custom handler
        if rule.custom_handler:
            try:
                rule.custom_handler(self, screen_size)
            except Exception as e:
                logger.error(f"Error in custom responsive handler: {e}")
    
    def get_current_screen_size(self) -> ScreenSize:
        """Get current screen size category."""
        return self._current_screen_size


class ResponsiveLayout(BaseUIComponent):
    """Adaptive layout management with breakpoints and responsive behavior."""
    
    # Signals
    layout_changed = pyqtSignal(ScreenSize)
    widget_adapted = pyqtSignal(QWidget, ScreenSize)
    
    def __init__(
        self,
        container: QWidget,
        event_bus: EventBus,
        config_manager: ConfigManager,
        state_manager: StateManager,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        self._container = container
        self._responsive_widgets: List[ResponsiveWidget] = []
        self._current_screen_size: ScreenSize = ScreenSize.MEDIUM
        self._custom_breakpoints: Dict[ScreenSize, Breakpoint] = {}
        
        # Layout adaptation settings
        self._adaptation_enabled = True
        self._adaptation_delay = 100  # milliseconds
        self._adaptation_timer: Optional[QTimer] = None
        
        # Screen monitoring
        self._monitor_screen_changes()
    
    def _setup_component(self) -> None:
        """Setup the responsive layout system."""
        self._setup_adaptation_timer()
        self._initial_layout_check()
        
        logger.info("Responsive layout system initialized")
    
    def _setup_adaptation_timer(self) -> None:
        """Setup timer for delayed layout adaptation."""
        self._adaptation_timer = QTimer(self)
        self._adaptation_timer.setSingleShot(True)
        self._adaptation_timer.timeout.connect(self._perform_layout_adaptation)
    
    def _monitor_screen_changes(self) -> None:
        """Monitor screen and window changes."""
        if self._container:
            self._container.resizeEvent = self._handle_container_resize
    
    def _handle_container_resize(self, event: QResizeEvent) -> None:
        """Handle container resize event."""
        # Call original resize event if it exists
        if hasattr(self._container.__class__, 'resizeEvent'):
            try:
                super(self._container.__class__, self._container).resizeEvent(event)
            except AttributeError:
                pass
        
        # Schedule layout adaptation
        if self._adaptation_enabled and self._adaptation_timer:
            self._adaptation_timer.start(self._adaptation_delay)
    
    def _initial_layout_check(self) -> None:
        """Perform initial layout check."""
        if self._container:
            width = self._container.width()
            self._update_layout_for_width(width)
    
    def set_breakpoints(self, breakpoints: Dict[ScreenSize, Breakpoint]) -> None:
        """Set custom breakpoints."""
        self._custom_breakpoints = breakpoints.copy()
        
        # Update all responsive widgets
        for widget in self._responsive_widgets:
            if hasattr(widget, '_breakpoints'):
                widget._breakpoints = breakpoints
    
    def add_responsive_widget(
        self,
        widget: QWidget,
        rules: Dict[ScreenSize, ResponsiveRule]
    ) -> ResponsiveWidget:
        """Add widget with responsive behavior."""
        # Convert to ResponsiveWidget if needed
        if not isinstance(widget, ResponsiveWidget):
            responsive_widget = ResponsiveWidget(widget.parent())
            
            # Copy widget properties
            responsive_widget.setObjectName(widget.objectName())
            responsive_widget.setVisible(widget.isVisible())
            responsive_widget.setSizePolicy(widget.sizePolicy())
            
            # Replace widget in layout
            parent = widget.parent()
            if parent and parent.layout():
                layout = parent.layout()
                index = layout.indexOf(widget)
                if index >= 0:
                    layout.removeWidget(widget)
                    layout.insertWidget(index, responsive_widget)
                    widget.setParent(responsive_widget)
                    
                    # Create layout for the responsive widget
                    container_layout = QVBoxLayout(responsive_widget)
                    container_layout.setContentsMargins(0, 0, 0, 0)
                    container_layout.addWidget(widget)
            
            widget = responsive_widget
        
        # Set responsive rules
        widget.set_responsive_rules(rules)
        
        # Apply custom breakpoints if set
        if self._custom_breakpoints:
            widget._breakpoints = self._custom_breakpoints
        
        # Connect signals
        widget.size_changed.connect(lambda size: self.widget_adapted.emit(widget, size))
        
        # Add to tracking list
        self._responsive_widgets.append(widget)
        
        # Apply current layout state
        widget._update_responsive_behavior(self._container.width() if self._container else 800)
        
        return widget
    
    def remove_responsive_widget(self, widget: ResponsiveWidget) -> None:
        """Remove responsive widget from management."""
        if widget in self._responsive_widgets:
            self._responsive_widgets.remove(widget)
            widget.size_changed.disconnect()
    
    def update_layout(self, size: QSize) -> None:
        """Update layout for specific size."""
        self._update_layout_for_width(size.width())
    
    def _update_layout_for_width(self, width: int) -> None:
        """Update layout based on container width."""
        new_screen_size = self._determine_screen_size(width)
        
        if new_screen_size != self._current_screen_size:
            self._current_screen_size = new_screen_size
            self.layout_changed.emit(new_screen_size)
            
            # Publish event
            self.publish_event("layout.size_changed", {
                "screen_size": new_screen_size.value,
                "width": width
            })
    
    def _determine_screen_size(self, width: int) -> ScreenSize:
        """Determine screen size from width."""
        breakpoints = self._custom_breakpoints or self._get_default_breakpoints()
        
        # Sort breakpoints by min_width in descending order
        sorted_breakpoints = sorted(
            breakpoints.items(),
            key=lambda x: x[1].min_width,
            reverse=True
        )
        
        for screen_size, breakpoint in sorted_breakpoints:
            if width >= breakpoint.min_width:
                if breakpoint.max_width is None or width <= breakpoint.max_width:
                    return screen_size
        
        return ScreenSize.EXTRA_SMALL
    
    def _get_default_breakpoints(self) -> Dict[ScreenSize, Breakpoint]:
        """Get default responsive breakpoints."""
        return {
            ScreenSize.EXTRA_SMALL: Breakpoint("xs", 0, 575),
            ScreenSize.SMALL: Breakpoint("sm", 576, 767),
            ScreenSize.MEDIUM: Breakpoint("md", 768, 991),
            ScreenSize.LARGE: Breakpoint("lg", 992, 1199),
            ScreenSize.EXTRA_LARGE: Breakpoint("xl", 1200, 1399),
            ScreenSize.EXTRA_EXTRA_LARGE: Breakpoint("xxl", 1400, None)
        }
    
    def _perform_layout_adaptation(self) -> None:
        """Perform actual layout adaptation."""
        if not self._container:
            return
        
        width = self._container.width()
        self._update_layout_for_width(width)
        
        # Update all responsive widgets
        for widget in self._responsive_widgets:
            widget._update_responsive_behavior(width)
    
    def optimize_for_screen_size(self, screen_size: Optional[ScreenSize] = None) -> None:
        """Optimize layout for specific screen size."""
        target_size = screen_size or self._current_screen_size
        
        # Apply optimizations based on screen size
        if target_size in [ScreenSize.EXTRA_SMALL, ScreenSize.SMALL]:
            self._optimize_for_mobile()
        elif target_size == ScreenSize.MEDIUM:
            self._optimize_for_tablet()
        else:
            self._optimize_for_desktop()
    
    def _optimize_for_mobile(self) -> None:
        """Optimize layout for mobile screens."""
        logger.debug("Applying mobile optimizations")
        
        # Find splitters and adjust them for mobile
        splitters = self._find_widgets_of_type(QSplitter)
        for splitter in splitters:
            if splitter.orientation() == 1:  # Horizontal
                # Convert horizontal splitters to vertical on mobile
                splitter.setOrientation(2)  # Vertical
    
    def _optimize_for_tablet(self) -> None:
        """Optimize layout for tablet screens."""
        logger.debug("Applying tablet optimizations")
        
        # Tablet-specific optimizations
        # Adjust margins and spacing for touch interfaces
        self._adjust_touch_targets()
    
    def _optimize_for_desktop(self) -> None:
        """Optimize layout for desktop screens."""
        logger.debug("Applying desktop optimizations")
        
        # Desktop-specific optimizations
        # Restore original orientations and layouts
        splitters = self._find_widgets_of_type(QSplitter)
        for splitter in splitters:
            # Restore to horizontal if that's the default
            if hasattr(splitter, '_original_orientation'):
                splitter.setOrientation(splitter._original_orientation)
    
    def _find_widgets_of_type(self, widget_type: type) -> List[QWidget]:
        """Find all widgets of specified type in container."""
        widgets = []
        
        def find_recursive(widget: QWidget):
            if isinstance(widget, widget_type):
                widgets.append(widget)
            
            for child in widget.findChildren(QWidget):
                if isinstance(child, widget_type):
                    widgets.append(child)
        
        if self._container:
            find_recursive(self._container)
        
        return widgets
    
    def _adjust_touch_targets(self) -> None:
        """Adjust UI elements for touch interfaces."""
        # Increase button sizes and spacing for touch
        from PyQt6.QtWidgets import QPushButton, QToolButton
        
        buttons = self._find_widgets_of_type(QPushButton) + self._find_widgets_of_type(QToolButton)
        
        for button in buttons:
            # Ensure minimum touch target size (44px recommended)
            current_size = button.sizeHint()
            min_size = QSize(44, 44)
            
            new_size = QSize(
                max(current_size.width(), min_size.width()),
                max(current_size.height(), min_size.height())
            )
            
            button.setMinimumSize(new_size)
    
    def enable_adaptation(self, enabled: bool) -> None:
        """Enable or disable automatic layout adaptation."""
        self._adaptation_enabled = enabled
        
        if enabled:
            self._initial_layout_check()
    
    def is_adaptation_enabled(self) -> bool:
        """Check if automatic adaptation is enabled."""
        return self._adaptation_enabled
    
    def set_adaptation_delay(self, delay_ms: int) -> None:
        """Set delay for layout adaptation."""
        self._adaptation_delay = max(0, delay_ms)
    
    def get_current_screen_size(self) -> ScreenSize:
        """Get current screen size category."""
        return self._current_screen_size
    
    def create_responsive_splitter(
        self,
        orientation: int,
        mobile_orientation: Optional[int] = None
    ) -> QSplitter:
        """Create a splitter that adapts to screen size."""
        splitter = QSplitter()
        splitter.setOrientation(orientation)
        
        # Store original orientation
        splitter._original_orientation = orientation
        
        # Set mobile orientation if specified
        if mobile_orientation is not None:
            splitter._mobile_orientation = mobile_orientation
        
        return splitter
    
    def create_responsive_scroll_area(self) -> QScrollArea:
        """Create scroll area optimized for responsive design."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(1)  # As needed
        scroll_area.setVerticalScrollBarPolicy(1)    # As needed
        
        return scroll_area
    
    def get_responsive_widgets(self) -> List[ResponsiveWidget]:
        """Get all responsive widgets being managed."""
        return self._responsive_widgets.copy()
    
    def clear_responsive_widgets(self) -> None:
        """Clear all responsive widgets from management."""
        for widget in self._responsive_widgets:
            widget.size_changed.disconnect()
        
        self._responsive_widgets.clear()