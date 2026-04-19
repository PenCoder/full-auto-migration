from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QRadioButton, QSizePolicy, QVBoxLayout, QWidget

from src.qt_ui.state import QtUiState


class BasePage(QWidget):
    request_next = Signal()
    request_back = Signal()
    loading_progress = Signal(int)

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
        card.setMinimumWidth(560)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(14)

        page_layout.addWidget(card)
        page_layout.addStretch(1)
        return card_layout

    def create_trust_banner(self, text: str) -> QWidget:
        banner = QLabel(text)
        banner.setObjectName("TrustBanner")
        banner.setWordWrap(True)
        banner.setAlignment(Qt.AlignCenter)
        return banner
    
    def create_guided_panel(self, title: str, description: str | list[str]) -> QFrame:
        panel = QFrame()
        panel.setProperty("card", "true")
        panel.setProperty("guided", "true")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("StepTitle")
        layout.addWidget(title_lbl)
        if isinstance(description, str):
            description = [description]
        desc_lbl = QLabel()
        for desc in description:
            desc_lbl.setText(desc_lbl.text() + "• " + desc + "<br>")
        desc_lbl.setObjectName("BodyText")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        return panel
    
    def create_guided_questionnaire(self, question: str, info: str = None, options: list[QWidget]=None) -> QFrame:
        questionnaire = QFrame()
        questionnaire.setProperty("card", "true")
        questionnaire.setProperty("guided", "true")
        layout = QVBoxLayout(questionnaire)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(16)
        question_lbl = QLabel(question)
        question_lbl.setObjectName("StepTitle")
        question_lbl.setWordWrap(True)
        # question_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(question_lbl)

        if info:
            info_lbl = QLabel(info)
            info_lbl.setObjectName("BodyText")
            info_lbl.setWordWrap(True)
            # info_lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
            info_lbl.setStyleSheet("font-size: 14px;")
            layout.addWidget(info_lbl)
        if options:
            for option in options:
                layout.addWidget(option)

        return questionnaire
    
    def create_stat_chip_row(self, chips: list[str]) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addStretch(1)

        for text in chips:
            chip = QLabel(text)
            chip.setObjectName("StatChip")
            layout.addWidget(chip)

        layout.addStretch(1)
        return row
    
    def radio_with_hint(self, text: str, hint: str) -> QFrame:
        radio = QRadioButton(text)

        hint_label = QLabel(hint)
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: gray; font-size: 12px; margin-left: 20px;")
        hint_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)

        layout = QVBoxLayout()
        layout.addWidget(radio)
        layout.addWidget(hint_label)
        container = QFrame()
        container.setLayout(layout)
        return container
    
    def hint_label(self, text: str) -> QLabel:
        hint_label = QLabel(text)
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("font-size: 12px; margin-left: 20px;")
        # hint_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
        return hint_label
        

    def refresh(self) -> None:
        """Refresh page content when global state changes."""
