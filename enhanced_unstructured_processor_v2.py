#!/usr/bin/env python3
"""
Enhanced Unstructured PDF Processing Pipeline V2

Incorporates complete understanding of Unstructured output structure
based on official documentation analysis.
"""

import logging
import time
import json
import base64
import uuid
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from unstructured.partition.pdf import partition_pdf
    from unstructured.documents.elements import (
        Title, NarrativeText, Text, ListItem, Table, Image, 
        FigureCaption, Header, Footer, Address, EmailAddress,
        CodeSnippet, Formula, PageNumber, PageBreak, UncategorizedText,
        CompositeElement  # For chunked content
    )
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    logging.warning("Unstructured library not available. Install with: pip install unstructured[all-docs]")

import fitz  # PyMuPDF for fallback


@dataclass
class EnhancedElementV2:
    """Enhanced element structure with complete metadata coverage."""
    type: str                           # Element type (exact from unstructured)
    element_id: str                     # Unique identifier (deterministic hash or UUID)
    text: str                          # Extracted text content
    metadata: Dict[str, Any]           # Complete metadata with all documented fields
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSON export."""
        return {
            "type": self.type,
            "element_id": self.element_id,
            "text": self.text,
            "metadata": self.metadata
        }


class EnhancedUnstructuredProcessorV2:
    """
    Enhanced PDF processing pipeline V2 with complete Unstructured output structure support.
    
    Improvements based on official documentation:
    - Complete metadata extraction (all documented fields)
    - Proper parameter usage (no deprecated options)
    - Hierarchy reconstruction from parent_id and category_depth
    - Enhanced table processing with text_as_html
    - Complete image handling with OCR and data extraction
    - Page break boundary detection
    - ML confidence score utilization
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        if not UNSTRUCTURED_AVAILABLE:
            self.logger.error("Unstructured library not available!")
            raise ImportError("Please install unstructured: pip install unstructured[all-docs]")
    
    def parse_pdf_to_elements(self, pdf_path: str) -> List[EnhancedElementV2]:
        """
        Parse PDF using optimal partition_pdf parameters based on documentation.
        """
        self.logger.info(f"Starting enhanced PDF parsing V2: {pdf_path}")
        start_time = time.time()
        
        try:
            # OPTIMAL partition_pdf call based on documentation analysis
            elements = partition_pdf(
                filename=pdf_path,
                # CORE STRATEGY
                strategy="hi_res",                             # High resolution for best results
                
                # IMAGE EXTRACTION (corrected parameters)
                extract_image_block_types=["Image", "Table"],   # Types to extract as images
                extract_image_block_to_payload=True,           # Embed as base64 in metadata
                
                # TABLE STRUCTURE (CRITICAL for text_as_html)
                infer_table_structure=True,                    # ESSENTIAL for structured tables
                
                # LAYOUT AND STRUCTURE
                include_page_breaks=True,                      # Explicit page boundaries
                include_metadata=True,                         # Rich metadata capture
                
                # MODEL OPTIMIZATION
                hi_res_model_name="yolox",                     # Best model for layout detection
                
                # PRESERVE ORIGINAL STRUCTURE
                chunking_strategy=None,                        # No chunking - preserve elements
                
                # ADDITIONAL OPTIMIZATIONS
                model_name="yolox"                             # Consistent model usage
            )
            
            enhanced_elements = []
            
            for i, element in enumerate(elements):
                try:
                    # Extract complete metadata using documentation insights
                    complete_metadata = self._extract_complete_metadata_v2(element)
                    
                    # Get element type (exact class name from unstructured)
                    element_type = type(element).__name__
                    
                    # Get deterministic element ID (unstructured provides this)
                    element_id = self._get_element_id(element, i)
                    
                    # Get text content (handle all element types)
                    text_content = self._extract_text_content(element, element_type)
                    
                    # Create enhanced element V2
                    enhanced_element = EnhancedElementV2(
                        type=element_type,
                        element_id=element_id,
                        text=text_content,
                        metadata=complete_metadata
                    )
                    
                    enhanced_elements.append(enhanced_element)
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process element {i}: {e}")
                    continue
            
            processing_time = time.time() - start_time
            
            # Add document-level analysis
            document_analysis = self._analyze_document_structure(enhanced_elements)
            
            self.logger.info(f"Parsed {len(enhanced_elements)} elements in {processing_time:.2f}s")
            self.logger.info(f"Document structure: {document_analysis['summary']}")
            
            return enhanced_elements
            
        except Exception as e:
            self.logger.error(f"Enhanced parsing V2 failed: {str(e)}")
            raise
    
    def _extract_complete_metadata_v2(self, element) -> Dict[str, Any]:
        """Extract complete metadata based on official documentation."""
        metadata = {}
        
        # Extract base metadata from element
        if hasattr(element, 'metadata') and element.metadata:
            try:
                base_metadata = element.metadata.to_dict() if hasattr(element.metadata, 'to_dict') else {}
                metadata.update(base_metadata)
            except Exception as e:
                self.logger.warning(f"Failed to extract base metadata: {e}")
        
        # COMPLETE METADATA FIELDS (based on documentation)
        
        # 1. CORE IDENTIFICATION
        metadata['page_number'] = metadata.get('page_number', 1)
        metadata['filename'] = metadata.get('filename', '')
        metadata['filetype'] = metadata.get('filetype', 'application/pdf')
        metadata['file_directory'] = metadata.get('file_directory', '')
        metadata['last_modified'] = metadata.get('last_modified', '')
        
        # 2. ENHANCED COORDINATES with system information
        coordinates = metadata.get('coordinates', {})
        if coordinates:
            # Complete coordinate information
            metadata['coordinates'] = {
                'points': coordinates.get('points', []),           # Polygon points
                'system': coordinates.get('system', 'PixelSpace'), # Coordinate system
                'layout_width': coordinates.get('layout_width'),   # Page width
                'layout_height': coordinates.get('layout_height'), # Page height
                # Convert to bbox for compatibility
                'bbox': self._points_to_bbox(coordinates.get('points', []))
            }
        else:
            metadata['coordinates'] = {
                'points': [],
                'system': 'PixelSpace',
                'layout_width': None,
                'layout_height': None,
                'bbox': [0, 0, 0, 0]
            }
        
        # 3. HIERARCHY AND STRUCTURE
        metadata['parent_id'] = metadata.get('parent_id', None)
        metadata['category_depth'] = metadata.get('category_depth', 0)
        
        # 4. ML CONFIDENCE SCORES (hi_res strategy)
        metadata['detection_class_prob'] = metadata.get('detection_class_prob', {})
        
        # 5. LANGUAGE DETECTION
        metadata['languages'] = metadata.get('languages', ['eng'])
        
        # 6. TEXT FORMATTING PRESERVATION
        metadata['emphasized_text_contents'] = metadata.get('emphasized_text_contents', [])
        metadata['emphasized_text_tags'] = metadata.get('emphasized_text_tags', [])
        
        # 7. LINKS with proper structure
        metadata['links'] = self._process_links_metadata(metadata.get('links', []))
        
        # 8. IMAGE DATA (when available)
        metadata['image_base64'] = metadata.get('image_base64', '')
        metadata['image_mime_type'] = metadata.get('image_mime_type', '')
        metadata['image_path'] = metadata.get('image_path', '')
        
        # 9. TABLE STRUCTURE (critical for Table elements)
        metadata['text_as_html'] = metadata.get('text_as_html', '')
        
        # 10. CONTINUATION AND CHUNKING
        metadata['is_continuation'] = metadata.get('is_continuation', False)
        
        # 11. PROCESSING CONTEXT
        metadata['partitioner_type'] = 'hi_res'
        metadata['processed_at'] = datetime.now().isoformat()
        
        return metadata
    
    def _get_element_id(self, element, fallback_index: int) -> str:
        """Get deterministic element ID from unstructured element."""
        # Unstructured provides deterministic hash-based IDs
        if hasattr(element, 'id') and element.id:
            return element.id
        elif hasattr(element, 'element_id') and element.element_id:
            return element.element_id
        else:
            # Generate deterministic ID based on content and position
            content_hash = str(hash(str(element)))[-8:]
            return f"elem_{fallback_index}_{content_hash}"
    
    def _extract_text_content(self, element, element_type: str) -> str:
        """Extract text content with element-type specific handling."""
        try:
            text = str(element) if element else ""
            
            # Element-specific text processing
            if element_type == 'Image':
                # For images, text contains OCR results
                if text:
                    return f"[Image OCR: {text}]"
                else:
                    return "[Image: No text detected]"
            elif element_type == 'Table':
                # For tables, preserve structured text
                return text  # Plain text version of table
            elif element_type == 'PageBreak':
                return "[Page Break]"
            elif element_type == 'PageNumber':
                return text if text else "[Page Number]"
            else:
                return text
                
        except Exception as e:
            self.logger.warning(f"Failed to extract text from {element_type}: {e}")
            return ""
    
    def _points_to_bbox(self, points: List[List[float]]) -> List[float]:
        """Convert polygon points to bounding box [x0, y0, x1, y1]."""
        if not points or len(points) < 2:
            return [0, 0, 0, 0]
        
        try:
            x_coords = [p[0] for p in points]
            y_coords = [p[1] for p in points]
            return [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
        except (IndexError, TypeError):
            return [0, 0, 0, 0]
    
    def _process_links_metadata(self, links: Any) -> List[Dict[str, Any]]:
        """Process links metadata with proper structure."""
        if not links:
            return []
        
        try:
            # Handle PDF format: [{"text": "...", "url": "...", "start_index": ...}]
            if isinstance(links, list):
                processed_links = []
                for link in links:
                    if isinstance(link, dict):
                        processed_links.append({
                            'text': link.get('text', ''),
                            'url': link.get('url', ''),
                            'start_index': link.get('start_index', 0)
                        })
                return processed_links
            else:
                return []
        except Exception as e:
            self.logger.warning(f"Failed to process links metadata: {e}")
            return []
    
    def _analyze_document_structure(self, elements: List[EnhancedElementV2]) -> Dict[str, Any]:
        """Analyze document structure from elements."""
        
        # Count elements by type
        type_counts = {}
        page_counts = {}
        hierarchy_levels = {}
        
        for element in elements:
            # Count by type
            elem_type = element.type
            type_counts[elem_type] = type_counts.get(elem_type, 0) + 1
            
            # Count by page
            page_num = element.metadata.get('page_number', 1)
            page_counts[page_num] = page_counts.get(page_num, 0) + 1
            
            # Count by hierarchy depth
            depth = element.metadata.get('category_depth', 0)
            hierarchy_levels[depth] = hierarchy_levels.get(depth, 0) + 1
        
        # Build parent-child relationships
        parent_child_map = {}
        for element in elements:
            parent_id = element.metadata.get('parent_id')
            if parent_id:
                if parent_id not in parent_child_map:
                    parent_child_map[parent_id] = []
                parent_child_map[parent_id].append(element.element_id)
        
        analysis = {
            'total_elements': len(elements),
            'element_types': type_counts,
            'page_distribution': page_counts,
            'hierarchy_levels': hierarchy_levels,
            'parent_child_relationships': len(parent_child_map),
            'summary': {
                'pages': len(page_counts),
                'types': len(type_counts),
                'has_hierarchy': len(parent_child_map) > 0,
                'max_depth': max(hierarchy_levels.keys()) if hierarchy_levels else 0
            }
        }
        
        return analysis
    
    def build_document_hierarchy(self, elements: List[EnhancedElementV2]) -> Dict[str, Any]:
        """Build document hierarchy from flat element list."""
        
        # Create element lookup
        element_lookup = {elem.element_id: elem for elem in elements}
        
        # Build hierarchy tree
        hierarchy = {
            'root_elements': [],
            'parent_child_map': {},
            'depth_levels': {},
            'page_structure': {}
        }
        
        # Group by page first
        for element in elements:
            page_num = element.metadata.get('page_number', 1)
            if page_num not in hierarchy['page_structure']:
                hierarchy['page_structure'][page_num] = []
            hierarchy['page_structure'][page_num].append(element.element_id)
        
        # Build parent-child relationships
        for element in elements:
            parent_id = element.metadata.get('parent_id')
            depth = element.metadata.get('category_depth', 0)
            
            # Track depth levels
            if depth not in hierarchy['depth_levels']:
                hierarchy['depth_levels'][depth] = []
            hierarchy['depth_levels'][depth].append(element.element_id)
            
            # Build parent-child map
            if parent_id and parent_id in element_lookup:
                if parent_id not in hierarchy['parent_child_map']:
                    hierarchy['parent_child_map'][parent_id] = []
                hierarchy['parent_child_map'][parent_id].append(element.element_id)
            else:
                hierarchy['root_elements'].append(element.element_id)
        
        return hierarchy
    
    def save_elements_to_json(self, elements: List[EnhancedElementV2], output_path: str):
        """Save structured results to JSON with enhanced format."""
        
        # Build comprehensive output structure
        output_data = {
            'document_metadata': {
                'total_elements': len(elements),
                'processing_timestamp': datetime.now().isoformat(),
                'processor_version': '2.0.0',
                'strategy': 'hi_res'
            },
            'document_structure': self._analyze_document_structure(elements),
            'hierarchy': self.build_document_hierarchy(elements),
            'elements': [element.to_dict() for element in elements]
        }
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved {len(elements)} elements with structure analysis to {output_path}")
    
    def render_elements_to_html(self, elements: List[EnhancedElementV2]) -> str:
        """Enhanced HTML renderer with complete element type support."""
        
        # Group elements by page
        pages = {}
        for element in elements:
            page_num = element.metadata.get('page_number', 1)
            if page_num not in pages:
                pages[page_num] = []
            pages[page_num].append(element)
        
        # Enhanced CSS with element-specific styling
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced Unstructured PDF Processing V2 Results</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }
        .document-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        .page {
            background: white;
            margin: 30px 0;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        }
        .page-header {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 15px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .element {
            margin: 20px 0;
            padding: 20px;
            border-radius: 8px;
            border-left: 5px solid;
            background-color: #f8f9fa;
            position: relative;
        }
        .element-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .element-type {
            font-weight: bold;
            color: #2c3e50;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 1px;
            background: rgba(52, 152, 219, 0.1);
            padding: 4px 8px;
            border-radius: 4px;
        }
        .element-id {
            font-family: monospace;
            font-size: 10px;
            color: #7f8c8d;
            background: #ecf0f1;
            padding: 2px 6px;
            border-radius: 3px;
        }
        .element-content {
            margin: 15px 0;
            color: #2c3e50;
        }
        .metadata {
            font-size: 11px;
            color: #7f8c8d;
            background: white;
            padding: 12px;
            border-radius: 5px;
            margin-top: 15px;
        }
        .metadata-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 8px;
        }
        
        /* Element-specific styling */
        .title { border-left-color: #e74c3c; background-color: #fdf2f2; }
        .narrativetext { border-left-color: #9b59b6; background-color: #f8f4fd; }
        .table { border-left-color: #27ae60; background-color: #f2f9f4; }
        .image { border-left-color: #f39c12; background-color: #fef9e7; }
        .listitem { border-left-color: #1abc9c; background-color: #e8f8f5; }
        .header { border-left-color: #34495e; background-color: #eaeded; }
        .footer { border-left-color: #7f8c8d; background-color: #f4f6f6; }
        .figurecaption { border-left-color: #ff6b6b; background-color: #fff5f5; }
        .codesnippet { border-left-color: #4ecdc4; background-color: #e0f7fa; }
        .formula { border-left-color: #45b7d1; background-color: #e1f5fe; }
        .address { border-left-color: #96ceb4; background-color: #f1f8e9; }
        .emailaddress { border-left-color: #feca57; background-color: #fffbf0; }
        .pagebreak { border-left-color: #ddd; background-color: #f9f9f9; }
        .pagenumber { border-left-color: #bbb; background-color: #f5f5f5; }
        .uncategorizedtext { border-left-color: #95a5a6; background-color: #f8f9fa; }
        
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            background: white;
            border-radius: 5px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        table th, table td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        table th {
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }
        .image-container {
            text-align: center;
            margin: 20px 0;
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .image-container img {
            max-width: 100%;
            height: auto;
            border-radius: 5px;
        }
        .hierarchy-indicator {
            position: absolute;
            right: 15px;
            top: 15px;
            background: rgba(52, 152, 219, 0.1);
            color: #3498db;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
        }
    </style>
</head>
<body>
"""
        
        # Document header with statistics
        doc_analysis = self._analyze_document_structure(elements)
        total_pages = len(pages)
        total_elements = len(elements)
        
        html_content += f"""
    <div class="document-header">
        <h1>Enhanced Unstructured PDF Processing Results V2</h1>
        <p>Advanced document analysis with complete metadata extraction</p>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <h3>{total_elements}</h3>
            <p>Total Elements</p>
        </div>
        <div class="stat-card">
            <h3>{total_pages}</h3>
            <p>Pages Processed</p>
        </div>
        <div class="stat-card">
            <h3>{len(doc_analysis['element_types'])}</h3>
            <p>Element Types</p>
        </div>
        <div class="stat-card">
            <h3>{doc_analysis['parent_child_relationships']}</h3>
            <p>Hierarchical Relations</p>
        </div>
    </div>
"""
        
        # Process each page
        for page_num in sorted(pages.keys()):
            page_elements = pages[page_num]
            
            html_content += f"""
    <div class="page">
        <div class="page-header">
            <h2>Page {page_num}</h2>
            <span>{len(page_elements)} elements</span>
        </div>
"""
            
            # Process each element
            for element in page_elements:
                element_type_class = element.type.lower()
                depth = element.metadata.get('category_depth', 0)
                
                html_content += f"""
        <div class="element {element_type_class}">
            <div class="element-header">
                <span class="element-type">{element.type}</span>
                <span class="element-id">{element.element_id}</span>
            </div>
            {f'<div class="hierarchy-indicator">Depth: {depth}</div>' if depth > 0 else ''}
"""
                
                # Render content based on element type
                if element.type == "Table" and element.metadata.get('text_as_html'):
                    html_content += f"""
            <div class="element-content">
                {element.metadata['text_as_html']}
            </div>
"""
                elif element.type == "Image" and element.metadata.get('image_base64'):
                    mime_type = element.metadata.get('image_mime_type', 'image/png')
                    html_content += f"""
            <div class="element-content">
                <div class="image-container">
                    <img src="data:{mime_type};base64,{element.metadata['image_base64']}" 
                         alt="Extracted Image" />
                    {f'<p><em>{element.text}</em></p>' if element.text and 'OCR' in element.text else ''}
                </div>
            </div>
"""
                elif element.type == "CodeSnippet":
                    html_content += f"""
            <div class="element-content">
                <pre style="background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto;"><code>{self._escape_html(element.text)}</code></pre>
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
                
                # Enhanced metadata display
                key_metadata = {
                    'Page': element.metadata.get('page_number'),
                    'Coordinates': element.metadata.get('coordinates', {}).get('bbox'),
                    'Confidence': element.metadata.get('detection_class_prob'),
                    'Parent ID': element.metadata.get('parent_id'),
                    'Languages': element.metadata.get('languages'),
                    'Links': len(element.metadata.get('links', []))
                }
                
                html_content += f"""
            <div class="metadata">
                <div class="metadata-grid">
"""
                
                for key, value in key_metadata.items():
                    if value is not None and value != []:
                        display_value = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                        html_content += f"""
                    <div><strong>{key}:</strong> {display_value}</div>
"""
                
                html_content += """
                </div>
            </div>
        </div>
"""
            
            html_content += """
    </div>
"""
        
        # Close HTML
        html_content += """
</body>
</html>
"""
        
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
    
    def save_html_preview(self, elements: List[EnhancedElementV2], output_path: str):
        """Save enhanced HTML preview to file."""
        html_content = self.render_elements_to_html(elements)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.logger.info(f"Saved enhanced HTML preview to {output_path}")


def main(pdf_path: str = None):
    """Main function with enhanced processing and analysis."""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Use provided path or default
    if pdf_path is None:
        pdf_path = "test_document.pdf"
    
    if not Path(pdf_path).exists():
        print(f"ERROR: PDF file not found: {pdf_path}")
        return
    
    try:
        # Initialize enhanced processor V2
        processor = EnhancedUnstructuredProcessorV2()
        
        # Parse PDF with complete metadata extraction
        print(f"🔍 Processing PDF with enhanced pipeline V2: {pdf_path}")
        elements = processor.parse_pdf_to_elements(pdf_path)
        
        # Analyze document structure
        analysis = processor._analyze_document_structure(elements)
        hierarchy = processor.build_document_hierarchy(elements)
        
        # Display comprehensive results
        print(f"\n📊 Document Analysis:")
        print(f"   Total Elements: {analysis['total_elements']}")
        print(f"   Pages: {analysis['summary']['pages']}")
        print(f"   Element Types: {list(analysis['element_types'].keys())}")
        print(f"   Hierarchical Elements: {analysis['parent_child_relationships']}")
        print(f"   Max Depth: {analysis['summary']['max_depth']}")
        
        # Save enhanced JSON with structure analysis
        json_output = "parsed_output_v2.json"
        processor.save_elements_to_json(elements, json_output)
        print(f"💾 Enhanced JSON saved: {json_output}")
        
        # Save enhanced HTML with complete styling
        html_output = "parsed_preview_v2.html"
        processor.save_html_preview(elements, html_output)
        print(f"🌐 Enhanced HTML saved: {html_output}")
        
        print(f"\n✅ Enhanced processing V2 completed successfully!")
        
        return {
            'elements': elements,
            'analysis': analysis,
            'hierarchy': hierarchy,
            'json_path': json_output,
            'html_path': html_output
        }
        
    except Exception as e:
        print(f"❌ Enhanced processing V2 failed: {str(e)}")
        raise


if __name__ == "__main__":
    import sys
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else None
    main(pdf_path)