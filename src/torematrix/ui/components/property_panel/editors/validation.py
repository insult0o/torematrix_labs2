<<<<<<< HEAD
"""Validation framework for property editors"""

from typing import Any, Optional, Dict, List, Callable, Pattern
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import re
from datetime import datetime


class ValidationSeverity(Enum):
    """Severity levels for validation messages"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
=======
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
>>>>>>> origin/main


@dataclass
class ValidationResult:
    """Result of a validation check"""
    is_valid: bool
<<<<<<< HEAD
    message: Optional[str] = None
    severity: ValidationSeverity = ValidationSeverity.ERROR
    field_name: Optional[str] = None
    error_code: Optional[str] = None
    
    def __bool__(self) -> bool:
        return self.is_valid


class BaseValidator(ABC):
    """Base class for property validators"""
    
    def __init__(self, error_message: Optional[str] = None, 
                 severity: ValidationSeverity = ValidationSeverity.ERROR):
        self.error_message = error_message
        self.severity = severity
    
    @abstractmethod
    def validate(self, value: Any, field_name: Optional[str] = None) -> ValidationResult:
        """Validate a value and return result"""
        pass
    
    def get_error_message(self, field_name: Optional[str] = None) -> str:
        """Get error message for validation failure"""
        if self.error_message:
            return self.error_message
        return self._get_default_error_message(field_name)
    
    @abstractmethod
    def _get_default_error_message(self, field_name: Optional[str] = None) -> str:
        """Get default error message"""
        pass


class RequiredValidator(BaseValidator):
    """Validator for required fields"""
    
    def __init__(self, error_message: Optional[str] = None):
        super().__init__(error_message, ValidationSeverity.ERROR)
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> ValidationResult:
        """Check if value is present and not empty"""
        if value is None:
            return ValidationResult(False, self.get_error_message(field_name), self.severity, field_name, "required")
        
        if isinstance(value, str) and not value.strip():
            return ValidationResult(False, self.get_error_message(field_name), self.severity, field_name, "required")
        
        if isinstance(value, (list, dict, tuple)) and len(value) == 0:
            return ValidationResult(False, self.get_error_message(field_name), self.severity, field_name, "required")
        
        return ValidationResult(True)
    
    def _get_default_error_message(self, field_name: Optional[str] = None) -> str:
        if field_name:
            return f"{field_name} is required"
        return "This field is required"


class LengthValidator(BaseValidator):
    """Validator for string/collection length"""
    
    def __init__(self, min_length: Optional[int] = None, max_length: Optional[int] = None,
                 error_message: Optional[str] = None):
        super().__init__(error_message, ValidationSeverity.ERROR)
        self.min_length = min_length
        self.max_length = max_length
        
        if min_length is not None and max_length is not None and min_length > max_length:
            raise ValueError("min_length cannot be greater than max_length")
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> ValidationResult:
        """Check if value length is within bounds"""
        if value is None:
            length = 0
        elif hasattr(value, '__len__'):
            length = len(value)
        else:
            length = len(str(value))
        
        if self.min_length is not None and length < self.min_length:
            return ValidationResult(False, self.get_error_message(field_name), self.severity, field_name, "min_length")
        
        if self.max_length is not None and length > self.max_length:
            return ValidationResult(False, self.get_error_message(field_name), self.severity, field_name, "max_length")
        
        return ValidationResult(True)
    
    def _get_default_error_message(self, field_name: Optional[str] = None) -> str:
        field = field_name or "Value"
        
        if self.min_length is not None and self.max_length is not None:
            return f"{field} must be between {self.min_length} and {self.max_length} characters"
        elif self.min_length is not None:
            return f"{field} must be at least {self.min_length} characters"
        elif self.max_length is not None:
            return f"{field} must be no more than {self.max_length} characters"
        else:
            return f"{field} length is invalid"


class RangeValidator(BaseValidator):
    """Validator for numeric ranges"""
    
    def __init__(self, min_value: Optional[float] = None, max_value: Optional[float] = None,
                 error_message: Optional[str] = None):
        super().__init__(error_message, ValidationSeverity.ERROR)
        self.min_value = min_value
        self.max_value = max_value
        
        if min_value is not None and max_value is not None and min_value > max_value:
            raise ValueError("min_value cannot be greater than max_value")
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> ValidationResult:
        """Check if numeric value is within range"""
        try:
            numeric_value = float(value)
        except (ValueError, TypeError):
            return ValidationResult(False, "Value must be a number", self.severity, field_name, "not_numeric")
        
        if self.min_value is not None and numeric_value < self.min_value:
            return ValidationResult(False, self.get_error_message(field_name), self.severity, field_name, "min_value")
        
        if self.max_value is not None and numeric_value > self.max_value:
            return ValidationResult(False, self.get_error_message(field_name), self.severity, field_name, "max_value")
        
        return ValidationResult(True)
    
    def _get_default_error_message(self, field_name: Optional[str] = None) -> str:
        field = field_name or "Value"
        
        if self.min_value is not None and self.max_value is not None:
            return f"{field} must be between {self.min_value} and {self.max_value}"
        elif self.min_value is not None:
            return f"{field} must be at least {self.min_value}"
        elif self.max_value is not None:
            return f"{field} must be no more than {self.max_value}"
        else:
            return f"{field} is out of range"


class PatternValidator(BaseValidator):
    """Validator for regex patterns"""
    
    def __init__(self, pattern: str, flags: int = 0, error_message: Optional[str] = None):
        super().__init__(error_message, ValidationSeverity.ERROR)
        self.pattern_str = pattern
        self.pattern = re.compile(pattern, flags)
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> ValidationResult:
        """Check if value matches regex pattern"""
        if value is None:
            return ValidationResult(False, self.get_error_message(field_name), self.severity, field_name, "pattern")
        
        text_value = str(value)
        if not self.pattern.match(text_value):
            return ValidationResult(False, self.get_error_message(field_name), self.severity, field_name, "pattern")
        
        return ValidationResult(True)
    
    def _get_default_error_message(self, field_name: Optional[str] = None) -> str:
        field = field_name or "Value"
        return f"{field} does not match required format"


class EmailValidator(PatternValidator):
    """Validator for email addresses"""
    
    EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    def __init__(self, error_message: Optional[str] = None):
        super().__init__(self.EMAIL_PATTERN, 0, error_message)
    
    def _get_default_error_message(self, field_name: Optional[str] = None) -> str:
        field = field_name or "Email"
        return f"{field} must be a valid email address"


class URLValidator(PatternValidator):
    """Validator for URLs"""
    
    URL_PATTERN = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:\w*))?)?$'
    
    def __init__(self, error_message: Optional[str] = None):
        super().__init__(self.URL_PATTERN, re.IGNORECASE, error_message)
    
    def _get_default_error_message(self, field_name: Optional[str] = None) -> str:
        field = field_name or "URL"
        return f"{field} must be a valid URL"


class TypeValidator(BaseValidator):
    """Validator for specific types"""
    
    def __init__(self, expected_type: type, error_message: Optional[str] = None):
        super().__init__(error_message, ValidationSeverity.ERROR)
        self.expected_type = expected_type
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> ValidationResult:
        """Check if value is of expected type"""
        if not isinstance(value, self.expected_type):
            return ValidationResult(False, self.get_error_message(field_name), self.severity, field_name, "type")
        
        return ValidationResult(True)
    
    def _get_default_error_message(self, field_name: Optional[str] = None) -> str:
        field = field_name or "Value"
        return f"{field} must be of type {self.expected_type.__name__}"


class ChoiceValidator(BaseValidator):
    """Validator for choice/enum values"""
    
    def __init__(self, choices: List[Any], error_message: Optional[str] = None):
        super().__init__(error_message, ValidationSeverity.ERROR)
        self.choices = choices
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> ValidationResult:
        """Check if value is in allowed choices"""
        if value not in self.choices:
            return ValidationResult(False, self.get_error_message(field_name), self.severity, field_name, "choice")
        
        return ValidationResult(True)
    
    def _get_default_error_message(self, field_name: Optional[str] = None) -> str:
        field = field_name or "Value"
        choices_str = ", ".join(str(choice) for choice in self.choices)
        return f"{field} must be one of: {choices_str}"


class CustomValidator(BaseValidator):
    """Validator using custom function"""
    
    def __init__(self, validator_func: Callable[[Any], bool], 
                 error_message: str, severity: ValidationSeverity = ValidationSeverity.ERROR):
        super().__init__(error_message, severity)
        self.validator_func = validator_func
    
    def validate(self, value: Any, field_name: Optional[str] = None) -> ValidationResult:
        """Check value using custom function"""
        try:
            is_valid = self.validator_func(value)
            if not is_valid:
                return ValidationResult(False, self.get_error_message(field_name), self.severity, field_name, "custom")
            return ValidationResult(True)
        except Exception as e:
            return ValidationResult(False, f"Validation error: {str(e)}", ValidationSeverity.ERROR, field_name, "custom_error")
    
    def _get_default_error_message(self, field_name: Optional[str] = None) -> str:
        return self.error_message or "Validation failed"


class ValidationEngine:
    """Engine for running multiple validators"""
    
    def __init__(self):
        self._validators: Dict[str, List[BaseValidator]] = {}
        self._global_validators: List[BaseValidator] = []
    
    def add_validator(self, field_name: str, validator: BaseValidator) -> None:
        """Add validator for specific field"""
        if field_name not in self._validators:
            self._validators[field_name] = []
        self._validators[field_name].append(validator)
    
    def add_global_validator(self, validator: BaseValidator) -> None:
        """Add validator that applies to all fields"""
        self._global_validators.append(validator)
    
    def remove_validators(self, field_name: str) -> None:
        """Remove all validators for a field"""
        if field_name in self._validators:
            del self._validators[field_name]
    
    def clear_validators(self) -> None:
        """Clear all validators"""
        self._validators.clear()
        self._global_validators.clear()
    
    def validate_field(self, field_name: str, value: Any) -> List[ValidationResult]:
        """Validate a single field"""
        results = []
        
        # Run global validators
        for validator in self._global_validators:
            result = validator.validate(value, field_name)
            results.append(result)
        
        # Run field-specific validators
        if field_name in self._validators:
            for validator in self._validators[field_name]:
                result = validator.validate(value, field_name)
                results.append(result)
        
        return results
    
    def validate_all(self, data: Dict[str, Any]) -> Dict[str, List[ValidationResult]]:
        """Validate all fields in data"""
        all_results = {}
        
        # Validate fields with specific validators
        for field_name in self._validators:
            value = data.get(field_name)
            results = self.validate_field(field_name, value)
            if results:
                all_results[field_name] = results
        
        # Validate remaining fields with global validators only
        for field_name, value in data.items():
            if field_name not in all_results and self._global_validators:
                results = []
                for validator in self._global_validators:
                    result = validator.validate(value, field_name)
                    results.append(result)
                if results:
                    all_results[field_name] = results
        
        return all_results
    
    def is_valid(self, field_name: str, value: Any) -> bool:
        """Check if field value is valid"""
        results = self.validate_field(field_name, value)
        return all(result.is_valid for result in results)
    
    def get_first_error(self, field_name: str, value: Any) -> Optional[ValidationResult]:
        """Get first error for field"""
        results = self.validate_field(field_name, value)
        for result in results:
            if not result.is_valid:
                return result
        return None
    
    def get_validators(self, field_name: str) -> List[BaseValidator]:
        """Get validators for a field"""
        validators = self._global_validators.copy()
        if field_name in self._validators:
            validators.extend(self._validators[field_name])
        return validators


class ValidationRuleParser:
    """Parser for validation rules from strings"""
    
    @staticmethod
    def parse_rule(rule_string: str) -> Optional[BaseValidator]:
        """Parse a validation rule string into a validator"""
        rule_string = rule_string.strip()
        
        if rule_string == "required":
            return RequiredValidator()
        
        elif rule_string.startswith("length:"):
            length_spec = rule_string[7:]
            if "-" in length_spec:
                try:
                    min_len, max_len = map(int, length_spec.split("-", 1))
                    return LengthValidator(min_len, max_len)
                except ValueError:
                    pass
            else:
                try:
                    max_len = int(length_spec)
                    return LengthValidator(max_length=max_len)
                except ValueError:
                    pass
        
        elif rule_string.startswith("range:"):
            range_spec = rule_string[6:]
            if "-" in range_spec:
                try:
                    min_val, max_val = map(float, range_spec.split("-", 1))
                    return RangeValidator(min_val, max_val)
                except ValueError:
                    pass
            elif range_spec.startswith(">="):
                try:
                    min_val = float(range_spec[2:])
                    return RangeValidator(min_value=min_val)
                except ValueError:
                    pass
            elif range_spec.startswith("<="):
                try:
                    max_val = float(range_spec[2:])
                    return RangeValidator(max_value=max_val)
                except ValueError:
                    pass
        
        elif rule_string.startswith("pattern:"):
            pattern = rule_string[8:]
            return PatternValidator(pattern)
        
        elif rule_string == "email":
            return EmailValidator()
        
        elif rule_string == "url":
            return URLValidator()
        
        elif rule_string.startswith("type:"):
            type_name = rule_string[5:]
            type_mapping = {
                "string": str,
                "str": str,
                "integer": int,
                "int": int,
                "float": float,
                "number": float,
                "boolean": bool,
                "bool": bool,
                "list": list,
                "dict": dict,
            }
            if type_name in type_mapping:
                return TypeValidator(type_mapping[type_name])
        
        elif rule_string.startswith("choice:"):
            choices_str = rule_string[7:]
            choices = [choice.strip() for choice in choices_str.split(",")]
            return ChoiceValidator(choices)
        
        return None
    
    @staticmethod
    def parse_rules(rule_strings: List[str]) -> List[BaseValidator]:
        """Parse multiple validation rule strings"""
        validators = []
        for rule_string in rule_strings:
            validator = ValidationRuleParser.parse_rule(rule_string)
            if validator:
                validators.append(validator)
        return validators
=======
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
>>>>>>> origin/main
