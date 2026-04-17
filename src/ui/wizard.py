import sys
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk

from src.services.restore_service import RestoreService
from src.config import MigrationConfigRoot, load_software_mapping
from src.services.migration_service import MigrationService
from src.ui.core import BasePage

from src.ui.pages.analysis import AnalysisPage
from src.ui.pages.backup import BackupPage
from src.ui.pages.finish import FinishPage
from src.ui.pages.inventory import InventoryPage
from src.ui.pages.modeSelection import ModeSelectionPage
from src.ui.pages.summary import SummaryPage
from src.ui.pages.welcome import WelcomePage
from src.ui.pages.preferences import MigrationPreferencesPage
from src.ui.pages.restore import RestorePage
from src.ui.pages.validation import ValidationPage


DEFAULT_FOLDERS = {
    "Documents": True,
    "Pictures": True,
    "Downloads": True,
    "Desktop": True,
}


class MigrationWizard(tk.Tk):
    """
    Main window for the Semi-Automated Migration Wizard.
    Orchestrates navigation between pages and holds shared state.
    """

    def __init__(self, app_config: MigrationConfigRoot, runtime: str) -> None:
        super().__init__()

        self.title("Semi-Automated Migration Wizard")
        self.geometry("1280x760")
        self.minsize(1100, 680)

        self.app_config = app_config
        self.demo_mode = app_config.app_demo.mode

        self.software_map = load_software_mapping(app_config.migration.software_map_config)

        # Shared state between pages (mode, paths, flags, etc.)
        self.state = {
            "mode": "guided",  # guided | balanced | expert
            "inventory_completed": False,
            "analysis_completed": False,
            "backup_completed": False,
            "last_cli_output": "",
            "selected_folders": DEFAULT_FOLDERS.copy(),
            "file_types": app_config.source_system.file_types,
        }

        # Setup migration service
        self.migration_service = MigrationService(self.app_config, self.state)

        # Top-level container
        container = ttk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.container = container
        self.pages = []

        self.runtime_mode = runtime

        # Initialize all pages
        for PageClass in self.build_pages():
            page = PageClass(parent=container, controller=self)
            self.pages.append(page)
            page.grid(row=0, column=0, sticky="nsew")

        # Navigation bar
        self.nav_frame = ttk.Frame(self)
        self.nav_frame.pack(side="bottom", fill="x")

        self.back_button = ttk.Button(
            self.nav_frame, text="⟵ Back", command=self.go_back
        )
        self.next_button = ttk.Button(
            self.nav_frame, text="Next ⟶", command=self.go_next
        )
        self.cancel_button = ttk.Button(
            self.nav_frame, text="Cancel", command=self.on_cancel
        )

        self.back_button.pack(side="left", padx=10, pady=10)
        self.cancel_button.pack(side="right", padx=10, pady=10)
        self.next_button.pack(side="right", padx=10, pady=10)

        self.current_index = 0
        if self.pages:
            self.show_page(self.pages[self.current_index])

    # ---------- Build Pages ----------

    def build_pages(self) -> None:
        if self.runtime_mode == "windows":
            return [
                WelcomePage,
                ModeSelectionPage,
                MigrationPreferencesPage,
                InventoryPage,
                AnalysisPage,
                BackupPage,
                SummaryPage,
            ]
        elif self.runtime_mode == "linux":
            return [
                WelcomePage,
                RestorePage,
                ValidationPage,
                FinishPage,
            ]
        return []

    # ---------- Navigation ----------

    def show_page(self, page) -> None:
        frame = page
        frame.tkraise()

        on_show = getattr(frame, "on_show", None)
        if callable(on_show):
            on_show()

        self.update_nav_buttons()

    def update_nav_buttons(self) -> None:
        # Disable Back on first page
        self.back_button["state"] = tk.NORMAL if self.current_index > 0 else tk.DISABLED
        # Next text changes on last page
        if self.current_index == len(self.pages) - 1:
            self.next_button["text"] = "Finish"
        else:
            self.next_button["text"] = "Next ⟶"

    def go_back(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self.show_page(self.pages[self.current_index])

    def go_next(self) -> None:
        # Let current page veto navigation if needed
        current_page = self.pages[self.current_index]
        before_leave = getattr(current_page, "before_leave", None)
        
        if callable(before_leave):
            if before_leave() is False:
                # Page requested to stay (e.g. validation failed)
                return
           
        if self.current_index < len(self.pages) - 1:
            self.current_index += 1
            self.show_page(self.pages[self.current_index])
        else:
            # Finish
            self.on_finish()

    def on_cancel(self) -> None:
        if messagebox.askyesno("Cancel", "Do you really want to exit the wizard?"):
            self.destroy()

    def on_finish(self) -> None:
        messagebox.showinfo(
            "Migration Wizard", "Wizard completed. You can now close the application."
        )
        self.destroy()

