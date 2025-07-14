"""Tests for theme stylesheet generation system."""

import pytest
import time
from unittest.mock import Mock, patch

from src.torematrix.ui.themes.styles import (
    StyleSheetGenerator, GenerationOptions, GenerationMetrics,
    ComponentStyleGenerator, MainWindowStyleGenerator, 
    MenuBarStyleGenerator, ButtonStyleGenerator,
    StyleSheetTarget
)
from src.torematrix.ui.themes.base import Theme, ColorPalette, Typography
from src.torematrix.ui.themes.types import (
    ThemeMetadata, ComponentType, ColorDefinition, TypographyDefinition
)


class TestStyleSheetGenerator:
    """Test StyleSheetGenerator class."""
    
    @pytest.fixture
    def mock_theme(self):
        """Create mock theme for testing."""
        metadata = ThemeMetadata(
            name="test_theme",
            version="1.0.0",
            description="Test theme",
            author="Test Author",
            category="light"
        )
        
        theme_data = {
            'colors': {
                'background': '#ffffff',
                'text_primary': '#000000',
                'accent': '#007bff',
                'surface': '#f5f5f5',
                'border': '#dee2e6'
            },
            'typography': {
                'default': {
                    'font_family': 'Arial',
                    'font_size': 12,
                    'font_weight': 400
                }
            }
        }
        
        return Theme("test_theme", metadata, theme_data)
    
    @pytest.fixture
    def generator(self):
        """Create StyleSheetGenerator instance."""
        return StyleSheetGenerator()
    
    def test_generator_initialization(self, generator):
        """Test generator initialization."""
        assert generator is not None
        assert len(generator._component_generators) > 0
        assert ComponentType.MAIN_WINDOW in generator._component_generators
        assert ComponentType.MENU_BAR in generator._component_generators
        assert ComponentType.BUTTON in generator._component_generators
    
    def test_generate_stylesheet_basic(self, generator, mock_theme):
        """Test basic stylesheet generation."""
        stylesheet = generator.generate_stylesheet(mock_theme)
        
        assert isinstance(stylesheet, str)
        assert len(stylesheet) > 0
        assert 'QMainWindow' in stylesheet
        assert '#ffffff' in stylesheet  # background color
        assert '#000000' in stylesheet  # text color
    
    def test_generate_stylesheet_with_options(self, generator, mock_theme):
        """Test stylesheet generation with options."""
        options = GenerationOptions(
            include_comments=True,
            minify=False,
            optimize_selectors=True
        )
        
        stylesheet = generator.generate_stylesheet(mock_theme, options=options)
        
        assert '/* ' in stylesheet  # Comments included
        assert len(stylesheet) > 0
    
    def test_generate_stylesheet_minified(self, generator, mock_theme):
        """Test minified stylesheet generation."""
        options = GenerationOptions(minify=True, include_comments=False)
        
        stylesheet = generator.generate_stylesheet(mock_theme, options=options)
        
        # Should not contain comments when minified
        assert '/* ' not in stylesheet
        assert len(stylesheet) > 0
    
    def test_generate_stylesheet_specific_components(self, generator, mock_theme):
        """Test stylesheet generation for specific components."""
        components = [ComponentType.MAIN_WINDOW, ComponentType.BUTTON]
        
        stylesheet = generator.generate_stylesheet(
            mock_theme, 
            components=components
        )
        
        assert 'QMainWindow' in stylesheet
        assert 'QPushButton' in stylesheet
        # Should not contain menu bar styles
        assert 'QMenuBar' not in stylesheet
    
    def test_performance_tracking(self, generator, mock_theme):
        """Test performance metrics tracking."""
        stylesheet = generator.generate_stylesheet(mock_theme)
        
        metrics = generator.get_generation_metrics(mock_theme.name)
        assert metrics is not None
        assert metrics.generation_time > 0
        assert metrics.output_size == len(stylesheet)
        assert metrics.rules_count > 0
    
    def test_performance_targets(self, generator, mock_theme):
        """Test that performance targets are met."""
        start_time = time.time()
        stylesheet = generator.generate_stylesheet(mock_theme)
        generation_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Should generate stylesheet in under 100ms
        assert generation_time < 100
        assert len(stylesheet) > 0
    
    def test_variable_resolution(self, generator, mock_theme):
        """Test theme variable resolution."""
        # Mock theme with variables
        mock_theme._data['test_variable'] = 'test_value'
        
        test_css = "color: ${test_variable};"
        resolved = generator._resolve_variables(test_css, mock_theme, GenerationOptions())
        
        assert 'test_value' in resolved
        assert '${test_variable}' not in resolved
    
    def test_stylesheet_optimization(self, generator):
        """Test stylesheet optimization."""
        test_css = """
        .test { color: red; }
        .test { color: red; }
        .empty { }
        .whitespace   {   color:   blue;   }
        """
        
        options = GenerationOptions(minify=True, merge_rules=True)
        optimized = generator._optimize_stylesheet(test_css, options)
        
        # Should be shorter than original
        assert len(optimized) < len(test_css)
        # Should not contain duplicate rules
        assert optimized.count('.test { color: red; }') <= 1
    
    def test_stylesheet_validation(self, generator):
        """Test stylesheet validation."""
        # Valid CSS
        valid_css = ".test { color: red; }"
        assert generator._validate_stylesheet(valid_css) is True
        
        # Invalid CSS (unbalanced braces)
        invalid_css = ".test { color: red;"
        with pytest.raises(Exception):
            generator._validate_stylesheet(invalid_css)
    
    def test_compile_component_styles(self, generator, mock_theme):
        """Test component-specific style compilation."""
        component_css = generator.compile_component_styles(
            mock_theme, 
            ComponentType.BUTTON
        )
        
        assert isinstance(component_css, str)
        assert 'QPushButton' in component_css
        assert len(component_css) > 0
    
    def test_register_custom_generator(self, generator):
        """Test registering custom component generator."""
        class CustomGenerator(ComponentStyleGenerator):
            def __init__(self):
                super().__init__(ComponentType.MAIN_WINDOW)
            
            def generate(self, theme, options):
                return "/* Custom styles */"
        
        custom_gen = CustomGenerator()
        generator.register_component_generator(ComponentType.MAIN_WINDOW, custom_gen)
        
        assert generator._component_generators[ComponentType.MAIN_WINDOW] == custom_gen


