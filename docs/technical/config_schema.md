# Configuration Schema Documentation
This document defines the structure, purpose, and semantics of the configuration file used by the semi-automated migration framework. The configuration schema ensures that the migration tool remains reproducible, extensible, and applicable across different systems.

---

## 1. Overview
The migration framework uses a YAML configuration file (`migration.config.yaml`) to centralize all parameters required for:

- Source system analysis  
- User data backup  
- Target Linux installation preparation  
- Automation behavior  
- Validation routines  
- Research logging  

This schema guarantees that the migration process remains deterministic and academically reproducible.

---

## 2. Schema Structure
The configuration file is structured into seven primary sections:

1. `project`
2. `source_system`
3. `target_system`
4. `migration`
5. `automation`
6. `validation`
7. `research`

Each section is described in detail below.

---

## 3. Section Descriptions

### 3.1 `project`
Metadata describing the overall project context.

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Human-readable project title. |
| `version` | string | Semantic version of the migration framework. |
| `maintainer` | string | Contact or author responsible for the configuration. |

---

### 3.2 `source_system`
Defines parameters relevant to the Windows system being migrated.

| Field | Type | Description |
|-------|------|-------------|
| `windows_user` | string | Username of the Windows account to migrate. |
| `inventory_output_dir` | string | Directory where inventory (JSON/CSV) files will be written. |
| `backup_output_dir` | string | Directory where the backup archive or manifest will be stored. |
| `backup_paths` | list of strings | Directories containing user data to back up. |
| `excluded_paths` | list of strings | Paths that should be ignored during backup. |

---

### 3.3 `target_system`
Defines the Linux Mint target installation environment.

| Field | Type | Description |
|-------|------|-------------|
| `distro` | enum | Target distribution (`linux-mint`, `ubuntu`). |
| `edition` | string | Desktop environment (e.g., `cinnamon`, `mate`, `xfce`). |
| `language` | string | System locale to configure after installation. |
| `timezone` | string | Geographic timezone for the system. |
| `hostname` | string | Computer hostname for the Linux installation. |
| `username` | string | Username to create on Linux. |
| `auto_login` | boolean | Whether to enable auto-login for the created user. |

---

### 3.4 `migration`
Defines how the migration should be executed.

| Field | Type | Description |
|-------|------|-------------|
| `mode` | enum | `full_clean` or `dual_boot` (future extension). |
| `target_disk` | string | Disk device for installation (e.g., `/dev/sda`). |
| `layout` | enum | Partitioning method (`full_disk`, `custom`). |
| `swap_size_gb` | integer | Size of swap partition. |
| `encrypt_root` | boolean | Whether to enable full-disk encryption. |
| `backup_location` | string | Location where Windows backup will be mounted under Linux. |
| `include_hidden_files` | boolean | Whether the backup includes hidden files. |
| `software_profile` | enum | `standard`, `developer`, or `custom`. |
| `extra_packages` | list of strings | Additional Linux packages to install. |

---

### 3.5 `automation`
Controls runtime behavior of the migration framework.

| Field | Type | Description |
|-------|------|-------------|
| `dry_run` | boolean | If true, no destructive actions will be executed. |
| `logging_level` | enum | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `log_file` | string | Output log file path. |
| `confirm_destructive_actions` | boolean | Whether to require explicit confirmation. |

---

### 3.6 `validation`
Defines which system checks to perform post-installation.

| Field | Type | Description |
|-------|------|-------------|
| `check_network` | boolean | Verify that network interfaces operate correctly. |
| `check_audio` | boolean | Verify audio playback. |
| `check_gpu` | boolean | Verify GPU driver functionality. |
| `check_video_playback` | boolean | Test video rendering capability. |
| `check_office_suite` | boolean | Confirm office suite availability. |

---

### 3.7 `research`
Defines parameters for empirical tracking and reproducibility.

| Field | Type | Description |
|-------|------|-------------|
| `record_metrics` | boolean | Log automation metrics. |
| `anonymize_machine_id` | boolean | Remove identifying hardware IDs. |
| `save_run_summary` | string | Path to store summary of each migration run. |

---

## 4. Validation and Error Handling
The configuration file is validated by the Python loader (`src/config.py`) to ensure:

- All required fields are present  
- Field types are correct  
- Unknown sections produce warnings  
- Migration mode and partitioning choices are compatible  

Validation supports academic reproducibility and eliminates ambiguous configuration states.

---

## 5. Example File
See `migration.config.example.yaml` for a complete working example.

---

## 6. Versioning
This schema follows semantic versioning. Changes to structure must be documented in:

