"""Comprehensive validation framework for property editors"""

from typing import List, Any, Optional, Dict, Callable, Union, Pattern
from dataclasses import dataclass
from enum import Enum
import re
from abc import ABC, abstractmethod

from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QColor


class ValidationSeverity(Enum):
    """Validation message severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Result of a validation check"""
    is_valid: bool
    severity: ValidationSeverity
    message: str
    field_name: Optional[str] = None
    suggestion: Optional[str] = None
    
    @classmethod
    def success(cls, message: str = "Valid") -> 'ValidationResult':
        """Create successful validation result"""
        return cls(True, ValidationSeverity.INFO, message)
    
    @classmethod
    def error(cls, message: str, suggestion: str = None) -> 'ValidationResult':
        """Create error validation result"""
        return cls(False, ValidationSeverity.ERROR, message, suggestion=suggestion)
    
    @classmethod
    def warning(cls, message: str, suggestion: str = None) -> 'ValidationResult':
        """Create warning validation result"""
        return cls(True, ValidationSeverity.WARNING, message, suggestion=suggestion)


class ValidationRule(ABC):
    """Abstract base class for validation rules"""
    
    def __init__(self, name: str, message: str = "", severity: ValidationSeverity = ValidationSeverity.ERROR):
        self.name = name
        self.message = message or f"Validation failed for rule: {name}"
        self.severity = severity
    
    @abstractmethod
    def validate(self, value: Any) -> ValidationResult:
        """Validate a value against this rule"""
        pass


class RequiredRule(ValidationRule):
    """Rule for required values (non-empty)"""
    
    def __init__(self, message: str = "This field is required"):
        super().__init__("required", message)
    
    def validate(self, value: Any) -> ValidationResult:
        if value is None or value == "" or (isinstance(value, (list, dict)) and len(value) == 0):
            return ValidationResult.error(self.message)
        return ValidationResult.success()


class RangeRule(ValidationRule):
    """Rule for numeric range validation"""
    
    def __init__(self, min_value: Optional[float] = None, max_value: Optional[float] = None, 
                 message: str = ""):
        self.min_value = min_value
        self.max_value = max_value
        if not message:
            if min_value is not None and max_value is not None:
                message = f"Value must be between {min_value} and {max_value}"
            elif min_value is not None:
                message = f"Value must be at least {min_value}"
            elif max_value is not None:
                message = f"Value must be at most {max_value}"
        super().__init__("range", message)
    
    def validate(self, value: Any) -> ValidationResult:
        try:
            num_value = float(value)
            if self.min_value is not None and num_value < self.min_value:
                return ValidationResult.error(self.message, f"Try a value >= {self.min_value}")
            if self.max_value is not None and num_value > self.max_value:
                return ValidationResult.error(self.message, f"Try a value <= {self.max_value}")
            return ValidationResult.success()
        except (ValueError, TypeError):
            return ValidationResult.error("Value must be a number")


class LengthRule(ValidationRule):
    """Rule for string/list length validation"""
    
    def __init__(self, min_length: Optional[int] = None, max_length: Optional[int] = None,
                 message: str = ""):
        self.min_length = min_length
        self.max_length = max_length
        if not message:
            if min_length is not None and max_length is not None:
                message = f"Length must be between {min_length} and {max_length}"
            elif min_length is not None:
                message = f"Length must be at least {min_length}"
            elif max_length is not None:
                message = f"Length must be at most {max_length}"
        super().__init__("length", message)
    
    def validate(self, value: Any) -> ValidationResult:
        try:
            length = len(value) if value is not None else 0
            if self.min_length is not None and length < self.min_length:
                return ValidationResult.error(self.message)
            if self.max_length is not None and length > self.max_length:
                return ValidationResult.error(self.message)
            return ValidationResult.success()
        except TypeError:
            return ValidationResult.error("Value must have a length")


