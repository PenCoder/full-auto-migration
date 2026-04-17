from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from src.qt_ui.pages.base_page import BasePage


class ModePage(BasePage):
    def __init__(self, ui_state) -> None:
        super().__init__(ui_state)
        self.setObjectName("StepCard")
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(16)

        step = QLabel("Step 1 of 4: Migration Mode")
        step.setObjectName("StepTitle")
        step.setAlignment(Qt.AlignCenter)
        root.addWidget(step)

        summary = QLabel(
            "Choose a simple mode now. You can open Expert Overrides at any point for advanced control."
        )
        summary.setObjectName("BodyText")
        summary.setWordWrap(True)
        summary.setAlignment(Qt.AlignCenter)
        root.addWidget(summary)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)

        self.guided_btn = self._mode_card(
            "Recommended Migration",
            "Safe defaults, least effort, best for novice users.",
            "guided",
        )
        self.balanced_btn = self._mode_card(
            "Custom Migration",
            "Balanced automation with selective choices.",
            "balanced",
        )
        self.expert_btn = self._mode_card(
            "System Assessment",
            "Insight-first flow with advanced controls.",
            "expert",
        )

        grid.addWidget(self.guided_btn, 0, 0)
        grid.addWidget(self.balanced_btn, 0, 1)
        grid.addWidget(self.expert_btn, 0, 2)
        root.addLayout(grid)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        continue_btn = QPushButton("Continue")
        continue_btn.setProperty("role", "cta")
        continue_btn.clicked.connect(self.request_next.emit)
        action_row.addWidget(continue_btn)
        root.addLayout(action_row)

    def _mode_card(self, title: str, detail: str, mode_value: str) -> QFrame:
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setProperty("card", True)
        card.setProperty("selected", False)

        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        h = QLabel(title)
        h.setObjectName("StepTitle")
        d = QLabel(detail)
        d.setObjectName("BodyText")
        d.setWordWrap(True)

        select_btn = QPushButton("Select")
        select_btn.setProperty("role", "primary")
        select_btn.clicked.connect(lambda: self._set_mode(mode_value))

        layout.addWidget(h)
        layout.addWidget(d)
        layout.addStretch(1)
        layout.addWidget(select_btn)
        return card

    def _set_mode(self, value: str) -> None:
        self.ui_state.mode = value
        self.refresh()

    def refresh(self) -> None:
        selected = self.ui_state.mode
        self._set_selected(self.guided_btn, selected == "guided")
        self._set_selected(self.balanced_btn, selected == "balanced")
        self._set_selected(self.expert_btn, selected == "expert")

    @staticmethod
    def _set_selected(card: QFrame, value: bool) -> None:
        card.setProperty("selected", value)
        style = card.style()
        style.unpolish(card)
        style.polish(card)
        card.update()
