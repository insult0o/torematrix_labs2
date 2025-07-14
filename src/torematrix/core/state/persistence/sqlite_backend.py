"""
SQLite database-based persistence backend.

This backend stores state in a SQLite database, providing transactional
persistence with better performance for frequent updates.
"""

import json
import sqlite3
import aiosqlite
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
from datetime import datetime
import gzip
import time

from .base import PersistenceBackend, PersistenceConfig

logger = logging.getLogger(__name__)


class SQLitePersistenceBackend(PersistenceBackend):
    """
    SQLite database-based persistence backend.
    
    Stores state versions in a SQLite database with proper indexing
    and transaction support for data integrity.
    """
    
    def __init__(self, config: PersistenceConfig, db_path: str = "state_storage.db"):
        super().__init__(config)
        self.db_path = Path(db_path)
        self._connection_pool: Optional[aiosqlite.Connection] = None
        self._connection_lock = asyncio.Lock()
        
    async def _do_initialize(self) -> None:
        """Initialize the SQLite database and create tables."""
        try:
            # Ensure parent directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create connection
            self._connection_pool = await aiosqlite.connect(
                self.db_path,
                timeout=30.0,
                isolation_level=None  # Use autocommit mode
            )
            
            # Enable WAL mode for better concurrency
            await self._connection_pool.execute("PRAGMA journal_mode=WAL")
            await self._connection_pool.execute("PRAGMA synchronous=NORMAL")
            await self._connection_pool.execute("PRAGMA cache_size=10000")
            await self._connection_pool.execute("PRAGMA temp_store=memory")
            
            # Create tables
            await self._create_tables()
            
            logger.info(f"SQLite persistence backend initialized at {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize SQLite backend: {e}")
            raise
    
    async def _create_tables(self) -> None:
        """Create the database tables."""
        async with self._connection_lock:
            # States table
            await self._connection_pool.execute("""
                CREATE TABLE IF NOT EXISTS states (
                    version TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    state_data TEXT NOT NULL,
                    compressed BOOLEAN DEFAULT FALSE,
                    size_bytes INTEGER DEFAULT 0,
                    checksum TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Metadata table
            await self._connection_pool.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    version TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (version) REFERENCES states (version) ON DELETE CASCADE
                )
            """)
            
            # Index table for efficient lookups
            await self._connection_pool.execute("""
                CREATE TABLE IF NOT EXISTS state_index (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    is_latest BOOLEAN DEFAULT FALSE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (version) REFERENCES states (version) ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            await self._connection_pool.execute("""
                CREATE INDEX IF NOT EXISTS idx_states_timestamp ON states (timestamp)
            """)
            
            await self._connection_pool.execute("""
                CREATE INDEX IF NOT EXISTS idx_metadata_timestamp ON metadata (timestamp)
            """)
            
            await self._connection_pool.execute("""
                CREATE INDEX IF NOT EXISTS idx_state_index_timestamp ON state_index (timestamp)
            """)
            
            await self._connection_pool.execute("""
                CREATE INDEX IF NOT EXISTS idx_state_index_latest ON state_index (is_latest)
            """)
            
            await self._connection_pool.commit()
    
    async def save_state(
        self, 
        state: Dict[str, Any], 
        version: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save state to the SQLite database.
        
        Args:
            state: The state data to save
            version: Version identifier for this state
            metadata: Optional metadata associated with this state
        """
        try:
            timestamp = time.time()
            
            # Serialize state
            state_json = json.dumps(state, ensure_ascii=False)
            state_data = state_json
            compressed = False
            
            # Compress if enabled and data is large enough
            if self.config.compression_enabled and len(state_json) > 1024:
                compressed_data = gzip.compress(state_json.encode('utf-8'))
                if len(compressed_data) < len(state_json.encode('utf-8')):
                    state_data = compressed_data.hex()  # Store as hex string
                    compressed = True
            
            # Calculate checksum (simple hash)
            checksum = str(hash(state_json))
            size_bytes = len(state_data.encode('utf-8') if not compressed else compressed_data)
            
            # Prepare metadata
            metadata_data = {
                "timestamp": timestamp,
                "size_bytes": size_bytes,
                "compressed": compressed,
                "compression_ratio": len(compressed_data) / len(state_json.encode('utf-8')) if compressed else 1.0,
                **(metadata or {})
            }
            metadata_json = json.dumps(metadata_data, ensure_ascii=False)
            
            async with self._connection_lock:
                async with self._connection_pool.execute("BEGIN TRANSACTION"):
                    # Insert or replace state
                    await self._connection_pool.execute("""
                        INSERT OR REPLACE INTO states 
                        (version, timestamp, state_data, compressed, size_bytes, checksum)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (version, timestamp, state_data, compressed, size_bytes, checksum))
                    
                    # Insert or replace metadata
                    await self._connection_pool.execute("""
                        INSERT OR REPLACE INTO metadata 
                        (version, timestamp, metadata_json)
                        VALUES (?, ?, ?)
                    """, (version, timestamp, metadata_json))
                    
                    # Update index
                    await self._update_index(version, timestamp)
                    
                    await self._connection_pool.commit()
            
            logger.debug(f"State version {version} saved to SQLite successfully")
            
        except Exception as e:
            logger.error(f"Failed to save state version {version} to SQLite: {e}")
            if self._connection_pool:
                await self._connection_pool.rollback()
            raise
    
    async def load_state(self, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Load state from the SQLite database.
        
        Args:
            version: Specific version to load, or None for latest
            
        Returns:
            The loaded state data
        """
        try:
            if version is None:
                version = await self._get_latest_version()
                if version is None:
                    return {}
            
            async with self._connection_lock:
                cursor = await self._connection_pool.execute("""
                    SELECT state_data, compressed FROM states WHERE version = ?
                """, (version,))
                
                row = await cursor.fetchone()
                if row is None:
                    raise ValueError(f"State version {version} not found")
                
                state_data, compressed = row
            
            # Deserialize state
            if compressed:
                # Decompress from hex string
                compressed_data = bytes.fromhex(state_data)
                state_json = gzip.decompress(compressed_data).decode('utf-8')
            else:
                state_json = state_data
            
            state = json.loads(state_json)
            
            logger.debug(f"State version {version} loaded from SQLite successfully")
            return state
            
        except Exception as e:
            logger.error(f"Failed to load state version {version} from SQLite: {e}")
            raise
    
    async def list_versions(self) -> List[str]:
        """
        List all saved state versions.
        
        Returns:
            List of version identifiers, sorted by creation time
        """
        try:
            async with self._connection_lock:
                cursor = await self._connection_pool.execute("""
                    SELECT version FROM state_index 
                    ORDER BY timestamp ASC
                """)
                
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to list versions from SQLite: {e}")
            return []
    
    async def delete_version(self, version: str) -> bool:
        """
        Delete a specific state version.
        
        Args:
            version: Version identifier to delete
            
        Returns:
            True if version was deleted, False if it didn't exist
        """
        try:
            async with self._connection_lock:
                async with self._connection_pool.execute("BEGIN TRANSACTION"):
                    # Check if version exists
                    cursor = await self._connection_pool.execute("""
                        SELECT COUNT(*) FROM states WHERE version = ?
                    """, (version,))
                    
                    count = (await cursor.fetchone())[0]
                    if count == 0:
                        await self._connection_pool.rollback()
                        return False
                    
                    # Delete from all tables (cascading)
                    await self._connection_pool.execute("""
                        DELETE FROM states WHERE version = ?
                    """, (version,))
                    
                    await self._connection_pool.execute("""
                        DELETE FROM metadata WHERE version = ?
                    """, (version,))
                    
                    await self._connection_pool.execute("""
                        DELETE FROM state_index WHERE version = ?
                    """, (version,))
                    
                    # Update latest version if needed
                    await self._update_latest_version()
                    
                    await self._connection_pool.commit()
            
            logger.debug(f"State version {version} deleted from SQLite")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete state version {version} from SQLite: {e}")
            if self._connection_pool:
                await self._connection_pool.rollback()
            return False
    
    async def get_metadata(self, version: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a specific version.
        
        Args:
            version: Version identifier
            
        Returns:
            Metadata dict or None if version doesn't exist
        """
        try:
            async with self._connection_lock:
                cursor = await self._connection_pool.execute("""
                    SELECT metadata_json FROM metadata WHERE version = ?
                """, (version,))
                
                row = await cursor.fetchone()
                if row is None:
                    return None
                
                metadata_json = row[0]
                return json.loads(metadata_json)
                
        except Exception as e:
            logger.error(f"Failed to get metadata for version {version} from SQLite: {e}")
            return None
    
    async def cleanup(self) -> None:
        """Clean up resources and close database connection."""
        if self._connection_pool:
            await self._connection_pool.close()
            self._connection_pool = None
        logger.debug("SQLite persistence backend cleaned up")
    
    async def _update_index(self, version: str, timestamp: float) -> None:
        """Update the state index with a new version."""
        # First, set all versions as not latest
        await self._connection_pool.execute("""
            UPDATE state_index SET is_latest = FALSE
        """)
        
        # Insert or update this version as latest
        await self._connection_pool.execute("""
            INSERT OR REPLACE INTO state_index 
            (version, timestamp, is_latest)
            VALUES (?, ?, TRUE)
        """, (version, timestamp))
    
    async def _update_latest_version(self) -> None:
        """Update the latest version flag after a deletion."""
        # Set all as not latest
        await self._connection_pool.execute("""
            UPDATE state_index SET is_latest = FALSE
        """)
        
        # Set the most recent as latest
        await self._connection_pool.execute("""
            UPDATE state_index 
            SET is_latest = TRUE 
            WHERE version = (
                SELECT version FROM state_index 
                ORDER BY timestamp DESC 
                LIMIT 1
            )
        """)
    
    async def _get_latest_version(self) -> Optional[str]:
        """Get the latest version from the index."""
        cursor = await self._connection_pool.execute("""
            SELECT version FROM state_index WHERE is_latest = TRUE LIMIT 1
        """)
        
        row = await cursor.fetchone()
        return row[0] if row else None
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            async with self._connection_lock:
                # Get total versions
                cursor = await self._connection_pool.execute("""
                    SELECT COUNT(*) FROM states
                """)
                total_versions = (await cursor.fetchone())[0]
                
                # Get total size
                cursor = await self._connection_pool.execute("""
                    SELECT SUM(size_bytes) FROM states
                """)
                total_size = (await cursor.fetchone())[0] or 0
                
                # Get compressed size
                cursor = await self._connection_pool.execute("""
                    SELECT SUM(size_bytes) FROM states WHERE compressed = TRUE
                """)
                compressed_size = (await cursor.fetchone())[0] or 0
                
                # Get latest version
                latest_version = await self._get_latest_version()
                
                # Get database file size
                db_file_size = self.db_path.stat().st_size if self.db_path.exists() else 0
                
                return {
                    "total_versions": total_versions,
                    "total_size_bytes": total_size,
                    "compressed_size_bytes": compressed_size,
                    "compression_ratio": compressed_size / total_size if total_size > 0 else 1.0,
                    "db_file_size_bytes": db_file_size,
                    "db_path": str(self.db_path),
                    "latest_version": latest_version
                }
                
        except Exception as e:
            logger.error(f"Failed to get storage stats from SQLite: {e}")
            return {}
    
    async def vacuum_database(self) -> None:
        """Vacuum the database to reclaim space after deletions."""
        try:
            async with self._connection_lock:
                await self._connection_pool.execute("VACUUM")
                await self._connection_pool.commit()
            logger.info("SQLite database vacuumed successfully")
        except Exception as e:
            logger.error(f"Failed to vacuum SQLite database: {e}")
            raise
    
    async def analyze_database(self) -> None:
        """Update database statistics for better query performance."""
        try:
            async with self._connection_lock:
                await self._connection_pool.execute("ANALYZE")
                await self._connection_pool.commit()
            logger.debug("SQLite database analyzed successfully")
        except Exception as e:
            logger.error(f"Failed to analyze SQLite database: {e}")
            raise