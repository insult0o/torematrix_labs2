# AGENT 3 - ELEMENT PROPERTY PANEL: VALIDATION FRAMEWORK & PERFORMANCE OPTIMIZATION

## 🎯 Your Assignment
You are **Agent 3** responsible for building comprehensive property validation system with real-time validation feedback, performance optimization for large property sets, and advanced validation indicators.

## 📋 Your Specific Tasks

### 1. Property Validation Framework
```python
# src/torematrix/ui/components/property_panel/validators.py
class PropertyValidator:
    """Base class for property validators"""
    
class ValidationEngine:
    """Core validation engine with rule processing"""
    
class ValidationResult:
    """Validation result with detailed feedback"""
    
class ValidationIndicator:
    """Visual validation feedback component"""
```

### 2. Validation Rules System
```python
# src/torematrix/ui/components/property_panel/rules.py
class ValidationRule:
    """Individual validation rule"""
    
class RuleEngine:
    """Validation rule engine and processor"""
    
class RuleBuilder:
    """Builder for creating custom validation rules"""
```

### 3. Visual Validation Indicators
```python
# src/torematrix/ui/components/property_panel/indicators.py
class ValidationIndicatorWidget:
    """Visual validation status indicator"""
    
class ValidationTooltip:
    """Detailed validation error tooltip"""
    
class ValidationHighlight:
    """Property highlighting for validation states"""
```

### 4. Performance Optimization
```python
# src/torematrix/ui/components/property_panel/optimization.py
class PropertyCache:
    """Intelligent property caching system"""
    
class ValidationCache:
    """Validation result caching"""
    
class PerformanceMonitor:
    """Performance monitoring and optimization"""
```

### 5. Property Virtualization
```python
# src/torematrix/ui/components/property_panel/virtualization.py
class PropertyVirtualizer:
    """Property display virtualization for large datasets"""
    
class VirtualScrollArea:
    """Virtual scrolling for property lists"""
```

## 🎯 Detailed Implementation Requirements

### Validation Framework Design
- **Real-time Validation**: Debounced validation with <50ms response time
- **Rule-based Engine**: Extensible validation rules with custom logic
- **Visual Feedback**: Clear validation indicators with accessibility support
- **Error Recovery**: Graceful handling of validation failures

### Performance Optimization
- **Property Caching**: Intelligent caching of property values and metadata
- **Validation Caching**: Cache validation results to avoid recomputation
- **Virtualization**: Display virtualization for 1000+ properties
- **Memory Management**: Efficient memory usage with garbage collection

### Visual Validation System
- **Real-time Indicators**: Immediate visual feedback for validation state
- **Error Messages**: User-friendly error descriptions with suggestions
- **Color Coding**: Consistent color scheme for validation states
- **Accessibility**: Screen reader support and keyboard navigation

### Rule Engine Architecture
- **Extensible Rules**: Plugin-based rule system for custom validation
- **Composite Rules**: Ability to combine multiple validation rules
- **Conditional Logic**: Support for complex conditional validation
- **Performance Optimized**: Fast rule evaluation for real-time feedback

## 🏗️ Files You Must Create

