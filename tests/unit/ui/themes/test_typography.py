"""Tests for typography system and font management."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from src.torematrix.ui.themes.typography import (
    TypographyManager, FontManager, TypographyScale,
    FontDefinition, FontWeight, FontCategory, FontMetrics
)


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestFontDefinition:
    """Test font definition data class."""
    
    def test_font_definition_creation(self):
        """Test font definition creation with defaults."""
        definition = FontDefinition(
            family="Arial",
            size=14
        )
        
        assert definition.family == "Arial"
        assert definition.size == 14
        assert definition.weight == FontWeight.NORMAL.value
        assert definition.italic is False
        assert definition.line_height == 1.4
        assert definition.letter_spacing == 0.0
        assert definition.category == FontCategory.SANS_SERIF
        assert definition.fallbacks == []
    
    def test_font_definition_with_fallbacks(self):
        """Test font definition with fallback fonts."""
        definition = FontDefinition(
            family="Custom Font",
            size=16,
            fallbacks=["Arial", "sans-serif"]
        )
        
        assert definition.fallbacks == ["Arial", "sans-serif"]


class TestTypographyScale:
    """Test typography scale functionality."""
    
    def test_create_modular_scale(self):
        """Test modular scale creation."""
        scale = TypographyScale.create_modular_scale("test", 16, 1.25)
        
        assert scale.name == "test"
        assert scale.base_size == 16
        assert scale.ratio == 1.25
        assert 'base' in scale.sizes
        assert scale.sizes['base'] == 16
        assert 'lg' in scale.sizes
        assert 'sm' in scale.sizes
        
        # Check that larger sizes are actually larger
        assert scale.sizes['lg'] > scale.sizes['base']
        assert scale.sizes['xl'] > scale.sizes['lg']
        
        # Check that smaller sizes are actually smaller
        assert scale.sizes['sm'] < scale.sizes['base']
        assert scale.sizes['xs'] < scale.sizes['sm']
    
    def test_scale_ratio_effects(self):
        """Test different scale ratios."""
        small_ratio = TypographyScale.create_modular_scale("small", 16, 1.1)
        large_ratio = TypographyScale.create_modular_scale("large", 16, 1.5)
        
        # Larger ratio should create bigger size differences
        small_diff = small_ratio.sizes['xl'] - small_ratio.sizes['base']
        large_diff = large_ratio.sizes['xl'] - large_ratio.sizes['base']
        
        assert large_diff > small_diff


class TestFontManager:
    """Test font manager functionality."""
    
    @pytest.fixture
    def font_manager(self, qapp):
        """Create font manager for testing."""
        return FontManager()
    
    def test_font_manager_initialization(self, font_manager):
        """Test font manager initialization."""
        assert font_manager is not None
        assert isinstance(font_manager._system_fonts, list)
        assert len(font_manager._system_fonts) > 0
        assert FontCategory.SANS_SERIF in font_manager.fallback_chains
        assert FontCategory.MONOSPACE in font_manager.fallback_chains
    
    def test_validate_font_availability(self, font_manager):
        """Test font availability validation."""
        # Test with a common system font
        assert font_manager.validate_font_availability("Arial") or \
               font_manager.validate_font_availability("DejaVu Sans")
        
        # Test with non-existent font
        assert not font_manager.validate_font_availability("NonExistentFont12345")
    
    def test_create_font_basic(self, font_manager):
        """Test basic font creation."""
        definition = FontDefinition(
            family="Arial",
            size=14,
            weight=FontWeight.NORMAL.value
        )
        
        font = font_manager.create_font(definition)
        
        assert isinstance(font, QFont)
        assert font.pointSize() == 14
        assert font.weight().value == FontWeight.NORMAL.value
    
    def test_create_font_with_scaling(self, font_manager):
        """Test font creation with scaling."""
        definition = FontDefinition(family="Arial", size=14)
        
        # Test different scale factors
        font_1x = font_manager.create_font(definition, 1.0)
        font_2x = font_manager.create_font(definition, 2.0)
        font_half = font_manager.create_font(definition, 0.5)
        
        assert font_2x.pointSize() == 28  # 14 * 2
        assert font_half.pointSize() == 7  # 14 * 0.5
        assert font_1x.pointSize() == 14
    
    def test_font_fallback_selection(self, font_manager):
        """Test font fallback selection."""
        # Test with non-existent primary font but valid fallback
        definition = FontDefinition(
            family="NonExistentFont12345",
            size=14,
            fallbacks=["Arial", "sans-serif"]
        )
        
        font = font_manager.create_font(definition)
        
        # Should fall back to a valid font
        assert isinstance(font, QFont)
        assert font.pointSize() == 14
    
    @patch.object(QFontDatabase, 'addApplicationFont')
    def test_load_font_family(self, mock_add_font, font_manager):
        """Test loading custom font family."""
        # Mock successful font loading
        mock_add_font.return_value = 1
        
        with patch.object(font_manager.font_database, 'applicationFontFamilies') as mock_families:
            mock_families.return_value = ["Custom Font"]
            
            result = font_manager.load_font_family("Custom Font", ["/fake/path.ttf"])
            
            assert result is True
            assert "Custom Font" in font_manager._custom_fonts
    
    def test_get_font_metrics(self, font_manager):
        """Test font metrics calculation."""
        definition = FontDefinition(family="Arial", size=14)
        font = font_manager.create_font(definition)
        
        metrics = font_manager.get_font_metrics(font)
        
        assert isinstance(metrics, FontMetrics)
        assert metrics.family == font.family()
        assert metrics.point_size == font.pointSize()
        assert metrics.weight == font.weight().value
        assert metrics.height > 0
        assert metrics.ascent > 0
    
    def test_cache_functionality(self, font_manager):
        """Test font caching."""
        definition = FontDefinition(family="Arial", size=14)
        
        # Create same font twice
        font1 = font_manager.create_font(definition)
        font2 = font_manager.create_font(definition)
        
        # Should be equivalent but different instances
        assert font1.family() == font2.family()
        assert font1.pointSize() == font2.pointSize()
        
        # Clear cache and verify
        initial_cache_size = len(font_manager._font_cache)
        font_manager.clear_cache()
        assert len(font_manager._font_cache) == 0


class TestTypographyManager:
    """Test typography manager functionality."""
    
    @pytest.fixture
    def typography_manager(self, qapp):
        """Create typography manager for testing."""
        return TypographyManager()
    
    def test_typography_manager_initialization(self, typography_manager):
        """Test typography manager initialization."""
        assert typography_manager is not None
        assert isinstance(typography_manager.font_manager, FontManager)
        assert len(typography_manager._typography_definitions) > 0
        assert len(typography_manager._typography_scales) > 0
        
        # Check built-in definitions
        assert 'default' in typography_manager._typography_definitions
        assert 'body' in typography_manager._typography_definitions
        assert 'heading' in typography_manager._typography_definitions
        
        # Check built-in scales
        assert 'professional' in typography_manager._typography_scales
        assert 'compact' in typography_manager._typography_scales
    
    def test_create_typography_scale(self, typography_manager):
        """Test typography scale creation."""
        scale = typography_manager.create_typography_scale("test_scale", 16, 1.3)
        
        assert isinstance(scale, TypographyScale)
        assert scale.name == "test_scale"
        assert scale.base_size == 16
        assert scale.ratio == 1.3
        assert "test_scale" in typography_manager._typography_scales
    
    def test_set_typography_scale(self, typography_manager):
        """Test setting active typography scale."""
        # Test setting existing scale
        result = typography_manager.set_typography_scale("professional")
        assert result is True
        assert typography_manager._current_scale is not None
        assert typography_manager._current_scale.name == "professional"
        
        # Test setting non-existent scale
        result = typography_manager.set_typography_scale("nonexistent")
        assert result is False
    
    def test_register_font_definition(self, typography_manager):
        """Test registering custom font definition."""
        definition = FontDefinition(
            family="Test Font",
            size=16,
            weight=FontWeight.BOLD.value
        )
        
        typography_manager.register_font_definition("test_font", definition)
        
        assert "test_font" in typography_manager._typography_definitions
        assert typography_manager._typography_definitions["test_font"] == definition
    
    def test_get_font(self, typography_manager):
        """Test font retrieval."""
        # Test getting existing font
        font = typography_manager.get_font("body")
        assert isinstance(font, QFont)
        
        # Test getting non-existent font
        font = typography_manager.get_font("nonexistent")
        assert isinstance(font, QFont)  # Should return default
    
    def test_get_font_with_overrides(self, typography_manager):
        """Test font retrieval with overrides."""
        # Test size override
        font_normal = typography_manager.get_font("body")
        font_large = typography_manager.get_font("body", size_override=20)
        
        assert font_large.pointSize() == 20
        assert font_large.pointSize() != font_normal.pointSize()
        
        # Test scale factor override
        font_scaled = typography_manager.get_font("body", scale_factor=2.0)
        assert font_scaled.pointSize() > font_normal.pointSize()
    
    def test_get_font_from_scale(self, typography_manager):
        """Test getting font from typography scale."""
        # Set up scale
        typography_manager.set_typography_scale("professional")
        
        # Test getting different sizes
        base_font = typography_manager.get_font_from_scale("professional", "base")
        lg_font = typography_manager.get_font_from_scale("professional", "lg")
        sm_font = typography_manager.get_font_from_scale("professional", "sm")
        
        assert base_font is not None
        assert lg_font is not None
        assert sm_font is not None
        
        # Larger size should have larger point size
        assert lg_font.pointSize() > base_font.pointSize()
        assert base_font.pointSize() > sm_font.pointSize()
    
    def test_global_scale_factor(self, typography_manager):
        """Test global scale factor functionality."""
        # Test setting scale factor
        typography_manager.set_global_scale_factor(1.5)
        assert typography_manager.get_global_scale_factor() == 1.5
        
        # Test bounds
        typography_manager.set_global_scale_factor(0.1)  # Too small
        assert typography_manager.get_global_scale_factor() == 0.5  # Should be clamped
        
        typography_manager.set_global_scale_factor(5.0)  # Too large
        assert typography_manager.get_global_scale_factor() == 3.0  # Should be clamped
    
    def test_generate_text_styles(self, typography_manager):
        """Test text style generation."""
        styles = typography_manager.generate_text_styles("body")
        
        assert isinstance(styles, dict)
        assert len(styles) > 0
        
        # Check for expected styles
        expected_styles = ['h1', 'h2', 'h3', 'body', 'caption', 'button']
        for style in expected_styles:
            assert style in styles
            assert isinstance(styles[style], QFont)
        
        # Check that headings are larger than body
        assert styles['h1'].pointSize() > styles['body'].pointSize()
        assert styles['h2'].pointSize() > styles['body'].pointSize()
    
    def test_get_font_metrics(self, typography_manager):
        """Test font metrics retrieval."""
        metrics = typography_manager.get_font_metrics("body")
        
        assert metrics is not None
        assert isinstance(metrics, FontMetrics)
        assert metrics.height > 0
        assert metrics.family != ""
    
    def test_save_and_load_typography(self, typography_manager, tmp_path):
        """Test typography persistence."""
        # Create custom definition
        custom_def = FontDefinition(
            family="Custom Font",
            size=18,
            weight=FontWeight.BOLD.value
        )
        typography_manager.register_font_definition("custom", custom_def)
        
        # Save to file
        save_path = tmp_path / "test_typography.json"
        result = typography_manager.save_typography_to_file(save_path)
        assert result is True
        assert save_path.exists()
        
        # Create new manager and load
        new_manager = TypographyManager()
        result = new_manager.load_typography_from_file(save_path)
        assert result is True
        assert "custom" in new_manager._typography_definitions


@pytest.mark.integration
class TestTypographyIntegration:
    """Integration tests for typography system."""
    
    def test_complete_typography_workflow(self, qapp):
        """Test complete typography workflow."""
        manager = TypographyManager()
        
        # Create custom scale
        scale = manager.create_typography_scale("integration_test", 15, 1.2)
        manager.set_typography_scale("integration_test")
        
        # Create custom font definition
        definition = FontDefinition(
            family="Arial",
            size=15,
            weight=FontWeight.MEDIUM.value,
            line_height=1.6
        )
        manager.register_font_definition("integration_font", definition)
        
        # Get font and verify
        font = manager.get_font("integration_font")
        assert font.pointSize() == 15
        assert font.weight().value == FontWeight.MEDIUM.value
        
        # Test with scale
        scale_font = manager.get_font_from_scale("integration_test", "lg")
        assert scale_font is not None
        assert scale_font.pointSize() > 15
        
        # Generate complete style set
        styles = manager.generate_text_styles("integration_font")
        assert len(styles) > 5
        
        # Test global scaling
        manager.set_global_scale_factor(1.5)
        scaled_font = manager.get_font("integration_font")
        expected_size = int(15 * 1.5)
        assert scaled_font.pointSize() == expected_size
    
    def test_font_fallback_integration(self, qapp):
        """Test font fallback system integration."""
        manager = TypographyManager()
        
        # Create definition with non-existent primary font
        definition = FontDefinition(
            family="NonExistentFont12345",
            size=14,
            fallbacks=["Arial", "DejaVu Sans", "sans-serif"]
        )
        manager.register_font_definition("fallback_test", definition)
        
        # Should still create valid font
        font = manager.get_font("fallback_test")
        assert isinstance(font, QFont)
        assert font.pointSize() == 14
        
        # Font family should be one of the fallbacks
        font_family = font.family()
        assert font_family != "NonExistentFont12345"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])