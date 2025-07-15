"""Property Validation Framework

Core validation framework for property panel with extensible validation rules,
real-time validation, and comprehensive error reporting. Provides a foundation
for all validation needs in the property editing system.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable, Union, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re
import json
from datetime import datetime
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget

from torematrix.core.models.element import ElementModel
from torematrix.core.models.types import TypeDefinition


class ValidationSeverity(Enum):
    """Validation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationMessage:
    """Individual validation message"""
    message: str
    severity: ValidationSeverity
    field: Optional[str] = None
    code: Optional[str] = None
    suggestion: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ValidationResult:
    """Comprehensive validation result with detailed feedback"""
    is_valid: bool
    messages: List[ValidationMessage] = field(default_factory=list)
    field_errors: Dict[str, List[ValidationMessage]] = field(default_factory=dict)
    warnings: List[ValidationMessage] = field(default_factory=list)
    info: List[ValidationMessage] = field(default_factory=list)
    performance_ms: Optional[float] = None
    validation_timestamp: datetime = field(default_factory=datetime.now)
    
    def add_message(self, message: ValidationMessage) -> None:
        """Add a validation message"""
        self.messages.append(message)
        
        # Categorize by severity
        if message.severity == ValidationSeverity.ERROR or message.severity == ValidationSeverity.CRITICAL:
            self.is_valid = False
        elif message.severity == ValidationSeverity.WARNING:
            self.warnings.append(message)
        elif message.severity == ValidationSeverity.INFO:
            self.info.append(message)
        
        # Categorize by field
        if message.field:
            if message.field not in self.field_errors:
                self.field_errors[message.field] = []
            self.field_errors[message.field].append(message)
    
    def add_error(self, message: str, field: Optional[str] = None, 
                  code: Optional[str] = None, suggestion: Optional[str] = None) -> None:
        """Add an error message"""
        msg = ValidationMessage(
            message=message,
            severity=ValidationSeverity.ERROR,
            field=field,
            code=code,
            suggestion=suggestion
        )
        self.add_message(msg)
    
    def add_warning(self, message: str, field: Optional[str] = None,
                    code: Optional[str] = None, suggestion: Optional[str] = None) -> None:
        """Add a warning message"""
        msg = ValidationMessage(
            message=message,
            severity=ValidationSeverity.WARNING,
            field=field,
            code=code,
            suggestion=suggestion
        )
        self.add_message(msg)
    
    def add_info(self, message: str, field: Optional[str] = None,
                 code: Optional[str] = None) -> None:
        """Add an info message"""
        msg = ValidationMessage(
            message=message,
            severity=ValidationSeverity.INFO,
            field=field,
            code=code
        )
        self.add_message(msg)
    
    def get_error_count(self) -> int:
        """Get count of error messages"""
        return len([m for m in self.messages 
                   if m.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]])
    
    def get_warning_count(self) -> int:
        """Get count of warning messages"""
        return len([m for m in self.messages if m.severity == ValidationSeverity.WARNING])
    
    def get_field_messages(self, field: str) -> List[ValidationMessage]:
        """Get all messages for a specific field"""
        return self.field_errors.get(field, [])
    
    def has_field_errors(self, field: str) -> bool:
        """Check if field has any error messages"""
        field_messages = self.get_field_messages(field)
        return any(m.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] 
                  for m in field_messages)
    
    def get_summary(self) -> str:
        """Get validation summary text"""
        if self.is_valid:
            if self.warnings:
                return f"Valid with {len(self.warnings)} warnings"
            return "Valid"
        else:
            error_count = self.get_error_count()
            warning_count = self.get_warning_count()
            summary = f"{error_count} errors"
            if warning_count > 0:
                summary += f", {warning_count} warnings"
            return summary


