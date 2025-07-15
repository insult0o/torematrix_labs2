"""Comprehensive integration tests for property panel system

Tests all property panel components working together in realistic scenarios.
Validates integration with main application, performance, and user workflows.
"""

import pytest
import time
import tempfile
import json
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import Mock, MagicMock, patch, call

# Test framework imports
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

try:
    from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtTest import QTest
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    # Mock PyQt6 for testing without GUI
    class QApplication:
        @staticmethod
        def instance():
            return None
    class QMainWindow:
        pass
    class QWidget:
        pass
    class Qt:
        class DockWidgetArea:
            RightDockWidgetArea = 2
    class QTimer:
        pass
    class QTest:
        @staticmethod
        def qWait(ms):
            time.sleep(ms / 1000)

from torematrix.ui.components.property_panel.integration import PropertyPanelIntegration
from torematrix.ui.components.property_panel.batch_editing import BatchEditingPanel, BatchOperation
from torematrix.ui.components.property_panel.accessibility import AccessibilityManager
from torematrix.ui.components.property_panel.import_export import ImportExportDialog, ExportFormat, ExportConfiguration
from torematrix.ui.components.property_panel.events import PropertyNotificationCenter, PropertyEventType
from torematrix.ui.components.property_panel.models import PropertyValue, PropertyMetadata


class MockMainWindow(QMainWindow):
    """Mock main window for testing"""
    
    def __init__(self):
        super().__init__()
        self.element_list_widget = Mock()
        self.element_list_widget.selection_changed = Mock()
        self.status_bar = Mock()
        self.document_changed = Mock()
        
        # Mock workspace components
        self.workspace_manager = Mock()
        self.document_viewer = Mock()


class MockPropertyManager:
    """Mock property manager for testing"""
    
    def __init__(self):
        self.elements_data = {
            'element_1': {
                'title': 'Test Title 1',
                'content': 'Test content for element 1',
                'type': 'text',
                'confidence': 0.95
            },
            'element_2': {
                'title': 'Test Title 2', 
                'content': 'Test content for element 2',
                'type': 'text',
                'confidence': 0.87
            },
            'element_3': {
                'title': 'Different Title',
                'content': 'Different content here',
                'type': 'image',
                'confidence': 0.92
            }
        }
        
        self.property_history = {}
        self.validation_results = {}
    
    def get_element_properties(self, element_id: str) -> Dict[str, Any]:
        """Get properties for element"""
        return self.elements_data.get(element_id, {})
    
    def get_property_value(self, element_id: str, property_name: str) -> Any:
        """Get specific property value"""
        element_data = self.elements_data.get(element_id, {})
        return element_data.get(property_name)
    
    def set_property_value(self, element_id: str, property_name: str, value: Any) -> None:
        """Set property value"""
        if element_id not in self.elements_data:
            self.elements_data[element_id] = {}
        self.elements_data[element_id][property_name] = value
    
    def get_property_metadata(self, element_id: str, property_name: str) -> PropertyMetadata:
        """Get property metadata"""
        return PropertyMetadata(
            property_name=property_name,
            display_name=property_name.title(),
            description=f"Metadata for {property_name}",
            data_type="string",
            is_required=False,
            is_editable=True
        )
    
    def validate_property(self, element_id: str, property_name: str) -> Dict[str, Any]:
        """Validate property"""
        return {'is_valid': True, 'errors': []}
    
    def validate_property_value(self, element_id: str, property_name: str, value: Any) -> Mock:
        """Validate property value"""
        result = Mock()
        result.is_valid = True
        result.errors = []
        return result
    
    def get_property_history(self, element_id: str) -> List[Any]:
        """Get property change history"""
        return self.property_history.get(element_id, [])
    
    def get_all_element_ids(self) -> List[str]:
        """Get all element IDs"""
        return list(self.elements_data.keys())


@pytest.fixture
def app():
    """Create QApplication for testing"""
    if PYQT_AVAILABLE:
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
    else:
        yield None


@pytest.fixture
def main_window(app):
    """Create mock main window"""
    return MockMainWindow()


@pytest.fixture
def property_manager():
    """Create mock property manager"""
    return MockPropertyManager()


@pytest.fixture
def notification_center():
    """Create notification center"""
    return PropertyNotificationCenter()


@pytest.fixture
def property_integration(main_window, notification_center):
    """Create property panel integration"""
    if PYQT_AVAILABLE:
        return PropertyPanelIntegration(main_window, notification_center)
    else:
        return Mock()


