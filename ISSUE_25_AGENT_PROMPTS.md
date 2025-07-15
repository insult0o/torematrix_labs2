# Issue #25 Agent Deployment Prompts - Search and Filter System

## 🚀 Ready-to-Use Agent Deployment Commands

Copy and paste these commands to deploy each agent immediately:

---

## 🔥 Agent 1 Deployment (Core Search Engine)
**Issue #213** - Deploy immediately to start the foundation

```
I need you to work on Issue #213 - Core Search Engine & Indexing Infrastructure.

You are Agent 1 implementing the foundation of the Search and Filter System. Your job is to create the core search engine with high-performance indexing, real-time updates, and full-text search capabilities.

Read your complete instructions from AGENT_1_SEARCH.md file in the repository root. This file contains:
- Your specific tasks and implementation details
- All files you need to create with code examples
- Performance requirements (<100ms search, <10ms indexing)
- Integration points with other agents
- Complete test coverage requirements (>95%)

Key deliverables:
1. SearchEngine class with full-text search
2. SearchIndexer with real-time updates
3. QueryParser for complex query handling
4. SearchRanker for relevance scoring
5. SearchHistory for tracking
6. Complete test suite with >95% coverage

Performance targets:
- Search: <100ms for 10K+ elements
- Indexing: <10ms per element update
- Memory: <1MB for 1K indexed elements

Start by creating your feature branch:
git checkout -b feature/search-engine-agent1-issue213

Begin with the SearchEngine class in src/torematrix/ui/search/engine.py as your central component.
```

---

## 🔥 Agent 2 Deployment (Advanced Filters)
**Issue #214** - Deploy after Agent 1 completes

```
I need you to work on Issue #214 - Advanced Filters & Query Processing.

You are Agent 2 implementing sophisticated filtering and query building capabilities. Your job is to create advanced filter management, visual query builder, and saved filter sets on top of Agent 1's search infrastructure.

Read your complete instructions from AGENT_2_SEARCH.md file in the repository root. This file contains:
- Your specific tasks building on Agent 1's work
- All filter types and query builder implementation
- DSL parser for power users
- Integration points with Agent 1's SearchEngine
- Complete test coverage requirements (>95%)

Key deliverables:
1. FilterManager for complex filter combinations
2. Type-based and property-based filters
3. Visual QueryBuilder interface
4. DSL parser for text-based queries
5. Saved filter sets with persistence
6. Quick filter presets library

Performance targets:
- Filter processing: <50ms for complex queries
- Support for 20+ filter types
- Unlimited saved filter sets
- 10+ nested filter conditions

Start by creating your feature branch:
git checkout -b feature/search-filters-agent2-issue214

Begin with the FilterManager class in src/torematrix/ui/search/filters.py, integrating with Agent 1's SearchEngine.
```

---

## 🔥 Agent 3 Deployment (Performance Optimization)
**Issue #215** - Deploy after Agents 1-2 complete

```
I need you to work on Issue #215 - Performance Optimization & Caching.

You are Agent 3 implementing high-performance optimization and intelligent caching. Your job is to make everything blazingly fast with smart caching, lazy loading, and performance monitoring on top of Agents 1-2's work.

Read your complete instructions from AGENT_3_SEARCH.md file in the repository root. This file contains:
- Your specific optimization tasks
- Caching strategies and lazy loading implementation
- Performance monitoring and analytics
- Integration with Agents 1-2's components
- Complete test coverage requirements (>95%)

Key deliverables:
1. CacheManager with LRU caching
2. LazyResultLoader for large datasets
3. SearchSuggestionEngine with autocomplete
4. VirtualScrollManager for UI
5. BackgroundIndexer optimization
6. SearchAnalytics and monitoring

Performance targets:
- Cache hit ratio: >80%
- Memory usage: <100MB for 1M elements
- Suggestion speed: <50ms response
- 10x performance improvement over basic implementation

Start by creating your feature branch:
git checkout -b feature/search-optimization-agent3-issue215

Begin with the CacheManager class in src/torematrix/ui/search/cache.py to provide immediate performance gains.
```

---

## 🔥 Agent 4 Deployment (Integration & Polish)
**Issue #216** - Deploy after all agents complete

```
I need you to work on Issue #216 - Integration, UI Components & Polish.

You are Agent 4 responsible for complete system integration with polished UI components. Your job is to create the final user interface, integrate all search and filter components from Agents 1-3, and deliver a production-ready search and filter system.

Read your complete instructions from AGENT_4_SEARCH.md file in the repository root. This file contains:
- Your integration and UI implementation tasks
- All UI components and widget specifications
- Export functionality and accessibility requirements
- Integration with all previous agents' work
- Complete test coverage including integration and e2e tests

Key deliverables:
1. Main SearchWidget combining all components
2. AdvancedSearchBar with autocomplete
3. FilterPanel with visual controls
4. SearchResultsView with highlighting
5. Export functionality (JSON, CSV, PDF)
6. Full accessibility compliance (WCAG 2.1 AA)
7. Comprehensive integration tests

Performance targets:
- UI responsiveness: <100ms for all interactions
- Export performance: 10K elements in <5 seconds
- 100% accessibility compliance
- Seamless integration with existing systems

Start by creating your feature branch:
git checkout -b feature/search-integration-agent4-issue216

Begin with the main SearchWidget class in src/torematrix/ui/search/widgets.py that orchestrates all components from Agents 1-3.
```

---

## 📋 Agent Sequence Commands

### Deploy All Agents in Sequence:
```bash
# Agent 1 (Day 1-2)
echo "Deploying Agent 1 - Core Search Engine"
# Use Agent 1 deployment prompt above

# Agent 2 (Day 2-3, after Agent 1)  
echo "Deploying Agent 2 - Advanced Filters"
# Use Agent 2 deployment prompt above

# Agent 3 (Day 3-4, after Agents 1-2)
echo "Deploying Agent 3 - Performance Optimization" 
# Use Agent 3 deployment prompt above

# Agent 4 (Day 4-6, after all agents)
echo "Deploying Agent 4 - Integration & Polish"
# Use Agent 4 deployment prompt above
```

---

## 🎯 Quick Reference

### Agent Files in Repository:
- `AGENT_1_SEARCH.md` - Agent 1 detailed instructions
- `AGENT_2_SEARCH.md` - Agent 2 detailed instructions  
- `AGENT_3_SEARCH.md` - Agent 3 detailed instructions
- `AGENT_4_SEARCH.md` - Agent 4 detailed instructions
- `SEARCH_COORDINATION.md` - Multi-agent coordination guide

### GitHub Issues:
- **Issue #213**: Agent 1 - Core Search Engine & Indexing Infrastructure
- **Issue #214**: Agent 2 - Advanced Filters & Query Processing  
- **Issue #215**: Agent 3 - Performance Optimization & Caching
- **Issue #216**: Agent 4 - Integration, UI Components & Polish

### Expected Timeline:
- **Days 1-2**: Agent 1 foundation work
- **Days 2-3**: Agent 2 filter implementation
- **Days 3-4**: Agent 3 optimization work
- **Days 4-6**: Agent 4 integration and polish

### Success Criteria:
- Search performance: <100ms for 10K+ elements
- Filter processing: <50ms for complex queries
- Cache hit ratio: >80% for typical usage
- UI responsiveness: <100ms for all interactions
- Test coverage: >95% across all components
- Full accessibility compliance (WCAG 2.1 AA)

Copy and paste the appropriate agent deployment prompt to begin implementation immediately!