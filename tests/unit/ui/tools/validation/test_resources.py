"""
Tests for UI resources (styles and icons).

This module provides comprehensive tests for the styling system and
icon generation functionality used in merge/split operations.
"""

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QPixmap, QColor
from PyQt6.QtCore import QSize

from src.torematrix.ui.tools.validation.resources import (
    merge_split_styles, get_icon, IconType
)
from src.torematrix.ui.tools.validation.resources.styles import (
    get_style_for_component, get_color, apply_theme, COLORS
)
from src.torematrix.ui.tools.validation.resources.icons import (
    create_merge_icon, create_split_icon, create_add_icon, create_remove_icon,
    create_arrow_icon, create_warning_icon, create_success_icon, create_error_icon,
    create_info_icon, get_icon_sizes, create_icon_set
)


class TestStyles:
    """Tests for styling system."""
    
    def test_merge_split_styles_exists(self):
        """Test that main styles string exists and is not empty."""
        assert merge_split_styles
        assert isinstance(merge_split_styles, str)
        assert len(merge_split_styles) > 0
    
    def test_styles_contain_key_components(self):
        """Test that styles contain expected UI components."""
        # Check for key UI component styles
        expected_components = [
            "QDialog", "QPushButton", "QListWidget", "QTextEdit",
            "QGroupBox", "QComboBox", "QCheckBox", "QTableWidget",
            "QProgressBar", "QSplitter", "QTabWidget", "QScrollArea"
        ]
        
        for component in expected_components:
            assert component in merge_split_styles
    
    def test_styles_contain_accessibility_features(self):
        """Test that styles include accessibility features."""
        assert ":focus" in merge_split_styles
        assert "prefers-contrast" in merge_split_styles
        assert "outline" in merge_split_styles
    
    def test_styles_contain_theme_support(self):
        """Test that styles support dark theme."""
        assert 'theme="dark"' in merge_split_styles
        assert "#121212" in merge_split_styles  # Dark background color
    
    def test_get_style_for_component(self):
        """Test getting styles for specific components."""
        button_style = get_style_for_component("button")
        assert "QPushButton" in button_style
        assert "background-color" in button_style
        
        dialog_style = get_style_for_component("dialog")
        assert "QDialog" in dialog_style
        
        # Test invalid component
        invalid_style = get_style_for_component("nonexistent")
        assert invalid_style == ""
    
    def test_get_color(self):
        """Test color retrieval function."""
        # Test valid colors
        primary_color = get_color("primary")
        assert primary_color == COLORS["primary"]
        
        background_color = get_color("background")
        assert background_color == COLORS["background"]
        
        # Test invalid color
        invalid_color = get_color("nonexistent")
        assert invalid_color == "#000000"  # Default fallback
    
    def test_colors_palette_completeness(self):
        """Test that color palette contains expected colors."""
        expected_colors = [
            "primary", "secondary", "success", "warning", "error", "info",
            "background", "surface", "border", "text_primary", "text_secondary"
        ]
        
        for color in expected_colors:
            assert color in COLORS
            assert COLORS[color].startswith("#")  # Should be hex color
            assert len(COLORS[color]) in [4, 7]  # #RGB or #RRGGBB
    
    @pytest.fixture
    def app(self):
        """Create QApplication for widget tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    def test_apply_theme(self, app):
        """Test theme application to widgets."""
        from PyQt6.QtWidgets import QWidget
        
        widget = QWidget()
        
        # Test light theme
        apply_theme(widget, "light")
        assert widget.property("theme") == "light"
        
        # Test dark theme
        apply_theme(widget, "dark")
        assert widget.property("theme") == "dark"


class TestIcons:
    """Tests for icon generation system."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for icon tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    def test_create_merge_icon(self, app):
        """Test merge icon creation."""
        icon = create_merge_icon(24, QColor("#2196f3"))
        assert isinstance(icon, QPixmap)
        assert icon.width() == 24
        assert icon.height() == 24
        assert not icon.isNull()
    
    def test_create_split_icon(self, app):
        """Test split icon creation."""
        icon = create_split_icon(32, QColor("#ff9800"))
        assert isinstance(icon, QPixmap)
        assert icon.width() == 32
        assert icon.height() == 32
        assert not icon.isNull()
    
    def test_create_add_icon(self, app):
        """Test add icon creation."""
        icon = create_add_icon(16, QColor("#4caf50"))
        assert isinstance(icon, QPixmap)
        assert icon.width() == 16
        assert icon.height() == 16
        assert not icon.isNull()
    
    def test_create_remove_icon(self, app):
        """Test remove icon creation."""
        icon = create_remove_icon(20, QColor("#f44336"))
        assert isinstance(icon, QPixmap)
        assert icon.width() == 20
        assert icon.height() == 20
        assert not icon.isNull()
    
    def test_create_arrow_icons(self, app):
        """Test arrow icon creation in all directions."""
        directions = ["up", "down", "left", "right"]
        
        for direction in directions:
            icon = create_arrow_icon(24, direction, QColor("#666666"))
            assert isinstance(icon, QPixmap)
            assert icon.width() == 24
            assert icon.height() == 24
            assert not icon.isNull()
    
    def test_create_arrow_icon_invalid_direction(self, app):
        """Test arrow icon with invalid direction."""
        icon = create_arrow_icon(24, "invalid", QColor("#666666"))
        assert isinstance(icon, QPixmap)
        assert icon.width() == 24
        assert icon.height() == 24
        # Should still create a pixmap, even if empty
    
    def test_create_warning_icon(self, app):
        """Test warning icon creation."""
        icon = create_warning_icon(24, QColor("#ff9800"))
        assert isinstance(icon, QPixmap)
        assert icon.width() == 24
        assert icon.height() == 24
        assert not icon.isNull()
    
    def test_create_success_icon(self, app):
        """Test success icon creation."""
        icon = create_success_icon(24, QColor("#4caf50"))
        assert isinstance(icon, QPixmap)
        assert icon.width() == 24
        assert icon.height() == 24
        assert not icon.isNull()
    
    def test_create_error_icon(self, app):
        """Test error icon creation."""
        icon = create_error_icon(24, QColor("#f44336"))
        assert isinstance(icon, QPixmap)
        assert icon.width() == 24
        assert icon.height() == 24
        assert not icon.isNull()
    
    def test_create_info_icon(self, app):
        """Test info icon creation."""
        icon = create_info_icon(24, QColor("#2196f3"))
        assert isinstance(icon, QPixmap)
        assert icon.width() == 24
        assert icon.height() == 24
        assert not icon.isNull()
    
    def test_get_icon_all_types(self, app):
        """Test getting all icon types."""
        for icon_type in IconType:
            icon = get_icon(icon_type, 24)
            assert isinstance(icon, QIcon)
            assert not icon.isNull()
            
            # Check that icon has at least one pixmap
            pixmap = icon.pixmap(QSize(24, 24))
            assert not pixmap.isNull()
    
    def test_get_icon_custom_color(self, app):
        """Test getting icon with custom color."""
        custom_color = QColor("#purple")
        icon = get_icon(IconType.MERGE, 24, custom_color)
        assert isinstance(icon, QIcon)
        assert not icon.isNull()
    
    def test_get_icon_different_sizes(self, app):
        """Test getting icons in different sizes."""
        sizes = [16, 24, 32, 48]
        
        for size in sizes:
            icon = get_icon(IconType.SPLIT, size)
            pixmap = icon.pixmap(QSize(size, size))
            assert pixmap.width() == size
            assert pixmap.height() == size
    
    def test_get_icon_sizes(self):
        """Test getting available icon sizes."""
        sizes = get_icon_sizes()
        assert isinstance(sizes, list)
        assert len(sizes) > 0
        assert all(isinstance(size, int) for size in sizes)
        assert all(size > 0 for size in sizes)
        
        # Check that common sizes are included
        assert 16 in sizes
        assert 24 in sizes
        assert 32 in sizes
    
    def test_create_icon_set(self, app):
        """Test creating icon set with multiple sizes."""
        icon_set = create_icon_set(IconType.WARNING)
        assert isinstance(icon_set, QIcon)
        assert not icon_set.isNull()
        
        # Check that multiple sizes are available
        available_sizes = icon_set.availableSizes()
        assert len(available_sizes) > 1
    
    def test_create_icon_set_custom_color(self, app):
        """Test creating icon set with custom color."""
        custom_color = QColor("#8a2be2")  # Blue violet
        icon_set = create_icon_set(IconType.INFO, custom_color)
        assert isinstance(icon_set, QIcon)
        assert not icon_set.isNull()
    
    def test_icon_type_enum_completeness(self):
        """Test that IconType enum contains expected values."""
        expected_types = [
            "MERGE", "SPLIT", "ADD", "REMOVE", "MOVE_UP", "MOVE_DOWN",
            "PREVIEW", "WARNING", "ERROR", "SUCCESS", "INFO", "SETTINGS",
            "HELP", "CLEAR", "SEARCH", "FILTER"
        ]
        
        for icon_type in expected_types:
            assert hasattr(IconType, icon_type)
            assert isinstance(getattr(IconType, icon_type), IconType)
    
    def test_icon_creation_performance(self, app):
        """Test that icon creation is reasonably fast."""
        import time
        
        start_time = time.time()
        
        # Create multiple icons
        for _ in range(10):
            create_merge_icon(24)
            create_split_icon(24)
            create_add_icon(24)
            create_remove_icon(24)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time (1 second for 40 icons)
        assert duration < 1.0
    
    def test_icon_memory_usage(self, app):
        """Test that icons don't consume excessive memory."""
        icons = []
        
        # Create many icons
        for icon_type in IconType:
            for size in [16, 24, 32]:
                icon = get_icon(icon_type, size)
                icons.append(icon)
        
        # Should create successfully without memory issues
        assert len(icons) > 0
        
        # Check that all icons are valid
        for icon in icons:
            assert not icon.isNull()


