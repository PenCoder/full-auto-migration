"""Scan page for inventory collection and recommendation generation."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QRadioButton

from src.orchestration.errors import user_facing_error
from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker


class ScanPage(BasePage):
    """Collect inventory and generate app-level recommendation previews."""

    def __init__(
        self,
        ui_state,
        run_inventory_cb: Callable[[bool], dict],
        run_recommendations_cb: Callable[[str, str], dict],
        current_step: int = 0,
        step_names: list[str] | None = None,
    ) -> None:
        super().__init__(ui_state)
        self.run_inventory_cb = run_inventory_cb
        self.run_recommendations_cb = run_recommendations_cb
        self.current_step = current_step
        self.step_names = step_names or ["Scan", "Data Selection", "Application Mapping", "Backup"]
        self.thread_pool = QThreadPool.globalInstance()
        self.is_running = False
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        question = "Would you want to migrate all supported applications or prioritize customizing which applications to migrate?"
        info = (
            "• You can choose to move all supported applications or customize which ones to prioritize. <br>"
            + "• We recommend prioritizing applications you use daily or that are critical for work to ensure a smooth transition."
        )

        self.migrate_all_radio = QRadioButton("Migrate All Supported Applications")
        self.prioritize_radio = QRadioButton("Prioritize Custom Selection")
        
        guided_panel = self.create_guided_questionnaire(
            question,
            info,
            options=[self.migrate_all_radio, self.prioritize_radio],
        )
        root.addWidget(guided_panel)

        if self.ui_state.recommendation_strategy == "prioritize":
            self.prioritize_radio.setChecked(True)
        else:
            self.migrate_all_radio.setChecked(True)

        self.recommendation_profile = QLabel("")
        self.recommendation_profile.setObjectName("BodyText")
        self.recommendation_profile.setWordWrap(True)
        self.recommendation_profile.setAlignment(Qt.AlignCenter)
        root.addWidget(self.recommendation_profile)

        self.status = QLabel("Run Quick Scan to collect hardware_inventory.json and software_inventory.json.")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        scan_row = QHBoxLayout()
        scan_row.setSpacing(10)

        self.quick_scan_btn = QPushButton("Quick Scan")
        self.quick_scan_btn.setProperty("role", "primary")
        self.quick_scan_btn.setFixedWidth(200)
        self.quick_scan_btn.clicked.connect(lambda: self._run_scan(deep_scan=False))
        scan_row.addWidget(self.quick_scan_btn)

        self.deep_scan_btn = QPushButton("Deep Scan")
        self.deep_scan_btn.setProperty("role", "primary")
        self.deep_scan_btn.setFixedWidth(200)
        self.deep_scan_btn.clicked.connect(lambda: self._run_scan(deep_scan=True))
        scan_row.addWidget(self.deep_scan_btn)

        root.addLayout(scan_row)

        rec_row = QHBoxLayout()
        rec_row.setSpacing(10)

        self.online_rec_btn = QPushButton("Recommend (Online)")
        self.online_rec_btn.setProperty("role", "badge")
        self.online_rec_btn.setMinimumHeight(42)
        self.online_rec_btn.setFixedWidth(200)
        self.online_rec_btn.clicked.connect(lambda: self._run_recommendations("online"))
        rec_row.addWidget(self.online_rec_btn)

        self.agent_rec_btn = QPushButton("Recommend (Agent)")
        self.agent_rec_btn.setProperty("role", "badge")
        self.agent_rec_btn.setMinimumHeight(42)
        self.agent_rec_btn.setFixedWidth(200)
        self.agent_rec_btn.clicked.connect(lambda: self._run_recommendations("agent"))
        rec_row.addWidget(self.agent_rec_btn)

        root.addLayout(rec_row)

        # self.next_btn = QPushButton("Continue")
        # self.next_btn.setProperty("role", "cta")
        # self.next_btn.setFixedWidth(200)
        # self.next_btn.clicked.connect(self.request_next.emit)
        # root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

        self.prioritize_radio.toggled.connect(self._on_priority_toggled)
        self.migrate_all_radio.toggled.connect(self._on_migrate_all_toggled)

    def _on_priority_toggled(self, checked: bool) -> None:
        if checked:
            self.ui_state.recommendation_strategy = "prioritize"
            self.refresh()

    def _on_migrate_all_toggled(self, checked: bool) -> None:
        if checked:
            self.ui_state.recommendation_strategy = "migrate_all"
        else:
            return
        self.refresh()

    def _set_running_state(self, running: bool) -> None:
        self.is_running = running
        self.quick_scan_btn.setEnabled(not running)
        self.deep_scan_btn.setEnabled(not running)
        self.online_rec_btn.setEnabled(not running)
        self.agent_rec_btn.setEnabled(not running)
        # self.next_btn.setEnabled(False)

    def _run_scan(self, deep_scan: bool) -> None:
        self._set_running_state(True)
        self.loading.setVisible(True)
        if deep_scan:
            self.status.setText("Running deep scan: registry, package managers, AppX, and startup inventory...")
            worker = FunctionWorker(lambda: self.run_inventory_cb(True))
        else:
            self.status.setText("Running quick scan: hardware and software inventory...")
            worker = FunctionWorker(lambda: self.run_inventory_cb(False))
        worker.signals.result.connect(self._on_scan_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self.thread_pool.start(worker)

    def _run_recommendations(self, strategy: str) -> None:
        self._set_running_state(True)
        self.loading.setVisible(True)
        if strategy == "agent":
            self.status.setText("Agent recommendation mode: scoring Linux package alternatives...")
        else:
            self.status.setText("Online recommendation mode: validating package signals...")
        preference = self.ui_state.recommendation_strategy
        worker = FunctionWorker(lambda: self.run_recommendations_cb(strategy, preference))
        worker.signals.result.connect(self._on_recommendation_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self.thread_pool.start(worker)

    def _on_scan_result(self, result: object) -> None:
        if isinstance(result, dict):
            self.ui_state.inventory_completed = True
            hw = len(result.get("hardware", {}).keys())
            sw = len(result.get("software", {}).get("entries", []))
            scan_depth = result.get("software", {}).get("scan_depth", "quick")
            if scan_depth == "deep":
                deep = result.get("software", {}).get("deep_scan_summary", {})
                self.status.setText(
                    "Deep scan completed. "
                    f"Hardware categories: {hw}, registry apps: {sw}, "
                    f"package manager entries: {deep.get('package_manager_entries', 0)}, "
                    f"AppX entries: {deep.get('appx_entries', 0)}."
                )
            else:
                self.status.setText(
                    f"Quick scan completed. Captured {hw} hardware categories and {sw} software entries."
                )
        else:
            self.status.setText("Scan finished but no results were returned.")
        self.refresh()

    def _on_recommendation_result(self, result: object) -> None:
        if isinstance(result, dict):
            count = int(result.get("recommended_count", 0))
            total = int(result.get("input_count", 0))
            strategy = str(result.get("strategy", "local"))
            preference = str(result.get("selection_profile", self.ui_state.recommendation_strategy))
            self.status.setText(
                f"{strategy.capitalize()} recommendations generated ({preference}): {count}/{total} matched. "
                f"Report: {result.get('markdown_path', '')}"
            )
        else:
            self.status.setText("Recommendation generation finished but returned no result.")
        self.refresh()

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Scan failed.\n{user_facing_error(error)}")
        self.refresh()

    def _on_finished(self) -> None:
        self.is_running = False
        self.loading.setVisible(False)
        self.refresh()

    def refresh(self) -> None:
        mode = self.ui_state.mode
        if self.ui_state.recommendation_strategy == "prioritize":
            self.recommendation_profile.setText(
                "Recommendation profile: Prioritized shortlist. Focuses high-confidence and high-value applications first."
            )
        else:
            self.recommendation_profile.setText(
                "Recommendation profile: Migrate all. Keeps all supported applications in the recommendation set."
            )

        if mode == "guided":
            if self.ui_state.recommendation_strategy != "migrate_all":
                self.ui_state.recommendation_strategy = "migrate_all"
                self.migrate_all_radio.setChecked(True)
            self.deep_scan_btn.setVisible(False)
            self.online_rec_btn.setVisible(False)
            self.agent_rec_btn.setVisible(False)
            self.prioritize_radio.setEnabled(False)
            self.migrate_all_radio.setEnabled(False)
            if not self.is_running:
                self.quick_scan_btn.setEnabled(True)
            self.status.setText(
                "Guided mode uses quick inventory only. Switch to Expert for deep scan and recommendation engines."
                if not self.ui_state.inventory_completed
                else self.status.text()
            )
        elif mode == "balanced":
            self.deep_scan_btn.setVisible(False)
            self.online_rec_btn.setVisible(False)
            self.agent_rec_btn.setVisible(False)
            self.prioritize_radio.setEnabled(True)
            self.migrate_all_radio.setEnabled(True)
            if not self.is_running:
                self.quick_scan_btn.setEnabled(True)
            if not self.ui_state.inventory_completed:
                self.status.setText(
                    "Balanced mode enables quick inventory with advanced features disabled for safer operation."
                )
        else:
            self.deep_scan_btn.setVisible(True)
            self.online_rec_btn.setVisible(True)
            self.agent_rec_btn.setVisible(True)
            self.prioritize_radio.setEnabled(True)
            self.migrate_all_radio.setEnabled(True)
            if not self.is_running:
                self.quick_scan_btn.setEnabled(True)
                self.deep_scan_btn.setEnabled(True)
                self.online_rec_btn.setEnabled(self.ui_state.inventory_completed)
                self.agent_rec_btn.setEnabled(self.ui_state.inventory_completed)

        # self.next_btn.setEnabled(self.ui_state.inventory_completed or self.ui_state.mode == "expert")