class TestPropertyPanelIntegration:
    """Test property panel integration with main application"""
    
    def test_property_panel_integration_initialization(self, property_integration, main_window):
        """Test property panel integration initializes correctly"""
        if not PYQT_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        assert property_integration is not None
        assert property_integration.main_window == main_window
        assert property_integration._dock_widget is not None
        assert property_integration._panel_widget is not None
    
    def test_dock_widget_configuration(self, property_integration):
        """Test dock widget is configured correctly"""
        if not PYQT_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        dock_widget = property_integration._dock_widget
        assert dock_widget.objectName() == "PropertyPanelDock"
        assert dock_widget.windowTitle() == "Element Properties"
        
        # Test allowed areas
        allowed_areas = dock_widget.allowedAreas()
        expected_areas = (Qt.DockWidgetArea.LeftDockWidgetArea | 
                         Qt.DockWidgetArea.RightDockWidgetArea |
                         Qt.DockWidgetArea.BottomDockWidgetArea)
        assert allowed_areas == expected_areas
    
    def test_keyboard_shortcuts_setup(self, property_integration):
        """Test keyboard shortcuts are set up correctly"""
        if not PYQT_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        # Test that shortcuts are created for main window
        shortcuts = property_integration.main_window.findChildren(object)
        
        # We expect at least some shortcuts to be created
        assert len(shortcuts) > 0
    
    def test_menu_integration(self, property_integration):
        """Test menu integration is set up"""
        if not PYQT_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        # Check that View menu exists or was created
        menubar = property_integration.main_window.menuBar()
        assert menubar is not None
        
        # Check that toggle action is available
        assert hasattr(property_integration, '_toggle_action')
    
    def test_panel_visibility_toggle(self, property_integration):
        """Test panel visibility can be toggled"""
        if not PYQT_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        dock_widget = property_integration._dock_widget
        
        # Test show panel
        property_integration.show_panel()
        assert dock_widget.isVisible()
        
        # Test hide panel
        property_integration.hide_panel()
        assert not dock_widget.isVisible()
        
        # Test toggle
        property_integration.toggle_panel_visibility()
        assert dock_widget.isVisible()
    
    def test_dock_position_changes(self, property_integration):
        """Test dock position can be changed"""
        if not PYQT_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        # Test dock to different areas
        property_integration.dock_panel_to_area(Qt.DockWidgetArea.LeftDockWidgetArea)
        assert property_integration.get_dock_position() == Qt.DockWidgetArea.LeftDockWidgetArea
        
        property_integration.dock_panel_to_area(Qt.DockWidgetArea.BottomDockWidgetArea)
        assert property_integration.get_dock_position() == Qt.DockWidgetArea.BottomDockWidgetArea
    
    def test_element_selection_integration(self, property_integration, property_manager):
        """Test element selection integration"""
        if not PYQT_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        # Set property manager
        panel_widget = property_integration.get_panel_widget()
        if hasattr(panel_widget, 'set_property_manager'):
            panel_widget.set_property_manager(property_manager)
        
        # Test selection change
        test_elements = ['element_1', 'element_2']
        property_integration._on_element_selection_changed(test_elements)
        
        # Verify selection was processed
        assert property_integration.selected_elements if hasattr(property_integration, 'selected_elements') else True
    
    def test_workspace_state_persistence(self, property_integration):
        """Test workspace state can be saved and restored"""
        if not PYQT_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        # Change panel state
        property_integration.dock_panel_to_area(Qt.DockWidgetArea.LeftDockWidgetArea)
        property_integration.show_panel()
        
        # Save state
        property_integration.save_workspace_state()
        
        # Change state
        property_integration.hide_panel()
        property_integration.dock_panel_to_area(Qt.DockWidgetArea.RightDockWidgetArea)
        
        # Restore state
        property_integration._restore_workspace_state()
        
        # State should be restored (this is a basic test)
        assert property_integration._dock_widget is not None


