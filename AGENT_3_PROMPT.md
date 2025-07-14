# AGENT 3 PROMPT - PDF.js Performance Optimization & Memory Management

## 📋 Your Mission
You are Agent 3, responsible for optimizing PDF.js performance for large documents, implementing efficient memory management, and adding hardware acceleration support.

## 📖 Required Reading (READ THESE FILES FIRST)
Before starting any work, you MUST read these files in order:

1. **Project Context**: `/home/insulto/torematrix_labs2/CLAUDE.md`
2. **Your Detailed Instructions**: `/home/insulto/torematrix_labs2/AGENT_3_PDFJS.md`
3. **Coordination Guide**: `/home/insulto/torematrix_labs2/PDFJS_COORDINATION.md`
4. **Agent 1's Work**: `/home/insulto/torematrix_labs2/AGENT_1_PDFJS.md` (understand the foundation you'll optimize)
5. **Agent 2's Work**: `/home/insulto/torematrix_labs2/AGENT_2_PDFJS.md` (understand the bridge you'll monitor)
6. **Your GitHub Issue**: Run `gh issue view 126` to see full requirements

## 🕐 When You Start
**Timeline**: Day 3-4 (you start AFTER Agent 2 has bridge working)

**Prerequisites**: 
- Agent 1's PDFViewer must be functional
- Agent 2's QWebChannel bridge must be operational
- Basic PDF rendering and communication must work

## 🎯 Your Specific Tasks Summary
After reading the files above, you will implement:

### Day 3: Performance Analysis & Memory Management
- Set up performance monitoring infrastructure
- Create benchmarking suite for PDF operations
- Implement intelligent page caching (LRU algorithm)
- Add memory pool for PDF resources
- Implement automatic garbage collection triggers

### Day 4: Large PDF Optimization & Hardware Acceleration
- Implement lazy loading for PDF pages (viewport-based)
- Create progressive rendering system
- Add prefetching algorithms for documents >100MB
- Enable GPU acceleration in QWebEngineView
- Add hardware acceleration detection and fallbacks

## 📁 Files You Will Create
```
src/torematrix/integrations/pdf/performance.py
src/torematrix/integrations/pdf/cache.py
src/torematrix/integrations/pdf/memory.py
src/torematrix/integrations/pdf/metrics.py
resources/pdfjs/performance.js
tests/performance/pdf/test_optimization.py
tests/performance/pdf/__init__.py
```

## 📊 Performance Targets You Must Achieve
- **50% reduction** in memory usage for large PDFs
- **3x faster** loading for documents >50MB
- **Hardware acceleration** functional on supported systems
- **Memory leaks eliminated** completely
- **<5s load time** for 100MB PDFs
- **<200MB total memory** for typical usage

## 🔧 Configuration System You Must Implement
```python
class PerformanceConfig:
    cache_size_mb: int = 200
    max_preload_pages: int = 5
    enable_gpu_acceleration: bool = True
    memory_pressure_threshold: float = 0.8
    cleanup_interval_ms: int = 30000
```

## 🔗 Integration Requirements
Your work depends on:
- **Agent 1**: Core viewer for optimization integration
- **Agent 2**: Bridge for performance event communication

Your work enables:
- **Agent 4**: Performance data for UI feedback and progress indicators

## 🧪 Testing Requirements You Must Meet
### Performance Tests
- Memory usage profiling with large PDFs (>100MB)
- Load time benchmarking across different PDF sizes
- Stress testing with multiple PDFs simultaneously
- Hardware acceleration verification on different systems

### Stress Tests
- Multiple large PDFs open simultaneously
- Memory pressure scenarios and recovery
- Long-running sessions (8+ hours)
- Resource exhaustion and recovery testing

## ✅ Definition of Done
- [ ] Memory management system operational
- [ ] Large PDF optimization complete (500+ page support)
- [ ] Hardware acceleration implemented with fallbacks
- [ ] Performance monitoring functional
- [ ] All optimization targets achieved
- [ ] Stress tests passing
- [ ] Memory leak tests clean
- [ ] Documentation written
- [ ] Ready for production workloads

## 🚀 Getting Started
1. Read all the files listed above
2. Wait for Agent 2 to complete bridge and notify you
3. Create your branch: `git checkout -b feature/pdfjs-performance`
4. Study Agent 1's viewer and Agent 2's bridge implementations
5. Start with performance monitoring infrastructure
6. Implement memory management first, then optimization
7. Test with increasingly large PDFs
8. Benchmark everything and document results

## 📞 Communication
- Coordinate with Agent 2 for handoff timing
- Work in parallel with Agent 4 (coordinate shared resources)
- Update your GitHub issue #126 with daily progress
- Share performance metrics with Agent 4 for UI integration
- Provide optimization hooks for Agent 4's features

**Your optimization work ensures production-ready performance!**