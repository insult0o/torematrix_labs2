"""Theme compilation and advanced CSS preprocessing.

This module provides sophisticated CSS preprocessing capabilities including variables,
mixins, functions, and advanced compilation features for the theme system.
"""

import logging
import re
import json
from typing import Dict, List, Optional, Any, Union, Callable, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import colorsys

from .base import Theme, ColorPalette
from .exceptions import ThemeError, ThemeValidationError

logger = logging.getLogger(__name__)


class PreprocessorFeature(Enum):
    """Available preprocessor features."""
    VARIABLES = "variables"
    MIXINS = "mixins"
    FUNCTIONS = "functions"
    CONDITIONALS = "conditionals"
    IMPORTS = "imports"
    NESTING = "nesting"


@dataclass
class CompilationOptions:
    """Options for theme compilation."""
    features: List[PreprocessorFeature] = field(default_factory=lambda: list(PreprocessorFeature))
    minify: bool = False
    source_map: bool = False
    strict_mode: bool = True
    custom_functions: Dict[str, Callable] = field(default_factory=dict)
    import_paths: List[Path] = field(default_factory=list)


@dataclass
class CompilationResult:
    """Result of theme compilation."""
    compiled_css: str
    source_map: Optional[str] = None
    variables_used: List[str] = field(default_factory=list)
    mixins_used: List[str] = field(default_factory=list)
    functions_called: List[str] = field(default_factory=list)
    compilation_time: float = 0.0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ColorFunctions:
    """Built-in color manipulation functions for CSS preprocessing."""
    
    @staticmethod
    def lighten(color: str, amount: Union[str, float]) -> str:
        """Lighten a color by a percentage.
        
        Args:
            color: Color in hex format (#rrggbb)
            amount: Amount to lighten (0-1 or percentage string)
            
        Returns:
            Lightened color in hex format
        """
        try:
            # Parse amount
            if isinstance(amount, str):
                amount = float(amount.rstrip('%')) / 100
            
            # Parse color
            if color.startswith('#'):
                color = color[1:]
            
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
            
            # Convert to HSL
            h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
            
            # Lighten
            l = min(1.0, l + amount)
            
            # Convert back to RGB
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            
            return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to lighten color '{color}': {e}")
            return color
    
    @staticmethod
    def darken(color: str, amount: Union[str, float]) -> str:
        """Darken a color by a percentage."""
        try:
            if isinstance(amount, str):
                amount = float(amount.rstrip('%')) / 100
            
            if color.startswith('#'):
                color = color[1:]
            
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
            h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
            
            # Darken
            l = max(0.0, l - amount)
            
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to darken color '{color}': {e}")
            return color
    
    @staticmethod
    def saturate(color: str, amount: Union[str, float]) -> str:
        """Saturate a color by a percentage."""
        try:
            if isinstance(amount, str):
                amount = float(amount.rstrip('%')) / 100
            
            if color.startswith('#'):
                color = color[1:]
            
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
            h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
            
            # Saturate
            s = min(1.0, s + amount)
            
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to saturate color '{color}': {e}")
            return color
    
    @staticmethod
    def desaturate(color: str, amount: Union[str, float]) -> str:
        """Desaturate a color by a percentage."""
        try:
            if isinstance(amount, str):
                amount = float(amount.rstrip('%')) / 100
            
            if color.startswith('#'):
                color = color[1:]
            
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
            h, l, s = colorsys.rgb_to_hls(r/255, g/255, b/255)
            
            # Desaturate
            s = max(0.0, s - amount)
            
            r, g, b = colorsys.hls_to_rgb(h, l, s)
            return f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to desaturate color '{color}': {e}")
            return color
    
    @staticmethod
    def rgba(color: str, alpha: Union[str, float]) -> str:
        """Convert hex color to rgba with alpha."""
        try:
            if isinstance(alpha, str):
                alpha = float(alpha)
            
            if color.startswith('#'):
                color = color[1:]
            
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
            return f"rgba({r}, {g}, {b}, {alpha})"
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to convert to rgba '{color}': {e}")
            return color
    
    @staticmethod
    def mix(color1: str, color2: str, weight: Union[str, float] = 0.5) -> str:
        """Mix two colors with specified weight."""
        try:
            if isinstance(weight, str):
                weight = float(weight.rstrip('%')) / 100
            
            # Parse colors
            if color1.startswith('#'):
                color1 = color1[1:]
            if color2.startswith('#'):
                color2 = color2[1:]
            
            r1, g1, b1 = int(color1[0:2], 16), int(color1[2:4], 16), int(color1[4:6], 16)
            r2, g2, b2 = int(color2[0:2], 16), int(color2[2:4], 16), int(color2[4:6], 16)
            
            # Mix colors
            r = int(r1 * (1 - weight) + r2 * weight)
            g = int(g1 * (1 - weight) + g2 * weight)
            b = int(b1 * (1 - weight) + b2 * weight)
            
            return f"#{r:02x}{g:02x}{b:02x}"
            
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to mix colors '{color1}' and '{color2}': {e}")
            return color1


