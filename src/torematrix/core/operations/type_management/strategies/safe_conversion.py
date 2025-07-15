"""Safe Conversion Strategy

Strategies for safe type conversions with minimal data loss.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any, Set

logger = logging.getLogger(__name__)


class ConversionSafetyLevel(Enum):
    """Safety levels for type conversions"""
    STRICT = "strict"           # No data loss allowed
    CONSERVATIVE = "conservative" # Minimal data loss acceptable
    MODERATE = "moderate"       # Some data loss acceptable with warnings
    PERMISSIVE = "permissive"   # Allow conversions with significant data loss


@dataclass
class SafeConversionRule:
    """Rule for safe type conversion"""
    from_type: str
    to_type: str
    safety_level: ConversionSafetyLevel
    required_validations: List[str]
    data_mapping: Dict[str, str]
    preservation_requirements: List[str]


class SafeConversionStrategy:
    """Strategy for safe type conversions"""
    
    def __init__(self, safety_level: ConversionSafetyLevel = ConversionSafetyLevel.CONSERVATIVE):
        self.safety_level = safety_level
        self._conversion_rules: Dict[tuple, SafeConversionRule] = {}
        self._initialize_rules()
    
    def is_conversion_safe(self, from_type: str, to_type: str, data: Optional[Dict] = None) -> bool:
        """Check if conversion is safe according to strategy"""
        rule_key = (from_type, to_type)
        if rule_key not in self._conversion_rules:
            return self.safety_level == ConversionSafetyLevel.PERMISSIVE
        
        rule = self._conversion_rules[rule_key]
        return rule.safety_level.value <= self.safety_level.value
    
    def get_conversion_requirements(self, from_type: str, to_type: str) -> Dict[str, Any]:
        """Get requirements for safe conversion"""
        rule_key = (from_type, to_type)
        if rule_key not in self._conversion_rules:
            return {'safe': False, 'requirements': []}
        
        rule = self._conversion_rules[rule_key]
        return {
            'safe': rule.safety_level.value <= self.safety_level.value,
            'requirements': rule.preservation_requirements,
            'validations': rule.required_validations,
            'data_mapping': rule.data_mapping
        }
    
    def _initialize_rules(self) -> None:
        """Initialize default safe conversion rules"""
        # Text to paragraph (very safe)
        self._conversion_rules[('text', 'paragraph')] = SafeConversionRule(
            from_type='text',
            to_type='paragraph',
            safety_level=ConversionSafetyLevel.STRICT,
            required_validations=['content_validation'],
            data_mapping={'content': 'content', 'formatting': 'formatting'},
            preservation_requirements=['preserve_content', 'preserve_formatting']
        )
        
        # Heading to text (moderate safety)
        self._conversion_rules[('heading', 'text')] = SafeConversionRule(
            from_type='heading',
            to_type='text',
            safety_level=ConversionSafetyLevel.MODERATE,
            required_validations=['hierarchy_validation'],
            data_mapping={'content': 'content'},
            preservation_requirements=['preserve_content', 'warn_hierarchy_loss']
        )