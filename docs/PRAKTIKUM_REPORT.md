# Praktikum Final Report
## Toward a Fully Automated Migration Framework from Windows 11 to Linux Mint

**Author:** Japhet Kofi Appau Arthur  
**Project:** Mobile Computing Seminar — Praktikum  
**Date:** May 2026

---

## 1. Introduction

This report documents the Praktikum project that extended an existing semi-automated Windows 11 to Linux Mint migration system toward a more automated, adaptive, and privacy-preserving workflow.

The original system provided a functional wizard-based pipeline (scan → backup → restore → validate) but relied on static CSV mappings, offered no file prioritisation logic, and had limited automation depth. This project addressed those gaps across six work packages.

---

## 2. Work Completed

### WP1 — System Refinement

The architecture was restructured into clearly separated layers:

- `src/inventory/` — hardware, software, and system settings collectors
- `src/analysis/` — hardware compatibility matrix and software mapping
- `src/services/` — recommendation, file recommendation, migration, restore, validation, report, pipeline
- `src/orchestration/` — error handling and checkpointing
- `src/qt_ui/` — page layer, presenter layer, controller layer (MVC separation)

A dedicated controller layer (`AutomationCoordinator`, `NavigationController`, `ModeController`, `OperationsController`) was extracted from the main window, keeping the Qt window thin and testable.

### WP2 — Recommendation Enhancement

Three concrete improvements were made to the recommendation engine:

**1. Dynamic mapping with fuzzy matching (`src/analysis/dynamic_rules.py`)**  
The `resolve_mapping` function uses Python's `SequenceMatcher` to find the best CSV match even when application names contain version numbers or slight variations. User overrides always take priority.

**2. CSV confidence as a floor for computed scores**  
Each CSV row carries an expert-assigned `confidence` column (`high`/`medium`/`low`). This is now used as a minimum floor for the fuzzy match score, preventing the algorithm from downgrading a manually curated high-confidence entry:

| CSV confidence | Floor applied |
|---|---|
| high | 0.90 |
| medium | 0.70 |
| low | 0.60 |

**3. Category propagation from CSV to recommendation output**  
The `category` field (e.g. Office, Browser, Media) was previously hardcoded to an empty string. It is now read from the CSV mapping row and flows through `MappingDecision` into the recommendation report. This enables the agent scoring's `category_bonus` to be applied correctly.

**4. Repology online metadata integration**  
The `RecommendationService._query_online_package_signal()` method queries Repology to verify whether a Linux package is available in Linux Mint 21/22, Ubuntu 22.04/24.04, or Flathub repositories. Results are session-cached. Only the package name is sent externally (no user data).

**5. AI-assisted ranking (expert mode)**  
In expert mode, an optional AI endpoint can re-rank recommendations and file priorities. This is disabled by default and policy-gated via `ai.enabled` and `ai.file_recommendation_online_enabled` in the config.

### WP3 — Workflow Integration

**Mode-driven pipeline (guided / balanced / expert)**  
Both the Qt `AutomationCoordinator` and the CLI `scan` command enforce the same mode policy:

| Stage | Guided | Balanced | Expert |
|---|---|---|---|
| Inventory | ✓ | ✓ | ✓ |
| Analysis | — | ✓ | ✓ |
| App recommendations | local | local | agent |
| File recommendations | — | all_files | ai_recommended |
| Backup | ✓ | ✓ | ✓ |

**CLI file recommendations (WP3.4)**  
The `scan` CLI command now generates file recommendations in balanced and expert modes, mirroring the Qt automation flow. A `_build_file_inventory()` helper scans the configured backup paths respecting the enabled file-type list and exclusion rules.

**Consistency verification (WP3.6)**  
The Qt `OperationsController.run_app_recommendations()` and the CLI scan both resolve to `strategy="agent"` in expert mode and `strategy="local"` otherwise. The mode policy is defined once per layer and consistently applied.

