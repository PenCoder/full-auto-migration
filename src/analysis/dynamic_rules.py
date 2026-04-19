from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class MappingDecision:
    linux_package: str
    linux_display_name: str
    migration_strategy: str
    notes: str
    confidence_score: float
    recommendation_source: str


def _norm(value: str) -> str:
    return (value or "").strip().lower()


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def resolve_mapping(
    display_name: str,
    base_mappings: list[dict[str, str]],
    overrides: list[dict[str, str]] | None = None,
) -> MappingDecision | None:
    name = _norm(display_name)
    overrides = overrides or []

    for item in overrides:
        windows_name = _norm(item.get("windows_name", ""))
        if windows_name and (windows_name in name or name in windows_name):
            return MappingDecision(
                linux_package=item.get("linux_package", ""),
                linux_display_name=item.get("linux_display_name", item.get("linux_package", "")),
                migration_strategy=item.get("migration_strategy", "manual"),
                notes=item.get("notes", "Custom override mapping"),
                confidence_score=0.98,
                recommendation_source="user_override",
            )

    best: dict[str, str] | None = None
    best_score = 0.0
    for item in base_mappings:
        windows_name = _norm(item.get("windows_name", ""))
        if not windows_name:
            continue
        if windows_name in name:
            score = 0.95
        else:
            score = _similarity(name, windows_name)

        if score > best_score:
            best = item
            best_score = score

    if not best or best_score < 0.6:
        return None

    return MappingDecision(
        linux_package=best.get("linux_package", ""),
        linux_display_name=best.get("linux_display_name", best.get("linux_package", "")),
        migration_strategy=best.get("migration_strategy", "manual"),
        notes=best.get("notes", ""),
        confidence_score=round(best_score, 2),
        recommendation_source="dynamic_base",
    )
