"""Contextual help — shows what to do on the current wizard page.

Two ways to get help, matching what was asked for:
  - An in-app panel with a short, page-specific brief (HelpDialog).
  - A button inside it that opens the full user guide as a rendered
    HTML page in the system browser — no internet required, since the
    guide ships locally as Markdown and gets converted on the fly.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from src.constants import BASE_DIR
from src.qt_ui.widgets.simple_markdown import render_user_manual

USER_MANUAL_PATH = BASE_DIR / "docs" / "USER_MIGRATION_GUIDE.md"

# Keyed by page class name (not the class itself, to avoid import cycles
# between this widget module and every page module). Icons match the ones
# each page already shows in its own header, so Help feels like part of
# the same page rather than a bolted-on extra.
HELP_CONTENT: dict[str, dict[str, object]] = {
    "WelcomePage": {
        "icon": "👋",
        "title": "Welcome",
        "steps": [
            "This tool moves your files, apps, and desktop settings from Windows 11 to Linux Mint in a few guided steps.",
        ],
        "note": "Nothing happens yet — click 'Start' when you're ready to begin.",
    },
    "ModePage": {
        "icon": "🧭",
        "title": "Get Started — Choose your migration mode",
        "steps": [
            "Guided — everything handled for you, no decisions needed.",
            "Balanced — you choose files/apps, defaults handle the rest.",
            "Expert — full manual control, including live online package verification and custom override rules.",
        ],
        "note": "You can switch modes later without losing progress.",
    },
    "ScanPage": {
        "icon": "🔍",
        "title": "System Scan",
        "steps": [
            "The scan starts automatically — apps, hardware, and desktop settings are inventoried.",
            "Choose how Windows apps should be matched to Linux alternatives.",
            "Decide whether to carry your desktop look (wallpaper/theme) across.",
        ],
        "note": "Nothing is read or sent anywhere except app names and hardware details.",
    },
    "DataSelectionPage": {
        "icon": "📁",
        "title": "Which files should come with you?",
        "steps": [
            "Choose how your personal files (documents, photos, music, etc.) should be handled.",
            "In Balanced/Expert mode you can narrow this to specific file types, or use a usage-based recommendation.",
        ],
        "note": "Nothing is moved yet — this only sets the plan for backup.",
    },
    "ReviewRecommendationsPage": {
        "icon": "🔍",
        "title": "Review & Confirm Your Migration Plan",
        "steps": [
            "A full summary of every choice made so far: mode, files, apps, and settings.",
            "Check the app and file recommendations — in 'choose from recommendations' mode you can tick/untick individual items.",
        ],
        "note": "Nothing is moved yet. Click Continue when the plan looks right.",
    },
    "BackupBundlePage": {
        "icon": "📦",
        "title": "Pack and export your migration data",
        "steps": [
            "Click 'Create My Migration Bundle' to pack everything into one self-contained archive (migration_bundle.zip).",
            "Optionally select a USB drive first — the bundle is copied there automatically once it's built.",
        ],
        "note": "Your original files are never modified — the bundle is a copy.",
    },
    "BundleReportPage": {
        "icon": "📋",
        "title": "Backup Bundle Report",
        "steps": [
            "A summary of everything that was just packed: files, apps, and settings included in the bundle.",
            "Carry the bundle archive to your Linux machine (USB, network share, or cloud storage), then continue there.",
        ],
    },
    "RestorePage": {
        "icon": "🚀",
        "title": "Restore your data (Linux side)",
        "steps": [
            "Click 'Browse' and select the migration_bundle.zip you carried over from Windows (or an already-unzipped bundle folder).",
            "Click 'Restore My Files to This Computer' — this automatically restores your files, verifies them, and generates your final report, one after another.",
            "Once it finishes, your Migration Score and report links appear right here — open the report or click 'Finish' when you're done.",
        ],
        "note": "If a step fails partway, you'll be offered 'Restart' (reset and try again) or 'Review & Complete Anyway' (continue with whatever already succeeded) — nothing fails silently.",
    },
}

DEFAULT_HELP = {
    "icon": "❓",
    "title": "Help",
    "steps": ["No specific guidance for this page yet — see the full user guide below."],
}


def _render_manual_to_html() -> Path | None:
    """Render the bundled Markdown user manual to a branded standalone HTML file.

    Returns the path to a temp .html file, or None if the manual is missing.
    """
    if not USER_MANUAL_PATH.exists():
        return None

    html = render_user_manual(USER_MANUAL_PATH.read_text(encoding="utf-8"), base_dir=USER_MANUAL_PATH.parent)

    out_path = Path(tempfile.gettempdir()) / "migration_tool_user_manual.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


def open_full_user_guide() -> None:
    """Open the full user guide as a rendered HTML page in the system browser."""
    html_path = _render_manual_to_html()
    if html_path is not None:
        QDesktopServices.openUrl(html_path.as_uri())
    elif USER_MANUAL_PATH.exists():
        QDesktopServices.openUrl(USER_MANUAL_PATH.as_uri())


class HelpDialog(QDialog):
    """Structured dialog showing what to do on the current page."""

    def __init__(self, page_class_name: str, parent=None) -> None:
        super().__init__(parent)
        info = HELP_CONTENT.get(page_class_name, DEFAULT_HELP)

        self.setWindowTitle(f"Help — {info['title']}")
        self.setMinimumWidth(480)
        self.setStyleSheet("QDialog { background: #FFFFFF; }")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(28, 24, 28, 22)
        outer.setSpacing(16)

        # ── Header: icon + title, matching each page's own header style ──────
        icon_lbl = QLabel(str(info["icon"]))
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet("font-size: 40px; background: transparent;")
        outer.addWidget(icon_lbl)

        title_lbl = QLabel(str(info["title"]))
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setWordWrap(True)
        title_lbl.setStyleSheet(
            "font-size: 19px; font-weight: 800; color: #1B1E28; letter-spacing: -0.2px;"
        )
        outer.addWidget(title_lbl)

        # ── What to do here — tinted card with one checkmark row per step ────
        steps_card = QFrame()
        steps_card.setProperty("card", "section")
        steps_layout = QVBoxLayout(steps_card)
        steps_layout.setContentsMargins(16, 14, 16, 14)
        steps_layout.setSpacing(10)

        steps_title = QLabel("WHAT TO DO HERE")
        steps_title.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #3F6FE0; letter-spacing: 0.5px;"
        )
        steps_layout.addWidget(steps_title)

        for step in info.get("steps", []):
            row = QHBoxLayout()
            row.setSpacing(10)

            bullet = QLabel("✓")
            bullet.setStyleSheet(
                "color: #FFFFFF; background: #3F6FE0; border-radius: 9px;"
                "font-size: 11px; font-weight: 700; min-width: 18px; max-width: 18px;"
                "min-height: 18px; max-height: 18px;"
            )
            bullet.setAlignment(Qt.AlignCenter)
            row.addWidget(bullet, alignment=Qt.AlignTop)

            text = QLabel(str(step))
            text.setWordWrap(True)
            text.setStyleSheet("font-size: 14px; color: #1B1E28; line-height: 1.4;")
            row.addWidget(text, stretch=1)

            steps_layout.addLayout(row)

        outer.addWidget(steps_card)

        # ── Optional aside — trust-banner style note ──────────────────────────
        note = info.get("note")
        if note:
            note_frame = QFrame()
            note_frame.setStyleSheet(
                "QFrame { background: #E8F0FE; border-radius: 10px; }"
            )
            note_layout = QHBoxLayout(note_frame)
            note_layout.setContentsMargins(12, 10, 12, 10)
            note_layout.setSpacing(8)

            info_icon = QLabel("ℹ")
            info_icon.setStyleSheet("font-size: 14px; color: #3F6FE0; background: transparent;")
            note_layout.addWidget(info_icon, alignment=Qt.AlignTop)

            note_lbl = QLabel(str(note))
            note_lbl.setWordWrap(True)
            note_lbl.setStyleSheet("font-size: 13px; color: #374151; background: transparent;")
            note_layout.addWidget(note_lbl, stretch=1)

            outer.addWidget(note_frame)

        # ── Footer actions ─────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        guide_btn = QPushButton("📖  Open Full User Guide")
        guide_btn.setProperty("role", "badge")
        guide_btn.clicked.connect(open_full_user_guide)
        btn_row.addWidget(guide_btn)

        btn_row.addStretch(1)

        close_btn = QPushButton("Got it")
        close_btn.setProperty("role", "cta")
        close_btn.setMinimumWidth(110)
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        outer.addLayout(btn_row)