class MathFunctions:
    """Built-in mathematical functions for CSS preprocessing."""
    
    @staticmethod
    def round_value(value: Union[str, float], precision: int = 0) -> str:
        """Round a numeric value."""
        try:
            if isinstance(value, str):
                # Extract numeric part
                numeric_match = re.match(r'([\d.]+)', value)
                if numeric_match:
                    numeric_part = float(numeric_match.group(1))
                    unit = value[len(numeric_match.group(1)):]
                    return f"{round(numeric_part, precision)}{unit}"
            else:
                return str(round(float(value), precision))
        except (ValueError, TypeError):
            return str(value)
    
    @staticmethod
    def min_value(*values: Union[str, float]) -> str:
        """Get minimum value from arguments."""
        try:
            numeric_values = []
            for val in values:
                if isinstance(val, str):
                    match = re.match(r'([\d.]+)', val)
                    if match:
                        numeric_values.append(float(match.group(1)))
                else:
                    numeric_values.append(float(val))
            
            if numeric_values:
                return str(min(numeric_values))
            return str(values[0]) if values else "0"
        except (ValueError, TypeError):
            return str(values[0]) if values else "0"
    
    @staticmethod
    def max_value(*values: Union[str, float]) -> str:
        """Get maximum value from arguments."""
        try:
            numeric_values = []
            for val in values:
                if isinstance(val, str):
                    match = re.match(r'([\d.]+)', val)
                    if match:
                        numeric_values.append(float(match.group(1)))
                else:
                    numeric_values.append(float(val))
            
            if numeric_values:
                return str(max(numeric_values))
            return str(values[0]) if values else "0"
        except (ValueError, TypeError):
            return str(values[0]) if values else "0"


