"""Multi-language text detection for OCR and image content."""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

try:
    import langdetect
    from langdetect import detect, detect_langs
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False


@dataclass
class LanguageResult:
    """Result of language detection."""
    primary_language: str
    confidence: float
    all_languages: Dict[str, float]
    script_type: str
    text_statistics: Dict[str, Any]
    detection_method: str


class LanguageDetector:
    """Multi-language text detection with script analysis."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("torematrix.parsers.language_detector")
        
        # Language code mappings
        self.language_names = {
            'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
            'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian', 'zh': 'Chinese',
            'ja': 'Japanese', 'ko': 'Korean', 'ar': 'Arabic', 'hi': 'Hindi',
            'nl': 'Dutch', 'sv': 'Swedish', 'da': 'Danish', 'no': 'Norwegian',
            'fi': 'Finnish', 'pl': 'Polish', 'cs': 'Czech', 'hu': 'Hungarian',
            'tr': 'Turkish', 'th': 'Thai', 'vi': 'Vietnamese', 'id': 'Indonesian',
            'ms': 'Malay', 'tl': 'Filipino', 'uk': 'Ukrainian', 'bg': 'Bulgarian',
            'hr': 'Croatian', 'sr': 'Serbian', 'sk': 'Slovak', 'sl': 'Slovenian',
            'et': 'Estonian', 'lv': 'Latvian', 'lt': 'Lithuanian', 'ro': 'Romanian',
            'el': 'Greek', 'he': 'Hebrew', 'fa': 'Persian', 'ur': 'Urdu',
            'bn': 'Bengali', 'ta': 'Tamil', 'te': 'Telugu', 'ml': 'Malayalam',
            'kn': 'Kannada', 'gu': 'Gujarati', 'pa': 'Punjabi', 'mr': 'Marathi'
        }
        
        # Script detection patterns
        self.script_patterns = {
            'latin': r'[A-Za-zÀ-ÿĀ-žА-я]',
            'cyrillic': r'[А-я]',
            'arabic': r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]',
            'chinese': r'[\u4e00-\u9fff]',
            'japanese_hiragana': r'[\u3040-\u309f]',
            'japanese_katakana': r'[\u30a0-\u30ff]',
            'korean': r'[\uac00-\ud7af]',
            'devanagari': r'[\u0900-\u097F]',
            'bengali': r'[\u0980-\u09FF]',
            'gujarati': r'[\u0A80-\u0AFF]',
            'tamil': r'[\u0B80-\u0BFF]',
            'telugu': r'[\u0C00-\u0C7F]',
            'kannada': r'[\u0C80-\u0CFF]',
            'malayalam': r'[\u0D00-\u0D7F]',
            'thai': r'[\u0E00-\u0E7F]',
            'hebrew': r'[\u0590-\u05FF]',
            'greek': r'[\u0370-\u03FF]'
        }
        
        # Common word patterns for language identification
        self.language_patterns = {
            'en': [r'\b(the|and|that|have|for|not|with|you|this|but|his|from|they)\b'],
            'es': [r'\b(que|de|no|la|el|en|es|se|le|da|lo|como|con|su|para)\b'],
            'fr': [r'\b(de|le|et|que|la|les|des|en|un|du|est|il|pour|pas|ce)\b'],
            'de': [r'\b(der|die|und|in|den|von|zu|das|mit|sich|des|auf|für)\b'],
            'it': [r'\b(che|di|la|il|un|è|per|una|in|del|da|non|le|si|con)\b'],
            'pt': [r'\b(que|de|não|o|a|do|da|em|um|para|é|com|uma|os|no)\b'],
            'ru': [r'\b(в|и|не|на|я|с|что|он|как|это|по|но|они|все|так)\b'],
            'zh': [r'[的是了我不人在他有这个上们来到时大地为子中你说生国年着就那和要她出也得里后自以会家可下而过天去能对小多然于心学么之都好看起发当没成只如事把还用第样道想作种开要来得了就你会没有什么'],
            'ja': [r'[のはがでにをとかしたこれそれあれどこいつだったです]'],
            'ko': [r'[이그저것하다있다되다없다같다많다크다작다좋다나쁘다새다오래다빠르다느리다]'],
            'ar': [r'[فيمنعلىإلىهذهذلكأنكلذيالتيليسكانتكونقدلاماإذاحتىبعدقبلعندعبر]']
        }

    def detect_language(self, text: str) -> LanguageResult:
        """Detect language of text.
        
        Args:
            text: Text to analyze
            
        Returns:
            LanguageResult with detection results
        """
        if not text or not text.strip():
            return LanguageResult(
                primary_language='unknown',
                confidence=0.0,
                all_languages={},
                script_type='unknown',
                text_statistics={},
                detection_method='none'
            )
        
        # Clean text
        cleaned_text = self._clean_text(text)
        
        # Calculate text statistics
        text_stats = self._calculate_text_statistics(cleaned_text)
        
        # Detect script type
        script_type = self._detect_script_type(cleaned_text)
        
        # Try different detection methods
        detection_results = {}
        
        # Method 1: Use langdetect library if available
        if LANGDETECT_AVAILABLE:
            langdetect_result = self._detect_with_langdetect(cleaned_text)
            if langdetect_result:
                detection_results['langdetect'] = langdetect_result
        
        # Method 2: Pattern-based detection
        pattern_result = self._detect_with_patterns(cleaned_text)
        if pattern_result:
            detection_results['patterns'] = pattern_result
        
        # Method 3: Script-based detection
        script_result = self._detect_with_scripts(cleaned_text, script_type)
        if script_result:
            detection_results['scripts'] = script_result
        
        # Method 4: Character frequency analysis
        frequency_result = self._detect_with_frequency(cleaned_text)
        if frequency_result:
            detection_results['frequency'] = frequency_result
        
        # Combine results
        final_result = self._combine_detection_results(detection_results, script_type, text_stats)
        
        return final_result

    def _clean_text(self, text: str) -> str:
        """Clean text for language detection."""
        # Remove URLs, emails, numbers, and special characters
        text = re.sub(r'http[s]?://\S+', '', text)
        text = re.sub(r'\S+@\S+', '', text)
        text = re.sub(r'\b\d+\b', '', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _calculate_text_statistics(self, text: str) -> Dict[str, Any]:
        """Calculate text statistics."""
        if not text:
            return {}
        
        words = text.split()
        chars = [c for c in text if c.isalpha()]
        
        return {
            'total_chars': len(text),
            'alpha_chars': len(chars),
            'word_count': len(words),
            'avg_word_length': sum(len(w) for w in words) / len(words) if words else 0,
            'unique_chars': len(set(chars)),
            'char_diversity': len(set(chars)) / len(chars) if chars else 0
        }

    def _detect_script_type(self, text: str) -> str:
        """Detect script type of text."""
        script_counts = {}
        
        for script_name, pattern in self.script_patterns.items():
            matches = len(re.findall(pattern, text))
            if matches > 0:
                script_counts[script_name] = matches
        
        if not script_counts:
            return 'unknown'
        
        # Return the script with the most matches
        return max(script_counts, key=script_counts.get)

    def _detect_with_langdetect(self, text: str) -> Optional[Dict[str, float]]:
        """Detect language using langdetect library."""
        try:
            if len(text) < 10:  # langdetect needs sufficient text
                return None
            
            # Get multiple language predictions
            langs = detect_langs(text)
            
            result = {}
            for lang_prob in langs:
                lang_code = lang_prob.lang
                confidence = lang_prob.prob
                result[lang_code] = confidence
            
            return result
            
        except Exception as e:
            self.logger.debug(f"Langdetect failed: {e}")
            return None

    def _detect_with_patterns(self, text: str) -> Optional[Dict[str, float]]:
        """Detect language using word patterns."""
        text_lower = text.lower()
        pattern_scores = {}
        
        for lang_code, patterns in self.language_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower))
                score += matches
            
            if score > 0:
                # Normalize by text length
                pattern_scores[lang_code] = score / len(text.split())
        
        if not pattern_scores:
            return None
        
        # Normalize scores to probabilities
        total_score = sum(pattern_scores.values())
        return {lang: score / total_score for lang, score in pattern_scores.items()}

    def _detect_with_scripts(self, text: str, script_type: str) -> Optional[Dict[str, float]]:
        """Detect language based on script type."""
        script_to_languages = {
            'latin': ['en', 'es', 'fr', 'de', 'it', 'pt', 'nl', 'sv', 'da', 'no', 'fi', 'pl'],
            'cyrillic': ['ru', 'uk', 'bg', 'sr', 'mk'],
            'arabic': ['ar', 'fa', 'ur'],
            'chinese': ['zh'],
            'japanese_hiragana': ['ja'],
            'japanese_katakana': ['ja'],
            'korean': ['ko'],
            'devanagari': ['hi', 'mr', 'ne'],
            'bengali': ['bn'],
            'tamil': ['ta'],
            'telugu': ['te'],
            'kannada': ['kn'],
            'malayalam': ['ml'],
            'gujarati': ['gu'],
            'thai': ['th'],
            'hebrew': ['he'],
            'greek': ['el']
        }
        
        if script_type not in script_to_languages:
            return None
        
        languages = script_to_languages[script_type]
        
        # Equal probability for all languages using this script
        prob_per_lang = 1.0 / len(languages)
        return {lang: prob_per_lang for lang in languages}

    def _detect_with_frequency(self, text: str) -> Optional[Dict[str, float]]:
        """Detect language using character frequency analysis."""
        if len(text) < 50:  # Need sufficient text for frequency analysis
            return None
        
        # Character frequencies for different languages (simplified)
        language_frequencies = {
            'en': {'e': 0.12, 't': 0.09, 'a': 0.08, 'o': 0.075, 'i': 0.07, 'n': 0.067},
            'es': {'e': 0.137, 'a': 0.125, 'o': 0.086, 's': 0.08, 'n': 0.071, 'r': 0.068},
            'fr': {'e': 0.147, 's': 0.081, 'a': 0.076, 'i': 0.075, 't': 0.074, 'n': 0.071},
            'de': {'e': 0.174, 'n': 0.097, 's': 0.072, 'r': 0.070, 'a': 0.065, 't': 0.061},
            'it': {'e': 0.117, 'a': 0.117, 'i': 0.101, 'o': 0.098, 'n': 0.069, 't': 0.063},
            'pt': {'a': 0.146, 'e': 0.123, 'o': 0.103, 's': 0.078, 'r': 0.065, 'i': 0.061}
        }
        
        # Calculate character frequencies in text
        text_chars = [c.lower() for c in text if c.isalpha()]
        text_freq = Counter(text_chars)
        total_chars = len(text_chars)
        
        if total_chars == 0:
            return None
        
        text_freq_normalized = {char: count / total_chars for char, count in text_freq.items()}
        
        # Calculate similarity to each language
        language_scores = {}
        for lang, expected_freq in language_frequencies.items():
            score = 0
            for char, expected_prob in expected_freq.items():
                actual_prob = text_freq_normalized.get(char, 0)
                # Calculate similarity (inverse of absolute difference)
                score += 1 - abs(expected_prob - actual_prob)
            
            language_scores[lang] = score / len(expected_freq)
        
        if not language_scores:
            return None
        
        # Normalize to probabilities
        total_score = sum(language_scores.values())
        return {lang: score / total_score for lang, score in language_scores.items()}

    def _combine_detection_results(self, detection_results: Dict[str, Dict[str, float]], 
                                 script_type: str, text_stats: Dict[str, Any]) -> LanguageResult:
        """Combine results from different detection methods."""
        if not detection_results:
            return LanguageResult(
                primary_language='unknown',
                confidence=0.0,
                all_languages={},
                script_type=script_type,
                text_statistics=text_stats,
                detection_method='none'
            )
        
        # Weight different methods
        method_weights = {
            'langdetect': 0.4,
            'patterns': 0.3,
            'scripts': 0.2,
            'frequency': 0.1
        }
        
        # Combine weighted scores
        combined_scores = {}
        total_weight = 0
        
        for method, results in detection_results.items():
            weight = method_weights.get(method, 0.1)
            total_weight += weight
            
            for lang, score in results.items():
                if lang not in combined_scores:
                    combined_scores[lang] = 0
                combined_scores[lang] += score * weight
        
        # Normalize by total weight
        if total_weight > 0:
            combined_scores = {lang: score / total_weight for lang, score in combined_scores.items()}
        
        # Find primary language
        if combined_scores:
            primary_language = max(combined_scores, key=combined_scores.get)
            primary_confidence = combined_scores[primary_language]
        else:
            primary_language = 'unknown'
            primary_confidence = 0.0
        
        # Determine detection method used
        methods_used = list(detection_results.keys())
        detection_method = '+'.join(methods_used)
        
        return LanguageResult(
            primary_language=primary_language,
            confidence=primary_confidence,
            all_languages=combined_scores,
            script_type=script_type,
            text_statistics=text_stats,
            detection_method=detection_method
        )

    def get_language_name(self, language_code: str) -> str:
        """Get full language name from code."""
        return self.language_names.get(language_code, language_code)

    def is_latin_script(self, text: str) -> bool:
        """Check if text uses Latin script."""
        return self._detect_script_type(text) == 'latin'

    def detect_multiple_languages(self, text: str) -> List[Tuple[str, float]]:
        """Detect multiple languages in text with confidence scores.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of (language_code, confidence) tuples sorted by confidence
        """
        result = self.detect_language(text)
        
        if not result.all_languages:
            return [(result.primary_language, result.confidence)]
        
        # Sort by confidence
        sorted_languages = sorted(
            result.all_languages.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_languages

    def get_detection_statistics(self, results: List[LanguageResult]) -> Dict[str, Any]:
        """Get statistics about language detection results.
        
        Args:
            results: List of LanguageResult objects
            
        Returns:
            Dictionary with detection statistics
        """
        if not results:
            return {}
        
        total_detections = len(results)
        successful_detections = sum(1 for r in results if r.primary_language != 'unknown')
        
        confidence_scores = [r.confidence for r in results]
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        
        languages_detected = Counter(r.primary_language for r in results)
        scripts_detected = Counter(r.script_type for r in results)
        methods_used = Counter(r.detection_method for r in results)
        
        return {
            'total_detections': total_detections,
            'successful_detections': successful_detections,
            'success_rate': successful_detections / total_detections,
            'average_confidence': avg_confidence,
            'languages_detected': dict(languages_detected),
            'scripts_detected': dict(scripts_detected),
            'methods_used': dict(methods_used),
            'langdetect_available': LANGDETECT_AVAILABLE
        }