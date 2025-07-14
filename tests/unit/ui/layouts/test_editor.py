"""Tests for layout editor system."""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtCore import QRect, QSize, QPoint, Qt
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPixmap

from src.torematrix.ui.layouts.editor import (
    EditorMode, GridMode, ComponentCategory, ComponentDefinition,
    EditorSettings, SelectionInfo, DragDropHint, ComponentPalette,
    LayoutCanvas, LayoutEditor
)
from src.torematrix.ui.layouts.manager import LayoutManager
from src.torematrix.ui.layouts.animations import AnimationManager
from src.torematrix.core.events import EventBus
from src.torematrix.core.config import ConfigurationManager
from src.torematrix.core.state import Store


class TestComponentDefinition:
    """Test ComponentDefinition class."""
    
    def test_component_definition_creation(self):
        """Test creating component definition."""
        definition = ComponentDefinition(
            id="test_component",
            name="Test Component",
            category=ComponentCategory.PANELS,
            description="A test component",
            default_size=QSize(300, 200),
            min_size=QSize(100, 100),
            max_size=QSize(1000, 800),
            resizable=True,
            properties={"color": "blue", "enabled": True}
        )
        
        assert definition.id == "test_component"
        assert definition.name == "Test Component"
        assert definition.category == ComponentCategory.PANELS
        assert definition.description == "A test component"
        assert definition.default_size == QSize(300, 200)
        assert definition.min_size == QSize(100, 100)
        assert definition.max_size == QSize(1000, 800)
        assert definition.resizable is True
        assert definition.properties == {"color": "blue", "enabled": True}
    
    def test_component_definition_defaults(self):
        """Test component definition with default values."""
        definition = ComponentDefinition(
            id="minimal",
            name="Minimal Component",
            category=ComponentCategory.CONTROLS,
            description="Minimal component"
        )
        
        assert definition.icon_path is None
        assert definition.default_size == QSize(200, 150)
        assert definition.min_size == QSize(50, 50)
        assert definition.max_size == QSize(2000, 2000)
        assert definition.resizable is True
        assert definition.properties == {}
    
    def test_create_widget(self):
        """Test creating widget from definition."""
        definition = ComponentDefinition(
            id="test_widget",
            name="Test Widget",
            category=ComponentCategory.CONTAINERS,
            description="Test widget",
            default_size=QSize(400, 300),
            min_size=QSize(100, 100),
            max_size=QSize(800, 600)
        )
        
        widget = definition.create_widget()
        
        assert isinstance(widget, QWidget)
        assert widget.objectName() == "test_widget"
        assert widget.size() == QSize(400, 300)
        assert widget.minimumSize() == QSize(100, 100)
        assert widget.maximumSize() == QSize(800, 600)


class TestEditorSettings:
    """Test EditorSettings class."""
    
    def test_editor_settings_defaults(self):
        """Test default editor settings."""
        settings = EditorSettings()
        
        assert settings.grid_size == 20
        assert settings.grid_mode == GridMode.SNAP
        assert settings.show_rulers is True
        assert settings.show_guidelines is True
        assert settings.snap_to_grid is True
        assert settings.snap_tolerance == 10
        assert settings.auto_save is True
        assert settings.auto_save_interval == 30
        assert settings.zoom_level == 1.0
        assert settings.min_zoom == 0.25
        assert settings.max_zoom == 4.0
    
    def test_editor_settings_custom(self):
        """Test custom editor settings."""
        settings = EditorSettings(
            grid_size=10,
            grid_mode=GridMode.LINES,
            show_rulers=False,
            snap_to_grid=False,
            auto_save=False,
            zoom_level=2.0
        )
        
        assert settings.grid_size == 10
        assert settings.grid_mode == GridMode.LINES
        assert settings.show_rulers is False
        assert settings.snap_to_grid is False
        assert settings.auto_save is False
        assert settings.zoom_level == 2.0


