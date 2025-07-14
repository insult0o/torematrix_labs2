"""Advanced theme management system for ToreMatrix V3.

This module provides sophisticated theme management with smooth transitions,
dark/light mode support, and integration with the configuration system.
"""

from typing import Dict, List, Optional, Callable, Any, Set
from pathlib import Path
from enum import Enum
import logging
from dataclasses import dataclass

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import QObject, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal, QSettings
from PyQt6.QtGui import QIcon, QColor, QPalette

from ..core.events import EventBus
from ..core.config import ConfigManager
from ..core.state import StateManager
from .base import BaseUIComponent

logger = logging.getLogger(__name__)


class ThemeType(Enum):
    """Available theme types."""
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"  # Follow system preference


@dataclass
class ThemeColors:
    """Color scheme for a theme."""
    # Main colors
    background: str
    primary_background: str
    text: str
    text_disabled: str
    
    # Accent colors
    accent: str
    accent_dark: str
    accent_light: str
    
    # UI element colors
    border: str
    button_background: str
    button_border: str
    button_hover: str
    button_pressed: str
    button_disabled: str
    
    # Menu colors
    menu_background: str
    menu_hover: str
    menu_separator: str
    
    # Status indicators
    success: str
    warning: str
    error: str
    info: str


class ThemeManager(BaseUIComponent):
    """Advanced theme management with smooth transitions and customization."""
    
    # Signals
    theme_changed = pyqtSignal(str)  # theme_name
    theme_loading = pyqtSignal(str)  # theme_name
    theme_loaded = pyqtSignal(str)   # theme_name
    theme_error = pyqtSignal(str, str)  # theme_name, error_message
    
    # Default themes
    LIGHT_THEME = "light"
    DARK_THEME = "dark"
    
    def __init__(
        self,
        event_bus: EventBus,
        config_manager: ConfigManager,
        state_manager: StateManager,
        parent: Optional[QObject] = None
    ):
        super().__init__(event_bus, config_manager, state_manager, parent)
        
        # Theme storage
        self._themes: Dict[str, ThemeColors] = {}
        self._stylesheets: Dict[str, str] = {}
        self._current_theme: str = self.LIGHT_THEME
        self._previous_theme: str = self.LIGHT_THEME
        
        # Theme callbacks
        self._theme_callbacks: List[Callable[[str], None]] = []
        
        # Theme transition
        self._transition_timer: Optional[QTimer] = None
        self._transition_steps: int = 10
        self._transition_duration: int = 200  # milliseconds
        
        # Icon management
        self._themed_icons: Dict[str, Dict[str, QIcon]] = {}  # icon_name -> theme -> icon
        
        # Settings
        self._settings = QSettings("ToreMatrix", "ToreMatrixV3")
        
        # Setup themes
        self._setup_builtin_themes()
        self._load_stylesheets()
        
    def _setup_component(self) -> None:
        """Setup the theme management system."""
        # Load saved theme preference
        self._load_theme_preference()
        
        # Subscribe to system theme changes
        self._event_bus.subscribe("system.theme_changed", self._handle_system_theme_change)
        
        logger.info("Theme manager initialized")
    
    def _setup_builtin_themes(self) -> None:
        """Setup built-in theme color schemes."""
        # Light theme colors
        light_colors = ThemeColors(
            # Main colors
            background="#ffffff",
            primary_background="#f8f9fa",
            text="#212529",
            text_disabled="#6c757d",
            
            # Accent colors
            accent="#007bff",
            accent_dark="#0056b3",
            accent_light="#66b3ff",
            
            # UI element colors
            border="#dee2e6",
            button_background="#ffffff",
            button_border="#ced4da",
            button_hover="#e9ecef",
            button_pressed="#dee2e6",
            button_disabled="#f8f9fa",
            
            # Menu colors
            menu_background="#ffffff",
            menu_hover="#007bff",
            menu_separator="#dee2e6",
            
            # Status indicators
            success="#28a745",
            warning="#ffc107",
            error="#dc3545",
            info="#17a2b8"
        )
        
        # Dark theme colors
        dark_colors = ThemeColors(
            # Main colors
            background="#2b2b2b",
            primary_background="#3c3c3c",
            text="#ffffff",
            text_disabled="#888888",
            
            # Accent colors
            accent="#0e639c",
            accent_dark="#0a4d79",
            accent_light="#4d8bc4",
            
            # UI element colors
            border="#555555",
            button_background="#3c3c3c",
            button_border="#555555",
            button_hover="#4a4a4a",
            button_pressed="#555555",
            button_disabled="#2b2b2b",
            
            # Menu colors
            menu_background="#3c3c3c",
            menu_hover="#0e639c",
            menu_separator="#555555",
            
            # Status indicators
            success="#2ea043",
            warning="#d1801a",
            error="#f85149",
            info="#1f6feb"
        )
        
        self._themes[self.LIGHT_THEME] = light_colors
        self._themes[self.DARK_THEME] = dark_colors
    
    def _load_stylesheets(self) -> None:
        """Load stylesheet files."""
        styles_dir = Path(__file__).parent / "styles"
        
        # Load built-in stylesheets
        for theme_name in [self.LIGHT_THEME, self.DARK_THEME]:
            stylesheet_path = styles_dir / f"{theme_name}.qss"
            if stylesheet_path.exists():
                try:
                    with open(stylesheet_path, 'r', encoding='utf-8') as f:
                        stylesheet = f.read()
                    self._stylesheets[theme_name] = stylesheet
                    logger.debug(f"Loaded stylesheet for {theme_name} theme")
                except Exception as e:
                    logger.error(f"Failed to load stylesheet for {theme_name}: {e}")
    
    def load_theme(self, theme_name: str) -> bool:
        """Load and apply a theme."""
        if theme_name not in self._themes:
            logger.error(f"Theme '{theme_name}' not found")
            self.theme_error.emit(theme_name, f"Theme '{theme_name}' not found")
            return False
        
        try:
            self.theme_loading.emit(theme_name)
            
            # Store previous theme
            self._previous_theme = self._current_theme
            self._current_theme = theme_name
            
            # Apply theme
            self._apply_theme(theme_name)
            
            # Save preference
            self._save_theme_preference(theme_name)
            
            # Notify callbacks
            for callback in self._theme_callbacks:
                try:
                    callback(theme_name)
                except Exception as e:
                    logger.error(f"Theme callback error: {e}")
            
            # Emit signals
            self.theme_loaded.emit(theme_name)
            self.theme_changed.emit(theme_name)
            
            # Publish event
            self.publish_event("theme.changed", {
                "theme": theme_name,
                "previous_theme": self._previous_theme
            })
            
            logger.info(f"Theme '{theme_name}' applied successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load theme '{theme_name}': {e}")
            self.theme_error.emit(theme_name, str(e))
            return False
    
    def _apply_theme(self, theme_name: str) -> None:
        """Apply theme to the application."""
        # Get application instance
        app = QApplication.instance()
        if not app:
            raise RuntimeError("No QApplication instance found")
        
        # Apply stylesheet
        if theme_name in self._stylesheets:
            app.setStyleSheet(self._stylesheets[theme_name])
        
        # Update application palette for better integration
        palette = self._create_palette_from_theme(theme_name)
        if palette:
            app.setPalette(palette)
    
    def _create_palette_from_theme(self, theme_name: str) -> Optional[QPalette]:
        """Create QPalette from theme colors."""
        if theme_name not in self._themes:
            return None
        
        colors = self._themes[theme_name]
        palette = QPalette()
        
        # Set palette colors
        palette.setColor(QPalette.ColorRole.Window, QColor(colors.background))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(colors.text))
        palette.setColor(QPalette.ColorRole.Base, QColor(colors.background))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(colors.primary_background))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(colors.menu_background))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(colors.text))
        palette.setColor(QPalette.ColorRole.Text, QColor(colors.text))
        palette.setColor(QPalette.ColorRole.Button, QColor(colors.button_background))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(colors.text))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(colors.accent_light))
        palette.setColor(QPalette.ColorRole.Link, QColor(colors.accent))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(colors.accent))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
        
        # Disabled colors
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(colors.text_disabled))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(colors.text_disabled))
        palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(colors.text_disabled))
        
        return palette
    
    def apply_theme(self, widget: QWidget, theme_name: str) -> bool:
        """Apply theme to a specific widget."""
        if theme_name not in self._themes:
            return False
        
        try:
            if theme_name in self._stylesheets:
                widget.setStyleSheet(self._stylesheets[theme_name])
            return True
        except Exception as e:
            logger.error(f"Failed to apply theme to widget: {e}")
            return False
    
    def toggle_theme(self) -> str:
        """Toggle between light and dark themes."""
        if self._current_theme == self.LIGHT_THEME:
            new_theme = self.DARK_THEME
        else:
            new_theme = self.LIGHT_THEME
        
        self.load_theme(new_theme)
        return new_theme
    
    def get_current_theme(self) -> str:
        """Get the current theme name."""
        return self._current_theme
    
    def get_previous_theme(self) -> str:
        """Get the previous theme name."""
        return self._previous_theme
    
    def get_available_themes(self) -> List[str]:
        """Get list of available theme names."""
        return list(self._themes.keys())
    
    def register_theme_change_callback(self, callback: Callable[[str], None]) -> None:
        """Register callback for theme changes."""
        if callback not in self._theme_callbacks:
            self._theme_callbacks.append(callback)
    
    def unregister_theme_change_callback(self, callback: Callable[[str], None]) -> None:
        """Unregister theme change callback."""
        if callback in self._theme_callbacks:
            self._theme_callbacks.remove(callback)
    
    def get_theme_icon(self, icon_name: str, size: Optional[int] = None) -> QIcon:
        """Get themed icon."""
        # Check if we have a themed version
        if icon_name in self._themed_icons and self._current_theme in self._themed_icons[icon_name]:
            return self._themed_icons[icon_name][self._current_theme]
        
        # Load icon from appropriate theme directory
        theme_dir = "dark" if self._current_theme == self.DARK_THEME else "light"
        icon_path = Path(__file__).parent / "icons" / theme_dir / f"{icon_name}.svg"
        
        if icon_path.exists():
            icon = QIcon(str(icon_path))
        else:
            # Fallback to default icon directory
            fallback_path = Path(__file__).parent / "icons" / f"{icon_name}.svg"
            icon = QIcon(str(fallback_path)) if fallback_path.exists() else QIcon()
        
        # Cache the icon
        if icon_name not in self._themed_icons:
            self._themed_icons[icon_name] = {}
        self._themed_icons[icon_name][self._current_theme] = icon
        
        return icon
    
    def get_theme_color(self, color_role: str) -> QColor:
        """Get color from current theme."""
        if self._current_theme not in self._themes:
            return QColor()
        
        colors = self._themes[self._current_theme]
        color_value = getattr(colors, color_role, None)
        
        if color_value:
            return QColor(color_value)
        
        return QColor()
    
    def register_custom_theme(self, theme_name: str, colors: ThemeColors, stylesheet: str = "") -> bool:
        """Register a custom theme."""
        try:
            self._themes[theme_name] = colors
            if stylesheet:
                self._stylesheets[theme_name] = stylesheet
            
            logger.info(f"Custom theme '{theme_name}' registered")
            return True
        except Exception as e:
            logger.error(f"Failed to register custom theme '{theme_name}': {e}")
            return False
    
    def get_theme_colors(self, theme_name: Optional[str] = None) -> Optional[ThemeColors]:
        """Get colors for a theme (current theme if none specified)."""
        theme_name = theme_name or self._current_theme
        return self._themes.get(theme_name)
    
    def _load_theme_preference(self) -> None:
        """Load saved theme preference."""
        saved_theme = self._settings.value("theme/current", self.LIGHT_THEME, str)
        if saved_theme in self._themes:
            self._current_theme = saved_theme
            self._apply_theme(saved_theme)
    
    def _save_theme_preference(self, theme_name: str) -> None:
        """Save theme preference."""
        self._settings.setValue("theme/current", theme_name)
    
    def _handle_system_theme_change(self, event_data: Dict[str, Any]) -> None:
        """Handle system theme change event."""
        system_theme = event_data.get("theme", "light")
        
        # Only auto-switch if user hasn't manually set a preference
        auto_switch = self._settings.value("theme/auto_switch", True, bool)
        if auto_switch:
            target_theme = self.DARK_THEME if system_theme == "dark" else self.LIGHT_THEME
            if target_theme != self._current_theme:
                self.load_theme(target_theme)
    
    def set_auto_theme_switching(self, enabled: bool) -> None:
        """Enable or disable automatic theme switching based on system theme."""
        self._settings.setValue("theme/auto_switch", enabled)
        
        if enabled:
            # Trigger immediate check
            self.publish_event("system.check_theme", {})
    
    def is_auto_theme_switching(self) -> bool:
        """Check if auto theme switching is enabled."""
        return self._settings.value("theme/auto_switch", True, bool)
    
    def export_theme(self, theme_name: str, file_path: Path) -> bool:
        """Export theme to file."""
        if theme_name not in self._themes:
            return False
        
        try:
            import json
            
            colors = self._themes[theme_name]
            stylesheet = self._stylesheets.get(theme_name, "")
            
            theme_data = {
                "name": theme_name,
                "colors": {
                    field.name: getattr(colors, field.name)
                    for field in colors.__dataclass_fields__.values()
                },
                "stylesheet": stylesheet
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(theme_data, f, indent=2)
            
            logger.info(f"Theme '{theme_name}' exported to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export theme '{theme_name}': {e}")
            return False
    
    def import_theme(self, file_path: Path) -> Optional[str]:
        """Import theme from file."""
        try:
            import json
            
            with open(file_path, 'r', encoding='utf-8') as f:
                theme_data = json.load(f)
            
            theme_name = theme_data.get("name", file_path.stem)
            colors_data = theme_data.get("colors", {})
            stylesheet = theme_data.get("stylesheet", "")
            
            # Create ThemeColors instance
            colors = ThemeColors(**colors_data)
            
            # Register theme
            if self.register_custom_theme(theme_name, colors, stylesheet):
                logger.info(f"Theme '{theme_name}' imported from {file_path}")
                return theme_name
            
        except Exception as e:
            logger.error(f"Failed to import theme from {file_path}: {e}")
        
        return None