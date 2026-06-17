"""Shared base helpers for Qt wizard pages."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QRadioButton, QSizePolicy, QVBoxLayout, QWidget

from src.qt_ui.state import QtUiState


class BasePage(QWidget):
    """Common scaffolding for the migration wizard pages."""

    request_next = Signal()
    request_back = Signal()
    loading_progress = Signal(int)
    mode_changed = Signal(str)
    processing_changed = Signal(bool)

    def __init__(self, ui_state: QtUiState) -> None:
        """Store the shared UI state for a page."""
        super().__init__()
        self.ui_state = ui_state
        self.is_processing: bool = False

    def create_center_card_layout(self, max_width: int = 920) -> QVBoxLayout:
        """Create a centered card layout used by the wizard pages."""
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("StepCard")
        card.setMaximumWidth(max_width)
        card.setMinimumWidth(560)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(14)

        page_layout.addWidget(card)
        page_layout.addStretch(1)
        return card_layout

    def set_scanning(self, busy: bool, message: str = "") -> None:
        """Update the processing state and notify the main window to show the global scan bar."""
        self.is_processing = busy
        self.processing_changed.emit(busy)

    def can_proceed(self) -> bool:
        """Return True if the user is allowed to navigate forward from this page."""
        return True

    def blocked_reason(self) -> str:
        """Message shown when the user tries to continue but can_proceed() is False."""
        return "Please complete this step before continuing."

    def _make_info_panel(self, text: str) -> tuple[QFrame, QLabel]:
        """Light blue information panel with an ℹ icon. Returns (panel, inner_label)."""
        panel = QFrame()
        panel.setStyleSheet(
            "QFrame#InfoPanel { background-color: #E3F2FD; border: 1px solid #90CAF9; border-radius: 5px; }"
            " QLabel { background: transparent; border: none; }"
        )
        panel.setObjectName("InfoPanel")
        row = QHBoxLayout(panel)
        row.setContentsMargins(12, 7, 12, 7)
        row.setSpacing(10)

        icon = QLabel("ℹ")
        icon.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        icon.setFixedWidth(16)
        icon.setStyleSheet("color: #1565C0; font-size: 14px; font-weight: bold;")
        row.addWidget(icon)

        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #1565C0; font-size: 12px;")
        row.addWidget(lbl, stretch=1)

        return panel, lbl

    def create_trust_banner(self, text: str) -> QFrame:
        """Create an informational light-blue panel with an info icon."""
        panel, _ = self._make_info_panel(text)
        return panel

    def create_success_banner(self, text: str) -> tuple[QFrame, QLabel]:
        """Create a green success panel with a rounded checkmark icon.

        Returns (panel, label) so the caller can update the message later.
        """
        panel = QFrame()
        panel.setObjectName("SuccessPanel")
        panel.setStyleSheet(
            "QFrame#SuccessPanel { background-color: #E8F5E9; border: 1px solid #A5D6A7; border-radius: 5px; }"
            " QLabel { background: transparent; border: none; }"
        )
        row = QHBoxLayout(panel)
        row.setContentsMargins(12, 7, 12, 7)
        row.setSpacing(10)

        icon = QLabel("✓")
        icon.setFixedSize(20, 20)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(
            "background-color: #2E7D32; color: white; font-size: 12px; font-weight: bold;"
            " border-radius: 10px;"
        )
        row.addWidget(icon, alignment=Qt.AlignTop)

        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #1B5E20; font-size: 12px; font-weight: 600;")
        row.addWidget(lbl, stretch=1)

        return panel, lbl
    
    def create_guided_panel(self, title: str, description: str | list[str]) -> QFrame:
        """Create a styled guidance card with a title and bullet content."""
        panel = QFrame()
        panel.setProperty("card", "true")
        panel.setProperty("guided", "true")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("StepTitle")
        layout.addWidget(title_lbl)
        if isinstance(description, str):
            description = [description]
        desc_lbl = QLabel()
        for desc in description:
            desc_lbl.setText(desc_lbl.text() + "• " + desc + "<br>")
        desc_lbl.setObjectName("BodyText")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)

        return panel
    
    def create_guided_questionnaire(self, question: str, info: str = None, options: list[QWidget]=None) -> QFrame:
        """Create a question card with supporting info and custom options."""
        questionnaire = QFrame()
        questionnaire.setProperty("card", "true")
        questionnaire.setProperty("guided", "true")
        layout = QVBoxLayout(questionnaire)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(16)
        question_lbl = QLabel(question)
        question_lbl.setObjectName("StepTitle")
        question_lbl.setWordWrap(True)
        # question_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(question_lbl)

        if info:
            info_lbl = QLabel(info)
            info_lbl.setObjectName("BodyText")
            info_lbl.setWordWrap(True)
            # info_lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)
            info_lbl.setStyleSheet("font-size: 14px;")
            layout.addWidget(info_lbl)
        if options:
            for option in options:
                layout.addWidget(option)

        return questionnaire
    
    def create_stat_chip_row(self, chips: list[str]) -> QWidget:
        """Create a centered row of compact status chips."""
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addStretch(1)

        for text in chips:
            chip = QLabel(text)
            chip.setObjectName("StatChip")
            layout.addWidget(chip)

        layout.addStretch(1)
        return row
    
    def radio_with_hint(self, text: str, hint: str) -> QFrame:
        """Create a radio button with a short explanatory hint."""
        radio = QRadioButton(text)

        hint_label = QLabel(hint)
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("color: gray; font-size: 12px; margin-left: 20px;")
        hint_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.MinimumExpanding)

        layout = QVBoxLayout()
        layout.addWidget(radio)
        layout.addWidget(hint_label)
        container = QFrame()
        container.setLayout(layout)
        return container
    
    def create_page_header(self, icon: str, title: str, subtitle: str = "") -> QWidget:
        """Create a prominent page header with icon, bold title, and optional subtitle."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 4, 0, 8)
        layout.setSpacing(6)

        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("PageIcon")
        icon_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("PageTitle")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setWordWrap(True)
        layout.addWidget(title_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setObjectName("PageSubtitle")
            sub_lbl.setAlignment(Qt.AlignCenter)
            sub_lbl.setWordWrap(True)
            layout.addWidget(sub_lbl)

        return container

    def hint_label(self, text: str) -> QLabel:
        """Create a small muted hint label."""
        hint_label = QLabel(text)
        hint_label.setWordWrap(True)
        hint_label.setStyleSheet("font-size: 12px; color: #546E7A; margin-left: 20px;")
        return hint_label
    
    def activit_list(self) -> QListWidget:
        """Create a simple activity list widget for logging."""
        
        a_list = QListWidget()
        # a_list.setObjectName("ActivityLog")
        a_list.setMinimumHeight(92)
        a_list.setMaximumHeight(136)

        return a_list
    
    def checklist_item(self, text: str, checked: bool) -> QListWidgetItem:
        """Create a checklist item with a checkbox."""
        item = QListWidgetItem(text)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        return item
        

    # ── HTML report helpers ──────────────────────────────────────────────────
    # Used by pages that render rich content into QTextEdit#ReportView widgets.
    # HTML content styles must be inline — Qt's HTML renderer ignores .qss.

    @staticmethod
    def html_pill(text: str, color: str = "#1565C0", bg: str = "#E3F2FD") -> str:
        """Small coloured badge for use inside report HTML."""
        return (
            f'<span style="background:{bg};color:{color};border-radius:4px;'
            f'padding:1px 7px;font-size:12px;font-weight:600;">{text}</span>'
        )

    @staticmethod
    def html_row(label: str, value: str) -> str:
        """One key-value table row for report sections."""
        return (
            f'<tr>'
            f'<td style="color:#546E7A;padding:3px 12px 3px 0;white-space:nowrap;font-size:13px;">{label}</td>'
            f'<td style="color:#0D1929;padding:3px 0;font-weight:500;font-size:13px;">{value}</td>'
            f'</tr>'
        )

    @staticmethod
    def html_section(icon: str, title: str, body: str) -> str:
        """Titled section block with a blue header line."""
        return (
            f'<div style="margin-bottom:14px;">'
            f'<div style="color:#1565C0;font-size:13px;font-weight:700;letter-spacing:0.3px;'
            f'margin-bottom:6px;border-bottom:1px solid #BBDEFB;padding-bottom:4px;">'
            f'{icon}&nbsp;&nbsp;{title}</div>'
            f'{body}'
            f'</div>'
        )

    @staticmethod
    def html_wrap(body: str) -> str:
        """Wrap body HTML in a full document with consistent base font."""
        return (
            '<html><body style="font-family:\'Segoe UI\',\'Noto Sans\',sans-serif;'
            'font-size:14px;color:#0D1929;margin:0;padding:0;">'
            + body
            + '</body></html>'
        )

    @staticmethod
    def html_empty(message: str) -> str:
        """Muted placeholder shown when a section has no data yet."""
        return f'<span style="color:#90A4AE;font-size:13px;">{message}</span>'

    def refresh(self) -> None:
        """Refresh page content when global state changes."""