class TestSelectionInfo:
    """Test SelectionInfo class."""
    
    def test_selection_info_defaults(self):
        """Test default selection info."""
        info = SelectionInfo()
        
        assert len(info.selected_items) == 0
        assert info.primary_selection is None
        assert info.selection_bounds is None
        assert info.multi_select is False
    
    def test_selection_info_with_items(self):
        """Test selection info with items."""
        items = {"item1", "item2", "item3"}
        bounds = QRect(10, 10, 100, 100)
        
        info = SelectionInfo(
            selected_items=items,
            primary_selection="item1",
            selection_bounds=bounds,
            multi_select=True
        )
        
        assert info.selected_items == items
        assert info.primary_selection == "item1"
        assert info.selection_bounds == bounds
        assert info.multi_select is True


class TestDragDropHint:
    """Test DragDropHint class."""
    
    def test_drag_drop_hint_creation(self):
        """Test creating drag drop hint."""
        rect = QRect(10, 10, 100, 50)
        hint = DragDropHint(rect, "insert")
        
        assert hint.rect == rect
        assert hint.hint_type == "insert"
        assert hint.visible is True
    
    def test_drag_drop_hint_default_type(self):
        """Test drag drop hint with default type."""
        rect = QRect(0, 0, 50, 50)
        hint = DragDropHint(rect)
        
        assert hint.hint_type == "insert"
    
    def test_drag_drop_hint_paint(self):
        """Test painting drag drop hint."""
        rect = QRect(10, 10, 100, 50)
        hint = DragDropHint(rect, "replace")
        
        # Mock painter
        painter = Mock()
        painter.save = Mock()
        painter.restore = Mock()
        painter.setPen = Mock()
        painter.setBrush = Mock()
        painter.drawRect = Mock()
        
        hint.paint(painter)
        
        painter.save.assert_called_once()
        painter.restore.assert_called_once()
        painter.setPen.assert_called_once()
        painter.setBrush.assert_called_once()
        painter.drawRect.assert_called_once_with(rect)
    
    def test_drag_drop_hint_paint_invisible(self):
        """Test painting invisible drag drop hint."""
        rect = QRect(10, 10, 100, 50)
        hint = DragDropHint(rect)
        hint.visible = False
        
        painter = Mock()
        hint.paint(painter)
        
        # Should not call any painter methods
        painter.save.assert_not_called()
        painter.restore.assert_not_called()


class TestComponentPalette:
    """Test ComponentPalette class."""
    
    def test_component_palette_initialization(self):
        """Test component palette initialization."""
        palette = ComponentPalette()
        
        assert palette._components is not None
        assert isinstance(palette._components, dict)
        assert len(palette._components) > 0  # Should have default components
    
    def test_register_component(self):
        """Test registering a component."""
        palette = ComponentPalette()
        
        component = ComponentDefinition(
            id="custom_component",
            name="Custom Component",
            category=ComponentCategory.CUSTOM,
            description="A custom component"
        )
        
        initial_count = len(palette._components.get(ComponentCategory.CUSTOM, []))
        palette.register_component(component)
        
        assert ComponentCategory.CUSTOM in palette._components
        assert len(palette._components[ComponentCategory.CUSTOM]) == initial_count + 1
        assert component in palette._components[ComponentCategory.CUSTOM]
    
    def test_get_component_existing(self):
        """Test getting existing component."""
        palette = ComponentPalette()
        
        # Register a known component
        component = ComponentDefinition(
            id="test_component",
            name="Test Component",
            category=ComponentCategory.PANELS,
            description="Test component"
        )
        palette.register_component(component)
        
        result = palette.get_component("test_component")
        
        assert result == component
    
    def test_get_component_nonexistent(self):
        """Test getting non-existent component."""
        palette = ComponentPalette()
        
        result = palette.get_component("nonexistent_component")
        
        assert result is None
    
    def test_default_components_registered(self):
        """Test that default components are registered."""
        palette = ComponentPalette()
        
        # Should have components in various categories
        assert ComponentCategory.CONTAINERS in palette._components
        assert ComponentCategory.PANELS in palette._components
        assert ComponentCategory.VIEWERS in palette._components
        
        # Check specific components
        assert palette.get_component("splitter_horizontal") is not None
        assert palette.get_component("document_viewer") is not None
        assert palette.get_component("pdf_viewer") is not None


