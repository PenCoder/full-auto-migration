"""Exception hierarchy for the migration framework."""

from __future__ import annotations


class MigrationException(Exception):
    """Base exception for all migration-related errors."""

    def __init__(self, message: str, error_code: str | None = None, details: dict | None = None):
        """Initialize migration exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "UNKNOWN_ERROR"
        self.details = details or {}


class InventoryException(MigrationException):
    """Raised when inventory collection fails."""
    pass


class AnalysisException(MigrationException):
    """Raised when analysis fails."""
    pass


class RecommendationException(MigrationException):
    """Raised when recommendation generation fails."""
    pass


class BackupException(MigrationException):
    """Raised when backup creation fails."""
    pass


class RestoreException(MigrationException):
    """Raised when restore operation fails."""
    pass


class ValidationException(MigrationException):
    """Raised when validation fails."""
    pass


class ConfigurationException(MigrationException):
    """Raised when configuration is invalid."""
    pass


class WorkflowException(MigrationException):
    """Raised when workflow execution fails."""
    pass


class StateException(MigrationException):
    """Raised when state operation fails."""
    pass


class ServiceException(MigrationException):
    """Raised when service operation fails."""
    pass
