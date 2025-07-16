"""
Advanced Features for Merge/Split Operations Engine.

Agent 4 - Integration & Advanced Features (Issue #237)
This package provides advanced capabilities for merge/split operations
including batch processing, AI suggestions, templates, and automation.
"""

from .batch_processor import (
    BatchProcessor,
    BatchOperation,
    BatchStatus,
    BatchProgress,
    BatchResult,
    OperationBatch,
    BatchConfiguration
)

from .ai_suggestions import (
    AISuggestionsEngine,
    SuggestionType,
    MergeSuggestion,
    SplitSuggestion,
    SuggestionConfidence,
    AIModel,
    SuggestionFilter
)

from .template_system import (
    TemplateManager,
    OperationTemplate,
    TemplateType,
    TemplateParameter,
    TemplateLibrary,
    TemplateValidationError
)

from .automation_engine import (
    AutomationEngine,
    AutomationRule,
    RuleCondition,
    RuleAction,
    TriggerEvent,
    AutomationStatus
)

__all__ = [
    # Batch Processing
    'BatchProcessor',
    'BatchOperation',
    'BatchStatus',
    'BatchProgress',
    'BatchResult',
    'OperationBatch',
    'BatchConfiguration',
    
    # AI Suggestions
    'AISuggestionsEngine',
    'SuggestionType',
    'MergeSuggestion',
    'SplitSuggestion',
    'SuggestionConfidence',
    'AIModel',
    'SuggestionFilter',
    
    # Template System
    'TemplateManager',
    'OperationTemplate',
    'TemplateType',
    'TemplateParameter',
    'TemplateLibrary',
    'TemplateValidationError',
    
    # Automation Engine
    'AutomationEngine',
    'AutomationRule',
    'RuleCondition',
    'RuleAction',
    'TriggerEvent',
    'AutomationStatus',
]