"""Navigation and page-state controller for the Qt migration window."""

from __future__ import annotations

from typing import Callable


class NavigationController:
    """Manage stack navigation and navigation button state."""

    def __init__(
        self,
        stack,
        stepper,
        back_btn,
        next_btn,
        clear_error_banner,
        is_auto_running,
        is_busy: Callable[[], bool] | None = None,
    ):
        self.stack = stack
        self.stepper = stepper
        self.back_btn = back_btn
        self.next_btn = next_btn
        self.clear_error_banner = clear_error_banner
        self.is_auto_running = is_auto_running
        self.is_busy = is_busy or (lambda: False)

    def _page_is_blocked(self) -> bool:
        """Return True if the current page has a background task running."""
        page = self.stack.currentWidget()
        return bool(getattr(page, "is_processing", False))

    def _page_can_proceed(self) -> bool:
        """Return True if the current page permits forward navigation."""
        page = self.stack.currentWidget()
        can_proceed = getattr(page, "can_proceed", None)
        return can_proceed() if callable(can_proceed) else True

    def _globally_blocked(self) -> bool:
        return self.is_auto_running() or self.is_busy() or self._page_is_blocked()

    def next_page(self) -> None:
        if self._globally_blocked() or not self._page_can_proceed():
            return
        self.clear_error_banner()
        current = self.stack.currentIndex()
        if current < self.stack.count() - 1:
            self.stack.setCurrentIndex(current + 1)
            page = self.stack.currentWidget()
            refresh = getattr(page, "refresh", None)
            if callable(refresh):
                refresh()
            self.sync_nav()

    def prev_page(self) -> None:
        if self._globally_blocked():
            return
        self.clear_error_banner()
        current = self.stack.currentIndex()
        if current > 0:
            self.stack.setCurrentIndex(current - 1)
            self.sync_nav()

    def go_to_page(self, index: int) -> None:
        """Navigate directly to a completed page (index must be before the current page)."""
        if self._globally_blocked():
            return
        current = self.stack.currentIndex()
        if index < 0 or index >= current:
            return
        self.clear_error_banner()
        self.stack.setCurrentIndex(index)
        page = self.stack.currentWidget()
        refresh = getattr(page, "refresh", None)
        if callable(refresh):
            refresh()
        self.sync_nav()

    def sync_nav(self) -> None:
        current = self.stack.currentIndex()
        blocked = self._globally_blocked()
        self.back_btn.setEnabled(not blocked and current > 0)
        self.next_btn.setEnabled(
            not blocked and current < self.stack.count() - 1 and self._page_can_proceed()
        )
        self.stepper.set_active_index(current)
        if current == self.stack.count() - 1:
            self.next_btn.setText("Done")
        else:
            self.next_btn.setText("Next")
