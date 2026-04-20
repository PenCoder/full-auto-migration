"""Data selection page for choosing the migration scope."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QRadioButton
from src.qt_ui.pages.base_page import BasePage


class DataSelectionPage(BasePage):
    """Let the user choose how files and data should be migrated."""

    def __init__(self, ui_state, current_step: int = 1, step_names: list[str] | None = None) -> None:
        super().__init__(ui_state)
        self.current_step = current_step
        self.step_names = step_names or ["Scan", "Data Selection", "Application Mapping", "Backup"]
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        question = "Which of the following would fits your preferences for migrating application data files?" \
                   " (You can change this later if you're unsure)"
        info = ("• We recommend migrating data files for applications you use frequently or that contain important information to ensure a smooth transition. <br>" +
                "• You can choose to migrate all data files, only those from applications you select, or skip data file migration and set it up manually on Linux.")
        
        self.migrate_all_radio = QRadioButton("Migrate All Files from Supported Applications")
        self.select_file_types_radio = QRadioButton("Select the file types to migrate (e.g. pdf, docx, mp3)")
        self.recommendations_radio = QRadioButton("Get migration recommendations based on my usage patterns")
        self.manual_radio = QRadioButton("Skip data file migration and set up manually on Linux")

        guided_panel = self.create_guided_questionnaire(
            question,
            info,
            options=[
                self.migrate_all_radio,
                self.select_file_types_radio,
                self.recommendations_radio,
                self.manual_radio,
            ]
        )
        root.addWidget(guided_panel)

        self._sync_radios_from_state()

        self.trust_banner = QLabel()
        self.trust_banner.setObjectName("TrustLabel")
        self.trust_banner.setWordWrap(True)
        self.trust_banner.setAlignment(Qt.AlignCenter)
        root.addWidget(self.trust_banner)

        self.choice_summary = QLabel("")
        self.choice_summary.setObjectName("BodyText")
        self.choice_summary.setWordWrap(True)
        self.choice_summary.setAlignment(Qt.AlignCenter)
        root.addWidget(self.choice_summary)

        row = QHBoxLayout()

        self.keep_all_btn = QPushButton("Keep Them All")
        self.keep_all_btn.setProperty("role", "primary")
        self.keep_all_btn.setMinimumHeight(48)
        self.keep_all_btn.setFixedWidth(220)
        self.keep_all_btn.clicked.connect(lambda: self._set_strategy("keep_all"))
        # row.addWidget(self.keep_all_btn)

        self.choose_btn = QPushButton("Let Me Choose")
        self.choose_btn.setProperty("role", "primary")
        self.choose_btn.setMinimumHeight(48)
        self.choose_btn.setFixedWidth(220)
        self.choose_btn.clicked.connect(lambda: self._set_strategy("let_me_choose"))
        row.addWidget(self.choose_btn)

        root.addLayout(row)

        self.next_btn = QPushButton("Continue")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedWidth(200)
        self.next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

        self.migrate_all_radio.toggled.connect(lambda checked: self._set_choice_mode("all_files", checked))
        self.select_file_types_radio.toggled.connect(lambda checked: self._set_choice_mode("selected_types", checked))
        self.recommendations_radio.toggled.connect(lambda checked: self._set_choice_mode("ai_recommended", checked))
        self.manual_radio.toggled.connect(lambda checked: self._set_choice_mode("manual", checked))

    def _set_strategy(self, strategy: str) -> None:
        self.ui_state.data_strategy = strategy
        self.refresh()

    def _set_choice_mode(self, mode: str, checked: bool) -> None:
        if not checked:
            return
        self.ui_state.data_choice_mode = mode
        if mode == "all_files":
            self.ui_state.data_strategy = "keep_all"
        else:
            self.ui_state.data_strategy = "let_me_choose"
        self.refresh()

    def _sync_radios_from_state(self) -> None:
        mode = self.ui_state.data_choice_mode
        if mode == "selected_types":
            self.select_file_types_radio.setChecked(True)
        elif mode == "ai_recommended":
            self.recommendations_radio.setChecked(True)
        elif mode == "manual":
            self.manual_radio.setChecked(True)
        else:
            self.migrate_all_radio.setChecked(True)

    def refresh(self) -> None:
        mode = self.ui_state.mode
        if mode == "guided" and self.ui_state.data_strategy != "keep_all":
            self.ui_state.data_strategy = "keep_all"
            self.ui_state.data_choice_mode = "all_files"
            self.migrate_all_radio.setChecked(True)

        strategy = self.ui_state.data_strategy
        choice_mode = self.ui_state.data_choice_mode

        if strategy == "keep_all":
            self.choose_btn.setEnabled(True)
        else:
            self.choose_btn.setEnabled(False)

        if mode == "guided":
            self.choose_btn.setEnabled(False)
            self.select_file_types_radio.setEnabled(False)
            self.recommendations_radio.setEnabled(False)
            self.manual_radio.setEnabled(False)
            self.trust_banner.setText(
                "Guided mode applies a safe default backup scope (all files from supported applications)."
            )
        elif mode == "balanced":
            self.select_file_types_radio.setEnabled(True)
            self.recommendations_radio.setEnabled(True)
            self.manual_radio.setEnabled(True)
            self.trust_banner.setText(
                "Balanced mode lets you choose a migration style while keeping advanced folder tuning in Expert Overrides."
            )
        else:
            self.select_file_types_radio.setEnabled(True)
            self.recommendations_radio.setEnabled(True)
            self.manual_radio.setEnabled(True)
            self.trust_banner.setText(
                "Expert mode unlocks full customization and recommendation-assisted data migration."
            )

        summary_map = {
            "all_files": "Current choice: Migrate all files from supported applications.",
            "selected_types": "Current choice: Migrate selected file types. Configure exact types in Expert Overrides.",
            "ai_recommended": "Current choice: AI-recommended file migration scope based on usage and scan signals.",
            "manual": "Current choice: Skip automatic data-file migration and configure manually on Linux.",
        }
        self.choice_summary.setText(summary_map.get(choice_mode, summary_map["all_files"]))

        self.next_btn.setEnabled(True)
