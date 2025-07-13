"""Mathematical formula detection and structure analysis."""

import re
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum


class FormulaType(Enum):
    """Types of mathematical formulas."""
    INLINE = "inline"
    DISPLAY = "display"
    EQUATION = "equation"
    EXPRESSION = "expression"
    MATRIX = "matrix"
    INTEGRAL = "integral"
    FRACTION = "fraction"
    SUMMATION = "summation"
    UNKNOWN = "unknown"


@dataclass
class MathComponent:
    """Individual mathematical component."""
    type: str  # variable, operator, function, constant, delimiter
    value: str
    position: int
    confidence: float
    subscript: Optional[str] = None
    superscript: Optional[str] = None


@dataclass
class FormulaStructure:
    """Mathematical formula structure analysis."""
    components: List[MathComponent] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)
    operators: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    constants: List[str] = field(default_factory=list)
    complexity_score: float = 0.0
    nesting_level: int = 0
    has_fractions: bool = False
    has_integrals: bool = False
    has_summations: bool = False
    has_matrices: bool = False


class MathDetector:
    """Advanced mathematical formula detection and analysis."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("torematrix.parsers.math_detector")
        
        # Mathematical patterns
        self.math_patterns = {
            'fraction': [
                r'\\frac\{([^}]*)\}\{([^}]*)\}',
                r'(\w+)/(\w+)',
                r'(\d+)/(\d+)'
            ],
            'integral': [
                r'\\int(_\{[^}]*\})?(\^\{[^}]*\})?',
                r'∫(_[^∫]*)?(\^[^∫]*)?'
            ],
            'summation': [
                r'\\sum(_\{[^}]*\})?(\^\{[^}]*\})?',
                r'∑(_[^∑]*)?(\^[^∑]*)?'
            ],
            'matrix': [
                r'\\begin\{(matrix|pmatrix|bmatrix|vmatrix)\}.*?\\end\{\1\}',
                r'\[([^\]]*\n[^\]]*)*\]'
            ],
            'greek_letters': [
                r'\\(alpha|beta|gamma|delta|epsilon|zeta|eta|theta|iota|kappa|lambda|mu|nu|xi|omicron|pi|rho|sigma|tau|upsilon|phi|chi|psi|omega)',
                r'[αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ]'
            ],
            'operators': [
                r'[+\-*/=<>≤≥≠±∓×÷√∇∂∞∈∉⊂⊃∪∩]',
                r'\\(pm|mp|times|div|sqrt|nabla|partial|infty|in|notin|subset|supset|cup|cap)'
            ],
            'functions': [
                r'\\(sin|cos|tan|log|ln|exp|lim|max|min|sup|inf)',
                r'\b(sin|cos|tan|log|ln|exp|lim|max|min|sup|inf)\b'
            ]
        }
        
        # Mathematical symbols and their meanings
        self.symbol_meanings = {
            '∫': 'integral',
            '∑': 'summation',
            '∏': 'product',
            '√': 'square_root',
            '∇': 'nabla',
            '∂': 'partial_derivative',
            '∞': 'infinity',
            '±': 'plus_minus',
            '∓': 'minus_plus',
            '×': 'multiplication',
            '÷': 'division',
            '≤': 'less_equal',
            '≥': 'greater_equal',
            '≠': 'not_equal',
            '∈': 'element_of',
            '∉': 'not_element_of',
            '⊂': 'subset',
            '⊃': 'superset',
            '∪': 'union',
            '∩': 'intersection'
        }

    def detect_type(self, formula_text: str) -> FormulaType:
        """Detect the type of mathematical formula.
        
        Args:
            formula_text: Text containing mathematical formula
            
        Returns:
            FormulaType enum value
        """
        if not formula_text:
            return FormulaType.UNKNOWN
        
        text = formula_text.strip()
        
        # Check for specific formula types
        if any(re.search(pattern, text) for pattern in self.math_patterns['matrix']):
            return FormulaType.MATRIX
        
        if any(re.search(pattern, text) for pattern in self.math_patterns['integral']):
            return FormulaType.INTEGRAL
        
        if any(re.search(pattern, text) for pattern in self.math_patterns['summation']):
            return FormulaType.SUMMATION
        
        if any(re.search(pattern, text) for pattern in self.math_patterns['fraction']):
            return FormulaType.FRACTION
        
        # Check for equation vs expression
        if '=' in text:
            return FormulaType.EQUATION
        
        # Check for display vs inline based on delimiters
        if text.startswith('$$') and text.endswith('$$'):
            return FormulaType.DISPLAY
        elif text.startswith('$') and text.endswith('$'):
            return FormulaType.INLINE
        elif text.startswith('\\[') and text.endswith('\\]'):
            return FormulaType.DISPLAY
        elif text.startswith('\\(') and text.endswith('\\)'):
            return FormulaType.INLINE
        
        # Default to expression
        return FormulaType.EXPRESSION

    async def analyze_structure(self, formula_text: str) -> FormulaStructure:
        """Analyze the structure of a mathematical formula.
        
        Args:
            formula_text: Text containing mathematical formula
            
        Returns:
            FormulaStructure with detailed analysis
        """
        structure = FormulaStructure()
        
        if not formula_text:
            return structure
        
        # Clean the formula text
        text = self._clean_formula_text(formula_text)
        
        # Extract components
        structure.components = await self._extract_components(text)
        
        # Categorize components
        for component in structure.components:
            if component.type == 'variable':
                structure.variables.append(component.value)
            elif component.type == 'operator':
                structure.operators.append(component.value)
            elif component.type == 'function':
                structure.functions.append(component.value)
            elif component.type == 'constant':
                structure.constants.append(component.value)
        
        # Remove duplicates
        structure.variables = list(set(structure.variables))
        structure.operators = list(set(structure.operators))
        structure.functions = list(set(structure.functions))
        structure.constants = list(set(structure.constants))
        
        # Analyze formula properties
        structure.has_fractions = any(re.search(pattern, text) for pattern in self.math_patterns['fraction'])
        structure.has_integrals = any(re.search(pattern, text) for pattern in self.math_patterns['integral'])
        structure.has_summations = any(re.search(pattern, text) for pattern in self.math_patterns['summation'])
        structure.has_matrices = any(re.search(pattern, text) for pattern in self.math_patterns['matrix'])
        
        # Calculate nesting level and complexity
        structure.nesting_level = self._calculate_nesting_level(text)
        structure.complexity_score = self._calculate_complexity_score(structure, text)
        
        return structure

    def _clean_formula_text(self, text: str) -> str:
        """Clean formula text for analysis."""
        # Remove common delimiters
        text = re.sub(r'^\$+|\$+$', '', text)
        text = re.sub(r'^\\[\[\(]|\\[\]\)]$', '', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    async def _extract_components(self, text: str) -> List[MathComponent]:
        """Extract mathematical components from formula text."""
        components = []
        position = 0
        
        # Define component patterns
        patterns = [
            (r'\\(sin|cos|tan|log|ln|exp|lim|max|min|sup|inf)\b', 'function'),
            (r'\\frac\{([^}]*)\}\{([^}]*)\}', 'fraction'),
            (r'\\(sqrt|sum|int|prod)\b', 'function'),
            (r'\\[a-zA-Z]+', 'command'),
            (r'[a-zA-Z][a-zA-Z0-9]*', 'variable'),
            (r'\d+\.?\d*', 'constant'),
            (r'[+\-*/=<>≤≥≠±∓×÷√∇∂∞∈∉⊂⊃∪∩]', 'operator'),
            (r'[(){}[\]]', 'delimiter'),
            (r'[_^]', 'modifier'),
        ]
        
        i = 0
        while i < len(text):
            matched = False
            
            for pattern, component_type in patterns:
                match = re.match(pattern, text[i:])
                if match:
                    value = match.group(0)
                    
                    component = MathComponent(
                        type=component_type,
                        value=value,
                        position=i,
                        confidence=0.9  # High confidence for pattern matches
                    )
                    
                    # Check for subscripts and superscripts
                    if i + len(value) < len(text):
                        next_chars = text[i + len(value):i + len(value) + 10]
                        
                        # Check for subscript
                        sub_match = re.match(r'_\{([^}]*)\}', next_chars)
                        if sub_match:
                            component.subscript = sub_match.group(1)
                        
                        # Check for superscript
                        sup_match = re.match(r'\^\{([^}]*)\}', next_chars)
                        if sup_match:
                            component.superscript = sup_match.group(1)
                    
                    components.append(component)
                    i += len(value)
                    matched = True
                    break
            
            if not matched:
                i += 1
        
        return components

    def _calculate_nesting_level(self, text: str) -> int:
        """Calculate the maximum nesting level of parentheses/brackets."""
        max_level = 0
        current_level = 0
        
        for char in text:
            if char in '({[':
                current_level += 1
                max_level = max(max_level, current_level)
            elif char in ')}]':
                current_level = max(0, current_level - 1)
        
        return max_level

    def _calculate_complexity_score(self, structure: FormulaStructure, text: str) -> float:
        """Calculate complexity score for the formula."""
        score = 0.0
        
        # Base complexity from component count
        score += len(structure.components) * 0.1
        
        # Variable complexity
        score += len(structure.variables) * 0.15
        
        # Function complexity
        score += len(structure.functions) * 0.2
        
        # Operator complexity
        score += len(structure.operators) * 0.1
        
        # Special structures add complexity
        if structure.has_fractions:
            score += 0.3
        if structure.has_integrals:
            score += 0.4
        if structure.has_summations:
            score += 0.3
        if structure.has_matrices:
            score += 0.5
        
        # Nesting adds complexity
        score += structure.nesting_level * 0.2
        
        # Greek letters add complexity
        greek_count = len(re.findall(r'[αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ]', text))
        score += greek_count * 0.1
        
        # LaTeX commands add complexity
        latex_commands = len(re.findall(r'\\[a-zA-Z]+', text))
        score += latex_commands * 0.15
        
        # Normalize to 0-1 range
        return min(1.0, score)

    def detect_math_in_text(self, text: str) -> List[Dict[str, Any]]:
        """Detect mathematical expressions within plain text.
        
        Args:
            text: Text that may contain mathematical expressions
            
        Returns:
            List of detected mathematical expressions with positions
        """
        expressions = []
        
        # Common math delimiters
        delimiters = [
            (r'\$\$(.*?)\$\$', 'display'),
            (r'\$(.*?)\$', 'inline'),
            (r'\\[\[(.*?)\\]\]', 'display'),
            (r'\\[\((.*?)\\)\]', 'inline'),
        ]
        
        for pattern, math_type in delimiters:
            for match in re.finditer(pattern, text, re.DOTALL):
                expressions.append({
                    'content': match.group(1),
                    'type': math_type,
                    'start': match.start(),
                    'end': match.end(),
                    'confidence': 0.9
                })
        
        # Look for undelimited mathematical expressions
        math_indicators = [
            r'[a-zA-Z]\s*[=]\s*[^=]',  # Variable assignments
            r'\d+\s*[+\-*/]\s*\d+',   # Arithmetic
            r'[αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ]',  # Greek letters
            r'[∫∑∏√∇∂∞±∓×÷≤≥≠∈∉⊂⊃∪∩]',  # Mathematical symbols
        ]
        
        for pattern in math_indicators:
            for match in re.finditer(pattern, text):
                # Expand to get full expression
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 20)
                context = text[start:end]
                
                expressions.append({
                    'content': context.strip(),
                    'type': 'expression',
                    'start': start,
                    'end': end,
                    'confidence': 0.6  # Lower confidence for undelimited
                })
        
        return expressions

    def is_likely_mathematical(self, text: str) -> bool:
        """Check if text is likely to contain mathematical content.
        
        Args:
            text: Text to analyze
            
        Returns:
            True if text likely contains mathematics
        """
        if not text:
            return False
        
        # Check for mathematical symbols
        math_symbols = r'[=+\-*/^_∫∑∏√∇∂∞±∓×÷≤≥≠∈∉⊂⊃∪∩αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ]'
        if re.search(math_symbols, text):
            return True
        
        # Check for LaTeX commands
        if re.search(r'\\[a-zA-Z]+', text):
            return True
        
        # Check for math delimiters
        delimiters = [r'\$.*?\$', r'\\[\[(.*?)\\]\]', r'\\[\((.*?)\\)\]']
        if any(re.search(pattern, text) for pattern in delimiters):
            return True
        
        # Check for mathematical function names
        functions = r'\b(sin|cos|tan|log|ln|exp|lim|max|min|sup|inf)\b'
        if re.search(functions, text):
            return True
        
        return False

    def get_formula_statistics(self, structure: FormulaStructure) -> Dict[str, Any]:
        """Get statistical information about a formula structure.
        
        Args:
            structure: FormulaStructure to analyze
            
        Returns:
            Dictionary with statistical information
        """
        return {
            'total_components': len(structure.components),
            'variable_count': len(structure.variables),
            'operator_count': len(structure.operators),
            'function_count': len(structure.functions),
            'constant_count': len(structure.constants),
            'complexity_score': structure.complexity_score,
            'nesting_level': structure.nesting_level,
            'has_special_structures': {
                'fractions': structure.has_fractions,
                'integrals': structure.has_integrals,
                'summations': structure.has_summations,
                'matrices': structure.has_matrices
            },
            'variables': structure.variables,
            'operators': structure.operators,
            'functions': structure.functions
        }