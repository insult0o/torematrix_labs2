"""
Performance tests for the Document Ingestion System.

These tests measure throughput, latency, memory usage, and system limits
to ensure the ingestion system meets performance requirements.
"""

import pytest
import asyncio
import time
import psutil
import gc
import statistics
from pathlib import Path
import tempfile
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
import resource

from src.torematrix.ingestion.integration import IngestionSystem, IngestionSettings
from tests.fixtures.ingestion_fixtures import (
    create_test_files,
    create_large_test_file,
    generate_random_content,
    TestDataGenerator,
    cleanup_test_files
)


@pytest.fixture
async def performance_system():
    """Create ingestion system optimized for performance testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        settings = IngestionSettings(
            upload_dir=str(Path(tmpdir) / "uploads"),
            database_url="sqlite:///perf_test.db",
            redis_url="redis://localhost:6379/2",  # Separate DB for perf tests
            max_workers=10,  # Higher concurrency for performance tests
            max_file_size=200 * 1024 * 1024  # 200MB for large file tests
        )
        
        system = IngestionSystem(settings)
        await system.initialize()
        
        yield system
        
        await system.shutdown()


@pytest.fixture
def performance_data_generator():
    """Create test data generator for performance tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        generator = TestDataGenerator(Path(tmpdir))
        yield generator
        generator.cleanup()


class PerformanceMonitor:
    """Monitor system performance during tests."""
    
    def __init__(self):
        self.process = psutil.Process()
        self.start_time = None
        self.start_memory = None
        self.measurements = []
    
    def start(self):
        """Start performance monitoring."""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.measurements = []
    
    def sample(self):
        """Take a performance sample."""
        current_time = time.time()
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        cpu_percent = self.process.cpu_percent()
        
        self.measurements.append({
            'time': current_time,
            'memory_mb': memory_mb,
            'cpu_percent': cpu_percent,
            'elapsed': current_time - self.start_time
        })
    
    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.measurements:
            return {}
        
        memory_values = [m['memory_mb'] for m in self.measurements]
        cpu_values = [m['cpu_percent'] for m in self.measurements]
        
        return {
            'duration': self.measurements[-1]['elapsed'],
            'memory': {
                'start_mb': self.start_memory,
                'peak_mb': max(memory_values),
                'final_mb': memory_values[-1],
                'increase_mb': max(memory_values) - self.start_memory,
                'avg_mb': statistics.mean(memory_values)
            },
            'cpu': {
                'peak_percent': max(cpu_values),
                'avg_percent': statistics.mean(cpu_values)
            }
        }


