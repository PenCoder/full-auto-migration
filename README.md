# Full Automation: Windows to Linux Migration Framework

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A reproducible migration tool for moving from Windows to Linux with a Qt UI, CLI utilities, analysis services, backup and restore flows, and report generation.

## Project Map

- `app.py` launches the Qt application.
- `qt_app.py` is an alternate Qt launcher entry point.
- `src/qt_ui/` contains the active UI.
- `src/services/`, `src/analysis/`, `src/backup/`, and `src/inventory/` contain the core migration logic.
- `src/cli.py` provides command-line access to inventory, analysis, backup, profile, and reporting tasks.

## End-to-end flow

The tool runs in two phases on two machines:

| Phase | Machine | What happens |
|---|---|---|
| **1 — Prepare** | Windows 11 | Scan → app mapping → backup bundle created in `data/restore/` |
| **2 — Restore** | Linux Mint | Copy bundle → run tool → files restored, apps installed, settings applied |

---

## Phase 1 — Windows (scan + backup)

```bash
# Install dependencies
pip install -r requirements.txt

# Launch the Qt wizard (guided 7-step flow)
python app.py

# Or use the CLI directly
python -m src.cli scan --mode balanced
python -m src.cli backup --yes
```

The wizard writes the backup bundle to `data/restore/`:

```
data/restore/
├── manifest.json          # file list + SHA-256 checksums
├── backup.zip             # all selected files, directory structure preserved
├── apps_to_install.json   # Linux packages to install (apt)
├── settings_inventory.json
├── settings_migration_plan.json
└── settings_assets/
    └── wallpaper.jpg      # exported wallpaper image
```

Copy this entire `data/restore/` folder to a USB stick alongside the project folder.

---

## Phase 2 — Linux Mint (restore)

### Option A — Setup script (recommended, no build required)

Copy the project folder to the Linux machine (via USB, network, etc.), then:

```bash
bash setup_linux.sh           # installs deps + launches Qt wizard
bash setup_linux.sh --cli     # installs deps + shows CLI help
bash setup_linux.sh --restore /path/to/bundle   # headless restore
```

The script:
1. Checks Python 3.10+ is installed
2. Installs system Qt/graphics libraries via `apt`
3. Creates a `.venv` and installs Python deps
4. Launches the app

### Option B — AppImage (double-click, no installation, no Python needed)

Build the AppImage on any machine with Docker:

```bash
bash build_linux.sh
```

Output: `dist/MigrationWizard-x86_64.AppImage` (~120 MB, fully self-contained).

Copy it to the USB stick alongside the bundle folder. On Linux Mint:
- **Double-click** the `.AppImage` file in the file manager, or
- Run from terminal: `./MigrationWizard-x86_64.AppImage`

No installation, no Python, no dependencies required on the target machine.

### Option C — CLI restore (headless)

```bash
bash setup_linux.sh --restore /media/usb/data/restore
# or after activating the venv:
python -m src.cli restore --source /media/usb/data/restore
python -m src.cli validate
python -m src.cli report
```

---

## What the restore does

1. **Files** — extracted from `backup.zip` into the correct Linux home folders:
   - `Documents/` → `~/Documents/`
   - `Pictures/` → `~/Pictures/`
   - `Music/`, `Videos/`, `Desktop/`, `Downloads/` → matching Linux paths
   - Unknown folders → `~/Restored_Migration/<folder>/`
2. **File integrity** — SHA-256 verified against the manifest after copy
3. **Desktop settings** — applied automatically where possible:
   - Wallpaper copied to `~/.local/share/backgrounds/` and set via `gsettings`/`xfconf-query`
   - Light/Dark preference applied via the detected DE (Cinnamon, GNOME, XFCE, KDE, MATE)
   - A `~/settings_migration_guidance.md` file is written with manual steps for accent color, theme
4. **Linux apps** — installed via `apt` using `pkexec` (GUI password prompt)

---

## Configuration

