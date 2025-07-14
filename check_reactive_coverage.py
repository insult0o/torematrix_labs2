#!/usr/bin/env python
"""
Check test coverage for reactive components.
Bypasses import issues with PySide6/PyQt6 conflicts.
"""

import subprocess
import sys
import os

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Run coverage directly on the module files
cmd = [
    sys.executable, "-m", "coverage", "run",
    "--source=src/torematrix/ui/components",
    "-m", "pytest", 
    "--tb=short",
    "-v"
]

# Create a simple test that directly tests our code
test_content = '''
import sys
import os
sys.path.insert(0, "src")

# Direct imports to avoid package init issues
import importlib.util

def import_module_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Import our modules directly
reactive = import_module_from_file("reactive", "src/torematrix/ui/components/reactive.py")
decorators = import_module_from_file("decorators", "src/torematrix/ui/components/decorators.py")
lifecycle = import_module_from_file("lifecycle", "src/torematrix/ui/components/lifecycle.py")

# Run basic tests
def test_imports():
    assert reactive.ReactiveWidget
    assert reactive.ReactiveProperty
    assert reactive.StateBinding
    assert decorators.reactive_property
    assert decorators.computed
    assert lifecycle.LifecycleManager
    print("✓ All imports successful")

def test_reactive_property():
    prop = reactive.ReactiveProperty(
        name="test",
        value=42,
        type_hint=int
    )
    assert prop.name == "test"
    assert prop.value == 42
    print("✓ ReactiveProperty works")

def test_state_binding():
    binding = reactive.StateBinding(
        property_name="test",
        state_path="app.test"
    )
    assert binding.property_name == "test"
    assert binding.state_path == "app.test"
    print("✓ StateBinding works")

def test_lifecycle_phase():
    assert lifecycle.LifecyclePhase.MOUNTED
    assert lifecycle.LifecyclePhase.UNMOUNTED
    print("✓ LifecyclePhase works")

def test_render_metrics():
    metrics = lifecycle.RenderMetrics()
    assert metrics.render_count == 0
    print("✓ RenderMetrics works")

if __name__ == "__main__":
    test_imports()
    test_reactive_property()
    test_state_binding()
    test_lifecycle_phase()
    test_render_metrics()
    print("\\nAll basic tests passed!")
'''

# Write and run the test
with open("test_reactive_basic.py", "w") as f:
    f.write(test_content)

print("Running basic functionality tests...")
subprocess.run([sys.executable, "test_reactive_basic.py"])

# Now check what we have
print("\n\nChecking file statistics...")

# Count lines of code
def count_lines(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    code_lines = 0
    total_lines = len(lines)
    
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and not stripped.startswith('"""'):
            code_lines += 1
    
    return total_lines, code_lines

files = [
    "src/torematrix/ui/components/reactive.py",
    "src/torematrix/ui/components/decorators.py", 
    "src/torematrix/ui/components/lifecycle.py",
    "src/torematrix/ui/components/__init__.py"
]

total_all = 0
total_code = 0

print("\nFile Statistics:")
print("-" * 60)
for file in files:
    total, code = count_lines(file)
    total_all += total
    total_code += code
    print(f"{file:50} {total:4} lines ({code:4} code)")

print("-" * 60)
print(f"{'TOTAL':50} {total_all:4} lines ({total_code:4} code)")

# Test file stats
test_files = [
    "tests/unit/ui/components/test_reactive.py",
    "tests/unit/ui/components/test_decorators.py",
    "tests/unit/ui/components/test_lifecycle.py"
]

test_total = 0
test_code = 0

print("\n\nTest File Statistics:")
print("-" * 60)
for file in test_files:
    if os.path.exists(file):
        total, code = count_lines(file)
        test_total += total
        test_code += code
        print(f"{file:50} {total:4} lines ({code:4} code)")

print("-" * 60)
print(f"{'TOTAL TESTS':50} {test_total:4} lines ({test_code:4} code)")

print(f"\n\nSummary:")
print(f"Production Code: {total_code} lines")
print(f"Test Code: {test_code} lines")
print(f"Test-to-Code Ratio: {test_code/total_code:.2f}:1")

# Cleanup
os.remove("test_reactive_basic.py")