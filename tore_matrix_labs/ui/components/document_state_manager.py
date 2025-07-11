"""
Document State Manager for TORE Matrix Labs

Centralized manager for active document state across all widgets.
Handles document selection, metadata caching, and cross-widget communication.
"""

from PyQt5.QtCore import QObject, pyqtSignal
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class DocumentStateManager(QObject):
    """Central manager for active document state across all widgets."""
    
    # Signals
    active_document_changed = pyqtSignal(str, dict)  # document_id, metadata
    document_data_updated = pyqtSignal(str, str, dict)  # document_id, data_type, data
    document_list_changed = pyqtSignal(list)  # list of document_ids
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_document_id: Optional[str] = None
        self.document_cache: Dict[str, Dict[str, Any]] = {}
        self.project_documents: Dict[str, Dict[str, Any]] = {}
        
        logger.info("DocumentStateManager initialized")
    
    def set_active_document(self, document_id: str, metadata: Dict[str, Any]):
        """Set the currently active document and notify all widgets."""
        if self.active_document_id != document_id:
            logger.info(f"Setting active document: {document_id}")
            self.active_document_id = document_id
            
            # Update cache
            self.document_cache[document_id] = metadata.copy()
            
            # Emit signal to notify all widgets
            self.active_document_changed.emit(document_id, metadata)
            
            logger.debug(f"Active document changed to: {document_id}")
    
    def get_active_document(self) -> Optional[tuple]:
        """Get current active document ID and metadata."""
        if self.active_document_id and self.active_document_id in self.document_cache:
            return self.active_document_id, self.document_cache[self.active_document_id]
        return None
    
    def update_document_data(self, document_id: str, data_type: str, data: Dict[str, Any]):
        """Update specific data for a document and notify widgets."""
        if document_id in self.document_cache:
            if 'data' not in self.document_cache[document_id]:
                self.document_cache[document_id]['data'] = {}
            
            self.document_cache[document_id]['data'][data_type] = data
            self.document_data_updated.emit(document_id, data_type, data)
            
            logger.debug(f"Updated {data_type} data for document: {document_id}")
    
    def get_document_metadata(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific document."""
        return self.document_cache.get(document_id)
    
    def load_project_documents(self, documents: list):
        """Load all documents from a project."""
        self.project_documents.clear()
        self.document_cache.clear()
        
        document_ids = []
        for doc in documents:
            doc_id = doc.get('id')
            if doc_id:
                self.project_documents[doc_id] = doc
                self.document_cache[doc_id] = {
                    'id': doc_id,
                    'path': doc.get('path', ''),
                    'name': doc.get('name', ''),
                    'file_path': doc.get('file_path', ''),
                    'file_name': doc.get('file_name', ''),
                    'file_size': doc.get('file_size', 0),
                    'page_count': doc.get('page_count', 0),
                    'processing_status': doc.get('processing_status', 'pending'),
                    'corrections_count': doc.get('corrections_count', 0),
                    'status': doc.get('status', 'pending'),
                    'corrections': doc.get('corrections', []),
                    'visual_areas': doc.get('visual_areas', {}),
                    'data': {}
                }
                document_ids.append(doc_id)
        
        self.document_list_changed.emit(document_ids)
        logger.info(f"Loaded {len(document_ids)} documents into state manager")
    
    def get_all_documents(self) -> Dict[str, Dict[str, Any]]:
        """Get all documents in the current project."""
        return self.document_cache.copy()
    
    def clear_state(self):
        """Clear all state (e.g., when closing project)."""
        self.active_document_id = None
        self.document_cache.clear()
        self.project_documents.clear()
        
        logger.info("Document state cleared")
    
    def has_document(self, document_id: str) -> bool:
        """Check if a document exists in the state manager."""
        return document_id in self.document_cache
    
    def get_document_count(self) -> int:
        """Get total number of documents."""
        return len(self.document_cache)
    
    def get_active_document_id(self) -> Optional[str]:
        """Get just the active document ID."""
        return self.active_document_id