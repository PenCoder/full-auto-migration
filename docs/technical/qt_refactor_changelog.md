# Qt Main Window Refactor Changelog

## Summary
This changelog captures the decomposition of `QtMigrationWindow` into focused controllers to reduce God-class responsibilities and improve maintainability.

## Phases Completed

### Phase 1: Activity Logging Extraction
- Added `ActivityLogController` for:
  - event normalization (level -> badge, phase -> icon)
  - in-memory log storage and filtering
  - markdown/json session log export
- `main_window.py` now delegates activity log behavior.

### Phase 2: Navigation Extraction
- Added `NavigationController` for:
  - next/back stack navigation
  - nav button enabled-state sync
  - stepper active index updates
  - next/done label switching
- `main_window.py` navigation handlers became thin delegates.

### Phase 3: Mode/Presentation Extraction
- Added `ModeController` for:
  - guided/balanced/expert mode transitions
  - expert dock visibility rules
  - mode badge updates and page refresh propagation
- `main_window.py` mode handlers now delegate to controller.

### Phase 4: Runtime Operations Extraction
- Added `OperationsController` for:
  - inventory, analysis, recommendation, backup, restore, validation, report workflows
  - selected-folder resolution
  - AI config mapping
- `main_window.py` operational methods converted to wrappers.

## Files Added
- `src/qt_ui/controllers/__init__.py`
- `src/qt_ui/controllers/activity_log_controller.py`
- `src/qt_ui/controllers/navigation_controller.py`
- `src/qt_ui/controllers/mode_controller.py`
- `src/qt_ui/controllers/automation_coordinator.py`
- `src/qt_ui/controllers/operations_controller.py`
- `tests/test_unit/test_qt_ui_controllers.py`

## Files Updated
- `src/qt_ui/main_window.py`

## Verification
- Unit/integration/e2e test suite remained green after refactor.
- Command: `pytest -q`
- Latest result: all tests passing.

## Outcome
`QtMigrationWindow` now primarily handles UI composition and signal wiring, while business/UI coordination logic is split into dedicated controller modules.