### 1. Property Validation Framework
**File**: `src/torematrix/ui/components/property_panel/validators.py`
```python
"""
Property validation framework providing comprehensive
validation capabilities with real-time feedback.
"""

from typing import Any, List, Dict, Optional, Callable, Union
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget
from dataclasses import dataclass
from enum import Enum
import re
from datetime import datetime

class ValidationSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class ValidationState(Enum):
    VALID = "valid"
    INVALID = "invalid"
    PENDING = "pending"
    UNKNOWN = "unknown"

@dataclass
class ValidationResult:
    """Validation result with detailed feedback"""
    is_valid: bool
    severity: ValidationSeverity = ValidationSeverity.INFO
    message: str = ""
    suggestion: str = ""
    rule_name: str = ""
    property_name: str = ""
    element_id: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "is_valid": self.is_valid,
            "severity": self.severity.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "rule_name": self.rule_name,
            "property_name": self.property_name,
            "element_id": self.element_id,
            "timestamp": self.timestamp.isoformat()
        }

class PropertyValidator(QObject):
    """Base class for property validators"""
    
    validation_completed = pyqtSignal(ValidationResult)
    
    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.name = name
        self._enabled = True
        self._cache_enabled = True
        self._validation_cache: Dict[str, ValidationResult] = {}
    
    def validate(self, value: Any, property_name: str = "", 
                element_id: str = "", context: Dict[str, Any] = None) -> ValidationResult:
        """Validate a property value"""
        cache_key = self._get_cache_key(value, property_name, element_id)
        
        # Check cache first
        if self._cache_enabled and cache_key in self._validation_cache:
            cached_result = self._validation_cache[cache_key]
            # Return cached result if still valid (within 5 minutes)
            if (datetime.now() - cached_result.timestamp).seconds < 300:
                return cached_result
        
        # Perform validation
        result = self._validate_implementation(value, property_name, element_id, context or {})
        result.rule_name = self.name
        result.property_name = property_name
        result.element_id = element_id
        
        # Cache result
        if self._cache_enabled:
            self._validation_cache[cache_key] = result
        
        # Emit signal
        self.validation_completed.emit(result)
        
        return result
    
    def _validate_implementation(self, value: Any, property_name: str, 
                                element_id: str, context: Dict[str, Any]) -> ValidationResult:
        """Override this method in subclasses"""
        return ValidationResult(is_valid=True, message="No validation implemented")
    
    def _get_cache_key(self, value: Any, property_name: str, element_id: str) -> str:
        """Generate cache key for validation result"""
        return f"{self.name}:{element_id}:{property_name}:{hash(str(value))}"
    
    def clear_cache(self) -> None:
        """Clear validation cache"""
        self._validation_cache.clear()
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable this validator"""
        self._enabled = enabled

class ValidationEngine(QObject):
    """Core validation engine with rule processing"""
    
    validation_started = pyqtSignal(str, str)  # element_id, property_name
    validation_completed = pyqtSignal(str, str, ValidationResult)  # element_id, property_name, result
    batch_validation_completed = pyqtSignal(int, int)  # total_count, error_count
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._validators: Dict[str, PropertyValidator] = {}
        self._property_validators: Dict[str, List[str]] = {}  # property_name -> validator_names
        self._validation_timer = QTimer()
        self._validation_timer.setSingleShot(True)
        self._validation_timer.timeout.connect(self._process_pending_validations)
        self._pending_validations: List[tuple] = []
        self._batch_mode = False
        
        # Register default validators
        self._register_default_validators()
    
    def _register_default_validators(self) -> None:
        """Register default property validators"""
        # Required field validator
        self.register_validator(RequiredFieldValidator())
        
        # Text length validator
        self.register_validator(TextLengthValidator())
        
        # Numeric range validator
        self.register_validator(NumericRangeValidator())
        
        # Coordinate validator
        self.register_validator(CoordinateValidator())
        
        # Confidence score validator
        self.register_validator(ConfidenceValidator())
        
        # Choice validator
        self.register_validator(ChoiceValidator())
    
    def register_validator(self, validator: PropertyValidator) -> None:
        """Register a new property validator"""
        self._validators[validator.name] = validator
        validator.validation_completed.connect(self._on_validator_completed)
    
    def unregister_validator(self, validator_name: str) -> None:
        """Unregister a property validator"""
        if validator_name in self._validators:
            validator = self._validators.pop(validator_name)
            validator.validation_completed.disconnect()
    
    def assign_validator_to_property(self, property_name: str, validator_name: str) -> None:
        """Assign a validator to a specific property"""
        if property_name not in self._property_validators:
            self._property_validators[property_name] = []
        if validator_name not in self._property_validators[property_name]:
            self._property_validators[property_name].append(validator_name)
    
    def validate_property(self, element_id: str, property_name: str, value: Any,
                         context: Dict[str, Any] = None, immediate: bool = False) -> ValidationResult:
        """Validate a single property"""
        if immediate or not self._batch_mode:
            return self._validate_immediately(element_id, property_name, value, context)
        else:
            # Add to pending validations
            self._pending_validations.append((element_id, property_name, value, context))
            self._validation_timer.start(100)  # 100ms batch delay
            return ValidationResult(is_valid=True, message="Validation pending...")
    
    def validate_properties_batch(self, property_data: List[tuple]) -> Dict[str, ValidationResult]:
        """Validate multiple properties efficiently"""
        self._batch_mode = True
        results = {}
        
        try:
            for element_id, property_name, value, context in property_data:
                result = self._validate_immediately(element_id, property_name, value, context)
                results[f"{element_id}.{property_name}"] = result
            
            # Emit batch completion signal
            error_count = sum(1 for r in results.values() if not r.is_valid)
            self.batch_validation_completed.emit(len(results), error_count)
            
        finally:
            self._batch_mode = False
        
        return results
    
    def _validate_immediately(self, element_id: str, property_name: str, value: Any,
                             context: Dict[str, Any] = None) -> ValidationResult:
        """Perform immediate validation"""
        self.validation_started.emit(element_id, property_name)
        
        # Get validators for this property
        validator_names = self._property_validators.get(property_name, [])
        if not validator_names:
            # Use all validators if none specifically assigned
            validator_names = list(self._validators.keys())
        
        # Run all validators and collect results
        results = []
        for validator_name in validator_names:
            if validator_name in self._validators:
                validator = self._validators[validator_name]
                if validator._enabled:
                    result = validator.validate(value, property_name, element_id, context)
                    results.append(result)
        
        # Combine results (most severe wins)
        combined_result = self._combine_validation_results(results)
        
        self.validation_completed.emit(element_id, property_name, combined_result)
        return combined_result
    
    def _combine_validation_results(self, results: List[ValidationResult]) -> ValidationResult:
        """Combine multiple validation results into one"""
        if not results:
            return ValidationResult(is_valid=True, message="No validators applied")
        
        # Find most severe result
        severity_order = [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR, 
                         ValidationSeverity.WARNING, ValidationSeverity.INFO]
        
        most_severe = results[0]
        for result in results[1:]:
            if not result.is_valid:
                # Invalid result always takes precedence
                if most_severe.is_valid or severity_order.index(result.severity) < severity_order.index(most_severe.severity):
                    most_severe = result
        
        return most_severe
    
    def _process_pending_validations(self) -> None:
        """Process pending validations in batch"""
        if self._pending_validations:
            results = self.validate_properties_batch(self._pending_validations)
            self._pending_validations.clear()
    
    def _on_validator_completed(self, result: ValidationResult) -> None:
        """Handle individual validator completion"""
        pass  # Additional processing if needed
    
    def clear_all_caches(self) -> None:
        """Clear all validator caches"""
        for validator in self._validators.values():
            validator.clear_cache()

# Default validator implementations

class RequiredFieldValidator(PropertyValidator):
    """Validates that required fields are not empty"""
    
    def __init__(self):
        super().__init__("required_field")
        self.required_properties = {"text", "content", "type"}
    
    def _validate_implementation(self, value: Any, property_name: str, 
                                element_id: str, context: Dict[str, Any]) -> ValidationResult:
        if property_name in self.required_properties:
            if value is None or (isinstance(value, str) and not value.strip()):
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"{property_name} is required and cannot be empty",
                    suggestion="Please provide a value for this field"
                )
        
        return ValidationResult(is_valid=True)

class TextLengthValidator(PropertyValidator):
    """Validates text length constraints"""
    
    def __init__(self):
        super().__init__("text_length")
        self.length_limits = {
            "text": (1, 10000),
            "content": (1, 50000),
            "type": (1, 50)
        }
    
    def _validate_implementation(self, value: Any, property_name: str, 
                                element_id: str, context: Dict[str, Any]) -> ValidationResult:
        if property_name in self.length_limits and isinstance(value, str):
            min_len, max_len = self.length_limits[property_name]
            value_len = len(value)
            
            if value_len < min_len:
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"{property_name} must be at least {min_len} characters",
                    suggestion=f"Current length: {value_len}, minimum: {min_len}"
                )
            elif value_len > max_len:
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"{property_name} must not exceed {max_len} characters",
                    suggestion=f"Current length: {value_len}, maximum: {max_len}"
                )
        
        return ValidationResult(is_valid=True)

class NumericRangeValidator(PropertyValidator):
    """Validates numeric values are within acceptable ranges"""
    
    def __init__(self):
        super().__init__("numeric_range")
        self.range_limits = {
            "x": (0, 10000),
            "y": (0, 10000),
            "width": (1, 10000),
            "height": (1, 10000),
            "confidence": (0.0, 1.0)
        }
    
    def _validate_implementation(self, value: Any, property_name: str, 
                                element_id: str, context: Dict[str, Any]) -> ValidationResult:
        if property_name in self.range_limits and isinstance(value, (int, float)):
            min_val, max_val = self.range_limits[property_name]
            
            if value < min_val:
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"{property_name} must be at least {min_val}",
                    suggestion=f"Current value: {value}, minimum: {min_val}"
                )
            elif value > max_val:
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"{property_name} must not exceed {max_val}",
                    suggestion=f"Current value: {value}, maximum: {max_val}"
                )
        
        return ValidationResult(is_valid=True)

class CoordinateValidator(PropertyValidator):
    """Validates coordinate values and formats"""
    
    def __init__(self):
        super().__init__("coordinate")
    
    def _validate_implementation(self, value: Any, property_name: str, 
                                element_id: str, context: Dict[str, Any]) -> ValidationResult:
        if property_name in {"x", "y", "width", "height"}:
            if not isinstance(value, (int, float)):
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"{property_name} must be a numeric value",
                    suggestion="Please enter a valid number"
                )
            
            if property_name in {"width", "height"} and value <= 0:
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"{property_name} must be greater than zero",
                    suggestion="Dimensions must be positive values"
                )
        
        return ValidationResult(is_valid=True)

class ConfidenceValidator(PropertyValidator):
    """Validates confidence score values"""
    
    def __init__(self):
        super().__init__("confidence")
    
    def _validate_implementation(self, value: Any, property_name: str, 
                                element_id: str, context: Dict[str, Any]) -> ValidationResult:
        if property_name == "confidence":
            if not isinstance(value, (int, float)):
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message="Confidence must be a numeric value",
                    suggestion="Please enter a value between 0.0 and 1.0"
                )
            
            if not (0.0 <= value <= 1.0):
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message="Confidence must be between 0.0 and 1.0",
                    suggestion=f"Current value {value} is out of range"
                )
            
            if value < 0.3:
                return ValidationResult(
                    is_valid=True,
                    severity=ValidationSeverity.WARNING,
                    message="Low confidence score detected",
                    suggestion="Consider reviewing this element for accuracy"
                )
        
        return ValidationResult(is_valid=True)

class ChoiceValidator(PropertyValidator):
    """Validates choice/enum values"""
    
    def __init__(self):
        super().__init__("choice")
        self.valid_choices = {
            "type": {"text", "table", "list", "image", "formula", "code", "header", "footer"}
        }
    
    def _validate_implementation(self, value: Any, property_name: str, 
                                element_id: str, context: Dict[str, Any]) -> ValidationResult:
        if property_name in self.valid_choices:
            valid_options = self.valid_choices[property_name]
            if value not in valid_options:
                return ValidationResult(
                    is_valid=False,
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid {property_name}: {value}",
                    suggestion=f"Valid options: {', '.join(valid_options)}"
                )
        
        return ValidationResult(is_valid=True)
```

