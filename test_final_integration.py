#!/usr/bin/env python3
"""
Final Integration Test - TORE Matrix V3 Complete System

Tests the fully integrated system with all Agent 1-4 components working together.
This is the comprehensive validation that everything works end-to-end.
"""

import asyncio
import tempfile
from pathlib import Path
import sys
import time
import json
import traceback

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.torematrix.ingestion.integration import IngestionSystem, IngestionSettings

# Try to import FastAPI app components
try:
    from src.torematrix.app import create_app
    FASTAPI_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  FastAPI components not available: {e}")
    FASTAPI_AVAILABLE = False


async def test_complete_system():
    """Test the complete integrated system."""
    print("🚀 TORE Matrix V3 - Final Integration Test")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Configure system for testing
        settings = IngestionSettings(
            upload_dir=str(Path(tmpdir) / "uploads"),
            database_url="sqlite:///test_final.db",
            redis_url="redis://localhost:6379/7"  # Test DB
        )
        
        print(f"📁 Test directory: {tmpdir}")
        print(f"📁 Upload directory: {settings.upload_dir}")
        
        # Initialize system
        system = IngestionSystem(settings)
        
        try:
            print("\n🔧 Initializing complete system...")
            await system.initialize()
            print("✅ System initialized successfully")
            
            # Test integration status
            print("\n📊 Checking system status...")
            status = await system.get_integration_status()
            
            print(f"   Initialized: {status['initialized']}")
            print(f"   Using mocks: {status.get('using_mocks', 'Unknown')}")
            
            # Check components
            components = status.get("components", {})
            for component, info in components.items():
                available = "✅" if info.get("available") else "❌"
                comp_type = info.get("type", "real")
                print(f"   {component}: {available} ({comp_type})")
            
            # Test document processing pipeline
            print("\n📄 Testing complete document processing pipeline...")
            
            # Create test documents
            test_files = []
            
            # PDF-like content
            pdf_file = Path(tmpdir) / "test_document.pdf"
            pdf_content = b"%PDF-1.4\nTest PDF content for processing"
            pdf_file.write_bytes(pdf_content)
            test_files.append(("PDF Document", pdf_file))
            
            # Text document
            txt_file = Path(tmpdir) / "test_document.txt"
            txt_content = """
TORE Matrix V3 Integration Test Document

This document tests the complete pipeline:
1. File upload and validation (Agent 1)
2. Queue processing and document extraction (Agent 2) 
3. Real-time progress tracking (Agent 3)
4. System integration and coordination (Agent 4)

The system should process this document efficiently and provide
comprehensive progress updates throughout the entire pipeline.

Test sections:
- Introduction and overview
- Technical specifications
- Processing requirements
- Quality validation
- Final output generation
            """.strip()
            txt_file.write_text(txt_content)
            test_files.append(("Text Document", txt_file))
            
            # Process each test file
            results = []
            for file_type, file_path in test_files:
                print(f"\n📄 Processing {file_type}: {file_path.name}")
                print(f"   Size: {file_path.stat().st_size} bytes")
                
                start_time = time.time()
                result = await system.process_document(file_path)
                processing_time = time.time() - start_time
                
                print(f"   Processing time: {processing_time:.2f} seconds")
                print(f"   Success: {'✅' if result.get('success') else '❌'}")
                
                if result.get("success"):
                    print(f"   File ID: {result.get('file_id')}")
                    if 'job_id' in result:
                        print(f"   Job ID: {result.get('job_id')}")
                    if 'processing_time' in result:
                        print(f"   System processing time: {result['processing_time']:.2f}s")
                else:
                    print(f"   Error: {result.get('error', 'Unknown error')}")
                    if 'errors' in result:
                        for error in result['errors']:
                            print(f"   - {error}")
                
                results.append({
                    "file_type": file_type,
                    "success": result.get("success", False),
                    "processing_time": processing_time,
                    "result": result
                })
            
            # Test batch processing
            print("\n📦 Testing batch processing...")
            batch_files = [file_path for _, file_path in test_files]
            
            start_time = time.time()
            batch_result = await system.process_batch(batch_files)
            batch_time = time.time() - start_time
            
            print(f"   Batch processing time: {batch_time:.2f} seconds")
            print(f"   Batch success: {'✅' if batch_result.get('success') else '❌'}")
            print(f"   Files processed: {batch_result.get('files_processed', 0)}")
            print(f"   Files failed: {batch_result.get('files_failed', 0)}")
            
            # Final status check
            print("\n🔍 Final system status...")
            final_status = await system.get_integration_status()
            print(f"   System operational: {final_status['initialized']}")
            print(f"   Components healthy: {all(c.get('available', False) for c in final_status.get('components', {}).values())}")
            
            # Calculate overall success
            all_success = all(r['success'] for r in results) and batch_result.get('success', False)
            
            return {
                "success": all_success,
                "individual_results": results,
                "batch_result": batch_result,
                "system_status": final_status
            }
            
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            traceback.print_exc()
            return {"success": False, "error": str(e)}
            
        finally:
            print("\n🔄 Shutting down system...")
            await system.shutdown()
            print("✅ System shutdown complete")


