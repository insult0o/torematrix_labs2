"""Base classes for the theme framework."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import logging

from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import QWidget

from .types import (
    ThemeMetadata, ColorDefinition, TypographyDefinition, 
    ThemeData, ColorMap, ComponentStyles, ComponentType
)
from .exceptions import ThemeValidationError, ThemeError

logger = logging.getLogger(__name__)


class ColorPalette:
    """Color palette management with accessibility support."""
    
    def __init__(self, colors: ColorMap):
        """Initialize color palette.
        
        Args:
            colors: Dictionary mapping color names to color values or definitions
        """
        self._colors: Dict[str, ColorDefinition] = {}
        self._load_colors(colors)
        
    def _load_colors(self, colors: ColorMap) -> None:
        """Load colors into the palette."""
        for name, color_data in colors.items():
            if isinstance(color_data, str):
                # Simple color value
                self._colors[name] = ColorDefinition(value=color_data)
            elif isinstance(color_data, ColorDefinition):
                # Full color definition
                self._colors[name] = color_data
            elif isinstance(color_data, dict):
                # Dictionary format
                self._colors[name] = ColorDefinition(**color_data)
            else:
                raise ThemeValidationError(f"Invalid color format for '{name}'")
    
    def get_color(self, name: str, default: str = "#000000") -> QColor:
        """Get color by name as QColor object."""
        color_def = self._colors.get(name)
        if color_def:
            return QColor(color_def.value)
        return QColor(default)
    
    def get_color_value(self, name: str, default: str = "#000000") -> str:
        """Get color value as string."""
        color_def = self._colors.get(name)
        if color_def:
            return color_def.value
        return default
    
    def get_color_definition(self, name: str) -> Optional[ColorDefinition]:
        """Get full color definition."""
        return self._colors.get(name)
    
    def has_color(self, name: str) -> bool:
        """Check if color exists in palette."""
        return name in self._colors
    
    def list_colors(self) -> List[str]:
        """Get list of all color names."""
        return list(self._colors.keys())
    
    def validate_accessibility(self) -> Dict[str, bool]:
        """Validate color accessibility compliance."""
        results = {}
        for name, color_def in self._colors.items():
            # Simple validation based on contrast ratio
            if color_def.contrast_ratio is not None:
                results[name] = color_def.contrast_ratio >= 4.5  # WCAG AA
            else:
                results[name] = True  # Assume valid if not specified
        return results


class Typography:
    """Typography management with scaling support."""
    
    def __init__(self, typography_data: Dict[str, Union[TypographyDefinition, Dict[str, Any]]]):
        """Initialize typography system.
        
        Args:
            typography_data: Dictionary mapping typography names to definitions
        """
        self._typography: Dict[str, TypographyDefinition] = {}
        self._base_size: int = 12
        self._scale_factor: float = 1.0
        self._load_typography(typography_data)
    
    def _load_typography(self, typography_data: Dict[str, Union[TypographyDefinition, Dict[str, Any]]]) -> None:
        """Load typography definitions."""
        for name, typo_data in typography_data.items():
            if isinstance(typo_data, TypographyDefinition):
                self._typography[name] = typo_data
            elif isinstance(typo_data, dict):
                self._typography[name] = TypographyDefinition(**typo_data)
            else:
                raise ThemeValidationError(f"Invalid typography format for '{name}'")
    
    def get_font(self, name: str, scale_factor: Optional[float] = None) -> QFont:
        """Get font by name as QFont object."""
        typo_def = self._typography.get(name)
        if not typo_def:
            # Return default font
            return QFont()
        
        font = QFont(typo_def.font_family)
        
        # Apply scaling
        effective_scale = scale_factor or self._scale_factor
        scaled_size = int(typo_def.font_size * effective_scale)
        font.setPointSize(scaled_size)
        font.setWeight(typo_def.font_weight)
        
        return font
    
    def get_typography_definition(self, name: str) -> Optional[TypographyDefinition]:
        """Get typography definition."""
        return self._typography.get(name)
    
    def set_scale_factor(self, factor: float) -> None:
        """Set global scale factor for typography."""
        self._scale_factor = max(0.5, min(3.0, factor))  # Limit scale range
    
    def get_scale_factor(self) -> float:
        """Get current scale factor."""
        return self._scale_factor
    
    def list_typography(self) -> List[str]:
        """Get list of all typography names."""
        return list(self._typography.keys())


class Theme:
    """Base theme class with core properties and methods."""
    
    def __init__(self, name: str, metadata: ThemeMetadata, data: ThemeData):
        """Initialize theme.
        
        Args:
            name: Theme name
            metadata: Theme metadata
            data: Raw theme data dictionary
        """
        self.name = name
        self.metadata = metadata
        self._data = data
        
        # Initialize components
        self._color_palette: Optional[ColorPalette] = None
        self._typography: Optional[Typography] = None
        self._component_styles: ComponentStyles = {}
        self._variables: Dict[str, str] = {}
        
        # Load theme components
        self._load_theme_data()
        
    def _load_theme_data(self) -> None:
        """Load theme data into components."""
        try:
            # Load color palette
            if 'colors' in self._data:
                self._color_palette = ColorPalette(self._data['colors'])
            
            # Load typography
            if 'typography' in self._data:
                self._typography = Typography(self._data['typography'])
            
            # Load component styles
            if 'components' in self._data:
                self._load_component_styles(self._data['components'])
            
            # Load variables
            if 'variables' in self._data:
                self._variables = self._data['variables']
                
        except Exception as e:
            raise ThemeValidationError(f"Failed to load theme data: {e}", self.name)
    
    def _load_component_styles(self, components_data: Dict[str, Any]) -> None:
        """Load component-specific styles."""
        for component_name, styles in components_data.items():
            try:
                # Convert string to ComponentType enum
                component_type = ComponentType(component_name)
                self._component_styles[component_type] = styles
            except ValueError:
                logger.warning(f"Unknown component type: {component_name}")
    
    def get_property(self, path: str, default: Any = None) -> Any:
        """Get property value by path (e.g., 'colors.primary')."""
        parts = path.split('.')
        current = self._data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        
        return current
    
    def set_property(self, path: str, value: Any) -> None:
        """Set property value by path."""
        parts = path.split('.')
        current = self._data
        
        # Navigate to parent of target
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set final value
        current[parts[-1]] = value
    
    def generate_stylesheet(self) -> str:
        """Generate Qt stylesheet from theme data."""
        # This is a basic implementation
        # Agent 3 will provide the sophisticated stylesheet generation
        stylesheet_parts = []
        
        if self._color_palette:
            # Add basic color-based styles
            bg_color = self._color_palette.get_color_value('background', '#ffffff')
            text_color = self._color_palette.get_color_value('text_primary', '#000000')
            
            stylesheet_parts.append(f"""
                QMainWindow {{
                    background-color: {bg_color};
                    color: {text_color};
                }}
            """)
        
        return '\n'.join(stylesheet_parts)
    
    def get_color_palette(self) -> Optional[ColorPalette]:
        """Get color palette."""
        return self._color_palette
    
    def get_typography(self) -> Optional[Typography]:
        """Get typography system."""
        return self._typography
    
    def get_component_styles(self, component: ComponentType) -> Dict[str, Any]:
        """Get styles for specific component."""
        return self._component_styles.get(component, {})
    
    def has_component_styles(self, component: ComponentType) -> bool:
        """Check if theme has styles for component."""
        return component in self._component_styles
    
    def get_variable(self, name: str, default: str = "") -> str:
        """Get theme variable value."""
        return self._variables.get(name, default)
    
    def resolve_variables(self, text: str) -> str:
        """Resolve variable references in text (e.g., ${colors.primary})."""
        import re
        
        def replace_var(match):
            var_path = match.group(1)
            return str(self.get_property(var_path, match.group(0)))
        
        # Replace ${path.to.property} patterns
        return re.sub(r'\$\{([^}]+)\}', replace_var, text)


class ThemeProvider(ABC):
    """Abstract base class for theme providers."""
    
    @abstractmethod
    def load_theme(self, theme_name: str) -> Theme:
        """Load a theme by name.
        
        Args:
            theme_name: Name of theme to load
            
        Returns:
            Loaded theme instance
            
        Raises:
            ThemeNotFoundError: If theme is not found
            ThemeLoadError: If theme loading fails
        """
        pass
    
    @abstractmethod
    def get_available_themes(self) -> List[str]:
        """Get list of available theme names."""
        pass
    
    @abstractmethod
    def theme_exists(self, theme_name: str) -> bool:
        """Check if theme exists."""
        pass
    
    def get_theme_metadata(self, theme_name: str) -> Optional[ThemeMetadata]:
        """Get theme metadata without loading full theme."""
        # Default implementation loads full theme
        try:
            theme = self.load_theme(theme_name)
            return theme.metadata
        except Exception:
            return None