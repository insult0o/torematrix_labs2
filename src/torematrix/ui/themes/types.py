"""Type definitions for the theme framework."""

from enum import Enum
from typing import Dict, Any, Union, List, Optional
from dataclasses import dataclass


class ThemeType(Enum):
    """Theme type categories."""
    LIGHT = "light"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"
    CUSTOM = "custom"


class ThemeFormat(Enum):
    """Supported theme file formats."""
    YAML = "yaml"
    JSON = "json" 
    TOML = "toml"


class ComponentType(Enum):
    """UI component types that can be themed."""
    MAIN_WINDOW = "main_window"
    MENU_BAR = "menu_bar"
    TOOLBAR = "toolbar"
    BUTTON = "button"
    DIALOG = "dialog"
    TREE_VIEW = "tree_view"
    TABLE_VIEW = "table_view"
    TEXT_EDIT = "text_edit"
    TAB_WIDGET = "tab_widget"
    PROGRESS_BAR = "progress_bar"
    STATUS_BAR = "status_bar"
    SPLITTER = "splitter"


@dataclass
class ThemeMetadata:
    """Theme metadata information."""
    name: str
    version: str
    description: str
    author: str
    category: ThemeType
    accessibility_compliant: bool = True
    high_contrast_available: bool = False
    requires_icons: bool = True
    

@dataclass 
class ColorDefinition:
    """Color definition with accessibility information."""
    value: str
    description: str = ""
    contrast_ratio: Optional[float] = None
    accessibility_level: str = "AA"  # AA, AAA
    

@dataclass
class TypographyDefinition:
    """Typography definition with scaling support."""
    font_family: str
    font_size: int
    font_weight: int = 400
    line_height: float = 1.4
    letter_spacing: float = 0.0
    

# Type aliases for better readability
ThemeData = Dict[str, Any]
ColorMap = Dict[str, Union[str, ColorDefinition]]
ComponentStyles = Dict[ComponentType, Dict[str, Any]]
VariableMap = Dict[str, str]