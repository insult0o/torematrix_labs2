"""
Bookmark System for Hierarchical Element List

Provides bookmark functionality for quick navigation to frequently accessed
elements and locations within the hierarchical tree structure.
"""

import logging
import json
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, QLabel, QLineEdit, QDialog, QDialogButtonBox, QTextEdit
from PyQt6.QtGui import QIcon

logger = logging.getLogger(__name__)


@dataclass
class Bookmark:
    """Single bookmark entry"""
    bookmark_id: str
    name: str
    element_id: str
    element_path: List[str]  # Path from root to element
    description: str = ""
    tags: Set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    is_favorite: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_access(self):
        """Update access information"""
        self.accessed_at = datetime.now()
        self.access_count += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['created_at'] = self.created_at.isoformat()
        data['accessed_at'] = self.accessed_at.isoformat()
        # Convert set to list
        data['tags'] = list(self.tags)
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Bookmark':
        """Create bookmark from dictionary"""
        # Convert ISO strings back to datetime
        if isinstance(data.get('created_at'), str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data.get('accessed_at'), str):
            data['accessed_at'] = datetime.fromisoformat(data['accessed_at'])
        # Convert list back to set
        if isinstance(data.get('tags'), list):
            data['tags'] = set(data['tags'])
        
        return cls(**data)


@dataclass
class BookmarkCategory:
    """Category for organizing bookmarks"""
    category_id: str
    name: str
    description: str = ""
    icon: Optional[str] = None
    color: Optional[str] = None
    bookmark_ids: Set[str] = field(default_factory=set)
    is_expanded: bool = True
    
    def add_bookmark(self, bookmark_id: str):
        """Add bookmark to this category"""
        self.bookmark_ids.add(bookmark_id)
    
    def remove_bookmark(self, bookmark_id: str):
        """Remove bookmark from this category"""
        self.bookmark_ids.discard(bookmark_id)


