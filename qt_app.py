"""Alternate launcher for the Qt-based migration application."""

import platform

from src.config import load_config
from src.constants import CONFIG_DIR
from src.qt_ui.app import run_qt_app


def detect_runtime_environment() -> str:
    """Detect the current OS and map it to the supported runtime mode."""
    system_platform = platform.system().lower()
    if system_platform == "windows":
        return "windows"
    if system_platform == "linux":
        return "linux"
    raise RuntimeError(f"Unsupported platform: {system_platform}")


def main() -> None:
    """Load configuration and launch the Qt application."""
    runtime_env = detect_runtime_environment()
    cfg = load_config(CONFIG_DIR / "migration.config.yaml")
    run_qt_app(cfg, runtime_env)


if __name__ == "__main__":
    main()
