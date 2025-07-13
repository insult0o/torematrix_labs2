"""
Performance Tests for Processing Pipeline System

Comprehensive performance benchmarks and load tests for the processing pipeline,
measuring throughput, latency, resource efficiency, and scalability.
"""

import pytest
import asyncio
import time
import statistics
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from unittest.mock import Mock, AsyncMock, patch
import psutil
import random

from torematrix.processing.integration import (
    ProcessingSystem,
    ProcessingSystemConfig,
    create_default_config,
    create_high_throughput_config,
    create_memory_efficient_config
)


@dataclass
class PerformanceMetrics:
    """Performance measurement results."""
    total_documents: int
    successful_documents: int
    failed_documents: int
    total_duration: float
    throughput: float  # docs/second
    average_latency: float
    p50_latency: float
    p95_latency: float
    p99_latency: float
    peak_cpu_percent: float
    peak_memory_mb: float
    error_rate: float


class PerformanceTester:
    """Helper class for performance testing."""
    
    def __init__(self, system: ProcessingSystem):
        self.system = system
        self.results: List[Dict[str, Any]] = []
    
    async def run_throughput_test(
        self, 
        documents: List[Path], 
        concurrent_limit: int = 10
    ) -> PerformanceMetrics:
        """Run throughput test with specified concurrency."""
        semaphore = asyncio.Semaphore(concurrent_limit)
        latencies = []
        results = []
        
        # Monitor system resources
        process = psutil.Process()
        initial_cpu = process.cpu_percent()
        initial_memory = process.memory_info().rss / (1024 * 1024)  # MB
        
        peak_cpu = initial_cpu
        peak_memory = initial_memory
        
        async def process_document_with_metrics(doc_path: Path) -> Dict[str, Any]:
            async with semaphore:
                start_time = time.time()
                
                try:
                    # Monitor resources during processing
                    cpu_percent = process.cpu_percent()
                    memory_mb = process.memory_info().rss / (1024 * 1024)
                    
                    nonlocal peak_cpu, peak_memory
                    peak_cpu = max(peak_cpu, cpu_percent)
                    peak_memory = max(peak_memory, memory_mb)
                    
                    # Process document
                    pipeline_id = await self.system.process_document(doc_path)
                    
                    end_time = time.time()
                    latency = end_time - start_time
                    
                    return {
                        "success": True,
                        "latency": latency,
                        "pipeline_id": pipeline_id,
                        "cpu_percent": cpu_percent,
                        "memory_mb": memory_mb
                    }
                    
                except Exception as e:
                    end_time = time.time()
                    latency = end_time - start_time
                    
                    return {
                        "success": False,
                        "latency": latency,
                        "error": str(e),
                        "cpu_percent": process.cpu_percent(),
                        "memory_mb": process.memory_info().rss / (1024 * 1024)
                    }
        
        # Run tests
        start_time = time.time()
        tasks = [process_document_with_metrics(doc) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Process results
        successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
        failed_results = [r for r in results if isinstance(r, dict) and not r.get("success")]
        exception_results = [r for r in results if isinstance(r, Exception)]
        
        total_successful = len(successful_results)
        total_failed = len(failed_results) + len(exception_results)
        total_duration = end_time - start_time
        
        # Calculate latency statistics
        latencies = [r["latency"] for r in successful_results]
        if latencies:
            average_latency = statistics.mean(latencies)
            p50_latency = statistics.median(latencies)
            p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)
            p99_latency = statistics.quantiles(latencies, n=100)[98] if len(latencies) >= 100 else max(latencies)
        else:
            average_latency = p50_latency = p95_latency = p99_latency = 0.0
        
        throughput = total_successful / total_duration if total_duration > 0 else 0.0
        error_rate = total_failed / len(documents) if documents else 0.0
        
        return PerformanceMetrics(
            total_documents=len(documents),
            successful_documents=total_successful,
            failed_documents=total_failed,
            total_duration=total_duration,
            throughput=throughput,
            average_latency=average_latency,
            p50_latency=p50_latency,
            p95_latency=p95_latency,
            p99_latency=p99_latency,
            peak_cpu_percent=peak_cpu,
            peak_memory_mb=peak_memory,
            error_rate=error_rate
        )
    
    async def run_latency_test(self, documents: List[Path]) -> List[float]:
        """Run sequential latency test."""
        latencies = []
        
        for doc in documents:
            start_time = time.time()
            
            try:
                await self.system.process_document(doc)
                end_time = time.time()
                latencies.append(end_time - start_time)
                
            except Exception:
                end_time = time.time()
                latencies.append(end_time - start_time)
        
        return latencies
    
    async def run_resource_efficiency_test(
        self, 
        documents: List[Path],
        duration_seconds: float = 60.0
    ) -> Dict[str, Any]:
        """Test resource efficiency over time."""
        process = psutil.Process()
        
        # Resource monitoring
        cpu_samples = []
        memory_samples = []
        
        # Start processing documents
        start_time = time.time()
        document_iterator = iter(documents * 10)  # Repeat documents if needed
        
        async def monitor_resources():
            while time.time() - start_time < duration_seconds:
                cpu_samples.append(process.cpu_percent())
                memory_samples.append(process.memory_info().rss / (1024 * 1024))
                await asyncio.sleep(1.0)
        
        async def process_documents():
            processed = 0
            while time.time() - start_time < duration_seconds:
                try:
                    doc = next(document_iterator)
                    await self.system.process_document(doc)
                    processed += 1
                except StopIteration:
                    # Restart iterator
                    document_iterator = iter(documents * 10)
                except Exception:
                    pass  # Continue processing
            return processed
        
        # Run monitoring and processing concurrently
        monitor_task = asyncio.create_task(monitor_resources())
        process_task = asyncio.create_task(process_documents())
        
        processed_count = await process_task
        monitor_task.cancel()
        
        end_time = time.time()
        actual_duration = end_time - start_time
        
        return {
            "duration": actual_duration,
            "processed_documents": processed_count,
            "throughput": processed_count / actual_duration,
            "average_cpu": statistics.mean(cpu_samples) if cpu_samples else 0,
            "peak_cpu": max(cpu_samples) if cpu_samples else 0,
            "average_memory_mb": statistics.mean(memory_samples) if memory_samples else 0,
            "peak_memory_mb": max(memory_samples) if memory_samples else 0,
            "cpu_efficiency": processed_count / statistics.mean(cpu_samples) if cpu_samples and statistics.mean(cpu_samples) > 0 else 0
        }


