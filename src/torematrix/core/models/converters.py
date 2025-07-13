"""
Format conversion utilities for transforming elements between different formats.
Supports conversion to/from JSON, XML, CSV, and other common formats.
"""

import json
import csv
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Union, TextIO
from io import StringIO
import uuid

from .element import Element, ElementType
from .factory import ElementFactory


class JSONConverter:
    """Convert elements to/from JSON format"""
    
    @staticmethod
    def elements_to_json(
        elements: List[Element],
        indent: Optional[int] = 2,
        include_metadata: bool = True
    ) -> str:
        """
        Convert elements to JSON string
        
        Args:
            elements: List of elements to convert
            indent: JSON indentation (None for compact)
            include_metadata: Whether to include metadata
            
        Returns:
            JSON string representation
        """
        data = []
        
        for element in elements:
            element_dict = {
                'element_id': element.element_id,
                'element_type': element.element_type.value,
                'text': element.text,
                'parent_id': element.parent_id
            }
            
            if include_metadata:
                element_dict['metadata'] = element.to_dict()['metadata']
            
            data.append(element_dict)
        
        return json.dumps(data, indent=indent, ensure_ascii=False)
    
    @staticmethod
    def elements_from_json(json_data: Union[str, Dict, List]) -> List[Element]:
        """
        Convert JSON to elements
        
        Args:
            json_data: JSON string or parsed data
            
        Returns:
            List of Element instances
            
        Raises:
            ValueError: If JSON format is invalid
        """
        if isinstance(json_data, str):
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {e}")
        else:
            data = json_data
        
        if not isinstance(data, list):
            raise ValueError("JSON must contain a list of elements")
        
        elements = []
        for item in data:
            try:
                element = Element.from_dict(item)
                elements.append(element)
            except Exception as e:
                raise ValueError(f"Failed to parse element: {e}")
        
        return elements
    
    @staticmethod
    def element_to_dict(
        element: Element,
        include_metadata: bool = True
    ) -> Dict[str, Any]:
        """Convert single element to dictionary"""
        result = {
            'element_id': element.element_id,
            'element_type': element.element_type.value,
            'text': element.text,
            'parent_id': element.parent_id
        }
        
        if include_metadata:
            result['metadata'] = element.to_dict()['metadata']
        
        return result


