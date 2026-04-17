from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from src.qt_ui.state import QtUiState


class BasePage(QWidget):
    request_next = Signal()
    request_back = Signal()

    def __init__(self, ui_state: QtUiState) -> None:
        super().__init__()
        self.ui_state = ui_state

    def create_center_card_layout(self, max_width: int = 920) -> QVBoxLayout:
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addStretch(1)

        card = QWidget()
        card.setObjectName("StepCard")
        card.setMaximumWidth(max_width)
        card.setMinimumWidth(760)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(16)

        page_layout.addWidget(card, alignment=Qt.AlignHCenter)
        page_layout.addStretch(1)
        return card_layout

    def refresh(self) -> None:
        """Refresh page content when global state changes."""
