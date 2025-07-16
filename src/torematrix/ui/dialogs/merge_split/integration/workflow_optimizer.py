"""
Workflow Optimizer for Merge/Split Operations - Agent 4 Implementation.

Provides intelligent workflow optimization through user behavior analysis and suggestions.
"""

from typing import Dict, List, Optional, Any, Deque
from dataclasses import dataclass
from enum import Enum
from collections import deque, defaultdict, Counter
from datetime import datetime


class WorkflowStage(Enum):
    """Stages in the workflow process."""
    SELECTION = "selection"
    ANALYSIS = "analysis" 
    OPERATION = "operation"
    VALIDATION = "validation"
    OPTIMIZATION = "optimization"
    COMPLETION = "completion"


class UserSkillLevel(Enum):
    """User skill levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class UserAction:
    """Represents a user action in the workflow."""
    action_type: str
    context: Dict[str, Any] = None
    duration: float = 0.0
    success: bool = True
    timestamp: datetime = None
    workflow_stage: WorkflowStage = WorkflowStage.OPERATION
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class WorkflowPattern:
    """Represents a detected workflow pattern."""
    name: str
    actions: List[str] = None
    frequency: int = 0
    success_rate: float = 1.0
    average_duration: float = 0.0
    context_conditions: Dict[str, Any] = None
    skill_level: UserSkillLevel = UserSkillLevel.INTERMEDIATE
    
    def __post_init__(self):
        if self.actions is None:
            self.actions = []
        if self.context_conditions is None:
            self.context_conditions = {}
    
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
    parameters: Dict[str, Any] = None
    confidence: float = 0.0
    estimated_time_savings: float = 0.0
    pattern_match: Optional[WorkflowPattern] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class WorkflowMetrics:
    """Workflow performance metrics."""
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    average_action_duration: float = 0.0
    most_common_actions: List[tuple] = None
    error_patterns: List[str] = None
    efficiency_score: float = 0.0
    
    def __post_init__(self):
        if self.most_common_actions is None:
            self.most_common_actions = []
        if self.error_patterns is None:
            self.error_patterns = []
    
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
                    avg_duration = sum(a.duration for a in pattern_actions) / len(pattern_actions) if pattern_actions else 0
                    success_rate = sum(1 for a in pattern_actions if a.success) / len(pattern_actions) if pattern_actions else 1
                    
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
        self.context_analyzers = [
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


class WorkflowOptimizerWidget:
    """Widget for workflow optimization and user behavior analysis."""
    
    def __init__(self, state_manager=None, event_bus=None, parent=None):
        self.state_manager = state_manager
        self.event_bus = event_bus
        
        self.behavior_analyzer = UserBehaviorAnalyzer()
        self.suggestion_engine = WorkflowSuggestionEngine(self.behavior_analyzer)
        
        self.tab_widget = None  # Placeholder
        
        # Mock PyQt signals
        self.suggestion_selected = MockSignal()
    
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
        context = {}
        if self.state_manager:
            context = {
                "selected_elements": getattr(self.state_manager, 'get_selected_elements', lambda: [])(),
                "all_elements": getattr(self.state_manager, 'get_all_elements', lambda: [])()
            }
        
        return self.suggestion_engine.get_suggestions(context)
    
    def get_current_metrics(self) -> WorkflowMetrics:
        """Get current workflow metrics."""
        return self.behavior_analyzer.get_metrics()


class MockSignal:
    """Mock PyQt signal for testing."""
    
    def __init__(self):
        self.callbacks = []
    
    def connect(self, callback):
        self.callbacks.append(callback)
    
    def emit(self, *args):
        for callback in self.callbacks:
            callback(*args)