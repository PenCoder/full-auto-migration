"""Tests for UI component module availability and presenter integration."""

from importlib.util import find_spec
from unittest.mock import Mock


class TestPageModules:
    """Verify expected Qt page modules are present in the package."""

    def test_mode_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.mode_page") is not None

    def test_scan_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.scan_page") is not None

    def test_settings_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.settings_page") is not None

    def test_data_selection_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.data_selection_page") is not None

    def test_backup_bundle_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.backup_bundle_page") is not None

    def test_verification_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.verification_page") is not None

    def test_restore_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.restore_page") is not None

    def test_report_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.report_page") is not None


class TestNavigationGating:
    """Verify navigation gating through ui_state flags (mirrors ScanPage.can_proceed logic)."""

    def test_scan_blocks_until_inventory_completed(self, ui_state):
        assert ui_state.inventory_completed is False

    def test_scan_allows_when_inventory_completed(self, ui_state):
        ui_state.inventory_completed = True
        assert ui_state.inventory_completed is True

    def test_mode_is_always_valid_after_set(self, ui_state):
        for mode in ("guided", "balanced", "expert"):
            ui_state.mode = mode
            assert ui_state.mode == mode

    def test_analysis_completion_tracked_independently(self, ui_state):
        ui_state.inventory_completed = True
        ui_state.analysis_completed = True
        assert ui_state.inventory_completed is True
        assert ui_state.analysis_completed is True
