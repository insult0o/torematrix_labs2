"""Tests for layout migration system."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from src.torematrix.ui.layouts.migration import (
    LayoutMigrator, LayoutVersionManager, LayoutMigrationManager,
    MigrationStep, MigrationPlan, MigrationRecord, MigrationResult,
    MigrationType, MigrationError
)
from src.torematrix.ui.layouts.persistence import LayoutPersistence


@pytest.fixture
def version_manager():
    """Create version manager for testing."""
    return LayoutVersionManager()


@pytest.fixture
def mock_persistence():
    """Create mock persistence for testing."""
    persistence = Mock(spec=LayoutPersistence)
    persistence._backup_path = Path("/tmp/backups")
    persistence._find_layout_file = Mock()
    return persistence


@pytest.fixture
def layout_migrator(version_manager, mock_persistence):
    """Create layout migrator for testing."""
    return LayoutMigrator(version_manager, mock_persistence)


class TestLayoutVersionManager:
    """Test layout version management."""
    
    def test_current_version(self, version_manager):
        """Test current version constant."""
        assert version_manager.get_current_version() == "3.0.0"
        assert version_manager.CURRENT_VERSION == "3.0.0"
    
    def test_version_support_check(self, version_manager):
        """Test version support checking."""
        # Supported versions
        assert version_manager.is_version_supported("1.0.0") is True
        assert version_manager.is_version_supported("2.0.0") is True
        assert version_manager.is_version_supported("3.0.0") is True
        
        # Unsupported versions
        assert version_manager.is_version_supported("0.9.0") is False
        assert version_manager.is_version_supported("invalid") is False
    
    def test_migration_needed_check(self, version_manager):
        """Test migration necessity checking."""
        # Older versions need migration
        assert version_manager.needs_migration("1.0.0") is True
        assert version_manager.needs_migration("2.0.0") is True
        
        # Current version doesn't need migration
        assert version_manager.needs_migration("3.0.0") is False
        
        # Invalid versions assume migration needed
        assert version_manager.needs_migration("invalid") is True
    
    def test_migration_path_calculation(self, version_manager):
        """Test migration path calculation."""
        path = version_manager.get_migration_path("1.0.0", "3.0.0")
        assert len(path) == 2
        assert path[0] == "1.0.0"
        assert path[1] == "3.0.0"
        
        # Same version should return empty path
        path = version_manager.get_migration_path("2.0.0", "2.0.0")
        assert len(path) == 0
    
    def test_version_detection_from_data(self, version_manager):
        """Test version detection from layout data."""
        # Test with explicit version in metadata
        data_with_version = {
            "metadata": {"version": "2.0.0"},
            "layout": {}
        }
        assert version_manager.detect_layout_version(data_with_version) == "2.0.0"
        
        # Test with root version field
        data_with_root_version = {
            "version": "1.5.0",
            "layout": {}
        }
        assert version_manager.detect_layout_version(data_with_root_version) == "1.5.0"
        
        # Test structure-based detection for v3.0.0
        v3_data = {
            "metadata": {"tags": [], "description": "test"},
            "displays": [],
            "global_properties": {},
            "layout": {}
        }
        assert version_manager.detect_layout_version(v3_data) == "3.0.0"
        
        # Test structure-based detection for v2.0.0
        v2_data = {
            "metadata": {"author": "test", "modified": "2024-01-01"},
            "displays": [],
            "layout": {}
        }
        assert version_manager.detect_layout_version(v2_data) == "2.0.0"
        
        # Test fallback to v1.0.0
        v1_data = {
            "metadata": {"name": "test"},
            "layout": {}
        }
        assert version_manager.detect_layout_version(v1_data) == "1.0.0"
    
    def test_version_schema_validation(self, version_manager):
        """Test version schema validation."""
        # Test valid v1.0.0 data
        v1_data = {
            "layout": {},
            "metadata": {"name": "test"}
        }
        assert version_manager.validate_layout_format(v1_data, "1.0.0") is True
        
        # Test invalid v1.0.0 data (missing required fields)
        invalid_v1_data = {
            "metadata": {"name": "test"}
            # Missing layout field
        }
        assert version_manager.validate_layout_format(invalid_v1_data, "1.0.0") is False
        
        # Test unknown version (should return True as fallback)
        assert version_manager.validate_layout_format({}, "999.0.0") is True


class TestMigrationStep:
    """Test migration step functionality."""
    
    def test_migration_step_creation(self):
        """Test creating migration step."""
        def dummy_migration(data):
            return data
        
        step = MigrationStep(
            step_id="test_step",
            name="Test Step",
            description="Test description",
            migration_type=MigrationType.SCHEMA_UPGRADE,
            from_version="1.0.0",
            to_version="2.0.0",
            migration_function=dummy_migration
        )
        
        assert step.step_id == "test_step"
        assert step.name == "Test Step"
        assert step.migration_type == MigrationType.SCHEMA_UPGRADE
        assert step.from_version == "1.0.0"
        assert step.to_version == "2.0.0"
        assert step.required is True
        assert step.backup_required is True
        assert step.reversible is False
        assert step.migration_function == dummy_migration


class TestLayoutMigrator:
    """Test layout migrator functionality."""
    
    def test_migration_step_registration(self, layout_migrator):
        """Test registering migration steps."""
        def dummy_migration(data):
            return data
        
        step = MigrationStep(
            step_id="test_registration",
            name="Test Registration",
            description="Test",
            migration_type=MigrationType.SCHEMA_UPGRADE,
            from_version="1.0.0",
            to_version="2.0.0",
            migration_function=dummy_migration
        )
        
        layout_migrator.register_migration_step(step)
        
        assert "test_registration" in layout_migrator._migration_steps
        assert layout_migrator._migration_steps["test_registration"] == step
    
    def test_migration_plan_creation(self, layout_migrator):
        """Test creating migration plan."""
        plan = layout_migrator.create_migration_plan("test_layout", "1.0.0", "3.0.0")
        
        assert isinstance(plan, MigrationPlan)
        assert plan.layout_name == "test_layout"
        assert plan.source_version == "1.0.0"
        assert plan.target_version == "3.0.0"
        assert len(plan.steps) > 0  # Should have builtin migration steps
        assert plan.estimated_duration > 0
        assert plan.risk_level in ["low", "medium", "high"]
    
    def test_builtin_migration_v1_to_v2(self, layout_migrator):
        """Test built-in v1 to v2 migration."""
        # Test adding displays
        v1_data = {
            "metadata": {"name": "test"},
            "layout": {}
        }
        
        migrated = layout_migrator._migrate_v1_to_v2_add_displays(v1_data)
        assert "displays" in migrated
        assert len(migrated["displays"]) == 1
        assert migrated["displays"][0]["primary"] is True
        
        # Test enhancing metadata
        migrated = layout_migrator._migrate_v1_to_v2_enhance_metadata(migrated)
        assert migrated["metadata"]["version"] == "2.0.0"
        assert "author" in migrated["metadata"]
        assert "modified" in migrated["metadata"]
    
    def test_builtin_migration_v2_to_v3(self, layout_migrator):
        """Test built-in v2 to v3 migration."""
        # Test adding global properties
        v2_data = {
            "metadata": {"name": "test", "version": "2.0.0"},
            "displays": [],
            "layout": {}
        }
        
        migrated = layout_migrator._migrate_v2_to_v3_add_global_properties(v2_data)
        assert "global_properties" in migrated
        assert "serialization_timestamp" in migrated["global_properties"]
        
        # Test enhancing metadata
        migrated = layout_migrator._migrate_v2_to_v3_enhance_metadata(migrated)
        assert migrated["metadata"]["version"] == "3.0.0"
        assert "description" in migrated["metadata"]
        assert "tags" in migrated["metadata"]
        assert "migrated" in migrated["metadata"]["tags"]
    
    def test_migration_execution_success(self, layout_migrator, mock_persistence):
        """Test successful migration execution."""
        # Mock layout data
        v1_data = {
            "metadata": {"name": "test_layout"},
            "layout": {"type": "widget", "component_id": "test"}
        }
        
        # Mock file operations
        layout_file = Mock()
        layout_file.exists.return_value = True
        mock_persistence._find_layout_file.return_value = layout_file
        
        with patch("builtins.open", mock=Mock()) as mock_open:
            with patch("json.load", return_value=v1_data):
                with patch("json.dump"):
                    # Create migration plan
                    plan = layout_migrator.create_migration_plan("test_layout", "1.0.0", "2.0.0")
                    
                    # Execute migration
                    record = layout_migrator.execute_migration_plan(plan)
                    
                    assert isinstance(record, MigrationRecord)
                    assert record.result == MigrationResult.SUCCESS
                    assert record.steps_completed > 0
                    assert record.error_message is None
    
    def test_migration_execution_failure(self, layout_migrator, mock_persistence):
        """Test migration execution failure."""
        # Mock file operations to fail
        layout_file = Mock()
        layout_file.exists.return_value = False
        mock_persistence._find_layout_file.return_value = layout_file
        
        # Create migration plan
        plan = layout_migrator.create_migration_plan("nonexistent_layout", "1.0.0", "2.0.0")
        
        # Execute migration (should fail)
        record = layout_migrator.execute_migration_plan(plan)
        
        assert record.result == MigrationResult.FAILED
        assert record.error_message is not None
        assert record.steps_completed == 0
    
    def test_migration_with_backup(self, layout_migrator, mock_persistence):
        """Test migration with backup creation."""
        v1_data = {
            "metadata": {"name": "test_layout"},
            "layout": {"type": "widget", "component_id": "test"}
        }
        
        layout_file = Mock()
        layout_file.exists.return_value = True
        mock_persistence._find_layout_file.return_value = layout_file
        
        with patch("builtins.open", mock=Mock()):
            with patch("json.load", return_value=v1_data):
                with patch("json.dump"):
                    with patch.object(layout_migrator, "_create_migration_backup", return_value="/tmp/backup.json"):
                        plan = layout_migrator.create_migration_plan("test_layout", "1.0.0", "2.0.0")
                        record = layout_migrator.execute_migration_plan(plan, create_backup=True)
                        
                        assert record.backup_path == "/tmp/backup.json"
                        assert record.rollback_available is True
    
    def test_migration_rollback(self, layout_migrator, mock_persistence):
        """Test migration rollback functionality."""
        # Create a migration record with backup
        record = MigrationRecord(
            record_id="test_record",
            layout_name="test_layout",
            plan_id="test_plan",
            from_version="1.0.0",
            to_version="2.0.0",
            result=MigrationResult.FAILED,
            started=datetime.now(timezone.utc),
            completed=datetime.now(timezone.utc),
            duration=1.0,
            steps_completed=0,
            total_steps=1,
            backup_path="/tmp/backup.json",
            rollback_available=True
        )
        
        layout_migrator._migration_records.append(record)
        
        with patch.object(layout_migrator, "_perform_rollback") as mock_rollback:
            result = layout_migrator.rollback_migration("test_record")
            
            assert result is True
            mock_rollback.assert_called_once_with("test_layout", "/tmp/backup.json")
    
    def test_migration_history(self, layout_migrator):
        """Test migration history tracking."""
        # Add some test records
        record1 = MigrationRecord(
            record_id="record1",
            layout_name="layout1",
            plan_id="plan1",
            from_version="1.0.0",
            to_version="2.0.0",
            result=MigrationResult.SUCCESS,
            started=datetime.now(timezone.utc),
            completed=datetime.now(timezone.utc),
            duration=1.0,
            steps_completed=1,
            total_steps=1
        )
        
        record2 = MigrationRecord(
            record_id="record2",
            layout_name="layout2",
            plan_id="plan2",
            from_version="2.0.0",
            to_version="3.0.0",
            result=MigrationResult.FAILED,
            started=datetime.now(timezone.utc),
            completed=datetime.now(timezone.utc),
            duration=0.5,
            steps_completed=0,
            total_steps=1
        )
        
        layout_migrator._migration_records.extend([record1, record2])
        
        # Get all history
        history = layout_migrator.get_migration_history()
        assert len(history) == 2
        
        # Get filtered history
        layout1_history = layout_migrator.get_migration_history("layout1")
        assert len(layout1_history) == 1
        assert layout1_history[0].layout_name == "layout1"
    
    def test_migration_integrity_validation(self, layout_migrator, mock_persistence):
        """Test migration integrity validation."""
        valid_data = {
            "metadata": {"name": "test", "version": "3.0.0"},
            "displays": [],
            "layout": {},
            "global_properties": {}
        }
        
        layout_file = Mock()
        layout_file.exists.return_value = True
        mock_persistence._find_layout_file.return_value = layout_file
        
        with patch("builtins.open", mock=Mock()):
            with patch("json.load", return_value=valid_data):
                result = layout_migrator.validate_migration_integrity("test_layout")
                assert result is True
        
        # Test with nonexistent layout
        layout_file.exists.return_value = False
        result = layout_migrator.validate_migration_integrity("nonexistent")
        assert result is False


class TestMigrationManager:
    """Test migration manager functionality."""
    
    @pytest.fixture
    def mock_event_bus(self):
        return Mock()
    
    @pytest.fixture
    def mock_config_manager(self):
        return Mock()
    
    @pytest.fixture
    def mock_state_manager(self):
        return Mock()
    
    @pytest.fixture
    def migration_manager(self, mock_event_bus, mock_config_manager, mock_state_manager, mock_persistence):
        from src.torematrix.ui.layouts.migration import LayoutMigrationManager
        return LayoutMigrationManager(
            mock_event_bus,
            mock_config_manager,
            mock_state_manager,
            mock_persistence
        )
    
    def test_migration_manager_initialization(self, migration_manager):
        """Test migration manager initialization."""
        assert migration_manager._version_manager is not None
        assert migration_manager._migrator is not None
        assert migration_manager._auto_migration_enabled is True
        assert migration_manager._backup_before_migration is True
    
    def test_layout_compatibility_check(self, migration_manager):
        """Test layout compatibility checking."""
        v1_data = {
            "metadata": {"name": "test"},
            "layout": {}
        }
        
        with patch.object(migration_manager._migrator, "_load_layout_data", return_value=v1_data):
            compatibility = migration_manager.check_layout_compatibility("test_layout")
            
            assert "compatible" in compatibility
            assert "current_version" in compatibility
            assert "needs_migration" in compatibility
            assert "is_supported" in compatibility
            assert compatibility["compatible"] is False  # v1.0.0 needs migration
            assert compatibility["needs_migration"] is True
            assert compatibility["current_version"] == "1.0.0"
    
    def test_migrate_layout_with_signals(self, migration_manager):
        """Test layout migration with signal emission."""
        v1_data = {
            "metadata": {"name": "test_layout"},
            "layout": {}
        }
        
        with patch.object(migration_manager._migrator, "_load_layout_data", return_value=v1_data):
            with patch.object(migration_manager._migrator, "migrate_layout") as mock_migrate:
                # Mock successful migration
                mock_record = Mock()
                mock_record.result = MigrationResult.SUCCESS
                mock_record.duration = 1.0
                mock_record.steps_completed = 2
                mock_migrate.return_value = mock_record
                
                # Perform migration
                record = migration_manager.migrate_layout("test_layout")
                
                # Verify signals were emitted
                migration_manager.migration_started.emit.assert_called_once()
                migration_manager.migration_completed.emit.assert_called_once()
                
                # Verify events were published
                assert migration_manager._event_bus.publish.call_count >= 2
    
    def test_migrate_all_layouts(self, migration_manager, mock_persistence):
        """Test migrating all layouts."""
        # Mock layout list
        mock_persistence.list_layouts.return_value = ["layout1", "layout2"]
        
        with patch.object(migration_manager, "migrate_layout") as mock_migrate:
            # Mock successful migrations
            mock_record = Mock()
            mock_record.result = MigrationResult.SUCCESS
            mock_migrate.return_value = mock_record
            
            results = migration_manager.migrate_all_layouts()
            
            assert len(results) == 2
            assert "layout1" in results
            assert "layout2" in results
            assert mock_migrate.call_count == 2
    
    def test_auto_migration_settings(self, migration_manager):
        """Test auto migration settings."""
        # Test enabling auto migration
        migration_manager.enable_auto_migration(False)
        assert migration_manager._auto_migration_enabled is False
        
        # Test backup setting
        migration_manager.set_backup_before_migration(False)
        assert migration_manager._backup_before_migration is False
    
    def test_auto_migration_on_layout_load(self, migration_manager):
        """Test automatic migration when layout is loaded."""
        migration_manager._auto_migration_enabled = True
        
        with patch.object(migration_manager, "check_layout_compatibility") as mock_check:
            with patch.object(migration_manager, "migrate_layout") as mock_migrate:
                # Mock layout that needs migration
                mock_check.return_value = {
                    "needs_migration": True,
                    "is_supported": True
                }
                
                # Simulate layout loaded event
                migration_manager._on_layout_loaded({"layout_name": "test_layout"})
                
                # Should trigger auto migration
                mock_migrate.assert_called_once_with("test_layout")
    
    def test_startup_migration_check(self, migration_manager, mock_persistence):
        """Test migration check on application startup."""
        migration_manager._auto_migration_enabled = True
        
        # Mock layouts that need migration
        mock_persistence.list_layouts.return_value = ["old_layout1", "old_layout2"]
        
        with patch.object(migration_manager, "check_layout_compatibility") as mock_check:
            mock_check.return_value = {"needs_migration": True}
            
            # Simulate startup event
            migration_manager._on_application_startup({})
            
            # Should publish event about outdated layouts
            migration_manager._event_bus.publish.assert_called()
            event_call = migration_manager._event_bus.publish.call_args
            assert event_call[0][0] == "layout.migration_needed"
            assert "outdated_layouts" in event_call[0][1]


class TestErrorHandling:
    """Test error handling in migration system."""
    
    def test_migration_error_handling(self, layout_migrator):
        """Test migration error handling."""
        # Test with invalid migration plan
        invalid_plan = MigrationPlan(
            plan_id="invalid",
            source_version="1.0.0",
            target_version="2.0.0",
            layout_name="nonexistent_layout"
        )
        
        record = layout_migrator.execute_migration_plan(invalid_plan)
        assert record.result == MigrationResult.FAILED
        assert record.error_message is not None
    
    def test_version_manager_error_handling(self, version_manager):
        """Test version manager error handling."""
        # Test with invalid version strings
        with pytest.raises(MigrationError):
            version_manager.get_migration_path("invalid", "also_invalid")
        
        # Test graceful handling of malformed data
        malformed_data = "not a dict"
        version = version_manager.detect_layout_version(malformed_data)
        # Should return some default or handle gracefully
        assert isinstance(version, str)
    
    def test_rollback_error_handling(self, layout_migrator):
        """Test rollback error handling."""
        # Test rollback with invalid record ID
        result = layout_migrator.rollback_migration("nonexistent_record")
        assert result is False
        
        # Test rollback with record that doesn't support rollback
        no_rollback_record = MigrationRecord(
            record_id="no_rollback",
            layout_name="test",
            plan_id="test",
            from_version="1.0.0",
            to_version="2.0.0",
            result=MigrationResult.SUCCESS,
            started=datetime.now(timezone.utc),
            completed=datetime.now(timezone.utc),
            duration=1.0,
            steps_completed=1,
            total_steps=1,
            rollback_available=False
        )
        
        layout_migrator._migration_records.append(no_rollback_record)
        result = layout_migrator.rollback_migration("no_rollback")
        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])