"""
Workflow Optimizer for Merge/Split Operations - Agent 4 Implementation.

This module provides intelligent workflow optimization through user behavior analysis,
pattern recognition, and intelligent suggestions. It learns from user actions to
provide contextual recommendations and streamline the document processing workflow.

Features:
- User behavior analysis and pattern recognition
- Context-aware workflow suggestions
- Performance metrics and analytics
- Adaptive UI based on user skill level
- Workflow automation recommendations
"""

from typing import Dict, List, Optional, Any, Union, Callable, Deque
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import deque, defaultdict, Counter
from datetime import datetime, timedelta
import json
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
    QLabel, QListWidget, QTextEdit, QComboBox, QSpinBox, QCheckBox,
    QGroupBox, QTabWidget, QSplitter, QTreeWidget, QTreeWidgetItem,
    QDialog, QDialogButtonBox, QProgressBar, QMessageBox, QToolButton,
    QLineEdit, QScrollArea, QFrame, QSlider, QButtonGroup, QRadioButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QMutex
from PyQt6.QtGui import QIcon, QPalette, QFont

from .....core.models.element import Element, ElementType
from .....core.state import StateManager
from .....core.events import EventBus
from .....ui.components.base import BaseWidget

logger = logging.getLogger(__name__)


class WorkflowStage(Enum):
    """Stages in the workflow process."""
    SELECTION = auto()
    ANALYSIS = auto()
    OPERATION = auto()
    VALIDATION = auto()
    OPTIMIZATION = auto()
    COMPLETION = auto()


class UserSkillLevel(Enum):
    """User skill levels."""
    BEGINNER = auto()
    INTERMEDIATE = auto()
    ADVANCED = auto()
    EXPERT = auto()


@dataclass
class UserAction:
    """Represents a user action in the workflow."""
    action_type: str
    context: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0
    success: bool = True
    timestamp: datetime = field(default_factory=datetime.now)
    workflow_stage: WorkflowStage = WorkflowStage.OPERATION
    error_message: Optional[str] = None


@dataclass
class WorkflowPattern:
    """Represents a detected workflow pattern."""
    name: str
    actions: List[str] = field(default_factory=list)
    frequency: int = 0
    success_rate: float = 1.0
    average_duration: float = 0.0
    context_conditions: Dict[str, Any] = field(default_factory=dict)
    skill_level: UserSkillLevel = UserSkillLevel.INTERMEDIATE
    
    def matches_context(self, context: Dict[str, Any]) -> float:
        """Calculate how well this pattern matches the given context."""
        if not self.context_conditions:
            return 0.5  # Neutral match
        
        total_conditions = len(self.context_conditions)
        matching_conditions = 0
        
        for condition_key, condition_value in self.context_conditions.items():
            if condition_key in context:
                if context[condition_key] == condition_value:
                    matching_conditions += 1
                elif isinstance(condition_value, (int, float)) and isinstance(context[condition_key], (int, float)):
                    # Allow for some tolerance in numeric values
                    tolerance = 0.1 * abs(condition_value)
                    if abs(context[condition_key] - condition_value) <= tolerance:
                        matching_conditions += 0.8
        
        return matching_conditions / total_conditions if total_conditions > 0 else 0.0


@dataclass
class WorkflowSuggestion:
    """Represents a workflow suggestion."""
    title: str
    description: str
    action_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    estimated_time_savings: float = 0.0
    pattern_match: Optional[WorkflowPattern] = None


@dataclass
class WorkflowMetrics:
    """Workflow performance metrics."""
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    average_action_duration: float = 0.0
    most_common_actions: List[tuple] = field(default_factory=list)
    error_patterns: List[str] = field(default_factory=list)
    efficiency_score: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_actions == 0:
            return 1.0
        return self.successful_actions / self.total_actions


