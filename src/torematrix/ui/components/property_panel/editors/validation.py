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


@dataclass
class ValidationResult:
    """Result of a validation check"""
    is_valid: bool
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