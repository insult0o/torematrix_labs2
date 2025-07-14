"""Advanced color palette management system with dynamic generation."""

import logging
import colorsys
import json
from typing import Dict, List, Optional, Tuple, Union, Any
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from PyQt6.QtGui import QColor

from .base import ColorPalette as BaseColorPalette
from .types import ColorDefinition, ThemeType
from .exceptions import ThemeValidationError

logger = logging.getLogger(__name__)


class ColorHarmony(Enum):
    """Color harmony types for palette generation."""
    MONOCHROMATIC = "monochromatic"
    ANALOGOUS = "analogous"
    COMPLEMENTARY = "complementary"
    TRIADIC = "triadic"
    TETRADIC = "tetradic"
    SPLIT_COMPLEMENTARY = "split_complementary"


@dataclass
class ColorPaletteMetadata:
    """Metadata for color palettes."""
    name: str
    description: str = ""
    author: str = ""
    version: str = "1.0.0"
    category: ThemeType = ThemeType.CUSTOM
    accessibility_level: str = "AA"
    created_from_base: Optional[str] = None
    harmony_type: Optional[ColorHarmony] = None


class ColorUtilities:
    """Advanced color manipulation and generation utilities."""
    
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
    def calculate_contrast_ratio(color1: str, color2: str) -> float:
        """Calculate WCAG contrast ratio between two colors."""
        rgb1 = ColorUtilities.hex_to_rgb(color1)
        rgb2 = ColorUtilities.hex_to_rgb(color2)
        
        lum1 = ColorUtilities.calculate_luminance(rgb1)
        lum2 = ColorUtilities.calculate_luminance(rgb2)
        
        # Ensure lighter color is in numerator
        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)
        
        return (lighter + 0.05) / (darker + 0.05)
    
    @staticmethod
    def adjust_lightness(hex_color: str, factor: float) -> str:
        """Adjust lightness of a color by factor (-1.0 to 1.0)."""
        rgb = ColorUtilities.hex_to_rgb(hex_color)
        h, l, s = ColorUtilities.rgb_to_hsl(rgb)
        
        # Adjust lightness
        l = max(0.0, min(1.0, l + factor))
        
        new_rgb = ColorUtilities.hsl_to_rgb((h, l, s))
        return ColorUtilities.rgb_to_hex(new_rgb)
    
    @staticmethod
    def adjust_saturation(hex_color: str, factor: float) -> str:
        """Adjust saturation of a color by factor (-1.0 to 1.0)."""
        rgb = ColorUtilities.hex_to_rgb(hex_color)
        h, s, v = ColorUtilities.rgb_to_hsv(rgb)
        
        # Adjust saturation
        s = max(0.0, min(1.0, s + factor))
        
        new_rgb = ColorUtilities.hsv_to_rgb((h, s, v))
        return ColorUtilities.rgb_to_hex(new_rgb)
    
    @staticmethod
    def generate_monochromatic(base_color: str, steps: int = 10) -> List[str]:
        """Generate monochromatic color variations."""
        colors = []
        rgb = ColorUtilities.hex_to_rgb(base_color)
        h, l, s = ColorUtilities.rgb_to_hsl(rgb)
        
        for i in range(steps):
            # Vary lightness from 0.1 to 0.9
            lightness = 0.1 + (0.8 * i / (steps - 1))
            new_rgb = ColorUtilities.hsl_to_rgb((h, lightness, s))
            colors.append(ColorUtilities.rgb_to_hex(new_rgb))
        
        return colors
    
    @staticmethod
    def generate_analogous(base_color: str, angle: float = 30.0) -> List[str]:
        """Generate analogous color scheme."""
        rgb = ColorUtilities.hex_to_rgb(base_color)
        h, s, v = ColorUtilities.rgb_to_hsv(rgb)
        
        colors = [base_color]
        
        # Generate colors at +/- angle degrees
        for offset in [-angle/360, angle/360]:
            new_h = (h + offset) % 1.0
            new_rgb = ColorUtilities.hsv_to_rgb((new_h, s, v))
            colors.append(ColorUtilities.rgb_to_hex(new_rgb))
        
        return colors
    
    @staticmethod
    def generate_complementary(base_color: str) -> str:
        """Generate complementary color."""
        rgb = ColorUtilities.hex_to_rgb(base_color)
        h, s, v = ColorUtilities.rgb_to_hsv(rgb)
        
        # Complementary is 180 degrees opposite
        comp_h = (h + 0.5) % 1.0
        comp_rgb = ColorUtilities.hsv_to_rgb((comp_h, s, v))
        
        return ColorUtilities.rgb_to_hex(comp_rgb)
    
    @staticmethod
    def generate_triadic(base_color: str) -> List[str]:
        """Generate triadic color scheme."""
        rgb = ColorUtilities.hex_to_rgb(base_color)
        h, s, v = ColorUtilities.rgb_to_hsv(rgb)
        
        colors = [base_color]
        
        # Triadic colors are 120 degrees apart
        for offset in [1/3, 2/3]:
            new_h = (h + offset) % 1.0
            new_rgb = ColorUtilities.hsv_to_rgb((new_h, s, v))
            colors.append(ColorUtilities.rgb_to_hex(new_rgb))
        
        return colors
    
    @staticmethod
    def generate_tetradic(base_color: str) -> List[str]:
        """Generate tetradic (square) color scheme."""
        rgb = ColorUtilities.hex_to_rgb(base_color)
        h, s, v = ColorUtilities.rgb_to_hsv(rgb)
        
        colors = [base_color]
        
        # Tetradic colors are 90 degrees apart
        for offset in [0.25, 0.5, 0.75]:
            new_h = (h + offset) % 1.0
            new_rgb = ColorUtilities.hsv_to_rgb((new_h, s, v))
            colors.append(ColorUtilities.rgb_to_hex(new_rgb))
        
        return colors
    
    @staticmethod
    def ensure_accessibility(
        foreground: str, 
        background: str, 
        level: str = "AA",
        target_type: str = "normal"
    ) -> str:
        """Adjust foreground color to meet accessibility requirements."""
        
        # WCAG contrast requirements
        requirements = {
            "AA": {"normal": 4.5, "large": 3.0},
            "AAA": {"normal": 7.0, "large": 4.5}
        }
        
        required_ratio = requirements.get(level, requirements["AA"]).get(target_type, 4.5)
        current_ratio = ColorUtilities.calculate_contrast_ratio(foreground, background)
        
        if current_ratio >= required_ratio:
            return foreground  # Already meets requirements
        
        # Try adjusting lightness to meet contrast ratio
        fg_rgb = ColorUtilities.hex_to_rgb(foreground)
        bg_rgb = ColorUtilities.hex_to_rgb(background)
        
        bg_luminance = ColorUtilities.calculate_luminance(bg_rgb)
        
        # Determine if we should go lighter or darker
        if bg_luminance > 0.5:
            # Light background, make foreground darker
            for lightness_adj in [-0.1, -0.2, -0.3, -0.4, -0.5]:
                adjusted_color = ColorUtilities.adjust_lightness(foreground, lightness_adj)
                ratio = ColorUtilities.calculate_contrast_ratio(adjusted_color, background)
                if ratio >= required_ratio:
                    return adjusted_color
        else:
            # Dark background, make foreground lighter
            for lightness_adj in [0.1, 0.2, 0.3, 0.4, 0.5]:
                adjusted_color = ColorUtilities.adjust_lightness(foreground, lightness_adj)
                ratio = ColorUtilities.calculate_contrast_ratio(adjusted_color, background)
                if ratio >= required_ratio:
                    return adjusted_color
        
        # If adjustment failed, return high contrast default
        return "#000000" if bg_luminance > 0.5 else "#FFFFFF"


