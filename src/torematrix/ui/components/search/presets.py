"""
Quick Filter Presets and Templates

Provides predefined filter sets for common search operations and
customizable templates for power users.
"""

from typing import Dict, List, Set, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from ....core.models.element import ElementType
from .filters import (
    FilterManager, FilterSet, FilterGroup, FilterCondition,
    FilterType, FilterOperator, FilterLogic, FilterValue
)


class PresetCategory(Enum):
    """Categories for organizing presets."""
    QUALITY = "quality"
    CONTENT_TYPE = "content_type"
    LOCATION = "location"
    METADATA = "metadata"
    ANALYSIS = "analysis"
    WORKFLOW = "workflow"
    CUSTOM = "custom"


@dataclass
class PresetTemplate:
    """Template for creating filter presets."""
    preset_id: str
    name: str
    description: str
    category: PresetCategory
    filter_set: FilterSet
    icon: str = "filter"
    keywords: List[str] = field(default_factory=list)
    difficulty: str = "beginner"  # beginner, intermediate, advanced
    use_count: int = 0
    
    def clone(self, new_name: str) -> 'PresetTemplate':
        """Create a clone of this preset with a new name."""
        cloned_data = self.filter_set.to_dict()
        cloned_data['name'] = new_name
        cloned_data['filter_set_id'] = f"{self.preset_id}_clone"
        
        cloned_filter_set = FilterSet.from_dict(cloned_data)
        
        return PresetTemplate(
            preset_id=f"{self.preset_id}_clone",
            name=new_name,
            description=f"Copy of {self.name}",
            category=self.category,
            filter_set=cloned_filter_set,
            icon=self.icon,
            keywords=self.keywords.copy(),
            difficulty=self.difficulty
        )


