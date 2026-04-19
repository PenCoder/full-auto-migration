# Full-automation: Windows → Linux Migration Framework

## Phase Documentation

- Complete Phases 1 to 6: [docs/progress/PHASES_1_TO_6_COMPLETE.md](docs/progress/PHASES_1_TO_6_COMPLETE.md)
- Milestone M1: [docs/progress/M1_setup.md](docs/progress/M1_setup.md)
- Milestone M2: [docs/progress/M2_discovery.md](docs/progress/M2_discovery.md)
- Milestone M3: [docs/progress/M3_framework.md](docs/progress/M3_framework.md)
- Milestone M4: [docs/progress/M4_evaluation.md](docs/progress/M4_evaluation.md)
- Milestone M5: [docs/progress/M5_evaluation.md](docs/progress/M5_evaluation.md)
- Milestone M6: [docs/progress/M6_finalization.md](docs/progress/M6_finalization.md)

## Full Automation Startup

Enable these settings in `configs/migration.config.yaml` to auto-run all phases when the Qt app opens:

- `automation.auto_start_full_flow: true`
- `automation.auto_start_delay_ms: 250`

Behavior:
- Windows runtime: scan -> analysis -> backup
- Linux runtime: restore -> validation

Linux requirement:
- `data/restore/manifest.json` and `data/restore/backup.zip` must exist before startup auto-run.

## Report Generation

After restore and validation, the app generates a final report bundle in `docs/reports/`.

Artifacts:
- `docs/reports/final_report.json`
- `docs/reports/final_report.md`
- `docs/reports/final_report.html`

CLI usage:
- `python -m src.cli report`

What the report contains:
- sovereignty score and rating
- restore and validation summary
- file-level evidence from the restore report
- links to the generated markdown, HTML, and JSON outputs

If you are using the Qt app, the final wizard step is the report dashboard. It lets you generate the same report bundle and open the exported markdown or HTML directly.
