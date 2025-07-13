"""
Command-line interface for configuration management.

This module provides a comprehensive CLI tool for managing configurations,
profiles, secrets, and performing various configuration operations.
"""

import click
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from .security.encryption import ConfigEncryption
from .security.secrets import SecretManager, EnvironmentSecretProvider, FileSecretProvider
from .security.vault import VaultSecretProvider
from .profiles.manager import ProfileManager, ProfileType
from .exceptions import ConfigurationError


@click.group()
@click.option('--config-dir', '-c', type=click.Path(path_type=Path), 
              help='Configuration directory')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.pass_context
def cli(ctx, config_dir, verbose):
    """TORE Matrix Configuration Management CLI."""
    ctx.ensure_object(dict)
    ctx.obj['config_dir'] = config_dir or Path.cwd() / 'config'
    ctx.obj['verbose'] = verbose


@cli.group()
def profile():
    """Profile management commands."""
    pass


@profile.command('create')
@click.argument('name')
@click.option('--type', 'profile_type', type=click.Choice(['environment', 'feature', 'deployment', 'user']),
              default='environment', help='Profile type')
@click.option('--parent', help='Parent profile for inheritance')
@click.option('--description', help='Profile description')
@click.option('--config', type=click.Path(exists=True, path_type=Path), 
              help='Configuration file to import')
@click.pass_context
def create_profile(ctx, name, profile_type, parent, description, config):
    """Create a new configuration profile."""
    try:
        profiles_dir = ctx.obj['config_dir'] / 'profiles'
        manager = ProfileManager(profiles_dir)
        
        # Load configuration
        if config:
            with config.open() as f:
                config_data = json.load(f)
        else:
            config_data = {}
        
        # Create profile
        profile = manager.create_profile(
            name=name,
            config=config_data,
            profile_type=ProfileType(profile_type),
            parent=parent,
            description=description
        )
        
        # Save to file
        profile_file = profiles_dir / f"{name}.json"
        manager.export_profile(name, profile_file)
        
        click.echo(f"Profile '{name}' created successfully")
        if ctx.obj['verbose']:
            click.echo(f"Type: {profile_type}")
            click.echo(f"Parent: {parent or 'None'}")
            click.echo(f"File: {profile_file}")
    
    except ConfigurationError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@profile.command('list')
@click.option('--type', 'profile_type', type=click.Choice(['environment', 'feature', 'deployment', 'user']),
              help='Filter by profile type')
@click.pass_context
def list_profiles(ctx, profile_type):
    """List all configuration profiles."""
    try:
        profiles_dir = ctx.obj['config_dir'] / 'profiles'
        manager = ProfileManager(profiles_dir)
        
        filter_type = ProfileType(profile_type) if profile_type else None
        profiles = manager.list_profiles(filter_type)
        
        if not profiles:
            click.echo("No profiles found")
            return
        
        click.echo("Available profiles:")
        for profile_name in sorted(profiles):
            profile = manager.get_profile(profile_name)
            type_str = profile.profile_type.value if profile else "unknown"
            parent_str = f" (parent: {profile.parent})" if profile and profile.parent else ""
            click.echo(f"  {profile_name} [{type_str}]{parent_str}")
    
    except ConfigurationError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@profile.command('activate')
@click.argument('name')
@click.pass_context
def activate_profile(ctx, name):
    """Activate a configuration profile."""
    try:
        profiles_dir = ctx.obj['config_dir'] / 'profiles'
        manager = ProfileManager(profiles_dir)
        
        manager.activate_profile(name)
        
        # Save active profile to state file
        state_file = ctx.obj['config_dir'] / '.active_profile'
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(name)
        
        click.echo(f"Profile '{name}' activated")
    
    except ConfigurationError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@profile.command('show')
@click.argument('name')
@click.option('--resolved', is_flag=True, help='Show resolved configuration with inheritance')
@click.pass_context
def show_profile(ctx, name, resolved):
    """Show profile configuration."""
    try:
        profiles_dir = ctx.obj['config_dir'] / 'profiles'
        manager = ProfileManager(profiles_dir)
        
        profile = manager.get_profile(name)
        if not profile:
            click.echo(f"Profile '{name}' not found", err=True)
            sys.exit(1)
        
        if resolved:
            # Show resolved configuration
            base_config = {}  # Could load from base config file
            resolved_config = manager.resolve_config(base_config, name)
            click.echo(f"Resolved configuration for '{name}':")
            click.echo(json.dumps(resolved_config, indent=2))
        else:
            # Show profile details
            click.echo(f"Profile: {profile.name}")
            click.echo(f"Type: {profile.profile_type.value}")
            click.echo(f"Parent: {profile.parent or 'None'}")
            click.echo(f"Description: {profile.description or 'None'}")
            click.echo("Configuration:")
            click.echo(json.dumps(profile.config, indent=2))
    
    except ConfigurationError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def secret():
    """Secret management commands."""
    pass


@secret.command('set')
@click.argument('key')
@click.argument('value')
@click.option('--provider', default='env', help='Secret provider to use')
@click.pass_context
def set_secret(ctx, key, value, provider):
    """Set a secret value."""
    try:
        manager = _get_secret_manager(ctx, provider)
        manager.set_secret(key, value, provider)
        click.echo(f"Secret '{key}' set successfully")
    
    except ConfigurationError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@secret.command('get')
