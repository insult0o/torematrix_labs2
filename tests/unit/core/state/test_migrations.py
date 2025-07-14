"""
Tests for state migration functionality.

Comprehensive tests for state migrations, version management, and schema evolution.
"""

import pytest
from unittest.mock import MagicMock

from src.torematrix.core.state.migrations import (
    StateMigrator, StateMigration, MigrationInfo, MigrationType,
    InitialStateMigration, ElementsListMigration, DocumentMetadataMigration
)


class TestMigrationInfo:
    """Test MigrationInfo data class."""
    
    def test_migration_info_creation(self):
        """Test creating migration info."""
        info = MigrationInfo(
            id="test_migration",
            name="Test Migration",
            description="A test migration",
            from_version="1.0.0",
            to_version="1.1.0",
            migration_type=MigrationType.SCHEMA_CHANGE,
            required=True,
            reversible=False
        )
        
        assert info.id == "test_migration"
        assert info.name == "Test Migration"
        assert info.from_version == "1.0.0"
        assert info.to_version == "1.1.0"
        assert info.migration_type == MigrationType.SCHEMA_CHANGE
        assert info.required is True
        assert info.reversible is False


class MockMigration(StateMigration):
    """Mock migration for testing."""
    
    def __init__(self, migration_id, from_version, to_version, required=True):
        self._info = MigrationInfo(
            id=migration_id,
            name=f"Mock Migration {migration_id}",
            description=f"Mock migration from {from_version} to {to_version}",
            from_version=from_version,
            to_version=to_version,
            migration_type=MigrationType.DATA_TRANSFORM,
            required=required
        )
        self.applied = False
    
    @property
    def info(self) -> MigrationInfo:
        return self._info
    
    def migrate(self, state):
        self.applied = True
        # Add migration marker
        if "_meta" not in state:
            state["_meta"] = {}
        state["_meta"][f"migration_{self.info.id}"] = True
        return state


