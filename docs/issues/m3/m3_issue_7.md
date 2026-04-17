## M3 – Issue 7: Integrate Configuration File

**Status:** Completed**

### Purpose
This issue ensures that all commands in the CLI framework load and apply settings from the central configuration file `migration.config.yaml`. This makes the migration framework reproducible, configurable, and cleanly separated from hard-coded values.

### Key Features
- Central configuration module (`src/config.py`).
- Support for default and custom config files using `--config`.
- Typed configuration objects (MigrationConfigRoot and nested classes).
- Automatic integration with the logging system.
- Configuration-driven inventory, analysis, backup, and validation behaviors.

### Benefits
- Ensures uniform behavior across all modules.
- Improves maintainability and reduces duplication.
- Supports advanced use cases and automation in later milestones.
- Enables reproducible experiments, required for academic reporting.

---
The attribute `source_system.windows_user` was removed from the configuration file because
the username can be resolved programmatically using `Path.home()` or `getpass.getuser()`.
Storing it in YAML would require users to manually edit the configuration file, which is 
error-prone and unnecessary. Instead, all paths in the configuration are treated as relative 
to the detected user home directory.
