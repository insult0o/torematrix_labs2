"""Advanced accessibility features and WCAG compliance for themes.

Provides comprehensive accessibility support including high contrast modes,
color blindness filters, WCAG compliance validation, and accessibility
enhancement features.
"""

import logging
import math
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QColor

from .base import Theme, ColorPalette
from .colors import ColorAnalyzer, ColorManipulator, ColorBlindnessType
from .types import ColorDefinition, ThemeMetadata
from .exceptions import ThemeError

logger = logging.getLogger(__name__)


class AccessibilityLevel(Enum):
    """WCAG accessibility compliance levels."""
    A = "A"
    AA = "AA"
    AAA = "AAA"


class TextSize(Enum):
    """Text size categories for accessibility."""
    NORMAL = "normal"      # Regular text
    LARGE = "large"        # 18pt+ or 14pt+ bold
    GRAPHICAL = "graphical"  # UI components


@dataclass
class AccessibilityRequirement:
    """WCAG accessibility requirements."""
    level: AccessibilityLevel
    text_size: TextSize
    min_contrast_ratio: float


@dataclass
class AccessibilityTestResult:
    """Result of an accessibility test."""
    test_name: str
    passed: bool
    actual_value: float
    required_value: float
    level: AccessibilityLevel
    recommendation: str


@dataclass
class AccessibilityReport:
    """Comprehensive accessibility report."""
    overall_compliance: AccessibilityLevel
    tests: List[AccessibilityTestResult]
    color_blindness_issues: List[str]
    recommendations: List[str]
    score: float  # 0-100


