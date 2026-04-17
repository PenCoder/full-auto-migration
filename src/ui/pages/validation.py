import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledText
from pathlib import Path
import json
import shutil

from src.constants import RESTORE_DIR, RESTORE_REPORT
from src.ui.core import BasePage


class ValidationPage(BasePage):
    """
    Validates the result of the restore operation using restore_report.json
    """
    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.header.config(text="Restore Validation")

        self.body_frame = ttk.Frame(self.body)
        self.body_frame.pack(anchor="w", pady=10)

        self.report = {}

        ttk.Button(
            self.body,
            text="Run Validation",
            command=self.run_validation,
        ).pack(anchor="w", pady=10)

        # Output box
        self.output_box = ScrolledText(self.body, height=15, wrap="word")
        self.output_box.pack(fill="both", expand=True)

    def run_validation(self):
        for w in self.body_frame.winfo_children():
            w.destroy()

        report_path = RESTORE_REPORT

        if not report_path.exists():
            ttk.Label(
                self.body_frame,
                text="Restore report not found. Run restore first.",
                foreground="red",
            ).pack(anchor="w")
            return

        with report_path.open(encoding="utf-8") as f:
            self.report = json.load(f)

        self._append_output("File Integrity Validation:\n\n")

        for fentry in self.report.get("files_restored", []).copy():
            exists = Path(fentry["destination"]).exists()
            status = "OK" if exists else "MISSING"
            fentry["status"] = status

            self._append_output(f"{fentry['relative_path']} → {status}\n")

        self._append_output("\nApplication Validation:\n\n")

        for app in self.report.get("applications_installed", []).copy():
            linux_pkg = app.get("linux_package")
            ok = shutil.which(linux_pkg) is not None
            status = "OK" if ok else "NOT FOUND"
            app["status"] = status

            self._append_output(f"{app['windows_name']} → {linux_pkg} → {status}\n")

        with report_path.open("w", encoding="utf-8") as f:
            json.dump(self.report, f, indent=2)

    def _append_output(self, text: str) -> None:
        self.output_box.insert("end", text)
        self.output_box.see("end")

    def before_leave(self) -> bool:
        self.controller.state["validation_report"] = self.report
        return True
