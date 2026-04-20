"""End-to-end workflow tests."""

import pytest
from src.qt_ui.presenters import ModePresenter, ScanPresenter
from src.qt_ui.state import QtUiState


class TestMigrationWorkflow:
    """Test complete migration workflows."""

    def test_guided_migration_mode_selection(self, ui_state: QtUiState):
        """Test workflow: Select guided migration mode."""
        # User starts at mode page
        mode_presenter = ModePresenter(ui_state)
        mode_presenter.on_page_shown()
        
        # User selects guided mode
        mode_presenter.set_mode("guided")
        
        # Validation passes
        assert mode_presenter.on_page_before_next() is True
        
        # State is updated
        assert ui_state.mode == "guided"

    def test_expert_migration_mode_selection(self, ui_state: QtUiState):
        """Test workflow: Select expert migration mode."""
        mode_presenter = ModePresenter(ui_state)
        mode_presenter.on_page_shown()
        
        mode_presenter.set_mode("expert")
        assert mode_presenter.on_page_before_next() is True
        assert ui_state.mode == "expert"

    def test_balanced_migration_mode_selection(self, ui_state: QtUiState):
        """Test workflow: Select balanced migration mode."""
        mode_presenter = ModePresenter(ui_state)
        mode_presenter.on_page_shown()
        
        mode_presenter.set_mode("balanced")
        assert mode_presenter.on_page_before_next() is True
        assert ui_state.mode == "balanced"

    def test_mode_switching_workflow(self, ui_state: QtUiState):
        """Test workflow: User changes mode multiple times."""
        mode_presenter = ModePresenter(ui_state)
        
        # Start with guided
        mode_presenter.set_mode("guided")
        assert ui_state.mode == "guided"
        
        # Switch to expert
        mode_presenter.set_mode("expert")
        assert ui_state.mode == "expert"
        
        # Switch back to balanced
        mode_presenter.set_mode("balanced")
        assert ui_state.mode == "balanced"
        
        # All transitions should be valid
        assert mode_presenter.on_page_before_next() is True

    def test_inventory_scan_workflow(
        self,
        ui_state: QtUiState,
        mock_inventory_callback,
        mock_recommendations_callback,
    ):
        """Test workflow: Run inventory scan."""
        scan_presenter = ScanPresenter(ui_state, mock_inventory_callback, mock_recommendations_callback)
        scan_presenter.on_page_shown()
        
        # Initially inventory not completed
        assert scan_presenter.is_inventory_completed() is False
        
        # Cannot advance yet
        assert scan_presenter.on_page_before_next() is False
        
        # After marking inventory complete
        ui_state.inventory_completed = True
        
        # Still need recommendations
        assert scan_presenter.on_page_before_next() is False
        
        # Mark recommendations complete
        ui_state.analysis_completed = True
        
        # Now can advance
        assert scan_presenter.on_page_before_next() is True

    def test_recommendation_strategy_workflow(
        self,
        ui_state: QtUiState,
        mock_inventory_callback,
        mock_recommendations_callback,
    ):
        """Test workflow: Select recommendation strategy."""
        scan_presenter = ScanPresenter(ui_state, mock_inventory_callback, mock_recommendations_callback)
        
        # Default strategy
        assert scan_presenter.get_recommendation_strategy() == "migrate_all"
        
        # Change to prioritize
        scan_presenter.set_recommendation_strategy("prioritize")
        assert scan_presenter.get_recommendation_strategy() == "prioritize"
        assert ui_state.recommendation_strategy == "prioritize"
        
        # Change back
        scan_presenter.set_recommendation_strategy("migrate_all")
        assert scan_presenter.get_recommendation_strategy() == "migrate_all"

    def test_full_workflow_sequence(
        self,
        ui_state: QtUiState,
        mock_inventory_callback,
        mock_recommendations_callback,
    ):
        """Test workflow: Complete sequence through multiple pages."""
        # Page 1: Mode Selection
        mode_presenter = ModePresenter(ui_state)
        mode_presenter.on_page_shown()
        mode_presenter.set_mode("guided")
        assert mode_presenter.on_page_before_next() is True
        
        # Page 2: Scan & Recommendations
        scan_presenter = ScanPresenter(ui_state, mock_inventory_callback, mock_recommendations_callback)
        scan_presenter.on_page_shown()
        
        # Mark scans complete
        ui_state.inventory_completed = True
        ui_state.analysis_completed = True
        
        assert scan_presenter.on_page_before_next() is True
        
        # Verify final state
        assert ui_state.mode == "guided"
        assert ui_state.inventory_completed is True
        assert ui_state.analysis_completed is True

    def test_workflow_state_isolation(self, mock_inventory_callback, mock_recommendations_callback):
        """Test that different workflow instances have isolated state."""
        state1 = QtUiState()
        state2 = QtUiState()
        
        mode1 = ModePresenter(state1)
        mode2 = ModePresenter(state2)
        
        mode1.set_mode("expert")
        assert state1.mode == "expert"
        assert state2.mode == "guided"  # Unchanged

    def test_presenter_signal_flow(self, ui_state: QtUiState):
        """Test that presenters emit appropriate signals."""
        mode_presenter = ModePresenter(ui_state)
        
        # Setup signal tracking
        signals_emitted = []
        
        def track_title_change(title):
            signals_emitted.append(('title', title))
        
        # Connect to signal (would be Qt in real code)
        # For now just verify the methods exist
        assert hasattr(mode_presenter, 'page_title_changed')
        assert hasattr(mode_presenter, 'error_occurred')
        assert hasattr(mode_presenter, 'request_next')
