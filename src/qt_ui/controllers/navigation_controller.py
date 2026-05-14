"""Navigation and page-state controller for the Qt migration window."""

from __future__ import annotations


class NavigationController:
    """Manage stack navigation and navigation button state."""

    def __init__(self, stack, stepper, back_btn, next_btn, clear_error_banner, is_auto_running):
        self.stack = stack
        self.stepper = stepper
        self.back_btn = back_btn
        self.next_btn = next_btn
        self.clear_error_banner = clear_error_banner
        self.is_auto_running = is_auto_running

    def next_page(self) -> None:
        if self.is_auto_running():
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
        if self.is_auto_running():
            return
        self.clear_error_banner()
        current = self.stack.currentIndex()
        if current > 0:
            self.stack.setCurrentIndex(current - 1)
            self.sync_nav()

    def sync_nav(self) -> None:
        current = self.stack.currentIndex()
        if not self.is_auto_running():
            self.back_btn.setEnabled(current > 0)
            self.next_btn.setEnabled(current < self.stack.count() - 1)
        self.stepper.set_active_index(current)
        if current == self.stack.count() - 1:
            self.next_btn.setText("Done")
        else:
            self.next_btn.setText("Next")
