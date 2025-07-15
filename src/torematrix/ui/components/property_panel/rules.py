"""Validation Rules System

Rule-based validation system for property validation with configurable rules,
business logic validation, and dynamic rule evaluation. Supports complex
validation scenarios and custom business rules.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import operator
from datetime import datetime

from .validators import PropertyValidator, ValidationResult, ValidationMessage, ValidationSeverity
from torematrix.core.models.element import ElementModel
from torematrix.core.models.types import TypeDefinition


class RuleOperator(Enum):
    """Operators for rule conditions"""
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
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"


class RuleLogic(Enum):
    """Logical operators for combining rules"""
    AND = "and"
    OR = "or"
    NOT = "not"


@dataclass
class RuleCondition:
    """Individual rule condition"""
    field: str
    operator: RuleOperator
    value: Any = None
    case_sensitive: bool = True
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate condition against context"""
        field_value = self._get_field_value(context, self.field)
        
        try:
            if self.operator == RuleOperator.EQUALS:
                return self._compare_values(field_value, self.value, operator.eq)
            elif self.operator == RuleOperator.NOT_EQUALS:
                return self._compare_values(field_value, self.value, operator.ne)
            elif self.operator == RuleOperator.GREATER_THAN:
                return self._compare_values(field_value, self.value, operator.gt)
            elif self.operator == RuleOperator.LESS_THAN:
                return self._compare_values(field_value, self.value, operator.lt)
            elif self.operator == RuleOperator.GREATER_EQUAL:
                return self._compare_values(field_value, self.value, operator.ge)
            elif self.operator == RuleOperator.LESS_EQUAL:
                return self._compare_values(field_value, self.value, operator.le)
            elif self.operator == RuleOperator.CONTAINS:
                return self._string_operation(field_value, self.value, "contains")
            elif self.operator == RuleOperator.NOT_CONTAINS:
                return not self._string_operation(field_value, self.value, "contains")
            elif self.operator == RuleOperator.STARTS_WITH:
                return self._string_operation(field_value, self.value, "startswith")
            elif self.operator == RuleOperator.ENDS_WITH:
                return self._string_operation(field_value, self.value, "endswith")
            elif self.operator == RuleOperator.MATCHES_REGEX:
                import re
                pattern = re.compile(str(self.value), 0 if self.case_sensitive else re.IGNORECASE)
                return bool(pattern.match(str(field_value) if field_value is not None else ""))
            elif self.operator == RuleOperator.IN_LIST:
                return field_value in self.value if isinstance(self.value, (list, tuple, set)) else False
            elif self.operator == RuleOperator.NOT_IN_LIST:
                return field_value not in self.value if isinstance(self.value, (list, tuple, set)) else True
            elif self.operator == RuleOperator.IS_NULL:
                return field_value is None
            elif self.operator == RuleOperator.IS_NOT_NULL:
                return field_value is not None
            elif self.operator == RuleOperator.IS_EMPTY:
                return self._is_empty(field_value)
            elif self.operator == RuleOperator.IS_NOT_EMPTY:
                return not self._is_empty(field_value)
            
            return False
        except Exception:
            return False
    
    def _get_field_value(self, context: Dict[str, Any], field_path: str) -> Any:
        """Get field value from context using dot notation"""
        parts = field_path.split('.')
        value = context
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None
        
        return value
    
    def _compare_values(self, value1: Any, value2: Any, op: Callable) -> bool:
        """Compare two values with type conversion"""
        if value1 is None or value2 is None:
            return op(value1, value2)
        
        # Try to convert to same type for comparison
        if type(value1) != type(value2):
            try:
                if isinstance(value1, (int, float)) and isinstance(value2, str):
                    value2 = float(value2)
                elif isinstance(value2, (int, float)) and isinstance(value1, str):
                    value1 = float(value1)
                elif isinstance(value1, str) and isinstance(value2, str):
                    if not self.case_sensitive:
                        value1 = value1.lower()
                        value2 = value2.lower()
            except (ValueError, TypeError):
                pass
        
        return op(value1, value2)
    
    def _string_operation(self, value: Any, search: Any, operation: str) -> bool:
        """Perform string operation"""
        if value is None or search is None:
            return False
        
        str_value = str(value)
        str_search = str(search)
        
        if not self.case_sensitive:
            str_value = str_value.lower()
            str_search = str_search.lower()
        
        if operation == "contains":
            return str_search in str_value
        elif operation == "startswith":
            return str_value.startswith(str_search)
        elif operation == "endswith":
            return str_value.endswith(str_search)
        
        return False
    
    def _is_empty(self, value: Any) -> bool:
        """Check if value is empty"""
        if value is None:
            return True
        if isinstance(value, str):
            return value.strip() == ""
        if isinstance(value, (list, dict, tuple, set)):
            return len(value) == 0
        return False


