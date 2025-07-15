"""Inline editing components module

This module provides comprehensive inline editing functionality for document elements
with support for multiple editor types, validation, auto-save, and performance optimization.
"""

from .base import BaseEditor, EditorConfig
from .inline import InlineEditor
from .factory import EditorFactory, EditorType
from .integration import ElementEditorBridge, ElementListIntegration
from .accessibility import AccessibilityManager
from .autosave import AutoSaveManager
from .markdown import MarkdownPreview

# Enhanced editors
try:
    from .enhanced import EnhancedTextEdit, SpellChecker, TextValidator
    from .diff import DiffViewer, DiffCalculator
    from .complete_system import CompleteInlineEditor, InlineEditingSystem
except ImportError:
    # Fallback for partial implementations
    pass

__all__ = [
    # Core interfaces
    'BaseEditor',
    'EditorConfig',
    
    # Basic editors
    'InlineEditor',
    
    # Factory and types
    'EditorFactory',
    'EditorType',
    
    # Integration
    'ElementEditorBridge',
    'ElementListIntegration',
    
    # Features
    'AccessibilityManager',
    'AutoSaveManager',
    'MarkdownPreview',
    
    # Enhanced components (if available)
    'EnhancedTextEdit',
    'SpellChecker', 
    'TextValidator',
    'DiffViewer',
    'DiffCalculator',
    'CompleteInlineEditor',
    'InlineEditingSystem'
]

# Version information
__version__ = '1.0.0'
__author__ = 'TORE Matrix Labs'
__description__ = 'Comprehensive inline editing system for document processing'