"""Tests for code parser functionality."""

import pytest
import asyncio
from unittest.mock import Mock, patch

from src.torematrix.core.processing.parsers.code import (
    CodeParser, LanguageDetector, SyntaxAnalyzer, CodeLanguage
)
from src.torematrix.core.processing.parsers.types import ProcessingHints, ParserConfig


class TestLanguageDetector:
    """Test language detection functionality."""
    
    def setup_method(self):
        self.detector = LanguageDetector()
    
    @pytest.mark.asyncio
    async def test_python_detection(self):
        """Test Python code detection."""
        python_code = """
def hello_world():
    print("Hello, World!")
    return True

if __name__ == "__main__":
    hello_world()
"""
        language = await self.detector.detect(python_code)
        assert language == CodeLanguage.PYTHON
    
    @pytest.mark.asyncio
    async def test_javascript_detection(self):
        """Test JavaScript code detection."""
        js_code = """
function helloWorld() {
    console.log("Hello, World!");
    return true;
}

const result = helloWorld();
"""
        language = await self.detector.detect(js_code)
        assert language == CodeLanguage.JAVASCRIPT
    
    @pytest.mark.asyncio
    async def test_java_detection(self):
        """Test Java code detection."""
        java_code = """
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
"""
        language = await self.detector.detect(java_code)
        assert language == CodeLanguage.JAVA
    
    @pytest.mark.asyncio
    async def test_filename_hint(self):
        """Test language detection with filename hint."""
        code = "print('hello')"
        language = await self.detector.detect(code, "script.py")
        assert language == CodeLanguage.PYTHON
    
    @pytest.mark.asyncio
    async def test_unknown_language(self):
        """Test detection of unknown language."""
        unknown_code = "This is just plain text without code patterns."
        language = await self.detector.detect(unknown_code)
        assert language == CodeLanguage.UNKNOWN


class TestSyntaxAnalyzer:
    """Test syntax analysis functionality."""
    
    def setup_method(self):
        self.analyzer = SyntaxAnalyzer()
    
    @pytest.mark.asyncio
    async def test_python_analysis(self):
        """Test Python syntax analysis."""
        python_code = """
import os
import sys

def calculate(x, y):
    return x + y

class Calculator:
    def __init__(self):
        self.result = 0
    
    def add(self, x, y):
        return x + y

result = calculate(5, 3)
"""
        structure = await self.analyzer.analyze(python_code, CodeLanguage.PYTHON)
        
        assert structure.language == CodeLanguage.PYTHON
        assert len(structure.functions) >= 2  # calculate, add
        assert len(structure.classes) >= 1   # Calculator
        assert len(structure.imports) >= 2   # os, sys
        assert structure.line_count > 0
        assert structure.syntax_valid
    
    @pytest.mark.asyncio
    async def test_javascript_analysis(self):
        """Test JavaScript syntax analysis."""
        js_code = """
const express = require('express');
const app = express();

function handleRequest(req, res) {
    res.send('Hello');
}

const port = 3000;
app.listen(port);
"""
        structure = await self.analyzer.analyze(js_code, CodeLanguage.JAVASCRIPT)
        
        assert structure.language == CodeLanguage.JAVASCRIPT
        assert "handleRequest" in structure.functions
        assert "express" in structure.imports
        assert "port" in structure.variables
    
    @pytest.mark.asyncio
    async def test_syntax_error_handling(self):
        """Test handling of syntax errors."""
        invalid_python = """
def broken_function(
    print("Missing closing parenthesis"
    return True
"""
        structure = await self.analyzer.analyze(invalid_python, CodeLanguage.PYTHON)
        
        assert structure.language == CodeLanguage.PYTHON
        assert not structure.syntax_valid
        assert len(structure.syntax_errors) > 0
    
    @pytest.mark.asyncio
    async def test_complexity_calculation(self):
        """Test code complexity calculation."""
        complex_code = """
def complex_function():
    for i in range(10):
        if i % 2 == 0:
            for j in range(i):
                if j > 5:
                    print(j)
                else:
                    continue
        else:
            break
    return True

class ComplexClass:
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
"""
        structure = await self.analyzer.analyze(complex_code, CodeLanguage.PYTHON)
        assert structure.complexity_score > 0


