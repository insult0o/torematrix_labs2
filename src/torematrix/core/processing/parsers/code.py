"""Code snippet parser with language detection and syntax analysis."""

import re
import ast
import json
import asyncio
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

from ...models.element import Element as UnifiedElement
from .base import BaseParser, ParserResult, ParserMetadata
from .types import ElementType, ParserCapabilities, ProcessingHints
from .exceptions import LanguageDetectionError, SyntaxValidationError


class CodeLanguage(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CSHARP = "csharp"
    CPP = "cpp"
    C = "c"
    GO = "go"
    RUST = "rust"
    PHP = "php"
    RUBY = "ruby"
    SWIFT = "swift"
    KOTLIN = "kotlin"
    SCALA = "scala"
    HTML = "html"
    CSS = "css"
    SQL = "sql"
    SHELL = "shell"
    BASH = "bash"
    POWERSHELL = "powershell"
    DOCKERFILE = "dockerfile"
    YAML = "yaml"
    JSON = "json"
    XML = "xml"
    MARKDOWN = "markdown"
    PERL = "perl"
    LUA = "lua"
    R = "r"
    MATLAB = "matlab"
    UNKNOWN = "unknown"


@dataclass
class CodeElement:
    """Represents a code element."""
    element_type: str  # function, class, variable, import, comment, etc.
    name: str
    line_start: int
    line_end: int
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class CodeStructure:
    """Represents code structure."""
    language: CodeLanguage
    elements: List[CodeElement]
    imports: List[str]
    functions: List[str]
    classes: List[str]
    variables: List[str]
    comments: List[str]
    complexity_score: float
    line_count: int
    syntax_valid: bool = True
    syntax_errors: List[str] = field(default_factory=list)


class LanguageDetector:
    """Detects programming language from code snippets."""
    
    def __init__(self):
        self.language_patterns = {
            CodeLanguage.PYTHON: [
                r'def\s+\w+\s*\(',
                r'import\s+\w+',
                r'from\s+\w+\s+import',
                r'class\s+\w+\s*:',
                r'if\s+__name__\s*==\s*["\']__main__["\']',
                r'elif\s+',
                r'^\s*#.*$'
            ],
            CodeLanguage.JAVASCRIPT: [
                r'function\s+\w+\s*\(',
                r'var\s+\w+\s*=',
                r'let\s+\w+\s*=',
                r'const\s+\w+\s*=',
                r'console\.log\s*\(',
                r'=>\s*{',
                r'require\s*\('
            ],
            CodeLanguage.TYPESCRIPT: [
                r'interface\s+\w+\s*{',
                r'type\s+\w+\s*=',
                r':\s*\w+\s*=',
                r'public\s+\w+\s*:',
                r'private\s+\w+\s*:',
                r'export\s+\w+'
            ],
            CodeLanguage.JAVA: [
                r'public\s+class\s+\w+',
                r'public\s+static\s+void\s+main',
                r'import\s+java\.',
                r'@\w+',
                r'System\.out\.println',
                r'public\s+\w+\s+\w+\s*\('
            ],
            CodeLanguage.CSHARP: [
                r'using\s+System',
                r'namespace\s+\w+',
                r'public\s+class\s+\w+',
                r'Console\.WriteLine',
                r'\[.*\]',
                r'public\s+static\s+void\s+Main'
            ],
            CodeLanguage.CPP: [
                r'#include\s*<.*>',
                r'using\s+namespace\s+std',
                r'int\s+main\s*\(',
                r'cout\s*<<',
                r'cin\s*>>',
                r'std::'
            ],
            CodeLanguage.C: [
                r'#include\s*<.*\.h>',
                r'int\s+main\s*\(',
                r'printf\s*\(',
                r'scanf\s*\(',
                r'malloc\s*\(',
                r'sizeof\s*\('
            ],
            CodeLanguage.GO: [
                r'package\s+\w+',
                r'import\s+\(',
                r'func\s+\w+\s*\(',
                r'go\s+\w+\s*\(',
                r'fmt\.Print',
                r'range\s+\w+'
            ],
            CodeLanguage.RUST: [
                r'fn\s+\w+\s*\(',
                r'let\s+mut\s+\w+',
                r'use\s+\w+',
                r'impl\s+\w+',
                r'match\s+\w+',
                r'println!\s*\('
            ],
            CodeLanguage.PHP: [
                r'<\?php',
                r'function\s+\w+\s*\(',
                r'\$\w+\s*=',
                r'echo\s+',
                r'include\s+',
                r'require\s+'
            ],
            CodeLanguage.RUBY: [
                r'def\s+\w+',
                r'class\s+\w+',
                r'require\s+',
                r'puts\s+',
                r'end\s*$',
                r'@\w+'
            ],
            CodeLanguage.SWIFT: [
                r'import\s+\w+',
                r'func\s+\w+\s*\(',
                r'var\s+\w+\s*:',
                r'let\s+\w+\s*=',
                r'print\s*\(',
                r'class\s+\w+\s*:'
            ],
            CodeLanguage.KOTLIN: [
                r'fun\s+\w+\s*\(',
                r'val\s+\w+\s*=',
                r'var\s+\w+\s*:',
                r'class\s+\w+\s*\(',
                r'println\s*\(',
                r'import\s+\w+'
            ],
            CodeLanguage.SCALA: [
                r'object\s+\w+',
                r'def\s+\w+\s*\(',
                r'val\s+\w+\s*=',
                r'var\s+\w+\s*:',
                r'println\s*\(',
                r'import\s+\w+'
            ],
            CodeLanguage.HTML: [
                r'<html.*>',
                r'<head.*>',
                r'<body.*>',
                r'<div.*>',
                r'<p.*>',
                r'<!DOCTYPE'
            ],
            CodeLanguage.CSS: [
                r'\w+\s*{',
                r':\s*\w+\s*;',
                r'@media\s+',
                r'#\w+\s*{',
                r'\.\w+\s*{',
                r'color\s*:'
            ],
            CodeLanguage.SQL: [
                r'SELECT\s+.*FROM',
                r'INSERT\s+INTO',
                r'UPDATE\s+\w+\s+SET',
                r'DELETE\s+FROM',
                r'CREATE\s+TABLE',
                r'ALTER\s+TABLE'
            ],
            CodeLanguage.SHELL: [
                r'#!/bin/sh',
                r'#!/bin/bash',
                r'echo\s+',
                r'grep\s+',
                r'awk\s+',
                r'sed\s+'
            ],
            CodeLanguage.BASH: [
                r'#!/bin/bash',
                r'for\s+\w+\s+in',
                r'while\s+\[',
                r'if\s+\[',
                r'\$\{\w+\}',
                r'export\s+\w+'
            ],
            CodeLanguage.POWERSHELL: [
                r'Get-\w+',
                r'Set-\w+',
                r'New-\w+',
                r'\$\w+\s*=',
                r'Write-Host',
                r'param\s*\('
            ],
            CodeLanguage.DOCKERFILE: [
                r'FROM\s+\w+',
                r'RUN\s+',
                r'COPY\s+',
                r'ADD\s+',
                r'WORKDIR\s+',
                r'EXPOSE\s+'
            ],
            CodeLanguage.YAML: [
                r'^\s*\w+\s*:',
                r'^\s*-\s+\w+',
                r'version\s*:',
                r'name\s*:',
                r'spec\s*:',
                r'metadata\s*:'
            ],
            CodeLanguage.JSON: [
                r'^\s*{',
                r'"\w+"\s*:',
                r':\s*".*"',
                r':\s*\d+',
                r':\s*true|false',
                r':\s*null'
            ]
        }
        
        self.file_extensions = {
            '.py': CodeLanguage.PYTHON,
            '.js': CodeLanguage.JAVASCRIPT,
            '.ts': CodeLanguage.TYPESCRIPT,
            '.java': CodeLanguage.JAVA,
            '.cs': CodeLanguage.CSHARP,
            '.cpp': CodeLanguage.CPP,
            '.cc': CodeLanguage.CPP,
            '.cxx': CodeLanguage.CPP,
            '.c': CodeLanguage.C,
            '.go': CodeLanguage.GO,
            '.rs': CodeLanguage.RUST,
            '.php': CodeLanguage.PHP,
            '.rb': CodeLanguage.RUBY,
            '.swift': CodeLanguage.SWIFT,
            '.kt': CodeLanguage.KOTLIN,
            '.scala': CodeLanguage.SCALA,
            '.html': CodeLanguage.HTML,
            '.htm': CodeLanguage.HTML,
            '.css': CodeLanguage.CSS,
            '.sql': CodeLanguage.SQL,
            '.sh': CodeLanguage.SHELL,
            '.bash': CodeLanguage.BASH,
            '.ps1': CodeLanguage.POWERSHELL,
            '.dockerfile': CodeLanguage.DOCKERFILE,
            '.yml': CodeLanguage.YAML,
            '.yaml': CodeLanguage.YAML,
            '.json': CodeLanguage.JSON,
            '.xml': CodeLanguage.XML,
            '.md': CodeLanguage.MARKDOWN,
            '.pl': CodeLanguage.PERL,
            '.lua': CodeLanguage.LUA,
            '.r': CodeLanguage.R,
            '.m': CodeLanguage.MATLAB
        }
    
    async def detect(self, code: str, filename_hint: Optional[str] = None) -> CodeLanguage:
        """Detect programming language from code snippet."""
        if not code.strip():
            return CodeLanguage.UNKNOWN
        
        # First try filename extension
        if filename_hint:
            for ext, lang in self.file_extensions.items():
                if filename_hint.lower().endswith(ext):
                    return lang
        
        # Try pattern matching
        language_scores = {}
        
        for language, patterns in self.language_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, code, re.MULTILINE | re.IGNORECASE))
                score += matches
            
            if score > 0:
                language_scores[language] = score
        
        if language_scores:
            # Return language with highest score
            best_language = max(language_scores, key=language_scores.get)
            return best_language
        
        return CodeLanguage.UNKNOWN


