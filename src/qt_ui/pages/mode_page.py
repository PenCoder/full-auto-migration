"""Mode selection page for the migration wizard."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from src.qt_ui.pages.base_page import BasePage


class ModePage(BasePage):
    """Let the user choose guided, balanced, or expert migration mode."""

    def __init__(self, ui_state) -> None:
        super().__init__(ui_state)
        self.setObjectName("StepCard")
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        root.addWidget(self.create_page_header(
            "🧭",
            "How much guidance would you like?",
            "All three options take you to the same destination — choose how much help you'd like along the way. "
            "You can change your mind at any step.",
        ))

        self.guided_radio = QRadioButton("Guided")
        self.guided_radio.setToolTip("The tool makes sensible choices for you and explains what it's doing.")
        self.guided_radio.toggled.connect(lambda: self._set_mode("guided"))
        guided_hint = self.hint_label(
            "Recommended for most people. Everything is handled for you with clear explanations at every step. "
            "No technical knowledge needed."
        )

        self.balanced_radio = QRadioButton("Balanced")
        self.balanced_radio.setToolTip("You get smart recommendations but can adjust the important choices.")
        self.balanced_radio.toggled.connect(lambda: self._set_mode("balanced"))
        balanced_hint = self.hint_label(
            "Great if you're comfortable with computers and want to decide things like which files and apps to bring across."
        )

        self.expert_radio = QRadioButton("Expert")
        self.expert_radio.setToolTip("All options and advanced settings are available upfront.")
        self.expert_radio.toggled.connect(lambda: self._set_mode("expert"))
        expert_hint = self.hint_label(
            "For experienced users who want to fine-tune every aspect of the migration, "
            "including live online package verification and custom override rules."
        )

        questionnaire = self.create_guided_questionnaire(
            question="Choose your experience level",
            info=(
                "• All three modes produce the same final result — your data, apps, and settings moved across safely.<br>"
                "• You can switch modes at any time without losing your progress."
            ),
            options=[
                self.guided_radio,
                guided_hint,
                self.balanced_radio,
                balanced_hint,
                self.expert_radio,
                expert_hint,
            ],
        )
        root.addWidget(questionnaire)

    def _set_mode(self, value: str) -> None:
        self.ui_state.mode = value
        self.refresh()

    def refresh(self) -> None:
        selected = self.ui_state.mode
        self._set_selected(self.guided_radio, selected == "guided")
        self._set_selected(self.balanced_radio, selected == "balanced")
        self._set_selected(self.expert_radio, selected == "expert")

    @staticmethod
    def _set_selected(card: QFrame, value: bool) -> None:
        card.setProperty("selected", value)
        style = card.style()
        style.unpolish(card)
        style.polish(card)
        card.update()
