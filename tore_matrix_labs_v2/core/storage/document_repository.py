#!/usr/bin/env python3
"""
Document Repository for TORE Matrix Labs V2

Implements the repository pattern for document data access and storage.
Provides a clean abstraction layer for document persistence.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import logging
from datetime import datetime

from .repository_base import RepositoryBase, StorageConfig, StorageBackend
from ..models.unified_document_model import UnifiedDocument, DocumentStatus


class DocumentRepository:
    """Repository for document data storage and retrieval."""
    
    def __init__(self, storage_config: Optional[Dict[str, Any]] = None):
        """Initialize document repository."""
        self.storage_config = storage_config or {}
        self.logger = logging.getLogger(__name__)
        
        # Simple in-memory storage for now
        self._documents: Dict[str, Dict[str, Any]] = {}
        
        self.logger.info("Document repository initialized")
    
    def save_document(self, document: UnifiedDocument) -> bool:
        """
        Save a document to storage.
        
        Args:
            document: Document to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Update modified timestamp
            document.modified_at = datetime.now()
            
            # Convert to dictionary
            doc_data = document.to_dict()
            
            # Save to in-memory storage
            self._documents[document.id] = doc_data
            self.logger.debug(f"Document saved: {document.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save document {document.id}: {str(e)}")
            return False
    
    def load_document(self, document_id: str) -> Optional[UnifiedDocument]:
        """
        Load a document by ID.
        
        Args:
            document_id: ID of document to load
            
        Returns:
            Document if found, None otherwise
        """
        try:
            # Load from in-memory storage
            doc_data = self._documents.get(document_id)
            if not doc_data:
                return None
            
            # Convert back to UnifiedDocument
            return UnifiedDocument.from_dict(doc_data)
            
        except Exception as e:
            self.logger.error(f"Failed to load document {document_id}: {str(e)}")
            return None
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document.
        
        Args:
            document_id: ID of document to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if document_id in self._documents:
                del self._documents[document_id]
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete document {document_id}: {str(e)}")
            return False
    
    def save(self, document: UnifiedDocument) -> bool:
        """Save a document (alias for save_document)."""
        return self.save_document(document)
    
    def list_documents(self, status: Optional[DocumentStatus] = None) -> List[UnifiedDocument]:
        """
        List all documents, optionally filtered by status.
        
        Args:
            status: Optional status filter
            
        Returns:
            List of documents
        """
        try:
            # Get all document IDs
            all_ids = self.list_all()
            documents = []
            
            for doc_id in all_ids:
                doc = self.load_document(doc_id)
                if doc and (status is None or doc.status == status):
                    documents.append(doc)
            
            return documents
            
        except Exception as e:
            self.logger.error(f"Failed to list documents: {str(e)}")
            return []
    
    def find_documents_by_name(self, name_pattern: str) -> List[UnifiedDocument]:
        """
        Find documents by name pattern.
        
        Args:
            name_pattern: Pattern to match against document names
            
        Returns:
            List of matching documents
        """
        try:
            all_documents = self.list_documents()
            matching_docs = []
            
            for doc in all_documents:
                if name_pattern.lower() in doc.file_name.lower():
                    matching_docs.append(doc)
            
            return matching_docs
            
        except Exception as e:
            self.logger.error(f"Failed to find documents by name: {str(e)}")
            return []
    
    def update_document_status(self, document_id: str, status: DocumentStatus) -> bool:
        """
        Update document status.
        
        Args:
            document_id: Document ID
            status: New status
            
        Returns:
            True if successful, False otherwise
        """
        try:
            doc = self.load_document(document_id)
            if not doc:
                return False
            
            doc.status = status
            doc.modified_at = datetime.now()
            
            return self.save_document(doc)
            
        except Exception as e:
            self.logger.error(f"Failed to update document status: {str(e)}")
            return False
    
    def get_document_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about stored documents.
        
        Returns:
            Dictionary with statistics
        """
        try:
            all_documents = self.list_documents()
            
            # Count by status
            status_counts = {}
            for status in DocumentStatus:
                status_counts[status.value] = len([
                    doc for doc in all_documents if doc.status == status
                ])
            
            # Calculate other statistics
            total_size = sum(doc.metadata.get("file_size", 0) for doc in all_documents)
            total_pages = sum(doc.metadata.get("page_count", 0) for doc in all_documents)
            
            return {
                "total_documents": len(all_documents),
                "status_counts": status_counts,
                "total_file_size": total_size,
                "total_pages": total_pages,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get document statistics: {str(e)}")
            return {}
    
    def backup_documents(self, backup_path: Path) -> bool:
        """
        Backup all documents to specified path.
        
        Args:
            backup_path: Path to save backup
            
        Returns:
            True if successful, False otherwise
        """
        try:
            all_documents = self.list_documents()
            
            backup_data = {
                "backup_created": datetime.now().isoformat(),
                "document_count": len(all_documents),
                "documents": [doc.to_dict() for doc in all_documents]
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Backup created: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {str(e)}")
            return False
    
    def restore_from_backup(self, backup_path: Path) -> bool:
        """
        Restore documents from backup file.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            documents_data = backup_data.get("documents", [])
            restored_count = 0
            
            for doc_data in documents_data:
                try:
                    document = UnifiedDocument.from_dict(doc_data)
                    if self.save_document(document):
                        restored_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to restore document: {str(e)}")
            
            self.logger.info(f"Restored {restored_count} documents from backup")
            return restored_count > 0
            
        except Exception as e:
            self.logger.error(f"Failed to restore from backup: {str(e)}")
            return False