class UserBehaviorAnalyzer:
    """Analyzes user behavior patterns for workflow optimization."""
    
    def __init__(self, max_history: int = 1000):
        self.action_history: Deque[UserAction] = deque(maxlen=max_history)
        self.patterns: Dict[str, WorkflowPattern] = {}
        self.user_preferences: Dict[str, Any] = {}
        self.skill_assessment: Dict[str, float] = defaultdict(float)
        self.max_history = max_history
    
    def record_action(self, action: UserAction):
        """Record a user action."""
        self.action_history.append(action)
        self._update_skill_assessment(action)
        
        # Trigger pattern analysis periodically
        if len(self.action_history) % 10 == 0:
            self._identify_patterns()
    
    def _update_skill_assessment(self, action: UserAction):
        """Update skill assessment based on action."""
        # Simple skill assessment based on speed and success
        base_score = 1.0 if action.success else 0.0
        
        # Bonus for speed (assuming shorter duration indicates skill)
        if action.duration > 0:
            speed_factor = max(0.5, 2.0 - (action.duration / 10.0))  # Normalize around 10 seconds
            base_score *= speed_factor
        
        # Update rolling average
        current_score = self.skill_assessment[action.action_type]
        self.skill_assessment[action.action_type] = (current_score * 0.8) + (base_score * 0.2)
    
    def get_user_skill_level(self) -> UserSkillLevel:
        """Determine overall user skill level."""
        if not self.skill_assessment:
            return UserSkillLevel.BEGINNER
        
        average_skill = sum(self.skill_assessment.values()) / len(self.skill_assessment)
        
        if average_skill >= 1.5:
            return UserSkillLevel.EXPERT
        elif average_skill >= 1.2:
            return UserSkillLevel.ADVANCED
        elif average_skill >= 0.8:
            return UserSkillLevel.INTERMEDIATE
        else:
            return UserSkillLevel.BEGINNER
    
    def _identify_patterns(self):
        """Identify patterns in user behavior."""
        if len(self.action_history) < 5:
            return
        
        # Look for sequences of actions
        recent_actions = list(self.action_history)[-20:]  # Last 20 actions
        action_sequences = []
        
        # Extract sequences of 3-5 actions
        for length in range(3, 6):
            for i in range(len(recent_actions) - length + 1):
                sequence = [action.action_type for action in recent_actions[i:i+length]]
                action_sequences.append(sequence)
        
        # Count sequence frequencies
        sequence_counts = Counter(tuple(seq) for seq in action_sequences)
        
        # Create patterns from frequent sequences
        for sequence, count in sequence_counts.items():
            if count >= 2:  # Must appear at least twice
                pattern_id = "_".join(sequence)
                
                if pattern_id not in self.patterns:
                    # Calculate average duration and success rate for this pattern
                    pattern_actions = [a for a in recent_actions if a.action_type in sequence]
                    avg_duration = sum(a.duration for a in pattern_actions) / len(pattern_actions)
                    success_rate = sum(1 for a in pattern_actions if a.success) / len(pattern_actions)
                    
                    self.patterns[pattern_id] = WorkflowPattern(
                        name=f"Pattern: {' -> '.join(sequence)}",
                        actions=list(sequence),
                        frequency=count,
                        success_rate=success_rate,
                        average_duration=avg_duration,
                        skill_level=self.get_user_skill_level()
                    )
                else:
                    # Update existing pattern
                    self.patterns[pattern_id].frequency = count
    
    def get_workflow_patterns(self) -> List[WorkflowPattern]:
        """Get identified workflow patterns."""
        return list(self.patterns.values())
    
    def get_metrics(self) -> WorkflowMetrics:
        """Calculate workflow metrics."""
        if not self.action_history:
            return WorkflowMetrics()
        
        actions = list(self.action_history)
        
        total_actions = len(actions)
        successful_actions = sum(1 for a in actions if a.success)
        failed_actions = total_actions - successful_actions
        
        total_duration = sum(a.duration for a in actions if a.duration > 0)
        action_count_with_duration = sum(1 for a in actions if a.duration > 0)
        average_duration = total_duration / action_count_with_duration if action_count_with_duration > 0 else 0.0
        
        # Most common actions
        action_counts = Counter(a.action_type for a in actions)
        most_common = action_counts.most_common(5)
        
        # Calculate efficiency score
        efficiency_score = self._calculate_efficiency_score(actions)
        
        return WorkflowMetrics(
            total_actions=total_actions,
            successful_actions=successful_actions,
            failed_actions=failed_actions,
            average_action_duration=average_duration,
            most_common_actions=most_common,
            efficiency_score=efficiency_score
        )
    
    def _calculate_efficiency_score(self, actions: List[UserAction]) -> float:
        """Calculate workflow efficiency score."""
        if not actions:
            return 0.0
        
        # Factors: success rate, speed, pattern utilization
        success_rate = sum(1 for a in actions if a.success) / len(actions)
        
        # Speed factor (inverse of average duration)
        durations = [a.duration for a in actions if a.duration > 0]
        avg_duration = sum(durations) / len(durations) if durations else 10.0
        speed_factor = min(1.0, 10.0 / avg_duration)  # Normalize around 10 seconds
        
        # Pattern utilization (how often user follows identified patterns)
        pattern_factor = min(1.0, len(self.patterns) / 5.0)  # More patterns = better
        
        return (success_rate * 0.5) + (speed_factor * 0.3) + (pattern_factor * 0.2)


