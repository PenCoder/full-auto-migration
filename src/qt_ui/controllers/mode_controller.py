"""Mode and presentation behavior controller for the Qt migration window."""

from __future__ import annotations


class ModeController:
    """Apply guided/balanced/expert presentation behavior and mode changes."""

    def __init__(
        self,
        ui_state,
        expert_panel,
        expert_dock,
        expert_toggle_btn,
        complete_all_btn,
        mode_badge,
        stack,
        log_activity,
    ) -> None:
        self.ui_state = ui_state
        self.expert_panel = expert_panel
        self.expert_dock = expert_dock
        self.expert_toggle_btn = expert_toggle_btn
        self.complete_all_btn = complete_all_btn
        self.mode_badge = mode_badge
        self.stack = stack
        self.log_activity = log_activity

    def on_mode_change(self, value: str) -> None:
        self.ui_state.mode = value
        self.mode_badge.setText(f"Mode Status: {value.capitalize()}")
        self.apply_mode_presentation(value)
        self.log_activity("system", f"Interaction mode changed to {value}.")
        for i in range(self.stack.count()):
            page = self.stack.widget(i)
            refresh = getattr(page, "refresh", None)
            if callable(refresh):
                refresh()

    def apply_mode_presentation(self, mode: str) -> None:
        self.expert_panel.apply_mode(mode)

        if mode == "guided":
            if self.expert_dock.isVisible():
                self.expert_dock.hide()
            self.ui_state.expert_panel_visible = False
            self.expert_toggle_btn.setText("Show Customize")
            self.expert_toggle_btn.setEnabled(False)
            return

        if mode == "expert":
            if not self.expert_dock.isVisible():
                self.expert_dock.show()
            self.ui_state.expert_panel_visible = True
            self.expert_toggle_btn.setText("Hide Customize")
            self.expert_toggle_btn.setEnabled(True)
            self.complete_all_btn.setEnabled(True)
            return

        # balanced mode keeps manual control, defaulting to hidden expert panel
        if self.expert_dock.isVisible() and not self.ui_state.expert_panel_visible:
            self.expert_dock.hide()
        self.expert_toggle_btn.setEnabled(True)
        self.complete_all_btn.setEnabled(True)
        self.expert_toggle_btn.setText("Hide Customize" if self.expert_dock.isVisible() else "Show Customize")

    def toggle_expert_panel(self) -> None:
        if self.ui_state.mode == "guided":
            return
        if self.expert_dock.isVisible():
            self.expert_dock.hide()
            self.ui_state.expert_panel_visible = False
            self.expert_toggle_btn.setText("Show Customize")
        else:
            self.expert_dock.show()
            self.ui_state.expert_panel_visible = True
            self.expert_toggle_btn.setText("Hide Customize")
