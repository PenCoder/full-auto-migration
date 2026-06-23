# Migration Wizard

**Move from Windows 11 to Linux Mint — automatically, step by step, with no technical knowledge required.**

[Download the latest release](downloads.md){ .md-button .md-button--primary }
[Read the user guide](USER_MIGRATION_GUIDE.md){ .md-button }

---

## Why this exists

Digital sovereignty — the capacity to exercise meaningful control over your own digital infrastructure, data flows, and computational processes — is increasingly hard to exercise on a closed platform. Windows 11 integrates telemetry that cannot be fully disabled, and there's no way to verify or constrain what it collects.

Survey data shows a real preference–behaviour gap in Europe: 63.2% of organisations rate open-source software as critical for sovereignty, 47.4% cite reducing dependency on non-EU vendors as a strategic priority — yet Windows still holds roughly two-thirds of EU desktop market share. The gap isn't a lack of will, it's migration barriers: technical complexity, fear of data loss, and uncertainty about whether familiar apps have a Linux equivalent.

This tool exists to remove that barrier — a semi-automated migration framework that moves files, applications, and desktop settings from Windows 11 to Linux Mint with data intact and workflow preserved.

See the [project walkthrough](PROJECT_WALKTHROUGH.md) for the full framing, including the project's own honest account of what was and wasn't achieved.

---

## How it works

| Phase | Machine | What happens |
|---|---|---|
| **1 — Prepare** | Windows 11 | Scan → app mapping → files and settings packed into a bundle |
| **2 — Restore** | Linux Mint | Bundle copied via USB → files restored, apps installed, settings applied — verified by hash, reported, and reversible |

Three modes trade off automation for control without changing the underlying pipeline:

| Mode | Who it is for | Online lookups |
|---|---|---|
| **Guided** | Non-technical users | Never |
| **Balanced** | Comfortable with computers | Never |
| **Expert** | Advanced users | Verifies a package already chosen via Repology — never to find one |

---

## What it does, by the numbers

- **238** curated Windows→Linux app mappings
- **192** automated tests (184 passing)
- **100%** file integrity (SHA-256 verified) on real restore runs
- **2** platforms packaged — Windows `.exe` and a Linux binary, auto-embedded into every bundle
- **0** telemetry, ads, or remote analytics calls — the only network call this tool ever makes is an opt-in Repology package check in Expert mode

---

## Get started

- [Download the latest release](downloads.md)
- [Follow the user migration guide](USER_MIGRATION_GUIDE.md)
- [Read the project walkthrough](PROJECT_WALKTHROUGH.md) for the project-management and sovereignty framing
- Browse the [source on GitHub](https://github.com/PenCoder/full-auto-migration)
