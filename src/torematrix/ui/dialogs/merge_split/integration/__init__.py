"""
Integration & Advanced Features for Merge/Split Operations - Agent 4 Package.

This package provides the complete integration layer for merge/split operations,
including template systems, automation engines, and workflow optimization.
"""

# Template System Components
from .template_system import (
    TemplateEngine,
    OperationTemplate,
    TemplateStep,
    TemplateMetadata,
    TemplateManagerWidget,
    TemplateCategory,
    TemplateType,
    StepType
)

# Automation Engine Components
from .automation_engine import (
    AutomationExecutor,
    AutomationRule,
    RuleConditionSpec,
    RuleActionSpec,
    AutomationControlWidget,
    RuleType,
    RuleCondition,
    RuleAction,
    ExecutionMode,
    RuleStatus
)

# Workflow Optimizer Components
from .workflow_optimizer import (
    WorkflowOptimizerWidget,
    UserBehaviorAnalyzer,
    WorkflowSuggestionEngine,
    WorkflowPattern,
    WorkflowSuggestion,
    WorkflowMetrics,
    UserAction,
    WorkflowStage,
    UserSkillLevel
)

__all__ = [
    # Template System
    "TemplateEngine",
    "OperationTemplate", 
    "TemplateStep",
    "TemplateMetadata",
    "TemplateManagerWidget",
    "TemplateCategory",
    "TemplateType",
    "StepType",
    
    # Automation Engine
    "AutomationExecutor",
    "AutomationRule",
    "RuleConditionSpec", 
    "RuleActionSpec",
    "AutomationControlWidget",
    "RuleType",
    "RuleCondition",
    "RuleAction",
    "ExecutionMode",
    "RuleStatus",
    
    # Workflow Optimizer
    "WorkflowOptimizerWidget",
    "UserBehaviorAnalyzer",
    "WorkflowSuggestionEngine",
    "WorkflowPattern",
    "WorkflowSuggestion", 
    "WorkflowMetrics",
    "UserAction",
    "WorkflowStage",
    "UserSkillLevel"
]