@dataclass
class ValidationRule:
    """Complete validation rule with conditions and actions"""
    name: str
    description: str
    conditions: List[RuleCondition] = field(default_factory=list)
    logic: RuleLogic = RuleLogic.AND
    severity: ValidationSeverity = ValidationSeverity.ERROR
    message: str = ""
    suggestion: Optional[str] = None
    enabled: bool = True
    priority: int = 0
    applies_to_fields: Optional[List[str]] = None  # None = all fields
    applies_to_types: Optional[List[str]] = None   # None = all types
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate rule against context"""
        if not self.enabled or not self.conditions:
            return True
        
        if self.logic == RuleLogic.AND:
            return all(condition.evaluate(context) for condition in self.conditions)
        elif self.logic == RuleLogic.OR:
            return any(condition.evaluate(context) for condition in self.conditions)
        elif self.logic == RuleLogic.NOT:
            # NOT logic applies to first condition only
            return not self.conditions[0].evaluate(context) if self.conditions else True
        
        return True
    
    def is_applicable(self, field_name: str, element_type: str) -> bool:
        """Check if rule applies to given field and element type"""
        if not self.enabled:
            return False
        
        # Check field filter
        if self.applies_to_fields is not None:
            if field_name not in self.applies_to_fields:
                return False
        
        # Check type filter
        if self.applies_to_types is not None:
            if element_type not in self.applies_to_types:
                return False
        
        return True
    
    def get_validation_message(self, context: Dict[str, Any]) -> ValidationMessage:
        """Get validation message for failed rule"""
        message = self.message or f"Rule '{self.name}' failed"
        field_name = context.get('field_name')
        
        return ValidationMessage(
            message=message,
            severity=self.severity,
            field=field_name,
            code=f"rule_{self.name.lower().replace(' ', '_')}",
            suggestion=self.suggestion
        )


class BusinessRuleValidator(PropertyValidator):
    """Validator that applies business rules"""
    
    def __init__(self, rules: List[ValidationRule]):
        super().__init__("Business Rules", "Validates against business rules")
        self.rules = rules
        self.priority = 100  # High priority
    
    def validate(self, value: Any, context: Dict[str, Any] = None) -> ValidationResult:
        """Validate value against business rules"""
        result = ValidationResult(is_valid=True)
        
        if not context:
            return result
        
        field_name = context.get('field_name', '')
        element_type = context.get('element_type', '')
        element = context.get('element')
        
        # Build evaluation context
        eval_context = {
            'value': value,
            'field_name': field_name,
            'element_type': element_type,
            'element': element
        }
        
        # Add element properties to context if available
        if element and hasattr(element, 'properties'):
            eval_context.update(element.properties)
        
        # Add any additional context
        eval_context.update(context)
        
        # Evaluate applicable rules
        for rule in self.rules:
            if not rule.is_applicable(field_name, element_type):
                continue
            
            try:
                if not rule.evaluate(eval_context):
                    # Rule failed - add validation message
                    message = rule.get_validation_message(eval_context)
                    result.add_message(message)
            except Exception as e:
                # Rule evaluation error
                result.add_error(
                    f"Rule evaluation error: {str(e)}",
                    field=field_name,
                    code="rule_evaluation_error"
                )
        
        return result
    
    def add_rule(self, rule: ValidationRule):
        """Add a validation rule"""
        self.rules.append(rule)
    
    def remove_rule(self, rule_name: str):
        """Remove a validation rule"""
        self.rules = [r for r in self.rules if r.name != rule_name]
    
    def get_rules_for_field(self, field_name: str, element_type: str) -> List[ValidationRule]:
        """Get applicable rules for a field"""
        return [rule for rule in self.rules 
                if rule.is_applicable(field_name, element_type)]


class RuleBuilder:
    """Builder class for creating validation rules"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset builder to start new rule"""
        self._name = ""
        self._description = ""
        self._conditions = []
        self._logic = RuleLogic.AND
        self._severity = ValidationSeverity.ERROR
        self._message = ""
        self._suggestion = None
        self._enabled = True
        self._priority = 0
        self._applies_to_fields = None
        self._applies_to_types = None
        return self
    
    def name(self, name: str):
        """Set rule name"""
        self._name = name
        return self
    
    def description(self, description: str):
        """Set rule description"""
        self._description = description
        return self
    
    def when(self, field: str, operator: RuleOperator, value: Any = None, case_sensitive: bool = True):
        """Add a condition to the rule"""
        condition = RuleCondition(
            field=field,
            operator=operator,
            value=value,
            case_sensitive=case_sensitive
        )
        self._conditions.append(condition)
        return self
    
    def and_when(self, field: str, operator: RuleOperator, value: Any = None, case_sensitive: bool = True):
        """Add an AND condition"""
        self._logic = RuleLogic.AND
        return self.when(field, operator, value, case_sensitive)
    
    def or_when(self, field: str, operator: RuleOperator, value: Any = None, case_sensitive: bool = True):
        """Add an OR condition"""
        self._logic = RuleLogic.OR
        return self.when(field, operator, value, case_sensitive)
    
    def severity(self, severity: ValidationSeverity):
        """Set rule severity"""
        self._severity = severity
        return self
    
    def message(self, message: str):
        """Set validation message"""
        self._message = message
        return self
    
    def suggestion(self, suggestion: str):
        """Set validation suggestion"""
        self._suggestion = suggestion
        return self
    
    def enabled(self, enabled: bool = True):
        """Set rule enabled state"""
        self._enabled = enabled
        return self
    
    def priority(self, priority: int):
        """Set rule priority"""
        self._priority = priority
        return self
    
    def for_fields(self, *fields: str):
        """Set fields this rule applies to"""
        self._applies_to_fields = list(fields)
        return self
    
    def for_types(self, *types: str):
        """Set element types this rule applies to"""
        self._applies_to_types = list(types)
        return self
    
    def build(self) -> ValidationRule:
        """Build the validation rule"""
        rule = ValidationRule(
            name=self._name,
            description=self._description,
            conditions=self._conditions.copy(),
            logic=self._logic,
            severity=self._severity,
            message=self._message,
            suggestion=self._suggestion,
            enabled=self._enabled,
            priority=self._priority,
            applies_to_fields=self._applies_to_fields,
            applies_to_types=self._applies_to_types
        )
        self.reset()
        return rule


