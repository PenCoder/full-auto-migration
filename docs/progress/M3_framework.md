# Milestone M3 — Semi-Automated Migration Framework  
### Design, Architecture, and Implementation Plan  
### Semi-Automated Migration from Windows 11 to Linux Mint  
### MSc Informatik — Project Documentation

---

## 1. Introduction

Milestone M3 transforms the analytical results from M2 into a **functional semi-automated migration framework**.  
This milestone introduces:

- a unified **Python CLI** for inventory, analysis, and backup  
- a fully interactive **GUI Wizard** built with Tkinter  
- a new **Migration Preferences module**, enabling mode-dependent behavior  
- manifest-based backup packaging  
- stub commands for restore, validation, and USB creation  

M3 marks the first *end-to-end demonstrable* version of the system.

---

## 2. Objectives of Milestone M3

1. **Design the CLI orchestration layer** (Typer-based).  
2. **Integrate all M2 modules** (inventory, analysis, mapping, backup).  
3. **Implement core CLI commands**:
   - `inventory` – hardware/software/all  
   - `analyze` – matrix/mapping/all  
   - `backup` – manifest generation  
   - `restore` – stub  
   - `validate` – stub  
   - `usb` – stub  
4. **Implement GUI Wizard** with:
   - multi-step navigation  
   - non-blocking threaded execution  
   - centralized mode handling  
5. **Add Migration Preferences Page**, enabling:
   - Guided Mode  
   - Balanced Mode  
   - Expert Mode  
6. **Enable configuration loading**, logging, and safe prompts.  
7. Prepare for testing and restoration implementation in M4.

---

## 3. Framework Architecture Overview

### 3.1 Architectural Layers

| Layer | Responsibilities | Components |
|------|------------------|------------|
| **GUI Wizard Layer** | Multi-step workflow, mode handling, user input | `src/ui/wizard.py`, `src/ui/pages/*` |
| **Preferences Layer** | Guided/Balanced/Expert configuration | `src/ui/pages/preferences.py` |
| **CLI Orchestration Layer** | Command execution, routing, safety | `src/cli.py` |
| **Configuration Layer** | YAML loading, path validation | `src/config.py` |
| **Logging Layer** | Namespaced event logging | `src/loggers.py` |
| **Inventory Layer** | Hardware/software collection | `src/inventory/*` |
| **Analysis Layer** | Compatibility matrix, mapping | `src/analysis/*` |
| **Backup Layer** | Manifest + file packaging | `src/backup/manifest.py` |
| **Migration Layer (Future)** | Restore, validation, USB automation | `src/restore/*`, `src/validate/*` |

---

## 4. New Component Added — Migration Preferences Module

Milestone M3 introduces a **mode-specific configuration system** controlling how much automation the user experiences.

### 4.1 Mode Definitions

| Mode | Description | User Interaction |
|------|-------------|------------------|
| **Guided** | Maximum automation | No decisions; system selects folders & apps |
| **Balanced** | Recommended defaults with user adjustments | User selects folder categories; apps installed automatically |
| **Expert** | Full manual control | User controls all aspects of backup/app restore |

### 4.2 Folder Selection Logic

Users can choose which logical folder groups to migrate:

- Documents  
- Pictures  
- Downloads  
- Desktop  

These selections feed directly into the backup subsystem:

```python
controller.state["selected_folders"]
controller.state["selected_apps"]
```

### 4.3 Impact on Backup + Restore

- Guided → all recommended folders + mapped apps included

- Balanced → user-selected folder categories affect backup manifest

- Expert → future full customization including per-file or per-app mapping

This module is implemented in:

```bash
src/ui/pages/preferences.py
```

---

## 5. System Architecture Diagram

```

                    +-------------------------------+
                    |       GUI Wizard Layer        |
                    |   Mode → Preferences → Steps  |
                    +-------------------------------+
                         /         |            \
                        v          v             v
                    Inventory   Analysis       Backup
                    (M2 code)   (M2 code)     Manifest
                     |            |            |
                     v            v            v
         hardware_inventory   matrices     manifest.json
         software_inventory   mapping      files/
                                  |
                                  v
            +--------------------------------------------+
            |          Future Milestones (M4–M6)          |
            | Restore → Automatic App Install → Validate  |
            +--------------------------------------------+

```

---

## 6. CLI Design (Typer)

Command hierarchy:

```

semi-migrate
│
├── inventory (hardware/software/all)
├── analyze   (hardware/software/all)
├── backup    (manifest + file packaging)
├── restore   (stub)
├── validate  (stub)
└── usb       (stub)
```

All commands support:

YAML configuration

namespaced logging

prompt bypass via --yes

---

## 7. Core Implementations in M3
### 7.1 Preferences Page (New in M3)

A new GUI page added after mode selection:

- Guided: summary screen, auto-selections

- Balanced: folder checkboxes + app auto-install

- Expert: full customization (future extension)

Provides actual functional difference across modes.

---

### 7.2 Backup Manifest + File Packaging

Backup now includes:

- Manifest (`manifest.json`)

- Real file copies (`backup/files/`)

Manifest structure:

```json
{
  "timestamp": "...",
  "total_files": 32,
  "entries": [
    {
      "source_path": "...",
      "relative_path": "...",
      "size_bytes": ...,
      "sha256": "..."
    }
  ]
}

```

File packaging uses:

```
shutil.copy2(src,dest)
```

---

---

### 7.3 Non-Blocking Wizard Execution (Threaded)

Each page runs CLI commands in background threads:

- prevents UI freezing

- spinner indicates progress

- full responsiveness during scanning, analysis, backup

---

### 7.4 Demo Mode

Demo mode allows:

- instant inventory, analysis, backup output

- limited file scanning

- extremely fast demonstration workflow

Enabled via:

```yaml
demo:
  mode: true
```

Provides clean, reliable presentation experience.

---

## 8. Workflow Summary

```pgsql
User → Mode → Preferences → Inventory → Analysis → Backup → Summary
                                                      |
                                                    manifest.json + files/

```

---

## 9. Summary of M3 Achievements

- Fully operational multi-step GUI wizard

- Mode-specific Preferences Page

- Integrated CLI commands

- Backup manifest + file packaging

- Threaded long-running tasks

- Demo mode for presentations

- Config-driven architecture with logging

- Foundation for restore + validation in M4