"""Final report page for exporting migration evidence artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel, QProgressBar, QPushButton, QTextEdit, QVBoxLayout

from src.orchestration.errors import user_facing_error
from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker
from src.services.report_service import ReportService


class ReportPage(BasePage):
    """Generate and open the final migration report outputs."""

    def __init__(self, ui_state, generate_report_cb: Callable[[], dict] | None = None) -> None:
        super().__init__(ui_state)
        self.generate_report_cb = generate_report_cb
        self.thread_pool = QThreadPool.globalInstance()
        self.report_paths: dict[str, str] = {}
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout(max_width=980)

        root.addWidget(
            self.create_trust_banner(
                "This report consolidates validation evidence, sovereignty score, and migration recommendations."
            )
        )

        self.score_display = QLabel("Sovereignty score: 0%")
        self.score_display.setObjectName("HeroTitle")
        self.score_display.setAlignment(Qt.AlignCenter)
        root.addWidget(self.score_display)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMinimumHeight(220)
        root.addWidget(self.summary_text)

        self.report_status = QLabel("Generate the final report to create markdown, HTML, and JSON evidence artifacts.")
        self.report_status.setObjectName("BodyText")
        self.report_status.setWordWrap(True)
        self.report_status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.report_status)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        self.generate_btn = QPushButton("Generate Final Report")
        self.generate_btn.setProperty("role", "primary")
        self.generate_btn.setMinimumHeight(48)
        self.generate_btn.clicked.connect(self._run_report_generation)
        root.addWidget(self.generate_btn, alignment=Qt.AlignHCenter)

        self.open_markdown_btn = QPushButton("Open Markdown Report")
        self.open_markdown_btn.setProperty("role", "cta")
        self.open_markdown_btn.setFixedWidth(230)
        self.open_markdown_btn.clicked.connect(self._open_markdown)
        root.addWidget(self.open_markdown_btn, alignment=Qt.AlignHCenter)

        self.open_html_btn = QPushButton("Open HTML Report")
        self.open_html_btn.setProperty("role", "badge")
        self.open_html_btn.setFixedWidth(230)
        self.open_html_btn.clicked.connect(self._open_html)
        root.addWidget(self.open_html_btn, alignment=Qt.AlignHCenter)

        self.next_btn = QPushButton("Finish")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedWidth(200)
        self.next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

    def _run_report_generation(self) -> None:
        self.generate_btn.setEnabled(False)
        self.open_markdown_btn.setEnabled(False)
        self.open_html_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.loading.setVisible(True)
        self.report_status.setText("Generating report artifacts and visual summary...")

        if self.generate_report_cb is not None:
            worker = FunctionWorker(self.generate_report_cb)
        else:
            worker = FunctionWorker(self._default_generate_report)

        worker.signals.result.connect(self._on_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self.thread_pool.start(worker)

    def _default_generate_report(self) -> dict:
        service = ReportService()
        return service.generate_report()

    def _on_result(self, result: object) -> None:
        if isinstance(result, dict):
            self.report_paths = {
                "json": result.get("json_path", ""),
                "markdown": result.get("markdown_path", ""),
                "html": result.get("html_path", ""),
            }
            report = result.get("report", {})
            summary = report.get("summary", {})
            validation = report.get("validation", {})
            score = int(summary.get("score", 0))
            self.ui_state.total_sovereignty_score = score
            self.score_display.setText(f"Sovereignty score: {score}%")
            self.summary_text.setPlainText(
                "Final report generated successfully.\n\n"
                f"Rating: {summary.get('rating', 'Unknown')}\n"
                f"Files restored: {validation.get('restored_files', 0)} / {validation.get('total_files', 0)}\n"
                f"Hash verified: {validation.get('hash_verified_files', 0)}\n"
                f"Hash failed: {validation.get('hash_failed_files', 0)}\n"
                f"Applications mapped: {validation.get('apps_mapped', 0)}\n\n"
                f"Markdown: {self.report_paths.get('markdown', '')}\n"
                f"HTML: {self.report_paths.get('html', '')}\n"
                f"JSON: {self.report_paths.get('json', '')}"
            )
            self.report_status.setText("Report generation complete. Use the buttons below to open the exported artifacts.")
            self.ui_state.verification_completed = True
        else:
            self.report_status.setText("Report generation finished without structured output.")

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.report_status.setText(f"Report generation failed.\n{user_facing_error(error)}")

    def _on_finished(self) -> None:
        self.generate_btn.setEnabled(True)
        self.open_markdown_btn.setEnabled(bool(self.report_paths.get("markdown")))
        self.open_html_btn.setEnabled(bool(self.report_paths.get("html")))
        self.next_btn.setEnabled(True)
        self.loading.setVisible(False)
        self.refresh()

    def _open_markdown(self) -> None:
        path = self.report_paths.get("markdown")
        if path:
            QDesktopServices.openUrl(Path(path).as_uri())

    def _open_html(self) -> None:
        path = self.report_paths.get("html")
        if path:
            QDesktopServices.openUrl(Path(path).as_uri())

    def refresh(self) -> None:
        self.next_btn.setEnabled(bool(self.report_paths))
