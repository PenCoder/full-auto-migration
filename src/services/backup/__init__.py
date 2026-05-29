"""Backup service implementation."""

from __future__ import annotations

from typing import Any
from src.loggers import get_logger
from src.backup.manifest import (
    generate_manifest as gen_manifest,
    write_manifest as write_manifest_file,
    copy_backup_files,
    create_backup_archive,
)


class BackupService:
    """Specialized service for backup creation and archival.
    
    Responsibilities:
    - Generate backup manifests from file selections
    - Execute file copying to backup location
    - Create compressed archives if configured
    - Persist manifest files
    - Handle backup-specific errors
    """

    def __init__(self, config: Any):
        """Initialize backup service.
        
        Args:
            config: MigrationConfigRoot configuration object
        """
        self.config = config
        self.logger = get_logger("services.backup")

    def generate_manifest(
        self,
        selected_folders: list[str],
        selected_file_types: dict[str, bool],
    ) -> dict[str, Any]:
        """Generate backup manifest from selected items.
        
        Args:
            selected_folders: List of folder paths to include
            selected_file_types: Dictionary mapping file types to inclusion flags
            
        Returns:
            Manifest dictionary describing backup contents
            
        Raises:
            Exception: If manifest generation fails
        """
        self.logger.info("Generating backup manifest with %d folders", len(selected_folders))
        try:
            # Update config with selections
            self.config.source_system.backup_paths = selected_folders
            self.config.source_system.file_types = selected_file_types
            
            # Generate manifest
            manifest = gen_manifest(self.config)
            total_files = manifest.get("total_files", 0)
            self.logger.info("Manifest generated with %d files", total_files)
            return manifest
        except Exception as exc:
            self.logger.exception("Manifest generation failed: %s", exc)
            raise

    def persist_manifest(self, manifest: dict[str, Any]) -> str:
        """Persist backup manifest to file.
        
        Args:
            manifest: Manifest dictionary to persist
            
        Returns:
            Path to the persisted manifest file
            
        Raises:
            Exception: If persistence fails
        """
        self.logger.info("Persisting backup manifest to file...")
        try:
            manifest_path = write_manifest_file(self.config, manifest)
            self.logger.info("Manifest persisted to %s", manifest_path)
            return str(manifest_path)
        except Exception as exc:
            self.logger.exception("Failed to persist manifest: %s", exc)
            raise

    def execute_backup(self, manifest: dict[str, Any]) -> dict[str, Any]:
        """Execute backup file copying based on manifest.
        
        Args:
            manifest: Backup manifest describing what to copy
            
        Returns:
            Dictionary with backup execution results
            
        Raises:
            Exception: If backup execution fails
        """
        self.logger.info("Starting backup file copying...")
        try:
            copy_backup_files(manifest, self.config)
            self.logger.info("Backup files copied successfully")
            return {"success": True, "files_backed_up": manifest.get("total_files", 0)}
        except Exception as exc:
            self.logger.exception("Backup execution failed: %s", exc)
            raise

    def create_archive(self, backup_location: str) -> str:
        """Create compressed archive of backup files.
        
        Args:
            backup_location: Root directory of backup files
            
        Returns:
            Path to created archive
            
        Raises:
            Exception: If archiving fails
        """
        self.logger.info("Creating backup archive...")
        try:
            files_location = f"{backup_location}/files"
            archive_path = self.config.backup.archive_name
            create_backup_archive(files_location, archive_path)
            self.logger.info("Archive created at %s", archive_path)
            return archive_path
        except Exception as exc:
            self.logger.exception("Archive creation failed: %s", exc)
            raise

    def create_backup_complete(
        self,
        selected_folders: list[str],
        selected_file_types: dict[str, bool],
    ) -> dict[str, Any]:
        """Execute complete backup workflow: manifest → persistence → copy → archive.
        
        Args:
            selected_folders: List of folders to include
            selected_file_types: File types to include
            
        Returns:
            Dictionary with keys:
            - 'manifest': Generated manifest
            - 'manifest_path': Path to manifest file
            - 'backup_location': Backup directory location
            - 'archive_path': Path to archive if created
            - 'total_files': Number of files backed up
        """
        # Generate and persist manifest
        manifest = self.generate_manifest(selected_folders, selected_file_types)
        manifest_path = self.persist_manifest(manifest)
        
        # Execute backup
        backup_result = self.execute_backup(manifest)
        backup_location = self.config.source_system.backup_output_dir
        
        result = {
            "manifest": manifest,
            "manifest_path": manifest_path,
            "backup_location": backup_location,
            "total_files": backup_result.get("files_backed_up", 0),
        }
        
        # Create archive if configured
        if self.config.backup.compress:
            archive_path = self.create_archive(backup_location)
            result["archive_path"] = archive_path
        
        return result
