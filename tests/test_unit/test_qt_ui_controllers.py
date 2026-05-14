"""Unit tests for extracted Qt UI controllers."""

from pathlib import Path

import pytest

from src.qt_ui.controllers import (
    ActivityLogController,
    AutomationCoordinator,
    NavigationController,
    ModeController,
    OperationsController,
)
from src.qt_ui.controllers import operations_controller as operations_module
from src.qt_ui.state import QtUiState


class _DummyPage:
    def __init__(self):
        self.refreshed = 0

    def refresh(self):
        self.refreshed += 1


class _DummyStack:
    def __init__(self, count=3):
        self._pages = [_DummyPage() for _ in range(count)]
        self._idx = 0

    def count(self):
        return len(self._pages)

    def currentIndex(self):
        return self._idx

    def setCurrentIndex(self, idx):
        self._idx = idx

    def currentWidget(self):
        return self._pages[self._idx]

    def widget(self, i):
        return self._pages[i]


class _DummyButton:
    def __init__(self):
        self.enabled = None
        self.text = ""

    def setEnabled(self, v):
        self.enabled = v

    def setText(self, v):
        self.text = v


class _DummyStepper:
    def __init__(self):
        self.active = None

    def set_active_index(self, i):
        self.active = i


class _DummyDock:
    def __init__(self):
        self.visible = False

    def isVisible(self):
        return self.visible

    def show(self):
        self.visible = True

    def hide(self):
        self.visible = False


class _DummyPanel:
    def __init__(self):
        self.last_mode = None

    def apply_mode(self, mode):
        self.last_mode = mode


class _DummyConfig:
    class _Src:
        backup_paths = ["Documents", "Desktop"]
        file_types = {".txt": True}

    class _AI:
        enabled = False
        endpoint = ""
        model = ""
        api_key = ""
        temperature = 0.2
        timeout_seconds = 10

    class _Target:
        distro = "ubuntu"

    source_system = _Src()
    ai = _AI()
    target_system = _Target()


class _DummyMigrationService:
    def run_inventory(self, deep_scan=False):
        if deep_scan:
            return {
                "software": {
                    "entries": ["a", "b"],
                    "deep_scan_summary": {"package_manager_entries": 1, "appx_entries": 1},
                },
                "hardware": {"cpu": "ok", "ram": "ok"},
            }
        return {
            "software": {"entries": ["a"]},
            "hardware": {"cpu": "ok"},
        }

    def run_analysis(self, sw_inventory, hw_inventory):
        return {
            "software": list(sw_inventory.get("entries", [])),
            "hardware": list(hw_inventory.keys()),
        }

    def run_backup(self, selected_folders, selected_file_types, **kwargs):
        return {
            "total_files": len(selected_folders) + len(selected_file_types),
        }


class _DummyRecommendationService:
    def generate_recommendations(self, software_inventory, strategy, selection_profile):
        return {
            "recommended_count": len(software_inventory.get("entries", [])),
            "markdown_path": f"{strategy}_{selection_profile}.md",
        }


class _DummyFileRecommendationService:
    def generate_recommendations(self, file_inventory, choice_mode, use_ai, ai_config, selected_file_types=None):
        return {
            "recommended_count": len(file_inventory.get("files", [])),
            "mode": choice_mode,
            "use_ai": use_ai,
            "enabled": ai_config.get("enabled", False),
        }


class _DummyReportService:
    def generate_report(self, activity_log=None):
        return {
            "report": {"status": "ok"},
            "markdown_path": "final.md",
        }


class TestActivityLogController:
    def test_append_and_filter(self, tmp_path: Path):
        ctl = ActivityLogController()
        ctl.append("analysis", "hello", "info")
        ctl.append("backup", "bad", "error")
        ctl.set_filter("info", False)
        visible = list(ctl.iter_visible_entries())
        assert len(visible) == 1
        assert visible[0]["badge"] == "FAIL"

    def test_export_session_log(self, tmp_path: Path):
        ctl = ActivityLogController()
        ctl.append("system", "boot", "info")
        ctl.append("report", "pipe | char", "warn")
        json_path, md_path = ctl.export_session_log(tmp_path, "windows")
        assert json_path.exists()
        assert md_path.exists()
        assert "pipe / char" in md_path.read_text(encoding="utf-8")

    @pytest.mark.parametrize(
        "level,badge",
        [
            ("success", "DONE"),
            ("warning", "WARN"),
            ("error", "FAIL"),
            ("info", "INFO"),
        ],
    )
    def test_level_to_badge(self, level, badge):
        assert ActivityLogController.level_to_badge(level) == badge


