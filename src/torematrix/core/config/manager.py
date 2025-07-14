"""
Configuration manager implementation with thread-safe operations.
"""

import threading
from typing import Dict, Any, Optional, List, Set, Callable, Union
from pathlib import Path
from datetime import datetime
import json
import copy

from .types import ConfigDict, ConfigSource, ConfigUpdatePolicy
from .models import ApplicationConfig
from .exceptions import (
    ConfigurationError,
    ValidationError,
    ConfigurationAccessError,
    ConfigurationLockError
)


class ConfigurationManager:
    """
    Thread-safe configuration manager with source tracking and validation.
    
    Features:
    - Thread-safe read/write operations
    - Source precedence management
    - Configuration validation
    - Change tracking and history
    - Observer pattern for change notifications
    """
    
    def __init__(self, base_config: Optional[ApplicationConfig] = None):
        """Initialize configuration manager."""
        self._config = base_config or ApplicationConfig()
        self._sources: Dict[ConfigSource, ConfigDict] = {}
        self._lock = threading.RLock()
        self._observers: List[Callable[[str, Any, Any], None]] = []
        self._history: List[Dict[str, Any]] = []
        self._max_history = 100
        self._frozen = False
        self._validation_errors: List[str] = []
        
        # Track configuration metadata
        self._metadata = {
            "created_at": datetime.now(),
            "last_modified": datetime.now(),
            "modification_count": 0,
            "sources_loaded": set()
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.
        
        Args:
            key: Dot-notation key (e.g., 'database.host')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        with self._lock:
            try:
                value = self._config
                for part in key.split('.'):
                    if hasattr(value, part):
                        value = getattr(value, part)
                    elif isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return default
                return value
            except Exception:
                return default
    
    def set(self, key: str, value: Any, source: ConfigSource = ConfigSource.RUNTIME) -> None:
        """
        Set configuration value with source tracking.
        
        Args:
            key: Dot-notation key
            value: Value to set
            source: Configuration source
            
        Raises:
            ConfigurationError: If configuration is frozen
            ValidationError: If value validation fails
        """
        with self._lock:
            if self._frozen:
                raise ConfigurationError("Configuration is frozen and cannot be modified")
            
            # Store old value for history
            old_value = self.get(key)
            
            # Navigate to the parent and set the value
            parts = key.split('.')
            target = self._config
            
            for i, part in enumerate(parts[:-1]):
                if hasattr(target, part):
                    target = getattr(target, part)
                else:
                    raise ConfigurationAccessError(
                        key, f"Path component '{part}' not found"
                    )
            
            # Set the final value
            final_key = parts[-1]
            if hasattr(target, final_key):
                try:
                    setattr(target, final_key, value)
                except Exception as e:
                    # Convert Pydantic ValidationError to our ValidationError
                    if "ValidationError" in str(type(e)):
                        raise ValidationError(f"Invalid value for {key}", [str(e)])
                    raise
            else:
                raise ConfigurationAccessError(
                    key, f"Configuration key '{final_key}' not found"
                )
            
            # Validate after setting
            errors = self._config.validate()
            if errors:
                # Rollback on validation failure
                setattr(target, final_key, old_value)
                raise ValidationError("Configuration validation failed", errors)
            
            # Update metadata
            self._update_metadata(key, old_value, value, source)
            
            # Track source
            if source not in self._sources:
                self._sources[source] = {}
            # Update the source with just this key/value
            keys = key.split('.')
            current = self._sources[source]
            for k in keys[:-1]:
                if k not in current:
                    current[k] = {}
                current = current[k]
            current[keys[-1]] = value
            
            # Notify observers
            self._notify_observers(key, old_value, value)
    
    def update(self, updates: ConfigDict, source: ConfigSource = ConfigSource.RUNTIME,
               policy: ConfigUpdatePolicy = ConfigUpdatePolicy.MERGE) -> None:
        """
        Batch update configuration values.
        
        Args:
            updates: Dictionary of updates
            source: Configuration source
            policy: Update policy (merge or replace)
        """
        with self._lock:
            if self._frozen:
                raise ConfigurationError("Configuration is frozen")
            
            # Store current state for rollback
            old_config = self._config.model_copy(deep=True)
            
            try:
                if policy == ConfigUpdatePolicy.REPLACE:
                    # Replace entire configuration
                    self._config = ApplicationConfig(**updates)
                else:
                    # Merge updates
                    self._merge_updates(updates, policy == ConfigUpdatePolicy.MERGE_DEEP)
                
                # Validate
                errors = self._config.validate()
                if errors:
                    raise ValidationError("Configuration validation failed", errors)
                
                # Update source tracking
                self._sources[source] = updates
                self._metadata["sources_loaded"].add(source.name)
                
            except Exception as e:
                # Rollback on any error
                self._config = old_config
                raise ConfigurationError(f"Update failed: {e}")
    
    def merge(self, config: ConfigDict, source: ConfigSource) -> None:
        """
        Merge configuration from a specific source.
        
        Args:
            config: Configuration dictionary
            source: Configuration source
        """
        self.update(config, source, ConfigUpdatePolicy.MERGE_DEEP)
    
    def validate(self) -> List[str]:
        """
        Validate current configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        with self._lock:
            self._validation_errors = self._config.validate()
            return self._validation_errors.copy()
    
    def freeze(self) -> None:
        """Freeze configuration to prevent further modifications."""
        with self._lock:
            self._frozen = True
    
    def unfreeze(self) -> None:
        """Unfreeze configuration to allow modifications."""
        with self._lock:
            self._frozen = False
    
    def is_frozen(self) -> bool:
        """Check if configuration is frozen."""
        with self._lock:
            return self._frozen
    
    def reset(self) -> None:
        """Reset configuration to defaults."""
        with self._lock:
            if self._frozen:
                raise ConfigurationError("Cannot reset frozen configuration")
            
            old_config = self._config.model_copy(deep=True)
            self._config = ApplicationConfig()
            self._sources.clear()
            self._metadata["sources_loaded"].clear()
            self._metadata["modification_count"] = 0
            
            # Notify about reset
            self._notify_observers("*", old_config, self._config)
    
    def to_dict(self) -> ConfigDict:
        """
        Export configuration as dictionary.
        
        Returns:
            Configuration dictionary
        """
        with self._lock:
            return self._config.to_dict()
    
    def to_json(self, pretty: bool = True) -> str:
        """
        Export configuration as JSON string.
        
        Args:
            pretty: Use pretty printing
            
        Returns:
            JSON string
        """
        config_dict = self.to_dict()
        if pretty:
            return json.dumps(config_dict, indent=2, default=str)
        return json.dumps(config_dict, default=str)
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get configuration metadata."""
        with self._lock:
            return copy.deepcopy(self._metadata)
    
    def get_source_info(self, key: str) -> Optional[ConfigSource]:
        """
        Get the source of a configuration value.
        
        Args:
            key: Configuration key
            
        Returns:
            Configuration source or None
        """
        with self._lock:
            # Check each source in reverse precedence order
            for source in reversed(list(ConfigSource)):
                if source in self._sources:
                    source_config = self._sources[source]
                    if self._key_exists_in_dict(key, source_config):
                        return source
            return None
    
    def add_observer(self, callback: Callable[[str, Any, Any], None]) -> None:
        """
        Add observer for configuration changes.
        
        Args:
            callback: Function called with (key, old_value, new_value)
        """
        with self._lock:
            self._observers.append(callback)
    
    def remove_observer(self, callback: Callable[[str, Any, Any], None]) -> None:
        """Remove configuration change observer."""
        with self._lock:
            if callback in self._observers:
                self._observers.remove(callback)
    
    def get_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get configuration change history.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of change entries
        """
        with self._lock:
            if limit:
                return self._history[-limit:]
            return self._history.copy()
    
    def clear_history(self) -> None:
        """Clear configuration change history."""
        with self._lock:
            self._history.clear()
    
    # Private methods
    
    def _merge_updates(self, updates: ConfigDict, deep: bool = True) -> None:
        """Merge updates into current configuration."""
        for key, value in updates.items():
            if hasattr(self._config, key):
                current = getattr(self._config, key)
                
                if deep and hasattr(current, 'merge') and isinstance(value, dict):
                    # Deep merge for nested configs
                    current.merge(value)
                else:
                    # Simple assignment
                    setattr(self._config, key, value)
    
    def _update_metadata(self, key: str, old_value: Any, new_value: Any,
                        source: ConfigSource) -> None:
        """Update configuration metadata after change."""
        self._metadata["last_modified"] = datetime.now()
        self._metadata["modification_count"] += 1
        
        # Add to history
        history_entry = {
            "timestamp": datetime.now(),
            "key": key,
            "old_value": old_value,
            "new_value": new_value,
            "source": source.name
        }
        
        self._history.append(history_entry)
        
        # Trim history if needed
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def _notify_observers(self, key: str, old_value: Any, new_value: Any) -> None:
        """Notify all observers about configuration change."""
        for observer in self._observers:
            try:
                observer(key, old_value, new_value)
            except Exception as e:
                # Log error but don't stop notification
                print(f"Observer error: {e}")
    
    def _key_exists_in_dict(self, key: str, data: Dict[str, Any]) -> bool:
        """Check if dot-notation key exists in dictionary."""
        parts = key.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return False
        
        return True