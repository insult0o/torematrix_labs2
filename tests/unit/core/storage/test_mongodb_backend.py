"""
Unit tests for MongoDB storage backend.
"""

import pytest
from dataclasses import dataclass
from typing import Optional
from unittest.mock import Mock, patch, MagicMock
import pymongo
from pymongo import MongoClient, ASCENDING, DESCENDING

from torematrix.core.storage import (
    MongoDBBackend, MongoDBRepository, MongoDBConfig,
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


class TestMongoDBBackend:
    """Test MongoDB backend functionality."""
    
    @pytest.fixture
    def config(self):
        """MongoDB configuration for testing."""
        return MongoDBConfig(
            connection_string="mongodb://localhost:27017/",
            database="test_torematrix"
        )
    
    @pytest.fixture
    def mock_client(self):
        """Mock MongoDB client and database."""
        client = Mock(spec=MongoClient)
        database = Mock()
        collection = Mock()
        
        # Setup client
        client.__getitem__.return_value = database
        client.admin.command.return_value = {"ok": 1}  # ping response
        client.close.return_value = None
        
        # Setup database
        database.__getitem__.return_value = collection
        database.list_collection_names.return_value = []
        database.create_collection.return_value = collection
        database.command.return_value = {
            "dataSize": 1024 * 1024,
            "storageSize": 2 * 1024 * 1024,
            "indexSize": 512 * 1024,
            "collections": 5,
            "indexes": 10
        }
        
        # Setup collection
        collection.create_index.return_value = None
        collection.insert_one.return_value = Mock(inserted_id="test-id")
        collection.find_one.return_value = None
        collection.find.return_value = Mock()
        collection.update_one.return_value = Mock(matched_count=1)
        collection.delete_one.return_value = Mock(deleted_count=1)
        collection.count_documents.return_value = 0
        
        return client, database, collection
    
    @pytest.fixture
    def backend(self, config, mock_client):
        """Create MongoDB backend with mocked client."""
        client, database, collection = mock_client
        
        with patch('torematrix.core.storage.mongodb_backend.MongoClient') as MockClient:
            MockClient.return_value = client
            backend = MongoDBBackend(config)
            
            yield backend, client, database, collection
    
    def test_config_defaults(self):
        """Test MongoDB configuration defaults."""
        config = MongoDBConfig()
        assert config.connection_string == "mongodb://localhost:27017/"
        assert config.database == "torematrix"
        assert config.write_concern == "majority"
        assert config.read_preference == "primary"
    
    def test_config_custom_values(self):
        """Test MongoDB configuration with custom values."""
        config = MongoDBConfig(
            connection_string="mongodb://user:pass@host:27018/",
            database="custom_db",
            write_concern="1",
            read_preference="secondary",
            max_pool_size=50
        )
        
        assert config.connection_string == "mongodb://user:pass@host:27018/"
        assert config.database == "custom_db"
        assert config.write_concern == "1"
        assert config.read_preference == "secondary"
        assert config.max_pool_size == 50
    
    def test_connect_success(self, backend):
        """Test successful MongoDB connection."""
        backend, client, database, collection = backend
        
        # Connection should be established during backend creation
        client.admin.command.assert_called_with('ping')
        assert backend.is_connected() is True
    
    def test_connect_failure(self, config):
        """Test MongoDB connection failure."""
        with patch('torematrix.core.storage.mongodb_backend.MongoClient') as MockClient:
            MockClient.side_effect = pymongo.errors.ServerSelectionTimeoutError("Connection failed")
            
            with pytest.raises(StorageError):
                MongoDBBackend(config)
    
    def test_disconnect(self, backend):
        """Test MongoDB disconnection."""
        backend, client, database, collection = backend
        
        backend.disconnect()
        
        client.close.assert_called_once()
        assert backend._client is None
        assert backend._database is None
    
    def test_is_connected(self, backend):
        """Test connection status check."""
        backend, client, database, collection = backend
        
        # Initially connected
        assert backend.is_connected() is True
        
        # Simulate connection failure
        client.admin.command.side_effect = pymongo.errors.ServerSelectionTimeoutError("Disconnected")
        assert backend.is_connected() is False
    
    def test_create_collection_new(self, backend):
        """Test creating new collection."""
        backend, client, database, collection = backend
        
        # Mock collection doesn't exist
        database.list_collection_names.return_value = []
        
        created_collection = backend.create_collection("test_collection")
        
        database.create_collection.assert_called_once_with("test_collection")
        collection.create_index.assert_any_call("created_at")
        collection.create_index.assert_any_call("updated_at")
        
        assert created_collection == collection
    
    def test_create_collection_exists(self, backend):
        """Test getting existing collection."""
        backend, client, database, collection = backend
        
        # Mock collection exists
        database.list_collection_names.return_value = ["test_collection"]
        
        existing_collection = backend.create_collection("test_collection")
        
        database.create_collection.assert_not_called()
        assert existing_collection == collection
    
    def test_create_collection_with_schema(self, backend):
        """Test creating collection with JSON schema validation."""
        backend, client, database, collection = backend
        
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"}
            }
        }
        
        database.list_collection_names.return_value = []
        
        backend.create_collection("test_collection", schema)
        
        database.create_collection.assert_called_once_with(
            "test_collection",
            validator={"$jsonSchema": schema},
            validationLevel="moderate"
        )
    
    def test_build_filter_simple(self, backend):
        """Test building simple MongoDB filters."""
        backend, client, database, collection = backend
        
        filters = [
            QueryFilter("name", "eq", "test"),
            QueryFilter("value", "gt", 10),
            QueryFilter("active", "ne", True)
        ]
        
        mongo_filter = backend._build_filter(filters)
        
        expected = {
            "name": "test",
            "value": {"$gt": 10},
            "active": {"$ne": True}
        }
        
        assert mongo_filter == expected
    
    def test_build_filter_complex(self, backend):
        """Test building complex MongoDB filters."""
        backend, client, database, collection = backend
        
        filters = [
            QueryFilter("status", "in", ["active", "pending"]),
            QueryFilter("name", "like", "test%"),
            QueryFilter("description", "contains", "important"),
            QueryFilter("score", "gte", 50),
            QueryFilter("priority", "lte", 5)
        ]
        
        mongo_filter = backend._build_filter(filters)
        
        expected = {
            "status": {"$in": ["active", "pending"]},
            "name": {"$regex": "test.*", "$options": "i"},
            "description": {"$regex": "important", "$options": "i"},
            "score": {"$gte": 50},
            "priority": {"$lte": 5}
        }
        
        assert mongo_filter == expected
    
    def test_build_filter_empty(self, backend):
        """Test building filter with no filters."""
        backend, client, database, collection = backend
        
        mongo_filter = backend._build_filter(None)
        assert mongo_filter == {}
        
        mongo_filter = backend._build_filter([])
        assert mongo_filter == {}
    
    def test_build_filter_unsupported_operator(self, backend):
        """Test building filter with unsupported operator."""
        backend, client, database, collection = backend
        
        filters = [QueryFilter("field", "unsupported", "value")]
        
        with pytest.raises(StorageError, match="Unsupported operator"):
            backend._build_filter(filters)
    
    def test_transaction_success(self, backend):
        """Test successful MongoDB transaction."""
        backend, client, database, collection = backend
        
        # Mock session
        mock_session = Mock()
        mock_session.start_transaction.return_value.__enter__ = Mock()
        mock_session.start_transaction.return_value.__exit__ = Mock(return_value=False)
        mock_session.end_session.return_value = None
        client.start_session.return_value = mock_session
        
        with backend.transaction() as session:
            assert session == mock_session
            assert backend._in_transaction is True
        
        mock_session.start_transaction.assert_called_once()
        mock_session.end_session.assert_called_once()
        assert backend._in_transaction is False
    
    def test_transaction_failure(self, backend):
        """Test MongoDB transaction failure and rollback."""
        backend, client, database, collection = backend
        
        # Mock session
        mock_session = Mock()
        mock_session.start_transaction.return_value.__enter__ = Mock(side_effect=Exception("Test error"))
        mock_session.start_transaction.return_value.__exit__ = Mock(return_value=False)
        mock_session.end_session.return_value = None
        client.start_session.return_value = mock_session
        
        with pytest.raises(TransactionError):
            with backend.transaction():
                pass
        
        mock_session.end_session.assert_called_once()
        assert backend._in_transaction is False
    
    def test_create_text_index(self, backend):
        """Test creating text index for full-text search."""
        backend, client, database, collection = backend
        
        fields = ["name", "description"]
        
        backend.create_text_index("test_collection", fields)
        
        expected_index_spec = [("name", pymongo.TEXT), ("description", pymongo.TEXT)]
        collection.create_index.assert_called_with(
            expected_index_spec,
            name="test_collection_text_index"
        )
    
    def test_create_compound_index(self, backend):
        """Test creating compound index."""
        backend, client, database, collection = backend
        
        fields = [("name", ASCENDING), ("created_at", DESCENDING)]
        
        backend.create_compound_index("test_collection", fields)
        
        collection.create_index.assert_called_with(fields)
    
    def test_get_statistics(self, backend):
        """Test getting MongoDB statistics."""
        backend, client, database, collection = backend
        
        # Mock database stats
        database.command.side_effect = [
            {  # dbStats
                "dataSize": 1024 * 1024,
                "storageSize": 2 * 1024 * 1024,
                "indexSize": 512 * 1024,
                "collections": 5,
                "indexes": 10
            },
            {  # collStats for test_collection
                "count": 100,
                "size": 50 * 1024,
                "avgObjSize": 512,
                "nindexes": 3
            }
        ]
        database.list_collection_names.return_value = ["test_collection"]
        
        stats = backend.get_statistics()
        
        assert stats["backend"] == "MongoDBBackend"
        assert stats["database_size_mb"] == 1.0
        assert stats["storage_size_mb"] == 2.0
        assert stats["index_size_mb"] == 0.5
        assert stats["collections"] == 5
        assert stats["indexes"] == 10
        
        assert "collections_details" in stats
        assert stats["collections_details"]["test_collection"]["documents"] == 100


