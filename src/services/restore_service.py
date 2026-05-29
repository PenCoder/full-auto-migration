from pathlib import Path
import json
import os
import shutil
import subprocess
import zipfile
import hashlib
from typing import Callable, Optional

from src.constants import EXTRACTED_BACKUP_DIR, RESTORE_REPORT
from src.loggers import get_logger
from src.orchestration.errors import ERR_ARCHIVE_UNSAFE_PATH, ERR_MISSING_BUNDLE, MigrationError
from src.services.package_manager import detect_package_manager, install_packages

# Maps Windows user-folder names (lowercase) to Linux home-directory equivalents.
# Files in known folders land directly in ~/Documents, ~/Pictures, etc.
# Everything else falls back to target_home/<folder_name>/.
_WIN_FOLDER_MAP: dict[str, str] = {
    "documents": "Documents",
    "pictures": "Pictures",
    "music": "Music",
    "videos": "Videos",
    "desktop": "Desktop",
    "downloads": "Downloads",
    "saved games": "Games",
    "favorites": ".favorites",
    "onedrive": "OneDrive",
}

# gsettings / xfconf keys per desktop environment for wallpaper and theme.
_DE_WALLPAPER: dict[str, list[list[str]]] = {
    "cinnamon": [
        ["gsettings", "set", "org.cinnamon.desktop.background", "picture-uri", "{uri}"],
    ],
    "gnome": [
        ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", "{uri}"],
        ["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", "{uri}"],
    ],
    "mate": [
        ["gsettings", "set", "org.mate.background", "picture-filename", "{path}"],
    ],
    "xfce": [
        ["xfconf-query", "-c", "xfce4-desktop", "-p",
         "/backdrop/screen0/monitor0/workspace0/last-image", "-s", "{path}"],
    ],
}

_DE_DARK_THEME: dict[str, list[str]] = {
    "cinnamon": ["gsettings", "set", "org.cinnamon.desktop.interface", "gtk-theme", "Mint-Y-Dark"],
    "gnome":    ["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", "prefer-dark"],
    "mate":     ["gsettings", "set", "org.mate.interface", "gtk-theme", "BlackMATE"],
    "xfce":     ["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName", "-s", "Greybird-dark"],
    "kde":      ["lookandfeeltool", "--apply", "org.kde.breezedark.desktop"],
}

_DE_LIGHT_THEME: dict[str, list[str]] = {
    "cinnamon": ["gsettings", "set", "org.cinnamon.desktop.interface", "gtk-theme", "Mint-Y"],
    "gnome":    ["gsettings", "set", "org.gnome.desktop.interface", "color-scheme", "default"],
    "mate":     ["gsettings", "set", "org.mate.interface", "gtk-theme", "Menta"],
    "xfce":     ["xfconf-query", "-c", "xsettings", "-p", "/Net/ThemeName", "-s", "Greybird"],
    "kde":      ["lookandfeeltool", "--apply", "org.kde.breeze.desktop"],
}


ProgressCb = Callable[[int, str], None]