class TestAutomationCoordinator:
    def test_windows_flow_guided(self):
        """Guided mode skips analysis and file recommendations."""
        ui_state = QtUiState()
        ui_state.mode = "guided"
        ctl = AutomationCoordinator()
        out = ctl.run(
            runtime_mode="windows",
            ui_state=ui_state,
            resolve_restore_bundle_dir=lambda: Path("/tmp"),
            run_inventory=lambda: {"inventory": True},
            run_analysis=lambda: {"analysis": True},
            run_app_recommendations=lambda: {"app": True},
            run_file_recommendations=lambda: {"file": True},
            run_backup=lambda: {"backup": True},
            run_restore=lambda _: {"restore": True},
            run_validation=lambda: {"validation": True},
            generate_final_report=lambda: {"report": True},
        )
        assert out["mode"] == "windows"
        assert out["automation_mode"] == "guided"
        assert ui_state.inventory_completed is True
        # guided mode does NOT run analysis
        assert ui_state.analysis_completed is False
        assert "analysis" not in out
        assert "file_recommendations" not in out

    def test_windows_flow_balanced(self):
        """Balanced mode runs inventory + analysis + both recommendation types + backup."""
        ui_state = QtUiState()
        ui_state.mode = "balanced"
        ctl = AutomationCoordinator()
        out = ctl.run(
            runtime_mode="windows",
            ui_state=ui_state,
            resolve_restore_bundle_dir=lambda: Path("/tmp"),
            run_inventory=lambda: {"inventory": True},
            run_analysis=lambda: {"analysis": True},
            run_app_recommendations=lambda: {"app": True},
            run_file_recommendations=lambda: {"file": True},
            run_backup=lambda: {"backup": True},
            run_restore=lambda _: {"restore": True},
            run_validation=lambda: {"validation": True},
            generate_final_report=lambda: {"report": True},
        )
        assert out["mode"] == "windows"
        assert ui_state.inventory_completed is True
        assert ui_state.analysis_completed is True
        assert "file_recommendations" in out

    def test_linux_flow(self):
        ui_state = QtUiState()
        ctl = AutomationCoordinator()
        out = ctl.run(
            runtime_mode="linux",
            ui_state=ui_state,
            resolve_restore_bundle_dir=lambda: Path("/tmp"),
            run_inventory=lambda: {"inventory": True},
            run_analysis=lambda: {"analysis": True},
            run_app_recommendations=lambda: {"app": True},
            run_file_recommendations=lambda: {"file": True},
            run_backup=lambda: {"backup": True},
            run_restore=lambda _: {"restore": True},
            run_validation=lambda: {"validation": True},
            generate_final_report=lambda: {"report": True},
        )
        assert out["mode"] == "linux"
        assert ui_state.restore_completed is True
        assert ui_state.verification_completed is True


class TestNavigationController:
    def test_navigation_forward_back(self):
        stack = _DummyStack(count=3)
        stepper = _DummyStepper()
        back_btn = _DummyButton()
        next_btn = _DummyButton()
        calls = {"clear": 0}

        ctl = NavigationController(
            stack=stack,
            stepper=stepper,
            back_btn=back_btn,
            next_btn=next_btn,
            clear_error_banner=lambda: calls.__setitem__("clear", calls["clear"] + 1),
            is_auto_running=lambda: False,
        )

        ctl.next_page()
        assert stack.currentIndex() == 1
        ctl.prev_page()
        assert stack.currentIndex() == 0
        assert calls["clear"] >= 2

    def test_next_page_blocked_while_auto_running(self):
        stack = _DummyStack(count=3)
        stepper = _DummyStepper()
        back_btn = _DummyButton()
        next_btn = _DummyButton()
        ctl = NavigationController(
            stack=stack,
            stepper=stepper,
            back_btn=back_btn,
            next_btn=next_btn,
            clear_error_banner=lambda: None,
            is_auto_running=lambda: True,
        )
        ctl.next_page()
        assert stack.currentIndex() == 0

    def test_sync_nav_sets_done_text_on_last_page(self):
        stack = _DummyStack(count=2)
        stack.setCurrentIndex(1)
        stepper = _DummyStepper()
        back_btn = _DummyButton()
        next_btn = _DummyButton()
        ctl = NavigationController(
            stack=stack,
            stepper=stepper,
            back_btn=back_btn,
            next_btn=next_btn,
            clear_error_banner=lambda: None,
            is_auto_running=lambda: False,
        )
        ctl.sync_nav()
        assert next_btn.text == "Done"
        assert stepper.active == 1


