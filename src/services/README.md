"""
# Phase 2: Service Layer Reorganization - Complete

## Architecture Overview

The services have been completely reorganized with clear separation of concerns and single responsibility principle.

### New Directory Structure

```
src/services/
├── inventory/          # Hardware and software collection
│   ├── __init__.py
│   ├── hardware.py     # HardwareInventoryService
│   └── software.py     # SoftwareInventoryService
├── analysis/           # Compatibility and mapping analysis
│   ├── __init__.py
│   ├── hardware.py     # HardwareAnalysisService
│   └── software.py     # SoftwareAnalysisService
├── backup/             # Backup creation and archival
│   ├── __init__.py (BackupService)
│   └── executor.py
├── recommendations/    # App and file recommendations
│   ├── __init__.py
│   ├── app_recommender.py      # AppRecommendationService
│   └── file_recommender.py     # FileRecommendationService
├── report/             # Report generation
│   ├── __init__.py
│   └── generator.py    # ReportGenerationService
├── restore/            # Restore and validation
│   ├── __init__.py (RestoreExecutionService)
├── registry.py         # ServiceRegistry and adapters
└── (old monolithic services remain for now)
```

## Service Breakdown

### 1. **Inventory Services**

#### HardwareInventoryService
```python
service.collect() → dict[str, Any]
service.persist(hw_data) → str
service.collect_and_persist() → dict[str, Any]
```

Responsibilities:
- Collect hardware information from system
- Persist to output files
- Handle hardware-specific errors

#### SoftwareInventoryService
```python
service.collect(deep_scan: bool) → dict[str, Any]
service.persist(sw_data) → str
service.collect_and_persist(deep_scan: bool) → dict[str, Any]
```

Responsibilities:
- Collect software information (quick or deep)
- Persist to output files
- Support different scan depths

### 2. **Analysis Services**

#### HardwareAnalysisService
```python
service.analyze(hw_inventory) → dict[str, Any]
service.persist(analysis) → str
service.analyze_and_persist(hw_inventory) → dict[str, Any]
```

Responsibilities:
- Analyze hardware for Linux compatibility
- Generate compatibility matrix
- Persist results

#### SoftwareAnalysisService
```python
service.analyze(sw_inventory) → dict[str, Any]
service.persist(analysis) → str
service.analyze_and_persist(sw_inventory) → dict[str, Any]
```

Responsibilities:
- Analyze software for Linux alternatives
- Generate mapping recommendations
- Persist results

### 3. **Backup Service**

#### BackupService
```python
service.generate_manifest(folders, file_types) → dict[str, Any]
service.persist_manifest(manifest) → str
service.execute_backup(manifest) → dict[str, Any]
service.create_archive(backup_location) → str
service.create_backup_complete(folders, file_types) → dict[str, Any]
```

Responsibilities:
- Generate backup manifests
- Execute file copying
- Create compressed archives
- Persist manifest files

### 4. **Recommendation Services**

#### AppRecommendationService
```python
service.generate(software_inventory, selection_profile="migrate_all") → dict[str, Any]
```

Responsibilities:
- Load Windows-to-Linux mapping database
- Match apps to alternatives
- Score by confidence and availability
- Filter by selection profile

#### FileRecommendationService
```python
service.generate(selected_paths, selection_profile="migrate_all") → dict[str, Any]
```

Responsibilities:
- Classify files by importance (critical, important, useful, low)
- Generate migration recommendations
- Support different selection profiles
- Estimate data volume

### 5. **Report Service**

#### ReportGenerationService
```python
service.generate(inventory, analysis, recommendations, validation=None) → dict[str, Any]
```

Responsibilities:
- Aggregate results into cohesive report
- Generate JSON, Markdown, HTML formats
- Compute quality metrics
- Persist to disk

### 6. **Restore Service**

#### RestoreExecutionService
```python
service.execute_restore() → dict[str, Any]
service.write_report(results) → Path
```

Responsibilities:
- Extract backup archives
- Restore files to target
- Verify file integrity
- Install applications
- Generate reports

### 7. **Service Registry**

#### ServiceRegistry
```python
registry = ServiceRegistry(config)
registry.get_service(name) → Any
registry.create_restore_service(bundle_dir, target_home) → RestoreExecutionService
registry.register_with_orchestrator(orchestrator) → None
```

Responsibilities:
- Create all service instances
- Manage service lifecycle
- Provide service lookup
- Register with orchestrator
- Adapt services to protocol interfaces

## Usage Example

### Basic Setup

```python
from src.config import MigrationConfigRoot
from src.core import MigrationState, WorkflowOrchestrator
from src.services.registry import ServiceRegistry

# Load configuration
config = MigrationConfigRoot.load("config.yaml")

# Create state
state = MigrationState(runtime_mode="windows", config=config)

# Create orchestrator
orchestrator = WorkflowOrchestrator(state)

# Create and register services
registry = ServiceRegistry(config)
registry.register_with_orchestrator(orchestrator)

# Execute workflow
orchestrator.execute_inventory_phase(
    deep_scan=True,
    on_complete=lambda result: print(f"Inventory complete: {result}"),
)
```

### Direct Service Usage

```python
from src.services.inventory import HardwareInventoryService

service = HardwareInventoryService(config)
hw_data = service.collect()
hw_path = service.persist(hw_data)
```

### Complete Workflow

```python
from src.services.inventory import HardwareInventoryService, SoftwareInventoryService
from src.services.analysis import HardwareAnalysisService, SoftwareAnalysisService
from src.services.backup import BackupService
from src.services.recommendations import AppRecommendationService

config = MigrationConfigRoot.load("config.yaml")

# Step 1: Inventory
hw_service = HardwareInventoryService(config)
sw_service = SoftwareInventoryService(config)

hw_data = hw_service.collect()
sw_data = sw_service.collect(deep_scan=False)

# Step 2: Analysis
hw_analyzer = HardwareAnalysisService(config)
sw_analyzer = SoftwareAnalysisService(config)

hw_analysis = hw_analyzer.analyze(hw_data)
sw_analysis = sw_analyzer.analyze(sw_data)

# Step 3: Recommendations
app_recommender = AppRecommendationService(config)
recommendations = app_recommender.generate(sw_data, selection_profile="prioritize")

# Step 4: Backup
backup_service = BackupService(config)
backup_result = backup_service.create_backup_complete(
    selected_folders=["Documents", "Desktop"],
    selected_file_types={"pdf": True, "doc": True},
)
```

## Protocol Implementations

### Inventory Protocol
- `collect_hardware() → dict`
- `collect_software(deep_scan: bool) → dict`

Implemented by: `_InventoryServiceAdapter`

### Analysis Protocol
- `analyze_hardware(inventory: dict) → dict`
- `analyze_software(inventory: dict) → dict`

Implemented by: `_AnalysisServiceAdapter`

### Recommendation Protocol
- `recommend_applications(software_inventory, selection_profile) → dict`
- `recommend_files(file_paths, selection_profile) → dict`

Implemented by: `_RecommendationsServiceAdapter`

### Backup Protocol
- `generate_manifest(folders, file_types) → dict`
- `create_backup(manifest, output_dir, compress) → dict`

Implemented by: `BackupService` (directly)

### Report Protocol
- `generate_report(inventory, analysis, recommendations, validation) → dict`
- `format_report(report, format) → str`

Implemented by: `ReportGenerationService` (directly)

### Restore Protocol
- `restore_backup(backup_location, target_location) → dict`
- `validate_restore(backup_manifest, restored_location) → dict`

Implemented by: `RestoreExecutionService` (directly)

## Benefits Achieved

✅ **Single Responsibility**: Each service has ONE clear responsibility
✅ **Loose Coupling**: Services don't depend on each other
✅ **Protocol Compliance**: All services implement defined contracts
✅ **Testability**: Services can be tested independently
✅ **Reusability**: Services can be used outside Qt context
✅ **Maintainability**: Clear organization and dependencies
✅ **Scalability**: Easy to add new services or variants
✅ **Dependency Injection**: ServiceRegistry enables flexible wiring

## Comparison: Before vs After

### Before (Monolithic)
```
MigrationService
├── run_inventory()  [Hardware + Software]
├── run_analysis()   [Hardware + Software]
├── run_backup()     [Manifest + Copy + Archive]
└── run_task()       [Threading]
```

**Problems:**
- Mixed concerns (hardware + software in one method)
- Hard to test individually
- Difficult to reuse
- Tightly coupled

### After (Reorganized)
```
Inventory/
  ├── HardwareInventoryService
  └── SoftwareInventoryService

Analysis/
  ├── HardwareAnalysisService
  └── SoftwareAnalysisService

Backup/
  └── BackupService

Recommendations/
  ├── AppRecommendationService
  └── FileRecommendationService

Report/
  └── ReportGenerationService

Restore/
  └── RestoreExecutionService
```

**Benefits:**
- Clear separation of concerns
- Each service is independently testable
- Services can be reused
- Easy to understand and maintain

## Next Steps (Phase 3)

The service layer is now complete and clean. Next phases will:

1. **Phase 3**: Configuration restructuring
   - Move dataclasses to config/schema.py
   - Create config/loader.py
   - Create config/validator.py

2. **Phase 4**: UI refactoring
   - Extract presenters for business logic
   - Simplify pages to rendering only
   - Implement state observer pattern

3. **Phase 5**: Integration & testing
   - Wire everything together
   - Run comprehensive tests
   - Performance optimization

## Migration from Old Code

The old monolithic `MigrationService` still exists but can be retired:

```python
# Old way (to be deprecated)
migration_service = MigrationService(config, context)
inventory = migration_service.run_inventory()
analysis = migration_service.run_analysis(inventory["software"], inventory["hardware"])

# New way (recommended)
registry = ServiceRegistry(config)
orchestrator = WorkflowOrchestrator(state)
registry.register_with_orchestrator(orchestrator)
orchestrator.execute_inventory_phase()
orchestrator.execute_analysis_phase()
```

The workflow orchestrator handles all coordination and service calling.
"""
