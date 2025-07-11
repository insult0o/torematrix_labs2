#!/usr/bin/env python3
"""
Persistence Service for TORE Matrix Labs V1 Enhancement

This module provides a unified interface for all persistence operations,
integrating state management, progress persistence, backups, and auto-save
into a cohesive system for the enhanced V1 application.
"""

import logging
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
from datetime import datetime

from .enhanced_state_manager import EnhancedStateManager, StateCategory, PersistenceLevel
from .progress_persistence import ProgressPersistence, ProcessingStage, ProgressSession
from .backup_manager import BackupManager, BackupStrategy
from .auto_save_manager import AutoSaveManager, AutoSaveConfig, SaveTrigger, SavePriority


class PersistenceMode(Enum):
    """Persistence operation modes."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class PersistenceConfig:
    """Configuration for the persistence service."""
    
    # Storage paths
    base_storage_dir: Optional[Path] = None
    state_storage_dir: Optional[Path] = None
    progress_storage_dir: Optional[Path] = None
    backup_storage_dir: Optional[Path] = None
    
    # Operation mode
    mode: PersistenceMode = PersistenceMode.PRODUCTION
    
    # Feature enablement
    enable_state_management: bool = True
    enable_progress_persistence: bool = True
    enable_backups: bool = True
    enable_auto_save: bool = True
    
    # Integration settings
    integrate_with_v1_managers: bool = True
    auto_connect_widgets: bool = True
    
    # Performance settings
    max_concurrent_operations: int = 5
    operation_timeout_seconds: int = 30
    
    # Auto-save configuration
    auto_save_config: Optional[AutoSaveConfig] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['mode'] = self.mode.value
        if self.auto_save_config:
            data['auto_save_config'] = self.auto_save_config.to_dict()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersistenceConfig':
        """Create from dictionary."""
        config_data = data.copy()
        
        # Convert mode
        if 'mode' in config_data:
            config_data['mode'] = PersistenceMode(config_data['mode'])
        
        # Convert paths
        for path_key in ['base_storage_dir', 'state_storage_dir', 'progress_storage_dir', 'backup_storage_dir']:
            if path_key in config_data and config_data[path_key]:
                config_data[path_key] = Path(config_data[path_key])
        
        # Convert auto-save config
        if 'auto_save_config' in config_data and config_data['auto_save_config']:
            config_data['auto_save_config'] = AutoSaveConfig.from_dict(config_data['auto_save_config'])
        
        return cls(**config_data)


class PersistenceService:
    """
    Unified persistence service for TORE Matrix Labs V1 enhancement.
    
    This service coordinates all persistence operations and provides a single
    interface for the application to manage state, progress, backups, and auto-save.
    
    Features:
    1. Centralized state management with V2 patterns
    2. Progress persistence for recovery
    3. Automatic backups with versioning
    4. Intelligent auto-save with change detection
    5. Integration with existing V1 managers
    6. Performance monitoring and statistics
    """
    
    def __init__(self, config: Optional[PersistenceConfig] = None):
        """Initialize the persistence service."""
        self.config = config or PersistenceConfig()
        self.logger = logging.getLogger(__name__)
        
        # Setup storage directories
        self._setup_storage_directories()
        
        # Initialize core components
        self.state_manager: Optional[EnhancedStateManager] = None
        self.progress_persistence: Optional[ProgressPersistence] = None
        self.backup_manager: Optional[BackupManager] = None
        self.auto_save_manager: Optional[AutoSaveManager] = None
        
        # Integration tracking
        self.registered_components: Dict[str, Dict[str, Any]] = {}
        self.active_sessions: Dict[str, str] = {}  # component -> session_id
        
        # Operation coordination
        self.operation_lock = threading.RLock()
        self.running_operations: Dict[str, threading.Thread] = {}
        
        # Statistics
        self.stats = {
            'operations_started': 0,
            'operations_completed': 0,
            'operations_failed': 0,
            'state_updates': 0,
            'progress_checkpoints': 0,
            'backups_created': 0,
            'auto_saves': 0
        }
        
        # Initialize components
        self._initialize_components()
        
        self.logger.info(f"Persistence service initialized in {self.config.mode.value} mode")
    
    def _setup_storage_directories(self):
        """Setup storage directory structure."""
        if self.config.base_storage_dir is None:
            self.config.base_storage_dir = Path.home() / '.tore_matrix_labs'
        
        base_dir = self.config.base_storage_dir
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Set component directories if not specified
        if self.config.state_storage_dir is None:
            self.config.state_storage_dir = base_dir / 'state'
        
        if self.config.progress_storage_dir is None:
            self.config.progress_storage_dir = base_dir / 'progress'
        
        if self.config.backup_storage_dir is None:
            self.config.backup_storage_dir = base_dir / 'backups'
        
        # Create directories
        for directory in [self.config.state_storage_dir, 
                         self.config.progress_storage_dir, 
                         self.config.backup_storage_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _initialize_components(self):
        """Initialize persistence components based on configuration."""
        try:
            # Initialize state manager
            if self.config.enable_state_management:
                self.state_manager = EnhancedStateManager(self.config.state_storage_dir)
                self.logger.debug("State manager initialized")
            
            # Initialize progress persistence
            if self.config.enable_progress_persistence:
                self.progress_persistence = ProgressPersistence(self.config.progress_storage_dir)
                self.logger.debug("Progress persistence initialized")
            
            # Initialize backup manager
            if self.config.enable_backups:
                self.backup_manager = BackupManager(self.config.backup_storage_dir)
                self.logger.debug("Backup manager initialized")
            
            # Initialize auto-save manager
            if self.config.enable_auto_save:
                auto_save_config = self.config.auto_save_config or AutoSaveConfig()
                self.auto_save_manager = AutoSaveManager(auto_save_config)
                
                # Set integrations
                self.auto_save_manager.set_integrations(
                    state_manager=self.state_manager,
                    backup_manager=self.backup_manager
                )
                self.logger.debug("Auto-save manager initialized")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize persistence components: {e}")
            raise
    
    # State Management Interface
    
    def register_component(self,
                          component_id: str,
                          category: StateCategory,
                          persistence_level: PersistenceLevel = PersistenceLevel.SESSION,
                          initial_state: Optional[Dict[str, Any]] = None,
                          auto_save: bool = True) -> bool:
        """
        Register a component for state management.
        
        Args:
            component_id: Unique component identifier
            category: State category
            persistence_level: Persistence level
            initial_state: Initial state data
            auto_save: Enable auto-save for this component
            
        Returns:
            True if successful
        """
        try:
            # Register with state manager
            component_state = None
            if self.state_manager:
                component_state = self.state_manager.register_component(
                    component_id, category, persistence_level, initial_state
                )
            
            # Register with auto-save if enabled
            if auto_save and self.auto_save_manager:
                def save_callback(source: str) -> bool:
                    return self.save_component_state(source)
                
                self.auto_save_manager.register_auto_save(
                    component_id,
                    save_callback,
                    triggers=[SaveTrigger.TIME_INTERVAL, SaveTrigger.CHANGE_COUNT]
                )
            
            # Track registration
            self.registered_components[component_id] = {
                'category': category,
                'persistence_level': persistence_level,
                'auto_save': auto_save,
                'registered_at': datetime.now()
            }
            
            self.logger.debug(f"Registered component: {component_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register component {component_id}: {e}")
            return False
    
    def update_component_state(self,
                              component_id: str,
                              updates: Dict[str, Any],
                              trigger_auto_save: bool = True) -> bool:
        """Update component state."""
        try:
            # Update state manager
            success = False
            if self.state_manager:
                success = self.state_manager.update_component_state(component_id, updates)
            
            if success:
                self.stats['state_updates'] += 1
                
                # Track change for auto-save
                if trigger_auto_save and self.auto_save_manager:
                    self.auto_save_manager.track_change(component_id, updates)
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to update component state {component_id}: {e}")
            return False
    
    def get_component_state(self,
                           component_id: str,
                           key: Optional[str] = None,
                           default: Any = None) -> Any:
        """Get component state."""
        if self.state_manager:
            return self.state_manager.get_component_state(component_id, key, default)
        return default
    
    def save_component_state(self, component_id: str) -> bool:
        """Save component state to disk."""
        if self.state_manager:
            return self.state_manager.save_component_state(component_id)
        return False
    
    def create_state_snapshot(self, components: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Create a state snapshot."""
        if self.state_manager:
            return self.state_manager.create_state_snapshot(components)
        return None
    
    def restore_state_snapshot(self, snapshot: Dict[str, Any]) -> bool:
        """Restore state from snapshot."""
        if self.state_manager:
            return self.state_manager.restore_state_snapshot(snapshot)
        return False
    
    # Progress Persistence Interface
    
    def start_processing_session(self,
                                project_path: str,
                                documents: List[str],
                                session_id: Optional[str] = None) -> Optional[str]:
        """Start a new processing session."""
        if self.progress_persistence:
            session_id = self.progress_persistence.create_session(project_path, documents, session_id)
            if session_id:
                self.active_sessions['current'] = session_id
            return session_id
        return None
    
    def create_progress_checkpoint(self,
                                  session_id: str,
                                  stage: ProcessingStage,
                                  **checkpoint_data) -> Optional[str]:
        """Create a progress checkpoint."""
        if self.progress_persistence:
            checkpoint_id = self.progress_persistence.create_checkpoint(session_id, stage, **checkpoint_data)
            if checkpoint_id:
                self.stats['progress_checkpoints'] += 1
            return checkpoint_id
        return None
    
    def get_recoverable_sessions(self) -> List[ProgressSession]:
        """Get sessions that can be recovered."""
        if self.progress_persistence:
            return self.progress_persistence.get_recoverable_sessions()
        return []
    
    def recover_session(self, session_id: str) -> Optional[ProgressSession]:
        """Recover a processing session."""
        if self.progress_persistence:
            session = self.progress_persistence.recover_session(session_id)
            if session:
                self.active_sessions['current'] = session_id
            return session
        return None
    
    # Backup Interface
    
    def create_backup(self,
                     source_path: Path,
                     strategy: BackupStrategy = BackupStrategy.FULL) -> Optional[str]:
        """Create a backup."""
        if self.backup_manager:
            backup_id = self.backup_manager.create_backup(source_path, strategy)
            if backup_id:
                self.stats['backups_created'] += 1
            return backup_id
        return None
    
    def restore_backup(self, backup_id: str, restore_path: Path) -> bool:
        """Restore a backup."""
        if self.backup_manager:
            return self.backup_manager.restore_backup(backup_id, restore_path)
        return False
    
    def schedule_automatic_backup(self,
                                 source_path: Path,
                                 interval_minutes: int = 60) -> bool:
        """Schedule automatic backups."""
        if self.backup_manager:
            self.backup_manager.schedule_automatic_backup(source_path, interval_minutes)
            return True
        return False
    
    # Auto-Save Interface
    
    def force_save_all(self) -> Dict[str, bool]:
        """Force save all components immediately."""
        if self.auto_save_manager:
            results = self.auto_save_manager.force_save_all()
            self.stats['auto_saves'] += sum(results.values())
            return results
        return {}
    
    def pause_auto_save(self, component_id: Optional[str] = None):
        """Pause auto-save for a component or all components."""
        if self.auto_save_manager:
            self.auto_save_manager.pause_auto_save(component_id)
    
    def resume_auto_save(self, component_id: Optional[str] = None):
        """Resume auto-save for a component or all components."""
        if self.auto_save_manager:
            self.auto_save_manager.resume_auto_save(component_id)
    
    # Integration Helpers
    
    def integrate_v1_managers(self, **managers):
        """Integrate with V1 state managers."""
        if self.state_manager and self.config.integrate_with_v1_managers:
            self.state_manager.integrate_v1_managers(**managers)
    
    def auto_connect_widget(self, widget) -> int:
        """Auto-connect widget signals to persistence system."""
        # This would be implemented with the signal bridge
        # For now, return 0
        return 0
    
    # Utility Methods
    
    def create_project_backup(self, project_path: Path) -> Optional[str]:
        """Create a comprehensive backup of a project."""
        try:
            with self.operation_lock:
                self.stats['operations_started'] += 1
            
            # Create state snapshot
            snapshot = self.create_state_snapshot()
            
            # Create project backup
            backup_id = self.create_backup(project_path, BackupStrategy.FULL)
            
            if backup_id and snapshot:
                # Save snapshot alongside backup
                backup_dir = self.config.backup_storage_dir
                snapshot_file = backup_dir / f"{backup_id}_snapshot.json"
                
                import json
                with open(snapshot_file, 'w') as f:
                    json.dump(snapshot, f, indent=2)
                
                self.logger.info(f"Created project backup: {backup_id}")
                self.stats['operations_completed'] += 1
                return backup_id
            
            self.stats['operations_failed'] += 1
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to create project backup: {e}")
            self.stats['operations_failed'] += 1
            return None
    
    def restore_project_backup(self, backup_id: str, restore_path: Path) -> bool:
        """Restore a comprehensive project backup."""
        try:
            with self.operation_lock:
                self.stats['operations_started'] += 1
            
            # Restore backup
            success = self.restore_backup(backup_id, restore_path)
            
            if success:
                # Try to restore state snapshot
                backup_dir = self.config.backup_storage_dir
                snapshot_file = backup_dir / f"{backup_id}_snapshot.json"
                
                if snapshot_file.exists():
                    import json
                    with open(snapshot_file, 'r') as f:
                        snapshot = json.load(f)
                    
                    self.restore_state_snapshot(snapshot)
                    self.logger.info(f"Restored project backup with state: {backup_id}")
                else:
                    self.logger.info(f"Restored project backup: {backup_id}")
                
                self.stats['operations_completed'] += 1
                return True
            
            self.stats['operations_failed'] += 1
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to restore project backup: {e}")
            self.stats['operations_failed'] += 1
            return False
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all persistence components."""
        status = {
            'service': {
                'mode': self.config.mode.value,
                'components_enabled': {
                    'state_management': self.config.enable_state_management,
                    'progress_persistence': self.config.enable_progress_persistence,
                    'backups': self.config.enable_backups,
                    'auto_save': self.config.enable_auto_save
                },
                'registered_components': len(self.registered_components),
                'active_sessions': len(self.active_sessions),
                'stats': self.stats.copy()
            }
        }
        
        # Add component statuses
        if self.state_manager:
            status['state_manager'] = self.state_manager.get_statistics()
        
        if self.progress_persistence:
            status['progress_persistence'] = self.progress_persistence.get_statistics()
        
        if self.backup_manager:
            status['backup_manager'] = self.backup_manager.get_statistics()
        
        if self.auto_save_manager:
            status['auto_save_manager'] = self.auto_save_manager.get_status()
        
        return status
    
    def cleanup(self):
        """Clean up persistence service and all components."""
        self.logger.info("Starting persistence service cleanup")
        
        # Force save all before cleanup
        self.force_save_all()
        
        # Cleanup components
        if self.auto_save_manager:
            self.auto_save_manager.cleanup()
        
        if self.backup_manager:
            self.backup_manager.cleanup()
        
        if self.state_manager:
            self.state_manager.cleanup()
        
        self.logger.info("Persistence service cleanup complete")


# Convenience function for easy initialization
def create_persistence_service(mode: PersistenceMode = PersistenceMode.PRODUCTION,
                              storage_dir: Optional[Path] = None,
                              **config_kwargs) -> PersistenceService:
    """Create a persistence service with common configuration."""
    config = PersistenceConfig(
        mode=mode,
        base_storage_dir=storage_dir,
        **config_kwargs
    )
    return PersistenceService(config)