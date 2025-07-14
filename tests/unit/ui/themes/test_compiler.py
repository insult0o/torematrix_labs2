"""Tests for theme compilation and CSS preprocessing."""

import pytest
from unittest.mock import Mock, patch

from src.torematrix.ui.themes.compiler import (
    ThemeCompiler, CSSPreprocessor, ColorFunctions, MathFunctions,
    CompilationOptions, CompilationResult, PreprocessorFeature
)
from src.torematrix.ui.themes.base import Theme, ColorPalette, Typography
from src.torematrix.ui.themes.types import ThemeMetadata


class TestColorFunctions:
    """Test color manipulation functions."""
    
    def test_lighten_color(self):
        """Test color lightening function."""
        # Test with hex color
        result = ColorFunctions.lighten("#000000", 0.5)
        assert result != "#000000"
        assert result.startswith("#")
        
        # Test with percentage string
        result = ColorFunctions.lighten("#808080", "25%")
        assert result.startswith("#")
        
        # Test invalid color (should return original)
        result = ColorFunctions.lighten("invalid", 0.5)
        assert result == "invalid"
    
    def test_darken_color(self):
        """Test color darkening function."""
        result = ColorFunctions.darken("#ffffff", 0.3)
        assert result != "#ffffff"
        assert result.startswith("#")
        
        # Darkening white should produce a darker color
        assert result < "#ffffff"
    
    def test_saturate_color(self):
        """Test color saturation."""
        result = ColorFunctions.saturate("#808080", 0.5)
        assert result.startswith("#")
        
        # Test with percentage
        result = ColorFunctions.saturate("#ff0000", "50%")
        assert result.startswith("#")
    
    def test_desaturate_color(self):
        """Test color desaturation."""
        result = ColorFunctions.desaturate("#ff0000", 0.3)
        assert result.startswith("#")
    
    def test_rgba_conversion(self):
        """Test RGBA conversion."""
        result = ColorFunctions.rgba("#ff0000", 0.5)
        assert result == "rgba(255, 0, 0, 0.5)"
        
        # Test with string alpha
        result = ColorFunctions.rgba("#00ff00", "0.8")
        assert result == "rgba(0, 255, 0, 0.8)"
    
    def test_mix_colors(self):
        """Test color mixing."""
        result = ColorFunctions.mix("#ff0000", "#0000ff", 0.5)
        assert result.startswith("#")
        
        # Mix red and blue should produce purple-ish
        assert result != "#ff0000"
        assert result != "#0000ff"
        
        # Test with percentage weight
        result = ColorFunctions.mix("#ffffff", "#000000", "25%")
        assert result.startswith("#")


class TestMathFunctions:
    """Test mathematical functions."""
    
    def test_round_value(self):
        """Test value rounding."""
        assert MathFunctions.round_value(3.7) == "4"
        assert MathFunctions.round_value("3.7px") == "4px"
        assert MathFunctions.round_value(3.14159, 2) == "3.14"
    
    def test_min_value(self):
        """Test minimum value function."""
        assert MathFunctions.min_value(5, 3, 8) == "3"
        assert MathFunctions.min_value("10px", "5px", "15px") == "5"
    
    def test_max_value(self):
        """Test maximum value function."""
        assert MathFunctions.max_value(5, 3, 8) == "8"
        assert MathFunctions.max_value("10px", "5px", "15px") == "15"


