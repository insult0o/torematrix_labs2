"""
SQLite backend implementation for local/desktop deployments.

Provides a lightweight, file-based storage solution with full SQL capabilities.
"""

import sqlite3
import json
import logging
from typing import (
    Dict, Any, Optional, List, Union, Type, TypeVar, 
    Iterator, Tuple, ContextManager
)
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
import threading

from .repository import (
    Repository, QueryFilter, Pagination, PaginatedResult,
    SortOrder, StorageError, NotFoundError, TransactionError
)
from .base_backend import BaseBackend, BackendConfig


logger = logging.getLogger(__name__)
T = TypeVar('T')


class SQLiteConfig(BackendConfig):
    """SQLite-specific configuration."""
    
    def __init__(self, database_path: Union[str, Path] = ":memory:", **kwargs):
        super().__init__(**kwargs)
        self.database_path = Path(database_path) if database_path != ":memory:" else database_path
        self.check_same_thread = kwargs.get('check_same_thread', False)
        self.timeout = kwargs.get('timeout', 30.0)
        self.isolation_level = kwargs.get('isolation_level', None)
        self.enable_foreign_keys = kwargs.get('enable_foreign_keys', True)
        self.enable_wal = kwargs.get('enable_wal', True)  # Write-Ahead Logging


class SQLiteBackend(BaseBackend):
    """
    SQLite storage backend implementation.
    
    Provides efficient local storage with full SQL capabilities,
    suitable for desktop applications and testing.
    """
    
    def __init__(self, config: SQLiteConfig):
        super().__init__(config)
        self.config: SQLiteConfig = config
        self._local = threading.local()
        self._table_schemas: Dict[str, Dict[str, str]] = {}
        
    @property
    def connection(self) -> sqlite3.Connection:
        """Get thread-local connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self.connect()
        return self._local.connection
    
    def connect(self) -> None:
        """Establish connection to SQLite database."""
        try:
            # Create directory if needed
            if self.config.database_path != ":memory:":
                self.config.database_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Connect with row factory for dict results
            self._local.connection = sqlite3.connect(
                str(self.config.database_path),
                timeout=self.config.timeout,
                check_same_thread=self.config.check_same_thread,
                isolation_level=self.config.isolation_level
            )
            
            # Enable row factory for dict-like access
            self._local.connection.row_factory = sqlite3.Row
            
            # Configure SQLite for better performance
            cursor = self._local.connection.cursor()
            
            if self.config.enable_foreign_keys:
                cursor.execute("PRAGMA foreign_keys = ON")
                
            if self.config.enable_wal and self.config.database_path != ":memory:":
                cursor.execute("PRAGMA journal_mode = WAL")
                
            # Optimize for performance
            cursor.execute("PRAGMA synchronous = NORMAL")
            cursor.execute("PRAGMA cache_size = -64000")  # 64MB cache
            cursor.execute("PRAGMA temp_store = MEMORY")
            
            cursor.close()
            
            logger.info(f"Connected to SQLite database: {self.config.database_path}")
            
        except Exception as e:
            self.handle_storage_error("connect", e)
    
    def disconnect(self) -> None:
        """Close SQLite connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None
            logger.info("Disconnected from SQLite database")
    
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
        
        # Always add timestamps and version
        if 'created_at' not in schema:
            columns.append("created_at TEXT")
        if 'updated_at' not in schema:
            columns.append("updated_at TEXT")
        if '_version' not in schema:
            columns.append("_version INTEGER DEFAULT 1")
            
        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                {', '.join(columns)}
            )
        """
        
        try:
            cursor = self.connection.cursor()
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
            
            self.connection.commit()
            cursor.close()
            
            logger.info(f"Created table: {table_name}")
            
        except Exception as e:
            self.handle_storage_error("create_table", e)
    
    def _build_where_clause(self, filters: Optional[List[QueryFilter]]) -> Tuple[str, List[Any]]:
        """Build WHERE clause from filters."""
        if not filters:
            return "", []
            
        conditions = []
        params = []
        
        for f in filters:
            if f.operator == "eq":
                conditions.append(f"{f.field} = ?")
                params.append(f.value)
            elif f.operator == "ne":
                conditions.append(f"{f.field} != ?")
                params.append(f.value)
            elif f.operator == "gt":
                conditions.append(f"{f.field} > ?")
                params.append(f.value)
            elif f.operator == "lt":
                conditions.append(f"{f.field} < ?")
                params.append(f.value)
            elif f.operator == "gte":
                conditions.append(f"{f.field} >= ?")
                params.append(f.value)
            elif f.operator == "lte":
                conditions.append(f"{f.field} <= ?")
                params.append(f.value)
            elif f.operator == "in":
                placeholders = ",".join("?" * len(f.value))
                conditions.append(f"{f.field} IN ({placeholders})")
                params.extend(f.value)
            elif f.operator == "like":
                conditions.append(f"{f.field} LIKE ?")
                params.append(f.value)
            elif f.operator == "contains":
                conditions.append(f"{f.field} LIKE ?")
                params.append(f"%{f.value}%")
            else:
                raise StorageError(f"Unsupported operator: {f.operator}")
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        return where_clause, params
    
    @contextmanager
    def transaction(self):
        """Transaction context manager."""
        cursor = self.connection.cursor()
        try:
            cursor.execute("BEGIN")
            self._in_transaction = True
            yield
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            raise TransactionError(f"Transaction failed: {e}")
        finally:
            self._in_transaction = False
            cursor.close()
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[List[Any]] = None,
        fetch_one: bool = False
    ) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
        """Execute a query and return results."""
        cursor = self.connection.cursor()
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
                # For INSERT/UPDATE/DELETE, commit if not in transaction
                if not self._in_transaction:
                    self.connection.commit()
                return None
                
        except Exception as e:
            self.handle_storage_error("execute_query", e)
        finally:
            cursor.close()
    
    def create_full_text_index(self, table_name: str, columns: List[str]) -> None:
        """Create FTS5 virtual table for full-text search."""
        try:
            # Create FTS5 virtual table
            fts_table = f"{table_name}_fts"
            columns_str = ", ".join(columns)
            
            cursor = self.connection.cursor()
            cursor.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {fts_table}
                USING fts5({columns_str}, content='{table_name}')
            """)
            
            # Create triggers to keep FTS in sync
            cursor.execute(f"""
                CREATE TRIGGER IF NOT EXISTS {table_name}_ai
                AFTER INSERT ON {table_name}
                BEGIN
                    INSERT INTO {fts_table}(rowid, {columns_str})
                    VALUES (new.rowid, {", ".join(f"new.{col}" for col in columns)});
                END
            """)
            
            cursor.execute(f"""
                CREATE TRIGGER IF NOT EXISTS {table_name}_ad
                AFTER DELETE ON {table_name}
                BEGIN
                    DELETE FROM {fts_table} WHERE rowid = old.rowid;
                END
            """)
            
            cursor.execute(f"""
                CREATE TRIGGER IF NOT EXISTS {table_name}_au
                AFTER UPDATE ON {table_name}
                BEGIN
                    UPDATE {fts_table}
                    SET {", ".join(f"{col} = new.{col}" for col in columns)}
                    WHERE rowid = new.rowid;
                END
            """)
            
            self.connection.commit()
            cursor.close()
            
            logger.info(f"Created FTS5 index for {table_name} on columns: {columns}")
            
        except Exception as e:
            self.handle_storage_error("create_full_text_index", e)
    
    def vacuum(self) -> None:
        """Optimize database file size."""
        if self.config.database_path != ":memory:":
            cursor = self.connection.cursor()
            cursor.execute("VACUUM")
            cursor.close()
            logger.info("Database vacuumed")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get SQLite statistics."""
        stats = super().get_statistics()
        
        if self.is_connected():
            cursor = self.connection.cursor()
            
            # Get database size
            if self.config.database_path != ":memory:":
                stats['database_size'] = self.config.database_path.stat().st_size
            
            # Get table information
            cursor.execute("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = cursor.fetchall()
            
            stats['tables'] = {}
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
                count = cursor.fetchone()[0]
                stats['tables'][table_name] = {
                    'row_count': count,
                    'schema': table[1]
                }
            
            cursor.close()
            
        return stats
    
    def create_backup(self, table_name: Optional[str] = None) -> Path:
        """Create backup of database or specific table."""
        if not self.config.backup_enabled or self.config.database_path == ":memory:":
            return None
            
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        if table_name:
            # Backup specific table
            backup_path = self.config.backup_path / f"{table_name}_{timestamp}.sql"
            
            cursor = self.connection.cursor()
            cursor.execute(f"SELECT sql FROM sqlite_master WHERE name=?", (table_name,))
            create_sql = cursor.fetchone()[0]
            
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            
            with open(backup_path, 'w') as f:
                f.write(f"{create_sql};\n\n")
                
                for row in rows:
                    values = ", ".join(
                        f"'{str(v).replace('\'', '\'\'')}'" if v is not None else "NULL"
                        for v in row
                    )
                    f.write(f"INSERT INTO {table_name} VALUES ({values});\n")
            
            cursor.close()
            
        else:
            # Backup entire database
            backup_path = self.config.backup_path / f"database_{timestamp}.db"
            backup_conn = sqlite3.connect(str(backup_path))
            self.connection.backup(backup_conn)
            backup_conn.close()
        
        logger.info(f"Created backup: {backup_path}")
        return backup_path


class SQLiteRepository(Repository[T], SQLiteBackend):
    """
    SQLite implementation of the Repository interface.
    
    Combines repository pattern with SQLite backend functionality.
    """
    
    def __init__(self, config: SQLiteConfig, entity_class: Type[T], table_name: str):
        SQLiteBackend.__init__(self, config)
        self.entity_class = entity_class
        self.table_name = table_name
        
        # Auto-create table based on entity class
        # This is a simplified version - in practice, you'd use proper schema generation
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Ensure the table exists for this entity."""
        # For now, create a generic table
        # In practice, this would inspect the entity class for fields
        schema = {
            "id": "TEXT PRIMARY KEY",
            "data": "TEXT NOT NULL",  # JSON serialized entity
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
        
        # Store as JSON
        json_data = json.dumps(data)
        
        query = f"INSERT INTO {self.table_name} (id, data) VALUES (?, ?)"
        self.execute_query(query, [entity.id, json_data])
        
        return entity
    
    def get(self, entity_id: str) -> Optional[T]:
        """Get entity by ID."""
        if not self.validate_id(entity_id):
            return None
            
        query = f"SELECT data FROM {self.table_name} WHERE id = ?"
        result = self.execute_query(query, [entity_id], fetch_one=True)
        
        if result:
            data = json.loads(result['data'])
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
        json_data = json.dumps(data)
        
        query = f"UPDATE {self.table_name} SET data = ? WHERE id = ?"
        self.execute_query(query, [json_data, entity.id])
        
        return entity
    
    def delete(self, entity_id: str) -> bool:
        """Delete entity by ID."""
        if not self.validate_id(entity_id):
            return False
            
        query = f"DELETE FROM {self.table_name} WHERE id = ?"
        self.execute_query(query, [entity_id])
        
        # Check if actually deleted
        return not self.exists(entity_id)
    
    def exists(self, entity_id: str) -> bool:
        """Check if entity exists."""
        if not self.validate_id(entity_id):
            return False
            
        query = f"SELECT 1 FROM {self.table_name} WHERE id = ? LIMIT 1"
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
        # For JSON data, we need to extract fields for filtering
        # This is a simplified implementation
        base_query = f"SELECT data FROM {self.table_name}"
        count_query = f"SELECT COUNT(*) as total FROM {self.table_name}"
        
        # Add ORDER BY
        if sort_by:
            base_query += f" ORDER BY json_extract(data, '$.{sort_by}') {sort_order.value}"
        else:
            base_query += " ORDER BY created_at DESC"
            
        # Handle pagination
        if pagination:
            # Get total count
            count_result = self.execute_query(count_query, fetch_one=True)
            total = count_result['total']
            
            # Add LIMIT and OFFSET
            base_query += f" LIMIT {pagination.limit} OFFSET {pagination.offset}"
            
            # Execute query
            results = self.execute_query(base_query)
            entities = [
                self.deserialize_entity(json.loads(r['data']), self.entity_class)
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
            results = self.execute_query(base_query)
            return [
                self.deserialize_entity(json.loads(r['data']), self.entity_class)
                for r in results
            ]
    
    def count(self, filters: Optional[List[QueryFilter]] = None) -> int:
        """Count entities matching filters."""
        query = f"SELECT COUNT(*) as total FROM {self.table_name}"
        result = self.execute_query(query, fetch_one=True)
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
        count = 0
        with self.transaction():
            for entity_id in entity_ids:
                if self.delete(entity_id):
                    count += 1
        return count
    
    def search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        pagination: Optional[Pagination] = None
    ) -> Union[List[T], PaginatedResult[T]]:
        """Full-text search across entities."""
        # For JSON storage, we do a simple LIKE search
        # In production, you'd use FTS5 on extracted fields
        search_query = f"""
            SELECT data FROM {self.table_name}
            WHERE data LIKE ?
            ORDER BY updated_at DESC
        """
        
        params = [f"%{query}%"]
        
        if pagination:
            count_query = f"""
                SELECT COUNT(*) as total FROM {self.table_name}
                WHERE data LIKE ?
            """
            count_result = self.execute_query(count_query, params, fetch_one=True)
            total = count_result['total']
            
            search_query += f" LIMIT {pagination.limit} OFFSET {pagination.offset}"
            results = self.execute_query(search_query, params)
            
            entities = [
                self.deserialize_entity(json.loads(r['data']), self.entity_class)
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
                self.deserialize_entity(json.loads(r['data']), self.entity_class)
                for r in results
            ]