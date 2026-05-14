"""Integration tests for CLI scan workflow."""

from pathlib import Path

import json
from typer.testing import CliRunner

import src.cli as cli


class _DummyRecommendationService:
    def generate_recommendations(self, software_inventory, strategy, selection_profile, ai_config=None, mapping_overrides=None):
        return {
            "recommended_count": len(software_inventory.get("entries", [])),
            "json_path": "docs/reports/recs.json",
            "markdown_path": "docs/reports/recs.md",
            "strategy": strategy,
            "selection_profile": selection_profile,
        }


class _DummyFileRecommendationService:
    def generate_recommendations(self, file_inventory, choice_mode="all_files", use_ai=False, ai_config=None, selected_file_types=None):
        return {
            "choice_mode": choice_mode,
            "ranking_method": "deterministic",
            "recommended_count": len(file_inventory.get("files", [])),
            "input_count": len(file_inventory.get("files", [])),
            "json_path": "docs/reports/file_recs.json",
            "markdown_path": "docs/reports/file_recs.md",
        }


def _fake_settings_inventory():
    return {
        "timestamp": "2026-04-21T00:00:00Z",
        "desktop": {"wallpaper_path": "C:/wallpaper.jpg", "wallpaper_style": "10", "tile_wallpaper": "0"},
        "appearance": {"current_theme": "C:/theme.theme", "apps_use_light_theme": 0, "system_uses_light_theme": 1, "accent_color": 123},
        "exported_assets": {"wallpaper": "docs/reports/settings_assets/wallpaper.jpg", "theme": "docs/reports/settings_assets/current_theme.theme"},
        "summary": {"portable_items": 2, "exported_items": 2},
    }


