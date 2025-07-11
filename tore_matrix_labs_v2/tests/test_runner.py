#!/usr/bin/env python3
"""
Test Runner for TORE Matrix Labs V2

This script provides a comprehensive test runner with reporting,
coverage analysis, and performance benchmarking.
"""

import pytest
import sys
import argparse
from pathlib import Path
import subprocess
import time
from datetime import datetime


def run_tests(test_type="all", coverage=True, verbose=False, parallel=False):
    """
    Run tests with specified configuration.
    
    Args:
        test_type: Type of tests to run (unit, integration, ui, performance, all)
        coverage: Whether to run coverage analysis
        verbose: Verbose output
        parallel: Run tests in parallel
    """
    
    # Base pytest arguments
    pytest_args = ["-v"] if verbose else []
    
    # Add coverage if requested
    if coverage:
        pytest_args.extend([
            "--cov=core",
            "--cov=ui", 
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under=80"
        ])
    
    # Add parallel execution if requested
    if parallel:
        pytest_args.extend(["-n", "auto"])
    
    # Add test markers based on type
    if test_type == "unit":
        pytest_args.extend(["-m", "unit"])
    elif test_type == "integration":
        pytest_args.extend(["-m", "integration"])
    elif test_type == "ui":
        pytest_args.extend(["-m", "ui"])
    elif test_type == "performance":
        pytest_args.extend(["-m", "performance"])
    elif test_type == "slow":
        pytest_args.extend(["-m", "slow"])
    # "all" runs everything (no marker filter)
    
    # Add test directories
    test_dirs = []
    if test_type in ["unit", "all"]:
        test_dirs.append("tests/unit")
    if test_type in ["integration", "all"]:
        test_dirs.append("tests/integration")
    if test_type in ["ui", "all"]:
        test_dirs.append("tests/ui")
    if test_type in ["performance", "all"]:
        test_dirs.append("tests/performance")
    
    # If no specific directories, test everything
    if not test_dirs:
        test_dirs = ["tests"]
    
    pytest_args.extend(test_dirs)
    
    print(f"🧪 Running {test_type} tests...")
    print(f"Command: pytest {' '.join(pytest_args)}")
    print("=" * 80)
    
    # Run tests
    start_time = time.time()
    exit_code = pytest.main(pytest_args)
    end_time = time.time()
    
    print("=" * 80)
    print(f"✅ Tests completed in {end_time - start_time:.2f} seconds")
    
    if exit_code == 0:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    return exit_code


def run_linting():
    """Run code linting checks."""
    print("🔍 Running code linting...")
    
    lint_commands = [
        ["flake8", "core", "ui", "--max-line-length=120"],
        ["pylint", "core", "ui", "--disable=C0114,C0115,C0116"],
        ["mypy", "core", "ui", "--ignore-missing-imports"]
    ]
    
    all_passed = True
    
    for cmd in lint_commands:
        print(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ {cmd[0]} passed")
            else:
                print(f"❌ {cmd[0]} failed:")
                print(result.stdout)
                print(result.stderr)
                all_passed = False
        except FileNotFoundError:
            print(f"⚠️ {cmd[0]} not found, skipping...")
    
    return all_passed


def run_security_checks():
    """Run security checks."""
    print("🔒 Running security checks...")
    
    security_commands = [
        ["bandit", "-r", "core", "ui"],
        ["safety", "check"]
    ]
    
    all_passed = True
    
    for cmd in security_commands:
        print(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ {cmd[0]} passed")
            else:
                print(f"❌ {cmd[0]} found issues:")
                print(result.stdout)
                print(result.stderr)
                all_passed = False
        except FileNotFoundError:
            print(f"⚠️ {cmd[0]} not found, skipping...")
    
    return all_passed


def generate_test_report():
    """Generate a comprehensive test report."""
    print("📊 Generating test report...")
    
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "test_results": {},
        "coverage": {},
        "performance": {}
    }
    
    # Run different test suites and collect results
    test_types = ["unit", "integration", "ui", "performance"]
    
    for test_type in test_types:
        print(f"Running {test_type} tests for report...")
        
        # Run tests with JSON output
        pytest_args = [
            "-v", 
            "--tb=short",
            f"-m {test_type}",
            f"tests/{test_type}",
            "--json-report",
            f"--json-report-file=test_report_{test_type}.json"
        ]
        
        start_time = time.time()
        exit_code = pytest.main(pytest_args)
        end_time = time.time()
        
        report_data["test_results"][test_type] = {
            "exit_code": exit_code,
            "duration": end_time - start_time,
            "passed": exit_code == 0
        }
    
    # Generate HTML report
    html_report = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>TORE Matrix Labs V2 - Test Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
            .section {{ margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }}
            .pass {{ color: #27ae60; }}
            .fail {{ color: #e74c3c; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>TORE Matrix Labs V2 - Test Report</h1>
            <p>Generated: {report_data['timestamp']}</p>
        </div>
        
        <div class="section">
            <h2>Test Results Summary</h2>
            <table>
                <tr><th>Test Type</th><th>Status</th><th>Duration</th></tr>
    """
    
    for test_type, result in report_data["test_results"].items():
        status_class = "pass" if result["passed"] else "fail"
        status_text = "✅ PASS" if result["passed"] else "❌ FAIL"
        html_report += f"""
                <tr>
                    <td>{test_type.title()}</td>
                    <td class="{status_class}">{status_text}</td>
                    <td>{result['duration']:.2f}s</td>
                </tr>
        """
    
    html_report += """
            </table>
        </div>
    </body>
    </html>
    """
    
    # Save report
    with open("test_report.html", "w") as f:
        f.write(html_report)
    
    print("📋 Test report saved to: test_report.html")
    return report_data


def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(description="TORE Matrix Labs V2 Test Runner")
    
    parser.add_argument(
        "test_type",
        choices=["unit", "integration", "ui", "performance", "all", "lint", "security", "report"],
        default="all",
        nargs="?",
        help="Type of tests to run"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage reporting"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run tests in parallel"
    )
    
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip slow tests"
    )
    
    args = parser.parse_args()
    
    # Change to the project directory
    project_root = Path(__file__).parent.parent
    import os
    os.chdir(project_root)
    
    print("🚀 TORE Matrix Labs V2 - Test Runner")
    print("=" * 50)
    print(f"Project root: {project_root}")
    print(f"Test type: {args.test_type}")
    print("=" * 50)
    
    if args.test_type == "lint":
        success = run_linting()
        sys.exit(0 if success else 1)
    
    elif args.test_type == "security":
        success = run_security_checks()
        sys.exit(0 if success else 1)
    
    elif args.test_type == "report":
        generate_test_report()
        sys.exit(0)
    
    else:
        # Add fast flag to pytest args if specified
        if args.fast:
            os.environ["PYTEST_ADDOPTS"] = "-m 'not slow'"
        
        exit_code = run_tests(
            test_type=args.test_type,
            coverage=not args.no_coverage,
            verbose=args.verbose,
            parallel=args.parallel
        )
        
        sys.exit(exit_code)


if __name__ == "__main__":
    main()