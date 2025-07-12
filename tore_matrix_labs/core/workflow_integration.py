#!/usr/bin/env python3
"""
Workflow integration for manual validation pipeline.
Replaces the existing document processing workflow.
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import json
import uuid
import hashlib
from datetime import datetime

from ..config.settings import Settings
from ..config.constants import DocumentType, ProcessingStatus
from ..models.document_models import Document, ProcessingConfiguration
from ..models.manual_validation_models import ManualValidationSession, ValidationStatus
from .enhanced_document_processor import EnhancedDocumentProcessor
from .parallel_processor import ValidationWorkflowOrchestrator
from .snippet_storage import SnippetStorageManager, ToreProjectExtension


class WorkflowIntegrationManager:
    """Manages the complete workflow integration for manual validation."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Initialize processors
        self.document_processor = EnhancedDocumentProcessor(settings)
        self.workflow_orchestrator = ValidationWorkflowOrchestrator(
            max_workers=settings.get('parallel_processing_workers', 4)
        )
        self.snippet_storage = SnippetStorageManager(settings)
        
        self.logger.info("Workflow integration manager initialized")


def generate_stable_document_id(file_path: str) -> str:
    """Generate a stable document ID based on file path.
    
    This ensures the same document gets the same ID across sessions,
    preventing duplicates when documents are reprocessed.
    """
    # Use the absolute file path to generate a consistent hash
    abs_path = str(Path(file_path).resolve())
    
    # Create MD5 hash of the path for a stable ID
    path_hash = hashlib.md5(abs_path.encode('utf-8')).hexdigest()
    
    # Create a shorter, more readable ID
    stable_id = f"doc_{path_hash[:12]}"
    
    logger = logging.getLogger(__name__)
    logger.debug(f"Generated stable ID '{stable_id}' for path '{abs_path}'")
    return stable_id
    
    def start_document_processing(self, file_path: str, 
                                document_type: DocumentType = DocumentType.ICAO,
                                processing_config: Optional[ProcessingConfiguration] = None) -> Dict[str, Any]:
        """
        Start the new document processing workflow with manual validation.
        
        Args:
            file_path: Path to document file
            document_type: Type of document
            processing_config: Processing configuration
            
        Returns:
            Dictionary with processing initialization results
        """
        self.logger.info(f"Starting new document processing workflow: {file_path}")
        
        try:
            # Step 1: Initialize document processing
            init_result = self.document_processor.process_document_with_manual_validation(
                file_path, document_type, processing_config
            )
            
            if not init_result['success']:
                return init_result
            
            # Step 2: Prepare for manual validation
            document = init_result['document']
            validation_session = init_result['validation_session']
            
            # Step 3: Create workflow state
            workflow_state = self._create_workflow_state(document, validation_session, init_result)
            
            return {
                'success': True,
                'workflow_state': workflow_state,
                'document': document,
                'validation_session': validation_session,
                'page_analyses': init_result['page_analyses'],
                'next_step': 'manual_validation',
                'message': 'Document ready for manual validation'
            }
            
        except Exception as e:
            self.logger.error(f"Error starting document processing: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to start document processing'
            }
    
    def complete_manual_validation(self, workflow_state: Dict[str, Any], 
                                 validation_session: ManualValidationSession) -> Dict[str, Any]:
        """
        Complete the manual validation step and continue processing.
        
        Args:
            workflow_state: Current workflow state
            validation_session: Completed validation session
            
        Returns:
            Dictionary with completion results
        """
        self.logger.info(f"Completing manual validation for document: {workflow_state['document_id']}")
        
        try:
            # Step 1: Mark validation as completed
            validation_session.mark_completed()
            
            # Step 2: Process validated snippets
            snippet_results = self._process_validation_snippets(validation_session)
            
            # Step 3: Continue with enhanced document processing
            document = workflow_state['document']
            page_analyses = workflow_state['page_analyses']
            
            completion_result = self.document_processor.complete_processing_after_validation(
                document, validation_session, page_analyses
            )
            
            if not completion_result['success']:
                return completion_result
            
            # Step 4: Update workflow state
            workflow_state['status'] = 'completed'
            workflow_state['validation_session'] = validation_session
            workflow_state['completion_result'] = completion_result
            workflow_state['snippet_results'] = snippet_results
            
            return {
                'success': True,
                'workflow_state': workflow_state,
                'document': completion_result['document'],
                'results': completion_result,
                'message': 'Document processing completed successfully'
            }
            
        except Exception as e:
            self.logger.error(f"Error completing manual validation: {e}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to complete manual validation'
            }
    
    def save_workflow_to_project(self, project_data: Dict[str, Any], 
                               workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Save workflow state to .tore project format."""
        try:
            # Add manual validation data to project
            if 'validation_session' in workflow_state:
                project_data = ToreProjectExtension.add_manual_validation_to_project(
                    project_data, workflow_state['validation_session']
                )
            
            # Add workflow metadata
            if 'workflow_metadata' not in project_data:
                project_data['workflow_metadata'] = {}
            
            project_data['workflow_metadata']['manual_validation_enabled'] = True
            project_data['workflow_metadata']['workflow_version'] = '2.0'
            project_data['workflow_metadata']['last_updated'] = datetime.now().isoformat()
            
            # Add processing statistics
            if 'completion_result' in workflow_state:
                project_data['workflow_metadata']['processing_statistics'] = {
                    'total_processing_time': workflow_state['completion_result'].get('processing_time', 0),
                    'parallel_processing_used': True,
                    'exclusion_zones_applied': True
                }
            
            return project_data
            
        except Exception as e:
            self.logger.error(f"Error saving workflow to project: {e}")
            return project_data
    
    def load_workflow_from_project(self, project_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Load workflow state from .tore project format."""
        try:
            # Load manual validation session
            validation_session = ToreProjectExtension.load_manual_validation_from_project(project_data)
            
            if not validation_session:
                return None
            
            # Create workflow state from project data
            workflow_state = {
                'document_id': validation_session.document_id,
                'document_path': validation_session.document_path,
                'validation_session': validation_session,
                'status': validation_session.status.value,
                'workflow_version': project_data.get('workflow_metadata', {}).get('workflow_version', '2.0'),
                'created_at': validation_session.started_at.isoformat(),
                'manual_validation_enabled': True
            }
            
            return workflow_state
            
        except Exception as e:
            self.logger.error(f"Error loading workflow from project: {e}")
            return None
    
    def _create_workflow_state(self, document: Document, 
                             validation_session: ManualValidationSession,
                             init_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create initial workflow state."""
        return {
            'workflow_id': str(uuid.uuid4()),
            'document_id': document.id,
            'document_path': document.metadata.file_path,
            'document': document,
            'validation_session': validation_session,
            'page_analyses': init_result['page_analyses'],
            'status': 'awaiting_manual_validation',
            'created_at': datetime.now().isoformat(),
            'workflow_version': '2.0',
            'manual_validation_enabled': True,
            'processing_statistics': {
                'initialization_time': init_result.get('processing_time', 0),
                'total_pages': document.metadata.page_count
            }
        }
    
    def _process_validation_snippets(self, validation_session: ManualValidationSession) -> Dict[str, Any]:
        """Process all validated snippets."""
        results = {
            'processed_snippets': 0,
            'failed_snippets': 0,
            'snippets_by_type': {'IMAGE': 0, 'TABLE': 0, 'DIAGRAM': 0},
            'processing_details': []
        }
        
        for snippet in validation_session.get_all_snippets():
            try:
                # Process snippet through storage manager
                success = self.snippet_storage.process_snippet(
                    validation_session.document_path,
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
                        'status': 'failed'
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
    
    def get_workflow_status(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Get current workflow status."""
        validation_session = workflow_state.get('validation_session')
        
        if not validation_session:
            return {'status': 'invalid', 'message': 'No validation session found'}
        
        stats = validation_session.get_statistics()
        
        return {
            'status': workflow_state.get('status', 'unknown'),
            'workflow_version': workflow_state.get('workflow_version', '2.0'),
            'document_path': workflow_state.get('document_path'),
            'validation_progress': {
                'total_pages': stats['total_pages'],
                'validated_pages': stats['validated_pages'],
                'completion_percentage': stats['completion_percentage']
            },
            'snippet_statistics': {
                'total_snippets': stats['total_snippets'],
                'by_type': stats['type_counts'],
                'pages_with_snippets': stats['pages_with_snippets']
            },
            'processing_statistics': workflow_state.get('processing_statistics', {}),
            'created_at': workflow_state.get('created_at'),
            'manual_validation_enabled': workflow_state.get('manual_validation_enabled', True)
        }
    
    def create_llm_ready_export(self, workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Create LLM-ready export of the processed document."""
        try:
            validation_session = workflow_state.get('validation_session')
            completion_result = workflow_state.get('completion_result')
            
            if not validation_session or not completion_result:
                return {'success': False, 'error': 'Incomplete workflow state'}
            
            # Create LLM-compatible format
            llm_export = {
                'document_metadata': {
                    'document_id': workflow_state['document_id'],
                    'document_path': workflow_state['document_path'],
                    'processing_completed': True,
                    'workflow_version': workflow_state.get('workflow_version', '2.0')
                },
                'manual_validation_results': {
                    'validation_status': validation_session.status.value,
                    'total_snippets': len(validation_session.get_all_snippets()),
                    'snippets_by_type': {
                        'images': [snippet.to_dict() for snippet in validation_session.get_snippets_by_type('IMAGE')],
                        'tables': [snippet.to_dict() for snippet in validation_session.get_snippets_by_type('TABLE')],
                        'diagrams': [snippet.to_dict() for snippet in validation_session.get_snippets_by_type('DIAGRAM')]
                    }
                },
                'extracted_content': {
                    'text_elements': completion_result.get('extracted_content', {}).get('text_elements', []),
                    'processed_images': completion_result.get('specialized_results', {}).get('images', []),
                    'processed_tables': completion_result.get('specialized_results', {}).get('tables', []),
                    'processed_diagrams': completion_result.get('specialized_results', {}).get('diagrams', [])
                },
                'quality_assessment': {
                    'overall_score': completion_result.get('document').quality_score,
                    'quality_level': completion_result.get('document').quality_level.value,
                    'export_ready': completion_result.get('post_processing').export_ready
                }
            }
            
            return {
                'success': True,
                'llm_export': llm_export,
                'export_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error creating LLM export: {e}")
            return {'success': False, 'error': str(e)}
    
    def cleanup(self):
        """Clean up resources."""
        self.workflow_orchestrator.cleanup()
        self.logger.info("Workflow integration manager cleaned up")


# Integration helper functions
def create_project_with_manual_validation(project_name: str, 
                                        document_paths: List[str],
                                        settings: Settings) -> Dict[str, Any]:
    """Create a new project with manual validation enabled."""
    project_data = {
        'name': project_name,
        'description': f'Project with manual validation - {len(document_paths)} documents',
        'created_at': datetime.now().isoformat(),
        'modified_at': datetime.now().isoformat(),
        'version': '2.0',
        'workflow_metadata': {
            'manual_validation_enabled': True,
            'workflow_version': '2.0',
            'created_with_enhanced_processor': True
        },
        'documents': []
    }
    
    # Add documents
    for doc_path in document_paths:
        # Use stable ID based on file path to prevent duplicates
        doc_id = generate_stable_document_id(doc_path)
        document_entry = {
            'id': doc_id,
            'path': doc_path,
            'name': Path(doc_path).name,
            'added_at': datetime.now().isoformat(),
            'status': 'pending_manual_validation',
            'processing_data': {
                'manual_validation_required': True,
                'processing_status': 'pending'
            }
        }
        project_data['documents'].append(document_entry)
    
    return project_data


def is_enhanced_workflow_project(project_data: Dict[str, Any]) -> bool:
    """Check if a project uses the enhanced workflow."""
    return (project_data.get('workflow_metadata', {}).get('manual_validation_enabled', False) or
            project_data.get('version') == '2.0')


def migrate_legacy_project(project_data: Dict[str, Any]) -> Dict[str, Any]:
    """Migrate legacy project to enhanced workflow format."""
    # Add workflow metadata
    if 'workflow_metadata' not in project_data:
        project_data['workflow_metadata'] = {}
    
    project_data['workflow_metadata']['manual_validation_enabled'] = True
    project_data['workflow_metadata']['workflow_version'] = '2.0'
    project_data['workflow_metadata']['migrated_from_legacy'] = True
    project_data['workflow_metadata']['migration_timestamp'] = datetime.now().isoformat()
    
    # Update version
    project_data['version'] = '2.0'
    
    # Update document statuses
    for document in project_data.get('documents', []):
        if 'processing_data' not in document:
            document['processing_data'] = {}
        
        document['processing_data']['manual_validation_required'] = True
        
        # Update status based on current state
        if document.get('status') == 'processed':
            document['status'] = 'requires_manual_validation'
        elif document.get('status') == 'validated':
            document['status'] = 'requires_manual_validation'
    
    return project_data