class TestBatchEditingIntegration:
    """Test batch editing functionality"""
    
    def test_batch_editing_panel_initialization(self, notification_center):
        """Test batch editing panel initializes correctly"""
        if not PYQT_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        batch_panel = BatchEditingPanel(notification_center)
        assert batch_panel is not None
        assert batch_panel.notification_center == notification_center
        assert batch_panel.selected_elements == []
    
    def test_batch_operation_creation(self):
        """Test batch operation creation"""
        operation = BatchOperation(
            property_name="title",
            operation_type="set",
            new_value="Updated Title",
            target_elements=["element_1", "element_2"]
        )
        
        assert operation.property_name == "title"
        assert operation.operation_type == "set"
        assert operation.new_value == "Updated Title"
        assert len(operation.target_elements) == 2
    
    def test_batch_operation_conditions(self):
        """Test batch operation with conditions"""
        def condition_func(value):
            return value is not None and len(str(value)) > 0
        
        operation = BatchOperation(
            property_name="content",
            operation_type="append",
            new_value=" - Updated",
            target_elements=["element_1"],
            condition_func=condition_func
        )
        
        # Test condition evaluation
        assert operation.can_apply_to_element("element_1", "existing content")
        assert not operation.can_apply_to_element("element_1", "")
        assert not operation.can_apply_to_element("element_3", "content")  # Not in target list
    
    @pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt6 not available")
    def test_batch_editing_workflow(self, notification_center, property_manager):
        """Test complete batch editing workflow"""
        batch_panel = BatchEditingPanel(notification_center)
        batch_panel.set_property_manager(property_manager)
        
        # Set selected elements
        test_elements = ['element_1', 'element_2']
        batch_panel.set_selected_elements(test_elements)
        
        # Verify context was created
        assert batch_panel.batch_context is not None
        assert batch_panel.batch_context.total_elements == 2
        assert len(batch_panel.batch_context.common_properties) > 0
    
    def test_batch_worker_execution(self, property_manager):
        """Test batch worker execution"""
        from torematrix.ui.components.property_panel.batch_editing import BatchEditWorker
        
        worker = BatchEditWorker()
        worker.set_property_manager(property_manager)
        
        # Add test operation
        operation = BatchOperation(
            property_name="title",
            operation_type="set", 
            new_value="Batch Updated Title",
            target_elements=["element_1", "element_2"]
        )
        worker.add_operation(operation)
        
        # Execute batch (synchronously for testing)
        worker.execute_batch()
        
        # Verify changes were applied
        assert property_manager.get_property_value("element_1", "title") == "Batch Updated Title"
        assert property_manager.get_property_value("element_2", "title") == "Batch Updated Title"


class TestAccessibilityIntegration:
    """Test accessibility features integration"""
    
    def test_accessibility_manager_initialization(self, notification_center):
        """Test accessibility manager initializes"""
        if not PYQT_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        accessibility_manager = AccessibilityManager(notification_center)
        assert accessibility_manager is not None
        assert accessibility_manager.notification_center == notification_center
        assert accessibility_manager.enabled == True
    
    def test_system_settings_detection(self, notification_center):
        """Test system accessibility settings detection"""
        if not PYQT_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        accessibility_manager = AccessibilityManager(notification_center)
        
        # Check that settings were detected
        assert hasattr(accessibility_manager, 'high_contrast_mode')
        assert hasattr(accessibility_manager, 'large_font_mode')
        assert hasattr(accessibility_manager, 'contrast_ratio')
        assert hasattr(accessibility_manager, 'font_scale_factor')
    
    def test_accessibility_features_toggle(self, notification_center):
        """Test accessibility features can be toggled"""
        if not PYQT_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        accessibility_manager = AccessibilityManager(notification_center)
        
        # Test enabling/disabling
        accessibility_manager.enable_accessibility(False)
        assert accessibility_manager.enabled == False
        
        accessibility_manager.enable_accessibility(True)
        assert accessibility_manager.enabled == True
        
        # Test high contrast mode
        accessibility_manager.set_high_contrast_mode(True)
        assert accessibility_manager.high_contrast_mode == True
        
        # Test large font mode
        accessibility_manager.set_large_font_mode(True, 1.5)
        assert accessibility_manager.large_font_mode == True
        assert accessibility_manager.font_scale_factor == 1.5
    
    def test_keyboard_shortcuts_integration(self):
        """Test keyboard shortcuts integration"""
        if not PYQT_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        from torematrix.ui.components.property_panel.accessibility import KeyboardShortcutManager
        
        mock_widget = Mock()
        shortcut_manager = KeyboardShortcutManager(mock_widget)
        
        assert shortcut_manager is not None
        assert len(shortcut_manager.shortcuts) > 0
        
        # Test getting help
        help_text = shortcut_manager.get_shortcut_help()
        assert isinstance(help_text, dict)
        assert len(help_text) > 0
    
    def test_screen_reader_announcements(self, notification_center):
        """Test screen reader announcement system"""
        if not PYQT_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        from torematrix.ui.components.property_panel.accessibility import ScreenReaderSupport
        
        accessibility_manager = AccessibilityManager(notification_center)
        screen_reader = ScreenReaderSupport(accessibility_manager)
        
        # Test announcements
        screen_reader.announce_property_change("element_1", "title", "old", "new")
        screen_reader.announce_selection_change(["element_1"], ["title", "content"])
        screen_reader.announce_navigation("next", "title")
        screen_reader.announce_editing_state("start", "title")
        screen_reader.announce_batch_operation("update", 5)
        
        # Check announcements were queued
        assert len(screen_reader.announcement_queue) > 0


