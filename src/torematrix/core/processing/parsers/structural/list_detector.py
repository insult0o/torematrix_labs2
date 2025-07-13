"""List hierarchy detection and structure analysis."""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class ListType(Enum):
    """Types of lists that can be detected."""
    UNORDERED = "unordered"
    ORDERED = "ordered"
    DEFINITION = "definition"
    MIXED = "mixed"


@dataclass
class ListItem:
    """Represents a single list item with hierarchy information."""
    content: str
    level: int
    item_type: str
    number: Optional[str] = None
    children: List['ListItem'] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ListStructure:
    """Complete list structure with hierarchy."""
    items: List[ListItem]
    list_type: ListType
    max_depth: int
    total_items: int
    has_mixed_content: bool = False


class ListDetector:
    """Hierarchical list detection with nested structure analysis."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("torematrix.parsers.list_detector")
        
        # Detection patterns
        self.patterns = {
            "ordered_numeric": r"^\s*(\d+)[\.\)]\s+(.+)$",
            "ordered_alpha_lower": r"^\s*([a-z])[\.\)]\s+(.+)$",
            "ordered_alpha_upper": r"^\s*([A-Z])[\.\)]\s+(.+)$",
            "ordered_roman_lower": r"^\s*([ivxlc]+)[\.\)]\s+(.+)$",
            "ordered_roman_upper": r"^\s*([IVXLC]+)[\.\)]\s+(.+)$",
            "unordered_bullet": r"^\s*[•·▪▫◦‣⁃]\s+(.+)$",
            "unordered_dash": r"^\s*[-*+]\s+(.+)$",
            "definition": r"^\s*(.+?):\s+(.+)$",
        }
        
        # Indentation detection
        self.min_indent_step = 2
        self.max_depth = self.config.get('max_depth', 5)
    
    async def detect_hierarchy(self, raw_items: List[str]) -> ListStructure:
        """Detect hierarchy and structure in list items."""
        try:
            if not raw_items:
                return ListStructure(
                    items=[],
                    list_type=ListType.UNORDERED,
                    max_depth=0,
                    total_items=0
                )
            
            # Parse individual items
            parsed_items = self._parse_items(raw_items)
            
            # Detect indentation levels
            leveled_items = self._detect_levels(parsed_items)
            
            # Determine list type
            list_type = self._determine_list_type(leveled_items)
            
            # Calculate statistics
            max_depth = max(item.level for item in leveled_items) if leveled_items else 0
            total_items = len(leveled_items)
            has_mixed = self._has_mixed_content(leveled_items)
            
            return ListStructure(
                items=leveled_items,
                list_type=list_type,
                max_depth=max_depth,
                total_items=total_items,
                has_mixed_content=has_mixed
            )
            
        except Exception as e:
            self.logger.error(f"List hierarchy detection failed: {e}")
            return ListStructure(
                items=[],
                list_type=ListType.UNORDERED,
                max_depth=0,
                total_items=0
            )
    
    def _parse_items(self, raw_items: List[str]) -> List[Dict[str, Any]]:
        """Parse raw text items into structured data."""
        parsed = []
        
        for item_text in raw_items:
            if not item_text.strip():
                continue
            
            # Try each pattern
            best_match = None
            best_pattern = None
            
            for pattern_name, pattern_regex in self.patterns.items():
                match = re.match(pattern_regex, item_text)
                if match:
                    best_match = match
                    best_pattern = pattern_name
                    break
            
            if best_match:
                if best_pattern == "definition":
                    # Definition list: term: definition
                    parsed.append({
                        "original_text": item_text,
                        "content": best_match.group(2),
                        "marker": best_match.group(1),
                        "pattern": best_pattern,
                        "indent": len(item_text) - len(item_text.lstrip())
                    })
                else:
                    # Regular list item
                    parsed.append({
                        "original_text": item_text,
                        "content": best_match.group(2) if best_match.lastindex >= 2 else best_match.group(1),
                        "marker": best_match.group(1) if best_match.lastindex >= 2 else "",
                        "pattern": best_pattern,
                        "indent": len(item_text) - len(item_text.lstrip())
                    })
            else:
                # No pattern matched - treat as plain text item
                parsed.append({
                    "original_text": item_text,
                    "content": item_text.strip(),
                    "marker": "",
                    "pattern": "plain",
                    "indent": len(item_text) - len(item_text.lstrip())
                })
        
        return parsed
    
    def _detect_levels(self, parsed_items: List[Dict[str, Any]]) -> List[ListItem]:
        """Detect hierarchy levels based on indentation and markers."""
        if not parsed_items:
            return []
        
        # Calculate indentation levels
        indents = [item["indent"] for item in parsed_items]
        unique_indents = sorted(set(indents))
        
        # Map indentation to levels
        indent_to_level = {indent: level for level, indent in enumerate(unique_indents)}
        
        # Create ListItem objects
        list_items = []
        
        for item_data in parsed_items:
            level = indent_to_level[item_data["indent"]]
            
            # Determine item type based on pattern
            item_type = self._pattern_to_item_type(item_data["pattern"])
            
            list_item = ListItem(
                content=item_data["content"],
                level=level,
                item_type=item_type,
                number=item_data["marker"] if item_data["marker"] else None,
                metadata={
                    "original_text": item_data["original_text"],
                    "pattern": item_data["pattern"],
                    "indent": item_data["indent"]
                }
            )
            
            list_items.append(list_item)
        
        return list_items
    
    def _pattern_to_item_type(self, pattern: str) -> str:
        """Convert pattern name to item type."""
        if pattern.startswith("ordered_"):
            return "ordered"
        elif pattern.startswith("unordered_"):
            return "unordered"
        elif pattern == "definition":
            return "definition"
        else:
            return "plain"
    
    def _determine_list_type(self, items: List[ListItem]) -> ListType:
        """Determine the overall list type."""
        if not items:
            return ListType.UNORDERED
        
        # Count different types
        type_counts = {}
        for item in items:
            item_type = item.item_type
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
        
        # Determine primary type
        if len(type_counts) == 1:
            primary_type = list(type_counts.keys())[0]
            if primary_type == "ordered":
                return ListType.ORDERED
            elif primary_type == "definition":
                return ListType.DEFINITION
            else:
                return ListType.UNORDERED
        else:
            return ListType.MIXED
    
    def _has_mixed_content(self, items: List[ListItem]) -> bool:
        """Check if list has mixed content types."""
        if not items:
            return False
        
        types = set(item.item_type for item in items)
        return len(types) > 1
    
    def validate_hierarchy(self, structure: ListStructure) -> List[str]:
        """Validate the detected hierarchy structure."""
        errors = []
        
        if not structure.items:
            errors.append("No list items found")
            return errors
        
        # Check depth limits
        if structure.max_depth > self.max_depth:
            errors.append(f"List depth {structure.max_depth} exceeds maximum {self.max_depth}")
        
        # Check level consistency
        prev_level = -1
        for i, item in enumerate(structure.items):
            if item.level < 0:
                errors.append(f"Item {i} has negative level: {item.level}")
            
            # Check for level jumps (shouldn't skip levels)
            if item.level > prev_level + 1:
                errors.append(f"Item {i} skips levels: from {prev_level} to {item.level}")
            
            prev_level = item.level
        
        # Check for empty content
        empty_items = [i for i, item in enumerate(structure.items) if not item.content.strip()]
        if empty_items:
            errors.append(f"Items with empty content at positions: {empty_items}")
        
        return errors
    
    def build_nested_structure(self, flat_items: List[ListItem]) -> List[ListItem]:
        """Build nested structure from flat list with levels."""
        if not flat_items:
            return []
        
        # Stack to keep track of current parents at each level
        parent_stack: List[ListItem] = []
        root_items: List[ListItem] = []
        
        for item in flat_items:
            # Clear stack to current level
            while len(parent_stack) > item.level:
                parent_stack.pop()
            
            # Add to appropriate parent
            if item.level == 0:
                root_items.append(item)
                parent_stack = [item]
            else:
                if parent_stack:
                    parent_stack[-1].children.append(item)
                    parent_stack.append(item)
                else:
                    # Orphaned item - add to root
                    root_items.append(item)
                    parent_stack = [item]
        
        return root_items