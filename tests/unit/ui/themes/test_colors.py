"""Tests for color utilities and analysis."""

import pytest
from unittest.mock import patch

from src.torematrix.ui.themes.colors import (
    ColorAnalyzer, ColorManipulator, ColorSchemeGenerator,
    ColorAnalysis, ContrastAnalysis, ColorBlindnessType
)


class TestColorAnalyzer:
    """Test color analyzer functionality."""
    
    def test_hex_to_rgb(self):
        """Test hex to RGB conversion."""
        assert ColorAnalyzer.hex_to_rgb("#FF0000") == (255, 0, 0)
        assert ColorAnalyzer.hex_to_rgb("#00FF00") == (0, 255, 0)
        assert ColorAnalyzer.hex_to_rgb("#0000FF") == (0, 0, 255)
        assert ColorAnalyzer.hex_to_rgb("#FFFFFF") == (255, 255, 255)
        assert ColorAnalyzer.hex_to_rgb("#000000") == (0, 0, 0)
        
        # Test 3-digit hex
        assert ColorAnalyzer.hex_to_rgb("#F00") == (255, 0, 0)
        assert ColorAnalyzer.hex_to_rgb("0F0") == (0, 255, 0)
    
    def test_rgb_to_hex(self):
        """Test RGB to hex conversion."""
        assert ColorAnalyzer.rgb_to_hex((255, 0, 0)) == "#ff0000"
        assert ColorAnalyzer.rgb_to_hex((0, 255, 0)) == "#00ff00"
        assert ColorAnalyzer.rgb_to_hex((0, 0, 255)) == "#0000ff"
        assert ColorAnalyzer.rgb_to_hex((255, 255, 255)) == "#ffffff"
        assert ColorAnalyzer.rgb_to_hex((0, 0, 0)) == "#000000"
    
    def test_color_space_conversions(self):
        """Test HSV and HSL conversions."""
        rgb = (255, 128, 0)  # Orange
        
        # Test RGB to HSV
        hsv = ColorAnalyzer.rgb_to_hsv(rgb)
        assert len(hsv) == 3
        assert 0 <= hsv[0] <= 1  # Hue
        assert 0 <= hsv[1] <= 1  # Saturation
        assert 0 <= hsv[2] <= 1  # Value
        
        # Test HSV back to RGB
        rgb_back = ColorAnalyzer.hsv_to_rgb(hsv)
        assert rgb_back == rgb
        
        # Test RGB to HSL
        hsl = ColorAnalyzer.rgb_to_hsl(rgb)
        assert len(hsl) == 3
        assert 0 <= hsl[0] <= 1  # Hue
        assert 0 <= hsl[1] <= 1  # Lightness
        assert 0 <= hsl[2] <= 1  # Saturation
        
        # Test HSL back to RGB
        rgb_back = ColorAnalyzer.hsl_to_rgb(hsl)
        assert rgb_back == rgb
    
    def test_calculate_luminance(self):
        """Test luminance calculation."""
        # Pure white should have luminance of 1
        white_lum = ColorAnalyzer.calculate_luminance((255, 255, 255))
        assert white_lum == pytest.approx(1.0, rel=1e-3)
        
        # Pure black should have luminance of 0
        black_lum = ColorAnalyzer.calculate_luminance((0, 0, 0))
        assert black_lum == pytest.approx(0.0, rel=1e-3)
        
        # Gray should be in between
        gray_lum = ColorAnalyzer.calculate_luminance((128, 128, 128))
        assert 0 < gray_lum < 1
    
    def test_calculate_perceived_brightness(self):
        """Test perceived brightness calculation."""
        # White should be brightest
        white_brightness = ColorAnalyzer.calculate_perceived_brightness((255, 255, 255))
        assert white_brightness == 1.0
        
        # Black should be darkest
        black_brightness = ColorAnalyzer.calculate_perceived_brightness((0, 0, 0))
        assert black_brightness == 0.0
        
        # Red should be less bright than white
        red_brightness = ColorAnalyzer.calculate_perceived_brightness((255, 0, 0))
        assert 0 < red_brightness < 1
    
    def test_calculate_contrast_ratio(self):
        """Test contrast ratio calculation."""
        # Maximum contrast: white on black
        max_ratio = ColorAnalyzer.calculate_contrast_ratio("#FFFFFF", "#000000")
        assert max_ratio == pytest.approx(21.0, rel=1e-1)
        
        # Minimum contrast: same colors
        min_ratio = ColorAnalyzer.calculate_contrast_ratio("#FF0000", "#FF0000")
        assert min_ratio == pytest.approx(1.0, rel=1e-3)
        
        # Test order independence
        ratio1 = ColorAnalyzer.calculate_contrast_ratio("#FFFFFF", "#000000")
        ratio2 = ColorAnalyzer.calculate_contrast_ratio("#000000", "#FFFFFF")
        assert ratio1 == ratio2
    
    def test_determine_color_temperature(self):
        """Test color temperature determination."""
        # Red should be warm
        red_hsv = ColorAnalyzer.rgb_to_hsv((255, 0, 0))
        assert ColorAnalyzer.determine_color_temperature(red_hsv) == "warm"
        
        # Blue should be cool
        blue_hsv = ColorAnalyzer.rgb_to_hsv((0, 0, 255))
        assert ColorAnalyzer.determine_color_temperature(blue_hsv) == "cool"
        
        # Green should be cool
        green_hsv = ColorAnalyzer.rgb_to_hsv((0, 255, 0))
        assert ColorAnalyzer.determine_color_temperature(green_hsv) == "cool"
    
    def test_analyze_color(self):
        """Test comprehensive color analysis."""
        analysis = ColorAnalyzer.analyze_color("#FF0000")
        
        assert isinstance(analysis, ColorAnalysis)
        assert analysis.hex_value == "#FF0000"
        assert analysis.rgb == (255, 0, 0)
        assert len(analysis.hsv) == 3
        assert len(analysis.hsl) == 3
        assert isinstance(analysis.luminance, float)
        assert isinstance(analysis.is_light, bool)
        assert isinstance(analysis.is_dark, bool)
        assert isinstance(analysis.perceived_brightness, float)
        assert analysis.temperature in ["warm", "cool", "neutral"]
    
    def test_analyze_contrast(self):
        """Test contrast analysis."""
        # Test high contrast
        high_contrast = ColorAnalyzer.analyze_contrast("#FFFFFF", "#000000")
        
        assert isinstance(high_contrast, ContrastAnalysis)
        assert high_contrast.ratio > 15
        assert high_contrast.aa_normal is True
        assert high_contrast.aaa_normal is True
        assert high_contrast.level == "AAA"
        
        # Test low contrast
        low_contrast = ColorAnalyzer.analyze_contrast("#AAAAAA", "#BBBBBB")
        
        assert low_contrast.ratio < 3.0
        assert low_contrast.aa_normal is False
        assert low_contrast.level == "Fail"


