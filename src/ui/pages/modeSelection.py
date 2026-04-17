import tkinter as tk
import ttkbootstrap as ttk

from src.ui.core import BasePage


class ModeSelectionPage(BasePage):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, controller)
        self.mode_var = tk.StringVar(value=self.controller.state.get("mode", "guided"))
        self.card_frames: dict[str, ttk.Labelframe] = {}
        self.card_badges: dict[str, ttk.Label] = {}
        self.card_buttons: dict[str, ttk.Button] = {}
        self.readiness_value = tk.StringVar(value="88%")
        self.readiness_note = tk.StringVar(value="High compatibility and auto-safe defaults")
        self.sovereignty_value = tk.StringVar(value="92%")
        self.sovereignty_note = tk.StringVar(value="Open-source alternatives available for most apps")

        self.header["text"] = "Pre-Migration Phase: Prepare"

        self.mode_profiles = {
            "guided": {
                "title": "Recommended Migration",
                "subtitle": "Max sovereignty",
                "summary": "Auto-detects and migrates files, settings, and open-source alternatives.",
                "eta": "Estimated time: 45 min",
                "readiness": "88%",
                "readiness_note": "High compatibility and auto-safe defaults",
                "sovereignty": "92%",
                "sovereignty_note": "Open-source alternatives available for most apps",
            },
            "balanced": {
                "title": "Custom Migration",
                "subtitle": "User agency",
                "summary": "Choose folders, specific applications, and software mappings.",
                "eta": "Estimated time: Variable",
                "readiness": "81%",
                "readiness_note": "Strong compatibility with moderate user decisions",
                "sovereignty": "89%",
                "sovereignty_note": "Great balance of automation and manual control",
            },
            "expert": {
                "title": "System Assessment Only",
                "subtitle": "Insight",
                "summary": "Generate a detailed compatibility and sovereignty report only.",
                "eta": "Estimated time: 15 min",
                "readiness": "74%",
                "readiness_note": "Best for planning and fine-grained tuning",
                "sovereignty": "95%",
                "sovereignty_note": "Maximum visibility for a fully customized migration",
            },
        }

        self._build_dashboard()

    def _build_dashboard(self) -> None:
        root = ttk.Frame(self.body)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=3)
        root.columnconfigure(1, weight=2)

        self._build_main_panel(root)
        self._build_side_panel(root)

    def _build_main_panel(self, parent: ttk.Frame) -> None:
        left = ttk.Frame(parent)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        step_row = ttk.Frame(left)
        step_row.pack(fill="x", pady=(0, 10))
        ttk.Label(step_row, text="Step 2 of 6", bootstyle="secondary").pack(side="left")
        ttk.Label(step_row, text="Novice Mode", bootstyle="info").pack(side="right")

        gauges = ttk.Frame(left)
        gauges.pack(fill="x", pady=(0, 12))
        gauges.columnconfigure(0, weight=2)
        gauges.columnconfigure(1, weight=1)

        canvas_bg = self.winfo_toplevel().cget("bg")
        self.primary_gauge = tk.Canvas(gauges, width=360, height=180, bg=canvas_bg, highlightthickness=0)
        self.primary_gauge.grid(row=0, column=0, sticky="w")

        right_gauge = ttk.Frame(gauges)
        right_gauge.grid(row=0, column=1, sticky="e")
        self.secondary_gauge = tk.Canvas(right_gauge, width=180, height=120, bg=canvas_bg, highlightthickness=0)
        self.secondary_gauge.pack(anchor="e")

        headline = ttk.Label(
            left,
            text="Ready to start your migration?",
            font=("Segoe UI", 20, "bold"),
        )
        headline.pack(anchor="w", pady=(8, 2))

        subtitle = ttk.Label(
            left,
            text="You can customize your choices below or proceed with recommendations.",
            font=("Segoe UI", 12),
            bootstyle="secondary",
        )
        subtitle.pack(anchor="w", pady=(0, 14))

        cards = ttk.Frame(left)
        cards.pack(fill="x", pady=(0, 14))
        cards.columnconfigure(0, weight=1)
        cards.columnconfigure(1, weight=1)
        cards.columnconfigure(2, weight=1)

        self._build_mode_card(cards, 0, "guided")
        self._build_mode_card(cards, 1, "balanced")
        self._build_mode_card(cards, 2, "expert")

        self.primary_cta = ttk.Button(
            left,
            text="Proceed With Recommended Migration",
            bootstyle="success",
            command=self._proceed_with_current_mode,
        )
        self.primary_cta.pack(fill="x", pady=(4, 0), ipady=8)

    def _build_mode_card(self, parent: ttk.Frame, col: int, mode_key: str) -> None:
        profile = self.mode_profiles[mode_key]
        card = ttk.Labelframe(parent, text=profile["title"], padding=12)
        card.grid(row=0, column=col, sticky="nsew", padx=6)

        badge = ttk.Label(card, text=profile["subtitle"].upper(), bootstyle="secondary")
        badge.pack(anchor="w", pady=(0, 8))

        summary = ttk.Label(card, text=profile["summary"], anchor="w", justify="left", wraplength=260)
        summary.pack(fill="x", pady=(0, 8))

        eta = ttk.Label(card, text=profile["eta"], bootstyle="secondary")
        eta.pack(anchor="w", pady=(0, 10))

        select_btn = ttk.Button(
            card,
            text="Select",
            bootstyle="secondary-outline",
            command=lambda m=mode_key: self._select_mode(m),
        )
        select_btn.pack(fill="x")

        # Make whole card clickable for faster UX.
        card.bind("<Button-1>", lambda _e, m=mode_key: self._select_mode(m))
        for widget in (badge, summary, eta):
            widget.bind("<Button-1>", lambda _e, m=mode_key: self._select_mode(m))

        self.card_frames[mode_key] = card
        self.card_badges[mode_key] = badge
        self.card_buttons[mode_key] = select_btn

    def _build_side_panel(self, parent: ttk.Frame) -> None:
        side = ttk.Labelframe(parent, text="Expert Customization")
        side.grid(row=0, column=1, sticky="nsew")

        ttk.Label(side, text="Hardware Advisories", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(10, 6))

        hw_items = [
            ("NVIDIA GPU", "88%", True),
            ("Intel Wi-Fi 6", "92%", False),
            ("Intel iGPU", "95%", False),
            ("Realtek NIC", "87%", False),
        ]
        self.hw_toggle_vars: dict[str, tk.BooleanVar] = {}
        for label, confidence, enabled in hw_items:
            row = ttk.Frame(side)
            row.pack(fill="x", padx=12, pady=3)
            ttk.Label(row, text=label).pack(side="left")
            ttk.Label(row, text=confidence, bootstyle="success").pack(side="left", padx=(8, 0))
            var = tk.BooleanVar(value=enabled)
            self.hw_toggle_vars[label] = var
            toggle = ttk.Checkbutton(row, variable=var)
            toggle.pack(side="right")

        ttk.Separator(side).pack(fill="x", padx=12, pady=10)

        ttk.Label(side, text="Target Distro Selection", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(2, 6))
        self.target_distro = ttk.Combobox(side, values=["Linux Mint", "Ubuntu", "Fedora", "Debian"], state="readonly")
        self.target_distro.set("Linux Mint")
        self.target_distro.pack(fill="x", padx=12)

        ttk.Label(side, text="Advanced Operations", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        self.incremental_var = tk.BooleanVar(value=True)
        self.hashing_var = tk.BooleanVar(value=True)
        self.rollback_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(side, text="Incremental backup", variable=self.incremental_var).pack(anchor="w", padx=12)
        ttk.Checkbutton(side, text="Parallel hashing", variable=self.hashing_var).pack(anchor="w", padx=12)
        ttk.Checkbutton(side, text="Create rollback point", variable=self.rollback_var).pack(anchor="w", padx=12, pady=(0, 10))

    def _draw_gauges(self) -> None:
        self.primary_gauge.delete("all")
        self.secondary_gauge.delete("all")

        readiness_pct = int(self.readiness_value.get().replace("%", ""))
        sovereignty_pct = int(self.sovereignty_value.get().replace("%", ""))

        # Primary readiness ring
        self.primary_gauge.create_arc(28, 20, 186, 178, start=130, extent=280, style="arc", width=14, outline="#cfd8df")
        self.primary_gauge.create_arc(
            28,
            20,
            186,
            178,
            start=130,
            extent=int(280 * readiness_pct / 100),
            style="arc",
            width=14,
            outline="#3dbb72",
        )
        self.primary_gauge.create_text(108, 78, text="Migration\nReadiness", font=("Segoe UI", 14, "bold"), fill="#17222e")
        self.primary_gauge.create_text(108, 118, text=self.readiness_value.get(), font=("Segoe UI", 30, "bold"), fill="#2d9f55")
        self.primary_gauge.create_text(224, 50, text="Confidence Score", font=("Segoe UI", 11, "bold"), fill="#213548", anchor="w")
        self.primary_gauge.create_text(224, 74, text=self.readiness_note.get(), font=("Segoe UI", 10), fill="#4f5f70", anchor="w", width=130)

        # Secondary sovereignty ring
        self.secondary_gauge.create_arc(18, 16, 122, 120, start=130, extent=280, style="arc", width=10, outline="#cfd8df")
        self.secondary_gauge.create_arc(
            18,
            16,
            122,
            120,
            start=130,
            extent=int(280 * sovereignty_pct / 100),
            style="arc",
            width=10,
            outline="#2ea7c7",
        )
        self.secondary_gauge.create_text(70, 70, text=self.sovereignty_value.get(), font=("Segoe UI", 24, "bold"), fill="#278faa")
        self.secondary_gauge.create_text(128, 35, text="Sovereignty", anchor="w", font=("Segoe UI", 11, "bold"), fill="#213548")
        self.secondary_gauge.create_text(
            128,
            63,
            text=self.sovereignty_note.get(),
            anchor="w",
            font=("Segoe UI", 9),
            fill="#4f5f70",
            width=120,
        )

    def _select_mode(self, mode_key: str) -> None:
        self.mode_var.set(mode_key)
        profile = self.mode_profiles[mode_key]
        self.readiness_value.set(profile["readiness"])
        self.readiness_note.set(profile["readiness_note"])
        self.sovereignty_value.set(profile["sovereignty"])
        self.sovereignty_note.set(profile["sovereignty_note"])

        for key in self.card_frames.keys():
            if key == mode_key:
                self.card_badges[key].configure(text=f"{self.mode_profiles[key]['subtitle'].upper()} · SELECTED", bootstyle="success")
                self.card_buttons[key].configure(text="Selected", bootstyle="success")
            else:
                self.card_badges[key].configure(text=self.mode_profiles[key]["subtitle"].upper(), bootstyle="secondary")
                self.card_buttons[key].configure(text="Select", bootstyle="secondary-outline")

        if mode_key == "guided":
            self.primary_cta.configure(text="Proceed With Recommended Migration", bootstyle="success")
        elif mode_key == "balanced":
            self.primary_cta.configure(text="Proceed With Custom Migration", bootstyle="info")
        else:
            self.primary_cta.configure(text="Proceed With System Assessment", bootstyle="secondary")

        self._draw_gauges()

    def _proceed_with_current_mode(self) -> None:
        self.controller.state["mode"] = self.mode_var.get()
        self.controller.state["target_distro"] = self.target_distro.get()
        self.controller.state["advanced_operations"] = {
            "incremental_backup": self.incremental_var.get(),
            "parallel_hashing": self.hashing_var.get(),
            "create_rollback_point": self.rollback_var.get(),
        }
        self.controller.go_next()

    def on_show(self) -> None:
        # Ensure the UI reflects any state loaded before
        selected = self.controller.state.get("mode", "guided")
        saved_distro = self.controller.state.get("target_distro")
        if saved_distro and saved_distro in self.target_distro.cget("values"):
            self.target_distro.set(saved_distro)

        ops = self.controller.state.get("advanced_operations", {})
        if ops:
            self.incremental_var.set(ops.get("incremental_backup", self.incremental_var.get()))
            self.hashing_var.set(ops.get("parallel_hashing", self.hashing_var.get()))
            self.rollback_var.set(ops.get("create_rollback_point", self.rollback_var.get()))

        self._select_mode(selected)

    def before_leave(self) -> bool:
        # Save selection into shared state
        self.controller.state["mode"] = self.mode_var.get()
        self.controller.state["target_distro"] = self.target_distro.get()
        self.controller.state["advanced_operations"] = {
            "incremental_backup": self.incremental_var.get(),
            "parallel_hashing": self.hashing_var.get(),
            "create_rollback_point": self.rollback_var.get(),
        }
        return True

