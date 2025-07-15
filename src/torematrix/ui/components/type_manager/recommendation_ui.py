"""Type Recommendation UI

AI-powered recommendations for type selection, optimization,
and best practices with explanations and confidence scores.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QTextEdit, QScrollArea, QFrame, QGroupBox,
    QListWidget, QListWidgetItem, QProgressBar, QComboBox,
    QCheckBox, QSpinBox, QSlider, QTabWidget, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QTimer
from PyQt6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor

from torematrix.core.models.types import TypeRegistry, TypeDefinition, get_type_registry
from torematrix.core.models.types.metadata import get_metadata_manager
from torematrix.core.models.types.validation import TypeValidationEngine


class RecommendationType(Enum):
    """Types of recommendations"""
    TYPE_SELECTION = "type_selection"
    TYPE_OPTIMIZATION = "type_optimization"
    TYPE_MIGRATION = "type_migration"
    BEST_PRACTICE = "best_practice"
    PERFORMANCE = "performance"
    SECURITY = "security"


class ConfidenceLevel(Enum):
    """Confidence levels for recommendations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class TypeRecommendation:
    """Represents a type recommendation"""
    id: str
    title: str
    description: str
    recommendation_type: RecommendationType
    confidence: ConfidenceLevel
    suggested_type_id: Optional[str] = None
    current_type_id: Optional[str] = None
    reasoning: List[str] = None
    benefits: List[str] = None
    risks: List[str] = None
    implementation_steps: List[str] = None
    priority_score: float = 0.0
    impact_score: float = 0.0
    effort_score: float = 0.0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.reasoning is None:
            self.reasoning = []
        if self.benefits is None:
            self.benefits = []
        if self.risks is None:
            self.risks = []
        if self.implementation_steps is None:
            self.implementation_steps = []
        if self.created_at is None:
            self.created_at = datetime.now()


