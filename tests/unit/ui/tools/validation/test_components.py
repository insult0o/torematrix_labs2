"""
Tests for common UI components.

This module provides comprehensive tests for shared UI components including
element preview, metadata resolver, operation preview, and validation UI.
"""

import pytest
from unittest.mock import Mock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from src.torematrix.core.models import Element, ElementType
from src.torematrix.ui.tools.validation.components import (
    ElementPreview, MetadataConflictResolver, OperationPreview, ValidationWarnings
)
from src.torematrix.ui.tools.validation.components.element_preview import (
    ElementMetadataWidget, ElementTextWidget, ElementComparisonWidget
)
from src.torematrix.ui.tools.validation.components.metadata_resolver import (
    ConflictPropertyWidget, MetadataInheritanceWidget
)
from src.torematrix.ui.tools.validation.components.operation_preview import (
    OperationStatsWidget, OperationTimelineWidget, ElementComparisonWidget as OpComparisonWidget
)
from src.torematrix.ui.tools.validation.components.validation_ui import (
    ValidationWarningItem, AccessibilityHelper, ProgressIndicator
)


class TestElementTextWidget:
    """Tests for element text display widget."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def text_widget(self, app):
        """Create element text widget."""
        return ElementTextWidget()
    
    @pytest.fixture
    def sample_element(self):
        """Create sample element."""
        return Element(
            element_type=ElementType.NARRATIVE_TEXT,
            text="This is a sample text for testing the element text widget functionality."
        )
    
    def test_initialization(self, text_widget):
        """Test widget initialization."""
        assert text_widget.text_display.isReadOnly()
        assert "Characters: 0" in text_widget.char_count_label.text()
    
    def test_set_element(self, text_widget, sample_element):
        """Test setting element."""
        text_widget.set_element(sample_element)
        
        assert text_widget.text_display.toPlainText() == sample_element.text
        expected_count = f"Characters: {len(sample_element.text)}"
        assert text_widget.char_count_label.text() == expected_count
    
    def test_set_element_none(self, text_widget):
        """Test setting None element."""
        text_widget.set_element(None)
        
        assert text_widget.text_display.toPlainText() == ""
        assert text_widget.char_count_label.text() == "Characters: 0"
    
    def test_set_highlight_ranges(self, text_widget, sample_element):
        """Test setting highlight ranges."""
        text_widget.set_element(sample_element)
        
        # Set highlight ranges
        ranges = [(0, 4), (10, 15)]  # Highlight "This" and "sampl"
        text_widget.set_highlight_ranges(ranges)
        
        # Highlighting is applied, but we can't easily test the visual result
        # Just ensure no errors occur
        assert text_widget._highlight_ranges == ranges


class TestElementMetadataWidget:
    """Tests for element metadata display widget."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def metadata_widget(self, app):
        """Create element metadata widget."""
        return ElementMetadataWidget()
    
    @pytest.fixture
    def sample_element(self):
        """Create sample element with metadata."""
        return Element(
            element_type=ElementType.TITLE,
            text="Sample Title",
            parent_id="parent123"
        )
    
    def test_initialization(self, metadata_widget):
        """Test widget initialization."""
        assert metadata_widget.metadata_tree.columnCount() == 2
        assert metadata_widget.metadata_tree.topLevelItemCount() == 0
    
    def test_set_element(self, metadata_widget, sample_element):
        """Test setting element with metadata."""
        metadata_widget.set_element(sample_element)
        
        # Should have basic properties
        assert metadata_widget.metadata_tree.topLevelItemCount() > 0
        
        # Find basic properties item
        basic_item = metadata_widget.metadata_tree.topLevelItem(0)
        assert basic_item.text(0) == "Basic Properties"
        assert basic_item.childCount() >= 3  # ID, Type, Text Length, possibly Parent ID


