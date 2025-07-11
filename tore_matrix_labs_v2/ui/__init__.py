#!/usr/bin/env python3
"""
UI module for TORE Matrix Labs V2

This module contains the simplified, modern UI implementation that consolidates
the complex widget hierarchy from the original codebase into clean, focused
components with proper separation of concerns.

Key improvements:
- Unified validation widget replaces multiple scattered widgets
- Event bus architecture for clean component communication
- Centralized state management
- Modern PyQt5 patterns with dependency injection
- Professional themes and responsive layouts
- Bug-free coordinate handling and synchronization

Components included:
- Views: Pure UI components (presentation layer)
- Controllers: UI logic and interaction handling
- Components: Reusable UI building blocks
- Services: UI-specific services (state management, events, themes)
"""

from .views import *
from .controllers import *
from .components import *
from .services import *

__all__ = [
    # Views
    "MainWindowV2",
    "UnifiedValidationView",
    "DocumentViewerV2",
    "ProjectManagerV2",
    
    # Controllers
    "ValidationController",
    "DocumentController", 
    "ProjectController",
    
    # Components
    "CoordinateMapper",
    "HighlightingRenderer",
    "AreaSelector",
    
    # Services
    "EventBus",
    "UIStateManager",
    "ThemeManager"
]