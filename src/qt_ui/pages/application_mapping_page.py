"""Application mapping page for compatibility review and analysis."""

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QThreadPool, Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QPushButton, QRadioButton

from src.orchestration.errors import user_facing_error
from src.qt_ui.pages.base_page import BasePage
from src.qt_ui.workers import FunctionWorker


class ApplicationMappingPage(BasePage):
    """Generate Linux application mapping guidance from the scan results."""

    def __init__(self, ui_state, run_analysis_cb: Callable[[], dict], current_step: int = 2, step_names: list[str] | None = None) -> None:
        super().__init__(ui_state)
        self.run_analysis_cb = run_analysis_cb
        self.current_step = current_step
        self.step_names = step_names or ["Scan", "Data Selection", "Application Mapping", "Backup"]
        self.thread_pool = QThreadPool.globalInstance()
        self.is_running = False
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        root.addWidget(self.create_page_header(
            "🗂️",
            "Plan your app transition",
            "We'll match each of your Windows apps to the best Linux alternative. "
            "Most apps have a great equivalent — and we've already done the research.",
        ))

        question = "How would you like to handle your apps?"
        info = (
            "We have a database of over 150 app matches ready to go. "
            "Choose how much you'd like to be involved in the selection."
        )

        self.migrate_all_radio = QRadioButton("Switch all my apps automatically — I trust your recommendations")
        self.migrate_all_hint = self.hint_label(
            "Best for most people. We pick the best Linux alternative for each of your apps and handle everything."
        )

        self.choose_from_recommendations_radio = QRadioButton("Show me the recommendations and let me pick")
        self.choose_from_recommendations_hint = self.hint_label(
            "We suggest alternatives for each app and you decide which ones to include. Great if you have preferences."
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

        self.status = QLabel("Click the button below to generate your personalised app transition plan.")
        self.status.setObjectName("BodyText")
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignCenter)
        root.addWidget(self.status)

        self.loading = QProgressBar()
        self.loading.setRange(0, 0)
        self.loading.setVisible(False)
        root.addWidget(self.loading)

        self.run_mapping_btn = QPushButton("Generate Mapping")
        self.run_mapping_btn.setProperty("role", "primary")
        self.run_mapping_btn.setMinimumHeight(48)
        self.run_mapping_btn.setFixedWidth(240)
        self.run_mapping_btn.clicked.connect(self._run_mapping)
        root.addWidget(self.run_mapping_btn, alignment=Qt.AlignHCenter)

        self.next_btn = QPushButton("Continue")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedWidth(200)
        self.next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

        self._sync_radios_from_state()

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

    def _choice_description(self) -> str:
        mode = self.ui_state.mapping_choice_mode
        descriptions = {
            "migrate_all_supported": "Current choice: migrate all supported applications with built-in recommendations.",
            "choose_from_recommendations": "Current choice: review recommendations and choose a subset to apply.",
            "manual_mapping": "Current choice: manually configure and validate mapping overrides.",
        }
        return descriptions.get(mode, descriptions["migrate_all_supported"])

    def _run_mapping(self) -> None:
        self.is_running = True
        self.run_mapping_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.loading.setVisible(True)
        self.status.setText(
            f"{self._choice_description()} Generating hardware/software analysis and mapping recommendations..."
        )
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
                f"✅  Done! We found Linux alternatives for {mapped} of your apps. You're ready to move on."
            )
        else:
            self.status.setText("App matching finished — you can proceed to the next step.")
        self.refresh()

    def _on_error(self, error: str) -> None:
        self.ui_state.last_error = error
        self.status.setText(f"Mapping failed.\n{user_facing_error(error)}")

    def _on_finished(self) -> None:
        self.is_running = False
        self.loading.setVisible(False)
        self.refresh()

    def refresh(self) -> None:
        mode = self.ui_state.mode
        mapping_mode = self.ui_state.mapping_choice_mode

        # Guided mode keeps mapping fully guided.
        if mode == "guided":
            self.choose_from_recommendations_radio.setVisible(False)
            self.manual_mapping_radio.setVisible(False)
            self.choose_from_recommendations_hint.setVisible(False)
            self.manual_mapping_hint.setVisible(False)
            self.migrate_all_radio.setEnabled(not self.is_running)
            self.migrate_all_radio.setVisible(True)
            self.migrate_all_hint.setVisible(True)
            if mapping_mode != "migrate_all_supported":
                self.ui_state.mapping_choice_mode = "migrate_all_supported"
                self.migrate_all_radio.setChecked(True)
        elif mode == "balanced":
            self.migrate_all_radio.setVisible(True)
            self.migrate_all_hint.setVisible(True)
            self.choose_from_recommendations_radio.setVisible(True)
            self.choose_from_recommendations_hint.setVisible(True)
            self.manual_mapping_radio.setVisible(False)
            self.manual_mapping_hint.setVisible(False)
            self.migrate_all_radio.setEnabled(not self.is_running)
            self.choose_from_recommendations_radio.setEnabled(not self.is_running)
            if mapping_mode == "manual_mapping":
                self.ui_state.mapping_choice_mode = "choose_from_recommendations"
                self.choose_from_recommendations_radio.setChecked(True)
        else:
            self.migrate_all_radio.setVisible(True)
            self.migrate_all_hint.setVisible(True)
            self.choose_from_recommendations_radio.setVisible(True)
            self.choose_from_recommendations_hint.setVisible(True)
            self.manual_mapping_radio.setVisible(True)
            self.manual_mapping_hint.setVisible(True)
            self.migrate_all_radio.setEnabled(not self.is_running)
            self.choose_from_recommendations_radio.setEnabled(not self.is_running)
            self.manual_mapping_radio.setEnabled(not self.is_running)

        if mode == "guided":
            self.status.setText(
                "We'll automatically find the best Linux app for each of your Windows apps — nothing for you to do here."
            )
        elif mode == "balanced":
            self.status.setText(
                "Generate the plan and we'll show you which Linux apps we recommend. You can keep them all or review the list."
            )
        else:
            self.status.setText(
                "All mapping options are available — use recommendations, review candidates, or configure overrides manually."
            )

        self.run_mapping_btn.setEnabled(not self.is_running)
        self.run_mapping_btn.setText(
            "Generate Mapping"
            if self.ui_state.mapping_choice_mode != "manual_mapping"
            else "Generate Mapping (Manual Strategy)"
        )

        self.next_btn.setEnabled(self.ui_state.analysis_completed or self.ui_state.mode == "expert")
