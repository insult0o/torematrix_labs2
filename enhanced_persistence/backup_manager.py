#!/usr/bin/env python3
"""
Backup Manager for TORE Matrix Labs V1 Enhancement

This module provides automatic backup and versioning capabilities for the V1 system,
ensuring data safety and recovery options for documents, projects, and state files.
"""

import logging
import shutil
import json
import gzip
import hashlib
import threading
import time
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    schedule = None
    SCHEDULE_AVAILABLE = False


class BackupStrategy(Enum):
    """Backup strategies for different content types."""
    INCREMENTAL = "incremental"
    FULL = "full"
    DIFFERENTIAL = "differential"
    SNAPSHOT = "snapshot"


class CompressionType(Enum):
    """Compression types for backups."""
    NONE = "none"
    GZIP = "gzip"
    AUTO = "auto"  # Choose based on file size


@dataclass
class BackupMetadata:
    """Metadata for a backup."""
    
    backup_id: str
    strategy: BackupStrategy
    created_at: datetime = field(default_factory=datetime.now)
    
    # Source information
    source_path: str = ""
    source_hash: str = ""
    source_size: int = 0
    
    # Backup information  
    backup_path: str = ""
    backup_size: int = 0
    compression: CompressionType = CompressionType.NONE
    compressed_size: int = 0
    
    # Content information
    file_count: int = 0
    directories: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    
    # Verification
    verified: bool = False
    verification_hash: str = ""
    
    # Recovery information
    recovery_time_estimate: float = 0.0  # seconds
    dependencies: List[str] = field(default_factory=list)  # Required for incremental
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['strategy'] = self.strategy.value
        data['compression'] = self.compression.value
        data['created_at'] = self.created_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BackupMetadata':
        """Create from dictionary."""
        backup = cls(
            backup_id=data['backup_id'],
            strategy=BackupStrategy(data['strategy']),
            source_path=data.get('source_path', ''),
            source_hash=data.get('source_hash', ''),
            source_size=data.get('source_size', 0),
            backup_path=data.get('backup_path', ''),
            backup_size=data.get('backup_size', 0),
            compression=CompressionType(data.get('compression', 'none')),
            compressed_size=data.get('compressed_size', 0),
            file_count=data.get('file_count', 0),
            directories=data.get('directories', []),
            files=data.get('files', []),
            verified=data.get('verified', False),
            verification_hash=data.get('verification_hash', ''),
            recovery_time_estimate=data.get('recovery_time_estimate', 0.0),
            dependencies=data.get('dependencies', [])
        )
        
        if 'created_at' in data:
            backup.created_at = datetime.fromisoformat(data['created_at'])
        
        return backup


