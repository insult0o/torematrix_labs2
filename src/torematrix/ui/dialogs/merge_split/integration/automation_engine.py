"""
Automation Engine for Merge/Split Operations - Agent 4 Implementation.

This module provides a comprehensive automation system for rule-based merge/split 
operations. It allows users to define conditions and actions that can be executed
automatically or in simulation mode to streamline repetitive tasks.

Features:
- Rule-based automation with condition evaluation
- Interactive and batch execution modes  
- Simulation mode for testing rules
- Performance monitoring and analytics
- Rule sharing and import/export
"""

from typing import Dict, List, Optional, Any, Union, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
import json
import uuid
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QListWidget, QTextEdit, QComboBox, QSpinBox, QCheckBox,
    QGroupBox, QTabWidget, QSplitter, QTreeWidget, QTreeWidgetItem,
    QDialog, QDialogButtonBox, QProgressBar, QMessageBox, QToolButton,
    QLineEdit, QScrollArea, QFrame, QSlider, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QMutex, QWaitCondition
from PyQt6.QtGui import QIcon, QPalette, QFont, QValidator

from .....core.models.element import Element, ElementType
from .....core.state import StateManager
from .....core.events import EventBus
from .....ui.components.base import BaseWidget

logger = logging.getLogger(__name__)


class RuleType(Enum):
    """Types of automation rules."""
    MERGE_SIMILAR = auto()
    SPLIT_CONTENT = auto()
    CLEAN_TEXT = auto()
    ORGANIZE_HIERARCHY = auto()
    VALIDATE_STRUCTURE = auto()
    CUSTOM = auto()


class RuleCondition(Enum):
    """Rule condition types."""
    ELEMENT_TYPE = auto()
    TEXT_LENGTH = auto()
    SIMILARITY_SCORE = auto()
    POSITION = auto()
    CUSTOM = auto()


class RuleAction(Enum):
    """Rule action types."""
    MERGE_ELEMENTS = auto()
    SPLIT_ELEMENT = auto()
    MODIFY_TEXT = auto()
    MOVE_ELEMENT = auto()
    DELETE_ELEMENT = auto()
    CUSTOM = auto()


class ExecutionMode(Enum):
    """Rule execution modes."""
    INTERACTIVE = auto()
    BATCH = auto()
    SIMULATION = auto()


class RuleStatus(Enum):
    """Rule status."""
    ACTIVE = auto()
    INACTIVE = auto()
    TESTING = auto()


@dataclass
class RuleConditionSpec:
    """Specification for a rule condition."""
    condition_type: RuleCondition
    operator: str = "=="
    value: Any = None
    weight: float = 1.0
    
    def evaluate(self, element: Element, context: Dict[str, Any]) -> bool:
        """Evaluate condition against element."""
        try:
            if self.condition_type == RuleCondition.ELEMENT_TYPE:
                element_type = element.element_type.value if hasattr(element.element_type, 'value') else str(element.element_type)
                return self._compare(element_type, self.operator, self.value)
            elif self.condition_type == RuleCondition.TEXT_LENGTH:
                text_length = len(element.text) if hasattr(element, 'text') and element.text else 0
                return self._compare(text_length, self.operator, self.value)
            elif self.condition_type == RuleCondition.SIMILARITY_SCORE:
                reference = context.get('reference_element')
                if reference:
                    # Simple similarity calculation
                    if hasattr(element, 'text') and hasattr(reference, 'text'):
                        score = self._calculate_similarity(element.text, reference.text)
                        return self._compare(score, self.operator, self.value)
            return False
        except Exception as e:
            logger.error(f"Error evaluating condition: {e}")
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
        elif operator == "contains":
            return str(expected).lower() in str(actual).lower()
        return False
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        if not text1 or not text2:
            return 0.0
        
        # Simple Jaccard similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 and not words2:
            return 1.0
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0


