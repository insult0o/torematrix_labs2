"""
Area Storage Manager for TORE Matrix Labs

Manages persistent area storage and retrieval from .tore files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..models.visual_area_models import VisualArea, AreaSelectionSession, AreaType, AreaStatus


class AreaStorageManager:
    """Manage persistent area storage in .tore files."""
    
    def __init__(self, project_manager=None):
        self.project_manager = project_manager
        self.logger = logging.getLogger(__name__)
        self.active_sessions: Dict[str, AreaSelectionSession] = {}
        
    def save_area(self, document_id: str, area: VisualArea) -> bool:
        """Save area to document's persistent storage."""
        try:
            self.logger.info(f"SAVE: Attempting to save area {area.id} for document '{document_id}'")
            
            if not self.project_manager:
                self.logger.warning("SAVE: No project manager available for area storage")
                return False
                
            project_data = self.project_manager.get_current_project()
            if not project_data:
                self.logger.warning("SAVE: No active project for area storage")
                return False
            
            self.logger.debug(f"SAVE: Current project has {len(project_data.get('documents', []))} documents")
            
            # Find document in project
            documents = project_data.get("documents", [])
            for doc in documents:
                self.logger.debug(f"SAVE: Checking document {doc.get('id')} against '{document_id}'")
                if doc.get("id") == document_id:
                    self.logger.info(f"SAVE: Found target document '{document_id}'")
                    
                    # Initialize visual_areas if not present
                    if "visual_areas" not in doc:
                        doc["visual_areas"] = {}
                        self.logger.debug("SAVE: Initialized visual_areas dict")
                    
                    # Save area data
                    area_dict = area.to_dict()
                    doc["visual_areas"][area.id] = area_dict
                    self.logger.info(f"SAVE: Added area {area.id} to document (page {area.page}, bbox {area.bbox})")
                    self.logger.debug(f"SAVE: Total areas in document: {len(doc['visual_areas'])}")
                    
                    # Mark area as saved
                    area.save()
                    
                    # Auto-save project
                    if hasattr(self.project_manager, 'save_current_project'):
                        save_result = self.project_manager.save_current_project()
                        self.logger.info(f"SAVE: Project auto-save result: {save_result}")
                        if save_result:
                            self.logger.info(f"SAVE: ✅ Successfully saved area {area.id} for document '{document_id}'")
                        else:
                            self.logger.error(f"SAVE: ❌ Project save failed for area {area.id}")
                        return save_result
                    else:
                        self.logger.warning("SAVE: Project manager doesn't support saving")
                        return False
            
            self.logger.warning(f"SAVE: ❌ Document '{document_id}' not found in project documents")
            return False
            
        except Exception as e:
            self.logger.error(f"SAVE: ❌ Error saving area: {e}")
            import traceback
            self.logger.error(f"SAVE: Traceback: {traceback.format_exc()}")
            return False
    
    def load_areas(self, document_id: str) -> Dict[str, VisualArea]:
        """Load all areas for a document."""
        try:
            self.logger.info(f"LOAD: Attempting to load areas for document '{document_id}'")
            
            if not self.project_manager:
                self.logger.warning("LOAD: No project manager available")
                return {}
                
            project_data = self.project_manager.get_current_project()
            if not project_data:
                self.logger.warning("LOAD: No active project")
                return {}
            
            self.logger.debug(f"LOAD: Current project has {len(project_data.get('documents', []))} documents")
            
            # Find document in project
            documents = project_data.get("documents", [])
            for doc in documents:
                self.logger.debug(f"LOAD: Checking document {doc.get('id')} against '{document_id}'")
                if doc.get("id") == document_id:
                    self.logger.info(f"LOAD: Found target document '{document_id}'")
                    
                    areas = {}
                    visual_areas_data = doc.get("visual_areas", {})
                    self.logger.info(f"LOAD: Document has {len(visual_areas_data)} stored visual areas")
                    
                    if not visual_areas_data:
                        self.logger.warning(f"LOAD: No visual_areas data found in document '{document_id}'")
                        return {}
                    
                    for area_id, area_data in visual_areas_data.items():
                        try:
                            self.logger.debug(f"LOAD: Processing area {area_id}")
                            # Convert dict back to VisualArea
                            area = self._dict_to_visual_area(area_data)
                            areas[area_id] = area
                            self.logger.debug(f"LOAD: Loaded area {area_id} on page {area.page}")
                        except Exception as e:
                            self.logger.error(f"LOAD: Error loading area {area_id}: {e}")
                    
                    self.logger.info(f"LOAD: ✅ Successfully loaded {len(areas)} areas for document '{document_id}'")
                    return areas
            
            self.logger.warning(f"LOAD: ❌ Document '{document_id}' not found in project documents")
            return {}
            
        except Exception as e:
            self.logger.error(f"LOAD: ❌ Error loading areas for document '{document_id}': {e}")
            import traceback
            self.logger.error(f"LOAD: Traceback: {traceback.format_exc()}")
            return {}
    
    def _dict_to_visual_area(self, area_data: Dict[str, Any]) -> VisualArea:
        """Convert dictionary to VisualArea object."""
        return VisualArea(
            id=area_data["id"],
            document_id=area_data["document_id"],
            area_type=AreaType(area_data["type"]),
            bbox=tuple(area_data["bbox"]),
            page=area_data["page"],
            color=area_data.get("color", "#FF4444"),
            status=AreaStatus(area_data.get("status", "saved")),
            created_at=datetime.fromisoformat(area_data["created_at"]),
            modified_at=datetime.fromisoformat(area_data["modified_at"]),
            user_notes=area_data.get("user_notes", ""),
            border_width=area_data.get("border_width", 2),
            fill_opacity=area_data.get("fill_opacity", 0.3),
            border_glow=area_data.get("border_glow", True),
            widget_rect=tuple(area_data["widget_rect"]) if area_data.get("widget_rect") else None
        )
    
    def delete_area(self, document_id: str, area_id: str) -> bool:
        """Delete area from document's storage."""
        try:
            if not self.project_manager:
                return False
                
            project_data = self.project_manager.get_current_project()
            if not project_data:
                return False
            
            # Find document in project
            documents = project_data.get("documents", [])
            for doc in documents:
                if doc.get("id") == document_id:
                    visual_areas = doc.get("visual_areas", {})
                    if area_id in visual_areas:
                        del visual_areas[area_id]
                        
                        # Auto-save project
                        if hasattr(self.project_manager, 'save_current_project'):
                            self.project_manager.save_current_project()
                            self.logger.info(f"Deleted area {area_id} from document {document_id}")
                            return True
                    break
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error deleting area: {e}")
            return False
    
    def get_areas_for_page(self, document_id: str, page: int) -> Dict[str, VisualArea]:
        """Get all areas for a specific page."""
        self.logger.info(f"GET_PAGE: Filtering areas for document '{document_id}', page {page}")
        
        all_areas = self.load_areas(document_id)
        self.logger.info(f"GET_PAGE: Document has {len(all_areas)} total areas")
        
        page_areas = {}
        for aid, area in all_areas.items():
            self.logger.debug(f"GET_PAGE: Area {aid} is on page {area.page} (looking for page {page})")
            if area.page == page:
                page_areas[aid] = area
                self.logger.debug(f"GET_PAGE: ✅ Area {aid} matches page {page}")
            else:
                self.logger.debug(f"GET_PAGE: ❌ Area {aid} on page {area.page} != {page}")
        
        self.logger.info(f"GET_PAGE: Found {len(page_areas)} areas for page {page}")
        return page_areas
    
    def update_area(self, document_id: str, area: VisualArea) -> bool:
        """Update an existing area."""
        self.logger.info(f"UPDATE: Updating area {area.id} for document '{document_id}'")
        self.logger.info(f"UPDATE: New bbox: {area.bbox}, page: {area.page}")
        
        area.modified_at = datetime.now()
        area.status = AreaStatus.MODIFIED
        
        save_result = self.save_area(document_id, area)
        self.logger.info(f"UPDATE: Save result for area {area.id}: {save_result}")
        
        return save_result
    
    def get_session(self, document_id: str) -> AreaSelectionSession:
        """Get or create area selection session for document."""
        if document_id not in self.active_sessions:
            # Create new session
            session = AreaSelectionSession(document_id=document_id)
            
            # Load existing areas into session
            existing_areas = self.load_areas(document_id)
            session.areas = existing_areas
            
            self.active_sessions[document_id] = session
            
        return self.active_sessions[document_id]
    
    def save_session(self, session: AreaSelectionSession) -> bool:
        """Save all areas in a session."""
        success = True
        for area in session.areas.values():
            if not self.save_area(session.document_id, area):
                success = False
        return success
    
    def clear_session(self, document_id: str):
        """Clear active session for document."""
        if document_id in self.active_sessions:
            del self.active_sessions[document_id]
    
    def get_area_statistics(self, document_id: str) -> Dict[str, Any]:
        """Get statistics about areas in a document."""
        areas = self.load_areas(document_id)
        
        type_counts = {}
        page_counts = {}
        
        for area in areas.values():
            # Count by type
            area_type = area.area_type.value
            type_counts[area_type] = type_counts.get(area_type, 0) + 1
            
            # Count by page
            page = area.page
            page_counts[page] = page_counts.get(page, 0) + 1
        
        return {
            'total_areas': len(areas),
            'type_counts': type_counts,
            'page_counts': page_counts,
            'pages_with_areas': len(page_counts)
        }
    
    def export_areas_to_json(self, document_id: str, output_file: str) -> bool:
        """Export all areas for a document to JSON file."""
        try:
            areas = self.load_areas(document_id)
            areas_data = {aid: area.to_dict() for aid, area in areas.items()}
            
            with open(output_file, 'w') as f:
                json.dump({
                    'document_id': document_id,
                    'exported_at': datetime.now().isoformat(),
                    'total_areas': len(areas),
                    'areas': areas_data
                }, f, indent=2)
            
            self.logger.info(f"Exported {len(areas)} areas to {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting areas: {e}")
            return False