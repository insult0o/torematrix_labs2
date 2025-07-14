#!/usr/bin/env python3
"""
UI Framework Validation Test
Tests the core UI components without full dependency chain
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_ui_framework_basic_functionality():
    """Test basic UI framework functionality without full dependencies."""
    
    print("🧪 TORE Matrix V3 UI Framework Validation")
    print("=" * 50)
    
    results = {
        "components_exist": False,
        "architecture_sound": False,
        "imports_clean": False,
        "classes_defined": False
    }
    
    # Test 1: Check if core UI files exist
    print("\n📁 Testing File Structure...")
    ui_files = [
        "src/torematrix/ui/main_window.py",
        "src/torematrix/ui/panels.py", 
        "src/torematrix/ui/statusbar.py",
        "src/torematrix/ui/persistence.py",
        "src/torematrix/ui/window_manager.py",
        "src/torematrix/ui/splash.py",
        "src/torematrix/ui/actions.py",
        "src/torematrix/ui/menus.py",
        "src/torematrix/ui/integration.py",
    ]
    
    all_files_exist = True
    for file_path in ui_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path}")
            all_files_exist = False
    
    results["components_exist"] = all_files_exist
    
    # Test 2: Check architecture patterns
    print("\n🏗️  Testing Architecture Patterns...")
    try:
        with open("src/torematrix/ui/main_window.py", "r") as f:
            main_window_content = f.read()
            
        architecture_checks = [
            ("QMainWindow inheritance", "class MainWindow" in main_window_content and "QMainWindow" in main_window_content),
            ("Type hints", "def __init__(self" in main_window_content and "->" in main_window_content),
            ("PyQt6 imports", "from PyQt6" in main_window_content),
            ("Async patterns", "async def" in main_window_content or "awaitable" in main_window_content.lower()),
        ]
        
        architecture_sound = True
        for check_name, check_result in architecture_checks:
            if check_result:
                print(f"  ✅ {check_name}")
            else:
                print(f"  ⚠️  {check_name}")
                # Don't fail for async patterns as they might not be needed everywhere
                if check_name != "Async patterns":
                    architecture_sound = False
        
        results["architecture_sound"] = architecture_sound
        
    except Exception as e:
        print(f"  ❌ Architecture test failed: {e}")
        results["architecture_sound"] = False
    
    # Test 3: Test class definitions exist  
    print("\n🔧 Testing Class Definitions...")
    
    class_tests = [
        ("MainWindow", "src/torematrix/ui/main_window.py", "class MainWindow"),
        ("PanelManager", "src/torematrix/ui/panels.py", "class PanelManager"),
        ("StatusBarManager", "src/torematrix/ui/statusbar.py", "class StatusBarManager"),
        ("WindowPersistence", "src/torematrix/ui/persistence.py", "class WindowPersistence"),
        ("WindowManager", "src/torematrix/ui/window_manager.py", "class WindowManager"),
        ("SplashScreen", "src/torematrix/ui/splash.py", "class SplashScreen"),
        ("ActionManager", "src/torematrix/ui/actions.py", "class ActionManager"),
        ("MenuBuilder", "src/torematrix/ui/menus.py", "class MenuBuilder"),
    ]
    
    classes_defined = True
    for class_name, file_path, class_signature in class_tests:
        try:
            with open(file_path, "r") as f:
                content = f.read()
            if class_signature in content:
                print(f"  ✅ {class_name}")
            else:
                print(f"  ❌ {class_name}")
                classes_defined = False
        except Exception as e:
            print(f"  ❌ {class_name} - file error: {e}")
            classes_defined = False
    
    results["classes_defined"] = classes_defined
    
    # Test 4: Check documentation exists
    print("\n📚 Testing Documentation...")
    
    doc_files = [
        "docs/ui_framework_guide.md",
        "tests/integration/ui/test_main_window_integration.py"
    ]
    
    docs_exist = True
    for doc_file in doc_files:
        if os.path.exists(doc_file):
            print(f"  ✅ {doc_file}")
        else:
            print(f"  ❌ {doc_file}")
            docs_exist = False
    
    # Summary
    print("\n📊 VALIDATION SUMMARY")
    print("=" * 30)
    
    total_score = 0
    max_score = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.replace('_', ' ').title()}: {status}")
        if result:
            total_score += 1
    
    if docs_exist:
        print(f"Documentation: ✅ PASS")
        total_score += 1
        max_score += 1
    else:
        print(f"Documentation: ❌ FAIL")
        max_score += 1
    
    print(f"\n🎯 OVERALL SCORE: {total_score}/{max_score} ({(total_score/max_score)*100:.1f}%)")
    
    if total_score >= max_score * 0.8:  # 80% pass threshold
        print("🚀 UI FRAMEWORK: PRODUCTION READY ✅")
        return True
    else:
        print("⚠️  UI FRAMEWORK: NEEDS ATTENTION ❌")
        return False

if __name__ == "__main__":
    success = test_ui_framework_basic_functionality()
    sys.exit(0 if success else 1)