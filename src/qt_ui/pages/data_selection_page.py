from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QRadioButton
from src.qt_ui.pages.base_page import BasePage


class DataSelectionPage(BasePage):
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
        
        migrate_all_radio = QRadioButton("Migrate All Files from Supported Applications")
        select_file_types_radio = QRadioButton("Select the files types to migrate (e.g. pdf, docx, mp3, etc.)")
        recommendations_radio = QRadioButton("Get migration recommendations based on my usage patterns")
        manual_radio = QRadioButton("Skip data file migration and set up manually on Linux")

        guided_panel = self.create_guided_questionnaire(
            question,
            info,
            options=[
                migrate_all_radio, 
                select_file_types_radio, 
                recommendations_radio, 
                manual_radio
            ]
        )
        root.addWidget(guided_panel)

        self.trust_banner = QLabel()
        self.trust_banner.setObjectName("TrustLabel")
        self.trust_banner.setWordWrap(True)
        self.trust_banner.setAlignment(Qt.AlignCenter)
        # root.addWidget(self.trust_banner)

        self.choice_summary = QLabel("")
        self.choice_summary.setObjectName("BodyText")
        self.choice_summary.setWordWrap(True)
        self.choice_summary.setAlignment(Qt.AlignCenter)
        # root.addWidget(self.choice_summary)

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
        # row.addWidget(self.choose_btn)

        root.addLayout(row)

        self.next_btn = QPushButton("Continue")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedWidth(200)
        self.next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

    def _set_strategy(self, strategy: str) -> None:
        self.ui_state.data_strategy = strategy
        self.refresh()

    def refresh(self) -> None:
        mode = self.ui_state.mode
        if mode == "guided" and self.ui_state.data_strategy != "keep_all":
            self.ui_state.data_strategy = "keep_all"

        strategy = self.ui_state.data_strategy
        if strategy == "keep_all":
            # self.choice_summary.setText(
            #     "Current selection: Keep Them All. The recommended safe default will include all configured folders."
            # )
            # self.keep_all_btn.setEnabled(False)
            self.choose_btn.setEnabled(True)
        else:
            # self.choice_summary.setText(
            #     "Current selection: Let Me Choose. Open Expert Overrides to select folder categories and fine-tune scope."
            # )
            # self.keep_all_btn.setEnabled(True)
            self.choose_btn.setEnabled(False)

        if mode == "guided":
            self.choose_btn.setEnabled(False)
            # self.keep_all_btn.setEnabled(False)
        #     self.trust_banner.setText(
        #         "Guided mode applies a safe default backup scope. Switch to Balanced or Expert to customize categories."
        #     )
        # elif mode == "balanced":
        #     self.trust_banner.setText(
        #         "Balanced mode lets you choose the backup strategy while keeping advanced tuning in Expert Overrides."
        #     )
        # else:
        #     self.trust_banner.setText(
        #         "Expert mode unlocks full path-level customization through Expert Overrides."
        #     )

        self.next_btn.setEnabled(True)
