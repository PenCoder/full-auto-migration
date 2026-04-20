"""Mode selection page for the migration wizard."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
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

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)

        self.guided_radio = QRadioButton("Guided Migration")
        self.guided_radio.setToolTip("You'll be guided through each step with recommended defaults and explanations.")
        self.guided_radio.toggled.connect(lambda: self._set_mode("guided"))
        guided_hint_text = ("ⓘ Recommended for most users, especially if you're new to Linux or want a hassle-free experience. " +
                        "You'll get helpful guidance and sensible defaults while still having the option to customize key choices.")
        guided_hint = self.hint_label(guided_hint_text)

        self.balanced_radio = QRadioButton("Balanced Migration")
        self.balanced_radio.setToolTip("You'll get recommended defaults but can customize key choices.")
        self.balanced_radio.toggled.connect(lambda: self._set_mode("balanced"))
        balanced_hint_text = ("ⓘ Good if you want a mix of guidance and control. You'll receive recommendations for each step but can choose to customize or skip them as you go.")
        balanced_hint = self.hint_label(balanced_hint_text)

        self.expert_radio = QRadioButton("Expert Migration")
        self.expert_radio.setToolTip("You'll have full control and see all options upfront.")
        self.expert_radio.toggled.connect(lambda: self._set_mode("expert"))
        expert_hint_text = ("ⓘ Best if you're experienced with migrations or want full control. You'll see all options and settings upfront and can customize everything from the start.")
        expert_hint = self.hint_label(expert_hint_text)

        question = "1. Choose a migration mode." \
        
        info = ("• Each mode offers different levels of guidance and control, yet all modes will produce the same final migration outcome. <br/>" + 
                "• You can switch modes at any time without affecting your progress."
                )

        questionnaire = self.create_guided_questionnaire(
            question=question,
            info=info,
            options=[
                self.guided_radio, 
                guided_hint,
                self.balanced_radio,
                balanced_hint,
                self.expert_radio,
                expert_hint
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
