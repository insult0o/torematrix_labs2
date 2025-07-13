"""
PostgreSQL backend implementation for enterprise deployments.

Provides scalable, enterprise-grade storage with advanced features.
"""

import logging
import json
import psycopg2
import psycopg2.extras
from typing import (
    Dict, Any, Optional, List, Union, Type, TypeVar,
    Iterator, Tuple, ContextManager
)
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
import threading
from urllib.parse import urlparse

from .repository import (
    Repository, AsyncRepository, QueryFilter, Pagination, 
    PaginatedResult, SortOrder, StorageError, NotFoundError, TransactionError
)
from .base_backend import BaseBackend, BackendConfig


logger = logging.getLogger(__name__)
T = TypeVar('T')


class PostgreSQLConfig(BackendConfig):
    """PostgreSQL-specific configuration."""
    
    def __init__(
        self, 
        host: str = "localhost",
        port: int = 5432,
        database: str = "torematrix",
        user: str = "torematrix",
        password: str = "",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.sslmode = kwargs.get('sslmode', 'prefer')
        self.application_name = kwargs.get('application_name', 'torematrix_v3')
        self.connection_string = kwargs.get('connection_string')
        
        # Connection pool settings
        self.min_connections = kwargs.get('min_connections', 1)
        self.max_connections = kwargs.get('max_connections', 20)
        self.connection_timeout = kwargs.get('connection_timeout', 30)
        
    def get_connection_string(self) -> str:
        """Build PostgreSQL connection string."""
        if self.connection_string:
            return self.connection_string
        
        return (
            f"postgresql://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
            f"?sslmode={self.sslmode}&application_name={self.application_name}"
        )


class PostgreSQLBackend(BaseBackend):
    """
    PostgreSQL storage backend implementation.
    
    Provides enterprise-grade storage with support for:
    - Advanced indexing and full-text search
    - JSONB for flexible schema
    - Concurrent access with proper locking
    - Streaming replication support
    """
    
    def __init__(self, config: PostgreSQLConfig):
        super().__init__(config)
        self.config: PostgreSQLConfig = config
        self._local = threading.local()
        self._table_schemas: Dict[str, Dict[str, str]] = {}
        
    @property
    def connection(self) -> psycopg2.extensions.connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self.connect()
        return self._local.connection
        
    def connect(self) -> None:
        """Establish connection to PostgreSQL database."""
        try:
            # Parse connection string if provided
            conn_string = self.config.get_connection_string()
            
            # Connect with JSON support
            self._local.connection = psycopg2.connect(
                conn_string,
                cursor_factory=psycopg2.extras.RealDictCursor,
                connect_timeout=self.config.connection_timeout
            )
            
            # Set autocommit for DDL operations
            self._local.connection.autocommit = True
            
            # Configure PostgreSQL for better performance
            with self._local.connection.cursor() as cursor:
                cursor.execute("SET search_path TO public")
                cursor.execute("SET timezone TO 'UTC'")
                cursor.execute("SET statement_timeout TO '30s'")
                
            logger.info(f"Connected to PostgreSQL: {self.config.host}:{self.config.port}/{self.config.database}")
            
        except Exception as e:
            self.handle_storage_error("connect", e)
    
    def disconnect(self) -> None:
        """Close PostgreSQL connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
            logger.info("Disconnected from PostgreSQL database")
    
    def create_table(self, table_name: str, schema: Dict[str, str]) -> None:
        """
        Create a table with the given schema.
        
        Args:
            table_name: Name of the table
            schema: Column definitions (name -> SQL type)
        """
        # Store schema for later use
        self._table_schemas[table_name] = schema
        
        # Build CREATE TABLE statement
        columns = []
        for col_name, col_type in schema.items():
            columns.append(f"{col_name} {col_type}")
        
        # Always add timestamps, version, and JSONB data column
        if 'created_at' not in schema:
            columns.append("created_at TIMESTAMPTZ DEFAULT NOW()")
        if 'updated_at' not in schema:
            columns.append("updated_at TIMESTAMPTZ DEFAULT NOW()")
        if '_version' not in schema:
            columns.append("_version INTEGER DEFAULT 1")
        if 'data' not in schema:
            columns.append("data JSONB")
            
        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {', '.join(columns)}
            )
        """
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(create_sql)
                
                # Create indexes for common queries
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_created_at 
                    ON {table_name}(created_at)
                """)
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_updated_at 
                    ON {table_name}(updated_at)
                """)
                
                # Create JSONB GIN index for fast queries
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_data_gin 
                    ON {table_name} USING GIN(data)
                """)
                
            logger.info(f"Created PostgreSQL table: {table_name}")
            
        except Exception as e:
            self.handle_storage_error("create_table", e)
    
    def _build_where_clause(self, filters: Optional[List[QueryFilter]], table_name: str) -> Tuple[str, List[Any]]:
        """Build WHERE clause from filters using JSONB operations."""
        if not filters:
            return "", []
            
        conditions = []
        params = []
        
        for f in filters:
            if f.operator == "eq":
                conditions.append(f"data->>%s = %s")
                params.extend([f.field, f.value])
            elif f.operator == "ne":
                conditions.append(f"data->>%s != %s")
                params.extend([f.field, f.value])
            elif f.operator == "gt":
                conditions.append(f"(data->>%s)::numeric > %s")
                params.extend([f.field, f.value])
            elif f.operator == "lt":
                conditions.append(f"(data->>%s)::numeric < %s")
                params.extend([f.field, f.value])
            elif f.operator == "gte":
                conditions.append(f"(data->>%s)::numeric >= %s")
                params.extend([f.field, f.value])
            elif f.operator == "lte":
                conditions.append(f"(data->>%s)::numeric <= %s")
                params.extend([f.field, f.value])
            elif f.operator == "in":
                placeholders = ",".join(["%s"] * len(f.value))
                conditions.append(f"data->>%s IN ({placeholders})")
                params.append(f.field)
                params.extend(f.value)
            elif f.operator == "like":
                conditions.append(f"data->>%s LIKE %s")
                params.extend([f.field, f.value])
            elif f.operator == "contains":
                conditions.append(f"data->>%s ILIKE %s")
                params.extend([f.field, f"%{f.value}%"])
            else:
                raise StorageError(f"Unsupported operator: {f.operator}")
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        return where_clause, params
    
    @contextmanager
    def transaction(self):
        """Transaction context manager."""
        # Disable autocommit for transaction
        self.connection.autocommit = False
        
        try:
            self._in_transaction = True
            yield
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            raise TransactionError(f"Transaction failed: {e}")
        finally:
            self._in_transaction = False
            self.connection.autocommit = True
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[List[Any]] = None,
        fetch_one: bool = False
    ) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
        """Execute a query and return results."""
        with self.connection.cursor() as cursor:
            try:
                cursor.execute(query, params or [])
                
                if query.strip().upper().startswith("SELECT"):
                    if fetch_one:
                        row = cursor.fetchone()
                        return dict(row) if row else None
                    else:
                        rows = cursor.fetchall()
                        return [dict(row) for row in rows]
                else:
                    # For INSERT/UPDATE/DELETE
                    return None
                    
            except Exception as e:
                self.handle_storage_error("execute_query", e)
    
    def create_full_text_index(self, table_name: str, columns: List[str]) -> None:
        """Create full-text search index using PostgreSQL's tsvector."""
        try:
            with self.connection.cursor() as cursor:
                # Create tsvector column
                tsvector_col = f"{table_name}_search_vector"
                
                cursor.execute(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN IF NOT EXISTS {tsvector_col} TSVECTOR
                """)
                
                # Create function to update tsvector
                update_function = f"""
                    CREATE OR REPLACE FUNCTION update_{table_name}_search_vector()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.{tsvector_col} := to_tsvector('english', 
                            COALESCE(NEW.data->>'{columns[0]}', '') || ' ' ||
                            COALESCE(NEW.data->>'{columns[1] if len(columns) > 1 else columns[0]}', '')
                        );
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                """
                cursor.execute(update_function)
                
                # Create trigger
                cursor.execute(f"""
                    DROP TRIGGER IF EXISTS {table_name}_search_trigger ON {table_name};
                    CREATE TRIGGER {table_name}_search_trigger
                    BEFORE INSERT OR UPDATE ON {table_name}
                    FOR EACH ROW EXECUTE FUNCTION update_{table_name}_search_vector();
                """)
                
                # Create GIN index on tsvector
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{table_name}_search 
                    ON {table_name} USING GIN({tsvector_col})
                """)
                
                logger.info(f"Created full-text search index for {table_name}")
                
        except Exception as e:
            self.handle_storage_error("create_full_text_index", e)
    
    def vacuum_analyze(self, table_name: Optional[str] = None) -> None:
        """Run VACUUM ANALYZE to optimize performance."""
        try:
            with self.connection.cursor() as cursor:
                if table_name:
                    cursor.execute(f"VACUUM ANALYZE {table_name}")
                    logger.info(f"Vacuumed table: {table_name}")
                else:
                    cursor.execute("VACUUM ANALYZE")
                    logger.info("Vacuumed all tables")
        except Exception as e:
            self.handle_storage_error("vacuum_analyze", e)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get PostgreSQL statistics."""
        stats = super().get_statistics()
        
        if self.is_connected():
            with self.connection.cursor() as cursor:
                # Get database size
                cursor.execute("""
                    SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
                """)
                result = cursor.fetchone()
                stats['database_size'] = result['db_size'] if result else 'unknown'
                
                # Get table information
                cursor.execute("""
                    SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del
                    FROM pg_stat_user_tables
                    WHERE schemaname = 'public'
                """)
                tables = cursor.fetchall()
                
                stats['tables'] = {}
                for table in tables:
                    table_name = table['tablename']
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                    count = cursor.fetchone()['count']
                    
                    stats['tables'][table_name] = {
                        'row_count': count,
                        'inserts': table['n_tup_ins'],
                        'updates': table['n_tup_upd'],
                        'deletes': table['n_tup_del']
                    }
                
        return stats
    
    def create_backup(self, table_name: Optional[str] = None) -> Path:
        """Create backup using pg_dump."""
        if not self.config.backup_enabled:
            return None
            
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        if table_name:
            backup_path = self.config.backup_path / f"{table_name}_{timestamp}.sql"
            cmd = f"pg_dump --table={table_name} {self.config.get_connection_string()}"
        else:
            backup_path = self.config.backup_path / f"database_{timestamp}.sql"
            cmd = f"pg_dump {self.config.get_connection_string()}"
        
        try:
            import subprocess
            with open(backup_path, 'w') as f:
                subprocess.run(cmd.split(), stdout=f, check=True)
            
            logger.info(f"Created PostgreSQL backup: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None


class PostgreSQLRepository(Repository[T], PostgreSQLBackend):
    """
    PostgreSQL implementation of the Repository interface.
    
    Uses JSONB for flexible schema while maintaining query performance.
    """
    
    def __init__(self, config: PostgreSQLConfig, entity_class: Type[T], table_name: str):
        PostgreSQLBackend.__init__(self, config)
        self.entity_class = entity_class
        self.table_name = table_name
        
        # Auto-create table
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Ensure the table exists for this entity."""
        schema = {
            "id": "TEXT PRIMARY KEY",
        }
        self.create_table(self.table_name, schema)
    
    def create(self, entity: T) -> T:
        """Create a new entity."""
        # Generate ID if not present
        if not hasattr(entity, 'id') or not entity.id:
            entity.id = self.generate_id()
        
        # Serialize entity
        data = self.serialize_entity(entity)
        data = self.add_timestamps(data)
        
        # Store as JSONB
        query = f"""
            INSERT INTO {self.table_name} (id, data, created_at, updated_at) 
            VALUES (%s, %s, %s, %s)
        """
        params = [
            entity.id, 
            json.dumps(data),
            data['created_at'],
            data['updated_at']
        ]
        
        self.execute_query(query, params)
        return entity
    
    def get(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        if not self.validate_id(entity_id):
            return None
            
        query = f"SELECT data FROM {self.table_name} WHERE id = %s"
        result = self.execute_query(query, [entity_id], fetch_one=True)
        
        if result:
            data = result['data'] if isinstance(result['data'], dict) else json.loads(result['data'])
            return self.deserialize_entity(data, self.entity_class)
        return None
    
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
        
        query = f"""
            UPDATE {self.table_name} 
            SET data = %s, updated_at = %s, _version = _version + 1
            WHERE id = %s
        """
        params = [json.dumps(data), data['updated_at'], entity.id]
        
        self.execute_query(query, params)
        return entity
    
    def delete(self, entity_id: str) -> bool:
        """Delete entity by ID."""
        if not self.validate_id(entity_id):
            return False
            
        query = f"DELETE FROM {self.table_name} WHERE id = %s"
        self.execute_query(query, [entity_id])
        
        return not self.exists(entity_id)
    
    def exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        if not self.validate_id(entity_id):
            return False
            
        query = f"SELECT 1 FROM {self.table_name} WHERE id = %s LIMIT 1"
        result = self.execute_query(query, [entity_id], fetch_one=True)
        return result is not None
    
    def list(
        self,
        filters: Optional[List[QueryFilter]] = None,
        sort_by: Optional[str] = None,
        sort_order: SortOrder = SortOrder.ASC,
        pagination: Optional[Pagination] = None
    ) -> Union[List[T], PaginatedResult[T]]:
        """List entities with filtering and pagination."""
        base_query = f"SELECT data FROM {self.table_name}"
        count_query = f"SELECT COUNT(*) as total FROM {self.table_name}"
        
        # Add WHERE clause
        where_clause, params = self._build_where_clause(filters, self.table_name)
        base_query += where_clause
        count_query += where_clause
        
        # Add ORDER BY
        if sort_by:
            base_query += f" ORDER BY data->>%s {sort_order.value}"
            params.append(sort_by)
        else:
            base_query += " ORDER BY created_at DESC"
            
        # Handle pagination
        if pagination:
            # Get total count
            count_result = self.execute_query(count_query, params[:len(params) - (1 if sort_by else 0)], fetch_one=True)
            total = count_result['total']
            
            # Add LIMIT and OFFSET
            base_query += f" LIMIT %s OFFSET %s"
            params.extend([pagination.limit, pagination.offset])
            
            # Execute query
            results = self.execute_query(base_query, params)
            entities = [
                self.deserialize_entity(
                    r['data'] if isinstance(r['data'], dict) else json.loads(r['data']), 
                    self.entity_class
                )
                for r in results
            ]
            
            return PaginatedResult(
                items=entities,
                total=total,
                page=pagination.page,
                per_page=pagination.per_page
            )
        else:
            # No pagination, return all results
            results = self.execute_query(base_query, params)
            return [
                self.deserialize_entity(
                    r['data'] if isinstance(r['data'], dict) else json.loads(r['data']), 
                    self.entity_class
                )
                for r in results
            ]
    
    def count(self, filters: Optional[List[QueryFilter]] = None) -> int:
        """Count entities matching filters."""
        query = f"SELECT COUNT(*) as total FROM {self.table_name}"
        where_clause, params = self._build_where_clause(filters, self.table_name)
        query += where_clause
        
        result = self.execute_query(query, params, fetch_one=True)
        return result['total']
    
    def bulk_create(self, entities: List[T]) -> List[T]:
        """Create multiple entities."""
        with self.transaction():
            created = []
            for entity in entities:
                created.append(self.create(entity))
            return created
    
    def bulk_update(self, entities: List[T]) -> List[T]:
        """Update multiple entities."""
        with self.transaction():
            updated = []
            for entity in entities:
                updated.append(self.update(entity))
            return updated
    
    def bulk_delete(self, entity_ids: List[str]) -> int:
        """Delete multiple entities."""
        if not entity_ids:
            return 0
            
        placeholders = ",".join(["%s"] * len(entity_ids))
        query = f"DELETE FROM {self.table_name} WHERE id IN ({placeholders})"
        
        with self.transaction():
            with self.connection.cursor() as cursor:
                cursor.execute(query, entity_ids)
                return cursor.rowcount
    
    def search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        pagination: Optional[Pagination] = None
    ) -> Union[List[T], PaginatedResult[T]]:
        """Full-text search using PostgreSQL's text search."""
        # Use JSONB containment for simple search
        search_query = f"""
            SELECT data FROM {self.table_name}
            WHERE data::text ILIKE %s
            ORDER BY updated_at DESC
        """
        
        params = [f"%{query}%"]
        
        if pagination:
            count_query = f"""
                SELECT COUNT(*) as total FROM {self.table_name}
                WHERE data::text ILIKE %s
            """
            count_result = self.execute_query(count_query, params, fetch_one=True)
            total = count_result['total']
            
            search_query += f" LIMIT %s OFFSET %s"
            params.extend([pagination.limit, pagination.offset])
            
            results = self.execute_query(search_query, params)
            entities = [
                self.deserialize_entity(
                    r['data'] if isinstance(r['data'], dict) else json.loads(r['data']), 
                    self.entity_class
                )
                for r in results
            ]
            
            return PaginatedResult(
                items=entities,
                total=total,
                page=pagination.page,
                per_page=pagination.per_page
            )
        else:
            results = self.execute_query(search_query, params)
            return [
                self.deserialize_entity(
                    r['data'] if isinstance(r['data'], dict) else json.loads(r['data']), 
                    self.entity_class
                )
                for r in results
            ]