class TestCSSPreprocessor:
    """Test CSS preprocessor functionality."""
    
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
                'primary': '#007bff',
                'secondary': '#6c757d',
                'background': '#ffffff'
            },
            'typography': {
                'default': {
                    'font_family': 'Arial',
                    'font_size': 14,
                    'font_weight': 400
                }
            },
            'variables': {
                'border_radius': '4px',
                'padding': '8px'
            }
        }
        
        return Theme("test_theme", metadata, theme_data)
    
    @pytest.fixture
    def preprocessor(self, mock_theme):
        """Create CSS preprocessor instance."""
        options = CompilationOptions(
            features=[
                PreprocessorFeature.VARIABLES,
                PreprocessorFeature.MIXINS,
                PreprocessorFeature.FUNCTIONS
            ]
        )
        return CSSPreprocessor(mock_theme, options)
    
    def test_variable_processing(self, preprocessor):
        """Test variable declaration and usage."""
        css_input = """
        @primary-color: #ff0000;
        @font-size: 16px;
        
        .test {
            color: @primary-color;
            font-size: @font-size;
        }
        """
        
        result = preprocessor.process_variables(css_input)
        
        # Variable declarations should be removed
        assert '@primary-color:' not in result
        assert '@font-size:' not in result
        
        # Variables should be replaced
        assert '#ff0000' in result
        assert '16px' in result
    
    def test_theme_variable_loading(self, preprocessor):
        """Test loading variables from theme."""
        # Theme colors should be available as variables
        assert 'color-primary' in preprocessor.variables
        assert preprocessor.variables['color-primary'] == '#007bff'
        
        # Typography should be available
        assert 'font-default-family' in preprocessor.variables
        assert preprocessor.variables['font-default-family'] == 'Arial'
        
        # Custom variables should be loaded
        assert 'border_radius' in preprocessor.variables
        assert preprocessor.variables['border_radius'] == '4px'
    
    def test_mixin_processing(self, preprocessor):
        """Test mixin declaration and inclusion."""
        css_input = """
        @mixin button-style {
            padding: 8px 16px;
            border-radius: 4px;
            border: none;
        }
        
        @mixin button-color($color) {
            background-color: $color;
            color: white;
        }
        
        .button {
            @include button-style;
            @include button-color(#007bff);
        }
        """
        
        result = preprocessor.process_mixins(css_input)
        
        # Mixin declarations should be removed
        assert '@mixin button-style' not in result
        assert '@mixin button-color' not in result
        
        # Mixin includes should be replaced with content
        assert 'padding: 8px 16px' in result
        assert 'border-radius: 4px' in result
        assert '@include' not in result
    
    def test_function_processing(self, preprocessor):
        """Test function calls in CSS."""
        css_input = """
        .test {
            color: lighten(#000000, 50%);
            background: rgba(#ff0000, 0.5);
            border-radius: round(3.7px);
        }
        """
        
        result = preprocessor.process_functions(css_input)
        
        # Function calls should be replaced with results
        assert 'lighten(' not in result
        assert 'rgba(' in result or 'rgba(255, 0, 0, 0.5)' in result
        assert 'round(' not in result
        assert '4px' in result  # rounded value
    
    def test_conditional_processing(self, preprocessor):
        """Test conditional statements."""
        css_input = """
        @if theme.colors.primary {
            .primary-button {
                background: blue;
            }
        } @else {
            .primary-button {
                background: gray;
            }
        }
        """
        
        result = preprocessor.process_conditionals(css_input)
        
        # Should contain the true branch
        assert 'background: blue' in result
        assert 'background: gray' not in result
        assert '@if' not in result
        assert '@else' not in result
    
    def test_css_compilation(self, preprocessor):
        """Test complete CSS compilation."""
        css_input = """
        @primary: #007bff;
        
        @mixin button-base {
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
        }
        
        .button {
            @include button-base;
            background: @primary;
            color: rgba(@primary, 0.9);
        }
        """
        
        result = preprocessor.compile(css_input)
        
        assert isinstance(result, CompilationResult)
        assert result.compiled_css
        assert result.compilation_time > 0
        
        # Check that processing worked
        css = result.compiled_css
        assert 'padding: 8px 16px' in css
        assert '#007bff' in css
        assert '@primary' not in css
        assert '@include' not in css
        assert '@mixin' not in css
    
    def test_minification(self, preprocessor):
        """Test CSS minification."""
        css_input = """
        /* Comment */
        .test {
            color: red;
            
            padding: 10px;
        }
        """
        
        minified = preprocessor.minify_css(css_input)
        
        # Comments should be removed
        assert '/*' not in minified
        assert '*/' not in minified
        
        # Extra whitespace should be removed
        assert len(minified) < len(css_input)
        assert 'color:red' in minified or 'color: red' in minified


