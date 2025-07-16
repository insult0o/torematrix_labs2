"""
API Integration for Merge/Split Operations Engine.

Agent 4 - Integration & Advanced Features (Issue #237)
Provides external system integration capabilities, REST API endpoints,
webhook management, and authentication for merge/split operations.
"""

from typing import Dict, List, Optional, Any, Callable, Union, Type
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import asyncio
import aiohttp
import json
import logging
import uuid
from datetime import datetime, timedelta
import hashlib
import hmac
import base64
from urllib.parse import urljoin, urlparse

from .....core.events import EventBus
from .....core.state import Store
from .....core.models import Element

logger = logging.getLogger(__name__)


class APIEndpointType(Enum):
    """Types of API endpoints."""
    MERGE = "merge"
    SPLIT = "split"
    BATCH = "batch"
    STATUS = "status"
    WEBHOOK = "webhook"
    AUTH = "auth"


class HTTPMethod(Enum):
    """HTTP methods for API endpoints."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


class AuthenticationType(Enum):
    """Authentication types for API access."""
    NONE = "none"
    API_KEY = "api_key"
    BEARER_TOKEN = "bearer_token"
    BASIC_AUTH = "basic_auth"
    OAUTH2 = "oauth2"
    CUSTOM = "custom"


@dataclass
class APIResponse:
    """Standard API response format."""
    success: bool
    status_code: int
    data: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class APIEndpoint:
    """Configuration for an API endpoint."""
    name: str
    endpoint_type: APIEndpointType
    path: str
    method: HTTPMethod
    description: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    auth_required: bool = True
    rate_limit: Optional[int] = None
    timeout: float = 30.0
    enabled: bool = True


@dataclass
class WebhookConfig:
    """Configuration for webhook endpoints."""
    url: str
    events: List[str]
    secret: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: float = 10.0
    retry_count: int = 3
    retry_delay: float = 1.0
    enabled: bool = True


class APIAuth:
    """Authentication manager for API access."""
    
    def __init__(self, auth_type: AuthenticationType = AuthenticationType.NONE):
        self.auth_type = auth_type
        self._credentials: Dict[str, Any] = {}
        self._tokens: Dict[str, str] = {}
        self._token_expiry: Dict[str, datetime] = {}
    
    def set_credentials(self, **credentials) -> None:
        """Set authentication credentials."""
        self._credentials.update(credentials)
    
    def set_token(self, token_type: str, token: str, expires_in: Optional[int] = None) -> None:
        """Set authentication token with optional expiry."""
        self._tokens[token_type] = token
        if expires_in:
            self._token_expiry[token_type] = datetime.now() + timedelta(seconds=expires_in)
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on auth type."""
        headers = {}
        
        if self.auth_type == AuthenticationType.API_KEY:
            api_key = self._credentials.get('api_key')
            if api_key:
                headers['X-API-Key'] = api_key
        
        elif self.auth_type == AuthenticationType.BEARER_TOKEN:
            token = self._tokens.get('access_token')
            if token and not self._is_token_expired('access_token'):
                headers['Authorization'] = f'Bearer {token}'
        
        elif self.auth_type == AuthenticationType.BASIC_AUTH:
            username = self._credentials.get('username')
            password = self._credentials.get('password')
            if username and password:
                credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()
                headers['Authorization'] = f'Basic {credentials}'
        
        return headers
    
    def _is_token_expired(self, token_type: str) -> bool:
        """Check if a token has expired."""
        expiry = self._token_expiry.get(token_type)
        return expiry is not None and datetime.now() >= expiry
    
    async def refresh_token_if_needed(self) -> bool:
        """Refresh authentication token if needed."""
        if self.auth_type == AuthenticationType.OAUTH2:
            if self._is_token_expired('access_token'):
                refresh_token = self._tokens.get('refresh_token')
                if refresh_token:
                    # Implement OAuth2 token refresh
                    return await self._refresh_oauth2_token(refresh_token)
        return True
    
    async def _refresh_oauth2_token(self, refresh_token: str) -> bool:
        """Refresh OAuth2 access token."""
        # Implementation for OAuth2 token refresh
        # This would make a request to the OAuth2 provider
        logger.info("OAuth2 token refresh not yet implemented")
        return False


