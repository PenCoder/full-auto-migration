"""Application mapping page — auto-triggers analysis when the page becomes visible."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThreadPool, QTimer, Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QRadioButton

from src.orchestration.errors import user_facing_error
from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker


class ApplicationMappingPage(BasePage):
    """Generate Linux application mapping guidance — fires automatically on page entry."""

    def __init__(
        self,
        ui_state,
        run_analysis_cb: Callable[[], dict],
        current_step: int = 2,
        step_names: list[str] | None = None,
    ) -> None:
        super().__init__(ui_state)
        self.run_analysis_cb = run_analysis_cb
        self.current_step = current_step
        self.step_names = step_names or ["Scan", "Data Selection", "Application Mapping", "Backup"]
        self.thread_pool = QThreadPool.globalInstance()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        root.addWidget(self.create_page_header(
            "🗂️",
            "Plan your app transition",
            "Each Windows app is matched to the best Linux alternative. "
            "Most have a great equivalent already in the database.",
        ))

        question = "How would you like to handle your apps?"
        info = (
            "A database of over 150 app matches is ready to go. "
            "Choose how much you'd like to be involved in the selection."
        )

        self.migrate_all_radio = QRadioButton("Switch all my apps automatically — I trust your recommendations")
        self.migrate_all_hint = self.hint_label(
            "Best for most people. The best Linux alternative is selected for each of your apps automatically."
        )

        self.choose_from_recommendations_radio = QRadioButton("Show me the recommendations and let me pick")
        self.choose_from_recommendations_hint = self.hint_label(
            "Alternatives are listed for each app — choose which ones to include."
        )

        self.manual_mapping_radio = QRadioButton("I'll configure the app matches myself")
        self.manual_mapping_hint = self.hint_label(
            "Full control — you specify exactly which Linux app replaces each Windows app."
        )

        self.migrate_all_radio.toggled.connect(
            lambda checked: self._set_mapping_choice_mode("migrate_all_supported", checked)
        )
        self.choose_from_recommendations_radio.toggled.connect(
            lambda checked: self._set_mapping_choice_mode("choose_from_recommendations", checked)
        )
        self.manual_mapping_radio.toggled.connect(
            lambda checked: self._set_mapping_choice_mode("manual_mapping", checked)
        )

        mapping_questionnaire = self.create_guided_questionnaire(
            question=question,
            info=info,
            options=[
                self.migrate_all_radio,
                self.migrate_all_hint,
                self.choose_from_recommendations_radio,
                self.choose_from_recommendations_hint,
                self.manual_mapping_radio,
                self.manual_mapping_hint,
            ],
        )
        root.addWidget(mapping_questionnaire)

        self.status = QLabel("Generating your personalised app transition plan…")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        self._sync_radios_from_state()

    # ── Auto-trigger ─────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self.ui_state.analysis_completed and not self.is_processing:
            QTimer.singleShot(300, self._run_mapping)

    # ── Mapping ──────────────────────────────────────────────────────────────

    def _sync_radios_from_state(self) -> None:
        mode = self.ui_state.mapping_choice_mode
        if mode == "choose_from_recommendations":
            self.choose_from_recommendations_radio.setChecked(True)
        elif mode == "manual_mapping":
            self.manual_mapping_radio.setChecked(True)
        else:
            self.migrate_all_radio.setChecked(True)

    def _set_mapping_choice_mode(self, mode: str, checked: bool) -> None:
        if not checked:
            return
        self.ui_state.mapping_choice_mode = mode
        self.refresh()

    def _run_mapping(self) -> None:
        if self.is_processing:
            return
        self.loading.setVisible(True)
        self.set_scanning(True)
        self.status.setText("Generating hardware/software analysis and mapping recommendations…")
        worker = FunctionWorker(self.run_analysis_cb)
        worker.signals.result.connect(self._on_result)
        worker.signals.error.connect(self._on_error)
        worker.signals.finished.connect(self._on_finished)
        self.thread_pool.start(worker)

    def _on_result(self, result: object) -> None:
        if isinstance(result, dict):
            self.ui_state.analysis_completed = True
            mapped = len(result.get("software", []))
            self.status.setText(
                f"✅  Done! Linux alternatives found for {mapped} of your apps. Ready to move on."
            )
        else:
            self.status.setText("App matching finished — you can proceed to the next step.")
        self.refresh()

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Mapping failed.\n{user_facing_error(error)}")

    def _on_finished(self) -> None:
        self.loading.setVisible(False)
        self.set_scanning(False)
        self.refresh()

    # ── Refresh ──────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        mode = self.ui_state.mode
        mapping_mode = self.ui_state.mapping_choice_mode

        if mode == "guided":
            self.choose_from_recommendations_radio.setVisible(False)
            self.manual_mapping_radio.setVisible(False)
            self.choose_from_recommendations_hint.setVisible(False)
            self.manual_mapping_hint.setVisible(False)
            self.migrate_all_radio.setEnabled(not self.is_processing)
            self.migrate_all_radio.setVisible(True)
            self.migrate_all_hint.setVisible(True)
            if mapping_mode != "migrate_all_supported":
                self.ui_state.mapping_choice_mode = "migrate_all_supported"
                self.migrate_all_radio.setChecked(True)
            if not self.is_processing and not self.ui_state.analysis_completed:
                self.status.setText(
                    "The best Linux app for each of your Windows apps will be selected automatically."
                )
        elif mode == "balanced":
            self.migrate_all_radio.setVisible(True)
            self.migrate_all_hint.setVisible(True)
            self.choose_from_recommendations_radio.setVisible(True)
            self.choose_from_recommendations_hint.setVisible(True)
            self.manual_mapping_radio.setVisible(False)
            self.manual_mapping_hint.setVisible(False)
            self.migrate_all_radio.setEnabled(not self.is_processing)
            self.choose_from_recommendations_radio.setEnabled(not self.is_processing)
            if mapping_mode == "manual_mapping":
                self.ui_state.mapping_choice_mode = "choose_from_recommendations"
                self.choose_from_recommendations_radio.setChecked(True)
            if not self.is_processing and not self.ui_state.analysis_completed:
                self.status.setText(
                    "Generating the plan — Linux alternatives for your apps will appear here."
                )
        else:
            self.migrate_all_radio.setVisible(True)
            self.migrate_all_hint.setVisible(True)
            self.choose_from_recommendations_radio.setVisible(True)
            self.choose_from_recommendations_hint.setVisible(True)
            self.manual_mapping_radio.setVisible(True)
            self.manual_mapping_hint.setVisible(True)
            self.migrate_all_radio.setEnabled(not self.is_processing)
            self.choose_from_recommendations_radio.setEnabled(not self.is_processing)
            self.manual_mapping_radio.setEnabled(not self.is_processing)
            if not self.is_processing and not self.ui_state.analysis_completed:
                self.status.setText(
                    "All mapping options are available — generating recommendations now."
                )
