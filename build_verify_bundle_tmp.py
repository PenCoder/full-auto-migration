"""Build a small, real migration-bundle test fixture for end-to-end verification.

Deliberately uses:
  - backslash-style relative_path in manifest.json (matches the real bug
    found earlier, to exercise the normalization fix for real).
  - a non-installable fake apt package (to exercise the non-fatal
    optional-step path for real — pkexec/apt-get genuinely don't exist
    on this Windows host, so this is a real failure, not a simulated one).
  - a backslash Windows path in settings_inventory.appearance.current_theme
    (exercises the theme-name display fix).
  - an unmapped top-level folder name ("VerifyTestFolder") so restored
    files land under target_home, NOT the real Windows ~/Documents.
"""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

WORK = Path("verify_bundle_work_tmp")
if WORK.exists():
    shutil.rmtree(WORK)
WORK.mkdir()

files_dir = WORK / "files" / "VerifyTestFolder"
files_dir.mkdir(parents=True)

contents = {
    "test1.txt": b"Hello from migration verification test file 1.\n",
    "test2.txt": b"Hello from migration verification test file 2.\n",
}
entries = []
for name, data in contents.items():
    (files_dir / name).write_bytes(data)
    entries.append({
        "source_path": f"C:\\Users\\kofi\\Documents\\{name}",
        "relative_path": f"VerifyTestFolder\\{name}",  # backslash on purpose
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    })

manifest = {
    "timestamp": "2026-06-20T00:00:00Z",
    "total_files": len(entries),
    "entries": entries,
}
(WORK / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

apps = {
    "applications": [
        {
            "windows_app": "Definitely Not A Real App",
            "linux_package": "definitely-not-a-real-package-xyz",
            "migration_strategy": "apt",
            "mapping_confidence": "low",
            "category": "utility",
            "icon_path": "",
        }
    ]
}
(WORK / "apps_to_install.json").write_text(json.dumps(apps, indent=2), encoding="utf-8")

settings_inventory = {
    "desktop": {"wallpaper_path": ""},
    "appearance": {
        "current_theme": "C:\\Users\\kofi\\AppData\\Local\\Microsoft\\Windows\\Themes\\Custom.theme",
        "apps_use_light_theme": 1,
        "system_uses_light_theme": 1,
        "accent_color": 123456,
    },
    "exported_assets": {},
}
(WORK / "settings_inventory.json").write_text(json.dumps(settings_inventory, indent=2), encoding="utf-8")

settings_plan = {"customization_depth": "guided", "items": [], "counts": {}}
(WORK / "settings_migration_plan.json").write_text(json.dumps(settings_plan, indent=2), encoding="utf-8")

shortcuts = {"entries": [], "counts": {"desktop": 0, "start_menu": 0, "taskbar": 0, "matched": 0}}
(WORK / "shortcuts_inventory.json").write_text(json.dumps(shortcuts, indent=2), encoding="utf-8")

zip_path = Path("verify_bundle_test.zip")
if zip_path.exists():
    zip_path.unlink()
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in WORK.rglob("*"):
        if p.is_file():
            zf.write(p, p.relative_to(WORK))

shutil.rmtree(WORK)
print("built:", zip_path.resolve())
