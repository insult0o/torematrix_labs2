"""
Bookmark System for Hierarchical Element List

Provides comprehensive bookmark functionality for quick navigation
to important elements with categories, search, and persistence.
"""

import logging
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class BookmarkType(Enum):
    """Types of bookmarks"""
    ELEMENT = "element"
    SELECTION = "selection"
    VIEW_STATE = "view_state"
    SEARCH_RESULT = "search_result"


@dataclass
class Bookmark:
    """Represents a single bookmark"""
    bookmark_id: str
    name: str
    bookmark_type: BookmarkType
    element_id: Optional[str] = None
    element_ids: List[str] = field(default_factory=list)
    category: str = "General"
    description: str = ""
    icon: Optional[str] = None
    color: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    view_state: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    is_pinned: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert bookmark to dictionary for serialization"""
        data = asdict(self)
        data['tags'] = list(self.tags)
        data['bookmark_type'] = self.bookmark_type.value
        data['created_at'] = self.created_at.isoformat()
        if self.last_accessed:
            data['last_accessed'] = self.last_accessed.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Bookmark':
        """Create bookmark from dictionary"""
        if 'tags' in data and isinstance(data['tags'], list):
            data['tags'] = set(data['tags'])
        if 'bookmark_type' in data and isinstance(data['bookmark_type'], str):
            data['bookmark_type'] = BookmarkType(data['bookmark_type'])
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'last_accessed' in data and isinstance(data['last_accessed'], str):
            data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
        return cls(**data)
    
    def update_access(self) -> None:
        """Update access tracking"""
        self.last_accessed = datetime.now()
        self.access_count += 1


@dataclass
class BookmarkCategory:
    """Represents a bookmark category"""
    category_id: str
    name: str
    description: str = ""
    icon: Optional[str] = None
    color: Optional[str] = None
    parent_category: Optional[str] = None
    is_system_category: bool = False
    bookmark_count: int = 0


class BookmarkSystem(QObject):
    """
    Comprehensive bookmark system for hierarchical element list
    
    Provides bookmark management with categories, search, import/export,
    and intelligent suggestions for navigation.
    """
    
    # Signals
    bookmark_added = pyqtSignal(object)  # Bookmark
    bookmark_removed = pyqtSignal(str)  # bookmark_id
    bookmark_updated = pyqtSignal(object)  # Bookmark
    bookmark_accessed = pyqtSignal(object)  # Bookmark
    bookmark_navigation_requested = pyqtSignal(str, list)  # element_id, path
    category_added = pyqtSignal(object)  # BookmarkCategory
    category_removed = pyqtSignal(str)  # category_id
    
    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        
        # Configuration
        self.max_bookmarks = 500
        self.auto_cleanup_days = 30
        self.enable_suggestions = True
        self.max_recent_bookmarks = 20
        
        # State
        self._bookmarks: Dict[str, Bookmark] = {}
        self._categories: Dict[str, BookmarkCategory] = {}
        self._bookmark_index: Dict[str, Set[str]] = {}  # element_id -> bookmark_ids
        self._tag_index: Dict[str, Set[str]] = {}  # tag -> bookmark_ids
        self._recent_bookmarks: List[str] = []  # bookmark_ids in order
        
        # Storage
        self._storage_provider = None
        self._auto_save = True
        
        # Setup default categories
        self._setup_default_categories()
        
        logger.info("BookmarkSystem initialized")
    
    def set_storage_provider(self, provider) -> None:
        """Set storage provider for bookmark persistence"""
        self._storage_provider = provider
        self._load_bookmarks()
        logger.debug("Storage provider set for bookmarks")
    
    def add_bookmark(self, name: str, element_id: Optional[str] = None, 
                    element_ids: Optional[List[str]] = None,
                    bookmark_type: BookmarkType = BookmarkType.ELEMENT,
                    category: str = "General", **kwargs) -> Optional[Bookmark]:
        """
        Add a new bookmark
        
        Args:
            name: Bookmark name
            element_id: Single element ID (for ELEMENT type)
            element_ids: Multiple element IDs (for SELECTION type)
            bookmark_type: Type of bookmark
            category: Category for the bookmark
            **kwargs: Additional bookmark properties
            
        Returns:
            Created Bookmark object or None if failed
        """
        if len(self._bookmarks) >= self.max_bookmarks:
            logger.warning(f"Cannot add more than {self.max_bookmarks} bookmarks")
            return None
        
        # Generate unique ID
        bookmark_id = self._generate_bookmark_id(name)
        
        # Validate inputs
        if bookmark_type == BookmarkType.ELEMENT and not element_id:
            logger.error("Element bookmark requires element_id")
            return None
        elif bookmark_type == BookmarkType.SELECTION and not element_ids:
            logger.error("Selection bookmark requires element_ids")
            return None
        
        # Create bookmark
        bookmark = Bookmark(
            bookmark_id=bookmark_id,
            name=name,
            bookmark_type=bookmark_type,
            element_id=element_id,
            element_ids=element_ids or [],
            category=category,
            **kwargs
        )
        
        # Add to collections
        self._bookmarks[bookmark_id] = bookmark
        self._update_indices(bookmark)
        self._update_category_count(category, 1)
        
        # Update recent bookmarks
        if bookmark_id in self._recent_bookmarks:
            self._recent_bookmarks.remove(bookmark_id)
        self._recent_bookmarks.insert(0, bookmark_id)
        if len(self._recent_bookmarks) > self.max_recent_bookmarks:
            self._recent_bookmarks = self._recent_bookmarks[:self.max_recent_bookmarks]
        
        # Save if auto-save enabled
        if self._auto_save:
            self._save_bookmarks()
        
        self.bookmark_added.emit(bookmark)
        logger.debug(f"Added bookmark: {name}")
        return bookmark
    
    def remove_bookmark(self, bookmark_id: str) -> bool:
        """
        Remove a bookmark
        
        Args:
            bookmark_id: ID of bookmark to remove
            
        Returns:
            True if bookmark was removed
        """
        if bookmark_id not in self._bookmarks:
            return False
        
        bookmark = self._bookmarks[bookmark_id]
        
        # Remove from collections
        del self._bookmarks[bookmark_id]
        self._remove_from_indices(bookmark)
        self._update_category_count(bookmark.category, -1)
        
        # Remove from recent bookmarks
        if bookmark_id in self._recent_bookmarks:
            self._recent_bookmarks.remove(bookmark_id)
        
        # Save if auto-save enabled
        if self._auto_save:
            self._save_bookmarks()
        
        self.bookmark_removed.emit(bookmark_id)
        logger.debug(f"Removed bookmark: {bookmark.name}")
        return True
    
    def update_bookmark(self, bookmark_id: str, **updates) -> bool:
        """
        Update an existing bookmark
        
        Args:
            bookmark_id: ID of bookmark to update
            **updates: Fields to update
            
        Returns:
            True if bookmark was updated
        """
        if bookmark_id not in self._bookmarks:
            return False
        
        bookmark = self._bookmarks[bookmark_id]
        old_category = bookmark.category
        
        # Update bookmark
        for key, value in updates.items():
            if hasattr(bookmark, key):
                setattr(bookmark, key, value)
        
        # Update indices
        self._remove_from_indices(bookmark)
        self._update_indices(bookmark)
        
        # Update category counts if category changed
        if 'category' in updates and updates['category'] != old_category:
            self._update_category_count(old_category, -1)
            self._update_category_count(bookmark.category, 1)
        
        # Save if auto-save enabled
        if self._auto_save:
            self._save_bookmarks()
        
        self.bookmark_updated.emit(bookmark)
        logger.debug(f"Updated bookmark: {bookmark.name}")
        return True
    
    def get_bookmark(self, bookmark_id: str) -> Optional[Bookmark]:
        """Get bookmark by ID"""
        return self._bookmarks.get(bookmark_id)
    
    def get_bookmarks_by_element(self, element_id: str) -> List[Bookmark]:
        """Get all bookmarks for a specific element"""
        bookmark_ids = self._bookmark_index.get(element_id, set())
        return [self._bookmarks[bid] for bid in bookmark_ids if bid in self._bookmarks]
    
    def get_bookmarks_by_category(self, category: str) -> List[Bookmark]:
        """Get all bookmarks in a category"""
        return [b for b in self._bookmarks.values() if b.category == category]
    
    def get_bookmarks_by_tag(self, tag: str) -> List[Bookmark]:
        """Get all bookmarks with a specific tag"""
        bookmark_ids = self._tag_index.get(tag, set())
        return [self._bookmarks[bid] for bid in bookmark_ids if bid in self._bookmarks]
    
    def search_bookmarks(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Bookmark]:
        """
        Search bookmarks by name, description, or tags
        
        Args:
            query: Search query
            filters: Additional filters (category, type, etc.)
            
        Returns:
            List of matching bookmarks
        """
        query_lower = query.lower()
        results = []
        
        for bookmark in self._bookmarks.values():
            # Text matching
            if (query_lower in bookmark.name.lower() or
                query_lower in bookmark.description.lower() or
                any(query_lower in tag.lower() for tag in bookmark.tags)):
                
                # Apply filters
                if filters:
                    if 'category' in filters and bookmark.category != filters['category']:
                        continue
                    if 'type' in filters and bookmark.bookmark_type != filters['type']:
                        continue
                    if 'is_pinned' in filters and bookmark.is_pinned != filters['is_pinned']:
                        continue
                
                results.append(bookmark)
        
        # Sort by relevance (access count, recency, etc.)
        results.sort(key=lambda b: (b.access_count, b.last_accessed or b.created_at), reverse=True)
        
        return results
    
    def navigate_to_bookmark(self, bookmark_id: str) -> bool:
        """
        Navigate to a bookmark
        
        Args:
            bookmark_id: ID of bookmark to navigate to
            
        Returns:
            True if navigation was successful
        """
        if bookmark_id not in self._bookmarks:
            return False
        
        bookmark = self._bookmarks[bookmark_id]
        bookmark.update_access()
        
        # Update recent bookmarks
        if bookmark_id in self._recent_bookmarks:
            self._recent_bookmarks.remove(bookmark_id)
        self._recent_bookmarks.insert(0, bookmark_id)
        
        # Emit navigation signal based on bookmark type
        if bookmark.bookmark_type == BookmarkType.ELEMENT and bookmark.element_id:
            self.bookmark_navigation_requested.emit(bookmark.element_id, [])
        elif bookmark.bookmark_type == BookmarkType.SELECTION and bookmark.element_ids:
            # Navigate to first element in selection
            self.bookmark_navigation_requested.emit(bookmark.element_ids[0], bookmark.element_ids)
        
        # Save if auto-save enabled
        if self._auto_save:
            self._save_bookmarks()
        
        self.bookmark_accessed.emit(bookmark)
        logger.debug(f"Navigated to bookmark: {bookmark.name}")
        return True
    
    def get_recent_bookmarks(self, limit: Optional[int] = None) -> List[Bookmark]:
        """Get recently accessed bookmarks"""
        limit = limit or self.max_recent_bookmarks
        recent_ids = self._recent_bookmarks[:limit]
        return [self._bookmarks[bid] for bid in recent_ids if bid in self._bookmarks]
    
    def get_pinned_bookmarks(self) -> List[Bookmark]:
        """Get all pinned bookmarks"""
        return [b for b in self._bookmarks.values() if b.is_pinned]
    
    def get_popular_bookmarks(self, limit: int = 10) -> List[Bookmark]:
        """Get most accessed bookmarks"""
        sorted_bookmarks = sorted(self._bookmarks.values(), 
                                key=lambda b: b.access_count, reverse=True)
        return sorted_bookmarks[:limit]
    
    def add_category(self, category_id: str, name: str, **kwargs) -> BookmarkCategory:
        """Add a new bookmark category"""
        if category_id in self._categories:
            logger.warning(f"Category '{category_id}' already exists")
            return self._categories[category_id]
        
        category = BookmarkCategory(
            category_id=category_id,
            name=name,
            **kwargs
        )
        
        self._categories[category_id] = category
        
        self.category_added.emit(category)
        logger.debug(f"Added category: {name}")
        return category
    
    def remove_category(self, category_id: str, move_to_category: str = "General") -> bool:
        """
        Remove a category and move its bookmarks
        
        Args:
            category_id: ID of category to remove
            move_to_category: Category to move bookmarks to
            
        Returns:
            True if category was removed
        """
        if category_id not in self._categories:
            return False
        
        category = self._categories[category_id]
        
        if category.is_system_category:
            logger.warning(f"Cannot remove system category: {category_id}")
            return False
        
        # Move bookmarks to new category
        for bookmark in self._bookmarks.values():
            if bookmark.category == category_id:
                bookmark.category = move_to_category
        
        # Remove category
        del self._categories[category_id]
        
        # Update category counts
        self._recalculate_category_counts()
        
        self.category_removed.emit(category_id)
        logger.debug(f"Removed category: {category.name}")
        return True
    
    def get_categories(self) -> List[BookmarkCategory]:
        """Get all bookmark categories"""
        return list(self._categories.values())
    
    def import_bookmarks(self, bookmarks_data: List[Dict[str, Any]]) -> int:
        """
        Import bookmarks from data
        
        Args:
            bookmarks_data: List of bookmark dictionaries
            
        Returns:
            Number of bookmarks imported
        """
        imported_count = 0
        
        for data in bookmarks_data:
            try:
                bookmark = Bookmark.from_dict(data)
                
                # Check for duplicates
                if bookmark.bookmark_id in self._bookmarks:
                    # Generate new ID
                    bookmark.bookmark_id = self._generate_bookmark_id(bookmark.name)
                
                # Add bookmark
                self._bookmarks[bookmark.bookmark_id] = bookmark
                self._update_indices(bookmark)
                self._update_category_count(bookmark.category, 1)
                
                imported_count += 1
                
            except Exception as e:
                logger.warning(f"Failed to import bookmark: {e}")
        
        # Save if auto-save enabled
        if self._auto_save:
            self._save_bookmarks()
        
        logger.info(f"Imported {imported_count} bookmarks")
        return imported_count
    
    def export_bookmarks(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Export bookmarks to data format
        
        Args:
            category: Optional category filter
            
        Returns:
            List of bookmark dictionaries
        """
        bookmarks_to_export = self._bookmarks.values()
        
        if category:
            bookmarks_to_export = [b for b in bookmarks_to_export if b.category == category]
        
        return [bookmark.to_dict() for bookmark in bookmarks_to_export]
    
    def cleanup_old_bookmarks(self) -> int:
        """
        Clean up old, unused bookmarks
        
        Returns:
            Number of bookmarks removed
        """
        if self.auto_cleanup_days <= 0:
            return 0
        
        cutoff_date = datetime.now().timestamp() - (self.auto_cleanup_days * 24 * 3600)
        to_remove = []
        
        for bookmark_id, bookmark in self._bookmarks.items():
            # Don't remove pinned bookmarks
            if bookmark.is_pinned:
                continue
            
            # Check if bookmark is old and unused
            last_access = bookmark.last_accessed or bookmark.created_at
            if (last_access.timestamp() < cutoff_date and 
                bookmark.access_count == 0):
                to_remove.append(bookmark_id)
        
        # Remove old bookmarks
        for bookmark_id in to_remove:
            self.remove_bookmark(bookmark_id)
        
        logger.info(f"Cleaned up {len(to_remove)} old bookmarks")
        return len(to_remove)
    
    def _setup_default_categories(self) -> None:
        """Setup default bookmark categories"""
        default_categories = [
            BookmarkCategory("general", "General", "General bookmarks", is_system_category=True),
            BookmarkCategory("favorites", "Favorites", "Favorite elements", is_system_category=True),
            BookmarkCategory("recent", "Recent", "Recently accessed", is_system_category=True),
            BookmarkCategory("work", "Work", "Work-related bookmarks"),
            BookmarkCategory("reference", "Reference", "Reference materials"),
        ]
        
        for category in default_categories:
            self._categories[category.category_id] = category
        
        logger.debug(f"Setup {len(default_categories)} default categories")
    
    def _generate_bookmark_id(self, name: str) -> str:
        """Generate unique bookmark ID"""
        import hashlib
        import time
        
        base_id = name.lower().replace(" ", "_")
        timestamp = str(int(time.time()))
        unique_str = f"{base_id}_{timestamp}"
        
        return hashlib.md5(unique_str.encode()).hexdigest()[:16]
    
    def _update_indices(self, bookmark: Bookmark) -> None:
        """Update bookmark indices"""
        # Update element index
        if bookmark.element_id:
            if bookmark.element_id not in self._bookmark_index:
                self._bookmark_index[bookmark.element_id] = set()
            self._bookmark_index[bookmark.element_id].add(bookmark.bookmark_id)
        
        for element_id in bookmark.element_ids:
            if element_id not in self._bookmark_index:
                self._bookmark_index[element_id] = set()
            self._bookmark_index[element_id].add(bookmark.bookmark_id)
        
        # Update tag index
        for tag in bookmark.tags:
            if tag not in self._tag_index:
                self._tag_index[tag] = set()
            self._tag_index[tag].add(bookmark.bookmark_id)
    
    def _remove_from_indices(self, bookmark: Bookmark) -> None:
        """Remove bookmark from indices"""
        # Remove from element index
        if bookmark.element_id and bookmark.element_id in self._bookmark_index:
            self._bookmark_index[bookmark.element_id].discard(bookmark.bookmark_id)
            if not self._bookmark_index[bookmark.element_id]:
                del self._bookmark_index[bookmark.element_id]
        
        for element_id in bookmark.element_ids:
            if element_id in self._bookmark_index:
                self._bookmark_index[element_id].discard(bookmark.bookmark_id)
                if not self._bookmark_index[element_id]:
                    del self._bookmark_index[element_id]
        
        # Remove from tag index
        for tag in bookmark.tags:
            if tag in self._tag_index:
                self._tag_index[tag].discard(bookmark.bookmark_id)
                if not self._tag_index[tag]:
                    del self._tag_index[tag]
    
    def _update_category_count(self, category_id: str, delta: int) -> None:
        """Update bookmark count for category"""
        if category_id in self._categories:
            self._categories[category_id].bookmark_count = max(
                0, self._categories[category_id].bookmark_count + delta
            )
    
    def _recalculate_category_counts(self) -> None:
        """Recalculate all category bookmark counts"""
        # Reset counts
        for category in self._categories.values():
            category.bookmark_count = 0
        
        # Count bookmarks
        for bookmark in self._bookmarks.values():
            if bookmark.category in self._categories:
                self._categories[bookmark.category].bookmark_count += 1
    
    def _save_bookmarks(self) -> None:
        """Save bookmarks to storage"""
        if not self._storage_provider:
            return
        
        try:
            data = {
                'bookmarks': [b.to_dict() for b in self._bookmarks.values()],
                'categories': [asdict(c) for c in self._categories.values()],
                'recent_bookmarks': self._recent_bookmarks
            }
            
            self._storage_provider.save_component_data('bookmarks', data)
            logger.debug("Saved bookmarks to storage")
            
        except Exception as e:
            logger.error(f"Failed to save bookmarks: {e}")
    
    def _load_bookmarks(self) -> None:
        """Load bookmarks from storage"""
        if not self._storage_provider:
            return
        
        try:
            data = self._storage_provider.get_component_data('bookmarks')
            if not data:
                return
            
            # Load bookmarks
            if 'bookmarks' in data:
                for bookmark_data in data['bookmarks']:
                    bookmark = Bookmark.from_dict(bookmark_data)
                    self._bookmarks[bookmark.bookmark_id] = bookmark
                    self._update_indices(bookmark)
            
            # Load categories
            if 'categories' in data:
                for category_data in data['categories']:
                    category = BookmarkCategory(**category_data)
                    self._categories[category.category_id] = category
            
            # Load recent bookmarks
            if 'recent_bookmarks' in data:
                self._recent_bookmarks = data['recent_bookmarks']
            
            logger.info(f"Loaded {len(self._bookmarks)} bookmarks from storage")
            
        except Exception as e:
            logger.error(f"Failed to load bookmarks: {e}")
    
    def get_bookmark_statistics(self) -> Dict[str, Any]:
        """Get bookmark system statistics"""
        return {
            "total_bookmarks": len(self._bookmarks),
            "total_categories": len(self._categories),
            "pinned_bookmarks": len(self.get_pinned_bookmarks()),
            "recent_bookmarks": len(self._recent_bookmarks),
            "total_tags": len(self._tag_index),
            "total_access_count": sum(b.access_count for b in self._bookmarks.values())
        }