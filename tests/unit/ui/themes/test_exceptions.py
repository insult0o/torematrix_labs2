"""Tests for theme exceptions."""

import pytest

from torematrix.ui.themes.exceptions import (
    ThemeError, ThemeNotFoundError, ThemeValidationError,
    ThemeLoadError, ThemeFormatError, StyleSheetGenerationError
)


class TestThemeError:
    """Test cases for base ThemeError."""
    
    def test_basic_theme_error(self):
        """Test basic theme error creation."""
        error = ThemeError("Test error message")
        assert str(error) == "Test error message"
        assert error.theme_name is None
        
    def test_theme_error_with_theme_name(self):
        """Test theme error with theme name."""
        error = ThemeError("Test error", "test_theme")
        assert str(error) == "Test error"
        assert error.theme_name == "test_theme"
        
    def test_theme_error_inheritance(self):
        """Test that ThemeError inherits from Exception."""
        error = ThemeError("Test")
        assert isinstance(error, Exception)


class TestThemeNotFoundError:
    """Test cases for ThemeNotFoundError."""
    
    def test_theme_not_found_error(self):
        """Test theme not found error creation."""
        error = ThemeNotFoundError("missing_theme")
        assert "Theme 'missing_theme' not found" in str(error)
        assert error.theme_name == "missing_theme"
        
    def test_theme_not_found_inheritance(self):
        """Test inheritance from ThemeError."""
        error = ThemeNotFoundError("test")
        assert isinstance(error, ThemeError)
        assert isinstance(error, Exception)


class TestThemeValidationError:
    """Test cases for ThemeValidationError."""
    
    def test_validation_error_basic(self):
        """Test basic validation error."""
        error = ThemeValidationError("Invalid theme data")
        assert str(error) == "Invalid theme data"
        assert error.theme_name is None
        assert error.field is None
        
    def test_validation_error_with_theme(self):
        """Test validation error with theme name."""
        error = ThemeValidationError("Invalid data", "test_theme")
        assert str(error) == "Invalid data"
        assert error.theme_name == "test_theme"
        
    def test_validation_error_with_field(self):
        """Test validation error with field information."""
        error = ThemeValidationError("Invalid field", "test_theme", "colors.primary")
        assert str(error) == "Invalid field"
        assert error.theme_name == "test_theme"
        assert error.field == "colors.primary"
        
    def test_validation_error_inheritance(self):
        """Test inheritance from ThemeError."""
        error = ThemeValidationError("Test")
        assert isinstance(error, ThemeError)


class TestThemeLoadError:
    """Test cases for ThemeLoadError."""
    
    def test_theme_load_error(self):
        """Test theme load error creation."""
        error = ThemeLoadError("test_theme", "File not found")
        assert "Failed to load theme 'test_theme': File not found" in str(error)
        assert error.theme_name == "test_theme"
        assert error.reason == "File not found"
        
    def test_theme_load_error_inheritance(self):
        """Test inheritance from ThemeError."""
        error = ThemeLoadError("test", "reason")
        assert isinstance(error, ThemeError)


class TestThemeFormatError:
    """Test cases for ThemeFormatError."""
    
    def test_theme_format_error(self):
        """Test theme format error creation."""
        error = ThemeFormatError("/path/to/theme.txt", "Unsupported format")
        assert "Invalid theme file format '/path/to/theme.txt': Unsupported format" in str(error)
        assert error.file_path == "/path/to/theme.txt"
        assert error.reason == "Unsupported format"
        
    def test_theme_format_error_inheritance(self):
        """Test inheritance from ThemeError."""
        error = ThemeFormatError("path", "reason")
        assert isinstance(error, ThemeError)


class TestStyleSheetGenerationError:
    """Test cases for StyleSheetGenerationError."""
    
    def test_stylesheet_generation_error(self):
        """Test stylesheet generation error creation."""
        error = StyleSheetGenerationError("dark_theme", "button", "Invalid color")
        expected_message = "Failed to generate stylesheet for 'button' in theme 'dark_theme': Invalid color"
        assert expected_message in str(error)
        assert error.theme_name == "dark_theme"
        assert error.component == "button"
        assert error.reason == "Invalid color"
        
    def test_stylesheet_generation_error_inheritance(self):
        """Test inheritance from ThemeError."""
        error = StyleSheetGenerationError("theme", "component", "reason")
        assert isinstance(error, ThemeError)


class TestExceptionChaining:
    """Test exception chaining and context."""
    
    def test_exception_raise_and_catch(self):
        """Test raising and catching theme exceptions."""
        with pytest.raises(ThemeNotFoundError) as excinfo:
            raise ThemeNotFoundError("test_theme")
            
        assert excinfo.value.theme_name == "test_theme"
        assert "not found" in str(excinfo.value)
        
    def test_exception_chaining(self):
        """Test exception chaining with original cause."""
        original_error = ValueError("Original error")
        
        try:
            raise original_error
        except ValueError as e:
            theme_error = ThemeLoadError("test_theme", f"Caused by: {e}")
            
        assert "Caused by: Original error" in str(theme_error)
        
    def test_multiple_exception_types(self):
        """Test catching multiple exception types."""
        exceptions_to_test = [
            ThemeNotFoundError("theme"),
            ThemeValidationError("validation"),
            ThemeLoadError("theme", "reason"),
            ThemeFormatError("file", "reason"),
            StyleSheetGenerationError("theme", "component", "reason")
        ]
        
        for exception in exceptions_to_test:
            with pytest.raises(ThemeError):
                raise exception
                
            # Test that specific type is also caught
            with pytest.raises(type(exception)):
                raise exception