class TestLayoutCanvas:
    """Test LayoutCanvas class."""
    
    @pytest.fixture
    def editor_settings(self):
        """Create editor settings."""
        return EditorSettings()
    
    @pytest.fixture
    def layout_canvas(self, editor_settings):
        """Create layout canvas."""
        return LayoutCanvas(editor_settings)
    
    def test_canvas_initialization(self, layout_canvas, editor_settings):
        """Test canvas initialization."""
        assert layout_canvas.settings == editor_settings
        assert len(layout_canvas._components) == 0
        assert len(layout_canvas._selection.selected_items) == 0
        assert layout_canvas._drag_hint is None
        assert layout_canvas._dragging is False
        assert layout_canvas._resizing is False
        assert layout_canvas._rubber_band is None
    
    def test_canvas_setup(self, layout_canvas):
        """Test canvas setup."""
        assert layout_canvas.acceptDrops() is True
        assert layout_canvas.hasMouseTracking() is True
        assert layout_canvas.focusPolicy() == Qt.FocusPolicy.StrongFocus
        assert layout_canvas.minimumSize() == QSize(800, 600)
    
    def test_add_component(self, layout_canvas):
        """Test adding component to canvas."""
        component_def = ComponentDefinition(
            id="test_component",
            name="Test Component",
            category=ComponentCategory.PANELS,
            description="Test component"
        )
        
        geometry = QRect(10, 10, 200, 150)
        
        layout_canvas.add_component("instance_1", component_def, geometry)
        
        assert "instance_1" in layout_canvas._components
        widget = layout_canvas._components["instance_1"]
        assert widget.geometry() == geometry
        assert widget.isVisible() is True
    
    def test_remove_component(self, layout_canvas):
        """Test removing component from canvas."""
        # Add a component first
        component_def = ComponentDefinition(
            id="test_component",
            name="Test Component",
            category=ComponentCategory.PANELS,
            description="Test component"
        )
        
        layout_canvas.add_component("instance_1", component_def, QRect(10, 10, 100, 100))
        
        # Select the component
        layout_canvas._selection.selected_items.add("instance_1")
        layout_canvas._selection.primary_selection = "instance_1"
        
        # Remove the component
        layout_canvas.remove_component("instance_1")
        
        assert "instance_1" not in layout_canvas._components
        assert "instance_1" not in layout_canvas._selection.selected_items
        assert layout_canvas._selection.primary_selection is None
    
    def test_remove_nonexistent_component(self, layout_canvas):
        """Test removing non-existent component."""
        # Should not raise exception
        layout_canvas.remove_component("nonexistent")
        
        assert len(layout_canvas._components) == 0
    
    def test_clear_selection(self, layout_canvas):
        """Test clearing selection."""
        layout_canvas._selection.selected_items = {"item1", "item2"}
        layout_canvas._selection.primary_selection = "item1"
        
        layout_canvas.clear_selection()
        
        assert len(layout_canvas._selection.selected_items) == 0
        assert layout_canvas._selection.primary_selection is None
    
    def test_select_all(self, layout_canvas):
        """Test selecting all components."""
        # Add some components
        component_def = ComponentDefinition(
            id="test_component",
            name="Test Component",
            category=ComponentCategory.PANELS,
            description="Test component"
        )
        
        layout_canvas.add_component("comp1", component_def, QRect(0, 0, 100, 100))
        layout_canvas.add_component("comp2", component_def, QRect(100, 0, 100, 100))
        
        layout_canvas.select_all()
        
        assert layout_canvas._selection.selected_items == {"comp1", "comp2"}
        assert layout_canvas._selection.primary_selection is not None
    
    def test_delete_selected(self, layout_canvas):
        """Test deleting selected components."""
        # Add components
        component_def = ComponentDefinition(
            id="test_component",
            name="Test Component",
            category=ComponentCategory.PANELS,
            description="Test component"
        )
        
        layout_canvas.add_component("comp1", component_def, QRect(0, 0, 100, 100))
        layout_canvas.add_component("comp2", component_def, QRect(100, 0, 100, 100))
        
        # Select one component
        layout_canvas._selection.selected_items = {"comp1"}
        
        layout_canvas.delete_selected()
        
        assert "comp1" not in layout_canvas._components
        assert "comp2" in layout_canvas._components
        assert len(layout_canvas._selection.selected_items) == 0
    
    def test_snap_to_grid(self, layout_canvas):
        """Test snapping to grid."""
        layout_canvas.settings.grid_size = 20
        layout_canvas.settings.snap_to_grid = True
        
        # Test snapping
        delta = QPoint(23, 17)
        snapped = layout_canvas._snap_to_grid(delta)
        
        assert snapped == QPoint(20, 20)
    
    def test_snap_to_grid_disabled(self, layout_canvas):
        """Test snapping when disabled."""
        layout_canvas.settings.snap_to_grid = False
        
        delta = QPoint(23, 17)
        snapped = layout_canvas._snap_to_grid(delta)
        
        assert snapped == delta  # Should return original
    
    def test_constrain_to_canvas(self, layout_canvas):
        """Test constraining rectangle to canvas bounds."""
        layout_canvas.resize(800, 600)
        
        # Test rectangle that goes outside canvas
        rect = QRect(-10, -10, 100, 100)
        constrained = layout_canvas._constrain_to_canvas(rect)
        
        assert constrained.left() >= 0
        assert constrained.top() >= 0
        
        # Test rectangle that goes beyond right/bottom
        rect = QRect(750, 550, 100, 100)
        constrained = layout_canvas._constrain_to_canvas(rect)
        
        assert constrained.right() <= 800
        assert constrained.bottom() <= 600
    
    def test_get_component_at_pos(self, layout_canvas):
        """Test getting component at position."""
        # Add a component
        component_def = ComponentDefinition(
            id="test_component",
            name="Test Component",
            category=ComponentCategory.PANELS,
            description="Test component"
        )
        
        layout_canvas.add_component("comp1", component_def, QRect(50, 50, 100, 100))
        
        # Test position inside component
        assert layout_canvas._get_component_at_pos(QPoint(75, 75)) == "comp1"
        
        # Test position outside component
        assert layout_canvas._get_component_at_pos(QPoint(200, 200)) is None
    
    def test_calculate_resize_rect(self, layout_canvas):
        """Test calculating resize rectangle."""
        original_rect = QRect(50, 50, 100, 100)
        delta = QPoint(10, 20)
        
        # Test southeast handle
        new_rect = layout_canvas._calculate_resize_rect(original_rect, delta, "se")
        assert new_rect == QRect(50, 50, 110, 120)
        
        # Test northwest handle
        new_rect = layout_canvas._calculate_resize_rect(original_rect, delta, "nw")
        assert new_rect == QRect(60, 70, 90, 80)
        
        # Test east handle
        new_rect = layout_canvas._calculate_resize_rect(original_rect, delta, "e")
        assert new_rect == QRect(50, 50, 110, 100)
    
    def test_apply_size_constraints(self, layout_canvas):
        """Test applying size constraints."""
        widget = QWidget()
        widget.setMinimumSize(QSize(50, 50))
        widget.setMaximumSize(QSize(500, 500))
        
        # Test rectangle below minimum
        rect = QRect(0, 0, 30, 30)
        constrained = layout_canvas._apply_size_constraints(rect, widget)
        assert constrained.size() == QSize(50, 50)
        
        # Test rectangle above maximum
        rect = QRect(0, 0, 600, 600)
        constrained = layout_canvas._apply_size_constraints(rect, widget)
        assert constrained.size() == QSize(500, 500)
        
        # Test rectangle within constraints
        rect = QRect(0, 0, 200, 200)
        constrained = layout_canvas._apply_size_constraints(rect, widget)
        assert constrained.size() == QSize(200, 200)


