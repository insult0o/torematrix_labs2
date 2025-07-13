"""
Agent 4 - Main UnstructuredIntegration class with comprehensive file format support.

This is the primary integration point that coordinates all format handlers and validators.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

# Agent 4 format handlers
from .formats import (
    PDFHandler, PDFFeatures,
    OfficeHandler, OfficeFeatures,
    WebHandler, WebFeatures,
    EmailHandler, EmailFeatures,
    TextHandler, TextFeatures
)

# Agent 4 validators
from .validators import FormatValidator, ValidationLevel, OutputValidator

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of document processing."""
    success: bool
    elements: List[Any]
    features: Any
    processing_time: float
    quality_score: float
    validation_result: Any
    warnings: List[str]
    errors: List[str]
    strategy_used: str
    file_path: Path
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []


class UnstructuredIntegration:
    """
    Main integration class for comprehensive document processing.
    
    Coordinates format handlers, validation, and integration with other agents.
    """
    
    def __init__(self, config=None):
        self.config = config
        self.is_initialized = False
        
        # Initialize format handlers
        self.handlers = {}
        self._initialize_handlers()
        
        # Initialize validators
        self.format_validator = FormatValidator(ValidationLevel.MODERATE)
        self.output_validator = OutputValidator()
        
        # Try to integrate with Agent 3's bridge
        self.bridge = None
        try:
            self._try_bridge_integration()
        except Exception as e:
            logger.warning(f"Bridge integration failed: {e}")
            self.bridge = None
        
        # Processing stats
        self.stats = {
            'documents_processed': 0,
            'total_processing_time': 0.0,
            'format_counts': {},
            'error_count': 0
        }
        
        logger.info("UnstructuredIntegration initialized")
    
    def _initialize_handlers(self) -> None:
        """Initialize all format handlers."""
        # All handlers will be initialized with no client initially
        # They will gracefully fallback to mock processing
        self.handlers = {
            'pdf': PDFHandler(),
            'office': OfficeHandler(),
            'web': WebHandler(),
            'email': EmailHandler(),
            'text': TextHandler()
        }
        
        logger.debug("Format handlers initialized")
    
    def _try_bridge_integration(self) -> None:
        """Try to integrate with Agent 3's optimization bridge."""
        try:
            from .bridge import OptimizedInfrastructureBridge, BridgeFactory
            from .strategies.adaptive import SelectionCriteria
            
            # Store selection criteria for later use
            self.SelectionCriteria = SelectionCriteria
            
            # Try to create bridge with development config first
            try:
                self.bridge = BridgeFactory.create_development_bridge()
                logger.info("Successfully integrated with Agent 3's optimization bridge (development config)")
            except Exception as e:
                logger.warning(f"Could not create development bridge: {e}")
                # Try production config
                try:
                    self.bridge = BridgeFactory.create_production_bridge()
                    logger.info("Successfully integrated with Agent 3's optimization bridge (production config)")
                except Exception as e2:
                    logger.warning(f"Could not create production bridge: {e2}")
                    # Try basic bridge with no config
                    try:
                        self.bridge = OptimizedInfrastructureBridge()
                        logger.info("Created basic Agent 3 bridge without specific config")
                    except Exception as e3:
                        logger.warning(f"Basic bridge creation failed: {e3}")
                        self.bridge = None
                    
        except ImportError as e:
            logger.info("Agent 3's bridge not available, using standalone mode")
            self.bridge = None
            self.SelectionCriteria = None
        except Exception as e:
            logger.warning(f"Bridge integration failed: {e}")
            self.bridge = None
            self.SelectionCriteria = None
    
    async def initialize(self) -> None:
        """Initialize the integration system."""
        if self.is_initialized:
            return
        
        try:
            # Initialize bridge if available
            if self.bridge:
                # Bridge might have its own initialization
                if hasattr(self.bridge, 'initialize'):
                    await self.bridge.initialize()
                    
            self.is_initialized = True
            logger.info("UnstructuredIntegration fully initialized")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            # Continue without bridge
            self.is_initialized = True
    
    async def process_document(self, file_path: Path, **kwargs) -> ProcessingResult:
        """
        Process a document with comprehensive format handling.
        
        Args:
            file_path: Path to the document
            **kwargs: Additional processing options
            
        Returns:
            ProcessingResult with elements, features, and metadata
        """
        start_time = time.time()
        
        try:
            # Step 1: Validate input file
            validation_result = await self.format_validator.validate_file(file_path)
            
            if not validation_result.is_valid:
                return ProcessingResult(
                    success=False,
                    elements=[],
                    features=None,
                    processing_time=time.time() - start_time,
                    quality_score=0.0,
                    validation_result=validation_result,
                    warnings=validation_result.warnings,
                    errors=validation_result.errors,
                    strategy_used="validation_failed",
                    file_path=file_path
                )
            
            # Step 2: Try optimized processing with Agent 3's bridge first
            if self.bridge:
                try:
                    bridge_result = await self._process_with_bridge(file_path, validation_result, **kwargs)
                    if bridge_result.success:
                        return bridge_result
                    else:
                        logger.warning("Bridge processing failed, falling back to direct handlers")
                except Exception as e:
                    logger.warning(f"Bridge processing error: {e}, falling back to direct handlers")
            
            # Step 3: Fallback to direct format handler processing
            handler_result = await self._process_with_handlers(file_path, validation_result, **kwargs)
            
            # Step 4: Update statistics
            self._update_stats(handler_result)
            
            return handler_result
            
        except Exception as e:
            logger.error(f"Document processing failed for {file_path}: {e}")
            return ProcessingResult(
                success=False,
                elements=[],
                features=None,
                processing_time=time.time() - start_time,
                quality_score=0.0,
                validation_result=None,
                warnings=[],
                errors=[f"Processing exception: {str(e)}"],
                strategy_used="error",
                file_path=file_path
            )
    
    async def _process_with_bridge(self, file_path: Path, validation_result, **kwargs) -> ProcessingResult:
        """Process document using Agent 3's optimization bridge."""
        start_time = time.time()
        
        try:
            # Determine selection criteria based on file characteristics
            selection_criteria = self._determine_selection_criteria(file_path, validation_result, **kwargs)
            
            # Use bridge's optimized parsing with intelligent strategy selection
            elements, metrics, analysis = await self.bridge.parse_document_optimized(
                file_path=file_path,
                selection_criteria=selection_criteria,
                use_cache=kwargs.get('use_cache', True)
            )
            
            # Validate output
            output_validation = await self.output_validator.validate_output(
                elements, file_path, processing_time=metrics.processing_time
            )
            
            return ProcessingResult(
                success=True,
                elements=elements,
                features=analysis,  # Agent 3's document analysis
                processing_time=time.time() - start_time,
                quality_score=output_validation.quality_score,
                validation_result=validation_result,
                warnings=validation_result.warnings + output_validation.warnings,
                errors=output_validation.errors,
                strategy_used=f"bridge_{metrics.strategy_name}",
                file_path=file_path
            )
            
        except Exception as e:
            logger.error(f"Bridge processing failed: {e}")
            return ProcessingResult(
                success=False,
                elements=[],
                features=None,
                processing_time=time.time() - start_time,
                quality_score=0.0,
                validation_result=validation_result,
                warnings=validation_result.warnings,
                errors=[f"Bridge error: {str(e)}"],
                strategy_used="bridge_failed",
                file_path=file_path
            )
    
    async def _process_with_handlers(self, file_path: Path, validation_result, **kwargs) -> ProcessingResult:
        """Process document using Agent 4's format handlers."""
        start_time = time.time()
        
        try:
            # Get appropriate handler
            format_category = validation_result.detected_format
            handler = self.handlers.get(format_category)
            
            if not handler:
                # Use text handler as fallback
                handler = self.handlers['text']
                format_category = 'text'
            
            # Process with handler
            elements, features = await handler.process(file_path, **kwargs)
            
            # Validate output
            output_validation = await self.output_validator.validate_output(
                elements, file_path, processing_time=time.time() - start_time
            )
            
            return ProcessingResult(
                success=True,
                elements=elements,
                features=features,
                processing_time=time.time() - start_time,
                quality_score=output_validation.quality_score,
                validation_result=validation_result,
                warnings=validation_result.warnings + output_validation.warnings,
                errors=output_validation.errors,
                strategy_used=f"handler_{format_category}",
                file_path=file_path
            )
            
        except Exception as e:
            logger.error(f"Handler processing failed: {e}")
            return ProcessingResult(
                success=False,
                elements=[],
                features=None,
                processing_time=time.time() - start_time,
                quality_score=0.0,
                validation_result=validation_result,
                warnings=validation_result.warnings,
                errors=[f"Handler error: {str(e)}"],
                strategy_used="handler_failed",
                file_path=file_path
            )
    
    async def process_batch(self, file_paths: List[Path], max_concurrent: int = 5, **kwargs) -> List[ProcessingResult]:
        """Process multiple documents concurrently."""
        logger.info(f"Starting batch processing of {len(file_paths)} documents")
        
        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single(file_path: Path) -> ProcessingResult:
            async with semaphore:
                # Add batch mode flag for optimized processing
                batch_kwargs = {**kwargs, 'batch_mode': True}
                return await self.process_document(file_path, **batch_kwargs)
        
        # Process all files concurrently
        tasks = [process_single(path) for path in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch processing failed for {file_paths[i]}: {result}")
                processed_results.append(ProcessingResult(
                    success=False,
                    elements=[],
                    features=None,
                    processing_time=0.0,
                    quality_score=0.0,
                    validation_result=None,
                    warnings=[],
                    errors=[f"Batch processing exception: {str(result)}"],
                    strategy_used="batch_error",
                    file_path=file_paths[i]
                ))
            else:
                processed_results.append(result)
        
        success_count = sum(1 for r in processed_results if r.success)
        logger.info(f"Batch processing complete: {success_count}/{len(file_paths)} successful")
        
        return processed_results
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """Get all supported file formats organized by category."""
        return {
            'pdf': ['.pdf'],
            'office': ['.docx', '.xlsx', '.pptx', '.doc', '.xls', '.ppt'],
            'text': ['.txt', '.md', '.rst', '.csv', '.json', '.log'],
            'web': ['.html', '.htm', '.xml', '.xhtml'],
            'email': ['.eml', '.msg']
        }
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get current integration status and capabilities."""
        return {
            'initialized': self.is_initialized,
            'bridge_available': self.bridge is not None,
            'handlers': list(self.handlers.keys()),
            'supported_formats': len(self.get_supported_formats()),
            'total_extensions': sum(len(exts) for exts in self.get_supported_formats().values()),
            'processing_stats': self.stats.copy()
        }
    
    def _update_stats(self, result: ProcessingResult) -> None:
        """Update processing statistics."""
        self.stats['documents_processed'] += 1
        self.stats['total_processing_time'] += result.processing_time
        
        if not result.success:
            self.stats['error_count'] += 1
        
        # Update format counts
        if result.validation_result and result.validation_result.detected_format:
            format_name = result.validation_result.detected_format
            self.stats['format_counts'][format_name] = self.stats['format_counts'].get(format_name, 0) + 1
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        summary = {
            'agent_4_stats': self.stats.copy(),
            'integration_status': self.get_integration_status()
        }
        
        # Add bridge performance if available
        if self.bridge:
            try:
                bridge_summary = await self.bridge.get_performance_summary()
                summary['bridge_performance'] = bridge_summary
            except Exception as e:
                logger.warning(f"Could not get bridge performance: {e}")
        
        return summary
    
    async def close(self) -> None:
        """Clean shutdown of the integration."""
        logger.info("Shutting down UnstructuredIntegration")
        
        if self.bridge:
            try:
                await self.bridge.shutdown()
            except Exception as e:
                logger.warning(f"Bridge shutdown failed: {e}")
        
        self.is_initialized = False
        logger.info("UnstructuredIntegration shutdown complete")
    
    def _determine_selection_criteria(self, file_path: Path, validation_result, **kwargs):
        """Determine optimal selection criteria based on file characteristics."""
        if not self.SelectionCriteria:
            return None  # No selection criteria available
        
        # Default to BALANCED
        criteria = self.SelectionCriteria.BALANCED
        
        # Override based on user preference
        if 'selection_criteria' in kwargs:
            return kwargs['selection_criteria']
        
        # Intelligent selection based on file characteristics
        file_size_mb = validation_result.file_size_mb if validation_result else 0
        format_type = validation_result.detected_format if validation_result else 'unknown'
        
        # Large files - prioritize memory efficiency
        if file_size_mb > 50:
            criteria = self.SelectionCriteria.MEMORY
        # Small files - prioritize quality
        elif file_size_mb < 1:
            criteria = self.SelectionCriteria.QUALITY
        # Medium files - check format
        else:
            if format_type == 'pdf':
                criteria = self.SelectionCriteria.QUALITY  # PDFs benefit from quality processing
            elif format_type in ['text', 'web']:
                criteria = self.SelectionCriteria.SPEED    # Text files can be processed quickly
            else:
                criteria = self.SelectionCriteria.BALANCED # Default for other formats
        
        # Override for batch processing
        if kwargs.get('batch_mode', False):
            criteria = self.SelectionCriteria.SPEED
        
        logger.debug(f"Selected criteria {criteria} for {file_path.name} (size: {file_size_mb:.1f}MB, format: {format_type})")
        return criteria