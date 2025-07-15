"""
Tests for structure wizard.
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch, mock_open
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from torematrix.ui.tools.validation.structure_wizard import (
    StructureWizard,
    StructureWizardStep,
    StructureTemplate,
    StructureRule,
    ExportConfiguration,
    ExportFormat,
    ExecutionThread
)
from torematrix.core.models.element import Element, ElementType
from torematrix.core.operations.hierarchy import HierarchyManager
from torematrix.core.state import StateStore
from torematrix.core.events import EventBus
from torematrix.utils.geometry import Rect


@pytest.fixture
def qapp():
    """Create QApplication instance for testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_hierarchy_manager():
    """Create mock hierarchy manager."""
    manager = Mock(spec=HierarchyManager)
    manager.get_reading_order.return_value = ['elem1', 'elem2', 'elem3']
    return manager


@pytest.fixture
def mock_state_store():
    """Create mock state store."""
    store = Mock(spec=StateStore)
    return store


@pytest.fixture
def mock_event_bus():
    """Create mock event bus."""
    bus = Mock(spec=EventBus)
    return bus


@pytest.fixture
def sample_elements():
    """Create sample elements for testing."""
    return [
        Element(
            id='elem1',
            element_type=ElementType.TITLE,
            text='Test Title',
            bounds=Rect(0, 0, 100, 50),
            parent_id=None,
            children=['elem2']
        ),
        Element(
            id='elem2',
            element_type=ElementType.NARRATIVE_TEXT,
            text='Test paragraph content',
            bounds=Rect(0, 60, 100, 40),
            parent_id='elem1',
            children=[]
        ),
        Element(
            id='elem3',
            element_type=ElementType.LIST_ITEM,
            text='Test list item',
            bounds=Rect(0, 110, 100, 30),
            parent_id=None,
            children=[]
        )
    ]


