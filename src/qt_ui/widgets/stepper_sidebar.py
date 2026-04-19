from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class StepperSidebar(QWidget):
    def __init__(self, title: str, subtitle: str, steps: list[str]) -> None:
        super().__init__()
        self.steps = steps
        self.dot_labels: list[QLabel] = []
        self.title_labels: list[QLabel] = []
        self.meta_labels: list[QLabel] = []
        self._build_ui(title, subtitle)

    def _build_ui(self, title: str, subtitle: str) -> None:
        self.setObjectName("StepperPanel")
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 16, 14, 16)
        root.setSpacing(10)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("StepperTitle")
        title_lbl.setWordWrap(True)
        root.addWidget(title_lbl)

        subtitle_lbl = QLabel(subtitle)
        subtitle_lbl.setObjectName("StepperSubtitle")
        subtitle_lbl.setWordWrap(True)
        root.addWidget(subtitle_lbl)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("StepperSeparator")
        root.addWidget(line)

        for idx, step in enumerate(self.steps, start=1):
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 4, 0, 4)
            row_layout.setSpacing(8)
            row_layout.setAlignment(Qt.AlignTop)

            dot = QLabel(str(idx))
            dot.setAlignment(Qt.AlignCenter)
            dot.setObjectName("StepDot")
            dot.setFixedSize(24, 24)

            text_col = QWidget()
            text_col_layout = QVBoxLayout(text_col)
            text_col_layout.setContentsMargins(0, 0, 0, 0)
            text_col_layout.setSpacing(2)

            title_text, _, meta_text = step.partition("\n")

            step_title = QLabel(title_text)
            step_title.setWordWrap(True)
            step_title.setObjectName("StepHeading")

            step_meta = QLabel(meta_text)
            step_meta.setWordWrap(True)
            step_meta.setObjectName("StepMeta")

            text_col_layout.addWidget(step_title)
            if meta_text:
                text_col_layout.addWidget(step_meta)

            row_layout.addWidget(dot, alignment=Qt.AlignTop)
            row_layout.addWidget(text_col, stretch=1)

            self.dot_labels.append(dot)
            self.title_labels.append(step_title)
            self.meta_labels.append(step_meta)
            root.addWidget(row)

        root.addStretch(1)

    def set_active_index(self, index: int) -> None:
        for i, dot in enumerate(self.dot_labels):
            if i < index:
                state = "done"
                dot.setText("✓")
            elif i == index:
                state = "active"
                dot.setText(str(i + 1))
            else:
                state = "pending"
                dot.setText(str(i + 1))

            dot.setProperty("state", state)
            self._repolish(dot)

            title = self.title_labels[i]
            title.setProperty("state", state)
            self._repolish(title)

            meta = self.meta_labels[i]
            meta.setProperty("state", state)
            self._repolish(meta)

    @staticmethod
    def _repolish(widget: QWidget) -> None:
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()
