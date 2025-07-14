"""
Persistence Utilities for Selection State Management.
This module provides utilities for saving and loading selection states,
managing different storage formats, and handling data migration.
"""
from __future__ import annotations

import json
import pickle
import sqlite3
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Union, BinaryIO, TextIO
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import zlib
import base64

from .state import SelectionStateSnapshot, SelectionSet, StateScope


class StorageFormat(Enum):
    """Supported storage formats."""
    JSON = "json"
    PICKLE = "pickle"
    XML = "xml"
    SQLITE = "sqlite"
    COMPRESSED_JSON = "compressed_json"


class CompressionLevel(Enum):
    """Compression levels for storage."""
    NONE = 0
    FAST = 1
    BALANCED = 6
    BEST = 9


@dataclass
class StorageOptions:
    """Options for storage operations."""
    format: StorageFormat = StorageFormat.JSON
    compression: CompressionLevel = CompressionLevel.NONE
    include_metadata: bool = True
    validate_on_load: bool = True
    backup_on_save: bool = True
    max_file_size: int = 100 * 1024 * 1024  # 100MB


class PersistenceManager:
    """
    Manager for different persistence formats and operations.
    
    This class handles saving and loading of selection states in various formats,
    with support for compression, validation, and migration between formats.
    """
    
    def __init__(self, storage_options: Optional[StorageOptions] = None):
        self.options = storage_options or StorageOptions()
        self.format_handlers = {
            StorageFormat.JSON: self._handle_json,
            StorageFormat.PICKLE: self._handle_pickle,
            StorageFormat.XML: self._handle_xml,
            StorageFormat.SQLITE: self._handle_sqlite,
            StorageFormat.COMPRESSED_JSON: self._handle_compressed_json
        }
    
    def save_selection_snapshot(
        self,
        snapshot: SelectionStateSnapshot,
        file_path: Path,
        options: Optional[StorageOptions] = None
    ) -> bool:
        """
        Save a selection snapshot to file.
        
        Args:
            snapshot: Snapshot to save
            file_path: Path to save to
            options: Storage options (uses default if None)
            
        Returns:
            True if successful
        """
        opts = options or self.options
        
        try:
            # Create backup if requested
            if opts.backup_on_save and file_path.exists():
                backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
                backup_path.write_bytes(file_path.read_bytes())
            
            # Prepare data
            data = snapshot.to_dict()
            if not opts.include_metadata:
                data.pop('metadata', None)
            
            # Use format handler
            handler = self.format_handlers.get(opts.format)
            if not handler:
                raise ValueError(f"Unsupported format: {opts.format}")
            
            return handler(data, file_path, 'save', opts)
            
        except Exception as e:
            print(f"Error saving snapshot: {e}")
            return False
    
    def load_selection_snapshot(
        self,
        file_path: Path,
        options: Optional[StorageOptions] = None
    ) -> Optional[SelectionStateSnapshot]:
        """
        Load a selection snapshot from file.
        
        Args:
            file_path: Path to load from
            options: Storage options (uses default if None)
            
        Returns:
            Loaded snapshot or None if failed
        """
        opts = options or self.options
        
        try:
            if not file_path.exists():
                return None
            
            # Check file size
            if file_path.stat().st_size > opts.max_file_size:
                raise ValueError(f"File size exceeds limit: {opts.max_file_size}")
            
            # Detect format if not specified
            if opts.format == StorageFormat.JSON:
                # Try to detect format from file extension
                if file_path.suffix.lower() == '.pkl':
                    opts.format = StorageFormat.PICKLE
                elif file_path.suffix.lower() == '.xml':
                    opts.format = StorageFormat.XML
                elif file_path.suffix.lower() == '.db':
                    opts.format = StorageFormat.SQLITE
            
            # Use format handler
            handler = self.format_handlers.get(opts.format)
            if not handler:
                raise ValueError(f"Unsupported format: {opts.format}")
            
            data = handler(None, file_path, 'load', opts)
            
            if data and opts.validate_on_load:
                if not self._validate_snapshot_data(data):
                    raise ValueError("Invalid snapshot data")
            
            return SelectionStateSnapshot.from_dict(data) if data else None
            
        except Exception as e:
            print(f"Error loading snapshot: {e}")
            return None
    
    def save_selection_set(
        self,
        selection_set: SelectionSet,
        file_path: Path,
        options: Optional[StorageOptions] = None
    ) -> bool:
        """
        Save a selection set to file.
        
        Args:
            selection_set: Selection set to save
            file_path: Path to save to
            options: Storage options (uses default if None)
            
        Returns:
            True if successful
        """
        opts = options or self.options
        
        try:
            # Create backup if requested
            if opts.backup_on_save and file_path.exists():
                backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
                backup_path.write_bytes(file_path.read_bytes())
            
            # Prepare data
            data = selection_set.to_dict()
            if not opts.include_metadata:
                # Remove metadata from snapshots
                for snapshot_data in data.get('snapshots', []):
                    snapshot_data.pop('metadata', None)
            
            # Use format handler
            handler = self.format_handlers.get(opts.format)
            if not handler:
                raise ValueError(f"Unsupported format: {opts.format}")
            
            return handler(data, file_path, 'save', opts)
            
        except Exception as e:
            print(f"Error saving selection set: {e}")
            return False
    
    def load_selection_set(
        self,
        file_path: Path,
        options: Optional[StorageOptions] = None
    ) -> Optional[SelectionSet]:
        """
        Load a selection set from file.
        
        Args:
            file_path: Path to load from
            options: Storage options (uses default if None)
            
        Returns:
            Loaded selection set or None if failed
        """
        opts = options or self.options
        
        try:
            if not file_path.exists():
                return None
            
            # Check file size
            if file_path.stat().st_size > opts.max_file_size:
                raise ValueError(f"File size exceeds limit: {opts.max_file_size}")
            
            # Use format handler
            handler = self.format_handlers.get(opts.format)
            if not handler:
                raise ValueError(f"Unsupported format: {opts.format}")
            
            data = handler(None, file_path, 'load', opts)
            
            if data and opts.validate_on_load:
                if not self._validate_selection_set_data(data):
                    raise ValueError("Invalid selection set data")
            
            return SelectionSet.from_dict(data) if data else None
            
        except Exception as e:
            print(f"Error loading selection set: {e}")
            return None
    
    def migrate_format(
        self,
        source_path: Path,
        target_path: Path,
        source_format: StorageFormat,
        target_format: StorageFormat
    ) -> bool:
        """
        Migrate data between storage formats.
        
        Args:
            source_path: Source file path
            target_path: Target file path
            source_format: Source format
            target_format: Target format
            
        Returns:
            True if successful
        """
        try:
            # Load with source format
            source_options = StorageOptions(format=source_format)
            
            # Try to load as snapshot first
            snapshot = self.load_selection_snapshot(source_path, source_options)
            if snapshot:
                target_options = StorageOptions(format=target_format)
                return self.save_selection_snapshot(snapshot, target_path, target_options)
            
            # Try to load as selection set
            selection_set = self.load_selection_set(source_path, source_options)
            if selection_set:
                target_options = StorageOptions(format=target_format)
                return self.save_selection_set(selection_set, target_path, target_options)
            
            return False
            
        except Exception as e:
            print(f"Error migrating format: {e}")
            return False
    
    def _handle_json(
        self,
        data: Optional[Dict[str, Any]],
        file_path: Path,
        operation: str,
        options: StorageOptions
    ) -> Union[bool, Dict[str, Any]]:
        """Handle JSON format operations."""
        if operation == 'save':
            try:
                with open(file_path, 'w') as f:
                    json.dump(data, f, indent=2, default=str)
                return True
            except Exception:
                return False
        
        elif operation == 'load':
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except Exception:
                return None
    
    def _handle_pickle(
        self,
        data: Optional[Dict[str, Any]],
        file_path: Path,
        operation: str,
        options: StorageOptions
    ) -> Union[bool, Dict[str, Any]]:
        """Handle pickle format operations."""
        if operation == 'save':
            try:
                with open(file_path, 'wb') as f:
                    pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
                return True
            except Exception:
                return False
        
        elif operation == 'load':
            try:
                with open(file_path, 'rb') as f:
                    return pickle.load(f)
            except Exception:
                return None
    
    def _handle_xml(
        self,
        data: Optional[Dict[str, Any]],
        file_path: Path,
        operation: str,
        options: StorageOptions
    ) -> Union[bool, Dict[str, Any]]:
        """Handle XML format operations."""
        if operation == 'save':
            try:
                root = self._dict_to_xml(data, 'selection_data')
                tree = ET.ElementTree(root)
                tree.write(file_path, encoding='utf-8', xml_declaration=True)
                return True
            except Exception:
                return False
        
        elif operation == 'load':
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                return self._xml_to_dict(root)
            except Exception:
                return None
    
    def _handle_sqlite(
        self,
        data: Optional[Dict[str, Any]],
        file_path: Path,
        operation: str,
        options: StorageOptions
    ) -> Union[bool, Dict[str, Any]]:
        """Handle SQLite format operations."""
        if operation == 'save':
            try:
                conn = sqlite3.connect(file_path)
                cursor = conn.cursor()
                
                # Create table if not exists
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS selection_data (
                        id INTEGER PRIMARY KEY,
                        data_type TEXT,
                        json_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Insert data
                data_type = 'snapshot' if 'selection_id' in data else 'selection_set'
                cursor.execute(
                    'INSERT INTO selection_data (data_type, json_data) VALUES (?, ?)',
                    (data_type, json.dumps(data, default=str))
                )
                
                conn.commit()
                conn.close()
                return True
            except Exception:
                return False
        
        elif operation == 'load':
            try:
                conn = sqlite3.connect(file_path)
                cursor = conn.cursor()
                
                # Get most recent entry
                cursor.execute(
                    'SELECT json_data FROM selection_data ORDER BY created_at DESC LIMIT 1'
                )
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    return json.loads(result[0])
                return None
            except Exception:
                return None
    
    def _handle_compressed_json(
        self,
        data: Optional[Dict[str, Any]],
        file_path: Path,
        operation: str,
        options: StorageOptions
    ) -> Union[bool, Dict[str, Any]]:
        """Handle compressed JSON format operations."""
        if operation == 'save':
            try:
                json_str = json.dumps(data, default=str)
                compressed = zlib.compress(
                    json_str.encode('utf-8'),
                    level=options.compression.value
                )
                
                with open(file_path, 'wb') as f:
                    f.write(compressed)
                return True
            except Exception:
                return False
        
        elif operation == 'load':
            try:
                with open(file_path, 'rb') as f:
                    compressed = f.read()
                
                decompressed = zlib.decompress(compressed)
                json_str = decompressed.decode('utf-8')
                return json.loads(json_str)
            except Exception:
                return None
    
    def _dict_to_xml(self, data: Dict[str, Any], root_name: str) -> ET.Element:
        """Convert dictionary to XML element."""
        root = ET.Element(root_name)
        
        for key, value in data.items():
            if isinstance(value, dict):
                child = self._dict_to_xml(value, key)
                root.append(child)
            elif isinstance(value, list):
                list_elem = ET.SubElement(root, key)
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        item_elem = self._dict_to_xml(item, f"item_{i}")
                        list_elem.append(item_elem)
                    else:
                        item_elem = ET.SubElement(list_elem, f"item_{i}")
                        item_elem.text = str(item)
            else:
                elem = ET.SubElement(root, key)
                elem.text = str(value)
        
        return root
    
    def _xml_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Convert XML element to dictionary."""
        result = {}
        
        for child in element:
            if len(child) == 0:
                # Leaf node
                result[child.tag] = child.text
            else:
                # Check if this is a list
                if child.tag.endswith('_list') or all(
                    grandchild.tag.startswith('item_') 
                    for grandchild in child
                ):
                    # This is a list
                    result[child.tag] = [
                        self._xml_to_dict(grandchild) if len(grandchild) > 0 else grandchild.text
                        for grandchild in child
                    ]
                else:
                    # This is a nested dict
                    result[child.tag] = self._xml_to_dict(child)
        
        return result
    
    def _validate_snapshot_data(self, data: Dict[str, Any]) -> bool:
        """Validate snapshot data structure."""
        required_fields = [
            'selection_id', 'timestamp', 'selection_mode',
            'selection_strategy', 'selected_elements', 'selection_bounds'
        ]
        
        for field in required_fields:
            if field not in data:
                return False
        
        # Validate timestamp format
        try:
            datetime.fromisoformat(data['timestamp'])
        except ValueError:
            return False
        
        # Validate bounds structure
        if not isinstance(data['selection_bounds'], list):
            return False
        
        for bounds in data['selection_bounds']:
            if not isinstance(bounds, dict):
                return False
            required_bounds_fields = ['x', 'y', 'width', 'height']
            for field in required_bounds_fields:
                if field not in bounds:
                    return False
        
        return True
    
    def _validate_selection_set_data(self, data: Dict[str, Any]) -> bool:
        """Validate selection set data structure."""
        required_fields = [
            'set_id', 'name', 'description', 'snapshots',
            'created_at', 'modified_at', 'tags'
        ]
        
        for field in required_fields:
            if field not in data:
                return False
        
        # Validate timestamps
        try:
            datetime.fromisoformat(data['created_at'])
            datetime.fromisoformat(data['modified_at'])
        except ValueError:
            return False
        
        # Validate snapshots
        if not isinstance(data['snapshots'], list):
            return False
        
        for snapshot_data in data['snapshots']:
            if not self._validate_snapshot_data(snapshot_data):
                return False
        
        return True


class SessionPersistence:
    """
    Utilities for session-specific persistence operations.
    
    This class handles session state persistence with automatic recovery,
    session expiration, and cleanup of old sessions.
    """
    
    def __init__(self, session_dir: Path, max_session_age: int = 86400):
        self.session_dir = session_dir
        self.max_session_age = max_session_age  # seconds
        self.session_dir.mkdir(parents=True, exist_ok=True)
    
    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Save session data to file."""
        try:
            session_file = self.session_dir / f"{session_id}.json"
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2, default=str)
            return True
        except Exception:
            return False
    
    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load session data from file."""
        try:
            session_file = self.session_dir / f"{session_id}.json"
            if not session_file.exists():
                return None
            
            with open(session_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    def cleanup_old_sessions(self) -> int:
        """Clean up old session files."""
        cleaned_count = 0
        current_time = datetime.now().timestamp()
        
        for session_file in self.session_dir.glob("*.json"):
            try:
                file_age = current_time - session_file.stat().st_mtime
                if file_age > self.max_session_age:
                    session_file.unlink()
                    cleaned_count += 1
            except Exception:
                continue
        
        return cleaned_count
    
    def get_active_sessions(self) -> List[str]:
        """Get list of active session IDs."""
        active_sessions = []
        current_time = datetime.now().timestamp()
        
        for session_file in self.session_dir.glob("*.json"):
            try:
                file_age = current_time - session_file.stat().st_mtime
                if file_age <= self.max_session_age:
                    session_id = session_file.stem
                    active_sessions.append(session_id)
            except Exception:
                continue
        
        return active_sessions
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a specific session."""
        try:
            session_file = self.session_dir / f"{session_id}.json"
            if session_file.exists():
                session_file.unlink()
                return True
            return False
        except Exception:
            return False