class TestColorManipulator:
    """Test color manipulation functions."""
    
    def test_adjust_lightness(self):
        """Test lightness adjustment."""
        original = "#FF0000"  # Red
        
        # Make lighter
        lighter = ColorManipulator.adjust_lightness(original, 0.2)
        assert lighter != original
        
        # Make darker
        darker = ColorManipulator.adjust_lightness(original, -0.2)
        assert darker != original
        assert darker != lighter
        
        # Test bounds - white should stay white
        white_result = ColorManipulator.adjust_lightness("#FFFFFF", 0.5)
        white_analysis = ColorAnalyzer.analyze_color(white_result)
        assert white_analysis.luminance > 0.9  # Should stay very light
        
        # Black should stay black
        black_result = ColorManipulator.adjust_lightness("#000000", -0.5)
        black_analysis = ColorAnalyzer.analyze_color(black_result)
        assert black_analysis.luminance < 0.1  # Should stay very dark
    
    def test_adjust_saturation(self):
        """Test saturation adjustment."""
        original = "#FF0000"  # Pure red
        
        # Reduce saturation (more gray)
        desaturated = ColorManipulator.adjust_saturation(original, -0.3)
        assert desaturated != original
        
        # Increase saturation (more vivid)
        saturated = ColorManipulator.adjust_saturation(original, 0.3)
        assert saturated != original
        
        # Pure red should stay pure when increasing saturation
        pure_red_saturated = ColorManipulator.adjust_saturation("#FF0000", 0.5)
        # Should be close to original since it's already fully saturated
        assert pure_red_saturated.lower() in ["#ff0000", "#fe0000", "#ff0001"]
    
    def test_adjust_hue(self):
        """Test hue adjustment."""
        original = "#FF0000"  # Red
        
        # Shift hue
        shifted = ColorManipulator.adjust_hue(original, 120)  # Should go towards green
        assert shifted != original
        
        # 360 degree shift should return to approximately original
        full_circle = ColorManipulator.adjust_hue(original, 360)
        # Allow some rounding error
        assert full_circle.lower() in ["#ff0000", "#fe0000", "#ff0001"]
    
    def test_blend_colors(self):
        """Test color blending."""
        red = "#FF0000"
        blue = "#0000FF"
        
        # 50% blend
        blend_50 = ColorManipulator.blend_colors(red, blue, 0.5)
        assert blend_50 != red
        assert blend_50 != blue
        
        # 0% blend should be first color
        blend_0 = ColorManipulator.blend_colors(red, blue, 0.0)
        assert blend_0 == red
        
        # 100% blend should be second color
        blend_100 = ColorManipulator.blend_colors(red, blue, 1.0)
        assert blend_100 == blue
    
    def test_create_tint_shade_tone(self):
        """Test tint, shade, and tone creation."""
        original = "#FF0000"  # Red
        
        # Tint (mix with white)
        tint = ColorManipulator.create_tint(original, 0.5)
        tint_analysis = ColorAnalyzer.analyze_color(tint)
        original_analysis = ColorAnalyzer.analyze_color(original)
        assert tint_analysis.luminance > original_analysis.luminance
        
        # Shade (mix with black)
        shade = ColorManipulator.create_shade(original, 0.5)
        shade_analysis = ColorAnalyzer.analyze_color(shade)
        assert shade_analysis.luminance < original_analysis.luminance
        
        # Tone (mix with gray)
        tone = ColorManipulator.create_tone(original, 0.5)
        assert tone != original
        assert tone != tint
        assert tone != shade
    
    def test_simulate_color_blindness(self):
        """Test color blindness simulation."""
        red = "#FF0000"
        green = "#00FF00"
        
        # Test different types of color blindness
        for blindness_type in ColorBlindnessType:
            red_sim = ColorManipulator.simulate_color_blindness(red, blindness_type)
            green_sim = ColorManipulator.simulate_color_blindness(green, blindness_type)
            
            assert isinstance(red_sim, str)
            assert isinstance(green_sim, str)
            assert red_sim.startswith("#")
            assert green_sim.startswith("#")
            
            # For red-green color blindness, red and green should become more similar
            if blindness_type in [ColorBlindnessType.PROTANOPIA, ColorBlindnessType.DEUTERANOPIA]:
                # The simulated colors should be different from originals
                assert red_sim != red or green_sim != green


