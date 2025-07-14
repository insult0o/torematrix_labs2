"""Advanced SVG icon theming and colorization system.

Provides comprehensive icon theming capabilities including SVG colorization,
icon set management, and dynamic theme-based icon generation.
"""

import logging
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor
import threading

from PyQt6.QtCore import QObject, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtSvgWidgets import QSvgWidget

from .base import Theme
from .colors import ColorManipulator
from .cache import ThemeCache
from .types import ComponentType
from .exceptions import ThemeError

logger = logging.getLogger(__name__)


class IconStyle(Enum):
    """Icon style categories."""
    FILLED = "filled"
    OUTLINE = "outline" 
    TWO_TONE = "two_tone"
    SHARP = "sharp"
    ROUND = "round"


class IconState(Enum):
    """Icon state variations."""
    NORMAL = "normal"
    HOVER = "hover"
    PRESSED = "pressed"
    DISABLED = "disabled"
    SELECTED = "selected"
    FOCUSED = "focused"


class IconSize(Enum):
    """Standard icon sizes."""
    SMALL = 16
    MEDIUM = 24
    LARGE = 32
    EXTRA_LARGE = 48
    HUGE = 64


@dataclass
class IconColorScheme:
    """Color scheme for icon theming."""
    primary: str = "#000000"
    secondary: str = "#666666"
    accent: str = "#007bff"
    background: str = "#ffffff"
    disabled: str = "#cccccc"
    hover_primary: str = "#333333"
    hover_secondary: str = "#888888"
    pressed_primary: str = "#555555"
    selected_primary: str = "#ffffff"
    selected_background: str = "#007bff"


@dataclass
class IconDefinition:
    """Definition of an icon including metadata and variations."""
    name: str
    category: str
    description: str
    svg_path: str
    keywords: List[str]
    style: IconStyle
    variations: Dict[IconState, str]
    license: str = "MIT"
    author: str = "TORE Matrix Labs"


@dataclass
class IconSet:
    """Collection of related icons."""
    name: str
    description: str
    style: IconStyle
    icons: Dict[str, IconDefinition]
    license: str = "MIT"
    version: str = "1.0.0"


