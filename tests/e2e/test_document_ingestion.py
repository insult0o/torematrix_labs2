"""
End-to-End tests for the Document Ingestion System.

These tests verify the complete pipeline from file upload through processing
to final results, testing integration between all components.
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
import time
from typing import List, Dict, Any
import uuid

from src.torematrix.ingestion.integration import IngestionSystem, IngestionSettings
from src.torematrix.ingestion.models import FileStatus, FileType
from tests.fixtures.ingestion_fixtures import (
    create_test_files,
    create_test_dataset,
    generate_random_content,
    TestDataGenerator,
    cleanup_test_files
)


@pytest.fixture
async def temp_directory():
    """Create temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
async def ingestion_system(temp_directory):
    """Create and initialize ingestion system for testing."""
    settings = IngestionSettings(
        upload_dir=str(temp_directory / "uploads"),
        database_url="sqlite:///test_ingestion.db",
        redis_url="redis://localhost:6379/1",  # Use different DB for tests
        max_file_size=50 * 1024 * 1024  # 50MB for tests
    )
    
    system = IngestionSystem(settings)
    await system.initialize()
    
    yield system
    
    await system.shutdown()


@pytest.fixture
def test_data_generator(temp_directory):
    """Create test data generator."""
    generator = TestDataGenerator(temp_directory)
    yield generator
    generator.cleanup()


class TestDocumentIngestionE2E:
    """End-to-end tests for the complete document ingestion pipeline."""
    
    @pytest.mark.asyncio
    async def test_single_file_processing(self, ingestion_system, temp_directory):
        """Test processing a single file through the complete pipeline."""
        # Create test file
        test_files = create_test_files([
            ("test_document.txt", "This is a test document for processing.")
        ], temp_directory)
        
        try:
            # Process the document
            result = await ingestion_system.process_document(test_files[0])
            
            # Verify successful processing
            assert result["success"] is True
            assert "file_id" in result
            assert "job_id" in result
            assert result["processing_time"] > 0
            
        finally:
            cleanup_test_files(test_files)
    
    @pytest.mark.asyncio
    async def test_multiple_file_types(self, ingestion_system, temp_directory):
        """Test processing multiple different file types."""
        # Create files of different types
        test_specs = [
            ("document.txt", "Plain text document content."),
            ("report.html", "<h1>HTML Report</h1><p>This is an HTML document.</p>"),
            ("data.json", '{"title": "Test Data", "content": "JSON content"}'),
            ("spreadsheet.csv", "Name,Value\nItem 1,100\nItem 2,200")
        ]
        
        test_files = create_test_files(test_specs, temp_directory)
        
        try:
            results = []
            for file_path in test_files:
                result = await ingestion_system.process_document(file_path)
                results.append((file_path.name, result))
            
            # Verify all files processed successfully
            for filename, result in results:
                assert result["success"] is True, f"Failed to process {filename}: {result.get('error')}"
                
            # Verify different file types were handled
            processed_types = {r[0].split('.')[-1] for r in results}
            assert len(processed_types) == 4  # txt, html, json, csv
            
        finally:
            cleanup_test_files(test_files)
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, ingestion_system, test_data_generator):
        """Test processing multiple files concurrently."""
        # Create batch of test files
        test_files = test_data_generator.create_document_batch(5)
        
        # Process all files concurrently
        tasks = [
            ingestion_system.process_document(file_path)
            for file_path in test_files
        ]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        processing_time = time.time() - start_time
        
        # Verify results
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_results = [r for r in results if not (isinstance(r, dict) and r.get("success"))]
        
        assert len(successful_results) >= 3, f"Expected at least 3 successful results, got {len(successful_results)}"
        assert len(failed_results) <= 2, f"Too many failures: {failed_results}"
        
        # Verify concurrent processing was faster than sequential
        # (This is a rough heuristic - real concurrent processing should be faster)
        assert processing_time < len(test_files) * 5, "Concurrent processing seems too slow"
    
    @pytest.mark.asyncio
    async def test_large_file_processing(self, ingestion_system, temp_directory):
        """Test processing larger files."""
        # Create a moderately large text file
        large_content = generate_random_content(words=5000)  # ~30-50KB of text
        test_files = create_test_files([
            ("large_document.txt", large_content)
        ], temp_directory)
        
        try:
            start_time = time.time()
            result = await ingestion_system.process_document(test_files[0])
            processing_time = time.time() - start_time
            
            # Verify processing
            assert result["success"] is True
            assert processing_time < 30, f"Large file processing took too long: {processing_time}s"
            
        finally:
            cleanup_test_files(test_files)
    
    @pytest.mark.asyncio
    async def test_error_handling(self, ingestion_system, temp_directory):
        """Test error handling for invalid files."""
        # Create problematic files
        problematic_files = [
            ("empty.txt", ""),  # Empty file
            ("binary_junk.pdf", "Not a real PDF file content"),  # Wrong format
        ]
        
        test_files = create_test_files(problematic_files, temp_directory)
        
        try:
            results = []
            for file_path in test_files:
                result = await ingestion_system.process_document(file_path)
                results.append((file_path.name, result))
            
            # Check that some files failed as expected
            failed_count = sum(1 for _, result in results if not result.get("success"))
            assert failed_count > 0, "Expected some files to fail validation/processing"
            
            # Verify error messages are provided
            for filename, result in results:
                if not result.get("success"):
                    assert "error" in result or "errors" in result, f"No error info for failed file {filename}"
                    
        finally:
            cleanup_test_files(test_files)
    
    @pytest.mark.asyncio
    async def test_integration_status(self, ingestion_system):
        """Test getting integration status and component health."""
        status = await ingestion_system.get_integration_status()
        
        # Verify status structure
        assert "initialized" in status
        assert "components" in status
        assert status["initialized"] is True
        
        # Check component status
        components = status["components"]
        expected_components = [
            "unstructured", "upload_manager", "queue_manager", 
            "progress_tracker", "websocket_handler"
        ]
        
        for component in expected_components:
            assert component in components, f"Missing component: {component}"
            assert "available" in components[component]
    
    @pytest.mark.asyncio
    async def test_realistic_document_batch(self, ingestion_system, test_data_generator):
        """Test processing a realistic batch of documents."""
        # Create realistic report
        report_file = test_data_generator.create_realistic_report("quarterly_report.txt")
        
        # Create additional documents
        additional_files = test_data_generator.create_document_batch(3, ['txt', 'html', 'json'])
        
        all_files = [report_file] + additional_files
        
        # Process all files
        results = []
        for file_path in all_files:
            result = await ingestion_system.process_document(file_path)
            results.append(result)
        
        # Verify processing
        successful_count = sum(1 for r in results if r.get("success"))
        assert successful_count >= len(all_files) * 0.8, "Too many processing failures"
        
        # Verify processing times are reasonable
        processing_times = [r.get("processing_time", 0) for r in results if r.get("success")]
        if processing_times:
            avg_time = sum(processing_times) / len(processing_times)
            assert avg_time < 15, f"Average processing time too high: {avg_time}s"
    
    @pytest.mark.asyncio
    async def test_system_stress(self, ingestion_system, test_data_generator):
        """Stress test with many files."""
        # Create many small files
        test_files = test_data_generator.create_document_batch(10)
        
        # Process in smaller concurrent batches to avoid overwhelming
        batch_size = 3
        all_results = []
        
        for i in range(0, len(test_files), batch_size):
            batch = test_files[i:i + batch_size]
            batch_tasks = [
                ingestion_system.process_document(file_path)
                for file_path in batch
            ]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            all_results.extend(batch_results)
            
            # Small delay between batches
            await asyncio.sleep(0.5)
        
        # Analyze results
        successful = [r for r in all_results if isinstance(r, dict) and r.get("success")]
        failed = [r for r in all_results if not (isinstance(r, dict) and r.get("success"))]
        
        success_rate = len(successful) / len(all_results)
        assert success_rate >= 0.7, f"Success rate too low: {success_rate:.2%}"
        
        # Verify system is still responsive
        status = await ingestion_system.get_integration_status()
        assert status["initialized"] is True


