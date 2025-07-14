"""Tests for layout utilities."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QSplitter, QScrollArea, QFrame, QPushButton, QLabel
)
from PyQt6.QtCore import Qt, QSize, QMargins

from torematrix.ui.utils.layout_utils import (
    LayoutUtilities, FlexDirection, FlexWrap, JustifyContent, 
    AlignItems, MasonryLayout, ResponsiveImageGrid
)


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestEnums:
    """Test layout utility enums."""
    
    def test_flex_direction_enum(self):
        """Test FlexDirection enum values."""
        assert FlexDirection.ROW.value == "row"
        assert FlexDirection.COLUMN.value == "column"
        assert FlexDirection.ROW_REVERSE.value == "row-reverse"
        assert FlexDirection.COLUMN_REVERSE.value == "column-reverse"
    
    def test_flex_wrap_enum(self):
        """Test FlexWrap enum values."""
        assert FlexWrap.NO_WRAP.value == "nowrap"
        assert FlexWrap.WRAP.value == "wrap"
        assert FlexWrap.WRAP_REVERSE.value == "wrap-reverse"
    
    def test_justify_content_enum(self):
        """Test JustifyContent enum values."""
        assert JustifyContent.FLEX_START.value == "flex-start"
        assert JustifyContent.FLEX_END.value == "flex-end"
        assert JustifyContent.CENTER.value == "center"
        assert JustifyContent.SPACE_BETWEEN.value == "space-between"
        assert JustifyContent.SPACE_AROUND.value == "space-around"
        assert JustifyContent.SPACE_EVENLY.value == "space-evenly"
    
    def test_align_items_enum(self):
        """Test AlignItems enum values."""
        assert AlignItems.FLEX_START.value == "flex-start"
        assert AlignItems.FLEX_END.value == "flex-end"
        assert AlignItems.CENTER.value == "center"
        assert AlignItems.STRETCH.value == "stretch"
        assert AlignItems.BASELINE.value == "baseline"


class TestLayoutUtilities:
    """Test LayoutUtilities static methods."""
    
    def test_create_flex_layout_row(self, app):
        """Test creating row flex layout."""
        layout = LayoutUtilities.create_flex_layout(
            direction=FlexDirection.ROW,
            spacing=8
        )
        
        assert isinstance(layout, QHBoxLayout)
        assert layout.spacing() == 8
    
    def test_create_flex_layout_column(self, app):
        """Test creating column flex layout."""
        layout = LayoutUtilities.create_flex_layout(
            direction=FlexDirection.COLUMN,
            spacing=12
        )
        
        assert isinstance(layout, QVBoxLayout)
        assert layout.spacing() == 12
    
    def test_add_flex_item(self, app):
        """Test adding items to flex layout."""
        layout = LayoutUtilities.create_flex_layout()
        widget = QWidget()
        
        # Add item with flex grow
        LayoutUtilities.add_flex_item(
            layout, widget,
            flex_grow=1,
            flex_basis=100
        )
        
        assert layout.count() == 1
        assert widget.minimumWidth() == 100
    
    def test_create_responsive_grid(self, app):
        """Test creating responsive grid layout."""
        columns = {
            "small": 1,
            "medium": 2,
            "large": 3
        }
        
        layout = LayoutUtilities.create_responsive_grid(
            columns=columns,
            spacing=16,
            margin=8
        )
        
        assert isinstance(layout, QGridLayout)
        assert layout.spacing() == 16
        assert layout.contentsMargins() == QMargins(8, 8, 8, 8)
        assert hasattr(layout, '_responsive_columns')
        assert layout._responsive_columns == columns
    
    def test_create_card_layout(self, app):
        """Test creating card layout."""
        # Test with title
        card, layout = LayoutUtilities.create_card_layout(
            title="Test Card",
            padding=20,
            elevation=True
        )
        
        assert isinstance(card, QFrame)
        assert isinstance(layout, QVBoxLayout)
        assert layout.contentsMargins() == QMargins(20, 20, 20, 20)
        assert layout.spacing() == 12
        assert layout.count() == 1  # Should have title label
        
        # Test without title
        card_no_title, layout_no_title = LayoutUtilities.create_card_layout(
            title=None,
            padding=16,
            elevation=False
        )
        
        assert layout_no_title.count() == 0  # No title label
    
    def test_create_sidebar_layout(self, app):
        """Test creating sidebar layout."""
        splitter, sidebar, main_content = LayoutUtilities.create_sidebar_layout(
            sidebar_width=300,
            collapsible=True,
            position="left"
        )
        
        assert isinstance(splitter, QSplitter)
        assert isinstance(sidebar, QWidget)
        assert isinstance(main_content, QWidget)
        assert sidebar.minimumWidth() == 300
        assert sidebar.maximumWidth() == 600  # 2 * sidebar_width
        assert splitter.orientation() == Qt.Orientation.Horizontal
    
    def test_create_sidebar_layout_right(self, app):
        """Test creating right sidebar layout."""
        splitter, sidebar, main_content = LayoutUtilities.create_sidebar_layout(
            position="right"
        )
        
        # For right position, main content should be added first
        assert splitter.widget(0) == main_content
        assert splitter.widget(1) == sidebar
    
    def test_create_toolbar_layout(self, app):
        """Test creating toolbar layout."""
        layout = LayoutUtilities.create_toolbar_layout(
            orientation=Qt.Orientation.Horizontal,
            icon_size=QSize(32, 32),
            spacing=6
        )
        
        assert isinstance(layout, QHBoxLayout)
        assert layout.spacing() == 6
        assert layout.contentsMargins() == QMargins(8, 4, 8, 4)
        assert hasattr(layout, '_icon_size')
        assert layout._icon_size == QSize(32, 32)
        
        # Test vertical toolbar
        v_layout = LayoutUtilities.create_toolbar_layout(
            orientation=Qt.Orientation.Vertical
        )
        assert isinstance(v_layout, QVBoxLayout)
    
    def test_create_form_layout(self, app):
        """Test creating form layout."""
        fields = [
            ("Name:", QWidget()),
            ("Email:", QWidget()),
            ("Phone:", QWidget())
        ]
        
        layout = LayoutUtilities.create_form_layout(
            fields=fields,
            label_width=100,
            spacing=10
        )
        
        assert isinstance(layout, QVBoxLayout)
        assert layout.spacing() == 10
        assert layout.count() == 1  # Contains form layout
    
    def test_create_tab_like_layout(self, app):
        """Test creating tab-like layout."""
        tabs = [
            ("Tab 1", QWidget()),
            ("Tab 2", QWidget()),
            ("Tab 3", QWidget())
        ]
        
        container, main_layout = LayoutUtilities.create_tab_like_layout(
            tabs=tabs,
            tab_position="top"
        )
        
        assert isinstance(container, QWidget)
        assert isinstance(main_layout, QVBoxLayout)
        assert main_layout.count() == 2  # Tab buttons layout + stacked widget
    
    def test_create_center_layout(self, app):
        """Test creating center layout."""
        content_widget = QWidget()
        
        layout = LayoutUtilities.create_center_layout(
            content_widget=content_widget,
            max_width=500,
            max_height=300
        )
        
        assert isinstance(layout, QVBoxLayout)
        assert content_widget.maximumWidth() == 500
        assert content_widget.maximumHeight() == 300
    
    def test_create_masonry_layout(self, app):
        """Test creating masonry layout."""
        masonry = LayoutUtilities.create_masonry_layout(
            columns=4,
            spacing=12
        )
        
        assert isinstance(masonry, MasonryLayout)
        assert masonry._columns == 4
        assert masonry._spacing == 12
    
    def test_add_separator(self, app):
        """Test adding separators to layout."""
        layout = QVBoxLayout()
        
        # Add horizontal separator
        LayoutUtilities.add_separator(
            layout,
            orientation=Qt.Orientation.Horizontal,
            margin=8
        )
        
        assert layout.count() == 1
        separator = layout.itemAt(0).widget()
        assert isinstance(separator, QFrame)
        assert separator.frameShape() == QFrame.Shape.HLine
        assert separator.maximumHeight() == 1
    
    def test_create_responsive_image_grid(self, app):
        """Test creating responsive image grid."""
        images = ["image1.jpg", "image2.jpg", "image3.jpg"]
        
        scroll_area = LayoutUtilities.create_responsive_image_grid(
            images=images,
            min_item_width=150,
            aspect_ratio=1.5,
            spacing=10
        )
        
        assert isinstance(scroll_area, QScrollArea)
        assert scroll_area.widgetResizable() is True
    
    def test_apply_spacing_scale(self, app):
        """Test applying spacing scale to layout."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)
        
        LayoutUtilities.apply_spacing_scale(layout, 2.0)
        
        assert layout.spacing() == 20  # 10 * 2.0
        margins = layout.contentsMargins()
        assert margins.left() == 10  # 5 * 2.0
        assert margins.top() == 10
        assert margins.right() == 10
        assert margins.bottom() == 10