### 2. Validation Rules System
**File**: `src/torematrix/ui/components/property_panel/rules.py`
```python
"""
Validation rules system providing extensible
rule-based validation with complex logic support.
"""

from typing import Any, Dict, List, Callable, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import re
import json

class RuleOperator(Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    MATCHES_REGEX = "matches_regex"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"

class RuleCondition(Enum):
    AND = "and"
    OR = "or"
    NOT = "not"

@dataclass
class ValidationRule:
    """Individual validation rule"""
    name: str
    property_name: str
    operator: RuleOperator
    expected_value: Any = None
    error_message: str = ""
    warning_message: str = ""
    suggestion: str = ""
    enabled: bool = True
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def evaluate(self, actual_value: Any, context: Dict[str, Any] = None) -> bool:
        """Evaluate the rule against an actual value"""
        if not self.enabled:
            return True
        
        try:
            return self._apply_operator(actual_value, self.operator, self.expected_value)
        except Exception as e:
            # Rule evaluation error - consider it a failure
            return False
    
    def _apply_operator(self, actual: Any, operator: RuleOperator, expected: Any) -> bool:
        """Apply the rule operator"""
        if operator == RuleOperator.EQUALS:
            return actual == expected
        elif operator == RuleOperator.NOT_EQUALS:
            return actual != expected
        elif operator == RuleOperator.GREATER_THAN:
            return actual > expected
        elif operator == RuleOperator.LESS_THAN:
            return actual < expected
        elif operator == RuleOperator.GREATER_EQUAL:
            return actual >= expected
        elif operator == RuleOperator.LESS_EQUAL:
            return actual <= expected
        elif operator == RuleOperator.CONTAINS:
            return str(expected) in str(actual)
        elif operator == RuleOperator.NOT_CONTAINS:
            return str(expected) not in str(actual)
        elif operator == RuleOperator.STARTS_WITH:
            return str(actual).startswith(str(expected))
        elif operator == RuleOperator.ENDS_WITH:
            return str(actual).endswith(str(expected))
        elif operator == RuleOperator.MATCHES_REGEX:
            return bool(re.match(str(expected), str(actual)))
        elif operator == RuleOperator.IS_EMPTY:
            return not actual or (isinstance(actual, str) and not actual.strip())
        elif operator == RuleOperator.IS_NOT_EMPTY:
            return actual and (not isinstance(actual, str) or actual.strip())
        elif operator == RuleOperator.IN_LIST:
            return actual in expected if isinstance(expected, (list, tuple, set)) else False
        elif operator == RuleOperator.NOT_IN_LIST:
            return actual not in expected if isinstance(expected, (list, tuple, set)) else True
        else:
            raise ValueError(f"Unknown operator: {operator}")
    
    def get_error_message(self, actual_value: Any) -> str:
        """Get formatted error message"""
        if self.error_message:
            return self.error_message.format(
                property_name=self.property_name,
                actual_value=actual_value,
                expected_value=self.expected_value
            )
        else:
            return f"{self.property_name} validation failed"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary for serialization"""
        return {
            "name": self.name,
            "property_name": self.property_name,
            "operator": self.operator.value,
            "expected_value": self.expected_value,
            "error_message": self.error_message,
            "warning_message": self.warning_message,
            "suggestion": self.suggestion,
            "enabled": self.enabled,
            "priority": self.priority,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidationRule':
        """Create rule from dictionary"""
        return cls(
            name=data["name"],
            property_name=data["property_name"],
            operator=RuleOperator(data["operator"]),
            expected_value=data.get("expected_value"),
            error_message=data.get("error_message", ""),
            warning_message=data.get("warning_message", ""),
            suggestion=data.get("suggestion", ""),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 0),
            metadata=data.get("metadata", {})
        )

@dataclass
class CompositeRule:
    """Composite rule combining multiple rules with logical operators"""
    name: str
    condition: RuleCondition
    rules: List[Union[ValidationRule, 'CompositeRule']]
    error_message: str = ""
    enabled: bool = True
    
    def evaluate(self, property_values: Dict[str, Any], context: Dict[str, Any] = None) -> bool:
        """Evaluate composite rule"""
        if not self.enabled or not self.rules:
            return True
        
        if self.condition == RuleCondition.AND:
            return all(self._evaluate_rule(rule, property_values, context) for rule in self.rules)
        elif self.condition == RuleCondition.OR:
            return any(self._evaluate_rule(rule, property_values, context) for rule in self.rules)
        elif self.condition == RuleCondition.NOT:
            # NOT condition applies to the first rule only
            if self.rules:
                return not self._evaluate_rule(self.rules[0], property_values, context)
        
        return True
    
    def _evaluate_rule(self, rule: Union[ValidationRule, 'CompositeRule'], 
                      property_values: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate individual rule or composite rule"""
        if isinstance(rule, ValidationRule):
            actual_value = property_values.get(rule.property_name)
            return rule.evaluate(actual_value, context)
        elif isinstance(rule, CompositeRule):
            return rule.evaluate(property_values, context)
        return True

class RuleEngine:
    """Validation rule engine and processor"""
    
    def __init__(self):
        self._rules: Dict[str, List[ValidationRule]] = {}  # property_name -> rules
        self._composite_rules: Dict[str, CompositeRule] = {}
        self._rule_cache: Dict[str, bool] = {}
        self._cache_enabled = True
    
    def add_rule(self, rule: ValidationRule) -> None:
        """Add a validation rule"""
        property_name = rule.property_name
        if property_name not in self._rules:
            self._rules[property_name] = []
        
        # Insert rule in priority order (higher priority first)
        inserted = False
        for i, existing_rule in enumerate(self._rules[property_name]):
            if rule.priority > existing_rule.priority:
                self._rules[property_name].insert(i, rule)
                inserted = True
                break
        
        if not inserted:
            self._rules[property_name].append(rule)
        
        self._clear_cache()
    
    def remove_rule(self, property_name: str, rule_name: str) -> bool:
        """Remove a validation rule"""
        if property_name in self._rules:
            for i, rule in enumerate(self._rules[property_name]):
                if rule.name == rule_name:
                    self._rules[property_name].pop(i)
                    self._clear_cache()
                    return True
        return False
    
    def add_composite_rule(self, rule: CompositeRule) -> None:
        """Add a composite validation rule"""
        self._composite_rules[rule.name] = rule
        self._clear_cache()
    
    def validate_property(self, property_name: str, value: Any, 
                         context: Dict[str, Any] = None) -> List[ValidationRule]:
        """Validate property and return failed rules"""
        failed_rules = []
        
        if property_name in self._rules:
            for rule in self._rules[property_name]:
                if not rule.evaluate(value, context):
                    failed_rules.append(rule)
        
        return failed_rules
    
    def validate_properties(self, property_values: Dict[str, Any], 
                           context: Dict[str, Any] = None) -> Dict[str, List[ValidationRule]]:
        """Validate multiple properties"""
        results = {}
        
        # Validate individual property rules
        for property_name, value in property_values.items():
            failed_rules = self.validate_property(property_name, value, context)
            if failed_rules:
                results[property_name] = failed_rules
        
        # Validate composite rules
        for composite_rule in self._composite_rules.values():
            if not composite_rule.evaluate(property_values, context):
                # Add composite rule failure to first property it references
                first_property = self._get_first_property_from_composite(composite_rule)
                if first_property:
                    if first_property not in results:
                        results[first_property] = []
                    # Create a pseudo-rule for the composite rule failure
                    pseudo_rule = ValidationRule(
                        name=composite_rule.name,
                        property_name=first_property,
                        operator=RuleOperator.EQUALS,
                        error_message=composite_rule.error_message or f"Composite rule '{composite_rule.name}' failed"
                    )
                    results[first_property].append(pseudo_rule)
        
        return results
    
    def get_rules_for_property(self, property_name: str) -> List[ValidationRule]:
        """Get all rules for a specific property"""
        return self._rules.get(property_name, []).copy()
    
    def get_all_rules(self) -> Dict[str, List[ValidationRule]]:
        """Get all validation rules"""
        return {prop: rules.copy() for prop, rules in self._rules.items()}
    
    def enable_rule(self, property_name: str, rule_name: str, enabled: bool = True) -> bool:
        """Enable or disable a specific rule"""
        if property_name in self._rules:
            for rule in self._rules[property_name]:
                if rule.name == rule_name:
                    rule.enabled = enabled
                    self._clear_cache()
                    return True
        return False
    
    def _get_first_property_from_composite(self, composite_rule: CompositeRule) -> Optional[str]:
        """Get the first property name referenced in a composite rule"""
        for rule in composite_rule.rules:
            if isinstance(rule, ValidationRule):
                return rule.property_name
            elif isinstance(rule, CompositeRule):
                prop = self._get_first_property_from_composite(rule)
                if prop:
                    return prop
        return None
    
    def _clear_cache(self) -> None:
        """Clear the rule cache"""
        self._rule_cache.clear()
    
    def export_rules(self) -> Dict[str, Any]:
        """Export all rules to dictionary"""
        return {
            "property_rules": {
                prop: [rule.to_dict() for rule in rules] 
                for prop, rules in self._rules.items()
            },
            "composite_rules": {
                name: {
                    "name": rule.name,
                    "condition": rule.condition.value,
                    "error_message": rule.error_message,
                    "enabled": rule.enabled,
                    "rules": [r.to_dict() if isinstance(r, ValidationRule) else r.name 
                             for r in rule.rules]
                }
                for name, rule in self._composite_rules.items()
            }
        }
    
    def import_rules(self, rules_data: Dict[str, Any]) -> None:
        """Import rules from dictionary"""
        # Clear existing rules
        self._rules.clear()
        self._composite_rules.clear()
        
        # Import property rules
        property_rules = rules_data.get("property_rules", {})
        for property_name, rule_list in property_rules.items():
            for rule_data in rule_list:
                rule = ValidationRule.from_dict(rule_data)
                self.add_rule(rule)
        
        # Import composite rules (simplified implementation)
        composite_rules = rules_data.get("composite_rules", {})
        for rule_name, rule_data in composite_rules.items():
            # This would need more complex logic to rebuild composite rules
            pass

class RuleBuilder:
    """Builder for creating custom validation rules"""
    
    def __init__(self):
        self._rule_data = {}
    
    def for_property(self, property_name: str) -> 'RuleBuilder':
        """Set the property name for the rule"""
        self._rule_data["property_name"] = property_name
        return self
    
    def named(self, name: str) -> 'RuleBuilder':
        """Set the rule name"""
        self._rule_data["name"] = name
        return self
    
    def must_equal(self, value: Any) -> 'RuleBuilder':
        """Value must equal the specified value"""
        self._rule_data["operator"] = RuleOperator.EQUALS
        self._rule_data["expected_value"] = value
        return self
    
    def must_not_equal(self, value: Any) -> 'RuleBuilder':
        """Value must not equal the specified value"""
        self._rule_data["operator"] = RuleOperator.NOT_EQUALS
        self._rule_data["expected_value"] = value
        return self
    
    def must_be_greater_than(self, value: Union[int, float]) -> 'RuleBuilder':
        """Value must be greater than the specified value"""
        self._rule_data["operator"] = RuleOperator.GREATER_THAN
        self._rule_data["expected_value"] = value
        return self
    
    def must_be_less_than(self, value: Union[int, float]) -> 'RuleBuilder':
        """Value must be less than the specified value"""
        self._rule_data["operator"] = RuleOperator.LESS_THAN
        self._rule_data["expected_value"] = value
        return self
    
    def must_contain(self, text: str) -> 'RuleBuilder':
        """Value must contain the specified text"""
        self._rule_data["operator"] = RuleOperator.CONTAINS
        self._rule_data["expected_value"] = text
        return self
    
    def must_not_be_empty(self) -> 'RuleBuilder':
        """Value must not be empty"""
        self._rule_data["operator"] = RuleOperator.IS_NOT_EMPTY
        return self
    
    def must_match_regex(self, pattern: str) -> 'RuleBuilder':
        """Value must match the specified regex pattern"""
        self._rule_data["operator"] = RuleOperator.MATCHES_REGEX
        self._rule_data["expected_value"] = pattern
        return self
    
    def must_be_in(self, values: List[Any]) -> 'RuleBuilder':
        """Value must be in the specified list"""
        self._rule_data["operator"] = RuleOperator.IN_LIST
        self._rule_data["expected_value"] = values
        return self
    
    def with_error_message(self, message: str) -> 'RuleBuilder':
        """Set custom error message"""
        self._rule_data["error_message"] = message
        return self
    
    def with_suggestion(self, suggestion: str) -> 'RuleBuilder':
        """Set suggestion for fixing the error"""
        self._rule_data["suggestion"] = suggestion
        return self
    
    def with_priority(self, priority: int) -> 'RuleBuilder':
        """Set rule priority (higher numbers = higher priority)"""
        self._rule_data["priority"] = priority
        return self
    
    def build(self) -> ValidationRule:
        """Build the validation rule"""
        required_fields = ["name", "property_name", "operator"]
        for field in required_fields:
            if field not in self._rule_data:
                raise ValueError(f"Missing required field: {field}")
        
        return ValidationRule(
            name=self._rule_data["name"],
            property_name=self._rule_data["property_name"],
            operator=self._rule_data["operator"],
            expected_value=self._rule_data.get("expected_value"),
            error_message=self._rule_data.get("error_message", ""),
            suggestion=self._rule_data.get("suggestion", ""),
            priority=self._rule_data.get("priority", 0)
        )

# Convenience functions for common rules
def required_field_rule(property_name: str) -> ValidationRule:
    """Create a required field rule"""
    return (RuleBuilder()
            .for_property(property_name)
            .named(f"{property_name}_required")
            .must_not_be_empty()
            .with_error_message(f"{property_name} is required")
            .with_suggestion("Please provide a value for this field")
            .build())

def text_length_rule(property_name: str, min_length: int, max_length: int) -> List[ValidationRule]:
    """Create text length validation rules"""
    rules = []
    
    if min_length > 0:
        rules.append(
            RuleBuilder()
            .for_property(property_name)
            .named(f"{property_name}_min_length")
            .must_be_greater_than(min_length - 1)  # length >= min_length
            .with_error_message(f"{property_name} must be at least {min_length} characters")
            .build()
        )
    
    if max_length > 0:
        rules.append(
            RuleBuilder()
            .for_property(property_name)
            .named(f"{property_name}_max_length")
            .must_be_less_than(max_length + 1)  # length <= max_length
            .with_error_message(f"{property_name} must not exceed {max_length} characters")
            .build()
        )
    
    return rules

def numeric_range_rule(property_name: str, min_value: float, max_value: float) -> List[ValidationRule]:
    """Create numeric range validation rules"""
    rules = []
    
    rules.append(
        RuleBuilder()
        .for_property(property_name)
        .named(f"{property_name}_min_value")
        .must_be_greater_than(min_value - 0.001)  # >= min_value
        .with_error_message(f"{property_name} must be at least {min_value}")
        .build()
    )
    
    rules.append(
        RuleBuilder()
        .for_property(property_name)
        .named(f"{property_name}_max_value")
        .must_be_less_than(max_value + 0.001)  # <= max_value
        .with_error_message(f"{property_name} must not exceed {max_value}")
        .build()
    )
    
    return rules
```

