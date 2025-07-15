"""Tests for accessibility features"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence

from torematrix.ui.components.property_panel.accessibility import (
    AccessibilityManager,
    KeyboardShortcutManager,
    FocusIndicator,
    ScreenReaderSupport,
    AccessiblePropertyWidget
)
from torematrix.ui.components.property_panel.events import PropertyNotificationCenter
from torematrix.ui.components.property_panel.models import PropertyMetadata


@pytest.fixture
def qt_app():
    """Create QApplication instance for testing"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def notification_center():
    """Create notification center"""
    return PropertyNotificationCenter()


@pytest.fixture
def accessibility_manager(notification_center):
    """Create accessibility manager"""
    return AccessibilityManager(notification_center)


@pytest.fixture
def test_widget(qt_app):
    """Create test widget"""
    widget = QWidget()
    widget.show()
    return widget


class TestAccessibilityManager:
    """Test accessibility manager"""
    
    def test_initialization(self, accessibility_manager):
        """Test accessibility manager initialization"""
        assert accessibility_manager.enabled is True
        assert isinstance(accessibility_manager.contrast_ratio, float)
        assert isinstance(accessibility_manager.font_scale_factor, float)
    
    def test_enable_disable_accessibility(self, accessibility_manager):
        """Test enabling/disabling accessibility"""
        # Disable accessibility
        accessibility_manager.enable_accessibility(False)
        assert not accessibility_manager.enabled
        
        # Enable accessibility
        accessibility_manager.enable_accessibility(True)
        assert accessibility_manager.enabled
    
    def test_high_contrast_mode(self, accessibility_manager):
        """Test high contrast mode"""
        # Enable high contrast
        accessibility_manager.set_high_contrast_mode(True)
        assert accessibility_manager.high_contrast_mode
        
        # Disable high contrast
        accessibility_manager.set_high_contrast_mode(False)
        assert not accessibility_manager.high_contrast_mode
    
    def test_large_font_mode(self, accessibility_manager):
        """Test large font mode"""
        # Enable large font mode
        accessibility_manager.set_large_font_mode(True, 1.5)
        assert accessibility_manager.large_font_mode
        assert accessibility_manager.font_scale_factor == 1.5
        
        # Disable large font mode
        accessibility_manager.set_large_font_mode(False)
        assert not accessibility_manager.large_font_mode
        assert accessibility_manager.font_scale_factor == 1.0
    
    def test_screen_reader_announcement(self, accessibility_manager):
        """Test screen reader announcements"""
        accessibility_manager.screen_reader_enabled = True
        
        with patch.object(accessibility_manager, 'screen_reader_announcement') as mock_signal:
            accessibility_manager.announce_to_screen_reader("Test announcement")
            mock_signal.emit.assert_called_once_with("Test announcement")
    
    def test_calculate_luminance(self, accessibility_manager):
        """Test luminance calculation"""
        from PyQt6.QtGui import QColor
        
        # Test with white
        white = QColor(255, 255, 255)
        luminance = accessibility_manager._calculate_luminance(white)
        assert 0.9 <= luminance <= 1.0  # White should have high luminance
        
        # Test with black
        black = QColor(0, 0, 0)
        luminance = accessibility_manager._calculate_luminance(black)
        assert 0.0 <= luminance <= 0.1  # Black should have low luminance
    
    def test_set_focus_description(self, accessibility_manager, test_widget):
        """Test setting focus description"""
        description = "Test focus description"
        accessibility_manager.set_focus_description(test_widget, description)
        assert test_widget.accessibleDescription() == description


