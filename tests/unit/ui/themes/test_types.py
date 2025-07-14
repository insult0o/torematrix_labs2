"""Tests for theme type definitions."""

import pytest
from dataclasses import asdict

from torematrix.ui.themes.types import (
    ThemeType, ThemeFormat, ComponentType,
    ThemeMetadata, ColorDefinition, TypographyDefinition
)


class TestThemeType:
    """Test cases for ThemeType enum."""
    
    def test_theme_type_values(self):
        """Test theme type enum values."""
        assert ThemeType.LIGHT.value == "light"
        assert ThemeType.DARK.value == "dark"
        assert ThemeType.HIGH_CONTRAST.value == "high_contrast"
        assert ThemeType.CUSTOM.value == "custom"
        
    def test_theme_type_from_string(self):
        """Test creating theme type from string."""
        assert ThemeType("light") == ThemeType.LIGHT
        assert ThemeType("dark") == ThemeType.DARK
        assert ThemeType("high_contrast") == ThemeType.HIGH_CONTRAST
        assert ThemeType("custom") == ThemeType.CUSTOM
        
    def test_invalid_theme_type(self):
        """Test invalid theme type raises error."""
        with pytest.raises(ValueError):
            ThemeType("invalid_type")


class TestThemeFormat:
    """Test cases for ThemeFormat enum."""
    
    def test_theme_format_values(self):
        """Test theme format enum values."""
        assert ThemeFormat.YAML.value == "yaml"
        assert ThemeFormat.JSON.value == "json"
        assert ThemeFormat.TOML.value == "toml"
        
    def test_theme_format_from_string(self):
        """Test creating theme format from string."""
        assert ThemeFormat("yaml") == ThemeFormat.YAML
        assert ThemeFormat("json") == ThemeFormat.JSON
        assert ThemeFormat("toml") == ThemeFormat.TOML


class TestComponentType:
    """Test cases for ComponentType enum."""
    
    def test_component_type_values(self):
        """Test component type enum has expected values."""
        expected_types = [
            "main_window", "menu_bar", "toolbar", "button", "dialog",
            "tree_view", "table_view", "text_edit", "tab_widget",
            "progress_bar", "status_bar", "splitter"
        ]
        
        for component_type in ComponentType:
            assert component_type.value in expected_types
            
    def test_component_type_from_string(self):
        """Test creating component type from string."""
        assert ComponentType("main_window") == ComponentType.MAIN_WINDOW
        assert ComponentType("menu_bar") == ComponentType.MENU_BAR
        assert ComponentType("button") == ComponentType.BUTTON


class TestThemeMetadata:
    """Test cases for ThemeMetadata dataclass."""
    
    def test_metadata_creation(self):
        """Test creating theme metadata."""
        metadata = ThemeMetadata(
            name="Test Theme",
            version="1.0.0",
            description="A test theme",
            author="Test Author",
            category=ThemeType.LIGHT,
            accessibility_compliant=True,
            high_contrast_available=False,
            requires_icons=True
        )
        
        assert metadata.name == "Test Theme"
        assert metadata.version == "1.0.0"
        assert metadata.description == "A test theme"
        assert metadata.author == "Test Author"
        assert metadata.category == ThemeType.LIGHT
        assert metadata.accessibility_compliant is True
        assert metadata.high_contrast_available is False
        assert metadata.requires_icons is True
        
    def test_metadata_defaults(self):
        """Test theme metadata with default values."""
        metadata = ThemeMetadata(
            name="Test",
            version="1.0.0",
            description="Test",
            author="Test",
            category=ThemeType.LIGHT
        )
        
        # Test default values
        assert metadata.accessibility_compliant is True
        assert metadata.high_contrast_available is False
        assert metadata.requires_icons is True
        
    def test_metadata_serialization(self):
        """Test metadata can be serialized to dict."""
        metadata = ThemeMetadata(
            name="Test Theme",
            version="1.0.0", 
            description="A test theme",
            author="Test Author",
            category=ThemeType.DARK
        )
        
        metadata_dict = asdict(metadata)
        assert isinstance(metadata_dict, dict)
        assert metadata_dict['name'] == "Test Theme"
        assert metadata_dict['category'] == ThemeType.DARK


class TestColorDefinition:
    """Test cases for ColorDefinition dataclass."""
    
    def test_color_definition_creation(self):
        """Test creating color definition."""
        color_def = ColorDefinition(
            value="#2196F3",
            description="Primary brand color",
            contrast_ratio=4.5,
            accessibility_level="AA"
        )
        
        assert color_def.value == "#2196F3"
        assert color_def.description == "Primary brand color"
        assert color_def.contrast_ratio == 4.5
        assert color_def.accessibility_level == "AA"
        
    def test_color_definition_defaults(self):
        """Test color definition with default values."""
        color_def = ColorDefinition(value="#FF0000")
        
        assert color_def.value == "#FF0000"
        assert color_def.description == ""
        assert color_def.contrast_ratio is None
        assert color_def.accessibility_level == "AA"
        
    def test_color_definition_serialization(self):
        """Test color definition can be serialized."""
        color_def = ColorDefinition(
            value="#2196F3",
            description="Primary color",
            contrast_ratio=5.2
        )
        
        color_dict = asdict(color_def)
        assert isinstance(color_dict, dict)
        assert color_dict['value'] == "#2196F3"
        assert color_dict['description'] == "Primary color"
        assert color_dict['contrast_ratio'] == 5.2


class TestTypographyDefinition:
    """Test cases for TypographyDefinition dataclass."""
    
    def test_typography_definition_creation(self):
        """Test creating typography definition."""
        typo_def = TypographyDefinition(
            font_family="Arial",
            font_size=14,
            font_weight=600,
            line_height=1.6,
            letter_spacing=0.5
        )
        
        assert typo_def.font_family == "Arial"
        assert typo_def.font_size == 14
        assert typo_def.font_weight == 600
        assert typo_def.line_height == 1.6
        assert typo_def.letter_spacing == 0.5
        
    def test_typography_definition_defaults(self):
        """Test typography definition with default values."""
        typo_def = TypographyDefinition(
            font_family="Times New Roman",
            font_size=12
        )
        
        assert typo_def.font_family == "Times New Roman"
        assert typo_def.font_size == 12
        assert typo_def.font_weight == 400  # Default
        assert typo_def.line_height == 1.4  # Default
        assert typo_def.letter_spacing == 0.0  # Default
        
    def test_typography_definition_serialization(self):
        """Test typography definition can be serialized."""
        typo_def = TypographyDefinition(
            font_family="Helvetica",
            font_size=16,
            font_weight=500
        )
        
        typo_dict = asdict(typo_def)
        assert isinstance(typo_dict, dict)
        assert typo_dict['font_family'] == "Helvetica"
        assert typo_dict['font_size'] == 16
        assert typo_dict['font_weight'] == 500