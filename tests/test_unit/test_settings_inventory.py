"""Tests for Windows settings inventory collection."""

from pathlib import Path

from src.inventory import settings as settings_inventory


def test_collect_settings_inventory_summarizes_and_exports(monkeypatch, tmp_path):
    def fake_read_registry(path, properties):
        if "Control Panel\\Desktop" in path:
            return {"WallPaper": str(tmp_path / "wall.jpg"), "WallpaperStyle": "10", "TileWallpaper": "0"}
        if "Themes\\Personalize" in path:
            return {"AppsUseLightTheme": 0, "SystemUsesLightTheme": 1}
        if path.endswith("Themes"):
            theme_path = tmp_path / "theme.theme"
            theme_path.write_text("theme", encoding="utf-8")
            return {"CurrentTheme": str(theme_path)}
        if "Windows\\DWM" in path:
            return {"ColorizationColor": 123}
        return {}

    wallpaper = tmp_path / "wall.jpg"
    wallpaper.write_bytes(b"wallpaper-bytes")

    monkeypatch.setattr(settings_inventory, "_read_registry_object", fake_read_registry)

    result = settings_inventory.collect_settings_inventory(export_assets=True)

    assert result["desktop"]["wallpaper_path"].endswith("wall.jpg")
    assert result["appearance"]["current_theme"].endswith("theme.theme")
    assert result["summary"]["portable_items"] == 2
    assert result["summary"]["exported_items"] == 2
    assert result["exported_assets"]["wallpaper"]
    assert result["exported_assets"]["theme"]


def test_write_settings_inventory_creates_file(tmp_path, monkeypatch):
    from src.config import MigrationConfigRoot, ProjectConfig, SourceSystemConfig, TargetSystemConfig
    from src.config import MigrationConfig, AutomationConfig, ValidationConfig, ResearchConfig, DemoConfig, BackupConfig, AIConfig

    config = MigrationConfigRoot(
        project=ProjectConfig(name="Test", version="1.0", maintainer="Tester"),
        source_system=SourceSystemConfig(windows_user="test", inventory_output_dir="inventory", backup_output_dir="backup", backup_paths=[]),
        target_system=TargetSystemConfig(distro="ubuntu", edition="22.04", language="en_US", timezone="UTC", hostname="host", username="user"),
        migration=MigrationConfig(mode="full_clean", target_disk="/dev/sda", layout="full_disk", swap_size_gb=4),
        automation=AutomationConfig(),
        validation=ValidationConfig(),
        research=ResearchConfig(),
        app_demo=DemoConfig(),
        backup=BackupConfig(),
        ai=AIConfig(),
    )

    monkeypatch.setattr(settings_inventory, "DATA_DIR", tmp_path)

    out = settings_inventory.write_settings_inventory(config, {"desktop": {"wallpaper_path": "x"}})
    assert out.exists()
    assert out.name == "settings_inventory.json"