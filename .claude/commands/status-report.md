---
description: Draft the two-weekly status report from git history and issues
argument-hint: <since date, e.g. 2026-11-23>
---
Draft a status report for the period since $ARGUMENTS.
Use `git log --since=$ARGUMENTS --oneline`, `gh issue list --state closed --search "closed:>=$ARGUMENTS"`
and `gh issue list --state open`.

Format:
Status report no. __ — weeks __–__
Phase / sprint:
Done: (closed issues and merged pull requests, in plain words)
Not done, and why: (open issues due in this period; leave the reason for me to fill in)
Next two weeks:
Next gate: G_ planned for week __
Risks (new or changed):
Change requests: (entries added to docs/thesis/CHANGELOG_BASELINE.md in this period, or none)
Need from supervisors:

Write it to docs/thesis/status-reports/ with the end date as file name. Keep it short and factual.
