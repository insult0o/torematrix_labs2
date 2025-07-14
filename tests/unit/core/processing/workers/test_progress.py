"""Tests for progress tracking system."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta

from torematrix.processing.workers.progress import (
    ProgressTracker, TaskProgress, PipelineProgress
)


class TestTaskProgress:
    """Test TaskProgress dataclass."""
    
    def test_create_task_progress(self):
        """Test creating task progress."""
        started_at = datetime.utcnow()
        progress = TaskProgress(
            task_id="task-123",
            processor_name="test_processor",
            document_id="doc-456",
            status="processing",
            progress=0.5,
            message="Half way done",
            started_at=started_at,
            current_step="processing data",
            total_steps=10,
            completed_steps=5,
            cpu_usage=45.2,
            memory_usage=60.8
        )
        
        assert progress.task_id == "task-123"
        assert progress.processor_name == "test_processor"
        assert progress.document_id == "doc-456"
        assert progress.status == "processing"
        assert progress.progress == 0.5
        assert progress.message == "Half way done"
        assert progress.started_at == started_at
        assert progress.current_step == "processing data"
        assert progress.total_steps == 10
        assert progress.completed_steps == 5
        assert progress.cpu_usage == 45.2
        assert progress.memory_usage == 60.8
    
    def test_duration_property(self):
        """Test duration property calculation."""
        started_at = datetime.utcnow() - timedelta(seconds=30)
        completed_at = started_at + timedelta(seconds=25)
        
        progress = TaskProgress(
            task_id="task-123",
            processor_name="test",
            document_id="doc",
            status="completed",
            progress=1.0,
            started_at=started_at,
            completed_at=completed_at
        )
        
        duration = progress.duration
        assert duration is not None
        assert abs(duration.total_seconds() - 25.0) < 1.0  # Allow small variance
    
    def test_duration_property_no_start(self):
        """Test duration property when no start time."""
        progress = TaskProgress(
            task_id="task-123",
            processor_name="test",
            document_id="doc",
            status="pending",
            progress=0.0
        )
        
        assert progress.duration is None
    
    def test_estimated_remaining_property(self):
        """Test estimated remaining time calculation."""
        started_at = datetime.utcnow() - timedelta(seconds=20)
        
        progress = TaskProgress(
            task_id="task-123",
            processor_name="test",
            document_id="doc",
            status="processing",
            progress=0.4,  # 40% complete
            started_at=started_at
        )
        
        estimated = progress.estimated_remaining
        assert estimated is not None
        # If 40% took 20 seconds, remaining 60% should take ~30 seconds
        assert 25 <= estimated.total_seconds() <= 35
    
    def test_estimated_remaining_no_progress(self):
        """Test estimated remaining when no progress made."""
        progress = TaskProgress(
            task_id="task-123",
            processor_name="test",
            document_id="doc",
            status="processing",
            progress=0.0,
            started_at=datetime.utcnow()
        )
        
        assert progress.estimated_remaining is None
    
    def test_to_dict(self):
        """Test converting task progress to dictionary."""
        started_at = datetime.utcnow()
        progress = TaskProgress(
            task_id="task-123",
            processor_name="test_processor",
            document_id="doc-456",
            status="processing",
            progress=0.7,
            started_at=started_at
        )
        
        progress_dict = progress.to_dict()
        
        assert isinstance(progress_dict, dict)
        assert progress_dict["task_id"] == "task-123"
        assert progress_dict["processor_name"] == "test_processor"
        assert progress_dict["document_id"] == "doc-456"
        assert progress_dict["status"] == "processing"
        assert progress_dict["progress"] == 0.7
        assert progress_dict["started_at"] == started_at.isoformat()


class TestPipelineProgress:
    """Test PipelineProgress dataclass."""
    
    def test_create_pipeline_progress(self):
        """Test creating pipeline progress."""
        started_at = datetime.utcnow()
        stages = ["stage1", "stage2", "stage3"]
        
        pipeline = PipelineProgress(
            pipeline_id="pipeline-123",
            document_id="doc-456",
            total_stages=3,
            started_at=started_at,
            stage_order=stages
        )
        
        assert pipeline.pipeline_id == "pipeline-123"
        assert pipeline.document_id == "doc-456"
        assert pipeline.total_stages == 3
        assert pipeline.completed_stages == 0
        assert pipeline.overall_progress == 0.0
        assert pipeline.started_at == started_at
        assert pipeline.stage_order == stages
    
    def test_update_stage(self):
        """Test updating pipeline stage progress."""
        pipeline = PipelineProgress(
            pipeline_id="pipeline-123",
            document_id="doc-456",
            total_stages=3
        )
        
        # Update stage 1 (completed)
        stage1_progress = TaskProgress(
            task_id="task-1",
            processor_name="processor1",
            document_id="doc-456",
            status="completed",
            progress=1.0
        )
        pipeline.update_stage("stage1", stage1_progress)
        
        assert pipeline.completed_stages == 1
        assert pipeline.overall_progress == 1.0 / 3.0
        assert "stage1" in pipeline.stage_progress
        
        # Update stage 2 (in progress)
        stage2_progress = TaskProgress(
            task_id="task-2",
            processor_name="processor2",
            document_id="doc-456",
            status="processing",
            progress=0.5
        )
        pipeline.update_stage("stage2", stage2_progress)
        
        # Should be 1 completed + 0.5 in progress = 1.5 / 3 = 0.5
        assert pipeline.completed_stages == 1
        assert abs(pipeline.overall_progress - 0.5) < 0.01
        assert pipeline.current_stage == "stage2"
    
    def test_estimated_completion(self):
        """Test estimated completion time calculation."""
        started_at = datetime.utcnow() - timedelta(seconds=60)
        
        pipeline = PipelineProgress(
            pipeline_id="pipeline-123",
            document_id="doc-456",
            total_stages=2,
            overall_progress=0.4,  # 40% complete
            started_at=started_at
        )
        
        estimated = pipeline.estimated_completion
        assert estimated is not None
        # If 40% took 60 seconds, total should take 150 seconds
        expected_completion = started_at + timedelta(seconds=150)
        assert abs((estimated - expected_completion).total_seconds()) < 5
    
    def test_to_dict(self):
        """Test converting pipeline progress to dictionary."""
        started_at = datetime.utcnow()
        pipeline = PipelineProgress(
            pipeline_id="pipeline-123",
            document_id="doc-456",
            total_stages=2,
            started_at=started_at
        )
        
        pipeline_dict = pipeline.to_dict()
        
        assert isinstance(pipeline_dict, dict)
        assert pipeline_dict["pipeline_id"] == "pipeline-123"
        assert pipeline_dict["document_id"] == "doc-456"
        assert pipeline_dict["total_stages"] == 2
        assert pipeline_dict["started_at"] == started_at.isoformat()


class TestProgressTracker:
    """Test ProgressTracker class."""
    
    @pytest.fixture
    def event_bus(self):
        """Create mock event bus."""
        return AsyncMock()
    
    @pytest.fixture
    def tracker(self, event_bus):
        """Create test progress tracker."""
        return ProgressTracker(event_bus=event_bus)
    
    def test_initialization(self, tracker, event_bus):
        """Test progress tracker initialization."""
        assert tracker.event_bus == event_bus
        assert tracker.task_progress == {}
        assert tracker.pipeline_progress == {}
        assert isinstance(tracker.task_stats, dict)
    
    @pytest.mark.asyncio
    async def test_start_task(self, tracker, event_bus):
        """Test starting task tracking."""
        await tracker.start_task(
            task_id="task-123",
            processor_name="test_processor",
            document_id="doc-456",
            total_steps=5
        )
        
        assert "task-123" in tracker.task_progress
        progress = tracker.task_progress["task-123"]
        assert progress.task_id == "task-123"
        assert progress.processor_name == "test_processor"
        assert progress.document_id == "doc-456"
        assert progress.status == "processing"
        assert progress.progress == 0.0
        assert progress.total_steps == 5
        assert progress.started_at is not None
        
        # Check event was emitted
        event_bus.emit.assert_called_once()
        call_args = event_bus.emit.call_args[0][0]
        assert call_args["type"] == "task_progress"
    
    @pytest.mark.asyncio
    async def test_update_task(self, tracker):
        """Test updating task progress."""
        # Start task first
        await tracker.start_task("task-123", "test_processor", "doc-456")
        
        # Update progress
        await tracker.update_task(
            task_id="task-123",
            progress=0.6,
            message="Making good progress",
            current_step="processing data",
            completed_steps=3,
            cpu_usage=45.0,
            memory_usage=60.0
        )
        
        progress = tracker.task_progress["task-123"]
        assert progress.progress == 0.6
        assert progress.message == "Making good progress"
        assert progress.current_step == "processing data"
        assert progress.completed_steps == 3
        assert progress.cpu_usage == 45.0
        assert progress.memory_usage == 60.0
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_task(self, tracker):
        """Test updating progress for non-existent task."""
        # Should not raise an error, just log a warning
        await tracker.update_task("nonexistent", 0.5)
        assert "nonexistent" not in tracker.task_progress
    
    @pytest.mark.asyncio
    async def test_complete_task_success(self, tracker):
        """Test completing a task successfully."""
        # Start task first
        await tracker.start_task("task-123", "test_processor", "doc-456")
        
        # Complete task
        await tracker.complete_task("task-123", success=True)
        
        progress = tracker.task_progress["task-123"]
        assert progress.status == "completed"
        assert progress.progress == 1.0
        assert progress.completed_at is not None
        assert progress.error is None
        
        # Check statistics were updated
        assert "test_processor" in tracker.task_stats
        assert len(tracker.task_stats["test_processor"]) == 1
    
    @pytest.mark.asyncio
    async def test_complete_task_failure(self, tracker):
        """Test completing a task with failure."""
        # Start task first
        await tracker.start_task("task-123", "test_processor", "doc-456")
        
        # Complete task with error
        await tracker.complete_task("task-123", success=False, error="Something went wrong")
        
        progress = tracker.task_progress["task-123"]
        assert progress.status == "failed"
        assert progress.completed_at is not None
        assert progress.error == "Something went wrong"
        
        # Statistics should not include failed tasks for duration
        assert len(tracker.task_stats.get("test_processor", [])) == 0
    
    @pytest.mark.asyncio
    async def test_start_pipeline(self, tracker, event_bus):
        """Test starting pipeline tracking."""
        stages = ["stage1", "stage2", "stage3"]
        
        await tracker.start_pipeline(
            pipeline_id="pipeline-123",
            document_id="doc-456",
            stages=stages
        )
        
        assert "pipeline-123" in tracker.pipeline_progress
        pipeline = tracker.pipeline_progress["pipeline-123"]
        assert pipeline.pipeline_id == "pipeline-123"
        assert pipeline.document_id == "doc-456"
        assert pipeline.total_stages == 3
        assert pipeline.stage_order == stages
        assert pipeline.started_at is not None
        
        # Check event was emitted
        event_bus.emit.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_pipeline_stage(self, tracker):
        """Test updating pipeline stage progress."""
        # Start pipeline first
        await tracker.start_pipeline("pipeline-123", "doc-456", ["stage1", "stage2"])
        
        # Create task progress for stage
        task_progress = TaskProgress(
            task_id="task-1",
            processor_name="processor1",
            document_id="doc-456",
            status="completed",
            progress=1.0
        )
        
        # Update pipeline stage
        await tracker.update_pipeline_stage("pipeline-123", "stage1", task_progress)
        
        pipeline = tracker.pipeline_progress["pipeline-123"]
        assert "stage1" in pipeline.stage_progress
        assert pipeline.stage_progress["stage1"] == task_progress
        assert pipeline.completed_stages == 1
        assert pipeline.overall_progress == 0.5  # 1 of 2 stages complete
    
    @pytest.mark.asyncio
    async def test_get_task_progress(self, tracker):
        """Test getting task progress."""
        await tracker.start_task("task-123", "test_processor", "doc-456")
        
        progress = await tracker.get_task_progress("task-123")
        assert progress is not None
        assert progress.task_id == "task-123"
        
        # Non-existent task
        progress = await tracker.get_task_progress("nonexistent")
        assert progress is None
    
    @pytest.mark.asyncio
    async def test_get_pipeline_progress(self, tracker):
        """Test getting pipeline progress."""
        await tracker.start_pipeline("pipeline-123", "doc-456", ["stage1"])
        
        progress = await tracker.get_pipeline_progress("pipeline-123")
        assert progress is not None
        assert progress.pipeline_id == "pipeline-123"
        
        # Non-existent pipeline
        progress = await tracker.get_pipeline_progress("nonexistent")
        assert progress is None
    
    @pytest.mark.asyncio
    async def test_get_active_tasks(self, tracker):
        """Test getting active tasks."""
        # Start multiple tasks
        await tracker.start_task("task-1", "processor1", "doc-1")
        await tracker.start_task("task-2", "processor2", "doc-2")
        await tracker.complete_task("task-1", success=True)
        
        active_tasks = await tracker.get_active_tasks()
        assert len(active_tasks) == 1
        assert active_tasks[0].task_id == "task-2"
        assert active_tasks[0].status == "processing"
    
    @pytest.mark.asyncio
    async def test_get_active_pipelines(self, tracker):
        """Test getting active pipelines."""
        # Start multiple pipelines
        await tracker.start_pipeline("pipeline-1", "doc-1", ["stage1"])
        await tracker.start_pipeline("pipeline-2", "doc-2", ["stage1"])
        
        # Complete one pipeline
        tracker.pipeline_progress["pipeline-1"].completed_at = datetime.utcnow()
        
        active_pipelines = await tracker.get_active_pipelines()
        assert len(active_pipelines) == 1
        assert active_pipelines[0].pipeline_id == "pipeline-2"
    
    def test_get_statistics(self, tracker):
        """Test getting processing statistics."""
        # Add some task durations to statistics
        tracker.task_stats["processor1"] = [10.0, 15.0, 12.0]
        tracker.task_stats["processor2"] = [8.0, 9.0]
        
        # Overall statistics
        stats = tracker.get_statistics()
        assert stats["total_tasks"] == 5
        assert stats["processors"] == 2
        assert "average_duration" in stats
        assert "median_duration" in stats
        assert "per_processor" in stats
        
        # Processor-specific statistics
        proc1_stats = tracker.get_statistics("processor1")
        assert proc1_stats["processor"] == "processor1"
        assert proc1_stats["total_tasks"] == 3
        assert proc1_stats["average_duration"] == 12.333333333333334
        assert proc1_stats["median_duration"] == 12.0
        
        # Non-existent processor
        empty_stats = tracker.get_statistics("nonexistent")
        assert empty_stats["total_tasks"] == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_completed(self, tracker):
        """Test cleaning up old completed tasks."""
        now = datetime.utcnow()
        old_time = now - timedelta(hours=25)  # 25 hours ago
        
        # Add old completed task
        old_progress = TaskProgress(
            task_id="old-task",
            processor_name="test",
            document_id="doc",
            status="completed",
            progress=1.0,
            completed_at=old_time
        )
        tracker.task_progress["old-task"] = old_progress
        
        # Add recent completed task
        recent_progress = TaskProgress(
            task_id="recent-task",
            processor_name="test",
            document_id="doc",
            status="completed",
            progress=1.0,
            completed_at=now - timedelta(hours=1)
        )
        tracker.task_progress["recent-task"] = recent_progress
        
        # Add old completed pipeline
        old_pipeline = PipelineProgress(
            pipeline_id="old-pipeline",
            document_id="doc",
            total_stages=1,
            completed_at=old_time
        )
        tracker.pipeline_progress["old-pipeline"] = old_pipeline
        
        # Cleanup
        await tracker.cleanup_completed(older_than_hours=24)
        
        # Old task and pipeline should be removed
        assert "old-task" not in tracker.task_progress
        assert "old-pipeline" not in tracker.pipeline_progress
        
        # Recent task should remain
        assert "recent-task" in tracker.task_progress
    
    def test_string_representation(self, tracker):
        """Test string representation of progress tracker."""
        # Add some test data
        tracker.task_progress["active-1"] = TaskProgress(
            task_id="active-1", processor_name="test", 
            document_id="doc", status="processing", progress=0.5
        )
        tracker.task_progress["completed-1"] = TaskProgress(
            task_id="completed-1", processor_name="test", 
            document_id="doc", status="completed", progress=1.0
        )
        tracker.pipeline_progress["pipeline-1"] = PipelineProgress(
            pipeline_id="pipeline-1", document_id="doc", total_stages=1
        )
        
        str_repr = str(tracker)
        assert "ProgressTracker" in str_repr
        assert "active_tasks=1" in str_repr
        assert "completed_tasks=1" in str_repr
        assert "active_pipelines=1" in str_repr


@pytest.mark.asyncio
class TestProgressTrackerIntegration:
    """Integration tests for progress tracker."""
    
    async def test_full_task_lifecycle(self):
        """Test complete task progress lifecycle."""
        event_bus = AsyncMock()
        tracker = ProgressTracker(event_bus)
        
        # Start task
        await tracker.start_task("task-123", "test_processor", "doc-456", total_steps=10)
        
        # Update progress multiple times
        await tracker.update_task("task-123", 0.3, "Starting processing")
        await tracker.update_task("task-123", 0.7, "Half way done", completed_steps=7)
        
        # Complete task
        await tracker.complete_task("task-123", success=True)
        
        # Verify final state
        progress = tracker.task_progress["task-123"]
        assert progress.status == "completed"
        assert progress.progress == 1.0
        assert progress.completed_steps == 7
        
        # Verify events were emitted
        assert event_bus.emit.call_count >= 4  # start + 2 updates + complete
    
    async def test_full_pipeline_lifecycle(self):
        """Test complete pipeline progress lifecycle."""
        event_bus = AsyncMock()
        tracker = ProgressTracker(event_bus)
        
        stages = ["extract", "transform", "validate"]
        
        # Start pipeline
        await tracker.start_pipeline("pipeline-123", "doc-456", stages)
        
        # Complete stages one by one
        for i, stage in enumerate(stages):
            task_progress = TaskProgress(
                task_id=f"task-{i}",
                processor_name=f"processor_{stage}",
                document_id="doc-456",
                status="completed",
                progress=1.0
            )
            await tracker.update_pipeline_stage("pipeline-123", stage, task_progress)
        
        # Verify final state
        pipeline = tracker.pipeline_progress["pipeline-123"]
        assert pipeline.completed_stages == 3
        assert pipeline.overall_progress == 1.0
        assert len(pipeline.stage_progress) == 3
        
        # Verify events were emitted
        assert event_bus.emit.call_count >= 4  # start + 3 stage updates