class WebhookManager:
    """Manager for webhook subscriptions and delivery."""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._webhooks: Dict[str, WebhookConfig] = {}
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> None:
        """Initialize webhook manager."""
        self._session = aiohttp.ClientSession()
        
        # Subscribe to events that trigger webhooks
        await self.event_bus.subscribe('merge_completed', self._handle_webhook_event)
        await self.event_bus.subscribe('split_completed', self._handle_webhook_event)
        await self.event_bus.subscribe('batch_completed', self._handle_webhook_event)
        await self.event_bus.subscribe('operation_failed', self._handle_webhook_event)
        
        logger.info("WebhookManager initialized")
    
    def register_webhook(self, webhook_id: str, config: WebhookConfig) -> None:
        """Register a webhook subscription."""
        self._webhooks[webhook_id] = config
        logger.info(f"Registered webhook: {webhook_id} -> {config.url}")
    
    def unregister_webhook(self, webhook_id: str) -> None:
        """Unregister a webhook subscription."""
        if webhook_id in self._webhooks:
            del self._webhooks[webhook_id]
            logger.info(f"Unregistered webhook: {webhook_id}")
    
    async def _handle_webhook_event(self, event_data: Dict[str, Any]) -> None:
        """Handle events that should trigger webhooks."""
        event_type = event_data.get('event_type', 'unknown')
        
        # Find webhooks that are subscribed to this event
        relevant_webhooks = [
            (webhook_id, config) for webhook_id, config in self._webhooks.items()
            if event_type in config.events and config.enabled
        ]
        
        if relevant_webhooks:
            # Send webhooks concurrently
            tasks = [
                self._send_webhook(webhook_id, config, event_type, event_data)
                for webhook_id, config in relevant_webhooks
            ]
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _send_webhook(
        self, 
        webhook_id: str, 
        config: WebhookConfig, 
        event_type: str, 
        event_data: Dict[str, Any]
    ) -> None:
        """Send a webhook with retry logic."""
        if not self._session:
            logger.error("WebhookManager not initialized")
            return
        
        payload = {
            'event_type': event_type,
            'webhook_id': webhook_id,
            'timestamp': datetime.now().isoformat(),
            'data': event_data
        }
        
        headers = dict(config.headers)
        headers['Content-Type'] = 'application/json'
        
        # Add signature if secret is configured
        if config.secret:
            signature = self._generate_signature(json.dumps(payload), config.secret)
            headers['X-Webhook-Signature'] = signature
        
        for attempt in range(config.retry_count + 1):
            try:
                async with self._session.post(
                    config.url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=config.timeout)
                ) as response:
                    if response.status == 200:
                        logger.info(f"Webhook {webhook_id} delivered successfully")
                        return
                    else:
                        logger.warning(f"Webhook {webhook_id} failed with status {response.status}")
                        
            except Exception as e:
                logger.error(f"Webhook {webhook_id} delivery failed (attempt {attempt + 1}): {e}")
                
                if attempt < config.retry_count:
                    await asyncio.sleep(config.retry_delay * (2 ** attempt))  # Exponential backoff
        
        logger.error(f"Webhook {webhook_id} failed after {config.retry_count + 1} attempts")
    
    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for webhook payload."""
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    async def shutdown(self) -> None:
        """Shutdown webhook manager."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("WebhookManager shut down")


