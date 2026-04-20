"""
Configuration schema definitions using dataclasses.

This module defines the complete structure of the migration configuration
through strongly-typed dataclasses. Each dataclass represents a logical
section of the configuration with its own set of parameters.

The main entry point is MigrationConfigRoot which aggregates all sections.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


@dataclass
class ProjectConfig:
    """
    Metadata describing the overall project context.

    This section contains information about the project itself, useful for
    documentation, logging, and audit trails.
    """
    name: str
    version: str
    maintainer: str


@dataclass
class SourceSystemConfig:
    """
    Configuration for the Windows source system.

    Specifies where to collect data from, where to store collected data,
    and which paths/file types to include or exclude.
    """
    windows_user: Optional[str]
    inventory_output_dir: str
    backup_output_dir: str
    backup_paths: List[str]
    excluded_paths: List[str] = field(default_factory=list)
    file_types: Dict[str, bool] = field(default_factory=dict)


@dataclass
class DemoConfig:
    """
    Optional demo-mode settings for reduced or synthetic runs.

    Used for testing and demonstration purposes with limited data scope.
    """
    include_dirs: str = "Documents"
    mode: bool = True
    max_files: int = 30
    file_extensions: List[str] = field(default_factory=list)


@dataclass
class TargetSystemConfig:
    """
    Configuration for the Linux target system.

    Specifies the desired Linux distribution, system settings, and user
    credentials for the target installation.
    """
    distro: Literal["linux-mint", "ubuntu"]
    edition: str
    language: str
    timezone: str
    hostname: str
    username: str
    auto_login: bool = False


@dataclass
class MigrationConfig:
    """
    Migration-related parameters (disk layout, mode, packages).

    Controls how the migration is executed, including which partition
    scheme to use, whether encryption is enabled, and which software
    should be installed.
    """
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
    """
    Runtime automation behaviour.

    Controls how the application handles automation, logging, checkpoints,
    and user confirmations during execution.
    """
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
    """
    Post-installation validation settings.

    Specifies which hardware and software capabilities to validate
    after the Linux system is installed.
    """
    check_network: bool = True
    check_audio: bool = True
    check_gpu: bool = True
    check_video_playback: bool = True
    check_office_suite: bool = True


@dataclass
class ResearchConfig:
    """
    Research-related logging and anonymisation settings.

    Controls metrics collection, machine ID anonymization, and
    summary report generation.
    """
    record_metrics: bool = True
    anonymize_machine_id: bool = True
    save_run_summary: str = "logs/run_summary.json"


@dataclass
class BackupConfig:
    """
    Backup-related settings.

    Controls backup compression and naming.
    """
    compress: bool = False
    archive_name: str = "backup.zip"


@dataclass
class AIConfig:
    """
    AI model and recommendation engine settings.

    Configuration for optional AI services, including model endpoint,
    credentials, and generation parameters.
    """
    enabled: bool = False
    endpoint: str = ""
    model: str = ""
    api_key: str = ""
    temperature: float = 0.2
    timeout_seconds: int = 10


@dataclass
class MigrationConfigRoot:
    """
    Top-level configuration object encapsulating all sections.

    This is the main configuration class that aggregates all subsections.
    Load via MigrationConfigRoot.load(path) or load_config(path).
    """
    project: ProjectConfig
    source_system: SourceSystemConfig
    target_system: TargetSystemConfig
    migration: MigrationConfig
    automation: AutomationConfig
    validation: ValidationConfig
    research: ResearchConfig
    app_demo: DemoConfig
    backup: BackupConfig
    ai: AIConfig

    @classmethod
    def load(cls, path: str) -> MigrationConfigRoot:
        """
        Load configuration from a YAML file.

        This is a convenience method that delegates to the loader module.

        Parameters
        ----------
        path : str
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
        # Import here to avoid circular imports
        from src.config.loader import load_config
        return load_config(path)