class SVGIconProcessor:
    """Advanced SVG icon processing and colorization."""
    
    def __init__(self):
        """Initialize SVG processor."""
        self._color_map_cache: Dict[str, Dict[str, str]] = {}
        
    def colorize_svg(self, svg_content: str, color_map: Dict[str, str]) -> str:
        """Replace colors in SVG content based on theme.
        
        Args:
            svg_content: Original SVG content
            color_map: Mapping of color names/values to new colors
            
        Returns:
            Modified SVG content with new colors
        """
        try:
            # Parse SVG
            root = ET.fromstring(svg_content)
            
            # Process all elements with color attributes
            self._process_element(root, color_map)
            
            # Convert back to string
            return ET.tostring(root, encoding='unicode')
            
        except ET.ParseError as e:
            logger.error(f"Failed to parse SVG: {e}")
            return svg_content
        except Exception as e:
            logger.error(f"Failed to colorize SVG: {e}")
            return svg_content
    
    def _process_element(self, element: ET.Element, color_map: Dict[str, str]) -> None:
        """Process an SVG element and its children."""
        # Color attributes to check
        color_attrs = ['fill', 'stroke', 'stop-color', 'flood-color']
        
        for attr in color_attrs:
            if attr in element.attrib:
                original_color = element.attrib[attr]
                new_color = self._map_color(original_color, color_map)
                if new_color:
                    element.attrib[attr] = new_color
        
        # Process style attribute
        if 'style' in element.attrib:
            element.attrib['style'] = self._process_style(element.attrib['style'], color_map)
        
        # Process children recursively
        for child in element:
            self._process_element(child, color_map)
    
    def _map_color(self, color: str, color_map: Dict[str, str]) -> Optional[str]:
        """Map a color to its theme equivalent."""
        color = color.strip().lower()
        
        # Skip 'none' and 'transparent'
        if color in ['none', 'transparent']:
            return None
            
        # Direct mapping
        if color in color_map:
            return color_map[color]
        
        # Check for hex colors
        if color.startswith('#'):
            return color_map.get(color, None)
        
        # Check for named colors
        for old_color, new_color in color_map.items():
            if old_color.lower() == color:
                return new_color
        
        # Check for semantic mappings
        semantic_mappings = {
            'black': 'primary',
            '#000000': 'primary',
            '#000': 'primary',
            'white': 'background',
            '#ffffff': 'background',
            '#fff': 'background',
            'gray': 'secondary',
            'grey': 'secondary',
        }
        
        semantic_color = semantic_mappings.get(color)
        if semantic_color and semantic_color in color_map:
            return color_map[semantic_color]
        
        return None
    
    def _process_style(self, style: str, color_map: Dict[str, str]) -> str:
        """Process inline style attribute."""
        # Split style into individual properties
        properties = [prop.strip() for prop in style.split(';') if prop.strip()]
        
        processed_props = []
        for prop in properties:
            if ':' in prop:
                name, value = prop.split(':', 1)
                name = name.strip()
                value = value.strip()
                
                # Check if this is a color property
                if name in ['fill', 'stroke', 'stop-color', 'flood-color']:
                    new_color = self._map_color(value, color_map)
                    if new_color:
                        value = new_color
                
                processed_props.append(f"{name}: {value}")
            else:
                processed_props.append(prop)
        
        return '; '.join(processed_props)
    
    def generate_icon_variants(self, svg_content: str, theme: Theme) -> Dict[str, str]:
        """Generate multiple icon variants for different states.
        
        Args:
            svg_content: Base SVG content
            theme: Theme to generate variants for
            
        Returns:
            Dictionary mapping state names to SVG content
        """
        variants = {}
        
        # Get theme colors
        colors = theme.colors
        
        # Normal state
        normal_map = {
            'primary': colors.get_color_value('icon_primary', '#000000'),
            'secondary': colors.get_color_value('icon_secondary', '#666666'),
            'background': colors.get_color_value('background', '#ffffff'),
        }
        variants[IconState.NORMAL.value] = self.colorize_svg(svg_content, normal_map)
        
        # Hover state
        hover_map = {
            'primary': colors.get_color_value('icon_hover', '#333333'),
            'secondary': colors.get_color_value('icon_secondary_hover', '#888888'),
            'background': colors.get_color_value('background', '#ffffff'),
        }
        variants[IconState.HOVER.value] = self.colorize_svg(svg_content, hover_map)
        
        # Pressed state
        pressed_map = {
            'primary': colors.get_color_value('icon_pressed', '#555555'),
            'secondary': colors.get_color_value('icon_secondary', '#666666'),
            'background': colors.get_color_value('background', '#ffffff'),
        }
        variants[IconState.PRESSED.value] = self.colorize_svg(svg_content, pressed_map)
        
        # Disabled state
        disabled_map = {
            'primary': colors.get_color_value('icon_disabled', '#cccccc'),
            'secondary': colors.get_color_value('icon_disabled', '#cccccc'),
            'background': colors.get_color_value('background', '#ffffff'),
        }
        variants[IconState.DISABLED.value] = self.colorize_svg(svg_content, disabled_map)
        
        # Selected state
        selected_map = {
            'primary': colors.get_color_value('icon_selected', '#ffffff'),
            'secondary': colors.get_color_value('icon_selected', '#ffffff'),
            'background': colors.get_color_value('accent', '#007bff'),
        }
        variants[IconState.SELECTED.value] = self.colorize_svg(svg_content, selected_map)
        
        return variants


