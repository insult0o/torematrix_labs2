"""
Dynamic Tooltip System for Document Viewer Overlay.
This module provides rich, dynamic tooltips with customizable content,
positioning, and styling for enhanced user experience.
"""
from __future__ import annotations

import threading
import time
import weakref
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Callable, Union, Tuple

from PyQt6.QtCore import QObject, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPixmap, QFont, QFontMetrics, QPainter, QPen, QBrush, QColor
from PyQt6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                           QFrame, QScrollArea, QTextEdit, QApplication)

from .coordinates import Point, Rectangle


class TooltipPosition(Enum):
    """Tooltip positioning options."""
    AUTO = "auto"           # Automatically position to avoid screen edges
    ABOVE = "above"         # Above the target
    BELOW = "below"         # Below the target
    LEFT = "left"           # Left of the target
    RIGHT = "right"         # Right of the target
    ABOVE_LEFT = "above_left"
    ABOVE_RIGHT = "above_right"
    BELOW_LEFT = "below_left"
    BELOW_RIGHT = "below_right"


class TooltipTheme(Enum):
    """Tooltip visual themes."""
    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    ACCENT = "accent"
    ERROR = "error"
    WARNING = "warning"
    SUCCESS = "success"


@dataclass
class TooltipStyle:
    """Tooltip styling configuration."""
    background_color: str = "#2b2b2b"
    border_color: str = "#555555"
    text_color: str = "#ffffff"
    border_width: int = 1
    border_radius: int = 6
    padding: int = 8
    font_family: str = "Arial"
    font_size: int = 11
    max_width: int = 300
    max_height: int = 200
    shadow_enabled: bool = True
    shadow_color: str = "#000000"
    shadow_offset: Tuple[int, int] = (2, 2)
    shadow_blur: int = 4


@dataclass
class TooltipContent:
    """Tooltip content structure."""
    title: Optional[str] = None
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    html_content: Optional[str] = None
    custom_widget: Optional[QWidget] = None
    image: Optional[QPixmap] = None
    links: Optional[List[Tuple[str, str]]] = None  # (text, url) pairs


class TooltipContentProvider(Protocol):
    """Protocol for objects that can provide tooltip content."""
    
    def get_tooltip_content(self) -> TooltipContent:
        """Return tooltip content for this object."""
        ...


