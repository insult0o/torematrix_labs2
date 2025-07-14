# Storage Layer Architecture

## Overview

The storage layer in TORE Matrix Labs V3 provides a flexible, multi-backend storage solution using the Repository pattern. It supports SQLite for desktop deployments, PostgreSQL for enterprise use, and MongoDB for flexible schema requirements.

## Design Principles

1. **Backend Agnostic**: Core application code doesn't depend on specific storage implementations
2. **Repository Pattern**: Clean interface for data access operations
3. **Type Safety**: Full type hints and generic support
4. **Async Support**: Both sync and async repository interfaces
5. **Migration Support**: Schema versioning and data migration tools

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Application Layer                       │
│          (Uses Repository Interface)                 │
└─────────────────┬───────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────┐
│            Repository Interface                      │
│      (Abstract CRUD + Query Operations)              │
└─────────────────┬───────────────────────────────────┘
                  │
        ┌─────────┴─────────┬─────────────┬
        │                   │             │
┌───────▼────────┐ ┌───────▼────────┐ ┌──▼──────────┐
│     SQLite     │ │   PostgreSQL    │ │   MongoDB   │
│    Backend     │ │    Backend      │ │   Backend   │
└────────────────┘ └─────────────────┘ └─────────────┘
```

## Core Components

### 1. Repository Interface

The `Repository` abstract base class defines the contract for all storage operations:

```python
class Repository(ABC, Generic[T]):
    # Basic CRUD
    def create(self, entity: T) -> T
    def get(self, entity_id: str) -> Optional[T]
    def update(self, entity: T) -> T
    def delete(self, entity_id: str) -> bool
    
    # Querying
    def list(filters, sort_by, pagination) -> List[T] | PaginatedResult[T]
    def count(filters) -> int
    def exists(entity_id: str) -> bool
    def search(query: str) -> List[T]
    
    # Bulk operations
    def bulk_create(entities: List[T]) -> List[T]
    def bulk_update(entities: List[T]) -> List[T]
    def bulk_delete(entity_ids: List[str]) -> int
    
    # Transactions
    def transaction() -> ContextManager
```

### 2. Query Capabilities

#### Filtering
```python
filters = [
    QueryFilter(field="status", operator="eq", value="active"),
    QueryFilter(field="created_at", operator="gte", value="2024-01-01"),
    QueryFilter(field="tags", operator="contains", value="important")
]
results = repo.list(filters=filters)
```

#### Pagination
```python
page_result = repo.list(
    pagination=Pagination(page=2, per_page=50),
    sort_by="created_at",
    sort_order=SortOrder.DESC
)
```

#### Full-text Search
```python
search_results = repo.search(
    query="document processing",
    fields=["title", "content"],
    pagination=Pagination(page=1, per_page=20)
)
```

### 3. Backend Implementations

#### SQLite (Default)
- File-based storage for desktop applications
- Full SQL capabilities with FTS5 for search
- Write-Ahead Logging (WAL) for performance
- Automatic backups and vacuum support

#### PostgreSQL
- Enterprise-grade with connection pooling
- JSONB for flexible schema with indexing
- Full-text search with pg_trgm
- Streaming replication support

#### MongoDB
- Document-oriented for maximum flexibility
- Aggregation pipeline for complex queries
- Horizontal scaling with sharding
- GridFS for large file storage

## Usage Examples

### Basic Usage

```python
from torematrix.core.storage import StorageFactory, StorageBackend
from myapp.models import Document

# Create repository
repo = StorageFactory.create_repository(
    backend=StorageBackend.SQLITE,
    entity_class=Document,
    collection_name="documents",
    database_path="data/myapp.db"
)

# Create document
doc = Document(title="My Document", content="...")
created_doc = repo.create(doc)

# Query documents
active_docs = repo.list(
    filters=[QueryFilter("status", "eq", "active")],
    sort_by="updated_at",
    sort_order=SortOrder.DESC
)

# Full-text search
results = repo.search("important keyword")
```

### Configuration

```python
# From configuration file
config = {
    "backend": "postgresql",
    "host": "db.example.com",
    "port": 5432,
    "database": "torematrix",
    "pool_size": 20
}

repo = StorageFactory.create_from_config(
    config_dict=config,
    entity_class=Document,
    collection_name="documents"
)
```

### Transactions

```python
with repo.transaction():
    # All operations in transaction
    doc1 = repo.create(Document(...))
    doc2 = repo.create(Document(...))
    doc1.status = "published"
    repo.update(doc1)
    # Commits on success, rolls back on exception
```

### Migrations

```python
from torematrix.core.storage import MigrationManager, BackendMigrator

# Apply schema migrations
manager = MigrationManager()
manager.migrate(repo, target_version="003")

# Migrate between backends
migrator = BackendMigrator()
stats = migrator.migrate_data(
    source_repo=sqlite_repo,
    target_repo=postgres_repo,
    progress_callback=lambda done, total: print(f"{done}/{total}")
)
```

## Performance Considerations

### Connection Pooling
- SQLite: Thread-local connections
- PostgreSQL: Configurable pool size
- MongoDB: Built-in connection pooling

### Indexing
- Automatic indexes on common fields (id, created_at, updated_at)
- Backend-specific index creation
- Full-text search indexes

### Caching
- Works with the caching layer (Issue #48)
- Repository results can be cached
- Cache invalidation on updates

## Error Handling

The storage layer provides specific exception types:

- `StorageError`: Base exception for all storage errors
- `NotFoundError`: Entity not found
- `DuplicateError`: Duplicate key/constraint violation
- `TransactionError`: Transaction failed

## Testing

### Unit Tests
```python
# Use in-memory SQLite for tests
test_repo = create_sqlite_repository(
    entity_class=MyEntity,
    collection_name="test_entities",
    database_path=":memory:"
)
```

### Integration Tests
- Test with real backend instances
- Use Docker containers for PostgreSQL/MongoDB
- Verify backend-specific features

## Future Enhancements

1. **Async Repository Implementation**
   - Full async/await support
   - AsyncIO-based connection pooling
   - Streaming query results

2. **Advanced Features**
   - Database sharding support
   - Read replicas
   - Geo-distributed storage
   - Time-series optimizations

3. **Additional Backends**
   - Redis for caching layer
   - Elasticsearch for advanced search
   - S3 for blob storage
   - CockroachDB for global distribution

## Security Considerations

1. **SQL Injection Prevention**
   - Parameterized queries only
   - Input validation
   - Schema validation

2. **Access Control**
   - Repository-level permissions
   - Row-level security (PostgreSQL)
   - Field-level encryption

3. **Audit Logging**
   - Track all modifications
   - User attribution
   - Compliance support

---

*The storage layer provides the foundation for reliable, scalable data persistence in TORE Matrix Labs V3*