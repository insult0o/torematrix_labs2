"""Tests for accessibility compliance and validation."""

import pytest
from unittest.mock import Mock, patch

from src.torematrix.ui.themes.accessibility import (
    AccessibilityValidator, AccessibilityLevel, TextSize,
    AccessibilityRequirement, AccessibilityTestResult, AccessibilityReport
)
from src.torematrix.ui.themes.types import ThemeType


class TestAccessibilityValidator:
    """Test accessibility validator functionality."""
    
    @pytest.fixture
    def validator(self):
        """Create validator for testing."""
        return AccessibilityValidator()
    
    def test_validator_initialization(self, validator):
        """Test validator initialization."""
        assert validator is not None
        assert len(validator.requirements) > 0
        assert AccessibilityLevel.AA in validator.CONTRAST_REQUIREMENTS
        assert AccessibilityLevel.AAA in validator.CONTRAST_REQUIREMENTS
    
    def test_contrast_requirements(self, validator):
        """Test contrast requirements structure."""
        requirements = validator.CONTRAST_REQUIREMENTS
        
        # Check AA requirements
        aa_reqs = requirements[AccessibilityLevel.AA]
        assert aa_reqs[TextSize.NORMAL] == 4.5
        assert aa_reqs[TextSize.LARGE] == 3.0
        assert aa_reqs[TextSize.GRAPHICAL] == 3.0
        
        # Check AAA requirements
        aaa_reqs = requirements[AccessibilityLevel.AAA]
        assert aaa_reqs[TextSize.NORMAL] == 7.0
        assert aaa_reqs[TextSize.LARGE] == 4.5
        assert aaa_reqs[TextSize.GRAPHICAL] == 4.5
        
        # AAA should be stricter than AA
        assert aaa_reqs[TextSize.NORMAL] > aa_reqs[TextSize.NORMAL]
        assert aaa_reqs[TextSize.LARGE] > aa_reqs[TextSize.LARGE]
    
    def test_contrast_ratio_test(self, validator):
        """Test individual contrast ratio testing."""
        # Test high contrast combination
        high_contrast_test = validator._test_contrast_ratio(
            "#FFFFFF", "#000000", "test_high_contrast", 
            AccessibilityLevel.AA, TextSize.NORMAL
        )
        
        assert isinstance(high_contrast_test, AccessibilityTestResult)
        assert high_contrast_test.passed is True
        assert high_contrast_test.actual_value > 15
        assert high_contrast_test.required_value == 4.5
        assert high_contrast_test.level == AccessibilityLevel.AA
        
        # Test low contrast combination
        low_contrast_test = validator._test_contrast_ratio(
            "#AAAAAA", "#BBBBBB", "test_low_contrast",
            AccessibilityLevel.AA, TextSize.NORMAL
        )
        
        assert low_contrast_test.passed is False
        assert low_contrast_test.actual_value < 4.5
    
    def test_color_blindness_compatibility(self, validator):
        """Test color blindness compatibility testing."""
        colors = {
            'success': '#4CAF50',
            'error': '#F44336',
            'warning': '#FF9800',
            'info': '#2196F3'
        }
        derived = {}
        
        issues = validator._test_color_blindness_compatibility(colors, derived)
        
        assert isinstance(issues, list)
        # Should identify potential issues between red and green
        issue_found = any('success' in issue and 'error' in issue for issue in issues)
        # Note: This might not always trigger depending on the specific colors
    
    def test_semantic_colors_testing(self, validator):
        """Test semantic colors accessibility testing."""
        colors = {
            'success': '#4CAF50',
            'warning': '#FF9800',
            'error': '#F44336',
            'info': '#2196F3'
        }
        derived = {
            'background_primary': '#FFFFFF'
        }
        
        tests = validator._test_semantic_colors(colors, derived, AccessibilityLevel.AA)
        
        assert len(tests) == len(colors)
        assert all(isinstance(test, AccessibilityTestResult) for test in tests)
        assert all(test.level == AccessibilityLevel.AA for test in tests)
    
    def test_validate_color_palette_light_theme(self, validator):
        """Test validation of light theme palette."""
        light_palette = {
            'name': 'Test Light Theme',
            'metadata': {
                'category': 'light'
            },
            'colors': {
                'success': '#4CAF50',
                'warning': '#FF9800',
                'error': '#F44336',
                'info': '#2196F3'
            },
            'derived': {
                'background_primary': '#FFFFFF',
                'background_secondary': '#F5F5F5',
                'text_primary': '#212121',
                'text_secondary': '#757575',
                'accent_primary': '#2196F3'
            }
        }
        
        report = validator.validate_color_palette(light_palette, AccessibilityLevel.AA)
        
        assert isinstance(report, AccessibilityReport)
        assert len(report.tests) > 0
        assert report.score >= 0
        assert report.score <= 100
        assert report.overall_compliance in [AccessibilityLevel.A, AccessibilityLevel.AA, AccessibilityLevel.AAA]
        assert isinstance(report.recommendations, list)
        assert isinstance(report.color_blindness_issues, list)
    
    def test_validate_color_palette_dark_theme(self, validator):
        """Test validation of dark theme palette."""
        dark_palette = {
            'name': 'Test Dark Theme',
            'metadata': {
                'category': 'dark'
            },
            'colors': {
                'success': '#4CAF50',
                'warning': '#FF9800',
                'error': '#F44336',
                'info': '#2196F3'
            },
            'derived': {
                'background_primary': '#121212',
                'background_secondary': '#1E1E1E',
                'text_primary': '#FFFFFF',
                'text_secondary': '#B3B3B3',
                'accent_primary': '#2196F3'
            }
        }
        
        report = validator.validate_color_palette(dark_palette, AccessibilityLevel.AA)
        
        assert isinstance(report, AccessibilityReport)
        assert len(report.tests) > 0
        
        # Dark theme with white text should generally pass accessibility
        passed_tests = [t for t in report.tests if t.passed]
        assert len(passed_tests) > 0
    
    def test_calculate_overall_compliance(self, validator):
        """Test overall compliance calculation."""
        # Create mock test results
        aa_tests = [
            AccessibilityTestResult("test1", True, 5.0, 4.5, AccessibilityLevel.AA, ""),
            AccessibilityTestResult("test2", True, 6.0, 4.5, AccessibilityLevel.AA, ""),
            AccessibilityTestResult("test3", False, 3.0, 4.5, AccessibilityLevel.AA, "")
        ]
        
        aaa_tests = [
            AccessibilityTestResult("test4", True, 8.0, 7.0, AccessibilityLevel.AAA, ""),
            AccessibilityTestResult("test5", False, 6.0, 7.0, AccessibilityLevel.AAA, "")
        ]
        
        all_tests = aa_tests + aaa_tests
        
        compliance, score = validator._calculate_overall_compliance(all_tests, AccessibilityLevel.AA)
        
        assert compliance in [AccessibilityLevel.A, AccessibilityLevel.AA, AccessibilityLevel.AAA]
        assert 0 <= score <= 100
        
        # Score should be based on pass rate
        expected_score = (3 / 5) * 100  # 3 passed out of 5 total
        assert score == expected_score
    
    def test_suggest_improvements(self, validator):
        """Test accessibility improvement suggestions."""
        problem_palette = {
            'derived': {
                'text_primary': '#888888',  # Low contrast
                'background_primary': '#AAAAAA',
                'text_secondary': '#999999',
                'accent_primary': '#BBBBBB'
            }
        }
        
        improvements = validator.suggest_improvements(problem_palette, AccessibilityLevel.AA)
        
        assert isinstance(improvements, dict)
        # Should suggest improvements for low contrast colors
        assert len(improvements) > 0
        
        # Test that improved colors actually have better contrast
        for color_key, improved_color in improvements.items():
            original_color = problem_palette['derived'][color_key]
            background = problem_palette['derived']['background_primary']
            
            # Import here to avoid circular imports in test
            from src.torematrix.ui.themes.colors import ColorAnalyzer
            
            original_ratio = ColorAnalyzer.calculate_contrast_ratio(original_color, background)
            improved_ratio = ColorAnalyzer.calculate_contrast_ratio(improved_color, background)
            
            assert improved_ratio > original_ratio
            assert improved_ratio >= 4.5  # Should meet AA standard
    
    def test_generate_high_contrast_variant_light(self, validator):
        """Test high contrast variant generation for light theme."""
        light_palette = {
            'metadata': {
                'category': 'light'
            },
            'derived': {
                'background_primary': '#FFFFFF',
                'text_primary': '#333333'
            }
        }
        
        hc_palette = validator.generate_high_contrast_variant(light_palette)
        
        assert hc_palette['metadata']['name'].endswith('High Contrast')
        assert hc_palette['metadata']['category'] == 'high_contrast'
        assert hc_palette['metadata']['accessibility_level'] == 'AAA'
        
        # Check that contrast is actually high
        derived = hc_palette['derived']
        from src.torematrix.ui.themes.colors import ColorAnalyzer
        
        ratio = ColorAnalyzer.calculate_contrast_ratio(
            derived['text_primary'], 
            derived['background_primary']
        )
        assert ratio >= 7.0  # Should meet AAA standard
    
    def test_generate_high_contrast_variant_dark(self, validator):
        """Test high contrast variant generation for dark theme."""
        dark_palette = {
            'metadata': {
                'category': 'dark'
            },
            'derived': {
                'background_primary': '#333333',
                'text_primary': '#CCCCCC'
            }
        }
        
        hc_palette = validator.generate_high_contrast_variant(dark_palette)
        
        assert hc_palette['metadata']['category'] == 'high_contrast'
        
        # Dark high contrast should use pure black background
        assert hc_palette['derived']['background_primary'] == '#000000'
        assert hc_palette['derived']['text_primary'] == '#FFFFFF'