class TestStructureWizard:
    """Test the StructureWizard class."""
    
    def test_init(self, qapp):
        """Test wizard initialization."""
        wizard = StructureWizard()
        
        assert wizard.hierarchy_manager is None
        assert wizard.state_store is None
        assert wizard.event_bus is None
        assert wizard.current_step == StructureWizardStep.WELCOME
        assert wizard.selected_template == StructureTemplate.DOCUMENT
        assert len(wizard.current_elements) == 0
        assert len(wizard.structure_rules) == 0
        assert isinstance(wizard.export_config, ExportConfiguration)
        assert len(wizard.wizard_results) == 0
    
    def test_set_managers(self, qapp, mock_hierarchy_manager, mock_state_store, mock_event_bus):
        """Test setting managers."""
        wizard = StructureWizard()
        
        wizard.set_hierarchy_manager(mock_hierarchy_manager)
        assert wizard.hierarchy_manager == mock_hierarchy_manager
        
        wizard.set_state_store(mock_state_store)
        assert wizard.state_store == mock_state_store
        
        wizard.set_event_bus(mock_event_bus)
        assert wizard.event_bus == mock_event_bus
    
    def test_show_elements(self, qapp, sample_elements):
        """Test showing elements."""
        wizard = StructureWizard()
        
        wizard.show_elements(sample_elements)
        
        assert wizard.current_elements == sample_elements
        assert len(wizard.current_elements) == 3
    
    def test_template_loading(self, qapp):
        """Test template loading."""
        wizard = StructureWizard()
        
        templates = wizard._load_templates()
        
        assert StructureTemplate.DOCUMENT in templates
        assert StructureTemplate.REPORT in templates
        assert StructureTemplate.MANUAL in templates
        assert StructureTemplate.ACADEMIC_PAPER in templates
        assert StructureTemplate.TECHNICAL_SPEC in templates
        assert StructureTemplate.CUSTOM in templates
        
        # Test template structure
        doc_template = templates[StructureTemplate.DOCUMENT]
        assert "name" in doc_template
        assert "description" in doc_template
        assert "hierarchy" in doc_template
    
    def test_step_navigation(self, qapp):
        """Test step navigation."""
        wizard = StructureWizard()
        
        # Test next step
        initial_step = wizard.current_step
        wizard._next_step()
        
        current_index = list(StructureWizardStep).index(wizard.current_step)
        initial_index = list(StructureWizardStep).index(initial_step)
        assert current_index == initial_index + 1
        
        # Test previous step
        wizard._previous_step()
        assert wizard.current_step == initial_step
    
    def test_template_selection(self, qapp):
        """Test template selection."""
        wizard = StructureWizard()
        
        # Test template change
        wizard._on_template_changed("Report")
        assert wizard.selected_template == StructureTemplate.REPORT
        
        # Test template preview update
        wizard._update_template_preview()
        # Should not raise exception
    
    def test_hierarchy_display_update(self, qapp, sample_elements):
        """Test hierarchy display update."""
        wizard = StructureWizard()
        
        wizard.current_elements = sample_elements
        wizard._update_hierarchy_display()
        
        # Check that tree widget was populated
        assert wizard.current_tree.topLevelItemCount() == 3
    
    def test_mapping_display_update(self, qapp, sample_elements):
        """Test mapping display update."""
        wizard = StructureWizard()
        
        wizard.current_elements = sample_elements
        wizard._update_mapping_display()
        
        # Check that lists were populated
        assert wizard.elements_list.count() == 3
        assert wizard.mapping_table.rowCount() == 3
    
    def test_export_configuration(self, qapp):
        """Test export configuration."""
        wizard = StructureWizard()
        
        # Test format change
        wizard._on_format_changed("XML")
        assert wizard.export_config.format == ExportFormat.XML
        
        # Test browse output path
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName') as mock_dialog:
            mock_dialog.return_value = ("/test/path/output.xml", "")
            wizard._browse_output_path()
            assert wizard.export_config.output_path == "/test/path/output.xml"
    
    def test_validation_rules(self, qapp):
        """Test validation rules management."""
        wizard = StructureWizard()
        
        # Test add rule
        wizard._add_validation_rule()
        # Should not raise exception
        
        # Test edit rule
        wizard._edit_validation_rule()
        # Should not raise exception
        
        # Test remove rule
        wizard._remove_validation_rule()
        # Should not raise exception
        
        # Test validation
        wizard._validate_structure()
        # Should not raise exception
    
    def test_wizard_completion(self, qapp):
        """Test wizard completion."""
        wizard = StructureWizard()
        
        # Test completion display update
        wizard.wizard_results = {"success": True, "execution_time": "2.5s"}
        wizard._update_completion_display()
        
        # Check that results were displayed
        assert "Wizard Results" in wizard.results_text.toPlainText()
    
    def test_step_display_update(self, qapp):
        """Test step display update."""
        wizard = StructureWizard()
        
        wizard.current_step = StructureWizardStep.TEMPLATE_SELECTION
        wizard._update_step_display()
        
        # Check that UI was updated
        step_index = list(StructureWizardStep).index(wizard.current_step)
        assert wizard.progress_bar.value() == step_index + 1
        assert wizard.step_stack.currentIndex() == step_index
    
    def test_signal_emission(self, qapp):
        """Test signal emission."""
        wizard = StructureWizard()
        
        # Mock signals
        wizard.structure_changed = Mock()
        wizard.export_completed = Mock()
        wizard.wizard_completed = Mock()
        wizard.step_changed = Mock()
        
        # Test step change signal
        wizard._next_step()
        # Should emit step_changed signal
        
        # Test wizard completion signal
        wizard.wizard_results = {"success": True}
        wizard._finish_wizard()
        wizard.wizard_completed.emit.assert_called_once()
    
    def test_execution_thread_handling(self, qapp):
        """Test execution thread handling."""
        wizard = StructureWizard()
        
        # Mock execution thread
        with patch('torematrix.ui.tools.validation.structure_wizard.ExecutionThread') as mock_thread:
            mock_thread_instance = Mock()
            mock_thread.return_value = mock_thread_instance
            
            wizard._start_execution()
            
            # Check that thread was created and started
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()
    
    def test_cancel_execution(self, qapp):
        """Test execution cancellation."""
        wizard = StructureWizard()
        
        # Mock execution thread
        mock_thread = Mock()
        wizard.execution_thread = mock_thread
        
        wizard._cancel_execution()
        
        mock_thread.terminate.assert_called_once()
    
    def test_new_wizard_start(self, qapp):
        """Test starting new wizard."""
        wizard = StructureWizard()
        
        # Set some state
        wizard.current_step = StructureWizardStep.COMPLETION
        wizard.current_elements = [Mock()]
        wizard.structure_rules = [Mock()]
        wizard.wizard_results = {"test": "data"}
        
        # Start new wizard
        wizard._start_new_wizard()
        
        # Check that state was reset
        assert wizard.current_step == StructureWizardStep.WELCOME
        assert len(wizard.current_elements) == 0
        assert len(wizard.structure_rules) == 0
        assert len(wizard.wizard_results) == 0


class TestStructureRule:
    """Test the StructureRule class."""
    
    def test_init(self):
        """Test rule initialization."""
        rule = StructureRule(
            name="Test Rule",
            description="Test description",
            element_types=[ElementType.TITLE],
            required=True,
            min_count=1,
            max_count=5
        )
        
        assert rule.name == "Test Rule"
        assert rule.description == "Test description"
        assert rule.element_types == [ElementType.TITLE]
        assert rule.required == True
        assert rule.min_count == 1
        assert rule.max_count == 5
    
    def test_defaults(self):
        """Test default values."""
        rule = StructureRule(
            name="Test Rule",
            description="Test description",
            element_types=[ElementType.TITLE]
        )
        
        assert rule.required == True
        assert rule.min_count == 0
        assert rule.max_count == -1
        assert len(rule.parent_types) == 0
        assert len(rule.child_types) == 0
        assert rule.validation_function is None


