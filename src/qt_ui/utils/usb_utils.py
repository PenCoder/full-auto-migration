"""Removable drive detection for Windows."""

from __future__ import annotations

import shutil
import string
from pathlib import Path


def detect_usb_drives() -> list[dict]:
    """Return removable drives available on the system.

    Uses the Windows kernel32 API via ctypes — no third-party packages needed.
    Returns an empty list on non-Windows platforms or when no drives are found.

    Each entry:
        letter   — drive letter (e.g. "E")
        path     — root path string (e.g. "E:\\")
        label    — volume label (e.g. "Kingston")
        free_gb  — free space in GB (float)
        total_gb — total size in GB (float)
        display  — formatted string for combo-box display
    """
    try:
        import ctypes
    except ImportError:
        return []

    try:
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    except AttributeError:
        return []

    drives: list[dict] = []
    for letter in string.ascii_uppercase:
        root = f"{letter}:\\"
        if not Path(root).exists():
            continue
        # GetDriveTypeW returns 2 for DRIVE_REMOVABLE
        if kernel32.GetDriveTypeW(root) != 2:
            continue
        try:
            total, _, free = shutil.disk_usage(root)
        except OSError:
            continue

        label_buf = ctypes.create_unicode_buffer(256)
        kernel32.GetVolumeInformationW(root, label_buf, 256, None, None, None, None, 0)
        label = label_buf.value.strip() or "USB Drive"
        free_gb = round(free / (1024 ** 3), 1)
        total_gb = round(total / (1024 ** 3), 1)
        drives.append({
            "letter": letter,
            "path": root,
            "label": label,
            "free_gb": free_gb,
            "total_gb": total_gb,
            "display": f"{letter}:\\  —  {label}  ({free_gb} GB free of {total_gb} GB)",
        })
    return drives


def copy_bundle_to_usb(bundle_archive: Path, usb_root: str) -> Path:
    """Copy the migration bundle archive (a single .zip) to a USB drive.

    Copies *bundle_archive* to ``<usb_root>/<archive name>``, removing any
    previous copy first. Returns the destination path.
    """
    dest = Path(usb_root) / bundle_archive.name
    if dest.exists():
        dest.unlink()
    shutil.copy2(bundle_archive, dest)
    return dest
