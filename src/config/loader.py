"""
Configuration loading and parsing logic.

This module handles loading configuration files from disk, parsing YAML,
and constructing configuration objects. It provides high-level functions
for common loading scenarios.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from src.constants import BASE_DIR, CONFIG_DIR
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
from src.config.validator import ConfigError, validate_section


def _require_section(raw: Dict[str, Any], key: str) -> Dict[str, Any]:
    """
    Ensure a top-level section exists in the YAML structure.

    Parameters
    ----------
    raw : Dict[str, Any]
        The raw parsed YAML dictionary.
    key : str
        The required section key.

    Returns
    -------
    Dict[str, Any]
        The section dictionary.

    Raises
    ------
    ConfigError
        If the section is missing or not a mapping.
    """
    if key not in raw:
        raise ConfigError(f"Missing required configuration section: '{key}'")
    section = raw[key]
    if not isinstance(section, dict):
        raise ConfigError(f"Section '{key}' must be a mapping (YAML object).")
    return section


def load_config(path: str | Path) -> MigrationConfigRoot:
    """
    Load and validate the migration configuration from a YAML file.

    This function:
    1. Reads the YAML file from disk
    2. Validates that all required sections exist
    3. Instantiates dataclass objects for each section
    4. Returns a complete MigrationConfigRoot object

    Parameters
    ----------
    path : str | Path
        Path to the YAML configuration file.

    Returns
    -------
    MigrationConfigRoot
        Fully populated configuration object.

    Raises
    ------
    FileNotFoundError
        If the configuration file does not exist.
    ConfigError
        If required sections or fields are missing or malformed.
    yaml.YAMLError
        If the YAML syntax is invalid.

    Examples
    --------
    >>> config = load_config("configs/migration.config.yaml")
    >>> print(config.project.name)
    >>> print(config.migration.mode)
    """
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse YAML configuration: {e}") from e

    if not isinstance(raw, dict):
        raise ConfigError("Top-level configuration must be a mapping (YAML object).")

    # Extract and validate sections
    project_raw = _require_section(raw, "project")
    source_raw = _require_section(raw, "source_system")
    target_raw = _require_section(raw, "target_system")
    migration_raw = _require_section(raw, "migration")
    automation_raw = raw.get("automation", {})
    validation_raw = raw.get("validation", {})
    research_raw = raw.get("research", {})
    demo_raw = raw.get("demo", {})
    backup_raw = raw.get("backup", {})
    ai_raw = raw.get("ai", {})

    try:
        project_cfg = ProjectConfig(**project_raw)
        source_cfg = SourceSystemConfig(**source_raw)
        target_cfg = TargetSystemConfig(**target_raw)
        migration_cfg = MigrationConfig(**migration_raw)
        automation_cfg = AutomationConfig(**automation_raw)
        validation_cfg = ValidationConfig(**validation_raw)
        research_cfg = ResearchConfig(**research_raw)
        demo_cfg = DemoConfig(**demo_raw)
        backup_cfg = BackupConfig(**backup_raw)
        ai_cfg = AIConfig(**ai_raw)
    except TypeError as e:
        # This typically indicates wrong or missing fields within a section
        raise ConfigError(f"Configuration field mismatch: {e}") from e

    return MigrationConfigRoot(
        project=project_cfg,
        source_system=source_cfg,
        target_system=target_cfg,
        migration=migration_cfg,
        automation=automation_cfg,
        validation=validation_cfg,
        research=research_cfg,
        app_demo=demo_cfg,
        backup=backup_cfg,
        ai=ai_cfg,
    )


def load_default_config() -> MigrationConfigRoot:
    """
    Convenience function to load the default configuration file.

    By convention, this attempts to load:
        ./configs/migration.config.yaml

    Returns
    -------
    MigrationConfigRoot
        The default configuration.

    Raises
    ------
    FileNotFoundError
        If the default configuration file does not exist.
    ConfigError
        If the configuration is invalid.

    Examples
    --------
    >>> config = load_default_config()
    """
    default_path = CONFIG_DIR / "migration.config.yaml"
    return load_config(default_path)


def load_software_mapping(csv_path: Optional[Path | str] = None) -> list[dict]:
    """
    Load Windows → Linux software mappings from a CSV file.

    Reads a CSV file containing mappings of Windows applications to their
    Linux equivalents. If no path is provided, uses the default mapping
    file in the configs directory.

    Parameters
    ----------
    csv_path : Optional[Path | str]
        Path to the CSV mapping file. If None, defaults to
        "configs/linux_ms_map.csv".

    Returns
    -------
    list[dict]
        A list of dictionaries, one per row, representing software mappings.

    Raises
    ------
    FileNotFoundError
        If the CSV file does not exist.
    csv.Error
        If the CSV is malformed.

    Examples
    --------
    >>> mappings = load_software_mapping()
    >>> for mapping in mappings:
    ...     print(f"{mapping['windows_app']} -> {mapping['linux_app']}")
    """
    if csv_path is None:
        csv_path = CONFIG_DIR / "linux_ms_map.csv"
    else:
        csv_path = CONFIG_DIR / csv_path

    mappings = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mappings.append(row)
    return mappings
