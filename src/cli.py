"""
cli.py

Top-level command-line interface for the
"Semi-Automated Migration from Windows 11 to Linux Mint" project.

Commands:

- scan           Run inventory, analysis, and recommendations (--mode guided|balanced|expert)
- inventory      hardware | software | all
- analyze        hardware | software | all
- backup         Bundle selected files and settings for migration
- restore        Extract backup bundle on the Linux target
- validate       Check restore report integrity and produce a validation summary
- report         Generate the final migration report (JSON, Markdown, HTML)
- recommended    Generate software migration recommendations
- profile        Show active configuration profile
- usb            (Live USB integration placeholder)

The CLI uses Typer and integrates migration.config.yaml with centralized logging.
"""

from __future__ import annotations

import getpass
import json
import logging
from pathlib import Path
from typing import Optional

import typer

from src.constants import BASE_DIR, DATA_DIR, RESTORE_DIR
from src.loggers import get_logger
from src.orchestration.mode_policy import (
    resolve_app_recommendation_strategy,
    should_run_analysis,
    should_run_file_recommendations,
)
from src.config import load_default_config, load_config, MigrationConfigRoot
from src.inventory.hardware import (
    collect_hardware_inventory,
    write_hardware_inventory,
)
from src.inventory.settings import (
    collect_settings_inventory,
    write_settings_inventory,
)
from src.inventory.software import (
    collect_software_inventory,
    write_software_inventory,
)
from src.backup.manifest import copy_backup_files, generate_manifest, write_manifest, _JUNK_DIR_NAMES
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
from src.orchestration.errors import MigrationError, user_facing_error
from src.services.validation_service import validate_restore_report
from src.services.profile_service import ProfileService
from src.services.report_service import ReportService
from src.services.file_recommendation_service import FileRecommendationService
from src.services.pipeline_service import PipelineService
from src.services.recommendation_service import RecommendationService


# ---------------------------------------------------------------------------
# CLI app and logging
# ---------------------------------------------------------------------------

app = typer.Typer(help="Semi-automated migration framework CLI")

inventory_app = typer.Typer(help="Inventory-related commands (hardware, software)")
analyze_app = typer.Typer(help="Analysis commands (hardware matrix, software mapping)")
profile_app = typer.Typer(help="Profile commands for saving custom migration preferences")

app.add_typer(inventory_app, name="inventory")
app.add_typer(analyze_app, name="analyze")
app.add_typer(profile_app, name="profile")

# logger = logging.getLogger("semi_migrate")
# logger.setLevel(logging.INFO)
logger = get_logger("cli")


def _handle_cli_error(exc: Exception, action: str) -> None:
    if isinstance(exc, MigrationError):
        logger.exception("%s failed: %s", action, exc)
        typer.echo(f"ERROR during {action}:\n{user_facing_error(str(exc))}")
    else:
        logger.exception("%s failed with unexpected error: %s", action, exc)
        typer.echo(f"ERROR during {action}: {exc}")
        typer.echo("Recovery: Review logs, verify inputs, and retry the command.")
    raise typer.Exit(code=1)



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


def _build_file_inventory(cfg: MigrationConfigRoot, max_files: int = 8000) -> dict:
    """Scan configured backup paths and return a lightweight file inventory dict.

    Applies the same junk-directory blocklist and config-excluded-path filtering
    as the backup manifest generator so CLI and Qt results are consistent.
    """
    import os as _os
    import time as _time

    enabled_exts = {ext.lower() for ext, on in cfg.source_system.file_types.items() if on}
    excluded_paths_abs = [
        Path(p).expanduser() if Path(p).expanduser().is_absolute() else Path.home() / p
        for p in cfg.source_system.excluded_paths
    ]
    now_ts = _time.time()
    files: list[dict] = []
    scanned = 0

    for raw_path in cfg.source_system.backup_paths:
        expanded = Path(raw_path).expanduser()
        if not expanded.exists() or not expanded.is_dir():
            continue
        for root, dirs, filenames in _os.walk(expanded):
            if scanned >= max_files:
                break
            root_path = Path(root)
            root_parts_lower = {p.lower() for p in root_path.parts}
            # Skip junk directories in-place so os.walk won't descend into them.
            if root_parts_lower & _JUNK_DIR_NAMES:
                dirs.clear()
                continue
            if any(str(root_path).lower().startswith(str(e).lower()) for e in excluded_paths_abs):
                dirs.clear()
                continue
            for name in filenames:
                if scanned >= max_files:
                    break
                ext = Path(name).suffix.lower()
                if enabled_exts and ext not in enabled_exts:
                    continue
                full_path = root_path / name
                try:
                    st = full_path.stat()
                except OSError:
                    continue
                days_ago = int((now_ts - st.st_atime) / 86400)
                files.append({
                    "path": str(full_path),
                    "size": st.st_size,
                    "last_accessed_days_ago": days_ago,
                })
                scanned += 1

    return {"files": files, "total_scanned": scanned}


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


