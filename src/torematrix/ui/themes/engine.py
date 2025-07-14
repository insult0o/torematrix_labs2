"""Core theme engine for TORE Matrix Labs V3."""

import logging
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path
import asyncio
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QApplication

from ...core.config import ConfigManager
from ...core.events import EventBus
from .base import Theme, ThemeProvider, ColorPalette, Typography
from .types import ThemeType, ThemeMetadata, ThemeData
from .exceptions import (
    ThemeError, ThemeNotFoundError, ThemeLoadError, 
    ThemeValidationError
)

logger = logging.getLogger(__name__)


class FileThemeProvider(ThemeProvider):
    """File-based theme provider for loading themes from disk."""
    
    def __init__(self, themes_directory: Path):
        """Initialize file theme provider.
        
        Args:
            themes_directory: Directory containing theme files
        """
        self.themes_directory = themes_directory
        self._theme_cache: Dict[str, Theme] = {}
        self._metadata_cache: Dict[str, ThemeMetadata] = {}
        
        # Ensure directory exists
        self.themes_directory.mkdir(parents=True, exist_ok=True)
        
    def load_theme(self, theme_name: str) -> Theme:
        """Load theme from file."""
        if theme_name in self._theme_cache:
            return self._theme_cache[theme_name]
        
        # Look for theme files
        theme_file = self._find_theme_file(theme_name)
        if not theme_file:
            raise ThemeNotFoundError(theme_name)
        
        try:
            theme_data = self._load_theme_file(theme_file)
            theme = self._create_theme_from_data(theme_name, theme_data)
            self._theme_cache[theme_name] = theme
            return theme
        except Exception as e:
            raise ThemeLoadError(theme_name, str(e))
    
    def _find_theme_file(self, theme_name: str) -> Optional[Path]:
        """Find theme file by name."""
        extensions = ['.yaml', '.yml', '.json', '.toml']
        for ext in extensions:
            theme_file = self.themes_directory / f"{theme_name}{ext}"
            if theme_file.exists():
                return theme_file
        return None
    
    def _load_theme_file(self, theme_file: Path) -> ThemeData:
        """Load theme data from file."""
        import yaml
        import json
        
        try:
            with open(theme_file, 'r', encoding='utf-8') as f:
                if theme_file.suffix in ['.yaml', '.yml']:
                    return yaml.safe_load(f)
                elif theme_file.suffix == '.json':
                    return json.load(f)
                elif theme_file.suffix == '.toml':
                    import tomli
                    return tomli.loads(f.read())
                else:
                    raise ThemeValidationError(f"Unsupported file format: {theme_file.suffix}")
        except Exception as e:
            raise ThemeLoadError(theme_file.stem, f"File reading error: {e}")
    
    def _create_theme_from_data(self, theme_name: str, theme_data: ThemeData) -> Theme:
        """Create Theme instance from data."""
        # Extract metadata
        metadata_data = theme_data.get('metadata', {})
        metadata = ThemeMetadata(
            name=metadata_data.get('name', theme_name),
            version=metadata_data.get('version', '1.0.0'),
            description=metadata_data.get('description', ''),
            author=metadata_data.get('author', ''),
            category=ThemeType(metadata_data.get('category', 'custom')),
            accessibility_compliant=metadata_data.get('accessibility_compliant', True),
            high_contrast_available=metadata_data.get('high_contrast_available', False),
            requires_icons=metadata_data.get('requires_icons', True),
        )
        
        return Theme(theme_name, metadata, theme_data)
    
    def get_available_themes(self) -> List[str]:
        """Get list of available theme names."""
        themes = []
        extensions = ['.yaml', '.yml', '.json', '.toml']
        
        for theme_file in self.themes_directory.glob('*'):
            if theme_file.is_file() and theme_file.suffix in extensions:
                themes.append(theme_file.stem)
        
        return sorted(themes)
    
    def theme_exists(self, theme_name: str) -> bool:
        """Check if theme exists."""
        return self._find_theme_file(theme_name) is not None
    
    def clear_cache(self) -> None:
        """Clear theme cache."""
        self._theme_cache.clear()
        self._metadata_cache.clear()


