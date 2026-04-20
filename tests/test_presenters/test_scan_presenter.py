"""Tests for ScanPresenter."""

import pytest
from unittest.mock import MagicMock

from src.qt_ui.presenters import ScanPresenter
from src.qt_ui.state import QtUiState


class TestScanPresenter:
    """Test suite for ScanPresenter."""

    def test_initialization(self, ui_state: QtUiState, mock_inventory_callback, mock_recommendations_callback):
        """Test presenter initialization."""
        presenter = ScanPresenter(ui_state, mock_inventory_callback, mock_recommendations_callback)
        
        assert presenter.ui_state is ui_state
        assert presenter.get_recommendation_strategy() == "migrate_all"  # Default

    def test_set_valid_strategy(self, ui_state: QtUiState, mock_inventory_callback, mock_recommendations_callback):
        """Test setting a valid strategy."""
        presenter = ScanPresenter(ui_state, mock_inventory_callback, mock_recommendations_callback)
        
        presenter.set_recommendation_strategy("prioritize")
        assert presenter.get_recommendation_strategy() == "prioritize"

    def test_set_invalid_strategy(self, ui_state: QtUiState, mock_inventory_callback, mock_recommendations_callback):
        """Test that invalid strategies raise ValueError."""
        presenter = ScanPresenter(ui_state, mock_inventory_callback, mock_recommendations_callback)
        
        with pytest.raises(ValueError):
            presenter.set_recommendation_strategy("invalid_strategy")

    def test_inventory_not_completed_initially(self, ui_state: QtUiState, mock_inventory_callback, mock_recommendations_callback):
        """Test that inventory is not completed initially."""
        presenter = ScanPresenter(ui_state, mock_inventory_callback, mock_recommendations_callback)
        assert presenter.is_inventory_completed() is False

    def test_recommendations_not_completed_initially(self, ui_state: QtUiState, mock_inventory_callback, mock_recommendations_callback):
        """Test that recommendations are not completed initially."""
        presenter = ScanPresenter(ui_state, mock_inventory_callback, mock_recommendations_callback)
        assert presenter.is_recommendations_completed() is False

    def test_before_next_without_inventory(self, ui_state: QtUiState, mock_inventory_callback, mock_recommendations_callback):
        """Test validation fails without inventory."""
        presenter = ScanPresenter(ui_state, mock_inventory_callback, mock_recommendations_callback)
        presenter.error_occurred = MagicMock()
        
        result = presenter.on_page_before_next()
        assert result is False

    def test_before_next_without_recommendations(self, ui_state: QtUiState, mock_inventory_callback, mock_recommendations_callback):
        """Test validation fails without recommendations."""
        presenter = ScanPresenter(ui_state, mock_inventory_callback, mock_recommendations_callback)
        ui_state.inventory_completed = True
        presenter.error_occurred = MagicMock()
        
        result = presenter.on_page_before_next()
        assert result is False

    def test_before_next_with_both_completed(self, ui_state: QtUiState, mock_inventory_callback, mock_recommendations_callback):
        """Test validation passes with both completed."""
        presenter = ScanPresenter(ui_state, mock_inventory_callback, mock_recommendations_callback)
        ui_state.inventory_completed = True
        ui_state.analysis_completed = True
        
        result = presenter.on_page_before_next()
        assert result is True

    def test_valid_scan_types(self):
        """Test that valid scan types are defined."""
        assert ScanPresenter.VALID_SCAN_TYPES == {"quick", "deep"}

    def test_valid_strategies(self):
        """Test that valid strategies are defined."""
        assert ScanPresenter.VALID_STRATEGIES == {"migrate_all", "prioritize"}

    def test_valid_recommendation_types(self):
        """Test that valid recommendation types are defined."""
        assert ScanPresenter.VALID_RECOMMENDATION_TYPES == {"online", "agent"}

    def test_run_invalid_scan_type(self, ui_state: QtUiState, mock_inventory_callback, mock_recommendations_callback):
        """Test that invalid scan types raise ValueError."""
        presenter = ScanPresenter(ui_state, mock_inventory_callback, mock_recommendations_callback)
        
        with pytest.raises(ValueError):
            presenter.run_inventory_scan("invalid_type")

    def test_run_invalid_recommendation_type(self, ui_state: QtUiState, mock_inventory_callback, mock_recommendations_callback):
        """Test that invalid recommendation types raise ValueError."""
        presenter = ScanPresenter(ui_state, mock_inventory_callback, mock_recommendations_callback)
        
        with pytest.raises(ValueError):
            presenter.run_recommendation_generation("invalid_type")

    def test_strategy_persistence(self, ui_state: QtUiState, mock_inventory_callback, mock_recommendations_callback):
        """Test that strategy persists in ui_state."""
        presenter = ScanPresenter(ui_state, mock_inventory_callback, mock_recommendations_callback)
        
        presenter.set_recommendation_strategy("prioritize")
        assert ui_state.recommendation_strategy == "prioritize"

    def test_page_shown(self, ui_state: QtUiState, mock_inventory_callback, mock_recommendations_callback):
        """Test on_page_shown calls refresh."""
        presenter = ScanPresenter(ui_state, mock_inventory_callback, mock_recommendations_callback)
        # Should not raise
        presenter.on_page_shown()
