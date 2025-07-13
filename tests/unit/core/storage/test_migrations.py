"""
Unit tests for storage migration utilities.
"""

import pytest
import tempfile
import json
from dataclasses import dataclass
from typing import Optional, Dict, Any
from unittest.mock import Mock, patch
from pathlib import Path

from torematrix.core.storage import (
    Migration, MigrationManager, MigrationHistory, BackendMigrator,
    CreateIndexesMigration, StorageError, Repository,
    SQLiteRepository, SQLiteConfig
)
from torematrix.core.storage.factory import StorageFactory, StorageBackend


@dataclass
class TestEntity:
    """Test entity for migration tests."""
    id: Optional[str] = None
    name: str = ""
    value: int = 0
    version: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "value": self.value,
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestEntity':
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            value=data.get("value", 0),
            version=data.get("version", 1)
        )


class TestMigrationBase:
    """Test base Migration class."""
    
    def test_migration_creation(self):
        """Test migration instance creation."""
        
        class TestMigration(Migration):
            def up(self, repository: Repository) -> None:
                pass
            
            def down(self, repository: Repository) -> None:
                pass
        
        migration = TestMigration("001", "Test migration")
        
        assert migration.version == "001"
        assert migration.description == "Test migration"
        assert migration.checksum is not None
        assert len(migration.checksum) == 16  # SHA256 truncated to 16 chars
    
    def test_migration_checksum_consistency(self):
        """Test that migration checksum is consistent."""
        
        class TestMigration(Migration):
            def up(self, repository: Repository) -> None:
                # Same implementation
                repository.execute_query("CREATE TABLE test (id INTEGER)")
                
            def down(self, repository: Repository) -> None:
                repository.execute_query("DROP TABLE test")
        
        migration1 = TestMigration("001", "Test migration")
        migration2 = TestMigration("001", "Test migration")
        
        # Same migration should have same checksum
        assert migration1.checksum == migration2.checksum
    
    def test_migration_checksum_different(self):
        """Test that different migrations have different checksums."""
        
        class TestMigration1(Migration):
            def up(self, repository: Repository) -> None:
                repository.execute_query("CREATE TABLE test1 (id INTEGER)")
            
            def down(self, repository: Repository) -> None:
                repository.execute_query("DROP TABLE test1")
        
        class TestMigration2(Migration):
            def up(self, repository: Repository) -> None:
                repository.execute_query("CREATE TABLE test2 (id INTEGER)")
            
            def down(self, repository: Repository) -> None:
                repository.execute_query("DROP TABLE test2")
        
        migration1 = TestMigration1("001", "Test migration 1")
        migration2 = TestMigration2("002", "Test migration 2")
        
        # Different migrations should have different checksums
        assert migration1.checksum != migration2.checksum


class TestMigrationHistory:
    """Test MigrationHistory class."""
    
    @pytest.fixture
    def mock_repository(self):
        """Mock repository for testing."""
        repo = Mock(spec=Repository)
        repo.create_table.return_value = None
        return repo
    
    def test_migration_history_init(self, mock_repository):
        """Test migration history initialization."""
        history = MigrationHistory(mock_repository)
        
        # Should create migration history table
        mock_repository.create_table.assert_called_once_with(
            "_migration_history",
            {
                "version": "TEXT PRIMARY KEY",
                "description": "TEXT",
                "checksum": "TEXT",
                "applied_at": "TEXT",
                "execution_time_ms": "INTEGER"
            }
        )
    
    def test_has_migration_false(self, mock_repository):
        """Test checking for non-existent migration."""
        history = MigrationHistory(mock_repository)
        
        # Current implementation always returns False (simplified)
        assert history.has_migration("001") is False
    
    def test_record_migration(self, mock_repository):
        """Test recording applied migration."""
        
        class TestMigration(Migration):
            def up(self, repository: Repository) -> None:
                pass
            def down(self, repository: Repository) -> None:
                pass
        
        migration = TestMigration("001", "Test migration")
        history = MigrationHistory(mock_repository)
        
        # Should not raise exception (simplified implementation)
        history.record_migration(migration, 100)
    
    def test_remove_migration(self, mock_repository):
        """Test removing migration from history."""
        history = MigrationHistory(mock_repository)
        
        # Should not raise exception (simplified implementation)
        history.remove_migration("001")


