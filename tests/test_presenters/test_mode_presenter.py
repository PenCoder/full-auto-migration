"""Tests for ModePresenter."""

import pytest
from src.qt_ui.presenters import ModePresenter
from src.qt_ui.state import QtUiState


class TestModePresenter:
    """Test suite for ModePresenter."""

    def test_initialization(self, ui_state: QtUiState):
        """Test presenter initialization."""
        presenter = ModePresenter(ui_state)
        assert presenter.ui_state is ui_state
        assert presenter.get_mode() == "guided"  # Default

    def test_set_valid_mode(self, ui_state: QtUiState):
        """Test setting a valid mode."""
        presenter = ModePresenter(ui_state)
        
        presenter.set_mode("balanced")
        assert presenter.get_mode() == "balanced"
        
        presenter.set_mode("expert")
        assert presenter.get_mode() == "expert"

    def test_set_invalid_mode(self, ui_state: QtUiState):
        """Test that invalid modes raise ValueError."""
        presenter = ModePresenter(ui_state)
        
        with pytest.raises(ValueError):
            presenter.set_mode("invalid_mode")

    def test_get_mode_description(self, ui_state: QtUiState):
        """Test getting mode descriptions."""
        presenter = ModePresenter(ui_state)
        
        # Test guided
        ui_state.mode = "guided"
        desc = presenter.get_mode_description()
        assert "guided" in desc.lower()
        
        # Test balanced
        ui_state.mode = "balanced"
        desc = presenter.get_mode_description()
        assert "recommended defaults" in desc.lower()
        
        # Test expert
        ui_state.mode = "expert"
        desc = presenter.get_mode_description()
        assert "full control" in desc.lower()

    def test_mode_validation_before_next(self, ui_state: QtUiState):
        """Test that validation always passes for mode (it's always set)."""
        presenter = ModePresenter(ui_state)
        
        # Mode is always valid
        assert presenter.on_page_before_next() is True
        
        # Change mode
        presenter.set_mode("expert")
        assert presenter.on_page_before_next() is True

    def test_valid_modes_constant(self):
        """Test that VALID_MODES constant is set correctly."""
        assert ModePresenter.VALID_MODES == {"guided", "balanced", "expert"}

    def test_refresh(self, ui_state: QtUiState):
        """Test refresh method."""
        presenter = ModePresenter(ui_state)
        # Should not raise
        presenter.refresh()

    def test_mode_state_persists(self, ui_state: QtUiState):
        """Test that mode state persists in ui_state."""
        presenter = ModePresenter(ui_state)
        
        presenter.set_mode("expert")
        assert ui_state.mode == "expert"
        
        # Create new presenter with same state
        presenter2 = ModePresenter(ui_state)
        assert presenter2.get_mode() == "expert"

    def test_all_valid_modes_can_be_set(self, ui_state: QtUiState):
        """Test that all valid modes can be set without error."""
        presenter = ModePresenter(ui_state)
        
        for mode in ModePresenter.VALID_MODES:
            presenter.set_mode(mode)
            assert presenter.get_mode() == mode
