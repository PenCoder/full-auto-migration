"""Single source of truth for guided/balanced/expert mode behaviour.

Both the Qt wizard (AutomationCoordinator, OperationsController) and the CLI
`scan` command must agree on what each mode does. Previously each interface
independently re-implemented these same three decisions — this module is the
one place they're defined now, so the two can no longer silently drift apart
when a mode's behaviour changes.
"""
from __future__ import annotations

VALID_MODES = ("guided", "balanced", "expert")


def _validate(mode: str) -> None:
    if mode not in VALID_MODES:
        raise ValueError(f"Unknown mode {mode!r}; expected one of {VALID_MODES}")


def should_run_analysis(mode: str) -> bool:
    """Hardware/software compatibility analysis runs in balanced and expert mode."""
    _validate(mode)
    return mode in {"balanced", "expert"}


def should_run_file_recommendations(mode: str) -> bool:
    """File recommendations run in balanced and expert mode."""
    _validate(mode)
    return mode in {"balanced", "expert"}


def resolve_app_recommendation_strategy(mode: str) -> str:
    """guided/balanced -> local (offline only); expert -> online (+ Repology verification)."""
    _validate(mode)
    return "online" if mode == "expert" else "local"