class TestComponentStyleGenerators:
    """Test component-specific style generators."""
    
    @pytest.fixture
    def mock_theme(self):
        """Create mock theme for testing."""
        metadata = ThemeMetadata(
            name="test_theme",
            version="1.0.0",
            description="Test theme",
            author="Test Author",
            category="light"
        )
        
        theme_data = {
            'colors': {
                'background': '#ffffff',
                'text_primary': '#000000',
                'surface': '#f5f5f5',
                'border': '#dee2e6',
                'accent': '#007bff',
                'accent_dark': '#0056b3',
                'accent_light': '#66b3ff',
                'button_background': '#ffffff',
                'button_border': '#ced4da',
                'button_hover': '#e9ecef',
                'button_pressed': '#dee2e6',
                'button_disabled': '#f8f9fa',
                'text_disabled': '#6c757d'
            },
            'typography': {
                'default': {
                    'font_family': 'Arial',
                    'font_size': 12,
                    'font_weight': 400
                }
            },
            'components': {
                'main_window': {},
                'menu_bar': {},
                'button': {}
            }
        }
        
        return Theme("test_theme", metadata, theme_data)
    
    def test_main_window_generator(self, mock_theme):
        """Test MainWindowStyleGenerator."""
        generator = MainWindowStyleGenerator(ComponentType.MAIN_WINDOW)
        options = GenerationOptions()
        
        css = generator.generate(mock_theme, options)
        
        assert 'QMainWindow' in css
        assert '#ffffff' in css  # background color
        assert '#000000' in css  # text color
    
    def test_menu_bar_generator(self, mock_theme):
        """Test MenuBarStyleGenerator."""
        generator = MenuBarStyleGenerator(ComponentType.MENU_BAR)
        options = GenerationOptions()
        
        css = generator.generate(mock_theme, options)
        
        assert 'QMenuBar' in css
        assert 'QMenu' in css
        assert '#f5f5f5' in css  # surface color
    
    def test_button_generator(self, mock_theme):
        """Test ButtonStyleGenerator."""
        generator = ButtonStyleGenerator(ComponentType.BUTTON)
        options = GenerationOptions()
        
        css = generator.generate(mock_theme, options)
        
        assert 'QPushButton' in css
        assert ':hover' in css
        assert ':pressed' in css
        assert ':disabled' in css
        assert ':default' in css
    
    def test_generator_validation(self, mock_theme):
        """Test component generator validation."""
        generator = MainWindowStyleGenerator(ComponentType.MAIN_WINDOW)
        
        # Should validate successfully with proper theme
        assert generator.validate_component_data(mock_theme) is True
        
        # Test with theme missing component styles
        mock_theme._component_styles.clear()
        # Should still work as validation is flexible
        assert generator.validate_component_data(mock_theme) is True
    
    def test_generator_default_selectors(self):
        """Test default selectors for generators."""
        main_gen = MainWindowStyleGenerator(ComponentType.MAIN_WINDOW)
        menu_gen = MenuBarStyleGenerator(ComponentType.MENU_BAR)
        button_gen = ButtonStyleGenerator(ComponentType.BUTTON)
        
        assert 'QMainWindow' in main_gen.get_default_selectors()
        assert 'QMenuBar' in menu_gen.get_default_selectors()
        assert 'QPushButton' in button_gen.get_default_selectors()


