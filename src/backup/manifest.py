"""
Backup manifest generator for the
"Semi-Automated Migration from Windows 11 to Linux Mint" project.

This module performs the following tasks:
1. Load the project configuration.
2. Determine backup source paths and exclusion paths.
3. Recursively enumerate all files from the configured backup_paths.
4. Compute SHA-256 hashes for each file (binary-safe, chunked).
5. Produce a structured manifest JSON including:
   - file path (absolute and relative)
   - file size
   - SHA-256 hash
   - timestamp
6. Save the manifest to the configured backup_output_dir.

The manifest is later used for:
- Data restoration
- Post-installation integrity verification
- Research evaluation in Milestone M4 (Validation)

This module must be executed on Windows, because the backup paths refer
to the Windows filesystem.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
import shutil
from typing import Dict, List, Any, Optional
import zipfile

from src.constants import BASE_DIR, DATA_DIR, RESTORE_DIR
from src.loggers import get_logger
from src.config import load_default_config, load_config, MigrationConfigRoot


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = get_logger("backup.manifest")


# ---------------------------------------------------------------------------
# File hashing
# ---------------------------------------------------------------------------

def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """
    Compute SHA-256 checksum for a file using chunked reads
    to support large files safely.

    Parameters
    ----------
    path : Path
        Path to the file to hash.
    chunk_size : int, optional
        Size of read buffer, by default 1MB.

    Returns
    -------
    str
        Hexadecimal SHA-256 digest.

    Raises
    ------
    OSError
        If the file cannot be opened or read.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Manifest generation
# ---------------------------------------------------------------------------

def _enumerate_backup_files(
    include_paths: List[str],
    accepted_extensions: set[str],
) -> List[Path]:
    """
    Enumerate files to be included in the backup, respecting exclusions.

    Parameters
    ----------
    include_paths : List[str]
        List of root directories to include.
    accepted_extensions : set[str]
        Set of accepted file extensions (lowercase, with dot, e.g. ".docx").

    Returns
    -------
    List[Path]
        List of file paths to be included.
    """
    include_dirs = [Path(p).expanduser() for p in include_paths]

    all_files: List[Path] = []

    for directory in include_dirs:
        if not directory.exists():
            logger.warning("Backup include path does not exist: %s", directory)
            continue
        
        for file_path in directory.rglob("*"):
            if not file_path.is_file():
                continue
            
            if file_path.suffix.lower() not in accepted_extensions:
                continue

            all_files.append(file_path)

    return all_files


def generate_manifest(config: MigrationConfigRoot) -> Dict[str, Any]:
    """
    Generate the backup manifest.

    Parameters
    ----------
    config : MigrationConfigRoot
        Loaded configuration object.

    Returns
    -------
    Dict[str, Any]
        Manifest dictionary containing:
        - timestamp
        - total_files
        - entries: list of {source_path, relative_path, size, sha256}
    """
    logger.info("Generating backup manifest...")

    include_paths = config.source_system.backup_paths
    file_types = config.source_system.file_types
    accepted_extensions = {ft.lower() for ft, selected in file_types.items() if selected}
    file_list = _enumerate_backup_files(include_paths, accepted_extensions)
    
    entries = []
    for file_path in file_list:
        try:
            sha256 = _sha256_file(file_path)
            size = file_path.stat().st_size
            
            # relative path inside the backup hierarchy
            # computed relative to the FIRST include_path that matches
            rel = None
            for root in include_paths:
                root_p = Path(root)
                try:
                    rel = file_path.relative_to(root_p)
                    break
                except ValueError:
                    continue
            if rel is None:
                # fallback: use name only
                rel = file_path.name

            entries.append({
                "source_path": str(file_path),
                "relative_path": str(rel),
                "size_bytes": size,
                "sha256": sha256,
            })
        except Exception as e:
            logger.error("Failed to process file: %s (%s)", file_path, e)

    manifest = {
        "timestamp": datetime.now().isoformat(timespec="seconds") + "Z",
        "total_files": len(entries),
        "entries": entries,
    }

    logger.info("Manifest generation complete. Total files: %d", len(entries))
    return manifest


def write_manifest(config: MigrationConfigRoot, manifest: Dict[str, Any]) -> Path:
    """
    Write manifest JSON to backup_output_dir.

    Parameters
    ----------
    config : MigrationConfigRoot
        Config specifying output directory.
    manifest : Dict[str, Any]
        Manifest generated by generate_manifest().

    Returns
    -------
    Path
        Path to the written manifest file.
    """
    out_dir = RESTORE_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    out_path = out_dir / "manifest.json"

    logger.info("Writing manifest to: %s", out_path)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return out_path


def copy_backup_files(manifest: dict, cfg: MigrationConfigRoot) -> None:
    """
    Copy all files referenced in manifest['entries'] into files_dir,
    preserving relative paths.
    """
    backup_root = DATA_DIR / cfg.source_system.backup_output_dir
    files_dir = backup_root / "files"
    if files_dir.exists():
        shutil.rmtree(files_dir)
    files_dir.mkdir(parents=True, exist_ok=True)
    
    for entry in manifest["entries"]:
        src = Path(entry["source_path"])
        dest = files_dir / entry["relative_path"]

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            # shutil.copy2(src, dest)
            shutil.copyfile(src, dest)
        except Exception as e:
            print(f"[WARN] Could not copy {src}: {e}")

    logger.info("Copied backup files to: %s", files_dir)


def create_backup_archive(source_dir: Path, archive_path: Path):
    """
    Create a zip archive of the specified source directory.

    :param source_dir: Directory to be archived.
    :param archive_path: Path where the zip archive will be created.
    """
    source_dir = DATA_DIR / source_dir
    archive_path = RESTORE_DIR / archive_path

    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in source_dir.rglob("*"):
            if file.is_file():
                zipf.write(file, file.relative_to(source_dir))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(config_path: Optional[str] = None) -> None:
    """
    CLI entry point for manifest generation.

    Steps:
    1. Setup logging.
    2. Load config.
    3. Generate manifest.
    4. Write manifest.json.
    """
    get_logger(__name__)

    if config_path is None:
        logger.info("Loading default configuration...")
        cfg = load_default_config()
    else:
        logger.info("Loading configuration from: %s", config_path)
        cfg = load_config(config_path)

    manifest = generate_manifest(cfg)
    out_file = write_manifest(cfg, manifest)
    copy_backup_files(manifest, cfg)

    if cfg.backup.compress:
        logger.info("Creating compressed backup archive...")
        backup_root = DATA_DIR / cfg.source_system.backup_output_dir
        archive_path = backup_root / cfg.backup.archive_name
        create_backup_archive(backup_root / "files", archive_path)
        logger.info("Backup archive created at: %s", archive_path)

    logger.info("Backup manifest written to: %s", out_file)


if __name__ == "__main__":
    main()