@pytest.fixture
def benchmark_documents(tmp_path) -> List[Path]:
    """Create test documents for benchmarking."""
    documents = []
    
    # Create documents of varying sizes
    sizes = [
        (100, "small"),    # 100 bytes
        (1024, "medium"),  # 1KB
        (10240, "large"),  # 10KB
        (102400, "xlarge") # 100KB
    ]
    
    for i in range(20):  # 20 documents total
        size, size_name = random.choice(sizes)
        
        doc = tmp_path / f"benchmark_{size_name}_{i}.pdf"
        content = f"Benchmark document {i} of size {size_name}\n" + "x" * (size - 50)
        doc.write_bytes(content.encode()[:size])
        documents.append(doc)
    
    return documents


@pytest.fixture
async def mock_processing_system():
    """Create mock processing system for performance tests."""
    config = create_default_config()
    
    with patch('torematrix.processing.integration.PipelineManager') as mock_pipeline, \
         patch('torematrix.processing.integration.WorkerPool') as mock_workers, \
         patch('torematrix.processing.integration.ResourceMonitor') as mock_resources, \
         patch('torematrix.processing.integration.ProcessorRegistry') as mock_registry, \
         patch('torematrix.processing.integration.ProgressTracker') as mock_progress, \
         patch('torematrix.processing.integration.StateStore') as mock_state:
        
        # Configure mocks for performance testing
        pipeline_counter = 0
        
        async def mock_process_delay():
            # Simulate realistic processing delay
            await asyncio.sleep(random.uniform(0.1, 0.5))
            nonlocal pipeline_counter
            pipeline_counter += 1
            return f"pipeline-{pipeline_counter}"
        
        mock_pipeline.return_value.create_pipeline = AsyncMock(side_effect=mock_process_delay)
        mock_pipeline.return_value.execute = AsyncMock()
        mock_pipeline.return_value.get_status.return_value = {"status": "completed"}
        mock_pipeline.return_value.get_stats.return_value = {"active_pipelines": 0}
        
        mock_workers.return_value.get_stats.return_value = {
            "active_workers": 4,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "queued_tasks": 0
        }
        mock_workers.return_value.start = AsyncMock()
        mock_workers.return_value.stop = AsyncMock()
        mock_workers.return_value.wait_for_completion = AsyncMock()
        mock_workers.return_value._running = True
        
        mock_resources.return_value.get_current_usage.return_value = {"cpu": 50.0, "memory": 60.0}
        mock_resources.return_value.start = AsyncMock()
        mock_resources.return_value.stop = AsyncMock()
        mock_resources.return_value._monitoring = True
        
        mock_registry.return_value.list_processors.return_value = ["test_processor"]
        mock_registry.return_value._instances = {}
        mock_registry.return_value.register = Mock()
        mock_registry.return_value.register_dependency = Mock()
        mock_registry.return_value.shutdown = AsyncMock()
        
        mock_state.return_value.load = AsyncMock()
        mock_state.return_value.save = AsyncMock()
        
        system = ProcessingSystem(config)
        await system.initialize()
        
        yield system
        
        await system.shutdown()


