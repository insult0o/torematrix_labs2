"""Inline Editing System Package

A comprehensive, production-ready framework for enabling seamless inline editing
of document elements with accessibility, performance, and extensibility.

Key Features:
- Element list integration bridge for seamless editing workflow
- Comprehensive accessibility support with WCAG compliance
- Advanced error handling and recovery with multiple strategies
- Complete system integration with monitoring and configuration
- Production-ready with performance optimization and testing

Usage:
    from src.torematrix.ui.components.editors import create_inline_editing_system
    
    # Create the system
    editing_system = create_inline_editing_system()
    
    # Set up editor factory
    editing_system.set_editor_factory(my_editor_factory)
    
    # Request editing
    editing_system.request_edit("element_id", "text", "current_value")
"""

# Core base classes and interfaces
from .base import BaseEditor, EditorConfig, EditorState

# Integration components
from .integration import ElementEditorBridge, EditRequest

# Accessibility support
from .accessibility import AccessibilityManager, AccessibilitySettings

# Error handling and recovery
from .recovery import (
    EditorErrorHandler, ErrorRecord, ErrorSeverity, 
    ErrorCategory, RecoveryStrategy
)

# Complete system integration
from .complete_system import (
    InlineEditingSystem, SystemConfiguration, SystemMetrics,
    SystemStatusWidget, create_inline_editing_system
)

# Public API exports
__all__ = [
    # Base classes
    'BaseEditor',
    'EditorConfig', 
    'EditorState',
    
    # Integration
    'ElementEditorBridge',
    'EditRequest',
    
    # Accessibility
    'AccessibilityManager',
    'AccessibilitySettings',
    
    # Error handling
    'EditorErrorHandler',
    'ErrorRecord',
    'ErrorSeverity',
    'ErrorCategory', 
    'RecoveryStrategy',
    
    # Complete system
    'InlineEditingSystem',
    'SystemConfiguration',
    'SystemMetrics',
    'SystemStatusWidget',
    'create_inline_editing_system'
]

# Version information
__version__ = '1.0.0'
__author__ = 'TORE Matrix Labs'
__description__ = 'Production-ready inline editing system with accessibility and error recovery'