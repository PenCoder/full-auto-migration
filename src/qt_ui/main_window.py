from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.constants import RESTORE_REPORT
from src.config import MigrationConfigRoot
from src.qt_ui.pages.application_mapping_page import ApplicationMappingPage
from src.qt_ui.pages.backup_bundle_page import BackupBundlePage
from src.qt_ui.pages.data_selection_page import DataSelectionPage
from src.qt_ui.pages.restore_page import RestorePage
from src.qt_ui.pages.scan_page import ScanPage
from src.qt_ui.pages.verification_page import VerificationPage
from src.qt_ui.state import QtUiState
from src.qt_ui.workers import FunctionWorker
from src.qt_ui.widgets.expert_panel import ExpertPanel
from src.qt_ui.widgets.stepper_sidebar import StepperSidebar
from src.services.migration_service import MigrationService
from src.services.restore_service import RestoreService


class QtMigrationWindow(QMainWindow):
    def __init__(self, config: MigrationConfigRoot, runtime_mode: str) -> None:
        super().__init__()
        self.config = config
        self.runtime_mode = runtime_mode
        self.ui_state = QtUiState()
        self.runtime_data: dict[str, object] = {}
        self.auto_running = False
        self.thread_pool = QThreadPool.globalInstance()

        self.migration_service = MigrationService(config=self.config, context={})

        self.setWindowTitle("Sovereignty Migration Platform (Qt)")
        self.resize(1360, 820)
        self.setMinimumSize(1160, 700)

        self._build_ui()
        self._sync_nav()

    def _build_ui(self) -> None:
        root = QWidget(self)
        root.setObjectName("RootSurface")
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 14, 18, 12)
        root_layout.setSpacing(12)

        # Title bar.
        top_bar = QHBoxLayout()
        title = QLabel("Sovereignty Migration Platform")
        title.setObjectName("AppTitle")
        top_bar.addStretch(1)
        top_bar.addWidget(title)
        top_bar.addStretch(1)
        root_layout.addLayout(top_bar)

        # Controls row.
        control_bar = QHBoxLayout()
        control_bar.addStretch(1)
        control_bar.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["guided", "balanced", "expert"])
        self.mode_combo.currentTextChanged.connect(self._on_mode_change)
        control_bar.addWidget(self.mode_combo)

        self.expert_toggle_btn = QPushButton("Show Expert Overrides")
        self.expert_toggle_btn.setProperty("role", "badge")
        self.expert_toggle_btn.clicked.connect(self._toggle_expert_panel)
        control_bar.addWidget(self.expert_toggle_btn)

        self.complete_all_btn = QPushButton("Complete All Phases")
        self.complete_all_btn.setProperty("role", "cta")
        self.complete_all_btn.clicked.connect(self._run_full_automation)
        control_bar.addWidget(self.complete_all_btn)
        root_layout.addLayout(control_bar)

        # Main content with left stepper + page stack.
        content_row = QHBoxLayout()
        content_row.setSpacing(16)
        self.stack = QStackedWidget()

        if self.runtime_mode == "windows":
            self.stepper = StepperSidebar(
                title="Example with Steps UI",
                subtitle="Follow the simple 4 steps to complete migration prep.",
                steps=[
                    "Windows Scan\nBrowse and scan",
                    "Data Selection\nSelect your data scope",
                    "Application Mapping\nChoose migration mapping",
                    "Create Backup\nReview and confirm",
                ],
            )
            self.scan_page = ScanPage(self.ui_state, run_inventory_cb=self._run_inventory)
            self.data_page = DataSelectionPage(self.ui_state)
            self.mapping_page = ApplicationMappingPage(self.ui_state, run_analysis_cb=self._run_analysis)
            self.backup_page = BackupBundlePage(self.ui_state, run_backup_cb=self._run_backup)

            self.scan_page.request_next.connect(self.next_page)
            self.data_page.request_next.connect(self.next_page)
            self.mapping_page.request_next.connect(self.next_page)
            self.backup_page.request_next.connect(self.next_page)

            self.stack.addWidget(self.scan_page)
            self.stack.addWidget(self.data_page)
            self.stack.addWidget(self.mapping_page)
            self.stack.addWidget(self.backup_page)
        else:
            self.stepper = StepperSidebar(
                title="Migration Steps",
                subtitle="Follow the 2 Linux-side steps to finalize migration.",
                steps=[
                    "Restore Data\nStart restoration",
                    "Validation\nReview and verify",
                ],
            )
            self.restore_page = RestorePage(self.ui_state, run_restore_cb=self._run_restore)
            self.verify_page = VerificationPage(self.ui_state, run_validation_cb=self._run_validation)

            self.restore_page.request_next.connect(self.next_page)
            self.stack.addWidget(self.restore_page)
            self.stack.addWidget(self.verify_page)

        self.stepper.setFixedWidth(260)
        content_row.addWidget(self.stepper)
        content_row.addWidget(self.stack, stretch=1)
        root_layout.addLayout(content_row, stretch=1)

        # Bottom navigation.
        nav = QHBoxLayout()
        self.mode_badge = QLabel("Novice Mode")
        self.mode_badge.setObjectName("FooterBadge")
        nav.addWidget(self.mode_badge)

        self.back_btn = QPushButton("Back")
        self.back_btn.setProperty("role", "badge")
        self.back_btn.clicked.connect(self.prev_page)
        nav.addWidget(self.back_btn)

        self.commitment_badge = QLabel("Open Source Commitment")
        self.commitment_badge.setObjectName("FooterBadge")
        nav.addWidget(self.commitment_badge)

        self.next_btn = QPushButton("Next")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.clicked.connect(self.next_page)
        nav.addStretch(1)
        nav.addWidget(self.next_btn)
        root_layout.addLayout(nav)

        self.setCentralWidget(root)

        # Right expert panel (dock).
        self.expert_dock = QDockWidget("Expert Overrides", self)
        self.expert_dock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.expert_panel = ExpertPanel(self.ui_state)
        self.expert_dock.setWidget(self.expert_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.expert_dock)
        self.expert_dock.hide()

    def _on_mode_change(self, value: str) -> None:
        self.ui_state.mode = value
        self.mode_badge.setText(f"{value.capitalize()} Mode")
        for i in range(self.stack.count()):
            page = self.stack.widget(i)
            refresh = getattr(page, "refresh", None)
            if callable(refresh):
                refresh()

    def _toggle_expert_panel(self) -> None:
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
        self.complete_all_btn.setEnabled(not running)
        self.expert_toggle_btn.setEnabled(not running)
        self.back_btn.setEnabled(not running and self.stack.currentIndex() > 0)
        self.next_btn.setEnabled(not running and self.stack.currentIndex() < self.stack.count() - 1)

    def _run_full_automation(self) -> None:
        if self.auto_running:
            return

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

            backup = self._run_backup()
            self.ui_state.backup_completed = backup is not None

            return {
                "mode": "windows",
                "inventory": inventory,
                "analysis": analysis,
                "backup": backup,
            }

        bundle_dir = self._resolve_restore_bundle_dir()
        restore = self._run_restore(bundle_dir)
        self.ui_state.restore_completed = True

        validation = self._run_validation()
        self.ui_state.verification_completed = True

        return {
            "mode": "linux",
            "restore": restore,
            "validation": validation,
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
            self.stack.setCurrentIndex(self.stack.count() - 1)
            current = self.stack.currentWidget()
            refresh = getattr(current, "refresh", None)
            if callable(refresh):
                refresh()
            self._sync_nav()

    def _on_automation_error(self, error: str) -> None:
        self.ui_state.last_error = error

    def _on_automation_finished(self) -> None:
        self._set_automation_running(False)
        self.complete_all_btn.setText("Complete All Phases")
        self._sync_nav()

    def next_page(self) -> None:
        if self.auto_running:
            return
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

    def _run_inventory(self) -> dict:
        if self.runtime_mode != "windows":
            raise RuntimeError("Inventory is only available in Windows pre-migration mode.")
        result = self.migration_service.run_inventory()
        self.runtime_data["inventory"] = result
        return result

    def _run_analysis(self) -> dict:
        if self.runtime_mode != "windows":
            raise RuntimeError("Analysis is only available in Windows pre-migration mode.")
        inv = self.runtime_data.get("inventory")
        if not inv:
            inv = self._run_inventory()
        result = self.migration_service.run_analysis(
            sw_inventory=inv.get("software", {}),
            hw_inventory=inv.get("hardware", {}),
        )
        self.runtime_data["analysis"] = result
        return result

    def _run_backup(self) -> dict | None:
        if self.runtime_mode != "windows":
            raise RuntimeError("Backup is only available in Windows pre-migration mode.")
        selected_folders = self._resolve_selected_folders()
        selected_file_types = self.config.source_system.file_types
        result = self.migration_service.run_backup(selected_folders, selected_file_types)
        self.runtime_data["backup"] = result
        return result

    def _resolve_selected_folders(self) -> list[str]:
        if self.ui_state.data_strategy == "keep_all":
            return list(self.config.source_system.backup_paths)

        selected = [
            f"~/{name}"
            for name, enabled in self.ui_state.selected_folders.items()
            if enabled
        ]
        if selected:
            return selected
        return list(self.config.source_system.backup_paths)

    def _run_restore(self, bundle_dir: Path) -> dict:
        if self.runtime_mode != "linux":
            raise RuntimeError("Restore is only available in Linux migration mode.")

        target_home = Path.home() / "Restored_Migration"
        service = RestoreService(bundle_dir=bundle_dir, target_home=target_home)
        service.run_restore()
        self.runtime_data["restore"] = {
            "target_home": str(target_home),
            "bundle_dir": str(bundle_dir),
        }
        self.ui_state.restore_completed = True
        return self.runtime_data["restore"]

    def _run_validation(self) -> dict:
        if not RESTORE_REPORT.exists():
            raise RuntimeError("restore_report.json not found. Run restore first.")

        with RESTORE_REPORT.open(encoding="utf-8") as f:
            report = json.load(f)

        files = report.get("files_restored", [])
        apps = report.get("applications_installed", [])

        restored_count = 0
        restored_bytes = 0
        for item in files:
            path = Path(item.get("destination", ""))
            if path.exists() and path.is_file():
                restored_count += 1
                try:
                    restored_bytes += path.stat().st_size
                except OSError:
                    pass

        total_files = len(files)
        integrity_score = int((restored_count / total_files) * 100) if total_files else 100
        openness_bonus = 15 if apps else 5
        total_score = min(100, integrity_score + openness_bonus)

        summary = {
            "report_path": str(RESTORE_REPORT),
            "total_files": total_files,
            "restored_files": restored_count,
            "apps_mapped": len(apps),
            "restored_data_size": self._format_size(restored_bytes),
            "total_sovereignty_score": total_score,
        }
        self.runtime_data["verification"] = summary
        self.ui_state.verification_completed = True
        return summary

    @staticmethod
    def _format_size(num_bytes: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(num_bytes)
        for unit in units:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