class PatternRule(ValidationRule):
    """Rule for regex pattern validation"""
    
    def __init__(self, pattern: Union[str, Pattern], message: str = "Value does not match required pattern"):
        self.pattern = re.compile(pattern) if isinstance(pattern, str) else pattern
        super().__init__("pattern", message)
    
    def validate(self, value: Any) -> ValidationResult:
        if value is None:
            return ValidationResult.success()  # Allow None unless required
        
        str_value = str(value)
        if self.pattern.match(str_value):
            return ValidationResult.success()
        return ValidationResult.error(self.message)


class EmailRule(PatternRule):
    """Rule for email validation"""
    
    def __init__(self, message: str = "Please enter a valid email address"):
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        super().__init__(email_pattern, message)


class URLRule(PatternRule):
    """Rule for URL validation"""
    
    def __init__(self, message: str = "Please enter a valid URL"):
        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        super().__init__(url_pattern, message)


class CustomRule(ValidationRule):
    """Rule for custom validation functions"""
    
    def __init__(self, validator_func: Callable[[Any], ValidationResult], name: str = "custom"):
        self.validator_func = validator_func
        super().__init__(name)
    
    def validate(self, value: Any) -> ValidationResult:
        return self.validator_func(value)


class PropertyValidator(QObject):
    """Validator for property values with multiple rules"""
    
    validation_completed = pyqtSignal(object)  # ValidationResult
    
    def __init__(self):
        super().__init__()
        self.rules: List[ValidationRule] = []
        self.stop_on_first_error = True
        
    def add_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule"""
        self.rules.append(rule)
    
    def remove_rule(self, rule_name: str) -> None:
        """Remove a validation rule by name"""
        self.rules = [rule for rule in self.rules if rule.name != rule_name]
    
    def clear_rules(self) -> None:
        """Clear all validation rules"""
        self.rules.clear()
    
    def validate(self, value: Any) -> ValidationResult:
        """Validate value against all rules"""
        if not self.rules:
            return ValidationResult.success("No validation rules")
        
        errors = []
        warnings = []
        
        for rule in self.rules:
            result = rule.validate(value)
            
            if not result.is_valid:
                errors.append(result)
                if self.stop_on_first_error:
                    break
            elif result.severity == ValidationSeverity.WARNING:
                warnings.append(result)
        
        # Return first error if any
        if errors:
            result = errors[0]
            self.validation_completed.emit(result)
            return result
        
        # Return first warning if any
        if warnings:
            result = warnings[0]
            self.validation_completed.emit(result)
            return result
        
        # All good
        result = ValidationResult.success("All validations passed")
        self.validation_completed.emit(result)
        return result
    
    def validate_async(self, value: Any) -> None:
        """Validate asynchronously and emit signal"""
        result = self.validate(value)
        self.validation_completed.emit(result)


class ValidationMixin:
    """Mixin class for adding validation to property editors"""
    
    def __init__(self):
        super().__init__()
        self.validator = PropertyValidator()
        self._validation_enabled = True
        self._last_validation_result: Optional[ValidationResult] = None
        
        # Connect validator signal if we're a QObject
        if hasattr(self, 'validation_failed'):
            self.validator.validation_completed.connect(self._on_validation_result)
    
    def _setup_validation(self) -> None:
        """Setup validation rules from configuration"""
        if not hasattr(self, 'config'):
            return
        
        validation_rules = self.config.custom_attributes.get('validation_rules', [])
        
        for rule_config in validation_rules:
            rule = self._create_validation_rule(rule_config)
            if rule:
                self.validator.add_rule(rule)
    
    def _create_validation_rule(self, rule_config: Dict[str, Any]) -> Optional[ValidationRule]:
        """Create validation rule from configuration"""
        rule_type = rule_config.get('type')
        
        if rule_type == 'required':
            return RequiredRule(rule_config.get('message', ''))
        
        elif rule_type == 'range':
            return RangeRule(
                rule_config.get('min_value'),
                rule_config.get('max_value'),
                rule_config.get('message', '')
            )
        
        elif rule_type == 'length':
            return LengthRule(
                rule_config.get('min_length'),
                rule_config.get('max_length'),
                rule_config.get('message', '')
            )
        
        elif rule_type == 'pattern':
            return PatternRule(
                rule_config.get('pattern'),
                rule_config.get('message', '')
            )
        
        elif rule_type == 'email':
            return EmailRule(rule_config.get('message', ''))
        
        elif rule_type == 'url':
            return URLRule(rule_config.get('message', ''))
        
        return None
    
    def _validate_input(self, value: Any) -> bool:
        """Validate input value and update UI state"""
        if not self._validation_enabled:
            return True
        
        result = self.validator.validate(value)
        self._last_validation_result = result
        
        # Update visual state
        self._update_validation_state(result)
        
        return result.is_valid
    
    def _update_validation_state(self, result: ValidationResult) -> None:
        """Update editor visual state based on validation result"""
        if not isinstance(self, QWidget):
            return
        
        # Update style based on validation state
        if result.is_valid:
            if result.severity == ValidationSeverity.WARNING:
                self._set_validation_style("warning")
            else:
                self._set_validation_style("valid")
        else:
            self._set_validation_style("error")
        
        # Update tooltip with validation message
        if result.message:
            tooltip = result.message
            if result.suggestion:
                tooltip += f"\n\nSuggestion: {result.suggestion}"
            self.setToolTip(tooltip)
        else:
            self.setToolTip("")
    
    def _set_validation_style(self, state: str) -> None:
        """Set visual style for validation state"""
        styles = {
            "valid": "border: 1px solid #4CAF50;",
            "warning": "border: 1px solid #FF9800;",
            "error": "border: 1px solid #F44336; background-color: #FFEBEE;"
        }
        
        style = styles.get(state, "")
        self.setStyleSheet(style)
    
    def _on_validation_result(self, result: ValidationResult) -> None:
        """Handle validation result signal"""
        if hasattr(self, 'validation_failed') and not result.is_valid:
            self.validation_failed.emit(result.message)
    
    def set_validation_enabled(self, enabled: bool) -> None:
        """Enable/disable validation"""
        self._validation_enabled = enabled
        if not enabled:
            self._set_validation_style("valid")
            self.setToolTip("")
    
    def get_last_validation_result(self) -> Optional[ValidationResult]:
        """Get the last validation result"""
        return self._last_validation_result
    
    def add_validation_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule"""
        self.validator.add_rule(rule)
    
    def remove_validation_rule(self, rule_name: str) -> None:
        """Remove a validation rule"""
        self.validator.remove_rule(rule_name)