class WorkflowSuggestionEngine:
    """Generates workflow suggestions based on user behavior and context."""
    
    def __init__(self, behavior_analyzer: UserBehaviorAnalyzer):
        self.behavior_analyzer = behavior_analyzer
        self.suggestion_cache: Dict[str, List[WorkflowSuggestion]] = {}
        self.context_analyzers: List[Callable] = [
            self._analyze_element_context,
            self._analyze_operation_context,
            self._analyze_performance_context
        ]
    
    def get_suggestions(self, context: Dict[str, Any]) -> List[WorkflowSuggestion]:
        """Get workflow suggestions for the current context."""
        context_key = self._generate_context_key(context)
        
        if context_key in self.suggestion_cache:
            return self.suggestion_cache[context_key]
        
        suggestions = []
        
        # Run context analyzers
        for analyzer in self.context_analyzers:
            analyzer_suggestions = analyzer(context)
            suggestions.extend(analyzer_suggestions)
        
        # Pattern-based suggestions
        pattern_suggestions = self._get_pattern_suggestions(context)
        suggestions.extend(pattern_suggestions)
        
        # Sort by confidence
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        
        # Cache results
        self.suggestion_cache[context_key] = suggestions[:10]  # Keep top 10
        
        return suggestions[:5]  # Return top 5
    
    def _generate_context_key(self, context: Dict[str, Any]) -> str:
        """Generate a cache key for the context."""
        key_parts = []
        
        if "selected_elements" in context:
            key_parts.append(f"elements_{len(context['selected_elements'])}")
        
        if "operation_intent" in context:
            key_parts.append(f"intent_{context['operation_intent']}")
        
        return "_".join(key_parts) if key_parts else "default"
    
    def _analyze_element_context(self, context: Dict[str, Any]) -> List[WorkflowSuggestion]:
        """Analyze element-related context for suggestions."""
        suggestions = []
        
        selected_elements = context.get("selected_elements", [])
        if not selected_elements:
            return suggestions
        
        element_count = len(selected_elements)
        
        # Suggest merge for multiple similar elements
        if element_count > 1:
            suggestions.append(WorkflowSuggestion(
                title="Merge Selected Elements",
                description=f"Combine {element_count} selected elements into one",
                action_type="merge_elements",
                parameters={"element_count": element_count},
                confidence=0.7,
                estimated_time_savings=5.0
            ))
        
        # Suggest split for large single element
        elif element_count == 1:
            element = selected_elements[0]
            if hasattr(element, 'text') and element.text and len(element.text) > 200:
                suggestions.append(WorkflowSuggestion(
                    title="Split Large Element",
                    description="Break down this large element into smaller parts",
                    action_type="split_element",
                    parameters={"text_length": len(element.text)},
                    confidence=0.6,
                    estimated_time_savings=8.0
                ))
        
        return suggestions
    
    def _analyze_operation_context(self, context: Dict[str, Any]) -> List[WorkflowSuggestion]:
        """Analyze operation-related context for suggestions."""
        suggestions = []
        
        operation_intent = context.get("operation_intent")
        if not operation_intent:
            return suggestions
        
        if operation_intent == "merge":
            suggestions.append(WorkflowSuggestion(
                title="Use Merge Template",
                description="Apply a predefined merge template for consistency",
                action_type="apply_template",
                parameters={"template_type": "merge"},
                confidence=0.8,
                estimated_time_savings=10.0
            ))
        
        elif operation_intent == "split":
            suggestions.append(WorkflowSuggestion(
                title="Auto-detect Split Points",
                description="Automatically identify optimal split locations",
                action_type="auto_split",
                parameters={},
                confidence=0.75,
                estimated_time_savings=15.0
            ))
        
        return suggestions
    
    def _analyze_performance_context(self, context: Dict[str, Any]) -> List[WorkflowSuggestion]:
        """Analyze performance context for optimization suggestions."""
        suggestions = []
        
        metrics = self.behavior_analyzer.get_metrics()
        
        # Suggest efficiency improvements
        if metrics.efficiency_score < 0.7:
            suggestions.append(WorkflowSuggestion(
                title="Improve Workflow Efficiency",
                description="Try keyboard shortcuts and batch operations",
                action_type="efficiency_tips",
                parameters={"current_score": metrics.efficiency_score},
                confidence=0.6,
                estimated_time_savings=20.0
            ))
        
        # Suggest pattern adoption
        patterns = self.behavior_analyzer.get_workflow_patterns()
        if len(patterns) > 0:
            best_pattern = max(patterns, key=lambda p: p.success_rate)
            suggestions.append(WorkflowSuggestion(
                title="Use Proven Pattern",
                description=f"Apply the '{best_pattern.name}' pattern",
                action_type="apply_pattern",
                parameters={"pattern_name": best_pattern.name},
                confidence=0.8,
                estimated_time_savings=best_pattern.average_duration * 0.3
            ))
        
        return suggestions
    
    def _get_pattern_suggestions(self, context: Dict[str, Any]) -> List[WorkflowSuggestion]:
        """Get suggestions based on identified patterns."""
        suggestions = []
        
        patterns = self.behavior_analyzer.get_workflow_patterns()
        
        for pattern in patterns:
            match_score = pattern.matches_context(context)
            if match_score > 0.5:
                suggestions.append(WorkflowSuggestion(
                    title=f"Follow {pattern.name}",
                    description=f"Pattern with {pattern.success_rate:.1%} success rate",
                    action_type="follow_pattern",
                    parameters={"pattern_actions": pattern.actions},
                    confidence=match_score * 0.9,
                    estimated_time_savings=pattern.average_duration * 0.2,
                    pattern_match=pattern
                ))
        
        return suggestions


