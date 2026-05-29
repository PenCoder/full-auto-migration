"""Pytest configuration and shared fixtures."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.qt_ui.state import QtUiState
from src.config import MigrationConfigRoot, ProjectConfig, SourceSystemConfig, TargetSystemConfig
from src.config import MigrationConfig, AutomationConfig, ValidationConfig, ResearchConfig
from src.config import BackupConfig, AIConfig, DemoConfig


@pytest.fixture
def ui_state() -> QtUiState:
    """Create a fresh UI state for testing."""
    return QtUiState()


@pytest.fixture
def mock_config() -> MigrationConfigRoot:
    """Create a mock configuration for testing."""
    return MigrationConfigRoot(
        project=ProjectConfig(
            name="Test Migration",
            version="1.0.0",
            maintainer="Test Suite",
        ),
        source_system=SourceSystemConfig(
            windows_user="testuser",
            inventory_output_dir="test_inventory",
            backup_output_dir="test_backups",
            backup_paths=["Documents", "Desktop"],
        ),
        target_system=TargetSystemConfig(
            distro="ubuntu",
            edition="22.04",
            language="en_US",
            timezone="America/New_York",
            hostname="ubuntu-test",
            username="testuser",
        ),
        migration=MigrationConfig(
            mode="full_clean",
            target_disk="/dev/sda",
            layout="full_disk",
            swap_size_gb=4,
        ),
        automation=AutomationConfig(),
        validation=ValidationConfig(),
        research=ResearchConfig(),
        app_demo=DemoConfig(include_dirs="Documents"),
        backup=BackupConfig(),
        ai=AIConfig(),
    )


@pytest.fixture
def mock_inventory_callback():
    """Create a mock inventory callback."""
    def callback(deep_scan: bool):
        return {
            "hardware": {"cpu": "Intel i7", "ram": 16},
            "software": {"applications": ["Notepad", "Firefox"]},
            "deep_scan": deep_scan,
        }
    return MagicMock(side_effect=callback)


@pytest.fixture
def mock_recommendations_callback():
    """Create a mock recommendations callback."""
    def callback(rec_type: str, strategy: str):
        return {
            "recommendations": [
                {"windows_app": "Notepad", "linux_app": "gedit"},
                {"windows_app": "Firefox", "linux_app": "firefox"},
            ],
            "rec_type": rec_type,
            "strategy": strategy,
        }
    return MagicMock(side_effect=callback)


@pytest.fixture
def project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent


# ============================================================================
# Fixtures for Mock Services
# ============================================================================

@pytest.fixture
def mock_migration_service():
    """Create a mock migration service."""
    service = MagicMock()
    service.create_backup = MagicMock(return_value=True)
    service.validate_config = MagicMock(return_value=True)
    service.estimate_time = MagicMock(return_value=3600)  # 1 hour
    return service


@pytest.fixture
def mock_restore_service():
    """Create a mock restore service."""
    service = MagicMock()
    service.validate_backup = MagicMock(return_value=True)
    service.restore_files = MagicMock(return_value=True)
    service.verify_restore = MagicMock(return_value=True)
    return service


@pytest.fixture
def mock_inventory_service():
    """Create a mock inventory service."""
    service = MagicMock()
    service.get_hardware_info = MagicMock(return_value={
        "cpu": "Intel Core i7",
        "ram": "16GB",
        "disk": "512GB SSD"
    })
    service.get_software_info = MagicMock(return_value={
        "packages": 150,
        "applications": 30
    })
    return service


# ============================================================================
# Fixtures for Mock UI Components
# ============================================================================

@pytest.fixture
def mock_page():
    """Create a mock page widget."""
    page = MagicMock()
    page.setVisible = MagicMock()
    page.show = MagicMock()
    page.hide = MagicMock()
    return page


@pytest.fixture
def mock_presenter():
    """Create a mock presenter."""
    presenter = MagicMock()
    presenter.on_page_shown = MagicMock()
    presenter.on_page_before_next = MagicMock(return_value=True)
    presenter.on_page_before_back = MagicMock(return_value=True)
    return presenter


# ============================================================================
# Fixtures for Parametrized Tests
# ============================================================================

@pytest.fixture(params=["guided", "balanced", "expert"])
def migration_mode(request):
    """Parametrized fixture for migration modes."""
    return request.param


@pytest.fixture(params=["ubuntu", "debian", "fedora", "archlinux"])
def linux_distro(request):
    """Parametrized fixture for Linux distributions."""
    return request.param


@pytest.fixture(params=[2, 4, 8, 16, 32])
def swap_size_gb(request):
    """Parametrized fixture for swap sizes."""
    return request.param


# ============================================================================
# Fixtures for Data
# ============================================================================

@pytest.fixture
def mock_backup_manifest():
    """Create a mock backup manifest."""
    manifest = {
        "timestamp": "2024-01-15T10:30:00",
        "version": "1.0",
        "total_files": 5000,
        "total_size_gb": 50.2,
        "integrity_hash": "abc123def456",
        "source_system": {
            "os": "Windows 11",
            "user": "testuser",
            "hostname": "DESKTOP-123"
        },
        "files": [
            {
                "path": "C:\\Users\\testuser\\Documents\\file1.txt",
                "size": 1024,
                "hash": "hash1"
            }
        ]
    }
    return manifest


@pytest.fixture
def sample_inventory_data():
    """Create sample inventory data."""
    return {
        "hardware": {
            "cpu": {
                "name": "Intel Core i7-10700K",
                "cores": 8,
                "threads": 16,
            },
            "memory": {
                "total_gb": 32,
                "available_gb": 28,
            },
            "storage": {
                "disks": [
                    {
                        "name": "C:",
                        "size_gb": 476,
                        "free_gb": 156,
                    }
                ]
            }
        },
        "software": {
            "os_version": "Windows 11",
            "installed_packages": 250,
            "applications": [
                "Google Chrome",
                "Visual Studio Code",
                "Discord",
            ]
        }
    }


# ============================================================================
# Helper Classes for Assertions
# ============================================================================

class ConfigAssertions:
    """Helper class for configuration assertions."""
    
    @staticmethod
    def assert_config_valid(config):
        """Assert that config has all required sections."""
        assert hasattr(config, 'project')
        assert hasattr(config, 'source_system')
        assert hasattr(config, 'target_system')
        assert hasattr(config, 'migration')
        return True
    
    @staticmethod
    def assert_config_section(config, section_name):
        """Assert that config section exists and is valid."""
        assert hasattr(config, section_name)
        section = getattr(config, section_name)
        assert section is not None
        return True


class StateAssertions:
    """Helper class for state assertions."""
    
    @staticmethod
    def assert_valid_mode(state, mode):
        """Assert that state mode is valid."""
        valid_modes = ["guided", "balanced", "expert"]
        assert mode in valid_modes
        return True
    
    @staticmethod
    def assert_completion_flags(state):
        """Assert that completion flags are boolean."""
        assert isinstance(state.inventory_completed, bool)
        assert isinstance(state.analysis_completed, bool)
        return True


class ServiceAssertions:
    """Helper class for service assertions."""
    
    @staticmethod
    def assert_service_initialized(service):
        """Assert that service is properly initialized."""
        assert service is not None
        return True
    
    @staticmethod
    def assert_backup_manifest_valid(manifest):
        """Assert that backup manifest has required fields."""
        required_fields = ["timestamp", "version", "total_files", "total_size_gb"]
        for field in required_fields:
            assert field in manifest
        return True
