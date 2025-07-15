"""Type Conversion Engine

Safe type conversions with data preservation and validation.
Provides intelligent conversion paths and data migration strategies.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Callable, Union
import json
import copy

from torematrix.core.models.types import TypeRegistry, TypeDefinition


logger = logging.getLogger(__name__)


class ConversionStrategy(Enum):
    """Conversion strategies for type changes"""
    DIRECT = "direct"           # Direct conversion without intermediate steps
    STAGED = "staged"           # Multi-step conversion through intermediate types
    COMPATIBLE = "compatible"   # Use compatible type features only
    BEST_EFFORT = "best_effort" # Convert what's possible, warn about losses


class ConversionRisk(Enum):
    """Risk levels for type conversions"""
    SAFE = "safe"               # No data loss expected
    LOW = "low"                # Minimal data loss risk
    MEDIUM = "medium"           # Some data may be lost or transformed
    HIGH = "high"               # Significant data loss expected
    UNSAFE = "unsafe"           # Conversion not recommended


@dataclass
class ConversionRule:
    """Rule for converting between specific types"""
    from_type: str
    to_type: str
    strategy: ConversionStrategy
    risk_level: ConversionRisk
    data_mapping: Dict[str, str] = field(default_factory=dict)
    validation_rules: List[str] = field(default_factory=list)
    transformation_function: Optional[Callable] = None
    preserve_metadata: bool = True
    warning_message: Optional[str] = None


@dataclass 
class DataMappingRule:
    """Rule for mapping data between type schemas"""
    source_field: str
    target_field: str
    transformation: Optional[str] = None
    default_value: Any = None
    required: bool = False
    validation: Optional[str] = None


@dataclass
class ConversionAnalysis:
    """Analysis of a type conversion"""
    from_type: str
    to_type: str
    conversion_path: List[str]
    risk_level: ConversionRisk
    data_preservation_score: float  # 0.0 to 1.0
    warnings: List[str]
    errors: List[str]
    estimated_duration: float
    data_mappings: List[DataMappingRule]
    required_transformations: List[str]
    
    @property
    def is_safe(self) -> bool:
        """Check if conversion is safe to execute"""
        return (self.risk_level in (ConversionRisk.SAFE, ConversionRisk.LOW) and
                len(self.errors) == 0 and
                self.data_preservation_score >= 0.8)


@dataclass
class ConversionResult:
    """Result of a type conversion operation"""
    element_id: str
    from_type: str
    to_type: str
    success: bool
    conversion_path: List[str]
    preserved_data: Dict[str, Any]
    lost_data: Dict[str, Any]
    warnings: List[str]
    errors: List[str]
    start_time: datetime
    end_time: datetime
    
    @property
    def duration_seconds(self) -> float:
        """Calculate conversion duration in seconds"""
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def data_preservation_rate(self) -> float:
        """Calculate data preservation rate"""
        total_fields = len(self.preserved_data) + len(self.lost_data)
        if total_fields == 0:
            return 1.0
        return len(self.preserved_data) / total_fields


class TypeConversionEngine:
    """Safe type conversions with data preservation
    
    Provides intelligent type conversion with:
    - Multiple conversion strategies
    - Data preservation and migration
    - Risk assessment and warnings
    - Conversion path optimization
    - Rollback capabilities
    """
    
    def __init__(self, registry: TypeRegistry):
        """Initialize conversion engine
        
        Args:
            registry: Type registry with type definitions
        """
        self.registry = registry
        self._conversion_rules: Dict[tuple, ConversionRule] = {}
        self._data_transformers: Dict[str, Callable] = {}
        self._initialize_default_rules()
        
        logger.info("TypeConversionEngine initialized")
    
    def register_conversion_rule(self, rule: ConversionRule) -> None:
        """Register a conversion rule
        
        Args:
            rule: ConversionRule to register
        """
        key = (rule.from_type, rule.to_type)
        self._conversion_rules[key] = rule
        logger.debug(f"Registered conversion rule: {rule.from_type} -> {rule.to_type}")
    
    def register_data_transformer(self, name: str, transformer: Callable) -> None:
        """Register a data transformation function
        
        Args:
            name: Name of the transformer
            transformer: Function that transforms data
        """
        self._data_transformers[name] = transformer
        logger.debug(f"Registered data transformer: {name}")
    
    def convert_element_type(self, 
                           element_id: str, 
                           from_type: str, 
                           to_type: str,
                           element_data: Optional[Dict[str, Any]] = None,
                           preserve_data: bool = True) -> ConversionResult:
        """Convert element type with data preservation
        
        Args:
            element_id: ID of element to convert
            from_type: Current type of element
            to_type: Target type for conversion
            element_data: Current element data (optional)
            preserve_data: Whether to preserve data during conversion
            
        Returns:
            ConversionResult with conversion details
            
        Raises:
            ValueError: If types are invalid
            RuntimeError: If conversion fails
        """
        logger.info(f"Converting element {element_id}: {from_type} -> {to_type}")
        
        start_time = datetime.now()
        
        # Validate types
        if not self.registry.has_type(from_type):
            raise ValueError(f"Source type '{from_type}' not found in registry")
        if not self.registry.has_type(to_type):
            raise ValueError(f"Target type '{to_type}' not found in registry")
        
        # Skip if already target type
        if from_type == to_type:
            return ConversionResult(
                element_id=element_id,
                from_type=from_type,
                to_type=to_type,
                success=True,
                conversion_path=[from_type],
                preserved_data=element_data or {},
                lost_data={},
                warnings=[],
                errors=[],
                start_time=start_time,
                end_time=datetime.now()
            )
        
        try:
            # Get conversion path
            conversion_path = self.get_conversion_path(from_type, to_type)
            if not conversion_path:
                raise RuntimeError(f"No conversion path found from {from_type} to {to_type}")
            
            # Get element data if not provided
            if element_data is None:
                element_data = self._get_element_data(element_id)
            
            # Execute conversion
            result_data = element_data.copy() if preserve_data else {}
            preserved_data = {}
            lost_data = {}
            warnings = []
            errors = []
            
            # Apply conversions along path
            current_data = element_data.copy()
            for i in range(len(conversion_path) - 1):
                current_type = conversion_path[i]
                next_type = conversion_path[i + 1]
                
                step_result = self._convert_single_step(
                    current_type, next_type, current_data, preserve_data
                )
                
                current_data = step_result['data']
                preserved_data.update(step_result['preserved'])
                lost_data.update(step_result['lost'])
                warnings.extend(step_result['warnings'])
                errors.extend(step_result['errors'])
                
                if step_result['errors']:
                    raise RuntimeError(f"Conversion failed at step {current_type} -> {next_type}")
            
            # Update element with new type and data
            if preserve_data:
                self._update_element_data(element_id, to_type, current_data)
            else:
                self._update_element_type(element_id, to_type)
            
            return ConversionResult(
                element_id=element_id,
                from_type=from_type,
                to_type=to_type,
                success=True,
                conversion_path=conversion_path,
                preserved_data=preserved_data,
                lost_data=lost_data,
                warnings=warnings,
                errors=errors,
                start_time=start_time,
                end_time=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Conversion failed for element {element_id}: {e}")
            return ConversionResult(
                element_id=element_id,
                from_type=from_type,
                to_type=to_type,
                success=False,
                conversion_path=[],
                preserved_data={},
                lost_data={},
                warnings=[],
                errors=[str(e)],
                start_time=start_time,
                end_time=datetime.now()
            )
    
    def get_conversion_path(self, from_type: str, to_type: str) -> List[str]:
        """Find optimal conversion path between types
        
        Args:
            from_type: Source type
            to_type: Target type
            
        Returns:
            List of types representing conversion path, empty if no path found
        """
        if from_type == to_type:
            return [from_type]
        
        # Check for direct conversion
        direct_key = (from_type, to_type)
        if direct_key in self._conversion_rules:
            return [from_type, to_type]
        
        # Use breadth-first search to find shortest path
        queue = [(from_type, [from_type])]
        visited = {from_type}
        
        while queue:
            current_type, path = queue.pop(0)
            
            # Check all possible conversions from current type
            for (source, target), rule in self._conversion_rules.items():
                if source == current_type and target not in visited:
                    new_path = path + [target]
                    
                    if target == to_type:
                        logger.debug(f"Found conversion path: {' -> '.join(new_path)}")
                        return new_path
                    
                    queue.append((target, new_path))
                    visited.add(target)
        
        logger.warning(f"No conversion path found from {from_type} to {to_type}")
        return []
    
    def analyze_conversion_impact(self, 
                                from_type: str, 
                                to_type: str,
                                sample_data: Optional[Dict[str, Any]] = None) -> ConversionAnalysis:
        """Analyze impact of type conversion
        
        Args:
            from_type: Source type
            to_type: Target type
            sample_data: Sample data to analyze (optional)
            
        Returns:
            ConversionAnalysis with detailed impact assessment
        """
        logger.debug(f"Analyzing conversion impact: {from_type} -> {to_type}")
        
        warnings = []
        errors = []
        
        # Get conversion path
        conversion_path = self.get_conversion_path(from_type, to_type)
        if not conversion_path:
            errors.append(f"No conversion path available from {from_type} to {to_type}")
            return ConversionAnalysis(
                from_type=from_type,
                to_type=to_type,
                conversion_path=[],
                risk_level=ConversionRisk.UNSAFE,
                data_preservation_score=0.0,
                warnings=warnings,
                errors=errors,
                estimated_duration=0.0,
                data_mappings=[],
                required_transformations=[]
            )
        
        # Analyze each step in conversion path
        overall_risk = ConversionRisk.SAFE
        preservation_scores = []
        data_mappings = []
        required_transformations = []
        
        for i in range(len(conversion_path) - 1):
            current_type = conversion_path[i]
            next_type = conversion_path[i + 1]
            
            step_key = (current_type, next_type)
            if step_key in self._conversion_rules:
                rule = self._conversion_rules[step_key]
                
                # Update overall risk
                if rule.risk_level.value > overall_risk.value:
                    overall_risk = rule.risk_level
                
                # Estimate data preservation for this step
                step_preservation = self._estimate_data_preservation(rule, sample_data)
                preservation_scores.append(step_preservation)
                
                # Collect data mappings
                for source_field, target_field in rule.data_mapping.items():
                    data_mappings.append(DataMappingRule(
                        source_field=source_field,
                        target_field=target_field
                    ))
                
                # Collect required transformations
                if rule.transformation_function:
                    required_transformations.append(f"{current_type}->{next_type}")
                
                # Add warnings
                if rule.warning_message:
                    warnings.append(rule.warning_message)
            else:
                warnings.append(f"No explicit rule for {current_type} -> {next_type}")
                preservation_scores.append(0.8)  # Conservative estimate
        
        # Calculate overall preservation score
        avg_preservation = sum(preservation_scores) / len(preservation_scores) if preservation_scores else 0.0
        
        # Estimate duration (simple heuristic)
        estimated_duration = len(conversion_path) * 0.1  # 100ms per step
        
        return ConversionAnalysis(
            from_type=from_type,
            to_type=to_type,
            conversion_path=conversion_path,
            risk_level=overall_risk,
            data_preservation_score=avg_preservation,
            warnings=warnings,
            errors=errors,
            estimated_duration=estimated_duration,
            data_mappings=data_mappings,
            required_transformations=required_transformations
        )
    
    def get_compatible_types(self, source_type: str) -> List[str]:
        """Get list of types compatible for conversion from source type
        
        Args:
            source_type: Source type to find compatible targets for
            
        Returns:
            List of compatible target types
        """
        compatible = []
        
        for (from_type, to_type), rule in self._conversion_rules.items():
            if from_type == source_type and rule.risk_level != ConversionRisk.UNSAFE:
                compatible.append(to_type)
        
        return sorted(compatible)
    
    def preserve_element_data(self, 
                            element_data: Dict[str, Any], 
                            conversion_map: Dict[str, str]) -> Dict[str, Any]:
        """Preserve element data during conversion using mapping
        
        Args:
            element_data: Original element data
            conversion_map: Mapping from source to target fields
            
        Returns:
            Preserved data with mapped fields
        """
        preserved = {}
        
        for source_field, target_field in conversion_map.items():
            if source_field in element_data:
                preserved[target_field] = element_data[source_field]
        
        return preserved
    
    def _initialize_default_rules(self) -> None:
        """Initialize default conversion rules for common types"""
        
        # Text type conversions
        self.register_conversion_rule(ConversionRule(
            from_type="text",
            to_type="paragraph",
            strategy=ConversionStrategy.DIRECT,
            risk_level=ConversionRisk.SAFE,
            data_mapping={"content": "content", "formatting": "formatting"}
        ))
        
        self.register_conversion_rule(ConversionRule(
            from_type="paragraph",
            to_type="heading",
            strategy=ConversionStrategy.DIRECT,
            risk_level=ConversionRisk.LOW,
            data_mapping={"content": "content"},
            warning_message="Paragraph formatting may be lost when converting to heading"
        ))
        
        self.register_conversion_rule(ConversionRule(
            from_type="heading",
            to_type="text",
            strategy=ConversionStrategy.DIRECT,
            risk_level=ConversionRisk.SAFE,
            data_mapping={"content": "content"}
        ))
        
        # List type conversions
        self.register_conversion_rule(ConversionRule(
            from_type="list_item",
            to_type="paragraph",
            strategy=ConversionStrategy.DIRECT,
            risk_level=ConversionRisk.LOW,
            data_mapping={"content": "content"}
        ))
        
        self.register_conversion_rule(ConversionRule(
            from_type="table_cell",
            to_type="text",
            strategy=ConversionStrategy.DIRECT,
            risk_level=ConversionRisk.MEDIUM,
            data_mapping={"content": "content"},
            warning_message="Table structure will be lost"
        ))
        
        logger.debug(f"Initialized {len(self._conversion_rules)} default conversion rules")
    
    def _convert_single_step(self, 
                           from_type: str, 
                           to_type: str,
                           data: Dict[str, Any],
                           preserve_data: bool) -> Dict[str, Any]:
        """Convert single step in conversion path"""
        
        result = {
            'data': {},
            'preserved': {},
            'lost': {},
            'warnings': [],
            'errors': []
        }
        
        rule_key = (from_type, to_type)
        if rule_key not in self._conversion_rules:
            result['errors'].append(f"No conversion rule for {from_type} -> {to_type}")
            return result
        
        rule = self._conversion_rules[rule_key]
        
        if preserve_data:
            # Apply data mapping
            for source_field, target_field in rule.data_mapping.items():
                if source_field in data:
                    result['data'][target_field] = data[source_field]
                    result['preserved'][target_field] = data[source_field]
                else:
                    result['warnings'].append(f"Source field '{source_field}' not found")
            
            # Track lost data
            for field, value in data.items():
                if field not in rule.data_mapping:
                    result['lost'][field] = value
            
            # Apply transformation if specified
            if rule.transformation_function:
                try:
                    result['data'] = rule.transformation_function(result['data'])
                except Exception as e:
                    result['errors'].append(f"Transformation failed: {e}")
        else:
            # No data preservation, just basic structure
            result['data'] = {}
        
        return result
    
    def _estimate_data_preservation(self, 
                                  rule: ConversionRule,
                                  sample_data: Optional[Dict[str, Any]]) -> float:
        """Estimate data preservation score for a conversion rule"""
        
        if not sample_data:
            # Base estimate on rule risk level
            risk_scores = {
                ConversionRisk.SAFE: 1.0,
                ConversionRisk.LOW: 0.9,
                ConversionRisk.MEDIUM: 0.7,
                ConversionRisk.HIGH: 0.4,
                ConversionRisk.UNSAFE: 0.0
            }
            return risk_scores.get(rule.risk_level, 0.5)
        
        # Calculate based on actual data mapping
        total_fields = len(sample_data)
        mapped_fields = len([f for f in sample_data.keys() if f in rule.data_mapping])
        
        if total_fields == 0:
            return 1.0
        
        return mapped_fields / total_fields
    
    # Mock helper methods (would interface with actual storage in real implementation)
    
    def _get_element_data(self, element_id: str) -> Dict[str, Any]:
        """Get element data from storage (mock)"""
        return {
            "content": f"Sample content for {element_id}",
            "formatting": {"bold": False, "italic": False},
            "metadata": {"created": datetime.now().isoformat()}
        }
    
    def _update_element_data(self, element_id: str, new_type: str, data: Dict[str, Any]) -> None:
        """Update element type and data in storage (mock)"""
        logger.debug(f"Updating element {element_id} to type {new_type} with data")
    
    def _update_element_type(self, element_id: str, new_type: str) -> None:
        """Update element type in storage (mock)"""
        logger.debug(f"Updating element {element_id} to type {new_type}")