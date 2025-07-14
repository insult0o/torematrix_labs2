"""
Unit tests for the accessibility system.
Tests screen reader integration, keyboard navigation, and WCAG compliance.
"""
import pytest
import platform
from unittest.mock import Mock, MagicMock, patch

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent

from src.torematrix.ui.viewer.accessibility import (
    AccessibilityManager, AccessibilityRole, AccessibilityState,
    AccessibilityProperties, FocusableElement, KeyboardNavigator,
    ScreenReaderInterface, WindowsScreenReader, MacOSScreenReader,
    LinuxScreenReader, AccessibilityMixin, make_accessible
)
from src.torematrix.ui.viewer.coordinates import Point, Rectangle


class MockScreenReader(ScreenReaderInterface):
    """Mock screen reader for testing."""
    
    def __init__(self, available=True):
        self._available = available
        self.announcements = []
        self.speeches = []
        self.stopped = False
    
    def is_available(self) -> bool:
        return self._available
    
    def announce(self, text: str, priority: str = "polite") -> None:
        self.announcements.append((text, priority))
    
    def speak(self, text: str, interrupt: bool = False) -> None:
        self.speeches.append((text, interrupt))
    
    def stop_speech(self) -> None:
        self.stopped = True


class TestAccessibilityProperties:
    """Test accessibility properties structure."""
    
    def test_default_properties(self):
        """Test default accessibility properties."""
        props = AccessibilityProperties()
        
        assert props.role == AccessibilityRole.REGION
        assert props.name == ""
        assert props.description == ""
        assert props.value == ""
        assert props.state == AccessibilityState.NORMAL
        assert props.level is None
        assert props.position_in_set is None
        assert props.set_size is None
        assert props.expanded is None
        assert props.selected is None
        assert not props.disabled
        assert not props.hidden
        assert not props.readonly
        assert not props.required
        assert not props.invalid
        assert props.live_region is None
        assert not props.atomic
        assert props.relevant == []
    
    def test_custom_properties(self):
        """Test custom accessibility properties."""
        props = AccessibilityProperties(
            role=AccessibilityRole.BUTTON,
            name="Save Button",
            description="Saves the current document",
            state=AccessibilityState.FOCUSED,
            disabled=False,
            selected=True,
            level=2,
            position_in_set=3,
            set_size=10
        )
        
        assert props.role == AccessibilityRole.BUTTON
        assert props.name == "Save Button"
        assert props.description == "Saves the current document"
        assert props.state == AccessibilityState.FOCUSED
        assert not props.disabled
        assert props.selected
        assert props.level == 2
        assert props.position_in_set == 3
        assert props.set_size == 10


class TestFocusableElement:
    """Test focusable element functionality."""
    
    def test_focusable_element_creation(self):
        """Test focusable element creation."""
        mock_element = Mock()
        props = AccessibilityProperties(
            role=AccessibilityRole.BUTTON,
            name="Test Button"
        )
        bounds = Rectangle(10, 20, 100, 50)
        
        focusable = FocusableElement(
            element=mock_element,
            tab_index=0,
            accessibility_props=props,
            bounds=bounds
        )
        
        assert focusable.element == mock_element
        assert focusable.tab_index == 0
        assert focusable.accessibility_props == props
        assert focusable.bounds == bounds
        assert focusable.parent is None
        assert len(focusable.children) == 0
    
    def test_is_focusable_normal(self):
        """Test normal focusable element."""
        props = AccessibilityProperties(disabled=False, hidden=False)
        focusable = FocusableElement(
            element=Mock(),
            tab_index=0,
            accessibility_props=props,
            bounds=Rectangle(0, 0, 100, 50)
        )
        
        assert focusable.is_focusable()
    
    def test_is_focusable_disabled(self):
        """Test disabled element is not focusable."""
        props = AccessibilityProperties(disabled=True)
        focusable = FocusableElement(
            element=Mock(),
            tab_index=0,
            accessibility_props=props,
            bounds=Rectangle(0, 0, 100, 50)
        )
        
        assert not focusable.is_focusable()
    
    def test_is_focusable_hidden(self):
        """Test hidden element is not focusable."""
        props = AccessibilityProperties(hidden=True)
        focusable = FocusableElement(
            element=Mock(),
            tab_index=0,
            accessibility_props=props,
            bounds=Rectangle(0, 0, 100, 50)
        )
        
        assert not focusable.is_focusable()
    
    def test_is_focusable_negative_tab_index(self):
        """Test element with negative tab index is not focusable."""
        props = AccessibilityProperties()
        focusable = FocusableElement(
            element=Mock(),
            tab_index=-1,
            accessibility_props=props,
            bounds=Rectangle(0, 0, 100, 50)
        )
        
        assert not focusable.is_focusable()


