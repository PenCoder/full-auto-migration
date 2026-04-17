# Semi-Automated Windows → Linux Migration Framework

A semi-automated framework for migrating a **Windows 11 user environment**
to Linux (Linux Mint / Ubuntu), providing tooling for inventory collection,
data backup, restoration, and post-migration validation.

> Scope note: This repository implements an automation framework and supporting tooling.

> It focuses on the migration workflow surrounding inventory collection,
data backup, restoration, integrity verification, and application re-installation assistance.

---

## Features

The framework is split into two execution phases:

### Windows-side (Source)
- Hardware inventory (PowerShell / CIM)
- Software inventory (registry uninstall keys)
- Backup manifest generation:
  - Enumerates selected folders
  - Filters by selected file types/extensions
  - Computes SHA-256 hashes
- Backup payload staging (copies files into a structured bundle)
- Optional ZIP archive creation (portable backup.zip)

### Linux-side (Target)
- Extracts backup archive into a staging directory
- Restores files into the target home directory
- Verifies integrity using SHA-256 (manifest vs restored)
- Optional application install (apt packages via pkexec)

---

## Repository Structure


### CLI Structure

- `src/cli.py` — Typer CLI entrypoint (inventory/analyze/backup + stubs)
- `src/inventory/` — Windows inventory collectors
- `src/analysis/` — Hardware compatibility + software mapping
- `src/backup/manifest.py` — Manifest generation + backup staging
- `src/services/restore_service.py` — Linux restore workflow
- `configs/migration.config.yaml` — Main config
- `configs/linux_ms_map.csv` — Windows→Linux software mapping table
- `docs/` — Research notes, reports, technical specs

The CLI is primarily intended for development, testing, and experimentation.
End-users are expected to interact with the system via the GUI.


### GUI Structure

- `app.py` — Application entrypoint
- `src/ui/` — Tkinter wizard pages
- `src/services/` — orchestration for inventory / analysis / backup / restore
- `src/backup/` — manifest generation, file copying, optional archive
- `src/inventory/` — hardware/software discovery
- `src/analysis/` — compatibility matrix + software mapping generation
- `configs/` — `migration.config.yaml` and software mapping CSV
- `data/restore/` — runtime output (manifest, restore report, archives)

---

## Runtime Outputs (where to look)

Both Windows and Linux executions write runtime artifacts using the same
directory structure for consistency.
The GUI writes its outputs under:

- **Development run:** `./data/restore/`
- **Packaged run (PyInstaller):** next to the executable: `./data/restore/`

Common files:

- `data/restore/manifest.json` — backup manifest (file list, hashes, sizes)
- `data/<backup_output_dir>/files/` — copied backup payload
- `data/restore/<archive_name>` — optional compressed archive
- `data/restore/restore_report.json` — restore + validation report (Linux)

---

## Requirements

### Windows (source machine)
- Python 3.11+
- PowerShell available in PATH
- Permissions to read target folders to be backed up

### Linux (target machine)
- Python 3.11+ (only required when running from source)
- `pkexec` available (PolicyKit) if using app installation
- `apt-get` (Debian/Ubuntu/Mint-based distros)

---

## Installation (Developer / Local)

This section is intended for developers or contributors running the
application from source. End-users should use the packaged executables in the `/dist/`.

### 1) Create a virtual environment
Windows (PowerShell):
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Linux:

```shell
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### Configuration

Edit: `configs/migration.config.yaml`

Key settings:

- `source_system.backup_paths` — folders to consider for backup
- `source_system.excluded_paths` — prefix-based exclusions (e.g., cache folders)
- `source_system.file_types` — file extension filter (supports `pdf` or `.pdf`)
- `source_system.backup_output_dir` — where copied files go under `./data/`
- `migration.software_map_config` — mapping CSV (relative to `configs/` or absolute)
- `backup.compress` and `backup.archive_name` — zip creation

---

## Usage (GUI)

Executables can be found in the `/dist/` directory
- `app` -> Linux executable
- `LinApp.desktop` -> Linux executable launcher
    - Note: Double click this file on linux to run the restoration on linux
- `WinApp.exe` -> Windows executable and launcher

**NB:** Go to next after each step

### On Windows (Backup Phase)

1. Launch the GUI (Double click `WinApp.exe`).
2. Select the operating **mode**.
3. Choose:
   - folders to back up (overrides `source_system.backup_paths` for this run)
   - file types to include (overrides `source_system.file_types`)
   - applications to reinstall

4. Run **Inventory**.
5. Run **Analysis**.
6. Run **Backup**.
7. Collect the produced payload:
   - `data/restore/`
   - `restore` directory include : `apps_to_install.json`, `backup.zip` and `manifest.json`.

After this step, the directory should contain:
- `/data/`
- `/log/`
- `WinApp.exe`
- `app`
- `LinApp.desktop`

Copy the payload to an external drive or a transfer location accessible from Linux.

### On Linux (Restore + Validation Phase)

The validation step compares restored files against the original manifest
and generates a detailed integrity report.

1. Launch the GUI on Linux (Double click `LinApp.desktop`).
2. Point the application (or your workflow) to the copied backup payload (`/data/restore/`).
3. Run **Restore**.
4. Run validation to review the final report:
   - `data/restore/restore_report.json`
    *NB: The validation step compares restored files against the original manifest and generates a detailed integrity report.*
---

## Deployment (GUI)

This section describes packaging the **GUI** as a desktop application.
CLI usage is intentionally not covered.

### 1) Install dependencies

Create a virtual environment and install:

```bash
pip install -r requirements.txt
```

### 2) Run from source

```bash
python app.py
```

### 3) Building packaged executables

Install PyInstaller:

```bash
pip install pyinstaller
```

#### Windows Package build

From the project root:

```powershell
.\build.ps1 
```

Output:
- `dist/WinApp.exe`

### Linux Package build

The Linux package can be built either:
- on Windows using Docker, or
- directly on a Linux distribution.

1. Using docker on windows, 

    From the project root:

    ```bash
    docker compose up --build
    ```

2. On linux distro

    From the project root:

    - Install modules
    ```bash
    pip install -r requirements.txt
    ```

    - Build package
    ```bash
    pyinstaller --noconsole --onefile app.py \
    --name app \
    --add-data "configs:configs"
    ```

Output:
    - `dist/app`


> Notes:
> - The application creates `data/` and `logs/` next to the executable at runtime.

---

## Troubleshooting

### Backup finds zero files
- Check `source_system.file_types` is enabled for the extensions you expect.
- Ensure extensions are written consistently (the app supports `pdf` and `.pdf`).
- Confirm folders exist and are accessible.

### Some folders should not be backed up
- Add prefix exclusions to `source_system.excluded_paths`.
- Example:
  - `C:\Users\<user>\AppData\Local\Temp`

### Mapping CSV not found
- If you use an absolute path for `migration.software_map_config`, the app uses it.
- If you use a relative path, it is resolved under `configs/`.

### Restore report missing
- Restore/validation writes to: `data/restore/restore_report.json`
- Confirm the restore step completed successfully.

---

## Security & Privacy

- The manifest contains file paths and hashes; treat it as sensitive.
- If you share reports, consider removing usernames/paths or using anonymization.

---

<!-- ## License -->