class TestMongoDBRepository:
    """Test MongoDB repository implementation."""
    
    @pytest.fixture
    def mock_backend(self):
        """Mock MongoDB backend for repository testing."""
        backend = Mock(spec=MongoDBBackend)
        collection = Mock()
        
        # Setup backend
        backend.create_collection.return_value = collection
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
        backend._build_filter.return_value = {}
        backend._session = None
        
        # Mock transaction context manager
        transaction_mock = Mock()
        transaction_mock.__enter__ = Mock(return_value=None)
        transaction_mock.__exit__ = Mock(return_value=False)
        backend.transaction.return_value = transaction_mock
        
        return backend, collection
    
    @pytest.fixture
    def repository(self, mock_backend):
        """Create repository with mocked backend."""
        mock_backend_obj, collection = mock_backend
        config = MongoDBConfig(database="test")
        
        with patch('torematrix.core.storage.mongodb_backend.MongoDBBackend') as MockBackend:
            MockBackend.return_value = mock_backend_obj
            repo = MongoDBRepository(config, TestEntity, "test_entities")
            
            # Replace backend methods with mock
            for attr_name in dir(mock_backend_obj):
                if not attr_name.startswith('_') and callable(getattr(mock_backend_obj, attr_name)):
                    setattr(repo, attr_name, getattr(mock_backend_obj, attr_name))
            
            repo._collection = collection
            
            return repo, mock_backend_obj, collection
    
    def test_create_entity(self, repository):
        """Test entity creation."""
        repo, mock_backend, collection = repository
        
        entity = TestEntity(name="test", value=42)
        
        # Mock insert_one
        collection.insert_one.return_value = Mock(inserted_id="test-id-123")
        
        created = repo.create(entity)
        
        assert created.id == "test-id-123"
        assert created.name == "test"
        assert created.value == 42
        
        # Verify insert_one was called
        collection.insert_one.assert_called_once()
        insert_data = collection.insert_one.call_args[0][0]
        assert insert_data["_id"] == "test-id-123"
        assert insert_data["name"] == "test"
        assert insert_data["value"] == 42
    
    def test_create_entity_with_session(self, repository):
        """Test entity creation within transaction."""
        repo, mock_backend, collection = repository
        
        entity = TestEntity(name="test", value=42)
        
        # Mock session
        mock_session = Mock()
        repo._session = mock_session
        
        created = repo.create(entity)
        
        # Verify insert_one was called with session
        collection.insert_one.assert_called()
        call_kwargs = collection.insert_one.call_args[1]
        assert call_kwargs["session"] == mock_session
    
    def test_get_entity(self, repository):
        """Test entity retrieval."""
        repo, mock_backend, collection = repository
        
        # Mock find_one response
        collection.find_one.return_value = {
            "_id": "test-id",
            "name": "test",
            "value": 42,
            "created_at": "2024-01-01T00:00:00"
        }
        
        entity = repo.get("test-id")
        
        assert entity is not None
        assert entity.id == "test-id-123"
        assert entity.name == "test"
        
        # Verify find_one query
        collection.find_one.assert_called_with({"_id": "test-id"})
    
    def test_get_entity_not_found(self, repository):
        """Test getting non-existent entity."""
        repo, mock_backend, collection = repository
        
        collection.find_one.return_value = None
        
        entity = repo.get("non-existent")
        
        assert entity is None
    
    def test_update_entity(self, repository):
        """Test entity update."""
        repo, mock_backend, collection = repository
        
        entity = TestEntity(id="test-id", name="updated", value=100)
        
        # Mock exists check
        repo.exists = Mock(return_value=True)
        collection.update_one.return_value = Mock(matched_count=1)
        
        updated = repo.update(entity)
        
        assert updated.name == "updated"
        assert updated.value == 100
        
        # Verify update_one query
        collection.update_one.assert_called()
        call_args = collection.update_one.call_args
        assert call_args[0][0] == {"_id": "test-id"}  # filter
        assert "$set" in call_args[0][1]  # update document
        assert "$inc" in call_args[0][1]  # version increment
    
    def test_update_entity_not_found(self, repository):
        """Test updating non-existent entity."""
        repo, mock_backend, collection = repository
        
        entity = TestEntity(id="non-existent", name="test")
        repo.exists = Mock(return_value=False)
        
        with pytest.raises(NotFoundError):
            repo.update(entity)
    
    def test_delete_entity(self, repository):
        """Test entity deletion."""
        repo, mock_backend, collection = repository
        
        collection.delete_one.return_value = Mock(deleted_count=1)
        
        result = repo.delete("test-id")
        
        assert result is True
        
        # Verify delete_one query
        collection.delete_one.assert_called_with({"_id": "test-id"})
    
    def test_delete_entity_not_found(self, repository):
        """Test deleting non-existent entity."""
        repo, mock_backend, collection = repository
        
        collection.delete_one.return_value = Mock(deleted_count=0)
        
        result = repo.delete("non-existent")
        
        assert result is False
    
    def test_exists(self, repository):
        """Test entity existence check."""
        repo, mock_backend, collection = repository
        
        collection.count_documents.return_value = 1
        
        exists = repo.exists("test-id")
        
        assert exists is True
        
        # Verify count_documents query
        collection.count_documents.assert_called_with({"_id": "test-id"}, limit=1)
    
    def test_list_entities_no_pagination(self, repository):
        """Test listing entities without pagination."""
        repo, mock_backend, collection = repository
        
        # Mock cursor
        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.__iter__ = Mock(return_value=iter([
            {"_id": "1", "name": "test1", "value": 1},
            {"_id": "2", "name": "test2", "value": 2}
        ]))
        
        collection.find.return_value = mock_cursor
        
        entities = repo.list()
        
        assert len(entities) == 2
        
        # Verify find query
        collection.find.assert_called_with({})
        mock_cursor.sort.assert_called_with([("created_at", DESCENDING)])
    
    def test_list_entities_with_pagination(self, repository):
        """Test listing entities with pagination."""
        repo, mock_backend, collection = repository
        
        # Mock cursor
        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__ = Mock(return_value=iter([
            {"_id": "1", "name": "test1", "value": 1}
        ]))
        
        collection.find.return_value = mock_cursor
        collection.count_documents.return_value = 10
        
        pagination = Pagination(page=2, per_page=5)
        result = repo.list(pagination=pagination)
        
        assert result.total == 10
        assert result.page == 2
        assert result.per_page == 5
        assert len(result.items) == 1
        
        # Verify pagination calls
        mock_cursor.skip.assert_called_with(5)  # (page-1) * per_page
        mock_cursor.limit.assert_called_with(5)
    
    def test_list_entities_with_filters(self, repository):
        """Test listing entities with filters."""
        repo, mock_backend, collection = repository
        
        filters = [QueryFilter("name", "eq", "test")]
        mock_backend._build_filter.return_value = {"name": "test"}
        
        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.__iter__ = Mock(return_value=iter([]))
        collection.find.return_value = mock_cursor
        
        repo.list(filters=filters)
        
        # Verify filter was built and used
        mock_backend._build_filter.assert_called_with(filters)
        collection.find.assert_called_with({"name": "test"})
    
    def test_count_entities(self, repository):
        """Test entity counting."""
        repo, mock_backend, collection = repository
        
        collection.count_documents.return_value = 42
        mock_backend._build_filter.return_value = {}
        
        count = repo.count()
        
        assert count == 42
        collection.count_documents.assert_called_with({})
    
    def test_bulk_create(self, repository):
        """Test bulk entity creation."""
        repo, mock_backend, collection = repository
        
        entities = [
            TestEntity(name="test1", value=1),
            TestEntity(name="test2", value=2),
            TestEntity(name="test3", value=3)
        ]
        
        collection.insert_many.return_value = Mock(inserted_ids=["id1", "id2", "id3"])
        
        created = repo.bulk_create(entities)
        
        assert len(created) == 3
        
        # Verify insert_many was called
        collection.insert_many.assert_called_once()
        docs = collection.insert_many.call_args[0][0]
        assert len(docs) == 3
        assert all("_id" in doc for doc in docs)
    
    def test_bulk_update(self, repository):
        """Test bulk entity update."""
        repo, mock_backend, collection = repository
        
        entities = [
            TestEntity(id="id1", name="updated1", value=10),
            TestEntity(id="id2", name="updated2", value=20)
        ]
        
        collection.bulk_write.return_value = Mock()
        
        updated = repo.bulk_update(entities)
        
        assert len(updated) == 2
        
        # Verify bulk_write was called
        collection.bulk_write.assert_called_once()
        operations = collection.bulk_write.call_args[0][0]
        assert len(operations) == 2
    
    def test_bulk_delete(self, repository):
        """Test bulk entity deletion."""
        repo, mock_backend, collection = repository
        
        entity_ids = ["id1", "id2", "id3"]
        
        collection.delete_many.return_value = Mock(deleted_count=3)
        
        deleted_count = repo.bulk_delete(entity_ids)
        
        assert deleted_count == 3
        
        # Verify delete_many query
        collection.delete_many.assert_called_with({"_id": {"$in": entity_ids}})
    
    def test_search_with_text_index(self, repository):
        """Test full-text search with text index."""
        repo, mock_backend, collection = repository
        
        # Mock successful text search
        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.__iter__ = Mock(return_value=iter([
            {"_id": "1", "name": "apple pie", "score": 1.5},
            {"_id": "2", "name": "apple juice", "score": 1.2}
        ]))
        
        collection.find.return_value = mock_cursor
        
        results = repo.search("apple")
        
        assert len(results) == 2
        
        # Verify text search query
        collection.find.assert_called()
        call_args = collection.find.call_args
        assert call_args[0][0] == {"$text": {"$search": "apple"}}
    
    def test_search_fallback_to_regex(self, repository):
        """Test search fallback to regex when text index not available."""
        repo, mock_backend, collection = repository
        
        # Mock text search failure, then regex search success
        def mock_find(*args, **kwargs):
            if "$text" in args[0]:
                raise pymongo.errors.OperationFailure("text index not found")
            else:
                mock_cursor = Mock()
                mock_cursor.__iter__ = Mock(return_value=iter([
                    {"_id": "1", "name": "apple pie"}
                ]))
                return mock_cursor
        
        collection.find.side_effect = mock_find
        
        results = repo.search("apple", fields=["name"])
        
        assert len(results) == 1
        
        # Should have tried text search first, then regex
        assert collection.find.call_count == 2
    
    def test_search_with_pagination(self, repository):
        """Test search with pagination."""
        repo, mock_backend, collection = repository
        
        # Mock cursor for pagination
        mock_cursor = Mock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.__iter__ = Mock(return_value=iter([
            {"_id": "1", "name": "apple pie", "score": 1.5}
        ]))
        
        collection.find.return_value = mock_cursor
        collection.count_documents.return_value = 5
        
        pagination = Pagination(page=1, per_page=2)
        result = repo.search("apple", pagination=pagination)
        
        assert result.total == 5
        assert result.page == 1
        assert len(result.items) == 1
        
        # Verify pagination
        mock_cursor.skip.assert_called_with(0)
        mock_cursor.limit.assert_called_with(2)


class TestMongoDBIntegration:
    """Integration tests that would require actual MongoDB."""
    
    @pytest.mark.skip(reason="Requires MongoDB instance")
    def test_real_mongodb_connection(self):
        """Test with real MongoDB connection."""
        config = MongoDBConfig(
            connection_string="mongodb://localhost:27017/",
            database="test_db"
        )
        
        backend = MongoDBBackend(config)
        
        # Test basic operations
        collection = backend.create_collection("test_collection")
        
        # Cleanup
        backend.disconnect()
    
    @pytest.mark.skip(reason="Requires MongoDB instance")
    def test_real_repository_operations(self):
        """Test repository with real MongoDB."""
        config = MongoDBConfig(
            connection_string="mongodb://localhost:27017/",
            database="test_db"
        )
        
        repo = MongoDBRepository(config, TestEntity, "test_entities")
        
        # Test CRUD operations
        entity = TestEntity(name="integration_test", value=999)
        created = repo.create(entity)
        
        retrieved = repo.get(created.id)
        assert retrieved.name == "integration_test"
        
        # Test search
        results = repo.search("integration")
        assert len(results) >= 1
        
        # Cleanup
        repo.delete(created.id)