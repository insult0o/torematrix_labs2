"""Search Result Highlighting System

Advanced highlighting system for search terms in results with
configurable styles, multi-term support, and performance optimization.
"""

import re
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from html import escape
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QTextCharFormat, QColor, QFont

from torematrix.core.models.element import Element

logger = logging.getLogger(__name__)


class HighlightMode(Enum):
    """Highlighting modes"""
    EXACT = "exact"
    WORD_BOUNDARY = "word_boundary"
    FUZZY = "fuzzy"
    REGEX = "regex"


class HighlightStyle(Enum):
    """Predefined highlight styles"""
    DEFAULT = "default"
    BOLD = "bold"
    UNDERLINE = "underline"
    BACKGROUND = "background"
    BORDER = "border"
    CUSTOM = "custom"


@dataclass
class HighlightConfig:
    """Configuration for highlighting behavior"""
    mode: HighlightMode = HighlightMode.WORD_BOUNDARY
    case_sensitive: bool = False
    whole_words_only: bool = False
    max_highlights_per_element: int = 50
    context_chars: int = 100
    enable_html_output: bool = True
    enable_text_output: bool = True
    
    # Style configuration
    background_color: str = "#ffff99"  # Light yellow
    text_color: str = "#000000"        # Black
    font_weight: str = "bold"
    text_decoration: str = "none"
    border: str = "1px solid #ff9900"
    border_radius: str = "2px"
    padding: str = "1px 2px"
    
    # Advanced options
    fade_previous_highlights: bool = True
    animate_new_highlights: bool = False
    show_match_count: bool = True
    group_consecutive_matches: bool = True


@dataclass 
class HighlightMatch:
    """Represents a single highlight match"""
    start_pos: int
    end_pos: int
    matched_text: str
    search_term: str
    confidence: float = 1.0
    context_before: str = ""
    context_after: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'start_pos': self.start_pos,
            'end_pos': self.end_pos,
            'matched_text': self.matched_text,
            'search_term': self.search_term,
            'confidence': self.confidence,
            'context_before': self.context_before,
            'context_after': self.context_after
        }


@dataclass
class HighlightedElement:
    """Element with highlighted content"""
    element: Element
    original_text: str
    highlighted_html: str
    highlighted_text: str
    matches: List[HighlightMatch] = field(default_factory=list)
    total_matches: int = 0
    search_terms: List[str] = field(default_factory=list)
    
    def get_match_summary(self) -> str:
        """Get summary of matches found"""
        if self.total_matches == 0:
            return "No matches"
        elif self.total_matches == 1:
            return "1 match"
        else:
            return f"{self.total_matches} matches"
    
    def get_first_match_context(self) -> str:
        """Get context around first match"""
        if not self.matches:
            return ""
        
        first_match = self.matches[0]
        return f"...{first_match.context_before}{first_match.matched_text}{first_match.context_after}..."


