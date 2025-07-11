#!/usr/bin/env python3
"""
Enhanced Persistence System for TORE Matrix Labs V1

This module provides V2-style persistence and state management for the V1 system,
enhancing the existing area storage and project persistence with modern patterns
while maintaining full backward compatibility.

Components:
- EnhancedStateManager: Global state management with V2 patterns
- ProgressPersistence: Save/restore processing progress for recovery
- BackupManager: Automatic backups and versioning
- AutoSaveManager: Automatic saving with configurable intervals
- PersistenceService: Unified interface for all persistence operations
"""

from .enhanced_state_manager import EnhancedStateManager, StateCategory, ComponentState, PersistenceLevel
from .progress_persistence import ProgressPersistence, ProgressSession, ProcessingCheckpoint

# Import backup manager components conditionally
try:
    from .backup_manager import BackupManager, BackupStrategy, BackupMetadata
    BACKUP_AVAILABLE = True
except ImportError:
    BackupManager = None
    BackupStrategy = None
    BackupMetadata = None
    BACKUP_AVAILABLE = False

from .auto_save_manager import AutoSaveManager, AutoSaveConfig
from .persistence_service import PersistenceService, PersistenceConfig, PersistenceMode

__all__ = [
    'EnhancedStateManager',
    'StateCategory', 
    'ComponentState',
    'PersistenceLevel',
    'ProgressPersistence',
    'ProgressSession',
    'ProcessingCheckpoint',
    'BackupManager',
    'BackupStrategy',
    'BackupMetadata',
    'AutoSaveManager',
    'AutoSaveConfig',
    'PersistenceService',
    'PersistenceConfig',
    'PersistenceMode'
]