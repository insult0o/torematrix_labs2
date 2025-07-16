"""
Workflow Management Module

This module provides comprehensive workflow management for document processing,
including validation workflows, automation pipelines, and progress tracking.
"""

# Validation Workflow System (Issue #30 - Agent 1)
try:
    from .validation import (
        ValidationWorkflowEngine,
        ValidationWorkflow,
        ValidationStep,
        WorkflowStatus,
        StepStatus,
        WorkflowTemplate,
        WorkflowProgress,
        WorkflowConfiguration,
        ValidationStepType,
        ValidationPriority
    )
    _validation_workflows_available = True
except ImportError:
    _validation_workflows_available = False

__all__ = []

# Add validation workflow components if available
if _validation_workflows_available:
    __all__.extend([
        # Core Workflow Engine - Agent 1 (Issue #260)
        'ValidationWorkflowEngine',
        'ValidationWorkflow',
        'ValidationStep',
        'WorkflowStatus',
        'StepStatus',
        'WorkflowTemplate',
        'WorkflowProgress',
        'WorkflowConfiguration',
        'ValidationStepType',
        'ValidationPriority',
    ])