"""Post-backup bundle report page — summarises everything packed for Linux."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QTextEdit

from src.qt_ui.pages.base_page import BasePage


class BundleReportPage(BasePage):
    """Display a comprehensive summary of the migration bundle after backup."""

    def __init__(self, ui_state, get_bundle_data_cb: Callable[[], dict]) -> None:
        super().__init__(ui_state)
        self.get_bundle_data_cb = get_bundle_data_cb
        self._build_ui()
        self.refresh()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = self.create_center_card_layout(max_width=980)

        root.addWidget(self.create_page_header(
            "📋",
            "Backup Bundle Report",
            "Everything packed for Linux is summarised below. "
            "Review the details, then carry the bundle to your Linux machine.",
        ))

        root.addWidget(self.create_trust_banner(
            "This report reflects the bundle that was just created on this machine. "
            "Your original files are untouched."
        ))

        self.report_view = QTextEdit()
        self.report_view.setObjectName("ReportView")
        self.report_view.setReadOnly(True)
        self.report_view.setMinimumHeight(380)
        root.addWidget(self.report_view)

        self.next_btn = QPushButton("Backup complete — move to Linux")
        self.next_btn.setProperty("role", "cta")
        self.next_btn.setFixedWidth(290)
        self.next_btn.clicked.connect(self.request_next.emit)
        root.addWidget(self.next_btn, alignment=Qt.AlignHCenter)

    # ── Rendering ────────────────────────────────────────────────────────────

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._render()

    def _render(self) -> None:
        try:
            data = self.get_bundle_data_cb()
        except Exception:
            self.report_view.setHtml(self.html_wrap(
                self.html_empty("Report data not available — complete the backup step first.")
            ))
            return

        manifest = data.get("manifest") or {}
        app_recs = data.get("app_recs") or {}
        local_path = str(data.get("local_bundle_path", ""))
        usb_path = str(data.get("usb_path", ""))
        sections = []

        # ── 1. Bundle location ───────────────────────────────────────────────
        loc_rows = self.html_row("Saved on this computer", local_path or "—")
        if usb_path:
            loc_rows += self.html_row(
                "USB copy", str(Path(usb_path) / "migration_bundle")
            )
        sections.append(self.html_section(
            "📁", "Bundle Location",
            f'<table style="width:100%;">{loc_rows}</table>',
        ))

        # ── 2. Files packed ──────────────────────────────────────────────────
        entries = manifest.get("entries", [])
        total_files = int(manifest.get("total_files", len(entries)))
        total_bytes = sum(int(e.get("size_bytes", 0)) for e in entries)

        folder_counts: dict[str, int] = defaultdict(int)
        folder_bytes: dict[str, int] = defaultdict(int)
        for e in entries:
            parts = Path(e.get("relative_path", "")).parts
            top = parts[0] if parts else "Other"
            folder_counts[top] += 1
            folder_bytes[top] += int(e.get("size_bytes", 0))

        file_rows = (
            self.html_row("Total files", f"{total_files:,}")
            + self.html_row("Total size", _fmt_size(total_bytes))
        )
        if folder_counts:
            breakdown_rows = "".join(
                self.html_row(
                    f"&nbsp;&nbsp;&nbsp;{folder}",
                    f"{count:,} files &nbsp;·&nbsp; {_fmt_size(folder_bytes[folder])}",
                )
                for folder, count in sorted(folder_counts.items(), key=lambda x: -x[1])
            )
            file_rows += self.html_row("By folder", "") + breakdown_rows

        sections.append(self.html_section(
            "📄", "Files Packed",
            f'<table style="width:100%;">{file_rows}</table>',
        ))

        # ── 3. App transition plan ───────────────────────────────────────────
        app_total = int(app_recs.get("input_count", 0))
        app_count = int(app_recs.get("recommended_count", 0))

        if app_total:
            stat_rows = (
                self.html_row("Windows apps detected", str(app_total))
                + self.html_row("Linux alternatives matched", str(app_count))
            )
            app_body = f'<table style="width:100%;">{stat_rows}</table>'

            recs = (app_recs.get("recommendations") or [])[:8]
            if recs:
                conf_color = {"high": "#1B5E20", "medium": "#E65100", "low": "#546E7A"}
                conf_bg = {"high": "#E8F5E9", "medium": "#FFF3E0", "low": "#ECEFF1"}
                rows = "".join(
                    f'<tr>'
                    f'<td style="padding:3px 10px 3px 0;font-size:12px;color:#0D1929;">{rec.get("windows_app","")}</td>'
                    f'<td style="padding:3px 10px 3px 0;font-size:12px;color:#1565C0;">{rec.get("linux_package","")}</td>'
                    f'<td style="padding:3px 0;">'
                    f'{self.html_pill(str(rec.get("mapping_confidence","")), conf_color.get(str(rec.get("mapping_confidence","")), "#546E7A"), conf_bg.get(str(rec.get("mapping_confidence","")), "#ECEFF1"))}'
                    f'</td></tr>'
                    for rec in recs
                )
                extra = len(app_recs.get("recommendations", [])) - 8
                if extra > 0:
                    rows += (
                        f'<tr><td colspan="3" style="color:#90A4AE;font-size:11px;'
                        f'padding-top:4px;">+ {extra} more matched</td></tr>'
                    )
                header = (
                    '<tr>'
                    '<th style="text-align:left;color:#90A4AE;font-size:11px;font-weight:600;padding-bottom:4px;">Windows App</th>'
                    '<th style="text-align:left;color:#90A4AE;font-size:11px;font-weight:600;padding-bottom:4px;">Linux Package</th>'
                    '<th style="text-align:left;color:#90A4AE;font-size:11px;font-weight:600;padding-bottom:4px;">Match</th>'
                    '</tr>'
                )
                app_body += (
                    f'<br><table style="width:100%;">{header}{rows}</table>'
                )
        else:
            app_body = self.html_empty(
                "No app recommendations available — run the Review step to generate them."
            )
        sections.append(self.html_section("🗂️", "App Transition Plan", app_body))

        # ── 4. Settings included ─────────────────────────────────────────────
        label_map = {
            "wallpaper": "Wallpaper",
            "theme": "Theme",
            "light_dark": "Light/Dark mode",
            "accent_color": "Accent colour",
            "taskbar_layout": "Taskbar layout",
            "keyboard_shortcuts": "Keyboard shortcuts",
            "file_associations": "File associations",
        }
        if self.ui_state.settings_migration_enabled:
            selected = [
                label_map[k]
                for k, v in self.ui_state.settings_selected_items.items()
                if v and k in label_map
            ]
            appearance_val = ", ".join(selected) if selected else "None selected"
        else:
            appearance_val = "Disabled"

        mode_labels = {
            "guided": "Guided",
            "balanced": "Balanced",
            "expert": "Expert",
        }
        settings_rows = (
            self.html_row("Migration mode", mode_labels.get(self.ui_state.mode, self.ui_state.mode.capitalize()))
            + self.html_row("Appearance items", appearance_val)
            + self.html_row("File strategy", _choice_label(self.ui_state.data_choice_mode))
            + self.html_row("Target distro", self.ui_state.target_distro)
        )
        sections.append(self.html_section(
            "🎨", "Configuration Summary",
            f'<table style="width:100%;">{settings_rows}</table>',
        ))

        # ── 5. What to do next ───────────────────────────────────────────────
        if usb_path:
            next_text = (
                "Eject the USB drive and insert it into your Linux machine. "
                "Open this tool in <b>Linux mode</b> and proceed to the Restore step."
            )
        else:
            next_text = (
                f'Copy the bundle folder from <span style="font-family:monospace;font-size:12px;">'
                f'{local_path}</span> to your Linux machine using a USB drive, '
                f'network share, or cloud storage. '
                f'Then open this tool in <b>Linux mode</b> and proceed to the Restore step.'
            )
        sections.append(self.html_section(
            "🚀", "What to do next",
            f'<p style="font-size:13px;color:#374151;line-height:1.7;margin:0;">{next_text}</p>',
        ))

        self.report_view.setHtml(self.html_wrap("".join(sections)))

    # ── Refresh ──────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        self.next_btn.setEnabled(self.ui_state.backup_completed)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fmt_size(b: int) -> str:
    if b >= 1024 ** 3:
        return f"{b / 1024**3:.1f} GB"
    if b >= 1024 ** 2:
        return f"{b / 1024**2:.1f} MB"
    if b >= 1024:
        return f"{b / 1024:.0f} KB"
    return f"{b} B"


def _choice_label(mode: str) -> str:
    return {
        "all_files": "All files",
        "selected_types": "Selected file types",
        "ai_recommended": "Usage-based recommendation",
        "manual": "Manual (no files)",
    }.get(mode, mode.replace("_", " ").capitalize())
