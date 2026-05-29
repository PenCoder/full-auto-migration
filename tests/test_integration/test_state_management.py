"""Integration tests for state management."""

import pytest
from src.qt_ui.state import QtUiState


class TestStateManagement:
    """Test suite for state management."""

    def test_state_initialization(self):
        """Test that state initializes with correct defaults."""
        state = QtUiState()
        
        assert state.mode == "guided"
        assert state.expert_panel_visible is False
        assert state.target_distro == "Linux Mint"
        assert state.data_strategy == "keep_all"
        assert state.recommendation_strategy == "migrate_all"
        assert state.inventory_completed is False
        assert state.analysis_completed is False

    def test_state_mutation(self):
        """Test that state can be mutated."""
        state = QtUiState()
        
        state.mode = "expert"
        assert state.mode == "expert"
        
        state.inventory_completed = True
        assert state.inventory_completed is True

    def test_selected_folders_default(self):
        """Test that selected folders have defaults."""
        state = QtUiState()
        
        assert "Documents" in state.selected_folders
        assert "Desktop" in state.selected_folders
        assert state.selected_folders["Documents"] is True

    def test_advanced_operations_default(self):
        """Test that advanced operations have defaults."""
        state = QtUiState()
        
        assert "incremental_backup" in state.advanced_operations
        assert state.advanced_operations["incremental_backup"] is True

    def test_state_isolation(self):
        """Test that state instances are isolated."""
        state1 = QtUiState()
        state2 = QtUiState()
        
        state1.mode = "expert"
        assert state2.mode == "guided"
        
        # Modify a mutable field
        state1.selected_folders["Documents"] = False
        assert state2.selected_folders["Documents"] is True

    def test_custom_paths_management(self):
        """Test custom paths list management."""
        state = QtUiState()
        
        assert state.custom_paths == []
        state.custom_paths.append("/custom/path")
        assert len(state.custom_paths) == 1
        assert state.custom_paths[0] == "/custom/path"

    def test_error_tracking(self):
        """Test error message tracking."""
        state = QtUiState()
        
        assert state.last_error == ""
        state.last_error = "Test error"
        assert state.last_error == "Test error"

    def test_score_tracking(self):
        """Test score tracking."""
        state = QtUiState()
        
        assert state.total_sovereignty_score == 0
        state.total_sovereignty_score = 85
        assert state.total_sovereignty_score == 85

    def test_state_fields_are_mutable(self):
        """Test that all state fields can be modified."""
        state = QtUiState()
        
        # Test string fields
        state.mode = "balanced"
        state.target_distro = "Ubuntu"
        
        # Test boolean fields
        state.inventory_completed = True
        state.analysis_completed = True
        
        # Test dict fields
        state.selected_folders["Downloads"] = False
        
        # All should change without errors
        assert state.mode == "balanced"
        assert state.inventory_completed is True
        assert state.selected_folders["Downloads"] is False
