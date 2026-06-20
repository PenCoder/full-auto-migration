"""Verification page for restore integrity and sovereignty scoring."""

from __future__ import annotations

from typing import Callable

from pathlib import Path

from PySide6.QtCore import QThreadPool, QTimer, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFrame, QLabel, QProgressBar, QPushButton, QVBoxLayout

from src.orchestration.errors import user_facing_error
from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker


class VerificationPage(BasePage):
    """Run validation checks and present the resulting sovereignty score."""

    def __init__(self, ui_state, run_validation_cb: Callable[[], dict]) -> None:
        super().__init__(ui_state)
        self.run_validation_cb = run_validation_cb
        self.thread_pool = QThreadPool.globalInstance()
        self.report_path: str = ""
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        root.addWidget(self.create_page_header(
            "✅",
            "Verify your migration was successful",
            "Every restored file is checked and assigned a Migration Score "
            "showing how complete and successful the move to Linux has been.",
        ))

        self.status = QLabel("Click the button below to verify your restored files.")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        root.addWidget(
            self.create_trust_banner(
                "Verification only reads files — it never modifies, moves, or deletes anything on your computer."
            )
        )

        results_card = QFrame()
        results_card.setProperty("card", "section")
        results_card_layout = QVBoxLayout(results_card)
        results_card_layout.setContentsMargins(14, 12, 14, 12)
        results_card_layout.setSpacing(10)

        results_title = QLabel("Verification results")
        results_title.setObjectName("SectionTitle")
        results_card_layout.addWidget(results_title)

        self.score_progress = QProgressBar()
        self.score_progress.setRange(0, 100)
        self.score_progress.setValue(0)
        self.score_progress.setFormat("Migration Score: %p%")
        self.score_progress.setTextVisible(True)
        results_card_layout.addWidget(self.score_progress)

        self.evidence_chips = self.create_stat_chip_row(
            ["Files checked: 0", "Verified intact: 0", "Apps matched: 0"]
        )
        results_card_layout.addWidget(self.evidence_chips)

        root.addWidget(results_card)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        self.verify_btn = QPushButton("Check Everything Arrived Safely")
        self.verify_btn.setProperty("role", "cta")
        self.verify_btn.setMinimumHeight(48)
        self.verify_btn.setMinimumWidth(260)
        self.verify_btn.clicked.connect(self._run_verification)
        root.addWidget(self.verify_btn, alignment=Qt.AlignHCenter)

        self.report_btn = QPushButton("View Migration Report")
        self.report_btn.setProperty("role", "badge")
        self.report_btn.setMinimumWidth(250)
        self.report_btn.clicked.connect(self._show_report_path)
        root.addWidget(self.report_btn, alignment=Qt.AlignHCenter)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self.ui_state.restore_completed and not self.ui_state.verification_completed and not self.is_processing:
            QTimer.singleShot(300, self._run_verification)

    def _run_verification(self) -> None:
        if self.is_processing:
            return
        self.set_scanning(True)
        self.verify_btn.setEnabled(False)
        self.report_btn.setEnabled(False)
        self.loading.setVisible(True)
        self.status.setText("Checking your files — comparing what was backed up with what arrived on Linux...")
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
            score = self.ui_state.total_sovereignty_score
            if score >= 90:
                summary = f"🎉  Excellent! Your Migration Score is {score}% — your move to Linux is a great success!"
            elif score >= 70:
                summary = f"✅  Good result! Your Migration Score is {score}% — almost everything made it across."
            else:
                summary = f"⚠️  Migration Score: {score}%. Some files may need attention — check the report for details."
            self.status.setText(summary)
        else:
            self.status.setText("Verification complete — click View Migration Report for full details.")
        self.refresh()

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Verification failed.\n{user_facing_error(error)}")
        self.refresh()

    def _show_report_path(self) -> None:
        if self.report_path and Path(self.report_path).exists():
            QDesktopServices.openUrl(Path(self.report_path).as_uri())
        elif self.report_path:
            self.status.setText(f"Report path: {self.report_path}")
        else:
            self.status.setText("No report available yet — run verification first.")

    def _on_finished(self) -> None:
        self.set_scanning(False)
        self.verify_btn.setEnabled(True)
        self.loading.setVisible(False)
        self.refresh()

    def refresh(self) -> None:
        self.report_btn.setEnabled(self.ui_state.verification_completed)
