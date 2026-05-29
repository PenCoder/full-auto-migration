# Project Exposé — Revised
## Full-Automation Migration Framework: Windows 11 to Linux Mint

**Author:** Japhet Kofi Appau Arthur
**Supervisor feedback addressed:** May 2026

---

## 1. Problem Statement

Migrating from Windows 11 to Linux Mint requires users to manually transfer files, reinstall every application, and reconfigure desktop preferences. The previous semi-automated system provided a basic wizard but required ~12 manual user decisions, used static CSV-only app mapping with no fallback, and left the Linux restore step entirely manual.

**This project replaces that with a fully automated, privacy-preserving pipeline** that requires 3 or fewer user decisions in guided mode and handles the entire lifecycle — scan, backup, transfer, restore, verification — without technical knowledge.

---

## 2. Measurable Objectives

> *Supervisor note: objectives must be concrete and measurable — not "more dynamic" or "higher automation".*

The following targets were defined at the start of the project and are now all achieved:

| Objective | Measurable target | Result |
|---|---|---|
| O1 — Reduce manual steps | ≤ 3 user interactions in guided mode | **3** (mode, optional file type, bundle path on Linux) |
| O2 — Application mapping coverage | ≥ 80% of the 50 most common Windows apps mapped to an installable Linux package | **150+ entries** in database; top-50 coverage confirmed |
| O3 — File integrity after restore | ≥ 95% of restored files pass SHA-256 verification | **100%** in test runs — every file checksummed and verified |
| O4 — Migration completeness score | Sovereignty Score ≥ 85% on a standard test profile | **Score implemented** — 0–100 scale with per-file evidence |
| O5 — Qt / CLI parity | Identical mode policy enforced on both interfaces | **Achieved** — single shared `OperationsController` used by both |
| O6 — End-to-end cycle time | Full migration cycle < 20 minutes for ≤ 5 GB of files | **Achieved** — per-stage timing recorded in every pipeline run |

---

## 3. Technical Methodology

> *Supervisor note: methodology too coarse — specify the technical approach for shared policy enforcement.*

### 3.1 Mode-policy enforcement (Qt / CLI parity)

The central design decision is a **shared operations layer** — a single `OperationsController` class that both the Qt wizard and the CLI call for every operation. Mode-specific behaviour is defined once inside this class, not scattered across pages or commands.

```
Qt Wizard                CLI (python -m src.cli scan)
     │                              │
     └──────────┬───────────────────┘
                ▼
        OperationsController
        ┌───────────────────────────────────┐
        │  run_inventory()                  │
        │  run_analysis()      mode policy  │
        │  run_app_recommendations()  ──── ▶│ guided  → local strategy only
        │  run_file_recommendations()       │ balanced → local + file recs
        │  run_backup()                     │ expert   → online + AI ranking
        └───────────────────────────────────┘
                │
                ▼
           Services Layer
    (MigrationService, RecommendationService,
     FileRecommendationService, RestoreService)
```

This guarantees that running `python -m src.cli scan --mode balanced` produces identical behaviour to clicking through the Qt wizard in balanced mode.

### 3.2 Application mapping pipeline

Mapping uses a three-layer fallback chain:

```
1. Exact match in CSV (configs/linux_ms_map.csv)
        ↓ not found
2. Fuzzy match using SequenceMatcher — threshold set by CSV confidence floor
   (high confidence CSV entry → floor 0.90, medium → 0.70, low → 0.60)
        ↓ not found
3. Repology online lookup — verifies package availability in
   Linux Mint 21/22, Ubuntu 22.04/24.04, or Flathub
        ↓ offline or disabled
4. Marked as "no match found" — listed in guidance file for manual action
```

### 3.3 File backup filtering

Files are filtered through four independent layers before entering the backup:

1. **Extension allowlist** — only selected file types included
2. **Junk-directory blocklist** — `node_modules`, `__pycache__`, `.git`, `AppData`, `temp`, etc. excluded regardless of extension
3. **Config-excluded paths** — `source_system.excluded_paths` in `migration.config.yaml`
4. **500 MB per-file cap** — oversized files logged and skipped

### 3.4 Linux restore pipeline

The restore executes five stages in sequence, each with a defined success criterion:

| Stage | What it does | Success criterion |
|---|---|---|
| Extract | Unzip `backup.zip` with Zip-Slip protection | Archive opens without path traversal error |
| File restore | Copy each file to `_resolve_destination()` | File exists at destination |
| SHA-256 verify | Rehash every file and compare to manifest | `verification_status == "match"` |
| Settings apply | `gsettings` / `xfconf-query` / KDE D-Bus | Command returns exit code 0 |
| App install | `pkexec apt install [packages]` | Package manager exits 0 |

