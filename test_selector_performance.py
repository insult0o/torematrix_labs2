#!/usr/bin/env python3
"""
Standalone selector performance test.
"""

import time
import sys
import os

# Add the selectors module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'torematrix', 'core', 'state', 'selectors'))

# Import selector modules directly
from base import Selector, create_selector

def main():
    print("🚀 Selector Performance Test")
    print("=" * 40)
    
    # Create test data - 10k elements
    print("Creating 10,000 test elements...")
    elements = [
        {
            'id': i,
            'type': 'text' if i % 2 == 0 else 'image',
            'status': 'validated' if i % 5 == 0 else 'pending',
            'visible': i % 4 != 0
        }
        for i in range(10000)
    ]
    
    state = {'elements': elements}
    print(f"Created state with {len(elements)} elements")
    
    # Define selector functions
    def get_elements(state):
        return state.get('elements', [])
    
    def filter_text_elements(elements):
        return [e for e in elements if e.get('type') == 'text']
    
    def filter_validated_text_elements(elements):
        return [e for e in elements 
                if e.get('type') == 'text' and e.get('status') == 'validated']
    
    # Create selectors
    simple_selector = create_selector(get_elements, filter_text_elements, name='simple_text_filter')
    complex_selector = create_selector(get_elements, filter_validated_text_elements, name='complex_filter')
    
    # Test 1: Simple selector performance
    print("\n📊 Simple Selector Test (text elements)")
    start_time = time.perf_counter()
    simple_result = simple_selector(state)
    simple_time = (time.perf_counter() - start_time) * 1000
    
    print(f"  Results: {len(simple_result)} text elements")
    print(f"  Execution time: {simple_time:.2f}ms")
    print(f"  Target: <10ms - {'✅ PASS' if simple_time < 10 else '❌ FAIL'}")
    
    # Test 2: Complex selector performance  
    print("\n📊 Complex Selector Test (validated text elements)")
    start_time = time.perf_counter()
    complex_result = complex_selector(state)
    complex_time = (time.perf_counter() - start_time) * 1000
    
    print(f"  Results: {len(complex_result)} validated text elements")
    print(f"  Execution time: {complex_time:.2f}ms")
    print(f"  Target: <10ms - {'✅ PASS' if complex_time < 10 else '❌ FAIL'}")
    
    # Test 3: Cache performance
    print("\n🏎️  Cache Performance Test")
    
    # Simple selector cache
    start_time = time.perf_counter()
    simple_cached = simple_selector(state)
    simple_cache_time = (time.perf_counter() - start_time) * 1000
    
    print(f"  Simple cached: {simple_cache_time:.3f}ms")
    print(f"  Target: <1ms - {'✅ PASS' if simple_cache_time < 1 else '❌ FAIL'}")
    print(f"  Results match: {'✅' if simple_result == simple_cached else '❌'}")
    
    # Complex selector cache
    start_time = time.perf_counter()
    complex_cached = complex_selector(state)
    complex_cache_time = (time.perf_counter() - start_time) * 1000
    
    print(f"  Complex cached: {complex_cache_time:.3f}ms")
    print(f"  Target: <1ms - {'✅ PASS' if complex_cache_time < 1 else '❌ FAIL'}")
    print(f"  Results match: {'✅' if complex_result == complex_cached else '❌'}")
    
    # Test 4: Cache hit rate (multiple executions)
    print("\n🔄 Cache Hit Rate Test")
    
    # Execute multiple times
    for i in range(10):
        simple_selector(state)
        complex_selector(state)
    
    # Get statistics
    simple_stats = simple_selector.get_stats()
    complex_stats = complex_selector.get_stats()
    
    print(f"  Simple selector:")
    print(f"    Total calls: {simple_stats['total_calls']}")
    print(f"    Cache hit rate: {simple_stats['cache_hit_rate']:.1f}%")
    print(f"    Avg execution: {simple_stats['avg_execution_time_ms']:.3f}ms")
    
    print(f"  Complex selector:")
    print(f"    Total calls: {complex_stats['total_calls']}")
    print(f"    Cache hit rate: {complex_stats['cache_hit_rate']:.1f}%")
    print(f"    Avg execution: {complex_stats['avg_execution_time_ms']:.3f}ms")
    
    # Test 5: Memory efficiency with larger dataset
    print("\n💾 Memory Efficiency Test")
    
    # Create very large state (100k elements)
    large_elements = [{'id': i, 'type': 'text' if i % 2 == 0 else 'image'} for i in range(100000)]
    large_state = {'elements': large_elements}
    
    print(f"  Testing with {len(large_elements)} elements...")
    
    start_time = time.perf_counter()
    large_result = simple_selector(large_state)
    large_time = (time.perf_counter() - start_time) * 1000
    
    print(f"  Results: {len(large_result)} text elements")
    print(f"  Execution time: {large_time:.2f}ms")
    print(f"  Target: <50ms - {'✅ PASS' if large_time < 50 else '❌ FAIL'}")
    
    # Cache test with large dataset
    start_time = time.perf_counter()
    large_cached = simple_selector(large_state)
    large_cache_time = (time.perf_counter() - start_time) * 1000
    
    print(f"  Cached time: {large_cache_time:.3f}ms")
    print(f"  Target: <5ms - {'✅ PASS' if large_cache_time < 5 else '❌ FAIL'}")
    
    # Final assessment
    print("\n🎯 Performance Summary")
    print("=" * 30)
    
    all_passed = True
    results = []
    
    # Check all targets
    if simple_time < 10:
        results.append("✅ Simple selector < 10ms")
    else:
        results.append(f"❌ Simple selector: {simple_time:.2f}ms (target: <10ms)")
        all_passed = False
    
    if complex_time < 10:
        results.append("✅ Complex selector < 10ms")
    else:
        results.append(f"❌ Complex selector: {complex_time:.2f}ms (target: <10ms)")
        all_passed = False
    
    if simple_cache_time < 1:
        results.append("✅ Cache performance < 1ms")
    else:
        results.append(f"❌ Cache performance: {simple_cache_time:.3f}ms (target: <1ms)")
        all_passed = False
    
    if simple_stats['cache_hit_rate'] > 90:
        results.append("✅ Cache hit rate > 90%")
    else:
        results.append(f"⚠️  Cache hit rate: {simple_stats['cache_hit_rate']:.1f}% (target: >90%)")
    
    if large_time < 50:
        results.append("✅ Large dataset performance good")
    else:
        results.append(f"❌ Large dataset: {large_time:.2f}ms (target: <50ms)")
        all_passed = False
    
    for result in results:
        print(f"  {result}")
    
    if all_passed:
        print("\n🎉 All performance targets achieved!")
        print("✅ Selectors ready for production use with 10k+ elements")
        return 0
    else:
        print("\n⚠️  Some targets need optimization")
        return 1

if __name__ == '__main__':
    exit(main())