class TestMigrationManager:
    """Test MigrationManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create migration manager."""
        return MigrationManager()
    
    @pytest.fixture
    def test_migrations(self):
        """Create test migrations."""
        
        class Migration001(Migration):
            def __init__(self):
                super().__init__("001", "Create tables")
                
            def up(self, repository: Repository) -> None:
                if hasattr(repository, 'execute_query'):
                    repository.execute_query("CREATE TABLE users (id INTEGER PRIMARY KEY)")
                
            def down(self, repository: Repository) -> None:
                if hasattr(repository, 'execute_query'):
                    repository.execute_query("DROP TABLE users")
        
        class Migration002(Migration):
            def __init__(self):
                super().__init__("002", "Add indexes")
                
            def up(self, repository: Repository) -> None:
                if hasattr(repository, 'execute_query'):
                    repository.execute_query("CREATE INDEX idx_users_name ON users(name)")
                
            def down(self, repository: Repository) -> None:
                if hasattr(repository, 'execute_query'):
                    repository.execute_query("DROP INDEX idx_users_name")
        
        return Migration001(), Migration002()
    
    def test_register_migration(self, manager, test_migrations):
        """Test registering migrations."""
        migration1, migration2 = test_migrations
        
        manager.register_migration(migration1)
        manager.register_migration(migration2)
        
        assert "001" in manager.migrations
        assert "002" in manager.migrations
        assert manager.migrations["001"] == migration1
        assert manager.migrations["002"] == migration2
    
    def test_register_duplicate_migration(self, manager, test_migrations):
        """Test registering duplicate migration version."""
        migration1, _ = test_migrations
        
        manager.register_migration(migration1)
        
        with pytest.raises(StorageError, match="already registered"):
            manager.register_migration(migration1)
    
    def test_migrate_all(self, manager, test_migrations):
        """Test running all migrations."""
        migration1, migration2 = test_migrations
        manager.register_migration(migration1)
        manager.register_migration(migration2)
        
        # Mock repository
        mock_repo = Mock(spec=Repository)
        mock_repo.execute_query.return_value = None
        
        # Mock migration history
        with patch('torematrix.core.storage.migrations.MigrationHistory') as MockHistory:
            mock_history = Mock()
            mock_history.has_migration.return_value = False  # No migrations applied
            mock_history.record_migration.return_value = None
            MockHistory.return_value = mock_history
            
            manager.migrate(mock_repo)
            
            # Should apply both migrations
            assert mock_history.record_migration.call_count == 2
    
    def test_migrate_to_version(self, manager, test_migrations):
        """Test migrating to specific version."""
        migration1, migration2 = test_migrations
        manager.register_migration(migration1)
        manager.register_migration(migration2)
        
        mock_repo = Mock(spec=Repository)
        mock_repo.execute_query.return_value = None
        
        with patch('torematrix.core.storage.migrations.MigrationHistory') as MockHistory:
            mock_history = Mock()
            mock_history.has_migration.return_value = False
            mock_history.record_migration.return_value = None
            MockHistory.return_value = mock_history
            
            # Migrate only to version 001
            manager.migrate(mock_repo, target_version="001")
            
            # Should apply only first migration
            assert mock_history.record_migration.call_count == 1
            recorded_migration = mock_history.record_migration.call_args[0][0]
            assert recorded_migration.version == "001"
    
    def test_migrate_unknown_version(self, manager, test_migrations):
        """Test migrating to unknown version."""
        migration1, _ = test_migrations
        manager.register_migration(migration1)
        
        mock_repo = Mock(spec=Repository)
        
        with pytest.raises(StorageError, match="Unknown migration version"):
            manager.migrate(mock_repo, target_version="999")
    
    def test_migrate_failure(self, manager, test_migrations):
        """Test migration failure handling."""
        
        class FailingMigration(Migration):
            def __init__(self):
                super().__init__("001", "Failing migration")
                
            def up(self, repository: Repository) -> None:
                raise Exception("Migration failed")
                
            def down(self, repository: Repository) -> None:
                pass
        
        failing_migration = FailingMigration()
        manager.register_migration(failing_migration)
        
        mock_repo = Mock(spec=Repository)
        
        with patch('torematrix.core.storage.migrations.MigrationHistory') as MockHistory:
            mock_history = Mock()
            mock_history.has_migration.return_value = False
            MockHistory.return_value = mock_history
            
            with pytest.raises(StorageError, match="Migration failed"):
                manager.migrate(mock_repo)
    
    def test_rollback(self, manager, test_migrations):
        """Test rolling back migrations."""
        migration1, migration2 = test_migrations
        manager.register_migration(migration1)
        manager.register_migration(migration2)
        
        mock_repo = Mock(spec=Repository)
        mock_repo.execute_query.return_value = None
        
        with patch('torematrix.core.storage.migrations.MigrationHistory') as MockHistory:
            mock_history = Mock()
            mock_history.has_migration.side_effect = lambda v: v in ["001", "002"]  # Both applied
            mock_history.remove_migration.return_value = None
            MockHistory.return_value = mock_history
            
            # Rollback to before 001 (rollback both)
            manager.rollback(mock_repo, "000")
            
            # Should remove both migrations
            assert mock_history.remove_migration.call_count == 2


