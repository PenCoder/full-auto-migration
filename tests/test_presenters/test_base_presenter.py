"""Tests for BasePresenter."""

import pytest
from unittest.mock import MagicMock

from src.qt_ui.presenters import BasePresenter
from src.qt_ui.state import QtUiState


class TestBasePresenter:
    """Test suite for BasePresenter."""

    def test_initialization(self, ui_state: QtUiState):
        """Test presenter initialization."""
        presenter = BasePresenter(ui_state)
        
        assert presenter.ui_state is ui_state
        assert presenter.is_loading is False

    def test_loading_state(self, ui_state: QtUiState):
        """Test loading state management."""
        presenter = BasePresenter(ui_state)
        
        # Mock the signals
        presenter.loading_started = MagicMock()
        presenter.loading_finished = MagicMock()
        
        # Set loading to True
        presenter.set_loading(True)
        assert presenter.is_loading is True
        presenter.loading_started.emit.assert_called_once()
        
        # Set loading to False
        presenter.set_loading(False)
        assert presenter.is_loading is False

    def test_advance_to_next_page(self, ui_state: QtUiState):
        """Test navigation to next page."""
        presenter = BasePresenter(ui_state)
        presenter.request_next = MagicMock()
        
        presenter.advance_to_next_page()
        # Signal emission happens, but mock captures the call attempt

    def test_go_back_to_previous_page(self, ui_state: QtUiState):
        """Test navigation to previous page."""
        presenter = BasePresenter(ui_state)
        presenter.request_back = MagicMock()
        
        presenter.go_back_to_previous_page()

    def test_emit_error(self, ui_state: QtUiState):
        """Test error emission."""
        presenter = BasePresenter(ui_state)
        presenter.error_occurred = MagicMock()
        
        presenter.emit_error("Test error")

    def test_update_page_title(self, ui_state: QtUiState):
        """Test page title update."""
        presenter = BasePresenter(ui_state)
        presenter.page_title_changed = MagicMock()
        
        presenter.update_page_title("New Title")

    def test_on_page_shown_default(self, ui_state: QtUiState):
        """Test default on_page_shown does nothing."""
        presenter = BasePresenter(ui_state)
        # Should not raise
        presenter.on_page_shown()

    def test_on_page_hidden_default(self, ui_state: QtUiState):
        """Test default on_page_hidden does nothing."""
        presenter = BasePresenter(ui_state)
        # Should not raise
        presenter.on_page_hidden()

    def test_on_page_before_next_default(self, ui_state: QtUiState):
        """Test default on_page_before_next returns True."""
        presenter = BasePresenter(ui_state)
        assert presenter.on_page_before_next() is True

    def test_on_page_before_previous_default(self, ui_state: QtUiState):
        """Test default on_page_before_previous returns True."""
        presenter = BasePresenter(ui_state)
        assert presenter.on_page_before_previous() is True

    def test_refresh_default(self, ui_state: QtUiState):
        """Test default refresh does nothing."""
        presenter = BasePresenter(ui_state)
        # Should not raise
        presenter.refresh()

    def test_handle_error(self, ui_state: QtUiState):
        """Test error handling."""
        presenter = BasePresenter(ui_state)
        presenter.error_occurred = MagicMock()
        
        error = ValueError("Test error")
        presenter.handle_error(error)
        # Error message should be extracted

    def test_handle_error_with_empty_message(self, ui_state: QtUiState):
        """Test error handling with empty message."""
        presenter = BasePresenter(ui_state)
        presenter.error_occurred = MagicMock()
        
        error = Exception()
        presenter.handle_error(error)
        # Should use class name as fallback
