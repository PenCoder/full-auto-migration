"""Validation helpers for restore outputs and migration evidence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.constants import RESTORE_DIR, RESTORE_REPORT
from src.orchestration.errors import ERR_VALIDATION_INPUT, MigrationError


def _format_size(num_bytes: int) -> str:
    """Format a byte count using human-friendly units."""
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def validate_restore_report(report_path: Path = RESTORE_REPORT) -> dict[str, Any]:
    """Validate a restore report and produce a detailed validation summary."""
    if not report_path.exists():
        raise MigrationError(ERR_VALIDATION_INPUT, f"Missing restore report: {report_path}")

    with report_path.open(encoding="utf-8") as f:
        report = json.load(f)

    validated_at = datetime.now(timezone.utc).isoformat()

    files = report.get("files_restored", [])
    apps = report.get("applications_installed", [])

    restored_count = 0
    restored_bytes = 0
    hash_verified_count = 0
    hash_failed_count = 0
    failed_files: list[dict[str, Any]] = []
    missing_files: list[dict[str, Any]] = []

    for item in files:
        dest = item.get("destination", "")
        rel_path = item.get("relative_path", dest)
        path = Path(dest) if dest else None

        if path and path.exists() and path.is_file():
            restored_count += 1
            try:
                restored_bytes += path.stat().st_size
            except OSError:
                pass
        elif dest:
            missing_files.append(
                {
                    "relative_path": rel_path,
                    "expected_destination": dest,
                    "source": item.get("source", ""),
                }
            )

        status = (item.get("verification_status") or "").lower()
        if status == "match":
            hash_verified_count += 1
        elif status == "mismatch":
            hash_failed_count += 1
            failed_files.append(
                {
                    "relative_path": rel_path,
                    "destination": dest,
                    "expected_hash": item.get("source_hash", ""),
                    "actual_hash": item.get("dest_hash", ""),
                }
            )

    total_files = len(files)
    integrity_score = int((restored_count / total_files) * 100) if total_files else 100
    openness_bonus = 15 if apps else 5
    total_score = min(100, integrity_score + openness_bonus)

    summary: dict[str, Any] = {
        "validated_at": validated_at,
        "restore_started_at": report.get("started_at", ""),
        "restore_completed_at": report.get("completed_at", ""),
        "report_path": str(report_path),
        "total_files": total_files,
        "restored_files": restored_count,
        "missing_files_count": len(missing_files),
        "hash_verified_files": hash_verified_count,
        "hash_failed_files": hash_failed_count,
        "apps_mapped": len(apps),
        "restored_data_size": _format_size(restored_bytes),
        "total_sovereignty_score": total_score,
        "failed_files": failed_files,
        "missing_files": missing_files,
    }

    validation_path = RESTORE_DIR / "validation_report.json"
    validation_path.parent.mkdir(parents=True, exist_ok=True)
    with validation_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    summary["validation_report_path"] = str(validation_path)
    return summary
