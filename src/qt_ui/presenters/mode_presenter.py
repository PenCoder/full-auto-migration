"""
Presenter for the mode selection page.

This presenter handles the logic for choosing between guided, balanced,
and expert migration modes.
"""

from __future__ import annotations

from src.qt_ui.presenters.base_presenter import BasePresenter
from src.qt_ui.state import QtUiState


class ModePresenter(BasePresenter):
    """
    Presenter for mode selection page.

    Manages the state and logic for selecting the migration mode
    (guided, balanced, or expert).
    """

    VALID_MODES = {"guided", "balanced", "expert"}

    def __init__(self, ui_state: QtUiState) -> None:
        """
        Initialize the mode presenter.

        Parameters
        ----------
        ui_state : QtUiState
            The shared UI state object.
        """
        super().__init__(ui_state)
        self.update_page_title("Choose Migration Mode")

    def on_page_shown(self) -> None:
        """
        Called when the page is shown.

        Refresh the state based on current ui_state.
        """
        self.refresh()

    def set_mode(self, mode: str) -> None:
        """
        Set the migration mode.

        Parameters
        ----------
        mode : str
            The migration mode ("guided", "balanced", or "expert").

        Raises
        ------
        ValueError
            If the mode is not a valid choice.
        """
        if mode not in self.VALID_MODES:
            raise ValueError(f"Invalid mode: {mode}. Must be one of {self.VALID_MODES}")

        self.ui_state.mode = mode
        self.refresh()

    def get_mode(self) -> str:
        """
        Get the currently selected migration mode.

        Returns
        -------
        str
            The current migration mode.
        """
        return self.ui_state.mode

    def get_mode_description(self) -> str:
        """
        Get a user-friendly description of the selected mode.

        Returns
        -------
        str
            Description of the current mode.
        """
        descriptions = {
            "guided": "You'll be guided through each step with recommended defaults and explanations.",
            "balanced": "You'll get recommended defaults but can customize key choices.",
            "expert": "You'll have full control and see all options upfront.",
        }
        return descriptions.get(self.ui_state.mode, "")

    def on_page_before_next(self) -> bool:
        """
        Validate before advancing to the next page.

        Returns
        -------
        bool
            Always True as mode is always set.
        """
        return True

    def refresh(self) -> None:
        """
        Refresh presenter state.

        This ensures internal state matches ui_state.
        """
        # Mode is stored in ui_state, so nothing to do here
        # But this method exists for consistency with the pattern
        pass
