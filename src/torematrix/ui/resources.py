"""Resource management system for ToreMatrix V3."""

import os
import logging
from typing import Dict, Optional, Set, List
from pathlib import Path
from enum import Enum

from PyQt6.QtCore import QObject, QSettings, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QFont

from ..core.events import EventBus
from ..core.config import ConfigManager
from ..core.state import StateManager
from .base import BaseUIComponent

logger = logging.getLogger(__name__)


class ResourceType(Enum):
    """Types of resources."""
    ICON = "icon"
    IMAGE = "image"
    FONT = "font"
    STYLESHEET = "stylesheet"
    TRANSLATION = "translation"


class IconSize(Enum):
    """Standard icon sizes."""
    SMALL = (16, 16)
    MEDIUM = (24, 24)
    LARGE = (32, 32)
    EXTRA_LARGE = (48, 48)
    TOOLBAR = (24, 24)
    MENU = (16, 16)


class ResourceManager(BaseUIComponent):
    """Resource management with caching and theme support."""
    
    # Signals
    resource_loaded = pyqtSignal(str, str)  # resource_name, resource_type
    resource_failed = pyqtSignal(str, str)  # resource_name, error
    theme_changed = pyqtSignal(str)         # theme_name
    
    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigManager,
        state_manager: StateManager,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        # Resource storage
        self._icons: Dict[str, QIcon] = {}
        self._pixmaps: Dict[str, QPixmap] = {}
        self._fonts: Dict[str, QFont] = {}
        self._stylesheets: Dict[str, str] = {}
        
        # Resource paths
        self._resource_paths: Dict[ResourceType, Path] = {}
        self._fallback_paths: Dict[ResourceType, Path] = {}
        
        # Theme management
        self._current_theme = "light"
        self._theme_aware_resources: Set[str] = set()
        
        # Cache management
        self._cache_enabled = True
        self._max_cache_size = 100  # Max items per resource type
        
        # Settings
        self._settings = QSettings("ToreMatrix", "ToreMatrixV3")
        
        # Setup resource system
        self._setup_resource_paths()
        self._load_theme_preference()
    
    def _setup_component(self) -> None:
        """Setup the resource management system."""
        self._preload_essential_resources()
    
    def _setup_resource_paths(self) -> None:
        """Setup resource directory paths."""
        base_path = Path(__file__).parent
        
        # Primary resource paths
        self._resource_paths = {
            ResourceType.ICON: base_path / "icons",
            ResourceType.IMAGE: base_path / "images", 
            ResourceType.FONT: base_path / "fonts",
            ResourceType.STYLESHEET: base_path / "styles",
            ResourceType.TRANSLATION: base_path / "translations"
        }
        
        # Fallback paths (system resources)
        self._fallback_paths = {
            ResourceType.ICON: Path("/usr/share/icons") if os.name == "posix" else Path(),
            ResourceType.IMAGE: Path(),
            ResourceType.FONT: Path("/usr/share/fonts") if os.name == "posix" else Path(),
            ResourceType.STYLESHEET: Path(),
            ResourceType.TRANSLATION: Path()
        }
        
        # Create directories if they don't exist
        for path in self._resource_paths.values():
            path.mkdir(parents=True, exist_ok=True)
    
    def _load_theme_preference(self) -> None:
        """Load theme preference from settings."""
        self._current_theme = self._settings.value("theme", "light", str)
    
    def _preload_essential_resources(self) -> None:
        """Preload essential application resources."""
        essential_icons = [
            "app_icon", "new", "open", "save", "save-as", "export",
            "undo", "redo", "cut", "copy", "paste", "preferences",
            "zoom-in", "zoom-out", "zoom-reset", "fullscreen",
            "help", "about", "exit"
        ]
        
        for icon_name in essential_icons:
            self.get_icon(icon_name, IconSize.SMALL, preload=True)
            self.get_icon(icon_name, IconSize.MEDIUM, preload=True)
    
    def get_icon(
        self,
        name: str,
        size: IconSize = IconSize.MEDIUM,
        theme_aware: bool = True,
        preload: bool = False
    ) -> QIcon:
        """Get icon with size and theme support."""
        cache_key = f"{name}_{size.name}_{self._current_theme if theme_aware else 'default'}"
        
        # Check cache first
        if cache_key in self._icons and not preload:
            return self._icons[cache_key]
        
        # Build icon path
        icon_path = self._build_icon_path(name, size, theme_aware)
        
        # Load icon
        icon = self._load_icon_from_path(icon_path)
        
        # Fallback to different sizes or themes
        if icon.isNull():
            icon = self._load_icon_fallback(name, size, theme_aware)
        
        # Cache if enabled
        if self._cache_enabled:
            self._cache_icon(cache_key, icon)
        
        # Track theme-aware resources
        if theme_aware:
            self._theme_aware_resources.add(name)
        
        if not icon.isNull():
            self.resource_loaded.emit(name, ResourceType.ICON.value)
        else:
            self.resource_failed.emit(name, f"Icon not found: {name}")
            # Return empty icon instead of None
            icon = QIcon()
        
        return icon
    
    def _build_icon_path(self, name: str, size: IconSize, theme_aware: bool) -> Path:
        """Build icon file path."""
        icon_dir = self._resource_paths[ResourceType.ICON]
        
        # Theme-aware path
        if theme_aware:
            theme_dir = icon_dir / self._current_theme
            if theme_dir.exists():
                icon_dir = theme_dir
        
        # Size-specific subdirectory
        size_dir = icon_dir / f"{size.value[0]}x{size.value[1]}"
        if size_dir.exists():
            icon_dir = size_dir
        
        # Try different file extensions
        for ext in [".svg", ".png", ".ico", ".xpm"]:
            icon_path = icon_dir / f"{name}{ext}"
            if icon_path.exists():
                return icon_path
        
        # Return non-existent path for fallback handling
        return icon_dir / f"{name}.svg"
    
    def _load_icon_from_path(self, icon_path: Path) -> QIcon:
        """Load icon from file path."""
        if icon_path.exists():
            try:
                return QIcon(str(icon_path))
            except Exception as e:
                logger.warning(f"Failed to load icon from {icon_path}: {e}")
        
        return QIcon()
    
    def _load_icon_fallback(self, name: str, size: IconSize, theme_aware: bool) -> QIcon:
        """Load icon with fallback strategies."""
        # Try other sizes
        for fallback_size in IconSize:
            if fallback_size != size:
                icon_path = self._build_icon_path(name, fallback_size, theme_aware)
                icon = self._load_icon_from_path(icon_path)
                if not icon.isNull():
                    return icon
        
        # Try other theme
        if theme_aware:
            fallback_theme = "light" if self._current_theme == "dark" else "dark"
            old_theme = self._current_theme
            self._current_theme = fallback_theme
            icon_path = self._build_icon_path(name, size, True)
            self._current_theme = old_theme
            
            icon = self._load_icon_from_path(icon_path)
            if not icon.isNull():
                return icon
        
        # Try non-theme-aware version
        if theme_aware:
            icon_path = self._build_icon_path(name, size, False)
            icon = self._load_icon_from_path(icon_path)
            if not icon.isNull():
                return icon
        
        # Try system fallback paths
        fallback_dir = self._fallback_paths.get(ResourceType.ICON)
        if fallback_dir and fallback_dir.exists():
            for ext in [".svg", ".png", ".ico"]:
                fallback_path = fallback_dir / f"{name}{ext}"
                icon = self._load_icon_from_path(fallback_path)
                if not icon.isNull():
                    return icon
        
        return QIcon()
    
    def _cache_icon(self, cache_key: str, icon: QIcon) -> None:
        """Cache icon with size management."""
        if len(self._icons) >= self._max_cache_size:
            # Remove oldest cached icon (simple FIFO)
            oldest_key = next(iter(self._icons))
            del self._icons[oldest_key]
        
        self._icons[cache_key] = icon
    
    def get_pixmap(self, name: str, width: int, height: int) -> QPixmap:
        """Get pixmap with specific dimensions."""
        cache_key = f"{name}_{width}x{height}"
        
        # Check cache
        if cache_key in self._pixmaps:
            return self._pixmaps[cache_key]
        
        # Load image
        image_path = self._resource_paths[ResourceType.IMAGE] / f"{name}.png"
        
        pixmap = QPixmap()
        if image_path.exists():
            pixmap.load(str(image_path))
            if not pixmap.isNull():
                pixmap = pixmap.scaled(width, height)
        
        # Cache
        if self._cache_enabled:
            self._pixmaps[cache_key] = pixmap
        
        return pixmap
    
    def get_font(self, name: str, size: int = 10) -> QFont:
        """Get font with specific size."""
        cache_key = f"{name}_{size}"
        
        # Check cache
        if cache_key in self._fonts:
            return self._fonts[cache_key]
        
        # Load font
        font_path = self._resource_paths[ResourceType.FONT] / f"{name}.ttf"
        
        if font_path.exists():
            # Load custom font (would need QFontDatabase.addApplicationFont)
            font = QFont(name, size)
        else:
            # Use system font
            font = QFont(name, size)
        
        # Cache
        if self._cache_enabled:
            self._fonts[cache_key] = font
        
        return font
    
    def get_stylesheet(self, name: str) -> str:
        """Get stylesheet content."""
        # Check cache
        if name in self._stylesheets:
            return self._stylesheets[name]
        
        # Load stylesheet
        style_path = self._resource_paths[ResourceType.STYLESHEET] / f"{name}.qss"
        
        stylesheet = ""
        if style_path.exists():
            try:
                with open(style_path, 'r', encoding='utf-8') as f:
                    stylesheet = f.read()
                    
                    # Process theme variables
                    stylesheet = self._process_stylesheet_variables(stylesheet)
                    
            except Exception as e:
                logger.error(f"Failed to load stylesheet {name}: {e}")
        
        # Cache
        if self._cache_enabled:
            self._stylesheets[name] = stylesheet
        
        return stylesheet
    
    def _process_stylesheet_variables(self, stylesheet: str) -> str:
        """Process theme variables in stylesheet."""
        # Simple variable replacement (could be enhanced)
        variables = {
            "@theme": self._current_theme,
            "@primary-color": "#007ACC" if self._current_theme == "light" else "#0E639C",
            "@background-color": "#FFFFFF" if self._current_theme == "light" else "#2B2B2B",
            "@text-color": "#000000" if self._current_theme == "light" else "#FFFFFF"
        }
        
        for var, value in variables.items():
            stylesheet = stylesheet.replace(var, value)
        
        return stylesheet
    
    def set_theme(self, theme_name: str) -> None:
        """Change application theme."""
        if theme_name != self._current_theme:
            old_theme = self._current_theme
            self._current_theme = theme_name
            
            # Clear theme-aware cached resources
            self._clear_theme_cache()
            
            # Save preference
            self._settings.setValue("theme", theme_name)
            
            # Emit signal
            self.theme_changed.emit(theme_name)
            
            logger.info(f"Theme changed from {old_theme} to {theme_name}")
    
    def _clear_theme_cache(self) -> None:
        """Clear cached theme-aware resources."""
        # Clear icons that are theme-aware
        keys_to_remove = []
        for key in self._icons.keys():
            for resource_name in self._theme_aware_resources:
                if key.startswith(f"{resource_name}_"):
                    keys_to_remove.append(key)
                    break
        
        for key in keys_to_remove:
            del self._icons[key]
        
        # Clear stylesheets (all are theme-aware)
        self._stylesheets.clear()
    
    def get_current_theme(self) -> str:
        """Get current theme name."""
        return self._current_theme
    
    def get_available_themes(self) -> List[str]:
        """Get list of available themes."""
        themes = ["light", "dark"]  # Default themes
        
        # Check for custom themes
        icon_dir = self._resource_paths[ResourceType.ICON]
        for item in icon_dir.iterdir():
            if item.is_dir() and item.name not in themes:
                themes.append(item.name)
        
        return themes
    
    def preload_resources(self, resource_names: List[str], resource_type: ResourceType) -> None:
        """Preload specific resources."""
        for name in resource_names:
            if resource_type == ResourceType.ICON:
                self.get_icon(name, preload=True)
            elif resource_type == ResourceType.IMAGE:
                self.get_pixmap(name, 32, 32)  # Default size
            elif resource_type == ResourceType.STYLESHEET:
                self.get_stylesheet(name)
    
    def clear_cache(self) -> None:
        """Clear all cached resources."""
        self._icons.clear()
        self._pixmaps.clear()
        self._fonts.clear()
        self._stylesheets.clear()
        
        logger.info("Resource cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "icons": len(self._icons),
            "pixmaps": len(self._pixmaps),
            "fonts": len(self._fonts),
            "stylesheets": len(self._stylesheets)
        }
    
    def set_cache_enabled(self, enabled: bool) -> None:
        """Enable or disable resource caching."""
        self._cache_enabled = enabled
        if not enabled:
            self.clear_cache()
    
    def get_resource_path(self, resource_type: ResourceType) -> Path:
        """Get resource directory path."""
        return self._resource_paths.get(resource_type, Path())
    
    def resource_exists(self, name: str, resource_type: ResourceType) -> bool:
        """Check if resource exists."""
        if resource_type == ResourceType.ICON:
            icon_path = self._build_icon_path(name, IconSize.MEDIUM, True)
            return icon_path.exists()
        elif resource_type == ResourceType.STYLESHEET:
            style_path = self._resource_paths[resource_type] / f"{name}.qss"
            return style_path.exists()
        
        return False