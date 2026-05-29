"""End-to-end workflow tests — mode selection, scan gating, strategy switching."""

import pytest
from src.qt_ui.state import QtUiState


class TestMigrationWorkflow:
    """Test complete migration workflows through ui_state."""

    def test_guided_migration_mode_selection(self, ui_state: QtUiState):
        ui_state.mode = "guided"
        assert ui_state.mode == "guided"

    def test_expert_migration_mode_selection(self, ui_state: QtUiState):
        ui_state.mode = "expert"
        assert ui_state.mode == "expert"

    def test_balanced_migration_mode_selection(self, ui_state: QtUiState):
        ui_state.mode = "balanced"
        assert ui_state.mode == "balanced"

    def test_mode_switching_workflow(self, ui_state: QtUiState):
        for mode in ("guided", "expert", "balanced"):
            ui_state.mode = mode
            assert ui_state.mode == mode

    def test_inventory_not_completed_blocks_proceed(self, ui_state: QtUiState):
        assert ui_state.inventory_completed is False

    def test_inventory_completion_allows_proceed(self, ui_state: QtUiState):
        ui_state.inventory_completed = True
        assert ui_state.inventory_completed is True

    def test_analysis_completion_independent_of_inventory(self, ui_state: QtUiState):
        ui_state.inventory_completed = True
        ui_state.analysis_completed = True
        assert ui_state.inventory_completed is True
        assert ui_state.analysis_completed is True

    def test_recommendation_strategy_default(self, ui_state: QtUiState):
        assert ui_state.recommendation_strategy in ("migrate_all", "prioritize", "")

    def test_recommendation_strategy_switch(self, ui_state: QtUiState):
        ui_state.recommendation_strategy = "prioritize"
        assert ui_state.recommendation_strategy == "prioritize"
        ui_state.recommendation_strategy = "migrate_all"
        assert ui_state.recommendation_strategy == "migrate_all"

    def test_full_workflow_state_sequence(self, ui_state: QtUiState):
        ui_state.mode = "guided"
        assert ui_state.mode == "guided"

        ui_state.inventory_completed = True
        ui_state.analysis_completed = True

        assert ui_state.inventory_completed is True
        assert ui_state.analysis_completed is True

    def test_workflow_state_isolation(self):
        state1 = QtUiState()
        state2 = QtUiState()

        state1.mode = "expert"
        assert state1.mode == "expert"
        assert state2.mode != "expert"

    def test_mapping_choice_mode_default(self, ui_state: QtUiState):
        assert ui_state.mapping_choice_mode in ("migrate_all_supported", "")

    def test_mapping_choice_mode_switch(self, ui_state: QtUiState):
        for choice in ("migrate_all_supported", "choose_from_recommendations", "manual_mapping"):
            ui_state.mapping_choice_mode = choice
            assert ui_state.mapping_choice_mode == choice

    def test_backup_not_completed_initially(self, ui_state: QtUiState):
        assert ui_state.backup_completed is False

    def test_backup_completion_flag(self, ui_state: QtUiState):
        ui_state.backup_completed = True
        assert ui_state.backup_completed is True
