"""Shared base helpers for Qt wizard pages."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.qt_ui.state import QtUiState


class _ChoiceCard(QFrame):
    """Card wrapping a radio + hint label, pinning the hint's height directly.

    Qt's heightForWidth propagation through several nested QVBoxLayout
    levels (page -> StepCard -> questionnaire -> choice card -> hint label)
    is unreliable and routinely under-reports, silently clipping the
    word-wrapped hint text. Recomputing the hint's required height directly
    against this card's own current width on every resize sidesteps that
    propagation entirely instead of depending on it.
    """

    def __init__(self, hint_label: QLabel | None = None) -> None:
        super().__init__()
        self._hint_label = hint_label
        self._adjusting = False

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._adjusting or self._hint_label is None or self._hint_label.width() <= 0:
            return
        needed = self._hint_label.heightForWidth(self._hint_label.width())
        if needed > 0 and needed != self._hint_label.minimumHeight():
            self._adjusting = True
            try:
                self._hint_label.setMinimumHeight(needed)
                # updateGeometry() alone is not enough here: the immediate
                # parent layout (the questionnaire frame's QVBoxLayout) caches
                # this card's minimumSizeHint from the first layout pass —
                # before the hint label corrected its own height — and
                # doesn't reliably re-query it on its own. Force the parent
                # to actually re-run its layout with the corrected value.
                self.updateGeometry()
                parent = self.parentWidget()
                if parent is not None:
                    parent.updateGeometry()
                    parent_layout = parent.layout()
                    if parent_layout is not None:
                        parent_layout.activate()
            finally:
                self._adjusting = False


class BasePage(QWidget):
    """Common scaffolding for the migration wizard pages."""

    request_next = Signal()
    request_back = Signal()
    request_finish = Signal()
    loading_progress = Signal(int)
    mode_changed = Signal(str)
    processing_changed = Signal(bool)

    def __init__(self, ui_state: QtUiState) -> None:
        """Store the shared UI state for a page."""
        super().__init__()
        self.ui_state = ui_state
        self.is_processing: bool = False

    def create_center_card_layout(self, max_width: int = 1040) -> QVBoxLayout:
        """Create a centered card layout used by the wizard pages."""
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 24, 0, 24)

        card = QWidget()
        card.setObjectName("StepCard")
        card.setMinimumWidth(560)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._card_max_width = max_width

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 28, 32, 28)
        card_layout.setSpacing(14)

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(36)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(63, 111, 224, 35))
        card.setGraphicsEffect(shadow)

        # Stored so main_window can reparent the shared nav button bar into
        # the bottom of whichever page's card is currently showing.
        self.card_widget = card
        self.card_layout = card_layout

        # Centering via addWidget(card, alignment=...) sizes the card to its
        # sizeHint() and ignores the Expanding policy entirely. Centering via
        # stretches on either side instead doesn't help either — empirically
        # QBoxLayout keeps a widget at its sizeHint/minimum and lets the
        # stretch *spacers* absorb all the extra space, regardless of the
        # widget's own stretch factor or Expanding policy. Both are reliable
        # Qt footguns here, so the card's width is instead set imperatively
        # in resizeEvent() below — these stretches now only matter for
        # whatever's left over once the card hits max_width.
        center_row = QHBoxLayout()
        center_row.setContentsMargins(0, 0, 0, 0)
        center_row.addStretch(1)
        center_row.addWidget(card)
        center_row.addStretch(1)

        page_layout.addLayout(center_row)
        page_layout.addStretch(1)
        return card_layout

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        card = getattr(self, "card_widget", None)
        if card is not None:
            max_width = getattr(self, "_card_max_width", 1040)
            card.setFixedWidth(min(self.width(), max_width))

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
            "QFrame#InfoPanel { background-color: #DCE6FF; border: none; border-radius: 16px; }"
            " QLabel { background: transparent; border: none; }"
        )
        panel.setObjectName("InfoPanel")
        row = QHBoxLayout(panel)
        row.setContentsMargins(14, 8, 14, 8)
        row.setSpacing(10)

        icon = QLabel("ℹ")
        icon.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        icon.setFixedWidth(16)
        icon.setStyleSheet("color: #1B3A86; font-size: 16px; font-weight: bold;")
        row.addWidget(icon)

        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #1B3A86; font-size: 14px;")
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
            "QFrame#SuccessPanel { background-color: #E3F6E9; border: none; border-radius: 16px; }"
            " QLabel { background: transparent; border: none; }"
        )
        row = QHBoxLayout(panel)
        row.setContentsMargins(14, 8, 14, 8)
        row.setSpacing(10)

        icon = QLabel("✓")
        icon.setFixedSize(20, 20)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(
            "background-color: #2E7D32; color: white; font-size: 14px; font-weight: bold;"
            " border-radius: 10px;"
        )
        row.addWidget(icon, alignment=Qt.AlignTop)

        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #1B5E20; font-size: 14px; font-weight: 600;")
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
        questionnaire.setProperty("card", "section")
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
            info_lbl.setStyleSheet("font-size: 16px;")
            layout.addWidget(info_lbl)
        if options:
            # Wrapping each radio in its own card frame breaks Qt's automatic
            # same-parent exclusivity grouping (radios are only mutually
            # exclusive when they share a direct parent) — group them
            # explicitly so only one choice can be selected at a time.
            button_group = QButtonGroup(questionnaire)
            button_group.setExclusive(True)
            self._button_groups = getattr(self, "_button_groups", [])
            self._button_groups.append(button_group)

            i = 0
            while i < len(options):
                widget = options[i]
                if isinstance(widget, QRadioButton):
                    button_group.addButton(widget)
                    i += 1
                    hint_widget = None
                    if i < len(options) and isinstance(options[i], QLabel):
                        hint_widget = options[i]
                        i += 1
                    card = _ChoiceCard(hint_widget)
                    card.setProperty("choice", "true")
                    card_layout = QVBoxLayout(card)
                    card_layout.setContentsMargins(14, 10, 14, 10)
                    card_layout.setSpacing(4)
                    card_layout.addWidget(widget)
                    if hint_widget is not None:
                        card_layout.addWidget(hint_widget)
                    self._wire_choice_card(card, widget)
                    layout.addWidget(card)
                else:
                    layout.addWidget(widget)
                    i += 1

        return questionnaire

    @staticmethod
    def _wire_choice_card(card: QFrame, radio: QRadioButton) -> None:
        """Keep a choice card's selected styling and visibility in sync with its radio button."""

        def _sync_selected(checked: bool) -> None:
            card.setProperty("selected", "true" if checked else "false")
            style = card.style()
            style.unpolish(card)
            style.polish(card)

        radio.toggled.connect(_sync_selected)
        _sync_selected(radio.isChecked())

        # Pages hide/show a radio directly (mode-filtered choices) without
        # knowing the card wrapper exists. A Show/Hide event filter can't
        # reliably mirror this: the radio is a *child* of the card, so once
        # the card itself is hidden, Qt won't deliver further Show events to
        # the radio (an already-hidden ancestor suppresses them) — that
        # leaves the card stuck hidden forever. Intercepting setVisible
        # directly sidesteps the ancestor-visibility coupling entirely.
        original_set_visible = radio.setVisible

        def _patched_set_visible(visible: bool) -> None:
            card.setVisible(visible)
            original_set_visible(visible)

        radio.setVisible = _patched_set_visible
        radio.show = lambda: _patched_set_visible(True)
        radio.hide = lambda: _patched_set_visible(False)


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
        hint_label.setStyleSheet("color: gray; font-size: 14px; margin-left: 20px;")
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
        hint_label.setStyleSheet("font-size: 14px; color: #6B7390; margin-left: 20px;")
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
    def html_pill(text: str, color: str = "#1B3A86", bg: str = "#DCE6FF") -> str:
        """Small coloured badge for use inside report HTML."""
        return (
            f'<span style="background:{bg};color:{color};border-radius:8px;'
            f'padding:1px 8px;font-size: 14px;font-weight:600;">{text}</span>'
        )

    @staticmethod
    def html_row(label: str, value: str) -> str:
        """One key-value table row for report sections."""
        return (
            f'<tr>'
            f'<td style="color:#6B7390;padding:3px 12px 3px 0;white-space:nowrap;font-size: 15px;">{label}</td>'
            f'<td style="color:#1B1E28;padding:3px 0;font-weight:500;font-size: 15px;">{value}</td>'
            f'</tr>'
        )

    @staticmethod
    def html_section(icon: str, title: str, body: str) -> str:
        """Titled section block with a blue header line."""
        return (
            f'<div style="margin-bottom:14px;">'
            f'<div style="color:#3F6FE0;font-size: 15px;font-weight:700;letter-spacing:0.3px;'
            f'margin-bottom:6px;border-bottom:1px solid #B7C9F7;padding-bottom:4px;">'
            f'{icon}&nbsp;&nbsp;{title}</div>'
            f'{body}'
            f'</div>'
        )

    @staticmethod
    def html_wrap(body: str) -> str:
        """Wrap body HTML in a full document with consistent base font."""
        return (
            '<html><body style="font-family:\'Segoe UI\',\'Noto Sans\',sans-serif;'
            'font-size: 16px;color:#1B1E28;margin:0;padding:0;">'
            + body
            + '</body></html>'
        )

    @staticmethod
    def html_empty(message: str) -> str:
        """Muted placeholder shown when a section has no data yet."""
        return f'<span style="color:#9AA6C0;font-size: 15px;">{message}</span>'

    def refresh(self) -> None:
        """Refresh page content when global state changes."""
