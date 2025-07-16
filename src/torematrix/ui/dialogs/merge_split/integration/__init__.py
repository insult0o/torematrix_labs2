"""
Integration Layer for Merge/Split Operations - Agent 4 Implementation.

This package provides the integration layer that unifies all Agent 1-3 components
into a cohesive system with advanced features including template systems,
automation engines, and workflow optimization.

Agent 4 Components:
- Template System: Reusable operation patterns and configurations
- Automation Engine: Rule-based operation execution 
- Workflow Optimizer: User behavior analysis and intelligent suggestions
- Integration Layer: Unified API and component coordination
"""

from .template_system import (
    TemplateEngine,
    TemplateManagerWidget,
    OperationTemplate,
    TemplateMetadata,
    TemplateStep,
    TemplateType,
    TemplateCategory,
    TemplatePatternMatcher
)

from .automation_engine import (
    AutomationExecutor,
    AutomationControlWidget,
    AutomationRule,
    RuleConditionSpec,
    RuleActionSpec,
    RuleType,
    RuleCondition,
    RuleAction,
    ExecutionMode,
    RuleStatus
)

from .workflow_optimizer import (
    WorkflowOptimizerWidget,
    UserBehaviorAnalyzer,
    WorkflowSuggestionEngine,
    UserAction,
    WorkflowPattern,
    WorkflowSuggestion,
    WorkflowMetrics,
    WorkflowStage,
    UserSkillLevel
)

__all__ = [
    # Template System
    'TemplateEngine',
    'TemplateManagerWidget', 
    'OperationTemplate',
    'TemplateMetadata',
    'TemplateStep',
    'TemplateType',
    'TemplateCategory',
    'TemplatePatternMatcher',
    
    # Automation Engine
    'AutomationExecutor',
    'AutomationControlWidget',
    'AutomationRule',
    'RuleConditionSpec',
    'RuleActionSpec',
    'RuleType',
    'RuleCondition',
    'RuleAction',
    'ExecutionMode',
    'RuleStatus',
    
    # Workflow Optimizer
    'WorkflowOptimizerWidget',
    'UserBehaviorAnalyzer',
    'WorkflowSuggestionEngine',
    'UserAction',
    'WorkflowPattern',
    'WorkflowSuggestion',
    'WorkflowMetrics',
    'WorkflowStage',
    'UserSkillLevel',
]