class PaletteManager:
    """Advanced color palette management with accessibility validation."""
    
    def __init__(self, theme_engine=None):
        """Initialize palette manager.
        
        Args:
            theme_engine: Reference to theme engine for integration
        """
        self.theme_engine = theme_engine
        self._palettes: Dict[str, Dict[str, Any]] = {}
        self._metadata: Dict[str, ColorPaletteMetadata] = {}
        
        # Load built-in palettes
        self._create_builtin_palettes()
    
    def create_palette(self, name: str, base_colors: Dict[str, str], metadata: Optional[ColorPaletteMetadata] = None) -> Dict[str, Any]:
        """Create a new color palette from base colors.
        
        Args:
            name: Palette name
            base_colors: Dictionary of base color definitions
            metadata: Optional palette metadata
            
        Returns:
            Complete palette dictionary
        """
        if metadata is None:
            metadata = ColorPaletteMetadata(name=name)
        
        # Generate complete palette from base colors
        palette = self._generate_complete_palette(base_colors, metadata)
        
        # Store palette and metadata
        self._palettes[name] = palette
        self._metadata[name] = metadata
        
        logger.info(f"Created palette '{name}' with {len(palette['colors'])} colors")
        return palette
    
    def _generate_complete_palette(self, base_colors: Dict[str, str], metadata: ColorPaletteMetadata) -> Dict[str, Any]:
        """Generate complete palette from base colors."""
        palette = {
            'name': metadata.name,
            'metadata': asdict(metadata),
            'colors': {},
            'derived': {},
            'accessibility': {}
        }
        
        # Process base colors
        for color_name, color_value in base_colors.items():
            if color_name == 'primary':
                # Generate primary color variations
                palette['colors']['primary'] = self._generate_color_scale(color_value, color_name)
            elif color_name == 'background':
                # Use as background base
                palette['colors']['background'] = color_value
            else:
                # Store as is
                palette['colors'][color_name] = color_value
        
        # Generate semantic colors if not provided
        if 'success' not in palette['colors']:
            palette['colors']['success'] = "#28A745"
        if 'warning' not in palette['colors']:
            palette['colors']['warning'] = "#FFC107"
        if 'error' not in palette['colors']:
            palette['colors']['error'] = "#DC3545"
        if 'info' not in palette['colors']:
            palette['colors']['info'] = "#17A2B8"
        
        # Generate neutral scale if not provided
        if 'neutral' not in palette['colors']:
            if metadata.category == ThemeType.DARK:
                neutral_base = "#FFFFFF"
            else:
                neutral_base = "#000000"
            palette['colors']['neutral'] = self._generate_neutral_scale(neutral_base, metadata.category)
        
        # Generate derived colors
        self._generate_derived_colors(palette, metadata)
        
        # Validate accessibility
        self._validate_palette_accessibility(palette, metadata.accessibility_level)
        
        return palette
    
    def _generate_color_scale(self, base_color: str, name: str) -> Dict[str, str]:
        """Generate color scale from base color."""
        scale = {}
        variations = ColorUtilities.generate_monochromatic(base_color, 10)
        
        # Map to standard scale (50, 100, 200, ..., 900)
        scale_keys = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900]
        for i, key in enumerate(scale_keys):
            scale[str(key)] = variations[i]
        
        return scale
    
    def _generate_neutral_scale(self, base_color: str, theme_type: ThemeType) -> Dict[str, str]:
        """Generate neutral color scale."""
        scale = {}
        
        if theme_type == ThemeType.DARK:
            # For dark themes, start from white and go to black
            colors = [
                "#FFFFFF",  # 0
                "#FAFAFA",  # 50
                "#F5F5F5",  # 100
                "#EEEEEE",  # 200
                "#E0E0E0",  # 300
                "#BDBDBD",  # 400
                "#9E9E9E",  # 500
                "#757575",  # 600
                "#616161",  # 700
                "#424242",  # 800
                "#212121",  # 900
                "#000000",  # 1000
            ]
            keys = ["0", "50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "1000"]
        else:
            # For light themes, standard gray scale
            colors = [
                "#FFFFFF",  # 0
                "#FAFAFA",  # 50
                "#F5F5F5",  # 100
                "#EEEEEE",  # 200
                "#E0E0E0",  # 300
                "#BDBDBD",  # 400
                "#9E9E9E",  # 500
                "#757575",  # 600
                "#616161",  # 700
                "#424242",  # 800
                "#212121",  # 900
            ]
            keys = ["0", "50", "100", "200", "300", "400", "500", "600", "700", "800", "900"]
        
        for key, color in zip(keys, colors):
            scale[key] = color
        
        return scale
    
    def _generate_derived_colors(self, palette: Dict[str, Any], metadata: ColorPaletteMetadata) -> None:
        """Generate derived colors for common UI elements."""
        colors = palette['colors']
        derived = palette['derived']
        
        if metadata.category == ThemeType.DARK:
            # Dark theme derived colors
            derived.update({
                'background_primary': colors.get('background', '#121212'),
                'background_secondary': colors.get('neutral', {}).get('900', '#1E1E1E'),
                'background_tertiary': colors.get('neutral', {}).get('800', '#2C2C2C'),
                'text_primary': colors.get('neutral', {}).get('0', '#FFFFFF'),
                'text_secondary': colors.get('neutral', {}).get('300', '#B3B3B3'),
                'text_disabled': colors.get('neutral', {}).get('500', '#666666'),
                'border_primary': colors.get('neutral', {}).get('700', '#333333'),
                'border_secondary': colors.get('neutral', {}).get('800', '#2C2C2C'),
            })
        else:
            # Light theme derived colors
            derived.update({
                'background_primary': colors.get('background', '#FFFFFF'),
                'background_secondary': colors.get('neutral', {}).get('50', '#FAFAFA'),
                'background_tertiary': colors.get('neutral', {}).get('100', '#F5F5F5'),
                'text_primary': colors.get('neutral', {}).get('900', '#212121'),
                'text_secondary': colors.get('neutral', {}).get('600', '#757575'),
                'text_disabled': colors.get('neutral', {}).get('400', '#BDBDBD'),
                'border_primary': colors.get('neutral', {}).get('300', '#E0E0E0'),
                'border_secondary': colors.get('neutral', {}).get('200', '#EEEEEE'),
            })
        
        # Add accent and interactive colors
        primary_color = colors.get('primary')
        if isinstance(primary_color, dict):
            derived['accent_primary'] = primary_color.get('500', primary_color.get('primary', '#2196F3'))
            derived['accent_hover'] = primary_color.get('600', '#1976D2')
            derived['accent_pressed'] = primary_color.get('700', '#1565C0')
        else:
            derived['accent_primary'] = primary_color or '#2196F3'
            derived['accent_hover'] = ColorUtilities.adjust_lightness(derived['accent_primary'], -0.1)
            derived['accent_pressed'] = ColorUtilities.adjust_lightness(derived['accent_primary'], -0.2)
    
    def _validate_palette_accessibility(self, palette: Dict[str, Any], level: str = "AA") -> None:
        """Validate palette accessibility and store results."""
        accessibility = palette['accessibility']
        derived = palette['derived']
        
        # Check critical color combinations
        combinations = [
            ('text_primary', 'background_primary'),
            ('text_secondary', 'background_primary'),
            ('text_primary', 'background_secondary'),
            ('accent_primary', 'background_primary'),
        ]
        
        for fg_key, bg_key in combinations:
            fg_color = derived.get(fg_key)
            bg_color = derived.get(bg_key)
            
            if fg_color and bg_color:
                ratio = ColorUtilities.calculate_contrast_ratio(fg_color, bg_color)
                accessibility[f"{fg_key}_on_{bg_key}"] = {
                    'ratio': ratio,
                    'aa_pass': ratio >= 4.5,
                    'aaa_pass': ratio >= 7.0,
                    'level': level
                }
        
        logger.debug(f"Accessibility validation completed for palette")
    
    def generate_palette_variations(self, base_palette: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate variations of a base palette."""
        variations = []
        metadata = ColorPaletteMetadata(**base_palette['metadata'])
        
        # Generate different harmony variations
        if 'primary' in base_palette['colors']:
            primary_color = base_palette['colors']['primary']
            if isinstance(primary_color, dict):
                base_color = primary_color.get('500', list(primary_color.values())[0])
            else:
                base_color = primary_color
            
            # Analogous variation
            analogous_colors = ColorUtilities.generate_analogous(base_color)
            for i, color in enumerate(analogous_colors[1:], 1):  # Skip original
                variant_metadata = ColorPaletteMetadata(
                    name=f"{metadata.name} Analogous {i}",
                    description=f"Analogous variation of {metadata.name}",
                    harmony_type=ColorHarmony.ANALOGOUS,
                    created_from_base=metadata.name
                )
                variant = self._generate_complete_palette({'primary': color, 'background': base_palette['colors'].get('background', '#FFFFFF')}, variant_metadata)
                variations.append(variant)
            
            # Complementary variation
            comp_color = ColorUtilities.generate_complementary(base_color)
            comp_metadata = ColorPaletteMetadata(
                name=f"{metadata.name} Complementary",
                description=f"Complementary variation of {metadata.name}",
                harmony_type=ColorHarmony.COMPLEMENTARY,
                created_from_base=metadata.name
            )
            comp_variant = self._generate_complete_palette({'primary': comp_color, 'background': base_palette['colors'].get('background', '#FFFFFF')}, comp_metadata)
            variations.append(comp_variant)
        
        return variations
    
    def save_palette(self, palette: Dict[str, Any], path: Union[str, Path]) -> None:
        """Save palette to file.
        
        Args:
            palette: Palette dictionary to save
            path: File path to save to
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(palette, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Palette '{palette['name']}' saved to {path}")
    
    def load_palette(self, path: Union[str, Path]) -> Dict[str, Any]:
        """Load palette from file.
        
        Args:
            path: File path to load from
            
        Returns:
            Loaded palette dictionary
        """
        path = Path(path)
        
        if not path.exists():
            raise FileNotFoundError(f"Palette file not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            palette = json.load(f)
        
        # Store in manager
        name = palette['name']
        self._palettes[name] = palette
        self._metadata[name] = ColorPaletteMetadata(**palette['metadata'])
        
        logger.info(f"Palette '{name}' loaded from {path}")
        return palette
    
    def get_contrasting_color(self, color: str, background: str, level: str = "AA") -> str:
        """Get contrasting color that meets accessibility requirements.
        
        Args:
            color: Base color to adjust
            background: Background color to contrast against
            level: Accessibility level (AA or AAA)
            
        Returns:
            Color that meets contrast requirements
        """
        return ColorUtilities.ensure_accessibility(color, background, level)
    
    def get_available_palettes(self) -> List[str]:
        """Get list of available palette names."""
        return list(self._palettes.keys())
    
    def get_palette(self, name: str) -> Optional[Dict[str, Any]]:
        """Get palette by name."""
        return self._palettes.get(name)
    
    def get_palette_metadata(self, name: str) -> Optional[ColorPaletteMetadata]:
        """Get palette metadata by name."""
        return self._metadata.get(name)
    
    def _create_builtin_palettes(self) -> None:
        """Create built-in professional palettes."""
        
        # Professional Dark Palette
        dark_metadata = ColorPaletteMetadata(
            name="Professional Dark",
            description="High-contrast dark theme for professional applications",
            author="TORE Matrix Labs",
            category=ThemeType.DARK,
            accessibility_level="AAA"
        )
        
        dark_base_colors = {
            'primary': '#2196F3',
            'background': '#121212'
        }
        
        self.create_palette("professional_dark", dark_base_colors, dark_metadata)
        
        # Professional Light Palette
        light_metadata = ColorPaletteMetadata(
            name="Professional Light",
            description="Clean light theme for professional applications",
            author="TORE Matrix Labs",
            category=ThemeType.LIGHT,
            accessibility_level="AAA"
        )
        
        light_base_colors = {
            'primary': '#1976D2',
            'background': '#FFFFFF'
        }
        
        self.create_palette("professional_light", light_base_colors, light_metadata)
        
        # High Contrast Palette
        high_contrast_metadata = ColorPaletteMetadata(
            name="High Contrast",
            description="Maximum contrast theme for accessibility",
            author="TORE Matrix Labs",
            category=ThemeType.HIGH_CONTRAST,
            accessibility_level="AAA"
        )
        
        high_contrast_base_colors = {
            'primary': '#0000FF',
            'background': '#FFFFFF'
        }
        
        self.create_palette("high_contrast", high_contrast_base_colors, high_contrast_metadata)
        
        logger.info("Built-in palettes created successfully")