class RestoreService:
    """
    Linux-side restoration:
    - Extract backup archive
    - Restore files to home directory preserving Windows folder structure
    - Verify file integrity via SHA-256
    - Apply desktop settings (wallpaper, light/dark preference)
    - Install selected Linux applications via the system package manager
    """

    def __init__(
        self,
        bundle_dir: Path,
        target_home: Path,
        progress_cb: Optional[ProgressCb] = None,
        target_distro: str | None = None,
    ):
        self.logger = get_logger("restore_service")
        self.bundle_dir = bundle_dir
        self.target_home = target_home
        self.progress_cb = progress_cb
        self.target_distro = target_distro

        self.manifest_path = bundle_dir / "manifest.json"
        self.archive_path = bundle_dir / "backup.zip"
        self.apps_path = bundle_dir / "apps_to_install.json"
        self.settings_inv_path = bundle_dir / "settings_inventory.json"
        self.settings_plan_path = bundle_dir / "settings_migration_plan.json"
        self.settings_assets_dir = bundle_dir / "settings_assets"

        self.restored_files: list[dict] = []
        self.installed_apps: list[dict] = []
        self.settings_applied: list[str] = []
        self.settings_guidance_path: str = ""
        self.apps_to_install: list[dict] = []
        self.report_path = RESTORE_REPORT

    def _progress(self, percent: int, msg: str) -> None:
        if self.progress_cb:
            self.progress_cb(max(0, min(100, int(percent))), msg)

    # ── Public entry point ────────────────────────────────────────────────────

    def run_restore(self) -> None:
        self._validate_bundle()

        self._progress(0, "Loading manifest…")
        manifest = self._load_manifest()

        self._progress(5, "Extracting backup archive…")
        extract_dir = self._extract_backup()

        self._progress(15, "Restoring files…")
        self._restore_files(manifest, extract_dir)

        self._progress(70, "Verifying file integrity…")
        self._verify_files(manifest)

        self._progress(82, "Applying desktop settings…")
        self._restore_settings()

        if self.apps_path.exists():
            self._progress(90, "Installing applications…")
            self._install_applications()

        self._write_restore_report()
        self._progress(100, "Restore complete.")

    def _validate_bundle(self) -> None:
        """Require manifest.json plus either backup.zip or an uncompressed files/ directory."""
        if not self.manifest_path.exists():
            raise MigrationError(ERR_MISSING_BUNDLE, str(self.bundle_dir))
        has_zip = self.archive_path.exists()
        has_files_dir = (self.bundle_dir / "files").is_dir()
        if not has_zip and not has_files_dir:
            raise MigrationError(ERR_MISSING_BUNDLE, str(self.bundle_dir))

    # ── Path resolution ───────────────────────────────────────────────────────

    def _resolve_destination(self, relative_path: str) -> Path:
        """Map a backup relative_path to its Linux destination.

        The first component is the original Windows folder name (e.g. 'Documents').
        Known folders map to ~/Documents, ~/Pictures, etc.
        Unknown folders fall back to target_home/<folder>/.
        """
        parts = Path(relative_path).parts
        if not parts:
            return self.target_home

        top = parts[0]
        linux_name = _WIN_FOLDER_MAP.get(top.lower())
        base = Path.home() / linux_name if linux_name else self.target_home / top

        rest = parts[1:]
        return base.joinpath(*rest) if rest else base

    # ── File restore ──────────────────────────────────────────────────────────

    def _load_manifest(self) -> dict:
        with self.manifest_path.open(encoding="utf-8") as f:
            return json.load(f)

    def _extract_backup(self) -> Path:
        """Extract backup.zip, or return the uncompressed files/ directory directly."""
        files_dir = self.bundle_dir / "files"

        if not self.archive_path.exists() and files_dir.is_dir():
            self.logger.info("No backup.zip found — using uncompressed files/ directory.")
            return files_dir

        extract_dir = EXTRACTED_BACKUP_DIR
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        extract_dir.mkdir(parents=True)

        with zipfile.ZipFile(self.archive_path, "r") as zf:
            for member in zf.infolist():
                target_path = (extract_dir / member.filename).resolve()
                if not str(target_path).startswith(str(extract_dir.resolve())):
                    raise MigrationError(ERR_ARCHIVE_UNSAFE_PATH, member.filename)
                if member.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member, "r") as src, target_path.open("wb") as dst:
                        shutil.copyfileobj(src, dst)

        self.logger.info("Backup archive extracted to %s", extract_dir)
        return extract_dir

    def _restore_files(self, manifest: dict, extract_dir: Path) -> None:
        entries = manifest.get("entries", [])
        total = max(1, len(entries))

        for i, entry in enumerate(entries, start=1):
            src = extract_dir / entry["relative_path"]
            dst = self._resolve_destination(entry["relative_path"])
            dst.parent.mkdir(parents=True, exist_ok=True)

            status = "restored"
            if dst.exists() and dst.is_file():
                if self._hash_file(dst) == entry["sha256"]:
                    status = "already_present"
                else:
                    shutil.copy2(src, dst)
            else:
                shutil.copy2(src, dst)

            self.restored_files.append({
                "relative_path": entry["relative_path"],
                "destination": str(dst),
                "sha256": entry["sha256"],
                "verification_status": status,
            })
            self._progress(15 + int((i / total) * 55), f"Restoring files… ({i}/{total})")

        self.logger.info("File restore complete: %d entries", len(entries))

    def _verify_files(self, manifest: dict) -> None:
        entries = manifest.get("entries", [])
        total = max(1, len(entries))

        for i, entry in enumerate(entries, start=1):
            path = self._resolve_destination(entry["relative_path"])
            actual = self._hash_file(path)
            status = "match" if actual == entry["sha256"] else "mismatch"
            if status == "mismatch":
                self.logger.error("Hash mismatch: %s", path)

            for item in self.restored_files:
                if item["relative_path"] == entry["relative_path"]:
                    item["verification_status"] = status
                    item["actual_sha256"] = actual
                    break

            self._progress(70 + int((i / total) * 12), f"Verifying… ({i}/{total})")

        mismatches = sum(1 for f in self.restored_files if f.get("verification_status") == "mismatch")
        if mismatches:
            self.logger.warning("%d hash mismatch(es) after restore", mismatches)
        else:
            self.logger.info("All files verified intact")

    @staticmethod
    def _hash_file(path: Path) -> str:
        h = hashlib.sha256()
        try:
            with path.open("rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
        except OSError:
            return ""
        return h.hexdigest()

    # ── Settings restoration ──────────────────────────────────────────────────

    def _detect_desktop_env(self) -> str:
        """Return a normalised desktop environment name from environment variables."""
        raw = (
            os.environ.get("XDG_CURRENT_DESKTOP", "")
            or os.environ.get("DESKTOP_SESSION", "")
        ).lower()
        for name in ("cinnamon", "gnome", "xfce", "kde", "plasma", "mate", "lxde", "budgie"):
            if name in raw:
                return "kde" if name == "plasma" else name
        return raw or "unknown"

    def _run_cmd(self, cmd: list[str]) -> bool:
        """Run a shell command silently; return True on success."""
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=15)
            return result.returncode == 0
        except Exception as exc:
            self.logger.debug("Command %s failed: %s", cmd, exc)
            return False

    def _apply_wallpaper(self, wallpaper_path: Path, de: str) -> bool:
        """Set the desktop wallpaper using the appropriate DE command."""
        uri = wallpaper_path.as_uri()
        path_str = str(wallpaper_path)
        commands = _DE_WALLPAPER.get(de, [])

        if not commands:
            # KDE uses a D-Bus script
            if de == "kde":
                script = (
                    f'var desktops = desktops();'
                    f'for (var i = 0; i < desktops.length; i++) {{'
                    f'  var d = desktops[i];'
                    f'  d.wallpaperPlugin = "org.kde.image";'
                    f'  d.currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];'
                    f'  d.writeConfig("Image", "{path_str}");'
                    f'}}'
                )
                return self._run_cmd([
                    "qdbus", "org.kde.plasmashell", "/PlasmaShell",
                    "org.kde.PlasmaShell.evaluateScript", script,
                ])
            return False

        success = False
        for template in commands:
            cmd = [
                part.replace("{uri}", uri).replace("{path}", path_str)
                for part in template
            ]
            if self._run_cmd(cmd):
                success = True
        return success

    def _apply_color_scheme(self, prefer_dark: bool, de: str) -> bool:
        """Set light or dark theme using the appropriate DE command."""
        cmd = (_DE_DARK_THEME if prefer_dark else _DE_LIGHT_THEME).get(de)
        return self._run_cmd(cmd) if cmd else False

    def _restore_settings(self) -> None:
        """Apply desktop settings from the bundle: wallpaper, light/dark, guidance file."""
        if not self.settings_inv_path.exists():
            self.logger.info("No settings_inventory.json in bundle — skipping settings restore.")
            return

        try:
            inventory = json.loads(self.settings_inv_path.read_text(encoding="utf-8"))
        except Exception as exc:
            self.logger.warning("Could not read settings inventory: %s", exc)
            return

        plan_items: dict[str, str] = {}
        if self.settings_plan_path.exists():
            try:
                plan = json.loads(self.settings_plan_path.read_text(encoding="utf-8"))
                plan_items = {
                    item["name"]: item["action"]
                    for item in plan.get("items", [])
                    if isinstance(item, dict)
                }
            except Exception:
                pass

        de = self._detect_desktop_env()
        self.logger.info("Desktop environment detected: %s", de)

        applied: list[str] = []
        manual: list[str] = []

        # ── Wallpaper ────────────────────────────────────────────────────────
        wallpaper_action = plan_items.get("Wallpaper", "auto_migrate")
        if wallpaper_action not in ("exclude",) and self.settings_assets_dir.exists():
            candidates = sorted(self.settings_assets_dir.glob("wallpaper.*"))
            if candidates:
                src = candidates[0]
                dst = Path.home() / ".local" / "share" / "backgrounds" / src.name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                self.logger.info("Wallpaper copied to %s", dst)

                if self._apply_wallpaper(dst, de):
                    applied.append(f"Wallpaper set from {src.name}")
                    self.logger.info("Wallpaper applied via %s", de)
                else:
                    manual.append(
                        f"Wallpaper — file saved to `{dst}`. "
                        f"Open System Settings → Background to apply it."
                    )
            else:
                self.logger.info("No wallpaper file found in settings_assets/")

        # ── Light / Dark preference ──────────────────────────────────────────
        appearance = inventory.get("appearance", {}) if isinstance(inventory, dict) else {}
        apps_light = appearance.get("apps_use_light_theme")
        sys_light = appearance.get("system_uses_light_theme")

        if apps_light is not None or sys_light is not None:
            prefer_dark = not bool(apps_light if apps_light is not None else sys_light)
            pref_label = "Dark" if prefer_dark else "Light"
            ld_action = plan_items.get("Light/Dark Preference", "suggest_review")

            if ld_action not in ("exclude",):
                if self._apply_color_scheme(prefer_dark, de):
                    applied.append(f"Color scheme: {pref_label} mode applied via {de}")
                    self.logger.info("Color scheme (%s) applied", pref_label)
                else:
                    manual.append(
                        f"Color scheme: Windows used **{pref_label}** mode. "
                        f"Set it in System Settings → Themes."
                    )

        # ── Accent color (guidance only — not automatable portably) ──────────
        accent = appearance.get("accent_color")
        if accent:
            manual.append(
                f"Accent color: Windows value `{accent}`. "
                f"Pick a close match in System Settings → Themes → Accent color."
            )

        # ── Theme name (guidance only — .theme files are not portable) ───────
        theme_val = appearance.get("current_theme", "")
        if theme_val:
            theme_name = Path(theme_val).stem
            manual.append(
                f"Windows theme: **{theme_name}**. "
                f"Windows `.theme` files are not compatible with Linux. "
                f"Browse available themes in System Settings → Themes."
            )

        # ── Write guidance file to home directory ────────────────────────────
        guidance = [
            "# Settings Migration Guidance",
            "",
            f"Desktop environment: **{de}**",
            "",
        ]

        if applied:
            guidance += ["## Applied automatically", ""]
            guidance += [f"- {a}" for a in applied]
            guidance += [""]

        if manual:
            guidance += ["## Needs manual setup", ""]
            guidance += [f"- {m}" for m in manual]
            guidance += [""]

        guidance += [
            "---",
            "_Generated by the Migration Tool during restore._",
        ]

        guidance_path = Path.home() / "settings_migration_guidance.md"
        try:
            guidance_path.write_text("\n".join(guidance), encoding="utf-8")
            self.settings_guidance_path = str(guidance_path)
            self.logger.info("Settings guidance written to %s", guidance_path)
        except OSError as exc:
            self.logger.warning("Could not write guidance file: %s", exc)

        self.settings_applied = applied
        self.logger.info(
            "Settings restore: %d applied automatically, %d need manual setup",
            len(applied), len(manual),
        )

    # ── Application installation ──────────────────────────────────────────────

    def _load_applications(self, path: Path) -> dict:
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    def _install_applications(self) -> None:
        applications = self._load_applications(self.apps_path)
        self.apps_to_install = applications.get("applications", [])

        packages = [
            app["linux_package"]
            for app in self.apps_to_install
            if app.get("migration_strategy") in {"apt", "dnf", "pacman", "install linux equivalent"}
            and app.get("linux_package")
        ]

        if not packages:
            self.logger.info("No installable packages found in apps_to_install.json")
            return

        manager = detect_package_manager(self.target_distro)
        self._progress(90, f"Installing {len(packages)} packages via {manager}…")
        result = install_packages(packages, manager=manager, use_pkexec=True)
        self.installed_apps = self.apps_to_install
        self.logger.info("Package installation complete. Output: %s", result.stdout)

    # ── Restore report ────────────────────────────────────────────────────────

    def _write_restore_report(self) -> None:
        report = {
            "files_restored": self.restored_files,
            "applications_installed": self.installed_apps,
            "settings_applied": self.settings_applied,
            "settings_guidance": self.settings_guidance_path,
        }
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        with self.report_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        self.logger.info("Restore report written to %s", self.report_path)