class TestGenerationOptions:
    """Test GenerationOptions class."""
    
    def test_default_options(self):
        """Test default generation options."""
        options = GenerationOptions()
        
        assert options.minify is False
        assert options.include_comments is True
        assert options.optimize_selectors is True
        assert options.merge_rules is True
        assert options.validate_css is True
        assert options.target == StyleSheetTarget.APPLICATION
        assert isinstance(options.custom_variables, dict)
    
    def test_custom_options(self):
        """Test custom generation options."""
        custom_vars = {'primary': '#ff0000'}
        
        options = GenerationOptions(
            minify=True,
            include_comments=False,
            custom_variables=custom_vars,
            target=StyleSheetTarget.WIDGET
        )
        
        assert options.minify is True
        assert options.include_comments is False
        assert options.custom_variables == custom_vars
        assert options.target == StyleSheetTarget.WIDGET


class TestGenerationMetrics:
    """Test GenerationMetrics class."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = GenerationMetrics()
        
        assert metrics.generation_time == 0.0
        assert metrics.output_size == 0
        assert metrics.rules_count == 0
        assert metrics.selectors_count == 0
        assert metrics.variables_resolved == 0
        assert metrics.optimization_savings == 0
        assert metrics.cache_hit is False
    
    def test_metrics_with_values(self):
        """Test metrics with actual values."""
        metrics = GenerationMetrics(
            generation_time=50.5,
            output_size=1024,
            rules_count=25,
            cache_hit=True
        )
        
        assert metrics.generation_time == 50.5
        assert metrics.output_size == 1024
        assert metrics.rules_count == 25
        assert metrics.cache_hit is True


@pytest.mark.integration
class TestStyleSheetGeneratorIntegration:
    """Integration tests for stylesheet generator."""
    
    def test_full_generation_pipeline(self):
        """Test complete stylesheet generation pipeline."""
        # Create a realistic theme
        metadata = ThemeMetadata(
            name="integration_theme",
            version="1.0.0",
            description="Integration test theme",
            author="Test Suite",
            category="light"
        )
        
        theme_data = {
            'colors': {
                'background': '#ffffff',
                'text_primary': '#333333',
                'surface': '#f8f9fa',
                'border': '#dee2e6',
                'accent': '#007bff',
                'accent_dark': '#0056b3',
                'button_background': '#ffffff',
                'button_hover': '#e9ecef'
            },
            'typography': {
                'default': {
                    'font_family': 'system-ui',
                    'font_size': 14,
                    'font_weight': 400
                }
            },
            'variables': {
                'border_radius': '4px'
            },
            'components': {
                'main_window': {},
                'menu_bar': {},
                'button': {}
            }
        }
        
        theme = Theme("integration_theme", metadata, theme_data)
        generator = StyleSheetGenerator()
        
        # Generate complete stylesheet
        start_time = time.time()
        stylesheet = generator.generate_stylesheet(theme)
        generation_time = (time.time() - start_time) * 1000
        
        # Verify results
        assert isinstance(stylesheet, str)
        assert len(stylesheet) > 500  # Should be substantial
        assert generation_time < 100  # Should be fast
        
        # Verify all components are included
        assert 'QMainWindow' in stylesheet
        assert 'QMenuBar' in stylesheet
        assert 'QPushButton' in stylesheet
        
        # Verify colors are applied
        assert '#ffffff' in stylesheet
        assert '#333333' in stylesheet
        assert '#007bff' in stylesheet
        
        # Verify typography is applied
        assert 'system-ui' in stylesheet
        assert '14px' in stylesheet
        
        # Verify metrics are tracked
        metrics = generator.get_generation_metrics(theme.name)
        assert metrics is not None
        assert metrics.generation_time > 0
        assert metrics.output_size == len(stylesheet)