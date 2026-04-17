"""
cli.py

Top-level command-line interface for the
"Semi-Automated Migration from Windows 11 to Linux Mint" project.

This CLI integrates the components developed in M2 into a single,
coherent interface and prepares the ground for further automation
in M3 and later milestones.

Provided commands (current stage):

- inventory
    - hardware
    - software
    - all
- analyze
    - hardware
    - software
    - all
- backup
- validate      (stub for future implementation)
- restore       (stub for future implementation)
- usb           (stub for future Live USB integration)

The CLI uses Typer for structured subcommands and integrates the
configuration file (migration.config.yaml) and centralized logging.
"""

from __future__ import annotations

import getpass
import logging
from pathlib import Path
from typing import Optional

import typer

from src.constants import BASE_DIR, DATA_DIR
from src.loggers import get_logger
from src.config import load_default_config, load_config, MigrationConfigRoot
from src.inventory.hardware import (
    collect_hardware_inventory,
    write_hardware_inventory,
)
from src.inventory.software import (
    collect_software_inventory,
    write_software_inventory,
)
# from src.backup.manifest import generate_manifest, write_manifest
from src.backup.manifest import copy_backup_files, generate_manifest, write_manifest
from src.analysis.hw_matrix import (
    generate_hardware_matrix,
    write_hardware_matrix,
    _load_hardware_inventory,
)
from src.analysis.software_mapping import (
    generate_software_mapping,
    write_software_mapping,
    _load_software_inventory,
)


# ---------------------------------------------------------------------------
# CLI app and logging
# ---------------------------------------------------------------------------

app = typer.Typer(help="Semi-automated migration framework CLI")

inventory_app = typer.Typer(help="Inventory-related commands (hardware, software)")
analyze_app = typer.Typer(help="Analysis commands (hardware matrix, software mapping)")

app.add_typer(inventory_app, name="inventory")
app.add_typer(analyze_app, name="analyze")

# logger = logging.getLogger("semi_migrate")
# logger.setLevel(logging.INFO)
logger = get_logger("cli")



def resolve_windows_user(config):
    return config.source_system.windows_user or getpass.getuser()


def setup_logging(config: MigrationConfigRoot) -> None:
    """
    Configure logging based on configuration file settings.

    At this stage, logging is still relatively simple, but this function
    serves as the central place for all logging-related behaviour.
    """
    if logger.handlers:
        return

    level_name = getattr(config.automation, "logging_level", "INFO")
    level = getattr(logging, str(level_name).upper(), logging.INFO)
    logging.getLogger().setLevel(level)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.setLevel(level)
    logger.addHandler(handler)


def load_configuration(config_path: Optional[Path]) -> MigrationConfigRoot:
    """
    Load configuration from given path or use default.
    """
    try:
        config_path = config_path.resolve() if config_path else None
        cfg = load_config(str(config_path)) if config_path else load_default_config()
        setup_logging(cfg)
        return cfg
    except Exception as exc:
        logger.error("Invalid configuration path: %s", exc)
        typer.echo("ERROR: Invalid configuration file.")
        raise typer.Exit(code=1)
    
    
# ---------------------------------------------------------------------------
# INVENTORY COMMANDS
# ---------------------------------------------------------------------------

@inventory_app.command("hardware")
def inventory_hardware(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to migration.config.yaml"
    )
) -> None:
    """
    Run hardware inventory and write hardware_inventory.json.
    """
    cfg = load_configuration(config)
    logger.info("Starting hardware inventory...")
    inv = collect_hardware_inventory()
    out_file = write_hardware_inventory(cfg, inv)
    logger.info("Hardware inventory written to %s", out_file)


@inventory_app.command("software")
def inventory_software(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to migration.config.yaml"
    )
) -> None:
    """
    Run software inventory and write software_inventory.json.
    """
    cfg = load_configuration(config)
    logger.info("Starting software inventory...")
    inv = collect_software_inventory()
    out_file = write_software_inventory(cfg, inv)
    logger.info("Software inventory written to %s", out_file)


@inventory_app.command("all")
def inventory_all(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to migration.config.yaml"
    )
) -> None:
    """
    Run both hardware and software inventories.
    """
    cfg = load_configuration(config)
    logger.info("Running full inventory (hardware + software)...")

    inv_h = collect_hardware_inventory()
    out_h = write_hardware_inventory(cfg, inv_h)
    logger.info("Hardware inventory written to %s", out_h)

    inv_s = collect_software_inventory()
    out_s = write_software_inventory(cfg, inv_s)
    logger.info("Software inventory written to %s", out_s)