class BackupManager:
    """
    Backup manager with automatic versioning and recovery capabilities.
    
    Provides:
    1. Automatic backups on schedule
    2. Multiple backup strategies (full, incremental, differential)
    3. Compression and verification
    4. Version management and cleanup
    5. Recovery and restoration
    """
    
    def __init__(self, backup_dir: Optional[Path] = None):
        """Initialize backup manager."""
        self.logger = logging.getLogger(__name__)
        
        # Storage configuration
        self.backup_dir = backup_dir or Path.home() / '.tore_matrix_labs' / 'backups'
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.metadata_dir = self.backup_dir / 'metadata'
        self.temp_dir = self.backup_dir / 'temp'
        
        for directory in [self.metadata_dir, self.temp_dir]:
            directory.mkdir(exist_ok=True)
        
        # Backup tracking
        self.backups: Dict[str, BackupMetadata] = {}
        self.backup_lock = threading.RLock()
        
        # Configuration
        self.max_backups_per_source = 10
        self.max_total_backups = 100
        self.compression_threshold = 1024 * 1024  # 1MB
        self.verification_enabled = True
        
        # Scheduling
        self.scheduler_thread = None
        self.scheduler_running = False
        self.scheduled_sources: Set[str] = set()
        
        # Statistics
        self.stats = {
            'backups_created': 0,
            'backups_verified': 0,
            'backups_restored': 0,
            'total_backup_size': 0,
            'compression_ratio': 0.0,
            'average_backup_time': 0.0
        }
        
        # Load existing backups
        self._load_existing_backups()
        
        # Start scheduler
        self._start_scheduler()
        
        self.logger.info("Backup manager initialized")
    
    def create_backup(self,
                     source_path: Path,
                     strategy: BackupStrategy = BackupStrategy.FULL,
                     compression: CompressionType = CompressionType.AUTO,
                     backup_id: Optional[str] = None) -> Optional[str]:
        """
        Create a backup of the specified source.
        
        Args:
            source_path: Path to backup
            strategy: Backup strategy to use
            compression: Compression type
            backup_id: Custom backup ID (generated if None)
            
        Returns:
            Backup ID if successful, None otherwise
        """
        start_time = time.time()
        
        try:
            if not source_path.exists():
                self.logger.error(f"Source path does not exist: {source_path}")
                return None
            
            # Generate backup ID
            if backup_id is None:
                backup_id = self._generate_backup_id(source_path, strategy)
            
            # Create backup metadata
            metadata = BackupMetadata(
                backup_id=backup_id,
                strategy=strategy,
                source_path=str(source_path),
                compression=compression
            )
            
            # Calculate source information
            metadata.source_hash, metadata.source_size = self._calculate_source_info(source_path)
            
            # Determine backup path
            backup_path = self.backup_dir / f"{backup_id}.backup"
            metadata.backup_path = str(backup_path)
            
            # Perform backup based on strategy
            success = False
            if strategy == BackupStrategy.FULL:
                success = self._create_full_backup(source_path, backup_path, metadata)
            elif strategy == BackupStrategy.INCREMENTAL:
                success = self._create_incremental_backup(source_path, backup_path, metadata)
            elif strategy == BackupStrategy.DIFFERENTIAL:
                success = self._create_differential_backup(source_path, backup_path, metadata)
            elif strategy == BackupStrategy.SNAPSHOT:
                success = self._create_snapshot_backup(source_path, backup_path, metadata)
            
            if not success:
                return None
            
            # Apply compression if needed
            if compression != CompressionType.NONE:
                compressed_path = self._compress_backup(backup_path, compression)
                if compressed_path:
                    metadata.compressed_size = compressed_path.stat().st_size
                    backup_path.unlink()  # Remove uncompressed version
                    metadata.backup_path = str(compressed_path)
            
            # Verify backup if enabled
            if self.verification_enabled:
                if self._verify_backup(metadata):
                    metadata.verified = True
                    self.stats['backups_verified'] += 1
            
            # Calculate backup size
            final_backup_path = Path(metadata.backup_path)
            metadata.backup_size = final_backup_path.stat().st_size
            
            # Save metadata
            self._save_backup_metadata(metadata)
            
            # Update tracking
            with self.backup_lock:
                self.backups[backup_id] = metadata
            
            # Update statistics
            backup_time = time.time() - start_time
            self._update_backup_stats(metadata, backup_time)
            
            # Cleanup old backups
            self._cleanup_old_backups(str(source_path))
            
            self.logger.info(f"Backup created: {backup_id} ({metadata.backup_size} bytes)")
            return backup_id
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return None
    
    def restore_backup(self, backup_id: str, restore_path: Path) -> bool:
        """
        Restore a backup to the specified path.
        
        Args:
            backup_id: Backup to restore
            restore_path: Path to restore to
            
        Returns:
            True if successful
        """
        try:
            with self.backup_lock:
                if backup_id not in self.backups:
                    self.logger.error(f"Backup {backup_id} not found")
                    return False
                
                metadata = self.backups[backup_id]
            
            backup_path = Path(metadata.backup_path)
            if not backup_path.exists():
                self.logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Create restore directory
            restore_path.mkdir(parents=True, exist_ok=True)
            
            # Decompress if needed
            working_path = backup_path
            if metadata.compression != CompressionType.NONE:
                working_path = self._decompress_backup(backup_path, self.temp_dir)
                if not working_path:
                    return False
            
            # Restore based on strategy
            success = False
            if metadata.strategy == BackupStrategy.FULL:
                success = self._restore_full_backup(working_path, restore_path, metadata)
            elif metadata.strategy == BackupStrategy.INCREMENTAL:
                success = self._restore_incremental_backup(backup_id, restore_path)
            elif metadata.strategy == BackupStrategy.DIFFERENTIAL:
                success = self._restore_differential_backup(backup_id, restore_path)
            elif metadata.strategy == BackupStrategy.SNAPSHOT:
                success = self._restore_snapshot_backup(working_path, restore_path, metadata)
            
            # Cleanup temporary files
            if working_path != backup_path and working_path.exists():
                if working_path.is_file():
                    working_path.unlink()
                else:
                    shutil.rmtree(working_path)
            
            if success:
                self.stats['backups_restored'] += 1
                self.logger.info(f"Backup restored: {backup_id} → {restore_path}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup {backup_id}: {e}")
            return False
    
    def schedule_automatic_backup(self,
                                 source_path: Path,
                                 interval_minutes: int = 60,
                                 strategy: BackupStrategy = BackupStrategy.INCREMENTAL):
        """Schedule automatic backups for a source."""
        if not SCHEDULE_AVAILABLE:
            self.logger.warning("Schedule library not available, automatic backups disabled")
            return
        
        source_str = str(source_path)
        
        def backup_job():
            self.create_backup(source_path, strategy)
        
        # Schedule the job
        schedule.every(interval_minutes).minutes.do(backup_job)
        
        self.scheduled_sources.add(source_str)
        self.logger.info(f"Scheduled backup every {interval_minutes} min for {source_str}")
    
    def get_backup_list(self, source_path: Optional[str] = None) -> List[BackupMetadata]:
        """Get list of backups, optionally filtered by source."""
        with self.backup_lock:
            backups = list(self.backups.values())
        
        if source_path:
            backups = [b for b in backups if b.source_path == source_path]
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda b: b.created_at, reverse=True)
        return backups
    
    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup and its metadata."""
        try:
            with self.backup_lock:
                if backup_id not in self.backups:
                    self.logger.error(f"Backup {backup_id} not found")
                    return False
                
                metadata = self.backups[backup_id]
            
            # Delete backup file
            backup_path = Path(metadata.backup_path)
            if backup_path.exists():
                backup_path.unlink()
            
            # Delete metadata file
            metadata_file = self.metadata_dir / f"{backup_id}.json"
            if metadata_file.exists():
                metadata_file.unlink()
            
            # Remove from tracking
            with self.backup_lock:
                del self.backups[backup_id]
            
            self.logger.info(f"Deleted backup: {backup_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete backup {backup_id}: {e}")
            return False
    
    def _generate_backup_id(self, source_path: Path, strategy: BackupStrategy) -> str:
        """Generate a unique backup ID."""
        content = f"{source_path}_{strategy.value}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _calculate_source_info(self, source_path: Path) -> tuple:
        """Calculate hash and size of source."""
        if source_path.is_file():
            size = source_path.stat().st_size
            with open(source_path, 'rb') as f:
                content = f.read()
            hash_value = hashlib.sha256(content).hexdigest()
            return hash_value, size
        else:
            # Directory - calculate recursive hash and size
            total_size = 0
            hash_md5 = hashlib.md5()
            
            for file_path in sorted(source_path.rglob('*')):
                if file_path.is_file():
                    try:
                        file_size = file_path.stat().st_size
                        total_size += file_size
                        
                        # Add file path and size to hash
                        relative_path = file_path.relative_to(source_path)
                        hash_md5.update(str(relative_path).encode())
                        hash_md5.update(str(file_size).encode())
                        
                    except (OSError, PermissionError):
                        continue
            
            return hash_md5.hexdigest(), total_size
    
    def _create_full_backup(self, source_path: Path, backup_path: Path, metadata: BackupMetadata) -> bool:
        """Create a full backup."""
        try:
            if source_path.is_file():
                shutil.copy2(source_path, backup_path)
                metadata.file_count = 1
                metadata.files = [source_path.name]
            else:
                # Create tar-like structure
                shutil.make_archive(str(backup_path.with_suffix('')), 'tar', source_path)
                archive_path = backup_path.with_suffix('.tar')
                archive_path.rename(backup_path)
                
                # Count files and directories
                metadata.file_count = sum(1 for _ in source_path.rglob('*') if _.is_file())
                metadata.directories = [str(d.relative_to(source_path)) for d in source_path.rglob('*') if d.is_dir()]
                metadata.files = [str(f.relative_to(source_path)) for f in source_path.rglob('*') if f.is_file()]
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create full backup: {e}")
            return False
    
    def _create_incremental_backup(self, source_path: Path, backup_path: Path, metadata: BackupMetadata) -> bool:
        """Create an incremental backup."""
        # Find the last backup for this source
        last_backup = self._find_last_backup(str(source_path))
        if not last_backup:
            # No previous backup, create full backup
            return self._create_full_backup(source_path, backup_path, metadata)
        
        # TODO: Implement incremental backup logic
        # For now, create full backup
        metadata.dependencies = [last_backup.backup_id]
        return self._create_full_backup(source_path, backup_path, metadata)
    
    def _create_differential_backup(self, source_path: Path, backup_path: Path, metadata: BackupMetadata) -> bool:
        """Create a differential backup."""
        # Find the last full backup for this source
        last_full_backup = self._find_last_full_backup(str(source_path))
        if not last_full_backup:
            # No previous full backup, create full backup
            return self._create_full_backup(source_path, backup_path, metadata)
        
        # TODO: Implement differential backup logic
        # For now, create full backup
        metadata.dependencies = [last_full_backup.backup_id]
        return self._create_full_backup(source_path, backup_path, metadata)
    
    def _create_snapshot_backup(self, source_path: Path, backup_path: Path, metadata: BackupMetadata) -> bool:
        """Create a snapshot backup."""
        return self._create_full_backup(source_path, backup_path, metadata)
    
    def _compress_backup(self, backup_path: Path, compression: CompressionType) -> Optional[Path]:
        """Compress a backup file."""
        try:
            if compression == CompressionType.AUTO:
                # Use gzip for files larger than threshold
                size = backup_path.stat().st_size
                if size < self.compression_threshold:
                    return backup_path  # No compression
                compression = CompressionType.GZIP
            
            if compression == CompressionType.GZIP:
                compressed_path = backup_path.with_suffix('.gz')
                with open(backup_path, 'rb') as f_in:
                    with gzip.open(compressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                return compressed_path
            
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Failed to compress backup: {e}")
            return None
    
    def _decompress_backup(self, backup_path: Path, temp_dir: Path) -> Optional[Path]:
        """Decompress a backup file."""
        try:
            if backup_path.suffix == '.gz':
                decompressed_path = temp_dir / backup_path.stem
                with gzip.open(backup_path, 'rb') as f_in:
                    with open(decompressed_path, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                return decompressed_path
            
            return backup_path
            
        except Exception as e:
            self.logger.error(f"Failed to decompress backup: {e}")
            return None
    
    def _verify_backup(self, metadata: BackupMetadata) -> bool:
        """Verify backup integrity."""
        try:
            backup_path = Path(metadata.backup_path)
            
            # Calculate verification hash
            with open(backup_path, 'rb') as f:
                content = f.read()
            verification_hash = hashlib.sha256(content).hexdigest()
            metadata.verification_hash = verification_hash
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to verify backup: {e}")
            return False
    
    def _restore_full_backup(self, backup_path: Path, restore_path: Path, metadata: BackupMetadata) -> bool:
        """Restore a full backup."""
        try:
            if len(metadata.files) == 1 and not metadata.directories:
                # Single file backup
                target_file = restore_path / metadata.files[0]
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_path, target_file)
            else:
                # Archive backup
                shutil.unpack_archive(backup_path, restore_path, 'tar')
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore full backup: {e}")
            return False
    
    def _restore_incremental_backup(self, backup_id: str, restore_path: Path) -> bool:
        """Restore an incremental backup chain."""
        # TODO: Implement incremental restore
        # For now, just restore as full
        metadata = self.backups[backup_id]
        backup_path = Path(metadata.backup_path)
        return self._restore_full_backup(backup_path, restore_path, metadata)
    
    def _restore_differential_backup(self, backup_id: str, restore_path: Path) -> bool:
        """Restore a differential backup."""
        # TODO: Implement differential restore
        # For now, just restore as full
        metadata = self.backups[backup_id]
        backup_path = Path(metadata.backup_path)
        return self._restore_full_backup(backup_path, restore_path, metadata)
    
    def _restore_snapshot_backup(self, backup_path: Path, restore_path: Path, metadata: BackupMetadata) -> bool:
        """Restore a snapshot backup."""
        return self._restore_full_backup(backup_path, restore_path, metadata)
    
    def _find_last_backup(self, source_path: str) -> Optional[BackupMetadata]:
        """Find the most recent backup for a source."""
        with self.backup_lock:
            source_backups = [b for b in self.backups.values() if b.source_path == source_path]
        
        if not source_backups:
            return None
        
        return max(source_backups, key=lambda b: b.created_at)
    
    def _find_last_full_backup(self, source_path: str) -> Optional[BackupMetadata]:
        """Find the most recent full backup for a source."""
        with self.backup_lock:
            full_backups = [
                b for b in self.backups.values() 
                if b.source_path == source_path and b.strategy == BackupStrategy.FULL
            ]
        
        if not full_backups:
            return None
        
        return max(full_backups, key=lambda b: b.created_at)
    
    def _save_backup_metadata(self, metadata: BackupMetadata):
        """Save backup metadata to disk."""
        try:
            metadata_file = self.metadata_dir / f"{metadata.backup_id}.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata.to_dict(), f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save backup metadata: {e}")
    
    def _load_existing_backups(self):
        """Load existing backup metadata on startup."""
        for metadata_file in self.metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    metadata_data = json.load(f)
                
                metadata = BackupMetadata.from_dict(metadata_data)
                
                # Verify backup file still exists
                backup_path = Path(metadata.backup_path)
                if backup_path.exists():
                    with self.backup_lock:
                        self.backups[metadata.backup_id] = metadata
                else:
                    # Backup file missing, remove metadata
                    metadata_file.unlink()
                    self.logger.warning(f"Removed metadata for missing backup: {metadata.backup_id}")
                    
            except Exception as e:
                self.logger.error(f"Error loading backup metadata {metadata_file}: {e}")
        
        self.logger.debug(f"Loaded {len(self.backups)} existing backups")
    
    def _cleanup_old_backups(self, source_path: str):
        """Clean up old backups for a source."""
        with self.backup_lock:
            source_backups = [b for b in self.backups.values() if b.source_path == source_path]
        
        if len(source_backups) <= self.max_backups_per_source:
            return
        
        # Sort by creation time and keep only the newest
        source_backups.sort(key=lambda b: b.created_at, reverse=True)
        backups_to_delete = source_backups[self.max_backups_per_source:]
        
        for backup in backups_to_delete:
            self.delete_backup(backup.backup_id)
    
    def _update_backup_stats(self, metadata: BackupMetadata, backup_time: float):
        """Update backup statistics."""
        self.stats['backups_created'] += 1
        self.stats['total_backup_size'] += metadata.backup_size
        
        # Update average backup time
        current_avg = self.stats['average_backup_time']
        count = self.stats['backups_created']
        new_avg = ((current_avg * (count - 1)) + backup_time) / count
        self.stats['average_backup_time'] = new_avg
        
        # Update compression ratio
        if metadata.compressed_size > 0:
            ratio = metadata.compressed_size / metadata.backup_size
            self.stats['compression_ratio'] = ratio
    
    def _start_scheduler(self):
        """Start the backup scheduler thread."""
        if not SCHEDULE_AVAILABLE:
            self.logger.debug("Schedule library not available, scheduler not started")
            return
        
        def scheduler_loop():
            while self.scheduler_running:
                try:
                    schedule.run_pending()
                    time.sleep(60)  # Check every minute
                except Exception as e:
                    self.logger.error(f"Error in backup scheduler: {e}")
        
        self.scheduler_running = True
        self.scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        self.logger.debug("Started backup scheduler")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get backup manager statistics."""
        with self.backup_lock:
            return {
                **self.stats,
                'total_backups': len(self.backups),
                'scheduled_sources': len(self.scheduled_sources)
            }
    
    def cleanup(self):
        """Clean up resources."""
        self.scheduler_running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5.0)
        
        self.logger.info("Backup manager cleanup complete")