class TestThroughputPerformance:
    """Throughput performance tests."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_sequential_throughput(self, mock_processing_system, benchmark_documents):
        """Test sequential document processing throughput."""
        tester = PerformanceTester(mock_processing_system)
        
        # Use subset for sequential test
        test_docs = benchmark_documents[:10]
        
        metrics = await tester.run_throughput_test(test_docs, concurrent_limit=1)
        
        # Assertions
        assert metrics.successful_documents > 0
        assert metrics.throughput > 0.5  # At least 0.5 docs/second
        assert metrics.error_rate < 0.1  # Less than 10% error rate
        
        print(f"Sequential Throughput: {metrics.throughput:.2f} docs/sec")
        print(f"Average Latency: {metrics.average_latency:.2f}s")
        print(f"Error Rate: {metrics.error_rate:.2%}")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_throughput(self, mock_processing_system, benchmark_documents):
        """Test concurrent document processing throughput."""
        tester = PerformanceTester(mock_processing_system)
        
        metrics = await tester.run_throughput_test(benchmark_documents, concurrent_limit=5)
        
        # Assertions
        assert metrics.successful_documents > 0
        assert metrics.throughput > 2.0  # Should be better than sequential
        assert metrics.error_rate < 0.1
        
        print(f"Concurrent Throughput: {metrics.throughput:.2f} docs/sec")
        print(f"P95 Latency: {metrics.p95_latency:.2f}s")
        print(f"Error Rate: {metrics.error_rate:.2%}")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_high_load_throughput(self, mock_processing_system, tmp_path):
        """Test throughput under high load."""
        # Create more documents for high load test
        documents = []
        for i in range(100):
            doc = tmp_path / f"load_test_{i}.pdf"
            doc.write_bytes(f"Load test document {i} content".encode())
            documents.append(doc)
        
        tester = PerformanceTester(mock_processing_system)
        
        metrics = await tester.run_throughput_test(documents, concurrent_limit=10)
        
        # Assertions for high load
        assert metrics.successful_documents >= 80  # At least 80% success
        assert metrics.throughput > 5.0  # Should handle good throughput
        assert metrics.error_rate < 0.2  # Less than 20% error rate under load
        
        print(f"High Load - Processed: {metrics.successful_documents}/{metrics.total_documents}")
        print(f"High Load Throughput: {metrics.throughput:.2f} docs/sec")
        print(f"High Load P99 Latency: {metrics.p99_latency:.2f}s")


class TestLatencyPerformance:
    """Latency performance tests."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_average_latency(self, mock_processing_system, benchmark_documents):
        """Test average processing latency."""
        tester = PerformanceTester(mock_processing_system)
        
        # Test with smaller subset for latency measurement
        test_docs = benchmark_documents[:5]
        latencies = await tester.run_latency_test(test_docs)
        
        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)
        
        # Assertions
        assert avg_latency < 2.0  # Average under 2 seconds
        assert max_latency < 5.0  # Max under 5 seconds
        
        print(f"Average Latency: {avg_latency:.2f}s")
        print(f"Max Latency: {max_latency:.2f}s")
        print(f"Min Latency: {min(latencies):.2f}s")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_latency_consistency(self, mock_processing_system, benchmark_documents):
        """Test latency consistency across multiple runs."""
        tester = PerformanceTester(mock_processing_system)
        
        # Run multiple latency tests
        all_latencies = []
        for run in range(3):
            test_docs = benchmark_documents[:3]
            latencies = await tester.run_latency_test(test_docs)
            all_latencies.extend(latencies)
        
        # Calculate variance
        avg_latency = statistics.mean(all_latencies)
        stdev_latency = statistics.stdev(all_latencies)
        coefficient_of_variation = stdev_latency / avg_latency
        
        # Assertions for consistency
        assert coefficient_of_variation < 0.5  # CV should be less than 50%
        
        print(f"Latency Consistency - Avg: {avg_latency:.2f}s")
        print(f"Latency Consistency - StdDev: {stdev_latency:.2f}s")
        print(f"Latency Consistency - CV: {coefficient_of_variation:.2%}")


