"""Shared filesystem paths used across the migration application."""

import sys
from pathlib import Path


if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # If the application is run as a bundle, the PyInstaller bootloader
    BASE_DIR = Path(sys._MEIPASS) #.resolve().parent
    EXEC_DIR = Path(sys.executable).resolve().parent
    DATA_DIR = EXEC_DIR / "data"
    RESTORE_DIR = DATA_DIR / "restore"
    LOGS_DIR = EXEC_DIR / "logs"
else:
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    RESTORE_DIR = DATA_DIR / "restore"
    LOGS_DIR = BASE_DIR / "logs"

CONFIG_DIR = BASE_DIR / "configs"

RESTORE_REPORT = RESTORE_DIR / "restore_report.json"
EXTRACTED_BACKUP_DIR = RESTORE_DIR / "extracted_backup"