# ---------------------------------------------------------------------------
# BACKUP COMMAND
# ---------------------------------------------------------------------------

@app.command("backup")
def backup_command(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to migration.config.yaml"
    ),
    confirm: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmation prompt and proceed directly.",
    ),
) -> None:
    """
    Generate backup manifest for configured backup paths.

    This command does NOT perform the actual copy to external media.
    It creates manifest.json containing file paths, sizes, and hashes
    as a basis for later backup and integrity checks.
    """
    cfg = load_configuration(config)

    if not confirm:
        proceed = typer.confirm(
            "This will scan all configured backup paths and compute SHA-256 hashes. "
            "This may take some time. Continue?"
        )
        if not proceed:
            typer.echo("Aborted by user.")
            raise typer.Exit(code=1)

    logger.info("Starting backup manifest generation...")

    try:
        manifest = generate_manifest(cfg)
        
        out_file = write_manifest(cfg, manifest)
        logger.info("Backup manifest written to %s", out_file)
        copy_backup_files(manifest, cfg)
    except Exception as exc:
        logger.exception("Backup command failed: %s", exc)
        typer.echo("ERROR: Backup failed. See logs for details.")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# ANALYSIS COMMANDS
# ---------------------------------------------------------------------------

@analyze_app.command("hardware")
def analyze_hardware(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to migration.config.yaml"
    ),
    inventory_filename: str = typer.Option(
        "hardware_inventory.json",
        help="Name of hardware inventory file in inventory_output_dir.",
    ),
) -> None:
    """
    Generate hardware compatibility matrix from hardware inventory.
    """
    cfg = load_configuration(config)
    inv_dir = DATA_DIR / cfg.source_system.inventory_output_dir
    inv_path = inv_dir / inventory_filename

    logger.info("Loading hardware inventory from %s", inv_path)
    inventory = _load_hardware_inventory(inv_path)

    rows = generate_hardware_matrix(cfg, inventory)
    out_file = write_hardware_matrix(cfg, rows)
    logger.info("Hardware compatibility matrix written to %s", out_file)


@analyze_app.command("software")
def analyze_software(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to migration.config.yaml"
    ),
    inventory_filename: str = typer.Option(
        "software_inventory.json",
        help="Name of software inventory file in inventory_output_dir.",
    ),
) -> None:
    """
    Generate software mapping table from software inventory.
    """
    cfg = load_configuration(config)
    inv_dir = DATA_DIR / cfg.source_system.inventory_output_dir
    inv_path = inv_dir / inventory_filename

    logger.info("Loading software inventory from %s", inv_path)
    entries = _load_software_inventory(inv_path)

    rows = generate_software_mapping(cfg, entries)
    out_file = write_software_mapping(rows)
    logger.info("Software mapping table written to %s", out_file)


@analyze_app.command("all")
def analyze_all(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to migration.config.yaml"
    )
) -> None:
    """
    Run both hardware and software analysis steps.
    """
    cfg = load_configuration(config)

    inv_dir = DATA_DIR / cfg.source_system.inventory_output_dir

    # Hardware
    hw_path = inv_dir / "hardware_inventory.json"
    logger.info("Loading hardware inventory from %s", hw_path)
    hw_inv = _load_hardware_inventory(hw_path)
    hw_rows = generate_hardware_matrix(cfg, hw_inv)
    hw_out = write_hardware_matrix(cfg, hw_rows)
    logger.info("Hardware compatibility matrix written to %s", hw_out)

    # Software
    sw_path = inv_dir / "software_inventory.json"
    logger.info("Loading software inventory from %s", sw_path)
    sw_entries = _load_software_inventory(sw_path)
    sw_rows = generate_software_mapping(cfg, sw_entries)
    sw_out = write_software_mapping(sw_rows)
    logger.info("Software mapping table written to %s", sw_out)


# ---------------------------------------------------------------------------
# VALIDATE COMMAND (stub for future extension)
# ---------------------------------------------------------------------------