class PresetManager:
    """Manages filter presets and templates."""
    
    def __init__(self):
        self.presets: Dict[str, PresetTemplate] = {}
        self.categories: Dict[PresetCategory, List[str]] = {}
        self._initialize_default_presets()
    
    def _initialize_default_presets(self) -> None:
        """Initialize default filter presets."""
        
        # Quality-based presets
        self._create_quality_presets()
        
        # Content type presets
        self._create_content_type_presets()
        
        # Location-based presets
        self._create_location_presets()
        
        # Metadata presets
        self._create_metadata_presets()
        
        # Analysis presets
        self._create_analysis_presets()
        
        # Workflow presets
        self._create_workflow_presets()
    
    def _create_quality_presets(self) -> None:
        """Create quality-based filter presets."""
        
        # High Quality Elements
        high_quality = FilterSet(
            name="High Quality Elements",
            description="Elements with confidence > 0.9",
            is_preset=True,
            tags=["quality", "confidence"]
        )
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.GREATER_THAN,
            value=FilterValue(0.9, "number")
        ))
        high_quality.add_group(group)
        
        self.add_preset(PresetTemplate(
            preset_id="high_quality",
            name="High Quality Elements",
            description="Find elements with very high confidence scores (>0.9)",
            category=PresetCategory.QUALITY,
            filter_set=high_quality,
            icon="star",
            keywords=["quality", "confidence", "high", "accurate"],
            difficulty="beginner"
        ))
        
        # Medium Quality Elements
        medium_quality = FilterSet(
            name="Medium Quality Elements",
            description="Elements with confidence 0.6-0.9",
            is_preset=True,
            tags=["quality", "confidence"]
        )
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.BETWEEN,
            value=FilterValue([0.6, 0.9], "list")
        ))
        medium_quality.add_group(group)
        
        self.add_preset(PresetTemplate(
            preset_id="medium_quality",
            name="Medium Quality Elements",
            description="Find elements with moderate confidence scores (0.6-0.9)",
            category=PresetCategory.QUALITY,
            filter_set=medium_quality,
            icon="info",
            keywords=["quality", "confidence", "medium", "moderate"],
            difficulty="beginner"
        ))
        
        # Low Quality Elements (for review)
        low_quality = FilterSet(
            name="Low Quality Elements",
            description="Elements with confidence < 0.6 (need review)",
            is_preset=True,
            tags=["quality", "confidence", "review"]
        )
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.LESS_THAN,
            value=FilterValue(0.6, "number")
        ))
        low_quality.add_group(group)
        
        self.add_preset(PresetTemplate(
            preset_id="low_quality",
            name="Low Quality Elements",
            description="Find elements that may need manual review (<0.6 confidence)",
            category=PresetCategory.QUALITY,
            filter_set=low_quality,
            icon="warning",
            keywords=["quality", "confidence", "low", "review", "check"],
            difficulty="beginner"
        ))
    
    def _create_content_type_presets(self) -> None:
        """Create content type-based presets."""
        
        # Text Content Only
        text_only = FilterSet(
            name="Text Content Only",
            description="All text-based elements",
            is_preset=True,
            tags=["text", "content"]
        )
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.ELEMENT_TYPE,
            operator=FilterOperator.IN,
            value=FilterValue([
                ElementType.NARRATIVE_TEXT.value,
                ElementType.TEXT.value,
                ElementType.TITLE.value,
                ElementType.HEADER.value
            ], "list")
        ))
        text_only.add_group(group)
        
        self.add_preset(PresetTemplate(
            preset_id="text_only",
            name="Text Content Only",
            description="Find all text-based elements (titles, headers, narrative text)",
            category=PresetCategory.CONTENT_TYPE,
            filter_set=text_only,
            icon="text",
            keywords=["text", "content", "narrative", "title", "header"],
            difficulty="beginner"
        ))
        
        # Structural Elements
        structural = FilterSet(
            name="Structural Elements",
            description="Tables, lists, and other structural elements",
            is_preset=True,
            tags=["structure", "table", "list"]
        )
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.ELEMENT_TYPE,
            operator=FilterOperator.IN,
            value=FilterValue([
                ElementType.TABLE.value,
                ElementType.LIST.value,
                ElementType.LIST_ITEM.value
            ], "list")
        ))
        structural.add_group(group)
        
        self.add_preset(PresetTemplate(
            preset_id="structural",
            name="Structural Elements",
            description="Find tables, lists, and other structural document elements",
            category=PresetCategory.CONTENT_TYPE,
            filter_set=structural,
            icon="table",
            keywords=["structure", "table", "list", "data", "organized"],
            difficulty="beginner"
        ))
        
        # Media Elements
        media = FilterSet(
            name="Media Elements",
            description="Images, figures, and formulas",
            is_preset=True,
            tags=["media", "image", "figure"]
        )
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.ELEMENT_TYPE,
            operator=FilterOperator.IN,
            value=FilterValue([
                ElementType.IMAGE.value,
                ElementType.FIGURE.value,
                ElementType.FIGURE_CAPTION.value,
                ElementType.FORMULA.value
            ], "list")
        ))
        media.add_group(group)
        
        self.add_preset(PresetTemplate(
            preset_id="media",
            name="Media Elements",
            description="Find images, figures, formulas, and related captions",
            category=PresetCategory.CONTENT_TYPE,
            filter_set=media,
            icon="image",
            keywords=["media", "image", "figure", "formula", "visual"],
            difficulty="beginner"
        ))
    
    def _create_location_presets(self) -> None:
        """Create location-based presets."""
        
        # First Pages
        first_pages = FilterSet(
            name="First Pages",
            description="Elements from the first 3 pages",
            is_preset=True,
            tags=["location", "page", "beginning"]
        )
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.PAGE_NUMBER,
            operator=FilterOperator.BETWEEN,
            value=FilterValue([1, 3], "list")
        ))
        first_pages.add_group(group)
        
        self.add_preset(PresetTemplate(
            preset_id="first_pages",
            name="First Pages",
            description="Find elements from the beginning of the document (pages 1-3)",
            category=PresetCategory.LOCATION,
            filter_set=first_pages,
            icon="page",
            keywords=["page", "first", "beginning", "start", "intro"],
            difficulty="beginner"
        ))
        
        # Last Pages
        last_pages = FilterSet(
            name="Last Pages",
            description="Elements from pages 90+",
            is_preset=True,
            tags=["location", "page", "end"]
        )
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.PAGE_NUMBER,
            operator=FilterOperator.GREATER_THAN,
            value=FilterValue(90, "number")
        ))
        last_pages.add_group(group)
        
        self.add_preset(PresetTemplate(
            preset_id="last_pages",
            name="Last Pages",
            description="Find elements from the end of the document (page 90+)",
            category=PresetCategory.LOCATION,
            filter_set=last_pages,
            icon="page-end",
            keywords=["page", "last", "end", "conclusion", "appendix"],
            difficulty="beginner"
        ))
        
        # Single Page
        page_template = FilterSet(
            name="Single Page Template",
            description="Template for filtering by specific page",
            is_preset=True,
            tags=["location", "page", "specific"]
        )
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.PAGE_NUMBER,
            operator=FilterOperator.EQUALS,
            value=FilterValue(1, "number")  # Default to page 1
        ))
        page_template.add_group(group)
        
        self.add_preset(PresetTemplate(
            preset_id="single_page_template",
            name="Single Page Template",
            description="Template for finding elements from a specific page (customize page number)",
            category=PresetCategory.LOCATION,
            filter_set=page_template,
            icon="page-single",
            keywords=["page", "specific", "single", "custom"],
            difficulty="intermediate"
        ))
    
    def _create_metadata_presets(self) -> None:
        """Create metadata-based presets."""
        
        # ML Detected
        ml_detected = FilterSet(
            name="ML Detected",
            description="Elements detected by machine learning",
            is_preset=True,
            tags=["metadata", "detection", "ml"]
        )
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.DETECTION_METHOD,
            operator=FilterOperator.CONTAINS,
            value=FilterValue("ml", "string")
        ))
        ml_detected.add_group(group)
        
        self.add_preset(PresetTemplate(
            preset_id="ml_detected",
            name="ML Detected Elements",
            description="Find elements that were detected using machine learning methods",
            category=PresetCategory.METADATA,
            filter_set=ml_detected,
            icon="brain",
            keywords=["ml", "machine", "learning", "ai", "detection"],
            difficulty="intermediate"
        ))
        
        # Rule-based Detection
        rule_based = FilterSet(
            name="Rule-based Detection",
            description="Elements detected by rules",
            is_preset=True,
            tags=["metadata", "detection", "rules"]
        )
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.DETECTION_METHOD,
            operator=FilterOperator.CONTAINS,
            value=FilterValue("rule", "string")
        ))
        rule_based.add_group(group)
        
        self.add_preset(PresetTemplate(
            preset_id="rule_based",
            name="Rule-based Detection",
            description="Find elements detected using rule-based methods",
            category=PresetCategory.METADATA,
            filter_set=rule_based,
            icon="rules",
            keywords=["rule", "rules", "pattern", "heuristic", "detection"],
            difficulty="intermediate"
        ))
    
    def _create_analysis_presets(self) -> None:
        """Create analysis-oriented presets."""
        
        # Content Analysis
        content_analysis = FilterSet(
            name="Content Analysis",
            description="Text elements with good quality for analysis",
            is_preset=True,
            tags=["analysis", "content", "text"]
        )
        
        # Group 1: Text elements
        text_group = FilterGroup()
        text_group.add_condition(FilterCondition(
            filter_type=FilterType.ELEMENT_TYPE,
            operator=FilterOperator.IN,
            value=FilterValue([
                ElementType.NARRATIVE_TEXT.value,
                ElementType.TEXT.value
            ], "list")
        ))
        content_analysis.add_group(text_group)
        
        # Group 2: Good quality
        quality_group = FilterGroup()
        quality_group.add_condition(FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.GREATER_THAN,
            value=FilterValue(0.7, "number")
        ))
        content_analysis.add_group(quality_group)
        
        content_analysis.combination_logic = FilterLogic.AND
        
        self.add_preset(PresetTemplate(
            preset_id="content_analysis",
            name="Content Analysis Ready",
            description="High-quality text elements suitable for content analysis",
            category=PresetCategory.ANALYSIS,
            filter_set=content_analysis,
            icon="chart",
            keywords=["analysis", "content", "text", "quality", "research"],
            difficulty="intermediate"
        ))
        
        # Data Extraction
        data_extraction = FilterSet(
            name="Data Extraction",
            description="Structured elements for data extraction",
            is_preset=True,
            tags=["analysis", "data", "extraction"]
        )
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.ELEMENT_TYPE,
            operator=FilterOperator.IN,
            value=FilterValue([
                ElementType.TABLE.value,
                ElementType.LIST.value,
                ElementType.LIST_ITEM.value
            ], "list")
        ))
        group.add_condition(FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.GREATER_THAN,
            value=FilterValue(0.8, "number")
        ))
        data_extraction.add_group(group)
        
        self.add_preset(PresetTemplate(
            preset_id="data_extraction",
            name="Data Extraction Ready",
            description="High-confidence structured elements ready for data extraction",
            category=PresetCategory.ANALYSIS,
            filter_set=data_extraction,
            icon="database",
            keywords=["data", "extraction", "table", "list", "structured"],
            difficulty="intermediate"
        ))
    
    def _create_workflow_presets(self) -> None:
        """Create workflow-oriented presets."""
        
        # Review Required
        review_required = FilterSet(
            name="Review Required",
            description="Elements that need manual review",
            is_preset=True,
            tags=["workflow", "review", "manual"]
        )
        
        # Group 1: Low confidence OR
        low_conf_group = FilterGroup(logic=FilterLogic.OR)
        low_conf_group.add_condition(FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.LESS_THAN,
            value=FilterValue(0.6, "number")
        ))
        # Complex elements that often need review
        low_conf_group.add_condition(FilterCondition(
            filter_type=FilterType.ELEMENT_TYPE,
            operator=FilterOperator.IN,
            value=FilterValue([
                ElementType.TABLE.value,
                ElementType.FORMULA.value
            ], "list")
        ))
        review_required.add_group(low_conf_group)
        
        self.add_preset(PresetTemplate(
            preset_id="review_required",
            name="Review Required",
            description="Elements that typically need manual review and validation",
            category=PresetCategory.WORKFLOW,
            filter_set=review_required,
            icon="eye",
            keywords=["review", "manual", "check", "validate", "verify"],
            difficulty="beginner"
        ))
        
        # Processing Complete
        processing_complete = FilterSet(
            name="Processing Complete",
            description="High-quality elements ready for export",
            is_preset=True,
            tags=["workflow", "complete", "export"]
        )
        group = FilterGroup()
        group.add_condition(FilterCondition(
            filter_type=FilterType.CONFIDENCE,
            operator=FilterOperator.GREATER_EQUAL,
            value=FilterValue(0.85, "number")
        ))
        processing_complete.add_group(group)
        
        self.add_preset(PresetTemplate(
            preset_id="processing_complete",
            name="Processing Complete",
            description="High-quality elements that are ready for export or further processing",
            category=PresetCategory.WORKFLOW,
            filter_set=processing_complete,
            icon="check",
            keywords=["complete", "ready", "export", "finished", "quality"],
            difficulty="beginner"
        ))
    
    def add_preset(self, preset: PresetTemplate) -> None:
        """Add a preset to the manager."""
        self.presets[preset.preset_id] = preset
        
        # Add to category index
        if preset.category not in self.categories:
            self.categories[preset.category] = []
        self.categories[preset.category].append(preset.preset_id)
    
    def get_preset(self, preset_id: str) -> Optional[PresetTemplate]:
        """Get a preset by ID."""
        return self.presets.get(preset_id)
    
    def list_presets(self, category: Optional[PresetCategory] = None) -> List[PresetTemplate]:
        """List presets, optionally filtered by category."""
        if category:
            preset_ids = self.categories.get(category, [])
            return [self.presets[pid] for pid in preset_ids if pid in self.presets]
        else:
            return list(self.presets.values())
    
    def search_presets(self, query: str) -> List[PresetTemplate]:
        """Search presets by name, description, or keywords."""
        query_lower = query.lower()
        results = []
        
        for preset in self.presets.values():
            # Check name and description
            if (query_lower in preset.name.lower() or 
                query_lower in preset.description.lower()):
                results.append(preset)
                continue
            
            # Check keywords
            if any(query_lower in keyword.lower() for keyword in preset.keywords):
                results.append(preset)
        
        return results
    
    def get_popular_presets(self, limit: int = 5) -> List[PresetTemplate]:
        """Get most popular presets by use count."""
        return sorted(self.presets.values(), key=lambda p: p.use_count, reverse=True)[:limit]
    
    def increment_use_count(self, preset_id: str) -> None:
        """Increment use count for a preset."""
        if preset_id in self.presets:
            self.presets[preset_id].use_count += 1
    
    def create_custom_preset(self, name: str, description: str, filter_set: FilterSet,
                           keywords: List[str] = None) -> PresetTemplate:
        """Create a custom preset from a filter set."""
        preset_id = f"custom_{name.lower().replace(' ', '_')}"
        
        preset = PresetTemplate(
            preset_id=preset_id,
            name=name,
            description=description,
            category=PresetCategory.CUSTOM,
            filter_set=filter_set,
            icon="custom",
            keywords=keywords or [],
            difficulty="custom"
        )
        
        self.add_preset(preset)
        return preset
    
    def delete_preset(self, preset_id: str) -> bool:
        """Delete a custom preset."""
        preset = self.presets.get(preset_id)
        if not preset or preset.category != PresetCategory.CUSTOM:
            return False
        
        del self.presets[preset_id]
        
        # Remove from category index
        if (preset.category in self.categories and 
            preset_id in self.categories[preset.category]):
            self.categories[preset.category].remove(preset_id)
        
        return True
    
    def export_preset(self, preset_id: str) -> Optional[str]:
        """Export a preset to JSON string."""
        preset = self.get_preset(preset_id)
        if not preset:
            return None
        
        export_data = {
            'preset_id': preset.preset_id,
            'name': preset.name,
            'description': preset.description,
            'category': preset.category.value,
            'filter_set': preset.filter_set.to_dict(),
            'icon': preset.icon,
            'keywords': preset.keywords,
            'difficulty': preset.difficulty
        }
        
        return json.dumps(export_data, indent=2)
    
    def import_preset(self, json_data: str) -> Optional[PresetTemplate]:
        """Import a preset from JSON string."""
        try:
            import json
            data = json.loads(json_data)
            
            filter_set = FilterSet.from_dict(data['filter_set'])
            
            preset = PresetTemplate(
                preset_id=data['preset_id'],
                name=data['name'],
                description=data['description'],
                category=PresetCategory(data['category']),
                filter_set=filter_set,
                icon=data.get('icon', 'custom'),
                keywords=data.get('keywords', []),
                difficulty=data.get('difficulty', 'custom')
            )
            
            self.add_preset(preset)
            return preset
            
        except Exception:
            return None