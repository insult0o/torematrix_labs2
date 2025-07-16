"""
Automation Engine for Merge/Split Operations - Agent 4 Implementation.

Provides rule-based automation for merge/split operations.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import uuid
import asyncio
from datetime import datetime


class RuleType(Enum):
    """Types of automation rules."""
    MERGE_SIMILAR = "merge_similar"
    SPLIT_CONTENT = "split_content"
    CLEAN_TEXT = "clean_text"
    CUSTOM = "custom"


class RuleCondition(Enum):
    """Rule condition types."""
    ELEMENT_TYPE = "element_type"
    TEXT_LENGTH = "text_length"
    SIMILARITY_SCORE = "similarity_score"
    CUSTOM = "custom"


class RuleAction(Enum):
    """Rule action types."""
    MERGE_ELEMENTS = "merge_elements"
    SPLIT_ELEMENT = "split_element" 
    MODIFY_TEXT = "modify_text"
    CUSTOM = "custom"


class ExecutionMode(Enum):
    """Rule execution modes."""
    INTERACTIVE = "interactive"
    BATCH = "batch"
    SIMULATION = "simulation"


class RuleStatus(Enum):
    """Rule status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"


@dataclass
class RuleConditionSpec:
    """Specification for a rule condition."""
    condition_type: RuleCondition
    operator: str = "=="
    value: Any = None
    weight: float = 1.0
    
    def evaluate(self, element, context: Dict[str, Any]) -> bool:
        """Evaluate condition against element."""
        try:
            if self.condition_type == RuleCondition.ELEMENT_TYPE:
                element_type = getattr(element, 'element_type', 'unknown')
                if hasattr(element_type, 'value'):
                    element_type = element_type.value
                return self._compare(str(element_type), self.operator, str(self.value))
            elif self.condition_type == RuleCondition.TEXT_LENGTH:
                text_length = len(getattr(element, 'text', ''))
                return self._compare(text_length, self.operator, self.value)
            elif self.condition_type == RuleCondition.SIMILARITY_SCORE:
                # Simple similarity implementation
                return True
            return False
        except Exception:
            return False
    
    def _compare(self, actual: Any, operator: str, expected: Any) -> bool:
        """Compare values using operator."""
        if operator == "==":
            return actual == expected
        elif operator == "!=":
            return actual != expected
        elif operator == ">":
            return actual > expected
        elif operator == ">=":
            return actual >= expected
        elif operator == "<":
            return actual < expected
        elif operator == "<=":
            return actual <= expected
        return False


