"""
Configuration validation framework with decorators and custom rules.
"""

import re
from typing import Any, Callable, List, Optional, Dict, Union, Type
from functools import wraps
from pathlib import Path

from .types import ValidationSeverity
from .exceptions import ValidationError


class ValidationRule:
    """Base validation rule class."""
    
    def __init__(self, message: str, severity: ValidationSeverity = ValidationSeverity.ERROR):
        self.message = message
        self.severity = severity
    
    def validate(self, value: Any) -> bool:
        """Validate value. Return True if valid."""
        raise NotImplementedError
    
    def get_error_message(self, field_name: str, value: Any) -> str:
        """Get formatted error message."""
        return f"{field_name}: {self.message} (got: {value})"


class RequiredRule(ValidationRule):
    """Validate that value is not None or empty."""
    
    def __init__(self):
        super().__init__("Field is required")
    
    def validate(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, (str, list, dict)) and len(value) == 0:
            return False
        return True


class TypeRule(ValidationRule):
    """Validate value type."""
    
    def __init__(self, expected_type: Type):
        self.expected_type = expected_type
        super().__init__(f"Must be of type {expected_type.__name__}")
    
    def validate(self, value: Any) -> bool:
        return isinstance(value, self.expected_type)


class RangeRule(ValidationRule):
    """Validate numeric value is within range."""
    
    def __init__(self, min_value: Optional[float] = None, max_value: Optional[float] = None):
        self.min_value = min_value
        self.max_value = max_value
        
        if min_value is not None and max_value is not None:
            message = f"Must be between {min_value} and {max_value}"
        elif min_value is not None:
            message = f"Must be >= {min_value}"
        else:
            message = f"Must be <= {max_value}"
        
        super().__init__(message)
    
    def validate(self, value: Any) -> bool:
        if not isinstance(value, (int, float)):
            return False
        
        if self.min_value is not None and value < self.min_value:
            return False
        if self.max_value is not None and value > self.max_value:
            return False
        
        return True


class LengthRule(ValidationRule):
    """Validate string/collection length."""
    
    def __init__(self, min_length: Optional[int] = None, max_length: Optional[int] = None):
        self.min_length = min_length
        self.max_length = max_length
        
        if min_length is not None and max_length is not None:
            message = f"Length must be between {min_length} and {max_length}"
        elif min_length is not None:
            message = f"Length must be >= {min_length}"
        else:
            message = f"Length must be <= {max_length}"
        
        super().__init__(message)
    
    def validate(self, value: Any) -> bool:
        if not hasattr(value, '__len__'):
            return False
        
        length = len(value)
        
        if self.min_length is not None and length < self.min_length:
            return False
        if self.max_length is not None and length > self.max_length:
            return False
        
        return True