class PropertyValidator(ABC):
    """Abstract base class for property validators"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.enabled = True
        self.priority = 0  # Higher priority runs first
    
    @abstractmethod
    def validate(self, value: Any, context: Dict[str, Any] = None) -> ValidationResult:
        """Validate a property value
        
        Args:
            value: The value to validate
            context: Additional validation context (element, field info, etc.)
            
        Returns:
            ValidationResult with validation outcome
        """
        pass
    
    def is_applicable(self, context: Dict[str, Any] = None) -> bool:
        """Check if validator applies to the given context
        
        Args:
            context: Validation context
            
        Returns:
            True if validator should be applied
        """
        return self.enabled
    
    def get_error_code(self) -> str:
        """Get unique error code for this validator"""
        return f"validator_{self.name.lower().replace(' ', '_')}"


class RequiredValidator(PropertyValidator):
    """Validates that a value is not empty/None"""
    
    def __init__(self):
        super().__init__("Required", "Value must not be empty")
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        
        # Check if value is empty
        if value is None:
            result.add_error("This field is required", code="required")
        elif isinstance(value, str) and not value.strip():
            result.add_error("This field cannot be empty", code="required")
        elif isinstance(value, (list, dict)) and len(value) == 0:
            result.add_error("This field must contain at least one item", code="required")
        
        return result


class TypeValidator(PropertyValidator):
    """Validates value type"""
    
    def __init__(self, expected_type: Union[type, Tuple[type, ...]], 
                 allow_none: bool = False):
        self.expected_type = expected_type
        self.allow_none = allow_none
        type_name = getattr(expected_type, '__name__', str(expected_type))
        super().__init__(f"Type ({type_name})", f"Value must be of type {type_name}")
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        
        if value is None and self.allow_none:
            return result
        
        if not isinstance(value, self.expected_type):
            expected_name = getattr(self.expected_type, '__name__', str(self.expected_type))
            actual_name = type(value).__name__
            result.add_error(
                f"Expected {expected_name}, got {actual_name}",
                code="type_mismatch",
                suggestion=f"Convert value to {expected_name}"
            )
        
        return result


class RangeValidator(PropertyValidator):
    """Validates numeric ranges"""
    
    def __init__(self, min_value: Optional[float] = None, 
                 max_value: Optional[float] = None,
                 inclusive: bool = True):
        self.min_value = min_value
        self.max_value = max_value
        self.inclusive = inclusive
        
        name_parts = []
        if min_value is not None:
            op = ">=" if inclusive else ">"
            name_parts.append(f"{op} {min_value}")
        if max_value is not None:
            op = "<=" if inclusive else "<"
            name_parts.append(f"{op} {max_value}")
        
        name = f"Range ({', '.join(name_parts)})"
        super().__init__(name, f"Value must be within specified range")
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        
        if value is None:
            return result
        
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            result.add_error("Value must be numeric for range validation", code="not_numeric")
            return result
        
        if self.min_value is not None:
            if self.inclusive and num_value < self.min_value:
                result.add_error(
                    f"Value must be >= {self.min_value}",
                    code="below_minimum",
                    suggestion=f"Use a value of at least {self.min_value}"
                )
            elif not self.inclusive and num_value <= self.min_value:
                result.add_error(
                    f"Value must be > {self.min_value}",
                    code="below_minimum",
                    suggestion=f"Use a value greater than {self.min_value}"
                )
        
        if self.max_value is not None:
            if self.inclusive and num_value > self.max_value:
                result.add_error(
                    f"Value must be <= {self.max_value}",
                    code="above_maximum",
                    suggestion=f"Use a value of at most {self.max_value}"
                )
            elif not self.inclusive and num_value >= self.max_value:
                result.add_error(
                    f"Value must be < {self.max_value}",
                    code="above_maximum",
                    suggestion=f"Use a value less than {self.max_value}"
                )
        
        return result


class LengthValidator(PropertyValidator):
    """Validates string/collection length"""
    
    def __init__(self, min_length: Optional[int] = None,
                 max_length: Optional[int] = None):
        self.min_length = min_length
        self.max_length = max_length
        
        name_parts = []
        if min_length is not None:
            name_parts.append(f"min {min_length}")
        if max_length is not None:
            name_parts.append(f"max {max_length}")
        
        name = f"Length ({', '.join(name_parts)})"
        super().__init__(name, "Value length must be within specified range")
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        
        if value is None:
            return result
        
        try:
            length = len(value)
        except TypeError:
            result.add_error("Value must have a length", code="no_length")
            return result
        
        if self.min_length is not None and length < self.min_length:
            result.add_error(
                f"Length must be at least {self.min_length} characters",
                code="too_short",
                suggestion=f"Add {self.min_length - length} more characters"
            )
        
        if self.max_length is not None and length > self.max_length:
            result.add_error(
                f"Length must not exceed {self.max_length} characters",
                code="too_long",
                suggestion=f"Remove {length - self.max_length} characters"
            )
        
        return result


class RegexValidator(PropertyValidator):
    """Validates string against regular expression"""
    
    def __init__(self, pattern: str, description: str = ""):
        self.pattern = pattern
        self.regex = re.compile(pattern)
        name = f"Pattern ({pattern})"
        super().__init__(name, description or f"Value must match pattern: {pattern}")
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        
        if value is None:
            return result
        
        if not isinstance(value, str):
            result.add_error("Value must be a string for pattern validation", code="not_string")
            return result
        
        if not self.regex.match(value):
            result.add_error(
                f"Value does not match required pattern",
                code="pattern_mismatch",
                suggestion=f"Use format matching: {self.pattern}"
            )
        
        return result


class ChoiceValidator(PropertyValidator):
    """Validates value is from allowed choices"""
    
    def __init__(self, choices: List[Any], case_sensitive: bool = True):
        self.choices = choices
        self.case_sensitive = case_sensitive
        super().__init__(f"Choice", f"Value must be one of: {', '.join(map(str, choices))}")
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> ValidationResult:
        result = ValidationResult(is_valid=True)
        
        if value is None:
            return result
        
        choices_to_check = self.choices
        value_to_check = value
        
        if not self.case_sensitive and isinstance(value, str):
            choices_to_check = [str(c).lower() for c in self.choices]
            value_to_check = value.lower()
        
        if value_to_check not in choices_to_check:
            result.add_error(
                f"Value must be one of: {', '.join(map(str, self.choices))}",
                code="invalid_choice",
                suggestion=f"Choose from: {', '.join(map(str, self.choices))}"
            )
        
        return result


class ValidationEngine(QObject):
    """Main validation engine for property validation"""
    
    # Signals
    validation_started = pyqtSignal(str)  # field_name
    validation_completed = pyqtSignal(str, ValidationResult)  # field_name, result
    validation_error = pyqtSignal(str, str)  # field_name, error_message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Validator registry
        self.validators: Dict[str, PropertyValidator] = {}
        self.field_validators: Dict[str, List[str]] = {}  # field -> validator names
        self.global_validators: List[str] = []  # Always applied
        
        # Performance settings
        self.max_validation_time_ms = 50  # Target <50ms validation time
        self.enable_performance_logging = True
        
        # Debouncing for real-time validation
        self.validation_timer = QTimer()
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self._perform_pending_validation)
        self.pending_validations: Dict[str, Any] = {}
        self.debounce_delay_ms = 300
        
        # Setup default validators
        self._register_default_validators()
    
    def _register_default_validators(self):
        """Register default validators"""
        self.register_validator("required", RequiredValidator())
        self.register_validator("string_type", TypeValidator(str, allow_none=True))
        self.register_validator("int_type", TypeValidator(int, allow_none=True))
        self.register_validator("float_type", TypeValidator(float, allow_none=True))
        self.register_validator("bool_type", TypeValidator(bool, allow_none=True))
    
    def register_validator(self, name: str, validator: PropertyValidator) -> None:
        """Register a validator
        
        Args:
            name: Unique validator name
            validator: Validator instance
        """
        self.validators[name] = validator
    
    def unregister_validator(self, name: str) -> None:
        """Unregister a validator"""
        if name in self.validators:
            del self.validators[name]
        
        # Remove from field mappings
        for field_name, validator_names in self.field_validators.items():
            if name in validator_names:
                validator_names.remove(name)
        
        # Remove from global validators
        if name in self.global_validators:
            self.global_validators.remove(name)
    
    def add_field_validator(self, field_name: str, validator_name: str) -> None:
        """Add validator to a specific field"""
        if field_name not in self.field_validators:
            self.field_validators[field_name] = []
        
        if validator_name not in self.field_validators[field_name]:
            self.field_validators[field_name].append(validator_name)
    
    def remove_field_validator(self, field_name: str, validator_name: str) -> None:
        """Remove validator from a specific field"""
        if field_name in self.field_validators:
            if validator_name in self.field_validators[field_name]:
                self.field_validators[field_name].remove(validator_name)
    
    def add_global_validator(self, validator_name: str) -> None:
        """Add validator that applies to all fields"""
        if validator_name not in self.global_validators:
            self.global_validators.append(validator_name)
    
    def remove_global_validator(self, validator_name: str) -> None:
        """Remove global validator"""
        if validator_name in self.global_validators:
            self.global_validators.remove(validator_name)
    
    def validate_field(self, field_name: str, value: Any, 
                      context: Dict[str, Any] = None) -> ValidationResult:
        """Validate a single field synchronously
        
        Args:
            field_name: Name of the field being validated
            value: Value to validate
            context: Additional validation context
            
        Returns:
            ValidationResult with validation outcome
        """
        start_time = datetime.now()
        self.validation_started.emit(field_name)
        
        try:
            result = ValidationResult(is_valid=True)
            
            # Get applicable validators
            validators_to_run = []
            
            # Add global validators
            for validator_name in self.global_validators:
                if validator_name in self.validators:
                    validators_to_run.append(self.validators[validator_name])
            
            # Add field-specific validators
            if field_name in self.field_validators:
                for validator_name in self.field_validators[field_name]:
                    if validator_name in self.validators:
                        validators_to_run.append(self.validators[validator_name])
            
            # Sort by priority (higher first)
            validators_to_run.sort(key=lambda v: v.priority, reverse=True)
            
            # Run validators
            validation_context = context or {}
            validation_context['field_name'] = field_name
            
            for validator in validators_to_run:
                if not validator.is_applicable(validation_context):
                    continue
                
                try:
                    validator_result = validator.validate(value, validation_context)
                    
                    # Merge results
                    result.is_valid = result.is_valid and validator_result.is_valid
                    for message in validator_result.messages:
                        if not message.field:
                            message.field = field_name
                        result.add_message(message)
                
                except Exception as e:
                    result.add_error(
                        f"Validation error: {str(e)}",
                        field=field_name,
                        code="validator_error"
                    )
            
            # Record performance
            end_time = datetime.now()
            result.performance_ms = (end_time - start_time).total_seconds() * 1000
            
            # Log performance if enabled
            if self.enable_performance_logging and result.performance_ms > self.max_validation_time_ms:
                result.add_warning(
                    f"Validation took {result.performance_ms:.1f}ms (target: {self.max_validation_time_ms}ms)",
                    code="performance_warning"
                )
            
            self.validation_completed.emit(field_name, result)
            return result
        
        except Exception as e:
            error_result = ValidationResult(is_valid=False)
            error_result.add_error(f"Validation failed: {str(e)}", field=field_name)
            self.validation_error.emit(field_name, str(e))
            return error_result
    
    def validate_field_async(self, field_name: str, value: Any,
                           context: Dict[str, Any] = None) -> None:
        """Validate field asynchronously with debouncing
        
        Args:
            field_name: Name of the field being validated
            value: Value to validate  
            context: Additional validation context
        """
        # Store pending validation
        self.pending_validations[field_name] = {
            'value': value,
            'context': context or {}
        }
        
        # Restart debounce timer
        self.validation_timer.stop()
        self.validation_timer.start(self.debounce_delay_ms)
    
    def _perform_pending_validation(self):
        """Perform all pending validations"""
        for field_name, validation_data in self.pending_validations.items():
            self.validate_field(
                field_name,
                validation_data['value'],
                validation_data['context']
            )
        
        self.pending_validations.clear()
    
    def validate_element(self, element: ElementModel) -> ValidationResult:
        """Validate an entire element
        
        Args:
            element: Element to validate
            
        Returns:
            Combined ValidationResult for all fields
        """
        combined_result = ValidationResult(is_valid=True)
        
        # Validate each property
        for prop_name, prop_value in element.properties.items():
            context = {
                'element': element,
                'element_type': element.type_id,
                'property_name': prop_name
            }
            
            field_result = self.validate_field(prop_name, prop_value, context)
            
            # Merge results
            combined_result.is_valid = combined_result.is_valid and field_result.is_valid
            for message in field_result.messages:
                combined_result.add_message(message)
        
        return combined_result
    
    def get_validator_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all registered validators"""
        info = {}
        for name, validator in self.validators.items():
            info[name] = {
                'name': validator.name,
                'description': validator.description,
                'enabled': validator.enabled,
                'priority': validator.priority,
                'error_code': validator.get_error_code()
            }
        return info
    
    def configure_debouncing(self, delay_ms: int) -> None:
        """Configure debouncing delay for real-time validation"""
        self.debounce_delay_ms = max(100, delay_ms)  # Minimum 100ms
    
    def set_performance_target(self, target_ms: float) -> None:
        """Set performance target for validation"""
        self.max_validation_time_ms = target_ms