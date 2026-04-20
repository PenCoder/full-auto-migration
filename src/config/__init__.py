"""
Configuration system for the Windows-to-Linux migration framework.

This package provides a structured, strongly-typed configuration system
organized into three layers:

1. **Schema** (schema.py): Dataclass definitions for configuration structure
2. **Loader** (loader.py): Functions to load and parse configuration files
3. **Validator** (validator.py): Validation logic and error handling

Public API
----------
Main Classes:
- MigrationConfigRoot: Top-level configuration object
- ProjectConfig, SourceSystemConfig, TargetSystemConfig, etc.

Main Functions:
- load_config(path): Load configuration from YAML file
- load_default_config(): Load default configuration
- load_software_mapping(csv_path): Load Windows→Linux app mappings

Exceptions:
- ConfigError: Raised on configuration-related errors

Examples
--------
Basic usage (recommended):

    from src.config import load_config, MigrationConfigRoot
    
    config = load_config("configs/migration.config.yaml")
    print(config.project.name)
    print(config.migration.mode)

Using class method:

    from src.config import MigrationConfigRoot
    
    config = MigrationConfigRoot.load("configs/migration.config.yaml")

Loading software mappings:

    from src.config import load_software_mapping
    
    mappings = load_software_mapping()
    for mapping in mappings:
        print(mapping)

Architecture
------------
The configuration system follows the Single Responsibility Principle:

- **schema.py** defines WHAT the configuration looks like
- **loader.py** handles HOW to load the configuration
- **validator.py** ensures the configuration is VALID

This separation allows each module to be tested, modified, and extended
independently.
"""

from src.config.schema import (
    ProjectConfig,
    SourceSystemConfig,
    DemoConfig,
    TargetSystemConfig,
    MigrationConfig,
    AutomationConfig,
    ValidationConfig,
    ResearchConfig,
    BackupConfig,
    AIConfig,
    MigrationConfigRoot,
)
from src.config.loader import (
    load_config,
    load_default_config,
    load_software_mapping,
)
from src.config.validator import ConfigError

__all__ = [
    # Schema classes
    "ProjectConfig",
    "SourceSystemConfig",
    "DemoConfig",
    "TargetSystemConfig",
    "MigrationConfig",
    "AutomationConfig",
    "ValidationConfig",
    "ResearchConfig",
    "BackupConfig",
    "AIConfig",
    "MigrationConfigRoot",
    # Loader functions
    "load_config",
    "load_default_config",
    "load_software_mapping",
    # Validator exceptions
    "ConfigError",
]