class TestLayoutEditor:
    """Test LayoutEditor class."""
    
    @pytest.fixture
    def layout_manager(self):
        """Create layout manager mock."""
        return Mock(spec=LayoutManager)
    
    @pytest.fixture
    def animation_manager(self):
        """Create animation manager mock."""
        return Mock(spec=AnimationManager)
    
    @pytest.fixture
    def event_bus(self):
        """Create event bus mock."""
        return Mock(spec=EventBus)
    
    @pytest.fixture
    def config_manager(self):
        """Create config manager mock."""
        manager = Mock(spec=ConfigurationManager)
        manager.get_config.return_value = None
        return manager
    
    @pytest.fixture
    def state_manager(self):
        """Create state manager mock."""
        return Mock(spec=Store)
    
    @pytest.fixture
    def layout_editor(self, layout_manager, animation_manager, event_bus, config_manager, state_manager):
        """Create layout editor."""
        return LayoutEditor(
            layout_manager=layout_manager,
            animation_manager=animation_manager,
            event_bus=event_bus,
            config_manager=config_manager,
            state_manager=state_manager
        )
    
    def test_editor_initialization(self, layout_editor):
        """Test editor initialization."""
        assert layout_editor.current_mode == EditorMode.DESIGN
        assert layout_editor.current_layout_id is None
        assert layout_editor.component_palette is None
        assert layout_editor.canvas is None
        assert len(layout_editor._component_definitions) == 0
        assert len(layout_editor._canvas_components) == 0
    
    def test_editor_setup(self, layout_editor):
        """Test editor setup."""
        layout_editor._setup_component()
        
        # Should subscribe to events
        layout_editor.event_bus.subscribe.assert_called()
        
        # Should load settings
        layout_editor.config_manager.get_config.assert_called()
    
    def test_set_editor_mode(self, layout_editor):
        """Test setting editor mode."""
        # Test mode change
        layout_editor.set_editor_mode(EditorMode.PREVIEW)
        
        assert layout_editor.current_mode == EditorMode.PREVIEW
        layout_editor.editor_mode_changed.emit.assert_called_once_with(EditorMode.PREVIEW)
    
    def test_set_editor_mode_same(self, layout_editor):
        """Test setting same editor mode."""
        layout_editor.set_editor_mode(EditorMode.DESIGN)
        
        # Should not emit signal for same mode
        layout_editor.editor_mode_changed.emit.assert_not_called()
    
    def test_set_editor_mode_with_canvas(self, layout_editor):
        """Test setting editor mode with canvas."""
        # Create mock canvas
        layout_editor.canvas = Mock()
        
        # Test preview mode
        layout_editor.set_editor_mode(EditorMode.PREVIEW)
        
        layout_editor.canvas.clear_selection.assert_called_once()
        layout_editor.canvas.setEnabled.assert_called_once_with(False)
        
        # Reset mock
        layout_editor.canvas.reset_mock()
        
        # Test design mode
        layout_editor.set_editor_mode(EditorMode.DESIGN)
        
        layout_editor.canvas.setEnabled.assert_called_once_with(True)
    
    def test_save_layout(self, layout_editor):
        """Test saving layout."""
        layout_editor.current_layout_id = "test_layout"
        
        # Mock the layout creation
        layout_editor._create_layout_configuration = Mock()
        
        result = layout_editor.save_layout("test_layout")
        
        assert result is True
        layout_editor.layout_saved.emit.assert_called_once_with("test_layout")
    
    def test_save_layout_exception(self, layout_editor):
        """Test saving layout with exception."""
        layout_editor.current_layout_id = "test_layout"
        
        # Mock the layout creation to raise exception
        layout_editor._create_layout_configuration = Mock(side_effect=Exception("Test error"))
        
        result = layout_editor.save_layout("test_layout")
        
        assert result is False
        layout_editor.layout_saved.emit.assert_not_called()
    
    def test_load_layout(self, layout_editor):
        """Test loading layout."""
        result = layout_editor.load_layout("test_layout")
        
        assert result is True
        assert layout_editor.current_layout_id == "test_layout"
        layout_editor.layout_loaded.emit.assert_called_once_with("test_layout")
    
    def test_load_layout_exception(self, layout_editor):
        """Test loading layout with exception."""
        # Mock to raise exception
        with patch.object(layout_editor, 'current_layout_id', side_effect=Exception("Test error")):
            result = layout_editor.load_layout("test_layout")
        
        assert result is False
        layout_editor.layout_loaded.emit.assert_not_called()
    
    def test_create_layout_configuration(self, layout_editor):
        """Test creating layout configuration."""
        # Mock canvas
        layout_editor.canvas = Mock()
        layout_editor.canvas.width.return_value = 800
        layout_editor.canvas.height.return_value = 600
        
        config = layout_editor._create_layout_configuration("test_layout")
        
        assert config.id == "test_layout"
        assert config.name == "Layout test_layout"
        assert config.geometry.width == 800
        assert config.geometry.height == 600
    
    def test_create_layout_configuration_no_canvas(self, layout_editor):
        """Test creating layout configuration without canvas."""
        layout_editor.canvas = None
        
        config = layout_editor._create_layout_configuration("test_layout")
        
        assert config.geometry.width == 800  # Default
        assert config.geometry.height == 600  # Default
    
    def test_toggle_grid(self, layout_editor):
        """Test toggling grid."""
        layout_editor._toggle_grid(True)
        
        assert layout_editor.settings.grid_mode == GridMode.SNAP
        
        layout_editor._toggle_grid(False)
        
        assert layout_editor.settings.grid_mode == GridMode.NONE
    
    def test_toggle_snap(self, layout_editor):
        """Test toggling snap."""
        layout_editor._toggle_snap(True)
        
        assert layout_editor.settings.snap_to_grid is True
        
        layout_editor._toggle_snap(False)
        
        assert layout_editor.settings.snap_to_grid is False
    
    def test_on_zoom_changed(self, layout_editor):
        """Test zoom change handling."""
        # Mock canvas
        layout_editor.canvas = Mock()
        layout_editor.canvas.transform.return_value = Mock()
        
        layout_editor._on_zoom_changed(150)  # 150%
        
        assert layout_editor.settings.zoom_level == 1.5
        layout_editor.canvas.transform.assert_called_once()
    
    def test_on_grid_size_changed(self, layout_editor):
        """Test grid size change handling."""
        # Mock canvas
        layout_editor.canvas = Mock()
        
        layout_editor._on_grid_size_changed(30)
        
        assert layout_editor.settings.grid_size == 30
        layout_editor.canvas.update.assert_called_once()
    
    def test_on_component_requested(self, layout_editor):
        """Test component request handling."""
        # Mock palette and canvas
        layout_editor.component_palette = Mock()
        layout_editor.canvas = Mock()
        layout_editor.canvas.rect.return_value = QRect(0, 0, 800, 600)
        
        # Mock component definition
        component_def = Mock()
        component_def.default_size = QSize(200, 150)
        layout_editor.component_palette.get_component.return_value = component_def
        
        layout_editor._on_component_requested("test_component")
        
        # Should add component to canvas
        layout_editor.canvas.add_component.assert_called_once()
        
        # Should store component definition
        assert len(layout_editor._component_definitions) == 1
        assert len(layout_editor._canvas_components) == 1
    
    def test_on_component_added(self, layout_editor):
        """Test component added handling."""
        # Mock palette
        layout_editor.component_palette = Mock()
        component_def = Mock()
        layout_editor.component_palette.get_component.return_value = component_def
        
        # Mock canvas
        layout_editor.canvas = Mock()
        
        geometry = QRect(10, 10, 200, 150)
        layout_editor._on_component_added("test_component", geometry)
        
        # Should add component to canvas
        layout_editor.canvas.add_component.assert_called_once()
        
        # Should store component definition
        assert len(layout_editor._component_definitions) == 1
        assert len(layout_editor._canvas_components) == 1
    
    def test_on_selection_changed(self, layout_editor):
        """Test selection change handling."""
        selected_items = ["item1", "item2"]
        
        layout_editor._on_selection_changed(selected_items)
        
        # Should log the selection (no other behavior in current implementation)
        # Test passes if no exception is raised
    
    def test_on_component_moved(self, layout_editor):
        """Test component moved handling."""
        geometry = QRect(50, 50, 200, 150)
        
        layout_editor._on_component_moved("test_component", geometry)
        
        # Should log the movement (no other behavior in current implementation)
        # Test passes if no exception is raised
    
    def test_on_component_resized(self, layout_editor):
        """Test component resized handling."""
        size = QSize(300, 200)
        
        layout_editor._on_component_resized("test_component", size)
        
        # Should log the resize (no other behavior in current implementation)
        # Test passes if no exception is raised
    
    def test_on_layout_modified(self, layout_editor):
        """Test layout modified handling."""
        layout_editor.settings.auto_save = True
        layout_editor.current_layout_id = "test_layout"
        
        with patch('PyQt6.QtCore.QTimer.singleShot') as mock_timer:
            layout_editor._on_layout_modified()
            
            # Should schedule auto-save
            mock_timer.assert_called_once()
    
    def test_on_layout_modified_no_auto_save(self, layout_editor):
        """Test layout modified without auto-save."""
        layout_editor.settings.auto_save = False
        
        with patch('PyQt6.QtCore.QTimer.singleShot') as mock_timer:
            layout_editor._on_layout_modified()
            
            # Should not schedule auto-save
            mock_timer.assert_not_called()
    
    def test_auto_save_layout(self, layout_editor):
        """Test auto-save layout."""
        layout_editor.current_layout_id = "test_layout"
        layout_editor.save_layout = Mock(return_value=True)
        
        layout_editor._auto_save_layout()
        
        layout_editor.save_layout.assert_called_once_with("test_layout")
    
    def test_auto_save_layout_no_current_layout(self, layout_editor):
        """Test auto-save without current layout."""
        layout_editor.current_layout_id = None
        layout_editor.save_layout = Mock()
        
        layout_editor._auto_save_layout()
        
        layout_editor.save_layout.assert_not_called()


def test_editor_mode_enum():
    """Test EditorMode enumeration."""
    assert EditorMode.DESIGN is not None
    assert EditorMode.PREVIEW is not None
    assert EditorMode.CODE is not None


def test_grid_mode_enum():
    """Test GridMode enumeration."""
    assert GridMode.NONE is not None
    assert GridMode.DOTS is not None
    assert GridMode.LINES is not None
    assert GridMode.SNAP is not None


def test_component_category_enum():
    """Test ComponentCategory enumeration."""
    assert ComponentCategory.CONTAINERS is not None
    assert ComponentCategory.PANELS is not None
    assert ComponentCategory.VIEWERS is not None
    assert ComponentCategory.CONTROLS is not None
    assert ComponentCategory.CUSTOM is not None