class AccessibilityValidator:
    """Comprehensive accessibility validation for color themes."""
    
    # WCAG 2.1 contrast requirements
    CONTRAST_REQUIREMENTS = {
        AccessibilityLevel.AA: {
            TextSize.NORMAL: 4.5,
            TextSize.LARGE: 3.0,
            TextSize.GRAPHICAL: 3.0
        },
        AccessibilityLevel.AAA: {
            TextSize.NORMAL: 7.0,
            TextSize.LARGE: 4.5,
            TextSize.GRAPHICAL: 4.5
        }
    }
    
    def __init__(self):
        """Initialize accessibility validator."""
        self.requirements = self._create_requirements()
    
    def _create_requirements(self) -> List[AccessibilityRequirement]:
        """Create list of accessibility requirements."""
        requirements = []
        
        for level, size_reqs in self.CONTRAST_REQUIREMENTS.items():
            for text_size, min_ratio in size_reqs.items():
                requirements.append(AccessibilityRequirement(
                    level=level,
                    text_size=text_size,
                    min_contrast_ratio=min_ratio
                ))
        
        return requirements
    
    def validate_color_palette(self, palette: Dict[str, Any], target_level: AccessibilityLevel = AccessibilityLevel.AA) -> AccessibilityReport:
        """Validate entire color palette for accessibility.
        
        Args:
            palette: Color palette dictionary
            target_level: Target accessibility level
            
        Returns:
            Comprehensive accessibility report
        """
        tests = []
        recommendations = []
        color_blindness_issues = []
        
        # Extract colors and derived colors
        colors = palette.get('colors', {})
        derived = palette.get('derived', {})
        
        # Test critical color combinations
        critical_combinations = [
            ('text_primary', 'background_primary', TextSize.NORMAL),
            ('text_secondary', 'background_primary', TextSize.NORMAL),
            ('text_primary', 'background_secondary', TextSize.NORMAL),
            ('accent_primary', 'background_primary', TextSize.GRAPHICAL),
        ]
        
        for fg_key, bg_key, text_size in critical_combinations:
            fg_color = derived.get(fg_key)
            bg_color = derived.get(bg_key)
            
            if fg_color and bg_color:
                test_result = self._test_contrast_ratio(
                    fg_color, bg_color, f"{fg_key}_on_{bg_key}", 
                    target_level, text_size
                )
                tests.append(test_result)
                
                if not test_result.passed:
                    recommendations.append(
                        f"Improve contrast between {fg_key} and {bg_key}: "
                        f"current ratio {test_result.actual_value:.2f}, "
                        f"required {test_result.required_value:.2f}"
                    )
        
        # Test color blindness compatibility
        color_blindness_issues = self._test_color_blindness_compatibility(colors, derived)
        
        # Test semantic color accessibility
        semantic_tests = self._test_semantic_colors(colors, derived, target_level)
        tests.extend(semantic_tests)
        
        # Calculate overall compliance and score
        overall_compliance, score = self._calculate_overall_compliance(tests, target_level)
        
        # Generate additional recommendations
        additional_recommendations = self._generate_recommendations(tests, palette)
        recommendations.extend(additional_recommendations)
        
        return AccessibilityReport(
            overall_compliance=overall_compliance,
            tests=tests,
            color_blindness_issues=color_blindness_issues,
            recommendations=recommendations,
            score=score
        )
    
    def _test_contrast_ratio(self, foreground: str, background: str, test_name: str, 
                           level: AccessibilityLevel, text_size: TextSize) -> AccessibilityTestResult:
        """Test contrast ratio between two colors."""
        actual_ratio = ColorAnalyzer.calculate_contrast_ratio(foreground, background)
        required_ratio = self.CONTRAST_REQUIREMENTS[level][text_size]
        
        passed = actual_ratio >= required_ratio
        
        if not passed:
            recommendation = f"Increase contrast to meet {level.value} standards"
        else:
            recommendation = "Contrast ratio meets requirements"
        
        return AccessibilityTestResult(
            test_name=test_name,
            passed=passed,
            actual_value=actual_ratio,
            required_value=required_ratio,
            level=level,
            recommendation=recommendation
        )
    
    def _test_color_blindness_compatibility(self, colors: Dict[str, Any], 
                                          derived: Dict[str, Any]) -> List[str]:
        """Test compatibility with different types of color blindness."""
        issues = []
        
        # Test primary colors for color blindness
        test_colors = {
            'success': colors.get('success'),
            'warning': colors.get('warning'),
            'error': colors.get('error'),
            'info': colors.get('info'),
            'primary': colors.get('primary')
        }
        
        # Test each color blindness type
        for blindness_type in ColorBlindnessType:
            problematic_colors = []
            
            for name, color in test_colors.items():
                if not color:
                    continue
                
                # Get the actual color value
                if isinstance(color, dict):
                    color = color.get('500', color.get('primary', list(color.values())[0]))
                
                # Simulate color blindness
                simulated = ColorManipulator.simulate_color_blindness(color, blindness_type)
                
                # Check if the color changes significantly
                original_analysis = ColorAnalyzer.analyze_color(color)
                simulated_analysis = ColorAnalyzer.analyze_color(simulated)
                
                # Calculate difference in perceived brightness
                brightness_diff = abs(original_analysis.perceived_brightness - 
                                    simulated_analysis.perceived_brightness)
                
                # If brightness difference is minimal, it might be hard to distinguish
                if brightness_diff < 0.1:
                    problematic_colors.append(name)
            
            if problematic_colors:
                issues.append(f"{blindness_type.value}: Colors {', '.join(problematic_colors)} "
                            f"may be difficult to distinguish")
        
        return issues
    
    def _test_semantic_colors(self, colors: Dict[str, Any], derived: Dict[str, Any], 
                            level: AccessibilityLevel) -> List[AccessibilityTestResult]:
        """Test semantic colors for accessibility."""
        tests = []
        background = derived.get('background_primary', '#FFFFFF')
        
        semantic_colors = {
            'success': colors.get('success'),
            'warning': colors.get('warning'),
            'error': colors.get('error'),
            'info': colors.get('info')
        }
        
        for name, color in semantic_colors.items():
            if color:
                test = self._test_contrast_ratio(
                    color, background, f"semantic_{name}_contrast", 
                    level, TextSize.GRAPHICAL
                )
                tests.append(test)
        
        return tests
    
    def _calculate_overall_compliance(self, tests: List[AccessibilityTestResult], 
                                    target_level: AccessibilityLevel) -> Tuple[AccessibilityLevel, float]:
        """Calculate overall compliance level and score."""
        if not tests:
            return AccessibilityLevel.A, 0.0
        
        # Count passed tests by level
        aa_tests = [t for t in tests if t.level == AccessibilityLevel.AA]
        aaa_tests = [t for t in tests if t.level == AccessibilityLevel.AAA]
        
        aa_passed = sum(1 for t in aa_tests if t.passed)
        aaa_passed = sum(1 for t in aaa_tests if t.passed)
        
        # Calculate pass rates
        aa_pass_rate = aa_passed / len(aa_tests) if aa_tests else 0
        aaa_pass_rate = aaa_passed / len(aaa_tests) if aaa_tests else 0
        
        # Determine overall compliance
        if aaa_pass_rate >= 0.9:
            overall_compliance = AccessibilityLevel.AAA
        elif aa_pass_rate >= 0.9:
            overall_compliance = AccessibilityLevel.AA
        else:
            overall_compliance = AccessibilityLevel.A
        
        # Calculate score (0-100)
        total_tests = len(tests)
        passed_tests = sum(1 for t in tests if t.passed)
        score = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        return overall_compliance, score
    
    def _generate_recommendations(self, tests: List[AccessibilityTestResult], 
                                palette: Dict[str, Any]) -> List[str]:
        """Generate additional accessibility recommendations."""
        recommendations = []
        
        # Check for insufficient color differentiation
        failed_tests = [t for t in tests if not t.passed]
        
        if len(failed_tests) > len(tests) * 0.3:
            recommendations.append(
                "Consider using a high contrast theme variant for better accessibility"
            )
        
        # Check for color-only information
        colors = palette.get('colors', {})
        if 'success' in colors and 'error' in colors:
            success_color = colors['success']
            error_color = colors['error']
            
            if isinstance(success_color, dict):
                success_color = success_color.get('500', list(success_color.values())[0])
            if isinstance(error_color, dict):
                error_color = error_color.get('500', list(error_color.values())[0])
            
            if success_color and error_color:
                # Check if colors are distinguishable for color blind users
                for blindness_type in [ColorBlindnessType.DEUTERANOPIA, ColorBlindnessType.PROTANOPIA]:
                    sim_success = ColorManipulator.simulate_color_blindness(success_color, blindness_type)
                    sim_error = ColorManipulator.simulate_color_blindness(error_color, blindness_type)
                    
                    if ColorAnalyzer.calculate_contrast_ratio(sim_success, sim_error) < 1.5:
                        recommendations.append(
                            "Success and error colors may be indistinguishable for color blind users. "
                            "Consider adding icons or other visual indicators."
                        )
                        break
        
        return recommendations
    
    def suggest_improvements(self, palette: Dict[str, Any], 
                           target_level: AccessibilityLevel = AccessibilityLevel.AA) -> Dict[str, str]:
        """Suggest specific color improvements for accessibility.
        
        Args:
            palette: Color palette dictionary
            target_level: Target accessibility level
            
        Returns:
            Dictionary mapping color keys to improved color values
        """
        improvements = {}
        derived = palette.get('derived', {})
        
        # Critical color combinations to improve
        combinations = [
            ('text_primary', 'background_primary'),
            ('text_secondary', 'background_primary'),
            ('accent_primary', 'background_primary'),
        ]
        
        for fg_key, bg_key in combinations:
            fg_color = derived.get(fg_key)
            bg_color = derived.get(bg_key)
            
            if fg_color and bg_color:
                current_ratio = ColorAnalyzer.calculate_contrast_ratio(fg_color, bg_color)
                required_ratio = self.CONTRAST_REQUIREMENTS[target_level][TextSize.NORMAL]
                
                if current_ratio < required_ratio:
                    # Suggest improved foreground color
                    improved_fg = self._improve_contrast(fg_color, bg_color, required_ratio)
                    improvements[fg_key] = improved_fg
        
        return improvements
    
    def _improve_contrast(self, foreground: str, background: str, target_ratio: float) -> str:
        """Improve contrast between foreground and background colors."""
        current_ratio = ColorAnalyzer.calculate_contrast_ratio(foreground, background)
        
        if current_ratio >= target_ratio:
            return foreground  # Already meets requirements
        
        # Determine if background is light or dark
        bg_analysis = ColorAnalyzer.analyze_color(background)
        
        # Adjust foreground color
        adjustment_step = 0.05
        max_adjustments = 20
        
        improved_color = foreground
        
        for i in range(max_adjustments):
            if bg_analysis.is_light:
                # Light background - make foreground darker
                improved_color = ColorManipulator.adjust_lightness(improved_color, -adjustment_step)
            else:
                # Dark background - make foreground lighter
                improved_color = ColorManipulator.adjust_lightness(improved_color, adjustment_step)
            
            new_ratio = ColorAnalyzer.calculate_contrast_ratio(improved_color, background)
            
            if new_ratio >= target_ratio:
                break
        
        return improved_color
    
    def generate_high_contrast_variant(self, palette: Dict[str, Any]) -> Dict[str, Any]:
        """Generate high contrast variant of a palette.
        
        Args:
            palette: Original palette dictionary
            
        Returns:
            High contrast palette variant
        """
        high_contrast_palette = palette.copy()
        
        # Create high contrast colors
        if palette.get('metadata', {}).get('category') == 'dark':
            # Dark theme high contrast
            high_contrast_colors = {
                'background_primary': '#000000',
                'background_secondary': '#1A1A1A',
                'text_primary': '#FFFFFF',
                'text_secondary': '#E0E0E0',
                'accent_primary': '#00BFFF',  # Bright blue
                'border_primary': '#404040',
                'success': '#00FF00',         # Bright green
                'warning': '#FFFF00',         # Bright yellow
                'error': '#FF0000',           # Bright red
                'info': '#00FFFF',            # Bright cyan
            }
        else:
            # Light theme high contrast
            high_contrast_colors = {
                'background_primary': '#FFFFFF',
                'background_secondary': '#F0F0F0',
                'text_primary': '#000000',
                'text_secondary': '#404040',
                'accent_primary': '#0000FF',  # Bright blue
                'border_primary': '#808080',
                'success': '#008000',         # Dark green
                'warning': '#FF8000',         # Orange
                'error': '#800000',           # Dark red
                'info': '#000080',            # Dark blue
            }
        
        # Update derived colors
        high_contrast_palette['derived'] = high_contrast_colors
        
        # Update metadata
        metadata = high_contrast_palette.get('metadata', {})
        metadata['name'] = metadata.get('name', 'Theme') + ' High Contrast'
        metadata['description'] = 'High contrast variant for maximum accessibility'
        metadata['accessibility_level'] = 'AAA'
        metadata['category'] = 'high_contrast'
        
        logger.info("Generated high contrast palette variant")
        return high_contrast_palette


