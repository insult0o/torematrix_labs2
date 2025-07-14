"""Advanced color utilities and manipulation algorithms."""

import logging
import colorsys
import math
from typing import Dict, List, Tuple, Optional, Union, Any
from enum import Enum
from dataclasses import dataclass

from PyQt6.QtGui import QColor

logger = logging.getLogger(__name__)


class ColorSpace(Enum):
    """Color space types for conversions."""
    RGB = "rgb"
    HSV = "hsv"
    HSL = "hsl" 
    LAB = "lab"
    LCH = "lch"


class ColorBlindnessType(Enum):
    """Types of color blindness for simulation."""
    PROTANOPIA = "protanopia"      # Red-blind
    DEUTERANOPIA = "deuteranopia"  # Green-blind
    TRITANOPIA = "tritanopia"      # Blue-blind
    PROTANOMALY = "protanomaly"    # Red-weak
    DEUTERANOMALY = "deuteranomaly" # Green-weak
    TRITANOMALY = "tritanomaly"    # Blue-weak


@dataclass
class ColorAnalysis:
    """Comprehensive color analysis results."""
    hex_value: str
    rgb: Tuple[int, int, int]
    hsv: Tuple[float, float, float]
    hsl: Tuple[float, float, float]
    luminance: float
    is_light: bool
    is_dark: bool
    perceived_brightness: float
    temperature: str  # "warm", "cool", "neutral"


@dataclass
class ContrastAnalysis:
    """Color contrast analysis results."""
    ratio: float
    aa_normal: bool
    aa_large: bool
    aaa_normal: bool
    aaa_large: bool
    level: str
    recommendation: str


