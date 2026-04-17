import platform
from src.config import load_config
from src.ui.wizard import MigrationWizard


def detect_runtime_environment() -> None:
    system_platform = platform.system().lower()
    if system_platform == "windows":
        return "windows"
    elif system_platform == "linux":
        return "linux"
    raise RuntimeError(f"Unsupported platform: {system_platform}")
        

def main():
    runtime_env = detect_runtime_environment()
    cfg = load_config("configs/migration.config.yaml")
    app = MigrationWizard(cfg, runtime_env)
    app.mainloop()

if __name__ == "__main__":
    main()