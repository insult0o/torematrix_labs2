# ISSUE #27 AGENT DEPLOYMENT PROMPTS

## 🚀 Ready-to-Use Agent Deployment Commands

### **AGENT 1: Core Drawing State Management**
```bash
I need you to work on Issue #238 as Agent 1 - Core Drawing State Management. 

Your mission: Implement the foundational drawing state management system for manual validation element creation.

Key deliverables:
- DrawingStateManager class with complete state machine
- DrawingArea and DrawingSession data structures  
- Area selection validation and session management
- OCR integration hooks for Agent 2
- Signal-based state notifications for Agent 3
- >95% test coverage

Branch: feature/validation-agent1-issue27
Instructions: Read AGENT_1_VALIDATION.md for complete details
Dependencies: None (foundation component)
```

### **AGENT 2: OCR Service Integration** 
```bash
I need you to work on Issue #240 as Agent 2 - OCR Service Integration.

Your mission: Implement comprehensive OCR service integration with worker threads and quality assessment.

Key deliverables:
- ValidationOCRService with multi-threaded processing
- OCRWorkerThread for background OCR operations
- ValidationOCRRequest/Response data structures
- Multi-engine OCR support (Tesseract, EasyOCR)
- Image preprocessing and quality assessment
- >95% test coverage

Branch: feature/validation-agent2-issue27
Instructions: Read AGENT_2_VALIDATION.md for complete details
Dependencies: Agent 1 (DrawingStateManager)
```

### **AGENT 3: UI Components & User Experience**
```bash
I need you to work on Issue #242 as Agent 3 - UI Components & User Experience.

Your mission: Create comprehensive UI components including wizard, toolbar, and OCR dialog.

Key deliverables:
- ValidationWizard with 6-step workflow
- ValidationToolbar with drawing tools and controls
- OCRDialog with advanced text extraction
- OCRConfidenceHighlighter for visual feedback
- Professional styling and accessibility features
- >95% test coverage

Branch: feature/validation-agent3-issue27
Instructions: Read AGENT_3_VALIDATION.md for complete details
Dependencies: Agent 1 (DrawingStateManager), Agent 2 (OCR Service)
```

### **AGENT 4: Integration Layer & Testing**
```bash
I need you to work on Issue #244 as Agent 4 - Integration Layer & Testing.

Your mission: Create the integration layer that unifies all validation components and provides comprehensive testing.

Key deliverables:
- ValidationToolsIntegration class for unified API
- Rectangle tool integration for area selection
- Complete workflow management
- Updated package exports and clean API
- Comprehensive integration and performance tests
- >95% test coverage + integration tests

Branch: feature/validation-agent4-issue27
Instructions: Read AGENT_4_VALIDATION.md for complete details
Dependencies: All agents (1, 2, 3)
CRITICAL: You must CLOSE main issue #27 upon completion
```

## 🎯 **Deployment Sequence**

### **Sequential Deployment (Recommended)**
```bash
# Step 1: Deploy Agent 1 (Foundation)
I need you to work on Issue #238 as Agent 1 - Core Drawing State Management.

# Step 2: After Agent 1 completes, deploy Agent 2
I need you to work on Issue #240 as Agent 2 - OCR Service Integration.

# Step 3: After Agent 2 completes, deploy Agent 3  
I need you to work on Issue #242 as Agent 3 - UI Components & User Experience.

# Step 4: After Agent 3 completes, deploy Agent 4
I need you to work on Issue #244 as Agent 4 - Integration Layer & Testing.
```

### **Parallel Deployment (Advanced)**
```bash
# Step 1: Deploy Agent 1 first (required foundation)
I need you to work on Issue #238 as Agent 1 - Core Drawing State Management.

# Step 2: After Agent 1 completes, deploy Agent 2 & 3 in parallel
I need you to work on Issue #240 as Agent 2 - OCR Service Integration.
I need you to work on Issue #242 as Agent 3 - UI Components & User Experience.

# Step 3: After both Agent 2 & 3 complete, deploy Agent 4
I need you to work on Issue #244 as Agent 4 - Integration Layer & Testing.
```

