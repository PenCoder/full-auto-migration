import threading
from src.analysis.hw_matrix import generate_hardware_matrix, write_hardware_matrix
from src.analysis.software_mapping import generate_software_mapping, write_software_mapping
from src.backup.manifest import copy_backup_files, generate_manifest, write_manifest, create_backup_archive
from src.inventory.hardware import collect_hardware_inventory, write_hardware_inventory
from src.inventory.software import collect_software_inventory, write_software_inventory
from src.loggers import get_logger

class MigrationService:
    def __init__(self, config, context):
        self.config = config
        self.context = context
        self.logger = get_logger("migration_service")

    def run_inventory(self, logger=None):
        if logger is not None:
            self.logger = logger

        # SCAN HARDWARE INVENTORY 
        self.logger.info("Starting hardware inventory scan...")
        hw = collect_hardware_inventory()
        self.logger.info("Hardware inventory scan completed.")

        self.logger.info("Writing hardware inventory to file...")
        hw_out = write_hardware_inventory(self.config, hw)
        self.logger.info("Hardware inventory written to %s", hw_out)

        # SCAN SOFTWARE INVENTORY
        self.logger.info("Starting software inventory scan...")
        sw = collect_software_inventory()
        self.logger.info("Software inventory scan completed.")

        self.logger.info("Writing software inventory to file...")
        sw_out = write_software_inventory(self.config, sw)
        self.logger.info("Software inventory written to %s", sw_out)

        return {"hardware": hw, "software": sw}

    def run_analysis(self, sw_inventory, hw_inventory, logger=None):
        if logger is not None:
            self.logger = logger
        
        # Hardware analysis
        self.logger.info("Starting hardware compatibility analysis...")
        hw_rows = generate_hardware_matrix(self.config, hw_inventory)
        self.logger.info("Hardware compatibility analysis completed.")

        self.logger.info("Writing hardware compatibility matrix to file...")
        hw_out = write_hardware_matrix(self.config, hw_rows)
        self.logger.info("Hardware compatibility matrix written to %s", hw_out)

        # Software analysis
        self.logger.info("Starting software mapping analysis...")
        entries = sw_inventory.get("entries", [])
        sw_rows = generate_software_mapping(self.config, entries)
        self.logger.info("Software mapping analysis completed.")

        self.logger.info("Writing software mapping table to file...")
        sw_out = write_software_mapping(sw_rows)
        self.logger.info("Software mapping table written to %s", sw_out)
        
        return {"hardware": hw_rows, "software": sw_rows}

    def run_backup(self, selected_folders, selected_file_types, logger=None):
        if logger is not None:  
            self.logger = logger

        self.logger.info("Starting backup manifest generation...")
        
        try:
            self.config.source_system.backup_paths = selected_folders
            self.config.source_system.file_types = selected_file_types
            manifest = generate_manifest(self.config)
            
            out_file = write_manifest(self.config, manifest)
            self.logger.info("Backup manifest written to %s", out_file)
            copy_backup_files(manifest, self.config)
            if self.config.backup.compress:
                backup_root = self.config.source_system.backup_output_dir
                archive_path = self.config.backup.archive_name
                create_backup_archive(backup_root + "/files", archive_path)
                self.logger.info("Backup archive created at: %s", archive_path)
            self.logger.info("Backup files copied successfully.")

            return manifest
        except Exception as exc:
            self.logger.exception("Backup command failed: %s", exc)
            return None

    def run_task(self, worker_fn, on_done):
        def _wrap():
            result = worker_fn()
            self.after(0, lambda: on_done(result))
        threading.Thread(target=_wrap, daemon=True).start()
