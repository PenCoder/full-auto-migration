# Working with Claude Code in VS Code

How to use Claude Code for the thesis implementation, and the prompts for each task.

## 1. Setup (once)

1. Install the **Claude Code** extension from the VS Code Marketplace (publisher: Anthropic) and sign in.
   Claude Code also runs in the VS Code terminal with the `claude` command.
2. Open the repository folder in VS Code. Claude Code reads `CLAUDE.md` at the start of every session.
3. Install the GitHub CLI and run `gh auth login`, so Claude Code can read issues and open pull requests.
4. Create a virtual environment and install dependencies:
   `python -m venv .venv`, activate it, then `pip install -r requirements.txt -r requirements-test.txt`.
5. Copy the project commands into `.claude/commands/`. They appear as slash commands:
   `/start-task`, `/gate-check`, `/status-report`, `/baseline-guard`.

## 2. How each task runs

1. **Branch.** `git switch -c s1/unattended-mode`.
2. **Plan first.** Switch to plan mode (Shift+Tab cycles the modes) or run `/start-task <issue number>`.
   Claude Code reads the issue, `CLAUDE.md` and the relevant `baseline/` files and proposes a plan
   without editing anything. Check the plan against the exposé before you approve it.
3. **Tests first.** Ask for the tests before the implementation. Read them: they define what "done" means.
4. **Implement in small steps.** Approve edits one file or one function at a time where possible.
5. **Run the checks.** `pytest -p no:flake8 -m "not requires_qt and not requires_network" -q`, then the full suite.
6. **Review the diff yourself.** `git diff main`. You must be able to explain every change in the defence.
   If you cannot, ask Claude Code to explain it or to simplify it.
7. **Commit and open a pull request.** `gh pr create --fill`, then merge after CI passes.
8. **Tick the task** in the execution plan.

## 3. Rules for using Claude Code in the thesis

- **Declare it.** Check the JMU examination regulations and ask Prof. Wehnes how AI assistance must be
  declared. Keep a short log of which parts were written with Claude Code (the commit messages and pull
  requests already record most of it).
- **You make the research decisions.** Rules, profiles, labels in the reference set, verification and
  readiness rules are written by you. Claude Code may help format them or turn them into code; it does
  not decide them.
- **The reference set is labelled by you, never by Claude Code.** Otherwise the answer key would come
  from a similar source as the tool it evaluates.
- **No edits to `baseline/` after G1.** Add this deny rule to `.claude/settings.json` on the day you tag
  `baseline-g1`:

  ```json
  {
    "permissions": {
      "deny": ["Edit(baseline/**)", "Write(baseline/**)", "Edit(evaluation/results/**)", "Write(evaluation/results/**)"]
    }
  }
  ```

  For an approved change, add it to `docs/thesis/CHANGELOG_BASELINE.md`, remove the rule for that one
  edit, and put it back afterwards.
- **Windows-side code is tested on the Windows VM.** Claude Code on your laptop can write PowerShell and
  registry code and test its logic with mocks; whether it really works is checked on the VM.

## 4. Prompts by task

Paste the prompt after `/start-task <issue>` or on its own in plan mode. Each one names the acceptance
criteria, so you can check the result.

### Step 0 (before week 1)

**Green test suite**
> Run `pytest -p no:flake8 -q`. For each of the 5 failing tests listed in `docs/thesis/REPO_PLAN.md`
> step 0, find out whether the test or the code is out of date and explain it to me before changing
> anything. Then trim `requirements-test.txt` to the plugins the tests actually use.

**Issues and milestones**
> Using `gh`, create milestones M0, G1, G2, G3, G4 and labels sprint-1, sprint-2, sprint-3, evaluation,
> baseline, docs. Then create one issue per task in Section 4 of this playbook (b1–b11, e1–e4, p4, p8/p9),
> with the prompt text as the issue body, the matching label and milestone (planning → G1, sprints → G2,
> evaluation → G3). Show me the list before creating them.

**Praktikum documents**
> Correct `docs/FULL_AUTOMATION_EXPOSE.md` (objective O6 was not met), `docs/USER_MIGRATION_GUIDE.md`
> step 9 (applications are installed by the restore, see `restore_service._install_applications`) and
> replace `docs/TESTING.md` with a short description of the tests that actually exist. Show the diff.

### Planning (weeks 1–4)

**p4 – Profile script feasibility**
> Read `baseline/test_profiles.md`. Write `testbench/profiles/common.ps1` with functions that create
> files with fixed content, install applications with winget at fixed versions, write Firefox bookmarks
> through a prepared `places.sqlite`, and set registry values. Then write `testbench/profiles/office.ps1`
> using these functions. Add `testbench/profiles/list_content.ps1`, which writes a sorted JSON list of
> everything the profile created (paths with SHA-256, installed apps with version, settings with values).
> Acceptance: running office.ps1 twice on fresh snapshots gives identical `list_content` output.

**p8 / p9 – Rules and scenarios as code**
> Read `baseline/readiness_rules.yaml` and `baseline/test_scenarios.md`. Create pytest tests for every
> scenario in Table 10 under `tests/test_thesis/`, marked `xfail(strict=True, reason="not implemented")`.
> Add a loader in `src/readiness/rules.py` that validates the YAML (layers, conditions, predicted states,
> reason codes) and tests for the loader. Do not change the YAML.

### Sprint 1 (weeks 5–6)

**b1 – All test profiles**
> Using `testbench/profiles/common.ps1`, write the remaining profile scripts listed in
> `baseline/test_profiles.md`. Each script is idempotent on a clean snapshot and ends by calling
> `list_content.ps1`. Acceptance: for each profile, two builds produce identical content lists.

