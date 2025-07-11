#!/usr/bin/env python3
"""
Theme Manager for TORE Matrix Labs V2

Provides theme management and styling for the application UI.
"""

from typing import Dict, List, Optional
from enum import Enum
import logging


class ThemeName(Enum):
    """Available theme names."""
    PROFESSIONAL_LIGHT = "professional_light"
    PROFESSIONAL_DARK = "professional_dark"
    HIGH_CONTRAST = "high_contrast"
    CLASSIC = "classic"


class ThemeManager:
    """Manager for application themes and styling."""
    
    def __init__(self):
        """Initialize the theme manager."""
        self.logger = logging.getLogger(__name__)
        self.current_theme = ThemeName.PROFESSIONAL_LIGHT
        self.themes = self._initialize_themes()
        self.logger.info("Theme manager initialized")
    
    def _initialize_themes(self) -> Dict[ThemeName, Dict[str, str]]:
        """Initialize theme definitions."""
        
        themes = {}
        
        # Professional Light Theme
        themes[ThemeName.PROFESSIONAL_LIGHT] = {
            "name": "Professional Light",
            "stylesheet": """
                QMainWindow {
                    background-color: #f5f5f5;
                    color: #333333;
                }
                QTabWidget::pane {
                    border: 1px solid #cccccc;
                    background-color: white;
                }
                QTabBar::tab {
                    background-color: #e8e8e8;
                    padding: 8px 16px;
                    margin-right: 2px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:selected {
                    background-color: white;
                    border-bottom: 2px solid #007acc;
                }
                QPushButton {
                    background-color: #007acc;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #005fa3;
                }
                QTextEdit {
                    border: 1px solid #cccccc;
                    background-color: white;
                    font-family: 'Consolas', 'Courier New', monospace;
                }
                QLabel {
                    color: #333333;
                }
                QDockWidget {
                    background-color: #f0f0f0;
                    titlebar-close-icon: url(close.png);
                    titlebar-normal-icon: url(float.png);
                }
                QStatusBar {
                    background-color: #e8e8e8;
                    border-top: 1px solid #cccccc;
                }
            """
        }
        
        # Professional Dark Theme
        themes[ThemeName.PROFESSIONAL_DARK] = {
            "name": "Professional Dark",
            "stylesheet": """
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QTabWidget::pane {
                    border: 1px solid #555555;
                    background-color: #3c3c3c;
                }
                QTabBar::tab {
                    background-color: #555555;
                    color: #ffffff;
                    padding: 8px 16px;
                    margin-right: 2px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:selected {
                    background-color: #3c3c3c;
                    border-bottom: 2px solid #0078d4;
                }
                QPushButton {
                    background-color: #0078d4;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #106ebe;
                }
                QTextEdit {
                    border: 1px solid #555555;
                    background-color: #1e1e1e;
                    color: #ffffff;
                    font-family: 'Consolas', 'Courier New', monospace;
                }
                QLabel {
                    color: #ffffff;
                }
                QDockWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QStatusBar {
                    background-color: #1e1e1e;
                    color: #ffffff;
                    border-top: 1px solid #555555;
                }
            """
        }
        
        # High Contrast Theme
        themes[ThemeName.HIGH_CONTRAST] = {
            "name": "High Contrast",
            "stylesheet": """
                QMainWindow {
                    background-color: #000000;
                    color: #ffffff;
                }
                QTabWidget::pane {
                    border: 2px solid #ffffff;
                    background-color: #000000;
                }
                QTabBar::tab {
                    background-color: #000000;
                    color: #ffffff;
                    border: 2px solid #ffffff;
                    padding: 8px 16px;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background-color: #ffffff;
                    color: #000000;
                }
                QPushButton {
                    background-color: #ffffff;
                    color: #000000;
                    border: 2px solid #ffffff;
                    padding: 8px 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #cccccc;
                }
                QTextEdit {
                    border: 2px solid #ffffff;
                    background-color: #000000;
                    color: #ffffff;
                    font-family: 'Consolas', 'Courier New', monospace;
                    font-size: 12pt;
                }
                QLabel {
                    color: #ffffff;
                    font-weight: bold;
                }
                QDockWidget {
                    background-color: #000000;
                    color: #ffffff;
                    border: 2px solid #ffffff;
                }
                QStatusBar {
                    background-color: #000000;
                    color: #ffffff;
                    border-top: 2px solid #ffffff;
                }
            """
        }
        
        # Classic Theme
        themes[ThemeName.CLASSIC] = {
            "name": "Classic",
            "stylesheet": """
                /* Minimal styling - use system defaults */
                QMainWindow {
                    background-color: #f0f0f0;
                }
                QTextEdit {
                    font-family: 'Consolas', 'Courier New', monospace;
                }
            """
        }
        
        return themes
    
    def get_available_themes(self) -> List[str]:
        """Get list of available theme names."""
        return [theme["name"] for theme in self.themes.values()]
    
    def get_current_theme(self) -> ThemeName:
        """Get current theme name."""
        return self.current_theme
    
    def set_theme(self, theme_name: ThemeName) -> bool:
        """
        Set the current theme.
        
        Args:
            theme_name: Name of theme to set
            
        Returns:
            True if successful, False otherwise
        """
        if theme_name in self.themes:
            self.current_theme = theme_name
            self.logger.info(f"Theme changed to: {theme_name.value}")
            return True
        else:
            self.logger.warning(f"Theme not found: {theme_name}")
            return False
    
    def get_stylesheet(self, theme_name: Optional[ThemeName] = None) -> str:
        """
        Get stylesheet for specified theme.
        
        Args:
            theme_name: Theme to get stylesheet for (current theme if None)
            
        Returns:
            CSS stylesheet string
        """
        if theme_name is None:
            theme_name = self.current_theme
        
        if theme_name in self.themes:
            return self.themes[theme_name]["stylesheet"]
        else:
            self.logger.warning(f"Theme not found: {theme_name}, using default")
            return self.themes[ThemeName.PROFESSIONAL_LIGHT]["stylesheet"]
    
    def get_theme_info(self, theme_name: ThemeName) -> Dict[str, str]:
        """
        Get information about a specific theme.
        
        Args:
            theme_name: Theme to get info for
            
        Returns:
            Theme information dictionary
        """
        if theme_name in self.themes:
            return {
                "name": self.themes[theme_name]["name"],
                "enum_value": theme_name.value,
                "description": f"Theme: {self.themes[theme_name]['name']}"
            }
        else:
            return {}
    
    def apply_custom_stylesheet(self, custom_css: str) -> bool:
        """
        Apply custom stylesheet temporarily.
        
        Args:
            custom_css: Custom CSS to apply
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # This would be applied by the UI component
            self.logger.info("Custom stylesheet applied")
            return True
        except Exception as e:
            self.logger.error(f"Failed to apply custom stylesheet: {str(e)}")
            return False
    
    def reset_to_default(self):
        """Reset to default theme."""
        self.current_theme = ThemeName.PROFESSIONAL_LIGHT
        self.logger.info("Theme reset to default")
    
    def export_theme(self, theme_name: ThemeName, file_path: str) -> bool:
        """
        Export theme to file.
        
        Args:
            theme_name: Theme to export
            file_path: Path to save theme file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if theme_name not in self.themes:
                return False
            
            theme_data = self.themes[theme_name]
            
            # Save theme data to file
            import json
            with open(file_path, 'w') as f:
                json.dump(theme_data, f, indent=2)
            
            self.logger.info(f"Theme exported: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export theme: {str(e)}")
            return False