class ColorAnalyzer:
    """Advanced color analysis and utilities."""
    
    @staticmethod
    def analyze_color(color: str) -> ColorAnalysis:
        """Perform comprehensive color analysis.
        
        Args:
            color: Hex color string
            
        Returns:
            ColorAnalysis with detailed information
        """
        # Convert to RGB
        rgb = ColorAnalyzer.hex_to_rgb(color)
        
        # Convert to other color spaces
        hsv = ColorAnalyzer.rgb_to_hsv(rgb)
        hsl = ColorAnalyzer.rgb_to_hsl(rgb)
        
        # Calculate luminance
        luminance = ColorAnalyzer.calculate_luminance(rgb)
        
        # Determine brightness characteristics
        is_light = luminance > 0.5
        is_dark = luminance < 0.179
        
        # Calculate perceived brightness (using different formula)
        perceived_brightness = ColorAnalyzer.calculate_perceived_brightness(rgb)
        
        # Determine temperature
        temperature = ColorAnalyzer.determine_color_temperature(hsv)
        
        return ColorAnalysis(
            hex_value=color,
            rgb=rgb,
            hsv=hsv,
            hsl=hsl,
            luminance=luminance,
            is_light=is_light,
            is_dark=is_dark,
            perceived_brightness=perceived_brightness,
            temperature=temperature
        )
    
    @staticmethod
    def analyze_contrast(foreground: str, background: str) -> ContrastAnalysis:
        """Analyze contrast between two colors.
        
        Args:
            foreground: Foreground color hex
            background: Background color hex
            
        Returns:
            ContrastAnalysis with WCAG compliance information
        """
        ratio = ColorAnalyzer.calculate_contrast_ratio(foreground, background)
        
        # WCAG compliance levels
        aa_normal = ratio >= 4.5
        aa_large = ratio >= 3.0
        aaa_normal = ratio >= 7.0
        aaa_large = ratio >= 4.5
        
        # Determine overall level
        if aaa_normal:
            level = "AAA"
        elif aa_normal:
            level = "AA"
        elif aa_large:
            level = "AA Large"
        else:
            level = "Fail"
        
        # Generate recommendation
        if ratio < 3.0:
            recommendation = "Poor contrast. Increase contrast significantly."
        elif ratio < 4.5:
            recommendation = "Acceptable for large text only. Improve for normal text."
        elif ratio < 7.0:
            recommendation = "Good contrast. Meets AA standards."
        else:
            recommendation = "Excellent contrast. Meets AAA standards."
        
        return ContrastAnalysis(
            ratio=ratio,
            aa_normal=aa_normal,
            aa_large=aa_large,
            aaa_normal=aaa_normal,
            aaa_large=aaa_large,
            level=level,
            recommendation=recommendation
        )
    
    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @staticmethod
    def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex color."""
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    @staticmethod
    def rgb_to_hsv(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
        """Convert RGB to HSV."""
        r, g, b = [x / 255.0 for x in rgb]
        return colorsys.rgb_to_hsv(r, g, b)
    
    @staticmethod
    def hsv_to_rgb(hsv: Tuple[float, float, float]) -> Tuple[int, int, int]:
        """Convert HSV to RGB."""
        r, g, b = colorsys.hsv_to_rgb(*hsv)
        return (int(r * 255), int(g * 255), int(b * 255))
    
    @staticmethod
    def rgb_to_hsl(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
        """Convert RGB to HSL."""
        r, g, b = [x / 255.0 for x in rgb]
        return colorsys.rgb_to_hls(r, g, b)
    
    @staticmethod
    def hsl_to_rgb(hsl: Tuple[float, float, float]) -> Tuple[int, int, int]:
        """Convert HSL to RGB."""
        h, l, s = hsl
        r, g, b = colorsys.hls_to_rgb(h, l, s)
        return (int(r * 255), int(g * 255), int(b * 255))
    
    @staticmethod
    def calculate_luminance(rgb: Tuple[int, int, int]) -> float:
        """Calculate relative luminance for contrast calculations."""
        r, g, b = [x / 255.0 for x in rgb]
        
        def gamma_correct(c):
            return c / 12.92 if c <= 0.03928 else pow((c + 0.055) / 1.055, 2.4)
        
        r = gamma_correct(r)
        g = gamma_correct(g)
        b = gamma_correct(b)
        
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    
    @staticmethod
    def calculate_perceived_brightness(rgb: Tuple[int, int, int]) -> float:
        """Calculate perceived brightness using ITU-R BT.709 formula."""
        r, g, b = rgb
        return (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    
    @staticmethod
    def calculate_contrast_ratio(color1: str, color2: str) -> float:
        """Calculate WCAG contrast ratio between two colors."""
        rgb1 = ColorAnalyzer.hex_to_rgb(color1)
        rgb2 = ColorAnalyzer.hex_to_rgb(color2)
        
        lum1 = ColorAnalyzer.calculate_luminance(rgb1)
        lum2 = ColorAnalyzer.calculate_luminance(rgb2)
        
        # Ensure lighter color is in numerator
        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)
        
        return (lighter + 0.05) / (darker + 0.05)
    
    @staticmethod
    def determine_color_temperature(hsv: Tuple[float, float, float]) -> str:
        """Determine if color is warm, cool, or neutral."""
        hue = hsv[0] * 360  # Convert to degrees
        
        # Define temperature ranges
        if (hue >= 0 and hue <= 60) or (hue >= 300 and hue <= 360):
            return "warm"  # Reds, oranges, yellows
        elif hue >= 120 and hue <= 240:
            return "cool"   # Greens, blues, purples
        else:
            return "neutral"  # In between ranges


class ColorManipulator:
    """Advanced color manipulation operations."""
    
    @staticmethod
    def adjust_lightness(color: str, amount: float) -> str:
        """Adjust lightness of a color.
        
        Args:
            color: Hex color string
            amount: Adjustment amount (-1.0 to 1.0)
            
        Returns:
            Adjusted hex color
        """
        rgb = ColorAnalyzer.hex_to_rgb(color)
        h, l, s = ColorAnalyzer.rgb_to_hsl(rgb)
        
        # Adjust lightness
        l = max(0.0, min(1.0, l + amount))
        
        new_rgb = ColorAnalyzer.hsl_to_rgb((h, l, s))
        return ColorAnalyzer.rgb_to_hex(new_rgb)
    
    @staticmethod
    def adjust_saturation(color: str, amount: float) -> str:
        """Adjust saturation of a color.
        
        Args:
            color: Hex color string
            amount: Adjustment amount (-1.0 to 1.0)
            
        Returns:
            Adjusted hex color
        """
        rgb = ColorAnalyzer.hex_to_rgb(color)
        h, s, v = ColorAnalyzer.rgb_to_hsv(rgb)
        
        # Adjust saturation
        s = max(0.0, min(1.0, s + amount))
        
        new_rgb = ColorAnalyzer.hsv_to_rgb((h, s, v))
        return ColorAnalyzer.rgb_to_hex(new_rgb)
    
    @staticmethod
    def adjust_hue(color: str, degrees: float) -> str:
        """Adjust hue of a color.
        
        Args:
            color: Hex color string
            degrees: Hue shift in degrees (-360 to 360)
            
        Returns:
            Adjusted hex color
        """
        rgb = ColorAnalyzer.hex_to_rgb(color)
        h, s, v = ColorAnalyzer.rgb_to_hsv(rgb)
        
        # Adjust hue (normalize to 0-1 range)
        h = (h + degrees / 360.0) % 1.0
        
        new_rgb = ColorAnalyzer.hsv_to_rgb((h, s, v))
        return ColorAnalyzer.rgb_to_hex(new_rgb)
    
    @staticmethod
    def blend_colors(color1: str, color2: str, ratio: float = 0.5) -> str:
        """Blend two colors together.
        
        Args:
            color1: First hex color
            color2: Second hex color
            ratio: Blend ratio (0.0 = all color1, 1.0 = all color2)
            
        Returns:
            Blended hex color
        """
        rgb1 = ColorAnalyzer.hex_to_rgb(color1)
        rgb2 = ColorAnalyzer.hex_to_rgb(color2)
        
        # Blend each channel
        blended_rgb = tuple(
            int(rgb1[i] * (1 - ratio) + rgb2[i] * ratio)
            for i in range(3)
        )
        
        return ColorAnalyzer.rgb_to_hex(blended_rgb)
    
    @staticmethod
    def create_tint(color: str, percentage: float) -> str:
        """Create a tint by mixing with white.
        
        Args:
            color: Base hex color
            percentage: Tint percentage (0.0 to 1.0)
            
        Returns:
            Tinted hex color
        """
        return ColorManipulator.blend_colors(color, "#FFFFFF", percentage)
    
    @staticmethod
    def create_shade(color: str, percentage: float) -> str:
        """Create a shade by mixing with black.
        
        Args:
            color: Base hex color
            percentage: Shade percentage (0.0 to 1.0)
            
        Returns:
            Shaded hex color
        """
        return ColorManipulator.blend_colors(color, "#000000", percentage)
    
    @staticmethod
    def create_tone(color: str, percentage: float) -> str:
        """Create a tone by mixing with gray.
        
        Args:
            color: Base hex color
            percentage: Tone percentage (0.0 to 1.0)
            
        Returns:
            Toned hex color
        """
        return ColorManipulator.blend_colors(color, "#808080", percentage)
    
    @staticmethod
    def simulate_color_blindness(color: str, blindness_type: ColorBlindnessType) -> str:
        """Simulate how a color appears with color blindness.
        
        Args:
            color: Hex color to simulate
            blindness_type: Type of color blindness
            
        Returns:
            Simulated hex color
        """
        rgb = ColorAnalyzer.hex_to_rgb(color)
        r, g, b = [x / 255.0 for x in rgb]
        
        # Transformation matrices for different types of color blindness
        # These are simplified approximations
        if blindness_type == ColorBlindnessType.PROTANOPIA:
            # Red-blind
            new_r = 0.567 * r + 0.433 * g
            new_g = 0.558 * r + 0.442 * g
            new_b = 0.242 * g + 0.758 * b
        elif blindness_type == ColorBlindnessType.DEUTERANOPIA:
            # Green-blind
            new_r = 0.625 * r + 0.375 * g
            new_g = 0.7 * r + 0.3 * g
            new_b = 0.3 * g + 0.7 * b
        elif blindness_type == ColorBlindnessType.TRITANOPIA:
            # Blue-blind
            new_r = 0.95 * r + 0.05 * g
            new_g = 0.433 * g + 0.567 * b
            new_b = 0.475 * g + 0.525 * b
        else:
            # For anomalous types, apply partial effect
            factor = 0.6  # Partial blindness factor
            if blindness_type == ColorBlindnessType.PROTANOMALY:
                normal_r = r
                blind_r = 0.567 * r + 0.433 * g
                new_r = normal_r * (1 - factor) + blind_r * factor
                new_g = g
                new_b = b
            elif blindness_type == ColorBlindnessType.DEUTERANOMALY:
                new_r = r
                normal_g = g
                blind_g = 0.7 * r + 0.3 * g
                new_g = normal_g * (1 - factor) + blind_g * factor
                new_b = b
            else:  # TRITANOMALY
                new_r = r
                new_g = g
                normal_b = b
                blind_b = 0.475 * g + 0.525 * b
                new_b = normal_b * (1 - factor) + blind_b * factor
        
        # Convert back to RGB values
        new_rgb = (
            int(max(0, min(255, new_r * 255))),
            int(max(0, min(255, new_g * 255))),
            int(max(0, min(255, new_b * 255)))
        )
        
        return ColorAnalyzer.rgb_to_hex(new_rgb)


class ColorSchemeGenerator:
    """Generate harmonious color schemes."""
    
    @staticmethod
    def generate_monochromatic(base_color: str, count: int = 5) -> List[str]:
        """Generate monochromatic color scheme.
        
        Args:
            base_color: Base hex color
            count: Number of colors to generate
            
        Returns:
            List of hex colors
        """
        colors = [base_color]
        rgb = ColorAnalyzer.hex_to_rgb(base_color)
        h, s, v = ColorAnalyzer.rgb_to_hsv(rgb)
        
        # Generate variations by adjusting lightness and saturation
        for i in range(1, count):
            # Create variations with different lightness
            lightness_factor = (i / (count - 1)) * 0.8 + 0.1  # 0.1 to 0.9
            new_v = lightness_factor
            
            # Slightly vary saturation too
            saturation_factor = max(0.3, s - (i * 0.1))
            new_s = min(1.0, saturation_factor)
            
            new_rgb = ColorAnalyzer.hsv_to_rgb((h, new_s, new_v))
            colors.append(ColorAnalyzer.rgb_to_hex(new_rgb))
        
        return colors
    
    @staticmethod
    def generate_analogous(base_color: str, angle: float = 30.0, count: int = 3) -> List[str]:
        """Generate analogous color scheme.
        
        Args:
            base_color: Base hex color
            angle: Angle between colors in degrees
            count: Number of colors to generate
            
        Returns:
            List of hex colors
        """
        colors = []
        rgb = ColorAnalyzer.hex_to_rgb(base_color)
        h, s, v = ColorAnalyzer.rgb_to_hsv(rgb)
        
        # Generate colors around the base hue
        for i in range(count):
            offset = (i - count // 2) * (angle / 360.0)
            new_h = (h + offset) % 1.0
            new_rgb = ColorAnalyzer.hsv_to_rgb((new_h, s, v))
            colors.append(ColorAnalyzer.rgb_to_hex(new_rgb))
        
        return colors
    
    @staticmethod
    def generate_complementary(base_color: str) -> List[str]:
        """Generate complementary color scheme.
        
        Args:
            base_color: Base hex color
            
        Returns:
            List with base color and its complement
        """
        rgb = ColorAnalyzer.hex_to_rgb(base_color)
        h, s, v = ColorAnalyzer.rgb_to_hsv(rgb)
        
        # Complementary is 180 degrees opposite
        comp_h = (h + 0.5) % 1.0
        comp_rgb = ColorAnalyzer.hsv_to_rgb((comp_h, s, v))
        
        return [base_color, ColorAnalyzer.rgb_to_hex(comp_rgb)]
    
    @staticmethod
    def generate_triadic(base_color: str) -> List[str]:
        """Generate triadic color scheme.
        
        Args:
            base_color: Base hex color
            
        Returns:
            List of three colors 120 degrees apart
        """
        colors = [base_color]
        rgb = ColorAnalyzer.hex_to_rgb(base_color)
        h, s, v = ColorAnalyzer.rgb_to_hsv(rgb)
        
        # Triadic colors are 120 degrees apart
        for offset in [1/3, 2/3]:
            new_h = (h + offset) % 1.0
            new_rgb = ColorAnalyzer.hsv_to_rgb((new_h, s, v))
            colors.append(ColorAnalyzer.rgb_to_hex(new_rgb))
        
        return colors
    
    @staticmethod
    def generate_tetradic(base_color: str) -> List[str]:
        """Generate tetradic (square) color scheme.
        
        Args:
            base_color: Base hex color
            
        Returns:
            List of four colors 90 degrees apart
        """
        colors = [base_color]
        rgb = ColorAnalyzer.hex_to_rgb(base_color)
        h, s, v = ColorAnalyzer.rgb_to_hsv(rgb)
        
        # Tetradic colors are 90 degrees apart
        for offset in [0.25, 0.5, 0.75]:
            new_h = (h + offset) % 1.0
            new_rgb = ColorAnalyzer.hsv_to_rgb((new_h, s, v))
            colors.append(ColorAnalyzer.rgb_to_hex(new_rgb))
        
        return colors
    
    @staticmethod
    def generate_split_complementary(base_color: str, angle: float = 30.0) -> List[str]:
        """Generate split complementary color scheme.
        
        Args:
            base_color: Base hex color
            angle: Split angle in degrees
            
        Returns:
            List with base color and two split complements
        """
        colors = [base_color]
        rgb = ColorAnalyzer.hex_to_rgb(base_color)
        h, s, v = ColorAnalyzer.rgb_to_hsv(rgb)
        
        # Split complementary colors
        comp_h = (h + 0.5) % 1.0
        angle_offset = angle / 360.0
        
        for offset in [-angle_offset, angle_offset]:
            new_h = (comp_h + offset) % 1.0
            new_rgb = ColorAnalyzer.hsv_to_rgb((new_h, s, v))
            colors.append(ColorAnalyzer.rgb_to_hex(new_rgb))
        
        return colors