### 3. Visual Validation Indicators
**File**: `src/torematrix/ui/components/property_panel/indicators.py`
```python
"""
Visual validation indicators providing clear feedback
on property validation states with accessibility support.
"""

from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (QWidget, QLabel, QHBoxLayout, QVBoxLayout, 
                            QToolTip, QFrame, QPushButton)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QFont
from .validators import ValidationResult, ValidationSeverity, ValidationState

class ValidationIndicatorWidget(QWidget):
    """Visual validation status indicator"""
    
    clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._validation_result: Optional[ValidationResult] = None
        self._state = ValidationState.UNKNOWN
        self._show_text = True
        self._icon_size = 16
        self.setFixedSize(20, 20)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def set_validation_result(self, result: ValidationResult) -> None:
        """Set the validation result to display"""
        self._validation_result = result
        self._state = ValidationState.VALID if result.is_valid else ValidationState.INVALID
        self.update()
        
        # Update tooltip
        if result.message:
            tooltip_text = result.message
            if result.suggestion:
                tooltip_text += f"\n\nSuggestion: {result.suggestion}"
            self.setToolTip(tooltip_text)
        else:
            self.setToolTip("")
    
    def set_state(self, state: ValidationState) -> None:
        """Set validation state directly"""
        self._state = state
        self.update()
    
    def paintEvent(self, event):
        """Custom paint event for validation indicator"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get colors based on state
        bg_color, border_color, icon_color = self._get_state_colors()
        
        # Draw background circle
        painter.fillRect(self.rect(), bg_color)
        
        # Draw border
        painter.setPen(QPen(border_color, 2))
        painter.drawRect(self.rect().adjusted(1, 1, -1, -1))
        
        # Draw icon
        self._draw_state_icon(painter, icon_color)
    
    def _get_state_colors(self) -> tuple:
        """Get colors for current validation state"""
        if self._state == ValidationState.VALID:
            return QColor(76, 175, 80), QColor(56, 142, 60), QColor(255, 255, 255)
        elif self._state == ValidationState.INVALID:
            if self._validation_result and self._validation_result.severity == ValidationSeverity.WARNING:
                return QColor(255, 193, 7), QColor(255, 160, 0), QColor(0, 0, 0)
            else:
                return QColor(244, 67, 54), QColor(211, 47, 47), QColor(255, 255, 255)
        elif self._state == ValidationState.PENDING:
            return QColor(33, 150, 243), QColor(25, 118, 210), QColor(255, 255, 255)
        else:  # UNKNOWN
            return QColor(158, 158, 158), QColor(117, 117, 117), QColor(255, 255, 255)
    
    def _draw_state_icon(self, painter: QPainter, color: QColor) -> None:
        """Draw icon based on validation state"""
        painter.setPen(QPen(color, 2))
        painter.setBrush(color)
        
        center_x = self.width() // 2
        center_y = self.height() // 2
        
        if self._state == ValidationState.VALID:
            # Draw checkmark
            points = [
                QPoint(center_x - 4, center_y),
                QPoint(center_x - 1, center_y + 3),
                QPoint(center_x + 4, center_y - 2)
            ]
            painter.drawPolyline(points)
        
        elif self._state == ValidationState.INVALID:
            if self._validation_result and self._validation_result.severity == ValidationSeverity.WARNING:
                # Draw exclamation mark
                painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "!")
            else:
                # Draw X
                painter.drawLine(center_x - 3, center_y - 3, center_x + 3, center_y + 3)
                painter.drawLine(center_x - 3, center_y + 3, center_x + 3, center_y - 3)
        
        elif self._state == ValidationState.PENDING:
            # Draw question mark
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "?")
        
        else:  # UNKNOWN
            # Draw dash
            painter.drawLine(center_x - 3, center_y, center_x + 3, center_y)
    
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

class ValidationTooltip(QWidget):
    """Detailed validation error tooltip"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._setup_ui()
        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
    
    def _setup_ui(self) -> None:
        """Setup tooltip UI"""
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(8, 6, 8, 6)
        self.layout().setSpacing(4)
        
        # Create frame for styling
        self._frame = QFrame()
        self._frame.setFrameStyle(QFrame.Shape.Box)
        self._frame.setStyleSheet("""
            QFrame {
                background-color: #fffbf0;
                border: 1px solid #f57f17;
                border-radius: 4px;
            }
        """)
        
        frame_layout = QVBoxLayout(self._frame)
        frame_layout.setContentsMargins(8, 6, 8, 6)
        
        # Error message label
        self._message_label = QLabel()
        self._message_label.setWordWrap(True)
        self._message_label.setFont(QFont("", 9))
        frame_layout.addWidget(self._message_label)
        
        # Suggestion label
        self._suggestion_label = QLabel()
        self._suggestion_label.setWordWrap(True)
        self._suggestion_label.setFont(QFont("", 8))
        self._suggestion_label.setStyleSheet("color: #666;")
        frame_layout.addWidget(self._suggestion_label)
        
        self.layout().addWidget(self._frame)
    
    def show_validation_error(self, result: ValidationResult, position: QPoint) -> None:
        """Show validation error at specified position"""
        if not result.message:
            return
        
        # Set message text
        self._message_label.setText(result.message)
        
        # Set suggestion text
        if result.suggestion:
            self._suggestion_label.setText(f"💡 {result.suggestion}")
            self._suggestion_label.show()
        else:
            self._suggestion_label.hide()
        
        # Update frame style based on severity
        style_map = {
            ValidationSeverity.ERROR: {
                "bg": "#ffebee",
                "border": "#f44336"
            },
            ValidationSeverity.WARNING: {
                "bg": "#fff8e1", 
                "border": "#ff9800"
            },
            ValidationSeverity.INFO: {
                "bg": "#e3f2fd",
                "border": "#2196f3"
            }
        }
        
        style = style_map.get(result.severity, style_map[ValidationSeverity.ERROR])
        self._frame.setStyleSheet(f"""
            QFrame {{
                background-color: {style["bg"]};
                border: 1px solid {style["border"]};
                border-radius: 4px;
            }}
        """)
        
        # Position and show tooltip
        self.adjustSize()
        self.move(position)
        self.show()
        
        # Auto-hide after 5 seconds
        self._hide_timer.start(5000)
    
    def hide_tooltip(self) -> None:
        """Hide the tooltip"""
        self.hide()
        self._hide_timer.stop()

class ValidationHighlight(QWidget):
    """Property highlighting for validation states"""
    
    def __init__(self, target_widget: QWidget, parent=None):
        super().__init__(parent)
        self.target_widget = target_widget
        self._validation_state = ValidationState.UNKNOWN
        self._original_style = target_widget.styleSheet()
        self._flash_timer = QTimer()
        self._flash_timer.timeout.connect(self._toggle_flash)
        self._flash_count = 0
        self._flash_visible = False
    
    def set_validation_state(self, state: ValidationState, 
                           severity: ValidationSeverity = ValidationSeverity.ERROR) -> None:
        """Set validation state and update highlighting"""
        self._validation_state = state
        self._apply_highlighting(severity)
    
    def clear_highlighting(self) -> None:
        """Clear all validation highlighting"""
        self._validation_state = ValidationState.UNKNOWN
        self.target_widget.setStyleSheet(self._original_style)
        self._flash_timer.stop()
    
    def flash_error(self, duration: int = 2000) -> None:
        """Flash error highlighting for specified duration"""
        self._flash_count = 0
        self._flash_visible = False
        self._flash_timer.start(100)  # Flash every 100ms
        
        # Stop flashing after duration
        QTimer.singleShot(duration, self._stop_flash)
    
    def _apply_highlighting(self, severity: ValidationSeverity) -> None:
        """Apply highlighting based on validation state"""
        if self._validation_state == ValidationState.VALID:
            # Green border for valid
            style = f"{self._original_style}; border: 2px solid #4caf50;"
        elif self._validation_state == ValidationState.INVALID:
            if severity == ValidationSeverity.WARNING:
                # Orange border for warnings
                style = f"{self._original_style}; border: 2px solid #ff9800;"
            else:
                # Red border for errors
                style = f"{self._original_style}; border: 2px solid #f44336;"
        elif self._validation_state == ValidationState.PENDING:
            # Blue border for pending
            style = f"{self._original_style}; border: 2px solid #2196f3;"
        else:
            # No highlighting for unknown state
            style = self._original_style
        
        self.target_widget.setStyleSheet(style)
    
    def _toggle_flash(self) -> None:
        """Toggle flash highlighting"""
        self._flash_count += 1
        self._flash_visible = not self._flash_visible
        
        if self._flash_visible:
            # Show flash (bright red background)
            style = f"{self._original_style}; background-color: #ffcdd2; border: 2px solid #f44336;"
        else:
            # Hide flash (normal highlighting)
            style = f"{self._original_style}; border: 2px solid #f44336;"
        
        self.target_widget.setStyleSheet(style)
    
    def _stop_flash(self) -> None:
        """Stop flashing animation"""
        self._flash_timer.stop()
        # Apply final highlighting based on current state
        if self._validation_state == ValidationState.INVALID:
            self._apply_highlighting(ValidationSeverity.ERROR)
        else:
            self.clear_highlighting()

class ValidationSummaryWidget(QWidget):
    """Summary widget showing overall validation status"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._validation_counts = {
            ValidationSeverity.ERROR: 0,
            ValidationSeverity.WARNING: 0,
            ValidationSeverity.INFO: 0
        }
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup validation summary UI"""
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(4, 2, 4, 2)
        self.layout().setSpacing(8)
        
        # Error count
        self._error_label = QLabel("Errors: 0")
        self._error_label.setStyleSheet("color: #f44336; font-weight: bold;")
        self.layout().addWidget(self._error_label)
        
        # Warning count
        self._warning_label = QLabel("Warnings: 0")
        self._warning_label.setStyleSheet("color: #ff9800; font-weight: bold;")
        self.layout().addWidget(self._warning_label)
        
        # Info count
        self._info_label = QLabel("Info: 0")
        self._info_label.setStyleSheet("color: #2196f3;")
        self.layout().addWidget(self._info_label)
        
        self.layout().addStretch()
        
        # Overall status
        self._status_label = QLabel("All Valid")
        self._status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
        self.layout().addWidget(self._status_label)
    
    def update_validation_counts(self, results: Dict[str, ValidationResult]) -> None:
        """Update validation counts based on results"""
        # Reset counts
        for severity in self._validation_counts:
            self._validation_counts[severity] = 0
        
        # Count results by severity
        for result in results.values():
            if not result.is_valid:
                self._validation_counts[result.severity] += 1
        
        # Update labels
        self._error_label.setText(f"Errors: {self._validation_counts[ValidationSeverity.ERROR]}")
        self._warning_label.setText(f"Warnings: {self._validation_counts[ValidationSeverity.WARNING]}")
        self._info_label.setText(f"Info: {self._validation_counts[ValidationSeverity.INFO]}")
        
        # Update overall status
        if self._validation_counts[ValidationSeverity.ERROR] > 0:
            self._status_label.setText("Has Errors")
            self._status_label.setStyleSheet("color: #f44336; font-weight: bold;")
        elif self._validation_counts[ValidationSeverity.WARNING] > 0:
            self._status_label.setText("Has Warnings")
            self._status_label.setStyleSheet("color: #ff9800; font-weight: bold;")
        else:
            self._status_label.setText("All Valid")
            self._status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
    
    def get_error_count(self) -> int:
        """Get current error count"""
        return self._validation_counts[ValidationSeverity.ERROR]
    
    def get_warning_count(self) -> int:
        """Get current warning count"""
        return self._validation_counts[ValidationSeverity.WARNING]
    
    def has_errors(self) -> bool:
        """Check if there are any validation errors"""
        return self._validation_counts[ValidationSeverity.ERROR] > 0
```