class TestKeyboardNavigator:
    """Test keyboard navigation functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.navigator = KeyboardNavigator()
        
        # Create test focusable elements
        self.elements = []
        for i in range(3):
            props = AccessibilityProperties(
                role=AccessibilityRole.BUTTON,
                name=f"Button {i+1}"
            )
            element = FocusableElement(
                element=Mock(),
                tab_index=i,
                accessibility_props=props,
                bounds=Rectangle(i*100, 0, 80, 40)
            )
            self.elements.append(element)
            self.navigator.add_focusable_element(element)
    
    def test_add_focusable_element(self):
        """Test adding focusable elements."""
        assert len(self.navigator.focusable_elements) == 3
        
        # Elements should be sorted by tab index
        for i, element in enumerate(self.navigator.focusable_elements):
            assert element.tab_index == i
    
    def test_focus_next(self):
        """Test focusing next element."""
        # Start with no focus
        assert self.navigator.current_focus_index == -1
        
        # Focus next should go to first element
        self.navigator.focus_next()
        assert self.navigator.current_focus_index == 0
        
        # Focus next should go to second element
        self.navigator.focus_next()
        assert self.navigator.current_focus_index == 1
        
        # Focus next should go to third element
        self.navigator.focus_next()
        assert self.navigator.current_focus_index == 2
        
        # Focus next should wrap to first element
        self.navigator.focus_next()
        assert self.navigator.current_focus_index == 0
    
    def test_focus_previous(self):
        """Test focusing previous element."""
        # Start at second element
        self.navigator.current_focus_index = 1
        
        # Focus previous should go to first element
        self.navigator.focus_previous()
        assert self.navigator.current_focus_index == 0
        
        # Focus previous should wrap to last element
        self.navigator.focus_previous()
        assert self.navigator.current_focus_index == 2
    
    def test_focus_first(self):
        """Test focusing first element."""
        self.navigator.current_focus_index = 2
        
        self.navigator.focus_first()
        assert self.navigator.current_focus_index == 0
    
    def test_focus_last(self):
        """Test focusing last element."""
        self.navigator.current_focus_index = 0
        
        self.navigator.focus_last()
        assert self.navigator.current_focus_index == 2
    
    def test_clear_focus(self):
        """Test clearing focus."""
        self.navigator.current_focus_index = 1
        
        self.navigator.clear_focus()
        assert self.navigator.current_focus_index == -1
    
    def test_activate_focused(self):
        """Test activating focused element."""
        self.navigator.current_focus_index = 1
        element = self.navigator.focusable_elements[1]
        element.element.activate = Mock()
        
        self.navigator.activate_focused()
        
        element.element.activate.assert_called_once()
    
    def test_key_event_conversion(self):
        """Test key event to string conversion."""
        # Mock key event
        event = Mock()
        event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
        event.text.return_value = "a"
        event.key.return_value = Qt.Key.Key_A
        
        result = self.navigator._key_event_to_string(event)
        
        # Should include modifiers and key
        assert "Ctrl" in result or "Shift" in result
    
    def test_remove_focusable_element(self):
        """Test removing focusable element."""
        element_to_remove = self.elements[1]
        
        self.navigator.remove_focusable_element(element_to_remove)
        
        assert len(self.navigator.focusable_elements) == 2
        assert element_to_remove not in self.navigator.focusable_elements
    
    def test_arrow_navigation(self):
        """Test spatial navigation with arrow keys."""
        # Set current focus
        self.navigator.current_focus_index = 0
        
        # Mock arrow key handling
        handled = self.navigator._handle_arrow_navigation("Right")
        
        # Should attempt to find element to the right
        # Exact behavior depends on element positions
        assert isinstance(handled, bool)


class TestScreenReaderInterfaces:
    """Test screen reader interface implementations."""
    
    def test_mock_screen_reader(self):
        """Test mock screen reader functionality."""
        reader = MockScreenReader()
        
        assert reader.is_available()
        
        reader.announce("Test announcement", "assertive")
        assert len(reader.announcements) == 1
        assert reader.announcements[0] == ("Test announcement", "assertive")
        
        reader.speak("Test speech", True)
        assert len(reader.speeches) == 1
        assert reader.speeches[0] == ("Test speech", True)
        
        reader.stop_speech()
        assert reader.stopped
    
    def test_windows_screen_reader_availability(self):
        """Test Windows screen reader availability check."""
        reader = WindowsScreenReader()
        
        # Availability depends on system configuration
        # Just test that method exists and returns boolean
        assert isinstance(reader.is_available(), bool)
    
    def test_macos_screen_reader_availability(self):
        """Test macOS screen reader availability check."""
        reader = MacOSScreenReader()
        
        # Mock subprocess for testing
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            assert reader.is_available()
            
            mock_run.return_value.returncode = 1
            assert not reader.is_available()
    
    def test_linux_screen_reader_initialization(self):
        """Test Linux screen reader initialization."""
        with patch('src.torematrix.ui.viewer.accessibility.LinuxScreenReader._check_speech_dispatcher', return_value=True), \
             patch('src.torematrix.ui.viewer.accessibility.LinuxScreenReader._check_espeak', return_value=True):
            
            reader = LinuxScreenReader()
            
            assert reader.speech_dispatcher_available
            assert reader.espeak_available
            assert reader.is_available()


class TestAccessibilityManager:
    """Test main accessibility manager functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.mock_overlay_engine = Mock()
        
        # Create manager with mock screen reader
        with patch.object(AccessibilityManager, '_create_screen_reader') as mock_create:
            mock_create.return_value = MockScreenReader()
            self.manager = AccessibilityManager(self.mock_overlay_engine)
    
    def test_initialization(self):
        """Test manager initialization."""
        assert self.manager.overlay_engine == self.mock_overlay_engine
        assert self.manager.screen_reader is not None
        assert self.manager.keyboard_navigator is not None
        assert not self.manager.high_contrast_mode
        assert not self.manager.large_text_mode
        assert not self.manager.reduced_motion
        assert len(self.manager.accessible_elements) == 0
        assert self.manager.screen_reader_active
    
    def test_register_element(self):
        """Test registering element with accessibility properties."""
        mock_element = Mock()
        props = AccessibilityProperties(
            role=AccessibilityRole.BUTTON,
            name="Test Button"
        )
        
        self.manager.register_element(mock_element, props)
        
        assert mock_element in self.manager.accessible_elements
        assert self.manager.accessible_elements[mock_element] == props
    
    def test_unregister_element(self):
        """Test unregistering element."""
        mock_element = Mock()
        props = AccessibilityProperties(role=AccessibilityRole.BUTTON)
        
        self.manager.register_element(mock_element, props)
        assert mock_element in self.manager.accessible_elements
        
        self.manager.unregister_element(mock_element)
        assert mock_element not in self.manager.accessible_elements
    
    def test_announce(self):
        """Test text announcement."""
        test_text = "Test announcement"
        
        self.manager.announce(test_text, "assertive")
        
        # Should queue announcement
        assert len(self.manager.announcement_queue) == 1
        assert self.manager.announcement_queue[0] == (test_text, "assertive")
    
    def test_describe_element(self):
        """Test element description generation."""
        mock_element = Mock()
        props = AccessibilityProperties(
            role=AccessibilityRole.BUTTON,
            name="Save Button",
            description="Saves the document",
            selected=True,
            position_in_set=2,
            set_size=5
        )
        
        self.manager.register_element(mock_element, props)
        description = self.manager.describe_element(mock_element)
        
        assert "button" in description
        assert "Save Button" in description
        assert "selected" in description
        assert "2 of 5" in description
        assert "Saves the document" in description
    
    def test_describe_unknown_element(self):
        """Test description of unknown element."""
        mock_element = Mock()
        
        description = self.manager.describe_element(mock_element)
        
        assert description == "Unknown element"
    
    def test_handle_focus_change(self):
        """Test handling focus change."""
        mock_element = Mock()
        props = AccessibilityProperties(
            role=AccessibilityRole.BUTTON,
            name="Test Button"
        )
        
        self.manager.register_element(mock_element, props)
        
        with patch.object(self.manager, 'announce') as mock_announce:
            self.manager.handle_focus_change(mock_element)
            
            mock_announce.assert_called_once()
            # First argument should be the description
            description = mock_announce.call_args[0][0]
            assert "button" in description
            assert "Test Button" in description
    
    def test_handle_selection_change_single(self):
        """Test handling single element selection."""
        mock_element = Mock()
        props = AccessibilityProperties(name="Test Element")
        
        self.manager.register_element(mock_element, props)
        
        with patch.object(self.manager, 'announce') as mock_announce:
            self.manager.handle_selection_change([mock_element])
            
            mock_announce.assert_called_once_with("Test Element selected", "polite")
    
    def test_handle_selection_change_multiple(self):
        """Test handling multiple element selection."""
        elements = [Mock(), Mock(), Mock()]
        
        with patch.object(self.manager, 'announce') as mock_announce:
            self.manager.handle_selection_change(elements)
            
            mock_announce.assert_called_once_with("3 elements selected", "polite")
    
    def test_handle_selection_change_cleared(self):
        """Test handling selection cleared."""
        with patch.object(self.manager, 'announce') as mock_announce:
            self.manager.handle_selection_change([])
            
            mock_announce.assert_called_once_with("Selection cleared", "polite")
    
    def test_toggle_high_contrast(self):
        """Test toggling high contrast mode."""
        assert not self.manager.high_contrast_mode
        
        with patch.object(self.manager, 'announce') as mock_announce, \
             patch.object(self.manager, '_apply_high_contrast_styles') as mock_apply:
            
            self.manager.toggle_high_contrast()
            
            assert self.manager.high_contrast_mode
            mock_announce.assert_called_once_with(
                "High contrast mode enabled", "assertive"
            )
            mock_apply.assert_called_once()
    
    def test_toggle_large_text(self):
        """Test toggling large text mode."""
        assert not self.manager.large_text_mode
        
        with patch.object(self.manager, 'announce') as mock_announce, \
             patch.object(self.manager, '_apply_large_text_styles') as mock_apply:
            
            self.manager.toggle_large_text()
            
            assert self.manager.large_text_mode
            mock_announce.assert_called_once_with(
                "Large text mode enabled", "assertive"
            )
            mock_apply.assert_called_once()
    
    def test_toggle_reduced_motion(self):
        """Test toggling reduced motion mode."""
        assert not self.manager.reduced_motion
        
        with patch.object(self.manager, 'announce') as mock_announce:
            self.manager.toggle_reduced_motion()
            
            assert self.manager.reduced_motion
            mock_announce.assert_called_once_with(
                "Reduced motion enabled", "assertive"
            )
    
    def test_toggle_screen_reader_announcements(self):
        """Test toggling screen reader announcements."""
        assert self.manager.screen_reader_active
        
        with patch.object(self.manager, 'announce') as mock_announce:
            self.manager.toggle_screen_reader_announcements()
            
            assert not self.manager.screen_reader_active
            mock_announce.assert_called_once_with(
                "Screen reader announcements disabled", "assertive"
            )
    
    def test_validate_wcag_compliance(self):
        """Test WCAG compliance validation."""
        # Register button without name (should be error)
        button_element = Mock()
        button_props = AccessibilityProperties(
            role=AccessibilityRole.BUTTON,
            name="",  # Missing name
            description=""  # Missing description
        )
        self.manager.register_element(button_element, button_props)
        
        # Register proper button
        good_button = Mock()
        good_props = AccessibilityProperties(
            role=AccessibilityRole.BUTTON,
            name="Good Button",
            description="A properly named button"
        )
        self.manager.register_element(good_button, good_props)
        
        issues = self.manager.validate_wcag_compliance()
        
        assert "errors" in issues
        assert "warnings" in issues
        assert "info" in issues
        
        # Should have at least one error for missing name
        assert len(issues["errors"]) >= 1
        assert any("missing accessible name" in error.lower() for error in issues["errors"])
    
    def test_get_accessibility_info(self):
        """Test getting comprehensive accessibility information."""
        info = self.manager.get_accessibility_info()
        
        required_keys = [
            "screen_reader_available",
            "screen_reader_active",
            "high_contrast_mode",
            "large_text_mode",
            "reduced_motion",
            "registered_elements",
            "focusable_elements",
            "wcag_compliance"
        ]
        
        for key in required_keys:
            assert key in info
        
        assert isinstance(info["screen_reader_available"], bool)
        assert isinstance(info["registered_elements"], int)
        assert isinstance(info["wcag_compliance"], dict)