class BookmarkSystem(QObject):
    """
    Comprehensive bookmark system for hierarchical element navigation
    
    Provides bookmark management, categorization, search, and persistence
    for quick navigation within element trees.
    """
    
    # Signals
    bookmark_added = pyqtSignal(object)  # Bookmark
    bookmark_removed = pyqtSignal(str)  # bookmark_id
    bookmark_updated = pyqtSignal(object)  # Bookmark
    bookmark_accessed = pyqtSignal(str)  # bookmark_id
    category_added = pyqtSignal(object)  # BookmarkCategory
    category_removed = pyqtSignal(str)  # category_id
    bookmarks_loaded = pyqtSignal(int)  # count
    bookmark_navigation_requested = pyqtSignal(str, list)  # element_id, path
    
    def __init__(self, parent: Optional[QObject] = None):
        """
        Initialize bookmark system
        
        Args:
            parent: Parent QObject
        """
        super().__init__(parent)
        
        # Configuration
        self.auto_save = True
        self.save_delay = 2000  # 2 seconds
        self.max_bookmarks = 1000
        self.max_recent_bookmarks = 20
        
        # State
        self._bookmarks: Dict[str, Bookmark] = {}
        self._categories: Dict[str, BookmarkCategory] = {}
        self._recent_bookmarks: List[str] = []  # Recent bookmark IDs
        self._bookmark_file: Optional[Path] = None
        
        # Auto-save timer
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_bookmarks)
        
        # Initialize default categories
        self._initialize_default_categories()
        
        logger.info("BookmarkSystem initialized")
    
    def set_bookmark_file(self, file_path: Path) -> None:
        """
        Set the file path for bookmark persistence
        
        Args:
            file_path: Path to bookmark file
        """
        self._bookmark_file = file_path
        logger.debug(f"Bookmark file set to: {file_path}")
    
    def add_bookmark(self, 
                    element_id: str, 
                    element_path: List[str],
                    name: Optional[str] = None,
                    description: str = "",
                    tags: Optional[Set[str]] = None,
                    category_id: Optional[str] = None) -> Bookmark:
        """
        Add a new bookmark
        
        Args:
            element_id: ID of element to bookmark
            element_path: Path from root to element
            name: Display name for bookmark
            description: Bookmark description
            tags: Set of tags for bookmark
            category_id: Category to add bookmark to
            
        Returns:
            Created bookmark
        """
        # Generate bookmark ID
        bookmark_id = f"bookmark_{len(self._bookmarks)}_{int(datetime.now().timestamp())}"
        
        # Generate name if not provided
        if name is None:
            if element_path:
                name = element_path[-1]  # Use last element in path
            else:
                name = f"Element {element_id[:8]}"
        
        # Create bookmark
        bookmark = Bookmark(
            bookmark_id=bookmark_id,
            name=name,
            element_id=element_id,
            element_path=element_path.copy(),
            description=description,
            tags=tags or set()
        )
        
        # Check for duplicates
        if self._has_duplicate_bookmark(element_id):
            logger.warning(f"Bookmark for element {element_id} already exists")
            return self._get_bookmark_by_element_id(element_id)
        
        # Add to bookmarks
        self._bookmarks[bookmark_id] = bookmark
        
        # Add to category if specified
        if category_id and category_id in self._categories:
            self._categories[category_id].add_bookmark(bookmark_id)
        else:
            # Add to default category
            self._categories["default"].add_bookmark(bookmark_id)
        
        # Update recent bookmarks
        self._update_recent_bookmarks(bookmark_id)
        
        # Schedule save
        self._schedule_save()
        
        logger.info(f"Added bookmark: {name} ({bookmark_id})")
        self.bookmark_added.emit(bookmark)
        
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
            logger.warning(f"Bookmark not found: {bookmark_id}")
            return False
        
        bookmark = self._bookmarks[bookmark_id]
        
        # Remove from categories
        for category in self._categories.values():
            category.remove_bookmark(bookmark_id)
        
        # Remove from recent bookmarks
        if bookmark_id in self._recent_bookmarks:
            self._recent_bookmarks.remove(bookmark_id)
        
        # Remove bookmark
        del self._bookmarks[bookmark_id]
        
        # Schedule save
        self._schedule_save()
        
        logger.info(f"Removed bookmark: {bookmark.name} ({bookmark_id})")
        self.bookmark_removed.emit(bookmark_id)
        
        return True
    
    def update_bookmark(self, bookmark_id: str, **kwargs) -> bool:
        """
        Update bookmark properties
        
        Args:
            bookmark_id: ID of bookmark to update
            **kwargs: Properties to update
            
        Returns:
            True if bookmark was updated
        """
        if bookmark_id not in self._bookmarks:
            logger.warning(f"Bookmark not found: {bookmark_id}")
            return False
        
        bookmark = self._bookmarks[bookmark_id]
        
        # Update properties
        for key, value in kwargs.items():
            if hasattr(bookmark, key):
                setattr(bookmark, key, value)
        
        # Schedule save
        self._schedule_save()
        
        logger.debug(f"Updated bookmark: {bookmark.name} ({bookmark_id})")
        self.bookmark_updated.emit(bookmark)
        
        return True
    
    def access_bookmark(self, bookmark_id: str) -> bool:
        """
        Access a bookmark (updates access statistics and navigates)
        
        Args:
            bookmark_id: ID of bookmark to access
            
        Returns:
            True if bookmark was accessed
        """
        if bookmark_id not in self._bookmarks:
            logger.warning(f"Bookmark not found: {bookmark_id}")
            return False
        
        bookmark = self._bookmarks[bookmark_id]
        
        # Update access information
        bookmark.update_access()
        
        # Update recent bookmarks
        self._update_recent_bookmarks(bookmark_id)
        
        # Schedule save
        self._schedule_save()
        
        logger.info(f"Accessed bookmark: {bookmark.name} ({bookmark_id})")
        self.bookmark_accessed.emit(bookmark_id)
        self.bookmark_navigation_requested.emit(bookmark.element_id, bookmark.element_path)
        
        return True
    
    def get_bookmark(self, bookmark_id: str) -> Optional[Bookmark]:
        """
        Get bookmark by ID
        
        Args:
            bookmark_id: Bookmark ID
            
        Returns:
            Bookmark if found, None otherwise
        """
        return self._bookmarks.get(bookmark_id)
    
    def get_all_bookmarks(self) -> List[Bookmark]:
        """
        Get all bookmarks
        
        Returns:
            List of all bookmarks
        """
        return list(self._bookmarks.values())
    
    def get_bookmarks_by_category(self, category_id: str) -> List[Bookmark]:
        """
        Get bookmarks in a specific category
        
        Args:
            category_id: Category ID
            
        Returns:
            List of bookmarks in category
        """
        if category_id not in self._categories:
            return []
        
        category = self._categories[category_id]
        bookmarks = []
        
        for bookmark_id in category.bookmark_ids:
            if bookmark_id in self._bookmarks:
                bookmarks.append(self._bookmarks[bookmark_id])
        
        return bookmarks
    
    def get_recent_bookmarks(self, limit: Optional[int] = None) -> List[Bookmark]:
        """
        Get recently accessed bookmarks
        
        Args:
            limit: Maximum number of bookmarks to return
            
        Returns:
            List of recent bookmarks
        """
        limit = limit or self.max_recent_bookmarks
        recent_ids = self._recent_bookmarks[:limit]
        
        bookmarks = []
        for bookmark_id in recent_ids:
            if bookmark_id in self._bookmarks:
                bookmarks.append(self._bookmarks[bookmark_id])
        
        return bookmarks
    
    def get_favorite_bookmarks(self) -> List[Bookmark]:
        """
        Get favorite bookmarks
        
        Returns:
            List of favorite bookmarks
        """
        return [bookmark for bookmark in self._bookmarks.values() if bookmark.is_favorite]
    
    def search_bookmarks(self, query: str, include_tags: bool = True) -> List[Bookmark]:
        """
        Search bookmarks by name, description, or tags
        
        Args:
            query: Search query
            include_tags: Whether to search in tags
            
        Returns:
            List of matching bookmarks
        """
        query_lower = query.lower()
        matching_bookmarks = []
        
        for bookmark in self._bookmarks.values():
            # Search in name and description
            if (query_lower in bookmark.name.lower() or 
                query_lower in bookmark.description.lower()):
                matching_bookmarks.append(bookmark)
                continue
            
            # Search in tags if enabled
            if include_tags:
                for tag in bookmark.tags:
                    if query_lower in tag.lower():
                        matching_bookmarks.append(bookmark)
                        break
        
        return matching_bookmarks
    
    def add_category(self, name: str, description: str = "", icon: Optional[str] = None) -> BookmarkCategory:
        """
        Add a new bookmark category
        
        Args:
            name: Category name
            description: Category description
            icon: Category icon
            
        Returns:
            Created category
        """
        category_id = f"category_{len(self._categories)}_{int(datetime.now().timestamp())}"
        
        category = BookmarkCategory(
            category_id=category_id,
            name=name,
            description=description,
            icon=icon
        )
        
        self._categories[category_id] = category
        
        # Schedule save
        self._schedule_save()
        
        logger.info(f"Added bookmark category: {name} ({category_id})")
        self.category_added.emit(category)
        
        return category
    
    def remove_category(self, category_id: str, move_bookmarks_to: Optional[str] = None) -> bool:
        """
        Remove a bookmark category
        
        Args:
            category_id: ID of category to remove
            move_bookmarks_to: Category to move bookmarks to (default category if None)
            
        Returns:
            True if category was removed
        """
        if category_id not in self._categories:
            logger.warning(f"Category not found: {category_id}")
            return False
        
        if category_id == "default":
            logger.warning("Cannot remove default category")
            return False
        
        category = self._categories[category_id]
        
        # Move bookmarks to another category
        target_category_id = move_bookmarks_to or "default"
        if target_category_id in self._categories:
            target_category = self._categories[target_category_id]
            for bookmark_id in category.bookmark_ids:
                target_category.add_bookmark(bookmark_id)
        
        # Remove category
        del self._categories[category_id]
        
        # Schedule save
        self._schedule_save()
        
        logger.info(f"Removed bookmark category: {category.name} ({category_id})")
        self.category_removed.emit(category_id)
        
        return True
    
    def get_categories(self) -> List[BookmarkCategory]:
        """
        Get all bookmark categories
        
        Returns:
            List of all categories
        """
        return list(self._categories.values())
    
    def move_bookmark_to_category(self, bookmark_id: str, category_id: str) -> bool:
        """
        Move bookmark to a different category
        
        Args:
            bookmark_id: ID of bookmark to move
            category_id: Target category ID
            
        Returns:
            True if bookmark was moved
        """
        if bookmark_id not in self._bookmarks:
            logger.warning(f"Bookmark not found: {bookmark_id}")
            return False
        
        if category_id not in self._categories:
            logger.warning(f"Category not found: {category_id}")
            return False
        
        # Remove from current categories
        for category in self._categories.values():
            category.remove_bookmark(bookmark_id)
        
        # Add to target category
        self._categories[category_id].add_bookmark(bookmark_id)
        
        # Schedule save
        self._schedule_save()
        
        logger.debug(f"Moved bookmark {bookmark_id} to category {category_id}")
        return True
    
    def export_bookmarks(self, file_path: Path, category_id: Optional[str] = None) -> bool:
        """
        Export bookmarks to file
        
        Args:
            file_path: Export file path
            category_id: Optional category to export (all if None)
            
        Returns:
            True if export succeeded
        """
        try:
            # Get bookmarks to export
            if category_id:
                bookmarks = self.get_bookmarks_by_category(category_id)
            else:
                bookmarks = self.get_all_bookmarks()
            
            # Convert to serializable format
            export_data = {
                'bookmarks': [bookmark.to_dict() for bookmark in bookmarks],
                'categories': {cid: asdict(cat) for cid, cat in self._categories.items()},
                'exported_at': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(bookmarks)} bookmarks to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export bookmarks: {e}")
            return False
    
    def import_bookmarks(self, file_path: Path, merge: bool = True) -> bool:
        """
        Import bookmarks from file
        
        Args:
            file_path: Import file path
            merge: Whether to merge with existing bookmarks
            
        Returns:
            True if import succeeded
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import_data = json.load(f)
            
            # Clear existing if not merging
            if not merge:
                self._bookmarks.clear()
                self._categories.clear()
                self._initialize_default_categories()
            
            # Import categories
            if 'categories' in import_data:
                for cat_data in import_data['categories'].values():
                    if cat_data['category_id'] not in self._categories:
                        category = BookmarkCategory(**cat_data)
                        self._categories[category.category_id] = category
            
            # Import bookmarks
            imported_count = 0
            if 'bookmarks' in import_data:
                for bookmark_data in import_data['bookmarks']:
                    try:
                        bookmark = Bookmark.from_dict(bookmark_data)
                        
                        # Check for duplicates if merging
                        if merge and self._has_duplicate_bookmark(bookmark.element_id):
                            continue
                        
                        self._bookmarks[bookmark.bookmark_id] = bookmark
                        imported_count += 1
                        
                    except Exception as e:
                        logger.warning(f"Failed to import bookmark: {e}")
            
            # Schedule save
            self._schedule_save()
            
            logger.info(f"Imported {imported_count} bookmarks from {file_path}")
            self.bookmarks_loaded.emit(imported_count)
            return True
            
        except Exception as e:
            logger.error(f"Failed to import bookmarks: {e}")
            return False
    
    def save_bookmarks(self) -> bool:
        """
        Save bookmarks to file
        
        Returns:
            True if save succeeded
        """
        if not self._bookmark_file:
            logger.warning("No bookmark file set")
            return False
        
        return self.export_bookmarks(self._bookmark_file)
    
    def load_bookmarks(self) -> bool:
        """
        Load bookmarks from file
        
        Returns:
            True if load succeeded
        """
        if not self._bookmark_file or not self._bookmark_file.exists():
            logger.info("No bookmark file to load")
            return True
        
        return self.import_bookmarks(self._bookmark_file, merge=False)
    
    def _has_duplicate_bookmark(self, element_id: str) -> bool:
        """Check if bookmark for element already exists"""
        return any(bookmark.element_id == element_id for bookmark in self._bookmarks.values())
    
    def _get_bookmark_by_element_id(self, element_id: str) -> Optional[Bookmark]:
        """Get bookmark by element ID"""
        for bookmark in self._bookmarks.values():
            if bookmark.element_id == element_id:
                return bookmark
        return None
    
    def _update_recent_bookmarks(self, bookmark_id: str) -> None:
        """Update recent bookmarks list"""
        # Remove if already in list
        if bookmark_id in self._recent_bookmarks:
            self._recent_bookmarks.remove(bookmark_id)
        
        # Add to front
        self._recent_bookmarks.insert(0, bookmark_id)
        
        # Trim to max size
        if len(self._recent_bookmarks) > self.max_recent_bookmarks:
            self._recent_bookmarks = self._recent_bookmarks[:self.max_recent_bookmarks]
    
    def _schedule_save(self) -> None:
        """Schedule auto-save if enabled"""
        if self.auto_save:
            self._save_timer.start(self.save_delay)
    
    def _save_bookmarks(self) -> None:
        """Internal save method for timer"""
        self.save_bookmarks()
    
    def _initialize_default_categories(self) -> None:
        """Initialize default bookmark categories"""
        
        # Default category
        default_category = BookmarkCategory(
            category_id="default",
            name="Default",
            description="Default bookmark category",
            icon="bookmark"
        )
        self._categories["default"] = default_category
        
        # Favorites category
        favorites_category = BookmarkCategory(
            category_id="favorites",
            name="Favorites",
            description="Favorite bookmarks",
            icon="star"
        )
        self._categories["favorites"] = favorites_category
        
        logger.debug("Initialized default bookmark categories")