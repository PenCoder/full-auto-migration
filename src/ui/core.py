
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.scrolled import ScrolledFrame
import tkinter as tk

class BasePage(ttk.Frame):
    """
    Common base for all pages. Provides a consistent layout.
    """

    def __init__(self, parent, controller) -> None:
        super().__init__(parent)
        self.controller = controller

        self.header = ttk.Label(self, text="", font=("Segoe UI", 16, "bold"))
        self.header.pack(pady=(20, 10))

        # self.body = ttk.Frame(self)
        self.body = ScrolledFrame(self, autohide=True)
        self.body.pack(fill=BOTH, expand=YES, padx=20, pady=10)

    # Optional hooks
    def on_show(self) -> None:
        """Called when the page is shown."""
        pass

    def before_leave(self) -> bool | None:
        """Return False to block navigation to next page."""
        return None
    
    def start_spinner(self, label_widget):
        self._spinner_running = True
        self._spinner_chars = ["|", "/", "-", "\\"]
        self._spinner_index = 0
        self._spinner_label = label_widget
        self._animate_spinner()

    def _animate_spinner(self):
        if not getattr(self, "_spinner_running", False):
            return
        char = self._spinner_chars[self._spinner_index]
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_chars)
        self._spinner_label.config(text=f"Running... {char}")
        self.after(100, self._animate_spinner)

    def stop_spinner(self):
        self._spinner_running = False
        if hasattr(self, "_spinner_label"):
            self._spinner_label.config(text="Done.")