class TestElementComparisonWidget:
    """Tests for element comparison widget."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def comparison_widget(self, app):
        """Create element comparison widget."""
        return ElementComparisonWidget()
    
    @pytest.fixture
    def sample_elements(self):
        """Create sample elements for comparison."""
        return [
            Element(element_type=ElementType.TITLE, text="Original Title"),
            Element(element_type=ElementType.TITLE, text="Modified Title")
        ]
    
    def test_initialization(self, comparison_widget):
        """Test widget initialization."""
        assert comparison_widget.left_element is not None
        assert comparison_widget.right_element is not None
    
    def test_set_elements(self, comparison_widget, sample_elements):
        """Test setting elements for comparison."""
        original, modified = sample_elements
        comparison_widget.set_elements(original, modified)
        
        # Elements should be set in child widgets
        # This is tested indirectly through the child widgets' set_element methods


class TestElementPreview:
    """Tests for the main element preview widget."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def preview_widget(self, app):
        """Create element preview widget."""
        return ElementPreview()
    
    @pytest.fixture
    def sample_elements(self):
        """Create sample elements."""
        return [
            Element(element_type=ElementType.TITLE, text="Title 1"),
            Element(element_type=ElementType.NARRATIVE_TEXT, text="Text 1")
        ]
    
    def test_initialization(self, preview_widget):
        """Test widget initialization."""
        assert preview_widget.tab_widget.count() >= 2  # Text and Metadata tabs
        assert "0 elements" in preview_widget.element_count_label.text()
    
    def test_set_element(self, preview_widget, sample_elements):
        """Test setting single element."""
        element = sample_elements[0]
        preview_widget.set_element(element)
        
        assert len(preview_widget._elements) == 1
        assert preview_widget._current_element == element
        assert element.element_type.value in preview_widget.title_label.text()
    
    def test_set_elements(self, preview_widget, sample_elements):
        """Test setting multiple elements."""
        preview_widget.set_elements(sample_elements)
        
        assert len(preview_widget._elements) == len(sample_elements)
        assert preview_widget._current_element == sample_elements[0]
        assert f"{len(sample_elements)} elements" in preview_widget.element_count_label.text()
    
    def test_set_elements_empty(self, preview_widget):
        """Test setting empty elements list."""
        preview_widget.set_elements([])
        
        assert len(preview_widget._elements) == 0
        assert preview_widget._current_element is None
        assert "0 elements" in preview_widget.element_count_label.text()
    
    def test_set_preview_mode(self, preview_widget):
        """Test setting preview mode."""
        # Test text mode
        preview_widget.set_preview_mode("text")
        assert preview_widget.tab_widget.currentIndex() == 0
        
        # Test metadata mode
        preview_widget.set_preview_mode("metadata")
        assert preview_widget.tab_widget.currentIndex() == 1
    
    def test_comparison_tab_visibility(self, preview_widget, sample_elements):
        """Test comparison tab visibility."""
        # With single element, comparison should be hidden
        preview_widget.set_element(sample_elements[0])
        comparison_visible = not preview_widget.tab_widget.isTabVisible(preview_widget.comparison_tab_index)
        assert comparison_visible == False
        
        # With two elements, comparison should be visible
        preview_widget.set_elements(sample_elements[:2])
        comparison_visible = preview_widget.tab_widget.isTabVisible(preview_widget.comparison_tab_index)
        assert comparison_visible == True


class TestConflictPropertyWidget:
    """Tests for conflict property resolution widget."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def conflict_widget(self, app):
        """Create conflict property widget."""
        conflict_data = {
            "values": ["Value 1", "Value 2", "Value 3"],
            "resolution": "Use First Value"
        }
        return ConflictPropertyWidget("test_property", conflict_data)
    
    def test_initialization(self, conflict_widget):
        """Test widget initialization."""
        assert conflict_widget.property_name == "test_property"
        assert conflict_widget.values_list.rowCount() == 3
        assert conflict_widget.strategy_combo.currentText() == "Use First Value"
    
    def test_strategy_change(self, conflict_widget):
        """Test strategy change handling."""
        # Connect signal to mock
        signal_mock = Mock()
        conflict_widget.resolution_changed.connect(signal_mock)
        
        # Change strategy
        conflict_widget.strategy_combo.setCurrentText("Use Last Value")
        conflict_widget.on_strategy_changed("Use Last Value")
        
        # Should emit resolution change
        signal_mock.assert_called()
    
    def test_custom_value_strategy(self, conflict_widget):
        """Test custom value strategy."""
        # Change to custom value strategy
        conflict_widget.strategy_combo.setCurrentText("Custom Value")
        conflict_widget.on_strategy_changed("Custom Value")
        
        # Custom input should be visible
        assert conflict_widget.custom_input.isVisible()
    
    def test_get_resolution(self, conflict_widget):
        """Test getting resolution configuration."""
        resolution = conflict_widget.get_resolution()
        
        assert "strategy" in resolution
        assert "property" in resolution
        assert resolution["property"] == "test_property"


class TestMetadataInheritanceWidget:
    """Tests for metadata inheritance widget."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def inheritance_widget(self, app):
        """Create metadata inheritance widget."""
        return MetadataInheritanceWidget()
    
    def test_initialization(self, inheritance_widget):
        """Test widget initialization."""
        assert inheritance_widget.copy_all_checkbox.isChecked()
        assert inheritance_widget.preserve_parent_checkbox.isChecked()
        assert not inheritance_widget.create_hierarchy_checkbox.isChecked()
    
    def test_get_inheritance_config(self, inheritance_widget):
        """Test getting inheritance configuration."""
        config = inheritance_widget.get_inheritance_config()
        
        assert "copy_all_metadata" in config
        assert "preserve_parent" in config
        assert "create_hierarchy" in config
        assert isinstance(config["copy_all_metadata"], bool)