@pytest.mark.performance
class TestIngestionThroughput:
    """Test document processing throughput under various conditions."""
    
    @pytest.mark.asyncio
    async def test_sequential_throughput(self, performance_system, performance_data_generator):
        """Measure sequential document processing throughput."""
        # Create test documents
        num_docs = 20
        test_files = performance_data_generator.create_document_batch(
            num_docs, ['txt', 'html', 'json']
        )
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        # Process documents sequentially
        results = []
        start_time = time.time()
        
        for file_path in test_files:
            monitor.sample()
            result = await performance_system.process_document(file_path)
            results.append(result)
        
        total_time = time.time() - start_time
        
        # Calculate metrics
        successful = [r for r in results if r.get("success")]
        throughput = len(successful) / total_time
        avg_time_per_doc = total_time / len(successful) if successful else 0
        
        stats = monitor.get_stats()
        
        print(f"\nSequential Throughput Results:")
        print(f"  Documents processed: {len(successful)}/{num_docs}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {throughput:.2f} docs/second")
        print(f"  Average time per doc: {avg_time_per_doc:.2f}s")
        print(f"  Memory increase: {stats['memory']['increase_mb']:.1f} MB")
        print(f"  Peak CPU: {stats['cpu']['peak_percent']:.1f}%")
        
        # Performance assertions
        assert throughput > 0.5, f"Sequential throughput too low: {throughput:.2f} docs/s"
        assert avg_time_per_doc < 10, f"Average processing time too high: {avg_time_per_doc:.2f}s"
        assert stats['memory']['increase_mb'] < 500, "Memory usage increase too high"
    
    @pytest.mark.asyncio
    async def test_concurrent_throughput(self, performance_system, performance_data_generator):
        """Measure concurrent document processing throughput."""
        num_docs = 20
        concurrency_levels = [1, 3, 5, 10]
        
        test_files = performance_data_generator.create_document_batch(num_docs)
        
        results_by_concurrency = {}
        
        for concurrency in concurrency_levels:
            if concurrency > len(test_files):
                continue
                
            monitor = PerformanceMonitor()
            monitor.start()
            
            # Process with specified concurrency
            semaphore = asyncio.Semaphore(concurrency)
            
            async def process_with_limit(file_path):
                async with semaphore:
                    return await performance_system.process_document(file_path)
            
            start_time = time.time()
            tasks = [process_with_limit(f) for f in test_files[:num_docs]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            total_time = time.time() - start_time
            
            # Calculate metrics
            successful = [r for r in results if isinstance(r, dict) and r.get("success")]
            throughput = len(successful) / total_time
            
            stats = monitor.get_stats()
            
            results_by_concurrency[concurrency] = {
                'throughput': throughput,
                'total_time': total_time,
                'successful': len(successful),
                'memory_increase': stats['memory']['increase_mb'],
                'peak_cpu': stats['cpu']['peak_percent']
            }
        
        # Print results
        print(f"\nConcurrent Throughput Results:")
        for concurrency, metrics in results_by_concurrency.items():
            print(f"  Concurrency {concurrency}: {metrics['throughput']:.2f} docs/s "
                  f"({metrics['successful']} docs in {metrics['total_time']:.2f}s)")
        
        # Verify concurrency improves performance
        if 1 in results_by_concurrency and 5 in results_by_concurrency:
            single_throughput = results_by_concurrency[1]['throughput']
            concurrent_throughput = results_by_concurrency[5]['throughput']
            improvement = concurrent_throughput / single_throughput
            
            print(f"  Concurrency improvement: {improvement:.2f}x")
            assert improvement > 1.5, f"Concurrency improvement too low: {improvement:.2f}x"
    
    @pytest.mark.asyncio
    async def test_batch_size_optimization(self, performance_system, performance_data_generator):
        """Test optimal batch sizes for processing."""
        total_files = 30
        batch_sizes = [1, 5, 10, 15]
        
        test_files = performance_data_generator.create_document_batch(total_files)
        
        batch_results = {}
        
        for batch_size in batch_sizes:
            monitor = PerformanceMonitor()
            monitor.start()
            
            # Process in batches
            start_time = time.time()
            all_results = []
            
            for i in range(0, len(test_files), batch_size):
                batch = test_files[i:i + batch_size]
                batch_tasks = [
                    performance_system.process_document(f) for f in batch
                ]
                batch_results_raw = await asyncio.gather(*batch_tasks, return_exceptions=True)
                all_results.extend(batch_results_raw)
                
                # Small delay between batches to simulate real usage
                if i + batch_size < len(test_files):
                    await asyncio.sleep(0.1)
            
            total_time = time.time() - start_time
            
            successful = [r for r in all_results if isinstance(r, dict) and r.get("success")]
            throughput = len(successful) / total_time
            
            stats = monitor.get_stats()
            
            batch_results[batch_size] = {
                'throughput': throughput,
                'total_time': total_time,
                'memory_peak': stats['memory']['peak_mb'],
                'successful': len(successful)
            }
        
        # Print results
        print(f"\nBatch Size Optimization Results:")
        for batch_size, metrics in batch_results.items():
            print(f"  Batch size {batch_size}: {metrics['throughput']:.2f} docs/s "
                  f"(peak memory: {metrics['memory_peak']:.1f} MB)")
        
        # Find optimal batch size
        best_batch_size = max(batch_results.keys(), 
                             key=lambda k: batch_results[k]['throughput'])
        print(f"  Optimal batch size: {best_batch_size}")


@pytest.mark.performance
class TestIngestionScalability:
    """Test system scalability with increasing load."""
    
    @pytest.mark.asyncio
    async def test_file_size_scaling(self, performance_system):
        """Test processing time scaling with file size."""
        file_sizes = [1, 5, 10, 25]  # MB
        
        with tempfile.TemporaryDirectory() as tmpdir:
            scaling_results = {}
            
            for size_mb in file_sizes:
                # Create large file
                large_file = create_large_test_file(size_mb, 
                    str(Path(tmpdir) / f"large_{size_mb}mb.bin"))
                
                try:
                    monitor = PerformanceMonitor()
                    monitor.start()
                    
                    start_time = time.time()
                    result = await performance_system.process_document(large_file)
                    processing_time = time.time() - start_time
                    
                    stats = monitor.get_stats()
                    
                    scaling_results[size_mb] = {
                        'processing_time': processing_time,
                        'success': result.get("success", False),
                        'memory_increase': stats['memory']['increase_mb'],
                        'throughput_mbps': size_mb / processing_time if result.get("success") else 0
                    }
                    
                finally:
                    if large_file.exists():
                        large_file.unlink()
            
            # Print results
            print(f"\nFile Size Scaling Results:")
            for size_mb, metrics in scaling_results.items():
                if metrics['success']:
                    print(f"  {size_mb} MB: {metrics['processing_time']:.2f}s "
                          f"({metrics['throughput_mbps']:.2f} MB/s)")
                else:
                    print(f"  {size_mb} MB: FAILED")
            
            # Verify reasonable scaling
            successful_results = {k: v for k, v in scaling_results.items() if v['success']}
            if len(successful_results) >= 2:
                sizes = sorted(successful_results.keys())
                small_time = successful_results[sizes[0]]['processing_time']
                large_time = successful_results[sizes[-1]]['processing_time']
                
                # Should scale sub-linearly (better than O(n))
                size_ratio = sizes[-1] / sizes[0]
                time_ratio = large_time / small_time
                
                print(f"  Scaling ratio: {time_ratio:.2f}x time for {size_ratio:.2f}x size")
                assert time_ratio < size_ratio * 2, "File size scaling too poor"
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self, performance_system, performance_data_generator):
        """Test memory usage behavior under sustained load."""
        batch_count = 5
        files_per_batch = 10
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        memory_samples = []
        
        for batch_num in range(batch_count):
            print(f"Processing batch {batch_num + 1}/{batch_count}")
            
            # Create fresh files for each batch
            test_files = performance_data_generator.create_document_batch(files_per_batch)
            
            # Process batch
            batch_start = time.time()
            tasks = [performance_system.process_document(f) for f in test_files]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            batch_time = time.time() - batch_start
            
            # Sample memory after batch
            monitor.sample()
            current_memory = monitor.measurements[-1]['memory_mb']
            memory_samples.append(current_memory)
            
            successful = [r for r in results if isinstance(r, dict) and r.get("success")]
            print(f"  Batch {batch_num + 1}: {len(successful)}/{files_per_batch} files "
                  f"in {batch_time:.2f}s, Memory: {current_memory:.1f} MB")
            
            # Force garbage collection between batches
            gc.collect()
            await asyncio.sleep(1)  # Allow cleanup
        
        stats = monitor.get_stats()
        
        # Analyze memory usage
        memory_growth = memory_samples[-1] - memory_samples[0]
        max_memory = max(memory_samples)
        
        print(f"\nMemory Usage Analysis:")
        print(f"  Start memory: {memory_samples[0]:.1f} MB")
        print(f"  End memory: {memory_samples[-1]:.1f} MB")
        print(f"  Peak memory: {max_memory:.1f} MB")
        print(f"  Net growth: {memory_growth:.1f} MB")
        print(f"  Growth per batch: {memory_growth / batch_count:.1f} MB")
        
        # Memory assertions
        assert memory_growth < 200, f"Memory growth too high: {memory_growth:.1f} MB"
        assert max_memory < 1000, f"Peak memory usage too high: {max_memory:.1f} MB"
    
    @pytest.mark.asyncio
    async def test_sustained_throughput(self, performance_system, performance_data_generator):
        """Test sustained throughput over extended period."""
        duration_minutes = 2  # Shorter for CI/testing
        target_docs_per_minute = 30
        
        total_docs_target = duration_minutes * target_docs_per_minute
        batch_size = 10
        
        monitor = PerformanceMonitor()
        monitor.start()
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        total_processed = 0
        total_successful = 0
        throughput_samples = []
        
        while time.time() < end_time:
            batch_start = time.time()
            
            # Create and process batch
            test_files = performance_data_generator.create_document_batch(batch_size)
            tasks = [performance_system.process_document(f) for f in test_files]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            batch_time = time.time() - batch_start
            successful = [r for r in results if isinstance(r, dict) and r.get("success")]
            
            total_processed += len(results)
            total_successful += len(successful)
            
            # Calculate current throughput
            if batch_time > 0:
                current_throughput = len(successful) / batch_time
                throughput_samples.append(current_throughput)
            
            monitor.sample()
            
            # Brief pause to prevent overwhelming
            await asyncio.sleep(0.5)
        
        total_time = time.time() - start_time
        overall_throughput = total_successful / total_time
        avg_throughput = statistics.mean(throughput_samples) if throughput_samples else 0
        
        stats = monitor.get_stats()
        
        print(f"\nSustained Throughput Test ({duration_minutes} minutes):")
        print(f"  Total processed: {total_successful}/{total_processed}")
        print(f"  Overall throughput: {overall_throughput:.2f} docs/second")
        print(f"  Average batch throughput: {avg_throughput:.2f} docs/second")
        print(f"  Target throughput: {target_docs_per_minute / 60:.2f} docs/second")
        print(f"  Memory increase: {stats['memory']['increase_mb']:.1f} MB")
        
        # Performance assertions
        min_acceptable_throughput = (target_docs_per_minute / 60) * 0.7  # 70% of target
        assert overall_throughput >= min_acceptable_throughput, \
            f"Sustained throughput too low: {overall_throughput:.2f} < {min_acceptable_throughput:.2f}"


