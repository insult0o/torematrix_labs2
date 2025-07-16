"""ToreMatrix UI Framework.

This module provides the user interface components for ToreMatrix,
including dialogs, widgets, themes, layouts, and workflow systems.
"""

from .dialogs import *

# Workflow systems (Agent 1 - Issue #260)
try:
    from .workflows import *
    _workflows_available = True
except ImportError:
    _workflows_available = False

__all__ = [
    # Dialog exports
    'BaseDialog',
    'DialogResult', 
    'DialogButton',
    'FileDialog',
    'FileFilter',
    'ConfirmationDialog',
    'ProgressDialog',
    'FormDialog',
    'FormField',
    'NotificationManager',
    'ToastNotification'
]

# Add workflow exports if available
if _workflows_available:
    __all__.extend([
        # Validation Workflow Engine - Agent 1 (Issue #260)
        'ValidationWorkflowEngine',
        'ValidationWorkflow',
        'ValidationStep',
        'WorkflowStatus',
        'StepStatus',
        'ValidationStepType',
        'ValidationPriority',
        'WorkflowProgress',
        'WorkflowTemplate',
        'WorkflowConfiguration'
    ])