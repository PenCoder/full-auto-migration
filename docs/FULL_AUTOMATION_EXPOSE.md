# Full-Automation Migration Exposé

## Project Scope
- Repository is being developed as the full-automation Windows-to-Linux migration extension of the earlier semi-automation project.
- The current direction is a complete migration workflow, including inventory, analysis, app mapping, file migration recommendations, backup and restore, and report generation.
- The branch is intended to deliver a migration-ready foundation with automation-capable UI, recommendation engines, and review/customize controls.

## Project Features
- **Qt wizard UI + CLI support**
  - A guided desktop wizard in `src/qt_ui/` plus command-line access in `src/cli.py`.
- **Inventory and analysis**
  - Windows hardware/software inventory collection.
  - Linux target configuration and compatibility analysis.
- **AI and usage-based recommendations**
  - Local and online recommendation modes for software mapping.
  - Usage-based file recommendations from local file activity.
  - Agent/AI-assisted scoring and recommendation strategies where enabled.
- **App recommendation mappings**
  - Automatic Windows-to-Linux app mapping candidates from `configs/linux_ms_map.csv`.
  - Review and customize mapping overrides before bundling.
  - Recommendation-driven app selection options: migrate all supported, choose from recommendations, or manual mapping.
- **Mode-driven workflow**
  - Guided, balanced, and expert UX modes with graduated control.
  - Mode-aware page behavior and security restrictions.
- **Backup / restore / validation**
  - Full backup bundle creation and restore support.
  - Post-restore validation and final report generation.
- **Expert panel controls**
  - Page-specific expert guidance and advanced controls on each wizard step.
  - No longer a catch-all panel; content changes with the current page.

## Current Status
- This branch is a full-automation extension built on the earlier semi-automation foundation.
- Core Qt wizard UI and CLI paths exist, with page-driven state, expert mode controls, and recommendation workflows.
- The UI now supports scan-driven app and file recommendation generation plus usage-based file-type discovery.
- Privacy-aware policy gating is implemented in the Qt recommendation flow for file AI ranking and software metadata lookups.
- App mapping controls support migration choice modes, including migrate-all, recommendation selection, and manual override.
- The remaining gap is end-to-end execution wiring, consistent mode enforcement across all pages, and full Linux restore/report validation.

## Executive Summary
- The project is currently a working full-automation migration foundation, not just a semi-automation UI prototype.
- Inventory, analysis, app recommendation, file recommendation, backup, restore, and validation services are present in code.
- The strongest progress is in UI architecture, recommendation pipelines, and mode-aware workflow design.
- Key areas still in progress: complete automation pipeline wiring, CLI/Qt feature parity, recommendation fallback handling, and regression coverage.

## Completed Work
- **UI and workflow architecture**
  - Established a clean separation between UI pages, state, and business logic.
  - Implemented a wizard flow that supports recommendation collection and review.
- **Expert panel redesign**
  - Rebuilt `src/qt_ui/widgets/expert_panel.py` with a page-specific stacked content model.
  - Added page title/description context for each wizard step.
- **Recommendation workflows**
  - Added support for software recommendation generation in `src/qt_ui/pages/scan_page.py`.
  - Added review controls for application mapping and file selection recommendations.
- **App mapping and override support**
  - Added application mapping choice modes in `src/qt_ui/pages/application_mapping_page.py`.
  - Implemented recommendation-driven app migration candidate handling.
- **Vertical mapping layout**
  - Converted expert mapping and review panels to vertical container layouts in `src/qt_ui/widgets/expert_panel.py`.
- **Persistence and automation foundations**
  - Built configuration-driven startup and automation settings in `configs/migration.config.yaml`.
  - Laid groundwork for pipeline state tracking and progress logging.

## Remaining Work
- Complete the end-to-end automation pipeline wiring across scan, mapping, backup, restore, and report flows.
- Finalize mode enforcement so guided, balanced, and expert restrictions behave consistently on every page.
- Complete recommendation UX polish and fallback handling for unavailable AI/agent services.
- Add full workflow validation and regression tests for the migration automation path.
- Validate final report and restore bundles end-to-end in the target Linux flow.

## Progress Estimate
- Estimated completion: **~75%**.
  - Most of the architecture, recommendation flows, and UI groundwork are now in place.
  - Remaining work centers on integration, automation execution, and validation.

## Presentation Statement
- This branch should be presented as:
  - **“Full-automation migration implementation in progress.”**
  - It is an active Windows-to-Linux migration tool with recommendation engines, app mapping review, and automation-ready UI.
  - The current milestone is delivering the automation foundation and reviewable recommendation workflows, not only UI cosmetics.
