import tkinter as tk
import ttkbootstrap as ttk
from src.ui.core import BasePage


DEFAULT_FOLDERS = {
    "Documents": True,
    "Pictures": True,
    "Downloads": True,
    "Desktop": True,
}

class MigrationPreferencesPage(BasePage):
    """
    Page displayed after mode selection.
    Shows different options depending on the user's selected migration mode:
    - Guided: summary only
    - Balanced: folder category checkboxes + basic app confirmation
    - Expert: full control (will expand later)
    """

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.header["text"] ="Migration Preferences"

        self.mode = self.controller.state.get("mode")

        self.selected_folders: dict = controller.state.get("selected_folders", DEFAULT_FOLDERS.copy())
        self.selected_apps: dict = controller.state.get("selected_apps", {})

        self.file_types = controller.state.get("file_types", {})

        description = (
            "Customize your migration preferences below. "
            "Options available depend on the selected migration mode."
        )
        ttk.Label(self.body, text=description, wraplength=800, justify="left").pack(
            anchor="w", pady=(0, 10)
        )

        ttk.Label(
            self.body,
            text=(
                f"{str.capitalize(self.mode)} Mode selected.\n"
            ),
            justify="left",
            wraplength=600
        ).pack(anchor="w", pady=10)

        self.main_frame = ttk.Frame(self.body)
        self.main_frame.pack(fill="both", expand=True)

        self.access_status = tk.StringVar(value=tk.NORMAL)

        self.setup_mode_radios()
        # File types section
        self.setup_file_types()
        # Applications section
        self.setup_app_selection()

    def setup_mode_radios(self):
        self.folder_vars = {}

        ttk.Label(
            self.main_frame,
            text=(
                "Recommended folders and applications will be chosen automatically.\n"
                "No manual adjustments required."
            ),
            justify="left",
            wraplength=600
        ).pack(anchor="w", pady=10)

        for name, default in self.selected_folders.items():
            var = tk.BooleanVar(value=default)
            cb = ttk.Checkbutton(self.main_frame, text=name, variable=var, state=self.access_status)
            cb.pack(anchor="w")
            self.folder_vars[name] = var

    def setup_file_types(self):
        self.file_type_vars = {}

        ttk.Label(
            self.main_frame,
            text="Select file types to include:",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", pady=(20, 5))

        for ext, default in self.file_types.items():
            var = tk.BooleanVar(value=default)
            cb = ttk.Checkbutton(self.main_frame, text=ext, variable=var, state=self.access_status)
            cb.pack(anchor="w")
            self.file_type_vars[ext] = var 

    def setup_app_selection(self):
        ttk.Label(
            self.main_frame,
            text="Application Migration:",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", pady=(20, 5))

        ttk.Label(
            self.main_frame,
            text="Mapped Linux applications will be installed automatically.\n"
                 "Uncheck any category above to exclude associated app config if needed."
        ).pack(anchor="w")

        self.app_vars = {}
        
        for entry in self.controller.software_map:
            var = tk.BooleanVar(value=True)
            label = f"{entry['windows_name']} → {entry['linux_display_name']}"
            ttk.Checkbutton(self.main_frame, text=label, variable=var, state=self.access_status).pack(anchor="w")

            self.app_vars[entry["windows_name"]] = {
                "linux_package": entry["linux_package"],
                "migration_strategy": entry["migration_strategy"],
                "var": var,
            }

    
    # ---------------------------
    # GUIDED MODE
    # ---------------------------
    def _build_guided_view(self):
        # Disable all controls
        for child in self.main_frame.winfo_children():
            child['state'] = tk.DISABLED
        
        for var in self.folder_vars.values():
            var.set(True)
        for var in self.file_type_vars.values():
            var.set(True) 
        for var in self.app_vars.values():
            var['var'].set(True)

    # ---------------------------
    # BALANCED MODE
    # ---------------------------
    def _build_balanced_view(self):
        # Enable all controls
        for child in self.main_frame.winfo_children():
            child['state'] = tk.NORMAL

        for var in self.folder_vars.values():
            var.set(True)
        for var in self.file_type_vars.values():
            var.set(True) 
        for var in self.app_vars.values():
            var['var'].set(True)

    # ---------------------------
    # EXPERT MODE
    # ---------------------------
    def _build_expert_view(self):
        # Enable all controls
        for child in self.main_frame.winfo_children():
            child['state'] = tk.NORMAL

        for var in self.folder_vars.values():
            var.set(False)
        for var in self.file_type_vars.values():
            var.set(False) 
        for var in self.app_vars.values():
            var['var'].set(False)


    def on_show(self) -> None:
        self.mode = self.controller.state.get("mode")

        if self.mode == "guided":
            self._build_guided_view()
        elif self.mode == "balanced":
            self._build_balanced_view()
        else:
            self._build_expert_view()


    # ---------------------------
    # NAVIGATION HOOKS
    # ---------------------------
    def before_leave(self):
        """Store the user's folder/app choices before leaving the page."""
        self.selected_folders = {name:var.get() for name, var in self.folder_vars.items()}
        self.file_types = {ext:var.get() for ext, var in self.file_type_vars.items()}

        if hasattr(self, "app_vars"):
            self.selected_apps = [
                {
                    "windows_name": win,
                    "linux_package": data["linux_package"],
                    "migration_strategy": data["migration_strategy"],
                }
                for win, data in self.app_vars.items()
                if data["var"].get()
            ]

        for widget in self.body.winfo_children():
            widget.destroy()

        # Save into controller.state so backup + restore can use it
        self.controller.state["selected_folders"] = self.selected_folders
        self.controller.state["selected_apps"] = self.selected_apps
        self.controller.state["file_types"] = self.file_types

        return True
    
