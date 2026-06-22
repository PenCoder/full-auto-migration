"""Automation flow coordinator for Qt migration window."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

from src.orchestration.mode_policy import should_run_analysis, should_run_file_recommendations
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
        on_phase: Optional[Callable[[str], None]] = None,
        on_step_done: Optional[Callable[[str], None]] = None,
    ) -> dict:
        if runtime_mode == "windows":
            return self._run_windows(
                ui_state=ui_state,
                run_inventory=run_inventory,
                run_analysis=run_analysis,
                run_app_recommendations=run_app_recommendations,
                run_file_recommendations=run_file_recommendations,
                run_backup=run_backup,
                on_phase=on_phase,
                on_step_done=on_step_done,
            )

        return self._run_linux(
            ui_state=ui_state,
            resolve_restore_bundle_dir=resolve_restore_bundle_dir,
            run_restore=run_restore,
            run_validation=run_validation,
            generate_final_report=generate_final_report,
            on_phase=on_phase,
            on_step_done=on_step_done,
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
        on_phase: Optional[Callable[[str], None]] = None,
        on_step_done: Optional[Callable[[str], None]] = None,
    ) -> dict:
        def _phase(msg: str) -> None:
            if on_phase:
                on_phase(msg)

        def _done(step: str) -> None:
            if on_step_done:
                on_step_done(step)

        mode = ui_state.mode
        timing: dict[str, float] = {}
        result: dict = {"mode": "windows", "automation_mode": mode}

        # Step 1 – Inventory (all modes).
        _phase("Scanning Windows…")
        inventory, t = _timed(run_inventory)
        ui_state.inventory_completed = True
        result["inventory"] = inventory
        timing["inventory_s"] = t

        # Step 2 – Analysis (balanced and expert only).
        if should_run_analysis(mode):
            _phase("Analysing system…")
            analysis, t = _timed(run_analysis)
            ui_state.analysis_completed = True
            result["analysis"] = analysis
            timing["analysis_s"] = t

        _done("scan")  # Windows Scan step complete

        # Step 3 – App recommendations (all modes; strategy differs per mode).
        _phase("Finding app alternatives…")
        app_recs, t = _timed(run_app_recommendations)
        result["app_recommendations"] = app_recs
        timing["app_recommendations_s"] = t

        # Step 4 – File recommendations (balanced and expert only).
        if should_run_file_recommendations(mode):
            _phase("Selecting files…")
            file_recs, t = _timed(run_file_recommendations)
            result["file_recommendations"] = file_recs
            timing["file_recommendations_s"] = t

        # Data Selection and Review used defaults — mark both done.
        _done("data")
        _done("review")

        # Step 5 – Backup (all modes).
        _phase("Creating backup bundle…")
        backup, t = _timed(run_backup)
        ui_state.backup_completed = backup is not None
        result["backup"] = backup
        timing["backup_s"] = t

        _done("backup")
        _phase("Done")
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
        on_phase: Optional[Callable[[str], None]] = None,
        on_step_done: Optional[Callable[[str], None]] = None,
    ) -> dict:
        def _phase(msg: str) -> None:
            if on_phase:
                on_phase(msg)

        def _done(step: str) -> None:
            if on_step_done:
                on_step_done(step)

        timing: dict[str, float] = {}

        bundle_dir = resolve_restore_bundle_dir()

        _phase("Restoring files…")
        restore, t = _timed(run_restore, bundle_dir)
        ui_state.restore_completed = True
        timing["restore_s"] = t
        _done("restore")

        _phase("Verifying files…")
        validation, t = _timed(run_validation)
        ui_state.verification_completed = True
        timing["validation_s"] = t
        _done("verification")

        _phase("Generating report…")
        report, t = _timed(generate_final_report)
        timing["report_s"] = t
        _done("report")

        _phase("Done")
        return {
            "mode": "linux",
            "restore": restore,
            "validation": validation,
            "report": report,
            "timing": timing,
        }
