"""Welcome / landing page shown before the migration wizard begins."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.qt_ui.pages.base_page import BasePage


class WelcomePage(BasePage):
    """Introduce the platform and invite the user to begin their migration journey."""

    def __init__(self, ui_state) -> None:
        super().__init__(ui_state)
        self.setObjectName("WelcomePage")
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ------------------------------------------------------------------ #
        # Hero banner — bold blue gradient                                    #
        # ------------------------------------------------------------------ #
        hero = QWidget()
        hero.setObjectName("WelcomeHero")
        hero.setMinimumHeight(230)
        hero.setStyleSheet("""
            QWidget#WelcomeHero {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1565C0, stop:1 #1E88E5);
            }
        """)
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(48, 36, 48, 36)
        hero_layout.setSpacing(14)

        # OS migration label row
        badge_row = QHBoxLayout()
        badge_row.setSpacing(10)
        badge_row.setAlignment(Qt.AlignCenter)

        win_badge = QLabel("  Windows 11  ")
        win_badge.setStyleSheet(
            "background: rgba(255,255,255,0.18); color: white;"
            "border: 1px solid rgba(255,255,255,0.45); border-radius: 20px;"
            "padding: 5px 14px; font-size: 13px; font-weight: 700;"
        )
        arrow_lbl = QLabel("→")
        arrow_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.7); font-size: 22px; font-weight: 300;"
            "background: transparent;"
        )
        mint_badge = QLabel("  Linux Mint  ")
        mint_badge.setStyleSheet(
            "background: #2E7D32; color: white;"
            "border: 1px solid rgba(255,255,255,0.35); border-radius: 20px;"
            "padding: 5px 14px; font-size: 13px; font-weight: 700;"
        )
        badge_row.addWidget(win_badge)
        badge_row.addWidget(arrow_lbl)
        badge_row.addWidget(mint_badge)
        hero_layout.addLayout(badge_row)

        hero_title = QLabel("Migration Platform")
        hero_title.setStyleSheet(
            "color: white; font-size: 34px; font-weight: 800;"
            "letter-spacing: -1px; background: transparent;"
        )
        hero_title.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(hero_title)

        hero_sub = QLabel(
            "Move your files, apps, and settings from Windows 11 to Linux Mint —"
            " step by step, all under your control."
        )
        hero_sub.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 14px; background: transparent;"
        )
        hero_sub.setAlignment(Qt.AlignCenter)
        hero_sub.setWordWrap(True)
        hero_layout.addWidget(hero_sub)

        outer.addWidget(hero)

        # ------------------------------------------------------------------ #
        # Body — feature cards + stats + CTA                                 #
        # ------------------------------------------------------------------ #
        body = QWidget()
        body.setStyleSheet("QWidget { background: #FFFFFF; }")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(36, 28, 36, 28)
        body_layout.setSpacing(22)

        # Feature cards
        features_row = QHBoxLayout()
        features_row.setSpacing(14)

        feature_data = [
            (
                "🔍",
                "Automated Discovery",
                "Scans your installed apps, desktop settings, and hardware to build"
                " a complete migration plan — and flags any drivers you will need on Linux Mint.",
            ),
            (
                "📦",
                "Secure Backup Bundle",
                "Packages your selected files, settings, and app list into a"
                " self-contained archive — ready to carry across platforms.",
            ),
            (
                "✅",
                "Verified Restoration",
                "Restores your data on Linux Mint with hash verification, missing-file"
                " detection, and a full evidence report you can submit.",
            ),
            (
                "🚀",
                "Three Migration Modes",
                "Guided keeps it simple for newcomers. Balanced gives intermediate"
                " control. Expert unlocks online package verification and full manual overrides.",
            ),
        ]

        for icon, title_text, desc_text in feature_data:
            card = QFrame()
            card.setProperty("card", "true")
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(16, 16, 16, 16)
            card_layout.setSpacing(8)

            icon_lbl = QLabel(icon)
            icon_lbl.setStyleSheet(
                "font-size: 26px; background: transparent; border: none;"
            )
            card_layout.addWidget(icon_lbl)

            t_lbl = QLabel(title_text)
            t_lbl.setStyleSheet(
                "font-size: 13px; font-weight: 700; color: #1565C0;"
                "background: transparent; border: none;"
            )
            card_layout.addWidget(t_lbl)

            d_lbl = QLabel(desc_text)
            d_lbl.setStyleSheet(
                "font-size: 12px; color: #546E7A; background: transparent; border: none;"
            )
            d_lbl.setWordWrap(True)
            card_layout.addWidget(d_lbl)
            card_layout.addStretch(1)

            features_row.addWidget(card)

        body_layout.addLayout(features_row)

        # Stats row
        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        stats_row.addStretch(1)
        for label in [
            "150+ App Mappings",
            "3 Migration Modes",
            "Zero External Data Transfer",
            "Open Source",
        ]:
            chip = QLabel(f"  {label}  ")
            chip.setObjectName("StatChip")
            stats_row.addWidget(chip)
        stats_row.addStretch(1)
        body_layout.addLayout(stats_row)

        body_layout.addWidget(self.create_trust_banner(
            "Privacy-first: your personal files and application data never leave"
            " your machine during scanning, backup, or any other step of this tool."
        ))

        # CTA button
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        self.start_btn = QPushButton("Start")
        self.start_btn.setProperty("role", "cta")
        self.start_btn.setMinimumHeight(46)
        self.start_btn.setMinimumWidth(200)
        self.start_btn.clicked.connect(self.request_next)
        btn_row.addWidget(self.start_btn)
        btn_row.addStretch(1)
        body_layout.addLayout(btn_row)

        outer.addWidget(body, stretch=1)
