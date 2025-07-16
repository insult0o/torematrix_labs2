"""
Template System for Merge/Split Operations - Agent 4 Implementation.

Provides template-based operation patterns for efficient merge/split workflows.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import uuid
import asyncio
from datetime import datetime


class TemplateCategory(Enum):
    """Categories of operation templates."""
    MERGE = "merge"
    SPLIT = "split"
    CLEAN = "clean"
    ANALYZE = "analyze"
    USER_DEFINED = "user_defined"


class TemplateType(Enum):
    """Types of templates."""
    BUILT_IN = "built_in"
    CUSTOM = "custom"
    IMPORTED = "imported"


class StepType(Enum):
    """Types of template steps."""
    SELECTION = "selection"
    ANALYSIS = "analysis"
    OPERATION = "operation"
    VALIDATION = "validation"


@dataclass
class TemplateStep:
    """Individual step in a template."""
    id: str = None
    name: str = ""
    description: str = ""
    step_type: StepType = StepType.OPERATION
    parameters: Dict[str, Any] = None
    conditions: Dict[str, Any] = None
    order: int = 0
    
    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())
        if self.parameters is None:
            self.parameters = {}
        if self.conditions is None:
            self.conditions = {}
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute template step."""
        try:
            # Validate conditions
            if not self._check_conditions(context):
                return {
                    "success": False,
                    "step_id": self.id,
                    "error": "Step conditions not met"
                }
            
            # Execute based on step type
            if self.step_type == StepType.SELECTION:
                return await self._execute_selection(context)
            elif self.step_type == StepType.ANALYSIS:
                return await self._execute_analysis(context)
            elif self.step_type == StepType.OPERATION:
                return await self._execute_operation(context)
            elif self.step_type == StepType.VALIDATION:
                return await self._execute_validation(context)
            
            return {"success": True, "step_id": self.id}
            
        except Exception as e:
            return {
                "success": False,
                "step_id": self.id,
                "error": str(e)
            }
    
    def _check_conditions(self, context: Dict[str, Any]) -> bool:
        """Check if step conditions are met."""
        if not self.conditions:
            return True
        
        for condition_key, condition_value in self.conditions.items():
            if condition_key not in context:
                return False
            
            context_value = context[condition_key]
            if isinstance(condition_value, dict):
                # Complex condition checking
                operator = condition_value.get("operator", "==")
                expected = condition_value.get("value")
                
                if operator == "==" and context_value != expected:
                    return False
                elif operator == "!=" and context_value == expected:
                    return False
                elif operator == ">" and context_value <= expected:
                    return False
                elif operator == ">=" and context_value < expected:
                    return False
                elif operator == "<" and context_value >= expected:
                    return False
                elif operator == "<=" and context_value > expected:
                    return False
                elif operator == "in" and context_value not in expected:
                    return False
            else:
                # Simple equality check
                if context_value != condition_value:
                    return False
        
        return True
    
    async def _execute_selection(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute selection step."""
        selection_criteria = self.parameters.get("criteria", {})
        elements = context.get("available_elements", [])
        
        selected = []
        for element in elements:
            if self._matches_criteria(element, selection_criteria):
                selected.append(element)
        
        return {
            "success": True,
            "step_id": self.id,
            "selected_elements": selected,
            "selection_count": len(selected)
        }
    
    async def _execute_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute analysis step."""
        elements = context.get("selected_elements", [])
        analysis_type = self.parameters.get("type", "similarity")
        
        if analysis_type == "similarity":
            # Simple similarity analysis
            similarity_scores = {}
            for i, elem1 in enumerate(elements):
                for j, elem2 in enumerate(elements[i+1:], i+1):
                    text1 = getattr(elem1, 'text', '')
                    text2 = getattr(elem2, 'text', '')
                    # Simple text similarity
                    similarity = self._calculate_text_similarity(text1, text2)
                    similarity_scores[f"{i}_{j}"] = similarity
            
            return {
                "success": True,
                "step_id": self.id,
                "analysis_type": analysis_type,
                "similarity_scores": similarity_scores
            }
        
        return {
            "success": True,
            "step_id": self.id,
            "analysis_type": analysis_type
        }
    
    async def _execute_operation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute operation step."""
        operation_type = self.parameters.get("type", "merge")
        elements = context.get("selected_elements", [])
        
        if operation_type == "merge":
            separator = self.parameters.get("separator", " ")
            texts = []
            
            for element in elements:
                text = getattr(element, 'text', '')
                if text:
                    texts.append(text)
            
            merged_text = separator.join(texts)
            
            return {
                "success": True,
                "step_id": self.id,
                "operation": "merge",
                "result_text": merged_text,
                "source_count": len(elements)
            }
        
        elif operation_type == "split":
            if len(elements) != 1:
                return {
                    "success": False,
                    "step_id": self.id,
                    "error": "Split operation requires exactly one element"
                }
            
            element = elements[0]
            text = getattr(element, 'text', '')
            pattern = self.parameters.get("pattern", r"\s+")
            
            import re
            parts = re.split(pattern, text)
            parts = [part.strip() for part in parts if part.strip()]
            
            return {
                "success": True,
                "step_id": self.id,
                "operation": "split",
                "parts": parts,
                "part_count": len(parts)
            }
        
        return {
            "success": True,
            "step_id": self.id,
            "operation": operation_type
        }
    
    async def _execute_validation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute validation step."""
        validation_rules = self.parameters.get("rules", [])
        elements = context.get("selected_elements", [])
        
        issues = []
        for rule in validation_rules:
            rule_type = rule.get("type", "text_length")
            
            if rule_type == "text_length":
                min_length = rule.get("min_length", 0)
                max_length = rule.get("max_length", 1000)
                
                for element in elements:
                    text = getattr(element, 'text', '')
                    if len(text) < min_length:
                        issues.append(f"Element text too short: {len(text)} < {min_length}")
                    if len(text) > max_length:
                        issues.append(f"Element text too long: {len(text)} > {max_length}")
        
        return {
            "success": len(issues) == 0,
            "step_id": self.id,
            "validation_issues": issues,
            "issue_count": len(issues)
        }
    
    def _matches_criteria(self, element, criteria: Dict[str, Any]) -> bool:
        """Check if element matches selection criteria."""
        for key, value in criteria.items():
            element_value = getattr(element, key, None)
            
            if element_value is None:
                return False
            
            if hasattr(element_value, 'value'):
                element_value = element_value.value
            
            if element_value != value:
                return False
        
        return True
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate simple text similarity."""
        if not text1 or not text2:
            return 0.0
        
        # Simple word-based similarity
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union) if union else 0.0


@dataclass
class TemplateMetadata:
    """Metadata for operation templates."""
    id: str
    name: str
    description: str = ""
    category: TemplateCategory = TemplateCategory.USER_DEFINED
    template_type: TemplateType = TemplateType.CUSTOM
    author: str = ""
    version: str = "1.0"
    created_at: datetime = None
    updated_at: datetime = None
    tags: List[str] = None
    usage_count: int = 0
    success_rate: float = 1.0
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.tags is None:
            self.tags = []


@dataclass
class OperationTemplate:
    """Complete operation template definition."""
    metadata: TemplateMetadata
    steps: List[TemplateStep] = None
    global_parameters: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.steps is None:
            self.steps = []
        if self.global_parameters is None:
            self.global_parameters = {}
    
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complete template."""
        try:
            self.metadata.usage_count += 1
            self.metadata.updated_at = datetime.now()
            
            # Merge global parameters into context
            execution_context = {**context, **self.global_parameters}
            
            results = []
            for step in sorted(self.steps, key=lambda s: s.order):
                result = await step.execute(execution_context)
                results.append(result)
                
                if not result.get("success", False):
                    return {
                        "success": False,
                        "template_id": self.metadata.id,
                        "failed_step": step.id,
                        "results": results,
                        "error": result.get("error", "Step execution failed")
                    }
                
                # Update context with step results
                execution_context.update(result)
            
            # Update success rate
            self._update_success_rate(True)
            
            return {
                "success": True,
                "template_id": self.metadata.id,
                "results": results,
                "steps_completed": len(results)
            }
            
        except Exception as e:
            self._update_success_rate(False)
            return {
                "success": False,
                "template_id": self.metadata.id,
                "error": str(e)
            }
    
    def _update_success_rate(self, success: bool):
        """Update template success rate."""
        if self.metadata.usage_count == 1:
            self.metadata.success_rate = 1.0 if success else 0.0
        else:
            # Simple moving average
            current_rate = self.metadata.success_rate
            weight = 0.1  # Weight for new data point
            new_value = 1.0 if success else 0.0
            self.metadata.success_rate = (current_rate * (1 - weight)) + (new_value * weight)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            "metadata": {
                "id": self.metadata.id,
                "name": self.metadata.name,
                "description": self.metadata.description,
                "category": self.metadata.category.value,
                "template_type": self.metadata.template_type.value,
                "author": self.metadata.author,
                "version": self.metadata.version,
                "created_at": self.metadata.created_at.isoformat(),
                "updated_at": self.metadata.updated_at.isoformat(),
                "tags": self.metadata.tags,
                "usage_count": self.metadata.usage_count,
                "success_rate": self.metadata.success_rate
            },
            "steps": [
                {
                    "id": step.id,
                    "name": step.name,
                    "description": step.description,
                    "step_type": step.step_type.value,
                    "parameters": step.parameters,
                    "conditions": step.conditions,
                    "order": step.order
                }
                for step in self.steps
            ],
            "global_parameters": self.global_parameters
        }


