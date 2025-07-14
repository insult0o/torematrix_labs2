"""Tests for color palette management system."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch

from src.torematrix.ui.themes.palettes import (
    PaletteManager, ColorUtilities, ColorHarmony,
    ColorPaletteMetadata
)
from src.torematrix.ui.themes.types import ThemeType


class TestColorUtilities:
    """Test color utility functions."""
    
    def test_hex_to_rgb(self):
        """Test hex to RGB conversion."""
        assert ColorUtilities.hex_to_rgb("#FF0000") == (255, 0, 0)
        assert ColorUtilities.hex_to_rgb("#00FF00") == (0, 255, 0)
        assert ColorUtilities.hex_to_rgb("#0000FF") == (0, 0, 255)
        assert ColorUtilities.hex_to_rgb("#FFFFFF") == (255, 255, 255)
        assert ColorUtilities.hex_to_rgb("#000000") == (0, 0, 0)
        
        # Test short format
        assert ColorUtilities.hex_to_rgb("#F00") == (255, 0, 0)
        assert ColorUtilities.hex_to_rgb("0F0") == (0, 255, 0)
    
    def test_rgb_to_hex(self):
        """Test RGB to hex conversion."""
        assert ColorUtilities.rgb_to_hex((255, 0, 0)) == "#ff0000"
        assert ColorUtilities.rgb_to_hex((0, 255, 0)) == "#00ff00"
        assert ColorUtilities.rgb_to_hex((0, 0, 255)) == "#0000ff"
        assert ColorUtilities.rgb_to_hex((255, 255, 255)) == "#ffffff"
        assert ColorUtilities.rgb_to_hex((0, 0, 0)) == "#000000"
    
    def test_calculate_luminance(self):
        """Test luminance calculation."""
        # Test pure colors
        white_lum = ColorUtilities.calculate_luminance((255, 255, 255))
        black_lum = ColorUtilities.calculate_luminance((0, 0, 0))
        
        assert white_lum == pytest.approx(1.0, rel=1e-3)
        assert black_lum == pytest.approx(0.0, rel=1e-3)
        assert white_lum > black_lum
    
    def test_calculate_contrast_ratio(self):
        """Test contrast ratio calculation."""
        # White on black should have maximum contrast
        ratio = ColorUtilities.calculate_contrast_ratio("#FFFFFF", "#000000")
        assert ratio == pytest.approx(21.0, rel=1e-1)
        
        # Same colors should have minimum contrast
        ratio = ColorUtilities.calculate_contrast_ratio("#FF0000", "#FF0000")
        assert ratio == pytest.approx(1.0, rel=1e-3)
        
        # Test WCAG examples
        ratio = ColorUtilities.calculate_contrast_ratio("#757575", "#FFFFFF")
        assert ratio >= 4.5  # Should pass AA for normal text
    
    def test_adjust_lightness(self):
        """Test lightness adjustment."""
        # Make red lighter
        lighter = ColorUtilities.adjust_lightness("#FF0000", 0.2)
        assert lighter != "#FF0000"
        
        # Make red darker
        darker = ColorUtilities.adjust_lightness("#FF0000", -0.2)
        assert darker != "#FF0000"
        assert darker != lighter
        
        # Test bounds
        white = ColorUtilities.adjust_lightness("#FFFFFF", 0.5)
        assert white == "#ffffff"  # Should stay white
        
        black = ColorUtilities.adjust_lightness("#000000", -0.5)
        assert black == "#000000"  # Should stay black
    
    def test_generate_monochromatic(self):
        """Test monochromatic color generation."""
        colors = ColorUtilities.generate_monochromatic("#FF0000", 5)
        
        assert len(colors) == 5
        assert all(isinstance(color, str) for color in colors)
        assert all(color.startswith("#") for color in colors)
        
        # Colors should be different
        assert len(set(colors)) == 5
    
    def test_generate_complementary(self):
        """Test complementary color generation."""
        comp = ColorUtilities.generate_complementary("#FF0000")
        
        assert isinstance(comp, str)
        assert comp.startswith("#")
        assert comp != "#FF0000"
        
        # Complementary of complementary should be close to original
        comp_comp = ColorUtilities.generate_complementary(comp)
        # Allow some variation due to rounding
        assert comp_comp.lower() in ["#ff0000", "#fe0000", "#ff0001"]
    
    def test_generate_triadic(self):
        """Test triadic color generation."""
        colors = ColorUtilities.generate_triadic("#FF0000")
        
        assert len(colors) == 3
        assert colors[0] == "#FF0000"  # First should be original
        assert all(isinstance(color, str) for color in colors)
        assert len(set(colors)) == 3  # All should be different
    
    def test_ensure_accessibility(self):
        """Test accessibility color adjustment."""
        # Test improving contrast
        improved = ColorUtilities.ensure_accessibility("#777777", "#FFFFFF", "AA", "normal")
        
        # Should improve contrast
        original_ratio = ColorUtilities.calculate_contrast_ratio("#777777", "#FFFFFF")
        improved_ratio = ColorUtilities.calculate_contrast_ratio(improved, "#FFFFFF")
        
        assert improved_ratio >= 4.5  # Should meet AA standard
        assert improved_ratio >= original_ratio


class TestPaletteManager:
    """Test palette manager functionality."""
    
    @pytest.fixture
    def palette_manager(self):
        """Create palette manager for testing."""
        return PaletteManager()
    
    def test_initialization(self, palette_manager):
        """Test palette manager initialization."""
        assert palette_manager is not None
        assert len(palette_manager._palettes) >= 3  # Built-in palettes
        assert "professional_dark" in palette_manager._palettes
        assert "professional_light" in palette_manager._palettes
        assert "high_contrast" in palette_manager._palettes
    
    def test_create_palette(self, palette_manager):
        """Test palette creation."""
        metadata = ColorPaletteMetadata(
            name="Test Palette",
            description="Test palette for unit tests",
            category=ThemeType.CUSTOM
        )
        
        base_colors = {
            'primary': '#FF0000',
            'background': '#FFFFFF'
        }
        
        palette = palette_manager.create_palette("test_palette", base_colors, metadata)
        
        assert palette['name'] == "Test Palette"
        assert 'colors' in palette
        assert 'derived' in palette
        assert 'accessibility' in palette
        assert 'metadata' in palette
        
        # Check derived colors were generated
        derived = palette['derived']
        assert 'background_primary' in derived
        assert 'text_primary' in derived
        assert 'accent_primary' in derived
    
    def test_generate_palette_variations(self, palette_manager):
        """Test palette variation generation."""
        base_palette = palette_manager.get_palette("professional_light")
        assert base_palette is not None
        
        variations = palette_manager.generate_palette_variations(base_palette)
        
        assert len(variations) > 0
        assert all('name' in var for var in variations)
        assert all('colors' in var for var in variations)
        
        # Check that variations are different from base
        for variation in variations:
            assert variation['name'] != base_palette['name']
    
    def test_get_contrasting_color(self, palette_manager):
        """Test contrasting color generation."""
        # Test light background
        contrasting = palette_manager.get_contrasting_color("#777777", "#FFFFFF", "AA")
        ratio = ColorUtilities.calculate_contrast_ratio(contrasting, "#FFFFFF")
        assert ratio >= 4.5
        
        # Test dark background
        contrasting = palette_manager.get_contrasting_color("#777777", "#000000", "AA")
        ratio = ColorUtilities.calculate_contrast_ratio(contrasting, "#000000")
        assert ratio >= 4.5
    
    def test_save_and_load_palette(self, palette_manager, tmp_path):
        """Test palette persistence."""
        # Create test palette
        metadata = ColorPaletteMetadata(name="Test Save", category=ThemeType.CUSTOM)
        base_colors = {'primary': '#FF0000', 'background': '#FFFFFF'}
        palette = palette_manager.create_palette("test_save", base_colors, metadata)
        
        # Save palette
        save_path = tmp_path / "test_palette.json"
        palette_manager.save_palette(palette, save_path)
        
        assert save_path.exists()
        
        # Clear manager and reload
        palette_manager._palettes.clear()
        loaded_palette = palette_manager.load_palette(save_path)
        
        assert loaded_palette['name'] == "Test Save"
        assert 'test_save' in palette_manager._palettes
    
    def test_builtin_palettes_accessibility(self, palette_manager):
        """Test that built-in palettes meet accessibility standards."""
        for palette_name in ["professional_dark", "professional_light", "high_contrast"]:
            palette = palette_manager.get_palette(palette_name)
            assert palette is not None
            
            accessibility = palette.get('accessibility', {})
            
            # Check critical combinations
            for test_name, result in accessibility.items():
                if isinstance(result, dict) and 'aa_pass' in result:
                    assert result['aa_pass'], f"{palette_name} failed accessibility: {test_name}"


class TestColorPaletteMetadata:
    """Test color palette metadata."""
    
    def test_metadata_creation(self):
        """Test metadata object creation."""
        metadata = ColorPaletteMetadata(
            name="Test Metadata",
            description="Test description",
            category=ThemeType.DARK,
            accessibility_level="AAA",
            harmony_type=ColorHarmony.COMPLEMENTARY
        )
        
        assert metadata.name == "Test Metadata"
        assert metadata.category == ThemeType.DARK
        assert metadata.accessibility_level == "AAA"
        assert metadata.harmony_type == ColorHarmony.COMPLEMENTARY
    
    def test_metadata_defaults(self):
        """Test metadata default values."""
        metadata = ColorPaletteMetadata(name="Test")
        
        assert metadata.name == "Test"
        assert metadata.description == ""
        assert metadata.author == ""
        assert metadata.version == "1.0.0"
        assert metadata.category == ThemeType.CUSTOM
        assert metadata.accessibility_level == "AA"


@pytest.mark.integration
class TestPaletteIntegration:
    """Integration tests for palette system."""
    
    def test_full_palette_workflow(self, tmp_path):
        """Test complete palette creation and validation workflow."""
        manager = PaletteManager()
        
        # Create custom palette
        metadata = ColorPaletteMetadata(
            name="Integration Test",
            description="Full workflow test",
            category=ThemeType.LIGHT,
            accessibility_level="AA"
        )
        
        base_colors = {
            'primary': '#2196F3',
            'background': '#FFFFFF'
        }
        
        # Create palette
        palette = manager.create_palette("integration_test", base_colors, metadata)
        
        # Verify structure
        assert 'colors' in palette
        assert 'derived' in palette
        assert 'accessibility' in palette
        
        # Generate variations
        variations = manager.generate_palette_variations(palette)
        assert len(variations) > 0
        
        # Save and reload
        save_path = tmp_path / "integration_test.json"
        manager.save_palette(palette, save_path)
        
        new_manager = PaletteManager()
        loaded_palette = new_manager.load_palette(save_path)
        
        assert loaded_palette['name'] == palette['name']
        assert loaded_palette['colors'] == palette['colors']
    
    def test_accessibility_validation_integration(self):
        """Test accessibility validation with real palette data."""
        manager = PaletteManager()
        
        # Test high contrast palette
        hc_palette = manager.get_palette("high_contrast")
        assert hc_palette is not None
        
        accessibility = hc_palette.get('accessibility', {})
        
        # High contrast should pass all tests
        for test_name, result in accessibility.items():
            if isinstance(result, dict) and 'aaa_pass' in result:
                assert result['aaa_pass'], f"High contrast failed: {test_name}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])