class ThemedIconSet:
    """Themed version of an icon set."""
    
    def __init__(self, base_icon_set: IconSet, theme: Theme, color_scheme: IconColorScheme):
        """Initialize themed icon set.
        
        Args:
            base_icon_set: Base icon set to theme
            theme: Theme to apply
            color_scheme: Color scheme for theming
        """
        self.base_icon_set = base_icon_set
        self.theme = theme
        self.color_scheme = color_scheme
        self._themed_icons: Dict[str, Dict[str, QIcon]] = {}
        self._processor = SVGIconProcessor()
        
    def get_icon(self, icon_name: str, size: IconSize = IconSize.MEDIUM, 
                 state: IconState = IconState.NORMAL) -> Optional[QIcon]:
        """Get themed icon by name and specifications.
        
        Args:
            icon_name: Name of the icon
            size: Desired icon size
            state: Icon state (normal, hover, etc.)
            
        Returns:
            Themed QIcon or None if not found
        """
        if icon_name not in self.base_icon_set.icons:
            logger.warning(f"Icon '{icon_name}' not found in set '{self.base_icon_set.name}'")
            return None
        
        # Check cache
        cache_key = f"{icon_name}_{size.value}_{state.value}"
        if icon_name in self._themed_icons and cache_key in self._themed_icons[icon_name]:
            return self._themed_icons[icon_name][cache_key]
        
        # Generate themed icon
        icon_def = self.base_icon_set.icons[icon_name]
        themed_icon = self._create_themed_icon(icon_def, size, state)
        
        # Cache the result
        if icon_name not in self._themed_icons:
            self._themed_icons[icon_name] = {}
        self._themed_icons[icon_name][cache_key] = themed_icon
        
        return themed_icon
    
    def _create_themed_icon(self, icon_def: IconDefinition, size: IconSize, 
                           state: IconState) -> QIcon:
        """Create a themed icon from definition."""
        try:
            # Load SVG content
            svg_path = Path(icon_def.svg_path)
            if not svg_path.exists():
                logger.error(f"SVG file not found: {svg_path}")
                return self._create_fallback_icon(size)
            
            svg_content = svg_path.read_text(encoding='utf-8')
            
            # Create color mapping based on state
            color_map = self._create_color_map(state)
            
            # Generate themed SVG
            themed_svg = self._processor.colorize_svg(svg_content, color_map)
            
            # Create QIcon from themed SVG
            return self._svg_to_qicon(themed_svg, size)
            
        except Exception as e:
            logger.error(f"Failed to create themed icon for '{icon_def.name}': {e}")
            return self._create_fallback_icon(size)
    
    def _create_color_map(self, state: IconState) -> Dict[str, str]:
        """Create color mapping for the given state."""
        base_map = {
            'primary': self.color_scheme.primary,
            'secondary': self.color_scheme.secondary,
            'background': self.color_scheme.background,
            'accent': self.color_scheme.accent,
            'black': self.color_scheme.primary,
            '#000000': self.color_scheme.primary,
            '#000': self.color_scheme.primary,
            'white': self.color_scheme.background,
            '#ffffff': self.color_scheme.background,
            '#fff': self.color_scheme.background,
        }
        
        # Modify based on state
        if state == IconState.HOVER:
            base_map.update({
                'primary': self.color_scheme.hover_primary,
                'secondary': self.color_scheme.hover_secondary,
                'black': self.color_scheme.hover_primary,
                '#000000': self.color_scheme.hover_primary,
                '#000': self.color_scheme.hover_primary,
            })
        elif state == IconState.PRESSED:
            base_map.update({
                'primary': self.color_scheme.pressed_primary,
                'black': self.color_scheme.pressed_primary,
                '#000000': self.color_scheme.pressed_primary,
                '#000': self.color_scheme.pressed_primary,
            })
        elif state == IconState.DISABLED:
            base_map.update({
                'primary': self.color_scheme.disabled,
                'secondary': self.color_scheme.disabled,
                'black': self.color_scheme.disabled,
                '#000000': self.color_scheme.disabled,
                '#000': self.color_scheme.disabled,
            })
        elif state == IconState.SELECTED:
            base_map.update({
                'primary': self.color_scheme.selected_primary,
                'secondary': self.color_scheme.selected_primary,
                'background': self.color_scheme.selected_background,
                'black': self.color_scheme.selected_primary,
                '#000000': self.color_scheme.selected_primary,
                '#000': self.color_scheme.selected_primary,
                'white': self.color_scheme.selected_primary,
                '#ffffff': self.color_scheme.selected_primary,
                '#fff': self.color_scheme.selected_primary,
            })
        
        return base_map
    
    def _svg_to_qicon(self, svg_content: str, size: IconSize) -> QIcon:
        """Convert SVG content to QIcon."""
        try:
            # Create a QIcon from SVG data
            # Note: This is a simplified implementation
            # In practice, you might want to use QSvgRenderer for better control
            
            from PyQt6.QtCore import QByteArray
            from PyQt6.QtGui import QPixmap
            from PyQt6.QtSvg import QSvgRenderer
            
            # Create SVG renderer
            svg_bytes = QByteArray(svg_content.encode('utf-8'))
            renderer = QSvgRenderer(svg_bytes)
            
            # Create pixmap
            pixmap = QPixmap(size.value, size.value)
            pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background
            
            # Render SVG to pixmap
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            
            # Create QIcon
            icon = QIcon(pixmap)
            return icon
            
        except Exception as e:
            logger.error(f"Failed to convert SVG to QIcon: {e}")
            return self._create_fallback_icon(size)
    
    def _create_fallback_icon(self, size: IconSize) -> QIcon:
        """Create a fallback icon when SVG processing fails."""
        # Create a simple colored square as fallback
        pixmap = QPixmap(size.value, size.value)
        pixmap.fill(QColor(self.color_scheme.primary))
        return QIcon(pixmap)


