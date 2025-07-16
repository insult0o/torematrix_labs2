"""
Integration Layer for Merge/Split Operations Engine.

Agent 4 - Integration & Advanced Features (Issue #237)
This package provides seamless integration between all merge/split components
and advanced features for production-ready merge/split operations.
"""

from .component_integrator import (
    MergeSplitIntegrator,
    IntegrationStatus,
    IntegrationConfig,
    ComponentRegistry,
    IntegrationError,
    OperationCoordinator
)

from .api_integration import (
    MergeSplitAPI,
    APIEndpoint,
    APIResponse,
    ExternalIntegration,
    WebhookManager,
    APIAuth
)

from .plugin_loader import (
    PluginLoader,
    PluginRegistry,
    PluginInterface,
    PluginMetadata,
    PluginError,
    CustomOperationPlugin
)

from .data_exchange import (
    DataExporter,
    DataImporter,
    ExportFormat,
    ImportFormat,
    ConfigurationExporter,
    HistoryExporter
)

__all__ = [
    # Component Integration
    'MergeSplitIntegrator',
    'IntegrationStatus',
    'IntegrationConfig',
    'ComponentRegistry',
    'IntegrationError',
    'OperationCoordinator',
    
    # API Integration
    'MergeSplitAPI',
    'APIEndpoint',
    'APIResponse',
    'ExternalIntegration', 
    'WebhookManager',
    'APIAuth',
    
    # Plugin System
    'PluginLoader',
    'PluginRegistry',
    'PluginInterface',
    'PluginMetadata',
    'PluginError',
    'CustomOperationPlugin',
    
    # Data Exchange
    'DataExporter',
    'DataImporter',
    'ExportFormat',
    'ImportFormat',
    'ConfigurationExporter',
    'HistoryExporter',
]