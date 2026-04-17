from tkinter import messagebox, ttk
import tkinter as tk
import threading

from src.loggers import get_logger
from src.ui.core import BasePage
from src.ui.utils.logger_handler import TextLoggerHandler


class AnalysisPage(BasePage):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, controller)
        self.header["text"] = "Step 2: Compatibility Analysis"

        desc = (
            "Based on the collected inventory, this step runs the analysis modules to "
            "generate a hardware compatibility matrix and a software mapping table.\n\n"
            "These results help estimate how well your current system will migrate to Linux Mint."
        )
        ttk.Label(self.body, text=desc, wraplength=800, justify="left").pack(
            anchor="w", pady=(0, 10)
        )

        self.run_button = ttk.Button(
            self.body, text="Run Analysis (hardware + software)", command=self.run_analysis
        )
        self.run_button.pack(anchor="w", pady=(0, 10))

        self.output_box = tk.Text(self.body, height=15, wrap="word")
        self.output_box.pack(fill="both", expand=True)
        self.output_box.insert(
            "end", "Output will appear here after the analysis is run...\n"
        )
        self.output_box.config(state="disabled")

        # SETUP LOGGER
        self.logger = get_logger("Analysis Page")
        self.log_handler = TextLoggerHandler(self.output_box)
        self.logger.addHandler(self.log_handler)

   
    def run_analysis(self) -> None:
        # Disable button immediately
        self.run_button["state"] = tk.DISABLED
        self._append_output("Starting analysis: running 'analyze all'...\n")

        # Run CLI in background thread
        thread = threading.Thread(target=self._run_scan_worker, daemon=True)
        thread.start()

    def _run_scan_worker(self) -> None:
        hw_inventory = self.controller.state.get("hardware_inventory", {})
        sw_inventory = self.controller.state.get("software_inventory", {})
        
        result = self.controller.migration_service.run_analysis(sw_inventory, hw_inventory, self.logger)
        
        self.after(0, self._scan_finished, result)

    def _scan_finished(self, output=None) -> None:
        self._append_output(f"\nSystem analysis completed.\n")

        if output is not None:
            self.controller.state["analysis_completed"] = True
            messagebox.showinfo("Analysis", "Analysis completed successfully.")
        else:
            messagebox.showerror(
                "Analysis",
                "Analysis failed. Please check the output and logs for details.",
            )

        self.run_button["state"] = tk.NORMAL

    def _append_output(self, text: str) -> None:
        self.output_box.config(state="normal")
        self.output_box.insert("end", text)
        self.output_box.see("end")
        self.output_box.config(state="disabled")

    def before_leave(self) -> bool:
        if not self.controller.state.get("analysis_completed", False):
            if not messagebox.askyesno(
                "Continue without analysis?",
                "You have not completed the analysis. Continue anyway?",
            ):
                return False
            
        # REMOVE LOGGER HANDLER
        self.logger.removeHandler(self.log_handler)

        return True

