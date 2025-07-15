"""
Tests for export system.
"""

import pytest
import json
import csv
import xml.etree.ElementTree as ET
from unittest.mock import Mock, MagicMock, patch, mock_open
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from torematrix.ui.tools.validation.export_system import (
    ExportEngine,
    ExportWidget,
    ExportOptions,
    ExportResult,
    ExportFormat,
    ExportScope,
    ExportStatus,
    ExportThread
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
            bounds=Rect(10, 20, 100, 30),
            parent_id=None,
            children=['elem2'],
            metadata={'confidence': 0.95}
        ),
        Element(
            id='elem2',
            element_type=ElementType.NARRATIVE_TEXT,
            text='Test paragraph with some content',
            bounds=Rect(10, 60, 100, 40),
            parent_id='elem1',
            children=[],
            metadata={'confidence': 0.88}
        ),
        Element(
            id='elem3',
            element_type=ElementType.LIST_ITEM,
            text='Test list item',
            bounds=Rect(20, 110, 80, 20),
            parent_id=None,
            children=[],
            metadata={'confidence': 0.92}
        )
    ]


@pytest.fixture
def export_options():
    """Create test export options."""
    return ExportOptions(
        format=ExportFormat.JSON,
        scope=ExportScope.ALL_ELEMENTS,
        include_metadata=True,
        include_coordinates=True,
        include_hierarchy=True,
        output_path="/test/output.json"
    )


