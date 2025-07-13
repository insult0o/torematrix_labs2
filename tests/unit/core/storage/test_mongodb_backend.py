import pytest
from datetime import datetime
from typing import Optional
from dataclasses import dataclass
from uuid import uuid4

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError

from torematrix.core.storage.mongodb_backend import MongoBackend
from torematrix.core.storage.base_backend import Entity, QueryFilter, SortOrder
from torematrix.core.storage.exceptions import StorageError

# Test entity
@dataclass
class TestDocument(Entity):
    id: str
    title: str
    content: str
    status: str
    created: datetime
    metadata: Optional[dict] = None

# Fixtures
@pytest.fixture
def mongo_url():
    """MongoDB connection URL for testing."""
    return "mongodb://localhost:27017"

@pytest.fixture
def mongo_db():
    """Test database name."""
    return "test_db"

@pytest.fixture
async def mongodb_backend(mongo_url, mongo_db):
    """Create MongoDB backend instance."""
    backend = MongoBackend(
        connection_string=mongo_url,
        database=mongo_db,
        entity_type=TestDocument,
        collection_name="test_documents"
    )
    await backend.initialize()
    yield backend
    # Cleanup
    await backend.client.drop_database(mongo_db)
    await backend.client.close()

@pytest.fixture
def sample_doc():
    """Create sample test document."""
    return TestDocument(
        id=str(uuid4()),
        title="Test Document",
        content="This is a test document",
        status="draft",
        created=datetime.utcnow(),
        metadata={"author": "test_user"}
    )

@pytest.mark.asyncio
async def test_create_and_read(mongodb_backend, sample_doc):
    """Test creating and reading a document."""
    # Create document
    created = await mongodb_backend.create(sample_doc)
    assert created == sample_doc
    
    # Read document
    read = await mongodb_backend.read(sample_doc.id)
    assert read == sample_doc
    
    # Read non-existent document
    missing = await mongodb_backend.read("missing-id")
    assert missing is None

@pytest.mark.asyncio
async def test_update(mongodb_backend, sample_doc):
    """Test updating a document."""
    # Create initial document
    await mongodb_backend.create(sample_doc)
    
    # Update document
    sample_doc.title = "Updated Title"
    updated = await mongodb_backend.update(sample_doc)
    assert updated.title == "Updated Title"
    
    # Verify update
    read = await mongodb_backend.read(sample_doc.id)
    assert read.title == "Updated Title"
    
    # Update non-existent document
    with pytest.raises(StorageError):
        non_existent = TestDocument(
            id="missing-id",
            title="Missing",
            content="Content",
            status="draft",
            created=datetime.utcnow()
        )
        await mongodb_backend.update(non_existent)

@pytest.mark.asyncio
async def test_delete(mongodb_backend, sample_doc):
    """Test deleting a document."""
    # Create document
    await mongodb_backend.create(sample_doc)
    
    # Delete document
    await mongodb_backend.delete(sample_doc.id)
    
    # Verify deletion
    read = await mongodb_backend.read(sample_doc.id)
    assert read is None
    
    # Delete non-existent document
    with pytest.raises(StorageError):
        await mongodb_backend.delete("missing-id")

@pytest.mark.asyncio
async def test_list_and_filter(mongodb_backend):
    """Test listing and filtering documents."""
    # Create test documents
    docs = [
        TestDocument(
            id=str(uuid4()),
            title=f"Doc {i}",
            content=f"Content {i}",
            status="draft" if i % 2 == 0 else "published",
            created=datetime.utcnow()
        )
        for i in range(5)
    ]
    
    for doc in docs:
        await mongodb_backend.create(doc)
    
    # List all documents
    all_docs = await mongodb_backend.list()
    assert len(all_docs) == 5
    
    # Filter by status
    filters = [QueryFilter(field="status", value="draft")]
    draft_docs = await mongodb_backend.list(filters=filters)
    assert len(draft_docs) == 3
    assert all(d.status == "draft" for d in draft_docs)
    
    # Test sorting
    sorted_docs = await mongodb_backend.list(
        sort_by="title",
        sort_order=SortOrder.DESC
    )
    assert [d.title for d in sorted_docs] == sorted(
        [d.title for d in docs],
        reverse=True
    )
    
    # Test pagination
    paged_docs = await mongodb_backend.list(skip=2, limit=2)
    assert len(paged_docs) == 2

@pytest.mark.asyncio
async def test_count(mongodb_backend):
    """Test counting documents."""
    # Create test documents
    docs = [
        TestDocument(
            id=str(uuid4()),
            title=f"Doc {i}",
            content=f"Content {i}",
            status="draft" if i % 2 == 0 else "published",
            created=datetime.utcnow()
        )
        for i in range(5)
    ]
    
    for doc in docs:
        await mongodb_backend.create(doc)
    
    # Count all documents
    total = await mongodb_backend.count()
    assert total == 5
    
    # Count with filter
    filters = [QueryFilter(field="status", value="draft")]
    draft_count = await mongodb_backend.count(filters=filters)
    assert draft_count == 3

@pytest.mark.asyncio
async def test_search(mongodb_backend):
    """Test full-text search."""
    # Create test documents
    docs = [
        TestDocument(
            id=str(uuid4()),
            title="Python Programming",
            content="Guide to Python programming language",
            status="published",
            created=datetime.utcnow()
        ),
        TestDocument(
            id=str(uuid4()),
            title="Database Design",
            content="Introduction to MongoDB database",
            status="published",
            created=datetime.utcnow()
        )
    ]
    
    for doc in docs:
        await mongodb_backend.create(doc)
    
    # Search for Python
    python_docs = await mongodb_backend.search("Python")
    assert len(python_docs) == 1
    assert "Python" in python_docs[0].title
    
    # Search for MongoDB
    db_docs = await mongodb_backend.search("MongoDB")
    assert len(db_docs) == 1
    assert "MongoDB" in db_docs[0].content

@pytest.mark.asyncio
async def test_bulk_operations(mongodb_backend):
    """Test bulk create and update operations."""
    # Create test documents
    docs = [
        TestDocument(
            id=str(uuid4()),
            title=f"Doc {i}",
            content=f"Content {i}",
            status="draft",
            created=datetime.utcnow()
        )
        for i in range(5)
    ]
    
    # Bulk create
    created_docs = await mongodb_backend.bulk_create(docs)
    assert len(created_docs) == 5
    
    # Verify creation
    for doc in docs:
        read = await mongodb_backend.read(doc.id)
        assert read == doc
    
    # Update documents
    for doc in docs:
        doc.status = "published"
    
    # Bulk update
    updated_docs = await mongodb_backend.bulk_update(docs)
    assert len(updated_docs) == 5
    
    # Verify updates
    for doc in docs:
        read = await mongodb_backend.read(doc.id)
        assert read.status == "published"

@pytest.mark.asyncio
async def test_transaction_rollback(mongodb_backend, sample_doc):
    """Test transaction rollback on error."""
    # Create initial document
    await mongodb_backend.create(sample_doc)
    
    # Try to update with invalid operation that should fail
    original = await mongodb_backend.read(sample_doc.id)
    
    with pytest.raises(StorageError):
        async with mongodb_backend.transaction() as session:
            # Update document
            await mongodb_backend.collection.update_one(
                {"id": sample_doc.id},
                {"$set": {"invalid_field": 1}},  # This should fail
                session=session
            )
            raise PyMongoError("Simulated error")
    
    # Verify rollback
    current = await mongodb_backend.read(sample_doc.id)
    assert current == original