# Repository plan for the master thesis

How the repository `PenCoder/full-auto-migration` is organised and used during the 19 weeks.
The tasks match the execution plan and the exposé (Sections 4–5).

## 1. Principles

- The Praktikum state is preserved with a tag before any thesis work starts.
- Work happens in short branches merged into `main` through pull requests, one task per branch.
- Every gate is a tag, so the state at each gate can be reproduced.
- The baseline (rules, profiles, reference set) lives in `baseline/` and is frozen at G1.
- Raw evaluation results are committed unchanged; analysis scripts read them and write tables and figures.

## 2. Target structure

```
baseline/                         frozen at G1 (tag baseline-g1)
  app_set.yaml                    data types: export, import, verification rule, expected limitations
  test_profiles.md                the ≥ 4 test profiles and their content lists
  verification_rules.md           per layer (Section 4.3 of the exposé)
  readiness_rules.yaml            Table 5, with version: "1.0"
  labelling_rules.md              how the reference set is labelled
  reference_set.csv               ~50 apps: windows_name, label, suitable, source, checked_on, second_label
  test_scenarios.md               Table 10
src/
  services/appdata/               base.py, firefox.py, edge_bookmarks.py, thunderbird.py, outlook_contacts.py
  readiness/                      rules.py, report.py, reason_codes.py
  analysis/matching.py            the merged mapping chain (exact → fuzzy → Repology)
testbench/
  profiles/                       office.ps1, student.ps1, home.ps1, technical.ps1, common.ps1
  vm/                             reset.sh, run_profile.sh, config.env (VM and snapshot names)
  linux/verify.py                 applies verification rules, writes items.json per run
  configs/                        unattended configuration files, one per test profile
evaluation/
  completeness.py                 RQ1: states per layer and profile, cause groups
  prediction.py                   RQ2: 3 × 3 confusion matrix, agreement, precision/recall per state
  mapping_eval.py                 precision and recall against the reference set, matches per stage
  sus.py                          SUS scoring
  results/                        raw run output (committed at G3, never edited by hand)
  tables/, figures/               generated output for the thesis
docs/thesis/
  REPO_PLAN.md                    this file
  CLAUDE_CODE_PLAYBOOK.md         how to work with Claude Code in VS Code
  CHANGELOG_BASELINE.md           approved changes to the baseline after G1
  status-reports/                 one Markdown file per report
CLAUDE.md                         guidance for Claude Code
.claude/commands/                 project slash commands
.github/workflows/tests.yml       pytest on every push and pull request
```

## 3. Branches, issues and tags

**Branches.** `main` is always working. Branch names: `s<sprint>/<short-name>`, for example
`s1/unattended-mode`, `s2/edge-bookmarks`. Planning work uses `g1/<name>`.

**Issues and milestones.** One GitHub issue per task in the execution plan, with milestones
`M0`, `G1`, `G2`, `G3`, `G4` and labels `sprint-1`, `sprint-2`, `sprint-3`, `evaluation`, `baseline`,
`docs`. Create them once with the `gh` commands in Section 6.

**Tags.**

| Tag | When | Content |
|---|---|---|
| `praktikum-final` | Step 0, before any change | State submitted for the Praktikum |
| `baseline-g1` | G1, week 4 | Baseline frozen |
| `tool-g2` | G2, week 11 | Tool complete |
| `results-g3` | G3, week 14 | All runs and raw results |
| `thesis-final` | G4, week 19 | Published version for the thesis |

## 4. Steps

### Step 0 · before week 1 (M0)

