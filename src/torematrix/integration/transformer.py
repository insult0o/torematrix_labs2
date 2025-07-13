"""
Data transformation layer to handle format differences between components.

This module provides transformers that convert data structures between
different component formats.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ElementTransformer:
    """
    Transforms element data between different component formats.
    
    Handles conversions between:
    - Unstructured.io format
    - Core Element model format
    - Pipeline processing format
    - Storage format
    """
    
    # Element type mappings
    TYPE_MAPPINGS = {
        # Unstructured -> Core Model
        "Title": "TitleElement",
        "NarrativeText": "NarrativeTextElement",
        "ListItem": "ListItemElement",
        "Table": "TableElement",
        "Image": "ImageElement",
        "Header": "HeaderElement",
        "Footer": "FooterElement",
        "PageBreak": "PageBreakElement",
        
        # Core Model -> Pipeline
        "TitleElement": "title",
        "NarrativeTextElement": "narrative_text",
        "ListItemElement": "list_item",
        "TableElement": "table",
        "ImageElement": "image",
        
        # Pipeline -> Storage
        "title": "TITLE",
        "narrative_text": "NARRATIVE_TEXT",
        "list_item": "LIST_ITEM",
        "table": "TABLE",
        "image": "IMAGE"
    }
    
    def unstructured_to_core(self, unstructured_element: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert Unstructured.io element to core Element model format.
        
        Unstructured format:
        {
            "type": "Title",
            "text": "Hello World",
            "metadata": {
                "page_number": 1,
                "coordinates": {...}
            }
        }
        
        Core format:
        {
            "element_type": "TitleElement",
            "text": "Hello World",
            "metadata": {
                "page_number": 1,
                "coordinates": {...}
            }
        }
        """
        element_type = unstructured_element.get("type", "Unknown")
        mapped_type = self.TYPE_MAPPINGS.get(element_type, element_type)
        
        core_element = {
            "element_type": mapped_type,
            "text": unstructured_element.get("text", ""),
            "metadata": self._transform_metadata(unstructured_element.get("metadata", {}))
        }
        
        # Handle special fields
        if "element_id" in unstructured_element:
            core_element["id"] = unstructured_element["element_id"]
        
        # Handle table data
        if element_type == "Table" and "table_data" in unstructured_element:
            core_element["table_data"] = unstructured_element["table_data"]
        
        # Handle image data
        if element_type == "Image":
            if "image_base64" in unstructured_element:
                core_element["image_data"] = unstructured_element["image_base64"]
            if "image_path" in unstructured_element:
                core_element["image_path"] = unstructured_element["image_path"]
        
        return core_element
    
    def core_to_pipeline(self, core_element: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert core Element to pipeline processing format.
        
        Core format uses element classes, pipeline uses simple dicts.
        """
        element_type = core_element.get("element_type", "Unknown")
        mapped_type = self.TYPE_MAPPINGS.get(element_type, element_type.lower())
        
        pipeline_element = {
            "type": mapped_type,
            "content": core_element.get("text", ""),
            "meta": core_element.get("metadata", {}),
            "id": core_element.get("id"),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Copy special fields
        for field in ["table_data", "image_data", "image_path"]:
            if field in core_element:
                pipeline_element[field] = core_element[field]
        
        return pipeline_element
    
    def pipeline_to_storage(self, pipeline_element: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert pipeline element to storage format.
        
        Storage format uses uppercase types and different field names.
        """
        element_type = pipeline_element.get("type", "unknown")
        mapped_type = self.TYPE_MAPPINGS.get(element_type, element_type.upper())
        
        storage_element = {
            "kind": mapped_type,
            "value": pipeline_element.get("content", ""),
            "properties": pipeline_element.get("meta", {}),
            "id": pipeline_element.get("id"),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Handle nested data
        if "table_data" in pipeline_element:
            storage_element["data"] = {
                "table": pipeline_element["table_data"]
            }
        
        if "image_data" in pipeline_element or "image_path" in pipeline_element:
            storage_element["data"] = {
                "image": {
                    "data": pipeline_element.get("image_data"),
                    "path": pipeline_element.get("image_path")
                }
            }
        
        return storage_element
    
    def storage_to_core(self, storage_element: Dict[str, Any]) -> Dict[str, Any]:
        """Convert storage format back to core Element format."""
        # Reverse the mappings
        reverse_type_map = {
            "TITLE": "TitleElement",
            "NARRATIVE_TEXT": "NarrativeTextElement",
            "LIST_ITEM": "ListItemElement",
            "TABLE": "TableElement",
            "IMAGE": "ImageElement"
        }
        
        element_type = storage_element.get("kind", "UNKNOWN")
        mapped_type = reverse_type_map.get(element_type, "Element")
        
        core_element = {
            "element_type": mapped_type,
            "text": storage_element.get("value", ""),
            "metadata": storage_element.get("properties", {}),
            "id": storage_element.get("id")
        }
        
        # Extract nested data
        if "data" in storage_element:
            if "table" in storage_element["data"]:
                core_element["table_data"] = storage_element["data"]["table"]
            if "image" in storage_element["data"]:
                image_data = storage_element["data"]["image"]
                if "data" in image_data:
                    core_element["image_data"] = image_data["data"]
                if "path" in image_data:
                    core_element["image_path"] = image_data["path"]
        
        return core_element
    
    def _transform_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Transform metadata between formats."""
        transformed = {}
        
        # Standard fields
        for field in ["page_number", "filename", "filetype", "coordinates"]:
            if field in metadata:
                transformed[field] = metadata[field]
        
        # Handle coordinate format differences
        if "coordinates" in metadata:
            coords = metadata["coordinates"]
            if isinstance(coords, dict):
                # Ensure consistent coordinate format
                transformed["coordinates"] = {
                    "points": coords.get("points", []),
                    "system": coords.get("system", "pixel"),
                    "layout_width": coords.get("layout_width"),
                    "layout_height": coords.get("layout_height")
                }
        
        # Add any additional metadata
        for key, value in metadata.items():
            if key not in transformed:
                transformed[key] = value
        
        return transformed


class DataTransformer:
    """
    General data transformer for various data structures.
    """
    
    def __init__(self):
        self.element_transformer = ElementTransformer()
    
    def transform_document_batch(
        self,
        elements: List[Dict[str, Any]],
        from_format: str,
        to_format: str
    ) -> List[Dict[str, Any]]:
        """
        Transform a batch of document elements between formats.
        
        Args:
            elements: List of elements to transform
            from_format: Source format (unstructured, core, pipeline, storage)
            to_format: Target format (unstructured, core, pipeline, storage)
            
        Returns:
            List of transformed elements
        """
        transformations = {
            ("unstructured", "core"): self.element_transformer.unstructured_to_core,
            ("core", "pipeline"): self.element_transformer.core_to_pipeline,
            ("pipeline", "storage"): self.element_transformer.pipeline_to_storage,
            ("storage", "core"): self.element_transformer.storage_to_core,
        }
        
        transform_func = transformations.get((from_format, to_format))
        if not transform_func:
            # Try to find intermediate path
            if from_format == "unstructured" and to_format == "pipeline":
                # unstructured -> core -> pipeline
                elements = [self.element_transformer.unstructured_to_core(e) for e in elements]
                elements = [self.element_transformer.core_to_pipeline(e) for e in elements]
                return elements
            elif from_format == "unstructured" and to_format == "storage":
                # unstructured -> core -> pipeline -> storage
                elements = [self.element_transformer.unstructured_to_core(e) for e in elements]
                elements = [self.element_transformer.core_to_pipeline(e) for e in elements]
                elements = [self.element_transformer.pipeline_to_storage(e) for e in elements]
                return elements
            else:
                raise ValueError(f"No transformation path from {from_format} to {to_format}")
        
        return [transform_func(element) for element in elements]
    
    def normalize_event_data(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize event data to ensure consistent format across components.
        """
        normalized = {
            "timestamp": event_data.get("timestamp", datetime.utcnow().isoformat()),
            "source": event_data.get("source", "unknown")
        }
        
        # Handle different ID field names
        for id_field in ["id", "document_id", "doc_id", "element_id"]:
            if id_field in event_data:
                normalized["id"] = event_data[id_field]
                break
        
        # Handle different status field names
        for status_field in ["status", "state", "result"]:
            if status_field in event_data:
                normalized["status"] = event_data[status_field]
                break
        
        # Copy remaining fields
        for key, value in event_data.items():
            if key not in normalized:
                normalized[key] = value
        
        return normalized
    
    def merge_configurations(self, *configs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge multiple configuration dictionaries into one.
        
        Later configs override earlier ones.
        """
        merged = {}
        
        for config in configs:
            for key, value in config.items():
                if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                    # Deep merge dictionaries
                    merged[key] = self.merge_configurations(merged[key], value)
                else:
                    merged[key] = value
        
        return merged