class RecommendationEngine(QThread):
    """AI-powered recommendation engine"""
    
    recommendations_generated = pyqtSignal(list)  # List[TypeRecommendation]
    progress_updated = pyqtSignal(int)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, registry: TypeRegistry, context: Dict[str, Any] = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry
        self.context = context or {}
        self.validation_engine = TypeValidationEngine()
        self.should_stop = False
    
    def stop(self):
        """Stop recommendation generation"""
        self.should_stop = True
    
    def run(self):
        """Generate recommendations"""
        try:
            self.progress_updated.emit(0)
            
            recommendations = []
            
            # Generate different types of recommendations
            rec_generators = [
                self._generate_type_selection_recommendations,
                self._generate_optimization_recommendations,
                self._generate_migration_recommendations,
                self._generate_best_practice_recommendations,
                self._generate_performance_recommendations
            ]
            
            for i, generator in enumerate(rec_generators):
                if self.should_stop:
                    return
                
                try:
                    recs = generator()
                    recommendations.extend(recs)
                except Exception as e:
                    print(f"Error in recommendation generator {i}: {e}")
                
                progress = int((i + 1) / len(rec_generators) * 100)
                self.progress_updated.emit(progress)
            
            # Sort recommendations by priority
            recommendations.sort(key=lambda r: r.priority_score, reverse=True)
            
            self.recommendations_generated.emit(recommendations)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def _generate_type_selection_recommendations(self) -> List[TypeRecommendation]:
        """Generate type selection recommendations"""
        recommendations = []
        
        # Get content type from context
        content_type = self.context.get('content_type', '')
        element_data = self.context.get('element_data', {})
        
        if content_type or element_data:
            # Analyze content and suggest appropriate types
            suggestions = self._analyze_content_for_type_suggestions(content_type, element_data)
            
            for suggestion in suggestions:
                rec = TypeRecommendation(
                    id=f"type_sel_{len(recommendations)}",
                    title=f"Use '{suggestion['type_name']}' for this content",
                    description=f"Based on content analysis, '{suggestion['type_name']}' is recommended for this element.",
                    recommendation_type=RecommendationType.TYPE_SELECTION,
                    confidence=suggestion['confidence'],
                    suggested_type_id=suggestion['type_id'],
                    reasoning=suggestion['reasoning'],
                    benefits=suggestion['benefits'],
                    priority_score=suggestion['priority'],
                    impact_score=suggestion['impact'],
                    effort_score=1.0  # Type selection is usually low effort
                )
                recommendations.append(rec)
        
        return recommendations
    
    def _generate_optimization_recommendations(self) -> List[TypeRecommendation]:
        """Generate type optimization recommendations"""
        recommendations = []
        
        # Find types with optimization opportunities
        all_types = self.registry.list_types()
        
        for type_def in all_types:
            # Check for missing properties that could improve functionality
            missing_props = self._identify_missing_beneficial_properties(type_def)
            
            if missing_props:
                rec = TypeRecommendation(
                    id=f"opt_props_{type_def.type_id}",
                    title=f"Add properties to '{type_def.name}'",
                    description=f"Adding {len(missing_props)} properties could improve '{type_def.name}' functionality.",
                    recommendation_type=RecommendationType.TYPE_OPTIMIZATION,
                    confidence=ConfidenceLevel.MEDIUM,
                    current_type_id=type_def.type_id,
                    reasoning=[f"Property '{prop}' would enhance {reason}" for prop, reason in missing_props],
                    benefits=["Better validation", "Enhanced functionality", "Improved user experience"],
                    implementation_steps=[
                        "Review current type definition",
                        "Add recommended properties",
                        "Update validation rules",
                        "Test with existing elements"
                    ],
                    priority_score=6.0,
                    impact_score=7.0,
                    effort_score=4.0
                )
                recommendations.append(rec)
            
            # Check for overly complex validation rules
            if self._has_complex_validation(type_def):
                rec = TypeRecommendation(
                    id=f"opt_validation_{type_def.type_id}",
                    title=f"Simplify validation for '{type_def.name}'",
                    description="Complex validation rules may impact performance and usability.",
                    recommendation_type=RecommendationType.TYPE_OPTIMIZATION,
                    confidence=ConfidenceLevel.MEDIUM,
                    current_type_id=type_def.type_id,
                    reasoning=[
                        "Current validation has high complexity",
                        "Simplified rules improve performance",
                        "Easier maintenance and updates"
                    ],
                    benefits=["Better performance", "Easier maintenance", "Reduced errors"],
                    risks=["May need to adjust existing elements", "Temporary validation gaps"],
                    priority_score=5.5,
                    impact_score=6.0,
                    effort_score=5.0
                )
                recommendations.append(rec)
        
        return recommendations
    
    def _generate_migration_recommendations(self) -> List[TypeRecommendation]:
        """Generate type migration recommendations"""
        recommendations = []
        
        # Look for deprecated or outdated type patterns
        all_types = self.registry.list_types()
        
        for type_def in all_types:
            # Check if type follows old patterns
            if self._is_legacy_pattern(type_def):
                modern_equivalent = self._find_modern_equivalent(type_def)
                
                if modern_equivalent:
                    rec = TypeRecommendation(
                        id=f"migrate_{type_def.type_id}",
                        title=f"Migrate '{type_def.name}' to modern pattern",
                        description=f"'{type_def.name}' uses legacy patterns that could be modernized.",
                        recommendation_type=RecommendationType.TYPE_MIGRATION,
                        confidence=ConfidenceLevel.HIGH,
                        current_type_id=type_def.type_id,
                        suggested_type_id=modern_equivalent,
                        reasoning=[
                            "Current type uses deprecated patterns",
                            "Modern equivalent provides better functionality",
                            "Improved maintainability and performance"
                        ],
                        benefits=[
                            "Access to modern features",
                            "Better performance",
                            "Future-proof implementation",
                            "Improved developer experience"
                        ],
                        risks=[
                            "Migration effort required",
                            "Potential compatibility issues",
                            "Testing required for all affected elements"
                        ],
                        implementation_steps=[
                            "Audit all elements using current type",
                            "Create migration plan",
                            "Test migration in development",
                            "Gradually migrate elements",
                            "Monitor for issues"
                        ],
                        priority_score=7.0,
                        impact_score=8.0,
                        effort_score=7.0
                    )
                    recommendations.append(rec)
        
        return recommendations
    
    def _generate_best_practice_recommendations(self) -> List[TypeRecommendation]:
        """Generate best practice recommendations"""
        recommendations = []
        
        # Check for common best practice violations
        best_practices = [
            {
                'id': 'consistent_naming',
                'title': 'Use consistent naming conventions',
                'check': self._check_naming_consistency,
                'priority': 6.0
            },
            {
                'id': 'proper_categorization',
                'title': 'Ensure proper type categorization',
                'check': self._check_categorization,
                'priority': 5.0
            },
            {
                'id': 'adequate_descriptions',
                'title': 'Provide adequate type descriptions',
                'check': self._check_descriptions,
                'priority': 4.0
            },
            {
                'id': 'validation_completeness',
                'title': 'Complete validation rule coverage',
                'check': self._check_validation_completeness,
                'priority': 7.0
            }
        ]
        
        for practice in best_practices:
            issues = practice['check']()
            
            if issues:
                rec = TypeRecommendation(
                    id=f"bp_{practice['id']}",
                    title=practice['title'],
                    description=f"Found {len(issues)} issues with {practice['title'].lower()}.",
                    recommendation_type=RecommendationType.BEST_PRACTICE,
                    confidence=ConfidenceLevel.HIGH,
                    reasoning=issues[:3],  # Top 3 issues
                    benefits=[
                        "Improved code quality",
                        "Better maintainability",
                        "Enhanced team productivity",
                        "Reduced errors"
                    ],
                    implementation_steps=[
                        "Review identified issues",
                        "Create improvement plan",
                        "Implement fixes gradually",
                        "Update team guidelines"
                    ],
                    priority_score=practice['priority'],
                    impact_score=6.0,
                    effort_score=3.0
                )
                recommendations.append(rec)
        
        return recommendations
    
    def _generate_performance_recommendations(self) -> List[TypeRecommendation]:
        """Generate performance recommendations"""
        recommendations = []
        
        # Look for performance optimization opportunities
        all_types = self.registry.list_types()
        
        # Check for types with many properties (potential performance impact)
        high_prop_types = [t for t in all_types if len(t.properties) > 20]
        
        if high_prop_types:
            for type_def in high_prop_types:
                rec = TypeRecommendation(
                    id=f"perf_props_{type_def.type_id}",
                    title=f"Optimize property count for '{type_def.name}'",
                    description=f"'{type_def.name}' has {len(type_def.properties)} properties, which may impact performance.",
                    recommendation_type=RecommendationType.PERFORMANCE,
                    confidence=ConfidenceLevel.MEDIUM,
                    current_type_id=type_def.type_id,
                    reasoning=[
                        f"Type has {len(type_def.properties)} properties",
                        "High property count can slow validation",
                        "Consider splitting into focused sub-types"
                    ],
                    benefits=[
                        "Faster validation",
                        "Reduced memory usage",
                        "Better modularity",
                        "Easier maintenance"
                    ],
                    implementation_steps=[
                        "Analyze property usage patterns",
                        "Identify logical groupings",
                        "Create focused sub-types",
                        "Migrate existing elements"
                    ],
                    priority_score=6.5,
                    impact_score=7.0,
                    effort_score=6.0
                )
                recommendations.append(rec)
        
        return recommendations
    
    # Helper methods for analysis
    
    def _analyze_content_for_type_suggestions(self, content_type: str, element_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze content and suggest appropriate types"""
        suggestions = []
        
        # Simple content-based suggestions
        if 'text' in content_type.lower():
            suggestions.append({
                'type_id': 'text_element',
                'type_name': 'Text Element',
                'confidence': ConfidenceLevel.HIGH,
                'reasoning': ['Content appears to be text-based', 'Text element provides appropriate formatting'],
                'benefits': ['Proper text rendering', 'Rich formatting options'],
                'priority': 8.0,
                'impact': 7.0
            })
        
        if 'image' in content_type.lower() or 'media' in content_type.lower():
            suggestions.append({
                'type_id': 'media_element',
                'type_name': 'Media Element',
                'confidence': ConfidenceLevel.HIGH,
                'reasoning': ['Content appears to be media-based', 'Media element supports various formats'],
                'benefits': ['Proper media handling', 'Format optimization'],
                'priority': 8.0,
                'impact': 8.0
            })
        
        return suggestions
    
    def _identify_missing_beneficial_properties(self, type_def: TypeDefinition) -> List[Tuple[str, str]]:
        """Identify missing properties that would be beneficial"""
        missing = []
        
        # Common beneficial properties
        if 'created_at' not in type_def.properties:
            missing.append(('created_at', 'timestamp tracking'))
        
        if 'updated_at' not in type_def.properties:
            missing.append(('updated_at', 'change tracking'))
        
        if 'version' not in type_def.properties:
            missing.append(('version', 'version control'))
        
        if type_def.category == 'content' and 'author' not in type_def.properties:
            missing.append(('author', 'content attribution'))
        
        return missing
    
    def _has_complex_validation(self, type_def: TypeDefinition) -> bool:
        """Check if type has overly complex validation"""
        return len(type_def.validation_rules) > 10
    
    def _is_legacy_pattern(self, type_def: TypeDefinition) -> bool:
        """Check if type uses legacy patterns"""
        # Simple heuristics for legacy patterns
        return (
            'legacy' in type_def.type_id.lower() or
            'old' in type_def.type_id.lower() or
            type_def.created_at < datetime(2023, 1, 1)  # Arbitrary cutoff
        )
    
    def _find_modern_equivalent(self, type_def: TypeDefinition) -> Optional[str]:
        """Find modern equivalent for legacy type"""
        # Simple mapping for demonstration
        modern_mapping = {
            'text_element': 'rich_text_element',
            'simple_list': 'dynamic_list',
            'basic_table': 'data_table'
        }
        
        return modern_mapping.get(type_def.type_id)
    
    def _check_naming_consistency(self) -> List[str]:
        """Check for naming consistency issues"""
        issues = []
        all_types = self.registry.list_types()
        
        for type_def in all_types:
            if '_' not in type_def.type_id and len(type_def.type_id.split()) > 1:
                issues.append(f"'{type_def.name}' uses inconsistent naming convention")
        
        return issues
    
    def _check_categorization(self) -> List[str]:
        """Check for categorization issues"""
        issues = []
        all_types = self.registry.list_types()
        
        for type_def in all_types:
            if not type_def.category or type_def.category == 'other':
                issues.append(f"'{type_def.name}' lacks proper category assignment")
        
        return issues
    
    def _check_descriptions(self) -> List[str]:
        """Check for description adequacy"""
        issues = []
        all_types = self.registry.list_types()
        
        for type_def in all_types:
            if not type_def.description or len(type_def.description) < 20:
                issues.append(f"'{type_def.name}' has inadequate description")
        
        return issues
    
    def _check_validation_completeness(self) -> List[str]:
        """Check for validation completeness"""
        issues = []
        all_types = self.registry.list_types()
        
        for type_def in all_types:
            if not type_def.validation_rules:
                issues.append(f"'{type_def.name}' has no validation rules")
            elif len(type_def.validation_rules) < 2:
                issues.append(f"'{type_def.name}' has minimal validation coverage")
        
        return issues


class RecommendationCard(QFrame):
    """Widget for displaying a single recommendation"""
    
    apply_requested = pyqtSignal(TypeRecommendation)
    details_requested = pyqtSignal(TypeRecommendation)
    dismiss_requested = pyqtSignal(str)  # recommendation_id
    
    def __init__(self, recommendation: TypeRecommendation, parent=None):
        super().__init__(parent)
        
        self.recommendation = recommendation
        self.setup_ui()
        self.apply_styles()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Title and type
        title_layout = QVBoxLayout()
        
        title_label = QLabel(self.recommendation.title)
        title_label.setFont(QFont("", 11, QFont.Weight.Bold))
        title_layout.addWidget(title_label)
        
        type_label = QLabel(self.recommendation.recommendation_type.value.replace('_', ' ').title())
        type_label.setFont(QFont("", 9))
        type_label.setStyleSheet("color: #666;")
        title_layout.addWidget(type_label)
        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        
        # Confidence indicator
        confidence_label = QLabel(self.recommendation.confidence.value.replace('_', ' ').title())
        confidence_label.setFont(QFont("", 9, QFont.Weight.Bold))
        
        confidence_colors = {
            ConfidenceLevel.LOW: "#ff8c00",
            ConfidenceLevel.MEDIUM: "#ffd700", 
            ConfidenceLevel.HIGH: "#32cd32",
            ConfidenceLevel.VERY_HIGH: "#008000"
        }
        
        color = confidence_colors.get(self.recommendation.confidence, "#666")
        confidence_label.setStyleSheet(f"color: {color};")
        header_layout.addWidget(confidence_label)
        
        layout.addLayout(header_layout)
        
        # Description
        desc_label = QLabel(self.recommendation.description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #333; line-height: 1.4;")
        layout.addWidget(desc_label)
        
        # Metrics
        metrics_layout = QHBoxLayout()
        
        metrics = [
            ("Priority", self.recommendation.priority_score, "#0078d4"),
            ("Impact", self.recommendation.impact_score, "#107c10"),
            ("Effort", self.recommendation.effort_score, "#ff8c00")
        ]
        
        for name, score, color in metrics:
            metric_layout = QVBoxLayout()
            
            name_label = QLabel(name)
            name_label.setFont(QFont("", 8))
            name_label.setStyleSheet("color: #666;")
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            metric_layout.addWidget(name_label)
            
            score_label = QLabel(f"{score:.1f}")
            score_label.setFont(QFont("", 10, QFont.Weight.Bold))
            score_label.setStyleSheet(f"color: {color};")
            score_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            metric_layout.addWidget(score_label)
            
            metrics_layout.addLayout(metric_layout)
        
        metrics_layout.addStretch()
        layout.addLayout(metrics_layout)
        
        # Actions
        actions_layout = QHBoxLayout()
        
        self.details_btn = QPushButton("Details")
        self.details_btn.clicked.connect(lambda: self.details_requested.emit(self.recommendation))
        actions_layout.addWidget(self.details_btn)
        
        if self.recommendation.suggested_type_id or self.recommendation.current_type_id:
            self.apply_btn = QPushButton("Apply")
            self.apply_btn.clicked.connect(lambda: self.apply_requested.emit(self.recommendation))
            self.apply_btn.setStyleSheet("""
                QPushButton {
                    background: #0078d4;
                    color: white;
                    border: none;
                    padding: 4px 12px;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background: #106ebe;
                }
            """)
            actions_layout.addWidget(self.apply_btn)
        
        self.dismiss_btn = QPushButton("Dismiss")
        self.dismiss_btn.clicked.connect(lambda: self.dismiss_requested.emit(self.recommendation.id))
        actions_layout.addWidget(self.dismiss_btn)
        
        actions_layout.addStretch()
        layout.addLayout(actions_layout)
    
    def apply_styles(self):
        """Apply card styles"""
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #ddd;
                border-radius: 8px;
                background: white;
                margin: 2px;
            }
            QFrame:hover {
                border-color: #0078d4;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
        """)
        
        self.setMinimumHeight(180)
        self.setMaximumHeight(220)


