"""Column data type detection and inference."""

import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from .table_analyzer import TableStructure, TableCell


class DataTyper:
    """Column data type detection and inference engine."""
    
    def __init__(self):
        self.logger = logging.getLogger("torematrix.parsers.data_typer")
        
        # Type detection patterns
        self.patterns = {
            "integer": r"^-?\d{1,3}(?:,\d{3})*$",
            "float": r"^-?\d{1,3}(?:,\d{3})*\.\d+$",
            "percentage": r"^-?\d+(?:\.\d+)?%$",
            "currency": r"^[\$€£¥₹]\d{1,3}(?:,\d{3})*(?:\.\d{2})?$",
            "date_iso": r"^\d{4}-\d{2}-\d{2}$",
            "date_us": r"^\d{1,2}/\d{1,2}/\d{4}$",
            "date_eu": r"^\d{1,2}-\d{1,2}-\d{4}$",
            "time": r"^\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AaPp][Mm])?$",
            "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            "phone": r"^(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$",
            "url": r"^https?://[^\s/$.?#].[^\s]*$",
            "boolean": r"^(?:true|false|yes|no|y|n|1|0)$",
        }
    
    def detect_types(self, structure: TableStructure) -> List[str]:
        """Detect data types for all columns in the table."""
        if not structure.rows:
            return []
        
        # Determine number of columns
        max_cols = max(len(row) for row in structure.rows) if structure.rows else 0
        column_types = []
        
        for col_idx in range(max_cols):
            # Extract all non-empty values from this column
            column_values = []
            for row in structure.rows:
                if col_idx < len(row) and row[col_idx].content.strip():
                    column_values.append(row[col_idx].content.strip())
            
            # Detect type for this column
            column_type = self._detect_column_type(column_values)
            column_types.append(column_type)
            
            # Update individual cell types
            for row in structure.rows:
                if col_idx < len(row):
                    row[col_idx].data_type = column_type
        
        return column_types
    
    def _detect_column_type(self, values: List[str]) -> str:
        """Detect the most appropriate data type for a column."""
        if not values:
            return "text"
        
        # Count matches for each type
        type_scores = {}
        total_values = len(values)
        
        for type_name, pattern in self.patterns.items():
            matches = sum(1 for value in values if re.match(pattern, value, re.IGNORECASE))
            type_scores[type_name] = matches / total_values
        
        # Special handling for boolean
        boolean_matches = sum(1 for value in values if self._is_boolean(value))
        type_scores["boolean"] = boolean_matches / total_values
        
        # Find the type with highest score (minimum 60% match)
        best_type = "text"
        best_score = 0.0
        
        for type_name, score in type_scores.items():
            if score > best_score and score >= 0.6:
                best_score = score
                best_type = type_name
        
        # Handle hierarchical types (float before integer)
        if best_type == "integer" and type_scores.get("float", 0) > 0.3:
            best_type = "float"
        
        return self._normalize_type_name(best_type)
    
    def _is_boolean(self, value: str) -> bool:
        """Check if value represents a boolean."""
        normalized = value.lower().strip()
        return normalized in [
            "true", "false", "yes", "no", "y", "n", "1", "0",
            "on", "off", "enabled", "disabled", "active", "inactive"
        ]
    
    def _normalize_type_name(self, type_name: str) -> str:
        """Normalize type names to standard categories."""
        type_mapping = {
            "date_iso": "date",
            "date_us": "date", 
            "date_eu": "date",
            "integer": "number",
            "float": "number",
            "percentage": "number",
            "currency": "number",
        }
        
        return type_mapping.get(type_name, type_name)
    
    def validate_type_consistency(self, structure: TableStructure) -> Dict[str, Any]:
        """Validate type consistency across the table."""
        validation_results = {
            "consistent_columns": 0,
            "inconsistent_columns": 0,
            "column_details": {},
            "overall_score": 0.0
        }
        
        if not structure.rows:
            return validation_results
        
        max_cols = max(len(row) for row in structure.rows) if structure.rows else 0
        
        for col_idx in range(max_cols):
            column_cells = []
            for row in structure.rows:
                if col_idx < len(row):
                    column_cells.append(row[col_idx])
            
            # Check type consistency within column
            if column_cells:
                primary_type = column_cells[0].data_type
                consistent_cells = sum(1 for cell in column_cells if cell.data_type == primary_type)
                consistency_ratio = consistent_cells / len(column_cells)
                
                validation_results["column_details"][f"column_{col_idx}"] = {
                    "primary_type": primary_type,
                    "consistency_ratio": consistency_ratio,
                    "total_cells": len(column_cells),
                    "consistent_cells": consistent_cells
                }
                
                if consistency_ratio >= 0.8:
                    validation_results["consistent_columns"] += 1
                else:
                    validation_results["inconsistent_columns"] += 1
        
        # Calculate overall score
        total_cols = validation_results["consistent_columns"] + validation_results["inconsistent_columns"]
        if total_cols > 0:
            validation_results["overall_score"] = validation_results["consistent_columns"] / total_cols
        
        return validation_results