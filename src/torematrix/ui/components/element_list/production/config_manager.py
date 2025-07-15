"""
Configuration Manager for Hierarchical Element List

Provides configuration management for element list settings,
preferences, and runtime parameters.
"""

import logging
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ElementListConfigManager(QObject):
    """
    Configuration manager for element list settings
    
    Manages user preferences, performance settings,
    and runtime configuration for the element list.
    """
    
    # Signals
    config_changed = pyqtSignal(str, object)  # setting_name, new_value
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        # Default configuration
        self._config = {
            "performance": {
                "enable_lazy_loading": True,
                "virtual_scrolling": True,
                "cache_size": 1000,
                "animation_duration": 250
            },
            "ui": {
                "show_breadcrumbs": True,
                "enable_search": True,
                "auto_expand_search_results": True,
                "theme": "default"
            },
            "accessibility": {
                "enable_screen_reader": True,
                "high_contrast": False,
                "keyboard_shortcuts": True
            }
        }
        
        logger.info("ElementListConfigManager initialized")
    
    def get_setting(self, key: str, default=None):
        """Get configuration setting"""
        keys = key.split(".")
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except KeyError:
            return default
    
    def set_setting(self, key: str, value: Any):
        """Set configuration setting"""
        keys = key.split(".")
        config = self._config
        
        # Navigate to parent
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set value
        config[keys[-1]] = value
        
        self.config_changed.emit(key, value)
        logger.debug(f"Setting {key} = {value}")
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all configuration settings"""
        return self._config.copy()