class TestCodeParser:
    """Test code parser functionality."""
    
    def setup_method(self):
        config = ParserConfig()
        self.parser = CodeParser(config)
    
    def create_mock_element(self, text, element_type="CodeBlock"):
        """Create mock element for testing."""
        element = Mock()
        element.type = element_type
        element.text = text
        element.metadata = {}
        return element
    
    @pytest.mark.asyncio
    async def test_can_parse_code_element(self):
        """Test code element recognition."""
        code_element = self.create_mock_element("def hello(): pass", "CodeBlock")
        assert self.parser.can_parse(code_element)
        
        text_element = self.create_mock_element("Just plain text", "Text")
        assert not self.parser.can_parse(text_element)
    
    @pytest.mark.asyncio
    async def test_code_indicators(self):
        """Test code pattern recognition."""
        code_text = """
```python
def hello_world():
    print("Hello!")
```
"""
        code_element = self.create_mock_element(code_text, "Text")
        assert self.parser.can_parse(code_element)
    
    @pytest.mark.asyncio
    async def test_parse_python_code(self):
        """Test parsing Python code."""
        python_code = """
import json
import os

def process_data(data):
    \"\"\"Process input data.\"\"\"
    result = []
    for item in data:
        if item.get('valid'):
            result.append(item['value'])
    return result

class DataProcessor:
    def __init__(self, config):
        self.config = config
    
    def run(self):
        return "processed"

# Main execution
if __name__ == "__main__":
    processor = DataProcessor({})
    print(processor.run())
"""
        element = self.create_mock_element(python_code)
        result = await self.parser.parse(element)
        
        assert result.success
        assert result.data["language"] == "python"
        assert result.data["syntax_valid"]
        assert "process_data" in result.data["elements"]["functions"]
        assert "DataProcessor" in result.data["elements"]["classes"]
        assert "json" in result.data["elements"]["imports"]
        assert result.metadata.confidence > 0.5
    
    @pytest.mark.asyncio
    async def test_parse_javascript_code(self):
        """Test parsing JavaScript code."""
        js_code = """
const express = require('express');
const { promisify } = require('util');

function createServer(port) {
    const app = express();
    
    app.get('/', (req, res) => {
        res.json({ message: 'Hello World' });
    });
    
    return app.listen(port);
}

class APIHandler {
    constructor(config) {
        this.config = config;
    }
    
    async handleRequest(req, res) {
        try {
            const result = await this.processRequest(req);
            res.json(result);
        } catch (error) {
            res.status(500).json({ error: error.message });
        }
    }
}

module.exports = { createServer, APIHandler };
"""
        element = self.create_mock_element(js_code)
        result = await self.parser.parse(element)
        
        assert result.success
        assert result.data["language"] == "javascript"
        assert "createServer" in result.data["elements"]["functions"]
        assert "APIHandler" in result.data["elements"]["classes"]
        assert "express" in result.data["elements"]["imports"]
    
    @pytest.mark.asyncio
    async def test_parse_with_hints(self):
        """Test parsing with processing hints."""
        code = "print('Hello')"
        element = self.create_mock_element(code)
        
        hints = ProcessingHints()
        hints.code_hints = {"filename": "script.py"}
        
        result = await self.parser.parse(element, hints)
        
        assert result.success
        assert result.data["language"] == "python"
    
    @pytest.mark.asyncio
    async def test_code_fence_removal(self):
        """Test removal of code fence markers."""
        fenced_code = """```python
def hello():
    return "world"
```"""
        element = self.create_mock_element(fenced_code)
        result = await self.parser.parse(element)
        
        assert result.success
        assert "```" not in result.extracted_content
        assert "def hello():" in result.extracted_content
    
    @pytest.mark.asyncio
    async def test_large_code_handling(self):
        """Test handling of large code files."""
        # Create large code that exceeds default limits
        large_code = "\n".join([f"# Line {i}" for i in range(20000)])
        element = self.create_mock_element(large_code)
        
        result = await self.parser.parse(element)
        
        # Should fail due to size limit
        assert not result.success
        assert "too large" in result.validation_errors[0].lower()
    
    @pytest.mark.asyncio
    async def test_low_confidence_handling(self):
        """Test handling of low confidence results."""
        # Configure parser with high confidence threshold
        config = ParserConfig()
        config.parser_specific = {"min_confidence": 0.9}
        parser = CodeParser(config)
        
        # Ambiguous text that might be detected as code but with low confidence
        ambiguous_text = "hello world test 123"
        element = self.create_mock_element(ambiguous_text)
        
        result = await parser.parse(element)
        
        # Should fail due to low confidence
        assert not result.success
        assert "confidence" in result.validation_errors[0].lower()
    
    @pytest.mark.asyncio
    async def test_syntax_highlighting(self):
        """Test syntax highlighting functionality."""
        python_code = "def hello(): return 'world'"
        element = self.create_mock_element(python_code)
        
        result = await self.parser.parse(element)
        
        assert result.success
        assert "highlighted_code" in result.data
        # Basic highlighting should add emphasis to keywords
        assert "**def**" in result.data["highlighted_code"]
    
    @pytest.mark.asyncio
    async def test_export_formats(self):
        """Test export format generation."""
        code = """
def test():
    pass

class Test:
    pass
"""
        element = self.create_mock_element(code)
        result = await self.parser.parse(element)
        
        assert result.success
        assert "highlighted" in result.export_formats
        assert "json" in result.export_formats
        assert "metrics" in result.export_formats
    
    @pytest.mark.asyncio
    async def test_validation(self):
        """Test result validation."""
        # Test successful result validation
        python_code = "def hello(): pass"
        element = self.create_mock_element(python_code)
        result = await self.parser.parse(element)
        
        validation_errors = self.parser.validate(result)
        assert len(validation_errors) == 0
        
        # Test failed result validation
        failed_result = Mock()
        failed_result.success = False
        failed_result.data = {}
        
        validation_errors = self.parser.validate(failed_result)
        assert len(validation_errors) > 0
        assert "failed" in validation_errors[0].lower()
    
    def test_get_supported_types(self):
        """Test supported element types."""
        supported_types = self.parser.get_supported_types()
        from src.torematrix.core.processing.parsers.types import ElementType
        
        assert ElementType.CODE_BLOCK in supported_types
        assert ElementType.CODE in supported_types
    
    def test_capabilities(self):
        """Test parser capabilities."""
        capabilities = self.parser.capabilities
        
        assert len(capabilities.supported_languages) > 20
        assert "python" in capabilities.supported_languages
        assert "javascript" in capabilities.supported_languages
        assert capabilities.supports_async
        assert capabilities.supports_validation
        assert "json" in capabilities.supports_export_formats


