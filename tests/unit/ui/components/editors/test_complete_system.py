<<<<<<< HEAD
"""Comprehensive test suite for inline editing system

Tests all components of the inline editing system including integration,
accessibility, error handling, and complete system functionality.
=======
"""
Comprehensive test suite for the complete inline editing system

Tests all Agent 4 components working together:
- System initialization and configuration
- Editor lifecycle management  
- Accessibility integration
- Error handling and recovery
- Performance monitoring
- Memory management
- Integration workflows
>>>>>>> origin/main
"""

import pytest
import time
<<<<<<< HEAD
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Dict

# Mock PyQt6 completely for testing
with patch.dict('sys.modules', {
    'PyQt6': MagicMock(),
    'PyQt6.QtWidgets': MagicMock(),
    'PyQt6.QtCore': MagicMock(),
    'PyQt6.QtGui': MagicMock(),
}):
    from src.torematrix.ui.components.editors.base import BaseEditor, EditorConfig, EditorState
    from src.torematrix.ui.components.editors.integration import ElementEditorBridge, EditRequest
    from src.torematrix.ui.components.editors.accessibility import AccessibilityManager, AccessibilitySettings
    from src.torematrix.ui.components.editors.recovery import (
        EditorErrorHandler, ErrorRecord, ErrorSeverity, ErrorCategory, RecoveryStrategy
    )
    from src.torematrix.ui.components.editors.complete_system import (
        InlineEditingSystem, SystemConfiguration, SystemMetrics, create_inline_editing_system
    )
=======
import weakref
from unittest.mock import Mock, patch, MagicMock
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import QTimer
from PyQt6.QtTest import QTest

# Import system components
from torematrix.ui.components.editors.complete_system import (
    InlineEditingSystem, InlineEditingSystemWidget, SystemConfiguration,
    SystemState, SystemMetrics
)
from torematrix.ui.components.editors.base import BaseEditor, EditorState, EditorConfig
from torematrix.ui.components.editors.recovery import ErrorSeverity, RecoveryStrategy
from torematrix.ui.components.editors.accessibility import AccessibilityFeatures
>>>>>>> origin/main


class MockEditor(BaseEditor):
    """Mock editor for testing"""
    
<<<<<<< HEAD
    def __init__(self, parent=None, config=None):
        super().__init__(parent, config)
        self._value = None
        self._validation_result = (True, "")
        
    def set_value(self, value: Any) -> bool:
        self._value = value
        self._set_current_value(value)
        return True
        
    def get_value(self) -> Any:
        return self._value
        
    def start_editing(self, value: Any = None) -> bool:
        if value is not None:
            self.set_value(value)
        self._set_state(EditorState.EDITING)
        self.editing_started.emit()
        return True
        
    def save(self) -> bool:
        if self._state == EditorState.EDITING:
            is_valid, _ = self.validate()
            if is_valid:
                self._set_state(EditorState.INACTIVE)
                self.editing_finished.emit(True)
                return True
        return False
        
    def cancel_editing(self) -> bool:
        if self._state == EditorState.EDITING:
            self._set_state(EditorState.INACTIVE)
            self.editing_finished.emit(False)
            return True
        return False
        
    def validate(self, value: Any = None) -> tuple[bool, str]:
        return self._validation_result
        
    def set_validation_result(self, is_valid: bool, message: str = ""):
        """Helper for testing"""
        self._validation_result = (is_valid, message)


class TestBaseEditor:
    """Test base editor functionality"""
    
    def test_editor_creation(self):
        """Test editor creation with config"""
        config = EditorConfig(auto_commit=True, required=True)
        editor = MockEditor(config=config)
        
        assert editor.config.auto_commit is True
        assert editor.config.required is True
        assert editor.get_state() == EditorState.INACTIVE
        assert not editor.is_editing()
        assert not editor.is_dirty()
        
    def test_editor_lifecycle(self):
        """Test complete editor lifecycle"""
        editor = MockEditor()
        
        # Start editing
        result = editor.start_editing("test value")
        assert result is True
        assert editor.is_editing()
        assert editor.get_value() == "test value"
        
        # Modify value
        editor.set_value("modified value")
        assert editor.is_dirty()
        assert editor.get_value() == "modified value"
        
        # Save
        result = editor.save()
        assert result is True
        assert not editor.is_editing()
        
    def test_editor_cancel(self):
        """Test editor cancellation"""
        editor = MockEditor()
        
        editor.start_editing("initial")
        editor.set_value("modified")
        
        result = editor.cancel_editing()
        assert result is True
        assert not editor.is_editing()
        
    def test_editor_validation(self):
        """Test editor validation"""
        editor = MockEditor()
        
        # Valid case
        editor.set_validation_result(True, "")
        is_valid, message = editor.validate("test")
        assert is_valid is True
        assert message == ""
        
        # Invalid case
        editor.set_validation_result(False, "Invalid input")
        is_valid, message = editor.validate("bad")
        assert is_valid is False
        assert message == "Invalid input"


class TestElementEditorBridge:
    """Test element editor bridge functionality"""
    
    def test_bridge_creation(self):
        """Test bridge creation"""
        bridge = ElementEditorBridge()
        assert bridge.editor_factory is None
        assert len(bridge.active_editors) == 0
        
    def test_set_editor_factory(self):
        """Test setting editor factory"""
        bridge = ElementEditorBridge()
        
        def mock_factory(element_id, element_type, parent, config):
            return MockEditor(parent, config)
            
        bridge.set_editor_factory(mock_factory)
        assert bridge.editor_factory is not None
        
    def test_request_edit(self):
        """Test edit request handling"""
        bridge = ElementEditorBridge()
        
        def mock_factory(element_id, element_type, parent, config):
            return MockEditor(parent, config)
            
        bridge.set_editor_factory(mock_factory)
        
        # Test successful request
        result = bridge.request_edit("elem1", "text", "initial value")
        assert result is True
        assert bridge.is_editing("elem1")
        
        # Test duplicate request
        result = bridge.request_edit("elem1", "text", "other value")
        assert result is False  # Should reject duplicate
        
    def test_cancel_edit(self):
        """Test edit cancellation"""
        bridge = ElementEditorBridge()
        bridge.set_editor_factory(lambda *args: MockEditor())
        
        bridge.request_edit("elem1", "text")
        assert bridge.is_editing("elem1")
        
        result = bridge.cancel_edit("elem1")
        assert result is True
        assert not bridge.is_editing("elem1")
        
    def test_get_edit_statistics(self):
        """Test edit statistics"""
        bridge = ElementEditorBridge()
        bridge.set_editor_factory(lambda *args: MockEditor())
        
        stats = bridge.get_edit_statistics()
        assert stats['total_edits'] == 0
        assert stats['successful_edits'] == 0
        
        # Start an edit
        bridge.request_edit("elem1", "text")
        stats = bridge.get_edit_statistics()
        assert stats['total_edits'] == 1


class TestAccessibilityManager:
    """Test accessibility manager functionality"""
    
    def test_accessibility_settings_creation(self):
        """Test accessibility settings creation"""
        settings = AccessibilitySettings()
        
        # Default values should be set
        assert settings.keyboard_navigation_enabled is True
        assert settings.contrast_ratio >= 4.5
        assert settings.font_scale_factor >= 1.0
        
    def test_accessibility_manager_creation(self):
        """Test accessibility manager creation"""
        manager = AccessibilityManager()
        
        assert manager.settings is not None
        assert len(manager.managed_widgets) == 0
        assert len(manager.shortcuts) == 0
        
    def test_setup_accessibility(self):
        """Test accessibility setup for widget"""
        manager = AccessibilityManager()
        widget = Mock()
        
        config = {
            'accessible_name': 'Test Editor',
            'accessible_description': 'Test description'
        }
        
        manager.setup_accessibility(widget, config)
        assert widget in manager.managed_widgets
        
    def test_announce_functionality(self):
        """Test screen reader announcements"""
        manager = AccessibilityManager()
        
        # Should not crash even if screen reader not available
        manager.announce("Test message")
        manager.announce("Urgent message", "assertive")
        
    def test_accessibility_summary(self):
        """Test accessibility status summary"""
        manager = AccessibilityManager()
        
        summary = manager.get_accessibility_summary()
        assert 'settings' in summary
        assert 'managed_widgets_count' in summary
        assert summary['managed_widgets_count'] == 0
=======
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = ""
        self._dirty = False
        self._editing = False
        
    def get_value(self):
        return self._value
        
    def set_value(self, value):
        old_value = self._value
        self._value = value
        if old_value != value:
            self._dirty = True
            self.value_changed.emit(value)
            
    def start_editing(self, initial_value=None):
        if initial_value is not None:
            self.set_value(initial_value)
        self._editing = True
        self.editing_started.emit()
        
    def finish_editing(self, save=True):
        if save:
            self.save()
        self._editing = False
        self.editing_finished.emit(save)
        
    def cancel_editing(self):
        self._editing = False
        self.editing_finished.emit(False)
        
    def save(self):
        self._dirty = False
        return True
        
    def is_dirty(self):
        return self._dirty
        
    def is_editing(self):
        return self._editing
        
    def validate(self):
        return True, ""


@pytest.fixture
def app():
    """Create QApplication for testing"""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def parent_widget(app):
    """Create parent widget for testing"""
    widget = QWidget()
    widget.setLayout(QVBoxLayout())
    return widget


@pytest.fixture
def default_config():
    """Create default system configuration"""
    return SystemConfiguration(
        enable_accessibility=True,
        enable_error_recovery=True,
        enable_performance_monitoring=True,
        auto_save_interval=1,  # Short interval for testing
        max_concurrent_editors=5
    )


@pytest.fixture
def editing_system(default_config, parent_widget):
    """Create editing system for testing"""
    system = InlineEditingSystem(default_config, parent_widget)
    yield system
    system.shutdown()


class TestSystemConfiguration:
    """Test system configuration validation"""
    
    def test_valid_configuration(self):
        """Test valid configuration creates successfully"""
        config = SystemConfiguration()
        issues = config.validate()
        assert len(issues) == 0
        
    def test_invalid_auto_save_interval(self):
        """Test invalid auto-save interval is caught"""
        config = SystemConfiguration(auto_save_interval=1)  # Too short
        issues = config.validate()
        assert any("Auto-save interval" in issue for issue in issues)
        
    def test_invalid_max_editors(self):
        """Test invalid max editors is caught"""
        config = SystemConfiguration(max_concurrent_editors=0)
        issues = config.validate()
        assert any("Maximum concurrent editors" in issue for issue in issues)
        
    def test_invalid_memory_limit(self):
        """Test invalid memory limit is caught"""
        config = SystemConfiguration(memory_limit_mb=5)
        issues = config.validate()
        assert any("Memory limit" in issue for issue in issues)


class TestSystemInitialization:
    """Test system initialization and state management"""
    
    def test_system_initialization(self, default_config, parent_widget):
        """Test system initializes correctly"""
        system = InlineEditingSystem(default_config, parent_widget)
        
        assert system.state == SystemState.READY
        assert system.config == default_config
        assert system.editor_bridge is not None
        assert system.accessibility_manager is not None
        assert system.recovery_manager is not None
        assert len(system.active_editors) == 0
        
        system.shutdown()
        
    def test_invalid_configuration_fails(self, parent_widget):
        """Test invalid configuration raises error"""
        invalid_config = SystemConfiguration(max_concurrent_editors=0)
        
        with pytest.raises(ValueError, match="Configuration issues"):
            InlineEditingSystem(invalid_config, parent_widget)
            
    def test_system_state_transitions(self, editing_system):
        """Test system state transitions"""
        # Should start in READY state
        assert editing_system.state == SystemState.READY
        
        # Shutdown should change state
        editing_system.shutdown()
        assert editing_system.state == SystemState.SHUTDOWN


class TestEditorLifecycle:
    """Test editor creation, management, and destruction"""
    
    @patch('torematrix.ui.components.editors.complete_system.ElementEditorBridge.create_editor')
    def test_create_editor_success(self, mock_create, editing_system, parent_widget):
        """Test successful editor creation"""
        mock_editor = MockEditor(parent_widget)
        mock_create.return_value = mock_editor
        
        editor = editing_system.create_editor("test_id", "text", parent_widget)
        
        assert editor is not None
        assert editor == mock_editor
        assert "test_id" in editing_system.active_editors
        assert editing_system.metrics.active_editors == 1
        
    def test_create_editor_duplicate(self, editing_system, parent_widget):
        """Test creating duplicate editor returns existing"""
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=MockEditor()):
            editor1 = editing_system.create_editor("test_id", "text", parent_widget)
            editor2 = editing_system.create_editor("test_id", "text", parent_widget)
            
            assert editor1 == editor2
            assert len(editing_system.active_editors) == 1
            
    def test_max_concurrent_editors(self, editing_system, parent_widget):
        """Test maximum concurrent editors limit"""
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=MockEditor()):
            # Create maximum number of editors
            for i in range(editing_system.config.max_concurrent_editors):
                editor = editing_system.create_editor(f"test_{i}", "text", parent_widget)
                assert editor is not None
                
            # Next creation should fail
            editor = editing_system.create_editor("overflow", "text", parent_widget)
            assert editor is None
            
    def test_get_editor(self, editing_system, parent_widget):
        """Test getting existing editor"""
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=MockEditor()):
            created_editor = editing_system.create_editor("test_id", "text", parent_widget)
            retrieved_editor = editing_system.get_editor("test_id")
            
            assert retrieved_editor == created_editor
            assert editing_system.get_editor("nonexistent") is None
            
    def test_destroy_editor(self, editing_system, parent_widget):
        """Test editor destruction"""
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=MockEditor()):
            editor = editing_system.create_editor("test_id", "text", parent_widget)
            assert len(editing_system.active_editors) == 1
            
            success = editing_system.destroy_editor("test_id")
            
            assert success
            assert len(editing_system.active_editors) == 0
            assert editing_system.metrics.active_editors == 0
            
    def test_destroy_nonexistent_editor(self, editing_system):
        """Test destroying nonexistent editor"""
        success = editing_system.destroy_editor("nonexistent")
        assert not success


class TestEditingWorkflow:
    """Test complete editing workflows"""
    
    def test_start_editing(self, editing_system, parent_widget):
        """Test starting editing workflow"""
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=MockEditor()):
            editor = editing_system.create_editor("test_id", "text", parent_widget)
            
            success = editing_system.start_editing("test_id", "initial value")
            
            assert success
            assert editor.is_editing()
            assert editor.get_value() == "initial value"
            assert editing_system.metrics.total_edits == 1
            
    def test_start_editing_nonexistent(self, editing_system):
        """Test starting editing for nonexistent editor"""
        success = editing_system.start_editing("nonexistent")
        assert not success
        
    def test_save_all_editors(self, editing_system, parent_widget):
        """Test saving all editors"""
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=MockEditor()):
            # Create multiple editors
            editor1 = editing_system.create_editor("test_1", "text", parent_widget)
            editor2 = editing_system.create_editor("test_2", "text", parent_widget)
            
            # Make them dirty
            editor1.set_value("value1")
            editor2.set_value("value2")
            
            # Save all
            results = editing_system.save_all_editors()
            
            assert len(results) == 2
            assert all(results.values())  # All should succeed
            assert not editor1.is_dirty()
            assert not editor2.is_dirty()
            assert editing_system.metrics.successful_saves == 2


class TestAccessibilityIntegration:
    """Test accessibility integration"""
    
    def test_accessibility_manager_created(self, editing_system):
        """Test accessibility manager is created when enabled"""
        assert editing_system.accessibility_manager is not None
        
    def test_accessibility_disabled(self, parent_widget):
        """Test system works without accessibility"""
        config = SystemConfiguration(enable_accessibility=False)
        system = InlineEditingSystem(config, parent_widget)
        
        assert system.accessibility_manager is None
        system.shutdown()
        
    def test_editor_accessibility_setup(self, editing_system, parent_widget):
        """Test accessibility is setup for new editors"""
        mock_editor = MockEditor(parent_widget)
        
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=mock_editor):
            with patch.object(editing_system.accessibility_manager, 'setup_accessibility') as mock_setup:
                editor = editing_system.create_editor("test_id", "text", parent_widget)
                
                mock_setup.assert_called_once_with(mock_editor)
>>>>>>> origin/main


class TestErrorHandling:
    """Test error handling and recovery"""
    
<<<<<<< HEAD
    def test_error_record_creation(self):
        """Test error record creation"""
        error = ValueError("Test error")
        handler = EditorErrorHandler()
        
        record = handler.handle_error(error, "test_component")
        
        assert record.error_type == "ValueError"
        assert record.message == "Test error"
        assert record.component == "test_component"
        assert record.category == ErrorCategory.VALIDATION
        assert record.severity == ErrorSeverity.LOW
        
    def test_error_classification(self):
        """Test error classification"""
        handler = EditorErrorHandler()
        
        # Test different error types
        memory_error = MemoryError("Out of memory")
        record = handler.handle_error(memory_error, "test")
        assert record.category == ErrorCategory.RESOURCE
        assert record.severity == ErrorSeverity.CRITICAL
        
        connection_error = ConnectionError("Network error")
        record = handler.handle_error(connection_error, "test")
        assert record.category == ErrorCategory.NETWORK
        assert record.severity == ErrorSeverity.HIGH
        
    def test_error_statistics(self):
        """Test error statistics collection"""
        handler = EditorErrorHandler()
        
        # Initial stats
        stats = handler.get_error_statistics()
        assert stats['total_errors'] == 0
        
        # Add some errors
        handler.handle_error(ValueError("Error 1"), "comp1")
        handler.handle_error(ConnectionError("Error 2"), "comp2")
        
        stats = handler.get_error_statistics()
        assert stats['total_errors'] == 2
        assert 'category_breakdown' in stats
        assert 'severity_breakdown' in stats


class TestCompleteSystem:
    """Test complete inline editing system"""
    
    def test_system_creation(self):
        """Test system creation with default config"""
        system = InlineEditingSystem()
        
        assert system.config is not None
        assert system.metrics is not None
        assert system.editor_bridge is not None
        assert system.accessibility_manager is not None
        assert system.error_handler is not None
        
    def test_system_creation_with_config(self):
        """Test system creation with custom config"""
        config = SystemConfiguration(
            auto_commit_enabled=True,
            max_concurrent_editors=5,
            accessibility_enabled=False
        )
        
        system = InlineEditingSystem(config=config)
        assert system.config.auto_commit_enabled is True
        assert system.config.max_concurrent_editors == 5
        assert system.config.accessibility_enabled is False
        
    def test_editor_factory_integration(self):
        """Test editor factory integration"""
        system = InlineEditingSystem()
        
        def mock_factory(element_id, element_type, parent, config):
            return MockEditor(parent, config)
            
        system.set_editor_factory(mock_factory)
        assert system.editor_factory is not None
        
    def test_request_edit_workflow(self):
        """Test complete edit request workflow"""
        system = InlineEditingSystem()
        system.set_editor_factory(lambda *args: MockEditor())
        
        # Request edit
        result = system.request_edit("elem1", "text", "initial")
        assert result is True
        assert system.is_editing("elem1")
        assert system.metrics.active_editors_count == 1
        
        # Get active editor
        editor = system.get_active_editor("elem1")
        assert editor is not None
        assert isinstance(editor, MockEditor)
        
    def test_concurrent_editor_limit(self):
        """Test concurrent editor limit enforcement"""
        config = SystemConfiguration(max_concurrent_editors=2)
        system = InlineEditingSystem(config=config)
        system.set_editor_factory(lambda *args: MockEditor())
        
        # Should accept first two
        assert system.request_edit("elem1", "text") is True
        assert system.request_edit("elem2", "text") is True
        
        # Should reject third
        assert system.request_edit("elem3", "text") is False
        
    def test_cancel_all_edits(self):
        """Test cancelling all active edits"""
        system = InlineEditingSystem()
        system.set_editor_factory(lambda *args: MockEditor())
        
        # Start multiple edits
        system.request_edit("elem1", "text")
        system.request_edit("elem2", "text")
        assert system.metrics.active_editors_count == 2
        
        # Cancel all
        system.cancel_all_edits()
        assert system.metrics.active_editors_count == 0
        
    def test_save_all_edits(self):
        """Test saving all active edits"""
        system = InlineEditingSystem()
        system.set_editor_factory(lambda *args: MockEditor())
        
        # Start edits
        system.request_edit("elem1", "text")
        system.request_edit("elem2", "text")
        
        # Save all
        results = system.save_all_edits()
        assert len(results) == 2
        assert all(results.values())  # All should succeed
        
    def test_system_metrics_tracking(self):
        """Test system metrics tracking"""
        system = InlineEditingSystem()
        system.set_editor_factory(lambda *args: MockEditor())
        
        # Initial metrics
        metrics = system.get_metrics()
        assert metrics.total_edits_started == 0
        assert metrics.success_rate() == 0.0
        
        # Start and complete an edit
        system.request_edit("elem1", "text")
        metrics = system.get_metrics()
        assert metrics.total_edits_started == 1
        assert metrics.active_editors_count == 1
        
    def test_configuration_update(self):
        """Test runtime configuration updates"""
        system = InlineEditingSystem()
        
        old_config = system.get_configuration()
        assert old_config.max_concurrent_editors == 10
        
        new_config = SystemConfiguration(max_concurrent_editors=5)
        system.update_configuration(new_config)
        
        updated_config = system.get_configuration()
        assert updated_config.max_concurrent_editors == 5
        
    def test_system_status_reporting(self):
        """Test system status reporting"""
        system = InlineEditingSystem()
        
        status = system.get_system_status()
        assert 'configuration' in status
        assert 'metrics' in status
        assert 'active_editors' in status
        assert 'accessibility_enabled' in status
        
    def test_diagnostics_export(self):
        """Test diagnostics export"""
        system = InlineEditingSystem()
        
        diagnostics = system.export_diagnostics()
        assert 'timestamp' in diagnostics
        assert 'system_status' in diagnostics
        assert 'component_versions' in diagnostics
        
    def test_system_shutdown(self):
        """Test graceful system shutdown"""
        system = InlineEditingSystem()
        system.set_editor_factory(lambda *args: MockEditor())
        
        # Start some edits
        system.request_edit("elem1", "text")
        system.request_edit("elem2", "text")
        
        # Shutdown should cancel all
        system.shutdown()
        assert system.metrics.active_editors_count == 0
        
    def test_factory_function(self):
        """Test factory function for system creation"""
        config = SystemConfiguration(accessibility_enabled=False)
        system = create_inline_editing_system(config=config)
        
        assert isinstance(system, InlineEditingSystem)
        assert system.config.accessibility_enabled is False


class TestIntegrationScenarios:
    """Test complete integration scenarios"""
    
    def test_full_editing_workflow(self):
        """Test complete editing workflow from start to finish"""
        system = InlineEditingSystem()
        system.set_editor_factory(lambda *args: MockEditor())
        
        # Track events
        edit_started_called = False
        edit_completed_called = False
        
        def on_edit_started(element_id, editor):
            nonlocal edit_started_called
            edit_started_called = True
            
        def on_edit_completed(element_id):
            nonlocal edit_completed_called
            edit_completed_called = True
            
        system.editor_activated.connect(on_edit_started)
        system.editor_deactivated.connect(on_edit_completed)
        
        # Start edit
        system.request_edit("elem1", "text", "initial value")
        assert edit_started_called
        
        # Get editor and complete edit
        editor = system.get_active_editor("elem1")
        editor.save()
        assert edit_completed_called
        
    def test_error_handling_integration(self):
        """Test error handling integration with system"""
        system = InlineEditingSystem()
        
        # Factory that raises an error
        def failing_factory(*args):
            raise ValueError("Factory error")
            
        system.set_editor_factory(failing_factory)
        
        # Request should fail gracefully
        result = system.request_edit("elem1", "text")
        assert result is False
        assert system.metrics.total_errors > 0
        
    def test_accessibility_integration(self):
        """Test accessibility integration with system"""
        config = SystemConfiguration(accessibility_enabled=True)
        system = InlineEditingSystem(config=config)
        system.set_editor_factory(lambda *args: MockEditor())
        
        # Request edit - accessibility should be setup
        system.request_edit("elem1", "text")
        editor = system.get_active_editor("elem1")
        
        # Editor should be managed by accessibility manager
        assert editor in system.accessibility_manager.managed_widgets
        
    def test_performance_monitoring(self):
        """Test performance monitoring integration"""
        config = SystemConfiguration(performance_monitoring=True)
        system = InlineEditingSystem(config=config)
        
        # Performance timer should be active
        assert hasattr(system, 'performance_timer')
        
        # Metrics should be tracked
        metrics = system.get_metrics()
        assert hasattr(metrics, 'memory_usage_mb')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
=======
    def test_recovery_manager_created(self, editing_system):
        """Test recovery manager is created when enabled"""
        assert editing_system.recovery_manager is not None
        
    def test_recovery_disabled(self, parent_widget):
        """Test system works without recovery"""
        config = SystemConfiguration(enable_error_recovery=False)
        system = InlineEditingSystem(config, parent_widget)
        
        assert system.recovery_manager is None
        system.shutdown()
        
    def test_editor_recovery_registration(self, editing_system, parent_widget):
        """Test editors are registered with recovery manager"""
        mock_editor = MockEditor(parent_widget)
        
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=mock_editor):
            with patch.object(editing_system.recovery_manager, 'register_editor') as mock_register:
                editor = editing_system.create_editor("test_id", "text", parent_widget)
                
                mock_register.assert_called_once_with(mock_editor)
                
    def test_error_during_creation(self, editing_system, parent_widget):
        """Test error handling during editor creation"""
        with patch.object(editing_system.editor_bridge, 'create_editor', side_effect=Exception("Creation failed")):
            with patch.object(editing_system.recovery_manager.error_handler, 'handle_error') as mock_handle:
                editor = editing_system.create_editor("test_id", "text", parent_widget)
                
                assert editor is None
                mock_handle.assert_called_once()


class TestPerformanceMonitoring:
    """Test performance monitoring and metrics"""
    
    def test_metrics_collection(self, editing_system):
        """Test metrics are collected correctly"""
        metrics = editing_system.get_system_metrics()
        
        assert isinstance(metrics, SystemMetrics)
        assert metrics.active_editors == 0
        assert metrics.uptime_seconds > 0
        
    def test_metrics_update_signal(self, editing_system):
        """Test metrics update signal is emitted"""
        signal_received = Mock()
        editing_system.metrics_updated.connect(signal_received)
        
        # Trigger metrics update
        editing_system._update_metrics()
        
        signal_received.assert_called_once()
        
    def test_performance_monitoring_disabled(self, parent_widget):
        """Test system works without performance monitoring"""
        config = SystemConfiguration(enable_performance_monitoring=False)
        system = InlineEditingSystem(config, parent_widget)
        
        # Metrics timer should not be running
        assert not system.metrics_timer.isActive()
        system.shutdown()
        
    def test_system_status(self, editing_system):
        """Test comprehensive system status"""
        status = editing_system.get_system_status()
        
        assert 'state' in status
        assert 'metrics' in status
        assert 'active_editors' in status
        assert 'config' in status
        assert status['state'] == SystemState.READY.value


class TestMemoryManagement:
    """Test memory management and cleanup"""
    
    def test_cleanup_timer(self, editing_system):
        """Test cleanup timer is running"""
        assert editing_system.cleanup_timer.isActive()
        
    def test_weak_references(self, editing_system, parent_widget):
        """Test weak references are used for editors"""
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=MockEditor()):
            editor = editing_system.create_editor("test_id", "text", parent_widget)
            
            assert "test_id" in editing_system.editor_weakrefs
            assert editing_system.editor_weakrefs["test_id"]() == editor
            
    def test_cleanup_dead_references(self, editing_system, parent_widget):
        """Test cleanup of dead weak references"""
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=MockEditor()):
            editor = editing_system.create_editor("test_id", "text", parent_widget)
            
            # Simulate editor deletion
            del editor
            
            # Force cleanup
            editing_system._perform_cleanup()
            
            # Should be cleaned up
            assert "test_id" not in editing_system.active_editors
            
    def test_auto_save_timer(self, editing_system):
        """Test auto-save timer functionality"""
        assert editing_system.auto_save_timer.isActive()
        
    def test_memory_limit_cleanup(self, editing_system):
        """Test cleanup when memory limit is exceeded"""
        # Set low memory limit to trigger cleanup
        editing_system.config.memory_limit_mb = 0.1
        editing_system.metrics.memory_usage_mb = 1.0  # Above limit
        
        with patch('gc.collect') as mock_gc:
            editing_system._perform_cleanup()
            mock_gc.assert_called_once()


class TestAutoSave:
    """Test auto-save functionality"""
    
    def test_auto_save_dirty_editors(self, editing_system, parent_widget):
        """Test auto-save saves dirty editors"""
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=MockEditor()):
            editor = editing_system.create_editor("test_id", "text", parent_widget)
            editor.set_value("test value")  # Make dirty
            
            assert editor.is_dirty()
            
            # Trigger auto-save
            editing_system._perform_auto_save()
            
            assert not editor.is_dirty()
            
    def test_auto_save_no_dirty_editors(self, editing_system, parent_widget):
        """Test auto-save with no dirty editors"""
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=MockEditor()):
            editor = editing_system.create_editor("test_id", "text", parent_widget)
            
            # No changes made, should not be dirty
            assert not editor.is_dirty()
            
            # Auto-save should not do anything
            editing_system._perform_auto_save()
            
            # Still not dirty
            assert not editor.is_dirty()


class TestSignals:
    """Test signal emissions"""
    
    def test_system_state_changed_signal(self, editing_system):
        """Test system state changed signal"""
        signal_received = Mock()
        editing_system.system_state_changed.connect(signal_received)
        
        editing_system.shutdown()
        
        signal_received.assert_called_with(SystemState.SHUTDOWN.value)
        
    def test_editor_created_signal(self, editing_system, parent_widget):
        """Test editor created signal"""
        signal_received = Mock()
        editing_system.editor_created.connect(signal_received)
        
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=MockEditor()):
            editor = editing_system.create_editor("test_id", "text", parent_widget)
            
            signal_received.assert_called_once_with("test_id", editor)
            
    def test_editor_destroyed_signal(self, editing_system, parent_widget):
        """Test editor destroyed signal"""
        signal_received = Mock()
        editing_system.editor_destroyed.connect(signal_received)
        
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=MockEditor()):
            editing_system.create_editor("test_id", "text", parent_widget)
            editing_system.destroy_editor("test_id")
            
            signal_received.assert_called_once_with("test_id")


class TestSystemShutdown:
    """Test system shutdown procedure"""
    
    def test_graceful_shutdown(self, editing_system, parent_widget):
        """Test graceful system shutdown"""
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=MockEditor()):
            # Create some editors
            editor1 = editing_system.create_editor("test_1", "text", parent_widget)
            editor2 = editing_system.create_editor("test_2", "text", parent_widget)
            
            # Make them dirty
            editor1.set_value("value1")
            editor2.set_value("value2")
            
            # Shutdown should save and destroy all
            editing_system.shutdown()
            
            assert editing_system.state == SystemState.SHUTDOWN
            assert len(editing_system.active_editors) == 0
            assert not editing_system.metrics_timer.isActive()
            assert not editing_system.cleanup_timer.isActive()
            assert not editing_system.auto_save_timer.isActive()


class TestInlineEditingSystemWidget:
    """Test the widget wrapper"""
    
    def test_widget_creation(self, default_config, parent_widget, app):
        """Test widget wrapper creates successfully"""
        widget = InlineEditingSystemWidget(default_config, parent_widget)
        
        assert widget.editing_system is not None
        assert widget.status_label is not None
        assert widget.metrics_label is not None
        assert widget.save_all_button is not None
        assert widget.shutdown_button is not None
        
        widget.editing_system.shutdown()
        
    def test_status_update(self, default_config, parent_widget, app):
        """Test status display updates"""
        widget = InlineEditingSystemWidget(default_config, parent_widget)
        
        # Initial status should show ready
        widget._update_status("ready")
        assert "Ready" in widget.status_label.text()
        
        widget.editing_system.shutdown()
        
    def test_metrics_update(self, default_config, parent_widget, app):
        """Test metrics display updates"""
        widget = InlineEditingSystemWidget(default_config, parent_widget)
        
        metrics = {'active_editors': 5, 'success_rate': 95.5}
        widget._update_metrics(metrics)
        
        assert "5" in widget.metrics_label.text()
        assert "95.5%" in widget.metrics_label.text()
        
        widget.editing_system.shutdown()


class TestIntegrationWorkflows:
    """Test complete integration workflows"""
    
    def test_complete_editing_workflow(self, editing_system, parent_widget):
        """Test complete end-to-end editing workflow"""
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=MockEditor()):
            # Create editor
            editor = editing_system.create_editor("test_id", "text", parent_widget)
            assert editor is not None
            
            # Start editing
            success = editing_system.start_editing("test_id", "initial")
            assert success
            assert editor.is_editing()
            
            # Modify value
            editor.set_value("modified")
            assert editor.is_dirty()
            
            # Save
            save_results = editing_system.save_all_editors()
            assert save_results["test_id"]
            assert not editor.is_dirty()
            
            # Finish editing
            editor.finish_editing()
            assert not editor.is_editing()
            
            # Destroy editor
            success = editing_system.destroy_editor("test_id")
            assert success
            assert len(editing_system.active_editors) == 0
            
    def test_error_recovery_workflow(self, editing_system, parent_widget):
        """Test error recovery workflow"""
        # Create editor that will fail
        failing_editor = MockEditor(parent_widget)
        failing_editor.save = Mock(side_effect=Exception("Save failed"))
        
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=failing_editor):
            editor = editing_system.create_editor("test_id", "text", parent_widget)
            editor.set_value("test")
            
            # Save should fail and be handled
            save_results = editing_system.save_all_editors()
            assert not save_results["test_id"]
            assert editing_system.metrics.failed_saves > 0
            
    def test_accessibility_workflow(self, editing_system, parent_widget):
        """Test accessibility integration workflow"""
        mock_editor = MockEditor(parent_widget)
        
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=mock_editor):
            with patch.object(editing_system.accessibility_manager, 'setup_accessibility') as mock_setup:
                # Create editor
                editor = editing_system.create_editor("test_id", "text", parent_widget)
                
                # Accessibility should be setup
                mock_setup.assert_called_once_with(mock_editor)
                
                # Destroy editor should cleanup accessibility
                with patch.object(editing_system.accessibility_manager, 'remove_widget') as mock_remove:
                    editing_system.destroy_editor("test_id")
                    mock_remove.assert_called_once_with(mock_editor)


class TestStressAndPerformance:
    """Stress tests and performance validation"""
    
    def test_many_editors_creation(self, editing_system, parent_widget):
        """Test creating many editors quickly"""
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=MockEditor()):
            start_time = time.time()
            
            # Create maximum number of editors
            max_editors = editing_system.config.max_concurrent_editors
            for i in range(max_editors):
                editor = editing_system.create_editor(f"test_{i}", "text", parent_widget)
                assert editor is not None
                
            creation_time = time.time() - start_time
            
            # Should create quickly (less than 1 second for 5 editors)
            assert creation_time < 1.0
            assert len(editing_system.active_editors) == max_editors
            
    def test_rapid_edit_operations(self, editing_system, parent_widget):
        """Test rapid editing operations"""
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=MockEditor()):
            editor = editing_system.create_editor("test_id", "text", parent_widget)
            
            start_time = time.time()
            
            # Perform many rapid operations
            for i in range(100):
                editor.set_value(f"value_{i}")
                assert editor.get_value() == f"value_{i}"
                
            operation_time = time.time() - start_time
            
            # Should handle rapid operations quickly
            assert operation_time < 0.5  # 100 operations in less than 0.5 seconds
            
    def test_memory_usage_stability(self, editing_system, parent_widget):
        """Test memory usage remains stable"""
        import gc
        
        with patch.object(editing_system.editor_bridge, 'create_editor', return_value=MockEditor()):
            # Create and destroy editors repeatedly
            for cycle in range(10):
                editors = []
                
                # Create editors
                for i in range(5):
                    editor = editing_system.create_editor(f"test_{cycle}_{i}", "text", parent_widget)
                    editors.append(editor)
                    
                # Destroy editors
                for i, editor in enumerate(editors):
                    editing_system.destroy_editor(f"test_{cycle}_{i}")
                    
                # Force garbage collection
                gc.collect()
                
            # Memory usage should be reasonable
            metrics = editing_system.get_system_metrics()
            assert metrics.memory_usage_mb < editing_system.config.memory_limit_mb


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
>>>>>>> origin/main
