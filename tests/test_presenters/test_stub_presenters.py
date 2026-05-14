"""Tests for stub presenter implementations."""

import pytest

from src.qt_ui.presenters import (
    ApplicationMappingPresenter,
    BackupBundlePresenter,
    DataSelectionPresenter,
    ExecutionPresenter,
    ReportPresenter,
    RestorePresenter,
    ReviewRecommendationsPresenter,
    SummaryPresenter,
    VerificationPresenter,
)


class TestStubPresenters:
    @pytest.mark.parametrize(
        "presenter_cls,expected_title",
        [
            (DataSelectionPresenter, "Select Data to Migrate"),
            (ApplicationMappingPresenter, "Review Application Recommendations"),
            (BackupBundlePresenter, "Create Backup Bundle"),
            (VerificationPresenter, "Verify System Compatibility"),
            (ExecutionPresenter, "Execute Migration"),
            (RestorePresenter, "Restore Data"),
            (ReviewRecommendationsPresenter, "Review Recommendations"),
            (SummaryPresenter, "Migration Summary"),
            (ReportPresenter, "Migration Report"),
        ],
    )
    def test_initialization_sets_page_title(self, ui_state, presenter_cls, expected_title):
        presenter = presenter_cls(ui_state)
        assert presenter.ui_state is ui_state
        assert presenter.on_page_before_previous() is True
        titles = []
        presenter.page_title_changed.connect(lambda title: titles.append(title))
        presenter.update_page_title(expected_title)
        assert titles[-1] == expected_title

    def test_data_selection_requires_one_folder(self, ui_state):
        presenter = DataSelectionPresenter(ui_state)
        ui_state.selected_folders = {"Documents": False, "Desktop": False}

        errors = []
        presenter.error_occurred.connect(lambda message: errors.append(message))
        assert presenter.on_page_before_next() is False
        assert errors[-1] == "Please select at least one folder"

        ui_state.selected_folders["Documents"] = True
        assert presenter.on_page_before_next() is True

    def test_backup_bundle_requires_backup_complete(self, ui_state):
        presenter = BackupBundlePresenter(ui_state)

        errors = []
        presenter.error_occurred.connect(lambda message: errors.append(message))

        ui_state.backup_completed = False
        assert presenter.on_page_before_next() is False
        assert errors[-1] == "Backup creation required"

        ui_state.backup_completed = True
        assert presenter.on_page_before_next() is True

    def test_restore_requires_restore_complete(self, ui_state):
        presenter = RestorePresenter(ui_state)

        errors = []
        presenter.error_occurred.connect(lambda message: errors.append(message))

        ui_state.restore_completed = False
        assert presenter.on_page_before_next() is False
        assert errors[-1] == "Restore operation required"

        ui_state.restore_completed = True
        assert presenter.on_page_before_next() is True

    def test_report_is_terminal_page(self, ui_state):
        presenter = ReportPresenter(ui_state)
        assert presenter.on_page_before_next() is False

    @pytest.mark.parametrize(
        "presenter_cls",
        [
            DataSelectionPresenter,
            ApplicationMappingPresenter,
            BackupBundlePresenter,
            VerificationPresenter,
            ExecutionPresenter,
            RestorePresenter,
            ReviewRecommendationsPresenter,
            SummaryPresenter,
            ReportPresenter,
        ],
    )
    def test_page_shown_and_refresh_are_safe(self, ui_state, presenter_cls):
        presenter = presenter_cls(ui_state)
        presenter.refresh()
        presenter.on_page_shown()
