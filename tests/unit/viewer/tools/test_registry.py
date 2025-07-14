"""
Tests for advanced tool registry system.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QObject

from src.torematrix.ui.viewer.tools.base import SelectionTool, ToolState
from src.torematrix.ui.viewer.tools.registry import (
    ToolCategory, ToolCapability, ToolMetadata, ToolInstance, ToolFactory,
    AdvancedToolRegistry, get_global_tool_registry
)
from src.torematrix.ui.viewer.tools.state import ToolStateManager
from src.torematrix.ui.viewer.tools.cursor import CursorManager
from src.torematrix.ui.viewer.tools.events import EventDispatcher


class MockTool(SelectionTool):
    """Mock tool for testing."""
    
    TOOL_NAME = "mock_tool"
    TOOL_DISPLAY_NAME = "Mock Tool"
    TOOL_DESCRIPTION = "A mock tool for testing"
    TOOL_VERSION = "1.0.0"
    TOOL_AUTHOR = "Test Author"
    TOOL_CATEGORY = "basic"
    TOOL_CAPABILITIES = ["point_selection", "area_selection"]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.activated = False
        self.deactivated = False
        self.cursor_manager = None
        self.event_dispatcher = None
        self.state_manager = None
    
    def activate(self):
        self.activated = True
        self._update_state(ToolState.ACTIVE)
    
    def deactivate(self):
        self.deactivated = True
        self._update_state(ToolState.INACTIVE)
    
    def handle_mouse_press(self, point, modifiers=None):
        return True
    
    def handle_mouse_move(self, point, modifiers=None):
        return True
    
    def handle_mouse_release(self, point, modifiers=None):
        return True
    
    def render_overlay(self, painter, viewport_rect):
        pass
    
    def set_cursor_manager(self, manager):
        self.cursor_manager = manager
    
    def set_event_dispatcher(self, dispatcher):
        self.event_dispatcher = dispatcher
    
    def set_state_manager(self, manager):
        self.state_manager = manager


class TestToolCategory:
    """Test ToolCategory enum."""
    
    def test_tool_categories_exist(self):
        """Test that all tool categories exist."""
        assert ToolCategory.BASIC.value == "basic"
        assert ToolCategory.SELECTION.value == "selection"
        assert ToolCategory.DRAWING.value == "drawing"
        assert ToolCategory.MEASUREMENT.value == "measurement"
        assert ToolCategory.ANNOTATION.value == "annotation"
        assert ToolCategory.CUSTOM.value == "custom"


class TestToolCapability:
    """Test ToolCapability enum."""
    
    def test_tool_capabilities_exist(self):
        """Test that all tool capabilities exist."""
        assert ToolCapability.POINT_SELECTION.value == "point_selection"
        assert ToolCapability.AREA_SELECTION.value == "area_selection"
        assert ToolCapability.MULTI_SELECTION.value == "multi_selection"
        assert ToolCapability.KEYBOARD_SHORTCUTS.value == "keyboard_shortcuts"
        assert ToolCapability.CONTEXT_MENU.value == "context_menu"
        assert ToolCapability.DRAG_AND_DROP.value == "drag_and_drop"
        assert ToolCapability.UNDO_REDO.value == "undo_redo"
        assert ToolCapability.PERSISTENCE.value == "persistence"
        assert ToolCapability.ANIMATION.value == "animation"
        assert ToolCapability.CUSTOM_CURSOR.value == "custom_cursor"


class TestToolMetadata:
    """Test ToolMetadata dataclass."""
    
    def test_tool_metadata_creation(self):
        """Test tool metadata creation."""
        metadata = ToolMetadata(
            name="test_tool",
            display_name="Test Tool",
            description="A test tool",
            version="1.0.0",
            author="Test Author",
            category=ToolCategory.BASIC
        )
        
        assert metadata.name == "test_tool"
        assert metadata.display_name == "Test Tool"
        assert metadata.description == "A test tool"
        assert metadata.version == "1.0.0"
        assert metadata.author == "Test Author"
        assert metadata.category == ToolCategory.BASIC
        assert isinstance(metadata.registration_time, float)
        assert metadata.enabled == True
    
    def test_tool_metadata_with_capabilities(self):
        """Test tool metadata with capabilities."""
        capabilities = {ToolCapability.POINT_SELECTION, ToolCapability.AREA_SELECTION}
        metadata = ToolMetadata(
            name="test_tool",
            display_name="Test Tool",
            description="A test tool",
            capabilities=capabilities
        )
        
        assert metadata.capabilities == capabilities
    
    def test_matches_search(self):
        """Test search matching."""
        metadata = ToolMetadata(
            name="selection_tool",
            display_name="Selection Tool",
            description="Tool for selecting elements",
            keywords=["select", "area", "rectangle"]
        )
        
        # Match in name
        assert metadata.matches_search("selection") == True
        
        # Match in display name
        assert metadata.matches_search("Selection") == True
        
        # Match in description
        assert metadata.matches_search("elements") == True
        
        # Match in keywords
        assert metadata.matches_search("rectangle") == True
        
        # No match
        assert metadata.matches_search("drawing") == False
        
        # Case insensitive
        assert metadata.matches_search("SELECTION") == True


class TestToolInstance:
    """Test ToolInstance dataclass."""
    
    def test_tool_instance_creation(self):
        """Test tool instance creation."""
        tool = MockTool()
        metadata = ToolMetadata(
            name="test_tool",
            display_name="Test Tool",
            description="A test tool"
        )
        
        instance = ToolInstance(tool=tool, metadata=metadata)
        
        assert instance.tool == tool
        assert instance.metadata == metadata
        assert instance.state_manager is None
        assert isinstance(instance.created_time, float)
        assert instance.last_used_time is None
        assert instance.usage_count == 0
    
    def test_mark_used(self):
        """Test marking instance as used."""
        tool = MockTool()
        metadata = ToolMetadata(name="test_tool", display_name="Test Tool", description="Test")
        instance = ToolInstance(tool=tool, metadata=metadata)
        
        assert instance.last_used_time is None
        assert instance.usage_count == 0
        
        instance.mark_used()
        
        assert instance.last_used_time is not None
        assert instance.usage_count == 1
        
        instance.mark_used()
        assert instance.usage_count == 2


class TestToolFactory:
    """Test ToolFactory class."""
    
    def test_tool_factory_creation(self):
        """Test tool factory creation."""
        metadata = ToolMetadata(name="test_tool", display_name="Test Tool", description="Test")
        factory = ToolFactory(MockTool, metadata)
        
        assert factory.tool_class == MockTool
        assert factory.metadata == metadata
        assert factory.get_creation_count() == 0
    
    def test_create_instance(self):
        """Test creating tool instance."""
        metadata = ToolMetadata(name="test_tool", display_name="Test Tool", description="Test")
        factory = ToolFactory(MockTool, metadata)
        
        instance = factory.create_instance()
        
        assert isinstance(instance, ToolInstance)
        assert isinstance(instance.tool, MockTool)
        assert instance.metadata == metadata
        assert factory.get_creation_count() == 1
        
        # Create another instance
        instance2 = factory.create_instance()
        assert factory.get_creation_count() == 2


class TestAdvancedToolRegistry:
    """Test AdvancedToolRegistry class."""
    
    def test_registry_creation(self):
        """Test registry creation."""
        registry = AdvancedToolRegistry()
        
        assert len(registry.get_registered_tools()) == 0
        assert registry.get_active_tool() is None
        assert registry.get_active_tool_name() is None
    
    def test_register_tool_class(self):
        """Test registering tool class."""
        registry = AdvancedToolRegistry()
        metadata = ToolMetadata(name="test_tool", display_name="Test Tool", description="Test")
        
        success = registry.register_tool_class(MockTool, metadata)
        
        assert success == True
        assert "test_tool" in registry.get_registered_tools()
        
        tool_metadata = registry.get_tool_metadata("test_tool")
        assert tool_metadata == metadata
    
    def test_register_duplicate_tool(self):
        """Test registering duplicate tool."""
        registry = AdvancedToolRegistry()
        metadata = ToolMetadata(name="test_tool", display_name="Test Tool", description="Test")
        
        # First registration should succeed
        success1 = registry.register_tool_class(MockTool, metadata)
        assert success1 == True
        
        # Second registration should fail (duplicates not allowed by default)
        success2 = registry.register_tool_class(MockTool, metadata)
        assert success2 == False
    
    def test_register_invalid_tool_class(self):
        """Test registering invalid tool class."""
        registry = AdvancedToolRegistry()
        metadata = ToolMetadata(name="test_tool", display_name="Test Tool", description="Test")
        
        # Try to register non-SelectionTool class
        success = registry.register_tool_class(str, metadata)
        assert success == False
    
    def test_unregister_tool(self):
        """Test unregistering tool."""
        registry = AdvancedToolRegistry()
        metadata = ToolMetadata(name="test_tool", display_name="Test Tool", description="Test")
        
        registry.register_tool_class(MockTool, metadata)
        assert "test_tool" in registry.get_registered_tools()
        
        success = registry.unregister_tool("test_tool")
        assert success == True
        assert "test_tool" not in registry.get_registered_tools()
        
        # Unregister non-existent tool
        success = registry.unregister_tool("nonexistent")
        assert success == False
    
    def test_get_tool_instance(self):
        """Test getting tool instance."""
        registry = AdvancedToolRegistry()
        metadata = ToolMetadata(name="test_tool", display_name="Test Tool", description="Test")
        
        registry.register_tool_class(MockTool, metadata)
        
        # Get instance (should create new one)
        instance = registry.get_tool_instance("test_tool")
        assert isinstance(instance, ToolInstance)
        assert isinstance(instance.tool, MockTool)
        
        # Get same instance again
        instance2 = registry.get_tool_instance("test_tool")
        assert instance2 is instance  # Should be same instance
        
        # Get non-existent tool
        instance3 = registry.get_tool_instance("nonexistent")
        assert instance3 is None
    
    def test_activate_tool(self):
        """Test activating tool."""
        registry = AdvancedToolRegistry()
        metadata = ToolMetadata(name="test_tool", display_name="Test Tool", description="Test")
        
        registry.register_tool_class(MockTool, metadata)
        
        success = registry.activate_tool("test_tool")
        assert success == True
        assert registry.get_active_tool_name() == "test_tool"
        
        active_instance = registry.get_active_tool()
        assert isinstance(active_instance, ToolInstance)
        assert active_instance.tool.activated == True
        
        # Activate non-existent tool
        success = registry.activate_tool("nonexistent")
        assert success == False
    
    def test_deactivate_tool(self):
        """Test deactivating tool."""
        registry = AdvancedToolRegistry()
        metadata = ToolMetadata(name="test_tool", display_name="Test Tool", description="Test")
        
        registry.register_tool_class(MockTool, metadata)
        registry.activate_tool("test_tool")
        
        assert registry.get_active_tool_name() == "test_tool"
        
        success = registry.deactivate_tool()
        assert success == True
        assert registry.get_active_tool_name() is None
        
        # Try to deactivate when no tool is active
        success = registry.deactivate_tool()
        assert success == False
    
    def test_switch_active_tool(self):
        """Test switching active tool."""
        registry = AdvancedToolRegistry()
        
        metadata1 = ToolMetadata(name="tool1", display_name="Tool 1", description="Test")
        metadata2 = ToolMetadata(name="tool2", display_name="Tool 2", description="Test")
        
        registry.register_tool_class(MockTool, metadata1)
        registry.register_tool_class(MockTool, metadata2)
        
        # Activate first tool
        registry.activate_tool("tool1")
        instance1 = registry.get_active_tool()
        assert instance1.tool.activated == True
        
        # Switch to second tool
        registry.activate_tool("tool2")
        instance2 = registry.get_active_tool()
        
        assert registry.get_active_tool_name() == "tool2"
        assert instance1.tool.deactivated == True
        assert instance2.tool.activated == True
    
    def test_unregister_active_tool(self):
        """Test unregistering active tool."""
        registry = AdvancedToolRegistry()
        metadata = ToolMetadata(name="test_tool", display_name="Test Tool", description="Test")
        
        registry.register_tool_class(MockTool, metadata)
        registry.activate_tool("test_tool")
        
        assert registry.get_active_tool_name() == "test_tool"
        
        registry.unregister_tool("test_tool")
        
        assert registry.get_active_tool_name() is None
        assert registry.get_active_tool() is None
    
    def test_search_tools(self):
        """Test searching tools."""
        registry = AdvancedToolRegistry()
        
        metadata1 = ToolMetadata(
            name="selection_tool",
            display_name="Selection Tool",
            description="Tool for selecting elements",
            category=ToolCategory.SELECTION,
            capabilities={ToolCapability.POINT_SELECTION}
        )
        
        metadata2 = ToolMetadata(
            name="drawing_tool",
            display_name="Drawing Tool",
            description="Tool for drawing shapes",
            category=ToolCategory.DRAWING,
            capabilities={ToolCapability.AREA_SELECTION}
        )
        
        registry.register_tool_class(MockTool, metadata1)
        registry.register_tool_class(MockTool, metadata2)
        
        # Search by query
        results = registry.search_tools("selection")
        assert len(results) == 1
        assert results[0].name == "selection_tool"
        
        # Search by category
        results = registry.search_tools("", category=ToolCategory.DRAWING)
        assert len(results) == 1
        assert results[0].name == "drawing_tool"
        
        # Search by capability
        results = registry.search_tools("", capabilities={ToolCapability.POINT_SELECTION})
        assert len(results) == 1
        assert results[0].name == "selection_tool"
    
    def test_get_tools_by_category(self):
        """Test getting tools by category."""
        registry = AdvancedToolRegistry()
        
        metadata1 = ToolMetadata(name="tool1", display_name="Tool 1", description="Test", category=ToolCategory.SELECTION)
        metadata2 = ToolMetadata(name="tool2", display_name="Tool 2", description="Test", category=ToolCategory.DRAWING)
        metadata3 = ToolMetadata(name="tool3", display_name="Tool 3", description="Test", category=ToolCategory.SELECTION)
        
        registry.register_tool_class(MockTool, metadata1)
        registry.register_tool_class(MockTool, metadata2)
        registry.register_tool_class(MockTool, metadata3)
        
        selection_tools = registry.get_tools_by_category(ToolCategory.SELECTION)
        assert len(selection_tools) == 2
        
        drawing_tools = registry.get_tools_by_category(ToolCategory.DRAWING)
        assert len(drawing_tools) == 1
    
    def test_get_tools_by_capability(self):
        """Test getting tools by capability."""
        registry = AdvancedToolRegistry()
        
        metadata1 = ToolMetadata(
            name="tool1", display_name="Tool 1", description="Test",
            capabilities={ToolCapability.POINT_SELECTION, ToolCapability.AREA_SELECTION}
        )
        metadata2 = ToolMetadata(
            name="tool2", display_name="Tool 2", description="Test",
            capabilities={ToolCapability.AREA_SELECTION}
        )
        
        registry.register_tool_class(MockTool, metadata1)
        registry.register_tool_class(MockTool, metadata2)
        
        point_tools = registry.get_tools_by_capability(ToolCapability.POINT_SELECTION)
        assert len(point_tools) == 1
        assert point_tools[0].name == "tool1"
        
        area_tools = registry.get_tools_by_capability(ToolCapability.AREA_SELECTION)
        assert len(area_tools) == 2
    
    def test_enable_disable_tool(self):
        """Test enabling and disabling tools."""
        registry = AdvancedToolRegistry()
        metadata = ToolMetadata(name="test_tool", display_name="Test Tool", description="Test")
        
        registry.register_tool_class(MockTool, metadata)
        
        # Tool should be enabled by default
        tool_metadata = registry.get_tool_metadata("test_tool")
        assert tool_metadata.enabled == True
        
        # Disable tool
        success = registry.disable_tool("test_tool")
        assert success == True
        
        tool_metadata = registry.get_tool_metadata("test_tool")
        assert tool_metadata.enabled == False
        
        # Enable tool
        success = registry.enable_tool("test_tool")
        assert success == True
        
        tool_metadata = registry.get_tool_metadata("test_tool")
        assert tool_metadata.enabled == True
    
    def test_disable_active_tool(self):
        """Test disabling active tool."""
        registry = AdvancedToolRegistry()
        metadata = ToolMetadata(name="test_tool", display_name="Test Tool", description="Test")
        
        registry.register_tool_class(MockTool, metadata)
        registry.activate_tool("test_tool")
        
        assert registry.get_active_tool_name() == "test_tool"
        
        registry.disable_tool("test_tool")
        
        # Should be deactivated
        assert registry.get_active_tool_name() is None
    
    def test_dependencies(self):
        """Test tool dependencies."""
        registry = AdvancedToolRegistry()
        
        # Register dependency first
        dep_metadata = ToolMetadata(name="dependency_tool", display_name="Dependency", description="Test")
        registry.register_tool_class(MockTool, dep_metadata)
        
        # Register tool with dependency
        metadata = ToolMetadata(
            name="dependent_tool",
            display_name="Dependent Tool",
            description="Test",
            dependencies=["dependency_tool"]
        )
        
        success = registry.register_tool_class(MockTool, metadata)
        assert success == True
        
        # Try to register tool with missing dependency
        metadata_bad = ToolMetadata(
            name="bad_tool",
            display_name="Bad Tool",
            description="Test",
            dependencies=["missing_tool"]
        )
        
        success = registry.register_tool_class(MockTool, metadata_bad)
        assert success == False
    
    def test_statistics(self):
        """Test registry statistics."""
        registry = AdvancedToolRegistry()
        metadata = ToolMetadata(name="test_tool", display_name="Test Tool", description="Test")
        
        registry.register_tool_class(MockTool, metadata)
        registry.activate_tool("test_tool")
        
        stats = registry.get_statistics()
        
        assert stats['registered_tools'] == 1
        assert stats['active_instances'] == 1
        assert stats['active_tool'] == "test_tool"
        assert stats['enabled_tools'] == 1
        assert stats['disabled_tools'] == 0
    
    def test_initialization_callbacks(self):
        """Test initialization callbacks."""
        registry = AdvancedToolRegistry()
        
        callback_called = []
        
        def init_callback(tool):
            callback_called.append(tool)
        
        registry.add_initialization_callback("test_tool", init_callback)
        
        metadata = ToolMetadata(name="test_tool", display_name="Test Tool", description="Test")
        registry.register_tool_class(MockTool, metadata)
        
        # Get instance (should trigger callback)
        instance = registry.get_tool_instance("test_tool")
        
        assert len(callback_called) == 1
        assert callback_called[0] is instance.tool
    
    def test_cleanup_callbacks(self):
        """Test cleanup callbacks."""
        registry = AdvancedToolRegistry()
        
        callback_called = []
        
        def cleanup_callback(tool):
            callback_called.append(tool)
        
        registry.add_cleanup_callback("test_tool", cleanup_callback)
        
        metadata = ToolMetadata(name="test_tool", display_name="Test Tool", description="Test")
        registry.register_tool_class(MockTool, metadata)
        
        instance = registry.get_tool_instance("test_tool")
        
        # Unregister (should trigger cleanup)
        registry.unregister_tool("test_tool")
        
        assert len(callback_called) == 1
        assert callback_called[0] is instance.tool
    
    def test_dependency_injection(self):
        """Test dependency injection."""
        registry = AdvancedToolRegistry()
        
        cursor_manager = Mock(spec=CursorManager)
        event_dispatcher = Mock(spec=EventDispatcher)
        
        registry.set_cursor_manager(cursor_manager)
        registry.set_event_dispatcher(event_dispatcher)
        
        metadata = ToolMetadata(name="test_tool", display_name="Test Tool", description="Test")
        registry.register_tool_class(MockTool, metadata)
        
        instance = registry.get_tool_instance("test_tool")
        
        # Check dependencies were injected
        assert instance.tool.cursor_manager is cursor_manager
        assert instance.tool.event_dispatcher is event_dispatcher


class TestGlobalToolRegistry:
    """Test global tool registry functions."""
    
    def test_get_global_tool_registry(self):
        """Test getting global tool registry."""
        registry1 = get_global_tool_registry()
        registry2 = get_global_tool_registry()
        
        # Should be same instance
        assert registry1 is registry2
        assert isinstance(registry1, AdvancedToolRegistry)
    
    def test_global_registry_persistence(self):
        """Test that global registry persists across calls."""
        registry = get_global_tool_registry()
        metadata = ToolMetadata(name="global_test_tool", display_name="Global Test", description="Test")
        
        registry.register_tool_class(MockTool, metadata)
        
        # Get registry again
        registry2 = get_global_tool_registry()
        
        # Should have the tool
        assert "global_test_tool" in registry2.get_registered_tools()


if __name__ == "__main__":
    pytest.main([__file__])