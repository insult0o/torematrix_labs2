# AGENT 2 - Theme Framework Color Palettes & Typography

## 🎯 Mission: Color Palettes & Typography System
**Timeline: Day 2 | Focus: Color & Font Data Management**

## 📋 Your Sub-Issue: #121
[Theme Framework] Sub-Issue #14.2: Color Palettes & Typography System

## 🏗️ Core Responsibilities
1. **Color Palette Management** - Comprehensive color scheme system
2. **Typography System** - Font management and text styling
3. **Color Theory Algorithms** - Dynamic color generation and manipulation
4. **Accessibility Compliance** - WCAG-compliant color combinations
5. **Palette Persistence** - Save/restore color schemes and font settings

## 📁 Files You'll Create/Modify
```
src/torematrix/ui/themes/
├── palettes.py                    # 🎯 YOUR MAIN FOCUS - Color palette management
├── typography.py                  # Font and text system
├── colors.py                      # Color utilities and algorithms
└── accessibility.py               # Accessibility compliance tools

resources/themes/
├── palettes/                      # Built-in color schemes
│   ├── dark_professional.json
│   ├── light_clean.json
│   ├── high_contrast.json
│   └── custom_template.json
└── fonts/                         # Font definitions
    ├── default_fonts.json
    └── font_mappings.json

tests/unit/ui/themes/
├── test_palettes.py               # 🎯 YOUR TESTS
├── test_typography.py
├── test_colors.py
└── test_accessibility.py
```

## 🔧 Technical Implementation Details

### Color Palette Manager Structure
```python
class PaletteManager:
    """Advanced color palette management with accessibility."""
    
    def __init__(self, theme_engine)
    def create_palette(self, name: str, base_colors: Dict) -> ColorPalette
    def generate_palette_variations(self, base_palette: ColorPalette) -> List[ColorPalette]
    def validate_accessibility(self, palette: ColorPalette) -> AccessibilityReport
    def save_palette(self, palette: ColorPalette, path: str)
    def load_palette(self, path: str) -> ColorPalette
    def get_contrasting_color(self, color: str, background: str) -> str
```

### Typography System Structure
```python
class TypographyManager:
    """Comprehensive font and text styling management."""
    
    def __init__(self, theme_engine)
    def create_typography_scale(self, base_size: int) -> TypographyScale
    def load_font_family(self, family_name: str, paths: List[str]) -> bool
    def get_font_metrics(self, font: QFont) -> FontMetrics
    def generate_text_styles(self, typography: Typography) -> Dict[str, QFont]
    def validate_font_availability(self, font_family: str) -> bool
```

### Key Technical Requirements
- **Color theory algorithms** (HSV, HSL, contrast ratios)
- **WCAG accessibility compliance** (AA and AAA levels)
- **Font loading and validation** from system and custom sources
- **Dynamic color generation** with harmonic relationships
- **Palette serialization** to JSON/YAML formats

## 🎨 Color Palette System Design

### Built-in Palette Structure
```json
{
  "name": "Dark Professional",
  "category": "dark",
  "accessibility_level": "AAA",
  "colors": {
    "primary": {
      "50": "#E3F2FD",
      "100": "#BBDEFB",
      "500": "#2196F3",
      "900": "#0D47A1"
    },
    "neutral": {
      "0": "#FFFFFF",
      "50": "#FAFAFA",
      "100": "#F5F5F5",
      "900": "#212121",
      "1000": "#000000"
    },
    "semantic": {
      "success": "#4CAF50",
      "warning": "#FF9800",
      "error": "#F44336",
      "info": "#2196F3"
    }
  },
  "derived": {
    "background_primary": "${colors.neutral.1000}",
    "background_secondary": "${colors.neutral.900}",
    "text_primary": "${colors.neutral.0}",
    "text_secondary": "${colors.neutral.100}"
  }
}
```