class TestResourceEfficiency:
    """Resource efficiency tests."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_cpu_efficiency(self, mock_processing_system, benchmark_documents):
        """Test CPU usage efficiency."""
        tester = PerformanceTester(mock_processing_system)
        
        # Run resource efficiency test
        results = await tester.run_resource_efficiency_test(
            benchmark_documents[:5],  # Smaller set for efficiency test
            duration_seconds=10.0
        )
        
        # Assertions
        assert results["average_cpu"] < 80.0  # CPU under 80%
        assert results["cpu_efficiency"] > 0.1  # At least 0.1 docs per CPU%
        
        print(f"CPU Efficiency: {results['cpu_efficiency']:.2f} docs per CPU%")
        print(f"Average CPU: {results['average_cpu']:.1f}%")
        print(f"Peak CPU: {results['peak_cpu']:.1f}%")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_efficiency(self, mock_processing_system, benchmark_documents):
        """Test memory usage efficiency."""
        tester = PerformanceTester(mock_processing_system)
        
        results = await tester.run_resource_efficiency_test(
            benchmark_documents[:5],
            duration_seconds=10.0
        )
        
        # Check memory growth
        memory_growth = results["peak_memory_mb"] - results["average_memory_mb"]
        
        # Assertions
        assert results["peak_memory_mb"] < 1000  # Peak memory under 1GB
        assert memory_growth < 500  # Memory growth under 500MB
        
        print(f"Average Memory: {results['average_memory_mb']:.1f} MB")
        print(f"Peak Memory: {results['peak_memory_mb']:.1f} MB")
        print(f"Memory Growth: {memory_growth:.1f} MB")


class TestScalabilityPerformance:
    """Scalability performance tests."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_worker_scaling(self, tmp_path):
        """Test performance scaling with different worker configurations."""
        documents = []
        for i in range(20):
            doc = tmp_path / f"scale_test_{i}.pdf"
            doc.write_bytes(f"Scale test document {i}".encode())
            documents.append(doc)
        
        # Test different worker configurations
        configs = [
            (2, 1, "Low"),
            (4, 2, "Medium"),
            (8, 4, "High")
        ]
        
        results = {}
        
        for async_workers, thread_workers, config_name in configs:
            config = create_default_config()
            config.worker_config.async_workers = async_workers
            config.worker_config.thread_workers = thread_workers
            
            with patch('torematrix.processing.integration.PipelineManager') as mock_pipeline, \
                 patch('torematrix.processing.integration.WorkerPool') as mock_workers, \
                 patch('torematrix.processing.integration.ResourceMonitor') as mock_resources, \
                 patch('torematrix.processing.integration.ProcessorRegistry') as mock_registry, \
                 patch('torematrix.processing.integration.ProgressTracker') as mock_progress, \
                 patch('torematrix.processing.integration.StateStore') as mock_state:
                
                # Configure mocks
                pipeline_counter = 0
                async def mock_process():
                    await asyncio.sleep(0.1)  # Consistent delay
                    nonlocal pipeline_counter
                    pipeline_counter += 1
                    return f"pipeline-{pipeline_counter}"
                
                mock_pipeline.return_value.create_pipeline = AsyncMock(side_effect=mock_process)
                mock_pipeline.return_value.execute = AsyncMock()
                mock_workers.return_value.start = AsyncMock()
                mock_workers.return_value.stop = AsyncMock()
                mock_workers.return_value.wait_for_completion = AsyncMock()
                mock_workers.return_value._running = True
                mock_workers.return_value.get_stats.return_value = {"active_workers": async_workers}
                mock_resources.return_value.start = AsyncMock()
                mock_resources.return_value.stop = AsyncMock()
                mock_resources.return_value._monitoring = True
                mock_resources.return_value.get_current_usage.return_value = {"cpu": 50.0}
                mock_registry.return_value.list_processors.return_value = ["test"]
                mock_registry.return_value._instances = {}
                mock_registry.return_value.register = Mock()
                mock_registry.return_value.register_dependency = Mock()
                mock_registry.return_value.shutdown = AsyncMock()
                mock_state.return_value.load = AsyncMock()
                mock_state.return_value.save = AsyncMock()
                
                system = ProcessingSystem(config)
                await system.initialize()
                
                try:
                    tester = PerformanceTester(system)
                    metrics = await tester.run_throughput_test(documents, concurrent_limit=async_workers)
                    results[config_name] = metrics
                    
                finally:
                    await system.shutdown()
        
        # Compare results
        low_throughput = results["Low"].throughput
        high_throughput = results["High"].throughput
        
        # High config should perform better
        assert high_throughput >= low_throughput
        
        for config_name, metrics in results.items():
            print(f"{config_name} Config - Throughput: {metrics.throughput:.2f} docs/sec")
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_queue_scaling(self, mock_processing_system, tmp_path):
        """Test performance with varying queue sizes."""
        # Create documents for queue test
        documents = []
        for i in range(50):
            doc = tmp_path / f"queue_test_{i}.pdf"
            doc.write_bytes(f"Queue test document {i}".encode())
            documents.append(doc)
        
        tester = PerformanceTester(mock_processing_system)
        
        # Test with high concurrency to stress queue
        metrics = await tester.run_throughput_test(documents, concurrent_limit=20)
        
        # Should handle queue pressure well
        assert metrics.successful_documents > 40  # At least 80% success
        assert metrics.throughput > 8.0  # Good throughput despite queue pressure
        
        print(f"Queue Scaling - Throughput: {metrics.throughput:.2f} docs/sec")
        print(f"Queue Scaling - Success Rate: {metrics.successful_documents/metrics.total_documents:.2%}")


