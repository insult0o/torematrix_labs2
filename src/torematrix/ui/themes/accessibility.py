"""Accessibility compliance tools and validation for themes."""

import logging
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

from .colors import ColorAnalyzer, ColorManipulator, ColorBlindnessType
from .types import ColorDefinition

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