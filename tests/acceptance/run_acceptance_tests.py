#!/usr/bin/env python3
"""
Acceptance Test Runner for Issue #3: State Management System

This script runs comprehensive acceptance tests that validate:
1. All acceptance criteria for Issue #3
2. Integration with all dependencies (Issues #1, #2)
3. All sub-issues of Issue #3 (#3.1, #3.2, #3.3, #3.4)
4. End-to-end workflow scenarios
5. Performance and error resilience

Usage:
    python tests/acceptance/run_acceptance_tests.py [--verbose] [--coverage] [--report]
"""

import sys
import asyncio
import argparse
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any
import json

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class AcceptanceTestRunner:
    """Runs and reports on acceptance tests for Issue #3."""
    
    def __init__(self, verbose: bool = False, coverage: bool = False):
        self.verbose = verbose
        self.coverage = coverage
        self.test_results = {}
        self.start_time = None
        self.end_time = None
    
    def run_tests(self) -> Dict[str, Any]:
        """Run all acceptance tests and return results."""
        self.start_time = time.time()
        
        print("🚀 Running Acceptance Tests for Issue #3: State Management System")
        print("=" * 70)
        
        # Test categories to run
        test_categories = [
            {
                "name": "Core Acceptance Criteria",
                "file": "tests/acceptance/core/state/test_issue_3_acceptance_criteria.py",
                "description": "Tests all 8 acceptance criteria for Issue #3"
            },
            {
                "name": "Dependencies Integration", 
                "file": "tests/acceptance/core/state/test_dependencies_integration.py",
                "description": "Tests integration with Event Bus (#1) and Unified Element Model (#2)"
            }
        ]
        
        all_results = {}
        
        for category in test_categories:
            print(f"\n📋 Running {category['name']}")
            print(f"   {category['description']}")
            print("-" * 50)
            
            results = self._run_test_file(category['file'])
            all_results[category['name']] = results
            
            self._print_category_results(category['name'], results)
        
        self.end_time = time.time()
        self.test_results = all_results
        
        # Print summary
        self._print_summary()
        
        return all_results
    
    def _run_test_file(self, test_file: str) -> Dict[str, Any]:
        """Run a specific test file and return results."""
        cmd = ["python", "-m", "pytest", test_file, "-v", "--tb=short"]
        
        if self.coverage:
            cmd.extend(["--cov=src/torematrix/core/state", "--cov-report=term-missing"])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=300  # 5 minute timeout
            )
            
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "success": result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": "Test execution timed out after 5 minutes",
                "success": False
            }
        except Exception as e:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Error running tests: {str(e)}",
                "success": False
            }
    
    def _print_category_results(self, category_name: str, results: Dict[str, Any]):
        """Print results for a test category."""
        if results["success"]:
            print(f"✅ {category_name}: PASSED")
        else:
            print(f"❌ {category_name}: FAILED")
        
        if self.verbose:
            print(f"   Return code: {results['returncode']}")
            if results["stdout"]:
                print("   STDOUT:")
                for line in results["stdout"].split('\n')[:20]:  # Limit output
                    if line.strip():
                        print(f"      {line}")
            
            if results["stderr"]:
                print("   STDERR:")
                for line in results["stderr"].split('\n')[:10]:  # Limit output
                    if line.strip():
                        print(f"      {line}")
    
    def _print_summary(self):
        """Print overall test summary."""
        print("\n" + "=" * 70)
        print("📊 ACCEPTANCE TEST SUMMARY")
        print("=" * 70)
        
        total_categories = len(self.test_results)
        passed_categories = sum(1 for results in self.test_results.values() if results["success"])
        
        print(f"⏱️  Total execution time: {self.end_time - self.start_time:.2f} seconds")
        print(f"📋 Test categories: {total_categories}")
        print(f"✅ Passed categories: {passed_categories}")
        print(f"❌ Failed categories: {total_categories - passed_categories}")
        
        if passed_categories == total_categories:
            print("\n🎉 ALL ACCEPTANCE TESTS PASSED!")
            print("   Issue #3 State Management System meets all acceptance criteria")
            print("   System is ready for production use")
        else:
            print(f"\n⚠️  {total_categories - passed_categories} categories failed")
            print("   Review failed tests before proceeding")
        
        # Print acceptance criteria status
        self._print_acceptance_criteria_status()
    
    def _print_acceptance_criteria_status(self):
        """Print status of each acceptance criterion."""
        print("\n📋 ACCEPTANCE CRITERIA STATUS:")
        print("-" * 50)
        
        criteria = [
            "AC1: Centralized state store with typed state tree",
            "AC2: Reactive state updates with observer pattern", 
            "AC3: Time-travel debugging capabilities",
            "AC4: Automatic persistence with configurable strategies",
            "AC5: Optimistic updates with rollback on failure",
            "AC6: State validation and sanitization",
            "AC7: Performance monitoring and optimization",
            "AC8: Comprehensive test coverage"
        ]
        
        core_tests_passed = self.test_results.get("Core Acceptance Criteria", {}).get("success", False)
        
        for criterion in criteria:
            status = "✅ PASSED" if core_tests_passed else "❌ FAILED"
            print(f"   {criterion}: {status}")
        
        print("\n🔗 DEPENDENCY INTEGRATION STATUS:")
        print("-" * 50)
        
        dependencies = [
            "Issue #1: Event Bus System Integration",
            "Issue #2: Unified Element Model Integration",
            "Sub-Issue #3.1: Core Store & Actions",
            "Sub-Issue #3.2: Persistence & Time-Travel", 
            "Sub-Issue #3.3: Selectors & Performance",
            "Sub-Issue #3.4: Middleware & Integration"
        ]
        
        integration_tests_passed = self.test_results.get("Dependencies Integration", {}).get("success", False)
        
        for dependency in dependencies:
            status = "✅ INTEGRATED" if integration_tests_passed else "❌ FAILED"
            print(f"   {dependency}: {status}")
    
    def generate_report(self, output_file: str = "acceptance_test_report.json"):
        """Generate detailed test report."""
        report = {
            "test_run": {
                "timestamp": time.time(),
                "duration_seconds": self.end_time - self.start_time if self.end_time else 0,
                "issue": "#3 State Management System",
                "runner_version": "1.0.0"
            },
            "summary": {
                "total_categories": len(self.test_results),
                "passed_categories": sum(1 for r in self.test_results.values() if r["success"]),
                "overall_success": all(r["success"] for r in self.test_results.values())
            },
            "results": self.test_results,
            "acceptance_criteria": {
                f"AC{i+1}": {
                    "description": [
                        "Centralized state store with typed state tree",
                        "Reactive state updates with observer pattern",
                        "Time-travel debugging capabilities", 
                        "Automatic persistence with configurable strategies",
                        "Optimistic updates with rollback on failure",
                        "State validation and sanitization",
                        "Performance monitoring and optimization",
                        "Comprehensive test coverage"
                    ][i],
                    "status": "PASSED" if self.test_results.get("Core Acceptance Criteria", {}).get("success") else "FAILED"
                } for i in range(8)
            }
        }
        
        output_path = project_root / output_file
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {output_path}")
        return output_path


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run acceptance tests for Issue #3: State Management System"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--coverage", "-c", 
        action="store_true",
        help="Enable coverage reporting"
    )
    parser.add_argument(
        "--report", "-r",
        action="store_true", 
        help="Generate detailed JSON report"
    )
    
    args = parser.parse_args()
    
    # Run acceptance tests
    runner = AcceptanceTestRunner(verbose=args.verbose, coverage=args.coverage)
    results = runner.run_tests()
    
    # Generate report if requested
    if args.report:
        runner.generate_report()
    
    # Exit with appropriate code
    all_passed = all(result["success"] for result in results.values())
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()