class TestStateMigrator:
    """Test StateMigrator functionality."""
    
    @pytest.fixture
    def migrator(self):
        """Create a StateMigrator instance."""
        return StateMigrator()
    
    def test_migrator_initialization(self, migrator):
        """Test migrator initialization."""
        assert len(migrator._migrations) == 0
        assert len(migrator._migration_order) == 0
        assert len(migrator._version_history) == 0
    
    def test_register_migration(self, migrator):
        """Test registering a migration."""
        migration = MockMigration("test_1", "1.0.0", "1.1.0")
        migrator.register_migration(migration)
        
        assert "test_1" in migrator._migrations
        assert "test_1" in migrator._migration_order
        assert migrator._migrations["test_1"] == migration
    
    def test_register_multiple_migrations(self, migrator):
        """Test registering multiple migrations in order."""
        migrations = [
            MockMigration("migration_1", "1.0.0", "1.1.0"),
            MockMigration("migration_2", "1.1.0", "1.2.0"),
            MockMigration("migration_3", "1.2.0", "1.3.0"),
        ]
        
        # Register in random order
        for migration in [migrations[1], migrations[0], migrations[2]]:
            migrator.register_migration(migration)
        
        # Should be ordered correctly
        assert migrator._migration_order == ["migration_1", "migration_2", "migration_3"]
    
    def test_migrate_state_single_migration(self, migrator):
        """Test migrating state with a single migration."""
        migration = MockMigration("single_migration", "1.0.0", "1.1.0")
        migrator.register_migration(migration)
        
        initial_state = {
            "_meta": {"version": "1.0.0"},
            "data": "test"
        }
        
        migrated_state = migrator.migrate_state(initial_state, "1.1.0")
        
        assert migration.applied is True
        assert migrated_state["_meta"]["version"] == "1.1.0"
        assert migrated_state["_meta"]["migration_single_migration"] is True
        assert migrated_state["_meta"]["last_migration"] == "single_migration"
    
    def test_migrate_state_multiple_migrations(self, migrator):
        """Test migrating state through multiple migrations."""
        migrations = [
            MockMigration("step_1", "1.0.0", "1.1.0"),
            MockMigration("step_2", "1.1.0", "1.2.0"),
            MockMigration("step_3", "1.2.0", "1.3.0"),
        ]
        
        for migration in migrations:
            migrator.register_migration(migration)
        
        initial_state = {
            "_meta": {"version": "1.0.0"},
            "data": "test"
        }
        
        migrated_state = migrator.migrate_state(initial_state, "1.3.0")
        
        # All migrations should have been applied
        for migration in migrations:
            assert migration.applied is True
        
        assert migrated_state["_meta"]["version"] == "1.3.0"
        assert migrated_state["_meta"]["migration_step_1"] is True
        assert migrated_state["_meta"]["migration_step_2"] is True
        assert migrated_state["_meta"]["migration_step_3"] is True
        assert migrated_state["_meta"]["last_migration"] == "step_3"
    
    def test_migrate_state_no_migrations_needed(self, migrator):
        """Test migrating state when no migrations are needed."""
        migration = MockMigration("not_needed", "1.0.0", "1.1.0")
        migrator.register_migration(migration)
        
        # State is already at target version
        current_state = {
            "_meta": {"version": "1.1.0"},
            "data": "test"
        }
        
        migrated_state = migrator.migrate_state(current_state, "1.1.0")
        
        assert migration.applied is False  # Should not have been applied
        assert migrated_state == current_state
    
    def test_migrate_state_to_latest(self, migrator):
        """Test migrating state to latest version."""
        migrations = [
            MockMigration("to_latest_1", "1.0.0", "1.1.0"),
            MockMigration("to_latest_2", "1.1.0", "1.2.0"),
        ]
        
        for migration in migrations:
            migrator.register_migration(migration)
        
        initial_state = {
            "_meta": {"version": "1.0.0"},
            "data": "test"
        }
        
        # Migrate to latest (no target version specified)
        migrated_state = migrator.migrate_state(initial_state)
        
        # Should migrate to the highest version available
        assert migrated_state["_meta"]["version"] == "1.2.0"
    
    def test_migrate_state_with_missing_version(self, migrator):
        """Test migrating state without version metadata."""
        migration = MockMigration("add_version", "*", "1.0.0")
        migrator.register_migration(migration)
        
        # State without version metadata
        initial_state = {"data": "no_version"}
        
        migrated_state = migrator.migrate_state(initial_state, "1.0.0")
        
        assert migration.applied is True
        assert migrated_state["_meta"]["version"] == "1.0.0"
    
    def test_can_migrate_to(self, migrator):
        """Test checking if state can be migrated to target version."""
        migration = MockMigration("can_migrate_test", "1.0.0", "1.1.0")
        migrator.register_migration(migration)
        
        state = {"_meta": {"version": "1.0.0"}}
        
        # Should be able to migrate
        can_migrate = migrator.can_migrate_to(state, "1.1.0")
        assert can_migrate is True
        
        # Cannot migrate to non-existent version
        can_migrate = migrator.can_migrate_to(state, "2.0.0")
        assert can_migrate is False
    
    def test_get_migration_info(self, migrator):
        """Test getting migration information."""
        migration = MockMigration("info_test", "1.0.0", "1.1.0")
        migrator.register_migration(migration)
        
        info = migrator.get_migration_info("info_test")
        assert info is not None
        assert info.id == "info_test"
        assert info.from_version == "1.0.0"
        assert info.to_version == "1.1.0"
        
        # Non-existent migration
        info = migrator.get_migration_info("nonexistent")
        assert info is None
    
    def test_list_migrations(self, migrator):
        """Test listing all migrations."""
        migrations = [
            MockMigration("list_1", "1.0.0", "1.1.0"),
            MockMigration("list_2", "1.1.0", "1.2.0"),
        ]
        
        for migration in migrations:
            migrator.register_migration(migration)
        
        migration_infos = migrator.list_migrations()
        assert len(migration_infos) == 2
        
        migration_ids = [info.id for info in migration_infos]
        assert "list_1" in migration_ids
        assert "list_2" in migration_ids
    
    def test_get_migration_path(self, migrator):
        """Test getting migration path between versions."""
        migrations = [
            MockMigration("path_1", "1.0.0", "1.1.0"),
            MockMigration("path_2", "1.1.0", "1.2.0"),
            MockMigration("path_3", "1.2.0", "1.3.0"),
        ]
        
        for migration in migrations:
            migrator.register_migration(migration)
        
        # Get path from 1.0.0 to 1.3.0
        path = migrator.get_migration_path("1.0.0", "1.3.0")
        assert len(path) == 3
        assert path[0].id == "path_1"
        assert path[1].id == "path_2"
        assert path[2].id == "path_3"
        
        # No migration needed
        path = migrator.get_migration_path("1.1.0", "1.1.0")
        assert len(path) == 0
    
    def test_version_comparison(self, migrator):
        """Test version comparison logic."""
        # Test _compare_versions method
        assert migrator._compare_versions("1.0.0", "1.0.0") == 0
        assert migrator._compare_versions("1.0.0", "1.1.0") == -1
        assert migrator._compare_versions("1.1.0", "1.0.0") == 1
        assert migrator._compare_versions("2.0.0", "1.9.9") == 1
        assert migrator._compare_versions("1.2.3", "1.2.4") == -1