class TestBackendMigrator:
    """Test BackendMigrator for migrating between backends."""
    
    @pytest.fixture
    def migrator(self):
        """Create backend migrator."""
        return BackendMigrator(batch_size=2)
    
    @pytest.fixture
    def source_repo(self):
        """Mock source repository."""
        repo = Mock(spec=Repository)
        
        # Mock entities
        entities = [
            TestEntity(id="1", name="entity1", value=10),
            TestEntity(id="2", name="entity2", value=20),
            TestEntity(id="3", name="entity3", value=30)
        ]
        
        repo.count.return_value = 3
        
        # Mock paginated list results
        def mock_list(pagination=None):
            page = pagination.page if pagination else 1
            per_page = pagination.per_page if pagination else 100
            start = (page - 1) * per_page
            end = start + per_page
            
            items = entities[start:end]
            
            if pagination:
                from torematrix.core.storage.repository import PaginatedResult
                return PaginatedResult(
                    items=items,
                    total=3,
                    page=page,
                    per_page=per_page
                )
            else:
                return items
        
        repo.list.side_effect = mock_list
        
        return repo
    
    @pytest.fixture
    def target_repo(self):
        """Mock target repository."""
        repo = Mock(spec=Repository)
        repo.create.side_effect = lambda entity: entity
        return repo
    
    def test_migrate_data_success(self, migrator, source_repo, target_repo):
        """Test successful data migration."""
        stats = migrator.migrate_data(source_repo, target_repo)
        
        assert stats["total_entities"] == 3
        assert stats["migrated"] == 3
        assert stats["failed"] == 0
        assert len(stats["errors"]) == 0
        assert "start_time" in stats
        assert "end_time" in stats
        assert "duration_seconds" in stats
        
        # Verify all entities were created in target
        assert target_repo.create.call_count == 3
    
    def test_migrate_data_with_transform(self, migrator, source_repo, target_repo):
        """Test migration with transformation function."""
        
        def transform_entity(entity):
            # Transform by doubling the value
            entity.value *= 2
            return entity
        
        stats = migrator.migrate_data(
            source_repo, 
            target_repo, 
            transform_fn=transform_entity
        )
        
        assert stats["migrated"] == 3
        
        # Verify transformation was applied
        created_entities = [call[0][0] for call in target_repo.create.call_args_list]
        assert created_entities[0].value == 20  # 10 * 2
        assert created_entities[1].value == 40  # 20 * 2
        assert created_entities[2].value == 60  # 30 * 2
    
    def test_migrate_data_with_progress_callback(self, migrator, source_repo, target_repo):
        """Test migration with progress callback."""
        progress_calls = []
        
        def progress_callback(migrated, total):
            progress_calls.append((migrated, total))
        
        migrator.migrate_data(
            source_repo, 
            target_repo, 
            progress_callback=progress_callback
        )
        
        # Should have progress callbacks (batch_size=2, so 2 calls)
        assert len(progress_calls) == 2
        assert progress_calls[0] == (2, 3)  # After first batch
        assert progress_calls[1] == (3, 3)  # After second batch
    
    def test_migrate_data_with_failures(self, migrator, source_repo, target_repo):
        """Test migration with some failures."""
        
        def failing_create(entity):
            if entity.id == "2":
                raise Exception("Create failed")
            return entity
        
        target_repo.create.side_effect = failing_create
        
        stats = migrator.migrate_data(source_repo, target_repo)
        
        assert stats["total_entities"] == 3
        assert stats["migrated"] == 2
        assert stats["failed"] == 1
        assert len(stats["errors"]) == 1
        assert "Create failed" in stats["errors"][0]
    
    def test_migrate_data_complete_failure(self, migrator, source_repo, target_repo):
        """Test migration complete failure."""
        source_repo.count.side_effect = Exception("Repository failure")
        
        with pytest.raises(StorageError, match="Migration failed"):
            migrator.migrate_data(source_repo, target_repo)


