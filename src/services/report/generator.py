"""Report generation service implementation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.loggers import get_logger
from src.constants import BASE_DIR, RESTORE_DIR


class ReportGenerationService:
    """Service for comprehensive migration report generation.
    
    Responsibilities:
    - Aggregate inventory, analysis, and validation results
    - Generate reports in multiple formats (JSON, Markdown, HTML)
    - Compute quality metrics and summaries
    - Persist reports to disk
    """

    def __init__(self, config: Any, report_dir: Path | None = None):
        """Initialize report generation service.
        
        Args:
            config: MigrationConfigRoot configuration object
            report_dir: Output directory for reports
        """
        self.config = config
        self.logger = get_logger("services.report")
        self.report_dir = report_dir or (BASE_DIR / "docs" / "reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        inventory: dict[str, Any],
        analysis: dict[str, Any],
        recommendations: dict[str, Any],
        validation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate comprehensive migration report.
        
        Args:
            inventory: Hardware and software inventory data
            analysis: Analysis and compatibility data
            recommendations: App and file recommendations
            validation: Optional validation and restore results
            
        Returns:
            Dictionary with paths to generated reports
        """
        self.logger.info("Generating migration report...")
        try:
            # Build report structure
            report_data = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "inventory": inventory,
                "analysis": analysis,
                "recommendations": recommendations,
                "validation": validation or {},
                "summary": self._build_summary(inventory, analysis, validation),
            }
            
            # Generate formats
            json_path = self._write_json(report_data)
            md_path = self._write_markdown(report_data)
            html_path = self._write_html(report_data)
            
            self.logger.info("Report generated successfully")
            return {
                "json_path": str(json_path),
                "markdown_path": str(md_path),
                "html_path": str(html_path),
                "report_data": report_data,
            }
        except Exception as exc:
            self.logger.exception("Report generation failed: %s", exc)
            raise

    def _write_json(self, report: dict[str, Any]) -> Path:
        """Write report as JSON file."""
        path = self.report_dir / "migration_report.json"
        path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        self.logger.info("JSON report written to %s", path)
        return path

    def _write_markdown(self, report: dict[str, Any]) -> Path:
        """Write report as Markdown file."""
        lines = [
            "# Migration Report",
            "",
            f"Generated: {report['generated_at']}",
            "",
            "## Summary",
            f"- Status: Migration completed",
            f"- Timestamp: {report['generated_at']}",
            "",
        ]
        
        summary = report.get("summary", {})
        if summary:
            lines.extend([
                "## Quality Metrics",
                f"- Sovereignty Score: {summary.get('sovereignty_score', 'N/A')}%",
                f"- Data Integrity: {summary.get('integrity_verified', 'N/A')} files verified",
                f"- Apps Mapped: {summary.get('apps_mapped', 'N/A')}",
                "",
            ])
        
        lines.extend([
            "## Inventory Summary",
            f"- Hardware components analyzed",
            f"- Software packages catalogued",
            "",
            "## Recommendations",
            "- Application migration mappings generated",
            "- File migration priorities assigned",
            "",
            "## Next Steps",
            "1. Review this report for migration planning",
            "2. Execute backup creation",
            "3. Deploy Linux system with backup",
            "4. Validate restore integrity",
            "",
        ])
        
        path = self.report_dir / "migration_report.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        self.logger.info("Markdown report written to %s", path)
        return path

    def _write_html(self, report: dict[str, Any]) -> Path:
        """Write report as HTML file."""
        summary = report.get("summary", {})
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Migration Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1, h2 {{ color: #333; }}
        .summary {{ background: #f0f0f0; padding: 15px; border-radius: 5px; }}
        .metric {{ margin: 10px 0; }}
    </style>
</head>
<body>
    <h1>Migration Report</h1>
    <p>Generated: {report['generated_at']}</p>
    
    <div class="summary">
        <h2>Summary</h2>
        <div class="metric">Sovereignty Score: {summary.get('sovereignty_score', 'N/A')}%</div>
        <div class="metric">Data Integrity: {summary.get('integrity_verified', 'N/A')} files verified</div>
        <div class="metric">Apps Mapped: {summary.get('apps_mapped', 'N/A')}</div>
    </div>
    
    <h2>Next Steps</h2>
    <ol>
        <li>Review this report for migration planning</li>
        <li>Execute backup creation</li>
        <li>Deploy Linux system with backup</li>
        <li>Validate restore integrity</li>
    </ol>
</body>
</html>"""
        
        path = self.report_dir / "migration_report.html"
        path.write_text(html_content, encoding="utf-8")
        self.logger.info("HTML report written to %s", path)
        return path

    @staticmethod
    def _build_summary(
        inventory: dict[str, Any],
        analysis: dict[str, Any],
        validation: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Build summary metrics for the report."""
        validation = validation or {}
        
        return {
            "sovereignty_score": validation.get("total_sovereignty_score", 0),
            "integrity_verified": validation.get("hash_verified_files", 0),
            "integrity_failed": validation.get("hash_failed_files", 0),
            "apps_mapped": len(analysis.get("software", [])) if analysis.get("software") else 0,
            "files_analyzed": len(inventory.get("software", {}).get("entries", [])) if inventory.get("software") else 0,
        }
