#!/usr/bin/env python3
"""
Snippet storage system for manual validation.
Handles both image file extraction and coordinate reference storage.
"""

import logging
import fitz  # PyMuPDF
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import json
from datetime import datetime
from PIL import Image
import io

from ..models.manual_validation_models import (
    DocumentSnippet, SnippetType, SnippetLocation, SnippetMetadata,
    ManualValidationSession, PageValidationResult
)
from ..config.settings import Settings


class SnippetStorageManager:
    """Manages storage and retrieval of document snippets."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = logging.getLogger(__name__)
        
        # Storage paths
        self.base_storage_path = Path(settings.get('snippet_storage_path', 'snippets'))
        self.image_storage_path = self.base_storage_path / 'images'
        self.metadata_storage_path = self.base_storage_path / 'metadata'
        
        # Create directories if they don't exist
        self._ensure_storage_directories()
    
    def _ensure_storage_directories(self):
        """Ensure all storage directories exist."""
        self.base_storage_path.mkdir(parents=True, exist_ok=True)
        self.image_storage_path.mkdir(parents=True, exist_ok=True)
        self.metadata_storage_path.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"Snippet storage initialized at: {self.base_storage_path}")
    
    def extract_snippet_image(self, 
                            document_path: str, 
                            snippet: DocumentSnippet,
                            image_format: str = "PNG",
                            quality: int = 95) -> Optional[str]:
        """Extract snippet image from PDF and save to storage."""
        try:
            # Open PDF document
            doc = fitz.open(document_path)
            page = doc[snippet.location.page - 1]  # Convert to 0-based indexing
            
            # Create extraction rectangle
            bbox = snippet.location.bbox
            rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3])
            
            # Extract image with high quality
            zoom = 2.0  # High resolution for better quality
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, clip=rect)
            
            # Generate filename
            filename = f"{snippet.id}.{image_format.lower()}"
            file_path = self.image_storage_path / filename
            
            # Save image
            if image_format.upper() == "PNG":
                pix.save(str(file_path))
            else:
                # Convert to PIL Image for other formats
                img_data = pix.tobytes("ppm")
                pil_image = Image.open(io.BytesIO(img_data))
                pil_image.save(str(file_path), format=image_format, quality=quality)
            
            doc.close()
            
            # Update snippet with image file path
            snippet.image_file = str(file_path)
            
            self.logger.info(f"Extracted snippet image: {file_path}")
            return str(file_path)
            
        except Exception as e:
            self.logger.error(f"Error extracting snippet image: {e}")
            return None
    
    def extract_snippet_context(self, 
                               document_path: str, 
                               snippet: DocumentSnippet,
                               context_window: int = 200) -> Optional[str]:
        """Extract surrounding text context for the snippet."""
        try:
            # Open PDF document
            doc = fitz.open(document_path)
            page = doc[snippet.location.page - 1]
            
            # Get page text
            page_text = page.get_text()
            
            # Extract text in larger area around snippet
            bbox = snippet.location.bbox
            expanded_bbox = [
                max(0, bbox[0] - 50),  # Expand left
                max(0, bbox[1] - 50),  # Expand up
                bbox[2] + 50,          # Expand right
                bbox[3] + 50           # Expand down
            ]
            
            expanded_rect = fitz.Rect(expanded_bbox)
            context_text = page.get_text(clip=expanded_rect)
            
            # Limit context text length
            if len(context_text) > context_window:
                context_text = context_text[:context_window] + "..."
            
            doc.close()
            
            # Update snippet metadata
            snippet.metadata.context_text = context_text.strip()
            
            self.logger.debug(f"Extracted context for snippet {snippet.id}: {len(context_text)} chars")
            return context_text
            
        except Exception as e:
            self.logger.error(f"Error extracting snippet context: {e}")
            return None
    
    def save_snippet_metadata(self, snippet: DocumentSnippet) -> bool:
        """Save snippet metadata to storage."""
        try:
            metadata_file = self.metadata_storage_path / f"{snippet.id}.json"
            
            # Convert to dictionary
            metadata_dict = snippet.to_dict()
            
            # Save to JSON file
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.debug(f"Saved snippet metadata: {metadata_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving snippet metadata: {e}")
            return False
    
    def load_snippet_metadata(self, snippet_id: str) -> Optional[DocumentSnippet]:
        """Load snippet metadata from storage."""
        try:
            metadata_file = self.metadata_storage_path / f"{snippet_id}.json"
            
            if not metadata_file.exists():
                return None
            
            # Load from JSON file
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata_dict = json.load(f)
            
            # Convert to DocumentSnippet
            snippet = DocumentSnippet.from_dict(metadata_dict)
            
            self.logger.debug(f"Loaded snippet metadata: {snippet_id}")
            return snippet
            
        except Exception as e:
            self.logger.error(f"Error loading snippet metadata: {e}")
            return None
    
    def save_validation_session(self, session: ManualValidationSession) -> bool:
        """Save complete validation session to storage."""
        try:
            session_file = self.metadata_storage_path / f"session_{session.session_id}.json"
            
            # Convert to dictionary
            session_dict = session.to_dict()
            
            # Save to JSON file
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved validation session: {session_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving validation session: {e}")
            return False
    
    def load_validation_session(self, session_id: str) -> Optional[ManualValidationSession]:
        """Load validation session from storage."""
        try:
            session_file = self.metadata_storage_path / f"session_{session_id}.json"
            
            if not session_file.exists():
                return None
            
            # Load from JSON file
            with open(session_file, 'r', encoding='utf-8') as f:
                session_dict = json.load(f)
            
            # Convert to ManualValidationSession
            session = ManualValidationSession.from_dict(session_dict)
            
            self.logger.info(f"Loaded validation session: {session_id}")
            return session
            
        except Exception as e:
            self.logger.error(f"Error loading validation session: {e}")
            return None
    
    def process_snippet(self, 
                       document_path: str, 
                       snippet: DocumentSnippet,
                       extract_image: bool = True,
                       extract_context: bool = True) -> bool:
        """Process a snippet by extracting image and context."""
        try:
            # Extract image if requested
            if extract_image:
                image_path = self.extract_snippet_image(document_path, snippet)
                if not image_path:
                    self.logger.warning(f"Failed to extract image for snippet {snippet.id}")
            
            # Extract context if requested
            if extract_context:
                context = self.extract_snippet_context(document_path, snippet)
                if not context:
                    self.logger.warning(f"Failed to extract context for snippet {snippet.id}")
            
            # Save metadata
            if not self.save_snippet_metadata(snippet):
                self.logger.error(f"Failed to save metadata for snippet {snippet.id}")
                return False
            
            self.logger.info(f"Successfully processed snippet {snippet.id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing snippet {snippet.id}: {e}")
            return False
    
    def get_snippet_storage_path(self, snippet_id: str) -> Path:
        """Get the storage path for a specific snippet."""
        return self.image_storage_path / f"{snippet_id}.png"
    
    def get_snippet_metadata_path(self, snippet_id: str) -> Path:
        """Get the metadata storage path for a specific snippet."""
        return self.metadata_storage_path / f"{snippet_id}.json"
    
    def cleanup_snippet(self, snippet_id: str) -> bool:
        """Clean up all files associated with a snippet."""
        try:
            # Remove image file
            image_path = self.get_snippet_storage_path(snippet_id)
            if image_path.exists():
                image_path.unlink()
            
            # Remove metadata file
            metadata_path = self.get_snippet_metadata_path(snippet_id)
            if metadata_path.exists():
                metadata_path.unlink()
            
            self.logger.info(f"Cleaned up snippet {snippet_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cleaning up snippet {snippet_id}: {e}")
            return False
    
    def get_storage_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            # Count image files
            image_files = list(self.image_storage_path.glob("*.png"))
            image_files.extend(list(self.image_storage_path.glob("*.jpg")))
            image_files.extend(list(self.image_storage_path.glob("*.jpeg")))
            
            # Count metadata files
            metadata_files = list(self.metadata_storage_path.glob("*.json"))
            
            # Calculate storage size
            total_size = 0
            for file_path in image_files + metadata_files:
                total_size += file_path.stat().st_size
            
            return {
                'total_snippets': len(metadata_files),
                'image_files': len(image_files),
                'metadata_files': len(metadata_files),
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024),
                'storage_path': str(self.base_storage_path)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting storage statistics: {e}")
            return {}


class ToreProjectExtension:
    """Extensions to .tore project format for manual validation."""
    
    @staticmethod
    def add_manual_validation_to_project(project_data: Dict[str, Any], 
                                       session: ManualValidationSession) -> Dict[str, Any]:
        """Add manual validation data to .tore project format."""
        if 'manual_validation' not in project_data:
            project_data['manual_validation'] = {}
        
        # Add validation session
        project_data['manual_validation'] = {
            'status': session.status.value,
            'session_id': session.session_id,
            'validator_id': session.validator_id,
            'started_at': session.started_at.isoformat(),
            'completed_at': session.completed_at.isoformat() if session.completed_at else None,
            'statistics': session.get_statistics(),
            'snippets': [snippet.to_dict() for snippet in session.get_all_snippets()],
            'snippets_by_type': {
                'images': [snippet.to_dict() for snippet in session.get_snippets_by_type(SnippetType.IMAGE)],
                'tables': [snippet.to_dict() for snippet in session.get_snippets_by_type(SnippetType.TABLE)],
                'diagrams': [snippet.to_dict() for snippet in session.get_snippets_by_type(SnippetType.DIAGRAM)]
            },
            'exclusion_zones': ToreProjectExtension._generate_exclusion_zones(session)
        }
        
        return project_data
    
    @staticmethod
    def _generate_exclusion_zones(session: ManualValidationSession) -> Dict[str, List[Dict[str, Any]]]:
        """Generate exclusion zones for text extraction."""
        exclusion_zones = {}
        
        for page_num, page_result in session.page_results.items():
            zones = []
            for snippet in page_result.snippets:
                zones.append({
                    'type': snippet.snippet_type.value,
                    'bbox': snippet.location.bbox,
                    'snippet_id': snippet.id
                })
            exclusion_zones[str(page_num)] = zones
        
        return exclusion_zones
    
    @staticmethod
    def load_manual_validation_from_project(project_data: Dict[str, Any]) -> Optional[ManualValidationSession]:
        """Load manual validation data from .tore project format."""
        if 'manual_validation' not in project_data:
            return None
        
        try:
            validation_data = project_data['manual_validation']
            
            # Create session from stored data
            session = ManualValidationSession(
                document_id=validation_data.get('document_id', ''),
                document_path=validation_data.get('document_path', ''),
                session_id=validation_data['session_id'],
                validator_id=validation_data.get('validator_id', ''),
                started_at=datetime.fromisoformat(validation_data['started_at']),
                completed_at=datetime.fromisoformat(validation_data['completed_at']) if validation_data.get('completed_at') else None
            )
            
            # Load snippets
            for snippet_data in validation_data.get('snippets', []):
                snippet = DocumentSnippet.from_dict(snippet_data)
                
                # Add to appropriate page
                page_num = snippet.location.page
                if page_num not in session.page_results:
                    session.page_results[page_num] = PageValidationResult(page_number=page_num)
                
                session.page_results[page_num].snippets.append(snippet)
            
            return session
            
        except Exception as e:
            logging.getLogger(__name__).error(f"Error loading manual validation from project: {e}")
            return None
    
    @staticmethod
    def get_exclusion_zones_for_page(project_data: Dict[str, Any], page_number: int) -> List[Dict[str, Any]]:
        """Get exclusion zones for a specific page."""
        if 'manual_validation' not in project_data:
            return []
        
        exclusion_zones = project_data['manual_validation'].get('exclusion_zones', {})
        return exclusion_zones.get(str(page_number), [])
    
    @staticmethod
    def create_llm_compatible_format(project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create LLM-compatible format from project data."""
        if 'manual_validation' not in project_data:
            return {}
        
        validation_data = project_data['manual_validation']
        
        return {
            'document_validation': {
                'status': validation_data.get('status', 'unknown'),
                'statistics': validation_data.get('statistics', {}),
                'content_types': {
                    'images': validation_data.get('snippets_by_type', {}).get('images', []),
                    'tables': validation_data.get('snippets_by_type', {}).get('tables', []),
                    'diagrams': validation_data.get('snippets_by_type', {}).get('diagrams', [])
                },
                'exclusion_zones_by_page': validation_data.get('exclusion_zones', {}),
                'metadata': {
                    'validator_id': validation_data.get('validator_id', ''),
                    'completed_at': validation_data.get('completed_at'),
                    'total_snippets': validation_data.get('statistics', {}).get('total_snippets', 0)
                }
            }
        }