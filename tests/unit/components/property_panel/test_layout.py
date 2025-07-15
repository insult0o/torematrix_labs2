"""Tests for responsive layout management"""

import pytest
from unittest.mock import Mock
from PyQt6.QtWidgets import QWidget, QLabel
from PyQt6.QtCore import QRect, QSize
from PyQt6.QtTest import QTest

from src.torematrix.ui.components.property_panel.layout import ResponsivePropertyLayout, PropertyCategoryFrame


class TestResponsivePropertyLayout:
    @pytest.fixture
    def layout(self, qtbot):
        """Create ResponsivePropertyLayout for testing"""
        widget = QWidget()
        layout = ResponsivePropertyLayout(widget)
        widget.setLayout(layout)
        qtbot.addWidget(widget)
        return layout
    
    @pytest.fixture
    def sample_widgets(self, qtbot):
        """Create sample widgets for layout testing"""
        widgets = []
        for i in range(5):
            widget = QLabel(f"Widget {i}")
            widget.setFixedSize(100, 50)
            qtbot.addWidget(widget)
            widgets.append(widget)
        return widgets
    
    def test_layout_initialization(self, layout):
        """Test layout initialization"""
        assert layout._layout_mode == "vertical"
        assert layout._min_column_width == 200
        assert layout._max_columns == 3
        assert layout._spacing == 4
        assert layout._adaptive_sizing is True
        assert len(layout._items) == 0
    
    def test_add_widgets(self, layout, sample_widgets):
        """Test adding widgets to layout"""
        for widget in sample_widgets:
            layout.addWidget(widget)
        
        assert layout.count() == 5
        assert len(layout._items) == 5
    
    def test_item_access(self, layout, sample_widgets):
        """Test item access methods"""
        for widget in sample_widgets:
            layout.addWidget(widget)
        
        # Test itemAt
        item = layout.itemAt(0)
        assert item is not None
        assert item.widget() == sample_widgets[0]
        
        # Test out of bounds
        assert layout.itemAt(10) is None
        assert layout.itemAt(-1) is None
    
    def test_take_item(self, layout, sample_widgets):
        """Test removing items from layout"""
        for widget in sample_widgets:
            layout.addWidget(widget)
        
        initial_count = layout.count()
        item = layout.takeAt(0)
        
        assert item is not None
        assert item.widget() == sample_widgets[0]
        assert layout.count() == initial_count - 1
    
    def test_size_hint_calculation(self, layout, sample_widgets):
        """Test size hint calculation"""
        # Empty layout
        assert layout.sizeHint() == QSize(0, 0)
        
        # Add widgets
        for widget in sample_widgets:
            layout.addWidget(widget)
        
        size_hint = layout.sizeHint()
        assert size_hint.width() > 0
        assert size_hint.height() > 0
    
    def test_minimum_size_calculation(self, layout, sample_widgets):
        """Test minimum size calculation"""
        # Empty layout
        assert layout.minimumSize() == QSize(0, 0)
        
        # Add widgets
        for widget in sample_widgets:
            layout.addWidget(widget)
        
        min_size = layout.minimumSize()
        assert min_size.width() >= layout._min_column_width
        assert min_size.height() > 0
    
    def test_vertical_layout_mode(self, layout, sample_widgets):
        """Test vertical layout arrangement"""
        layout.set_layout_mode("vertical")
        
        for widget in sample_widgets:
            layout.addWidget(widget)
        
        # Set geometry to trigger layout
        rect = QRect(0, 0, 300, 500)
        layout.setGeometry(rect)
        
        # Verify vertical arrangement
        items = layout.get_items()
        if len(items) >= 2:
            item1 = items[0]
            item2 = items[1]
            # Second item should be below first item
            assert item2.geometry().y() > item1.geometry().y()
    
    def test_horizontal_layout_mode(self, layout, sample_widgets):
        """Test horizontal layout arrangement"""
        layout.set_layout_mode("horizontal")
        
        for widget in sample_widgets:
            layout.addWidget(widget)
        
        # Set geometry to trigger layout
        rect = QRect(0, 0, 800, 100)
        layout.setGeometry(rect)
        
        # Verify horizontal arrangement
        items = layout.get_items()
        if len(items) >= 2:
            item1 = items[0]
            item2 = items[1]
            # Second item should be to the right of first item
            assert item2.geometry().x() > item1.geometry().x()
    
    def test_grid_layout_mode(self, layout, sample_widgets):
        """Test grid layout arrangement"""
        layout.set_layout_mode("grid")
        layout.set_grid_columns(2)
        
        for widget in sample_widgets:
            layout.addWidget(widget)
        
        # Set geometry to trigger layout
        rect = QRect(0, 0, 500, 400)
        layout.setGeometry(rect)
        
        # Verify grid arrangement
        items = layout.get_items()
        if len(items) >= 3:
            # First row items should have same y coordinate
            item1 = items[0]
            item2 = items[1]
            assert abs(item1.geometry().y() - item2.geometry().y()) < 5
            
            # Second row item should be below first row
            item3 = items[2]
            assert item3.geometry().y() > item1.geometry().y()
    
    def test_auto_layout_mode(self, layout, sample_widgets):
        """Test auto layout mode adaptation"""
        layout.set_layout_mode("auto")
        
        for widget in sample_widgets:
            layout.addWidget(widget)
        
        # Test narrow width (should use vertical)
        narrow_rect = QRect(0, 0, 300, 500)
        layout.setGeometry(narrow_rect)
        assert layout.get_effective_layout_mode() == "vertical"
        
        # Test medium width (should use horizontal)
        medium_rect = QRect(0, 0, 500, 300)
        layout.setGeometry(medium_rect)
        assert layout.get_effective_layout_mode() == "horizontal"
        
        # Test wide width (should use grid)
        wide_rect = QRect(0, 0, 800, 400)
        layout.setGeometry(wide_rect)
        assert layout.get_effective_layout_mode() == "grid"
    
    def test_spacing_configuration(self, layout):
        """Test spacing configuration"""
        layout.set_spacing(10)
        assert layout._spacing == 10
        
        # Negative spacing should be clamped to 0
        layout.set_spacing(-5)
        assert layout._spacing == 0
    
    def test_margins_configuration(self, layout):
        """Test margins configuration"""
        layout.set_margins(5, 10, 15, 20)
        assert layout._margins == (5, 10, 15, 20)
    
    def test_column_width_configuration(self, layout):
        """Test minimum column width configuration"""
        layout.set_min_column_width(250)
        assert layout._min_column_width == 250
        
        # Very small width should be clamped to minimum
        layout.set_min_column_width(50)
        assert layout._min_column_width == 100
    
    def test_adaptive_sizing_toggle(self, layout):
        """Test adaptive sizing enable/disable"""
        layout.set_adaptive_sizing(False)
        assert layout._adaptive_sizing is False
        
        layout.set_adaptive_sizing(True)
        assert layout._adaptive_sizing is True
    
    def test_width_thresholds_configuration(self, layout):
        """Test width thresholds for auto mode"""
        layout.set_width_thresholds(700, 450)
        assert layout._width_threshold_grid == 700
        assert layout._width_threshold_horizontal == 450
    
    def test_clear_layout(self, layout, sample_widgets):
        """Test clearing all items from layout"""
        for widget in sample_widgets:
            layout.addWidget(widget)
        
        assert layout.count() == 5
        
        layout.clear_layout()
        assert layout.count() == 0
        assert len(layout._items) == 0
    
    def test_get_items(self, layout, sample_widgets):
        """Test getting layout items"""
        for widget in sample_widgets:
            layout.addWidget(widget)
        
        items = layout.get_items()
        assert len(items) == 5
        assert items is not layout._items  # Should be a copy