@app.command("validate")
def validate_command(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to migration.config.yaml"
    ),
) -> None:
    """
    Validate post-migration system state (stub).

    Future work (Milestone M4 and M5) will implement:
    - Verification of restored files against manifest.json (hash comparison)
    - Basic system checks: network, audio, GPU driver readiness
    - Video playback validation (codec availability)
    - Office suite readiness (LibreOffice available and functional)
    """
    cfg = load_configuration(config)

    logger.info("Validation command invoked (stub mode).")
    typer.echo(
        "validate: This feature is not implemented yet.\n"
        "Planned functionality includes:\n"
        "1. Compare restored files against manifest.json (SHA-256).\n"
        "2. Run network connectivity tests.\n"
        "3. Validate audio output and microphone.\n"
        "4. Check GPU driver readiness and acceleration.\n"
        "5. Validate video playback (H.264, MP4).\n"
        "6. Confirm office suite availability and functionality.\n"
        "7. Produce a structured validation report.\n"
    )

# ---------------------------------------------------------------------------
# RESTORE COMMAND (stub for future extension)
# ---------------------------------------------------------------------------

@app.command("restore")
def restore_command(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to migration.config.yaml"
    ),
    source: Optional[Path] = typer.Option(
        None,
        "--source",
        help="Path to the mounted backup location on Linux (e.g. /mnt/backup).",
    ),
) -> None:
    """
    Restore data from backup location to the Linux home directory (stub).

    Future work (Milestone M4 and M5) will implement:
    - Reading manifest.json
    - Restoring files with rsync or a Python copy mechanism
    - Rebuilding directory structures under /home/<user>
    - Handling permissions and ownership
    - Running hash validation to ensure correctness
    """
    cfg = load_configuration(config)

    logger.info("Restore command invoked (stub mode).")
    typer.echo(
        "restore: This feature is not implemented yet.\n"
        "Planned functionality:\n"
        "1. Load manifest.json from backup.\n"
        "2. Validate backup source path (--source).\n"
        "3. Reconstruct directory structure in /home/<user>.\n"
        "4. Copy files from backup to target system.\n"
        "5. Verify file integrity via SHA-256.\n"
        "6. Produce a restore report.\n"
    )


# ---------------------------------------------------------------------------
# USB COMMAND (stub for future Live USB integration)
# ---------------------------------------------------------------------------

@app.command("usb")
def usb_command(
    iso: Optional[Path] = typer.Option(
        None,
        "--iso",
        help="Path to the Linux Mint ISO image (e.g. linuxmint-21.3-cinnamon-64bit.iso).",
    ),
    device: Optional[str] = typer.Option(
        None,
        "--device",
        help="Identifier of the target USB device (e.g. /dev/sdX on Linux or drive letter on Windows).",
    ),
) -> None:
    """
    Prepare or assist in preparing a Linux Mint Live USB that includes this
    migration framework (stub implementation).

    Future work (Milestones M4/M5) may:
    - Automate USB imaging on Linux (e.g., using 'dd' or 'cp' with safety checks).
    - Copy the migration tool onto the Live USB.
    - Optionally add helper scripts for easier execution after boot.

    For now, this command validates the inputs and prints step-by-step
    instructions for manual USB creation using standard tools.
    """
    logger.info("USB command invoked (stub mode).")

    typer.echo("usb: Live USB integration is not implemented yet.")
    typer.echo()
    typer.echo("Planned future functionality:")
    typer.echo("1. Verify the provided Linux Mint ISO.")
    typer.echo("2. Safely write the ISO to the specified USB device.")
    typer.echo("3. Copy this migration framework onto the USB.")
    typer.echo("4. Provide a helper script to run after boot.")
    typer.echo()

    typer.echo("For now, please follow these manual steps:")

    if iso is not None:
        typer.echo(f"- ISO file provided: {iso}")
    else:
        typer.echo("- No ISO file was specified. Download a Linux Mint ISO from the official website.")

    if device is not None:
        typer.echo(f"- Target device hint: {device}")
    else:
        typer.echo("- No device identifier provided. Identify your USB stick using your OS tools.")

    typer.echo()
    typer.echo("On Windows (recommended):")
    typer.echo("  1. Download and open Rufus (rufus.ie).")
    typer.echo("  2. Select the Linux Mint ISO.")
    typer.echo("  3. Select your USB device.")
    typer.echo("  4. Start the imaging process.")
    typer.echo("  5. After imaging, copy this project folder onto the USB stick.")
    typer.echo()
    typer.echo("On Linux:")
    typer.echo("  1. Identify your USB device using 'lsblk'.")
    typer.echo("  2. Use 'dd' or 'cp' to write the ISO to the USB (with extreme care).")
    typer.echo("  3. Mount the USB and copy this migration project onto it.")
    typer.echo()
    typer.echo("This stub provides the interface and documentation for future automation.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app()


if __name__ == "__main__":
    main()