class TestThemeCompiler:
    """Test high-level theme compiler."""
    
    @pytest.fixture
    def mock_theme(self):
        """Create mock theme for testing."""
        metadata = ThemeMetadata(
            name="compiler_test",
            version="1.0.0",
            description="Compiler test theme",
            author="Test Suite",
            category="dark"
        )
        
        theme_data = {
            'colors': {
                'primary': '#17a2b8',
                'background': '#212529',
                'text': '#ffffff'
            },
            'typography': {
                'heading': {
                    'font_family': 'Roboto',
                    'font_size': 18,
                    'font_weight': 600
                }
            }
        }
        
        return Theme("compiler_test", metadata, theme_data)
    
    @pytest.fixture
    def compiler(self):
        """Create theme compiler instance."""
        return ThemeCompiler()
    
    def test_theme_compilation(self, compiler, mock_theme):
        """Test complete theme compilation."""
        css_input = """
        @primary: ${colors.primary};
        
        .header {
            background: @primary;
            color: ${colors.text};
            font-family: ${typography.heading.font_family};
        }
        """
        
        options = CompilationOptions(
            features=[PreprocessorFeature.VARIABLES],
            minify=False
        )
        
        result = compiler.compile_theme(mock_theme, css_input, options)
        
        assert isinstance(result, CompilationResult)
        assert result.compiled_css
        assert '#17a2b8' in result.compiled_css  # primary color
        assert '#ffffff' in result.compiled_css  # text color
        assert 'Roboto' in result.compiled_css   # font family
        assert result.compilation_time > 0
    
    def test_compilation_caching(self, compiler, mock_theme):
        """Test compilation result caching."""
        css_input = ".test { color: red; }"
        
        # First compilation
        result1 = compiler.compile_theme(mock_theme, css_input)
        
        # Second compilation should use cache
        css_hash = hash(css_input)
        cached_result = compiler.get_cached_result(mock_theme.name, css_hash)
        
        assert cached_result is not None
        assert cached_result.compiled_css == result1.compiled_css
    
    def test_cache_clearing(self, compiler, mock_theme):
        """Test cache clearing."""
        css_input = ".test { color: blue; }"
        
        # Compile to populate cache
        compiler.compile_theme(mock_theme, css_input)
        
        # Clear cache
        compiler.clear_cache()
        
        # Should not find cached result
        css_hash = hash(css_input)
        cached_result = compiler.get_cached_result(mock_theme.name, css_hash)
        assert cached_result is None


class TestCompilationOptions:
    """Test compilation options."""
    
    def test_default_options(self):
        """Test default compilation options."""
        options = CompilationOptions()
        
        assert PreprocessorFeature.VARIABLES in options.features
        assert PreprocessorFeature.MIXINS in options.features
        assert PreprocessorFeature.FUNCTIONS in options.features
        assert options.minify is False
        assert options.source_map is False
        assert options.strict_mode is True
        assert isinstance(options.custom_functions, dict)
        assert isinstance(options.import_paths, list)
    
    def test_custom_options(self):
        """Test custom compilation options."""
        custom_func = lambda x: x
        import_paths = ['/path/to/styles']
        
        options = CompilationOptions(
            features=[PreprocessorFeature.VARIABLES],
            minify=True,
            source_map=True,
            strict_mode=False,
            custom_functions={'custom': custom_func},
            import_paths=import_paths
        )
        
        assert options.features == [PreprocessorFeature.VARIABLES]
        assert options.minify is True
        assert options.source_map is True
        assert options.strict_mode is False
        assert 'custom' in options.custom_functions
        assert options.import_paths == import_paths


