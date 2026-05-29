"""Automation flow coordinator for Qt migration window."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from src.qt_ui.state import QtUiState


def _timed(fn: Callable, *args, **kwargs) -> tuple:
    """Call fn and return (result, elapsed_seconds)."""
    t0 = time.monotonic()
    result = fn(*args, **kwargs)
    return result, round(time.monotonic() - t0, 2)


class AutomationCoordinator:
    """Coordinate full-flow automation across windows and linux runtimes.

    Mode policy
    -----------
    guided   – inventory → local recommendations → backup  (no analysis, no expert steps)
    balanced – inventory → analysis → app + file recommendations → backup
    expert   – full pipeline including agent-ranked recommendations
    """

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
            return self._run_windows(
                ui_state=ui_state,
                run_inventory=run_inventory,
                run_analysis=run_analysis,
                run_app_recommendations=run_app_recommendations,
                run_file_recommendations=run_file_recommendations,
                run_backup=run_backup,
            )

        return self._run_linux(
            ui_state=ui_state,
            resolve_restore_bundle_dir=resolve_restore_bundle_dir,
            run_restore=run_restore,
            run_validation=run_validation,
            generate_final_report=generate_final_report,
        )

    # ------------------------------------------------------------------
    # Windows-side pipeline
    # ------------------------------------------------------------------

    def _run_windows(
        self,
        ui_state: QtUiState,
        run_inventory: Callable[[], dict],
        run_analysis: Callable[[], dict],
        run_app_recommendations: Callable[[], dict],
        run_file_recommendations: Callable[[], dict],
        run_backup: Callable[[], dict | None],
    ) -> dict:
        mode = ui_state.mode
        timing: dict[str, float] = {}
        result: dict = {"mode": "windows", "automation_mode": mode}

        # Step 1 – Inventory (all modes).
        inventory, t = _timed(run_inventory)
        ui_state.inventory_completed = True
        result["inventory"] = inventory
        timing["inventory_s"] = t

        # Step 2 – Analysis (balanced and expert only).
        if mode in {"balanced", "expert"}:
            analysis, t = _timed(run_analysis)
            ui_state.analysis_completed = True
            result["analysis"] = analysis
            timing["analysis_s"] = t

        # Step 3 – App recommendations (all modes; strategy differs per mode).
        app_recs, t = _timed(run_app_recommendations)
        result["app_recommendations"] = app_recs
        timing["app_recommendations_s"] = t

        # Step 4 – File recommendations (balanced and expert only).
        if mode in {"balanced", "expert"}:
            file_recs, t = _timed(run_file_recommendations)
            result["file_recommendations"] = file_recs
            timing["file_recommendations_s"] = t

        # Step 5 – Backup (all modes).
        backup, t = _timed(run_backup)
        ui_state.backup_completed = backup is not None
        result["backup"] = backup
        timing["backup_s"] = t

        result["timing"] = timing
        return result

    # ------------------------------------------------------------------
    # Linux-side pipeline (mode has no effect here – always full restore)
    # ------------------------------------------------------------------

    def _run_linux(
        self,
        ui_state: QtUiState,
        resolve_restore_bundle_dir: Callable[[], Path],
        run_restore: Callable[[Path], dict],
        run_validation: Callable[[], dict],
        generate_final_report: Callable[[], dict],
    ) -> dict:
        timing: dict[str, float] = {}

        bundle_dir = resolve_restore_bundle_dir()

        restore, t = _timed(run_restore, bundle_dir)
        ui_state.restore_completed = True
        timing["restore_s"] = t

        validation, t = _timed(run_validation)
        ui_state.verification_completed = True
        timing["validation_s"] = t

        report, t = _timed(generate_final_report)
        timing["report_s"] = t

        return {
            "mode": "linux",
            "restore": restore,
            "validation": validation,
            "report": report,
            "timing": timing,
        }
