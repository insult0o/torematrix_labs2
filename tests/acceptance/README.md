# Acceptance Tests for Issue #3: State Management System

This directory contains comprehensive acceptance tests that validate all acceptance criteria for Issue #3 and its dependencies.

## 🎯 Test Coverage

### Core Acceptance Criteria (Issue #3)
- **AC1**: Centralized state store with typed state tree
- **AC2**: Reactive state updates with observer pattern
- **AC3**: Time-travel debugging capabilities
- **AC4**: Automatic persistence with configurable strategies
- **AC5**: Optimistic updates with rollback on failure
- **AC6**: State validation and sanitization
- **AC7**: Performance monitoring and optimization
- **AC8**: Comprehensive test coverage

### Dependencies Integration
- **Issue #1**: Event Bus System Integration
- **Issue #2**: Unified Element Model Integration

### Sub-Issues Integration
- **Sub-Issue #3.1**: Core Store & Actions Implementation
- **Sub-Issue #3.2**: Persistence & Time-Travel Implementation
- **Sub-Issue #3.3**: Selectors & Performance Optimization
- **Sub-Issue #3.4**: Middleware & Integration System

## 📁 Test Structure

```
tests/acceptance/core/state/
├── __init__.py
├── test_issue_3_acceptance_criteria.py     # Core acceptance criteria tests
├── test_dependencies_integration.py        # Dependency integration tests
└── README.md

tests/acceptance/
├── run_acceptance_tests.py                 # Test runner script
└── README.md                              # This file
```

## 🚀 Running Tests

### Quick Run
```bash
python tests/acceptance/run_acceptance_tests.py
```

### Verbose Output
```bash
python tests/acceptance/run_acceptance_tests.py --verbose
```

### With Coverage Report
```bash
python tests/acceptance/run_acceptance_tests.py --coverage
```

### Generate Detailed Report
```bash
python tests/acceptance/run_acceptance_tests.py --report
```

### All Options
```bash
python tests/acceptance/run_acceptance_tests.py --verbose --coverage --report
```

## 📊 Test Categories

### 1. Core Acceptance Criteria Tests
**File**: `test_issue_3_acceptance_criteria.py`

Tests each acceptance criterion with specific test classes:
- `TestAcceptanceCriterion1` - Centralized state store
- `TestAcceptanceCriterion2` - Reactive updates
- `TestAcceptanceCriterion3` - Time-travel debugging
- `TestAcceptanceCriterion4` - Automatic persistence
- `TestAcceptanceCriterion5` - Optimistic updates
- `TestAcceptanceCriterion6` - State validation
- `TestAcceptanceCriterion7` - Performance monitoring
- `TestAcceptanceCriterion8` - Test coverage validation

Plus end-to-end workflow tests:
- `TestEndToEndWorkflow` - Complete document processing scenarios

### 2. Dependencies Integration Tests
**File**: `test_dependencies_integration.py`