class SearchHighlighter(QObject):
    """Advanced search result highlighting system"""
    
    # Signals
    highlighting_started = pyqtSignal(int)  # total_elements
    highlighting_progress = pyqtSignal(int, int)  # current, total
    highlighting_completed = pyqtSignal(list)  # List[HighlightedElement]
    
    def __init__(self, config: Optional[HighlightConfig] = None):
        super().__init__()
        
        self.config = config or HighlightConfig()
        self._compiled_patterns: Dict[str, re.Pattern] = {}
        self._style_cache: Dict[str, str] = {}
        
        # Performance tracking
        self._total_elements = 0
        self._processed_elements = 0
        
        logger.debug("SearchHighlighter initialized")
    
    def set_config(self, config: HighlightConfig):
        """Update highlighting configuration"""
        self.config = config
        self._compiled_patterns.clear()
        self._style_cache.clear()
        logger.debug("Highlighting configuration updated")
    
    def highlight_elements(self, elements: List[Element], search_terms: List[str]) -> List[HighlightedElement]:
        """Highlight search terms in multiple elements"""
        if not elements or not search_terms:
            return []
        
        self._total_elements = len(elements)
        self._processed_elements = 0
        
        self.highlighting_started.emit(self._total_elements)
        
        highlighted_elements = []
        
        for element in elements:
            try:
                highlighted = self.highlight_element(element, search_terms)
                if highlighted:
                    highlighted_elements.append(highlighted)
                
                self._processed_elements += 1
                self.highlighting_progress.emit(self._processed_elements, self._total_elements)
                
            except Exception as e:
                logger.warning(f"Error highlighting element {element.element_id}: {e}")
                continue
        
        self.highlighting_completed.emit(highlighted_elements)
        logger.info(f"Highlighted {len(highlighted_elements)} elements with terms: {search_terms}")
        
        return highlighted_elements
    
    def highlight_element(self, element: Element, search_terms: List[str]) -> Optional[HighlightedElement]:
        """Highlight search terms in a single element"""
        try:
            # Get text content to highlight
            text_content = self._extract_text_content(element)
            if not text_content.strip():
                return None
            
            # Find all matches
            all_matches = []
            for term in search_terms:
                matches = self._find_matches(text_content, term)
                all_matches.extend(matches)
            
            if not all_matches:
                return None
            
            # Sort matches by position and remove overlaps
            sorted_matches = self._process_matches(all_matches)
            
            # Limit matches if configured
            if self.config.max_highlights_per_element > 0:
                sorted_matches = sorted_matches[:self.config.max_highlights_per_element]
            
            # Generate highlighted content
            highlighted_html = self._generate_html_highlights(text_content, sorted_matches)
            highlighted_text = self._generate_text_highlights(text_content, sorted_matches)
            
            # Create highlighted element
            highlighted_element = HighlightedElement(
                element=element,
                original_text=text_content,
                highlighted_html=highlighted_html,
                highlighted_text=highlighted_text,
                matches=sorted_matches,
                total_matches=len(sorted_matches),
                search_terms=search_terms.copy()
            )
            
            return highlighted_element
            
        except Exception as e:
            logger.error(f"Error highlighting element {element.element_id}: {e}")
            return None
    
    def highlight_text(self, text: str, search_terms: List[str], output_html: bool = True) -> str:
        """Highlight search terms in plain text"""
        if not text or not search_terms:
            return text
        
        try:
            # Find all matches
            all_matches = []
            for term in search_terms:
                matches = self._find_matches(text, term)
                all_matches.extend(matches)
            
            if not all_matches:
                return text
            
            # Process matches
            sorted_matches = self._process_matches(all_matches)
            
            # Generate output
            if output_html:
                return self._generate_html_highlights(text, sorted_matches)
            else:
                return self._generate_text_highlights(text, sorted_matches)
                
        except Exception as e:
            logger.error(f"Error highlighting text: {e}")
            return text
    
    def clear_highlights(self, text: str) -> str:
        """Remove all highlighting from text"""
        try:
            # Remove HTML highlight tags
            clean_text = re.sub(r'<mark[^>]*>', '', text)
            clean_text = re.sub(r'</mark>', '', clean_text)
            
            # Remove other highlight markers
            clean_text = re.sub(r'\*\*([^*]+)\*\*', r'\1', clean_text)  # **highlighted**
            clean_text = re.sub(r'__([^_]+)__', r'\1', clean_text)      # __highlighted__
            
            return clean_text
            
        except Exception as e:
            logger.error(f"Error clearing highlights: {e}")
            return text
    
    def get_highlight_statistics(self, highlighted_elements: List[HighlightedElement]) -> Dict[str, Any]:
        """Get statistics about highlighting results"""
        if not highlighted_elements:
            return {
                'total_elements': 0,
                'elements_with_matches': 0,
                'total_matches': 0,
                'average_matches_per_element': 0.0,
                'terms_found': [],
                'match_distribution': {}
            }
        
        total_matches = sum(elem.total_matches for elem in highlighted_elements)
        elements_with_matches = len(highlighted_elements)
        
        # Count matches per term
        term_counts = {}
        for elem in highlighted_elements:
            for match in elem.matches:
                term = match.search_term
                term_counts[term] = term_counts.get(term, 0) + 1
        
        # Match count distribution
        match_counts = [elem.total_matches for elem in highlighted_elements]
        distribution = {}
        for count in match_counts:
            distribution[count] = distribution.get(count, 0) + 1
        
        return {
            'total_elements': len(highlighted_elements),
            'elements_with_matches': elements_with_matches,
            'total_matches': total_matches,
            'average_matches_per_element': total_matches / elements_with_matches if elements_with_matches > 0 else 0.0,
            'terms_found': list(term_counts.keys()),
            'term_match_counts': term_counts,
            'match_distribution': distribution,
            'min_matches': min(match_counts) if match_counts else 0,
            'max_matches': max(match_counts) if match_counts else 0
        }
    
    def update_highlight_style(self, style_updates: Dict[str, str]):
        """Update highlight style configuration"""
        for key, value in style_updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # Clear style cache to force regeneration
        self._style_cache.clear()
        logger.debug(f"Updated highlight styles: {style_updates}")
    
    def get_predefined_styles(self) -> Dict[str, Dict[str, str]]:
        """Get predefined highlight styles"""
        return {
            'default': {
                'background_color': '#ffff99',
                'text_color': '#000000',
                'font_weight': 'bold',
                'text_decoration': 'none'
            },
            'bright': {
                'background_color': '#ff6b6b',
                'text_color': '#ffffff',
                'font_weight': 'bold',
                'text_decoration': 'none'
            },
            'subtle': {
                'background_color': '#f0f0f0',
                'text_color': '#333333',
                'font_weight': 'normal',
                'text_decoration': 'underline'
            },
            'modern': {
                'background_color': '#4ecdc4',
                'text_color': '#ffffff',
                'font_weight': '600',
                'border_radius': '4px',
                'padding': '2px 4px'
            },
            'classic': {
                'background_color': 'transparent',
                'text_color': '#000000',
                'font_weight': 'bold',
                'text_decoration': 'none',
                'border': '2px solid #ff9900'
            }
        }
    
    # Private methods
    
    def _extract_text_content(self, element: Element) -> str:
        """Extract text content from element"""
        try:
            # Get text from various element properties
            text_parts = []
            
            if hasattr(element, 'text') and element.text:
                text_parts.append(str(element.text))
            
            if hasattr(element, 'content') and element.content:
                text_parts.append(str(element.content))
            
            if hasattr(element, 'title') and element.title:
                text_parts.append(str(element.title))
            
            # Combine all text
            full_text = ' '.join(text_parts).strip()
            
            # Remove extra whitespace
            full_text = re.sub(r'\s+', ' ', full_text)
            
            return full_text
            
        except Exception as e:
            logger.warning(f"Error extracting text from element: {e}")
            return ""
    
    def _find_matches(self, text: str, search_term: str) -> List[HighlightMatch]:
        """Find all matches of search term in text"""
        if not text or not search_term:
            return []
        
        try:
            # Get or compile pattern
            pattern = self._get_compiled_pattern(search_term)
            if not pattern:
                return []
            
            matches = []
            for match in pattern.finditer(text):
                start_pos = match.start()
                end_pos = match.end()
                matched_text = match.group()
                
                # Get context
                context_before = self._get_context_before(text, start_pos)
                context_after = self._get_context_after(text, end_pos)
                
                highlight_match = HighlightMatch(
                    start_pos=start_pos,
                    end_pos=end_pos,
                    matched_text=matched_text,
                    search_term=search_term,
                    confidence=1.0,  # Could implement fuzzy matching confidence
                    context_before=context_before,
                    context_after=context_after
                )
                
                matches.append(highlight_match)
            
            return matches
            
        except Exception as e:
            logger.warning(f"Error finding matches for term '{search_term}': {e}")
            return []
    
    def _get_compiled_pattern(self, search_term: str) -> Optional[re.Pattern]:
        """Get compiled regex pattern for search term"""
        cache_key = f"{search_term}_{self.config.mode.value}_{self.config.case_sensitive}_{self.config.whole_words_only}"
        
        if cache_key in self._compiled_patterns:
            return self._compiled_patterns[cache_key]
        
        try:
            # Escape special regex characters if not in regex mode
            if self.config.mode != HighlightMode.REGEX:
                escaped_term = re.escape(search_term)
            else:
                escaped_term = search_term
            
            # Build pattern based on mode
            if self.config.mode == HighlightMode.EXACT:
                pattern_str = escaped_term
            elif self.config.mode == HighlightMode.WORD_BOUNDARY:
                if self.config.whole_words_only:
                    pattern_str = r'\b' + escaped_term + r'\b'
                else:
                    pattern_str = escaped_term
            elif self.config.mode == HighlightMode.FUZZY:
                # Simple fuzzy matching - insert .* between characters
                fuzzy_chars = '.*'.join(re.escape(c) for c in search_term)
                pattern_str = fuzzy_chars
            elif self.config.mode == HighlightMode.REGEX:
                pattern_str = escaped_term
            else:
                pattern_str = escaped_term
            
            # Compile with appropriate flags
            flags = 0
            if not self.config.case_sensitive:
                flags |= re.IGNORECASE
            
            pattern = re.compile(pattern_str, flags)
            self._compiled_patterns[cache_key] = pattern
            
            return pattern
            
        except re.error as e:
            logger.error(f"Invalid regex pattern for term '{search_term}': {e}")
            self._compiled_patterns[cache_key] = None
            return None
    
    def _get_context_before(self, text: str, pos: int) -> str:
        """Get context before match position"""
        start = max(0, pos - self.config.context_chars)
        context = text[start:pos]
        
        # Find word boundary to avoid cutting words
        if start > 0:
            space_pos = context.find(' ')
            if space_pos != -1:
                context = context[space_pos + 1:]
        
        return context.strip()
    
    def _get_context_after(self, text: str, pos: int) -> str:
        """Get context after match position"""
        end = min(len(text), pos + self.config.context_chars)
        context = text[pos:end]
        
        # Find word boundary to avoid cutting words
        if end < len(text):
            space_pos = context.rfind(' ')
            if space_pos != -1:
                context = context[:space_pos]
        
        return context.strip()
    
    def _process_matches(self, matches: List[HighlightMatch]) -> List[HighlightMatch]:
        """Process and clean up matches list"""
        if not matches:
            return []
        
        # Sort by position
        sorted_matches = sorted(matches, key=lambda m: m.start_pos)
        
        # Remove overlapping matches (keep first one)
        filtered_matches = []
        last_end = -1
        
        for match in sorted_matches:
            if match.start_pos >= last_end:
                filtered_matches.append(match)
                last_end = match.end_pos
        
        return filtered_matches
    
    def _generate_html_highlights(self, text: str, matches: List[HighlightMatch]) -> str:
        """Generate HTML with highlighted matches"""
        if not matches:
            return escape(text)
        
        try:
            result_parts = []
            last_end = 0
            
            for match in matches:
                # Add text before match
                if match.start_pos > last_end:
                    before_text = text[last_end:match.start_pos]
                    result_parts.append(escape(before_text))
                
                # Add highlighted match
                matched_text = text[match.start_pos:match.end_pos]
                highlight_html = self._create_highlight_span(matched_text, match.search_term)
                result_parts.append(highlight_html)
                
                last_end = match.end_pos
            
            # Add remaining text
            if last_end < len(text):
                remaining_text = text[last_end:]
                result_parts.append(escape(remaining_text))
            
            return ''.join(result_parts)
            
        except Exception as e:
            logger.error(f"Error generating HTML highlights: {e}")
            return escape(text)
    
    def _generate_text_highlights(self, text: str, matches: List[HighlightMatch]) -> str:
        """Generate plain text with highlight markers"""
        if not matches:
            return text
        
        try:
            result_parts = []
            last_end = 0
            
            for match in matches:
                # Add text before match
                if match.start_pos > last_end:
                    result_parts.append(text[last_end:match.start_pos])
                
                # Add highlighted match with markers
                matched_text = text[match.start_pos:match.end_pos]
                result_parts.append(f"**{matched_text}**")
                
                last_end = match.end_pos
            
            # Add remaining text
            if last_end < len(text):
                result_parts.append(text[last_end:])
            
            return ''.join(result_parts)
            
        except Exception as e:
            logger.error(f"Error generating text highlights: {e}")
            return text
    
    def _create_highlight_span(self, text: str, search_term: str) -> str:
        """Create HTML span element for highlighted text"""
        style = self._get_highlight_css_style()
        escaped_text = escape(text)
        
        return f'<mark style="{style}" data-search-term="{escape(search_term)}">{escaped_text}</mark>'
    
    def _get_highlight_css_style(self) -> str:
        """Get CSS style string for highlights"""
        cache_key = f"{self.config.background_color}_{self.config.text_color}_{self.config.font_weight}"
        
        if cache_key in self._style_cache:
            return self._style_cache[cache_key]
        
        style_parts = []
        
        if self.config.background_color:
            style_parts.append(f"background-color: {self.config.background_color}")
        
        if self.config.text_color:
            style_parts.append(f"color: {self.config.text_color}")
        
        if self.config.font_weight:
            style_parts.append(f"font-weight: {self.config.font_weight}")
        
        if self.config.text_decoration:
            style_parts.append(f"text-decoration: {self.config.text_decoration}")
        
        if self.config.border:
            style_parts.append(f"border: {self.config.border}")
        
        if self.config.border_radius:
            style_parts.append(f"border-radius: {self.config.border_radius}")
        
        if self.config.padding:
            style_parts.append(f"padding: {self.config.padding}")
        
        style_string = "; ".join(style_parts)
        self._style_cache[cache_key] = style_string
        
        return style_string


