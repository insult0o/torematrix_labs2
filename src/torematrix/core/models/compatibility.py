"""
V1 .tore format compatibility module.

This module provides backward compatibility with the V1 TORE Matrix format,
enabling seamless migration and support for existing .tore files.
"""

import json
from typing import Any, Dict, List, Optional, Union
from dataclasses import asdict
from datetime import datetime

from .element import Element, ElementType
from .metadata import ElementMetadata
from .coordinates import Coordinates
from .complex_types import (
    TableElement, ImageElement, FormulaElement, 
    PageBreakElement, CodeBlockElement,
    TableMetadata, ImageMetadata, FormulaMetadata, CodeMetadata,
    FormulaType, CodeLanguage
)


class ToreV1Converter:
    """
    Converter for V1 .tore format compatibility.
    
    Handles bidirectional conversion between V1 format and new unified model.
    Maintains data integrity and provides migration path.
    """
    
    # V1 to V3 element type mapping
    V1_TYPE_MAPPING = {
        "title": ElementType.TITLE,
        "narrative_text": ElementType.NARRATIVE_TEXT,
        "list_item": ElementType.LIST_ITEM,
        "header": ElementType.HEADER,
        "footer": ElementType.FOOTER,
        "text": ElementType.TEXT,
        "table": ElementType.TABLE,
        "table_row": ElementType.TABLE_ROW,
        "table_cell": ElementType.TABLE_CELL,
        "image": ElementType.IMAGE,
        "figure": ElementType.FIGURE,
        "figure_caption": ElementType.FIGURE_CAPTION,
        "formula": ElementType.FORMULA,
        "address": ElementType.ADDRESS,
        "email_address": ElementType.EMAIL_ADDRESS,
        "page_break": ElementType.PAGE_BREAK,
        "page_number": ElementType.PAGE_NUMBER,
        "uncategorized_text": ElementType.UNCATEGORIZED_TEXT,
        "code_block": ElementType.CODE_BLOCK,
        "list": ElementType.LIST,
        "composite_element": ElementType.COMPOSITE_ELEMENT,
        "table_of_contents": ElementType.TABLE_OF_CONTENTS,
    }
    
    # V3 to V1 element type mapping (reverse)
    V3_TYPE_MAPPING = {v: k for k, v in V1_TYPE_MAPPING.items()}
    
    @staticmethod
    def from_v1_format(v1_data: Dict[str, Any]) -> List[Element]:
        """
        Convert V1 .tore format to new unified model.
        
        Args:
            v1_data: Dictionary containing V1 .tore file data
            
        Returns:
            List of Element instances in new format
            
        Raises:
            ValueError: If V1 data format is invalid
        """
        try:
            elements = []
            
            # Handle different V1 formats
            if "elements" in v1_data:
                v1_elements = v1_data["elements"]
            elif "content" in v1_data:
                v1_elements = v1_data["content"]
            elif isinstance(v1_data, list):
                v1_elements = v1_data
            else:
                raise ValueError("Unknown V1 format structure")
            
            for v1_element in v1_elements:
                element = ToreV1Converter._convert_v1_element(v1_element)
                if element:
                    elements.append(element)
            
            return elements
            
        except Exception as e:
            raise ValueError(f"Failed to convert V1 format: {e}")
    
    @staticmethod
    def _convert_v1_element(v1_element: Dict[str, Any]) -> Optional[Element]:
        """Convert single V1 element to V3 format"""
        try:
            # Extract basic properties
            element_type_str = v1_element.get("type", "narrative_text")
            text = v1_element.get("text", "")
            element_id = v1_element.get("id")
            
            # Map V1 type to V3 type
            element_type = ToreV1Converter.V1_TYPE_MAPPING.get(
                element_type_str.lower(), 
                ElementType.NARRATIVE_TEXT
            )
            
            # Convert metadata
            metadata = ToreV1Converter._convert_v1_metadata(v1_element)
            
            # Handle complex types with special processing
            if element_type == ElementType.TABLE:
                return ToreV1Converter._convert_v1_table(v1_element, metadata)
            elif element_type == ElementType.IMAGE:
                return ToreV1Converter._convert_v1_image(v1_element, metadata)
            elif element_type == ElementType.FORMULA:
                return ToreV1Converter._convert_v1_formula(v1_element, metadata)
            elif element_type == ElementType.CODE_BLOCK:
                return ToreV1Converter._convert_v1_code_block(v1_element, metadata)
            elif element_type == ElementType.PAGE_BREAK:
                return PageBreakElement(
                    element_id=element_id,
                    text=text or "[Page Break]",
                    metadata=metadata
                )
            else:
                # Standard element
                return Element(
                    element_id=element_id,
                    element_type=element_type,
                    text=text,
                    metadata=metadata,
                    parent_id=v1_element.get("parent_id")
                )
                
        except Exception as e:
            print(f"Warning: Failed to convert V1 element: {e}")
            return None
    
    @staticmethod
    def _convert_v1_metadata(v1_element: Dict[str, Any]) -> Optional[ElementMetadata]:
        """Convert V1 metadata to V3 format"""
        metadata_dict = {}
        
        # Handle coordinates
        if "bbox" in v1_element or "coordinates" in v1_element:
            bbox_data = v1_element.get("bbox") or v1_element.get("coordinates")
            if bbox_data:
                coordinates = Coordinates(
                    layout_bbox=bbox_data.get("layout_bbox"),
                    text_bbox=bbox_data.get("text_bbox"),
                    points=bbox_data.get("points"),
                    system=bbox_data.get("system", "pixel")
                )
                metadata_dict["coordinates"] = coordinates
        
        # Handle other metadata fields
        metadata_dict["confidence"] = v1_element.get("confidence", 1.0)
        metadata_dict["detection_method"] = "v1_migration"
        metadata_dict["page_number"] = v1_element.get("page_number")
        metadata_dict["languages"] = v1_element.get("languages", [])
        
        # Custom fields for V1-specific data
        custom_fields = {}
        for key, value in v1_element.items():
            if key not in ["type", "text", "id", "parent_id", "bbox", "coordinates", 
                          "confidence", "page_number", "languages"]:
                custom_fields[f"v1_{key}"] = value
        
        if custom_fields:
            metadata_dict["custom_fields"] = custom_fields
        
        if any(metadata_dict.values()):
            return ElementMetadata(**metadata_dict)
        return None
    
    @staticmethod
    def _convert_v1_table(v1_element: Dict[str, Any], metadata: Optional[ElementMetadata]) -> TableElement:
        """Convert V1 table to TableElement"""
        # Extract table data
        cells = v1_element.get("cells", [])
        headers = v1_element.get("headers")
        
        # Create table metadata
        table_metadata = TableMetadata(
            num_rows=len(cells),
            num_cols=max(len(row) for row in cells) if cells else 0,
            has_header=headers is not None,
            table_type=v1_element.get("table_type", "standard")
        )
        
        return TableElement(
            element_id=v1_element.get("id"),
            text=v1_element.get("text", ""),
            metadata=metadata,
            cells=cells,
            headers=headers,
            table_metadata=table_metadata
        )
    
    @staticmethod
    def _convert_v1_image(v1_element: Dict[str, Any], metadata: Optional[ElementMetadata]) -> ImageElement:
        """Convert V1 image to ImageElement"""
        # Create image metadata
        image_metadata = ImageMetadata(
            width=v1_element.get("width"),
            height=v1_element.get("height"),
            format=v1_element.get("format"),
            dpi=v1_element.get("dpi")
        )
        
        return ImageElement(
            element_id=v1_element.get("id"),
            text=v1_element.get("text", ""),
            metadata=metadata,
            image_data=v1_element.get("image_data"),
            image_url=v1_element.get("image_url"),
            alt_text=v1_element.get("alt_text"),
            caption=v1_element.get("caption"),
            image_metadata=image_metadata
        )
    
    @staticmethod
    def _convert_v1_formula(v1_element: Dict[str, Any], metadata: Optional[ElementMetadata]) -> FormulaElement:
        """Convert V1 formula to FormulaElement"""
        # Map formula type
        formula_type = FormulaType.INLINE
        if v1_element.get("formula_type") == "display":
            formula_type = FormulaType.DISPLAY
        elif v1_element.get("formula_type") == "equation":
            formula_type = FormulaType.EQUATION
        
        formula_metadata = FormulaMetadata(formula_type=formula_type)
        
        return FormulaElement(
            element_id=v1_element.get("id"),
            text=v1_element.get("text", ""),
            metadata=metadata,
            latex=v1_element.get("latex", ""),
            mathml=v1_element.get("mathml"),
            formula_metadata=formula_metadata
        )
    
    @staticmethod
    def _convert_v1_code_block(v1_element: Dict[str, Any], metadata: Optional[ElementMetadata]) -> CodeBlockElement:
        """Convert V1 code block to CodeBlockElement"""
        # Map language
        language = CodeLanguage.UNKNOWN
        lang_str = v1_element.get("language", "").lower()
        try:
            language = CodeLanguage(lang_str)
        except ValueError:
            pass
        
        code_metadata = CodeMetadata(
            language=language,
            line_count=len(v1_element.get("text", "").split('\n'))
        )
        
        return CodeBlockElement(
            element_id=v1_element.get("id"),
            text=v1_element.get("text", ""),
            metadata=metadata,
            code_metadata=code_metadata
        )
    
    @staticmethod
    def to_v1_format(elements: List[Element]) -> Dict[str, Any]:
        """
        Convert new unified model to V1 .tore format.
        
        Args:
            elements: List of Element instances in new format
            
        Returns:
            Dictionary in V1 .tore format
            
        Raises:
            ValueError: If conversion fails
        """
        try:
            v1_elements = []
            
            for element in elements:
                v1_element = ToreV1Converter._convert_to_v1_element(element)
                if v1_element:
                    v1_elements.append(v1_element)
            
            # V1 format structure
            return {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "migrated_from": "v3",
                "elements": v1_elements
            }
            
        except Exception as e:
            raise ValueError(f"Failed to convert to V1 format: {e}")
    
    @staticmethod
    def _convert_to_v1_element(element: Element) -> Dict[str, Any]:
        """Convert single V3 element to V1 format"""
        # Basic V1 structure
        v1_element = {
            "id": element.element_id,
            "type": ToreV1Converter.V3_TYPE_MAPPING.get(element.element_type, "narrative_text"),
            "text": element.text
        }
        
        if element.parent_id:
            v1_element["parent_id"] = element.parent_id
        
        # Convert metadata
        if element.metadata:
            if element.metadata.coordinates:
                v1_element["bbox"] = {
                    "layout_bbox": element.metadata.coordinates.layout_bbox,
                    "text_bbox": element.metadata.coordinates.text_bbox,
                    "points": element.metadata.coordinates.points,
                    "system": element.metadata.coordinates.system
                }
            
            v1_element["confidence"] = element.metadata.confidence
            v1_element["page_number"] = element.metadata.page_number
            v1_element["languages"] = element.metadata.languages
            
            # Extract V1-specific fields from custom_fields
            if element.metadata.custom_fields:
                for key, value in element.metadata.custom_fields.items():
                    if key.startswith("v1_"):
                        v1_element[key[3:]] = value  # Remove "v1_" prefix
        
        # Handle complex types
        if isinstance(element, TableElement):
            v1_element.update({
                "cells": element.cells,
                "headers": element.headers,
                "table_type": element.table_metadata.table_type
            })
        elif isinstance(element, ImageElement):
            v1_element.update({
                "image_data": element.image_data,
                "image_url": element.image_url,
                "alt_text": element.alt_text,
                "caption": element.caption,
                "width": element.image_metadata.width,
                "height": element.image_metadata.height,
                "format": element.image_metadata.format,
                "dpi": element.image_metadata.dpi
            })
        elif isinstance(element, FormulaElement):
            v1_element.update({
                "latex": element.latex,
                "mathml": element.mathml,
                "formula_type": element.formula_metadata.formula_type.value
            })
        elif isinstance(element, CodeBlockElement):
            v1_element.update({
                "language": element.code_metadata.language.value
            })
        
        return v1_element


