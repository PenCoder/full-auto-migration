"""Welcome / landing page shown before the migration wizard begins."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
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
                    stop:0 #3F6FE0, stop:1 #7BA0F2);
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
            "padding: 5px 14px; font-size: 15px; font-weight: 700;"
        )
        arrow_lbl = QLabel("→")
        arrow_lbl.setStyleSheet(
            "color: rgba(255,255,255,0.7); font-size: 25px; font-weight: 300;"
            "background: transparent;"
        )
        mint_badge = QLabel("  Linux Mint  ")
        mint_badge.setStyleSheet(
            "background: #2E7D32; color: white;"
            "border: 1px solid rgba(255,255,255,0.35); border-radius: 20px;"
            "padding: 5px 14px; font-size: 15px; font-weight: 700;"
        )
        badge_row.addWidget(win_badge)
        badge_row.addWidget(arrow_lbl)
        badge_row.addWidget(mint_badge)
        hero_layout.addLayout(badge_row)

        hero_title = QLabel("Migration Platform")
        hero_title.setStyleSheet(
            "color: white; font-size: 39px; font-weight: 800;"
            "letter-spacing: -1px; background: transparent;"
        )
        hero_title.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(hero_title)

        hero_sub = QLabel(
            "Move your files, apps, and settings from Windows 11 to Linux Mint —"
            " step by step, all under your control."
        )
        hero_sub.setStyleSheet(
            "color: rgba(255,255,255,0.88); font-size: 16px; background: transparent;"
        )
        hero_sub.setAlignment(Qt.AlignCenter)
        hero_sub.setWordWrap(True)
        hero_layout.addWidget(hero_sub)

        outer.addWidget(hero)

        # ------------------------------------------------------------------ #
        # Body — feature cards + stats + CTA                                 #
        # ------------------------------------------------------------------ #
        body = QWidget()
        body.setObjectName("WelcomeBody")
        body.setStyleSheet("QWidget#WelcomeBody { background: #FFFFFF; }")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(36, 28, 36, 28)
        body_layout.setSpacing(22)

        # Feature cards — laid out in a grid so the column count can drop as
        # the window narrows, instead of clipping silently (horizontal
        # scrolling is disabled on the page's scroll area).
        self.features_grid = QGridLayout()
        self.features_grid.setSpacing(14)
        self._feature_columns = 0
        self._feature_cards: list[QFrame] = []

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
                "font-size: 30px; background: transparent; border: none;"
            )
            card_layout.addWidget(icon_lbl)

            t_lbl = QLabel(title_text)
            t_lbl.setStyleSheet(
                "font-size: 15px; font-weight: 700; color: #3F6FE0;"
                "background: transparent; border: none;"
            )
            card_layout.addWidget(t_lbl)

            d_lbl = QLabel(desc_text)
            d_lbl.setStyleSheet(
                "font-size: 14px; color: #546E7A; background: transparent; border: none;"
            )
            d_lbl.setWordWrap(True)
            card_layout.addWidget(d_lbl)
            card_layout.addStretch(1)

            self._feature_cards.append(card)

        body_layout.addLayout(self.features_grid)
        self._relayout_feature_cards(4)

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

        # Exposed so main_window can attach the shared Back/Next nav bar —
        # this page uses a custom hero layout instead of create_center_card_layout.
        self.card_widget = body
        self.card_layout = body_layout

        outer.addWidget(body, stretch=1)

    def _relayout_feature_cards(self, columns: int) -> None:
        if columns == self._feature_columns:
            return
        self._feature_columns = columns
        while self.features_grid.count():
            self.features_grid.takeAt(0)
        for idx, card in enumerate(self._feature_cards):
            row, col = divmod(idx, columns)
            self.features_grid.addWidget(card, row, col)

    def resizeEvent(self, event) -> None:
        # This page has its own full-width hero + body layout instead of the
        # shared centered StepCard, so skip BasePage's card-width clamping —
        # only the feature-card grid needs to reflow here.
        columns = 4 if self.width() >= 980 else (2 if self.width() >= 560 else 1)
        self._relayout_feature_cards(columns)