class TestAccessibilityMixin:
    """Test accessibility mixin functionality."""
    
    def test_mixin_initialization(self):
        """Test mixin initialization."""
        
        class TestWidget(AccessibilityMixin):
            def __init__(self):
                super().__init__()
        
        widget = TestWidget()
        
        assert widget.accessibility_props is None
        assert widget.accessibility_manager is None
    
    def test_set_accessibility_properties(self):
        """Test setting accessibility properties."""
        
        class TestWidget(AccessibilityMixin):
            def __init__(self):
                super().__init__()
        
        widget = TestWidget()
        props = AccessibilityProperties(
            role=AccessibilityRole.BUTTON,
            name="Test Button"
        )
        
        widget.set_accessibility_properties(props)
        
        assert widget.accessibility_props == props
    
    def test_set_accessibility_manager(self):
        """Test setting accessibility manager."""
        
        class TestWidget(AccessibilityMixin):
            def __init__(self):
                super().__init__()
        
        widget = TestWidget()
        mock_manager = Mock()
        
        widget.set_accessibility_manager(mock_manager)
        
        assert widget.accessibility_manager == mock_manager
    
    def test_announce_with_manager(self):
        """Test announcement with accessibility manager."""
        
        class TestWidget(AccessibilityMixin):
            def __init__(self):
                super().__init__()
        
        widget = TestWidget()
        mock_manager = Mock()
        widget.set_accessibility_manager(mock_manager)
        
        widget.announce("Test message", "assertive")
        
        mock_manager.announce.assert_called_once_with("Test message", "assertive")


class TestUtilityFunctions:
    """Test utility functions."""
    
    def test_make_accessible(self):
        """Test make_accessible utility function."""
        props = make_accessible(
            Mock(),
            AccessibilityRole.BUTTON,
            "Save Button",
            "Saves the current document"
        )
        
        assert props.role == AccessibilityRole.BUTTON
        assert props.name == "Save Button"
        assert props.description == "Saves the current document"


if __name__ == "__main__":
    pytest.main([__file__])