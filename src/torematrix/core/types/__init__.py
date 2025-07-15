"""Advanced Type Management System

This package provides advanced type management features including:
- Custom type creation with visual builder
- Plugin architecture for extensible types
- Import/export functionality for type definitions
- AI-powered type recommendations
- Advanced search and discovery
- Complete system integration
"""

from .custom_types import CustomTypeBuilder, CustomTypeDefinition, CustomTypeResult
from .plugin_system import TypePluginManager, TypePlugin, PluginCapabilities
from .import_export import TypeDefinitionImportExport, ExportResult, ImportResult
from .recommendations import TypeRecommendationEngine, TypeRecommendation, ContentAnalysis
from .api_integration import TypeManagementAPI, APIResponse, APIError
from .documentation import TypeDocumentationGenerator, DocumentationFormat
from .search_engine import AdvancedTypeSearch, SearchResult, SearchQuery
from .system_integration import TypeSystemIntegrator, IntegrationResult

__all__ = [
    # Core classes
    'CustomTypeBuilder',
    'TypePluginManager', 
    'TypeDefinitionImportExport',
    'TypeRecommendationEngine',
    'TypeManagementAPI',
    'TypeDocumentationGenerator',
    'AdvancedTypeSearch',
    'TypeSystemIntegrator',
    
    # Data classes
    'CustomTypeDefinition',
    'CustomTypeResult',
    'TypePlugin',
    'PluginCapabilities',
    'ExportResult',
    'ImportResult',
    'TypeRecommendation',
    'ContentAnalysis',
    'APIResponse',
    'APIError',
    'DocumentationFormat',
    'SearchResult',
    'SearchQuery',
    'IntegrationResult',
]

# Version info
__version__ = "1.0.0"
__author__ = "Agent 4"
__description__ = "Advanced Type Management Features & Integration"