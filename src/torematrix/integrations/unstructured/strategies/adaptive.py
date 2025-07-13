"""
Adaptive strategy selection for optimal parsing performance.
"""

from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .base import ParsingStrategyBase, StrategyMetrics


class SelectionCriteria(Enum):
    """Criteria for strategy selection."""
    SPEED = "speed"           # Prioritize fastest processing
    QUALITY = "quality"       # Prioritize best extraction quality
    MEMORY = "memory"         # Prioritize low memory usage
    BALANCED = "balanced"     # Balance all factors


@dataclass
class StrategySelection:
    """Result of strategy selection process."""
    selected_strategy: ParsingStrategyBase
    selection_reason: str
    confidence_score: float
    alternatives: List[ParsingStrategyBase]


class AdaptiveStrategySelector:
    """Intelligent strategy selector based on document analysis and performance history."""
    
    def __init__(self, config=None, memory_manager=None):
        self.config = config
        self.memory_manager = memory_manager
        self.strategies: List[ParsingStrategyBase] = []
        self._selection_history: List[Dict[str, Any]] = []
    
    def register_strategy(self, strategy: ParsingStrategyBase) -> None:
        """Register a parsing strategy."""
        self.strategies.append(strategy)
    
    async def select_strategy(self, 
                            file_path: Path,
                            criteria: SelectionCriteria = SelectionCriteria.BALANCED,
                            constraints: Optional[Dict[str, Any]] = None) -> StrategySelection:
        """Select optimal strategy for given file and criteria."""
        
        if not self.strategies:
            raise ValueError("No strategies registered")
        
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        constraints = constraints or {}
        
        # Filter strategies that can handle the file
        capable_strategies = [
            strategy for strategy in self.strategies
            if strategy.can_handle(file_path, file_size_mb)
        ]
        
        if not capable_strategies:
            # Fallback to first strategy if none can explicitly handle it
            capable_strategies = [self.strategies[0]]
        
        # Score strategies based on criteria
        scored_strategies = []
        for strategy in capable_strategies:
            score = self._score_strategy(strategy, file_path, file_size_mb, criteria, constraints)
            scored_strategies.append((strategy, score))
        
        # Sort by score (highest first)
        scored_strategies.sort(key=lambda x: x[1], reverse=True)
        
        selected_strategy, best_score = scored_strategies[0]
        alternatives = [strategy for strategy, _ in scored_strategies[1:3]]  # Top 2 alternatives
        
        selection_reason = self._generate_selection_reason(
            selected_strategy, criteria, best_score, file_size_mb
        )
        
        # Record selection for learning
        self._selection_history.append({
            "file_path": str(file_path),
            "file_size_mb": file_size_mb,
            "criteria": criteria.value,
            "selected_strategy": selected_strategy.name,
            "score": best_score,
            "timestamp": __import__("time").time()
        })
        
        return StrategySelection(
            selected_strategy=selected_strategy,
            selection_reason=selection_reason,
            confidence_score=best_score,
            alternatives=alternatives
        )
    
    def _score_strategy(self, 
                       strategy: ParsingStrategyBase,
                       file_path: Path, 
                       file_size_mb: float,
                       criteria: SelectionCriteria,
                       constraints: Dict[str, Any]) -> float:
        """Score a strategy based on selection criteria."""
        
        base_score = 0.5  # Base score for capable strategies
        
        # Get strategy estimates
        estimates = strategy.estimate_resources(file_path, file_size_mb)
        performance_summary = strategy.get_performance_summary()
        
        # Apply criteria-based scoring
        if criteria == SelectionCriteria.SPEED:
            # Favor strategies with faster processing times
            if performance_summary.get("avg_processing_time", 0) > 0:
                # Lower time = higher score
                base_score += 0.3 / max(performance_summary["avg_processing_time"], 0.1)
            
            # Penalize high estimated time
            estimated_time = estimates.get("time_seconds", 5.0)
            base_score -= min(estimated_time * 0.02, 0.2)
        
        elif criteria == SelectionCriteria.MEMORY:
            # Favor strategies with lower memory usage
            estimated_memory = estimates.get("memory_mb", 100.0)
            base_score -= min(estimated_memory * 0.001, 0.3)
            
            # Check memory constraints
            memory_limit = constraints.get("memory_limit_mb", 2048)
            if estimated_memory > memory_limit:
                base_score -= 0.5  # Heavy penalty for exceeding limits
        
        elif criteria == SelectionCriteria.QUALITY:
            # Favor strategies with better extraction rates
            if performance_summary.get("avg_elements_extracted", 0) > 0:
                base_score += min(performance_summary["avg_elements_extracted"] * 0.01, 0.3)
        
        elif criteria == SelectionCriteria.BALANCED:
            # Balance all factors
            success_rate = performance_summary.get("success_rate", 0.5)
            base_score += success_rate * 0.2
            
            # Moderate penalties for resource usage
            estimated_time = estimates.get("time_seconds", 5.0)
            estimated_memory = estimates.get("memory_mb", 100.0)
            base_score -= min(estimated_time * 0.01, 0.1)
            base_score -= min(estimated_memory * 0.0005, 0.1)
        
        # Bonus for strategies with good historical performance
        if performance_summary.get("total_runs", 0) > 5:
            success_rate = performance_summary.get("success_rate", 0.5)
            base_score += (success_rate - 0.5) * 0.2
        
        # Apply constraints
        estimated_memory = estimates.get("memory_mb", 100.0)
        memory_limit = constraints.get("memory_limit_mb", 2048)
        if estimated_memory > memory_limit:
            base_score *= 0.3  # Heavy penalty for constraint violations
        
        return max(0.0, min(1.0, base_score))  # Clamp to [0, 1]
    
    def _generate_selection_reason(self, 
                                 strategy: ParsingStrategyBase,
                                 criteria: SelectionCriteria,
                                 score: float,
                                 file_size_mb: float) -> str:
        """Generate human-readable reason for strategy selection."""
        
        reasons = [
            f"Selected {strategy.name} (score: {score:.2f})"
        ]
        
        if criteria == SelectionCriteria.SPEED:
            reasons.append("optimized for speed")
        elif criteria == SelectionCriteria.MEMORY:
            reasons.append("optimized for low memory usage")
        elif criteria == SelectionCriteria.QUALITY:
            reasons.append("optimized for extraction quality")
        else:
            reasons.append("balanced optimization")
        
        if file_size_mb > 100:
            reasons.append(f"large file handling ({file_size_mb:.1f}MB)")
        elif file_size_mb < 1:
            reasons.append("small file processing")
        
        return " - ".join(reasons)
    
    def get_selection_statistics(self) -> Dict[str, Any]:
        """Get statistics on strategy selection patterns."""
        if not self._selection_history:
            return {"total_selections": 0}
        
        strategy_counts = {}
        criteria_counts = {}
        
        for selection in self._selection_history:
            strategy = selection["selected_strategy"]
            criteria = selection["criteria"]
            
            strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1
            criteria_counts[criteria] = criteria_counts.get(criteria, 0) + 1
        
        avg_score = sum(s["score"] for s in self._selection_history) / len(self._selection_history)
        
        return {
            "total_selections": len(self._selection_history),
            "strategy_distribution": strategy_counts,
            "criteria_distribution": criteria_counts,
            "average_confidence_score": avg_score,
            "registered_strategies": len(self.strategies)
        }