class TestIngestionSystemHealth:
    """Tests for system health monitoring and diagnostics."""
    
    @pytest.mark.asyncio
    async def test_system_initialization(self, temp_directory):
        """Test system initialization and shutdown."""
        settings = IngestionSettings(
            upload_dir=str(temp_directory / "test_uploads")
        )
        
        system = IngestionSystem(settings)
        
        # Test initialization
        await system.initialize()
        assert system._initialized is True
        
        # Test status after init
        status = await system.get_integration_status()
        assert status["initialized"] is True
        
        # Test shutdown
        await system.shutdown()
        assert system._initialized is False
    
    @pytest.mark.asyncio
    async def test_mock_component_detection(self, ingestion_system):
        """Test that mock components are properly detected."""
        status = await ingestion_system.get_integration_status()
        
        # Should be using mocks if real components aren't available
        if status.get("using_mocks"):
            components = status["components"]
            
            # Check for mock indicators
            mock_components = [
                comp for comp, info in components.items()
                if info.get("type") == "mock"
            ]
            
            # At least some components should be mocks in test environment
            assert len(mock_components) > 0, "Expected some mock components in test environment"
    
    @pytest.mark.asyncio
    async def test_unstructured_integration(self, ingestion_system):
        """Test Unstructured.io integration status."""
        status = await ingestion_system.get_integration_status()
        unstructured_status = status["components"]["unstructured"]
        
        # Should have some status information
        assert "available" in unstructured_status
        
        # If available, should have format information
        if unstructured_status["available"]:
            assert "supported_formats" in unstructured_status or "status" in unstructured_status


# Performance test markers
@pytest.mark.performance
class TestPerformanceBaseline:
    """Basic performance tests to establish baselines."""
    
    @pytest.mark.asyncio
    async def test_single_file_speed(self, ingestion_system, temp_directory):
        """Measure processing speed for single file."""
        content = generate_random_content(500)  # Medium-sized content
        test_files = create_test_files([("speed_test.txt", content)], temp_directory)
        
        try:
            start_time = time.time()
            result = await ingestion_system.process_document(test_files[0])
            total_time = time.time() - start_time
            
            if result.get("success"):
                # Should process reasonably quickly
                assert total_time < 10, f"Single file processing too slow: {total_time}s"
                print(f"Single file processing time: {total_time:.2f}s")
            
        finally:
            cleanup_test_files(test_files)
    
    @pytest.mark.asyncio
    async def test_throughput_estimate(self, ingestion_system, test_data_generator):
        """Estimate system throughput."""
        # Process small batch and measure
        test_files = test_data_generator.create_document_batch(5)
        
        start_time = time.time()
        tasks = [ingestion_system.process_document(f) for f in test_files]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        successful = [r for r in results if isinstance(r, dict) and r.get("success")]
        
        if successful:
            throughput = len(successful) / total_time
            print(f"Estimated throughput: {throughput:.2f} files/second")
            
            # Basic throughput expectation
            assert throughput > 0.1, f"Throughput too low: {throughput} files/s"