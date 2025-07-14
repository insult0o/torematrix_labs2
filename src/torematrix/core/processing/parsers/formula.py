"""Mathematical formula parser with LaTeX conversion and structure analysis."""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import re

from torematrix_parser.src.torematrix.core.models.element import Element as UnifiedElement
from .base import BaseParser, ParserResult, ParserMetadata
from .types import ElementType, ParserCapabilities, ProcessingHints
from .advanced.math_detector import MathDetector, FormulaType, FormulaStructure, MathComponent
from .advanced.latex_converter import LaTeXConverter, LaTeXResult


@dataclass
class FormulaMetadata:
    """Metadata for mathematical formulas."""
    formula_type: str = "unknown"
    complexity_score: float = 0.0
    variable_count: int = 0
    operator_count: int = 0
    function_count: int = 0
    has_fractions: bool = False
    has_integrals: bool = False
    has_summations: bool = False
    has_matrices: bool = False
    nesting_level: int = 0
    language_detected: str = "mathematical"


class FormulaParser(BaseParser):
    """Advanced mathematical formula parser with LaTeX conversion."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.math_detector = MathDetector()
        self.latex_converter = LaTeXConverter()
        self.min_confidence = self.config.parser_specific.get('min_confidence', 0.7)
        self.validate_latex = self.config.parser_specific.get('validate_latex', True)
        self.enable_structure_analysis = self.config.parser_specific.get('enable_structure_analysis', True)
    
    @property
    def capabilities(self) -> ParserCapabilities:
        return ParserCapabilities(
            supported_types=[ElementType.FORMULA],
            supported_languages=["mathematical", "latex", "mathml"],
            max_element_size=10000,  # 10KB max formula size
            supports_batch=True,
            supports_async=True,
            supports_validation=True,
            supports_metadata_extraction=True,
            supports_structured_output=True,
            supports_export_formats=["latex", "mathml", "json", "text"],
            confidence_range=(0.0, 1.0)
        )
    
    def can_parse(self, element: UnifiedElement) -> bool:
        """Check if element contains mathematical formula."""
        # Check element type
        if hasattr(element, 'type') and element.type == "Formula":
            return True
        
        if hasattr(element, 'category') and element.category == "formula":
            return True
        
        # Check for mathematical content
        if hasattr(element, 'text') and element.text:
            return self.math_detector.is_likely_mathematical(element.text)
        
        return False
    
    async def parse(self, element: UnifiedElement, hints: Optional[ProcessingHints] = None) -> ParserResult:
        """Parse mathematical formula with LaTeX conversion and structure analysis."""
        try:
            # Extract formula text
            formula_text = self._extract_formula_text(element)
            if not formula_text:
                return self._create_failure_result("No formula text found")
            
            # Detect formula type and structure
            formula_type = self.math_detector.detect_type(formula_text)
            
            structure = None
            if self.enable_structure_analysis:
                structure = await self.math_detector.analyze_structure(formula_text)
            
            # Convert to LaTeX
            latex_result = await self.latex_converter.convert(formula_text, formula_type)
            
            # Validate LaTeX if enabled
            latex_valid = True
            validation_errors = []
            if self.validate_latex and latex_result.latex:
                latex_valid, validation_errors = self.latex_converter.validate(latex_result.latex)
            
            # Generate human-readable description
            description = self._generate_description(structure, formula_type)
            
            # Create formula metadata
            formula_metadata = self._create_formula_metadata(structure, formula_type, latex_result)
            
            # Calculate overall confidence
            confidence = self._calculate_confidence(structure, latex_result, latex_valid, formula_type)
            
            # Prepare export formats
            export_formats = self._create_export_formats(formula_text, latex_result, structure)
            
            return ParserResult(
                success=True,
                data={
                    "formula_type": formula_type.value,
                    "original_text": formula_text,
                    "latex": latex_result.latex,
                    "description": description,
                    "structure": structure.__dict__ if structure else None,
                    "complexity": structure.complexity_score if structure else 0.0,
                    "variables": structure.variables if structure else [],
                    "operators": structure.operators if structure else [],
                    "functions": structure.functions if structure else [],
                    "constants": structure.constants if structure else [],
                    "metadata": formula_metadata.__dict__,
                    "latex_confidence": latex_result.confidence,
                    "conversion_method": latex_result.conversion_method,
                    "has_validation_errors": not latex_valid
                },
                metadata=ParserMetadata(
                    confidence=confidence,
                    validation_score=0.9 if latex_valid else 0.5,
                    structure_quality=structure.complexity_score if structure else 0.0,
                    content_completeness=1.0 if formula_text else 0.0,
                    warnings=validation_errors if not latex_valid else [],
                    element_metadata=formula_metadata.__dict__
                ),
                validation_errors=validation_errors if not latex_valid else [],
                extracted_content=formula_text,
                structured_data={
                    "type": "formula",
                    "latex": latex_result.latex,
                    "structure": structure.__dict__ if structure else None,
                    "metadata": formula_metadata.__dict__
                },
                export_formats=export_formats
            )
            
        except Exception as e:
            self.logger.error(f"Formula parsing failed: {e}")
            return self._create_failure_result(
                f"Formula parsing failed: {str(e)}",
                validation_errors=[f"Formula analysis error: {str(e)}"]
            )
    
    def validate(self, result: ParserResult) -> List[str]:
        """Validate formula parsing result."""
        errors = []
        
        if not result.success:
            return ["Formula parsing failed"]
        
        # Validate LaTeX output
        latex = result.data.get("latex")
        if not latex:
            errors.append("No LaTeX output generated")
        elif self.validate_latex:
            latex_valid, latex_errors = self.latex_converter.validate(latex)
            if not latex_valid:
                errors.extend(latex_errors)
        
        # Validate structure if available
        structure_data = result.data.get("structure")
        if self.enable_structure_analysis and not structure_data:
            errors.append("No formula structure detected")
        elif structure_data:
            components = structure_data.get("components", [])
            if not components:
                errors.append("No mathematical components identified")
        
        # Validate confidence
        confidence = result.metadata.confidence
        if confidence < self.min_confidence:
            errors.append(f"Formula confidence {confidence:.2f} below threshold {self.min_confidence}")
        
        # Validate formula type
        formula_type = result.data.get("formula_type")
        if not formula_type or formula_type == "unknown":
            errors.append("Could not determine formula type")
        
        return errors
    
    def _extract_formula_text(self, element: UnifiedElement) -> Optional[str]:
        """Extract formula text from element."""
        # Try different text sources
        if hasattr(element, 'text') and element.text:
            return element.text.strip()
        
        if hasattr(element, 'content') and element.content:
            return element.content.strip()
        
        # Check metadata for formula content
        if hasattr(element, 'metadata') and element.metadata:
            for field in ['formula', 'equation', 'math', 'latex']:
                if field in element.metadata and element.metadata[field]:
                    return str(element.metadata[field]).strip()
        
        return None
    
    def _generate_description(self, structure: Optional[FormulaStructure], formula_type: FormulaType) -> str:
        """Generate human-readable description of formula."""
        parts = []
        
        # Add formula type
        type_descriptions = {
            FormulaType.EQUATION: "Mathematical equation",
            FormulaType.EXPRESSION: "Mathematical expression", 
            FormulaType.INTEGRAL: "Integral expression",
            FormulaType.FRACTION: "Fractional expression",
            FormulaType.MATRIX: "Matrix expression",
            FormulaType.SUMMATION: "Summation expression",
            FormulaType.INLINE: "Inline mathematical expression",
            FormulaType.DISPLAY: "Display mathematical expression"
        }
        
        parts.append(type_descriptions.get(formula_type, "Mathematical formula"))
        
        if not structure:
            return parts[0]
        
        # Add variable information
        if structure.variables:
            if len(structure.variables) == 1:
                parts.append(f"with variable {structure.variables[0]}")
            else:
                parts.append(f"with variables {', '.join(structure.variables)}")
        
        # Add function information
        if structure.functions:
            functions_str = ', '.join(structure.functions)
            parts.append(f"containing functions: {functions_str}")
        
        # Add complexity information
        complexity_desc = {
            (0.0, 0.3): "simple",
            (0.3, 0.7): "moderate",
            (0.7, 1.0): "complex"
        }
        
        for (min_val, max_val), desc in complexity_desc.items():
            if min_val <= structure.complexity_score < max_val:
                parts.append(f"({desc} complexity)")
                break
        
        # Add special features
        features = []
        if structure.has_fractions:
            features.append("fractions")
        if structure.has_integrals:
            features.append("integrals")
        if structure.has_summations:
            features.append("summations")
        if structure.has_matrices:
            features.append("matrices")
        
        if features:
            parts.append(f"with {', '.join(features)}")
        
        return "; ".join(parts)
    
    def _create_formula_metadata(self, structure: Optional[FormulaStructure], 
                                formula_type: FormulaType, latex_result: LaTeXResult) -> FormulaMetadata:
        """Create comprehensive formula metadata."""
        metadata = FormulaMetadata()
        
        metadata.formula_type = formula_type.value
        
        if structure:
            metadata.complexity_score = structure.complexity_score
            metadata.variable_count = len(structure.variables)
            metadata.operator_count = len(structure.operators)
            metadata.function_count = len(structure.functions)
            metadata.has_fractions = structure.has_fractions
            metadata.has_integrals = structure.has_integrals
            metadata.has_summations = structure.has_summations
            metadata.has_matrices = structure.has_matrices
            metadata.nesting_level = structure.nesting_level
        
        # Detect if it's LaTeX vs other mathematical notation
        if latex_result.conversion_method == "direct":
            metadata.language_detected = "latex"
        elif "unicode" in latex_result.conversion_method:
            metadata.language_detected = "unicode_math"
        else:
            metadata.language_detected = "mathematical"
        
        return metadata
    
    def _calculate_confidence(self, structure: Optional[FormulaStructure], latex_result: LaTeXResult,
                            latex_valid: bool, formula_type: FormulaType) -> float:
        """Calculate overall confidence in formula parsing."""
        confidence_factors = []
        
        # LaTeX conversion confidence (40%)
        confidence_factors.append(latex_result.confidence * 0.4)
        
        # Structure analysis confidence (30%)
        if structure:
            structure_confidence = min(1.0, structure.complexity_score + 0.3)
            confidence_factors.append(structure_confidence * 0.3)
        else:
            confidence_factors.append(0.3 * 0.3)  # Lower confidence without structure
        
        # LaTeX validation confidence (20%)
        validation_confidence = 1.0 if latex_valid else 0.5
        confidence_factors.append(validation_confidence * 0.2)
        
        # Formula type detection confidence (10%)
        type_confidence = 0.9 if formula_type != FormulaType.UNKNOWN else 0.3
        confidence_factors.append(type_confidence * 0.1)
        
        return sum(confidence_factors)
    
    def _create_export_formats(self, formula_text: str, latex_result: LaTeXResult,
                             structure: Optional[FormulaStructure]) -> Dict[str, Any]:
        """Create various export formats for the formula."""
        exports = {}
        
        # LaTeX format
        exports["latex"] = {
            "content": latex_result.latex,
            "confidence": latex_result.confidence,
            "method": latex_result.conversion_method
        }
        
        # Plain text format
        exports["text"] = {
            "content": formula_text,
            "encoding": "utf-8"
        }
        
        # JSON format with structure
        exports["json"] = {
            "formula_text": formula_text,
            "latex": latex_result.latex,
            "structure": structure.__dict__ if structure else None,
            "type": structure.components[0].type if structure and structure.components else "unknown"
        }
        
        # MathML format (basic conversion)
        exports["mathml"] = {
            "content": self._convert_to_mathml(latex_result.latex),
            "version": "3.0"
        }
        
        return exports
    
    def _convert_to_mathml(self, latex: str) -> str:
        """Basic LaTeX to MathML conversion."""
        # This is a simplified conversion - in practice you'd use a proper library
        mathml = f'<math xmlns="http://www.w3.org/1998/Math/MathML">'
        
        # Basic conversions
        content = latex
        content = re.sub(r'\\frac\{([^}]*)\}\{([^}]*)\}', r'<mfrac><mi>\1</mi><mi>\2</mi></mfrac>', content)
        content = re.sub(r'\\sqrt\{([^}]*)\}', r'<msqrt><mi>\1</mi></msqrt>', content)
        content = re.sub(r'([a-zA-Z])', r'<mi>\1</mi>', content)
        content = re.sub(r'(\d+)', r'<mn>\1</mn>', content)
        
        mathml += content + '</math>'
        return mathml
    
    def get_formula_statistics(self, results: List[ParserResult]) -> Dict[str, Any]:
        """Get statistics about formula parsing results."""
        if not results:
            return {}
        
        total_formulas = len(results)
        successful_parses = sum(1 for r in results if r.success)
        
        # Confidence statistics
        confidences = [r.metadata.confidence for r in results if r.success]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Formula type distribution
        formula_types = [r.data.get("formula_type", "unknown") for r in results if r.success]
        type_distribution = {}
        for formula_type in formula_types:
            type_distribution[formula_type] = type_distribution.get(formula_type, 0) + 1
        
        # Complexity distribution
        complexities = [r.data.get("complexity", 0) for r in results if r.success]
        avg_complexity = sum(complexities) / len(complexities) if complexities else 0
        
        # LaTeX conversion statistics
        latex_conversions = [r.data.get("latex_confidence", 0) for r in results if r.success]
        avg_latex_confidence = sum(latex_conversions) / len(latex_conversions) if latex_conversions else 0
        
        return {
            "total_formulas": total_formulas,
            "successful_parses": successful_parses,
            "success_rate": successful_parses / total_formulas,
            "average_confidence": avg_confidence,
            "average_complexity": avg_complexity,
            "formula_type_distribution": type_distribution,
            "latex_conversion_confidence": avg_latex_confidence,
            "validation_enabled": self.validate_latex,
            "structure_analysis_enabled": self.enable_structure_analysis
        }
    
    def get_priority(self, element: UnifiedElement) -> int:
        """Get parser priority for mathematical formulas."""
        if not self.can_parse(element):
            return 0
        
        priority = 50  # Base priority
        
        # Boost for explicit formula elements
        if hasattr(element, 'type') and element.type == "Formula":
            priority += 30
        
        # Boost for LaTeX content
        if hasattr(element, 'text') and element.text:
            text = element.text
            if '\\' in text and any(cmd in text for cmd in ['frac', 'sqrt', 'sum', 'int']):
                priority += 20
        
        # Boost for mathematical symbols
        if hasattr(element, 'text') and element.text:
            math_symbols = r'[∫∑∏√∇∂∞±∓×÷≤≥≠∈∉⊂⊃∪∩]'
            if re.search(math_symbols, element.text):
                priority += 15
        
        return priority