@app.command("scan")
def scan_command(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to migration.config.yaml"
    ),
    mode: str = typer.Option(
        "balanced",
        "--mode",
        "-m",
        help="Automation policy: guided (inventory + local recs + backup), "
             "balanced (+ analysis + file recs), expert (+ agent ranking).",
    ),
    deep: bool = typer.Option(
        False,
        "--deep",
        help="Run deep software scan (package managers + appx where available).",
    ),
    include_analysis: bool = typer.Option(
        None,
        "--analysis/--no-analysis",
        help="Run hardware/software analysis. Defaults to True for balanced/expert, False for guided.",
    ),
    recommendations: str = typer.Option(
        None,
        "--recommendations",
        help="Recommendation strategy override: none, local, online, agent. "
             "Defaults to mode-appropriate strategy when omitted.",
    ),
    selection_profile: str = typer.Option(
        "migrate_all",
        "--selection-profile",
        help="Recommendation profile: migrate_all or prioritize.",
    ),
) -> None:
    """
    Run scan workflow from the CLI applying the chosen mode policy.

    Modes
    -----
    guided   – inventory + local recommendations only (fast, minimal decisions)
    balanced – inventory + analysis + app/file recommendations  [default]
    expert   – balanced + online Repology-verified recommendations
    """
    try:
        valid_modes = {"guided", "balanced", "expert"}
        valid_recommendations = {"none", "local", "online", "agent"}
        valid_profiles = {"migrate_all", "prioritize"}

        if mode not in valid_modes:
            raise typer.BadParameter(
                f"Invalid mode '{mode}'. Use one of: {sorted(valid_modes)}"
            )

        # Apply mode-default strategy when not explicitly overridden — shared with the Qt wizard.
        if recommendations is None:
            recommendations = resolve_app_recommendation_strategy(mode)

        # Analysis runs by default in balanced/expert; skip in guided unless forced.
        if include_analysis is None:
            include_analysis = should_run_analysis(mode)

        if recommendations not in valid_recommendations:
            raise typer.BadParameter(
                f"Invalid recommendations mode '{recommendations}'. Use one of: {sorted(valid_recommendations)}"
            )

        # "agent" is an alias for "online" in the recommendation service.
        effective_rec_strategy = "online" if recommendations == "agent" else recommendations
        if selection_profile not in valid_profiles:
            raise typer.BadParameter(
                f"Invalid selection profile '{selection_profile}'. Use one of: {sorted(valid_profiles)}"
            )

        cfg = load_configuration(config)

        logger.info("Starting CLI scan workflow (mode=%s, deep=%s)", mode, deep)
        hw_inventory = collect_hardware_inventory()
        sw_inventory = collect_software_inventory(deep_scan=deep)
        settings_inventory = collect_settings_inventory(export_assets=True)

        hw_output = write_hardware_inventory(cfg, hw_inventory)
        sw_output = write_software_inventory(cfg, sw_inventory)
        settings_output = write_settings_inventory(cfg, settings_inventory)

        result: dict[str, object] = {
            "scan": {
                "mode": mode,
                "depth": "deep" if deep else "quick",
                "hardware_output": str(hw_output),
                "software_output": str(sw_output),
                "settings_output": str(settings_output),
                "hardware_categories": len(hw_inventory.keys()),
                "software_entries": len(sw_inventory.get("entries", [])),
                "settings_summary": settings_inventory.get("summary", {}),
            }
        }

        if include_analysis:
            hw_rows = generate_hardware_matrix(cfg, hw_inventory)
            sw_rows = generate_software_mapping(cfg, sw_inventory.get("entries", []))

            hw_matrix_path = write_hardware_matrix(cfg, hw_rows)
            sw_mapping_path = write_software_mapping(sw_rows)

            result["analysis"] = {
                "hardware_rows": len(hw_rows),
                "software_rows": len(sw_rows),
                "hardware_matrix_output": str(hw_matrix_path),
                "software_mapping_output": str(sw_mapping_path),
            }

        if recommendations != "none":
            repology_cfg = {
                "software_online_lookup_enabled": getattr(cfg.repology, "enabled", True),
                "software_online_provider": getattr(cfg.repology, "provider", "repology"),
                "software_online_send_fields": list(getattr(cfg.repology, "send_fields", ["name", "version", "publisher"])),
                "redact_user_paths": getattr(cfg.repology, "redact_user_paths", True),
            }
            rec_result = RecommendationService().generate_recommendations(
                software_inventory=sw_inventory,
                strategy=effective_rec_strategy,
                selection_profile=selection_profile,
                repology_config=repology_cfg,
            )
            result["recommendations"] = {
                "strategy": recommendations,
                "selection_profile": selection_profile,
                "recommended_count": rec_result.get("recommended_count", 0),
                "json_path": rec_result.get("json_path", ""),
                "markdown_path": rec_result.get("markdown_path", ""),
            }

        # File recommendations run in balanced and expert modes — shared with the Qt wizard.
        if should_run_file_recommendations(mode) and recommendations != "none":
            file_inventory = _build_file_inventory(cfg)
            choice_mode = "all_files"
            file_rec_result = FileRecommendationService().generate_recommendations(
                file_inventory=file_inventory,
                choice_mode=choice_mode,
                selected_file_types=cfg.source_system.file_types,
            )
            result["file_recommendations"] = {
                "choice_mode": choice_mode,
                "recommended_count": file_rec_result.get("recommended_count", 0),
                "input_count": file_rec_result.get("input_count", 0),
                "json_path": file_rec_result.get("json_path", ""),
                "markdown_path": file_rec_result.get("markdown_path", ""),
            }
            logger.info(
                "File recommendations: %d / %d files selected",
                file_rec_result.get("recommended_count", 0),
                file_rec_result.get("input_count", 0),
            )

        typer.echo(json.dumps(result, indent=2))
        logger.info("CLI scan workflow completed successfully")
    except typer.Exit:
        raise
    except typer.BadParameter as exc:
        typer.echo(f"ERROR: {exc}")
        raise typer.Exit(code=2)
    except Exception as exc:
        _handle_cli_error(exc, "scan")

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
    try:
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

        manifest = generate_manifest(cfg)
        out_file = write_manifest(cfg, manifest)
        logger.info("Backup manifest written to %s", out_file)
        copy_backup_files(manifest, cfg)
    except typer.Exit:
        raise
    except Exception as exc:
        _handle_cli_error(exc, "backup")


