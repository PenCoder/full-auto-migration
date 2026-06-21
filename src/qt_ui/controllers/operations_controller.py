"""Runtime operations controller for Qt migration workflows."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path

from src.constants import RESTORE_REPORT
from src.services.restore_service import RestoreService
from src.services.validation_service import validate_restore_report


class OperationsController:
    """Execute migration operations while keeping UI window thin."""

    @staticmethod
    def collect_usage_recommendations(
        *,
        selected_folders: list[str],
        file_type_catalog: dict[str, bool],
        max_files: int = 8000,
    ) -> list[dict[str, object]]:
        """Collect extension usage recommendations from local filesystem activity."""
        if not file_type_catalog:
            return []

        now_ts = datetime.now(timezone.utc).timestamp()
        extensions = {str(ext).lower() for ext in file_type_catalog.keys()}
        stats = {
            ext: {"count": 0, "recent_30_days": 0, "score": 0.0}
            for ext in extensions
        }

        scanned = 0
        for raw_path in selected_folders:
            expanded = Path(raw_path.replace("~", str(Path.home()))).expanduser()
            if not expanded.exists() or not expanded.is_dir():
                continue

            for root, _, files in os.walk(expanded):
                for name in files:
                    if scanned >= max_files:
                        break
                    ext = Path(name).suffix.lower()
                    if ext not in stats:
                        continue
                    full_path = Path(root) / name
                    try:
                        st = full_path.stat()
                    except OSError:
                        continue

                    scanned += 1
                    days_ago = (now_ts - float(st.st_atime)) / 86400.0
                    entry = stats[ext]
                    entry["count"] += 1
                    if days_ago <= 30:
                        entry["recent_30_days"] += 1
                        entry["score"] += 2.0
                    else:
                        entry["score"] += 1.0
                if scanned >= max_files:
                    break

        total_score = sum(float(item["score"]) for item in stats.values())
        if total_score <= 0:
            return []

        recommendations: list[dict[str, object]] = []
        for ext in sorted(stats.keys()):
            item = stats[ext]
            if int(item["count"]) == 0:
                continue
            usage_percent = round((float(item["score"]) / total_score) * 100.0, 2)
            recommendations.append(
                {
                    "extension": ext,
                    "count": int(item["count"]),
                    "recent_30_days": int(item["recent_30_days"]),
                    "usage_percent": usage_percent,
                    "recommended": usage_percent >= 3.0,
                }
            )

        recommendations.sort(
            key=lambda row: (float(row.get("usage_percent", 0.0)), int(row.get("count", 0))),
            reverse=True,
        )
        return recommendations

    @staticmethod
    def resolve_selected_folders(ui_state, config) -> list[str]:
        custom = [p for p in ui_state.custom_paths if p]
        if ui_state.data_strategy == "keep_all":
            combined = list(config.source_system.backup_paths) + custom
            return list(dict.fromkeys(combined))

        selected = [
            f"~/{name}"
            for name, enabled in ui_state.selected_folders.items()
            if enabled
        ]
        selected.extend(custom)
        if selected:
            return list(dict.fromkeys(selected))
        combined = list(config.source_system.backup_paths) + custom
        return list(dict.fromkeys(combined))

    @staticmethod
    def get_repology_config(config) -> dict:
        cfg = getattr(config, "repology", None) or getattr(config, "ai", None)
        return {
            "software_online_lookup_enabled": getattr(cfg, "enabled", True),
            "software_online_provider": getattr(cfg, "provider", "repology"),
            "software_online_send_fields": list(getattr(cfg, "send_fields", ["name", "version", "publisher"])),
            "redact_user_paths": getattr(cfg, "redact_user_paths", True),
        }

    # Backward-compatible alias.
    get_ai_config = get_repology_config

    def run_inventory(
        self,
        *,
        runtime_mode: str,
        migration_service,
        runtime_data: dict[str, object],
        log_activity,
        mark_action_done,
        clear_error_banner,
        deep_scan: bool = False,
    ) -> dict:
        if runtime_mode != "windows":
            raise RuntimeError("Inventory is only available in Windows pre-migration mode.")
        clear_error_banner()
        scan_label = "deep" if deep_scan else "quick"
        log_activity("inventory", f"Starting {scan_label} hardware and software inventory scan...")
        result = migration_service.run_inventory(deep_scan=deep_scan)
        runtime_data["inventory"] = result
        sw_entries = len(result.get("software", {}).get("entries", []))
        hw_keys = len(result.get("hardware", {}).keys())
        if deep_scan:
            deep_summary = result.get("software", {}).get("deep_scan_summary", {})
            log_activity(
                "inventory",
                "Deep inventory completed: "
                f"hardware={hw_keys}, registry_apps={sw_entries}, "
                f"pkg_mgr={deep_summary.get('package_manager_entries', 0)}, "
                f"appx={deep_summary.get('appx_entries', 0)}.",
                level="success",
            )
        else:
            log_activity(
                "inventory",
                f"Inventory completed: {hw_keys} hardware categories, {sw_entries} software entries.",
                level="success",
            )
        mark_action_done("inventory")
        return result

    def run_analysis(
        self,
        *,
        runtime_mode: str,
        migration_service,
        runtime_data: dict[str, object],
        log_activity,
        mark_action_done,
        clear_error_banner,
        run_inventory,
    ) -> dict:
        if runtime_mode != "windows":
            raise RuntimeError("Analysis is only available in Windows pre-migration mode.")
        clear_error_banner()
        log_activity("analysis", "Generating compatibility matrix and software mapping...")
        inv = runtime_data.get("inventory")
        if not inv:
            inv = run_inventory()
        result = migration_service.run_analysis(
            sw_inventory=inv.get("software", {}),
            hw_inventory=inv.get("hardware", {}),
        )
        runtime_data["analysis"] = result
        mapped = len(result.get("software", []))
        hw_rows = len(result.get("hardware", []))
        log_activity(
            "analysis",
            f"Analysis completed: {hw_rows} hardware advisories, {mapped} software mapping rows.",
            level="success",
        )
        mark_action_done("analysis")
        return result

    def generate_software_recommendations(
        self,
        *,
        runtime_mode: str,
        ui_state,
        ai_config: dict,
        recommendation_service,
        runtime_data: dict[str, object],
        log_activity,
        run_inventory,
        strategy: str = "local",
        selection_profile: str = "migrate_all",
    ) -> dict:
        if runtime_mode != "windows":
            raise RuntimeError("Software recommendations are available in Windows pre-migration mode only.")
        if ui_state.mode != "expert":
            raise RuntimeError("Switch to expert mode to generate advanced software recommendations.")

        inventory = runtime_data.get("inventory")
        if not inventory:
            inventory = run_inventory(deep_scan=False)

        software_inventory = inventory.get("software", {}) if isinstance(inventory, dict) else {}
        effective_profile = selection_profile or ui_state.recommendation_strategy
        log_activity("analysis", f"Generating {strategy} software recommendations ({effective_profile})...")
        result = recommendation_service.generate_recommendations(
            software_inventory=software_inventory,
            strategy=strategy,
            selection_profile=effective_profile,
            repology_config=ai_config,
        )
        runtime_data[f"recommendations_{strategy}_{effective_profile}"] = result
        log_activity(
            "analysis",
            f"{strategy.capitalize()} ({effective_profile}) recommendation report created: {result.get('markdown_path', '')}",
            level="success",
        )
        return result

    def run_app_recommendations(
        self,
        *,
        runtime_mode: str,
        ui_state,
        ai_config: dict,
        recommendation_service,
        runtime_data: dict[str, object],
        log_activity,
        run_inventory,
    ) -> dict:
        if runtime_mode != "windows":
            raise RuntimeError("App recommendations are only available in Windows pre-migration mode.")

        inventory = runtime_data.get("inventory")
        if not inventory:
            inventory = run_inventory(deep_scan=False)

        software_inventory = inventory.get("software", {}) if isinstance(inventory, dict) else {}
        strategy = "online" if ui_state.mode == "expert" else "local"
        selection_profile = ui_state.recommendation_strategy

        log_activity("recommendations", f"Generating {strategy} app recommendations ({selection_profile})...")
        result = recommendation_service.generate_recommendations(
            software_inventory=software_inventory,
            strategy=strategy,
            selection_profile=selection_profile,
            repology_config=ai_config,
        )
        runtime_data["review_app_recommendations"] = result
        log_activity(
            "recommendations",
            f"App recommendations ready: {result.get('recommended_count', 0)} apps",
            level="success",
        )
        return result

    def run_file_recommendations(
        self,
        *,
        runtime_mode: str,
        config,
        ui_state,
        file_recommendation_service,
        runtime_data: dict[str, object],
        log_activity,
        ai_config: dict,
    ) -> dict:
        if runtime_mode != "windows":
            raise RuntimeError("File recommendations are only available in Windows pre-migration mode.")

        choice_mode = ui_state.data_choice_mode
        log_activity("recommendations", f"Generating file recommendations ({choice_mode})...")

        catalog = dict(ui_state.selected_file_types or config.source_system.file_types)
        selected_folders = self.resolve_selected_folders(ui_state, config)
        usage_recs = self.collect_usage_recommendations(
            selected_folders=selected_folders,
            file_type_catalog=catalog,
        )
        ui_state.usage_recommendations = usage_recs

        file_inventory = {
            "files": [
                {
                    "path": f"usage:{item.get('extension', '')}",
                    "size": int(item.get("count", 0)) * 1024,
                    "last_accessed_days_ago": 0 if int(item.get("recent_30_days", 0)) > 0 else 60,
                }
                for item in usage_recs
            ]
        }

        result = file_recommendation_service.generate_recommendations(
            file_inventory=file_inventory,
            choice_mode=choice_mode,
            selected_file_types=catalog,
        )
        runtime_data["review_file_recommendations"] = result
        log_activity(
            "recommendations",
            f"File recommendations ready: {result.get('recommended_count', 0)} files",
            level="success",
        )
        return result

    def run_backup(
        self,
        *,
        runtime_mode: str,
        migration_service,
        config,
        ui_state,
        runtime_data: dict[str, object],
        log_activity,
        mark_action_done,
        clear_error_banner,
        selected_folders: list[str],
        cancel_event=None,
    ) -> dict | None:
        if runtime_mode != "windows":
            raise RuntimeError("Backup is only available in Windows pre-migration mode.")
        clear_error_banner()
        default_types = dict(config.source_system.file_types)
        if ui_state.data_choice_mode == "manual":
            selected_file_types = {ext: False for ext in default_types.keys()}
        elif ui_state.data_choice_mode == "all_files":
            selected_file_types = {ext: True for ext in default_types.keys()}
        elif ui_state.data_choice_mode == "selected_types":
            selected_file_types = dict(ui_state.selected_file_types or default_types)
        elif ui_state.data_choice_mode == "ai_recommended":
            selected_file_types = {ext: False for ext in default_types.keys()}
            usage_map = {
                str(item.get("extension", "")).lower(): bool(item.get("recommended", False))
                for item in ui_state.usage_recommendations
                if isinstance(item, dict)
            }
            for ext in selected_file_types.keys():
                selected_file_types[ext] = bool(usage_map.get(str(ext).lower(), default_types.get(ext, False)))
        else:
            selected_file_types = default_types

        config.source_system.file_types = selected_file_types
        dry_run = bool(ui_state.advanced_operations.get("dry_run", False))
        log_activity(
            "backup",
            f"{'[DRY RUN] Simulating' if dry_run else 'Creating'} bundle"
            f" from {len(selected_folders)} folder scope(s) and selected file filters...",
        )
        # Pull app recommendations from runtime_data — prefer the review-page result,
        # fall back to any earlier scan-page result.
        app_recommendations = (
            runtime_data.get("review_app_recommendations")
            or next(
                (v for k, v in runtime_data.items() if k.startswith("recommendations_") and isinstance(v, dict)),
                None,
            )
        )

        result = migration_service.run_backup(
            selected_folders,
            selected_file_types,
            settings_inventory=ui_state.settings_inventory or None,
            settings_plan=ui_state.settings_migration_plan or None,
            shortcuts_inventory=ui_state.shortcuts_inventory or None,
            app_recommendations=app_recommendations,
            dry_run=dry_run,
            cancel_event=cancel_event,
        )
        runtime_data["backup"] = result
        files = int(result.get("total_files", 0)) if isinstance(result, dict) else 0
        if isinstance(result, dict) and result.get("cancelled"):
            log_activity("backup", "Backup cancelled by user.", level="warning")
            return result
        if dry_run:
            log_activity(
                "backup",
                f"Dry run complete — {files} files would be backed up. No data written to disk.",
                level="success",
            )
        else:
            log_activity(
                "backup",
                f"Backup bundle completed. Manifest entries: {files}.",
                level="success",
            )
        mark_action_done("backup")
        return result

    def run_restore(
        self,
        *,
        runtime_mode: str,
        config,
        runtime_data: dict[str, object],
        ui_state,
        log_activity,
        mark_action_done,
        clear_error_banner,
        bundle_dir: Path,
    ) -> dict:
        if runtime_mode != "linux":
            raise RuntimeError("Restore is only available in Linux migration mode.")
        clear_error_banner()
        log_activity("restore", f"Starting restore from bundle: {bundle_dir}")

        last_progress = {"value": -10}

        def progress_cb(percent: int, msg: str) -> None:
            if percent == 100 or percent - last_progress["value"] >= 10:
                last_progress["value"] = percent
                log_activity("restore", f"{msg} ({percent}%)")

        target_home = Path.home() / "Restored_Migration"
        service = RestoreService(
            bundle_dir=bundle_dir,
            target_home=target_home,
            progress_cb=progress_cb,
            target_distro=config.target_system.distro,
        )
        service.run_restore()
        runtime_data["restore"] = {
            "target_home": str(target_home),
            "bundle_dir": str(bundle_dir),
            "report_path": str(service.report_path),
            "warnings": service.warnings,
        }
        ui_state.restore_completed = True
        log_activity("restore", f"Restore completed. Report written to {service.report_path}", level="success")
        mark_action_done("restore")
        return runtime_data["restore"]

    def reset_restore(
        self,
        *,
        config,
        ui_state,
        log_activity,
        clear_error_banner,
        uninstall_apps: bool = False,
    ) -> dict:
        """Undo a previous restore: files, shortcuts, the wallpaper file we wrote,
        and (only if uninstall_apps) the apps this tool itself installed.
        """
        clear_error_banner()
        log_activity("restore", f"Resetting previous restore (uninstall_apps={uninstall_apps})...")

        last_progress = {"value": -10}

        def progress_cb(percent: int, msg: str) -> None:
            if percent == 100 or percent - last_progress["value"] >= 10:
                last_progress["value"] = percent
                log_activity("restore", f"{msg} ({percent}%)")

        service = RestoreService(target_distro=config.target_system.distro, progress_cb=progress_cb)
        result = service.undo_restore(uninstall_apps=uninstall_apps)

        ui_state.restore_completed = False
        ui_state.verification_completed = False
        ui_state.total_sovereignty_score = 0
        log_activity(
            "restore",
            f"Reset complete: {result['files_removed']} file(s) removed, "
            f"{result['shortcuts_removed']} shortcut(s) removed, "
            f"{len(result['apps_removed'])} app(s) uninstalled.",
            level="success",
        )
        return result

    def run_validation(
        self,
        *,
        runtime_data: dict[str, object],
        ui_state,
        log_activity,
        mark_action_done,
        clear_error_banner,
    ) -> dict:
        clear_error_banner()
        log_activity("validation", "Running integrity and sovereignty validation checks...")
        summary = validate_restore_report(RESTORE_REPORT)
        runtime_data["verification"] = summary
        ui_state.verification_completed = True
        log_activity(
            "validation",
            f"Validation complete. Score={summary.get('total_sovereignty_score', 0)}%, files={summary.get('total_files', 0)}.",
            level="success",
        )
        mark_action_done("validation")
        return summary

    def generate_final_report(
        self,
        *,
        runtime_data: dict[str, object],
        report_service,
        log_activity,
        mark_action_done,
        clear_error_banner,
        activity_log: list | None = None,
    ) -> dict:
        clear_error_banner()
        log_activity("report", "Compiling final report artifacts (JSON, Markdown, HTML)...")
        result = report_service.generate_report(activity_log=activity_log or [])
        runtime_data["report"] = result.get("report", {})
        log_activity(
            "report",
            f"Report completed: {result.get('markdown_path', '')}",
            level="success",
        )
        mark_action_done("report")
        return result
