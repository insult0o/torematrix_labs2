from typing import Any, Dict, List, Optional, TypeVar, Generic, Type
from datetime import datetime
import json
import logging
from contextlib import asynccontextmanager

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING, TEXT
from bson.objectid import ObjectId

from .base_backend import BaseStorageBackend, Entity, QueryFilter, SortOrder
from .exceptions import StorageError

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Entity)

class MongoBackend(BaseStorageBackend, Generic[T]):
    """MongoDB storage backend."""
    
    def __init__(
        self,
        connection_string: str,
        database: str,
        entity_type: Type[T],
        collection_name: str,
        **kwargs
    ):
        super().__init__(entity_type)
        self.client = AsyncIOMotorClient(connection_string, **kwargs)
        self.db = self.client[database]
        self.collection_name = collection_name
        self.collection: AsyncIOMotorCollection = self.db[collection_name]
        
    async def initialize(self):
        """Initialize collection and indexes."""
        # Create indexes
        await self.collection.create_index([("id", ASCENDING)], unique=True)
        await self.collection.create_index([("version", ASCENDING)])
        await self.collection.create_index([("created_at", ASCENDING)])
        await self.collection.create_index([("updated_at", ASCENDING)])
        
        # Create text index for search
        await self.collection.create_index([("$**", TEXT)])
        
    @asynccontextmanager
    async def transaction(self):
        """Provide transaction context with automatic rollback on error."""
        async with await self.client.start_session() as session:
            async with session.start_transaction():
                try:
                    yield session
                except Exception as e:
                    await session.abort_transaction()
                    raise StorageError(f"Transaction failed: {str(e)}") from e
    
    async def create(self, entity: T) -> T:
        """Create new entity in database."""
        now = datetime.utcnow()
        data = self.serialize(entity)
        
        doc = {
            "id": entity.id,
            "version": 1,
            "data": data,
            "created_at": now,
            "updated_at": now
        }
        
        try:
            await self.collection.insert_one(doc)
        except Exception as e:
            raise StorageError(f"Failed to create entity: {str(e)}") from e
            
        return entity
    
    async def read(self, entity_id: str) -> Optional[T]:
        """Read entity by ID."""
        doc = await self.collection.find_one({"id": entity_id})
        
        if doc is None:
            return None
            
        return self.deserialize(doc["data"])
    
    async def update(self, entity: T) -> T:
        """Update existing entity."""
        now = datetime.utcnow()
        data = self.serialize(entity)
        
        # Get current version
        doc = await self.collection.find_one({"id": entity.id})
        if doc is None:
            raise StorageError(f"Entity {entity.id} not found")
            
        new_version = doc["version"] + 1
        
        # Update document
        result = await self.collection.update_one(
            {"id": entity.id},
            {
                "$set": {
                    "data": data,
                    "version": new_version,
                    "updated_at": now
                }
            }
        )
        
        if result.modified_count == 0:
            raise StorageError(f"Failed to update entity {entity.id}")
            
        return entity
    
    async def delete(self, entity_id: str):
        """Delete entity by ID."""
        result = await self.collection.delete_one({"id": entity_id})
        
        if result.deleted_count == 0:
            raise StorageError(f"Entity {entity_id} not found")
    
    async def list(
        self,
        filters: Optional[List[QueryFilter]] = None,
        sort_by: Optional[str] = None,
        sort_order: SortOrder = SortOrder.ASC,
        skip: int = 0,
        limit: Optional[int] = None
    ) -> List[T]:
        """List entities with filtering, sorting and pagination."""
        # Build query
        query = {}
        if filters:
            for f in filters:
                query[f"data.{f.field}"] = f.value
                
        # Build sort
        sort_spec = []
        if sort_by:
            direction = ASCENDING if sort_order == SortOrder.ASC else DESCENDING
            sort_spec.append((f"data.{sort_by}", direction))
            
        # Execute query
        cursor = self.collection.find(query)
        
        if sort_spec:
            cursor = cursor.sort(sort_spec)
            
        cursor = cursor.skip(skip)
        if limit:
            cursor = cursor.limit(limit)
            
        docs = await cursor.to_list(length=None)
        return [self.deserialize(doc["data"]) for doc in docs]
    
    async def count(self, filters: Optional[List[QueryFilter]] = None) -> int:
        """Count entities matching filters."""
        query = {}
        if filters:
            for f in filters:
                query[f"data.{f.field}"] = f.value
                
        return await self.collection.count_documents(query)
    
    async def search(self, query: str, limit: Optional[int] = None) -> List[T]:
        """Full-text search using text index."""
        cursor = self.collection.find(
            {"$text": {"$search": query}},
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})])
        
        if limit:
            cursor = cursor.limit(limit)
            
        docs = await cursor.to_list(length=None)
        return [self.deserialize(doc["data"]) for doc in docs]
    
    async def bulk_create(self, entities: List[T]) -> List[T]:
        """Create multiple entities in a single transaction."""
        if not entities:
            return []
            
        now = datetime.utcnow()
        docs = []
        
        for entity in entities:
            data = self.serialize(entity)
            docs.append({
                "id": entity.id,
                "version": 1,
                "data": data,
                "created_at": now,
                "updated_at": now
            })
            
        try:
            await self.collection.insert_many(docs)
        except Exception as e:
            raise StorageError(f"Bulk create failed: {str(e)}") from e
            
        return entities
    
    async def bulk_update(self, entities: List[T]) -> List[T]:
        """Update multiple entities in a single transaction."""
        if not entities:
            return []
            
        async with self.transaction() as session:
            for entity in entities:
                # Get current version
                doc = await self.collection.find_one(
                    {"id": entity.id},
                    session=session
                )
                if doc is None:
                    raise StorageError(f"Entity {entity.id} not found")
                    
                new_version = doc["version"] + 1
                data = self.serialize(entity)
                now = datetime.utcnow()
                
                # Update document
                result = await self.collection.update_one(
                    {"id": entity.id},
                    {
                        "$set": {
                            "data": data,
                            "version": new_version,
                            "updated_at": now
                        }
                    },
                    session=session
                )
                
                if result.modified_count == 0:
                    raise StorageError(f"Failed to update entity {entity.id}")
                    
        return entities