class SyntaxAnalyzer:
    """Analyzes code syntax and structure."""
    
    async def analyze(self, code: str, language: CodeLanguage) -> CodeStructure:
        """Analyze code structure for given language."""
        structure = CodeStructure(
            language=language,
            elements=[],
            imports=[],
            functions=[],
            classes=[],
            variables=[],
            comments=[],
            complexity_score=0.0,
            line_count=len(code.splitlines())
        )
        
        # Language-specific analysis
        if language == CodeLanguage.PYTHON:
            await self._analyze_python(code, structure)
        elif language == CodeLanguage.JAVASCRIPT:
            await self._analyze_javascript(code, structure)
        elif language == CodeLanguage.JAVA:
            await self._analyze_java(code, structure)
        else:
            # Generic analysis for other languages
            await self._analyze_generic(code, structure)
        
        # Calculate complexity
        structure.complexity_score = self._calculate_complexity(structure)
        
        return structure
    
    async def _analyze_python(self, code: str, structure: CodeStructure) -> None:
        """Analyze Python code structure."""
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    structure.functions.append(node.name)
                    structure.elements.append(CodeElement(
                        element_type="function",
                        name=node.name,
                        line_start=node.lineno,
                        line_end=getattr(node, 'end_lineno', node.lineno),
                        content=self._extract_node_content(code, node),
                        metadata={"args": len(node.args.args)}
                    ))
                
                elif isinstance(node, ast.ClassDef):
                    structure.classes.append(node.name)
                    structure.elements.append(CodeElement(
                        element_type="class",
                        name=node.name,
                        line_start=node.lineno,
                        line_end=getattr(node, 'end_lineno', node.lineno),
                        content=self._extract_node_content(code, node),
                        metadata={"methods": len([n for n in node.body if isinstance(n, ast.FunctionDef)])}
                    ))
                
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        structure.imports.append(alias.name)
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        structure.imports.append(node.module)
                
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            structure.variables.append(target.id)
            
            structure.syntax_valid = True
            
        except SyntaxError as e:
            structure.syntax_valid = False
            structure.syntax_errors.append(str(e))
            # Fall back to regex-based analysis
            await self._analyze_python_regex(code, structure)
    
    async def _analyze_javascript(self, code: str, structure: CodeStructure) -> None:
        """Analyze JavaScript code structure."""
        # Function declarations
        func_pattern = r'function\s+(\w+)\s*\('
        for match in re.finditer(func_pattern, code):
            structure.functions.append(match.group(1))
        
        # Arrow functions
        arrow_pattern = r'(\w+)\s*=\s*\([^)]*\)\s*=>'
        for match in re.finditer(arrow_pattern, code):
            structure.functions.append(match.group(1))
        
        # Variable declarations
        var_pattern = r'(var|let|const)\s+(\w+)'
        for match in re.finditer(var_pattern, code):
            structure.variables.append(match.group(2))
        
        # Imports/requires
        import_pattern = r'(import|require)\s*\(?\s*["\']([^"\']+)["\']'
        for match in re.finditer(import_pattern, code):
            structure.imports.append(match.group(2))
    
    async def _analyze_java(self, code: str, structure: CodeStructure) -> None:
        """Analyze Java code structure."""
        # Class declarations
        class_pattern = r'(public\s+)?class\s+(\w+)'
        for match in re.finditer(class_pattern, code):
            structure.classes.append(match.group(2))
        
        # Method declarations
        method_pattern = r'(public|private|protected)?\s*(static\s+)?[\w<>\[\]]+\s+(\w+)\s*\('
        for match in re.finditer(method_pattern, code):
            structure.functions.append(match.group(3))
        
        # Import statements
        import_pattern = r'import\s+([\w.]+)'
        for match in re.finditer(import_pattern, code):
            structure.imports.append(match.group(1))
    
    async def _analyze_generic(self, code: str, structure: CodeStructure) -> None:
        """Generic analysis for languages without specific parsers."""
        lines = code.splitlines()
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            
            # Comments
            if line.startswith('#') or line.startswith('//') or line.startswith('/*'):
                structure.comments.append(line)
            
            # Functions (generic patterns)
            func_patterns = [
                r'function\s+(\w+)',
                r'def\s+(\w+)',
                r'fn\s+(\w+)',
                r'func\s+(\w+)'
            ]
            
            for pattern in func_patterns:
                match = re.search(pattern, line)
                if match:
                    structure.functions.append(match.group(1))
                    break
    
    async def _analyze_python_regex(self, code: str, structure: CodeStructure) -> None:
        """Fallback regex-based Python analysis."""
        # Function definitions
        func_pattern = r'def\s+(\w+)\s*\('
        for match in re.finditer(func_pattern, code):
            structure.functions.append(match.group(1))
        
        # Class definitions
        class_pattern = r'class\s+(\w+)\s*:'
        for match in re.finditer(class_pattern, code):
            structure.classes.append(match.group(1))
        
        # Imports
        import_pattern = r'import\s+(\w+)'
        for match in re.finditer(import_pattern, code):
            structure.imports.append(match.group(1))
        
        from_import_pattern = r'from\s+(\w+)\s+import'
        for match in re.finditer(from_import_pattern, code):
            structure.imports.append(match.group(1))
    
    def _extract_node_content(self, code: str, node) -> str:
        """Extract source code for an AST node."""
        lines = code.splitlines()
        start_line = node.lineno - 1
        end_line = getattr(node, 'end_lineno', node.lineno) - 1
        
        if start_line < len(lines):
            if end_line < len(lines):
                return '\n'.join(lines[start_line:end_line + 1])
            else:
                return lines[start_line]
        
        return ""
    
    def _calculate_complexity(self, structure: CodeStructure) -> float:
        """Calculate code complexity score."""
        complexity = 0.0
        
        # Base complexity from structure
        complexity += len(structure.functions) * 2
        complexity += len(structure.classes) * 3
        complexity += len(structure.imports) * 0.5
        
        # Normalize by line count
        if structure.line_count > 0:
            complexity = complexity / structure.line_count * 100
        
        return min(complexity, 100.0)  # Cap at 100