class TestExportEngine:
    """Test the ExportEngine class."""
    
    def test_init(self):
        """Test engine initialization."""
        engine = ExportEngine()
        
        assert engine.logger is not None
        assert len(engine.supported_formats) > 0
        assert ExportFormat.JSON in engine.supported_formats
        assert ExportFormat.XML in engine.supported_formats
        assert ExportFormat.CSV in engine.supported_formats
        assert ExportFormat.HTML in engine.supported_formats
        assert ExportFormat.MARKDOWN in engine.supported_formats
        assert ExportFormat.TXT in engine.supported_formats
        assert ExportFormat.YAML in engine.supported_formats
    
    def test_validate_options(self, export_options):
        """Test options validation."""
        engine = ExportEngine()
        
        # Valid options
        assert engine._validate_options(export_options) == True
        
        # Invalid options - no output path
        invalid_options = ExportOptions(output_path="")
        assert engine._validate_options(invalid_options) == False
    
    def test_filter_elements(self, sample_elements, export_options):
        """Test element filtering."""
        engine = ExportEngine()
        
        # No filter
        filtered = engine._filter_elements(sample_elements, export_options)
        assert len(filtered) == 3
        
        # Filter by element types
        export_options.filter_types = [ElementType.TITLE]
        filtered = engine._filter_elements(sample_elements, export_options)
        assert len(filtered) == 1
        assert filtered[0].element_type == ElementType.TITLE
    
    def test_export_json(self, sample_elements, export_options):
        """Test JSON export."""
        engine = ExportEngine()
        
        result = engine._export_json(sample_elements, export_options)
        
        # Parse and validate JSON
        data = json.loads(result)
        assert "export_info" in data
        assert "elements" in data
        assert data["export_info"]["format"] == "json"
        assert data["export_info"]["element_count"] == 3
        assert len(data["elements"]) == 3
        
        # Check element structure
        element = data["elements"][0]
        assert "id" in element
        assert "type" in element
        assert "text" in element
        assert "coordinates" in element
        assert "metadata" in element
        assert "parent_id" in element
        assert "children" in element
    
    def test_export_xml(self, sample_elements, export_options):
        """Test XML export."""
        engine = ExportEngine()
        
        result = engine._export_xml(sample_elements, export_options)
        
        # Parse and validate XML
        root = ET.fromstring(result)
        assert root.tag == "document"
        
        # Check export info
        export_info = root.find("export_info")
        assert export_info is not None
        assert export_info.find("format").text == "xml"
        assert export_info.find("element_count").text == "3"
        
        # Check elements
        elements = root.find("elements")
        assert elements is not None
        assert len(elements.findall("element")) == 3
        
        # Check element structure
        element = elements.find("element")
        assert element.get("id") is not None
        assert element.get("type") is not None
        assert element.find("text") is not None
        assert element.find("coordinates") is not None
    
    def test_export_csv(self, sample_elements, export_options):
        """Test CSV export."""
        engine = ExportEngine()
        
        result = engine._export_csv(sample_elements, export_options)
        
        # Parse and validate CSV
        lines = result.strip().split('\n')
        assert len(lines) == 4  # Header + 3 elements
        
        # Check header
        header = lines[0].split(',')
        assert 'id' in header
        assert 'type' in header
        assert 'text' in header
        assert 'x' in header
        assert 'y' in header
        assert 'width' in header
        assert 'height' in header
        assert 'parent_id' in header
        assert 'children' in header
        assert 'metadata' in header
        
        # Check data rows
        for i in range(1, 4):
            row = lines[i].split(',')
            assert len(row) == len(header)
    
    def test_export_html(self, sample_elements, export_options):
        """Test HTML export."""
        engine = ExportEngine()
        
        result = engine._export_html(sample_elements, export_options)
        
        # Check HTML structure
        assert result.startswith('<!DOCTYPE html>')
        assert '<html>' in result
        assert '<head>' in result
        assert '<body>' in result
        assert '<title>Document Export</title>' in result
        assert 'Total elements: 3' in result
        
        # Check elements
        assert 'elem1' in result
        assert 'elem2' in result
        assert 'elem3' in result
    
    def test_export_markdown(self, sample_elements, export_options):
        """Test Markdown export."""
        engine = ExportEngine()
        
        result = engine._export_markdown(sample_elements, export_options)
        
        # Check Markdown structure
        assert result.startswith('# Document Export')
        assert 'Total elements: 3' in result
        assert '## Element: elem1' in result
        assert '## Element: elem2' in result
        assert '## Element: elem3' in result
        assert '**Type:**' in result
        assert '**Text:**' in result
        assert '**Coordinates:**' in result
    
    def test_export_txt(self, sample_elements, export_options):
        """Test plain text export."""
        engine = ExportEngine()
        
        result = engine._export_txt(sample_elements, export_options)
        
        # Check text structure
        assert result.startswith('Document Export')
        assert 'Total elements: 3' in result
        assert 'Element 1: elem1' in result
        assert 'Element 2: elem2' in result
        assert 'Element 3: elem3' in result
        assert 'Type:' in result
        assert 'Text:' in result
        assert 'Coordinates:' in result
    
    def test_export_yaml(self, sample_elements, export_options):
        """Test YAML export."""
        engine = ExportEngine()
        
        result = engine._export_yaml(sample_elements, export_options)
        
        # Check YAML structure
        assert 'export_info:' in result
        assert 'format: yaml' in result
        assert 'element_count: 3' in result
        assert 'elements:' in result
        assert 'id: elem1' in result
        assert 'type: title' in result
    
    def test_export_with_options(self, sample_elements):
        """Test export with various options."""
        engine = ExportEngine()
        
        # Test without coordinates
        options = ExportOptions(
            format=ExportFormat.JSON,
            include_coordinates=False,
            output_path="/test/output.json"
        )
        result = engine._export_json(sample_elements, options)
        data = json.loads(result)
        assert "coordinates" not in data["elements"][0]
        
        # Test without metadata
        options = ExportOptions(
            format=ExportFormat.JSON,
            include_metadata=False,
            output_path="/test/output.json"
        )
        result = engine._export_json(sample_elements, options)
        data = json.loads(result)
        assert "metadata" not in data["elements"][0]
        
        # Test with text length limit
        options = ExportOptions(
            format=ExportFormat.JSON,
            max_text_length=10,
            output_path="/test/output.json"
        )
        result = engine._export_json(sample_elements, options)
        data = json.loads(result)
        assert len(data["elements"][1]["text"]) <= 10
    
    def test_write_to_file(self, export_options):
        """Test file writing."""
        engine = ExportEngine()
        
        test_data = "test export data"
        
        with patch('builtins.open', mock_open()) as mock_file:
            file_size = engine._write_to_file(test_data, export_options)
            
            # Check that file was opened and written
            mock_file.assert_called_once_with(export_options.output_path, 'w', encoding='utf-8')
            mock_file().write.assert_called_once_with(test_data)
            
            # Check file size
            assert file_size == len(test_data.encode('utf-8'))
    
    def test_export_success(self, sample_elements, export_options):
        """Test successful export."""
        engine = ExportEngine()
        
        with patch.object(engine, '_write_to_file') as mock_write:
            mock_write.return_value = 1000
            
            result = engine.export(sample_elements, export_options)
            
            assert result.success == True
            assert result.export_path == export_options.output_path
            assert result.format == export_options.format
            assert result.element_count == 3
            assert result.file_size == 1000
            assert result.execution_time > 0
    
    def test_export_failure(self, sample_elements, export_options):
        """Test export failure."""
        engine = ExportEngine()
        
        # Test with invalid options
        invalid_options = ExportOptions(output_path="")
        result = engine.export(sample_elements, invalid_options)
        
        assert result.success == False
        assert "Invalid export options" in result.error_message
    
    def test_export_unsupported_format(self, sample_elements, export_options):
        """Test export with unsupported format."""
        engine = ExportEngine()
        
        # Remove format from supported formats
        del engine.supported_formats[ExportFormat.JSON]
        
        result = engine.export(sample_elements, export_options)
        
        assert result.success == False
        assert "Unsupported format" in result.error_message


