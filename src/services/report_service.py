"""Final report generation for restore and validation outcomes."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.constants import DATA_DIR, REPORTS_DIR, RESTORE_DIR
from src.loggers import get_logger


class ReportService:
    """Build JSON, Markdown, and HTML report artifacts for the migration run."""

    def __init__(self, report_dir: Path | None = None) -> None:
        """Create the report service and ensure the output directory exists."""
        self.logger = get_logger("report_service")
        self.report_dir = report_dir or REPORTS_DIR
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def load_validation_summary(self) -> dict[str, Any]:
        """Load the validation summary produced by the restore workflow."""
        summary_path = RESTORE_DIR / "validation_report.json"
        if not summary_path.exists():
            raise FileNotFoundError(f"Validation summary not found: {summary_path}")
        return json.loads(summary_path.read_text(encoding="utf-8"))

    def generate_report(self, activity_log: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        """Generate the final report bundle and return the artifact paths."""
        validation = self.load_validation_summary()
        restore_report_path = RESTORE_DIR / "restore_report.json"
        restore_report: dict[str, Any] = {}
        if restore_report_path.exists():
            restore_report = json.loads(restore_report_path.read_text(encoding="utf-8"))

        generated_at = datetime.now(timezone.utc).isoformat()
        report_json = {
            "generated_at": generated_at,
            "validation": validation,
            "restore_report_path": str(restore_report_path),
            "validation_report_path": str(RESTORE_DIR / "validation_report.json"),
            "summary": self._build_summary(validation),
            "activity_log": activity_log or [],
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
        """Derive the human-readable summary metrics for the report."""
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
        """Render the final report as Markdown."""
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
            f"- Missing files: {validation.get('missing_files_count', 0)}",
            f"- Applications mapped: {validation.get('apps_mapped', 0)}",
            f"- Restored data size: {validation.get('restored_data_size', '0 B')}",
            "",
            "## Timing",
            f"- Restore started: {validation.get('restore_started_at', 'n/a')}",
            f"- Restore completed: {validation.get('restore_completed_at', 'n/a')}",
            f"- Validated at: {validation.get('validated_at', 'n/a')}",
            "",
            "## Validation Evidence",
            f"- Validation report: {report['validation_report_path']}",
            f"- Restore report: {report['restore_report_path']}",
            "",
        ]

        warnings: list[str] = restore_report.get("warnings", [])
        if warnings:
            lines += ["## Warnings — Steps That Didn't Fully Complete", ""]
            for w in warnings:
                lines.append(f"- ⚠️ {w}")
            lines.append("")

        settings_applied: list[str] = restore_report.get("settings_applied", [])
        settings_manual: list[str] = restore_report.get("settings_manual", [])
        if settings_applied or settings_manual:
            lines += ["## Settings & Configuration", ""]
            for s in settings_applied:
                lines.append(f"- ✅ {s}")
            for s in settings_manual:
                lines.append(f"- ⚠️ Needs manual setup: {s}")
            if restore_report.get("settings_guidance"):
                lines.append(f"- Full guidance written to: `{restore_report['settings_guidance']}`")
            lines.append("")

        failed_files: list[dict[str, Any]] = validation.get("failed_files", [])
        if failed_files:
            lines += ["## Hash Mismatches", ""]
            for item in failed_files:
                lines.append(f"- `{item.get('relative_path', item.get('destination', 'unknown'))}`")
                if item.get("expected_hash"):
                    lines.append(f"  - Expected: `{item['expected_hash']}`")
                if item.get("actual_hash"):
                    lines.append(f"  - Actual:   `{item['actual_hash']}`")
            lines.append("")

        missing_files: list[dict[str, Any]] = validation.get("missing_files", [])
        if missing_files:
            lines += ["## Missing Files", ""]
            for item in missing_files:
                lines.append(f"- `{item.get('relative_path', item.get('expected_destination', 'unknown'))}`")
            lines.append("")

        apps_installed: list[dict[str, Any]] = restore_report.get("applications_installed", [])
        if apps_installed:
            lines += ["## Application Map", "", "| Windows App | Linux Package | Confidence |", "|---|---|---|"]
            for app in apps_installed:
                lines.append(
                    f"| {app.get('windows_app', 'unknown')} | {app.get('linux_package', 'unknown')} "
                    f"| {app.get('mapping_confidence', '')} |"
                )
            lines.append("")

        shortcuts_restored: list[dict[str, Any]] = restore_report.get("shortcuts_restored", [])
        if shortcuts_restored:
            lines += ["## Shortcuts & Launchers", "", "| Shortcut | Category | Status |", "|---|---|---|"]
            for sc in shortcuts_restored:
                lines.append(
                    f"| {sc.get('name', 'unknown')} | {sc.get('category', '')} | {sc.get('status', '')} |"
                )
            lines.append("")

        lines += ["## Restore Details", ""]
        all_files = restore_report.get("files_restored", [])
        if all_files:
            for item in all_files:
                lines.append(
                    f"- {item.get('relative_path', 'unknown')} -> {item.get('destination', 'unknown')} "
                    f"[{item.get('verification_status', 'unknown')}]"
                )
        else:
            lines.append("- No file restoration entries available.")

        activity_log: list[dict[str, Any]] = report.get("activity_log", [])
        if activity_log:
            lines += ["", "## Activity Log", ""]
            for entry in activity_log:
                ts = entry.get("time") or entry.get("timestamp", "")
                stage = entry.get("phase") or entry.get("stage", "")
                msg = entry.get("message", str(entry))
                prefix = f"[{ts}] " if ts else ""
                tag = f"[{stage}] " if stage else ""
                lines.append(f"- {prefix}{tag}{msg}")

        lines.extend([
            "",
            "## Recommendations",
            "- Review any failed integrity checks before redistribution.",
            "- Retain the final_report.json and validation_report.json as evidence.",
            "- Archive the report bundle with the project submission.",
            "",
        ])
        return "\n".join(lines)

    @staticmethod
    def _icon_data_uri(icon_path: str) -> str:
        """Read a bundled icon PNG (relative to RESTORE_DIR) and return a base64 data URI."""
        if not icon_path:
            return ""
        full_path = RESTORE_DIR / icon_path
        try:
            data = full_path.read_bytes()
        except OSError:
            return ""
        return f"data:image/png;base64,{base64.b64encode(data).decode('ascii')}"

    def _build_html(self, report: dict[str, Any], restore_report: dict[str, Any]) -> str:
        """Render the final report as a standalone HTML page."""
        validation = report["validation"]
        summary = report["summary"]

        def _esc(text: str) -> str:
            return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        all_files = restore_report.get("files_restored", [])
        file_rows = "".join(
            f"<tr><td>{_esc(item.get('relative_path', 'unknown'))}</td>"
            f"<td>{_esc(item.get('destination', 'unknown'))}</td>"
            f"<td>{_esc(item.get('verification_status', 'unknown'))}</td></tr>"
            for item in all_files
        ) or "<tr><td colspan='3'>No restoration entries available.</td></tr>"

        apps_installed: list[dict[str, Any]] = restore_report.get("applications_installed", [])
        app_rows = "".join(
            f"<tr><td>"
            + (f"<img class='app-icon' src='{self._icon_data_uri(app.get('icon_path', ''))}' alt=''/>"
               if self._icon_data_uri(app.get("icon_path", "")) else "<span class='app-icon-placeholder'></span>")
            + f"{_esc(str(app.get('windows_app', 'unknown')))}</td>"
            f"<td>{_esc(str(app.get('linux_package', 'unknown')))}</td>"
            f"<td>{_esc(str(app.get('mapping_confidence', '')))}</td></tr>"
            for app in apps_installed
        )
        app_map_section = (
            f"<div class='card'><h2>Application Map ({len(apps_installed)})</h2>"
            f"<table><tr><th>Windows App</th><th>Linux Package</th><th>Confidence</th></tr>{app_rows}</table></div>"
            if apps_installed
            else ""
        )

        shortcuts_restored: list[dict[str, Any]] = restore_report.get("shortcuts_restored", [])
        shortcuts_rows = "".join(
            f"<tr><td>{_esc(str(sc.get('name', 'unknown')))}</td>"
            f"<td>{_esc(str(sc.get('category', '')))}</td>"
            f"<td>{_esc(str(sc.get('status', '')))}</td></tr>"
            for sc in shortcuts_restored
        )
        shortcuts_section = (
            f"<div class='card'><h2>Shortcuts &amp; Launchers ({len(shortcuts_restored)})</h2>"
            f"<table><tr><th>Shortcut</th><th>Category</th><th>Status</th></tr>{shortcuts_rows}</table></div>"
            if shortcuts_restored
            else ""
        )

        warnings: list[str] = restore_report.get("warnings", [])
        warning_items = "".join(f"<li>⚠️ {_esc(str(w))}</li>" for w in warnings)
        warnings_section = (
            f"<div class='card warning-card'><h2>Warnings — Steps That Didn't Fully Complete ({len(warnings)})</h2>"
            f"<ul>{warning_items}</ul></div>"
            if warnings
            else ""
        )

        settings_applied: list[str] = restore_report.get("settings_applied", [])
        settings_manual: list[str] = restore_report.get("settings_manual", [])
        settings_guidance: str = restore_report.get("settings_guidance", "")
        settings_items = "".join(f"<li class='ok'>✅ {_esc(str(s))}</li>" for s in settings_applied)
        settings_items += "".join(f"<li class='warn'>⚠️ Needs manual setup: {_esc(str(s))}</li>" for s in settings_manual)
        settings_section = (
            f"<div class='card'><h2>Settings &amp; Configuration</h2><ul class='settings'>{settings_items}</ul>"
            + (f"<p class='hint'>Full guidance written to <code>{_esc(settings_guidance)}</code></p>" if settings_guidance else "")
            + "</div>"
            if (settings_applied or settings_manual)
            else ""
        )

        failed_files: list[dict[str, Any]] = validation.get("failed_files", [])
        failed_rows = "".join(
            f"<tr><td>{_esc(item.get('relative_path', item.get('destination', 'unknown')))}</td>"
            f"<td><code>{_esc(item.get('expected_hash', ''))}</code></td>"
            f"<td><code>{_esc(item.get('actual_hash', ''))}</code></td></tr>"
            for item in failed_files
        )
        failed_section = (
            f"<div class='card'><h2>Hash Mismatches ({len(failed_files)})</h2>"
            f"<table><tr><th>File</th><th>Expected</th><th>Actual</th></tr>{failed_rows}</table></div>"
            if failed_files
            else ""
        )

        missing_files: list[dict[str, Any]] = validation.get("missing_files", [])
        missing_rows = "".join(
            f"<li>{_esc(item.get('relative_path', item.get('expected_destination', 'unknown')))}</li>"
            for item in missing_files
        )
        missing_section = (
            f"<div class='card'><h2>Missing Files ({len(missing_files)})</h2><ul>{missing_rows}</ul></div>"
            if missing_files
            else ""
        )

        activity_log: list[dict[str, Any]] = report.get("activity_log", [])
        log_items = "".join(
            f"<li><span class='ts'>{_esc(entry.get('time') or entry.get('timestamp', ''))}</span> "
            f"<span class='stage'>[{_esc(entry.get('phase') or entry.get('stage', ''))}]</span> "
            f"{_esc(entry.get('message', str(entry)))}</li>"
            for entry in activity_log
        )
        log_section = (
            f"<div class='card'><h2>Activity Log</h2><ul class='log'>{log_items}</ul></div>"
            if activity_log
            else ""
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Final Migration Report</title>
  <style>
    body {{ font-family: Segoe UI, sans-serif; margin: 32px; color: #1b2e38; background: #f7fbfe; }}
    .card {{ background: white; border: 1px solid #c3d6e0; border-radius: 16px; padding: 24px; margin-bottom: 20px; }}
    .score {{ font-size: 54px; font-weight: 800; color: #1e6b46; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(220px, 1fr)); gap: 14px; }}
    .metric {{ background: #eef7fb; border: 1px solid #bfd6e2; border-radius: 12px; padding: 12px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border: 1px solid #c3d6e0; padding: 6px 10px; text-align: left; }}
    th {{ background: #eef7fb; }}
    ul.log {{ list-style: none; padding: 0; font-size: 13px; }}
    ul.log li {{ border-bottom: 1px solid #edf2f5; padding: 4px 0; }}
    .ts {{ color: #6b8fa3; margin-right: 6px; }}
    .stage {{ color: #1e6b46; font-weight: 600; margin-right: 4px; }}
    h1, h2 {{ margin-top: 0; }}
    .app-icon {{ width: 20px; height: 20px; vertical-align: middle; margin-right: 8px; border-radius: 4px; }}
    .app-icon-placeholder {{ display: inline-block; width: 20px; height: 20px; vertical-align: middle; margin-right: 8px; }}
    .warning-card {{ background: #fff8e6; border-color: #f0c674; }}
    .warning-card ul {{ margin: 0; padding-left: 20px; }}
    ul.settings {{ list-style: none; padding: 0; }}
    ul.settings li {{ padding: 4px 0; border-bottom: 1px solid #edf2f5; }}
    ul.settings li.warn {{ color: #8a5a00; }}
    .hint {{ color: #6b8fa3; font-size: 13px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Final Migration Report</h1>
    <p>Generated at {_esc(report['generated_at'])}</p>
    <div class="score">{summary['score']}%</div>
    <p>{_esc(summary['rating'])} final rating</p>
  </div>
  <div class="card">
    <h2>Key Metrics</h2>
    <div class="grid">
      <div class="metric">Files restored: {validation.get('restored_files', 0)} / {validation.get('total_files', 0)}</div>
      <div class="metric">Missing files: {validation.get('missing_files_count', 0)}</div>
      <div class="metric">Hash verified: {validation.get('hash_verified_files', 0)}</div>
      <div class="metric">Hash failed: {validation.get('hash_failed_files', 0)}</div>
      <div class="metric">Applications mapped: {validation.get('apps_mapped', 0)}</div>
      <div class="metric">Restored data: {_esc(validation.get('restored_data_size', '0 B'))}</div>
    </div>
  </div>
  {warnings_section}
  <div class="card">
    <h2>Timing</h2>
    <table>
      <tr><th>Event</th><th>Timestamp</th></tr>
      <tr><td>Restore started</td><td>{_esc(validation.get('restore_started_at', 'n/a'))}</td></tr>
      <tr><td>Restore completed</td><td>{_esc(validation.get('restore_completed_at', 'n/a'))}</td></tr>
      <tr><td>Validated at</td><td>{_esc(validation.get('validated_at', 'n/a'))}</td></tr>
    </table>
  </div>
  {settings_section}
  {failed_section}
  {missing_section}
  {app_map_section}
  {shortcuts_section}
  <div class="card">
    <h2>Restore Details ({len(all_files)} files)</h2>
    <table>
      <tr><th>Relative Path</th><th>Destination</th><th>Status</th></tr>
      {file_rows}
    </table>
  </div>
  {log_section}
</body>
</html>"""
