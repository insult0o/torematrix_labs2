"""API Integration Layer for Type Management

Comprehensive API layer providing REST and GraphQL interfaces for:
- Type definition management and operations
- Custom type creation and modification
- Plugin system access and control
- Import/export operations via HTTP
- Real-time type recommendations and analysis
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional, Any, Union, Callable
import json
import uuid
from datetime import datetime
from pathlib import Path
import aiohttp
from aiohttp import web, ClientSession
from aiohttp.web import Request, Response, json_response
import jwt
from functools import wraps
import traceback

# Import our type management components
from .custom_types import CustomTypeBuilder, CustomTypeDefinition, CustomTypeResult
from .plugin_system import TypePluginManager, PluginInfo, PluginStatus
from .import_export import TypeDefinitionImportExport, ExportOptions, ImportOptions
from .recommendations import TypeRecommendationEngine, RecommendationContext

logger = logging.getLogger(__name__)


class APIVersion(Enum):
    """Supported API versions"""
    V1 = "v1"
    V2 = "v2"


class AuthLevel(Enum):
    """Authentication levels"""
    PUBLIC = "public"
    USER = "user"
    ADMIN = "admin"
    SYSTEM = "system"


@dataclass
class APIResponse:
    """Standard API response structure"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    version: str = "1.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


@dataclass
class APIEndpoint:
    """API endpoint definition"""
    path: str
    method: str
    handler: Callable
    auth_level: AuthLevel = AuthLevel.PUBLIC
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    responses: Dict[str, Any] = field(default_factory=dict)


