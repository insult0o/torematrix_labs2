"""AI-Powered Type Recommendation Engine

Intelligent recommendations for type management with:
- ML-based content analysis and type suggestions
- Pattern recognition and optimization recommendations
- Performance analysis and improvement suggestions
- Context-aware type selection and validation
"""

import logging
import re
import statistics
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Set, Union
import numpy as np
from collections import defaultdict, Counter
import datetime
import asyncio
import json

logger = logging.getLogger(__name__)


class RecommendationType(Enum):
    """Types of recommendations"""
    TYPE_SUGGESTION = "type_suggestion"
    OPTIMIZATION = "optimization"
    VALIDATION = "validation"
    PERFORMANCE = "performance"
    STRUCTURE = "structure"
    CONSISTENCY = "consistency"
    BEST_PRACTICE = "best_practice"


class ConfidenceLevel(Enum):
    """Confidence levels for recommendations"""
    VERY_LOW = "very_low"     # < 30%
    LOW = "low"               # 30-50%
    MEDIUM = "medium"         # 50-75%
    HIGH = "high"             # 75-90%
    VERY_HIGH = "very_high"   # > 90%


class Priority(Enum):
    """Recommendation priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ContentAnalysis:
    """Analysis results for content"""
    content_type: str
    detected_patterns: List[str] = field(default_factory=list)
    content_length: int = 0
    language: Optional[str] = None
    structure_complexity: str = "simple"  # simple, moderate, complex
    special_features: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Statistical analysis
    character_distribution: Dict[str, float] = field(default_factory=dict)
    word_frequency: Dict[str, int] = field(default_factory=dict)
    sentence_stats: Dict[str, float] = field(default_factory=dict)
    
    # Pattern analysis
    has_numbers: bool = False
    has_dates: bool = False
    has_urls: bool = False
    has_emails: bool = False
    has_code: bool = False
    has_formulas: bool = False
    has_tables: bool = False
    has_lists: bool = False


@dataclass
class TypeRecommendation:
    """A single type recommendation"""
    recommended_type: str
    confidence: float  # 0.0 to 1.0
    confidence_level: ConfidenceLevel
    priority: Priority
    recommendation_type: RecommendationType
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)
    
    # Supporting evidence
    evidence: List[str] = field(default_factory=list)
    patterns_matched: List[str] = field(default_factory=list)
    
    # Impact analysis
    expected_improvement: Optional[float] = None
    potential_issues: List[str] = field(default_factory=list)
    implementation_effort: str = "low"  # low, medium, high
    
    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)


@dataclass
class RecommendationContext:
    """Context for generating recommendations"""
    element_id: str
    current_type: Optional[str] = None
    content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    related_elements: List[str] = field(default_factory=list)
    document_context: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    historical_data: Dict[str, Any] = field(default_factory=dict)


class ContentAnalyzer:
    """Analyzes content to extract features for type recommendations"""
    
    def __init__(self):
        self.patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'url': re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'),
            'date': re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'),
            'time': re.compile(r'\b\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\b'),
            'number': re.compile(r'\b\d+(?:\.\d+)?\b'),
            'currency': re.compile(r'[$€£¥]\s*\d+(?:,\d{3})*(?:\.\d{2})?|\b\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP|JPY)\b'),
            'code': re.compile(r'(?:def\s+\w+|function\s+\w+|class\s+\w+|import\s+\w+|#include|<?xml|<html|<script)'),
            'formula': re.compile(r'[=]\s*[A-Z]+\d+|[∑∫∂]|\b(?:sum|integral|derivative)\b'),
            'table_marker': re.compile(r'\|.*\||\t.*\t|,.*,.*,'),
            'list_marker': re.compile(r'^\s*[-*•]\s+|^\s*\d+\.\s+', re.MULTILINE),
            'heading': re.compile(r'^#+\s+.*$|^.+\n[=-]+$', re.MULTILINE),
            'bold': re.compile(r'\*\*.*?\*\*|__.*?__|<b>.*?</b>'),
            'italic': re.compile(r'\*.*?\*|_.*?_|<i>.*?</i>'),
            'quote': re.compile(r'^>\s+.*$', re.MULTILINE),
        }
        
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'must', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him',
            'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }
    
    def analyze_content(self, content: str, context: Optional[RecommendationContext] = None) -> ContentAnalysis:
        """Perform comprehensive content analysis"""
        analysis = ContentAnalysis(
            content_type="unknown",
            content_length=len(content)
        )
        
        # Basic pattern detection
        self._detect_patterns(content, analysis)
        
        # Statistical analysis
        self._analyze_statistics(content, analysis)
        
        # Structure analysis
        self._analyze_structure(content, analysis)
        
        # Content type classification
        self._classify_content_type(analysis)
        
        # Language detection (simplified)
        self._detect_language(content, analysis)
        
        # Add context-specific analysis
        if context:
            self._analyze_context(content, context, analysis)
        
        return analysis
    
    def _detect_patterns(self, content: str, analysis: ContentAnalysis):
        """Detect various patterns in content"""
        detected_patterns = []
        
        for pattern_name, pattern in self.patterns.items():
            matches = pattern.findall(content)
            if matches:
                detected_patterns.append(pattern_name)
                analysis.metadata[f"{pattern_name}_count"] = len(matches)
                analysis.metadata[f"{pattern_name}_examples"] = matches[:3]  # Store first 3 examples
                
                # Set flags
                if pattern_name == 'email':
                    analysis.has_emails = True
                elif pattern_name == 'url':
                    analysis.has_urls = True
                elif pattern_name in ['date', 'time']:
                    analysis.has_dates = True
                elif pattern_name in ['number', 'currency']:
                    analysis.has_numbers = True
                elif pattern_name == 'code':
                    analysis.has_code = True
                elif pattern_name == 'formula':
                    analysis.has_formulas = True
                elif pattern_name == 'table_marker':
                    analysis.has_tables = True
                elif pattern_name == 'list_marker':
                    analysis.has_lists = True
        
        analysis.detected_patterns = detected_patterns
    
    def _analyze_statistics(self, content: str, analysis: ContentAnalysis):
        """Perform statistical analysis of content"""
        if not content:
            return
        
        # Character distribution
        char_count = Counter(content.lower())
        total_chars = len(content)
        analysis.character_distribution = {
            char: count / total_chars 
            for char, count in char_count.most_common(10)
        }
        
        # Word frequency analysis
        words = re.findall(r'\b\w+\b', content.lower())
        meaningful_words = [w for w in words if w not in self.stop_words and len(w) > 2]
        analysis.word_frequency = dict(Counter(meaningful_words).most_common(20))
        
        # Sentence statistics
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if sentences:
            sentence_lengths = [len(s.split()) for s in sentences]
            analysis.sentence_stats = {
                'count': len(sentences),
                'avg_length': statistics.mean(sentence_lengths),
                'max_length': max(sentence_lengths),
                'min_length': min(sentence_lengths),
                'median_length': statistics.median(sentence_lengths)
            }
        
        # Additional metrics
        analysis.metadata.update({
            'word_count': len(words),
            'unique_words': len(set(words)),
            'vocabulary_richness': len(set(words)) / max(len(words), 1),
            'avg_word_length': statistics.mean([len(w) for w in words]) if words else 0,
            'uppercase_ratio': sum(1 for c in content if c.isupper()) / max(len(content), 1),
            'digit_ratio': sum(1 for c in content if c.isdigit()) / max(len(content), 1),
            'punctuation_ratio': sum(1 for c in content if not c.isalnum() and not c.isspace()) / max(len(content), 1)
        })
    
    def _analyze_structure(self, content: str, analysis: ContentAnalysis):
        """Analyze content structure and complexity"""
        # Line analysis
        lines = content.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Paragraph analysis
        paragraphs = re.split(r'\n\s*\n', content)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        # Indentation analysis
        indented_lines = sum(1 for line in lines if line.startswith((' ', '\t')))
        
        # Structure features
        structure_features = []
        
        if analysis.has_lists:
            structure_features.append("lists")
        if analysis.has_tables:
            structure_features.append("tables")
        if 'heading' in analysis.detected_patterns:
            structure_features.append("headings")
        if 'quote' in analysis.detected_patterns:
            structure_features.append("quotes")
        if indented_lines > len(lines) * 0.2:
            structure_features.append("indentation")
        
        analysis.special_features = structure_features
        
        # Complexity assessment
        complexity_score = 0
        
        # Length-based complexity
        if len(content) > 1000:
            complexity_score += 1
        if len(paragraphs) > 5:
            complexity_score += 1
        
        # Structure-based complexity
        complexity_score += len(structure_features)
        
        # Pattern-based complexity
        if analysis.has_code:
            complexity_score += 2
        if analysis.has_formulas:
            complexity_score += 2
        if analysis.has_tables:
            complexity_score += 1
        
        # Vocabulary-based complexity
        vocab_richness = analysis.metadata.get('vocabulary_richness', 0)
        if vocab_richness > 0.7:
            complexity_score += 1
        
        # Assign complexity level
        if complexity_score <= 2:
            analysis.structure_complexity = "simple"
        elif complexity_score <= 5:
            analysis.structure_complexity = "moderate"
        else:
            analysis.structure_complexity = "complex"
        
        analysis.metadata.update({
            'line_count': len(lines),
            'paragraph_count': len(paragraphs),
            'indented_lines': indented_lines,
            'complexity_score': complexity_score
        })
    
    def _classify_content_type(self, analysis: ContentAnalysis):
        """Classify content type based on analysis"""
        # Rule-based classification
        patterns = analysis.detected_patterns
        features = analysis.special_features
        
        # Code content
        if analysis.has_code or 'code' in patterns:
            analysis.content_type = "code"
        
        # Table/data content
        elif analysis.has_tables or 'table_marker' in patterns:
            analysis.content_type = "table"
        
        # Mathematical content
        elif analysis.has_formulas or 'formula' in patterns:
            analysis.content_type = "formula"
        
        # List content
        elif analysis.has_lists and len(analysis.detected_patterns) <= 2:
            analysis.content_type = "list"
        
        # Title/heading content
        elif ('heading' in patterns and analysis.content_length < 200 and 
              analysis.metadata.get('line_count', 0) <= 3):
            analysis.content_type = "title"
        
        # Contact/address content
        elif analysis.has_emails or ('email' in patterns and 'url' in patterns):
            analysis.content_type = "contact"
        
        # Narrative/paragraph content
        elif (analysis.metadata.get('paragraph_count', 0) > 1 and 
              analysis.sentence_stats.get('count', 0) > 3):
            analysis.content_type = "paragraph"
        
        # Simple text
        elif analysis.content_length < 100 and analysis.sentence_stats.get('count', 0) <= 2:
            analysis.content_type = "text"
        
        # Default to text
        else:
            analysis.content_type = "text"
    
    def _detect_language(self, content: str, analysis: ContentAnalysis):
        """Simplified language detection"""
        # This is a very basic implementation
        # In production, you might use a proper language detection library
        
        # Simple character-based detection
        latin_chars = sum(1 for c in content if ord(c) < 256)
        total_chars = len(content)
        
        if total_chars > 0:
            latin_ratio = latin_chars / total_chars
            if latin_ratio > 0.9:
                analysis.language = "latin"  # English, etc.
            else:
                analysis.language = "non-latin"
        else:
            analysis.language = "unknown"
    
    def _analyze_context(self, content: str, context: RecommendationContext, analysis: ContentAnalysis):
        """Add context-specific analysis"""
        # Document context influence
        doc_context = context.document_context
        if doc_context.get('document_type') == 'technical':
            if analysis.has_code:
                analysis.special_features.append("technical_code")
        
        # Historical data influence
        historical = context.historical_data
        if historical.get('previous_types'):
            analysis.metadata['historical_types'] = historical['previous_types']
        
        # User preferences
        user_prefs = context.user_preferences
        if user_prefs.get('prefer_detailed_types'):
            analysis.metadata['user_prefers_detailed'] = True


class TypeSuggestionEngine:
    """Engine for suggesting appropriate types based on content analysis"""
    
    def __init__(self):
        self.type_rules = self._load_type_rules()
        self.content_analyzer = ContentAnalyzer()
        
        # Type scoring weights
        self.scoring_weights = {
            'pattern_match': 0.4,
            'content_type_match': 0.3,
            'structure_match': 0.2,
            'context_match': 0.1
        }
    
    def _load_type_rules(self) -> Dict[str, Dict[str, Any]]:
        """Load type suggestion rules"""
        return {
            'title': {
                'patterns': ['heading'],
                'content_types': ['title'],
                'max_length': 200,
                'max_lines': 3,
                'structure_features': [],
                'priority_keywords': ['title', 'header', 'heading', 'caption']
            },
            'paragraph': {
                'patterns': ['quote'],
                'content_types': ['paragraph'],
                'min_length': 100,
                'min_sentences': 3,
                'structure_features': ['quotes'],
                'priority_keywords': ['paragraph', 'body', 'content', 'text']
            },
            'list': {
                'patterns': ['list_marker'],
                'content_types': ['list'],
                'structure_features': ['lists'],
                'priority_keywords': ['list', 'bullet', 'item', 'enumeration']
            },
            'table': {
                'patterns': ['table_marker'],
                'content_types': ['table'],
                'structure_features': ['tables'],
                'priority_keywords': ['table', 'grid', 'matrix', 'data']
            },
            'formula': {
                'patterns': ['formula', 'number'],
                'content_types': ['formula'],
                'structure_features': [],
                'priority_keywords': ['formula', 'equation', 'calculation', 'math']
            },
            'code': {
                'patterns': ['code'],
                'content_types': ['code'],
                'structure_features': ['indentation'],
                'priority_keywords': ['code', 'script', 'program', 'function']
            },
            'image': {
                'patterns': ['url'],
                'content_types': [],
                'max_length': 500,
                'priority_keywords': ['image', 'picture', 'photo', 'figure', 'diagram']
            },
            'text': {
                'patterns': [],
                'content_types': ['text'],
                'structure_features': [],
                'priority_keywords': ['text', 'content']
            }
        }
    
    def suggest_types(self, content: str, context: RecommendationContext) -> List[TypeRecommendation]:
        """Generate type suggestions for content"""
        try:
            # Analyze content
            analysis = self.content_analyzer.analyze_content(content, context)
            
            # Generate suggestions for each possible type
            suggestions = []
            
            for type_name, rules in self.type_rules.items():
                score = self._calculate_type_score(analysis, rules, context)
                
                if score > 0.1:  # Minimum threshold
                    recommendation = self._create_type_recommendation(
                        type_name, score, analysis, rules, context
                    )
                    suggestions.append(recommendation)
            
            # Sort by confidence score
            suggestions.sort(key=lambda x: x.confidence, reverse=True)
            
            # Add ranking context
            for i, suggestion in enumerate(suggestions):
                suggestion.context['ranking'] = i + 1
                suggestion.context['total_suggestions'] = len(suggestions)
            
            return suggestions[:5]  # Return top 5 suggestions
            
        except Exception as e:
            logger.error(f"Error generating type suggestions: {e}")
            return []
    
    def _calculate_type_score(self, analysis: ContentAnalysis, rules: Dict[str, Any], 
                            context: RecommendationContext) -> float:
        """Calculate score for a specific type"""
        score = 0.0
        
        # Pattern matching score
        pattern_score = self._calculate_pattern_score(analysis, rules)
        score += pattern_score * self.scoring_weights['pattern_match']
        
        # Content type matching score
        content_type_score = self._calculate_content_type_score(analysis, rules)
        score += content_type_score * self.scoring_weights['content_type_match']
        
        # Structure matching score
        structure_score = self._calculate_structure_score(analysis, rules)
        score += structure_score * self.scoring_weights['structure_match']
        
        # Context matching score
        context_score = self._calculate_context_score(analysis, rules, context)
        score += context_score * self.scoring_weights['context_match']
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _calculate_pattern_score(self, analysis: ContentAnalysis, rules: Dict[str, Any]) -> float:
        """Calculate pattern matching score"""
        required_patterns = rules.get('patterns', [])
        if not required_patterns:
            return 0.5  # Neutral score for types without specific patterns
        
        matched_patterns = sum(1 for pattern in required_patterns 
                             if pattern in analysis.detected_patterns)
        
        return matched_patterns / len(required_patterns)
    
    def _calculate_content_type_score(self, analysis: ContentAnalysis, rules: Dict[str, Any]) -> float:
        """Calculate content type matching score"""
        target_types = rules.get('content_types', [])
        if not target_types:
            return 0.5  # Neutral score
        
        return 1.0 if analysis.content_type in target_types else 0.0
    
    def _calculate_structure_score(self, analysis: ContentAnalysis, rules: Dict[str, Any]) -> float:
        """Calculate structure matching score"""
        score = 0.0
        
        # Length constraints
        if 'max_length' in rules:
            if analysis.content_length <= rules['max_length']:
                score += 0.3
        
        if 'min_length' in rules:
            if analysis.content_length >= rules['min_length']:
                score += 0.3
        
        # Line constraints
        if 'max_lines' in rules:
            line_count = analysis.metadata.get('line_count', 0)
            if line_count <= rules['max_lines']:
                score += 0.2
        
        # Sentence constraints
        if 'min_sentences' in rules:
            sentence_count = analysis.sentence_stats.get('count', 0)
            if sentence_count >= rules['min_sentences']:
                score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_context_score(self, analysis: ContentAnalysis, rules: Dict[str, Any], 
                               context: RecommendationContext) -> float:
        """Calculate context-based score"""
        score = 0.0
        
        # Historical type preference
        historical_types = context.historical_data.get('previous_types', [])
        if historical_types:
            # Boost score if this type was used before
            type_name = next((k for k, v in self.type_rules.items() if v == rules), 'unknown')
            if type_name in historical_types:
                score += 0.3
        
        # Document context
        doc_context = context.document_context
        if doc_context.get('document_type') == 'technical' and 'code' in rules.get('patterns', []):
            score += 0.2
        
        # User preferences
        user_prefs = context.user_preferences
        if user_prefs.get('prefer_detailed_types') and len(rules.get('patterns', [])) > 1:
            score += 0.1
        
        return min(score, 1.0)
    
    def _create_type_recommendation(self, type_name: str, score: float, 
                                  analysis: ContentAnalysis, rules: Dict[str, Any],
                                  context: RecommendationContext) -> TypeRecommendation:
        """Create a type recommendation object"""
        # Convert score to confidence level
        if score >= 0.9:
            confidence_level = ConfidenceLevel.VERY_HIGH
            priority = Priority.HIGH
        elif score >= 0.75:
            confidence_level = ConfidenceLevel.HIGH
            priority = Priority.HIGH
        elif score >= 0.5:
            confidence_level = ConfidenceLevel.MEDIUM
            priority = Priority.MEDIUM
        elif score >= 0.3:
            confidence_level = ConfidenceLevel.LOW
            priority = Priority.LOW
        else:
            confidence_level = ConfidenceLevel.VERY_LOW
            priority = Priority.LOW
        
        # Generate reason and evidence
        reason, evidence = self._generate_explanation(type_name, analysis, rules, score)
        
        # Identify matched patterns
        patterns_matched = [p for p in rules.get('patterns', []) 
                          if p in analysis.detected_patterns]
        
        recommendation = TypeRecommendation(
            recommended_type=type_name,
            confidence=score,
            confidence_level=confidence_level,
            priority=priority,
            recommendation_type=RecommendationType.TYPE_SUGGESTION,
            reason=reason,
            evidence=evidence,
            patterns_matched=patterns_matched,
            context={
                'content_type': analysis.content_type,
                'structure_complexity': analysis.structure_complexity,
                'content_length': analysis.content_length,
                'special_features': analysis.special_features
            }
        )
        
        return recommendation
    
    def _generate_explanation(self, type_name: str, analysis: ContentAnalysis, 
                            rules: Dict[str, Any], score: float) -> Tuple[str, List[str]]:
        """Generate human-readable explanation for recommendation"""
        evidence = []
        
        # Pattern evidence
        matched_patterns = [p for p in rules.get('patterns', []) 
                          if p in analysis.detected_patterns]
        if matched_patterns:
            evidence.append(f"Detected patterns: {', '.join(matched_patterns)}")
        
        # Content type evidence
        if analysis.content_type in rules.get('content_types', []):
            evidence.append(f"Content classified as '{analysis.content_type}'")
        
        # Structure evidence
        if analysis.special_features:
            relevant_features = [f for f in analysis.special_features 
                               if f in rules.get('structure_features', [])]
            if relevant_features:
                evidence.append(f"Structure features: {', '.join(relevant_features)}")
        
        # Length evidence
        if 'max_length' in rules and analysis.content_length <= rules['max_length']:
            evidence.append(f"Content length ({analysis.content_length}) within expected range")
        
        # Generate main reason
        if score >= 0.8:
            reason = f"Strong match for '{type_name}' type based on content analysis"
        elif score >= 0.6:
            reason = f"Good match for '{type_name}' type with some supporting evidence"
        elif score >= 0.4:
            reason = f"Possible match for '{type_name}' type based on limited evidence"
        else:
            reason = f"Weak match for '{type_name}' type - consider alternatives"
        
        return reason, evidence


class TypeRecommendationEngine:
    """Main engine for AI-powered type recommendations"""
    
    def __init__(self):
        self.suggestion_engine = TypeSuggestionEngine()
        self.content_analyzer = ContentAnalyzer()
        
        # Cache for performance
        self.analysis_cache = {}
        self.recommendation_cache = {}
        
        logger.info("TypeRecommendationEngine initialized")
    
    async def get_recommendations(self, context: RecommendationContext) -> List[TypeRecommendation]:
        """Get comprehensive type recommendations"""
        try:
            recommendations = []
            
            # Get type suggestions
            type_suggestions = await self._get_type_suggestions(context)
            recommendations.extend(type_suggestions)
            
            # Get optimization recommendations
            optimization_recs = await self._get_optimization_recommendations(context)
            recommendations.extend(optimization_recs)
            
            # Get validation recommendations
            validation_recs = await self._get_validation_recommendations(context)
            recommendations.extend(validation_recs)
            
            # Sort by priority and confidence
            recommendations.sort(key=lambda r: (r.priority.value, -r.confidence))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error generating recommendations: {e}")
            return []
    
    async def _get_type_suggestions(self, context: RecommendationContext) -> List[TypeRecommendation]:
        """Get type suggestions based on content analysis"""
        cache_key = f"type_suggestions_{hash(context.content)}"
        
        if cache_key in self.recommendation_cache:
            return self.recommendation_cache[cache_key]
        
        # Generate suggestions
        suggestions = self.suggestion_engine.suggest_types(context.content, context)
        
        # Cache results
        self.recommendation_cache[cache_key] = suggestions
        
        return suggestions
    
    async def _get_optimization_recommendations(self, context: RecommendationContext) -> List[TypeRecommendation]:
        """Get optimization recommendations"""
        recommendations = []
        
        # Analyze content for optimization opportunities
        analysis = self.content_analyzer.analyze_content(context.content, context)
        
        # Complex content that might benefit from structure
        if (analysis.structure_complexity == "complex" and 
            context.current_type == "text"):
            
            rec = TypeRecommendation(
                recommended_type="paragraph" if analysis.content_type == "paragraph" else "structured_text",
                confidence=0.7,
                confidence_level=ConfidenceLevel.HIGH,
                priority=Priority.MEDIUM,
                recommendation_type=RecommendationType.OPTIMIZATION,
                reason="Complex content would benefit from more structured type",
                evidence=[
                    f"Content complexity: {analysis.structure_complexity}",
                    f"Special features: {', '.join(analysis.special_features)}"
                ],
                expected_improvement=0.3,
                implementation_effort="low"
            )
            recommendations.append(rec)
        
        # Performance recommendations for large content
        if analysis.content_length > 5000:
            rec = TypeRecommendation(
                recommended_type="optimized_text",
                confidence=0.6,
                confidence_level=ConfidenceLevel.MEDIUM,
                priority=Priority.LOW,
                recommendation_type=RecommendationType.PERFORMANCE,
                reason="Large content size may benefit from performance optimizations",
                evidence=[
                    f"Content length: {analysis.content_length} characters",
                    "Consider content chunking or lazy loading"
                ],
                expected_improvement=0.2,
                implementation_effort="medium"
            )
            recommendations.append(rec)
        
        return recommendations
    
    async def _get_validation_recommendations(self, context: RecommendationContext) -> List[TypeRecommendation]:
        """Get validation and consistency recommendations"""
        recommendations = []
        
        # Check for inconsistencies with related elements
        if context.related_elements:
            # This would analyze related elements for consistency
            # For now, we'll create a simple recommendation
            rec = TypeRecommendation(
                recommended_type=context.current_type or "consistent_type",
                confidence=0.5,
                confidence_level=ConfidenceLevel.MEDIUM,
                priority=Priority.INFO,
                recommendation_type=RecommendationType.CONSISTENCY,
                reason="Consider type consistency with related elements",
                evidence=[
                    f"Related elements: {len(context.related_elements)}",
                    "Type consistency improves document structure"
                ],
                implementation_effort="low"
            )
            recommendations.append(rec)
        
        return recommendations
    
    def analyze_content_features(self, content: str) -> ContentAnalysis:
        """Public method to analyze content features"""
        cache_key = f"analysis_{hash(content)}"
        
        if cache_key in self.analysis_cache:
            return self.analysis_cache[cache_key]
        
        analysis = self.content_analyzer.analyze_content(content)
        self.analysis_cache[cache_key] = analysis
        
        return analysis
    
    def get_supported_types(self) -> List[str]:
        """Get list of supported types for recommendations"""
        return list(self.suggestion_engine.type_rules.keys())
    
    def clear_cache(self):
        """Clear recommendation and analysis caches"""
        self.analysis_cache.clear()
        self.recommendation_cache.clear()
        logger.info("Recommendation caches cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        return {
            'analysis_cache_size': len(self.analysis_cache),
            'recommendation_cache_size': len(self.recommendation_cache)
        }


# Export main components
__all__ = [
    'RecommendationType',
    'ConfidenceLevel',
    'Priority',
    'ContentAnalysis',
    'TypeRecommendation', 
    'RecommendationContext',
    'ContentAnalyzer',
    'TypeSuggestionEngine',
    'TypeRecommendationEngine'
]