### 4. Performance Optimization System
**File**: `src/torematrix/ui/components/property_panel/optimization.py`
```python
"""
Performance optimization system providing intelligent
caching, memory management, and performance monitoring.
"""

from typing import Dict, Any, List, Optional, Callable, Set
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
import time
import weakref
from collections import OrderedDict
from datetime import datetime, timedelta
import psutil
import threading

class PropertyCache:
    """Intelligent property caching system"""
    
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl = timedelta(seconds=ttl_seconds)
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._access_times: Dict[str, datetime] = {}
        self._hit_count = 0
        self._miss_count = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self._cache:
            # Check if expired
            if key in self._access_times:
                if datetime.now() - self._access_times[key] > self.ttl:
                    self._remove(key)
                    self._miss_count += 1
                    return None
            
            # Move to end (most recently used)
            value = self._cache.pop(key)
            self._cache[key] = value
            self._access_times[key] = datetime.now()
            self._hit_count += 1
            return value
        
        self._miss_count += 1
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set value in cache"""
        # Remove if already exists
        if key in self._cache:
            self._cache.pop(key)
        
        # Add to cache
        self._cache[key] = value
        self._access_times[key] = datetime.now()
        
        # Evict if over size limit
        while len(self._cache) > self.max_size:
            oldest_key = next(iter(self._cache))
            self._remove(oldest_key)
    
    def remove(self, key: str) -> bool:
        """Remove value from cache"""
        return self._remove(key)
    
    def _remove(self, key: str) -> bool:
        """Internal remove method"""
        if key in self._cache:
            self._cache.pop(key)
            self._access_times.pop(key, None)
            return True
        return False
    
    def clear(self) -> None:
        """Clear all cached values"""
        self._cache.clear()
        self._access_times.clear()
        self._hit_count = 0
        self._miss_count = 0
    
    def cleanup_expired(self) -> int:
        """Remove expired entries and return count removed"""
        now = datetime.now()
        expired_keys = [
            key for key, access_time in self._access_times.items()
            if now - access_time > self.ttl
        ]
        
        for key in expired_keys:
            self._remove(key)
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = self._hit_count + self._miss_count
        hit_ratio = self._hit_count / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hit_count": self._hit_count,
            "miss_count": self._miss_count,
            "hit_ratio": hit_ratio,
            "ttl_seconds": self.ttl.total_seconds()
        }

class ValidationCache(PropertyCache):
    """Specialized cache for validation results"""
    
    def __init__(self, max_size: int = 5000, ttl_seconds: int = 180):
        super().__init__(max_size, ttl_seconds)
        self._validation_count = 0
    
    def get_validation_result(self, element_id: str, property_name: str, 
                            value_hash: str) -> Optional[Any]:
        """Get cached validation result"""
        key = f"{element_id}:{property_name}:{value_hash}"
        return self.get(key)
    
    def set_validation_result(self, element_id: str, property_name: str,
                            value_hash: str, result: Any) -> None:
        """Cache validation result"""
        key = f"{element_id}:{property_name}:{value_hash}"
        self.set(key, result)
        self._validation_count += 1
    
    def invalidate_property(self, element_id: str, property_name: str) -> int:
        """Invalidate all cached results for a property"""
        prefix = f"{element_id}:{property_name}:"
        keys_to_remove = [key for key in self._cache.keys() if key.startswith(prefix)]
        
        for key in keys_to_remove:
            self._remove(key)
        
        return len(keys_to_remove)
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation-specific cache statistics"""
        stats = self.get_stats()
        stats["validation_count"] = self._validation_count
        return stats

class PerformanceMonitor(QObject):
    """Performance monitoring and optimization"""
    
    performance_alert = pyqtSignal(str, dict)  # alert_type, metrics
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._metrics: Dict[str, List[float]] = {
            "property_update_time": [],
            "validation_time": [],
            "render_time": [],
            "memory_usage": []
        }
        self._thresholds = {
            "property_update_time": 100.0,  # ms
            "validation_time": 50.0,        # ms
            "render_time": 16.67,           # ms (60 FPS)
            "memory_usage": 500.0           # MB
        }
        self._monitor_timer = QTimer()
        self._monitor_timer.timeout.connect(self._collect_metrics)
        self._monitor_timer.start(1000)  # Collect every second
        self._alert_cooldown: Dict[str, datetime] = {}
    
    def record_property_update_time(self, duration_ms: float) -> None:
        """Record property update timing"""
        self._add_metric("property_update_time", duration_ms)
        
        if duration_ms > self._thresholds["property_update_time"]:
            self._check_alert("property_update_slow", {
                "duration_ms": duration_ms,
                "threshold_ms": self._thresholds["property_update_time"]
            })
    
    def record_validation_time(self, duration_ms: float) -> None:
        """Record validation timing"""
        self._add_metric("validation_time", duration_ms)
        
        if duration_ms > self._thresholds["validation_time"]:
            self._check_alert("validation_slow", {
                "duration_ms": duration_ms,
                "threshold_ms": self._thresholds["validation_time"]
            })
    
    def record_render_time(self, duration_ms: float) -> None:
        """Record render timing"""
        self._add_metric("render_time", duration_ms)
        
        if duration_ms > self._thresholds["render_time"]:
            self._check_alert("render_slow", {
                "duration_ms": duration_ms,
                "threshold_ms": self._thresholds["render_time"]
            })
    
    def _collect_metrics(self) -> None:
        """Collect system metrics"""
        try:
            # Memory usage
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self._add_metric("memory_usage", memory_mb)
            
            if memory_mb > self._thresholds["memory_usage"]:
                self._check_alert("memory_high", {
                    "memory_mb": memory_mb,
                    "threshold_mb": self._thresholds["memory_usage"]
                })
        except Exception:
            pass  # Ignore monitoring errors
    
    def _add_metric(self, metric_name: str, value: float) -> None:
        """Add metric value with size limiting"""
        if metric_name not in self._metrics:
            self._metrics[metric_name] = []
        
        self._metrics[metric_name].append(value)
        
        # Keep only last 100 values
        if len(self._metrics[metric_name]) > 100:
            self._metrics[metric_name].pop(0)
    
    def _check_alert(self, alert_type: str, metrics: Dict[str, Any]) -> None:
        """Check if alert should be emitted (with cooldown)"""
        now = datetime.now()
        last_alert = self._alert_cooldown.get(alert_type)
        
        # Cooldown period of 30 seconds
        if last_alert is None or now - last_alert > timedelta(seconds=30):
            self._alert_cooldown[alert_type] = now
            self.performance_alert.emit(alert_type, metrics)
    
    def get_metrics_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of all metrics"""
        summary = {}
        
        for metric_name, values in self._metrics.items():
            if values:
                summary[metric_name] = {
                    "current": values[-1],
                    "average": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values)
                }
            else:
                summary[metric_name] = {
                    "current": 0.0,
                    "average": 0.0,
                    "min": 0.0,
                    "max": 0.0,
                    "count": 0
                }
        
        return summary
    
    def set_threshold(self, metric_name: str, threshold: float) -> None:
        """Set performance threshold for a metric"""
        self._thresholds[metric_name] = threshold
    
    def get_thresholds(self) -> Dict[str, float]:
        """Get current performance thresholds"""
        return self._thresholds.copy()

class PropertyCacheManager:
    """Manages multiple caches for different property types"""
    
    def __init__(self):
        self._caches: Dict[str, PropertyCache] = {
            "property_values": PropertyCache(max_size=5000, ttl_seconds=300),
            "property_metadata": PropertyCache(max_size=2000, ttl_seconds=600),
            "validation_results": ValidationCache(max_size=3000, ttl_seconds=180),
            "display_formatting": PropertyCache(max_size=1000, ttl_seconds=120)
        }
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._cleanup_all_caches)
        self._cleanup_timer.start(60000)  # Cleanup every minute
    
    def get_cache(self, cache_name: str) -> Optional[PropertyCache]:
        """Get a specific cache by name"""
        return self._caches.get(cache_name)
    
    def invalidate_element_caches(self, element_id: str) -> int:
        """Invalidate all caches for an element"""
        total_removed = 0
        
        for cache in self._caches.values():
            keys_to_remove = []
            for key in cache._cache.keys():
                if key.startswith(f"{element_id}:"):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                if cache._remove(key):
                    total_removed += 1
        
        return total_removed
    
    def clear_all_caches(self) -> None:
        """Clear all caches"""
        for cache in self._caches.values():
            cache.clear()
    
    def _cleanup_all_caches(self) -> None:
        """Cleanup expired entries in all caches"""
        for cache in self._caches.values():
            cache.cleanup_expired()
    
    def get_cache_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches"""
        return {name: cache.get_stats() for name, cache in self._caches.items()}

class PerformanceOptimizer:
    """Main performance optimization coordinator"""
    
    def __init__(self):
        self.cache_manager = PropertyCacheManager()
        self.monitor = PerformanceMonitor()
        self._optimization_enabled = True
        self._performance_mode = "balanced"  # balanced, speed, memory
        
        # Connect performance alerts
        self.monitor.performance_alert.connect(self._handle_performance_alert)
    
    def set_performance_mode(self, mode: str) -> None:
        """Set performance optimization mode"""
        if mode not in ["balanced", "speed", "memory"]:
            raise ValueError("Mode must be 'balanced', 'speed', or 'memory'")
        
        self._performance_mode = mode
        self._adjust_caches_for_mode()
    
    def _adjust_caches_for_mode(self) -> None:
        """Adjust cache settings based on performance mode"""
        if self._performance_mode == "speed":
            # Optimize for speed - larger caches, longer TTL
            for cache in self.cache_manager._caches.values():
                if hasattr(cache, 'max_size'):
                    cache.max_size = int(cache.max_size * 1.5)
                if hasattr(cache, 'ttl'):
                    cache.ttl = cache.ttl * 2
        
        elif self._performance_mode == "memory":
            # Optimize for memory - smaller caches, shorter TTL
            for cache in self.cache_manager._caches.values():
                if hasattr(cache, 'max_size'):
                    cache.max_size = int(cache.max_size * 0.7)
                if hasattr(cache, 'ttl'):
                    cache.ttl = cache.ttl * 0.5
    
    def _handle_performance_alert(self, alert_type: str, metrics: Dict[str, Any]) -> None:
        """Handle performance alerts"""
        if not self._optimization_enabled:
            return
        
        if alert_type == "memory_high":
            # Clear some caches to free memory
            self.cache_manager.clear_all_caches()
        
        elif alert_type in ["property_update_slow", "validation_slow"]:
            # Reduce cache sizes to improve responsiveness
            for cache in self.cache_manager._caches.values():
                if hasattr(cache, 'max_size'):
                    cache.max_size = max(100, int(cache.max_size * 0.8))
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Get comprehensive optimization report"""
        return {
            "performance_mode": self._performance_mode,
            "optimization_enabled": self._optimization_enabled,
            "cache_stats": self.cache_manager.get_cache_stats(),
            "performance_metrics": self.monitor.get_metrics_summary(),
            "performance_thresholds": self.monitor.get_thresholds()
        }
    
    def enable_optimization(self, enabled: bool = True) -> None:
        """Enable or disable performance optimization"""
        self._optimization_enabled = enabled
```