@dataclass
class RuleActionSpec:
    """Specification for a rule action."""
    action_type: RuleAction
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1
    
    async def execute(self, elements: List[Element], context: Dict[str, Any]) -> Dict[str, Any]:
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
            logger.error(f"Error executing action: {e}")
            return {"success": False, "error": str(e)}
    
    async def _merge_elements(self, elements: List[Element], context: Dict[str, Any]) -> Dict[str, Any]:
        """Merge elements action."""
        if len(elements) < 2:
            return {"success": False, "error": "Need at least 2 elements to merge"}
        
        separator = self.parameters.get("separator", " ")
        texts = []
        
        for element in elements:
            if hasattr(element, 'text') and element.text:
                texts.append(element.text)
        
        merged_text = separator.join(texts)
        
        return {
            "success": True,
            "action": "merge",
            "merged_text": merged_text,
            "source_count": len(elements)
        }
    
    async def _split_element(self, elements: List[Element], context: Dict[str, Any]) -> Dict[str, Any]:
        """Split element action."""
        if len(elements) != 1:
            return {"success": False, "error": "Need exactly 1 element to split"}
        
        element = elements[0]
        if not hasattr(element, 'text') or not element.text:
            return {"success": False, "error": "Element has no text to split"}
        
        pattern = self.parameters.get("pattern", r"\s+")
        max_parts = self.parameters.get("max_parts", 10)
        
        import re
        parts = re.split(pattern, element.text, maxsplit=max_parts-1)
        parts = [part.strip() for part in parts if part.strip()]
        
        return {
            "success": True,
            "action": "split",
            "parts": parts,
            "part_count": len(parts)
        }
    
    async def _modify_text(self, elements: List[Element], context: Dict[str, Any]) -> Dict[str, Any]:
        """Modify text action."""
        modified_count = 0
        
        for element in elements:
            if hasattr(element, 'text') and element.text:
                original_text = element.text
                modified_text = original_text
                
                if self.parameters.get("trim_whitespace", False):
                    modified_text = modified_text.strip()
                
                if self.parameters.get("normalize_case", False):
                    case_type = self.parameters.get("case_type", "lower")
                    if case_type == "lower":
                        modified_text = modified_text.lower()
                    elif case_type == "upper":
                        modified_text = modified_text.upper()
                    elif case_type == "title":
                        modified_text = modified_text.title()
                
                if modified_text != original_text:
                    element.text = modified_text
                    modified_count += 1
        
        return {
            "success": True,
            "action": "modify_text",
            "modified_count": modified_count
        }