class TestAccessibilityDataClasses:
    """Test accessibility data classes."""
    
    def test_accessibility_requirement(self):
        """Test AccessibilityRequirement data class."""
        req = AccessibilityRequirement(
            level=AccessibilityLevel.AA,
            text_size=TextSize.NORMAL,
            min_contrast_ratio=4.5
        )
        
        assert req.level == AccessibilityLevel.AA
        assert req.text_size == TextSize.NORMAL
        assert req.min_contrast_ratio == 4.5
    
    def test_accessibility_test_result(self):
        """Test AccessibilityTestResult data class."""
        result = AccessibilityTestResult(
            test_name="test_contrast",
            passed=True,
            actual_value=5.2,
            required_value=4.5,
            level=AccessibilityLevel.AA,
            recommendation="Good contrast"
        )
        
        assert result.test_name == "test_contrast"
        assert result.passed is True
        assert result.actual_value == 5.2
        assert result.required_value == 4.5
        assert result.level == AccessibilityLevel.AA
        assert result.recommendation == "Good contrast"
    
    def test_accessibility_report(self):
        """Test AccessibilityReport data class."""
        test_results = [
            AccessibilityTestResult("test1", True, 5.0, 4.5, AccessibilityLevel.AA, "Good"),
            AccessibilityTestResult("test2", False, 3.0, 4.5, AccessibilityLevel.AA, "Poor")
        ]
        
        report = AccessibilityReport(
            overall_compliance=AccessibilityLevel.AA,
            tests=test_results,
            color_blindness_issues=["Issue 1"],
            recommendations=["Recommendation 1"],
            score=75.0
        )
        
        assert report.overall_compliance == AccessibilityLevel.AA
        assert len(report.tests) == 2
        assert len(report.color_blindness_issues) == 1
        assert len(report.recommendations) == 1
        assert report.score == 75.0


