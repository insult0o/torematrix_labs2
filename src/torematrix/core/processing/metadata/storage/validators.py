"""Relationship validation for ensuring graph consistency.

This module provides validation capabilities for relationships to ensure
graph consistency, detect conflicts, and maintain data quality.
"""

import logging
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum

from ..models.relationship import Relationship, RelationshipType
from ..graph import ElementRelationshipGraph
from ....models.element import Element as UnifiedElement

logger = logging.getLogger(__name__)


class ValidationLevel(str, Enum):
    """Validation strictness levels."""
    STRICT = "strict"
    MODERATE = "moderate"
    LENIENT = "lenient"


class ValidationIssueType(str, Enum):
    """Types of validation issues."""
    MISSING_ELEMENT = "missing_element"
    DUPLICATE_RELATIONSHIP = "duplicate_relationship"
    CONFLICTING_RELATIONSHIP = "conflicting_relationship"
    INVALID_CONFIDENCE = "invalid_confidence"
    CYCLIC_HIERARCHY = "cyclic_hierarchy"
    SPATIAL_INCONSISTENCY = "spatial_inconsistency"
    LOGICAL_INCONSISTENCY = "logical_inconsistency"
    ORPHANED_ELEMENT = "orphaned_element"
    BROKEN_CHAIN = "broken_chain"


@dataclass
class ValidationIssue:
    """Represents a validation issue."""
    issue_type: ValidationIssueType
    severity: str  # "error", "warning", "info"
    message: str
    affected_elements: List[str]
    affected_relationships: List[str]
    metadata: Dict[str, Any]


@dataclass
class ValidationResult:
    """Result of relationship validation."""
    is_valid: bool
    issues: List[ValidationIssue]
    statistics: Dict[str, Any]
    suggestions: List[str]
    
    @property
    def error_count(self) -> int:
        """Get number of error-level issues."""
        return len([i for i in self.issues if i.severity == "error"])
    
    @property
    def warning_count(self) -> int:
        """Get number of warning-level issues."""
        return len([i for i in self.issues if i.severity == "warning"])