class TestBuiltInMigrations:
    """Test the built-in migration implementations."""
    
    def test_initial_state_migration(self):
        """Test InitialStateMigration."""
        migration = InitialStateMigration()
        
        # Test migration info
        info = migration.info
        assert info.id == "initial_state"
        assert info.from_version == "*"
        assert info.to_version == "1.0.0"
        assert info.required is False
        
        # Test migration on state without metadata
        state = {"data": "test"}
        migrated_state = migration.migrate(state)
        
        assert "_meta" in migrated_state
        assert migrated_state["_meta"]["version"] == "1.0.0"
        assert migrated_state["_meta"]["schema_version"] == 1
        
        # Test migration on state with existing metadata
        state_with_meta = {
            "_meta": {"existing": True},
            "data": "test"
        }
        migrated_state = migration.migrate(state_with_meta)
        
        # Should not overwrite existing metadata
        assert migrated_state["_meta"]["existing"] is True
    
    def test_elements_list_migration(self):
        """Test ElementsListMigration."""
        migration = ElementsListMigration()
        
        # Test migration info
        info = migration.info
        assert info.id == "elements_list"
        assert info.from_version == "1.0.0"
        assert info.to_version == "1.1.0"
        assert info.required is True
        assert info.reversible is True
        
        # Test forward migration (dict to list)
        state_with_dict = {
            "elements": {
                "elem1": {"type": "text", "content": "Hello"},
                "elem2": {"type": "image", "src": "image.jpg"},
                "elem3": {"type": "table", "rows": 5}
            }
        }
        
        migrated_state = migration.migrate(state_with_dict)
        
        assert isinstance(migrated_state["elements"], list)
        assert len(migrated_state["elements"]) == 3
        
        # Check that IDs were preserved
        element_ids = [elem["id"] for elem in migrated_state["elements"]]
        assert "elem1" in element_ids
        assert "elem2" in element_ids
        assert "elem3" in element_ids
        
        # Test reverse migration (list to dict)
        reversed_state = migration.reverse_migrate(migrated_state)
        
        assert isinstance(reversed_state["elements"], dict)
        assert "elem1" in reversed_state["elements"]
        assert reversed_state["elements"]["elem1"]["type"] == "text"
    
    def test_document_metadata_migration(self):
        """Test DocumentMetadataMigration."""
        migration = DocumentMetadataMigration()
        
        # Test migration info
        info = migration.info
        assert info.id == "document_metadata"
        assert info.from_version == "1.1.0"
        assert info.to_version == "1.2.0"
        assert info.required is True
        
        # Test migration with old metadata format
        state_old_format = {
            "document": {
                "id": "test_doc",
                "metadata": {
                    "filename": "test.pdf",
                    "file_size": 1024000,
                    "file_type": "pdf",
                    "file_path": "/path/to/test.pdf",
                    "parsed_at": "2023-01-01T12:00:00",
                    "parser_version": "1.0.0",
                    "pages": 10,
                    "has_tables": True,
                    "has_images": False
                }
            },
            "elements": [{"id": "elem1"}, {"id": "elem2"}]
        }
        
        migrated_state = migration.migrate(state_old_format)
        
        new_metadata = migrated_state["document"]["metadata"]
        
        # Check new structure
        assert "file_info" in new_metadata
        assert "processing_info" in new_metadata
        assert "content_info" in new_metadata
        
        # Check file_info
        file_info = new_metadata["file_info"]
        assert file_info["name"] == "test.pdf"
        assert file_info["size"] == 1024000
        assert file_info["type"] == "pdf"
        assert file_info["path"] == "/path/to/test.pdf"
        
        # Check processing_info
        processing_info = new_metadata["processing_info"]
        assert processing_info["parsed_at"] == "2023-01-01T12:00:00"
        assert processing_info["parser_version"] == "1.0.0"
        assert processing_info["page_count"] == 10
        
        # Check content_info
        content_info = new_metadata["content_info"]
        assert content_info["elements_count"] == 2
        assert content_info["has_tables"] is True
        assert content_info["has_images"] is False


