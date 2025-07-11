#!/usr/bin/env python3
"""
Area Repository for TORE Matrix Labs V2

Repository for visual area data storage and retrieval.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from .repository_base import RepositoryBase
from ..models.unified_area_model import UnifiedArea, AreaType, AreaStatus


class AreaRepository(RepositoryBase):
    """Repository for area data storage and retrieval."""
    
    def __init__(self, storage_config: Optional[Dict[str, Any]] = None):
        """Initialize area repository."""
        super().__init__(storage_config)
        self.logger = logging.getLogger(__name__)
        self.logger.info("Area repository initialized")
    
    def save_area(self, area: UnifiedArea) -> bool:
        """Save an area to storage."""
        try:
            area.modified_at = datetime.now()
            area_data = area.to_dict()
            return self.save(area.id, area_data)
        except Exception as e:
            self.logger.error(f"Failed to save area {area.id}: {str(e)}")
            return False
    
    def load_area(self, area_id: str) -> Optional[UnifiedArea]:
        """Load an area by ID."""
        try:
            area_data = self.load(area_id)
            if not area_data:
                return None
            return UnifiedArea.from_dict(area_data)
        except Exception as e:
            self.logger.error(f"Failed to load area {area_id}: {str(e)}")
            return None
    
    def delete_area(self, area_id: str) -> bool:
        """Delete an area."""
        try:
            return self.delete(area_id)
        except Exception as e:
            self.logger.error(f"Failed to delete area {area_id}: {str(e)}")
            return False
    
    def list_areas_by_document(self, document_id: str) -> List[UnifiedArea]:
        """List all areas for a document."""
        try:
            all_ids = self.list_all()
            areas = []
            
            for area_id in all_ids:
                area = self.load_area(area_id)
                if area and area.document_id == document_id:
                    areas.append(area)
            
            return areas
        except Exception as e:
            self.logger.error(f"Failed to list areas for document: {str(e)}")
            return []
    
    def list_areas_by_type(self, area_type: AreaType) -> List[UnifiedArea]:
        """List all areas of specific type."""
        try:
            all_ids = self.list_all()
            areas = []
            
            for area_id in all_ids:
                area = self.load_area(area_id)
                if area and area.area_type == area_type:
                    areas.append(area)
            
            return areas
        except Exception as e:
            self.logger.error(f"Failed to list areas by type: {str(e)}")
            return []