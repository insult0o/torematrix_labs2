"""
Utility functions for configuration management.
"""

import os
import re
from typing import Dict, Any, Union, List, Optional
from pathlib import Path
import json
import yaml
import toml
from configparser import ConfigParser


def merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.
    
    Args:
        base: Base dictionary
        override: Dictionary with values to override
        
    Returns:
        Merged dictionary
    """
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursive merge for nested dicts
            result[key] = merge_dicts(result[key], value)
        else:
            # Direct override
            result[key] = value
    
    return result


def flatten_dict(nested_dict: Dict[str, Any], parent_key: str = '', 
                separator: str = '.') -> Dict[str, Any]:
    """
    Flatten nested dictionary to dot-notation.
    
    Args:
        nested_dict: Nested dictionary
        parent_key: Parent key prefix
        separator: Key separator
        
    Returns:
        Flattened dictionary
    """
    items = []
    
    for key, value in nested_dict.items():
        new_key = f"{parent_key}{separator}{key}" if parent_key else key
        
        if isinstance(value, dict):
            items.extend(flatten_dict(value, new_key, separator).items())
        else:
            items.append((new_key, value))
    
    return dict(items)


def unflatten_dict(flat_dict: Dict[str, Any], separator: str = '.') -> Dict[str, Any]:
    """
    Convert flat dot-notation dictionary to nested structure.
    
    Args:
        flat_dict: Flat dictionary
        separator: Key separator
        
    Returns:
        Nested dictionary
    """
    result = {}
    
    for key, value in flat_dict.items():
        parts = key.split(separator)
        current = result
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    return result


def substitute_env_vars(text: str) -> str:
    """
    Substitute environment variables in text.
    
    Supports formats:
    - ${VAR_NAME}
    - ${VAR_NAME:-default_value}
    - $VAR_NAME
    
    Args:
        text: Text with environment variables
        
    Returns:
        Text with substituted values
    """
    # Pattern for ${VAR} or ${VAR:-default}
    pattern = re.compile(r'\$\{([^}]+)\}')
    
    def replacer(match):
        var_expr = match.group(1)
        
        # Check for default value
        if ':-' in var_expr:
            var_name, default_value = var_expr.split(':-', 1)
        else:
            var_name = var_expr
            default_value = ''
        
        return os.environ.get(var_name.strip(), default_value)
    
    # Replace ${VAR} patterns
    text = pattern.sub(replacer, text)
    
    # Replace simple $VAR patterns
    simple_pattern = re.compile(r'\$([A-Za-z_][A-Za-z0-9_]*)')
    text = simple_pattern.sub(lambda m: os.environ.get(m.group(1), f'${m.group(1)}'), text)
    
    return text


def load_config_file(file_path: Path) -> Dict[str, Any]:
    """
    Load configuration from file based on extension.
    
    Args:
        file_path: Path to configuration file
        
    Returns:
        Configuration dictionary
        
    Raises:
        ValueError: If file format is not supported
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    suffix = file_path.suffix.lower()
    content = file_path.read_text()
    
    # Substitute environment variables
    content = substitute_env_vars(content)
    
    if suffix in ['.yaml', '.yml']:
        return yaml.safe_load(content) or {}
    
    elif suffix == '.json':
        return json.loads(content)
    
    elif suffix == '.toml':
        return toml.loads(content)
    
    elif suffix in ['.ini', '.cfg']:
        parser = ConfigParser()
        parser.read_string(content)
        
        # Convert to dict
        result = {}
        for section in parser.sections():
            result[section] = dict(parser.items(section))
        return result
    
    else:
        raise ValueError(f"Unsupported configuration format: {suffix}")


def save_config_file(config: Dict[str, Any], file_path: Path) -> None:
    """
    Save configuration to file based on extension.
    
    Args:
        config: Configuration dictionary
        file_path: Path to save configuration
        
    Raises:
        ValueError: If file format is not supported
    """
    suffix = file_path.suffix.lower()
    
    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    if suffix in ['.yaml', '.yml']:
        content = yaml.dump(config, default_flow_style=False, allow_unicode=True)
    
    elif suffix == '.json':
        content = json.dumps(config, indent=2, ensure_ascii=False)
    
    elif suffix == '.toml':
        content = toml.dumps(config)
    
    elif suffix in ['.ini', '.cfg']:
        parser = ConfigParser()
        
        # Convert dict to ConfigParser format
        for section, values in config.items():
            if isinstance(values, dict):
                parser.add_section(section)
                for key, value in values.items():
                    parser.set(section, key, str(value))
        
        from io import StringIO
        output = StringIO()
        parser.write(output)
        content = output.getvalue()
    
    else:
        raise ValueError(f"Unsupported configuration format: {suffix}")
    
    file_path.write_text(content)


def get_config_diff(old_config: Dict[str, Any], new_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get differences between two configurations.
    
    Args:
        old_config: Original configuration
        new_config: New configuration
        
    Returns:
        Dictionary with 'added', 'modified', 'removed' keys
    """
    diff = {
        'added': {},
        'modified': {},
        'removed': {}
    }
    
    # Flatten both configs for easier comparison
    old_flat = flatten_dict(old_config)
    new_flat = flatten_dict(new_config)
    
    # Find added and modified
    for key, value in new_flat.items():
        if key not in old_flat:
            diff['added'][key] = value
        elif old_flat[key] != value:
            diff['modified'][key] = {
                'old': old_flat[key],
                'new': value
            }
    
    # Find removed
    for key, value in old_flat.items():
        if key not in new_flat:
            diff['removed'][key] = value
    
    return diff


def mask_sensitive_values(config: Dict[str, Any], 
                         sensitive_keys: List[str] = None) -> Dict[str, Any]:
    """
    Mask sensitive values in configuration.
    
    Args:
        config: Configuration dictionary
        sensitive_keys: List of key patterns to mask
        
    Returns:
        Configuration with masked values
    """
    if sensitive_keys is None:
        sensitive_keys = [
            'password', 'secret', 'key', 'token', 'credential',
            'private', 'auth', 'api_key', 'access_key'
        ]
    
    def should_mask(key: str) -> bool:
        key_lower = key.lower()
        return any(pattern in key_lower for pattern in sensitive_keys)
    
    def mask_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        
        for key, value in d.items():
            if should_mask(key) and value is not None:
                if isinstance(value, str):
                    result[key] = '*' * min(len(value), 8)
                else:
                    result[key] = '***'
            elif isinstance(value, dict):
                result[key] = mask_dict(value)
            else:
                result[key] = value
        
        return result
    
    return mask_dict(config)


def validate_config_schema(config: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """
    Validate configuration against a JSON schema.
    
    Args:
        config: Configuration dictionary
        schema: JSON schema dictionary
        
    Returns:
        List of validation errors
    """
    try:
        import jsonschema
        
        validator = jsonschema.Draft7Validator(schema)
        errors = []
        
        for error in validator.iter_errors(config):
            path = '.'.join(str(p) for p in error.path)
            errors.append(f"{path}: {error.message}")
        
        return errors
        
    except ImportError:
        return ["jsonschema library not installed"]


def resolve_path(path: Union[str, Path], base_path: Optional[Path] = None) -> Path:
    """
    Resolve path relative to base path.
    
    Args:
        path: Path to resolve
        base_path: Base path for relative paths
        
    Returns:
        Resolved absolute path
    """
    path = Path(path)
    
    if path.is_absolute():
        return path
    
    if base_path:
        return base_path / path
    
    return path.resolve()