### WP4 — Validation Improvements

**Per-stage timing metrics (WP4.4)**  
Both the Qt `AutomationCoordinator` and the `PipelineService` now record wall-clock duration for each pipeline stage and include a `timing` dict in the result:

```json
{
  "timing": {
    "inventory_s": 1.42,
    "analysis_s": 0.31,
    "app_recommendations_s": 0.08,
    "file_recommendations_s": 2.15,
    "backup_s": 5.83
  }
}
```

**Validation report (existing, confirmed complete)**  
The `ValidationService` produces hash-verified file counts, missing file lists, and a Sovereignty Score (0–100%). The `ReportService` generates JSON, Markdown, and HTML reports with an embedded activity log.

### WP5 — Testing and Evaluation

The test suite covers:

| Level | Files | Key coverage |
|---|---|---|
| Unit | `test_recommendation_quality.py`, `test_error_handling.py`, `test_settings_inventory.py` | Mapping accuracy, scoring, graceful failure |
| Integration | `test_automation_pipeline.py`, `test_cli_scan.py`, `test_recommendation_report_pipeline.py` | Mode gating, timing, category/confidence propagation, file recs in CLI |
| E2E | `test_e2e/test_workflows.py` | Full mode-selection → scan → recommendation presenter flow |
| Performance | `test_performance/test_performance.py` | Throughput benchmarks |

New tests added in this project:
- `test_windows_result_includes_timing_dict` — verifies per-stage timing is present
- `test_guided_timing_omits_analysis_and_file_rec_keys` — verifies mode gating of timing
- `test_linux_result_includes_timing_dict` — verifies Linux-side timing
- `test_scan_balanced_mode_includes_file_recommendations` — CLI file-rec integration
- `test_scan_guided_mode_omits_file_recommendations` — CLI mode gating
- `test_category_is_populated_from_csv` — WP2.5 category regression
- `test_csv_confidence_floor_applied_to_mapping_score` — WP2.5 confidence regression
- `test_agent_score_benefits_from_category` — WP2.5 scoring regression

### WP6 — Documentation and Finalisation

- **User migration guide** (`docs/USER_MIGRATION_GUIDE.md`) — step-by-step instructions for non-technical users covering all 9 phases from scanning to app installation on Linux Mint
- **This report** (`docs/PRAKTIKUM_REPORT.md`) — technical and academic summary of work completed

---

## 3. System Architecture

```
app.py
└── src/qt_ui/app.py           # Qt application entry point
    └── QtMigrationWindow      # Main window
        ├── Controllers
        │   ├── AutomationCoordinator   # Full-flow automation
        │   ├── NavigationController    # Page transitions (+ stepper click-to-navigate)
        │   ├── ModeController          # guided/balanced/expert UI
        │   ├── OperationsController    # Individual operation runners
        │   └── ActivityLogController   # Event logging
        └── Pages (7 wizard steps — Windows side)
            └── WelcomePage, ModePage, ScanPage (inventory + analysis + strategy),
                SettingsPage, DataSelectionPage,
                ReviewRecommendationsPage, BackupBundlePage
            └── Pages (3 steps — Linux side)
            └── RestorePage, VerificationPage, ReportPage

src/cli.py                     # Typer CLI (scan, backup, restore, validate, report)
src/services/
├── recommendation_service.py  # App mapping + Repology + AI ranking
├── file_recommendation_service.py  # File prioritisation + AI ranking
├── pipeline_service.py        # End-to-end orchestration (with timing)
├── migration_service.py       # Inventory + analysis + backup orchestration
├── restore_service.py         # Bundle extraction + hash verification
├── validation_service.py      # Post-restore report validation
└── report_service.py          # JSON + Markdown + HTML report generation

src/analysis/
├── dynamic_rules.py           # Fuzzy mapping + CSV confidence floor + category
└── software_mapping.py        # Software compatibility table

src/inventory/
├── software.py                # Windows registry + package manager scan
├── hardware.py                # CPU, RAM, GPU, storage inventory
└── settings.py                # Desktop theme, wallpaper, locale settings
```

