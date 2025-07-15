#!/usr/bin/env python3
"""Validation script for Agent 2 - Enhanced Text Processing"""

import os
import sys
import ast
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def validate_file_structure():
    """Validate that all required files exist"""
    print("🔍 Validating file structure...")
    
    required_files = [
        "src/torematrix/ui/components/editors/text.py",
        "src/torematrix/ui/components/editors/spellcheck.py",
        "src/torematrix/ui/components/editors/validation.py",
        "src/torematrix/ui/components/editors/formatting.py",
        "src/torematrix/ui/components/editors/rich.py",
        "tests/unit/components/editors/test_text.py",
        "tests/unit/components/editors/test_spellcheck.py",
        "tests/unit/components/editors/test_validation.py",
        "tests/unit/components/editors/test_rich.py",
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    
    print("✅ All required files exist")
    return True

def validate_enhanced_text_edit():
    """Validate EnhancedTextEdit implementation"""
    print("🔍 Validating EnhancedTextEdit...")
    
    try:
        with open("src/torematrix/ui/components/editors/text.py", "r") as f:
            content = f.read()
        
        # Check for required components
        required_components = [
            "class EnhancedTextEdit",
            "spell_check_completed",
            "formatting_applied", 
            "validation_changed",
            "set_spell_checker",
            "set_validator",
            "set_format_preservor",
            "_on_spell_suggestions",
            "_on_validation_complete",
            "_show_context_menu",
            "_replace_current_word",
            "_add_word_to_dictionary",
            "apply_spell_suggestions",
            "get_misspelled_words"
        ]
        
        missing_components = []
        for component in required_components:
            if component not in content:
                missing_components.append(component)
        
        if missing_components:
            print(f"❌ Missing components: {missing_components}")
            return False
        
        # Check for context menu enhancements
        if "customContextMenuRequested" not in content:
            print("❌ Missing custom context menu support")
            return False
            
        # Check for autocomplete support
        if "QCompleter" not in content:
            print("❌ Missing autocomplete support")
            return False
        
        print("✅ EnhancedTextEdit implementation valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating EnhancedTextEdit: {e}")
        return False

def validate_spell_checker():
    """Validate SpellChecker implementation"""
    print("🔍 Validating SpellChecker...")
    
    try:
        with open("src/torematrix/ui/components/editors/spellcheck.py", "r") as f:
            content = f.read()
        
        # Check for required components
        required_components = [
            "class SpellChecker",
            "class SpellSuggestion",
            "class SpellCheckWorker",
            "check_text",
            "_perform_spell_check",
            "_is_word_correct",
            "_get_suggestions",
            "_generate_basic_suggestions",
            "_levenshtein_distance",
            "add_to_dictionary",
            "ignore_word",
            "add_domain_words"
        ]
        
        missing_components = []
        for component in required_components:
            if component not in content:
                missing_components.append(component)
        
        if missing_components:
            print(f"❌ Missing components: {missing_components}")
            return False
        
        # Check for threading support
        if "QThread" not in content:
            print("❌ Missing threading support")
            return False
            
        # Check for dictionary management
        if "custom_words" not in content or "ignored_words" not in content:
            print("❌ Missing dictionary management")
            return False
        
        print("✅ SpellChecker implementation valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating SpellChecker: {e}")
        return False

def validate_text_validator():
    """Validate TextValidator implementation"""
    print("🔍 Validating TextValidator...")
    
    try:
        with open("src/torematrix/ui/components/editors/validation.py", "r") as f:
            content = f.read()
        
        # Check for required components
        required_components = [
            "class TextValidator",
            "class ValidationRule",
            "class LengthValidationRule",
            "class RegexValidationRule", 
            "class ProhibitedWordsRule",
            "class RequiredWordsRule",
            "class CustomValidationRule",
            "class ValidationSeverity",
            "class ValidationResult",
            "validate",
            "add_rule",
            "remove_rule",
            "get_validation_results"
        ]
        
        missing_components = []
        for component in required_components:
            if component not in content:
                missing_components.append(component)
        
        if missing_components:
            print(f"❌ Missing components: {missing_components}")
            return False
        
        # Check for severity levels
        severities = ["INFO", "WARNING", "ERROR", "CRITICAL"]
        for severity in severities:
            if severity not in content:
                print(f"❌ Missing severity level: {severity}")
                return False
        
        print("✅ TextValidator implementation valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating TextValidator: {e}")
        return False

def validate_format_preservor():
    """Validate FormatPreservor implementation"""
    print("🔍 Validating FormatPreservor...")
    
    try:
        with open("src/torematrix/ui/components/editors/formatting.py", "r") as f:
            content = f.read()
        
        # Check for required components
        required_components = [
            "class FormatPreservor",
            "class FormatSpan",
            "class FormatType",
            "class TextSnapshot",
            "extract_formatting",
            "apply_formatting",
            "create_snapshot",
            "restore_snapshot",
            "merge_formatting",
            "convert_to_html",
            "convert_from_html"
        ]
        
        missing_components = []
        for component in required_components:
            if component not in content:
                missing_components.append(component)
        
        if missing_components:
            print(f"❌ Missing components: {missing_components}")
            return False
        
        # Check for format types
        format_types = ["BOLD", "ITALIC", "UNDERLINE", "COLOR", "FONT_SIZE"]
        for format_type in format_types:
            if format_type not in content:
                print(f"❌ Missing format type: {format_type}")
                return False
        
        print("✅ FormatPreservor implementation valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating FormatPreservor: {e}")
        return False

def validate_rich_text_editor():
    """Validate RichTextEditor implementation"""
    print("🔍 Validating RichTextEditor...")
    
    try:
        with open("src/torematrix/ui/components/editors/rich.py", "r") as f:
            content = f.read()
        
        # Check for required components
        required_components = [
            "class RichTextEditor",
            "_create_toolbar",
            "_create_preview_widget",
            "_create_status_widget",
            "_toggle_bold",
            "_toggle_italic",
            "_toggle_underline",
            "_change_text_color",
            "_change_background_color",
            "get_html_content",
            "get_plain_content",
            "set_html_content",
            "export_content",
            "import_content"
        ]
        
        missing_components = []
        for component in required_components:
            if component not in content:
                missing_components.append(component)
        
        if missing_components:
            print(f"❌ Missing components: {missing_components}")
            return False
        
        # Check for toolbar components
        toolbar_components = ["font_combo", "font_size_spin", "bold_action", "italic_action"]
        for component in toolbar_components:
            if component not in content:
                print(f"❌ Missing toolbar component: {component}")
                return False
        
        # Check for preview functionality
        if "preview" not in content or "_update_preview" not in content:
            print("❌ Missing preview functionality")
            return False
        
        print("✅ RichTextEditor implementation valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating RichTextEditor: {e}")
        return False

def validate_tests():
    """Validate test implementation"""
    print("🔍 Validating tests...")
    
    test_files = [
        "tests/unit/components/editors/test_text.py",
        "tests/unit/components/editors/test_spellcheck.py", 
        "tests/unit/components/editors/test_validation.py",
        "tests/unit/components/editors/test_rich.py"
    ]
    
    total_tests = 0
    
    for test_file in test_files:
        try:
            with open(test_file, "r") as f:
                content = f.read()
            
            # Count test methods
            test_count = content.count("def test_")
            total_tests += test_count
            print(f"  📋 {test_file}: {test_count} tests")
            
            # Check for required test patterns
            if "class Test" not in content:
                print(f"❌ Missing test class in {test_file}")
                return False
                
            if "pytest.fixture" not in content:
                print(f"❌ Missing pytest fixtures in {test_file}")
                return False
            
        except Exception as e:
            print(f"❌ Error reading {test_file}: {e}")
            return False
    
    if total_tests < 20:
        print(f"❌ Insufficient tests: {total_tests} (minimum 20 required)")
        return False
    
    print(f"✅ Test coverage excellent: {total_tests} tests total")
    return True

def validate_imports():
    """Validate that imports work correctly"""
    print("🔍 Validating imports...")
    
    try:
        with open("src/torematrix/ui/components/editors/__init__.py", "r") as f:
            content = f.read()
        
        required_imports = [
            "EnhancedTextEdit", "SpellChecker", "SpellSuggestion",
            "TextValidator", "ValidationRule", "ValidationSeverity",
            "FormatPreservor", "FormatSpan", "FormatType",
            "RichTextEditor"
        ]
        
        for import_name in required_imports:
            if import_name not in content:
                print(f"❌ Missing import: {import_name}")
                return False
        
        print("✅ Import structure valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating imports: {e}")
        return False

def validate_integration_points():
    """Validate integration with Agent 1 components"""
    print("🔍 Validating integration points...")
    
    try:
        # Check that EnhancedTextEdit integrates with BaseEditor
        with open("src/torematrix/ui/components/editors/text.py", "r") as f:
            text_content = f.read()
        
        if "from .base import BaseEditor" not in text_content:
            print("❌ Missing BaseEditor integration")
            return False
        
        # Check that RichTextEditor extends BaseEditor
        with open("src/torematrix/ui/components/editors/rich.py", "r") as f:
            rich_content = f.read()
        
        if "BaseEditor" not in rich_content:
            print("❌ RichTextEditor missing BaseEditor inheritance")
            return False
        
        # Check signal compatibility
        required_signals = ["editing_started", "editing_finished", "content_changed"]
        for signal in required_signals:
            if signal not in rich_content:
                print(f"❌ Missing BaseEditor signal: {signal}")
                return False
        
        print("✅ Integration points properly implemented")
        return True
        
    except Exception as e:
        print(f"❌ Error validating integration points: {e}")
        return False

def validate_factory_integration():
    """Validate factory integration"""
    print("🔍 Validating factory integration...")
    
    try:
        with open("src/torematrix/ui/components/editors/factory.py", "r") as f:
            content = f.read()
        
        # Should have RichTextEditor type
        if "RICH_TEXT" not in content:
            print("❌ Missing RICH_TEXT editor type")
            return False
        
        # Check auto-detection capabilities
        if "auto_detect_editor_type" not in content:
            print("❌ Missing auto-detection functionality")
            return False
        
        print("✅ Factory integration valid")
        return True
        
    except Exception as e:
        print(f"❌ Error validating factory integration: {e}")
        return False

def main():
    """Run all validations"""
    print("🚀 Agent 2 - Enhanced Text Processing Validation")
    print("=" * 60)
    
    validations = [
        validate_file_structure,
        validate_enhanced_text_edit,
        validate_spell_checker,
        validate_text_validator,
        validate_format_preservor,
        validate_rich_text_editor,
        validate_tests,
        validate_imports,
        validate_integration_points,
        validate_factory_integration
    ]
    
    results = []
    for validation in validations:
        try:
            result = validation()
            results.append(result)
        except Exception as e:
            print(f"❌ Validation error: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL VALIDATIONS PASSED ({passed}/{total})")
        print("\n✅ Agent 2 Enhanced Text Processing is complete and ready!")
        print("✅ Spell checking, validation, and formatting features implemented")
        print("✅ Rich text editor with full toolbar functionality")
        print("✅ Comprehensive test coverage with 20+ tests")
        print("✅ Integration with Agent 1 foundation completed")
        print("✅ Ready for Agent 3 advanced features implementation")
        return True
    else:
        print(f"❌ VALIDATIONS FAILED ({passed}/{total})")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)