# Factory functions for easy instantiation
def create_highlighter(mode: HighlightMode = HighlightMode.WORD_BOUNDARY,
                      case_sensitive: bool = False,
                      **config_kwargs) -> SearchHighlighter:
    """Create and configure a SearchHighlighter instance"""
    config = HighlightConfig(
        mode=mode,
        case_sensitive=case_sensitive,
        **config_kwargs
    )
    
    return SearchHighlighter(config)


def create_highlight_config(style_name: str = "default", **overrides) -> HighlightConfig:
    """Create highlight configuration with predefined style"""
    config = HighlightConfig()
    
    # Apply predefined style
    highlighter = SearchHighlighter()
    styles = highlighter.get_predefined_styles()
    
    if style_name in styles:
        style = styles[style_name]
        for key, value in style.items():
            if hasattr(config, key):
                setattr(config, key, value)
    
    # Apply overrides
    for key, value in overrides.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return config


def highlight_quick(text: str, search_terms: List[str], 
                   style: str = "default", mode: str = "word_boundary") -> str:
    """Quick highlighting function for simple use cases"""
    mode_enum = HighlightMode(mode)
    config = create_highlight_config(style, mode=mode_enum)
    highlighter = SearchHighlighter(config)
    
    return highlighter.highlight_text(text, search_terms, output_html=True)