# Quick Start Commands for Each Instance

## 🚀 Copy-Paste Commands for Each Claude Instance

### Instance 1: Event Bus System (Issue #1)

```bash
# 1. Initial Setup
cd /home/insulto/torematrix_labs2
pwd
git status
git pull origin main

# 2. Read Issue
gh issue view 1 --repo insult0o/torematrix_labs2

# 3. Create Branch
git checkout -b feature/event-bus-system
git push -u origin feature/event-bus-system

# 4. Update Issue
gh issue edit 1 --repo insult0o/torematrix_labs2 --add-label "in-progress"
gh issue comment 1 --repo insult0o/torematrix_labs2 --body "Starting implementation of Event Bus System. Working on feature/event-bus-system branch."

# 5. Create Initial Structure
mkdir -p src/torematrix/core/events
mkdir -p tests/unit/core/events
touch src/torematrix/core/events/__init__.py
touch src/torematrix/core/events/event_bus.py
touch src/torematrix/core/events/event_types.py
touch src/torematrix/core/events/middleware.py
touch tests/unit/core/events/test_event_bus.py

# 6. Read Key Files
cat docs/ENHANCED_SYSTEM_DESIGN_V2.md | grep -A 50 "Event Bus"
cat docs/architecture/overview.md
```

---

### Instance 2: Multi-Library PDF Parser (Issue #41)

```bash
# 1. Initial Setup
cd /home/insulto/torematrix_labs2
pwd
git status
git pull origin main

# 2. Read Issue
gh issue view 41 --repo insult0o/torematrix_labs2

# 3. Create Branch
git checkout -b feature/multi-parser-system
git push -u origin feature/multi-parser-system

# 4. Update Issue
gh issue edit 41 --repo insult0o/torematrix_labs2 --add-label "in-progress"
gh issue comment 41 --repo insult0o/torematrix_labs2 --body "Starting implementation of Multi-Library PDF Parser System. This will provide fallback parsing with pdfplumber, PyMuPDF, pdfminer.six, and PyPDF2."

# 5. Create Initial Structure
mkdir -p src/torematrix/infrastructure/parsers
mkdir -p tests/unit/infrastructure/parsers
mkdir -p tests/fixtures/pdf_samples
touch src/torematrix/infrastructure/parsers/__init__.py
touch src/torematrix/infrastructure/parsers/pdf_parser_manager.py
touch src/torematrix/infrastructure/parsers/base_parser.py
touch tests/unit/infrastructure/parsers/test_pdf_parser_manager.py

# 6. Read Key Files
cat docs/PDF_TO_LLM_GAP_ANALYSIS.md
cat docs/ENHANCED_SYSTEM_DESIGN_V2.md | grep -A 100 "Multi-Parser"
```

---

### Instance 3: Caching System (Issue #48)

```bash
# 1. Initial Setup
cd /home/insulto/torematrix_labs2
pwd
git status
git pull origin main

# 2. Read Issue
gh issue view 48 --repo insult0o/torematrix_labs2

# 3. Create Branch
git checkout -b feature/caching-system
git push -u origin feature/caching-system

# 4. Update Issue
gh issue edit 48 --repo insult0o/torematrix_labs2 --add-label "in-progress"
gh issue comment 48 --repo insult0o/torematrix_labs2 --body "Starting implementation of multi-level caching system. This will include memory, disk, Redis, and object storage layers with incremental processing support."

# 5. Create Initial Structure
mkdir -p src/torematrix/core/cache
mkdir -p tests/unit/core/cache
mkdir -p config
touch src/torematrix/core/cache/__init__.py
touch src/torematrix/core/cache/multi_level_cache.py
touch src/torematrix/core/cache/change_detector.py
touch tests/unit/core/cache/test_multi_level_cache.py
touch config/cache_config.yaml

# 6. Read Key Files
cat docs/CACHING_AND_INCREMENTAL_PROCESSING.md
cat docs/ENHANCED_SYSTEM_DESIGN_V2.md | grep -A 100 "Caching"
```

---

## 🔄 Common Commands for All Instances

### Testing Commands
```bash
# Run your tests
pytest tests/unit/[your-area] -v

# Check coverage
pytest --cov=src/torematrix/[your-module] --cov-report=html

# Run all tests
pytest

# Run with specific marker
pytest -m "not slow"
```

### Git Commands
```bash
# Check status
git status

# Stage all changes
git add -A

# Commit with good message
git commit -m "feat(component): Description"

# Push changes
git push

# Check branch
git branch

# See recent commits
git log --oneline -10
```

### GitHub CLI Commands
```bash
# View your issue
gh issue view [number] --repo insult0o/torematrix_labs2

# Add comment
gh issue comment [number] --repo insult0o/torematrix_labs2 --body "Your update"

# Create PR when ready
gh pr create --title "feat(component): Description" --body "Closes #[number]"

# List all issues
gh issue list --repo insult0o/torematrix_labs2
```

### Python Environment
```bash
# Activate virtual environment (if exists)
source venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"

# Install specific package
pip install pdfplumber  # for parser instance
pip install diskcache   # for cache instance
pip install cachetools  # for cache instance
```

---

## 📝 Quick Reference

### File Paths
- **Source Code**: `/src/torematrix/`
- **Tests**: `/tests/`
- **Docs**: `/docs/`
- **Config**: `/config/`

### Key Documentation
- System Design: `/docs/ENHANCED_SYSTEM_DESIGN_V2.md`
- Architecture: `/docs/architecture/overview.md`
- Your Component: `/docs/[specific-guide].md`

### Python Package Structure
```
src/torematrix/
├── __init__.py
├── core/           # Domain logic (Event Bus, Cache)
├── infrastructure/ # External integrations (Parsers)
├── application/    # Use cases
└── presentation/   # UI (not your focus)
```

---

*Save this file locally for quick command reference!*