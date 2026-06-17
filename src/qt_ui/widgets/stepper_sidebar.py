"""Reusable sidebar stepper widget for wizard navigation."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class _StepRow(QWidget):
    """A single step row that becomes clickable when its state is 'done'."""

    def __init__(self, index: int, on_click, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._index = index
        self._on_click = on_click
        self._clickable = False

    def set_clickable(self, clickable: bool) -> None:
        self._clickable = clickable
        self.setCursor(Qt.PointingHandCursor if clickable else Qt.ArrowCursor)
        self.setProperty("clickable", "true" if clickable else "false")
        style = self.style()
        style.unpolish(self)
        style.polish(self)

    def mousePressEvent(self, event) -> None:
        if self._clickable:
            self._on_click(self._index)
        super().mousePressEvent(event)


class StepperSidebar(QWidget):
    """Render a vertical step list with state-aware, clickable labels."""

    step_clicked = Signal(int)

    def __init__(self, title: str, subtitle: str, steps: list[str]) -> None:
        super().__init__()
        self.steps = steps
        self.dot_labels: list[QLabel] = []
        self.title_labels: list[QLabel] = []
        self.meta_labels: list[QLabel] = []
        self._row_widgets: list[_StepRow] = []
        self._step_states: list[str] = ["pending"] * len(steps)
        self._build_ui(title, subtitle)

    def _build_ui(self, title: str, subtitle: str) -> None:
        self.setObjectName("StepperPanel")
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 18, 16, 16)
        root.setSpacing(8)

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

        for idx, step in enumerate(self.steps):
            row = _StepRow(idx, self._on_row_click)
            row.setMinimumHeight(52)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(4, 6, 4, 6)
            row_layout.setSpacing(10)
            row_layout.setAlignment(Qt.AlignTop)

            dot = QLabel(str(idx + 1))
            dot.setAlignment(Qt.AlignCenter)
            dot.setObjectName("StepDot")
            dot.setFixedSize(26, 26)

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
            self._row_widgets.append(row)
            root.addWidget(row)

        root.addStretch(1)

    def _on_row_click(self, index: int) -> None:
        if self._step_states[index] == "done":
            self.step_clicked.emit(index)

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

            self._step_states[i] = state
            self._row_widgets[i].set_clickable(state == "done")

            dot.setProperty("state", state)
            self._repolish(dot)

            title = self.title_labels[i]
            title.setProperty("state", state)
            self._repolish(title)

            meta = self.meta_labels[i]
            meta.setProperty("state", state)
            self._repolish(meta)

    def mark_step_done(self, index: int) -> None:
        """Mark a single step as done (✓) without affecting surrounding steps.

        Safe to call repeatedly or out of order — only updates the given index.
        """
        if index < 0 or index >= len(self.dot_labels):
            return
        if self._step_states[index] == "done":
            return

        dot = self.dot_labels[index]
        dot.setText("✓")
        self._step_states[index] = "done"
        self._row_widgets[index].set_clickable(True)

        for widget in (dot, self.title_labels[index], self.meta_labels[index]):
            widget.setProperty("state", "done")
            self._repolish(widget)

    @staticmethod
    def _repolish(widget: QWidget) -> None:
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()
