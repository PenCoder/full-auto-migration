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
    """Scan configured backup paths and return a lightweight file inventory dict."""
    import os as _os
    import time as _time

    enabled_exts = {ext.lower() for ext, on in cfg.source_system.file_types.items() if on}
    excluded = {p.lower() for p in cfg.source_system.excluded_paths}
    now_ts = _time.time()
    files: list[dict] = []
    scanned = 0

    for raw_path in cfg.source_system.backup_paths:
        expanded = Path(raw_path.replace("~", str(Path.home()))).expanduser()
        if not expanded.exists() or not expanded.is_dir():
            continue
        for root, _, filenames in _os.walk(expanded):
            if scanned >= max_files:
                break
            if any(excl in root.lower() for excl in excluded):
                continue
            for name in filenames:
                if scanned >= max_files:
                    break
                ext = Path(name).suffix.lower()
                if enabled_exts and ext not in enabled_exts:
                    continue
                full_path = Path(root) / name
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
    expert   – balanced + agent-ranked recommendations via AI endpoint
    """
    try:
        valid_modes = {"guided", "balanced", "expert"}
        valid_recommendations = {"none", "local", "online", "agent"}
        valid_profiles = {"migrate_all", "prioritize"}

        if mode not in valid_modes:
            raise typer.BadParameter(
                f"Invalid mode '{mode}'. Use one of: {sorted(valid_modes)}"
            )

        # Apply mode-default strategy when not explicitly overridden.
        if recommendations is None:
            recommendations = {"guided": "local", "balanced": "local", "expert": "agent"}[mode]

        # Analysis runs by default in balanced/expert; skip in guided unless forced.
        if include_analysis is None:
            include_analysis = mode in {"balanced", "expert"}

        if recommendations not in valid_recommendations:
            raise typer.BadParameter(
                f"Invalid recommendations mode '{recommendations}'. Use one of: {sorted(valid_recommendations)}"
            )
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
            ai_cfg = {
                "software_online_lookup_enabled": getattr(cfg.ai, "software_online_lookup_enabled", False),
                "software_online_provider": getattr(cfg.ai, "software_online_provider", "repology"),
                "software_online_send_fields": getattr(cfg.ai, "software_online_send_fields", ["name"]),
            }
            rec_result = RecommendationService().generate_recommendations(
                software_inventory=sw_inventory,
                strategy=recommendations,
                selection_profile=selection_profile,
                ai_config=ai_cfg,
            )
            result["recommendations"] = {
                "strategy": recommendations,
                "selection_profile": selection_profile,
                "recommended_count": rec_result.get("recommended_count", 0),
                "json_path": rec_result.get("json_path", ""),
                "markdown_path": rec_result.get("markdown_path", ""),
            }

        # File recommendations run in balanced and expert modes (mirrors Qt AutomationCoordinator).
        if mode in {"balanced", "expert"} and recommendations != "none":
            file_inventory = _build_file_inventory(cfg)
            choice_mode = "ai_recommended" if mode == "expert" else "all_files"
            use_ai = mode == "expert"
            ai_file_cfg = {
                "file_recommendation_online_enabled": getattr(cfg.ai, "file_recommendation_online_enabled", False),
                "endpoint": getattr(cfg.ai, "endpoint", ""),
                "model": getattr(cfg.ai, "model", ""),
                "api_key": getattr(cfg.ai, "api_key", ""),
            }
            file_rec_result = FileRecommendationService().generate_recommendations(
                file_inventory=file_inventory,
                choice_mode=choice_mode,
                use_ai=use_ai,
                ai_config=ai_file_cfg,
                selected_file_types=cfg.source_system.file_types,
            )
            result["file_recommendations"] = {
                "choice_mode": choice_mode,
                "ranking_method": file_rec_result.get("ranking_method", ""),
                "recommended_count": file_rec_result.get("recommended_count", 0),
                "input_count": file_rec_result.get("input_count", 0),
                "json_path": file_rec_result.get("json_path", ""),
                "markdown_path": file_rec_result.get("markdown_path", ""),
            }
            logger.info(
                "File recommendations: %d / %d files selected (%s)",
                file_rec_result.get("recommended_count", 0),
                file_rec_result.get("input_count", 0),
                file_rec_result.get("ranking_method", ""),
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
