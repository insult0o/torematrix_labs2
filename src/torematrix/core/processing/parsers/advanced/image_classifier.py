"""Image classification for document elements."""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class ImageType(Enum):
    """Types of images that can be classified."""
    CHART = "chart"
    DIAGRAM = "diagram"
    PHOTO = "photo"
    DOCUMENT = "document"
    SCREENSHOT = "screenshot"
    LOGO = "logo"
    ICON = "icon"
    MAP = "map"
    GRAPH = "graph"
    FLOWCHART = "flowchart"
    SCHEMATIC = "schematic"
    BANNER = "banner"
    PORTRAIT = "portrait"
    LANDSCAPE = "landscape"
    TABLE_IMAGE = "table_image"
    FORMULA_IMAGE = "formula_image"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    """Result of image classification."""
    image_type: ImageType
    confidence: float
    features: Dict[str, Any]
    reasoning: List[str]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ImageClassifier:
    """Advanced image classifier for document elements."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger("torematrix.parsers.image_classifier")
        
        # Classification keywords for different image types
        self.type_keywords = {
            ImageType.CHART: [
                'chart', 'graph', 'plot', 'bar chart', 'line chart', 'pie chart',
                'histogram', 'scatter plot', 'box plot', 'bubble chart', 'area chart'
            ],
            ImageType.DIAGRAM: [
                'diagram', 'flowchart', 'flow chart', 'schematic', 'blueprint',
                'architecture', 'structure', 'layout', 'plan', 'design'
            ],
            ImageType.PHOTO: [
                'photo', 'photograph', 'picture', 'image', 'snapshot',
                'portrait', 'landscape', 'nature', 'people', 'person'
            ],
            ImageType.DOCUMENT: [
                'document', 'page', 'text', 'paper', 'form', 'letter',
                'manuscript', 'article', 'scan', 'scanned'
            ],
            ImageType.SCREENSHOT: [
                'screenshot', 'screen shot', 'screen capture', 'screen grab',
                'ui', 'interface', 'application', 'software', 'window'
            ],
            ImageType.LOGO: [
                'logo', 'brand', 'company logo', 'trademark', 'emblem',
                'symbol', 'mark', 'branding'
            ],
            ImageType.ICON: [
                'icon', 'button', 'symbol', 'pictogram', 'glyph',
                'indicator', 'marker', 'sign'
            ],
            ImageType.MAP: [
                'map', 'geographical', 'location', 'route', 'navigation',
                'satellite', 'terrain', 'street map', 'world map'
            ],
            ImageType.FLOWCHART: [
                'flowchart', 'flow chart', 'process flow', 'workflow',
                'decision tree', 'algorithm', 'process diagram'
            ],
            ImageType.SCHEMATIC: [
                'schematic', 'circuit', 'wiring', 'electrical', 'technical',
                'engineering', 'blueprint', 'technical drawing'
            ],
            ImageType.TABLE_IMAGE: [
                'table', 'grid', 'spreadsheet', 'data table', 'matrix',
                'rows', 'columns', 'cells'
            ],
            ImageType.FORMULA_IMAGE: [
                'formula', 'equation', 'mathematical', 'math', 'expression',
                'calculation', 'theorem', 'proof'
            ]
        }
        
        # File format indicators
        self.format_indicators = {
            'vector': ['svg', 'eps', 'ai'],
            'raster': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff'],
            'document': ['pdf'],
            'raw': ['raw', 'cr2', 'nef', 'arw']
        }

    async def classify(self, image_data: Any, metadata: Optional[Dict[str, Any]] = None) -> ClassificationResult:
        """Classify an image based on available data.
        
        Args:
            image_data: Image data (PIL Image, path, or raw data)
            metadata: Optional metadata about the image
            
        Returns:
            ClassificationResult with classification and confidence
        """
        features = {}
        reasoning = []
        
        try:
            # Extract image dimensions and basic properties
            if PIL_AVAILABLE:
                dimensions = await self._extract_image_dimensions(image_data)
                if dimensions:
                    features.update(dimensions)
                    reasoning.append(f"Image dimensions: {dimensions['width']}x{dimensions['height']}")
            
            # Analyze metadata if available
            if metadata:
                meta_classification = await self._classify_from_metadata(metadata)
                if meta_classification:
                    features['metadata_hints'] = meta_classification
                    reasoning.append(f"Metadata suggests: {meta_classification}")
            
            # Analyze filename/path if available
            filename_hints = await self._classify_from_filename(image_data)
            if filename_hints:
                features['filename_hints'] = filename_hints
                reasoning.append(f"Filename suggests: {filename_hints}")
            
            # Analyze text content if available
            text_hints = await self._classify_from_text_content(metadata)
            if text_hints:
                features['text_hints'] = text_hints
                reasoning.append(f"Text content suggests: {text_hints}")
            
            # Analyze dimensions and aspect ratio
            dimension_hints = await self._classify_from_dimensions(features)
            if dimension_hints:
                features['dimension_hints'] = dimension_hints
                reasoning.append(f"Dimensions suggest: {dimension_hints}")
            
            # Make final classification
            image_type, confidence = await self._make_final_classification(features, reasoning)
            
            return ClassificationResult(
                image_type=image_type,
                confidence=confidence,
                features=features,
                reasoning=reasoning,
                metadata=metadata or {}
            )
            
        except Exception as e:
            self.logger.error(f"Image classification failed: {e}")
            return ClassificationResult(
                image_type=ImageType.UNKNOWN,
                confidence=0.0,
                features=features,
                reasoning=[f"Classification failed: {str(e)}"],
                metadata=metadata or {}
            )

    async def _extract_image_dimensions(self, image_data: Any) -> Optional[Dict[str, Any]]:
        """Extract dimensions from image data."""
        if not PIL_AVAILABLE:
            return None
        
        try:
            image = None
            
            if hasattr(image_data, 'size'):
                # Already a PIL Image
                image = image_data
            elif isinstance(image_data, (str, bytes)):
                # Try to open as image
                if isinstance(image_data, str) and ('/' in image_data or '\\' in image_data):
                    # Looks like a file path
                    image = Image.open(image_data)
                # Otherwise might be raw data or base64
            
            if image:
                width, height = image.size
                aspect_ratio = width / height if height > 0 else 1.0
                
                return {
                    'width': width,
                    'height': height,
                    'aspect_ratio': aspect_ratio,
                    'total_pixels': width * height,
                    'format': getattr(image, 'format', 'unknown')
                }
                
        except Exception as e:
            self.logger.debug(f"Could not extract image dimensions: {e}")
        
        return None

    async def _classify_from_metadata(self, metadata: Dict[str, Any]) -> Optional[List[str]]:
        """Classify based on metadata content."""
        hints = []
        
        if not metadata:
            return None
        
        # Check text fields in metadata
        text_fields = ['caption', 'alt_text', 'description', 'title', 'filename']
        
        for field in text_fields:
            if field in metadata and metadata[field]:
                text = str(metadata[field]).lower()
                
                for image_type, keywords in self.type_keywords.items():
                    for keyword in keywords:
                        if keyword in text:
                            hints.append(image_type.value)
                            break
        
        # Check format information
        if 'format' in metadata:
            format_val = str(metadata['format']).lower()
            for format_type, extensions in self.format_indicators.items():
                if any(ext in format_val for ext in extensions):
                    if format_type == 'vector':
                        hints.extend(['logo', 'icon', 'diagram'])
                    elif format_type == 'document':
                        hints.extend(['document', 'formula_image'])
        
        return list(set(hints)) if hints else None

    async def _classify_from_filename(self, image_data: Any) -> Optional[List[str]]:
        """Classify based on filename or path."""
        hints = []
        
        # Extract filename if available
        filename = None
        if isinstance(image_data, str):
            if '/' in image_data or '\\' in image_data:
                filename = image_data.split('/')[-1].split('\\')[-1]
            else:
                filename = image_data
        
        if not filename:
            return None
        
        filename_lower = filename.lower()
        
        # Check for type keywords in filename
        for image_type, keywords in self.type_keywords.items():
            for keyword in keywords:
                if keyword.replace(' ', '_') in filename_lower or keyword.replace(' ', '') in filename_lower:
                    hints.append(image_type.value)
        
        # Check file extensions
        for format_type, extensions in self.format_indicators.items():
            if any(filename_lower.endswith(f'.{ext}') for ext in extensions):
                if format_type == 'vector':
                    hints.extend(['logo', 'icon', 'diagram'])
                elif format_type == 'raw':
                    hints.append('photo')
        
        # Check common naming patterns
        patterns = {
            r'chart|graph|plot': 'chart',
            r'diagram|flow|schema': 'diagram',
            r'photo|pic|img': 'photo',
            r'screen|capture|shot': 'screenshot',
            r'logo|brand': 'logo',
            r'icon|button': 'icon',
            r'map|location': 'map',
            r'table|grid': 'table_image',
            r'formula|equation|math': 'formula_image'
        }
        
        for pattern, image_type in patterns.items():
            if re.search(pattern, filename_lower):
                hints.append(image_type)
        
        return list(set(hints)) if hints else None

    async def _classify_from_text_content(self, metadata: Dict[str, Any]) -> Optional[List[str]]:
        """Classify based on associated text content."""
        if not metadata:
            return None
        
        hints = []
        
        # Get all text content
        text_content = []
        text_fields = ['text', 'caption', 'alt_text', 'description', 'surrounding_text']
        
        for field in text_fields:
            if field in metadata and metadata[field]:
                text_content.append(str(metadata[field]))
        
        if not text_content:
            return None
        
        full_text = ' '.join(text_content).lower()
        
        # Look for mathematical content
        math_patterns = [
            r'[=+\-*/^_∫∑∏√∇∂∞±∓×÷≤≥≠∈∉⊂⊃∪∩]',
            r'\\[a-zA-Z]+',  # LaTeX commands
            r'\b(equation|formula|theorem|proof|calculate|derivative|integral)\b'
        ]
        
        if any(re.search(pattern, full_text) for pattern in math_patterns):
            hints.append('formula_image')
        
        # Look for data/chart indicators
        data_patterns = [
            r'\b(data|statistics|percent|percentage|trend|analysis)\b',
            r'\b(x-axis|y-axis|legend|scale|measurement)\b',
            r'\b(increase|decrease|growth|decline|comparison)\b'
        ]
        
        if any(re.search(pattern, full_text) for pattern in data_patterns):
            hints.append('chart')
        
        # Look for process/flow indicators
        process_patterns = [
            r'\b(step|process|flow|procedure|workflow|algorithm)\b',
            r'\b(start|end|decision|input|output|next|then|if)\b'
        ]
        
        if any(re.search(pattern, full_text) for pattern in process_patterns):
            hints.append('flowchart')
        
        return list(set(hints)) if hints else None

    async def _classify_from_dimensions(self, features: Dict[str, Any]) -> Optional[List[str]]:
        """Classify based on image dimensions and aspect ratio."""
        if 'width' not in features or 'height' not in features:
            return None
        
        hints = []
        width = features['width']
        height = features['height']
        aspect_ratio = features.get('aspect_ratio', 1.0)
        total_pixels = features.get('total_pixels', 0)
        
        # Very small images are likely icons
        if width <= 64 and height <= 64:
            hints.append('icon')
        elif width <= 200 and height <= 200:
            hints.extend(['icon', 'logo'])
        
        # Very wide images might be banners
        if aspect_ratio > 3.0:
            hints.append('banner')
        
        # Very tall images might be portraits or documents
        if aspect_ratio < 0.5:
            hints.extend(['portrait', 'document'])
        
        # Square-ish images
        if 0.8 <= aspect_ratio <= 1.2:
            hints.extend(['icon', 'logo', 'chart'])
        
        # Landscape orientation
        if 1.2 < aspect_ratio <= 2.0:
            hints.extend(['photo', 'screenshot', 'chart'])
        
        # High resolution suggests photos or detailed diagrams
        if total_pixels > 2000000:  # > 2MP
            hints.extend(['photo', 'diagram', 'document'])
        
        # Low resolution suggests simple graphics
        if total_pixels < 100000:  # < 0.1MP
            hints.extend(['icon', 'logo', 'simple_diagram'])
        
        return list(set(hints)) if hints else None

    async def _make_final_classification(self, features: Dict[str, Any], reasoning: List[str]) -> Tuple[ImageType, float]:
        """Make final classification decision based on all features."""
        # Collect all hints
        all_hints = []
        
        for feature_name in ['metadata_hints', 'filename_hints', 'text_hints', 'dimension_hints']:
            if feature_name in features and features[feature_name]:
                all_hints.extend(features[feature_name])
        
        if not all_hints:
            return ImageType.UNKNOWN, 0.1
        
        # Count occurrences of each hint
        hint_counts = {}
        for hint in all_hints:
            hint_counts[hint] = hint_counts.get(hint, 0) + 1
        
        # Find most common hint
        most_common_hint = max(hint_counts, key=hint_counts.get)
        max_count = hint_counts[most_common_hint]
        
        # Convert hint to ImageType
        try:
            image_type = ImageType(most_common_hint)
        except ValueError:
            # Handle special cases
            if most_common_hint == 'simple_diagram':
                image_type = ImageType.DIAGRAM
            else:
                image_type = ImageType.UNKNOWN
        
        # Calculate confidence based on consistency
        total_hints = len(all_hints)
        consistency = max_count / total_hints if total_hints > 0 else 0
        
        # Base confidence
        confidence = 0.3 + (consistency * 0.6)
        
        # Boost confidence for strong indicators
        if max_count >= 3:
            confidence += 0.1
        if total_hints >= 5:
            confidence += 0.1
        
        # Adjust confidence based on image type specificity
        specific_types = [ImageType.FORMULA_IMAGE, ImageType.TABLE_IMAGE, ImageType.FLOWCHART, ImageType.SCHEMATIC]
        if image_type in specific_types:
            confidence += 0.1
        
        return image_type, min(1.0, confidence)

    def get_classification_confidence_breakdown(self, result: ClassificationResult) -> Dict[str, Any]:
        """Get detailed breakdown of classification confidence.
        
        Args:
            result: ClassificationResult to analyze
            
        Returns:
            Dictionary with confidence breakdown
        """
        breakdown = {
            'final_type': result.image_type.value,
            'final_confidence': result.confidence,
            'feature_contributions': {},
            'reasoning_steps': result.reasoning,
            'features_detected': len(result.features)
        }
        
        # Analyze feature contributions
        for feature_name, feature_value in result.features.items():
            if isinstance(feature_value, list):
                breakdown['feature_contributions'][feature_name] = {
                    'hints_found': len(feature_value),
                    'hints': feature_value
                }
            else:
                breakdown['feature_contributions'][feature_name] = feature_value
        
        return breakdown

    def get_supported_types(self) -> List[ImageType]:
        """Get list of supported image types."""
        return list(ImageType)