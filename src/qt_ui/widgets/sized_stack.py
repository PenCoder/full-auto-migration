"""QStackedWidget that reports only the current page's size.

By default QStackedWidget's sizeHint/minimumSizeHint is the maximum across
all child pages (even hidden ones), which inflates the apparent height of
every page when the stack is wrapped in a QScrollArea — short pages get
extra empty scrollable space sized for the tallest page ever added to the
stack. Delegating to the current widget fixes that.
"""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QStackedWidget


class CurrentSizeStackedWidget(QStackedWidget):
    """A QStackedWidget whose size hints track only the visible page."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.currentChanged.connect(lambda _index: self.updateGeometry())

    def sizeHint(self) -> QSize:
        current = self.currentWidget()
        return current.sizeHint() if current else super().sizeHint()

    def minimumSizeHint(self) -> QSize:
        current = self.currentWidget()
        return current.minimumSizeHint() if current else super().minimumSizeHint()
