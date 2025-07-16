"""
Workflow Systems for TORE Matrix Labs V3.

This package provides workflow management systems for document processing,
including validation workflows and quality assurance processes.
"""

try:
    from .validation import (
        ValidationWorkflowEngine,
        ValidationWorkflow,
        ValidationStep,
        ValidationIssue,
        ValidationStepType,
        ValidationStepStatus,
        ValidationPriority,
        ChecklistManager,
        ValidationChecklist,
        ChecklistExecution,
        ChecklistCriterion,
        ChecklistResponse,
        ChecklistItemType,
        ChecklistScope,
        QualityMetricsCalculator,
        QualityAssessment,
        QualityMetric,
        MetricType,
        MetricScope,
        ValidationReportGenerator,
        ValidationReport,
        ReportConfiguration,
        ReportType,
        ReportFormat,
        ReportScope,
        BatchValidationEngine,
        BatchValidationJob,
        ExportReadinessAssessment,
        ExportReadinessCheck,
        BatchProcessingMode,
        ExportReadinessLevel,
        BatchValidationStatus
    )
    _validation_available = True
except ImportError:
    _validation_available = False

__all__ = []

# Add validation workflow components if available
if _validation_available:
    __all__.extend([
        # Workflow Engine
        'ValidationWorkflowEngine',
        'ValidationWorkflow',
        'ValidationStep',
        'ValidationIssue',
        'ValidationStepType',
        'ValidationStepStatus',
        'ValidationPriority',
        
        # Checklist System
        'ChecklistManager',
        'ValidationChecklist',
        'ChecklistExecution',
        'ChecklistCriterion',
        'ChecklistResponse',
        'ChecklistItemType',
        'ChecklistScope',
        
        # Quality Metrics
        'QualityMetricsCalculator',
        'QualityAssessment',
        'QualityMetric',
        'MetricType',
        'MetricScope',
        
        # Report Generation
        'ValidationReportGenerator',
        'ValidationReport',
        'ReportConfiguration',
        'ReportType',
        'ReportFormat',
        'ReportScope',
        
        # Batch Validation
        'BatchValidationEngine',
        'BatchValidationJob',
        'ExportReadinessAssessment',
        'ExportReadinessCheck',
        'BatchProcessingMode',
        'ExportReadinessLevel',
        'BatchValidationStatus',
    ])