`configs/migration.config.yaml` is the primary runtime configuration file.

Key sections:

- `source_system.backup_paths` — which Windows folders to back up
- `source_system.excluded_paths` — folders to skip (AppData/Temp, etc.)
- `source_system.file_types` — which file extensions to include
- `target_system.distro` — `linux-mint` or `ubuntu`
- `automation.auto_start_full_flow` — run the full pipeline automatically on launch

## Configuration

`configs/migration.config.yaml` is the primary runtime configuration file. The typed loader lives in `src/config.py`.

Key sections:

- `project` for metadata
- `source_system` for inventory and backup inputs
- `target_system` for Linux target settings
- `migration` for backup and install behavior
- `automation` for startup, logging, and checkpoints
- `validation` for post-install checks
- `research` for reproducibility tracking
- `ai` for optional recommendation ranking

Important notes:

- AI features are optional and must fall back safely when unavailable.
- Keep secrets out of the repository; use config values or environment variables for local testing only.
- `configs/linux_ms_map.csv` is the current Windows-to-Linux mapping source.

## Architecture

The repository uses a layered structure so the migration flow stays readable and easy to extend.

Entry points:

- `app.py` and `qt_app.py` start the Qt application.
- `src/cli.py` exposes the command-line interface.

Qt UI layer:

- `src/qt_ui/main_window.py` orchestrates the wizard flow.
- `src/qt_ui/pages/` contains the individual pages.
- `src/qt_ui/state.py` stores UI state shared across pages.

Orchestration layer:

- `src/orchestration/` centralizes user-facing error handling and step coordination.

Service layer:

- `src/services/` runs migration analysis, recommendation, reporting, restore, and validation workflows.

Domain layer:

- `src/inventory/`, `src/analysis/`, and `src/backup/` collect and transform the migration data.

Guidelines:

- Do not duplicate Tk and Qt implementations.
- Prefer new services over embedding business logic in UI pages.
- Keep the report layer separate from UI display logic.
- Treat generated artifacts as outputs, not source code.

## Reproducibility

Use these inputs as reproducibility anchors:

- `configs/migration.config.yaml`
- `configs/linux_ms_map.csv`
- inventory outputs in `data/`
- restore report artifacts in `data/restore/`
- generated reports in `docs/reports/`

Validation commands:

- `python -m py_compile app.py qt_app.py src/**/*.py`
- `python -m src.cli --help`
- start the Qt application and confirm the migration pages load in order

## Contributing

Keep changes small, focused, and deterministic.

Rules of thumb:

- preserve the separation between UI, orchestration, and services
- update the README whenever behavior, configuration, or file layout changes
- prefer descriptive names and short, purpose-driven functions
- remove unused files instead of keeping parallel implementations around
- document any AI or network-backed feature with its required environment variables and failure mode

Before opening a change, validate at minimum:

- `python -m py_compile` for touched Python files
- the Qt launcher import path
- config loading after YAML or schema changes
- any changed UI flow with the relevant page path

## Full Automation Startup

Enable these settings in `configs/migration.config.yaml` to auto-run the full flow when the Qt app opens:

- `automation.auto_start_full_flow: true`
- `automation.auto_start_delay_ms: 250`

Behavior:

- Windows runtime: scan -> analysis -> backup
- Linux runtime: restore -> validation

Linux requirement:

- `data/restore/manifest.json` and `data/restore/backup.zip` must exist before startup auto-run.

## Report Generation

After restore and validation, the app generates a final report bundle in `docs/reports/`.

Artifacts:

- `docs/reports/final_report.json`
- `docs/reports/final_report.md`
- `docs/reports/final_report.html`

What the report contains:

- sovereignty score and rating
- restore and validation summary
- file-level evidence from the restore report
- links to the generated markdown, HTML, and JSON outputs

If you are using the Qt app, the final wizard step is the report dashboard. It lets you generate the same report bundle and open the exported markdown or HTML directly.
