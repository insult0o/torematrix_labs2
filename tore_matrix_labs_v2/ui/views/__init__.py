#!/usr/bin/env python3
"""
Views module for TORE Matrix Labs V2 UI

This module contains the pure UI view components that replace the complex
widget hierarchy from the original codebase. Views are responsible only
for presentation and delegate all logic to controllers.

Key improvements:
- Pure presentation layer (no business logic)
- Clean separation of concerns
- Simplified widget hierarchy
- Consistent styling and theming
- Performance optimization

Views included:
- MainWindowV2: Streamlined main application window
- UnifiedValidationView: Single validation interface replacing multiple widgets
- DocumentViewerV2: Enhanced document viewing with coordinate mapping
- ProjectManagerV2: Simplified project management interface
"""

from .main_window_v2 import MainWindowV2
from .unified_validation_view import UnifiedValidationView
from .document_viewer_v2 import DocumentViewerV2  
from .project_manager_v2 import ProjectManagerV2

__all__ = [
    "MainWindowV2",
    "UnifiedValidationView",
    "DocumentViewerV2",
    "ProjectManagerV2"
]