class CSSPreprocessor:
    """Advanced CSS preprocessor with theme-aware features."""
    
    def __init__(self, theme: Theme, options: Optional[CompilationOptions] = None):
        """Initialize CSS preprocessor.
        
        Args:
            theme: Theme instance for variable resolution
            options: Compilation options
        """
        self.theme = theme
        self.options = options or CompilationOptions()
        
        # Built-in functions
        self.functions: Dict[str, Callable] = {
            # Color functions
            'lighten': ColorFunctions.lighten,
            'darken': ColorFunctions.darken,
            'saturate': ColorFunctions.saturate,
            'desaturate': ColorFunctions.desaturate,
            'rgba': ColorFunctions.rgba,
            'mix': ColorFunctions.mix,
            
            # Math functions
            'round': MathFunctions.round_value,
            'min': MathFunctions.min_value,
            'max': MathFunctions.max_value,
        }
        
        # Add custom functions
        self.functions.update(self.options.custom_functions)
        
        # Mixins storage
        self.mixins: Dict[str, str] = {}
        
        # Variables storage  
        self.variables: Dict[str, str] = {}
        self._load_theme_variables()
        
        # Compilation tracking
        self.result = CompilationResult(compiled_css="")
    
    def _load_theme_variables(self) -> None:
        """Load variables from theme."""
        # Load colors as variables
        palette = self.theme.get_color_palette()
        if palette:
            for color_name in palette.list_colors():
                self.variables[f"color-{color_name}"] = palette.get_color_value(color_name)
        
        # Load typography as variables
        typography = self.theme.get_typography()
        if typography:
            for typo_name in typography.list_typography():
                typo_def = typography.get_typography_definition(typo_name)
                if typo_def:
                    self.variables[f"font-{typo_name}-family"] = typo_def.font_family
                    self.variables[f"font-{typo_name}-size"] = f"{typo_def.font_size}px"
                    self.variables[f"font-{typo_name}-weight"] = str(typo_def.font_weight)
        
        # Load theme properties as variables
        self.variables.update(self.theme.get_property('variables', {}))
    
    def compile(self, css_input: str) -> CompilationResult:
        """Compile CSS with preprocessing features.
        
        Args:
            css_input: Input CSS with preprocessor syntax
            
        Returns:
            Compilation result with processed CSS
        """
        import time
        start_time = time.time()
        
        try:
            # Initialize result
            self.result = CompilationResult(compiled_css=css_input)
            
            processed_css = css_input
            
            # Apply preprocessing features in order
            if PreprocessorFeature.VARIABLES in self.options.features:
                processed_css = self.process_variables(processed_css)
            
            if PreprocessorFeature.MIXINS in self.options.features:
                processed_css = self.process_mixins(processed_css)
            
            if PreprocessorFeature.FUNCTIONS in self.options.features:
                processed_css = self.process_functions(processed_css)
            
            if PreprocessorFeature.CONDITIONALS in self.options.features:
                processed_css = self.process_conditionals(processed_css)
            
            if PreprocessorFeature.NESTING in self.options.features:
                processed_css = self.process_nesting(processed_css)
            
            if PreprocessorFeature.IMPORTS in self.options.features:
                processed_css = self.process_imports(processed_css)
            
            # Final optimization
            if self.options.minify:
                processed_css = self.minify_css(processed_css)
            
            # Update result
            self.result.compiled_css = processed_css
            self.result.compilation_time = time.time() - start_time
            
            logger.debug(f"CSS preprocessing completed in {self.result.compilation_time:.3f}s")
            return self.result
            
        except Exception as e:
            self.result.errors.append(str(e))
            logger.error(f"CSS preprocessing failed: {e}")
            raise ThemeError(f"CSS preprocessing failed: {e}")
    
    def process_variables(self, css: str) -> str:
        """Process variable declarations and references.
        
        Variables syntax:
        @var-name: value;
        color: @var-name;
        """
        # Extract variable declarations
        var_declarations = re.findall(r'@([\w-]+):\s*([^;]+);', css)
        for var_name, var_value in var_declarations:
            self.variables[var_name] = var_value.strip()
            self.result.variables_used.append(var_name)
        
        # Remove variable declarations from CSS
        css = re.sub(r'@[\w-]+:\s*[^;]+;', '', css)
        
        # Replace variable references
        def replace_var(match):
            var_name = match.group(1)
            if var_name in self.variables:
                return self.variables[var_name]
            else:
                self.result.warnings.append(f"Undefined variable: @{var_name}")
                return match.group(0)
        
        css = re.sub(r'@([\w-]+)', replace_var, css)
        
        return css
    
    def process_mixins(self, css: str) -> str:
        """Process mixin declarations and includes.
        
        Mixin syntax:
        @mixin mixin-name(param1, param2) {
            property: value;
        }
        
        @include mixin-name(arg1, arg2);
        """
        # Extract mixin declarations
        mixin_pattern = r'@mixin\s+([\w-]+)\s*(?:\(([^)]*)\))?\s*\{([^}]+)\}'
        mixin_matches = re.finditer(mixin_pattern, css, re.DOTALL)
        
        for match in mixin_matches:
            mixin_name = match.group(1)
            params = match.group(2) or ""
            body = match.group(3)
            
            self.mixins[mixin_name] = {
                'params': [p.strip() for p in params.split(',') if p.strip()],
                'body': body.strip()
            }
            self.result.mixins_used.append(mixin_name)
        
        # Remove mixin declarations
        css = re.sub(mixin_pattern, '', css, flags=re.DOTALL)
        
        # Process mixin includes
        def replace_include(match):
            mixin_name = match.group(1)
            args = match.group(2) or ""
            
            if mixin_name in self.mixins:
                mixin = self.mixins[mixin_name]
                mixin_body = mixin['body']
                
                # Replace parameters with arguments
                if args and mixin['params']:
                    arg_values = [a.strip() for a in args.split(',')]
                    for i, param in enumerate(mixin['params']):
                        if i < len(arg_values):
                            mixin_body = mixin_body.replace(f"${param}", arg_values[i])
                
                return mixin_body
            else:
                self.result.warnings.append(f"Undefined mixin: {mixin_name}")
                return ""
        
        include_pattern = r'@include\s+([\w-]+)\s*(?:\(([^)]*)\))?\s*;'
        css = re.sub(include_pattern, replace_include, css)
        
        return css
    
    def process_functions(self, css: str) -> str:
        """Process function calls in CSS values."""
        def replace_function(match):
            func_name = match.group(1)
            args_str = match.group(2)
            
            if func_name in self.functions:
                try:
                    # Parse arguments
                    args = []
                    if args_str:
                        # Simple argument parsing (could be enhanced)
                        args = [arg.strip().strip('"\'') for arg in args_str.split(',')]
                    
                    # Call function
                    result = self.functions[func_name](*args)
                    self.result.functions_called.append(func_name)
                    return str(result)
                    
                except Exception as e:
                    self.result.warnings.append(f"Function call failed: {func_name}({args_str}) - {e}")
                    return match.group(0)
            else:
                self.result.warnings.append(f"Unknown function: {func_name}")
                return match.group(0)
        
        # Match function calls: function_name(arg1, arg2, ...)
        function_pattern = r'([\w-]+)\(([^)]*)\)'
        css = re.sub(function_pattern, replace_function, css)
        
        return css
    
    def process_conditionals(self, css: str) -> str:
        """Process conditional statements.
        
        Conditional syntax:
        @if condition {
            // CSS rules
        } @else {
            // CSS rules  
        }
        """
        # Simple conditional processing
        # This is a basic implementation - could be enhanced significantly
        
        def evaluate_condition(condition: str) -> bool:
            """Evaluate a simple condition."""
            condition = condition.strip()
            
            # Check theme properties
            if condition.startswith('theme.'):
                property_path = condition[6:]  # Remove 'theme.'
                value = self.theme.get_property(property_path)
                return bool(value)
            
            # Check variable existence  
            if condition.startswith('@'):
                var_name = condition[1:]
                return var_name in self.variables
            
            # Default to false for unknown conditions
            return False
        
        # Process @if/@else blocks
        conditional_pattern = r'@if\s+([^{]+)\s*\{([^}]*)\}(?:\s*@else\s*\{([^}]*)\})?'
        
        def replace_conditional(match):
            condition = match.group(1)
            if_block = match.group(2)
            else_block = match.group(3) or ""
            
            if evaluate_condition(condition):
                return if_block
            else:
                return else_block
        
        css = re.sub(conditional_pattern, replace_conditional, css, flags=re.DOTALL)
        
        return css
    
    def process_nesting(self, css: str) -> str:
        """Process nested CSS rules (basic implementation)."""
        # This is a simplified nesting processor
        # A full implementation would need a proper CSS parser
        
        def expand_nested_rules(css_block: str, parent_selector: str = "") -> str:
            """Recursively expand nested rules."""
            result = []
            current_rule = ""
            brace_count = 0
            
            lines = css_block.split('\n')
            for line in lines:
                stripped = line.strip()
                
                if '{' in stripped:
                    brace_count += stripped.count('{')
                    if parent_selector and brace_count == 1:
                        # This is a nested rule
                        selector = stripped.split('{')[0].strip()
                        if selector.startswith('&'):
                            # Ampersand reference to parent
                            full_selector = selector.replace('&', parent_selector)
                        else:
                            # Descendant selector
                            full_selector = f"{parent_selector} {selector}"
                        
                        current_rule = full_selector + " {\n"
                    else:
                        current_rule += line + "\n"
                
                elif '}' in stripped:
                    brace_count -= stripped.count('}')
                    current_rule += line + "\n"
                    
                    if brace_count == 0 and current_rule.strip():
                        result.append(current_rule.strip())
                        current_rule = ""
                else:
                    current_rule += line + "\n"
            
            return '\n'.join(result)
        
        # Basic nesting expansion (simplified)
        return css  # For now, return as-is - full nesting would need proper parsing
    
    def process_imports(self, css: str) -> str:
        """Process @import statements."""
        import_pattern = r'@import\s+["\']([^"\']+)["\'];'
        
        def replace_import(match):
            import_path = match.group(1)
            
            # Look for file in import paths
            for base_path in self.options.import_paths:
                full_path = base_path / import_path
                if full_path.exists():
                    try:
                        with open(full_path, 'r', encoding='utf-8') as f:
                            imported_css = f.read()
                        
                        # Recursively process imported CSS
                        return self.compile(imported_css).compiled_css
                        
                    except Exception as e:
                        self.result.warnings.append(f"Failed to import '{import_path}': {e}")
                        return ""
            
            self.result.warnings.append(f"Import not found: {import_path}")
            return ""
        
        css = re.sub(import_pattern, replace_import, css)
        
        return css
    
    def minify_css(self, css: str) -> str:
        """Minify CSS by removing unnecessary whitespace and comments."""
        # Remove comments
        css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
        
        # Remove extra whitespace
        css = re.sub(r'\s+', ' ', css)
        
        # Remove spaces around certain characters
        css = re.sub(r'\s*([{}:;,>+~])\s*', r'\1', css)
        
        # Remove trailing semicolons
        css = re.sub(r';\s*}', '}', css)
        
        return css.strip()


