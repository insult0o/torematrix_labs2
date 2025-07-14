"""
Progress tracking system for document processing pipeline.

This module provides real-time progress tracking for individual files and
entire upload sessions, with Redis-based storage and event emission.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from dataclasses import dataclass, asdict
from collections import defaultdict
import json

import redis.asyncio as redis

from ..core.events import EventBus, ProcessingEvent, ProcessingEventTypes

logger = logging.getLogger(__name__)


@dataclass
class FileProgress:
    """Progress information for a single file."""
    file_id: str
    filename: str
    status: str
    progress: float  # 0.0 to 1.0
    current_step: str
    total_steps: int
    completed_steps: int
    session_id: Optional[str] = None
    size: int = 0
    processed_size: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    job_id: Optional[str] = None
    retry_count: int = 0
    processing_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FileProgress':
        """Create from dictionary."""
        # Convert ISO strings back to datetime
        if data.get('started_at'):
            data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return cls(**data)


@dataclass
class SessionProgress:
    """Progress information for an upload session."""
    session_id: str
    total_files: int
    processed_files: int
    failed_files: int
    cancelled_files: int
    total_size: int
    processed_size: int
    overall_progress: float
    status: str  # active, completed, failed, cancelled
    started_at: datetime
    completed_at: Optional[datetime] = None
    files: Dict[str, FileProgress] = None
    
    def __post_init__(self):
        if self.files is None:
            self.files = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        # Convert file progress objects to dicts
        data['files'] = {fid: fp.to_dict() for fid, fp in self.files.items()}
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionProgress':
        """Create from dictionary."""
        # Convert datetime strings
        data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        # Convert file progress dicts to objects
        if 'files' in data:
            data['files'] = {
                fid: FileProgress.from_dict(fp_data)
                for fid, fp_data in data['files'].items()
            }
        return cls(**data)


class ProgressTracker:
    """Tracks processing progress for files and sessions with Redis persistence."""
    
    def __init__(
        self,
        redis_client: redis.Redis,
        event_bus: Optional[EventBus] = None,
        key_prefix: str = "progress"
    ):
        self.redis = redis_client
        self.event_bus = event_bus or EventBus()
        self.key_prefix = key_prefix
        
        # Redis key templates
        self._session_key = f"{key_prefix}:session:{{session_id}}"
        self._file_key = f"{key_prefix}:file:{{file_id}}"
        self._session_files_key = f"{key_prefix}:session:{{session_id}}:files"
        
        # Local cache for performance
        self._session_cache: Dict[str, SessionProgress] = {}
        self._file_cache: Dict[str, FileProgress] = {}
        
        # Processing steps configuration
        self.default_steps = [
            "uploaded",
            "validated", 
            "queued",
            "processing",
            "completed"
        ]
    
    async def init_session(
        self,
        session_id: str,
        files: List[Dict[str, Any]],
        user_id: Optional[str] = None
    ) -> SessionProgress:
        """
        Initialize progress tracking for a new session.
        
        Args:
            session_id: Unique session identifier
            files: List of file information dicts
            user_id: Optional user identifier
            
        Returns:
            Initialized SessionProgress object
        """
        try:
            total_size = sum(f.get("size", 0) for f in files)
            
            session_progress = SessionProgress(
                session_id=session_id,
                total_files=len(files),
                processed_files=0,
                failed_files=0,
                cancelled_files=0,
                total_size=total_size,
                processed_size=0,
                overall_progress=0.0,
                status="active",
                started_at=datetime.utcnow()
            )
            
            # Initialize progress for each file
            for file_data in files:
                await self.init_file(
                    session_id=session_id,
                    file_id=file_data["file_id"],
                    filename=file_data.get("filename", "unknown"),
                    size=file_data.get("size", 0)
                )
            
            # Store session in Redis and cache
            await self._store_session(session_progress)
            self._session_cache[session_id] = session_progress
            
            # Add files to session set
            file_ids = [f["file_id"] for f in files]
            if file_ids:
                await self.redis.sadd(
                    self._session_files_key.format(session_id=session_id),
                    *file_ids
                )
                await self.redis.expire(
                    self._session_files_key.format(session_id=session_id),
                    86400  # 24 hours
                )
            
            logger.info(f"Initialized session {session_id} with {len(files)} files")
            return session_progress
            
        except Exception as e:
            logger.error(f"Failed to initialize session {session_id}: {e}")
            raise
    
    async def init_file(
        self,
        session_id: str,
        file_id: str,
        filename: str,
        size: int,
        job_id: Optional[str] = None
    ) -> FileProgress:
        """
        Initialize progress tracking for a single file.
        
        Args:
            session_id: Associated session ID
            file_id: Unique file identifier
            filename: Original filename
            size: File size in bytes
            job_id: Optional associated job ID
            
        Returns:
            Initialized FileProgress object
        """
        try:
            file_progress = FileProgress(
                file_id=file_id,
                filename=filename,
                status="uploaded",
                progress=0.0,
                current_step="uploaded",
                total_steps=len(self.default_steps),
                completed_steps=1,  # uploaded step is done
                session_id=session_id,
                size=size,
                processed_size=0,
                job_id=job_id
            )
            
            # Store in Redis and cache
            await self._store_file_progress(file_progress)
            self._file_cache[file_id] = file_progress
            
            logger.debug(f"Initialized file progress for {file_id}")
            return file_progress
            
        except Exception as e:
            logger.error(f"Failed to initialize file progress for {file_id}: {e}")
            raise
    
    async def update_file_progress(
        self,
        file_id: str,
        status: str,
        current_step: str,
        progress: Optional[float] = None,
        completed_steps: Optional[int] = None,
        error: Optional[str] = None,
        job_id: Optional[str] = None,
        processing_time: Optional[float] = None
    ) -> Optional[FileProgress]:
        """
        Update progress for a specific file.
        
        Args:
            file_id: File identifier
            status: New status
            current_step: Current processing step
            progress: Optional progress override (0.0-1.0)
            completed_steps: Number of completed steps
            error: Optional error message
            job_id: Optional job ID
            processing_time: Optional processing time in seconds
            
        Returns:
            Updated FileProgress object or None if not found
        """
        try:
            # Get current progress
            file_progress = await self.get_file_progress(file_id)
            if not file_progress:
                logger.warning(f"No progress tracking found for file {file_id}")
                return None
            
            # Update fields
            file_progress.status = status
            file_progress.current_step = current_step
            
            if progress is not None:
                file_progress.progress = max(0.0, min(1.0, progress))
            elif completed_steps is not None:
                file_progress.completed_steps = completed_steps
                file_progress.progress = completed_steps / file_progress.total_steps
            
            if error:
                file_progress.error = error
            
            if job_id:
                file_progress.job_id = job_id
            
            if processing_time is not None:
                file_progress.processing_time = processing_time
            
            # Set timestamps
            if status == "processing" and not file_progress.started_at:
                file_progress.started_at = datetime.utcnow()
            elif status in ["completed", "failed", "cancelled"]:
                file_progress.completed_at = datetime.utcnow()
                if file_progress.started_at and not processing_time:
                    file_progress.processing_time = (
                        file_progress.completed_at - file_progress.started_at
                    ).total_seconds()
            
            # Store updated progress
            await self._store_file_progress(file_progress)
            self._file_cache[file_id] = file_progress
            
            # Update session progress
            if file_progress.session_id:
                await self._update_session_progress(file_progress.session_id)
            
            # Emit progress event
            await self.event_bus.publish(ProcessingEvent(
                event_type=ProcessingEventTypes.PROGRESS_UPDATED.value,
                file_id=file_id,
                job_id=job_id,
                session_id=file_progress.session_id,
                progress=file_progress.progress,
                data={
                    "status": status,
                    "current_step": current_step,
                    "filename": file_progress.filename,
                    "error": error,
                    "processing_time": processing_time
                }
            ))
            
            logger.debug(f"Updated progress for file {file_id}: {status} ({file_progress.progress:.1%})")
            return file_progress
            
        except Exception as e:
            logger.error(f"Failed to update file progress for {file_id}: {e}")
            return None
    
    async def get_file_progress(self, file_id: str) -> Optional[FileProgress]:
        """Get progress for a specific file."""
        try:
            # Check cache first
            if file_id in self._file_cache:
                return self._file_cache[file_id]
            
            # Get from Redis
            data = await self.redis.hgetall(self._file_key.format(file_id=file_id))
            if not data:
                return None
            
            # Convert Redis data back to FileProgress
            progress_data = {
                "file_id": file_id,
                "filename": data.get("filename", "unknown"),
                "status": data.get("status", "unknown"),
                "progress": float(data.get("progress", 0)),
                "current_step": data.get("current_step", "unknown"),
                "total_steps": int(data.get("total_steps", 5)),
                "completed_steps": int(data.get("completed_steps", 0)),
                "session_id": data.get("session_id"),
                "size": int(data.get("size", 0)),
                "processed_size": int(data.get("processed_size", 0)),
                "job_id": data.get("job_id"),
                "retry_count": int(data.get("retry_count", 0)),
                "error": data.get("error"),
                "processing_time": float(data["processing_time"]) if data.get("processing_time") else None
            }
            
            # Handle datetime fields
            if data.get("started_at"):
                progress_data["started_at"] = datetime.fromisoformat(data["started_at"])
            if data.get("completed_at"):
                progress_data["completed_at"] = datetime.fromisoformat(data["completed_at"])
            
            file_progress = FileProgress(**progress_data)
            self._file_cache[file_id] = file_progress
            return file_progress
            
        except Exception as e:
            logger.error(f"Failed to get file progress for {file_id}: {e}")
            return None
    
    async def get_session_progress(self, session_id: str) -> Optional[SessionProgress]:
        """Get comprehensive progress for an entire session."""
        try:
            # Check cache first
            if session_id in self._session_cache:
                session = self._session_cache[session_id]
            else:
                # Get from Redis
                data = await self.redis.hgetall(self._session_key.format(session_id=session_id))
                if not data:
                    return None
                
                session = SessionProgress.from_dict(data)
                self._session_cache[session_id] = session
            
            # Get all files for this session
            file_ids = await self.redis.smembers(
                self._session_files_key.format(session_id=session_id)
            )
            
            session.files = {}
            for file_id in file_ids:
                file_progress = await self.get_file_progress(file_id)
                if file_progress:
                    session.files[file_id] = file_progress
            
            return session
            
        except Exception as e:
            logger.error(f"Failed to get session progress for {session_id}: {e}")
            return None
    
    async def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session summary without detailed file progress."""
        try:
            data = await self.redis.hgetall(self._session_key.format(session_id=session_id))
            if not data:
                return None
            
            return {
                "session_id": session_id,
                "total_files": int(data.get("total_files", 0)),
                "processed_files": int(data.get("processed_files", 0)),
                "failed_files": int(data.get("failed_files", 0)),
                "cancelled_files": int(data.get("cancelled_files", 0)),
                "total_size": int(data.get("total_size", 0)),
                "processed_size": int(data.get("processed_size", 0)),
                "overall_progress": float(data.get("overall_progress", 0)),
                "status": data.get("status", "unknown"),
                "started_at": data.get("started_at"),
                "completed_at": data.get("completed_at")
            }
            
        except Exception as e:
            logger.error(f"Failed to get session summary for {session_id}: {e}")
            return None
    
    async def mark_session_complete(self, session_id: str) -> bool:
        """Mark a session as completed."""
        try:
            session = await self.get_session_progress(session_id)
            if not session:
                return False
            
            session.status = "completed"
            session.completed_at = datetime.utcnow()
            
            # Determine final status based on file results
            if session.failed_files > 0:
                session.status = "partial_failure"
            elif session.cancelled_files > 0:
                session.status = "partial_cancellation"
            
            await self._store_session(session)
            self._session_cache[session_id] = session
            
            # Emit session completion event
            await self.event_bus.publish(ProcessingEvent(
                event_type=ProcessingEventTypes.SESSION_PROGRESS_UPDATED.value,
                session_id=session_id,
                data={
                    "status": session.status,
                    "completed_at": session.completed_at.isoformat(),
                    "total_files": session.total_files,
                    "processed_files": session.processed_files,
                    "failed_files": session.failed_files
                }
            ))
            
            logger.info(f"Marked session {session_id} as {session.status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark session {session_id} complete: {e}")
            return False
    
    async def cleanup_expired_sessions(self, hours: int = 24) -> int:
        """Clean up expired session data."""
        try:
            # This would need a more sophisticated implementation
            # with session expiry tracking
            logger.info(f"Cleanup not yet implemented")
            return 0
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def _store_file_progress(self, file_progress: FileProgress):
        """Store file progress in Redis."""
        data = file_progress.to_dict()
        # Remove None values and convert to strings
        redis_data = {
            k: str(v) for k, v in data.items() 
            if v is not None
        }
        
        await self.redis.hset(
            self._file_key.format(file_id=file_progress.file_id),
            mapping=redis_data
        )
        # Set expiry (24 hours)
        await self.redis.expire(
            self._file_key.format(file_id=file_progress.file_id),
            86400
        )
    
    async def _store_session(self, session: SessionProgress):
        """Store session progress in Redis."""
        data = session.to_dict()
        # Remove files dict for session storage (stored separately)
        if 'files' in data:
            del data['files']
            
        redis_data = {
            k: str(v) for k, v in data.items()
            if v is not None
        }
        
        await self.redis.hset(
            self._session_key.format(session_id=session.session_id),
            mapping=redis_data
        )
        # Set expiry (48 hours for sessions)
        await self.redis.expire(
            self._session_key.format(session_id=session.session_id),
            172800
        )
    
    async def _update_session_progress(self, session_id: str):
        """Recalculate and update session-level progress."""
        try:
            # Get all files for this session
            file_ids = await self.redis.smembers(
                self._session_files_key.format(session_id=session_id)
            )
            
            if not file_ids:
                return
            
            # Collect file progress data
            total_progress = 0.0
            processed_files = 0
            failed_files = 0
            cancelled_files = 0
            total_size = 0
            processed_size = 0
            
            for file_id in file_ids:
                file_progress = await self.get_file_progress(file_id)
                if not file_progress:
                    continue
                
                total_progress += file_progress.progress
                total_size += file_progress.size
                processed_size += file_progress.processed_size
                
                if file_progress.status == "completed":
                    processed_files += 1
                elif file_progress.status == "failed":
                    failed_files += 1
                elif file_progress.status == "cancelled":
                    cancelled_files += 1
            
            # Calculate overall progress
            overall_progress = total_progress / len(file_ids) if file_ids else 0.0
            
            # Update session data
            session_key = self._session_key.format(session_id=session_id)
            await self.redis.hset(session_key, mapping={
                "processed_files": str(processed_files),
                "failed_files": str(failed_files),
                "cancelled_files": str(cancelled_files),
                "processed_size": str(processed_size),
                "overall_progress": str(overall_progress)
            })
            
            # Update cache
            if session_id in self._session_cache:
                session = self._session_cache[session_id]
                session.processed_files = processed_files
                session.failed_files = failed_files
                session.cancelled_files = cancelled_files
                session.processed_size = processed_size
                session.overall_progress = overall_progress
            
            logger.debug(f"Updated session {session_id} progress: {overall_progress:.1%}")
            
        except Exception as e:
            logger.error(f"Failed to update session progress for {session_id}: {e}")