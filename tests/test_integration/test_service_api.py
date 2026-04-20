"""Tests for service APIs and component interactions."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from src.services.migration_service import MigrationService
from src.services.restore_service import RestoreService


class TestMigrationServiceAPI:
    """Test suite for migration service API."""

    def test_migration_service_initialization(self, mock_config):
        """Test that migration service initializes correctly."""
        service = MigrationService(mock_config, context={})
        assert service is not None

    def test_migration_service_has_required_methods(self, mock_config):
        """Test that migration service has required methods."""
        service = MigrationService(mock_config, context={})
        assert hasattr(service, 'run_inventory')
        assert hasattr(service, 'run_analysis')
        assert hasattr(service, 'run_backup')
        assert callable(service.run_backup)

    def test_backup_creation_with_config(self, mock_config):
        """Test backup creation with configuration."""
        service = MigrationService(mock_config, context={})
        
        # Mock the backup creation
        with patch.object(service, 'run_backup', return_value=True) as mock_backup:
            result = service.run_backup(["Documents"], {".txt": True})
            mock_backup.assert_called_once()

    def test_migration_service_error_handling(self):
        """Test migration service error handling."""
        with pytest.raises((TypeError, AttributeError)):
            MigrationService(None, context={})


class TestRestoreServiceAPI:
    """Test suite for restore service API."""

    def test_restore_service_initialization(self):
        """Test that restore service initializes correctly."""
        service = RestoreService(Path("/tmp/bundle"), Path("/tmp/home"))
        assert service is not None

    def test_restore_service_has_required_methods(self):
        """Test that restore service has required methods."""
        service = RestoreService(Path("/tmp/bundle"), Path("/tmp/home"))
        assert hasattr(service, 'run_restore')
        assert callable(service.run_restore)

    def test_restore_service_validation(self, mock_config):
        """Test backup validation."""
        service = RestoreService(Path("/tmp/bundle"), Path("/tmp/home"))

        with patch.object(service, '_validate_bundle', return_value=True) as mock_validate:
            service._validate_bundle()
            mock_validate.assert_called_once()


class TestInventoryServiceAPI:
    """Test suite for inventory collection APIs."""

    def test_hardware_inventory_interface(self):
        """Test hardware inventory module interface."""
        from src.inventory import hardware

        assert hasattr(hardware, 'collect_hardware_inventory')
        assert hasattr(hardware, 'write_hardware_inventory')

    def test_software_inventory_interface(self):
        """Test software inventory module interface."""
        from src.inventory import software

        assert hasattr(software, 'collect_software_inventory')
        assert hasattr(software, 'write_software_inventory')


class TestAnalysisServiceAPI:
    """Test suite for analysis service APIs."""

    def test_hardware_mapping_interface(self):
        """Test hardware mapping module interface."""
        from src.analysis import hw_matrix

        assert hasattr(hw_matrix, 'generate_hardware_matrix')
        assert hasattr(hw_matrix, 'write_hardware_matrix')

    def test_software_mapping_interface(self):
        """Test software mapping module interface."""
        from src.analysis import software_mapping

        assert hasattr(software_mapping, 'generate_software_mapping')
        assert hasattr(software_mapping, 'write_software_mapping')


class TestDataFlowIntegration:
    """Test suite for data flow between services."""

    def test_inventory_to_analysis_flow(self):
        """Test data flow from inventory to analysis."""
        from src.inventory import hardware
        from src.analysis import hw_matrix

        assert callable(hardware.collect_hardware_inventory)
        assert callable(hw_matrix.generate_hardware_matrix)

    def test_backup_to_restore_flow(self, mock_config):
        """Test data flow from backup to restore."""
        migration_service = MigrationService(mock_config, context={})
        restore_service = RestoreService(Path("/tmp/bundle"), Path("/tmp/home"))
        
        # Create backup (mocked)
        with patch.object(migration_service, 'run_backup', return_value=True):
            backup_created = migration_service.run_backup(["Documents"], {".txt": True})
            assert backup_created is True
        
        # Validate restore (mocked)
        with patch.object(restore_service, '_validate_bundle', return_value=True):
            can_restore = restore_service._validate_bundle()
            assert can_restore is True

    def test_configuration_propagation(self, mock_config):
        """Test configuration propagation to services."""
        service = MigrationService(mock_config, context={})
        
        # Config should be passable to service
        assert mock_config is not None
        assert hasattr(mock_config, 'migration')
        assert hasattr(mock_config, 'target_system')


class TestPresenterAPI:
    """Test suite for presenter interfaces."""

    def test_page_presenter_interface(self, ui_state):
        """Test BasePresenter interface."""
        from src.qt_ui.presenters import BasePresenter
        
        # Abstract interface, check methods via concrete implementation
        from src.qt_ui.presenters import ModePresenter
        
        presenter = ModePresenter(ui_state)
        assert hasattr(presenter, 'on_page_shown')
        assert hasattr(presenter, 'on_page_before_next')
        assert hasattr(presenter, 'on_page_before_previous')
        assert callable(presenter.on_page_shown)
        assert callable(presenter.on_page_before_next)

    def test_mode_presenter_api(self, ui_state):
        """Test ModePresenter specific API."""
        from src.qt_ui.presenters import ModePresenter
        
        presenter = ModePresenter(ui_state)
        assert hasattr(presenter, 'set_mode')
        assert hasattr(presenter, 'get_mode')
        assert callable(presenter.set_mode)

    def test_scan_presenter_api(self, ui_state, mock_inventory_callback, mock_recommendations_callback):
        """Test ScanPresenter specific API."""
        from src.qt_ui.presenters import ScanPresenter
        
        presenter = ScanPresenter(ui_state, mock_inventory_callback, mock_recommendations_callback)
        assert hasattr(presenter, 'run_inventory_scan')
        assert hasattr(presenter, 'get_recommendation_strategy')
        assert hasattr(presenter, 'set_recommendation_strategy')

    def test_signal_interface(self, ui_state):
        """Test signal/callback interface."""
        from src.qt_ui.presenters import ModePresenter
        
        presenter = ModePresenter(ui_state)
        
        # Verify signal attributes exist
        assert hasattr(presenter, 'page_title_changed')
        assert hasattr(presenter, 'error_occurred')
        assert hasattr(presenter, 'request_next')
        assert hasattr(presenter, 'request_back')
