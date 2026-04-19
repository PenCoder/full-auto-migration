from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.constants import BASE_DIR, DATA_DIR, RESTORE_DIR
from src.loggers import get_logger


class ReportService:
    def __init__(self, report_dir: Path | None = None) -> None:
        self.logger = get_logger("report_service")
        self.report_dir = report_dir or (BASE_DIR / "docs" / "reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def load_validation_summary(self) -> dict[str, Any]:
        summary_path = RESTORE_DIR / "validation_report.json"
        if not summary_path.exists():
            raise FileNotFoundError(f"Validation summary not found: {summary_path}")
        return json.loads(summary_path.read_text(encoding="utf-8"))

    def generate_report(self) -> dict[str, Any]:
        validation = self.load_validation_summary()
        restore_report_path = RESTORE_DIR / "restore_report.json"
        restore_report = {}
        if restore_report_path.exists():
            restore_report = json.loads(restore_report_path.read_text(encoding="utf-8"))

        generated_at = datetime.now(timezone.utc).isoformat()
        report_json = {
            "generated_at": generated_at,
            "validation": validation,
            "restore_report_path": str(restore_report_path),
            "validation_report_path": str(RESTORE_DIR / "validation_report.json"),
            "summary": self._build_summary(validation),
        }

        json_path = self.report_dir / "final_report.json"
        markdown_path = self.report_dir / "final_report.md"
        html_path = self.report_dir / "final_report.html"

        json_path.write_text(json.dumps(report_json, indent=2), encoding="utf-8")
        markdown_path.write_text(self._build_markdown(report_json, restore_report), encoding="utf-8")
        html_path.write_text(self._build_html(report_json, restore_report), encoding="utf-8")

        self.logger.info("Final report written to %s", markdown_path)
        return {
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
            "html_path": str(html_path),
            "report": report_json,
        }

    def _build_summary(self, validation: dict[str, Any]) -> dict[str, Any]:
        score = int(validation.get("total_sovereignty_score", 0))
        integrity = int(validation.get("hash_verified_files", 0))
        failed = int(validation.get("hash_failed_files", 0))
        files = int(validation.get("total_files", 0))
        rating = "Excellent" if score >= 90 else "Strong" if score >= 75 else "Needs Review"
        return {
            "score": score,
            "integrity_verified": integrity,
            "integrity_failed": failed,
            "files": files,
            "rating": rating,
        }

    def _build_markdown(self, report: dict[str, Any], restore_report: dict[str, Any]) -> str:
        validation = report["validation"]
        summary = report["summary"]
        lines = [
            "# Final Migration Report",
            "",
            f"Generated at: {report['generated_at']}",
            "",
            "## Executive Summary",
            f"- Sovereignty score: {summary['score']}%",
            f"- Rating: {summary['rating']}",
            f"- Files restored: {validation.get('restored_files', 0)} / {validation.get('total_files', 0)}",
            f"- Hash verified files: {validation.get('hash_verified_files', 0)}",
            f"- Hash failed files: {validation.get('hash_failed_files', 0)}",
            f"- Applications mapped: {validation.get('apps_mapped', 0)}",
            "",
            "## Validation Evidence",
            f"- Validation report: {report['validation_report_path']}",
            f"- Restore report: {report['restore_report_path']}",
            f"- Restored data size: {validation.get('restored_data_size', '0 B')}",
            "",
            "## Restore Details",
        ]

        files = restore_report.get("files_restored", [])
        if files:
            for item in files[:25]:
                lines.append(
                    f"- {item.get('relative_path', 'unknown')} -> {item.get('verification_status', 'unknown')}"
                )
        else:
            lines.append("- No file restoration entries available.")

        lines.extend([
            "",
            "## Recommendations",
            "- Review any failed integrity checks before redistribution.",
            "- Retain the final_report.json and validation_report.json as evidence.",
            "- Archive the report bundle with the project submission.",
            "",
        ])
        return "\n".join(lines)

    def _build_html(self, report: dict[str, Any], restore_report: dict[str, Any]) -> str:
        validation = report["validation"]
        summary = report["summary"]
        items = []
        for item in restore_report.get("files_restored", [])[:25]:
            items.append(
                f"<li><strong>{item.get('relative_path', 'unknown')}</strong> - {item.get('verification_status', 'unknown')}</li>"
            )
        items_html = "".join(items) if items else "<li>No restoration entries available.</li>"
        return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <title>Final Migration Report</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; margin: 32px; color: #1b2e38; background: #f7fbfe; }}
    .card {{ background: white; border: 1px solid #c3d6e0; border-radius: 16px; padding: 24px; margin-bottom: 20px; }}
    .score {{ font-size: 54px; font-weight: 800; color: #1e6b46; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(220px, 1fr)); gap: 14px; }}
    .metric {{ background: #eef7fb; border: 1px solid #bfd6e2; border-radius: 12px; padding: 12px; }}
    h1, h2 {{ margin-top: 0; }}
  </style>
</head>
<body>
  <div class=\"card\">
    <h1>Final Migration Report</h1>
    <p>Generated at {report['generated_at']}</p>
    <div class=\"score\">{summary['score']}%</div>
    <p>{summary['rating']} final rating</p>
  </div>
  <div class=\"card\">
    <h2>Key Metrics</h2>
    <div class=\"grid\">
      <div class=\"metric\">Files restored: {validation.get('restored_files', 0)} / {validation.get('total_files', 0)}</div>
      <div class=\"metric\">Hash verified: {validation.get('hash_verified_files', 0)}</div>
      <div class=\"metric\">Hash failed: {validation.get('hash_failed_files', 0)}</div>
      <div class=\"metric\">Applications mapped: {validation.get('apps_mapped', 0)}</div>
    </div>
  </div>
  <div class=\"card\">
    <h2>Restore Evidence</h2>
    <ul>{items_html}</ul>
  </div>
</body>
</html>"""
