"""Conversion Warning System

Pre-conversion analysis and warning system for type conversions.
Provides detailed risk assessment and user guidance for safe conversions.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Union
import json

from torematrix.core.models.types import TypeRegistry, TypeDefinition


logger = logging.getLogger(__name__)


class WarningLevel(Enum):
    """Severity levels for conversion warnings"""
    INFO = "info"           # Informational message
    LOW = "low"             # Minor concern, proceed with caution
    MEDIUM = "medium"       # Moderate concern, review carefully
    HIGH = "high"           # Major concern, proceed only if necessary
    CRITICAL = "critical"   # Severe risk, strongly discouraged


class WarningCategory(Enum):
    """Categories of conversion warnings"""
    DATA_LOSS = "data_loss"                 # Potential data loss
    FORMAT_CHANGE = "format_change"         # Format/structure changes
    COMPATIBILITY = "compatibility"         # Compatibility issues
    PERFORMANCE = "performance"             # Performance implications
    VALIDATION = "validation"               # Validation concerns
    DEPENDENCY = "dependency"               # Dependency impacts
    REVERSIBILITY = "reversibility"         # Reversibility concerns


@dataclass
class ConversionWarning:
    """Individual conversion warning"""
    warning_id: str
    level: WarningLevel
    category: WarningCategory
    title: str
    message: str
    details: str = ""
    affected_fields: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    documentation_links: List[str] = field(default_factory=list)
    can_suppress: bool = True
    requires_confirmation: bool = False
    
    @property
    def is_blocking(self) -> bool:
        """Check if warning should block conversion"""
        return self.level == WarningLevel.CRITICAL and self.requires_confirmation


@dataclass
class WarningReport:
    """Comprehensive warning report for conversion"""
    from_type: str
    to_type: str
    element_count: int
    warnings: List[ConversionWarning]
    overall_risk_level: WarningLevel
    blocking_warnings: List[ConversionWarning]
    suppressible_warnings: List[ConversionWarning]
    estimated_data_loss: float  # Percentage
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.now)
    
    @property
    def total_warnings(self) -> int:
        """Total number of warnings"""
        return len(self.warnings)
    
    @property
    def critical_warnings(self) -> List[ConversionWarning]:
        """List of critical warnings"""
        return [w for w in self.warnings if w.level == WarningLevel.CRITICAL]
    
    @property
    def high_warnings(self) -> List[ConversionWarning]:
        """List of high-level warnings"""
        return [w for w in self.warnings if w.level == WarningLevel.HIGH]
    
    @property
    def can_proceed(self) -> bool:
        """Check if conversion can proceed without user confirmation"""
        return len(self.blocking_warnings) == 0
    
    @property
    def warnings_by_category(self) -> Dict[WarningCategory, List[ConversionWarning]]:
        """Group warnings by category"""
        grouped = {}
        for warning in self.warnings:
            if warning.category not in grouped:
                grouped[warning.category] = []
            grouped[warning.category].append(warning)
        return grouped


class ConversionWarningSystem:
    """Pre-conversion analysis and warning system
    
    Provides comprehensive risk assessment including:
    - Data loss analysis
    - Format compatibility checking
    - Performance impact assessment
    - Dependency validation
    - User guidance and recommendations
    """
    
    def __init__(self, registry: TypeRegistry):
        """Initialize warning system
        
        Args:
            registry: Type registry for type definitions
        """
        self.registry = registry
        self._warning_rules: Dict[tuple, List[ConversionWarning]] = {}
        self._suppressed_warnings: Set[str] = set()
        self._custom_analyzers: Dict[str, callable] = {}
        
        self._initialize_default_warnings()
        
        logger.info("ConversionWarningSystem initialized")
    
    def analyze_conversion(self, 
                         from_type: str, 
                         to_type: str,
                         element_count: int = 1,
                         sample_data: Optional[Dict[str, Any]] = None) -> WarningReport:
        """Analyze conversion and generate warning report
        
        Args:
            from_type: Source type for conversion
            to_type: Target type for conversion  
            element_count: Number of elements being converted
            sample_data: Sample element data for analysis
            
        Returns:
            WarningReport with detailed analysis
            
        Raises:
            ValueError: If types are not found in registry
        """
        logger.info(f"Analyzing conversion: {from_type} -> {to_type} ({element_count} elements)")
        
        # Validate types exist
        if not self.registry.has_type(from_type):
            raise ValueError(f"Source type '{from_type}' not found in registry")
        if not self.registry.has_type(to_type):
            raise ValueError(f"Target type '{to_type}' not found in registry")
        
        warnings = []
        
        # Get type definitions
        source_def = self.registry.get_type(from_type)
        target_def = self.registry.get_type(to_type)
        
        # Check for predefined warnings
        rule_key = (from_type, to_type)
        if rule_key in self._warning_rules:
            warnings.extend(self._warning_rules[rule_key])
        
        # Analyze schema compatibility
        schema_warnings = self._analyze_schema_compatibility(source_def, target_def)
        warnings.extend(schema_warnings)
        
        # Analyze data preservation
        data_warnings = self._analyze_data_preservation(source_def, target_def, sample_data)
        warnings.extend(data_warnings)
        
        # Analyze performance implications
        perf_warnings = self._analyze_performance_impact(from_type, to_type, element_count)
        warnings.extend(perf_warnings)
        
        # Analyze dependencies
        dep_warnings = self._analyze_dependencies(from_type, to_type)
        warnings.extend(dep_warnings)
        
        # Run custom analyzers
        for analyzer_name, analyzer_func in self._custom_analyzers.items():
            try:
                custom_warnings = analyzer_func(from_type, to_type, sample_data)
                if custom_warnings:
                    warnings.extend(custom_warnings)
            except Exception as e:
                logger.warning(f"Custom analyzer {analyzer_name} failed: {e}")
        
        # Filter suppressed warnings
        active_warnings = [w for w in warnings if w.warning_id not in self._suppressed_warnings]
        
        # Calculate overall risk and categorize warnings
        overall_risk = self._calculate_overall_risk(active_warnings)
        blocking_warnings = [w for w in active_warnings if w.is_blocking]
        suppressible_warnings = [w for w in active_warnings if w.can_suppress]
        
        # Estimate data loss percentage
        data_loss_estimate = self._estimate_data_loss(source_def, target_def, sample_data)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(active_warnings, from_type, to_type)
        
        return WarningReport(
            from_type=from_type,
            to_type=to_type,
            element_count=element_count,
            warnings=active_warnings,
            overall_risk_level=overall_risk,
            blocking_warnings=blocking_warnings,
            suppressible_warnings=suppressible_warnings,
            estimated_data_loss=data_loss_estimate,
            recommendations=recommendations
        )
    
    def register_warning_rule(self, 
                            from_type: str, 
                            to_type: str, 
                            warning: ConversionWarning) -> None:
        """Register a warning rule for specific type conversion
        
        Args:
            from_type: Source type
            to_type: Target type
            warning: Warning to register
        """
        rule_key = (from_type, to_type)
        if rule_key not in self._warning_rules:
            self._warning_rules[rule_key] = []
        self._warning_rules[rule_key].append(warning)
        
        logger.debug(f"Registered warning rule: {from_type} -> {to_type}: {warning.title}")
    
    def register_custom_analyzer(self, name: str, analyzer_func: callable) -> None:
        """Register custom warning analyzer
        
        Args:
            name: Name of the analyzer
            analyzer_func: Function that analyzes conversions and returns warnings
        """
        self._custom_analyzers[name] = analyzer_func
        logger.debug(f"Registered custom analyzer: {name}")
    
    def suppress_warning(self, warning_id: str) -> None:
        """Suppress a specific warning
        
        Args:
            warning_id: ID of warning to suppress
        """
        self._suppressed_warnings.add(warning_id)
        logger.debug(f"Suppressed warning: {warning_id}")
    
    def unsuppress_warning(self, warning_id: str) -> None:
        """Remove warning suppression
        
        Args:
            warning_id: ID of warning to unsuppress
        """
        self._suppressed_warnings.discard(warning_id)
        logger.debug(f"Unsuppressed warning: {warning_id}")
    
    def get_warning_details(self, warning_id: str) -> Optional[ConversionWarning]:
        """Get detailed information about a specific warning
        
        Args:
            warning_id: ID of warning to look up
            
        Returns:
            ConversionWarning if found, None otherwise
        """
        for warnings_list in self._warning_rules.values():
            for warning in warnings_list:
                if warning.warning_id == warning_id:
                    return warning
        return None
    
    def validate_conversion_safety(self, 
                                 from_type: str, 
                                 to_type: str,
                                 element_count: int = 1) -> bool:
        """Quick safety check for conversion
        
        Args:
            from_type: Source type
            to_type: Target type
            element_count: Number of elements
            
        Returns:
            True if conversion is considered safe, False otherwise
        """
        try:
            report = self.analyze_conversion(from_type, to_type, element_count)
            return (report.overall_risk_level in (WarningLevel.INFO, WarningLevel.LOW) and 
                   report.can_proceed and
                   report.estimated_data_loss < 0.1)  # Less than 10% data loss
        except Exception as e:
            logger.error(f"Safety validation failed: {e}")
            return False
    
    def _initialize_default_warnings(self) -> None:
        """Initialize default warning rules for common conversions"""
        
        # Text to heading conversion
        self.register_warning_rule(
            "text", "heading",
            ConversionWarning(
                warning_id="text_to_heading_formatting",
                level=WarningLevel.LOW,
                category=WarningCategory.FORMAT_CHANGE,
                title="Formatting Changes",
                message="Text formatting may be adjusted to match heading styles",
                details="Headings have specific formatting requirements that may override existing text formatting",
                suggested_actions=["Review heading styles", "Check formatting consistency"]
            )
        )
        
        # Heading to text conversion
        self.register_warning_rule(
            "heading", "text",
            ConversionWarning(
                warning_id="heading_to_text_hierarchy",
                level=WarningLevel.MEDIUM,
                category=WarningCategory.DATA_LOSS,
                title="Document Structure Loss",
                message="Converting headings to text will lose document hierarchy information",
                details="Headings provide structural information that will be lost in conversion",
                affected_fields=["level", "hierarchy_position"],
                suggested_actions=["Consider preserving heading levels", "Update document navigation"]
            )
        )
        
        # Table cell to text conversion
        self.register_warning_rule(
            "table_cell", "text",
            ConversionWarning(
                warning_id="table_cell_structure_loss",
                level=WarningLevel.HIGH,
                category=WarningCategory.DATA_LOSS,
                title="Table Structure Loss",
                message="Converting table cells to text will lose all table structure and relationships",
                details="Table structure, cell relationships, and tabular data organization will be lost",
                affected_fields=["row_index", "column_index", "table_id", "cell_type"],
                suggested_actions=["Export table data separately", "Consider paragraph conversion instead"],
                requires_confirmation=True
            )
        )
        
        # List item to paragraph conversion
        self.register_warning_rule(
            "list_item", "paragraph",
            ConversionWarning(
                warning_id="list_item_enumeration_loss",
                level=WarningLevel.MEDIUM,
                category=WarningCategory.FORMAT_CHANGE,
                title="List Structure Loss",
                message="Converting list items to paragraphs will lose list enumeration and nesting",
                details="List bullet points, numbering, and hierarchical nesting will be lost",
                affected_fields=["list_type", "nesting_level", "item_number"],
                suggested_actions=["Preserve list markers in text", "Consider keeping as list structure"]
            )
        )
        
        # Generic high-volume warning
        self.register_warning_rule(
            "*", "*",  # Wildcard for any conversion
            ConversionWarning(
                warning_id="bulk_operation_performance",
                level=WarningLevel.INFO,
                category=WarningCategory.PERFORMANCE,
                title="Bulk Operation Performance",
                message="Large bulk operations may impact system performance",
                details="Converting large numbers of elements may require significant processing time",
                suggested_actions=["Consider processing in batches", "Schedule during low-usage periods"]
            )
        )
        
        logger.debug(f"Initialized {len(self._warning_rules)} default warning rules")
    
    def _analyze_schema_compatibility(self, 
                                    source_def: TypeDefinition, 
                                    target_def: TypeDefinition) -> List[ConversionWarning]:
        """Analyze schema compatibility between types"""
        warnings = []
        
        # Mock schema analysis - in real implementation would compare actual schemas
        if source_def.category != target_def.category:
            warnings.append(ConversionWarning(
                warning_id=f"category_change_{source_def.category}_{target_def.category}",
                level=WarningLevel.LOW,
                category=WarningCategory.FORMAT_CHANGE,
                title="Category Change",
                message=f"Type category changing from {source_def.category} to {target_def.category}",
                details="Different categories may have different behavior and validation rules"
            ))
        
        return warnings
    
    def _analyze_data_preservation(self, 
                                 source_def: TypeDefinition,
                                 target_def: TypeDefinition,
                                 sample_data: Optional[Dict[str, Any]]) -> List[ConversionWarning]:
        """Analyze data preservation during conversion"""
        warnings = []
        
        if not sample_data:
            return warnings
        
        # Mock data analysis - would compare field compatibility
        source_fields = set(sample_data.keys())
        target_fields = set()  # Would get from target schema
        
        potentially_lost_fields = source_fields - target_fields
        if potentially_lost_fields:
            warnings.append(ConversionWarning(
                warning_id="potential_data_loss",
                level=WarningLevel.MEDIUM,
                category=WarningCategory.DATA_LOSS,
                title="Potential Data Loss",
                message=f"Some fields may not be preserved: {', '.join(potentially_lost_fields)}",
                affected_fields=list(potentially_lost_fields),
                suggested_actions=["Review field mappings", "Backup original data"]
            ))
        
        return warnings
    
    def _analyze_performance_impact(self, 
                                  from_type: str, 
                                  to_type: str, 
                                  element_count: int) -> List[ConversionWarning]:
        """Analyze performance implications of conversion"""
        warnings = []
        
        # Large batch warning
        if element_count > 10000:
            warnings.append(ConversionWarning(
                warning_id="large_batch_performance",
                level=WarningLevel.MEDIUM,
                category=WarningCategory.PERFORMANCE,
                title="Large Batch Operation",
                message=f"Converting {element_count} elements may take significant time",
                details="Large batch operations can impact system performance and user experience",
                suggested_actions=["Process in smaller batches", "Schedule during off-peak hours"]
            ))
        
        # Complex conversion warning
        complex_conversions = [("table", "text"), ("image", "text")]
        if (from_type, to_type) in complex_conversions:
            warnings.append(ConversionWarning(
                warning_id="complex_conversion_performance",
                level=WarningLevel.LOW,
                category=WarningCategory.PERFORMANCE,
                title="Complex Conversion",
                message="This conversion requires additional processing time",
                details="Complex type conversions involve data transformation that may be resource-intensive"
            ))
        
        return warnings
    
    def _analyze_dependencies(self, from_type: str, to_type: str) -> List[ConversionWarning]:
        """Analyze dependency impacts of conversion"""
        warnings = []
        
        # Mock dependency analysis
        dependencies = self._get_type_dependencies(from_type)
        if dependencies:
            warnings.append(ConversionWarning(
                warning_id="dependency_impact",
                level=WarningLevel.MEDIUM,
                category=WarningCategory.DEPENDENCY,
                title="Dependency Impact",
                message=f"Type {from_type} has dependencies that may be affected",
                details=f"Dependencies: {', '.join(dependencies)}",
                suggested_actions=["Review dependent elements", "Update references"]
            ))
        
        return warnings
    
    def _calculate_overall_risk(self, warnings: List[ConversionWarning]) -> WarningLevel:
        """Calculate overall risk level from warnings"""
        if not warnings:
            return WarningLevel.INFO
        
        # Get highest warning level
        max_level = max(warnings, key=lambda w: self._warning_level_priority(w.level))
        return max_level.level
    
    def _warning_level_priority(self, level: WarningLevel) -> int:
        """Get numeric priority for warning level"""
        priorities = {
            WarningLevel.INFO: 1,
            WarningLevel.LOW: 2,
            WarningLevel.MEDIUM: 3,
            WarningLevel.HIGH: 4,
            WarningLevel.CRITICAL: 5
        }
        return priorities.get(level, 0)
    
    def _estimate_data_loss(self, 
                          source_def: TypeDefinition,
                          target_def: TypeDefinition,
                          sample_data: Optional[Dict[str, Any]]) -> float:
        """Estimate percentage of data that may be lost"""
        if not sample_data:
            return 0.0
        
        # Mock estimation - would analyze field mappings
        total_fields = len(sample_data)
        if total_fields == 0:
            return 0.0
        
        # Simple heuristic: assume some data loss for cross-category conversions
        if source_def.category != target_def.category:
            return 0.2  # 20% estimated loss
        
        return 0.05  # 5% estimated loss for same-category conversions
    
    def _generate_recommendations(self, 
                                warnings: List[ConversionWarning],
                                from_type: str,
                                to_type: str) -> List[str]:
        """Generate recommendations based on warnings"""
        recommendations = []
        
        # Collect suggestions from warnings
        for warning in warnings:
            recommendations.extend(warning.suggested_actions)
        
        # Add general recommendations
        if any(w.category == WarningCategory.DATA_LOSS for w in warnings):
            recommendations.append("Create backup before proceeding with conversion")
        
        if any(w.level in (WarningLevel.HIGH, WarningLevel.CRITICAL) for w in warnings):
            recommendations.append("Review all warnings carefully before proceeding")
        
        # Remove duplicates and return
        return list(dict.fromkeys(recommendations))
    
    def _get_type_dependencies(self, type_id: str) -> List[str]:
        """Get dependencies for a type (mock)"""
        # Mock implementation - would query actual dependencies
        mock_dependencies = {
            "table_cell": ["table", "table_row"],
            "list_item": ["list"],
            "heading": ["document_structure"]
        }
        return mock_dependencies.get(type_id, [])