class PatternRule(ValidationRule):
    """Validate string matches regex pattern."""
    
    def __init__(self, pattern: str, message: Optional[str] = None):
        self.pattern = re.compile(pattern)
        super().__init__(message or f"Must match pattern: {pattern}")
    
    def validate(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(self.pattern.match(value))


class ChoiceRule(ValidationRule):
    """Validate value is in allowed choices."""
    
    def __init__(self, choices: List[Any]):
        self.choices = choices
        super().__init__(f"Must be one of: {choices}")
    
    def validate(self, value: Any) -> bool:
        return value in self.choices


class PathRule(ValidationRule):
    """Validate path exists or can be created."""
    
    def __init__(self, must_exist: bool = False, create_if_missing: bool = False):
        self.must_exist = must_exist
        self.create_if_missing = create_if_missing
        
        message = "Path validation failed"
        if must_exist:
            message = "Path must exist"
        
        super().__init__(message)
    
    def validate(self, value: Any) -> bool:
        if not isinstance(value, (str, Path)):
            return False
        
        path = Path(value)
        
        if self.must_exist and not path.exists():
            if self.create_if_missing:
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    return True
                except Exception:
                    return False
            return False
        
        return True


class URLRule(ValidationRule):
    """Validate URL format."""
    
    URL_PATTERN = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    
    def __init__(self):
        super().__init__("Must be a valid URL")
    
    def validate(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(self.URL_PATTERN.match(value))


class EmailRule(ValidationRule):
    """Validate email format."""
    
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    def __init__(self):
        super().__init__("Must be a valid email address")
    
    def validate(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(self.EMAIL_PATTERN.match(value))


class CustomRule(ValidationRule):
    """Custom validation rule with user-defined function."""
    
    def __init__(self, validator: Callable[[Any], bool], message: str):
        self.validator = validator
        super().__init__(message)
    
    def validate(self, value: Any) -> bool:
        try:
            return self.validator(value)
        except Exception:
            return False


class ConfigValidator:
    """Configuration validator with rule management."""
    
    def __init__(self):
        self.rules: Dict[str, List[ValidationRule]] = {}
        self.cross_field_rules: List[Callable[[Dict[str, Any]], List[str]]] = []
    
    def add_rule(self, field: str, rule: ValidationRule) -> None:
        """Add validation rule for a field."""
        if field not in self.rules:
            self.rules[field] = []
        self.rules[field].append(rule)
    
    def add_rules(self, field: str, rules: List[ValidationRule]) -> None:
        """Add multiple validation rules for a field."""
        for rule in rules:
            self.add_rule(field, rule)
    
    def add_cross_field_rule(self, rule: Callable[[Dict[str, Any]], List[str]]) -> None:
        """Add cross-field validation rule."""
        self.cross_field_rules.append(rule)
    
    def validate_field(self, field: str, value: Any) -> List[str]:
        """Validate a single field."""
        errors = []
        
        if field in self.rules:
            for rule in self.rules[field]:
                if not rule.validate(value):
                    errors.append(rule.get_error_message(field, value))
        
        return errors
    
    def validate(self, config: Dict[str, Any]) -> List[str]:
        """Validate entire configuration."""
        errors = []
        
        # Validate individual fields
        for field, rules in self.rules.items():
            value = config.get(field)
            errors.extend(self.validate_field(field, value))
        
        # Run cross-field validations
        for cross_rule in self.cross_field_rules:
            try:
                cross_errors = cross_rule(config)
                errors.extend(cross_errors)
            except Exception as e:
                errors.append(f"Cross-field validation error: {e}")
        
        return errors


# Validation decorators

def validate_field(*rules: ValidationRule):
    """Decorator to add validation rules to a field."""
    def decorator(func):
        if not hasattr(func, '_validation_rules'):
            func._validation_rules = []
        func._validation_rules.extend(rules)
        return func
    return decorator


def validate_config(validator: ConfigValidator):
    """Decorator to validate configuration on method call."""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get configuration dict
            if hasattr(self, 'to_dict'):
                config_dict = self.to_dict()
            else:
                config_dict = self.__dict__
            
            # Validate
            errors = validator.validate(config_dict)
            if errors:
                raise ValidationError("Configuration validation failed", errors)
            
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


# Pre-built validators

def create_default_validator() -> ConfigValidator:
    """Create validator with default rules for ApplicationConfig."""
    validator = ConfigValidator()
    
    # Basic fields
    validator.add_rule("app_name", RequiredRule())
    validator.add_rule("app_name", LengthRule(min_length=1, max_length=100))
    
    validator.add_rule("version", RequiredRule())
    validator.add_rule("version", PatternRule(r'^\d+\.\d+\.\d+(-\w+)?$'))
    
    validator.add_rule("environment", RequiredRule())
    validator.add_rule("environment", ChoiceRule(
        ["development", "testing", "staging", "production"]
    ))
    
    # Paths
    for path_field in ["data_dir", "temp_dir", "log_dir"]:
        validator.add_rule(path_field, PathRule(create_if_missing=True))
    
    # Database
    validator.add_rule("database.type", ChoiceRule(["sqlite", "postgresql", "mongodb"]))
    validator.add_rule("database.port", RangeRule(min_value=1, max_value=65535))
    
    # Performance
    validator.add_rule("performance.worker_threads", RangeRule(min_value=1, max_value=32))
    validator.add_rule("performance.max_memory_usage_percent", RangeRule(
        min_value=50, max_value=95
    ))
    
    # Cross-field validations
    def validate_database_config(config: Dict[str, Any]) -> List[str]:
        errors = []
        db_config = config.get("database", {})
        
        if db_config.get("type") != "sqlite":
            if not db_config.get("user"):
                errors.append("Database user required for non-SQLite databases")
            if not db_config.get("password"):
                errors.append("Database password required for non-SQLite databases")
        
        return errors
    
    validator.add_cross_field_rule(validate_database_config)
    
    return validator