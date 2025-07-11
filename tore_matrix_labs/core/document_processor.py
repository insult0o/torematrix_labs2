#!/usr/bin/env python3
"""
Complete document processing pipeline for TORE Matrix Labs.
Orchestrates analysis, extraction, post-processing, and quality assessment.
"""

import logging
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

from ..config.constants import ProcessingStatus, DocumentType
from ..config.settings import Settings
from ..models.document_models import Document, DocumentMetadata, ProcessingConfiguration
from .document_analyzer import DocumentAnalyzer, PageAnalysis
from .content_extractor import ContentExtractor, ExtractedContent
from .post_processor import PostProcessor, PostProcessingResult


class DocumentProcessor:
    """
    Complete document processing pipeline that orchestrates all processing stages
    from initial analysis through post-processing and quality assessment.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Initialize processing components
        self.document_analyzer = DocumentAnalyzer(settings)
        self.content_extractor = ContentExtractor(settings)
        self.post_processor = PostProcessor(settings)
        
        self.logger.info("Document processor initialized")
    
    def process_document(self, file_path: str, document_type: DocumentType = DocumentType.ICAO,
                        processing_config: Optional[ProcessingConfiguration] = None) -> Dict[str, Any]:
        """
        Execute complete document processing pipeline.
        
        Args:
            file_path: Path to document file
            document_type: Type of document being processed
            processing_config: Processing configuration options
            
        Returns:
            Dictionary with complete processing results
        """
        start_time = time.time()
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Document file not found: {file_path}")
        
        self.logger.info(f"Starting complete document processing: {file_path.name}")
        
        try:
            # Step 1: Create document metadata
            self.logger.info("Step 1: Creating document metadata")
            document = self._create_document_metadata(file_path, document_type, processing_config)
            document.update_status(ProcessingStatus.PROCESSING)
            
            # Step 2: Document structure analysis
            self.logger.info("Step 2: Analyzing document structure")
            document_analysis = self.document_analyzer.analyze_document(str(file_path))
            page_analyses = document_analysis.page_analyses
            
            # Update document metadata with page count
            document.metadata.page_count = document_analysis.total_pages
            
            # Step 3: Content extraction
            self.logger.info("Step 3: Extracting content")
            extracted_content = self.content_extractor.extract_content(str(file_path), page_analyses)
            
            # Update document with extracted content (FULL CONTENT SAVE)
            import dataclasses
            import json
            
            def safe_serialize(obj):
                """Safely serialize objects to JSON-compatible format."""
                try:
                    if dataclasses.is_dataclass(obj):
                        # Convert dataclass to dict and recursively serialize all fields
                        data_dict = dataclasses.asdict(obj)
                        return {k: safe_serialize(v) for k, v in data_dict.items()}
                    elif hasattr(obj, 'value'):  # Handle enums (including ElementType) - CHECK THIS FIRST
                        return str(obj.value)
                    elif hasattr(obj, '__dict__'):
                        return {k: safe_serialize(v) for k, v in obj.__dict__.items() if not k.startswith('_')}
                    elif isinstance(obj, (list, tuple)):
                        return [safe_serialize(item) for item in obj]
                    elif isinstance(obj, dict):
                        return {k: safe_serialize(v) for k, v in obj.items()}
                    else:
                        # Try to serialize to check if it's JSON-compatible
                        json.dumps(obj)
                        return obj
                except (TypeError, ValueError):
                    return str(obj)
            
            document.extracted_content = {
                'text_elements_count': len(extracted_content.text_elements),
                'tables_count': len(extracted_content.tables),
                'images_count': len(extracted_content.images),
                'extraction_time': extracted_content.extraction_time,
                'initial_quality_score': extracted_content.quality_score,
                # Save the actual content data with safe serialization
                'text_elements': [safe_serialize(elem) for elem in extracted_content.text_elements],
                'tables': [safe_serialize(table) for table in extracted_content.tables],
                'images': [safe_serialize(image) for image in extracted_content.images],
                'metadata': safe_serialize(extracted_content.metadata)
            }
            document.update_status(ProcessingStatus.EXTRACTED)
            
            # Ensure processing status is also JSON-serializable
            if hasattr(document.processing_status, 'value'):
                document.processing_status = str(document.processing_status.value)
            elif hasattr(document.processing_status, 'name'):
                document.processing_status = str(document.processing_status.name)
            else:
                document.processing_status = str(document.processing_status)
            
            # Step 4: Post-processing and quality assessment
            self.logger.info("Step 4: Post-processing and quality assessment")
            post_processing_result = self.post_processor.process_document(
                document, extracted_content, page_analyses
            )
            
            # Update document with final results
            document.quality_score = post_processing_result.quality_assessment.overall_score
            document.quality_level = post_processing_result.quality_assessment.quality_level
            document.add_validation_result(post_processing_result.validation_result)
            
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
                'extracted_content': extracted_content,
                'post_processing': post_processing_result,
                'processing_time': total_time,
                'summary': self._generate_processing_summary(
                    document, post_processing_result, total_time
                )
            }
            
            self.logger.info(f"Document processing completed successfully in {total_time:.2f}s")
            return results
            
        except Exception as e:
            self.logger.error(f"Document processing failed: {str(e)}")
            if 'document' in locals():
                document.update_status(ProcessingStatus.FAILED)
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': time.time() - start_time
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
            page_count=0,  # Will be updated after analysis
            title=file_path.stem
        )
        
        # Use provided config or create default
        if processing_config is None:
            processing_config = ProcessingConfiguration()
        
        # Create document
        document = Document(
            id=f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_path.stem}",
            metadata=metadata,
            document_type=document_type,
            processing_status=ProcessingStatus.PENDING,
            processing_config=processing_config,
            quality_level=self.settings.processing.default_quality_level,
            quality_score=0.0
        )
        
        return document
    
    def _generate_processing_summary(self, document: Document, 
                                   post_processing_result: PostProcessingResult,
                                   total_time: float) -> Dict[str, Any]:
        """Generate comprehensive processing summary."""
        quality_assessment = post_processing_result.quality_assessment
        validation_result = post_processing_result.validation_result
        
        summary = {
            'document_info': {
                'id': document.id,
                'file_name': document.metadata.file_name,
                'file_size': document.metadata.file_size,
                'document_type': document.document_type.value,
                'processing_status': document.processing_status.value
            },
            'processing_metrics': {
                'total_time': total_time,
                'extraction_time': document.extracted_content.get('extraction_time', 0),
                'post_processing_time': post_processing_result.processing_time,
                'total_steps': len(document.processing_history)
            },
            'content_metrics': {
                'text_elements': document.extracted_content.get('text_elements_count', 0),
                'tables': document.extracted_content.get('tables_count', 0),
                'images': document.extracted_content.get('images_count', 0),
                'chunk_count': post_processing_result.content_optimization.get('chunk_count', 0),
                'duplicates_removed': post_processing_result.content_optimization.get('duplicate_removal_count', 0)
            },
            'quality_metrics': {
                'overall_score': quality_assessment.overall_score,
                'quality_level': quality_assessment.quality_level.value,
                'total_issues': len(quality_assessment.issues),
                'critical_issues': len([i for i in quality_assessment.issues if i.severity == 'critical']),
                'major_issues': len([i for i in quality_assessment.issues if i.severity == 'major']),
                'minor_issues': len([i for i in quality_assessment.issues if i.severity == 'minor'])
            },
            'validation_status': {
                'state': validation_result.state.value,
                'confidence': validation_result.confidence,
                'issues_found': len(validation_result.issues_found),
                'export_ready': post_processing_result.export_ready
            },
            'recommendations': post_processing_result.recommendations,
            'next_steps': self._generate_next_steps(post_processing_result)
        }
        
        return summary
    
    def _generate_next_steps(self, post_processing_result: PostProcessingResult) -> List[str]:
        """Generate recommended next steps based on processing results."""
        next_steps = []
        
        if post_processing_result.export_ready:
            next_steps.append("✅ Document ready for export to production systems")
            next_steps.append("🚀 Can be used for RAG indexing or LLM fine-tuning")
        else:
            next_steps.append("⚠️ Document requires review before production use")
            
            # Add specific action items based on validation state
            validation_state = post_processing_result.validation_result.state.value
            if validation_state == 'rejected':
                next_steps.append("❌ Address critical issues and reprocess document")
            elif validation_state == 'pending_review':
                next_steps.append("👤 Manual review required - check quality issues")
        
        # Add quality-specific recommendations
        quality_score = post_processing_result.quality_assessment.overall_score
        if quality_score < 0.7:
            next_steps.append("🔧 Consider re-processing with different extraction settings")
        elif quality_score < 0.8:
            next_steps.append("✨ Minor quality improvements recommended")
        
        # Add content-specific recommendations
        if post_processing_result.content_optimization.get('duplicate_removal_count', 0) > 5:
            next_steps.append("📄 Source document may have redundant content")
        
        return next_steps
    
    def process_batch(self, file_paths: List[str], document_type: DocumentType = DocumentType.ICAO,
                     output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Process multiple documents in batch.
        
        Args:
            file_paths: List of document file paths
            document_type: Type of documents being processed
            output_dir: Optional output directory for results
            
        Returns:
            Dictionary with batch processing results
        """
        self.logger.info(f"Starting batch processing of {len(file_paths)} documents")
        start_time = time.time()
        
        results = {
            'total_documents': len(file_paths),
            'successful': 0,
            'failed': 0,
            'processing_time': 0,
            'documents': [],
            'summary': {}
        }
        
        for i, file_path in enumerate(file_paths):
            self.logger.info(f"Processing document {i+1}/{len(file_paths)}: {Path(file_path).name}")
            
            try:
                doc_result = self.process_document(file_path, document_type)
                
                if doc_result['success']:
                    results['successful'] += 1
                    results['documents'].append(doc_result)
                    
                    # Export individual results if output directory specified
                    if output_dir:
                        self._export_document_results(doc_result, output_dir)
                else:
                    results['failed'] += 1
                    results['documents'].append(doc_result)
                    
            except Exception as e:
                self.logger.error(f"Failed to process {file_path}: {str(e)}")
                results['failed'] += 1
                results['documents'].append({
                    'success': False,
                    'file_path': file_path,
                    'error': str(e)
                })
        
        results['processing_time'] = time.time() - start_time
        results['summary'] = self._generate_batch_summary(results)
        
        self.logger.info(f"Batch processing completed: {results['successful']}/{results['total_documents']} successful")
        return results
    
    def _export_document_results(self, doc_result: Dict[str, Any], output_dir: str):
        """Export individual document results."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        document = doc_result['document']
        post_processing = doc_result['post_processing']
        
        # Export post-processing results
        result_file = output_path / f"{document.id}_results.json"
        self.post_processor.export_results(post_processing, result_file)
    
    def _generate_batch_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary statistics for batch processing."""
        successful_docs = [doc for doc in results['documents'] if doc.get('success', False)]
        
        if not successful_docs:
            return {'message': 'No documents processed successfully'}
        
        # Aggregate quality metrics
        quality_scores = [doc['post_processing'].quality_assessment.overall_score 
                         for doc in successful_docs]
        
        total_issues = sum(len(doc['post_processing'].quality_assessment.issues) 
                          for doc in successful_docs)
        
        export_ready_count = sum(1 for doc in successful_docs 
                               if doc['post_processing'].export_ready)
        
        return {
            'success_rate': f"{results['successful']}/{results['total_documents']} ({results['successful']/results['total_documents']*100:.1f}%)",
            'average_quality_score': sum(quality_scores) / len(quality_scores),
            'total_issues_found': total_issues,
            'export_ready_documents': f"{export_ready_count}/{results['successful']}",
            'total_processing_time': f"{results['processing_time']:.2f} seconds",
            'average_time_per_document': f"{results['processing_time']/results['total_documents']:.2f} seconds"
        }