class TestColorSchemeGenerator:
    """Test color scheme generation."""
    
    def test_generate_monochromatic(self):
        """Test monochromatic scheme generation."""
        colors = ColorSchemeGenerator.generate_monochromatic("#FF0000", 5)
        
        assert len(colors) == 5
        assert all(isinstance(color, str) for color in colors)
        assert all(color.startswith("#") for color in colors)
        
        # Colors should be different
        assert len(set(colors)) == 5
        
        # All colors should be variations of red (same hue)
        for color in colors:
            rgb = ColorAnalyzer.hex_to_rgb(color)
            hsv = ColorAnalyzer.rgb_to_hsv(rgb)
            # Hue should be similar (allowing for some variation)
            # Red is around hue 0, but can wrap to 1
            assert hsv[0] < 0.1 or hsv[0] > 0.9
    
    def test_generate_analogous(self):
        """Test analogous scheme generation."""
        colors = ColorSchemeGenerator.generate_analogous("#FF0000", 30.0, 3)
        
        assert len(colors) == 3
        assert colors[0] == "#FF0000"  # First should be original
        assert all(isinstance(color, str) for color in colors)
        
        # Colors should be different
        assert len(set(colors)) == 3
    
    def test_generate_complementary(self):
        """Test complementary scheme generation."""
        colors = ColorSchemeGenerator.generate_complementary("#FF0000")
        
        assert len(colors) == 2
        assert colors[0] == "#FF0000"  # First should be original
        assert isinstance(colors[1], str)
        assert colors[1] != colors[0]
        
        # Complementary should be approximately cyan/teal
        comp_rgb = ColorAnalyzer.hex_to_rgb(colors[1])
        comp_hsv = ColorAnalyzer.rgb_to_hsv(comp_rgb)
        # Should be around 180 degrees from red (0.5 in normalized hue)
        assert 0.4 < comp_hsv[0] < 0.6
    
    def test_generate_triadic(self):
        """Test triadic scheme generation."""
        colors = ColorSchemeGenerator.generate_triadic("#FF0000")
        
        assert len(colors) == 3
        assert colors[0] == "#FF0000"  # First should be original
        assert all(isinstance(color, str) for color in colors)
        
        # Colors should be different
        assert len(set(colors)) == 3
        
        # Test hue differences (approximately 120 degrees apart)
        base_hsv = ColorAnalyzer.rgb_to_hsv(ColorAnalyzer.hex_to_rgb(colors[0]))
        for i, color in enumerate(colors[1:], 1):
            rgb = ColorAnalyzer.hex_to_rgb(color)
            hsv = ColorAnalyzer.rgb_to_hsv(rgb)
            
            # Calculate expected hue
            expected_hue = (base_hsv[0] + i / 3) % 1.0
            # Allow some tolerance for rounding
            assert abs(hsv[0] - expected_hue) < 0.05 or abs(hsv[0] - expected_hue) > 0.95
    
    def test_generate_tetradic(self):
        """Test tetradic scheme generation."""
        colors = ColorSchemeGenerator.generate_tetradic("#FF0000")
        
        assert len(colors) == 4
        assert colors[0] == "#FF0000"  # First should be original
        assert all(isinstance(color, str) for color in colors)
        
        # Colors should be different
        assert len(set(colors)) == 4
    
    def test_generate_split_complementary(self):
        """Test split complementary scheme generation."""
        colors = ColorSchemeGenerator.generate_split_complementary("#FF0000", 30.0)
        
        assert len(colors) == 3
        assert colors[0] == "#FF0000"  # First should be original
        assert all(isinstance(color, str) for color in colors)
        
        # Colors should be different
        assert len(set(colors)) == 3


