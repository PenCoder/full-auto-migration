# Migration Wizard — Windows 11 to Linux Mint

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)
[![Tests](https://img.shields.io/badge/Tests-190%20passing-brightgreen)](#testing)

A guided, privacy-preserving migration tool that moves your files, applications, and desktop settings from Windows 11 to Linux Mint — automatically, step by step, with no technical knowledge required.

---

## How it works

The tool runs in two phases on two machines.

| Phase | Machine | What happens |
|---|---|---|
| **1 — Prepare** | Windows 11 | Scan → app mapping → files and settings packed into a bundle |
| **2 — Restore** | Linux Mint | Bundle copied via USB → files restored, apps installed, settings applied |

---

## Quick start — Windows

### Option A — Double-click (no setup)

Build or download `MigrationWizard.exe`, double-click it, and follow the 7-step wizard.

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

### Option A — AppImage (recommended, double-click, no setup)

Copy `MigrationWizard-x86_64.AppImage` from the USB stick to your Linux machine and double-click it.

> If nothing happens on double-click: right-click the file → Properties → Permissions → tick "Allow executing file as program".

### Option B — Setup script (from source, no Docker)

```bash
bash setup_linux.sh                                    # installs deps + opens wizard
bash setup_linux.sh --restore /media/usb/data/restore  # headless restore
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
└── settings_assets/
    └── wallpaper.jpg         # your actual wallpaper image
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

4. **Linux apps** installed via `apt` using `pkexec` (a password prompt appears — this is normal)

---

## Building the distributables

### Windows — `.exe`

Run `build.ps1` in PowerShell. Requires PyInstaller (`pip install pyinstaller`).

```powershell
.\build.ps1
# Output: dist\MigrationWizard.exe
```

### Linux — AppImage

Requires Docker. Works on Windows, macOS, or Linux.

```bash
bash build_linux.sh
# Output: dist/MigrationWizard-x86_64.AppImage
```

---

## Wizard pages (Windows side)

| Step | Page | What happens |
|---|---|---|
| 1 | Welcome | Introduction and overview |
| 2 | Mode Selection | Choose Guided, Balanced, or Expert |
| 3 | Scan & Plan | Inventory runs automatically; app alternatives matched |
| 4 | Settings Migration | Wallpaper and theme captured |
| 5 | Data Selection | Choose file types and folders |
| 6 | Review & Confirm | App list and file list previewed |
| 7 | Create Backup Bundle | Bundle created automatically |

All pages auto-trigger their work on entry — no action buttons to click.

---

## Interaction modes

| Mode | Who it is for | What the user controls |
|---|---|---|
| **Guided** | Non-technical users | Nothing — the tool decides everything |
| **Balanced** | Comfortable with computers | File types and app selection |
| **Expert** | Advanced users | All of the above plus manual app mapping and overrides |

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
| `repology.enabled` | Enable online package verification (default: true) |

`configs/linux_ms_map.csv` is the Windows-to-Linux application mapping database (150+ entries).

---

## Architecture

```
app.py                          Qt application entry point
src/
├── qt_ui/
│   ├── main_window.py          Orchestrates the wizard and navigation
│   ├── pages/                  One file per wizard page
│   ├── widgets/                Stepper sidebar, expert panel
│   ├── controllers/            Navigation, mode, operations, activity log
│   ├── state.py                Shared UI state (QtUiState)
│   └── theme.qss               Stylesheet
├── services/
│   ├── migration_service.py    Inventory, analysis, backup orchestration
│   ├── restore_service.py      Linux-side restore — files, settings, apps
│   ├── recommendation_service.py
│   ├── file_recommendation_service.py
│   ├── validation_service.py
│   ├── report_service.py
│   └── pipeline_service.py     End-to-end pipeline with timing
├── inventory/                  Hardware, software, settings collectors
├── analysis/                   HW compatibility matrix, SW mapping, fuzzy rules
├── backup/                     Manifest generator, file copy, zip creation
├── orchestration/              Error handling, checkpointing
└── cli.py                      Typer CLI
configs/
├── migration.config.yaml       Runtime configuration
└── linux_ms_map.csv            App mapping database
```

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

Current status: **190 passing, 3 skipped** (PySide6 not available in CI).

---

## Documentation

| Document | Description |
|---|---|
| [User Manual](docs/USER_MANUAL.md) | Step-by-step guide for end users |
| [Praktikum Report](docs/PRAKTIKUM_REPORT.md) | Technical and academic project summary |
| [Project Management Plan](docs/PROJECT_MANAGEMENT_PLAN.md) | WBS, timeline, risk register |

---

## Contributing

- Keep the separation between UI pages, service layer, and domain layer
- All pages must call `set_scanning(True/False)` around background operations
- New features go in `src/services/` — not in UI pages
- Update `configs/linux_ms_map.csv` to add new app mappings
- Run `python -m pytest tests/` before committing

---

## Licence

MIT — see [LICENSE](LICENSE).