class RecommendationDetailsDialog(QWidget):
    """Dialog showing detailed recommendation information"""
    
    def __init__(self, recommendation: TypeRecommendation, parent=None):
        super().__init__(parent)
        
        self.recommendation = recommendation
        self.setWindowTitle(f"Recommendation: {recommendation.title}")
        self.setMinimumSize(500, 400)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel(self.recommendation.title)
        title.setFont(QFont("", 14, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        confidence = QLabel(f"Confidence: {self.recommendation.confidence.value.title()}")
        confidence.setFont(QFont("", 10, QFont.Weight.Bold))
        header_layout.addWidget(confidence)
        
        layout.addLayout(header_layout)
        
        # Tabs
        tabs = QTabWidget()
        
        # Overview tab
        overview_widget = QWidget()
        overview_layout = QVBoxLayout(overview_widget)
        
        overview_layout.addWidget(QLabel("Description:"))
        desc_text = QTextEdit()
        desc_text.setPlainText(self.recommendation.description)
        desc_text.setReadOnly(True)
        desc_text.setMaximumHeight(80)
        overview_layout.addWidget(desc_text)
        
        if self.recommendation.reasoning:
            overview_layout.addWidget(QLabel("Reasoning:"))
            reasoning_text = "\n".join(f"• {reason}" for reason in self.recommendation.reasoning)
            reasoning_label = QLabel(reasoning_text)
            reasoning_label.setWordWrap(True)
            overview_layout.addWidget(reasoning_label)
        
        tabs.addTab(overview_widget, "Overview")
        
        # Benefits & Risks tab
        if self.recommendation.benefits or self.recommendation.risks:
            benefits_risks_widget = QWidget()
            br_layout = QVBoxLayout(benefits_risks_widget)
            
            if self.recommendation.benefits:
                br_layout.addWidget(QLabel("Benefits:"))
                benefits_text = "\n".join(f"✓ {benefit}" for benefit in self.recommendation.benefits)
                benefits_label = QLabel(benefits_text)
                benefits_label.setStyleSheet("color: #107c10;")
                benefits_label.setWordWrap(True)
                br_layout.addWidget(benefits_label)
            
            if self.recommendation.risks:
                br_layout.addWidget(QLabel("Risks:"))
                risks_text = "\n".join(f"⚠️ {risk}" for risk in self.recommendation.risks)
                risks_label = QLabel(risks_text)
                risks_label.setStyleSheet("color: #d13438;")
                risks_label.setWordWrap(True)
                br_layout.addWidget(risks_label)
            
            br_layout.addStretch()
            tabs.addTab(benefits_risks_widget, "Benefits & Risks")
        
        # Implementation tab
        if self.recommendation.implementation_steps:
            impl_widget = QWidget()
            impl_layout = QVBoxLayout(impl_widget)
            
            impl_layout.addWidget(QLabel("Implementation Steps:"))
            
            for i, step in enumerate(self.recommendation.implementation_steps, 1):
                step_label = QLabel(f"{i}. {step}")
                step_label.setWordWrap(True)
                impl_layout.addWidget(step_label)
            
            impl_layout.addStretch()
            tabs.addTab(impl_widget, "Implementation")
        
        layout.addWidget(tabs)


class TypeRecommendationUI(QWidget):
    """Complete type recommendation interface"""
    
    # Signals
    recommendation_applied = pyqtSignal(TypeRecommendation)
    type_selection_requested = pyqtSignal(str)  # type_id
    
    def __init__(self, registry: TypeRegistry = None, parent=None):
        super().__init__(parent)
        
        self.registry = registry or get_type_registry()
        self.current_recommendations: List[TypeRecommendation] = []
        self.dismissed_recommendations: set = set()
        self.recommendation_engine: Optional[RecommendationEngine] = None
        
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        """Setup user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel("AI Recommendations")
        title.setFont(QFont("", 12, QFont.Weight.Bold))
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Filters
        self.type_filter = QComboBox()
        self.type_filter.addItems([
            "All Recommendations",
            "Type Selection",
            "Optimization", 
            "Migration",
            "Best Practices",
            "Performance"
        ])
        header_layout.addWidget(self.type_filter)
        
        self.confidence_filter = QComboBox()
        self.confidence_filter.addItems([
            "All Confidence Levels",
            "High Confidence Only",
            "Medium+ Confidence"
        ])
        header_layout.addWidget(self.confidence_filter)
        
        # Generate button
        self.generate_btn = QPushButton("✨ Generate Recommendations")
        self.generate_btn.clicked.connect(self.generate_recommendations)
        header_layout.addWidget(self.generate_btn)
        
        layout.addLayout(header_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Recommendations area
        self.recommendations_scroll = QScrollArea()
        self.recommendations_widget = QWidget()
        self.recommendations_layout = QVBoxLayout(self.recommendations_widget)
        self.recommendations_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.recommendations_scroll.setWidget(self.recommendations_widget)
        self.recommendations_scroll.setWidgetResizable(True)
        layout.addWidget(self.recommendations_scroll)
        
        # Empty state
        self.empty_label = QLabel("Click 'Generate Recommendations' to get AI-powered suggestions")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #999; font-style: italic; font-size: 14px;")
        layout.addWidget(self.empty_label)
        
        # Initially show empty state
        self.show_empty_state()
    
    def connect_signals(self):
        """Connect signals"""
        self.type_filter.currentTextChanged.connect(self.filter_recommendations)
        self.confidence_filter.currentTextChanged.connect(self.filter_recommendations)
    
    def generate_recommendations(self, context: Dict[str, Any] = None):
        """Generate recommendations with optional context"""
        if self.recommendation_engine and self.recommendation_engine.isRunning():
            self.recommendation_engine.stop()
            self.recommendation_engine.wait()
        
        # Show progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.generate_btn.setEnabled(False)
        
        # Start generation
        self.recommendation_engine = RecommendationEngine(self.registry, context or {})
        self.recommendation_engine.recommendations_generated.connect(self.on_recommendations_generated)
        self.recommendation_engine.progress_updated.connect(self.progress_bar.setValue)
        self.recommendation_engine.error_occurred.connect(self.on_generation_error)
        self.recommendation_engine.start()
    
    @pyqtSlot(list)
    def on_recommendations_generated(self, recommendations: List[TypeRecommendation]):
        """Handle generated recommendations"""
        self.current_recommendations = recommendations
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)
        
        self.update_recommendations_display()
    
    @pyqtSlot(str)
    def on_generation_error(self, error: str):
        """Handle generation error"""
        self.progress_bar.setVisible(False)
        self.generate_btn.setEnabled(True)
        
        # Could show error message to user
        print(f"Recommendation generation error: {error}")
    
    def update_recommendations_display(self):
        """Update recommendations display"""
        # Clear existing recommendations
        for i in reversed(range(self.recommendations_layout.count())):
            widget = self.recommendations_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Filter recommendations
        filtered_recs = self.filter_recommendations_list(self.current_recommendations)
        
        if filtered_recs:
            self.show_recommendations()
            
            for rec in filtered_recs:
                if rec.id not in self.dismissed_recommendations:
                    card = RecommendationCard(rec)
                    card.apply_requested.connect(self.apply_recommendation)
                    card.details_requested.connect(self.show_recommendation_details)
                    card.dismiss_requested.connect(self.dismiss_recommendation)
                    
                    self.recommendations_layout.addWidget(card)
        else:
            self.show_empty_state()
    
    def filter_recommendations_list(self, recommendations: List[TypeRecommendation]) -> List[TypeRecommendation]:
        """Filter recommendations based on current filters"""
        filtered = recommendations.copy()
        
        # Type filter
        type_filter = self.type_filter.currentText()
        if type_filter != "All Recommendations":
            filter_map = {
                "Type Selection": RecommendationType.TYPE_SELECTION,
                "Optimization": RecommendationType.TYPE_OPTIMIZATION,
                "Migration": RecommendationType.TYPE_MIGRATION,
                "Best Practices": RecommendationType.BEST_PRACTICE,
                "Performance": RecommendationType.PERFORMANCE
            }
            
            if type_filter in filter_map:
                filtered = [r for r in filtered if r.recommendation_type == filter_map[type_filter]]
        
        # Confidence filter
        confidence_filter = self.confidence_filter.currentText()
        if confidence_filter == "High Confidence Only":
            filtered = [r for r in filtered if r.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH]]
        elif confidence_filter == "Medium+ Confidence":
            filtered = [r for r in filtered if r.confidence != ConfidenceLevel.LOW]
        
        return filtered
    
    def filter_recommendations(self):
        """Apply current filters"""
        self.update_recommendations_display()
    
    def show_recommendations(self):
        """Show recommendations area"""
        self.empty_label.setVisible(False)
        self.recommendations_scroll.setVisible(True)
    
    def show_empty_state(self):
        """Show empty state"""
        self.empty_label.setVisible(True)
        self.recommendations_scroll.setVisible(False)
    
    def apply_recommendation(self, recommendation: TypeRecommendation):
        """Apply a recommendation"""
        self.recommendation_applied.emit(recommendation)
        
        # Remove from display
        self.dismiss_recommendation(recommendation.id)
    
    def show_recommendation_details(self, recommendation: TypeRecommendation):
        """Show recommendation details"""
        details_dialog = RecommendationDetailsDialog(recommendation, self)
        details_dialog.show()
    
    def dismiss_recommendation(self, recommendation_id: str):
        """Dismiss a recommendation"""
        self.dismissed_recommendations.add(recommendation_id)
        self.update_recommendations_display()
    
    def set_context(self, context: Dict[str, Any]):
        """Set context for recommendations"""
        # Could trigger automatic re-generation with new context
        pass
    
    def refresh(self):
        """Refresh recommendations"""
        if self.current_recommendations:
            self.generate_recommendations()
