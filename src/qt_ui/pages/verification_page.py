from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QPushButton, QVBoxLayout

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

        step = QLabel("Migration - Step 2 of 2: Validation and Verification")
        step.setObjectName("StepTitle")
        step.setAlignment(Qt.AlignCenter)
        root.addWidget(step)

        self.step_progress = QProgressBar()
        self.step_progress.setRange(0, 100)
        self.step_progress.setValue(100)
        self.step_progress.setTextVisible(False)
        self.step_progress.setFixedHeight(10)
        root.addWidget(self.step_progress)

        text = QLabel("Migration complete. We are now verifying your data integrity.")
        text.setObjectName("HeroTitle")
        text.setWordWrap(True)
        text.setAlignment(Qt.AlignCenter)
        root.addWidget(text)

        self.status = QLabel("Run verification to compute restore integrity and readiness score.")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        self.verify_btn = QPushButton("Run Verification")
        self.verify_btn.setProperty("role", "primary")
        self.verify_btn.setMinimumHeight(58)
        self.verify_btn.setFixedWidth(260)
        self.verify_btn.clicked.connect(self._run_verification)
        root.addWidget(self.verify_btn, alignment=Qt.AlignHCenter)

        self.report_btn = QPushButton("Final Sovereignty Report")
        self.report_btn.setProperty("role", "cta")
        self.report_btn.setFixedWidth(280)
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
            self.status.setText(
                "Verification complete. "
                f"Total Sovereignty Score: {self.ui_state.total_sovereignty_score}%"
            )
        else:
            self.status.setText("Verification returned no summary.")
        self.refresh()

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Verification failed: {error}")
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