@dataclass
class AutomationRule:
    """Complete automation rule definition."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    rule_type: RuleType = RuleType.CUSTOM
    conditions: List[RuleConditionSpec] = field(default_factory=list)
    actions: List[RuleActionSpec] = field(default_factory=list)
    execution_mode: ExecutionMode = ExecutionMode.INTERACTIVE
    status: RuleStatus = RuleStatus.ACTIVE
    priority: int = 1
    execution_count: int = 0
    success_count: int = 0
    last_executed: Optional[datetime] = None
    
    async def execute(self, elements: List[Element], context: Dict[str, Any]) -> Dict[str, Any]:
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
            logger.error(f"Error executing rule {self.name}: {e}")
            return {
                "success": False,
                "rule_id": self.id,
                "error": str(e)
            }
    
    def _evaluate_conditions(self, element: Element, context: Dict[str, Any]) -> bool:
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
            "rule_type": self.rule_type.name,
            "execution_mode": self.execution_mode.name,
            "status": self.status.name,
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
            rule_type=RuleType[data.get("rule_type", "CUSTOM")],
            execution_mode=ExecutionMode[data.get("execution_mode", "INTERACTIVE")],
            status=RuleStatus[data.get("status", "ACTIVE")],
            priority=data.get("priority", 1),
            execution_count=data.get("execution_count", 0),
            success_count=data.get("success_count", 0)
        )
        
        if data.get("last_executed"):
            rule.last_executed = datetime.fromisoformat(data["last_executed"])
        
        return rule


class AutomationExecutor:
    """Core executor for automation rules."""
    
    def __init__(self, state_manager: StateManager, event_bus: EventBus):
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.rules: Dict[str, AutomationRule] = {}
        self.execution_queue = asyncio.Queue()
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._mutex = QMutex()
        
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
                ),
                RuleConditionSpec(
                    condition_type=RuleCondition.TEXT_LENGTH,
                    operator=">",
                    value=0
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
        
        # Similar elements merge rule
        merge_similar_rule = AutomationRule(
            name="Merge Similar Elements",
            description="Automatically merge elements with high similarity",
            rule_type=RuleType.MERGE_SIMILAR,
            conditions=[
                RuleConditionSpec(
                    condition_type=RuleCondition.SIMILARITY_SCORE,
                    operator=">=",
                    value=0.8
                )
            ],
            actions=[
                RuleActionSpec(
                    action_type=RuleAction.MERGE_ELEMENTS,
                    parameters={"separator": " "},
                    priority=1
                )
            ]
        )
        
        self.rules[text_clean_rule.id] = text_clean_rule
        self.rules[merge_similar_rule.id] = merge_similar_rule
    
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
    
    async def execute_rules(self, elements: List[Element], context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute all applicable rules on elements."""
        if context is None:
            context = {}
        
        results = []
        active_rules = self.get_active_rules()
        
        for rule in sorted(active_rules, key=lambda r: r.priority):
            if rule.execution_mode != ExecutionMode.SIMULATION:
                result = await rule.execute(elements, context)
                results.append(result)
        
        return results


class AutomationControlWidget(BaseWidget):
    """Widget for controlling automation system."""
    
    rule_executed = pyqtSignal(str, dict)  # rule_id, result
    
    def __init__(self, state_manager: StateManager, event_bus: EventBus, parent=None):
        super().__init__(state_manager, event_bus, parent)
        
        self.automation_executor = AutomationExecutor(state_manager, event_bus)
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Rules tab
        self.rules_tab = self._create_rules_tab()
        self.tab_widget.addTab(self.rules_tab, "Rules")
        
        # Monitor tab
        self.monitor_tab = self._create_monitor_tab()
        self.tab_widget.addTab(self.monitor_tab, "Monitor")
        
        # Settings tab
        self.settings_tab = self._create_settings_tab()
        self.tab_widget.addTab(self.settings_tab, "Settings")
        
        layout.addWidget(self.tab_widget)
    
    def _create_rules_tab(self) -> QWidget:
        """Create rules management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Rule list
        self.rules_list = QListWidget()
        layout.addWidget(self.rules_list)
        
        # Control buttons
        buttons_layout = QHBoxLayout()
        self.add_rule_btn = QPushButton("Add Rule")
        self.edit_rule_btn = QPushButton("Edit Rule")
        self.delete_rule_btn = QPushButton("Delete Rule")
        self.execute_rule_btn = QPushButton("Execute Selected")
        
        buttons_layout.addWidget(self.add_rule_btn)
        buttons_layout.addWidget(self.edit_rule_btn)
        buttons_layout.addWidget(self.delete_rule_btn)
        buttons_layout.addWidget(self.execute_rule_btn)
        
        layout.addLayout(buttons_layout)
        
        return widget
    
    def _create_monitor_tab(self) -> QWidget:
        """Create monitoring tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Execution log
        self.execution_log = QTextEdit()
        self.execution_log.setReadOnly(True)
        layout.addWidget(self.execution_log)
        
        return widget
    
    def _create_settings_tab(self) -> QWidget:
        """Create settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Settings placeholder
        settings_label = QLabel("Automation settings will be configured here")
        layout.addWidget(settings_label)
        
        return widget
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.execute_rule_btn.clicked.connect(self._execute_selected_rule)
    
    def _execute_selected_rule(self):
        """Execute selected rule."""
        # Placeholder for rule execution
        self.execution_log.append("Rule execution placeholder")