class ExternalIntegration:
    """Integration with external systems via HTTP APIs."""
    
    def __init__(self, base_url: str, auth: Optional[APIAuth] = None):
        self.base_url = base_url.rstrip('/')
        self.auth = auth or APIAuth()
        self._session: Optional[aiohttp.ClientSession] = None
        self._endpoints: Dict[str, APIEndpoint] = {}
    
    async def initialize(self) -> None:
        """Initialize external integration."""
        self._session = aiohttp.ClientSession()
        logger.info(f"ExternalIntegration initialized for {self.base_url}")
    
    def register_endpoint(self, endpoint: APIEndpoint) -> None:
        """Register an API endpoint."""
        self._endpoints[endpoint.name] = endpoint
        logger.info(f"Registered API endpoint: {endpoint.name} ({endpoint.method.value} {endpoint.path})")
    
    async def call_endpoint(
        self, 
        endpoint_name: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> APIResponse:
        """Call a registered API endpoint."""
        if not self._session:
            return APIResponse(
                success=False,
                status_code=0,
                error="ExternalIntegration not initialized"
            )
        
        endpoint = self._endpoints.get(endpoint_name)
        if not endpoint:
            return APIResponse(
                success=False,
                status_code=0,
                error=f"Endpoint '{endpoint_name}' not found"
            )
        
        if not endpoint.enabled:
            return APIResponse(
                success=False,
                status_code=0,
                error=f"Endpoint '{endpoint_name}' is disabled"
            )
        
        # Refresh authentication if needed
        if endpoint.auth_required:
            await self.auth.refresh_token_if_needed()
        
        # Build request
        url = urljoin(self.base_url, endpoint.path.lstrip('/'))
        request_headers = dict(endpoint.headers)
        
        if endpoint.auth_required:
            request_headers.update(self.auth.get_auth_headers())
        
        if headers:
            request_headers.update(headers)
        
        request_id = str(uuid.uuid4())
        request_headers['X-Request-ID'] = request_id
        
        try:
            # Make request
            kwargs = {
                'headers': request_headers,
                'params': params,
                'timeout': aiohttp.ClientTimeout(total=endpoint.timeout)
            }
            
            if data and endpoint.method in [HTTPMethod.POST, HTTPMethod.PUT, HTTPMethod.PATCH]:
                kwargs['json'] = data
            
            async with self._session.request(
                endpoint.method.value,
                url,
                **kwargs
            ) as response:
                response_data = None
                try:
                    response_data = await response.json()
                except Exception:
                    response_data = await response.text()
                
                return APIResponse(
                    success=response.status < 400,
                    status_code=response.status,
                    data=response_data,
                    request_id=request_id,
                    headers=dict(response.headers)
                )
                
        except asyncio.TimeoutError:
            return APIResponse(
                success=False,
                status_code=0,
                error="Request timeout",
                error_code="TIMEOUT",
                request_id=request_id
            )
        except Exception as e:
            return APIResponse(
                success=False,
                status_code=0,
                error=str(e),
                error_code="REQUEST_FAILED",
                request_id=request_id
            )
    
    async def export_merge_result(self, merge_result: Dict[str, Any]) -> APIResponse:
        """Export merge result to external system."""
        return await self.call_endpoint('merge', data=merge_result)
    
    async def export_split_result(self, split_result: Dict[str, Any]) -> APIResponse:
        """Export split result to external system."""
        return await self.call_endpoint('split', data=split_result)
    
    async def get_operation_status(self, operation_id: str) -> APIResponse:
        """Get operation status from external system."""
        return await self.call_endpoint('status', params={'operation_id': operation_id})
    
    async def shutdown(self) -> None:
        """Shutdown external integration."""
        if self._session:
            await self._session.close()
            self._session = None
        logger.info("ExternalIntegration shut down")


class MergeSplitAPI:
    """Main API integration coordinator for merge/split operations."""
    
    def __init__(self, event_bus: EventBus, store: Store):
        self.event_bus = event_bus
        self.store = store
        
        self.webhook_manager = WebhookManager(event_bus)
        self._external_integrations: Dict[str, ExternalIntegration] = {}
        self._api_endpoints: Dict[str, APIEndpoint] = {}
        
        # Setup default endpoints
        self._setup_default_endpoints()
    
    def _setup_default_endpoints(self) -> None:
        """Setup default API endpoints."""
        # Merge endpoint
        self.register_endpoint(APIEndpoint(
            name="merge",
            endpoint_type=APIEndpointType.MERGE,
            path="/api/v1/merge",
            method=HTTPMethod.POST,
            description="Merge multiple elements"
        ))
        
        # Split endpoint
        self.register_endpoint(APIEndpoint(
            name="split",
            endpoint_type=APIEndpointType.SPLIT,
            path="/api/v1/split",
            method=HTTPMethod.POST,
            description="Split an element"
        ))
        
        # Batch operations endpoint
        self.register_endpoint(APIEndpoint(
            name="batch",
            endpoint_type=APIEndpointType.BATCH,
            path="/api/v1/batch",
            method=HTTPMethod.POST,
            description="Execute batch operations"
        ))
        
        # Status endpoint
        self.register_endpoint(APIEndpoint(
            name="status",
            endpoint_type=APIEndpointType.STATUS,
            path="/api/v1/status",
            method=HTTPMethod.GET,
            description="Get operation status",
            auth_required=False
        ))
    
    async def initialize(self) -> None:
        """Initialize API integration."""
        await self.webhook_manager.initialize()
        
        # Initialize external integrations
        for integration in self._external_integrations.values():
            await integration.initialize()
        
        logger.info("MergeSplitAPI initialized")
    
    def register_endpoint(self, endpoint: APIEndpoint) -> None:
        """Register an API endpoint."""
        self._api_endpoints[endpoint.name] = endpoint
    
    def register_external_integration(self, name: str, integration: ExternalIntegration) -> None:
        """Register an external integration."""
        self._external_integrations[name] = integration
    
    def register_webhook(self, webhook_id: str, config: WebhookConfig) -> None:
        """Register a webhook."""
        self.webhook_manager.register_webhook(webhook_id, config)
    
    async def export_to_external_system(
        self, 
        system_name: str, 
        endpoint_name: str, 
        data: Dict[str, Any]
    ) -> APIResponse:
        """Export data to an external system."""
        integration = self._external_integrations.get(system_name)
        if not integration:
            return APIResponse(
                success=False,
                status_code=0,
                error=f"External system '{system_name}' not found"
            )
        
        return await integration.call_endpoint(endpoint_name, data=data)
    
    async def get_available_endpoints(self) -> List[Dict[str, Any]]:
        """Get list of available API endpoints."""
        return [
            {
                'name': endpoint.name,
                'type': endpoint.endpoint_type.value,
                'path': endpoint.path,
                'method': endpoint.method.value,
                'description': endpoint.description,
                'auth_required': endpoint.auth_required,
                'enabled': endpoint.enabled
            }
            for endpoint in self._api_endpoints.values()
        ]
    
    async def shutdown(self) -> None:
        """Shutdown API integration."""
        await self.webhook_manager.shutdown()
        
        for integration in self._external_integrations.values():
            await integration.shutdown()
        
        logger.info("MergeSplitAPI shut down")


# Convenience factory functions
def create_api_auth(auth_type: AuthenticationType, **credentials) -> APIAuth:
    """Create and configure API authentication."""
    auth = APIAuth(auth_type)
    auth.set_credentials(**credentials)
    return auth


async def create_merge_split_api(event_bus: EventBus, store: Store) -> MergeSplitAPI:
    """Create and initialize merge/split API."""
    api = MergeSplitAPI(event_bus, store)
    await api.initialize()
    return api