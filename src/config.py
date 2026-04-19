from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Literal, Any, Dict, Optional

import yaml

from src.constants import BASE_DIR, CONFIG_DIR


# ---------------------------------------------------------------------------
# Dataclass definitions for the configuration schema
# ---------------------------------------------------------------------------

@dataclass
class ProjectConfig:
    """Metadata describing the overall project context."""
    name: str
    version: str
    maintainer: str


@dataclass
class SourceSystemConfig:
    """Configuration for the Windows source system."""
    windows_user: Optional[str]
    inventory_output_dir: str
    backup_output_dir: str
    backup_paths: List[str]
    excluded_paths: List[str] = field(default_factory=list)
    file_types: Dict[str, bool] = field(default_factory=dict)


@dataclass
class DemoConfig:
    """Demo."""
    include_dirs: str
    mode: bool = True
    max_files: int = 30
    file_extensions: List[str] = field(default_factory=list)

@dataclass
class TargetSystemConfig:
    """Configuration for the Linux target system."""
    distro: Literal["linux-mint", "ubuntu"]
    edition: str
    language: str
    timezone: str
    hostname: str
    username: str
    auto_login: bool = False


@dataclass
class MigrationConfig:
    """Migration-related parameters (disk layout, mode, packages)."""
    mode: Literal["full_clean", "dual_boot"]
    target_disk: str
    layout: Literal["full_disk", "custom"]
    swap_size_gb: int
    encrypt_root: bool = False
    backup_location: str = "/mnt/backup"
    include_hidden_files: bool = False
    software_profile: Literal["standard", "developer", "custom"] = "standard"
    extra_packages: List[str] = field(default_factory=list)
    software_map_config: str = "linux_ms_map.csv"


@dataclass
class AutomationConfig:
    """Runtime automation behaviour."""
    dry_run: bool = False
    auto_start_full_flow: bool = False
    auto_start_delay_ms: int = 250
    enable_dynamic_rules: bool = True
    active_profile_path: str = "data/profiles/active_profile.json"
    checkpoint_dir: str = "data/checkpoints"
    logging_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_file: str = "logs/migration.log"
    confirm_destructive_actions: bool = True


@dataclass
class ValidationConfig:
    """Post-installation validation settings."""
    check_network: bool = True
    check_audio: bool = True
    check_gpu: bool = True
    check_video_playback: bool = True
    check_office_suite: bool = True


@dataclass
class ResearchConfig:
    """Research-related logging and anonymisation settings."""
    record_metrics: bool = True
    anonymize_machine_id: bool = True
    save_run_summary: str = "logs/run_summary.json"


@dataclass
class BackupConfig:
    """Backup-related settings."""
    compress: bool = False
    archive_name: str = "backup.zip"

@dataclass
class MigrationConfigRoot:
    """Top-level configuration object encapsulating all sections."""
    project: ProjectConfig
    source_system: SourceSystemConfig
    target_system: TargetSystemConfig
    migration: MigrationConfig
    automation: AutomationConfig
    validation: ValidationConfig
    research: ResearchConfig
    app_demo: DemoConfig
    backup: BackupConfig

# ---------------------------------------------------------------------------
# Loader and validation helpers
# ---------------------------------------------------------------------------

class ConfigError(Exception):
    """Custom exception for configuration-related errors."""
    pass


def _require_section(raw: Dict[str, Any], key: str) -> Dict[str, Any]:
    """Ensure a top-level section exists in the YAML structure."""
    if key not in raw:
        raise ConfigError(f"Missing required configuration section: '{key}'")
    section = raw[key]
    if not isinstance(section, dict):
        raise ConfigError(f"Section '{key}' must be a mapping (YAML object).")
    return section


def load_config(path: str | Path) -> MigrationConfigRoot:
    """
    Load and validate the migration configuration from a YAML file.

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
    )


def load_default_config() -> MigrationConfigRoot:
    """
    Convenience function to load the default configuration file.

    By convention, this attempts to load:
        ./configs/migration.config.yaml

    This can be adapted if the project adopts a different convention.
    """
    default_path = CONFIG_DIR / "migration.config.yaml"
    return load_config(default_path)


def load_software_mapping(csv_path: Optional[Path | str]) -> list[dict]:
    """
    Load Windows → Linux software mappings from CSV.
    """
    mappings = []
    if csv_path is None:
        csv_path = CONFIG_DIR / "linux_ms_map.csv"
    else:
        csv_path = CONFIG_DIR / csv_path

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mappings.append(row)
    return mappings
