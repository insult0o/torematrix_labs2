"""Advanced Qt StyleSheet generation from theme data.

This module provides sophisticated stylesheet generation with performance optimization,
component-based styling, and CSS-like preprocessing features for the theme framework.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Union, Callable
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import re

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QWidget, QApplication

from .base import Theme, ColorPalette, Typography
from .types import ComponentType, ThemeData
from .exceptions import ThemeError, ThemeValidationError

logger = logging.getLogger(__name__)


class StyleSheetTarget(Enum):
    """StyleSheet application targets."""
    APPLICATION = "application"
    WIDGET = "widget" 
    COMPONENT = "component"


@dataclass
class GenerationOptions:
    """Options for stylesheet generation."""
    minify: bool = False
    include_comments: bool = True
    optimize_selectors: bool = True
    merge_rules: bool = True
    validate_css: bool = True
    target: StyleSheetTarget = StyleSheetTarget.APPLICATION
    custom_variables: Dict[str, str] = field(default_factory=dict)


@dataclass 
class GenerationMetrics:
    """Metrics for stylesheet generation performance."""
    generation_time: float = 0.0
    output_size: int = 0
    rules_count: int = 0
    selectors_count: int = 0
    variables_resolved: int = 0
    optimization_savings: int = 0
    cache_hit: bool = False


class ComponentStyleGenerator:
    """Base class for component-specific stylesheet generation."""
    
    def __init__(self, component_type: ComponentType):
        """Initialize component style generator.
        
        Args:
            component_type: Type of component this generator handles
        """
        self.component_type = component_type
        self._base_selectors: List[str] = []
        self._style_templates: Dict[str, str] = {}
        self._setup_component_styles()
    
    def _setup_component_styles(self) -> None:
        """Setup component-specific style templates."""
        # Override in subclasses for specific components
        pass
    
    def generate(self, theme: Theme, options: GenerationOptions) -> str:
        """Generate stylesheet for this component.
        
        Args:
            theme: Theme to generate styles from
            options: Generation options
            
        Returns:
            Generated CSS string for this component
        """
        raise NotImplementedError("Subclasses must implement generate()")
    
    def get_default_selectors(self) -> List[str]:
        """Get default Qt selectors for this component."""
        return self._base_selectors.copy()
    
    def validate_component_data(self, theme: Theme) -> bool:
        """Validate that theme has required data for this component."""
        return theme.has_component_styles(self.component_type)


class MainWindowStyleGenerator(ComponentStyleGenerator):
    """StyleSheet generator for main window components."""
    
    def _setup_component_styles(self) -> None:
        """Setup main window style templates."""
        self._base_selectors = [
            "QMainWindow",
            "QMainWindow::separator",
            "QMainWindow > QWidget"
        ]
        
        self._style_templates = {
            'main': """
                QMainWindow {{
                    background-color: {background};
                    color: {text_primary};
                    border: none;
                }}
            """,
            'separator': """
                QMainWindow::separator {{
                    background-color: {border};
                    width: 2px;
                    height: 2px;
                }}
                
                QMainWindow::separator:hover {{
                    background-color: {accent};
                }}
            """
        }
    
    def generate(self, theme: Theme, options: GenerationOptions) -> str:
        """Generate main window stylesheet."""
        if not self.validate_component_data(theme):
            return ""
        
        palette = theme.get_color_palette()
        if not palette:
            return ""
        
        styles = []
        
        # Main window background and basic styling
        styles.append(self._style_templates['main'].format(
            background=palette.get_color_value('background', '#ffffff'),
            text_primary=palette.get_color_value('text_primary', '#000000')
        ))
        
        # Separator styling
        styles.append(self._style_templates['separator'].format(
            border=palette.get_color_value('border', '#cccccc'),
            accent=palette.get_color_value('accent', '#007bff')
        ))
        
        return '\n'.join(styles)


class MenuBarStyleGenerator(ComponentStyleGenerator):
    """StyleSheet generator for menu bar components."""
    
    def _setup_component_styles(self) -> None:
        """Setup menu bar style templates."""
        self._base_selectors = [
            "QMenuBar",
            "QMenuBar::item",
            "QMenu",
            "QMenu::item"
        ]
        
        self._style_templates = {
            'menubar': """
                QMenuBar {{
                    background-color: {surface};
                    color: {text_primary};
                    border-bottom: 1px solid {border};
                    padding: 2px;
                }}
                
                QMenuBar::item {{
                    background-color: transparent;
                    padding: 6px 12px;
                    margin: 2px;
                    border-radius: 4px;
                }}
                
                QMenuBar::item:selected {{
                    background-color: {accent};
                    color: {text_on_accent};
                }}
                
                QMenuBar::item:pressed {{
                    background-color: {accent_dark};
                }}
            """,
            'menu': """
                QMenu {{
                    background-color: {surface};
                    color: {text_primary};
                    border: 1px solid {border};
                    border-radius: 6px;
                    padding: 4px;
                }}
                
                QMenu::item {{
                    background-color: transparent;
                    padding: 8px 16px;
                    margin: 1px;
                    border-radius: 4px;
                }}
                
                QMenu::item:selected {{
                    background-color: {accent};
                    color: {text_on_accent};
                }}
                
                QMenu::separator {{
                    height: 1px;
                    background-color: {border};
                    margin: 4px 8px;
                }}
            """
        }
    
    def generate(self, theme: Theme, options: GenerationOptions) -> str:
        """Generate menu bar stylesheet."""
        if not self.validate_component_data(theme):
            return ""
        
        palette = theme.get_color_palette()
        if not palette:
            return ""
        
        styles = []
        
        # Menu bar styling
        styles.append(self._style_templates['menubar'].format(
            surface=palette.get_color_value('surface', '#f5f5f5'),
            text_primary=palette.get_color_value('text_primary', '#000000'),
            border=palette.get_color_value('border', '#cccccc'),
            accent=palette.get_color_value('accent', '#007bff'),
            accent_dark=palette.get_color_value('accent_dark', '#0056b3'),
            text_on_accent='#ffffff'
        ))
        
        # Menu styling  
        styles.append(self._style_templates['menu'].format(
            surface=palette.get_color_value('surface', '#f5f5f5'),
            text_primary=palette.get_color_value('text_primary', '#000000'),
            border=palette.get_color_value('border', '#cccccc'),
            accent=palette.get_color_value('accent', '#007bff'),
            text_on_accent='#ffffff'
        ))
        
        return '\n'.join(styles)


class ButtonStyleGenerator(ComponentStyleGenerator):
    """StyleSheet generator for button components."""
    
    def _setup_component_styles(self) -> None:
        """Setup button style templates."""
        self._base_selectors = [
            "QPushButton",
            "QToolButton", 
            "QCommandLinkButton"
        ]
        
        self._style_templates = {
            'button': """
                QPushButton {{
                    background-color: {button_background};
                    color: {text_primary};
                    border: 1px solid {button_border};
                    border-radius: {border_radius}px;
                    padding: {padding_v}px {padding_h}px;
                    font-family: {font_family};
                    font-size: {font_size}px;
                    font-weight: {font_weight};
                    min-width: 80px;
                    min-height: 24px;
                }}
                
                QPushButton:hover {{
                    background-color: {button_hover};
                    border-color: {accent};
                }}
                
                QPushButton:pressed {{
                    background-color: {button_pressed};
                    border-color: {accent_dark};
                }}
                
                QPushButton:disabled {{
                    background-color: {button_disabled};
                    color: {text_disabled};
                    border-color: {border};
                }}
                
                QPushButton:default {{
                    background-color: {accent};
                    color: {text_on_accent};
                    border-color: {accent_dark};
                    font-weight: 600;
                }}
                
                QPushButton:default:hover {{
                    background-color: {accent_light};
                }}
                
                QPushButton:default:pressed {{
                    background-color: {accent_dark};
                }}
            """
        }
    
    def generate(self, theme: Theme, options: GenerationOptions) -> str:
        """Generate button stylesheet."""
        if not self.validate_component_data(theme):
            return ""
        
        palette = theme.get_color_palette()
        typography = theme.get_typography()
        
        if not palette:
            return ""
        
        # Get typography settings
        default_typo = typography.get_typography_definition('default') if typography else None
        font_family = default_typo.font_family if default_typo else 'Segoe UI'
        font_size = default_typo.font_size if default_typo else 12
        font_weight = default_typo.font_weight if default_typo else 400
        
        styles = []
        styles.append(self._style_templates['button'].format(
            button_background=palette.get_color_value('button_background', '#ffffff'),
            text_primary=palette.get_color_value('text_primary', '#000000'),
            button_border=palette.get_color_value('button_border', '#cccccc'),
            border_radius=theme.get_property('geometry.border_radius', 4),
            padding_v=6,
            padding_h=12,
            font_family=font_family,
            font_size=font_size,
            font_weight=font_weight,
            button_hover=palette.get_color_value('button_hover', '#f8f9fa'),
            accent=palette.get_color_value('accent', '#007bff'),
            button_pressed=palette.get_color_value('button_pressed', '#e9ecef'),
            accent_dark=palette.get_color_value('accent_dark', '#0056b3'),
            button_disabled=palette.get_color_value('button_disabled', '#f8f9fa'),
            text_disabled=palette.get_color_value('text_disabled', '#6c757d'),
            border=palette.get_color_value('border', '#dee2e6'),
            text_on_accent='#ffffff',
            accent_light=palette.get_color_value('accent_light', '#66b3ff')
        ))
        
        return '\n'.join(styles)


class StyleSheetGenerator(QObject):
    """Advanced Qt StyleSheet generation engine with performance optimization."""
    
    # Signals for generation events
    generation_started = pyqtSignal(str)  # theme_name
    generation_completed = pyqtSignal(str, float)  # theme_name, time_taken
    generation_error = pyqtSignal(str, str)  # theme_name, error_message
    
    def __init__(self, parent: Optional[QObject] = None):
        """Initialize stylesheet generator.
        
        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        
        # Component generators registry
        self._component_generators: Dict[ComponentType, ComponentStyleGenerator] = {}
        self._setup_component_generators()
        
        # Performance tracking
        self._generation_metrics: Dict[str, GenerationMetrics] = {}
        self._performance_targets = {
            'max_generation_time': 0.1,  # 100ms
            'max_output_size': 50000,    # 50KB
            'min_cache_hit_ratio': 0.85  # 85%
        }
        
        # CSS optimization patterns
        self._optimization_patterns = {
            'duplicate_rules': re.compile(r'(\{[^}]+\})\s*\1+'),
            'empty_rules': re.compile(r'[^{]+\{\s*\}'),
            'extra_whitespace': re.compile(r'\s+'),
            'trailing_semicolons': re.compile(r';\s*}'),
        }
        
        logger.info("StyleSheetGenerator initialized")
    
    def _setup_component_generators(self) -> None:
        """Setup component-specific generators."""
        self._component_generators = {
            ComponentType.MAIN_WINDOW: MainWindowStyleGenerator(ComponentType.MAIN_WINDOW),
            ComponentType.MENU_BAR: MenuBarStyleGenerator(ComponentType.MENU_BAR), 
            ComponentType.BUTTON: ButtonStyleGenerator(ComponentType.BUTTON),
            # Additional generators will be added by Agent 4
        }
    
    def generate_stylesheet(
        self, 
        theme: Theme, 
        components: Optional[List[ComponentType]] = None,
        options: Optional[GenerationOptions] = None
    ) -> str:
        """Generate complete stylesheet from theme data.
        
        Args:
            theme: Theme to generate stylesheet from
            components: Specific components to generate (None for all)
            options: Generation options
            
        Returns:
            Generated Qt stylesheet string
            
        Raises:
            ThemeError: If generation fails
        """
        start_time = time.time()
        
        try:
            self.generation_started.emit(theme.name)
            
            # Setup options
            if options is None:
                options = GenerationOptions()
            
            # Initialize metrics
            metrics = GenerationMetrics()
            
            # Determine components to generate
            target_components = components or list(self._component_generators.keys())
            
            # Generate component stylesheets
            component_styles = []
            for component_type in target_components:
                if component_type in self._component_generators:
                    generator = self._component_generators[component_type]
                    try:
                        component_css = generator.generate(theme, options)
                        if component_css.strip():
                            if options.include_comments:
                                component_styles.append(f"/* {component_type.value.title()} Styles */")
                            component_styles.append(component_css)
                            metrics.rules_count += component_css.count('{')
                    except Exception as e:
                        logger.warning(f"Failed to generate styles for {component_type}: {e}")
            
            # Combine all styles
            combined_stylesheet = '\n\n'.join(component_styles)
            
            # Resolve theme variables
            resolved_stylesheet = self._resolve_variables(combined_stylesheet, theme, options)
            metrics.variables_resolved = combined_stylesheet.count('${') - resolved_stylesheet.count('${')
            
            # Apply optimizations
            if options.optimize_selectors or options.merge_rules or options.minify:
                optimized_stylesheet = self._optimize_stylesheet(resolved_stylesheet, options)
                metrics.optimization_savings = len(resolved_stylesheet) - len(optimized_stylesheet)
                final_stylesheet = optimized_stylesheet
            else:
                final_stylesheet = resolved_stylesheet
            
            # Validate if requested
            if options.validate_css:
                self._validate_stylesheet(final_stylesheet)
            
            # Update metrics
            generation_time = time.time() - start_time
            metrics.generation_time = generation_time
            metrics.output_size = len(final_stylesheet)
            metrics.selectors_count = final_stylesheet.count('{')
            
            # Store metrics
            self._generation_metrics[theme.name] = metrics
            
            # Check performance targets
            self._check_performance_targets(theme.name, metrics)
            
            # Emit completion signal
            self.generation_completed.emit(theme.name, generation_time)
            
            logger.debug(f"Generated stylesheet for '{theme.name}' in {generation_time:.3f}s "
                        f"({metrics.output_size} bytes, {metrics.rules_count} rules)")
            
            return final_stylesheet
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to generate stylesheet for '{theme.name}': {error_msg}")
            self.generation_error.emit(theme.name, error_msg)
            raise ThemeError(f"Stylesheet generation failed: {error_msg}", theme.name)
    
    def _resolve_variables(self, stylesheet: str, theme: Theme, options: GenerationOptions) -> str:
        """Resolve theme variable references in stylesheet.
        
        Args:
            stylesheet: CSS with variable references
            theme: Theme for variable resolution
            options: Generation options with custom variables
            
        Returns:
            CSS with resolved variables
        """
        def replace_variable(match):
            var_name = match.group(1)
            
            # Check custom variables first
            if var_name in options.custom_variables:
                return options.custom_variables[var_name]
            
            # Check theme properties
            var_value = theme.get_property(var_name)
            if var_value is not None:
                return str(var_value)
            
            # Return original if not found
            logger.warning(f"Unresolved variable: ${{{var_name}}}")
            return match.group(0)
        
        # Replace ${variable.path} patterns
        variable_pattern = re.compile(r'\$\{([^}]+)\}')
        return variable_pattern.sub(replace_variable, stylesheet)
    
    def _optimize_stylesheet(self, stylesheet: str, options: GenerationOptions) -> str:
        """Apply CSS optimizations to stylesheet.
        
        Args:
            stylesheet: CSS to optimize
            options: Optimization options
            
        Returns:
            Optimized CSS
        """
        optimized = stylesheet
        
        # Remove duplicate rules
        if options.merge_rules:
            optimized = self._optimization_patterns['duplicate_rules'].sub(r'\1', optimized)
        
        # Remove empty rules
        optimized = self._optimization_patterns['empty_rules'].sub('', optimized)
        
        # Minify if requested
        if options.minify:
            # Remove comments
            optimized = re.sub(r'/\*.*?\*/', '', optimized, flags=re.DOTALL)
            
            # Compress whitespace
            optimized = self._optimization_patterns['extra_whitespace'].sub(' ', optimized)
            
            # Remove trailing semicolons before closing braces
            optimized = self._optimization_patterns['trailing_semicolons'].sub('}', optimized)
            
            # Remove leading/trailing whitespace
            optimized = optimized.strip()
        
        return optimized
    
    def _validate_stylesheet(self, stylesheet: str) -> bool:
        """Validate generated stylesheet syntax.
        
        Args:
            stylesheet: CSS to validate
            
        Returns:
            True if valid
            
        Raises:
            ThemeValidationError: If validation fails
        """
        # Basic validation - check balanced braces
        open_braces = stylesheet.count('{')
        close_braces = stylesheet.count('}')
        
        if open_braces != close_braces:
            raise ThemeValidationError(f"Unbalanced braces: {open_braces} opening, {close_braces} closing")
        
        # Check for common CSS errors
        if ';;' in stylesheet:
            logger.warning("Double semicolons found in stylesheet")
        
        return True
    
    def _check_performance_targets(self, theme_name: str, metrics: GenerationMetrics) -> None:
        """Check if generation meets performance targets.
        
        Args:
            theme_name: Name of theme
            metrics: Generation metrics
        """
        if metrics.generation_time > self._performance_targets['max_generation_time']:
            logger.warning(f"Theme '{theme_name}' generation time ({metrics.generation_time:.3f}s) "
                          f"exceeds target ({self._performance_targets['max_generation_time']}s)")
        
        if metrics.output_size > self._performance_targets['max_output_size']:
            logger.warning(f"Theme '{theme_name}' output size ({metrics.output_size} bytes) "
                          f"exceeds target ({self._performance_targets['max_output_size']} bytes)")
    
    def compile_component_styles(self, theme: Theme, component: ComponentType, options: Optional[GenerationOptions] = None) -> str:
        """Generate stylesheet for specific component.
        
        Args:
            theme: Theme to generate from
            component: Component to generate styles for
            options: Generation options
            
        Returns:
            Component-specific stylesheet
        """
        if component not in self._component_generators:
            logger.warning(f"No generator available for component: {component}")
            return ""
        
        if options is None:
            options = GenerationOptions()
        
        generator = self._component_generators[component]
        return generator.generate(theme, options)
    
    def get_generation_metrics(self, theme_name: str) -> Optional[GenerationMetrics]:
        """Get generation metrics for theme.
        
        Args:
            theme_name: Name of theme
            
        Returns:
            Generation metrics or None if not found
        """
        return self._generation_metrics.get(theme_name)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get overall performance statistics."""
        if not self._generation_metrics:
            return {}
        
        all_metrics = list(self._generation_metrics.values())
        generation_times = [m.generation_time for m in all_metrics]
        output_sizes = [m.output_size for m in all_metrics]
        
        return {
            'themes_generated': len(all_metrics),
            'avg_generation_time': sum(generation_times) / len(generation_times),
            'max_generation_time': max(generation_times),
            'avg_output_size': sum(output_sizes) / len(output_sizes),
            'max_output_size': max(output_sizes),
            'total_optimization_savings': sum(m.optimization_savings for m in all_metrics),
            'performance_targets': self._performance_targets,
        }
    
    def register_component_generator(self, component_type: ComponentType, generator: ComponentStyleGenerator) -> None:
        """Register a custom component generator.
        
        Args:
            component_type: Type of component
            generator: Generator instance
        """
        self._component_generators[component_type] = generator
        logger.info(f"Registered generator for component: {component_type}")
    
    def clear_metrics(self) -> None:
        """Clear all generation metrics."""
        self._generation_metrics.clear()
        logger.debug("Generation metrics cleared")