def test_scan_quick_without_analysis_or_recommendations(monkeypatch, mock_config):
    runner = CliRunner()

    monkeypatch.setattr(cli, "load_configuration", lambda _cfg: mock_config)
    monkeypatch.setattr(cli, "collect_hardware_inventory", lambda: {"cpu": "ok"})
    monkeypatch.setattr(cli, "collect_software_inventory", lambda deep_scan=False: {"entries": [{"DisplayName": "App"}]})
    monkeypatch.setattr(cli, "collect_settings_inventory", lambda export_assets=True: _fake_settings_inventory())
    monkeypatch.setattr(cli, "write_hardware_inventory", lambda _cfg, _inv: Path("data/hardware_inventory.json"))
    monkeypatch.setattr(cli, "write_software_inventory", lambda _cfg, _inv: Path("data/software_inventory.json"))
    monkeypatch.setattr(cli, "write_settings_inventory", lambda _cfg, _inv: Path("data/settings_inventory.json"))

    result = runner.invoke(
        cli.app,
        ["scan", "--no-analysis", "--recommendations", "none"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["scan"]["depth"] == "quick"
    assert payload["scan"]["settings_summary"]["portable_items"] == 2
    assert "analysis" not in payload
    assert "recommendations" not in payload


def test_scan_deep_with_analysis_and_recommendations(monkeypatch, mock_config):
    runner = CliRunner()

    monkeypatch.setattr(cli, "load_configuration", lambda _cfg: mock_config)
    monkeypatch.setattr(cli, "collect_hardware_inventory", lambda: {"cpu": "ok", "ram": "ok"})
    monkeypatch.setattr(
        cli,
        "collect_software_inventory",
        lambda deep_scan=False: {
            "entries": [{"DisplayName": "App1"}, {"DisplayName": "App2"}],
            "deep_scan": deep_scan,
        },
    )
    monkeypatch.setattr(cli, "collect_settings_inventory", lambda export_assets=True: _fake_settings_inventory())
    monkeypatch.setattr(cli, "write_hardware_inventory", lambda _cfg, _inv: Path("data/hardware_inventory.json"))
    monkeypatch.setattr(cli, "write_software_inventory", lambda _cfg, _inv: Path("data/software_inventory.json"))
    monkeypatch.setattr(cli, "write_settings_inventory", lambda _cfg, _inv: Path("data/settings_inventory.json"))
    monkeypatch.setattr(cli, "generate_hardware_matrix", lambda _cfg, _inv: [{"item": "cpu"}])
    monkeypatch.setattr(cli, "write_hardware_matrix", lambda _cfg, _rows: Path("data/hardware_matrix.md"))
    monkeypatch.setattr(cli, "generate_software_mapping", lambda _cfg, _entries: [{"win": "App1", "linux": "app1"}])
    monkeypatch.setattr(cli, "write_software_mapping", lambda _rows: Path("data/software_mapping.md"))
    monkeypatch.setattr(cli, "RecommendationService", _DummyRecommendationService)

    result = runner.invoke(
        cli.app,
        ["scan", "--deep", "--analysis", "--recommendations", "local", "--selection-profile", "prioritize"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["scan"]["depth"] == "deep"
    assert payload["analysis"]["hardware_rows"] == 1
    assert payload["recommendations"]["strategy"] == "local"
    assert payload["recommendations"]["selection_profile"] == "prioritize"


def test_scan_balanced_mode_includes_file_recommendations(monkeypatch, mock_config):
    """Balanced mode scan should produce file_recommendations in output."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "load_configuration", lambda _cfg: mock_config)
    monkeypatch.setattr(cli, "collect_hardware_inventory", lambda: {"cpu": "ok"})
    monkeypatch.setattr(cli, "collect_software_inventory", lambda deep_scan=False: {"entries": [{"DisplayName": "Firefox"}]})
    monkeypatch.setattr(cli, "collect_settings_inventory", lambda export_assets=True: _fake_settings_inventory())
    monkeypatch.setattr(cli, "write_hardware_inventory", lambda _cfg, _inv: Path("data/hardware_inventory.json"))
    monkeypatch.setattr(cli, "write_software_inventory", lambda _cfg, _inv: Path("data/software_inventory.json"))
    monkeypatch.setattr(cli, "write_settings_inventory", lambda _cfg, _inv: Path("data/settings_inventory.json"))
    monkeypatch.setattr(cli, "generate_hardware_matrix", lambda _cfg, _inv: [])
    monkeypatch.setattr(cli, "write_hardware_matrix", lambda _cfg, _rows: Path("data/hw.md"))
    monkeypatch.setattr(cli, "generate_software_mapping", lambda _cfg, _entries: [])
    monkeypatch.setattr(cli, "write_software_mapping", lambda _rows: Path("data/sw.md"))
    monkeypatch.setattr(cli, "RecommendationService", _DummyRecommendationService)
    monkeypatch.setattr(cli, "FileRecommendationService", _DummyFileRecommendationService)
    monkeypatch.setattr(cli, "_build_file_inventory", lambda cfg, max_files=8000: {"files": [{"path": "/tmp/a.txt", "size": 100, "last_accessed_days_ago": 5}]})

    result = runner.invoke(cli.app, ["scan", "--mode", "balanced"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert "file_recommendations" in payload, "balanced mode must emit file_recommendations"
    assert payload["file_recommendations"]["input_count"] == 1
    assert payload["file_recommendations"]["choice_mode"] == "all_files"


def test_scan_guided_mode_omits_file_recommendations(monkeypatch, mock_config):
    """Guided mode scan should NOT include file_recommendations."""
    runner = CliRunner()

    monkeypatch.setattr(cli, "load_configuration", lambda _cfg: mock_config)
    monkeypatch.setattr(cli, "collect_hardware_inventory", lambda: {"cpu": "ok"})
    monkeypatch.setattr(cli, "collect_software_inventory", lambda deep_scan=False: {"entries": []})
    monkeypatch.setattr(cli, "collect_settings_inventory", lambda export_assets=True: _fake_settings_inventory())
    monkeypatch.setattr(cli, "write_hardware_inventory", lambda _cfg, _inv: Path("data/hw.json"))
    monkeypatch.setattr(cli, "write_software_inventory", lambda _cfg, _inv: Path("data/sw.json"))
    monkeypatch.setattr(cli, "write_settings_inventory", lambda _cfg, _inv: Path("data/settings.json"))
    monkeypatch.setattr(cli, "RecommendationService", _DummyRecommendationService)

    result = runner.invoke(cli.app, ["scan", "--mode", "guided"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert "file_recommendations" not in payload, "guided mode must not emit file_recommendations"


def test_scan_rejects_invalid_recommendation_mode():
    runner = CliRunner()
    result = runner.invoke(cli.app, ["scan", "--recommendations", "invalid"])
    assert result.exit_code == 2
    assert "Invalid recommendations mode" in result.stdout
