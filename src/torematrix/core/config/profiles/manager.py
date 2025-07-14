"""
Configuration profile management.

This module provides profile management capabilities for different
environments and deployment scenarios.
"""

from typing import Dict, Any, Optional, List, Set
from pathlib import Path
import json
import copy
from enum import Enum
from ..types import ConfigDict
from ..exceptions import ConfigurationError
from .resolver import ProfileResolver
from .inheritance import InheritanceResolver


class ProfileType(Enum):
    """Profile types for different use cases."""
    ENVIRONMENT = "environment"  # dev, test, prod
    FEATURE = "feature"         # feature flags
    DEPLOYMENT = "deployment"   # cloud, on-prem
    USER = "user"              # user-specific overrides


class Profile:
    """
    Represents a configuration profile.
    
    A profile contains configuration overrides and metadata
    for a specific environment or deployment scenario.
    """
    
    def __init__(
        self,
        name: str,
        config: ConfigDict,
        profile_type: ProfileType = ProfileType.ENVIRONMENT,
        parent: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.name = name
        self.config = config
        self.profile_type = profile_type
        self.parent = parent
        self.description = description
        self.metadata = metadata or {}
        self.children: Set[str] = set()
        
        # Validation
        if not name:
            raise ConfigurationError("Profile name cannot be empty")
        if not isinstance(config, dict):
            raise ConfigurationError("Profile config must be a dictionary")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary representation."""
        return {
            "name": self.name,
            "config": self.config,
            "type": self.profile_type.value,
            "parent": self.parent,
            "description": self.description,
            "metadata": self.metadata,
            "children": list(self.children)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Profile':
        """Create profile from dictionary representation."""
        profile_type = ProfileType(data.get("type", ProfileType.ENVIRONMENT.value))
        
        profile = cls(
            name=data["name"],
            config=data["config"],
            profile_type=profile_type,
            parent=data.get("parent"),
            description=data.get("description"),
            metadata=data.get("metadata", {})
        )
        
        # Set children if provided
        children = data.get("children", [])
        profile.children = set(children)
        
        return profile


class ProfileManager:
    """
    Manage configuration profiles and environment-specific overrides.
    
    Features:
    - Profile inheritance hierarchy
    - Environment-specific configurations
    - Profile activation and switching
    - Validation and conflict resolution
    """
    
    def __init__(self, profiles_dir: Optional[Path] = None):
        """
        Initialize profile manager.
        
        Args:
            profiles_dir: Directory containing profile files
        """
        self.profiles: Dict[str, Profile] = {}
        self.profiles_dir = profiles_dir
        self.active_profile: Optional[str] = None
        self.resolver = ProfileResolver()
        self.inheritance_resolver = InheritanceResolver()
        
        # Load profiles from directory if provided
        if profiles_dir and profiles_dir.exists():
            self.load_profiles_from_directory(profiles_dir)
    
    def create_profile(
        self,
        name: str,
        config: ConfigDict,
        profile_type: ProfileType = ProfileType.ENVIRONMENT,
        parent: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Profile:
        """
        Create a new configuration profile.
        
        Args:
            name: Profile name
            config: Configuration overrides
            profile_type: Type of profile
            parent: Parent profile name for inheritance
            description: Profile description
            metadata: Additional metadata
            
        Returns:
            Created profile
        """
        if name in self.profiles:
            raise ConfigurationError(f"Profile '{name}' already exists")
        
        if parent and parent not in self.profiles:
            raise ConfigurationError(f"Parent profile '{parent}' not found")
        
        profile = Profile(
            name=name,
            config=config,
            profile_type=profile_type,
            parent=parent,
            description=description,
            metadata=metadata
        )
        
        self.profiles[name] = profile
        
        # Update parent's children set
        if parent:
            self.profiles[parent].children.add(name)
        
        return profile
    
    def get_profile(self, name: str) -> Optional[Profile]:
        """Get profile by name."""
        return self.profiles.get(name)
    
    def delete_profile(self, name: str) -> bool:
        """
        Delete a profile.
        
        Args:
            name: Profile name to delete
            
        Returns:
            True if deleted, False if not found
        """
        if name not in self.profiles:
            return False
        
        profile = self.profiles[name]
        
        # Check for children
        if profile.children:
            raise ConfigurationError(
                f"Cannot delete profile '{name}' with children: {profile.children}"
            )
        
        # Remove from parent's children
        if profile.parent:
            parent_profile = self.profiles.get(profile.parent)
            if parent_profile:
                parent_profile.children.discard(name)
        
        # Deactivate if this is the active profile
        if self.active_profile == name:
            self.active_profile = None
        
        del self.profiles[name]
        return True
    
    def list_profiles(self, profile_type: Optional[ProfileType] = None) -> List[str]:
        """
        List all profile names, optionally filtered by type.
        
        Args:
            profile_type: Filter by profile type
            
        Returns:
            List of profile names
        """
        if profile_type is None:
            return list(self.profiles.keys())
        
        return [
            name for name, profile in self.profiles.items()
            if profile.profile_type == profile_type
        ]
    
    def activate_profile(self, name: str) -> None:
        """
        Activate a configuration profile.
        
        Args:
            name: Profile name to activate
        """
        if name not in self.profiles:
            raise ConfigurationError(f"Profile '{name}' not found")
        
        self.active_profile = name
    
    def deactivate_profile(self) -> None:
        """Deactivate the current profile."""
        self.active_profile = None
    
    def get_active_profile(self) -> Optional[Profile]:
        """Get the currently active profile."""
        if self.active_profile:
            return self.profiles.get(self.active_profile)
        return None
    
    def resolve_config(
        self,
        base_config: ConfigDict,
        profile_name: Optional[str] = None
    ) -> ConfigDict:
        """
        Resolve configuration with profile overrides.
        
        Args:
            base_config: Base configuration
            profile_name: Profile to apply (uses active if None)
            
        Returns:
            Resolved configuration
        """
        if profile_name is None:
            profile_name = self.active_profile
        
        if not profile_name:
            return base_config
        
        if profile_name not in self.profiles:
            raise ConfigurationError(f"Profile '{profile_name}' not found")
        
        # Build inheritance chain
        inheritance_chain = self._build_inheritance_chain(profile_name)
        
        # Apply profiles in order (parent to child)
        result = copy.deepcopy(base_config)
        
        for profile_name in inheritance_chain:
            profile = self.profiles[profile_name]
            result = self.resolver.merge_config(result, profile.config)
        
        return result
    
    def validate_profile(self, name: str) -> List[str]:
        """
        Validate a profile configuration.
        
        Args:
            name: Profile name to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        if name not in self.profiles:
            return [f"Profile '{name}' not found"]
        
        errors = []
        profile = self.profiles[name]
        
        # Check for circular inheritance
        try:
            self._build_inheritance_chain(name)
        except ConfigurationError as e:
            errors.append(str(e))
        
        # Validate configuration structure
        try:
            self._validate_config_structure(profile.config)
        except ConfigurationError as e:
            errors.append(f"Invalid config structure: {e}")
        
        return errors
    
    def get_profile_hierarchy(self, name: str) -> Dict[str, Any]:
        """
        Get the inheritance hierarchy for a profile.
        
        Args:
            name: Profile name
            
        Returns:
            Hierarchy representation
        """
        if name not in self.profiles:
            raise ConfigurationError(f"Profile '{name}' not found")
        
        def build_hierarchy(profile_name: str) -> Dict[str, Any]:
            profile = self.profiles[profile_name]
            node = {
                "name": profile_name,
                "type": profile.profile_type.value,
                "description": profile.description,
                "children": []
            }
            
            for child_name in sorted(profile.children):
                node["children"].append(build_hierarchy(child_name))
            
            return node
        
        # Find root of hierarchy
        current = name
        while self.profiles[current].parent:
            current = self.profiles[current].parent
        
        return build_hierarchy(current)
    
    def export_profile(self, name: str, file_path: Path) -> None:
        """
        Export profile to file.
        
        Args:
            name: Profile name to export
            file_path: Output file path
        """
        if name not in self.profiles:
            raise ConfigurationError(f"Profile '{name}' not found")
        
        profile = self.profiles[name]
        profile_data = profile.to_dict()
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open('w') as f:
            json.dump(profile_data, f, indent=2)
    
    def import_profile(self, file_path: Path) -> Profile:
        """
        Import profile from file.
        
        Args:
            file_path: Profile file path
            
        Returns:
            Imported profile
        """
        if not file_path.exists():
            raise ConfigurationError(f"Profile file not found: {file_path}")
        
        try:
            with file_path.open('r') as f:
                profile_data = json.load(f)
            
            profile = Profile.from_dict(profile_data)
            
            # Check if profile already exists
            if profile.name in self.profiles:
                raise ConfigurationError(f"Profile '{profile.name}' already exists")
            
            # Add to profiles
            self.profiles[profile.name] = profile
            
            return profile
        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise ConfigurationError(f"Invalid profile file: {e}")
    
    def load_profiles_from_directory(self, directory: Path) -> int:
        """
        Load all profiles from a directory.
        
        Args:
            directory: Directory containing profile files
            
        Returns:
            Number of profiles loaded
        """
        if not directory.exists():
            raise ConfigurationError(f"Profiles directory not found: {directory}")
        
        loaded_count = 0
        
        # Load .json files as profiles
        for profile_file in directory.glob("*.json"):
            try:
                self.import_profile(profile_file)
                loaded_count += 1
            except ConfigurationError:
                # Skip invalid profile files
                continue
        
        return loaded_count
    
    def save_profiles_to_directory(self, directory: Path) -> int:
        """
        Save all profiles to a directory.
        
        Args:
            directory: Target directory
            
        Returns:
            Number of profiles saved
        """
        directory.mkdir(parents=True, exist_ok=True)
        
        saved_count = 0
        
        for profile_name, profile in self.profiles.items():
            file_path = directory / f"{profile_name}.json"
            try:
                self.export_profile(profile_name, file_path)
                saved_count += 1
            except ConfigurationError:
                continue
        
        return saved_count
    
    def _build_inheritance_chain(self, name: str) -> List[str]:
        """Build inheritance chain from root to specified profile."""
        chain = []
        visited = set()
        current = name
        
        # Build chain from child to parent
        while current:
            if current in visited:
                raise ConfigurationError(f"Circular inheritance detected: {current}")
            
            visited.add(current)
            chain.append(current)
            
            profile = self.profiles.get(current)
            if not profile:
                raise ConfigurationError(f"Profile '{current}' not found in chain")
            
            current = profile.parent
        
        # Reverse to get parent-to-child order
        chain.reverse()
        return chain
    
    def _validate_config_structure(self, config: ConfigDict) -> None:
        """Validate configuration structure."""
        if not isinstance(config, dict):
            raise ConfigurationError("Configuration must be a dictionary")
        
        # Additional validation can be added here
        # For example, checking required fields, data types, etc.
        
        for key, value in config.items():
            if not isinstance(key, str):
                raise ConfigurationError(f"Configuration key must be string: {key}")
            
            # Recursively validate nested dictionaries
            if isinstance(value, dict):
                self._validate_config_structure(value)