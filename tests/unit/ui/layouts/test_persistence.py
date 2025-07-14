"""Tests for layout persistence system."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from PyQt6.QtWidgets import QWidget, QSplitter, QApplication
from PyQt6.QtCore import Qt

from src.torematrix.ui.layouts.persistence import (
    LayoutPersistence, LayoutConfigManager, LayoutStorageType,
    LayoutProfile, LayoutBackup, PersistenceError
)
from src.torematrix.ui.layouts.serialization import LayoutMetadata, SerializedLayout, LayoutNode, ComponentState, LayoutType


@pytest.fixture
def qt_app():
    """Create QApplication for tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_event_bus():
    """Create mock event bus."""
    return Mock()


@pytest.fixture
def mock_config_manager():
    """Create mock config manager."""
    config = Mock()
    config.get.return_value = {}
    config.set.return_value = None
    config.has_section.return_value = False
    config.set_section.return_value = None
    return config


@pytest.fixture
def mock_state_manager():
    """Create mock state manager."""
    return Mock()


@pytest.fixture
def temp_storage_path():
    """Create temporary storage path for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def layout_config_manager(mock_config_manager):
    """Create layout config manager for testing."""
    return LayoutConfigManager(mock_config_manager)


@pytest.fixture
def layout_persistence(mock_event_bus, mock_config_manager, mock_state_manager, temp_storage_path):
    """Create layout persistence for testing."""
    return LayoutPersistence(
        mock_event_bus,
        mock_config_manager,
        mock_state_manager,
        temp_storage_path
    )


class TestLayoutProfile:
    """Test layout profile functionality."""
    
    def test_profile_creation(self):
        """Test creating layout profile."""
        profile = LayoutProfile(
            name="Test Profile",
            description="Test description",
            storage_type=LayoutStorageType.CUSTOM
        )
        
        assert profile.name == "Test Profile"
        assert profile.description == "Test description"
        assert profile.storage_type == LayoutStorageType.CUSTOM
        assert profile.auto_restore is True
        assert isinstance(profile.created, datetime)
        assert isinstance(profile.last_used, datetime)
        assert profile.usage_count == 0
        assert profile.tags == []
    
    def test_profile_defaults(self):
        """Test profile default values."""
        profile = LayoutProfile(name="Default Test")
        
        assert profile.description == ""
        assert profile.storage_type == LayoutStorageType.CUSTOM
        assert profile.auto_restore is True
        assert profile.usage_count == 0
        assert len(profile.tags) == 0


class TestLayoutBackup:
    """Test layout backup functionality."""
    
    def test_backup_creation(self):
        """Test creating layout backup."""
        backup = LayoutBackup(
            backup_id="test_backup_123",
            original_name="Test Layout",
            backup_timestamp=datetime.now(timezone.utc),
            backup_reason="test",
            layout_data='{"test": "data"}'
        )
        
        assert backup.backup_id == "test_backup_123"
        assert backup.original_name == "Test Layout"
        assert backup.backup_reason == "test"
        assert backup.layout_data == '{"test": "data"}'
        assert backup.metadata == {}


class TestLayoutConfigManager:
    """Test layout configuration manager."""
    
    def test_config_manager_initialization(self, layout_config_manager, mock_config_manager):
        """Test config manager initialization."""
        # Should ensure layout section exists
        mock_config_manager.has_section.assert_called_with("layouts")
        mock_config_manager.set_section.assert_called_once()
    
    def test_default_layout_management(self, layout_config_manager, mock_config_manager):
        """Test default layout management."""
        # Test setting default layout
        layout_config_manager.set_default_layout("test_layout")
        mock_config_manager.set.assert_called_with("layouts.default_layout", "test_layout")
        
        # Test getting default layout
        mock_config_manager.get.return_value = "saved_layout"
        result = layout_config_manager.get_default_layout()
        assert result == "saved_layout"
        mock_config_manager.get.assert_called_with("layouts.default_layout")
    
    def test_auto_restore_settings(self, layout_config_manager, mock_config_manager):
        """Test auto restore settings."""
        # Test enabling auto restore
        layout_config_manager.set_auto_restore_enabled(True)
        mock_config_manager.set.assert_called_with("layouts.auto_restore", True)
        
        # Test checking auto restore status
        mock_config_manager.get.return_value = False
        result = layout_config_manager.is_auto_restore_enabled()
        assert result is False
        mock_config_manager.get.assert_called_with("layouts.auto_restore", True)
    
    def test_backup_settings(self, layout_config_manager, mock_config_manager):
        """Test backup settings management."""
        # Test backup enabled
        layout_config_manager.set_backup_enabled(False)
        mock_config_manager.set.assert_called_with("layouts.backup_enabled", False)
        
        # Test backup retention
        layout_config_manager.set_backup_retention_days(45)
        mock_config_manager.set.assert_called_with("layouts.backup_retention_days", 45)
    
    def test_recent_layouts_management(self, layout_config_manager, mock_config_manager):
        """Test recent layouts management."""
        # Mock existing recent layouts
        mock_config_manager.get.return_value = ["layout1", "layout2"]
        
        # Add new layout
        layout_config_manager.add_recent_layout("layout3")
        
        # Should update with new layout at front
        expected_call = mock_config_manager.set.call_args
        assert expected_call[0][0] == "layouts.recent_layouts"
        recent_list = expected_call[0][1]
        assert recent_list[0] == "layout3"
        assert "layout1" in recent_list
        assert "layout2" in recent_list
    
    def test_project_layout_management(self, layout_config_manager, mock_config_manager):
        """Test project-specific layout management."""
        # Mock existing project layouts
        mock_config_manager.get.return_value = {"project1": "layout1"}
        
        # Set project layout
        layout_config_manager.set_project_layout("project2", "layout2")
        
        # Should call set with updated project layouts
        expected_call = mock_config_manager.set.call_args
        assert expected_call[0][0] == "layouts.project_layouts"
        project_layouts = expected_call[0][1]
        assert project_layouts["project1"] == "layout1"
        assert project_layouts["project2"] == "layout2"
    
    def test_user_preferences(self, layout_config_manager, mock_config_manager):
        """Test user preferences management."""
        # Test setting preference
        layout_config_manager.set_user_preference("test_key", "test_value")
        mock_config_manager.set.assert_called_with(
            "layouts.user_preferences.test_key", "test_value"
        )
        
        # Test getting preference with default
        mock_config_manager.get.return_value = None
        result = layout_config_manager.get_user_preference("missing_key", "default")
        assert result == "default"


class TestLayoutPersistence:
    """Test layout persistence functionality."""
    
    def test_persistence_initialization(self, layout_persistence, temp_storage_path):
        """Test persistence initialization."""
        # Should create storage directories
        assert (temp_storage_path / "backups").exists()
        assert (temp_storage_path / "temp").exists()
    
    def test_save_simple_layout(self, layout_persistence, qt_app, temp_storage_path):
        """Test saving a simple layout."""
        # Create test widget
        widget = QWidget()
        widget.setObjectName("test_widget")
        
        # Save layout
        result = layout_persistence.save_layout(
            "test_layout",
            widget,
            description="Test layout",
            storage_type=LayoutStorageType.CUSTOM
        )
        
        assert result is True
        
        # Check file was created
        layout_file = temp_storage_path / "custom" / "test_layout.json"
        assert layout_file.exists()
        
        # Verify file content
        with open(layout_file, 'r') as f:
            data = json.load(f)
        
        assert "metadata" in data
        assert "layout" in data
        assert data["metadata"]["name"] == "test_layout"
        assert data["metadata"]["description"] == "Test layout"
    
    def test_save_layout_overwrite_protection(self, layout_persistence, qt_app):
        """Test layout overwrite protection."""
        widget = QWidget()
        
        # Save initial layout
        layout_persistence.save_layout("protected_layout", widget)
        
        # Try to save again without overwrite flag
        with pytest.raises(PersistenceError, match="already exists"):
            layout_persistence.save_layout("protected_layout", widget)
        
        # Should succeed with overwrite=True
        result = layout_persistence.save_layout(
            "protected_layout", widget, overwrite=True
        )
        assert result is True
    
    def test_save_with_backup_creation(self, layout_persistence, qt_app, temp_storage_path):
        """Test saving with backup creation."""
        widget = QWidget()
        
        # Save initial layout
        layout_persistence.save_layout("backup_test", widget)
        
        # Save again with backup
        result = layout_persistence.save_layout(
            "backup_test", widget, overwrite=True, create_backup=True
        )
        
        assert result is True
        
        # Check backup was created
        backup_files = list((temp_storage_path / "backups").glob("backup_test_*.json"))
        assert len(backup_files) > 0
    
    def test_load_layout(self, layout_persistence, qt_app, temp_storage_path):
        """Test loading a layout."""
        # Create and save a splitter layout
        splitter = QSplitter(Qt.Orientation.Horizontal)
        child1 = QWidget()
        child1.setObjectName("child1")
        child2 = QWidget()
        child2.setObjectName("child2")
        splitter.addWidget(child1)
        splitter.addWidget(child2)
        splitter.setSizes([200, 300])
        
        layout_persistence.save_layout("load_test", splitter)
        
        # Load the layout
        loaded_widget = layout_persistence.load_layout("load_test")
        
        assert isinstance(loaded_widget, QSplitter)
        assert loaded_widget.orientation() == Qt.Orientation.Horizontal
        assert loaded_widget.count() == 2
        assert loaded_widget.sizes() == [200, 300]
    
    def test_load_nonexistent_layout(self, layout_persistence):
        """Test loading nonexistent layout."""
        with pytest.raises(PersistenceError, match="not found"):
            layout_persistence.load_layout("nonexistent")
    
    def test_delete_layout(self, layout_persistence, qt_app, temp_storage_path):
        """Test deleting a layout."""
        widget = QWidget()
        layout_name = "delete_test"
        
        # Save layout
        layout_persistence.save_layout(layout_name, widget)
        
        # Verify it exists
        assert layout_persistence.layout_exists(layout_name)
        
        # Delete it
        result = layout_persistence.delete_layout(layout_name)
        assert result is True
        
        # Verify it's gone
        assert not layout_persistence.layout_exists(layout_name)
    
    def test_delete_with_backup(self, layout_persistence, qt_app, temp_storage_path):
        """Test deleting layout with backup creation."""
        widget = QWidget()
        layout_name = "delete_backup_test"
        
        # Save layout
        layout_persistence.save_layout(layout_name, widget)
        
        # Delete with backup
        result = layout_persistence.delete_layout(layout_name, create_backup=True)
        assert result is True
        
        # Check backup was created
        backup_files = list((temp_storage_path / "backups").glob(f"{layout_name}_*.json"))
        assert len(backup_files) > 0
    
    def test_list_layouts(self, layout_persistence, qt_app):
        """Test listing layouts."""
        widget = QWidget()
        
        # Save multiple layouts
        layout_persistence.save_layout("list_test_1", widget, storage_type=LayoutStorageType.CUSTOM)
        layout_persistence.save_layout("list_test_2", widget, storage_type=LayoutStorageType.CUSTOM)
        
        # List layouts
        layouts = layout_persistence.list_layouts(LayoutStorageType.CUSTOM)
        
        assert "list_test_1" in layouts
        assert "list_test_2" in layouts
    
    def test_list_layouts_with_metadata(self, layout_persistence, qt_app):
        """Test listing layouts with metadata."""
        widget = QWidget()
        
        # Save layout with metadata
        layout_persistence.save_layout(
            "metadata_test",
            widget,
            description="Test description",
            storage_type=LayoutStorageType.CUSTOM
        )
        
        # List with metadata
        layouts = layout_persistence.list_layouts(
            LayoutStorageType.CUSTOM,
            include_metadata=True
        )
        
        assert len(layouts) > 0
        
        # Find our layout
        test_layout = next((l for l in layouts if l["name"] == "metadata_test"), None)
        assert test_layout is not None
        assert test_layout["description"] == "Test description"
        assert "created" in test_layout
        assert "modified" in test_layout
    
    def test_layout_exists(self, layout_persistence, qt_app):
        """Test layout existence checking."""
        widget = QWidget()
        layout_name = "exists_test"
        
        # Should not exist initially
        assert not layout_persistence.layout_exists(layout_name)
        
        # Save layout
        layout_persistence.save_layout(layout_name, widget)
        
        # Should exist now
        assert layout_persistence.layout_exists(layout_name)
    
    def test_export_layout(self, layout_persistence, qt_app, temp_storage_path):
        """Test exporting layout to external file."""
        widget = QWidget()
        layout_name = "export_test"
        
        # Save layout
        layout_persistence.save_layout(layout_name, widget)
        
        # Export to external file
        export_path = temp_storage_path / "exported_layout.json"
        result = layout_persistence.export_layout(layout_name, export_path)
        
        assert result is True
        assert export_path.exists()
        
        # Verify exported content
        with open(export_path, 'r') as f:
            data = json.load(f)
        
        assert data["metadata"]["name"] == layout_name
    
    def test_import_layout(self, layout_persistence, qt_app, temp_storage_path):
        """Test importing layout from external file."""
        # Create external layout file
        layout_data = {
            "metadata": {
                "name": "imported_layout",
                "version": "1.0.0",
                "created": "2024-01-01T00:00:00Z",
                "modified": "2024-01-01T00:00:00Z",
                "author": "Test",
                "description": "Imported layout",
                "tags": []
            },
            "displays": [],
            "layout": {
                "type": "widget",
                "component_id": "test_widget",
                "state": {
                    "visible": True,
                    "enabled": True,
                    "geometry": None,
                    "size_policy": None,
                    "properties": {}
                },
                "children": [],
                "properties": {}
            },
            "global_properties": {}
        }
        
        import_path = temp_storage_path / "import_test.json"
        with open(import_path, 'w') as f:
            json.dump(layout_data, f)
        
        # Import the layout
        result = layout_persistence.import_layout(import_path)
        
        assert result is True
        assert layout_persistence.layout_exists("imported_layout")
    
    def test_import_with_rename(self, layout_persistence, qt_app, temp_storage_path):
        """Test importing layout with name change."""
        # Create external layout file
        layout_data = {
            "metadata": {
                "name": "original_name",
                "version": "1.0.0",
                "created": "2024-01-01T00:00:00Z",
                "modified": "2024-01-01T00:00:00Z",
                "author": "Test",
                "description": "",
                "tags": []
            },
            "displays": [],
            "layout": {
                "type": "widget",
                "component_id": "test_widget",
                "state": {
                    "visible": True,
                    "enabled": True,
                    "geometry": None,
                    "size_policy": None,
                    "properties": {}
                },
                "children": [],
                "properties": {}
            },
            "global_properties": {}
        }
        
        import_path = temp_storage_path / "rename_test.json"
        with open(import_path, 'w') as f:
            json.dump(layout_data, f)
        
        # Import with new name
        result = layout_persistence.import_layout(
            import_path,
            layout_name="renamed_layout"
        )
        
        assert result is True
        assert layout_persistence.layout_exists("renamed_layout")
        assert not layout_persistence.layout_exists("original_name")
    
    def test_get_layout_info(self, layout_persistence, qt_app):
        """Test getting detailed layout information."""
        widget = QWidget()
        layout_name = "info_test"
        
        # Save layout
        layout_persistence.save_layout(
            layout_name,
            widget,
            description="Test info layout"
        )
        
        # Get info
        info = layout_persistence.get_layout_info(layout_name)
        
        assert info is not None
        assert info["name"] == layout_name
        assert info["description"] == "Test info layout"
        assert "created" in info
        assert "modified" in info
        assert "file_path" in info
        assert "file_size" in info
    
    def test_auto_restore_layout_setting(self, layout_persistence):
        """Test setting auto-restore layout."""
        layout_name = "auto_restore_test"
        
        # Set auto-restore layout
        layout_persistence.set_auto_restore_layout(layout_name)
        
        # Should call config manager
        layout_persistence._config_mgr._config.set.assert_called()
    
    def test_auto_save_functionality(self, layout_persistence, qt_app):
        """Test auto-save functionality."""
        widget = QWidget()
        
        # Enable auto-save and set short interval for testing
        layout_persistence._auto_save_enabled = True
        layout_persistence._config_mgr.get_user_preference = Mock(return_value=1)  # 1 second
        
        # First auto-save should work
        result1 = layout_persistence.auto_save_current_layout(widget, "autosave_test")
        assert result1 is True
        
        # Second auto-save within interval should be skipped
        result2 = layout_persistence.auto_save_current_layout(widget, "autosave_test")
        assert result2 is False
    
    def test_cleanup_old_backups(self, layout_persistence, temp_storage_path):
        """Test cleanup of old backups."""
        # Create some mock backup files
        backup_dir = temp_storage_path / "backups"
        
        # Create old backup file
        old_backup = backup_dir / "old_backup.json"
        old_backup.write_text('{"test": "data"}')
        
        # Mock backup registry with old entry
        old_timestamp = datetime.now(timezone.utc) - layout_persistence._config_mgr.get_backup_retention_days() * 2
        layout_persistence._backup_registry["old_backup"] = LayoutBackup(
            backup_id="old_backup",
            original_name="test_layout",
            backup_timestamp=old_timestamp,
            backup_reason="test",
            layout_data='{"test": "data"}'
        )
        
        # Run cleanup
        removed_count = layout_persistence.cleanup_old_backups()
        
        assert removed_count > 0
        assert "old_backup" not in layout_persistence._backup_registry


class TestErrorHandling:
    """Test error handling in persistence system."""
    
    def test_save_invalid_widget(self, layout_persistence):
        """Test saving invalid widget."""
        with pytest.raises(PersistenceError):
            layout_persistence.save_layout("invalid", None)
    
    def test_load_corrupted_file(self, layout_persistence, temp_storage_path):
        """Test loading corrupted layout file."""
        # Create corrupted file
        layout_file = temp_storage_path / "custom" / "corrupted.json"
        layout_file.parent.mkdir(parents=True, exist_ok=True)
        layout_file.write_text("invalid json content")
        
        with pytest.raises(PersistenceError):
            layout_persistence.load_layout("corrupted")
    
    def test_storage_path_permissions(self, mock_event_bus, mock_config_manager, mock_state_manager):
        """Test handling of storage path permission issues."""
        # Try to create persistence with invalid path
        invalid_path = Path("/invalid/path/that/does/not/exist")
        
        # Should handle gracefully or raise appropriate error
        try:
            persistence = LayoutPersistence(
                mock_event_bus,
                mock_config_manager,
                mock_state_manager,
                invalid_path
            )
            # If it succeeds, the path should be created
            assert invalid_path.exists()
        except (PermissionError, OSError):
            # Expected for paths we can't create
            pass


if __name__ == "__main__":
    pytest.main([__file__])