class TestExportWidget:
    """Test the ExportWidget class."""
    
    def test_init(self, qapp):
        """Test widget initialization."""
        widget = ExportWidget()
        
        assert widget.hierarchy_manager is None
        assert widget.state_store is None
        assert widget.event_bus is None
        assert isinstance(widget.export_engine, ExportEngine)
        assert len(widget.current_elements) == 0
        assert isinstance(widget.export_options, ExportOptions)
    
    def test_set_managers(self, qapp, mock_hierarchy_manager, mock_state_store, mock_event_bus):
        """Test setting managers."""
        widget = ExportWidget()
        
        widget.set_hierarchy_manager(mock_hierarchy_manager)
        assert widget.hierarchy_manager == mock_hierarchy_manager
        
        widget.set_state_store(mock_state_store)
        assert widget.state_store == mock_state_store
        
        widget.set_event_bus(mock_event_bus)
        assert widget.event_bus == mock_event_bus
    
    def test_show_elements(self, qapp, sample_elements):
        """Test showing elements."""
        widget = ExportWidget()
        
        widget.show_elements(sample_elements)
        
        assert widget.current_elements == sample_elements
        assert widget.elements_tree.topLevelItemCount() == 3
    
    def test_options_update(self, qapp):
        """Test options update."""
        widget = ExportWidget()
        
        # Test format change
        widget.format_combo.setCurrentText("XML")
        widget._update_options()
        assert widget.export_options.format == ExportFormat.XML
        
        # Test scope change
        widget.scope_combo.setCurrentText("Selected Elements")
        widget._update_options()
        assert widget.export_options.scope == ExportScope.SELECTED_ELEMENTS
        
        # Test include options
        widget.include_metadata_cb.setChecked(False)
        widget._update_options()
        assert widget.export_options.include_metadata == False
        
        widget.include_coordinates_cb.setChecked(False)
        widget._update_options()
        assert widget.export_options.include_coordinates == False
        
        # Test text options
        widget.max_text_length_spin.setValue(100)
        widget._update_options()
        assert widget.export_options.max_text_length == 100
        
        widget.pretty_print_cb.setChecked(False)
        widget._update_options()
        assert widget.export_options.pretty_print == False
    
    def test_browse_output_path(self, qapp):
        """Test browsing for output path."""
        widget = ExportWidget()
        
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName') as mock_dialog:
            mock_dialog.return_value = ("/test/path/output.json", "")
            
            widget._browse_output_path()
            
            assert widget.output_path_edit.text() == "/test/path/output.json"
    
    def test_preview_export(self, qapp, sample_elements):
        """Test export preview."""
        widget = ExportWidget()
        
        widget.show_elements(sample_elements)
        widget._preview_export()
        
        # Check that preview tab was activated
        assert widget.preview_tabs.currentIndex() == 1
        
        # Check that preview was updated
        preview_text = widget.output_preview.toPlainText()
        assert len(preview_text) > 0
    
    def test_start_export(self, qapp, sample_elements):
        """Test starting export."""
        widget = ExportWidget()
        
        widget.show_elements(sample_elements)
        widget.export_options.output_path = "/test/output.json"
        
        with patch('torematrix.ui.tools.validation.export_system.ExportThread') as mock_thread:
            mock_thread_instance = Mock()
            mock_thread.return_value = mock_thread_instance
            
            widget._start_export()
            
            # Check that thread was created and started
            mock_thread.assert_called_once()
            mock_thread_instance.start.assert_called_once()
            
            # Check UI state
            assert widget.export_button.isEnabled() == False
            assert widget.cancel_button.isEnabled() == True
    
    def test_start_export_validation(self, qapp):
        """Test export validation."""
        widget = ExportWidget()
        
        with patch('PyQt6.QtWidgets.QMessageBox.warning') as mock_warning:
            # Test with no elements
            widget._start_export()
            mock_warning.assert_called_with(widget, "Export Error", "No elements to export")
            
            # Test with no output path
            widget.current_elements = [Mock()]
            widget._start_export()
            mock_warning.assert_called_with(widget, "Export Error", "Please specify output path")
    
    def test_cancel_export(self, qapp):
        """Test canceling export."""
        widget = ExportWidget()
        
        # Mock export thread
        mock_thread = Mock()
        widget.export_thread = mock_thread
        
        widget._cancel_export()
        
        mock_thread.terminate.assert_called_once()
        assert widget.export_button.isEnabled() == True
        assert widget.cancel_button.isEnabled() == False
    
    def test_export_completion_success(self, qapp):
        """Test successful export completion."""
        widget = ExportWidget()
        
        result = ExportResult(
            success=True,
            export_path="/test/output.json",
            format=ExportFormat.JSON,
            element_count=3,
            file_size=1000,
            execution_time=2.5
        )
        
        with patch('PyQt6.QtWidgets.QMessageBox.information') as mock_info:
            widget._on_export_completed(result)
            
            mock_info.assert_called_once()
            assert widget.export_button.isEnabled() == True
            assert widget.cancel_button.isEnabled() == False
            assert widget.progress_bar.value() == 100
    
    def test_export_completion_failure(self, qapp):
        """Test failed export completion."""
        widget = ExportWidget()
        
        result = ExportResult(
            success=False,
            export_path="",
            format=ExportFormat.JSON,
            element_count=0,
            file_size=0,
            execution_time=0.0,
            error_message="Test error"
        )
        
        with patch('PyQt6.QtWidgets.QMessageBox.critical') as mock_error:
            widget._on_export_completed(result)
            
            mock_error.assert_called_once()
            assert widget.export_button.isEnabled() == True
            assert widget.cancel_button.isEnabled() == False
            assert widget.progress_bar.value() == 0


