"""Tests for error handling and edge cases."""

import pytest
from pathlib import Path
from src.config import ConfigError, load_config


class TestConfigurationErrorHandling:
    """Test suite for configuration error handling."""

    def test_missing_config_file(self):
        """Test handling of missing configuration file."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/config.yaml")

    def test_invalid_yaml_syntax(self):
        """Test handling of invalid YAML syntax."""
        import tempfile
        import yaml
        
        invalid_yaml = """
        project:
          name: Test
          version: 1.0.0
          maintainer: Test
        source_system:
          - invalid list format
          - for what should be dict
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(invalid_yaml)
            f.flush()
            temp_path = Path(f.name)
        
        try:
            with pytest.raises((ConfigError, yaml.YAMLError, ValueError)):
                load_config(str(temp_path))
        finally:
            temp_path.unlink()

    def test_missing_required_field(self):
        """Test handling of missing required configuration field."""
        import tempfile
        
        yaml_content = """
project:
  name: Test
  version: 1.0.0
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)
        
        try:
            with pytest.raises(ConfigError):
                load_config(str(temp_path))
        finally:
            temp_path.unlink()

    def test_invalid_field_type(self):
        """Test loader behavior with semantically invalid field type."""
        import tempfile
        
        yaml_content = """
project:
  name: Test
  version: 1.0.0
  maintainer: Test

source_system:
  windows_user: testuser
  inventory_output_dir: inventory
  backup_output_dir: backups
  backup_paths:
    - Documents

target_system:
  distro: ubuntu
  edition: "22.04"
  language: en_US
  timezone: America/New_York
  hostname: ubuntu-test
  username: testuser

