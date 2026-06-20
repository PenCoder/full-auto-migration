"""Full-area overlay shown while the automatic migration pipeline runs."""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget


class AutomationOverlay(QWidget):
    """Covers the main content area while the automatic pipeline runs.

    Parent it to the central widget so it fills the whole window surface.
    It installs an event filter on its parent to stay correctly sized across
    window resizes without requiring any changes in the parent class.
    """

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        parent.installEventFilter(self)

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            "AutomationOverlay { background-color: rgba(22, 34, 61, 0.85); }"
        )
        self.resize(parent.size())

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(14)

        self._subtitle_label = QLabel("Running migration automatically")
        self._subtitle_label.setAlignment(Qt.AlignCenter)
        self._subtitle_label.setStyleSheet(
            "color: #8CAFFA; font-size: 15px; font-weight: 500; background: transparent;"
        )
        layout.addWidget(self._subtitle_label)

        self._phase_label = QLabel("Starting…")
        self._phase_label.setAlignment(Qt.AlignCenter)
        self._phase_label.setStyleSheet(
            "color: #FFFFFF; font-size: 23px; font-weight: 700; background: transparent;"
        )
        layout.addWidget(self._phase_label)

        spinner = QProgressBar()
        spinner.setRange(0, 0)
        spinner.setTextVisible(False)
        spinner.setFixedWidth(340)
        spinner.setFixedHeight(5)
        spinner.setStyleSheet(
            "QProgressBar {"
            "  background-color: rgba(255,255,255,0.12);"
            "  border-radius: 3px; border: none;"
            "}"
            "QProgressBar::chunk {"
            "  background-color: #8CAFFA; border-radius: 3px;"
            "}"
        )
        layout.addWidget(spinner, alignment=Qt.AlignCenter)

        self.hide()

    def set_phase(self, phase: str) -> None:
        """Update the phase text shown on the overlay."""
        self._phase_label.setText(phase)

    def set_subtitle(self, subtitle: str) -> None:
        """Update the small caption above the phase text."""
        self._subtitle_label.setText(subtitle)

    def eventFilter(self, obj: object, event: object) -> bool:
        if obj is self.parent() and hasattr(event, "type") and event.type() == QEvent.Resize:
            self.resize(self.parent().size())  # type: ignore[attr-defined]
        return super().eventFilter(obj, event)
