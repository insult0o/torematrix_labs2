"""
Web Handler for Agent 4 - HTML and XML processing.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Any, Optional, Dict, Tuple

logger = logging.getLogger(__name__)


@dataclass
class WebFeatures:
    """Features detected in web documents."""
    document_type: str = "html"  # html, xml, xhtml
    has_scripts: bool = False
    has_styles: bool = False
    has_forms: bool = False
    has_tables: bool = False
    has_images: bool = False
    has_links: bool = False
    has_metadata: bool = False
    encoding: str = "utf-8"
    title: Optional[str] = None
    language: Optional[str] = None
    element_count: int = 0


class WebHandler:
    """HTML and XML document handler."""
    
    def __init__(self, client=None):
        self.client = client
        
    async def process(self, file_path: Path, **kwargs) -> Tuple[List[Any], WebFeatures]:
        """Process web documents with format-specific handling."""
        try:
            # Read and analyze the document
            content, features = await self._analyze_web_document(file_path)
            
            # Process based on document type
            if features.document_type == "xml":
                elements = await self._process_xml_document(content, features, **kwargs)
            elif features.document_type == "xhtml":
                elements = await self._process_xhtml_document(content, features, **kwargs)
            else:  # HTML
                elements = await self._process_html_document(content, features, **kwargs)
            
            logger.info(f"Web document processed: {features.document_type}, {len(elements)} elements")
            return elements, features
            
        except Exception as e:
            logger.error(f"Web processing failed for {file_path}: {e}")
            return [self._create_fallback_element(file_path, str(e))], WebFeatures()
    
    async def _analyze_web_document(self, file_path: Path) -> Tuple[str, WebFeatures]:
        """Analyze web document to detect features."""
        features = WebFeatures()
        
        try:
            # Read content with encoding detection
            content = await self._read_with_encoding_detection(file_path)
            
            # Detect document type
            features.document_type = self._detect_web_type(file_path, content)
            
            # Analyze features
            features = self._analyze_web_features(content, features)
            
            return content, features
            
        except Exception as e:
            logger.warning(f"Web document analysis failed: {e}")
            return "", WebFeatures()
    
    async def _read_with_encoding_detection(self, file_path: Path) -> str:
        """Read file with encoding detection."""
        # Try common web encodings
        encodings = ['utf-8', 'iso-8859-1', 'cp1252', 'utf-16']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
                
        # Fallback
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            return raw_data.decode('utf-8', errors='replace')
    
    def _detect_web_type(self, file_path: Path, content: str) -> str:
        """Detect web document type."""
        suffix = file_path.suffix.lower()
        
        if suffix == '.xml':
            return "xml"
        elif suffix == '.xhtml':
            return "xhtml"
        elif suffix in ['.html', '.htm']:
            return "html"
        
        # Content-based detection
        content_lower = content.lower()
        
        if '<?xml' in content_lower and 'xhtml' in content_lower:
            return "xhtml"
        elif '<?xml' in content_lower:
            return "xml"
        elif '<html' in content_lower or '<!doctype html' in content_lower:
            return "html"
        
        return "html"  # Default
    
    def _analyze_web_features(self, content: str, features: WebFeatures) -> WebFeatures:
        """Analyze web document features."""
        content_lower = content.lower()
        
        # Basic feature detection
        features.has_scripts = '<script' in content_lower
        features.has_styles = '<style' in content_lower or 'css' in content_lower
        features.has_forms = '<form' in content_lower
        features.has_tables = '<table' in content_lower
        features.has_images = '<img' in content_lower
        features.has_links = '<a ' in content_lower and 'href' in content_lower
        features.has_metadata = '<meta' in content_lower
        
        # Extract title
        title_match = re.search(r'<title[^>]*>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
        if title_match:
            features.title = title_match.group(1).strip()
        
        # Extract language
        lang_match = re.search(r'<html[^>]*lang=["\']([^"\']+)["\']', content, re.IGNORECASE)
        if lang_match:
            features.language = lang_match.group(1)
        
        # Count elements (rough estimate)
        features.element_count = content.count('<') - content.count('<!--')
        
        # Extract encoding from meta tags
        encoding_match = re.search(r'charset=["\']?([^"\'\s>]+)', content, re.IGNORECASE)
        if encoding_match:
            features.encoding = encoding_match.group(1).lower()
        
        return features
    
    async def _process_html_document(self, content: str, features: WebFeatures, **kwargs) -> List[Any]:
        """Process HTML documents."""
        if self.client:
            # Use client if available - create temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
                f.write(content)
                temp_path = Path(f.name)
            
            try:
                return await self.client.parse_document(temp_path, **kwargs)
            finally:
                temp_path.unlink()
        else:
            # Fallback HTML processing
            elements = []
            
            if features.title:
                elements.append(self._create_element("Title", features.title))
            
            # Extract text content (simplified)
            text_content = self._extract_text_content(content)
            
            # Process different HTML elements
            elements.extend(self._extract_headers(content))
            elements.extend(self._extract_paragraphs(text_content))
            
            if features.has_tables:
                elements.extend(self._extract_tables(content))
                
            if features.has_links:
                elements.extend(self._extract_links(content))
                
            if features.has_images:
                elements.extend(self._extract_images(content))
                
            if features.has_forms:
                elements.extend(self._extract_forms(content))
                
            return elements
    
    async def _process_xml_document(self, content: str, features: WebFeatures, **kwargs) -> List[Any]:
        """Process XML documents."""
        if self.client:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
                f.write(content)
                temp_path = Path(f.name)
            
            try:
                return await self.client.parse_document(temp_path, **kwargs)
            finally:
                temp_path.unlink()
        else:
            # Fallback XML processing
            elements = []
            
            # Extract XML structure (simplified)
            root_match = re.search(r'<(\w+)[^>]*>', content)
            if root_match:
                elements.append(self._create_element("XMLRoot", f"Root element: {root_match.group(1)}"))
            
            # Extract text nodes
            text_nodes = re.findall(r'>([^<]+)<', content)
            for text in text_nodes:
                text = text.strip()
                if text and not text.startswith('<?'):
                    elements.append(self._create_element("XMLText", text))
                    
            # Extract attributes
            attributes = re.findall(r'(\w+)=["\']([^"\']+)["\']', content)
            for attr_name, attr_value in attributes[:5]:  # Limit for demo
                elements.append(self._create_element("XMLAttribute", f"{attr_name}={attr_value}"))
                
            return elements
    
    async def _process_xhtml_document(self, content: str, features: WebFeatures, **kwargs) -> List[Any]:
        """Process XHTML documents."""
        # XHTML is stricter HTML, process similar to HTML
        return await self._process_html_document(content, features, **kwargs)
    
    def _extract_text_content(self, html: str) -> str:
        """Extract text content from HTML (simplified)."""
        # Remove scripts and styles
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.IGNORECASE | re.DOTALL)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.IGNORECASE | re.DOTALL)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _extract_headers(self, html: str) -> List[Any]:
        """Extract header elements."""
        elements = []
        
        for level in range(1, 7):  # h1 to h6
            headers = re.findall(f'<h{level}[^>]*>(.*?)</h{level}>', html, re.IGNORECASE | re.DOTALL)
            for header in headers:
                header_text = re.sub(r'<[^>]+>', '', header).strip()
                if header_text:
                    elements.append(self._create_element(f"Header{level}", header_text))
                    
        return elements
    
    def _extract_paragraphs(self, text: str) -> List[Any]:
        """Extract paragraph-like content."""
        sentences = text.split('. ')
        elements = []
        
        for sentence in sentences[:10]:  # Limit for demo
            sentence = sentence.strip()
            if len(sentence) > 20:  # Only meaningful sentences
                elements.append(self._create_element("NarrativeText", sentence))
                
        return elements
    
    def _extract_tables(self, html: str) -> List[Any]:
        """Extract table elements."""
        elements = []
        
        # Find tables
        tables = re.findall(r'<table[^>]*>(.*?)</table>', html, re.IGNORECASE | re.DOTALL)
        
        for i, table in enumerate(tables[:3]):  # Limit for demo
            elements.append(self._create_element("Table", f"Table {i+1}"))
            
            # Extract cells
            cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', table, re.IGNORECASE | re.DOTALL)
            for cell in cells[:5]:  # Limit cells
                cell_text = re.sub(r'<[^>]+>', '', cell).strip()
                if cell_text:
                    elements.append(self._create_element("TableCell", cell_text))
                    
        return elements
    
    def _extract_links(self, html: str) -> List[Any]:
        """Extract link elements."""
        elements = []
        
        links = re.findall(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.IGNORECASE | re.DOTALL)
        
        for href, link_text in links[:10]:  # Limit for demo
            link_text = re.sub(r'<[^>]+>', '', link_text).strip()
            if link_text:
                elements.append(self._create_element("Link", f"{link_text} ({href})"))
                
        return elements
    
    def _extract_images(self, html: str) -> List[Any]:
        """Extract image elements."""
        elements = []
        
        images = re.findall(r'<img[^>]*src=["\']([^"\']+)["\'][^>]*(?:alt=["\']([^"\']*)["\'])?', html, re.IGNORECASE)
        
        for src, alt in images[:5]:  # Limit for demo
            alt_text = alt if alt else f"Image: {src}"
            elements.append(self._create_element("Image", alt_text))
            
        return elements
    
    def _extract_forms(self, html: str) -> List[Any]:
        """Extract form elements."""
        elements = []
        
        forms = re.findall(r'<form[^>]*>(.*?)</form>', html, re.IGNORECASE | re.DOTALL)
        
        for i, form in enumerate(forms[:3]):  # Limit for demo
            elements.append(self._create_element("Form", f"Form {i+1}"))
            
            # Extract input fields
            inputs = re.findall(r'<input[^>]*name=["\']([^"\']+)["\']', form, re.IGNORECASE)
            for input_name in inputs[:5]:  # Limit inputs
                elements.append(self._create_element("FormField", f"Input: {input_name}"))
                
        return elements
    
    def _create_element(self, element_type: str, text: str) -> Any:
        """Create a mock element for fallback processing."""
        from unittest.mock import Mock
        element = Mock()
        element.category = element_type
        element.text = text
        element.metadata = {"agent": "Agent 4 Web Handler"}
        return element
    
    def _create_fallback_element(self, file_path: Path, error: str) -> Any:
        """Create fallback element when processing fails."""
        return self._create_element("Error", f"Web processing failed for {file_path.name}: {error}")