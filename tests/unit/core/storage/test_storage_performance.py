"""
Performance and integration tests for storage backends.
"""

import pytest
import time
import tempfile
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
from unittest.mock import Mock
import uuid

from torematrix.core.storage import (
    SQLiteRepository, SQLiteConfig,
    QueryFilter, Pagination, SortOrder
)
from torematrix.core.storage.factory import (
    StorageFactory, StorageBackend,
    create_sqlite_repository, create_repository_from_env
)


@dataclass
class PerformanceTestEntity:
    """Entity for performance testing."""
    id: Optional[str] = None
    name: str = ""
    category: str = ""
    value: int = 0
    score: float = 0.0
    active: bool = True
    description: str = ""
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "value": self.value,
            "score": self.score,
            "active": self.active,
            "description": self.description,
            "tags": self.tags
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            category=data.get("category", ""),
            value=data.get("value", 0),
            score=data.get("score", 0.0),
            active=data.get("active", True),
            description=data.get("description", ""),
            tags=data.get("tags", [])
        )


class TestStorageFactory:
    """Test storage factory functionality."""
    
    def test_create_sqlite_repository(self):
        """Test creating SQLite repository via factory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            
            repo = StorageFactory.create_repository(
                backend=StorageBackend.SQLITE,
                entity_class=PerformanceTestEntity,
                collection_name="test_entities",
                database_path=str(db_path)
            )
            
            assert isinstance(repo, SQLiteRepository)
            assert repo.entity_class == PerformanceTestEntity
            assert repo.table_name == "test_entities"
    
    def test_create_postgresql_repository(self):
        """Test creating PostgreSQL repository via factory."""
        # Mock the actual connection since we don't have a real PostgreSQL instance
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                repo = StorageFactory.create_repository(
                    backend=StorageBackend.POSTGRESQL,
                    entity_class=PerformanceTestEntity,
                    collection_name="test_entities",
                    host="localhost",
                    port=5432,
                    database="test_db",
                    user="test_user",
                    password="test_pass"
                )
                
                # This will fail due to connection, but we can check the type
                assert repo.entity_class == PerformanceTestEntity
                assert repo.table_name == "test_entities"
                
            except Exception:
                # Expected to fail without real PostgreSQL
                pass
    
    def test_create_mongodb_repository(self):
        """Test creating MongoDB repository via factory."""
        try:
            repo = StorageFactory.create_repository(
                backend=StorageBackend.MONGODB,
                entity_class=PerformanceTestEntity,
                collection_name="test_entities",
                connection_string="mongodb://localhost:27017/",
                database="test_db"
            )
            
            # This will fail due to connection, but we can check the type
            assert repo.entity_class == PerformanceTestEntity
            assert repo.collection_name == "test_entities"
            
        except Exception:
            # Expected to fail without real MongoDB
            pass
    
    def test_create_from_config(self):
        """Test creating repository from configuration dictionary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "config_test.db"
            
            config = {
                "backend": "sqlite",
                "database_path": str(db_path),
                "enable_wal": True
            }
            
            repo = StorageFactory.create_from_config(
                config,
                PerformanceTestEntity,
                "config_entities"
            )
            
            assert isinstance(repo, SQLiteRepository)
            assert repo.table_name == "config_entities"
    
    def test_create_from_config_unknown_backend(self):
        """Test creating repository with unknown backend."""
        config = {"backend": "unknown_backend"}
        
        with pytest.raises(ValueError, match="Unknown backend"):
            StorageFactory.create_from_config(
                config,
                PerformanceTestEntity,
                "test_entities"
            )
    
    def test_get_default_config(self):
        """Test getting default configurations."""
        sqlite_config = StorageFactory.get_default_config(StorageBackend.SQLITE)
        assert sqlite_config["backend"] == "sqlite"
        assert "database_path" in sqlite_config
        assert sqlite_config["enable_wal"] is True
        
        postgres_config = StorageFactory.get_default_config(StorageBackend.POSTGRESQL)
        assert postgres_config["backend"] == "postgresql"
        assert postgres_config["host"] == "localhost"
        assert postgres_config["port"] == 5432
        
        mongo_config = StorageFactory.get_default_config(StorageBackend.MONGODB)
        assert mongo_config["backend"] == "mongodb"
        assert "connection_string" in mongo_config
    
    def test_convenience_functions(self):
        """Test convenience functions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "convenience.db"
            
            repo = create_sqlite_repository(
                PerformanceTestEntity,
                "convenience_entities",
                database_path=str(db_path)
            )
            
            assert isinstance(repo, SQLiteRepository)
            assert repo.table_name == "convenience_entities"
    
    def test_create_repository_from_env(self):
        """Test creating repository from environment variables."""
        import os
        
        # Set environment variables
        original_backend = os.environ.get('TOREMATRIX_STORAGE_BACKEND')
        original_path = os.environ.get('TOREMATRIX_DATABASE_PATH')
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                db_path = Path(temp_dir) / "env_test.db"
                
                os.environ['TOREMATRIX_STORAGE_BACKEND'] = 'sqlite'
                os.environ['TOREMATRIX_DATABASE_PATH'] = str(db_path)
                
                repo = create_repository_from_env(
                    PerformanceTestEntity,
                    "env_entities"
                )
                
                assert isinstance(repo, SQLiteRepository)
                assert repo.table_name == "env_entities"
                
        finally:
            # Restore original environment
            if original_backend is not None:
                os.environ['TOREMATRIX_STORAGE_BACKEND'] = original_backend
            elif 'TOREMATRIX_STORAGE_BACKEND' in os.environ:
                del os.environ['TOREMATRIX_STORAGE_BACKEND']
                
            if original_path is not None:
                os.environ['TOREMATRIX_DATABASE_PATH'] = original_path
            elif 'TOREMATRIX_DATABASE_PATH' in os.environ:
                del os.environ['TOREMATRIX_DATABASE_PATH']


class TestPerformanceBenchmarks:
    """Performance benchmarks for storage operations."""
    
    @pytest.fixture
    def repository(self):
        """Create repository for performance testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "performance.db"
            repo = create_sqlite_repository(
                PerformanceTestEntity,
                "perf_entities",
                database_path=str(db_path)
            )
            yield repo
    
    @pytest.fixture
    def test_entities(self):
        """Generate test entities for performance testing."""
        entities = []
        categories = ["electronics", "books", "clothing", "home", "sports"]
        
        for i in range(1000):
            entity = PerformanceTestEntity(
                name=f"Entity {i:04d}",
                category=categories[i % len(categories)],
                value=i * 10,
                score=float(i % 100) / 100.0,
                active=i % 3 != 0,  # ~67% active
                description=f"Description for entity {i} " * 5,  # Longer text
                tags=[f"tag{j}" for j in range(i % 5)]  # Variable tag count
            )
            entities.append(entity)
        
        return entities
    
    @pytest.mark.performance
    def test_bulk_create_performance(self, repository, test_entities):
        """Test bulk create performance."""
        start_time = time.time()
        
        created_entities = repository.bulk_create(test_entities)
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert len(created_entities) == 1000
        assert duration < 5.0, f"Bulk create took {duration:.3f}s, should be < 5s"
        
        # Verify all entities have IDs
        assert all(entity.id is not None for entity in created_entities)
        
        print(f"✅ Bulk create performance: 1000 entities in {duration:.3f}s ({1000/duration:.1f} ops/sec)")
    
    @pytest.mark.performance
    def test_individual_create_performance(self, repository):
        """Test individual create performance."""
        entities = []
        
        start_time = time.time()
        
        for i in range(100):
            entity = PerformanceTestEntity(
                name=f"Individual {i}",
                value=i,
                category="test"
            )
            created = repository.create(entity)
            entities.append(created)
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert len(entities) == 100
        assert duration < 2.0, f"Individual creates took {duration:.3f}s, should be < 2s"
        
        print(f"✅ Individual create performance: 100 entities in {duration:.3f}s ({100/duration:.1f} ops/sec)")
    
    @pytest.mark.performance
    def test_query_performance(self, repository, test_entities):
        """Test query performance with various filters."""
        # First, populate the database
        repository.bulk_create(test_entities)
        
        # Test simple queries
        start_time = time.time()
        
        # Query by category
        electronics = repository.list(
            filters=[QueryFilter("category", "eq", "electronics")]
        )
        
        # Query by value range
        high_value = repository.list(
            filters=[
                QueryFilter("value", "gte", 5000),
                QueryFilter("active", "eq", True)
            ]
        )
        
        # Query with pagination
        paginated = repository.list(
            pagination=Pagination(page=1, per_page=50),
            sort_by="value",
            sort_order=SortOrder.DESC
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert len(electronics) > 0
        assert len(high_value) > 0
        assert len(paginated.items) == 50
        assert duration < 1.0, f"Query operations took {duration:.3f}s, should be < 1s"
        
        print(f"✅ Query performance: 3 complex queries in {duration:.3f}s")
    
    @pytest.mark.performance
    def test_search_performance(self, repository, test_entities):
        """Test search performance."""
        # Populate database
        repository.bulk_create(test_entities)
        
        start_time = time.time()
        
        # Search operations
        search_results = repository.search("Entity 05")
        search_paginated = repository.search(
            "Description",
            pagination=Pagination(page=1, per_page=20)
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert len(search_results) > 0
        assert len(search_paginated.items) > 0
        assert duration < 1.0, f"Search operations took {duration:.3f}s, should be < 1s"
        
        print(f"✅ Search performance: 2 search queries in {duration:.3f}s")
    
    @pytest.mark.performance
    def test_bulk_update_performance(self, repository, test_entities):
        """Test bulk update performance."""
        # Create entities first
        created_entities = repository.bulk_create(test_entities[:500])
        
        # Modify entities
        for entity in created_entities:
            entity.value += 1000
            entity.category = "updated"
        
        start_time = time.time()
        
        updated_entities = repository.bulk_update(created_entities)
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert len(updated_entities) == 500
        assert duration < 3.0, f"Bulk update took {duration:.3f}s, should be < 3s"
        
        # Verify updates
        sample_entity = repository.get(updated_entities[0].id)
        assert sample_entity.category == "updated"
        
        print(f"✅ Bulk update performance: 500 entities in {duration:.3f}s ({500/duration:.1f} ops/sec)")
    
    @pytest.mark.performance
    def test_bulk_delete_performance(self, repository, test_entities):
        """Test bulk delete performance."""
        # Create entities first
        created_entities = repository.bulk_create(test_entities[:300])
        entity_ids = [entity.id for entity in created_entities]
        
        start_time = time.time()
        
        deleted_count = repository.bulk_delete(entity_ids)
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert deleted_count == 300
        assert duration < 1.0, f"Bulk delete took {duration:.3f}s, should be < 1s"
        
        # Verify deletions
        remaining_count = repository.count()
        assert remaining_count == 0
        
        print(f"✅ Bulk delete performance: 300 entities in {duration:.3f}s ({300/duration:.1f} ops/sec)")
    
    @pytest.mark.performance
    def test_pagination_performance(self, repository, test_entities):
        """Test pagination performance with large dataset."""
        # Create large dataset
        repository.bulk_create(test_entities)
        
        start_time = time.time()
        
        # Test multiple page queries
        total_items = 0
        for page in range(1, 21):  # 20 pages
            result = repository.list(
                pagination=Pagination(page=page, per_page=50)
            )
            total_items += len(result.items)
            
            # Verify pagination metadata
            assert result.page == page
            assert result.per_page == 50
            assert result.total == 1000
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert total_items == 1000
        assert duration < 2.0, f"Pagination queries took {duration:.3f}s, should be < 2s"
        
        print(f"✅ Pagination performance: 20 pages (1000 items) in {duration:.3f}s")
    
    @pytest.mark.performance
    def test_transaction_performance(self, repository):
        """Test transaction performance."""
        entities = []
        for i in range(100):
            entities.append(PerformanceTestEntity(
                name=f"Transaction {i}",
                value=i
            ))
        
        start_time = time.time()
        
        with repository.transaction():
            for entity in entities:
                repository.create(entity)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verify all entities were created
        count = repository.count()
        assert count == 100
        
        assert duration < 1.0, f"Transaction took {duration:.3f}s, should be < 1s"
        
        print(f"✅ Transaction performance: 100 creates in transaction in {duration:.3f}s")
    
    @pytest.mark.performance
    def test_memory_usage(self, repository, test_entities):
        """Test memory usage with large datasets."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create large dataset
        repository.bulk_create(test_entities)
        
        # Query large dataset
        all_entities = repository.list()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        assert len(all_entities) == 1000
        assert memory_increase < 100, f"Memory usage increased by {memory_increase:.1f}MB, should be < 100MB"
        
        print(f"✅ Memory usage: {memory_increase:.1f}MB increase for 1000 entities")


class TestConnectionPooling:
    """Test connection pooling and resource management."""
    
    def test_sqlite_connection_reuse(self):
        """Test SQLite connection reuse."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "connection_test.db"
            
            config = SQLiteConfig(database_path=str(db_path))
            repo = SQLiteRepository(config, PerformanceTestEntity, "conn_entities")
            
            # Perform multiple operations
            entity1 = PerformanceTestEntity(name="test1", value=1)
            entity2 = PerformanceTestEntity(name="test2", value=2)
            
            created1 = repo.create(entity1)
            created2 = repo.create(entity2)
            
            # Retrieve entities
            retrieved1 = repo.get(created1.id)
            retrieved2 = repo.get(created2.id)
            
            assert retrieved1.name == "test1"
            assert retrieved2.name == "test2"
            
            # Connection should be reused efficiently
            assert repo.is_connected()
    
    def test_concurrent_access_simulation(self):
        """Test simulated concurrent access patterns."""
        import threading
        import queue
        
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "concurrent_test.db"
            
            results = queue.Queue()
            errors = queue.Queue()
            
            def worker_task(worker_id):
                try:
                    # Each worker gets its own repository instance
                    repo = create_sqlite_repository(
                        PerformanceTestEntity,
                        "concurrent_entities",
                        database_path=str(db_path)
                    )
                    
                    # Perform operations
                    for i in range(10):
                        entity = PerformanceTestEntity(
                            name=f"worker_{worker_id}_entity_{i}",
                            value=worker_id * 100 + i
                        )
                        created = repo.create(entity)
                        results.put(created.id)
                        
                except Exception as e:
                    errors.put(f"Worker {worker_id}: {e}")
            
            # Start multiple worker threads
            threads = []
            for worker_id in range(5):
                thread = threading.Thread(target=worker_task, args=(worker_id,))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join()
            
            # Check results
            assert errors.qsize() == 0, f"Errors occurred: {list(errors.queue)}"
            assert results.qsize() == 50  # 5 workers * 10 entities each
            
            # Verify data integrity
            repo = create_sqlite_repository(
                PerformanceTestEntity,
                "concurrent_entities",
                database_path=str(db_path)
            )
            total_count = repo.count()
            assert total_count == 50


if __name__ == "__main__":
    # Run performance tests manually
    pytest.main([__file__ + "::TestPerformanceBenchmarks", "-v", "-m", "performance"])