# Validation utilities
class ValidationUtils:
    """Utility functions for common validations"""
    
    @staticmethod
    def is_positive_number(value: Any) -> ValidationResult:
        """Check if value is a positive number"""
        try:
            num = float(value)
            if num > 0:
                return ValidationResult.success()
            return ValidationResult.error("Value must be positive")
        except (ValueError, TypeError):
            return ValidationResult.error("Value must be a number")
    
    @staticmethod
    def is_integer(value: Any) -> ValidationResult:
        """Check if value is an integer"""
        try:
            int(value)
            return ValidationResult.success()
        except (ValueError, TypeError):
            return ValidationResult.error("Value must be an integer")
    
    @staticmethod
    def is_coordinate(value: Any) -> ValidationResult:
        """Check if value is a valid coordinate pair"""
        if isinstance(value, (tuple, list)) and len(value) == 2:
            try:
                float(value[0])
                float(value[1])
                return ValidationResult.success()
            except (ValueError, TypeError):
                pass
        return ValidationResult.error("Value must be a coordinate pair (x, y)")
    
    @staticmethod
    def is_color_hex(value: Any) -> ValidationResult:
        """Check if value is a valid hex color"""
        if isinstance(value, str):
            pattern = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')
            if pattern.match(value):
                return ValidationResult.success()
        return ValidationResult.error("Value must be a valid hex color (e.g., #FF0000)")


# Export validation components
__all__ = [
    'ValidationSeverity',
    'ValidationResult', 
    'ValidationRule',
    'RequiredRule',
    'RangeRule',
    'LengthRule',
    'PatternRule',
    'EmailRule',
    'URLRule',
    'CustomRule',
    'PropertyValidator',
    'ValidationMixin',
    'ValidationUtils'
]