class XMLConverter:
    """Convert elements to/from XML format"""
    
    @staticmethod
    def elements_to_xml(
        elements: List[Element],
        root_name: str = "document",
        include_metadata: bool = True
    ) -> str:
        """
        Convert elements to XML string
        
        Args:
            elements: List of elements to convert
            root_name: Name of root XML element
            include_metadata: Whether to include metadata
            
        Returns:
            XML string representation
        """
        root = ET.Element(root_name)
        
        for element in elements:
            elem_xml = ET.SubElement(root, "element")
            elem_xml.set("id", element.element_id)
            elem_xml.set("type", element.element_type.value)
            
            if element.parent_id:
                elem_xml.set("parent_id", element.parent_id)
            
            # Add text content
            text_elem = ET.SubElement(elem_xml, "text")
            text_elem.text = element.text
            
            # Add metadata if requested
            if include_metadata:
                metadata_elem = ET.SubElement(elem_xml, "metadata")
                XMLConverter._add_metadata_to_xml(metadata_elem, element)
        
        # Format XML
        XMLConverter._indent_xml(root)
        return ET.tostring(root, encoding='unicode')
    
    @staticmethod
    def elements_from_xml(xml_data: str) -> List[Element]:
        """
        Convert XML to elements
        
        Args:
            xml_data: XML string
            
        Returns:
            List of Element instances
            
        Raises:
            ValueError: If XML format is invalid
        """
        try:
            root = ET.fromstring(xml_data)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML: {e}")
        
        elements = []
        
        for elem_xml in root.findall("element"):
            try:
                # Extract basic attributes
                element_id = elem_xml.get("id")
                element_type = elem_xml.get("type")
                parent_id = elem_xml.get("parent_id")
                
                # Extract text
                text_elem = elem_xml.find("text")
                text = text_elem.text if text_elem is not None else ""
                
                # Extract metadata
                metadata = {}
                metadata_elem = elem_xml.find("metadata")
                if metadata_elem is not None:
                    metadata = XMLConverter._parse_metadata_from_xml(metadata_elem)
                
                # Create element
                element = ElementFactory.create_element(
                    element_type=element_type,
                    text=text,
                    metadata=metadata,
                    element_id=element_id,
                    parent_id=parent_id
                )
                elements.append(element)
                
            except Exception as e:
                raise ValueError(f"Failed to parse XML element: {e}")
        
        return elements
    
    @staticmethod
    def _add_metadata_to_xml(metadata_elem: ET.Element, element: Element):
        """Add metadata to XML element"""
        metadata = element.metadata
        
        # Add basic metadata
        if metadata.confidence != 1.0:
            confidence_elem = ET.SubElement(metadata_elem, "confidence")
            confidence_elem.text = str(metadata.confidence)
        
        if metadata.detection_method != "default":
            method_elem = ET.SubElement(metadata_elem, "detection_method")
            method_elem.text = metadata.detection_method
        
        if metadata.page_number is not None:
            page_elem = ET.SubElement(metadata_elem, "page_number")
            page_elem.text = str(metadata.page_number)
        
        if metadata.languages:
            lang_elem = ET.SubElement(metadata_elem, "languages")
            for lang in metadata.languages:
                lang_item = ET.SubElement(lang_elem, "language")
                lang_item.text = lang
        
        # Add coordinates
        if metadata.coordinates:
            coord_elem = ET.SubElement(metadata_elem, "coordinates")
            coords = metadata.coordinates
            
            if coords.layout_bbox:
                bbox_elem = ET.SubElement(coord_elem, "layout_bbox")
                bbox_elem.text = ",".join(str(x) for x in coords.layout_bbox)
            
            if coords.text_bbox:
                bbox_elem = ET.SubElement(coord_elem, "text_bbox")
                bbox_elem.text = ",".join(str(x) for x in coords.text_bbox)
            
            if coords.system != "pixel":
                system_elem = ET.SubElement(coord_elem, "system")
                system_elem.text = coords.system
        
        # Add custom fields
        if metadata.custom_fields:
            custom_elem = ET.SubElement(metadata_elem, "custom_fields")
            for key, value in metadata.custom_fields.items():
                field_elem = ET.SubElement(custom_elem, "field")
                field_elem.set("name", key)
                field_elem.text = str(value)
    
    @staticmethod
    def _parse_metadata_from_xml(metadata_elem: ET.Element) -> Dict[str, Any]:
        """Parse metadata from XML element"""
        metadata = {}
        
        # Basic metadata
        confidence_elem = metadata_elem.find("confidence")
        if confidence_elem is not None:
            metadata['confidence'] = float(confidence_elem.text)
        
        method_elem = metadata_elem.find("detection_method")
        if method_elem is not None:
            metadata['detection_method'] = method_elem.text
        
        page_elem = metadata_elem.find("page_number")
        if page_elem is not None:
            metadata['page_number'] = int(page_elem.text)
        
        # Languages
        lang_elem = metadata_elem.find("languages")
        if lang_elem is not None:
            languages = [lang.text for lang in lang_elem.findall("language")]
            metadata['languages'] = languages
        
        # Coordinates
        coord_elem = metadata_elem.find("coordinates")
        if coord_elem is not None:
            coordinates = {}
            
            layout_bbox_elem = coord_elem.find("layout_bbox")
            if layout_bbox_elem is not None:
                coordinates['layout_bbox'] = [float(x) for x in layout_bbox_elem.text.split(",")]
            
            text_bbox_elem = coord_elem.find("text_bbox")
            if text_bbox_elem is not None:
                coordinates['text_bbox'] = [float(x) for x in text_bbox_elem.text.split(",")]
            
            system_elem = coord_elem.find("system")
            if system_elem is not None:
                coordinates['system'] = system_elem.text
            
            if coordinates:
                metadata['coordinates'] = coordinates
        
        # Custom fields
        custom_elem = metadata_elem.find("custom_fields")
        if custom_elem is not None:
            custom_fields = {}
            for field_elem in custom_elem.findall("field"):
                name = field_elem.get("name")
                value = field_elem.text
                custom_fields[name] = value
            metadata['custom_fields'] = custom_fields
        
        return metadata
    
    @staticmethod
    def _indent_xml(elem: ET.Element, level: int = 0):
        """Add indentation to XML for pretty printing"""
        indent = "\n" + "  " * level
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = indent + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = indent
            for child in elem:
                XMLConverter._indent_xml(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = indent
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = indent


class CSVConverter:
    """Convert elements to/from CSV format"""
    
    @staticmethod
    def elements_to_csv(
        elements: List[Element],
        include_metadata: bool = False,
        delimiter: str = ","
    ) -> str:
        """
        Convert elements to CSV string
        
        Args:
            elements: List of elements to convert
            include_metadata: Whether to include metadata columns
            delimiter: CSV delimiter
            
        Returns:
            CSV string representation
        """
        output = StringIO()
        
        # Define basic columns
        fieldnames = ['element_id', 'element_type', 'text', 'parent_id']
        
        # Add metadata columns if requested
        if include_metadata:
            fieldnames.extend([
                'confidence', 'detection_method', 'page_number',
                'languages', 'layout_bbox', 'text_bbox', 'custom_fields'
            ])
        
        writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        
        for element in elements:
            row = {
                'element_id': element.element_id,
                'element_type': element.element_type.value,
                'text': element.text,
                'parent_id': element.parent_id or ''
            }
            
            if include_metadata:
                metadata = element.metadata
                row.update({
                    'confidence': metadata.confidence,
                    'detection_method': metadata.detection_method,
                    'page_number': metadata.page_number or '',
                    'languages': ';'.join(metadata.languages) if metadata.languages else '',
                    'layout_bbox': ','.join(str(x) for x in metadata.coordinates.layout_bbox) if metadata.coordinates and metadata.coordinates.layout_bbox else '',
                    'text_bbox': ','.join(str(x) for x in metadata.coordinates.text_bbox) if metadata.coordinates and metadata.coordinates.text_bbox else '',
                    'custom_fields': json.dumps(metadata.custom_fields) if metadata.custom_fields else ''
                })
            
            writer.writerow(row)
        
        return output.getvalue()
    
    @staticmethod
    def elements_from_csv(
        csv_data: str,
        has_metadata: bool = False,
        delimiter: str = ","
    ) -> List[Element]:
        """
        Convert CSV to elements
        
        Args:
            csv_data: CSV string
            has_metadata: Whether CSV includes metadata columns
            delimiter: CSV delimiter
            
        Returns:
            List of Element instances
            
        Raises:
            ValueError: If CSV format is invalid
        """
        try:
            reader = csv.DictReader(StringIO(csv_data), delimiter=delimiter)
            elements = []
            
            for row in reader:
                # Basic element data
                element_data = {
                    'element_type': row['element_type'],
                    'text': row['text'],
                    'element_id': row.get('element_id', str(uuid.uuid4())),
                    'parent_id': row.get('parent_id') or None
                }
                
                # Parse metadata if present
                if has_metadata:
                    metadata = {}
                    
                    if 'confidence' in row and row['confidence']:
                        metadata['confidence'] = float(row['confidence'])
                    
                    if 'detection_method' in row and row['detection_method']:
                        metadata['detection_method'] = row['detection_method']
                    
                    if 'page_number' in row and row['page_number']:
                        metadata['page_number'] = int(row['page_number'])
                    
                    if 'languages' in row and row['languages']:
                        metadata['languages'] = row['languages'].split(';')
                    
                    # Parse coordinates
                    coordinates = {}
                    if 'layout_bbox' in row and row['layout_bbox']:
                        coordinates['layout_bbox'] = [float(x) for x in row['layout_bbox'].split(',')]
                    
                    if 'text_bbox' in row and row['text_bbox']:
                        coordinates['text_bbox'] = [float(x) for x in row['text_bbox'].split(',')]
                    
                    if coordinates:
                        metadata['coordinates'] = coordinates
                    
                    # Parse custom fields
                    if 'custom_fields' in row and row['custom_fields']:
                        try:
                            metadata['custom_fields'] = json.loads(row['custom_fields'])
                        except json.JSONDecodeError:
                            pass  # Skip invalid JSON
                    
                    element_data['metadata'] = metadata
                
                # Create element
                element = ElementFactory.create_element(**element_data)
                elements.append(element)
            
            return elements
            
        except Exception as e:
            raise ValueError(f"Failed to parse CSV: {e}")


class PlainTextConverter:
    """Convert elements to/from plain text format"""
    
    @staticmethod
    def elements_to_text(
        elements: List[Element],
        include_types: bool = False,
        separator: str = "\n\n"
    ) -> str:
        """
        Convert elements to plain text
        
        Args:
            elements: List of elements to convert
            include_types: Whether to include element types
            separator: Text separator between elements
            
        Returns:
            Plain text representation
        """
        lines = []
        
        for element in elements:
            if include_types:
                line = f"[{element.element_type.value}] {element.text}"
            else:
                line = element.text
            
            lines.append(line)
        
        return separator.join(lines)
    
    @staticmethod
    def text_to_elements(
        text: str,
        element_type: ElementType = ElementType.NARRATIVE_TEXT,
        split_by: str = "\n\n"
    ) -> List[Element]:
        """
        Convert plain text to elements
        
        Args:
            text: Plain text content
            element_type: Default element type
            split_by: Text splitter for creating multiple elements
            
        Returns:
            List of Element instances
        """
        if not text.strip():
            return []
        
        # Split text into segments
        segments = [seg.strip() for seg in text.split(split_by) if seg.strip()]
        
        elements = []
        for segment in segments:
            element = ElementFactory.create_from_text(
                text=segment,
                element_type=element_type
            )
            elements.append(element)
        
        return elements


class UniversalConverter:
    """Universal converter that auto-detects format"""
    
    FORMAT_CONVERTERS = {
        'json': JSONConverter,
        'xml': XMLConverter,
        'csv': CSVConverter,
        'txt': PlainTextConverter
    }
    
    @staticmethod
    def auto_convert_from_string(
        data: str,
        format_hint: Optional[str] = None
    ) -> List[Element]:
        """
        Auto-detect format and convert to elements
        
        Args:
            data: String data in unknown format
            format_hint: Optional format hint ('json', 'xml', 'csv', 'txt')
            
        Returns:
            List of Element instances
            
        Raises:
            ValueError: If format cannot be detected or conversion fails
        """
        if format_hint and format_hint in UniversalConverter.FORMAT_CONVERTERS:
            converter = UniversalConverter.FORMAT_CONVERTERS[format_hint]
            
            if format_hint == 'json':
                return converter.elements_from_json(data)
            elif format_hint == 'xml':
                return converter.elements_from_xml(data)
            elif format_hint == 'csv':
                return converter.elements_from_csv(data)
            elif format_hint == 'txt':
                return converter.text_to_elements(data)
        
        # Try to auto-detect format
        data_stripped = data.strip()
        
        # Try JSON first
        if (data_stripped.startswith('[') and data_stripped.endswith(']')) or \
           (data_stripped.startswith('{') and data_stripped.endswith('}')):
            try:
                return JSONConverter.elements_from_json(data)
            except:
                pass
        
        # Try XML
        if data_stripped.startswith('<') and data_stripped.endswith('>'):
            try:
                return XMLConverter.elements_from_xml(data)
            except:
                pass
        
        # Try CSV (look for comma-separated headers)
        lines = data_stripped.split('\n')
        if len(lines) > 1 and ',' in lines[0]:
            try:
                return CSVConverter.elements_from_csv(data, has_metadata=True)
            except:
                try:
                    return CSVConverter.elements_from_csv(data, has_metadata=False)
                except:
                    pass
        
        # Default to plain text
        return PlainTextConverter.text_to_elements(data)
    
    @staticmethod
    def convert_elements_to_format(
        elements: List[Element],
        output_format: str,
        **kwargs
    ) -> str:
        """
        Convert elements to specified format
        
        Args:
            elements: List of elements to convert
            output_format: Target format ('json', 'xml', 'csv', 'txt')
            **kwargs: Format-specific options
            
        Returns:
            String in specified format
            
        Raises:
            ValueError: If format is not supported
        """
        if output_format not in UniversalConverter.FORMAT_CONVERTERS:
            raise ValueError(f"Unsupported format: {output_format}")
        
        converter = UniversalConverter.FORMAT_CONVERTERS[output_format]
        
        if output_format == 'json':
            return converter.elements_to_json(elements, **kwargs)
        elif output_format == 'xml':
            return converter.elements_to_xml(elements, **kwargs)
        elif output_format == 'csv':
            return converter.elements_to_csv(elements, **kwargs)
        elif output_format == 'txt':
            return converter.elements_to_text(elements, **kwargs)
        
        raise ValueError(f"Conversion not implemented for format: {output_format}")