class TestExportOptions:
    """Test the ExportOptions class."""
    
    def test_init(self):
        """Test options initialization."""
        options = ExportOptions(
            format=ExportFormat.XML,
            scope=ExportScope.SELECTED_ELEMENTS,
            include_metadata=False,
            output_path="/test/path"
        )
        
        assert options.format == ExportFormat.XML
        assert options.scope == ExportScope.SELECTED_ELEMENTS
        assert options.include_metadata == False
        assert options.output_path == "/test/path"
    
    def test_defaults(self):
        """Test default values."""
        options = ExportOptions()
        
        assert options.format == ExportFormat.JSON
        assert options.scope == ExportScope.ALL_ELEMENTS
        assert options.include_metadata == True
        assert options.include_coordinates == True
        assert options.include_hierarchy == True
        assert options.include_relationships == True
        assert options.include_text == True
        assert options.include_images == False
        assert options.flatten_hierarchy == False
        assert len(options.custom_fields) == 0
        assert len(options.filter_types) == 0
        assert options.max_text_length == -1
        assert options.encoding == "utf-8"
        assert options.pretty_print == True
        assert options.compression == False
        assert options.output_path == ""
        assert options.template_path == ""
        assert len(options.additional_options) == 0


class TestExportResult:
    """Test the ExportResult class."""
    
    def test_init(self):
        """Test result initialization."""
        result = ExportResult(
            success=True,
            export_path="/test/output.json",
            format=ExportFormat.JSON,
            element_count=5,
            file_size=2000,
            execution_time=1.5,
            error_message="",
            warnings=["Warning 1"],
            metadata={"key": "value"}
        )
        
        assert result.success == True
        assert result.export_path == "/test/output.json"
        assert result.format == ExportFormat.JSON
        assert result.element_count == 5
        assert result.file_size == 2000
        assert result.execution_time == 1.5
        assert result.error_message == ""
        assert result.warnings == ["Warning 1"]
        assert result.metadata == {"key": "value"}
    
    def test_defaults(self):
        """Test default values."""
        result = ExportResult(
            success=True,
            export_path="/test/output.json",
            format=ExportFormat.JSON,
            element_count=5,
            file_size=2000,
            execution_time=1.5
        )
        
        assert result.error_message == ""
        assert len(result.warnings) == 0
        assert len(result.metadata) == 0


