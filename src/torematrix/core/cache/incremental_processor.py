"""Incremental processing system for documents."""

from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .multi_level_cache import MultiLevelCache
from .change_detector import ChangeDetector


class IncrementalProcessor:
    """Processes documents incrementally based on detected changes."""
    
    def __init__(self, cache: MultiLevelCache):
        """Initialize incremental processor.
        
        Args:
            cache: Multi-level cache instance
        """
        self.cache = cache
        self.change_detector = ChangeDetector()
    
    def process_document_incremental(self, document_path: Path, 
                                   force_full: bool = False) -> Dict:
        """Process document incrementally if possible.
        
        Args:
            document_path: Path to document file
            force_full: Force full reprocessing
            
        Returns:
            Processing result dictionary
        """
        document_id = self._get_document_id(document_path)
        
        # Check if entire document has changed
        if force_full or self.change_detector.has_file_changed(document_path):
            return self._process_with_change_detection(document_path, document_id)
        else:
            # Document unchanged, return cached result
            if cached_result := self.cache.get(f"result:{document_id}"):
                return cached_result
            else:
                # Cache miss, process entire document
                return self._process_full_document(document_path, document_id)
    
    def _process_with_change_detection(self, document_path: Path, 
                                     document_id: str) -> Dict:
        """Process document with page-level change detection.
        
        Args:
            document_path: Path to document file
            document_id: Document identifier
            
        Returns:
            Processing result dictionary
        """
        # Get current page information
        current_pages = self._extract_page_info(document_path)
        
        # Identify changed pages
        changed_pages = self.change_detector.get_changed_pages(
            document_id, current_pages
        )
        
        if not changed_pages:
            # No changes, return cached result
            if cached_result := self.cache.get(f"result:{document_id}"):
                return cached_result
        
        # Get previous result if exists
        previous_result = self.cache.get(f"result:{document_id}")
        
        # If less than 30% changed, do incremental update
        if (previous_result and 
            len(changed_pages) < len(current_pages) * 0.3):
            return self._incremental_update(
                document_path, document_id,
                previous_result, changed_pages
            )
        else:
            # Too many changes, reprocess entire document
            return self._process_full_document(document_path, document_id)
    
    def _incremental_update(self, document_path: Path, document_id: str,
                          previous_result: Dict, 
                          changed_pages: List[int]) -> Dict:
        """Update only changed pages.
        
        Args:
            document_path: Path to document file
            document_id: Document identifier
            previous_result: Previous processing result
            changed_pages: List of page numbers that changed
            
        Returns:
            Updated processing result
        """
        updated_result = previous_result.copy()
        
        # Process each changed page
        for page_num in changed_pages:
            # Extract page
            page_data = self._extract_page(document_path, page_num)
            
            # Check cache for processed page
            page_cache_key = f"page:{document_id}:{page_num}"
            if cached_page := self.cache.get(page_cache_key):
                processed_page = cached_page
            else:
                # Process page
                processed_page = self._process_page(page_data)
                # Cache processed page
                self.cache.set(page_cache_key, processed_page, 
                             ttl=86400)  # 24 hours
            
            # Update result
            self._update_page(updated_result, page_num, processed_page)
        
        # Update metadata
        updated_result['metadata'].update({
            'last_updated': datetime.now().isoformat(),
            'incremental_update': True,
            'changed_pages': changed_pages
        })
        
        # Cache updated result
        self.cache.set(f"result:{document_id}", updated_result)
        
        return updated_result
    
    def _process_full_document(self, document_path: Path, 
                             document_id: str) -> Dict:
        """Process entire document.
        
        Args:
            document_path: Path to document file
            document_id: Document identifier
            
        Returns:
            Processing result dictionary
        """
        # Extract and process all pages
        pages = self._extract_page_info(document_path)
        processed_pages = []
        
        for page in pages:
            page_num = page['page_number']
            page_cache_key = f"page:{document_id}:{page_num}"
            
            processed_page = self._process_page(page)
            processed_pages.append(processed_page)
            
            # Cache individual page result
            self.cache.set(page_cache_key, processed_page, ttl=86400)
        
        # Combine results
        result = {
            'document_id': document_id,
            'pages': processed_pages,
            'metadata': {
                'page_count': len(pages),
                'processed_at': datetime.now().isoformat(),
                'incremental_update': False
            }
        }
        
        # Cache full result
        self.cache.set(f"result:{document_id}", result)
        
        return result
    
    def _get_document_id(self, document_path: Path) -> str:
        """Generate unique document identifier."""
        return f"{document_path.stem}:{document_path.stat().st_mtime}"
    
    def _extract_page_info(self, document_path: Path) -> List[Dict]:
        """Extract basic information about document pages.
        
        This method should be implemented by subclasses to handle
        specific document formats.
        """
        raise NotImplementedError
    
    def _extract_page(self, document_path: Path, page_num: int) -> Dict:
        """Extract data for specific page.
        
        This method should be implemented by subclasses to handle
        specific document formats.
        """
        raise NotImplementedError
    
    def _process_page(self, page_data: Dict) -> Dict:
        """Process extracted page data.
        
        This method should be implemented by subclasses to handle
        specific document formats and processing requirements.
        """
        raise NotImplementedError
    
    def _update_page(self, result: Dict, page_num: int, 
                    processed_page: Dict) -> None:
        """Update page in result dictionary.
        
        Args:
            result: Result dictionary to update
            page_num: Page number to update
            processed_page: New processed page data
        """
        for i, page in enumerate(result['pages']):
            if page['page_number'] == page_num:
                result['pages'][i] = processed_page
                return
        
        # Page not found, append it
        result['pages'].append(processed_page)