class TestComplexMigrationScenarios:
    """Test complex migration scenarios."""
    
    def test_full_migration_chain(self):
        """Test a complete migration chain with all built-in migrations."""
        migrator = StateMigrator()
        
        # Register all built-in migrations
        migrator.register_migration(InitialStateMigration())
        migrator.register_migration(ElementsListMigration())
        migrator.register_migration(DocumentMetadataMigration())
        
        # Start with raw state (no metadata)
        initial_state = {
            "document": {
                "id": "chain_test",
                "metadata": {
                    "filename": "chain_test.pdf",
                    "file_size": 2048000,
                    "file_type": "pdf",
                    "pages": 20,
                    "has_tables": True,
                    "has_images": True
                }
            },
            "elements": {
                "text1": {"type": "text", "content": "Hello World"},
                "table1": {"type": "table", "rows": 3, "cols": 4},
                "image1": {"type": "image", "src": "diagram.png"}
            }
        }
        
        # Migrate to latest version
        final_state = migrator.migrate_state(initial_state)
        
        # Check that all migrations were applied
        assert final_state["_meta"]["version"] == "1.2.0"
        
        # Check elements are now a list
        assert isinstance(final_state["elements"], list)
        assert len(final_state["elements"]) == 3
        
        # Check document metadata is restructured
        metadata = final_state["document"]["metadata"]
        assert "file_info" in metadata
        assert "processing_info" in metadata
        assert "content_info" in metadata
        assert metadata["content_info"]["elements_count"] == 3
    
    def test_optional_migration_handling(self):
        """Test handling of optional migrations."""
        migrator = StateMigrator()
        
        # Create an optional migration that might fail
        class OptionalMigration(StateMigration):
            @property
            def info(self):
                return MigrationInfo(
                    id="optional_test",
                    name="Optional Test",
                    description="Optional migration for testing",
                    from_version="1.0.0",
                    to_version="1.1.0",
                    migration_type=MigrationType.DATA_TRANSFORM,
                    required=False
                )
            
            def can_migrate(self, state):
                # Only migrate if state has specific field
                return "special_field" in state
            
            def migrate(self, state):
                state["optional_applied"] = True
                return state
        
        migrator.register_migration(OptionalMigration())
        
        # Test with state that can't be migrated
        state_without_field = {"_meta": {"version": "1.0.0"}, "data": "test"}
        migrated_state = migrator.migrate_state(state_without_field, "1.1.0")
        
        # Should complete without error, but optional migration not applied
        assert "optional_applied" not in migrated_state
        
        # Test with state that can be migrated
        state_with_field = {
            "_meta": {"version": "1.0.0"},
            "special_field": True,
            "data": "test"
        }
        migrated_state = migrator.migrate_state(state_with_field, "1.1.0")
        
        # Optional migration should have been applied
        assert migrated_state.get("optional_applied") is True
    
    def test_migration_failure_handling(self):
        """Test handling of migration failures."""
        migrator = StateMigrator()
        
        # Create a migration that always fails
        class FailingMigration(StateMigration):
            @property
            def info(self):
                return MigrationInfo(
                    id="failing_migration",
                    name="Failing Migration",
                    description="Migration that always fails",
                    from_version="1.0.0",
                    to_version="1.1.0",
                    migration_type=MigrationType.DATA_TRANSFORM,
                    required=True
                )
            
            def migrate(self, state):
                raise ValueError("Migration failed intentionally")
        
        migrator.register_migration(FailingMigration())
        
        state = {"_meta": {"version": "1.0.0"}, "data": "test"}
        
        # Should raise the migration error
        with pytest.raises(ValueError, match="Migration failed intentionally"):
            migrator.migrate_state(state, "1.1.0")
    
    def test_version_pattern_matching(self):
        """Test version pattern matching in migrations."""
        # Create migration with pattern matching
        class PatternMigration(StateMigration):
            @property
            def info(self):
                return MigrationInfo(
                    id="pattern_migration",
                    name="Pattern Migration",
                    description="Migration with version patterns",
                    from_version="1.x.x",  # Matches any 1.x.x version
                    to_version="2.0.0",
                    migration_type=MigrationType.VERSION_UPGRADE,
                    required=True
                )
            
            def migrate(self, state):
                state["pattern_applied"] = True
                return state
        
        migration = PatternMigration()
        
        # Test pattern matching
        assert migration._version_matches("1.0.0", "1.x.x") is True
        assert migration._version_matches("1.5.3", "1.x.x") is True
        assert migration._version_matches("2.0.0", "1.x.x") is False
        assert migration._version_matches("1.0.0", "*") is True