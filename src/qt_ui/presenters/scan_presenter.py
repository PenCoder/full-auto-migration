"""
Presenter for the inventory scan page.

This presenter handles inventory collection, scanning (quick/deep),
and recommendation generation for applications.
"""

from __future__ import annotations

from typing import Callable, Optional

from src.qt_ui.presenters.base_presenter import BasePresenter
from src.qt_ui.state import QtUiState


class ScanPresenter(BasePresenter):
    """
    Presenter for inventory scan page.

    Manages the logic for collecting system inventory, running scans
    (quick or deep), and generating application recommendations.
    """

    VALID_STRATEGIES = {"migrate_all", "prioritize"}
    VALID_SCAN_TYPES = {"quick", "deep"}
    VALID_RECOMMENDATION_TYPES = {"online", "agent"}

    def __init__(
        self,
        ui_state: QtUiState,
        run_inventory_cb: Callable[[bool], dict],
        run_recommendations_cb: Callable[[str, str], dict],
    ) -> None:
        """
        Initialize the scan presenter.

        Parameters
        ----------
        ui_state : QtUiState
            The shared UI state object.
        run_inventory_cb : Callable[[bool], dict]
            Callback to run inventory collection.
            Takes deep_scan (bool) and returns inventory dict.
        run_recommendations_cb : Callable[[str, str], dict]
            Callback to generate recommendations.
            Takes recommendation_type (str) and strategy (str),
            returns recommendations dict.
        """
        super().__init__(ui_state)
        self.run_inventory_cb = run_inventory_cb
        self.run_recommendations_cb = run_recommendations_cb
        self.update_page_title("Scan System & Generate Recommendations")

    def on_page_shown(self) -> None:
        """Called when the page is shown."""
        self.refresh()

    def set_recommendation_strategy(self, strategy: str) -> None:
        """
        Set the recommendation strategy.

        Parameters
        ----------
        strategy : str
            The strategy to use ("migrate_all" or "prioritize").

        Raises
        ------
        ValueError
            If the strategy is not valid.
        """
        if strategy not in self.VALID_STRATEGIES:
            raise ValueError(f"Invalid strategy: {strategy}. Must be one of {self.VALID_STRATEGIES}")

        self.ui_state.recommendation_strategy = strategy
        self.refresh()

    def get_recommendation_strategy(self) -> str:
        """
        Get the current recommendation strategy.

        Returns
        -------
        str
            The current recommendation strategy.
        """
        return self.ui_state.recommendation_strategy

    def run_inventory_scan(self, scan_type: str = "quick") -> None:
        """
        Run an inventory scan (quick or deep).

        This method:
        1. Sets loading state
        2. Calls the inventory callback
        3. Marks inventory as completed
        4. Clears loading state
        5. Emits signals for UI updates

        Parameters
        ----------
        scan_type : str
            Type of scan ("quick" or "deep").

        Raises
        ------
        ValueError
            If scan_type is not valid.
        """
        if scan_type not in self.VALID_SCAN_TYPES:
            raise ValueError(f"Invalid scan type: {scan_type}. Must be one of {self.VALID_SCAN_TYPES}")

        deep_scan = scan_type == "deep"

        try:
            self.set_loading(True)

            # Call the service callback
            result = self.run_inventory_cb(deep_scan)

            # Update state
            self.ui_state.inventory_completed = True
            self.refresh()

        except Exception as e:
            self.handle_error(e)
        finally:
            self.set_loading(False)

    def run_recommendation_generation(self, rec_type: str = "online") -> None:
        """
        Generate application recommendations.

        This method:
        1. Sets loading state
        2. Calls the recommendation callback
        3. Marks analysis as completed
        4. Clears loading state
        5. Emits signals for UI updates

        Parameters
        ----------
        rec_type : str
            Type of recommendation ("online" or "agent").

        Raises
        ------
        ValueError
            If rec_type is not valid.
        """
        if rec_type not in self.VALID_RECOMMENDATION_TYPES:
            raise ValueError(
                f"Invalid recommendation type: {rec_type}. Must be one of {self.VALID_RECOMMENDATION_TYPES}"
            )

        try:
            self.set_loading(True)

            # Call the service callback with strategy
            result = self.run_recommendations_cb(rec_type, self.ui_state.recommendation_strategy)

            # Update state
            self.ui_state.analysis_completed = True
            self.refresh()

        except Exception as e:
            self.handle_error(e)
        finally:
            self.set_loading(False)

    def is_inventory_completed(self) -> bool:
        """Check if inventory collection is completed."""
        return self.ui_state.inventory_completed

    def is_recommendations_completed(self) -> bool:
        """Check if recommendation generation is completed."""
        return self.ui_state.analysis_completed

    def on_page_before_next(self) -> bool:
        """
        Validate before advancing to the next page.

        Returns
        -------
        bool
            True if both inventory and recommendations are completed.
        """
        if not self.ui_state.inventory_completed:
            self.emit_error("Please run a scan first.")
            return False

        if not self.ui_state.analysis_completed:
            self.emit_error("Please generate recommendations first.")
            return False

        return True

    def refresh(self) -> None:
        """Refresh presenter state based on ui_state."""
        # State is in ui_state, so just validate consistency
        # This could emit signals to update UI if needed
        pass
