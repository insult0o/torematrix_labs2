"""Change detection system for document-level caching."""

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .cache_metrics import CacheMetrics


class ChangeDetector:
    """Detects changes in documents for selective cache invalidation."""
    
    def __init__(self):
        """Initialize change detector."""
        self.file_hash_cache = {}
        self.metadata_cache = {}
        self.metrics = CacheMetrics()
    
    def has_file_changed(self, file_path: Path) -> bool:
        """Check if file has changed since last processing.
        
        Args:
            file_path: Path to document file
            
        Returns:
            True if file has changed, False otherwise
        """
        current_hash = self._calculate_file_hash(file_path)
        current_mtime = file_path.stat().st_mtime
        
        cached_info = self.file_hash_cache.get(str(file_path))
        
        if not cached_info:
            # First time seeing this file
            self._update_cache(file_path, current_hash, current_mtime)
            return True
        
        # Check both hash and modification time
        if (cached_info['hash'] != current_hash or 
            cached_info['mtime'] != current_mtime):
            self._update_cache(file_path, current_hash, current_mtime)
            return True
        
        return False
    
    def get_changed_pages(self, document_id: str, 
                         current_pages: List[Dict]) -> List[int]:
        """Identify which pages have changed.
        
        Args:
            document_id: Document identifier
            current_pages: List of page info dictionaries
            
        Returns:
            List of changed page numbers
        """
        cached_pages = self.metadata_cache.get(f"{document_id}:pages", {})
        changed_pages = []
        
        for page_info in current_pages:
            page_num = page_info['page_number']
            page_hash = self._calculate_page_hash(page_info)
            
            if cached_pages.get(page_num) != page_hash:
                changed_pages.append(page_num)
                cached_pages[page_num] = page_hash
        
        # Update cache
        self.metadata_cache[f"{document_id}:pages"] = cached_pages
        
        return changed_pages
    
    def get_changed_sections(self, document_id: str, 
                           current_sections: List[Dict]) -> List[str]:
        """Identify which sections have changed.
        
        Args:
            document_id: Document identifier
            current_sections: List of section info dictionaries
            
        Returns:
            List of changed section identifiers
        """
        cached_sections = self.metadata_cache.get(f"{document_id}:sections", {})
        changed_sections = []
        
        for section_info in current_sections:
            section_id = section_info['id']
            section_hash = self._calculate_section_hash(section_info)
            
            if cached_sections.get(section_id) != section_hash:
                changed_sections.append(section_id)
                cached_sections[section_id] = section_hash
        
        # Update cache
        self.metadata_cache[f"{document_id}:sections"] = cached_sections
        
        return changed_sections
    
    def compute_document_hash(self, document: Dict) -> Dict[str, str]:
        """Compute hierarchical hash for document.
        
        Args:
            document: Document content and metadata
            
        Returns:
            Dictionary of hash values for different aspects
        """
        return {
            'file': self._calculate_file_hash(Path(document['path'])),
            'content': self._hash_string(document.get('content', '')),
            'structure': self._hash_dict(document.get('structure', {})),
            'metadata': self._hash_dict(document.get('metadata', {})),
            'page_hashes': [
                self._calculate_page_hash(page)
                for page in document.get('pages', [])
            ]
        }
    
    def detect_changes(self, old_hashes: Dict[str, str],
                      new_hashes: Dict[str, str]) -> Dict:
        """Detect type and scope of changes between versions.
        
        Args:
            old_hashes: Previous document hashes
            new_hashes: Current document hashes
            
        Returns:
            Change report dictionary
        """
        changes = {
            'type': 'none',  # none, partial, full
            'affected_pages': [],
            'affected_sections': [],
            'metadata_changed': False,
            'structure_changed': False
        }
        
        # Check content hash for any change
        if old_hashes['content'] != new_hashes['content']:
            changes['type'] = 'partial'
            
            # Compare page hashes
            old_pages = old_hashes['page_hashes']
            new_pages = new_hashes['page_hashes']
            
            for i, (old, new) in enumerate(zip(old_pages, new_pages)):
                if old != new:
                    changes['affected_pages'].append(i + 1)
            
            # Check for major changes
            if (old_hashes['structure'] != new_hashes['structure'] or
                len(old_pages) != len(new_pages)):
                changes['type'] = 'full'
                changes['structure_changed'] = True
        
        # Check metadata
        if old_hashes['metadata'] != new_hashes['metadata']:
            changes['metadata_changed'] = True
        
        return changes
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file contents."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def _calculate_page_hash(self, page_info: Dict) -> str:
        """Calculate hash of page content and layout."""
        content = json.dumps({
            'text': page_info.get('text', ''),
            'bbox': page_info.get('bbox', []),
            'elements': page_info.get('elements', []),
            'layout': page_info.get('layout', {}),
            'images': page_info.get('images', [])
        }, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()
    
    def _calculate_section_hash(self, section_info: Dict) -> str:
        """Calculate hash of section content."""
        content = json.dumps(section_info, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()
    
    def _hash_string(self, text: str) -> str:
        """Calculate hash of string content."""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _hash_dict(self, data: Dict) -> str:
        """Calculate hash of dictionary content."""
        content = json.dumps(data, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()
    
    def _update_cache(self, file_path: Path, file_hash: str, 
                     mtime: float) -> None:
        """Update file hash cache."""
        self.file_hash_cache[str(file_path)] = {
            'hash': file_hash,
            'mtime': mtime,
            'last_checked': datetime.now().isoformat()
        }