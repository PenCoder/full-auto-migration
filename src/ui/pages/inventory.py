import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import threading

from src.loggers import get_logger
from src.ui.core import BasePage
from src.ui.utils.logger_handler import TextLoggerHandler


class InventoryPage(BasePage):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, controller)
        self.header["text"] = "Step 1: System Scan (Inventory)"

        desc = (
            "In this step, the wizard will collect a hardware and software inventory "
            "from your Windows 11 system using the underlying Python CLI.\n\n"
            "This may take a few minutes depending on the number of installed applications."
        )
        ttk.Label(self.body, text=desc, wraplength=800, justify="left").pack(
            anchor="w", pady=(0, 10)
        )

        self.run_button = ttk.Button(
            self.body, text="Run System Scan (hardware + software)", command=self.run_scan
        )
        self.run_button.pack(anchor="w", pady=(0, 10))

        # Output box
        self.output_box = tk.Text(self.body, height=15, wrap="word")
        self.output_box.pack(fill="both", expand=True)
        self.output_box.insert("end", "Output will appear here after the scan...\n")
        self.output_box.config(state="disabled")

        self.spinner_label = ttk.Label(self.body, text="")
        self.spinner_label.pack(anchor="w", pady=5)

        # SETUP LOGGER
        self.logger = get_logger("Inventory Page")
        self.log_handler = TextLoggerHandler(self.output_box)
        self.logger.addHandler(self.log_handler)

    def run_scan(self) -> None:
        # Disable button immediately
        self.run_button["state"] = tk.DISABLED
        self._append_output("Starting inventory: running 'inventory all'...\n")

        self.start_spinner(self.spinner_label)

        # Run CLI in background thread
        thread = threading.Thread(target=self._run_scan_worker, daemon=True)
        thread.start()

    def _run_scan_worker(self) -> None:
        result = self.controller.migration_service.run_inventory(self.logger)

        # Back to UI thread using after()
        self.after(0, self._scan_finished, result)

    def _scan_finished(self, output = None) -> None:
        self.stop_spinner()
        self._append_output(f"\nSystem scan completed!\n")

        if output:
            self.controller.state["hardware_inventory"] = output.get("hardware", {})
            self.controller.state["software_inventory"] = output.get("software", {})
           
            self.controller.state["inventory_completed"] = True
            messagebox.showinfo("Inventory", "System scan completed successfully.")
        else:
            messagebox.showerror(
                "Inventory",
                "System scan failed. Please check the output and logs for details.",
            )
        
        self.run_button["state"] = tk.NORMAL

    def _append_output(self, text: str) -> None:
        self.output_box.config(state="normal")
        self.output_box.insert("end", text)
        self.output_box.see("end")
        self.output_box.config(state="disabled")

    def before_leave(self) -> bool:
        mode = self.controller.state.get("mode", "guided")
        if not self.controller.state.get("inventory_completed", False):
            if mode == "guided":
                # Force completion in guided mode
                messagebox.showwarning(
                    "Inventory required",
                    "Please complete the inventory before continuing in Guided mode."
                )
                return False
            else:
                # Balanced / Expert can skip
                if not messagebox.askyesno(
                    "Continue without scan?",
                    "Inventory not completed. Continue anyway?"
                ):
                    return False
        # REMOVE LOGGER HANDLER
        self.logger.removeHandler(self.log_handler)

        return True

