from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel


class HorizontalStepper(QWidget):
    """Horizontal progress stepper with connected nodes and labels."""

    def __init__(self, steps: list[str]) -> None:
        super().__init__()
        self.steps = steps
        self.current_index = 0
        self.node_labels: list[QLabel] = []
        self.setObjectName("HorizontalStepper")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(24)

        # Canvas for drawing connectors and nodes
        self.canvas = _StepperCanvas(self.steps, self)
        root.addWidget(self.canvas)

        # Labels row
        labels_layout = QHBoxLayout()
        labels_layout.setContentsMargins(0, 0, 0, 0)
        labels_layout.setSpacing(0)

        for i, step in enumerate(self.steps):
            label = QLabel(step)
            label.setAlignment(Qt.AlignCenter)
            label.setObjectName("StepLabel")
            label.setProperty("state", "pending")
            labels_layout.addWidget(label, stretch=1)
            self.node_labels.append(label)

        root.addLayout(labels_layout)

    def set_active_index(self, index: int) -> None:
        self.current_index = index
        for i, label in enumerate(self.node_labels):
            if i < index:
                state = "done"
            elif i == index:
                state = "active"
            else:
                state = "pending"

            label.setProperty("state", state)
            style = label.style()
            style.unpolish(label)
            style.polish(label)
            label.update()

        self.canvas.update()


class _StepperCanvas(QWidget):
    """Renders the progress nodes and connecting lines."""

    def __init__(self, steps: list[str], parent: HorizontalStepper) -> None:
        super().__init__(parent)
        self.steps = steps
        self.parent_stepper = parent
        self.setFixedHeight(60)
        self.setStyleSheet("background: transparent;")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        if len(self.steps) == 0:
            painter.end()
            return

        width = self.width()
        height = self.height()
        step_count = len(self.steps)

        if step_count == 1:
            node_x = [width // 2]
        else:
            node_x = [
                int((width / (step_count - 1)) * i) for i in range(step_count)
            ]

        node_y = height // 2
        node_radius = 18

        # Draw connecting lines
        for i in range(len(node_x) - 1):
            x1, x2 = node_x[i], node_x[i + 1]
            is_done = i < self.parent_stepper.current_index

            line_color = QColor("#70e0a1") if is_done else QColor("#d0d0d0")
            pen = QPen(line_color, 3)
            painter.setPen(pen)
            painter.drawLine(x1 + node_radius, node_y, x2 - node_radius, node_y)

        # Draw nodes
        for i, x in enumerate(node_x):
            if i < self.parent_stepper.current_index:
                # Completed: green circle with checkmark
                painter.setBrush(QBrush(QColor("#70e0a1")))
                painter.setPen(QPen(QColor("#70e0a1"), 1))
                painter.drawEllipse(x - node_radius, node_y - node_radius, node_radius * 2, node_radius * 2)
                painter.setPen(QPen(QColor("#ffffff"), 2))
                font = QFont()
                font.setPointSize(16)
                font.setWeight(QFont.Bold)
                painter.setFont(font)
                painter.drawText(
                    x - node_radius,
                    node_y - node_radius,
                    node_radius * 2,
                    node_radius * 2,
                    Qt.AlignCenter,
                    "✓",
                )
            elif i == self.parent_stepper.current_index:
                # Current: blue circle
                painter.setBrush(QBrush(QColor("#4a9eff")))
                painter.setPen(QPen(QColor("#4a9eff"), 1))
                painter.drawEllipse(x - node_radius, node_y - node_radius, node_radius * 2, node_radius * 2)
            else:
                # Pending: light gray circle
                painter.setBrush(QBrush(QColor("#e0e0e0")))
                painter.setPen(QPen(QColor("#999999"), 1))
                painter.drawEllipse(x - node_radius, node_y - node_radius, node_radius * 2, node_radius * 2)

        painter.end()