class TestExportThread:
    """Test the ExportThread class."""
    
    def test_init(self, sample_elements, export_options):
        """Test thread initialization."""
        engine = ExportEngine()
        
        thread = ExportThread(sample_elements, export_options, engine)
        
        assert thread.elements == sample_elements
        assert thread.options == export_options
        assert thread.engine == engine
    
    def test_run_success(self, sample_elements, export_options, qapp):
        """Test successful thread execution."""
        engine = ExportEngine()
        
        thread = ExportThread(sample_elements, export_options, engine)
        
        # Mock signals
        thread.progress_updated = Mock()
        thread.status_updated = Mock()
        thread.export_completed = Mock()
        
        # Mock engine export
        mock_result = ExportResult(
            success=True,
            export_path="/test/output.json",
            format=ExportFormat.JSON,
            element_count=3,
            file_size=1000,
            execution_time=1.0
        )
        
        with patch.object(engine, 'export', return_value=mock_result):
            thread.run()
            
            # Check that signals were emitted
            assert thread.progress_updated.emit.call_count > 0
            assert thread.status_updated.emit.call_count > 0
            thread.export_completed.emit.assert_called_once_with(mock_result)
    
    def test_run_failure(self, sample_elements, export_options, qapp):
        """Test thread execution failure."""
        engine = ExportEngine()
        
        thread = ExportThread(sample_elements, export_options, engine)
        
        # Mock signals
        thread.progress_updated = Mock()
        thread.status_updated = Mock()
        thread.export_completed = Mock()
        
        # Mock engine export to raise exception
        with patch.object(engine, 'export', side_effect=Exception("Test error")):
            thread.run()
            
            # Check that error result was emitted
            call_args = thread.export_completed.emit.call_args[0][0]
            assert call_args.success == False
            assert "Test error" in call_args.error_message


class TestExportEnums:
    """Test export-related enumerations."""
    
    def test_export_format(self):
        """Test export format enumeration."""
        assert ExportFormat.JSON.value == "json"
        assert ExportFormat.XML.value == "xml"
        assert ExportFormat.CSV.value == "csv"
        assert ExportFormat.HTML.value == "html"
        assert ExportFormat.MARKDOWN.value == "markdown"
        assert ExportFormat.DOCX.value == "docx"
        assert ExportFormat.PDF.value == "pdf"
        assert ExportFormat.XLSX.value == "xlsx"
        assert ExportFormat.TXT.value == "txt"
        assert ExportFormat.YAML.value == "yaml"
    
    def test_export_scope(self):
        """Test export scope enumeration."""
        assert ExportScope.ALL_ELEMENTS.value == "all_elements"
        assert ExportScope.SELECTED_ELEMENTS.value == "selected_elements"
        assert ExportScope.CURRENT_PAGE.value == "current_page"
        assert ExportScope.HIERARCHY_BRANCH.value == "hierarchy_branch"
        assert ExportScope.FILTERED_ELEMENTS.value == "filtered_elements"
    
    def test_export_status(self):
        """Test export status enumeration."""
        assert ExportStatus.PENDING.value == "pending"
        assert ExportStatus.PREPARING.value == "preparing"
        assert ExportStatus.EXPORTING.value == "exporting"
        assert ExportStatus.COMPLETED.value == "completed"
        assert ExportStatus.FAILED.value == "failed"
        assert ExportStatus.CANCELLED.value == "cancelled"


if __name__ == '__main__':
    pytest.main([__file__])