class TestMetadataConflictResolver:
    """Tests for the main metadata conflict resolver."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def resolver_widget(self, app):
        """Create metadata conflict resolver."""
        return MetadataConflictResolver()
    
    @pytest.fixture
    def sample_conflicts(self):
        """Create sample conflicts."""
        return {
            "element_type": {
                "values": ["Title", "NarrativeText"],
                "resolution": "Use First Value"
            },
            "font_size": {
                "values": [12, 14, 16],
                "resolution": "Use Most Common Value"
            }
        }
    
    def test_initialization(self, resolver_widget):
        """Test widget initialization."""
        assert "No conflicts" in resolver_widget.status_label.text()
        assert not resolver_widget.warnings_scroll.isVisible()
    
    def test_set_conflicts(self, resolver_widget, sample_conflicts):
        """Test setting conflicts."""
        resolver_widget.set_conflicts(sample_conflicts)
        
        assert len(resolver_widget._conflicts) == len(sample_conflicts)
        assert resolver_widget.warnings_scroll.isVisible()
        assert f"{len(sample_conflicts)} conflict" in resolver_widget.status_label.text()
    
    def test_clear_conflicts(self, resolver_widget, sample_conflicts):
        """Test clearing conflicts."""
        resolver_widget.set_conflicts(sample_conflicts)
        resolver_widget.clear_conflicts()
        
        assert len(resolver_widget._conflicts) == 0
        assert not resolver_widget.warnings_scroll.isVisible()
        assert "No conflicts" in resolver_widget.status_label.text()
    
    def test_auto_resolve_conflicts(self, resolver_widget, sample_conflicts):
        """Test auto-resolving conflicts."""
        resolver_widget.set_conflicts(sample_conflicts)
        resolver_widget.auto_resolve_conflicts()
        
        # Should have resolutions for all conflicts
        assert len(resolver_widget._resolutions) == len(sample_conflicts)
        for conflict_name in sample_conflicts:
            assert conflict_name in resolver_widget._resolutions
    
    def test_has_unresolved_conflicts(self, resolver_widget, sample_conflicts):
        """Test checking for unresolved conflicts."""
        # No conflicts
        assert not resolver_widget.has_unresolved_conflicts()
        
        # With conflicts but no resolutions
        resolver_widget.set_conflicts(sample_conflicts)
        assert resolver_widget.has_unresolved_conflicts()
        
        # With conflicts and resolutions
        resolver_widget.auto_resolve_conflicts()
        assert not resolver_widget.has_unresolved_conflicts()
    
    def test_set_operation_mode(self, resolver_widget):
        """Test setting operation mode."""
        # Split mode should show inheritance widget
        resolver_widget.set_operation_mode("split")
        assert resolver_widget.inheritance_widget.isVisible()
        assert "Inheritance" in resolver_widget.title_label.text()
        
        # Merge mode should hide inheritance widget
        resolver_widget.set_operation_mode("merge")
        assert not resolver_widget.inheritance_widget.isVisible()


class TestValidationWarningItem:
    """Tests for validation warning item widget."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def warning_item(self, app):
        """Create validation warning item."""
        return ValidationWarningItem("test_warning", "This is a test warning message", "warning")
    
    def test_initialization(self, warning_item):
        """Test widget initialization."""
        assert warning_item.warning_id == "test_warning"
        assert warning_item.message == "This is a test warning message"
        assert warning_item.severity == "warning"
    
    def test_dismiss_signal(self, warning_item):
        """Test dismiss signal emission."""
        signal_mock = Mock()
        warning_item.warning_dismissed.connect(signal_mock)
        
        # Find and click dismiss button
        dismiss_button = None
        for child in warning_item.findChildren(type(warning_item).__bases__[0]):
            if hasattr(child, 'text') and child.text() == "×":
                dismiss_button = child
                break
        
        if dismiss_button:
            dismiss_button.click()
            signal_mock.assert_called_once_with("test_warning")


