from typing import Any, Dict, List, Optional, TypeVar, Generic, Type
from datetime import datetime
import json
import logging
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, JSON, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import select, insert, update, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
from sqlalchemy.pool import AsyncAdaptedQueuePool

from .base_backend import BaseStorageBackend, Entity, QueryFilter, SortOrder
from .exceptions import StorageError

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Entity)

class PostgresBackend(BaseStorageBackend, Generic[T]):
    """PostgreSQL storage backend with JSON document storage."""
    
    def __init__(
        self,
        connection_string: str,
        entity_type: Type[T],
        table_name: str,
        **kwargs
    ):
        super().__init__(entity_type)
        self.table_name = table_name
        self.engine = self._create_engine(connection_string, **kwargs)
        self.metadata = MetaData()
        self.table = self._create_table()
        
    def _create_engine(self, connection_string: str, **kwargs) -> Engine:
        """Create SQLAlchemy engine with connection pooling."""
        return create_engine(
            connection_string,
            json_serializer=json.dumps,
            json_deserializer=json.loads,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=5,
            max_overflow=10,
            pool_timeout=30,
            pool_recycle=1800,  # Recycle connections after 30 minutes
            **kwargs
        )
        
    def _create_table(self) -> Table:
        """Create table definition with JSONB storage."""
        return Table(
            self.table_name,
            self.metadata,
            Column('id', String, primary_key=True),
            Column('version', Integer, nullable=False),
            Column('data', JSONB, nullable=False),
            Column('created_at', DateTime, nullable=False),
            Column('updated_at', DateTime, nullable=False),
            Column('search_vector', JSONB),  # For full-text search
            extend_existing=True
        )
        
    async def initialize(self):
        """Create tables and indexes if they don't exist."""
        async with self.engine.begin() as conn:
            await conn.run_sync(self.metadata.create_all)
            
            # Create GIN index on JSONB data
            await conn.execute(
                f'CREATE INDEX IF NOT EXISTS idx_{self.table_name}_data_gin ON {self.table_name} USING GIN (data jsonb_path_ops)'
            )
            
            # Create GIN index for full-text search
            await conn.execute(
                f'CREATE INDEX IF NOT EXISTS idx_{self.table_name}_search ON {self.table_name} USING GIN (search_vector)'
            )
    
    @asynccontextmanager
    async def transaction(self):
        """Provide transaction context with automatic rollback on error."""
        async with self.engine.begin() as conn:
            try:
                yield conn
            except Exception as e:
                await conn.rollback()
                raise StorageError(f"Transaction failed: {str(e)}") from e
    
    async def create(self, entity: T) -> T:
        """Create new entity in database."""
        now = datetime.utcnow()
        data = self.serialize(entity)
        search_vector = self._create_search_vector(entity)
        
        async with self.transaction() as conn:
            stmt = insert(self.table).values(
                id=entity.id,
                version=1,
                data=data,
                created_at=now,
                updated_at=now,
                search_vector=search_vector
            )
            await conn.execute(stmt)
            
        return entity
    
    async def read(self, entity_id: str) -> Optional[T]:
        """Read entity by ID."""
        async with self.engine.connect() as conn:
            stmt = select(self.table).where(self.table.c.id == entity_id)
            result = await conn.execute(stmt)
            row = result.first()
            
            if row is None:
                return None
                
            return self.deserialize(row.data)
    
    async def update(self, entity: T) -> T:
        """Update existing entity."""
        now = datetime.utcnow()
        data = self.serialize(entity)
        search_vector = self._create_search_vector(entity)
        
        async with self.transaction() as conn:
            # Get current version
            stmt = select(self.table.c.version).where(self.table.c.id == entity.id)
            result = await conn.execute(stmt)
            row = result.first()
            
            if row is None:
                raise StorageError(f"Entity {entity.id} not found")
                
            new_version = row.version + 1
            
            # Update entity
            stmt = update(self.table).where(self.table.c.id == entity.id).values(
                version=new_version,
                data=data,
                updated_at=now,
                search_vector=search_vector
            )
            await conn.execute(stmt)
            
        return entity
    
    async def delete(self, entity_id: str):
        """Delete entity by ID."""
        async with self.transaction() as conn:
            stmt = delete(self.table).where(self.table.c.id == entity_id)
            await conn.execute(stmt)
    
    async def list(
        self,
        filters: Optional[List[QueryFilter]] = None,
        sort_by: Optional[str] = None,
        sort_order: SortOrder = SortOrder.ASC,
        skip: int = 0,
        limit: Optional[int] = None
    ) -> List[T]:
        """List entities with filtering, sorting and pagination."""
        stmt = select(self.table)
        
        # Apply filters
        if filters:
            for f in filters:
                stmt = stmt.where(self.table.c.data[f.field].astext == str(f.value))
        
        # Apply sorting
        if sort_by:
            col = self.table.c.data[sort_by].astext
            stmt = stmt.order_by(col.asc() if sort_order == SortOrder.ASC else col.desc())
            
        # Apply pagination
        stmt = stmt.offset(skip)
        if limit:
            stmt = stmt.limit(limit)
            
        async with self.engine.connect() as conn:
            result = await conn.execute(stmt)
            return [self.deserialize(row.data) for row in result]
    
    async def count(self, filters: Optional[List[QueryFilter]] = None) -> int:
        """Count entities matching filters."""
        stmt = select(self.table)
        
        if filters:
            for f in filters:
                stmt = stmt.where(self.table.c.data[f.field].astext == str(f.value))
                
        async with self.engine.connect() as conn:
            result = await conn.execute(stmt)
            return len(result.all())
    
    async def search(self, query: str, limit: Optional[int] = None) -> List[T]:
        """Full-text search using GIN index."""
        stmt = select(self.table).where(
            self.table.c.search_vector.op('@@')(
                func.plainto_tsquery('english', query)
            )
        )
        
        if limit:
            stmt = stmt.limit(limit)
            
        async with self.engine.connect() as conn:
            result = await conn.execute(stmt)
            return [self.deserialize(row.data) for row in result]
    
    async def bulk_create(self, entities: List[T]) -> List[T]:
        """Create multiple entities in a single transaction."""
        if not entities:
            return []
            
        now = datetime.utcnow()
        values = []
        
        for entity in entities:
            data = self.serialize(entity)
            search_vector = self._create_search_vector(entity)
            values.append({
                'id': entity.id,
                'version': 1,
                'data': data,
                'created_at': now,
                'updated_at': now,
                'search_vector': search_vector
            })
            
        async with self.transaction() as conn:
            stmt = insert(self.table)
            await conn.execute(stmt, values)
            
        return entities
    
    async def bulk_update(self, entities: List[T]) -> List[T]:
        """Update multiple entities in a single transaction."""
        if not entities:
            return []
            
        now = datetime.utcnow()
        
        async with self.transaction() as conn:
            for entity in entities:
                data = self.serialize(entity)
                search_vector = self._create_search_vector(entity)
                
                # Get current version
                stmt = select(self.table.c.version).where(self.table.c.id == entity.id)
                result = await conn.execute(stmt)
                row = result.first()
                
                if row is None:
                    raise StorageError(f"Entity {entity.id} not found")
                    
                new_version = row.version + 1
                
                # Update entity
                stmt = update(self.table).where(self.table.c.id == entity.id).values(
                    version=new_version,
                    data=data,
                    updated_at=now,
                    search_vector=search_vector
                )
                await conn.execute(stmt)
                
        return entities
    
    def _create_search_vector(self, entity: T) -> Dict[str, Any]:
        """Create search vector from entity text fields."""
        # Extract text fields for search
        search_fields = {}
        data = self.serialize(entity)
        
        def extract_text(obj: Any, prefix: str = ''):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, (str, int, float, bool)):
                        field = f"{prefix}{key}" if prefix else key
                        search_fields[field] = str(value)
                    elif isinstance(value, (dict, list)):
                        new_prefix = f"{prefix}{key}." if prefix else f"{key}."
                        extract_text(value, new_prefix)
            elif isinstance(obj, list):
                for i, value in enumerate(obj):
                    extract_text(value, f"{prefix}{i}.")
                    
        extract_text(data)
        return search_fields