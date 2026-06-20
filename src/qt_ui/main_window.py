"""Main Qt window that orchestrates the migration workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, QThreadPool, QTimer, Qt, Signal
from PySide6.QtWidgets import QMessageBox

from PySide6.QtWidgets import (
    QDockWidget,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QProgressBar,
    QRadioButton,
    QSizePolicy,
    QSplitter,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.constants import RESTORE_DIR, RESTORE_REPORT
from src.config import MigrationConfigRoot
from src.qt_ui.pages.backup_bundle_page import BackupBundlePage
from src.qt_ui.pages.bundle_report_page import BundleReportPage
from src.qt_ui.pages.data_selection_page import DataSelectionPage
from src.qt_ui.pages.report_page import ReportPage
from src.qt_ui.pages.restore_page import RestorePage
from src.qt_ui.pages.scan_page import ScanPage
from src.qt_ui.pages.mode_page import ModePage
from src.qt_ui.pages.review_recommendations_page import ReviewRecommendationsPage
from src.qt_ui.pages.verification_page import VerificationPage
from src.qt_ui.pages.welcome_page import WelcomePage
from src.qt_ui.state import QtUiState
from src.qt_ui.workers import FunctionWorker
from src.qt_ui.widgets.automation_overlay import AutomationOverlay
from src.qt_ui.widgets.expert_panel import ExpertPanel
from src.qt_ui.widgets.help_dialog import HelpDialog
from src.qt_ui.widgets.sized_stack import CurrentSizeStackedWidget
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
    automation_phase = Signal(str)
    automation_step_done = Signal(str)

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
        self.automation_phase.connect(self._on_automation_phase)
        self.automation_step_done.connect(self._on_automation_step_done)

        self.setWindowTitle("Sovereignty Migration Platform (Qt)")
        self.resize(1440, 860)
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
        self._root_widget = root
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Right-hand column: title/controls/banners stacked above the page
        # content. Built as its own widget so the sidebar (added directly to
        # the splitter alongside it) can span the full window height instead
        # of starting below a full-width title bar.
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(18, 14, 18, 12)
        right_layout.setSpacing(12)

        # Title bar.
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)
        title = QLabel("Sovereignty Migration Platform")
        title.setObjectName("AppTitle")
        top_bar.addStretch(1)
        top_bar.addWidget(title)
        top_bar.addStretch(1)
        right_layout.addLayout(top_bar)

        subtitle = QLabel(
            "A guided migration workspace for discovery, backup, restore, validation, and evidence reports."
        )
        subtitle.setObjectName("AppSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        right_layout.addWidget(subtitle)

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

        self.expert_toggle_btn = QPushButton("Customize ▸")
        self.expert_toggle_btn.setProperty("role", "badge")
        self.expert_toggle_btn.clicked.connect(self._toggle_expert_panel)
        control_bar.addWidget(self.expert_toggle_btn)

        self.help_btn = QPushButton("❓ Help")
        self.help_btn.setProperty("role", "badge")
        self.help_btn.setToolTip("What to do on this page")
        self.help_btn.clicked.connect(self._show_help)
        control_bar.addWidget(self.help_btn)

        right_layout.addLayout(control_bar)

        self.error_banner = QLabel("")
        self.error_banner.setObjectName("ErrorBanner")
        self.error_banner.setWordWrap(True)
        self.error_banner.setVisible(False)
        right_layout.addWidget(self.error_banner)

        self.global_scan_bar = QProgressBar()
        self.global_scan_bar.setObjectName("GlobalScanBar")
        self.global_scan_bar.setRange(0, 0)
        self.global_scan_bar.setFixedHeight(4)
        self.global_scan_bar.setTextVisible(False)
        self.global_scan_bar.setVisible(False)
        right_layout.addWidget(self.global_scan_bar)

        self.stack = CurrentSizeStackedWidget()
        self.stack.setObjectName("PageStack")
        self.stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.stack.installEventFilter(self)

        if self.runtime_mode == "windows":
            self.stepper = StepperSidebar(
                title="Windows 11 → Linux Mint",
                subtitle="Five steps to prepare your complete migration bundle.",
                steps=[
                    "Get Started\nChoose your migration mode",
                    "System Scan\nDiscover apps, hardware and settings",
                    "Configure\nFiles and recommendations",
                    "Bundle\nPack and export your migration data",
                    "Report\nReview everything before moving to Linux",
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
                on_selection_changed=lambda recs: self.runtime_data.update({"review_app_recommendations": recs}),
            )
            self.backup_page = BackupBundlePage(self.ui_state, run_backup_cb=self._run_backup)
            self.bundle_report_page = BundleReportPage(self.ui_state, get_bundle_data_cb=self._get_bundle_data)

            self.welcome_page.request_next.connect(self.next_page)
            self.mode_page.request_next.connect(self.next_page)
            self.scan_page.request_next.connect(self.next_page)
            self.data_page.request_next.connect(self.next_page)
            self.review_page.request_next.connect(self.next_page)
            self.backup_page.request_next.connect(self.next_page)
            self.bundle_report_page.request_finish.connect(self._on_finish)

            self.guided_radio.toggled.connect(self.mode_page.guided_radio.setChecked)
            self.balanced_radio.toggled.connect(self.mode_page.balanced_radio.setChecked)
            self.expert_radio.toggled.connect(self.mode_page.expert_radio.setChecked)

            self.mode_page.guided_radio.toggled.connect(lambda checked: self.guided_radio.setChecked(checked))
            self.mode_page.balanced_radio.toggled.connect(lambda checked: self.balanced_radio.setChecked(checked))
            self.mode_page.expert_radio.toggled.connect(lambda checked: self.expert_radio.setChecked(checked))

            # Order: Welcome → Mode → Scan → Data → Review → Backup → Bundle Report
            self.stack.addWidget(self.welcome_page)
            self.stack.addWidget(self.mode_page)
            self.stack.addWidget(self.scan_page)
            self.stack.addWidget(self.data_page)
            self.stack.addWidget(self.review_page)
            self.stack.addWidget(self.backup_page)
            self.stack.addWidget(self.bundle_report_page)

            # Connect each page's processing_changed → sync_nav so nav buttons update in real-time.
            for _p in [
                self.welcome_page, self.mode_page, self.scan_page,
                self.data_page, self.review_page, self.backup_page, self.bundle_report_page,
            ]:
                _p.processing_changed.connect(self._sync_nav)
                _p.processing_changed.connect(self._on_any_page_processing_changed)
                # A LayoutRequest from a deeply nested widget (e.g. a choice
                # card's hint label correcting its own height) bubbles up to
                # the page widget itself, not to self.stack — install the
                # filter on each page too so _resize_stack_to_current() gets
                # re-triggered once that settles.
                _p.installEventFilter(self)
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
            self.report_page.request_finish.connect(self._on_finish)
            self.stack.addWidget(self.restore_page)
            self.stack.addWidget(self.verify_page)
            self.stack.addWidget(self.report_page)
            for _p in (self.restore_page, self.verify_page, self.report_page):
                _p.installEventFilter(self)

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
        stepper_scroll.setStyleSheet("QScrollArea { background: #16223D; border: none; } QScrollArea > QWidget { background: #16223D; }")

        self.stack_scroll = QScrollArea()
        self.stack_scroll.setWidgetResizable(True)
        self.stack_scroll.setFrameShape(QFrame.NoFrame)
        self.stack_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.stack_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.stack_scroll.setWidget(self.stack)
        right_layout.addWidget(self.stack_scroll, stretch=1)

        # Bottom navigation — built as its own widget so it can be reparented
        # into the bottom of whichever page's own card is currently showing,
        # instead of floating in a separate bar below the content.
        self.nav_bar = QWidget()
        nav = QHBoxLayout(self.nav_bar)
        nav.setContentsMargins(0, 0, 0, 0)
        nav.setSpacing(10)

        nav.addStretch(1)

        self.back_btn = QPushButton("Back")
        self.back_btn.setProperty("role", "badge")
        self.back_btn.setFixedHeight(38)
        self.back_btn.clicked.connect(self.prev_page)
        nav.addWidget(self.back_btn)

        self.complete_all_btn = QPushButton("Run Automatically")
        self.complete_all_btn.setProperty("role", "badge")
        self.complete_all_btn.setFixedHeight(38)
        self.complete_all_btn.setToolTip(
            "Run the full migration pipeline with default settings — no page-by-page steps needed."
        )
        self.complete_all_btn.clicked.connect(self._run_full_automation)
        self.complete_all_btn.setEnabled(True)
        nav.addWidget(self.complete_all_btn)

        self.next_btn = QPushButton("Next")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedHeight(38)
        self.next_btn.clicked.connect(self.next_page)
        nav.addWidget(self.next_btn)

        nav.addStretch(1)

        # Sidebar | right column, in a splitter spanning the full window
        # height so the dark sidebar isn't cut off below a title bar.
        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setObjectName("MainSplitter")
        content_splitter.setChildrenCollapsible(False)
        content_splitter.setHandleWidth(10)
        content_splitter.addWidget(stepper_scroll)
        content_splitter.addWidget(right_column)
        content_splitter.setStretchFactor(0, 0)
        content_splitter.setStretchFactor(1, 1)
        content_splitter.setSizes([260, 1160])

        root_layout.addWidget(content_splitter, stretch=1)

        # App-wide footer — mode/license status, pinned to the very bottom
        # of the window (spans full width, below the sidebar too) instead of
        # cluttering the per-page nav button row.
        footer = QHBoxLayout()
        footer.setContentsMargins(18, 6, 18, 8)
        footer.setSpacing(8)
        footer.addStretch(1)

        self.mode_badge = QLabel("Mode Status: Guided")
        self.mode_badge.setObjectName("StatusPill")
        self.mode_badge.setToolTip("Current interaction mode status")
        footer.addWidget(self.mode_badge)

        self.commitment_badge = QLabel("License: Open Source")
        self.commitment_badge.setObjectName("StatusPill")
        self.commitment_badge.setToolTip("Project licensing and openness status")
        footer.addWidget(self.commitment_badge)

        footer.addStretch(1)
        root_layout.addLayout(footer)

        self.navigation = NavigationController(
            stack=self.stack,
            stepper=self.stepper,
            back_btn=self.back_btn,
            next_btn=self.next_btn,
            clear_error_banner=self._clear_error_banner,
            is_auto_running=lambda: self.auto_running,
            is_busy=self._is_busy,
            page_to_step=self._PAGE_TO_STEP if self.runtime_mode == "windows" else None,
            show_blocked_message=self._show_blocked_message,
            on_finish=self._on_finish,
        )

        self.stepper.step_clicked.connect(self._on_stepper_step_clicked)
        self.stack.currentChanged.connect(self._sync_nav)

        self.setCentralWidget(root)

        # Right expert panel (dock).
        self.expert_dock = QDockWidget("Customize", self)
        self.expert_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.expert_dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        profile_path = Path(self.config.automation.active_profile_path)
        if not profile_path.is_absolute():
            profile_path = Path(__file__).resolve().parents[2] / profile_path
        self.expert_panel = ExpertPanel(self.ui_state, profile_path=profile_path)
        if hasattr(self, "scan_page"):
            self.expert_panel.on_settings_changed = self.scan_page._sync_settings_selections
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

        # Overlay must be created last so it sits on top of all other children.
        self.overlay = AutomationOverlay(root)

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

    def _show_help(self) -> None:
        current = self.stack.currentWidget()
        page_name = type(current).__name__ if current is not None else ""
        dialog = HelpDialog(page_name, parent=self)
        dialog.exec()

    def _is_busy(self) -> bool:
        return self._busy_count > 0

    def _on_any_page_processing_changed(self, _: bool) -> None:
        any_busy = any(
            getattr(self.stack.widget(i), "is_processing", False)
            for i in range(self.stack.count())
        )
        self.global_scan_bar.setVisible(any_busy)

        if self.auto_running:
            return  # the full-automation flow already owns the overlay
        if any_busy:
            self.overlay.set_subtitle("Please wait")
            self.overlay.set_phase(self._current_page_status_text())
            self.overlay.show()
            self.overlay.raise_()
            # Pages typically call set_scanning(True) and THEN set their
            # status label's text — both within the same call, before
            # control returns to the event loop. Re-read once deferred so
            # the overlay doesn't show whatever stale text was there before
            # this operation started.
            QTimer.singleShot(0, self._refresh_overlay_phase_from_current_page)
        else:
            self.overlay.hide()

    def _current_page_status_text(self) -> str:
        status_label = getattr(self.stack.currentWidget(), "status", None)
        text = status_label.text() if status_label is not None and hasattr(status_label, "text") else ""
        return text or "Working…"

    def _refresh_overlay_phase_from_current_page(self) -> None:
        if self.overlay.isVisible() and not self.auto_running:
            self.overlay.set_phase(self._current_page_status_text())

    def _set_busy(self, busy: bool) -> None:
        self._busy_count = max(0, self._busy_count + (1 if busy else -1))
        self._sync_nav()

    def _set_automation_running(self, running: bool) -> None:
        self.auto_running = running
        self.complete_all_btn.setEnabled(not running)
        self.expert_toggle_btn.setEnabled(not running and self.ui_state.mode != "guided")
        if running:
            self.overlay.set_subtitle("Running migration automatically")
            self.overlay.set_phase("Starting…")
            self.overlay.show()
            self.overlay.raise_()
        else:
            self.overlay.hide()
        self._sync_nav()

    def _run_full_automation(self) -> None:
        if self.auto_running:
            return

        dialog = QMessageBox(self)
        dialog.setWindowTitle("Run Migration Automatically")
        dialog.setText("<b>Run the full pipeline with default settings?</b>")
        dialog.setInformativeText(
            "The following defaults will be applied:<br><br>"
            "&nbsp;&nbsp;<b>Files:</b> Documents, Desktop, Downloads, Pictures (all types)<br>"
            "&nbsp;&nbsp;<b>Appearance:</b> Wallpaper, Theme, Light/Dark mode, Accent colour<br>"
            "&nbsp;&nbsp;<b>Apps:</b> Automatically match all supported apps<br>"
            "&nbsp;&nbsp;<b>Target distro:</b> Linux Mint<br><br>"
            "The pipeline runs in the background — progress is shown on the button. "
            "You can also step through the pages manually to customise any of the above."
        )
        dialog.setStandardButtons(QMessageBox.Cancel | QMessageBox.Ok)
        dialog.button(QMessageBox.Ok).setText("Run with Defaults")
        dialog.setDefaultButton(QMessageBox.Ok)
        if dialog.exec() != QMessageBox.Ok:
            return

        self._apply_default_config()
        self._log_activity("pipeline", "Automatic migration started with default configuration.")
        self._set_automation_running(True)
        self.complete_all_btn.setText("Starting…")
        worker = FunctionWorker(self._complete_full_flow)
        worker.signals.result.connect(self._on_automation_result)
        worker.signals.error.connect(self._on_automation_error)
        worker.signals.finished.connect(self._on_automation_finished)
        self.thread_pool.start(worker)

    def _apply_default_config(self) -> None:
        self.ui_state.settings_migration_enabled = True
        self.ui_state.settings_selected_items = {
            "wallpaper": True,
            "theme": True,
            "light_dark": True,
            "accent_color": True,
            "taskbar_layout": False,
            "keyboard_shortcuts": False,
            "file_associations": False,
        }
        self.ui_state.data_choice_mode = "all_files"
        self.ui_state.selected_folders = {
            "Documents": True,
            "Desktop": True,
            "Downloads": True,
            "Pictures": True,
        }
        self.ui_state.mapping_choice_mode = "migrate_all_supported"
        self.ui_state.target_distro = "Linux Mint"

    def _on_automation_phase(self, phase: str) -> None:
        self.complete_all_btn.setText(phase)
        if phase == "Done":
            self.overlay.hide()
        else:
            self.overlay.set_phase(phase)

    # ── Page↔Step mappings (Windows 7 pages → 5 stepper steps) ──────────────
    #   Page indices:  0=Welcome 1=Mode 2=Scan 3=Data 4=Review 5=Backup 6=Report
    #   Step indices:  0=GetStarted  1=Scan  2=Configure  3=Bundle  4=Report
    _PAGE_TO_STEP: dict[int, int] = {
        0: 0,  # Welcome      → Get Started
        1: 0,  # Mode         → Get Started
        2: 1,  # Scan         → System Scan
        3: 2,  # Data         → Configure
        4: 2,  # Review       → Configure
        5: 3,  # Backup       → Bundle
        6: 4,  # BundleReport → Report
    }
    _STEP_TO_FIRST_PAGE: dict[int, int] = {
        0: 0,  # Get Started  → Welcome
        1: 2,  # System Scan  → Scan
        2: 3,  # Configure    → Data
        3: 5,  # Bundle       → Backup
        4: 6,  # Report       → BundleReport
    }

    # Automation step-name → stepper step index
    _WIN_STEP_MAP: dict[str, int] = {
        "scan": 1,
        "data": 2,
        "review": 2,
        "backup": 3,
    }
    _LIN_STEP_MAP: dict[str, int] = {
        "restore": 0,
        "verification": 1,
        "report": 2,
    }

    def _on_automation_step_done(self, step_name: str) -> None:
        step_map = self._WIN_STEP_MAP if self.runtime_mode == "windows" else self._LIN_STEP_MAP
        idx = step_map.get(step_name)
        if idx is not None and hasattr(self, "stepper"):
            self.stepper.mark_step_done(idx)

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
            on_phase=self.automation_phase.emit,
            on_step_done=self.automation_step_done.emit,
        )

    def _resolve_restore_bundle_dir(self) -> Path:
        def _is_valid_bundle(path: Path) -> bool:
            return (path / "manifest.json").exists() and (
                (path / "backup.zip").exists() or (path / "files").is_dir()
            )

        # Prefer whatever bundle the user already selected on the Restore
        # page (browsed .zip gets auto-extracted there, or an already-
        # unzipped folder) — Run Automatically should pick up from there
        # instead of silently ignoring it.
        selected = getattr(self.restore_page, "bundle_path", None) if hasattr(self, "restore_page") else None
        if selected and _is_valid_bundle(Path(selected)):
            return Path(selected)

        bundle_dir = RESTORE_REPORT.parent
        if _is_valid_bundle(bundle_dir):
            return bundle_dir

        raise RuntimeError(
            "No backup bundle found. Browse to your migration_bundle.zip (or an unzipped "
            "bundle folder) on the Restore page first, or run the Windows backup flow so "
            "manifest.json and files are present in the restore directory."
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

        if "No backup bundle found" in error and hasattr(self, "restore_page"):
            self._clear_error_banner()
            dialog = QMessageBox(self)
            dialog.setWindowTitle("Bundle not found")
            dialog.setIcon(QMessageBox.Warning)
            dialog.setText("<b>Run Automatically couldn't find a migration bundle.</b>")
            dialog.setInformativeText(
                "Go to the Restore Data step and click 'Browse' to select your "
                "migration_bundle.zip (or an already-unzipped bundle folder), "
                "then try Run Automatically again."
            )
            dialog.setStandardButtons(QMessageBox.Ok)
            go_btn = dialog.addButton("Go to Restore Data", QMessageBox.ActionRole)
            dialog.exec()
            if dialog.clickedButton() is go_btn:
                idx = self.stack.indexOf(self.restore_page)
                if idx >= 0:
                    self.stack.setCurrentIndex(idx)
                    self._sync_nav()
            return

        self.error_banner.setText(user_facing_error(error))
        self.error_banner.setVisible(True)

    def _clear_error_banner(self) -> None:
        self.error_banner.setVisible(False)
        self.error_banner.setText("")

    def _on_automation_finished(self) -> None:
        self._set_automation_running(False)
        self.complete_all_btn.setText("Run Automatically")
        self._sync_nav()

    def _on_stepper_step_clicked(self, index: int) -> None:
        if self.navigation is not None:
            page_idx = self._STEP_TO_FIRST_PAGE.get(index, index) if self.runtime_mode == "windows" else index
            self.navigation.go_to_page(page_idx)
        self._sync_expert_page_context()

    def next_page(self) -> None:
        if self.navigation is not None:
            self.navigation.next_page()
        self._sync_expert_page_context()

    def prev_page(self) -> None:
        if self.navigation is not None:
            self.navigation.prev_page()
        self._sync_expert_page_context()

    def _show_blocked_message(self, message: str) -> None:
        QMessageBox.information(self, "Can't continue yet", message)

    def _on_finish(self) -> None:
        verb = "move the bundle to your Linux machine" if self.runtime_mode == "windows" else "close this tool"
        QMessageBox.information(
            self,
            "Migration Complete",
            f"Migration complete. You can now {verb}.",
        )
        self.close()

    def _sync_nav(self) -> None:
        if self.navigation is not None:
            self.navigation.sync_nav()
        current = self.stack.currentWidget()
        hide_automation = isinstance(current, (BackupBundlePage, BundleReportPage))
        self.complete_all_btn.setVisible(not hide_automation)
        self._resize_stack_to_current()
        self._attach_nav_bar_to_current_page()
        self._sync_expert_page_context()

    def _attach_nav_bar_to_current_page(self) -> None:
        """Move the shared nav button bar into the bottom of the current page's own card."""
        current = self.stack.currentWidget()
        card_layout = getattr(current, "card_layout", None)
        if card_layout is None:
            return
        card_layout.addWidget(self.nav_bar)
        # Dynamic-property-styled buttons (role="cta"/"badge") can end up
        # with a stale/blank paint buffer after being reparented into a new
        # widget hierarchy — force a style + repaint refresh.
        for widget in (self.back_btn, self.complete_all_btn, self.next_btn, self.nav_bar):
            style = widget.style()
            style.unpolish(widget)
            style.polish(widget)
            widget.update()

    @staticmethod
    def _fix_wrapped_label_heights(root: QWidget) -> None:
        """Pin every word-wrapped descendant label's minimum height to its
        real heightForWidth() before any ancestor layout computes sizes.
        """
        for label in root.findChildren(QLabel):
            if not label.wordWrap() or label.width() <= 0:
                continue
            needed = label.heightForWidth(label.width())
            if needed > 0 and needed != label.minimumHeight():
                label.setMinimumHeight(needed)

    def _resize_stack_to_current(self) -> None:
        """Shrink-or-grow the page stack to the current page's actual height.

        QScrollArea's widgetResizable mode only ever grows the contained
        widget to fit the viewport — plain resize() calls get silently
        overridden back to the largest size it has ever held. Pinning the
        height via setFixedHeight (which Qt does honor) keeps the scrollable
        range matched to the visible page instead of the tallest page ever
        shown, while never going below the viewport height.
        """
        if getattr(self, "_resizing_stack", False):
            return
        current = self.stack.currentWidget()
        if current is None:
            return
        self._resizing_stack = True
        try:
            # Fix every word-wrapped label's minimum height BEFORE asking any
            # ancestor layout to compute sizes. The propagation-after-the-fact
            # approach (correct a label, then hope updateGeometry() invalidates
            # every ancestor's cached sizeHint) is unreliable through several
            # nested QVBoxLayout levels — each level can keep using a stale
            # snapshot of its child's needs taken before the correction.
            # Fixing all labels first, then doing one fresh activate() pass,
            # sidesteps that ordering problem entirely. The whole method body
            # runs under the _resizing_stack guard since activate() and the
            # label height changes below also post LayoutRequest events that
            # would otherwise re-trigger this same method via the event
            # filter installed on the stack/page.
            self._fix_wrapped_label_heights(current)
            page_layout = current.layout()
            if page_layout is not None:
                page_layout.activate()
            viewport_height = self.stack_scroll.viewport().height()
            if page_layout is not None and page_layout.hasHeightForWidth():
                # current.sizeHint() is unreliable here: Qt's height-for-width
                # propagation through several nested QVBoxLayout levels (choice
                # cards inside a questionnaire frame inside the page) routinely
                # under-reports, silently clipping word-wrapped hint text. Asking
                # the layout directly for its heightForWidth at the actual
                # current width is the accurate path.
                content_height = max(page_layout.heightForWidth(current.width()), current.minimumSizeHint().height())
            else:
                content_height = max(current.sizeHint().height(), current.minimumSizeHint().height())
            target_height = max(content_height, viewport_height)
            if self.stack.height() != target_height:
                self.stack.setFixedHeight(target_height)
        finally:
            self._resizing_stack = False

    def eventFilter(self, obj, event) -> bool:
        # Any descendant page's layout invalidating (a radio toggling a
        # choice card's visibility, mode-dependent widgets appearing, etc.)
        # posts a LayoutRequest up through the ancestor chain to the stack
        # itself — catching it here keeps the card's pinned height in sync
        # with the current page's actual content instead of only updating
        # on page-change. Guarded against recursion since setFixedHeight()
        # below will itself trigger another LayoutRequest.
        is_relevant = obj is self.stack or obj is self.stack.currentWidget()
        if is_relevant and event.type() == QEvent.LayoutRequest and not getattr(self, "_resizing_stack", False):
            # Deferred via singleShot(0): word-wrapped labels inside a
            # freshly toggled choice card report a stale/short sizeHint if
            # queried synchronously here — Qt needs one more event-loop
            # pass to finish the height-for-width reflow first.
            QTimer.singleShot(0, self._resize_stack_to_current)
        return super().eventFilter(obj, event)

    def _sync_expert_page_context(self) -> None:
        if not hasattr(self, "expert_panel"):
            return
        current = self.stack.currentWidget()
        page_key = "mode_selection"
        if isinstance(current, WelcomePage):
            page_key = "welcome"
        elif isinstance(current, ModePage):
            page_key = "mode_selection"
        elif isinstance(current, DataSelectionPage):
            page_key = "data_selection"
        elif isinstance(current, ReviewRecommendationsPage):
            page_key = "review_recommendations"
        elif isinstance(current, ScanPage):
            page_key = "scan"
        elif isinstance(current, BackupBundlePage):
            page_key = "backup_bundle"
        elif isinstance(current, BundleReportPage):
            page_key = "bundle_report"
        elif isinstance(current, RestorePage):
            page_key = "restore"
        elif isinstance(current, VerificationPage):
            page_key = "verification"
        elif isinstance(current, ReportPage):
            page_key = "report"

        self.expert_panel.set_page_context(page_key)

    def _log_activity(self, phase: str, message: str, level: str = "info") -> None:
        self.activity_event.emit(phase, message, level)

    def _on_activity_event(self, phase: str, message: str, level: str) -> None:
        self.activity_log.append(phase=phase, message=message, level=level)

    def closeEvent(self, event) -> None:
        """Disconnect transient signals before Qt destroys child widgets."""
        try:
            self.activity_event.disconnect(self._on_activity_event)
        except Exception:
            pass
        super().closeEvent(event)

    def resizeEvent(self, event) -> None:
        """Re-pin the page stack's height to the current page when the window resizes."""
        super().resizeEvent(event)
        if hasattr(self, "stack_scroll"):
            self._resize_stack_to_current()

    def _mark_action_done(self, action_key: str) -> None:
        self.completed_actions.add(action_key)

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

    def _get_bundle_data(self) -> dict:
        return {
            "manifest": self.runtime_data.get("backup") or {},
            "app_recs": self.runtime_data.get("review_app_recommendations") or {},
            "local_bundle_path": self.ui_state.bundle_archive_path or str(RESTORE_DIR),
            "usb_path": self.ui_state.backup_usb_path,
        }

    def _run_backup(self, cancel_event=None) -> dict | None:
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
            cancel_event=cancel_event,
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