class ThemeCompiler:
    """High-level theme compilation orchestrator."""
    
    def __init__(self):
        """Initialize theme compiler."""
        self.preprocessors: Dict[str, CSSPreprocessor] = {}
        self.compilation_cache: Dict[str, CompilationResult] = {}
        
    def compile_theme(
        self, 
        theme: Theme, 
        css_input: str, 
        options: Optional[CompilationOptions] = None
    ) -> CompilationResult:
        """Compile theme with preprocessing.
        
        Args:
            theme: Theme instance
            css_input: CSS input with preprocessor syntax
            options: Compilation options
            
        Returns:
            Compilation result
        """
        if options is None:
            options = CompilationOptions()
        
        # Create preprocessor for this theme
        preprocessor = CSSPreprocessor(theme, options)
        
        # Compile CSS
        result = preprocessor.compile(css_input)
        
        # Cache result
        cache_key = f"{theme.name}_{hash(css_input)}"
        self.compilation_cache[cache_key] = result
        
        return result
    
    def get_cached_result(self, theme_name: str, css_hash: int) -> Optional[CompilationResult]:
        """Get cached compilation result.
        
        Args:
            theme_name: Name of theme
            css_hash: Hash of CSS input
            
        Returns:
            Cached result or None
        """
        cache_key = f"{theme_name}_{css_hash}"
        return self.compilation_cache.get(cache_key)
    
    def clear_cache(self) -> None:
        """Clear compilation cache."""
        self.compilation_cache.clear()
        self.preprocessors.clear()
        logger.debug("Theme compilation cache cleared")