#!/usr/bin/env python3
"""
Enhanced Event System for TORE Matrix Labs V1

This module provides V2-style event architecture for the V1 system,
enhancing the existing PyQt signal system with modern event patterns
while maintaining full backward compatibility.

Components:
- UnifiedEventBus: Modern event bus with type safety
- SignalBridge: Bridge between V1 PyQt signals and V2 events
- GlobalSignalProcessor: Centralized signal processing and coordination
- EventTypes: Type-safe event definitions
"""

from .unified_event_bus import UnifiedEventBus, V1EventBus
from .signal_bridge import SignalBridge, SignalEventAdapter
from .global_signal_processor import GlobalSignalProcessor
from .event_types_v1 import EventTypeV1, V1EventData, EventPriority

__all__ = [
    'UnifiedEventBus',
    'V1EventBus', 
    'SignalBridge',
    'SignalEventAdapter',
    'GlobalSignalProcessor',
    'EventTypeV1',
    'V1EventData',
    'EventPriority'
]