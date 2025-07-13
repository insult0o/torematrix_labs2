"""Document-level metadata extractor with language and encoding detection."""

from typing import Dict, List, Any, Optional
import re
from datetime import datetime
import chardet
import langdetect
from langdetect.lang_detect_exception import LangDetectException

from ..types import (
    ExtractionContext, MetadataValidationResult, ExtractionMethod,
    LanguageCode, EncodingType, ExtractorResult
)
from .base import BaseExtractor


class DocumentMetadataExtractor(BaseExtractor):
    """Extract document-level metadata including properties and language detection."""
    
    def get_supported_extraction_methods(self) -> List[ExtractionMethod]:
        """Return supported extraction methods."""
        return [
            ExtractionMethod.DIRECT_PARSING,
            ExtractionMethod.HEURISTIC_ANALYSIS,
            ExtractionMethod.HYBRID
        ]
    
    async def extract(
        self,
        document: Any,
        context: ExtractionContext
    ) -> ExtractorResult:
        """Extract document-level metadata.
        
        Args:
            document: Document to extract metadata from
            context: Extraction context
            
        Returns:
            Dictionary containing document metadata
        """
        metadata = {
            "metadata_type": "document",
            "extraction_method": ExtractionMethod.HYBRID
        }
        
        # Extract basic document properties
        metadata.update(await self._extract_basic_properties(document))
        
        # Extract document structure information
        metadata.update(await self._extract_structure_info(document))
        
        # Detect language and encoding
        metadata.update(await self._detect_language_encoding(document))
        
        # Extract file properties
        metadata.update(await self._extract_file_properties(document))
        
        # Extract security properties
        metadata.update(await self._extract_security_properties(document))
        
        # Calculate quality metrics
        metadata.update(await self._calculate_quality_metrics(document, metadata))
        
        return metadata
    
    def validate_metadata(self, metadata: Dict[str, Any]) -> MetadataValidationResult:
        """Validate extracted document metadata.
        
        Args:
            metadata: Metadata dictionary to validate
            
        Returns:
            Validation result with confidence and errors
        """
        errors = []
        warnings = []
        confidence_factors = []
        
        # Validate required fields
        if not metadata.get("metadata_type"):
            errors.append("Missing metadata_type field")
        elif metadata["metadata_type"] != "document":
            errors.append("Invalid metadata_type for document extractor")
        
        # Validate page count
        page_count = metadata.get("page_count", 0)
        if page_count < 0:
            errors.append("Page count cannot be negative")
        elif page_count == 0:
            warnings.append("Document has zero pages")
        
        confidence_factors.append(0.9 if page_count > 0 else 0.5)
        
        # Validate element count consistency
        total_elements = metadata.get("total_elements", 0)
        if total_elements < 0:
            errors.append("Total elements cannot be negative")
        elif page_count > 0 and total_elements == 0:
            warnings.append("Document has pages but no elements")
        
        confidence_factors.append(0.9 if total_elements > 0 else 0.6)
        
        # Validate language detection
        language = metadata.get("language")
        language_confidence = metadata.get("language_confidence", 0.0)
        if language and language != LanguageCode.UNKNOWN:
            confidence_factors.append(min(1.0, language_confidence + 0.3))
        else:
            confidence_factors.append(0.5)
            warnings.append("Language detection failed or uncertain")
        
        # Validate encoding
        encoding = metadata.get("encoding")
        if not encoding:
            warnings.append("No encoding information available")
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.9)
        
        # Validate dates
        creation_date = metadata.get("creation_date")
        modification_date = metadata.get("modification_date")
        if creation_date and modification_date:
            if modification_date < creation_date:
                warnings.append("Modification date is before creation date")
                confidence_factors.append(0.7)
            else:
                confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.8)
        
        # Calculate overall confidence
        if confidence_factors:
            confidence_score = sum(confidence_factors) / len(confidence_factors)
        else:
            confidence_score = 0.5
        
        # Adjust confidence based on errors
        if errors:
            confidence_score *= 0.3
        elif warnings:
            confidence_score *= 0.8
        
        return MetadataValidationResult(
            is_valid=len(errors) == 0,
            confidence_score=max(0.0, min(1.0, confidence_score)),
            validation_errors=errors,
            validation_warnings=warnings
        )
    
    async def _extract_basic_properties(self, document: Any) -> Dict[str, Any]:
        """Extract basic document properties like title, author, etc."""
        properties = {}
        
        # Try to extract from document metadata if available
        if hasattr(document, 'metadata'):
            doc_meta = document.metadata
            properties.update({
                "title": self._clean_text(doc_meta.get("title")),
                "author": self._clean_text(doc_meta.get("author")),
                "subject": self._clean_text(doc_meta.get("subject")),
                "creator": self._clean_text(doc_meta.get("creator")),
                "producer": self._clean_text(doc_meta.get("producer")),
                "keywords": self._extract_keywords(doc_meta.get("keywords", ""))
            })
        
        # Extract dates
        if hasattr(document, 'metadata'):
            doc_meta = document.metadata
            properties.update({
                "creation_date": self._parse_date(doc_meta.get("creation_date")),
                "modification_date": self._parse_date(doc_meta.get("modification_date")),
                "metadata_date": self._parse_date(doc_meta.get("metadata_date"))
            })
        
        return {k: v for k, v in properties.items() if v is not None}
    
    async def _extract_structure_info(self, document: Any) -> Dict[str, Any]:
        """Extract document structure information."""
        structure = {}
        
        # Get page count
        if hasattr(document, 'pages'):
            structure["page_count"] = len(document.pages)
        elif hasattr(document, 'page_count'):
            structure["page_count"] = document.page_count
        else:
            structure["page_count"] = 1  # Default assumption
        
        # Get element count
        if hasattr(document, 'elements'):
            structure["total_elements"] = len(document.elements)
            
            # Count words and characters if text content available
            total_words = 0
            total_chars = 0
            for element in document.elements:
                if hasattr(element, 'text') and element.text:
                    words = len(element.text.split())
                    total_words += words
                    total_chars += len(element.text)
            
            if total_words > 0:
                structure["total_words"] = total_words
            if total_chars > 0:
                structure["total_characters"] = total_chars
        else:
            structure["total_elements"] = 0
        
        return structure
    
    async def _detect_language_encoding(self, document: Any) -> Dict[str, Any]:
        """Detect document language and encoding."""
        detection = {}
        
        # Extract text for analysis
        text_content = self._extract_text_content(document)
        
        # Detect language
        if text_content:
            language, confidence = self._detect_language(text_content)
            detection["language"] = language
            detection["language_confidence"] = confidence
            
            # Detect encoding
            encoding, enc_confidence = self._detect_encoding(text_content)
            detection["encoding"] = encoding
            detection["encoding_confidence"] = enc_confidence
        else:
            detection["language"] = LanguageCode.UNKNOWN
            detection["language_confidence"] = 0.0
            detection["encoding"] = EncodingType.UTF8  # Default assumption
            detection["encoding_confidence"] = 0.5
        
        return detection
    
    async def _extract_file_properties(self, document: Any) -> Dict[str, Any]:
        """Extract file-level properties."""
        properties = {}
        
        # File size
        if hasattr(document, 'file_size'):
            properties["file_size_bytes"] = document.file_size
        
        # File format
        if hasattr(document, 'file_format'):
            properties["file_format"] = document.file_format
        elif hasattr(document, 'source_path'):
            # Infer from file extension
            import pathlib
            suffix = pathlib.Path(document.source_path).suffix.lower()
            format_map = {
                '.pdf': 'PDF',
                '.docx': 'DOCX',
                '.doc': 'DOC',
                '.txt': 'TXT',
                '.rtf': 'RTF',
                '.odt': 'ODT'
            }
            properties["file_format"] = format_map.get(suffix, suffix.upper())
        
        # File version (if available)
        if hasattr(document, 'file_version'):
            properties["file_version"] = document.file_version
        
        # Additional file properties
        file_props = {}
        if hasattr(document, 'metadata'):
            for key, value in document.metadata.items():
                if key.startswith('file_') or key in ['version', 'application']:
                    file_props[key] = value
        
        if file_props:
            properties["file_properties"] = file_props
        
        return properties
    
    async def _extract_security_properties(self, document: Any) -> Dict[str, Any]:
        """Extract security-related properties."""
        security = {}
        
        # Check for encryption
        if hasattr(document, 'is_encrypted'):
            security["is_encrypted"] = document.is_encrypted
        else:
            security["is_encrypted"] = False
        
        # Check for digital signature
        if hasattr(document, 'has_signature'):
            security["has_digital_signature"] = document.has_signature
        else:
            security["has_digital_signature"] = False
        
        # Extract permissions if available
        permissions = {}
        if hasattr(document, 'permissions'):
            permissions = document.permissions
        elif hasattr(document, 'metadata'):
            # Look for permission-related metadata
            meta = document.metadata
            for key in ['can_print', 'can_modify', 'can_copy', 'can_extract']:
                if key in meta:
                    permissions[key] = meta[key]
        
        if permissions:
            security["permissions"] = permissions
        
        return security
    
    async def _calculate_quality_metrics(
        self,
        document: Any,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate document quality metrics."""
        quality = {}
        
        # Text quality score based on completeness and consistency
        text_quality_factors = []
        
        # Check if we have text content
        if metadata.get("total_characters", 0) > 0:
            text_quality_factors.append(0.9)
        else:
            text_quality_factors.append(0.3)
        
        # Check language detection confidence
        lang_confidence = metadata.get("language_confidence", 0.0)
        text_quality_factors.append(min(1.0, lang_confidence + 0.2))
        
        # Check encoding confidence
        enc_confidence = metadata.get("encoding_confidence", 0.0)
        text_quality_factors.append(min(1.0, enc_confidence + 0.1))
        
        if text_quality_factors:
            quality["text_quality_score"] = sum(text_quality_factors) / len(text_quality_factors)
        
        # Structure quality score
        structure_quality_factors = []
        
        # Check page/element ratio
        page_count = metadata.get("page_count", 0)
        element_count = metadata.get("total_elements", 0)
        if page_count > 0 and element_count > 0:
            ratio = element_count / page_count
            if 1 <= ratio <= 100:  # Reasonable range
                structure_quality_factors.append(0.9)
            else:
                structure_quality_factors.append(0.6)
        else:
            structure_quality_factors.append(0.4)
        
        # Check metadata completeness
        filled_fields = sum(1 for v in metadata.values() if v is not None and v != "")
        completeness = filled_fields / len(metadata) if metadata else 0
        structure_quality_factors.append(min(1.0, completeness + 0.2))
        
        if structure_quality_factors:
            quality["structure_quality_score"] = sum(structure_quality_factors) / len(structure_quality_factors)
        
        # Overall quality score
        text_score = quality.get("text_quality_score", 0.5)
        structure_score = quality.get("structure_quality_score", 0.5)
        quality["overall_quality_score"] = (text_score + structure_score) / 2
        
        return quality
    
    def _extract_text_content(self, document: Any) -> str:
        """Extract text content from document for analysis."""
        text_parts = []
        
        if hasattr(document, 'elements'):
            for element in document.elements:
                if hasattr(element, 'text') and element.text:
                    text_parts.append(element.text)
        elif hasattr(document, 'text'):
            text_parts.append(document.text)
        
        return " ".join(text_parts)[:10000]  # Limit for analysis
    
    def _detect_language(self, text: str) -> tuple[LanguageCode, float]:
        """Detect language of text content."""
        if not text or len(text.strip()) < 10:
            return LanguageCode.UNKNOWN, 0.0
        
        try:
            # Use langdetect library
            detected = langdetect.detect_langs(text)
            if detected:
                lang_code = detected[0].lang
                confidence = detected[0].prob
                
                # Map to our LanguageCode enum
                lang_mapping = {
                    'en': LanguageCode.ENGLISH,
                    'es': LanguageCode.SPANISH,
                    'fr': LanguageCode.FRENCH,
                    'de': LanguageCode.GERMAN,
                    'it': LanguageCode.ITALIAN,
                    'pt': LanguageCode.PORTUGUESE,
                    'nl': LanguageCode.DUTCH,
                    'ru': LanguageCode.RUSSIAN,
                    'zh': LanguageCode.CHINESE,
                    'ja': LanguageCode.JAPANESE,
                    'ko': LanguageCode.KOREAN,
                    'ar': LanguageCode.ARABIC
                }
                
                language = lang_mapping.get(lang_code, LanguageCode.UNKNOWN)
                return language, confidence
        
        except (LangDetectException, Exception) as e:
            self.logger.warning(f"Language detection failed: {e}")
        
        return LanguageCode.UNKNOWN, 0.0
    
    def _detect_encoding(self, text: str) -> tuple[EncodingType, float]:
        """Detect text encoding."""
        if not text:
            return EncodingType.UTF8, 0.5
        
        try:
            # Try to detect encoding from bytes
            text_bytes = text.encode('utf-8')
            detection = chardet.detect(text_bytes)
            
            if detection and detection['encoding']:
                encoding_name = detection['encoding'].lower()
                confidence = detection['confidence']
                
                # Map to our EncodingType enum
                encoding_mapping = {
                    'utf-8': EncodingType.UTF8,
                    'utf-16': EncodingType.UTF16,
                    'utf-32': EncodingType.UTF32,
                    'ascii': EncodingType.ASCII,
                    'latin-1': EncodingType.LATIN1,
                    'cp1252': EncodingType.CP1252
                }
                
                encoding = encoding_mapping.get(encoding_name, EncodingType.UTF8)
                return encoding, confidence
                
        except Exception as e:
            self.logger.warning(f"Encoding detection failed: {e}")
        
        return EncodingType.UTF8, 0.8  # Default to UTF-8 with medium confidence
    
    def _clean_text(self, text: Optional[str]) -> Optional[str]:
        """Clean and normalize text content."""
        if not text:
            return None
        
        # Remove extra whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # Remove control characters
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
        
        return cleaned if cleaned else None
    
    def _extract_keywords(self, keywords_str: str) -> List[str]:
        """Extract and clean keywords from keyword string."""
        if not keywords_str:
            return []
        
        # Split on common delimiters
        keywords = re.split(r'[,;|]', keywords_str)
        
        # Clean and filter keywords
        cleaned_keywords = []
        for keyword in keywords:
            cleaned = keyword.strip()
            if cleaned and len(cleaned) > 1:
                cleaned_keywords.append(cleaned)
        
        return cleaned_keywords
    
    def _parse_date(self, date_value: Any) -> Optional[datetime]:
        """Parse date from various formats."""
        if not date_value:
            return None
        
        if isinstance(date_value, datetime):
            return date_value
        
        if isinstance(date_value, str):
            # Try common date formats
            date_formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%Y/%m/%d'
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(date_value, fmt)
                except ValueError:
                    continue
        
        return None