class TestKeyboardShortcutManager:
    """Test keyboard shortcut manager"""
    
    def test_initialization(self, test_widget):
        """Test shortcut manager initialization"""
        manager = KeyboardShortcutManager(test_widget)
        assert manager.parent_widget == test_widget
        assert manager.enabled is True
        assert len(manager.shortcuts) > 0
    
    def test_add_remove_shortcut(self, test_widget):
        """Test adding and removing shortcuts"""
        manager = KeyboardShortcutManager(test_widget)
        
        # Add custom shortcut
        test_handler = Mock()
        manager.add_shortcut("test_action", "Ctrl+T", test_handler)
        
        assert "test_action" in manager.shortcuts
        
        # Remove shortcut
        manager.remove_shortcut("test_action")
        assert "test_action" not in manager.shortcuts
    
    def test_enable_disable_shortcuts(self, test_widget):
        """Test enabling/disabling shortcuts"""
        manager = KeyboardShortcutManager(test_widget)
        
        # Get initial shortcut count
        initial_count = len(manager.shortcuts)
        
        # Disable shortcuts
        manager.set_enabled(False)
        assert not manager.enabled
        
        # All shortcuts should be disabled
        for shortcut in manager.shortcuts.values():
            assert not shortcut.isEnabled()
        
        # Enable shortcuts
        manager.set_enabled(True)
        assert manager.enabled
        
        # All shortcuts should be enabled
        for shortcut in manager.shortcuts.values():
            assert shortcut.isEnabled()
    
    def test_shortcut_help(self, test_widget):
        """Test shortcut help generation"""
        manager = KeyboardShortcutManager(test_widget)
        help_dict = manager.get_shortcut_help()
        
        assert isinstance(help_dict, dict)
        assert len(help_dict) > 0
        
        # Check that help contains key sequences and descriptions
        for key_sequence, description in help_dict.items():
            assert isinstance(key_sequence, str)
            assert isinstance(description, str)
            assert len(key_sequence) > 0
            assert len(description) > 0
    
    def test_shortcut_activation(self, test_widget):
        """Test shortcut activation"""
        manager = KeyboardShortcutManager(test_widget)
        
        # Mock handler
        test_handler = Mock()
        manager.add_shortcut("test_action", "Ctrl+Shift+T", test_handler)
        
        # Simulate shortcut activation
        with patch.object(manager, 'shortcut_activated') as mock_signal:
            manager._handle_shortcut("test_action", test_handler)
            
            test_handler.assert_called_once()
            mock_signal.emit.assert_called_once_with("test_action", "property_panel")


class TestFocusIndicator:
    """Test focus indicator"""
    
    def test_initialization(self, test_widget):
        """Test focus indicator initialization"""
        indicator = FocusIndicator(test_widget)
        assert indicator.target_widget is None
        assert not indicator.isVisible()
    
    def test_show_focus_for_widget(self, test_widget):
        """Test showing focus for widget"""
        indicator = FocusIndicator(test_widget)
        target_widget = QWidget(test_widget)
        target_widget.resize(100, 50)
        target_widget.show()
        
        indicator.show_focus_for_widget(target_widget)
        
        assert indicator.target_widget == target_widget
        assert indicator.isVisible()
        assert indicator.animation_timer.isActive()
    
    def test_hide_focus(self, test_widget):
        """Test hiding focus"""
        indicator = FocusIndicator(test_widget)
        target_widget = QWidget(test_widget)
        
        # Show focus first
        indicator.show_focus_for_widget(target_widget)
        assert indicator.isVisible()
        
        # Hide focus
        indicator.hide_focus()
        assert not indicator.isVisible()
        assert indicator.target_widget is None
        assert not indicator.animation_timer.isActive()
    
    def test_animation(self, test_widget):
        """Test focus animation"""
        indicator = FocusIndicator(test_widget)
        
        initial_phase = indicator.animation_phase
        indicator._animate_focus()
        
        # Animation phase should change
        assert indicator.animation_phase != initial_phase


class TestScreenReaderSupport:
    """Test screen reader support"""
    
    def test_initialization(self, accessibility_manager):
        """Test screen reader support initialization"""
        support = ScreenReaderSupport(accessibility_manager)
        assert support.accessibility_manager == accessibility_manager
        assert support.current_context == {}
        assert support.announcement_queue == []
    
    def test_announce_property_change(self, accessibility_manager):
        """Test property change announcement"""
        support = ScreenReaderSupport(accessibility_manager)
        
        support.announce_property_change("elem1", "test_prop", "old_value", "new_value")
        
        assert len(support.announcement_queue) == 1
        assert "test_prop" in support.announcement_queue[0]
        assert "old_value" in support.announcement_queue[0]
        assert "new_value" in support.announcement_queue[0]
    
    def test_announce_selection_change(self, accessibility_manager):
        """Test selection change announcement"""
        support = ScreenReaderSupport(accessibility_manager)
        
        # Single element
        support.announce_selection_change(["elem1"], ["prop1", "prop2"])
        assert len(support.announcement_queue) == 1
        assert "1 element" in support.announcement_queue[0]
        
        # Clear queue
        support.announcement_queue.clear()
        
        # Multiple elements
        support.announce_selection_change(["elem1", "elem2"], ["prop1"])
        assert len(support.announcement_queue) == 1
        assert "2 elements" in support.announcement_queue[0]
    
    def test_context_description(self, accessibility_manager):
        """Test context description"""
        support = ScreenReaderSupport(accessibility_manager)
        
        # Empty context
        description = support.get_context_description()
        assert description == "Property panel"
        
        # Set context
        support.set_context({
            "element_count": 3,
            "property_count": 5,
            "current_property": "test_prop"
        })
        
        description = support.get_context_description()
        assert "3 elements" in description
        assert "5 properties" in description
        assert "test_prop" in description
    
    def test_announcement_queue_processing(self, accessibility_manager):
        """Test announcement queue processing"""
        support = ScreenReaderSupport(accessibility_manager)
        
        # Queue multiple announcements
        support._queue_announcement("First announcement")
        support._queue_announcement("Second announcement")
        
        assert len(support.announcement_queue) == 2
        
        # Process queue
        support._process_announcement_queue()
        
        # Should have one less announcement
        assert len(support.announcement_queue) == 1