class TooltipWidget(QWidget):
    """Custom tooltip widget with rich content support."""
    
    def __init__(self, content: TooltipContent, style: TooltipStyle):
        super().__init__()
        
        self.content = content
        self.style = style
        
        # Widget setup
        self.setWindowFlags(
            self.windowFlags() | 
            self.windowFlags().FramelessWindowHint | 
            self.windowFlags().WindowStaysOnTopHint |
            self.windowFlags().Tool
        )
        self.setAttribute(self.getAttribute().WA_TranslucentBackground)
        self.setAttribute(self.getAttribute().WA_ShowWithoutActivating)
        
        # Setup UI
        self._setup_ui()
        self._apply_style()
        
        # Animation for show/hide
        self.show_animation = QPropertyAnimation(self, b"windowOpacity")
        self.show_animation.setDuration(150)
        self.show_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.hide_animation = QPropertyAnimation(self, b"windowOpacity")
        self.hide_animation.setDuration(100)
        self.hide_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        
    def _setup_ui(self) -> None:
        """Setup the tooltip UI based on content."""
        layout = QVBoxLayout()
        layout.setContentsMargins(self.style.padding, self.style.padding, 
                                 self.style.padding, self.style.padding)
        layout.setSpacing(4)
        
        # Title
        if self.content.title:
            title_label = QLabel(self.content.title)
            title_font = QFont(self.style.font_family, self.style.font_size + 1)
            title_font.setBold(True)
            title_label.setFont(title_font)
            title_label.setStyleSheet(f"color: {self.style.text_color};")
            layout.addWidget(title_label)
        
        # Image
        if self.content.image:
            image_label = QLabel()
            image_label.setPixmap(self.content.image.scaled(200, 150, 
                                  self.content.image.KeepAspectRatio,
                                  self.content.image.SmoothTransformation))
            layout.addWidget(image_label)
        
        # Description
        if self.content.description:
            desc_label = QLabel(self.content.description)
            desc_label.setFont(QFont(self.style.font_family, self.style.font_size))
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet(f"color: {self.style.text_color};")
            layout.addWidget(desc_label)
        
        # HTML content
        if self.content.html_content:
            html_widget = QTextEdit()
            html_widget.setHtml(self.content.html_content)
            html_widget.setReadOnly(True)
            html_widget.setMaximumHeight(100)
            html_widget.setVerticalScrollBarPolicy(html_widget.ScrollBarAsNeeded)
            layout.addWidget(html_widget)
        
        # Properties
        if self.content.properties:
            self._add_properties_section(layout, "Properties", self.content.properties)
        
        # Metadata
        if self.content.metadata:
            self._add_properties_section(layout, "Metadata", self.content.metadata)
        
        # Links
        if self.content.links:
            self._add_links_section(layout)
        
        # Custom widget
        if self.content.custom_widget:
            layout.addWidget(self.content.custom_widget)
        
        self.setLayout(layout)
    
    def _add_properties_section(self, layout: QVBoxLayout, title: str, properties: Dict[str, Any]) -> None:
        """Add a properties section to the tooltip."""
        if not properties:
            return
            
        # Section title
        section_label = QLabel(title + ":")
        section_font = QFont(self.style.font_family, self.style.font_size)
        section_font.setBold(True)
        section_label.setFont(section_font)
        section_label.setStyleSheet(f"color: {self.style.text_color}; margin-top: 4px;")
        layout.addWidget(section_label)
        
        # Properties
        for key, value in properties.items():
            prop_layout = QHBoxLayout()
            
            key_label = QLabel(f"{key}:")
            key_label.setFont(QFont(self.style.font_family, self.style.font_size))
            key_label.setStyleSheet(f"color: {self.style.text_color}; font-weight: bold;")
            
            value_label = QLabel(str(value))
            value_label.setFont(QFont(self.style.font_family, self.style.font_size))
            value_label.setStyleSheet(f"color: {self.style.text_color};")
            value_label.setWordWrap(True)
            
            prop_layout.addWidget(key_label)
            prop_layout.addWidget(value_label, 1)
            
            layout.addLayout(prop_layout)
    
    def _add_links_section(self, layout: QVBoxLayout) -> None:
        """Add links section to the tooltip."""
        if not self.content.links:
            return
            
        links_label = QLabel("Links:")
        links_font = QFont(self.style.font_family, self.style.font_size)
        links_font.setBold(True)
        links_label.setFont(links_font)
        links_label.setStyleSheet(f"color: {self.style.text_color}; margin-top: 4px;")
        layout.addWidget(links_label)
        
        for text, url in self.content.links:
            link_label = QLabel(f'<a href="{url}" style="color: #4a9eff;">{text}</a>')
            link_label.setFont(QFont(self.style.font_family, self.style.font_size))
            link_label.setOpenExternalLinks(True)
            layout.addWidget(link_label)
    
    def _apply_style(self) -> None:
        """Apply styling to the tooltip widget."""
        style_sheet = f"""
        QWidget {{
            background-color: {self.style.background_color};
            border: {self.style.border_width}px solid {self.style.border_color};
            border-radius: {self.style.border_radius}px;
        }}
        """
        self.setStyleSheet(style_sheet)
        
        # Set size constraints
        self.setMaximumWidth(self.style.max_width)
        self.setMaximumHeight(self.style.max_height)
    
    def show_animated(self) -> None:
        """Show tooltip with animation."""
        self.setWindowOpacity(0.0)
        self.show()
        
        self.show_animation.setStartValue(0.0)
        self.show_animation.setEndValue(0.95)
        self.show_animation.start()
    
    def hide_animated(self, callback: Optional[Callable] = None) -> None:
        """Hide tooltip with animation."""
        self.hide_animation.setStartValue(self.windowOpacity())
        self.hide_animation.setEndValue(0.0)
        
        if callback:
            self.hide_animation.finished.connect(callback)
        
        self.hide_animation.finished.connect(self.close)
        self.hide_animation.start()


