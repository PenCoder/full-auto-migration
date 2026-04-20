"""Tests for UI component module availability and presenter integration."""

from importlib.util import find_spec
from unittest.mock import Mock


class TestPageModules:
    """Verify expected Qt page modules are present in the package."""

    def test_mode_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.mode_page") is not None

    def test_scan_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.scan_page") is not None

    def test_data_selection_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.data_selection_page") is not None

    def test_application_mapping_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.application_mapping_page") is not None

    def test_backup_bundle_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.backup_bundle_page") is not None

    def test_verification_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.verification_page") is not None

    def test_execution_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.execution_page") is not None

    def test_restore_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.restore_page") is not None

    def test_summary_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.summary_page") is not None

    def test_report_page_module_exists(self):
        assert find_spec("src.qt_ui.pages.report_page") is not None


class TestPresenterNavigation:
    """Verify presenter navigation hooks used by the Qt flow."""

    def test_mode_presenter_navigation_contract(self, ui_state):
        from src.qt_ui.presenters import ModePresenter

        presenter = ModePresenter(ui_state)
        assert presenter.on_page_before_next() is True
        assert presenter.on_page_before_previous() is True

    def test_scan_presenter_blocks_until_completed(self, ui_state):
        from src.qt_ui.presenters import ScanPresenter

        presenter = ScanPresenter(ui_state, Mock(return_value={}), Mock(return_value={}))
        assert presenter.on_page_before_next() is False

    def test_scan_presenter_allows_when_completed(self, ui_state):
        from src.qt_ui.presenters import ScanPresenter

        ui_state.inventory_completed = True
        ui_state.analysis_completed = True
        presenter = ScanPresenter(ui_state, Mock(return_value={}), Mock(return_value={}))
        assert presenter.on_page_before_next() is True


class TestPresenterSignals:
    """Verify signal attributes exist for UI wiring."""

    def test_mode_presenter_signal_attributes(self, ui_state):
        from src.qt_ui.presenters import ModePresenter

        presenter = ModePresenter(ui_state)
        assert hasattr(presenter, "page_title_changed")
        assert hasattr(presenter, "error_occurred")
        assert hasattr(presenter, "request_next")
        assert hasattr(presenter, "request_back")
