"""Tests for theme base classes."""

import pytest
from unittest.mock import Mock

from PyQt6.QtGui import QColor, QFont

from torematrix.ui.themes.base import Theme, ColorPalette, Typography, ThemeProvider
from torematrix.ui.themes.types import ThemeMetadata, ThemeType, ComponentType, ColorDefinition, TypographyDefinition
from torematrix.ui.themes.exceptions import ThemeValidationError, ThemeNotFoundError


class TestColorPalette:
    """Test cases for ColorPalette class."""
    
    def test_initialization_with_strings(self):
        """Test color palette initialization with string colors."""
        colors = {
            'primary': '#2196F3',
            'secondary': '#FF9800',
            'background': '#FFFFFF',
        }
        palette = ColorPalette(colors)
        
        assert palette.has_color('primary')
        assert palette.get_color_value('primary') == '#2196F3'
        
    def test_initialization_with_definitions(self):
        """Test color palette initialization with color definitions."""
        colors = {
            'primary': ColorDefinition(
                value='#2196F3',
                description='Primary brand color',
                contrast_ratio=4.5,
                accessibility_level='AA'
            ),
            'secondary': '#FF9800',
        }
        palette = ColorPalette(colors)
        
        color_def = palette.get_color_definition('primary')
        assert color_def is not None
        assert color_def.value == '#2196F3'
        assert color_def.description == 'Primary brand color'
        
    def test_get_color_as_qcolor(self):
        """Test getting color as QColor object."""
        colors = {'test_color': '#FF0000'}
        palette = ColorPalette(colors)
        
        qcolor = palette.get_color('test_color')
        assert isinstance(qcolor, QColor)
        assert qcolor.name() == '#ff0000'  # QColor normalizes to lowercase
        
    def test_get_nonexistent_color(self):
        """Test getting non-existent color returns default."""
        palette = ColorPalette({})
        
        # Should return default color
        qcolor = palette.get_color('nonexistent', '#000000')
        assert qcolor.name() == '#000000'
        
        # Should return default value
        value = palette.get_color_value('nonexistent', '#000000')
        assert value == '#000000'
        
    def test_list_colors(self):
        """Test listing all color names."""
        colors = {'color1': '#FF0000', 'color2': '#00FF00', 'color3': '#0000FF'}
        palette = ColorPalette(colors)
        
        color_list = palette.list_colors()
        assert 'color1' in color_list
        assert 'color2' in color_list
        assert 'color3' in color_list
        assert len(color_list) == 3
        
    def test_accessibility_validation(self):
        """Test accessibility validation."""
        colors = {
            'good_contrast': ColorDefinition(value='#000000', contrast_ratio=5.0),
            'poor_contrast': ColorDefinition(value='#CCCCCC', contrast_ratio=2.0),
            'no_ratio': ColorDefinition(value='#FF0000'),
        }
        palette = ColorPalette(colors)
        
        results = palette.validate_accessibility()
        assert results['good_contrast'] is True
        assert results['poor_contrast'] is False
        assert results['no_ratio'] is True  # Assumes valid if not specified
        
    def test_invalid_color_format(self):
        """Test handling of invalid color format."""
        colors = {'invalid': 123}  # Invalid format
        
        with pytest.raises(ThemeValidationError):
            ColorPalette(colors)


class TestTypography:
    """Test cases for Typography class."""
    
    def test_initialization(self):
        """Test typography initialization."""
        typography_data = {
            'default': TypographyDefinition(
                font_family='Arial',
                font_size=12,
                font_weight=400,
                line_height=1.4,
            ),
            'heading': {
                'font_family': 'Arial',
                'font_size': 16,
                'font_weight': 600,
            }
        }
        typography = Typography(typography_data)
        
        assert typography.get_typography_definition('default') is not None
        assert typography.get_typography_definition('heading') is not None
        
    def test_get_font(self):
        """Test getting font as QFont object."""
        typography_data = {
            'test_font': TypographyDefinition(
                font_family='Arial',
                font_size=14,
                font_weight=500,
            )
        }
        typography = Typography(typography_data)
        
        font = typography.get_font('test_font')
        assert isinstance(font, QFont)
        assert font.family() == 'Arial'
        assert font.pointSize() == 14
        assert font.weight() == 500
        
    def test_font_scaling(self):
        """Test font scaling functionality."""
        typography_data = {
            'scalable': TypographyDefinition(font_family='Arial', font_size=12)
        }
        typography = Typography(typography_data)
        
        # Test default scale
        font_normal = typography.get_font('scalable')
        assert font_normal.pointSize() == 12
        
        # Test with scale factor
        font_scaled = typography.get_font('scalable', scale_factor=1.5)
        assert font_scaled.pointSize() == 18  # 12 * 1.5
        
        # Test global scale factor
        typography.set_scale_factor(2.0)
        font_global_scaled = typography.get_font('scalable')
        assert font_global_scaled.pointSize() == 24  # 12 * 2.0
        
    def test_scale_factor_limits(self):
        """Test scale factor limits."""
        typography = Typography({})
        
        # Test minimum limit
        typography.set_scale_factor(0.1)
        assert typography.get_scale_factor() == 0.5  # Should be limited to 0.5
        
        # Test maximum limit
        typography.set_scale_factor(5.0)
        assert typography.get_scale_factor() == 3.0  # Should be limited to 3.0
        
    def test_nonexistent_font(self):
        """Test getting non-existent font returns default."""
        typography = Typography({})
        
        font = typography.get_font('nonexistent')
        assert isinstance(font, QFont)  # Should return default QFont
        
    def test_list_typography(self):
        """Test listing typography names."""
        typography_data = {
            'font1': {'font_family': 'Arial', 'font_size': 12},
            'font2': {'font_family': 'Times', 'font_size': 14},
        }
        typography = Typography(typography_data)
        
        font_list = typography.list_typography()
        assert 'font1' in font_list
        assert 'font2' in font_list