### 5. Property Virtualization System
**File**: `src/torematrix/ui/components/property_panel/virtualization.py`
```python
"""
Property virtualization system for efficient display
of large property sets with virtual scrolling.
"""

from typing import List, Dict, Any, Optional, Callable
from PyQt6.QtWidgets import (QWidget, QScrollArea, QVBoxLayout, QHBoxLayout,
                            QAbstractScrollArea, QScrollBar, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QTimer, QSize
from PyQt6.QtGui import QPainter, QFontMetrics
import math

class VirtualPropertyItem:
    """Virtual property item for display virtualization"""
    
    def __init__(self, element_id: str, property_name: str, value: Any,
                 property_type: str = "string", height: int = 24):
        self.element_id = element_id
        self.property_name = property_name
        self.value = value
        self.property_type = property_type
        self.height = height
        self.y_position = 0
        self.visible = False
        self.widget: Optional[QWidget] = None

class PropertyVirtualizer(QWidget):
    """Property display virtualization for large datasets"""
    
    item_selected = pyqtSignal(str, str)  # element_id, property_name
    item_value_changed = pyqtSignal(str, str, object)  # element_id, property_name, value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[VirtualPropertyItem] = []
        self._visible_items: Dict[int, VirtualPropertyItem] = {}
        self._item_widgets: Dict[int, QWidget] = {}
        self._item_height = 24
        self._viewport_height = 0
        self._scroll_position = 0
        self._total_height = 0
        self._buffer_items = 5  # Extra items to render outside viewport
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._update_visible_items)
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup virtualization UI"""
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
        
        # Create scroll area
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll_area.verticalScrollBar().valueChanged.connect(self._on_scroll)
        
        # Create content widget
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        
        self._scroll_area.setWidget(self._content_widget)
        self.layout().addWidget(self._scroll_area)
    
    def set_items(self, items: List[VirtualPropertyItem]) -> None:
        """Set the list of items to virtualize"""
        self._items = items
        self._calculate_positions()
        self._update_content_size()
        self._schedule_update()
    
    def add_item(self, item: VirtualPropertyItem) -> None:
        """Add a single item"""
        self._items.append(item)
        self._calculate_positions()
        self._update_content_size()
        self._schedule_update()
    
    def remove_item(self, element_id: str, property_name: str) -> bool:
        """Remove an item by element ID and property name"""
        for i, item in enumerate(self._items):
            if item.element_id == element_id and item.property_name == property_name:
                self._items.pop(i)
                self._calculate_positions()
                self._update_content_size()
                self._schedule_update()
                return True
        return False
    
    def update_item_value(self, element_id: str, property_name: str, new_value: Any) -> bool:
        """Update an item's value"""
        for item in self._items:
            if item.element_id == element_id and item.property_name == property_name:
                item.value = new_value
                # Update widget if currently visible
                for widget in self._item_widgets.values():
                    if hasattr(widget, 'update_value'):
                        widget.update_value(new_value)
                return True
        return False
    
    def _calculate_positions(self) -> None:
        """Calculate Y positions for all items"""
        y_pos = 0
        for item in self._items:
            item.y_position = y_pos
            y_pos += item.height
        
        self._total_height = y_pos
    
    def _update_content_size(self) -> None:
        """Update the content widget size"""
        self._content_widget.setFixedHeight(self._total_height)
    
    def _schedule_update(self) -> None:
        """Schedule visible items update"""
        self._update_timer.start(1)  # 1ms delay for batching
    
    def _on_scroll(self, value: int) -> None:
        """Handle scroll position change"""
        self._scroll_position = value
        self._schedule_update()
    
    def _update_visible_items(self) -> None:
        """Update which items are visible and create/destroy widgets"""
        viewport_rect = self._scroll_area.viewport().rect()
        self._viewport_height = viewport_rect.height()
        
        # Calculate visible range with buffer
        start_y = max(0, self._scroll_position - self._buffer_items * self._item_height)
        end_y = self._scroll_position + self._viewport_height + self._buffer_items * self._item_height
        
        # Find visible items
        new_visible_items = {}
        for i, item in enumerate(self._items):
            if item.y_position + item.height >= start_y and item.y_position <= end_y:
                new_visible_items[i] = item
                item.visible = True
            else:
                item.visible = False
        
        # Remove widgets for items no longer visible
        for item_index in list(self._item_widgets.keys()):
            if item_index not in new_visible_items:
                widget = self._item_widgets.pop(item_index)
                self._content_layout.removeWidget(widget)
                widget.deleteLater()
        
        # Create widgets for newly visible items
        for item_index, item in new_visible_items.items():
            if item_index not in self._item_widgets:
                widget = self._create_item_widget(item)
                self._item_widgets[item_index] = widget
                self._content_layout.addWidget(widget)
        
        self._visible_items = new_visible_items
        self._position_visible_widgets()
    
    def _create_item_widget(self, item: VirtualPropertyItem) -> QWidget:
        """Create widget for a virtual item"""
        # Import here to avoid circular imports
        from .display import PropertyDisplayWidget
        
        widget = PropertyDisplayWidget(
            property_name=item.property_name,
            value=item.value,
            property_type=item.property_type
        )
        
        # Connect signals
        widget.property_clicked.connect(
            lambda name: self.item_selected.emit(item.element_id, name)
        )
        widget.edit_requested.connect(
            lambda name: self._handle_edit_request(item.element_id, name)
        )
        
        return widget
    
    def _position_visible_widgets(self) -> None:
        """Position visible widgets correctly"""
        for item_index, widget in self._item_widgets.items():
            if item_index in self._visible_items:
                item = self._visible_items[item_index]
                y_pos = item.y_position - self._scroll_position
                widget.move(0, y_pos)
                widget.setFixedHeight(item.height)
    
    def _handle_edit_request(self, element_id: str, property_name: str) -> None:
        """Handle edit request for an item"""
        # This would trigger the property editor
        # Implementation depends on integration with Agent 2's editors
        pass
    
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        self._schedule_update()
    
    def get_visible_count(self) -> int:
        """Get number of currently visible items"""
        return len(self._visible_items)
    
    def get_total_count(self) -> int:
        """Get total number of items"""
        return len(self._items)
    
    def scroll_to_item(self, element_id: str, property_name: str) -> bool:
        """Scroll to make a specific item visible"""
        for item in self._items:
            if item.element_id == element_id and item.property_name == property_name:
                self._scroll_area.verticalScrollBar().setValue(item.y_position)
                return True
        return False

class VirtualScrollArea(QAbstractScrollArea):
    """Virtual scrolling area for property lists"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: List[Dict[str, Any]] = []
        self._item_height = 24
        self._visible_start = 0
        self._visible_count = 0
        self._total_height = 0
        self._item_renderer: Optional[Callable] = None
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    
    def set_items(self, items: List[Dict[str, Any]]) -> None:
        """Set items to display"""
        self._items = items
        self._total_height = len(items) * self._item_height
        self._update_scrollbars()
        self.viewport().update()
    
    def set_item_renderer(self, renderer: Callable[[Dict[str, Any], QRect, QPainter], None]) -> None:
        """Set custom item renderer function"""
        self._item_renderer = renderer
    
    def _update_scrollbars(self) -> None:
        """Update scrollbar ranges"""
        viewport_height = self.viewport().height()
        max_scroll = max(0, self._total_height - viewport_height)
        
        self.verticalScrollBar().setRange(0, max_scroll)
        self.verticalScrollBar().setPageStep(viewport_height)
        self.verticalScrollBar().setSingleStep(self._item_height)
    
    def paintEvent(self, event):
        """Paint visible items"""
        if not self._items or not self._item_renderer:
            return
        
        painter = QPainter(self.viewport())
        viewport_rect = self.viewport().rect()
        scroll_offset = self.verticalScrollBar().value()
        
        # Calculate visible range
        first_visible = scroll_offset // self._item_height
        last_visible = min(len(self._items) - 1, 
                          (scroll_offset + viewport_rect.height()) // self._item_height + 1)
        
        # Render visible items
        for i in range(first_visible, last_visible + 1):
            if i >= len(self._items):
                break
            
            item_rect = QRect(
                0,
                i * self._item_height - scroll_offset,
                viewport_rect.width(),
                self._item_height
            )
            
            # Only paint if item is within viewport
            if item_rect.intersects(viewport_rect):
                self._item_renderer(self._items[i], item_rect, painter)
    
    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        self._update_scrollbars()
    
    def wheelEvent(self, event):
        """Handle wheel events for scrolling"""
        delta = event.angleDelta().y()
        scroll_amount = -delta // 8  # Convert to scroll units
        current_value = self.verticalScrollBar().value()
        new_value = current_value + scroll_amount
        self.verticalScrollBar().setValue(new_value)
    
    def sizeHint(self) -> QSize:
        """Return size hint"""
        return QSize(300, 400)

class PropertyListVirtualizer:
    """High-level virtualizer for property lists"""
    
    def __init__(self, container_widget: QWidget):
        self.container = container_widget
        self.virtualizer = PropertyVirtualizer(container_widget)
        self._property_data: Dict[str, Dict[str, Any]] = {}
        self._filter_func: Optional[Callable] = None
        self._sort_func: Optional[Callable] = None
    
    def set_property_data(self, element_id: str, properties: Dict[str, Any]) -> None:
        """Set property data for an element"""
        self._property_data[element_id] = properties
        self._refresh_virtual_items()
    
    def update_property(self, element_id: str, property_name: str, value: Any) -> None:
        """Update a single property"""
        if element_id in self._property_data:
            self._property_data[element_id][property_name] = value
            self.virtualizer.update_item_value(element_id, property_name, value)
    
    def set_filter(self, filter_func: Callable[[str, str, Any], bool]) -> None:
        """Set filter function for properties"""
        self._filter_func = filter_func
        self._refresh_virtual_items()
    
    def set_sort(self, sort_func: Callable[[VirtualPropertyItem], Any]) -> None:
        """Set sort function for properties"""
        self._sort_func = sort_func
        self._refresh_virtual_items()
    
    def _refresh_virtual_items(self) -> None:
        """Refresh the virtual items list"""
        items = []
        
        for element_id, properties in self._property_data.items():
            for property_name, value in properties.items():
                # Apply filter if set
                if self._filter_func and not self._filter_func(element_id, property_name, value):
                    continue
                
                # Create virtual item
                item = VirtualPropertyItem(
                    element_id=element_id,
                    property_name=property_name,
                    value=value,
                    property_type=self._get_property_type(property_name),
                    height=self._calculate_item_height(property_name, value)
                )
                items.append(item)
        
        # Apply sort if set
        if self._sort_func:
            items.sort(key=self._sort_func)
        
        self.virtualizer.set_items(items)
    
    def _get_property_type(self, property_name: str) -> str:
        """Get property type for a property name"""
        type_mapping = {
            "confidence": "confidence",
            "x": "coordinate",
            "y": "coordinate",
            "width": "coordinate", 
            "height": "coordinate",
            "type": "choice"
        }
        return type_mapping.get(property_name, "string")
    
    def _calculate_item_height(self, property_name: str, value: Any) -> int:
        """Calculate height needed for an item"""
        base_height = 24
        
        # Larger height for multiline content
        if isinstance(value, str) and len(value) > 100:
            return base_height * 2
        elif property_name in ["text", "content"] and isinstance(value, str):
            lines = len(value.split('\n'))
            return base_height * min(3, max(1, lines))
        
        return base_height
    
    def clear(self) -> None:
        """Clear all property data"""
        self._property_data.clear()
        self.virtualizer.set_items([])
    
    def get_stats(self) -> Dict[str, int]:
        """Get virtualization statistics"""
        return {
            "total_elements": len(self._property_data),
            "total_properties": sum(len(props) for props in self._property_data.values()),
            "visible_items": self.virtualizer.get_visible_count(),
            "total_virtual_items": self.virtualizer.get_total_count()
        }
```

