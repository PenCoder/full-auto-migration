"""Automation flow coordinator for Qt migration window."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from src.qt_ui.state import QtUiState


class AutomationCoordinator:
    """Coordinate full-flow automation across windows and linux runtimes."""

    def run(
        self,
        runtime_mode: str,
        ui_state: QtUiState,
        resolve_restore_bundle_dir: Callable[[], Path],
        run_inventory: Callable[[], dict],
        run_analysis: Callable[[], dict],
        run_app_recommendations: Callable[[], dict],
        run_file_recommendations: Callable[[], dict],
        run_backup: Callable[[], dict | None],
        run_restore: Callable[[Path], dict],
        run_validation: Callable[[], dict],
        generate_final_report: Callable[[], dict],
    ) -> dict:
        if runtime_mode == "windows":
            inventory = run_inventory()
            ui_state.inventory_completed = True

            analysis = run_analysis()
            ui_state.analysis_completed = True

            app_recs = run_app_recommendations()
            file_recs = run_file_recommendations()

            backup = run_backup()
            ui_state.backup_completed = backup is not None

            return {
                "mode": "windows",
                "inventory": inventory,
                "analysis": analysis,
                "app_recommendations": app_recs,
                "file_recommendations": file_recs,
                "backup": backup,
            }

        bundle_dir = resolve_restore_bundle_dir()
        restore = run_restore(bundle_dir)
        ui_state.restore_completed = True

        validation = run_validation()
        ui_state.verification_completed = True

        report = generate_final_report()

        return {
            "mode": "linux",
            "restore": restore,
            "validation": validation,
            "report": report,
        }