class TestMasonryLayout:
    """Test MasonryLayout functionality."""
    
    def test_initialization(self, app):
        """Test MasonryLayout initialization."""
        layout = MasonryLayout(columns=3, spacing=8)
        
        assert layout._columns == 3
        assert layout._spacing == 8
        assert len(layout._column_heights) == 3
        assert all(h == 0 for h in layout._column_heights)
    
    def test_add_item(self, app):
        """Test adding items to masonry layout."""
        layout = MasonryLayout()
        widget = QWidget()
        
        layout.addWidget(widget)
        
        assert layout.count() == 1
        assert len(layout._items) == 1
    
    def test_item_management(self, app):
        """Test item management operations."""
        layout = MasonryLayout()
        widget1 = QWidget()
        widget2 = QWidget()
        
        layout.addWidget(widget1)
        layout.addWidget(widget2)
        
        # Test itemAt
        item = layout.itemAt(0)
        assert item is not None
        assert item.widget() == widget1
        
        # Test takeAt
        taken_item = layout.takeAt(0)
        assert taken_item is not None
        assert layout.count() == 1
        
        # Test invalid index
        assert layout.itemAt(10) is None
        assert layout.takeAt(10) is None
    
    def test_size_hint(self, app):
        """Test size hint calculation."""
        layout = MasonryLayout()
        
        size_hint = layout.sizeHint()
        assert isinstance(size_hint, QSize)
        assert size_hint.width() == 400  # Default
        assert size_hint.height() == 300  # Default
        
        min_size = layout.minimumSize()
        assert isinstance(min_size, QSize)
        assert min_size.width() == 200
        assert min_size.height() == 100
    
    def test_geometry_setting(self, app):
        """Test setting layout geometry."""
        layout = MasonryLayout(columns=2)
        widget1 = QWidget()
        widget2 = QWidget()
        
        layout.addWidget(widget1)
        layout.addWidget(widget2)
        
        # Mock widget size hints
        widget1.sizeHint = Mock(return_value=QSize(100, 150))
        widget2.sizeHint = Mock(return_value=QSize(100, 100))
        
        from PyQt6.QtCore import QRect
        test_rect = QRect(0, 0, 300, 400)
        
        # This should trigger item arrangement
        layout.setGeometry(test_rect)
        
        # Verify the geometry was set
        assert layout.geometry() == test_rect


