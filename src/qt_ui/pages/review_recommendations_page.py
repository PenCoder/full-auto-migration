"""Review page for app and file migration recommendations."""

from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
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
        current_step: int = 3,
        step_names: list[str] | None = None,
    ) -> None:
        super().__init__(ui_state)
        self.run_app_recommendations_cb = run_app_recommendations_cb
        self.run_file_recommendations_cb = run_file_recommendations_cb
        self.current_step = current_step
        self.step_names = step_names or ["Scan", "Data Selection", "Application Mapping", "Review & Backup"]
        self.thread_pool = QThreadPool.globalInstance()
        self.app_recommendations: dict[str, Any] = {}
        self.file_recommendations: dict[str, Any] = {}
        self.is_running = False
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout(max_width=1000)

        step = QLabel("Preparation - Step 4 of 5: Review Migration Recommendations")
        step.setObjectName("StepTitle")
        step.setAlignment(Qt.AlignCenter)
        root.addWidget(step)

        question = "Review proposed app and file migrations before creating the backup bundle."
        info = (
            "• Your migration recommendations are based on scanned inventory and your chosen strategy. <br>"
            + "• Review each section and customize selections if needed using Expert Overrides. <br>"
            + "• Green (checked) items will be migrated; unchecked items will be excluded."
        )

        guided_panel = self.create_guided_questionnaire(question, info, options=[])
        root.addWidget(guided_panel)

        # App recommendations section
        app_title = QLabel("Application Recommendations")
        app_title.setObjectName("StepTitle")
        root.addWidget(app_title)

        self.app_summary = QLabel(
            "Click 'Refresh Recommendations' to generate app-level migration suggestions based on your scan."
        )
        self.app_summary.setObjectName("BodyText")
        self.app_summary.setWordWrap(True)
        root.addWidget(self.app_summary)

        self.app_details = QTextEdit()
        self.app_details.setReadOnly(True)
        self.app_details.setMinimumHeight(120)
        self.app_details.setMaximumHeight(180)
        root.addWidget(self.app_details)

        # File recommendations section
        file_title = QLabel("File Migration Recommendations")
        file_title.setObjectName("StepTitle")
        root.addWidget(file_title)

        self.file_summary = QLabel(
            "Click 'Refresh Recommendations' to generate file-level migration suggestions based on your data selection."
        )
        self.file_summary.setObjectName("BodyText")
        self.file_summary.setWordWrap(True)
        root.addWidget(self.file_summary)

        self.file_details = QTextEdit()
        self.file_details.setReadOnly(True)
        self.file_details.setMinimumHeight(120)
        self.file_details.setMaximumHeight(180)
        root.addWidget(self.file_details)

        # Status and action buttons
        self.status = QLabel("Ready to generate recommendations.")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        # Button row
        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        self.refresh_btn = QPushButton("Refresh Recommendations")
        self.refresh_btn.setProperty("role", "primary")
        self.refresh_btn.setMinimumHeight(48)
        self.refresh_btn.setFixedWidth(240)
        self.refresh_btn.clicked.connect(self._run_recommendations)
        button_row.addWidget(self.refresh_btn)

        self.customize_btn = QPushButton("Customize (Expert)")
        self.customize_btn.setProperty("role", "badge")
        self.customize_btn.setMinimumHeight(48)
        self.customize_btn.setFixedWidth(180)
        self.customize_btn.clicked.connect(self._open_expert_panel)
        button_row.addWidget(self.customize_btn)

        root.addLayout(button_row)

        self.next_btn = QPushButton("Continue to Backup")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedWidth(220)
        self.next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

    def _run_recommendations(self) -> None:
        self._set_running_state(True)
        self.loading.setVisible(True)
        self.status.setText("Generating app and file migration recommendations...")

        # Run both in parallel conceptually by using a worker function that calls both
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
                    f"Application recommendations: {app_count}/{app_total} matched apps ready for migration."
                )
                recs = app_recs.get("recommendations", [])
                apps_text = "\n".join(
                    [f"✓ {rec.get('windows_app', '')}" for rec in recs[:10]]
                )
                if len(recs) > 10:
                    apps_text += f"\n... and {len(recs) - 10} more"
                self.app_details.setPlainText(apps_text or "No app recommendations available.")
            else:
                self.app_summary.setText("Failed to generate app recommendations.")
                self.app_details.setPlainText("")

            if isinstance(file_recs, dict) and "error" not in file_recs:
                self.file_recommendations = file_recs
                file_count = int(file_recs.get("recommended_count", 0))
                file_total = int(file_recs.get("input_count", 0))
                self.file_summary.setText(
                    f"File recommendations: {file_count}/{file_total} selected for migration."
                )
                recs = file_recs.get("recommendations", [])
                files_text = "\n".join(
                    [f"✓ {rec.get('file_path', '')[:60]}" for rec in recs[:10]]
                )
                if len(recs) > 10:
                    files_text += f"\n... and {len(recs) - 10} more files"
                self.file_details.setPlainText(files_text or "No file recommendations available.")
            else:
                self.file_summary.setText("Failed to generate file recommendations.")
                self.file_details.setPlainText("")

            self.status.setText("Recommendations ready. Review above and click 'Continue to Backup' to proceed.")
        else:
            self.status.setText("Recommendation generation returned unexpected format.")

        self.refresh()

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Recommendation generation failed.\n{user_facing_error(error)}")
        self.refresh()

    def _on_finished(self) -> None:
        self.is_running = False
        self.loading.setVisible(False)
        self.refresh()

    def _open_expert_panel(self) -> None:
        if self.ui_state.mode != "expert":
            self.status.setText("Expert customization is available in Expert mode. Switch modes at the top and return here.")
        else:
            self.status.setText("Use Expert Overrides (right panel) to customize app/file selections before backup.")

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
            self.status.setText("Guided mode uses automatic recommendations. Switch to Expert if you need to customize.")
        elif mode == "balanced":
            self.refresh_btn.setVisible(True)
            self.customize_btn.setVisible(False)
            self.status.setText("Balanced mode: click Refresh to see recommendations (Expert panel hidden).")
        else:  # expert
            self.refresh_btn.setVisible(True)
            self.customize_btn.setVisible(True)
            self.status.setText("Expert mode: click Refresh or customize via Expert Overrides panel.")

        self.next_btn.setEnabled(not self.is_running)
