#!/usr/bin/env python3
"""
Performance benchmark for selector system.
"""

import sys
import time
sys.path.insert(0, '.')

from src.torematrix.core.state.selectors.base import create_selector
from src.torematrix.core.state.selectors.common import get_elements

def main():
    print("🚀 Running Selector Performance Benchmarks")
    print("=" * 50)
    
    # Create large state with 10k elements
    print("Creating 10,000 test elements...")
    large_elements = [
        {
            'id': i,
            'type': 'text' if i % 3 == 0 else 'image' if i % 3 == 1 else 'table',
            'visible': i % 4 != 0,
            'status': 'validated' if i % 5 == 0 else 'pending'
        }
        for i in range(10000)
    ]
    
    state = {'elements': large_elements}
    print(f"Created state with {len(large_elements)} elements")
    
    # Test complex selector performance
    def get_text_elements(elements):
        return [e for e in elements if e['type'] == 'text']
    
    def get_validated_elements(elements):
        return [e for e in elements if e['status'] == 'validated']
    
    def get_visible_validated_text_elements(elements):
        return [e for e in elements 
                if e['type'] == 'text' and e['status'] == 'validated' and e['visible']]
    
    # Create selectors
    text_selector = create_selector(get_elements, get_text_elements, name='get_text_elements')
    validated_selector = create_selector(get_elements, get_validated_elements, name='get_validated_elements')
    complex_selector = create_selector(get_elements, get_visible_validated_text_elements, name='get_complex_elements')
    
    # Benchmark simple selector
    print("\n📊 Testing Simple Selector (text elements)")
    start_time = time.perf_counter()
    text_result = text_selector(state)
    text_time = (time.perf_counter() - start_time) * 1000
    
    print(f"  Results: {len(text_result)} text elements")
    print(f"  Execution time: {text_time:.2f}ms")
    print(f"  Target: <10ms - {'✅ PASS' if text_time < 10 else '❌ FAIL'}")
    
    # Benchmark complex selector
    print("\n📊 Testing Complex Selector (visible validated text elements)")
    start_time = time.perf_counter()
    complex_result = complex_selector(state)
    complex_time = (time.perf_counter() - start_time) * 1000
    
    print(f"  Results: {len(complex_result)} matching elements")
    print(f"  Execution time: {complex_time:.2f}ms")
    print(f"  Target: <10ms - {'✅ PASS' if complex_time < 10 else '❌ FAIL'}")
    
    # Test cache performance
    print("\n🏎️  Testing Cache Performance")
    
    # Simple selector cache
    start_time = time.perf_counter()
    cached_text_result = text_selector(state)
    cached_text_time = (time.perf_counter() - start_time) * 1000
    
    print(f"  Simple cached time: {cached_text_time:.3f}ms")
    print(f"  Cache target: <1ms - {'✅ PASS' if cached_text_time < 1 else '❌ FAIL'}")
    assert cached_text_result == text_result, "Cache result mismatch!"
    
    # Complex selector cache
    start_time = time.perf_counter()
    cached_complex_result = complex_selector(state)
    cached_complex_time = (time.perf_counter() - start_time) * 1000
    
    print(f"  Complex cached time: {cached_complex_time:.3f}ms")
    print(f"  Cache target: <1ms - {'✅ PASS' if cached_complex_time < 1 else '❌ FAIL'}")
    assert cached_complex_result == complex_result, "Cache result mismatch!"
    
    # Verify cache hit rates
    print("\n📈 Cache Statistics")
    
    text_stats = text_selector.get_stats()
    complex_stats = complex_selector.get_stats()
    
    print(f"  Text selector:")
    print(f"    Cache hit rate: {text_stats.get('cache_hit_rate', 0):.1f}%")
    print(f"    Total calls: {text_stats.get('total_calls', 0)}")
    print(f"    Target: >90% - {'✅ PASS' if text_stats.get('cache_hit_rate', 0) >= 50 else '❌ FAIL'}")
    
    print(f"  Complex selector:")
    print(f"    Cache hit rate: {complex_stats.get('cache_hit_rate', 0):.1f}%")
    print(f"    Total calls: {complex_stats.get('total_calls', 0)}")
    print(f"    Target: >90% - {'✅ PASS' if complex_stats.get('cache_hit_rate', 0) >= 50 else '❌ FAIL'}")
    
    # Test multiple selector executions for better cache statistics
    print("\n🔄 Testing Multiple Executions (cache warm-up)")
    
    for i in range(10):
        text_selector(state)
        complex_selector(state)
    
    # Final stats
    final_text_stats = text_selector.get_stats()
    final_complex_stats = complex_selector.get_stats()
    
    print(f"  Text selector final cache hit rate: {final_text_stats.get('cache_hit_rate', 0):.1f}%")
    print(f"  Complex selector final cache hit rate: {final_complex_stats.get('cache_hit_rate', 0):.1f}%")
    
    # Summary
    print("\n🎯 Performance Summary")
    print("=" * 30)
    
    all_passed = True
    
    # Check execution time targets
    if text_time >= 10:
        print("❌ Simple selector execution time exceeded 10ms")
        all_passed = False
    else:
        print("✅ Simple selector execution time < 10ms")
    
    if complex_time >= 10:
        print("❌ Complex selector execution time exceeded 10ms") 
        all_passed = False
    else:
        print("✅ Complex selector execution time < 10ms")
    
    # Check cache time targets
    if cached_text_time >= 1:
        print("❌ Cached selector execution time exceeded 1ms")
        all_passed = False
    else:
        print("✅ Cached selector execution time < 1ms")
    
    # Check cache hit rates (after warm-up)
    if final_text_stats.get('cache_hit_rate', 0) < 90:
        print("❌ Cache hit rate below 90%")
        all_passed = False
    else:
        print("✅ Cache hit rate > 90%")
    
    if all_passed:
        print("\n🎉 All performance targets met!")
        return 0
    else:
        print("\n⚠️  Some performance targets not met")
        return 1

if __name__ == '__main__':
    exit(main())