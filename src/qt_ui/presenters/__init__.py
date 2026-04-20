"""
Presenters for UI pages.

This package contains presenter/controller classes that manage business logic
and state for each page in the migration wizard. Presenters implement the
Model-View-Presenter (MVP) pattern to separate concerns:

- View (Page): Renders UI and captures user input
- Presenter: Handles business logic and state transitions
- Model (Services): Performs actual migration tasks

Public API
----------
BasePresenter: Base class for all presenters

Full Presenters (fully implemented):
- ModePresenter: Presenter for mode selection page
- ScanPresenter: Presenter for inventory scan page

Stub Presenters (template implementations):
- DataSelectionPresenter: Data folder selection
- ApplicationMappingPresenter: App recommendations
- BackupBundlePresenter: Backup creation
- VerificationPresenter: System verification
- ExecutionPresenter: Migration execution
- RestorePresenter: Data restore
- ReviewRecommendationsPresenter: Review recommendations
- SummaryPresenter: Summary page
- ReportPresenter: Final report

Architecture
------------
Each presenter:
1. Extends BasePresenter
2. Manages state transitions for its page
3. Handles callbacks and long-running operations
4. Emits signals for UI updates
5. Validates user input before processing

Example
-------
from src.qt_ui.presenters import ModePresenter

presenter = ModePresenter(ui_state)
presenter.request_next.connect(on_next_page)
presenter.on_page_shown()
"""

from src.qt_ui.presenters.base_presenter import BasePresenter
from src.qt_ui.presenters.mode_presenter import ModePresenter
from src.qt_ui.presenters.scan_presenter import ScanPresenter
from src.qt_ui.presenters.stub_presenters import (
    DataSelectionPresenter,
    ApplicationMappingPresenter,
    BackupBundlePresenter,
    VerificationPresenter,
    ExecutionPresenter,
    RestorePresenter,
    ReviewRecommendationsPresenter,
    SummaryPresenter,
    ReportPresenter,
)

__all__ = [
    "BasePresenter",
    "ModePresenter",
    "ScanPresenter",
    "DataSelectionPresenter",
    "ApplicationMappingPresenter",
    "BackupBundlePresenter",
    "VerificationPresenter",
    "ExecutionPresenter",
    "RestorePresenter",
    "ReviewRecommendationsPresenter",
    "SummaryPresenter",
    "ReportPresenter",
]