@app.command("recommended")
def recommended_command(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to migration.config.yaml"
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip confirmations and run full recommended pre-migration pipeline.",
    ),
) -> None:
    """
    Run one-click recommended Windows-side pipeline:
    inventory -> analysis -> backup.
    """
    try:
        cfg = load_configuration(config)

        if not yes:
            proceed = typer.confirm("Run full recommended pipeline (inventory, analysis, backup)?")
            if not proceed:
                typer.echo("Aborted by user.")
                raise typer.Exit(code=1)

        logger.info("Starting recommended migration pipeline")
        pipeline = PipelineService(cfg)
        result = pipeline.run_windows_pre_migration()
        logger.info(
            "Recommended pipeline complete: inventory=%d software entries, mappings=%d, backup=%s",
            len(result.inventory.get("software", {}).get("entries", [])),
            len(result.analysis.get("software", [])),
            "ok" if result.backup else "failed",
        )
        if result.backup is None:
            typer.echo("ERROR: Recommended pipeline failed during backup stage.")
            raise typer.Exit(code=1)

        typer.echo("Recommended pipeline completed successfully.")
    except typer.Exit:
        raise
    except Exception as exc:
        _handle_cli_error(exc, "recommended pipeline")


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
    report: Optional[Path] = typer.Option(
        None,
        "--report",
        help="Path to restore_report.json. Defaults to data/restore/restore_report.json.",
    ),
) -> None:
    """
    Validate post-migration state from restore_report.json and emit
    a machine-readable validation_report.json summary.
    """
    try:
        load_configuration(config)

        report_path = report or (RESTORE_DIR / "restore_report.json")
        summary = validate_restore_report(report_path)
        typer.echo(json.dumps(summary, indent=2))
        logger.info("Validation summary generated at %s", summary.get("validation_report_path"))
    except typer.Exit:
        raise
    except Exception as exc:
        _handle_cli_error(exc, "validation")

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
    target: Optional[Path] = typer.Option(
        None,
        "--target",
        help="Target directory for restored files. Defaults to ~/Restored_Migration.",
    ),
) -> None:
    """
    Restore data from backup bundle to the Linux target directory,
    verify hashes, and emit restore_report.json.
    """
    try:
        cfg = load_configuration(config)

        source_dir = source or RESTORE_DIR
        target_home = target or (Path.home() / "Restored_Migration")
        logger.info("Restore command invoked with source=%s target=%s", source_dir, target_home)

        pipeline = PipelineService(cfg)
        result = pipeline.run_linux_post_migration(
            bundle_dir=source_dir,
            target_home=target_home,
        )
        typer.echo(f"Restore completed. Report: {result.restore['report_path']}")
    except typer.Exit:
        raise
    except Exception as exc:
        _handle_cli_error(exc, "restore")


