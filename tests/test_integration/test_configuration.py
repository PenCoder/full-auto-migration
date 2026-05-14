"""Tests for configuration loading and validation."""

import pytest
import tempfile
from pathlib import Path
from src.config import load_config, load_default_config, ConfigError, MigrationConfigRoot


class TestConfigurationLoading:
    """Test suite for configuration loading."""

    def test_load_config_with_valid_yaml(self):
        """Test loading a valid YAML configuration."""
        yaml_content = """
project:
  name: Test Migration
  version: 1.0.0
  maintainer: Test Suite

source_system:
  windows_user: testuser
  inventory_output_dir: inventory
  backup_output_dir: backups
  backup_paths:
    - Documents
    - Desktop
  file_types:
    .pdf: true
    .docx: true
  file_type_labels:
    .pdf: PDF files
    .docx: Word document files

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

demo:
  include_dirs: Documents

automation:
  dry_run: false

validation:
  check_network: true
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)
        
        try:
            config = load_config(str(temp_path))
            assert config.project.name == "Test Migration"
            assert config.migration.mode == "full_clean"
            assert config.target_system.distro == "ubuntu"
            assert config.source_system.file_type_labels[".pdf"] == "PDF files"
        finally:
            temp_path.unlink()

    def test_load_config_missing_file(self):
        """Test that loading a missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.yaml")

    def test_load_config_missing_required_section(self):
        """Test that missing required sections raise ConfigError."""
        yaml_content = """
project:
  name: Test
  version: 1.0.0
  maintainer: Test
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

    def test_config_root_load_method(self):
        """Test MigrationConfigRoot.load() class method."""
        yaml_content = """
project:
  name: Test Migration
  version: 1.0.0
  maintainer: Test Suite

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

demo:
  include_dirs: Documents
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)
        
        try:
            config = MigrationConfigRoot.load(str(temp_path))
            assert isinstance(config, MigrationConfigRoot)
            assert config.project.name == "Test Migration"
        finally:
            temp_path.unlink()

    def test_config_with_all_optional_sections(self):
        """Test loading config with all optional sections."""
        yaml_content = """
project:
  name: Test
  version: 1.0.0
  maintainer: Test

source_system:
  windows_user: null
  inventory_output_dir: inv
  backup_output_dir: bak
  backup_paths: [.]

target_system:
  distro: ubuntu
  edition: "22.04"
  language: en_US
  timezone: UTC
  hostname: test
  username: user

migration:
  mode: full_clean
  target_disk: /dev/sda
  layout: full_disk
  swap_size_gb: 4

demo:
  include_dirs: Documents

automation:
  dry_run: true
  logging_level: DEBUG

validation:
  check_network: false

research:
  record_metrics: false

backup:
  compress: true

ai:
  enabled: false
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            temp_path = Path(f.name)
        
        try:
            config = load_config(str(temp_path))
            assert config.automation.dry_run is True
            assert config.automation.logging_level == "DEBUG"
            assert config.validation.check_network is False
            assert config.backup.compress is True
        finally:
            temp_path.unlink()

    def test_config_default_values(self):
        """Test that config fields have proper defaults."""
        from src.config.schema import AutomationConfig, ValidationConfig
        
        auto = AutomationConfig()
        assert auto.dry_run is False
        assert auto.logging_level == "INFO"
        
        val = ValidationConfig()
        assert val.check_network is True
        assert val.check_audio is True


class TestConfigStructure:
    """Test suite for configuration structure."""

    def test_migration_config_root_has_all_sections(self, mock_config):
        """Test that MigrationConfigRoot has all required sections."""
        assert hasattr(mock_config, 'project')
        assert hasattr(mock_config, 'source_system')
        assert hasattr(mock_config, 'target_system')
        assert hasattr(mock_config, 'migration')
        assert hasattr(mock_config, 'automation')
        assert hasattr(mock_config, 'validation')
        assert hasattr(mock_config, 'research')
        assert hasattr(mock_config, 'app_demo')
        assert hasattr(mock_config, 'backup')
        assert hasattr(mock_config, 'ai')

    def test_all_config_sections_are_dataclasses(self, mock_config):
        """Test that all sections are properly typed."""
        from dataclasses import is_dataclass
        
        assert is_dataclass(mock_config.project)
        assert is_dataclass(mock_config.source_system)
        assert is_dataclass(mock_config.target_system)
        assert is_dataclass(mock_config.migration)
        assert is_dataclass(mock_config.automation)
        assert is_dataclass(mock_config.validation)
        assert is_dataclass(mock_config.research)
        assert is_dataclass(mock_config.app_demo)
        assert is_dataclass(mock_config.backup)
        assert is_dataclass(mock_config.ai)
