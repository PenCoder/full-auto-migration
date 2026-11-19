---
description: List changes to the frozen baseline since G1 and check them against the change log
---
Run `git diff --stat baseline-g1 -- baseline/` and `git diff baseline-g1 -- baseline/`.
For every change, check whether docs/thesis/CHANGELOG_BASELINE.md has an approved entry for it.
Report changes without an approved entry. Do not change any file.
