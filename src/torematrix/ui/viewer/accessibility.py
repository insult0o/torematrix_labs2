"""
Accessibility Features for Document Viewer Overlay.
This module provides comprehensive accessibility support including
screen reader integration, keyboard navigation, and WCAG 2.1 AA compliance.
"""
from __future__ import annotations

import platform
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Callable, Tuple, Union

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, Qt, QEvent
from PyQt6.QtGui import QKeyEvent, QFocusEvent, QAccessible, QAccessibleInterface
from PyQt6.QtWidgets import QWidget, QApplication

from .coordinates import Point, Rectangle


class AccessibilityRole(Enum):
    """ARIA roles for accessibility."""
    BUTTON = "button"
    LINK = "link"
    DOCUMENT = "document"
    REGION = "region"
    ARTICLE = "article"
    MAIN = "main"
    NAVIGATION = "navigation"
    BANNER = "banner"
    CONTENTINFO = "contentinfo"
    COMPLEMENTARY = "complementary"
    FORM = "form"
    SEARCH = "search"
    TABPANEL = "tabpanel"
    TAB = "tab"
    TABLIST = "tablist"
    LISTBOX = "listbox"
    OPTION = "option"
    GRID = "grid"
    GRIDCELL = "gridcell"
    ROW = "row"
    COLUMNHEADER = "columnheader"
    ROWHEADER = "rowheader"


class AccessibilityState(Enum):
    """Accessibility states."""
    NORMAL = "normal"
    FOCUSED = "focused"
    SELECTED = "selected"
    DISABLED = "disabled"
    EXPANDED = "expanded"
    COLLAPSED = "collapsed"
    CHECKED = "checked"
    UNCHECKED = "unchecked"
    PRESSED = "pressed"
    HIDDEN = "hidden"


@dataclass
class AccessibilityProperties:
    """Accessibility properties for elements."""
    role: AccessibilityRole = AccessibilityRole.REGION
    name: str = ""
    description: str = ""
    value: str = ""
    state: AccessibilityState = AccessibilityState.NORMAL
    level: Optional[int] = None  # For headings (1-6)
    position_in_set: Optional[int] = None
    set_size: Optional[int] = None
    expanded: Optional[bool] = None
    selected: Optional[bool] = None
    disabled: bool = False
    hidden: bool = False
    readonly: bool = False
    required: bool = False
    invalid: bool = False
    live_region: Optional[str] = None  # "polite", "assertive", "off"
    atomic: bool = False
    relevant: List[str] = field(default_factory=list)


@dataclass
class FocusableElement:
    """Element that can receive keyboard focus."""
    element: Any
    tab_index: int
    accessibility_props: AccessibilityProperties
    bounds: Rectangle
    parent: Optional['FocusableElement'] = None
    children: List['FocusableElement'] = field(default_factory=list)
    
    def is_focusable(self) -> bool:
        """Check if element can receive focus."""
        return (not self.accessibility_props.disabled and 
                not self.accessibility_props.hidden and
                self.tab_index >= 0)


