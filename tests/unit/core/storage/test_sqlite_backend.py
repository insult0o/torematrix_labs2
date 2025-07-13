"""
Unit tests for SQLite storage backend.
"""

import pytest
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import uuid

from torematrix.core.storage import (
    SQLiteBackend, SQLiteRepository, SQLiteConfig,
    QueryFilter, Pagination, SortOrder,
    StorageError, NotFoundError
)


@dataclass
class TestEntity:
    """Test entity for storage tests."""
    id: Optional[str] = None
    name: str = ""
    value: int = 0
    active: bool = True
    tags: list = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class TestSQLiteBackend:
    """Test SQLite backend functionality."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        # Cleanup
        if db_path.exists():
            db_path.unlink()
    
    @pytest.fixture
    def memory_config(self):
        """In-memory SQLite configuration."""
        return SQLiteConfig(database_path=":memory:")
    
    @pytest.fixture
    def file_config(self, temp_db):
        """File-based SQLite configuration."""
        return SQLiteConfig(database_path=temp_db)
    
    @pytest.fixture
    def backend(self, memory_config):
        """Create SQLite backend instance."""
        return SQLiteBackend(memory_config)
    
    def test_connect_disconnect(self, backend):
        """Test connection lifecycle."""
        # Should connect automatically
        assert backend.is_connected()
        
        # Explicit disconnect
        backend.disconnect()
        assert not backend.is_connected()
        
        # Reconnect
        backend.connect()
        assert backend.is_connected()
    
    def test_create_table(self, backend):
        """Test table creation."""
        schema = {
            "id": "TEXT PRIMARY KEY",
            "name": "TEXT NOT NULL",
            "value": "INTEGER DEFAULT 0"
        }
        
        backend.create_table("test_table", schema)
        
        # Verify table exists
        cursor = backend.connection.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
        )
        result = cursor.fetchone()
        assert result is not None
        cursor.close()
    
    def test_transaction(self, backend):
        """Test transaction management."""
        backend.create_table("test_trans", {"id": "INTEGER PRIMARY KEY", "data": "TEXT"})
        
        # Successful transaction
        with backend.transaction():
            backend.execute_query("INSERT INTO test_trans (data) VALUES (?)", ["test1"])
            backend.execute_query("INSERT INTO test_trans (data) VALUES (?)", ["test2"])
        
        # Verify data was committed
        result = backend.execute_query("SELECT COUNT(*) as count FROM test_trans", fetch_one=True)
        assert result['count'] == 2
        
        # Failed transaction (should rollback)
        with pytest.raises(Exception):
            with backend.transaction():
                backend.execute_query("INSERT INTO test_trans (data) VALUES (?)", ["test3"])
                # Force error
                backend.execute_query("INVALID SQL")
        
        # Verify rollback
        result = backend.execute_query("SELECT COUNT(*) as count FROM test_trans", fetch_one=True)
        assert result['count'] == 2  # Still 2, not 3
    
    def test_file_persistence(self, file_config):
        """Test that data persists in file-based database."""
        # Create and populate database
        backend1 = SQLiteBackend(file_config)
        backend1.create_table("persist_test", {"id": "INTEGER PRIMARY KEY", "data": "TEXT"})
        backend1.execute_query("INSERT INTO persist_test (data) VALUES (?)", ["persistent"])
        backend1.disconnect()
        
        # Open again and verify data
        backend2 = SQLiteBackend(file_config)
        result = backend2.execute_query(
            "SELECT data FROM persist_test WHERE data = ?", 
            ["persistent"], 
            fetch_one=True
        )
        assert result is not None
        assert result['data'] == "persistent"
        backend2.disconnect()


class TestSQLiteRepository:
    """Test SQLite repository implementation."""
    
    @pytest.fixture
    def repository(self):
        """Create test repository."""
        config = SQLiteConfig(database_path=":memory:")
        return SQLiteRepository(config, TestEntity, "test_entities")
    
    def test_create_entity(self, repository):
        """Test entity creation."""
        entity = TestEntity(name="Test", value=42)
        created = repository.create(entity)
        
        assert created.id is not None
        assert created.name == "Test"
        assert created.value == 42
        
        # Verify in database
        retrieved = repository.get(created.id)
        assert retrieved is not None
        assert retrieved.name == "Test"
    
    def test_get_entity(self, repository):
        """Test entity retrieval."""
        # Create entity
        entity = TestEntity(name="GetTest", value=100)
        created = repository.create(entity)
        
        # Get by ID
        retrieved = repository.get(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "GetTest"
        assert retrieved.value == 100
        
        # Get non-existent
        assert repository.get("non-existent-id") is None
    
    def test_update_entity(self, repository):
        """Test entity update."""
        # Create entity
        entity = TestEntity(name="Original", value=1)
        created = repository.create(entity)
        
        # Update
        created.name = "Updated"
        created.value = 2
        updated = repository.update(created)
        
        # Verify update
        retrieved = repository.get(created.id)
        assert retrieved.name == "Updated"
        assert retrieved.value == 2
        
        # Update non-existent should fail
        fake_entity = TestEntity(id="fake-id", name="Fake")
        with pytest.raises(NotFoundError):
            repository.update(fake_entity)
    
    def test_delete_entity(self, repository):
        """Test entity deletion."""
        # Create entity
        entity = TestEntity(name="ToDelete")
        created = repository.create(entity)
        
        # Delete
        assert repository.delete(created.id) is True
        
        # Verify deleted
        assert repository.get(created.id) is None
        assert repository.exists(created.id) is False
        
        # Delete non-existent
        assert repository.delete("non-existent") is False
    
    def test_list_entities(self, repository):
        """Test entity listing."""
        # Create multiple entities
        for i in range(5):
            repository.create(TestEntity(name=f"Entity{i}", value=i))
        
        # List all
        all_entities = repository.list()
        assert len(all_entities) == 5
        
        # List with pagination
        page1 = repository.list(pagination=Pagination(page=1, per_page=2))
        assert len(page1.items) == 2
        assert page1.total == 5
        assert page1.pages == 3
        assert page1.has_next is True
        
        page2 = repository.list(pagination=Pagination(page=2, per_page=2))
        assert len(page2.items) == 2
        assert page2.has_prev is True
        assert page2.has_next is True
        
        # List with sorting
        sorted_asc = repository.list(sort_by="value", sort_order=SortOrder.ASC)
        assert sorted_asc[0].value == 0
        assert sorted_asc[-1].value == 4
    
    def test_bulk_operations(self, repository):
        """Test bulk create, update, delete."""
        # Bulk create
        entities = [
            TestEntity(name=f"Bulk{i}", value=i) 
            for i in range(3)
        ]
        created = repository.bulk_create(entities)
        assert len(created) == 3
        assert all(e.id is not None for e in created)
        
        # Bulk update
        for e in created:
            e.value *= 10
        updated = repository.bulk_update(created)
        assert updated[0].value == 0
        assert updated[1].value == 10
        assert updated[2].value == 20
        
        # Bulk delete
        ids = [e.id for e in created]
        deleted_count = repository.bulk_delete(ids)
        assert deleted_count == 3
        
        # Verify all deleted
        assert repository.count() == 0
    
    def test_search(self, repository):
        """Test search functionality."""
        # Create searchable entities
        repository.create(TestEntity(name="Apple Pie", value=1))
        repository.create(TestEntity(name="Apple Juice", value=2))
        repository.create(TestEntity(name="Orange Juice", value=3))
        repository.create(TestEntity(name="Banana Split", value=4))
        
        # Search
        apple_results = repository.search("Apple")
        assert len(apple_results) == 2
        
        juice_results = repository.search("Juice")
        assert len(juice_results) == 2
        
        # Search with pagination
        paged_results = repository.search(
            "e",  # Should match all (Apple, Orange, Juice)
            pagination=Pagination(page=1, per_page=2)
        )
        assert len(paged_results.items) == 2
        assert paged_results.total == 4
    
    def test_count_and_exists(self, repository):
        """Test count and exists methods."""
        # Empty repository
        assert repository.count() == 0
        
        # Add entities
        e1 = repository.create(TestEntity(name="One"))
        e2 = repository.create(TestEntity(name="Two"))
        
        # Count
        assert repository.count() == 2
        
        # Exists
        assert repository.exists(e1.id) is True
        assert repository.exists(e2.id) is True
        assert repository.exists("fake-id") is False
    
    def test_error_handling(self, repository):
        """Test error handling."""
        # Invalid ID format
        assert repository.get("") is None
        assert repository.get(None) is None
        
        # Create without required fields (if any)
        # Update without ID
        entity_no_id = TestEntity(name="NoId")
        with pytest.raises(StorageError):
            repository.update(entity_no_id)