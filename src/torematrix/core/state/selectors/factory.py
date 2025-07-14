"""
Selector factory for creating commonly used selectors with optimized patterns.
"""

from typing import Any, Callable, Dict, List, Optional, Union, TypeVar
from .base import Selector, ParametricSelector, create_selector, create_parametric_selector
from .memoization import cache_manager

T = TypeVar('T')


class SelectorFactory:
    """
    Factory for creating optimized selectors with common patterns.
    """
    
    def __init__(self, cache_name: Optional[str] = None):
        self.cache_name = cache_name or 'selector_factory'
        self._created_selectors: Dict[str, Selector] = {}
    
    def create_path_selector(
        self,
        path: str,
        default_value: Any = None,
        name: Optional[str] = None
    ) -> Selector:
        """
        Create a selector that extracts a value from a specific state path.
        
        Args:
            path: Dot-separated path (e.g., 'document.metadata.title')
            default_value: Value to return if path doesn't exist
            name: Optional selector name
            
        Returns:
            Selector that extracts the path value
        """
        selector_name = name or f"path_{path.replace('.', '_')}"
        
        if selector_name in self._created_selectors:
            return self._created_selectors[selector_name]
        
        def path_selector(state: Dict[str, Any]) -> Any:
            """Extract value from nested path."""
            current = state
            
            try:
                for key in path.split('.'):
                    if isinstance(current, dict):
                        current = current.get(key)
                    elif hasattr(current, key):
                        current = getattr(current, key)
                    else:
                        return default_value
                    
                    if current is None:
                        return default_value
                
                return current
            except (KeyError, AttributeError, TypeError):
                return default_value
        
        selector = Selector(
            selector_fn=path_selector,
            name=selector_name
        )
        
        self._created_selectors[selector_name] = selector
        return selector
    
    def create_filter_selector(
        self,
        base_selector: Union[Selector, Callable],
        filter_fn: Callable[[Any], bool],
        name: Optional[str] = None
    ) -> Selector:
        """
        Create a selector that filters results from a base selector.
        
        Args:
            base_selector: Base selector or function
            filter_fn: Function to filter items
            name: Optional selector name
            
        Returns:
            Selector that filters base selector results
        """
        selector_name = name or f"filter_{id(filter_fn)}"
        
        if selector_name in self._created_selectors:
            return self._created_selectors[selector_name]
        
        def filter_selector(items: List[Any]) -> List[Any]:
            """Filter items based on predicate."""
            if not isinstance(items, (list, tuple)):
                return []
            
            try:
                return [item for item in items if filter_fn(item)]
            except Exception:
                return []
        
        selector = create_selector(
            base_selector,
            filter_selector,
            name=selector_name
        )
        
        self._created_selectors[selector_name] = selector
        return selector
    
    def create_map_selector(
        self,
        base_selector: Union[Selector, Callable],
        map_fn: Callable[[Any], Any],
        name: Optional[str] = None
    ) -> Selector:
        """
        Create a selector that maps/transforms results from a base selector.
        
        Args:
            base_selector: Base selector or function
            map_fn: Function to transform items
            name: Optional selector name
            
        Returns:
            Selector that transforms base selector results
        """
        selector_name = name or f"map_{id(map_fn)}"
        
        if selector_name in self._created_selectors:
            return self._created_selectors[selector_name]
        
        def map_selector(items: List[Any]) -> List[Any]:
            """Map items through transformation function."""
            if not isinstance(items, (list, tuple)):
                return []
            
            try:
                return [map_fn(item) for item in items]
            except Exception:
                return []
        
        selector = create_selector(
            base_selector,
            map_selector,
            name=selector_name
        )
        
        self._created_selectors[selector_name] = selector
        return selector
    
    def create_aggregation_selector(
        self,
        base_selector: Union[Selector, Callable],
        aggregation_fn: Callable[[List[Any]], Any],
        name: Optional[str] = None
    ) -> Selector:
        """
        Create a selector that aggregates results from a base selector.
        
        Args:
            base_selector: Base selector or function
            aggregation_fn: Function to aggregate items (count, sum, etc.)
            name: Optional selector name
            
        Returns:
            Selector that aggregates base selector results
        """
        selector_name = name or f"agg_{id(aggregation_fn)}"
        
        if selector_name in self._created_selectors:
            return self._created_selectors[selector_name]
        
        def aggregation_selector(items: List[Any]) -> Any:
            """Aggregate items using aggregation function."""
            if not isinstance(items, (list, tuple)):
                return aggregation_fn([])
            
            try:
                return aggregation_fn(items)
            except Exception:
                return aggregation_fn([])
        
        selector = create_selector(
            base_selector,
            aggregation_selector,
            name=selector_name
        )
        
        self._created_selectors[selector_name] = selector
        return selector
    
    def create_parametric_filter_selector(
        self,
        base_selector: Union[Selector, Callable],
        name: Optional[str] = None
    ) -> ParametricSelector:
        """
        Create a parametric selector for dynamic filtering.
        
        Args:
            base_selector: Base selector or function
            name: Optional selector name
            
        Returns:
            Parametric selector that accepts filter parameters
            
        Example:
            filter_by_type = factory.create_parametric_filter_selector(get_elements)
            text_elements = filter_by_type(state, element_type='text')
        """
        selector_name = name or f"param_filter_{id(base_selector)}"
        
        def parametric_filter(items: List[Any], **filter_params) -> List[Any]:
            """Filter items based on dynamic parameters."""
            if not isinstance(items, (list, tuple)):
                return []
            
            if not filter_params:
                return list(items)
            
            try:
                filtered = []
                for item in items:
                    match = True
                    for key, value in filter_params.items():
                        if isinstance(item, dict):
                            item_value = item.get(key)
                        elif hasattr(item, key):
                            item_value = getattr(item, key)
                        else:
                            match = False
                            break
                        
                        if item_value != value:
                            match = False
                            break
                    
                    if match:
                        filtered.append(item)
                
                return filtered
            except Exception:
                return []
        
        return create_parametric_selector(
            base_selector,
            output_fn=parametric_filter,
            name=selector_name
        )
    
    def create_sorted_selector(
        self,
        base_selector: Union[Selector, Callable],
        sort_key: Union[str, Callable],
        reverse: bool = False,
        name: Optional[str] = None
    ) -> Selector:
        """
        Create a selector that sorts results from a base selector.
        
        Args:
            base_selector: Base selector or function
            sort_key: Key function or attribute name for sorting
            reverse: Whether to sort in reverse order
            name: Optional selector name
            
        Returns:
            Selector that sorts base selector results
        """
        selector_name = name or f"sorted_{id(sort_key)}"
        
        if selector_name in self._created_selectors:
            return self._created_selectors[selector_name]
        
        def sort_selector(items: List[Any]) -> List[Any]:
            """Sort items by key."""
            if not isinstance(items, (list, tuple)):
                return []
            
            try:
                if isinstance(sort_key, str):
                    # Sort by attribute/key name
                    def key_fn(item):
                        if isinstance(item, dict):
                            return item.get(sort_key, 0)
                        elif hasattr(item, sort_key):
                            return getattr(item, sort_key, 0)
                        else:
                            return 0
                    
                    return sorted(items, key=key_fn, reverse=reverse)
                else:
                    # Sort by custom function
                    return sorted(items, key=sort_key, reverse=reverse)
                    
            except Exception:
                return list(items)
        
        selector = create_selector(
            base_selector,
            sort_selector,
            name=selector_name
        )
        
        self._created_selectors[selector_name] = selector
        return selector
    
    def create_computed_selector(
        self,
        *dependencies,
        compute_fn: Callable,
        name: Optional[str] = None
    ) -> Selector:
        """
        Create a selector that computes a derived value from multiple dependencies.
        
        Args:
            *dependencies: Input selectors or functions
            compute_fn: Function to compute final result
            name: Optional selector name
            
        Returns:
            Selector that computes derived value
        """
        selector_name = name or f"computed_{id(compute_fn)}"
        
        if selector_name in self._created_selectors:
            return self._created_selectors[selector_name]
        
        selector = create_selector(
            *dependencies,
            output_fn=compute_fn,
            name=selector_name
        )
        
        self._created_selectors[selector_name] = selector
        return selector
    
    def get_created_selectors(self) -> Dict[str, Selector]:
        """Get all selectors created by this factory."""
        return self._created_selectors.copy()
    
    def clear_cache(self):
        """Clear factory selector cache."""
        self._created_selectors.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get factory statistics."""
        return {
            'created_selectors': len(self._created_selectors),
            'selector_names': list(self._created_selectors.keys())
        }


# Global factory instance
default_factory = SelectorFactory('default')