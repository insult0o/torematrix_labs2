"""
MongoDB backend implementation for flexible schema requirements.

Provides document-oriented storage with dynamic schema capabilities.
"""

import logging
from typing import Dict, Any, Optional, List, Union, Type, TypeVar
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import pymongo
from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.collection import Collection
from pymongo.database import Database
from bson import ObjectId
from bson.errors import InvalidId

from .repository import (
    Repository, AsyncRepository, QueryFilter, Pagination,
    PaginatedResult, SortOrder, StorageError, NotFoundError, TransactionError
)
from .base_backend import BaseBackend, BackendConfig


logger = logging.getLogger(__name__)
T = TypeVar('T')


class MongoDBConfig(BackendConfig):
    """MongoDB-specific configuration."""
    
    def __init__(
        self,
        connection_string: str = "mongodb://localhost:27017/",
        database: str = "torematrix",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.connection_string = connection_string
        self.database = database
        self.write_concern = kwargs.get('write_concern', 'majority')
        self.read_preference = kwargs.get('read_preference', 'primary')
        self.server_selection_timeout = kwargs.get('server_selection_timeout', 30000)
        self.max_pool_size = kwargs.get('max_pool_size', 100)
        self.min_pool_size = kwargs.get('min_pool_size', 0)
        self.connect_timeout = kwargs.get('connect_timeout', 20000)
        self.socket_timeout = kwargs.get('socket_timeout', 20000)


class MongoDBBackend(BaseBackend):
    """
    MongoDB storage backend implementation.
    
    Provides flexible document storage with:
    - Dynamic schema support
    - Powerful aggregation pipeline
    - Horizontal scaling with sharding
    - Full-text search capabilities
    """
    
    def __init__(self, config: MongoDBConfig):
        super().__init__(config)
        self.config: MongoDBConfig = config
        self._client: Optional[MongoClient] = None
        self._database: Optional[Database] = None
        self._session = None
        self._in_transaction = False
        
    @property
    def client(self) -> MongoClient:
        """Get MongoDB client."""
        if self._client is None:
            self.connect()
        return self._client
    
    @property 
    def database(self) -> Database:
        """Get MongoDB database."""
        if self._database is None:
            self.connect()
        return self._database
        
    def connect(self) -> None:
        """Establish connection to MongoDB."""
        try:
            # Create client with configuration
            self._client = MongoClient(
                self.config.connection_string,
                maxPoolSize=self.config.max_pool_size,
                minPoolSize=self.config.min_pool_size,
                connectTimeoutMS=self.config.connect_timeout,
                socketTimeoutMS=self.config.socket_timeout,
                serverSelectionTimeoutMS=self.config.server_selection_timeout,
                retryWrites=True,
                w=self.config.write_concern
            )
            
            # Get database reference
            self._database = self._client[self.config.database]
            
            # Test connection
            self._client.admin.command('ping')
            
            logger.info(f"Connected to MongoDB: {self.config.database}")
            
        except Exception as e:
            self.handle_storage_error("connect", e)
    
    def disconnect(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._database = None
            logger.info("Disconnected from MongoDB")
    
    def is_connected(self) -> bool:
        """Check if connected to MongoDB."""
        if not self._client:
            return False
        try:
            self._client.admin.command('ping')
            return True
        except Exception:
            return False
    
    def create_collection(self, collection_name: str, schema: Optional[Dict[str, Any]] = None) -> Collection:
        """
        Create a collection with optional schema validation.
        
        Args:
            collection_name: Name of the collection
            schema: Optional JSON schema for validation
        """
        try:
            if collection_name not in self.database.list_collection_names():
                # Create collection with validation if schema provided
                if schema:
                    validator = {"$jsonSchema": schema}
                    self.database.create_collection(
                        collection_name,
                        validator=validator,
                        validationLevel="moderate"  # Allow updates that don't match
                    )
                else:
                    self.database.create_collection(collection_name)
                
                # Create default indexes
                collection = self.database[collection_name]
                collection.create_index("created_at")
                collection.create_index("updated_at")
                
                logger.info(f"Created MongoDB collection: {collection_name}")
            
            return self.database[collection_name]
            
        except Exception as e:
            self.handle_storage_error("create_collection", e)
    
    def _build_filter(self, filters: Optional[List[QueryFilter]]) -> Dict[str, Any]:
        """Build MongoDB filter from QueryFilter list."""
        if not filters:
            return {}
            
        mongo_filter = {}
        
        for f in filters:
            if f.operator == "eq":
                mongo_filter[f.field] = f.value
            elif f.operator == "ne":
                mongo_filter[f.field] = {"$ne": f.value}
            elif f.operator == "gt":
                mongo_filter[f.field] = {"$gt": f.value}
            elif f.operator == "lt":
                mongo_filter[f.field] = {"$lt": f.value}
            elif f.operator == "gte":
                mongo_filter[f.field] = {"$gte": f.value}
            elif f.operator == "lte":
                mongo_filter[f.field] = {"$lte": f.value}
            elif f.operator == "in":
                mongo_filter[f.field] = {"$in": f.value}
            elif f.operator == "like":
                # Convert SQL LIKE to MongoDB regex
                pattern = f.value.replace('%', '.*').replace('_', '.')
                mongo_filter[f.field] = {"$regex": pattern, "$options": "i"}
            elif f.operator == "contains":
                mongo_filter[f.field] = {"$regex": f.value, "$options": "i"}
            else:
                raise StorageError(f"Unsupported operator: {f.operator}")
        
        return mongo_filter
    
    @contextmanager
    def transaction(self):
        """Transaction context manager using MongoDB sessions."""
        session = self.client.start_session()
        try:
            with session.start_transaction():
                self._session = session
                self._in_transaction = True
                yield session
                # Transaction commits automatically if no exception
        except Exception as e:
            # Transaction aborts automatically on exception
            raise TransactionError(f"Transaction failed: {e}")
        finally:
            self._session = None
            self._in_transaction = False
            session.end_session()
    
    def create_text_index(self, collection_name: str, fields: List[str]) -> None:
        """Create text index for full-text search."""
        try:
            collection = self.database[collection_name]
            
            # Create text index on specified fields
            index_spec = [(field, TEXT) for field in fields]
            collection.create_index(index_spec, name=f"{collection_name}_text_index")
            
            logger.info(f"Created text index for {collection_name} on fields: {fields}")
            
        except Exception as e:
            self.handle_storage_error("create_text_index", e)
    
    def create_compound_index(self, collection_name: str, fields: List[tuple]) -> None:
        """
        Create compound index.
        
        Args:
            collection_name: Collection name
            fields: List of (field_name, direction) tuples
        """
        try:
            collection = self.database[collection_name]
            collection.create_index(fields)
            
            logger.info(f"Created compound index for {collection_name}: {fields}")
            
        except Exception as e:
            self.handle_storage_error("create_compound_index", e)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get MongoDB statistics."""
        stats = super().get_statistics()
        
        if self.is_connected():
            # Database stats
            db_stats = self.database.command("dbStats")
            stats.update({
                'database_size_mb': db_stats.get('dataSize', 0) / (1024 * 1024),
                'storage_size_mb': db_stats.get('storageSize', 0) / (1024 * 1024),
                'index_size_mb': db_stats.get('indexSize', 0) / (1024 * 1024),
                'collections': db_stats.get('collections', 0),
                'indexes': db_stats.get('indexes', 0)
            })
            
            # Collection stats
            collection_stats = {}
            for collection_name in self.database.list_collection_names():
                coll_stats = self.database.command("collStats", collection_name)
                collection_stats[collection_name] = {
                    'documents': coll_stats.get('count', 0),
                    'size_mb': coll_stats.get('size', 0) / (1024 * 1024),
                    'avg_obj_size': coll_stats.get('avgObjSize', 0),
                    'indexes': coll_stats.get('nindexes', 0)
                }
            
            stats['collections_details'] = collection_stats
            
        return stats
    
    def create_backup(self, collection_name: Optional[str] = None) -> Path:
        """Create backup using mongodump."""
        if not self.config.backup_enabled:
            return None
            
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        if collection_name:
            backup_path = self.config.backup_path / f"{collection_name}_{timestamp}"
            cmd = [
                "mongodump", 
                "--uri", self.config.connection_string,
                "--collection", collection_name,
                "--out", str(backup_path)
            ]
        else:
            backup_path = self.config.backup_path / f"database_{timestamp}"
            cmd = [
                "mongodump", 
                "--uri", self.config.connection_string,
                "--out", str(backup_path)
            ]
        
        try:
            import subprocess
            subprocess.run(cmd, check=True)
            
            logger.info(f"Created MongoDB backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None


class MongoDBRepository(Repository[T], MongoDBBackend):
    """
    MongoDB implementation of the Repository interface.
    
    Leverages MongoDB's document model for flexible schema evolution.
    """
    
    def __init__(self, config: MongoDBConfig, entity_class: Type[T], collection_name: str):
        MongoDBBackend.__init__(self, config)
        self.entity_class = entity_class
        self.collection_name = collection_name
        
        # Get or create collection
        self._collection = self.create_collection(collection_name)
    
    @property
    def collection(self) -> Collection:
        """Get MongoDB collection."""
        return self._collection
    
    def create(self, entity: T) -> T:
        """Create a new entity."""
        # Generate ID if not present
        if not hasattr(entity, 'id') or not entity.id:
            entity.id = self.generate_id()
        
        # Serialize entity
        data = self.serialize_entity(entity)
        data = self.add_timestamps(data)
        
        # Set MongoDB _id to our id for consistency
        data['_id'] = entity.id
        
        try:
            # Insert with session if in transaction
            if self._session:
                self.collection.insert_one(data, session=self._session)
            else:
                self.collection.insert_one(data)
            
            return entity
            
        except Exception as e:
            self.handle_storage_error("create", e)
    
    def get(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        if not self.validate_id(entity_id):
            return None
            
        try:
            # Query by _id
            doc = self.collection.find_one({"_id": entity_id})
            
            if doc:
                # Remove MongoDB _id before deserialization
                doc.pop('_id', None)
                return self.deserialize_entity(doc, self.entity_class)
            return None
            
        except Exception as e:
            self.handle_storage_error("get", e)
    
    def update(self, entity: T) -> T:
        """Update existing entity."""
        if not hasattr(entity, 'id'):
            raise StorageError("Entity must have an id for update")
            
        # Check if exists
        if not self.exists(entity.id):
            raise NotFoundError(f"Entity {entity.id} not found")
        
        # Serialize and update timestamps
        data = self.serialize_entity(entity)
        data = self.add_timestamps(data, update=True)
        
        try:
            # Update operation
            update_doc = {"$set": data, "$inc": {"_version": 1}}
            
            if self._session:
                result = self.collection.update_one(
                    {"_id": entity.id}, 
                    update_doc, 
                    session=self._session
                )
            else:
                result = self.collection.update_one({"_id": entity.id}, update_doc)
            
            if result.matched_count == 0:
                raise NotFoundError(f"Entity {entity.id} not found")
            
            return entity
            
        except Exception as e:
            self.handle_storage_error("update", e)
    
    def delete(self, entity_id: str) -> bool:
        """Delete entity by ID."""
        if not self.validate_id(entity_id):
            return False
            
        try:
            if self._session:
                result = self.collection.delete_one({"_id": entity_id}, session=self._session)
            else:
                result = self.collection.delete_one({"_id": entity_id})
            
            return result.deleted_count > 0
            
        except Exception as e:
            self.handle_storage_error("delete", e)
    
    def exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        if not self.validate_id(entity_id):
            return False
            
        try:
            return self.collection.count_documents({"_id": entity_id}, limit=1) > 0
        except Exception as e:
            self.handle_storage_error("exists", e)
    
    def list(
        self,
        filters: Optional[List[QueryFilter]] = None,
        sort_by: Optional[str] = None,
        sort_order: SortOrder = SortOrder.ASC,
        pagination: Optional[Pagination] = None
    ) -> Union[List[T], PaginatedResult[T]]:
        """List entities with filtering and pagination."""
        try:
            # Build filter
            mongo_filter = self._build_filter(filters)
            
            # Build sort
            sort_spec = []
            if sort_by:
                direction = ASCENDING if sort_order == SortOrder.ASC else DESCENDING
                sort_spec.append((sort_by, direction))
            else:
                sort_spec.append(("created_at", DESCENDING))
            
            # Handle pagination
            if pagination:
                # Get total count
                total = self.collection.count_documents(mongo_filter)
                
                # Get paginated results
                cursor = self.collection.find(mongo_filter).sort(sort_spec)
                cursor = cursor.skip(pagination.offset).limit(pagination.limit)
                
                docs = list(cursor)
                entities = []
                for doc in docs:
                    doc.pop('_id', None)  # Remove MongoDB _id
                    entities.append(self.deserialize_entity(doc, self.entity_class))
                
                return PaginatedResult(
                    items=entities,
                    total=total,
                    page=pagination.page,
                    per_page=pagination.per_page
                )
            else:
                # No pagination, return all results
                cursor = self.collection.find(mongo_filter).sort(sort_spec)
                docs = list(cursor)
                
                entities = []
                for doc in docs:
                    doc.pop('_id', None)  # Remove MongoDB _id
                    entities.append(self.deserialize_entity(doc, self.entity_class))
                
                return entities
                
        except Exception as e:
            self.handle_storage_error("list", e)
    
    def count(self, filters: Optional[List[QueryFilter]] = None) -> int:
        """Count entities matching filters."""
        try:
            mongo_filter = self._build_filter(filters)
            return self.collection.count_documents(mongo_filter)
        except Exception as e:
            self.handle_storage_error("count", e)
    
    def bulk_create(self, entities: List[T]) -> List[T]:
        """Create multiple entities."""
        if not entities:
            return []
            
        try:
            docs = []
            for entity in entities:
                # Generate ID if not present
                if not hasattr(entity, 'id') or not entity.id:
                    entity.id = self.generate_id()
                
                # Serialize entity
                data = self.serialize_entity(entity)
                data = self.add_timestamps(data)
                data['_id'] = entity.id
                docs.append(data)
            
            # Bulk insert
            if self._session:
                self.collection.insert_many(docs, session=self._session)
            else:
                self.collection.insert_many(docs)
            
            return entities
            
        except Exception as e:
            self.handle_storage_error("bulk_create", e)
    
    def bulk_update(self, entities: List[T]) -> List[T]:
        """Update multiple entities."""
        if not entities:
            return []
            
        try:
            operations = []
            for entity in entities:
                if not hasattr(entity, 'id'):
                    raise StorageError("Entity must have an id for update")
                
                data = self.serialize_entity(entity)
                data = self.add_timestamps(data, update=True)
                
                operations.append(
                    pymongo.UpdateOne(
                        {"_id": entity.id},
                        {"$set": data, "$inc": {"_version": 1}}
                    )
                )
            
            # Bulk update
            if self._session:
                self.collection.bulk_write(operations, session=self._session)
            else:
                self.collection.bulk_write(operations)
            
            return entities
            
        except Exception as e:
            self.handle_storage_error("bulk_update", e)
    
    def bulk_delete(self, entity_ids: List[str]) -> int:
        """Delete multiple entities."""
        if not entity_ids:
            return 0
            
        try:
            if self._session:
                result = self.collection.delete_many(
                    {"_id": {"$in": entity_ids}}, 
                    session=self._session
                )
            else:
                result = self.collection.delete_many({"_id": {"$in": entity_ids}})
            
            return result.deleted_count
            
        except Exception as e:
            self.handle_storage_error("bulk_delete", e)
    
    def search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        pagination: Optional[Pagination] = None
    ) -> Union[List[T], PaginatedResult[T]]:
        """Full-text search using MongoDB text search."""
        try:
            # Use MongoDB text search if available, otherwise regex search
            search_filter = {"$text": {"$search": query}}
            
            if pagination:
                # Get total count (text search count is approximate)
                total = self.collection.count_documents(search_filter)
                
                # Get paginated results with text score sorting
                cursor = self.collection.find(
                    search_filter,
                    {"score": {"$meta": "textScore"}}
                ).sort([("score", {"$meta": "textScore"})])
                
                cursor = cursor.skip(pagination.offset).limit(pagination.limit)
                
                docs = list(cursor)
                entities = []
                for doc in docs:
                    doc.pop('_id', None)
                    doc.pop('score', None)  # Remove text score
                    entities.append(self.deserialize_entity(doc, self.entity_class))
                
                return PaginatedResult(
                    items=entities,
                    total=total,
                    page=pagination.page,
                    per_page=pagination.per_page
                )
            else:
                # No pagination
                cursor = self.collection.find(
                    search_filter,
                    {"score": {"$meta": "textScore"}}
                ).sort([("score", {"$meta": "textScore"})])
                
                docs = list(cursor)
                entities = []
                for doc in docs:
                    doc.pop('_id', None)
                    doc.pop('score', None)  # Remove text score
                    entities.append(self.deserialize_entity(doc, self.entity_class))
                
                return entities
                
        except Exception:
            # Fallback to regex search if text index doesn't exist
            if fields:
                # Search specific fields
                regex_filter = {
                    "$or": [
                        {field: {"$regex": query, "$options": "i"}} 
                        for field in fields
                    ]
                }
            else:
                # Search all text fields (this is a simplified approach)
                regex_filter = {
                    "$or": [
                        {"name": {"$regex": query, "$options": "i"}},
                        {"text": {"$regex": query, "$options": "i"}},
                        {"content": {"$regex": query, "$options": "i"}}
                    ]
                }
            
            if pagination:
                total = self.collection.count_documents(regex_filter)
                cursor = self.collection.find(regex_filter)
                cursor = cursor.skip(pagination.offset).limit(pagination.limit)
                
                docs = list(cursor)
                entities = [
                    self.deserialize_entity(doc, self.entity_class) 
                    for doc in docs
                ]
                
                return PaginatedResult(
                    items=entities,
                    total=total,
                    page=pagination.page,
                    per_page=pagination.per_page
                )
            else:
                docs = list(self.collection.find(regex_filter))
                return [
                    self.deserialize_entity(doc, self.entity_class) 
                    for doc in docs
                ]