**b2 – VM control**
> Write `testbench/vm/reset.sh` and `testbench/vm/run_profile.sh` using `VBoxManage`. Names of VMs and
> snapshots come from `testbench/vm/config.env`. `run_profile.sh <profile> <run>` restores both snapshots,
> starts the VMs, builds the profile on Windows, runs the unattended migration, copies the bundle,
> runs restore and `verify.py` on Linux and stores everything under
> `evaluation/results/<profile>/run-<run>/` together with the tool's git commit. Fail loudly on any step.

**b3 – Unattended mode**
> Add a CLI command `run` in `src/cli.py` that performs scan, mapping, readiness report and bundle on
> Windows, or restore on Linux, from a configuration file without any prompt. Extend
> `src/config/schema.py` and `src/config/validator.py` with an `unattended` section (mode, file types,
> folders, applications, bundle path). Acceptance: the Table 10 scenarios "Valid configuration file" and
> "Invalid configuration file" pass; an invalid file stops before any change and names the invalid entry.

**b4 – Verification on Linux**
> Write `testbench/linux/verify.py`. It reads the profile's content list and the verification rules in
> `baseline/verification_rules.md` (implemented as code, one function per layer) and writes `items.json`
> in the format of `docs/thesis/REPO_PLAN.md` Section 5. Application data is read from the profile the
> application actually loads (for Firefox: the default profile in `profiles.ini`). Applications pass if
> installed and the process is still running 30 seconds after start. Add unit tests with fixture data.

### Sprint 2 (weeks 7–8)

**b5 – Firefox (path A)**
> Create `src/services/appdata/base.py` with an `AppDataMigrator` interface (`detect`, `export`,
> `import_`, `verify`) and `src/services/appdata/firefox.py`. Export the default profile's bookmarks and
> history (`places.sqlite`, `favicons.sqlite`) without credentials (never `logins.json`, `key4.db`,
> `cookies.sqlite`). On Linux, import into the profile Firefox loads and adjust Windows paths. Add the
> data to the bundle manifest with checksums. Tests use small fixture databases.

**b6 – Edge to Firefox (path B)**
> Create `src/services/appdata/edge_bookmarks.py`. Read Edge's `Bookmarks` JSON from the default profile,
> convert it to the Netscape HTML bookmark format, and import it into Firefox on Linux (use a policy or
> profile file that Firefox reads at start; explain the method in the docstring). Verification compares
> URL and folder path. Report records that lose details separately.

**b7 – One mapping chain**
> Compare `src/analysis/software_mapping.py` and `src/services/recommendations/app_recommender.py`.
> Propose one module `src/analysis/matching.py` with the chain exact → fuzzy → Repology, where Repology
> runs only in Expert mode. Each result records the stage that produced it. Replace both call sites, keep
> the existing tests passing and add tests for each stage. Show me the plan before changing call sites.

### Sprint 3 (weeks 9–10)

**b8 – Thunderbird (path A)**
> Create `src/services/appdata/thunderbird.py`: account settings (without passwords), local folders and
> address book. Verification: messages by Message-ID, contacts by name and email.

**b9 – Outlook contacts (path B) and mailbox (path C)**
> Create `src/services/appdata/outlook_contacts.py`: export contacts to vCard (or CSV if vCard export is
> not possible without Outlook automation; explain the choice) and import into Thunderbird's address book.
> For the PST mailbox, produce step-by-step instructions in the migration report and set the item to
> `manual` with reason `proprietary_format`. Do not attempt PST conversion.

**b10 – Settings**
> Extend `src/inventory/settings.py` to read keyboard layout, display language, time zone and default
> browser and mail application on Windows, and `restore_service` to apply them on Linux Mint with
> `localectl`, `timedatectl` and `xdg-mime`. Verification reads each value back. Settings without an apply
> rule become `manual` with reason `not_supported`.

**b11 – Readiness report**
> Implement `src/readiness/report.py`. Inputs: inventory, mapping results, app set and path model,
> hardware check. Apply `baseline/readiness_rules.yaml` to every item and write `readiness.json`
> (item_id, layer, path, predicted_state, reason_code, rules_version) and a readable Markdown report with
> a summary per layer. Item ids must match those from `verify.py`. Call it from the `run` command before
> the bundle is created.

### Evaluation (weeks 12–14)

**e1 – Runs**
> Write `testbench/run_all.sh` that runs every profile three times through `run_profile.sh` and logs
> start and end time, bundle size, decisions required and remaining manual steps per run to
> `evaluation/results/runs.csv`. Do not run it; I will start it.

**e2 / e3 / e4 – Analysis**
> Write `evaluation/completeness.py`, `evaluation/prediction.py` and `evaluation/mapping_eval.py` as
> described in Section 4.3–4.5 of the exposé (copy in `docs/thesis/`). They only read
> `evaluation/results/` and `baseline/reference_set.csv` and write CSV tables to `evaluation/tables/` and
> figures to `evaluation/figures/`. `prediction.py` reports install or launch failures after an
> `automatic` prediction separately. `mapping_eval.py` counts a proposal for an app without a suitable
> equivalent as a false positive. Add tests with small synthetic inputs where the expected numbers are
> computed by hand.

## 5. Session habits

- Start each session with: "Read CLAUDE.md and docs/thesis/REPO_PLAN.md. Today’s task: …".
- Keep sessions to one task; use `/clear` between tasks so earlier context does not leak in.
- When Claude Code proposes changing a rule, a threshold or a test expectation, say no and log it as a
  possible change request instead.
- Every two weeks run `/status-report` and paste the result into the execution plan’s report draft.
