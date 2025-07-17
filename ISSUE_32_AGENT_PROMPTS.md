# Issue #32 Agent Deployment Prompts

## 🚀 Ready-to-Deploy Agent Commands

### Agent 1: Core Export Engine & Text Processing
```
I need you to work on Issue #32.1 - Core Export Engine & Text Processing. Please implement the core text export infrastructure for fine-tuning applications.

You are Agent 1 working on the Core Export Engine & Text Processing component for Issue #32 - Fine-tuning Text Exporter. Your mission is to create the foundational export infrastructure and text processing pipeline.

Key responsibilities:
1. Create base export framework with abstract classes and interfaces
2. Implement core text processing engine with structure preservation
3. Build element-to-text conversion pipeline
4. Establish hierarchy mapping and content extraction systems
5. Integrate with Unified Element Model and Element Parsers

Create your feature branch: feature/export-core-agent1-issue32.1

Follow the detailed specification in AGENT_1_EXPORT.md for complete implementation requirements.

Focus on building the foundation that Agents 2-4 will build upon. Ensure robust interfaces and comprehensive structure preservation.
```

### Agent 2: Format Processors & Template System  
```
I need you to work on Issue #32.2 - Format Processors & Template System. Please implement the format processors and template system for the fine-tuning text exporter.

You are Agent 2 working on Format Processors & Template System for Issue #32 - Fine-tuning Text Exporter. Your mission is to build format-specific processors and a flexible template system.

Key responsibilities:
1. Implement Markdown, Plain text, and JSONL format processors
2. Create comprehensive template engine with custom format support
3. Build advanced table-to-text conversion system
4. Develop output generation pipeline with quality validation
5. Integrate with Agent 1's core engine and text processor

Create your feature branch: feature/export-formats-agent2-issue32.2

Follow the detailed specification in AGENT_2_EXPORT.md for complete implementation requirements.

Build on Agent 1's foundation to create production-ready format processors that preserve document structure across all output formats.
```

### Agent 3: Tokenization & Optimization Features
```
I need you to work on Issue #32.3 - Tokenization & Optimization Features. Please implement tokenization analysis and dataset optimization for the fine-tuning text exporter.

You are Agent 3 working on Tokenization & Optimization Features for Issue #32 - Fine-tuning Text Exporter. Your mission is to implement advanced tokenization and optimization capabilities.

Key responsibilities:
1. Build multi-model tokenizer support (OpenAI, HuggingFace, custom)
2. Implement dataset splitting and optimization algorithms
3. Create content quality filtering and assessment system
4. Develop parallel processing and performance optimization
5. Integrate with Agents 1-2's text processing and format systems

Create your feature branch: feature/export-optimization-agent3-issue32.3

Follow the detailed specification in AGENT_3_EXPORT.md for complete implementation requirements.

Focus on optimization features that make the export system production-ready for ML training workflows.
```

### Agent 4: Integration & Quality Assurance
```
I need you to work on Issue #32.4 - Integration & Quality Assurance. Please integrate all export components and prepare the system for production deployment.

You are Agent 4 working on Integration & Quality Assurance for Issue #32 - Fine-tuning Text Exporter. Your mission is to integrate all components and ensure production readiness.

Key responsibilities:
1. Integrate all export components into unified system
2. Create comprehensive API and CLI interface
3. Implement end-to-end testing and validation
4. Build production deployment configuration
5. Complete documentation and example creation

Create your feature branch: feature/export-integration-agent4-issue32.4

Follow the detailed specification in AGENT_4_EXPORT.md for complete implementation requirements.

Ensure seamless integration of all components and production-ready deployment with comprehensive testing and documentation.
```

## 📋 Deployment Sequence

### Sequential Deployment (Recommended)
Deploy agents in dependency order for smooth integration:

1. **Deploy Agent 1 First**
   ```
   "I need you to work on Issue #32.1 - Core Export Engine & Text Processing..."
   ```

2. **Deploy Agent 2 After Agent 1 Complete**
   ```
   "I need you to work on Issue #32.2 - Format Processors & Template System..."
   ```

3. **Deploy Agent 3 After Agents 1-2 Complete**
   ```
   "I need you to work on Issue #32.3 - Tokenization & Optimization Features..."
   ```

4. **Deploy Agent 4 After All Agents Complete**
   ```
   "I need you to work on Issue #32.4 - Integration & Quality Assurance..."
   ```

### Parallel Deployment (Advanced)
For experienced coordination, Agents 1-2 can work in parallel:

```bash
# Session 1: Deploy Agent 1
"I need you to work on Issue #32.1 - Core Export Engine & Text Processing..."

# Session 2: Deploy Agent 2 (after Agent 1 interfaces defined)  
"I need you to work on Issue #32.2 - Format Processors & Template System..."
```

## 🔧 Pre-Deployment Checklist

### Before Agent 1
- [ ] Verify Unified Element Model (#2) availability
- [ ] Confirm Element Parsers (#9) integration
- [ ] Check Hierarchy Management (#29) system

### Before Agent 2  
- [ ] Agent 1 core interfaces complete
- [ ] Text processing pipeline functional
- [ ] Base exporter classes available

### Before Agent 3
- [ ] Agents 1-2 format processors complete
- [ ] External tokenization libraries available
- [ ] Performance requirements defined

### Before Agent 4
- [ ] All Agents 1-3 components tested
- [ ] Integration interfaces verified
- [ ] Production deployment requirements confirmed

## 📊 Coordination Commands

### Check Agent Progress
```
"What is the current status of the fine-tuning text exporter development?"
```

### Verify Integration
```
"Please verify that all export system components are properly integrated and test the end-to-end workflow."
```

### Performance Validation
```
"Run performance tests on the complete export system and validate against requirements."
```

## 🎯 Success Validation

### After Each Agent
- [ ] Component functionality verified
- [ ] Integration tests pass
- [ ] Performance requirements met
- [ ] Documentation updated

### Final System Validation
- [ ] All export formats working (Markdown, Plain text, JSONL)
- [ ] Token analysis functional across models
- [ ] Dataset optimization effective
- [ ] CLI interface operational
- [ ] Production deployment ready

---

**Deployment Ready**: All agents have complete specifications and are ready for immediate deployment using these prompts.