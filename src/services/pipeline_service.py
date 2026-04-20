"""Orchestration service for the end-to-end migration pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config import MigrationConfigRoot
from src.services.migration_service import MigrationService
from src.services.report_service import ReportService
from src.services.restore_service import RestoreService
from src.services.validation_service import validate_restore_report


@dataclass
class WindowsPipelineResult:
    """Result bundle for the Windows-side inventory, analysis, and backup flow."""
    inventory: dict[str, Any]
    analysis: dict[str, Any]
    backup: dict[str, Any] | None


@dataclass
class LinuxPipelineResult:
    """Result bundle for the Linux-side restore and validation flow."""
    restore: dict[str, Any]
    validation: dict[str, Any]


@dataclass
class ReportPipelineResult:
    """Result bundle for the final report generation flow."""
    report: dict[str, Any]


class PipelineService:
    """Backend orchestrator for full migration pipelines."""

    def __init__(self, config: MigrationConfigRoot) -> None:
        """Create a pipeline service bound to a specific configuration."""
        self.config = config
        self.migration = MigrationService(config=config, context={})

    def run_windows_pre_migration(
        self,
        selected_folders: list[str] | None = None,
        selected_file_types: dict[str, bool] | None = None,
    ) -> WindowsPipelineResult:
        """Run the Windows-side inventory, analysis, and backup flow."""
        inventory = self.migration.run_inventory()
        analysis = self.migration.run_analysis(
            sw_inventory=inventory.get("software", {}),
            hw_inventory=inventory.get("hardware", {}),
        )

        folders = selected_folders or list(self.config.source_system.backup_paths)
        file_types = selected_file_types or dict(self.config.source_system.file_types)
        backup = self.migration.run_backup(folders, file_types)

        return WindowsPipelineResult(
            inventory=inventory,
            analysis=analysis,
            backup=backup,
        )

    def run_linux_post_migration(
        self,
        bundle_dir: Path,
        target_home: Path,
    ) -> LinuxPipelineResult:
        """Run the Linux-side restore and validation flow."""
        service = RestoreService(
            bundle_dir=bundle_dir,
            target_home=target_home,
            target_distro=self.config.target_system.distro,
        )
        service.run_restore()
        restore_summary = {
            "bundle_dir": str(bundle_dir),
            "target_home": str(target_home),
            "report_path": str(service.report_path),
        }
        validation_summary = validate_restore_report(service.report_path)

        return LinuxPipelineResult(
            restore=restore_summary,
            validation=validation_summary,
        )

    def generate_final_report(self) -> ReportPipelineResult:
        """Generate the final migration report bundle."""
        service = ReportService()
        report = service.generate_report()
        return ReportPipelineResult(report=report)
