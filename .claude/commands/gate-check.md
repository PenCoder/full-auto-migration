---
description: Check the repository against a gate's criteria
argument-hint: <M0|G1|G2|G3|G4>
---
Check gate $ARGUMENTS against the criteria in docs/thesis/REPO_PLAN.md and the exposé (Table 7).
For each criterion, say whether the repository shows it as met, with the file, test or tag as evidence,
or what is missing. Run `pytest -p no:flake8 -m "not requires_qt and not requires_network" -q` and include the result.
List open GitHub issues in the milestone: `gh issue list --milestone $ARGUMENTS --state open`.
Do not change any file.
