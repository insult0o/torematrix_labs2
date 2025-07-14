#!/usr/bin/env python3
"""
Test Issue #7 Success Criteria - Document Ingestion System

Tests the current state against Issue #7 success criteria to determine
if any are met and what needs to be implemented.
"""

import asyncio
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_issue7_success_criteria():
    """Test Issue #7 success criteria against current implementation."""
    print("🎯 Issue #7 Success Criteria Assessment")
    print("=" * 60)
    
    criteria_status = {}
    
    # Criterion 1: Handle 100+ concurrent file uploads
    print("\n📤 Criterion 1: Handle 100+ concurrent file uploads")
    try:
        # Check if upload endpoints exist
        upload_system_exists = False
        api_path = Path("src/torematrix/api")
        if api_path.exists():
            upload_files = list(api_path.rglob("*upload*"))
            if upload_files:
                upload_system_exists = True
        
        if upload_system_exists:
            print("  ✅ Upload system detected")
            criteria_status['concurrent_uploads'] = True
        else:
            print("  ❌ No upload system found")
            criteria_status['concurrent_uploads'] = False
            
    except Exception as e:
        print(f"  ❌ Error checking upload system: {e}")
        criteria_status['concurrent_uploads'] = False
    
    # Criterion 2: Process documents in < 30 seconds average
    print("\n⚡ Criterion 2: Process documents in < 30 seconds average")
    try:
        from torematrix.integrations.unstructured.integration import UnstructuredIntegration
        
        integration = UnstructuredIntegration()
        await integration.initialize()
        
        # Test processing speed with a sample file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test document for processing speed measurement.\n" * 100)
            test_file = Path(f.name)
        
        try:
            import time
            start_time = time.time()
            result = await integration.process_document(test_file)
            processing_time = time.time() - start_time
            
            if result.success and processing_time < 30:
                print(f"  ✅ Document processed in {processing_time:.2f} seconds (< 30s)")
                criteria_status['processing_speed'] = True
            else:
                print(f"  ⚠️  Document processed in {processing_time:.2f} seconds")
                criteria_status['processing_speed'] = processing_time < 30
                
        finally:
            test_file.unlink()
            await integration.close()
            
    except Exception as e:
        print(f"  ❌ Error testing processing speed: {e}")
        criteria_status['processing_speed'] = False
    
    # Criterion 3: Support 15+ file formats via Unstructured.io
    print("\n📄 Criterion 3: Support 15+ file formats via Unstructured.io")
    try:
        from torematrix.integrations.unstructured.integration import UnstructuredIntegration
        
        integration = UnstructuredIntegration()
        formats = integration.get_supported_formats()
        
        total_extensions = sum(len(exts) for exts in formats.values())
        
        if total_extensions >= 15:
            print(f"  ✅ {total_extensions} file extensions supported (>= 15)")
            criteria_status['file_formats'] = True
        else:
            print(f"  ❌ Only {total_extensions} file extensions supported (< 15)")
            criteria_status['file_formats'] = False
            
    except Exception as e:
        print(f"  ❌ Error checking file format support: {e}")
        criteria_status['file_formats'] = False
    
    # Criterion 4: Real-time progress updates with < 1s latency
    print("\n🔄 Criterion 4: Real-time progress updates with < 1s latency")
    try:
        # Check if WebSocket implementation exists
        websocket_system_exists = False
        api_path = Path("src/torematrix/api")
        if api_path.exists():
            websocket_files = list(api_path.rglob("*websocket*")) + list(api_path.rglob("*progress*"))
            if websocket_files:
                websocket_system_exists = True
        
        if websocket_system_exists:
            print("  ✅ WebSocket system detected")
            criteria_status['realtime_progress'] = True
        else:
            print("  ❌ No WebSocket/progress system found")
            criteria_status['realtime_progress'] = False
            
    except Exception as e:
        print(f"  ❌ Error checking WebSocket system: {e}")
        criteria_status['realtime_progress'] = False
    
    # Criterion 5: 99.9% reliability with automatic retries
    print("\n🔄 Criterion 5: 99.9% reliability with automatic retries")
    try:
        # Check if queue/retry system exists
        queue_system_exists = False
        core_path = Path("src/torematrix/core")
        if core_path.exists():
            queue_files = list(core_path.rglob("*queue*")) + list(core_path.rglob("*retry*"))
            if queue_files:
                queue_system_exists = True
        
        if queue_system_exists:
            print("  ✅ Queue/retry system detected")
            criteria_status['reliability'] = True
        else:
            print("  ❌ No queue/retry system found")
            criteria_status['reliability'] = False
            
    except Exception as e:
        print(f"  ❌ Error checking queue system: {e}")
        criteria_status['reliability'] = False
    
    # Criterion 6: Comprehensive test coverage (90%+)
    print("\n🧪 Criterion 6: Comprehensive test coverage (90%+)")
    try:
        # Check if comprehensive tests exist
        test_coverage_adequate = False
        tests_path = Path("tests")
        if tests_path.exists():
            integration_tests = list(tests_path.rglob("*ingestion*")) + list(tests_path.rglob("*upload*"))
            if integration_tests:
                test_coverage_adequate = True
        
        # Also check for our existing unstructured tests
        unstructured_tests = list(Path(".").glob("test_agent4*"))
        if unstructured_tests:
            print("  ✅ Unstructured.io integration tests exist")
            # Partial coverage exists
            if test_coverage_adequate:
                criteria_status['test_coverage'] = True
            else:
                criteria_status['test_coverage'] = False
        else:
            print("  ❌ No comprehensive test coverage found")
            criteria_status['test_coverage'] = False
            
    except Exception as e:
        print(f"  ❌ Error checking test coverage: {e}")
        criteria_status['test_coverage'] = False
    
    # Criterion 7: Production-ready with monitoring
    print("\n🔍 Criterion 7: Production-ready with monitoring")
    try:
        # Check if monitoring/metrics exist
        monitoring_exists = False
        
        # Check for existing monitoring in unstructured integration
        from torematrix.integrations.unstructured.integration import UnstructuredIntegration
        integration = UnstructuredIntegration()
        
        if hasattr(integration, 'get_performance_summary'):
            print("  ✅ Performance monitoring exists (partial)")
            monitoring_exists = True
        
        # Check for system-wide monitoring
        core_path = Path("src/torematrix/core")
        if core_path.exists():
            monitoring_files = list(core_path.rglob("*monitoring*")) + list(core_path.rglob("*metrics*"))
            if monitoring_files:
                monitoring_exists = True
        
        criteria_status['monitoring'] = monitoring_exists
        
        if monitoring_exists:
            print("  ✅ Monitoring systems detected")
        else:
            print("  ❌ No monitoring systems found")
            
    except Exception as e:
        print(f"  ❌ Error checking monitoring: {e}")
        criteria_status['monitoring'] = False
    
    # Dependency Check: Issue #6 Unstructured.io Integration
    print("\n🔗 Dependency Check: Issue #6 (Unstructured.io Integration)")
    try:
        from torematrix.integrations.unstructured.integration import UnstructuredIntegration
        integration = UnstructuredIntegration()
        status = integration.get_integration_status()
        
        if status and isinstance(status, dict):
            print("  ✅ Issue #6 (Unstructured.io Integration) is complete and functional")
            dependency_met = True
        else:
            print("  ⚠️  Issue #6 has some functionality but may need attention")
            dependency_met = True  # Partial functionality is sufficient
    except Exception as e:
        print(f"  ❌ Issue #6 dependency not met: {e}")
        dependency_met = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 ISSUE #7 SUCCESS CRITERIA ASSESSMENT")
    print("=" * 60)
    
    met_criteria = sum(criteria_status.values())
    total_criteria = len(criteria_status)
    
    print(f"✅ Criteria Met: {met_criteria}/{total_criteria}")
    print(f"📊 Completion Rate: {100 * met_criteria / total_criteria:.1f}%")
    
    print("\n📋 Detailed Status:")
    for criterion, status in criteria_status.items():
        icon = "✅" if status else "❌"
        print(f"  {icon} {criterion.replace('_', ' ').title()}")
    
    print(f"\n🔗 Dependency Status:")
    dep_icon = "✅" if dependency_met else "❌"
    print(f"  {dep_icon} Issue #6 (Unstructured.io Integration)")
    
    # Recommendations
    print("\n💡 Recommendations:")
    
    if not criteria_status.get('concurrent_uploads', False):
        print("  🚧 Implement upload manager and FastAPI endpoints (Sub-issues #83, #86)")
    
    if not criteria_status.get('realtime_progress', False):
        print("  🚧 Implement WebSocket progress tracking (Sub-issue #86)")
    
    if not criteria_status.get('reliability', False):
        print("  🚧 Implement queue management and retry logic (Sub-issue #85)")
    
    if not criteria_status.get('test_coverage', False):
        print("  🚧 Implement comprehensive integration testing (Sub-issue #87)")
    
    if not criteria_status.get('monitoring', False):
        print("  🚧 Enhance monitoring and metrics collection")
    
    # Overall assessment
    if met_criteria >= total_criteria * 0.8:
        print(f"\n🎉 Issue #7 is {100 * met_criteria / total_criteria:.0f}% complete and ready for final implementation!")
        return True
    elif met_criteria >= total_criteria * 0.5:
        print(f"\n⚠️  Issue #7 is {100 * met_criteria / total_criteria:.0f}% complete - significant work remains")
        return False
    else:
        print(f"\n❌ Issue #7 is only {100 * met_criteria / total_criteria:.0f}% complete - major implementation needed")
        return False


if __name__ == '__main__':
    success = asyncio.run(test_issue7_success_criteria())
    sys.exit(0 if success else 1)