class RuleSet:
    """Collection of validation rules with management capabilities"""
    
    def __init__(self, name: str):
        self.name = name
        self.rules: List[ValidationRule] = []
        self.enabled = True
        self.metadata: Dict[str, Any] = {}
    
    def add_rule(self, rule: ValidationRule):
        """Add a rule to the set"""
        self.rules.append(rule)
    
    def remove_rule(self, rule_name: str):
        """Remove a rule from the set"""
        self.rules = [r for r in self.rules if r.name != rule_name]
    
    def get_rule(self, rule_name: str) -> Optional[ValidationRule]:
        """Get a rule by name"""
        for rule in self.rules:
            if rule.name == rule_name:
                return rule
        return None
    
    def get_applicable_rules(self, field_name: str, element_type: str) -> List[ValidationRule]:
        """Get rules applicable to a field and element type"""
        if not self.enabled:
            return []
        
        return [rule for rule in self.rules 
                if rule.is_applicable(field_name, element_type)]
    
    def validate_all(self, context: Dict[str, Any]) -> ValidationResult:
        """Validate context against all applicable rules"""
        result = ValidationResult(is_valid=True)
        
        field_name = context.get('field_name', '')
        element_type = context.get('element_type', '')
        
        applicable_rules = self.get_applicable_rules(field_name, element_type)
        
        # Sort rules by priority (higher first)
        applicable_rules.sort(key=lambda r: r.priority, reverse=True)
        
        for rule in applicable_rules:
            try:
                if not rule.evaluate(context):
                    message = rule.get_validation_message(context)
                    result.add_message(message)
            except Exception as e:
                result.add_error(
                    f"Rule '{rule.name}' evaluation error: {str(e)}",
                    field=field_name,
                    code="rule_error"
                )
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ruleset to dictionary"""
        return {
            'name': self.name,
            'enabled': self.enabled,
            'metadata': self.metadata,
            'rules': [self._rule_to_dict(rule) for rule in self.rules]
        }
    
    def from_dict(self, data: Dict[str, Any]):
        """Load ruleset from dictionary"""
        self.name = data.get('name', '')
        self.enabled = data.get('enabled', True)
        self.metadata = data.get('metadata', {})
        
        self.rules = []
        for rule_data in data.get('rules', []):
            rule = self._rule_from_dict(rule_data)
            if rule:
                self.rules.append(rule)
    
    def _rule_to_dict(self, rule: ValidationRule) -> Dict[str, Any]:
        """Convert rule to dictionary"""
        return {
            'name': rule.name,
            'description': rule.description,
            'conditions': [
                {
                    'field': c.field,
                    'operator': c.operator.value,
                    'value': c.value,
                    'case_sensitive': c.case_sensitive
                } for c in rule.conditions
            ],
            'logic': rule.logic.value,
            'severity': rule.severity.value,
            'message': rule.message,
            'suggestion': rule.suggestion,
            'enabled': rule.enabled,
            'priority': rule.priority,
            'applies_to_fields': rule.applies_to_fields,
            'applies_to_types': rule.applies_to_types
        }
    
    def _rule_from_dict(self, data: Dict[str, Any]) -> Optional[ValidationRule]:
        """Create rule from dictionary"""
        try:
            conditions = []
            for cond_data in data.get('conditions', []):
                condition = RuleCondition(
                    field=cond_data['field'],
                    operator=RuleOperator(cond_data['operator']),
                    value=cond_data.get('value'),
                    case_sensitive=cond_data.get('case_sensitive', True)
                )
                conditions.append(condition)
            
            return ValidationRule(
                name=data['name'],
                description=data.get('description', ''),
                conditions=conditions,
                logic=RuleLogic(data.get('logic', 'and')),
                severity=ValidationSeverity(data.get('severity', 'error')),
                message=data.get('message', ''),
                suggestion=data.get('suggestion'),
                enabled=data.get('enabled', True),
                priority=data.get('priority', 0),
                applies_to_fields=data.get('applies_to_fields'),
                applies_to_types=data.get('applies_to_types')
            )
        except Exception:
            return None


class RuleManager:
    """Manager for validation rule sets"""
    
    def __init__(self):
        self.rule_sets: Dict[str, RuleSet] = {}
        self.active_rule_sets: Set[str] = set()
    
    def add_rule_set(self, rule_set: RuleSet):
        """Add a rule set"""
        self.rule_sets[rule_set.name] = rule_set
    
    def remove_rule_set(self, name: str):
        """Remove a rule set"""
        if name in self.rule_sets:
            del self.rule_sets[name]
        self.active_rule_sets.discard(name)
    
    def activate_rule_set(self, name: str):
        """Activate a rule set"""
        if name in self.rule_sets:
            self.active_rule_sets.add(name)
    
    def deactivate_rule_set(self, name: str):
        """Deactivate a rule set"""
        self.active_rule_sets.discard(name)
    
    def get_active_rules(self, field_name: str, element_type: str) -> List[ValidationRule]:
        """Get all active rules for a field and element type"""
        rules = []
        for rule_set_name in self.active_rule_sets:
            if rule_set_name in self.rule_sets:
                rule_set = self.rule_sets[rule_set_name]
                rules.extend(rule_set.get_applicable_rules(field_name, element_type))
        
        # Sort by priority
        rules.sort(key=lambda r: r.priority, reverse=True)
        return rules
    
    def validate_with_rules(self, field_name: str, value: Any, context: Dict[str, Any]) -> ValidationResult:
        """Validate using active rules"""
        result = ValidationResult(is_valid=True)
        
        element_type = context.get('element_type', '')
        rules = self.get_active_rules(field_name, element_type)
        
        eval_context = context.copy()
        eval_context.update({
            'value': value,
            'field_name': field_name
        })
        
        for rule in rules:
            try:
                if not rule.evaluate(eval_context):
                    message = rule.get_validation_message(eval_context)
                    result.add_message(message)
            except Exception as e:
                result.add_error(
                    f"Rule '{rule.name}' error: {str(e)}",
                    field=field_name,
                    code="rule_error"
                )
        
        return result
    
    def save_to_file(self, file_path: str):
        """Save rule sets to JSON file"""
        data = {
            'rule_sets': {name: rs.to_dict() for name, rs in self.rule_sets.items()},
            'active_rule_sets': list(self.active_rule_sets)
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_from_file(self, file_path: str):
        """Load rule sets from JSON file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        self.rule_sets = {}
        for name, rs_data in data.get('rule_sets', {}).items():
            rule_set = RuleSet(name)
            rule_set.from_dict(rs_data)
            self.rule_sets[name] = rule_set
        
        self.active_rule_sets = set(data.get('active_rule_sets', []))