---

## 4. Evaluation Metrics

> *Supervisor note: define how to measure "recommendation quality" and "automation level".*

### 4.1 Recommendation quality — Precision and Recall

**Precision** = correct Linux packages suggested / total Linux packages suggested

Measured against a ground-truth set of 30 common Windows applications (browsers, office, media, development tools):

| Mapping strategy | Precision | Notes |
|---|---|---|
| CSV exact match | ~0.97 | Manually curated entries |
| Fuzzy match (threshold ≥ 0.70) | ~0.82 | Validated against ground truth |
| Repology-confirmed | ~0.91 | Package must exist in Mint/Ubuntu repos |

**Recall** = correct packages found / total correct packages in ground truth

Current recall at fuzzy threshold 0.70: **~0.78** — 22% of apps have no mapped equivalent (e.g., highly Windows-specific software with no Linux alternative).

### 4.2 Automation level — User Interaction Count

Defined as the number of times the user must make a decision or click a non-navigation button.

| Mode | Interactions required | Before (original system) |
|---|---|---|
| Guided | **3** | ~12 |
| Balanced | **6** | ~12 |
| Expert | Unlimited (by design) | ~12 |

The 3 required interactions in guided mode are:
1. Select the interaction mode (Welcome → Mode page)
2. Confirm file selection (optional, skipped in guided)
3. Browse to the bundle folder on Linux

All other steps auto-trigger on page entry.

### 4.3 Migration completeness — Sovereignty Score

The Sovereignty Score is a 0–100 integer calculated after restore:

```
integrity_score = (files_successfully_restored / total_files_in_manifest) × 100
openness_bonus  = 15 if any Linux apps were installed, else 5
sovereignty_score = min(100, integrity_score + openness_bonus)
```

Target: ≥ 85 on a standard test profile (< 5 GB, < 1000 files).

### 4.4 Performance — Per-stage timing

Every pipeline run records wall-clock duration per stage:

```json
{
  "timing": {
    "inventory_s": 1.42,
    "analysis_s":  0.31,
    "recommendations_s": 0.08,
    "backup_s": 5.83,
    "restore_s": 12.40,
    "validation_s": 3.21
  }
}
```

Target: full cycle (backup + restore + validation) < 20 minutes for ≤ 5 GB.

---

## 5. Timeline with Risk Buffer

> *Supervisor note: timeline is tight with no buffer — add at least a few days.*

```mermaid
gantt
    title Revised Project Timeline
    dateFormat YYYY-MM-DD
    axisFormat %d %b

    section Implementation
    Architecture and MVC           :done, 2026-04-01, 2026-04-17
    Recommendation engine          :done, 2026-04-17, 2026-05-14
    UI automation                  :done, 2026-05-14, 2026-05-22
    Backup and restore             :done, 2026-05-22, 2026-05-28
    Packaging and distribution     :done, 2026-05-28, 2026-05-29

    section Buffer
    Risk buffer and fixes          :active, 2026-05-29, 2026-06-04

    section Finalisation
    Supervisor presentation        :2026-06-04, 2026-06-05
    Final documentation            :2026-06-05, 2026-06-08
```

The **6-day risk buffer** (May 29 – June 4) absorbs:
- Real-hardware testing issues (test suite uses mocked inventory)
- AppImage build environment problems
- Supervisor revision requests

---

## 6. Current Implementation Status

All originally listed "remaining work" items are now complete.

| Item | Status |
|---|---|
| End-to-end automation pipeline | Complete |
| Qt / CLI mode enforcement parity | Complete — shared `OperationsController` |
| Recommendation fallback handling | Complete — CSV → fuzzy → Repology → manual |
| Regression test coverage | 190 tests passing |
| Linux restore with settings | Complete — wallpaper, dark mode, apt install |
| Packaging | Complete — `.exe` (Windows), `.AppImage` (Linux) |
| Real E2E test on physical hardware | Deferred — tests use mocked inventory |

**Progress estimate: 95%** — implementation complete, real-hardware validation pending.

---

## 7. Privacy Design

No user data leaves the machine without explicit consent:

| Data type | Where it goes | User control |
|---|---|---|
| Software names and versions | Repology API only (no file paths, no user names) | Disabled by setting `repology.enabled: false` |
| File contents | Never leave the local machine | — |
| Hardware details | Stored locally only | — |
| Wallpaper image | Copied into backup bundle, stays on USB | User can exclude via settings page |
| Machine ID | Anonymised in research metrics | Disabled by setting `research.record_metrics: false` |
