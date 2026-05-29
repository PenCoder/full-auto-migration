"""Tests for settings migration planning service."""

from src.services.settings_service import SettingsMigrationService


def _sample_inventory():
    return {
        "desktop": {"wallpaper_path": "C:/wallpaper.jpg", "wallpaper_style": "10", "tile_wallpaper": "0"},
        "appearance": {"current_theme": "C:/theme.theme", "apps_use_light_theme": 0, "system_uses_light_theme": 1, "accent_color": 123},
        "exported_assets": {"wallpaper": "docs/reports/settings_assets/wallpaper.jpg", "theme": "docs/reports/settings_assets/current_theme.theme"},
    }


def test_build_plan_guided_has_safe_defaults():
    service = SettingsMigrationService()
    plan = service.build_plan(_sample_inventory(), "guided")

    assert plan["mode"] == "guided"
    assert plan["customization_depth"] == "minimal"
    assert plan["counts"]["auto_migrate"] >= 1
    assert plan["counts"]["manual_review"] == 0


def test_build_plan_expert_adds_manual_review_items():
    service = SettingsMigrationService()
    plan = service.build_plan(_sample_inventory(), "expert")

    assert plan["mode"] == "expert"
    assert plan["customization_depth"] == "advanced"
    assert plan["counts"]["excluded"] >= 3
    assert any(item["name"] == "Taskbar / Panel Layout" for item in plan["items"])


def test_build_plan_expert_selected_advanced_items_require_manual_review():
    service = SettingsMigrationService()
    plan = service.build_plan(
        _sample_inventory(),
        "expert",
        selections={
            "wallpaper": True,
            "theme": True,
            "light_dark": True,
            "accent_color": True,
            "taskbar_layout": True,
            "keyboard_shortcuts": True,
            "file_associations": True,
        },
    )

    assert plan["counts"]["manual_review"] >= 3


def test_build_plan_honors_selection_preferences():
    service = SettingsMigrationService()
    plan = service.build_plan(
        _sample_inventory(),
        "balanced",
        selections={"wallpaper": True, "theme": False, "light_dark": True, "accent_color": False},
    )

    actions = {item["name"]: item["action"] for item in plan["items"]}
    assert actions["Wallpaper"] == "auto_migrate"
    assert actions["Theme File"] == "exclude"
    assert actions["Accent Color"] == "exclude"


def test_write_plan_creates_artifacts(tmp_path):
    service = SettingsMigrationService()
    plan = service.build_plan(_sample_inventory(), "balanced")
    paths = service.write_plan(plan, report_dir=tmp_path)

    assert (tmp_path / "settings_migration_plan.json").exists()
    assert (tmp_path / "settings_migration_plan.md").exists()
    assert paths["json_path"].endswith("settings_migration_plan.json")