class ToreFileHandler:
    """Handler for .tore file operations with V1 compatibility"""
    
    @staticmethod
    def load_tore_file(file_path: str) -> List[Element]:
        """
        Load .tore file and convert to unified model.
        
        Automatically detects V1 vs V3 format and converts appropriately.
        
        Args:
            file_path: Path to .tore file
            
        Returns:
            List of Element instances
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Detect format version
            if ToreFileHandler._is_v1_format(data):
                return ToreV1Converter.from_v1_format(data)
            else:
                # Assume V3 format
                return ToreFileHandler._load_v3_format(data)
                
        except FileNotFoundError:
            raise FileNotFoundError(f"TORE file not found: {file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in TORE file: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load TORE file: {e}")
    
    @staticmethod
    def save_tore_file(
        elements: List[Element], 
        file_path: str, 
        format_version: str = "v3",
        preserve_v1_compatibility: bool = True
    ) -> None:
        """
        Save elements to .tore file.
        
        Args:
            elements: List of elements to save
            file_path: Output file path
            format_version: "v1" or "v3" 
            preserve_v1_compatibility: Include V1-compatible fields
            
        Raises:
            ValueError: If save operation fails
        """
        try:
            if format_version == "v1":
                data = ToreV1Converter.to_v1_format(elements)
            else:
                data = ToreFileHandler._save_v3_format(elements, preserve_v1_compatibility)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            raise ValueError(f"Failed to save TORE file: {e}")
    
    @staticmethod
    def _is_v1_format(data: Dict[str, Any]) -> bool:
        """Detect if data is in V1 format"""
        # V1 format indicators
        if "version" in data and data["version"].startswith("1"):
            return True
        
        # Check structure patterns
        if "elements" in data and isinstance(data["elements"], list):
            if data["elements"] and "type" in data["elements"][0]:
                # V1 has "type" field, V3 has "element_type"
                return "element_type" not in data["elements"][0]
        
        return False
    
    @staticmethod
    def _load_v3_format(data: Dict[str, Any]) -> List[Element]:
        """Load V3 format data"""
        elements = []
        
        if "elements" in data:
            for elem_data in data["elements"]:
                element = Element.from_dict(elem_data)
                elements.append(element)
        
        return elements
    
    @staticmethod
    def _save_v3_format(elements: List[Element], include_v1_compat: bool) -> Dict[str, Any]:
        """Save in V3 format with optional V1 compatibility"""
        element_dicts = []
        
        for element in elements:
            elem_dict = element.to_dict()
            
            # Add V1 compatibility fields if requested
            if include_v1_compat:
                elem_dict["v1_type"] = ToreV1Converter.V3_TYPE_MAPPING.get(
                    element.element_type, "narrative_text"
                )
            
            element_dicts.append(elem_dict)
        
        return {
            "version": "3.0",
            "format": "unified_element_model",
            "created_at": datetime.now().isoformat(),
            "v1_compatible": include_v1_compat,
            "elements": element_dicts
        }