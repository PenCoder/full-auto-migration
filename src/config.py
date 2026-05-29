"""
Backward compatibility module for the configuration system.

This module maintains backward compatibility with code that imports
from src.config. All functionality has been moved to the src.config
package (config/), but this module re-exports the public API.

New code should import from src.config directly:
    from src.config import load_config, MigrationConfigRoot

Existing code can continue to import from src.config:
    from src.config import load_config, MigrationConfigRoot

Both work identically.
"""

# Re-export all public APIs from the config package
from src.config import (
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
    load_config,
    load_default_config,
    load_software_mapping,
    ConfigError,
)

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
