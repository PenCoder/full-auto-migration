"""Core migration service that executes inventory, analysis, and backup steps."""

from __future__ import annotations

import json
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Any

from src.analysis.hw_matrix import generate_hardware_matrix, write_hardware_matrix
from src.analysis.software_mapping import generate_software_mapping, write_software_mapping
from src.backup.manifest import copy_backup_files, generate_manifest, write_manifest, create_backup_archive
from src.constants import BASE_DIR, RESTORE_DIR
from src.inventory.hardware import collect_hardware_inventory, write_hardware_inventory
from src.inventory.settings import collect_settings_inventory, write_settings_inventory
from src.inventory.software import collect_software_inventory, write_software_inventory
from src.loggers import get_logger
from src.orchestration.checkpoints import CheckpointManager
from src.orchestration.errors import ERR_BACKUP_FAILED, MigrationError


class MigrationService:
    """Coordinate inventory, analysis, and backup operations for the app."""

    def __init__(self, config, context):
        """Bind the service to a configuration object and shared context."""
        self.config = config
        self.context = context
        self.logger = get_logger("migration_service")
        run_id = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")
        checkpoint_dir = Path(self.config.automation.checkpoint_dir)
        if not checkpoint_dir.is_absolute():
            checkpoint_dir = BASE_DIR / checkpoint_dir
        self.checkpoints = CheckpointManager(run_id=run_id, checkpoint_dir=checkpoint_dir)

    def run_inventory(self, logger=None, deep_scan: bool = False):
        """Collect hardware and software inventory and persist the outputs."""
        if logger is not None:
            self.logger = logger
        self.checkpoints.mark_phase("inventory_started")
        try:
            # SCAN HARDWARE INVENTORY
            self.logger.info("Starting hardware inventory scan...")
            hw = collect_hardware_inventory()
            self.logger.info("Hardware inventory scan completed.")

            self.logger.info("Writing hardware inventory to file...")
            hw_out = write_hardware_inventory(self.config, hw)
            self.logger.info("Hardware inventory written to %s", hw_out)

            # SCAN SOFTWARE INVENTORY
            self.logger.info("Starting software inventory scan...")
            sw = collect_software_inventory(deep_scan=deep_scan)
            self.logger.info("Software inventory scan completed.")

            self.logger.info("Writing software inventory to file...")
            sw_out = write_software_inventory(self.config, sw)
            self.logger.info("Software inventory written to %s", sw_out)

            self.logger.info("Collecting settings and desktop personalization inventory...")
            settings = collect_settings_inventory(export_assets=True)
            self.logger.info("Writing settings inventory to file...")
            settings_out = write_settings_inventory(self.config, settings)
            self.logger.info("Settings inventory written to %s", settings_out)

            self.checkpoints.mark_phase(
                "inventory_completed",
                hardware_output=str(hw_out),
                software_output=str(sw_out),
                settings_output=str(settings_out),
                scan_depth="deep" if deep_scan else "quick",
            )
            return {"hardware": hw, "software": sw, "settings": settings}
        except Exception as exc:
            self.checkpoints.mark_phase("inventory_failed", error=str(exc))
            raise

    def run_analysis(self, sw_inventory, hw_inventory, logger=None):
        """Generate hardware and software analysis outputs."""
        if logger is not None:
            self.logger = logger
        self.checkpoints.mark_phase("analysis_started")

        try:
            # Hardware analysis
            self.logger.info("Starting hardware compatibility analysis...")
            hw_rows = generate_hardware_matrix(self.config, hw_inventory)
            self.logger.info("Hardware compatibility analysis completed.")

            self.logger.info("Writing hardware compatibility matrix to file...")
            hw_out = write_hardware_matrix(self.config, hw_rows)
            self.logger.info("Hardware compatibility matrix written to %s", hw_out)

            # Software analysis
            self.logger.info("Starting software mapping analysis...")
            entries = sw_inventory.get("entries", [])
            sw_rows = generate_software_mapping(self.config, entries)
            self.logger.info("Software mapping analysis completed.")

            self.logger.info("Writing software mapping table to file...")
            sw_out = write_software_mapping(sw_rows)
            self.logger.info("Software mapping table written to %s", sw_out)
            self.checkpoints.mark_phase("analysis_completed", hardware_matrix=str(hw_out), software_mapping=str(sw_out))

            return {"hardware": hw_rows, "software": sw_rows}
        except Exception as exc:
            self.checkpoints.mark_phase("analysis_failed", error=str(exc))
            raise

    def run_backup(self, selected_folders, selected_file_types, logger=None, settings_inventory=None, settings_plan=None, app_recommendations=None):
        """Create the backup manifest, copy selected files, and bundle settings and app data."""
        if logger is not None:
            self.logger = logger

        self.logger.info("Starting backup manifest generation...")
        self.checkpoints.mark_phase("backup_started", selected_folders=selected_folders)

        try:
            self.config.source_system.backup_paths = selected_folders
            self.config.source_system.file_types = selected_file_types
            manifest = generate_manifest(self.config)

            out_file = write_manifest(self.config, manifest)
            self.logger.info("Backup manifest written to %s", out_file)
            copy_backup_files(manifest, self.config)

            # Bundle settings and app recommendations for the Linux restore side.
            self._bundle_settings(settings_inventory, settings_plan)
            self._bundle_apps(app_recommendations)

            if self.config.backup.compress:
                backup_root = self.config.source_system.backup_output_dir
                archive_path = self.config.backup.archive_name
                create_backup_archive(backup_root + "/files", archive_path)
                self.logger.info("Backup archive created at: %s", archive_path)
            else:
                # No zip — copy the staged files into RESTORE_DIR/files/ so the
                # bundle folder is self-contained and can be taken to Linux as-is.
                staged = DATA_DIR / self.config.source_system.backup_output_dir / "files"
                bundle_files = RESTORE_DIR / "files"
                if staged.exists():
                    if bundle_files.exists():
                        shutil.rmtree(bundle_files)
                    shutil.copytree(staged, bundle_files)
                    self.logger.info("Uncompressed files copied to bundle at %s", bundle_files)
            self.logger.info("Backup files copied successfully.")
            self.checkpoints.complete(manifest_entries=manifest.get("total_files", 0), archive_enabled=self.config.backup.compress)

            return manifest
        except Exception as exc:
            self.logger.exception("Backup command failed: %s", exc)
            self.checkpoints.mark_phase("backup_failed", error=str(exc))
            raise MigrationError(ERR_BACKUP_FAILED, str(exc)) from exc

    def _bundle_settings(self, settings_inventory: dict | None, settings_plan: dict | None) -> None:
        """Write settings inventory and plan JSON into RESTORE_DIR and copy exported assets."""
        RESTORE_DIR.mkdir(parents=True, exist_ok=True)

        if settings_inventory:
            inv_path = RESTORE_DIR / "settings_inventory.json"
            inv_path.write_text(json.dumps(settings_inventory, indent=2), encoding="utf-8")
            self.logger.info("Settings inventory bundled at %s", inv_path)

            # Copy exported wallpaper/theme assets alongside the manifest.
            exported = settings_inventory.get("exported_assets", {}) if isinstance(settings_inventory, dict) else {}
            assets_dst = RESTORE_DIR / "settings_assets"
            assets_dst.mkdir(parents=True, exist_ok=True)
            for label, src_path in exported.items():
                if src_path and Path(src_path).is_file():
                    dst = assets_dst / Path(src_path).name
                    shutil.copy2(src_path, dst)
                    self.logger.info("Settings asset '%s' copied to %s", label, dst)

        if settings_plan:
            plan_path = RESTORE_DIR / "settings_migration_plan.json"
            plan_path.write_text(json.dumps(settings_plan, indent=2), encoding="utf-8")
            self.logger.info("Settings migration plan bundled at %s", plan_path)

    def _bundle_apps(self, app_recommendations: dict | None) -> None:
        """Write apps_to_install.json into RESTORE_DIR so the Linux restore can install packages.

        Filters to only installable entries (migration_strategy == 'apt') and
        drops duplicates by linux_package name before writing.
        """
        if not app_recommendations:
            return

        recs = app_recommendations.get("recommendations", [])
        if not recs:
            return

        RESTORE_DIR.mkdir(parents=True, exist_ok=True)

        seen: set[str] = set()
        installable: list[dict] = []
        for rec in recs:
            pkg = str(rec.get("linux_package", "")).strip()
            strategy = str(rec.get("migration_strategy", "")).lower()
            if not pkg or pkg in seen:
                continue
            seen.add(pkg)
            installable.append({
                "windows_app": str(rec.get("windows_app", "")),
                "linux_package": pkg,
                "migration_strategy": strategy,
                "mapping_confidence": str(rec.get("mapping_confidence", "")),
                "category": str(rec.get("category", "")),
            })

        apps_path = RESTORE_DIR / "apps_to_install.json"
        apps_path.write_text(
            json.dumps({"applications": installable}, indent=2),
            encoding="utf-8",
        )
        self.logger.info(
            "App install list bundled: %d installable packages → %s",
            len(installable),
            apps_path,
        )

    def run_task(self, worker_fn: Callable[[], Any], on_done: Callable[[Any], None]) -> None:
        """Run a worker function asynchronously and hand the result back on completion."""
        def _wrap():
            result = worker_fn()
            on_done(result)

        threading.Thread(target=_wrap, daemon=True).start()
