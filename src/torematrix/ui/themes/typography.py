"""Comprehensive typography system with font management and scaling."""

import logging
import json
from typing import Dict, List, Optional, Union, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

from PyQt6.QtCore import QStandardPaths
from PyQt6.QtGui import QFont, QFontDatabase, QFontMetrics, QFontInfo
from PyQt6.QtWidgets import QApplication

from .types import TypographyDefinition
from .exceptions import ThemeValidationError

logger = logging.getLogger(__name__)


class FontWeight(Enum):
    """Standard font weights."""
    THIN = 100
    EXTRA_LIGHT = 200
    LIGHT = 300
    NORMAL = 400
    MEDIUM = 500
    SEMI_BOLD = 600
    BOLD = 700
    EXTRA_BOLD = 800
    BLACK = 900


class FontCategory(Enum):
    """Font categories for different use cases."""
    SERIF = "serif"
    SANS_SERIF = "sans_serif"
    MONOSPACE = "monospace"
    DISPLAY = "display"
    HANDWRITING = "handwriting"


@dataclass
class FontMetrics:
    """Font metrics information."""
    family: str
    point_size: int
    weight: int
    height: int
    ascent: int
    descent: int
    leading: int
    line_spacing: int
    average_char_width: int
    max_width: int


@dataclass
class FontDefinition:
    """Extended font definition with metadata."""
    family: str
    size: int
    weight: int = FontWeight.NORMAL.value
    italic: bool = False
    line_height: float = 1.4
    letter_spacing: float = 0.0
    category: FontCategory = FontCategory.SANS_SERIF
    fallbacks: List[str] = None
    
    def __post_init__(self):
        if self.fallbacks is None:
            self.fallbacks = []


@dataclass
class TypographyScale:
    """Typography scale definition with harmonious sizing."""
    name: str
    base_size: int
    ratio: float
    sizes: Dict[str, int]
    
    @classmethod
    def create_modular_scale(cls, name: str, base_size: int = 16, ratio: float = 1.25) -> 'TypographyScale':
        """Create modular typography scale.
        
        Args:
            name: Scale name
            base_size: Base font size in points
            ratio: Scale ratio (1.125 = Major Second, 1.25 = Major Third, etc.)
            
        Returns:
            Typography scale instance
        """
        sizes = {}
        
        # Generate smaller sizes
        for i, key in enumerate(['xs', 'sm'], start=1):
            sizes[key] = max(8, int(base_size / (ratio ** i)))
        
        # Base size
        sizes['base'] = base_size
        
        # Generate larger sizes
        scale_keys = ['lg', 'xl', '2xl', '3xl', '4xl', '5xl', '6xl']
        for i, key in enumerate(scale_keys, start=1):
            sizes[key] = int(base_size * (ratio ** i))
        
        return cls(name=name, base_size=base_size, ratio=ratio, sizes=sizes)