class BuiltinThemeProvider(ThemeProvider):
    """Provider for built-in themes."""
    
    def __init__(self):
        """Initialize built-in theme provider."""
        self._themes: Dict[str, Theme] = {}
        self._create_builtin_themes()
    
    def _create_builtin_themes(self) -> None:
        """Create built-in themes."""
        # Light theme
        light_theme_data = {
            'metadata': {
                'name': 'Light Professional',
                'version': '1.0.0',
                'description': 'Clean light theme for professional use',
                'author': 'TORE Matrix Labs',
                'category': 'light',
                'accessibility_compliant': True,
            },
            'colors': {
                'primary': '#2196F3',
                'secondary': '#FF9800', 
                'background': '#FFFFFF',
                'surface': '#F5F5F5',
                'text_primary': '#212529',
                'text_secondary': '#6C757D',
                'border': '#DEE2E6',
                'accent': '#007BFF',
                'success': '#28A745',
                'warning': '#FFC107',
                'error': '#DC3545',
                'info': '#17A2B8',
            },
            'typography': {
                'default': {
                    'font_family': 'Segoe UI',
                    'font_size': 12,
                    'font_weight': 400,
                    'line_height': 1.4,
                },
                'heading': {
                    'font_family': 'Segoe UI',
                    'font_size': 16,
                    'font_weight': 600,
                    'line_height': 1.2,
                },
            },
            'components': {
                'main_window': {
                    'background': '${colors.background}',
                    'border': 'none',
                },
                'menu_bar': {
                    'background': '${colors.surface}',
                    'color': '${colors.text_primary}',
                },
            }
        }
        
        # Dark theme
        dark_theme_data = {
            'metadata': {
                'name': 'Dark Professional',
                'version': '1.0.0',
                'description': 'Professional dark theme for reduced eye strain',
                'author': 'TORE Matrix Labs',
                'category': 'dark',
                'accessibility_compliant': True,
            },
            'colors': {
                'primary': '#2196F3',
                'secondary': '#FF9800',
                'background': '#121212',
                'surface': '#1E1E1E',
                'text_primary': '#FFFFFF',
                'text_secondary': '#B3B3B3',
                'border': '#333333',
                'accent': '#2196F3',
                'success': '#4CAF50',
                'warning': '#FF9800',
                'error': '#F44336',
                'info': '#2196F3',
            },
            'typography': {
                'default': {
                    'font_family': 'Segoe UI',
                    'font_size': 12,
                    'font_weight': 400,
                    'line_height': 1.4,
                },
                'heading': {
                    'font_family': 'Segoe UI',
                    'font_size': 16,
                    'font_weight': 600,
                    'line_height': 1.2,
                },
            },
            'components': {
                'main_window': {
                    'background': '${colors.background}',
                    'border': 'none',
                },
                'menu_bar': {
                    'background': '${colors.surface}',
                    'color': '${colors.text_primary}',
                },
            }
        }
        
        # Create theme instances
        light_metadata = ThemeMetadata(**light_theme_data['metadata'])
        dark_metadata = ThemeMetadata(**dark_theme_data['metadata'])
        
        self._themes['light'] = Theme('light', light_metadata, light_theme_data)
        self._themes['dark'] = Theme('dark', dark_metadata, dark_theme_data)
    
    def load_theme(self, theme_name: str) -> Theme:
        """Load built-in theme."""
        if theme_name not in self._themes:
            raise ThemeNotFoundError(theme_name)
        return self._themes[theme_name]
    
    def get_available_themes(self) -> List[str]:
        """Get list of built-in themes."""
        return list(self._themes.keys())
    
    def theme_exists(self, theme_name: str) -> bool:
        """Check if built-in theme exists."""
        return theme_name in self._themes


