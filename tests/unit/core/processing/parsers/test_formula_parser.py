"""Tests for the mathematical formula parser."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from torematrix.core.processing.parsers.formula import FormulaParser, FormulaMetadata
from torematrix.core.processing.parsers.base import ParserResult
from torematrix.core.processing.parsers.types import ParserConfig, ElementType
from torematrix.core.processing.parsers.advanced.math_detector import FormulaType, FormulaStructure
from torematrix.core.processing.parsers.advanced.latex_converter import LaTeXResult


@pytest.fixture
def parser_config():
    """Create a test parser configuration."""
    return ParserConfig(
        parser_specific={
            'min_confidence': 0.7,
            'validate_latex': True,
            'enable_structure_analysis': True
        }
    )


@pytest.fixture
def formula_parser(parser_config):
    """Create a formula parser instance."""
    return FormulaParser(parser_config)


@pytest.fixture
def mock_element():
    """Create a mock UnifiedElement."""
    element = Mock()
    element.type = "Formula"
    element.text = "E = mc^2"
    element.metadata = {}
    return element


class TestFormulaParser:
    """Test cases for FormulaParser."""
    
    def test_capabilities(self, formula_parser):
        """Test parser capabilities."""
        capabilities = formula_parser.capabilities
        
        assert ElementType.FORMULA in capabilities.supported_types
        assert capabilities.supports_async is True
        assert capabilities.supports_validation is True
        assert "latex" in capabilities.supports_export_formats
        assert "mathml" in capabilities.supports_export_formats
        
    def test_can_parse_formula_element(self, formula_parser, mock_element):
        """Test parsing formula element type."""
        assert formula_parser.can_parse(mock_element) is True
        
    def test_can_parse_formula_category(self, formula_parser):
        """Test parsing formula category."""
        element = Mock()
        element.type = "Text"
        element.category = "formula"
        element.text = "x = y + z"
        
        assert formula_parser.can_parse(element) is True
        
    def test_can_parse_mathematical_text(self, formula_parser):
        """Test parsing mathematical text content."""
        element = Mock()
        element.type = "Text"
        element.text = "∫ f(x) dx = F(x) + C"
        
        with patch.object(formula_parser.math_detector, 'is_likely_mathematical', return_value=True):
            assert formula_parser.can_parse(element) is True
    
    def test_cannot_parse_non_formula(self, formula_parser):
        """Test rejecting non-formula elements."""
        element = Mock()
        element.type = "Text"
        element.text = "This is just regular text without math."
        
        with patch.object(formula_parser.math_detector, 'is_likely_mathematical', return_value=False):
            assert formula_parser.can_parse(element) is False
    
    @pytest.mark.asyncio
    async def test_parse_simple_equation(self, formula_parser, mock_element):
        """Test parsing a simple equation."""
        # Mock the dependencies
        with patch.object(formula_parser.math_detector, 'detect_type') as mock_detect_type, \
             patch.object(formula_parser.math_detector, 'analyze_structure') as mock_analyze_structure, \
             patch.object(formula_parser.latex_converter, 'convert') as mock_convert, \
             patch.object(formula_parser.latex_converter, 'validate') as mock_validate:
            
            # Setup mocks
            mock_detect_type.return_value = FormulaType.EQUATION
            
            mock_structure = FormulaStructure()
            mock_structure.variables = ['E', 'm', 'c']
            mock_structure.operators = ['=', '^']
            mock_structure.complexity_score = 0.3
            mock_analyze_structure.return_value = mock_structure
            
            mock_latex_result = LaTeXResult(
                latex="E = mc^2",
                confidence=0.9,
                original_text="E = mc^2",
                conversion_method="pattern_based",
                validation_passed=True
            )
            mock_convert.return_value = mock_latex_result
            mock_validate.return_value = (True, [])
            
            # Parse the element
            result = await formula_parser.parse(mock_element)
            
            # Verify result
            assert result.success is True
            assert result.data["formula_type"] == "equation"
            assert result.data["original_text"] == "E = mc^2"
            assert result.data["latex"] == "E = mc^2"
            assert "E" in result.data["variables"]
            assert "m" in result.data["variables"]
            assert "c" in result.data["variables"]
            assert result.metadata.confidence > 0.7
    
    @pytest.mark.asyncio
    async def test_parse_complex_formula(self, formula_parser):
        """Test parsing a complex mathematical formula."""
        element = Mock()
        element.type = "Formula"
        element.text = "∫₀^∞ e^(-x²) dx = √π/2"
        
        with patch.object(formula_parser.math_detector, 'detect_type') as mock_detect_type, \
             patch.object(formula_parser.math_detector, 'analyze_structure') as mock_analyze_structure, \
             patch.object(formula_parser.latex_converter, 'convert') as mock_convert, \
             patch.object(formula_parser.latex_converter, 'validate') as mock_validate:
            
            mock_detect_type.return_value = FormulaType.INTEGRAL
            
            mock_structure = FormulaStructure()
            mock_structure.variables = ['x']
            mock_structure.functions = ['exp']
            mock_structure.has_integrals = True
            mock_structure.complexity_score = 0.8
            mock_analyze_structure.return_value = mock_structure
            
            mock_latex_result = LaTeXResult(
                latex="\\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}",
                confidence=0.85,
                original_text=element.text,
                conversion_method="structure_based",
                validation_passed=True
            )
            mock_convert.return_value = mock_latex_result
            mock_validate.return_value = (True, [])
            
            result = await formula_parser.parse(element)
            
            assert result.success is True
            assert result.data["formula_type"] == "integral"
            assert result.data["complexity"] == 0.8
            assert result.data["structure"]["has_integrals"] is True
            assert "exp" in result.data["functions"]
    
    @pytest.mark.asyncio
    async def test_parse_with_validation_errors(self, formula_parser, mock_element):
        """Test parsing with LaTeX validation errors."""
        with patch.object(formula_parser.math_detector, 'detect_type') as mock_detect_type, \
             patch.object(formula_parser.math_detector, 'analyze_structure') as mock_analyze_structure, \
             patch.object(formula_parser.latex_converter, 'convert') as mock_convert, \
             patch.object(formula_parser.latex_converter, 'validate') as mock_validate:
            
            mock_detect_type.return_value = FormulaType.EXPRESSION
            mock_analyze_structure.return_value = FormulaStructure()
            
            mock_latex_result = LaTeXResult(
                latex="E = mc^{2",  # Missing closing brace
                confidence=0.6,
                original_text="E = mc^2",
                conversion_method="fallback",
                validation_passed=False
            )
            mock_convert.return_value = mock_latex_result
            mock_validate.return_value = (False, ["Unbalanced braces"])
            
            result = await formula_parser.parse(mock_element)
            
            assert result.success is True  # Still succeeds but with warnings
            assert len(result.validation_errors) > 0
            assert "Unbalanced braces" in result.validation_errors
            assert result.data["has_validation_errors"] is True
    
    @pytest.mark.asyncio
    async def test_parse_failure(self, formula_parser):
        """Test parsing failure handling."""
        element = Mock()
        element.text = None  # No text to parse
        
        result = await formula_parser.parse(element)
        
        assert result.success is False
        assert "No formula text found" in result.validation_errors[0]
    
    def test_validate_successful_result(self, formula_parser):
        """Test validation of successful parsing result."""
        result = ParserResult(
            success=True,
            data={
                "latex": "E = mc^2",
                "structure": {"components": ["E", "=", "m", "c", "^", "2"]},
                "formula_type": "equation"
            },
            metadata=Mock(confidence=0.8),
            validation_errors=[],
            extracted_content="E = mc^2",
            structured_data={}
        )
        
        errors = formula_parser.validate(result)
        assert len(errors) == 0
    
    def test_validate_failed_result(self, formula_parser):
        """Test validation of failed parsing result."""
        result = ParserResult(
            success=False,
            data={},
            metadata=Mock(confidence=0.0),
            validation_errors=["Parsing failed"],
            extracted_content="",
            structured_data={}
        )
        
        errors = formula_parser.validate(result)
        assert "Formula parsing failed" in errors
    
    def test_validate_missing_latex(self, formula_parser):
        """Test validation when LaTeX is missing."""
        result = ParserResult(
            success=True,
            data={
                "latex": None,
                "structure": {"components": []},
                "formula_type": "unknown"
            },
            metadata=Mock(confidence=0.8),
            validation_errors=[],
            extracted_content="",
            structured_data={}
        )
        
        errors = formula_parser.validate(result)
        assert "No LaTeX output generated" in errors
    
    def test_validate_low_confidence(self, formula_parser):
        """Test validation with low confidence."""
        result = ParserResult(
            success=True,
            data={
                "latex": "x = y",
                "structure": {"components": ["x", "=", "y"]},
                "formula_type": "equation"
            },
            metadata=Mock(confidence=0.5),  # Below threshold
            validation_errors=[],
            extracted_content="x = y",
            structured_data={}
        )
        
        errors = formula_parser.validate(result)
        assert any("below threshold" in error for error in errors)
    
    def test_extract_formula_text_from_element(self, formula_parser):
        """Test extracting formula text from various element sources."""
        # Test text attribute
        element = Mock()
        element.text = "  E = mc^2  "
        text = formula_parser._extract_formula_text(element)
        assert text == "E = mc^2"
        
        # Test content attribute
        element = Mock()
        element.text = None
        element.content = "F = ma"
        text = formula_parser._extract_formula_text(element)
        assert text == "F = ma"
        
        # Test metadata
        element = Mock()
        element.text = None
        element.content = None
        element.metadata = {"formula": "v = u + at"}
        text = formula_parser._extract_formula_text(element)
        assert text == "v = u + at"
    
    def test_generate_description(self, formula_parser):
        """Test generating human-readable descriptions."""
        structure = FormulaStructure()
        structure.variables = ["x", "y"]
        structure.functions = ["sin", "cos"]
        structure.complexity_score = 0.4
        structure.has_fractions = True
        
        description = formula_parser._generate_description(structure, FormulaType.EQUATION)
        
        assert "Mathematical equation" in description
        assert "variables x, y" in description
        assert "functions: sin, cos" in description
        assert "moderate complexity" in description
        assert "fractions" in description
    
    def test_create_formula_metadata(self, formula_parser):
        """Test creating formula metadata."""
        structure = FormulaStructure()
        structure.variables = ["x", "y", "z"]
        structure.operators = ["+", "-", "="]
        structure.functions = ["sin"]
        structure.complexity_score = 0.6
        structure.has_integrals = True
        
        latex_result = LaTeXResult(
            latex="\\sin(x) + y = z",
            confidence=0.9,
            original_text="sin(x) + y = z",
            conversion_method="direct"
        )
        
        metadata = formula_parser._create_formula_metadata(structure, FormulaType.EQUATION, latex_result)
        
        assert metadata.formula_type == "equation"
        assert metadata.variable_count == 3
        assert metadata.operator_count == 3
        assert metadata.function_count == 1
        assert metadata.has_integrals is True
        assert metadata.language_detected == "latex"
    
    def test_calculate_confidence(self, formula_parser):
        """Test confidence calculation."""
        structure = FormulaStructure()
        structure.complexity_score = 0.5
        
        latex_result = LaTeXResult(
            latex="E = mc^2",
            confidence=0.8,
            original_text="E = mc^2",
            conversion_method="pattern_based"
        )
        
        confidence = formula_parser._calculate_confidence(
            structure, latex_result, True, FormulaType.EQUATION
        )
        
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be reasonably high
    
    def test_get_priority(self, formula_parser):
        """Test parser priority calculation."""
        # High priority for explicit formula elements
        element = Mock()
        element.type = "Formula"
        element.text = "E = mc^2"
        
        with patch.object(formula_parser, 'can_parse', return_value=True):
            priority = formula_parser.get_priority(element)
            assert priority >= 80  # Base + explicit formula boost
        
        # Lower priority for LaTeX content
        element.type = "Text"
        element.text = "\\frac{a}{b}"
        
        with patch.object(formula_parser, 'can_parse', return_value=True):
            priority = formula_parser.get_priority(element)
            assert 50 <= priority < 80
        
        # No priority for non-parseable elements
        with patch.object(formula_parser, 'can_parse', return_value=False):
            priority = formula_parser.get_priority(element)
            assert priority == 0
    
    @pytest.mark.asyncio
    async def test_convert_to_mathml(self, formula_parser):
        """Test basic LaTeX to MathML conversion."""
        latex = "\\frac{a}{b}"
        mathml = formula_parser._convert_to_mathml(latex)
        
        assert mathml.startswith('<math xmlns="http://www.w3.org/1998/Math/MathML">')
        assert mathml.endswith('</math>')
        assert "mfrac" in mathml  # Should contain fraction markup
    
    def test_get_formula_statistics(self, formula_parser):
        """Test formula statistics generation."""
        # Create mock results
        results = []
        for i in range(5):
            result = ParserResult(
                success=True,
                data={
                    "formula_type": "equation" if i % 2 == 0 else "expression",
                    "complexity": 0.5 + (i * 0.1),
                    "latex_confidence": 0.8 + (i * 0.05)
                },
                metadata=Mock(confidence=0.7 + (i * 0.05)),
                validation_errors=[],
                extracted_content="",
                structured_data={}
            )
            results.append(result)
        
        stats = formula_parser.get_formula_statistics(results)
        
        assert stats["total_formulas"] == 5
        assert stats["successful_parses"] == 5
        assert stats["success_rate"] == 1.0
        assert "equation" in stats["formula_type_distribution"]
        assert "expression" in stats["formula_type_distribution"]
        assert stats["average_confidence"] > 0.7


@pytest.mark.integration
class TestFormulaParserIntegration:
    """Integration tests for FormulaParser with real dependencies."""
    
    @pytest.mark.asyncio
    async def test_real_formula_parsing(self):
        """Test parsing with real math detector and LaTeX converter."""
        parser = FormulaParser()
        
        element = Mock()
        element.type = "Formula"
        element.text = "x^2 + y^2 = r^2"
        
        result = await parser.parse(element)
        
        # Should succeed with real components
        assert result.success is True
        assert result.data["original_text"] == "x^2 + y^2 = r^2"
        assert result.data["latex"] is not None
        assert len(result.data["variables"]) > 0