class HighContrastLevel(Enum):
    """High contrast enhancement levels."""
    STANDARD = "standard"    # WCAG AA (4.5:1)
    ENHANCED = "enhanced"    # WCAG AAA (7:1)
    MAXIMUM = "maximum"      # Pure black/white (21:1)


@dataclass
class ContrastAnalysis:
    """Results of contrast ratio analysis."""
    ratio: float
    passes_aa: bool
    passes_aaa: bool
    meets_requirement: bool
    recommendation: str
    adjusted_color: Optional[str] = None


@dataclass
class AccessibilityReport:
    """Comprehensive accessibility analysis report."""
    theme_name: str
    overall_compliance: AccessibilityLevel
    issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    contrast_results: Dict[str, ContrastAnalysis]
    color_blind_friendly: bool
    high_contrast_available: bool
    improvements_made: List[str]


@dataclass
class AccessibilitySettings:
    """User accessibility settings and preferences."""
    high_contrast_enabled: bool = False
    high_contrast_level: HighContrastLevel = HighContrastLevel.STANDARD
    color_blindness_filter: Optional[ColorBlindnessType] = None
    increased_font_sizes: bool = False
    enhanced_focus_indicators: bool = False
    reduced_motion: bool = False
    reduced_transparency: bool = False
    high_contrast_cursor: bool = False
    keyboard_navigation_enhanced: bool = False


