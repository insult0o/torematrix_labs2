"""
Runtime configuration API with path-based access and advanced query capabilities.

This module provides a high-level API for accessing and manipulating configuration
with advanced features like path-based queries, subscriptions, and validation.
"""

import re
import fnmatch
from typing import Dict, Any, Optional, List, Union, Callable, Set, Type, TypeVar, Generic
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from enum import Enum
import weakref

from .runtime import RuntimeConfigurationManager
from .events import ConfigurationEventEmitter, ConfigEventType
from .types import ConfigDict, ConfigSource
from .exceptions import ConfigurationError, ConfigurationAccessError

T = TypeVar('T')


class QueryOperator(Enum):
    """Configuration query operators."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    EXISTS = "exists"
    TYPE_IS = "type_is"
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_EQUAL = "gte"
    LESS_EQUAL = "lte"
    IN = "in"
    NOT_IN = "not_in"


@dataclass
class ConfigQuery:
    """Configuration query specification."""
    path: str
    operator: QueryOperator
    value: Any = None
    case_sensitive: bool = True
    
    def matches(self, config_value: Any) -> bool:
        """Check if a configuration value matches this query."""
        try:
            if self.operator == QueryOperator.EXISTS:
                return config_value is not None
            
            if config_value is None:
                return False
            
            if self.operator == QueryOperator.EQUALS:
                return config_value == self.value
            
            elif self.operator == QueryOperator.NOT_EQUALS:
                return config_value != self.value
            
            elif self.operator == QueryOperator.TYPE_IS:
                return type(config_value).__name__ == self.value
            
            elif self.operator == QueryOperator.GREATER_THAN:
                return config_value > self.value
            
            elif self.operator == QueryOperator.LESS_THAN:
                return config_value < self.value
            
            elif self.operator == QueryOperator.GREATER_EQUAL:
                return config_value >= self.value
            
            elif self.operator == QueryOperator.LESS_EQUAL:
                return config_value <= self.value
            
            elif self.operator == QueryOperator.IN:
                return config_value in self.value
            
            elif self.operator == QueryOperator.NOT_IN:
                return config_value not in self.value
            
            # String operations
            if isinstance(config_value, str):
                search_value = str(self.value)
                
                if not self.case_sensitive:
                    config_value = config_value.lower()
                    search_value = search_value.lower()
                
                if self.operator == QueryOperator.CONTAINS:
                    return search_value in config_value
                
                elif self.operator == QueryOperator.STARTS_WITH:
                    return config_value.startswith(search_value)
                
                elif self.operator == QueryOperator.ENDS_WITH:
                    return config_value.endswith(search_value)
                
                elif self.operator == QueryOperator.REGEX:
                    flags = 0 if self.case_sensitive else re.IGNORECASE
                    return bool(re.search(search_value, config_value, flags))
            
            return False
            
        except Exception:
            return False


@dataclass
class ConfigSubscription:
    """Configuration change subscription."""
    id: str
    path_pattern: str
    callback: Callable[[str, Any, Any], None]
    query: Optional[ConfigQuery] = None
    active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    trigger_count: int = 0


class ConfigurationAPI:
    """
    High-level configuration API with advanced query and subscription capabilities.
    
    Features:
    - Path-based configuration access with dot notation
    - Pattern matching for configuration keys
    - Subscription system for change notifications
    - Query-based configuration filtering
    - Type-safe configuration access
    - Validation and constraint checking
    """
    
    def __init__(self, runtime_manager: RuntimeConfigurationManager):
        """
        Initialize configuration API.
        
        Args:
            runtime_manager: Runtime configuration manager instance
        """
        self._runtime_manager = runtime_manager
        self._subscriptions: Dict[str, ConfigSubscription] = {}
        self._subscription_counter = 0
        self._path_cache: Dict[str, Any] = {}
        self._cache_valid = True
        
        # Setup change notifications to invalidate cache
        self._runtime_manager._event_emitter.add_change_callback(self._handle_config_change)
    
    def get(self, path: str, default: Any = None, type_hint: Optional[Type[T]] = None) -> Union[Any, T]:
        """
        Get configuration value by path with optional type checking.
        
        Args:
            path: Dot-notation path (e.g., 'database.host')
            default: Default value if path not found
            type_hint: Expected type for validation
            
        Returns:
            Configuration value or default
            
        Raises:
            ConfigurationAccessError: If type validation fails
        """
        value = self._runtime_manager.get(path, default)
        
        if type_hint and value is not default:
            if not isinstance(value, type_hint):
                raise ConfigurationAccessError(
                    path,
                    f"Expected type {type_hint.__name__}, got {type(value).__name__}"
                )
        
        return value
    
    def set(self, path: str, value: Any, source: ConfigSource = ConfigSource.RUNTIME) -> None:
        """
        Set configuration value by path.
        
        Args:
            path: Dot-notation path
            value: Value to set
            source: Configuration source
        """
        self._runtime_manager.set(path, value, source)
        self._invalidate_cache()
    
    def exists(self, path: str) -> bool:
        """
        Check if configuration path exists.
        
        Args:
            path: Dot-notation path
            
        Returns:
            True if path exists
        """
        try:
            value = self._runtime_manager.get(path, object())
            return value is not object()
        except Exception:
            return False
    
    def delete(self, path: str) -> bool:
        """
        Delete configuration value by path.
        
        Args:
            path: Dot-notation path
            
        Returns:
            True if value was deleted
        """
        # This is a simplified implementation
        # A full implementation would need to modify the underlying config structure
        try:
            if self.exists(path):
                # Set to None as a deletion marker
                self.set(path, None)
                return True
            return False
        except Exception:
            return False
    
    def get_paths(self, pattern: str = "*") -> List[str]:
        """
        Get all configuration paths matching a pattern.
        
        Args:
            pattern: Glob pattern for path matching
            
        Returns:
            List of matching paths
        """
        if not self._cache_valid:
            self._rebuild_path_cache()
        
        if pattern == "*":
            return list(self._path_cache.keys())
        
        return [path for path in self._path_cache.keys() if fnmatch.fnmatch(path, pattern)]
    
    def query(self, queries: Union[ConfigQuery, List[ConfigQuery]]) -> Dict[str, Any]:
        """
        Query configuration values based on criteria.
        
        Args:
            queries: Single query or list of queries
            
        Returns:
            Dictionary of matching path-value pairs
        """
        if isinstance(queries, ConfigQuery):
            queries = [queries]
        
        if not self._cache_valid:
            self._rebuild_path_cache()
        
        results = {}
        
        for path, value in self._path_cache.items():
            for query in queries:
                # Check if path matches query path pattern
                if fnmatch.fnmatch(path, query.path):
                    if query.matches(value):
                        results[path] = value
                        break
        
        return results
    
    def get_section(self, path_prefix: str) -> Dict[str, Any]:
        """
        Get all configuration values under a path prefix.
        
        Args:
            path_prefix: Path prefix (e.g., 'database')
            
        Returns:
            Dictionary of configuration values
        """
        if not self._cache_valid:
            self._rebuild_path_cache()
        
        prefix = f"{path_prefix}."
        section = {}
        
        for path, value in self._path_cache.items():
            if path.startswith(prefix):
                relative_path = path[len(prefix):]
                section[relative_path] = value
        
        return section
    
    def get_typed(self, path: str, type_class: Type[T], default: Optional[T] = None) -> T:
        """
        Get configuration value with type validation and conversion.
        
        Args:
            path: Dot-notation path
            type_class: Expected type class
            default: Default value if path not found
            
        Returns:
            Typed configuration value
            
        Raises:
            ConfigurationAccessError: If type conversion fails
        """
        value = self.get(path, default)
        
        if value is None and default is not None:
            return default
        
        try:
            if isinstance(value, type_class):
                return value
            
            # Attempt type conversion
            if type_class == bool and isinstance(value, str):
                return value.lower() in ('true', '1', 'yes', 'on')
            
            return type_class(value)
            
        except (ValueError, TypeError) as e:
            raise ConfigurationAccessError(
                path,
                f"Cannot convert value '{value}' to type {type_class.__name__}: {e}"
            )
    
    def subscribe(self,
                 path_pattern: str,
                 callback: Callable[[str, Any, Any], None],
                 query: Optional[ConfigQuery] = None) -> str:
        """
        Subscribe to configuration changes matching a pattern.
        
        Args:
            path_pattern: Glob pattern for paths to watch
            callback: Function called with (path, old_value, new_value)
            query: Optional query filter for values
            
        Returns:
            Subscription ID
        """
        self._subscription_counter += 1
        subscription_id = f"sub_{self._subscription_counter}"
        
        subscription = ConfigSubscription(
            id=subscription_id,
            path_pattern=path_pattern,
            callback=callback,
            query=query
        )
        
        self._subscriptions[subscription_id] = subscription
        
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Remove a configuration subscription.
        
        Args:
            subscription_id: Subscription ID to remove
            
        Returns:
            True if subscription was removed
        """
        if subscription_id in self._subscriptions:
            del self._subscriptions[subscription_id]
            return True
        return False
    
    def pause_subscription(self, subscription_id: str) -> bool:
        """Pause a configuration subscription."""
        if subscription_id in self._subscriptions:
            self._subscriptions[subscription_id].active = False
            return True
        return False
    
    def resume_subscription(self, subscription_id: str) -> bool:
        """Resume a configuration subscription."""
        if subscription_id in self._subscriptions:
            self._subscriptions[subscription_id].active = True
            return True
        return False
    
    def get_subscriptions(self) -> List[Dict[str, Any]]:
        """Get information about all subscriptions."""
        return [
            {
                "id": sub.id,
                "path_pattern": sub.path_pattern,
                "active": sub.active,
                "created_at": sub.created_at.isoformat(),
                "trigger_count": sub.trigger_count,
                "has_query": sub.query is not None
            }
            for sub in self._subscriptions.values()
        ]
    
    def validate_path(self, path: str, value: Any) -> List[str]:
        """
        Validate a configuration path and value.
        
        Args:
            path: Configuration path
            value: Configuration value
            
        Returns:
            List of validation errors
        """
        errors = []
        
        # Basic path validation
        if not path or not isinstance(path, str):
            errors.append("Path must be a non-empty string")
            return errors
        
        if path.startswith('.') or path.endswith('.') or '..' in path:
            errors.append("Path contains invalid dot notation")
        
        # Value type validation (basic)
        if value is not None:
            try:
                # Ensure value is JSON serializable
                import json
                json.dumps(value, default=str)
            except (TypeError, ValueError):
                errors.append(f"Value is not serializable: {type(value)}")
        
        return errors
    
    def get_schema(self, path_pattern: str = "*") -> Dict[str, Any]:
        """
        Get configuration schema for matching paths.
        
        Args:
            path_pattern: Pattern to match paths
            
        Returns:
            Schema information
        """
        if not self._cache_valid:
            self._rebuild_path_cache()
        
        schema = {}
        
        for path in self.get_paths(path_pattern):
            value = self._path_cache[path]
            schema[path] = {
                "type": type(value).__name__ if value is not None else "null",
                "value": value,
                "exists": True
            }
        
        return schema
    
    def export_config(self, path_pattern: str = "*", include_metadata: bool = False) -> Dict[str, Any]:
        """
        Export configuration matching a pattern.
        
        Args:
            path_pattern: Pattern to match paths
            include_metadata: Include metadata about values
            
        Returns:
            Exported configuration
        """
        matching_paths = self.get_paths(path_pattern)
        exported = {}
        
        for path in matching_paths:
            value = self.get(path)
            
            if include_metadata:
                exported[path] = {
                    "value": value,
                    "type": type(value).__name__ if value is not None else "null",
                    "path": path
                }
            else:
                exported[path] = value
        
        return exported
    
    def import_config(self, config_data: Dict[str, Any], source: ConfigSource = ConfigSource.RUNTIME) -> int:
        """
        Import configuration data.
        
        Args:
            config_data: Configuration data to import
            source: Configuration source
            
        Returns:
            Number of configuration values imported
        """
        count = 0
        
        for path, value in config_data.items():
            try:
                self.set(path, value, source)
                count += 1
            except Exception as e:
                # Log error but continue importing
                print(f"Failed to import {path}: {e}")
        
        return count
    
    def get_api_stats(self) -> Dict[str, Any]:
        """Get API usage statistics."""
        return {
            "total_subscriptions": len(self._subscriptions),
            "active_subscriptions": sum(1 for sub in self._subscriptions.values() if sub.active),
            "total_trigger_count": sum(sub.trigger_count for sub in self._subscriptions.values()),
            "cache_valid": self._cache_valid,
            "cached_paths": len(self._path_cache),
            "runtime_info": self._runtime_manager.get_runtime_info()
        }
    
    def _handle_config_change(self, event) -> None:
        """Handle configuration change events."""
        # Invalidate cache
        self._invalidate_cache()
        
        # Extract change information
        if hasattr(event, 'config_key') and event.config_key:
            path = event.config_key
            old_value = getattr(event, 'old_value', None)
            new_value = getattr(event, 'new_value', None)
            
            # Notify matching subscriptions
            self._notify_subscriptions(path, old_value, new_value)
    
    def _notify_subscriptions(self, path: str, old_value: Any, new_value: Any) -> None:
        """Notify subscriptions about configuration changes."""
        for subscription in self._subscriptions.values():
            if not subscription.active:
                continue
            
            # Check if path matches pattern
            if not fnmatch.fnmatch(path, subscription.path_pattern):
                continue
            
            # Apply query filter if present
            if subscription.query and not subscription.query.matches(new_value):
                continue
            
            # Notify callback
            try:
                subscription.callback(path, old_value, new_value)
                subscription.trigger_count += 1
            except Exception as e:
                print(f"Error in subscription callback: {e}")
    
    def _rebuild_path_cache(self) -> None:
        """Rebuild the path cache from current configuration."""
        self._path_cache.clear()
        config = self._runtime_manager._runtime_config.config
        
        self._flatten_config(config, "", self._path_cache)
        self._cache_valid = True
    
    def _flatten_config(self, config: Dict[str, Any], prefix: str, cache: Dict[str, Any]) -> None:
        """Recursively flatten configuration into path-value pairs."""
        for key, value in config.items():
            path = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                # Recursively flatten nested dictionaries
                self._flatten_config(value, path, cache)
            else:
                # Store leaf values
                cache[path] = value
    
    def _invalidate_cache(self) -> None:
        """Invalidate the path cache."""
        self._cache_valid = False