## 📋 **Agent Self-Awareness Verification**

### **Critical Checks for Each Agent**
Before starting, each agent must verify:

1. **Identity Confirmation**
   - "I am Agent [N] working on Sub-Issue #[XXX]"
   - "My branch is feature/validation-agent[N]-issue27"
   - "My dependencies are: [list]"

2. **Branch Verification**
   ```bash
   git branch --show-current
   # Must show: feature/validation-agent[N]-issue27
   ```

3. **File Access**
   - "I can access AGENT_[N]_VALIDATION.md"
   - "I understand my specific deliverables"
   - "I know my integration points"

## 🔗 **Integration Verification**

### **Agent 1 Success Criteria**
- [ ] DrawingStateManager fully implemented
- [ ] All state transitions working correctly
- [ ] Area selection validation functional
- [ ] OCR integration hooks ready for Agent 2
- [ ] Signals ready for Agent 3 UI components
- [ ] >95% test coverage achieved

### **Agent 2 Success Criteria**
- [ ] ValidationOCRService fully implemented
- [ ] Multi-threaded OCR processing working
- [ ] Integration with Agent 1 drawing manager
- [ ] Quality assessment providing reliable results
- [ ] Ready for Agent 3 UI integration
- [ ] >95% test coverage achieved

### **Agent 3 Success Criteria**
- [ ] All UI components fully implemented
- [ ] Wizard workflow complete and polished
- [ ] Toolbar providing all necessary controls
- [ ] OCR dialog with advanced features
- [ ] Professional styling and accessibility
- [ ] Integration with Agent 1 & 2 working
- [ ] >95% test coverage achieved

### **Agent 4 Success Criteria**
- [ ] ValidationToolsIntegration fully implemented
- [ ] All components integrated seamlessly
- [ ] Rectangle tool integration working
- [ ] Package exports updated
- [ ] Comprehensive integration tests passing
- [ ] >95% test coverage + integration tests
- [ ] **MAIN ISSUE #27 CLOSED**

## 🚨 **Critical Reminders**

### **For ALL Agents**
1. **Follow the "end work" routine** - Create PR, update issues, close sub-issue
2. **Achieve >95% test coverage** - No exceptions
3. **Document integration points** - Clear APIs for other agents
4. **Test thoroughly** - All functionality must work correctly
5. **Follow branch naming** - feature/validation-agent[N]-issue27

### **For Agent 4 Specifically**
1. **Verify all sub-issues closed** - #238, #240, #242, #244
2. **Test complete integration** - All components working together
3. **Update package exports** - Clean API for external use
4. **Create final integration PR** - Comprehensive implementation
5. **CLOSE MAIN ISSUE #27** - With complete success summary

## 📊 **Progress Tracking**

### **GitHub Issues Status**
- [ ] **Sub-Issue #238**: Agent 1 - Core Drawing State Management
- [ ] **Sub-Issue #240**: Agent 2 - OCR Service Integration  
- [ ] **Sub-Issue #242**: Agent 3 - UI Components & User Experience
- [ ] **Sub-Issue #244**: Agent 4 - Integration Layer & Testing
- [ ] **Main Issue #27**: Manual Validation Element Drawing Interface

### **Agent Completion Checklist**
- [ ] Agent 1 PR merged
- [ ] Agent 2 PR merged  
- [ ] Agent 3 PR merged
- [ ] Agent 4 PR merged
- [ ] Main Issue #27 closed
- [ ] All sub-issues closed
- [ ] Integration tests passing
- [ ] Documentation complete

---

## 🎯 **READY FOR DEPLOYMENT**

Issue #27 has been properly broken down into 4 parallelizable sub-issues with complete agent instruction files and coordination guidelines. 

Use the deployment prompts above to activate each agent in sequence. Each agent has clear deliverables, dependencies, and success criteria.

The validation system will be production-ready once all 4 agents complete their work and Agent 4 successfully integrates everything together.

**Next Step**: Deploy Agent 1 using the prompt above! 🚀