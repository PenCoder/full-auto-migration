"""Core migration service that executes inventory, analysis, and backup steps."""

from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Any

from src.analysis.hw_matrix import generate_hardware_matrix, write_hardware_matrix
from src.analysis.software_mapping import generate_software_mapping, write_software_mapping
from src.backup.manifest import copy_backup_files, generate_manifest, write_manifest, create_backup_archive
from src.constants import BASE_DIR
from src.inventory.hardware import collect_hardware_inventory, write_hardware_inventory
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
        run_id = datetime.utcnow().strftime("run_%Y%m%d_%H%M%S")
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

            self.checkpoints.mark_phase(
                "inventory_completed",
                hardware_output=str(hw_out),
                software_output=str(sw_out),
                scan_depth="deep" if deep_scan else "quick",
            )
            return {"hardware": hw, "software": sw}
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

    def run_backup(self, selected_folders, selected_file_types, logger=None):
        """Create the backup manifest and copy the selected files."""
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
            if self.config.backup.compress:
                backup_root = self.config.source_system.backup_output_dir
                archive_path = self.config.backup.archive_name
                create_backup_archive(backup_root + "/files", archive_path)
                self.logger.info("Backup archive created at: %s", archive_path)
            self.logger.info("Backup files copied successfully.")
            self.checkpoints.complete(manifest_entries=manifest.get("total_files", 0), archive_enabled=self.config.backup.compress)

            return manifest
        except Exception as exc:
            self.logger.exception("Backup command failed: %s", exc)
            self.checkpoints.mark_phase("backup_failed", error=str(exc))
            raise MigrationError(ERR_BACKUP_FAILED, str(exc)) from exc

    def run_task(self, worker_fn: Callable[[], Any], on_done: Callable[[Any], None]) -> None:
        """Run a worker function asynchronously and hand the result back on completion."""
        def _wrap():
            result = worker_fn()
            on_done(result)

        threading.Thread(target=_wrap, daemon=True).start()