class CodeParser(BaseParser):
    """Advanced code snippet parser with language detection."""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.language_detector = LanguageDetector()
        self.syntax_analyzer = SyntaxAnalyzer()
        self.max_lines = self.config.parser_specific.get('max_lines', 10000)
        self.min_confidence = self.config.parser_specific.get('min_confidence', 0.8)
    
    @property
    def capabilities(self) -> ParserCapabilities:
        return ParserCapabilities(
            supported_types=[ElementType.CODE_BLOCK, ElementType.CODE],
            supported_languages=[lang.value for lang in CodeLanguage if lang != CodeLanguage.UNKNOWN],
            supports_batch=True,
            supports_async=True,
            supports_validation=True,
            supports_metadata_extraction=True,
            supports_structured_output=True,
            supports_export_formats=["json", "syntax_highlighted", "ast", "metrics"]
        )
    
    def can_parse(self, element: UnifiedElement) -> bool:
        """Check if element contains code."""
        return (
            (hasattr(element, 'type') and element.type in ["CodeBlock", "Code"]) or
            (hasattr(element, 'category') and element.category == "code") or
            self._has_code_indicators(element)
        )
    
    async def parse(self, element: UnifiedElement, hints: Optional[ProcessingHints] = None) -> ParserResult:
        """Parse code with language detection and structure analysis."""
        try:
            # Extract code content
            code_content = self._extract_code_content(element)
            
            if len(code_content.splitlines()) > self.max_lines:
                return self._create_failure_result(
                    f"Code too large: {len(code_content.splitlines())} lines > {self.max_lines}",
                    validation_errors=["Code exceeds maximum line limit"]
                )
            
            # Get filename hint
            filename_hint = None
            if hints and hints.code_hints:
                filename_hint = hints.code_hints.get('filename')
            
            # Detect programming language
            language = await self.language_detector.detect(code_content, filename_hint)
            
            # Analyze code structure
            structure = await self.syntax_analyzer.analyze(code_content, language)
            
            # Apply syntax highlighting
            highlighted_code = await self._apply_syntax_highlighting(code_content, language)
            
            # Calculate confidence
            confidence = self._calculate_confidence(language, structure, len(code_content))
            
            if confidence < self.min_confidence:
                return self._create_failure_result(
                    f"Low confidence in code parsing: {confidence:.2f} < {self.min_confidence}",
                    validation_errors=[f"Confidence too low: {confidence:.2f}"]
                )
            
            return ParserResult(
                success=True,
                data={
                    "language": language.value,
                    "structure": structure.__dict__,
                    "highlighted_code": highlighted_code,
                    "syntax_valid": structure.syntax_valid,
                    "elements": {
                        "functions": structure.functions,
                        "classes": structure.classes,
                        "imports": structure.imports,
                        "variables": structure.variables
                    },
                    "metrics": {
                        "line_count": structure.line_count,
                        "complexity": structure.complexity_score,
                        "element_count": len(structure.elements),
                        "function_count": len(structure.functions),
                        "class_count": len(structure.classes)
                    }
                },
                metadata=ParserMetadata(
                    confidence=confidence,
                    element_metadata={
                        "language": language.value,
                        "syntax_valid": structure.syntax_valid,
                        "complexity_level": self._get_complexity_level(structure.complexity_score)
                    }
                ),
                validation_errors=structure.syntax_errors,
                extracted_content=code_content,
                structured_data=self._export_formats(code_content, structure, highlighted_code),
                export_formats={
                    "highlighted": highlighted_code,
                    "json": json.dumps(structure.__dict__, default=str, indent=2),
                    "metrics": self._generate_metrics_report(structure)
                }
            )
            
        except Exception as e:
            return self._create_failure_result(
                f"Code parsing failed: {str(e)}",
                validation_errors=[f"Code parsing error: {str(e)}"]
            )
    
    def validate(self, result: ParserResult) -> List[str]:
        """Validate code parsing result."""
        errors = []
        
        if not result.success:
            return ["Code parsing failed"]
        
        # Validate language detection
        language = result.data.get("language")
        if language == "unknown":
            errors.append("Could not detect programming language")
        
        # Validate structure
        structure = result.data.get("structure")
        if not structure:
            errors.append("No code structure detected")
        
        # Check syntax validity for supported languages
        if language in ['python', 'javascript'] and not result.data.get("syntax_valid", True):
            errors.append("Syntax validation failed")
        
        return errors
    
    def get_supported_types(self) -> List[ElementType]:
        """Return supported code element types."""
        return [ElementType.CODE_BLOCK, ElementType.CODE]
    
    def _extract_code_content(self, element: UnifiedElement) -> str:
        """Extract code content from element."""
        if hasattr(element, 'text') and element.text:
            content = element.text.strip()
            
            # Remove code fence markers if present
            if content.startswith('```'):
                lines = content.splitlines()
                if len(lines) > 1:
                    # Remove first and last line if they're fence markers
                    if lines[0].startswith('```') and lines[-1] == '```':
                        content = '\n'.join(lines[1:-1])
                    elif lines[0].startswith('```'):
                        content = '\n'.join(lines[1:])
            
            return content
        
        return ""
    
    def _has_code_indicators(self, element: UnifiedElement) -> bool:
        """Check if element has code-like indicators."""
        if not hasattr(element, 'text') or not element.text:
            return False
        
        text = element.text
        
        # Look for code patterns
        code_patterns = [
            r'```[\w]*\n',  # Code fences
            r'^\s*def\s+\w+\s*\(',  # Function definitions
            r'^\s*class\s+\w+',  # Class definitions
            r'^\s*import\s+\w+',  # Import statements
            r'^\s*#include\s*<.*>',  # C/C++ includes
            r'^\s*function\s+\w+\s*\(',  # JavaScript functions
            r';\s*$',  # Semicolon at end of line
            r'{\s*$',  # Opening brace at end of line
        ]
        
        for pattern in code_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return True
        
        # Check for high density of programming keywords
        programming_keywords = [
            'function', 'class', 'import', 'export', 'const', 'let', 'var',
            'def', 'return', 'if', 'else', 'for', 'while', 'try', 'catch',
            'public', 'private', 'protected', 'static', 'void', 'int', 'string'
        ]
        
        word_count = len(text.split())
        keyword_count = sum(1 for word in text.split() if word.lower() in programming_keywords)
        
        if word_count > 10 and keyword_count / word_count > 0.1:  # 10% programming keywords
            return True
        
        return False
    
    async def _apply_syntax_highlighting(self, code: str, language: CodeLanguage) -> str:
        """Apply basic syntax highlighting to code."""
        # This is a simplified version - in production you'd use pygments or similar
        
        if language == CodeLanguage.PYTHON:
            return self._highlight_python(code)
        elif language == CodeLanguage.JAVASCRIPT:
            return self._highlight_javascript(code)
        else:
            return code  # Return as-is for unsupported languages
    
    def _highlight_python(self, code: str) -> str:
        """Apply basic Python syntax highlighting."""
        # Keywords
        keywords = ['def', 'class', 'import', 'from', 'if', 'else', 'elif', 'for', 'while', 'try', 'except', 'return']
        for keyword in keywords:
            code = re.sub(rf'\b{keyword}\b', f'**{keyword}**', code)
        
        return code
    
    def _highlight_javascript(self, code: str) -> str:
        """Apply basic JavaScript syntax highlighting."""
        keywords = ['function', 'var', 'let', 'const', 'if', 'else', 'for', 'while', 'return']
        for keyword in keywords:
            code = re.sub(rf'\b{keyword}\b', f'**{keyword}**', code)
        
        return code
    
    def _calculate_confidence(self, language: CodeLanguage, structure: CodeStructure, content_length: int) -> float:
        """Calculate confidence in code parsing."""
        confidence_factors = []
        
        # Language detection confidence (40%)
        if language != CodeLanguage.UNKNOWN:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.2)
        
        # Structure extraction confidence (30%)
        if structure.elements or structure.functions or structure.classes:
            confidence_factors.append(0.9)
        elif structure.imports or structure.variables:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.3)
        
        # Syntax validity (20%)
        if structure.syntax_valid:
            confidence_factors.append(1.0)
        else:
            confidence_factors.append(0.5)
        
        # Content length (10%)
        if content_length > 100:
            confidence_factors.append(0.8)
        elif content_length > 20:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.4)
        
        # Weighted average
        weights = [0.4, 0.3, 0.2, 0.1]
        return sum(factor * weight for factor, weight in zip(confidence_factors, weights))
    
    def _get_complexity_level(self, complexity_score: float) -> str:
        """Get human-readable complexity level."""
        if complexity_score > 50:
            return "high"
        elif complexity_score > 20:
            return "medium"
        else:
            return "low"
    
    def _export_formats(self, code: str, structure: CodeStructure, highlighted: str) -> Dict[str, Any]:
        """Generate export formats."""
        return {
            "raw_code": code,
            "highlighted": highlighted,
            "structure": {
                "language": structure.language.value,
                "functions": structure.functions,
                "classes": structure.classes,
                "imports": structure.imports,
                "metrics": {
                    "lines": structure.line_count,
                    "complexity": structure.complexity_score,
                    "elements": len(structure.elements)
                }
            }
        }
    
    def _generate_metrics_report(self, structure: CodeStructure) -> str:
        """Generate a metrics report for the code."""
        report = f"""Code Metrics Report
==================
Language: {structure.language.value}
Lines of Code: {structure.line_count}
Complexity Score: {structure.complexity_score:.1f}
Syntax Valid: {'Yes' if structure.syntax_valid else 'No'}

Structure:
- Functions: {len(structure.functions)}
- Classes: {len(structure.classes)}
- Imports: {len(structure.imports)}
- Variables: {len(structure.variables)}
- Total Elements: {len(structure.elements)}
"""
        
        if structure.syntax_errors:
            report += f"\nSyntax Errors:\n"
            for error in structure.syntax_errors:
                report += f"- {error}\n"
        
        return report