class TestPerformanceRegression:
    """Performance regression tests."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_baseline(self, mock_processing_system, benchmark_documents):
        """Establish performance baseline for regression testing."""
        tester = PerformanceTester(mock_processing_system)
        
        # Standard test
        metrics = await tester.run_throughput_test(benchmark_documents, concurrent_limit=5)
        
        # Record baseline metrics (these would be compared against in CI)
        baseline = {
            "throughput": metrics.throughput,
            "p95_latency": metrics.p95_latency,
            "error_rate": metrics.error_rate,
            "peak_cpu": metrics.peak_cpu_percent,
            "peak_memory": metrics.peak_memory_mb
        }
        
        print("Performance Baseline:")
        for metric, value in baseline.items():
            print(f"  {metric}: {value}")
        
        # Basic sanity checks
        assert baseline["throughput"] > 1.0
        assert baseline["p95_latency"] < 10.0
        assert baseline["error_rate"] < 0.2
        
        # In a real scenario, you would save/compare against historical baselines
        return baseline


# Utility functions for performance analysis

def analyze_performance_trends(metrics_history: List[PerformanceMetrics]) -> Dict[str, Any]:
    """Analyze performance trends across multiple test runs."""
    if not metrics_history:
        return {}
    
    throughputs = [m.throughput for m in metrics_history]
    latencies = [m.average_latency for m in metrics_history]
    error_rates = [m.error_rate for m in metrics_history]
    
    return {
        "throughput": {
            "mean": statistics.mean(throughputs),
            "median": statistics.median(throughputs),
            "trend": "improving" if throughputs[-1] > throughputs[0] else "degrading"
        },
        "latency": {
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "trend": "improving" if latencies[-1] < latencies[0] else "degrading"
        },
        "reliability": {
            "mean_error_rate": statistics.mean(error_rates),
            "trend": "improving" if error_rates[-1] < error_rates[0] else "degrading"
        }
    }


@pytest.mark.performance
def test_performance_summary():
    """Print performance test summary."""
    print("\n" + "="*50)
    print("PERFORMANCE TEST SUMMARY")
    print("="*50)
    print("Tests completed. Check individual test outputs for detailed metrics.")
    print("Key Performance Indicators:")
    print("- Throughput: Documents processed per second")
    print("- Latency: Time to process individual documents")
    print("- Resource Efficiency: CPU/Memory usage vs. throughput")
    print("- Error Rate: Percentage of failed processing attempts")
    print("="*50)