class ScreenReaderInterface(ABC):
    """Abstract interface for screen reader communication."""
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if screen reader is available."""
        pass
    
    @abstractmethod
    def announce(self, text: str, priority: str = "polite") -> None:
        """Announce text to screen reader."""
        pass
    
    @abstractmethod
    def speak(self, text: str, interrupt: bool = False) -> None:
        """Speak text immediately."""
        pass
    
    @abstractmethod
    def stop_speech(self) -> None:
        """Stop current speech."""
        pass


class WindowsScreenReader(ScreenReaderInterface):
    """Windows screen reader interface (NVDA, JAWS, Narrator)."""
    
    def __init__(self):
        self.available = self._check_availability()
    
    def is_available(self) -> bool:
        """Check if Windows screen reader is available."""
        return self.available
    
    def announce(self, text: str, priority: str = "polite") -> None:
        """Announce text using Windows accessibility API."""
        if self.available:
            try:
                # Use Windows SAPI for speech
                import comtypes.client
                voice = comtypes.client.CreateObject("SAPI.SpVoice")
                voice.Speak(text, 1)  # Async speech
            except Exception:
                # Fallback to system notification
                self._fallback_announce(text)
    
    def speak(self, text: str, interrupt: bool = False) -> None:
        """Speak text immediately."""
        if self.available:
            try:
                import comtypes.client
                voice = comtypes.client.CreateObject("SAPI.SpVoice")
                flags = 0 if not interrupt else 2  # SVSFPurgeBeforeSpeak
                voice.Speak(text, flags)
            except Exception:
                self._fallback_announce(text)
    
    def stop_speech(self) -> None:
        """Stop current speech."""
        try:
            import comtypes.client
            voice = comtypes.client.CreateObject("SAPI.SpVoice")
            voice.Speak("", 2)  # Purge speech queue
        except Exception:
            pass
    
    def _check_availability(self) -> bool:
        """Check if Windows screen reader features are available."""
        try:
            import comtypes.client
            comtypes.client.CreateObject("SAPI.SpVoice")
            return True
        except Exception:
            return False
    
    def _fallback_announce(self, text: str) -> None:
        """Fallback announcement method."""
        # Could use Windows toast notifications or other methods
        pass


class MacOSScreenReader(ScreenReaderInterface):
    """macOS VoiceOver interface."""
    
    def is_available(self) -> bool:
        """Check if VoiceOver is available."""
        try:
            result = subprocess.run(['defaults', 'read', 'com.apple.universalaccess', 'voiceOverOnOffKey'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False
    
    def announce(self, text: str, priority: str = "polite") -> None:
        """Announce text using VoiceOver."""
        try:
            subprocess.run(['say', text], check=False)
        except Exception:
            pass
    
    def speak(self, text: str, interrupt: bool = False) -> None:
        """Speak text immediately."""
        try:
            if interrupt:
                subprocess.run(['killall', 'say'], check=False)
            subprocess.run(['say', text], check=False)
        except Exception:
            pass
    
    def stop_speech(self) -> None:
        """Stop current speech."""
        try:
            subprocess.run(['killall', 'say'], check=False)
        except Exception:
            pass


class LinuxScreenReader(ScreenReaderInterface):
    """Linux screen reader interface (Orca, espeak)."""
    
    def __init__(self):
        self.speech_dispatcher_available = self._check_speech_dispatcher()
        self.espeak_available = self._check_espeak()
    
    def is_available(self) -> bool:
        """Check if Linux screen reader is available."""
        return self.speech_dispatcher_available or self.espeak_available
    
    def announce(self, text: str, priority: str = "polite") -> None:
        """Announce text using Linux screen reader."""
        if self.speech_dispatcher_available:
            try:
                import speechd
                client = speechd.Speaker()
                if priority == "assertive":
                    client.set_priority(speechd.Priority.IMPORTANT)
                client.say(text)
                client.close()
            except Exception:
                self._fallback_espeak(text)
        elif self.espeak_available:
            self._fallback_espeak(text)
    
    def speak(self, text: str, interrupt: bool = False) -> None:
        """Speak text immediately."""
        self.announce(text, "assertive" if interrupt else "polite")
    
    def stop_speech(self) -> None:
        """Stop current speech."""
        try:
            subprocess.run(['killall', 'espeak'], check=False)
        except Exception:
            pass
    
    def _check_speech_dispatcher(self) -> bool:
        """Check if speech-dispatcher is available."""
        try:
            import speechd
            return True
        except ImportError:
            return False
    
    def _check_espeak(self) -> bool:
        """Check if espeak is available."""
        try:
            result = subprocess.run(['espeak', '--version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False
    
    def _fallback_espeak(self, text: str) -> None:
        """Fallback to espeak."""
        try:
            subprocess.run(['espeak', text], check=False)
        except Exception:
            pass


class KeyboardNavigator:
    """Handles keyboard navigation through focusable elements."""
    
    def __init__(self):
        self.focusable_elements: List[FocusableElement] = []
        self.current_focus_index: int = -1
        self.focus_visible: bool = True
        self.tab_wrap: bool = True
        
        # Keyboard shortcuts
        self.shortcuts: Dict[str, Callable] = {
            'Tab': self.focus_next,
            'Shift+Tab': self.focus_previous,
            'Home': self.focus_first,
            'End': self.focus_last,
            'Escape': self.clear_focus,
            'Enter': self.activate_focused,
            'Space': self.activate_focused,
            'F6': self.focus_next_region,
            'Shift+F6': self.focus_previous_region,
        }
    
    def add_focusable_element(self, element: FocusableElement) -> None:
        """Add an element to the keyboard navigation order."""
        # Insert in tab order
        inserted = False
        for i, existing in enumerate(self.focusable_elements):
            if element.tab_index < existing.tab_index:
                self.focusable_elements.insert(i, element)
                inserted = True
                break
        
        if not inserted:
            self.focusable_elements.append(element)
        
        # Update indices
        self._update_focus_indices()
    
    def remove_focusable_element(self, element: FocusableElement) -> None:
        """Remove an element from keyboard navigation."""
        if element in self.focusable_elements:
            old_index = self.focusable_elements.index(element)
            self.focusable_elements.remove(element)
            
            # Adjust current focus index
            if old_index <= self.current_focus_index:
                self.current_focus_index -= 1
            
            self._update_focus_indices()
    
    def handle_key_event(self, key_event: QKeyEvent) -> bool:
        """Handle keyboard navigation events."""
        key_sequence = self._key_event_to_string(key_event)
        
        if key_sequence in self.shortcuts:
            self.shortcuts[key_sequence]()
            return True
        
        # Handle arrow keys for spatial navigation
        if key_sequence in ['Up', 'Down', 'Left', 'Right']:
            return self._handle_arrow_navigation(key_sequence)
        
        return False
    
    def focus_next(self) -> None:
        """Focus the next element in tab order."""
        if not self.focusable_elements:
            return
        
        start_index = self.current_focus_index
        next_index = (self.current_focus_index + 1) % len(self.focusable_elements)
        
        # Find next focusable element
        while next_index != start_index:
            element = self.focusable_elements[next_index]
            if element.is_focusable():
                self._set_focus(next_index)
                return
            
            next_index = (next_index + 1) % len(self.focusable_elements)
            
            if not self.tab_wrap and next_index == 0:
                break
    
    def focus_previous(self) -> None:
        """Focus the previous element in tab order."""
        if not self.focusable_elements:
            return
        
        start_index = self.current_focus_index
        prev_index = (self.current_focus_index - 1) % len(self.focusable_elements)
        
        # Find previous focusable element
        while prev_index != start_index:
            element = self.focusable_elements[prev_index]
            if element.is_focusable():
                self._set_focus(prev_index)
                return
            
            prev_index = (prev_index - 1) % len(self.focusable_elements)
            
            if not self.tab_wrap and prev_index == len(self.focusable_elements) - 1:
                break
    
    def focus_first(self) -> None:
        """Focus the first focusable element."""
        for i, element in enumerate(self.focusable_elements):
            if element.is_focusable():
                self._set_focus(i)
                return
    
    def focus_last(self) -> None:
        """Focus the last focusable element."""
        for i in range(len(self.focusable_elements) - 1, -1, -1):
            element = self.focusable_elements[i]
            if element.is_focusable():
                self._set_focus(i)
                return
    
    def clear_focus(self) -> None:
        """Clear current focus."""
        self.current_focus_index = -1
    
    def activate_focused(self) -> None:
        """Activate the currently focused element."""
        if 0 <= self.current_focus_index < len(self.focusable_elements):
            element = self.focusable_elements[self.current_focus_index]
            # Trigger element activation
            if hasattr(element.element, 'activate'):
                element.element.activate()
    
    def focus_next_region(self) -> None:
        """Focus next major region (landmark navigation)."""
        # Implementation for landmark navigation
        pass
    
    def focus_previous_region(self) -> None:
        """Focus previous major region (landmark navigation)."""
        # Implementation for landmark navigation
        pass
    
    def _handle_arrow_navigation(self, direction: str) -> bool:
        """Handle spatial navigation with arrow keys."""
        if self.current_focus_index < 0 or not self.focusable_elements:
            return False
        
        current_element = self.focusable_elements[self.current_focus_index]
        current_bounds = current_element.bounds
        
        best_element_index = -1
        best_distance = float('inf')
        
        for i, element in enumerate(self.focusable_elements):
            if i == self.current_focus_index or not element.is_focusable():
                continue
            
            element_bounds = element.bounds
            
            # Check if element is in the correct direction
            is_valid_direction = False
            if direction == 'Up' and element_bounds.y < current_bounds.y:
                is_valid_direction = True
            elif direction == 'Down' and element_bounds.y > current_bounds.y:
                is_valid_direction = True
            elif direction == 'Left' and element_bounds.x < current_bounds.x:
                is_valid_direction = True
            elif direction == 'Right' and element_bounds.x > current_bounds.x:
                is_valid_direction = True
            
            if is_valid_direction:
                # Calculate distance
                center1 = Point(
                    current_bounds.x + current_bounds.width / 2,
                    current_bounds.y + current_bounds.height / 2
                )
                center2 = Point(
                    element_bounds.x + element_bounds.width / 2,
                    element_bounds.y + element_bounds.height / 2
                )
                
                distance = ((center1.x - center2.x) ** 2 + 
                           (center1.y - center2.y) ** 2) ** 0.5
                
                if distance < best_distance:
                    best_distance = distance
                    best_element_index = i
        
        if best_element_index >= 0:
            self._set_focus(best_element_index)
            return True
        
        return False
    
    def _set_focus(self, index: int) -> None:
        """Set focus to element at index."""
        if 0 <= index < len(self.focusable_elements):
            self.current_focus_index = index
            element = self.focusable_elements[index]
            
            # Notify element of focus
            if hasattr(element.element, 'set_focus'):
                element.element.set_focus(True)
    
    def _update_focus_indices(self) -> None:
        """Update focus indices after element changes."""
        if self.current_focus_index >= len(self.focusable_elements):
            self.current_focus_index = len(self.focusable_elements) - 1
    
    def _key_event_to_string(self, event: QKeyEvent) -> str:
        """Convert QKeyEvent to string representation."""
        modifiers = []
        
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            modifiers.append("Ctrl")
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            modifiers.append("Shift")
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            modifiers.append("Alt")
        if event.modifiers() & Qt.KeyboardModifier.MetaModifier:
            modifiers.append("Meta")
        
        key_name = QKeyEvent(event).text()
        if not key_name:
            # Handle special keys
            key_map = {
                Qt.Key.Key_Tab: "Tab",
                Qt.Key.Key_Return: "Enter",
                Qt.Key.Key_Enter: "Enter",
                Qt.Key.Key_Escape: "Escape",
                Qt.Key.Key_Space: "Space",
                Qt.Key.Key_Up: "Up",
                Qt.Key.Key_Down: "Down",
                Qt.Key.Key_Left: "Left",
                Qt.Key.Key_Right: "Right",
                Qt.Key.Key_Home: "Home",
                Qt.Key.Key_End: "End",
                Qt.Key.Key_F6: "F6",
            }
            key_name = key_map.get(event.key(), "")
        
        if modifiers and key_name:
            return "+".join(modifiers + [key_name])
        return key_name


class AccessibilitySignals(QObject):
    """Signals for accessibility events."""
    focus_changed = pyqtSignal(object)  # FocusableElement
    announcement_made = pyqtSignal(str)  # announcement_text
    screen_reader_status_changed = pyqtSignal(bool)  # available


class AccessibilityManager(QObject):
    """
    Main accessibility manager for the overlay system.
    Coordinates screen reader integration, keyboard navigation, and WCAG compliance.
    """
    
    def __init__(self, overlay_engine: Optional[Any] = None):
        super().__init__()
        
        # Dependencies
        self.overlay_engine = overlay_engine
        
        # Screen reader interface
        self.screen_reader = self._create_screen_reader()
        
        # Keyboard navigation
        self.keyboard_navigator = KeyboardNavigator()
        
        # Accessibility state
        self.high_contrast_mode = False
        self.large_text_mode = False
        self.reduced_motion = False
        self.screen_reader_active = self.screen_reader.is_available()
        
        # Element registry
        self.accessible_elements: Dict[Any, AccessibilityProperties] = {}
        
        # Signals
        self.signals = AccessibilitySignals()
        
        # Live region announcements
        self.announcement_queue: List[Tuple[str, str]] = []  # (text, priority)
        self.announcement_timer = QTimer()
        self.announcement_timer.setSingleShot(True)
        self.announcement_timer.timeout.connect(self._process_announcements)
        
        # Setup
        self._setup_accessibility_features()
    
    def _create_screen_reader(self) -> ScreenReaderInterface:
        """Create appropriate screen reader interface for the platform."""
        system = platform.system().lower()
        
        if system == "windows":
            return WindowsScreenReader()
        elif system == "darwin":
            return MacOSScreenReader()
        elif system == "linux":
            return LinuxScreenReader()
        else:
            # Fallback - no screen reader support
            class DummyScreenReader(ScreenReaderInterface):
                def is_available(self) -> bool:
                    return False
                def announce(self, text: str, priority: str = "polite") -> None:
                    pass
                def speak(self, text: str, interrupt: bool = False) -> None:
                    pass
                def stop_speech(self) -> None:
                    pass
            
            return DummyScreenReader()
    
    def _setup_accessibility_features(self) -> None:
        """Setup accessibility features based on system preferences."""
        # Check system accessibility preferences
        self._detect_accessibility_preferences()
        
        # Setup keyboard shortcuts
        self._setup_accessibility_shortcuts()
    
    def _detect_accessibility_preferences(self) -> None:
        """Detect system accessibility preferences."""
        # This would query system accessibility settings
        # Implementation varies by platform
        pass
    
    def _setup_accessibility_shortcuts(self) -> None:
        """Setup accessibility-specific keyboard shortcuts."""
        # Add accessibility shortcuts to keyboard navigator
        accessibility_shortcuts = {
            'Ctrl+Alt+H': self.toggle_high_contrast,
            'Ctrl+Alt+L': self.toggle_large_text,
            'Ctrl+Alt+M': self.toggle_reduced_motion,
            'Ctrl+Alt+S': self.toggle_screen_reader_announcements,
        }
        
        self.keyboard_navigator.shortcuts.update(accessibility_shortcuts)
    
    def register_element(self, element: Any, props: AccessibilityProperties) -> None:
        """Register an element with accessibility properties."""
        self.accessible_elements[element] = props
        
        # Add to keyboard navigation if focusable
        if props.role in [AccessibilityRole.BUTTON, AccessibilityRole.LINK]:
            focusable = FocusableElement(
                element=element,
                tab_index=getattr(element, 'tab_index', 0),
                accessibility_props=props,
                bounds=getattr(element, 'bounds', Rectangle(0, 0, 0, 0))
            )
            self.keyboard_navigator.add_focusable_element(focusable)
    
    def unregister_element(self, element: Any) -> None:
        """Unregister an element from accessibility system."""
        if element in self.accessible_elements:
            del self.accessible_elements[element]
        
        # Remove from keyboard navigation
        for focusable in self.keyboard_navigator.focusable_elements:
            if focusable.element == element:
                self.keyboard_navigator.remove_focusable_element(focusable)
                break
    
    def announce(self, text: str, priority: str = "polite") -> None:
        """Announce text to screen reader."""
        if self.screen_reader_active and text.strip():
            self.announcement_queue.append((text, priority))
            
            if not self.announcement_timer.isActive():
                self.announcement_timer.start(100)  # Small delay to batch announcements
            
            self.signals.announcement_made.emit(text)
    
    def _process_announcements(self) -> None:
        """Process queued announcements."""
        if not self.announcement_queue:
            return
        
        # Get highest priority announcement
        announcement = self.announcement_queue.pop(0)
        text, priority = announcement
        
        self.screen_reader.announce(text, priority)
        
        # Process remaining announcements
        if self.announcement_queue:
            self.announcement_timer.start(500)  # Delay between announcements
    
    def describe_element(self, element: Any) -> str:
        """Generate accessibility description for an element."""
        if element not in self.accessible_elements:
            return "Unknown element"
        
        props = self.accessible_elements[element]
        
        # Build description
        parts = []
        
        # Role
        if props.role:
            parts.append(props.role.value)
        
        # Name
        if props.name:
            parts.append(props.name)
        
        # Value
        if props.value:
            parts.append(f"value {props.value}")
        
        # State
        if props.selected is not None:
            parts.append("selected" if props.selected else "not selected")
        
        if props.expanded is not None:
            parts.append("expanded" if props.expanded else "collapsed")
        
        if props.disabled:
            parts.append("disabled")
        
        # Position info
        if props.position_in_set and props.set_size:
            parts.append(f"{props.position_in_set} of {props.set_size}")
        
        # Description
        if props.description:
            parts.append(props.description)
        
        return ", ".join(parts)
    
    def handle_focus_change(self, element: Any) -> None:
        """Handle element focus change."""
        if element in self.accessible_elements:
            description = self.describe_element(element)
            self.announce(description, "polite")
            
            # Update focus indicator
            self._update_focus_indicator(element)
        
        self.signals.focus_changed.emit(element)
    
    def handle_selection_change(self, elements: List[Any]) -> None:
        """Handle selection change announcement."""
        if not elements:
            self.announce("Selection cleared", "polite")
        elif len(elements) == 1:
            element = elements[0]
            if element in self.accessible_elements:
                props = self.accessible_elements[element]
                self.announce(f"{props.name or 'Element'} selected", "polite")
        else:
            self.announce(f"{len(elements)} elements selected", "polite")
    
    def handle_keyboard_event(self, event: QKeyEvent) -> bool:
        """Handle keyboard events for accessibility."""
        return self.keyboard_navigator.handle_key_event(event)
    
    def toggle_high_contrast(self) -> None:
        """Toggle high contrast mode."""
        self.high_contrast_mode = not self.high_contrast_mode
        self.announce(
            f"High contrast mode {'enabled' if self.high_contrast_mode else 'disabled'}",
            "assertive"
        )
        self._apply_high_contrast_styles()
    
    def toggle_large_text(self) -> None:
        """Toggle large text mode."""
        self.large_text_mode = not self.large_text_mode
        self.announce(
            f"Large text mode {'enabled' if self.large_text_mode else 'disabled'}",
            "assertive"
        )
        self._apply_large_text_styles()
    
    def toggle_reduced_motion(self) -> None:
        """Toggle reduced motion mode."""
        self.reduced_motion = not self.reduced_motion
        self.announce(
            f"Reduced motion {'enabled' if self.reduced_motion else 'disabled'}",
            "assertive"
        )
    
    def toggle_screen_reader_announcements(self) -> None:
        """Toggle screen reader announcements."""
        self.screen_reader_active = not self.screen_reader_active
        self.announce(
            f"Screen reader announcements {'enabled' if self.screen_reader_active else 'disabled'}",
            "assertive"
        )
        self.signals.screen_reader_status_changed.emit(self.screen_reader_active)
    
    def _update_focus_indicator(self, element: Any) -> None:
        """Update visual focus indicator."""
        if hasattr(self.overlay_engine, 'set_focus_indicator'):
            self.overlay_engine.set_focus_indicator(element)
    
    def _apply_high_contrast_styles(self) -> None:
        """Apply high contrast visual styles."""
        if hasattr(self.overlay_engine, 'set_high_contrast_mode'):
            self.overlay_engine.set_high_contrast_mode(self.high_contrast_mode)
    
    def _apply_large_text_styles(self) -> None:
        """Apply large text styles."""
        if hasattr(self.overlay_engine, 'set_large_text_mode'):
            self.overlay_engine.set_large_text_mode(self.large_text_mode)
    
    def validate_wcag_compliance(self) -> Dict[str, List[str]]:
        """Validate WCAG 2.1 AA compliance."""
        issues = {
            "errors": [],
            "warnings": [],
            "info": []
        }
        
        # Check all registered elements
        for element, props in self.accessible_elements.items():
            # Check for missing names
            if not props.name and props.role in [AccessibilityRole.BUTTON, AccessibilityRole.LINK]:
                issues["errors"].append(f"Interactive element missing accessible name")
            
            # Check for missing descriptions
            if props.role == AccessibilityRole.BUTTON and not props.description:
                issues["warnings"].append(f"Button missing description")
            
            # Check for proper heading hierarchy
            if props.role == AccessibilityRole.ARTICLE and props.level:
                if props.level > 6:
                    issues["errors"].append(f"Heading level {props.level} exceeds maximum (6)")
            
            # Check for keyboard accessibility
            if hasattr(element, 'is_interactive') and element.is_interactive():
                if not hasattr(element, 'tab_index') or element.tab_index < 0:
                    issues["errors"].append(f"Interactive element not keyboard accessible")
        
        return issues
    
    def get_accessibility_info(self) -> Dict[str, Any]:
        """Get comprehensive accessibility information."""
        return {
            "screen_reader_available": self.screen_reader.is_available(),
            "screen_reader_active": self.screen_reader_active,
            "high_contrast_mode": self.high_contrast_mode,
            "large_text_mode": self.large_text_mode,
            "reduced_motion": self.reduced_motion,
            "registered_elements": len(self.accessible_elements),
            "focusable_elements": len(self.keyboard_navigator.focusable_elements),
            "wcag_compliance": self.validate_wcag_compliance()
        }


# Utility functions for accessibility
def make_accessible(element: Any, role: AccessibilityRole, 
                   name: str, description: str = "") -> AccessibilityProperties:
    """Create accessibility properties for an element."""
    return AccessibilityProperties(
        role=role,
        name=name,
        description=description
    )


def announce_to_screen_reader(text: str, priority: str = "polite") -> None:
    """Utility function to announce text to screen reader."""
    # This would get the global accessibility manager instance
    pass


class AccessibilityMixin:
    """Mixin to add accessibility support to any widget."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.accessibility_props: Optional[AccessibilityProperties] = None
        self.accessibility_manager: Optional[AccessibilityManager] = None
    
    def set_accessibility_properties(self, props: AccessibilityProperties) -> None:
        """Set accessibility properties for this widget."""
        self.accessibility_props = props
        
        if self.accessibility_manager:
            self.accessibility_manager.register_element(self, props)
    
    def set_accessibility_manager(self, manager: AccessibilityManager) -> None:
        """Set the accessibility manager."""
        self.accessibility_manager = manager
        
        if self.accessibility_props:
            manager.register_element(self, self.accessibility_props)
    
    def announce(self, text: str, priority: str = "polite") -> None:
        """Announce text via accessibility manager."""
        if self.accessibility_manager:
            self.accessibility_manager.announce(text, priority)