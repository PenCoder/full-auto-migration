"""Integration tests for the recommendation → validation → report pipeline.

These tests wire RecommendationService, validate_restore_report, and
ReportService together using only filesystem I/O (no Qt, no network).
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from src.services.recommendation_service import RecommendationService
from src.services.report_service import ReportService
from src.services.validation_service import validate_restore_report


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_dirs(tmp_path: Path) -> dict[str, Path]:
    dirs = {
        "reports": tmp_path / "reports",
        "restore": tmp_path / "restore",
        "files": tmp_path / "files",
    }
    for d in dirs.values():
        d.mkdir(parents=True)
    return dirs


@pytest.fixture()
def csv_map_rows() -> list[dict[str, str]]:
    map_file = Path(__file__).parent.parent.parent / "configs" / "linux_ms_map.csv"
    if not map_file.exists():
        pytest.skip("linux_ms_map.csv not found")
    with map_file.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _write_restore_report(restore_dir: Path, files_dir: Path, *, introduce_mismatch: bool = False) -> Path:
    """Write a synthetic restore_report.json into restore_dir."""
    # Create two real files on disk so validate_restore_report can stat them.
    f1 = files_dir / "Documents" / "notes.txt"
    f1.parent.mkdir(parents=True, exist_ok=True)
    f1.write_text("hello world", encoding="utf-8")

    f2 = files_dir / "Documents" / "report.pdf"
    f2.write_bytes(b"%PDF-1.4 fake content")

    f3 = files_dir / "Pictures" / "photo.jpg"
    f3.parent.mkdir(parents=True, exist_ok=True)
    f3.write_bytes(b"\xff\xd8\xff fake jpeg")

    # f4 is referenced in the report but NOT created — becomes a missing file.
    f4_path = str(files_dir / "Music" / "song.mp3")

    report = {
        "started_at": "2025-05-01T10:00:00+00:00",
        "completed_at": "2025-05-01T10:05:00+00:00",
        "files_restored": [
            {
                "relative_path": "Documents/notes.txt",
                "destination": str(f1),
                "source": "backup:/notes.txt",
                "verification_status": "match",
                "source_hash": "abc123",
                "dest_hash": "abc123",
            },
            {
                "relative_path": "Documents/report.pdf",
                "destination": str(f2),
                "source": "backup:/report.pdf",
                "verification_status": "mismatch" if introduce_mismatch else "match",
                "source_hash": "def456",
                "dest_hash": "zzz000" if introduce_mismatch else "def456",
            },
            {
                "relative_path": "Pictures/photo.jpg",
                "destination": str(f3),
                "source": "backup:/photo.jpg",
                "verification_status": "match",
                "source_hash": "ghi789",
                "dest_hash": "ghi789",
            },
            {
                "relative_path": "Music/song.mp3",
                "destination": f4_path,
                "source": "backup:/song.mp3",
                "verification_status": "unknown",
                "source_hash": "",
                "dest_hash": "",
            },
        ],
        "applications_installed": [
            {"name": "firefox", "status": "installed"},
            {"name": "libreoffice", "status": "installed"},
        ],
    }
    report_path = restore_dir / "restore_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# Recommendation pipeline tests
# ---------------------------------------------------------------------------

class TestRecommendationPipeline:
    def test_generate_recommendations_produces_report_files(
        self, tmp_dirs: dict[str, Path], csv_map_rows
    ):
        svc = RecommendationService(reports_dir=tmp_dirs["reports"])
        svc._load_mapping_rows = lambda: csv_map_rows  # type: ignore[method-assign]

        inventory = {
            "entries": [
                {"DisplayName": "Mozilla Firefox", "Version": "120", "Publisher": "Mozilla"},
                {"DisplayName": "Microsoft Word", "Version": "2021", "Publisher": "Microsoft"},
                {"DisplayName": "VLC media player", "Version": "3.0", "Publisher": "VideoLAN"},
            ]
        }
        result = svc.generate_recommendations(software_inventory=inventory, strategy="local")

        assert result["recommended_count"] >= 1
        assert Path(result["json_path"]).exists()
        assert Path(result["markdown_path"]).exists()

        payload = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
        assert payload["strategy"] == "local"
        assert isinstance(payload["recommendations"], list)

    def test_online_strategy_adds_repology_score(
        self, tmp_dirs: dict[str, Path], csv_map_rows
    ):
        svc = RecommendationService(reports_dir=tmp_dirs["reports"])
        svc._load_mapping_rows = lambda: csv_map_rows  # type: ignore[method-assign]

        inventory = {"entries": [{"DisplayName": "Mozilla Firefox", "Version": "120", "Publisher": "Mozilla"}]}
        with patch.object(svc, "_query_online_package_signal", return_value="verified"):
            result = svc.generate_recommendations(
                software_inventory=inventory,
                strategy="online",
                repology_config={"software_online_lookup_enabled": True, "software_online_send_fields": ["name"]},
            )

        for rec in result["recommendations"]:
            assert "repology_score" in rec

    def test_category_is_populated_from_csv(
        self, tmp_dirs: dict[str, Path], csv_map_rows
    ):
        """WP2.5: category must be read from the CSV mapping row, not hardcoded to empty."""
        svc = RecommendationService(reports_dir=tmp_dirs["reports"])
        svc._load_mapping_rows = lambda: csv_map_rows  # type: ignore[method-assign]

        inventory = {
            "entries": [
                {"DisplayName": "Mozilla Firefox", "Version": "120", "Publisher": "Mozilla"},
                {"DisplayName": "Microsoft Word", "Version": "2021", "Publisher": "Microsoft"},
                {"DisplayName": "VLC media player", "Version": "3.0", "Publisher": "VideoLAN"},
            ]
        }
        result = svc.generate_recommendations(software_inventory=inventory, strategy="local")

        categories = {rec["windows_app"]: rec.get("category", "") for rec in result["recommendations"]}
        for app, cat in categories.items():
            assert cat != "", f"{app!r} must have a non-empty category — it should be read from the CSV"

    def test_csv_confidence_floor_applied_to_mapping_score(self, csv_map_rows):
        """WP2.5: a CSV row marked 'high' confidence must yield at least 0.90 confidence_score."""
        from src.analysis.dynamic_rules import resolve_mapping

        # Microsoft Word is marked 'high' in the CSV.
        decision = resolve_mapping("Microsoft Word", csv_map_rows)
        assert decision is not None
        assert decision.confidence_score >= 0.90, (
            f"CSV 'high' confidence must floor the score to ≥0.90; got {decision.confidence_score}"
        )

    def test_repology_score_benefits_from_category(
        self, tmp_dirs: dict[str, Path], csv_map_rows
    ):
        """WP2.5: repology_score for a categorised app must exceed the score for one without a category."""
        svc = RecommendationService(reports_dir=tmp_dirs["reports"])
        svc._load_mapping_rows = lambda: csv_map_rows  # type: ignore[method-assign]

        inventory = {"entries": [{"DisplayName": "Mozilla Firefox", "Version": "120", "Publisher": "Mozilla"}]}
        with patch.object(svc, "_query_online_package_signal", return_value="not_verified"):
            result = svc.generate_recommendations(
                software_inventory=inventory,
                strategy="online",
                repology_config={"software_online_lookup_enabled": True, "software_online_send_fields": ["name"]},
            )

        for rec in result["recommendations"]:
            # Firefox has category="Browser" — category_bonus (12) must be included.
            assert int(rec.get("repology_score", 0)) > RecommendationService._agent_score(
                confidence=rec["mapping_confidence"],
                category="",
                online_signal=rec["online_signal"],
            ), "A recommendation with a category must score higher than the same one without"


# ---------------------------------------------------------------------------
# Validation pipeline tests
# ---------------------------------------------------------------------------

class TestValidationPipeline:
    def test_validate_clean_report(self, tmp_dirs: dict[str, Path]):
        report_path = _write_restore_report(tmp_dirs["restore"], tmp_dirs["files"])

        with patch("src.services.validation_service.RESTORE_DIR", tmp_dirs["restore"]):
            summary = validate_restore_report(report_path)

        assert summary["total_files"] == 4
        assert summary["restored_files"] == 3  # one missing (song.mp3)
        assert summary["missing_files_count"] == 1
        assert summary["hash_verified_files"] >= 2
        assert summary["hash_failed_files"] == 0
        assert summary["failed_files"] == []
        assert len(summary["missing_files"]) == 1
        assert summary["missing_files"][0]["relative_path"] == "Music/song.mp3"
        assert summary["total_sovereignty_score"] > 0
        assert summary["validated_at"]

    def test_validate_report_with_mismatch(self, tmp_dirs: dict[str, Path]):
        report_path = _write_restore_report(
            tmp_dirs["restore"], tmp_dirs["files"], introduce_mismatch=True
        )

        with patch("src.services.validation_service.RESTORE_DIR", tmp_dirs["restore"]):
            summary = validate_restore_report(report_path)

        assert summary["hash_failed_files"] == 1
        assert len(summary["failed_files"]) == 1
        failed = summary["failed_files"][0]
        assert failed["relative_path"] == "Documents/report.pdf"
        assert failed["expected_hash"] == "def456"
        assert failed["actual_hash"] == "zzz000"

    def test_validate_writes_validation_report_json(self, tmp_dirs: dict[str, Path]):
        report_path = _write_restore_report(tmp_dirs["restore"], tmp_dirs["files"])

        with patch("src.services.validation_service.RESTORE_DIR", tmp_dirs["restore"]):
            summary = validate_restore_report(report_path)

        val_report = tmp_dirs["restore"] / "validation_report.json"
        assert val_report.exists()
        data = json.loads(val_report.read_text(encoding="utf-8"))
        assert data["total_files"] == summary["total_files"]

    def test_validate_preserves_timing_from_restore_report(self, tmp_dirs: dict[str, Path]):
        report_path = _write_restore_report(tmp_dirs["restore"], tmp_dirs["files"])

        with patch("src.services.validation_service.RESTORE_DIR", tmp_dirs["restore"]):
            summary = validate_restore_report(report_path)

        assert summary["restore_started_at"] == "2025-05-01T10:00:00+00:00"
        assert summary["restore_completed_at"] == "2025-05-01T10:05:00+00:00"

    def test_validate_missing_report_raises(self, tmp_dirs: dict[str, Path]):
        from src.orchestration.errors import MigrationError
        with pytest.raises(MigrationError):
            validate_restore_report(tmp_dirs["restore"] / "nonexistent.json")


# ---------------------------------------------------------------------------
# Full pipeline: validate → report
# ---------------------------------------------------------------------------

class TestFullValidateReportPipeline:
    def test_validate_then_report(self, tmp_dirs: dict[str, Path]):
        report_path = _write_restore_report(tmp_dirs["restore"], tmp_dirs["files"])

        # Step 1: validate
        with patch("src.services.validation_service.RESTORE_DIR", tmp_dirs["restore"]):
            summary = validate_restore_report(report_path)

        assert (tmp_dirs["restore"] / "validation_report.json").exists()

        # Step 2: generate final report
        report_svc = ReportService(report_dir=tmp_dirs["reports"])
        with patch.object(report_svc, "load_validation_summary", return_value=summary):
            with patch("src.services.report_service.RESTORE_DIR", tmp_dirs["restore"]):
                # copy restore_report.json so report_service can read it
                (tmp_dirs["restore"] / "restore_report.json").write_text(
                    report_path.read_text(encoding="utf-8"), encoding="utf-8"
                )
                result = report_svc.generate_report(
                    activity_log=[
                        {"time": "10:05:00", "phase": "restore", "message": "Restore completed."},
                        {"time": "10:06:00", "phase": "validation", "message": "Validation complete. Score=90%."},
                    ]
                )

        assert Path(result["json_path"]).exists()
        assert Path(result["markdown_path"]).exists()
        assert Path(result["html_path"]).exists()

        # Validate JSON content
        payload = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
        assert payload["summary"]["score"] > 0
        assert len(payload["activity_log"]) == 2

        # Validate Markdown content
        md = Path(result["markdown_path"]).read_text(encoding="utf-8")
        assert "## Activity Log" in md
        assert "restore" in md
        assert "Missing Files" in md or "missing" in md.lower()

        # Validate HTML content
        html = Path(result["html_path"]).read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html
        assert "Activity Log" in html

    def test_report_without_activity_log_still_works(self, tmp_dirs: dict[str, Path]):
        report_path = _write_restore_report(tmp_dirs["restore"], tmp_dirs["files"])

        with patch("src.services.validation_service.RESTORE_DIR", tmp_dirs["restore"]):
            summary = validate_restore_report(report_path)

        report_svc = ReportService(report_dir=tmp_dirs["reports"])
        with patch.object(report_svc, "load_validation_summary", return_value=summary):
            with patch("src.services.report_service.RESTORE_DIR", tmp_dirs["restore"]):
                (tmp_dirs["restore"] / "restore_report.json").write_text(
                    report_path.read_text(encoding="utf-8"), encoding="utf-8"
                )
                result = report_svc.generate_report()  # no activity_log passed

        html = Path(result["html_path"]).read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in html
        assert "Activity Log" not in html