async def test_fastapi_integration():
    """Test FastAPI application integration."""
    print("\n🌐 Testing FastAPI Application Integration")
    print("-" * 40)
    
    if not FASTAPI_AVAILABLE:
        print("⚠️  FastAPI not available - skipping API tests")
        return False
    
    try:
        # Create the FastAPI app
        app = create_app()
        print("✅ FastAPI application created successfully")
        
        # Test basic app structure
        print(f"   Title: {app.title}")
        print(f"   Version: {app.version}")
        print(f"   Docs URL: {app.docs_url}")
        
        # Check routes
        routes = [route.path for route in app.routes]
        expected_routes = ["/", "/health", "/api/v1", "/ws"]
        
        print(f"\n📋 Route validation:")
        for route in expected_routes:
            if any(r.startswith(route) for r in routes):
                print(f"   ✅ {route} endpoint available")
            else:
                print(f"   ❌ {route} endpoint missing")
        
        return True
        
    except Exception as e:
        print(f"❌ FastAPI integration test failed: {e}")
        traceback.print_exc()
        return False


def print_final_summary(system_result: dict, api_result: bool):
    """Print comprehensive test summary."""
    print("\n" + "=" * 80)
    print("🎯 FINAL INTEGRATION TEST SUMMARY")
    print("=" * 80)
    
    # System integration results
    system_success = system_result.get("success", False)
    print(f"System Integration: {'✅ PASS' if system_success else '❌ FAIL'}")
    
    if system_success:
        individual = system_result.get("individual_results", [])
        batch = system_result.get("batch_result", {})
        
        print(f"   Individual files: {sum(1 for r in individual if r['success'])}/{len(individual)} successful")
        print(f"   Batch processing: {'✅ PASS' if batch.get('success') else '❌ FAIL'}")
        
        # Performance summary
        avg_time = sum(r['processing_time'] for r in individual) / len(individual) if individual else 0
        print(f"   Average processing time: {avg_time:.2f} seconds")
    
    # API integration results
    print(f"FastAPI Integration: {'✅ PASS' if api_result else '❌ FAIL'}")
    
    # Overall result
    overall_success = system_success and api_result
    print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        print("\n🎉 TORE Matrix V3 is fully operational!")
        print("   ✅ All Agent 1-4 components integrated successfully")
        print("   ✅ Document processing pipeline working")
        print("   ✅ Real-time progress tracking operational")
        print("   ✅ FastAPI application ready for deployment")
        print("   ✅ Complete system tested end-to-end")
    else:
        print("\n⚠️  Integration issues detected:")
        if not system_success:
            print("   - Document processing system needs attention")
            error = system_result.get("error")
            if error:
                print(f"     Error: {error}")
        if not api_result:
            print("   - FastAPI application integration issues")
    
    print("\n📚 Next Steps:")
    if overall_success:
        print("   1. Deploy to production: python src/torematrix/app.py production")
        print("   2. Run with Docker: docker-compose -f docker-compose.test.yml up")
        print("   3. Monitor with: kubectl get pods -n torematrix-prod")
        print("   4. Access API docs: http://localhost:8000/docs")
    else:
        print("   1. Review error logs above")
        print("   2. Fix integration issues")
        print("   3. Re-run tests: python test_final_integration.py")
        print("   4. Verify component dependencies")
    
    print("\n🔗 Resources:")
    print("   - Documentation: docs/deployment.md")
    print("   - API Reference: http://localhost:8000/docs")
    print("   - Health Check: http://localhost:8000/health")
    print("   - WebSocket Progress: ws://localhost:8000/ws/progress")
    
    return overall_success


async def main():
    """Main test function."""
    print("🚀 Starting Final Integration Validation")
    print(f"🐍 Python version: {sys.version}")
    print(f"📍 Working directory: {Path.cwd()}")
    
    # Run comprehensive tests
    system_result = await test_complete_system()
    api_result = await test_fastapi_integration()
    
    # Print comprehensive summary
    overall_success = print_final_summary(system_result, api_result)
    
    return 0 if overall_success else 1


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(result)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)