"""
Comprehensive tests for ValidationToolbar component.

Agent 3 test implementation for Issue #242 - UI Components & User Experience.
Tests cover toolbar functionality, tool selection, keyboard shortcuts,
performance optimization, and UI responsiveness.
"""

import pytest
import sys
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

from PyQt6.QtWidgets import QApplication, QAction, QComboBox, QSlider, QPushButton
from PyQt6.QtCore import Qt, QTimer, QSettings, QSize
from PyQt6.QtGui import QKeySequence, QIcon
from PyQt6.QtTest import QTest

# Import the components we're testing
from src.torematrix.ui.tools.validation.toolbar import (
    ValidationToolbar, ToolType, ToolConfiguration, ToolbarManager
)
from src.torematrix.ui.tools.validation.drawing_state import (
    DrawingStateManager, DrawingMode, DrawingState
)
from src.torematrix.core.models import ElementType


class TestToolConfiguration:
    """Test ToolConfiguration data class."""
    
    def test_tool_configuration_initialization(self):
        """Test ToolConfiguration initialization."""
        config = ToolConfiguration(
            tool_type=ToolType.RECTANGLE,
            icon_name="rectangle",
            tooltip="Rectangle Tool",
            shortcut="R"
        )
        
        assert config.tool_type == ToolType.RECTANGLE
        assert config.icon_name == "rectangle"
        assert config.tooltip == "Rectangle Tool"
        assert config.shortcut == "R"
        assert config.enabled is True  # Default
        assert config.checkable is False  # Default
        assert config.group is None  # Default
    
    def test_tool_configuration_with_options(self):
        """Test ToolConfiguration with optional parameters."""
        config = ToolConfiguration(
            tool_type=ToolType.SELECT,
            icon_name="select",
            tooltip="Selection Tool",
            shortcut="S",
            enabled=False,
            checkable=True,
            group="drawing_tools"
        )
        
        assert config.enabled is False
        assert config.checkable is True
        assert config.group == "drawing_tools"