@pytest.mark.performance
class TestIngestionLimits:
    """Test system limits and resource constraints."""
    
    @pytest.mark.asyncio
    async def test_maximum_concurrent_uploads(self, performance_system, performance_data_generator):
        """Test maximum number of concurrent uploads the system can handle."""
        max_concurrent_levels = [10, 20, 50, 100]
        
        for max_concurrent in max_concurrent_levels:
            print(f"\nTesting {max_concurrent} concurrent uploads:")
            
            # Create files
            test_files = performance_data_generator.create_document_batch(max_concurrent)
            
            monitor = PerformanceMonitor()
            monitor.start()
            
            # Limit concurrency with semaphore
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def process_with_semaphore(file_path):
                async with semaphore:
                    return await performance_system.process_document(file_path)
            
            try:
                start_time = time.time()
                tasks = [process_with_semaphore(f) for f in test_files]
                results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=120  # 2 minute timeout
                )
                total_time = time.time() - start_time
                
                successful = [r for r in results if isinstance(r, dict) and r.get("success")]
                success_rate = len(successful) / len(results)
                throughput = len(successful) / total_time
                
                stats = monitor.get_stats()
                
                print(f"  Success rate: {success_rate:.1%} ({len(successful)}/{len(results)})")
                print(f"  Throughput: {throughput:.2f} docs/second")
                print(f"  Memory peak: {stats['memory']['peak_mb']:.1f} MB")
                print(f"  CPU peak: {stats['cpu']['peak_percent']:.1f}%")
                
                # If success rate drops significantly, we've likely hit a limit
                if success_rate < 0.8:
                    print(f"  System limit reached at ~{max_concurrent} concurrent uploads")
                    break
                    
            except asyncio.TimeoutError:
                print(f"  Timeout at {max_concurrent} concurrent uploads - likely at system limit")
                break
            except Exception as e:
                print(f"  Error at {max_concurrent} concurrent uploads: {e}")
                break
    
    @pytest.mark.asyncio
    async def test_file_size_limits(self, performance_system):
        """Test processing of files at size limits."""
        # Test files near the configured limit
        max_size_mb = 50  # Based on test settings
        test_sizes = [max_size_mb * 0.8, max_size_mb * 0.95, max_size_mb * 1.1]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            for size_mb in test_sizes:
                print(f"\nTesting {size_mb:.1f} MB file:")
                
                large_file = create_large_test_file(
                    int(size_mb), 
                    str(Path(tmpdir) / f"limit_test_{size_mb:.1f}mb.bin")
                )
                
                try:
                    monitor = PerformanceMonitor()
                    monitor.start()
                    
                    start_time = time.time()
                    result = await asyncio.wait_for(
                        performance_system.process_document(large_file),
                        timeout=60  # 1 minute timeout per file
                    )
                    processing_time = time.time() - start_time
                    
                    stats = monitor.get_stats()
                    
                    if result.get("success"):
                        print(f"  SUCCESS: {processing_time:.2f}s, "
                              f"Memory: {stats['memory']['peak_mb']:.1f} MB")
                    else:
                        print(f"  FAILED: {result.get('error', 'Unknown error')}")
                    
                except asyncio.TimeoutError:
                    print(f"  TIMEOUT: Processing took longer than 60 seconds")
                except Exception as e:
                    print(f"  ERROR: {e}")
                finally:
                    if large_file.exists():
                        large_file.unlink()


def print_system_info():
    """Print system information for performance context."""
    print("\n" + "="*60)
    print("SYSTEM INFORMATION")
    print("="*60)
    print(f"CPU cores: {psutil.cpu_count()}")
    print(f"Memory: {psutil.virtual_memory().total / 1024**3:.1f} GB")
    print(f"Python process PID: {psutil.Process().pid}")
    
    # Get resource limits
    try:
        soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
        print(f"File descriptor limit: {soft_limit} (soft), {hard_limit} (hard)")
    except:
        pass
    
    print("="*60)


# Run system info when module is imported
if __name__ != "__main__":
    print_system_info()