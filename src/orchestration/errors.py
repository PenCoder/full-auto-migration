"""Structured error codes and user-facing recovery hints."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ErrorCode:
    """Immutable error metadata used by orchestration and services."""
    code: str
    message: str


ERR_INVALID_CONFIG = ErrorCode("E_CFG_001", "Invalid configuration")
ERR_CHECKPOINT_IO = ErrorCode("E_CKP_001", "Checkpoint storage failure")
ERR_BACKUP_FAILED = ErrorCode("E_BKP_001", "Backup generation failed")
ERR_MISSING_BUNDLE = ErrorCode("E_RST_001", "Backup bundle is incomplete")
ERR_ARCHIVE_UNSAFE_PATH = ErrorCode("E_RST_002", "Unsafe archive path detected")
ERR_HASH_MISMATCH = ErrorCode("E_RST_003", "File hash mismatch detected")
ERR_PACKAGE_INSTALL = ErrorCode("E_PKG_001", "Package installation failed")
ERR_UNSUPPORTED_PM = ErrorCode("E_PKG_002", "Unsupported package manager")
ERR_VALIDATION_INPUT = ErrorCode("E_VAL_001", "Validation input is missing or invalid")


ERROR_HINTS = {
    "E_CFG_001": "Check migration.config.yaml and ensure required fields are valid.",
    "E_CKP_001": "Verify write permissions for the checkpoint directory and try again.",
    "E_BKP_001": "Check selected backup paths, permissions, and available disk space.",
    "E_RST_001": "Ensure manifest.json and backup.zip exist in the selected bundle folder.",
    "E_RST_002": "Backup archive appears unsafe. Regenerate backup bundle and retry restore.",
    "E_RST_003": "Some files failed integrity checks. Re-run restore or regenerate backup bundle.",
    "E_PKG_001": "Package installation failed. Check internet access and package manager privileges.",
    "E_PKG_002": "No supported package manager detected. Choose a supported Linux distribution.",
    "E_VAL_001": "Run restore first and make sure restore_report.json exists.",
}


def extract_error_code(message: str) -> str | None:
    """Extract an application error code from a free-form message."""
    match = re.search(r"\b(E_[A-Z]{3}_[0-9]{3})\b", message or "")
    if not match:
        return None
    return match.group(1)


def recovery_hint(message: str) -> str:
    """Return a recovery hint for a message or error code."""
    code = extract_error_code(message)
    if not code:
        return "Review logs, verify inputs, and retry the operation."
    return ERROR_HINTS.get(code, "Review logs and retry the operation.")


def user_facing_error(message: str) -> str:
    """Format an error message with a recovery suggestion."""
    code = extract_error_code(message)
    hint = recovery_hint(message)
    if code:
        return f"{message}\nRecovery: {hint}"
    return f"{message}\nRecovery: {hint}"


class MigrationError(RuntimeError):
    """Exception raised when a migration step fails with a known error code."""

    def __init__(self, error: ErrorCode, details: str = "") -> None:
        """Build a readable exception message from a structured error code."""
        self.error = error
        self.details = details
        message = f"{error.code}: {error.message}"
        if details:
            message = f"{message} ({details})"
        super().__init__(message)