class ThemeEngine(QObject):
    """Core theme management engine with loading and switching."""
    
    # Signals for theme events
    theme_loading = pyqtSignal(str)  # theme_name
    theme_loaded = pyqtSignal(str)   # theme_name
    theme_changed = pyqtSignal(str, str)  # new_theme, previous_theme
    theme_error = pyqtSignal(str, str)    # theme_name, error_message
    
    def __init__(
        self, 
        config_manager: ConfigManager,
        event_bus: EventBus,
        parent: Optional[QObject] = None
    ):
        """Initialize theme engine.
        
        Args:
            config_manager: Configuration manager instance
            event_bus: Event bus for communication
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self.config_manager = config_manager
        self.event_bus = event_bus
        
        # Current state
        self.current_theme: Optional[Theme] = None
        self.previous_theme_name: Optional[str] = None
        
        # Theme providers
        self.theme_providers: List[ThemeProvider] = []
        self.builtin_provider = BuiltinThemeProvider()
        self.theme_providers.append(self.builtin_provider)
        
        # Theme cache and management
        self.theme_cache: Dict[str, Theme] = {}
        self.cache_enabled: bool = True
        self.max_cache_size: int = 50
        
        # Callbacks for theme changes
        self.theme_change_callbacks: List[Callable[[Theme], None]] = []
        
        # Performance monitoring
        self.load_times: Dict[str, float] = {}
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="theme")
        
        # Setup file provider for custom themes
        themes_dir = Path(config_manager.get('theme.custom_themes_directory', 'themes'))
        self.file_provider = FileThemeProvider(themes_dir)
        self.theme_providers.append(self.file_provider)
        
        # Validation settings
        self.validate_themes: bool = True
        self.strict_validation: bool = False
        
        logger.info("ThemeEngine initialized")
    
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
        import time
        start_time = time.time()
        
        try:
            self.theme_loading.emit(theme_name)
            
            # Check cache first
            if self.cache_enabled and theme_name in self.theme_cache:
                theme = self.theme_cache[theme_name]
                logger.debug(f"Theme '{theme_name}' loaded from cache")
                self.theme_loaded.emit(theme_name)
                return theme
            
            # Try each provider
            theme = None
            for provider in self.theme_providers:
                try:
                    if provider.theme_exists(theme_name):
                        theme = provider.load_theme(theme_name)
                        break
                except Exception as e:
                    logger.warning(f"Provider {type(provider).__name__} failed to load '{theme_name}': {e}")
                    continue
            
            if theme is None:
                raise ThemeNotFoundError(theme_name)
            
            # Validate theme if enabled
            if self.validate_themes:
                self._validate_theme(theme)
            
            # Cache theme
            if self.cache_enabled:
                self._cache_theme(theme)
            
            # Track performance
            load_time = time.time() - start_time
            self.load_times[theme_name] = load_time
            logger.debug(f"Theme '{theme_name}' loaded in {load_time:.3f}s")
            
            self.theme_loaded.emit(theme_name)
            return theme
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to load theme '{theme_name}': {error_msg}")
            self.theme_error.emit(theme_name, error_msg)
            raise
    
    def apply_theme(self, theme: Theme, target: Optional[QWidget] = None) -> None:
        """Apply theme to target widget or application.
        
        Args:
            theme: Theme to apply
            target: Target widget (None for application-wide)
        """
        try:
            # Generate stylesheet
            stylesheet = theme.generate_stylesheet()
            
            # Apply to target or application
            if target:
                target.setStyleSheet(stylesheet)
                logger.debug(f"Theme '{theme.name}' applied to widget {type(target).__name__}")
            else:
                app = QApplication.instance()
                if app:
                    app.setStyleSheet(stylesheet)
                    logger.debug(f"Theme '{theme.name}' applied application-wide")
            
            # Notify event bus
            self.event_bus.emit('theme.applied', {
                'theme_name': theme.name,
                'target_type': type(target).__name__ if target else 'application'
            })
            
        except Exception as e:
            logger.error(f"Failed to apply theme '{theme.name}': {e}")
            raise ThemeError(f"Failed to apply theme: {e}", theme.name)
    
    def switch_theme(self, theme_name: str) -> bool:
        """Switch to a different theme.
        
        Args:
            theme_name: Name of theme to switch to
            
        Returns:
            True if switch was successful
        """
        try:
            # Store previous theme
            previous_theme_name = self.current_theme.name if self.current_theme else None
            
            # Load new theme
            new_theme = self.load_theme(theme_name)
            
            # Apply theme
            self.apply_theme(new_theme)
            
            # Update current theme
            self.current_theme = new_theme
            self.previous_theme_name = previous_theme_name
            
            # Notify callbacks
            for callback in self.theme_change_callbacks:
                try:
                    callback(new_theme)
                except Exception as e:
                    logger.error(f"Theme change callback error: {e}")
            
            # Emit signals
            self.theme_changed.emit(theme_name, previous_theme_name or "")
            
            # Publish event
            self.event_bus.emit('theme.changed', {
                'new_theme': theme_name,
                'previous_theme': previous_theme_name,
                'timestamp': time.time()
            })
            
            # Save preference
            self.config_manager.set('theme.current', theme_name)
            
            logger.info(f"Theme switched from '{previous_theme_name}' to '{theme_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to switch to theme '{theme_name}': {e}")
            self.theme_error.emit(theme_name, str(e))
            return False
    
    def get_current_theme(self) -> Optional[Theme]:
        """Get currently active theme."""
        return self.current_theme
    
    def register_theme_provider(self, provider: ThemeProvider) -> None:
        """Register a new theme provider.
        
        Args:
            provider: Theme provider to register
        """
        if provider not in self.theme_providers:
            self.theme_providers.append(provider)
            logger.info(f"Registered theme provider: {type(provider).__name__}")
    
    def get_available_themes(self) -> List[str]:
        """Get list of all available theme names."""
        all_themes = set()
        
        for provider in self.theme_providers:
            try:
                themes = provider.get_available_themes()
                all_themes.update(themes)
            except Exception as e:
                logger.warning(f"Provider {type(provider).__name__} failed to list themes: {e}")
        
        return sorted(list(all_themes))
    
    def get_theme_metadata(self, theme_name: str) -> Optional[ThemeMetadata]:
        """Get theme metadata without loading full theme.
        
        Args:
            theme_name: Name of theme
            
        Returns:
            Theme metadata or None if not found
        """
        for provider in self.theme_providers:
            try:
                if provider.theme_exists(theme_name):
                    return provider.get_theme_metadata(theme_name)
            except Exception as e:
                logger.warning(f"Failed to get metadata for '{theme_name}' from {type(provider).__name__}: {e}")
        
        return None
    
    def validate_theme(self, theme_data: Dict[str, Any]) -> bool:
        """Validate theme data structure.
        
        Args:
            theme_data: Theme data dictionary
            
        Returns:
            True if valid
            
        Raises:
            ThemeValidationError: If validation fails
        """
        required_sections = ['metadata', 'colors']
        
        for section in required_sections:
            if section not in theme_data:
                raise ThemeValidationError(f"Missing required section: {section}")
        
        # Validate metadata
        metadata = theme_data['metadata']
        required_metadata = ['name', 'version', 'author']
        
        for field in required_metadata:
            if field not in metadata:
                raise ThemeValidationError(f"Missing required metadata field: {field}")
        
        # Validate colors
        colors = theme_data['colors']
        required_colors = ['background', 'text_primary']
        
        for color in required_colors:
            if color not in colors:
                raise ThemeValidationError(f"Missing required color: {color}")
        
        return True
    
    def _validate_theme(self, theme: Theme) -> None:
        """Internal theme validation."""
        if self.strict_validation:
            # Comprehensive validation
            if not theme.get_color_palette():
                raise ThemeValidationError("Theme missing color palette", theme.name)
            
            # Validate accessibility if required
            if theme.metadata.accessibility_compliant:
                palette = theme.get_color_palette()
                if palette:
                    accessibility_results = palette.validate_accessibility()
                    failed_colors = [name for name, valid in accessibility_results.items() if not valid]
                    if failed_colors:
                        logger.warning(f"Theme '{theme.name}' has accessibility issues with colors: {failed_colors}")
    
    def _cache_theme(self, theme: Theme) -> None:
        """Cache theme with size management."""
        if len(self.theme_cache) >= self.max_cache_size:
            # Remove oldest entry
            oldest_theme = next(iter(self.theme_cache))
            del self.theme_cache[oldest_theme]
        
        self.theme_cache[theme.name] = theme
        logger.debug(f"Theme '{theme.name}' cached")
    
    def register_theme_change_callback(self, callback: Callable[[Theme], None]) -> None:
        """Register callback for theme changes.
        
        Args:
            callback: Function to call when theme changes
        """
        if callback not in self.theme_change_callbacks:
            self.theme_change_callbacks.append(callback)
    
    def unregister_theme_change_callback(self, callback: Callable[[Theme], None]) -> None:
        """Unregister theme change callback.
        
        Args:
            callback: Function to remove from callbacks
        """
        if callback in self.theme_change_callbacks:
            self.theme_change_callbacks.remove(callback)
    
    def clear_cache(self) -> None:
        """Clear theme cache."""
        self.theme_cache.clear()
        self.file_provider.clear_cache()
        logger.info("Theme cache cleared")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get theme loading performance statistics."""
        if not self.load_times:
            return {}
        
        times = list(self.load_times.values())
        return {
            'themes_loaded': len(self.load_times),
            'avg_load_time': sum(times) / len(times),
            'min_load_time': min(times),
            'max_load_time': max(times),
            'cache_size': len(self.theme_cache),
        }
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        self.executor.shutdown(wait=True)
        self.clear_cache()
        logger.info("ThemeEngine cleaned up")