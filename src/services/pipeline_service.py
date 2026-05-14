"""Orchestration service for the end-to-end migration pipelines."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
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
    timing: dict[str, float] = field(default_factory=dict)


@dataclass
class LinuxPipelineResult:
    """Result bundle for the Linux-side restore and validation flow."""
    restore: dict[str, Any]
    validation: dict[str, Any]
    timing: dict[str, float] = field(default_factory=dict)


@dataclass
class ReportPipelineResult:
    """Result bundle for the final report generation flow."""
    report: dict[str, Any]
    timing: dict[str, float] = field(default_factory=dict)


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
        timing: dict[str, float] = {}

        t0 = time.monotonic()
        inventory = self.migration.run_inventory()
        timing["inventory_s"] = round(time.monotonic() - t0, 2)

        t0 = time.monotonic()
        analysis = self.migration.run_analysis(
            sw_inventory=inventory.get("software", {}),
            hw_inventory=inventory.get("hardware", {}),
        )
        timing["analysis_s"] = round(time.monotonic() - t0, 2)

        folders = selected_folders or list(self.config.source_system.backup_paths)
        file_types = selected_file_types or dict(self.config.source_system.file_types)
        t0 = time.monotonic()
        backup = self.migration.run_backup(folders, file_types)
        timing["backup_s"] = round(time.monotonic() - t0, 2)

        return WindowsPipelineResult(
            inventory=inventory,
            analysis=analysis,
            backup=backup,
            timing=timing,
        )

    def run_linux_post_migration(
        self,
        bundle_dir: Path,
        target_home: Path,
    ) -> LinuxPipelineResult:
        """Run the Linux-side restore and validation flow."""
        timing: dict[str, float] = {}

        service = RestoreService(
            bundle_dir=bundle_dir,
            target_home=target_home,
            target_distro=self.config.target_system.distro,
        )
        t0 = time.monotonic()
        service.run_restore()
        timing["restore_s"] = round(time.monotonic() - t0, 2)

        restore_summary = {
            "bundle_dir": str(bundle_dir),
            "target_home": str(target_home),
            "report_path": str(service.report_path),
        }

        t0 = time.monotonic()
        validation_summary = validate_restore_report(service.report_path)
        timing["validation_s"] = round(time.monotonic() - t0, 2)

        return LinuxPipelineResult(
            restore=restore_summary,
            validation=validation_summary,
            timing=timing,
        )

    def generate_final_report(self) -> ReportPipelineResult:
        """Generate the final migration report bundle."""
        t0 = time.monotonic()
        service = ReportService()
        report = service.generate_report()
        return ReportPipelineResult(
            report=report,
            timing={"report_s": round(time.monotonic() - t0, 2)},
        )