@app.command("report")
def report_command(
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="Path to migration.config.yaml"
    ),
) -> None:
    """
    Generate the final migration report bundle from restore and validation evidence.
    """
    try:
        load_configuration(config)

        result = ReportService().generate_report()
        report = result.get("report", {})
        summary = report.get("summary", {})

        typer.echo(json.dumps({
            "json_path": result.get("json_path"),
            "markdown_path": result.get("markdown_path"),
            "html_path": result.get("html_path"),
            "summary": summary,
        }, indent=2))
        logger.info("Final report generated at %s", result.get("markdown_path"))
    except typer.Exit:
        raise
    except Exception as exc:
        _handle_cli_error(exc, "report generation")


@profile_app.command("save")
def profile_save(
    mode: str = typer.Option("guided", "--mode", help="Migration mode: guided, balanced, expert"),
    include_docs: bool = typer.Option(True, "--docs", help="Include Documents folder"),
    include_desktop: bool = typer.Option(True, "--desktop", help="Include Desktop folder"),
    include_downloads: bool = typer.Option(True, "--downloads", help="Include Downloads folder"),
    include_pictures: bool = typer.Option(True, "--pictures", help="Include Pictures folder"),
) -> None:
    """
    Save an active profile for customization-aware flows.
    """
    profile = {
        "mode": mode,
        "selected_folders": {
            "Documents": include_docs,
            "Desktop": include_desktop,
            "Downloads": include_downloads,
            "Pictures": include_pictures,
        },
        "mapping_overrides": [],
    }
    path = ProfileService().save(profile)
    typer.echo(f"Profile saved: {path}")


