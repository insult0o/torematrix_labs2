"""
Unit tests for PostgreSQL storage backend.
"""

import pytest
import json
from dataclasses import dataclass
from typing import Optional
from unittest.mock import Mock, patch, MagicMock
import psycopg2
from psycopg2.extras import RealDictCursor

from torematrix.core.storage import (
    PostgreSQLBackend, PostgreSQLRepository, PostgreSQLConfig,
    QueryFilter, Pagination, SortOrder,
    StorageError, NotFoundError, TransactionError
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


class TestPostgreSQLBackend:
    """Test PostgreSQL backend functionality."""
    
    @pytest.fixture
    def config(self):
        """PostgreSQL configuration for testing."""
        return PostgreSQLConfig(
            host="localhost",
            port=5432,
            database="test_torematrix",
            user="test_user",
            password="test_pass"
        )
    
    @pytest.fixture
    def mock_connection(self):
        """Mock PostgreSQL connection."""
        connection = Mock()
        cursor = Mock()
        cursor.fetchone.return_value = None
        cursor.fetchall.return_value = []
        cursor.execute.return_value = None
        cursor.__enter__ = Mock(return_value=cursor)
        cursor.__exit__ = Mock(return_value=False)
        
        connection.cursor.return_value = cursor
        connection.commit.return_value = None
        connection.rollback.return_value = None
        connection.close.return_value = None
        connection.autocommit = True
        
        return connection, cursor
    
    @pytest.fixture
    def backend(self, config, mock_connection):
        """Create PostgreSQL backend with mocked connection."""
        connection, cursor = mock_connection
        
        backend = PostgreSQLBackend(config)
        
        # Mock the connection property
        with patch.object(PostgreSQLBackend, 'connection', new=connection):
            yield backend, connection, cursor
    
    def test_config_connection_string(self, config):
        """Test PostgreSQL connection string generation."""
        conn_str = config.get_connection_string()
        expected = (
            "postgresql://test_user:test_pass@localhost:5432/test_torematrix"
            "?sslmode=prefer&application_name=torematrix_v3"
        )
        assert conn_str == expected
    
    def test_config_with_connection_string(self):
        """Test config with explicit connection string."""
        config = PostgreSQLConfig(
            connection_string="postgresql://custom:pass@host:1234/db"
        )
        assert config.get_connection_string() == "postgresql://custom:pass@host:1234/db"
    
    @patch('torematrix.core.storage.postgres_backend.psycopg2.connect')
    def test_connect_success(self, mock_connect, config):
        """Test successful connection."""
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        mock_connection.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_connection
        
        backend = PostgreSQLBackend(config)
        backend.connect()
        
        # Verify connection was attempted
        mock_connect.assert_called_once()
        call_args = mock_connect.call_args
        assert "postgresql://test_user:test_pass@localhost:5432/test_torematrix" in call_args[0][0]
        assert call_args[1]['cursor_factory'] == RealDictCursor
        
        # Verify initial setup queries
        expected_queries = [
            "SET search_path TO public",
            "SET timezone TO 'UTC'",
            "SET statement_timeout TO '30s'"
        ]
        actual_calls = [call[0][0] for call in mock_cursor.execute.call_args_list]
        for query in expected_queries:
            assert query in actual_calls
    
    @patch('torematrix.core.storage.postgres_backend.psycopg2.connect')
    def test_connect_failure(self, mock_connect, config):
        """Test connection failure handling."""
        mock_connect.side_effect = psycopg2.OperationalError("Connection failed")
        
        backend = PostgreSQLBackend(config)
        
        with pytest.raises(StorageError):
            backend.connect()
    
    def test_create_table(self, backend):
        """Test table creation."""
        backend, connection, cursor = backend
        
        schema = {
            "id": "TEXT PRIMARY KEY",
            "name": "TEXT NOT NULL",
            "value": "INTEGER DEFAULT 0"
        }
        
        backend.create_table("test_table", schema)
        
        # Verify CREATE TABLE was called
        calls = cursor.execute.call_args_list
        create_call = next((call for call in calls if "CREATE TABLE" in call[0][0]), None)
        assert create_call is not None
        
        create_sql = create_call[0][0]
        assert "test_table" in create_sql
        assert "id TEXT PRIMARY KEY" in create_sql
        assert "name TEXT NOT NULL" in create_sql
        assert "data JSONB" in create_sql  # Should add JSONB column
        
        # Verify indexes were created
        index_calls = [call for call in calls if "CREATE INDEX" in call[0][0]]
        assert len(index_calls) >= 3  # created_at, updated_at, data_gin
    
    def test_build_where_clause(self, backend):
        """Test WHERE clause building with JSONB operations."""
        backend, connection, cursor = backend
        
        filters = [
            QueryFilter("name", "eq", "test"),
            QueryFilter("value", "gt", 10),
            QueryFilter("active", "in", [True, False])
        ]
        
        where_clause, params = backend._build_where_clause(filters, "test_table")
        
        assert "WHERE" in where_clause
        assert "data->>%s = %s" in where_clause  # eq operation
        assert "(data->>%s)::numeric > %s" in where_clause  # gt operation
        assert "data->>%s IN (%s,%s)" in where_clause  # in operation
        
        assert params == ["name", "test", "value", 10, "active", True, False]
    
    def test_transaction_success(self, backend):
        """Test successful transaction."""
        backend, connection, cursor = backend
        
        with backend.transaction():
            # Transaction should set autocommit=False
            assert connection.autocommit == False
            
        # After transaction, should commit and restore autocommit
        connection.commit.assert_called_once()
        assert connection.autocommit == True
    
    def test_transaction_failure(self, backend):
        """Test transaction rollback on failure."""
        backend, connection, cursor = backend
        
        with pytest.raises(TransactionError):
            with backend.transaction():
                raise Exception("Test error")
        
        # Should rollback on exception
        connection.rollback.assert_called_once()
        assert connection.autocommit == True
    
    def test_execute_query_select(self, backend):
        """Test query execution for SELECT."""
        backend, connection, cursor = backend
        
        # Mock return data
        cursor.fetchall.return_value = [
            {"id": "1", "name": "test1"},
            {"id": "2", "name": "test2"}
        ]
        
        result = backend.execute_query("SELECT * FROM test_table")
        
        cursor.execute.assert_called_with("SELECT * FROM test_table", [])
        assert len(result) == 2
        assert result[0]["name"] == "test1"
    
    def test_execute_query_insert(self, backend):
        """Test query execution for INSERT."""
        backend, connection, cursor = backend
        
        result = backend.execute_query(
            "INSERT INTO test_table (name) VALUES (%s)", 
            ["test"]
        )
        
        cursor.execute.assert_called_with(
            "INSERT INTO test_table (name) VALUES (%s)", 
            ["test"]
        )
        assert result is None  # Non-SELECT queries return None
    
    def test_get_statistics(self, backend):
        """Test statistics collection."""
        backend, connection, cursor = backend
        
        # Mock database stats
        cursor.fetchone.side_effect = [
            {"db_size": "10 MB"},  # Database size query
            {"count": 100}         # Table count query
        ]
        cursor.fetchall.return_value = [
            {
                "schemaname": "public",
                "tablename": "test_table",
                "n_tup_ins": 50,
                "n_tup_upd": 10,
                "n_tup_del": 5
            }
        ]
        
        # Mock is_connected
        with patch.object(backend, 'is_connected', return_value=True):
            stats = backend.get_statistics()
        
        assert stats["backend"] == "PostgreSQLBackend"
        assert stats["database_size"] == "10 MB"
        assert "tables" in stats
        assert stats["tables"]["test_table"]["row_count"] == 100


class TestPostgreSQLRepository:
    """Test PostgreSQL repository implementation."""
    
    @pytest.fixture
    def mock_backend(self):
        """Mock PostgreSQL backend for repository testing."""
        backend = Mock(spec=PostgreSQLBackend)
        backend.execute_query.return_value = None
        backend.create_table.return_value = None
        backend.generate_id.return_value = "test-id-123"
        backend.validate_id.return_value = True
        backend.serialize_entity.return_value = {"name": "test", "value": 42}
        backend.add_timestamps.return_value = {
            "name": "test", 
            "value": 42,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
        backend.deserialize_entity.return_value = TestEntity(
            id="test-id-123", 
            name="test", 
            value=42
        )
        backend._build_where_clause.return_value = ("", [])
        
        # Mock transaction context manager
        transaction_mock = Mock()
        transaction_mock.__enter__ = Mock(return_value=None)
        transaction_mock.__exit__ = Mock(return_value=False)
        backend.transaction.return_value = transaction_mock
        
        return backend
    
    @pytest.fixture
    def repository(self, mock_backend):
        """Create repository with mocked backend."""
        config = PostgreSQLConfig(database="test")
        
        with patch('torematrix.core.storage.postgres_backend.PostgreSQLBackend') as MockBackend:
            MockBackend.return_value = mock_backend
            repo = PostgreSQLRepository(config, TestEntity, "test_entities")
            
            # Replace backend methods with mock
            for attr_name in dir(mock_backend):
                if not attr_name.startswith('_') and callable(getattr(mock_backend, attr_name)):
                    setattr(repo, attr_name, getattr(mock_backend, attr_name))
            
            return repo, mock_backend
    
    def test_create_entity(self, repository):
        """Test entity creation."""
        repo, mock_backend = repository
        
        entity = TestEntity(name="test", value=42)
        
        # Mock execute_query for INSERT
        mock_backend.execute_query.return_value = None
        
        created = repo.create(entity)
        
        assert created.id == "test-id-123"
        assert created.name == "test"
        assert created.value == 42
        
        # Verify INSERT query was called
        mock_backend.execute_query.assert_called()
        call_args = mock_backend.execute_query.call_args
        assert "INSERT INTO test_entities" in call_args[0][0]
        assert "VALUES (%s, %s, %s, %s)" in call_args[0][0]
    
    def test_get_entity(self, repository):
        """Test entity retrieval."""
        repo, mock_backend = repository
        
        # Mock database response
        mock_backend.execute_query.return_value = {
            "data": '{"id": "test-id", "name": "test", "value": 42}'
        }
        
        entity = repo.get("test-id")
        
        assert entity is not None
        assert entity.id == "test-id-123"
        assert entity.name == "test"
        
        # Verify SELECT query
        mock_backend.execute_query.assert_called_with(
            "SELECT data FROM test_entities WHERE id = %s",
            ["test-id"],
            fetch_one=True
        )
    
    def test_get_entity_not_found(self, repository):
        """Test getting non-existent entity."""
        repo, mock_backend = repository
        
        mock_backend.execute_query.return_value = None
        
        entity = repo.get("non-existent")
        
        assert entity is None
    
    def test_update_entity(self, repository):
        """Test entity update."""
        repo, mock_backend = repository
        
        entity = TestEntity(id="test-id", name="updated", value=100)
        
        # Mock exists check
        mock_backend.exists.return_value = True
        mock_backend.execute_query.return_value = None
        
        updated = repo.update(entity)
        
        assert updated.name == "updated"
        assert updated.value == 100
        
        # Verify UPDATE query
        mock_backend.execute_query.assert_called()
        call_args = mock_backend.execute_query.call_args
        assert "UPDATE test_entities" in call_args[0][0]
        assert "_version = _version + 1" in call_args[0][0]
    
    def test_update_entity_not_found(self, repository):
        """Test updating non-existent entity."""
        repo, mock_backend = repository
        
        entity = TestEntity(id="non-existent", name="test")
        mock_backend.exists.return_value = False
        
        with pytest.raises(NotFoundError):
            repo.update(entity)
    
    def test_delete_entity(self, repository):
        """Test entity deletion."""
        repo, mock_backend = repository
        
        mock_backend.execute_query.return_value = None
        mock_backend.exists.side_effect = [True, False]  # Exists before, not after
        
        result = repo.delete("test-id")
        
        assert result is True
        
        # Verify DELETE query
        mock_backend.execute_query.assert_called_with(
            "DELETE FROM test_entities WHERE id = %s",
            ["test-id"]
        )
    
    def test_list_entities_with_pagination(self, repository):
        """Test listing entities with pagination."""
        repo, mock_backend = repository
        
        # Mock count query
        count_result = {"total": 10}
        # Mock data query
        data_results = [
            {"data": '{"id": "1", "name": "test1"}'},
            {"data": '{"id": "2", "name": "test2"}'}
        ]
        
        mock_backend.execute_query.side_effect = [count_result, data_results]
        mock_backend._build_where_clause.return_value = ("", [])
        
        pagination = Pagination(page=1, per_page=2)
        result = repo.list(pagination=pagination)
        
        assert result.total == 10
        assert result.page == 1
        assert result.per_page == 2
        assert len(result.items) == 2
    
    def test_bulk_create(self, repository):
        """Test bulk entity creation."""
        repo, mock_backend = repository
        
        entities = [
            TestEntity(name="test1", value=1),
            TestEntity(name="test2", value=2),
            TestEntity(name="test3", value=3)
        ]
        
        # Mock individual creates
        def mock_create(entity):
            entity.id = f"id-{entity.value}"
            return entity
        
        repo.create = Mock(side_effect=mock_create)
        
        created = repo.bulk_create(entities)
        
        assert len(created) == 3
        assert created[0].id == "id-1"
        assert created[1].id == "id-2"
        assert created[2].id == "id-3"
        
        # Verify transaction was used
        mock_backend.transaction.assert_called_once()
    
    def test_bulk_delete_optimized(self, repository):
        """Test optimized bulk delete."""
        repo, mock_backend = repository
        
        entity_ids = ["id1", "id2", "id3"]
        
        # Mock cursor for rowcount
        mock_cursor = Mock()
        mock_cursor.rowcount = 3
        mock_cursor.execute.return_value = None
        mock_cursor.__enter__ = Mock(return_value=mock_cursor)
        mock_cursor.__exit__ = Mock(return_value=False)
        
        # Mock connection
        mock_connection = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_backend.connection = mock_connection
        
        deleted_count = repo.bulk_delete(entity_ids)
        
        assert deleted_count == 3
        
        # Verify single DELETE query with IN clause
        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "DELETE FROM test_entities WHERE id IN (%s,%s,%s)" in call_args[0][0]
        assert call_args[0][1] == entity_ids
    
    def test_search_entities(self, repository):
        """Test full-text search."""
        repo, mock_backend = repository
        
        # Mock search results
        search_results = [
            {"data": '{"id": "1", "name": "apple pie"}'},
            {"data": '{"id": "2", "name": "apple juice"}'}
        ]
        
        mock_backend.execute_query.return_value = search_results
        
        results = repo.search("apple")
        
        assert len(results) == 2
        
        # Verify search query
        mock_backend.execute_query.assert_called()
        call_args = mock_backend.execute_query.call_args
        assert "WHERE data::text ILIKE %s" in call_args[0][0]
        assert call_args[0][1] == ["%apple%"]
    
    def test_count_entities(self, repository):
        """Test entity counting."""
        repo, mock_backend = repository
        
        mock_backend.execute_query.return_value = {"total": 42}
        mock_backend._build_where_clause.return_value = ("", [])
        
        count = repo.count()
        
        assert count == 42
        
        # Verify COUNT query
        mock_backend.execute_query.assert_called_with(
            "SELECT COUNT(*) as total FROM test_entities",
            [],
            fetch_one=True
        )
    
    def test_exists(self, repository):
        """Test entity existence check."""
        repo, mock_backend = repository
        
        mock_backend.execute_query.return_value = {"exists": 1}
        
        exists = repo.exists("test-id")
        
        assert exists is True
        
        # Verify EXISTS query
        mock_backend.execute_query.assert_called_with(
            "SELECT 1 FROM test_entities WHERE id = %s LIMIT 1",
            ["test-id"],
            fetch_one=True
        )


class TestPostgreSQLIntegration:
    """Integration tests that would require actual PostgreSQL."""
    
    @pytest.mark.skip(reason="Requires PostgreSQL instance")
    def test_real_postgres_connection(self):
        """Test with real PostgreSQL connection."""
        config = PostgreSQLConfig(
            host="localhost",
            database="test_db",
            user="test_user",
            password="test_pass"
        )
        
        backend = PostgreSQLBackend(config)
        backend.connect()
        
        # Test basic operations
        backend.create_table("test_table", {"id": "TEXT PRIMARY KEY"})
        
        # Cleanup
        backend.disconnect()
    
    @pytest.mark.skip(reason="Requires PostgreSQL instance") 
    def test_real_repository_operations(self):
        """Test repository with real PostgreSQL."""
        config = PostgreSQLConfig(
            host="localhost",
            database="test_db",
            user="test_user",
            password="test_pass"
        )
        
        repo = PostgreSQLRepository(config, TestEntity, "test_entities")
        
        # Test CRUD operations
        entity = TestEntity(name="integration_test", value=999)
        created = repo.create(entity)
        
        retrieved = repo.get(created.id)
        assert retrieved.name == "integration_test"
        
        # Cleanup
        repo.delete(created.id)