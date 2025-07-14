# PROMPT FOR CLAUDE CODE INSTANCE 2

Copy and paste this entire prompt into a new Claude Code instance:

---

You are working on TORE Matrix Labs V3, implementing the Multi-Library PDF Parser System (Issue #41) - a critical enhancement for accurate document processing.

## Project Context
- **Repository**: https://github.com/insult0o/torematrix_labs2
- **Working Directory**: /home/insulto/torematrix_labs2
- **Current Branch**: You'll create feature/multi-parser-system
- **Issue Number**: #41
- **Priority**: High (PDF Enhancement)

## Initial Setup Tasks
1. Verify your environment:
   ```bash
   pwd  # Should be /home/insulto/torematrix_labs2
   git status  # Check current branch
   git pull origin main  # Get latest changes
   ```

2. Read the GitHub issue thoroughly:
   ```bash
   gh issue view 41 --repo insult0o/torematrix_labs2
   ```

3. Create and checkout your feature branch:
   ```bash
   git checkout -b feature/multi-parser-system
   git push -u origin feature/multi-parser-system
   ```

4. Update the issue status:
   ```bash
   gh issue edit 41 --repo insult0o/torematrix_labs2 --add-label "in-progress"
   gh issue comment 41 --repo insult0o/torematrix_labs2 --body "Starting implementation of Multi-Library PDF Parser System. This will provide fallback parsing with pdfplumber, PyMuPDF, pdfminer.six, and PyPDF2."
   ```

## Key Implementation Requirements
From the PDF-to-LLM best practices analysis:
- Implement fallback system with multiple PDF parsing libraries
- Auto-select parser based on document characteristics
- Merge results from multiple parsers for best output
- Handle parser failures gracefully
- Cache parsing results for performance

## Files to Create/Modify
1. `/src/torematrix/infrastructure/parsers/pdf_parser_manager.py` - Main system
2. `/src/torematrix/infrastructure/parsers/pdfplumber_parser.py`
3. `/src/torematrix/infrastructure/parsers/pymupdf_parser.py`
4. `/src/torematrix/infrastructure/parsers/pdfminer_parser.py`
5. `/src/torematrix/infrastructure/parsers/pypdf2_parser.py`
6. `/src/torematrix/infrastructure/parsers/parser_selector.py` - Selection logic
7. `/tests/unit/infrastructure/parsers/` - Test directory
8. `/tests/fixtures/pdf_samples/` - Test PDFs

## Important Context Files to Read
- `/docs/PDF_TO_LLM_GAP_ANALYSIS.md` - Missing capabilities
- `/docs/ENHANCED_SYSTEM_DESIGN_V2.md` - Multi-parser architecture
- `/docs/CACHING_AND_INCREMENTAL_PROCESSING.md` - Caching strategies

## Dependencies to Add
Update `/pyproject.toml`:
```toml
dependencies = [
    # ... existing deps
    "pdfplumber>=0.9.0",
    "PyMuPDF>=1.23.0",
    "pdfminer.six>=20221105",
    "PyPDF2>=3.0.0",
]
```

## Implementation Strategy
1. Start with base parser interface
2. Implement each parser adapter
3. Create intelligent selector based on PDF characteristics
4. Build result merger for combining outputs
5. Add caching layer
6. Comprehensive testing with various PDF types

## Testing Requirements
- Unit tests for each parser adapter
- Integration tests with real PDFs
- Performance benchmarks
- Fallback scenario testing
- Cache hit/miss testing

## Progress Tracking
```bash
# Regular commits
git add -A
git commit -m "feat(parsers): [specific implementation detail]"
git push

# Update issue with progress
gh issue comment 41 --repo insult0o/torematrix_labs2 --body "[What you implemented today]"
```

## Completion Checklist
- [ ] Base parser interface defined
- [ ] All 4 parser adapters implemented
- [ ] Parser selector with document profiling
- [ ] Result merger algorithm
- [ ] Caching integration
- [ ] Error handling and fallback logic
- [ ] 95%+ test coverage
- [ ] Performance benchmarks documented
- [ ] Technical documentation written
- [ ] PR created with comprehensive description

Remember: This system is critical for handling diverse PDF types. Each parser has strengths - pdfplumber for layout, PyMuPDF for speed, pdfminer for detail, PyPDF2 for simplicity.