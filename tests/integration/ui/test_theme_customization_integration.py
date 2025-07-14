"""Integration tests for theme customization and validation systems.

Tests the complete theme customization workflow including theme building,
validation, export/import, and live preview capabilities.
"""

import pytest
import tempfile
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch
import zipfile

from PyQt6.QtWidgets import QApplication, QWidget, QPushButton
from PyQt6.QtCore import QTimer, pyqtSignal

from torematrix.ui.themes.customization import (
    ThemeBuilder, ThemeCustomizer, ThemeExporter, CustomThemeConfig,
    ThemeTemplate, ThemeExportSettings, ExportFormat, ColorSchemePreset,
    BUILTIN_COLOR_SCHEMES
)
from torematrix.ui.themes.validation import (
    ThemeValidator, ValidationLevel, ValidationCategory, ValidationResult,
    ThemeAutoFixer, validate_dark_theme_contrast, validate_high_contrast_theme
)
from torematrix.ui.themes.base import Theme
from torematrix.ui.themes.types import ThemeMetadata, ThemeType
from torematrix.ui.themes.accessibility import AccessibilityLevel


class TestThemeCustomizationIntegration:
    """Integration tests for theme customization workflow."""
    
    @pytest.fixture
    def app(self):
        """QApplication fixture."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        yield app
    
    @pytest.fixture
    def temp_dir(self):
        """Temporary directory fixture."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def sample_config(self):
        """Sample theme configuration."""
        return CustomThemeConfig(
            name='Integration Test Theme',
            description='Theme created for integration testing',
            author='Integration Test Suite',
            category=ThemeType.LIGHT,
            base_template=ThemeTemplate.LIGHT_MODERN,
            accessibility_target=AccessibilityLevel.AA,
            include_icons=True,
            include_typography=True,
            color_blindness_support=True
        )
    
    def test_complete_theme_building_workflow(self, sample_config):
        """Test complete theme building workflow from configuration to final theme."""
        # 1. Create theme builder
        builder = ThemeBuilder(sample_config)
        
        # Verify initial template was loaded
        theme_data = builder.get_theme_data()
        assert 'metadata' in theme_data
        assert 'colors' in theme_data
        assert 'typography' in theme_data
        
        # Verify metadata was properly set
        metadata = theme_data['metadata']
        assert metadata['name'] == sample_config.name
        assert metadata['description'] == sample_config.description
        assert metadata['author'] == sample_config.author
        assert metadata['category'] == sample_config.category.value
        
        # 2. Customize colors
        custom_colors = {
            'primary': '#1976D2',
            'secondary': '#388E3C',
            'accent': '#FF5722',
            'background': '#FAFAFA',
            'text_primary': '#212121'
        }
        
        for color_name, color_value in custom_colors.items():
            builder.set_color(color_name, color_value, f"Custom {color_name} color")
        
        # Verify colors were set
        updated_data = builder.get_theme_data()
        for color_name, color_value in custom_colors.items():
            assert color_name in updated_data['colors']
            color_data = updated_data['colors'][color_name]
            if isinstance(color_data, dict):
                assert color_data['value'] == color_value
            else:
                assert color_data == color_value
        
        # 3. Apply color scheme preset
        material_blue = next(
            preset for preset in BUILTIN_COLOR_SCHEMES 
            if preset.name == 'Material Blue'
        )
        builder.apply_color_scheme_preset(material_blue)
        
        # 4. Set typography
        typography_configs = [
            ('heading', 'Arial Black', 18, 700, 1.2),
            ('body', 'Helvetica Neue', 14, 400, 1.5),
            ('caption', 'Arial', 12, 400, 1.3)
        ]
        
        for typo_name, font_family, font_size, font_weight, line_height in typography_configs:
            builder.set_typography(typo_name, font_family, font_size, font_weight, line_height)
        
        # Verify typography was set
        updated_data = builder.get_theme_data()
        for typo_name, font_family, font_size, font_weight, line_height in typography_configs:
            assert typo_name in updated_data['typography']
            typo_data = updated_data['typography'][typo_name]
            assert typo_data['font_family'] == font_family
            assert typo_data['font_size'] == font_size
            assert typo_data['font_weight'] == font_weight
            assert typo_data['line_height'] == line_height
        
        # 5. Auto-generate variants and optimize
        builder.auto_generate_variants()
        builder.optimize_for_accessibility()
        
        # 6. Validate theme
        validation_issues = builder.validate_theme()
        if validation_issues:
            print(f"Validation issues found: {validation_issues}")
            # Issues are acceptable as long as they're not critical
            critical_issues = [issue for issue in validation_issues if 'error' in issue.lower()]
            assert len(critical_issues) == 0, f"Critical validation issues: {critical_issues}"
        
        # 7. Build final theme
        final_theme = builder.build_theme()
        assert final_theme is not None
        assert final_theme.name == sample_config.name
        assert final_theme.metadata.description == sample_config.description
        assert final_theme.metadata.author == sample_config.author
        
        # Verify theme can generate stylesheet
        stylesheet = final_theme.generate_stylesheet()
        assert isinstance(stylesheet, str)
        assert len(stylesheet) > 0
        
        print("✅ Complete theme building workflow test passed!")
    
    def test_theme_customizer_live_preview(self, app, sample_config):
        """Test theme customizer with live preview functionality."""
        customizer = ThemeCustomizer()
        
        # Mock preview widget
        preview_widget = QWidget()
        customizer.set_preview_widget(preview_widget)
        
        # Start customization session
        customizer.start_customization(sample_config)
        
        # Track signal emissions
        color_changed_signals = []
        typography_changed_signals = []
        validation_signals = []
        preview_update_signals = []
        
        def track_color_changed(color_name, color_value):
            color_changed_signals.append((color_name, color_value))
        
        def track_typography_changed(typo_name, definition):
            typography_changed_signals.append((typo_name, definition))
        
        def track_validation(is_valid, issues):
            validation_signals.append((is_valid, issues))
        
        def track_preview_update():
            preview_update_signals.append(True)
        
        customizer.colorChanged.connect(track_color_changed)
        customizer.typographyChanged.connect(track_typography_changed)
        customizer.themeValidated.connect(track_validation)
        customizer.previewUpdated.connect(track_preview_update)
        
        # Test color changes
        test_colors = [
            ('primary', '#E91E63'),
            ('secondary', '#9C27B0'),
            ('accent', '#FF5722')
        ]
        
        for color_name, color_value in test_colors:
            customizer.set_color(color_name, color_value)
        
        # Allow time for signals to process
        QTimer.singleShot(100, lambda: None)
        app.processEvents()
        
        # Verify signals were emitted
        assert len(color_changed_signals) == len(test_colors)
        for i, (color_name, color_value) in enumerate(test_colors):
            assert color_changed_signals[i] == (color_name, color_value)
        
        # Test typography changes
        customizer.set_typography('heading', 'Impact', 20, 800, 1.1)
        
        # Allow time for signals
        QTimer.singleShot(100, lambda: None)
        app.processEvents()
        
        assert len(typography_changed_signals) > 0
        
        # Test color scheme application
        nature_green = next(
            preset for preset in BUILTIN_COLOR_SCHEMES 
            if preset.name == 'Nature Green'
        )
        customizer.apply_color_scheme(nature_green)
        
        # Test accessibility optimization
        customizer.auto_optimize_accessibility()
        
        # Verify customizer state
        assert customizer.has_unsaved_changes()
        
        # Get final theme data
        theme_data = customizer.get_current_theme_data()
        assert theme_data is not None
        assert 'colors' in theme_data
        assert 'typography' in theme_data
        
        # Build final theme
        final_theme = customizer.build_final_theme()
        assert final_theme is not None
        
        print("✅ Theme customizer live preview test passed!")
    
    def test_theme_export_import_comprehensive(self, temp_dir):
        """Test comprehensive theme export and import functionality."""
        # Create test theme
        config = CustomThemeConfig(
            name='Export Test Theme',
            description='Theme for testing export/import functionality',
            author='Export Test',
            category=ThemeType.DARK,
            base_template=ThemeTemplate.DARK_PROFESSIONAL
        )
        
        builder = ThemeBuilder(config)
        builder.set_color('primary', '#2196F3')
        builder.set_color('accent', '#FF9800')
        builder.set_typography('default', 'Roboto', 14, 400, 1.4)
        
        test_theme = builder.build_theme()
        exporter = ThemeExporter()
        
        # Test different export formats
        export_formats = [
            (ExportFormat.JSON, '.json'),
            (ExportFormat.YAML, '.yaml'),
            (ExportFormat.THEME_PACKAGE, '.zip')
        ]
        
        exported_files = []
        
        for export_format, extension in export_formats:
            export_settings = ThemeExportSettings(
                format=export_format,
                include_metadata=True,
                include_icons=True,
                include_documentation=True,
                minify_output=False,
                validate_before_export=True
            )
            
            export_file = temp_dir / f'test_theme{extension}'
            
            # Export theme
            success = exporter.export_theme(test_theme, export_file, export_settings)
            assert success, f"Export failed for format {export_format.value}"
            assert export_file.exists(), f"Export file not created for {export_format.value}"
            
            exported_files.append((export_file, export_format))
            
            # Verify file content
            if export_format == ExportFormat.JSON:
                with open(export_file, 'r') as f:
                    data = json.load(f)
                assert 'metadata' in data
                assert 'colors' in data
                assert data['metadata']['name'] == test_theme.name
            
            elif export_format == ExportFormat.YAML:
                # Basic file existence check
                content = export_file.read_text()
                assert 'name:' in content
                assert 'colors:' in content
            
            elif export_format == ExportFormat.THEME_PACKAGE:
                # Verify ZIP contents
                with zipfile.ZipFile(export_file, 'r') as zf:
                    files_in_zip = zf.namelist()
                    assert 'theme.json' in files_in_zip
                    if export_settings.include_metadata:
                        assert 'metadata.json' in files_in_zip
                    if export_settings.include_documentation:
                        assert 'README.md' in files_in_zip
        
        # Test import for each exported file
        for export_file, export_format in exported_files:
            imported_theme = exporter.import_theme(export_file)
            
            assert imported_theme is not None, f"Import failed for {export_format.value}"
            assert imported_theme.name == test_theme.name
            assert imported_theme.metadata.description == test_theme.metadata.description
            assert imported_theme.metadata.author == test_theme.metadata.author
            
            # Verify color data is preserved
            original_colors = test_theme.get_color_palette()
            imported_colors = imported_theme.get_color_palette()
            
            if original_colors and imported_colors:
                # Check key colors are preserved
                key_colors = ['primary', 'accent']
                for color_name in key_colors:
                    if original_colors.has_color(color_name):
                        original_value = original_colors.get_color_value(color_name)
                        imported_value = imported_colors.get_color_value(color_name, '')
                        assert imported_value == original_value, f"Color {color_name} not preserved in {export_format.value}"
        
        print("✅ Theme export/import comprehensive test passed!")
    
    def test_theme_validation_comprehensive(self):
        """Test comprehensive theme validation with different levels and scenarios."""
        validator = ThemeValidator(ValidationLevel.STRICT)
        
        # Test 1: Valid theme
        valid_theme_data = {
            'metadata': {
                'name': 'Valid Theme',
                'version': '1.0.0',
                'description': 'A valid theme for testing',
                'author': 'Test Author',
                'category': 'light'
            },
            'colors': {
                'background': '#FFFFFF',
                'surface': '#F5F5F5',
                'text_primary': '#212529',
                'text_secondary': '#6C757D',
                'primary': '#007BFF',
                'secondary': '#6C757D',
                'accent': '#17A2B8',
                'border': '#DEE2E6',
                'success': '#28A745',
                'warning': '#FFC107',
                'error': '#DC3545',
                'info': '#17A2B8'
            },
            'typography': {
                'default': {
                    'font_family': 'Segoe UI',
                    'font_size': 12,
                    'font_weight': 400,
                    'line_height': 1.4
                },
                'heading': {
                    'font_family': 'Segoe UI',
                    'font_size': 16,
                    'font_weight': 600,
                    'line_height': 1.2
                }
            },
            'components': {
                'button': {
                    'background': '${colors.primary}',
                    'color': '${colors.text_primary}'
                }
            }
        }
        
        result = validator.validate_theme_data(valid_theme_data)
        assert result.is_valid
        assert result.score > 80.0
        assert result.error_count == 0
        
        # Test 2: Theme with issues
        problematic_theme_data = {
            'metadata': {
                'name': 'Problematic Theme'
                # Missing required fields
            },
            'colors': {
                'background': '#FFFFFF',
                'text_primary': '#DDDDDD'  # Low contrast
                # Missing required colors
            }
            # Missing typography
        }
        
        result = validator.validate_theme_data(problematic_theme_data)
        assert not result.is_valid
        assert result.error_count > 0
        assert result.score < 80.0
        
        # Test auto-fixing
        auto_fixer = ThemeAutoFixer()
        fixed_data, applied_fixes = auto_fixer.auto_fix_theme(problematic_theme_data, result.issues)
        
        assert len(applied_fixes) > 0
        assert 'metadata' in fixed_data
        assert 'typography' in fixed_data
        
        # Validate fixed theme
        fixed_result = validator.validate_theme_data(fixed_data)
        assert fixed_result.score > result.score
        
        # Test 3: Custom validation rules
        def custom_forbidden_name_rule(theme_data):
            from torematrix.ui.themes.validation import ValidationIssue, ValidationCategory
            issues = []
            metadata = theme_data.get('metadata', {})
            if 'forbidden' in metadata.get('name', '').lower():
                issues.append(ValidationIssue(
                    category=ValidationCategory.METADATA,
                    severity="error",
                    message="Theme name contains forbidden word",
                    location="metadata.name"
                ))
            return issues
        
        validator.add_custom_rule(custom_forbidden_name_rule)
        
        forbidden_theme_data = valid_theme_data.copy()
        forbidden_theme_data['metadata']['name'] = 'Forbidden Theme'
        
        result = validator.validate_theme_data(forbidden_theme_data)
        assert result.error_count > 0
        
        # Test built-in validation rules
        dark_theme_data = valid_theme_data.copy()
        dark_theme_data['metadata']['category'] = 'dark'
        dark_theme_data['colors']['background'] = '#FFFFFF'  # Light background for "dark" theme
        
        dark_issues = validate_dark_theme_contrast(dark_theme_data)
        assert len(dark_issues) > 0
        
        print("✅ Theme validation comprehensive test passed!")
    
    def test_theme_templates_integration(self):
        """Test integration of all theme templates."""
        templates_to_test = [
            ThemeTemplate.BLANK,
            ThemeTemplate.LIGHT_MODERN,
            ThemeTemplate.DARK_PROFESSIONAL,
            ThemeTemplate.HIGH_CONTRAST,
            ThemeTemplate.CORPORATE,
            ThemeTemplate.CREATIVE
        ]
        
        for template in templates_to_test:
            config = CustomThemeConfig(
                name=f'Test {template.value.title()} Theme',
                description=f'Testing {template.value} template',
                author='Template Test',
                category=ThemeType.LIGHT if 'dark' not in template.value else ThemeType.DARK,
                base_template=template
            )
            
            builder = ThemeBuilder(config)
            
            # Verify template was loaded correctly
            theme_data = builder.get_theme_data()
            assert 'colors' in theme_data
            assert 'typography' in theme_data
            assert 'metadata' in theme_data
            
            # Verify required colors exist
            colors = theme_data['colors']
            required_colors = [
                'primary', 'secondary', 'background', 'text_primary'
            ]
            
            for color_name in required_colors:
                assert color_name in colors, f"Required color {color_name} missing in {template.value} template"
            
            # Build theme to verify it's valid
            try:
                theme = builder.build_theme()
                assert theme is not None
                assert theme.name == config.name
            except Exception as e:
                pytest.fail(f"Failed to build theme from {template.value} template: {e}")
        
        print("✅ Theme templates integration test passed!")
    
    def test_color_scheme_presets_integration(self):
        """Test integration of built-in color scheme presets."""
        config = CustomThemeConfig(
            name='Preset Test Theme',
            description='Testing color scheme presets',
            author='Preset Test',
            category=ThemeType.LIGHT,
            base_template=ThemeTemplate.BLANK
        )
        
        for preset in BUILTIN_COLOR_SCHEMES:
            builder = ThemeBuilder(config)
            
            # Apply preset
            builder.apply_color_scheme_preset(preset)
            
            # Verify preset colors were applied
            theme_data = builder.get_theme_data()
            colors = theme_data['colors']
            
            for color_name, color_value in preset.colors.items():
                assert color_name in colors
                color_data = colors[color_name]
                
                # Handle both string and dict formats
                actual_value = color_data if isinstance(color_data, str) else color_data.get('value', color_data)
                assert actual_value == color_value, f"Preset color {color_name} not applied correctly"
            
            # Verify accessibility level is preserved
            metadata = theme_data['metadata']
            expected_level = preset.accessibility_level.value
            actual_level = metadata.get('accessibility_target', AccessibilityLevel.AA.value)
            # Note: accessibility_target might be overridden by config, so we just verify it's set
            assert actual_level in ['A', 'AA', 'AAA']
            
            # Build theme to verify it's valid
            try:
                theme = builder.build_theme()
                assert theme is not None
            except Exception as e:
                pytest.fail(f"Failed to build theme with {preset.name} preset: {e}")
        
        print("✅ Color scheme presets integration test passed!")
    
    def test_performance_of_customization_workflow(self):
        """Test performance of theme customization workflow."""
        import time
        
        # Test theme building performance
        config = CustomThemeConfig(
            name='Performance Test Theme',
            description='Theme for performance testing',
            author='Performance Test',
            category=ThemeType.LIGHT,
            base_template=ThemeTemplate.LIGHT_MODERN
        )
        
        # Time theme building
        start_time = time.time()
        builder = ThemeBuilder(config)
        
        # Add many customizations
        for i in range(50):
            builder.set_color(f'custom_color_{i}', f'#{i*51:06x}')
        
        for i in range(10):
            builder.set_typography(f'custom_typo_{i}', 'Arial', 10 + i, 400, 1.0 + i * 0.1)
        
        # Auto-generate variants and optimize
        builder.auto_generate_variants()
        builder.optimize_for_accessibility()
        
        # Validate and build
        issues = builder.validate_theme()
        theme = builder.build_theme()
        
        build_time = time.time() - start_time
        assert build_time < 5.0, f"Theme building took too long: {build_time:.2f}s"
        
        # Test validation performance
        validator = ThemeValidator(ValidationLevel.STRICT)
        
        start_time = time.time()
        result = validator.validate_theme_data(theme._data)
        validation_time = time.time() - start_time
        
        assert validation_time < 2.0, f"Validation took too long: {validation_time:.2f}s"
        
        # Test export performance
        exporter = ThemeExporter()
        export_settings = ThemeExportSettings(
            format=ExportFormat.JSON,
            validate_before_export=True
        )
        
        start_time = time.time()
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as temp_file:
            success = exporter.export_theme(theme, Path(temp_file.name), export_settings)
            export_time = time.time() - start_time
        
        assert success
        assert export_time < 1.0, f"Export took too long: {export_time:.2f}s"
        
        print(f"✅ Performance test passed! Build: {build_time:.2f}s, Validation: {validation_time:.2f}s, Export: {export_time:.2f}s")


@pytest.mark.integration
@pytest.mark.customization
def test_customization_integration_suite():
    """Run all customization integration tests."""
    pytest.main([__file__, "-v", "-m", "customization"])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])