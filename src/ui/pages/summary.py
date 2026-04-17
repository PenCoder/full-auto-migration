import ttkbootstrap as ttk

from src.ui.core import BasePage


class SummaryPage(BasePage):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, controller)
        self.header["text"] = "Summary & Next Steps"

        self.summary_label = ttk.Label(
            self.body, text="", wraplength=800, justify="left"
        )
        self.summary_label.pack(anchor="w", pady=(0, 10))

        info_text = (
            "Next steps (outside this wizard):\n"
            "  • Create a Linux Mint Live USB (e.g., with Rufus on Windows).\n"
            "  • Install Linux Mint on the target machine.\n"
            "  • (Future work) Run the restore and validation tools on the Linux side.\n\n"
            "You can now close the wizard or go back to review previous steps."
        )
        ttk.Label(self.body, text=info_text, wraplength=800, justify="left").pack(
            anchor="w", pady=(10, 0)
        )

    def on_show(self) -> None:
        state = self.controller.state
        mode = state.get("mode", "guided")
        inv = "Completed" if state.get("inventory_completed") else "Not completed"
        ana = "Completed" if state.get("analysis_completed") else "Not completed"
        bak = "Completed" if state.get("backup_completed") else "Not completed"

        summary = (
            f"Migration Wizard Summary\n\n"
            f"Mode selected: {mode}\n"
            f"Inventory: {inv}\n"
            f"Analysis: {ana}\n"
            f"Backup manifest: {bak}\n"
        )

        self.summary_label["text"] = summary