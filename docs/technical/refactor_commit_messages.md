# Refactor Commit Messages

## Option A: Single Squash Commit

Title:
refactor(qt-ui): split main window responsibilities into dedicated controllers

Body:
- extract activity logging behavior into ActivityLogController
- extract full-flow orchestration into AutomationCoordinator
- extract page transitions and nav state into NavigationController
- extract mode/presentation logic into ModeController
- extract runtime operation handlers into OperationsController
- keep QtMigrationWindow focused on widget composition and signal wiring
- add focused controller unit tests for positive and guard-path behavior
- keep test suite green after refactor

## Option B: Per-Phase Commit Set

### 1) Activity Logging
Title:
refactor(qt-ui): extract activity logging into ActivityLogController

Body:
- move log badge/icon mapping, filter handling, and log export from main window
- keep existing activity event flow and ui refresh behavior unchanged

### 2) Automation Coordination
Title:
refactor(qt-ui): move full-flow automation to AutomationCoordinator

Body:
- extract runtime mode branching and phase sequencing
- preserve existing windows and linux full-flow outputs and completion flags

### 3) Navigation State
Title:
refactor(qt-ui): extract stack navigation and nav sync into NavigationController

Body:
- move next/back logic and nav button state updates from main window
- keep stepper index and next/done labels aligned with page position

### 4) Mode and Presentation
Title:
refactor(qt-ui): extract mode transitions and expert panel behavior

Body:
- move guided, balanced, and expert presentation rules into ModeController
- preserve expert dock toggling and mode badge updates

### 5) Runtime Operations
Title:
refactor(qt-ui): extract migration operation handlers into OperationsController

Body:
- move inventory, analysis, recommendations, backup, restore, validation, report flows
- keep runtime guards and progress logging semantics unchanged

### 6) Tests and Documentation
Title:
test+docs(qt-ui): add controller unit coverage and refactor changelog

Body:
- add unit tests for controller happy paths and guard paths
- add refactor changelog and commit guidance docs for PR review
