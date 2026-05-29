"""Main Qt window that orchestrates the migration workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QThreadPool, QTimer, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QDockWidget,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QRadioButton,
    QSizePolicy,
    QStackedWidget,
    QSplitter,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.constants import RESTORE_REPORT
from src.config import MigrationConfigRoot
from src.qt_ui.pages.backup_bundle_page import BackupBundlePage
from src.qt_ui.pages.data_selection_page import DataSelectionPage
from src.qt_ui.pages.report_page import ReportPage
from src.qt_ui.pages.restore_page import RestorePage
from src.qt_ui.pages.scan_page import ScanPage
from src.qt_ui.pages.settings_page import SettingsPage
from src.qt_ui.pages.mode_page import ModePage
from src.qt_ui.pages.review_recommendations_page import ReviewRecommendationsPage
from src.qt_ui.pages.verification_page import VerificationPage
from src.qt_ui.pages.welcome_page import WelcomePage
from src.qt_ui.state import QtUiState
from src.qt_ui.workers import FunctionWorker
from src.qt_ui.widgets.expert_panel import ExpertPanel
from src.qt_ui.widgets.stepper_sidebar import StepperSidebar
from src.qt_ui.controllers import ActivityLogController, AutomationCoordinator, NavigationController, ModeController, OperationsController

from src.orchestration.errors import user_facing_error

from src.services.migration_service import MigrationService
from src.services.pipeline_service import PipelineService
from src.services.recommendation_service import RecommendationService
from src.services.file_recommendation_service import FileRecommendationService
from src.services.report_service import ReportService


class QtMigrationWindow(QMainWindow):
    """Coordinate page navigation, background tasks, and migration state."""

    activity_event = Signal(str, str, str)

    def __init__(self, config: MigrationConfigRoot, runtime_mode: str) -> None:
        """Build the main window and wire the runtime services."""
        super().__init__()
        self.config = config
        self.runtime_mode = runtime_mode
        self.ui_state = QtUiState()
        self.runtime_data: dict[str, object] = {}
        self.auto_running = False
        self._busy_count: int = 0
        self.thread_pool = QThreadPool.globalInstance()
        self.completed_actions: set[str] = set()
        self.total_actions = 7 if runtime_mode == "windows" else 3
        self.activity_log = ActivityLogController()
        self.activity_entries = self.activity_log.entries
        self.activity_filters = self.activity_log.filters
        self.automation = AutomationCoordinator()
        self.navigation = None
        self.mode_controller = None
        self.operations = OperationsController()

        self.migration_service = MigrationService(config=self.config, context={})
        self.pipeline_service = PipelineService(config=self.config)
        self.report_service = ReportService()
        self.recommendation_service = RecommendationService()
        self.file_recommendation_service = FileRecommendationService()
        self.activity_event.connect(self._on_activity_event)

        self.setWindowTitle("Sovereignty Migration Platform (Qt)")
        self.resize(1360, 820)
        self.setMinimumSize(1160, 700)

        self._build_ui()
        self._sync_nav()
        self._apply_mode_presentation(self.ui_state.mode)
        self._schedule_auto_start_if_enabled()

    def _schedule_auto_start_if_enabled(self) -> None:
        """Start the full automation flow automatically when enabled."""
        if not self.config.automation.auto_start_full_flow:
            return

        delay = max(0, int(self.config.automation.auto_start_delay_ms))
        QTimer.singleShot(delay, self._run_full_automation)

    def _build_ui(self) -> None:
        """Construct the window layout, page stack, and activity console."""
        root = QWidget(self)
        root.setObjectName("RootSurface")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 14, 18, 12)
        root_layout.setSpacing(12)

        # Title bar.
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)
        title = QLabel("Sovereignty Migration Platform")
        title.setObjectName("AppTitle")
        top_bar.addStretch(1)
        top_bar.addWidget(title)
        top_bar.addStretch(1)
        root_layout.addLayout(top_bar)

        subtitle = QLabel(
            "A guided migration workspace for discovery, backup, restore, validation, and evidence reports."
        )
        subtitle.setObjectName("AppSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        root_layout.addWidget(subtitle)

        # Controls row.
        control_bar = QHBoxLayout()
        control_bar.addStretch(1)
        control_bar.addWidget(QLabel("Mode:"))
        self.guided_radio = QRadioButton("Guided")
        self.guided_radio.setChecked(True)

        self.balanced_radio = QRadioButton("Balanced")
        self.expert_radio = QRadioButton("Expert")

        self.guided_radio.toggled.connect(lambda: self._on_mode_change("guided") if self.guided_radio.isChecked() else None)
        self.balanced_radio.toggled.connect(lambda: self._on_mode_change("balanced") if self.balanced_radio.isChecked() else None)
        self.expert_radio.toggled.connect(lambda: self._on_mode_change("expert") if self.expert_radio.isChecked() else None)

        control_bar.addWidget(self.guided_radio)
        control_bar.addWidget(self.balanced_radio)
        control_bar.addWidget(self.expert_radio)

        self.expert_toggle_btn = QPushButton("Advanced Controls")
        self.expert_toggle_btn.setProperty("role", "badge")
        self.expert_toggle_btn.clicked.connect(self._toggle_expert_panel)
        control_bar.addWidget(self.expert_toggle_btn)

        root_layout.addLayout(control_bar)

        self.error_banner = QLabel("")
        self.error_banner.setObjectName("ErrorBanner")
        self.error_banner.setWordWrap(True)
        self.error_banner.setVisible(False)
        root_layout.addWidget(self.error_banner)

        self.global_scan_bar = QProgressBar()
        self.global_scan_bar.setObjectName("GlobalScanBar")
        self.global_scan_bar.setRange(0, 0)
        self.global_scan_bar.setFixedHeight(4)
        self.global_scan_bar.setTextVisible(False)
        self.global_scan_bar.setVisible(False)
        root_layout.addWidget(self.global_scan_bar)

        # Main content with left stepper + page stack.
        content_row = QHBoxLayout()
        content_row.setSpacing(16)
        self.stack = QStackedWidget()
        self.stack.setObjectName("PageStack")
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        if self.runtime_mode == "windows":
            self.stepper = StepperSidebar(
                title="Windows 11 → Linux Mint",
                subtitle="Follow the steps below to prepare your complete migration bundle.",
                steps=[
                    "Welcome\nGet oriented before you begin",
                    "Mode Selection\nChoose your interaction mode",
                    "Windows Scan\nInventory + app recommendations",
                    "Settings Migration\nDesktop preferences & themes",
                    "Data Selection\nChoose your files & folders",
                    "Review & Customize\nFinalise recommendations",
                    "Create Backup Bundle\nPack and export your data",
                ],
            )

            self.welcome_page = WelcomePage(self.ui_state)
            self.mode_page = ModePage(self.ui_state)
            self.scan_page = ScanPage(
                self.ui_state,
                run_inventory_cb=self._run_inventory,
                run_analysis_cb=self._run_analysis,
                privacy_policy=self.operations.get_ai_config(self.config),
            )
            self.settings_page = SettingsPage(self.ui_state)
            self.data_page = DataSelectionPage(
                self.ui_state,
                file_type_catalog=self.config.source_system.file_types,
                file_type_labels=self.config.source_system.file_type_labels,
                usage_recommendation_cb=self._collect_usage_recommendations,
            )
            self.review_page = ReviewRecommendationsPage(
                self.ui_state,
                run_app_recommendations_cb=self._run_app_recommendations,
                run_file_recommendations_cb=self._run_file_recommendations,
            )
            self.backup_page = BackupBundlePage(self.ui_state, run_backup_cb=self._run_backup)

            self.welcome_page.request_next.connect(self.next_page)
            self.mode_page.request_next.connect(self.next_page)
            self.scan_page.request_next.connect(self.next_page)
            self.settings_page.request_next.connect(self.next_page)
            self.data_page.request_next.connect(self.next_page)
            self.review_page.request_next.connect(self.next_page)
            self.backup_page.request_next.connect(self.next_page)

            self.guided_radio.toggled.connect(self.mode_page.guided_radio.setChecked)
            self.balanced_radio.toggled.connect(self.mode_page.balanced_radio.setChecked)
            self.expert_radio.toggled.connect(self.mode_page.expert_radio.setChecked)

            self.mode_page.guided_radio.toggled.connect(lambda checked: self.guided_radio.setChecked(checked))
            self.mode_page.balanced_radio.toggled.connect(lambda checked: self.balanced_radio.setChecked(checked))
            self.mode_page.expert_radio.toggled.connect(lambda checked: self.expert_radio.setChecked(checked))

            # Order: Welcome → Mode → Scan (inventory + analysis + strategy) → Settings → Data → Review → Backup
            self.stack.addWidget(self.welcome_page)
            self.stack.addWidget(self.mode_page)
            self.stack.addWidget(self.scan_page)
            self.stack.addWidget(self.settings_page)
            self.stack.addWidget(self.data_page)
            self.stack.addWidget(self.review_page)
            self.stack.addWidget(self.backup_page)

            # Connect each page's processing_changed → sync_nav so nav buttons update in real-time.
            for _p in [
                self.welcome_page, self.mode_page, self.scan_page, self.settings_page,
                self.data_page, self.review_page, self.backup_page,
            ]:
                _p.processing_changed.connect(self._sync_nav)
                _p.processing_changed.connect(self._on_any_page_processing_changed)
        else:
            self.stepper = StepperSidebar(
                title="Migration Steps",
                subtitle="Follow the Linux-side steps to finalize migration and publish the report.",
                steps=[
                    "Restore Data\nStart restoration",
                    "Validation\nReview and verify",
                    "Final Report\nGenerate evidence",
                ],
            )
            self.restore_page = RestorePage(self.ui_state, run_restore_cb=self._run_restore)
            self.verify_page = VerificationPage(self.ui_state, run_validation_cb=self._run_validation)
            self.report_page = ReportPage(self.ui_state, generate_report_cb=self._generate_final_report)

            self.restore_page.request_next.connect(self.next_page)
            self.verify_page.request_next.connect(self.next_page)
            self.report_page.request_next.connect(self.next_page)
            self.stack.addWidget(self.restore_page)
            self.stack.addWidget(self.verify_page)
            self.stack.addWidget(self.report_page)

        self.stepper.setMinimumWidth(260)
        self.stepper.setMaximumWidth(310)
        self.stack.setMinimumWidth(0)

        # Wrap stepper in a scroll area so all steps stay reachable on short windows.
        stepper_scroll = QScrollArea()
        stepper_scroll.setWidgetResizable(True)
        stepper_scroll.setFrameShape(QFrame.NoFrame)
        stepper_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        stepper_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        stepper_scroll.setWidget(self.stepper)
        stepper_scroll.setMinimumWidth(260)
        stepper_scroll.setMaximumWidth(310)
        stepper_scroll.setStyleSheet("QScrollArea { background: #0D1929; border: none; } QScrollArea > QWidget { background: #0D1929; }")

        self.stack_scroll = QScrollArea()
        self.stack_scroll.setWidgetResizable(True)
        self.stack_scroll.setFrameShape(QFrame.NoFrame)
        self.stack_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.stack_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.stack_scroll.setWidget(self.stack)

        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setObjectName("MainSplitter")
        content_splitter.setChildrenCollapsible(False)
        content_splitter.setHandleWidth(10)
        content_splitter.addWidget(stepper_scroll)
        content_splitter.addWidget(self.stack_scroll)
        content_splitter.setStretchFactor(0, 0)
        content_splitter.setStretchFactor(1, 1)
        content_splitter.setSizes([270, 920])

        content_row.addWidget(content_splitter, stretch=1)
        root_layout.addLayout(content_row, stretch=1)

        # Live operation console (collapsible).
        self.activity_group = QGroupBox()
        self.activity_group.setObjectName("ActivityGroup")
        activity_layout = QVBoxLayout(self.activity_group)
        activity_layout.setContentsMargins(12, 10, 12, 12)
        activity_layout.setSpacing(8)

        # Header row: status label + collapse toggle
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        self.activity_status = QLabel("Pipeline idle. Start a step to see detailed runtime events.")
        self.activity_status.setObjectName("ActivityStatus")
        self.activity_status.setWordWrap(True)
        header_row.addWidget(self.activity_status, stretch=1)

        self.collapse_activity_btn = QPushButton("▼  Hide")
        self.collapse_activity_btn.setProperty("role", "badge")
        self.collapse_activity_btn.setToolTip("Collapse activity panel")
        self.collapse_activity_btn.clicked.connect(self._toggle_activity_collapse)
        header_row.addWidget(self.collapse_activity_btn)

        activity_layout.addLayout(header_row)

        # Collapsible body
        self._activity_collapsed = False
        self.activity_body = QWidget()
        body_layout = QVBoxLayout(self.activity_body)
        body_layout.setContentsMargins(0, 4, 0, 0)
        body_layout.setSpacing(8)

        self.pipeline_progress = QProgressBar()
        self.pipeline_progress.setRange(0, 100)
        self.pipeline_progress.setValue(0)
        self.pipeline_progress.setFormat("Overall Progress: %p%")
        self.pipeline_progress.setTextVisible(True)
        body_layout.addWidget(self.pipeline_progress)

        filter_row = QHBoxLayout()
        self.toggle_filters_btn = QPushButton("Show Log Filters")
        self.toggle_filters_btn.setProperty("role", "badge")
        self.toggle_filters_btn.clicked.connect(self._toggle_log_filters)
        filter_row.addWidget(self.toggle_filters_btn)

        self.export_log_btn = QPushButton("Export Session Log")
        self.export_log_btn.setProperty("role", "badge")
        self.export_log_btn.clicked.connect(self._export_session_log)
        filter_row.addWidget(self.export_log_btn)
        filter_row.addStretch(1)
        body_layout.addLayout(filter_row)

        self.log_filters_panel = QWidget()
        self.log_filters_panel.setObjectName("LogFiltersPanel")
        filters_layout = QHBoxLayout(self.log_filters_panel)
        filters_layout.setContentsMargins(8, 6, 8, 6)
        filters_layout.setSpacing(12)

        self.info_filter = QCheckBox("Info")
        self.info_filter.setChecked(True)
        self.info_filter.toggled.connect(lambda v: self._set_log_filter("info", v))
        filters_layout.addWidget(self.info_filter)

        self.done_filter = QCheckBox("Done")
        self.done_filter.setChecked(True)
        self.done_filter.toggled.connect(lambda v: self._set_log_filter("done", v))
        filters_layout.addWidget(self.done_filter)

        self.warn_filter = QCheckBox("Warn")
        self.warn_filter.setChecked(True)
        self.warn_filter.toggled.connect(lambda v: self._set_log_filter("warn", v))
        filters_layout.addWidget(self.warn_filter)

        self.fail_filter = QCheckBox("Fail")
        self.fail_filter.setChecked(True)
        self.fail_filter.toggled.connect(lambda v: self._set_log_filter("fail", v))
        filters_layout.addWidget(self.fail_filter)
        filters_layout.addStretch(1)

        self.log_filters_panel.setVisible(False)
        body_layout.addWidget(self.log_filters_panel)

        self.activity_list = QListWidget()
        self.activity_list.setObjectName("ActivityLog")
        self.activity_list.setMinimumHeight(92)
        self.activity_list.setMaximumHeight(136)
        body_layout.addWidget(self.activity_list)

        activity_layout.addWidget(self.activity_body)

        root_layout.addWidget(self.activity_group)

        # Bottom navigation.
        nav = QHBoxLayout()
        nav.setSpacing(10)

        self.back_btn = QPushButton("Back")
        self.back_btn.setProperty("role", "badge")
        self.back_btn.clicked.connect(self.prev_page)
        nav.addWidget(self.back_btn, alignment=Qt.AlignLeft)

        nav.addStretch(1)

        center_status = QWidget()
        center_status.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        center_status_layout = QHBoxLayout(center_status)
        center_status_layout.setContentsMargins(0, 0, 0, 0)
        center_status_layout.setSpacing(8)

        self.mode_badge = QLabel("Mode Status: Guided")
        self.mode_badge.setObjectName("StatusPill")
        self.mode_badge.setToolTip("Current interaction mode status")
        center_status_layout.addWidget(self.mode_badge)

        self.commitment_badge = QLabel("License: Open Source")
        self.commitment_badge.setObjectName("StatusPill")
        self.commitment_badge.setToolTip("Project licensing and openness status")
        center_status_layout.addWidget(self.commitment_badge)

        nav.addWidget(center_status, alignment=Qt.AlignCenter)
        nav.addStretch(1)

        self.complete_all_btn = QPushButton("Complete All Phases")
        self.complete_all_btn.setProperty("role", "cta")
        self.complete_all_btn.clicked.connect(self._run_full_automation)
        self.complete_all_btn.setEnabled(False)
        nav.addWidget(self.complete_all_btn, alignment=Qt.AlignRight)

        self.next_btn = QPushButton("Next")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.clicked.connect(self.next_page)
        nav.addWidget(self.next_btn, alignment=Qt.AlignRight)
        root_layout.addLayout(nav)

        self.navigation = NavigationController(
            stack=self.stack,
            stepper=self.stepper,
            back_btn=self.back_btn,
            next_btn=self.next_btn,
            clear_error_banner=self._clear_error_banner,
            is_auto_running=lambda: self.auto_running,
            is_busy=self._is_busy,
        )

        self.stepper.step_clicked.connect(self._on_stepper_step_clicked)

        self.setCentralWidget(root)

        # Right expert panel (dock).
        self.expert_dock = QDockWidget("Expert Overrides", self)
        self.expert_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.expert_dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        profile_path = Path(self.config.automation.active_profile_path)
        if not profile_path.is_absolute():
            profile_path = Path(__file__).resolve().parents[2] / profile_path
        self.expert_panel = ExpertPanel(self.ui_state, profile_path=profile_path)
        self.expert_panel.setMaximumWidth(460)
        self.expert_dock.setMinimumWidth(360)
        self.expert_dock.setMaximumWidth(460)

        self.expert_scroll = QScrollArea()
        self.expert_scroll.setWidgetResizable(True)
        self.expert_scroll.setFrameShape(QScrollArea.NoFrame)
        self.expert_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.expert_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.expert_scroll.setWidget(self.expert_panel)

        self.expert_dock.setWidget(self.expert_scroll)
        self.addDockWidget(Qt.RightDockWidgetArea, self.expert_dock)
        self.expert_dock.hide()

        self.mode_controller = ModeController(
            ui_state=self.ui_state,
            expert_panel=self.expert_panel,
            expert_dock=self.expert_dock,
            expert_toggle_btn=self.expert_toggle_btn,
            complete_all_btn=self.complete_all_btn,
            mode_badge=self.mode_badge,
            stack=self.stack,
            log_activity=self._log_activity,
        )

        self._log_activity("system", "Application initialized. Waiting for action.")

    def _on_mode_change(self, value: str) -> None:
        if self.mode_controller is not None:
            self.mode_controller.on_mode_change(value)
        self._sync_expert_page_context()

    def _apply_mode_presentation(self, mode: str) -> None:
        if self.mode_controller is not None:
            self.mode_controller.apply_mode_presentation(mode)

    def _toggle_expert_panel(self) -> None:
        if self.mode_controller is not None:
            self.mode_controller.toggle_expert_panel()

    def _is_busy(self) -> bool:
        return self._busy_count > 0

    def _on_any_page_processing_changed(self, _: bool) -> None:
        any_busy = any(
            getattr(self.stack.widget(i), "is_processing", False)
            for i in range(self.stack.count())
        )
        self.global_scan_bar.setVisible(any_busy)

    def _set_busy(self, busy: bool) -> None:
        self._busy_count = max(0, self._busy_count + (1 if busy else -1))
        self._sync_nav()

    def _set_automation_running(self, running: bool) -> None:
        self.auto_running = running
        self.complete_all_btn.setEnabled(not running and self.ui_state.mode != "guided")
        self.expert_toggle_btn.setEnabled(not running and self.ui_state.mode != "guided")
        self._sync_nav()
        if running:
            self.activity_status.setText("Automation is running. Follow step-by-step events below.")

    def _run_full_automation(self) -> None:
        if self.auto_running:
            return

        self._log_activity("pipeline", "Full automation requested.")
        self._set_automation_running(True)
        self.complete_all_btn.setText("Running...")
        worker = FunctionWorker(self._complete_full_flow)
        worker.signals.result.connect(self._on_automation_result)
        worker.signals.error.connect(self._on_automation_error)
        worker.signals.finished.connect(self._on_automation_finished)
        self.thread_pool.start(worker)

    def _complete_full_flow(self) -> dict:
        return self.automation.run(
            runtime_mode=self.runtime_mode,
            ui_state=self.ui_state,
            resolve_restore_bundle_dir=self._resolve_restore_bundle_dir,
            run_inventory=self._run_inventory,
            run_analysis=self._run_analysis,
            run_app_recommendations=self._run_app_recommendations,
            run_file_recommendations=self._run_file_recommendations,
            run_backup=self._run_backup,
            run_restore=self._run_restore,
            run_validation=self._run_validation,
            generate_final_report=self._generate_final_report,
        )

    def _resolve_restore_bundle_dir(self) -> Path:
        bundle_dir = RESTORE_REPORT.parent
        if (bundle_dir / "manifest.json").exists() and (bundle_dir / "backup.zip").exists():
            return bundle_dir

        raise RuntimeError(
            "No backup bundle found. Run the Windows backup flow first so manifest.json and backup.zip exist in the restore directory."
        )

    def _on_automation_result(self, result: object) -> None:
        if isinstance(result, dict):
            self._log_activity("pipeline", "Full automation completed successfully.")
            self.stack.setCurrentIndex(self.stack.count() - 1)
            current = self.stack.currentWidget()
            refresh = getattr(current, "refresh", None)
            if callable(refresh):
                refresh()
            self._sync_nav()

    def _on_automation_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self._log_activity("pipeline", f"Automation failed: {error}", level="error")
        self.error_banner.setText(user_facing_error(error))
        self.error_banner.setVisible(True)

    def _clear_error_banner(self) -> None:
        self.error_banner.setVisible(False)
        self.error_banner.setText("")

    def _on_automation_finished(self) -> None:
        self._set_automation_running(False)
        self.complete_all_btn.setText("Complete All Phases")
        self._sync_nav()

    def _on_stepper_step_clicked(self, index: int) -> None:
        if self.navigation is not None:
            self.navigation.go_to_page(index)
        self._sync_expert_page_context()

    def next_page(self) -> None:
        current = self.stack.currentWidget()
        if isinstance(current, SettingsPage):
            self.ui_state.settings_completed = True
            self._mark_action_done("settings")
        if self.navigation is not None:
            self.navigation.next_page()
        self._sync_expert_page_context()

    def prev_page(self) -> None:
        if self.navigation is not None:
            self.navigation.prev_page()
        self._sync_expert_page_context()

    def _sync_nav(self) -> None:
        if self.navigation is not None:
            self.navigation.sync_nav()
        self._sync_expert_page_context()

    def _sync_expert_page_context(self) -> None:
        if hasattr(self, "activity_group"):
            self.activity_group.setVisible(self.stack.currentIndex() > 0)
        if not hasattr(self, "expert_panel"):
            return
        current = self.stack.currentWidget()
        page_key = "mode_selection"
        if isinstance(current, WelcomePage):
            page_key = "welcome"
        elif isinstance(current, ModePage):
            page_key = "mode_selection"
        elif isinstance(current, SettingsPage):
            page_key = "settings_migration"
        elif isinstance(current, DataSelectionPage):
            page_key = "data_selection"
        elif isinstance(current, ReviewRecommendationsPage):
            page_key = "review_recommendations"
        elif isinstance(current, ScanPage):
            page_key = "scan"
        elif isinstance(current, BackupBundlePage):
            page_key = "backup_bundle"
        elif isinstance(current, RestorePage):
            page_key = "restore"
        elif isinstance(current, VerificationPage):
            page_key = "verification"
        elif isinstance(current, ReportPage):
            page_key = "report"

        self.expert_panel.set_page_context(page_key)

    def _toggle_activity_collapse(self) -> None:
        self._activity_collapsed = not self._activity_collapsed
        self.activity_body.setVisible(not self._activity_collapsed)
        if self._activity_collapsed:
            self.collapse_activity_btn.setText("▶  Show")
            self.collapse_activity_btn.setToolTip("Expand activity panel")
        else:
            self.collapse_activity_btn.setText("▼  Hide")
            self.collapse_activity_btn.setToolTip("Collapse activity panel")

    def _toggle_log_filters(self) -> None:
        if self.ui_state.mode == "guided":
            return
        new_state = not self.log_filters_panel.isVisible()
        self.log_filters_panel.setVisible(new_state)
        self.toggle_filters_btn.setText("Hide Log Filters" if new_state else "Show Log Filters")

    def _set_log_filter(self, key: str, enabled: bool) -> None:
        self.activity_log.set_filter(key, enabled)
        self._refresh_activity_log()


    def _badge_color(self, badge: str) -> QColor:
        return {
            "DONE": QColor("#70e0a1"),
            "WARN": QColor("#ffd96d"),
            "FAIL": QColor("#ff9090"),
            "INFO": QColor("#9ad7f7"),
        }.get(badge, QColor("#9ad7f7"))

    def _refresh_activity_log(self) -> None:
        self.activity_list.clear()
        for entry in self.activity_log.iter_visible_entries():
            badge = entry.get("badge", "INFO")
            item = QListWidgetItem(
                f"[{entry.get('time', '--:--:--')}] [{badge}] [{entry.get('icon', 'LOG')}] {entry.get('phase', '').upper()}: {entry.get('message', '')}"
            )
            item.setForeground(self._badge_color(badge))
            self.activity_list.addItem(item)

        while self.activity_list.count() > 220:
            self.activity_list.takeItem(self.activity_list.count() - 1)

    def _export_session_log(self) -> None:
        if self.ui_state.mode == "guided":
            self._log_activity("report", "Session log export is available in Balanced and Expert modes.", level="warn")
            return

        reports_dir = Path(__file__).resolve().parents[2] / "docs" / "reports"
        try:
            _, md_path = self.activity_log.export_session_log(
                reports_dir=reports_dir,
                runtime_mode=self.runtime_mode,
            )
            self._log_activity("report", f"Session log exported to {md_path}", level="success")
        except Exception as exc:
            self._log_activity("report", f"Session log export failed: {exc}", level="error")

    def _log_activity(self, phase: str, message: str, level: str = "info") -> None:
        self.activity_event.emit(phase, message, level)

    def _on_activity_event(self, phase: str, message: str, level: str) -> None:
        self.activity_log.append(phase=phase, message=message, level=level)
        # Late events can arrive while the window is being destroyed.
        try:
            self._refresh_activity_log()
            self.activity_status.setText(message)
        except RuntimeError:
            return

    def closeEvent(self, event) -> None:
        """Disconnect transient signals before Qt destroys child widgets."""
        try:
            self.activity_event.disconnect(self._on_activity_event)
        except Exception:
            pass
        super().closeEvent(event)

    def _mark_action_done(self, action_key: str) -> None:
        self.completed_actions.add(action_key)
        progress = int((len(self.completed_actions) / max(1, self.total_actions)) * 100)
        self.pipeline_progress.setValue(progress)

    def _run_inventory(self, deep_scan: bool = False) -> dict:
        return self.operations.run_inventory(
            runtime_mode=self.runtime_mode,
            migration_service=self.migration_service,
            runtime_data=self.runtime_data,
            log_activity=self._log_activity,
            mark_action_done=self._mark_action_done,
            clear_error_banner=self._clear_error_banner,
            deep_scan=deep_scan,
        )

    def _generate_software_recommendations(self, strategy: str = "local", selection_profile: str = "migrate_all") -> dict:
        return self.operations.generate_software_recommendations(
            runtime_mode=self.runtime_mode,
            ui_state=self.ui_state,
            ai_config=self.operations.get_ai_config(self.config),
            recommendation_service=self.recommendation_service,
            runtime_data=self.runtime_data,
            log_activity=self._log_activity,
            run_inventory=self._run_inventory,
            strategy=strategy,
            selection_profile=selection_profile,
        )

    def _run_app_recommendations(self) -> dict:
        """Generate app-level recommendations for review page."""
        return self.operations.run_app_recommendations(
            runtime_mode=self.runtime_mode,
            ui_state=self.ui_state,
            ai_config=self.operations.get_ai_config(self.config),
            recommendation_service=self.recommendation_service,
            runtime_data=self.runtime_data,
            log_activity=self._log_activity,
            run_inventory=self._run_inventory,
        )

    def _run_file_recommendations(self) -> dict:
        """Generate file-level recommendations for review page."""
        return self.operations.run_file_recommendations(
            runtime_mode=self.runtime_mode,
            config=self.config,
            ui_state=self.ui_state,
            file_recommendation_service=self.file_recommendation_service,
            runtime_data=self.runtime_data,
            log_activity=self._log_activity,
            ai_config=self.operations.get_ai_config(self.config),
        )

    def _run_analysis(self) -> dict:
        return self.operations.run_analysis(
            runtime_mode=self.runtime_mode,
            migration_service=self.migration_service,
            runtime_data=self.runtime_data,
            log_activity=self._log_activity,
            mark_action_done=self._mark_action_done,
            clear_error_banner=self._clear_error_banner,
            run_inventory=self._run_inventory,
        )

    def _collect_usage_recommendations(self) -> None:
        selected_folders = self.operations.resolve_selected_folders(self.ui_state, self.config)
        worker = FunctionWorker(
            self.operations.collect_usage_recommendations,
            selected_folders=selected_folders,
            file_type_catalog=self.config.source_system.file_types,
        )
        worker.signals.result.connect(self._on_recommendations_ready)
        self.thread_pool.start(worker)

    def _on_recommendations_ready(self, recommendations: list[dict[str, Any]]) -> None:
        self._log_activity("recommendation", "Usage recommendations are ready for review.")
        self.ui_state.usage_recommendations = recommendations
        current = self.stack.currentWidget()
        if hasattr(current, "_refresh_usage_recommendations"):
            current._refresh_usage_recommendations()

    def _run_backup(self) -> dict | None:
        selected_folders = self.operations.resolve_selected_folders(self.ui_state, self.config)
        return self.operations.run_backup(
            runtime_mode=self.runtime_mode,
            migration_service=self.migration_service,
            config=self.config,
            ui_state=self.ui_state,
            runtime_data=self.runtime_data,
            log_activity=self._log_activity,
            mark_action_done=self._mark_action_done,
            clear_error_banner=self._clear_error_banner,
            selected_folders=selected_folders,
        )

    def _run_restore(self, bundle_dir: Path) -> dict:
        return self.operations.run_restore(
            runtime_mode=self.runtime_mode,
            config=self.config,
            runtime_data=self.runtime_data,
            ui_state=self.ui_state,
            log_activity=self._log_activity,
            mark_action_done=self._mark_action_done,
            clear_error_banner=self._clear_error_banner,
            bundle_dir=bundle_dir,
        )

    def _run_validation(self) -> dict:
        return self.operations.run_validation(
            runtime_data=self.runtime_data,
            ui_state=self.ui_state,
            log_activity=self._log_activity,
            mark_action_done=self._mark_action_done,
            clear_error_banner=self._clear_error_banner,
        )

    def _generate_final_report(self) -> dict:
        return self.operations.generate_final_report(
            runtime_data=self.runtime_data,
            report_service=self.report_service,
            log_activity=self._log_activity,
            mark_action_done=self._mark_action_done,
            clear_error_banner=self._clear_error_banner,
            activity_log=list(self.activity_log.entries),
        )

    @staticmethod
    def _format_size(num_bytes: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(num_bytes)
        for unit in units:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
