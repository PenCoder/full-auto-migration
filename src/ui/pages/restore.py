import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import threading

from src.ui.core import BasePage
from src.services.restore_service import RestoreService


class RestorePage(BasePage):
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.header.config(text="Restore Migration Bundle")

        self.bundle_path: Path | None = None
        self._build_ui()

    def _build_ui(self):
        ttk.Label(self.body, text="Select the migration bundle directory:", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 5))

        ttk.Button(self.body, text="Choose Folder…", command=self._select_bundle).pack(anchor="w")
        self.bundle_label = ttk.Label(self.body, text="No folder selected")
        self.bundle_label.pack(anchor="w", pady=(5, 15))

        ttk.Label(self.body, text="Restore Progress:", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.progress_label = ttk.Label(self.body, text="0%")
        self.progress_label.pack(anchor="w", pady=(5, 0))

        self.progress = ttk.Progressbar(self.body, mode="determinate", length=420, maximum=100)
        self.progress.pack(anchor="w", pady=(5, 15))

        self.start_btn = ttk.Button(self.body, text="Start Restore", command=self._start_restore, state="disabled")
        self.start_btn.pack(anchor="w")

    def _select_bundle(self):
        path = filedialog.askdirectory(title="Select Migration Bundle")
        if not path:
            return
        self.bundle_path = Path(path)
        self.bundle_label.config(text=str(self.bundle_path))
        self.start_btn.config(state="normal")

        self.controller.state["bundle_dir"] = str(self.bundle_path)

    def _start_restore(self):
        if not self.bundle_path:
            return

        confirm = messagebox.askyesno(
            "Confirm Restore",
            "This will restore files and install applications.\n"
            "Administrator authentication may be required.\n\nProceed?",
        )
        if not confirm:
            return

        self.start_btn.config(state="disabled")
        self._set_progress(0, "Starting…")

        thread = threading.Thread(target=self._run_restore, daemon=True)
        thread.start()

    def _set_progress(self, percent: int, msg: str):
        self.progress["value"] = percent
        self.progress_label.config(text=f"{percent}% — {msg}")

    def _progress_cb(self, percent: int, msg: str):
        # Ensure UI update happens on main thread
        self.controller.after(0, lambda: self._set_progress(percent, msg))

    def _run_restore(self):
        try:
            target_home = Path.home() / "Restored_Migration"
            service = RestoreService(bundle_dir=self.bundle_path, target_home=target_home, progress_cb=self._progress_cb)
            service.run_restore()
            self.controller.state["restored_applications"] = service.apps_to_install
            self.controller.after(0, self._on_restore_success)
        except Exception as exc:
            self.controller.after(0, lambda e=exc: self._on_restore_error(e))

    def _on_restore_success(self):
        self._set_progress(100, "Completed.")
        self.start_btn.config(state="normal")
        messagebox.showinfo("Restore Complete", "Your files and applications have been restored successfully.")

    def _on_restore_error(self, exc: Exception):
        self.start_btn.config(state="normal")
        messagebox.showerror("Restore Failed", f"An error occurred during restore:\n\n{exc}")

    def before_leave(self) -> bool:
        return True
