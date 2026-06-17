"""Windows .exe/.ico icon extraction for embedding in migration reports.

Only functional on Windows with pywin32 and Pillow installed — both are
optional dependencies, so this module degrades to a no-op elsewhere.
"""

from __future__ import annotations

from pathlib import Path

from src.loggers import get_logger

logger = get_logger("services.icon_extractor")

try:
    import win32gui
    import win32ui
    import win32api
    import win32con
    from PIL import Image
    _ICON_SUPPORT = True
except ImportError:
    _ICON_SUPPORT = False


def _hicon_to_pil(hicon, size: int) -> "Image.Image":
    hdc_screen = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
    hbmp = win32ui.CreateBitmap()
    hbmp.CreateCompatibleBitmap(hdc_screen, size, size)
    hdc_mem = hdc_screen.CreateCompatibleDC()
    hdc_mem.SelectObject(hbmp)
    hdc_mem.DrawIcon((0, 0), hicon)

    info = hbmp.GetInfo()
    bits = hbmp.GetBitmapBits(True)
    image = Image.frombuffer(
        "RGBA",
        (info["bmWidth"], info["bmHeight"]),
        bits,
        "raw",
        "BGRA",
        0,
        1,
    )
    win32gui.DeleteObject(hbmp.GetHandle())
    hdc_mem.DeleteDC()
    hdc_screen.DeleteDC()
    return image


def extract_icon_png(icon_source: str, dest_path: Path, size: int = 64) -> bool:
    """Extract an icon from a Windows ``DisplayIcon``-style path and save as PNG.

    ``icon_source`` may be a bare path to a .exe/.ico/.dll, or a path suffixed
    with ",N" indicating a resource index. Returns True on success.
    """
    if not _ICON_SUPPORT or not icon_source:
        return False

    raw = str(icon_source).strip().strip('"')
    index = 0
    if "," in raw:
        path_part, _, idx_part = raw.rpartition(",")
        try:
            index = int(idx_part.strip())
            raw = path_part.strip().strip('"')
        except ValueError:
            pass

    source_path = Path(raw)
    if not source_path.exists():
        return False

    try:
        if source_path.suffix.lower() == ".ico":
            image = Image.open(source_path).convert("RGBA")
        else:
            large, small = win32gui.ExtractIconEx(str(source_path), index, 1)
            hicon = (large or small or [None])[0]
            if not hicon:
                return False
            try:
                image = _hicon_to_pil(hicon, size)
            finally:
                for handle in set((large or []) + (small or [])):
                    win32gui.DestroyIcon(handle)

        image = image.resize((size, size), Image.LANCZOS)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(dest_path, format="PNG")
        return True
    except Exception as exc:
        logger.debug("Icon extraction failed for %s: %s", icon_source, exc)
        return False