class TooltipManager(QObject):
    """
    Singleton tooltip manager for coordinating tooltip display.
    Handles tooltip timing, positioning, and lifecycle management.
    """
    
    _instance: Optional['TooltipManager'] = None
    _lock = threading.Lock()
    
    tooltip_shown = pyqtSignal(object)  # element
    tooltip_hidden = pyqtSignal()
    
    def __new__(cls) -> 'TooltipManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
            
        super().__init__()
        self._initialized = True
        
        # State
        self.active_tooltip: Optional[TooltipWidget] = None
        self.pending_element: Optional[Any] = None
        self.pending_position: Optional[Point] = None
        
        # Configuration
        self.tooltip_delay = 500  # ms
        self.hide_delay = 100     # ms
        self.default_style = TooltipStyle()
        self.theme_styles: Dict[TooltipTheme, TooltipStyle] = {
            TooltipTheme.DEFAULT: TooltipStyle(),
            TooltipTheme.DARK: TooltipStyle(
                background_color="#1e1e1e",
                border_color="#404040",
                text_color="#ffffff"
            ),
            TooltipTheme.LIGHT: TooltipStyle(
                background_color="#ffffff",
                border_color="#cccccc",
                text_color="#000000"
            ),
            TooltipTheme.ERROR: TooltipStyle(
                background_color="#ff4444",
                border_color="#cc0000",
                text_color="#ffffff"
            ),
            TooltipTheme.WARNING: TooltipStyle(
                background_color="#ffaa00",
                border_color="#cc8800",
                text_color="#000000"
            ),
            TooltipTheme.SUCCESS: TooltipStyle(
                background_color="#44ff44",
                border_color="#00cc00",
                text_color="#000000"
            )
        }
        
        # Timers
        self.show_timer = QTimer()
        self.show_timer.setSingleShot(True)
        self.show_timer.timeout.connect(self._show_pending_tooltip)
        
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._hide_current_tooltip)
        
        # Cache for tooltip content
        self.content_cache: Dict[Any, TooltipContent] = weakref.WeakKeyDictionary()
        
    @classmethod
    def get_instance(cls) -> 'TooltipManager':
        """Get the singleton instance."""
        return cls()
    
    def show_tooltip(self, element: Any, position: Point, 
                    theme: TooltipTheme = TooltipTheme.DEFAULT,
                    delay: Optional[int] = None) -> None:
        """Show tooltip for the specified element."""
        # Cancel any pending operations
        self.show_timer.stop()
        self.hide_timer.stop()
        
        # Hide current tooltip immediately if different element
        if self.active_tooltip and self.pending_element != element:
            self._hide_current_tooltip()
        
        # Set up pending tooltip
        self.pending_element = element
        self.pending_position = position
        
        # Start show timer
        show_delay = delay if delay is not None else self.tooltip_delay
        self.show_timer.start(show_delay)
    
    def hide_tooltip(self, delay: Optional[int] = None) -> None:
        """Hide the current tooltip."""
        # Cancel show timer
        self.show_timer.stop()
        
        if self.active_tooltip:
            hide_delay = delay if delay is not None else self.hide_delay
            self.hide_timer.start(hide_delay)
    
    def hide_tooltip_immediately(self) -> None:
        """Hide tooltip immediately without delay."""
        self.show_timer.stop()
        self.hide_timer.stop()
        self._hide_current_tooltip()
    
    def _show_pending_tooltip(self) -> None:
        """Show the pending tooltip."""
        if not self.pending_element or not self.pending_position:
            return
        
        # Get tooltip content
        content = self._get_tooltip_content(self.pending_element)
        if not content:
            return
        
        # Get style for theme
        style = self.theme_styles.get(TooltipTheme.DEFAULT, self.default_style)
        
        # Create tooltip widget
        tooltip = TooltipWidget(content, style)
        
        # Position tooltip
        tooltip_pos = self._calculate_tooltip_position(
            self.pending_position, tooltip.sizeHint(), TooltipPosition.AUTO
        )
        tooltip.move(int(tooltip_pos.x), int(tooltip_pos.y))
        
        # Show tooltip
        tooltip.show_animated()
        
        # Update state
        self.active_tooltip = tooltip
        self.tooltip_shown.emit(self.pending_element)
        
        # Clear pending
        self.pending_element = None
        self.pending_position = None
    
    def _hide_current_tooltip(self) -> None:
        """Hide the current tooltip."""
        if self.active_tooltip:
            self.active_tooltip.hide_animated()
            self.active_tooltip = None
            self.tooltip_hidden.emit()
    
    def _get_tooltip_content(self, element: Any) -> Optional[TooltipContent]:
        """Get tooltip content for an element."""
        # Check cache first
        if element in self.content_cache:
            return self.content_cache[element]
        
        content = None
        
        # Try to get content from element itself
        if hasattr(element, 'get_tooltip_content'):
            content = element.get_tooltip_content()
        elif isinstance(element, TooltipContentProvider):
            content = element.get_tooltip_content()
        else:
            # Generate default content
            content = self._generate_default_content(element)
        
        # Cache content
        if content:
            self.content_cache[element] = content
        
        return content
    
    def _generate_default_content(self, element: Any) -> TooltipContent:
        """Generate default tooltip content for an element."""
        content = TooltipContent()
        
        # Try to extract basic information
        if hasattr(element, 'type'):
            content.title = f"Element: {element.type}"
        elif hasattr(element, '__class__'):
            content.title = f"Element: {element.__class__.__name__}"
        else:
            content.title = "Element"
        
        # Try to get description
        if hasattr(element, 'description'):
            content.description = element.description
        elif hasattr(element, 'text'):
            content.description = element.text
        
        # Try to get properties
        properties = {}
        if hasattr(element, 'bounds'):
            bounds = element.bounds
            properties['Position'] = f"({bounds.x:.1f}, {bounds.y:.1f})"
            properties['Size'] = f"{bounds.width:.1f} × {bounds.height:.1f}"
        
        if hasattr(element, 'layer'):
            properties['Layer'] = element.layer
        
        if hasattr(element, 'id'):
            properties['ID'] = element.id
        
        if properties:
            content.properties = properties
        
        # Try to get metadata
        if hasattr(element, 'metadata'):
            content.metadata = element.metadata
        
        return content
    
    def _calculate_tooltip_position(self, target_position: Point, 
                                   tooltip_size, 
                                   preferred_position: TooltipPosition) -> Point:
        """Calculate optimal tooltip position."""
        # Get screen geometry
        screen = QApplication.primaryScreen()
        screen_rect = screen.availableGeometry()
        
        tooltip_width = tooltip_size.width()
        tooltip_height = tooltip_size.height()
        
        # Default offset from cursor
        offset_x = 10
        offset_y = 10
        
        # Calculate initial position based on preference
        if preferred_position == TooltipPosition.AUTO:
            # Determine best position automatically
            x = target_position.x + offset_x
            y = target_position.y + offset_y
            
            # Adjust if tooltip would go off screen
            if x + tooltip_width > screen_rect.right():
                x = target_position.x - tooltip_width - offset_x
            
            if y + tooltip_height > screen_rect.bottom():
                y = target_position.y - tooltip_height - offset_y
            
            # Ensure tooltip stays on screen
            x = max(screen_rect.left(), min(x, screen_rect.right() - tooltip_width))
            y = max(screen_rect.top(), min(y, screen_rect.bottom() - tooltip_height))
            
        elif preferred_position == TooltipPosition.ABOVE:
            x = target_position.x - tooltip_width // 2
            y = target_position.y - tooltip_height - offset_y
        elif preferred_position == TooltipPosition.BELOW:
            x = target_position.x - tooltip_width // 2
            y = target_position.y + offset_y
        elif preferred_position == TooltipPosition.LEFT:
            x = target_position.x - tooltip_width - offset_x
            y = target_position.y - tooltip_height // 2
        elif preferred_position == TooltipPosition.RIGHT:
            x = target_position.x + offset_x
            y = target_position.y - tooltip_height // 2
        else:
            # Use auto positioning for other cases
            x = target_position.x + offset_x
            y = target_position.y + offset_y
        
        return Point(x, y)
    
    def set_tooltip_delay(self, delay_ms: int) -> None:
        """Set the tooltip show delay."""
        self.tooltip_delay = delay_ms
    
    def set_hide_delay(self, delay_ms: int) -> None:
        """Set the tooltip hide delay."""
        self.hide_delay = delay_ms
    
    def register_custom_theme(self, theme_name: str, style: TooltipStyle) -> None:
        """Register a custom tooltip theme."""
        # Convert string theme to enum if needed
        if isinstance(theme_name, str):
            # Create a dynamic enum value
            custom_theme = type('CustomTheme', (TooltipTheme,), {theme_name.upper(): theme_name})
            self.theme_styles[custom_theme] = style
        else:
            self.theme_styles[theme_name] = style
    
    def clear_content_cache(self) -> None:
        """Clear the tooltip content cache."""
        self.content_cache.clear()
    
    def is_tooltip_visible(self) -> bool:
        """Check if a tooltip is currently visible."""
        return self.active_tooltip is not None and self.active_tooltip.isVisible()
    
    def get_tooltip_element(self) -> Optional[Any]:
        """Get the element for the currently visible tooltip."""
        return self.pending_element if self.active_tooltip else None


