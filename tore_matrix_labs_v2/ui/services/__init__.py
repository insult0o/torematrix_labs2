#!/usr/bin/env python3
"""
UI Services module for TORE Matrix Labs V2

This module contains UI-specific services that provide shared functionality
across the user interface, implementing clean patterns for state management,
event handling, and theming.

Services included:
- EventBus: Simplified event-driven communication between UI components
- UIStateManager: Centralized state management for UI components
- ThemeManager: Professional themes and styling management
"""

from .event_bus import EventBus, UIEvent, EventType
from .ui_state_manager import UIStateManager, UIState
from .theme_manager import ThemeManager, ThemeName

__all__ = [
    "EventBus",
    "UIEvent", 
    "EventType",
    "UIStateManager",
    "UIState",
    "ThemeManager",
    "ThemeName"
]