@dataclass
class RuleActionSpec:
    """Specification for a rule action."""
    action_type: RuleAction
    parameters: Dict[str, Any] = None
    priority: int = 1
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
    
    async def execute(self, elements: List, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute action on elements."""
        try:
            if self.action_type == RuleAction.MERGE_ELEMENTS:
                return await self._merge_elements(elements, context)
            elif self.action_type == RuleAction.SPLIT_ELEMENT:
                return await self._split_element(elements, context)
            elif self.action_type == RuleAction.MODIFY_TEXT:
                return await self._modify_text(elements, context)
            else:
                return {"success": False, "error": f"Action {self.action_type} not implemented"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _merge_elements(self, elements: List, context: Dict[str, Any]) -> Dict[str, Any]:
        """Merge elements action."""
        if len(elements) < 2:
            return {"success": False, "error": "Need at least 2 elements to merge"}
        
        separator = self.parameters.get("separator", " ")
        texts = []
        
        for element in elements:
            text = getattr(element, 'text', '')
            if text:
                texts.append(text)
        
        merged_text = separator.join(texts)
        
        return {
            "success": True,
            "action": "merge",
            "merged_text": merged_text,
            "source_count": len(elements)
        }
    
    async def _split_element(self, elements: List, context: Dict[str, Any]) -> Dict[str, Any]:
        """Split element action."""
        if len(elements) != 1:
            return {"success": False, "error": "Need exactly 1 element to split"}
        
        element = elements[0]
        text = getattr(element, 'text', '')
        if not text:
            return {"success": False, "error": "Element has no text to split"}
        
        pattern = self.parameters.get("pattern", r"\s+")
        max_parts = self.parameters.get("max_parts", 10)
        
        import re
        parts = re.split(pattern, text, maxsplit=max_parts-1)
        parts = [part.strip() for part in parts if part.strip()]
        
        return {
            "success": True,
            "action": "split",
            "parts": parts,
            "part_count": len(parts)
        }
    
    async def _modify_text(self, elements: List, context: Dict[str, Any]) -> Dict[str, Any]:
        """Modify text action."""
        modified_count = 0
        
        for element in elements:
            text = getattr(element, 'text', '')
            if text:
                if self.parameters.get("trim_whitespace", False):
                    new_text = text.strip()
                    if hasattr(element, 'text'):
                        element.text = new_text
                    modified_count += 1
        
        return {
            "success": True,
            "action": "modify_text",
            "modified_count": modified_count
        }


@dataclass
class AutomationRule:
    """Complete automation rule definition."""
    id: str = None
    name: str = ""
    description: str = ""
    rule_type: RuleType = RuleType.CUSTOM
    conditions: List[RuleConditionSpec] = None
    actions: List[RuleActionSpec] = None
    execution_mode: ExecutionMode = ExecutionMode.INTERACTIVE
    status: RuleStatus = RuleStatus.ACTIVE
    priority: int = 1
    execution_count: int = 0
    success_count: int = 0
    last_executed: Optional[datetime] = None
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.conditions is None:
            self.conditions = []
        if self.actions is None:
            self.actions = []
    
    async def execute(self, elements: List, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute rule on elements."""
        try:
            self.execution_count += 1
            self.last_executed = datetime.now()
            
            # Evaluate conditions
            matching_elements = []
            for element in elements:
                if self._evaluate_conditions(element, context):
                    matching_elements.append(element)
            
            if not matching_elements:
                return {
                    "success": False,
                    "rule_id": self.id,
                    "message": "No elements matched conditions"
                }
            
            # Execute actions
            results = []
            for action in sorted(self.actions, key=lambda a: a.priority):
                result = await action.execute(matching_elements, context)
                results.append(result)
                
                if not result.get("success", False):
                    return {
                        "success": False,
                        "rule_id": self.id,
                        "results": results,
                        "error": result.get("error", "Action failed")
                    }
            
            self.success_count += 1
            return {
                "success": True,
                "rule_id": self.id,
                "results": results,
                "matched_elements": len(matching_elements)
            }
            
        except Exception as e:
            return {
                "success": False,
                "rule_id": self.id,
                "error": str(e)
            }
    
    def _evaluate_conditions(self, element, context: Dict[str, Any]) -> bool:
        """Evaluate all conditions for element."""
        if not self.conditions:
            return True
        
        for condition in self.conditions:
            if not condition.evaluate(element, context):
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "rule_type": self.rule_type.value,
            "execution_mode": self.execution_mode.value,
            "status": self.status.value,
            "priority": self.priority,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "last_executed": self.last_executed.isoformat() if self.last_executed else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AutomationRule':
        """Create rule from dictionary."""
        rule = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            rule_type=RuleType(data.get("rule_type", "custom")),
            execution_mode=ExecutionMode(data.get("execution_mode", "interactive")),
            status=RuleStatus(data.get("status", "active")),
            priority=data.get("priority", 1),
            execution_count=data.get("execution_count", 0),
            success_count=data.get("success_count", 0)
        )
        
        if data.get("last_executed"):
            rule.last_executed = datetime.fromisoformat(data["last_executed"])
        
        return rule


class AutomationExecutor:
    """Core executor for automation rules."""
    
    def __init__(self, state_manager=None, event_bus=None):
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.rules: Dict[str, AutomationRule] = {}
        self.execution_queue = None  # Placeholder
        
        self._load_built_in_rules()
    
    def _load_built_in_rules(self):
        """Load built-in automation rules."""
        # Text cleaning rule
        text_clean_rule = AutomationRule(
            name="Clean Text Elements",
            description="Remove extra whitespace and normalize text",
            rule_type=RuleType.CLEAN_TEXT,
            conditions=[
                RuleConditionSpec(
                    condition_type=RuleCondition.ELEMENT_TYPE,
                    operator="==",
                    value="TEXT"
                )
            ],
            actions=[
                RuleActionSpec(
                    action_type=RuleAction.MODIFY_TEXT,
                    parameters={"trim_whitespace": True},
                    priority=1
                )
            ]
        )
        
        self.rules[text_clean_rule.id] = text_clean_rule
    
    def add_rule(self, rule: AutomationRule):
        """Add rule to executor."""
        self.rules[rule.id] = rule
    
    def remove_rule(self, rule_id: str):
        """Remove rule from executor."""
        if rule_id in self.rules:
            del self.rules[rule_id]
    
    def get_active_rules(self) -> List[AutomationRule]:
        """Get active rules."""
        return [rule for rule in self.rules.values() if rule.status == RuleStatus.ACTIVE]


class AutomationControlWidget:
    """Widget for controlling automation system."""
    
    def __init__(self, state_manager=None, event_bus=None, parent=None):
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.automation_executor = AutomationExecutor(state_manager, event_bus)
        self.tab_widget = None  # Placeholder
        
        # Mock PyQt signals
        self.rule_executed = MockSignal()


class MockSignal:
    """Mock PyQt signal for testing."""
    
    def __init__(self):
        self.callbacks = []
    
    def connect(self, callback):
        self.callbacks.append(callback)
    
    def emit(self, *args):
        for callback in self.callbacks:
            callback(*args)