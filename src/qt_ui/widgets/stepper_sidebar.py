from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class StepperSidebar(QWidget):
    def __init__(self, title: str, subtitle: str, steps: list[str]) -> None:
        super().__init__()
        self.steps = steps
        self.dot_labels: list[QLabel] = []
        self.text_labels: list[QLabel] = []
        self._build_ui(title, subtitle)

    def _build_ui(self, title: str, subtitle: str) -> None:
        self.setObjectName("StepperPanel")
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 16, 14, 16)
        root.setSpacing(10)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("StepperTitle")
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
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(0, 4, 0, 4)
            row_layout.setSpacing(4)

            dot = QLabel(str(idx))
            dot.setAlignment(Qt.AlignCenter)
            dot.setObjectName("StepDot")
            dot.setFixedSize(24, 24)

            text = QLabel(step)
            text.setWordWrap(True)
            text.setObjectName("StepText")

            row_layout.addWidget(dot, alignment=Qt.AlignLeft)
            row_layout.addWidget(text)

            self.dot_labels.append(dot)
            self.text_labels.append(text)
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

            text = self.text_labels[i]
            text.setProperty("state", state)
            self._repolish(text)

    @staticmethod
    def _repolish(widget: QWidget) -> None:
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()