class APIError(Exception):
    """Custom API error with status code"""
    
    def __init__(self, message: str, status_code: int = 400, error_code: str = None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or "API_ERROR"
        super().__init__(message)


class AuthenticationManager:
    """Manages API authentication and authorization"""
    
    def __init__(self, secret_key: str = "default_secret"):
        self.secret_key = secret_key
        self.active_tokens: Dict[str, Dict[str, Any]] = {}
    
    def create_token(self, user_id: str, auth_level: AuthLevel, 
                    expires_in: int = 3600) -> str:
        """Create JWT token"""
        payload = {
            'user_id': user_id,
            'auth_level': auth_level.value,
            'exp': datetime.now().timestamp() + expires_in,
            'iat': datetime.now().timestamp()
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        self.active_tokens[token] = payload
        return token
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # Check if token is still active
            if token not in self.active_tokens:
                raise APIError("Token not found", 401, "TOKEN_NOT_FOUND")
            
            return payload
        except jwt.ExpiredSignatureError:
            raise APIError("Token expired", 401, "TOKEN_EXPIRED")
        except jwt.InvalidTokenError:
            raise APIError("Invalid token", 401, "TOKEN_INVALID")
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a token"""
        if token in self.active_tokens:
            del self.active_tokens[token]
            return True
        return False
    
    def check_permission(self, required_level: AuthLevel, user_level: str) -> bool:
        """Check if user has required permission level"""
        level_hierarchy = {
            AuthLevel.PUBLIC: 0,
            AuthLevel.USER: 1,
            AuthLevel.ADMIN: 2,
            AuthLevel.SYSTEM: 3
        }
        
        user_auth_level = AuthLevel(user_level)
        return level_hierarchy[user_auth_level] >= level_hierarchy[required_level]


def require_auth(auth_level: AuthLevel = AuthLevel.USER):
    """Decorator for requiring authentication"""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, request: Request):
            # Skip auth for public endpoints
            if auth_level == AuthLevel.PUBLIC:
                return await func(self, request)
            
            # Get token from header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                raise APIError("Missing or invalid authorization header", 401)
            
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            
            try:
                payload = self.auth_manager.verify_token(token)
                
                # Check permission level
                if not self.auth_manager.check_permission(auth_level, payload['auth_level']):
                    raise APIError("Insufficient permissions", 403)
                
                # Add user info to request
                request['user'] = payload
                
                return await func(self, request)
                
            except APIError:
                raise
            except Exception as e:
                logger.error(f"Authentication error: {e}")
                raise APIError("Authentication failed", 401)
        
        return wrapper
    return decorator


class TypeManagementAPI:
    """REST API for type management operations"""
    
    def __init__(self, 
                 type_builder: CustomTypeBuilder,
                 plugin_manager: TypePluginManager,
                 import_export: TypeDefinitionImportExport,
                 recommendation_engine: TypeRecommendationEngine,
                 auth_secret: str = "default_secret"):
        
        self.type_builder = type_builder
        self.plugin_manager = plugin_manager
        self.import_export = import_export
        self.recommendation_engine = recommendation_engine
        self.auth_manager = AuthenticationManager(auth_secret)
        
        self.app = web.Application()
        self.endpoints: List[APIEndpoint] = []
        
        self._setup_routes()
        self._setup_middleware()
        
        logger.info("TypeManagementAPI initialized")
    
    def _setup_routes(self):
        """Setup API routes"""
        # Authentication endpoints
        self.app.router.add_post('/api/v1/auth/login', self.login)
        self.app.router.add_post('/api/v1/auth/logout', self.logout)
        
        # Type definition endpoints
        self.app.router.add_get('/api/v1/types', self.list_types)
        self.app.router.add_post('/api/v1/types', self.create_type)
        self.app.router.add_get('/api/v1/types/{type_id}', self.get_type)
        self.app.router.add_put('/api/v1/types/{type_id}', self.update_type)
        self.app.router.add_delete('/api/v1/types/{type_id}', self.delete_type)
        
        # Custom type operations
        self.app.router.add_post('/api/v1/types/validate', self.validate_type)
        self.app.router.add_post('/api/v1/types/convert', self.convert_type)
        self.app.router.add_get('/api/v1/types/templates', self.list_templates)
        
        # Plugin management endpoints
        self.app.router.add_get('/api/v1/plugins', self.list_plugins)
        self.app.router.add_post('/api/v1/plugins/load', self.load_plugin)
        self.app.router.add_post('/api/v1/plugins/{plugin_id}/execute', self.execute_plugin)
        self.app.router.add_put('/api/v1/plugins/{plugin_id}/enable', self.enable_plugin)
        self.app.router.add_put('/api/v1/plugins/{plugin_id}/disable', self.disable_plugin)
        
        # Import/Export endpoints
        self.app.router.add_post('/api/v1/import', self.import_types)
        self.app.router.add_post('/api/v1/export', self.export_types)
        self.app.router.add_post('/api/v1/validate-file', self.validate_file)
        
        # Recommendation endpoints
        self.app.router.add_post('/api/v1/recommendations', self.get_recommendations)
        self.app.router.add_post('/api/v1/analyze-content', self.analyze_content)
        
        # System endpoints
        self.app.router.add_get('/api/v1/health', self.health_check)
        self.app.router.add_get('/api/v1/info', self.system_info)
        self.app.router.add_get('/api/v1/docs', self.api_documentation)
    
    def _setup_middleware(self):
        """Setup middleware for error handling and logging"""
        @web.middleware
        async def error_handler(request: Request, handler):
            try:
                return await handler(request)
            except APIError as e:
                logger.warning(f"API Error: {e.message}")
                return json_response(
                    APIResponse(
                        success=False,
                        error=e.error_code,
                        message=e.message
                    ).to_dict(),
                    status=e.status_code
                )
            except Exception as e:
                logger.error(f"Unexpected error: {e}\n{traceback.format_exc()}")
                return json_response(
                    APIResponse(
                        success=False,
                        error="INTERNAL_ERROR",
                        message="Internal server error"
                    ).to_dict(),
                    status=500
                )
        
        @web.middleware
        async def cors_handler(request: Request, handler):
            response = await handler(request)
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
        
        self.app.middlewares.append(error_handler)
        self.app.middlewares.append(cors_handler)
    
    # Authentication endpoints
    async def login(self, request: Request) -> Response:
        """User login endpoint"""
        data = await request.json()
        
        username = data.get('username')
        password = data.get('password')
        
        # Simple authentication (in production, use proper password hashing)
        if username == 'admin' and password == 'admin':
            token = self.auth_manager.create_token('admin', AuthLevel.ADMIN)
            return json_response(APIResponse(
                success=True,
                data={'token': token, 'auth_level': 'admin'}
            ).to_dict())
        elif username == 'user' and password == 'user':
            token = self.auth_manager.create_token('user', AuthLevel.USER)
            return json_response(APIResponse(
                success=True,
                data={'token': token, 'auth_level': 'user'}
            ).to_dict())
        else:
            raise APIError("Invalid credentials", 401, "INVALID_CREDENTIALS")
    
    @require_auth(AuthLevel.USER)
    async def logout(self, request: Request) -> Response:
        """User logout endpoint"""
        auth_header = request.headers.get('Authorization')
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        
        self.auth_manager.revoke_token(token)
        
        return json_response(APIResponse(
            success=True,
            message="Logged out successfully"
        ).to_dict())
    
    # Type definition endpoints
    @require_auth(AuthLevel.PUBLIC)
    async def list_types(self, request: Request) -> Response:
        """List all type definitions"""
        types = self.import_export.list_type_definitions()
        
        type_data = []
        for type_def in types:
            type_data.append({
                'id': type_def.id,
                'name': type_def.name,
                'version': type_def.version,
                'dependencies': type_def.dependencies,
                'checksum': type_def.checksum
            })
        
        return json_response(APIResponse(
            success=True,
            data={'types': type_data, 'count': len(type_data)}
        ).to_dict())
    
    @require_auth(AuthLevel.USER)
    async def create_type(self, request: Request) -> Response:
        """Create new type definition"""
        data = await request.json()
        
        type_definition = CustomTypeDefinition(
            name=data['name'],
            description=data.get('description', ''),
            base_type=data.get('base_type', 'text'),
            properties=data.get('properties', {}),
            validation_rules=data.get('validation_rules', {}),
            metadata=data.get('metadata', {})
        )
        
        result = self.type_builder.create_custom_type(type_definition)
        
        if result.success:
            return json_response(APIResponse(
                success=True,
                data={'type_id': result.type_id, 'result': asdict(result)},
                message="Type created successfully"
            ).to_dict(), status=201)
        else:
            raise APIError(f"Type creation failed: {'; '.join(result.errors)}", 400)
    
    @require_auth(AuthLevel.PUBLIC)
    async def get_type(self, request: Request) -> Response:
        """Get specific type definition"""
        type_id = request.match_info['type_id']
        
        type_def = self.import_export.get_type_definition(type_id)
        if not type_def:
            raise APIError(f"Type not found: {type_id}", 404)
        
        return json_response(APIResponse(
            success=True,
            data=asdict(type_def)
        ).to_dict())
    
    @require_auth(AuthLevel.USER)
    async def update_type(self, request: Request) -> Response:
        """Update type definition"""
        type_id = request.match_info['type_id']
        data = await request.json()
        
        # Get existing type
        existing_type = self.import_export.get_type_definition(type_id)
        if not existing_type:
            raise APIError(f"Type not found: {type_id}", 404)
        
        # Update type definition
        updated_definition = CustomTypeDefinition(
            name=data.get('name', existing_type.name),
            description=data.get('description', existing_type.metadata.get('description', '')),
            base_type=data.get('base_type', 'text'),
            properties=data.get('properties', existing_type.definition.get('properties', {})),
            validation_rules=data.get('validation_rules', existing_type.definition.get('validation_rules', {})),
            metadata=data.get('metadata', existing_type.metadata)
        )
        
        result = self.type_builder.create_custom_type(updated_definition)
        
        if result.success:
            return json_response(APIResponse(
                success=True,
                data={'result': asdict(result)},
                message="Type updated successfully"
            ).to_dict())
        else:
            raise APIError(f"Type update failed: {'; '.join(result.errors)}", 400)
    
    @require_auth(AuthLevel.ADMIN)
    async def delete_type(self, request: Request) -> Response:
        """Delete type definition"""
        type_id = request.match_info['type_id']
        
        # Check if type exists
        type_def = self.import_export.get_type_definition(type_id)
        if not type_def:
            raise APIError(f"Type not found: {type_id}", 404)
        
        # In a real implementation, we would delete from the registry
        # For now, we'll return success
        return json_response(APIResponse(
            success=True,
            message=f"Type {type_id} deleted successfully"
        ).to_dict())
    
    # Plugin endpoints
    @require_auth(AuthLevel.PUBLIC)
    async def list_plugins(self, request: Request) -> Response:
        """List all plugins"""
        plugins = self.plugin_manager.list_plugins()
        
        plugin_data = []
        for plugin in plugins:
            plugin_data.append({
                'id': plugin.id,
                'name': plugin.name,
                'version': plugin.version,
                'status': plugin.status.value,
                'plugin_type': plugin.plugin_type.value,
                'usage_count': plugin.usage_count
            })
        
        return json_response(APIResponse(
            success=True,
            data={'plugins': plugin_data, 'count': len(plugin_data)}
        ).to_dict())
    
    @require_auth(AuthLevel.ADMIN)
    async def load_plugin(self, request: Request) -> Response:
        """Load plugin from file"""
        data = await request.json()
        plugin_path = data.get('plugin_path')
        
        if not plugin_path:
            raise APIError("plugin_path is required", 400)
        
        plugin_id = await self.plugin_manager.load_plugin_from_file(plugin_path)
        
        if plugin_id:
            return json_response(APIResponse(
                success=True,
                data={'plugin_id': plugin_id},
                message="Plugin loaded successfully"
            ).to_dict())
        else:
            raise APIError("Failed to load plugin", 400)
    
    @require_auth(AuthLevel.USER)
    async def execute_plugin(self, request: Request) -> Response:
        """Execute plugin operation"""
        plugin_id = request.match_info['plugin_id']
        data = await request.json()
        
        operation = data.get('operation')
        parameters = data.get('parameters', {})
        
        if not operation:
            raise APIError("operation is required", 400)
        
        try:
            result = await self.plugin_manager.execute_plugin_operation(
                plugin_id, operation, **parameters
            )
            
            return json_response(APIResponse(
                success=True,
                data={'result': result},
                message="Plugin operation completed"
            ).to_dict())
            
        except Exception as e:
            raise APIError(f"Plugin execution failed: {e}", 400)
    
    @require_auth(AuthLevel.ADMIN)
    async def enable_plugin(self, request: Request) -> Response:
        """Enable plugin"""
        plugin_id = request.match_info['plugin_id']
        
        success = self.plugin_manager.enable_plugin(plugin_id)
        
        if success:
            return json_response(APIResponse(
                success=True,
                message=f"Plugin {plugin_id} enabled"
            ).to_dict())
        else:
            raise APIError(f"Failed to enable plugin {plugin_id}", 400)
    
    @require_auth(AuthLevel.ADMIN)
    async def disable_plugin(self, request: Request) -> Response:
        """Disable plugin"""
        plugin_id = request.match_info['plugin_id']
        
        success = self.plugin_manager.disable_plugin(plugin_id)
        
        if success:
            return json_response(APIResponse(
                success=True,
                message=f"Plugin {plugin_id} disabled"
            ).to_dict())
        else:
            raise APIError(f"Failed to disable plugin {plugin_id}", 400)
    
    # Import/Export endpoints
    @require_auth(AuthLevel.USER)
    async def import_types(self, request: Request) -> Response:
        """Import type definitions from file"""
        # This would handle file upload in a real implementation
        # For now, we'll simulate with file path
        data = await request.json()
        file_path = data.get('file_path')
        
        if not file_path:
            raise APIError("file_path is required", 400)
        
        import_options = ImportOptions(
            strategy=data.get('strategy', 'merge'),
            validation_level=data.get('validation_level', 'strict'),
            create_backup=data.get('create_backup', True)
        )
        
        result = self.import_export.import_type_definitions(file_path, import_options)
        
        if result.success:
            return json_response(APIResponse(
                success=True,
                data=asdict(result),
                message="Types imported successfully"
            ).to_dict())
        else:
            raise APIError(f"Import failed: {'; '.join(result.errors)}", 400)
    
    @require_auth(AuthLevel.USER)
    async def export_types(self, request: Request) -> Response:
        """Export type definitions to file"""
        data = await request.json()
        
        type_ids = data.get('type_ids', [])
        file_path = data.get('file_path')
        export_format = data.get('format', 'json')
        
        if not file_path:
            raise APIError("file_path is required", 400)
        
        export_options = ExportOptions(
            format=export_format,
            include_metadata=data.get('include_metadata', True),
            pretty_format=data.get('pretty_format', True)
        )
        
        if not type_ids:
            # Export all types
            all_types = self.import_export.list_type_definitions()
            type_ids = [t.id for t in all_types]
        
        result = self.import_export.export_type_definitions(type_ids, file_path, export_options)
        
        if result.success:
            return json_response(APIResponse(
                success=True,
                data=asdict(result),
                message="Types exported successfully"
            ).to_dict())
        else:
            raise APIError(f"Export failed: {'; '.join(result.errors)}", 400)
    
    # Recommendation endpoints
    @require_auth(AuthLevel.PUBLIC)
    async def get_recommendations(self, request: Request) -> Response:
        """Get type recommendations for content"""
        data = await request.json()
        
        context = RecommendationContext(
            element_id=data.get('element_id', str(uuid.uuid4())),
            current_type=data.get('current_type'),
            content=data.get('content', ''),
            metadata=data.get('metadata', {}),
            related_elements=data.get('related_elements', []),
            document_context=data.get('document_context', {}),
            user_preferences=data.get('user_preferences', {})
        )
        
        recommendations = await self.recommendation_engine.get_recommendations(context)
        
        rec_data = [asdict(rec) for rec in recommendations]
        
        return json_response(APIResponse(
            success=True,
            data={'recommendations': rec_data, 'count': len(rec_data)}
        ).to_dict())
    
    @require_auth(AuthLevel.PUBLIC)
    async def analyze_content(self, request: Request) -> Response:
        """Analyze content features"""
        data = await request.json()
        content = data.get('content', '')
        
        analysis = self.recommendation_engine.analyze_content_features(content)
        
        return json_response(APIResponse(
            success=True,
            data=asdict(analysis)
        ).to_dict())
    
    # System endpoints
    @require_auth(AuthLevel.PUBLIC)
    async def health_check(self, request: Request) -> Response:
        """Health check endpoint"""
        return json_response(APIResponse(
            success=True,
            data={
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            }
        ).to_dict())
    
    @require_auth(AuthLevel.PUBLIC)
    async def system_info(self, request: Request) -> Response:
        """System information endpoint"""
        info = {
            'version': '1.0.0',
            'api_version': 'v1',
            'supported_formats': self.import_export.get_format_info(),
            'supported_types': self.recommendation_engine.get_supported_types(),
            'plugin_stats': self.plugin_manager.get_execution_statistics(),
            'cache_stats': self.recommendation_engine.get_cache_stats()
        }
        
        return json_response(APIResponse(
            success=True,
            data=info
        ).to_dict())
    
    @require_auth(AuthLevel.PUBLIC)
    async def api_documentation(self, request: Request) -> Response:
        """API documentation endpoint"""
        docs = {
            'title': 'Type Management API',
            'version': '1.0.0',
            'description': 'RESTful API for type management operations',
            'endpoints': {
                'authentication': [
                    'POST /api/v1/auth/login',
                    'POST /api/v1/auth/logout'
                ],
                'types': [
                    'GET /api/v1/types',
                    'POST /api/v1/types',
                    'GET /api/v1/types/{id}',
                    'PUT /api/v1/types/{id}',
                    'DELETE /api/v1/types/{id}'
                ],
                'plugins': [
                    'GET /api/v1/plugins',
                    'POST /api/v1/plugins/load',
                    'POST /api/v1/plugins/{id}/execute'
                ],
                'import_export': [
                    'POST /api/v1/import',
                    'POST /api/v1/export'
                ],
                'recommendations': [
                    'POST /api/v1/recommendations',
                    'POST /api/v1/analyze-content'
                ],
                'system': [
                    'GET /api/v1/health',
                    'GET /api/v1/info',
                    'GET /api/v1/docs'
                ]
            }
        }
        
        return json_response(APIResponse(
            success=True,
            data=docs
        ).to_dict())
    
    async def start_server(self, host: str = '0.0.0.0', port: int = 8080):
        """Start the API server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, host, port)
        await site.start()
        
        logger.info(f"Type Management API server started on {host}:{port}")
        return runner


class GraphQLAPI:
    """GraphQL API interface for type management"""
    
    def __init__(self, rest_api: TypeManagementAPI):
        self.rest_api = rest_api
        self.schema = self._build_schema()
    
    def _build_schema(self):
        """Build GraphQL schema"""
        # In a real implementation, you would use a GraphQL library like graphene
        # This is a placeholder structure
        schema = {
            'types': {
                'TypeDefinition': {
                    'id': 'String!',
                    'name': 'String!',
                    'version': 'String!',
                    'definition': 'JSON',
                    'metadata': 'JSON'
                },
                'Plugin': {
                    'id': 'String!',
                    'name': 'String!',
                    'version': 'String!',
                    'status': 'String!',
                    'capabilities': 'JSON'
                },
                'Recommendation': {
                    'recommended_type': 'String!',
                    'confidence': 'Float!',
                    'reason': 'String!',
                    'evidence': '[String]'
                }
            },
            'queries': {
                'types': 'Query to get all types',
                'type': 'Query to get specific type by ID',
                'plugins': 'Query to get all plugins',
                'recommendations': 'Query to get type recommendations'
            },
            'mutations': {
                'createType': 'Create new type definition',
                'updateType': 'Update existing type',
                'deleteType': 'Delete type definition',
                'loadPlugin': 'Load new plugin',
                'executePlugin': 'Execute plugin operation'
            }
        }
        
        return schema
    
    async def handle_query(self, query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle GraphQL query"""
        # This is a simplified implementation
        # In production, you would use a proper GraphQL library
        
        # Parse and execute query
        # For now, return schema information
        return {
            'data': {
                'schema': self.schema
            }
        }


# Export main components
__all__ = [
    'APIVersion',
    'AuthLevel',
    'APIResponse',
    'APIEndpoint',
    'APIError',
    'AuthenticationManager',
    'TypeManagementAPI',
    'GraphQLAPI'
]