@click.argument('key')
@click.option('--provider', default='env', help='Secret provider to use')
@click.pass_context
def get_secret(ctx, key, provider):
    """Get a secret value."""
    try:
        manager = _get_secret_manager(ctx, provider)
        value = manager.get_secret(key, provider)
        
        if value is not None:
            click.echo(value)
        else:
            click.echo(f"Secret '{key}' not found", err=True)
            sys.exit(1)
    
    except ConfigurationError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@secret.command('list')
@click.option('--provider', default='env', help='Secret provider to use')
@click.pass_context
def list_secrets(ctx, key, provider):
    """List all secret keys."""
    try:
        manager = _get_secret_manager(ctx, provider)
        secrets = manager.list_secrets(provider)
        
        if secrets:
            click.echo("Available secrets:")
            for secret_key in sorted(secrets):
                click.echo(f"  {secret_key}")
        else:
            click.echo("No secrets found")
    
    except ConfigurationError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def encrypt():
    """Encryption commands."""
    pass


@encrypt.command('init')
@click.option('--key-file', type=click.Path(path_type=Path), 
              help='Key file path (default: config/.encryption.key)')
@click.option('--password', help='Password for key derivation')
@click.pass_context
def init_encryption(ctx, key_file, password):
    """Initialize encryption with a new key."""
    try:
        if not key_file:
            key_file = ctx.obj['config_dir'] / '.encryption.key'
        
        encryption = ConfigEncryption()
        
        if password:
            # Derive key from password
            salt = encryption.set_key_from_password(password)
            
            # Save salt alongside key
            salt_file = key_file.with_suffix('.salt')
            salt_file.write_bytes(salt)
            click.echo(f"Encryption initialized with password-derived key")
            click.echo(f"Salt saved to: {salt_file}")
        else:
            # Generate random key
            key = ConfigEncryption.generate_key()
            encryption.set_key(key)
            encryption.save_key(key_file, key)
            click.echo(f"Encryption initialized with random key")
        
        click.echo(f"Key saved to: {key_file}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@encrypt.command('file')
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.argument('output_file', type=click.Path(path_type=Path))
@click.option('--key-file', type=click.Path(exists=True, path_type=Path),
              help='Encryption key file')
@click.option('--fields', help='Comma-separated list of fields to encrypt')
@click.pass_context
def encrypt_file(ctx, input_file, output_file, key_file, fields):
    """Encrypt sensitive fields in a configuration file."""
    try:
        # Load encryption key
        if not key_file:
            key_file = ctx.obj['config_dir'] / '.encryption.key'
        
        encryption = ConfigEncryption()
        encryption.load_key(key_file)
        
        # Load configuration
        with input_file.open() as f:
            config = json.load(f)
        
        # Encrypt specified fields or use defaults
        if fields:
            field_list = [f.strip() for f in fields.split(',')]
            encrypted_config = config
            for field in field_list:
                encrypted_config = encryption.encrypt_field(encrypted_config, field)
        else:
            encrypted_config = encryption.encrypt_config(config)
        
        # Save encrypted configuration
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with output_file.open('w') as f:
            json.dump(encrypted_config, f, indent=2)
        
        click.echo(f"Configuration encrypted and saved to: {output_file}")
        
        if ctx.obj['verbose']:
            encrypted_fields = encryption.get_encrypted_fields()
            click.echo(f"Encrypted fields: {', '.join(encrypted_fields)}")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('config_file', type=click.Path(exists=True, path_type=Path))
@click.option('--profile', help='Profile to apply')
@click.option('--output', type=click.Path(path_type=Path), help='Output file')
@click.option('--decrypt', is_flag=True, help='Decrypt encrypted fields')
@click.pass_context
def resolve(ctx, config_file, profile, output, decrypt):
    """Resolve configuration with profiles and secrets."""
    try:
        # Load base configuration
        with config_file.open() as f:
            config = json.load(f)
        
        # Apply profile if specified
        if profile:
            profiles_dir = ctx.obj['config_dir'] / 'profiles'
            manager = ProfileManager(profiles_dir)
            config = manager.resolve_config(config, profile)
        
        # Interpolate secrets
        secret_manager = _get_secret_manager(ctx)
        config = secret_manager.interpolate_secrets(config)
        
        # Decrypt if requested
        if decrypt:
            key_file = ctx.obj['config_dir'] / '.encryption.key'
            if key_file.exists():
                encryption = ConfigEncryption()
                encryption.load_key(key_file)
                config = encryption.decrypt_config(config)
        
        # Output result
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open('w') as f:
                json.dump(config, f, indent=2)
            click.echo(f"Resolved configuration saved to: {output}")
        else:
            click.echo(json.dumps(config, indent=2))
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _get_secret_manager(ctx, provider_name: Optional[str] = None) -> SecretManager:
    """Get configured secret manager."""
    manager = SecretManager()
    
    # Register environment provider
    env_provider = EnvironmentSecretProvider()
    manager.register_provider('env', env_provider, is_default=True)
    
    # Register file provider
    secrets_file = ctx.obj['config_dir'] / 'secrets.json'
    file_provider = FileSecretProvider(secrets_file)
    manager.register_provider('file', file_provider)
    
    # Register Vault provider if configured
    vault_url = ctx.obj.get('vault_url')
    if vault_url:
        try:
            vault_provider = VaultSecretProvider(vault_url)
            manager.register_provider('vault', vault_provider)
        except Exception:
            # Vault not available
            pass
    
    return manager


if __name__ == '__main__':
    cli()