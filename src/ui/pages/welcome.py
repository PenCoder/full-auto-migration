import ttkbootstrap as ttk

from src.ui.core import BasePage



class WelcomePage(BasePage):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, controller)
        
        if controller.runtime_mode == "windows":
            self.windows_view()
        else:
            self.linux_view()

    def windows_view(self):
        self.header["text"] = "Welcome to the Migration Wizard"

        text = (
            "This wizard will guide you through a semi-automated migration from "
            "Windows 11 to Linux Mint.\n\n"
            "You will:\n"
            "  • Scan your current system (hardware and software)\n"
            "  • Review compatibility analysis\n"
            "  • Prepare a backup manifest\n"
            "  • Receive migration and restore instructions\n\n"
            "Click 'Next' to choose your level of automation and guidance."
        )

        label = ttk.Label(self.body, text=text, justify="left", wraplength=800)
        label.pack(anchor="w")

    def linux_view(self):
        self.header.config(text="Welcome to Linux Migration Restore")

        ttk.Label(
            self.body,
            text=(
                "This system is running on Linux.\n\n"
                "You are about to restore files and applications from a "
                "previously created Windows migration bundle.\n\n"
                "No data will be collected from this system."
            ),
            wraplength=600,
            justify="left",
        ).pack(anchor="w", pady=20)

        ttk.Label(
            self.body,
            text=(
                "Steps:\n"
                "• Select migration bundle\n"
                "• Restore files\n"
                "• Install applications automatically\n"
                "• Validate system readiness"
            ),
            justify="left",
        ).pack(anchor="w", pady=10)

