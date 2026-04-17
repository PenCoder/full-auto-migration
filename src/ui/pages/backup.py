import threading
from tkinter import messagebox, ttk
import tkinter as tk


from src.loggers import get_logger
from src.ui.core import BasePage
from src.ui.utils.logger_handler import TextLoggerHandler


class BackupPage(BasePage):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, controller)
        self.header["text"] = "Step 3: Backup Manifest"

        desc = (
            "This step generates a backup manifest from your configured paths. "
            "The manifest contains file hashes and metadata and is used later for "
            "verifying restore integrity.\n\n"
            "The actual backup and restore process will be further implemented in later milestones."
        )
        ttk.Label(self.body, text=desc, wraplength=800, justify="left").pack(
            anchor="w", pady=(0, 10)
        )

        self.run_button = ttk.Button(
            self.body,
            text="Generate Backup Manifest",
            command=self.run_backup_manifest,
        )
        self.run_button.pack(anchor="w", pady=(0, 10))

        self.output_box = tk.Text(self.body, height=15, wrap="word")
        self.output_box.pack(fill="both", expand=True)
        self.output_box.insert(
            "end",
            "Output will appear here after the backup manifest is generated...\n",
        )
        self.output_box.config(state="disabled")

        # SETUP LOGGER
        self.logger = get_logger("Backup Page")
        self.log_handler = TextLoggerHandler(self.output_box)
        self.logger.addHandler(self.log_handler)
        
    def run_backup_manifest(self) -> None:
        # Disable button immediately
        self.run_button["state"] = tk.DISABLED
        self._append_output("Starting backup manifest generation: running 'backup'...\n")

        # Run CLI in background thread
        thread = threading.Thread(target=self._run_scan_worker, daemon=True)
        thread.start()

    def _run_scan_worker(self) -> None:
        selected_folders = self.controller.state.get("selected_folders", {})
        selected_file_types = self.controller.state.get("file_types", {})
        if selected_folders:
            selected_folders = [f"~/{name}" for name, selected in selected_folders.items() if selected]
            results = self.controller.migration_service.run_backup(selected_folders, selected_file_types, self.logger)

            # Back to UI thread using after()
            self.after(0, self._scan_finished, results)

    def _scan_finished(self, output: dict) -> None:
        self._append_output("\n--- CLI OUTPUT ---\n")
        # self._append_output(output + "\n")
        self._append_output(f"\nSystem back complete.\n")

        if output:
            self.controller.state["backup_completed"] = True
            messagebox.showinfo("Backup", "Backup manifest generated successfully.")
        else:
            messagebox.showerror(
                "Backup",
                "Backup manifest generation failed. Please check the output and logs.",
            )

        self.run_button["state"] = tk.NORMAL

    def _append_output(self, text: str) -> None:
        self.output_box.config(state="normal")
        self.output_box.insert("end", text)
        self.output_box.see("end")
        self.output_box.config(state="disabled")

    def before_leave(self) -> bool:
        if not self.controller.state.get("backup_completed", False):
            if not messagebox.askyesno(
                "Continue without backup?",
                "You have not generated a backup manifest. Continue anyway?",
            ):
                return False
        return True

