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
    EXEC_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "data"
    RESTORE_DIR = DATA_DIR / "restore"
    LOGS_DIR = BASE_DIR / "logs"

# The pre-built Linux binary can reach the .exe two ways: baked in at
# PyInstaller build time via `datas` (MigrationWizard.spec does this
# automatically if it already exists at build time — true single-file
# standalone, but means the Linux binary must be built BEFORE the Windows
# .exe), or dropped into a folder next to the built .exe afterwards, no
# rebuild needed. Both are checked at lookup time so neither order is
# required — see resolve_linux_build_binary().
_LINUX_BUILD_CANDIDATES = (
    BASE_DIR / "assets" / "linux_build" / "MigrationWizard",
    EXEC_DIR / "assets" / "linux_build" / "MigrationWizard",
)


def resolve_linux_build_binary() -> Path | None:
    """Return the pre-built Linux binary's path if found, else None."""
    for candidate in _LINUX_BUILD_CANDIDATES:
        if candidate.exists():
            return candidate
    return None

CONFIG_DIR = BASE_DIR / "configs"

RESTORE_REPORT = RESTORE_DIR / "restore_report.json"
EXTRACTED_BACKUP_DIR = RESTORE_DIR / "extracted_backup"

REPORTS_DIR = BASE_DIR / "docs" / "reports"
FINAL_REPORT_JSON = REPORTS_DIR / "final_report.json"
FINAL_REPORT_MARKDOWN = REPORTS_DIR / "final_report.md"
FINAL_REPORT_HTML = REPORTS_DIR / "final_report.html"

