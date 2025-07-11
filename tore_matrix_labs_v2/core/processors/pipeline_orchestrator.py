#!/usr/bin/env python3
"""
Pipeline Orchestrator for TORE Matrix Labs V2

This orchestrator manages the complete document processing workflow,
coordinating between different services and ensuring proper error handling,
state management, and performance optimization.

Key improvements:
- Clean workflow orchestration
- Comprehensive error handling and recovery
- State persistence and recovery
- Performance monitoring
- Extensible pipeline stages
- Event-driven architecture
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..models.unified_document_model import UnifiedDocument, DocumentStatus, ProcessingStage, ProcessingResult
from ..services.coordinate_mapping_service import CoordinateMappingService
from ..services.text_extraction_service import TextExtractionService
from ..services.validation_service import ValidationService
from .unified_document_processor import UnifiedDocumentProcessor
from .quality_assessment_engine import QualityAssessmentEngine, QualityMetrics


class PipelineStage(Enum):
    """Pipeline processing stages."""
    INITIALIZATION = "initialization"
    DOCUMENT_LOADING = "document_loading"
    TEXT_EXTRACTION = "text_extraction"
    QUALITY_ASSESSMENT = "quality_assessment"
    VALIDATION = "validation"
    FINALIZATION = "finalization"
    EXPORT = "export"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStatus(Enum):
    """Pipeline execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineConfig:
    """Configuration for pipeline execution."""
    
    # Processing options
    enable_parallel_processing: bool = True
    max_concurrent_documents: int = 4
    
    # Quality options
    require_manual_validation: bool = True
    min_quality_threshold: float = 0.8
    
    # Error handling
    retry_on_failure: bool = True
    max_retries: int = 3
    continue_on_error: bool = False
    
    # Performance options
    enable_caching: bool = True
    cache_timeout: int = 3600  # seconds
    
    # Monitoring
    enable_metrics: bool = True
    log_performance: bool = True
    
    # Export options
    auto_export: bool = False
    export_formats: List[str] = field(default_factory=lambda: ["jsonl"])


@dataclass
class PipelineMetrics:
    """Metrics for pipeline execution."""
    
    # Execution metrics
    total_documents: int = 0
    successful_documents: int = 0
    failed_documents: int = 0
    
    # Timing metrics
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_processing_time: float = 0.0
    average_time_per_document: float = 0.0
    
    # Quality metrics
    average_quality_score: float = 0.0
    documents_requiring_validation: int = 0
    
    # Stage metrics
    stage_timings: Dict[str, float] = field(default_factory=dict)
    stage_success_rates: Dict[str, float] = field(default_factory=dict)
    
    # Error metrics
    error_counts: Dict[str, int] = field(default_factory=dict)
    retry_counts: Dict[str, int] = field(default_factory=dict)


