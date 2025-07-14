"""Core metadata extraction engine with async processing and pluggable extractors."""

from typing import Dict, List, Optional, Any, Set, Tuple
import asyncio
import logging
from datetime import datetime
from pathlib import Path

from .types import (
    MetadataConfig, ExtractionContext, ExtractionMethod,
    MetadataDict, ExtractorResult
)
from .schema import (
    MetadataSchema, DocumentMetadata, PageMetadata, ElementMetadata,
    RelationshipMetadata, BaseMetadata
)
from .confidence import ConfidenceScorer
from .extractors.base import BaseExtractor, ExtractorRegistry


logger = logging.getLogger(__name__)


class MetadataExtractionEngine:
    """Core metadata extraction engine with pluggable extractors."""
    
    def __init__(self, config: MetadataConfig):
        """Initialize metadata extraction engine.
        
        Args:
            config: Engine configuration
        """
        self.config = config
        self.extractors = ExtractorRegistry()
        self.confidence_scorer = ConfidenceScorer(config.confidence_weights)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Performance tracking
        self._extraction_stats = {
            "total_documents": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "average_duration": 0.0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # Simple in-memory cache for demonstration
        self._metadata_cache: Dict[str, MetadataSchema] = {}
        
        self.logger.info("MetadataExtractionEngine initialized")
    
    async def extract_metadata(
        self,
        document: Any,  # ProcessedDocument from processing system
        extraction_types: Optional[List[str]] = None,
        context: Optional[ExtractionContext] = None
    ) -> MetadataSchema:
        """Extract comprehensive metadata from document.
        
        Args:
            document: The document to extract metadata from
            extraction_types: Specific types of metadata to extract
            context: Extraction context (created if None)
            
        Returns:
            Complete metadata schema for the document
        """
        start_time = datetime.utcnow()
        self._extraction_stats["total_documents"] += 1
        
        try:
            # Create extraction context if not provided
            if context is None:
                context = ExtractionContext(
                    document_id=getattr(document, 'document_id', str(document)),
                    extraction_timestamp=start_time
                )
            
            # Check cache first
            cache_key = self._generate_cache_key(document, extraction_types)
            if self.config.cache_enabled and cache_key in self._metadata_cache:
                self._extraction_stats["cache_hits"] += 1
                self.logger.debug(f"Cache hit for document: {context.document_id}")
                return self._metadata_cache[cache_key]
            
            self._extraction_stats["cache_misses"] += 1
            
            # Determine which extractors to run
            target_extractors = self._select_extractors(extraction_types)
            
            # Run extractors in parallel if enabled
            if self.config.enable_parallel_extraction:
                metadata_results = await self._extract_parallel(
                    document, context, target_extractors
                )
            else:
                metadata_results = await self._extract_sequential(
                    document, context, target_extractors
                )
            
            # Combine results into metadata schema
            metadata_schema = self._combine_extraction_results(
                metadata_results, context
            )
            
            # Calculate overall confidence
            overall_confidence = self.confidence_scorer.calculate_aggregated_confidence(
                self._get_all_metadata_objects(metadata_schema),
                context
            )[0]
            
            metadata_schema.total_confidence_score = overall_confidence
            metadata_schema.extraction_context = context
            
            # Cache results
            if self.config.cache_enabled:
                self._metadata_cache[cache_key] = metadata_schema
                self._cleanup_cache()
            
            # Update statistics
            duration = (datetime.utcnow() - start_time).total_seconds()
            self._update_extraction_stats(duration, True)
            
            self.logger.info(
                f"Metadata extraction completed for {context.document_id} "
                f"in {duration:.2f}s with confidence {overall_confidence:.3f}"
            )
            
            return metadata_schema
            
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            self._update_extraction_stats(duration, False)
            
            self.logger.error(
                f"Metadata extraction failed for document: {str(e)}",
                exc_info=True
            )
            
            # Return empty schema with error information
            return MetadataSchema(
                extraction_context=context,
                total_confidence_score=0.0
            )
    
    async def extract_incremental(
        self,
        document: Any,
        previous_metadata: MetadataSchema,
        changes: Optional[Dict[str, Any]] = None
    ) -> MetadataSchema:
        """Perform incremental metadata extraction for document updates.
        
        Args:
            document: Updated document
            previous_metadata: Previously extracted metadata
            changes: Information about what changed in the document
            
        Returns:
            Updated metadata schema
        """
        self.logger.info("Starting incremental metadata extraction")
        
        # Create context for incremental extraction
        context = ExtractionContext(
            document_id=previous_metadata.extraction_context.document_id
            if previous_metadata.extraction_context else str(document),
            processing_hints={
                "incremental": True,
                "previous_extraction": True,
                "changes": changes or {}
            }
        )
        
        # Determine which extractors need to run based on changes
        required_extractors = self._determine_incremental_extractors(
            changes, previous_metadata
        )
        
        # Run only necessary extractors
        if required_extractors:
            # Extract metadata for changed components
            new_results = await self._extract_parallel(
                document, context, required_extractors
            )
            
            # Merge with previous metadata
            updated_schema = self._merge_metadata_schemas(
                previous_metadata, new_results, context
            )
        else:
            # No changes requiring extraction
            updated_schema = previous_metadata
            updated_schema.extraction_context = context
        
        self.logger.info("Incremental metadata extraction completed")
        return updated_schema
    
    def register_extractor(self, name: str, extractor: BaseExtractor) -> None:
        """Register a metadata extractor.
        
        Args:
            name: Unique name for the extractor
            extractor: Extractor instance
        """
        self.extractors.register_extractor(name, extractor)
        self.logger.info(f"Registered extractor: {name}")
    
    def unregister_extractor(self, name: str) -> None:
        """Unregister a metadata extractor.
        
        Args:
            name: Name of extractor to remove
        """
        self.extractors.unregister_extractor(name)
        self.logger.info(f"Unregistered extractor: {name}")
    
    def get_available_extractors(self) -> List[str]:
        """Get list of available extractors.
        
        Returns:
            List of extractor names
        """
        return self.extractors.list_extractors()
    
    def get_engine_statistics(self) -> Dict[str, Any]:
        """Get comprehensive engine statistics.
        
        Returns:
            Dictionary with performance metrics
        """
        total = self._extraction_stats["total_documents"]
        successful = self._extraction_stats["successful_extractions"]
        
        return {
            "engine_info": {
                "total_documents_processed": total,
                "successful_extractions": successful,
                "failed_extractions": self._extraction_stats["failed_extractions"],
                "success_rate": successful / total if total > 0 else 0.0,
                "average_duration_seconds": self._extraction_stats["average_duration"],
            },
            "cache_info": {
                "cache_enabled": self.config.cache_enabled,
                "cache_size": len(self._metadata_cache),
                "cache_hits": self._extraction_stats["cache_hits"],
                "cache_misses": self._extraction_stats["cache_misses"],
                "cache_hit_rate": (
                    self._extraction_stats["cache_hits"] / 
                    (self._extraction_stats["cache_hits"] + self._extraction_stats["cache_misses"])
                    if self._extraction_stats["cache_hits"] + self._extraction_stats["cache_misses"] > 0
                    else 0.0
                )
            },
            "extractor_info": self.extractors.get_registry_info(),
            "configuration": self.config.dict()
        }
    
    async def _extract_parallel(
        self,
        document: Any,
        context: ExtractionContext,
        extractors: Dict[str, BaseExtractor]
    ) -> Dict[str, Dict[str, Any]]:
        """Run extractors in parallel.
        
        Args:
            document: Document to process
            context: Extraction context
            extractors: Dictionary of extractors to run
            
        Returns:
            Dictionary mapping extractor names to results
        """
        # Create semaphore to limit concurrent extractions
        semaphore = asyncio.Semaphore(self.config.max_workers)
        
        async def extract_with_semaphore(name: str, extractor: BaseExtractor):
            async with semaphore:
                return name, await extractor.extract_with_validation(document, context)
        
        # Run all extractors concurrently
        tasks = [
            extract_with_semaphore(name, extractor)
            for name, extractor in extractors.items()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        extraction_results = {}
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Extractor failed: {result}")
                continue
            
            name, extraction_result = result
            extraction_results[name] = extraction_result
        
        return extraction_results
    
    async def _extract_sequential(
        self,
        document: Any,
        context: ExtractionContext,
        extractors: Dict[str, BaseExtractor]
    ) -> Dict[str, Dict[str, Any]]:
        """Run extractors sequentially.
        
        Args:
            document: Document to process
            context: Extraction context
            extractors: Dictionary of extractors to run
            
        Returns:
            Dictionary mapping extractor names to results
        """
        extraction_results = {}
        
        for name, extractor in extractors.items():
            try:
                result = await extractor.extract_with_validation(document, context)
                extraction_results[name] = result
            except Exception as e:
                self.logger.error(f"Extractor {name} failed: {e}")
                continue
        
        return extraction_results
    
    def _select_extractors(
        self,
        extraction_types: Optional[List[str]]
    ) -> Dict[str, BaseExtractor]:
        """Select which extractors to run based on requirements.
        
        Args:
            extraction_types: Specific types to extract (None for all)
            
        Returns:
            Dictionary of selected extractors
        """
        if extraction_types is None:
            return self.extractors.get_enabled_extractors()
        
        selected = {}
        for extractor_name in extraction_types:
            extractor = self.extractors.get_extractor(extractor_name)
            if extractor and extractor.is_enabled():
                selected[extractor_name] = extractor
            else:
                self.logger.warning(f"Extractor not found or disabled: {extractor_name}")
        
        return selected
    
    def _combine_extraction_results(
        self,
        results: Dict[str, Dict[str, Any]],
        context: ExtractionContext
    ) -> MetadataSchema:
        """Combine extraction results into a metadata schema.
        
        Args:
            results: Dictionary of extraction results
            context: Extraction context
            
        Returns:
            Combined metadata schema
        """
        schema = MetadataSchema(extraction_context=context)
        
        for extractor_name, result in results.items():
            if not result.get("extraction_info", {}).get("success", False):
                continue
            
            metadata = result.get("metadata", {})
            validation = result.get("validation")
            
            # Process based on metadata type
            metadata_type = metadata.get("metadata_type")
            
            if metadata_type == "document":
                schema.document_metadata = self._create_document_metadata(
                    metadata, validation, extractor_name, context
                )
            elif metadata_type == "page":
                page_metadata = self._create_page_metadata(
                    metadata, validation, extractor_name, context
                )
                if page_metadata:
                    schema.page_metadata.append(page_metadata)
            elif metadata_type == "element":
                element_metadata = self._create_element_metadata(
                    metadata, validation, extractor_name, context
                )
                if element_metadata:
                    schema.element_metadata.append(element_metadata)
            elif metadata_type == "relationship":
                relationship_metadata = self._create_relationship_metadata(
                    metadata, validation, extractor_name, context
                )
                if relationship_metadata:
                    schema.relationship_metadata.append(relationship_metadata)
        
        return schema
    
    def _create_document_metadata(
        self,
        metadata: Dict[str, Any],
        validation: Any,
        extractor_name: str,
        context: ExtractionContext
    ) -> Optional[DocumentMetadata]:
        """Create DocumentMetadata from extraction results."""
        try:
            # Calculate confidence score
            confidence = self.confidence_scorer.calculate_confidence(
                BaseMetadata(
                    metadata_type="document",
                    confidence_score=validation.confidence_score if validation else 0.5,
                    source_extractor=extractor_name,
                    extraction_method=metadata.get("extraction_method", "direct_parsing"),
                    validation_result=validation
                ),
                context
            )
            
            return DocumentMetadata(
                confidence_score=confidence,
                source_extractor=extractor_name,
                extraction_method=metadata.get("extraction_method", "direct_parsing"),
                validation_result=validation,
                **{k: v for k, v in metadata.items() if k != "metadata_type"}
            )
        except Exception as e:
            self.logger.error(f"Failed to create document metadata: {e}")
            return None
    
    def _create_page_metadata(
        self,
        metadata: Dict[str, Any],
        validation: Any,
        extractor_name: str,
        context: ExtractionContext
    ) -> Optional[PageMetadata]:
        """Create PageMetadata from extraction results."""
        try:
            confidence = self.confidence_scorer.calculate_confidence(
                BaseMetadata(
                    metadata_type="page",
                    confidence_score=validation.confidence_score if validation else 0.5,
                    source_extractor=extractor_name,
                    extraction_method=metadata.get("extraction_method", "direct_parsing"),
                    validation_result=validation
                ),
                context
            )
            
            return PageMetadata(
                confidence_score=confidence,
                source_extractor=extractor_name,
                extraction_method=metadata.get("extraction_method", "direct_parsing"),
                validation_result=validation,
                document_id=context.document_id,
                **{k: v for k, v in metadata.items() if k not in ["metadata_type", "document_id"]}
            )
        except Exception as e:
            self.logger.error(f"Failed to create page metadata: {e}")
            return None
    
    def _create_element_metadata(
        self,
        metadata: Dict[str, Any],
        validation: Any,
        extractor_name: str,
        context: ExtractionContext
    ) -> Optional[ElementMetadata]:
        """Create ElementMetadata from extraction results."""
        try:
            confidence = self.confidence_scorer.calculate_confidence(
                BaseMetadata(
                    metadata_type="element",
                    confidence_score=validation.confidence_score if validation else 0.5,
                    source_extractor=extractor_name,
                    extraction_method=metadata.get("extraction_method", "direct_parsing"),
                    validation_result=validation
                ),
                context
            )
            
            return ElementMetadata(
                confidence_score=confidence,
                source_extractor=extractor_name,
                extraction_method=metadata.get("extraction_method", "direct_parsing"),
                validation_result=validation,
                document_id=context.document_id,
                **{k: v for k, v in metadata.items() if k not in ["metadata_type", "document_id"]}
            )
        except Exception as e:
            self.logger.error(f"Failed to create element metadata: {e}")
            return None
    
    def _create_relationship_metadata(
        self,
        metadata: Dict[str, Any],
        validation: Any,
        extractor_name: str,
        context: ExtractionContext
    ) -> Optional[RelationshipMetadata]:
        """Create RelationshipMetadata from extraction results."""
        try:
            confidence = self.confidence_scorer.calculate_confidence(
                BaseMetadata(
                    metadata_type="relationship",
                    confidence_score=validation.confidence_score if validation else 0.5,
                    source_extractor=extractor_name,
                    extraction_method=metadata.get("extraction_method", "direct_parsing"),
                    validation_result=validation
                ),
                context
            )
            
            return RelationshipMetadata(
                confidence_score=confidence,
                source_extractor=extractor_name,
                extraction_method=metadata.get("extraction_method", "direct_parsing"),
                validation_result=validation,
                **{k: v for k, v in metadata.items() if k != "metadata_type"}
            )
        except Exception as e:
            self.logger.error(f"Failed to create relationship metadata: {e}")
            return None
    
    def _get_all_metadata_objects(self, schema: MetadataSchema) -> List[BaseMetadata]:
        """Get all metadata objects from schema for confidence calculation."""
        metadata_objects = []
        
        if schema.document_metadata:
            metadata_objects.append(schema.document_metadata)
        
        metadata_objects.extend(schema.page_metadata)
        metadata_objects.extend(schema.element_metadata)
        metadata_objects.extend(schema.relationship_metadata)
        
        return metadata_objects
    
    def _generate_cache_key(
        self,
        document: Any,
        extraction_types: Optional[List[str]]
    ) -> str:
        """Generate cache key for document and extraction parameters."""
        doc_id = getattr(document, 'document_id', str(document))
        types_str = ",".join(sorted(extraction_types)) if extraction_types else "all"
        return f"{doc_id}:{types_str}"
    
    def _cleanup_cache(self) -> None:
        """Clean up cache based on TTL and size limits."""
        # Simple cleanup - in production, implement proper TTL and LRU
        if len(self._metadata_cache) > 1000:  # Simple size limit
            # Remove oldest entries
            keys_to_remove = list(self._metadata_cache.keys())[:100]
            for key in keys_to_remove:
                del self._metadata_cache[key]
    
    def _update_extraction_stats(self, duration: float, success: bool) -> None:
        """Update extraction performance statistics."""
        if success:
            self._extraction_stats["successful_extractions"] += 1
        else:
            self._extraction_stats["failed_extractions"] += 1
        
        # Update average duration
        total = self._extraction_stats["total_documents"]
        current_avg = self._extraction_stats["average_duration"]
        new_avg = ((current_avg * (total - 1)) + duration) / total
        self._extraction_stats["average_duration"] = new_avg
    
    def _determine_incremental_extractors(
        self,
        changes: Optional[Dict[str, Any]],
        previous_metadata: MetadataSchema
    ) -> Dict[str, BaseExtractor]:
        """Determine which extractors need to run for incremental extraction."""
        # Simple implementation - in practice, this would be more sophisticated
        if not changes:
            return {}
        
        # For now, return all extractors for any changes
        return self.extractors.get_enabled_extractors()
    
    def _merge_metadata_schemas(
        self,
        previous: MetadataSchema,
        new_results: Dict[str, Dict[str, Any]],
        context: ExtractionContext
    ) -> MetadataSchema:
        """Merge previous metadata with new extraction results."""
        # Simple merge implementation - combine new results with previous
        updated_schema = self._combine_extraction_results(new_results, context)
        
        # Keep previous metadata that wasn't updated
        if not updated_schema.document_metadata and previous.document_metadata:
            updated_schema.document_metadata = previous.document_metadata
        
        # For page/element metadata, this would be more complex in practice
        if not updated_schema.page_metadata:
            updated_schema.page_metadata = previous.page_metadata
        
        if not updated_schema.element_metadata:
            updated_schema.element_metadata = previous.element_metadata
        
        return updated_schema