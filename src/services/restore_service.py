from pathlib import Path
import json
import zipfile
import hashlib
import shutil
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

# logger = logging.getLogger("restore")


ProgressCb = Callable[[int, str], None]


class RestoreService:
    """
    Linux-side restoration:
    - Extract backup archive
    - Restore files to home directory
    - Verify file integrity
    - Install selected applications using pkexec
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

        self.manifest_path = bundle_dir / "manifest.json"
        self.archive_path = bundle_dir / "backup.zip"
        self.apps_path = bundle_dir / "apps_to_install.json"

        self.apps_to_install = []
        self.target_distro = target_distro

        self.restored_files = []
        self.installed_apps = []
        self.report_path = RESTORE_REPORT


    def _progress(self, percent: int, msg: str):
        if self.progress_cb:
            self.progress_cb(max(0, min(100, int(percent))), msg)

    # -------------------------
    # PUBLIC ENTRY POINT
    # -------------------------
    def run_restore(self):
        self._validate_bundle()
        self._progress(0, "Loading manifest…")
        manifest = self._load_manifest()

        self._progress(5, "Extracting backup archive…")
        extract_dir = self._extract_backup()

        self._progress(15, "Restoring files…")
        self._restore_files(manifest, extract_dir)

        self._progress(75, "Verifying file integrity…")
        self._verify_files(manifest)

        if self.apps_path.exists():
            self._progress(90, "Installing applications…")
            self._install_applications()

        self._write_restore_report()

        self._progress(100, "Restore completed.")

    def _validate_bundle(self) -> None:
        if not self.manifest_path.exists() or not self.archive_path.exists():
            raise MigrationError(ERR_MISSING_BUNDLE, str(self.bundle_dir))


    def _write_restore_report(self):
        report = {
            "files_restored": self.restored_files,
            "applications_installed": self.installed_apps,
        }

        with self.report_path.open("w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        self.logger.info("Restore report written to %s", self.report_path)


    # -------------------------
    # PATH RESOLUTION
    # -------------------------
    def _resolve_destination(self, relative_path: str) -> Path:
        """Map a backup relative_path to its Linux destination.

        The first path component is the original Windows folder name (e.g. 'Documents').
        Known Windows user-folders are translated to their Linux home equivalents so
        files land in ~/Documents, ~/Pictures, etc. rather than ~/Restored_Migration/.
        Unknown folders fall back to target_home/<folder_name>/.
        """
        parts = Path(relative_path).parts
        if not parts:
            return self.target_home

        top = parts[0]
        linux_name = _WIN_FOLDER_MAP.get(top.lower())
        base = Path.home() / linux_name if linux_name else self.target_home / top

        rest = parts[1:]
        return base.joinpath(*rest) if rest else base

    # -------------------------
    # FILE RESTORE
    # -------------------------
    def _load_manifest(self) -> dict:
        with self.manifest_path.open(encoding="utf-8") as f:
            return json.load(f)

    def _extract_backup(self) -> Path:
        extract_dir = EXTRACTED_BACKUP_DIR

        if extract_dir.exists():
            shutil.rmtree(extract_dir)

        extract_dir.mkdir(parents=True)

        with zipfile.ZipFile(self.archive_path, "r") as zf:
            for member in zf.infolist():
                # Zip Slip protection
                target_path = (extract_dir / member.filename).resolve()
                if not str(target_path).startswith(str(extract_dir.resolve())):
                    raise MigrationError(ERR_ARCHIVE_UNSAFE_PATH, member.filename)
                if member.is_dir():
                    target_path.mkdir(parents=True, exist_ok=True)
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member, "r") as src, target_path.open("wb") as dst:
                        shutil.copyfileobj(src, dst)

        self.logger.info("Backup archive extracted")
        return extract_dir

    def _restore_files(self, manifest: dict, extract_dir: Path):
        entries = manifest.get("entries", [])
        total = max(1, len(entries))

        for i, entry in enumerate(entries, start=1):
            src = extract_dir / entry["relative_path"]
            dst = self._resolve_destination(entry["relative_path"])

            dst.parent.mkdir(parents=True, exist_ok=True)

            verification_status = "restored"
            if dst.exists() and dst.is_file():
                current_hash = self._hash_file(dst)
                if current_hash == entry["sha256"]:
                    verification_status = "already_present"
                else:
                    shutil.copy2(src, dst)
            else:
                shutil.copy2(src, dst)

            self.restored_files.append({
                "relative_path": entry["relative_path"],
                "destination": str(dst),
                "sha256": entry["sha256"],
                "verification_status": verification_status,
            })

            pct = 15 + int((i / total) * 55)
            self._progress(pct, f"Restoring files… ({i}/{total})")

        self.logger.info("Files restored to home directory")

    def _verify_files(self, manifest: dict):
        entries = manifest.get("entries", [])
        total = max(1, len(entries))

        for i, entry in enumerate(entries, start=1):
            path = self._resolve_destination(entry["relative_path"])
            expected = entry["sha256"]

            actual = self._hash_file(path)
            status = "match"
            if actual != expected:
                status = "mismatch"
                self.logger.error("Hash mismatch for %s: expected %s, got %s", path, expected, actual)

            for item in self.restored_files:
                if item.get("relative_path") == entry["relative_path"]:
                    item["verification_status"] = status
                    item["actual_sha256"] = actual
                    break
                
            # map verify phase into 75%..89%
            pct = 75 + int((i / total) * 14)
            self._progress(pct, f"Verifying… ({i}/{total})")

        mismatches = [f for f in self.restored_files if f.get("verification_status") == "mismatch"]
        if mismatches:
            self.logger.warning("File integrity completed with %d mismatch(es)", len(mismatches))
        else:
            self.logger.info("File integrity verified")

    @staticmethod
    def _hash_file(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _load_applications(self, path: Path) -> str:
        with path.open(encoding="utf-8") as f:
            return json.load(f)

    # -------------------------
    # APPLICATION INSTALLATION
    # -------------------------
    def _install_applications(self):
        applications = self._load_applications(self.apps_path)
        self.apps_to_install = applications.get("applications", [])

        packages = [
            app["linux_package"]
            for app in self.apps_to_install
            if app.get("migration_strategy") in {"apt", "dnf", "pacman", "install linux equivalent"}
            and app.get("linux_package")
        ]

        if not packages:
            self.logger.info("No applications to install")
            self._progress(100, "Restore completed.")
            return

        manager = detect_package_manager(self.target_distro)
        self._progress(90, f"Installing {len(packages)} applications with {manager}…")
        result = install_packages(packages, manager=manager, use_pkexec=True)

        self.logger.info("Applications installed")
        self.installed_apps = self.apps_to_install
        self.logger.info("Package manager output: %s", result.stdout)