class WorkflowOptimizerWidget(BaseWidget):
    """Widget for workflow optimization and user behavior analysis."""
    
    suggestion_selected = pyqtSignal(str, dict)  # action_type, parameters
    
    def __init__(self, state_manager: StateManager, event_bus: EventBus, parent=None):
        super().__init__(state_manager, event_bus, parent)
        
        self.behavior_analyzer = UserBehaviorAnalyzer()
        self.suggestion_engine = WorkflowSuggestionEngine(self.behavior_analyzer)
        
        self._setup_ui()
        self._connect_signals()
        
        # Setup periodic updates
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_displays)
        self.update_timer.start(5000)  # Update every 5 seconds
    
    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Suggestions tab
        self.suggestions_tab = self._create_suggestions_tab()
        self.tab_widget.addTab(self.suggestions_tab, "Suggestions")
        
        # Analytics tab
        self.analytics_tab = self._create_analytics_tab()
        self.tab_widget.addTab(self.analytics_tab, "Analytics")
        
        # Workflows tab
        self.workflows_tab = self._create_workflows_tab()
        self.tab_widget.addTab(self.workflows_tab, "Workflows")
        
        layout.addWidget(self.tab_widget)
    
    def _create_suggestions_tab(self) -> QWidget:
        """Create suggestions tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Current context
        context_group = QGroupBox("Current Context")
        context_layout = QVBoxLayout(context_group)
        
        self.context_label = QLabel("No active context")
        context_layout.addWidget(self.context_label)
        
        layout.addWidget(context_group)
        
        # Suggestions list
        suggestions_group = QGroupBox("Workflow Suggestions")
        suggestions_layout = QVBoxLayout(suggestions_group)
        
        self.suggestions_list = QListWidget()
        suggestions_layout.addWidget(self.suggestions_list)
        
        # Apply suggestion button
        self.apply_suggestion_btn = QPushButton("Apply Selected Suggestion")
        self.apply_suggestion_btn.setEnabled(False)
        suggestions_layout.addWidget(self.apply_suggestion_btn)
        
        layout.addWidget(suggestions_group)
        
        return widget
    
    def _create_analytics_tab(self) -> QWidget:
        """Create analytics tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Metrics display
        metrics_group = QGroupBox("Performance Metrics")
        metrics_layout = QGridLayout(metrics_group)
        
        self.total_actions_label = QLabel("Total Actions: 0")
        self.success_rate_label = QLabel("Success Rate: 100%")
        self.avg_duration_label = QLabel("Avg Duration: 0s")
        self.efficiency_label = QLabel("Efficiency: 0%")
        
        metrics_layout.addWidget(self.total_actions_label, 0, 0)
        metrics_layout.addWidget(self.success_rate_label, 0, 1)
        metrics_layout.addWidget(self.avg_duration_label, 1, 0)
        metrics_layout.addWidget(self.efficiency_label, 1, 1)
        
        layout.addWidget(metrics_group)
        
        # Skill assessment
        skill_group = QGroupBox("Skill Assessment")
        skill_layout = QVBoxLayout(skill_group)
        
        self.skill_level_label = QLabel("Skill Level: Beginner")
        skill_layout.addWidget(self.skill_level_label)
        
        layout.addWidget(skill_group)
        
        # Action history
        history_group = QGroupBox("Recent Actions")
        history_layout = QVBoxLayout(history_group)
        
        self.action_history_list = QListWidget()
        history_layout.addWidget(self.action_history_list)
        
        layout.addWidget(history_group)
        
        return widget
    
    def _create_workflows_tab(self) -> QWidget:
        """Create workflows tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Identified patterns
        patterns_group = QGroupBox("Identified Patterns")
        patterns_layout = QVBoxLayout(patterns_group)
        
        self.patterns_list = QListWidget()
        patterns_layout.addWidget(self.patterns_list)
        
        layout.addWidget(patterns_group)
        
        return widget
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.apply_suggestion_btn.clicked.connect(self._apply_selected_suggestion)
        self.suggestions_list.itemSelectionChanged.connect(self._on_suggestion_selection_changed)
    
    def record_user_action(self, action_type: str, context: Dict[str, Any] = None, 
                          duration: float = 0.0, success: bool = True, 
                          workflow_stage: WorkflowStage = WorkflowStage.OPERATION):
        """Record a user action for analysis."""
        if context is None:
            context = {}
        
        action = UserAction(
            action_type=action_type,
            context=context,
            duration=duration,
            success=success,
            workflow_stage=workflow_stage
        )
        
        self.behavior_analyzer.record_action(action)
    
    def get_workflow_suggestions(self) -> List[WorkflowSuggestion]:
        """Get current workflow suggestions."""
        context = {
            "selected_elements": self.state_manager.get_selected_elements(),
            "all_elements": self.state_manager.get_all_elements()
        }
        
        return self.suggestion_engine.get_suggestions(context)
    
    def get_current_metrics(self) -> WorkflowMetrics:
        """Get current workflow metrics."""
        return self.behavior_analyzer.get_metrics()
    
    def _update_displays(self):
        """Update all display components."""
        self._update_suggestions()
        self._update_analytics()
        self._update_workflows()
    
    def _update_suggestions(self):
        """Update suggestions display."""
        suggestions = self.get_workflow_suggestions()
        
        self.suggestions_list.clear()
        for suggestion in suggestions:
            item_text = f"{suggestion.title} (Confidence: {suggestion.confidence:.1%})"
            self.suggestions_list.addItem(item_text)
        
        # Update context
        selected_count = len(self.state_manager.get_selected_elements())
        self.context_label.setText(f"Selected Elements: {selected_count}")
    
    def _update_analytics(self):
        """Update analytics display."""
        metrics = self.behavior_analyzer.get_metrics()
        
        self.total_actions_label.setText(f"Total Actions: {metrics.total_actions}")
        self.success_rate_label.setText(f"Success Rate: {metrics.success_rate:.1%}")
        self.avg_duration_label.setText(f"Avg Duration: {metrics.average_action_duration:.1f}s")
        self.efficiency_label.setText(f"Efficiency: {metrics.efficiency_score:.1%}")
        
        skill_level = self.behavior_analyzer.get_user_skill_level()
        self.skill_level_label.setText(f"Skill Level: {skill_level.name.title()}")
        
        # Update action history
        self.action_history_list.clear()
        recent_actions = list(self.behavior_analyzer.action_history)[-10:]
        for action in reversed(recent_actions):
            status = "✓" if action.success else "✗"
            item_text = f"{status} {action.action_type} ({action.duration:.1f}s)"
            self.action_history_list.addItem(item_text)
    
    def _update_workflows(self):
        """Update workflows display."""
        patterns = self.behavior_analyzer.get_workflow_patterns()
        
        self.patterns_list.clear()
        for pattern in patterns:
            item_text = f"{pattern.name} (Frequency: {pattern.frequency}, Success: {pattern.success_rate:.1%})"
            self.patterns_list.addItem(item_text)
    
    def _on_suggestion_selection_changed(self):
        """Handle suggestion selection change."""
        has_selection = len(self.suggestions_list.selectedItems()) > 0
        self.apply_suggestion_btn.setEnabled(has_selection)
    
    def _apply_selected_suggestion(self):
        """Apply the selected suggestion."""
        current_row = self.suggestions_list.currentRow()
        if current_row >= 0:
            suggestions = self.get_workflow_suggestions()
            if current_row < len(suggestions):
                suggestion = suggestions[current_row]
                self.suggestion_selected.emit(suggestion.action_type, suggestion.parameters)