## 🧪 Testing Requirements

### Test Structure
```python
# tests/unit/components/property_panel/test_validators.py
class TestPropertyValidators:
    def test_validation_engine(self):
        """Test validation engine functionality"""
        
    def test_custom_rules(self):
        """Test custom validation rules"""

# tests/performance/property_panel/test_optimization.py
class TestPropertyOptimization:
    def test_cache_performance(self):
        """Test caching performance"""
        
    def test_virtualization_performance(self):
        """Test virtualization performance"""
```

## 🎯 Success Criteria
- [ ] Real-time validation <50ms response time
- [ ] Batch validation <200ms for 100+ properties
- [ ] Property panel handles 1000+ properties smoothly
- [ ] Memory usage <20MB with virtualization
- [ ] Zero validation-related crashes or data corruption

## 🤝 Integration Points

**You depend on Agent 1:**
- Property framework and validation hooks
- Event system for validation notifications
- Property data models and change tracking

**You depend on Agent 2:**
- Property display widgets and editor interfaces
- Category system for validation organization
- Search interfaces for optimization

**You provide to Agent 4:**
- Complete validation framework and APIs
- Performance optimization tools and monitoring
- Virtualization system for large datasets

## 📅 Timeline
**Days 3-5**: Complete after Agents 1-2 provide their frameworks

## 🚀 Getting Started

1. **Wait for Agents 1-2**: Ensure frameworks and display components are ready
2. **Create your feature branch**: `git checkout -b feature/property-panel-agent3-issue181`
3. **Study integration APIs**: Review Agent 1's validation hooks and Agent 2's display interfaces
4. **Start with validation framework**: Build the core validation engine first
5. **Add performance monitoring**: Implement caching and optimization
6. **Create virtualization**: Build virtual scrolling for large datasets
7. **Test thoroughly**: >95% coverage and performance benchmarks

Your validation and optimization work ensures the property panel performs well at scale!