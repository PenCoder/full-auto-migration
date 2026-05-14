"""Review page for app and file migration recommendations."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTextEdit,
)

from src.orchestration.errors import user_facing_error
from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker


class ReviewRecommendationsPage(BasePage):
    """Present app and file recommendation summaries before backup."""

    def __init__(
        self,
        ui_state,
        run_app_recommendations_cb: Callable[[], dict],
        run_file_recommendations_cb: Callable[[], dict],
    ) -> None:
        super().__init__(ui_state)
        self.run_app_recommendations_cb = run_app_recommendations_cb
        self.run_file_recommendations_cb = run_file_recommendations_cb
        self.thread_pool = QThreadPool.globalInstance()
        self.app_recommendations: dict[str, Any] = {}
        self.file_recommendations: dict[str, Any] = {}
        self.is_running = False
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout(max_width=1000)

        root.addWidget(self.create_page_header(
            "🔍",
            "Review & Confirm Your Migration Plan",
            "Here's what we're planning to move for you — your apps and your files. "
            "Look through the lists and click 'Continue' when you're happy.",
        ))

        root.addWidget(
            self.create_trust_banner(
                "💡  Nothing is moved yet. This is just a preview. "
                "You can adjust everything before we create your migration bundle."
            )
        )

        app_title = QLabel("Apps: What we'll find for you on Linux")
        app_title.setObjectName("SectionTitle")
        root.addWidget(app_title)

        self.app_summary = QLabel(
            "Hit 'Refresh Plan' below to see which of your Windows apps have Linux alternatives ready."
        )
        self.app_summary.setObjectName("BodyText")
        self.app_summary.setWordWrap(True)
        root.addWidget(self.app_summary)

        self.app_details = QTextEdit()
        self.app_details.setReadOnly(True)
        self.app_details.setMinimumHeight(120)
        self.app_details.setMaximumHeight(180)
        root.addWidget(self.app_details)

        file_title = QLabel("Files: What we'll bring across for you")
        file_title.setObjectName("SectionTitle")
        root.addWidget(file_title)

        self.file_summary = QLabel(
            "Hit 'Refresh Plan' below to see which of your personal files are selected for migration."
        )
        self.file_summary.setObjectName("BodyText")
        self.file_summary.setWordWrap(True)
        root.addWidget(self.file_summary)

        self.file_details = QTextEdit()
        self.file_details.setReadOnly(True)
        self.file_details.setMinimumHeight(120)
        self.file_details.setMaximumHeight(180)
        root.addWidget(self.file_details)

        self.status = QLabel("Ready — hit 'Refresh Plan' to load your migration preview.")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        self.refresh_btn = QPushButton("Refresh Plan")
        self.refresh_btn.setProperty("role", "primary")
        self.refresh_btn.setMinimumHeight(48)
        self.refresh_btn.setFixedWidth(200)
        self.refresh_btn.clicked.connect(self._run_recommendations)
        button_row.addWidget(self.refresh_btn)

        self.customize_btn = QPushButton("Fine-tune (Expert)")
        self.customize_btn.setProperty("role", "badge")
        self.customize_btn.setMinimumHeight(48)
        self.customize_btn.setFixedWidth(180)
        self.customize_btn.clicked.connect(self._open_expert_panel)
        button_row.addWidget(self.customize_btn)

        root.addLayout(button_row)

        self.next_btn = QPushButton("Looks good — Continue to Backup")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedWidth(280)
        self.next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

    def _run_recommendations(self) -> None:
        self._set_running_state(True)
        self.loading.setVisible(True)
        self.status.setText("Working out the best migration plan for you...")

        def _generate_both() -> tuple[dict, dict]:
            try:
                apps = self.run_app_recommendations_cb()
            except Exception as e:
                apps = {"error": str(e)}

            try:
                files = self.run_file_recommendations_cb()
            except Exception as e:
                files = {"error": str(e)}

            return apps, files

        worker = FunctionWorker(_generate_both)
        worker.signals.result.connect(self._on_recommendations_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self.thread_pool.start(worker)

    def _on_recommendations_result(self, result: object) -> None:
        if isinstance(result, tuple) and len(result) == 2:
            app_recs, file_recs = result

            if isinstance(app_recs, dict) and "error" not in app_recs:
                self.app_recommendations = app_recs
                app_count = int(app_recs.get("recommended_count", 0))
                app_total = int(app_recs.get("input_count", 0))
                self.app_summary.setText(
                    f"We found Linux alternatives for {app_count} of your {app_total} Windows apps."
                )
                recs = app_recs.get("recommendations", [])
                apps_text = "\n".join(
                    [f"✓ {rec.get('windows_app', '')}" for rec in recs[:10]]
                )
                if len(recs) > 10:
                    apps_text += f"\n... and {len(recs) - 10} more"
                self.app_details.setPlainText(apps_text or "No app recommendations available.")
            else:
                self.app_summary.setText("We couldn't generate app recommendations right now — you can continue anyway.")
                self.app_details.setPlainText("")

            if isinstance(file_recs, dict) and "error" not in file_recs:
                self.file_recommendations = file_recs
                file_count = int(file_recs.get("recommended_count", 0))
                file_total = int(file_recs.get("input_count", 0))
                self.file_summary.setText(
                    f"{file_count} of {file_total} selected files will be included in your migration bundle."
                )
                recs = file_recs.get("recommendations", [])
                files_text = "\n".join(
                    [f"✓ {rec.get('file_path', '')[:60]}" for rec in recs[:10]]
                )
                if len(recs) > 10:
                    files_text += f"\n... and {len(recs) - 10} more files"
                self.file_details.setPlainText(files_text or "No file recommendations available.")
            else:
                self.file_summary.setText("We couldn't generate file recommendations right now — you can continue anyway.")
                self.file_details.setPlainText("")

            self.status.setText("Your migration plan is ready! Review the lists above, then click 'Continue to Backup'.")
        else:
            self.status.setText("Something unexpected happened — please try refreshing the plan again.")

        self.refresh()

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Couldn't generate recommendations.\n{user_facing_error(error)}")
        self.refresh()

    def _on_finished(self) -> None:
        self.is_running = False
        self.loading.setVisible(False)
        self.refresh()

    def _open_expert_panel(self) -> None:
        if self.ui_state.mode != "expert":
            self.status.setText("Fine-tuning is available in Expert mode — switch at the top and come back here.")
        else:
            self.status.setText("Use the Expert Overrides panel on the right to adjust which apps and files are included.")

    def _set_running_state(self, running: bool) -> None:
        self.is_running = running
        self.refresh_btn.setEnabled(not running)
        self.customize_btn.setEnabled(not running)
        self.next_btn.setEnabled(not running)

    def refresh(self) -> None:
        mode = self.ui_state.mode
        if mode == "guided":
            self.refresh_btn.setVisible(False)
            self.customize_btn.setVisible(False)
            self.status.setText("We've automatically prepared the best migration plan for you. Click 'Continue' when ready.")
        elif mode == "balanced":
            self.refresh_btn.setVisible(True)
            self.customize_btn.setVisible(False)
            self.status.setText("Click 'Refresh Plan' to preview what will be migrated.")
        else:
            self.refresh_btn.setVisible(True)
            self.customize_btn.setVisible(True)
            self.status.setText("Click 'Refresh Plan' or use the Expert panel on the right to fine-tune your selections.")

        self.next_btn.setEnabled(not self.is_running)