class TypedConfigurationAPI(Generic[T]):
    """
    Type-safe configuration API wrapper.
    
    This provides a type-safe interface for accessing configuration
    with compile-time type checking support.
    """
    
    def __init__(self, api: ConfigurationAPI, config_type: Type[T]):
        """
        Initialize typed configuration API.
        
        Args:
            api: Base configuration API
            config_type: Configuration type class
        """
        self._api = api
        self._config_type = config_type
    
    def get_typed_config(self) -> T:
        """
        Get fully typed configuration object.
        
        Returns:
            Typed configuration instance
            
        Raises:
            ConfigurationError: If configuration cannot be typed
        """
        try:
            config_dict = self._api._runtime_manager._runtime_config.config
            return self._config_type(**config_dict)
        except Exception as e:
            raise ConfigurationError(f"Cannot create typed config: {e}")
    
    def get_section_typed(self, section: str, section_type: Type) -> object:
        """
        Get a typed configuration section.
        
        Args:
            section: Section name
            section_type: Section type class
            
        Returns:
            Typed section instance
        """
        section_data = self._api.get_section(section)
        return section_type(**section_data)
    
    def validate_against_type(self) -> List[str]:
        """
        Validate current configuration against the type.
        
        Returns:
            List of validation errors
        """
        try:
            self.get_typed_config()
            return []
        except Exception as e:
            return [str(e)]