class TestModeController:
    def test_mode_transitions(self):
        ui_state = QtUiState()
        panel = _DummyPanel()
        dock = _DummyDock()
        toggle_btn = _DummyButton()
        complete_btn = _DummyButton()
        mode_badge = _DummyButton()
        stack = _DummyStack(count=2)
        logs = []

        ctl = ModeController(
            ui_state=ui_state,
            expert_panel=panel,
            expert_dock=dock,
            expert_toggle_btn=toggle_btn,
            complete_all_btn=complete_btn,
            mode_badge=mode_badge,
            stack=stack,
            log_activity=lambda phase, message: logs.append((phase, message)),
        )

        ctl.on_mode_change("expert")
        assert ui_state.mode == "expert"
        assert dock.isVisible() is True
        ctl.toggle_expert_panel()
        assert dock.isVisible() is False

    def test_guided_mode_disables_expert_controls(self):
        ui_state = QtUiState()
        panel = _DummyPanel()
        dock = _DummyDock()
        dock.show()
        toggle_btn = _DummyButton()
        complete_btn = _DummyButton()
        mode_badge = _DummyButton()
        stack = _DummyStack(count=2)

        ctl = ModeController(
            ui_state=ui_state,
            expert_panel=panel,
            expert_dock=dock,
            expert_toggle_btn=toggle_btn,
            complete_all_btn=complete_btn,
            mode_badge=mode_badge,
            stack=stack,
            log_activity=lambda *_args: None,
        )

        ctl.apply_mode_presentation("guided")
        assert dock.isVisible() is False
        assert toggle_btn.enabled is False
        assert complete_btn.enabled is False


class TestOperationsController:
    def test_helpers(self):
        ui_state = QtUiState()
        cfg = _DummyConfig()
        ctl = OperationsController()

        selected = ctl.resolve_selected_folders(ui_state, cfg)
        assert "Documents" in selected
        ai_cfg = ctl.get_ai_config(cfg)
        assert "enabled" in ai_cfg

    def test_runtime_guard_inventory(self):
        ctl = OperationsController()
        with pytest.raises(RuntimeError):
            ctl.run_inventory(
                runtime_mode="linux",
                migration_service=object(),
                runtime_data={},
                log_activity=lambda *args, **kwargs: None,
                mark_action_done=lambda *args, **kwargs: None,
                clear_error_banner=lambda: None,
            )

    def test_resolve_selected_folders_with_custom_and_selected(self):
        ui_state = QtUiState()
        ui_state.data_strategy = "select"
        ui_state.selected_folders = {"Documents": True, "Pictures": False}
        ui_state.custom_paths = ["/opt/custom"]
        cfg = _DummyConfig()
        ctl = OperationsController()
        selected = ctl.resolve_selected_folders(ui_state, cfg)
        assert "~/Documents" in selected
        assert "/opt/custom" in selected

    def test_run_analysis_uses_inventory_fallback(self):
        ctl = OperationsController()
        runtime_data = {}
        marks = []
        clears = []
        logs = []
        fallback_called = {"value": False}

        def _fallback_inventory():
            fallback_called["value"] = True
            return {
                "software": {"entries": ["pkg"]},
                "hardware": {"cpu": "ok"},
            }

        out = ctl.run_analysis(
            runtime_mode="windows",
            migration_service=_DummyMigrationService(),
            runtime_data=runtime_data,
            log_activity=lambda *args, **kwargs: logs.append(args),
            mark_action_done=lambda key: marks.append(key),
            clear_error_banner=lambda: clears.append(True),
            run_inventory=_fallback_inventory,
        )
        assert fallback_called["value"] is True
        assert "analysis" in runtime_data
        assert out["software"] == ["pkg"]
        assert marks == ["analysis"]
        assert clears

    def test_run_backup_and_validation_happy_paths(self, monkeypatch):
        ctl = OperationsController()
        runtime_data = {}
        ui_state = QtUiState()
        logs = []
        marks = []
        clears = []

        backup = ctl.run_backup(
            runtime_mode="windows",
            migration_service=_DummyMigrationService(),
            config=_DummyConfig(),
            ui_state=ui_state,
            runtime_data=runtime_data,
            log_activity=lambda *args, **kwargs: logs.append(args),
            mark_action_done=lambda key: marks.append(key),
            clear_error_banner=lambda: clears.append(True),
            selected_folders=["~/Documents"],
        )
        assert isinstance(backup, dict)
        assert marks[-1] == "backup"

        monkeypatch.setattr(
            operations_module,
            "validate_restore_report",
            lambda _path: {"total_sovereignty_score": 90, "total_files": 10},
        )
        validation = ctl.run_validation(
            runtime_data=runtime_data,
            ui_state=ui_state,
            log_activity=lambda *args, **kwargs: logs.append(args),
            mark_action_done=lambda key: marks.append(key),
            clear_error_banner=lambda: clears.append(True),
        )
        assert validation["total_sovereignty_score"] == 90
        assert ui_state.verification_completed is True
        assert marks[-1] == "validation"

    def test_generate_final_report_happy_path(self):
        ctl = OperationsController()
        runtime_data = {}
        marks = []
        out = ctl.generate_final_report(
            runtime_data=runtime_data,
            report_service=_DummyReportService(),
            log_activity=lambda *args, **kwargs: None,
            mark_action_done=lambda key: marks.append(key),
            clear_error_banner=lambda: None,
        )
        assert out["report"]["status"] == "ok"
        assert runtime_data["report"]["status"] == "ok"
        assert marks == ["report"]