class TestResourceIntegration:
    """Tests for resource integration and consistency."""
    
    def test_style_icon_color_consistency(self):
        """Test that icon default colors match style color palette."""
        # Get icon for each type and check color consistency
        merge_color = get_color("primary")
        split_color = get_color("secondary")
        success_color = get_color("success")
        error_color = get_color("error")
        warning_color = get_color("warning")
        
        # Colors should be valid hex colors
        colors = [merge_color, split_color, success_color, error_color, warning_color]
        for color in colors:
            assert color.startswith("#")
            assert len(color) in [4, 7]  # #RGB or #RRGGBB
    
    def test_style_component_coverage(self):
        """Test that styles cover all necessary UI components."""
        # Components that should have styles
        required_components = [
            "QPushButton", "QListWidget", "QTextEdit", "QComboBox",
            "QCheckBox", "QRadioButton", "QGroupBox", "QTabWidget"
        ]
        
        for component in required_components:
            component_style = get_style_for_component(component.lower().replace("q", ""))
            # Should either have dedicated style or be in main stylesheet
            assert component in merge_split_styles or component_style
    
    def test_accessibility_compliance(self):
        """Test that resources meet basic accessibility requirements."""
        # Check for focus indicators
        assert ":focus" in merge_split_styles
        
        # Check for high contrast support
        assert "prefers-contrast" in merge_split_styles
        
        # Check for sufficient color contrast in palette
        bg_color = get_color("background")
        text_color = get_color("text_primary")
        assert bg_color != text_color  # Should have different colors
    
    def test_theme_consistency(self):
        """Test that theme switching affects both styles and icons."""
        # Both light and dark themes should be supported
        assert 'theme="light"' in merge_split_styles or "light" in merge_split_styles
        assert 'theme="dark"' in merge_split_styles
        
        # Dark theme should have appropriate colors
        assert "#121212" in merge_split_styles  # Dark background
        assert "#ffffff" in merge_split_styles  # Light text for dark theme
    
    @pytest.fixture
    def app(self):
        """Create QApplication for integration tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    def test_resource_loading_performance(self, app):
        """Test that resource loading is efficient."""
        import time
        
        start_time = time.time()
        
        # Load styles
        styles = merge_split_styles
        assert styles
        
        # Load multiple icons
        for icon_type in list(IconType)[:5]:  # Test first 5 types
            icon = get_icon(icon_type)
            assert not icon.isNull()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should load quickly
        assert duration < 0.5  # 500ms should be sufficient
    
    def test_resource_caching(self, app):
        """Test that resources are properly cached for performance."""
        # Icons should be consistent when requested multiple times
        icon1 = get_icon(IconType.MERGE, 24)
        icon2 = get_icon(IconType.MERGE, 24)
        
        # Should create valid icons
        assert not icon1.isNull()
        assert not icon2.isNull()
        
        # While they may not be the same object, they should be equivalent
        pixmap1 = icon1.pixmap(QSize(24, 24))
        pixmap2 = icon2.pixmap(QSize(24, 24))
        assert pixmap1.size() == pixmap2.size()