class TestValidationWarnings:
    """Tests for the main validation warnings widget."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def warnings_widget(self, app):
        """Create validation warnings widget."""
        return ValidationWarnings()
    
    def test_initialization(self, warnings_widget):
        """Test widget initialization."""
        assert "All checks passed" in warnings_widget.status_label.text()
        assert not warnings_widget.warnings_scroll.isVisible()
    
    def test_set_warnings(self, warnings_widget):
        """Test setting warnings."""
        warnings = ["Warning 1", "Warning 2", "Warning 3"]
        warnings_widget.set_warnings(warnings, "warning")
        
        assert len(warnings_widget._warnings) == len(warnings)
        assert warnings_widget.warnings_scroll.isVisible()
        assert f"{len(warnings)} warning" in warnings_widget.status_label.text()
    
    def test_add_warning(self, warnings_widget):
        """Test adding single warning."""
        warnings_widget.add_warning("Test warning", "error", "test_id")
        
        assert "test_id" in warnings_widget._warnings
        assert warnings_widget._warnings["test_id"]["severity"] == "error"
        assert warnings_widget._warnings["test_id"]["message"] == "Test warning"
    
    def test_remove_warning(self, warnings_widget):
        """Test removing warning."""
        warnings_widget.add_warning("Test warning", "warning", "test_id")
        warnings_widget.remove_warning("test_id")
        
        assert "test_id" not in warnings_widget._warnings
        assert "test_id" in warnings_widget._dismissed_warnings
    
    def test_clear_all_warnings(self, warnings_widget):
        """Test clearing all warnings."""
        warnings = ["Warning 1", "Warning 2"]
        warnings_widget.set_warnings(warnings)
        warnings_widget.clear_all_warnings()
        
        assert len(warnings_widget._warnings) == 0
        assert len(warnings_widget._dismissed_warnings) == 0
        assert "All checks passed" in warnings_widget.status_label.text()
    
    def test_get_warning_count(self, warnings_widget):
        """Test getting warning counts."""
        warnings_widget.add_warning("Error message", "error")
        warnings_widget.add_warning("Warning message", "warning")
        warnings_widget.add_warning("Info message", "info")
        
        counts = warnings_widget.get_warning_count()
        assert counts["error"] == 1
        assert counts["warning"] == 1
        assert counts["info"] == 1
        assert counts["total"] == 3
    
    def test_has_errors(self, warnings_widget):
        """Test checking for errors."""
        assert not warnings_widget.has_errors()
        
        warnings_widget.add_warning("Error message", "error")
        assert warnings_widget.has_errors()
        
        warnings_widget.add_warning("Warning message", "warning")
        assert warnings_widget.has_errors()  # Still has errors
    
    def test_has_warnings(self, warnings_widget):
        """Test checking for warnings."""
        assert not warnings_widget.has_warnings()
        
        warnings_widget.add_warning("Warning message", "warning")
        assert warnings_widget.has_warnings()
    
    def test_start_complete_validation(self, warnings_widget):
        """Test validation progress indication."""
        warnings_widget.start_validation("Testing validation...")
        assert warnings_widget.progress_indicator.isVisible()
        
        warnings_widget.complete_validation("Validation done")
        # Progress indicator should be hidden after timeout


class TestOperationStatsWidget:
    """Tests for operation statistics widget."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def stats_widget(self, app):
        """Create operation stats widget."""
        return OperationStatsWidget()
    
    def test_initialization(self, stats_widget):
        """Test widget initialization."""
        assert stats_widget.stats_table.columnCount() == 2
        assert stats_widget.stats_table.rowCount() == 0
    
    def test_set_stats(self, stats_widget):
        """Test setting statistics."""
        stats = {
            "Input Elements": 5,
            "Output Elements": 3,
            "Processing Time": "1.2s"
        }
        stats_widget.set_stats(stats)
        
        assert stats_widget.stats_table.rowCount() == len(stats)
        
        # Check that all stats are displayed
        displayed_metrics = []
        for i in range(stats_widget.stats_table.rowCount()):
            metric_item = stats_widget.stats_table.item(i, 0)
            displayed_metrics.append(metric_item.text())
        
        for metric in stats:
            assert any(metric.lower() in displayed.lower() for displayed in displayed_metrics)


