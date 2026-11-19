# CLAUDE.md

Guidance for Claude Code in this repository. Read this first in every session.

## What this repository is

A Windows 11 → Linux Mint migration tool (Python, PySide6 GUI, Typer CLI), first built in the Praktikum
"Toward a Fully Automated Migration Framework from Windows 11 to Linux Mint". It is now being extended
and evaluated in the master thesis "Automated Migration from Windows to Linux: How Much of a Working
Environment Can Be Moved?" (JMU Würzburg, supervisor Prof. Dr. Harald Wehnes, second supervisor
Dipl.-Math. Guido Bacharach).

The thesis is a measurement study. The tool and the test bench are instruments. Correct measurement
matters more than features: never make a result look better by changing how it is measured.

Plans and rules for the thesis live in `docs/thesis/` and `baseline/`. Read `docs/thesis/REPO_PLAN.md`
before starting a task.

## Terms used in this repository

- **Layer**: files, applications, application data, settings.
- **Migration item**: one file, one installed application, one data type of one application
  (for example "Firefox bookmarks"), or one setting.
- **Item state**: `automatic` (migrated and verified), `manual` (manual step required; instructions
  given, not carried out), `not_migrated`. Only `automatic` counts as complete.
- **Path**: A = same application on both systems; B = alternative via a standard format (HTML bookmarks,
  vCard, CSV, iCalendar); C = no common format (for example an Outlook PST mailbox).
- **Test profile**: a scripted Windows user setup on the test bench (`testbench/profiles/`).
  Do not confuse with `src/services/profile_service.py`, which stores the user's wizard choices.
- **Reference set**: about 50 Windows applications labelled by hand with their correct Linux equivalent
  (`baseline/reference_set.csv`). It is the answer key for the mapping evaluation and is independent of
  `configs/linux_ms_map.csv` (the tool's own mapping table, 238 entries).
- **Readiness report**: the tool's prediction of every item's state before migration, from the rules in
  `baseline/readiness_rules.yaml`.

## Architecture map

- `src/cli.py` – Typer CLI (`scan`, `backup`, `recommended`, `validate`, `restore`, `report`, `usb`, ...).
- `src/inventory/` – Windows inventory: software, hardware, settings (registry/PowerShell), shortcuts.
- `src/analysis/software_mapping.py` – mapping engine 1 (used by the CLI and `migration_service`).
- `src/services/recommendations/app_recommender.py` – mapping engine 2 (GUI recommendations, Repology lookup).
  The thesis merges both into one chain: exact → fuzzy → Repology. Repology runs only in Expert mode.
- `src/backup/` – bundle archive and manifest with per-file SHA-256.
- `src/services/restore_service.py` – restore on Linux: files to `~/Restored_Migration/`, hash
  verification, apt installs (`_install_applications`), wallpaper and theme, shortcuts, restore report.
- `src/services/settings_service.py` – settings plan.
- `src/qt_ui/` – GUI (pages, controllers, widgets).
- `configs/migration.config.yaml` – configuration; `configs/linux_ms_map.csv` – mapping table.

New code for the thesis goes here (create as needed):

- `src/services/appdata/` – one module per application data type (Firefox, Edge → Firefox,
  Thunderbird, Outlook contacts) behind a common interface: `export()`, `import_()`, `verify()`.
- `src/readiness/` – readiness report: rules engine, reason codes, JSON and Markdown output.
- `testbench/` – profile scripts, VM control, run orchestration, Linux verification.
- `evaluation/` – analysis scripts; raw results under `evaluation/results/`.

## Commands

```bash
pip install -r requirements.txt -r requirements-test.txt
pytest -p no:flake8 -m "not requires_qt and not requires_network" -q   # fast checks, any OS
pytest -p no:flake8 -q                                                   # full suite
python -m src.cli --help
```

`-p no:flake8` is needed because `pytest-flake8` in `requirements-test.txt` does not load with
current pytest versions (until that file is cleaned up in step 0 of the repo plan).

Windows-only code (registry, PowerShell, `winapps`) cannot run on Linux or in CI. Test its logic with
fixtures and mocks; run it for real only on the Windows VM.

## Rules

1. **Baseline is frozen after G1.** Do not edit anything in `baseline/` once the tag `baseline-g1`
   exists unless the task names an approved change log entry (`docs/thesis/CHANGELOG_BASELINE.md`).
   If code shows a rule does not work, stop and report it; do not change the rule.
2. **Do not touch measurement to improve results.** Verification rules, item states and reason codes
   follow `baseline/`. Never relax a check, skip an item, or reclassify a failure to raise a number.
3. **Never write to `evaluation/results/`** except through the evaluation scripts, and never edit
   raw result files by hand.
4. **Credentials are never exported.** Saved passwords, `logins.json`, `key4.db`, Wi-Fi keys and
   similar are excluded and reported as `not_migrated` with reason `excluded_by_design`.
5. **Guided and Balanced mode stay offline.** Network access (Repology) only in Expert mode.
6. **No silent failures.** Every item ends in one of the three states with a reason code; path C items
   produce written instructions in the report.
7. **Tests first for new behaviour.** Add or update pytest tests with every change; tests must not use
   the network. Keep the test scenarios in `baseline/test_scenarios.md` passing.
8. **Small changes.** One task per branch and pull request. Do not refactor unrelated code.
9. **Keep it explainable.** The author must be able to explain every line in the thesis defence.
   Prefer simple, readable code over clever code, and explain non-obvious decisions in comments.

## Style

Python 3.10+, type hints, docstrings on public functions, `pathlib` for paths, `logging` via
`src/loggers.py`. JSON outputs use snake_case keys and include a `schema_version` field.