class IconThemeManager(QObject):
    """Advanced SVG icon theming with dynamic colorization."""
    
    # Signals
    iconSetLoaded = pyqtSignal(str)  # icon_set_name
    iconSetError = pyqtSignal(str, str)  # icon_set_name, error_message
    themeApplied = pyqtSignal(str)  # theme_name
    
    def __init__(self, theme_engine, style_generator, cache: Optional[ThemeCache] = None):
        """Initialize icon theme manager.
        
        Args:
            theme_engine: Theme engine instance
            style_generator: Style generator for integration
            cache: Optional cache for performance
        """
        super().__init__()
        self.theme_engine = theme_engine
        self.style_generator = style_generator
        self.cache = cache or ThemeCache()
        
        self._icon_sets: Dict[str, IconSet] = {}
        self._themed_icon_sets: Dict[str, Dict[str, ThemedIconSet]] = {}
        self._current_theme: Optional[Theme] = None
        self._current_icon_set: str = "default"
        
        # Thread pool for async operations
        self._thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # Icon directories
        self._icon_directories: List[Path] = []
        
        # Preload timer for performance
        self._preload_timer = QTimer()
        self._preload_timer.setSingleShot(True)
        self._preload_timer.timeout.connect(self._preload_common_icons)
        
        # Connect to theme engine
        if hasattr(self.theme_engine, 'themeChanged'):
            self.theme_engine.themeChanged.connect(self._on_theme_changed)
    
    def add_icon_directory(self, directory: Path) -> None:
        """Add directory to search for icon sets."""
        if directory.exists() and directory.is_dir():
            self._icon_directories.append(directory)
            logger.info(f"Added icon directory: {directory}")
        else:
            logger.warning(f"Icon directory does not exist: {directory}")
    
    def load_icon_set(self, set_name: str) -> Optional[IconSet]:
        """Load icon set from disk.
        
        Args:
            set_name: Name of the icon set to load
            
        Returns:
            Loaded IconSet or None if not found
        """
        if set_name in self._icon_sets:
            return self._icon_sets[set_name]
        
        # Search for icon set in directories
        for directory in self._icon_directories:
            set_dir = directory / set_name
            if set_dir.exists():
                try:
                    icon_set = self._load_icon_set_from_directory(set_dir)
                    self._icon_sets[set_name] = icon_set
                    self.iconSetLoaded.emit(set_name)
                    return icon_set
                except Exception as e:
                    error_msg = f"Failed to load icon set '{set_name}': {e}"
                    logger.error(error_msg)
                    self.iconSetError.emit(set_name, str(e))
                    return None
        
        logger.warning(f"Icon set '{set_name}' not found")
        return None
    
    def _load_icon_set_from_directory(self, set_dir: Path) -> IconSet:
        """Load icon set from directory structure."""
        # Look for metadata file
        metadata_file = set_dir / "metadata.json"
        if not metadata_file.exists():
            raise ThemeError(f"No metadata.json found in {set_dir}")
        
        import json
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        # Load icon definitions
        icons = {}
        icons_dir = set_dir / "icons"
        if icons_dir.exists():
            for svg_file in icons_dir.glob("*.svg"):
                icon_name = svg_file.stem
                icon_def = IconDefinition(
                    name=icon_name,
                    category=metadata.get('category', 'general'),
                    description=f"{icon_name} icon",
                    svg_path=str(svg_file),
                    keywords=[icon_name],
                    style=IconStyle(metadata.get('style', 'filled')),
                    variations={IconState.NORMAL: str(svg_file)}
                )
                icons[icon_name] = icon_def
        
        return IconSet(
            name=metadata['name'],
            description=metadata.get('description', ''),
            style=IconStyle(metadata.get('style', 'filled')),
            icons=icons,
            license=metadata.get('license', 'MIT'),
            version=metadata.get('version', '1.0.0')
        )
    
    def set_current_icon_set(self, set_name: str) -> bool:
        """Set the current icon set.
        
        Args:
            set_name: Name of the icon set to use
            
        Returns:
            True if successful, False otherwise
        """
        if set_name not in self._icon_sets:
            if not self.load_icon_set(set_name):
                return False
        
        self._current_icon_set = set_name
        
        # Regenerate themed icons if we have a current theme
        if self._current_theme:
            self._generate_themed_icon_set(self._current_theme, set_name)
        
        return True
    
    def colorize_icon(self, icon_path: str, color_scheme: IconColorScheme) -> QIcon:
        """Colorize a single icon with the given color scheme.
        
        Args:
            icon_path: Path to the SVG icon file
            color_scheme: Color scheme to apply
            
        Returns:
            Colorized QIcon
        """
        try:
            svg_path = Path(icon_path)
            if not svg_path.exists():
                logger.error(f"Icon file not found: {icon_path}")
                return QIcon()
            
            svg_content = svg_path.read_text(encoding='utf-8')
            processor = SVGIconProcessor()
            
            color_map = {
                'primary': color_scheme.primary,
                'secondary': color_scheme.secondary,
                'background': color_scheme.background,
                'accent': color_scheme.accent,
            }
            
            themed_svg = processor.colorize_svg(svg_content, color_map)
            
            # Convert to QIcon (simplified)
            from PyQt6.QtCore import QByteArray
            from PyQt6.QtSvg import QSvgRenderer
            
            svg_bytes = QByteArray(themed_svg.encode('utf-8'))
            renderer = QSvgRenderer(svg_bytes)
            
            pixmap = QPixmap(24, 24)  # Default size
            pixmap.fill(QColor(0, 0, 0, 0))
            
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            
            return QIcon(pixmap)
            
        except Exception as e:
            logger.error(f"Failed to colorize icon '{icon_path}': {e}")
            return QIcon()
    
    def generate_themed_iconset(self, theme: Theme, icon_set_name: str) -> Optional[ThemedIconSet]:
        """Generate themed version of an icon set.
        
        Args:
            theme: Theme to apply
            icon_set_name: Name of the icon set
            
        Returns:
            ThemedIconSet or None if failed
        """
        if icon_set_name not in self._icon_sets:
            if not self.load_icon_set(icon_set_name):
                return None
        
        icon_set = self._icon_sets[icon_set_name]
        
        # Create color scheme from theme
        color_scheme = self._create_color_scheme_from_theme(theme)
        
        # Create themed icon set
        themed_set = ThemedIconSet(icon_set, theme, color_scheme)
        
        # Cache it
        if theme.name not in self._themed_icon_sets:
            self._themed_icon_sets[theme.name] = {}
        self._themed_icon_sets[theme.name][icon_set_name] = themed_set
        
        return themed_set
    
    def _create_color_scheme_from_theme(self, theme: Theme) -> IconColorScheme:
        """Create icon color scheme from theme."""
        colors = theme.colors
        
        return IconColorScheme(
            primary=colors.get_color_value('icon_primary', colors.get_color_value('text_primary', '#000000')),
            secondary=colors.get_color_value('icon_secondary', colors.get_color_value('text_secondary', '#666666')),
            accent=colors.get_color_value('accent', '#007bff'),
            background=colors.get_color_value('background', '#ffffff'),
            disabled=colors.get_color_value('icon_disabled', colors.get_color_value('text_disabled', '#cccccc')),
            hover_primary=colors.get_color_value('icon_hover', colors.get_color_value('text_hover', '#333333')),
            hover_secondary=colors.get_color_value('icon_secondary_hover', colors.get_color_value('text_secondary', '#888888')),
            pressed_primary=colors.get_color_value('icon_pressed', colors.get_color_value('text_pressed', '#555555')),
            selected_primary=colors.get_color_value('icon_selected', colors.get_color_value('text_selected', '#ffffff')),
            selected_background=colors.get_color_value('selection_background', colors.get_color_value('accent', '#007bff'))
        )
    
    def cache_themed_icons(self, themed_set: ThemedIconSet) -> None:
        """Cache themed icons for performance."""
        # Implementation would cache the themed icons to disk/memory
        # This is a placeholder for the actual caching implementation
        cache_key = f"themed_icons_{themed_set.theme.name}_{themed_set.base_icon_set.name}"
        
        if self.cache:
            # Store themed icon data in cache
            cache_data = {
                'theme_name': themed_set.theme.name,
                'icon_set_name': themed_set.base_icon_set.name,
                'color_scheme': themed_set.color_scheme.__dict__,
                'generated_at': str(time.time())
            }
            self.cache.set(cache_key, cache_data)
    
    def get_icon(self, name: str, size: int = 24, theme: Optional[Theme] = None,
                 state: IconState = IconState.NORMAL) -> QIcon:
        """Get themed icon by name.
        
        Args:
            name: Icon name
            size: Icon size in pixels
            theme: Theme to use (current theme if None)
            state: Icon state
            
        Returns:
            Themed QIcon
        """
        # Use current theme if none specified
        if theme is None:
            theme = self._current_theme
        
        if theme is None:
            logger.warning("No theme available for icon generation")
            return QIcon()
        
        # Get or generate themed icon set
        themed_set = self._get_themed_icon_set(theme, self._current_icon_set)
        if not themed_set:
            return QIcon()
        
        # Convert size to IconSize enum
        icon_size = self._size_to_enum(size)
        
        # Get the icon
        icon = themed_set.get_icon(name, icon_size, state)
        return icon if icon else QIcon()
    
    def _get_themed_icon_set(self, theme: Theme, icon_set_name: str) -> Optional[ThemedIconSet]:
        """Get or generate themed icon set."""
        # Check cache first
        if (theme.name in self._themed_icon_sets and 
            icon_set_name in self._themed_icon_sets[theme.name]):
            return self._themed_icon_sets[theme.name][icon_set_name]
        
        # Generate new themed icon set
        return self.generate_themed_iconset(theme, icon_set_name)
    
    def _size_to_enum(self, size: int) -> IconSize:
        """Convert pixel size to IconSize enum."""
        if size <= 16:
            return IconSize.SMALL
        elif size <= 24:
            return IconSize.MEDIUM
        elif size <= 32:
            return IconSize.LARGE
        elif size <= 48:
            return IconSize.EXTRA_LARGE
        else:
            return IconSize.HUGE
    
    def _on_theme_changed(self, theme: Theme) -> None:
        """Handle theme change."""
        self._current_theme = theme
        
        # Clear themed icon cache for the new theme
        if theme.name not in self._themed_icon_sets:
            self._themed_icon_sets[theme.name] = {}
        
        # Generate themed icon set for current icon set
        self._generate_themed_icon_set(theme, self._current_icon_set)
        
        # Start preloading common icons
        self._preload_timer.start(100)  # Delay to avoid blocking UI
        
        self.themeApplied.emit(theme.name)
    
    def _generate_themed_icon_set(self, theme: Theme, icon_set_name: str) -> None:
        """Generate themed icon set asynchronously."""
        def generate():
            try:
                themed_set = self.generate_themed_iconset(theme, icon_set_name)
                if themed_set:
                    self.cache_themed_icons(themed_set)
            except Exception as e:
                logger.error(f"Failed to generate themed icon set: {e}")
        
        # Run in thread pool to avoid blocking UI
        self._thread_pool.submit(generate)
    
    def _preload_common_icons(self) -> None:
        """Preload commonly used icons for better performance."""
        if not self._current_theme:
            return
        
        common_icons = [
            'file', 'folder', 'save', 'open', 'close', 'copy', 'paste', 'cut',
            'undo', 'redo', 'search', 'settings', 'help', 'info', 'warning', 'error'
        ]
        
        def preload():
            for icon_name in common_icons:
                try:
                    # Preload in multiple sizes and states
                    for size in [IconSize.SMALL, IconSize.MEDIUM, IconSize.LARGE]:
                        for state in [IconState.NORMAL, IconState.HOVER, IconState.DISABLED]:
                            self.get_icon(icon_name, size.value, self._current_theme, state)
                except Exception as e:
                    logger.debug(f"Failed to preload icon '{icon_name}': {e}")
        
        # Run preloading in background
        self._thread_pool.submit(preload)
    
    def get_available_icon_sets(self) -> List[str]:
        """Get list of available icon sets."""
        return list(self._icon_sets.keys())
    
    def get_available_icons(self, icon_set_name: Optional[str] = None) -> List[str]:
        """Get list of available icons in a set.
        
        Args:
            icon_set_name: Icon set name (current set if None)
            
        Returns:
            List of icon names
        """
        set_name = icon_set_name or self._current_icon_set
        if set_name in self._icon_sets:
            return list(self._icon_sets[set_name].icons.keys())
        return []
    
    def search_icons(self, query: str, icon_set_name: Optional[str] = None) -> List[str]:
        """Search for icons by name or keywords.
        
        Args:
            query: Search query
            icon_set_name: Icon set to search in (current set if None)
            
        Returns:
            List of matching icon names
        """
        set_name = icon_set_name or self._current_icon_set
        if set_name not in self._icon_sets:
            return []
        
        query = query.lower()
        matches = []
        
        for icon_name, icon_def in self._icon_sets[set_name].icons.items():
            # Check name
            if query in icon_name.lower():
                matches.append(icon_name)
                continue
            
            # Check keywords
            if any(query in keyword.lower() for keyword in icon_def.keywords):
                matches.append(icon_name)
                continue
        
        return matches


