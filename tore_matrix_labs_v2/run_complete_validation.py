#!/usr/bin/env python3
"""
Complete Validation Runner for TORE Matrix Labs V2

This is the single entry point script that executes the entire validation
framework without any manual intervention.

Usage:
    python run_complete_validation.py

This script will:
1. Test every single function in the V2 codebase
2. Validate all requirements against implementation
3. Compare performance against V1 baseline
4. Verify migration completeness
5. Generate comprehensive reports
6. Provide clear pass/fail results

NO MANUAL INTERVENTION REQUIRED - Fully automated testing
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add test validation directory to path
sys.path.append(str(Path(__file__).parent / "tests" / "validation"))

from master_test_orchestrator import MasterTestOrchestrator


def print_banner():
    """Print validation banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    TORE Matrix Labs V2 - Complete Validation                ║
║                                                                              ║
║  🧪 Testing every single endpoint, function, and tool                       ║
║  📋 Validating all requirements and planned features                        ║
║  ⚡ Benchmarking performance against V1 baseline                           ║
║  🔄 Verifying complete migration capabilities                               ║
║  📊 Generating comprehensive comparison reports                             ║
║                                                                              ║
║  🚀 NO MANUAL INTERVENTION REQUIRED - Fully Automated                      ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_phase_header(phase_name: str, phase_num: int, total_phases: int):
    """Print phase header."""
    print("\n" + "=" * 80)
    print(f"📋 PHASE {phase_num}/{total_phases}: {phase_name}")
    print("=" * 80)


def print_summary(session):
    """Print validation summary."""
    print("\n" + "╔" + "═" * 78 + "╗")
    print("║" + " " * 25 + "VALIDATION COMPLETE" + " " * 33 + "║")
    print("╚" + "═" * 78 + "╝")
    
    # Overall status
    status_emoji = "✅" if session.overall_status == "completed" else "❌"
    print(f"\n{status_emoji} Overall Status: {session.overall_status.upper()}")
    
    # Phase summary
    completed_phases = len([p for p in session.phases if p.status == "completed"])
    failed_phases = len([p for p in session.phases if p.status == "failed"])
    
    print(f"📊 Testing Phases: {completed_phases}/{len(session.phases)} completed")
    if failed_phases > 0:
        print(f"❌ Failed Phases: {failed_phases}")
    
    # Test statistics
    if session.summary_report:
        testing_summary = session.summary_report.get("testing_summary", {})
        requirements_compliance = session.summary_report.get("requirements_compliance", {})
        
        print(f"\n📈 Test Results:")
        print(f"   • Total Tests: {testing_summary.get('total_tests', 0)}")
        print(f"   • Pass Rate: {testing_summary.get('overall_pass_rate', 0):.1f}%")
        print(f"   • Requirements Compliance: {requirements_compliance.get('compliance_score', 0):.1f}%")
    
    # Recommendations
    if session.recommendations:
        print(f"\n💡 Top Recommendations:")
        for i, rec in enumerate(session.recommendations[:3], 1):
            print(f"   {i}. {rec}")
    
    print(f"\n📁 Detailed reports saved to: master_validation_results/")
    print("   • master_validation_report.html (Interactive report)")
    print("   • executive_summary.md (Executive summary)")
    print("   • Detailed test data and analysis")


def main():
    """Main validation execution."""
    start_time = time.time()
    
    print_banner()
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Working directory: {Path.cwd()}")
    
    try:
        # Initialize and run master validation
        print_phase_header("Master Test Orchestration", 1, 1)
        print("🚀 Initializing comprehensive validation system...")
        
        orchestrator = MasterTestOrchestrator()
        session = orchestrator.execute_master_validation()
        
        print("📊 Generating comprehensive reports...")
        orchestrator.export_master_report()
        
        # Print summary
        print_summary(session)
        
        # Calculate total time
        total_time = time.time() - start_time
        print(f"\n⏱️ Total validation time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
        
        # Exit with appropriate code
        if session.overall_status == "completed":
            print("\n🎉 All validation completed successfully!")
            print("✅ V2 system is ready for production use")
            return 0
        else:
            print("\n⚠️ Validation completed with issues")
            print("🔍 Please review the detailed reports for specific problems")
            return 1
            
    except KeyboardInterrupt:
        print("\n⚠️ Validation interrupted by user")
        return 130
        
    except Exception as e:
        print(f"\n❌ Validation failed with error: {str(e)}")
        print("🔍 Check the logs for detailed error information")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)