class TestCompilationResult:
    """Test compilation result object."""
    
    def test_result_initialization(self):
        """Test compilation result initialization."""
        result = CompilationResult(compiled_css="test css")
        
        assert result.compiled_css == "test css"
        assert result.source_map is None
        assert result.variables_used == []
        assert result.mixins_used == []
        assert result.functions_called == []
        assert result.compilation_time == 0.0
        assert result.warnings == []
        assert result.errors == []
    
    def test_result_with_data(self):
        """Test compilation result with tracking data."""
        result = CompilationResult(
            compiled_css=".test { color: red; }",
            variables_used=['primary-color'],
            mixins_used=['button-style'],
            functions_called=['lighten'],
            compilation_time=25.5,
            warnings=['Unused variable'],
            errors=[]
        )
        
        assert result.compiled_css == ".test { color: red; }"
        assert 'primary-color' in result.variables_used
        assert 'button-style' in result.mixins_used
        assert 'lighten' in result.functions_called
        assert result.compilation_time == 25.5
        assert 'Unused variable' in result.warnings
        assert len(result.errors) == 0


@pytest.mark.integration
class TestCompilerIntegration:
    """Integration tests for the compiler system."""
    
    def test_full_compilation_pipeline(self):
        """Test complete compilation from theme to final CSS."""
        # Create comprehensive theme
        metadata = ThemeMetadata(
            name="integration_theme",
            version="1.0.0",
            description="Integration test theme",
            author="Test Suite",
            category="light"
        )
        
        theme_data = {
            'colors': {
                'primary': '#007bff',
                'secondary': '#6c757d',
                'success': '#28a745',
                'background': '#ffffff',
                'text': '#212529'
            },
            'typography': {
                'default': {
                    'font_family': 'system-ui',
                    'font_size': 14,
                    'font_weight': 400
                },
                'heading': {
                    'font_family': 'system-ui',
                    'font_size': 24,
                    'font_weight': 600
                }
            },
            'variables': {
                'border_radius': '6px',
                'spacing_unit': '8px'
            }
        }
        
        theme = Theme("integration_theme", metadata, theme_data)
        compiler = ThemeCompiler()
        
        # Complex CSS with all features
        css_input = """
        /* Theme variables */
        @primary: ${colors.primary};
        @bg: ${colors.background};
        @radius: ${variables.border_radius};
        
        /* Mixins */
        @mixin card-style {
            background: @bg;
            border-radius: @radius;
            padding: ${variables.spacing_unit};
        }
        
        @mixin button-variant($color) {
            background: $color;
            border: 1px solid darken($color, 10%);
            color: rgba(#ffffff, 0.9);
        }
        
        /* Components */
        .card {
            @include card-style;
            box-shadow: 0 2px 4px rgba(#000000, 0.1);
        }
        
        .btn-primary {
            @include button-variant(@primary);
            font-family: ${typography.default.font_family};
        }
        
        .btn-success {
            @include button-variant(${colors.success});
        }
        """
        
        options = CompilationOptions(
            features=[
                PreprocessorFeature.VARIABLES,
                PreprocessorFeature.MIXINS,
                PreprocessorFeature.FUNCTIONS
            ],
            minify=False,
            strict_mode=True
        )
        
        result = compiler.compile_theme(theme, css_input, options)
        
        # Verify compilation was successful
        assert result.compiled_css
        assert len(result.errors) == 0
        assert result.compilation_time > 0
        
        css = result.compiled_css
        
        # Verify variables were resolved
        assert '#007bff' in css  # primary color
        assert '#ffffff' in css  # background
        assert '6px' in css      # border radius
        assert '8px' in css      # spacing unit
        
        # Verify mixins were expanded
        assert 'padding: 8px' in css
        assert 'border-radius: 6px' in css
        
        # Verify functions were processed
        assert 'rgba(' in css
        assert 'darken(' not in css  # Should be processed
        
        # Verify typography was applied
        assert 'system-ui' in css
        
        # Verify preprocessing artifacts are removed
        assert '@primary:' not in css
        assert '@include' not in css
        assert '@mixin' not in css
        
        # Verify tracking data
        assert len(result.variables_used) > 0
        assert len(result.mixins_used) > 0
        assert len(result.functions_called) > 0