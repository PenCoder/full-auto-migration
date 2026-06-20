"""Core migration service that executes inventory, analysis, and backup steps."""

from __future__ import annotations

import json
import os
import re
import shutil
import threading
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Any

from src.analysis.hw_matrix import generate_hardware_matrix, write_hardware_matrix
from src.analysis.software_mapping import generate_software_mapping, write_software_mapping
from src.backup.manifest import copy_backup_files, generate_manifest, write_manifest, create_backup_archive
from src.constants import BASE_DIR, DATA_DIR, RESTORE_DIR
from src.inventory.hardware import collect_hardware_inventory, write_hardware_inventory
from src.inventory.settings import collect_settings_inventory, write_settings_inventory
from src.inventory.software import collect_software_inventory, write_software_inventory
from src.inventory.shortcuts import collect_shortcuts_inventory, write_shortcuts_inventory
from src.loggers import get_logger
from src.orchestration.checkpoints import CheckpointManager
from src.orchestration.errors import ERR_BACKUP_FAILED, MigrationError
from src.services.icon_extractor import extract_icon_png

BUNDLE_ARCHIVE_NAME = "migration_bundle.zip"
LINUX_BUILD_BINARY = BASE_DIR / "assets" / "linux_build" / "MigrationWizard"


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

            self.logger.info("Collecting Desktop / Start Menu / Taskbar shortcuts...")
            shortcuts = collect_shortcuts_inventory(sw.get("entries", []))
            shortcuts_out = write_shortcuts_inventory(self.config, shortcuts)
            self.logger.info("Shortcuts inventory written to %s", shortcuts_out)

            self.checkpoints.mark_phase(
                "inventory_completed",
                hardware_output=str(hw_out),
                software_output=str(sw_out),
                settings_output=str(settings_out),
                shortcuts_output=str(shortcuts_out),
                scan_depth="deep" if deep_scan else "quick",
            )
            return {"hardware": hw, "software": sw, "settings": settings, "shortcuts": shortcuts}
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

    def run_backup(
        self,
        selected_folders,
        selected_file_types,
        logger=None,
        settings_inventory=None,
        settings_plan=None,
        shortcuts_inventory=None,
        app_recommendations=None,
        dry_run=False,
        cancel_event: threading.Event | None = None,
    ):
        """Create the backup manifest, copy selected files, and bundle settings and app data."""
        if logger is not None:
            self.logger = logger

        self.logger.info("Starting backup manifest generation%s...", " (dry run)" if dry_run else "")
        self.checkpoints.mark_phase("backup_started", selected_folders=selected_folders)

        try:
            self.config.source_system.backup_paths = selected_folders
            self.config.source_system.file_types = selected_file_types
            manifest = generate_manifest(self.config)

            if dry_run:
                self.logger.info(
                    "DRY RUN: %d files would be backed up. Skipping all disk writes.",
                    manifest.get("total_files", 0),
                )
                manifest["dry_run"] = True
                self.checkpoints.complete(manifest_entries=manifest.get("total_files", 0), archive_enabled=False)
                return manifest

            if cancel_event is not None and cancel_event.is_set():
                self.logger.info("Backup cancelled by user before file copy began.")
                self.checkpoints.mark_phase("backup_cancelled")
                manifest["cancelled"] = True
                return manifest

            out_file = write_manifest(self.config, manifest)
            self.logger.info("Backup manifest written to %s", out_file)
            completed = copy_backup_files(manifest, self.config, cancel_event=cancel_event)
            if not completed:
                self.logger.info("Backup cancelled by user during file copy.")
                self.checkpoints.mark_phase("backup_cancelled")
                manifest["cancelled"] = True
                return manifest

            # Bundle settings and app recommendations for the Linux restore side.
            self._bundle_settings(settings_inventory, settings_plan)
            self._bundle_shortcuts(shortcuts_inventory, settings_plan)
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

            bundle_archive_path = self._finalize_bundle_archive()
            manifest["bundle_archive_path"] = str(bundle_archive_path) if bundle_archive_path else ""

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

    def _bundle_shortcuts(self, shortcuts_inventory: dict | None, settings_plan: dict | None) -> None:
        """Write shortcuts_inventory.json into RESTORE_DIR unless the plan excludes it."""
        if not shortcuts_inventory or not shortcuts_inventory.get("entries"):
            return

        plan_items = {
            item.get("name"): item.get("action")
            for item in (settings_plan or {}).get("items", [])
            if isinstance(item, dict)
        }
        if plan_items.get("App Shortcuts") == "exclude":
            self.logger.info("App Shortcuts excluded by settings plan — skipping shortcuts bundle.")
            return

        RESTORE_DIR.mkdir(parents=True, exist_ok=True)
        shortcuts_path = RESTORE_DIR / "shortcuts_inventory.json"
        shortcuts_path.write_text(json.dumps(shortcuts_inventory, indent=2), encoding="utf-8")
        self.logger.info("Shortcuts inventory bundled at %s", shortcuts_path)

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

        icons_dir = RESTORE_DIR / "icons"
        seen: set[str] = set()
        installable: list[dict] = []
        for rec in recs:
            pkg = str(rec.get("linux_package", "")).strip()
            strategy = str(rec.get("migration_strategy", "")).lower()
            if not pkg or pkg in seen:
                continue
            seen.add(pkg)

            icon_path = ""
            icon_source = str(rec.get("icon_source", "")).strip()
            if icon_source:
                safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", pkg).strip("_") or "app"
                dest = icons_dir / f"{safe_name}.png"
                if extract_icon_png(icon_source, dest):
                    icon_path = f"icons/{dest.name}"

            installable.append({
                "windows_app": str(rec.get("windows_app", "")),
                "linux_package": pkg,
                "migration_strategy": strategy,
                "mapping_confidence": str(rec.get("mapping_confidence", "")),
                "category": str(rec.get("category", "")),
                "icon_path": icon_path,
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

    def _finalize_bundle_archive(self) -> Path | None:
        """Embed the pre-built Linux binary (if present) and zip the whole
        bundle folder into a single self-contained archive for export.

        Returns the path to the created archive, or None if RESTORE_DIR has
        nothing to bundle yet.
        """
        if not RESTORE_DIR.exists() or not any(RESTORE_DIR.iterdir()):
            return None

        if LINUX_BUILD_BINARY.exists():
            dest_binary = RESTORE_DIR / LINUX_BUILD_BINARY.name
            shutil.copy2(LINUX_BUILD_BINARY, dest_binary)
            try:
                os.chmod(dest_binary, 0o755)
            except OSError:
                pass
            self.logger.info("Embedded pre-built Linux binary into bundle at %s", dest_binary)

            readme_path = RESTORE_DIR / "RUN_ME.txt"
            readme_path.write_text(
                "Migration bundle — Linux restore\n"
                "=================================\n\n"
                "1. Unzip this archive if you haven't already.\n"
                "2. Run ./MigrationWizard (in a terminal: `./MigrationWizard`;\n"
                "   `chmod +x MigrationWizard` first if it's not executable).\n"
                "3. On the Restore page, click Browse and select this same folder.\n",
                encoding="utf-8",
            )

        archive_path = DATA_DIR / BUNDLE_ARCHIVE_NAME
        if archive_path.exists():
            archive_path.unlink()

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_path in RESTORE_DIR.rglob("*"):
                if not file_path.is_file():
                    continue
                rel = file_path.relative_to(RESTORE_DIR)
                # extracted_backup/ is local scratch space from a restore run
                # performed directly against this RESTORE_DIR — never bundle it.
                if rel.parts and rel.parts[0] == "extracted_backup":
                    continue
                zf.write(file_path, rel)

        self.logger.info("Migration bundle archived at %s", archive_path)
        return archive_path

    def run_task(self, worker_fn: Callable[[], Any], on_done: Callable[[Any], None]) -> None:
        """Run a worker function asynchronously and hand the result back on completion."""
        def _wrap():
            result = worker_fn()
            on_done(result)

        threading.Thread(target=_wrap, daemon=True).start()
