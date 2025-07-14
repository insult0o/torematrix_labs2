"""Integration layer for metadata extraction in processing pipeline."""

from typing import Dict, List, Optional, Any, AsyncIterator
import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass

from torematrix.core.events.event_bus import EventBus
from torematrix.core.events.event_types import ProcessingEvent
from torematrix.core.models.element import ProcessedDocument


@dataclass
class IntegrationConfig:
    """Configuration for metadata pipeline integration."""
    enable_realtime_updates: bool = True
    batch_size: int = 100
    max_concurrent_extractions: int = 10
    timeout_seconds: int = 300
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600


@dataclass
class PipelineContext:
    """Context information for pipeline processing."""
    document_id: str
    user_id: str
    session_id: str
    processing_options: Dict[str, Any]
    metadata: Dict[str, Any]


@dataclass
class DocumentWithMetadata:
    """Document with extracted metadata and relationships."""
    document: ProcessedDocument
    metadata: Dict[str, Any]
    relationships: List[Dict[str, Any]]
    extraction_stats: Dict[str, Any]
    processing_time: float


class MetadataPipelineIntegration:
    """Integration layer for metadata extraction in processing pipeline."""
    
    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.event_bus = EventBus()
        self.logger = logging.getLogger(__name__)
        self._processing_sessions: Dict[str, asyncio.Task] = {}
        
    async def initialize(self):
        """Initialize the metadata pipeline integration."""
        await self.event_bus.initialize()
        self.logger.info("Metadata pipeline integration initialized")
        
    async def integrate_with_pipeline(self, pipeline):
        """Integrate metadata extraction into existing pipeline."""
        # Register event handlers for pipeline events
        await self.event_bus.subscribe(
            "document.processing.started",
            self._handle_document_processing_started
        )
        await self.event_bus.subscribe(
            "document.processing.completed", 
            self._handle_document_processing_completed
        )
        
        # Register metadata extraction stage in pipeline
        pipeline.register_stage(
            "metadata_extraction",
            self.extract_metadata_stage,
            dependencies=["element_parsing"]
        )
        
        self.logger.info("Metadata extraction integrated with processing pipeline")
        
    async def process_document_with_metadata(
        self, 
        document: ProcessedDocument,
        pipeline_context: PipelineContext
    ) -> DocumentWithMetadata:
        """Process document through complete metadata pipeline."""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Emit processing started event
            await self.event_bus.emit(ProcessingEvent(
                event_type="metadata.extraction.started",
                document_id=pipeline_context.document_id,
                user_id=pipeline_context.user_id,
                data={"session_id": pipeline_context.session_id}
            ))
            
            # Extract metadata using all agents' components
            metadata = await self._extract_comprehensive_metadata(document)
            relationships = await self._detect_relationships(document, metadata)
            
            # Calculate extraction statistics
            stats = {
                "total_elements": len(document.elements),
                "metadata_fields": len(metadata),
                "relationships_found": len(relationships),
                "processing_time": asyncio.get_event_loop().time() - start_time
            }
            
            result = DocumentWithMetadata(
                document=document,
                metadata=metadata,
                relationships=relationships,
                extraction_stats=stats,
                processing_time=stats["processing_time"]
            )
            
            # Emit completion event
            await self.event_bus.emit(ProcessingEvent(
                event_type="metadata.extraction.completed",
                document_id=pipeline_context.document_id,
                user_id=pipeline_context.user_id,
                data={
                    "session_id": pipeline_context.session_id,
                    "stats": stats
                }
            ))
            
            return result
            
        except Exception as e:
            self.logger.error(f"Metadata extraction failed: {e}")
            await self.event_bus.emit(ProcessingEvent(
                event_type="metadata.extraction.failed",
                document_id=pipeline_context.document_id,
                user_id=pipeline_context.user_id,
                data={
                    "session_id": pipeline_context.session_id,
                    "error": str(e)
                }
            ))
            raise
            
    async def _extract_comprehensive_metadata(
        self, 
        document: ProcessedDocument
    ) -> Dict[str, Any]:
        """Extract comprehensive metadata using Agent 1's engine."""
        from torematrix.core.processing.metadata.extractors.semantic import SemanticRoleExtractor
        from torematrix.core.processing.metadata.extractors.reading_order import ReadingOrderExtractor
        
        # Extract semantic metadata
        semantic_extractor = SemanticRoleExtractor()
        semantic_data = await semantic_extractor.extract_roles(document.elements)
        
        # Extract reading order
        reading_order_extractor = ReadingOrderExtractor()
        reading_order = await reading_order_extractor.extract_reading_order(document.elements)
        
        return {
            "semantic_roles": semantic_data,
            "reading_order": reading_order,
            "document_structure": await self._analyze_document_structure(document),
            "content_analysis": await self._analyze_content(document)
        }
        
    async def _detect_relationships(
        self, 
        document: ProcessedDocument, 
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Detect relationships using Agent 2's engine."""
        from torematrix.core.processing.metadata.relationships import RelationshipDetectionEngine
        
        # Use Agent 2's relationship detection
        relationship_engine = RelationshipDetectionEngine()
        relationships = await relationship_engine.detect_relationships(
            document.elements,
            metadata
        )
        
        return [rel.to_dict() for rel in relationships]
        
    async def _analyze_document_structure(
        self, 
        document: ProcessedDocument
    ) -> Dict[str, Any]:
        """Analyze document structure for metadata."""
        return {
            "total_pages": getattr(document, 'page_count', 1),
            "element_types": self._count_element_types(document.elements),
            "document_layout": await self._analyze_layout(document.elements)
        }
        
    async def _analyze_content(
        self, 
        document: ProcessedDocument
    ) -> Dict[str, Any]:
        """Analyze document content for metadata."""
        from torematrix.core.processing.metadata.algorithms.content import ContentAnalyzer
        
        content_analyzer = ContentAnalyzer()
        return await content_analyzer.analyze_document_content(document.elements)
        
    def _count_element_types(self, elements: List) -> Dict[str, int]:
        """Count elements by type."""
        type_counts = {}
        for element in elements:
            element_type = getattr(element, 'type', 'unknown')
            type_counts[element_type] = type_counts.get(element_type, 0) + 1
        return type_counts
        
    async def _analyze_layout(self, elements: List) -> Dict[str, Any]:
        """Analyze document layout from elements."""
        from torematrix.core.processing.metadata.algorithms.spatial import SpatialAnalyzer
        
        spatial_analyzer = SpatialAnalyzer()
        return await spatial_analyzer.analyze_spatial_layout(elements)
        
    async def extract_metadata_stage(
        self, 
        document: ProcessedDocument, 
        context: PipelineContext
    ) -> ProcessedDocument:
        """Pipeline stage for metadata extraction."""
        metadata_result = await self.process_document_with_metadata(document, context)
        
        # Enhance document with metadata
        enhanced_document = document
        enhanced_document.metadata = metadata_result.metadata
        enhanced_document.relationships = metadata_result.relationships
        
        return enhanced_document
        
    async def _handle_document_processing_started(self, event: ProcessingEvent):
        """Handle document processing started event."""
        self.logger.info(f"Document processing started: {event.document_id}")
        
    async def _handle_document_processing_completed(self, event: ProcessingEvent):
        """Handle document processing completed event."""
        self.logger.info(f"Document processing completed: {event.document_id}")
        
    async def get_processing_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of metadata processing session."""
        if session_id in self._processing_sessions:
            task = self._processing_sessions[session_id]
            return {
                "session_id": session_id,
                "status": "running" if not task.done() else "completed",
                "progress": await self._get_session_progress(session_id)
            }
        return {"session_id": session_id, "status": "not_found"}
        
    async def _get_session_progress(self, session_id: str) -> Dict[str, Any]:
        """Get progress information for a processing session."""
        # This would integrate with Agent 3's performance monitoring
        return {
            "current_stage": "metadata_extraction",
            "completion_percentage": 75,
            "estimated_time_remaining": 30
        }
        
    async def cleanup(self):
        """Cleanup resources and connections."""
        for session_id, task in self._processing_sessions.items():
            if not task.done():
                task.cancel()
                
        await self.event_bus.shutdown()
        self.logger.info("Metadata pipeline integration cleaned up")