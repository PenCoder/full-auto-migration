from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QPushButton, QVBoxLayout

from src.orchestration.errors import user_facing_error
from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker


class VerificationPage(BasePage):
    def __init__(self, ui_state, run_validation_cb: Callable[[], dict]) -> None:
        super().__init__(ui_state)
        self.run_validation_cb = run_validation_cb
        self.thread_pool = QThreadPool.globalInstance()
        self.report_path: str = ""
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        text = QLabel("Validate restored files, integrity hashes, and migration sovereignty readiness.")
        text.setObjectName("HeroTitle")
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignCenter)
        root.addWidget(text)

        self.status = QLabel("Run verification to compute restore integrity and readiness score.")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        root.addWidget(
            self.create_trust_banner(
                "Trust indicator: verification compares restored files and records machine-readable evidence reports."
            )
        )

        self.score_progress = QProgressBar()
        self.score_progress.setRange(0, 100)
        self.score_progress.setValue(0)
        self.score_progress.setFormat("Sovereignty Score: %p%")
        self.score_progress.setTextVisible(True)
        root.addWidget(self.score_progress)

        self.evidence_chips = self.create_stat_chip_row(
            ["Files: 0", "Hash Verified: 0", "Apps: 0"]
        )
        root.addWidget(self.evidence_chips)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        self.verify_btn = QPushButton("Run Verification")
        self.verify_btn.setProperty("role", "primary")
        self.verify_btn.setMinimumHeight(48)
        self.verify_btn.setFixedWidth(230)
        self.verify_btn.clicked.connect(self._run_verification)
        root.addWidget(self.verify_btn, alignment=Qt.AlignHCenter)

        self.report_btn = QPushButton("Final Sovereignty Report")
        self.report_btn.setProperty("role", "cta")
        self.report_btn.setFixedWidth(250)
        self.report_btn.clicked.connect(self._show_report_path)
        root.addWidget(self.report_btn, alignment=Qt.AlignHCenter)

    def _run_verification(self) -> None:
        self.verify_btn.setEnabled(False)
        self.report_btn.setEnabled(False)
        self.loading.setVisible(True)
        self.status.setText("Validating restored files and application status...")
        worker = FunctionWorker(self.run_validation_cb)
        worker.signals.result.connect(self._on_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self.thread_pool.start(worker)

    def _on_result(self, result: object) -> None:
        if isinstance(result, dict):
            self.ui_state.verification_completed = True
            self.ui_state.total_sovereignty_score = int(result.get("total_sovereignty_score", 0))
            self.ui_state.restored_data_size_label = result.get("restored_data_size", "")
            self.report_path = result.get("report_path", "")
            self.score_progress.setValue(self.ui_state.total_sovereignty_score)

            total_files = int(result.get("total_files", 0))
            hash_verified = int(result.get("hash_verified_files", 0))
            apps = int(result.get("apps_mapped", 0))
            chips_layout = self.evidence_chips.layout()
            chips_layout.itemAt(1).widget().setText(f"Files: {total_files}")
            chips_layout.itemAt(2).widget().setText(f"Hash Verified: {hash_verified}")
            chips_layout.itemAt(3).widget().setText(f"Apps: {apps}")
            self.status.setText(
                "Verification complete. "
                f"Total Sovereignty Score: {self.ui_state.total_sovereignty_score}%"
            )
        else:
            self.status.setText("Verification returned no summary.")
        self.refresh()

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Verification failed.\n{user_facing_error(error)}")
        self.refresh()

    def _show_report_path(self) -> None:
        if self.report_path:
            self.status.setText(f"Report available at: {self.report_path}")
        else:
            self.status.setText("No report available yet. Run verification first.")

    def _on_finished(self) -> None:
        self.verify_btn.setEnabled(True)
        self.loading.setVisible(False)
        self.refresh()

    def refresh(self) -> None:
        self.report_btn.setEnabled(self.ui_state.verification_completed)
