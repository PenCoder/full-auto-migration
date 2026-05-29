"""
# Core Module Architecture

## Overview

The `core` module provides the foundational infrastructure for the migration framework:
- **Centralized State Management**: Single source of truth for all workflow state
- **Service Contracts**: Protocol definitions for all services
- **Workflow Orchestration**: Coordination of service execution with proper separation of concerns
- **Exception Hierarchy**: Clean error handling throughout the application

## Components

### 1. State Management (`state.py`)

**`MigrationState`** is the single source of truth containing:

#### User Preferences
- Migration mode (guided, balanced, expert)
- Target distro and system configuration
- Advanced operation flags

#### Data Selection
- Selected folders and file types
- Custom paths
- Data choice strategy

#### Analysis & Recommendations
- Recommendation strategy
- Inventory strategy
- Profile overrides

#### Execution State
- Current phase
- Completed phases
- Phase completion order

#### Runtime Results
- Hardware/software inventory
- Analysis results
- Recommendations
- Backup and restore results
- Final reports

#### Quality Metrics & Logging
- Sovereignty score
- Activity entries with filtering
- Error tracking

### Key Methods

```python
# Phase Management
state.mark_phase_started(phase)
state.mark_phase_complete(phase)
state.is_phase_complete(phase)

# Error Handling
state.record_error(message, details)
state.clear_error()
state.has_error()

# Activity Logging
state.log_activity(level, phase, message, details)
state.get_filtered_activities()

# Result Storage
state.store_result(key, data)
state.get_result(key)

# Progress Tracking
state.get_completion_percentage()

# Session Management
state.reset_for_new_session()
```

### 2. Service Contracts (`interfaces.py`)

Protocols define the contract for all services without implementation details:

#### Business Services
- **InventoryService**: Hardware and software inventory collection
- **AnalysisService**: Compatibility and mapping analysis
- **BackupService**: Backup creation and manifest generation
- **RecommendationService**: App and file recommendations
- **ReportService**: Report generation in multiple formats
- **RestoreService**: Restore and validation operations

#### Supporting Patterns
- **TaskRunner**: Background task execution
- **StateObserver**: Notification pattern for state changes
- **Callback Types**: Logging, progress, completion, error callbacks

### 3. Workflow Orchestration (`workflow.py`)

**`WorkflowOrchestrator`** coordinates service execution:

#### Responsibilities
- Service registration and lookup
- Phase execution with proper sequencing
- Observer pattern for state changes
- Error handling and recovery
- Progress tracking

#### Phase Execution Methods
```python
orchestrator.execute_inventory_phase(deep_scan=False)
orchestrator.execute_analysis_phase()
orchestrator.execute_recommendations_phase()
orchestrator.execute_backup_phase()
orchestrator.execute_restore_phase()
orchestrator.execute_report_phase()
```

#### Observer Pattern
```python
orchestrator.attach_observer(observer)
orchestrator.detach_observer(observer)
```

### 4. Exception Hierarchy (`exceptions.py`)

Clean exception hierarchy for proper error handling:

```
MigrationException (base)
├── InventoryException
├── AnalysisException
├── RecommendationException
├── BackupException
├── RestoreException
├── ValidationException
├── ConfigurationException
├── WorkflowException
├── StateException
└── ServiceException
```

Each exception includes:
- Human-readable message
- Machine-readable error code
- Additional details dictionary

## Usage Example

### 1. Initialize State
```python
from src.config import MigrationConfigRoot
from src.core import MigrationState

config = MigrationConfigRoot.load("config.yaml")
state = MigrationState(
    runtime_mode="windows",
    config=config,
)
```

### 2. Register Services
```python
from src.core import WorkflowOrchestrator
from src.services.inventory import InventoryServiceImpl
from src.services.analysis import AnalysisServiceImpl

orchestrator = WorkflowOrchestrator(state)
orchestrator.register_service("inventory", InventoryServiceImpl())
orchestrator.register_service("analysis", AnalysisServiceImpl())
# ... register other services
```

### 3. Attach Observers (e.g., Qt UI)
```python
class QtUIObserver:
    def on_phase_changed(self, new_phase, old_phase):
        print(f"Phase: {old_phase} → {new_phase}")
    
    def on_error_occurred(self, message, details):
        print(f"Error: {message}")
    
    # ... other methods

orchestrator.attach_observer(QtUIObserver())
```

### 4. Execute Workflow
```python
def on_inventory_complete(result):
    print(f"Inventory complete: {result}")

def on_inventory_error(message, exc):
    print(f"Inventory failed: {message}")

orchestrator.execute_inventory_phase(
    deep_scan=True,
    on_complete=on_inventory_complete,
    on_error=on_inventory_error,
)
```

### 5. Query State
```python
status = orchestrator.get_workflow_status()
print(f"Progress: {status['completion_percentage']}%")

activities = state.get_filtered_activities()
for activity in activities:
    print(f"[{activity.level.value}] {activity.message}")

if state.has_error():
    print(f"Error: {state.last_error}")
```

## Design Principles

### 1. **Separation of Concerns**
- State management separated from business logic
- Service contracts separated from implementations
- UI separated from orchestration

### 2. **Single Source of Truth**
- One `MigrationState` instance per workflow
- All state changes go through `MigrationState` methods
- No scattered state across multiple objects

### 3. **Observer Pattern**
- Services don't know about UI
- UI observes state changes through callbacks
- Loose coupling between layers

### 4. **Clean Architecture**
- Core is independent of UI framework (no PySide6 imports)
- Services can be tested independently
- Easy to add new services without modifying core

### 5. **Error Handling**
- Structured exception hierarchy
- Error details stored in state
- Callbacks for error propagation

## Migration Path

This core infrastructure enables gradual refactoring:

1. **Phase 1** (Current): Core infrastructure ✅
   - State management
   - Service contracts
   - Workflow orchestration

2. **Phase 2**: Service layer reorganization
   - Split monolithic services
   - Create domain-specific services
   - Implement service contracts

3. **Phase 3**: Configuration restructuring
   - Separate schema, loading, validation
   - Add configuration validation

4. **Phase 4**: UI refactoring
   - Extract presenters
   - Simplify pages
   - Implement observers

5. **Phase 5**: Integration & testing
   - Wire everything together
   - Run comprehensive tests
   - Performance optimization

## Benefits Achieved in Phase 1

✅ **Centralized State Management**: Single point of truth eliminates scattered state
✅ **Service Contracts**: Clear interfaces for all services
✅ **Testability**: Core is pure Python, no Qt dependencies
✅ **Reusability**: Services can be used independently
✅ **Observer Pattern**: Loose coupling between layers
✅ **Error Handling**: Structured exception handling
✅ **Progress Tracking**: Built-in completion tracking
✅ **Activity Logging**: Comprehensive activity history
"""