### Typography Scale Definition
```json
{
  "name": "Professional Typography",
  "base_font_family": "Segoe UI",
  "fallback_families": ["Arial", "sans-serif"],
  "scale": {
    "xs": 10,
    "sm": 12,
    "base": 14,
    "lg": 16,
    "xl": 18,
    "2xl": 24,
    "3xl": 32
  },
  "weights": {
    "light": 300,
    "normal": 400,
    "medium": 500,
    "semibold": 600,
    "bold": 700
  },
  "line_heights": {
    "tight": 1.2,
    "normal": 1.4,
    "relaxed": 1.6
  }
}
```

## 🎨 Color Theory Implementation

### Advanced Color Algorithms
```python
class ColorUtilities:
    """Advanced color manipulation and generation."""
    
    @staticmethod
    def generate_monochromatic(base_color: str, steps: int = 10) -> List[str]:
        """Generate monochromatic color variations."""
        pass
        
    @staticmethod
    def generate_complementary(base_color: str) -> str:
        """Generate complementary color."""
        pass
        
    @staticmethod
    def generate_triadic(base_color: str) -> List[str]:
        """Generate triadic color scheme."""
        pass
        
    @staticmethod
    def calculate_contrast_ratio(color1: str, color2: str) -> float:
        """Calculate WCAG contrast ratio."""
        pass
        
    @staticmethod
    def ensure_accessibility(foreground: str, background: str, level: str = "AA") -> str:
        """Adjust foreground color to meet accessibility requirements."""
        pass
```

## ♿ Accessibility Compliance Features

### WCAG Compliance Levels
```python
WCAG_REQUIREMENTS = {
    "AA": {
        "normal_text": 4.5,
        "large_text": 3.0,
        "graphics": 3.0
    },
    "AAA": {
        "normal_text": 7.0,
        "large_text": 4.5,
        "graphics": 4.5
    }
}

class AccessibilityValidator:
    """Ensure color combinations meet accessibility standards."""
    
    def validate_palette(self, palette: ColorPalette, level: str = "AA") -> AccessibilityReport
    def suggest_improvements(self, palette: ColorPalette) -> List[Suggestion]
    def generate_high_contrast_variant(self, palette: ColorPalette) -> ColorPalette
```

## 🔗 Integration Points
- **Agent 1 (Core Engine)**: Use theme engine foundation for palette/typography management
- **Agent 3 (StyleSheet/Performance)**: Provide color and font data for stylesheet generation
- **Agent 4 (Icons/Integration)**: Supply color schemes for icon theming

## 🧪 Testing Requirements
- **Color generation** algorithm tests
- **Accessibility compliance** validation tests
- **Typography scaling** and font loading tests
- **Palette serialization** and persistence tests
- **Cross-platform font** compatibility tests
- **>95% code coverage** requirement

## ⚡ Success Criteria Checklist
- [ ] Dark and light palettes fully functional
- [ ] Typography system with proper scaling
- [ ] Color accessibility compliance (WCAG AA/AAA)
- [ ] Dynamic palette generation working
- [ ] Font loading and validation operational
- [ ] Palette persistence system complete
- [ ] Comprehensive test coverage

## 📅 Day 2 Completion Target
By end of Day 2, Agent 3 and 4 should have:
- Complete color palette system to use
- Typography system ready for stylesheet generation
- Accessibility-compliant color combinations
- Foundation for icon colorization

## 📞 Dependencies You'll Use
- ✅ **Agent 1 Output** - Theme engine foundation (Day 1)
- ✅ **Configuration Management** (#5) - For palette/font settings

## 🎯 Example Color Palette Generation
```python
def generate_professional_dark_palette():
    """Generate a professional dark theme palette."""
    base_colors = {
        'primary': '#2196F3',
        'background': '#121212'
    }
    
    # Generate full palette with accessibility compliance
    palette = PaletteManager.create_palette(
        name="Professional Dark",
        base_colors=base_colors
    )
    
    # Ensure WCAG AAA compliance
    AccessibilityValidator.validate_palette(palette, level="AAA")
    
    return palette
```

Focus on creating beautiful, accessible, and comprehensive color and typography systems!