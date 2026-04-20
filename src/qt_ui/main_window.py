"""Main Qt window that orchestrates the migration workflow."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThreadPool, QTimer, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
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
from src.qt_ui.pages.application_mapping_page import ApplicationMappingPage
from src.qt_ui.pages.backup_bundle_page import BackupBundlePage
from src.qt_ui.pages.data_selection_page import DataSelectionPage
from src.qt_ui.pages.report_page import ReportPage
from src.qt_ui.pages.restore_page import RestorePage
from src.qt_ui.pages.scan_page import ScanPage
from src.qt_ui.pages.mode_page import ModePage
from src.qt_ui.pages.review_recommendations_page import ReviewRecommendationsPage
from src.qt_ui.pages.verification_page import VerificationPage
from src.qt_ui.state import QtUiState
from src.qt_ui.workers import FunctionWorker
from src.qt_ui.widgets.expert_panel import ExpertPanel
from src.qt_ui.widgets.stepper_sidebar import StepperSidebar

from src.orchestration.errors import user_facing_error

from src.services.migration_service import MigrationService
from src.services.pipeline_service import PipelineService
from src.services.recommendation_service import RecommendationService
from src.services.file_recommendation_service import FileRecommendationService
from src.services.report_service import ReportService
from src.services.restore_service import RestoreService
from src.services.validation_service import validate_restore_report


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
        self.thread_pool = QThreadPool.globalInstance()
        self.completed_actions: set[str] = set()
        self.total_actions = 5 if runtime_mode == "windows" else 3
        self.activity_entries: list[dict[str, str]] = []
        self.activity_filters: dict[str, bool] = {
            "info": True,
            "done": True,
            "warn": True,
            "fail": True,
        }

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

        self.expert_toggle_btn = QPushButton("Show Expert Overrides")
        self.expert_toggle_btn.setProperty("role", "badge")
        self.expert_toggle_btn.clicked.connect(self._toggle_expert_panel)
        control_bar.addWidget(self.expert_toggle_btn)

        self.complete_all_btn = QPushButton("Complete All Phases")
        self.complete_all_btn.setProperty("role", "cta")
        self.complete_all_btn.clicked.connect(self._run_full_automation)
        control_bar.addWidget(self.complete_all_btn)
        root_layout.addLayout(control_bar)

        self.error_banner = QLabel("")
        self.error_banner.setObjectName("ErrorBanner")
        self.error_banner.setWordWrap(True)
        self.error_banner.setVisible(False)
        root_layout.addWidget(self.error_banner)

        # Main content with left stepper + page stack.
        content_row = QHBoxLayout()
        content_row.setSpacing(16)
        self.stack = QStackedWidget()

        if self.runtime_mode == "windows":
            self.stepper = StepperSidebar(
                title="Windows Migration Preparation",
                subtitle="Collect inventory, resolve mapping, review recommendations, and produce a migration bundle.",
                steps=[
                    "Mode Selection\nChoose your interaction mode",
                    "Windows Scan\nBrowse and scan",
                    "Data Selection\nSelect your data scope",
                    "Application Mapping\nChoose migration mapping",
                    "Review & Customize\nAcknowledge recommendations",
                    "Create Backup\nReview and confirm",
                ],
            )
            
            self.mode_page = ModePage(self.ui_state)
            self.scan_page = ScanPage(
                self.ui_state,
                run_inventory_cb=self._run_inventory,
                run_recommendations_cb=self._generate_software_recommendations,
            )
            self.data_page = DataSelectionPage(self.ui_state)
            self.mapping_page = ApplicationMappingPage(self.ui_state, run_analysis_cb=self._run_analysis)
            self.review_page = ReviewRecommendationsPage(
                self.ui_state,
                run_app_recommendations_cb=self._run_app_recommendations,
                run_file_recommendations_cb=self._run_file_recommendations,
            )
            self.backup_page = BackupBundlePage(self.ui_state, run_backup_cb=self._run_backup)

            self.mode_page.request_next.connect(self.next_page)
            self.scan_page.request_next.connect(self.next_page)
            self.data_page.request_next.connect(self.next_page)
            self.mapping_page.request_next.connect(self.next_page)
            self.review_page.request_next.connect(self.next_page)
            self.backup_page.request_next.connect(self.next_page)

            self.guided_radio.toggled.connect(self.mode_page.guided_radio.setChecked)
            self.balanced_radio.toggled.connect(self.mode_page.balanced_radio.setChecked)
            self.expert_radio.toggled.connect(self.mode_page.expert_radio.setChecked)

            self.mode_page.guided_radio.toggled.connect(lambda checked: self.guided_radio.setChecked(checked))
            self.mode_page.balanced_radio.toggled.connect(lambda checked: self.balanced_radio.setChecked(checked))
            self.mode_page.expert_radio.toggled.connect(lambda checked: self.expert_radio.setChecked(checked))
            
            self.stack.addWidget(self.mode_page)
            self.stack.addWidget(self.scan_page)
            self.stack.addWidget(self.data_page)
            self.stack.addWidget(self.mapping_page)
            self.stack.addWidget(self.review_page)
            self.stack.addWidget(self.backup_page)
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

        self.stepper.setMinimumWidth(240)
        self.stepper.setMaximumWidth(280)
        self.stack.setMinimumWidth(0)

        content_splitter = QSplitter(Qt.Horizontal)
        content_splitter.setObjectName("MainSplitter")
        content_splitter.setChildrenCollapsible(False)
        content_splitter.setHandleWidth(10)
        content_splitter.addWidget(self.stepper)
        content_splitter.addWidget(self.stack)
        content_splitter.setStretchFactor(0, 0)
        content_splitter.setStretchFactor(1, 1)
        content_splitter.setSizes([245, 920])

        content_row.addWidget(content_splitter, stretch=1)
        root_layout.addLayout(content_row, stretch=1)

        # Live operation console.
        activity_group = QGroupBox("Live Migration Activity")
        activity_group.setObjectName("ActivityGroup")
        activity_layout = QVBoxLayout(activity_group)
        activity_layout.setContentsMargins(12, 12, 12, 12)
        activity_layout.setSpacing(8)

        self.activity_status = QLabel("Pipeline idle. Start a step to see detailed runtime events.")
        self.activity_status.setObjectName("ActivityStatus")
        self.activity_status.setWordWrap(True)
        activity_layout.addWidget(self.activity_status)

        self.pipeline_progress = QProgressBar()
        self.pipeline_progress.setRange(0, 100)
        self.pipeline_progress.setValue(0)
        self.pipeline_progress.setFormat("Overall Progress: %p%")
        self.pipeline_progress.setTextVisible(True)
        activity_layout.addWidget(self.pipeline_progress)

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
        activity_layout.addLayout(filter_row)

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
        activity_layout.addWidget(self.log_filters_panel)

        self.activity_list = QListWidget()
        self.activity_list.setObjectName("ActivityLog")
        self.activity_list.setMinimumHeight(92)
        self.activity_list.setMaximumHeight(136)
        activity_layout.addWidget(self.activity_list)

        # root_layout.addWidget(activity_group)

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

        self.next_btn = QPushButton("Next")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.clicked.connect(self.next_page)
        nav.addWidget(self.next_btn, alignment=Qt.AlignRight)
        root_layout.addLayout(nav)

        self.setCentralWidget(root)

        # Right expert panel (dock).
        self.expert_dock = QDockWidget("Expert Overrides", self)
        self.expert_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.expert_dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        profile_path = Path(self.config.automation.active_profile_path)
        if not profile_path.is_absolute():
            profile_path = Path(__file__).resolve().parents[2] / profile_path
        self.expert_panel = ExpertPanel(self.ui_state, profile_path=profile_path)
        self.expert_dock.setMinimumWidth(360)
        self.expert_dock.setMaximumWidth(460)

        self.expert_scroll = QScrollArea()
        self.expert_scroll.setWidgetResizable(True)
        self.expert_scroll.setFrameShape(QScrollArea.NoFrame)
        self.expert_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.expert_scroll.setWidget(self.expert_panel)

        self.expert_dock.setWidget(self.expert_scroll)
        self.addDockWidget(Qt.RightDockWidgetArea, self.expert_dock)
        self.expert_dock.hide()

        self._log_activity("system", "Application initialized. Waiting for action.")

    def _on_mode_change(self, value: str) -> None:
        self.ui_state.mode = value
        self.mode_badge.setText(f"Mode Status: {value.capitalize()}")
        self._apply_mode_presentation(value)
        self._log_activity("system", f"Interaction mode changed to {value}.")
        for i in range(self.stack.count()):
            page = self.stack.widget(i)
            refresh = getattr(page, "refresh", None)
            if callable(refresh):
                refresh()

    def _apply_mode_presentation(self, mode: str) -> None:
        self.expert_panel.apply_mode(mode)

        if mode == "guided":
            if self.expert_dock.isVisible():
                self.expert_dock.hide()
            self.ui_state.expert_panel_visible = False
            self.expert_toggle_btn.setText("Show Expert Overrides")
            self.expert_toggle_btn.setEnabled(False)
            self.complete_all_btn.setEnabled(False)
            # self.toggle_filters_btn.setEnabled(False)
            # self.log_filters_panel.setVisible(False)
            # self.export_log_btn.setEnabled(False)
            return

        if mode == "expert":
            if not self.expert_dock.isVisible():
                self.expert_dock.show()
            self.ui_state.expert_panel_visible = True
            self.expert_toggle_btn.setText("Hide Expert Overrides")
            self.expert_toggle_btn.setEnabled(True)
            self.complete_all_btn.setEnabled(True)
            # self.toggle_filters_btn.setEnabled(True)
            # self.export_log_btn.setEnabled(True)
            return

        # balanced mode keeps manual control, defaulting to hidden expert panel
        if self.expert_dock.isVisible() and not self.ui_state.expert_panel_visible:
            self.expert_dock.hide()
        self.expert_toggle_btn.setEnabled(True)
        self.complete_all_btn.setEnabled(True)
        # self.toggle_filters_btn.setEnabled(True)
        # self.export_log_btn.setEnabled(True)
        self.expert_toggle_btn.setText("Hide Expert Overrides" if self.expert_dock.isVisible() else "Show Expert Overrides")

    def _toggle_expert_panel(self) -> None:
        if self.ui_state.mode == "guided":
            return
        if self.expert_dock.isVisible():
            self.expert_dock.hide()
            self.ui_state.expert_panel_visible = False
            self.expert_toggle_btn.setText("Show Expert Overrides")
        else:
            self.expert_dock.show()
            self.ui_state.expert_panel_visible = True
            self.expert_toggle_btn.setText("Hide Expert Overrides")

    def _set_automation_running(self, running: bool) -> None:
        self.auto_running = running
        self.complete_all_btn.setEnabled(not running and self.ui_state.mode != "guided")
        self.expert_toggle_btn.setEnabled(not running and self.ui_state.mode != "guided")
        self.back_btn.setEnabled(not running and self.stack.currentIndex() > 0)
        self.next_btn.setEnabled(not running and self.stack.currentIndex() < self.stack.count() - 1)
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
        if self.runtime_mode == "windows":
            inventory = self._run_inventory()
            self.ui_state.inventory_completed = True

            analysis = self._run_analysis()
            self.ui_state.analysis_completed = True

            app_recs = self._run_app_recommendations()
            file_recs = self._run_file_recommendations()

            backup = self._run_backup()
            self.ui_state.backup_completed = backup is not None

            return {
                "mode": "windows",
                "inventory": inventory,
                "analysis": analysis,
                "app_recommendations": app_recs,
                "file_recommendations": file_recs,
                "backup": backup,
            }

        bundle_dir = self._resolve_restore_bundle_dir()
        restore = self._run_restore(bundle_dir)
        self.ui_state.restore_completed = True

        validation = self._run_validation()
        self.ui_state.verification_completed = True

        report = self._generate_final_report()

        return {
            "mode": "linux",
            "restore": restore,
            "validation": validation,
            "report": report,
        }

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

    def next_page(self) -> None:
        if self.auto_running:
            return
        self._clear_error_banner()
        current = self.stack.currentIndex()
        if current < self.stack.count() - 1:
            self.stack.setCurrentIndex(current + 1)
            page = self.stack.currentWidget()
            refresh = getattr(page, "refresh", None)
            if callable(refresh):
                refresh()
            self._sync_nav()

    def prev_page(self) -> None:
        if self.auto_running:
            return
        self._clear_error_banner()
        current = self.stack.currentIndex()
        if current > 0:
            self.stack.setCurrentIndex(current - 1)
            self._sync_nav()

    def _sync_nav(self) -> None:
        current = self.stack.currentIndex()
        if not self.auto_running:
            self.back_btn.setEnabled(current > 0)
            self.next_btn.setEnabled(current < self.stack.count() - 1)
        self.stepper.set_active_index(current)
        if current == self.stack.count() - 1:
            self.next_btn.setText("Done")
        else:
            self.next_btn.setText("Next")

    def _toggle_log_filters(self) -> None:
        if self.ui_state.mode == "guided":
            return
        # new_state = not self.log_filters_panel.isVisible()
        # self.log_filters_panel.setVisible(new_state)
        # self.toggle_filters_btn.setText("Hide Log Filters" if new_state else "Show Log Filters")

    def _set_log_filter(self, key: str, enabled: bool) -> None:
        self.activity_filters[key] = enabled
        self._refresh_activity_log()


    # --------------------------------------------------------------------
    def _set_loading_progress(self, progress: int) -> None:
        self.pipeline_progress.setValue(progress)

    @staticmethod
    def _level_to_badge(level: str) -> str:
        norm = level.lower()
        if norm in {"success", "done"}:
            return "DONE"
        if norm in {"warn", "warning"}:
            return "WARN"
        if norm in {"error", "fail"}:
            return "FAIL"
        return "INFO"

    @staticmethod
    def _phase_to_icon(phase: str) -> str:
        return {
            "system": "SYS",
            "pipeline": "PIP",
            "inventory": "INV",
            "analysis": "MAP",
            "backup": "BKP",
            "restore": "RST",
            "validation": "VAL",
            "report": "RPT",
        }.get(phase.lower(), "LOG")

    @staticmethod
    def _badge_to_level_key(badge: str) -> str:
        key = badge.lower()
        if key == "done":
            return "done"
        if key == "warn":
            return "warn"
        if key == "fail":
            return "fail"
        return "info"

    def _badge_color(self, badge: str) -> QColor:
        return {
            "DONE": QColor("#70e0a1"),
            "WARN": QColor("#ffd96d"),
            "FAIL": QColor("#ff9090"),
            "INFO": QColor("#9ad7f7"),
        }.get(badge, QColor("#9ad7f7"))

    def _refresh_activity_log(self) -> None:
        # self.activity_list.clear()
        for entry in reversed(self.activity_entries):
            badge = entry.get("badge", "INFO")
            level_key = self._badge_to_level_key(badge)
            if not self.activity_filters.get(level_key, True):
                continue

            item = QListWidgetItem(
                f"[{entry.get('time', '--:--:--')}] [{badge}] [{entry.get('icon', 'LOG')}] {entry.get('phase', '').upper()}: {entry.get('message', '')}"
            )
            item.setForeground(self._badge_color(badge))
            # self.activity_list.addItem(item)

        # while self.activity_list.count() > 220:
        #     self.activity_list.takeItem(self.activity_list.count() - 1)

    def _export_session_log(self) -> None:
        if self.ui_state.mode == "guided":
            self._log_activity("report", "Session log export is available in Balanced and Expert modes.", level="warn")
            return

        reports_dir = Path(__file__).resolve().parents[2] / "docs" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = reports_dir / f"session_activity_log_{stamp}.json"
        md_path = reports_dir / f"session_activity_log_{stamp}.md"

        payload = {
            "generated_at": datetime.now().isoformat(),
            "runtime_mode": self.runtime_mode,
            "entries": self.activity_entries,
        }

        try:
            json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            lines = [
                "# Session Activity Log",
                "",
                f"Generated at: {payload['generated_at']}",
                f"Runtime mode: {self.runtime_mode}",
                "",
                "| Time | Badge | Phase | Message |",
                "|---|---|---|---|",
            ]
            for entry in self.activity_entries:
                lines.append(
                    f"| {entry.get('time', '--:--:--')} | {entry.get('badge', 'INFO')} | {entry.get('phase', '').upper()} | {entry.get('message', '').replace('|', '/')} |"
                )
            md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            self._log_activity("report", f"Session log exported to {md_path}", level="success")
        except Exception as exc:
            self._log_activity("report", f"Session log export failed: {exc}", level="error")

    def _log_activity(self, phase: str, message: str, level: str = "info") -> None:
        self.activity_event.emit(phase, message, level)

    def _on_activity_event(self, phase: str, message: str, level: str) -> None:
        badge = self._level_to_badge(level)
        icon = self._phase_to_icon(phase)
        ts = datetime.now().strftime("%H:%M:%S")
        self.activity_entries.append(
            {
                "time": ts,
                "badge": badge,
                "icon": icon,
                "phase": phase,
                "message": message,
            }
        )
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
        if self.runtime_mode != "windows":
            raise RuntimeError("Inventory is only available in Windows pre-migration mode.")
        self._clear_error_banner()
        scan_label = "deep" if deep_scan else "quick"
        self._log_activity("inventory", f"Starting {scan_label} hardware and software inventory scan...")
        result = self.migration_service.run_inventory(deep_scan=deep_scan)
        self.runtime_data["inventory"] = result
        sw_entries = len(result.get("software", {}).get("entries", []))
        hw_keys = len(result.get("hardware", {}).keys())
        if deep_scan:
            deep_summary = result.get("software", {}).get("deep_scan_summary", {})
            self._log_activity(
                "inventory",
                "Deep inventory completed: "
                f"hardware={hw_keys}, registry_apps={sw_entries}, "
                f"pkg_mgr={deep_summary.get('package_manager_entries', 0)}, "
                f"appx={deep_summary.get('appx_entries', 0)}.",
                level="success",
            )
        else:
            self._log_activity(
                "inventory",
                f"Inventory completed: {hw_keys} hardware categories, {sw_entries} software entries.",
                level="success",
            )
        self._mark_action_done("inventory")
        return result

    def _generate_software_recommendations(self, strategy: str = "local", selection_profile: str = "migrate_all") -> dict:
        if self.runtime_mode != "windows":
            raise RuntimeError("Software recommendations are available in Windows pre-migration mode only.")
        if self.ui_state.mode != "expert":
            raise RuntimeError("Switch to expert mode to generate advanced software recommendations.")

        inventory = self.runtime_data.get("inventory")
        if not inventory:
            inventory = self._run_inventory(deep_scan=False)

        software_inventory = inventory.get("software", {}) if isinstance(inventory, dict) else {}
        effective_profile = selection_profile or self.ui_state.recommendation_strategy
        self._log_activity("analysis", f"Generating {strategy} software recommendations ({effective_profile})...")
        result = self.recommendation_service.generate_recommendations(
            software_inventory=software_inventory,
            strategy=strategy,
            selection_profile=effective_profile,
        )
        self.runtime_data[f"recommendations_{strategy}_{effective_profile}"] = result
        self._log_activity(
            "analysis",
            f"{strategy.capitalize()} ({effective_profile}) recommendation report created: {result.get('markdown_path', '')}",
            level="success",
        )
        return result

    def _run_app_recommendations(self) -> dict:
        """Generate app-level recommendations for review page."""
        if self.runtime_mode != "windows":
            raise RuntimeError("App recommendations are only available in Windows pre-migration mode.")

        inventory = self.runtime_data.get("inventory")
        if not inventory:
            inventory = self._run_inventory(deep_scan=False)

        software_inventory = inventory.get("software", {}) if isinstance(inventory, dict) else {}
        strategy = "agent" if self.ui_state.mode == "expert" else "local"
        selection_profile = self.ui_state.recommendation_strategy

        self._log_activity("recommendations", f"Generating {strategy} app recommendations ({selection_profile})...")
        result = self.recommendation_service.generate_recommendations(
            software_inventory=software_inventory,
            strategy=strategy,
            selection_profile=selection_profile,
        )
        self.runtime_data["review_app_recommendations"] = result
        self._log_activity(
            "recommendations",
            f"App recommendations ready: {result.get('recommended_count', 0)} apps",
            level="success",
        )
        return result

    def _run_file_recommendations(self) -> dict:
        """Generate file-level recommendations for review page."""
        if self.runtime_mode != "windows":
            raise RuntimeError("File recommendations are only available in Windows pre-migration mode.")

        # For now, return placeholder; file inventory integration would be added when file scanning is available
        choice_mode = self.ui_state.data_choice_mode
        self._log_activity("recommendations", f"Generating file recommendations ({choice_mode})...")

        result = self.file_recommendation_service.generate_recommendations(
            file_inventory={"files": []},  # Placeholder; would use actual file scan from inventory
            choice_mode=choice_mode,
            use_ai=self.ui_state.mode == "expert",
            ai_config=self._get_ai_config(),
        )
        self.runtime_data["review_file_recommendations"] = result
        self._log_activity(
            "recommendations",
            f"File recommendations ready: {result.get('recommended_count', 0)} files",
            level="success",
        )
        return result

    def _get_ai_config(self) -> dict:
        """Retrieve AI configuration from config or environment."""
        ai_cfg = self.config.ai
        return {
            "enabled": ai_cfg.enabled,
            "endpoint": ai_cfg.endpoint or "",
            "model": ai_cfg.model or "",
            "api_key": ai_cfg.api_key or "",
            "temperature": ai_cfg.temperature,
            "timeout_seconds": ai_cfg.timeout_seconds,
        }

    def _run_analysis(self) -> dict:
        if self.runtime_mode != "windows":
            raise RuntimeError("Analysis is only available in Windows pre-migration mode.")
        self._clear_error_banner()
        self._log_activity("analysis", "Generating compatibility matrix and software mapping...")
        inv = self.runtime_data.get("inventory")
        if not inv:
            inv = self._run_inventory()
        result = self.migration_service.run_analysis(
            sw_inventory=inv.get("software", {}),
            hw_inventory=inv.get("hardware", {}),
        )
        self.runtime_data["analysis"] = result
        mapped = len(result.get("software", []))
        hw_rows = len(result.get("hardware", []))
        self._log_activity(
            "analysis",
            f"Analysis completed: {hw_rows} hardware advisories, {mapped} software mapping rows.",
            level="success",
        )
        self._mark_action_done("analysis")
        return result

    def _run_backup(self) -> dict | None:
        if self.runtime_mode != "windows":
            raise RuntimeError("Backup is only available in Windows pre-migration mode.")
        self._clear_error_banner()
        selected_folders = self._resolve_selected_folders()
        selected_file_types = self.config.source_system.file_types
        self._log_activity(
            "backup",
            f"Creating bundle from {len(selected_folders)} folder scope(s) and selected file filters...",
        )
        result = self.migration_service.run_backup(selected_folders, selected_file_types)
        self.runtime_data["backup"] = result
        files = int(result.get("total_files", 0)) if isinstance(result, dict) else 0
        self._log_activity(
            "backup",
            f"Backup bundle completed. Manifest entries: {files}.",
            level="success",
        )
        self._mark_action_done("backup")
        return result

    def _resolve_selected_folders(self) -> list[str]:
        custom = [p for p in self.ui_state.custom_paths if p]
        if self.ui_state.data_strategy == "keep_all":
            combined = list(self.config.source_system.backup_paths) + custom
            return list(dict.fromkeys(combined))

        selected = [
            f"~/{name}"
            for name, enabled in self.ui_state.selected_folders.items()
            if enabled
        ]
        selected.extend(custom)
        if selected:
            return list(dict.fromkeys(selected))
        combined = list(self.config.source_system.backup_paths) + custom
        return list(dict.fromkeys(combined))

    def _run_restore(self, bundle_dir: Path) -> dict:
        if self.runtime_mode != "linux":
            raise RuntimeError("Restore is only available in Linux migration mode.")
        self._clear_error_banner()
        self._log_activity("restore", f"Starting restore from bundle: {bundle_dir}")

        last_progress = {"value": -10}

        def progress_cb(percent: int, msg: str) -> None:
            if percent == 100 or percent - last_progress["value"] >= 10:
                last_progress["value"] = percent
                self._log_activity("restore", f"{msg} ({percent}%)")

        target_home = Path.home() / "Restored_Migration"
        service = RestoreService(
            bundle_dir=bundle_dir,
            target_home=target_home,
            progress_cb=progress_cb,
            target_distro=self.config.target_system.distro,
        )
        service.run_restore()
        self.runtime_data["restore"] = {
            "target_home": str(target_home),
            "bundle_dir": str(bundle_dir),
            "report_path": str(service.report_path),
        }
        self.ui_state.restore_completed = True
        self._log_activity("restore", f"Restore completed. Report written to {service.report_path}", level="success")
        self._mark_action_done("restore")
        return self.runtime_data["restore"]

    def _run_validation(self) -> dict:
        self._clear_error_banner()
        self._log_activity("validation", "Running integrity and sovereignty validation checks...")
        summary = validate_restore_report(RESTORE_REPORT)
        self.runtime_data["verification"] = summary
        self.ui_state.verification_completed = True
        self._log_activity(
            "validation",
            f"Validation complete. Score={summary.get('total_sovereignty_score', 0)}%, files={summary.get('total_files', 0)}.",
            level="success",
        )
        self._mark_action_done("validation")
        return summary

    def _generate_final_report(self) -> dict:
        self._clear_error_banner()
        self._log_activity("report", "Compiling final report artifacts (JSON, Markdown, HTML)...")
        result = self.report_service.generate_report()
        self.runtime_data["report"] = result.get("report", {})
        self._log_activity(
            "report",
            f"Report completed: {result.get('markdown_path', '')}",
            level="success",
        )
        self._mark_action_done("report")
        return result

    @staticmethod
    def _format_size(num_bytes: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(num_bytes)
        for unit in units:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