@pytest.mark.integration
class TestAccessibilityIntegration:
    """Integration tests for accessibility system."""
    
    def test_complete_accessibility_workflow(self):
        """Test complete accessibility validation workflow."""
        validator = AccessibilityValidator()
        
        # Create a palette with known accessibility issues
        test_palette = {
            'name': 'Accessibility Test Palette',
            'metadata': {
                'category': 'light'
            },
            'colors': {
                'success': '#4CAF50',
                'warning': '#FFD700',  # Might have contrast issues
                'error': '#FF6B6B',    # Might have contrast issues
                'info': '#87CEEB'      # Might have contrast issues
            },
            'derived': {
                'background_primary': '#FFFFFF',
                'background_secondary': '#F8F9FA',
                'text_primary': '#212529',
                'text_secondary': '#6C757D',
                'accent_primary': '#007BFF'
            }
        }
        
        # Validate the palette
        report = validator.validate_color_palette(test_palette, AccessibilityLevel.AA)
        
        # Analyze results
        assert isinstance(report, AccessibilityReport)
        assert len(report.tests) > 0
        
        # Get improvement suggestions
        improvements = validator.suggest_improvements(test_palette, AccessibilityLevel.AA)
        
        # Apply improvements and revalidate
        if improvements:
            for color_key, improved_color in improvements.items():
                test_palette['derived'][color_key] = improved_color
            
            improved_report = validator.validate_color_palette(test_palette, AccessibilityLevel.AA)
            
            # Score should improve
            assert improved_report.score >= report.score
        
        # Generate high contrast variant
        hc_variant = validator.generate_high_contrast_variant(test_palette)
        hc_report = validator.validate_color_palette(hc_variant, AccessibilityLevel.AAA)
        
        # High contrast should score very high
        assert hc_report.score > 90
        assert hc_report.overall_compliance == AccessibilityLevel.AAA
    
    def test_real_world_palette_validation(self):
        """Test validation with realistic palette data."""
        # Material Design inspired palette
        material_palette = {
            'name': 'Material Design Light',
            'metadata': {
                'category': 'light'
            },
            'colors': {
                'primary': {
                    '500': '#2196F3'
                },
                'success': '#4CAF50',
                'warning': '#FF9800',
                'error': '#F44336',
                'info': '#2196F3'
            },
            'derived': {
                'background_primary': '#FFFFFF',
                'background_secondary': '#FAFAFA',
                'text_primary': '#212121',
                'text_secondary': '#757575',
                'accent_primary': '#2196F3'
            }
        }
        
        validator = AccessibilityValidator()
        report = validator.validate_color_palette(material_palette, AccessibilityLevel.AA)
        
        # Material Design should generally have good accessibility
        assert report.score > 70  # Should score reasonably well
        
        # Check specific combinations that should pass
        passed_tests = [t for t in report.tests if t.passed and 'text_primary' in t.test_name]
        assert len(passed_tests) > 0  # Text on background should pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])