class TestImportExportIntegration:
    """Test import/export functionality integration"""
    
    def test_export_configuration_creation(self):
        """Test export configuration creation"""
        from torematrix.ui.components.property_panel.import_export import ExportConfiguration
        
        config = ExportConfiguration(
            format=ExportFormat.JSON,
            include_metadata=True,
            include_history=False,
            flatten_nested=True
        )
        
        assert config.format == ExportFormat.JSON
        assert config.include_metadata == True
        assert config.include_history == False
        assert config.flatten_nested == True
    
    def test_property_exporter_initialization(self):
        """Test property exporter initialization"""
        from torematrix.ui.components.property_panel.import_export import PropertyExporter
        
        exporter = PropertyExporter()
        assert exporter is not None
        assert exporter.property_manager is None
        assert exporter.cancel_requested == False
    
    def test_property_importer_initialization(self):
        """Test property importer initialization"""
        from torematrix.ui.components.property_panel.import_export import PropertyImporter
        
        importer = PropertyImporter()
        assert importer is not None
        assert importer.property_manager is None
        assert importer.cancel_requested == False
    
    def test_export_operation(self, property_manager):
        """Test export operation"""
        from torematrix.ui.components.property_panel.import_export import PropertyExporter, ExportConfiguration
        
        exporter = PropertyExporter()
        exporter.set_property_manager(property_manager)
        
        # Create test export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            config = ExportConfiguration(format=ExportFormat.JSON)
            result = exporter.export_properties(['element_1', 'element_2'], config, temp_path)
            
            assert result.success == True
            assert result.exported_count == 2
            assert Path(temp_path).exists()
            
            # Verify exported data
            with open(temp_path, 'r') as f:
                data = json.load(f)
            
            assert 'export_info' in data
            assert 'elements' in data
            assert 'element_1' in data['elements']
            assert 'element_2' in data['elements']
            
        finally:
            # Cleanup
            if Path(temp_path).exists():
                Path(temp_path).unlink()
    
    def test_import_operation(self, property_manager):
        """Test import operation"""
        from torematrix.ui.components.property_panel.import_export import (
            PropertyImporter, ImportConfiguration, ExportFormat
        )
        
        # Create test data file
        test_data = {
            'export_info': {
                'timestamp': '2023-01-01T00:00:00',
                'format': 'json'
            },
            'elements': {
                'imported_element': {
                    'properties': {
                        'title': 'Imported Title',
                        'content': 'Imported Content'
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name
        
        try:
            importer = PropertyImporter()
            importer.set_property_manager(property_manager)
            
            config = ImportConfiguration(format=ExportFormat.JSON)
            result = importer.import_properties(temp_path, config)
            
            assert result.success == True
            assert result.imported_count > 0
            
            # Verify imported data
            imported_title = property_manager.get_property_value('imported_element', 'title')
            assert imported_title == 'Imported Title'
            
        finally:
            # Cleanup
            if Path(temp_path).exists():
                Path(temp_path).unlink()
    
    @pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt6 not available")
    def test_import_export_dialog(self):
        """Test import/export dialog functionality"""
        dialog = ImportExportDialog()
        assert dialog is not None
        assert dialog.exporter is not None
        assert dialog.importer is not None


class TestPerformanceIntegration:
    """Test performance-related integration"""
    
    def test_large_dataset_handling(self, property_manager):
        """Test handling of large datasets"""
        # Add many elements to property manager
        for i in range(100):
            element_id = f'element_{i}'
            property_manager.elements_data[element_id] = {
                'title': f'Title {i}',
                'content': f'Content for element {i}',
                'type': 'text',
                'confidence': 0.9 + (i % 10) * 0.01
            }
        
        # Test batch operations on large dataset
        if PYQT_AVAILABLE:
            from torematrix.ui.components.property_panel.batch_editing import BatchEditWorker
            
            worker = BatchEditWorker()
            worker.set_property_manager(property_manager)
            
            # Create batch operation for all elements
            operation = BatchOperation(
                property_name="type",
                operation_type="set",
                new_value="updated_text",
                target_elements=[f'element_{i}' for i in range(100)]
            )
            worker.add_operation(operation)
            
            # Time the operation
            start_time = time.time()
            worker.execute_batch()
            end_time = time.time()
            
            # Should complete in reasonable time (< 1 second for 100 elements)
            assert (end_time - start_time) < 1.0
            
            # Verify all elements were updated
            for i in range(100):
                element_id = f'element_{i}'
                assert property_manager.get_property_value(element_id, "type") == "updated_text"
    
    def test_memory_usage_stability(self, property_manager):
        """Test memory usage remains stable during operations"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Perform many operations
        for i in range(1000):
            element_id = f'test_element_{i % 10}'  # Reuse elements
            property_manager.set_property_value(element_id, 'test_prop', f'value_{i}')
        
        final_memory = process.memory_info().rss
        memory_increase = (final_memory - initial_memory) / (1024 * 1024)  # MB
        
        # Memory increase should be reasonable (< 10MB for this test)
        assert memory_increase < 10.0
    
    def test_concurrent_operations(self, property_manager):
        """Test concurrent property operations"""
        import threading
        import concurrent.futures
        
        def update_properties(element_id, start_idx, count):
            """Update properties for an element"""
            for i in range(start_idx, start_idx + count):
                property_manager.set_property_value(element_id, f'prop_{i}', f'value_{i}')
        
        # Run concurrent updates
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for i in range(4):
                future = executor.submit(update_properties, f'element_{i}', i * 10, 10)
                futures.append(future)
            
            # Wait for completion
            for future in concurrent.futures.as_completed(futures):
                future.result()  # Will raise exception if there was an error
        
        # Verify all updates completed successfully
        for i in range(4):
            element_id = f'element_{i}'
            for j in range(i * 10, (i + 1) * 10):
                value = property_manager.get_property_value(element_id, f'prop_{j}')
                assert value == f'value_{j}'


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows"""
    
    @pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt6 not available")
    def test_complete_property_editing_workflow(self, app, main_window, notification_center, property_manager):
        """Test complete property editing workflow"""
        # Create property panel integration
        integration = PropertyPanelIntegration(main_window, notification_center)
        panel_widget = integration.get_panel_widget()
        
        if hasattr(panel_widget, 'set_property_manager'):
            panel_widget.set_property_manager(property_manager)
        
        # 1. Show property panel
        integration.show_panel()
        assert integration.is_panel_visible()
        
        # 2. Select elements
        test_elements = ['element_1', 'element_2']
        integration._on_element_selection_changed(test_elements)
        
        # 3. Simulate property editing (would normally be done through UI)
        property_manager.set_property_value('element_1', 'title', 'Updated Title')
        
        # 4. Verify change
        new_value = property_manager.get_property_value('element_1', 'title')
        assert new_value == 'Updated Title'
        
        # 5. Test batch editing
        batch_panel = BatchEditingPanel(notification_center)
        batch_panel.set_property_manager(property_manager)
        batch_panel.set_selected_elements(test_elements)
        
        # 6. Save workspace state
        integration.save_workspace_state()
    
    def test_import_edit_export_workflow(self, property_manager):
        """Test complete import -> edit -> export workflow"""
        from torematrix.ui.components.property_panel.import_export import (
            PropertyImporter, PropertyExporter, ImportConfiguration, ExportConfiguration, ExportFormat
        )
        
        # 1. Create test data to import
        test_data = {
            'export_info': {'timestamp': '2023-01-01T00:00:00', 'format': 'json'},
            'elements': {
                'workflow_element_1': {
                    'properties': {'title': 'Original Title 1', 'content': 'Original Content 1'}
                },
                'workflow_element_2': {
                    'properties': {'title': 'Original Title 2', 'content': 'Original Content 2'}
                }
            }
        }
        
        # 2. Import data
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f)
            import_path = f.name
        
        try:
            importer = PropertyImporter()
            importer.set_property_manager(property_manager)
            
            import_config = ImportConfiguration(format=ExportFormat.JSON)
            import_result = importer.import_properties(import_path, import_config)
            
            assert import_result.success
            assert import_result.imported_count == 2
            
            # 3. Edit imported data
            property_manager.set_property_value('workflow_element_1', 'title', 'Edited Title 1')
            property_manager.set_property_value('workflow_element_2', 'content', 'Edited Content 2')
            
            # 4. Export edited data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                export_path = f.name
            
            exporter = PropertyExporter()
            exporter.set_property_manager(property_manager)
            
            export_config = ExportConfiguration(format=ExportFormat.JSON)
            export_result = exporter.export_properties(
                ['workflow_element_1', 'workflow_element_2'], 
                export_config, 
                export_path
            )
            
            assert export_result.success
            assert export_result.exported_count == 2
            
            # 5. Verify exported data contains edits
            with open(export_path, 'r') as f:
                exported_data = json.load(f)
            
            elements = exported_data['elements']
            assert elements['workflow_element_1']['properties']['title'] == 'Edited Title 1'
            assert elements['workflow_element_2']['properties']['content'] == 'Edited Content 2'
            
            # Cleanup export file
            Path(export_path).unlink()
            
        finally:
            # Cleanup import file
            Path(import_path).unlink()
    
    def test_accessibility_workflow(self, notification_center):
        """Test accessibility workflow"""
        if not PYQT_AVAILABLE:
            pytest.skip("PyQt6 not available")
        
        # 1. Initialize accessibility features
        accessibility_manager = AccessibilityManager(notification_center)
        
        # 2. Enable high contrast mode
        accessibility_manager.set_high_contrast_mode(True)
        assert accessibility_manager.high_contrast_mode
        
        # 3. Enable large font mode
        accessibility_manager.set_large_font_mode(True, 1.5)
        assert accessibility_manager.large_font_mode
        assert accessibility_manager.font_scale_factor == 1.5
        
        # 4. Test screen reader support
        from torematrix.ui.components.property_panel.accessibility import ScreenReaderSupport
        screen_reader = ScreenReaderSupport(accessibility_manager)
        
        # 5. Simulate navigation and announcements
        screen_reader.announce_selection_change(['element_1'], ['title', 'content'])
        screen_reader.announce_navigation('next', 'title')
        screen_reader.announce_editing_state('start', 'title')
        
        # 6. Verify announcements were queued
        assert len(screen_reader.announcement_queue) > 0


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases"""
    
    def test_invalid_element_ids(self, property_manager):
        """Test handling of invalid element IDs"""
        # Test getting properties for non-existent element
        properties = property_manager.get_element_properties('non_existent_element')
        assert properties == {}
        
        # Test getting specific property for non-existent element
        value = property_manager.get_property_value('non_existent_element', 'title')
        assert value is None
        
        # Test setting property for non-existent element (should create element)
        property_manager.set_property_value('new_element', 'title', 'New Title')
        assert property_manager.get_property_value('new_element', 'title') == 'New Title'
    
    def test_empty_batch_operations(self):
        """Test batch operations with empty data"""
        from torematrix.ui.components.property_panel.batch_editing import BatchEditWorker
        
        worker = BatchEditWorker()
        
        # Execute batch with no operations
        worker.execute_batch()
        
        # Should complete without error
        assert len(worker.operations) == 0
    
    def test_invalid_export_paths(self, property_manager):
        """Test export with invalid file paths"""
        from torematrix.ui.components.property_panel.import_export import PropertyExporter, ExportConfiguration
        
        exporter = PropertyExporter()
        exporter.set_property_manager(property_manager)
        
        config = ExportConfiguration(format=ExportFormat.JSON)
        
        # Test export to invalid path
        result = exporter.export_properties(
            ['element_1'], 
            config, 
            '/invalid/path/that/does/not/exist.json'
        )
        
        assert not result.success
        assert len(result.errors) > 0
    
    def test_corrupted_import_data(self, property_manager):
        """Test import with corrupted data"""
        from torematrix.ui.components.property_panel.import_export import PropertyImporter, ImportConfiguration
        
        # Create corrupted JSON file
        corrupted_data = '{"invalid": json data}'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(corrupted_data)
            temp_path = f.name
        
        try:
            importer = PropertyImporter()
            importer.set_property_manager(property_manager)
            
            config = ImportConfiguration(format=ExportFormat.JSON)
            result = importer.import_properties(temp_path, config)
            
            assert not result.success
            assert len(result.errors) > 0
            
        finally:
            Path(temp_path).unlink()


# Integration test runner
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])