class FontManager:
    """Advanced font management with loading and validation."""
    
    def __init__(self):
        """Initialize font manager."""
        self.font_database = QFontDatabase()
        self._custom_fonts: Dict[str, str] = {}  # family -> path
        self._font_cache: Dict[str, QFont] = {}
        self._metrics_cache: Dict[str, FontMetrics] = {}
        
        # Get system fonts
        self._system_fonts = self.font_database.families()
        
        # Standard fallback chains
        self.fallback_chains = {
            FontCategory.SANS_SERIF: [
                "Segoe UI", "Helvetica Neue", "Helvetica", "Arial", 
                "sans-serif"
            ],
            FontCategory.SERIF: [
                "Times New Roman", "Georgia", "Times", "serif"
            ],
            FontCategory.MONOSPACE: [
                "Consolas", "Monaco", "Menlo", "DejaVu Sans Mono",
                "Courier New", "monospace"
            ],
            FontCategory.DISPLAY: [
                "Segoe UI", "Helvetica Neue", "Arial", "sans-serif"
            ]
        }
        
        logger.info(f"FontManager initialized with {len(self._system_fonts)} system fonts")
    
    def load_font_family(self, family_name: str, font_paths: List[Union[str, Path]]) -> bool:
        """Load custom font family from files.
        
        Args:
            family_name: Name to register font under
            font_paths: List of font file paths
            
        Returns:
            True if loading was successful
        """
        loaded_count = 0
        
        for path in font_paths:
            path = Path(path)
            if not path.exists():
                logger.warning(f"Font file not found: {path}")
                continue
            
            try:
                font_id = self.font_database.addApplicationFont(str(path))
                if font_id != -1:
                    families = self.font_database.applicationFontFamilies(font_id)
                    if families:
                        actual_family = families[0]
                        self._custom_fonts[actual_family] = str(path)
                        loaded_count += 1
                        logger.debug(f"Loaded font: {actual_family} from {path}")
                    else:
                        logger.warning(f"No font families found in {path}")
                else:
                    logger.error(f"Failed to load font from {path}")
            except Exception as e:
                logger.error(f"Error loading font from {path}: {e}")
        
        if loaded_count > 0:
            logger.info(f"Successfully loaded {loaded_count} fonts for family '{family_name}'")
            return True
        
        return False
    
    def validate_font_availability(self, font_family: str) -> bool:
        """Check if font family is available.
        
        Args:
            font_family: Font family name to check
            
        Returns:
            True if font is available
        """
        return (font_family in self._system_fonts or 
                font_family in self._custom_fonts)
    
    def get_font_metrics(self, font: QFont) -> FontMetrics:
        """Get comprehensive font metrics.
        
        Args:
            font: QFont instance to analyze
            
        Returns:
            FontMetrics instance
        """
        cache_key = f"{font.family()}_{font.pointSize()}_{font.weight()}"
        
        if cache_key in self._metrics_cache:
            return self._metrics_cache[cache_key]
        
        metrics = QFontMetrics(font)
        
        font_metrics = FontMetrics(
            family=font.family(),
            point_size=font.pointSize(),
            weight=font.weight(),
            height=metrics.height(),
            ascent=metrics.ascent(),
            descent=metrics.descent(),
            leading=metrics.leading(),
            line_spacing=metrics.lineSpacing(),
            average_char_width=metrics.averageCharWidth(),
            max_width=metrics.maxWidth()
        )
        
        self._metrics_cache[cache_key] = font_metrics
        return font_metrics
    
    def create_font(self, definition: FontDefinition, scale_factor: float = 1.0) -> QFont:
        """Create QFont from definition with scaling.
        
        Args:
            definition: Font definition
            scale_factor: Scaling factor to apply
            
        Returns:
            Configured QFont instance
        """
        cache_key = f"{definition.family}_{definition.size}_{definition.weight}_{scale_factor}"
        
        if cache_key in self._font_cache:
            return QFont(self._font_cache[cache_key])
        
        # Find best available font family
        family = self._find_best_font_family(definition.family, definition.category, definition.fallbacks)
        
        # Create font
        font = QFont(family)
        font.setPointSize(max(6, int(definition.size * scale_factor)))
        font.setWeight(QFont.Weight(definition.weight))
        font.setItalic(definition.italic)
        
        # Apply letter spacing if specified
        if definition.letter_spacing != 0.0:
            font.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 
                                100 + (definition.letter_spacing * 100))
        
        self._font_cache[cache_key] = font
        return QFont(font)
    
    def _find_best_font_family(self, preferred: str, category: FontCategory, fallbacks: List[str]) -> str:
        """Find the best available font family.
        
        Args:
            preferred: Preferred font family
            category: Font category for fallbacks
            fallbacks: Custom fallback list
            
        Returns:
            Best available font family name
        """
        # Check preferred font first
        if self.validate_font_availability(preferred):
            return preferred
        
        # Check custom fallbacks
        for fallback in fallbacks:
            if self.validate_font_availability(fallback):
                return fallback
        
        # Check category fallbacks
        category_fallbacks = self.fallback_chains.get(category, [])
        for fallback in category_fallbacks:
            if self.validate_font_availability(fallback):
                return fallback
        
        # Last resort - use default system font
        logger.warning(f"Could not find font '{preferred}', using system default")
        return QFont().defaultFamily()
    
    def get_available_fonts(self, category: Optional[FontCategory] = None) -> List[str]:
        """Get list of available fonts, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of available font family names
        """
        if category is None:
            return sorted(self._system_fonts + list(self._custom_fonts.keys()))
        
        # Simple category filtering based on font names
        # This is basic and could be enhanced with font metadata
        filtered_fonts = []
        
        for font in self._system_fonts + list(self._custom_fonts.keys()):
            if category == FontCategory.MONOSPACE:
                if any(mono_indicator in font.lower() for mono_indicator in 
                      ['mono', 'console', 'courier', 'code', 'source']):
                    filtered_fonts.append(font)
            elif category == FontCategory.SERIF:
                if any(serif_indicator in font.lower() for serif_indicator in 
                      ['times', 'georgia', 'serif', 'book']):
                    filtered_fonts.append(font)
            else:
                # Default to sans-serif
                if not any(exclude in font.lower() for exclude in 
                          ['mono', 'console', 'courier', 'times', 'serif']):
                    filtered_fonts.append(font)
        
        return sorted(filtered_fonts)
    
    def clear_cache(self) -> None:
        """Clear font and metrics caches."""
        self._font_cache.clear()
        self._metrics_cache.clear()
        logger.debug("Font caches cleared")


