"""Type Conversion System

Safe type conversions with data preservation, conversion path analysis,
and comprehensive validation for element type changes.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple, Union
from uuid import uuid4

from torematrix.core.models.types import TypeRegistry, TypeDefinition, get_type_registry
from torematrix.core.models.validation import ValidationResult


class ConversionStrategy(Enum):
    """Type conversion strategies"""
    DIRECT = "direct"           # Direct type change
    HIERARCHICAL = "hierarchical"  # Use type hierarchy
    TRANSFORM = "transform"     # Transform data structure
    MANUAL = "manual"          # Requires manual intervention


class DataPreservationLevel(Enum):
    """Data preservation levels"""
    STRICT = "strict"          # Preserve all data exactly
    COMPATIBLE = "compatible"  # Preserve compatible data
    LOSSY = "lossy"           # Allow data loss with warnings
    DESTRUCTIVE = "destructive"  # May lose significant data


@dataclass
class ConversionRule:
    """Rule for type conversion"""
    from_type: str
    to_type: str
    strategy: ConversionStrategy
    preservation_level: DataPreservationLevel
    data_mapping: Dict[str, str] = field(default_factory=dict)
    required_transformations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    is_reversible: bool = True
    conversion_cost: float = 1.0  # Relative cost/complexity


@dataclass
class ConversionPath:
    """Path for multi-step type conversion"""
    from_type: str
    to_type: str
    steps: List[ConversionRule]
    total_cost: float
    total_warnings: List[str]
    is_safe: bool
    estimated_data_loss: float


@dataclass
class ConversionAnalysis:
    """Analysis of type conversion requirements"""
    from_type: str
    to_type: str
    is_possible: bool
    recommended_path: Optional[ConversionPath]
    alternative_paths: List[ConversionPath]
    data_compatibility: Dict[str, str]  # field -> compatibility status
    required_user_decisions: List[str]
    estimated_complexity: float
    warnings: List[str]
    errors: List[str]


@dataclass
class ConversionResult:
    """Result of type conversion operation"""
    conversion_id: str
    element_id: str
    from_type: str
    to_type: str
    success: bool
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    conversion_path: Optional[ConversionPath] = None
    original_data: Dict[str, Any] = field(default_factory=dict)
    converted_data: Dict[str, Any] = field(default_factory=dict)
    data_loss_report: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    rollback_data: Optional[Dict[str, Any]] = None


class TypeConversionEngine:
    """Safe type conversions with data preservation and analysis"""
    
    def __init__(self, registry: TypeRegistry = None):
        """Initialize conversion engine
        
        Args:
            registry: Type registry for type information
        """
        self.registry = registry or get_type_registry()
        self.logger = logging.getLogger(__name__)
        
        # Conversion rules database
        self.conversion_rules: Dict[Tuple[str, str], ConversionRule] = {}
        self.conversion_cache: Dict[Tuple[str, str], ConversionPath] = {}
        
        # Statistics
        self.conversion_stats = {
            'total_conversions': 0,
            'successful_conversions': 0,
            'failed_conversions': 0,
            'average_conversion_time': 0.0
        }
        
        # Initialize default conversion rules
        self._initialize_default_rules()
    
    def convert_element_type(self, 
                           element_id: str, 
                           from_type: str, 
                           to_type: str,
                           preserve_data: bool = True,
                           allow_data_loss: bool = False) -> ConversionResult:
        """Convert element from one type to another
        
        Args:
            element_id: ID of element to convert
            from_type: Source type ID
            to_type: Target type ID
            preserve_data: Whether to preserve element data
            allow_data_loss: Whether to allow lossy conversions
            
        Returns:
            ConversionResult with operation details
        """
        conversion_id = str(uuid4())
        start_time = datetime.now()
        
        result = ConversionResult(
            conversion_id=conversion_id,
            element_id=element_id,
            from_type=from_type,
            to_type=to_type,
            success=False,
            start_time=start_time
        )
        
        try:
            # Validate types exist
            if not self.registry.type_exists(from_type):
                result.errors.append(f"Source type '{from_type}' does not exist")
                return result
            
            if not self.registry.type_exists(to_type):
                result.errors.append(f"Target type '{to_type}' does not exist")
                return result
            
            # Same type - no conversion needed
            if from_type == to_type:
                result.success = True
                result.warnings.append("Source and target types are identical")
                return result
            
            # Get conversion path
            conversion_path = self.get_conversion_path(from_type, to_type)
            if not conversion_path or not conversion_path.is_safe:
                result.errors.append("No safe conversion path available")
                if conversion_path:
                    result.warnings.extend(conversion_path.total_warnings)
                return result
            
            result.conversion_path = conversion_path
            
            # Check data preservation requirements
            if preserve_data and not allow_data_loss:
                max_allowed_loss = 0.1  # 10% data loss threshold
                if conversion_path.estimated_data_loss > max_allowed_loss:
                    result.errors.append(
                        f"Conversion would cause {conversion_path.estimated_data_loss:.1%} "
                        f"data loss (max allowed: {max_allowed_loss:.1%})"
                    )
                    return result
            
            # Get original element data
            if preserve_data:
                result.original_data = self._get_element_data(element_id)
                if not result.original_data:
                    result.warnings.append("No element data found to preserve")
            
            # Execute conversion
            converted_data = self._execute_conversion(
                result.original_data, conversion_path, preserve_data
            )
            result.converted_data = converted_data
            
            # Apply conversion to element
            success = self._apply_conversion_to_element(
                element_id, to_type, converted_data
            )
            
            if success:
                result.success = True
                
                # Generate data loss report
                if preserve_data:
                    result.data_loss_report = self._generate_data_loss_report(
                        result.original_data, result.converted_data
                    )
                
                # Prepare rollback data
                result.rollback_data = {
                    'original_type': from_type,
                    'original_data': result.original_data,
                    'element_id': element_id
                }
                
                self.logger.info(
                    f"Successfully converted element {element_id} "
                    f"from {from_type} to {to_type}"
                )
            else:
                result.errors.append("Failed to apply conversion to element")
                
        except Exception as e:
            result.errors.append(f"Conversion failed: {str(e)}")
            self.logger.error(f"Conversion error for element {element_id}: {e}")
        
        finally:
            # Finalize result
            result.end_time = datetime.now()
            result.duration_seconds = (
                result.end_time - result.start_time
            ).total_seconds()
            
            # Update statistics
            self._update_conversion_stats(result)
        
        return result
    
    def get_conversion_path(self, from_type: str, to_type: str) -> Optional[ConversionPath]:
        """Get optimal conversion path between types
        
        Args:
            from_type: Source type ID
            to_type: Target type ID
            
        Returns:
            ConversionPath if conversion is possible, None otherwise
        """
        # Check cache first
        cache_key = (from_type, to_type)
        if cache_key in self.conversion_cache:
            return self.conversion_cache[cache_key]
        
        # Same type - no conversion needed
        if from_type == to_type:
            path = ConversionPath(
                from_type=from_type,
                to_type=to_type,
                steps=[],
                total_cost=0.0,
                total_warnings=[],
                is_safe=True,
                estimated_data_loss=0.0
            )
            self.conversion_cache[cache_key] = path
            return path
        
        # Find direct conversion rule
        direct_rule = self.conversion_rules.get((from_type, to_type))
        if direct_rule:
            path = ConversionPath(
                from_type=from_type,
                to_type=to_type,
                steps=[direct_rule],
                total_cost=direct_rule.conversion_cost,
                total_warnings=direct_rule.warnings.copy(),
                is_safe=direct_rule.preservation_level != DataPreservationLevel.DESTRUCTIVE,
                estimated_data_loss=self._estimate_data_loss(direct_rule)
            )
            self.conversion_cache[cache_key] = path
            return path
        
        # Try hierarchical conversion (through common ancestor)
        hierarchical_path = self._find_hierarchical_path(from_type, to_type)
        if hierarchical_path:
            self.conversion_cache[cache_key] = hierarchical_path
            return hierarchical_path
        
        # Try multi-step conversion
        multi_step_path = self._find_multi_step_path(from_type, to_type)
        if multi_step_path:
            self.conversion_cache[cache_key] = multi_step_path
            return multi_step_path
        
        # No conversion path found
        return None
    
    def analyze_conversion_impact(self, from_type: str, to_type: str) -> ConversionAnalysis:
        """Analyze impact and requirements of type conversion
        
        Args:
            from_type: Source type ID
            to_type: Target type ID
            
        Returns:
            ConversionAnalysis with detailed analysis
        """
        analysis = ConversionAnalysis(
            from_type=from_type,
            to_type=to_type,
            is_possible=False,
            recommended_path=None,
            alternative_paths=[],
            data_compatibility={},
            required_user_decisions=[],
            estimated_complexity=0.0,
            warnings=[],
            errors=[]
        )
        
        try:
            # Validate types
            from_type_def = self.registry.get_type(from_type)
            to_type_def = self.registry.get_type(to_type)
            
            if not from_type_def:
                analysis.errors.append(f"Source type '{from_type}' not found")
                return analysis
            
            if not to_type_def:
                analysis.errors.append(f"Target type '{to_type}' not found")
                return analysis
            
            # Find conversion paths
            primary_path = self.get_conversion_path(from_type, to_type)
            if primary_path:
                analysis.is_possible = True
                analysis.recommended_path = primary_path
                analysis.estimated_complexity = primary_path.total_cost
            
            # Find alternative paths
            alternative_paths = self._find_alternative_paths(from_type, to_type)
            analysis.alternative_paths = alternative_paths
            
            # Analyze data compatibility
            analysis.data_compatibility = self._analyze_data_compatibility(
                from_type_def, to_type_def
            )
            
            # Identify required user decisions
            analysis.required_user_decisions = self._identify_user_decisions(
                from_type_def, to_type_def, primary_path
            )
            
            # Generate warnings
            if primary_path and primary_path.estimated_data_loss > 0:
                analysis.warnings.append(
                    f"Conversion may result in {primary_path.estimated_data_loss:.1%} data loss"
                )
            
            if not analysis.alternative_paths:
                analysis.warnings.append("No alternative conversion paths available")
            
        except Exception as e:
            analysis.errors.append(f"Analysis failed: {str(e)}")
            self.logger.error(f"Conversion analysis error: {e}")
        
        return analysis
    
    def preserve_element_data(self, 
                            element_data: Dict[str, Any], 
                            conversion_map: Dict[str, str]) -> Dict[str, Any]:
        """Preserve element data during conversion using mapping
        
        Args:
            element_data: Original element data
            conversion_map: Field mapping for conversion
            
        Returns:
            Preserved data dictionary
        """
        preserved_data = {}
        
        for source_field, target_field in conversion_map.items():
            if source_field in element_data:
                preserved_data[target_field] = element_data[source_field]
        
        # Copy unmapped fields that don't conflict
        for field, value in element_data.items():
            if field not in conversion_map and field not in preserved_data:
                preserved_data[field] = value
        
        return preserved_data
    
    def register_conversion_rule(self, rule: ConversionRule):
        """Register a new conversion rule
        
        Args:
            rule: ConversionRule to register
        """
        key = (rule.from_type, rule.to_type)
        self.conversion_rules[key] = rule
        
        # Clear cache for affected conversions
        self._clear_conversion_cache(rule.from_type, rule.to_type)
        
        self.logger.info(
            f"Registered conversion rule: {rule.from_type} -> {rule.to_type}"
        )
    
    def get_conversion_statistics(self) -> Dict[str, Any]:
        """Get conversion engine statistics
        
        Returns:
            Dictionary with conversion statistics
        """
        return {
            **self.conversion_stats,
            'registered_rules': len(self.conversion_rules),
            'cached_paths': len(self.conversion_cache)
        }
    
    def _initialize_default_rules(self):
        """Initialize default conversion rules"""
        # Text-based conversions
        self.register_conversion_rule(ConversionRule(
            from_type="text",
            to_type="title",
            strategy=ConversionStrategy.DIRECT,
            preservation_level=DataPreservationLevel.STRICT,
            conversion_cost=0.5
        ))
        
        self.register_conversion_rule(ConversionRule(
            from_type="title",
            to_type="text",
            strategy=ConversionStrategy.DIRECT,
            preservation_level=DataPreservationLevel.STRICT,
            conversion_cost=0.5
        ))
        
        # Structure-based conversions
        self.register_conversion_rule(ConversionRule(
            from_type="list_item",
            to_type="text",
            strategy=ConversionStrategy.TRANSFORM,
            preservation_level=DataPreservationLevel.COMPATIBLE,
            data_mapping={"content": "text", "bullet": "prefix"},
            conversion_cost=1.0
        ))
        
        # Media conversions
        self.register_conversion_rule(ConversionRule(
            from_type="image",
            to_type="text",
            strategy=ConversionStrategy.TRANSFORM,
            preservation_level=DataPreservationLevel.LOSSY,
            data_mapping={"alt_text": "text", "caption": "description"},
            warnings=["Image visual content will be lost"],
            conversion_cost=2.0
        ))
    
    def _find_hierarchical_path(self, from_type: str, to_type: str) -> Optional[ConversionPath]:
        """Find conversion path through type hierarchy"""
        try:
            from_type_def = self.registry.get_type(from_type)
            to_type_def = self.registry.get_type(to_type)
            
            # Check if types are related in hierarchy
            if to_type in from_type_def.get_all_parent_types(self.registry):
                # Converting to parent type (generalization)
                rule = ConversionRule(
                    from_type=from_type,
                    to_type=to_type,
                    strategy=ConversionStrategy.HIERARCHICAL,
                    preservation_level=DataPreservationLevel.COMPATIBLE,
                    conversion_cost=1.0
                )
                
                return ConversionPath(
                    from_type=from_type,
                    to_type=to_type,
                    steps=[rule],
                    total_cost=1.0,
                    total_warnings=["Generalizing to parent type"],
                    is_safe=True,
                    estimated_data_loss=0.1
                )
            
            elif from_type in to_type_def.get_all_parent_types(self.registry):
                # Converting to child type (specialization)
                rule = ConversionRule(
                    from_type=from_type,
                    to_type=to_type,
                    strategy=ConversionStrategy.HIERARCHICAL,
                    preservation_level=DataPreservationLevel.COMPATIBLE,
                    conversion_cost=1.5,
                    warnings=["Specializing to child type may require additional data"]
                )
                
                return ConversionPath(
                    from_type=from_type,
                    to_type=to_type,
                    steps=[rule],
                    total_cost=1.5,
                    total_warnings=rule.warnings,
                    is_safe=True,
                    estimated_data_loss=0.0
                )
        
        except Exception as e:
            self.logger.error(f"Error finding hierarchical path: {e}")
        
        return None
    
    def _find_multi_step_path(self, from_type: str, to_type: str) -> Optional[ConversionPath]:
        """Find multi-step conversion path using graph search"""
        # Simplified implementation - could use Dijkstra's algorithm
        # For now, try single intermediate step
        
        for intermediate_type in self.registry.list_types():
            step1 = self.conversion_rules.get((from_type, intermediate_type.type_id))
            step2 = self.conversion_rules.get((intermediate_type.type_id, to_type))
            
            if step1 and step2:
                total_cost = step1.conversion_cost + step2.conversion_cost
                total_warnings = step1.warnings + step2.warnings
                
                # Only allow if total cost is reasonable
                if total_cost <= 5.0:
                    return ConversionPath(
                        from_type=from_type,
                        to_type=to_type,
                        steps=[step1, step2],
                        total_cost=total_cost,
                        total_warnings=total_warnings,
                        is_safe=step1.preservation_level != DataPreservationLevel.DESTRUCTIVE and
                               step2.preservation_level != DataPreservationLevel.DESTRUCTIVE,
                        estimated_data_loss=self._estimate_data_loss(step1) + 
                                          self._estimate_data_loss(step2)
                    )
        
        return None
    
    def _find_alternative_paths(self, from_type: str, to_type: str) -> List[ConversionPath]:
        """Find alternative conversion paths"""
        alternatives = []
        
        # Find all possible intermediate steps
        for intermediate_type in self.registry.list_types():
            type_id = intermediate_type.type_id
            if type_id != from_type and type_id != to_type:
                path = self._find_multi_step_path(from_type, to_type)
                if path and path not in alternatives:
                    alternatives.append(path)
        
        # Sort by cost and safety
        alternatives.sort(key=lambda p: (not p.is_safe, p.total_cost))
        
        return alternatives[:3]  # Return top 3 alternatives
    
    def _analyze_data_compatibility(self, 
                                  from_type: TypeDefinition, 
                                  to_type: TypeDefinition) -> Dict[str, str]:
        """Analyze compatibility of data fields between types"""
        compatibility = {}
        
        # Compare properties
        from_props = set(from_type.properties.keys())
        to_props = set(to_type.properties.keys())
        
        for prop in from_props:
            if prop in to_props:
                compatibility[prop] = "compatible"
            else:
                compatibility[prop] = "will_be_lost"
        
        for prop in to_props - from_props:
            compatibility[prop] = "requires_default_value"
        
        return compatibility
    
    def _identify_user_decisions(self, 
                               from_type: TypeDefinition, 
                               to_type: TypeDefinition,
                               conversion_path: Optional[ConversionPath]) -> List[str]:
        """Identify decisions that require user input"""
        decisions = []
        
        if conversion_path:
            for step in conversion_path.steps:
                if step.strategy == ConversionStrategy.MANUAL:
                    decisions.append(f"Manual conversion required for {step.from_type} -> {step.to_type}")
                
                if step.preservation_level == DataPreservationLevel.LOSSY:
                    decisions.append(f"Confirm data loss for {step.from_type} -> {step.to_type}")
        
        return decisions
    
    def _execute_conversion(self, 
                          original_data: Dict[str, Any], 
                          conversion_path: ConversionPath,
                          preserve_data: bool) -> Dict[str, Any]:
        """Execute the actual data conversion"""
        current_data = original_data.copy() if preserve_data else {}
        
        for step in conversion_path.steps:
            if step.data_mapping and preserve_data:
                current_data = self.preserve_element_data(current_data, step.data_mapping)
            
            # Apply any required transformations
            for transformation in step.required_transformations:
                current_data = self._apply_transformation(current_data, transformation)
        
        return current_data
    
    def _apply_transformation(self, data: Dict[str, Any], transformation: str) -> Dict[str, Any]:
        """Apply data transformation"""
        # Placeholder for transformation logic
        return data
    
    def _apply_conversion_to_element(self, 
                                   element_id: str, 
                                   new_type: str, 
                                   new_data: Dict[str, Any]) -> bool:
        """Apply conversion result to actual element"""
        # Placeholder - would update actual element in storage
        return True
    
    def _get_element_data(self, element_id: str) -> Dict[str, Any]:
        """Get current element data"""
        # Placeholder - would retrieve from actual storage
        return {"text": "sample content", "confidence": 0.9}
    
    def _generate_data_loss_report(self, 
                                 original_data: Dict[str, Any], 
                                 converted_data: Dict[str, Any]) -> List[str]:
        """Generate report of data loss during conversion"""
        lost_fields = []
        
        for field in original_data:
            if field not in converted_data:
                lost_fields.append(f"Field '{field}' was removed")
            elif original_data[field] != converted_data[field]:
                lost_fields.append(f"Field '{field}' was modified")
        
        return lost_fields
    
    def _estimate_data_loss(self, rule: ConversionRule) -> float:
        """Estimate percentage of data loss for conversion rule"""
        loss_map = {
            DataPreservationLevel.STRICT: 0.0,
            DataPreservationLevel.COMPATIBLE: 0.05,
            DataPreservationLevel.LOSSY: 0.25,
            DataPreservationLevel.DESTRUCTIVE: 0.75
        }
        return loss_map.get(rule.preservation_level, 0.5)
    
    def _update_conversion_stats(self, result: ConversionResult):
        """Update conversion statistics"""
        self.conversion_stats['total_conversions'] += 1
        
        if result.success:
            self.conversion_stats['successful_conversions'] += 1
        else:
            self.conversion_stats['failed_conversions'] += 1
        
        if result.duration_seconds:
            current_avg = self.conversion_stats['average_conversion_time']
            total = self.conversion_stats['total_conversions']
            new_avg = (current_avg * (total - 1) + result.duration_seconds) / total
            self.conversion_stats['average_conversion_time'] = new_avg
    
    def _clear_conversion_cache(self, from_type: str, to_type: str):
        """Clear cached conversion paths affected by new rule"""
        keys_to_remove = [
            key for key in self.conversion_cache.keys()
            if key[0] == from_type or key[1] == to_type
        ]
        
        for key in keys_to_remove:
            del self.conversion_cache[key]