class TestExportConfiguration:
    """Test the ExportConfiguration class."""
    
    def test_init(self):
        """Test configuration initialization."""
        config = ExportConfiguration(
            format=ExportFormat.XML,
            include_metadata=False,
            output_path="/test/path"
        )
        
        assert config.format == ExportFormat.XML
        assert config.include_metadata == False
        assert config.output_path == "/test/path"
    
    def test_defaults(self):
        """Test default values."""
        config = ExportConfiguration()
        
        assert config.format == ExportFormat.JSON
        assert config.include_metadata == True
        assert config.include_coordinates == True
        assert config.include_relationships == True
        assert config.hierarchical_structure == True
        assert len(config.custom_fields) == 0
        assert config.output_path == ""
        assert config.template_path == ""
        assert len(config.options) == 0


class TestExecutionThread:
    """Test the ExecutionThread class."""
    
    def test_init(self, sample_elements):
        """Test thread initialization."""
        rules = [Mock(spec=StructureRule)]
        config = ExportConfiguration()
        
        thread = ExecutionThread(sample_elements, rules, config)
        
        assert thread.elements == sample_elements
        assert thread.rules == rules
        assert thread.export_config == config
    
    def test_run_success(self, sample_elements, qapp):
        """Test successful execution."""
        rules = [Mock(spec=StructureRule)]
        config = ExportConfiguration()
        
        thread = ExecutionThread(sample_elements, rules, config)
        
        # Mock signals
        thread.progress_updated = Mock()
        thread.status_updated = Mock()
        thread.execution_completed = Mock()
        
        # Run thread
        thread.run()
        
        # Check that signals were emitted
        assert thread.progress_updated.emit.call_count > 0
        assert thread.status_updated.emit.call_count > 0
        thread.execution_completed.emit.assert_called_once()
        
        # Check that success result was emitted
        call_args = thread.execution_completed.emit.call_args[0][0]
        assert call_args['success'] == True
    
    def test_run_failure(self, sample_elements, qapp):
        """Test execution failure."""
        rules = [Mock(spec=StructureRule)]
        config = ExportConfiguration()
        
        thread = ExecutionThread(sample_elements, rules, config)
        
        # Mock signals
        thread.progress_updated = Mock()
        thread.status_updated = Mock()
        thread.execution_completed = Mock()
        
        # Mock exception
        with patch.object(thread, 'status_updated') as mock_status:
            mock_status.emit.side_effect = Exception("Test error")
            
            thread.run()
            
            # Check that failure result was emitted
            call_args = thread.execution_completed.emit.call_args[0][0]
            assert call_args['success'] == False
            assert 'error' in call_args


class TestWizardSteps:
    """Test wizard step enumeration."""
    
    def test_step_values(self):
        """Test step enum values."""
        assert StructureWizardStep.WELCOME.value == "welcome"
        assert StructureWizardStep.TEMPLATE_SELECTION.value == "template_selection"
        assert StructureWizardStep.HIERARCHY_REVIEW.value == "hierarchy_review"
        assert StructureWizardStep.STRUCTURE_MAPPING.value == "structure_mapping"
        assert StructureWizardStep.VALIDATION_RULES.value == "validation_rules"
        assert StructureWizardStep.EXPORT_OPTIONS.value == "export_options"
        assert StructureWizardStep.EXECUTION.value == "execution"
        assert StructureWizardStep.COMPLETION.value == "completion"
    
    def test_step_count(self):
        """Test total number of steps."""
        assert len(StructureWizardStep) == 8


class TestStructureTemplates:
    """Test structure template enumeration."""
    
    def test_template_values(self):
        """Test template enum values."""
        assert StructureTemplate.DOCUMENT.value == "document"
        assert StructureTemplate.REPORT.value == "report"
        assert StructureTemplate.MANUAL.value == "manual"
        assert StructureTemplate.ACADEMIC_PAPER.value == "academic_paper"
        assert StructureTemplate.TECHNICAL_SPEC.value == "technical_spec"
        assert StructureTemplate.CUSTOM.value == "custom"
    
    def test_template_count(self):
        """Test total number of templates."""
        assert len(StructureTemplate) == 6


class TestExportFormats:
    """Test export format enumeration."""
    
    def test_format_values(self):
        """Test format enum values."""
        assert ExportFormat.JSON.value == "json"
        assert ExportFormat.XML.value == "xml"
        assert ExportFormat.CSV.value == "csv"
        assert ExportFormat.HTML.value == "html"
        assert ExportFormat.MARKDOWN.value == "markdown"
        assert ExportFormat.PDF.value == "pdf"
        assert ExportFormat.DOCX.value == "docx"
        assert ExportFormat.XLSX.value == "xlsx"
    
    def test_format_count(self):
        """Test total number of formats."""
        assert len(ExportFormat) == 8


if __name__ == '__main__':
    pytest.main([__file__])