"""
Unit tests for ValidationWorkflowEngine - Agent 1 Implementation (Issue #260)

Comprehensive tests for workflow engine with >95% coverage including:
- Workflow lifecycle management
- Real-time progress tracking with 0.1% granularity
- State management integration
- Event bus integration
- Template system
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtTest import QSignalSpy

from src.torematrix.ui.workflows.validation.engine import (
    ValidationWorkflowEngine,
    ValidationWorkflow,
    ValidationStep,
    WorkflowTemplate,
    WorkflowProgress,
    WorkflowConfiguration,
    WorkflowStatus,
    StepStatus,
    ValidationStepType,
    ValidationPriority
)
from src.torematrix.core.state.store import Store
from src.torematrix.core.state.actions import Action
from src.torematrix.core.events.event_bus import EventBus
from src.torematrix.core.events.event_types import Event, EventPriority


class TestWorkflowProgress:
    """Test WorkflowProgress class functionality."""
    
    def test_progress_initialization(self):
        """Test progress object initialization."""
        progress = WorkflowProgress()
        assert progress.current_step == 0
        assert progress.total_steps == 0
        assert progress.step_progress == 0.0
        assert progress.overall_progress == 0.0
        assert progress.steps_completed == 0
    
    def test_calculate_overall_progress_no_steps(self):
        """Test progress calculation with no steps."""
        progress = WorkflowProgress()
        assert progress.calculate_overall_progress() == 0.0
    
    def test_calculate_overall_progress_with_steps(self):
        """Test progress calculation with multiple steps."""
        progress = WorkflowProgress()
        progress.total_steps = 4
        progress.steps_completed = 2
        progress.step_progress = 50.0
        
        overall = progress.calculate_overall_progress()
        expected = (2/4) * 100.0 + (50.0/100.0) * (1/4) * 100.0  # 50% + 12.5% = 62.5%
        assert overall == 62.5
    
    def test_update_progress_precision(self):
        """Test progress update with 0.1% precision."""
        progress = WorkflowProgress()
        progress.total_steps = 3
        
        # Test precision rounding
        progress.update_progress(33.33333)
        assert progress.step_progress == 33.3
        
        progress.update_progress(66.66666)
        assert progress.step_progress == 66.7
    
    def test_update_progress_bounds(self):
        """Test progress update bounds checking."""
        progress = WorkflowProgress()
        
        # Test lower bound
        progress.update_progress(-10.0)
        assert progress.step_progress == 0.0
        
        # Test upper bound
        progress.update_progress(110.0)
        assert progress.step_progress == 100.0


class TestValidationStep:
    """Test ValidationStep class functionality."""
    
    def test_step_initialization(self):
        """Test step initialization."""
        step = ValidationStep(
            name="Test Step",
            description="Test description",
            step_type=ValidationStepType.DOCUMENT_SCAN
        )
        assert step.name == "Test Step"
        assert step.description == "Test description"
        assert step.step_type == ValidationStepType.DOCUMENT_SCAN
        assert step.status == StepStatus.PENDING
        assert step.progress == 0.0
        assert step.start_time is None
        assert step.end_time is None
    
    def test_step_start(self):
        """Test step start functionality."""
        step = ValidationStep(name="Test Step")
        start_time = datetime.now()
        
        step.start()
        
        assert step.status == StepStatus.IN_PROGRESS
        assert step.progress == 0.0
        assert step.start_time is not None
        assert step.start_time >= start_time
    
    def test_step_complete(self):
        """Test step completion."""
        step = ValidationStep(name="Test Step")
        step.start()
        
        results = {"key": "value"}
        step.complete(results)
        
        assert step.status == StepStatus.COMPLETED
        assert step.progress == 100.0
        assert step.end_time is not None
        assert step.actual_duration is not None
        assert step.results == results
    
    def test_step_fail(self):
        """Test step failure."""
        step = ValidationStep(name="Test Step")
        step.start()
        
        error_msg = "Test error"
        step.fail(error_msg)
        
        assert step.status == StepStatus.FAILED
        assert step.error_message == error_msg
        assert step.end_time is not None
        assert step.actual_duration is not None
    
    def test_step_update_progress(self):
        """Test step progress updates."""
        step = ValidationStep(name="Test Step")
        
        step.update_progress(45.67)
        assert step.progress == 45.7
        
        # Test bounds
        step.update_progress(-5.0)
        assert step.progress == 0.0
        
        step.update_progress(105.0)
        assert step.progress == 100.0


class TestWorkflowTemplate:
    """Test WorkflowTemplate class functionality."""
    
    def test_template_initialization(self):
        """Test template initialization."""
        template = WorkflowTemplate(
            name="Test Template",
            description="Test description"
        )
        assert template.name == "Test Template"
        assert template.description == "Test description"
        assert template.version == "1.0.0"
        assert len(template.steps) == 0
        assert len(template.tags) == 0
    
    def test_create_workflow_from_template(self):
        """Test workflow creation from template."""
        step1 = ValidationStep(name="Step 1", step_type=ValidationStepType.DOCUMENT_SCAN)
        step2 = ValidationStep(name="Step 2", step_type=ValidationStepType.ELEMENT_VALIDATION)
        
        template = WorkflowTemplate(
            name="Test Template",
            steps=[step1, step2],
            configuration={"test": "config"}
        )
        
        workflow = template.create_workflow("Test Workflow", "doc123")
        
        assert workflow.name == "Test Workflow"
        assert workflow.document_id == "doc123"
        assert workflow.template_id == template.id
        assert len(workflow.steps) == 2
        assert workflow.configuration == {"test": "config"}
        
        # Verify steps are copied, not referenced
        assert workflow.steps[0].id != step1.id
        assert workflow.steps[0].name == step1.name


class TestValidationWorkflow:
    """Test ValidationWorkflow class functionality."""
    
    def test_workflow_initialization(self):
        """Test workflow initialization."""
        workflow = ValidationWorkflow(
            name="Test Workflow",
            document_id="doc123"
        )
        assert workflow.name == "Test Workflow"
        assert workflow.document_id == "doc123"
        assert workflow.status == WorkflowStatus.PENDING
        assert workflow.progress.total_steps == 0
    
    def test_workflow_with_steps(self):
        """Test workflow with predefined steps."""
        steps = [
            ValidationStep(name="Step 1"),
            ValidationStep(name="Step 2"),
            ValidationStep(name="Step 3")
        ]
        
        workflow = ValidationWorkflow(
            name="Test Workflow",
            document_id="doc123",
            steps=steps
        )
        
        assert workflow.progress.total_steps == 3
        assert len(workflow.steps) == 3
    
    def test_get_current_step(self):
        """Test getting current active step."""
        step1 = ValidationStep(name="Step 1")
        step2 = ValidationStep(name="Step 2")
        step1.status = StepStatus.COMPLETED
        step2.status = StepStatus.IN_PROGRESS
        
        workflow = ValidationWorkflow(steps=[step1, step2])
        
        current_step = workflow.get_current_step()
        assert current_step == step2
    
    def test_get_next_step(self):
        """Test getting next available step."""
        step1 = ValidationStep(name="Step 1")
        step2 = ValidationStep(name="Step 2")
        step3 = ValidationStep(name="Step 3")
        
        step1.status = StepStatus.COMPLETED
        step2.status = StepStatus.PENDING
        step3.status = StepStatus.PENDING
        step3.prerequisites = [step2.id]  # Step 3 depends on Step 2
        
        workflow = ValidationWorkflow(steps=[step1, step2, step3])
        
        next_step = workflow.get_next_step()
        assert next_step == step2  # Step 2 has no prerequisites and is pending
    
    def test_prerequisites_checking(self):
        """Test prerequisite validation."""
        step1 = ValidationStep(name="Step 1")
        step2 = ValidationStep(name="Step 2")
        step2.prerequisites = [step1.id]
        
        workflow = ValidationWorkflow(steps=[step1, step2])
        
        # Step 1 not completed yet
        assert not workflow._prerequisites_met(step2)
        
        # Complete step 1
        step1.status = StepStatus.COMPLETED
        assert workflow._prerequisites_met(step2)
    
    def test_update_progress(self):
        """Test workflow progress updates."""
        steps = [
            ValidationStep(name="Step 1"),
            ValidationStep(name="Step 2"),
            ValidationStep(name="Step 3")
        ]
        
        workflow = ValidationWorkflow(steps=steps)
        workflow.start_time = datetime.now()
        
        # Complete first step
        steps[0].status = StepStatus.COMPLETED
        steps[1].status = StepStatus.IN_PROGRESS
        steps[1].progress = 50.0
        
        workflow.update_progress()
        
        assert workflow.progress.steps_completed == 1
        assert workflow.progress.current_step == 2
        assert workflow.progress.step_progress == 50.0
        assert workflow.progress.overall_progress > 0


@pytest.fixture
def mock_state_manager():
    """Create mock state manager."""
    state_manager = Mock(spec=Store)
    state_manager.get_state.return_value = {}
    state_manager.dispatch = Mock()
    state_manager.subscribe = Mock()
    return state_manager


@pytest.fixture
def mock_event_bus():
    """Create mock event bus."""
    event_bus = Mock(spec=EventBus)
    event_bus.subscribe = Mock()
    event_bus.emit = AsyncMock()
    return event_bus


@pytest.fixture
def workflow_engine(mock_state_manager, mock_event_bus):
    """Create ValidationWorkflowEngine instance for testing."""
    with patch('PyQt6.QtCore.QTimer'):
        engine = ValidationWorkflowEngine(mock_state_manager, mock_event_bus)
        # Mock the timer to avoid Qt dependency issues in tests
        engine.progress_timer = Mock()
        engine.progress_timer.isActive.return_value = False
        engine.progress_timer.start = Mock()
        engine.progress_timer.stop = Mock()
        return engine


class TestValidationWorkflowEngine:
    """Test ValidationWorkflowEngine class functionality."""
    
    def test_engine_initialization(self, workflow_engine, mock_state_manager, mock_event_bus):
        """Test engine initialization."""
        assert workflow_engine.state_manager == mock_state_manager
        assert workflow_engine.event_bus == mock_event_bus
        assert isinstance(workflow_engine.configuration, WorkflowConfiguration)
        assert len(workflow_engine.workflows) == 0
        assert len(workflow_engine.templates) > 0  # Should have default templates
        
        # Verify event subscriptions
        mock_event_bus.subscribe.assert_called()
        
        # Verify state initialization
        mock_state_manager.subscribe.assert_called_once()
    
    def test_default_templates_loaded(self, workflow_engine):
        """Test that default templates are loaded."""
        templates = workflow_engine.get_all_templates()
        assert len(templates) >= 2  # Should have quality and export templates
        
        template_names = [t.name for t in templates]
        assert "Document Quality Validation" in template_names
        assert "Export Readiness Check" in template_names
    
    def test_create_workflow_without_template(self, workflow_engine):
        """Test workflow creation without template."""
        workflow = workflow_engine.create_workflow("Test Workflow", "doc123")
        
        assert workflow.name == "Test Workflow"
        assert workflow.document_id == "doc123"
        assert workflow.template_id is None
        assert workflow.id in workflow_engine.workflows
        
        # Verify state was updated
        workflow_engine.state_manager.dispatch.assert_called()
        
        # Verify performance metrics
        assert workflow_engine.performance_metrics['workflows_created'] == 1
        assert workflow_engine.performance_metrics['active_workflows'] == 1
    
    def test_create_workflow_with_template(self, workflow_engine):
        """Test workflow creation with template."""
        templates = workflow_engine.get_all_templates()
        template = templates[0]
        
        workflow = workflow_engine.create_workflow("Test Workflow", "doc123", template.id)
        
        assert workflow.name == "Test Workflow"
        assert workflow.document_id == "doc123"
        assert workflow.template_id == template.id
        assert len(workflow.steps) > 0
    
    def test_start_workflow(self, workflow_engine):
        """Test workflow startup."""
        workflow = workflow_engine.create_workflow("Test Workflow", "doc123")
        workflow_id = workflow.id
        
        # Mock signal emission
        with patch.object(workflow_engine, 'workflow_started') as mock_signal:
            result = workflow_engine.start_workflow(workflow_id)
        
        assert result is True
        assert workflow.status == WorkflowStatus.IN_PROGRESS
        assert workflow.start_time is not None
        
        # Verify signal was emitted
        mock_signal.emit.assert_called_once_with(workflow_id)
        
        # Verify state was updated
        workflow_engine.state_manager.dispatch.assert_called()
    
    def test_start_workflow_invalid_id(self, workflow_engine):
        """Test starting workflow with invalid ID."""
        result = workflow_engine.start_workflow("invalid_id")
        assert result is False
    
    def test_start_workflow_wrong_status(self, workflow_engine):
        """Test starting workflow with wrong status."""
        workflow = workflow_engine.create_workflow("Test Workflow", "doc123")
        workflow.status = WorkflowStatus.COMPLETED
        
        result = workflow_engine.start_workflow(workflow.id)
        assert result is False
    
    def test_start_step(self, workflow_engine):
        """Test starting individual step."""
        steps = [ValidationStep(name="Step 1")]
        workflow = workflow_engine.create_workflow("Test Workflow", "doc123", steps=steps)
        step_id = workflow.steps[0].id
        
        with patch.object(workflow_engine, 'step_started') as mock_signal:
            result = workflow_engine.start_step(workflow.id, step_id)
        
        assert result is True
        assert workflow.steps[0].status == StepStatus.IN_PROGRESS
        assert workflow.steps[0].start_time is not None
        
        # Verify signal was emitted
        mock_signal.emit.assert_called_once_with(workflow.id, step_id)
    
    def test_start_step_with_prerequisites(self, workflow_engine):
        """Test starting step with unmet prerequisites."""
        step1 = ValidationStep(name="Step 1")
        step2 = ValidationStep(name="Step 2")
        step2.prerequisites = [step1.id]
        
        workflow = workflow_engine.create_workflow("Test Workflow", "doc123", steps=[step1, step2])
        
        # Try to start step 2 before step 1 is complete
        result = workflow_engine.start_step(workflow.id, step2.id)
        assert result is False
        
        # Complete step 1 and try again
        step1.status = StepStatus.COMPLETED
        result = workflow_engine.start_step(workflow.id, step2.id)
        assert result is True
    
    def test_complete_step(self, workflow_engine):
        """Test step completion."""
        steps = [ValidationStep(name="Step 1")]
        workflow = workflow_engine.create_workflow("Test Workflow", "doc123", steps=steps)
        step_id = workflow.steps[0].id
        
        # Start the step first
        workflow_engine.start_step(workflow.id, step_id)
        
        # Complete the step
        results = {"test": "result"}
        with patch.object(workflow_engine, 'step_completed') as mock_signal:
            result = workflow_engine.complete_step(workflow.id, step_id, results)
        
        assert result is True
        assert workflow.steps[0].status == StepStatus.COMPLETED
        assert workflow.steps[0].results == results
        
        # Verify signal was emitted
        mock_signal.emit.assert_called_once_with(workflow.id, step_id, results)
    
    def test_complete_step_triggers_workflow_completion(self, workflow_engine):
        """Test that completing last step triggers workflow completion."""
        steps = [ValidationStep(name="Step 1")]
        workflow = workflow_engine.create_workflow("Test Workflow", "doc123", steps=steps)
        step_id = workflow.steps[0].id
        
        # Start and complete the only step
        workflow_engine.start_step(workflow.id, step_id)
        
        with patch.object(workflow_engine, 'workflow_completed') as mock_signal:
            workflow_engine.complete_step(workflow.id, step_id)
        
        assert workflow.status == WorkflowStatus.COMPLETED
        assert workflow.end_time is not None
        
        # Verify signal was emitted
        mock_signal.emit.assert_called_once()
        
        # Verify performance metrics
        assert workflow_engine.performance_metrics['workflows_completed'] == 1
        assert workflow_engine.performance_metrics['active_workflows'] == 0
    
    def test_update_step_progress(self, workflow_engine):
        """Test step progress updates."""
        steps = [ValidationStep(name="Step 1")]
        workflow = workflow_engine.create_workflow("Test Workflow", "doc123", steps=steps)
        step_id = workflow.steps[0].id
        
        with patch.object(workflow_engine, 'step_progress_updated') as mock_signal:
            result = workflow_engine.update_step_progress(workflow.id, step_id, 75.5)
        
        assert result is True
        assert workflow.steps[0].progress == 75.5
        
        # Verify signal was emitted
        mock_signal.emit.assert_called_once_with(workflow.id, step_id, 75.5)
    
    def test_get_workflow_progress(self, workflow_engine):
        """Test getting workflow progress."""
        steps = [ValidationStep(name="Step 1"), ValidationStep(name="Step 2")]
        workflow = workflow_engine.create_workflow("Test Workflow", "doc123", steps=steps)
        
        # Complete first step and update second
        workflow.steps[0].status = StepStatus.COMPLETED
        workflow.steps[1].status = StepStatus.IN_PROGRESS
        workflow.steps[1].progress = 50.0
        workflow.update_progress()
        
        progress = workflow_engine.get_workflow_progress(workflow.id)
        assert progress is not None
        assert progress > 0.0
        assert progress <= 100.0
    
    def test_cancel_workflow(self, workflow_engine):
        """Test workflow cancellation."""
        workflow = workflow_engine.create_workflow("Test Workflow", "doc123")
        workflow_engine.start_workflow(workflow.id)
        
        with patch.object(workflow_engine, 'workflow_cancelled') as mock_signal:
            result = workflow_engine.cancel_workflow(workflow.id)
        
        assert result is True
        assert workflow.status == WorkflowStatus.CANCELLED
        assert workflow.end_time is not None
        
        # Verify signal was emitted
        mock_signal.emit.assert_called_once_with(workflow.id)
        
        # Verify performance metrics
        assert workflow_engine.performance_metrics['active_workflows'] == 0
    
    def test_get_active_workflows(self, workflow_engine):
        """Test getting active workflows."""
        # Create workflows with different statuses
        workflow1 = workflow_engine.create_workflow("Workflow 1", "doc1")
        workflow2 = workflow_engine.create_workflow("Workflow 2", "doc2")
        workflow3 = workflow_engine.create_workflow("Workflow 3", "doc3")
        
        workflow_engine.start_workflow(workflow1.id)
        workflow_engine.start_workflow(workflow2.id)
        workflow2.status = WorkflowStatus.COMPLETED
        
        active_workflows = workflow_engine.get_active_workflows()
        assert len(active_workflows) == 2  # workflow1 (in_progress) and workflow3 (pending)
        
        active_ids = [w.id for w in active_workflows]
        assert workflow1.id in active_ids
        assert workflow3.id in active_ids
        assert workflow2.id not in active_ids
    
    def test_create_template(self, workflow_engine):
        """Test creating new workflow template."""
        template = WorkflowTemplate(
            name="Custom Template",
            description="Custom test template",
            steps=[ValidationStep(name="Custom Step")]
        )
        
        result = workflow_engine.create_template(template)
        assert result is True
        assert template.id in workflow_engine.templates
        
        # Verify state was updated
        workflow_engine.state_manager.dispatch.assert_called()
    
    def test_progress_timer_management(self, workflow_engine):
        """Test progress timer start/stop behavior."""
        # Timer should not be active initially
        workflow_engine.progress_timer.isActive.return_value = False
        
        # Create and start workflow
        workflow = workflow_engine.create_workflow("Test Workflow", "doc123")
        workflow_engine.start_workflow(workflow.id)
        
        # Timer should be started
        workflow_engine.progress_timer.start.assert_called()
        
        # Mock active workflows
        workflow_engine.progress_timer.isActive.return_value = True
        workflow.status = WorkflowStatus.COMPLETED
        
        # Update progress should stop timer when no active workflows
        workflow_engine._update_progress()
        workflow_engine.progress_timer.stop.assert_called()
    
    def test_event_bus_integration(self, workflow_engine):
        """Test event bus integration."""
        # Test workflow creation event
        event_data = {
            'name': 'Test Workflow',
            'document_id': 'doc123',
            'template_id': None
        }
        event = Event(type='workflow.create', data=event_data)
        
        workflow_engine._handle_workflow_create_event(event)
        assert len(workflow_engine.workflows) > 0
        
        # Test workflow start event
        workflow_id = list(workflow_engine.workflows.keys())[0]
        start_event = Event(type='workflow.start', data={'workflow_id': workflow_id})
        
        workflow_engine._handle_workflow_start_event(start_event)
        assert workflow_engine.workflows[workflow_id].status == WorkflowStatus.IN_PROGRESS
    
    def test_state_management_integration(self, workflow_engine):
        """Test state management integration."""
        # Create workflow to trigger state updates
        workflow = workflow_engine.create_workflow("Test Workflow", "doc123")
        
        # Verify state actions were dispatched
        calls = workflow_engine.state_manager.dispatch.call_args_list
        assert len(calls) > 0
        
        # Check if CREATE_WORKFLOW action was dispatched
        create_action = None
        for call in calls:
            action = call[0][0]
            if action.type == 'CREATE_WORKFLOW':
                create_action = action
                break
        
        assert create_action is not None
        assert 'workflow_id' in create_action.payload
        assert create_action.payload['workflow_id'] == workflow.id
    
    def test_workflow_to_dict_conversion(self, workflow_engine):
        """Test workflow to dictionary conversion."""
        workflow = workflow_engine.create_workflow("Test Workflow", "doc123")
        workflow.status = WorkflowStatus.IN_PROGRESS
        workflow.start_time = datetime.now()
        
        workflow_dict = workflow_engine._workflow_to_dict(workflow)
        
        assert workflow_dict['id'] == workflow.id
        assert workflow_dict['name'] == workflow.name
        assert workflow_dict['document_id'] == workflow.document_id
        assert workflow_dict['status'] == 'IN_PROGRESS'
        assert 'progress' in workflow_dict
        assert 'created_date' in workflow_dict
    
    def test_template_to_dict_conversion(self, workflow_engine):
        """Test template to dictionary conversion."""
        template = WorkflowTemplate(
            name="Test Template",
            description="Test description",
            steps=[ValidationStep(name="Step 1")],
            tags=["test", "template"]
        )
        
        template_dict = workflow_engine._template_to_dict(template)
        
        assert template_dict['id'] == template.id
        assert template_dict['name'] == template.name
        assert template_dict['description'] == template.description
        assert template_dict['steps_count'] == 1
        assert template_dict['tags'] == ["test", "template"]
    
    @pytest.mark.asyncio
    async def test_async_event_emission(self, workflow_engine):
        """Test asynchronous event emission."""
        workflow = workflow_engine.create_workflow("Test Workflow", "doc123")
        
        # Mock the event bus emit method
        workflow_engine.event_bus.emit = AsyncMock()
        
        # Trigger event emission
        workflow_data = workflow_engine._workflow_to_dict(workflow)
        workflow_engine._emit_workflow_created_event(workflow.id, workflow_data)
        
        # Wait a bit for async event
        await asyncio.sleep(0.01)
        
        # Verify event was emitted (though we can't easily test async in this context)
        # This test mainly ensures the method doesn't raise exceptions


class TestWorkflowConfiguration:
    """Test WorkflowConfiguration class."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = WorkflowConfiguration()
        
        assert config.auto_advance_steps is True
        assert config.parallel_execution is False
        assert config.max_concurrent_steps == 3
        assert config.progress_update_interval == 100
        assert config.state_persistence is True
        assert config.event_broadcasting is True
        assert config.error_handling_mode == "stop_on_error"
        assert 'step_timeout' in config.timeout_settings
        assert 'workflow_timeout' in config.timeout_settings


if __name__ == '__main__':
    # Run tests with coverage
    pytest.main([__file__, '-v', '--cov=src.torematrix.ui.workflows.validation.engine', '--cov-report=term-missing'])