Tests integration with all dependencies:
- `TestEventBusIntegration` - Event Bus System (#1)
- `TestUnifiedElementModelIntegration` - Unified Element Model (#2)
- `TestSubIssue31Integration` - Core Store & Actions (#3.1)
- `TestSubIssue32Integration` - Persistence & Time-Travel (#3.2)
- `TestSubIssue33Integration` - Selectors & Performance (#3.3)
- `TestSubIssue34Integration` - Middleware & Integration (#3.4)
- `TestCompleteSystemIntegration` - Full system integration

## 🧪 Test Scenarios

### End-to-End Workflows
1. **Document Processing Workflow**
   - Document initialization
   - Element parsing and addition
   - User corrections and edits
   - Snapshot creation
   - Time-travel debugging
   - State restoration

2. **Multi-User Collaboration**
   - Concurrent user actions
   - Optimistic updates
   - Conflict resolution
   - State synchronization

3. **Performance Under Load**
   - High-frequency operations
   - Large state collections (1000+ elements)
   - Memory efficiency validation
   - Response time verification

4. **Error Resilience**
   - Invalid action handling
   - Middleware failure recovery
   - State consistency validation
   - Graceful degradation

### Integration Scenarios
1. **Event Bus Integration**
   - State change event emission
   - External event handling
   - Event-driven state updates

2. **Element Model Integration**
   - All element types support
   - Metadata preservation
   - Validation integration
   - Factory pattern usage

3. **Cross-Component Integration**
   - Multiple middleware chains
   - Persistence + time-travel
   - Selectors + performance monitoring
   - Complete system workflow

## 📋 Acceptance Criteria Validation

Each test directly maps to acceptance criteria:

| Criterion | Test Method | Validation |
|-----------|-------------|------------|
| AC1 | `test_centralized_store_creation` | Store provides centralized state management |
| AC1 | `test_typed_state_tree` | State maintains proper typing throughout |
| AC1 | `test_state_immutability` | State is properly immutable |
| AC2 | `test_reactive_state_subscriptions` | Observer pattern with reactive updates |
| AC2 | `test_selective_subscriptions` | Selective state subscriptions for performance |
| AC3 | `test_time_travel_recording` | Actions recorded for time-travel |
| AC3 | `test_time_travel_navigation` | Forward/backward navigation works |
| AC3 | `test_time_travel_branching` | History branching for debugging |
| AC4 | `test_immediate_persistence_strategy` | Immediate persistence works |
| AC4 | `test_configurable_persistence_strategies` | All strategies configurable |
| AC4 | `test_persistence_error_recovery` | Error handling and recovery |
| AC5 | `test_optimistic_updates` | Optimistic updates succeed |
| AC5 | `test_optimistic_rollback_on_failure` | Rollback on failure works |
| AC6 | `test_state_validation` | State validation during updates |
| AC6 | `test_state_sanitization` | Input data sanitization |
| AC6 | `test_metadata_validation` | Metadata validation and integrity |
| AC7 | `test_performance_monitoring` | Performance metrics collection |
| AC7 | `test_large_state_performance` | Performance with large states |
| AC8 | `test_all_core_components_tested` | All components have tests |
| AC8 | `test_error_scenarios_covered` | Error scenarios properly handled |

## 🎯 Success Criteria

For Issue #3 to be considered complete, all tests must pass:

### ✅ Core Functionality
- [x] Centralized state store operational
- [x] Reactive updates working
- [x] Time-travel debugging functional
- [x] Persistence strategies configurable
- [x] Optimistic updates with rollback
- [x] State validation and sanitization
- [x] Performance monitoring active
- [x] Comprehensive test coverage

### ✅ Dependency Integration
- [x] Event Bus System integrated
- [x] Unified Element Model integrated
- [x] All sub-issues integrated

### ✅ Performance Requirements
- [x] Handle 1000+ elements efficiently
- [x] State access < 1s for large collections
- [x] Action dispatch < 100ms average
- [x] Memory usage bounded with pruning

### ✅ Error Resilience
- [x] Graceful error handling
- [x] State consistency maintained
- [x] Recovery from failures
- [x] Invalid input rejected safely

## 📄 Test Reports

The test runner generates detailed reports:

### Console Output
- Real-time test progress
- Pass/fail status per category
- Summary statistics
- Acceptance criteria status

### JSON Report (`acceptance_test_report.json`)
```json
{
  "test_run": {
    "timestamp": 1234567890,
    "duration_seconds": 45.67,
    "issue": "#3 State Management System"
  },
  "summary": {
    "total_categories": 2,
    "passed_categories": 2,
    "overall_success": true
  },
  "acceptance_criteria": {
    "AC1": {"description": "...", "status": "PASSED"},
    ...
  }
}
```

## 🔧 Test Configuration

### Environment Requirements
- Python 3.8+
- pytest
- All project dependencies
- Temporary file system access
- Network access (for Redis tests, optional)

### Test Data
Tests use:
- Temporary directories for persistence
- Mock document data
- Generated element collections
- Simulated user interactions

### Performance Thresholds
- Action dispatch: < 100ms average
- Large state operations: < 10s for 1000 elements
- State access: < 1s for large collections
- Memory usage: Bounded with automatic pruning

## 🚨 Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure project root in Python path
   export PYTHONPATH="$PWD:$PYTHONPATH"
   ```

2. **Permission Errors**
   ```bash
   # Make test runner executable
   chmod +x tests/acceptance/run_acceptance_tests.py
   ```

3. **Timeout Errors**
   ```bash
   # Increase timeout for slow systems
   # Edit timeout in run_acceptance_tests.py
   ```

4. **Redis Connection Errors**
   ```bash
   # Redis tests are optional
   # Set REDIS_URL environment variable if available
   export REDIS_URL="redis://localhost:6379"
   ```

### Debug Mode
For detailed debugging:
```bash
python tests/acceptance/run_acceptance_tests.py --verbose 2>&1 | tee test_debug.log
```

## 📞 Support

For issues with acceptance tests:
1. Check test output for specific errors
2. Verify all dependencies are installed
3. Ensure test environment meets requirements
4. Review test report for detailed failure information

The acceptance tests serve as the definitive validation that Issue #3 meets all requirements and is ready for production use.