@pytest.mark.integration
class TestCodeParserIntegration:
    """Integration tests for code parser."""
    
    @pytest.mark.asyncio
    async def test_multiple_language_detection(self):
        """Test detection across multiple languages."""
        test_cases = [
            ("def hello(): pass", CodeLanguage.PYTHON),
            ("function hello() { return true; }", CodeLanguage.JAVASCRIPT),
            ("public class Hello {}", CodeLanguage.JAVA),
            ("SELECT * FROM users", CodeLanguage.SQL),
            ("<html><body></body></html>", CodeLanguage.HTML),
        ]
        
        parser = CodeParser()
        
        for code, expected_lang in test_cases:
            element = Mock()
            element.type = "CodeBlock"
            element.text = code
            element.metadata = {}
            
            result = await parser.parse(element)
            
            if result.success:
                assert result.data["language"] == expected_lang.value
    
    @pytest.mark.asyncio
    async def test_performance_with_large_codebase(self):
        """Test performance with realistic code size."""
        # Simulate a moderate-sized Python file
        large_python_code = '''
import os
import sys
import json
from typing import Dict, List, Optional

class DocumentProcessor:
    """Process documents with various formats."""
    
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.processed_count = 0
    
    def process_file(self, filepath: str) -> Optional[Dict]:
        """Process a single file."""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            result = self._analyze_content(content)
            self.processed_count += 1
            return result
            
        except Exception as e:
            print(f"Error processing {filepath}: {e}")
            return None
    
    def _analyze_content(self, content: str) -> Dict:
        """Analyze content and extract metadata."""
        lines = content.splitlines()
        
        analysis = {
            'line_count': len(lines),
            'char_count': len(content),
            'word_count': len(content.split()),
            'has_code': self._detect_code_patterns(content),
            'language': self._detect_language(content)
        }
        
        return analysis
    
    def _detect_code_patterns(self, content: str) -> bool:
        """Detect if content contains code patterns."""
        code_indicators = ['def ', 'class ', 'import ', 'function', 'var ']
        return any(indicator in content for indicator in code_indicators)
    
    def _detect_language(self, content: str) -> str:
        """Basic language detection."""
        if 'def ' in content and 'import ' in content:
            return 'python'
        elif 'function' in content and 'var ' in content:
            return 'javascript'
        else:
            return 'unknown'
    
    def batch_process(self, filepaths: List[str]) -> List[Dict]:
        """Process multiple files."""
        results = []
        
        for filepath in filepaths:
            result = self.process_file(filepath)
            if result:
                results.append(result)
        
        return results
    
    def get_statistics(self) -> Dict:
        """Get processing statistics."""
        return {
            'processed_count': self.processed_count,
            'config': self.config
        }

def main():
    """Main entry point."""
    config = {'output_dir': '/tmp/processed'}
    processor = DocumentProcessor(config)
    
    # Example usage
    files = ['doc1.txt', 'doc2.txt', 'doc3.txt']
    results = processor.batch_process(files)
    
    print(f"Processed {len(results)} files")
    print(processor.get_statistics())

if __name__ == '__main__':
    main()
'''
        
        parser = CodeParser()
        element = Mock()
        element.type = "CodeBlock"
        element.text = large_python_code
        element.metadata = {}
        
        import time
        start_time = time.time()
        
        result = await parser.parse(element)
        
        processing_time = time.time() - start_time
        
        assert result.success
        assert processing_time < 5.0  # Should complete within 5 seconds
        assert result.data["language"] == "python"
        assert len(result.data["elements"]["functions"]) >= 5
        assert len(result.data["elements"]["classes"]) >= 1
        assert result.metadata.confidence > 0.7