# Built-in icon sets configuration
BUILTIN_ICON_SETS = {
    'default': {
        'name': 'Default',
        'description': 'Default filled icon set',
        'style': IconStyle.FILLED,
        'license': 'MIT',
        'icons': {
            'file': {'category': 'files', 'keywords': ['document', 'file']},
            'folder': {'category': 'files', 'keywords': ['directory', 'folder']},
            'save': {'category': 'actions', 'keywords': ['save', 'disk']},
            'open': {'category': 'actions', 'keywords': ['open', 'load']},
            'close': {'category': 'actions', 'keywords': ['close', 'exit']},
            'copy': {'category': 'actions', 'keywords': ['copy', 'duplicate']},
            'paste': {'category': 'actions', 'keywords': ['paste', 'insert']},
            'cut': {'category': 'actions', 'keywords': ['cut', 'remove']},
            'undo': {'category': 'actions', 'keywords': ['undo', 'back']},
            'redo': {'category': 'actions', 'keywords': ['redo', 'forward']},
            'search': {'category': 'actions', 'keywords': ['search', 'find']},
            'settings': {'category': 'interface', 'keywords': ['settings', 'config']},
            'help': {'category': 'interface', 'keywords': ['help', 'info']},
            'warning': {'category': 'status', 'keywords': ['warning', 'alert']},
            'error': {'category': 'status', 'keywords': ['error', 'problem']},
        }
    },
    'outline': {
        'name': 'Outline',
        'description': 'Outline style icon set',
        'style': IconStyle.OUTLINE,
        'license': 'MIT',
        'icons': {
            # Same icons as default but in outline style
        }
    }
}