class ColorBlindnessSimulator:
    """Simulate different types of color blindness."""
    
    # LMS transformation matrices for different color blindness types
    TRANSFORMATION_MATRICES = {
        ColorBlindnessType.PROTANOPIA: [
            [0.567, 0.433, 0.000],
            [0.558, 0.442, 0.000],
            [0.000, 0.242, 0.758]
        ],
        ColorBlindnessType.DEUTERANOPIA: [
            [0.625, 0.375, 0.000],
            [0.700, 0.300, 0.000],
            [0.000, 0.300, 0.700]
        ],
        ColorBlindnessType.TRITANOPIA: [
            [0.950, 0.050, 0.000],
            [0.000, 0.433, 0.567],
            [0.000, 0.475, 0.525]
        ],
        ColorBlindnessType.PROTANOMALY: [
            [0.817, 0.183, 0.000],
            [0.333, 0.667, 0.000],
            [0.000, 0.125, 0.875]
        ],
        ColorBlindnessType.DEUTERANOMALY: [
            [0.800, 0.200, 0.000],
            [0.258, 0.742, 0.000],
            [0.000, 0.142, 0.858]
        ],
        ColorBlindnessType.TRITANOMALY: [
            [0.967, 0.033, 0.000],
            [0.000, 0.733, 0.267],
            [0.000, 0.183, 0.817]
        ]
    }
    
    @classmethod
    def simulate_color_blindness(cls, color: str, blindness_type: ColorBlindnessType) -> str:
        """Simulate how a color appears to someone with color blindness.
        
        Args:
            color: Original color in hex format
            blindness_type: Type of color blindness to simulate
            
        Returns:
            Simulated color in hex format
        """
        if blindness_type == ColorBlindnessType.ACHROMATOPSIA:
            return cls._to_grayscale(color)
        elif blindness_type == ColorBlindnessType.ACHROMATOMALY:
            return cls._partial_grayscale(color, 0.5)
        
        # Convert to RGB
        rgb = cls._hex_to_rgb(color)
        
        # Apply transformation matrix
        matrix = cls.TRANSFORMATION_MATRICES.get(blindness_type)
        if not matrix:
            return color
        
        # Linear RGB
        linear_rgb = [cls._gamma_to_linear(c / 255.0) for c in rgb]
        
        # Apply color blindness matrix
        new_rgb = [
            matrix[0][0] * linear_rgb[0] + matrix[0][1] * linear_rgb[1] + matrix[0][2] * linear_rgb[2],
            matrix[1][0] * linear_rgb[0] + matrix[1][1] * linear_rgb[1] + matrix[1][2] * linear_rgb[2],
            matrix[2][0] * linear_rgb[0] + matrix[2][1] * linear_rgb[1] + matrix[2][2] * linear_rgb[2]
        ]
        
        # Convert back to sRGB
        srgb = [cls._linear_to_gamma(c) for c in new_rgb]
        final_rgb = [max(0, min(255, int(c * 255))) for c in srgb]
        
        return cls._rgb_to_hex(final_rgb)
    
    @classmethod
    def _hex_to_rgb(cls, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    @classmethod
    def _rgb_to_hex(cls, rgb: Tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex color."""
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    @classmethod
    def _gamma_to_linear(cls, value: float) -> float:
        """Convert gamma-corrected value to linear."""
        if value <= 0.04045:
            return value / 12.92
        else:
            return pow((value + 0.055) / 1.055, 2.4)
    
    @classmethod
    def _linear_to_gamma(cls, value: float) -> float:
        """Convert linear value to gamma-corrected."""
        if value <= 0.0031308:
            return 12.92 * value
        else:
            return 1.055 * pow(value, 1.0 / 2.4) - 0.055
    
    @classmethod
    def _to_grayscale(cls, color: str) -> str:
        """Convert color to grayscale."""
        rgb = cls._hex_to_rgb(color)
        # Use luminance formula
        gray = int(0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2])
        return cls._rgb_to_hex((gray, gray, gray))
    
    @classmethod
    def _partial_grayscale(cls, color: str, factor: float) -> str:
        """Convert color to partial grayscale."""
        rgb = cls._hex_to_rgb(color)
        gray = int(0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2])
        
        # Blend with original
        new_rgb = (
            int(rgb[0] * (1 - factor) + gray * factor),
            int(rgb[1] * (1 - factor) + gray * factor),
            int(rgb[2] * (1 - factor) + gray * factor)
        )
        return cls._rgb_to_hex(new_rgb)


class HighContrastGenerator:
    """Generate high contrast theme variants."""
    
    CONTRAST_REQUIREMENTS = {
        HighContrastLevel.STANDARD: 4.5,   # WCAG AA
        HighContrastLevel.ENHANCED: 7.0,   # WCAG AAA
        HighContrastLevel.MAXIMUM: 21.0    # Pure black/white
    }
    
    @classmethod
    def generate_high_contrast_theme(cls, base_theme: Theme, level: HighContrastLevel) -> Theme:
        """Generate high contrast variant of existing theme.
        
        Args:
            base_theme: Original theme to enhance
            level: Desired contrast level
            
        Returns:
            High contrast version of the theme
        """
        target_ratio = cls.CONTRAST_REQUIREMENTS[level]
        
        # Create new theme metadata
        hc_metadata = ThemeMetadata(
            name=f"{base_theme.metadata.name} (High Contrast {level.value.upper()})",
            version=base_theme.metadata.version,
            description=f"High contrast variant of {base_theme.metadata.name}",
            author=base_theme.metadata.author,
            category=base_theme.metadata.category,
            accessibility_compliant=True,
            high_contrast_available=True
        )
        
        # Generate high contrast colors
        hc_colors = cls._generate_high_contrast_colors(base_theme.get_color_palette(), target_ratio)
        
        # Create new theme
        return Theme(
            name=hc_metadata.name,
            metadata=hc_metadata,
            data={
                'colors': hc_colors,
                'typography': base_theme._data.get('typography', {}),
                'components': base_theme._data.get('components', {}),
                'variables': base_theme._data.get('variables', {}),
                'accessibility': {
                    'high_contrast': True,
                    'contrast_level': level.value,
                    'base_theme': base_theme.name
                }
            }
        )
    
    @classmethod
    def _generate_high_contrast_colors(cls, base_colors: ColorPalette, 
                                     target_ratio: float) -> Dict[str, str]:
        """Generate high contrast color palette."""
        hc_colors = {}
        
        # Determine if theme is light or dark based on background
        bg_color = base_colors.get_color_value('background', '#ffffff')
        bg_luminance = ColorAnalyzer.calculate_luminance(bg_color)
        is_light_theme = bg_luminance > 0.5
        
        if target_ratio >= 21.0:  # Maximum contrast
            # Use pure black and white
            if is_light_theme:
                text_color = '#000000'
                bg_color = '#ffffff'
                accent_color = '#0000ff'
            else:
                text_color = '#ffffff'
                bg_color = '#000000'
                accent_color = '#00ffff'
        else:
            # Calculate appropriate colors for target ratio
            if is_light_theme:
                text_color = cls._find_dark_color_for_ratio(bg_color, target_ratio)
                accent_color = cls._adjust_color_for_contrast(
                    base_colors.get_color_value('accent', '#007bff'), 
                    bg_color, target_ratio
                )
            else:
                text_color = cls._find_light_color_for_ratio(bg_color, target_ratio)
                accent_color = cls._adjust_color_for_contrast(
                    base_colors.get_color_value('accent', '#007bff'), 
                    bg_color, target_ratio
                )
        
        # Build high contrast color map
        hc_colors.update({
            'background': bg_color,
            'text_primary': text_color,
            'text_secondary': text_color,
            'accent': accent_color,
            'border': text_color,
            'surface': bg_color,
            'surface_variant': cls._blend_colors(bg_color, text_color, 0.1),
            'selection_background': accent_color,
            'selection_text': bg_color,
            'button_background': bg_color,
            'button_text': text_color,
            'button_border': text_color,
            'button_hover': cls._blend_colors(bg_color, text_color, 0.1),
            'button_pressed': cls._blend_colors(bg_color, text_color, 0.2),
            'icon_primary': text_color,
            'icon_secondary': text_color,
            'icon_disabled': cls._blend_colors(bg_color, text_color, 0.5),
        })
        
        return hc_colors
    
    @classmethod
    def _find_dark_color_for_ratio(cls, bg_color: str, target_ratio: float) -> str:
        """Find dark color that meets contrast ratio with background."""
        bg_luminance = ColorAnalyzer.calculate_luminance(bg_color)
        
        # Calculate required luminance for text
        # contrast = (L1 + 0.05) / (L2 + 0.05) where L1 > L2
        required_luminance = (bg_luminance + 0.05) / target_ratio - 0.05
        required_luminance = max(0, required_luminance)
        
        # Convert luminance to RGB (approximate)
        gray_value = int(required_luminance * 255)
        return f"#{gray_value:02x}{gray_value:02x}{gray_value:02x}"
    
    @classmethod
    def _find_light_color_for_ratio(cls, bg_color: str, target_ratio: float) -> str:
        """Find light color that meets contrast ratio with background."""
        bg_luminance = ColorAnalyzer.calculate_luminance(bg_color)
        
        # Calculate required luminance for text
        required_luminance = target_ratio * (bg_luminance + 0.05) - 0.05
        required_luminance = min(1, required_luminance)
        
        # Convert luminance to RGB (approximate)
        gray_value = int(required_luminance * 255)
        return f"#{gray_value:02x}{gray_value:02x}{gray_value:02x}"
    
    @classmethod
    def _adjust_color_for_contrast(cls, color: str, bg_color: str, 
                                  target_ratio: float) -> str:
        """Adjust color to meet contrast ratio with background."""
        current_ratio = ColorAnalyzer.calculate_contrast_ratio(color, bg_color)
        
        if current_ratio >= target_ratio:
            return color  # Already meets requirement
        
        # Determine if we need to make it lighter or darker
        color_luminance = ColorAnalyzer.calculate_luminance(color)
        bg_luminance = ColorAnalyzer.calculate_luminance(bg_color)
        
        if color_luminance > bg_luminance:
            # Make lighter
            return cls._find_light_color_for_ratio(bg_color, target_ratio)
        else:
            # Make darker
            return cls._find_dark_color_for_ratio(bg_color, target_ratio)
    
    @classmethod
    def _blend_colors(cls, color1: str, color2: str, factor: float) -> str:
        """Blend two colors by a given factor."""
        rgb1 = ColorBlindnessSimulator._hex_to_rgb(color1)
        rgb2 = ColorBlindnessSimulator._hex_to_rgb(color2)
        
        blended = (
            int(rgb1[0] * (1 - factor) + rgb2[0] * factor),
            int(rgb1[1] * (1 - factor) + rgb2[1] * factor),
            int(rgb1[2] * (1 - factor) + rgb2[2] * factor)
        )
        
        return ColorBlindnessSimulator._rgb_to_hex(blended)


class AccessibilityThemeValidator:
    """Enhanced accessibility validator for theme systems."""
    
    # WCAG 2.1 contrast requirements
    WCAG_REQUIREMENTS = {
        AccessibilityLevel.AA: {
            TextSize.NORMAL: 4.5,
            TextSize.LARGE: 3.0,
            TextSize.GRAPHICAL: 3.0
        },
        AccessibilityLevel.AAA: {
            TextSize.NORMAL: 7.0,
            TextSize.LARGE: 4.5,
            TextSize.GRAPHICAL: 3.0
        }
    }
    
    @classmethod
    def validate_theme_accessibility(cls, theme: Theme, 
                                   target_level: AccessibilityLevel = AccessibilityLevel.AA) -> AccessibilityReport:
        """Perform comprehensive accessibility validation of a theme.
        
        Args:
            theme: Theme to validate
            target_level: Target WCAG compliance level
            
        Returns:
            Detailed accessibility report
        """
        issues = []
        warnings = []
        recommendations = []
        contrast_results = {}
        improvements_made = []
        
        colors = theme.get_color_palette()
        if not colors:
            return AccessibilityReport(
                theme_name=theme.name,
                overall_compliance=AccessibilityLevel.A,
                issues=["No color palette found"],
                warnings=[],
                recommendations=["Add color palette to theme"],
                contrast_results={},
                color_blind_friendly=False,
                high_contrast_available=False,
                improvements_made=[]
            )
        
        # Get background color
        bg_color = colors.get_color_value('background', '#ffffff')
        
        # Test critical color combinations
        critical_combinations = [
            ('text_primary', 'background', TextSize.NORMAL, 'Primary text on background'),
            ('text_secondary', 'background', TextSize.NORMAL, 'Secondary text on background'),
            ('button_text', 'button_background', TextSize.NORMAL, 'Button text'),
            ('selection_text', 'selection_background', TextSize.NORMAL, 'Selected text'),
            ('accent', 'background', TextSize.GRAPHICAL, 'Accent color contrast'),
            ('border', 'background', TextSize.GRAPHICAL, 'Border visibility'),
        ]
        
        for fg_key, bg_key, text_size, description in critical_combinations:
            fg_color = colors.get_color_value(fg_key, '#000000')
            bg_color = colors.get_color_value(bg_key, '#ffffff')
            
            analysis = cls._analyze_contrast(fg_color, bg_color, text_size, target_level)
            contrast_results[f"{fg_key}_on_{bg_key}"] = analysis
            
            if not analysis.meets_requirement:
                issues.append(f"{description}: {analysis.recommendation}")
            elif not analysis.passes_aaa:
                warnings.append(f"{description}: Could be improved for AAA compliance")
        
        # Check color blindness friendliness
        color_blind_friendly = cls._check_color_blindness_friendliness(theme)
        if not color_blind_friendly:
            warnings.append("Theme may not be suitable for users with color blindness")
            recommendations.append("Consider using patterns, textures, or shapes in addition to color")
        
        # Check if high contrast variant is available
        high_contrast_available = theme._data.get('accessibility', {}).get('high_contrast', False)
        if not high_contrast_available:
            recommendations.append("Consider providing a high contrast variant")
        
        # Determine overall compliance level
        overall_compliance = AccessibilityLevel.A
        if all(result.passes_aa for result in contrast_results.values()):
            overall_compliance = AccessibilityLevel.AA
            if all(result.passes_aaa for result in contrast_results.values()):
                overall_compliance = AccessibilityLevel.AAA
        
        return AccessibilityReport(
            theme_name=theme.name,
            overall_compliance=overall_compliance,
            issues=issues,
            warnings=warnings,
            recommendations=recommendations,
            contrast_results=contrast_results,
            color_blind_friendly=color_blind_friendly,
            high_contrast_available=high_contrast_available,
            improvements_made=improvements_made
        )
    
    @classmethod
    def _analyze_contrast(cls, fg_color: str, bg_color: str, text_size: TextSize,
                         target_level: AccessibilityLevel) -> ContrastAnalysis:
        """Analyze contrast ratio between foreground and background colors."""
        ratio = ColorAnalyzer.calculate_contrast_ratio(fg_color, bg_color)
        
        # Get requirements
        aa_req = cls.WCAG_REQUIREMENTS[AccessibilityLevel.AA][text_size]
        aaa_req = cls.WCAG_REQUIREMENTS[AccessibilityLevel.AAA][text_size]
        target_req = cls.WCAG_REQUIREMENTS[target_level][text_size]
        
        passes_aa = ratio >= aa_req
        passes_aaa = ratio >= aaa_req
        meets_requirement = ratio >= target_req
        
        # Generate recommendation
        if meets_requirement:
            if passes_aaa:
                recommendation = f"Excellent contrast ({ratio:.1f}:1, exceeds AAA)"
            else:
                recommendation = f"Good contrast ({ratio:.1f}:1, meets {target_level.value})"
        else:
            needed_ratio = target_req
            recommendation = f"Insufficient contrast ({ratio:.1f}:1, needs {needed_ratio}:1 for {target_level.value})"
        
        # Suggest adjusted color if needed
        adjusted_color = None
        if not meets_requirement:
            adjusted_color = HighContrastGenerator._adjust_color_for_contrast(fg_color, bg_color, target_req)
        
        return ContrastAnalysis(
            ratio=ratio,
            passes_aa=passes_aa,
            passes_aaa=passes_aaa,
            meets_requirement=meets_requirement,
            recommendation=recommendation,
            adjusted_color=adjusted_color
        )
    
    @classmethod
    def _check_color_blindness_friendliness(cls, theme: Theme) -> bool:
        """Check if theme is friendly to color blind users."""
        colors = theme.get_color_palette()
        if not colors:
            return False
        
        # Test critical color combinations under different color blindness conditions
        critical_pairs = [
            ('text_primary', 'background'),
            ('accent', 'background'),
            ('selection_text', 'selection_background'),
        ]
        
        for fg_key, bg_key in critical_pairs:
            fg_color = colors.get_color_value(fg_key, '#000000')
            bg_color = colors.get_color_value(bg_key, '#ffffff')
            
            # Test under different color blindness conditions
            for blindness_type in [ColorBlindnessType.PROTANOPIA, ColorBlindnessType.DEUTERANOPIA, ColorBlindnessType.TRITANOPIA]:
                sim_fg = ColorBlindnessSimulator.simulate_color_blindness(fg_color, blindness_type)
                sim_bg = ColorBlindnessSimulator.simulate_color_blindness(bg_color, blindness_type)
                
                ratio = ColorAnalyzer.calculate_contrast_ratio(sim_fg, sim_bg)
                if ratio < 3.0:  # Minimum for basic usability
                    return False
        
        return True


class AccessibilityManager(QObject):
    """Comprehensive accessibility features and compliance management."""
    
    # Signals
    settingsChanged = pyqtSignal(AccessibilitySettings)
    highContrastToggled = pyqtSignal(bool)
    colorBlindnessFilterChanged = pyqtSignal(object)  # ColorBlindnessType or None
    
    def __init__(self, theme_engine):
        """Initialize accessibility manager.
        
        Args:
            theme_engine: Theme engine instance for integration
        """
        super().__init__()
        self.theme_engine = theme_engine
        self._settings = AccessibilitySettings()
        self._original_themes: Dict[str, Theme] = {}
        self._high_contrast_themes: Dict[str, Dict[str, Theme]] = {}
        
        # Connect to theme engine
        if hasattr(self.theme_engine, 'themeChanged'):
            self.theme_engine.themeChanged.connect(self._on_theme_changed)
    
    def get_accessibility_settings(self) -> AccessibilitySettings:
        """Get current accessibility settings."""
        return self._settings
    
    def update_settings(self, settings: AccessibilitySettings) -> None:
        """Update accessibility settings.
        
        Args:
            settings: New accessibility settings
        """
        old_settings = self._settings
        self._settings = settings
        
        # Apply changes
        if old_settings.high_contrast_enabled != settings.high_contrast_enabled:
            self._apply_high_contrast(settings.high_contrast_enabled, settings.high_contrast_level)
        
        if old_settings.color_blindness_filter != settings.color_blindness_filter:
            self._apply_color_blindness_filter(settings.color_blindness_filter)
        
        self.settingsChanged.emit(settings)
    
    def enable_high_contrast_mode(self, level: HighContrastLevel = HighContrastLevel.STANDARD) -> bool:
        """Enable high contrast mode.
        
        Args:
            level: High contrast enhancement level
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._settings.high_contrast_enabled = True
            self._settings.high_contrast_level = level
            
            success = self._apply_high_contrast(True, level)
            if success:
                self.highContrastToggled.emit(True)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to enable high contrast mode: {e}")
            return False
    
    def disable_high_contrast_mode(self) -> bool:
        """Disable high contrast mode."""
        try:
            self._settings.high_contrast_enabled = False
            
            success = self._apply_high_contrast(False, self._settings.high_contrast_level)
            if success:
                self.highContrastToggled.emit(False)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to disable high contrast mode: {e}")
            return False
    
    def apply_color_blindness_filter(self, filter_type: Optional[ColorBlindnessType]) -> bool:
        """Apply color blindness simulation filter.
        
        Args:
            filter_type: Type of color blindness to simulate (None to disable)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._settings.color_blindness_filter = filter_type
            
            success = self._apply_color_blindness_filter(filter_type)
            if success:
                self.colorBlindnessFilterChanged.emit(filter_type)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to apply color blindness filter: {e}")
            return False
    
    def validate_accessibility_compliance(self, theme: Theme, 
                                        level: AccessibilityLevel = AccessibilityLevel.AA) -> AccessibilityReport:
        """Validate theme for accessibility compliance.
        
        Args:
            theme: Theme to validate
            level: Target compliance level
            
        Returns:
            Accessibility validation report
        """
        return AccessibilityThemeValidator.validate_theme_accessibility(theme, level)
    
    def generate_accessible_alternatives(self, theme: Theme) -> List[Theme]:
        """Generate accessible alternatives for a theme.
        
        Args:
            theme: Base theme to create alternatives for
            
        Returns:
            List of accessible theme variants
        """
        alternatives = []
        
        # Generate high contrast variants
        for level in HighContrastLevel:
            try:
                hc_theme = HighContrastGenerator.generate_high_contrast_theme(theme, level)
                alternatives.append(hc_theme)
            except Exception as e:
                logger.error(f"Failed to generate {level.value} high contrast theme: {e}")
        
        return alternatives
    
    def _apply_high_contrast(self, enabled: bool, level: HighContrastLevel) -> bool:
        """Apply high contrast mode to current theme."""
        current_theme = self.theme_engine.get_current_theme()
        if not current_theme:
            return False
        
        if enabled:
            # Generate high contrast version
            if current_theme.name not in self._original_themes:
                self._original_themes[current_theme.name] = current_theme
            
            # Check if we already have this high contrast variant
            if (current_theme.name in self._high_contrast_themes and 
                level.value in self._high_contrast_themes[current_theme.name]):
                hc_theme = self._high_contrast_themes[current_theme.name][level.value]
            else:
                # Generate new high contrast theme
                hc_theme = HighContrastGenerator.generate_high_contrast_theme(current_theme, level)
                
                # Cache it
                if current_theme.name not in self._high_contrast_themes:
                    self._high_contrast_themes[current_theme.name] = {}
                self._high_contrast_themes[current_theme.name][level.value] = hc_theme
            
            # Apply high contrast theme
            return self.theme_engine.apply_theme(hc_theme)
        else:
            # Restore original theme
            if current_theme.name in self._original_themes:
                original_theme = self._original_themes[current_theme.name]
                return self.theme_engine.apply_theme(original_theme)
            
        return True
    
    def _apply_color_blindness_filter(self, filter_type: Optional[ColorBlindnessType]) -> bool:
        """Apply color blindness filter to current theme."""
        # This would typically modify the theme colors through the color blindness simulator
        # For now, this is a placeholder for the actual implementation
        
        if filter_type:
            logger.info(f"Applied color blindness filter: {filter_type.value}")
        else:
            logger.info("Removed color blindness filter")
        
        return True
    
    def _on_theme_changed(self, theme: Theme) -> None:
        """Handle theme change - reapply accessibility settings if needed."""
        if self._settings.high_contrast_enabled:
            self._apply_high_contrast(True, self._settings.high_contrast_level)
        
        if self._settings.color_blindness_filter:
            self._apply_color_blindness_filter(self._settings.color_blindness_filter)


# Accessibility utility functions
def get_wcag_contrast_requirement(text_size: TextSize, level: AccessibilityLevel) -> float:
    """Get WCAG contrast requirement for given context.
    
    Args:
        text_size: Size category of text
        level: Target accessibility level
        
    Returns:
        Required contrast ratio
    """
    try:
        return AccessibilityThemeValidator.WCAG_REQUIREMENTS[level][text_size]
    except KeyError:
        # Default to AA normal text
        return 4.5


def is_color_accessible(fg_color: str, bg_color: str, 
                       text_size: TextSize = TextSize.NORMAL,
                       level: AccessibilityLevel = AccessibilityLevel.AA) -> bool:
    """Check if color combination meets accessibility requirements.
    
    Args:
        fg_color: Foreground color
        bg_color: Background color
        text_size: Text size category
        level: Target accessibility level
        
    Returns:
        True if accessible, False otherwise
    """
    ratio = ColorAnalyzer.calculate_contrast_ratio(fg_color, bg_color)
    required_ratio = get_wcag_contrast_requirement(text_size, level)
    return ratio >= required_ratio


def suggest_accessible_color(fg_color: str, bg_color: str,
                           text_size: TextSize = TextSize.NORMAL,
                           level: AccessibilityLevel = AccessibilityLevel.AA) -> str:
    """Suggest an accessible version of a foreground color.
    
    Args:
        fg_color: Original foreground color
        bg_color: Background color
        text_size: Text size category
        level: Target accessibility level
        
    Returns:
        Accessible foreground color
    """
    required_ratio = get_wcag_contrast_requirement(text_size, level)
    return HighContrastGenerator._adjust_color_for_contrast(fg_color, bg_color, required_ratio)