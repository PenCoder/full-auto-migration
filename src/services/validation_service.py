from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.constants import RESTORE_DIR, RESTORE_REPORT
from src.orchestration.errors import ERR_VALIDATION_INPUT, MigrationError


def _format_size(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(num_bytes)
    for unit in units:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"


def validate_restore_report(report_path: Path = RESTORE_REPORT) -> dict[str, Any]:
    if not report_path.exists():
        raise MigrationError(ERR_VALIDATION_INPUT, f"Missing restore report: {report_path}")

    with report_path.open(encoding="utf-8") as f:
        report = json.load(f)

    files = report.get("files_restored", [])
    apps = report.get("applications_installed", [])

    restored_count = 0
    restored_bytes = 0
    hash_verified_count = 0
    hash_failed_count = 0

    for item in files:
        path = Path(item.get("destination", ""))
        if path.exists() and path.is_file():
            restored_count += 1
            try:
                restored_bytes += path.stat().st_size
            except OSError:
                pass

        status = (item.get("verification_status") or "").lower()
        if status == "match":
            hash_verified_count += 1
        elif status == "mismatch":
            hash_failed_count += 1

    total_files = len(files)
    integrity_score = int((restored_count / total_files) * 100) if total_files else 100
    openness_bonus = 15 if apps else 5
    total_score = min(100, integrity_score + openness_bonus)

    summary = {
        "report_path": str(report_path),
        "total_files": total_files,
        "restored_files": restored_count,
        "hash_verified_files": hash_verified_count,
        "hash_failed_files": hash_failed_count,
        "apps_mapped": len(apps),
        "restored_data_size": _format_size(restored_bytes),
        "total_sovereignty_score": total_score,
    }

    validation_path = RESTORE_DIR / "validation_report.json"
    validation_path.parent.mkdir(parents=True, exist_ok=True)
    with validation_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    summary["validation_report_path"] = str(validation_path)
    return summary