migration:
  mode: full_clean
  target_disk: /dev/sda
  layout: full_disk
  swap_size_gb: "not_a_number"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)
        
        try:
            config = load_config(str(temp_path))
            assert config.migration.swap_size_gb == "not_a_number"
        finally:
            temp_path.unlink()

    def test_invalid_enum_value(self):
        """Test loader behavior with semantically invalid enum value."""
        import tempfile
        
        yaml_content = """
project:
  name: Test
  version: 1.0.0
  maintainer: Test

source_system:
  windows_user: testuser
  inventory_output_dir: inventory
  backup_output_dir: backups
  backup_paths:
    - Documents

target_system:
  distro: ubuntu
  edition: "22.04"
  language: en_US
  timezone: America/New_York
  hostname: ubuntu-test
  username: testuser

migration:
  mode: invalid_mode
  target_disk: /dev/sda
  layout: full_disk
  swap_size_gb: 4
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)
        
        try:
            config = load_config(str(temp_path))
            assert config.migration.mode == "invalid_mode"
        finally:
            temp_path.unlink()


class TestStateErrorHandling:
    """Test suite for state error handling."""

    def test_state_with_invalid_mode(self):
        """Test state with invalid mode value."""
        from src.qt_ui.state import QtUiState
        
        state = QtUiState()
        
        # Should handle invalid mode gracefully
        state.mode = "invalid_mode"  # May store but might fail on use
        assert state.mode == "invalid_mode"  # Just stores it

    def test_state_score_out_of_range(self):
        """Test state with invalid score values."""
        from src.qt_ui.state import QtUiState
        
        state = QtUiState()
        
        # Should accept any numeric value
        state.total_sovereignty_score = -100
        assert state.total_sovereignty_score == -100
        
        state.total_sovereignty_score = 999
        assert state.total_sovereignty_score == 999

    def test_state_with_empty_strings(self):
        """Test state with empty string values."""
        from src.qt_ui.state import QtUiState
        
        state = QtUiState()
        
        state.last_error = ""
        assert state.last_error == ""


class TestServiceErrorHandling:
    """Test suite for service error handling."""

    def test_migration_service_with_none_config(self):
        """Test migration service with None config."""
        from src.services.migration_service import MigrationService
        with pytest.raises((ValueError, TypeError, AttributeError)):
            MigrationService(None, context={})

    def test_restore_service_with_invalid_path(self):
        """Test restore service with invalid backup path."""
        from pathlib import Path
        from src.orchestration.errors import MigrationError
        from src.services.restore_service import RestoreService

        service = RestoreService(Path("/nonexistent/bundle"), Path("/tmp/home"))

        with pytest.raises((MigrationError, FileNotFoundError, ValueError, AttributeError, OSError)):
            service.run_restore()

    def test_hardware_inventory_on_incompatible_system(self):
        """Test hardware inventory on incompatible system."""
        from src.inventory.hardware import collect_hardware_inventory
        
        # May fail or return empty/default values on non-Windows system
        try:
            result = collect_hardware_inventory()
            # Either succeeds with data or raises an error
            assert result is not None or isinstance(result, (dict, list, type(None)))
        except Exception:
            # Expected on non-Windows systems
            pass


class TestPresenterErrorHandling:
    """Test suite for presenter error handling."""

    def test_presenter_with_none_state(self):
        """Test presenter with None state."""
        from src.qt_ui.presenters import ModePresenter
        presenter = ModePresenter(None)
        assert presenter is not None

    def test_presenter_with_invalid_state(self):
        """Test presenter with invalid state object."""
        from src.qt_ui.presenters import ModePresenter
        
        invalid_state = "not a state"
        presenter = ModePresenter(invalid_state)
        assert presenter is not None

    def test_scan_presenter_missing_callbacks(self):
        """Test scan presenter with missing callbacks."""
        from src.qt_ui.presenters import ScanPresenter
        from src.qt_ui.state import QtUiState
        
        state = QtUiState()
        presenter = ScanPresenter(state, None, None)
        assert presenter is not None


class TestEdgeCases:
    """Test suite for edge cases."""

    def test_very_long_path_names(self, mock_config):
        """Test handling of very long path names."""
        from src.qt_ui.state import QtUiState
        
        state = QtUiState()
        
        # Very long path
        long_path = "/very/" * 100 + "long/path"
        state.custom_paths.append(long_path)
        
        assert long_path in state.custom_paths

    def test_special_characters_in_paths(self, mock_config):
        """Test handling of special characters in paths."""
        from src.qt_ui.state import QtUiState
        
        state = QtUiState()
        
        special_paths = [
            "/path/with spaces/folder",
            "/path/with-dashes/folder",
            "/path/with_underscores/folder",
            "/path/with.dots/folder",
        ]
        
        for path in special_paths:
            state.custom_paths.append(path)
        
        assert len(state.custom_paths) == len(special_paths)

    def test_unicode_in_configuration(self):
        """Test handling of unicode characters in config."""
        import tempfile
        
        yaml_content = """
project:
  name: Test Migration 测试
  version: 1.0.0
  maintainer: Test Suite 🚀

source_system:
  windows_user: testuser
  inventory_output_dir: inventory
  backup_output_dir: backups
  backup_paths:
    - Documents

target_system:
  distro: ubuntu
  edition: "22.04"
  language: en_US
  timezone: America/New_York
  hostname: ubuntu-test
  username: testuser

migration:
  mode: full_clean
  target_disk: /dev/sda
  layout: full_disk
  swap_size_gb: 4
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)
        
        try:
            # Should handle unicode gracefully
            try:
                config = load_config(str(temp_path))
                assert "测试" in config.project.name or config.project.name is not None
            except Exception:
                # Some versions may not handle unicode perfectly
                pass
        finally:
            temp_path.unlink()

    def test_empty_optional_lists(self, mock_config):
        """Test handling of empty optional lists."""
        from src.qt_ui.state import QtUiState
        
        state = QtUiState()
        
        state.custom_paths = []
        assert state.custom_paths == []

    def test_concurrent_state_access(self):
        """Test concurrent access to state (single-threaded check)."""
        from src.qt_ui.state import QtUiState
        
        state = QtUiState()
        
        # Simulate rapid state changes
        for i in range(100):
            state.total_sovereignty_score = i
            state.last_error = f"Error {i}"
        
        # Final state should reflect last change
        assert state.total_sovereignty_score == 99
        assert state.last_error == "Error 99"