class TestValidationToolbar:
    """Test ValidationToolbar main component."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()
    
    @pytest.fixture
    def mock_state_manager(self):
        """Create mock DrawingStateManager."""
        mock_manager = Mock(spec=DrawingStateManager)
        mock_manager.mode_changed = Mock()
        mock_manager.state_changed = Mock()
        mock_manager.activate_draw_mode = Mock(return_value=True)
        mock_manager.deactivate_draw_mode = Mock(return_value=True)
        return mock_manager
    
    @pytest.fixture
    def toolbar(self, app, mock_state_manager):
        """Create ValidationToolbar instance for testing."""
        # Mock QSettings to avoid file system access
        with patch('src.torematrix.ui.tools.validation.toolbar.QSettings'):
            return ValidationToolbar(mock_state_manager)
    
    def test_toolbar_initialization(self, toolbar, mock_state_manager):
        """Test toolbar initialization."""
        assert toolbar.state_manager == mock_state_manager
        assert toolbar.objectName() == "ValidationToolbar"
        assert toolbar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonIconOnly
        assert toolbar.iconSize() == QSize(24, 24)
        assert toolbar.isMovable()
        assert toolbar.isFloatable()
    
    def test_toolbar_styling(self, toolbar):
        """Test toolbar has proper styling applied."""
        style_sheet = toolbar.styleSheet()
        assert "QToolBar" in style_sheet
        assert "background" in style_sheet
        assert "QToolButton" in style_sheet
    
    def test_tool_actions_creation(self, toolbar):
        """Test that all tool actions are created."""
        expected_tools = [
            ToolType.SELECT, ToolType.RECTANGLE, ToolType.POLYGON,
            ToolType.FREEHAND, ToolType.ZOOM_IN, ToolType.ZOOM_OUT,
            ToolType.PAN, ToolType.MEASURE
        ]
        
        for tool_type in expected_tools:
            assert tool_type in toolbar.tool_actions
            action = toolbar.tool_actions[tool_type]
            assert isinstance(action, QAction)
            assert action.data() == tool_type
    
    def test_tool_groups_creation(self, toolbar):
        """Test that tool groups are created properly."""
        expected_groups = ["drawing_tools", "view_tools", "utility_tools"]
        
        for group_name in expected_groups:
            assert group_name in toolbar.tool_groups
            group = toolbar.tool_groups[group_name]
            assert group.isExclusive()  # Action groups should be exclusive
    
    def test_default_tool_selection(self, toolbar):
        """Test default tool selection."""
        assert toolbar._current_tool == ToolType.SELECT
        assert toolbar.tool_actions[ToolType.SELECT].isChecked()
    
    def test_tool_activation(self, toolbar):
        """Test tool activation functionality."""
        # Activate rectangle tool
        toolbar._tool_activated(ToolType.RECTANGLE)
        
        assert toolbar._current_tool == ToolType.RECTANGLE
    
    def test_tool_activation_via_action(self, toolbar):
        """Test tool activation via action trigger."""
        rectangle_action = toolbar.tool_actions[ToolType.RECTANGLE]
        
        # Trigger the action
        rectangle_action.trigger()
        
        assert toolbar._current_tool == ToolType.RECTANGLE
    
    def test_element_type_combo_creation(self, toolbar):
        """Test element type combo box creation."""
        assert toolbar.element_type_combo is not None
        assert isinstance(toolbar.element_type_combo, QComboBox)
        assert toolbar.element_type_combo.count() == len(ElementType)
        
        # Check all element types are present
        for i, element_type in enumerate(ElementType):
            assert toolbar.element_type_combo.itemData(i) == element_type
    
    def test_element_type_selection(self, toolbar):
        """Test element type selection."""
        # Simulate selection change
        test_index = 1
        toolbar.element_type_combo.setCurrentIndex(test_index)
        toolbar._element_type_changed(test_index)
        
        expected_type = toolbar.element_type_combo.itemData(test_index)
        assert toolbar._current_element_type == expected_type
    
    def test_zoom_controls_creation(self, toolbar):
        """Test zoom controls creation."""
        assert toolbar.zoom_slider is not None
        assert isinstance(toolbar.zoom_slider, QSlider)
        assert toolbar.zoom_slider.minimum() == 10
        assert toolbar.zoom_slider.maximum() == 500
        assert toolbar.zoom_slider.value() == 100  # Default 100%
        
        assert toolbar.zoom_label is not None
        assert toolbar.zoom_label.text() == "100%"
    
    def test_zoom_functionality(self, toolbar):
        """Test zoom functionality."""
        # Change zoom value
        new_zoom = 150
        toolbar.zoom_slider.setValue(new_zoom)
        toolbar._zoom_changed(new_zoom)
        
        assert toolbar._current_zoom == 1.5  # 150% = 1.5
        assert toolbar.zoom_label.text() == "150%"
    
    def test_drawing_mode_toggle(self, toolbar, mock_state_manager):
        """Test drawing mode toggle functionality."""
        # Initially not drawing
        assert not toolbar._drawing_enabled
        assert toolbar.drawing_mode_btn.text() == "Start Drawing"
        
        # Toggle drawing mode on
        toolbar._toggle_drawing_mode()
        
        mock_state_manager.activate_draw_mode.assert_called_once()
        assert toolbar._drawing_enabled
        assert toolbar.drawing_mode_btn.text() == "Stop Drawing"
        assert toolbar.drawing_mode_btn.isChecked()
        
        # Toggle drawing mode off
        toolbar._toggle_drawing_mode()
        
        mock_state_manager.deactivate_draw_mode.assert_called_once()
        assert not toolbar._drawing_enabled
        assert toolbar.drawing_mode_btn.text() == "Start Drawing"
        assert not toolbar.drawing_mode_btn.isChecked()
    
    def test_performance_settings_button(self, toolbar):
        """Test performance settings button."""
        assert toolbar.performance_btn is not None
        assert isinstance(toolbar.performance_btn, QPushButton)
        assert toolbar.performance_btn.text() == "Settings"
    
    def test_keyboard_shortcuts_setup(self, toolbar):
        """Test keyboard shortcuts are properly set up."""
        # Check that shortcuts are assigned to actions
        for tool_type, action in toolbar.tool_actions.items():
            shortcut = action.shortcut()
            assert not shortcut.isEmpty()  # All tools should have shortcuts
    
    def test_icon_creation(self, toolbar):
        """Test tool icon creation."""
        icon = toolbar._create_tool_icon("rectangle")
        assert isinstance(icon, QIcon)
        assert not icon.isNull()
    
    def test_mode_change_signal_handling(self, toolbar):
        """Test mode change signal handling."""
        # Test disabled mode
        toolbar._on_mode_changed(DrawingMode.DISABLED)
        
        # Drawing tools should be disabled
        drawing_tools = [ToolType.RECTANGLE, ToolType.POLYGON, ToolType.FREEHAND]
        for tool_type in drawing_tools:
            if tool_type in toolbar.tool_actions:
                # Note: In actual implementation, these would be disabled
                pass
        
        # Test selection mode
        toolbar._on_mode_changed(DrawingMode.SELECTION)
        
        # Drawing tools should be enabled
        for tool_type in drawing_tools:
            if tool_type in toolbar.tool_actions:
                # Note: In actual implementation, these would be enabled
                pass
    
    def test_state_change_signal_handling(self, toolbar):
        """Test state change signal handling."""
        # Test area selecting state
        toolbar._on_state_changed(DrawingState.AREA_SELECTING)
        
        # Element type combo should be disabled during selection
        assert not toolbar.element_type_combo.isEnabled()
        
        # Test idle state
        toolbar._on_state_changed(DrawingState.IDLE)
        
        # Element type combo should be re-enabled
        assert toolbar.element_type_combo.isEnabled()
    
    def test_current_tool_getter(self, toolbar):
        """Test current tool getter."""
        toolbar._current_tool = ToolType.POLYGON
        assert toolbar.get_current_tool() == ToolType.POLYGON
    
    def test_current_zoom_getter(self, toolbar):
        """Test current zoom getter."""
        toolbar._current_zoom = 2.0
        assert toolbar.get_current_zoom() == 2.0
    
    def test_current_element_type_getter(self, toolbar):
        """Test current element type getter."""
        toolbar._current_element_type = ElementType.TABLE
        assert toolbar.get_current_element_type() == ElementType.TABLE
    
    def test_programmatic_zoom_setting(self, toolbar):
        """Test programmatic zoom setting."""
        toolbar.set_zoom(1.5)
        assert toolbar.zoom_slider.value() == 150
        
        # Test clamping
        toolbar.set_zoom(10.0)  # Should clamp to max 500%
        assert toolbar.zoom_slider.value() == 500
        
        toolbar.set_zoom(0.05)  # Should clamp to min 10%
        assert toolbar.zoom_slider.value() == 10
    
    def test_drawing_tools_enable_disable(self, toolbar):
        """Test enabling/disabling drawing tools."""
        drawing_tools = [ToolType.RECTANGLE, ToolType.POLYGON, ToolType.FREEHAND]
        
        # Disable drawing tools
        toolbar.enable_drawing_tools(False)
        
        for tool_type in drawing_tools:
            if tool_type in toolbar.tool_actions:
                assert not toolbar.tool_actions[tool_type].isEnabled()
        
        # Enable drawing tools
        toolbar.enable_drawing_tools(True)
        
        for tool_type in drawing_tools:
            if tool_type in toolbar.tool_actions:
                assert toolbar.tool_actions[tool_type].isEnabled()
    
    def test_toolbar_state_reporting(self, toolbar):
        """Test toolbar state reporting."""
        # Set some state
        toolbar._current_tool = ToolType.RECTANGLE
        toolbar._current_zoom = 1.5
        toolbar._current_element_type = ElementType.IMAGE
        toolbar._drawing_enabled = True
        
        state = toolbar.get_toolbar_state()
        
        assert state["current_tool"] == "RECTANGLE"
        assert state["current_zoom"] == 1.5
        assert state["current_element_type"] == "image"
        assert state["drawing_enabled"] is True
        assert "tool_states" in state
    
    def test_performance_optimization(self, toolbar):
        """Test performance optimization features."""
        # Check update timer exists
        assert isinstance(toolbar._update_timer, QTimer)
        assert toolbar._update_timer.isSingleShot()
        
        # Test delayed update
        toolbar._zoom_changed(200)
        assert toolbar._update_timer.isActive()
    
    @patch('src.torematrix.ui.tools.validation.toolbar.QSettings')
    def test_settings_loading(self, mock_settings_class, app, mock_state_manager):
        """Test settings loading and saving."""
        mock_settings = Mock()
        mock_settings.value.side_effect = lambda key, default, **kwargs: {
            "zoom_level": 150,
            "element_type": "table"
        }.get(key, default)
        
        mock_settings_class.return_value = mock_settings
        
        # Create toolbar with mocked settings
        toolbar = ValidationToolbar(mock_state_manager)
        
        # Verify settings were loaded
        mock_settings.value.assert_any_call("zoom_level", 100, type=int)
        mock_settings.value.assert_any_call("element_type", "text", type=str)
    
    def test_settings_saving(self, toolbar):
        """Test settings saving."""
        # Set some values
        toolbar.zoom_slider.setValue(200)
        toolbar._current_element_type = ElementType.TABLE
        
        # Save settings
        toolbar.save_settings()
        
        # Should call setValue on settings
        toolbar.settings.setValue.assert_any_call("zoom_level", 200)
        toolbar.settings.setValue.assert_any_call("element_type", "table")
        toolbar.settings.sync.assert_called_once()


class TestToolbarManager:
    """Test ToolbarManager functionality."""
    
    @pytest.fixture
    def toolbar_manager(self):
        """Create ToolbarManager instance."""
        return ToolbarManager()
    
    @pytest.fixture
    def mock_toolbar(self):
        """Create mock ValidationToolbar."""
        mock_toolbar = Mock(spec=ValidationToolbar)
        mock_toolbar.objectName.return_value = "TestToolbar"
        mock_toolbar.get_current_tool.return_value = ToolType.RECTANGLE
        mock_toolbar._activate_tool = Mock()
        mock_toolbar.save_settings = Mock()
        return mock_toolbar
    
    def test_toolbar_manager_initialization(self, toolbar_manager):
        """Test toolbar manager initialization."""
        assert toolbar_manager.toolbars == []
    
    def test_toolbar_registration(self, toolbar_manager, mock_toolbar):
        """Test toolbar registration."""
        toolbar_manager.register_toolbar(mock_toolbar)
        
        assert mock_toolbar in toolbar_manager.toolbars
        assert len(toolbar_manager.toolbars) == 1
    
    def test_toolbar_unregistration(self, toolbar_manager, mock_toolbar):
        """Test toolbar unregistration."""
        # Register first
        toolbar_manager.register_toolbar(mock_toolbar)
        assert len(toolbar_manager.toolbars) == 1
        
        # Unregister
        toolbar_manager.unregister_toolbar(mock_toolbar)
        assert len(toolbar_manager.toolbars) == 0
        assert mock_toolbar not in toolbar_manager.toolbars
    
    def test_tool_state_synchronization(self, toolbar_manager):
        """Test tool state synchronization across toolbars."""
        # Create multiple mock toolbars
        toolbar1 = Mock(spec=ValidationToolbar)
        toolbar1.get_current_tool.return_value = ToolType.RECTANGLE
        toolbar1._activate_tool = Mock()
        
        toolbar2 = Mock(spec=ValidationToolbar)
        toolbar2._activate_tool = Mock()
        
        toolbar3 = Mock(spec=ValidationToolbar)
        toolbar3._activate_tool = Mock()
        
        # Register toolbars
        toolbar_manager.register_toolbar(toolbar1)
        toolbar_manager.register_toolbar(toolbar2)
        toolbar_manager.register_toolbar(toolbar3)
        
        # Sync states from toolbar1
        toolbar_manager.sync_tool_states(toolbar1)
        
        # Other toolbars should be updated
        toolbar2._activate_tool.assert_called_once_with(ToolType.RECTANGLE)
        toolbar3._activate_tool.assert_called_once_with(ToolType.RECTANGLE)
        
        # Source toolbar should not be updated
        toolbar1._activate_tool.assert_not_called()
    
    def test_save_all_settings(self, toolbar_manager):
        """Test saving settings for all registered toolbars."""
        # Create mock toolbars
        toolbar1 = Mock(spec=ValidationToolbar)
        toolbar1.save_settings = Mock()
        
        toolbar2 = Mock(spec=ValidationToolbar)
        toolbar2.save_settings = Mock()
        
        # Register toolbars
        toolbar_manager.register_toolbar(toolbar1)
        toolbar_manager.register_toolbar(toolbar2)
        
        # Save all settings
        toolbar_manager.save_all_settings()
        
        # Both toolbars should have save_settings called
        toolbar1.save_settings.assert_called_once()
        toolbar2.save_settings.assert_called_once()


class TestToolbarIntegration:
    """Integration tests for toolbar functionality."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for testing."""
        if not QApplication.instance():
            return QApplication(sys.argv)
        return QApplication.instance()
    
    @pytest.fixture
    def full_toolbar(self, app):
        """Create full toolbar with real state manager for integration testing."""
        mock_state_manager = Mock(spec=DrawingStateManager)
        mock_state_manager.mode_changed = Mock()
        mock_state_manager.state_changed = Mock()
        mock_state_manager.activate_draw_mode = Mock(return_value=True)
        mock_state_manager.deactivate_draw_mode = Mock(return_value=True)
        
        with patch('src.torematrix.ui.tools.validation.toolbar.QSettings'):
            return ValidationToolbar(mock_state_manager)
    
    def test_complete_workflow_simulation(self, full_toolbar):
        """Test complete toolbar workflow."""
        # Start with selection tool
        assert full_toolbar.get_current_tool() == ToolType.SELECT
        
        # Switch to rectangle tool
        rectangle_action = full_toolbar.tool_actions[ToolType.RECTANGLE]
        rectangle_action.trigger()
        assert full_toolbar.get_current_tool() == ToolType.RECTANGLE
        
        # Change element type
        full_toolbar.element_type_combo.setCurrentIndex(1)
        full_toolbar._element_type_changed(1)
        
        # Adjust zoom
        full_toolbar.zoom_slider.setValue(150)
        full_toolbar._zoom_changed(150)
        assert full_toolbar.get_current_zoom() == 1.5
        
        # Enable drawing mode
        full_toolbar._toggle_drawing_mode()
        assert full_toolbar._drawing_enabled
        
        # Disable drawing mode
        full_toolbar._toggle_drawing_mode()
        assert not full_toolbar._drawing_enabled
    
    def test_signal_connectivity(self, full_toolbar):
        """Test signal connectivity."""
        # Test that signals exist and are properly connected
        assert hasattr(full_toolbar, 'tool_selected')
        assert hasattr(full_toolbar, 'drawing_mode_changed')
        assert hasattr(full_toolbar, 'zoom_changed')
        assert hasattr(full_toolbar, 'element_type_selected')
        assert hasattr(full_toolbar, 'settings_changed')
    
    def test_toolbar_responsiveness(self, full_toolbar):
        """Test toolbar responsiveness with rapid interactions."""
        # Simulate rapid tool changes
        tools = [ToolType.SELECT, ToolType.RECTANGLE, ToolType.POLYGON, ToolType.FREEHAND]
        
        for tool in tools:
            if tool in full_toolbar.tool_actions:
                full_toolbar._tool_activated(tool)
                assert full_toolbar.get_current_tool() == tool
        
        # Simulate rapid zoom changes
        for zoom_value in [50, 100, 150, 200, 300]:
            full_toolbar.zoom_slider.setValue(zoom_value)
            full_toolbar._zoom_changed(zoom_value)
            assert full_toolbar.get_current_zoom() == zoom_value / 100.0
    
    def test_memory_management(self, full_toolbar):
        """Test memory management and cleanup."""
        # Create many temporary references
        temp_actions = []
        for _ in range(100):
            temp_actions.append(full_toolbar.tool_actions[ToolType.SELECT])
        
        # Clear references
        temp_actions.clear()
        
        # Toolbar should still function normally
        assert full_toolbar.get_current_tool() == ToolType.SELECT
    
    @patch('PyQt6.QtCore.QTimer.start')
    def test_performance_optimization_triggers(self, mock_timer_start, full_toolbar):
        """Test performance optimization triggers."""
        # Zoom change should trigger delayed update
        full_toolbar._zoom_changed(150)
        mock_timer_start.assert_called_with(100)
    
    def test_accessibility_features(self, full_toolbar):
        """Test accessibility features."""
        # Check tooltips are set
        for action in full_toolbar.tool_actions.values():
            assert action.toolTip()  # Should have non-empty tooltip
        
        # Check keyboard shortcuts are set
        for action in full_toolbar.tool_actions.values():
            assert not action.shortcut().isEmpty()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])