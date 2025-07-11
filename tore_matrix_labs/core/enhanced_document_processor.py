#!/usr/bin/env python3
"""
Enhanced document processing pipeline with manual validation integration.
Replaces the existing document processor with support for manual validation workflow.
"""

import logging
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import uuid

from ..config.constants import ProcessingStatus, DocumentType
from ..config.settings import Settings
from ..models.document_models import Document, DocumentMetadata, ProcessingConfiguration
from ..models.manual_validation_models import (
    ManualValidationSession, ValidationStatus, DocumentSnippet, 
    SnippetType, SnippetLocation, SnippetMetadata
)
from .document_analyzer import DocumentAnalyzer, PageAnalysis
from .content_extractor import ContentExtractor, ExtractedContent
from .post_processor import PostProcessor, PostProcessingResult
from .snippet_storage import SnippetStorageManager, ToreProjectExtension


class EnhancedDocumentProcessor:
    """
    Enhanced document processing pipeline with manual validation integration.
    Supports both manual validation workflow and automated processing.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Initialize processing components
        self.document_analyzer = DocumentAnalyzer(settings)
        self.content_extractor = ContentExtractor(settings)
        self.post_processor = PostProcessor(settings)
        self.snippet_storage = SnippetStorageManager(settings)
        
        self.logger.info("Enhanced document processor initialized")
    
    def process_document_with_manual_validation(self, file_path: str, 
                                              document_type: DocumentType = DocumentType.ICAO,
                                              processing_config: Optional[ProcessingConfiguration] = None) -> Dict[str, Any]:
        """
        Execute document processing pipeline with manual validation requirement.
        
        Args:
            file_path: Path to document file
            document_type: Type of document being processed
            processing_config: Processing configuration options
            
        Returns:
            Dictionary with processing results and manual validation session
        """
        start_time = time.time()
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")
        
        self.logger.info(f"Starting document processing with manual validation: {file_path.name}")
        
        try:
            # Step 1: Create document metadata
            self.logger.info("Step 1: Creating document metadata")
            document = self._create_document_metadata(file_path, document_type, processing_config)
            document.update_status(ProcessingStatus.PROCESSING)
            
            # Step 2: Document structure analysis (lightweight)
            self.logger.info("Step 2: Analyzing document structure")
            document_analysis = self.document_analyzer.analyze_document(str(file_path))
            page_analyses = document_analysis.page_analyses
            
            # Update document metadata with page count
            document.metadata.page_count = document_analysis.total_pages
            
            # Step 3: Create manual validation session
            self.logger.info("Step 3: Creating manual validation session")
            validation_session = self._create_validation_session(document, document_analysis)
            
            # Step 4: Set status to waiting for manual validation
            document.update_status(ProcessingStatus.VALIDATING)
            
            total_time = time.time() - start_time
            
            # Return results with validation session
            results = {
                'success': True,
                'document': document,
                'page_analyses': page_analyses,
                'validation_session': validation_session,
                'processing_time': total_time,
                'status': 'awaiting_manual_validation',
                'next_step': 'complete_manual_validation'
            }
            
            self.logger.info(f"Document prepared for manual validation in {total_time:.2f}s")
            return results
            
        except Exception as e:
            self.logger.error(f"Document processing initialization failed: {str(e)}")
            if 'document' in locals():
                document.update_status(ProcessingStatus.FAILED)
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time,
                'status': 'failed'
            }
    
    def complete_processing_after_validation(self, document: Document, 
                                           validation_session: ManualValidationSession,
                                           page_analyses: List[PageAnalysis]) -> Dict[str, Any]:
        """
        Complete document processing after manual validation is finished.
        
        Args:
            document: Document being processed
            validation_session: Completed validation session
            page_analyses: Page analyses from initial processing
            
        Returns:
            Dictionary with complete processing results
        """
        start_time = time.time()
        
        self.logger.info(f"Completing processing after manual validation: {document.metadata.file_name}")
        
        try:
            # Step 1: Process validated snippets
            self.logger.info("Step 1: Processing validated snippets")
            snippet_results = self._process_validated_snippets(document, validation_session)
            
            # Step 2: Generate exclusion zones for text extraction
            self.logger.info("Step 2: Generating exclusion zones")
            exclusion_zones = self._generate_exclusion_zones(validation_session)
            
            # Step 3: Content extraction with exclusion zones
            self.logger.info("Step 3: Extracting content with exclusion zones")
            extracted_content = self._extract_content_with_exclusions(
                document.metadata.file_path, page_analyses, exclusion_zones
            )
            
            # Step 3.5: Check for auto-detection conflicts
            if extracted_content.has_conflicts():
                conflicts = extracted_content.get_all_conflicts()
                self.logger.warning(f"Found {len(conflicts)} auto-detection conflicts requiring resolution")
                
                # Return early with conflict resolution required
                return {
                    'success': False,
                    'status': 'conflicts_require_resolution',
                    'conflicts': conflicts,
                    'document': document,
                    'validation_session': validation_session,
                    'page_analyses': page_analyses,
                    'extracted_content': extracted_content,
                    'exclusion_zones': exclusion_zones,
                    'processing_time': time.time() - start_time,
                    'next_step': 'resolve_conflicts_and_continue'
                }
            
            # Step 4: Parallel processing of specialized content
            self.logger.info("Step 4: Processing specialized content")
            specialized_results = self._process_specialized_content(validation_session, document)
            
            # Step 5: Merge results
            self.logger.info("Step 5: Merging processing results")
            merged_content = self._merge_content_results(
                extracted_content, specialized_results, validation_session
            )
            
            # Step 6: Post-processing and quality assessment
            self.logger.info("Step 6: Post-processing and quality assessment")
            post_processing_result = self.post_processor.process_document(
                document, merged_content, page_analyses
            )
            
            # Step 7: Update document with final results
            document.quality_score = post_processing_result.quality_assessment.overall_score
            document.quality_level = post_processing_result.quality_assessment.quality_level
            document.add_validation_result(post_processing_result.validation_result)
            
            # Update document with content statistics
            document.extracted_content = {
                'text_elements_count': len(merged_content.text_elements),
                'tables_count': len(merged_content.tables),
                'images_count': len(merged_content.images),
                'extraction_time': merged_content.extraction_time,
                'initial_quality_score': merged_content.quality_score,
                'manual_validation_snippets': len(validation_session.get_all_snippets()),
                'snippets_by_type': {
                    'images': len(validation_session.get_snippets_by_type(SnippetType.IMAGE)),
                    'tables': len(validation_session.get_snippets_by_type(SnippetType.TABLE)),
                    'diagrams': len(validation_session.get_snippets_by_type(SnippetType.DIAGRAM))
                }
            }
            
            # Determine final status
            if post_processing_result.export_ready:
                if post_processing_result.validation_result.state.value == 'approved':
                    document.update_status(ProcessingStatus.APPROVED)
                else:
                    document.update_status(ProcessingStatus.VALIDATED)
            else:
                document.update_status(ProcessingStatus.FAILED)
            
            total_time = time.time() - start_time
            
            # Compile comprehensive results
            results = {
                'success': True,
                'document': document,
                'page_analyses': page_analyses,
                'extracted_content': merged_content,
                'post_processing': post_processing_result,
                'validation_session': validation_session,
                'snippet_results': snippet_results,
                'specialized_results': specialized_results,
                'processing_time': total_time,
                'status': 'completed',
                'summary': self._generate_processing_summary(
                    document, post_processing_result, validation_session, total_time
                )
            }
            
            self.logger.info(f"Enhanced document processing completed in {total_time:.2f}s")
            return results
            
        except Exception as e:
            self.logger.error(f"Post-validation processing failed: {str(e)}")
            document.update_status(ProcessingStatus.FAILED)
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time,
                'status': 'failed'
            }
    
    def _create_document_metadata(self, file_path: Path, document_type: DocumentType,
                                 processing_config: Optional[ProcessingConfiguration]) -> Document:
        """Create document with metadata."""
        # Get file statistics
        file_stat = file_path.stat()
        
        # Create metadata
        metadata = DocumentMetadata(
            file_name=file_path.name,
            file_path=str(file_path),
            file_size=file_stat.st_size,
            file_type=file_path.suffix.lower(),
            creation_date=datetime.fromtimestamp(file_stat.st_ctime),
            modification_date=datetime.fromtimestamp(file_stat.st_mtime),
            page_count=0  # Will be updated after analysis
        )
        
        # Use provided config or create default
        if processing_config is None:
            processing_config = ProcessingConfiguration()
        
        # Create document
        document = Document(
            id=str(uuid.uuid4()),
            metadata=metadata,
            document_type=document_type,
            processing_status=ProcessingStatus.PENDING,
            processing_config=processing_config,
            quality_level=self.settings.get('default_quality_level', 'medium'),
            quality_score=0.0
        )
        
        return document
    
    def _create_validation_session(self, document: Document, 
                                 document_analysis: Any) -> ManualValidationSession:
        """Create manual validation session for the document."""
        session = ManualValidationSession(
            document_id=document.id,
            document_path=document.metadata.file_path,
            session_id=str(uuid.uuid4()),
            status=ValidationStatus.PENDING,
            total_pages=document_analysis.total_pages
        )
        
        return session
    
    def _process_validated_snippets(self, document: Document, 
                                  validation_session: ManualValidationSession) -> Dict[str, Any]:
        """Process all validated snippets (extract images, context, etc.)."""
        results = {
            'processed_snippets': 0,
            'failed_snippets': 0,
            'snippets_by_type': {'IMAGE': 0, 'TABLE': 0, 'DIAGRAM': 0},
            'processing_details': []
        }
        
        for snippet in validation_session.get_all_snippets():
            try:
                # Process snippet (extract image, context, save metadata)
                success = self.snippet_storage.process_snippet(
                    document.metadata.file_path, 
                    snippet,
                    extract_image=True,
                    extract_context=True
                )
                
                if success:
                    results['processed_snippets'] += 1
                    results['snippets_by_type'][snippet.snippet_type.value] += 1
                    results['processing_details'].append({
                        'snippet_id': snippet.id,
                        'type': snippet.snippet_type.value,
                        'status': 'success',
                        'image_file': snippet.image_file
                    })
                else:
                    results['failed_snippets'] += 1
                    results['processing_details'].append({
                        'snippet_id': snippet.id,
                        'type': snippet.snippet_type.value,
                        'status': 'failed',
                        'error': 'Processing failed'
                    })
            
            except Exception as e:
                results['failed_snippets'] += 1
                results['processing_details'].append({
                    'snippet_id': snippet.id,
                    'type': snippet.snippet_type.value,
                    'status': 'error',
                    'error': str(e)
                })
                self.logger.error(f"Error processing snippet {snippet.id}: {e}")
        
        return results
    
    def _generate_exclusion_zones(self, validation_session: ManualValidationSession) -> Dict[int, List[Dict[str, Any]]]:
        """Generate exclusion zones for text extraction."""
        exclusion_zones = {}
        
        for page_num, page_result in validation_session.page_results.items():
            zones = []
            for snippet in page_result.snippets:
                zones.append({
                    'type': snippet.snippet_type.value,
                    'bbox': snippet.location.bbox,
                    'snippet_id': snippet.id,
                    'exclude_from_text': True
                })
            exclusion_zones[page_num] = zones
        
        return exclusion_zones
    
    def _extract_content_with_exclusions(self, file_path: str, 
                                       page_analyses: List[PageAnalysis],
                                       exclusion_zones: Dict[int, List[Dict[str, Any]]]) -> ExtractedContent:
        """Extract content while excluding manually validated areas."""
        # Pass exclusion zones to content extractor
        extracted_content = self.content_extractor.extract_content(
            file_path, page_analyses, exclusion_zones=exclusion_zones
        )
        
        return extracted_content
    
    def _process_specialized_content(self, validation_session: ManualValidationSession, 
                                   document: Document) -> Dict[str, Any]:
        """
        Process specialized content (images, tables, diagrams) from validation using AI-powered toolsets.
        
        This method completes the critical integration between manual validation and specialized processing:
        - IMAGES: AI-powered description generation with comprehensive visual analysis
        - TABLES: Advanced multi-strategy extraction (Camelot, Tabula, PyMuPDF, OCR fallback)
        - DIAGRAMS: Flow analysis with element extraction and relationship mapping
        
        Each area type is processed with its respective specialized toolset for maximum accuracy.
        Graceful fallbacks ensure robust operation even when advanced processing fails.
        
        Returns comprehensive results ready for LLM integration and final document assembly.
        """
        results = {
            'images': [],
            'tables': [],
            'diagrams': []
        }
        
        # Process images with ImageToolset for AI description generation
        for image_snippet in validation_session.get_snippets_by_type(SnippetType.IMAGE):
            try:
                # Initialize ImageToolset for AI-powered description generation
                from ..specialized_toolsets.image_toolset import ImageToolset
                import fitz
                
                image_toolset = ImageToolset(self.settings)
                
                # Load PDF document for toolset processing
                pdf_document = fitz.open(document.metadata.file_path)
                
                # Prepare area data for ImageToolset processing
                area_data = {
                    'snippet_id': image_snippet.id,
                    'bbox': image_snippet.location.bbox,
                    'page': image_snippet.location.page,
                    'type': 'IMAGE',
                    'context': image_snippet.metadata.context_text,
                    'image_file': image_snippet.image_file
                }
                
                self.logger.info(f"Processing IMAGE snippet {image_snippet.id} with AI description generation")
                
                # Process with ImageToolset for comprehensive analysis
                toolset_result = image_toolset.process_area(area_data, pdf_document)
                pdf_document.close()
                
                if toolset_result.get('success', False):
                    # Successful AI processing
                    ai_description = toolset_result.get('description', 'AI-generated comprehensive image description')
                    ai_analysis = toolset_result.get('analysis', {})
                    extracted_text = toolset_result.get('extracted_text', '')
                    quality_score = toolset_result.get('quality_score', 0.8)
                    
                    self.logger.info(f"AI description generated for IMAGE {image_snippet.id}: {len(ai_description)} chars")
                else:
                    # Fallback for failed AI processing
                    ai_description = f'Professional image at page {image_snippet.location.page + 1} - AI analysis temporarily unavailable'
                    ai_analysis = {'processing_status': 'failed', 'error': toolset_result.get('error', 'Unknown error')}
                    extracted_text = ''
                    quality_score = 0.3
                    
                    self.logger.warning(f"AI processing failed for IMAGE {image_snippet.id}: {toolset_result.get('error', 'Unknown error')}")
                
            except Exception as e:
                # Exception handling with graceful fallback
                self.logger.error(f"Error in AI image processing for {image_snippet.id}: {e}")
                ai_description = f'Technical diagram/image on page {image_snippet.location.page + 1} - Professional content requiring manual review'
                ai_analysis = {'processing_error': str(e), 'requires_manual_review': True}
                extracted_text = ''
                quality_score = 0.2
            
            # Create comprehensive image result with AI enhancement
            image_result = {
                'snippet_id': image_snippet.id,
                'type': 'IMAGE',
                'location': image_snippet.location.to_dict(),
                'image_file': image_snippet.image_file,  # Preserved for UI preview
                'description': ai_description,  # AI-generated or professional fallback
                'ai_analysis': ai_analysis,  # Detailed AI analysis data
                'extracted_text': extracted_text,  # OCR text from image if available
                'context': image_snippet.metadata.context_text,
                'quality_score': quality_score,  # Processing quality indicator
                'processing_method': 'ai_enhanced'  # Processing method indicator
            }
            results['images'].append(image_result)
        
        # Process tables with TableToolset for advanced extraction and correction
        for table_snippet in validation_session.get_snippets_by_type(SnippetType.TABLE):
            try:
                # Initialize TableToolset for advanced table extraction
                from ..specialized_toolsets.table_toolset import TableToolset
                import fitz
                
                table_toolset = TableToolset(self.settings)
                
                # Load PDF document for toolset processing
                pdf_document = fitz.open(document.metadata.file_path)
                
                # Prepare area data for TableToolset processing
                area_data = {
                    'snippet_id': table_snippet.id,
                    'bbox': table_snippet.location.bbox,
                    'page': table_snippet.location.page,
                    'type': 'TABLE',
                    'context': table_snippet.metadata.context_text,
                    'image_file': table_snippet.image_file
                }
                
                self.logger.info(f"Processing TABLE snippet {table_snippet.id} with advanced extraction strategies")
                
                # Process with TableToolset using multiple extraction strategies
                toolset_result = table_toolset.process_area(area_data, pdf_document)
                pdf_document.close()
                
                if toolset_result.get('success', False):
                    # Successful table extraction
                    extracted_data = toolset_result.get('extracted_data', {})
                    table_structure = toolset_result.get('table_structure', {})
                    extraction_method = toolset_result.get('extraction_method', 'advanced_parsing')
                    quality_score = toolset_result.get('quality_score', 0.85)
                    
                    # Generate human-readable summary
                    rows_count = len(extracted_data.get('rows', []))
                    cols_count = len(extracted_data.get('columns', []))
                    table_summary = f"Table with {rows_count} rows and {cols_count} columns extracted using {extraction_method}"
                    
                    self.logger.info(f"Table extraction successful for {table_snippet.id}: {rows_count}x{cols_count} table")
                else:
                    # Fallback for failed extraction
                    extracted_data = {
                        'error': 'Advanced table extraction failed',
                        'fallback_text': 'Complex table structure detected - manual review recommended'
                    }
                    table_structure = {'extraction_failed': True}
                    extraction_method = 'fallback'
                    quality_score = 0.3
                    table_summary = f'Complex table structure on page {table_snippet.location.page + 1} - extraction partially failed'
                    
                    self.logger.warning(f"Table extraction failed for {table_snippet.id}: {toolset_result.get('error', 'Unknown error')}")
                
            except Exception as e:
                # Exception handling with graceful fallback
                self.logger.error(f"Error in table processing for {table_snippet.id}: {e}")
                extracted_data = {
                    'error': f'Table processing error: {str(e)}',
                    'requires_manual_extraction': True
                }
                table_structure = {'processing_error': str(e)}
                extraction_method = 'error_fallback'
                quality_score = 0.1
                table_summary = f'Data table on page {table_snippet.location.page + 1} - requires manual extraction due to processing error'
            
            # Create comprehensive table result with advanced extraction
            table_result = {
                'snippet_id': table_snippet.id,
                'type': 'TABLE',
                'location': table_snippet.location.to_dict(),
                'image_file': table_snippet.image_file,  # Preserved for UI preview
                'extracted_data': extracted_data,  # Structured table data
                'table_structure': table_structure,  # Table structure analysis
                'extraction_method': extraction_method,  # Method used for extraction
                'table_summary': table_summary,  # Human-readable summary
                'context': table_snippet.metadata.context_text,
                'quality_score': quality_score,  # Extraction quality indicator
                'processing_method': 'multi_strategy_extraction'  # Processing method indicator
            }
            results['tables'].append(table_result)
        
        # Process diagrams with DiagramToolset for flow analysis and element extraction
        for diagram_snippet in validation_session.get_snippets_by_type(SnippetType.DIAGRAM):
            try:
                # Initialize DiagramToolset for comprehensive diagram analysis
                from ..specialized_toolsets.diagram_toolset import DiagramToolset
                import fitz
                
                diagram_toolset = DiagramToolset(self.settings)
                
                # Load PDF document for toolset processing
                pdf_document = fitz.open(document.metadata.file_path)
                
                # Prepare area data for DiagramToolset processing
                area_data = {
                    'snippet_id': diagram_snippet.id,
                    'bbox': diagram_snippet.location.bbox,
                    'page': diagram_snippet.location.page,
                    'type': 'DIAGRAM',
                    'context': diagram_snippet.metadata.context_text,
                    'image_file': diagram_snippet.image_file
                }
                
                self.logger.info(f"Processing DIAGRAM snippet {diagram_snippet.id} with flow analysis and element extraction")
                
                # Process with DiagramToolset for comprehensive analysis
                toolset_result = diagram_toolset.process_area(area_data, pdf_document)
                pdf_document.close()
                
                if toolset_result.get('success', False):
                    # Successful diagram processing
                    processed_data = toolset_result.get('processed_data', {})
                    flow_analysis = toolset_result.get('flow_analysis', {})
                    diagram_type = toolset_result.get('diagram_type', 'technical_diagram')
                    elements = toolset_result.get('elements', [])
                    relationships = toolset_result.get('relationships', [])
                    quality_score = toolset_result.get('quality_score', 0.8)
                    
                    # Generate comprehensive diagram summary
                    elements_count = len(elements)
                    relationships_count = len(relationships)
                    flow_info = flow_analysis.get('flow_summary', 'flow analysis complete')
                    diagram_summary = f"{diagram_type.replace('_', ' ').title()} with {elements_count} elements, {relationships_count} relationships - {flow_info}"
                    
                    self.logger.info(f"Diagram analysis successful for {diagram_snippet.id}: {diagram_type} with {elements_count} elements")
                else:
                    # Fallback for failed processing
                    processed_data = {
                        'error': 'Advanced diagram analysis failed',
                        'fallback_description': 'Complex technical diagram requiring specialized analysis'
                    }
                    flow_analysis = {'analysis_failed': True}
                    diagram_type = 'complex_technical'
                    elements = []
                    relationships = []
                    quality_score = 0.4
                    diagram_summary = f'Technical diagram on page {diagram_snippet.location.page + 1} - advanced analysis partially failed'
                    
                    self.logger.warning(f"Diagram processing failed for {diagram_snippet.id}: {toolset_result.get('error', 'Unknown error')}")
                
            except Exception as e:
                # Exception handling with graceful fallback
                self.logger.error(f"Error in diagram processing for {diagram_snippet.id}: {e}")
                processed_data = {
                    'error': f'Diagram processing error: {str(e)}',
                    'requires_manual_analysis': True
                }
                flow_analysis = {'processing_error': str(e)}
                diagram_type = 'processing_error'
                elements = []
                relationships = []
                quality_score = 0.2
                diagram_summary = f'Professional diagram on page {diagram_snippet.location.page + 1} - requires manual analysis due to processing complexity'
            
            # Create comprehensive diagram result with flow analysis
            diagram_result = {
                'snippet_id': diagram_snippet.id,
                'type': 'DIAGRAM',
                'location': diagram_snippet.location.to_dict(),
                'image_file': diagram_snippet.image_file,  # Preserved for UI preview
                'processed_data': processed_data,  # Comprehensive diagram data
                'flow_analysis': flow_analysis,  # Flow and relationship analysis
                'diagram_type': diagram_type,  # Detected diagram type
                'elements': elements,  # Extracted diagram elements
                'relationships': relationships,  # Element relationships and connections
                'diagram_summary': diagram_summary,  # Human-readable summary
                'context': diagram_snippet.metadata.context_text,
                'quality_score': quality_score,  # Processing quality indicator
                'processing_method': 'advanced_flow_analysis'  # Processing method indicator
            }
            results['diagrams'].append(diagram_result)
        
        return results
    
    def _merge_content_results(self, extracted_content: ExtractedContent, 
                             specialized_results: Dict[str, Any],
                             validation_session: ManualValidationSession) -> ExtractedContent:
        """Merge regular extracted content with specialized content."""
        # Create new merged content
        merged_content = ExtractedContent(
            text_elements=extracted_content.text_elements,
            tables=extracted_content.tables,
            images=extracted_content.images,
            extraction_time=extracted_content.extraction_time,
            quality_score=extracted_content.quality_score
        )
        
        # Add specialized content references
        for image_result in specialized_results['images']:
            merged_content.images.append({
                'type': 'manual_validation_image',
                'snippet_id': image_result['snippet_id'],
                'location': image_result['location'],
                'image_file': image_result['image_file'],
                'description': image_result['description']
            })
        
        for table_result in specialized_results['tables']:
            merged_content.tables.append({
                'type': 'manual_validation_table',
                'snippet_id': table_result['snippet_id'],
                'location': table_result['location'],
                'image_file': table_result['image_file'],
                'extracted_data': table_result['extracted_data']
            })
        
        # Add diagram references (treated as special images for now)
        for diagram_result in specialized_results['diagrams']:
            merged_content.images.append({
                'type': 'manual_validation_diagram',
                'snippet_id': diagram_result['snippet_id'],
                'location': diagram_result['location'],
                'image_file': diagram_result['image_file'],
                'processed_data': diagram_result['processed_data']
            })
        
        return merged_content
    
    def _generate_processing_summary(self, document: Document, 
                                   post_processing_result: PostProcessingResult,
                                   validation_session: ManualValidationSession,
                                   total_time: float) -> Dict[str, Any]:
        """Generate comprehensive processing summary."""
        validation_stats = validation_session.get_statistics()
        
        return {
            'document_id': document.id,
            'file_name': document.metadata.file_name,
            'file_size': document.metadata.file_size,
            'page_count': document.metadata.page_count,
            'processing_time': total_time,
            'final_status': document.processing_status.value,
            'quality_score': document.quality_score,
            'quality_level': document.quality_level.value,
            'manual_validation': {
                'total_snippets': validation_stats['total_snippets'],
                'snippets_by_type': validation_stats['type_counts'],
                'pages_validated': validation_stats['validated_pages'],
                'completion_percentage': validation_stats['completion_percentage']
            },
            'content_extraction': {
                'text_elements': len(document.extracted_content.get('text_elements', [])),
                'tables': len(document.extracted_content.get('tables', [])),
                'images': len(document.extracted_content.get('images', [])),
                'manual_snippets': validation_stats['total_snippets']
            },
            'post_processing': {
                'corrections_count': post_processing_result.corrections_count,
                'export_ready': post_processing_result.export_ready,
                'validation_state': post_processing_result.validation_result.state.value
            }
        }
    
    def continue_processing_after_conflict_resolution(self, document: Document, 
                                                    validation_session: ManualValidationSession,
                                                    page_analyses: List[PageAnalysis],
                                                    extracted_content: Any,
                                                    exclusion_zones: Dict[int, List[Dict[str, Any]]],
                                                    conflict_resolutions: Dict[str, Any]) -> Dict[str, Any]:
        """
        Continue processing after conflict resolution is complete.
        
        Args:
            document: Document being processed
            validation_session: Manual validation session
            page_analyses: Page analyses from initial processing
            extracted_content: Extracted content with conflicts
            exclusion_zones: Original exclusion zones
            conflict_resolutions: Resolution decisions for each conflict
            
        Returns:
            Dictionary with complete processing results
        """
        start_time = time.time()
        
        self.logger.info(f"Continuing processing after conflict resolution: {document.metadata.file_name}")
        self.logger.info(f"Conflict resolutions: {conflict_resolutions.get('resolution_summary', {})}")
        
        try:
            # Step 1: Apply conflict resolutions to exclusion zones
            self.logger.info("Step 1: Applying conflict resolutions")
            updated_exclusion_zones = self._apply_conflict_resolutions(
                exclusion_zones, conflict_resolutions, validation_session
            )
            
            # Step 2: Re-extract content with updated exclusion zones
            self.logger.info("Step 2: Re-extracting content with resolved conflicts")
            final_extracted_content = self._extract_content_with_exclusions(
                document.metadata.file_path, page_analyses, updated_exclusion_zones
            )
            
            # Step 3: Continue with normal processing flow
            return self._continue_normal_processing_flow(
                document, validation_session, page_analyses, final_extracted_content, start_time
            )
            
        except Exception as e:
            self.logger.error(f"Post-conflict processing failed: {str(e)}")
            document.update_status(ProcessingStatus.FAILED)
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time,
                'status': 'failed'
            }
    
    def _apply_conflict_resolutions(self, exclusion_zones: Dict[int, List[Dict[str, Any]]],
                                  conflict_resolutions: Dict[str, Any],
                                  validation_session: ManualValidationSession) -> Dict[int, List[Dict[str, Any]]]:
        """Apply conflict resolutions to update exclusion zones."""
        updated_zones = exclusion_zones.copy()
        
        # Process each resolution
        for conflict_id, resolution in conflict_resolutions.get('resolutions', {}).items():
            if resolution == 'force_text':
                # Remove all exclusion zones for areas where text extraction is forced
                # This allows text to be extracted from manually classified areas
                self.logger.info(f"Forcing text extraction for conflict {conflict_id}")
                # Implementation would need conflict ID to zone mapping
            elif resolution == 'use_auto':
                # Update manual validation session with auto-detected classification
                self.logger.info(f"Using auto-detection for conflict {conflict_id}")
                # Implementation would update validation session
            # 'keep_manual' requires no changes to exclusion zones
        
        return updated_zones
    
    def _continue_normal_processing_flow(self, document: Document, 
                                       validation_session: ManualValidationSession,
                                       page_analyses: List[PageAnalysis],
                                       extracted_content: Any,
                                       start_time: float) -> Dict[str, Any]:
        """Continue with the normal processing flow after conflict resolution."""
        # Step 4: Parallel processing of specialized content
        self.logger.info("Step 4: Processing specialized content")
        specialized_results = self._process_specialized_content(validation_session, document)
        
        # Step 5: Merge results
        self.logger.info("Step 5: Merging processing results")
        merged_content = self._merge_content_results(
            extracted_content, specialized_results, validation_session
        )
        
        # Step 6: Post-processing and quality assessment
        self.logger.info("Step 6: Post-processing and quality assessment")
        post_processing_result = self.post_processor.process_document(
            document, merged_content, page_analyses
        )
        
        # Step 7: Update document with final results
        document.quality_score = post_processing_result.quality_assessment.overall_score
        document.quality_level = post_processing_result.quality_assessment.quality_level
        document.add_validation_result(post_processing_result.validation_result)
        
        # Update document with content statistics
        document.extracted_content = {
            'text_elements_count': len(merged_content.text_elements),
            'tables_count': len(merged_content.tables),
            'images_count': len(merged_content.images),
            'extraction_time': merged_content.extraction_time,
            'initial_quality_score': merged_content.quality_score,
            'manual_validation_snippets': len(validation_session.get_all_snippets()),
            'snippets_by_type': {
                'images': len(validation_session.get_snippets_by_type(SnippetType.IMAGE)),
                'tables': len(validation_session.get_snippets_by_type(SnippetType.TABLE)),
                'diagrams': len(validation_session.get_snippets_by_type(SnippetType.DIAGRAM))
            }
        }
        
        # Determine final status
        if post_processing_result.export_ready:
            if post_processing_result.validation_result.state.value == 'approved':
                document.update_status(ProcessingStatus.APPROVED)
            else:
                document.update_status(ProcessingStatus.VALIDATED)
        else:
            document.update_status(ProcessingStatus.FAILED)
        
        total_time = time.time() - start_time
        
        # Compile comprehensive results
        results = {
            'success': True,
            'document': document,
            'page_analyses': page_analyses,
            'extracted_content': merged_content,
            'post_processing': post_processing_result,
            'validation_session': validation_session,
            'specialized_results': specialized_results,
            'processing_time': total_time,
            'status': 'completed',
            'summary': self._generate_processing_summary(
                document, post_processing_result, validation_session, total_time
            )
        }
        
        self.logger.info(f"Enhanced document processing completed in {total_time:.2f}s")
        return results
    
    def save_validation_session_to_project(self, project_data: Dict[str, Any], 
                                         validation_session: ManualValidationSession) -> Dict[str, Any]:
        """Save validation session to .tore project format."""
        return ToreProjectExtension.add_manual_validation_to_project(
            project_data, validation_session
        )
    
    def load_validation_session_from_project(self, project_data: Dict[str, Any]) -> Optional[ManualValidationSession]:
        """Load validation session from .tore project format."""
        return ToreProjectExtension.load_manual_validation_from_project(project_data)
    
    def get_exclusion_zones_for_page(self, project_data: Dict[str, Any], 
                                   page_number: int) -> List[Dict[str, Any]]:
        """Get exclusion zones for a specific page."""
        return ToreProjectExtension.get_exclusion_zones_for_page(project_data, page_number)