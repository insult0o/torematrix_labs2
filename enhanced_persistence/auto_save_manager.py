#!/usr/bin/env python3
"""
Auto Save Manager for TORE Matrix Labs V1 Enhancement

This module provides automatic saving capabilities with configurable intervals,
smart change detection, and integration with the enhanced state management system.
"""

import logging
import threading
import time
import json
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from collections import defaultdict


class SaveTrigger(Enum):
    """Triggers for auto-save operations."""
    TIME_INTERVAL = "time_interval"
    CHANGE_COUNT = "change_count"
    IDLE_TIME = "idle_time"
    DOCUMENT_CHANGE = "document_change"
    PROJECT_CHANGE = "project_change"
    MANUAL = "manual"


class SavePriority(Enum):
    """Priority levels for save operations."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AutoSaveConfig:
    """Configuration for auto-save behavior."""
    
    # Timing configuration
    save_interval_seconds: int = 300  # 5 minutes
    idle_threshold_seconds: int = 30  # 30 seconds
    min_save_interval_seconds: int = 10  # Minimum 10 seconds between saves
    
    # Change-based triggers
    max_unsaved_changes: int = 50
    enable_change_counting: bool = True
    
    # Content filters
    save_document_state: bool = True
    save_project_state: bool = True
    save_ui_state: bool = True
    save_validation_state: bool = True
    
    # Performance settings
    max_concurrent_saves: int = 3
    save_timeout_seconds: int = 30
    
    # Backup settings
    create_backup_before_save: bool = True
    max_backup_versions: int = 5
    
    # Recovery settings
    enable_crash_recovery: bool = True
    recovery_file_retention_days: int = 7
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AutoSaveConfig':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class SaveOperation:
    """Represents a save operation."""
    
    operation_id: str
    trigger: SaveTrigger
    priority: SavePriority
    
    # Target information
    target_path: Path
    content_type: str = ""
    
    # Operation details
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Content information
    data_to_save: Optional[Dict[str, Any]] = None
    callback: Optional[Callable] = None
    
    # Status
    status: str = "pending"  # pending, running, completed, failed
    error_message: Optional[str] = None
    
    # Metrics
    size_bytes: int = 0
    duration_seconds: float = 0.0
    
    def is_pending(self) -> bool:
        return self.status == "pending"
    
    def is_running(self) -> bool:
        return self.status == "running"
    
    def is_completed(self) -> bool:
        return self.status == "completed"
    
    def is_failed(self) -> bool:
        return self.status == "failed"


class AutoSaveManager:
    """
    Automatic saving manager with intelligent change detection and scheduling.
    
    Features:
    1. Time-based auto-save with configurable intervals
    2. Change-based triggers (count, document events)
    3. Idle detection for optimal save timing
    4. Priority-based save queue
    5. Concurrent save operations
    6. Backup creation before saves
    7. Crash recovery file management
    """
    
    def __init__(self, config: Optional[AutoSaveConfig] = None):
        """Initialize auto-save manager."""
        self.config = config or AutoSaveConfig()
        self.logger = logging.getLogger(__name__)
        
        # Save queue and processing
        self.save_queue: List[SaveOperation] = []
        self.running_operations: Dict[str, SaveOperation] = {}
        self.completed_operations: List[SaveOperation] = []
        self.queue_lock = threading.RLock()
        
        # Change tracking
        self.change_counts: Dict[str, int] = defaultdict(int)
        self.last_activity: Dict[str, datetime] = {}
        self.last_save_time: Dict[str, datetime] = {}
        self.change_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Threading
        self.worker_threads: List[threading.Thread] = []
        self.scheduler_thread: Optional[threading.Thread] = None
        self.running = False
        self.shutdown_event = threading.Event()
        
        # Integration points
        self.state_manager = None  # Will be set by persistence service
        self.backup_manager = None  # Will be set by persistence service
        
        # Statistics
        self.stats = {
            'saves_completed': 0,
            'saves_failed': 0,
            'total_save_time': 0.0,
            'average_save_time': 0.0,
            'bytes_saved': 0,
            'changes_tracked': 0,
            'triggers_fired': {trigger.value: 0 for trigger in SaveTrigger}
        }
        
        # Start worker threads
        self._start_workers()
        
        self.logger.info("Auto-save manager initialized")
    
    def set_integrations(self, state_manager=None, backup_manager=None):
        """Set integration components."""
        self.state_manager = state_manager
        self.backup_manager = backup_manager
        self.logger.debug("Auto-save integrations set")
    
    def track_change(self, source: str, change_data: Optional[Dict[str, Any]] = None):
        """
        Track a change for auto-save triggering.
        
        Args:
            source: Source identifier for the change
            change_data: Optional data about the change
        """
        current_time = datetime.now()
        
        with self.queue_lock:
            self.change_counts[source] += 1
            self.last_activity[source] = current_time
            self.stats['changes_tracked'] += 1
        
        # Check if change count trigger should fire
        if (self.config.enable_change_counting and 
            self.change_counts[source] >= self.config.max_unsaved_changes):
            self._trigger_save(source, SaveTrigger.CHANGE_COUNT, SavePriority.HIGH)
        
        # Notify change callbacks
        for callback in self.change_callbacks.get(source, []):
            try:
                callback(source, change_data)
            except Exception as e:
                self.logger.error(f"Error in change callback: {e}")
        
        self.logger.debug(f"Tracked change for {source} (count: {self.change_counts[source]})")
    
    def register_auto_save(self,
                          source: str,
                          save_callback: Callable[[str], bool],
                          triggers: Optional[List[SaveTrigger]] = None,
                          priority: SavePriority = SavePriority.NORMAL):
        """
        Register a source for auto-saving.
        
        Args:
            source: Source identifier
            save_callback: Function to call when saving
            triggers: Save triggers to enable
            priority: Default save priority
        """
        if triggers is None:
            triggers = [SaveTrigger.TIME_INTERVAL, SaveTrigger.CHANGE_COUNT]
        
        # Store callback for this source
        if not hasattr(self, '_save_callbacks'):
            self._save_callbacks = {}
        self._save_callbacks[source] = save_callback
        
        # Initialize tracking
        with self.queue_lock:
            if source not in self.change_counts:
                self.change_counts[source] = 0
            self.last_activity[source] = datetime.now()
        
        self.logger.info(f"Registered auto-save for {source} with triggers: {[t.value for t in triggers]}")
    
    def schedule_save(self,
                     source: str,
                     trigger: SaveTrigger = SaveTrigger.MANUAL,
                     priority: SavePriority = SavePriority.NORMAL,
                     data: Optional[Dict[str, Any]] = None) -> str:
        """
        Schedule a save operation.
        
        Args:
            source: Source to save
            trigger: What triggered the save
            priority: Save priority
            data: Optional data to save
            
        Returns:
            Operation ID
        """
        operation_id = f"{source}_{int(time.time() * 1000)}"
        
        operation = SaveOperation(
            operation_id=operation_id,
            trigger=trigger,
            priority=priority,
            target_path=Path(source),
            content_type=source,
            data_to_save=data
        )
        
        with self.queue_lock:
            # Insert based on priority
            insert_index = 0
            for i, existing_op in enumerate(self.save_queue):
                if self._compare_priority(priority, existing_op.priority) <= 0:
                    insert_index = i + 1
                else:
                    break
            
            self.save_queue.insert(insert_index, operation)
            self.stats['triggers_fired'][trigger.value] += 1
        
        self.logger.debug(f"Scheduled save operation: {operation_id} ({trigger.value}, {priority.value})")
        return operation_id
    
    def force_save_all(self) -> Dict[str, bool]:
        """Force save all registered sources immediately."""
        results = {}
        
        with self.queue_lock:
            sources = list(self.change_counts.keys())
        
        for source in sources:
            operation_id = self.schedule_save(source, SaveTrigger.MANUAL, SavePriority.CRITICAL)
            
            # Wait for completion
            start_time = time.time()
            while time.time() - start_time < self.config.save_timeout_seconds:
                operation = self._find_operation(operation_id)
                if operation and operation.is_completed():
                    results[source] = True
                    break
                elif operation and operation.is_failed():
                    results[source] = False
                    break
                time.sleep(0.1)
            else:
                results[source] = False  # Timeout
        
        self.logger.info(f"Force save all completed: {sum(results.values())}/{len(results)} successful")
        return results
    
    def pause_auto_save(self, source: Optional[str] = None):
        """Pause auto-save for a source or all sources."""
        if not hasattr(self, '_paused_sources'):
            self._paused_sources = set()
        
        if source:
            self._paused_sources.add(source)
            self.logger.debug(f"Paused auto-save for {source}")
        else:
            with self.queue_lock:
                self._paused_sources.update(self.change_counts.keys())
            self.logger.info("Paused auto-save for all sources")
    
    def resume_auto_save(self, source: Optional[str] = None):
        """Resume auto-save for a source or all sources."""
        if not hasattr(self, '_paused_sources'):
            return
        
        if source:
            self._paused_sources.discard(source)
            self.logger.debug(f"Resumed auto-save for {source}")
        else:
            self._paused_sources.clear()
            self.logger.info("Resumed auto-save for all sources")
    
    def _start_workers(self):
        """Start worker threads for save operations."""
        self.running = True
        
        # Start worker threads
        for i in range(self.config.max_concurrent_saves):
            worker = threading.Thread(target=self._worker_loop, daemon=True)
            worker.start()
            self.worker_threads.append(worker)
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.debug(f"Started {len(self.worker_threads)} worker threads and scheduler")
    
    def _worker_loop(self):
        """Main worker loop for processing save operations."""
        while self.running and not self.shutdown_event.wait(0.1):
            operation = self._get_next_operation()
            if not operation:
                continue
            
            try:
                self._execute_save_operation(operation)
            except Exception as e:
                operation.status = "failed"
                operation.error_message = str(e)
                operation.completed_at = datetime.now()
                self.logger.error(f"Save operation failed: {operation.operation_id} - {e}")
                self.stats['saves_failed'] += 1
            finally:
                self._complete_operation(operation)
    
    def _scheduler_loop(self):
        """Scheduler loop for time-based triggers."""
        while self.running and not self.shutdown_event.wait(1.0):
            try:
                current_time = datetime.now()
                
                with self.queue_lock:
                    sources_to_check = list(self.change_counts.keys())
                
                for source in sources_to_check:
                    # Check if source is paused
                    if hasattr(self, '_paused_sources') and source in self._paused_sources:
                        continue
                    
                    # Check time interval trigger
                    last_save = self.last_save_time.get(source)
                    if (not last_save or 
                        (current_time - last_save).total_seconds() >= self.config.save_interval_seconds):
                        
                        # Only trigger if there are changes
                        if self.change_counts.get(source, 0) > 0:
                            self._trigger_save(source, SaveTrigger.TIME_INTERVAL, SavePriority.NORMAL)
                    
                    # Check idle time trigger
                    last_activity = self.last_activity.get(source)
                    if (last_activity and 
                        (current_time - last_activity).total_seconds() >= self.config.idle_threshold_seconds):
                        
                        # Only trigger if there are changes and we haven't saved recently
                        if (self.change_counts.get(source, 0) > 0 and
                            (not last_save or 
                             (current_time - last_save).total_seconds() >= self.config.min_save_interval_seconds)):
                            self._trigger_save(source, SaveTrigger.IDLE_TIME, SavePriority.LOW)
                
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
    
    def _trigger_save(self, source: str, trigger: SaveTrigger, priority: SavePriority):
        """Trigger a save operation for a source."""
        # Check minimum time between saves
        current_time = datetime.now()
        last_save = self.last_save_time.get(source)
        if (last_save and 
            (current_time - last_save).total_seconds() < self.config.min_save_interval_seconds):
            return
        
        self.schedule_save(source, trigger, priority)
    
    def _get_next_operation(self) -> Optional[SaveOperation]:
        """Get the next operation from the queue."""
        with self.queue_lock:
            if not self.save_queue:
                return None
            
            # Find highest priority operation that's not already running
            for i, operation in enumerate(self.save_queue):
                if operation.is_pending():
                    operation.status = "running"
                    operation.started_at = datetime.now()
                    self.running_operations[operation.operation_id] = operation
                    del self.save_queue[i]
                    return operation
        
        return None
    
    def _execute_save_operation(self, operation: SaveOperation):
        """Execute a save operation."""
        start_time = time.time()
        source = operation.content_type
        
        try:
            # Create backup if enabled and backup manager available
            if (self.config.create_backup_before_save and 
                self.backup_manager and 
                operation.target_path.exists()):
                
                backup_id = self.backup_manager.create_backup(
                    operation.target_path,
                    strategy=self.backup_manager.BackupStrategy.SNAPSHOT
                )
                if backup_id:
                    self.logger.debug(f"Created backup {backup_id} before save")
            
            # Execute save callback
            if hasattr(self, '_save_callbacks') and source in self._save_callbacks:
                callback = self._save_callbacks[source]
                success = callback(source)
                
                if success:
                    operation.status = "completed"
                    self.stats['saves_completed'] += 1
                    
                    # Reset change count
                    with self.queue_lock:
                        self.change_counts[source] = 0
                        self.last_save_time[source] = datetime.now()
                    
                else:
                    operation.status = "failed"
                    operation.error_message = "Save callback returned False"
                    self.stats['saves_failed'] += 1
            
            elif self.state_manager:
                # Use state manager for save
                success = self.state_manager.save_component_state(source)
                
                if success:
                    operation.status = "completed"
                    self.stats['saves_completed'] += 1
                    
                    with self.queue_lock:
                        self.change_counts[source] = 0
                        self.last_save_time[source] = datetime.now()
                else:
                    operation.status = "failed"
                    operation.error_message = "State manager save failed"
                    self.stats['saves_failed'] += 1
            
            else:
                operation.status = "failed"
                operation.error_message = "No save mechanism available"
                self.stats['saves_failed'] += 1
            
            # Calculate metrics
            operation.duration_seconds = time.time() - start_time
            operation.completed_at = datetime.now()
            
            # Update statistics
            self.stats['total_save_time'] += operation.duration_seconds
            if self.stats['saves_completed'] > 0:
                self.stats['average_save_time'] = (
                    self.stats['total_save_time'] / self.stats['saves_completed']
                )
            
            self.logger.debug(f"Save operation completed: {operation.operation_id} in {operation.duration_seconds:.2f}s")
            
        except Exception as e:
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.now()
            operation.duration_seconds = time.time() - start_time
            self.stats['saves_failed'] += 1
            raise
    
    def _complete_operation(self, operation: SaveOperation):
        """Complete a save operation."""
        with self.queue_lock:
            if operation.operation_id in self.running_operations:
                del self.running_operations[operation.operation_id]
            
            self.completed_operations.append(operation)
            
            # Limit completed operations history
            if len(self.completed_operations) > 100:
                self.completed_operations = self.completed_operations[-50:]
    
    def _find_operation(self, operation_id: str) -> Optional[SaveOperation]:
        """Find an operation by ID."""
        with self.queue_lock:
            # Check running operations
            if operation_id in self.running_operations:
                return self.running_operations[operation_id]
            
            # Check completed operations
            for operation in self.completed_operations:
                if operation.operation_id == operation_id:
                    return operation
            
            # Check queue
            for operation in self.save_queue:
                if operation.operation_id == operation_id:
                    return operation
        
        return None
    
    def _compare_priority(self, p1: SavePriority, p2: SavePriority) -> int:
        """Compare two priorities. Returns -1 if p1 > p2, 0 if equal, 1 if p1 < p2."""
        priority_order = {
            SavePriority.CRITICAL: 0,
            SavePriority.HIGH: 1,
            SavePriority.NORMAL: 2,
            SavePriority.LOW: 3
        }
        
        return priority_order[p1] - priority_order[p2]
    
    def get_status(self) -> Dict[str, Any]:
        """Get auto-save manager status."""
        with self.queue_lock:
            return {
                'running': self.running,
                'queue_size': len(self.save_queue),
                'running_operations': len(self.running_operations),
                'tracked_sources': len(self.change_counts),
                'total_changes': sum(self.change_counts.values()),
                'stats': self.stats.copy()
            }
    
    def get_source_status(self, source: str) -> Dict[str, Any]:
        """Get status for a specific source."""
        with self.queue_lock:
            return {
                'changes': self.change_counts.get(source, 0),
                'last_activity': self.last_activity.get(source),
                'last_save': self.last_save_time.get(source),
                'paused': hasattr(self, '_paused_sources') and source in self._paused_sources
            }
    
    def cleanup(self):
        """Clean up auto-save manager."""
        self.logger.info("Shutting down auto-save manager")
        
        # Force save all before shutdown
        self.force_save_all()
        
        # Stop threads
        self.running = False
        self.shutdown_event.set()
        
        # Wait for threads to finish
        for worker in self.worker_threads:
            if worker.is_alive():
                worker.join(timeout=5.0)
        
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5.0)
        
        self.logger.info("Auto-save manager shutdown complete")