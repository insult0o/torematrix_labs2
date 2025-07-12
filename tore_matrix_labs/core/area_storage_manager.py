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
                self.logger.warning("LOAD: No active project - attempting to load from document file directly")
                return self._load_areas_from_document_file(document_id)
            
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
    
    def _load_areas_from_document_file(self, document_id: str) -> Dict[str, VisualArea]:
        """Load areas directly from the current project file when no active project manager."""
        try:
            # First, try to get the current project file path from settings or context
            project_file = self._get_current_project_file()
            
            if not project_file:
                self.logger.warning(f"DIRECT LOAD: No current project file available for document '{document_id}'")
                return {}
            
            self.logger.info(f"DIRECT LOAD: Loading areas from current project file: {project_file}")
            
            # Load the project file
            with open(project_file, 'r') as f:
                project_data = json.load(f)
            
            # Check if this file has documents
            documents = project_data.get("documents", [])
            if not documents:
                self.logger.info(f"DIRECT LOAD: Project file '{project_file}' has no documents - checking for direct areas")
                # Check for areas directly in the project file (legacy format)
                visual_areas_data = project_data.get("visual_areas", {})
                # Only return areas if they belong to this document
                if visual_areas_data and self._is_same_project_document(project_data, document_id):
                    return self._convert_areas_data_to_objects(visual_areas_data, document_id)
                return {}
            
            # Find the matching document
            for doc in documents:
                if doc.get("id") == document_id:
                    self.logger.info(f"DIRECT LOAD: Found document '{document_id}' in current project")
                    visual_areas_data = doc.get("visual_areas", {})
                    return self._convert_areas_data_to_objects(visual_areas_data, document_id)
            
            self.logger.warning(f"DIRECT LOAD: Document '{document_id}' not found in current project '{project_file}'")
            return {}
            
        except Exception as e:
            self.logger.error(f"DIRECT LOAD: Error loading areas from project file: {e}")
            import traceback
            self.logger.error(f"DIRECT LOAD: Traceback: {traceback.format_exc()}")
            return {}
    
    def _convert_areas_data_to_objects(self, visual_areas_data: dict, document_id: str) -> Dict[str, VisualArea]:
        """Convert areas data dictionary to VisualArea objects."""
        areas = {}
        self.logger.info(f"CONVERT: Processing {len(visual_areas_data)} stored visual areas")
        
        for area_id, area_data in visual_areas_data.items():
            try:
                # Use existing conversion method
                area = self._dict_to_visual_area(area_data)
                areas[area_id] = area
                self.logger.debug(f"CONVERT: Converted area {area_id} on page {area.page}")
                
            except Exception as e:
                self.logger.error(f"CONVERT: Error converting area {area_id}: {e}")
                continue
        
        self.logger.info(f"CONVERT: Successfully converted {len(areas)} areas")
        return areas
    
    def _dict_to_visual_area(self, area_data: Dict[str, Any]) -> VisualArea:
        """Convert dictionary to VisualArea object with robust error handling."""
        try:
            # Safe enum conversion for area type
            area_type = AreaType.IMAGE  # Default fallback
            try:
                if "type" in area_data:
                    if isinstance(area_data["type"], str):
                        area_type = AreaType(area_data["type"])
                    else:
                        area_type = area_data["type"]  # Already an enum
            except (ValueError, KeyError) as e:
                self.logger.warning(f"CONVERT: Invalid area type '{area_data.get('type')}', using IMAGE: {e}")
                area_type = AreaType.IMAGE
            
            # Safe enum conversion for status
            status = AreaStatus.SAVED  # Default fallback
            try:
                status_value = area_data.get("status", "saved")
                if isinstance(status_value, str):
                    status = AreaStatus(status_value)
                else:
                    status = status_value  # Already an enum
            except (ValueError, KeyError) as e:
                self.logger.warning(f"CONVERT: Invalid status '{area_data.get('status')}', using SAVED: {e}")
                status = AreaStatus.SAVED
            
            # Safe datetime conversion
            created_at = datetime.now()
            modified_at = datetime.now()
            
            try:
                if "created_at" in area_data:
                    created_at = datetime.fromisoformat(area_data["created_at"])
            except (ValueError, TypeError) as e:
                self.logger.warning(f"CONVERT: Invalid created_at '{area_data.get('created_at')}', using current time: {e}")
            
            try:
                if "modified_at" in area_data:
                    modified_at = datetime.fromisoformat(area_data["modified_at"])
            except (ValueError, TypeError) as e:
                self.logger.warning(f"CONVERT: Invalid modified_at '{area_data.get('modified_at')}', using current time: {e}")
            
            # Safe bbox conversion
            bbox = (0, 0, 100, 100)  # Default bbox
            try:
                if "bbox" in area_data and area_data["bbox"]:
                    bbox_data = area_data["bbox"]
                    if isinstance(bbox_data, (list, tuple)) and len(bbox_data) >= 4:
                        bbox = tuple(float(x) for x in bbox_data[:4])
                    else:
                        self.logger.warning(f"CONVERT: Invalid bbox format '{bbox_data}', using default")
            except (ValueError, TypeError) as e:
                self.logger.warning(f"CONVERT: Error converting bbox '{area_data.get('bbox')}', using default: {e}")
            
            # Safe widget_rect conversion
            widget_rect = None
            try:
                if area_data.get("widget_rect"):
                    widget_data = area_data["widget_rect"]
                    if isinstance(widget_data, (list, tuple)) and len(widget_data) >= 4:
                        widget_rect = tuple(float(x) for x in widget_data[:4])
            except (ValueError, TypeError) as e:
                self.logger.warning(f"CONVERT: Error converting widget_rect, using None: {e}")
            
            # Create VisualArea with safe values
            visual_area = VisualArea(
                id=str(area_data.get("id", "unknown")),
                document_id=str(area_data.get("document_id", "")),
                area_type=area_type,
                bbox=bbox,
                page=int(area_data.get("page", 1)),
                color=str(area_data.get("color", "#FF4444")),
                status=status,
                created_at=created_at,
                modified_at=modified_at,
                user_notes=str(area_data.get("user_notes", "")),
                border_width=float(area_data.get("border_width", 2)),
                fill_opacity=float(area_data.get("fill_opacity", 0.3)),
                border_glow=bool(area_data.get("border_glow", True)),
                widget_rect=widget_rect
            )
            
            self.logger.debug(f"CONVERT: Successfully converted area {visual_area.id} (type: {visual_area.area_type.value})")
            return visual_area
            
        except Exception as e:
            self.logger.error(f"CONVERT: Critical error converting area data: {e}")
            self.logger.error(f"CONVERT: Area data: {area_data}")
            import traceback
            self.logger.error(f"CONVERT: Traceback: {traceback.format_exc()}")
            
            # Return a minimal valid VisualArea as fallback
            return VisualArea(
                id=str(area_data.get("id", f"error_{int(datetime.now().timestamp())}")),
                document_id=str(area_data.get("document_id", "")),
                area_type=AreaType.IMAGE,
                bbox=(0, 0, 100, 100),
                page=int(area_data.get("page", 1)),
                color="#FF4444",
                status=AreaStatus.SAVED,
                created_at=datetime.now(),
                modified_at=datetime.now(),
                user_notes="Recovered from conversion error",
                border_width=2,
                fill_opacity=0.3,
                border_glow=True,
                widget_rect=None
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
    
    def _get_current_project_file(self) -> Optional[str]:
        """Get the current project file path from project manager or context."""
        try:
            # First, try to get from project manager if available
            if self.project_manager and hasattr(self.project_manager, 'project_file_path'):
                project_file = self.project_manager.project_file_path
                if project_file and Path(project_file).exists():
                    self.logger.debug(f"Got project file from manager: {project_file}")
                    return project_file
            
            # Try to get from settings or stored context
            # This could be enhanced to store the last opened project in settings
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting current project file: {e}")
            return None
    
    def _is_same_project_document(self, project_data: dict, document_id: str) -> bool:
        """Check if the document belongs to the same project."""
        try:
            # For legacy format where document ID might be the project name
            project_name = project_data.get('name', '')
            if project_name == document_id or project_name == Path(document_id).stem:
                return True
            
            # Check if any document in the project matches
            for doc in project_data.get('documents', []):
                if doc.get('id') == document_id:
                    return True
                    
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking project document: {e}")
            return False
    
    def _convert_tore_area_to_visual_area_format(self, area_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert .tore file area format to VisualArea model format."""
        converted = area_data.copy()
        
        # Map field names to match VisualArea model expectations
        field_mappings = {
            'area_type': 'type',
            'selection_type': 'type', 
            'updated_at': 'modified_at',
            'text': 'user_notes'
        }
        
        for old_field, new_field in field_mappings.items():
            if old_field in converted:
                converted[new_field] = converted.pop(old_field)
        
        # Ensure required fields have defaults
        defaults = {
            'type': 'TEXT',
            'status': 'saved',
            'color': '#FF4444',
            'border_width': 2,
            'fill_opacity': 0.3,
            'border_glow': True,
            'user_notes': '',
            'widget_rect': None
        }
        
        for field, default_value in defaults.items():
            if field not in converted:
                converted[field] = default_value
        
        # Convert area_type values to match AreaType enum
        if 'type' in converted:
            type_mappings = {
                'text': 'TEXT',
                'image': 'IMAGE', 
                'table': 'TABLE',
                'diagram': 'DIAGRAM'
            }
            area_type = str(converted['type']).lower()
            if area_type in type_mappings:
                converted['type'] = type_mappings[area_type]
            else:
                converted['type'] = str(converted['type']).upper()
        
        return converted