1. `git tag praktikum-final && git push origin praktikum-final`.
2. Add `CLAUDE.md`, `.claude/commands/`, `docs/thesis/` from the thesis kit.
3. Add `.github/workflows/tests.yml` and get the test suite green. A run on the current `main`
   (checked on 11 November 2026, Python 3.13 on Linux) showed:
   - `requirements-test.txt` installs `pytest-flake8`, which stops pytest from starting with current
     pytest versions. Remove the plugins the project does not use (flake8, pylint, mypy, allure,
     randomly, sugar, faker, ...) or run pytest with `-p no:flake8`.
   - 184 tests pass, 3 are skipped and 5 fail:
     `test_state_management.py::test_advanced_operations_default`,
     `test_qt_ui_controllers.py::TestModeController::test_mode_transitions`,
     `test_qt_ui_controllers.py::TestModeController::test_guided_mode_disables_expert_controls`,
     `test_settings_service.py::test_build_plan_expert_adds_manual_review_items`,
     `test_settings_service.py::test_build_plan_expert_selected_advanced_items_require_manual_review`.
     Decide for each whether the test or the code is out of date and fix it, so that every later
     failure means something.
4. Clean up Praktikum documents:
   - `docs/FULL_AUTOMATION_EXPOSE.md`: O6 is marked "Achieved" but was not met; correct it.
   - `docs/USER_MIGRATION_GUIDE.md` step 9 describes installing applications by hand, but the restore
     installs them through `restore_service._install_applications`; correct it.
   - `docs/TESTING.md` is generic (mentions PyQt5, CI stages that do not exist); replace it with
     what the project actually does.
5. Create issues and milestones (Section 6).

### Step 1 · weeks 1–4 (G1)

- `baseline/`: write all files listed in Section 2. `readiness_rules.yaml` encodes Table 5 so that
  `src/readiness/rules.py` can load it.
- `testbench/vm/`: first version of `reset.sh` and `run_profile.sh` for the feasibility check.
- `testbench/profiles/common.ps1` and one profile script: build it twice and compare the content lists.
- Test scenarios from Table 10 as pytest tests marked `xfail` until implemented.
- At G1: `git tag baseline-g1`, push the tag, add the deny rule for `baseline/` to
  `.claude/settings.json` (see the playbook).

### Step 2 · sprints 1–3, weeks 5–11 (G2)

| Sprint | Issues |
|---|---|
| 1 (weeks 5–6) | Profile scripts for all test profiles · VM reset and run scripts · unattended mode from a configuration file · `testbench/linux/verify.py` |
| 2 (weeks 7–8) | `appdata/firefox.py` (A) · `appdata/edge_bookmarks.py` (B) · merged mapping chain in `src/analysis/matching.py` |
| 3 (weeks 9–10) | `appdata/thunderbird.py` (A) · `appdata/outlook_contacts.py` (B, PST as instructions, C) · settings: keyboard, language, time zone, default apps · readiness report |
| Buffer (week 11) | One test profile end to end · defects · `git tag tool-g2` |

### Step 3 · weeks 12–14 (G3)

- Run every test profile three times; raw output to `evaluation/results/<profile>/run-<n>/`.
- Run the evaluation scripts; commit raw results, tables and figures; `git tag results-g3`.

### Step 4 · weeks 15–19 (G4)

- README section "Reproducing the thesis results".
- Licence check, release notes, `git tag thesis-final`, GitHub release.

## 5. Output formats

`testbench/linux/verify.py` writes one `items.json` per run:

```json
{
  "schema_version": "1.0",
  "profile": "office",
  "run": 2,
  "tool_commit": "<git sha>",
  "items": [
    {"item_id": "appdata:firefox:bookmarks", "layer": "application_data", "path": "A",
     "state": "automatic", "reason_code": null,
     "detail": {"records_expected": 100, "records_transferred": 98}}
  ]
}
```

The readiness report writes the same `item_id` values with `predicted_state` and `reason_code`, so that
`evaluation/prediction.py` can join prediction and observation by `item_id`.

## 6. One-time GitHub setup

```bash
for m in M0 G1 G2 G3 G4; do gh api repos/PenCoder/full-auto-migration/milestones -f title="$m"; done
for l in sprint-1 sprint-2 sprint-3 evaluation baseline docs; do gh label create "$l"; done
gh issue create --title "Unattended mode from configuration file" --label sprint-1 --milestone G2 \
  --body "Execution plan b3. Acceptance: Table 10 scenarios 'Valid configuration file' and 'Invalid configuration file' pass."
```

Repeat the last command for each task, or ask Claude Code to create them (see the playbook).
