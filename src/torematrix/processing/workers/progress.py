"""Progress tracking system for processing tasks and pipelines."""

from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict
import statistics
import logging

logger = logging.getLogger(__name__)


@dataclass
class TaskProgress:
    """Progress information for a single task."""
    task_id: str
    processor_name: str
    document_id: str
    status: str
    progress: float  # 0.0 to 1.0
    message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    # Detailed progress
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    completed_steps: int = 0
    
    # Performance metrics
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate task duration."""
        if not self.started_at:
            return None
        end_time = self.completed_at or datetime.utcnow()
        return end_time - self.started_at
    
    @property
    def estimated_remaining(self) -> Optional[timedelta]:
        """Estimate remaining time based on progress."""
        if not self.started_at or self.progress <= 0:
            return None
        
        elapsed = (datetime.utcnow() - self.started_at).total_seconds()
        if self.progress >= 1.0:
            return timedelta(seconds=0)
        
        total_estimated = elapsed / self.progress
        remaining = total_estimated - elapsed
        return timedelta(seconds=max(0, remaining))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "processor_name": self.processor_name,
            "document_id": self.document_id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "duration_seconds": self.duration.total_seconds() if self.duration else None,
            "estimated_remaining_seconds": (
                self.estimated_remaining.total_seconds() 
                if self.estimated_remaining else None
            )
        }


@dataclass
class PipelineProgress:
    """Progress information for an entire pipeline."""
    pipeline_id: str
    document_id: str
    total_stages: int
    completed_stages: int = 0
    current_stage: Optional[str] = None
    overall_progress: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Stage details
    stage_progress: Dict[str, TaskProgress] = field(default_factory=dict)
    stage_order: List[str] = field(default_factory=list)
    
    def update_stage(self, stage_name: str, progress: TaskProgress):
        """Update progress for a specific stage."""
        self.stage_progress[stage_name] = progress
        
        # Recalculate overall progress
        if self.total_stages > 0:
            completed = sum(
                1 for p in self.stage_progress.values()
                if p.status == "completed"
            )
            in_progress = sum(
                p.progress for p in self.stage_progress.values()
                if p.status == "processing"
            )
            self.overall_progress = (completed + in_progress) / self.total_stages
            self.completed_stages = completed
            
            # Update current stage
            processing_stages = [
                name for name, p in self.stage_progress.items()
                if p.status == "processing"
            ]
            self.current_stage = processing_stages[0] if processing_stages else None
    
    @property
    def estimated_completion(self) -> Optional[datetime]:
        """Estimate pipeline completion time."""
        if not self.started_at or self.overall_progress <= 0:
            return None
        
        if self.overall_progress >= 1.0:
            return self.completed_at or datetime.utcnow()
        
        elapsed = (datetime.utcnow() - self.started_at).total_seconds()
        total_estimated = elapsed / self.overall_progress
        return self.started_at + timedelta(seconds=total_estimated)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "pipeline_id": self.pipeline_id,
            "document_id": self.document_id,
            "total_stages": self.total_stages,
            "completed_stages": self.completed_stages,
            "current_stage": self.current_stage,
            "overall_progress": self.overall_progress,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "stage_progress": {
                name: progress.to_dict() 
                for name, progress in self.stage_progress.items()
            },
            "stage_order": self.stage_order,
            "estimated_completion": (
                self.estimated_completion.isoformat() 
                if self.estimated_completion else None
            )
        }


class ProgressTracker:
    """
    Tracks and reports progress for all processing tasks.
    
    Provides real-time updates via EventBus and aggregated statistics.
    """
    
    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        
        # Progress tracking
        self.task_progress: Dict[str, TaskProgress] = {}
        self.pipeline_progress: Dict[str, PipelineProgress] = {}
        
        # Statistics
        self.task_stats: Dict[str, List[float]] = defaultdict(list)
        self._lock = asyncio.Lock()
        
        # Subscribe to worker events if event bus is available
        if self.event_bus:
            asyncio.create_task(self._subscribe_to_events())
    
    async def start_task(
        self,
        task_id: str,
        processor_name: str,
        document_id: str,
        total_steps: Optional[int] = None
    ):
        """Record task start."""
        async with self._lock:
            progress = TaskProgress(
                task_id=task_id,
                processor_name=processor_name,
                document_id=document_id,
                status="processing",
                progress=0.0,
                started_at=datetime.utcnow(),
                total_steps=total_steps
            )
            self.task_progress[task_id] = progress
        
        await self._emit_progress_update(task_id, progress)
        logger.debug(f"Started tracking task {task_id} for processor {processor_name}")
    
    async def update_task(
        self,
        task_id: str,
        progress: float,
        message: str = "",
        current_step: Optional[str] = None,
        completed_steps: Optional[int] = None,
        cpu_usage: Optional[float] = None,
        memory_usage: Optional[float] = None
    ):
        """Update task progress."""
        async with self._lock:
            if task_id not in self.task_progress:
                logger.warning(f"Task {task_id} not found for progress update")
                return
            
            task = self.task_progress[task_id]
            task.progress = max(0.0, min(1.0, progress))
            if message:
                task.message = message
            if current_step is not None:
                task.current_step = current_step
            if completed_steps is not None:
                task.completed_steps = completed_steps
            if cpu_usage is not None:
                task.cpu_usage = cpu_usage
            if memory_usage is not None:
                task.memory_usage = memory_usage
        
        await self._emit_progress_update(task_id, task)
        logger.debug(f"Updated task {task_id} progress: {progress:.1%}")
    
    async def complete_task(
        self,
        task_id: str,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Mark task as completed."""
        async with self._lock:
            if task_id not in self.task_progress:
                logger.warning(f"Task {task_id} not found for completion")
                return
            
            task = self.task_progress[task_id]
            task.status = "completed" if success else "failed"
            task.progress = 1.0 if success else task.progress
            task.completed_at = datetime.utcnow()
            task.error = error
            
            # Update statistics
            if task.duration:
                duration_seconds = task.duration.total_seconds()
                self.task_stats[task.processor_name].append(duration_seconds)
        
        await self._emit_progress_update(task_id, task)
        status = "completed" if success else "failed"
        logger.info(f"Task {task_id} {status} in {task.duration}")
    
    async def start_pipeline(
        self,
        pipeline_id: str,
        document_id: str,
        stages: List[str]
    ):
        """Start tracking a pipeline."""
        async with self._lock:
            pipeline = PipelineProgress(
                pipeline_id=pipeline_id,
                document_id=document_id,
                total_stages=len(stages),
                started_at=datetime.utcnow(),
                stage_order=stages.copy()
            )
            self.pipeline_progress[pipeline_id] = pipeline
        
        await self._emit_pipeline_update(pipeline_id, pipeline)
        logger.info(f"Started tracking pipeline {pipeline_id} with {len(stages)} stages")
    
    async def update_pipeline_stage(
        self,
        pipeline_id: str,
        stage_name: str,
        task_progress: TaskProgress
    ):
        """Update progress for a pipeline stage."""
        async with self._lock:
            if pipeline_id not in self.pipeline_progress:
                logger.warning(f"Pipeline {pipeline_id} not found for stage update")
                return
            
            pipeline = self.pipeline_progress[pipeline_id]
            pipeline.update_stage(stage_name, task_progress)
            
            # Check if pipeline is complete
            if pipeline.overall_progress >= 1.0 and not pipeline.completed_at:
                pipeline.completed_at = datetime.utcnow()
        
        await self._emit_pipeline_update(pipeline_id, pipeline)
    
    async def get_task_progress(self, task_id: str) -> Optional[TaskProgress]:
        """Get progress for a specific task."""
        async with self._lock:
            return self.task_progress.get(task_id)
    
    async def get_pipeline_progress(self, pipeline_id: str) -> Optional[PipelineProgress]:
        """Get progress for a specific pipeline."""
        async with self._lock:
            return self.pipeline_progress.get(pipeline_id)
    
    async def get_active_tasks(self) -> List[TaskProgress]:
        """Get all currently active tasks."""
        async with self._lock:
            return [
                task for task in self.task_progress.values()
                if task.status == "processing"
            ]
    
    async def get_active_pipelines(self) -> List[PipelineProgress]:
        """Get all currently active pipelines."""
        async with self._lock:
            return [
                pipeline for pipeline in self.pipeline_progress.values()
                if pipeline.completed_at is None
            ]
    
    def get_statistics(self, processor_name: Optional[str] = None) -> Dict[str, Any]:
        """Get processing statistics."""
        if processor_name:
            durations = self.task_stats.get(processor_name, [])
            if not durations:
                return {"processor": processor_name, "total_tasks": 0}
            
            return {
                "processor": processor_name,
                "total_tasks": len(durations),
                "average_duration": statistics.mean(durations),
                "median_duration": statistics.median(durations),
                "min_duration": min(durations),
                "max_duration": max(durations),
                "std_deviation": statistics.stdev(durations) if len(durations) > 1 else 0.0
            }
        
        # Overall statistics
        all_durations = []
        for durations in self.task_stats.values():
            all_durations.extend(durations)
        
        if not all_durations:
            return {"total_tasks": 0}
        
        return {
            "total_tasks": len(all_durations),
            "processors": len(self.task_stats),
            "average_duration": statistics.mean(all_durations),
            "median_duration": statistics.median(all_durations),
            "min_duration": min(all_durations),
            "max_duration": max(all_durations),
            "std_deviation": statistics.stdev(all_durations) if len(all_durations) > 1 else 0.0,
            "per_processor": {
                name: self.get_statistics(name)
                for name in self.task_stats.keys()
            }
        }
    
    async def cleanup_completed(self, older_than_hours: int = 24):
        """Clean up completed tasks older than specified hours."""
        cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)
        
        async with self._lock:
            # Clean up completed tasks
            to_remove = []
            for task_id, task in self.task_progress.items():
                if (task.status in ["completed", "failed"] and 
                    task.completed_at and task.completed_at < cutoff):
                    to_remove.append(task_id)
            
            for task_id in to_remove:
                del self.task_progress[task_id]
            
            # Clean up completed pipelines
            to_remove = []
            for pipeline_id, pipeline in self.pipeline_progress.items():
                if (pipeline.completed_at and pipeline.completed_at < cutoff):
                    to_remove.append(pipeline_id)
            
            for pipeline_id in to_remove:
                del self.pipeline_progress[pipeline_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old completed tasks/pipelines")
    
    async def _emit_progress_update(self, task_id: str, progress: TaskProgress):
        """Emit progress update event."""
        if not self.event_bus:
            return
        
        try:
            await self.event_bus.emit({
                "type": "task_progress",
                "data": {
                    "task_id": task_id,
                    "progress": progress.to_dict()
                }
            })
        except Exception as e:
            logger.error(f"Failed to emit progress update for task {task_id}: {e}")
    
    async def _emit_pipeline_update(self, pipeline_id: str, pipeline: PipelineProgress):
        """Emit pipeline progress update event."""
        if not self.event_bus:
            return
        
        try:
            await self.event_bus.emit({
                "type": "pipeline_progress",
                "data": {
                    "pipeline_id": pipeline_id,
                    "progress": pipeline.to_dict()
                }
            })
        except Exception as e:
            logger.error(f"Failed to emit pipeline update for {pipeline_id}: {e}")
    
    async def _subscribe_to_events(self):
        """Subscribe to worker and task events."""
        if not self.event_bus:
            return
        
        # TODO: Implement event subscription when EventBus interface is available
        logger.info("Progress tracker ready to receive events")
    
    def __str__(self) -> str:
        """String representation of progress tracker."""
        active_tasks = len([
            t for t in self.task_progress.values() 
            if t.status == "processing"
        ])
        completed_tasks = len([
            t for t in self.task_progress.values() 
            if t.status in ["completed", "failed"]
        ])
        active_pipelines = len([
            p for p in self.pipeline_progress.values()
            if p.completed_at is None
        ])
        
        return (
            f"ProgressTracker("
            f"active_tasks={active_tasks}, "
            f"completed_tasks={completed_tasks}, "
            f"active_pipelines={active_pipelines}"
            f")"
        )