# Utility functions for easy tooltip integration
def show_tooltip(element: Any, position: Point, 
                theme: TooltipTheme = TooltipTheme.DEFAULT) -> None:
    """Convenience function to show a tooltip."""
    manager = TooltipManager.get_instance()
    manager.show_tooltip(element, position, theme)


def hide_tooltip() -> None:
    """Convenience function to hide the current tooltip."""
    manager = TooltipManager.get_instance()
    manager.hide_tooltip()


def set_tooltip_delay(delay_ms: int) -> None:
    """Convenience function to set tooltip delay."""
    manager = TooltipManager.get_instance()
    manager.set_tooltip_delay(delay_ms)


class TooltipMixin:
    """Mixin class to add tooltip support to any object."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tooltip_content: Optional[TooltipContent] = None
    
    def set_tooltip_content(self, content: TooltipContent) -> None:
        """Set custom tooltip content."""
        self._tooltip_content = content
    
    def get_tooltip_content(self) -> Optional[TooltipContent]:
        """Get tooltip content for this object."""
        return self._tooltip_content
    
    def show_tooltip_at(self, position: Point, 
                       theme: TooltipTheme = TooltipTheme.DEFAULT) -> None:
        """Show tooltip for this object at the specified position."""
        show_tooltip(self, position, theme)