"""
Repository pattern interface for multi-backend storage.

This module provides abstract base classes for synchronous and asynchronous
repository implementations, ensuring a consistent interface across all storage backends.
"""

from abc import ABC, abstractmethod
from typing import (
    Generic, TypeVar, Optional, List, Dict, Any, Union, 
    AsyncIterator, Iterator, Tuple
)
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import uuid


# Type variable for entity types
T = TypeVar('T')


class SortOrder(Enum):
    """Sort order for queries."""
    ASC = "asc"
    DESC = "desc"


@dataclass
class QueryFilter:
    """Filter criteria for queries."""
    field: str
    operator: str  # eq, ne, gt, lt, gte, lte, in, like, contains
    value: Any
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "field": self.field,
            "operator": self.operator,
            "value": self.value
        }


@dataclass
class Pagination:
    """Pagination parameters."""
    page: int = 1
    per_page: int = 50
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries."""
        return (self.page - 1) * self.per_page
    
    @property
    def limit(self) -> int:
        """Alias for per_page."""
        return self.per_page


@dataclass
class PaginatedResult(Generic[T]):
    """Result container for paginated queries."""
    items: List[T]
    total: int
    page: int
    per_page: int
    
    @property
    def pages(self) -> int:
        """Calculate total number of pages."""
        return (self.total + self.per_page - 1) // self.per_page
    
    @property
    def has_next(self) -> bool:
        """Check if there's a next page."""
        return self.page < self.pages
    
    @property
    def has_prev(self) -> bool:
        """Check if there's a previous page."""
        return self.page > 1


class Repository(ABC, Generic[T]):
    """
    Abstract base class for synchronous repository implementations.
    
    Provides CRUD operations and query capabilities for entities.
    """
    
    @abstractmethod
    def create(self, entity: T) -> T:
        """
        Create a new entity.
        
        Args:
            entity: The entity to create
            
        Returns:
            The created entity with generated ID
            
        Raises:
            StorageError: If creation fails
        """
        pass
    
    @abstractmethod
    def get(self, entity_id: str) -> Optional[T]:
        """
        Retrieve an entity by ID.
        
        Args:
            entity_id: The unique identifier
            
        Returns:
            The entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    def update(self, entity: T) -> T:
        """
        Update an existing entity.
        
        Args:
            entity: The entity with updated values
            
        Returns:
            The updated entity
            
        Raises:
            StorageError: If update fails
            NotFoundError: If entity doesn't exist
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: str) -> bool:
        """
        Delete an entity by ID.
        
        Args:
            entity_id: The unique identifier
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abstractmethod
    def list(
        self,
        filters: Optional[List[QueryFilter]] = None,
        sort_by: Optional[str] = None,
        sort_order: SortOrder = SortOrder.ASC,
        pagination: Optional[Pagination] = None
    ) -> Union[List[T], PaginatedResult[T]]:
        """
        List entities with optional filtering, sorting, and pagination.
        
        Args:
            filters: List of filter criteria
            sort_by: Field to sort by
            sort_order: Sort direction
            pagination: Pagination parameters
            
        Returns:
            List of entities or paginated result
        """
        pass
    
    @abstractmethod
    def count(self, filters: Optional[List[QueryFilter]] = None) -> int:
        """
        Count entities matching filters.
        
        Args:
            filters: List of filter criteria
            
        Returns:
            Number of matching entities
        """
        pass
    
    @abstractmethod
    def exists(self, entity_id: str) -> bool:
        """
        Check if an entity exists.
        
        Args:
            entity_id: The unique identifier
            
        Returns:
            True if exists, False otherwise
        """
        pass
    
    @abstractmethod
    def bulk_create(self, entities: List[T]) -> List[T]:
        """
        Create multiple entities in a single operation.
        
        Args:
            entities: List of entities to create
            
        Returns:
            List of created entities with IDs
            
        Raises:
            StorageError: If bulk creation fails
        """
        pass
    
    @abstractmethod
    def bulk_update(self, entities: List[T]) -> List[T]:
        """
        Update multiple entities in a single operation.
        
        Args:
            entities: List of entities to update
            
        Returns:
            List of updated entities
            
        Raises:
            StorageError: If bulk update fails
        """
        pass
    
    @abstractmethod
    def bulk_delete(self, entity_ids: List[str]) -> int:
        """
        Delete multiple entities in a single operation.
        
        Args:
            entity_ids: List of entity IDs to delete
            
        Returns:
            Number of entities deleted
        """
        pass
    
    @abstractmethod
    def search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        pagination: Optional[Pagination] = None
    ) -> Union[List[T], PaginatedResult[T]]:
        """
        Full-text search across entities.
        
        Args:
            query: Search query string
            fields: Fields to search in (None = all searchable fields)
            pagination: Pagination parameters
            
        Returns:
            Search results
        """
        pass
    
    @abstractmethod
    def transaction(self):
        """
        Start a transaction context.
        
        Usage:
            with repo.transaction():
                repo.create(entity1)
                repo.update(entity2)
                # Commits on success, rolls back on exception
        """
        pass


class AsyncRepository(ABC, Generic[T]):
    """
    Abstract base class for asynchronous repository implementations.
    
    Provides async CRUD operations and query capabilities for entities.
    """
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Async version of create."""
        pass
    
    @abstractmethod
    async def get(self, entity_id: str) -> Optional[T]:
        """Async version of get."""
        pass
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """Async version of update."""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """Async version of delete."""
        pass
    
    @abstractmethod
    async def list(
        self,
        filters: Optional[List[QueryFilter]] = None,
        sort_by: Optional[str] = None,
        sort_order: SortOrder = SortOrder.ASC,
        pagination: Optional[Pagination] = None
    ) -> Union[List[T], PaginatedResult[T]]:
        """Async version of list."""
        pass
    
    @abstractmethod
    async def count(self, filters: Optional[List[QueryFilter]] = None) -> int:
        """Async version of count."""
        pass
    
    @abstractmethod
    async def exists(self, entity_id: str) -> bool:
        """Async version of exists."""
        pass
    
    @abstractmethod
    async def bulk_create(self, entities: List[T]) -> List[T]:
        """Async version of bulk_create."""
        pass
    
    @abstractmethod
    async def bulk_update(self, entities: List[T]) -> List[T]:
        """Async version of bulk_update."""
        pass
    
    @abstractmethod
    async def bulk_delete(self, entity_ids: List[str]) -> int:
        """Async version of bulk_delete."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        pagination: Optional[Pagination] = None
    ) -> Union[List[T], PaginatedResult[T]]:
        """Async version of search."""
        pass
    
    @abstractmethod
    async def transaction(self):
        """Async transaction context."""
        pass
    
    @abstractmethod
    async def stream(
        self,
        filters: Optional[List[QueryFilter]] = None,
        batch_size: int = 100
    ) -> AsyncIterator[T]:
        """
        Stream entities in batches for memory-efficient processing.
        
        Args:
            filters: Optional filters to apply
            batch_size: Number of entities per batch
            
        Yields:
            Entities one at a time
        """
        pass


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class NotFoundError(StorageError):
    """Entity not found exception."""
    pass


class DuplicateError(StorageError):
    """Duplicate entity exception."""
    pass


class TransactionError(StorageError):
    """Transaction failed exception."""
    pass