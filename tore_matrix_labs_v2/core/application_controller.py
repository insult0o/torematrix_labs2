#!/usr/bin/env python3
"""
Application Controller for TORE Matrix Labs V2

This controller bridges the UI and backend processing, providing the missing
link that connects user interactions to actual document processing functionality.

This addresses the user feedback "alot of stuff is missing" by implementing
the actual business logic that powers the application.
"""

import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime

from .models.unified_document_model import UnifiedDocument, DocumentStatus, ProcessingStage
from .processors.unified_document_processor import UnifiedDocumentProcessor, ProcessingConfig
from .services.coordinate_mapping_service import CoordinateMappingService
from .services.text_extraction_service import TextExtractionService
from .services.validation_service import ValidationService
from .processors.quality_assessment_engine import QualityAssessmentEngine
from .storage.document_repository import DocumentRepository
from .storage.migration_manager import MigrationManager


class ApplicationController:
    """
    Central controller that manages all document processing operations.
    
    This controller serves as the main interface between the UI and the
    backend processing systems, handling all business logic and coordinating
    between different services.
    """
    
    def __init__(self):
        """Initialize the application controller."""
        self.logger = logging.getLogger(__name__)
        
        # Initialize core services
        self.coordinate_service = CoordinateMappingService()
        self.extraction_service = TextExtractionService(self.coordinate_service)
        self.validation_service = ValidationService(self.coordinate_service, self.extraction_service)
        self.quality_engine = QualityAssessmentEngine()
        
        # Initialize repositories
        self.document_repository = DocumentRepository()
        self.migration_manager = MigrationManager(self.document_repository)
        
        # Initialize main processor
        self.document_processor = UnifiedDocumentProcessor(
            coordinate_service=self.coordinate_service,
            extraction_service=self.extraction_service,
            validation_service=self.validation_service,
            quality_engine=self.quality_engine
        )
        
        # Current state
        self.current_project_id: Optional[str] = None
        self.loaded_documents: Dict[str, UnifiedDocument] = {}
        self.processing_results: Dict[str, Any] = {}
        
        self.logger.info("Application controller initialized")
    
    def load_document(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Load a document for processing.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Document information for the UI
        """
        try:
            self.logger.info(f"Loading document: {file_path}")
            
            # Convert to Path object
            path = Path(file_path)
            
            if not path.exists():
                raise FileNotFoundError(f"Document not found: {path}")
            
            # Check if it's a .tore file (existing project)
            if path.suffix.lower() == '.tore':
                return self._load_tore_file(path)
            
            # Create new document
            document = self._create_document_from_file(path)
            
            # Store in memory
            self.loaded_documents[document.id] = document
            
            # Extract basic information for UI
            document_info = self._extract_document_info(document)
            
            self.logger.info(f"Document loaded successfully: {document.id}")
            return document_info
            
        except Exception as e:
            self.logger.error(f"Failed to load document: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "file_path": str(file_path)
            }
    
    def process_document(self, document_id: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a loaded document.
        
        Args:
            document_id: ID of the document to process
            config: Processing configuration override
            
        Returns:
            Processing result information
        """
        try:
            self.logger.info(f"Processing document: {document_id}")
            
            # Get document
            if document_id not in self.loaded_documents:
                raise ValueError(f"Document not loaded: {document_id}")
            
            document = self.loaded_documents[document_id]
            
            # Update processing config if provided
            if config:
                document.processing_config = ProcessingConfig(**config)
            
            # Process the document
            result = self.document_processor.process_document(
                document.file_path,
                project_id=self.current_project_id
            )
            
            # Update document with results
            self._update_document_with_results(document, result)
            
            # Store results
            self.processing_results[document_id] = result
            
            # Save to repository
            self.document_repository.save(document)
            
            self.logger.info(f"Document processing completed: {document_id}")
            return result.to_dict()
            
        except Exception as e:
            self.logger.error(f"Failed to process document: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "document_id": document_id
            }
    
    def get_document_list(self) -> List[Dict[str, Any]]:
        """Get list of all loaded documents."""
        documents = []
        
        for doc_id, document in self.loaded_documents.items():
            documents.append({
                "id": doc_id,
                "name": document.file_name,
                "status": document.status.value,
                "pages": document.get_page_count(),
                "quality": document.get_quality_score(),
                "created": document.created_at.isoformat(),
                "file_path": document.file_path
            })
        
        return documents
    
    def get_document_content(self, document_id: str, page: Optional[int] = None) -> Dict[str, Any]:
        """
        Get document content for display.
        
        Args:
            document_id: ID of the document
            page: Optional specific page number
            
        Returns:
            Document content information
        """
        try:
            if document_id not in self.loaded_documents:
                raise ValueError(f"Document not found: {document_id}")
            
            document = self.loaded_documents[document_id]
            
            # If not processed yet, extract basic content
            if not document.is_processed():
                extraction_result = self.extraction_service.extract_text(document)
                content = extraction_result.text
            else:
                content = document.extracted_text
            
            # Return content information
            result = {
                "document_id": document_id,
                "name": document.file_name,
                "content": content,
                "page_count": document.get_page_count(),
                "current_page": page or 1,
                "metadata": {
                    "file_size": document.metadata.file_size,
                    "file_type": document.metadata.file_type,
                    "pages": document.metadata.page_count,
                    "quality_score": document.metadata.quality_score
                }
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to get document content: {str(e)}")
            return {
                "error": str(e),
                "document_id": document_id
            }
    
    def get_validation_data(self, document_id: str) -> Dict[str, Any]:
        """Get validation data for a document."""
        try:
            if document_id not in self.loaded_documents:
                raise ValueError(f"Document not found: {document_id}")
            
            document = self.loaded_documents[document_id]
            
            return {
                "document_id": document_id,
                "validation_results": document.validation_results,
                "quality_assessment": document.quality_assessment,
                "areas": document.areas,
                "errors": document.errors,
                "warnings": document.warnings,
                "requires_validation": document.requires_validation()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get validation data: {str(e)}")
            return {"error": str(e), "document_id": document_id}
    
    def create_new_project(self, project_name: str) -> Dict[str, Any]:
        """Create a new project."""
        try:
            project_id = self._generate_project_id(project_name)
            
            project_data = {
                "id": project_id,
                "name": project_name,
                "created_at": datetime.now().isoformat(),
                "documents": [],
                "status": "active"
            }
            
            self.current_project_id = project_id
            
            self.logger.info(f"New project created: {project_name}")
            return {
                "success": True,
                "project_data": project_data
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create project: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def load_project(self, project_path: Union[str, Path]) -> Dict[str, Any]:
        """Load an existing project."""
        try:
            path = Path(project_path)
            
            if not path.exists():
                raise FileNotFoundError(f"Project file not found: {path}")
            
            # Load project using migration manager
            project_data = self.migration_manager.load_project(str(path))
            
            self.current_project_id = project_data.get("id")
            
            # Load associated documents
            for doc_info in project_data.get("documents", []):
                doc_path = doc_info.get("file_path")
                if doc_path and Path(doc_path).exists():
                    self.load_document(doc_path)
            
            self.logger.info(f"Project loaded: {project_data.get('name')}")
            return {
                "success": True,
                "project_data": project_data
            }
            
        except Exception as e:
            self.logger.error(f"Failed to load project: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def save_project(self, save_path: Optional[str] = None) -> Dict[str, Any]:
        """Save the current project."""
        try:
            if not self.current_project_id:
                raise ValueError("No active project to save")
            
            # Prepare project data
            project_data = {
                "id": self.current_project_id,
                "name": f"Project_{self.current_project_id}",
                "created_at": datetime.now().isoformat(),
                "documents": [],
                "processing_results": self.processing_results
            }
            
            # Add document information
            for doc_id, document in self.loaded_documents.items():
                doc_info = {
                    "id": doc_id,
                    "file_path": document.file_path,
                    "status": document.status.value,
                    "processed_at": document.processed_at.isoformat() if document.processed_at else None
                }
                project_data["documents"].append(doc_info)
            
            # Save using migration manager
            if save_path:
                saved_path = self.migration_manager.save_project(project_data, save_path)
            else:
                saved_path = self.migration_manager.save_project(project_data)
            
            self.logger.info(f"Project saved: {saved_path}")
            return {
                "success": True,
                "saved_path": saved_path,
                "project_data": project_data
            }
            
        except Exception as e:
            self.logger.error(f"Failed to save project: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        total_documents = len(self.loaded_documents)
        processed_count = sum(1 for doc in self.loaded_documents.values() if doc.is_processed())
        
        return {
            "total_documents": total_documents,
            "processed_documents": processed_count,
            "pending_documents": total_documents - processed_count,
            "current_project": self.current_project_id,
            "extraction_stats": self.extraction_service.get_performance_stats(),
            "processing_results_count": len(self.processing_results)
        }
    
    def _load_tore_file(self, tore_path: Path) -> Dict[str, Any]:
        """Load a .tore file (existing project)."""
        try:
            # Use migration manager to load
            document_data = self.migration_manager.load_document(str(tore_path))
            
            # Convert to UnifiedDocument
            document = UnifiedDocument.from_dict(document_data)
            
            # Store in memory
            self.loaded_documents[document.id] = document
            
            return self._extract_document_info(document)
            
        except Exception as e:
            self.logger.error(f"Failed to load .tore file: {str(e)}")
            raise
    
    def _create_document_from_file(self, file_path: Path) -> UnifiedDocument:
        """Create a new document from a file."""
        import hashlib
        
        # Generate document ID
        content = f"{file_path.name}_{file_path.stat().st_size}_{file_path.stat().st_mtime}"
        doc_id = hashlib.md5(content.encode()).hexdigest()[:12]
        
        # Create document
        document = UnifiedDocument(
            id=doc_id,
            project_id=self.current_project_id,
            file_path=str(file_path),
            file_name=file_path.name,
            original_filename=file_path.name,
            status=DocumentStatus.LOADED
        )
        
        # Set metadata
        document.metadata.file_size = file_path.stat().st_size
        document.metadata.file_type = file_path.suffix.lower()
        
        # Get page count for PDFs
        if file_path.suffix.lower() == '.pdf':
            try:
                import fitz
                pdf_doc = fitz.open(str(file_path))
                document.metadata.page_count = len(pdf_doc)
                pdf_doc.close()
            except Exception as e:
                self.logger.warning(f"Could not get page count: {str(e)}")
                document.metadata.page_count = 1
        else:
            document.metadata.page_count = 1
        
        return document
    
    def _extract_document_info(self, document: UnifiedDocument) -> Dict[str, Any]:
        """Extract document information for UI display."""
        return {
            "success": True,
            "document_id": document.id,
            "name": document.file_name,
            "status": document.status.value,
            "file_path": document.file_path,
            "page_count": document.get_page_count(),
            "file_size": document.metadata.file_size,
            "file_type": document.metadata.file_type,
            "created_at": document.created_at.isoformat(),
            "quality_score": document.get_quality_score(),
            "requires_validation": document.requires_validation(),
            "metadata": {
                "pages": document.metadata.page_count,
                "file_size": document.metadata.file_size,
                "file_type": document.metadata.file_type,
                "language": document.metadata.language
            }
        }
    
    def _update_document_with_results(self, document: UnifiedDocument, result):
        """Update document with processing results."""
        if result.success:
            document.update_status(DocumentStatus.PROCESSED, ProcessingStage.FINALIZATION)
            document.extracted_text = result.extraction_data.get("text", "")
            document.extraction_results = result.extraction_data
            document.quality_assessment = result.quality_assessment
            document.validation_results = result.validation_data or {}
            
            # Update metadata
            document.metadata.quality_score = result.quality_assessment.get("overall_score", 0.0)
            document.metadata.processing_time = result.processing_time
            document.metadata.extraction_method = result.extraction_data.get("method", "unknown")
        else:
            document.update_status(DocumentStatus.FAILED)
            document.add_error("processing_failed", result.error_message or "Unknown error")
    
    def _generate_project_id(self, project_name: str) -> str:
        """Generate a unique project ID."""
        import hashlib
        content = f"{project_name}_{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]