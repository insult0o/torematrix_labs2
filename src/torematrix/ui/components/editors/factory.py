"""Editor factory for creating different types of inline editors"""

from enum import Enum
from typing import Dict, Any, Optional, Type, Callable
from PyQt6.QtWidgets import QWidget

from .base import BaseEditor, EditorConfig


class EditorType(Enum):
    """Enumeration of available editor types"""
    INLINE = "inline"
    RICH_TEXT = "rich_text"
    CODE = "code"
    FORMULA = "formula"
    MARKDOWN = "markdown"
    MULTILINE = "multiline"
    SINGLE_LINE = "single_line"
    
    def __str__(self):
        return self.value


class EditorFactory:
    """Factory class for creating different types of inline editors
    
    Features:
    - Automatic editor type detection based on content
    - Configurable editor creation with custom settings
    - Registration of custom editor types
    - Fallback to default editor types
    """
    
    # Registry of editor types and their classes
    _editor_registry: Dict[EditorType, Type[BaseEditor]] = {}
    
    # Registry of content-based auto-detection functions
    _auto_detection_registry: Dict[str, Callable[[str], bool]] = {}
    
    @classmethod
    def register_editor(cls, editor_type: EditorType, editor_class: Type[BaseEditor]):
        """Register a new editor type
        
        Args:
            editor_type: Type of editor
            editor_class: Editor class to register
        """
        cls._editor_registry[editor_type] = editor_class
    
    @classmethod
    def register_auto_detection(cls, content_type: str, detection_func: Callable[[str], bool]):
        """Register content auto-detection function
        
        Args:
            content_type: Content type identifier
            detection_func: Function that returns True if content matches this type
        """
        cls._auto_detection_registry[content_type] = detection_func
    
    @classmethod
    def create_editor(cls, editor_type: EditorType, 
                     config: Optional[Dict[str, Any]] = None,
                     parent: Optional[QWidget] = None) -> BaseEditor:
        """Create an editor of the specified type
        
        Args:
            editor_type: Type of editor to create
            config: Configuration dictionary for the editor
            parent: Parent widget
            
        Returns:
            Configured editor instance
            
        Raises:
            ValueError: If editor type is not supported
        """
        # Convert config dict to EditorConfig if needed
        if config is None:
            editor_config = EditorConfig()
        elif isinstance(config, dict):
            editor_config = EditorConfig.from_dict(config)
        else:
            editor_config = config
        
        # Get editor class from registry
        editor_class = cls._get_editor_class(editor_type)
        
        if editor_class is None:
            # Fall back to default inline editor
            editor_class = cls._get_default_editor_class()
        
        # Create and configure editor
        try:
            editor = editor_class(config=editor_config, parent=parent)
            
            # Apply any additional configuration
            cls._apply_additional_config(editor, editor_type, config or {})
            
            return editor
            
        except Exception as e:
            # If creation fails, fall back to basic inline editor
            from .inline import InlineEditor
            return InlineEditor(config=editor_config, parent=parent)
    
    @classmethod
    def auto_detect_editor_type(cls, content: str, element_type: str = "") -> EditorType:
        """Automatically detect the best editor type for given content
        
        Args:
            content: Content to analyze
            element_type: Hint about element type
            
        Returns:
            Recommended editor type
        """
        # Check element type hint first
        if element_type:
            type_mapping = {
                'code': EditorType.CODE,
                'formula': EditorType.FORMULA,
                'markdown': EditorType.MARKDOWN,
                'rich_text': EditorType.RICH_TEXT,
                'text': EditorType.INLINE
            }
            
            if element_type.lower() in type_mapping:
                return type_mapping[element_type.lower()]
        
        # Analyze content characteristics
        if not content.strip():
            return EditorType.INLINE
        
        # Check for multi-line content
        if '\n' in content and len(content.splitlines()) > 3:
            # Check for specific content types
            if cls._is_code_content(content):
                return EditorType.CODE
            elif cls._is_markdown_content(content):
                return EditorType.MARKDOWN
            else:
                return EditorType.MULTILINE
        
        # Check for specific single-line patterns
        if cls._is_formula_content(content):
            return EditorType.FORMULA
        elif cls._has_rich_formatting(content):
            return EditorType.RICH_TEXT
        
        # Default to inline editor for simple text
        return EditorType.INLINE
    
    @classmethod
    def get_supported_types(cls) -> list[EditorType]:
        """Get list of supported editor types
        
        Returns:
            List of supported editor types
        """
        # Return built-in types plus registered types
        built_in_types = [
            EditorType.INLINE,
            EditorType.MULTILINE,
            EditorType.SINGLE_LINE
        ]
        
        registered_types = list(cls._editor_registry.keys())
        
        # Combine and deduplicate
        all_types = list(set(built_in_types + registered_types))
        return sorted(all_types, key=lambda x: x.value)
    
    @classmethod
    def create_configured_editor(cls, element_type: str, content: str = "",
                                config_overrides: Optional[Dict[str, Any]] = None,
                                parent: Optional[QWidget] = None) -> BaseEditor:
        """Create an editor configured for specific element type and content
        
        Args:
            element_type: Type of element being edited
            content: Initial content (for auto-detection)
            config_overrides: Configuration overrides
            parent: Parent widget
            
        Returns:
            Configured editor instance
        """
        # Auto-detect best editor type
        editor_type = cls.auto_detect_editor_type(content, element_type)
        
        # Create base configuration
        config = EditorConfig()
        
        # Apply element-type specific configuration
        element_configs = {
            'code': {
                'font_family': 'Consolas, Monaco, monospace',
                'tab_behavior': 'indent',
                'enter_commits': False,
                'validation_rules': ['valid_syntax']
            },
            'formula': {
                'font_family': 'Times New Roman, serif',
                'max_length': 500,
                'validation_rules': ['valid_formula']
            },
            'markdown': {
                'enter_commits': False,
                'tab_behavior': 'indent',
                'validation_rules': ['valid_markdown']
            },
            'rich_text': {
                'validation_rules': ['valid_html'],
                'max_length': 50000
            }
        }
        
        if element_type in element_configs:
            for key, value in element_configs[element_type].items():
                setattr(config, key, value)
        
        # Apply configuration overrides
        if config_overrides:
            for key, value in config_overrides.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        # Set element context
        config.element_type = element_type
        
        return cls.create_editor(editor_type, config.to_dict(), parent)
    
    @classmethod
    def _get_editor_class(cls, editor_type: EditorType) -> Optional[Type[BaseEditor]]:
        """Get editor class for given type
        
        Args:
            editor_type: Type of editor
            
        Returns:
            Editor class or None if not found
        """
        # Check registry first
        if editor_type in cls._editor_registry:
            return cls._editor_registry[editor_type]
        
        # Check built-in types
        try:
            if editor_type == EditorType.INLINE:
                from .inline import InlineEditor
                return InlineEditor
            elif editor_type == EditorType.MULTILINE:
                from .inline import InlineEditor
                return InlineEditor  # For now, use inline for multiline
            elif editor_type == EditorType.SINGLE_LINE:
                from .inline import InlineEditor
                return InlineEditor
            elif editor_type == EditorType.RICH_TEXT:
                try:
                    from .enhanced import RichTextEditor
                    return RichTextEditor
                except ImportError:
                    from .inline import InlineEditor
                    return InlineEditor
            elif editor_type == EditorType.CODE:
                try:
                    from .code import CodeEditor
                    return CodeEditor
                except ImportError:
                    from .inline import InlineEditor
                    return InlineEditor
            elif editor_type == EditorType.FORMULA:
                try:
                    from .formula import FormulaEditor
                    return FormulaEditor
                except ImportError:
                    from .inline import InlineEditor
                    return InlineEditor
            elif editor_type == EditorType.MARKDOWN:
                try:
                    from .markdown_editor import MarkdownEditor
                    return MarkdownEditor
                except ImportError:
                    from .inline import InlineEditor
                    return InlineEditor
        except ImportError:
            pass
        
        return None
    
    @classmethod
    def _get_default_editor_class(cls) -> Type[BaseEditor]:
        """Get default editor class
        
        Returns:
            Default editor class
        """
        from .inline import InlineEditor
        return InlineEditor
    
    @classmethod
    def _apply_additional_config(cls, editor: BaseEditor, editor_type: EditorType, config: Dict[str, Any]):
        """Apply additional configuration to editor
        
        Args:
            editor: Editor instance
            editor_type: Type of editor
            config: Configuration dictionary
        """
        # Apply type-specific configuration
        if editor_type == EditorType.CODE:
            # Enable syntax highlighting if available
            if hasattr(editor, 'enable_syntax_highlighting'):
                editor.enable_syntax_highlighting()
        elif editor_type == EditorType.MARKDOWN:
            # Enable markdown preview if available
            if hasattr(editor, 'enable_preview'):
                editor.enable_preview()
        elif editor_type == EditorType.FORMULA:
            # Enable formula validation if available
            if hasattr(editor, 'enable_formula_validation'):
                editor.enable_formula_validation()
    
    @classmethod
    def _is_code_content(cls, content: str) -> bool:
        """Check if content appears to be code
        
        Args:
            content: Content to check
            
        Returns:
            True if content appears to be code
        """
        code_indicators = [
            'def ', 'function ', 'class ', 'import ', 'from ',
            '#include', '<?php', '<!DOCTYPE', '<html>', '<script>',
            'var ', 'let ', 'const ', 'if (', 'for (', 'while (',
            '#!/', '/*', '*/', '//', '--', '/**'
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in code_indicators)
    
    @classmethod
    def _is_markdown_content(cls, content: str) -> bool:
        """Check if content appears to be markdown
        
        Args:
            content: Content to check
            
        Returns:
            True if content appears to be markdown
        """
        markdown_indicators = [
            '# ', '## ', '### ', '#### ', '##### ', '###### ',
            '* ', '- ', '+ ', '1. ', '2. ', '3. ',
            '**', '__', '*', '_', '`', '```',
            '[', '](', '![', '> ', '---', '***'
        ]
        
        lines = content.splitlines()
        indicator_count = 0
        
        for line in lines:
            stripped = line.strip()
            if any(stripped.startswith(indicator) for indicator in markdown_indicators):
                indicator_count += 1
        
        # If more than 20% of lines have markdown indicators, consider it markdown
        return len(lines) > 0 and (indicator_count / len(lines)) > 0.2
    
    @classmethod
    def _is_formula_content(cls, content: str) -> bool:
        """Check if content appears to be a mathematical formula
        
        Args:
            content: Content to check
            
        Returns:
            True if content appears to be a formula
        """
        formula_indicators = [
            '∑', '∫', '∂', '√', '∆', '∇', '∞', '≤', '≥', '≠', '±', '×', '÷',
            '²', '³', '⁴', '⁵', '⁶', '⁷', '⁸', '⁹', '⁰', '¹',
            'sin(', 'cos(', 'tan(', 'log(', 'ln(', 'exp(', 'sqrt(',
            'sum(', 'integral(', 'derivative(', 'lim(', 'max(', 'min(',
            '\\frac', '\\sqrt', '\\sum', '\\int', '\\partial', '\\Delta',
            '$', '$$', '\\(', '\\)', '\\[', '\\]'
        ]
        
        content_lower = content.lower()
        indicator_count = sum(1 for indicator in formula_indicators if indicator in content_lower)
        
        # If multiple formula indicators or specific patterns, consider it a formula
        return indicator_count >= 2 or any(pattern in content for pattern in ['$$', '\\[', '\\('])
    
    @classmethod
    def _has_rich_formatting(cls, content: str) -> bool:
        """Check if content has rich text formatting
        
        Args:
            content: Content to check
            
        Returns:
            True if content has rich formatting
        """
        html_tags = [
            '<b>', '<i>', '<u>', '<strong>', '<em>', '<span>',
            '<div>', '<p>', '<br>', '<h1>', '<h2>', '<h3>',
            '<ul>', '<ol>', '<li>', '<a>', '<img>'
        ]
        
        content_lower = content.lower()
        return any(tag in content_lower for tag in html_tags)


# Initialize factory with default editor registrations
def _initialize_factory():
    """Initialize factory with default editor types"""
    try:
        from .inline import InlineEditor
        EditorFactory.register_editor(EditorType.INLINE, InlineEditor)
        EditorFactory.register_editor(EditorType.MULTILINE, InlineEditor)
        EditorFactory.register_editor(EditorType.SINGLE_LINE, InlineEditor)
    except ImportError:
        pass
    
    # Register auto-detection functions
    EditorFactory.register_auto_detection('code', EditorFactory._is_code_content)
    EditorFactory.register_auto_detection('markdown', EditorFactory._is_markdown_content)
    EditorFactory.register_auto_detection('formula', EditorFactory._is_formula_content)
    EditorFactory.register_auto_detection('rich_text', EditorFactory._has_rich_formatting)


# Initialize factory on module import
_initialize_factory()