from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QProgressBar, QVBoxLayout

from src.qt_ui.pages.base_page import BasePage


class DataSelectionPage(BasePage):
    def __init__(self, ui_state) -> None:
        super().__init__(ui_state)
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        root = self.create_center_card_layout()

        step = QLabel("Step 2 of 4: Data Selection")
        step.setObjectName("StepTitle")
        step.setAlignment(Qt.AlignCenter)
        root.addWidget(step)

        step_progress = QProgressBar()
        step_progress.setRange(0, 100)
        step_progress.setValue(50)
        step_progress.setTextVisible(False)
        step_progress.setFixedHeight(10)
        root.addWidget(step_progress)

        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(66)
        root.addWidget(progress)

        question = QLabel("Where should we keep your files safe during the move?")
        question.setWordWrap(True)
        question.setObjectName("HeroTitle")
        question.setAlignment(Qt.AlignCenter)
        root.addWidget(question)

        info = QLabel(
            "Simple mode keeps this page minimal. Open Expert Overrides for per-category tuning if needed."
        )
        info.setObjectName("BodyText")
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignCenter)
        root.addWidget(info)

        row = QHBoxLayout()

        keep_all = QPushButton("Keep Them All")
        keep_all.setProperty("role", "primary")
        keep_all.setMinimumHeight(64)
        keep_all.clicked.connect(lambda: self._set_strategy("keep_all"))
        row.addWidget(keep_all)

        choose = QPushButton("Let Me Choose")
        choose.setProperty("role", "primary")
        choose.setMinimumHeight(64)
        choose.clicked.connect(lambda: self._set_strategy("let_me_choose"))
        row.addWidget(choose)

        root.addLayout(row)

        next_btn = QPushButton("Continue")
        next_btn.setProperty("role", "cta")
        next_btn.setFixedWidth(220)
        next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(next_btn, alignment=Qt.AlignHCenter)

    def _set_strategy(self, strategy: str) -> None:
        self.ui_state.data_strategy = strategy

    def refresh(self) -> None:
        # Kept intentionally simple for this page.
        return
