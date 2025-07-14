"""
Accessibility features for selection tools.

This module provides comprehensive accessibility support including
keyboard navigation, screen reader integration, high contrast modes,
and assistive technology compatibility.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Callable, Any

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, Qt, QEvent
from PyQt6.QtGui import QKeyEvent, QAccessible, QColor, QPalette, QFont
from PyQt6.QtWidgets import QWidget, QApplication

from .base import SelectionTool, ToolState
from ..coordinates import Point, Rectangle


logger = logging.getLogger(__name__)


class AccessibilityMode(Enum):
    """Accessibility modes for different user needs."""
    DEFAULT = "default"
    HIGH_CONTRAST = "high_contrast"
    LARGE_TEXT = "large_text"
    SCREEN_READER = "screen_reader"
    MOTOR_IMPAIRED = "motor_impaired"
    COLOR_BLIND = "color_blind"


class NavigationDirection(Enum):
    """Navigation directions for keyboard accessibility."""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"
    NEXT = "next"
    PREVIOUS = "previous"
    FIRST = "first"
    LAST = "last"


@dataclass
class AccessibilitySettings:
    """Configuration for accessibility features."""
    mode: AccessibilityMode = AccessibilityMode.DEFAULT
    high_contrast_enabled: bool = False
    large_text_enabled: bool = False
    screen_reader_enabled: bool = False
    keyboard_navigation_enabled: bool = True
    focus_indicators_enabled: bool = True
    audio_feedback_enabled: bool = False
    
    # Visual settings
    contrast_ratio: float = 4.5  # WCAG AA minimum
    text_scale_factor: float = 1.0
    focus_border_width: int = 2
    
    # Timing settings
    selection_timeout: int = 0  # Disable timeouts for accessibility
    hover_delay: int = 1000  # Longer hover delay for motor impaired
    
    # Keyboard settings
    sticky_keys_enabled: bool = False
    repeat_key_filter: bool = False


class AccessibilityManager(QObject):
    """
    Manages accessibility features for selection tools.
    
    Provides keyboard navigation, screen reader support, high contrast
    modes, and other accessibility enhancements.
    """
    
    # Signals
    mode_changed = pyqtSignal(AccessibilityMode)
    focus_changed = pyqtSignal(object)  # element or tool
    selection_announced = pyqtSignal(str)  # announcement text
    navigation_feedback = pyqtSignal(str)  # navigation feedback
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._settings = AccessibilitySettings()
        self._tools: Dict[str, SelectionTool] = {}
        self._current_tool: Optional[SelectionTool] = None
        self._focused_element: Optional[Any] = None
        self._navigation_history: List[Any] = []
        
        # Keyboard navigation state
        self._navigation_enabled = True
        self._current_focus_index = -1
        self._focusable_elements: List[Any] = []
        
        # Audio feedback
        self._announcement_queue: List[str] = []
        self._announcement_timer = QTimer()
        self._announcement_timer.setSingleShot(True)
        self._announcement_timer.timeout.connect(self._process_announcement_queue)
        
        # High contrast colors
        self._high_contrast_colors = {
            'background': QColor(0, 0, 0),
            'foreground': QColor(255, 255, 255),
            'selection': QColor(255, 255, 0),
            'focus': QColor(0, 255, 255),
            'border': QColor(255, 255, 255)
        }
        
        self._setup_accessibility()
    
    def _setup_accessibility(self) -> None:
        """Initialize accessibility features."""
        # Check system accessibility settings
        self._detect_system_accessibility()
        
        # Setup keyboard navigation
        self._setup_keyboard_navigation()
        
        # Apply initial accessibility mode
        self.apply_accessibility_mode(self._settings.mode)
    
    def _detect_system_accessibility(self) -> None:
        """Detect system-level accessibility settings."""
        try:
            # Check for high contrast mode
            app = QApplication.instance()
            if app:
                palette = app.palette()
                # Simple heuristic for high contrast detection
                bg = palette.color(QPalette.ColorRole.Window)
                fg = palette.color(QPalette.ColorRole.WindowText)
                contrast_ratio = self._calculate_contrast_ratio(bg, fg)
                
                if contrast_ratio > 7.0:  # WCAG AAA threshold
                    self._settings.high_contrast_enabled = True
                    self._settings.mode = AccessibilityMode.HIGH_CONTRAST
                
                # Check for large text
                font = app.font()
                if font.pointSize() > 12:
                    self._settings.large_text_enabled = True
                    self._settings.text_scale_factor = font.pointSize() / 10.0
        
        except Exception as e:
            logger.warning(f"Failed to detect system accessibility settings: {e}")
    
    def _setup_keyboard_navigation(self) -> None:
        """Setup keyboard navigation handlers."""
        # Key mappings for navigation
        self._navigation_keys = {
            Qt.Key.Key_Tab: NavigationDirection.NEXT,
            Qt.Key.Key_Backtab: NavigationDirection.PREVIOUS,
            Qt.Key.Key_Up: NavigationDirection.UP,
            Qt.Key.Key_Down: NavigationDirection.DOWN,
            Qt.Key.Key_Left: NavigationDirection.LEFT,
            Qt.Key.Key_Right: NavigationDirection.RIGHT,
            Qt.Key.Key_Home: NavigationDirection.FIRST,
            Qt.Key.Key_End: NavigationDirection.LAST
        }
        
        # Tool selection keys
        self._tool_keys = {
            Qt.Key.Key_P: "pointer_tool",
            Qt.Key.Key_R: "rectangle_tool",
            Qt.Key.Key_L: "lasso_tool",
            Qt.Key.Key_E: "element_aware_tool",
            Qt.Key.Key_M: "multi_select_tool"
        }
    
    def register_tool(self, tool: SelectionTool) -> None:
        """Register a tool for accessibility management."""
        if tool.tool_id not in self._tools:
            self._tools[tool.tool_id] = tool
            
            # Connect to tool signals for accessibility feedback
            tool.selection_changed.connect(self._on_selection_changed)
            tool.state_changed.connect(self._on_tool_state_changed)
            
            logger.info(f"Registered tool for accessibility: {tool.tool_id}")
    
    def unregister_tool(self, tool_id: str) -> None:
        """Unregister a tool from accessibility management."""
        if tool_id in self._tools:
            tool = self._tools[tool_id]
            tool.selection_changed.disconnect(self._on_selection_changed)
            tool.state_changed.disconnect(self._on_tool_state_changed)
            del self._tools[tool_id]
            
            logger.info(f"Unregistered tool from accessibility: {tool_id}")
    
    def set_current_tool(self, tool: Optional[SelectionTool]) -> None:
        """Set the currently active tool for accessibility."""
        if self._current_tool != tool:
            self._current_tool = tool
            
            if tool:
                self.announce(f"Selected {tool.name}")
                self._update_focusable_elements()
    
    def handle_key_event(self, event: QKeyEvent) -> bool:
        """
        Handle keyboard input for accessibility navigation.
        
        Returns True if the event was handled, False otherwise.
        """
        if not self._navigation_enabled:
            return False
        
        key = event.key()
        modifiers = event.modifiers()
        
        # Handle tool selection with Alt key
        if modifiers & Qt.KeyboardModifier.AltModifier:
            if key in self._tool_keys:
                tool_id = self._tool_keys[key]
                if tool_id in self._tools:
                    self.set_current_tool(self._tools[tool_id])
                    return True
        
        # Handle navigation keys
        if key in self._navigation_keys:
            direction = self._navigation_keys[key]
            self._navigate(direction, modifiers)
            return True
        
        # Handle action keys
        if key == Qt.Key.Key_Space or key == Qt.Key.Key_Return:
            self._activate_current_focus()
            return True
        
        # Handle escape key
        if key == Qt.Key.Key_Escape:
            self._clear_focus()
            return True
        
        # Handle accessibility mode toggles
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if key == Qt.Key.Key_H:  # Ctrl+H for high contrast
                self.toggle_high_contrast()
                return True
            elif key == Qt.Key.Key_Plus:  # Ctrl++ for larger text
                self.increase_text_size()
                return True
            elif key == Qt.Key.Key_Minus:  # Ctrl+- for smaller text
                self.decrease_text_size()
                return True
        
        return False
    
    def _navigate(self, direction: NavigationDirection, modifiers: Qt.KeyboardModifier) -> None:
        """Navigate between focusable elements."""
        if not self._focusable_elements:
            self._update_focusable_elements()
        
        if not self._focusable_elements:
            self.announce("No focusable elements available")
            return
        
        old_index = self._current_focus_index
        
        if direction == NavigationDirection.NEXT:
            self._current_focus_index = (self._current_focus_index + 1) % len(self._focusable_elements)
        elif direction == NavigationDirection.PREVIOUS:
            self._current_focus_index = (self._current_focus_index - 1) % len(self._focusable_elements)
        elif direction == NavigationDirection.FIRST:
            self._current_focus_index = 0
        elif direction == NavigationDirection.LAST:
            self._current_focus_index = len(self._focusable_elements) - 1
        else:
            # Spatial navigation (up, down, left, right)
            self._spatial_navigate(direction)
        
        if self._current_focus_index != old_index:
            self._set_focus(self._current_focus_index)
    
    def _spatial_navigate(self, direction: NavigationDirection) -> None:
        """Navigate spatially between elements."""
        if not self._focused_element or not self._focusable_elements:
            return
        
        current_bounds = self._get_element_bounds(self._focused_element)
        if not current_bounds:
            return
        
        best_candidate = None
        best_distance = float('inf')
        
        for i, element in enumerate(self._focusable_elements):
            if element == self._focused_element:
                continue
            
            element_bounds = self._get_element_bounds(element)
            if not element_bounds:
                continue
            
            # Check if element is in the right direction
            if not self._is_in_direction(current_bounds, element_bounds, direction):
                continue
            
            # Calculate distance
            distance = self._calculate_navigation_distance(current_bounds, element_bounds, direction)
            if distance < best_distance:
                best_distance = distance
                best_candidate = i
        
        if best_candidate is not None:
            self._current_focus_index = best_candidate
            self._set_focus(self._current_focus_index)
    
    def _is_in_direction(self, from_bounds: Rectangle, to_bounds: Rectangle, direction: NavigationDirection) -> bool:
        """Check if target bounds is in the specified direction from source bounds."""
        from_center = Point(from_bounds.x + from_bounds.width / 2, from_bounds.y + from_bounds.height / 2)
        to_center = Point(to_bounds.x + to_bounds.width / 2, to_bounds.y + to_bounds.height / 2)
        
        if direction == NavigationDirection.UP:
            return to_center.y < from_center.y
        elif direction == NavigationDirection.DOWN:
            return to_center.y > from_center.y
        elif direction == NavigationDirection.LEFT:
            return to_center.x < from_center.x
        elif direction == NavigationDirection.RIGHT:
            return to_center.x > from_center.x
        
        return False
    
    def _calculate_navigation_distance(self, from_bounds: Rectangle, to_bounds: Rectangle, direction: NavigationDirection) -> float:
        """Calculate navigation distance between two elements."""
        from_center = Point(from_bounds.x + from_bounds.width / 2, from_bounds.y + from_bounds.height / 2)
        to_center = Point(to_bounds.x + to_bounds.width / 2, to_bounds.y + to_bounds.height / 2)
        
        # Euclidean distance
        dx = to_center.x - from_center.x
        dy = to_center.y - from_center.y
        distance = (dx ** 2 + dy ** 2) ** 0.5
        
        # Weight based on alignment with direction
        if direction in [NavigationDirection.UP, NavigationDirection.DOWN]:
            # Prefer elements that are horizontally aligned
            distance += abs(dx) * 0.5
        elif direction in [NavigationDirection.LEFT, NavigationDirection.RIGHT]:
            # Prefer elements that are vertically aligned
            distance += abs(dy) * 0.5
        
        return distance
    
    def _set_focus(self, index: int) -> None:
        """Set focus to element at the specified index."""
        if 0 <= index < len(self._focusable_elements):
            element = self._focusable_elements[index]
            self._focused_element = element
            
            # Announce the focused element
            description = self._get_element_description(element)
            self.announce(f"Focused: {description}")
            
            self.focus_changed.emit(element)
    
    def _activate_current_focus(self) -> None:
        """Activate the currently focused element."""
        if self._focused_element and self._current_tool:
            # Simulate selection of the focused element
            bounds = self._get_element_bounds(self._focused_element)
            if bounds:
                center = Point(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2)
                # This would need to be integrated with the actual selection system
                self.announce(f"Selected: {self._get_element_description(self._focused_element)}")
    
    def _clear_focus(self) -> None:
        """Clear current focus."""
        self._focused_element = None
        self._current_focus_index = -1
        self.announce("Focus cleared")
        self.focus_changed.emit(None)
    
    def _update_focusable_elements(self) -> None:
        """Update the list of focusable elements."""
        # This would be implemented to get elements from the overlay system
        # For now, return empty list as placeholder
        self._focusable_elements = []
        self._current_focus_index = -1
    
    def _get_element_bounds(self, element: Any) -> Optional[Rectangle]:
        """Get bounds for an element."""
        # This would be implemented to get actual element bounds
        # For now, return None as placeholder
        return None
    
    def _get_element_description(self, element: Any) -> str:
        """Get accessible description for an element."""
        if hasattr(element, 'accessibility_description'):
            return element.accessibility_description
        elif hasattr(element, 'type'):
            return f"{element.type} element"
        else:
            return "Unknown element"
    
    def announce(self, text: str) -> None:
        """Announce text for screen readers."""
        if self._settings.screen_reader_enabled or self._settings.audio_feedback_enabled:
            self._announcement_queue.append(text)
            
            if not self._announcement_timer.isActive():
                self._announcement_timer.start(100)  # Small delay to batch announcements
        
        self.selection_announced.emit(text)
        logger.info(f"Accessibility announcement: {text}")
    
    def _process_announcement_queue(self) -> None:
        """Process queued announcements."""
        if self._announcement_queue:
            # Combine multiple announcements
            text = ". ".join(self._announcement_queue)
            self._announcement_queue.clear()
            
            # Send to screen reader (this would use actual screen reader API)
            QAccessible.updateAccessibility(QAccessible.Event.Announcement)
    
    def apply_accessibility_mode(self, mode: AccessibilityMode) -> None:
        """Apply accessibility mode settings."""
        old_mode = self._settings.mode
        self._settings.mode = mode
        
        if mode == AccessibilityMode.HIGH_CONTRAST:
            self._apply_high_contrast()
        elif mode == AccessibilityMode.LARGE_TEXT:
            self._apply_large_text()
        elif mode == AccessibilityMode.SCREEN_READER:
            self._apply_screen_reader_mode()
        elif mode == AccessibilityMode.MOTOR_IMPAIRED:
            self._apply_motor_impaired_mode()
        elif mode == AccessibilityMode.COLOR_BLIND:
            self._apply_color_blind_mode()
        else:
            self._apply_default_mode()
        
        if old_mode != mode:
            self.announce(f"Accessibility mode changed to {mode.value}")
            self.mode_changed.emit(mode)
    
    def _apply_high_contrast(self) -> None:
        """Apply high contrast visual settings."""
        self._settings.high_contrast_enabled = True
        self._settings.focus_border_width = 3
        # Additional high contrast settings would be applied here
    
    def _apply_large_text(self) -> None:
        """Apply large text settings."""
        self._settings.large_text_enabled = True
        self._settings.text_scale_factor = 1.5
    
    def _apply_screen_reader_mode(self) -> None:
        """Apply screen reader compatibility settings."""
        self._settings.screen_reader_enabled = True
        self._settings.audio_feedback_enabled = True
        self._settings.focus_indicators_enabled = True
    
    def _apply_motor_impaired_mode(self) -> None:
        """Apply settings for motor-impaired users."""
        self._settings.hover_delay = 2000  # Longer hover delay
        self._settings.selection_timeout = 0  # No timeouts
        self._settings.sticky_keys_enabled = True
    
    def _apply_color_blind_mode(self) -> None:
        """Apply color-blind friendly settings."""
        # Use patterns and shapes in addition to colors
        # This would modify the visual rendering of selection tools
        pass
    
    def _apply_default_mode(self) -> None:
        """Apply default accessibility settings."""
        self._settings = AccessibilitySettings()  # Reset to defaults
    
    def toggle_high_contrast(self) -> None:
        """Toggle high contrast mode."""
        if self._settings.mode == AccessibilityMode.HIGH_CONTRAST:
            self.apply_accessibility_mode(AccessibilityMode.DEFAULT)
        else:
            self.apply_accessibility_mode(AccessibilityMode.HIGH_CONTRAST)
    
    def increase_text_size(self) -> None:
        """Increase text size for better readability."""
        self._settings.text_scale_factor = min(self._settings.text_scale_factor + 0.1, 3.0)
        self.announce(f"Text size increased to {self._settings.text_scale_factor:.1f}x")
    
    def decrease_text_size(self) -> None:
        """Decrease text size."""
        self._settings.text_scale_factor = max(self._settings.text_scale_factor - 0.1, 0.5)
        self.announce(f"Text size decreased to {self._settings.text_scale_factor:.1f}x")
    
    def _calculate_contrast_ratio(self, color1: QColor, color2: QColor) -> float:
        """Calculate contrast ratio between two colors."""
        # Convert to relative luminance
        def relative_luminance(color: QColor) -> float:
            def channel_luminance(channel: int) -> float:
                c = channel / 255.0
                if c <= 0.03928:
                    return c / 12.92
                else:
                    return ((c + 0.055) / 1.055) ** 2.4
            
            r = channel_luminance(color.red())
            g = channel_luminance(color.green())
            b = channel_luminance(color.blue())
            
            return 0.2126 * r + 0.7152 * g + 0.0722 * b
        
        l1 = relative_luminance(color1)
        l2 = relative_luminance(color2)
        
        # Ensure l1 is the lighter color
        if l1 < l2:
            l1, l2 = l2, l1
        
        return (l1 + 0.05) / (l2 + 0.05)
    
    def _on_selection_changed(self, result) -> None:
        """Handle selection change for accessibility feedback."""
        if result and result.elements:
            element_count = len(result.elements)
            if element_count == 1:
                description = self._get_element_description(result.elements[0])
                self.announce(f"Selected {description}")
            else:
                self.announce(f"Selected {element_count} elements")
        else:
            self.announce("Selection cleared")
    
    def _on_tool_state_changed(self, state: ToolState) -> None:
        """Handle tool state change for accessibility feedback."""
        if self._current_tool:
            if state == ToolState.ACTIVE:
                self.announce(f"{self._current_tool.name} activated")
            elif state == ToolState.SELECTING:
                self.announce("Selection in progress")
            elif state == ToolState.SELECTED:
                self.announce("Selection completed")
    
    def get_settings(self) -> AccessibilitySettings:
        """Get current accessibility settings."""
        return self._settings
    
    def update_settings(self, settings: AccessibilitySettings) -> None:
        """Update accessibility settings."""
        self._settings = settings
        self.apply_accessibility_mode(settings.mode)
    
    def get_keyboard_shortcuts(self) -> Dict[str, str]:
        """Get available keyboard shortcuts."""
        return {
            "Alt+P": "Select Pointer Tool",
            "Alt+R": "Select Rectangle Tool", 
            "Alt+L": "Select Lasso Tool",
            "Alt+E": "Select Element Aware Tool",
            "Alt+M": "Select Multi-Select Tool",
            "Tab": "Navigate to next element",
            "Shift+Tab": "Navigate to previous element",
            "Arrow Keys": "Spatial navigation",
            "Home": "Navigate to first element",
            "End": "Navigate to last element",
            "Space/Enter": "Activate focused element",
            "Escape": "Clear focus/selection",
            "Ctrl+H": "Toggle high contrast mode",
            "Ctrl++": "Increase text size",
            "Ctrl+-": "Decrease text size"
        }