class TestResponsiveImageGrid:
    """Test ResponsiveImageGrid functionality."""
    
    def test_initialization(self, app):
        """Test ResponsiveImageGrid initialization."""
        grid = ResponsiveImageGrid(
            min_item_width=200,
            aspect_ratio=1.5,
            spacing=12
        )
        
        assert grid._min_item_width == 200
        assert grid._aspect_ratio == 1.5
        assert grid._current_columns == 1
        assert grid.spacing() == 12
    
    def test_widget_addition(self, app):
        """Test adding widgets to responsive grid."""
        grid = ResponsiveImageGrid()
        widget = QWidget()
        
        with patch.object(grid, '_rearrange_grid') as mock_rearrange:
            grid.addWidget(widget)
            
            # Should trigger rearrangement
            mock_rearrange.assert_called_once()
    
    def test_column_calculation(self, app):
        """Test column count calculation."""
        grid = ResponsiveImageGrid(min_item_width=150)
        
        # Mock parent widget
        parent = QWidget()
        parent.width = Mock(return_value=500)
        grid.setParent(parent)
        
        # Calculate optimal columns: 500 / (150 + spacing) ≈ 3
        grid._rearrange_grid()
        
        # Should calculate appropriate number of columns
        assert grid._current_columns >= 1
    
    def test_item_reorganization(self, app):
        """Test item reorganization when columns change."""
        grid = ResponsiveImageGrid()
        widget1 = QWidget()
        widget2 = QWidget()
        widget3 = QWidget()
        
        # Add widgets
        grid.addWidget(widget1)
        grid.addWidget(widget2)
        grid.addWidget(widget3)
        
        # Change column count and reorganize
        grid._current_columns = 2
        
        with patch.object(grid, 'takeAt') as mock_take:
            with patch.object(grid, 'addWidget') as mock_add:
                # Mock widgets being taken and re-added
                mock_take.side_effect = [
                    Mock(widget=Mock(return_value=widget1)),
                    Mock(widget=Mock(return_value=widget2)),
                    Mock(widget=Mock(return_value=widget3)),
                    None  # End of items
                ]
                
                grid._reorganize_items()
                
                # Should reorganize all widgets
                assert mock_take.call_count >= 3
    
    def test_resize_handling(self, app):
        """Test resize event handling."""
        grid = ResponsiveImageGrid()
        
        with patch.object(grid, '_rearrange_grid') as mock_rearrange:
            # Simulate resize event
            from PyQt6.QtGui import QResizeEvent
            resize_event = QResizeEvent(QSize(800, 600), QSize(600, 400))
            
            grid.resizeEvent(resize_event)
            
            # Should trigger grid rearrangement
            mock_rearrange.assert_called_once()
    
    def test_empty_grid_handling(self, app):
        """Test handling of empty grid."""
        grid = ResponsiveImageGrid()
        
        # Should handle empty grid gracefully
        grid._rearrange_grid()
        grid._reorganize_items()
        
        # No exceptions should be raised
        assert grid._current_columns == 1
    
    def test_parent_width_handling(self, app):
        """Test handling when parent has no width."""
        grid = ResponsiveImageGrid()
        
        # No parent set
        grid._rearrange_grid()
        assert grid._current_columns == 1
        
        # Parent with zero width
        parent = QWidget()
        parent.width = Mock(return_value=0)
        grid.setParent(parent)
        
        grid._rearrange_grid()
        assert grid._current_columns == 1