@dataclass
class PipelineState:
    """State of pipeline execution."""
    
    # Identity
    pipeline_id: str
    
    # Status
    status: PipelineStatus = PipelineStatus.PENDING
    current_stage: PipelineStage = PipelineStage.INITIALIZATION
    
    # Documents
    document_queue: List[str] = field(default_factory=list)
    processing_documents: Dict[str, PipelineStage] = field(default_factory=dict)
    completed_documents: Dict[str, ProcessingResult] = field(default_factory=dict)
    failed_documents: Dict[str, str] = field(default_factory=dict)
    
    # Progress
    progress_percentage: float = 0.0
    current_document_index: int = 0
    
    # Metrics
    metrics: PipelineMetrics = field(default_factory=PipelineMetrics)
    
    # Configuration
    config: PipelineConfig = field(default_factory=PipelineConfig)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PipelineOrchestrator:
    """
    Orchestrates the complete document processing pipeline.
    
    This orchestrator manages the workflow between different services,
    handles errors and retries, monitors performance, and provides
    comprehensive state management.
    """
    
    def __init__(self,
                 document_processor: UnifiedDocumentProcessor,
                 coordinate_service: CoordinateMappingService,
                 extraction_service: TextExtractionService,
                 validation_service: ValidationService,
                 quality_engine: QualityAssessmentEngine):
        """Initialize the pipeline orchestrator."""
        self.logger = logging.getLogger(__name__)
        
        # Core services
        self.document_processor = document_processor
        self.coordinate_service = coordinate_service
        self.extraction_service = extraction_service
        self.validation_service = validation_service
        self.quality_engine = quality_engine
        
        # Pipeline state management
        self.active_pipelines: Dict[str, PipelineState] = {}
        self.pipeline_history: List[PipelineState] = []
        
        # Event handlers
        self.stage_handlers: Dict[PipelineStage, Callable] = {}
        self.error_handlers: Dict[str, Callable] = {}
        self.progress_callbacks: List[Callable] = []
        
        # Performance monitoring
        self.performance_stats = {
            "pipelines_executed": 0,
            "total_documents_processed": 0,
            "average_pipeline_time": 0.0,
            "success_rate": 0.0
        }
        
        self._register_default_handlers()
        self.logger.info("Pipeline orchestrator initialized")
    
    def create_pipeline(self,
                       documents: List[Union[str, Path, UnifiedDocument]],
                       config: Optional[PipelineConfig] = None,
                       pipeline_id: Optional[str] = None) -> str:
        """
        Create a new processing pipeline.
        
        Args:
            documents: List of documents to process
            config: Pipeline configuration
            pipeline_id: Optional pipeline identifier
            
        Returns:
            Pipeline ID
        """
        if not pipeline_id:
            pipeline_id = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(self.active_pipelines)}"
        
        # Convert documents to document IDs
        document_queue = []
        for doc in documents:
            if isinstance(doc, UnifiedDocument):
                document_queue.append(doc.id)
            else:
                # Create document ID from path
                doc_path = Path(doc)
                doc_id = f"doc_{doc_path.stem}_{doc_path.stat().st_mtime}"
                document_queue.append(doc_id)
        
        # Create pipeline state
        pipeline_state = PipelineState(
            pipeline_id=pipeline_id,
            document_queue=document_queue,
            config=config or PipelineConfig()
        )
        
        pipeline_state.metrics.total_documents = len(document_queue)
        
        # Register pipeline
        self.active_pipelines[pipeline_id] = pipeline_state
        
        self.logger.info(f"Created pipeline {pipeline_id} with {len(document_queue)} documents")
        return pipeline_id
    
    async def execute_pipeline(self, pipeline_id: str) -> PipelineState:
        """
        Execute a processing pipeline.
        
        Args:
            pipeline_id: ID of pipeline to execute
            
        Returns:
            Final pipeline state
        """
        if pipeline_id not in self.active_pipelines:
            raise ValueError(f"Pipeline not found: {pipeline_id}")
        
        pipeline_state = self.active_pipelines[pipeline_id]
        
        try:
            self.logger.info(f"Starting pipeline execution: {pipeline_id}")
            
            # Update state
            pipeline_state.status = PipelineStatus.RUNNING
            pipeline_state.started_at = datetime.now()
            pipeline_state.metrics.start_time = datetime.now()
            
            # Execute pipeline stages
            await self._execute_pipeline_stages(pipeline_state)
            
            # Finalize pipeline
            pipeline_state.status = PipelineStatus.COMPLETED
            pipeline_state.completed_at = datetime.now()
            pipeline_state.metrics.end_time = datetime.now()
            
            # Calculate final metrics
            self._calculate_final_metrics(pipeline_state)
            
            # Move to history
            self.pipeline_history.append(pipeline_state)
            del self.active_pipelines[pipeline_id]
            
            self.logger.info(f"Pipeline completed: {pipeline_id}")
            return pipeline_state
            
        except Exception as e:
            self.logger.error(f"Pipeline execution failed: {pipeline_id} - {str(e)}")
            
            # Update state
            pipeline_state.status = PipelineStatus.FAILED
            pipeline_state.completed_at = datetime.now()
            
            # Move to history
            self.pipeline_history.append(pipeline_state)
            del self.active_pipelines[pipeline_id]
            
            raise
    
    async def _execute_pipeline_stages(self, pipeline_state: PipelineState):
        """Execute all pipeline stages."""
        stages = [
            PipelineStage.INITIALIZATION,
            PipelineStage.DOCUMENT_LOADING,
            PipelineStage.TEXT_EXTRACTION,
            PipelineStage.QUALITY_ASSESSMENT,
            PipelineStage.VALIDATION,
            PipelineStage.FINALIZATION
        ]
        
        for stage in stages:
            if pipeline_state.status != PipelineStatus.RUNNING:
                break
                
            await self._execute_stage(pipeline_state, stage)
    
    async def _execute_stage(self, pipeline_state: PipelineState, stage: PipelineStage):
        """Execute a specific pipeline stage."""
        stage_start_time = datetime.now()
        
        try:
            self.logger.info(f"Executing stage {stage.value} for pipeline {pipeline_state.pipeline_id}")
            
            pipeline_state.current_stage = stage
            
            # Call stage handler
            if stage in self.stage_handlers:
                await self.stage_handlers[stage](pipeline_state)
            else:
                await self._default_stage_handler(pipeline_state, stage)
            
            # Update stage metrics
            stage_time = (datetime.now() - stage_start_time).total_seconds()
            pipeline_state.metrics.stage_timings[stage.value] = stage_time
            
            # Notify progress callbacks
            self._notify_progress_callbacks(pipeline_state)
            
        except Exception as e:
            self.logger.error(f"Stage {stage.value} failed: {str(e)}")
            
            # Handle stage error
            if not await self._handle_stage_error(pipeline_state, stage, e):
                raise
    
    async def _default_stage_handler(self, pipeline_state: PipelineState, stage: PipelineStage):
        """Default handler for pipeline stages."""
        if stage == PipelineStage.INITIALIZATION:
            await self._initialize_pipeline(pipeline_state)
        elif stage == PipelineStage.DOCUMENT_LOADING:
            await self._load_documents(pipeline_state)
        elif stage == PipelineStage.TEXT_EXTRACTION:
            await self._extract_text(pipeline_state)
        elif stage == PipelineStage.QUALITY_ASSESSMENT:
            await self._assess_quality(pipeline_state)
        elif stage == PipelineStage.VALIDATION:
            await self._perform_validation(pipeline_state)
        elif stage == PipelineStage.FINALIZATION:
            await self._finalize_processing(pipeline_state)
    
    async def _initialize_pipeline(self, pipeline_state: PipelineState):
        """Initialize pipeline resources."""
        # Clear caches if needed
        if not pipeline_state.config.enable_caching:
            self.coordinate_service.clear_cache()
        
        # Initialize metrics
        pipeline_state.metrics.start_time = datetime.now()
        
        self.logger.info(f"Pipeline {pipeline_state.pipeline_id} initialized")
    
    async def _load_documents(self, pipeline_state: PipelineState):
        """Load all documents in the pipeline."""
        # For now, documents are loaded on-demand during processing
        # This stage validates that all documents exist and are accessible
        
        valid_documents = []
        for doc_id in pipeline_state.document_queue:
            try:
                # Validate document exists (implementation depends on document storage)
                valid_documents.append(doc_id)
            except Exception as e:
                self.logger.warning(f"Document {doc_id} not accessible: {str(e)}")
                pipeline_state.failed_documents[doc_id] = str(e)
        
        pipeline_state.document_queue = valid_documents
        pipeline_state.metrics.total_documents = len(valid_documents)
        
        self.logger.info(f"Loaded {len(valid_documents)} valid documents")
    
    async def _extract_text(self, pipeline_state: PipelineState):
        """Extract text from all documents."""
        if pipeline_state.config.enable_parallel_processing:
            await self._extract_text_parallel(pipeline_state)
        else:
            await self._extract_text_sequential(pipeline_state)
    
    async def _extract_text_sequential(self, pipeline_state: PipelineState):
        """Extract text sequentially."""
        for i, doc_id in enumerate(pipeline_state.document_queue):
            try:
                # Process document
                result = await self._process_single_document(doc_id, pipeline_state)
                pipeline_state.completed_documents[doc_id] = result
                pipeline_state.metrics.successful_documents += 1
                
            except Exception as e:
                self.logger.error(f"Document processing failed: {doc_id} - {str(e)}")
                pipeline_state.failed_documents[doc_id] = str(e)
                pipeline_state.metrics.failed_documents += 1
                
                if not pipeline_state.config.continue_on_error:
                    raise
            
            # Update progress
            pipeline_state.current_document_index = i + 1
            pipeline_state.progress_percentage = (i + 1) / len(pipeline_state.document_queue) * 100
    
    async def _extract_text_parallel(self, pipeline_state: PipelineState):
        """Extract text in parallel."""
        max_concurrent = pipeline_state.config.max_concurrent_documents
        
        # Process documents in batches
        for i in range(0, len(pipeline_state.document_queue), max_concurrent):
            batch = pipeline_state.document_queue[i:i + max_concurrent]
            
            # Create tasks for batch
            tasks = [
                self._process_single_document(doc_id, pipeline_state)
                for doc_id in batch
            ]
            
            # Execute batch
            try:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for doc_id, result in zip(batch, results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Document processing failed: {doc_id} - {str(result)}")
                        pipeline_state.failed_documents[doc_id] = str(result)
                        pipeline_state.metrics.failed_documents += 1
                    else:
                        pipeline_state.completed_documents[doc_id] = result
                        pipeline_state.metrics.successful_documents += 1
                
            except Exception as e:
                if not pipeline_state.config.continue_on_error:
                    raise
            
            # Update progress
            pipeline_state.current_document_index = min(i + max_concurrent, len(pipeline_state.document_queue))
            pipeline_state.progress_percentage = pipeline_state.current_document_index / len(pipeline_state.document_queue) * 100
    
    async def _process_single_document(self, doc_id: str, pipeline_state: PipelineState) -> ProcessingResult:
        """Process a single document."""
        # This is a placeholder - actual implementation would load the document
        # and call the document processor
        
        # For now, return a mock result
        return ProcessingResult(
            document_id=doc_id,
            success=True,
            extraction_data={"text": "mock extracted text"},
            quality_assessment={"overall_score": 0.85},
            created_at=datetime.now()
        )
    
    async def _assess_quality(self, pipeline_state: PipelineState):
        """Assess quality for all processed documents."""
        total_quality = 0.0
        quality_count = 0
        
        for doc_id, result in pipeline_state.completed_documents.items():
            if result.quality_assessment:
                quality_score = result.quality_assessment.get("overall_score", 0.0)
                total_quality += quality_score
                quality_count += 1
                
                # Check if validation required
                if quality_score < pipeline_state.config.min_quality_threshold:
                    pipeline_state.metrics.documents_requiring_validation += 1
        
        if quality_count > 0:
            pipeline_state.metrics.average_quality_score = total_quality / quality_count
        
        self.logger.info(f"Quality assessment completed: avg score {pipeline_state.metrics.average_quality_score:.3f}")
    
    async def _perform_validation(self, pipeline_state: PipelineState):
        """Perform validation for documents that require it."""
        if not pipeline_state.config.require_manual_validation:
            return
        
        validation_required = pipeline_state.metrics.documents_requiring_validation
        
        if validation_required > 0:
            self.logger.info(f"Manual validation required for {validation_required} documents")
            # Validation implementation would go here
    
    async def _finalize_processing(self, pipeline_state: PipelineState):
        """Finalize processing for all documents."""
        # Clean up resources, export results if configured, etc.
        
        if pipeline_state.config.auto_export:
            await self._export_results(pipeline_state)
        
        self.logger.info(f"Pipeline {pipeline_state.pipeline_id} finalized")
    
    async def _export_results(self, pipeline_state: PipelineState):
        """Export pipeline results."""
        # Export implementation would go here
        self.logger.info(f"Exporting results for pipeline {pipeline_state.pipeline_id}")
    
    async def _handle_stage_error(self, pipeline_state: PipelineState, stage: PipelineStage, error: Exception) -> bool:
        """
        Handle stage error.
        
        Returns:
            True if error was handled and processing should continue, False otherwise
        """
        error_type = type(error).__name__
        
        # Update error metrics
        if error_type not in pipeline_state.metrics.error_counts:
            pipeline_state.metrics.error_counts[error_type] = 0
        pipeline_state.metrics.error_counts[error_type] += 1
        
        # Check if retry is configured
        if pipeline_state.config.retry_on_failure:
            retry_key = f"{stage.value}_{error_type}"
            retry_count = pipeline_state.metrics.retry_counts.get(retry_key, 0)
            
            if retry_count < pipeline_state.config.max_retries:
                pipeline_state.metrics.retry_counts[retry_key] = retry_count + 1
                self.logger.info(f"Retrying stage {stage.value} (attempt {retry_count + 1})")
                
                # Wait before retry
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                
                try:
                    await self._execute_stage(pipeline_state, stage)
                    return True
                except Exception as retry_error:
                    self.logger.error(f"Retry failed: {str(retry_error)}")
        
        # Call error handler if available
        if error_type in self.error_handlers:
            return await self.error_handlers[error_type](pipeline_state, stage, error)
        
        return False
    
    def _calculate_final_metrics(self, pipeline_state: PipelineState):
        """Calculate final pipeline metrics."""
        if pipeline_state.metrics.start_time and pipeline_state.metrics.end_time:
            pipeline_state.metrics.total_processing_time = (
                pipeline_state.metrics.end_time - pipeline_state.metrics.start_time
            ).total_seconds()
            
            if pipeline_state.metrics.total_documents > 0:
                pipeline_state.metrics.average_time_per_document = (
                    pipeline_state.metrics.total_processing_time / pipeline_state.metrics.total_documents
                )
        
        # Update global performance stats
        self.performance_stats["pipelines_executed"] += 1
        self.performance_stats["total_documents_processed"] += pipeline_state.metrics.successful_documents
        
        # Update average pipeline time
        total_pipelines = self.performance_stats["pipelines_executed"]
        current_avg = self.performance_stats["average_pipeline_time"]
        new_time = pipeline_state.metrics.total_processing_time
        self.performance_stats["average_pipeline_time"] = ((current_avg * (total_pipelines - 1)) + new_time) / total_pipelines
        
        # Update success rate
        total_docs = self.performance_stats["total_documents_processed"]
        if total_docs > 0:
            self.performance_stats["success_rate"] = total_docs / (total_docs + pipeline_state.metrics.failed_documents)
    
    def _notify_progress_callbacks(self, pipeline_state: PipelineState):
        """Notify all registered progress callbacks."""
        for callback in self.progress_callbacks:
            try:
                callback(pipeline_state)
            except Exception as e:
                self.logger.error(f"Progress callback failed: {str(e)}")
    
    def _register_default_handlers(self):
        """Register default stage and error handlers."""
        # Default handlers are implemented in the class methods
        pass
    
    def register_stage_handler(self, stage: PipelineStage, handler: Callable):
        """Register a custom stage handler."""
        self.stage_handlers[stage] = handler
        self.logger.info(f"Registered custom handler for stage {stage.value}")
    
    def register_error_handler(self, error_type: str, handler: Callable):
        """Register a custom error handler."""
        self.error_handlers[error_type] = handler
        self.logger.info(f"Registered custom error handler for {error_type}")
    
    def register_progress_callback(self, callback: Callable):
        """Register a progress callback."""
        self.progress_callbacks.append(callback)
        self.logger.info("Registered progress callback")
    
    def get_pipeline_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a pipeline."""
        if pipeline_id in self.active_pipelines:
            state = self.active_pipelines[pipeline_id]
            return {
                "pipeline_id": pipeline_id,
                "status": state.status.value,
                "current_stage": state.current_stage.value,
                "progress": state.progress_percentage,
                "documents_processed": state.current_document_index,
                "total_documents": state.metrics.total_documents,
                "successful": state.metrics.successful_documents,
                "failed": state.metrics.failed_documents
            }
        
        # Check history
        for state in self.pipeline_history:
            if state.pipeline_id == pipeline_id:
                return {
                    "pipeline_id": pipeline_id,
                    "status": state.status.value,
                    "progress": 100.0 if state.status == PipelineStatus.COMPLETED else 0.0,
                    "documents_processed": state.metrics.total_documents,
                    "total_documents": state.metrics.total_documents,
                    "successful": state.metrics.successful_documents,
                    "failed": state.metrics.failed_documents
                }
        
        return None
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get overall performance statistics."""
        return self.performance_stats.copy()
    
    def cancel_pipeline(self, pipeline_id: str) -> bool:
        """Cancel a running pipeline."""
        if pipeline_id in self.active_pipelines:
            pipeline_state = self.active_pipelines[pipeline_id]
            pipeline_state.status = PipelineStatus.CANCELLED
            pipeline_state.completed_at = datetime.now()
            
            # Move to history
            self.pipeline_history.append(pipeline_state)
            del self.active_pipelines[pipeline_id]
            
            self.logger.info(f"Pipeline cancelled: {pipeline_id}")
            return True
        
        return False