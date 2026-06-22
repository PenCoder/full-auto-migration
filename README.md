# Migration Wizard — Windows 11 to Linux Mint

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)
[![Tests](https://img.shields.io/badge/Tests-184%20passing%20%2F%20192%20total-yellow)](#testing)

A guided, privacy-preserving migration tool that moves your files, applications, and desktop settings from Windows 11 to Linux Mint — automatically, step by step, with no technical knowledge required.

It's an extension of an academic seminar project on **digital sovereignty** — the idea that the technical complexity of leaving a closed platform is itself a barrier to choosing an open one. See [`docs/PROJECT_WALKTHROUGH.md`](docs/PROJECT_WALKTHROUGH.md) for the full framing and the project's own honest account of what was and wasn't achieved.

---

## How it works

The tool runs in two phases on two machines.

| Phase | Machine | What happens |
|---|---|---|
| **1 — Prepare** | Windows 11 | Scan → app mapping → files and settings packed into a bundle |
| **2 — Restore** | Linux Mint | Bundle copied via USB → files restored, apps installed, settings applied — verified by hash, reported, and reversible |

---

## Quick start — Windows

### Option A — Double-click (no setup)

Build or download `migrate.exe`, double-click it, and follow the 7-step wizard.

### Option B — Run from source

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Launch the Qt wizard
python app.py

# 3. Or use the CLI
python -m src.cli scan --mode balanced
python -m src.cli backup --yes
```

---

## Quick start — Linux Mint

### Option A — Double-click (no setup)

The Windows-side bundle automatically embeds a pre-built Linux binary (`restore`) when one is available — copy the bundle to your USB stick, plug it into the Linux machine, and double-click the binary inside it.

> If nothing happens on double-click: right-click the file → Properties → Permissions → tick "Allow executing file as program".

### Option B — Build from source on the target machine

PyInstaller does not cross-compile, so the Linux binary must be built **on** a Linux Mint machine:

```bash
pip install -r requirements.txt
pyinstaller MigrationWizard_linux.spec
# Output: dist/restore — copy into assets/linux_build/restore so future
# Windows-side bundles embed it automatically.
```

### Option C — CLI (headless)

```bash
python -m src.cli restore --source /path/to/bundle
python -m src.cli validate
python -m src.cli report
```

---

## The migration bundle

Everything the Linux restore needs lives in one folder — `data/restore/` on Windows.
Copy this entire folder to your USB stick.

```
data/restore/
├── manifest.json             # file list + SHA-256 checksums
├── backup.zip                # all selected files, directory structure preserved
├── apps_to_install.json      # Linux packages to install via apt
├── settings_inventory.json   # wallpaper path, light/dark preference, accent colour
├── settings_migration_plan.json
├── settings_assets/
│   └── wallpaper.jpg         # your actual wallpaper image
└── linux_build/
    └── restore               # pre-built Linux binary, embedded automatically if available
```

---

## What the restore does

1. **Files** restored to the correct Linux home folders:

   | Windows folder | Linux destination |
   |---|---|
   | Documents | `~/Documents/` |
   | Pictures | `~/Pictures/` |
   | Music | `~/Music/` |
   | Videos | `~/Videos/` |
   | Desktop | `~/Desktop/` |
   | Downloads | `~/Downloads/` |
   | Other folders | `~/Restored_Migration/<folder>/` |

2. **File integrity** — every file SHA-256 verified against the manifest after copy

3. **Desktop settings** applied automatically:
   - Wallpaper set via `gsettings` / `xfconf-query` / KDE D-Bus
   - Light or dark mode applied to the detected desktop environment
   - A `~/settings_migration_guidance.md` file written for anything that needs manual attention

4. **Linux apps** installed via `apt` using `pkexec` (a password prompt appears — this is normal). Installs are attempted as a batch first, then retried per-package on failure, so one bad package name can't take down the whole install.

5. **Reset** — a restore can be undone: files removed, shortcuts removed, the wallpaper file cleaned up, and (opt-in only) installed apps uninstalled. Works even from a fresh app session, reading only the restore report.

---

## Building the distributables

### Windows — `migrate.exe`

```powershell
.\build.ps1
# Output: dist\migrate.exe
```

If `assets/linux_build/restore` already exists (built per Option B above), it's baked into the `.exe` so the result is a single standalone file.

### Linux — `restore` binary

Built directly on a Linux Mint VM — see "Quick start — Linux Mint, Option B" above. There is also a separate, currently-unused Docker/AppImage build path (`build_linux.sh`, `Dockerfile`) from an earlier design; it isn't referenced anywhere in the app and isn't the build used by the actual packaging flow.

---

## Wizard pages (Windows side)

| Step | Page | What happens |
|---|---|---|
| 1 | Welcome | Introduction and overview |
| 2 | Mode | Choose Guided, Balanced, or Expert |
| 3 | Scan | Inventory runs automatically; apps matched to Linux equivalents |
| 4 | Data | Choose file types and folders (skipped in Guided mode) |
| 5 | Review | App list and file list previewed |
| 6 | Backup | Bundle created |
| 7 | Bundle Report | Summary of what was packed |

All pages auto-trigger their work on entry — no action buttons to click. The Linux side is a single page: restore, verify, and report all happen within one click.

---

## Interaction modes

| Mode | Who it is for | What the user controls | Online lookups |
|---|---|---|---|
| **Guided** | Non-technical users | Nothing — the tool decides everything | Never |
| **Balanced** | Comfortable with computers | File types and app selection | Never |
| **Expert** | Advanced users | All of the above plus manual app mapping and overrides | Yes — verifies a package already chosen via Repology, never to find one |

Mode-dependent behaviour (whether analysis runs, whether file recommendations run, whether app matching goes online) is defined once in [`src/orchestration/mode_policy.py`](src/orchestration/mode_policy.py) and imported by both the Qt wizard and the CLI, so the two interfaces can't silently drift apart.

---

## CLI reference

```bash
python -m src.cli scan       --mode guided|balanced|expert  --deep
python -m src.cli backup     --yes
python -m src.cli restore    --source /path/to/bundle
python -m src.cli validate
python -m src.cli report
python -m src.cli inventory  all|hardware|software
python -m src.cli analyze    all|hardware|software
python -m src.cli usb        --iso /path/to/linuxmint.iso --device /dev/sdX
```

---

## Configuration

`configs/migration.config.yaml` controls runtime behaviour.

| Section | What it controls |
|---|---|
| `source_system.backup_paths` | Which Windows folders to back up |
| `source_system.excluded_paths` | Folders to skip — junk dirs are excluded automatically |
| `source_system.file_types` | Which file extensions to include |
| `backup.compress` | `true` creates `backup.zip`; `false` copies files as a directory |
| `target_system.distro` | `linux-mint` or `ubuntu` |
| `automation.auto_start_full_flow` | Run the full pipeline automatically on launch |
| `repology.enabled` | Enable online package verification in Expert mode (default: true) |

`configs/linux_ms_map.csv` is the Windows-to-Linux application mapping database (**238 entries**).

---

## Architecture

```
app.py                          Qt application entry point
src/
├── qt_ui/
│   ├── main_window.py          Orchestrates the wizard and navigation
│   ├── pages/                  One file per wizard page
│   ├── widgets/                Stepper sidebar, expert panel
│   ├── controllers/            Navigation, mode, operations, automation, activity log
│   ├── state.py                Shared UI state (QtUiState)
│   └── theme.qss               Stylesheet
├── services/
│   ├── migration_service.py    Inventory, analysis, backup orchestration
│   ├── restore_service.py      Linux-side restore — files, settings, apps, undo
│   ├── recommendation_service.py     App matching used by the wizard + CLI scan
│   ├── recommendations/        A second, separate app-matching implementation,
│   │                           used by the full-automation pipeline path
│   ├── file_recommendation_service.py
│   ├── settings_service.py     Settings migration planning
│   ├── validation_service.py   Sovereignty Score + restore validation
│   ├── report_service.py
│   ├── package_manager.py      apt install/remove with per-package fallback
│   └── pipeline_service.py     End-to-end full-automation pipeline with timing
├── orchestration/
│   └── mode_policy.py          Single source of truth for guided/balanced/expert behaviour
├── inventory/                  Hardware, software, settings collectors
├── analysis/                   HW compatibility matrix, SW mapping, fuzzy rules
├── backup/                     Manifest generator, file copy, zip creation
└── cli.py                      Typer CLI
configs/
├── migration.config.yaml       Runtime configuration
└── linux_ms_map.csv            App mapping database (238 entries)
```

**Note**: there are currently two independent app-recommendation implementations (`recommendation_service.py` and `services/recommendations/app_recommender.py`) serving two different entry points — the interactive wizard/CLI scan, and the separate full-automation pipeline. They duplicate similar logic (matching, scoring, Repology lookups) with different caching and timeout values. Worth unifying the same way `mode_policy.py` unified the mode-decision duplication, but not yet done.

---

## Testing

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src

# Run a specific level
python -m pytest tests/test_unit/
python -m pytest tests/test_integration/
python -m pytest tests/test_e2e/
python -m pytest tests/test_performance/
```

Current status: **192 collected — 184 passing, 5 failing, 3 skipped** (skips are PySide6 not being available in this shell, not a real gap).

The 5 known failures are pre-existing drift between tests and implementation, not flakiness:
- One test expects an `advanced_operations` field (`incremental_backup`) that was never implemented.
- Two `ModeController` tests assert behaviour (auto-opening the expert dock, auto-disabling the complete button in guided mode) that the controller's own code comments say was deliberately changed to manual-only control — the tests weren't updated to match.
- Two `SettingsMigrationService` tests expect a catalog item named `"Taskbar / Panel Layout"` (the actual item is named `"App Shortcuts"`) and expect 3 manual-review items where the service currently produces 2.

See [`docs/TESTING.md`](docs/TESTING.md) for testing strategy and [`docs/TEST_QUICK_REFERENCE.md`](docs/TEST_QUICK_REFERENCE.md) for the pytest command reference.

---

## Documentation

| Document | Description |
|---|---|
| [Project Walkthrough](docs/PROJECT_WALKTHROUGH.md) | Concise PM/sovereignty-framed account of the project, including its own honest critique |
| [Full Automation Exposé](docs/FULL_AUTOMATION_EXPOSE.md) | Revised exposé responding point-by-point to supervisor feedback |
| [Praktikum Report](docs/PRAKTIKUM_REPORT.md) | Official Praktikum deliverable — technical and academic project summary |
| [User Migration Guide](docs/USER_MIGRATION_GUIDE.md) | Step-by-step guide for end users, both machines |
| [Testing Strategy](docs/TESTING.md) | Test pyramid, organization, and patterns |
| [Test Quick Reference](docs/TEST_QUICK_REFERENCE.md) | pytest command cheat sheet |

---

## Contributing

- Keep the separation between UI pages, service layer, and domain layer
- All pages must call `set_scanning(True/False)` around background operations
- New features go in `src/services/` — not in UI pages
- Update `configs/linux_ms_map.csv` to add new app mappings
- Mode-dependent behaviour belongs in `src/orchestration/mode_policy.py`, not duplicated per-interface
- Run `python -m pytest tests/` before committing

---

## Licence

MIT — see [LICENSE](LICENSE).