class TestPropertyCategoryFrame:
    @pytest.fixture
    def category_frame(self, qtbot):
        """Create PropertyCategoryFrame for testing"""
        frame = PropertyCategoryFrame("Test Category")
        qtbot.addWidget(frame)
        return frame
    
    @pytest.fixture
    def sample_property_widgets(self, qtbot):
        """Create sample property widgets"""
        widgets = []
        for i in range(3):
            widget = QLabel(f"Property {i}")
            qtbot.addWidget(widget)
            widgets.append(widget)
        return widgets
    
    def test_category_frame_initialization(self, category_frame):
        """Test category frame initialization"""
        assert category_frame._category_name == "Test Category"
        assert category_frame._is_collapsible is True
        assert category_frame._is_collapsed is False
        assert len(category_frame._property_widgets) == 0
    
    def test_category_header_display(self, category_frame):
        """Test category header display"""
        assert category_frame._name_label.text() == "Test Category"
        assert category_frame._toggle_button.text() == "−"  # Expanded state
        assert category_frame._count_label.text() == "0"
    
    def test_add_property_widgets(self, category_frame, sample_property_widgets):
        """Test adding property widgets to category"""
        for widget in sample_property_widgets:
            category_frame.add_property_widget(widget)
        
        assert len(category_frame._property_widgets) == 3
        assert category_frame.get_property_count() == 3
        assert category_frame._count_label.text() == "3"
    
    def test_remove_property_widget(self, category_frame, sample_property_widgets):
        """Test removing property widget from category"""
        # Add widgets first
        for widget in sample_property_widgets:
            category_frame.add_property_widget(widget)
        
        # Remove one widget
        category_frame.remove_property_widget(sample_property_widgets[0])
        
        assert len(category_frame._property_widgets) == 2
        assert sample_property_widgets[0] not in category_frame._property_widgets
        assert category_frame._count_label.text() == "2"
    
    def test_clear_property_widgets(self, category_frame, sample_property_widgets):
        """Test clearing all property widgets"""
        # Add widgets first
        for widget in sample_property_widgets:
            category_frame.add_property_widget(widget)
        
        assert len(category_frame._property_widgets) == 3
        
        category_frame.clear_property_widgets()
        
        assert len(category_frame._property_widgets) == 0
        assert category_frame._count_label.text() == "0"
    
    def test_toggle_collapsed_state(self, category_frame):
        """Test toggling collapsed state"""
        # Initially expanded
        assert category_frame._is_collapsed is False
        assert category_frame._content_widget.isVisible() is True
        assert category_frame._toggle_button.text() == "−"
        
        # Toggle to collapsed
        category_frame._toggle_collapsed()
        
        assert category_frame._is_collapsed is True
        assert category_frame._content_widget.isVisible() is False
        assert category_frame._toggle_button.text() == "+"
        
        # Toggle back to expanded
        category_frame._toggle_collapsed()
        
        assert category_frame._is_collapsed is False
        assert category_frame._content_widget.isVisible() is True
        assert category_frame._toggle_button.text() == "−"
    
    def test_set_collapsed_programmatically(self, category_frame):
        """Test setting collapsed state programmatically"""
        category_frame.set_collapsed(True)
        assert category_frame._is_collapsed is True
        assert category_frame._content_widget.isVisible() is False
        
        category_frame.set_collapsed(False)
        assert category_frame._is_collapsed is False
        assert category_frame._content_widget.isVisible() is True
    
    def test_layout_mode_delegation(self, category_frame):
        """Test layout mode setting delegation to content layout"""
        # This tests that the method exists and can be called
        category_frame.set_layout_mode("horizontal")
        # The actual layout behavior is tested in ResponsivePropertyLayout tests
    
    def test_category_name_getter(self, category_frame):
        """Test getting category name"""
        assert category_frame.get_category_name() == "Test Category"
    
    def test_is_collapsed_getter(self, category_frame):
        """Test collapsed state getter"""
        assert category_frame.is_collapsed() is False
        
        category_frame.set_collapsed(True)
        assert category_frame.is_collapsed() is True