class TypographyManager:
    """Comprehensive typography system with scaling and management."""
    
    def __init__(self, theme_engine=None):
        """Initialize typography manager.
        
        Args:
            theme_engine: Reference to theme engine for integration
        """
        self.theme_engine = theme_engine
        self.font_manager = FontManager()
        
        # Typography definitions and scales
        self._typography_definitions: Dict[str, FontDefinition] = {}
        self._typography_scales: Dict[str, TypographyScale] = {}
        
        # Current settings
        self._current_scale: Optional[TypographyScale] = None
        self._global_scale_factor: float = 1.0
        self._base_line_height: float = 1.4
        
        # Create built-in typography definitions
        self._create_builtin_typography()
        
        logger.info("TypographyManager initialized")
    
    def create_typography_scale(self, name: str, base_size: int = 14, ratio: float = 1.25) -> TypographyScale:
        """Create typography scale with harmonious sizing.
        
        Args:
            name: Scale name
            base_size: Base font size
            ratio: Scale ratio
            
        Returns:
            Typography scale instance
        """
        scale = TypographyScale.create_modular_scale(name, base_size, ratio)
        self._typography_scales[name] = scale
        
        logger.info(f"Created typography scale '{name}' with base size {base_size} and ratio {ratio}")
        return scale
    
    def set_typography_scale(self, scale_name: str) -> bool:
        """Set active typography scale.
        
        Args:
            scale_name: Name of scale to activate
            
        Returns:
            True if scale was set successfully
        """
        if scale_name not in self._typography_scales:
            logger.error(f"Typography scale '{scale_name}' not found")
            return False
        
        self._current_scale = self._typography_scales[scale_name]
        logger.info(f"Active typography scale set to '{scale_name}'")
        return True
    
    def get_typography_scale(self, name: str) -> Optional[TypographyScale]:
        """Get typography scale by name."""
        return self._typography_scales.get(name)
    
    def register_font_definition(self, name: str, definition: FontDefinition) -> None:
        """Register typography definition.
        
        Args:
            name: Definition name
            definition: Font definition
        """
        self._typography_definitions[name] = definition
        logger.debug(f"Registered typography definition '{name}'")
    
    def get_font(self, name: str, size_override: Optional[int] = None, 
                 scale_factor: Optional[float] = None) -> QFont:
        """Get font by typography name.
        
        Args:
            name: Typography definition name
            size_override: Optional size override
            scale_factor: Optional scale factor override
            
        Returns:
            Configured QFont instance
        """
        if name not in self._typography_definitions:
            # Return default font if definition not found
            logger.warning(f"Typography definition '{name}' not found, using default")
            return QFont()
        
        definition = self._typography_definitions[name]
        
        # Apply size override if provided
        if size_override is not None:
            definition = FontDefinition(
                family=definition.family,
                size=size_override,
                weight=definition.weight,
                italic=definition.italic,
                line_height=definition.line_height,
                letter_spacing=definition.letter_spacing,
                category=definition.category,
                fallbacks=definition.fallbacks.copy() if definition.fallbacks else []
            )
        
        # Use provided scale factor or global one
        effective_scale = scale_factor if scale_factor is not None else self._global_scale_factor
        
        return self.font_manager.create_font(definition, effective_scale)
    
    def get_font_from_scale(self, scale_name: str, size_key: str) -> Optional[QFont]:
        """Get font using typography scale.
        
        Args:
            scale_name: Typography scale name
            size_key: Size key (e.g., 'base', 'lg', '2xl')
            
        Returns:
            Font with scale-appropriate size
        """
        scale = self._typography_scales.get(scale_name)
        if not scale:
            return None
        
        size = scale.sizes.get(size_key)
        if size is None:
            return None
        
        # Use base typography definition with scale size
        base_definition = self._typography_definitions.get('body', 
                                                         self._typography_definitions.get('default'))
        if not base_definition:
            return None
        
        sized_definition = FontDefinition(
            family=base_definition.family,
            size=size,
            weight=base_definition.weight,
            italic=base_definition.italic,
            line_height=base_definition.line_height,
            letter_spacing=base_definition.letter_spacing,
            category=base_definition.category,
            fallbacks=base_definition.fallbacks.copy() if base_definition.fallbacks else []
        )
        
        return self.font_manager.create_font(sized_definition, self._global_scale_factor)
    
    def set_global_scale_factor(self, factor: float) -> None:
        """Set global typography scale factor.
        
        Args:
            factor: Scale factor (0.5 to 3.0)
        """
        self._global_scale_factor = max(0.5, min(3.0, factor))
        
        # Clear font cache to apply new scaling
        self.font_manager.clear_cache()
        
        logger.info(f"Global typography scale factor set to {self._global_scale_factor}")
    
    def get_global_scale_factor(self) -> float:
        """Get current global scale factor."""
        return self._global_scale_factor
    
    def get_font_metrics(self, name: str) -> Optional[FontMetrics]:
        """Get font metrics for typography definition.
        
        Args:
            name: Typography definition name
            
        Returns:
            Font metrics or None if not found
        """
        font = self.get_font(name)
        if font:
            return self.font_manager.get_font_metrics(font)
        return None
    
    def generate_text_styles(self, base_typography: str = 'body') -> Dict[str, QFont]:
        """Generate complete set of text styles.
        
        Args:
            base_typography: Base typography definition to derive from
            
        Returns:
            Dictionary of style names to QFont instances
        """
        styles = {}
        
        if base_typography not in self._typography_definitions:
            logger.error(f"Base typography '{base_typography}' not found")
            return styles
        
        base_def = self._typography_definitions[base_typography]
        
        # Generate heading styles
        heading_sizes = [32, 28, 24, 20, 18, 16]
        for i, size in enumerate(heading_sizes, 1):
            heading_def = FontDefinition(
                family=base_def.family,
                size=size,
                weight=FontWeight.SEMI_BOLD.value,
                category=base_def.category,
                fallbacks=base_def.fallbacks.copy() if base_def.fallbacks else [],
                line_height=1.2
            )
            styles[f'h{i}'] = self.font_manager.create_font(heading_def, self._global_scale_factor)
        
        # Generate body styles
        styles['body'] = self.get_font(base_typography)
        styles['body_large'] = self.get_font(base_typography, size_override=base_def.size + 2)
        styles['body_small'] = self.get_font(base_typography, size_override=base_def.size - 2)
        
        # Generate utility styles
        caption_def = FontDefinition(
            family=base_def.family,
            size=base_def.size - 2,
            weight=FontWeight.NORMAL.value,
            category=base_def.category,
            fallbacks=base_def.fallbacks.copy() if base_def.fallbacks else []
        )
        styles['caption'] = self.font_manager.create_font(caption_def, self._global_scale_factor)
        
        button_def = FontDefinition(
            family=base_def.family,
            size=base_def.size,
            weight=FontWeight.MEDIUM.value,
            category=base_def.category,
            fallbacks=base_def.fallbacks.copy() if base_def.fallbacks else []
        )
        styles['button'] = self.font_manager.create_font(button_def, self._global_scale_factor)
        
        logger.debug(f"Generated {len(styles)} text styles from '{base_typography}'")
        return styles
    
    def load_typography_from_file(self, path: Union[str, Path]) -> bool:
        """Load typography definitions from file.
        
        Args:
            path: File path to load from
            
        Returns:
            True if loading was successful
        """
        path = Path(path)
        
        if not path.exists():
            logger.error(f"Typography file not found: {path}")
            return False
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load typography definitions
            if 'typography' in data:
                for name, definition_data in data['typography'].items():
                    definition = FontDefinition(**definition_data)
                    self.register_font_definition(name, definition)
            
            # Load typography scales
            if 'scales' in data:
                for scale_name, scale_data in data['scales'].items():
                    scale = TypographyScale(**scale_data)
                    self._typography_scales[scale_name] = scale
            
            logger.info(f"Typography loaded from {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load typography from {path}: {e}")
            return False
    
    def save_typography_to_file(self, path: Union[str, Path]) -> bool:
        """Save typography definitions to file.
        
        Args:
            path: File path to save to
            
        Returns:
            True if saving was successful
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            data = {
                'typography': {
                    name: asdict(definition) 
                    for name, definition in self._typography_definitions.items()
                },
                'scales': {
                    name: asdict(scale)
                    for name, scale in self._typography_scales.items()
                }
            }
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Typography saved to {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save typography to {path}: {e}")
            return False
    
    def get_available_typography(self) -> List[str]:
        """Get list of available typography definition names."""
        return list(self._typography_definitions.keys())
    
    def get_available_scales(self) -> List[str]:
        """Get list of available typography scale names."""
        return list(self._typography_scales.keys())
    
    def _create_builtin_typography(self) -> None:
        """Create built-in typography definitions."""
        
        # Professional typography set
        professional_fallbacks = ["Segoe UI", "Helvetica Neue", "Arial", "sans-serif"]
        
        typography_definitions = {
            'default': FontDefinition(
                family="Segoe UI",
                size=14,
                weight=FontWeight.NORMAL.value,
                category=FontCategory.SANS_SERIF,
                fallbacks=professional_fallbacks
            ),
            'body': FontDefinition(
                family="Segoe UI",
                size=14,
                weight=FontWeight.NORMAL.value,
                category=FontCategory.SANS_SERIF,
                fallbacks=professional_fallbacks,
                line_height=1.5
            ),
            'heading': FontDefinition(
                family="Segoe UI",
                size=24,
                weight=FontWeight.SEMI_BOLD.value,
                category=FontCategory.SANS_SERIF,
                fallbacks=professional_fallbacks,
                line_height=1.2
            ),
            'subheading': FontDefinition(
                family="Segoe UI",
                size=18,
                weight=FontWeight.MEDIUM.value,
                category=FontCategory.SANS_SERIF,
                fallbacks=professional_fallbacks,
                line_height=1.3
            ),
            'caption': FontDefinition(
                family="Segoe UI",
                size=12,
                weight=FontWeight.NORMAL.value,
                category=FontCategory.SANS_SERIF,
                fallbacks=professional_fallbacks,
                line_height=1.4
            ),
            'button': FontDefinition(
                family="Segoe UI",
                size=14,
                weight=FontWeight.MEDIUM.value,
                category=FontCategory.SANS_SERIF,
                fallbacks=professional_fallbacks
            ),
            'monospace': FontDefinition(
                family="Consolas",
                size=13,
                weight=FontWeight.NORMAL.value,
                category=FontCategory.MONOSPACE,
                fallbacks=["Monaco", "Menlo", "DejaVu Sans Mono", "Courier New", "monospace"]
            ),
            'title': FontDefinition(
                family="Segoe UI",
                size=32,
                weight=FontWeight.BOLD.value,
                category=FontCategory.SANS_SERIF,
                fallbacks=professional_fallbacks,
                line_height=1.1
            )
        }
        
        # Register all definitions
        for name, definition in typography_definitions.items():
            self.register_font_definition(name, definition)
        
        # Create built-in scales
        self.create_typography_scale("professional", base_size=14, ratio=1.25)
        self.create_typography_scale("compact", base_size=12, ratio=1.2)
        self.create_typography_scale("comfortable", base_size=16, ratio=1.333)
        
        # Set default scale
        self.set_typography_scale("professional")
        
        logger.info("Built-in typography definitions and scales created")