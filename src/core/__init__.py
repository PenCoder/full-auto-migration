"""Core module providing application state management, service interfaces, and workflow orchestration."""

from __future__ import annotations

from src.core.state import MigrationState, ActivityEntry, MigrationPhase, ActivityLevel
from src.core.interfaces import (
    InventoryService,
    AnalysisService,
    BackupService,
    RecommendationService as RecommendationServiceInterface,
    ReportService as ReportServiceInterface,
    RestoreService as RestoreServiceInterface,
    TaskRunner,
    StateObserver,
)
from src.core.workflow import WorkflowOrchestrator
from src.core.exceptions import (
    MigrationException,
    InventoryException,
    AnalysisException,
    RecommendationException,
    BackupException,
    RestoreException,
    ValidationException,
    ConfigurationException,
    WorkflowException,
    StateException,
    ServiceException,
)

__all__ = [
    # State Management
    "MigrationState",
    "ActivityEntry",
    "MigrationPhase",
    "ActivityLevel",
    # Service Contracts
    "InventoryService",
    "AnalysisService",
    "BackupService",
    "RecommendationServiceInterface",
    "ReportServiceInterface",
    "RestoreServiceInterface",
    "TaskRunner",
    "StateObserver",
    # Orchestration
    "WorkflowOrchestrator",
    # Exceptions
    "MigrationException",
    "InventoryException",
    "AnalysisException",
    "RecommendationException",
    "BackupException",
    "RestoreException",
    "ValidationException",
    "ConfigurationException",
    "WorkflowException",
    "StateException",
    "ServiceException",
]