class RelationshipValidator:
    """Validator for relationship graphs."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        """Initialize relationship validator.
        
        Args:
            validation_level: Strictness level for validation
        """
        self.validation_level = validation_level
        self.conflict_rules = self._init_conflict_rules()
        self.logical_rules = self._init_logical_rules()
    
    def validate_graph(
        self, 
        graph: ElementRelationshipGraph,
        elements: Optional[List[UnifiedElement]] = None
    ) -> ValidationResult:
        """Validate complete relationship graph.
        
        Args:
            graph: Relationship graph to validate
            elements: Optional list of elements for cross-validation
            
        Returns:
            Validation result with issues and suggestions
        """
        logger.info(f"Validating graph with {len(graph)} elements")
        
        issues = []
        
        # Basic structure validation
        issues.extend(self._validate_structure(graph, elements))
        
        # Relationship consistency validation
        issues.extend(self._validate_relationship_consistency(graph))
        
        # Spatial consistency validation
        issues.extend(self._validate_spatial_consistency(graph))
        
        # Logical consistency validation
        issues.extend(self._validate_logical_consistency(graph))
        
        # Hierarchy validation
        issues.extend(self._validate_hierarchy(graph))
        
        # Duplicate detection
        issues.extend(self._detect_duplicates(graph))
        
        # Orphan detection
        issues.extend(self._detect_orphans(graph))
        
        # Generate statistics
        statistics = self._generate_statistics(graph, issues)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(issues)
        
        # Determine overall validity
        error_count = len([i for i in issues if i.severity == "error"])
        is_valid = error_count == 0
        
        result = ValidationResult(
            is_valid=is_valid,
            issues=issues,
            statistics=statistics,
            suggestions=suggestions
        )
        
        logger.info(f"Validation completed: {len(issues)} issues found ({error_count} errors)")
        return result
    
    def validate_relationship(
        self, 
        relationship: Relationship,
        graph: ElementRelationshipGraph
    ) -> List[ValidationIssue]:
        """Validate a single relationship.
        
        Args:
            relationship: Relationship to validate
            graph: Graph context
            
        Returns:
            List of validation issues
        """
        issues = []
        
        # Check if elements exist
        if relationship.source_id not in graph:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.MISSING_ELEMENT,
                severity="error",
                message=f"Source element {relationship.source_id} not found in graph",
                affected_elements=[relationship.source_id],
                affected_relationships=[relationship.id],
                metadata={}
            ))
        
        if relationship.target_id not in graph:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.MISSING_ELEMENT,
                severity="error",
                message=f"Target element {relationship.target_id} not found in graph",
                affected_elements=[relationship.target_id],
                affected_relationships=[relationship.id],
                metadata={}
            ))
        
        # Validate confidence score
        if not 0.0 <= relationship.confidence <= 1.0:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.INVALID_CONFIDENCE,
                severity="error",
                message=f"Invalid confidence score: {relationship.confidence}",
                affected_elements=[],
                affected_relationships=[relationship.id],
                metadata={"confidence": relationship.confidence}
            ))
        
        # Check for self-relationships
        if relationship.source_id == relationship.target_id:
            severity = "warning" if self.validation_level == ValidationLevel.LENIENT else "error"
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.LOGICAL_INCONSISTENCY,
                severity=severity,
                message=f"Self-relationship detected: {relationship.source_id}",
                affected_elements=[relationship.source_id],
                affected_relationships=[relationship.id],
                metadata={}
            ))
        
        return issues
    
    def _validate_structure(
        self, 
        graph: ElementRelationshipGraph,
        elements: Optional[List[UnifiedElement]]
    ) -> List[ValidationIssue]:
        """Validate basic graph structure."""
        issues = []
        
        # Check if all elements in relationships exist in graph
        for _, _, edge_data in graph.graph.edges(data=True):
            if 'relationship' in edge_data:
                rel = edge_data['relationship']
                issues.extend(self.validate_relationship(rel, graph))
        
        # Cross-validate with provided elements if available
        if elements:
            element_ids = {e.id for e in elements}
            graph_element_ids = set(graph.element_index.keys())
            
            # Check for missing elements
            missing_in_graph = element_ids - graph_element_ids
            if missing_in_graph:
                issues.append(ValidationIssue(
                    issue_type=ValidationIssueType.MISSING_ELEMENT,
                    severity="warning",
                    message=f"Elements missing in graph: {list(missing_in_graph)[:5]}...",
                    affected_elements=list(missing_in_graph),
                    affected_relationships=[],
                    metadata={"count": len(missing_in_graph)}
                ))
            
            # Check for extra elements
            extra_in_graph = graph_element_ids - element_ids
            if extra_in_graph:
                issues.append(ValidationIssue(
                    issue_type=ValidationIssueType.ORPHANED_ELEMENT,
                    severity="info",
                    message=f"Extra elements in graph: {list(extra_in_graph)[:5]}...",
                    affected_elements=list(extra_in_graph),
                    affected_relationships=[],
                    metadata={"count": len(extra_in_graph)}
                ))
        
        return issues
    
    def _validate_relationship_consistency(
        self, 
        graph: ElementRelationshipGraph
    ) -> List[ValidationIssue]:
        """Validate relationship consistency."""
        issues = []
        
        # Check for conflicting relationships
        for element_id in graph.element_index.keys():
            outgoing_rels = graph.get_outgoing_relationships(element_id)
            
            # Check for conflicts based on rules
            for rel1 in outgoing_rels:
                for rel2 in outgoing_rels:
                    if rel1.id != rel2.id and rel1.target_id == rel2.target_id:
                        conflict = self._check_relationship_conflict(rel1, rel2)
                        if conflict:
                            issues.append(ValidationIssue(
                                issue_type=ValidationIssueType.CONFLICTING_RELATIONSHIP,
                                severity="warning",
                                message=f"Conflicting relationships: {rel1.relationship_type} vs {rel2.relationship_type}",
                                affected_elements=[element_id, rel1.target_id],
                                affected_relationships=[rel1.id, rel2.id],
                                metadata={"conflict_reason": conflict}
                            ))
        
        return issues
    
    def _validate_spatial_consistency(
        self, 
        graph: ElementRelationshipGraph
    ) -> List[ValidationIssue]:
        """Validate spatial relationship consistency."""
        issues = []
        
        spatial_relationships = graph.filter_by_relationship_type(RelationshipType.SPATIAL_CONTAINS)
        
        for rel_id in spatial_relationships.graph.edges():
            # Get the relationship
            edge_data = spatial_relationships.graph.get_edge_data(rel_id[0], rel_id[1])
            if not edge_data:
                continue
            
            for edge_key, data in edge_data.items():
                if 'relationship' in data:
                    rel = data['relationship']
                    
                    # Validate spatial containment
                    if rel.relationship_type == RelationshipType.SPATIAL_CONTAINS:
                        source_elem = graph.get_element(rel.source_id)
                        target_elem = graph.get_element(rel.target_id)
                        
                        if source_elem and target_elem:
                            spatial_issue = self._validate_spatial_containment(source_elem, target_elem)
                            if spatial_issue:
                                issues.append(spatial_issue)
        
        return issues
    
    def _validate_logical_consistency(
        self, 
        graph: ElementRelationshipGraph
    ) -> List[ValidationIssue]:
        """Validate logical consistency using rules."""
        issues = []
        
        for rule in self.logical_rules:
            rule_issues = rule(graph)
            issues.extend(rule_issues)
        
        return issues
    
    def _validate_hierarchy(
        self, 
        graph: ElementRelationshipGraph
    ) -> List[ValidationIssue]:
        """Validate hierarchical relationships for cycles."""
        issues = []
        
        # Extract hierarchical relationships
        hierarchical_graph = graph.filter_by_relationship_type(RelationshipType.PARENT_CHILD)
        
        # Check for cycles
        try:
            cycles = list(nx.simple_cycles(hierarchical_graph.graph))
            if cycles:
                for cycle in cycles:
                    issues.append(ValidationIssue(
                        issue_type=ValidationIssueType.CYCLIC_HIERARCHY,
                        severity="error",
                        message=f"Cyclic hierarchy detected: {' -> '.join(cycle)}",
                        affected_elements=cycle,
                        affected_relationships=[],
                        metadata={"cycle_length": len(cycle)}
                    ))
        except Exception as e:
            logger.warning(f"Error checking for cycles: {e}")
        
        return issues
    
    def _detect_duplicates(
        self, 
        graph: ElementRelationshipGraph
    ) -> List[ValidationIssue]:
        """Detect duplicate relationships."""
        issues = []
        
        # Group relationships by source-target-type
        relationship_groups = {}
        
        for _, _, edge_data in graph.graph.edges(data=True):
            if 'relationship' in edge_data:
                rel = edge_data['relationship']
                key = (rel.source_id, rel.target_id, rel.relationship_type)
                
                if key not in relationship_groups:
                    relationship_groups[key] = []
                relationship_groups[key].append(rel)
        
        # Find groups with multiple relationships
        for key, rels in relationship_groups.items():
            if len(rels) > 1:
                issues.append(ValidationIssue(
                    issue_type=ValidationIssueType.DUPLICATE_RELATIONSHIP,
                    severity="warning",
                    message=f"Duplicate relationships found: {key[2]} between {key[0]} and {key[1]}",
                    affected_elements=[key[0], key[1]],
                    affected_relationships=[r.id for r in rels],
                    metadata={"duplicate_count": len(rels)}
                ))
        
        return issues
    
    def _detect_orphans(
        self, 
        graph: ElementRelationshipGraph
    ) -> List[ValidationIssue]:
        """Detect orphaned elements with no relationships."""
        issues = []
        
        orphaned_elements = []
        
        for element_id in graph.element_index.keys():
            relationships = graph.get_relationships(element_id)
            if not relationships:
                orphaned_elements.append(element_id)
        
        if orphaned_elements:
            severity = "info" if self.validation_level == ValidationLevel.LENIENT else "warning"
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.ORPHANED_ELEMENT,
                severity=severity,
                message=f"Found {len(orphaned_elements)} orphaned elements",
                affected_elements=orphaned_elements,
                affected_relationships=[],
                metadata={"count": len(orphaned_elements)}
            ))
        
        return issues
    
    def _init_conflict_rules(self) -> Dict:
        """Initialize relationship conflict rules."""
        return {
            # Spatial conflicts
            (RelationshipType.SPATIAL_CONTAINS, RelationshipType.SPATIAL_OVERLAPS): "Contains and overlaps are mutually exclusive",
            
            # Hierarchy conflicts
            (RelationshipType.PARENT_CHILD, RelationshipType.SIBLING): "Cannot be both parent-child and sibling",
        }
    
    def _init_logical_rules(self) -> List:
        """Initialize logical consistency rules."""
        return [
            self._rule_reading_order_consistency,
            self._rule_caption_target_consistency,
            self._rule_spatial_transitivity,
        ]
    
    def _check_relationship_conflict(
        self, 
        rel1: Relationship, 
        rel2: Relationship
    ) -> Optional[str]:
        """Check if two relationships conflict."""
        conflict_key = (rel1.relationship_type, rel2.relationship_type)
        reverse_key = (rel2.relationship_type, rel1.relationship_type)
        
        return self.conflict_rules.get(conflict_key) or self.conflict_rules.get(reverse_key)
    
    def _validate_spatial_containment(
        self, 
        source_elem: UnifiedElement, 
        target_elem: UnifiedElement
    ) -> Optional[ValidationIssue]:
        """Validate spatial containment relationship."""
        # Check if source actually contains target spatially
        if not (source_elem.metadata and target_elem.metadata):
            return None
        
        source_coords = source_elem.metadata.coordinates
        target_coords = target_elem.metadata.coordinates
        
        if not (source_coords and target_coords):
            return None
        
        source_bbox = source_coords.layout_bbox
        target_bbox = target_coords.layout_bbox
        
        if not (source_bbox and target_bbox and len(source_bbox) >= 4 and len(target_bbox) >= 4):
            return None
        
        # Check if source actually contains target
        contains = (
            source_bbox[0] <= target_bbox[0] and
            source_bbox[1] <= target_bbox[1] and
            source_bbox[2] >= target_bbox[2] and
            source_bbox[3] >= target_bbox[3]
        )
        
        if not contains:
            return ValidationIssue(
                issue_type=ValidationIssueType.SPATIAL_INCONSISTENCY,
                severity="warning",
                message=f"Spatial containment mismatch: {source_elem.id} does not contain {target_elem.id}",
                affected_elements=[source_elem.id, target_elem.id],
                affected_relationships=[],
                metadata={
                    "source_bbox": source_bbox,
                    "target_bbox": target_bbox
                }
            )
        
        return None
    
    def _rule_reading_order_consistency(self, graph: ElementRelationshipGraph) -> List[ValidationIssue]:
        """Check reading order consistency."""
        issues = []
        
        reading_order_rels = graph.filter_by_relationship_type(RelationshipType.READING_ORDER)
        
        # Check for broken chains in reading order
        # This is a simplified check - full implementation would be more complex
        
        return issues
    
    def _rule_caption_target_consistency(self, graph: ElementRelationshipGraph) -> List[ValidationIssue]:
        """Check caption-target relationship consistency."""
        issues = []
        
        caption_rels = graph.filter_by_relationship_type(RelationshipType.CAPTION_TARGET)
        
        for _, _, edge_data in caption_rels.graph.edges(data=True):
            if 'relationship' in edge_data:
                rel = edge_data['relationship']
                
                # Check if caption element is appropriate for target
                caption_elem = graph.get_element(rel.source_id)
                target_elem = graph.get_element(rel.target_id)
                
                if caption_elem and target_elem:
                    if target_elem.type not in ['Figure', 'Image', 'Table', 'Chart']:
                        issues.append(ValidationIssue(
                            issue_type=ValidationIssueType.LOGICAL_INCONSISTENCY,
                            severity="warning",
                            message=f"Caption relationship to non-captionable element: {target_elem.type}",
                            affected_elements=[rel.source_id, rel.target_id],
                            affected_relationships=[rel.id],
                            metadata={"target_type": target_elem.type}
                        ))
        
        return issues
    
    def _rule_spatial_transitivity(self, graph: ElementRelationshipGraph) -> List[ValidationIssue]:
        """Check spatial transitivity rules."""
        issues = []
        
        # Check containment transitivity: if A contains B and B contains C, then A should contain C
        containment_rels = graph.filter_by_relationship_type(RelationshipType.SPATIAL_CONTAINS)
        
        # This would require more complex graph traversal - simplified for now
        
        return issues
    
    def _generate_statistics(
        self, 
        graph: ElementRelationshipGraph, 
        issues: List[ValidationIssue]
    ) -> Dict[str, Any]:
        """Generate validation statistics."""
        return {
            "total_elements": len(graph.element_index),
            "total_relationships": graph.graph.number_of_edges(),
            "total_issues": len(issues),
            "errors": len([i for i in issues if i.severity == "error"]),
            "warnings": len([i for i in issues if i.severity == "warning"]),
            "info": len([i for i in issues if i.severity == "info"]),
            "issue_types": {
                issue_type.value: len([i for i in issues if i.issue_type == issue_type])
                for issue_type in ValidationIssueType
            }
        }
    
    def _generate_suggestions(self, issues: List[ValidationIssue]) -> List[str]:
        """Generate suggestions for fixing issues."""
        suggestions = []
        
        error_count = len([i for i in issues if i.severity == "error"])
        warning_count = len([i for i in issues if i.severity == "warning"])
        
        if error_count > 0:
            suggestions.append(f"Fix {error_count} critical errors before proceeding")
        
        if warning_count > 5:
            suggestions.append("Consider reviewing relationship detection algorithms")
        
        # Type-specific suggestions
        issue_type_counts = {}
        for issue in issues:
            issue_type_counts[issue.issue_type] = issue_type_counts.get(issue.issue_type, 0) + 1
        
        if issue_type_counts.get(ValidationIssueType.DUPLICATE_RELATIONSHIP, 0) > 3:
            suggestions.append("Consider implementing duplicate relationship merging")
        
        if issue_type_counts.get(ValidationIssueType.SPATIAL_INCONSISTENCY, 0) > 5:
            suggestions.append("Review spatial relationship detection accuracy")
        
        if issue_type_counts.get(ValidationIssueType.ORPHANED_ELEMENT, 0) > 10:
            suggestions.append("Consider adjusting relationship detection thresholds")
        
        return suggestions