class TemplateEngine:
    """Core engine for template management and execution."""
    
    def __init__(self, state_manager=None, event_bus=None):
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.templates: Dict[str, OperationTemplate] = {}
        
        self._load_built_in_templates()
    
    def _load_built_in_templates(self):
        """Load built-in operation templates."""
        # Simple merge template
        merge_template = OperationTemplate(
            metadata=TemplateMetadata(
                id="builtin_simple_merge",
                name="Simple Text Merge",
                description="Merge selected text elements with space separator",
                category=TemplateCategory.MERGE,
                template_type=TemplateType.BUILT_IN,
                author="System"
            ),
            steps=[
                TemplateStep(
                    name="Select Text Elements",
                    step_type=StepType.SELECTION,
                    parameters={"criteria": {"element_type": "TEXT"}},
                    order=1
                ),
                TemplateStep(
                    name="Merge Elements",
                    step_type=StepType.OPERATION,
                    parameters={"type": "merge", "separator": " "},
                    order=2
                ),
                TemplateStep(
                    name="Validate Result",
                    step_type=StepType.VALIDATION,
                    parameters={"rules": [{"type": "text_length", "min_length": 1}]},
                    order=3
                )
            ]
        )
        
        # Simple split template
        split_template = OperationTemplate(
            metadata=TemplateMetadata(
                id="builtin_simple_split",
                name="Simple Text Split",
                description="Split text element by whitespace",
                category=TemplateCategory.SPLIT,
                template_type=TemplateType.BUILT_IN,
                author="System"
            ),
            steps=[
                TemplateStep(
                    name="Select Single Element",
                    step_type=StepType.SELECTION,
                    parameters={"criteria": {"element_type": "TEXT"}},
                    conditions={"selected_count": 1},
                    order=1
                ),
                TemplateStep(
                    name="Split Element",
                    step_type=StepType.OPERATION,
                    parameters={"type": "split", "pattern": r"\s+"},
                    order=2
                ),
                TemplateStep(
                    name="Validate Parts",
                    step_type=StepType.VALIDATION,
                    parameters={"rules": [{"type": "text_length", "min_length": 1}]},
                    order=3
                )
            ]
        )
        
        self.templates[merge_template.metadata.id] = merge_template
        self.templates[split_template.metadata.id] = split_template
    
    def add_template(self, template: OperationTemplate):
        """Add template to engine."""
        self.templates[template.metadata.id] = template
    
    def remove_template(self, template_id: str):
        """Remove template from engine."""
        if template_id in self.templates:
            del self.templates[template_id]
    
    def get_templates_by_category(self, category: TemplateCategory) -> List[OperationTemplate]:
        """Get templates by category."""
        return [template for template in self.templates.values() 
                if template.metadata.category == category]
    
    def get_template(self, template_id: str) -> Optional[OperationTemplate]:
        """Get template by ID."""
        return self.templates.get(template_id)


class TemplateManagerWidget:
    """Widget for template management and execution."""
    
    def __init__(self, state_manager=None, event_bus=None, parent=None):
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.template_engine = TemplateEngine(state_manager, event_bus)
        self.tab_widget = None  # Placeholder
        
        # Mock PyQt signals
        self.template_executed = MockSignal()
        self.template_created = MockSignal()


class MockSignal:
    """Mock PyQt signal for testing."""
    
    def __init__(self):
        self.callbacks = []
    
    def connect(self, callback):
        self.callbacks.append(callback)
    
    def emit(self, *args):
        for callback in self.callbacks:
            callback(*args)