---

## 4. Privacy Design

The system enforces strict privacy at every layer:

| Component | Privacy measure |
|---|---|
| File inventory | Files never leave the local machine; paths are redacted in logs |
| Repology lookup | Only `name`/`version`/`publisher` sent; controlled by `software_online_send_fields` |
| AI ranking | Disabled by default (`ai.enabled: false`); file paths never sent externally |
| Research metrics | Machine ID anonymised; no personal identifiers in `run_summary.json` |
| Backup bundle | Stored locally; user controls destination |

---

## 5. Evaluation

### Functionality

All core migration stages operate end-to-end:
- Inventory scan (Windows registry + file system)
- Application mapping (CSV + fuzzy matching + Repology + optional AI)
- File recommendation (heuristic scoring + optional AI)
- Backup bundle creation (zip + manifest + SHA-256 checksums)
- Restore with hash verification
- Validation report (Sovereignty Score, missing files, hash mismatches)
- Final report (JSON + Markdown + HTML)

### Recommendation Quality

After WP2.5 fixes:
- All CSV-mapped applications now carry their `category` in the output
- Expert-assigned CSV confidence values are honoured as minimum floors
- The agent scoring `category_bonus` is now correctly applied
- Test suite confirms mappings for all common Windows applications (Firefox, Chrome, Word, VLC, 7-Zip, etc.)

### Automation Level

The mode system successfully reduces required user interaction:
- **Guided mode** — user makes no decisions after mode selection; tool runs inventory → recommendations → backup automatically
- **Balanced mode** — adds file type selection; full pipeline with usage-based file prioritisation
- **Expert mode** — all of balanced plus override panel and AI-assisted ranking

### Performance

Per-stage timing is now recorded in every pipeline run, providing data for the evaluation metrics required by the Praktikum assessment.

---

## 6. Remaining Work

| Item | Priority | Notes |
|---|---|---|
| Real E2E test on physical machine | High | Current E2E tests use mocked inventory; a real Windows scan test requires a live system |
| Final Praktikum presentation slides | High | To be prepared separately |
| Live USB automation | Low | `usb` CLI command is a stub; Rufus/ISO integration deferred |

### UI improvements completed post-report

- Scan page and Application Mapping page merged into a single step — inventory chains directly into compatibility analysis, followed by the app-strategy choice (automatic / let me pick / manual)
- Stepper sidebar steps are now clickable — completed steps navigate directly on click
- Global scan bar fixed above the scroll area — always visible during any background operation
- Backup file paths now preserve directory structure (`Documents/Work/report.pdf` instead of `Work/report.pdf`) and restore to Linux home equivalents (`~/Documents`, `~/Pictures`, etc.)
- Backup enumeration now excludes junk directories (`node_modules`, `__pycache__`, `.git`, `AppData`, etc.) and enforces a 500 MB per-file cap; `excluded_paths` from config is now wired and active

---

## 7. Conclusion

This Praktikum project successfully extended the semi-automated migration system toward a more automated, privacy-preserving, and well-tested solution. The key contributions are:

1. **Dynamic recommendation quality** — fuzzy matching, CSV confidence floors, category propagation, and Repology integration all work together to produce more accurate and informative application mappings
2. **Unified mode policy** — guided/balanced/expert modes are consistently enforced across both the Qt wizard and the CLI, eliminating divergence between interfaces
3. **Execution metrics** — per-stage timing in every pipeline run enables performance evaluation and debugging
4. **File recommendations in the CLI** — the CLI `scan` command now produces file recommendations in balanced and expert modes, matching the Qt automation flow
5. **Comprehensive test coverage** — new integration tests specifically cover the WP2.5 fixes and the timing additions, providing regression protection

The system is ready for end-to-end demonstration on a real Windows 11 machine.
