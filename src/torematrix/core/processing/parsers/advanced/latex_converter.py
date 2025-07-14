"""LaTeX conversion for mathematical formulas with validation."""

import re
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum

from .math_detector import FormulaType, FormulaStructure, MathComponent


@dataclass
class LaTeXResult:
    """Result of LaTeX conversion."""
    latex: str
    confidence: float
    original_text: str
    conversion_method: str
    validation_passed: bool = False
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class ConversionMethod(Enum):
    """Methods used for LaTeX conversion."""
    DIRECT = "direct"  # Already in LaTeX format
    PATTERN_BASED = "pattern_based"  # Using regex patterns
    STRUCTURE_BASED = "structure_based"  # Using parsed structure
    FALLBACK = "fallback"  # Simple text conversion


class LaTeXConverter:
    """Advanced LaTeX converter for mathematical formulas."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("torematrix.parsers.latex_converter")
        
        # Symbol mappings for conversion
        self.unicode_to_latex = {
            # Greek letters
            'α': r'\alpha', 'β': r'\beta', 'γ': r'\gamma', 'δ': r'\delta',
            'ε': r'\epsilon', 'ζ': r'\zeta', 'η': r'\eta', 'θ': r'\theta',
            'ι': r'\iota', 'κ': r'\kappa', 'λ': r'\lambda', 'μ': r'\mu',
            'ν': r'\nu', 'ξ': r'\xi', 'ο': 'o', 'π': r'\pi',
            'ρ': r'\rho', 'σ': r'\sigma', 'τ': r'\tau', 'υ': r'\upsilon',
            'φ': r'\phi', 'χ': r'\chi', 'ψ': r'\psi', 'ω': r'\omega',
            
            # Capital Greek letters
            'Α': 'A', 'Β': 'B', 'Γ': r'\Gamma', 'Δ': r'\Delta',
            'Ε': 'E', 'Ζ': 'Z', 'Η': 'H', 'Θ': r'\Theta',
            'Ι': 'I', 'Κ': 'K', 'Λ': r'\Lambda', 'Μ': 'M',
            'Ν': 'N', 'Ξ': r'\Xi', 'Ο': 'O', 'Π': r'\Pi',
            'Ρ': 'P', 'Σ': r'\Sigma', 'Τ': 'T', 'Υ': r'\Upsilon',
            'Φ': r'\Phi', 'Χ': 'X', 'Ψ': r'\Psi', 'Ω': r'\Omega',
            
            # Mathematical symbols
            '∫': r'\int', '∑': r'\sum', '∏': r'\prod',
            '√': r'\sqrt', '∇': r'\nabla', '∂': r'\partial',
            '∞': r'\infty', '±': r'\pm', '∓': r'\mp',
            '×': r'\times', '÷': r'\div', '≤': r'\leq', '≥': r'\geq',
            '≠': r'\neq', '∈': r'\in', '∉': r'\notin',
            '⊂': r'\subset', '⊃': r'\supset', '⊆': r'\subseteq', '⊇': r'\supseteq',
            '∪': r'\cup', '∩': r'\cap', '∅': r'\emptyset',
            '→': r'\rightarrow', '←': r'\leftarrow', '↔': r'\leftrightarrow',
            '⇒': r'\Rightarrow', '⇐': r'\Leftarrow', '⇔': r'\Leftrightarrow',
            '∀': r'\forall', '∃': r'\exists', '∴': r'\therefore', '∵': r'\because',
            
            # Special characters
            '°': r'^\circ', '′': "'", '″': "''", '‴': "'''",
        }
        
        # Common conversion patterns
        self.conversion_patterns = [
            # Fractions
            (r'(\w+)/(\w+)', r'\\frac{\1}{\2}'),
            (r'(\d+)/(\d+)', r'\\frac{\1}{\2}'),
            (r'\(([^)]+)\)/\(([^)]+)\)', r'\\frac{\1}{\2}'),
            
            # Powers and subscripts
            (r'(\w+)\^(\w+)', r'\1^{\2}'),
            (r'(\w+)_(\w+)', r'\1_{\2}'),
            (r'(\w+)\^(\d+)', r'\1^{\2}'),
            (r'(\w+)_(\d+)', r'\1_{\2}'),
            
            # Square roots
            (r'sqrt\(([^)]+)\)', r'\\sqrt{\1}'),
            (r'√\(([^)]+)\)', r'\\sqrt{\1}'),
            (r'√(\w+)', r'\\sqrt{\1}'),
            
            # Trigonometric functions
            (r'\b(sin|cos|tan|cot|sec|csc)\s*\(', r'\\\1('),
            (r'\b(arcsin|arccos|arctan)\s*\(', r'\\\1('),
            
            # Logarithms
            (r'\blog\s*\(', r'\\log('),
            (r'\bln\s*\(', r'\\ln('),
            
            # Limits
            (r'\blim\s*', r'\\lim'),
            
            # Derivatives
            (r'd/dx', r'\\frac{d}{dx}'),
            (r'∂/∂(\w+)', r'\\frac{\\partial}{\\partial \1}'),
        ]

    async def convert(self, formula_text: str, formula_type: Optional[FormulaType] = None) -> LaTeXResult:
        """Convert mathematical formula to LaTeX format.
        
        Args:
            formula_text: Input mathematical formula
            formula_type: Optional hint about formula type
            
        Returns:
            LaTeXResult with converted LaTeX and metadata
        """
        if not formula_text:
            return LaTeXResult("", 0.0, formula_text, ConversionMethod.FALLBACK.value)
        
        original_text = formula_text.strip()
        
        # Check if already in LaTeX format
        if self._is_latex_format(original_text):
            return LaTeXResult(
                latex=self._clean_latex(original_text),
                confidence=0.95,
                original_text=original_text,
                conversion_method=ConversionMethod.DIRECT.value,
                validation_passed=True
            )
        
        # Try pattern-based conversion
        try:
            latex_result = await self._convert_with_patterns(original_text)
            if latex_result.confidence >= 0.7:
                return latex_result
        except Exception as e:
            self.logger.warning(f"Pattern-based conversion failed: {e}")
        
        # Try structure-based conversion
        try:
            from .math_detector import MathDetector
            detector = MathDetector()
            structure = await detector.analyze_structure(original_text)
            latex_result = await self._convert_with_structure(original_text, structure)
            if latex_result.confidence >= 0.6:
                return latex_result
        except Exception as e:
            self.logger.warning(f"Structure-based conversion failed: {e}")
        
        # Fallback to simple conversion
        return await self._fallback_conversion(original_text)

    def _is_latex_format(self, text: str) -> bool:
        """Check if text is already in LaTeX format."""
        latex_indicators = [
            r'\\[a-zA-Z]+',  # LaTeX commands
            r'\{.*?\}',      # Braces
            r'\$.*?\$',      # Math delimiters
            r'\\[\[\(].*?\\[\]\)]',  # Display math
        ]
        
        return any(re.search(pattern, text) for pattern in latex_indicators)

    def _clean_latex(self, latex_text: str) -> str:
        """Clean and normalize LaTeX text."""
        # Remove outer delimiters
        text = re.sub(r'^\$+|\$+$', '', latex_text)
        text = re.sub(r'^\\[\[\(]|\\[\]\)]$', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Ensure proper spacing around operators
        text = re.sub(r'([=+\-*/])', r' \1 ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    async def _convert_with_patterns(self, text: str) -> LaTeXResult:
        """Convert using regex patterns."""
        converted_text = text
        confidence = 0.8
        warnings = []
        
        # Convert Unicode symbols to LaTeX
        for unicode_char, latex_cmd in self.unicode_to_latex.items():
            if unicode_char in converted_text:
                converted_text = converted_text.replace(unicode_char, latex_cmd)
                confidence += 0.1
        
        # Apply conversion patterns
        for pattern, replacement in self.conversion_patterns:
            if re.search(pattern, converted_text):
                converted_text = re.sub(pattern, replacement, converted_text)
                confidence += 0.05
        
        # Post-processing
        converted_text = self._post_process_latex(converted_text)
        
        # Validate result
        validation_passed, validation_warnings = self.validate(converted_text)
        warnings.extend(validation_warnings)
        
        if not validation_passed:
            confidence *= 0.8
        
        return LaTeXResult(
            latex=converted_text,
            confidence=min(1.0, confidence),
            original_text=text,
            conversion_method=ConversionMethod.PATTERN_BASED.value,
            validation_passed=validation_passed,
            warnings=warnings
        )

    async def _convert_with_structure(self, text: str, structure: FormulaStructure) -> LaTeXResult:
        """Convert using parsed mathematical structure."""
        latex_parts = []
        confidence = 0.7
        warnings = []
        
        try:
            # Process components in order
            for component in structure.components:
                latex_part = await self._convert_component(component)
                latex_parts.append(latex_part)
                
                # Add subscripts and superscripts
                if component.subscript:
                    latex_parts.append(f"_{{{component.subscript}}}")
                if component.superscript:
                    latex_parts.append(f"^{{{component.superscript}}}")
            
            # Join parts
            latex_text = ''.join(latex_parts)
            
            # Apply structure-specific formatting
            if structure.has_fractions:
                confidence += 0.1
            if structure.has_integrals:
                confidence += 0.1
            if structure.has_summations:
                confidence += 0.1
            
            # Post-processing
            latex_text = self._post_process_latex(latex_text)
            
            # Validate result
            validation_passed, validation_warnings = self.validate(latex_text)
            warnings.extend(validation_warnings)
            
            if not validation_passed:
                confidence *= 0.8
            
            return LaTeXResult(
                latex=latex_text,
                confidence=min(1.0, confidence),
                original_text=text,
                conversion_method=ConversionMethod.STRUCTURE_BASED.value,
                validation_passed=validation_passed,
                warnings=warnings
            )
            
        except Exception as e:
            self.logger.error(f"Structure-based conversion failed: {e}")
            return await self._fallback_conversion(text)

    async def _convert_component(self, component: MathComponent) -> str:
        """Convert a single mathematical component to LaTeX."""
        value = component.value
        
        if component.type == 'function':
            # Mathematical functions
            if value in ['sin', 'cos', 'tan', 'log', 'ln', 'exp', 'lim', 'max', 'min']:
                return f'\\{value}'
            else:
                return value
        
        elif component.type == 'operator':
            # Convert operators
            if value in self.unicode_to_latex:
                return self.unicode_to_latex[value]
            else:
                return value
        
        elif component.type == 'variable':
            # Variables (usually italic in LaTeX)
            if len(value) == 1:
                return value  # Single letter variables
            else:
                return f'\\mathrm{{{value}}}'  # Multi-letter variables
        
        elif component.type == 'constant':
            # Constants (numbers, special constants)
            if value in ['e', 'π', 'i']:
                return f'\\{value}' if value != 'π' else '\\pi'
            else:
                return value
        
        elif component.type == 'delimiter':
            # Parentheses, brackets, etc.
            delimiter_map = {
                '(': '\\left(', ')': '\\right)',
                '[': '\\left[', ']': '\\right]',
                '{': '\\left\\{', '}': '\\right\\}',
                '|': '\\left|'
            }
            return delimiter_map.get(value, value)
        
        else:
            return value

    async def _fallback_conversion(self, text: str) -> LaTeXResult:
        """Fallback conversion for simple cases."""
        converted_text = text
        warnings = []
        
        # Convert basic Unicode symbols
        for unicode_char, latex_cmd in self.unicode_to_latex.items():
            if unicode_char in converted_text:
                converted_text = converted_text.replace(unicode_char, latex_cmd)
        
        # Simple pattern replacements
        simple_patterns = [
            (r'(\w+)\^(\w+)', r'\1^{\2}'),
            (r'(\w+)_(\w+)', r'\1_{\2}'),
            (r'sqrt\(([^)]+)\)', r'\\sqrt{\1}'),
        ]
        
        for pattern, replacement in simple_patterns:
            converted_text = re.sub(pattern, replacement, converted_text)
        
        # Validate result
        validation_passed, validation_warnings = self.validate(converted_text)
        warnings.extend(validation_warnings)
        
        return LaTeXResult(
            latex=converted_text,
            confidence=0.4,  # Low confidence for fallback
            original_text=text,
            conversion_method=ConversionMethod.FALLBACK.value,
            validation_passed=validation_passed,
            warnings=warnings
        )

    def _post_process_latex(self, latex_text: str) -> str:
        """Post-process LaTeX text for better formatting."""
        # Normalize spacing
        text = re.sub(r'\s+', ' ', latex_text).strip()
        
        # Fix common spacing issues
        text = re.sub(r'\s*([=+\-*/])\s*', r' \1 ', text)
        text = re.sub(r'\s*([{}])\s*', r'\1', text)
        
        # Fix fraction formatting
        text = re.sub(r'\\frac\s*\{\s*([^}]*)\s*\}\s*\{\s*([^}]*)\s*\}', r'\\frac{\1}{\2}', text)
        
        # Fix function calls
        text = re.sub(r'\\([a-zA-Z]+)\s+', r'\\\1 ', text)
        
        return text

    def validate(self, latex_text: str) -> Tuple[bool, List[str]]:
        """Validate LaTeX syntax.
        
        Args:
            latex_text: LaTeX code to validate
            
        Returns:
            Tuple of (is_valid, list_of_warnings)
        """
        warnings = []
        
        if not latex_text:
            return False, ["Empty LaTeX code"]
        
        # Check for balanced braces
        brace_count = latex_text.count('{') - latex_text.count('}')
        if brace_count != 0:
            warnings.append(f"Unbalanced braces: {abs(brace_count)} {'opening' if brace_count > 0 else 'closing'} braces")
        
        # Check for balanced parentheses
        paren_count = latex_text.count('(') - latex_text.count(')')
        if paren_count != 0:
            warnings.append(f"Unbalanced parentheses: {abs(paren_count)} {'opening' if paren_count > 0 else 'closing'} parentheses")
        
        # Check for valid LaTeX commands
        commands = re.findall(r'\\([a-zA-Z]+)', latex_text)
        valid_commands = {
            'frac', 'sqrt', 'sum', 'int', 'prod', 'lim', 'sin', 'cos', 'tan',
            'log', 'ln', 'exp', 'max', 'min', 'alpha', 'beta', 'gamma', 'delta',
            'epsilon', 'theta', 'lambda', 'mu', 'pi', 'sigma', 'phi', 'omega',
            'infty', 'partial', 'nabla', 'in', 'notin', 'subset', 'cup', 'cap',
            'times', 'div', 'pm', 'mp', 'leq', 'geq', 'neq', 'left', 'right',
            'mathrm', 'mathbf', 'mathit', 'text', 'begin', 'end'
        }
        
        for cmd in commands:
            if cmd not in valid_commands:
                warnings.append(f"Unknown LaTeX command: \\{cmd}")
        
        # Check for proper fraction syntax
        frac_matches = re.findall(r'\\frac\{([^}]*)\}\{([^}]*)\}', latex_text)
        for numerator, denominator in frac_matches:
            if not numerator.strip():
                warnings.append("Empty fraction numerator")
            if not denominator.strip():
                warnings.append("Empty fraction denominator")
        
        # Check for proper sqrt syntax
        sqrt_matches = re.findall(r'\\sqrt\{([^}]*)\}', latex_text)
        for content in sqrt_matches:
            if not content.strip():
                warnings.append("Empty square root")
        
        # Overall validation
        is_valid = len(warnings) == 0 or all('Unknown LaTeX command' not in w for w in warnings)
        
        return is_valid, warnings

    def get_conversion_statistics(self, results: List[LaTeXResult]) -> Dict[str, Any]:
        """Get statistics about conversion results.
        
        Args:
            results: List of LaTeXResult objects
            
        Returns:
            Dictionary with conversion statistics
        """
        if not results:
            return {}
        
        total_conversions = len(results)
        successful_conversions = sum(1 for r in results if r.validation_passed)
        
        confidence_scores = [r.confidence for r in results]
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        
        methods_used = {}
        for result in results:
            method = result.conversion_method
            methods_used[method] = methods_used.get(method, 0) + 1
        
        return {
            'total_conversions': total_conversions,
            'successful_conversions': successful_conversions,
            'success_rate': successful_conversions / total_conversions,
            'average_confidence': avg_confidence,
            'methods_used': methods_used,
            'common_warnings': self._get_common_warnings(results)
        }

    def _get_common_warnings(self, results: List[LaTeXResult]) -> Dict[str, int]:
        """Get common warnings from conversion results."""
        warning_counts = {}
        
        for result in results:
            for warning in result.warnings:
                warning_counts[warning] = warning_counts.get(warning, 0) + 1
        
        return dict(sorted(warning_counts.items(), key=lambda x: x[1], reverse=True))