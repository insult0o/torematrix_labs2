"""
Configuration profile inheritance resolution.

This module provides inheritance resolution for configuration profiles,
including multiple inheritance, mixin support, and dependency resolution.
"""

from typing import Dict, Any, List, Set, Optional, Tuple
import copy
from enum import Enum
from ..types import ConfigDict
from ..exceptions import ConfigurationError


class InheritanceMode(Enum):
    """Inheritance modes for profile resolution."""
    SINGLE = "single"        # Single inheritance only
    MULTIPLE = "multiple"    # Multiple inheritance allowed
    MIXIN = "mixin"         # Mixin-style inheritance


class DependencyOrder(Enum):
    """Order for resolving dependencies."""
    DEPTH_FIRST = "depth_first"      # Depth-first traversal
    BREADTH_FIRST = "breadth_first"  # Breadth-first traversal
    TOPOLOGICAL = "topological"     # Topological sort


class InheritanceResolver:
    """
    Resolve configuration profile inheritance with support for
    multiple inheritance patterns and dependency resolution.
    
    Features:
    - Single and multiple inheritance
    - Mixin support
    - Circular dependency detection
    - Configurable resolution order
    - Conflict detection and resolution
    """
    
    def __init__(
        self,
        mode: InheritanceMode = InheritanceMode.SINGLE,
        dependency_order: DependencyOrder = DependencyOrder.DEPTH_FIRST
    ):
        """
        Initialize inheritance resolver.
        
        Args:
            mode: Inheritance mode
            dependency_order: Order for dependency resolution
        """
        self.mode = mode
        self.dependency_order = dependency_order
        self.profile_cache: Dict[str, ConfigDict] = {}
        self.resolution_cache: Dict[Tuple[str, ...], ConfigDict] = {}
    
    def resolve_inheritance(
        self,
        target_profile: str,
        profiles: Dict[str, Any],
        base_config: Optional[ConfigDict] = None
    ) -> ConfigDict:
        """
        Resolve inheritance for a target profile.
        
        Args:
            target_profile: Name of profile to resolve
            profiles: All available profiles
            base_config: Base configuration to start from
            
        Returns:
            Resolved configuration
        """
        # Build dependency graph
        dependency_graph = self._build_dependency_graph(profiles)
        
        # Get resolution order
        resolution_order = self._get_resolution_order(
            target_profile, dependency_graph
        )
        
        # Check cache
        cache_key = tuple(resolution_order)
        if cache_key in self.resolution_cache:
            result = copy.deepcopy(self.resolution_cache[cache_key])
            if base_config:
                result = self._merge_configs(base_config, result)
            return result
        
        # Resolve in order
        result = base_config or {}
        
        for profile_name in resolution_order:
            if profile_name not in profiles:
                raise ConfigurationError(f"Profile '{profile_name}' not found")
            
            profile_config = self._get_profile_config(profile_name, profiles)
            result = self._merge_configs(result, profile_config)
        
        # Cache result
        self.resolution_cache[cache_key] = copy.deepcopy(result)
        
        return result
    
    def resolve_multiple_inheritance(
        self,
        target_profile: str,
        profiles: Dict[str, Any],
        parents: List[str],
        base_config: Optional[ConfigDict] = None
    ) -> ConfigDict:
        """
        Resolve multiple inheritance for a profile.
        
        Args:
            target_profile: Target profile name
            profiles: All available profiles
            parents: List of parent profiles
            base_config: Base configuration
            
        Returns:
            Resolved configuration with multiple inheritance
        """
        if self.mode == InheritanceMode.SINGLE and len(parents) > 1:
            raise ConfigurationError(
                f"Multiple inheritance not allowed in {self.mode.value} mode"
            )
        
        # Use C3 linearization for multiple inheritance
        if len(parents) > 1:
            resolution_order = self._c3_linearization(target_profile, profiles, parents)
        else:
            # Single inheritance - simple traversal
            resolution_order = self._get_resolution_order(target_profile, 
                                                        self._build_dependency_graph(profiles))
        
        # Resolve configurations
        result = base_config or {}
        
        for profile_name in resolution_order:
            if profile_name == target_profile:
                continue  # Skip self
            
            profile_config = self._get_profile_config(profile_name, profiles)
            result = self._merge_configs(result, profile_config)
        
        # Finally apply target profile
        target_config = self._get_profile_config(target_profile, profiles)
        result = self._merge_configs(result, target_config)
        
        return result
    
    def detect_circular_dependencies(self, profiles: Dict[str, Any]) -> List[List[str]]:
        """
        Detect circular dependencies in profile inheritance.
        
        Args:
            profiles: All available profiles
            
        Returns:
            List of circular dependency chains
        """
        dependency_graph = self._build_dependency_graph(profiles)
        cycles = []
        
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]) -> None:
            if node in rec_stack:
                # Found cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in dependency_graph.get(node, []):
                dfs(neighbor, path + [neighbor])
            
            rec_stack.remove(node)
        
        for profile in profiles:
            if profile not in visited:
                dfs(profile, [profile])
        
        return cycles
    
    def validate_inheritance_tree(self, profiles: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Validate inheritance tree for all profiles.
        
        Args:
            profiles: All available profiles
            
        Returns:
            Dictionary mapping profile names to validation errors
        """
        errors = {}
        
        # Check for circular dependencies
        cycles = self.detect_circular_dependencies(profiles)
        if cycles:
            for cycle in cycles:
                for profile in cycle:
                    if profile not in errors:
                        errors[profile] = []
                    errors[profile].append(f"Circular dependency: {' -> '.join(cycle)}")
        
        # Check for missing parent references
        for profile_name, profile_data in profiles.items():
            profile_errors = []
            
            parents = self._get_profile_parents(profile_data)
            for parent in parents:
                if parent not in profiles:
                    profile_errors.append(f"Parent profile '{parent}' not found")
            
            # Validate multiple inheritance rules
            if self.mode == InheritanceMode.SINGLE and len(parents) > 1:
                profile_errors.append(
                    f"Multiple inheritance not allowed: {parents}"
                )
            
            if profile_errors:
                errors[profile_name] = profile_errors
        
        return errors
    
    def get_inheritance_tree(self, profiles: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get visual representation of inheritance tree.
        
        Args:
            profiles: All available profiles
            
        Returns:
            Tree structure representation
        """
        dependency_graph = self._build_dependency_graph(profiles)
        
        # Find root profiles (no parents)
        roots = []
        for profile_name in profiles:
            parents = self._get_profile_parents(profiles[profile_name])
            if not parents:
                roots.append(profile_name)
        
        def build_tree(profile_name: str, visited: Set[str]) -> Dict[str, Any]:
            if profile_name in visited:
                return {"name": profile_name, "circular": True}
            
            visited.add(profile_name)
            
            node = {
                "name": profile_name,
                "parents": self._get_profile_parents(profiles.get(profile_name, {})),
                "children": []
            }
            
            # Find children (profiles that inherit from this one)
            for other_profile, other_data in profiles.items():
                parents = self._get_profile_parents(other_data)
                if profile_name in parents:
                    child_node = build_tree(other_profile, visited.copy())
                    node["children"].append(child_node)
            
            return node
        
        tree = {"roots": []}
        for root in roots:
            tree["roots"].append(build_tree(root, set()))
        
        return tree
    
    def clear_cache(self) -> None:
        """Clear resolution cache."""
        self.profile_cache.clear()
        self.resolution_cache.clear()
    
    def _build_dependency_graph(self, profiles: Dict[str, Any]) -> Dict[str, List[str]]:
        """Build dependency graph from profiles."""
        graph = {}
        
        for profile_name, profile_data in profiles.items():
            parents = self._get_profile_parents(profile_data)
            graph[profile_name] = parents
        
        return graph
    
    def _get_profile_parents(self, profile_data: Any) -> List[str]:
        """Extract parent profile names from profile data."""
        if hasattr(profile_data, 'parent'):
            # Profile object
            return [profile_data.parent] if profile_data.parent else []
        elif isinstance(profile_data, dict):
            # Dictionary representation
            parent = profile_data.get('parent')
            parents = profile_data.get('parents', [])
            
            if parent:
                return [parent]
            elif parents:
                return parents if isinstance(parents, list) else [parents]
            else:
                return []
        else:
            return []
    
    def _get_profile_config(self, profile_name: str, profiles: Dict[str, Any]) -> ConfigDict:
        """Get configuration from profile data."""
        if profile_name in self.profile_cache:
            return copy.deepcopy(self.profile_cache[profile_name])
        
        profile_data = profiles[profile_name]
        
        if hasattr(profile_data, 'config'):
            # Profile object
            config = profile_data.config
        elif isinstance(profile_data, dict):
            # Dictionary representation
            config = profile_data.get('config', {})
        else:
            config = {}
        
        self.profile_cache[profile_name] = copy.deepcopy(config)
        return config
    
    def _get_resolution_order(
        self,
        target_profile: str,
        dependency_graph: Dict[str, List[str]]
    ) -> List[str]:
        """Get resolution order based on dependency order setting."""
        if self.dependency_order == DependencyOrder.TOPOLOGICAL:
            return self._topological_sort(target_profile, dependency_graph)
        elif self.dependency_order == DependencyOrder.BREADTH_FIRST:
            return self._breadth_first_order(target_profile, dependency_graph)
        else:  # DEPTH_FIRST
            return self._depth_first_order(target_profile, dependency_graph)
    
    def _depth_first_order(
        self,
        target_profile: str,
        dependency_graph: Dict[str, List[str]]
    ) -> List[str]:
        """Get depth-first resolution order."""
        visited = set()
        order = []
        
        def dfs(profile: str):
            if profile in visited:
                return
            
            visited.add(profile)
            
            # Visit parents first
            for parent in dependency_graph.get(profile, []):
                dfs(parent)
            
            order.append(profile)
        
        dfs(target_profile)
        return order
    
    def _breadth_first_order(
        self,
        target_profile: str,
        dependency_graph: Dict[str, List[str]]
    ) -> List[str]:
        """Get breadth-first resolution order."""
        from collections import deque
        
        queue = deque([target_profile])
        visited = set()
        order = []
        
        while queue:
            profile = queue.popleft()
            
            if profile in visited:
                continue
            
            visited.add(profile)
            order.append(profile)
            
            # Add parents to queue
            for parent in dependency_graph.get(profile, []):
                if parent not in visited:
                    queue.append(parent)
        
        # Reverse to get proper resolution order (parents first)
        return list(reversed(order))
    
    def _topological_sort(
        self,
        target_profile: str,
        dependency_graph: Dict[str, List[str]]
    ) -> List[str]:
        """Get topological sort order."""
        # Build reverse graph (children -> parents becomes parents -> children)
        reverse_graph = {}
        in_degree = {}
        
        # Initialize
        all_profiles = set([target_profile])
        all_profiles.update(dependency_graph.get(target_profile, []))
        
        for profile in all_profiles:
            reverse_graph[profile] = []
            in_degree[profile] = 0
        
        # Build reverse edges and calculate in-degrees
        for profile, parents in dependency_graph.items():
            if profile in all_profiles:
                for parent in parents:
                    if parent in all_profiles:
                        reverse_graph[parent].append(profile)
                        in_degree[profile] += 1
        
        # Kahn's algorithm
        from collections import deque
        
        queue = deque([p for p in all_profiles if in_degree[p] == 0])
        order = []
        
        while queue:
            profile = queue.popleft()
            order.append(profile)
            
            for child in reverse_graph[profile]:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        
        return order
    
    def _c3_linearization(
        self,
        target_profile: str,
        profiles: Dict[str, Any],
        parents: List[str]
    ) -> List[str]:
        """
        C3 linearization algorithm for multiple inheritance.
        
        This ensures a consistent method resolution order that respects
        local precedence order and monotonicity.
        """
        def merge(*sequences):
            """Merge sequences according to C3 algorithm."""
            result = []
            sequences = [list(seq) for seq in sequences if seq]
            
            while sequences:
                # Find a candidate (head of a sequence that doesn't appear
                # in the tail of any other sequence)
                candidate = None
                
                for seq in sequences:
                    if not seq:
                        continue
                    
                    head = seq[0]
                    
                    # Check if head appears in tail of any sequence
                    appears_in_tail = False
                    for other_seq in sequences:
                        if len(other_seq) > 1 and head in other_seq[1:]:
                            appears_in_tail = True
                            break
                    
                    if not appears_in_tail:
                        candidate = head
                        break
                
                if candidate is None:
                    raise ConfigurationError(
                        f"Cannot create consistent linearization for {target_profile}"
                    )
                
                result.append(candidate)
                
                # Remove candidate from all sequences
                sequences = [
                    seq[1:] if seq and seq[0] == candidate else seq
                    for seq in sequences
                ]
                sequences = [seq for seq in sequences if seq]
            
            return result
        
        # Get linearizations for all parents
        parent_linearizations = []
        for parent in parents:
            parent_deps = self._build_dependency_graph({parent: profiles[parent]} 
                                                     if parent in profiles else {})
            parent_order = self._get_resolution_order(parent, parent_deps)
            parent_linearizations.append(parent_order)
        
        # C3 merge
        try:
            linearization = merge(*parent_linearizations, parents)
            return linearization + [target_profile]
        except ConfigurationError:
            # Fallback to simple depth-first
            return self._depth_first_order(target_profile, 
                                         self._build_dependency_graph(profiles))
    
    def _merge_configs(self, base: ConfigDict, override: ConfigDict) -> ConfigDict:
        """Simple deep merge of configurations."""
        result = copy.deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        
        return result