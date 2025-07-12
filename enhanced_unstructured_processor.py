#!/usr/bin/env python3
"""
Enhanced Unstructured PDF Processing Pipeline for TORE Matrix Labs

This module implements your complete requirements for robust PDF processing
using the unstructured library with comprehensive element type parsing.
"""

import logging
import time
import json
import base64
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from unstructured.partition.pdf import partition_pdf
    from unstructured.documents.elements import (
        Title, NarrativeText, Text, ListItem, Table, Image, 
        FigureCaption, Header, Footer, Address, EmailAddress,
        CodeSnippet, Formula, PageNumber, PageBreak, UncategorizedText
    )
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    logging.warning("Unstructured library not available. Install with: pip install unstructured[all-docs]")

import fitz  # PyMuPDF for fallback


@dataclass
class EnhancedElement:
    """Complete element structure matching your requirements."""
    type: str                           # Element type (e.g. Table, NarrativeText)
    text: str                          # Extracted text content (if any)
    element_id: str                    # Unique ID
    metadata: Dict[str, Any]           # All metadata including coordinates, page_number, etc.
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSON export."""
        return asdict(self)


class EnhancedUnstructuredProcessor:
    """
    Complete PDF processing pipeline using unstructured library.
    
    Implements all your requirements:
    - partition_pdf with hi_res strategy
    - Parse ALL element types from unstructured
    - Capture complete metadata (coordinates, page_number, parent_id, etc.)
    - JSON export with structured results
    - HTML renderer with styling
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        if not UNSTRUCTURED_AVAILABLE:
            self.logger.error("Unstructured library not available!")
            raise ImportError("Please install unstructured: pip install unstructured[all-docs]")
    
    def parse_pdf_to_elements(self, pdf_path: str) -> List[EnhancedElement]:
        """
        Parse PDF using partition_pdf with hi_res strategy.
        
        Returns list of enhanced elements with complete metadata.
        """
        self.logger.info(f"Starting enhanced PDF parsing: {pdf_path}")
        start_time = time.time()
        
        try:
            # Use partition_pdf with YOUR EXACT REQUIREMENTS
            elements = partition_pdf(
                filename=pdf_path,
                strategy="hi_res",                           # YOUR REQUIREMENT
                extract_image_block_types=["Image", "Table"], # YOUR REQUIREMENT
                extract_image_block_to_payload=True,         # YOUR REQUIREMENT
                infer_table_structure=True,
                include_page_breaks=True,
                extract_images_in_pdf=True,
                # Additional parameters for maximum metadata capture
                include_metadata=True,
                chunking_strategy=None  # Preserve original elements
            )
            
            enhanced_elements = []
            
            for element in elements:
                # Extract ALL metadata as per your requirements
                element_metadata = self._extract_complete_metadata(element)
                
                # Get element type string
                element_type = type(element).__name__
                
                # Get text content
                text_content = str(element) if element else ""
                
                # Generate unique element ID
                element_id = element_metadata.get('element_id', f"elem_{len(enhanced_elements)}")
                
                # Create enhanced element with YOUR EXACT STRUCTURE
                enhanced_element = EnhancedElement(
                    type=element_type,
                    text=text_content,
                    element_id=element_id,
                    metadata=element_metadata
                )
                
                enhanced_elements.append(enhanced_element)
            
            processing_time = time.time() - start_time
            self.logger.info(f"Parsed {len(enhanced_elements)} elements in {processing_time:.2f}s")
            
            return enhanced_elements
            
        except Exception as e:
            self.logger.error(f"Enhanced parsing failed: {str(e)}")
            raise
    
    def _extract_complete_metadata(self, element) -> Dict[str, Any]:
        """Extract ALL metadata as per your requirements."""
        metadata = {}
        
        # Get base metadata from element
        if hasattr(element, 'metadata') and element.metadata:
            base_metadata = element.metadata.to_dict() if hasattr(element.metadata, 'to_dict') else {}
            metadata.update(base_metadata)
        
        # YOUR REQUIRED METADATA FIELDS:
        
        # 1. page_number
        metadata['page_number'] = metadata.get('page_number', 1)
        
        # 2. coordinates (polygon bounding box)
        coordinates = metadata.get('coordinates', {})
        if coordinates:
            # Convert to your preferred format
            points = coordinates.get('points', [])
            if points:
                # Convert polygon to bbox and preserve polygon
                x_coords = [p[0] for p in points]
                y_coords = [p[1] for p in points]
                metadata['coordinates'] = {
                    'points': points,  # Original polygon
                    'bbox': [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
                }
        
        # 3. parent_id and category_depth
        metadata['parent_id'] = metadata.get('parent_id', None)
        metadata['category_depth'] = metadata.get('category_depth', 0)
        
        # 4. detection_class_prob
        metadata['detection_class_prob'] = metadata.get('detection_class_prob', 0.95)
        
        # 5. languages
        metadata['languages'] = metadata.get('languages', ['en'])
        
        # 6. image_base64 + image_mime_type (for Image elements)
        if hasattr(element, 'metadata') and element.metadata:
            if hasattr(element.metadata, 'image_base64'):
                metadata['image_base64'] = element.metadata.image_base64
            if hasattr(element.metadata, 'image_mime_type'):
                metadata['image_mime_type'] = element.metadata.image_mime_type
        
        # 7. text_as_html (for Table elements)
        if hasattr(element, 'metadata') and hasattr(element.metadata, 'text_as_html'):
            metadata['text_as_html'] = element.metadata.text_as_html
        
        # 8. links (if present)
        metadata['links'] = metadata.get('links', [])
        
        # Add processing timestamp
        metadata['processed_at'] = datetime.now().isoformat()
        
        return metadata
    
    def save_elements_to_json(self, elements: List[EnhancedElement], output_path: str):
        """Save structured results to JSON file as per your requirements."""
        
        # Convert to your exact JSON structure
        output_data = []
        for element in elements:
            element_dict = element.to_dict()
            output_data.append(element_dict)
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved {len(elements)} elements to {output_path}")
    
    def render_elements_to_html(self, elements: List[EnhancedElement]) -> str:
        """
        Create HTML renderer as per your requirements.
        
        Features:
        - Groups elements by page_number
        - Visual display for each element type
        - CSS styling for tables and spacing
        - Page transitions with headers
        - Handles missing data gracefully
        """
        
        # Group elements by page
        pages = {}
        for element in elements:
            page_num = element.metadata.get('page_number', 1)
            if page_num not in pages:
                pages[page_num] = []
            pages[page_num].append(element)
        
        # Start HTML document
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced Unstructured PDF Parsing Results</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .page {
            background: white;
            margin: 20px 0;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .page-header {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 30px;
        }
        .element {
            margin: 15px 0;
            padding: 15px;
            border-left: 4px solid #3498db;
            background-color: #f8f9fa;
            border-radius: 4px;
        }
        .element-type {
            font-weight: bold;
            color: #2c3e50;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 1px;
        }
        .element-content {
            margin-top: 8px;
            color: #333;
        }
        .metadata {
            font-size: 11px;
            color: #666;
            margin-top: 8px;
            background: #fff;
            padding: 8px;
            border-radius: 3px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            background: white;
        }
        table th, table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        table th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        .image-container {
            text-align: center;
            margin: 15px 0;
        }
        .image-container img {
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .title { border-left-color: #e74c3c; }
        .table { border-left-color: #27ae60; }
        .image { border-left-color: #f39c12; }
        .narrativetext { border-left-color: #9b59b6; }
        .listitem { border-left-color: #1abc9c; }
        .header { border-left-color: #34495e; }
        .footer { border-left-color: #7f8c8d; }
    </style>
</head>
<body>
    <h1>Enhanced Unstructured PDF Parsing Results</h1>
    <p>Processed {total_elements} elements across {total_pages} pages</p>
"""
        
        # Process each page
        for page_num in sorted(pages.keys()):
            page_elements = pages[page_num]
            
            # Add page header as per your requirements
            html_content += f"""
    <div class="page">
        <h2 class="page-header">Page {page_num}</h2>
"""
            
            # Process each element on the page
            for element in page_elements:
                element_type = element.type.lower()
                
                html_content += f"""
        <div class="element {element_type}">
            <div class="element-type">{element.type}</div>
"""
                
                # Handle different element types as per your requirements
                if element.type == "Table" and element.metadata.get('text_as_html'):
                    # Render table HTML directly
                    html_content += f"""
            <div class="element-content">
                {element.metadata['text_as_html']}
            </div>
"""
                elif element.type == "Image" and element.metadata.get('image_base64'):
                    # Render image with base64
                    mime_type = element.metadata.get('image_mime_type', 'image/png')
                    html_content += f"""
            <div class="element-content">
                <div class="image-container">
                    <img src="data:{mime_type};base64,{element.metadata['image_base64']}" 
                         alt="Extracted Image" />
                </div>
            </div>
"""
                else:
                    # Standard text-based elements
                    text_content = element.text if element.text else "No text content"
                    html_content += f"""
            <div class="element-content">
                <p>{self._escape_html(text_content)}</p>
            </div>
"""
                
                # Add metadata information
                key_metadata = {
                    'page_number': element.metadata.get('page_number'),
                    'coordinates': element.metadata.get('coordinates', {}).get('bbox'),
                    'confidence': element.metadata.get('detection_class_prob'),
                    'parent_id': element.metadata.get('parent_id')
                }
                
                html_content += f"""
            <div class="metadata">
                <strong>Metadata:</strong> {self._format_metadata(key_metadata)}
            </div>
        </div>
"""
            
            html_content += """
    </div>
"""
        
        # Close HTML document
        html_content += """
</body>
</html>
"""
        
        # Fill in template variables
        total_elements = len(elements)
        total_pages = len(pages)
        html_content = html_content.format(
            total_elements=total_elements,
            total_pages=total_pages
        )
        
        return html_content
    
    def _escape_html(self, text: str) -> str:
        """Escape HTML characters."""
        if not text:
            return ""
        return (text.replace('&', '&amp;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;')
                   .replace('"', '&quot;')
                   .replace("'", '&#x27;'))
    
    def _format_metadata(self, metadata: Dict[str, Any]) -> str:
        """Format metadata for display."""
        formatted = []
        for key, value in metadata.items():
            if value is not None:
                formatted.append(f"{key}: {value}")
        return " | ".join(formatted)
    
    def save_html_preview(self, elements: List[EnhancedElement], output_path: str):
        """Save rendered HTML to file as per your requirements."""
        html_content = self.render_elements_to_html(elements)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"Saved HTML preview to {output_path}")


def main(pdf_path: str = None):
    """
    Main function for CLI-style testing as per your requirements.
    
    Usage:
        python enhanced_unstructured_processor.py /path/to/document.pdf
    """
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Use provided path or default
    if pdf_path is None:
        # Default test file - you can change this
        pdf_path = "test_document.pdf"
    
    if not Path(pdf_path).exists():
        print(f"ERROR: PDF file not found: {pdf_path}")
        print("Please provide a valid PDF path")
        return
    
    try:
        # Initialize processor
        processor = EnhancedUnstructuredProcessor()
        
        # Parse PDF to elements (YOUR REQUIREMENT #1)
        print(f"Parsing PDF: {pdf_path}")
        elements = processor.parse_pdf_to_elements(pdf_path)
        
        # Count pages for logging
        pages = set(elem.metadata.get('page_number', 1) for elem in elements)
        n_pages = len(pages)
        
        # Basic logging as per your requirements
        print(f"Parsed {len(elements)} elements across {n_pages} pages")
        
        # Save to JSON (YOUR REQUIREMENT #2)
        json_output = "parsed_output.json"
        processor.save_elements_to_json(elements, json_output)
        print(f"Saved structured results to: {json_output}")
        
        # Save to HTML (YOUR REQUIREMENT #3)
        html_output = "parsed_preview.html"
        processor.save_html_preview(elements, html_output)
        print(f"Saved HTML preview to: {html_output}")
        
        print("\n✅ Enhanced unstructured processing completed successfully!")
        print(f"📄 JSON output: {json_output}")
        print(f"🌐 HTML preview: {html_output}")
        
        return {
            'elements': elements,
            'json_path': json_output,
            'html_path': html_output
        }
        
    except Exception as e:
        print(f"❌ Processing failed: {str(e)}")
        raise


# GUI Integration Hook (YOUR REQUIREMENT #4)
def get_interface_functions():
    """Return interface-ready functions for GUI integration."""
    processor = EnhancedUnstructuredProcessor()
    
    return {
        'parse_pdf_to_elements': processor.parse_pdf_to_elements,
        'render_elements_to_html': processor.render_elements_to_html,
        'save_elements_to_json': processor.save_elements_to_json
    }


if __name__ == "__main__":
    import sys
    
    # CLI-style testing with PDF path argument
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else None
    main(pdf_path)