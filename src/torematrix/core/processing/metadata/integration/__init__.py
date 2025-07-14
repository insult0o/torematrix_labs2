"""Integration layer for metadata extraction system.

This package provides integration components to connect the metadata extraction
engine with the broader TORE Matrix Labs processing pipeline, including API
endpoints, WebSocket support, and system monitoring.
"""

from .pipeline_integration import MetadataPipelineIntegration
from .storage_integration import MetadataStorageIntegration
from .api_integration import MetadataAPIIntegration
from .websocket_integration import MetadataWebSocketManager

__all__ = [
    'MetadataPipelineIntegration',
    'MetadataStorageIntegration', 
    'MetadataAPIIntegration',
    'MetadataWebSocketManager'
]