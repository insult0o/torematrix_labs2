"""Search Suggestions Engine

Real-time search suggestions and autocomplete with intelligent ranking,
typo correction, and popularity-based recommendations for enhanced
user search experience.
"""

import asyncio
import logging
import re
import time
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from difflib import SequenceMatcher
from heapq import nlargest

from torematrix.core.models.element import Element


logger = logging.getLogger(__name__)


@dataclass
class Suggestion:
    """A search suggestion with metadata"""
    text: str
    score: float
    suggestion_type: str  # 'completion', 'correction', 'popular', 'semantic'
    source: str = 'general'
    metadata: Dict[str, Any] = field(default_factory=dict)
    frequency: int = 0
    last_used: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Normalize score to 0-1 range"""
        self.score = max(0.0, min(1.0, self.score))


@dataclass
class SuggestionConfig:
    """Configuration for suggestion engine"""
    max_suggestions: int = 10
    min_query_length: int = 1
    max_query_length: int = 100
    response_timeout_ms: float = 50.0
    enable_typo_correction: bool = True
    enable_popularity_boost: bool = True
    enable_semantic_suggestions: bool = True
    typo_distance_threshold: int = 2
    popularity_decay_days: int = 30
    cache_size: int = 1000
    precompute_popular_queries: bool = True


@dataclass
class QueryStats:
    """Statistics for a search query"""
    query: str
    total_searches: int = 0
    successful_searches: int = 0
    last_searched: datetime = field(default_factory=datetime.now)
    average_result_count: float = 0.0
    user_selections: int = 0  # How often users select results from this query
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_searches == 0:
            return 0.0
        return (self.successful_searches / self.total_searches) * 100.0
    
    @property
    def popularity_score(self) -> float:
        """Calculate popularity score based on usage and success"""
        age_days = (datetime.now() - self.last_searched).days
        age_factor = max(0.1, 1.0 - (age_days / 365))  # Decay over year
        
        usage_score = min(1.0, self.total_searches / 100)  # Normalize to 100 searches
        success_factor = self.success_rate / 100.0
        selection_factor = min(1.0, self.user_selections / 10)  # Normalize to 10 selections
        
        return usage_score * success_factor * selection_factor * age_factor


class PopularityTracker:
    """Track and analyze query popularity patterns"""
    
    def __init__(self, decay_days: int = 30):
        """Initialize popularity tracker
        
        Args:
            decay_days: Days after which popularity decays
        """
        self.decay_days = decay_days
        self.query_stats: Dict[str, QueryStats] = {}
        self.query_patterns: Dict[str, Counter] = defaultdict(Counter)
        self.recent_queries: List[Tuple[str, datetime]] = []
        self.trending_queries: List[str] = []
        
    def record_search(self, 
                     query: str, 
                     result_count: int = 0,
                     user_selected: bool = False) -> None:
        """Record a search query
        
        Args:
            query: Search query
            result_count: Number of results returned
            user_selected: Whether user selected a result
        """
        query = query.strip().lower()
        
        if query not in self.query_stats:
            self.query_stats[query] = QueryStats(query=query)
        
        stats = self.query_stats[query]
        stats.total_searches += 1
        stats.last_searched = datetime.now()
        
        if result_count > 0:
            stats.successful_searches += 1
            # Update rolling average
            current_avg = stats.average_result_count
            total_successful = stats.successful_searches
            stats.average_result_count = (
                (current_avg * (total_successful - 1) + result_count) / total_successful
            )
        
        if user_selected:
            stats.user_selections += 1
        
        # Track recent queries for trending analysis
        self.recent_queries.append((query, datetime.now()))
        
        # Keep only recent queries (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.recent_queries = [
            (q, t) for q, t in self.recent_queries if t > cutoff_time
        ]
        
        # Update trending queries periodically
        if len(self.recent_queries) % 10 == 0:  # Every 10 queries
            self._update_trending_queries()
    
    def get_popular_queries(self, limit: int = 10) -> List[Tuple[str, float]]:
        """Get most popular queries with scores
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of (query, popularity_score) tuples
        """
        # Calculate popularity scores
        scored_queries = []
        for query, stats in self.query_stats.items():
            score = stats.popularity_score
            if score > 0:
                scored_queries.append((query, score))
        
        # Sort by popularity score
        scored_queries.sort(key=lambda x: x[1], reverse=True)
        
        return scored_queries[:limit]
    
    def get_trending_queries(self, limit: int = 5) -> List[str]:
        """Get currently trending queries
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of trending query strings
        """
        return self.trending_queries[:limit]
    
    def get_query_completions(self, prefix: str, limit: int = 10) -> List[str]:
        """Get query completions based on popular queries
        
        Args:
            prefix: Query prefix to complete
            limit: Maximum completions to return
            
        Returns:
            List of completion strings
        """
        prefix = prefix.strip().lower()
        if not prefix:
            return []
        
        completions = []
        for query in self.query_stats.keys():
            if query.startswith(prefix) and query != prefix:
                stats = self.query_stats[query]
                completions.append((query, stats.popularity_score))
        
        # Sort by popularity and return
        completions.sort(key=lambda x: x[1], reverse=True)
        return [query for query, _ in completions[:limit]]
    
    def cleanup_old_queries(self) -> None:
        """Remove old query statistics"""
        cutoff_date = datetime.now() - timedelta(days=self.decay_days * 2)
        
        old_queries = [
            query for query, stats in self.query_stats.items()
            if stats.last_searched < cutoff_date
        ]
        
        for query in old_queries:
            del self.query_stats[query]
        
        if old_queries:
            logger.info(f"Cleaned up {len(old_queries)} old query statistics")
    
    def _update_trending_queries(self) -> None:
        """Update list of trending queries based on recent activity"""
        # Count queries in recent time window
        recent_counts = Counter()
        for query, timestamp in self.recent_queries:
            recent_counts[query] += 1
        
        # Get queries with significant recent activity
        trending = []
        for query, count in recent_counts.most_common(10):
            # Only consider trending if it has reasonable activity
            if count >= 2:
                trending.append(query)
        
        self.trending_queries = trending


class TypoCorrector:
    """Intelligent typo correction for search queries"""
    
    def __init__(self, max_distance: int = 2):
        """Initialize typo corrector
        
        Args:
            max_distance: Maximum edit distance for corrections
        """
        self.max_distance = max_distance
        self.word_frequency: Counter = Counter()
        self.common_patterns: Dict[str, str] = {}
        self._build_common_patterns()
        
    def add_vocabulary(self, words: List[str]) -> None:
        """Add words to correction vocabulary
        
        Args:
            words: List of words to add
        """
        for word in words:
            word = word.strip().lower()
            if word:
                self.word_frequency[word] += 1
    
    def suggest_corrections(self, query: str, limit: int = 5) -> List[Tuple[str, float]]:
        """Suggest typo corrections for query
        
        Args:
            query: Query to correct
            limit: Maximum corrections to return
            
        Returns:
            List of (correction, confidence) tuples
        """
        query = query.strip().lower()
        words = query.split()
        
        if not words:
            return []
        
        # Generate corrections for each word
        all_corrections = []
        
        for word in words:
            corrections = self._get_word_corrections(word)
            
            # If no corrections found, keep original word
            if not corrections:
                corrections = [(word, 1.0)]
            
            all_corrections.append(corrections)
        
        # Combine word corrections into full query corrections
        query_corrections = self._combine_corrections(words, all_corrections)
        
        # Filter out original query and sort by confidence
        query_corrections = [
            (correction, confidence) for correction, confidence in query_corrections
            if correction != query
        ]
        
        query_corrections.sort(key=lambda x: x[1], reverse=True)
        
        return query_corrections[:limit]
    
    def _get_word_corrections(self, word: str) -> List[Tuple[str, float]]:
        """Get corrections for a single word
        
        Args:
            word: Word to correct
            
        Returns:
            List of (correction, confidence) tuples
        """
        if not word:
            return []
        
        # Check if word is already correct (in vocabulary)
        if word in self.word_frequency:
            return [(word, 1.0)]
        
        # Check common pattern corrections first
        pattern_correction = self._apply_common_patterns(word)
        if pattern_correction and pattern_correction != word:
            if pattern_correction in self.word_frequency:
                return [(pattern_correction, 0.9)]
        
        # Generate edit distance corrections
        corrections = []
        
        for vocab_word in self.word_frequency:
            distance = self._edit_distance(word, vocab_word)
            
            if distance <= self.max_distance:
                # Calculate confidence based on edit distance and frequency
                confidence = self._calculate_correction_confidence(
                    word, vocab_word, distance
                )
                corrections.append((vocab_word, confidence))
        
        # Sort by confidence and return top candidates
        corrections.sort(key=lambda x: x[1], reverse=True)
        return corrections[:5]
    
    def _combine_corrections(self, 
                           original_words: List[str], 
                           word_corrections: List[List[Tuple[str, float]]]) -> List[Tuple[str, float]]:
        """Combine individual word corrections into full query corrections
        
        Args:
            original_words: Original words in query
            word_corrections: Corrections for each word
            
        Returns:
            List of (corrected_query, confidence) tuples
        """
        if not word_corrections:
            return []
        
        # For simplicity, take best correction for each word
        # In a more sophisticated implementation, this would generate
        # all combinations up to a reasonable limit
        
        corrected_words = []
        total_confidence = 1.0
        
        for i, corrections in enumerate(word_corrections):
            if corrections:
                best_word, confidence = corrections[0]
                corrected_words.append(best_word)
                total_confidence *= confidence
            else:
                corrected_words.append(original_words[i])
                total_confidence *= 0.5  # Penalty for no correction found
        
        corrected_query = ' '.join(corrected_words)
        return [(corrected_query, total_confidence)]
    
    def _edit_distance(self, word1: str, word2: str) -> int:
        """Calculate Levenshtein edit distance between two words
        
        Args:
            word1: First word
            word2: Second word
            
        Returns:
            Edit distance
        """
        m, n = len(word1), len(word2)
        
        # Create DP table
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        
        # Initialize base cases
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        
        # Fill DP table
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if word1[i-1] == word2[j-1]:
                    dp[i][j] = dp[i-1][j-1]
                else:
                    dp[i][j] = 1 + min(
                        dp[i-1][j],    # deletion
                        dp[i][j-1],    # insertion
                        dp[i-1][j-1]   # substitution
                    )
        
        return dp[m][n]
    
    def _calculate_correction_confidence(self, 
                                       original: str, 
                                       correction: str, 
                                       distance: int) -> float:
        """Calculate confidence score for a correction
        
        Args:
            original: Original word
            correction: Corrected word
            distance: Edit distance
            
        Returns:
            Confidence score (0-1)
        """
        # Base confidence decreases with edit distance
        distance_penalty = 0.8 ** distance
        
        # Boost confidence for more frequent words
        frequency = self.word_frequency.get(correction, 1)
        frequency_boost = min(1.2, 1.0 + (frequency / 100))
        
        # Boost confidence for similar length words
        length_diff = abs(len(original) - len(correction))
        length_penalty = 0.9 ** length_diff
        
        confidence = distance_penalty * frequency_boost * length_penalty
        
        return min(1.0, confidence)
    
    def _apply_common_patterns(self, word: str) -> str:
        """Apply common typo patterns
        
        Args:
            word: Word to correct
            
        Returns:
            Corrected word
        """
        for pattern, replacement in self.common_patterns.items():
            if pattern in word:
                return word.replace(pattern, replacement)
        
        return word
    
    def _build_common_patterns(self) -> None:
        """Build common typo correction patterns"""
        self.common_patterns = {
            # Common letter substitutions
            'teh': 'the',
            'adn': 'and',
            'taht': 'that',
            'woudl': 'would',
            'coudl': 'could',
            'shoudl': 'should',
            
            # Common letter swaps
            'recieve': 'receive',
            'beleive': 'believe',
            'seperate': 'separate',
            'occured': 'occurred',
            
            # Double letters
            'comming': 'coming',
            'runing': 'running',
            'stoping': 'stopping',
        }


class SearchSuggestionEngine:
    """Real-time search suggestions and autocomplete engine"""
    
    def __init__(self, config: Optional[SuggestionConfig] = None):
        """Initialize suggestion engine
        
        Args:
            config: Suggestion configuration
        """
        self.config = config or SuggestionConfig()
        self.popularity_tracker = PopularityTracker(self.config.popularity_decay_days)
        self.typo_corrector = TypoCorrector(self.config.typo_distance_threshold)
        
        # Caching
        self.suggestion_cache: Dict[str, Tuple[List[Suggestion], float]] = {}
        self.completion_cache: Dict[str, Tuple[List[str], float]] = {}
        
        # Element content for semantic suggestions
        self.element_terms: Set[str] = set()
        self.element_phrases: Dict[str, int] = Counter()
        
        # Performance tracking
        self.response_times: List[float] = []
        self.cache_hit_ratio = 0.0
        self.total_requests = 0
        self.cache_hits = 0
        
        logger.info("SearchSuggestionEngine initialized")
    
    async def get_suggestions(self, 
                            partial_query: str, 
                            limit: int = None) -> List[Suggestion]:
        """Get search suggestions for partial query (<50ms target)
        
        Args:
            partial_query: Partial search query
            limit: Maximum suggestions to return
            
        Returns:
            List of Suggestion objects
        """
        start_time = time.time()
        limit = limit or self.config.max_suggestions
        
        try:
            # Validate input
            partial_query = partial_query.strip()
            if (len(partial_query) < self.config.min_query_length or
                len(partial_query) > self.config.max_query_length):
                return []
            
            self.total_requests += 1
            
            # Check cache first
            cache_key = f"{partial_query}:{limit}"
            if cache_key in self.suggestion_cache:
                cached_suggestions, cache_time = self.suggestion_cache[cache_key]
                
                # Use cache if not too old (5 minutes)
                if time.time() - cache_time < 300:
                    self.cache_hits += 1
                    return cached_suggestions[:limit]
            
            # Generate suggestions
            suggestions = await self._generate_suggestions(partial_query, limit)
            
            # Cache results
            self.suggestion_cache[cache_key] = (suggestions, time.time())
            
            # Cleanup cache if too large
            if len(self.suggestion_cache) > self.config.cache_size:
                await self._cleanup_cache()
            
            return suggestions[:limit]
        
        finally:
            # Track response time
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            self.response_times.append(response_time)
            
            # Keep only recent response times
            if len(self.response_times) > 100:
                self.response_times = self.response_times[-100:]
            
            # Update cache hit ratio
            self.cache_hit_ratio = self.cache_hits / max(1, self.total_requests)
    
    async def get_completions(self, partial_query: str) -> List[str]:
        """Get query completions based on history and popularity
        
        Args:
            partial_query: Partial query to complete
            
        Returns:
            List of completion strings
        """
        partial_query = partial_query.strip().lower()
        
        # Check completion cache
        if partial_query in self.completion_cache:
            cached_completions, cache_time = self.completion_cache[partial_query]
            if time.time() - cache_time < 300:  # 5 minute cache
                return cached_completions
        
        # Get completions from popularity tracker
        completions = self.popularity_tracker.get_query_completions(
            partial_query, 
            self.config.max_suggestions
        )
        
        # Add element-based completions
        element_completions = self._get_element_completions(partial_query)
        completions.extend(element_completions)
        
        # Remove duplicates and sort
        unique_completions = list(dict.fromkeys(completions))  # Preserve order
        
        # Cache results
        self.completion_cache[partial_query] = (unique_completions, time.time())
        
        return unique_completions[:self.config.max_suggestions]
    
    async def correct_typos(self, query: str) -> List[str]:
        """Suggest typo corrections
        
        Args:
            query: Query to correct
            
        Returns:
            List of corrected query strings
        """
        if not self.config.enable_typo_correction:
            return []
        
        corrections = self.typo_corrector.suggest_corrections(
            query, 
            self.config.max_suggestions
        )
        
        return [correction for correction, _ in corrections]
    
    def update_popularity(self, 
                         query: str, 
                         results_count: int,
                         user_selected: bool = False) -> None:
        """Update query popularity for better suggestions
        
        Args:
            query: Search query
            results_count: Number of results returned
            user_selected: Whether user selected a result
        """
        self.popularity_tracker.record_search(
            query, 
            results_count, 
            user_selected
        )
        
        # Clear related cache entries
        self._invalidate_cache_for_query(query)
    
    def add_element_content(self, elements: List[Element]) -> None:
        """Add element content for semantic suggestions
        
        Args:
            elements: List of elements to extract terms from
        """
        for element in elements:
            # Extract individual terms
            words = re.findall(r'\b\w+\b', element.text.lower())
            for word in words:
                if len(word) >= 3:  # Ignore very short words
                    self.element_terms.add(word)
            
            # Extract phrases (2-3 words)
            for i in range(len(words) - 1):
                phrase = ' '.join(words[i:i+2])
                if len(phrase) >= 6:  # Reasonable phrase length
                    self.element_phrases[phrase] += 1
                
                if i < len(words) - 2:
                    phrase3 = ' '.join(words[i:i+3])
                    if len(phrase3) >= 10:
                        self.element_phrases[phrase3] += 1
        
        # Update typo corrector vocabulary
        self.typo_corrector.add_vocabulary(list(self.element_terms))
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get suggestion engine performance statistics
        
        Returns:
            Dictionary with performance statistics
        """
        avg_response_time = 0.0
        if self.response_times:
            avg_response_time = sum(self.response_times) / len(self.response_times)
        
        return {
            'total_requests': self.total_requests,
            'cache_hits': self.cache_hits,
            'cache_hit_ratio': self.cache_hit_ratio,
            'average_response_time_ms': avg_response_time,
            'suggestion_cache_size': len(self.suggestion_cache),
            'completion_cache_size': len(self.completion_cache),
            'vocabulary_size': len(self.element_terms),
            'tracked_queries': len(self.popularity_tracker.query_stats),
            'trending_queries': len(self.popularity_tracker.trending_queries)
        }
    
    async def _generate_suggestions(self, 
                                  partial_query: str, 
                                  limit: int) -> List[Suggestion]:
        """Generate all types of suggestions for partial query
        
        Args:
            partial_query: Partial query string
            limit: Maximum suggestions to generate
            
        Returns:
            List of Suggestion objects
        """
        suggestions = []
        
        # 1. Query completions (highest priority)
        completions = self.popularity_tracker.get_query_completions(
            partial_query, limit // 2
        )
        
        for completion in completions:
            stats = self.popularity_tracker.query_stats.get(completion)
            score = stats.popularity_score if stats else 0.5
            
            suggestions.append(Suggestion(
                text=completion,
                score=score,
                suggestion_type='completion',
                source='history',
                frequency=stats.total_searches if stats else 0
            ))
        
        # 2. Typo corrections (if enabled)
        if self.config.enable_typo_correction:
            corrections = self.typo_corrector.suggest_corrections(
                partial_query, 
                max(1, limit // 4)
            )
            
            for correction, confidence in corrections:
                suggestions.append(Suggestion(
                    text=correction,
                    score=confidence * 0.8,  # Slightly lower than completions
                    suggestion_type='correction',
                    source='typo_corrector'
                ))
        
        # 3. Popular queries (trending)
        if self.config.enable_popularity_boost:
            trending = self.popularity_tracker.get_trending_queries(limit // 4)
            
            for trending_query in trending:
                if partial_query.lower() in trending_query.lower():
                    suggestions.append(Suggestion(
                        text=trending_query,
                        score=0.7,
                        suggestion_type='popular',
                        source='trending'
                    ))
        
        # 4. Semantic suggestions from element content
        if self.config.enable_semantic_suggestions:
            semantic_suggestions = self._get_semantic_suggestions(
                partial_query, 
                limit // 4
            )
            suggestions.extend(semantic_suggestions)
        
        # Remove duplicates and sort by score
        unique_suggestions = {}
        for suggestion in suggestions:
            if suggestion.text not in unique_suggestions:
                unique_suggestions[suggestion.text] = suggestion
            else:
                # Keep suggestion with higher score
                existing = unique_suggestions[suggestion.text]
                if suggestion.score > existing.score:
                    unique_suggestions[suggestion.text] = suggestion
        
        final_suggestions = list(unique_suggestions.values())
        final_suggestions.sort(key=lambda s: s.score, reverse=True)
        
        return final_suggestions
    
    def _get_element_completions(self, partial_query: str) -> List[str]:
        """Get completions based on element content
        
        Args:
            partial_query: Partial query
            
        Returns:
            List of completion strings
        """
        completions = []
        partial_lower = partial_query.lower()
        
        # Check element terms
        for term in self.element_terms:
            if term.startswith(partial_lower) and term != partial_lower:
                completions.append(term)
        
        # Check element phrases
        for phrase in self.element_phrases:
            if phrase.startswith(partial_lower) and phrase != partial_lower:
                completions.append(phrase)
        
        return completions[:5]
    
    def _get_semantic_suggestions(self, 
                                partial_query: str, 
                                limit: int) -> List[Suggestion]:
        """Get semantic suggestions based on element content
        
        Args:
            partial_query: Partial query
            limit: Maximum suggestions
            
        Returns:
            List of semantic suggestions
        """
        suggestions = []
        partial_lower = partial_query.lower()
        
        # Find related terms and phrases
        related_terms = []
        
        for term in self.element_terms:
            if partial_lower in term or term in partial_lower:
                similarity = SequenceMatcher(None, partial_lower, term).ratio()
                if similarity > 0.3:  # Minimum similarity threshold
                    related_terms.append((term, similarity))
        
        # Sort by similarity and convert to suggestions
        related_terms.sort(key=lambda x: x[1], reverse=True)
        
        for term, similarity in related_terms[:limit]:
            suggestions.append(Suggestion(
                text=term,
                score=similarity * 0.6,  # Lower than direct completions
                suggestion_type='semantic',
                source='element_content'
            ))
        
        return suggestions
    
    def _invalidate_cache_for_query(self, query: str) -> None:
        """Invalidate cache entries related to a query
        
        Args:
            query: Query that was just used
        """
        query_lower = query.lower()
        
        # Find and remove related cache entries
        cache_keys_to_remove = []
        
        for cache_key in self.suggestion_cache:
            cached_query = cache_key.split(':')[0].lower()
            if query_lower.startswith(cached_query) or cached_query.startswith(query_lower):
                cache_keys_to_remove.append(cache_key)
        
        for key in cache_keys_to_remove:
            del self.suggestion_cache[key]
    
    async def _cleanup_cache(self) -> None:
        """Clean up old cache entries"""
        current_time = time.time()
        
        # Remove old suggestion cache entries
        old_suggestion_keys = []
        for key, (suggestions, cache_time) in self.suggestion_cache.items():
            if current_time - cache_time > 600:  # 10 minutes
                old_suggestion_keys.append(key)
        
        for key in old_suggestion_keys:
            del self.suggestion_cache[key]
        
        # Remove old completion cache entries
        old_completion_keys = []
        for key, (completions, cache_time) in self.completion_cache.items():
            if current_time - cache_time > 600:  # 10 minutes
                old_completion_keys.append(key)
        
        for key in old_completion_keys:
            del self.completion_cache[key]
        
        # Cleanup popularity tracker
        self.popularity_tracker.cleanup_old_queries()


# Utility functions
def create_suggestion_engine(enable_all_features: bool = True) -> SearchSuggestionEngine:
    """Create suggestion engine with default configuration
    
    Args:
        enable_all_features: Whether to enable all features
        
    Returns:
        Configured SearchSuggestionEngine
    """
    config = SuggestionConfig(
        enable_typo_correction=enable_all_features,
        enable_popularity_boost=enable_all_features,
        enable_semantic_suggestions=enable_all_features
    )
    return SearchSuggestionEngine(config)


def create_fast_suggestion_engine() -> SearchSuggestionEngine:
    """Create suggestion engine optimized for speed
    
    Returns:
        Speed-optimized SearchSuggestionEngine
    """
    config = SuggestionConfig(
        max_suggestions=5,
        response_timeout_ms=25.0,
        enable_typo_correction=False,  # Disable for speed
        enable_semantic_suggestions=False,  # Disable for speed
        cache_size=500,  # Smaller cache
        precompute_popular_queries=True
    )
    return SearchSuggestionEngine(config)