@pytest.mark.integration
class TestColorIntegration:
    """Integration tests for color system."""
    
    def test_color_analysis_workflow(self):
        """Test complete color analysis workflow."""
        # Start with a base color
        base_color = "#2196F3"  # Material Blue
        
        # Analyze the color
        analysis = ColorAnalyzer.analyze_color(base_color)
        assert analysis.hex_value == base_color
        
        # Create variations
        lighter = ColorManipulator.adjust_lightness(base_color, 0.2)
        darker = ColorManipulator.adjust_lightness(base_color, -0.2)
        
        # Analyze variations
        lighter_analysis = ColorAnalyzer.analyze_color(lighter)
        darker_analysis = ColorAnalyzer.analyze_color(darker)
        
        # Verify relationships
        assert lighter_analysis.luminance > analysis.luminance
        assert darker_analysis.luminance < analysis.luminance
        
        # Test contrast with backgrounds
        white_contrast = ColorAnalyzer.analyze_contrast(base_color, "#FFFFFF")
        black_contrast = ColorAnalyzer.analyze_contrast(base_color, "#000000")
        
        # One should be better than the other
        assert white_contrast.ratio != black_contrast.ratio
    
    def test_accessibility_improvement_workflow(self):
        """Test color accessibility improvement workflow."""
        # Start with a low contrast combination
        foreground = "#888888"
        background = "#AAAAAA"
        
        # Check initial contrast
        initial_contrast = ColorAnalyzer.analyze_contrast(foreground, background)
        assert initial_contrast.aa_normal is False  # Should fail initially
        
        # Improve the foreground color
        bg_analysis = ColorAnalyzer.analyze_color(background)
        
        if bg_analysis.is_light:
            # Light background - make foreground darker
            improved_fg = ColorManipulator.adjust_lightness(foreground, -0.3)
        else:
            # Dark background - make foreground lighter
            improved_fg = ColorManipulator.adjust_lightness(foreground, 0.3)
        
        # Check improved contrast
        improved_contrast = ColorAnalyzer.analyze_contrast(improved_fg, background)
        assert improved_contrast.ratio > initial_contrast.ratio
    
    def test_color_scheme_generation_workflow(self):
        """Test complete color scheme generation workflow."""
        base_color = "#E91E63"  # Material Pink
        
        # Generate different schemes
        monochromatic = ColorSchemeGenerator.generate_monochromatic(base_color, 5)
        analogous = ColorSchemeGenerator.generate_analogous(base_color)
        complementary = ColorSchemeGenerator.generate_complementary(base_color)
        triadic = ColorSchemeGenerator.generate_triadic(base_color)
        
        # Verify all schemes contain the base color
        assert base_color in monochromatic
        assert analogous[0] == base_color
        assert complementary[0] == base_color
        assert triadic[0] == base_color
        
        # Test color blindness simulation on the schemes
        for scheme in [monochromatic, analogous, complementary, triadic]:
            for color in scheme:
                for blindness_type in [ColorBlindnessType.PROTANOPIA, ColorBlindnessType.DEUTERANOPIA]:
                    simulated = ColorManipulator.simulate_color_blindness(color, blindness_type)
                    assert isinstance(simulated, str)
                    assert simulated.startswith("#")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])