#!/usr/bin/env python3
"""
Progress Persistence for TORE Matrix Labs V1 Enhancement

This module provides progress saving and restoration capabilities for the V1 system,
allowing users to recover from interruptions and continue processing where they left off.
"""

import logging
import json
import threading
import time
import shutil
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import hashlib


class ProcessingStage(Enum):
    """Stages of document processing."""
    INITIAL = "initial"
    LOADING = "loading"
    MANUAL_VALIDATION = "manual_validation"
    AREA_SELECTION = "area_selection"
    PROCESSING = "processing"
    EXTRACTION = "extraction"
    QUALITY_ASSESSMENT = "quality_assessment"
    QA_VALIDATION = "qa_validation"
    PAGE_VALIDATION = "page_validation"
    POST_PROCESSING = "post_processing"
    EXPORT = "export"
    COMPLETED = "completed"
    FAILED = "failed"


class SessionStatus(Enum):
    """Status of a processing session."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    RECOVERED = "recovered"
    ABANDONED = "abandoned"


@dataclass
class ProcessingCheckpoint:
    """Represents a checkpoint in document processing."""
    
    checkpoint_id: str
    session_id: str
    stage: ProcessingStage
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Progress data
    document_id: str = ""
    document_path: str = ""
    current_page: int = 1
    total_pages: int = 1
    progress_percentage: float = 0.0
    
    # Processing state
    areas_selected: List[Dict[str, Any]] = field(default_factory=list)
    excluded_areas: List[Dict[str, Any]] = field(default_factory=list)
    processing_results: Dict[str, Any] = field(default_factory=dict)
    validation_data: Dict[str, Any] = field(default_factory=dict)
    quality_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Component states
    component_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Error information
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    
    # Recovery metadata
    recovery_hint: str = ""
    can_resume: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['stage'] = self.stage.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessingCheckpoint':
        """Create from dictionary."""
        checkpoint = cls(
            checkpoint_id=data['checkpoint_id'],
            session_id=data['session_id'],
            stage=ProcessingStage(data['stage']),
            document_id=data.get('document_id', ''),
            document_path=data.get('document_path', ''),
            current_page=data.get('current_page', 1),
            total_pages=data.get('total_pages', 1),
            progress_percentage=data.get('progress_percentage', 0.0),
            areas_selected=data.get('areas_selected', []),
            excluded_areas=data.get('excluded_areas', []),
            processing_results=data.get('processing_results', {}),
            validation_data=data.get('validation_data', {}),
            quality_metrics=data.get('quality_metrics', {}),
            component_states=data.get('component_states', {}),
            errors=data.get('errors', []),
            warnings=data.get('warnings', []),
            recovery_hint=data.get('recovery_hint', ''),
            can_resume=data.get('can_resume', True)
        )
        
        if 'timestamp' in data:
            checkpoint.timestamp = datetime.fromisoformat(data['timestamp'])
        
        return checkpoint


@dataclass
class ProgressSession:
    """Represents a complete processing session with checkpoints."""
    
    session_id: str
    project_path: str = ""
    status: SessionStatus = SessionStatus.ACTIVE
    
    # Session metadata
    started_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # Documents being processed
    documents: List[str] = field(default_factory=list)
    current_document: str = ""
    
    # Checkpoints
    checkpoints: List[ProcessingCheckpoint] = field(default_factory=list)
    latest_checkpoint_id: Optional[str] = None
    
    # Session statistics
    total_processing_time: float = 0.0
    documents_completed: int = 0
    documents_failed: int = 0
    
    # Recovery information
    recovery_count: int = 0
    last_recovery_at: Optional[datetime] = None
    
    def add_checkpoint(self, checkpoint: ProcessingCheckpoint):
        """Add a checkpoint to the session."""
        self.checkpoints.append(checkpoint)
        self.latest_checkpoint_id = checkpoint.checkpoint_id
        self.last_updated = datetime.now()
    
    def get_latest_checkpoint(self) -> Optional[ProcessingCheckpoint]:
        """Get the most recent checkpoint."""
        if not self.checkpoints:
            return None
        return self.checkpoints[-1]
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[ProcessingCheckpoint]:
        """Get a specific checkpoint by ID."""
        for checkpoint in self.checkpoints:
            if checkpoint.checkpoint_id == checkpoint_id:
                return checkpoint
        return None
    
    def calculate_progress(self) -> float:
        """Calculate overall session progress."""
        if not self.documents:
            return 0.0
        
        if self.status == SessionStatus.COMPLETED:
            return 100.0
        
        # Calculate based on completed documents and current progress
        document_progress = (self.documents_completed / len(self.documents)) * 100
        
        # Add current document progress
        latest_checkpoint = self.get_latest_checkpoint()
        if latest_checkpoint:
            current_doc_progress = latest_checkpoint.progress_percentage / len(self.documents)
            document_progress += current_doc_progress
        
        return min(document_progress, 100.0)
    
    def mark_completed(self):
        """Mark session as completed."""
        self.status = SessionStatus.COMPLETED
        self.completed_at = datetime.now()
        self.last_updated = self.completed_at
    
    def mark_failed(self, error_message: str = ""):
        """Mark session as failed."""
        self.status = SessionStatus.FAILED
        self.last_updated = datetime.now()
        
        # Add error to latest checkpoint
        latest_checkpoint = self.get_latest_checkpoint()
        if latest_checkpoint:
            latest_checkpoint.errors.append({
                'timestamp': self.last_updated.isoformat(),
                'message': error_message,
                'type': 'session_failure'
            })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        data['started_at'] = self.started_at.isoformat()
        data['last_updated'] = self.last_updated.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        if self.last_recovery_at:
            data['last_recovery_at'] = self.last_recovery_at.isoformat()
        
        # Convert checkpoints
        data['checkpoints'] = [cp.to_dict() for cp in self.checkpoints]
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProgressSession':
        """Create from dictionary."""
        session = cls(
            session_id=data['session_id'],
            project_path=data.get('project_path', ''),
            status=SessionStatus(data.get('status', 'active')),
            documents=data.get('documents', []),
            current_document=data.get('current_document', ''),
            latest_checkpoint_id=data.get('latest_checkpoint_id'),
            total_processing_time=data.get('total_processing_time', 0.0),
            documents_completed=data.get('documents_completed', 0),
            documents_failed=data.get('documents_failed', 0),
            recovery_count=data.get('recovery_count', 0)
        )
        
        # Parse timestamps
        if 'started_at' in data:
            session.started_at = datetime.fromisoformat(data['started_at'])
        if 'last_updated' in data:
            session.last_updated = datetime.fromisoformat(data['last_updated'])
        if data.get('completed_at'):
            session.completed_at = datetime.fromisoformat(data['completed_at'])
        if data.get('last_recovery_at'):
            session.last_recovery_at = datetime.fromisoformat(data['last_recovery_at'])
        
        # Parse checkpoints
        for checkpoint_data in data.get('checkpoints', []):
            checkpoint = ProcessingCheckpoint.from_dict(checkpoint_data)
            session.checkpoints.append(checkpoint)
        
        return session


class ProgressPersistence:
    """
    Progress persistence system for recovery and resumption.
    
    Provides capabilities to save processing progress at key points
    and restore sessions after interruptions.
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize progress persistence."""
        self.logger = logging.getLogger(__name__)
        
        # Storage configuration
        self.storage_dir = storage_dir or Path.home() / '.tore_matrix_labs' / 'progress'
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.sessions_dir = self.storage_dir / 'sessions'
        self.checkpoints_dir = self.storage_dir / 'checkpoints'
        self.backups_dir = self.storage_dir / 'backups'
        
        for directory in [self.sessions_dir, self.checkpoints_dir, self.backups_dir]:
            directory.mkdir(exist_ok=True)
        
        # Active sessions
        self.active_sessions: Dict[str, ProgressSession] = {}
        self.session_lock = threading.RLock()
        
        # Configuration
        self.auto_checkpoint_interval = 300  # 5 minutes
        self.max_checkpoints_per_session = 50
        self.session_timeout = timedelta(hours=24)
        
        # Statistics
        self.stats = {
            'sessions_created': 0,
            'sessions_recovered': 0,
            'checkpoints_created': 0,
            'recovery_attempts': 0,
            'successful_recoveries': 0
        }
        
        # Load existing sessions
        self._load_existing_sessions()
        
        # Start maintenance thread
        self._start_maintenance_thread()
        
        self.logger.info("Progress persistence initialized")
    
    def create_session(self, 
                      project_path: str,
                      documents: List[str],
                      session_id: Optional[str] = None) -> str:
        """
        Create a new processing session.
        
        Args:
            project_path: Path to the project file
            documents: List of documents to process
            session_id: Optional custom session ID
            
        Returns:
            Session ID
        """
        if session_id is None:
            session_id = self._generate_session_id(project_path, documents)
        
        session = ProgressSession(
            session_id=session_id,
            project_path=project_path,
            documents=documents
        )
        
        with self.session_lock:
            self.active_sessions[session_id] = session
        
        # Save session
        self._save_session(session)
        
        self.stats['sessions_created'] += 1
        self.logger.info(f"Created progress session: {session_id}")
        
        return session_id
    
    def create_checkpoint(self,
                         session_id: str,
                         stage: ProcessingStage,
                         document_id: str = "",
                         document_path: str = "",
                         current_page: int = 1,
                         total_pages: int = 1,
                         progress_percentage: float = 0.0,
                         additional_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a processing checkpoint.
        
        Args:
            session_id: Session to create checkpoint for
            stage: Current processing stage
            document_id: ID of current document
            document_path: Path to current document
            current_page: Current page number
            total_pages: Total number of pages
            progress_percentage: Progress percentage for current document
            additional_data: Additional checkpoint data
            
        Returns:
            Checkpoint ID
        """
        with self.session_lock:
            if session_id not in self.active_sessions:
                self.logger.error(f"Session {session_id} not found")
                return ""
            
            session = self.active_sessions[session_id]
        
        # Generate checkpoint ID
        checkpoint_id = self._generate_checkpoint_id(session_id, stage)
        
        # Create checkpoint
        checkpoint = ProcessingCheckpoint(
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            stage=stage,
            document_id=document_id,
            document_path=document_path,
            current_page=current_page,
            total_pages=total_pages,
            progress_percentage=progress_percentage
        )
        
        # Add additional data
        if additional_data:
            for key, value in additional_data.items():
                if hasattr(checkpoint, key):
                    setattr(checkpoint, key, value)
                else:
                    checkpoint.component_states[key] = value
        
        # Add checkpoint to session
        session.add_checkpoint(checkpoint)
        
        # Limit number of checkpoints
        if len(session.checkpoints) > self.max_checkpoints_per_session:
            # Remove oldest checkpoints, keeping important ones
            session.checkpoints = self._keep_important_checkpoints(session.checkpoints)
        
        # Save checkpoint and session
        self._save_checkpoint(checkpoint)
        self._save_session(session)
        
        self.stats['checkpoints_created'] += 1
        self.logger.debug(f"Created checkpoint: {checkpoint_id} for stage {stage.value}")
        
        return checkpoint_id
    
    def get_session(self, session_id: str) -> Optional[ProgressSession]:
        """Get a processing session."""
        with self.session_lock:
            return self.active_sessions.get(session_id)
    
    def get_recoverable_sessions(self) -> List[ProgressSession]:
        """Get sessions that can be recovered."""
        recoverable = []
        
        # Check all session files
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                
                session = ProgressSession.from_dict(session_data)
                
                # Check if session is recoverable
                if (session.status in [SessionStatus.ACTIVE, SessionStatus.PAUSED] and
                    session.get_latest_checkpoint() and
                    session.get_latest_checkpoint().can_resume):
                    recoverable.append(session)
                    
            except Exception as e:
                self.logger.error(f"Error reading session file {session_file}: {e}")
        
        return recoverable
    
    def recover_session(self, session_id: str) -> Optional[ProgressSession]:
        """
        Recover a session from disk.
        
        Args:
            session_id: Session to recover
            
        Returns:
            Recovered session or None
        """
        try:
            session_file = self.sessions_dir / f"{session_id}.json"
            if not session_file.exists():
                self.logger.error(f"Session file not found: {session_file}")
                return None
            
            # Load session
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            session = ProgressSession.from_dict(session_data)
            
            # Check if recovery is possible
            latest_checkpoint = session.get_latest_checkpoint()
            if not latest_checkpoint or not latest_checkpoint.can_resume:
                self.logger.warning(f"Session {session_id} cannot be resumed")
                return None
            
            # Update session status
            session.status = SessionStatus.RECOVERED
            session.recovery_count += 1
            session.last_recovery_at = datetime.now()
            session.last_updated = datetime.now()
            
            # Add to active sessions
            with self.session_lock:
                self.active_sessions[session_id] = session
            
            # Save updated session
            self._save_session(session)
            
            self.stats['recovery_attempts'] += 1
            self.stats['successful_recoveries'] += 1
            self.stats['sessions_recovered'] += 1
            
            self.logger.info(f"Recovered session: {session_id}")
            return session
            
        except Exception as e:
            self.logger.error(f"Failed to recover session {session_id}: {e}")
            self.stats['recovery_attempts'] += 1
            return None
    
    def complete_session(self, session_id: str):
        """Mark a session as completed."""
        with self.session_lock:
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                session.mark_completed()
                self._save_session(session)
                
                # Move to completed (remove from active)
                del self.active_sessions[session_id]
                
                self.logger.info(f"Completed session: {session_id}")
    
    def fail_session(self, session_id: str, error_message: str = ""):
        """Mark a session as failed."""
        with self.session_lock:
            if session_id in self.active_sessions:
                session = self.active_sessions[session_id]
                session.mark_failed(error_message)
                self._save_session(session)
                
                self.logger.error(f"Failed session: {session_id} - {error_message}")
    
    def cleanup_old_sessions(self, older_than_days: int = 30):
        """Clean up old session files."""
        cutoff_time = datetime.now() - timedelta(days=older_than_days)
        cleaned_count = 0
        
        # Clean session files
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                if session_file.stat().st_mtime < cutoff_time.timestamp():
                    # Check if it's a completed or failed session
                    with open(session_file, 'r') as f:
                        session_data = json.load(f)
                    
                    status = SessionStatus(session_data.get('status', 'active'))
                    if status in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.ABANDONED]:
                        session_file.unlink()
                        cleaned_count += 1
                        
            except Exception as e:
                self.logger.error(f"Error cleaning session file {session_file}: {e}")
        
        # Clean checkpoint files
        for checkpoint_file in self.checkpoints_dir.glob("*.json"):
            try:
                if checkpoint_file.stat().st_mtime < cutoff_time.timestamp():
                    checkpoint_file.unlink()
                    
            except Exception as e:
                self.logger.error(f"Error cleaning checkpoint file {checkpoint_file}: {e}")
        
        if cleaned_count > 0:
            self.logger.info(f"Cleaned up {cleaned_count} old sessions")
    
    def _generate_session_id(self, project_path: str, documents: List[str]) -> str:
        """Generate a unique session ID."""
        content = f"{project_path}_{len(documents)}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _generate_checkpoint_id(self, session_id: str, stage: ProcessingStage) -> str:
        """Generate a unique checkpoint ID."""
        content = f"{session_id}_{stage.value}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def _save_session(self, session: ProgressSession):
        """Save session to disk."""
        try:
            session_file = self.sessions_dir / f"{session.session_id}.json"
            with open(session_file, 'w') as f:
                json.dump(session.to_dict(), f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save session {session.session_id}: {e}")
    
    def _save_checkpoint(self, checkpoint: ProcessingCheckpoint):
        """Save checkpoint to disk."""
        try:
            checkpoint_file = self.checkpoints_dir / f"{checkpoint.checkpoint_id}.json"
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint.to_dict(), f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint {checkpoint.checkpoint_id}: {e}")
    
    def _load_existing_sessions(self):
        """Load existing active sessions on startup."""
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
                
                session = ProgressSession.from_dict(session_data)
                
                # Only load active or paused sessions
                if session.status in [SessionStatus.ACTIVE, SessionStatus.PAUSED]:
                    with self.session_lock:
                        self.active_sessions[session.session_id] = session
                        
            except Exception as e:
                self.logger.error(f"Error loading session file {session_file}: {e}")
        
        self.logger.debug(f"Loaded {len(self.active_sessions)} active sessions")
    
    def _keep_important_checkpoints(self, checkpoints: List[ProcessingCheckpoint]) -> List[ProcessingCheckpoint]:
        """Keep important checkpoints when limiting checkpoint count."""
        # Always keep the first and last checkpoints
        if len(checkpoints) <= 2:
            return checkpoints
        
        important = [checkpoints[0], checkpoints[-1]]  # First and last
        
        # Keep checkpoints at major stages
        important_stages = {
            ProcessingStage.MANUAL_VALIDATION,
            ProcessingStage.PROCESSING,
            ProcessingStage.QA_VALIDATION,
            ProcessingStage.COMPLETED,
            ProcessingStage.FAILED
        }
        
        for checkpoint in checkpoints[1:-1]:  # Exclude first and last
            if checkpoint.stage in important_stages:
                important.append(checkpoint)
        
        # Sort by timestamp
        important.sort(key=lambda cp: cp.timestamp)
        
        # If still too many, keep evenly spaced ones
        if len(important) > self.max_checkpoints_per_session:
            step = len(important) // self.max_checkpoints_per_session
            important = important[::step]
        
        return important
    
    def _start_maintenance_thread(self):
        """Start maintenance thread for cleanup."""
        def maintenance_loop():
            while True:
                try:
                    time.sleep(3600)  # Run every hour
                    
                    # Clean up old sessions
                    self.cleanup_old_sessions()
                    
                    # Check for timed-out sessions
                    current_time = datetime.now()
                    timed_out_sessions = []
                    
                    with self.session_lock:
                        for session_id, session in self.active_sessions.items():
                            if (current_time - session.last_updated) > self.session_timeout:
                                timed_out_sessions.append(session_id)
                    
                    # Mark timed-out sessions as abandoned
                    for session_id in timed_out_sessions:
                        self.fail_session(session_id, "Session timeout")
                    
                except Exception as e:
                    self.logger.error(f"Error in progress maintenance: {e}")
        
        maintenance_thread = threading.Thread(target=maintenance_loop, daemon=True)
        maintenance_thread.start()
        self.logger.debug("Started progress maintenance thread")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get progress persistence statistics."""
        with self.session_lock:
            active_sessions_count = len(self.active_sessions)
            total_checkpoints = sum(len(session.checkpoints) for session in self.active_sessions.values())
        
        return {
            **self.stats,
            'active_sessions': active_sessions_count,
            'total_checkpoints': total_checkpoints,
            'recoverable_sessions': len(self.get_recoverable_sessions())
        }