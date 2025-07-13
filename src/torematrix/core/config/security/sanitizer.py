"""
Configuration sanitization for safe logging and export.

This module provides utilities to sanitize configuration data by
masking or removing sensitive information.
"""

from typing import Dict, Any, List, Set, Pattern, Callable, Optional
import re
from ..types import ConfigDict


class ConfigSanitizer:
    """
    Sanitize configuration data for safe logging and export.
    
    Features:
    - Pattern-based field detection
    - Custom sanitization rules
    - Configurable masking strategies
    - Safe defaults for common sensitive fields
    """
    
    # Default patterns for sensitive field names
    DEFAULT_SENSITIVE_PATTERNS = [
        r'password',
        r'passwd',
        r'pwd',
        r'secret',
        r'key',
        r'token',
        r'auth',
        r'credential',
        r'api[_-]?key',
        r'private[_-]?key',
        r'access[_-]?token',
        r'refresh[_-]?token',
        r'bearer[_-]?token',
        r'cert',
        r'certificate',
        r'ssl[_-]?cert',
        r'tls[_-]?cert',
    ]
    
    # Default patterns for sensitive values
    DEFAULT_VALUE_PATTERNS = [
        r'^[A-Za-z0-9+/]+=*$',  # Base64-like
        r'^[0-9a-fA-F]{32,}$',  # Long hex strings
        r'^[A-Za-z0-9]{40,}$',  # Long alphanumeric strings
    ]
    
    def __init__(
        self,
        sensitive_patterns: Optional[List[str]] = None,
        value_patterns: Optional[List[str]] = None,
        masking_strategy: str = "partial",
        custom_rules: Optional[Dict[str, Callable[[Any], Any]]] = None
    ):
        """
        Initialize sanitizer.
        
        Args:
            sensitive_patterns: Regex patterns for sensitive field names
            value_patterns: Regex patterns for sensitive values
            masking_strategy: How to mask values ("full", "partial", "hash")
            custom_rules: Custom sanitization rules by field path
        """
        self.sensitive_patterns = sensitive_patterns or self.DEFAULT_SENSITIVE_PATTERNS
        self.value_patterns = value_patterns or self.DEFAULT_VALUE_PATTERNS
        self.masking_strategy = masking_strategy
        self.custom_rules = custom_rules or {}
        
        # Compile regex patterns
        self._compiled_field_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.sensitive_patterns
        ]
        self._compiled_value_patterns = [
            re.compile(pattern) for pattern in self.value_patterns
        ]
        
        # Track sanitized paths for reporting
        self._sanitized_paths: Set[str] = set()
    
    def sanitize(self, config: ConfigDict) -> ConfigDict:
        """
        Sanitize configuration data.
        
        Args:
            config: Configuration to sanitize
            
        Returns:
            Sanitized configuration
        """
        self._sanitized_paths.clear()
        return self._sanitize_recursive(config)
    
    def get_sanitized_paths(self) -> Set[str]:
        """Get set of field paths that were sanitized."""
        return self._sanitized_paths.copy()
    
    def _sanitize_recursive(self, obj: Any, path: str = "") -> Any:
        """Recursively sanitize data structure."""
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                field_path = f"{path}.{key}" if path else key
                
                # Check for custom rule
                if field_path in self.custom_rules:
                    result[key] = self.custom_rules[field_path](value)
                    self._sanitized_paths.add(field_path)
                # Check if field name is sensitive
                elif self._is_sensitive_field(key):
                    result[key] = self._mask_value(value)
                    self._sanitized_paths.add(field_path)
                else:
                    result[key] = self._sanitize_recursive(value, field_path)
            return result
        
        elif isinstance(obj, list):
            return [
                self._sanitize_recursive(item, f"{path}[{i}]")
                for i, item in enumerate(obj)
            ]
        
        elif isinstance(obj, str):
            # Check if value looks sensitive
            if self._is_sensitive_value(obj):
                self._sanitized_paths.add(path)
                return self._mask_value(obj)
            return obj
        
        else:
            return obj
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if field name matches sensitive patterns."""
        return any(
            pattern.search(field_name) 
            for pattern in self._compiled_field_patterns
        )
    
    def _is_sensitive_value(self, value: str) -> bool:
        """Check if value looks sensitive based on patterns."""
        if len(value) < 8:  # Too short to be meaningful
            return False
        
        return any(
            pattern.match(value)
            for pattern in self._compiled_value_patterns
        )
    
    def _mask_value(self, value: Any) -> str:
        """Mask a sensitive value according to strategy."""
        if value is None:
            return None
        
        str_value = str(value)
        
        if self.masking_strategy == "full":
            return "[REDACTED]"
        
        elif self.masking_strategy == "partial":
            if len(str_value) <= 4:
                return "*" * len(str_value)
            elif len(str_value) <= 8:
                return str_value[:2] + "*" * (len(str_value) - 4) + str_value[-2:]
            else:
                return str_value[:3] + "*" * (len(str_value) - 6) + str_value[-3:]
        
        elif self.masking_strategy == "hash":
            import hashlib
            hash_value = hashlib.sha256(str_value.encode()).hexdigest()[:8]
            return f"[HASH:{hash_value}]"
        
        elif self.masking_strategy == "length":
            return f"[{len(str_value)} chars]"
        
        else:
            return "[REDACTED]"
    
    def add_sensitive_pattern(self, pattern: str) -> None:
        """Add a new sensitive field pattern."""
        self.sensitive_patterns.append(pattern)
        self._compiled_field_patterns.append(re.compile(pattern, re.IGNORECASE))
    
    def add_value_pattern(self, pattern: str) -> None:
        """Add a new sensitive value pattern."""
        self.value_patterns.append(pattern)
        self._compiled_value_patterns.append(re.compile(pattern))
    
    def add_custom_rule(self, field_path: str, rule: Callable[[Any], Any]) -> None:
        """Add a custom sanitization rule for a specific field path."""
        self.custom_rules[field_path] = rule
    
    def create_safe_copy(self, config: ConfigDict, include_metadata: bool = True) -> Dict[str, Any]:
        """
        Create a completely safe copy for logging/export.
        
        Args:
            config: Configuration to sanitize
            include_metadata: Whether to include sanitization metadata
            
        Returns:
            Safe configuration copy with optional metadata
        """
        sanitized = self.sanitize(config)
        
        if include_metadata:
            result = {
                "config": sanitized,
                "sanitization_info": {
                    "sanitized_fields": list(self._sanitized_paths),
                    "total_fields_sanitized": len(self._sanitized_paths),
                    "masking_strategy": self.masking_strategy,
                    "patterns_used": {
                        "field_patterns": self.sensitive_patterns,
                        "value_patterns": self.value_patterns
                    }
                }
            }
            return result
        
        return sanitized
    
    def validate_safe_for_logging(self, config: ConfigDict) -> bool:
        """
        Check if configuration is safe for logging without sanitization.
        
        Args:
            config: Configuration to check
            
        Returns:
            True if safe, False if contains sensitive data
        """
        # Create a copy and sanitize it
        original_paths = self._sanitized_paths.copy()
        self._sanitize_recursive(config)
        has_sensitive = bool(self._sanitized_paths)
        
        # Restore original state
        self._sanitized_paths = original_paths
        
        return not has_sensitive
    
    def get_sanitization_report(self, config: ConfigDict) -> Dict[str, Any]:
        """
        Generate a detailed sanitization report.
        
        Args:
            config: Configuration to analyze
            
        Returns:
            Detailed report of what would be sanitized
        """
        # Sanitize to populate paths
        self.sanitize(config)
        
        report = {
            "total_fields": self._count_fields(config),
            "sensitive_fields": len(self._sanitized_paths),
            "sanitized_paths": list(self._sanitized_paths),
            "safety_score": self._calculate_safety_score(config),
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _count_fields(self, obj: Any, count: int = 0) -> int:
        """Count total number of fields in configuration."""
        if isinstance(obj, dict):
            count += len(obj)
            for value in obj.values():
                count = self._count_fields(value, count)
        elif isinstance(obj, list):
            for item in obj:
                count = self._count_fields(item, count)
        
        return count
    
    def _calculate_safety_score(self, config: ConfigDict) -> float:
        """Calculate safety score (0-100, higher is safer)."""
        total_fields = self._count_fields(config)
        if total_fields == 0:
            return 100.0
        
        sensitive_fields = len(self._sanitized_paths)
        safety_ratio = 1.0 - (sensitive_fields / total_fields)
        return safety_ratio * 100.0
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations for improving configuration security."""
        recommendations = []
        
        if len(self._sanitized_paths) > 0:
            recommendations.append(
                "Consider using environment variables or secret management "
                "for sensitive configuration values"
            )
        
        if any("password" in path.lower() for path in self._sanitized_paths):
            recommendations.append(
                "Passwords found in configuration. Consider using "
                "secret references instead of plain text passwords"
            )
        
        if any("key" in path.lower() for path in self._sanitized_paths):
            recommendations.append(
                "API keys or cryptographic keys found. These should be "
                "stored in a secure secret management system"
            )
        
        return recommendations