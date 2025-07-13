"""Structure validation rules for tables and lists."""

import logging
from typing import Dict, Any, List, Optional
from .table_analyzer import TableStructure
from .list_detector import ListStructure


class StructureValidator:
    """Validator for table and list structures."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("torematrix.parsers.structure_validator")
        
        # Validation thresholds
        self.min_table_rows = self.config.get('min_table_rows', 1)
        self.min_table_cols = self.config.get('min_table_cols', 2)
        self.max_table_rows = self.config.get('max_table_rows', 1000)
        self.max_table_cols = self.config.get('max_table_cols', 100)
        self.min_data_quality = self.config.get('min_data_quality', 0.5)
    
    def validate_table_structure(self, structure: TableStructure) -> List[str]:
        """Validate table structure integrity."""
        errors = []
        
        try:
            # Basic structure validation
            if not structure.rows:
                errors.append("Table has no data rows")
                return errors
            
            # Dimension validation
            row_count = len(structure.rows)
            if row_count < self.min_table_rows:
                errors.append(f"Table has {row_count} rows, minimum required is {self.min_table_rows}")
            
            if row_count > self.max_table_rows:
                errors.append(f"Table has {row_count} rows, maximum allowed is {self.max_table_rows}")
            
            # Column validation
            if structure.rows:
                col_count = len(structure.rows[0]) if structure.rows[0] else 0
                
                if col_count < self.min_table_cols:
                    errors.append(f"Table has {col_count} columns, minimum required is {self.min_table_cols}")
                
                if col_count > self.max_table_cols:
                    errors.append(f"Table has {col_count} columns, maximum allowed is {self.max_table_cols}")
                
                # Check row consistency
                for i, row in enumerate(structure.rows):
                    if len(row) != col_count:
                        errors.append(f"Row {i} has {len(row)} columns, expected {col_count}")
            
            # Header validation
            if structure.has_headers and structure.headers:
                header_count = sum(len(row) for row in structure.headers)
                expected_cols = len(structure.rows[0]) if structure.rows else 0
                
                if header_count != expected_cols and expected_cols > 0:
                    errors.append(f"Header count {header_count} doesn't match column count {expected_cols}")
            
            # Cell span validation
            for row_idx, row in enumerate(structure.rows):
                for col_idx, cell in enumerate(row):
                    if cell.row_span < 1:
                        errors.append(f"Invalid row_span {cell.row_span} at row {row_idx}, col {col_idx}")
                    if cell.col_span < 1:
                        errors.append(f"Invalid col_span {cell.col_span} at row {row_idx}, col {col_idx}")
                    
                    # Check if spans exceed table boundaries
                    if row_idx + cell.row_span > len(structure.rows):
                        errors.append(f"Row span at row {row_idx}, col {col_idx} exceeds table boundary")
                    if col_idx + cell.col_span > len(row):
                        errors.append(f"Column span at row {row_idx}, col {col_idx} exceeds row boundary")
            
            # Data quality validation
            data_quality = self._calculate_table_data_quality(structure)
            if data_quality < self.min_data_quality:
                errors.append(f"Data quality {data_quality:.2f} below minimum threshold {self.min_data_quality}")
        
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return errors
    
    def validate_list_structure(self, structure: ListStructure) -> List[str]:
        """Validate list structure integrity."""
        errors = []
        
        try:
            # Basic structure validation
            if not structure.items:
                errors.append("List has no items")
                return errors
            
            # Depth validation
            max_allowed_depth = self.config.get('max_list_depth', 5)
            if structure.max_depth > max_allowed_depth:
                errors.append(f"List depth {structure.max_depth} exceeds maximum {max_allowed_depth}")
            
            # Item count validation
            min_items = self.config.get('min_list_items', 1)
            max_items = self.config.get('max_list_items', 1000)
            
            if structure.total_items < min_items:
                errors.append(f"List has {structure.total_items} items, minimum required is {min_items}")
            
            if structure.total_items > max_items:
                errors.append(f"List has {structure.total_items} items, maximum allowed is {max_items}")
            
            # Level consistency validation
            prev_level = -1
            for i, item in enumerate(structure.items):
                if item.level < 0:
                    errors.append(f"Item {i} has negative level: {item.level}")
                
                # Check for excessive level jumps
                if item.level > prev_level + 1:
                    errors.append(f"Item {i} jumps from level {prev_level} to {item.level}")
                
                prev_level = max(prev_level, item.level)
            
            # Content validation
            empty_items = []
            for i, item in enumerate(structure.items):
                if not item.content.strip():
                    empty_items.append(i)
            
            if empty_items:
                errors.append(f"Items with empty content at positions: {empty_items}")
            
            # Type consistency validation (for ordered lists)
            if structure.list_type.value == "ordered":
                self._validate_ordered_list_numbering(structure, errors)
        
        except Exception as e:
            errors.append(f"List validation error: {str(e)}")
        
        return errors
    
    def _calculate_table_data_quality(self, structure: TableStructure) -> float:
        """Calculate data quality score for table (0-1)."""
        if not structure.rows:
            return 0.0
        
        total_cells = 0
        non_empty_cells = 0
        
        for row in structure.rows:
            for cell in row:
                total_cells += 1
                if cell.content.strip():
                    non_empty_cells += 1
        
        return non_empty_cells / total_cells if total_cells > 0 else 0.0
    
    def _validate_ordered_list_numbering(self, structure: ListStructure, errors: List[str]) -> None:
        """Validate numbering in ordered lists."""
        # Group items by level
        level_items = {}
        for item in structure.items:
            if item.level not in level_items:
                level_items[item.level] = []
            level_items[item.level].append(item)
        
        # Check numbering consistency at each level
        for level, items in level_items.items():
            ordered_items = [item for item in items if item.item_type == "ordered" and item.number]
            
            if len(ordered_items) > 1:
                # Check if numbers are sequential
                try:
                    numbers = [int(item.number) for item in ordered_items if item.number.isdigit()]
                    if len(numbers) > 1:
                        for i in range(1, len(numbers)):
                            if numbers[i] != numbers[i-1] + 1:
                                errors.append(f"Non-sequential numbering at level {level}: {numbers[i-1]} -> {numbers[i]}")
                except ValueError:
                    # Non-numeric numbering (letters, roman numerals, etc.)
                    pass
    
    def get_validation_summary(self, table_errors: List[str], list_errors: List[str]) -> Dict[str, Any]:
        """Get comprehensive validation summary."""
        return {
            "table_validation": {
                "error_count": len(table_errors),
                "errors": table_errors,
                "is_valid": len(table_errors) == 0
            },
            "list_validation": {
                "error_count": len(list_errors),
                "errors": list_errors,
                "is_valid": len(list_errors) == 0
            },
            "overall_valid": len(table_errors) == 0 and len(list_errors) == 0
        }