@profile_app.command("show")
def profile_show() -> None:
    """
    Show the currently active customization profile.
    """
    profile = ProfileService().load()
    if not profile:
        typer.echo("No active profile found.")
        return
    typer.echo(json.dumps(profile, indent=2))


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
        help="Target USB device path on Linux (e.g. /dev/sdb) or drive letter on Windows (e.g. E:).",
    ),
    copy_tool: bool = typer.Option(
        False,
        "--copy-tool",
        help="Also copy this migration project folder onto the USB after imaging.",
    ),
) -> None:
    """
    Validate inputs and generate ready-to-run USB imaging commands.

    On Linux: verifies the ISO, confirms the device, and prints a dd command
    with a safety check. On Windows: validates the ISO and guides through Rufus.
    Does NOT write to the device without explicit --device confirmation.
    """
    import platform
    import shutil

    logger.info("USB command invoked (iso=%s, device=%s)", iso, device)
    system = platform.system().lower()

    # ── ISO validation ────────────────────────────────────────────────────────
    if iso is None:
        typer.echo("No ISO specified. Download Linux Mint from https://linuxmint.com/download.php")
        typer.echo("Then re-run:  python -m src.cli usb --iso /path/to/linuxmint.iso --device <device>")
        raise typer.Exit(code=0)

    iso = iso.resolve()
    if not iso.exists():
        typer.echo(f"ERROR: ISO file not found: {iso}")
        raise typer.Exit(code=1)

    iso_size_mb = iso.stat().st_size // (1024 * 1024)
    typer.echo(f"ISO: {iso}  ({iso_size_mb} MB)  ✓")

    if not iso.suffix.lower() == ".iso":
        typer.echo("WARNING: file does not have a .iso extension — double-check it is a valid ISO image.")

    # ── Device guidance ───────────────────────────────────────────────────────
    if device is None:
        typer.echo()
        if "linux" in system:
            typer.echo("No device specified. List available block devices with:")
            typer.echo("  lsblk -d -o NAME,SIZE,MODEL")
            typer.echo("Then re-run with --device /dev/sdX  (replace sdX with your USB device).")
        else:
            typer.echo("No device specified. Identify your USB drive letter in File Explorer,")
            typer.echo("then re-run with --device E:  (replace E: with your USB drive letter).")
        raise typer.Exit(code=0)

    # ── Platform-specific imaging guidance ───────────────────────────────────
    typer.echo()
    if "linux" in system:
        dd = shutil.which("dd")
        if dd is None:
            typer.echo("WARNING: 'dd' not found in PATH — install coreutils.")

        typer.echo("Ready to image. Run the following command as root (DESTRUCTIVE — all data on the device will be lost):")
        typer.echo()
        typer.echo(f"  sudo dd if='{iso}' of='{device}' bs=4M status=progress oflag=sync")
        typer.echo()
        typer.echo("Verify after imaging:")
        typer.echo(f"  sudo dd if='{device}' bs=4M count={iso.stat().st_size // (4 * 1024 * 1024) + 1} | md5sum")
        typer.echo(f"  md5sum '{iso}'")

        if copy_tool:
            typer.echo()
            typer.echo("To copy this migration tool onto the USB after imaging:")
            project_dir = Path(__file__).resolve().parent.parent
            typer.echo(f"  sudo mount {device}1 /mnt/usb")
            typer.echo(f"  sudo cp -r '{project_dir}' /mnt/usb/migration-tool")
            typer.echo("  sudo umount /mnt/usb")
    else:
        typer.echo("On Windows, use Rufus to write the ISO to the USB drive:")
        typer.echo("  1. Download Rufus from https://rufus.ie")
        typer.echo(f"  2. Select ISO: {iso}")
        typer.echo(f"  3. Select device: {device}")
        typer.echo("  4. Partition scheme: GPT  |  Target system: UEFI (non CSM)")
        typer.echo("  5. Click START — all data on the device will be erased.")

        if copy_tool:
            typer.echo()
            project_dir = Path(__file__).resolve().parent.parent
            typer.echo("After Rufus finishes, copy the migration tool onto the USB:")
            typer.echo(f"  xcopy \"{project_dir}\" \"{device}\\migration-tool\" /E /I /H")

    typer.echo()
    typer.echo("Once booted into Linux Mint Live, run the migration tool from the USB with:")
    typer.echo("  python migration-tool/app.py")
    logger.info("USB command completed successfully")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app()


if __name__ == "__main__":
    main()