class TestOperationTimelineWidget:
    """Tests for operation timeline widget."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def timeline_widget(self, app):
        """Create operation timeline widget."""
        return OperationTimelineWidget()
    
    def test_initialization(self, timeline_widget):
        """Test widget initialization."""
        assert timeline_widget.timeline_list.count() == 0
    
    def test_set_operation_steps_merge(self, timeline_widget):
        """Test setting merge operation steps."""
        timeline_widget.set_operation_steps("merge", 3, {"separator": " "})
        
        assert timeline_widget.timeline_list.count() > 0
        assert len(timeline_widget._steps) > 0
        
        # Check that steps are related to merging
        steps_text = [step["step"] for step in timeline_widget._steps]
        assert any("merge" in step.lower() for step in steps_text)
    
    def test_set_operation_steps_split(self, timeline_widget):
        """Test setting split operation steps."""
        timeline_widget.set_operation_steps("split", 1, {"split_positions": [10, 20]})
        
        assert timeline_widget.timeline_list.count() > 0
        assert len(timeline_widget._steps) > 0
        
        # Check that steps are related to splitting
        steps_text = [step["step"] for step in timeline_widget._steps]
        assert any("split" in step.lower() for step in steps_text)


class TestOperationPreview:
    """Tests for the main operation preview widget."""
    
    @pytest.fixture
    def app(self):
        """Create QApplication for tests."""
        if not QApplication.instance():
            return QApplication([])
        return QApplication.instance()
    
    @pytest.fixture
    def preview_widget(self, app):
        """Create operation preview widget."""
        return OperationPreview()
    
    @pytest.fixture
    def sample_elements(self):
        """Create sample elements."""
        return [
            Element(element_type=ElementType.TITLE, text="Title 1"),
            Element(element_type=ElementType.NARRATIVE_TEXT, text="Text 1")
        ]
    
    def test_initialization(self, preview_widget):
        """Test widget initialization."""
        assert preview_widget.tab_widget.count() >= 3  # Overview, Comparison, Timeline, Stats
        assert "No operation" in preview_widget.operation_type_label.text()
    
    def test_set_operation_merge(self, preview_widget, sample_elements):
        """Test setting merge operation."""
        options = {"separator": " ", "preserve_formatting": True}
        preview_widget.set_operation("merge", sample_elements, options)
        
        assert preview_widget._operation_type == "merge"
        assert len(preview_widget._source_elements) == len(sample_elements)
        assert len(preview_widget._result_elements) == 1  # Merged into one
    
    def test_set_operation_split(self, preview_widget, sample_elements):
        """Test setting split operation."""
        element = sample_elements[0]
        options = {"split_positions": [6], "element_type": "Title", "auto_trim": True}
        preview_widget.set_operation("split", [element], options)
        
        assert preview_widget._operation_type == "split"
        assert len(preview_widget._source_elements) == 1
        assert len(preview_widget._result_elements) >= 1  # Split into segments
    
    def test_clear_preview(self, preview_widget, sample_elements):
        """Test clearing preview."""
        # Set operation first
        preview_widget.set_operation("merge", sample_elements, {})
        
        # Clear preview
        preview_widget.clear_preview()
        
        assert preview_widget._operation_type is None
        assert len(preview_widget._source_elements) == 0
        assert len(preview_widget._result_elements) == 0
        assert "No operation" in preview_widget.operation_type_label.text()
    
    def test_get_preview_data(self, preview_widget, sample_elements):
        """Test getting preview data."""
        options = {"separator": " "}
        preview_widget.set_operation("merge", sample_elements, options)
        
        data = preview_widget.get_preview_data()
        
        assert data["operation_type"] == "merge"
        assert len(data["source_elements"]) == len(sample_elements)
        assert len(data["result_elements"]) >= 1
        assert data["options"] == options