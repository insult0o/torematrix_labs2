"""
Text Handler for Agent 4 - Comprehensive text format processing.
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Any, Optional, Dict, Tuple

logger = logging.getLogger(__name__)


@dataclass  
class TextFeatures:
    """Features detected in text documents."""
    document_type: str = "plain_text"  # plain_text, markdown, csv, json, etc.
    encoding: str = "utf-8"
    has_headers: bool = False
    has_links: bool = False
    has_code_blocks: bool = False
    has_tables: bool = False
    line_count: int = 0
    word_count: int = 0
    character_count: int = 0
    structure_score: float = 0.0  # How structured the document is
    

class TextHandler:
    """Comprehensive text format handler."""
    
    def __init__(self, client=None):
        self.client = client
        
    async def process(self, file_path: Path, **kwargs) -> Tuple[List[Any], TextFeatures]:
        """Process text documents with format-specific handling."""
        try:
            # Read and analyze the file
            content, features = await self._analyze_text_file(file_path)
            
            # Process based on detected type
            if features.document_type == "markdown":
                elements = await self._process_markdown(content, features, **kwargs)
            elif features.document_type == "csv":
                elements = await self._process_csv(content, features, **kwargs) 
            elif features.document_type == "json":
                elements = await self._process_json(content, features, **kwargs)
            elif features.document_type == "code":
                elements = await self._process_code(content, features, **kwargs)
            else:
                elements = await self._process_plain_text(content, features, **kwargs)
            
            logger.info(f"Text processed: {features.document_type}, {len(elements)} elements")
            return elements, features
            
        except Exception as e:
            logger.error(f"Text processing failed for {file_path}: {e}")
            return [self._create_fallback_element(file_path, str(e))], TextFeatures()
    
    async def _analyze_text_file(self, file_path: Path) -> Tuple[str, TextFeatures]:
        """Analyze text file to detect format and features."""
        features = TextFeatures()
        
        try:
            # Detect encoding and read content
            content = await self._read_with_encoding_detection(file_path)
            
            # Basic metrics
            features.character_count = len(content)
            features.line_count = content.count('\n') + 1
            features.word_count = len(content.split())
            
            # Detect document type based on extension and content
            features.document_type = self._detect_document_type(file_path, content)
            
            # Analyze structure
            features = self._analyze_structure(content, features)
            
            return content, features
            
        except Exception as e:
            logger.warning(f"Text analysis failed: {e}")
            return "", TextFeatures()
    
    async def _read_with_encoding_detection(self, file_path: Path) -> str:
        """Read file with encoding detection."""
        # Try common encodings
        encodings = ['utf-8', 'utf-16', 'latin1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
                
        # Fallback to binary mode
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            return raw_data.decode('utf-8', errors='replace')
    
    def _detect_document_type(self, file_path: Path, content: str) -> str:
        """Detect the document type based on extension and content."""
        suffix = file_path.suffix.lower()
        
        # Extension-based detection
        if suffix == '.md':
            return "markdown"
        elif suffix == '.csv':
            return "csv"
        elif suffix == '.json':
            return "json"
        elif suffix in ['.py', '.js', '.java', '.cpp', '.c', '.h']:
            return "code"
        elif suffix in ['.rst']:
            return "restructured_text"
        
        # Content-based detection
        content_lower = content.lower()
        
        if re.search(r'^#{1,6}\s', content, re.MULTILINE):  # Markdown headers
            return "markdown"
        elif content.count(',') > content.count('\n') * 2:  # Likely CSV
            return "csv"
        elif content.strip().startswith('{') and content.strip().endswith('}'):
            return "json"
        elif re.search(r'(def |class |import |function\s*\()', content):
            return "code"
        
        return "plain_text"
    
    def _analyze_structure(self, content: str, features: TextFeatures) -> TextFeatures:
        """Analyze document structure."""
        
        # Check for headers (markdown style)
        if re.search(r'^#{1,6}\s', content, re.MULTILINE):
            features.has_headers = True
            
        # Check for links
        if re.search(r'https?://|www\.|mailto:', content):
            features.has_links = True
            
        # Check for code blocks
        if '```' in content or '    ' in content:  # Code blocks or indented code
            features.has_code_blocks = True
            
        # Check for table-like structures
        if re.search(r'\|.*\|', content, re.MULTILINE):  # Markdown tables
            features.has_tables = True
        elif content.count('\t') > features.line_count * 0.5:  # Tab-separated
            features.has_tables = True
            
        # Calculate structure score
        structure_indicators = [
            features.has_headers,
            features.has_links, 
            features.has_code_blocks,
            features.has_tables,
            features.line_count > 10,
            features.word_count > 100
        ]
        features.structure_score = sum(structure_indicators) / len(structure_indicators)
        
        return features
    
    async def _process_markdown(self, content: str, features: TextFeatures, **kwargs) -> List[Any]:
        """Process markdown content."""
        if self.client:
            # Use client if available - create temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
                f.write(content)
                temp_path = Path(f.name)
            
            try:
                return await self.client.parse_document(temp_path, **kwargs)
            finally:
                temp_path.unlink()
        else:
            # Fallback markdown processing
            elements = []
            lines = content.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.startswith('#'):
                    level = len(line) - len(line.lstrip('#'))
                    elements.append(self._create_element(f"Header{level}", line.lstrip('# ')))
                elif line.startswith('```'):
                    elements.append(self._create_element("CodeBlock", line.lstrip('`')))
                elif re.match(r'^\*\s', line):
                    elements.append(self._create_element("ListItem", line.lstrip('* ')))
                elif re.search(r'\[.*\]\(.*\)', line):
                    elements.append(self._create_element("Link", line))
                else:
                    elements.append(self._create_element("NarrativeText", line))
                    
            return elements
    
    async def _process_csv(self, content: str, features: TextFeatures, **kwargs) -> List[Any]:
        """Process CSV content."""
        if self.client:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write(content)
                temp_path = Path(f.name)
            
            try:
                return await self.client.parse_document(temp_path, **kwargs)
            finally:
                temp_path.unlink()
        else:
            # Fallback CSV processing
            elements = []
            lines = content.split('\n')
            
            if lines:
                # First line as header
                headers = [h.strip() for h in lines[0].split(',')]
                elements.append(self._create_element("TableHeader", f"Headers: {', '.join(headers)}"))
                
                # Process data rows
                for i, line in enumerate(lines[1:], 1):
                    if line.strip():
                        elements.append(self._create_element("TableRow", f"Row {i}: {line}"))
                        
            return elements
    
    async def _process_json(self, content: str, features: TextFeatures, **kwargs) -> List[Any]:
        """Process JSON content."""
        if self.client:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                f.write(content)
                temp_path = Path(f.name)
            
            try:
                return await self.client.parse_document(temp_path, **kwargs)
            finally:
                temp_path.unlink()
        else:
            # Fallback JSON processing
            try:
                import json
                data = json.loads(content)
                elements = [self._create_element("JSONStructure", f"JSON with {len(str(data))} characters")]
                
                if isinstance(data, dict):
                    for key in data.keys():
                        elements.append(self._create_element("JSONKey", str(key)))
                        
                return elements
            except json.JSONDecodeError:
                return [self._create_element("Error", "Invalid JSON format")]
    
    async def _process_code(self, content: str, features: TextFeatures, **kwargs) -> List[Any]:
        """Process code files."""
        elements = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('//'):
                continue
                
            if re.search(r'(def |class |function)', line):
                elements.append(self._create_element("FunctionDefinition", line))
            elif re.search(r'(import |from |#include)', line):
                elements.append(self._create_element("Import", line))
            elif line:
                elements.append(self._create_element("CodeLine", line))
                
        return elements
    
    async def _process_plain_text(self, content: str, features: TextFeatures, **kwargs) -> List[Any]:
        """Process plain text content."""
        if self.client:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                temp_path = Path(f.name)
            
            try:
                return await self.client.parse_document(temp_path, **kwargs)
            finally:
                temp_path.unlink()
        else:
            # Fallback plain text processing
            elements = []
            paragraphs = content.split('\n\n')
            
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if paragraph:
                    elements.append(self._create_element("NarrativeText", paragraph))
                    
            return elements
    
    def _create_element(self, element_type: str, text: str) -> Any:
        """Create a mock element for fallback processing."""
        from unittest.mock import Mock
        element = Mock()
        element.category = element_type
        element.text = text
        element.metadata = {"agent": "Agent 4 Text Handler"}
        return element
    
    def _create_fallback_element(self, file_path: Path, error: str) -> Any:
        """Create fallback element when processing fails."""
        return self._create_element("Error", f"Text processing failed for {file_path.name}: {error}")