class TestTheme:
    """Test cases for Theme class."""
    
    def test_initialization(self, sample_theme_metadata, sample_theme_data):
        """Test theme initialization."""
        theme = Theme('test_theme', sample_theme_metadata, sample_theme_data)
        
        assert theme.name == 'test_theme'
        assert theme.metadata == sample_theme_metadata
        assert theme.get_color_palette() is not None
        assert theme.get_typography() is not None
        
    def test_get_property(self, sample_theme, sample_theme_data):
        """Test getting property by path."""
        # Test simple property
        assert sample_theme.get_property('metadata.name') == 'Test Theme'
        
        # Test nested property
        assert sample_theme.get_property('colors.primary') == '#2196F3'
        
        # Test non-existent property
        assert sample_theme.get_property('nonexistent.path', 'default') == 'default'
        
    def test_set_property(self, sample_theme):
        """Test setting property by path."""
        sample_theme.set_property('colors.new_color', '#FF0000')
        assert sample_theme.get_property('colors.new_color') == '#FF0000'
        
        # Test creating nested structure
        sample_theme.set_property('new.nested.property', 'value')
        assert sample_theme.get_property('new.nested.property') == 'value'
        
    def test_variable_resolution(self, sample_theme):
        """Test variable resolution in text."""
        text_with_vars = "Background: ${colors.background}, Primary: ${colors.primary}"
        resolved = sample_theme.resolve_variables(text_with_vars)
        
        assert "${colors.background}" not in resolved
        assert "#FFFFFF" in resolved
        assert "#2196F3" in resolved
        
    def test_get_variable(self, sample_theme):
        """Test getting theme variable."""
        # Add variables to theme data
        sample_theme._variables = {'test_var': 'test_value'}
        
        assert sample_theme.get_variable('test_var') == 'test_value'
        assert sample_theme.get_variable('nonexistent', 'default') == 'default'
        
    def test_component_styles(self, sample_theme):
        """Test component styles functionality."""
        # Check if component styles are loaded
        assert sample_theme.has_component_styles(ComponentType.MAIN_WINDOW)
        
        styles = sample_theme.get_component_styles(ComponentType.MAIN_WINDOW)
        assert 'background' in styles
        
        # Non-existent component
        assert not sample_theme.has_component_styles(ComponentType.BUTTON)
        assert sample_theme.get_component_styles(ComponentType.BUTTON) == {}
        
    def test_generate_stylesheet(self, sample_theme):
        """Test basic stylesheet generation."""
        stylesheet = sample_theme.generate_stylesheet()
        assert isinstance(stylesheet, str)
        assert len(stylesheet) > 0
        
    def test_invalid_theme_data(self, sample_theme_metadata):
        """Test theme with invalid data."""
        invalid_data = {
            'colors': {
                'invalid_color': 123  # Invalid color format
            }
        }
        
        with pytest.raises(ThemeValidationError):
            Theme('invalid_theme', sample_theme_metadata, invalid_data)


class TestThemeProvider:
    """Test cases for ThemeProvider abstract class."""
    
    def test_abstract_methods(self):
        """Test that ThemeProvider is abstract."""
        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            ThemeProvider()
            
    def test_concrete_implementation(self):
        """Test concrete implementation of ThemeProvider."""
        class TestProvider(ThemeProvider):
            def load_theme(self, theme_name: str) -> Theme:
                if theme_name == 'test':
                    metadata = ThemeMetadata(
                        name='test', version='1.0.0', description='', 
                        author='', category=ThemeType.LIGHT
                    )
                    return Theme('test', metadata, {'colors': {'primary': '#000000'}})
                raise ThemeNotFoundError(theme_name)
                
            def get_available_themes(self) -> list:
                return ['test']
                
            def theme_exists(self, theme_name: str) -> bool:
                return theme_name == 'test'
                
        provider = TestProvider()
        
        # Test methods work
        assert provider.theme_exists('test')
        assert not provider.theme_exists('nonexistent')
        assert 'test' in provider.get_available_themes()
        
        theme = provider.load_theme('test')
        assert theme.name == 'test'
        
        with pytest.raises(ThemeNotFoundError):
            provider.load_theme('nonexistent')
            
    def test_get_theme_metadata_default(self):
        """Test default implementation of get_theme_metadata."""
        class TestProvider(ThemeProvider):
            def load_theme(self, theme_name: str) -> Theme:
                metadata = ThemeMetadata(
                    name='test', version='1.0.0', description='test description',
                    author='test author', category=ThemeType.LIGHT
                )
                return Theme('test', metadata, {'colors': {'primary': '#000000'}})
                
            def get_available_themes(self) -> list:
                return ['test']
                
            def theme_exists(self, theme_name: str) -> bool:
                return theme_name == 'test'
                
        provider = TestProvider()
        
        # Default implementation loads full theme
        metadata = provider.get_theme_metadata('test')
        assert metadata is not None
        assert metadata.name == 'test'
        assert metadata.description == 'test description'
        
        # Non-existent theme
        metadata = provider.get_theme_metadata('nonexistent')
        assert metadata is None