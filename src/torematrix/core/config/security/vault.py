"""
HashiCorp Vault integration for secret management.

This module provides integration with HashiCorp Vault for enterprise-grade
secret management and storage.
"""

from typing import Dict, Any, Optional, List
import os
import requests
from pathlib import Path
from .secrets import SecretProvider
from ..exceptions import ConfigurationError


class VaultSecretProvider(SecretProvider):
    """
    HashiCorp Vault secret provider.
    
    Supports authentication via:
    - Token
    - AppRole
    - Kubernetes
    - Environment variables
    """
    
    def __init__(
        self,
        vault_url: str,
        mount_path: str = "secret",
        token: Optional[str] = None,
        role_id: Optional[str] = None,
        secret_id: Optional[str] = None,
        namespace: Optional[str] = None,
        verify_ssl: bool = True
    ):
        """
        Initialize Vault provider.
        
        Args:
            vault_url: Vault server URL
            mount_path: Secret mount path
            token: Vault token for authentication
            role_id: AppRole role ID
            secret_id: AppRole secret ID
            namespace: Vault namespace (for Enterprise)
            verify_ssl: Whether to verify SSL certificates
        """
        self.vault_url = vault_url.rstrip('/')
        self.mount_path = mount_path
        self.namespace = namespace
        self.verify_ssl = verify_ssl
        self.token: Optional[str] = None
        
        # Set up session
        self.session = requests.Session()
        if not verify_ssl:
            self.session.verify = False
        
        # Authenticate
        if token:
            self.token = token
        elif role_id and secret_id:
            self._authenticate_approle(role_id, secret_id)
        else:
            self._authenticate_from_env()
    
    def _authenticate_from_env(self) -> None:
        """Authenticate using environment variables."""
        # Try token from environment
        token = os.getenv('VAULT_TOKEN')
        if token:
            self.token = token
            return
        
        # Try AppRole from environment
        role_id = os.getenv('VAULT_ROLE_ID')
        secret_id = os.getenv('VAULT_SECRET_ID')
        if role_id and secret_id:
            self._authenticate_approle(role_id, secret_id)
            return
        
        # Try token file
        token_file = Path.home() / '.vault-token'
        if token_file.exists():
            self.token = token_file.read_text().strip()
            return
        
        raise ConfigurationError("No Vault authentication method available")
    
    def _authenticate_approle(self, role_id: str, secret_id: str) -> None:
        """Authenticate using AppRole method."""
        url = f"{self.vault_url}/v1/auth/approle/login"
        headers = self._get_headers()
        
        data = {
            'role_id': role_id,
            'secret_id': secret_id
        }
        
        try:
            response = self.session.post(url, json=data, headers=headers)
            response.raise_for_status()
            
            auth_data = response.json()
            self.token = auth_data['auth']['client_token']
        except requests.RequestException as e:
            raise ConfigurationError(f"AppRole authentication failed: {e}")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['X-Vault-Token'] = self.token
        
        if self.namespace:
            headers['X-Vault-Namespace'] = self.namespace
        
        return headers
    
    def _make_request(self, method: str, path: str, **kwargs) -> requests.Response:
        """Make authenticated request to Vault."""
        url = f"{self.vault_url}/v1/{path}"
        headers = self._get_headers()
        
        try:
            response = self.session.request(
                method, url, headers=headers, **kwargs
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            raise ConfigurationError(f"Vault request failed: {e}")
    
    def get_secret(self, key: str) -> Optional[str]:
        """
        Get secret from Vault.
        
        Args:
            key: Secret path (can include nested keys with dots)
        
        Returns:
            Secret value or None if not found
        """
        # Parse key path
        if '.' in key:
            secret_path, field = key.rsplit('.', 1)
        else:
            secret_path = key
            field = 'value'  # Default field name
        
        # Build Vault path
        vault_path = f"{self.mount_path}/data/{secret_path}"
        
        try:
            response = self._make_request('GET', vault_path)
            data = response.json()
            
            # Extract the secret data
            secret_data = data.get('data', {}).get('data', {})
            return secret_data.get(field)
        
        except ConfigurationError:
            # Secret not found
            return None
    
    def set_secret(self, key: str, value: str) -> None:
        """
        Set secret in Vault.
        
        Args:
            key: Secret path
            value: Secret value
        """
        # Parse key path
        if '.' in key:
            secret_path, field = key.rsplit('.', 1)
        else:
            secret_path = key
            field = 'value'
        
        # Build Vault path
        vault_path = f"{self.mount_path}/data/{secret_path}"
        
        # Get existing secret data to preserve other fields
        existing_data = {}
        try:
            response = self._make_request('GET', vault_path)
            existing_data = response.json().get('data', {}).get('data', {})
        except ConfigurationError:
            # Secret doesn't exist yet
            pass
        
        # Update the specific field
        existing_data[field] = value
        
        # Write the secret
        data = {'data': existing_data}
        self._make_request('POST', vault_path, json=data)
    
    def delete_secret(self, key: str) -> bool:
        """
        Delete secret from Vault.
        
        Args:
            key: Secret path
        
        Returns:
            True if deleted, False if not found
        """
        # Parse key path
        if '.' in key:
            secret_path, field = key.rsplit('.', 1)
            
            # For field deletion, we need to update the secret
            vault_path = f"{self.mount_path}/data/{secret_path}"
            
            try:
                # Get existing data
                response = self._make_request('GET', vault_path)
                secret_data = response.json().get('data', {}).get('data', {})
                
                if field in secret_data:
                    del secret_data[field]
                    
                    # If no fields left, delete the entire secret
                    if not secret_data:
                        delete_path = f"{self.mount_path}/metadata/{secret_path}"
                        self._make_request('DELETE', delete_path)
                    else:
                        # Update with remaining fields
                        data = {'data': secret_data}
                        self._make_request('POST', vault_path, json=data)
                    
                    return True
                
            except ConfigurationError:
                pass
            
            return False
        
        else:
            # Delete entire secret
            secret_path = key
            vault_path = f"{self.mount_path}/metadata/{secret_path}"
            
            try:
                self._make_request('DELETE', vault_path)
                return True
            except ConfigurationError:
                return False
    
    def list_secrets(self) -> List[str]:
        """
        List all secrets in the mount path.
        
        Returns:
            List of secret paths
        """
        vault_path = f"{self.mount_path}/metadata"
        
        try:
            response = self._make_request('LIST', vault_path)
            data = response.json()
            
            keys = data.get('data', {}).get('keys', [])
            
            # Recursively list nested paths
            all_secrets = []
            for key in keys:
                if key.endswith('/'):
                    # This is a directory, list its contents
                    nested_secrets = self._list_nested_secrets(key.rstrip('/'))
                    all_secrets.extend(nested_secrets)
                else:
                    all_secrets.append(key)
            
            return all_secrets
        
        except ConfigurationError:
            return []
    
    def _list_nested_secrets(self, path: str) -> List[str]:
        """Recursively list secrets in a nested path."""
        vault_path = f"{self.mount_path}/metadata/{path}"
        
        try:
            response = self._make_request('LIST', vault_path)
            data = response.json()
            
            keys = data.get('data', {}).get('keys', [])
            secrets = []
            
            for key in keys:
                full_path = f"{path}/{key}"
                if key.endswith('/'):
                    # Recurse into subdirectory
                    nested = self._list_nested_secrets(full_path.rstrip('/'))
                    secrets.extend(nested)
                else:
                    secrets.append(full_path)
            
            return secrets
        
        except ConfigurationError:
            return []
    
    def health_check(self) -> bool:
        """
        Check if Vault is accessible and authenticated.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Check Vault status
            response = self._make_request('GET', 'sys/health')
            
            # Check authentication by reading our own token info
            if self.token:
                self._make_request('GET', 'auth/token/lookup-self')
            
            return True
        
        except ConfigurationError:
            return False
    
    def get_secret_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a secret.
        
        Args:
            key: Secret path
        
        Returns:
            Metadata dictionary or None if not found
        """
        vault_path = f"{self.mount_path}/metadata/{key}"
        
        try:
            response = self._make_request('GET', vault_path)
            return response.json().get('data', {})
        
        except ConfigurationError:
            return None
    
    def create_or_update_secret(self, key: str, data: Dict[str, str], check_and_set: Optional[int] = None) -> None:
        """
        Create or update a secret with multiple fields.
        
        Args:
            key: Secret path
            data: Dictionary of field names to values
            check_and_set: Version number for optimistic locking
        """
        vault_path = f"{self.mount_path}/data/{key}"
        
        payload = {'data': data}
        if check_and_set is not None:
            payload['options'] = {'cas': check_and_set}
        
        self._make_request('POST', vault_path, json=payload)