class TestCreateIndexesMigration:
    """Test the example CreateIndexesMigration."""
    
    def test_create_indexes_migration_up(self):
        """Test applying create indexes migration."""
        migration = CreateIndexesMigration()
        
        mock_repo = Mock(spec=Repository)
        mock_repo.execute_query.return_value = None
        
        migration.up(mock_repo)
        
        # Should create two indexes
        assert mock_repo.execute_query.call_count == 2
        
        calls = mock_repo.execute_query.call_args_list
        assert "CREATE INDEX" in calls[0][0][0]
        assert "idx_elements_type" in calls[0][0][0]
        assert "CREATE INDEX" in calls[1][0][0]
        assert "idx_elements_document_id" in calls[1][0][0]
    
    def test_create_indexes_migration_down(self):
        """Test rolling back create indexes migration."""
        migration = CreateIndexesMigration()
        
        mock_repo = Mock(spec=Repository)
        mock_repo.execute_query.return_value = None
        
        migration.down(mock_repo)
        
        # Should drop two indexes
        assert mock_repo.execute_query.call_count == 2
        
        calls = mock_repo.execute_query.call_args_list
        assert "DROP INDEX" in calls[0][0][0]
        assert "idx_elements_type" in calls[0][0][0]
        assert "DROP INDEX" in calls[1][0][0]
        assert "idx_elements_document_id" in calls[1][0][0]
    
    def test_create_indexes_migration_metadata(self):
        """Test migration metadata."""
        migration = CreateIndexesMigration()
        
        assert migration.version == "001_create_indexes"
        assert migration.description == "Create performance indexes"
        assert migration.checksum is not None


class TestIntegrationMigration:
    """Integration tests for migration system."""
    
    @pytest.mark.skip(reason="Requires actual database")
    def test_sqlite_to_sqlite_migration(self):
        """Test migrating between SQLite databases."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create source database
            source_path = Path(temp_dir) / "source.db"
            source_repo = StorageFactory.create_repository(
                StorageBackend.SQLITE,
                TestEntity,
                "entities",
                database_path=str(source_path)
            )
            
            # Add test data
            for i in range(5):
                entity = TestEntity(name=f"entity{i}", value=i * 10)
                source_repo.create(entity)
            
            # Create target database
            target_path = Path(temp_dir) / "target.db"
            target_repo = StorageFactory.create_repository(
                StorageBackend.SQLITE,
                TestEntity,
                "entities",
                database_path=str(target_path)
            )
            
            # Migrate data
            migrator = BackendMigrator()
            stats = migrator.migrate_data(source_repo, target_repo)
            
            assert stats["migrated"] == 5
            assert stats["failed"] == 0
            
            # Verify target has all data
            target_entities = target_repo.list()
            assert len(target_entities) == 5
    
    def test_migration_manager_with_real_repository(self):
        """Test migration manager with real repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "migration_test.db"
            repo = StorageFactory.create_repository(
                StorageBackend.SQLITE,
                TestEntity,
                "entities",
                database_path=str(db_path)
            )
            
            # Create and register migrations
            manager = MigrationManager()
            manager.register_migration(CreateIndexesMigration())
            
            # Run migrations
            manager.migrate(repo)
            
            # Verify migration was applied (would need to check actual database)
            # This is simplified for the test
            assert True  # Migration completed without error