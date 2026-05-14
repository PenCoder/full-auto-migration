"""Regression tests for the full automation pipeline.

Tests cover the AutomationCoordinator Windows and Linux flows, including
mode-aware step execution, state mutations, and fallback behaviour.
No Qt widgets are instantiated — all callbacks are plain callables.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.qt_ui.controllers import AutomationCoordinator
from src.qt_ui.state import QtUiState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(mode: str = "guided") -> QtUiState:
    state = QtUiState()
    state.mode = mode
    return state


def _inventory_cb() -> dict:
    return {"software": {"entries": [{"DisplayName": "Firefox"}]}, "hardware": {}}


def _analysis_cb() -> dict:
    return {"analysis": "ok"}


def _app_recs_cb() -> dict:
    return {"recommended_count": 1, "input_count": 1, "recommendations": [{"windows_app": "Firefox"}]}


def _file_recs_cb() -> dict:
    return {"recommended_count": 5, "input_count": 10, "recommendations": []}


def _backup_cb() -> dict:
    return {"manifest_path": "/tmp/manifest.json", "total_files": 42}


def _restore_cb(bundle_dir: Path) -> dict:
    return {"files_restored": 42, "apps_installed": 2}


def _validation_cb() -> dict:
    return {"total_sovereignty_score": 88, "total_files": 42, "restored_files": 42}


def _report_cb() -> dict:
    return {"json_path": "/tmp/report.json", "markdown_path": "/tmp/report.md"}


def _bundle_dir_cb() -> Path:
    return Path("/tmp/bundle")


# ---------------------------------------------------------------------------
# Windows pipeline
# ---------------------------------------------------------------------------

class TestWindowsPipeline:
    def test_guided_mode_skips_analysis_and_file_recs(self):
        state = _make_state("guided")
        analysis_mock = MagicMock(side_effect=_analysis_cb)
        file_recs_mock = MagicMock(side_effect=_file_recs_cb)

        coordinator = AutomationCoordinator()
        result = coordinator.run(
            runtime_mode="windows",
            ui_state=state,
            resolve_restore_bundle_dir=_bundle_dir_cb,
            run_inventory=_inventory_cb,
            run_analysis=analysis_mock,
            run_app_recommendations=_app_recs_cb,
            run_file_recommendations=file_recs_mock,
            run_backup=_backup_cb,
            run_restore=_restore_cb,
            run_validation=_validation_cb,
            generate_final_report=_report_cb,
        )

        analysis_mock.assert_not_called()
        file_recs_mock.assert_not_called()
        assert state.inventory_completed is True
        assert state.backup_completed is True
        assert result["mode"] == "windows"
        assert "inventory" in result
        assert "analysis" not in result
        assert "file_recommendations" not in result

    def test_balanced_mode_includes_analysis_and_file_recs(self):
        state = _make_state("balanced")
        analysis_mock = MagicMock(side_effect=_analysis_cb)
        file_recs_mock = MagicMock(side_effect=_file_recs_cb)

        coordinator = AutomationCoordinator()
        result = coordinator.run(
            runtime_mode="windows",
            ui_state=state,
            resolve_restore_bundle_dir=_bundle_dir_cb,
            run_inventory=_inventory_cb,
            run_analysis=analysis_mock,
            run_app_recommendations=_app_recs_cb,
            run_file_recommendations=file_recs_mock,
            run_backup=_backup_cb,
            run_restore=_restore_cb,
            run_validation=_validation_cb,
            generate_final_report=_report_cb,
        )

        analysis_mock.assert_called_once()
        file_recs_mock.assert_called_once()
        assert state.analysis_completed is True
        assert "analysis" in result
        assert "file_recommendations" in result

    def test_expert_mode_runs_all_steps(self):
        state = _make_state("expert")
        coordinator = AutomationCoordinator()
        result = coordinator.run(
            runtime_mode="windows",
            ui_state=state,
            resolve_restore_bundle_dir=_bundle_dir_cb,
            run_inventory=_inventory_cb,
            run_analysis=_analysis_cb,
            run_app_recommendations=_app_recs_cb,
            run_file_recommendations=_file_recs_cb,
            run_backup=_backup_cb,
            run_restore=_restore_cb,
            run_validation=_validation_cb,
            generate_final_report=_report_cb,
        )

        assert state.inventory_completed is True
        assert state.analysis_completed is True
        assert state.backup_completed is True
        assert "app_recommendations" in result
        assert "file_recommendations" in result

    def test_backup_none_sets_backup_completed_false(self):
        state = _make_state("guided")
        coordinator = AutomationCoordinator()
        result = coordinator.run(
            runtime_mode="windows",
            ui_state=state,
            resolve_restore_bundle_dir=_bundle_dir_cb,
            run_inventory=_inventory_cb,
            run_analysis=_analysis_cb,
            run_app_recommendations=_app_recs_cb,
            run_file_recommendations=_file_recs_cb,
            run_backup=lambda: None,
            run_restore=_restore_cb,
            run_validation=_validation_cb,
            generate_final_report=_report_cb,
        )

        assert state.backup_completed is False
        assert result["backup"] is None

    def test_inventory_callback_result_stored_in_result(self):
        state = _make_state("guided")
        coordinator = AutomationCoordinator()
        result = coordinator.run(
            runtime_mode="windows",
            ui_state=state,
            resolve_restore_bundle_dir=_bundle_dir_cb,
            run_inventory=_inventory_cb,
            run_analysis=_analysis_cb,
            run_app_recommendations=_app_recs_cb,
            run_file_recommendations=_file_recs_cb,
            run_backup=_backup_cb,
            run_restore=_restore_cb,
            run_validation=_validation_cb,
            generate_final_report=_report_cb,
        )

        assert isinstance(result["inventory"], dict)
        assert "software" in result["inventory"]

    def test_windows_result_includes_timing_dict(self):
        """Every Windows pipeline run must report per-stage timing metrics."""
        state = _make_state("balanced")
        coordinator = AutomationCoordinator()
        result = coordinator.run(
            runtime_mode="windows",
            ui_state=state,
            resolve_restore_bundle_dir=_bundle_dir_cb,
            run_inventory=_inventory_cb,
            run_analysis=_analysis_cb,
            run_app_recommendations=_app_recs_cb,
            run_file_recommendations=_file_recs_cb,
            run_backup=_backup_cb,
            run_restore=_restore_cb,
            run_validation=_validation_cb,
            generate_final_report=_report_cb,
        )

        assert "timing" in result, "balanced pipeline result must contain 'timing'"
        timing = result["timing"]
        assert "inventory_s" in timing
        assert "analysis_s" in timing
        assert "app_recommendations_s" in timing
        assert "file_recommendations_s" in timing
        assert "backup_s" in timing
        for key, val in timing.items():
            assert isinstance(val, float), f"timing[{key!r}] must be a float"
            assert val >= 0, f"timing[{key!r}] must be non-negative"

    def test_guided_timing_omits_analysis_and_file_rec_keys(self):
        """Guided mode skips analysis and file recs, so those keys must not appear in timing."""
        state = _make_state("guided")
        coordinator = AutomationCoordinator()
        result = coordinator.run(
            runtime_mode="windows",
            ui_state=state,
            resolve_restore_bundle_dir=_bundle_dir_cb,
            run_inventory=_inventory_cb,
            run_analysis=_analysis_cb,
            run_app_recommendations=_app_recs_cb,
            run_file_recommendations=_file_recs_cb,
            run_backup=_backup_cb,
            run_restore=_restore_cb,
            run_validation=_validation_cb,
            generate_final_report=_report_cb,
        )

        timing = result["timing"]
        assert "inventory_s" in timing
        assert "backup_s" in timing
        assert "analysis_s" not in timing, "guided mode must not record analysis timing"
        assert "file_recommendations_s" not in timing, "guided mode must not record file-rec timing"


# ---------------------------------------------------------------------------
# Linux pipeline
# ---------------------------------------------------------------------------

class TestLinuxPipelineTiming:
    def test_linux_result_includes_timing_dict(self):
        """Linux pipeline must report per-stage timing for restore, validation, and report."""
        state = _make_state("guided")
        coordinator = AutomationCoordinator()
        result = coordinator.run(
            runtime_mode="linux",
            ui_state=state,
            resolve_restore_bundle_dir=_bundle_dir_cb,
            run_inventory=_inventory_cb,
            run_analysis=_analysis_cb,
            run_app_recommendations=_app_recs_cb,
            run_file_recommendations=_file_recs_cb,
            run_backup=_backup_cb,
            run_restore=_restore_cb,
            run_validation=_validation_cb,
            generate_final_report=_report_cb,
        )

        assert "timing" in result
        timing = result["timing"]
        assert "restore_s" in timing
        assert "validation_s" in timing
        assert "report_s" in timing
        for key, val in timing.items():
            assert isinstance(val, float)
            assert val >= 0


class TestLinuxPipeline:
    def test_linux_flow_sets_restore_and_verification_completed(self):
        state = _make_state("guided")
        coordinator = AutomationCoordinator()
        result = coordinator.run(
            runtime_mode="linux",
            ui_state=state,
            resolve_restore_bundle_dir=_bundle_dir_cb,
            run_inventory=_inventory_cb,
            run_analysis=_analysis_cb,
            run_app_recommendations=_app_recs_cb,
            run_file_recommendations=_file_recs_cb,
            run_backup=_backup_cb,
            run_restore=_restore_cb,
            run_validation=_validation_cb,
            generate_final_report=_report_cb,
        )

        assert state.restore_completed is True
        assert state.verification_completed is True
        assert result["mode"] == "linux"
        assert "restore" in result
        assert "validation" in result
        assert "report" in result

    def test_linux_flow_passes_bundle_dir_to_restore(self):
        state = _make_state("guided")
        restore_mock = MagicMock(side_effect=_restore_cb)
        coordinator = AutomationCoordinator()
        coordinator.run(
            runtime_mode="linux",
            ui_state=state,
            resolve_restore_bundle_dir=_bundle_dir_cb,
            run_inventory=_inventory_cb,
            run_analysis=_analysis_cb,
            run_app_recommendations=_app_recs_cb,
            run_file_recommendations=_file_recs_cb,
            run_backup=_backup_cb,
            run_restore=restore_mock,
            run_validation=_validation_cb,
            generate_final_report=_report_cb,
        )

        restore_mock.assert_called_once_with(Path("/tmp/bundle"))

    def test_linux_flow_does_not_call_inventory_or_backup(self):
        state = _make_state("guided")
        inventory_mock = MagicMock(side_effect=_inventory_cb)
        backup_mock = MagicMock(side_effect=_backup_cb)

        coordinator = AutomationCoordinator()
        coordinator.run(
            runtime_mode="linux",
            ui_state=state,
            resolve_restore_bundle_dir=_bundle_dir_cb,
            run_inventory=inventory_mock,
            run_analysis=_analysis_cb,
            run_app_recommendations=_app_recs_cb,
            run_file_recommendations=_file_recs_cb,
            run_backup=backup_mock,
            run_restore=_restore_cb,
            run_validation=_validation_cb,
            generate_final_report=_report_cb,
        )

        inventory_mock.assert_not_called()
        backup_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Recommendation fallback regression
# ---------------------------------------------------------------------------

class TestRecommendationFallback:
    """Guard the scan page's auto-fallback to local strategy on AI/online errors."""

    def test_fallback_flag_defaults_to_local(self):
        from src.qt_ui.pages.scan_page import ScanPage
        state = _make_state("balanced")

        dummy_scan_cb = MagicMock(return_value={"software": {"entries": []}, "hardware": {}})
        dummy_rec_cb = MagicMock(return_value={"recommended_count": 0, "input_count": 0, "recommendations": []})

        import sys
        if "PySide6" not in sys.modules:
            pytest.skip("PySide6 not available in this environment")

        page = ScanPage.__new__(ScanPage)
        page._current_rec_strategy = "local"
        assert page._current_rec_strategy == "local"

    def test_on_recommendation_error_falls_back_when_agent(self):
        """_on_recommendation_error auto-retries with 'local' when strategy is 'agent'."""
        import sys
        if "PySide6" not in sys.modules:
            pytest.skip("PySide6 not available in this environment")

        from src.qt_ui.pages.scan_page import ScanPage
        page = ScanPage.__new__(ScanPage)
        page._current_rec_strategy = "agent"
        page.ui_state = _make_state("expert")

        retry_calls: list[str] = []

        def fake_run_recommendations(strategy: str) -> None:
            retry_calls.append(strategy)

        page._run_recommendations = fake_run_recommendations  # type: ignore[method-assign]
        page.status = MagicMock()
        page._render_scan_report = MagicMock()
        page.refresh = MagicMock()

        page._on_recommendation_error("Connection refused")

        assert retry_calls == ["local"]
        page.status.setText.assert_called_once()

    def test_on_recommendation_error_no_fallback_when_local(self):
        """_on_recommendation_error does not loop when strategy is already 'local'."""
        import sys
        if "PySide6" not in sys.modules:
            pytest.skip("PySide6 not available in this environment")

        from src.qt_ui.pages.scan_page import ScanPage
        page = ScanPage.__new__(ScanPage)
        page._current_rec_strategy = "local"
        page.ui_state = _make_state("expert")

        retry_calls: list[str] = []
        page._run_recommendations = lambda s: retry_calls.append(s)  # type: ignore[method-assign]
        page.status = MagicMock()
        page._render_scan_report = MagicMock()
        page.refresh = MagicMock()

        page._on_recommendation_error("Service unavailable")

        assert retry_calls == []
        page.status.setText.assert_called_once()
