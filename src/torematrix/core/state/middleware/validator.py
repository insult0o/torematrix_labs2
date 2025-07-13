"""
Validation middleware for ensuring action and state integrity.
"""

from typing import Dict, Any, Callable, List, Optional
import logging
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Error raised when validation fails."""
    pass


class Validator(ABC):
    """Abstract base class for validators."""
    
    @abstractmethod
    def validate(self, value: Any, context: Dict[str, Any]) -> bool:
        """
        Validate a value.
        
        Args:
            value: Value to validate
            context: Additional context for validation
            
        Returns:
            True if valid, False otherwise
            
        Raises:
            ValidationError: If validation fails with details
        """
        pass


@dataclass
class ValidationRule:
    """A validation rule configuration."""
    name: str
    validator: Validator
    required: bool = True
    error_message: str = ""


class ValidatorMiddleware:
    """
    Middleware for validating actions and state changes.
    
    Supports both action validation (before processing) and
    state validation (after processing).
    """
    
    def __init__(self):
        self.action_validators: Dict[str, List[ValidationRule]] = {}
        self.state_validators: List[ValidationRule] = []
        self.validation_stats = {
            'total_validations': 0,
            'failed_validations': 0,
            'validation_errors': []
        }
    
    def __call__(self, store):
        """Create validation middleware."""
        def middleware(next_dispatch):
            def dispatch(action):
                # Validate action before processing
                self._validate_action(action)
                
                # Get state before action
                state_before = store.get_state()
                
                # Process action
                result = next_dispatch(action)
                
                # Validate state after action
                state_after = store.get_state()
                self._validate_state(state_after, {
                    'action': action,
                    'state_before': state_before,
                    'state_after': state_after
                })
                
                self.validation_stats['total_validations'] += 1
                return result
            
            return dispatch
        return middleware
    
    def add_action_validator(self, action_type: str, rule: ValidationRule):
        """Add a validation rule for a specific action type."""
        if action_type not in self.action_validators:
            self.action_validators[action_type] = []
        self.action_validators[action_type].append(rule)
        logger.debug(f"Added action validator for {action_type}: {rule.name}")
    
    def add_state_validator(self, rule: ValidationRule):
        """Add a validation rule for state."""
        self.state_validators.append(rule)
        logger.debug(f"Added state validator: {rule.name}")
    
    def _validate_action(self, action):
        """Validate an action before processing."""
        action_type = getattr(action, 'type', None)
        if not action_type:
            self._record_validation_error("Action missing type", action)
            raise ValidationError("Action must have a type")
        
        # Run action-specific validators
        if action_type in self.action_validators:
            for rule in self.action_validators[action_type]:
                try:
                    is_valid = rule.validator.validate(action, {'action_type': action_type})
                    if not is_valid and rule.required:
                        error_msg = rule.error_message or f"Action validation failed: {rule.name}"
                        self._record_validation_error(error_msg, action)
                        raise ValidationError(error_msg)
                except ValidationError:
                    raise
                except Exception as e:
                    error_msg = f"Validator {rule.name} failed: {e}"
                    self._record_validation_error(error_msg, action)
                    if rule.required:
                        raise ValidationError(error_msg)
    
    def _validate_state(self, state, context):
        """Validate state after an action."""
        for rule in self.state_validators:
            try:
                is_valid = rule.validator.validate(state, context)
                if not is_valid and rule.required:
                    error_msg = rule.error_message or f"State validation failed: {rule.name}"
                    self._record_validation_error(error_msg, context.get('action'))
                    raise ValidationError(error_msg)
            except ValidationError:
                raise
            except Exception as e:
                error_msg = f"State validator {rule.name} failed: {e}"
                self._record_validation_error(error_msg, context.get('action'))
                if rule.required:
                    raise ValidationError(error_msg)
    
    def _record_validation_error(self, message: str, action):
        """Record a validation error for metrics."""
        self.validation_stats['failed_validations'] += 1
        self.validation_stats['validation_errors'].append({
            'message': message,
            'action_type': getattr(action, 'type', 'unknown'),
            'timestamp': __import__('time').time()
        })
        
        # Keep only last 100 errors
        if len(self.validation_stats['validation_errors']) > 100:
            self.validation_stats['validation_errors'].pop(0)
        
        logger.warning(f"Validation error: {message}")
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        total = self.validation_stats['total_validations']
        failed = self.validation_stats['failed_validations']
        
        return {
            **self.validation_stats,
            'success_rate': (total - failed) / total if total > 0 else 1.0,
            'failure_rate': failed / total if total > 0 else 0.0
        }


# Built-in validators
class TypeValidator(Validator):
    """Validator for checking types."""
    
    def __init__(self, expected_type):
        self.expected_type = expected_type
    
    def validate(self, value: Any, context: Dict[str, Any]) -> bool:
        return isinstance(value, self.expected_type)


class RequiredFieldValidator(Validator):
    """Validator for checking required fields."""
    
    def __init__(self, field_name: str):
        self.field_name = field_name
    
    def validate(self, value: Any, context: Dict[str, Any]) -> bool:
        if hasattr(value, self.field_name):
            field_value = getattr(value, self.field_name)
            return field_value is not None
        elif isinstance(value, dict):
            return self.field_name in value and value[self.field_name] is not None
        return False


class RangeValidator(Validator):
    """Validator for numeric ranges."""
    
    def __init__(self, min_value: Optional[float] = None, max_value: Optional[float] = None):
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, value: Any, context: Dict[str, Any]) -> bool:
        if not isinstance(value, (int, float)):
            return False
        
        if self.min_value is not None and value < self.min_value:
            return False
        
        if self.max_value is not None and value > self.max_value:
            return False
        
        return True


class CustomValidator(Validator):
    """Validator that uses a custom function."""
    
    def __init__(self, validation_func: Callable[[Any, Dict[str, Any]], bool]):
        self.validation_func = validation_func
    
    def validate(self, value: Any, context: Dict[str, Any]) -> bool:
        return self.validation_func(value, context)