class TestAccessiblePropertyWidget:
    """Test accessible property widget"""
    
    def test_initialization(self, qt_app):
        """Test accessible widget initialization"""
        metadata = PropertyMetadata(
            name="test_prop",
            display_name="Test Property",
            description="A test property for accessibility testing",
            category="Test"
        )
        
        widget = AccessiblePropertyWidget(metadata)
        widget.show()
        
        assert widget.property_metadata == metadata
        assert widget.accessibleName() == "Test Property"
        assert widget.accessibleDescription() == "A test property for accessibility testing"
    
    def test_focus_events(self, qt_app, accessibility_manager):
        """Test focus event handling"""
        metadata = PropertyMetadata(
            name="test_prop",
            display_name="Test Property",
            description="Test description",
            category="Test"
        )
        
        widget = AccessiblePropertyWidget(metadata)
        widget.set_accessibility_manager(accessibility_manager)
        widget.show()
        
        # Mock focus events
        from PyQt6.QtGui import QFocusEvent
        
        focus_in_event = QFocusEvent(QFocusEvent.Type.FocusIn)
        focus_out_event = QFocusEvent(QFocusEvent.Type.FocusOut)
        
        # Test focus in
        widget.focusInEvent(focus_in_event)
        assert widget.focus_indicator is not None
        
        # Test focus out
        widget.focusOutEvent(focus_out_event)
    
    def test_detailed_description(self, qt_app):
        """Test detailed description generation"""
        metadata = PropertyMetadata(
            name="test_prop",
            display_name="Test Property",
            description="Test description",
            category="Test"
        )
        
        widget = AccessiblePropertyWidget(metadata)
        
        # Add mock get_value method
        widget.get_value = Mock(return_value="test_value")
        
        description = widget.get_detailed_description()
        
        assert "Test Property" in description
        assert "Test description" in description
        assert "test_value" in description


@pytest.mark.integration
class TestAccessibilityIntegration:
    """Integration tests for accessibility features"""
    
    def test_complete_accessibility_workflow(self, qt_app, notification_center):
        """Test complete accessibility workflow"""
        # Create accessibility manager
        manager = AccessibilityManager(notification_center)
        
        # Create test widget
        test_widget = QWidget()
        test_widget.show()
        
        # Create shortcut manager
        shortcut_manager = KeyboardShortcutManager(test_widget)
        
        # Create screen reader support
        screen_reader = ScreenReaderSupport(manager)
        
        # Test workflow
        # 1. Enable accessibility features
        manager.enable_accessibility(True)
        manager.set_high_contrast_mode(True)
        manager.set_large_font_mode(True, 1.25)
        
        # 2. Test focus indicator
        focus_indicator = FocusIndicator(test_widget)
        focus_indicator.show_focus_for_widget(test_widget)
        
        # 3. Test screen reader announcements
        screen_reader.announce_property_change("elem1", "prop1", "old", "new")
        screen_reader.announce_selection_change(["elem1", "elem2"], ["prop1"])
        
        # 4. Test keyboard shortcuts
        help_dict = shortcut_manager.get_shortcut_help()
        assert len(help_dict) > 0
        
        # 5. Test accessible widget
        metadata = PropertyMetadata("test", "Test", "Description", "Category")
        accessible_widget = AccessiblePropertyWidget(metadata, test_widget)
        accessible_widget.set_accessibility_manager(manager)
        
        # Verify everything is properly integrated
        assert manager.enabled
        assert manager.high_contrast_mode
        assert manager.large_font_mode
        assert focus_indicator.isVisible()
        assert len(screen_reader.announcement_queue) > 0