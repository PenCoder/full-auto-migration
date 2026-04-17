# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

import logging
import platform

from .constants import LOGS_DIR

def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger with standardized formatting.
    Ensures that handlers are only added once.
    """
    system_platform = platform.system().lower()
    if system_platform == "windows":
        action = "migrate"
    elif system_platform == "linux":
        action = "restore"
    else:
        raise RuntimeError(f"Unsupported platform: {system_platform}")
    
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"{action}.log"

    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
